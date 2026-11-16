"""
Chartered Accountant Export Router
Provides comprehensive export functionality for inventory transactions,
stock movements, and financial data for accounting and audit purposes.
"""
from datetime import datetime
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from ..database import get_db
from ..auth import get_current_user
from ..models import (
    User, Product, StockMovement, Invoice, InvoiceItem, 
    Payment, ProductPriceHistory, Farmer
)


router = APIRouter(prefix="/ca-export", tags=["CA Export"])


def _apply_header_style(worksheet, row_num: int):
    """Apply consistent header styling to Excel worksheet."""
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for cell in worksheet[row_num]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border


def _auto_adjust_column_width(worksheet):
    """Auto-adjust column widths based on content."""
    for column in worksheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)  # Cap at 50
        worksheet.column_dimensions[column_letter].width = adjusted_width


def _format_decimal(value) -> str:
    """Format decimal values for display."""
    if value is None:
        return "0.00"
    return f"{float(value):.2f}"


def _format_date(value) -> str:
    """Format datetime values."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d %H:%M:%S")


@router.get("/inventory-transactions")
async def export_inventory_transactions(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_inactive: bool = Query(False, description="Include inactive products"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export comprehensive inventory transactions for chartered accountant.
    
    Creates an Excel file with multiple sheets:
    - Product Master: All products with current status
    - Stock Movements: All stock in/out transactions
    - Sales Detail: Invoice items with tax breakup
    - Price History: Changes in purchase/selling prices
    - Payment Receipts: All payment transactions
    - Summary: Aggregate statistics
    """
    
    # Parse date filters
    date_start = None
    date_end = None
    if start_date:
        try:
            date_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            date_end = datetime.strptime(end_date, "%Y-%m-%d")
            date_end = date_end.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    # Create workbook
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet
    
    # ===== SHEET 1: Product Master =====
    ws_products = wb.create_sheet("Product Master")
    product_headers = [
        "S.No", "Product Name", "SKU", "HSN/SAC Code", "Category", "Unit",
        "Current Stock", "Min Stock", "Status", "Purchase Price (Excl. GST)",
        "Purchase Price (Incl. GST)", "GST Rate %", "Selling Price",
        "Discount %", "Supplier", "Pack Size", "Active"
    ]
    ws_products.append(product_headers)
    _apply_header_style(ws_products, 1)
    
    # Fetch products
    products_query = db.query(Product)
    if not include_inactive:
        products_query = products_query.filter(Product.is_active == True)
    products = products_query.order_by(Product.name).all()
    
    for idx, product in enumerate(products, start=1):
        ws_products.append([
            idx,
            product.name,
            product.sku,
            product.hsn_code or "",
            product.category,
            product.unit,
            _format_decimal(product.stock),
            _format_decimal(product.min_stock),
            product.status,
            _format_decimal(product.purchase_price_excluding_gst),
            _format_decimal(product.purchase_price_including_gst),
            _format_decimal(product.gst_rate),
            _format_decimal(product.selling_price),
            _format_decimal(product.discount_percentage),
            product.supplier or "",
            product.pack_size or "",
            "Yes" if product.is_active else "No"
        ])
    
    _auto_adjust_column_width(ws_products)
    
    # ===== SHEET 2: Stock Movements =====
    ws_stock = wb.create_sheet("Stock Movements")
    stock_headers = [
        "S.No", "Date", "Product Name", "SKU", "Movement Type",
        "Quantity In", "Quantity Out", "Previous Stock", "New Stock",
        "Reference No", "Notes", "Created By"
    ]
    ws_stock.append(stock_headers)
    _apply_header_style(ws_stock, 1)
    
    # Fetch stock movements
    stock_query = db.query(
        StockMovement, Product.name, Product.sku, User.username
    ).join(Product, StockMovement.product_id == Product.id
    ).outerjoin(User, StockMovement.created_by == User.id)
    
    if date_start:
        stock_query = stock_query.filter(StockMovement.movement_date >= date_start)
    if date_end:
        stock_query = stock_query.filter(StockMovement.movement_date <= date_end)
    
    stock_movements = stock_query.order_by(desc(StockMovement.movement_date)).all()
    
    for idx, (movement, product_name, sku, username) in enumerate(stock_movements, start=1):
        ws_stock.append([
            idx,
            _format_date(movement.movement_date),
            product_name,
            sku,
            movement.movement_type,
            _format_decimal(movement.quantity_in),
            _format_decimal(movement.quantity_out),
            _format_decimal(movement.previous_stock),
            _format_decimal(movement.new_stock),
            movement.reference_number or "",
            movement.notes or "",
            username or "System"
        ])
    
    _auto_adjust_column_width(ws_stock)
    
    # ===== SHEET 3: Sales Detail =====
    ws_sales = wb.create_sheet("Sales Detail")
    sales_headers = [
        "S.No", "Invoice No", "Invoice Date", "Customer Name", "Mobile",
        "Product Name", "SKU", "HSN Code", "Quantity", "Unit", "Rate",
        "Taxable Amount", "GST Rate %", "GST Amount", "Total Amount",
        "Payment Method", "Amount Paid", "Balance Due", "Status"
    ]
    ws_sales.append(sales_headers)
    _apply_header_style(ws_sales, 1)
    
    # Fetch sales transactions
    sales_query = db.query(
        Invoice, InvoiceItem, Farmer, Product
    ).join(InvoiceItem, Invoice.id == InvoiceItem.invoice_id
    ).outerjoin(Farmer, Invoice.farmer_id == Farmer.id
    ).outerjoin(Product, InvoiceItem.product_id == Product.id)
    
    if date_start:
        sales_query = sales_query.filter(Invoice.date >= date_start)
    if date_end:
        sales_query = sales_query.filter(Invoice.date <= date_end)
    
    sales = sales_query.order_by(desc(Invoice.date)).all()
    
    for idx, (invoice, item, farmer, product) in enumerate(sales, start=1):
        ws_sales.append([
            idx,
            invoice.invoice_no,
            _format_date(invoice.date),
            farmer.name if farmer else "Walk-in Customer",
            farmer.mobile if farmer else "",
            item.product_name,
            product.sku if product else "",
            product.hsn_code if product else "",
            _format_decimal(item.qty),
            item.unit,
            _format_decimal(item.rate),
            _format_decimal(item.taxable_amount),
            _format_decimal(item.gst_rate),
            _format_decimal(item.tax_amount),
            _format_decimal(item.total_amount),
            invoice.payment_method.value,
            _format_decimal(invoice.amount_paid),
            _format_decimal(invoice.balance_due),
            invoice.status.value
        ])
    
    _auto_adjust_column_width(ws_sales)
    
    # ===== SHEET 4: Price History =====
    ws_price = wb.create_sheet("Price History")
    price_headers = [
        "S.No", "Date", "Product Name", "SKU",
        "Old Purchase Price", "New Purchase Price",
        "Old Selling Price", "New Selling Price",
        "Changed By", "Reason"
    ]
    ws_price.append(price_headers)
    _apply_header_style(ws_price, 1)
    
    # Fetch price history
    price_query = db.query(
        ProductPriceHistory, Product.name, Product.sku, User.username
    ).join(Product, ProductPriceHistory.product_id == Product.id
    ).outerjoin(User, ProductPriceHistory.changed_by == User.id)
    
    if date_start:
        price_query = price_query.filter(ProductPriceHistory.changed_at >= date_start)
    if date_end:
        price_query = price_query.filter(ProductPriceHistory.changed_at <= date_end)
    
    price_history = price_query.order_by(desc(ProductPriceHistory.changed_at)).all()
    
    for idx, (history, product_name, sku, username) in enumerate(price_history, start=1):
        ws_price.append([
            idx,
            _format_date(history.changed_at),
            product_name,
            sku,
            _format_decimal(history.old_purchase_price),
            _format_decimal(history.new_purchase_price),
            _format_decimal(history.old_selling_price),
            _format_decimal(history.new_selling_price),
            username or "System",
            history.reason or ""
        ])
    
    _auto_adjust_column_width(ws_price)
    
    # ===== SHEET 5: Payment Receipts =====
    ws_payments = wb.create_sheet("Payment Receipts")
    payment_headers = [
        "S.No", "Receipt No", "Date", "Invoice No", "Customer Name",
        "Amount", "Payment Method", "Received By"
    ]
    ws_payments.append(payment_headers)
    _apply_header_style(ws_payments, 1)
    
    # Fetch payments
    payment_query = db.query(
        Payment, Invoice, Farmer, User
    ).join(Invoice, Payment.invoice_id == Invoice.id
    ).outerjoin(Farmer, Invoice.farmer_id == Farmer.id
    ).outerjoin(User, Payment.user_id == User.id)
    
    if date_start:
        payment_query = payment_query.filter(Payment.received_at >= date_start)
    if date_end:
        payment_query = payment_query.filter(Payment.received_at <= date_end)
    
    payments = payment_query.order_by(desc(Payment.received_at)).all()
    
    for idx, (payment, invoice, farmer, user) in enumerate(payments, start=1):
        ws_payments.append([
            idx,
            payment.receipt_no,
            _format_date(payment.received_at),
            invoice.invoice_no,
            farmer.name if farmer else "Walk-in Customer",
            _format_decimal(payment.amount),
            payment.method.value,
            user.username if user else "System"
        ])
    
    _auto_adjust_column_width(ws_payments)
    
    # ===== SHEET 6: Summary =====
    ws_summary = wb.create_sheet("Summary")
    ws_summary.append(["INVENTORY TRANSACTION SUMMARY"])
    ws_summary.append(["Generated On:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    ws_summary.append(["Generated By:", current_user.username])
    ws_summary.append(["Date Range:", f"{start_date or 'All'} to {end_date or 'All'}"])
    ws_summary.append([])
    
    # Calculate statistics
    total_products = db.query(func.count(Product.id)).scalar()
    active_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()
    total_stock_value = db.query(
        func.sum(Product.stock * Product.purchase_price_excluding_gst)
    ).filter(Product.is_active == True).scalar() or 0
    
    ws_summary.append(["INVENTORY STATISTICS", ""])
    ws_summary.append(["Total Products:", total_products])
    ws_summary.append(["Active Products:", active_products])
    ws_summary.append(["Total Stock Value (₹):", _format_decimal(total_stock_value)])
    ws_summary.append([])
    
    # Sales statistics
    invoice_filter = []
    if date_start:
        invoice_filter.append(Invoice.date >= date_start)
    if date_end:
        invoice_filter.append(Invoice.date <= date_end)
    
    if invoice_filter:
        total_invoices = db.query(func.count(Invoice.id)).filter(*invoice_filter).scalar()
        total_sales = db.query(func.sum(Invoice.grand_total)).filter(*invoice_filter).scalar() or 0
        total_paid = db.query(func.sum(Invoice.amount_paid)).filter(*invoice_filter).scalar() or 0
        total_outstanding = db.query(func.sum(Invoice.balance_due)).filter(*invoice_filter).scalar() or 0
    else:
        total_invoices = db.query(func.count(Invoice.id)).scalar()
        total_sales = db.query(func.sum(Invoice.grand_total)).scalar() or 0
        total_paid = db.query(func.sum(Invoice.amount_paid)).scalar() or 0
        total_outstanding = db.query(func.sum(Invoice.balance_due)).scalar() or 0
    
    ws_summary.append(["SALES STATISTICS", ""])
    ws_summary.append(["Total Invoices:", total_invoices])
    ws_summary.append(["Total Sales (₹):", _format_decimal(total_sales)])
    ws_summary.append(["Total Amount Paid (₹):", _format_decimal(total_paid)])
    ws_summary.append(["Total Outstanding (₹):", _format_decimal(total_outstanding)])
    
    # Style summary sheet
    ws_summary['A1'].font = Font(bold=True, size=14)
    for row in ws_summary.iter_rows(min_row=6, max_row=6):
        for cell in row:
            cell.font = Font(bold=True)
    for row in ws_summary.iter_rows(min_row=11, max_row=11):
        for cell in row:
            cell.font = Font(bold=True)
    
    _auto_adjust_column_width(ws_summary)
    
    # Move Summary to first position
    wb._sheets.insert(0, wb._sheets.pop())
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename
    date_suffix = ""
    if start_date and end_date:
        date_suffix = f"_{start_date}_to_{end_date}"
    elif start_date:
        date_suffix = f"_from_{start_date}"
    elif end_date:
        date_suffix = f"_until_{end_date}"
    
    filename = f"Inventory_Transactions_CA_Export{date_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/gst-report")
async def export_gst_report(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export GST report for tax filing purposes.
    
    Creates an Excel file with GST-wise sales summary.
    """
    
    # Parse dates
    try:
        date_start = datetime.strptime(start_date, "%Y-%m-%d")
        date_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "GST Summary"
    
    # Headers
    headers = [
        "HSN/SAC Code", "GST Rate %", "Taxable Amount (₹)",
        "CGST (₹)", "SGST (₹)", "Total GST (₹)", "Total Amount (₹)"
    ]
    ws.append(headers)
    _apply_header_style(ws, 1)
    
    # Fetch GST-wise sales
    gst_data = db.query(
        Product.hsn_code,
        InvoiceItem.gst_rate,
        func.sum(InvoiceItem.taxable_amount).label("taxable_amount"),
        func.sum(InvoiceItem.tax_amount).label("tax_amount"),
        func.sum(InvoiceItem.total_amount).label("total_amount")
    ).join(InvoiceItem, Product.id == InvoiceItem.product_id
    ).join(Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(
        Invoice.date >= date_start,
        Invoice.date <= date_end
    ).group_by(Product.hsn_code, InvoiceItem.gst_rate
    ).order_by(Product.hsn_code, InvoiceItem.gst_rate).all()
    
    total_taxable = 0
    total_gst = 0
    total_amount = 0
    
    for hsn_code, gst_rate, taxable_amount, tax_amount, item_total in gst_data:
        cgst = float(tax_amount or 0) / 2
        sgst = float(tax_amount or 0) / 2
        
        ws.append([
            hsn_code or "N/A",
            _format_decimal(gst_rate),
            _format_decimal(taxable_amount),
            _format_decimal(cgst),
            _format_decimal(sgst),
            _format_decimal(tax_amount),
            _format_decimal(item_total)
        ])
        
        total_taxable += float(taxable_amount or 0)
        total_gst += float(tax_amount or 0)
        total_amount += float(item_total or 0)
    
    # Add totals
    ws.append([])
    ws.append([
        "TOTAL", "",
        _format_decimal(total_taxable),
        _format_decimal(total_gst / 2),
        _format_decimal(total_gst / 2),
        _format_decimal(total_gst),
        _format_decimal(total_amount)
    ])
    
    # Style totals row
    total_row = ws.max_row
    for cell in ws[total_row]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    
    _auto_adjust_column_width(ws)
    
    # Add metadata
    ws.insert_rows(0, 3)
    ws['A1'] = "GST REPORT"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f"Period: {start_date} to {end_date}"
    ws['A3'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"GST_Report_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
