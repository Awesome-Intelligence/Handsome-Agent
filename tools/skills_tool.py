#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills Tool - Skill directory scanning and management.

🏃 Execution - 🛠️ ToolExec - 技能工具

参考 Hermes 的 tools/skills_tool.py 设计，提供：
- 技能目录扫描
- SKILL.md 解析
- 技能视图获取
- 平台过滤
- 使用追踪
- AST 审计

📋 Logging Layer: SkillsTool
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .path_security import has_traversal_component, validate_within_dir
from .skill_env_collector import extract_required_env_vars, get_missing_env_vars
from .skills_guard import detect_prompt_injection

logger = logging.getLogger(__name__)

# Default skills directory
SKILLS_DIR = Path(__file__).parent.parent / "skills"


def get_skills_dir() -> Path:
    """Get the skills directory."""
    return SKILLS_DIR


def set_skills_dir(path: Path | str):
    """Set a custom skills directory."""
    global SKILLS_DIR
    SKILLS_DIR = Path(path)


def list_skills() -> list[Dict[str, Any]]:
    """List all available skills with minimal metadata (progressive disclosure).

    Returns:
        List of skill info dicts with only essential metadata (name, description, category).
        Includes warnings for duplicate skill names.
    """
    skills = []

    if not SKILLS_DIR.exists():
        return skills

    seen_names: dict[str, list[str]] = {}

    for skill_path in SKILLS_DIR.iterdir():
        if not skill_path.is_dir() or skill_path.name.startswith("."):
            continue

        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)

            # Get skill name from frontmatter or directory name
            skill_name = frontmatter.get("name", skill_path.name)

            # Track duplicate names for conflict detection
            if skill_name in seen_names:
                seen_names[skill_name].append(str(skill_path))
            else:
                seen_names[skill_name] = [str(skill_path)]

            # Progressive disclosure: only return minimal metadata
            skills.append({
                "name": skill_name,
                "path": str(skill_path.relative_to(SKILLS_DIR)),
                "description": frontmatter.get("description", ""),
                "category": frontmatter.get("category", "general"),
            })
        except Exception as e:
            logger.debug(f"Failed to load skill at {skill_path}: {e}")

    # Add warnings for duplicate skill names
    duplicate_warnings = []
    for name, paths in seen_names.items():
        if len(paths) > 1:
            duplicate_warnings.append({
                "skill_name": name,
                "locations": paths,
                "message": f"Duplicate skill name '{name}' found at multiple locations",
            })

    if duplicate_warnings:
        logger.warning(f"Found {len(duplicate_warnings)} skill name conflicts")

    return skills


def list_skills_full() -> list[Dict[str, Any]]:
    """List all available skills with full metadata.

    Returns:
        List of skill info dicts with complete metadata (author, version, enabled, etc.).
    """
    skills = []

    if not SKILLS_DIR.exists():
        return skills

    for skill_path in SKILLS_DIR.iterdir():
        if not skill_path.is_dir() or skill_path.name.startswith("."):
            continue

        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)

            skills.append({
                "name": skill_path.name,
                "path": str(skill_path.relative_to(SKILLS_DIR)),
                "description": frontmatter.get("description", ""),
                "category": frontmatter.get("category", "general"),
                "author": frontmatter.get("author", ""),
                "version": frontmatter.get("version", "1.0.0"),
                "enabled": not frontmatter.get("disabled", False),
                "skill_dir": str(skill_path),
            })
        except Exception as e:
            logger.debug(f"Failed to load skill at {skill_path}: {e}")

    return skills


def skill_exists(skill_name: str) -> bool:
    """Check if a skill exists.

    Args:
        skill_name: Skill name

    Returns:
        True if skill exists
    """
    skill_path = SKILLS_DIR / skill_name
    return skill_path.exists() and (skill_path / "SKILL.md").exists()


def skill_view(skill_name: str, task_id: str = None, preprocess: bool = True) -> str:
    """Get the skill view (formatted skill content).

    Args:
        skill_name: Skill name
        task_id: Optional task ID
        preprocess: Whether to preprocess content

    Returns:
        JSON string with skill info and content
    """
    from agent.skill_platform import skill_matches_platform

    result = {
        "success": False,
        "name": skill_name,
        "path": "",
        "content": "",
        "error": "",
    }

    # Check for path traversal before processing
    if has_traversal_component(skill_name):
        result["error"] = "Path traversal attempt detected"
        result["security_error"] = True
        return json.dumps(result)

    # Try direct path first
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        # Try without leading slash
        if skill_name.startswith("/"):
            skill_name = skill_name[1:]
            skill_path = SKILLS_DIR / skill_name

    if not skill_path.exists():
        result["error"] = f"Skill not found: {skill_name}"
        return json.dumps(result)

    # Validate skill path is within skills directory
    validation_error = validate_within_dir(skill_path, SKILLS_DIR)
    if validation_error:
        result["error"] = validation_error
        result["security_error"] = True
        return json.dumps(result)

    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        result["error"] = f"SKILL.md not found in {skill_name}"
        return json.dumps(result)

    try:
        content = skill_file.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)

        # Check platform compatibility
        if not skill_matches_platform(frontmatter):
            result["success"] = False
            result["error"] = f"Skill '{skill_name}' is not supported on this platform."
            result["readiness_status"] = "unsupported"
            return json.dumps(result)

        # Get actual content (after frontmatter)
        body_content = _get_content_after_frontmatter(content)

        # 检测 Prompt 注入
        is_dangerous, patterns = detect_prompt_injection(body_content)
        if is_dangerous:
            logger.warning(
                f"Skill '{skill_name}' contains potential prompt injection patterns: {patterns}"
            )

        result["success"] = True
        result["name"] = skill_path.name
        result["path"] = str(skill_path.relative_to(SKILLS_DIR))
        result["content"] = body_content
        result["skill_dir"] = str(skill_path)
        result["description"] = frontmatter.get("description", "")
        result["category"] = frontmatter.get("category", "general")
        result["security_warning"] = f"Potential prompt injection detected. Patterns: {patterns}" if is_dangerous else None
        result["readiness_status"] = "available"

        # 提取环境变量需求并检查缺失
        requirements = extract_required_env_vars(frontmatter)
        missing_vars = get_missing_env_vars(requirements)

        result["required_environment_variables"] = [r.__dict__ for r in requirements]
        result["missing_required_environment_variables"] = missing_vars
        result["setup_needed"] = len(missing_vars) > 0

        if preprocess:
            result["content"] = _preprocess_content(body_content, skill_path)

        # 记录技能查看
        _record_skill_view(skill_path.name)

    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result)


def _record_skill_view(skill_name: str) -> None:
    """记录技能查看，同时更新多个追踪系统
    
    Args:
        skill_name: 技能名称
    """
    # 更新 agent/skill_usage_tracker.py
    try:
        from agent.skill_usage_tracker import bump_view
        bump_view(skill_name)
    except ImportError:
        pass
    
    logger.debug(f"Recorded skill view: {skill_name}")


def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from skill content.

    委托给 agent.skill_utils 中的统一实现。

    Args:
        content: Raw skill content

    Returns:
        Dict of frontmatter values
    """
    from agent.skill_utils import parse_frontmatter
    fm, _ = parse_frontmatter(content)
    return fm


def _get_content_after_frontmatter(content: str) -> str:
    """Get content after frontmatter.

    Args:
        content: Raw content with frontmatter

    Returns:
        Content after frontmatter
    """
    lines = content.split("\n")

    if len(lines) < 3 or lines[0].strip() != "---":
        return content

    # Find closing ---
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return content

    return "\n".join(lines[end_idx + 1:]).strip()


def _preprocess_content(content: str, skill_dir: Path) -> str:
    """Preprocess skill content.

    Args:
        content: Raw content
        skill_dir: Skill directory

    Returns:
        Preprocessed content
    """
    from agent.skill_preprocessing import preprocess_skill_content
    processed_content, warnings = preprocess_skill_content(content, skill_dir)
    return processed_content


def get_skill_references(skill_name: str) -> list[Dict[str, str]]:
    """Get skill reference files.

    Args:
        skill_name: Skill name

    Returns:
        List of reference files
    """
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        return []

    references = []
    ref_dir = skill_path / "references"

    if not ref_dir.exists():
        return []

    for ref_file in ref_dir.iterdir():
        if ref_file.is_file():
            references.append({
                "name": ref_file.name,
                "path": str(ref_file.relative_to(SKILLS_DIR)),
                "type": ref_file.suffix.lstrip("."),
            })

    return references


def get_skill_prompts(skill_name: str) -> list[Dict[str, str]]:
    """Get skill prompt templates.

    Args:
        skill_name: Skill name

    Returns:
        List of prompt templates
    """
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        return []

    prompts = []
    prompts_dir = skill_path / "prompts"

    if not prompts_dir.exists():
        return []

    for prompt_file in prompts_dir.iterdir():
        if prompt_file.is_file() and prompt_file.suffix == ".md":
            try:
                content = prompt_file.read_text(encoding="utf-8")
                prompts.append({
                    "name": prompt_file.stem,
                    "path": str(prompt_file.relative_to(SKILLS_DIR)),
                    "content": content,
                })
            except Exception:
                pass

    return prompts


# =============================================================================
# Skill Analysis Tool - 技能分析
# =============================================================================

def skill_analysis(
    action: str,
    name: str = None,
    category: str = None,
    limit: int = 10,
) -> str:
    """技能分析工具"""
    import json
    try:
        if action == "stats":
            result = _analysis_stats()
        elif action == "top":
            result = _analysis_top(limit)
        elif action == "trends":
            result = _analysis_trends(limit)
        elif action == "quality":
            if not name:
                return json.dumps({"success": False, "error": "name is required for 'quality'"})
            result = _analysis_quality(name)
        elif action == "compare":
            result = _analysis_compare()
        elif action == "suggest":
            result = _analysis_suggest(limit)
        else:
            result = {"success": False, "error": f"Unknown action '{action}'"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


def _analysis_stats() -> Dict[str, Any]:
    """获取全局统计"""
    try:
        from agent.skill_usage_tracker import get_usage_tracker
        from agent.skill_lock import list_locked_skills

        tracker = get_usage_tracker()
        locked = list_locked_skills()
        all_records = tracker.list_all_records()
        stats = tracker.get_stats()

        return {
            "success": True,
            "stats": {
                "total_skills": len(all_records),
                "tracked_skills": len(all_records),
                "locked_skills": len(locked),
                "total_uses": stats.get("total_use_count", 0),
                "total_views": stats.get("total_view_count", 0),
            },
            "curator": {
                "active": sum(1 for r in all_records if r.state == "active"),
                "stale": sum(1 for r in all_records if r.state == "stale"),
                "archived": sum(1 for r in all_records if r.state == "archived"),
                "pinned": sum(1 for r in all_records if r.pinned),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analysis_top(limit: int) -> Dict[str, Any]:
    """获取使用最多的技能"""
    try:
        from agent.skill_usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        all_records = tracker.list_all_records()
        sorted_records = sorted(all_records, key=lambda r: (r.use_count, r.view_count), reverse=True)[:limit]
        return {
            "success": True,
            "top_skills": [{"name": r.skill_name, "use_count": r.use_count} for r in sorted_records],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analysis_trends(limit: int) -> Dict[str, Any]:
    """获取使用趋势"""
    try:
        from agent.skill_usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        all_records = tracker.list_all_records()
        sorted_records = sorted(all_records, key=lambda r: r.last_used_at or "", reverse=True)[:limit]
        return {
            "success": True,
            "recently_used": [{"name": r.skill_name, "last_used": r.last_used_at} for r in sorted_records],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analysis_quality(name: str) -> Dict[str, Any]:
    """评估技能质量"""
    try:
        from agent.skill_utils import parse_frontmatter
        from common.config import get_skills_dir
        skill_file = get_skills_dir() / name / "SKILL.md"
        if not skill_file.exists():
            return {"success": False, "error": f"Skill '{name}' not found"}
        content = skill_file.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        score = 20
        score += 10 if frontmatter.get("description") else 0
        score += 10 if frontmatter.get("triggers") else 0
        grade = "A" if score >= 30 else "B" if score >= 20 else "C"
        return {"success": True, "skill_name": name, "quality_score": score, "grade": grade}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analysis_compare() -> Dict[str, Any]:
    """对比所有技能"""
    try:
        from agent.skill_usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        all_records = tracker.list_all_records()
        return {
            "success": True,
            "skills": [{"name": r.skill_name, "use_count": r.use_count} for r in all_records],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _analysis_suggest(limit: int) -> Dict[str, Any]:
    """建议可能需要的技能"""
    try:
        from agent.skill_usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        all_records = tracker.list_all_records()
        unused = [r.skill_name for r in all_records if r.use_count == 0][:limit]
        return {"success": True, "suggestions": {"unused_skills": unused}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Skill Scheduler Tool - 技能调度和锁定
# =============================================================================

def skill_scheduler(action: str, task_name: str = None, source_filter: str = None) -> str:
    """技能调度和锁定工具"""
    import json
    try:
        from agent.skill_scheduler import get_scheduler
        from agent.skill_lock import list_locked_skills
        scheduler = get_scheduler()

        if action == "scheduler_status":
            status = scheduler.get_status()
            result = {"success": True, "running": status.get("running", False), "tasks_count": status.get("tasks_count", 0)}
        elif action == "scheduler_list":
            tasks = scheduler.list_tasks()
            result = {"success": True, "tasks": tasks}
        elif action == "scheduler_run":
            success = scheduler.run_now(task_name or "curator_cleanup")
            result = {"success": success, "message": f"Task triggered" if success else "Task not found"}
        elif action == "scheduler_enable":
            success = scheduler.enable_task(task_name or "")
            result = {"success": success}
        elif action == "scheduler_disable":
            success = scheduler.disable_task(task_name or "")
            result = {"success": success}
        elif action == "lock_list":
            entries = list_locked_skills(source_filter)
            result = {"success": True, "count": len(entries), "skills": [{"name": e.skill_name} for e in entries]}
        elif action == "lock_check":
            result = {"success": True, "message": "Update check not implemented in tool context"}
        else:
            result = {"success": False, "error": f"Unknown action '{action}'"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =============================================================================
# Skill Curator Tool - 技能生命周期管理
# =============================================================================

def skill_curator(action: str, name: str = None, dry_run: bool = False) -> str:
    """技能生命周期管理工具"""
    import json
    try:
        from agent.skill_curator import run_curator, get_curator_config, pin_skill, unpin_skill
        from agent.skill_usage_tracker import get_usage_tracker

        if action == "status":
            tracker = get_usage_tracker()
            all_records = tracker.list_all_records()
            result = {
                "success": True,
                "stats": {
                    "total": len(all_records),
                    "active": sum(1 for r in all_records if r.state == "active"),
                    "stale": sum(1 for r in all_records if r.state == "stale"),
                    "archived": sum(1 for r in all_records if r.state == "archived"),
                },
            }
        elif action == "run":
            config = get_curator_config()
            config.dry_run = dry_run
            report = run_curator(config)
            result = {"success": True, "marked_stale": len([a for a in report.actions if a.action == "mark_stale"])}
        elif action == "pin":
            if not name:
                return json.dumps({"success": False, "error": "name is required"})
            success = pin_skill(name)
            result = {"success": success}
        elif action == "unpin":
            if not name:
                return json.dumps({"success": False, "error": "name is required"})
            success = unpin_skill(name)
            result = {"success": success}
        elif action == "archive":
            result = {"success": False, "error": "Use agent.skill_curator.force_archive_skill"}
        elif action == "restore":
            result = {"success": False, "error": "Use agent.skill_curator.restore_archived_skill"}
        elif action == "list":
            tracker = get_usage_tracker()
            all_records = tracker.list_all_records()
            result = {"success": True, "active": [r.skill_name for r in all_records if r.state == "active"]}
        else:
            result = {"success": False, "error": f"Unknown action '{action}'"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =============================================================================
# Skill History Tool - 技能版本历史
# =============================================================================

def skill_history(
    action: str, name: str = None, version: str = None,
    v1: str = None, v2: str = None, content: str = None, message: str = None,
) -> str:
    """技能版本历史工具"""
    import json
    try:
        from agent.skill_history import get_history
        history = get_history()

        if action == "record":
            if not name:
                return json.dumps({"success": False, "error": "name is required"})
            if not content:
                from common.config import get_skills_dir
                content = (get_skills_dir() / name / "SKILL.md").read_text(encoding="utf-8")
            entry = history.record_change(name, "edit", content, message or "")
            result = {"success": bool(entry), "version": entry.version if entry else None}
        elif action == "list" or action == "versions":
            if not name:
                return json.dumps({"success": False, "error": "name is required"})
            versions = history.get_version_list(name)
            result = {"success": True, "versions": versions}
        elif action == "diff":
            if not name or not v1:
                return json.dumps({"success": False, "error": "name and v1 are required"})
            diff = history.diff(name, v1, v2)
            result = {"success": True, **diff}
        elif action == "rollback":
            if not name or not version:
                return json.dumps({"success": False, "error": "name and version are required"})
            result = history.rollback(name, version)
        else:
            result = {"success": False, "error": f"Unknown action '{action}'"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =============================================================================
# Skill Bundle Tool - 技能导入导出
# =============================================================================

def skill_bundle(
    action: str, name: str = None, output_path: str = None,
    bundle_path: str = None, template_id: str = None, category: str = None,
    overwrite: bool = False, dry_run: bool = False,
) -> str:
    """技能导入导出工具"""
    import json
    try:
        from agent.skill_bundle import get_bundle, ExportOptions, ImportOptions

        bundle = get_bundle()

        if action == "export":
            if not output_path:
                return json.dumps({"success": False, "error": "output_path is required"})
            options = ExportOptions()
            success = bundle.export_skill(name, output_path, options) if name else bundle.export_all(output_path, options)
            result = {"success": success, "output_path": output_path}
        elif action == "import":
            if not bundle_path:
                return json.dumps({"success": False, "error": "bundle_path is required"})
            options = ImportOptions(overwrite=overwrite, dry_run=dry_run)
            result = bundle.import_bundle(bundle_path, options)
        elif action == "templates":
            templates = bundle.list_templates()
            result = {"success": True, "templates": templates}
        elif action == "create_from_template":
            if not template_id or not name:
                return json.dumps({"success": False, "error": "template_id and name are required"})
            result = bundle.create_from_template(template_id, name, category)
        else:
            result = {"success": False, "error": f"Unknown action '{action}'"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =============================================================================
# 统一注册所有工具
# =============================================================================

def _register_all_skills_tools():
    """注册所有技能相关工具到 registry"""
    from tools.registry import registry

    # skill_analysis
    registry.register(
        name="skill_analysis", toolset="skills",
        schema={
            "name": "skill_analysis",
            "description": "Analyze skills: stats, top, trends, quality, compare, suggest",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["stats", "top", "trends", "quality", "compare", "suggest"]},
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["action"],
            },
        },
        handler=lambda args, **kw: skill_analysis(action=args.get("action", ""), name=args.get("name"), category=args.get("category"), limit=args.get("limit", 10)),
        emoji="📊",
    )

    # skill_scheduler
    registry.register(
        name="skill_scheduler", toolset="skills",
        schema={
            "name": "skill_scheduler",
            "description": "Manage scheduler and locks: scheduler_status, scheduler_list, lock_list, lock_check",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["scheduler_status", "scheduler_list", "scheduler_run", "scheduler_enable", "scheduler_disable", "lock_list", "lock_info", "lock_check"]},
                    "task_name": {"type": "string"},
                    "source_filter": {"type": "string"},
                },
                "required": ["action"],
            },
        },
        handler=lambda args, **kw: skill_scheduler(action=args.get("action", ""), task_name=args.get("task_name"), source_filter=args.get("source_filter")),
        emoji="⏰",
    )

    # skill_curator
    registry.register(
        name="skill_curator", toolset="skills",
        schema={
            "name": "skill_curator",
            "description": "Manage skill lifecycle: status, run, pin, unpin, list",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["status", "run", "pin", "unpin", "archive", "restore", "list"]},
                    "name": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["action"],
            },
        },
        handler=lambda args, **kw: skill_curator(action=args.get("action", ""), name=args.get("name"), dry_run=args.get("dry_run", False)),
        emoji="🧹",
    )

    # skill_history
    registry.register(
        name="skill_history", toolset="skills",
        schema={
            "name": "skill_history",
            "description": "Manage version history: record, list, diff, rollback",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["record", "list", "diff", "rollback", "versions"]},
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "v1": {"type": "string"},
                    "v2": {"type": "string"},
                    "content": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["action"],
            },
        },
        handler=lambda args, **kw: skill_history(action=args.get("action", ""), name=args.get("name"), version=args.get("version"), v1=args.get("v1"), v2=args.get("v2"), content=args.get("content"), message=args.get("message")),
        emoji="📜",
    )

    # skill_bundle
    registry.register(
        name="skill_bundle", toolset="skills",
        schema={
            "name": "skill_bundle",
            "description": "Import/export skills: export, import, templates, create_from_template",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["export", "import", "templates", "create_from_template"]},
                    "name": {"type": "string"},
                    "output_path": {"type": "string"},
                    "bundle_path": {"type": "string"},
                    "template_id": {"type": "string"},
                    "category": {"type": "string"},
                    "overwrite": {"type": "boolean"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["action"],
            },
        },
        handler=lambda args, **kw: skill_bundle(action=args.get("action", ""), name=args.get("name"), output_path=args.get("output_path"), bundle_path=args.get("bundle_path"), template_id=args.get("template_id"), category=args.get("category"), overwrite=args.get("overwrite", False), dry_run=args.get("dry_run", False)),
        emoji="📦",
    )


# 自动注册
_register_all_skills_tools()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Test
    print("Skills directory:", SKILLS_DIR)
    print("\nAvailable skills:")
    skills = list_skills()
    for skill in skills:
        print(f"  - {skill['name']}: {skill.get('description', '')}")