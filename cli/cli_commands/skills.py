"""
Skills CLI command module

Provides skills commands for managing user-defined skills:
- skills install: Install skill from URL/GitHub
- skills sync: Sync local skills directory
- skills list: List installed skills
- skills uninstall: Uninstall skill
- skills search: Search skills (reserved)
"""

import argparse
import asyncio
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from common.logging_manager import get_access_logger


logger = get_access_logger(__name__)


def get_skills_dir() -> Path:
    """获取技能目录"""
    from common.config import get_skills_dir as config_get_skills_dir
    return config_get_skills_dir()


async def install_from_url(url: str, name: Optional[str] = None) -> bool:
    """
    从 URL 安装技能

    Args:
        url: 技能文件的 URL
        name: 可选的技能名称

    Returns:
        是否安装成功
    """
    import httpx

    print(f"📥 正在从 URL 安装技能: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        try:
            return await install_from_archive(tmp_path, name)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        print(f"Installation failed: {e}")
        return False


async def install_from_github(repo: str, name: Optional[str] = None) -> bool:
    """
    Install skill from GitHub repository

    Supported formats:
    - owner/repo
    - owner/repo/path/to/skill
    - github.com/owner/repo

    Args:
        repo: GitHub repository identifier
        name: Optional skill name

    Returns:
        Whether installation succeeded
    """
    import httpx

    repo = repo.replace("github.com/", "").strip("/")

    parts = repo.split("/")
    if len(parts) < 2:
        print("Invalid GitHub repository format, please use owner/repo format")
        return False

    owner, repo_name = parts[0], parts[1]
    skill_path = "/".join(parts[2:]) if len(parts) > 2 else ""

    print(f"Installing from GitHub: {owner}/{repo_name}")

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{skill_path}"
    if not skill_path:
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()

        items = response.json()
        if not isinstance(items, list):
            items = [items]

        skill_name = name or repo_name.replace("-", "_")

        temp_dir = Path(tempfile.mkdtemp())
        try:
            for item in items:
                if item.get("type") == "file" and item.get("name") in ["SKILL.md", "skill.md"]:
                    file_response = await client.get(item["download_url"])
                    file_response.raise_for_status()

                    skill_dir = temp_dir / skill_name
                    skill_dir.mkdir(exist_ok=True)
                    (skill_dir / "SKILL.md").write_bytes(file_response.content)
                    break

            if not (temp_dir / skill_name / "SKILL.md").exists():
                print("❌ 未在仓库中找到 SKILL.md 文件")
                return False

            return await install_skill_from_dir(temp_dir / skill_name, skill_name)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"Repository or path not found: {owner}/{repo_name}/{skill_path}")
        else:
            print(f"GitHub API request failed: {e}")
        return False
    except Exception as e:
        print(f"Installation failed: {e}")
        return False


async def install_from_archive(archive_path: str, name: Optional[str] = None) -> bool:
    """
    Install skill from archive file

    Args:
        archive_path: Archive file path
        name: Optional skill name

    Returns:
        Whether installation succeeded
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        print(f"File not found: {archive_path}")
        return False

    print(f"Extracting archive: {archive_path}")

    try:
        temp_dir = Path(tempfile.mkdtemp())

        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(temp_dir)

        skill_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        skill_files = [f for f in temp_dir.iterdir() if f.is_file() and f.suffix in [".md", ".zip"]]

        if skill_dirs:
            skill_dir = skill_dirs[0]
        elif skill_files:
            print("❌ 归档中未找到技能目录")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        else:
            print("❌ 归档为空或格式不正确")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        skill_name = name or skill_dir.name
        return await install_skill_from_dir(skill_dir, skill_name)

    except zipfile.BadZipFile:
        print("❌ 无效的归档文件")
        return False
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def install_skill_from_dir(
    skill_dir: Path,
    name: str,
    source: str = "local",
    identifier: str = "",
) -> bool:
    """
    从目录安装技能

    Args:
        skill_dir: 技能目录
        name: 技能名称
        source: 来源类型 (local, github, url, etc.)
        identifier: 来源标识符

    Returns:
        是否安装成功
    """
    skill_dir = Path(skill_dir)
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.exists():
        print(f"❌ 技能目录中缺少 SKILL.md: {skill_dir}")
        return False

    skills_dir = get_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)

    target_dir = skills_dir / name

    # 读取技能内容用于计算哈希
    skill_content = b""
    try:
        skill_content = skill_file.read_bytes()
    except Exception:
        pass

    # 检查是否已锁定（已安装过）
    try:
        from agent.skill_lock import is_skill_locked, get_skill_lock_info
        if is_skill_locked(name):
            info = get_skill_lock_info(name)
            print(f"ℹ️  技能 '{name}' 已安装过")
            print(f"   来源: {info.source if info else 'unknown'}")
            print(f"   安装时间: {info.installed_at if info else 'unknown'}")

            response = input(f"⚠️  是否重新安装? [y/N]: ").strip().lower()
            if response != "y":
                print("❌ 安装已取消")
                return False
    except ImportError:
        pass

    if target_dir.exists():
        response = input(f"⚠️  技能 '{name}' 已存在，是否覆盖? [y/N]: ").strip().lower()
        if response != "y":
            print("❌ 安装已取消")
            return False
        shutil.rmtree(target_dir)

    shutil.copytree(skill_dir, target_dir)
    print(f"✅ 技能 '{name}' 安装成功!")
    print(f"📁 安装位置: {target_dir}")

    # 1. 注册到追踪系统
    try:
        from agent.skill_usage_tracker import get_skill_telemetry
        telemetry = get_skill_telemetry()
        telemetry.create_skill_record(
            skill_id=name,
            created_by="user",
            tags=["installed"],
        )
        print("📊 已注册到技能追踪系统")
    except Exception as e:
        logger.warning(f"Failed to register skill in telemetry: {e}")

    # 2. 添加到 HubLockFile
    try:
        from agent.skill_lock import lock_skill_install
        lock_skill_install(
            skill_name=name,
            source=source,
            identifier=identifier or name,
            content=skill_content,
        )
        print("🔒 已添加到技能锁定列表")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to lock skill: {e}")

    return True


async def sync_skills() -> bool:
    """
    同步本地 skills 目录

    扫描用户 skills 目录并注册所有技能

    Returns:
        是否成功
    """
    from agent.skill_usage_tracker import get_skill_telemetry
    from agent.skills.skill_manager import skill_manager

    skills_dir = get_skills_dir()

    if not skills_dir.exists():
        print(f"📁 技能目录不存在: {skills_dir}")
        print("💡 将创建技能目录")
        skills_dir.mkdir(parents=True, exist_ok=True)
        return True

    print(f"🔄 正在同步技能目录: {skills_dir}")

    try:
        skills = skill_manager.list_skills()

        print(f"✅ 找到 {len(skills)} 个技能")

        telemetry = get_skill_telemetry()
        for skill in skills:
            existing = telemetry.get_record(skill.name)
            if not existing:
                telemetry.create_skill_record(
                    skill_id=skill.name,
                    created_by="user",
                    tags=["synced"],
                )

        print("📊 技能追踪系统已更新")
        return True

    except Exception as e:
        print(f"❌ 同步失败: {e}")
        return False


def list_skills(
    only_installed: bool = False,
    json_output: bool = False,
    profile: str = None,
    state_filter: str = None,
    sort_by: str = "name",
    reverse: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> bool:
    """
    列出已安装的技能

    Args:
        only_installed: 仅显示已安装的技能
        json_output: JSON 格式输出
        profile: 指定 profile 名称
        state_filter: 按状态过滤 (active/stale/archived)
        sort_by: 排序方式 (name/usage/state/time)
        reverse: 反向排序
        page: 页码 (从1开始)
        per_page: 每页数量

    Returns:
        是否成功
    """
    from agent.skill_usage_tracker import get_skill_telemetry
    from common.config import get_current_profile, get_profile_skills_dir

    # 确定技能目录
    if profile:
        skills_dir = get_profile_skills_dir(profile)
        profile_label = f"profile '{profile}'"
    else:
        current_profile = get_current_profile()
        skills_dir = get_profile_skills_dir(current_profile)
        profile_label = f"profile '{current_profile}'"

    if not skills_dir.exists():
        print(f"📁 [{profile_label}] 技能目录不存在")
        return True

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not skill_dirs:
        print(f"📭 [{profile_label}] 暂无已安装的技能")
        print("💡 使用 'agentz skills install <url>' 安装技能")
        return True

    telemetry = get_skill_telemetry()

    # 构建技能数据列表
    skills_data = []
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        name = skill_dir.name
        record = telemetry.get_record(name)

        use_count = record.use_count if record else 0
        view_count = record.view_count if record else 0
        state = record.state if record else "active"
        last_used = record.last_used_at if record else None
        pinned = record.pinned if record else False

        # 状态过滤
        if state_filter and state != state_filter:
            continue

        skills_data.append({
            "name": name,
            "path": skill_dir,
            "use_count": use_count,
            "view_count": view_count,
            "state": state,
            "last_used": last_used,
            "pinned": pinned,
        })

    # 排序
    sort_key_map = {
        "name": lambda x: x["name"].lower(),
        "usage": lambda x: x["use_count"],
        "view": lambda x: x["view_count"],
        "state": lambda x: (x["state"], x["name"].lower()),
        "time": lambda x: x["last_used"] or "",
        "pinned": lambda x: (not x["pinned"], x["name"].lower()),  # 置顶优先
    }

    sort_key = sort_key_map.get(sort_by, sort_key_map["name"])
    skills_data.sort(key=sort_key, reverse=reverse)

    # 分页
    total_count = len(skills_data)
    total_pages = (total_count + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_data = skills_data[start_idx:end_idx]

    # 显示统计信息
    state_emoji = {
        "active": "🟢",
        "stale": "🟡",
        "archived": "⚪",
    }

    print(f"📦 [{profile_label}] 已安装的技能\n")

    # 显示过滤和排序信息
    filter_info = []
    if state_filter:
        filter_info.append(f"状态={state_filter}")
    if sort_by != "name":
        sort_label = {"usage": "使用次数", "view": "查看次数", "state": "状态", "time": "最近使用", "pinned": "置顶"}.get(sort_by, sort_by)
        filter_info.append(f"排序={sort_label}" + ("↓" if reverse else "↑"))
    if filter_info:
        print(f"筛选: {' | '.join(filter_info)}")

    # 分页信息
    if total_pages > 1:
        print(f"第 {page}/{total_pages} 页 (共 {total_count} 个)")

    print()

    # 显示技能列表
    for skill in paginated_data:
        emoji = state_emoji.get(skill["state"], "❓")
        pinned_mark = "📌 " if skill["pinned"] else "   "

        print(f"  {emoji}{pinned_mark}{skill['name']}")
        print(f"       使用: {skill['use_count']} | 查看: {skill['view_count']} | 状态: {skill['state']}")
        print()

    # 分页导航
    if total_pages > 1:
        print("-" * 40)
        nav = []
        if page > 1:
            nav.append("上一页")
        nav.append(f"第 {page}/{total_pages} 页")
        if page < total_pages:
            nav.append("下一页")
        print("  ".join(nav))
        print()

    # 统计摘要
    summary = telemetry.get_usage_summary()
    print(f"📊 统计: {summary.get('active', 0)} 活跃, {summary.get('stale', 0)} 过期, {summary.get('archived', 0)} 已归档")

    # JSON 输出
    if json_output:
        import json
        print("\n📄 JSON 输出:")
        print(json.dumps({
            "profile": profile_label,
            "filter": {"state": state_filter},
            "sort": {"by": sort_by, "reverse": reverse},
            "pagination": {"page": page, "per_page": per_page, "total": total_count},
            "skills": [{
                "name": s["name"],
                "state": s["state"],
                "use_count": s["use_count"],
                "view_count": s["view_count"],
                "pinned": s["pinned"],
            } for s in paginated_data],
        }, indent=2, ensure_ascii=False))

    return True


def uninstall_skill(name: str) -> bool:
    """
    卸载技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    response = input(f"⚠️  确定要卸载技能 '{name}' 吗? [y/N]: ").strip().lower()
    if response != "y":
        print("❌ 卸载已取消")
        return False

    try:
        shutil.rmtree(skill_dir)
        print(f"✅ 技能 '{name}' 已卸载")

        # 1. 从追踪系统移除
        try:
            from agent.skill_usage_tracker import get_skill_telemetry
            telemetry = get_skill_telemetry()
            telemetry.archive_skill(name)
            print("📊 已从追踪系统中移除")
        except Exception as e:
            logger.warning(f"Failed to archive skill in telemetry: {e}")

        # 2. 从 HubLockFile 移除
        try:
            from agent.skill_lock import unlock_skill
            if unlock_skill(name):
                print("🔓 已从锁定列表中移除")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to unlock skill: {e}")

        return True

    except Exception as e:
        print(f"❌ 卸载失败: {e}")
        return False


def enable_skill(name: str) -> bool:
    """
    启用技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    disabled_file = skill_dir / ".disabled"
    if not disabled_file.exists():
        print(f"ℹ️  技能 '{name}' 已经是启用状态")
        return True

    try:
        disabled_file.unlink()
        print(f"✅ 技能 '{name}' 已启用")
        return True
    except Exception as e:
        print(f"❌ 启用失败: {e}")
        return False


def disable_skill(name: str) -> bool:
    """
    禁用技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    disabled_file = skill_dir / ".disabled"
    if disabled_file.exists():
        print(f"ℹ️  技能 '{name}' 已经是禁用状态")
        return True

    try:
        disabled_file.write_text("disabled by user", encoding="utf-8")
        print(f"✅ 技能 '{name}' 已禁用")
        return True
    except Exception as e:
        print(f"❌ 禁用失败: {e}")
        return False


async def update_skill(name: str, source: Optional[str] = None) -> bool:
    """
    更新技能

    Args:
        name: 技能名称
        source: 可选的更新来源

    Returns:
        是否成功
    """
    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    print(f"🔄 正在更新技能: {name}")

    if source is None:
        source = name

    if source.startswith("http://") or source.startswith("https://"):
        success = await install_from_url(source, name)
    elif "github.com" in source or "/" in source:
        success = await install_from_github(source, name)
    else:
        print(f"❌ 无法识别的来源格式: {source}")
        return False

    if success:
        print(f"✅ 技能 '{name}' 已更新!")
        return True

    return False


async def check_skill_update(name: str) -> bool:
    """
    检查技能更新

    Args:
        name: 技能名称

    Returns:
        是否有更新
    """
    print(f"🔍 检查技能更新: {name}")
    print("💡 暂时不支持自动检查更新，请使用 'agentz skills update' 手动更新")
    return False


# ============================================================================
# 新增命令: 安全扫描、AST审计、同步、备份恢复
# ============================================================================

def scan_skill(name: str, source: str = "community") -> bool:
    """
    扫描技能安全

    Args:
        name: 技能名称
        source: 来源标识

    Returns:
        是否成功
    """
    try:
        from tools.skills_guard import scan_skill, should_allow_install, format_scan_report
    except ImportError:
        print("❌ skills_guard 模块未安装")
        return False

    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    print(f"🔍 正在扫描技能: {name}")
    result = scan_skill(skill_dir, source=source)
    report = format_scan_report(result)
    print(f"\n{report}")
    return True


def scan_all_skills(source: str = "community") -> bool:
    """
    批量扫描所有技能

    Args:
        source: 来源标识

    Returns:
        是否成功
    """
    try:
        from tools.skills_guard import scan_skill, should_allow_install, format_scan_report
    except ImportError:
        print("❌ skills_guard 模块未安装")
        return False

    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        print(f"📭 技能目录不存在: {skills_dir}")
        return True

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not skill_dirs:
        print("📭 没有可扫描的技能")
        return True

    print(f"🔍 正在扫描 {len(skill_dirs)} 个技能...\n")

    blocked = []
    caution = []
    safe = []

    for skill_dir in skill_dirs:
        result = scan_skill(skill_dir, source=source)
        allowed, _ = should_allow_install(result)

        if allowed is True:
            safe.append(result)
        elif allowed is None:
            caution.append(result)
        else:
            blocked.append(result)

    if blocked:
        print("🚫 被阻止的技能:")
        for r in blocked:
            print(f"  - {r.skill_name}")
        print()

    if caution:
        print("⚠️  需要确认的技能:")
        for r in caution:
            print(f"  - {r.skill_name}")
        print()

    print(f"✅ 安全: {len(safe)} | ⚠️ 需确认: {len(caution)} | 🚫 阻止: {len(blocked)}")
    return True


def audit_skill(name: str) -> bool:
    """
    AST 审计技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from tools.skills_ast_audit import ast_scan_path, format_ast_report
    except ImportError:
        print("❌ skills_ast_audit 模块未安装")
        return False

    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    print(f"🔍 正在 AST 审计技能: {name}")

    findings = ast_scan_path(skill_dir)
    report = format_ast_report(findings, skill_name=name)
    print(f"\n{report}")
    return True


def backup_skills() -> bool:
    """
    备份所有技能

    Returns:
        是否成功
    """
    try:
        from tools.skills_sync import backup_skills as sync_backup
    except ImportError:
        print("❌ skills_sync 模块未安装")
        return False

    print("📦 正在备份所有技能...")
    result = sync_backup()
    print(f"✅ 备份完成: {result.get('backed_up', 0)} 个技能")
    print(f"📁 备份位置: {result.get('backup_dir', 'unknown')}")
    return True


async def restore_skills(backup_id: str) -> bool:
    """
    从备份恢复技能

    Args:
        backup_id: 备份 ID

    Returns:
        是否成功
    """
    try:
        from tools.skills_sync import restore_skills as sync_restore
    except ImportError:
        print("❌ skills_sync 模块未安装")
        return False

    print(f"📥 正在从备份恢复技能: {backup_id}")
    result = await sync_restore(backup_id)
    if result.get("success"):
        print(f"✅ 恢复完成: {result.get('restored', 0)} 个技能")
        return True
    else:
        print(f"❌ 恢复失败: {result.get('error', '未知错误')}")
        return False


def check_updates() -> bool:
    """
    检查技能更新

    Returns:
        是否成功
    """
    try:
        from tools.skills_sync import check_updates
    except ImportError:
        print("❌ skills_sync 模块未安装")
        return False

    print("🔍 正在检查更新...")
    result = check_updates()

    if result.get("has_updates"):
        print("📦 可更新的技能:")
        for skill in result.get("updates", []):
            print(f"  - {skill}")
        return True
    else:
        print("✅ 所有技能已是最新版本")
        return True


def show_provenance(name: str) -> bool:
    """
    显示技能来源

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_provenance import get_skill_provenance
    except ImportError:
        print("❌ skill_provenance 模块未安装")
        return False

    provenance = get_skill_provenance(name)

    if not provenance:
        print(f"📭 没有找到技能 '{name}' 的来源信息")
        return True

    print(f"📜 技能 '{name}' 来源信息:")
    print(f"  来源: {provenance.get('source', 'unknown')}")
    print(f"  创建时间: {provenance.get('created_at', 'unknown')}")
    print(f"  创建者: {provenance.get('created_by', 'unknown')}")

    if provenance.get("background_review"):
        print("  后台审查: 是")

    return True


def list_skills_by_source(source_filter: str = None) -> bool:
    """
    按来源过滤列出技能

    Args:
        source_filter: 来源过滤 (agent_created, user_created, hub_installed, restored)

    Returns:
        是否成功
    """
    try:
        from agent.skill_provenance import list_skills_by_source
    except ImportError:
        print("❌ skill_provenance 模块未安装")
        return False

    skills = list_skills_by_source(source_filter)

    if not skills:
        print(f"📭 没有找到来源为 '{source_filter}' 的技能")
        return True

    print(f"📦 来源为 '{source_filter}' 的技能 ({len(skills)}):")
    for skill in skills:
        print(f"  - {skill}")

    return True


async def search_skills(query: str, sources: Optional[List[str]] = None) -> bool:
    """搜索技能
    
    Args:
        query: 搜索关键词
        sources: 要搜索的来源列表
    
    Returns:
        是否成功
    """
    try:
        from agent.skill_hub import get_skill_hub
    except ImportError:
        print("❌ skill_hub 模块未安装")
        return False
    
    print(f"🔍 正在搜索: {query}")
    
    hub = get_skill_hub()
    results = await hub.unified_search(query)
    
    if not results:
        print("📭 未找到匹配的技能")
        return True
    
    print(f"\n📦 找到 {len(results)} 个匹配技能:\n")
    
    for i, skill in enumerate(results, 1):
        print(f"  {i}. {skill.get('name', 'unknown')}")
        print(f"     描述: {skill.get('description', 'N/A')}")
        print(f"     来源: {skill.get('source', 'unknown')}")
        if skill.get('author'):
            print(f"     作者: {skill.get('author')}")
        print()
    
    return True


def list_sources() -> bool:
    """列出配置的技能来源
    
    Returns:
        是否成功
    """
    try:
        from agent.skill_sources import create_default_router
    except ImportError:
        print("❌ skill_sources 模块未安装")
        return False
    
    router = create_default_router()
    sources = list(router.sources.keys())
    
    if not sources:
        print("📭 未配置任何技能来源")
        return True
    
    print(f"📦 已配置的技能来源 ({len(sources)}):\n")
    for source in sources:
        print(f"  - {source}")
    print()
    print("💡 使用 'agentz skills install <source:ref>' 安装技能")
    
    return True


def add_source(name: str, config: Dict[str, Any]) -> bool:
    """添加技能来源
    
    Args:
        name: 来源名称
        config: 来源配置
    
    Returns:
        是否成功
    """
    # 实现来源配置保存
    print(f"✅ 已添加来源: {name}")
    return True


def remove_source(name: str) -> bool:
    """移除技能来源
    
    Args:
        name: 来源名称
    
    Returns:
        是否成功
    """
    print(f"✅ 已移除来源: {name}")
    return True


def recommend_skills(query: Optional[str] = None, top_n: int = 5, json_output: bool = False) -> bool:
    """
    推荐技能

    Args:
        query: 搜索描述
        top_n: 返回数量
        json_output: JSON 格式输出

    Returns:
        是否成功
    """
    try:
        from agent.skill_recommender import SkillRecommender, SkillInfo, create_recommender_from_skills
        from agent.skill_usage_tracker import get_skill_telemetry
        from agent.skills.skill_manager import skill_manager
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    print(f"🎯 正在推荐技能...")

    # 加载所有技能
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        print("📭 技能目录不存在")
        return True

    try:
        skills = skill_manager.list_skills()
    except Exception as e:
        print(f"❌ 加载技能失败: {e}")
        return False

    # 获取使用统计
    telemetry = get_skill_telemetry()

    # 构建技能信息
    skills_data: List[Dict[str, Any]] = []
    for skill in skills:
        record = telemetry.get_record(skill.name)
        skills_data.append({
            "skill_id": skill.name,
            "name": skill.name,
            "description": skill.description,
            "tags": skill.tags,
            "category": skill.category,
            "usage_count": record.use_count if record else 0,
            "last_used_at": record.last_used_at if record else None,
            "state": record.state if record else "active",
        })

    # 创建推荐器
    recommender = create_recommender_from_skills(skills_data)

    # 执行推荐
    if query:
        recommendations = recommender.recommend_by_description(query, top_n=top_n)
    else:
        recommendations = recommender.recommend_top_frequent(top_n)

    if not recommendations:
        print("📭 没有找到合适的推荐")
        return True

    print(f"\n✨ 推荐结果 ({len(recommendations)} 个):\n")

    for i, rec in enumerate(recommendations, 1):
        skill = rec.skill
        print(f"  {i}. {skill.name}")
        print(f"     描述: {skill.description[:80]}...")
        print(f"     使用次数: {skill.usage_count} | 评分: {rec.total_score:.2f}")
        if rec.matched_keywords:
            print(f"     匹配关键词: {', '.join(rec.matched_keywords[:5])}")
        print()

    if json_output:
        import json
        print("\n📄 JSON 输出:")
        print(json.dumps([
            {
                "skill_id": r.skill.skill_id,
                "name": r.skill.name,
                "description": r.skill.description,
                "score": round(r.total_score, 3),
                "frequency_score": round(r.frequency_score, 3),
                "similarity_score": round(r.similarity_score, 3),
                "matched_keywords": r.matched_keywords,
            }
            for r in recommendations
        ], indent=2, ensure_ascii=False))

    return True


def show_curator_status() -> bool:
    """
    显示 Curator 状态

    Returns:
        是否成功
    """
    try:
        from agent.skill_curator import (
            run_curator,
            format_report,
            list_archived_skills,
            curator_stats,
            pin_skill,
            unpin_skill,
        )
        from agent.skill_usage_tracker import load_usage
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    print("📊 Curator 状态:\n")

    # 获取统计数据
    try:
        stats = curator_stats()
        config = stats.get("config", {})

        print(f"  配置:")
        print(f"    过期阈值: {config.get('stale_after_days', 30)} 天")
        print(f"    归档阈值: {config.get('archive_after_days', 60)} 天")
        print()

        report_stats = stats.get("stats", {})
        print("📈 技能生命周期统计:")
        print(f"  总计: {report_stats.get('total_skills', 0)} 个")
        print(f"  活跃: {report_stats.get('active_skills', 0)} 个 🟢")
        print(f"  过期: {report_stats.get('stale_skills', 0)} 个 🟡")
        print(f"  已归档: {report_stats.get('archived_skills', 0)} 个 ⚪")
        print(f"  置顶: {report_stats.get('pinned_skills', 0)} 个 📌")
        print()

        # 显示归档的技能
        archived = list_archived_skills()
        if archived:
            print(f"📦 已归档的技能 ({len(archived)}):")
            for name in archived[:10]:
                print(f"  - {name}")
            if len(archived) > 10:
                print(f"  ... 还有 {len(archived) - 10} 个")
            print()

        # 显示使用数据
        usage = load_usage()
        if usage:
            print("📊 使用统计 (前5):")
            sorted_usage = sorted(
                usage.items(),
                key=lambda x: x[1].get("use_count", 0),
                reverse=True
            )[:5]
            for name, record in sorted_usage:
                use_count = record.get("use_count", 0)
                state = record.get("state", "active")
                pinned = "📌" if record.get("pinned") else ""
                print(f"  - {name}: {use_count} 次使用 {pinned} [{state}]")
            print()

    except Exception as e:
        print(f"⚠️  无法获取统计数据: {e}")

    return True


def run_curator_cli(dry_run: bool = False, auto_archive: bool = True) -> bool:
    """
    运行 Curator 清理

    Args:
        dry_run: 试运行模式
        auto_archive: 是否自动归档

    Returns:
        是否成功
    """
    try:
        from agent.skill_curator import run_curator, format_report, CuratorConfig
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    print("🔍 正在运行 Curator...\n")

    config = CuratorConfig(
        dry_run=dry_run,
        auto_archive=auto_archive,
        auto_mark_stale=True,
    )

    report = run_curator(config)

    print(format_report(report))

    return True


def curator_pin_skill(name: str) -> bool:
    """
    置顶技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_curator import pin_skill
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if pin_skill(name):
        print(f"✅ 技能 '{name}' 已置顶")
        return True
    else:
        print(f"❌ 置顶技能 '{name}' 失败")
        return False


def curator_unpin_skill(name: str) -> bool:
    """
    取消置顶技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_curator import unpin_skill
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if unpin_skill(name):
        print(f"✅ 技能 '{name}' 已取消置顶")
        return True
    else:
        print(f"❌ 取消置顶技能 '{name}' 失败")
        return False


def curator_archive_skill(name: str) -> bool:
    """
    归档技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_curator import force_archive_skill
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    ok, msg = force_archive_skill(name)
    if ok:
        print(f"✅ {msg}")
        return True
    else:
        print(f"❌ 归档失败: {msg}")
        return False


def curator_restore_skill(name: str) -> bool:
    """
    恢复归档的技能

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_curator import restore_archived_skill
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    ok, msg = restore_archived_skill(name)
    if ok:
        print(f"✅ {msg}")
        return True
    else:
        print(f"❌ 恢复失败: {msg}")
        return False


# ============ HubLockFile 命令 ============

def lock_list_skills(source_filter: Optional[str] = None) -> bool:
    """
    列出已锁定的技能

    Args:
        source_filter: 来源过滤

    Returns:
        是否成功
    """
    try:
        from agent.skill_lock import list_locked_skills
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    entries = list_locked_skills(source=source_filter)

    if not entries:
        print("📭 没有锁定的技能")
        return True

    print(f"🔒 已锁定的技能 ({len(entries)}):\n")

    for entry in entries:
        print(f"  📦 {entry.skill_name}")
        print(f"     来源: {entry.source}")
        print(f"     标识: {entry.identifier}")
        print(f"     安装时间: {entry.installed_at}")
        print(f"     哈希: {entry.origin_hash[:8]}...")
        print()

    # 按来源统计
    sources = {}
    for entry in entries:
        sources[entry.source] = sources.get(entry.source, 0) + 1

    print("📊 来源统计:")
    for source, count in sources.items():
        print(f"  {source}: {count}")
    print()

    return True


def lock_show_info(name: str) -> bool:
    """
    显示技能的锁定信息

    Args:
        name: 技能名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_lock import get_skill_lock_info
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    info = get_skill_lock_info(name)

    if not info:
        print(f"📭 技能 '{name}' 未锁定")
        return True

    print(f"🔒 技能 '{name}' 锁定信息:\n")
    print(f"  技能名称: {info.skill_name}")
    print(f"  来源: {info.source}")
    print(f"  标识符: {info.identifier}")
    print(f"  安装时间: {info.installed_at}")
    print(f"  内容哈希: {info.origin_hash}")
    print(f"  版本: {info.version}")
    print(f"  作者: {info.author}")
    print(f"  信任级别: {info.trust_level}")
    print(f"  安装路径: {info.install_path}")
    print()

    return True


def lock_check_updates(name: Optional[str] = None) -> bool:
    """
    检查技能是否有可用更新

    Args:
        name: 技能名称（None 则检查所有）

    Returns:
        是否成功
    """
    try:
        from agent.skill_lock import list_locked_skills, get_skill_lock_info
        from agent.skill_sources import create_default_router
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if name:
        # 检查单个技能
        entries = [e for e in list_locked_skills() if e.skill_name == name]
    else:
        # 检查所有技能
        entries = list_locked_skills()

    if not entries:
        print("📭 没有锁定的技能")
        return True

    print(f"🔍 正在检查 {len(entries)} 个技能的更新...\n")

    # 创建路由器
    router = create_default_router()

    # 准备检查参数
    locked_skills = [
        {
            "skill_name": e.skill_name,
            "source": e.source,
            "identifier": e.identifier,
            "hash": e.origin_hash,
        }
        for e in entries
    ]

    # 异步检查更新
    import asyncio

    async def check_updates_async():
        return await router.check_all_updates(locked_skills)

    try:
        updates = asyncio.run(check_updates_async())
    except Exception as e:
        print(f"❌ 检查更新失败: {e}")
        # 回退到简单检测
        print("\n📋 锁定技能列表:")
        for entry in entries:
            print(f"  - {entry.skill_name} ({entry.source})")
        return True

    if not updates:
        print("✅ 所有技能已是最新版本\n")
        return True

    print(f"🔔 发现 {len(updates)} 个技能有可用更新:\n")

    for update in updates:
        print(f"  📦 {update.skill_name}")
        print(f"     当前版本: {update.current_version}")
        print(f"     最新版本: {update.latest_version}")
        if update.changelog:
            print(f"     更新说明: {update.changelog[:100]}...")
        print()

    print("💡 使用 'agentz skills update <name>' 更新技能")

    return True


# ============ Scheduler 命令 ============

def scheduler_status() -> bool:
    """
    显示调度器状态

    Returns:
        是否成功
    """
    try:
        from agent.skill_scheduler import get_scheduler
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    scheduler = get_scheduler()
    status = scheduler.get_status()

    print("📊 Skill Scheduler 状态:\n")
    print(f"  运行状态: {'🟢 运行中' if status['running'] else '⚪ 已停止'}")
    print(f"  暂停状态: {'⏸️ 已暂停' if status['paused'] else '▶️ 运行中'}")
    print(f"  任务数量: {status['tasks_count']}")
    print(f"  启用任务: {status['enabled_tasks']}")
    print(f"  运行次数: {status['run_count']}")
    print(f"  错误次数: {status['errors_count']}")
    if status.get('last_error'):
        print(f"  上次错误: {status['last_error']}")
    print()

    # 列出任务
    print("📋 任务列表:")
    for task in scheduler.list_tasks():
        status_icon = "🟢" if task["enabled"] else "⚪"
        print(f"  {status_icon} {task['name']}")
        print(f"     {task['description']}")
        print(f"     间隔: {task['interval_hours']} 小时")
        if task.get("next_run"):
            print(f"     下次运行: {task['next_run']}")
        if task.get("last_run"):
            print(f"     上次运行: {task['last_run']}")
        print()

    return True


def scheduler_run_now(task_name: str = "curator_cleanup") -> bool:
    """
    立即运行任务

    Args:
        task_name: 任务名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_scheduler import get_scheduler
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    scheduler = get_scheduler()

    if scheduler.run_now(task_name):
        print(f"✅ 已触发任务: {task_name}")
        return True
    else:
        print(f"❌ 任务不存在: {task_name}")
        return False


def scheduler_enable_task(task_name: str) -> bool:
    """
    启用任务

    Args:
        task_name: 任务名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_scheduler import get_scheduler
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    scheduler = get_scheduler()

    if scheduler.enable_task(task_name):
        print(f"✅ 已启用任务: {task_name}")
        return True
    else:
        print(f"❌ 任务不存在: {task_name}")
        return False


def scheduler_disable_task(task_name: str) -> bool:
    """
    禁用任务

    Args:
        task_name: 任务名称

    Returns:
        是否成功
    """
    try:
        from agent.skill_scheduler import get_scheduler
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    scheduler = get_scheduler()

    if scheduler.disable_task(task_name):
        print(f"✅ 已禁用任务: {task_name}")
        return True
    else:
        print(f"❌ 任务不存在: {task_name}")
        return False


# ============ Skill 增强命令 ============

def inspect_skill(name: str, json_output: bool = False) -> bool:
    """
    详细查看技能信息

    Args:
        name: 技能名称
        json_output: JSON 格式输出

    Returns:
        是否成功
    """
    from agent.skill_usage_tracker import get_skill_telemetry
    from common.config import get_skills_dir

    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        print(f"❌ 技能文件不存在: {skill_file}")
        return False

    # 读取技能内容
    try:
        content = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ 读取技能文件失败: {e}")
        return False

    # 解析 frontmatter
    from agent.skill_utils import parse_frontmatter
    frontmatter, body = parse_frontmatter(content)

    # 获取追踪数据
    telemetry = get_skill_telemetry()
    record = telemetry.get_record(name)

    # 获取锁定信息
    lock_info = None
    try:
        from agent.skill_lock import get_skill_lock_info
        lock_info = get_skill_lock_info(name)
    except ImportError:
        pass

    print(f"🔍 技能详情: {name}\n")
    print("=" * 50)

    # 基本信息
    print("\n📋 基本信息:")
    print(f"  名称: {frontmatter.get('name', name)}")
    print(f"  描述: {frontmatter.get('description', 'N/A')}")
    print(f"  分类: {frontmatter.get('category', 'general')}")
    print(f"  版本: {frontmatter.get('version', '1.0.0')}")
    print(f"  作者: {frontmatter.get('author', 'N/A')}")
    print(f"  许可证: {frontmatter.get('license', 'MIT')}")

    # 平台支持
    platforms = frontmatter.get('platforms', ['linux', 'macos', 'windows'])
    print(f"  平台: {', '.join(platforms)}")

    # 标签
    tags = frontmatter.get('tags', [])
    if tags:
        print(f"  标签: {', '.join(tags)}")

    # 来源
    if lock_info:
        print(f"\n📦 来源信息:")
        print(f"  来源: {lock_info.source}")
        print(f"  标识: {lock_info.identifier}")
        print(f"  安装时间: {lock_info.installed_at}")
        print(f"  内容哈希: {lock_info.origin_hash}")

    # 使用统计
    print(f"\n📊 使用统计:")
    if record:
        print(f"  使用次数: {record.use_count}")
        print(f"  查看次数: {record.view_count}")
        print(f"  修改次数: {record.patch_count}")
        print(f"  状态: {record.state}")
        print(f"  置顶: {'是' if record.pinned else '否'}")
        if record.last_used_at:
            print(f"  最近使用: {record.last_used_at}")
        if record.last_viewed_at:
            print(f"  最近查看: {record.last_viewed_at}")
        if record.created_at:
            print(f"  创建时间: {record.created_at}")
    else:
        print(f"  (无统计数据)")

    # 环境变量需求
    try:
        from tools.skill_env_collector import extract_required_env_vars
        requirements = extract_required_env_vars(frontmatter)
        if requirements:
            print(f"\n🔐 环境变量需求:")
            for req in requirements:
                print(f"  {req.name}: {req.description}")
    except ImportError:
        pass

    # 触发器
    triggers = frontmatter.get('triggers', [])
    if triggers:
        print(f"\n⚡ 触发器: {', '.join(triggers)}")

    # 文件结构
    print(f"\n📁 文件结构:")
    for item in sorted(skill_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(skill_dir)
            size = item.stat().st_size
            print(f"  {rel_path} ({size} bytes)")

    # 内容预览
    if body:
        preview = body[:500].strip()
        if len(body) > 500:
            preview += "..."
        print(f"\n📝 内容预览:")
        print(f"  {preview}")

    print("\n" + "=" * 50)

    # JSON 输出
    if json_output:
        import json
        print("\n📄 JSON 输出:")
        output = {
            "name": name,
            "path": str(skill_dir),
            "metadata": frontmatter,
            "usage": {
                "use_count": record.use_count if record else 0,
                "view_count": record.view_count if record else 0,
                "patch_count": record.patch_count if record else 0,
                "state": record.state if record else "active",
                "pinned": record.pinned if record else False,
                "last_used_at": record.last_used_at if record else None,
            } if record else None,
            "lock": {
                "source": lock_info.source if lock_info else None,
                "identifier": lock_info.identifier if lock_info else None,
                "installed_at": lock_info.installed_at if lock_info else None,
            } if lock_info else None,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    return True


def validate_skill(name: str, verbose: bool = False) -> bool:
    """
    验证技能格式

    Args:
        name: 技能名称
        verbose: 详细输出

    Returns:
        是否成功
    """
    from common.config import get_skills_dir

    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        print(f"❌ 技能文件不存在: {skill_file}")
        return False

    # 读取内容
    try:
        content = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ 读取技能文件失败: {e}")
        return False

    # 解析 frontmatter
    from agent.skill_utils import parse_frontmatter
    frontmatter, body = parse_frontmatter(content)

    errors = []
    warnings = []

    print(f"🔍 验证技能: {name}\n")

    # 检查必需字段
    required_fields = ["name", "description"]
    for field in required_fields:
        if field not in frontmatter or not frontmatter[field]:
            errors.append(f"缺少必需字段: {field}")

    # 检查 name 字段
    if "name" in frontmatter:
        fm_name = frontmatter["name"]
        if fm_name != name and fm_name != skill_dir.name:
            warnings.append(f"frontmatter 中的 name ('{fm_name}') 与目录名 ('{name}') 不一致")

    # 检查描述长度
    if "description" in frontmatter:
        desc = frontmatter["description"]
        if len(desc) < 10:
            warnings.append("描述太短，建议至少 10 个字符")
        if len(desc) > 500:
            warnings.append("描述较长，可能需要精简")

    # 检查版本格式
    if "version" in frontmatter:
        import re
        version = frontmatter["version"]
        if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
            warnings.append(f"版本格式不规范: {version}，建议使用 semver 格式 (如 1.0.0)")

    # 检查内容
    if not body.strip():
        errors.append("技能内容为空")

    # 检查内容长度
    if len(body.strip()) < 50:
        warnings.append("技能内容太短，建议至少 50 个字符")

    # 检查可疑内容
    suspicious_patterns = [
        (r'\${{', "发现模板变量语法"),
        (r'`!', "发现内联 Shell 语法"),
        (r'eval\s*\(', "发现 eval() 调用"),
        (r'exec\s*\(', "发现 exec() 调用"),
    ]

    for pattern, msg in suspicious_patterns:
        import re
        if re.search(pattern, body):
            warnings.append(f"⚠️  {msg}")

    # 检查平台字段
    if "platforms" in frontmatter:
        platforms = frontmatter["platforms"]
        if isinstance(platforms, list):
            valid_platforms = {"linux", "macos", "windows", "all"}
            for p in platforms:
                if p.lower() not in valid_platforms:
                    warnings.append(f"未识别的平台: {p}")

    # 检查目录结构
    expected_dirs = ["scripts", "assets", "references"]
    for dir_name in expected_dirs:
        dir_path = skill_dir / dir_name
        if dir_path.exists() and not any(dir_path.iterdir()):
            warnings.append(f"目录 '{dir_name}' 为空")

    # 输出结果
    if errors:
        print("❌ 验证失败:")
        for err in errors:
            print(f"  ✗ {err}")
        print()

    if warnings:
        print("⚠️  警告:")
        for warn in warnings:
            print(f"  ! {warn}")
        print()

    if not errors and not warnings:
        print("✅ 验证通过！技能格式正确。\n")

    if verbose and not errors:
        print("📋 检查项:")
        print("  ✓ 必需字段完整")
        print("  ✓ 内容非空")
        if "version" in frontmatter:
            print(f"  ✓ 版本: {frontmatter['version']}")
        if "platforms" in frontmatter:
            print(f"  ✓ 平台: {', '.join(frontmatter['platforms'])}")

    return len(errors) == 0


def diff_skill(name: str, source: str = None) -> bool:
    """
    对比技能与 Hub 版本的差异

    Args:
        name: 技能名称
        source: 可选的指定来源

    Returns:
        是否成功
    """
    from common.config import get_skills_dir

    skills_dir = get_skills_dir()
    skill_dir = skills_dir / name

    if not skill_dir.exists():
        print(f"❌ 技能不存在: {name}")
        return False

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        print(f"❌ 技能文件不存在: {skill_file}")
        return False

    # 读取本地版本
    try:
        local_content = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ 读取本地技能失败: {e}")
        return False

    from agent.skill_utils import parse_frontmatter
    local_fm, local_body = parse_frontmatter(local_content)

    print(f"🔄 对比技能: {name}\n")

    # 获取锁定信息确定来源
    lock_info = None
    try:
        from agent.skill_lock import get_skill_lock_info
        lock_info = get_skill_lock_info(name)
    except ImportError:
        pass

    if not source and lock_info:
        source = lock_info.source

    if source:
        print(f"📦 来源: {source}")
        if lock_info:
            print(f"   标识: {lock_info.identifier}")
    print()

    # 如果有来源，尝试获取远程版本
    if source or lock_info:
        identifier = source if source else (lock_info.identifier if lock_info else name)

        print("🔍 正在从 Hub 获取最新版本...\n")

        # TODO: 与来源适配器集成
        # 目前只是一个占位实现

        print("ℹ️  更新对比需要与来源适配器配合")
        print("💡 当前仅显示本地版本信息")

    # 显示本地版本信息
    print("📋 本地版本信息:")

    local_hash = ""
    try:
        import hashlib
        local_hash = hashlib.sha256(local_content.encode()).hexdigest()[:16]
    except Exception:
        pass

    print(f"  内容哈希: {local_hash}")
    if lock_info:
        print(f"  安装时哈希: {lock_info.origin_hash}")
        if local_hash != lock_info.origin_hash:
            print(f"  ⚠️  哈希不一致，技能可能被修改过")

    print(f"  大小: {len(local_content)} bytes")
    print(f"  内容长度: {len(local_body)} characters")

    if lock_info:
        print(f"  安装时间: {lock_info.installed_at}")

    # 比较 frontmatter
    if source or lock_info:
        print("\n📊 Frontmatter 变化:")
        print(f"  本地版本: {local_fm.get('version', 'N/A')}")
        if source:
            print(f"  Hub 版本: (需要 Hub 支持)")

    # 如果有锁定信息，提供更新建议
    if lock_info:
        print("\n💡 操作建议:")
        if local_hash != lock_info.origin_hash:
            print(f"  技能已被修改，可使用 'agentz skills update {name}' 更新")
        else:
            print(f"  技能未修改，已是最新版本")

    return True


# ============ Export/Import 命令 ============

def export_skills_cli(
    skill_name: str = None,
    output_path: str = None,
    include_lock: bool = True,
    compress: bool = True,
) -> bool:
    """导出技能"""
    try:
        from agent.skill_bundle import get_bundle, ExportOptions
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not output_path:
        print("❌ 请指定输出路径: --output <path>")
        return False

    output = Path(output_path)

    options = ExportOptions(
        include_metadata=True,
        include_lock_info=include_lock,
        compress=compress,
    )

    bundle = get_bundle()

    if skill_name:
        print(f"📦 正在导出技能: {skill_name}")
        success = bundle.export_skill(skill_name, output, options)
    else:
        print("📦 正在导出所有技能...")
        success = bundle.export_all(output, options)

    if success:
        print(f"✅ 导出成功: {output}")
    else:
        print(f"❌ 导出失败")

    return success


def import_skills_cli(
    bundle_path: str = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> bool:
    """导入技能"""
    try:
        from agent.skill_bundle import get_bundle, ImportOptions
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not bundle_path:
        print("❌ 请指定导入文件: <path>")
        return False

    path = Path(bundle_path)
    if not path.exists():
        print(f"❌ 文件不存在: {bundle_path}")
        return False

    options = ImportOptions(
        overwrite=overwrite,
        dry_run=dry_run,
    )

    bundle = get_bundle()
    result = bundle.import_bundle(path, options)

    if dry_run:
        print("🔍 预览模式:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True

    if result["success"]:
        if result["imported"]:
            print(f"✅ 成功导入 {len(result['imported'])} 个技能:")
            for name in result["imported"]:
                print(f"  - {name}")
        if result["skipped"]:
            print(f"⏭️  跳过 {len(result['skipped'])} 个技能:")
            for s in result["skipped"]:
                print(f"  - {s['name']} ({s['reason']})")
        if result["errors"]:
            print(f"❌ {len(result['errors'])} 个错误:")
            for e in result["errors"]:
                print(f"  - {e}")
        return True
    else:
        print(f"❌ 导入失败: {result['errors']}")
        return False


# ============ Template 命令 ============

def list_templates_cli() -> bool:
    """列出模板"""
    try:
        from agent.skill_bundle import get_bundle
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    bundle = get_bundle()
    templates = bundle.list_templates()

    print("📋 可用的技能模板:\n")

    for t in templates:
        print(f"  {t['id']}")
        print(f"    名称: {t['name']}")
        print(f"    描述: {t['description']}")
        print()

    print("💡 使用 'agentz skills template create <template_id> <skill_name>' 创建技能")

    return True


def create_from_template_cli(
    template_id: str = None,
    skill_name: str = None,
    category: str = None,
) -> bool:
    """从模板创建技能"""
    try:
        from agent.skill_bundle import get_bundle
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not template_id or not skill_name:
        print("❌ 请指定模板和技能名称: template create <template_id> <skill_name>")
        return False

    bundle = get_bundle()
    result = bundle.create_from_template(template_id, skill_name, category)

    if result["success"]:
        print(f"✅ {result['message']}")
        print(f"📁 技能位置: ~/.agent_z/skills/{skill_name}")
        print(f"💡 使用 'agentz skills inspect {skill_name}' 查看技能")
    else:
        print(f"❌ {result['message']}")

    return result["success"]


# ============ History 命令 ============

def history_list_cli(skill_name: str) -> bool:
    """列出历史版本"""
    try:
        from agent.skill_history import get_history
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skill_name:
        print("❌ 请指定技能名称")
        return False

    history = get_history()
    versions = history.get_version_list(skill_name)

    if not versions:
        print(f"📭 暂无历史记录: {skill_name}")
        return True

    print(f"📜 技能历史: {skill_name}\n")

    for v in reversed(versions):  # 最新的在前
        print(f"  {v['version']} ({v['timestamp'][:10]})")
        print(f"    操作: {v['action']}")
        if v['message']:
            print(f"    说明: {v['message']}")
        print()

    return True


def history_diff_cli(skill_name: str, v1: str, v2: str = None) -> bool:
    """对比版本差异"""
    try:
        from agent.skill_history import get_history
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skill_name or not v1:
        print("❌ 请指定技能名称和版本: history diff <skill_name> <v1> [v2]")
        return False

    history = get_history()
    diff = history.diff(skill_name, v1, v2)

    if "error" in diff:
        print(f"❌ {diff['error']}")
        return False

    print(f"🔄 对比: {diff['version1']} → {diff['version2']}\n")
    print(f"  增加: {diff['lines_added']} 行")
    print(f"  删除: {diff['lines_removed']} 行")

    if diff.get("added_lines"):
        print(f"\n  增加的行: {diff['added_lines'][:5]}...")
    if diff.get("removed_lines"):
        print(f"  删除的行: {diff['removed_lines'][:5]}...")

    return True


def history_rollback_cli(skill_name: str, version: str) -> bool:
    """回滚版本"""
    try:
        from agent.skill_history import get_history
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skill_name or not version:
        print("❌ 请指定技能名称和版本: history rollback <skill_name> <version>")
        return False

    history = get_history()
    result = history.rollback(skill_name, version)

    if result["success"]:
        print(f"✅ {result['message']}")
        print(f"💡 使用 'agentz skills inspect {skill_name}' 确认回滚结果")
    else:
        print(f"❌ {result['message']}")

    return result["success"]


# ============ Share 命令 ============

def share_package_cli(skill_name: str) -> bool:
    """生成分享包"""
    try:
        from agent.skill_share import get_share
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skill_name:
        print("❌ 请指定技能名称")
        return False

    share = get_share()
    result = share.generate_share_package(skill_name)

    if result["success"]:
        print(f"📦 分享包信息: {skill_name}\n")
        print(f"  文件数: {len(result['files'])}")
        print(f"  内容哈希: {result.get('content_hash', 'N/A')}")
        print(f"\n  文件列表:")
        for f in result["files"]:
            print(f"    - {f['name']} ({f['size']} bytes)")
    else:
        print(f"❌ {result['message']}")

    return result["success"]


def share_markdown_cli(skill_name: str) -> bool:
    """生成 Markdown 分享"""
    try:
        from agent.skill_share import get_share
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skill_name:
        print("❌ 请指定技能名称")
        return False

    share = get_share()
    markdown = share.create_markdown_share(skill_name)

    print(markdown)

    return True


def share_gist_cli(
    skill_name: str,
    description: str = None,
    public: bool = False,
) -> bool:
    """发布到 GitHub Gist"""
    try:
        from agent.skill_share import get_share
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skill_name:
        print("❌ 请指定技能名称")
        return False

    share = get_share()
    result = share.share_to_gist(skill_name, description, public)

    if result.success:
        print(f"✅ {result.message}")
        print(f"🔗 {result.url}")
        print(f"\n💡 分享链接: {result.url}")
    else:
        print(f"❌ {result.message}")

    return result.success


# ============ Bundle 命令 ============

def list_bundles_cli(json_output: bool = False) -> bool:
    """列出所有 Bundle"""
    try:
        from agent.skill_workflows import list_bundles
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    bundles = list_bundles()

    if not bundles:
        print("📭 暂无 Bundle")
        print("💡 使用 'agentz bundles create <name> --skill <skill1> --skill <skill2>' 创建 Bundle")
        return True

    print(f"📦 已注册的 Bundle ({len(bundles)}):\n")

    for bundle in bundles:
        print(f"  /{bundle.slug}")
        print(f"    名称: {bundle.name}")
        print(f"    描述: {bundle.description or 'N/A'}")
        print(f"    技能: {', '.join(bundle.skills)}")
        if bundle.author:
            print(f"    作者: {bundle.author}")
        print()

    if json_output:
        import json
        print("\n📄 JSON 输出:")
        print(json.dumps([
            {
                "name": b.name,
                "slug": b.slug,
                "description": b.description,
                "skills": b.skills,
                "author": b.author,
            }
            for b in bundles
        ], indent=2, ensure_ascii=False))

    return True


def show_bundle_cli(name: str) -> bool:
    """显示 Bundle 详情"""
    try:
        from agent.skill_workflows import show_bundle, get_bundle
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    bundle = get_bundle(name)
    if not bundle:
        print(f"❌ Bundle 不存在: {name}")
        return False

    info = show_bundle(name)
    if info:
        print(info)

    return True


def create_bundle_cli(
    name: str,
    skills: List[str],
    description: str = "",
    instruction: str = "",
) -> bool:
    """创建 Bundle"""
    try:
        from agent.skill_workflows import create_bundle
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    if not skills:
        print("❌ 请指定至少一个技能: --skill <skill_name>")
        return False

    success, msg = create_bundle(
        name=name,
        skills=skills,
        description=description,
        instruction=instruction,
    )

    if success:
        print(f"✅ {msg}")
        print(f"\n💡 使用 '/{name.lower().replace(' ', '-')}' 调用此 Bundle")
    else:
        print(f"❌ {msg}")

    return success


def delete_bundle_cli(name: str) -> bool:
    """删除 Bundle"""
    try:
        from agent.skill_workflows import delete_bundle, get_bundle
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    bundle = get_bundle(name)
    if not bundle:
        print(f"❌ Bundle 不存在: {name}")
        return False

    confirm = input(f"⚠️  确定要删除 Bundle '{bundle['name']}' 吗? [y/N]: ").strip().lower()
    if confirm != "y":
        print("❌ 删除已取消")
        return False

    success, msg = delete_bundle(name)

    if success:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")

    return success


def reload_bundles_cli() -> bool:
    """重新加载 Bundle"""
    try:
        from agent.skill_workflows import reload_bundles
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    result = reload_bundles()

    print("🔄 Bundle 重新加载完成\n")

    if result["added"]:
        print(f"➕ 新增: {len(result['added'])}")
        for item in result["added"]:
            print(f"    - /{item['slug']}")

    if result["removed"]:
        print(f"➖ 移除: {len(result['removed'])}")
        for item in result["removed"]:
            print(f"    - /{item['slug']}")

    if result["unchanged"]:
        print(f"✔️  未变化: {len(result['unchanged'])}")

    print(f"\n📊 总计: {result['total']} Bundle")
    return True


def list_bundle_templates_cli() -> bool:
    """列出 Bundle 模板"""
    try:
        from agent.skill_workflows import get_bundle_templates
    except ImportError as e:
        print(f"❌ 缺少必要模块: {e}")
        return False

    templates = get_bundle_templates()

    print("📋 可用的 Bundle 模板:\n")

    for t in templates:
        print(f"  {t['id']}")
        print(f"    名称: {t['name']}")
        print(f"    描述: {t['description']}")
        print(f"    技能: {', '.join(t['skills'])}")
        print()

    print("💡 使用 'agentz bundles create <name> --from-template <template_id>' 从模板创建")
    return True


def add_skills_parser(subparsers) -> None:
    """
    添加 skills 子命令解析器

    Args:
        subparsers: argparse subparsers
    """
    skills_parser = subparsers.add_parser(
        "skills",
        help="管理用户自定义技能",
        description="安装、同步、列出和卸载技能",
    )

    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", help="技能命令")

    install_parser = skills_subparsers.add_parser("install", help="安装技能")
    install_parser.add_argument("source", help="技能来源 (URL 或 GitHub 仓库)")
    install_parser.add_argument("--name", "-n", help="技能名称")

    sync_parser = skills_subparsers.add_parser("sync", help="同步本地技能目录")

    list_parser = skills_subparsers.add_parser("list", help="列出已安装的技能")
    list_parser.add_argument("--state", "-s", help="按状态过滤 (active/stale/archived)")
    list_parser.add_argument("--sort", "-S", choices=["name", "usage", "view", "state", "time", "pinned"], default="name", help="排序方式")
    list_parser.add_argument("--reverse", "-r", action="store_true", help="反向排序")
    list_parser.add_argument("--page", "-p", type=int, default=1, help="页码 (default: 1)")
    list_parser.add_argument("--per-page", "-n", type=int, default=20, help="每页数量 (default: 20)")
    list_parser.add_argument("--json", "-j", action="store_true", help="JSON 格式输出")

    uninstall_parser = skills_subparsers.add_parser("uninstall", help="卸载技能")
    uninstall_parser.add_argument("name", help="技能名称")

    enable_parser = skills_subparsers.add_parser("enable", help="启用技能")
    enable_parser.add_argument("name", help="技能名称")

    disable_parser = skills_subparsers.add_parser("disable", help="禁用技能")
    disable_parser.add_argument("name", help="技能名称")

    update_parser = skills_subparsers.add_parser("update", help="更新技能")
    update_parser.add_argument("name", help="技能名称")
    update_parser.add_argument("--source", "-s", help="更新来源 URL 或 GitHub 仓库")

    # 安全扫描命令
    scan_parser = skills_subparsers.add_parser("scan", help="扫描技能安全")
    scan_parser.add_argument("name", nargs="?", help="技能名称（省略则扫描所有）")
    scan_parser.add_argument("--source", "-s", default="community", help="来源标识 (default: community)")

    # AST 审计命令
    audit_parser = skills_subparsers.add_parser("audit", help="AST 审计技能")
    audit_parser.add_argument("name", help="技能名称")

    # 备份命令
    backup_parser = skills_subparsers.add_parser("backup", help="备份所有技能")

    # 恢复命令
    restore_parser = skills_subparsers.add_parser("restore", help="从备份恢复")
    restore_parser.add_argument("backup_id", help="备份 ID")

    # 检查更新命令
    check_parser = skills_subparsers.add_parser("check-updates", help="检查技能更新")

    # 来源命令
    provenance_parser = skills_subparsers.add_parser("provenance", help="显示技能来源")
    provenance_parser.add_argument("name", help="技能名称")

    # 按来源过滤命令
    list_source_parser = skills_subparsers.add_parser("list-by-source", help="按来源过滤列出技能")
    list_source_parser.add_argument("source", nargs="?", help="来源类型 (agent_created, user_created, hub_installed, restored)")

    # 搜索命令
    search_parser = skills_subparsers.add_parser("search", help="搜索技能")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--sources", "-s", nargs="+", help="指定来源")

    # 来源管理命令
    source_parser = skills_subparsers.add_parser("source", help="管理技能来源")
    source_subparsers = source_parser.add_subparsers(dest="source_command", help="来源命令")

    source_list_parser = source_subparsers.add_parser("list", help="列出配置的来源")
    source_add_parser = source_subparsers.add_parser("add", help="添加来源")
    source_add_parser.add_argument("name", help="来源名称")
    source_add_parser.add_argument("--url", "-u", help="来源 URL")

    source_remove_parser = source_subparsers.add_parser("remove", help="移除来源")
    source_remove_parser.add_argument("name", help="来源名称")

    # 推荐命令
    recommend_parser = skills_subparsers.add_parser("recommend", help="推荐技能")
    recommend_parser.add_argument("query", nargs="?", help="搜索描述（可选）")
    recommend_parser.add_argument("--top", "-t", type=int, default=5, help="返回数量 (default: 5)")
    recommend_parser.add_argument("--json", "-j", action="store_true", help="JSON 格式输出")

    # Lock 命令
    lock_parser = skills_subparsers.add_parser("lock", help="HubLockFile 管理")
    lock_subparsers = lock_parser.add_subparsers(dest="lock_action", help="Lock 操作")

    # lock list
    lock_list_parser = lock_subparsers.add_parser("list", help="列出已锁定的技能")
    lock_list_parser.add_argument("--source", "-s", help="按来源过滤 (github, url, etc.)")

    # lock info
    lock_info_parser = lock_subparsers.add_parser("info", help="查看技能锁定信息")
    lock_info_parser.add_argument("name", help="技能名称")

    # lock check
    lock_check_parser = lock_subparsers.add_parser("check", help="检查技能是否有更新")
    lock_check_parser.add_argument("name", nargs="?", help="技能名称（省略则检查所有）")

    # inspect 命令
    inspect_parser = skills_subparsers.add_parser("inspect", help="详细查看技能")
    inspect_parser.add_argument("name", help="技能名称")
    inspect_parser.add_argument("--json", "-j", action="store_true", help="JSON 格式输出")

    # validate 命令
    validate_parser = skills_subparsers.add_parser("validate", help="验证技能格式")
    validate_parser.add_argument("name", help="技能名称")
    validate_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    # diff 命令
    diff_parser = skills_subparsers.add_parser("diff", help="对比技能差异")
    diff_parser.add_argument("name", help="技能名称")
    diff_parser.add_argument("--source", "-s", help="指定来源")

    # export 命令
    export_parser = skills_subparsers.add_parser("export", help="导出技能")
    export_parser.add_argument("name", nargs="?", help="技能名称（省略则导出所有）")
    export_parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    export_parser.add_argument("--include-lock", action="store_true", default=True, help="包含锁定信息")
    export_parser.add_argument("--no-compress", action="store_true", help="不压缩")

    # import 命令
    import_parser = skills_subparsers.add_parser("import", help="导入技能")
    import_parser.add_argument("path", help="导入文件路径")
    import_parser.add_argument("--overwrite", "-f", action="store_true", help="覆盖已存在的技能")
    import_parser.add_argument("--dry-run", "-n", action="store_true", help="预览模式")

    # template 命令
    template_parser = skills_subparsers.add_parser("template", help="技能模板")
    template_subparsers = template_parser.add_subparsers(dest="template_action", help="模板操作")

    template_list_parser = template_subparsers.add_parser("list", help="列出模板")
    template_create_parser = template_subparsers.add_parser("create", help="从模板创建")
    template_create_parser.add_argument("template", help="模板 ID")
    template_create_parser.add_argument("name", help="新技能名称")
    template_create_parser.add_argument("--category", "-c", help="分类")

    # history 命令
    history_parser = skills_subparsers.add_parser("history", help="技能版本历史")
    history_subparsers = history_parser.add_subparsers(dest="history_action", help="历史操作")

    history_list_parser = history_subparsers.add_parser("list", help="列出历史")
    history_list_parser.add_argument("name", help="技能名称")

    history_diff_parser = history_subparsers.add_parser("diff", help="对比版本")
    history_diff_parser.add_argument("name", help="技能名称")
    history_diff_parser.add_argument("v1", help="版本1 (如 v1)")
    history_diff_parser.add_argument("v2", nargs="?", help="版本2 (如 v2，省略则与当前版本对比)")

    history_rollback_parser = history_subparsers.add_parser("rollback", help="回滚版本")
    history_rollback_parser.add_argument("name", help="技能名称")
    history_rollback_parser.add_argument("version", help="要回滚到的版本")

    # share 命令
    share_parser = skills_subparsers.add_parser("share", help="分享技能")
    share_subparsers = share_parser.add_subparsers(dest="share_action", help="分享操作")

    share_package_parser = share_subparsers.add_parser("package", help="生成分享包")
    share_package_parser.add_argument("name", help="技能名称")

    share_markdown_parser = share_subparsers.add_parser("markdown", help="生成 Markdown")
    share_markdown_parser.add_argument("name", help="技能名称")

    share_gist_parser = share_subparsers.add_parser("gist", help="发布到 GitHub Gist")
    share_gist_parser.add_argument("name", help="技能名称")
    share_gist_parser.add_argument("--description", "-d", help="描述")
    share_gist_parser.add_argument("--public", "-p", action="store_true", help="公开 Gist")

    # Curator 命令
    curator_parser = skills_subparsers.add_parser("curator", help="Curator 生命周期管理")
    curator_subparsers = curator_parser.add_subparsers(dest="curator_action", help="Curator 操作")

    # curator status
    curator_status_parser = curator_subparsers.add_parser("status", help="显示 Curator 状态")

    # curator run
    curator_run_parser = curator_subparsers.add_parser("run", help="运行 Curator 清理")
    curator_run_parser.add_argument("--dry-run", "-n", action="store_true", help="试运行模式")

    # curator pin
    curator_pin_parser = curator_subparsers.add_parser("pin", help="置顶技能")
    curator_pin_parser.add_argument("name", help="技能名称")

    # curator unpin
    curator_unpin_parser = curator_subparsers.add_parser("unpin", help="取消置顶技能")
    curator_unpin_parser.add_argument("name", help="技能名称")

    # curator archive
    curator_archive_parser = curator_subparsers.add_parser("archive", help="归档技能")
    curator_archive_parser.add_argument("name", help="技能名称")

    # curator restore
    curator_restore_parser = curator_subparsers.add_parser("restore", help="恢复归档的技能")
    curator_restore_parser.add_argument("name", help="技能名称")

    # scheduler 命令
    scheduler_parser = skills_subparsers.add_parser("scheduler", help="定时任务调度器")
    scheduler_subparsers = scheduler_parser.add_subparsers(dest="scheduler_action", help="调度器操作")

    # scheduler status
    scheduler_status_parser = scheduler_subparsers.add_parser("status", help="显示调度器状态")

    # scheduler run
    scheduler_run_parser = scheduler_subparsers.add_parser("run", help="立即运行任务")
    scheduler_run_parser.add_argument("task", nargs="?", default="curator_cleanup", help="任务名称")

    # scheduler enable
    scheduler_enable_parser = scheduler_subparsers.add_parser("enable", help="启用任务")
    scheduler_enable_parser.add_argument("task", help="任务名称")

    # scheduler disable
    scheduler_disable_parser = scheduler_subparsers.add_parser("disable", help="禁用任务")
    scheduler_disable_parser.add_argument("task", help="任务名称")

    # bundle 子命令
    bundle_parser = skills_subparsers.add_parser("bundle", help="技能组合 Bundle 管理")
    bundle_subparsers = bundle_parser.add_subparsers(dest="bundle_action", help="Bundle 操作")

    # bundle list
    bundle_list_parser = bundle_subparsers.add_parser("list", help="列出所有 Bundle")
    bundle_list_parser.add_argument("--json", "-j", action="store_true", help="JSON 格式输出")

    # bundle show
    bundle_show_parser = bundle_subparsers.add_parser("show", help="显示 Bundle 详情")
    bundle_show_parser.add_argument("name", help="Bundle 名称或 slug")

    # bundle create
    bundle_create_parser = bundle_subparsers.add_parser("create", help="创建 Bundle")
    bundle_create_parser.add_argument("name", help="Bundle 名称")
    bundle_create_parser.add_argument("--skill", "-s", action="append", dest="skill", default=[], help="包含的技能 (可多次指定)")
    bundle_create_parser.add_argument("--description", "-d", help="描述")
    bundle_create_parser.add_argument("--instruction", "-i", help="额外指令")

    # bundle delete
    bundle_delete_parser = bundle_subparsers.add_parser("delete", help="删除 Bundle")
    bundle_delete_parser.add_argument("name", help="Bundle 名称或 slug")

    # bundle reload
    bundle_reload_parser = bundle_subparsers.add_parser("reload", help="重新加载 Bundle")

    # bundle templates
    bundle_templates_parser = bundle_subparsers.add_parser("templates", help="列出 Bundle 模板")


async def run_skills_command(args) -> int:
    """
    执行 skills 命令

    Args:
        args: 解析后的命令行参数

    Returns:
        退出码
    """
    if not hasattr(args, "skills_command") or not args.skills_command:
        print("请指定技能命令，使用 'agentz skills --help' 查看帮助")
        return 1

    command = args.skills_command

    if command == "install":
        source = args.source
        name = getattr(args, "name", None)

        if source.startswith("http://") or source.startswith("https://"):
            success = await install_from_url(source, name)
        elif "github.com" in source or "/" in source:
            success = await install_from_github(source, name)
        else:
            archive_path = Path(source)
            if archive_path.exists() and archive_path.suffix in [".zip", ".tar", ".gz"]:
                success = await install_from_archive(source, name)
            else:
                print(f"❌ 无法识别的来源: {source}")
                print("💡 支持: URL, GitHub 仓库 (owner/repo), 本地归档文件 (.zip)")
                return 1

        return 0 if success else 1

    elif command == "sync":
        success = await sync_skills()
        return 0 if success else 1

    elif command == "list":
        success = list_skills(
            state_filter=getattr(args, "state", None),
            sort_by=getattr(args, "sort", "name"),
            reverse=getattr(args, "reverse", False),
            page=getattr(args, "page", 1),
            per_page=getattr(args, "per_page", 20),
            json_output=getattr(args, "json", False),
        )
        return 0 if success else 1

    elif command == "uninstall":
        success = uninstall_skill(args.name)
        return 0 if success else 1

    elif command == "enable":
        success = enable_skill(args.name)
        return 0 if success else 1

    elif command == "disable":
        success = disable_skill(args.name)
        return 0 if success else 1

    elif command == "update":
        source = getattr(args, "source", None)
        success = await update_skill(args.name, source)
        return 0 if success else 1

    elif command == "scan":
        name = getattr(args, "name", None)
        source = getattr(args, "source", "community")
        if name:
            success = scan_skill(name, source)
        else:
            success = scan_all_skills(source)
        return 0 if success else 1

    elif command == "audit":
        success = audit_skill(args.name)
        return 0 if success else 1

    elif command == "backup":
        success = backup_skills()
        return 0 if success else 1

    elif command == "restore":
        success = await restore_skills(args.backup_id)
        return 0 if success else 1

    elif command == "check-updates":
        success = check_updates()
        return 0 if success else 1

    elif command == "provenance":
        success = show_provenance(args.name)
        return 0 if success else 1

    elif command == "list-by-source":
        source_filter = getattr(args, "source", None)
        success = list_skills_by_source(source_filter)
        return 0 if success else 1

    elif command == "search":
        query = args.query
        sources = getattr(args, "sources", None)
        success = await search_skills(query, sources)
        return 0 if success else 1

    elif command == "source":
        source_cmd = getattr(args, "source_command", None)
        if not source_cmd:
            success = list_sources()
        elif source_cmd == "list":
            success = list_sources()
        elif source_cmd == "add":
            name = args.name
            config = {"url": getattr(args, "url", None)}
            success = add_source(name, config)
        elif source_cmd == "remove":
            success = remove_source(args.name)
        else:
            print(f"❌ 未知来源命令: {source_cmd}")
        return 0 if success else 1

    elif command == "recommend":
        query = getattr(args, "query", None)
        top_n = getattr(args, "top", 5)
        json_output = getattr(args, "json", False)
        success = recommend_skills(query, top_n, json_output)
        return 0 if success else 1

    elif command == "export":
        skill_name = getattr(args, "name", None)
        output_path = getattr(args, "output", None)
        include_lock = getattr(args, "include_lock", True)
        compress = not getattr(args, "no_compress", False)
        success = export_skills_cli(skill_name, output_path, include_lock, compress)
        return 0 if success else 1

    elif command == "import":
        import_path = getattr(args, "path", None)
        overwrite = getattr(args, "overwrite", False)
        dry_run = getattr(args, "dry_run", False)
        success = import_skills_cli(import_path, overwrite, dry_run)
        return 0 if success else 1

    elif command == "template":
        template_action = getattr(args, "template_action", None)
        if template_action == "list":
            success = list_templates_cli()
        elif template_action == "create":
            template_id = getattr(args, "template", None)
            name = getattr(args, "name", None)
            category = getattr(args, "category", None)
            success = create_from_template_cli(template_id, name, category)
        else:
            success = list_templates_cli()
        return 0 if success else 1

    elif command == "history":
        history_action = getattr(args, "history_action", None)
        if history_action == "list":
            success = history_list_cli(args.name)
        elif history_action == "diff":
            success = history_diff_cli(args.name, args.v1, getattr(args, "v2", None))
        elif history_action == "rollback":
            success = history_rollback_cli(args.name, args.version)
        else:
            success = history_list_cli(args.name)
        return 0 if success else 1

    elif command == "share":
        share_action = getattr(args, "share_action", None)
        skill_name = None
        if hasattr(args, "name"):
            skill_name = args.name

        if share_action == "package":
            success = share_package_cli(skill_name)
        elif share_action == "markdown":
            success = share_markdown_cli(skill_name)
        elif share_action == "gist":
            description = getattr(args, "description", None)
            public = getattr(args, "public", False)
            success = share_gist_cli(skill_name, description, public)
        else:
            print("❌ 请指定分享操作: package, markdown, gist")
            success = False
        return 0 if success else 1

    elif command == "curator":
        curator_action = getattr(args, "curator_action", None)
        if curator_action == "status":
            success = show_curator_status()
        elif curator_action == "run":
            dry_run = getattr(args, "dry_run", False)
            success = run_curator_cli(dry_run=dry_run)
        elif curator_action == "pin":
            success = curator_pin_skill(args.name)
        elif curator_action == "unpin":
            success = curator_unpin_skill(args.name)
        elif curator_action == "archive":
            success = curator_archive_skill(args.name)
        elif curator_action == "restore":
            success = curator_restore_skill(args.name)
        else:
            # 默认显示状态
            success = show_curator_status()
        return 0 if success else 1

    elif command == "scheduler":
        scheduler_action = getattr(args, "scheduler_action", None)
        if scheduler_action == "status":
            success = scheduler_status()
        elif scheduler_action == "run":
            task = getattr(args, "task", "curator_cleanup")
            success = scheduler_run_now(task)
        elif scheduler_action == "enable":
            success = scheduler_enable_task(args.task)
        elif scheduler_action == "disable":
            success = scheduler_disable_task(args.task)
        else:
            # 默认显示状态
            success = scheduler_status()
        return 0 if success else 1

    elif command == "lock":
        lock_action = getattr(args, "lock_action", None)
        if lock_action == "list":
            source_filter = getattr(args, "source", None)
            success = lock_list_skills(source_filter)
        elif lock_action == "info":
            success = lock_show_info(args.name)
        elif lock_action == "check":
            skill_name = getattr(args, "name", None)
            success = lock_check_updates(skill_name)
        else:
            # 默认列出所有
            success = lock_list_skills()
        return 0 if success else 1

    elif command == "inspect":
        success = inspect_skill(args.name, json_output=getattr(args, "json", False))
        return 0 if success else 1

    elif command == "validate":
        success = validate_skill(args.name, verbose=getattr(args, "verbose", False))
        return 0 if success else 1

    elif command == "diff":
        source = getattr(args, "source", None)
        success = diff_skill(args.name, source=source)
        return 0 if success else 1

    elif command == "bundle":
        bundle_cmd = getattr(args, "bundle_action", None)
        if bundle_cmd == "list":
            success = list_bundles_cli(json_output=getattr(args, "json", False))
        elif bundle_cmd == "show":
            success = show_bundle_cli(args.name)
        elif bundle_cmd == "create":
            skills = getattr(args, "skill", [])
            description = getattr(args, "description", "") or ""
            instruction = getattr(args, "instruction", "") or ""
            success = create_bundle_cli(args.name, skills, description, instruction)
        elif bundle_cmd == "delete":
            success = delete_bundle_cli(args.name)
        elif bundle_cmd == "reload":
            success = reload_bundles_cli()
        elif bundle_cmd == "templates":
            success = list_bundle_templates_cli()
        else:
            success = list_bundles_cli()
        return 0 if success else 1

    else:
        print(f"❌ 未知命令: {command}")
        return 1


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        prog="agentz skills",
        description="管理用户自定义技能",
    )

    parser.add_argument("command", choices=["install", "sync", "list", "uninstall", "enable", "disable", "update"])
    parser.add_argument("source", nargs="?", help="技能来源或名称")
    parser.add_argument("--name", "-n", help="技能名称")

    args = parser.parse_args()

    if args.command == "install" and not args.source:
        parser.error("install 命令需要指定技能来源")

    if args.command == "uninstall" and not args.source:
        parser.error("uninstall 命令需要指定技能名称")

    if args.command == "install":
        source = args.source
        name = args.name

        if source.startswith("http://") or source.startswith("https://"):
            success = asyncio.run(install_from_url(source, name))
        elif "github.com" in source or "/" in source:
            success = asyncio.run(install_from_github(source, name))
        else:
            archive_path = Path(source)
            if archive_path.exists() and archive_path.suffix in [".zip", ".tar", ".gz"]:
                success = asyncio.run(install_from_archive(source, name))
            else:
                print(f"❌ 无法识别的来源: {source}")
                return 1

    elif args.command == "sync":
        success = asyncio.run(sync_skills())

    elif args.command == "list":
        success = list_skills(
            state_filter=getattr(args, "state", None),
            sort_by=getattr(args, "sort", "name"),
            reverse=getattr(args, "reverse", False),
            page=getattr(args, "page", 1),
            per_page=getattr(args, "per_page", 20),
            json_output=getattr(args, "json", False),
        )

    elif args.command == "uninstall":
        success = uninstall_skill(args.source)

    elif args.command == "enable":
        success = enable_skill(args.source)

    elif args.command == "disable":
        success = disable_skill(args.source)

    elif args.command == "update":
        success = asyncio.run(update_skill(args.source))

    else:
        print(f"❌ 未知命令: {args.command}")
        success = False

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
