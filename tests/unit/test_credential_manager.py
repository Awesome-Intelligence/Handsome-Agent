#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Credential Manager 模块测试
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.logging_manager import configure_logging
from tools.credential_manager import (
    CredentialManager,
    SecretMetadata,
    SecretCaptureResult,
    get_credential_manager,
    reset_credential_manager,
)


def test_credential_manager_basic():
    """测试凭证管理器基本功能"""
    # 重置单例
    reset_credential_manager()
    
    # 创建实例
    manager = CredentialManager()
    
    # 测试 home_dir 属性
    assert manager.home_dir == Path.home()
    
    # 测试自定义 home_dir
    custom_dir = Path("E:/test_creds")
    manager2 = CredentialManager(home_dir=str(custom_dir))
    assert manager2.home_dir == custom_dir
    
    print("✓ 基本初始化测试通过")


def test_capture_secret_already_set():
    """测试捕获已设置的环境变量"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 设置测试环境变量
    test_var = "TEST_API_KEY_12345"
    test_value = "sk-test-secret-key"
    os.environ[test_var] = test_value
    
    try:
        result = manager.capture_secret(
            env_var=test_var,
            prompt="请输入 API Key",
        )
        
        assert isinstance(result, SecretCaptureResult)
        assert result.success is True
        assert result.env_var == test_var
        assert result.value == test_value
        assert result.already_set is True
        print("✓ 捕获已设置密钥测试通过")
    finally:
        # 清理
        if test_var in os.environ:
            del os.environ[test_var]


def test_capture_secret_not_set():
    """测试捕获未设置的环境变量"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 确保环境变量不存在
    test_var = "TEST_API_KEY_NOT_SET_67890"
    if test_var in os.environ:
        del os.environ[test_var]
    
    result = manager.capture_secret(
        env_var=test_var,
        prompt="请输入 API Key",
    )
    
    assert isinstance(result, SecretCaptureResult)
    assert result.success is False
    assert result.env_var == test_var
    assert result.value is None
    assert result.already_set is False
    assert "请输入 API Key" in result.message
    
    print("✓ 捕获未设置密钥测试通过")


def test_validate_env_var():
    """测试环境变量验证"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 测试已设置的变量
    test_var = "TEST_VALIDATE_VAR"
    test_value = "test_value"
    os.environ[test_var] = test_value
    
    try:
        is_set, value = manager.validate_env_var(test_var)
        assert is_set is True
        assert value == test_value
        print("✓ 环境变量验证（已设置）测试通过")
    finally:
        if test_var in os.environ:
            del os.environ[test_var]
    
    # 测试未设置的变量
    is_set, value = manager.validate_env_var("NON_EXIST_VAR_123456")
    assert is_set is False
    assert value is None
    print("✓ 环境变量验证（未设置）测试通过")


def test_required_env_vars():
    """测试必需环境变量管理"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 添加必需变量
    manager.add_required_env_var("REQUIRED_VAR_1")
    manager.add_required_env_var("REQUIRED_VAR_2")
    
    # 验证缺失列表
    all_set, missing = manager.validate_required_env_vars()
    assert all_set is False
    assert "REQUIRED_VAR_1" in missing
    assert "REQUIRED_VAR_2" in missing
    print("✓ 必需环境变量验证（缺失）测试通过")
    
    # 设置变量
    os.environ["REQUIRED_VAR_1"] = "value1"
    os.environ["REQUIRED_VAR_2"] = "value2"
    
    try:
        all_set, missing = manager.validate_required_env_vars()
        assert all_set is True
        assert len(missing) == 0
        print("✓ 必需环境变量验证（已设置）测试通过")
    finally:
        if "REQUIRED_VAR_1" in os.environ:
            del os.environ["REQUIRED_VAR_1"]
        if "REQUIRED_VAR_2" in os.environ:
            del os.environ["REQUIRED_VAR_2"]
    
    # 移除变量
    manager.remove_required_env_var("REQUIRED_VAR_1")
    assert "REQUIRED_VAR_1" not in manager._required_env_vars
    print("✓ 移除必需环境变量测试通过")


def test_register_credential_file():
    """测试凭证文件注册"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 测试拒绝绝对路径
    success, missing = manager.register_credential_file("/etc/secrets/api_key.json")
    assert success is False
    assert len(missing) > 0
    print("✓ 拒绝绝对路径测试通过")
    
    # 测试路径遍历攻击
    success, missing = manager.register_credential_file("../etc/passwd")
    assert success is False
    print("✓ 拒绝路径遍历测试通过")
    
    # 测试不存在的文件
    success, missing = manager.register_credential_file("nonexistent_file.json")
    assert success is False
    assert "nonexistent_file.json" in missing
    print("✓ 不存在文件测试通过")
    
    # 测试创建真实文件
    test_file = manager.home_dir / "test_credential_file.txt"
    test_file.write_text("test content")
    
    try:
        # 使用相对路径（相对于 home_dir）
        success, missing = manager.register_credential_file("test_credential_file.txt")
        assert success is True
        assert len(missing) == 0
        
        registered = manager.get_registered_files()
        assert len(registered) > 0
        print("✓ 有效凭证文件注册测试通过")
    finally:
        if test_file.exists():
            test_file.unlink()
    
    # 清理
    manager.clear_registered_files()
    assert len(manager.get_registered_files()) == 0
    print("✓ 清除已注册文件测试通过")


def test_register_credential_files_batch():
    """测试批量注册凭证文件"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 创建测试文件
    test_files = [
        manager.home_dir / "test_file1.txt",
        manager.home_dir / "test_file2.txt",
    ]
    
    for f in test_files:
        f.write_text("test")
    
    try:
        paths = ["test_file1.txt", "test_file2.txt", "nonexistent.txt"]
        success, missing = manager.register_credential_files(paths)
        
        assert success is False
        assert "test_file1.txt" not in missing
        assert "test_file2.txt" not in missing
        assert "nonexistent.txt" in missing
        print("✓ 批量注册凭证文件测试通过")
    finally:
        for f in test_files:
            if f.exists():
                f.unlink()


def test_get_credential_file_mounts():
    """测试获取凭证文件挂载信息"""
    reset_credential_manager()
    manager = get_credential_manager()
    
    # 创建测试文件
    test_file = manager.home_dir / "mount_test.txt"
    test_file.write_text("mount content")
    
    try:
        manager.register_credential_file("mount_test.txt")
        mounts = manager.get_credential_file_mounts()
        
        assert len(mounts) > 0
        assert "host_path" in mounts[0]
        assert "container_path" in mounts[0]
        assert "mount_test.txt" in mounts[0]["host_path"]
        print("✓ 获取凭证文件挂载信息测试通过")
    finally:
        if test_file.exists():
            test_file.unlink()


def test_singleton_pattern():
    """测试单例模式"""
    reset_credential_manager()
    
    manager1 = get_credential_manager()
    manager2 = get_credential_manager()
    
    assert manager1 is manager2
    print("✓ 单例模式测试通过")
    
    reset_credential_manager()
    manager3 = get_credential_manager()
    assert manager3 is not manager1
    print("✓ 重置单例测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("开始运行 CredentialManager 测试...")
    print("=" * 50)
    
    # 配置日志（只显示关键信息）
    configure_logging({"log_level": "brief"})
    
    test_credential_manager_basic()
    test_capture_secret_already_set()
    test_capture_secret_not_set()
    test_validate_env_var()
    test_required_env_vars()
    test_register_credential_file()
    test_register_credential_files_batch()
    test_get_credential_file_mounts()
    test_singleton_pattern()
    
    print("=" * 50)
    print("所有测试通过！")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
