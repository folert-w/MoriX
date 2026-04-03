import logging
from logging.handlers import RotatingFileHandler
from .config import LOGS_DIR

_LOGGER_NAME = "MoriX"

def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # уже настроен
        return logger

    logger.setLevel(logging.INFO)

    log_file = LOGS_DIR / "app.log"
    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    fmt = logging.Formatter(
        fmt="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    # Параллельно в консоль
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    return logger
