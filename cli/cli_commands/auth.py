#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth CLI - Authentication CLI commands.

🚪 Access - 💬 CLI - 认证 CLI

提供认证管理功能：添加、列出、删除、测试认证。
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".agent_z"
        self.secrets_file = self.config_dir / "secrets.json"
        self._secrets: Dict[str, str] = {}
        self._load_secrets()
    
    def _load_secrets(self) -> None:
        """加载密钥"""
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file, 'r', encoding='utf-8') as f:
                    self._secrets = json.load(f)
            except Exception:
                self._secrets = {}
    
    def _save_secrets(self) -> None:
        """保存密钥"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.secrets_file, 'w', encoding='utf-8') as f:
            json.dump(self._secrets, f, indent=2)
    
    def add_credential(self, provider: str, api_key: str) -> bool:
        """添加 API Key"""
        if not api_key or len(api_key) < 5:
            return False
        
        self._secrets[f"{provider}_api_key"] = api_key
        self._save_secrets()
        return True
    
    def get_credential(self, provider: str) -> Optional[str]:
        """获取 API Key"""
        return self._secrets.get(f"{provider}_api_key")
    
    def delete_credential(self, provider: str) -> bool:
        """删除 API Key"""
        key = f"{provider}_api_key"
        if key in self._secrets:
            del self._secrets[key]
            self._save_secrets()
            return True
        return False
    
    def list_credentials(self) -> List[Dict]:
        """列出所有已存储的认证"""
        from cli.cli_commands.providers import PROVIDERS
        
        credentials = []
        for key, value in self._secrets.items():
            if key.endswith("_api_key"):
                provider = key.replace("_api_key", "")
                
                # 检查是否是有效的 Provider
                is_valid = provider in PROVIDERS
                provider_name = PROVIDERS.get(provider, {}).get("display_name", provider)
                
                credentials.append({
                    "provider": provider,
                    "provider_name": provider_name,
                    "has_key": bool(value),
                    "key_preview": self._mask_key(value) if value else None,
                    "is_configured": is_valid,
                })
        
        return credentials
    
    def test_connection(self, provider: str) -> Dict:
        """测试 Provider 连接"""
        api_key = self.get_credential(provider)
        
        if not api_key:
            return {
                "status": "error",
                "message": "API key not configured",
                "provider": provider,
            }
        
        # 简单测试：检查 API key 格式
        if len(api_key) < 10:
            return {
                "status": "error",
                "message": "API key appears to be invalid",
                "provider": provider,
            }
        
        return {
            "status": "ok",
            "message": "API key format is valid",
            "provider": provider,
        }
    
    def _mask_key(self, key: str) -> str:
        """掩码 API Key"""
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + "*" * (len(key) - 8) + key[-4:]


# 全局实例
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """获取认证管理器实例"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def add_credential(provider: str, api_key: str) -> bool:
    """添加 API Key"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error
    
    print_header("🔐 添加认证")
    
    manager = get_auth_manager()
    
    if manager.add_credential(provider, api_key):
        print_success(f"API key added for {provider}")
        return True
    else:
        print_error("Failed to add API key")
        return False


def list_credentials() -> None:
    """列出所有认证"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header
    
    print_header("🔐 认证列表")
    
    manager = get_auth_manager()
    credentials = manager.list_credentials()
    
    if not credentials:
        print()
        print("  No credentials stored")
        print()
        return
    
    print()
    print("  Provider               Status               Key Preview")
    print("  " + "-" * 70)
    
    for cred in credentials:
        provider = cred["provider_name"][:20]
        
        if cred["has_key"]:
            status = f"● Configured"
            preview = cred["key_preview"] or "N/A"
        else:
            status = "○ Not Set"
            preview = "-"
        
        print(f"  {provider:20s} {status:20s} {preview}")
    
    print()


def delete_credential(provider: str) -> bool:
    """删除认证"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error
    
    print_header("🗑️ 删除认证")
    
    manager = get_auth_manager()
    
    if manager.delete_credential(provider):
        print_success(f"Credential deleted for {provider}")
        return True
    else:
        print_error(f"No credential found for {provider}")
        return False


def test_connection(provider: str) -> bool:
    """测试连接"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error
    
    print_header(f"🔍 测试连接: {provider}")
    
    manager = get_auth_manager()
    result = manager.test_connection(provider)
    
    print()
    
    if result["status"] == "ok":
        print_success(f"✓ {result.get('message', 'OK')}")
        return True
    else:
        print_error(f"✗ {result.get('message', 'Failed')}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Authentication management")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    add_parser = subparsers.add_parser("add", help="Add credential")
    add_parser.add_argument("provider", help="Provider ID")
    add_parser.add_argument("api_key", help="API Key")
    
    list_parser = subparsers.add_parser("list", help="List credentials")
    
    delete_parser = subparsers.add_parser("delete", help="Delete credential")
    delete_parser.add_argument("provider", help="Provider ID")
    
    test_parser = subparsers.add_parser("test", help="Test connection")
    test_parser.add_argument("provider", help="Provider ID")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_credential(args.provider, args.api_key)
    elif args.command == "list":
        list_credentials()
    elif args.command == "delete":
        delete_credential(args.provider)
    elif args.command == "test":
        test_connection(args.provider)
    else:
        list_credentials()