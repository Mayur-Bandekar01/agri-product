from datetime import datetime
from typing import Literal, Optional, List
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import RoleEnum, PaymentMethodEnum, InvoiceStatusEnum


# ---------- AUTH ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: RoleEnum = RoleEnum.staff


class InitialAdminCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    username: str
    role: RoleEnum
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- PRODUCTS ----------
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=40)
    rate: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    purchase_price_including_gst: Optional[Decimal] = Field(default=None, ge=0)
    purchase_price_excluding_gst: Optional[Decimal] = Field(default=None, ge=0)
    purchase_gst_component: Optional[Decimal] = Field(default=None, ge=0)
    gst_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    gst_selection_type: Optional[Literal['preset', 'custom']] = None
    pack_size: Optional[str] = Field(default=None, max_length=80)
    initial_quantity: Optional[Decimal] = Field(default=None, ge=0)
    selling_price_tax_mode: Literal['inclusive', 'exclusive'] = 'exclusive'
    stock: float = Field(default=0, ge=0)
    min_stock: float = Field(default=10, ge=0)
    expires_on: Optional[datetime] = None
    supplier: Optional[str] = Field(default=None, max_length=160)
    is_active: bool = True
    hsn_code: Optional[str] = Field(default=None, max_length=12)
    discount_percentage: Optional[Decimal] = Field(default=0, ge=0, le=100)

    @model_validator(mode='before')
    @classmethod
    def sync_legacy_rate(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            if 'selling_price' not in value and 'rate' in value:
                value['selling_price'] = value['rate']
            elif 'rate' not in value and 'selling_price' in value:
                value['rate'] = value['selling_price']
        return value

    @model_validator(mode='after')
    def validate_gst_selection(self):
        if (self.gst_selection_type == 'preset' and self.gst_rate is not None
                and self.gst_rate not in {Decimal('0'), Decimal('5'), Decimal('12'), Decimal('18'), Decimal('28')}):
            raise ValueError('Preset GST must be 0%, 5%, 12%, 18%, or 28%; select Custom GST for other rates')
        return self


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=80)
    category: Optional[str] = Field(default=None, min_length=1, max_length=80)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=40)
    rate: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    purchase_price_including_gst: Optional[Decimal] = Field(default=None, ge=0)
    purchase_price_excluding_gst: Optional[Decimal] = Field(default=None, ge=0)
    purchase_gst_component: Optional[Decimal] = Field(default=None, ge=0)
    gst_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    gst_selection_type: Optional[Literal['preset', 'custom']] = None
    pack_size: Optional[str] = Field(default=None, max_length=80)
    initial_quantity: Optional[Decimal] = Field(default=None, ge=0)
    selling_price_tax_mode: Optional[Literal['inclusive', 'exclusive']] = None
    stock: Optional[float] = Field(default=None, ge=0)
    min_stock: Optional[float] = Field(default=None, ge=0)
    expires_on: Optional[datetime] = None
    supplier: Optional[str] = Field(default=None, max_length=160)
    is_active: Optional[bool] = None
    hsn_code: Optional[str] = Field(default=None, max_length=12)
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=100)

    @model_validator(mode='before')
    @classmethod
    def sync_legacy_rate(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            if 'selling_price' not in value and 'rate' in value:
                value['selling_price'] = value['rate']
            elif 'rate' not in value and 'selling_price' in value:
                value['rate'] = value['selling_price']
        return value

    @model_validator(mode='after')
    def validate_gst_selection(self):
        if (self.gst_selection_type == 'preset' and self.gst_rate is not None
                and self.gst_rate not in {Decimal('0'), Decimal('5'), Decimal('12'), Decimal('18'), Decimal('28')}):
            raise ValueError('Preset GST must be 0%, 5%, 12%, 18%, or 28%; select Custom GST for other rates')
        return self


class ProductOut(ProductBase):
    # Existing databases may contain historical negative inventory.  Preserve
    # their readability so an administrator can correct the record; new and
    # updated product input remains constrained by ProductBase/ProductUpdate.
    # Keep historical products readable while new and updated products use
    # the controlled Fertilizer/Pesticides product types.
    category: str
    stock: float
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str


# ---------- FARMERS ----------
class FarmerBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    mobile: str = Field(min_length=6, max_length=30)
    location: Optional[str] = Field(default=None, max_length=160)


class FarmerCreate(FarmerBase):
    pass


class FarmerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    mobile: Optional[str] = Field(default=None, min_length=6, max_length=30)
    location: Optional[str] = Field(default=None, max_length=160)


class FarmerOut(FarmerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class FarmerProfile(FarmerOut):
    total_purchases: float
    outstanding: float
    bill_count: int


class FarmerListOut(FarmerProfile):
    last_purchase: Optional[datetime] = None


# ---------- BILLING ----------
class BillItemIn(BaseModel):
    product_id: int = Field(gt=0)
    qty: float = Field(gt=0)


class InvoiceCreate(BaseModel):
    farmer_id: Optional[int] = None
    items: List[BillItemIn]
    discount: float = Field(default=0, ge=0)
    payment_method: PaymentMethodEnum = PaymentMethodEnum.cash
    amount_paid: float = Field(default=0, ge=0)


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    method: PaymentMethodEnum


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    receipt_no: str
    amount: float
    method: PaymentMethodEnum
    received_at: datetime


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: str
    unit: str
    qty: float
    rate: float
    amount: float
    gst_rate: Optional[Decimal] = None
    gst_selection_type: Optional[Literal['preset', 'custom']] = None
    selling_price_tax_mode: Optional[Literal['inclusive', 'exclusive']] = None
    taxable_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_no: str
    farmer_id: Optional[int]
    date: datetime
    subtotal: float
    discount: float
    tax: float
    grand_total: float
    payment_method: PaymentMethodEnum
    amount_paid: float
    balance_due: float
    status: InvoiceStatusEnum
    items: List[InvoiceItemOut] = []


class InvoiceListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_no: str
    farmer_id: Optional[int]
    farmer_name: Optional[str] = None
    date: datetime
    grand_total: float
    amount_paid: float
    balance_due: float
    payment_method: PaymentMethodEnum
    status: InvoiceStatusEnum


# ---------- DASHBOARD / REPORTS ----------
class DashboardSummary(BaseModel):
    todays_sales: float
    bills_today: int
    outstanding_total: float
    low_stock_count: int


class SalesPoint(BaseModel):
    label: str
    total: float


class TopProduct(BaseModel):
    name: str
    total: float


class PaymentSplit(BaseModel):
    method: str
    total: float
    percent: float


class OutstandingSummary(BaseModel):
    total_outstanding: float
    due_today: float
    overdue: float
    customers_with_dues: int


class NotificationOut(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    message: str
    created_at: datetime
    action_view: Optional[str] = None
