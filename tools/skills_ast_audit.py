#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AST-level Deep Audit for Skill Python Files - 技能代码深度审计

这是一个可选的诊断工具，不是安全门控。

根据安全规范，Skills Guard 是进程内启发式检查（有用的，但不是安全边界）。
这个模块是一个单独的可选诊断工具，用于标记动态 import / 动态属性访问模式，
供操作员在审查第三方技能代码时查看。每一个被标记的模式都有合法的用途；
发现只是人类审查的提示，不是安全裁定。

用途：
- 扫描技能中的 Python 文件
- 检测危险模式：importlib.import_module, __import__, getattr, __dict__[]
- 生成审计报告

📋 Logging Layer: SkillASTAudit

CLI 用法: handsome skills audit --deep
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import List, Tuple, Optional

from common.logging_manager import get_execution_logger

logger = get_execution_logger("SkillASTAudit")

# 审计发现类型 (file, line, pattern_id, description)
ASTPatternFinding = Tuple[str, int, str, str]

# 要排除的目录
_IGNORED_DIRS = frozenset({
    "__pycache__", ".venv", "venv", "node_modules", ".git", ".github"
})


def _scan_source(content: str, rel_path: str) -> List[ASTPatternFinding]:
    """扫描源代码中的危险模式

    Args:
        content: 源代码内容
        rel_path: 相对路径（用于报告）

    Returns:
        发现列表 [(file, line, pattern_id, description), ...]
    """
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError, RecursionError):
        return []

    findings: List[ASTPatternFinding] = []

    class DynamicAccessVisitor(ast.NodeVisitor):
        """访问 AST 节点，检测动态访问模式"""

        def visit_Call(self, node: ast.Call) -> None:
            f = node.func

            # importlib.import_module(...)
            if isinstance(f, ast.Attribute) and f.attr == "import_module":
                findings.append((
                    rel_path,
                    node.lineno,
                    "dynamic_import",
                    "importlib.import_module() — 在运行时加载任意模块"
                ))

            # __import__(<computed>)
            elif isinstance(f, ast.Name) and f.id == "__import__":
                if node.args and not isinstance(node.args[0], ast.Constant):
                    findings.append((
                        rel_path,
                        node.lineno,
                        "dynamic_import_computed",
                        "__import__ with non-literal module name"
                    ))

            # getattr(obj, <computed>)
            elif isinstance(f, ast.Name) and f.id == "getattr":
                if len(node.args) >= 2 and not isinstance(node.args[1], ast.Constant):
                    findings.append((
                        rel_path,
                        node.lineno,
                        "dynamic_getattr",
                        "getattr with non-literal attribute name"
                    ))

            # eval(...) and exec(...)
            elif isinstance(f, ast.Name):
                if f.id == "eval":
                    findings.append((
                        rel_path,
                        node.lineno,
                        "dangerous_eval",
                        "eval() — 动态代码执行"
                    ))
                elif f.id == "exec":
                    findings.append((
                        rel_path,
                        node.lineno,
                        "dangerous_exec",
                        "exec() — 动态代码执行"
                    ))

            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            # obj.__dict__[<computed>]
            if (isinstance(node.value, ast.Attribute)
                    and node.value.attr == "__dict__"
                    and not isinstance(node.slice, ast.Constant)):
                findings.append((
                    rel_path,
                    node.lineno,
                    "dict_access",
                    "__dict__[<computed>] — dynamic attribute access"
                ))
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                # importlib 导入
                if alias.name == "importlib" or alias.name.startswith("importlib."):
                    findings.append((
                        rel_path,
                        node.lineno,
                        "importlib_import",
                        f"import {alias.name} — enables dynamic module loading"
                    ))
                # os.system, os.popen
                elif alias.name in ("os",):
                    # 检查是否使用 system 或 popen
                    pass
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            module = node.module or ""
            if module == "importlib" or module.startswith("importlib."):
                findings.append((
                    rel_path,
                    node.lineno,
                    "importlib_import",
                    f"from {module} import ... — enables dynamic module loading"
                ))
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            # 危险属性访问
            dangerous_attrs = {
                "__globals__": "访问全局变量字典",
                "__code__": "访问代码对象",
                "__closure__": "访问闭包",
                "__builtins__": "访问内置函数",
            }
            if node.attr in dangerous_attrs:
                findings.append((
                    rel_path,
                    node.lineno,
                    "dangerous_attribute",
                    f"访问 {node.attr} — {dangerous_attrs[node.attr]}"
                ))
            self.generic_visit(node)

    try:
        DynamicAccessVisitor().visit(tree)
    except (RecursionError, ValueError, RuntimeError):
        # 恶意/病态输入：返回已收集的结果
        pass

    return findings


def ast_scan_path(path: Path) -> List[ASTPatternFinding]:
    """扫描单个 .py 文件或递归扫描目录

    Args:
        path: 文件或目录路径

    Returns:
        [(file, line, pattern_id, description), ...] 元组列表
        非 Python 路径、缺失路径或无匹配模式的返回空列表
    """
    if path.is_file():
        if path.suffix.lower() != ".py":
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return _scan_source(content, path.name)

    if not path.is_dir():
        return []

    out: List[ASTPatternFinding] = []
    for py in sorted(path.rglob("*.py")):
        # 排除特定目录
        if set(py.parent.parts) & _IGNORED_DIRS:
            continue
        try:
            content = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = py.relative_to(path).as_posix()
        except ValueError:
            rel = py.name
        out.extend(_scan_source(content, rel))

    return out


def scan_skill_directory(skill_dir: Path) -> List[ASTPatternFinding]:
    """扫描技能目录中的所有 Python 文件

    Args:
        skill_dir: 技能目录路径

    Returns:
        发现列表
    """
    all_findings = []

    # 扫描 scripts 目录
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        all_findings.extend(ast_scan_path(scripts_dir))

    # 扫描根目录的 Python 文件
    for py_file in skill_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        findings = _scan_source(
            py_file.read_text(encoding="utf-8", errors="replace"),
            py_file.name
        )
        all_findings.extend(findings)

    return all_findings


def format_ast_report(findings: List[ASTPatternFinding], skill_name: str = "") -> str:
    """生成纯文本报告（无 Rich 标记）

    Args:
        findings: 发现列表
        skill_name: 技能名称

    Returns:
        格式化的报告字符串
    """
    header = f"AST Deep Scan: {skill_name}" if skill_name else "AST Deep Scan"
    if not findings:
        return f"{header}\n  No dynamic import/access patterns detected."

    lines = [header, f"  {len(findings)} finding(s):"]
    current_file = None

    for file, line, pid, desc in sorted(findings):
        if file != current_file:
            current_file = file
            lines.append(f"  {file}")
        lines.append(f"    L{line}  {pid}  — {desc}")

    lines.append("")
    lines.append("  Note: diagnostic hints for human review, not security verdicts.")

    return "\n".join(lines)


def get_severity_level(findings: List[ASTPatternFinding]) -> str:
    """根据发现数量评估严重程度

    Args:
        findings: 发现列表

    Returns:
        严重程度: "low", "medium", "high", "critical"
    """
    if not findings:
        return "none"

    # 统计各类发现
    dangerous_count = sum(1 for f in findings if f[2] in {
        "dynamic_import", "dynamic_import_computed", "dangerous_eval",
        "dangerous_exec", "dangerous_attribute"
    })

    if dangerous_count >= 3:
        return "critical"
    elif dangerous_count >= 1:
        return "high"
    elif len(findings) >= 5:
        return "medium"
    else:
        return "low"


def generate_skill_report(skill_dir: Path) -> dict:
    """为技能生成完整的审计报告

    Args:
        skill_dir: 技能目录

    Returns:
        包含报告信息的字典
    """
    findings = scan_skill_directory(skill_dir)
    severity = get_severity_level(findings)

    return {
        "skill_dir": str(skill_dir),
        "skill_name": skill_dir.name,
        "findings_count": len(findings),
        "severity": severity,
        "findings": findings,
        "report": format_ast_report(findings, skill_dir.name),
    }


# CLI 入口点（可选）
def main():
    """CLI 入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AST Deep Audit for Skill Python Files")
    parser.add_argument("path", help="Skill directory or Python file to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    skill_path = Path(args.path)
    if not skill_path.exists():
        print(f"Error: Path not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    report = generate_skill_report(skill_path)

    if args.json:
        import json
        # 转换 ASTPatternFinding 为 JSON 兼容格式
        report["findings"] = [list(f) for f in report["findings"]]
        print(json.dumps(report, indent=2))
    else:
        print(report["report"])
        sys.exit(1 if report["severity"] in ("high", "critical") else 0)


if __name__ == "__main__":
    main()
