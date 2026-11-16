"""SQLite schema setup and forward-only, versioned migrations."""
import logging

from .. import models  # Register ORM tables before migration metadata is inspected.
from .connection import Base, engine

logger = logging.getLogger(__name__)

CATALOG_MIGRATION = "001_actual_product_catalog"
INVENTORY_LEDGER_MIGRATION = "003_inventory_import_ledger"
EXPLICIT_SELLING_PRICE_MIGRATION = "004_explicit_selling_price"
PRODUCT_GST_INVOICE_SNAPSHOT_MIGRATION = "005_product_gst_invoice_snapshots"
FOREIGN_KEYS_ENABLED_MIGRATION = "006_foreign_keys_enabled"
RECEIPT_NUMBERING_MIGRATION = "007_receipt_numbering"
HSN_AND_DISCOUNT_MIGRATION = "008_hsn_and_discount_fields"


def migrate_schema() -> None:
    """Create missing tables and apply idempotent upgrades to existing DBs."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        # Foreign keys are now enabled at connection level (see connection.py)
        # This migration just records that the change was applied
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS app_migrations (version VARCHAR(120) PRIMARY KEY)"
        )
        
        product_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(products)")}
        if "expires_on" not in product_columns:
            connection.exec_driver_sql("ALTER TABLE products ADD COLUMN expires_on DATETIME")
        if "supplier" not in product_columns:
            connection.exec_driver_sql("ALTER TABLE products ADD COLUMN supplier VARCHAR(160)")
        
        product_upgrades = {
            "pack_size": "VARCHAR(80)",
            "selling_price": "NUMERIC(12, 2)",
            "purchase_price_including_gst": "NUMERIC(12, 2)",
            "purchase_price_excluding_gst": "NUMERIC(12, 2)",
            "purchase_gst_component": "NUMERIC(12, 2)",
            "gst_rate": "NUMERIC(5, 2)",
            "gst_selection_type": "VARCHAR(12) NOT NULL DEFAULT 'preset'",
            "selling_price_tax_mode": "VARCHAR(20) NOT NULL DEFAULT 'exclusive'",
            "initial_quantity": "NUMERIC(12, 2)",
            "source_reference": "VARCHAR(200)",
            "hsn_code": "VARCHAR(12)",
            "discount_percentage": "NUMERIC(5, 2) DEFAULT 0",
        }
        for column, sql_type in product_upgrades.items():
            if column not in product_columns:
                connection.exec_driver_sql(f"ALTER TABLE products ADD COLUMN {column} {sql_type}")
        
        connection.exec_driver_sql("UPDATE products SET selling_price = rate WHERE selling_price IS NULL")
        
        item_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(invoice_items)")}
        item_upgrades = {
            "gst_rate": "NUMERIC(5, 2)",
            "gst_selection_type": "VARCHAR(12)",
            "selling_price_tax_mode": "VARCHAR(20)",
            "taxable_amount": "NUMERIC(12, 2)",
            "tax_amount": "NUMERIC(12, 2)",
            "total_amount": "NUMERIC(12, 2)",
        }
        for column, sql_type in item_upgrades.items():
            if column not in item_columns:
                connection.exec_driver_sql(f"ALTER TABLE invoice_items ADD COLUMN {column} {sql_type}")

        # Rebuild only legacy databases whose rate column disallows NULL
        rate_column = next(
            (row for row in connection.exec_driver_sql("PRAGMA table_info(products)") if row[1] == "rate"),
            None,
        )
        if rate_column and rate_column[3]:
            logger.info("Rebuilding products table to allow NULL rates...")
            connection.exec_driver_sql("ALTER TABLE products RENAME TO products_legacy_rate")
            connection.exec_driver_sql("""CREATE TABLE products (
                id INTEGER NOT NULL PRIMARY KEY, name VARCHAR NOT NULL, sku VARCHAR NOT NULL,
                category VARCHAR NOT NULL, unit VARCHAR NOT NULL, rate NUMERIC(12, 2),
                stock NUMERIC(12, 2), min_stock NUMERIC(12, 2), expires_on DATETIME,
                supplier VARCHAR(160), is_active BOOLEAN)""")
            connection.exec_driver_sql("""INSERT INTO products
                (id,name,sku,category,unit,rate,stock,min_stock,expires_on,supplier,is_active)
                SELECT id,name,sku,category,unit,rate,stock,min_stock,expires_on,supplier,is_active
                FROM products_legacy_rate""")
            connection.exec_driver_sql("DROP TABLE products_legacy_rate")
            connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_products_sku ON products (sku)")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_products_id ON products (id)")

        invoice_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(invoices)")}
        if "client_request_id" not in invoice_columns:
            connection.exec_driver_sql("ALTER TABLE invoices ADD COLUMN client_request_id VARCHAR(64)")
        
        # Create indexes for better query performance
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_invoices_client_request_id "
            "ON invoices (client_request_id)"
        )
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_invoices_date ON invoices (date)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_invoices_farmer_id ON invoices (farmer_id)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_invoices_balance_due ON invoices (balance_due)")
        
        # Composite indexes for common query patterns
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_invoices_farmer_date ON invoices (farmer_id, date)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_invoice_items_product ON invoice_items (product_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_stock_movements_product_date ON stock_movements (product_id, movement_date)"
        )
        
        # Add receipt numbering to payments
        payment_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(payments)")}
        if "receipt_no" not in payment_columns:
            logger.info("Adding receipt_no column to payments table...")
            connection.exec_driver_sql("ALTER TABLE payments ADD COLUMN receipt_no VARCHAR(40)")
            
            # Backfill existing payments with generated receipt numbers
            existing_payments = connection.exec_driver_sql("SELECT id FROM payments ORDER BY id").fetchall()
            for payment_row in existing_payments:
                payment_id = payment_row[0]
                receipt_no = f"REC-{payment_id:06d}"
                connection.exec_driver_sql(
                    "UPDATE payments SET receipt_no = ? WHERE id = ?",
                    (receipt_no, payment_id)
                )
            
            # Make receipt_no NOT NULL after backfill
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_receipt_no ON payments (receipt_no)"
            )
            logger.info(f"Backfilled {len(existing_payments)} receipt numbers")
        
        # Record migrations
        for migration in [
            INVENTORY_LEDGER_MIGRATION,
            EXPLICIT_SELLING_PRICE_MIGRATION,
            PRODUCT_GST_INVOICE_SNAPSHOT_MIGRATION,
            FOREIGN_KEYS_ENABLED_MIGRATION,
            RECEIPT_NUMBERING_MIGRATION,
            HSN_AND_DISCOUNT_MIGRATION,
        ]:
            connection.exec_driver_sql(
                "INSERT OR IGNORE INTO app_migrations(version) VALUES (?)",
                (migration,),
            )
        
        # Create index for HSN code lookups
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_products_hsn_code ON products (hsn_code)"
        )
        
        logger.info("Database schema migrations completed successfully")


def seed_products() -> None:
    """Retire the legacy hardcoded catalog seed without touching product data.

    Product records are now managed explicitly through database-backed product
    workflows and versioned imports. Older versions of this function rewrote
    names/prices and could delete or deactivate records at first startup.
    """
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS app_migrations (version VARCHAR(120) PRIMARY KEY)"
        )
        connection.exec_driver_sql(
            "INSERT OR IGNORE INTO app_migrations(version) VALUES (?)",
            ("002_retire_mutating_catalog_seed",),
        )


def initialize_database() -> None:
    """Run schema migrations followed by the repeatable catalog seed."""
    logger.info("Initializing database...")
    migrate_schema()
    seed_products()
    logger.info("Database initialization complete")

