#!/usr/bin/env python3
"""
代码审查检查脚本 - 检测硬编码违规
🚪 Access - 🔧 System - 代码质量检查

此脚本用于在代码提交前检查是否违反硬编码规则。
运行方式: python scripts/pre_commit_check.py
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# 硬编码检测模式
HARDCODE_PATTERNS = {
    # 意图理解硬编码
    "intent_hardcode": [
        (r'if\s+["\'].+["\']\s+in\s+\w+', "检测到可能的意图硬编码关键词判断"),
        (r'if\s+\w+\s+in\s+["\'].+["\']', "检测到可能的意图硬编码关键词判断"),
        (r're\.match\(["\'].+["\']', "检测到可能的意图硬编码正则匹配"),
        (r'\.startswith\(["\']', "检测到可能的硬编码前缀判断"),
        (r'\.endswith\(["\']', "检测到可能的硬编码后缀判断"),
        (r'use_react\s*\(\s*\)', "检测到 ReAct 模式硬编码调用"),
    ],
    # 敏感信息硬编码
    "secret_hardcode": [
        (r'password\s*=\s*["\'][^"\'${}]+["\']', "检测到密码硬编码"),
        (r'api_key\s*=\s*["\'][^"\'${}]+["\']', "检测到 API Key 硬编码"),
        (r'secret\s*=\s*["\'][^"\'${}]+["\']', "检测到 Secret 硬编码"),
        (r'token\s*=\s*["\'][^"\'${}]{10,}["\']', "检测到 Token 硬编码"),
    ],
    # 路径硬编码
    "path_hardcode": [
        (r'["\'][^"\']*[/\\\\]+[^"\']+["\'].*replace', "检测到可能的路径分隔符硬编码"),
        (r'["\']\\[^"\'\\]+["\']', "检测到 Windows 路径硬编码"),
    ],
}

# 需要忽略的目录
IGNORE_DIRS = {
    "tests", ".git", "__pycache__", ".venv", "venv",
    "node_modules", ".pytest_cache", ".ruff_cache"
}

# 需要忽略的文件
IGNORE_FILES = {
    "pre_commit_check.py", "test_", ".pyi"
}


def should_ignore(path: Path) -> bool:
    """检查是否应该忽略该路径"""
    for ignore_dir in IGNORE_DIRS:
        if ignore_dir in path.parts:
            return True
    for ignore_file in IGNORE_FILES:
        if path.name.startswith(ignore_file):
            return True
    return False


def check_file(filepath: Path) -> List[Tuple[str, int, str]]:
    """
    检查单个文件的硬编码
    返回: List[(违规类型, 行号, 违规内容)]
    """
    violations = []

    if not filepath.suffix == '.py':
        return violations

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return violations

    for line_no, line in enumerate(lines, 1):
        # 跳过注释
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for violation_type, patterns in HARDCODE_PATTERNS.items():
            for pattern, message in patterns:
                if re.search(pattern, line):
                    # 排除测试中的模拟数据
                    if 'test' in filepath.name.lower() and ('mock' in line or 'fixture' in line):
                        continue
                    # 排除常量定义（正常用途）
                    if 'CONSTANT' in line or 'DEFAULT' in line or 'CONFIG' in line:
                        continue
                    violations.append((violation_type, line_no, message))

    return violations


def scan_directory(root_path: Path) -> List[Tuple[Path, str, int, str]]:
    """
    扫描目录下的所有 Python 文件
    返回: List[(文件路径, 违规类型, 行号, 违规内容)]
    """
    all_violations = []

    for py_file in root_path.rglob("*.py"):
        if should_ignore(py_file):
            continue

        violations = check_file(py_file)
        for violation_type, line_no, message in violations:
            all_violations.append((py_file, violation_type, line_no, message))

    return all_violations


def print_report(violations: List[Tuple[Path, str, int, str]]):
    """打印检查报告"""
    if not violations:
        print("\n✅ 未检测到硬编码违规！代码审查通过。")
        return True

    print("\n❌ 检测到以下硬编码违规:\n")

    # 按文件分组
    by_file = {}
    for filepath, violation_type, line_no, message in violations:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append((violation_type, line_no, message))

    for filepath, file_violations in by_file.items():
        print(f"📄 {filepath}")
        for violation_type, line_no, message in file_violations:
            type_emoji = {
                "intent_hardcode": "🧠",
                "secret_hardcode": "🔐",
                "path_hardcode": "📁"
            }.get(violation_type, "❓")
            print(f"   {type_emoji} 第 {line_no} 行: {message}")
        print()

    print(f"\n总计: {len(violations)} 处违规")
    print("\n请修复上述问题后重新提交。参考 rule.md 中的 2.0 强制约束声明")
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("🛡️  Handsome Agent 代码审查检查")
    print("=" * 60)
    print("\n检查是否违反硬编码规则...\n")

    # 检查当前目录
    root = Path(__file__).parent.parent if '__file__' in dir() else Path.cwd()

    violations = scan_directory(root)
    success = print_report(violations)

    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()