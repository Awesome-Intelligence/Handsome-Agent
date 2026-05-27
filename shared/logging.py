"""日志配置"""
import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    
    logging.basicConfig(level=level, format=format_string, handlers=handlers)
    
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("brain_trajectory").setLevel(logging.INFO)
    logging.getLogger("brain_curator").setLevel(logging.INFO)
    logging.getLogger("brain.agent").setLevel(logging.INFO)
    logging.getLogger("brain.service").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
