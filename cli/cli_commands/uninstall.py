#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uninstall command - Uninstall Agent-Z

🚪 Access - 💬 CLI - 卸载功能

提供完整的卸载功能，包括确认提示和备份选项。
"""

import sys
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional


def uninstall_agent(force: bool = False, backup: bool = True) -> None:
    """Uninstall Agent-Z.
    
    Args:
        force: Skip confirmation
        backup: Create backup before uninstall
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info, print_warning
    
    print_header("🗑️ 卸载 Agent-Z")
    
    config_dir = Path.home() / ".agent_z"
    
    if not config_dir.exists():
        print_error("未找到配置目录，Agent 可能未安装")
        return
    
    # 显示将要删除的内容
    print()
    print_warning("以下内容将被删除:")
    print()
    
    items_to_delete = [
        ("配置目录", config_dir),
        ("PID 文件", Path.home() / ".agent_z" / "*.pid"),
        ("Socket 文件", Path.home() / ".agent_z" / "*.sock"),
    ]
    
    for name, path in items_to_delete:
        if isinstance(path, Path) and path.exists():
            print(f"  • {name}: {path}")
        elif "*" in str(path):
            print(f"  • {name}: {str(path).replace('*', '*')}")
    
    print()
    
    # 确认提示
    if not force:
        print_info("此操作不可撤销！")
        print()
        
        response = input(color("  确认卸载? (输入 'yes' 继续): ", Colors.YELLOW)).strip().lower()
        
        if response != "yes":
            print()
            print_info("卸载已取消")
            return
    
    # 备份选项
    backup_path = None
    if backup:
        backup_path = _create_backup(config_dir)
        if backup_path:
            print_success(f"备份已保存到: {backup_path}")
    
    # 删除配置目录
    print()
    print_info("正在删除配置...")
    
    try:
        shutil.rmtree(config_dir)
        print_success("配置目录已删除")
    except Exception as e:
        print_error(f"删除失败: {e}")
        return
    
    # 显示 pip 卸载提示
    print()
    print_info("如需完全移除，请运行:")
    print()
    print(color(f"  pip uninstall Agent-Z", Colors.DIM))
    print()
    
    print_success("卸载完成！")
    print()
    print_info("感谢使用 Agent-Z")


def _create_backup(config_dir: Path) -> Optional[Path]:
    """创建备份"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_info, print_error
    
    print_info("正在创建备份...")
    
    try:
        # 创建备份目录
        backup_dir = Path.home() / ".agent_z_backup"
        if backup_dir.exists():
            # 添加时间戳避免覆盖
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path.home() / f".agent_z_backup_{timestamp}"
        
        # 复制文件
        shutil.copytree(config_dir, backup_dir)
        
        # 创建 zip 压缩包
        zip_path = backup_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(backup_dir)
                    zipf.write(file_path, arcname)
        
        # 删除原始备份目录
        shutil.rmtree(backup_dir)
        
        return zip_path
        
    except Exception as e:
        print_error(f"备份失败: {e}")
        return None


def restore_from_backup(backup_path: Optional[Path] = None) -> None:
    """从备份恢复"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info
    
    print_header("♻️ 从备份恢复")
    
    if not backup_path:
        # 查找最新的备份
        backup_dir = Path.home()
        backups = list(backup_dir.glob(".agent_z_backup*.zip"))
        
        if not backups:
            print_error("没有找到备份文件")
            return
        
        backup_path = max(backups, key=lambda p: p.stat().st_mtime)
    
    print_info(f"恢复自: {backup_path}")
    
    try:
        # 解压备份
        extract_dir = Path.home() / ".agent_z_backup_temp"
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(extract_dir)
        
        # 移动到目标位置
        config_dir = Path.home() / ".agent_z"
        
        if config_dir.exists():
            shutil.rmtree(config_dir)
        
        # 找到解压的目录
        extracted = next(extract_dir.iterdir())
        shutil.move(str(extracted), str(config_dir))
        
        # 清理临时目录
        shutil.rmtree(extract_dir)
        
        print_success("恢复完成！")
        
    except Exception as e:
        print_error(f"恢复失败: {e}")


def list_backups() -> None:
    """列出可用的备份"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_info
    
    print_header("📦 可用备份")
    
    backup_dir = Path.home()
    backups = list(backup_dir.glob(".agent_z_backup*.zip"))
    
    if not backups:
        print_info("没有找到备份文件")
        return
    
    print()
    for backup in sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True):
        size = backup.stat().st_size / 1024  # KB
        time_str = backup.stat().st_mtime
        
        from datetime import datetime
        dt = datetime.fromtimestamp(time_str)
        time_str = dt.strftime("%Y-%m-%d %H:%M")
        
        print(f"  • {backup.name}")
        print(f"    大小: {size:.1f} KB")
        print(f"    时间: {time_str}")
        print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Uninstall Agent-Z")
    parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    parser.add_argument("--no-backup", action="store_true", help="Don't create backup")
    parser.add_argument("action", nargs="?", choices=["backup", "restore", "list"],
                        help="Additional actions")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        from common.terminal.ui import print_info
        print_info("创建备份...")
        # 备份功能已整合到卸载中
    elif args.action == "restore":
        restore_from_backup()
    elif args.action == "list":
        list_backups()
    else:
        uninstall_agent(force=args.force, backup=not args.no_backup)