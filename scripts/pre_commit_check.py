#!/usr/bin/env python3
"""
代码审查检查脚本 - 检测硬编码违规
🚪 Access - 🔧 System - 代码质量检查

此脚本用于在代码提交前检查是否违反硬编码规则。
运行方式: python scripts/pre_commit_check.py

优化版：减少误报
- 排除 ANSI 转义序列 (\033)
- 排除正则表达式中的反斜杠
- 排除注释中的内容
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# 硬编码检测模式（优化后）
HARDCODE_PATTERNS = {
    # 意图理解硬编码 - 只检测业务意图判断
    "intent_hardcode": [
        # 检测用户输入/命令的关键词判断（如 "做个", "帮我" 等）
        (r'\bif\s+["\'"][\u4e00-\u9fa5]{2,10}["\']\s+in\s+\w+', 
         "检测到可能的用户意图硬编码关键词判断"),
        # 检测业务逻辑中的硬编码命令词
        (r'if\s+["\'"](skill|task|do|make|run|exec)["\']\s+in\s+\w+', 
         "检测到可能的业务命令硬编码"),
    ],
    # 敏感信息硬编码
    "secret_hardcode": [
        # 等号赋值（排除环境变量、正则等）
        (r'(?<![\w_])(password|api_key|apikey|secret|token)\s*=\s*["\'][^"\'${}]{8,}["\'](?!\s*%|\s*\.|\s*\+)', 
         "检测到敏感信息硬编码"),
    ],
}

# Windows 路径硬编码模式（更严格 - 只检测真正的路径字符串）
WINDOWS_PATH_PATTERNS = [
    # 匹配 C:\、D:\ 等盘符开头的绝对路径
    (r'(?<!["\'])\b[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+[/\\])*[^\\/:*?"<>|\r\n]*', 
     "Windows 绝对路径"),
]

# 需要忽略的目录
IGNORE_DIRS = {
    "tests", ".git", "__pycache__", ".venv", "venv",
    "node_modules", ".pytest_cache", ".ruff_cache"
}

# 需要忽略的文件
IGNORE_FILES = {
    "pre_commit_check.py", "test_", ".pyi"
}

# 排除模式（减少误报）
EXCLUDE_PATTERNS = [
    r'\\033\[',      # ANSI 转义序列
    r'\\x[0-9a-fA-F]{2}',  # 十六进制转义
    r'\\\\[a-z]',    # 转义字母（正则中的 \n, \t 等）
    r'\[\\',         # 字符类中的反斜杠
    r're\.compile\(',  # 正则编译
    r'r["\']',       # 原始字符串前缀
    r'default=.*\\\\',  # 默认值中的反斜杠
]


def should_ignore(path: Path) -> bool:
    """检查是否应该忽略该路径"""
    for ignore_dir in IGNORE_DIRS:
        if ignore_dir in path.parts:
            return True
    for ignore_file in IGNORE_FILES:
        if path.name.startswith(ignore_file):
            return True
    return False


def is_excluded_line(line: str) -> bool:
    """检查该行是否应该被排除"""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def check_file(filepath: Path) -> List[Tuple[str, int, str, str]]:
    """
    检查单个文件的硬编码
    返回: List[(违规类型, 行号, 违规内容, 行内容)]
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
        stripped = line.strip()
        
        # 跳过注释行
        if stripped.startswith('#'):
            continue
        
        # 跳过被排除的行
        if is_excluded_line(line):
            continue

        # 检查意图硬编码
        for pattern, message in HARDCODE_PATTERNS.get("intent_hardcode", []):
            if re.search(pattern, line):
                # 额外检查：排除明显是代码逻辑的（如 startswith）
                if 'startswith' in line or 'endswith' in line:
                    continue
                violations.append(("intent_hardcode", line_no, message, line.strip()[:80]))

        # 检查敏感信息硬编码
        for pattern, message in HARDCODE_PATTERNS.get("secret_hardcode", []):
            if re.search(pattern, line):
                if 'os.environ' in line or 'os.getenv' in line:
                    continue
                violations.append(("secret_hardcode", line_no, message, line.strip()[:80]))

        # 检查 Windows 路径硬编码
        for pattern, message in WINDOWS_PATH_PATTERNS:
            if re.search(pattern, line):
                # 排除注释
                if '#' in line.split(pattern.lstrip('(r?)'))[0]:
                    continue
                # 排除已经是 Path 对象的
                if 'Path(' in line or 'pathlib' in line:
                    continue
                # 排除字符串格式化中的反斜杠
                if '%' in line or '{' in line:
                    if '\\n' in line or '\\t' in line:
                        continue
                violations.append(("path_hardcode", line_no, message, line.strip()[:80]))

    return violations


def scan_directory(root_path: Path) -> List[Tuple[Path, str, int, str, str]]:
    """
    扫描目录下的所有 Python 文件
    返回: List[(文件路径, 违规类型, 行号, 违规内容, 行内容)]
    """
    all_violations = []

    for py_file in root_path.rglob("*.py"):
        if should_ignore(py_file):
            continue

        violations = check_file(py_file)
        for violation in violations:
            all_violations.append((py_file, *violation))

    return all_violations


def print_report(violations: List[Tuple[Path, str, int, str, str]]):
    """打印检查报告"""
    if not violations:
        print("\n✅ 未检测到硬编码违规！代码审查通过。")
        return True

    print("\n❌ 检测到以下硬编码违规:\n")

    # 按文件分组
    by_file = {}
    for filepath, violation_type, line_no, message, line_content in violations:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append((violation_type, line_no, message, line_content))

    for filepath, file_violations in by_file.items():
        print(f"📄 {filepath}")
        for violation_type, line_no, message, line_content in file_violations:
            type_emoji = {
                "intent_hardcode": "🧠",
                "secret_hardcode": "🔐",
                "path_hardcode": "📁"
            }.get(violation_type, "❓")
            print(f"   {type_emoji} 第 {line_no} 行: {message}")
            print(f"      代码: {line_content}")
        print()

    print(f"\n总计: {len(violations)} 处违规")
    print("\n请修复上述问题后重新提交。参考 rule.md 中的 2.0 强制约束声明")
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("🛡️  Agent-Z 代码审查检查")
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