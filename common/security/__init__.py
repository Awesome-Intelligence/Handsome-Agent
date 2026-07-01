# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
安全扫描模块
提供技能安全扫描、隔离、审计等功能
"""

from common.security.audit import (
    append_audit_log,
    clear_audit_log,
    ensure_audit_dirs,
    get_audit_log,
)
from common.security.patterns import (
    INJECTION_PATTERNS,
    INVISIBLE_CHARS,
    SCANNABLE_EXTENSIONS,
    SUSPICIOUS_BINARY_EXTENSIONS,
    THREAT_PATTERNS,
    get_unicode_char_name,
)
from common.security.quarantine import (
    delete_quarantined_skill,
    get_quarantined_skills,
    quarantine_bundle,
    validate_bundle_rel_path,
    validate_skill_name,
)
from common.security.scanner import (
    Finding,
    ScanResult,
    check_injection_in_content,
    format_scan_report,
    scan_file,
    scan_skill,
)
from common.security.trust import (
    TrustLevel,
    Verdict,
    get_trust_level_description,
    resolve_trust_level,
    should_allow_install,
)
from common.security.url_safety import check_urls_in_content, is_safe_url

__all__ = [
    # 核心扫描
    "scan_skill",
    "scan_file",
    "ScanResult",
    "Finding",
    "format_scan_report",
    "check_injection_in_content",
    # 信任管理
    "TrustLevel",
    "Verdict",
    "resolve_trust_level",
    "should_allow_install",
    "get_trust_level_description",
    # 隔离区管理
    "quarantine_bundle",
    "get_quarantined_skills",
    "delete_quarantined_skill",
    "validate_skill_name",
    "validate_bundle_rel_path",
    # 审计日志
    "append_audit_log",
    "get_audit_log",
    "clear_audit_log",
    "ensure_audit_dirs",
    # URL安全
    "is_safe_url",
    "check_urls_in_content",
    # 模式库
    "INJECTION_PATTERNS",
    "THREAT_PATTERNS",
    "INVISIBLE_CHARS",
    "SCANNABLE_EXTENSIONS",
    "SUSPICIOUS_BINARY_EXTENSIONS",
    "get_unicode_char_name",
]