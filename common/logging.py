"""Logging configuration"""
import logging
import sys
from typing import Optional
from common.logging_manager import get_system_logger


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    
    logging.basicConfig(level=level, format=format_string, handlers=handlers)
    
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("markdown_it").setLevel(logging.WARNING)
    logging.getLogger("brain_trajectory").setLevel(logging.INFO)
    logging.getLogger("brain_curator").setLevel(logging.INFO)
    logging.getLogger("brain.agent").setLevel(logging.INFO)
    logging.getLogger("brain.service").setLevel(logging.INFO)


def get_logger(name: str):
    return get_system_logger(name)
