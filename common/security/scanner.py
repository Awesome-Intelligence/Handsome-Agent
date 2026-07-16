# Copyright (c) 2026 Agent-Z Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
安全扫描器核心模块
扫描技能目录中的所有安全威胁
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from common.logging_manager import get_logger
from common.security.patterns import (
    INJECTION_PATTERNS,
    INVISIBLE_CHARS,
    SCANNABLE_EXTENSIONS,
    SUSPICIOUS_BINARY_EXTENSIONS,
    THREAT_PATTERNS,
    get_unicode_char_name,
)
from common.security.trust import (
    TrustLevel,
    Verdict,
    resolve_trust_level,
    should_allow_install,
)

logger = get_logger(__name__)

# 结构限制常量
MAX_FILE_COUNT = 50  # 技能目录最大文件数
MAX_TOTAL_SIZE_KB = 1024  # 最大总大小 1MB
MAX_SINGLE_FILE_KB = 256  # 单个文件最大 256KB


@dataclass
class Finding:
    """安全发现项"""
    pattern_id: str
    severity: str  # "critical" | "high" | "medium" | "low"
    category: str  # "exfiltration" | "injection" | "destructive" | "persistence" | "network" | "obfuscation"
    file: str
    line: int
    match: str
    description: str

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "pattern_id": self.pattern_id,
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "match": self.match,
            "description": self.description,
        }


@dataclass
class ScanResult:
    """扫描结果"""
    skill_name: str
    source: str
    trust_level: TrustLevel
    verdict: Verdict
    findings: List[Finding] = field(default_factory=list)
    scanned_at: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "skill_name": self.skill_name,
            "source": self.source,
            "trust_level": self.trust_level.value,
            "verdict": self.verdict.value,
            "findings": [f.to_dict() for f in self.findings],
            "scanned_at": self.scanned_at,
            "summary": self.summary,
        }

    @property
    def findings_count(self) -> int:
        """发现问题数量"""
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        """严重问题数量"""
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        """高危问题数量"""
        return sum(1 for f in self.findings if f.severity == "high")


def scan_file(file_path: Path, rel_path: str = "") -> List[Finding]:
    """
    扫描单个文件的安全威胁

    Args:
        file_path: 文件路径
        rel_path: 相对路径（用于报告）

    Returns:
        发现的问题列表
    """
    if not rel_path:
        rel_path = file_path.name

    # 检查是否应该扫描此文件
    if (
        file_path.suffix.lower() not in SCANNABLE_EXTENSIONS
        and file_path.name != "SKILL.md"
        and file_path.name != "SKILL.yaml"
        and file_path.name != "SKILL.yml"
    ):
        return []

    # 读取文件内容
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    findings: List[Finding] = []
    lines = content.split("\n")
    seen: set = set()  # (pattern_id, line_number) 用于去重

    # 正则模式匹配
    for pattern, pid, severity, category, description in THREAT_PATTERNS:
        for i, line in enumerate(lines, start=1):
            if (pid, i) in seen:
                continue
            if re.search(pattern, line, re.IGNORECASE):
                seen.add((pid, i))
                matched_text = line.strip()
                if len(matched_text) > 120:
                    matched_text = matched_text[:117] + "..."
                findings.append(
                    Finding(
                        pattern_id=pid,
                        severity=severity,
                        category=category,
                        file=rel_path,
                        line=i,
                        match=matched_text,
                        description=description,
                    )
                )

    # 不可见unicode字符检测
    for i, line in enumerate(lines, start=1):
        for char in INVISIBLE_CHARS:
            if char in line:
                char_name = get_unicode_char_name(char)
                findings.append(
                    Finding(
                        pattern_id="invisible_unicode",
                        severity="high",
                        category="injection",
                        file=rel_path,
                        line=i,
                        match=f"U+{ord(char):04X} ({char_name})",
                        description=f"invisible unicode character {char_name} (possible text hiding/injection)",
                    )
                )
                break  # 每行只报告一次

    return findings


def _check_structure(skill_dir: Path) -> List[Finding]:
    """
    检查技能目录结构异常

    Args:
        skill_dir: 技能目录路径

    Returns:
        发现的问题列表
    """
    findings: List[Finding] = []
    file_count = 0
    total_size = 0

    for f in skill_dir.rglob("*"):
        if not f.is_file() and not f.is_symlink():
            continue

        rel = str(f.relative_to(skill_dir))
        file_count += 1

        # 符号链接检查
        if f.is_symlink():
            try:
                resolved = f.resolve()
                # 检查符号链接是否指向技能目录外
                try:
                    skill_dir_resolved = skill_dir.resolve()
                    if not resolved.is_relative_to(skill_dir_resolved):
                        findings.append(
                            Finding(
                                pattern_id="symlink_escape",
                                severity="critical",
                                category="traversal",
                                file=rel,
                                line=0,
                                match=f"symlink -> {resolved}",
                                description="symlink points outside the skill directory",
                            )
                        )
                except ValueError:
                    # is_relative_to在某些情况下可能失败
                    findings.append(
                        Finding(
                            pattern_id="symlink_escape",
                            severity="critical",
                            category="traversal",
                            file=rel,
                            line=0,
                            match=f"symlink -> {resolved}",
                            description="symlink may point outside the skill directory",
                        )
                    )
            except OSError:
                findings.append(
                    Finding(
                        pattern_id="broken_symlink",
                        severity="medium",
                        category="traversal",
                        file=rel,
                        line=0,
                        match="broken symlink",
                        description="broken or circular symlink",
                    )
                )
            continue

        # 大小检查
        try:
            size = f.stat().st_size
            total_size += size
        except OSError:
            continue

        # 单文件过大
        if size > MAX_SINGLE_FILE_KB * 1024:
            findings.append(
                Finding(
                    pattern_id="oversized_file",
                    severity="medium",
                    category="structural",
                    file=rel,
                    line=0,
                    match=f"{size // 1024}KB",
                    description=f"file is {size // 1024}KB (limit: {MAX_SINGLE_FILE_KB}KB)",
                )
            )

        # 二进制/可执行文件检测
        ext = f.suffix.lower()
        if ext in SUSPICIOUS_BINARY_EXTENSIONS:
            findings.append(
                Finding(
                    pattern_id="binary_file",
                    severity="critical",
                    category="structural",
                    file=rel,
                    line=0,
                    match=f"binary: {ext}",
                    description=f"binary/executable file ({ext}) should not be in a skill",
                )
            )

    # 文件数量限制
    if file_count > MAX_FILE_COUNT:
        findings.append(
            Finding(
                pattern_id="too_many_files",
                severity="medium",
                category="structural",
                file="(directory)",
                line=0,
                match=f"{file_count} files",
                description=f"skill has {file_count} files (limit: {MAX_FILE_COUNT})",
            )
        )

    # 总大小限制
    if total_size > MAX_TOTAL_SIZE_KB * 1024:
        findings.append(
            Finding(
                pattern_id="oversized_skill",
                severity="high",
                category="structural",
                file="(directory)",
                line=0,
                match=f"{total_size // 1024}KB total",
                description=f"skill is {total_size // 1024}KB total (limit: {MAX_TOTAL_SIZE_KB}KB)",
            )
        )

    return findings


def _determine_verdict(findings: List[Finding]) -> Verdict:
    """
    根据发现的问题确定扫描判决

    Args:
        findings: 发现的问题列表

    Returns:
        判决结果
    """
    if not findings:
        return Verdict.SAFE

    # 有任何严重问题 -> dangerous
    if any(f.severity == "critical" for f in findings):
        return Verdict.DANGEROUS

    # 有任何高危问题 -> dangerous
    if any(f.severity == "high" for f in findings):
        return Verdict.DANGEROUS

    # 只有中低危问题 -> caution
    return Verdict.CAUTION


def _build_summary(
    skill_name: str,
    source: str,
    trust_level: TrustLevel,
    verdict: Verdict,
    findings: List[Finding],
) -> str:
    """
    构建扫描摘要

    Args:
        skill_name: 技能名称
        source: 来源
        trust_level: 信任级别
        verdict: 判决结果
        findings: 发现的问题

    Returns:
        摘要文本
    """
    critical = sum(1 for f in findings if f.severity == "critical")
    high = sum(1 for f in findings if f.severity == "high")
    medium = sum(1 for f in findings if f.severity == "medium")
    low = sum(1 for f in findings if f.severity == "low")

    summary_parts = [
        f"Skill: {skill_name}",
        f"Source: {source}",
        f"Trust Level: {trust_level.value}",
        f"Verdict: {verdict.value}",
        f"Findings: {len(findings)} total",
    ]

    if critical:
        summary_parts.append(f"Critical: {critical}")
    if high:
        summary_parts.append(f"High: {high}")
    if medium:
        summary_parts.append(f"Medium: {medium}")
    if low:
        summary_parts.append(f"Low: {low}")

    return " | ".join(summary_parts)


def _scan_python_ast(file_path: Path, rel_path: str) -> List[Finding]:
    """
    使用 AST 对 Python 文件进行深度审计。

    检测危险模式：
    - importlib.import_module() 动态导入
    - __import__() 带非字面量参数
    - getattr() 带非字面量属性名
    - __dict__[] 动态属性访问

    Args:
        file_path: Python 文件路径
        rel_path: 相对路径（用于报告）

    Returns:
        发现列表
    """
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8")
        from tools.skills_ast_audit import _scan_source
        ast_findings = _scan_source(content, rel_path)

        # 转换 AST 审计发现为安全扫描发现
        for file_rel, line_no, pattern_id, description in ast_findings:
            # 截取匹配的代码片段
            lines = content.split("\n")
            match = lines[line_no - 1].strip() if line_no <= len(lines) else ""

            findings.append(Finding(
                pattern_id=f"ast_{pattern_id}",
                severity="medium",  # AST 发现通常是中等严重性
                category="obfuscation",
                file=rel_path,
                line=line_no,
                match=match[:100],
                description=description,
            ))
    except Exception:
        pass  # 无法解析的文件跳过

    return findings


def scan_skill(skill_path: Path, source: str = "community", enable_ast_audit: bool = False) -> ScanResult:
    """
    扫描技能目录中的所有安全威胁

    Args:
        skill_path: 技能路径（目录或文件）
        source: 技能来源标识
        enable_ast_audit: 是否启用 AST 深度审计

    Returns:
        扫描结果
    """
    skill_name = skill_path.name
    trust_level = resolve_trust_level(source)
    all_findings: List[Finding] = []

    if skill_path.is_dir():
        # 首先进行结构性检查
        all_findings.extend(_check_structure(skill_path))

        # 对每个文件进行模式扫描
        for f in skill_path.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(skill_path))
                all_findings.extend(scan_file(f, rel))

                # AST 深度审计（可选）
                if enable_ast_audit and f.suffix == ".py":
                    all_findings.extend(_scan_python_ast(f, rel))
    elif skill_path.is_file():
        all_findings.extend(scan_file(skill_path, skill_path.name))

        # AST 深度审计（可选）
        if enable_ast_audit and skill_path.suffix == ".py":
            all_findings.extend(_scan_python_ast(skill_path, skill_path.name))

    verdict = _determine_verdict(all_findings)
    summary = _build_summary(skill_name, source, trust_level, verdict, all_findings)

    result = ScanResult(
        skill_name=skill_name,
        source=source,
        trust_level=trust_level,
        verdict=verdict,
        findings=all_findings,
        scanned_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
    )

    logger.info(
        "Scanned skill '%s' from %s: %s (findings: %d)",
        skill_name,
        source,
        verdict.value,
        len(all_findings),
    )

    return result


def check_injection_in_content(content: str) -> List[str]:
    """
    快速检查内容中是否包含注入模式

    Args:
        content: 要检查的内容

    Returns:
        发现的注入模式列表
    """
    detected = []
    content_lower = content.lower()

    for pattern in INJECTION_PATTERNS:
        if pattern.lower() in content_lower:
            detected.append(pattern)

    return detected


def format_scan_report(result: ScanResult) -> str:
    """
    格式化扫描结果为可读报告

    Args:
        result: 扫描结果

    Returns:
        格式化的报告文本
    """
    lines = []

    verdict_display = result.verdict.value.upper()
    lines.append(
        f"Scan: {result.skill_name} ({result.source}/{result.trust_level.value})  "
        f"Verdict: {verdict_display}"
    )

    if result.findings:
        # 按严重级别排序：critical > high > medium > low
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(
            result.findings, key=lambda f: severity_order.get(f.severity, 4)
        )

        for f in sorted_findings:
            sev = f.severity.upper().ljust(8)
            cat = f.category.ljust(14)
            loc = f"{f.file}:{f.line}".ljust(30)
            match_text = f.match[:60] if len(f.match) > 60 else f.match
            lines.append(f'  {sev} {cat} {loc} "{match_text}"')

        lines.append("")

    allowed, reason = should_allow_install(
        result.verdict, result.trust_level, findings_count=len(result.findings)
    )

    if allowed is True:
        status = "ALLOWED"
    elif allowed is None:
        status = "NEEDS CONFIRMATION"
    else:
        status = "BLOCKED"

    lines.append(f"Decision: {status} — {reason}")

    return "\n".join(lines)