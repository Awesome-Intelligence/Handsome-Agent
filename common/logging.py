"""Logging configuration"""
import logging
import sys
from typing import Optional
from common.logging_manager import (
    get_system_logger,
    suppress_library_logs,
    set_module_log_level,
)


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(level=level, format=format_string, handlers=handlers)

    suppress_library_logs()

    for lib, lib_level in (
        ("uvicorn", logging.WARNING),
        ("fastapi", logging.WARNING),
        ("markdown_it", logging.WARNING),
        ("brain_trajectory", logging.INFO),
        ("brain_curator", logging.INFO),
        ("brain.agent", logging.INFO),
        ("brain.service", logging.INFO),
    ):
        set_module_log_level(lib, lib_level)


def get_logger(name: str):
    return get_system_logger(name)
