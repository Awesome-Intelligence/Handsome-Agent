#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Computer Use Skill Implementation - 系统操作技能
"""

import subprocess
import json
import os
from typing import Optional

from core.skill_manager import BaseSkill, SkillResult, SkillMetadata, SkillParameter


class ComputerUseSkill(BaseSkill):
    """系统操作技能：打开文件夹、浏览器、获取系统信息等"""
    
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="computer-use",
            name="Computer Use",
            description="系统操作技能：打开文件夹、浏览器、应用程序等",
            category="system",
            parameters=[
                SkillParameter(
                    name="action",
                    type=str,
                    description="操作类型: open_folder, open_browser, list_browsers, get_system_info",
                    required=True
                ),
                SkillParameter(
                    name="path",
                    type=str,
                    description="文件夹路径（用于open_folder）",
                    required=False
                ),
                SkillParameter(
                    name="url",
                    type=str,
                    description="网址（用于open_browser）",
                    required=False
                ),
                SkillParameter(
                    name="browser",
                    type=str,
                    description="浏览器名称: chrome, edge, firefox（用于open_browser）",
                    required=False
                ),
                SkillParameter(
                    name="info_type",
                    type=str,
                    description="信息类型: os, cpu, memory, disk, all（用于get_system_info）",
                    required=False,
                    default="all"
                )
            ],
            aliases=["computer-use", "打开文件夹", "打开浏览器", "系统操作"],
            examples=[
                "打开当前文件夹",
                "打开浏览器访问百度",
                "列出已安装的浏览器",
                "获取系统信息"
            ],
            source="system",
            version="1.0.0",
            author="Handsome Agent",
            license="MIT",
            platforms=["windows", "linux", "macos"],
            tags=["system", "computer", "file", "browser", "folder", "open"],
            related_skills=["terminal"]
        )
    
    def _run_script(self, action: str, **kwargs) -> SkillResult:
        """运行脚本执行操作"""
        try:
            script_path = os.path.join(
                os.path.dirname(__file__),
                "scripts",
                "computer_ops.py"
            )
            
            if not os.path.exists(script_path):
                return SkillResult(
                    success=False,
                    output="",
                    error=f"脚本文件不存在: {script_path}"
                )
            
            cmd = ["python", script_path, action]
            
            if action == "open_folder" and kwargs.get("path"):
                cmd.append(kwargs["path"])
            elif action == "open_browser":
                if kwargs.get("url"):
                    cmd.append(f"url={kwargs['url']}")
                if kwargs.get("browser"):
                    cmd.append(f"browser={kwargs['browser']}")
            elif action == "get_system_info" and kwargs.get("info_type"):
                cmd.append(kwargs["info_type"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    return SkillResult(
                        success=data.get("success", True),
                        output=data.get("output", result.stdout.strip()),
                        data=data
                    )
                except json.JSONDecodeError:
                    return SkillResult(
                        success=True,
                        output=result.stdout.strip()
                    )
            else:
                return SkillResult(
                    success=False,
                    output="",
                    error=result.stderr.strip()
                )
        except subprocess.TimeoutExpired:
            return SkillResult(success=False, output="", error="操作超时")
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))
    
    async def execute(self, action: str, **kwargs) -> SkillResult:
        """执行系统操作"""
        action = action.lower().strip()
        
        if action == "open_folder":
            return self._run_script("open_folder", path=kwargs.get("path"))
        
        elif action == "open_browser":
            return self._run_script(
                "open_browser",
                url=kwargs.get("url"),
                browser=kwargs.get("browser")
            )
        
        elif action == "list_browsers":
            return self._run_script("list_browsers")
        
        elif action == "get_system_info":
            return self._run_script(
                "get_system_info",
                info_type=kwargs.get("info_type", "all")
            )
        
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"未知操作类型: {action}。可用操作: open_folder, open_browser, list_browsers, get_system_info"
            )


computer_use_skill = ComputerUseSkill()
