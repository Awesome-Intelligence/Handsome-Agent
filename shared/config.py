"""配置管理"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    app_name: str = "HandsomeAgent"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务配置
    brain_service_host: str = "0.0.0.0"
    brain_service_port: int = 8001
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    executor_port: int = 8002
    
    # 数据库配置
    db_path: str = ".handsome_agent.db"
    
    # 安全配置
    api_key: Optional[str] = None
    allowed_origins: list[str] = ["*"]
    
    # 技能目录
    skills_dir: str = "~/.skills"
    
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