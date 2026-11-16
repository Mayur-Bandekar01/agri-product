from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/invoices", tags=["Billing"])

TAX_RATE = Decimal("0.05")  # Compatibility rate for legacy products without GST configured.
MONEY = Decimal("0.01")


def _money(value: Decimal | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _invoice_matches_payload(invoice: models.Invoice, payload: schemas.InvoiceCreate) -> bool:
    requested_quantities: dict[int, Decimal] = {}
    for item in payload.items:
        requested_quantities[item.product_id] = requested_quantities.get(item.product_id, Decimal("0")) + Decimal(str(item.qty))

    saved_quantities: dict[int, Decimal] = {}
    for item in invoice.items:
        if item.product_id is not None:
            saved_quantities[item.product_id] = saved_quantities.get(item.product_id, Decimal("0")) + Decimal(item.qty)

    requested_discount = min(_money(payload.discount), Decimal(invoice.subtotal))
    requested_paid = min(_money(payload.amount_paid), Decimal(invoice.grand_total))
    return (
        invoice.farmer_id == payload.farmer_id
        and saved_quantities == requested_quantities
        and Decimal(invoice.discount) == requested_discount
        and invoice.payment_method == payload.payment_method
        and Decimal(invoice.amount_paid) == requested_paid
    )


@router.post("", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    payload: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
    client_request_id: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    if client_request_id and len(client_request_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid checkout request key")
    if client_request_id:
        existing = db.query(models.Invoice).filter(
            models.Invoice.client_request_id == client_request_id
        ).first()
        if existing:
            if not _invoice_matches_payload(existing, payload):
                raise HTTPException(status_code=409, detail="Checkout key was already used for a different bill")
            return existing
        # The read above opens SQLAlchemy's deferred SQLite transaction.
        # End it before requesting an IMMEDIATE write lock below.
        db.rollback()
    # SQLite only permits one writer. Taking the write lock before reading
    # inventory makes validation, invoice numbering and stock deduction one
    # transaction rather than a check-then-write race.
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        # Check again after the write lock. A concurrent retry may have
        # completed while this request waited for SQLite.
        if client_request_id:
            existing = db.query(models.Invoice).filter(
                models.Invoice.client_request_id == client_request_id
            ).first()
            if existing:
                if not _invoice_matches_payload(existing, payload):
                    raise HTTPException(status_code=409, detail="Checkout key was already used for a different bill")
                db.rollback()
                return existing
        return _create_invoice(payload, db, current_user, client_request_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def _create_invoice(
    payload: schemas.InvoiceCreate, db: Session, current_user: models.User,
    client_request_id: str | None = None,
) -> models.Invoice:
    if not payload.items:
        raise HTTPException(status_code=400, detail="A bill needs at least one item")
    if payload.payment_method == models.PaymentMethodEnum.credit and payload.amount_paid > 0:
        raise HTTPException(status_code=400, detail="A credit invoice cannot include an immediate payment")

    if payload.farmer_id is not None:
        farmer = db.query(models.Farmer).filter(models.Farmer.id == payload.farmer_id).first()
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer not found")

    requested_quantities: dict[int, Decimal] = {}
    for item in payload.items:
        requested_quantities[item.product_id] = requested_quantities.get(item.product_id, Decimal("0")) + Decimal(str(item.qty))

    line_items = []
    subtotal = Decimal("0")

    for product_id, qty in requested_quantities.items():
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        if product.rate is None:
            raise HTTPException(status_code=400, detail=f"Price is not set for '{product.name}'")
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
        if Decimal(product.stock) < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{product.name}' (available: {product.stock})",
            )
        rate = Decimal(str(product.gst_rate if product.gst_rate is not None else TAX_RATE * 100))
        tax_fraction = rate / Decimal("100")
        mode = product.selling_price_tax_mode or "exclusive"
        listed_amount = _money(Decimal(product.rate) * qty)
        taxable_before_discount = (
            _money(listed_amount / (Decimal("1") + tax_fraction))
            if mode == "inclusive" and rate > 0 else listed_amount
        )
        subtotal += taxable_before_discount
        line_items.append({
            "product": product, "qty": qty, "rate": Decimal(product.rate),
            "gst_rate": rate, "gst_selection_type": product.gst_selection_type or "preset",
            "selling_price_tax_mode": mode, "taxable_before_discount": taxable_before_discount,
        })

    # Invoice-level discount is allocated over taxable line values; GST is
    # then calculated once at each product's snapshotted rate.
    discount = min(_money(payload.discount), subtotal)
    remaining_discount = discount
    remaining_taxable = subtotal
    tax = Decimal("0")
    grand_total = Decimal("0")
    for index, line in enumerate(line_items):
        before = line["taxable_before_discount"]
        allocated_discount = (
            remaining_discount if index == len(line_items) - 1 else
            min(before, _money(discount * before / subtotal)) if subtotal else Decimal("0")
        )
        remaining_discount -= allocated_discount
        taxable_line = max(Decimal("0"), before - allocated_discount)
        line_tax = _money(taxable_line * line["gst_rate"] / Decimal("100"))
        line_total = _money(taxable_line + line_tax)
        line.update(taxable_amount=taxable_line, tax_amount=line_tax, total_amount=line_total)
        tax += line_tax
        grand_total += line_total
    tax = _money(tax)
    grand_total = _money(grand_total)
    taxable_amount = max(Decimal("0"), subtotal - discount)
    amount_paid = _money(payload.amount_paid)

    if payload.payment_method == models.PaymentMethodEnum.credit and amount_paid == 0:
        status_ = models.InvoiceStatusEnum.credit
    elif amount_paid >= grand_total:
        status_ = models.InvoiceStatusEnum.paid
        amount_paid = grand_total  # don't overpay on record
    elif amount_paid <= 0:
        status_ = models.InvoiceStatusEnum.credit
    else:
        status_ = models.InvoiceStatusEnum.partial

    balance_due = max(Decimal("0"), grand_total - amount_paid)

    invoice = models.Invoice(
        # The numeric primary key, assigned by the database, is the only
        # concurrency-safe invoice sequence. A temporary unique value lets us
        # flush first and then format the customer-facing number.
        invoice_no=f"PENDING-{uuid4()}",
        client_request_id=client_request_id,
        farmer_id=payload.farmer_id,
        user_id=current_user.id,
        date=datetime.now(UTC).replace(tzinfo=None),
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        grand_total=grand_total,
        payment_method=payload.payment_method,
        amount_paid=amount_paid,
        balance_due=balance_due,
        status=status_,
    )
    db.add(invoice)
    db.flush()  # get invoice.id before adding items
    invoice.invoice_no = f"INV-{invoice.id:06d}"

    for line in line_items:
        product, qty = line["product"], line["qty"]
        db.add(
            models.InvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                product_name=product.name,
                unit=product.unit,
                qty=qty,
                rate=line["rate"],
                amount=line["total_amount"],
                gst_rate=line["gst_rate"],
                gst_selection_type=line["gst_selection_type"],
                selling_price_tax_mode=line["selling_price_tax_mode"],
                taxable_amount=line["taxable_amount"],
                tax_amount=line["tax_amount"],
                total_amount=line["total_amount"],
            )
        )
        product.stock = Decimal(product.stock) - Decimal(str(qty))  # deduct stock

    if amount_paid > 0:
        payment = models.Payment(
            receipt_no=f"PENDING-{uuid4()}",
            invoice_id=invoice.id,
            user_id=current_user.id,
            amount=amount_paid,
            method=payload.payment_method,
        )
        db.add(payment)
        db.flush()
        payment.receipt_no = f"REC-{payment.id:06d}"

    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin")),
):
    """Remove an erroneous invoice and return its quantities to inventory."""
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        for item in invoice.items:
            if item.product_id is not None:
                product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
                if product:
                    product.stock = Decimal(product.stock) + Decimal(item.qty)
        db.delete(invoice)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return None


@router.post("/{invoice_id}/payments", response_model=schemas.InvoiceOut)
def record_payment(
    invoice_id: int,
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        amount = _money(payload.amount)
        if payload.method == models.PaymentMethodEnum.credit:
            raise HTTPException(status_code=400, detail="Credit is not a received payment method")
        if amount > Decimal(invoice.balance_due):
            raise HTTPException(status_code=400, detail="Payment cannot exceed the outstanding balance")

        payment = models.Payment(
            receipt_no=f"PENDING-{uuid4()}",
            invoice_id=invoice.id,
            user_id=current_user.id,
            amount=amount,
            method=payload.method,
        )
        db.add(payment)
        db.flush()
        payment.receipt_no = f"REC-{payment.id:06d}"
        invoice.amount_paid = _money(Decimal(invoice.amount_paid) + amount)
        invoice.balance_due = _money(Decimal(invoice.grand_total) - Decimal(invoice.amount_paid))
        invoice.status = (
            models.InvoiceStatusEnum.paid if invoice.balance_due == 0
            else models.InvoiceStatusEnum.partial
        )
        db.commit()
        db.refresh(invoice)
        return invoice
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=List[schemas.InvoiceListOut])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    invoices = (
        db.query(models.Invoice)
        .options(joinedload(models.Invoice.farmer))
        .order_by(models.Invoice.date.desc())
        .all()
    )
    return [
        schemas.InvoiceListOut(
            id=i.id,
            invoice_no=i.invoice_no,
            farmer_id=i.farmer_id,
            farmer_name=i.farmer.name if i.farmer else "Walk-in Customer",
            date=i.date,
            grand_total=i.grand_total,
            amount_paid=i.amount_paid,
            balance_due=i.balance_due,
            payment_method=i.payment_method,
            status=i.status,
        )
        for i in invoices
    ]


@router.get("/{invoice_id}", response_model=schemas.InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
