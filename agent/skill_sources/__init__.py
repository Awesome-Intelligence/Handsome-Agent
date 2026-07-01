"""技能来源适配器模块"""

from .base import SkillSource, SourceResult, SourceSkillInfo
from .github import GitHubSource
from .url import UrlSource
from .router import SourceRouter, create_default_router
from .github_auth import GitHubAuth, get_github_auth
from .hermes_index import HermesIndexSource
from .audit_log import append_audit_log
from .skill_cache import (
    GitHubTreeCache,
    SearchResultCache,
    get_github_tree_cache,
    get_search_result_cache,
    clear_cache,
    get_cache_stats,
)
from .skills_sh import SkillsShSource
from .claude_market import ClaudeMarketSource
from .optional_skill import OptionalSkillSource
from .well_known import WellKnownSkillSource
from .taps_manager import (
    Tap,
    TapsManager,
    get_taps_manager,
    list_taps,
    add_tap,
    remove_tap,
)

__all__ = [
    # 基础
    'SkillSource',
    'SourceResult',
    'SourceSkillInfo',
    # 来源
    'GitHubSource',
    'UrlSource',
    'HermesIndexSource',
    'SkillsShSource',
    'ClaudeMarketSource',
    'OptionalSkillSource',
    'WellKnownSkillSource',
    # 路由
    'SourceRouter',
    'create_default_router',
    # 认证
    'GitHubAuth',
    'get_github_auth',
    # 审计
    'append_audit_log',
    # 缓存
    'GitHubTreeCache',
    'SearchResultCache',
    'get_github_tree_cache',
    'get_search_result_cache',
    'clear_cache',
    'get_cache_stats',
    # Taps
    'Tap',
    'TapsManager',
    'get_taps_manager',
    'list_taps',
    'add_tap',
    'remove_tap',
]