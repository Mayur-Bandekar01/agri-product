from typing import Optional, List
from decimal import Decimal, ROUND_HALF_UP
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/products", tags=["Products"])
logger = logging.getLogger(__name__)


def _sync_purchase_cost(data):
    """Derive ex-tax cost and GST component from the tax-inclusive cost."""
    inclusive = data.get("purchase_price_including_gst")
    gst = data.get("gst_rate")
    if inclusive is not None and gst is not None:
        inclusive, gst = Decimal(inclusive), Decimal(gst)
        excluding = (inclusive / (Decimal(1) + gst / Decimal(100))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        data["purchase_price_excluding_gst"] = excluding
        data["purchase_gst_component"] = inclusive - excluding


def _gst_selection(rate):
    if rate is None:
        return "preset"
    return "preset" if Decimal(rate) in {Decimal("0"), Decimal("5"), Decimal("12"), Decimal("18"), Decimal("28")} else "custom"


@router.get("", response_model=List[schemas.ProductOut])
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = Query(None, description="Filter by category, or 'All'"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.Product).filter(models.Product.is_active == True)  # noqa: E712
    if category and category != "All":
        q = q.filter(models.Product.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Product.name.ilike(like)) | (models.Product.sku.ilike(like))
        )
    return q.order_by(models.Product.name).all()


@router.get("/low-stock", response_model=List[schemas.ProductOut])
def low_stock_products(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    products = db.query(models.Product).filter(models.Product.is_active == True).all()  # noqa: E712
    return [p for p in products if p.stock <= p.min_stock]


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=schemas.ProductOut, status_code=201)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    if db.query(models.Product).filter(models.Product.sku == payload.sku).first():
        raise HTTPException(status_code=400, detail="SKU already exists")
    data = payload.model_dump()
    data["gst_selection_type"] = data.get("gst_selection_type") or _gst_selection(data.get("gst_rate"))
    selling_price = data.get("selling_price", data.get("rate"))
    data["selling_price"] = data["rate"] = selling_price
    _sync_purchase_cost(data)
    product = models.Product(**data)
    db.add(product)
    try:
        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        logger.exception("Failed to create product sku=%s", payload.sku)
        raise
    return product


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.sku is not None and payload.sku != product.sku:
        duplicate = db.query(models.Product).filter(models.Product.sku == payload.sku).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="SKU already exists")
    changes = payload.model_dump(exclude_unset=True)
    if "gst_rate" in changes and "gst_selection_type" not in changes:
        changes["gst_selection_type"] = _gst_selection(changes["gst_rate"])
    if "selling_price" in changes or "rate" in changes:
        selling_price = changes.get("selling_price", changes.get("rate"))
        changes["selling_price"] = changes["rate"] = selling_price
    calculation = {
        "purchase_price_including_gst": changes.get("purchase_price_including_gst", product.purchase_price_including_gst),
        "gst_rate": changes.get("gst_rate", product.gst_rate),
    }
    if "purchase_price_including_gst" in changes or "gst_rate" in changes:
        _sync_purchase_cost(calculation)
        changes.update({k: calculation[k] for k in ("purchase_price_excluding_gst", "purchase_gst_component") if k in calculation})
    old_purchase = product.purchase_price_including_gst
    old_selling = product.selling_price if product.selling_price is not None else product.rate
    for field, value in changes.items():
        setattr(product, field, value)
    new_purchase = product.purchase_price_including_gst
    new_selling = product.selling_price if product.selling_price is not None else product.rate
    if old_purchase != new_purchase or old_selling != new_selling:
        db.add(models.ProductPriceHistory(
            product_id=product.id,
            old_purchase_price=old_purchase,
            new_purchase_price=new_purchase,
            old_selling_price=old_selling,
            new_selling_price=new_selling,
            changed_by=current_user.id,
            reason="Product pricing edited",
        ))
    try:
        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        logger.exception("Failed to update product id=%s sku=%s", product.id, product.sku)
        raise
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Soft delete to preserve invoice history integrity
    product.is_active = False
    db.commit()
    return None
