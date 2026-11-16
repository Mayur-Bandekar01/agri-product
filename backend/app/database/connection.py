import os
import sqlite3
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Resolve relative to backend so the app and desktop package use the same DB.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.abspath(os.getenv("ADINATH_DB_PATH", os.path.join(BACKEND_DIR, "adinath.db")))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
)

# Enable foreign key constraints for data integrity
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys and optimize SQLite for better performance."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_integrity() -> tuple[bool, str]:
    """
    Run SQLite integrity check on the database.
    Returns (is_valid, message).
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == "ok":
            return True, "Database integrity check passed"
        else:
            return False, f"Database integrity check failed: {result}"
            
    except Exception as e:
        return False, f"Database integrity check error: {e}"


def optimize_database():
    """Run VACUUM and ANALYZE to optimize database performance."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        conn.close()
        logger.info("Database optimized successfully")
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")

