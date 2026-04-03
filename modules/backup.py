from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil

from .config import DATA_DIR, DB_PATH
from .logger import get_logger

log = get_logger("MoriX.backup")

BACKUP_DIR = DATA_DIR / "backups"


def _ensure_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_backup() -> Path:
    """
    Делает копию базы MoriX в папку backups/.
    Имя вида: morix_YYYYMMDD_HHMMSS.db
    """
    _ensure_dir()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"morix_{ts}.db"

    if not DB_PATH.exists():
        raise FileNotFoundError(f"База не найдена: {DB_PATH}")

    shutil.copy2(DB_PATH, target)
    log.info(f"Backup created: {target}")
    return target


def list_backups(limit: int = 20) -> list[Path]:
    """
    Возвращает последние доступные бэкапы.
    """
    _ensure_dir()
    files = sorted(BACKUP_DIR.glob("morix_*.db"), reverse=True)
    return files[:limit]


def restore_backup(src: Path) -> None:
    """
    Восстановление базы из выбранного файла.
    Пока можно не использовать в GUI, но оставить как возможность.
    """
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(f"Файл бэкапа не найден: {src}")

    _ensure_dir()
    shutil.copy2(src, DB_PATH)
    log.info(f"Backup restored from: {src}")
