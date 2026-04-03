from pathlib import Path

# ---- Colors
COLORS = {
    "ORANGE": "#FF7A00",
    "BLACK": "#000000",
    "WHITE": "#FFFFFF",
    "DARK_GRAY": "#2B2B2B",
}

# ---- Flags
FLAGS = {
    "prefer_local": True,   # Сначала локально
    "allow_cloud": False,   # Оффлайн
}

# ---- Paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "morix.db"

# Создаём директории при импорте
for d in (DATA_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---- Confirmation policy
CONFIRMATION_POLICY = {
    "require_confirmation": True,
    "destructive_keywords": ["delete", "drop", "format", "wipe"],
}

# ---- Security
SECURITY = {
    "offline_only": not FLAGS.get("allow_cloud", False),
    "network_allowed": FLAGS.get("allow_cloud", False),
    "allowed_scopes": [
        "core.echo",
    ],
    "denied_scopes": [
    ],
    "require_confirmation_scopes": [
        "fs.delete",
        "db.drop",
        "system.exec",
    ],
    "fs_read_roots": [],
    "fs_write_roots": [str(DATA_DIR)],
    "audit_enabled": True,
    "rate_limit": {"per_minute": 120},
    "max_output_chars": 20000,
}
