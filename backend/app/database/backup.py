"""Automated database backup and restore functionality."""
import os
import shutil
import sqlite3
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from .connection import DB_PATH

logger = logging.getLogger(__name__)

# Backup directory relative to database
BACKUP_DIR = Path(DB_PATH).parent / "backups"
MAX_BACKUPS = 30  # Keep last 30 backups


def ensure_backup_directory() -> Path:
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def create_backup(reason: str = "manual") -> Optional[Path]:
    """
    Create a backup of the database using SQLite's backup API.
    
    This is safer than file copy as it handles active connections properly.
    Returns the backup file path or None if backup failed.
    """
    try:
        backup_dir = ensure_backup_directory()
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_name = f"adinath_backup_{timestamp}_{reason}.db"
        backup_path = backup_dir / backup_name
        
        # Use SQLite's backup API for safe backup of active database
        source = sqlite3.connect(DB_PATH)
        dest = sqlite3.connect(str(backup_path))
        
        with dest:
            source.backup(dest, pages=1, progress=_backup_progress)
        
        source.close()
        dest.close()
        
        # Verify backup integrity
        if verify_backup(backup_path):
            logger.info(f"Database backup created: {backup_path}")
            cleanup_old_backups()
            return backup_path
        else:
            logger.error(f"Backup verification failed: {backup_path}")
            backup_path.unlink(missing_ok=True)
            return None
            
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return None


def _backup_progress(status, remaining, total):
    """Optional progress callback for large databases."""
    if remaining == 0:
        logger.debug(f"Backup complete: {total} pages copied")


def verify_backup(backup_path: Path) -> bool:
    """Verify backup integrity by running SQLite integrity check."""
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == "ok"
    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        return False


def restore_backup(backup_path: Path) -> bool:
    """
    Restore database from backup.
    WARNING: This will overwrite the current database!
    """
    try:
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        if not verify_backup(backup_path):
            logger.error(f"Cannot restore corrupted backup: {backup_path}")
            return False
        
        # Create safety backup of current database before restore
        safety_backup = Path(DB_PATH).parent / f"pre_restore_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB_PATH, safety_backup)
        logger.info(f"Safety backup created: {safety_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, DB_PATH)
        logger.info(f"Database restored from: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        return False


def cleanup_old_backups():
    """Remove old backups, keeping only the most recent MAX_BACKUPS."""
    try:
        backup_dir = ensure_backup_directory()
        backups = sorted(backup_dir.glob("adinath_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for old_backup in backups[MAX_BACKUPS:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup.name}")
            
    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {e}")


def list_backups() -> list[dict]:
    """List all available backups with metadata."""
    try:
        backup_dir = ensure_backup_directory()
        backups = []
        
        for backup_file in sorted(backup_dir.glob("adinath_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                "valid": verify_backup(backup_file)
            })
        
        return backups
        
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return []


def auto_backup_on_startup() -> Optional[Path]:
    """Create automatic backup on application startup."""
    return create_backup(reason="startup")


def auto_backup_on_shutdown() -> Optional[Path]:
    """Create automatic backup on application shutdown."""
    return create_backup(reason="shutdown")
