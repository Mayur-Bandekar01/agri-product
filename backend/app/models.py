import enum
from datetime import UTC, datetime

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey, Enum, Boolean
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    """Return a UTC timestamp compatible with the existing naive SQLite columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class RoleEnum(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class PaymentMethodEnum(str, enum.Enum):
    cash = "cash"
    upi = "upi"
    bank = "bank"
    credit = "credit"


class InvoiceStatusEnum(str, enum.Enum):
    paid = "paid"
    partial = "partial"
    credit = "credit"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.staff, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    unit = Column(String, nullable=False)       # Bag, Kg, Packet, Bottle, etc.
    rate = Column(Numeric(12, 2), nullable=True)
    # `rate` remains as a compatibility field for billing/history integrations.
    selling_price = Column(Numeric(12, 2), nullable=True)
    stock = Column(Numeric(12, 2), default=0)
    min_stock = Column(Numeric(12, 2), default=10)
    expires_on = Column(DateTime, nullable=True)
    supplier = Column(String(160), nullable=True)
    is_active = Column(Boolean, default=True)
    pack_size = Column(String(80), nullable=True)
    purchase_price_including_gst = Column(Numeric(12, 2), nullable=True)
    purchase_price_excluding_gst = Column(Numeric(12, 2), nullable=True)
    purchase_gst_component = Column(Numeric(12, 2), nullable=True)
    gst_rate = Column(Numeric(5, 2), nullable=True)
    gst_selection_type = Column(String(12), nullable=False, default="preset")
    selling_price_tax_mode = Column(String(20), nullable=False, default="exclusive")
    initial_quantity = Column(Numeric(12, 2), nullable=True)
    source_reference = Column(String(200), nullable=True)
    # New fields based on PDF structure
    hsn_code = Column(String(12), nullable=True, index=True)  # HSN/SAC code for GST
    discount_percentage = Column(Numeric(5, 2), nullable=True, default=0)  # Default discount %

    invoice_items = relationship("InvoiceItem", back_populates="product")

    @property
    def status(self) -> str:
        if self.stock <= 0:
            return "out_of_stock"
        if self.stock <= self.min_stock:
            return "low_stock"
        return "in_stock"


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    movement_type = Column(String(30), nullable=False)
    quantity_in = Column(Numeric(12, 2), nullable=False, default=0)
    quantity_out = Column(Numeric(12, 2), nullable=False, default=0)
    previous_stock = Column(Numeric(12, 2), nullable=False)
    new_stock = Column(Numeric(12, 2), nullable=False)
    reference_number = Column(String(120), nullable=True)
    movement_date = Column(DateTime, default=utcnow, nullable=False)
    notes = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class ProductPriceHistory(Base):
    __tablename__ = "product_price_history"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    old_purchase_price = Column(Numeric(12, 2), nullable=True)
    new_purchase_price = Column(Numeric(12, 2), nullable=True)
    old_selling_price = Column(Numeric(12, 2), nullable=True)
    new_selling_price = Column(Numeric(12, 2), nullable=True)
    changed_at = Column(DateTime, default=utcnow, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String(300), nullable=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = Column(Integer, primary_key=True)
    source_reference = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    inserted_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    report_json = Column(String, nullable=True)


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    invoices = relationship("Invoice", back_populates="farmer")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, unique=True, index=True, nullable=False)
    # A checkout key makes retrying a request safe when a browser loses the
    # response after SQLite has already committed the sale.
    client_request_id = Column(String(64), unique=True, index=True, nullable=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    date = Column(DateTime, default=utcnow, index=True)
    subtotal = Column(Numeric(12, 2), default=0)
    discount = Column(Numeric(12, 2), default=0)
    tax = Column(Numeric(12, 2), default=0)
    grand_total = Column(Numeric(12, 2), default=0)

    payment_method = Column(Enum(PaymentMethodEnum), default=PaymentMethodEnum.cash)
    amount_paid = Column(Numeric(12, 2), default=0)
    balance_due = Column(Numeric(12, 2), default=0, index=True)
    status = Column(Enum(InvoiceStatusEnum), default=InvoiceStatusEnum.paid)

    farmer = relationship("Farmer", back_populates="invoices")
    user = relationship("User")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    product_name = Column(String, nullable=False)  # snapshot at time of sale
    unit = Column(String, nullable=False)
    qty = Column(Numeric(12, 2), nullable=False)
    rate = Column(Numeric(12, 2), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=True)
    gst_selection_type = Column(String(12), nullable=True)
    selling_price_tax_mode = Column(String(20), nullable=True)
    taxable_amount = Column(Numeric(12, 2), nullable=True)
    tax_amount = Column(Numeric(12, 2), nullable=True)
    total_amount = Column(Numeric(12, 2), nullable=True)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")


class Payment(Base):
    """An immutable receipt against an invoice."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    receipt_no = Column(String(40), unique=True, nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(Enum(PaymentMethodEnum), nullable=False)
    received_at = Column(DateTime, default=utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="payments")
    user = relationship("User")
