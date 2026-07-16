#!/usr/bin/env python3
"""
Skill Manager Tool Module

Provides skill registration, discovery and execution functionality:
- Skill registration and discovery
- Skill execution interface
- Skill metadata management

Based on Hermes Agent's skill_manager_tool.py and skills_tool.py implementation.

Usage:
    from tools.skill_manager_tool import skill_manage
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from common.logging_manager import get_execution_logger
from common.skill_utils import parse_frontmatter
from common.file_utils import atomic_replace, atomic_write_text
from tools.registry import registry


def tool_error(message: str, success: bool = False) -> str:
    """Simple tool error response function"""
    return json.dumps({
        "success": success,
        "error": message
    }, ensure_ascii=False)

logger = get_execution_logger("SkillManagerTool")

# 技能目录
def get_skills_dir() -> Path:
    """获取技能存储目录"""
    base_dir = Path.home() / ".agent_z"
    skills_dir = base_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_CONTENT_CHARS = 100000
MAX_SKILL_FILE_BYTES = 1048576

# 技能名称验证
VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')

# 允许的子目录
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}


def _validate_name(name: str) -> Optional[str]:
    """验证技能名称"""
    if not name:
        return "Skill name is required."
    if len(name) > MAX_NAME_LENGTH:
        return f"Skill name exceeds {MAX_NAME_LENGTH} characters."
    if not VALID_NAME_RE.match(name):
        return (
            f"Invalid skill name '{name}'. Use lowercase letters, numbers, "
            f"hyphens, dots, and underscores. Must start with a letter or digit."
        )
    return None


def _validate_category(category: Optional[str]) -> Optional[str]:
    """验证可选分类"""
    if category is None:
        return None
    if not isinstance(category, str):
        return "Category must be a string."
    
    category = category.strip()
    if not category:
        return None
    if "/" in category or "\\" in category:
        return (
            f"Invalid category '{category}'. Use lowercase letters, numbers, "
            "hyphens, dots, and underscores. Categories must be a single directory name."
        )
    if len(category) > MAX_NAME_LENGTH:
        return f"Category exceeds {MAX_NAME_LENGTH} characters."
    if not VALID_NAME_RE.match(category):
        return (
            f"Invalid category '{category}'. Use lowercase letters, numbers, "
            "hyphens, dots, and underscores."
        )
    return None


def _validate_frontmatter(content: str) -> Optional[str]:
    """验证 SKILL.md 内容包含正确的 frontmatter"""
    if not content.strip():
        return "Content cannot be empty."

    parsed, body = parse_frontmatter(content)
    if parsed == {} and not content.startswith("---"):
        return "SKILL.md must start with YAML frontmatter (---). See existing skills for format."

    if not isinstance(parsed, dict):
        return "Frontmatter must be a YAML mapping (key: value pairs)."

    if "name" not in parsed:
        return "Frontmatter must include 'name' field."
    if "description" not in parsed:
        return "Frontmatter must include 'description' field."
    if len(str(parsed["description"])) > MAX_DESCRIPTION_LENGTH:
        return f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters."

    if not body.strip():
        return "SKILL.md must have content after the frontmatter (instructions, procedures, etc.)."

    return None


def _validate_content_size(content: str, label: str = "SKILL.md") -> Optional[str]:
    """验证内容大小"""
    if len(content) > MAX_SKILL_CONTENT_CHARS:
        return (
            f"{label} content is {len(content):,} characters "
            f"(limit: {MAX_SKILL_CONTENT_CHARS:,}). "
            f"Consider splitting into a smaller SKILL.md with supporting files "
            f"in references/ or templates/."
        )
    return None


def _resolve_skill_dir(name: str, category: str = None) -> Path:
    """构建技能目录路径"""
    if category:
        return get_skills_dir() / category / name
    return get_skills_dir() / name


def _find_skill(name: str) -> Optional[Dict[str, Any]]:
    """查找技能"""
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return None
    
    # 直接在 skills 目录下查找
    skill_dir = skills_dir / name
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        return {"path": skill_dir}
    
    # 在子目录中查找
    for item in skills_dir.iterdir():
        if item.is_dir():
            skill_dir = item / name
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                return {"path": skill_dir}
    
    return None


def _validate_file_path(file_path: str) -> Optional[str]:
    """验证文件路径安全性"""
    if not file_path:
        return "file_path is required."
    
    normalized = Path(file_path)
    
    # 1. 防止路径遍历
    if ".." in str(normalized):
        return "Path traversal ('..') is not allowed."
    
    # 2. 检查绝对路径（跨平台兼容）
    if normalized.is_absolute() or str(normalized).startswith("/"):
        return "Absolute paths are not allowed. Use relative paths."
    
    # 3. 规范化后再次检查（处理编码后的 ..）
    try:
        normalized_resolved = normalized.resolve()
        if ".." in str(normalized_resolved):
            return "Path traversal detected after normalization."
    except Exception:
        pass
    
    # 4. 必须在允许的子目录下
    if not normalized.parts or normalized.parts[0] not in ALLOWED_SUBDIRS:
        allowed = ", ".join(sorted(ALLOWED_SUBDIRS))
        return f"File must be under one of: {allowed}. Got: '{file_path}'"
    
    # 5. 必须有文件名
    if len(normalized.parts) < 2:
        return f"Provide a file path, not just a directory. Example: '{normalized.parts[0]}/myfile.md'"
    
    # 6. 检查文件名安全性（防止隐藏文件）
    filename = normalized.parts[-1]
    if filename.startswith("."):
        return "Hidden files (starting with '.') are not allowed."
    
    return None


def _resolve_skill_target(skill_dir: Path, file_path: str) -> tuple[Optional[Path], Optional[str]]:
    """解析支持文件路径（带安全检查）"""
    # 先验证路径
    validation_error = _validate_file_path(file_path)
    if validation_error:
        return None, validation_error
    
    target = skill_dir / file_path
    
    # 最终安全检查：确保解析后的路径仍在 skill_dir 内
    try:
        target_resolved = target.resolve()
        skill_dir_resolved = skill_dir.resolve()
        target_resolved.relative_to(skill_dir_resolved)
    except ValueError:
        return None, "File path escapes skill directory (security violation)."
    
    return target, None


def _atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子化写入文本（委托给 common.file_utils）"""
    atomic_write_text(file_path, content, encoding)


def _create_skill(name: str, content: str, category: str = None) -> Dict[str, Any]:
    """创建新技能"""
    # 验证名称
    err = _validate_name(name)
    if err:
        return {"success": False, "error": err}
    
    err = _validate_category(category)
    if err:
        return {"success": False, "error": err}
    
    # 验证内容
    err = _validate_frontmatter(content)
    if err:
        return {"success": False, "error": err}
    
    err = _validate_content_size(content)
    if err:
        return {"success": False, "error": err}
    
    # 检查是否已存在
    existing = _find_skill(name)
    if existing:
        return {
            "success": False,
            "error": f"A skill named '{name}' already exists at {existing['path']}."
        }
    
    # 创建技能目录
    skill_dir = _resolve_skill_dir(name, category)
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入 SKILL.md
    skill_md = skill_dir / "SKILL.md"
    _atomic_write_text(skill_md, content)
    
    result = {
        "success": True,
        "message": f"Skill '{name}' created.",
        "path": str(skill_dir.relative_to(get_skills_dir())),
        "skill_md": str(skill_md),
    }
    if category:
        result["category"] = category
    result["hint"] = (
        f"To add reference files, templates, or scripts, use "
        f"skill_manage(action='write_file', name='{name}', file_path='references/example.md', file_content='...')"
    )
    return result


def _edit_skill(name: str, content: str) -> Dict[str, Any]:
    """编辑现有技能"""
    err = _validate_frontmatter(content)
    if err:
        return {"success": False, "error": err}
    
    err = _validate_content_size(content)
    if err:
        return {"success": False, "error": err}
    
    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}
    
    skill_md = existing["path"] / "SKILL.md"
    original_content = skill_md.read_text(encoding="utf-8") if skill_md.exists() else None
    
    _atomic_write_text(skill_md, content)
    
    return {
        "success": True,
        "message": f"Skill '{name}' updated.",
        "path": str(existing["path"]),
    }


def _patch_skill(
    name: str,
    old_string: str,
    new_string: str,
    file_path: str = None,
    replace_all: bool = False,
) -> Dict[str, Any]:
    """修补技能文件"""
    if not old_string:
        return {"success": False, "error": "old_string is required for 'patch'."}
    if new_string is None:
        return {"success": False, "error": "new_string is required for 'patch'. Use empty string to delete matched text."}
    
    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}
    
    skill_dir = existing["path"]
    
    if file_path:
        # 修补支持文件
        err = _validate_file_path(file_path)
        if err:
            return {"success": False, "error": err}
        target, err = _resolve_skill_target(skill_dir, file_path)
        if err:
            return {"success": False, "error": err}
    else:
        # 修补 SKILL.md
        target = skill_dir / "SKILL.md"
    
    if not target.exists():
        return {"success": False, "error": f"File not found: {target.relative_to(skill_dir)}"}
    
    content = target.read_text(encoding="utf-8")
    
    # 简单的字符串替换
    if old_string not in content:
        return {"success": False, "error": f"Could not find old_string in file. No changes made."}
    
    # 检查是否有多个匹配
    match_count = content.count(old_string)
    if match_count > 1 and not replace_all:
        return {
            "success": False,
            "error": f"Found {match_count} matches. Use replace_all=true to replace all, or provide a more specific old_string with surrounding context."
        }
    
    # 执行替换
    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)
    
    # 验证大小
    target_label = "SKILL.md" if not file_path else file_path
    err = _validate_content_size(new_content, label=target_label)
    if err:
        return {"success": False, "error": err}
    
    # 如果是 SKILL.md，验证 frontmatter 仍然有效
    if not file_path:
        err = _validate_frontmatter(new_content)
        if err:
            return {
                "success": False,
                "error": f"Patch would break SKILL.md structure: {err}"
            }
    
    original_content = content
    _atomic_write_text(target, new_content)
    
    return {
        "success": True,
        "message": f"Patched {'SKILL.md' if not file_path else file_path} in skill '{name}' ({1 if not replace_all else match_count} replacement{'s' if replace_all and match_count > 1 else ''})."
    }


def _delete_skill(name: str, absorbed_into: Optional[str] = None) -> Dict[str, Any]:
    """删除技能"""
    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}
    
    # 验证 absorbed_into
    if absorbed_into is not None and isinstance(absorbed_into, str) and absorbed_into.strip():
        target_name = absorbed_into.strip()
        if target_name == name:
            return {
                "success": False,
                "error": f"absorbed_into='{target_name}' cannot equal the skill being deleted."
            }
        target = _find_skill(target_name)
        if not target:
            return {
                "success": False,
                "error": (
                    f"absorbed_into='{target_name}' does not exist. "
                    f"Create or patch the umbrella skill first, then retry the delete."
                )
            }
    
    skill_dir = existing["path"]
    shutil.rmtree(skill_dir)
    
    # 清理空分类目录
    parent = skill_dir.parent
    if parent != get_skills_dir() and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
    
    message = f"Skill '{name}' deleted."
    if absorbed_into is not None and isinstance(absorbed_into, str) and absorbed_into.strip():
        message += f" Content absorbed into '{absorbed_into.strip()}'."
    
    return {
        "success": True,
        "message": message
    }


def _write_file(name: str, file_path: str, file_content: str) -> Dict[str, Any]:
    """写入支持文件"""
    err = _validate_file_path(file_path)
    if err:
        return {"success": False, "error": err}
    
    if file_content is None:
        return {"success": False, "error": "file_content is required."}
    
    # 检查大小
    content_bytes = len(file_content.encode("utf-8"))
    if content_bytes > MAX_SKILL_FILE_BYTES:
        return {
            "success": False,
            "error": (
                f"File content is {content_bytes:,} bytes "
                f"(limit: {MAX_SKILL_FILE_BYTES:,} bytes / 1 MiB). "
                f"Consider splitting into smaller files."
            )
        }
    err = _validate_content_size(file_content, label=file_path)
    if err:
        return {"success": False, "error": err}
    
    existing = _find_skill(name)
    if not existing:
        return {
            "success": False,
            "error": f"Skill '{name}' not found. Create it first with action='create'."
        }
    
    target, err = _resolve_skill_target(existing["path"], file_path)
    if err:
        return {"success": False, "error": err}
    
    original_content = target.read_text(encoding="utf-8") if target.exists() else None
    _atomic_write_text(target, file_content)
    
    return {
        "success": True,
        "message": f"File '{file_path}' written to skill '{name}'.",
        "path": str(target),
    }


def _remove_file(name: str, file_path: str) -> Dict[str, Any]:
    """删除支持文件"""
    err = _validate_file_path(file_path)
    if err:
        return {"success": False, "error": err}
    
    existing = _find_skill(name)
    if not existing:
        return {"success": False, "error": f"Skill '{name}' not found."}
    
    skill_dir = existing["path"]
    target, err = _resolve_skill_target(skill_dir, file_path)
    if err:
        return {"success": False, "error": err}
    
    if not target.exists():
        # 列出可用文件
        available = []
        for subdir in ALLOWED_SUBDIRS:
            d = skill_dir / subdir
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        available.append(str(f.relative_to(skill_dir)))
        return {
            "success": False,
            "error": f"File '{file_path}' not found in skill '{name}'.",
            "available_files": available if available else None
        }
    
    target.unlink()
    
    # 清理空目录
    parent = target.parent
    if parent != skill_dir and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
    
    return {
        "success": True,
        "message": f"File '{file_path}' removed from skill '{name}'."
    }


def skill_manage(
    action: str,
    name: str,
    content: str = None,
    category: str = None,
    file_path: str = None,
    file_content: str = None,
    old_string: str = None,
    new_string: str = None,
    replace_all: bool = False,
    absorbed_into: str = None,
) -> str:
    """
    技能管理工具入口函数。

    Args:
        action: 操作类型 - create, patch, edit, delete, write_file, remove_file
        name: 技能名称
        content: SKILL.md 完整内容，用于 create 和 edit
        category: 可选分类
        file_path: 支持文件路径，用于 patch, write_file, remove_file
        file_content: 文件内容，用于 write_file
        old_string: 要替换的旧字符串，用于 patch
        new_string: 新字符串，用于 patch
        replace_all: 是否替换所有匹配
        absorbed_into: 合并到的技能名称，用于 delete

    Returns:
        JSON 格式的结果字符串
    """
    if action == "create":
        if not content:
            return tool_error("content is required for 'create'. Provide the full SKILL.md text (frontmatter + body).", success=False)
        result = _create_skill(name, content, category)
    elif action == "edit":
        if not content:
            return tool_error("content is required for 'edit'. Provide the full updated SKILL.md text.", success=False)
        result = _edit_skill(name, content)
    elif action == "patch":
        if not old_string:
            return tool_error("old_string is required for 'patch'. Provide the text to find.", success=False)
        if new_string is None:
            return tool_error("new_string is required for 'patch'. Use empty string to delete matched text.", success=False)
        result = _patch_skill(name, old_string, new_string, file_path, replace_all)
    elif action == "delete":
        result = _delete_skill(name, absorbed_into=absorbed_into)
    elif action == "write_file":
        if not file_path:
            return tool_error("file_path is required for 'write_file'. Example: 'references/api-guide.md'", success=False)
        if file_content is None:
            return tool_error("file_content is required for 'write_file'.", success=False)
        result = _write_file(name, file_path, file_content)
    elif action == "remove_file":
        if not file_path:
            return tool_error("file_path is required for 'remove_file'.", success=False)
        result = _remove_file(name, file_path)
    else:
        result = {"success": False, "error": f"Unknown action '{action}'. Use: create, edit, patch, delete, write_file, remove_file"}
    
    return json.dumps(result, ensure_ascii=False)


def check_skill_requirements() -> bool:
    """技能工具无外部依赖，始终可用"""
    return True


# 工具定义
SKILL_MANAGE_SCHEMA = {
    "name": "skill_manage",
    "description": (
        "Manage skills (create, update, delete). Skills are your procedural "
        "memory — reusable approaches for recurring task types.\n\n"
        "Actions: create (full SKILL.md + optional category), "
        "patch (old_string/new_string — preferred for fixes), "
        "edit (full SKILL.md rewrite — major overhauls only), "
        "delete, write_file, remove_file.\n\n"
        "Create when: complex task succeeded (5+ calls), errors overcome, "
        "user-corrected approach worked, non-trivial workflow discovered, "
        "or user asks you to remember a procedure.\n"
        "Update when: instructions stale/wrong, OS-specific failures, "
        "missing steps or pitfalls found during use. "
        "If you used a skill and hit issues not covered by it, patch it immediately.\n\n"
        "Good skills: trigger conditions, numbered steps with exact commands, "
        "pitfalls section, verification steps. Use skill_view to see format examples."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "patch", "edit", "delete", "write_file", "remove_file"],
                "description": "The action to perform."
            },
            "name": {
                "type": "string",
                "description": "Skill name (lowercase, hyphens/underscores, max 64 chars). Must match an existing skill for patch/edit/delete/write_file/remove_file."
            },
            "content": {
                "type": "string",
                "description": "Full SKILL.md content (YAML frontmatter + markdown body). Required for 'create' and 'edit'."
            },
            "old_string": {
                "type": "string",
                "description": "Text to find in the file (required for 'patch'). Must be unique unless replace_all=true. Include enough surrounding context to ensure uniqueness."
            },
            "new_string": {
                "type": "string",
                "description": "Replacement text (required for 'patch'). Can be empty string to delete the matched text."
            },
            "replace_all": {
                "type": "boolean",
                "description": "For 'patch': replace all occurrences instead of requiring a unique match (default: false)."
            },
            "category": {
                "type": "string",
                "description": "Optional category/domain for organizing the skill (e.g., 'devops', 'data-science', 'mlops'). Creates a subdirectory grouping. Only used with 'create'."
            },
            "file_path": {
                "type": "string",
                "description": "Path to a supporting file within the skill directory. For 'write_file'/'remove_file': required, must be under references/, templates/, scripts/, or assets/. For 'patch': optional, defaults to SKILL.md if omitted."
            },
            "file_content": {
                "type": "string",
                "description": "Content for the file. Required for 'write_file'."
            },
            "absorbed_into": {
                "type": "string",
                "description": "For 'delete' only — declares intent so downstream tooling knows whether to update references. Pass the umbrella skill name when this skill's content was merged into another (the target must already exist). Pass an empty string when the skill is truly stale and being pruned with no forwarding target."
            },
        },
        "required": ["action", "name"],
    },
}


# 注册工具
registry.register(
    name="skill_manage",
    toolset="skills",
    schema=SKILL_MANAGE_SCHEMA,
    handler=lambda args, **kw: skill_manage(
        action=args.get("action", ""),
        name=args.get("name", ""),
        content=args.get("content"),
        category=args.get("category"),
        file_path=args.get("file_path"),
        file_content=args.get("file_content"),
        old_string=args.get("old_string"),
        new_string=args.get("new_string"),
        replace_all=args.get("replace_all", False),
        absorbed_into=args.get("absorbed_into"),
    ),
    check_fn=check_skill_requirements,
    emoji="📝",
)
