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


async def install_skill_from_dir(skill_dir: Path, name: str) -> bool:
    """
    从目录安装技能

    Args:
        skill_dir: 技能目录
        name: 技能名称

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

    if target_dir.exists():
        response = input(f"⚠️  技能 '{name}' 已存在，是否覆盖? [y/N]: ").strip().lower()
        if response != "y":
            print("❌ 安装已取消")
            return False
        shutil.rmtree(target_dir)

    shutil.copytree(skill_dir, target_dir)
    print(f"✅ 技能 '{name}' 安装成功!")
    print(f"📁 安装位置: {target_dir}")

    try:
        from skills import get_skill_telemetry
        telemetry = get_skill_telemetry()
        telemetry.create_skill_record(
            skill_id=name,
            created_by="user",
            tags=["installed"],
        )
        print("📊 已注册到技能追踪系统")
    except Exception as e:
        logger.warning(f"Failed to register skill in telemetry: {e}")

    return True


async def sync_skills() -> bool:
    """
    同步本地 skills 目录

    扫描用户 skills 目录并注册所有技能

    Returns:
        是否成功
    """
    from skills import SkillsLoader, get_skill_telemetry

    skills_dir = get_skills_dir()

    if not skills_dir.exists():
        print(f"📁 技能目录不存在: {skills_dir}")
        print("💡 将创建技能目录")
        skills_dir.mkdir(parents=True, exist_ok=True)
        return True

    print(f"🔄 正在同步技能目录: {skills_dir}")

    try:
        loader = SkillsLoader(skills_dir=skills_dir)
        skills = await loader.load_all()

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


def list_skills() -> bool:
    """
    列出已安装的技能

    Returns:
        是否成功
    """
    from skills import get_skill_telemetry

    skills_dir = get_skills_dir()

    if not skills_dir.exists():
        print("📁 技能目录不存在")
        return True

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not skill_dirs:
        print("📭 暂无已安装的技能")
        print("💡 使用 'handsome skills install <url>' 安装技能")
        return True

    print(f"📦 已安装的技能 ({len(skill_dirs)}):\n")

    telemetry = get_skill_telemetry()

    for skill_dir in sorted(skill_dirs):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        name = skill_dir.name
        record = telemetry.get_record(name)

        use_count = record.use_count if record else 0
        state = record.state if record else "active"

        state_emoji = {
            "active": "🟢",
            "stale": "🟡",
            "archived": "⚪",
        }.get(state, "❓")

        print(f"  {state_emoji} {name}")
        print(f"     使用次数: {use_count} | 状态: {state}")
        print(f"     路径: {skill_dir}")
        print()

    summary = telemetry.get_usage_summary()
    print(f"📊 统计: {summary.get('active', 0)} 活跃, {summary.get('stale', 0)} 过期, {summary.get('archived', 0)} 已归档")

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

        try:
            from skills import get_skill_telemetry
            telemetry = get_skill_telemetry()
            telemetry.archive_skill(name)
            print("📊 已从追踪系统中移除")
        except Exception as e:
            logger.warning(f"Failed to archive skill in telemetry: {e}")

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
    print("💡 暂时不支持自动检查更新，请使用 'handsome skills update' 手动更新")
    return False


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

    uninstall_parser = skills_subparsers.add_parser("uninstall", help="卸载技能")
    uninstall_parser.add_argument("name", help="技能名称")

    enable_parser = skills_subparsers.add_parser("enable", help="启用技能")
    enable_parser.add_argument("name", help="技能名称")

    disable_parser = skills_subparsers.add_parser("disable", help="禁用技能")
    disable_parser.add_argument("name", help="技能名称")

    update_parser = skills_subparsers.add_parser("update", help="更新技能")
    update_parser.add_argument("name", help="技能名称")
    update_parser.add_argument("--source", "-s", help="更新来源 URL 或 GitHub 仓库")


async def run_skills_command(args) -> int:
    """
    执行 skills 命令

    Args:
        args: 解析后的命令行参数

    Returns:
        退出码
    """
    if not hasattr(args, "skills_command") or not args.skills_command:
        print("请指定技能命令，使用 'handsome skills --help' 查看帮助")
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
        success = list_skills()
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

    else:
        print(f"❌ 未知命令: {command}")
        return 1


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        prog="handsome skills",
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
        success = list_skills()

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
