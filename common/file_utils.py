"""文件系统工具模块"""

import logging
import os
import tempfile
from pathlib import Path

from common.logging_manager import get_execution_logger

logger = get_execution_logger("file_utils")


def atomic_replace(tmp_path: Path, target_path: Path) -> None:
    """原子化替换文件"""
    try:
        if os.name == 'nt':
            os.replace(str(tmp_path), str(target_path))
        else:
            os.rename(str(tmp_path), str(target_path))
    except Exception as e:
        logger.error(f"Atomic replace failed: {e}")
        raise


def atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子化写入文本"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(file_path.parent),
        prefix=f".{file_path.name}.tmp.",
        suffix=""
    )
    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
        atomic_replace(Path(tmp_path), file_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise
