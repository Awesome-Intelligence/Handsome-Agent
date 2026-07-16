#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bundle CLI command module

Provides bundle commands for managing skill bundles:
- bundle list: List all available skill bundles
- bundle create: Create a new skill bundle
- bundle delete: Delete a skill bundle
- bundle info: Show bundle details

🚪 Access - 💬 CLI - 技能包命令
"""

import argparse
from typing import List, Optional, Dict, Any

from common.logging_manager import get_access_logger

logger = get_access_logger(__name__)


class BundleCommands:
    """技能包命令处理类"""

    def __init__(self):
        """初始化 BundleCommands"""
        self._bundle_manager = None

    @property
    def bundle_manager(self):
        """延迟加载 bundle_manager"""
        if self._bundle_manager is None:
            from agent.skills.skill_command_bundle import SkillBundleManager
            self._bundle_manager = SkillBundleManager()
        return self._bundle_manager

    def list_bundles(self) -> int:
        """
        列出所有可用的技能包

        Returns:
            退出码 (0=成功, 1=失败)
        """
        bundles = self.bundle_manager.list_bundles()

        if not bundles:
            print("📭 暂无已创建的技能包")
            print("💡 使用 'bundle create <name> <skills...>' 创建第一个技能包")
            return 0

        print(f"📦 可用的技能包 ({len(bundles)}):\n")

        for bundle in bundles:
            skill_count = len(bundle.skills)
            desc_preview = bundle.description[:40] + "..." if len(bundle.description) > 40 else bundle.description

            print(f"  📁 {bundle.name}")
            if bundle.description:
                print(f"     描述: {desc_preview}")
            print(f"     技能数: {skill_count}")
            if bundle.skills:
                skills_preview = ", ".join(bundle.skills[:3])
                if len(bundle.skills) > 3:
                    skills_preview += f" (+{len(bundle.skills) - 3} more)"
                print(f"     技能: {skills_preview}")
            print()

        return 0

    def create_bundle(
        self,
        name: str,
        skills: List[str],
        description: str = "",
        instruction: str = ""
    ) -> int:
        """
        创建新的技能包

        Args:
            name: 技能包名称
            skills: 技能列表
            description: 技能包描述
            instruction: 额外指令

        Returns:
            退出码 (0=成功, 1=失败)
        """
        if not name:
            print("❌ 请指定技能包名称")
            print("💡 用法: bundle create <name> <skills...>")
            return 1

        if not skills:
            print("❌ 请至少指定一个技能")
            print("💡 用法: bundle create <name> <skills...>")
            return 1

        print(f"📦 正在创建技能包: {name}")
        print(f"   技能: {', '.join(skills)}")

        success = self.bundle_manager.create_bundle(
            name=name,
            skills=skills,
            description=description,
            instruction=instruction
        )

        if success:
            print(f"✅ 技能包 '{name}' 创建成功!")
            print(f"📁 位置: {self.bundle_manager._bundles_dir / f'{self.bundle_manager._slugify(name)}.yaml'}")
            return 0
        else:
            print(f"❌ 技能包 '{name}' 已存在或创建失败")
            return 1

    def delete_bundle(self, name: str) -> int:
        """
        删除指定的技能包

        Args:
            name: 技能包名称

        Returns:
            退出码 (0=成功, 1=失败)
        """
        if not name:
            print("❌ 请指定要删除的技能包名称")
            print("💡 用法: bundle delete <name>")
            return 1

        # 检查 bundle 是否存在
        bundle = self.bundle_manager.load_bundle(name)
        if not bundle:
            print(f"❌ 技能包 '{name}' 不存在")
            return 1

        # 确认删除
        print(f"⚠️  确定要删除技能包 '{name}' 吗?")
        print(f"   包含 {len(bundle.skills)} 个技能: {', '.join(bundle.skills[:5])}")
        if len(bundle.skills) > 5:
            print(f"   ... 以及其他 {len(bundle.skills) - 5} 个技能")

        response = input("\n确认删除? [y/N]: ").strip().lower()
        if response != "y":
            print("❌ 删除已取消")
            return 1

        success = self.bundle_manager.delete_bundle(name)

        if success:
            print(f"✅ 技能包 '{name}' 已删除")
            return 0
        else:
            print(f"❌ 删除技能包 '{name}' 失败")
            return 1

    def get_bundle_info(self, name: str) -> int:
        """
        查看技能包详情

        Args:
            name: 技能包名称

        Returns:
            退出码 (0=成功, 1=失败)
        """
        if not name:
            print("❌ 请指定技能包名称")
            print("💡 用法: bundle info <name>")
            return 1

        bundle_info = self.bundle_manager.get_bundle_info(name)

        if not bundle_info:
            print(f"❌ 技能包 '{name}' 不存在")
            return 1

        print(f"\n{'='*50}")
        print(f"📦 技能包详情: {bundle_info['name']}")
        print(f"{'='*50}\n")

        print(f"  名称: {bundle_info['name']}")
        print(f"  Slug: {bundle_info['slug']}")

        if bundle_info['description']:
            print(f"  描述: {bundle_info['description']}")

        print(f"  技能数: {bundle_info['skills_count']}")

        if bundle_info['skills']:
            print(f"\n  技能列表:")
            for i, skill in enumerate(bundle_info['skills'], start=1):
                print(f"    {i}. {skill}")

        if bundle_info.get('instruction'):
            instruction = bundle_info['instruction']
            instr_preview = instruction[:100] + "..." if len(instruction) > 100 else instruction
            print(f"\n  指令: {instr_preview}")

        print(f"\n  路径: {bundle_info['path']}")
        print()

        return 0


# 全局实例
_bundle_commands: Optional[BundleCommands] = None


def get_bundle_commands() -> BundleCommands:
    """获取 BundleCommands 全局实例"""
    global _bundle_commands
    if _bundle_commands is None:
        _bundle_commands = BundleCommands()
    return _bundle_commands


def add_bundle_parser(subparsers) -> None:
    """
    添加 bundle 子命令解析器

    Args:
        subparsers: argparse subparsers
    """
    bundle_parser = subparsers.add_parser(
        "bundle",
        help="管理技能包",
        description="创建、列出、删除和查看技能包详情",
    )

    bundle_subparsers = bundle_parser.add_subparsers(dest="bundle_command", help="技能包命令")

    # bundle list
    list_parser = bundle_subparsers.add_parser("list", help="列出所有技能包")

    # bundle create
    create_parser = bundle_subparsers.add_parser("create", help="创建新的技能包")
    create_parser.add_argument("name", help="技能包名称")
    create_parser.add_argument("skills", nargs="+", help="技能列表 (至少一个)")
    create_parser.add_argument("--description", "-d", help="技能包描述")
    create_parser.add_argument("--instruction", "-i", help="额外指令")

    # bundle delete
    delete_parser = bundle_subparsers.add_parser("delete", help="删除技能包")
    delete_parser.add_argument("name", help="技能包名称")

    # bundle info
    info_parser = bundle_subparsers.add_parser("info", help="查看技能包详情")
    info_parser.add_argument("name", help="技能包名称")


async def run_bundle_command(args) -> int:
    """
    执行 bundle 命令

    Args:
        args: 解析后的命令行参数

    Returns:
        退出码
    """
    if not hasattr(args, "bundle_command") or not args.bundle_command:
        print("请指定技能包命令，使用 'bundle --help' 查看帮助")
        return 1

    cmd = get_bundle_commands()
    command = args.bundle_command

    if command == "list":
        return cmd.list_bundles()

    elif command == "create":
        name = args.name
        skills = args.skills
        description = getattr(args, "description", "") or ""
        instruction = getattr(args, "instruction", "") or ""
        return cmd.create_bundle(name, skills, description, instruction)

    elif command == "delete":
        return cmd.delete_bundle(args.name)

    elif command == "info":
        return cmd.get_bundle_info(args.name)

    else:
        print(f"❌ 未知命令: {command}")
        return 1


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        prog="agentz bundle",
        description="管理技能包 - 创建、列出、删除和查看技能包详情",
    )

    subparsers = parser.add_subparsers(dest="command", help="技能包命令")

    # bundle list
    subparsers.add_parser("list", help="列出所有技能包")

    # bundle create
    create_parser = subparsers.add_parser("create", help="创建新的技能包")
    create_parser.add_argument("name", help="技能包名称")
    create_parser.add_argument("skills", nargs="+", help="技能列表")
    create_parser.add_argument("-d", "--description", help="技能包描述")
    create_parser.add_argument("-i", "--instruction", help="额外指令")

    # bundle delete
    delete_parser = subparsers.add_parser("delete", help="删除技能包")
    delete_parser.add_argument("name", help="技能包名称")

    # bundle info
    info_parser = subparsers.add_parser("info", help="查看技能包详情")
    info_parser.add_argument("name", help="技能包名称")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    import asyncio
    return asyncio.run(run_bundle_command(args))


if __name__ == "__main__":
    exit(main())