#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工作区配置
"""
import os
import tempfile
from shared.config import get_settings, get_sessions_dir, get_memories_dir, get_logs_dir, get_config_dir, ensure_workspace_dirs, HANDSOME_HOME
from core.session import SessionManager, Session


def test_workspace_config():
    """测试工作区配置"""
    print("=== 测试工作区配置 ===")
    
    settings = get_settings()
    print(f"Handsome Home: {settings.handsome_home}")
    print(f"Sessions Dir: {get_sessions_dir()}")
    print(f"Memories Dir: {get_memories_dir()}")
    print(f"Logs Dir: {get_logs_dir()}")
    print(f"Config Dir: {get_config_dir()}")
    
    print("\n确保工作区目录存在...")
    ensure_workspace_dirs()
    
    print("\n=== 测试 SessionManager ===")
    manager = SessionManager()
    print(f"SessionManager 创建成功")
    print(f"历史路径: {manager.config.history_path}")
    
    print("\n=== 创建会话 ===")
    session = manager.create_session("test_workspace_session")
    print(f"会话创建成功: {session.session_id}")
    
    session.add_message("user", "你好，这是一个测试消息")
    session.add_message("assistant", "你好！这是我的回复")
    
    print(f"消息数量: {len(session.messages)}")
    session.end()
    
    print("\n=== 测试完成 ===")
    print(f"会话将保存在: {settings.handsome_home}")


def test_env_var():
    """测试环境变量配置"""
    print("\n\n=== 测试环境变量配置 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        original_env = os.environ.get("HANDSOME_HOME")
        try:
            os.environ["HANDSOME_HOME"] = temp_dir
            
            # 重新导入配置模块
            import importlib
            import shared.config
            importlib.reload(shared.config)
            
            from shared.config import get_settings, get_sessions_dir, HANDSOME_HOME
            
            print(f"环境变量 HANDSOME_HOME: {os.environ['HANDSOME_HOME']}")
            print(f"配置 HANDSOME_HOME: {HANDSOME_HOME}")
            print(f"Sessions Dir: {get_sessions_dir()}")
            
        finally:
            if original_env:
                os.environ["HANDSOME_HOME"] = original_env
            else:
                os.environ.pop("HANDSOME_HOME", None)


if __name__ == "__main__":
    test_workspace_config()
    test_env_var()
