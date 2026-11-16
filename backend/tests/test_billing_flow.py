"""End-to-end checks for the core billing rules."""
import os
import tempfile
import io
import zipfile
import pytest

# Configure an isolated SQLite file before importing the application modules.
db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db_file.close()
os.environ["ADINATH_DB_PATH"] = db_file.name

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def login_as_admin(client: TestClient) -> dict[str, str]:
    setup = client.post("/auth/setup", json={
        "name": "Test Admin", "username": "admin", "password": "safe-password-123",
    })
    assert setup.status_code == 201
    login = client.post("/auth/login", data={"username": "admin", "password": "safe-password-123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_invoice_deducts_stock_and_updates_dashboard():
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Seed & Feed", "sku": "SEED-1", "category": "Fertilizer", "unit": "Bag",
        "rate": 100, "stock": 10, "min_stock": 2,
    })
    assert product.status_code == 201

    invoice = client.post("/invoices", headers=headers, json={
        "items": [{"product_id": product.json()["id"], "qty": 3}],
        "payment_method": "cash", "amount_paid": 315,
    })
    assert invoice.status_code == 201
    assert invoice.json()["grand_total"] == 315
    assert invoice.json()["status"] == "paid"

    remaining = client.get(f"/products/{product.json()['id']}", headers=headers)
    assert remaining.json()["stock"] == 7
    assert client.get("/dashboard/sales-chart?range=7d", headers=headers).status_code == 200


def test_custom_decimal_gst_is_saved_and_snapshotted_on_invoice():
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Custom GST Item", "sku": "CUSTOM-GST-1", "category": "Fertilizer",
        "unit": "Bag", "selling_price": 107.50, "stock": 2,
        "gst_rate": 7.5, "gst_selection_type": "custom", "selling_price_tax_mode": "inclusive",
    })
    assert product.status_code == 201, product.text
    assert float(product.json()["gst_rate"]) == 7.5
    assert product.json()["gst_selection_type"] == "custom"

    invoice = client.post("/invoices", headers=headers, json={
        "items": [{"product_id": product.json()["id"], "qty": 1}],
        "payment_method": "cash", "amount_paid": 107.50,
    })
    assert invoice.status_code == 201, invoice.text
    item = invoice.json()["items"][0]
    assert float(item["gst_rate"]) == 7.5
    assert item["gst_selection_type"] == "custom"
    assert item["selling_price_tax_mode"] == "inclusive"
    assert item["taxable_amount"] == 100
    assert item["tax_amount"] == 7.5
    assert item["total_amount"] == 107.5


def test_custom_gst_range_and_preset_rates_are_validated():
    client = TestClient(app)
    headers = login_as_admin(client)
    payload = {
        "name": "Invalid GST Item", "sku": "INVALID-GST-1", "category": "Fertilizer",
        "unit": "Bag", "selling_price": 10, "stock": 1,
    }
    too_high = client.post("/products", headers=headers, json={
        **payload, "gst_rate": 100.01, "gst_selection_type": "custom",
    })
    assert too_high.status_code == 422
    wrong_preset = client.post("/products", headers=headers, json={
        **payload, "sku": "INVALID-GST-2", "gst_rate": 7.5, "gst_selection_type": "preset",
    })
    assert wrong_preset.status_code == 422


def test_product_supplier_and_active_status_are_saved():
    client = TestClient(app)
    headers = login_as_admin(client)
    created = client.post("/products", headers=headers, json={
        "name": "Supplier Tracked Fertilizer", "sku": "SUP-1", "category": "Fertilizer",
        "unit": "Bag", "rate": 100, "stock": 10, "min_stock": 2,
        "supplier": "Adinath Wholesale",
    })
    assert created.status_code == 201
    assert created.json()["supplier"] == "Adinath Wholesale"
    listed = client.get("/products", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == created.json()["id"] for item in listed.json())

    updated = client.put(f"/products/{created.json()['id']}", headers=headers, json={
        "supplier": "New Agri Supplier", "is_active": False,
    })
    assert updated.status_code == 200
    assert updated.json()["supplier"] == "New Agri Supplier"
    assert updated.json()["is_active"] is False


def test_duplicate_line_items_cannot_bypass_stock_check():
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Fertilizer", "sku": "FERT-1", "category": "Fertilizer", "unit": "Bag",
        "rate": 10, "stock": 5, "min_stock": 1,
    }).json()

    invoice = client.post("/invoices", headers=headers, json={
        "items": [{"product_id": product["id"], "qty": 3}, {"product_id": product["id"], "qty": 3}],
        "payment_method": "cash", "amount_paid": 0,
    })
    assert invoice.status_code == 400
    assert "Insufficient stock" in invoice.json()["detail"]


def test_checkout_idempotency_key_prevents_duplicate_sale_after_retry():
    """A lost client response can safely be retried without deducting stock twice."""
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Retry-safe Seed", "sku": "SAFE-1", "category": "Fertilizer",
        "unit": "Bag", "rate": 100, "stock": 5, "min_stock": 1,
    }).json()
    checkout_headers = {**headers, "X-Idempotency-Key": "checkout-retry-001"}
    payload = {
        "items": [{"product_id": product["id"], "qty": 2}],
        "payment_method": "cash", "amount_paid": 210,
    }

    first = client.post("/invoices", headers=checkout_headers, json=payload)
    retry = client.post("/invoices", headers=checkout_headers, json=payload)

    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert client.get(f"/products/{product['id']}", headers=headers).json()["stock"] == 3


def test_checkout_idempotency_key_rejects_a_changed_bill():
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Changed Retry Seed", "sku": "CHANGED-1", "category": "Fertilizer",
        "unit": "Bag", "rate": 100, "stock": 5, "min_stock": 1,
    }).json()
    checkout_headers = {**headers, "X-Idempotency-Key": "checkout-changed-001"}
    original_payload = {
        "items": [{"product_id": product["id"], "qty": 2}],
        "payment_method": "cash", "amount_paid": 210,
    }

    first = client.post("/invoices", headers=checkout_headers, json=original_payload)
    changed_payload = {**original_payload, "items": [{"product_id": product["id"], "qty": 3}]}
    retry = client.post("/invoices", headers=checkout_headers, json=changed_payload)

    assert first.status_code == 201
    assert retry.status_code == 409
    assert client.get(f"/products/{product['id']}", headers=headers).json()["stock"] == 3


def test_svg_brand_asset_has_the_correct_content_type():
    response = TestClient(app).get("/icons/adinath-agri-logo.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_consecutive_invoices_continue_after_a_failed_attempt():
    """The invoice endpoint remains usable for Bill 1 -> Bill 2 -> Bill 3.

    A rejected checkout must roll back its transaction fully, so a POS client
    can immediately retry with a valid quantity without corrupting stock or
    the invoice sequence.
    """
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Consecutive Sale Product", "sku": "POS-3", "category": "Fertilizer",
        "unit": "Bag", "rate": 100, "stock": 10, "min_stock": 1,
    }).json()

    failed = client.post("/invoices", headers=headers, json={
        "items": [{"product_id": product["id"], "qty": 11}],
        "payment_method": "cash", "amount_paid": 0,
    })
    assert failed.status_code == 400

    invoice_numbers = []
    for quantity in (1, 2, 3):
        response = client.post("/invoices", headers=headers, json={
            "items": [{"product_id": product["id"], "qty": quantity}],
            "payment_method": "cash", "amount_paid": quantity * 105,
        })
        assert response.status_code == 201
        invoice_numbers.append(response.json()["invoice_no"])

    assert invoice_numbers == ["INV-000001", "INV-000002", "INV-000003"]
    assert client.get(f"/products/{product['id']}", headers=headers).json()["stock"] == 4


def test_invoice_caps_discount_and_payment_and_report_values_reconcile():
    client = TestClient(app)
    headers = login_as_admin(client)
    product = client.post("/products", headers=headers, json={
        "name": "Crop Guard", "sku": "CROP-1", "category": "Pesticides", "unit": "Bottle",
        "rate": 100, "stock": 5, "min_stock": 1,
    }).json()
    # A UI or API client cannot turn an oversized discount or payment into an
    # invalid stored total. The API and export data remain reconciled.
    invoice = client.post("/invoices", headers=headers, json={
        "items": [{"product_id": product["id"], "qty": 2}], "discount": 999,
        "payment_method": "cash", "amount_paid": 999,
    })
    assert invoice.status_code == 201
    data = invoice.json()
    assert data["subtotal"] == 200
    assert data["discount"] == 200
    assert data["tax"] == 0
    assert data["grand_total"] == 0
    assert data["amount_paid"] == 0
    assert data["balance_due"] == 0

    report = client.get("/reports/data?range=today", headers=headers)
    assert report.status_code == 200
    assert report.json()["sales"] == data["grand_total"]
    assert report.json()["rows"][0]["amount"] == data["grand_total"]


@pytest.mark.parametrize("period", ["today", "weekly", "monthly"])
def test_report_export_downloads_valid_pdf_for_every_period(period):
    client = TestClient(app)
    headers = login_as_admin(client)

    response = client.get(f"/reports/export?range={period}&format=pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert f'filename="Adinath_Agri_{period.title()}_Report.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-1.4")
    assert response.content.endswith(b"%%EOF")


def test_report_export_downloads_a_valid_excel_workbook():
    client = TestClient(app)
    response = client.get("/reports/export?range=monthly&format=xlsx", headers=login_as_admin(client))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(response.content)) as workbook:
        assert "xl/workbook.xml" in workbook.namelist()
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
