"""配置管理"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


def get_default_handsome_home() -> Path:
    """Get the default HANDSOME_HOME directory."""
    home = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    if home:
        return Path(home) / ".handsome_agent"
    return Path(".") / ".handsome_agent"


HANDSOME_HOME = Path(os.environ.get("HANDSOME_HOME", get_default_handsome_home()))


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    app_name: str = "HandsomeAgent"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Workspace 配置
    handsome_home: str = str(HANDSOME_HOME)
    
    # 服务配置
    brain_service_host: str = "0.0.0.0"
    brain_service_port: int = 8001
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    executor_port: int = 8002
    
    # 数据库配置
    db_path: str = str(HANDSOME_HOME / "handsome_agent.db")
    
    # 安全配置
    api_key: Optional[str] = None
    allowed_origins: list[str] = ["*"]
    
    # 技能目录
    skills_dir: str = str(HANDSOME_HOME / "skills")
    
    # Agent 配置
    max_iterations: int = 10
    timeout_seconds: float = 60.0
    
    # 执行器配置
    allowed_commands: list[str] = ["git", "npm", "pip", "python", "mkdir", "ls", "cat", "echo"]
    blocked_patterns: list[str] = ["rm -rf /", "curl | sh"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置（单例）"""
    return Settings()


def get_sessions_dir() -> Path:
    """获取会话保存目录"""
    settings = get_settings()
    return Path(settings.handsome_home) / "sessions"


def get_memories_dir() -> Path:
    """获取记忆保存目录"""
    settings = get_settings()
    return Path(settings.handsome_home) / "memories"


def get_logs_dir() -> Path:
    """获取日志保存目录"""
    settings = get_settings()
    return Path(settings.handsome_home) / "logs"


def get_config_dir() -> Path:
    """获取配置保存目录"""
    settings = get_settings()
    return Path(settings.handsome_home) / "config"


def ensure_workspace_dirs():
    """确保工作区目录存在"""
    for dir_path in [
        Path(get_settings().handsome_home),
        get_sessions_dir(),
        get_memories_dir(),
        get_logs_dir(),
        get_config_dir(),
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)