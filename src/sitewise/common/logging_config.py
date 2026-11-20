"""
Módulo logging_config.py: Configuración centralizada de logging para SiteWise.
Escribe simultáneamente en consola y en fichero rotativo.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_CONFIGURED = False
DEFAULT_LOG_FILE = "logs/sitewise.log"


def setup_logging(
    level: str | None = None,
    log_file: str | None = None,
    force: bool = False,
) -> None:
    """
    Configura el sistema de logging de la aplicación de forma idempotente.

    - Escribe siempre en consola (stdout) y en fichero rotativo (por defecto `logs/sitewise.log`).
    - Permite sobrescribir nivel con `SITEWISE_LOG_LEVEL` o `LOG_LEVEL`.
    - Permite sobrescribir ruta de fichero con `SITEWISE_LOG_FILE`.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    resolved_level_name = (
        level
        or os.getenv("LOG_LEVEL")
        or "INFO"
    ).upper()
    resolved_level = getattr(logging, resolved_level_name, logging.INFO)

    resolved_log_file = log_file or os.getenv("SITEWISE_LOG_FILE") or DEFAULT_LOG_FILE

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)

    # 2. Handler de fichero rotativo (máx. 5 MB por archivo, mantiene 3 respaldos)
    log_dir = os.path.dirname(resolved_log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        resolved_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(resolved_level)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)
    for old_handler in list(root_logger.handlers):
        old_handler.close()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reducir ruido de librerías de terceros
    for noisy_logger in (
        "httpx",
        "httpcore",
        "urllib3",
        "chromadb",
        "sentence_transformers",
        "huggingface_hub",
        "groq",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _CONFIGURED = True