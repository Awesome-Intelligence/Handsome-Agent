# Copyright (c) 2026 Agent-Z Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
信任级别管理模块
定义和管理技能的信任级别及其安装策略
"""

from enum import Enum
from typing import Dict, Tuple

# 可信的仓库列表
TRUSTED_REPOS: set = {
    "openai/skills",
    "anthropic/skills",
    "huggingface/skills",
    "handsome-agent/official",
}


class TrustLevel(str, Enum):
    """信任级别枚举"""
    BUILTIN = "builtin"
    TRUSTED = "trusted"
    COMMUNITY = "community"
    AGENT_CREATED = "agent-created"


class Verdict(str, Enum):
    """扫描判决结果枚举"""
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


# 安装策略: (safe时操作, caution时操作, dangerous时操作)
# 操作选项: "allow", "block", "ask"
INSTALL_POLICY: Dict[TrustLevel, Tuple[str, str, str]] = {
    TrustLevel.BUILTIN: ("allow", "allow", "allow"),
    TrustLevel.TRUSTED: ("allow", "allow", "block"),
    TrustLevel.COMMUNITY: ("allow", "block", "block"),
    TrustLevel.AGENT_CREATED: ("allow", "allow", "ask"),
}

# 判决结果的优先级索引
VERDICT_INDEX: Dict[Verdict, int] = {
    Verdict.SAFE: 0,
    Verdict.CAUTION: 1,
    Verdict.DANGEROUS: 2,
}


def resolve_trust_level(source: str) -> TrustLevel:
    """
    根据来源标识解析信任级别

    Args:
        source: 技能来源标识

    Returns:
        信任级别
    """
    if not source:
        return TrustLevel.COMMUNITY

    # 标准化来源标识
    normalized_source = source.lower().strip()

    # 处理前缀别名
    prefixes_to_strip = (
        "skills-sh/",
        "skills.sh/",
        "skils-sh/",
        "skils.sh/",
    )
    for prefix in prefixes_to_strip:
        if normalized_source.startswith(prefix):
            normalized_source = normalized_source[len(prefix):]
            break

    # Agent创建的技能
    if normalized_source == "agent-created":
        return TrustLevel.AGENT_CREATED

    # 官方技能
    if normalized_source.startswith("official/") or normalized_source == "official":
        return TrustLevel.BUILTIN

    # 检查可信仓库
    for trusted in TRUSTED_REPOS:
        if normalized_source.startswith(trusted) or normalized_source == trusted:
            return TrustLevel.TRUSTED

    return TrustLevel.COMMUNITY


def should_allow_install(
    verdict: Verdict,
    trust_level: TrustLevel,
    force: bool = False,
    findings_count: int = 0,
) -> Tuple[bool, str]:
    """
    根据扫描结果和信任级别决定是否允许安装

    Args:
        verdict: 扫描判决结果
        trust_level: 信任级别
        force: 是否强制安装
        findings_count: 发现的问题数量

    Returns:
        (是否允许, 原因说明)
    """
    policy = INSTALL_POLICY.get(trust_level, INSTALL_POLICY[TrustLevel.COMMUNITY])
    vi = VERDICT_INDEX.get(verdict, 2)
    decision = policy[vi]

    if decision == "allow":
        return True, f"Allowed ({trust_level.value} source, {verdict.value} verdict)"

    # force参数可以在某些情况下覆盖阻止
    if force and not (verdict == Verdict.DANGEROUS and trust_level in (
        TrustLevel.COMMUNITY,
        TrustLevel.TRUSTED,
    )):
        return True, (
            f"Force-installed despite {verdict.value} verdict "
            f"({findings_count} findings)"
        )

    if decision == "ask":
        return None, (
            f"Requires confirmation ({trust_level.value} source + {verdict.value} verdict, "
            f"{findings_count} findings)"
        )

    # Dangerous verdict 不能被 force 覆盖 (community/trusted)
    if verdict == Verdict.DANGEROUS and trust_level in (
        TrustLevel.COMMUNITY,
        TrustLevel.TRUSTED,
    ):
        return False, (
            f"Blocked ({trust_level.value} source + dangerous verdict, "
            f"{findings_count} findings). --force does not override a dangerous verdict."
        )

    return False, (
        f"Blocked ({trust_level.value} source + {verdict.value} verdict, "
        f"{findings_count} findings). Use --force to override."
    )


def get_trust_level_description(level: TrustLevel) -> str:
    """
    获取信任级别的描述

    Args:
        level: 信任级别

    Returns:
        描述文本
    """
    descriptions = {
        TrustLevel.BUILTIN: "官方内置技能，完全可信",
        TrustLevel.TRUSTED: "来自可信仓库，经过验证",
        TrustLevel.COMMUNITY: "社区贡献，需要扫描验证",
        TrustLevel.AGENT_CREATED: "Agent自动创建，需要扫描验证",
    }
    return descriptions.get(level, "未知信任级别")