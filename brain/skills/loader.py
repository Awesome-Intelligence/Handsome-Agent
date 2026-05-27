"""
技能加载器
从 ~/.skills/ 目录加载技能
"""

import os
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class LoadedSkill:
    """加载的技能"""
    skill_id: str
    name: str
    description: str
    command: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]
    path: str


class SkillsLoader:
    """技能加载器"""
    
    def __init__(self, skills_dir: str = "~/.skills"):
        self.skills_dir = Path(skills_dir).expanduser()
    
    async def load_all(self) -> List[LoadedSkill]:
        """加载所有技能"""
        skills = []
        
        if not self.skills_dir.exists():
            # 创建默认技能目录
            self._create_default_skills()
            return []
        
        for skill_file in self.skills_dir.rglob("*.skill"):
            try:
                skill = await self._load_skill_file(skill_file)
                if skill:
                    skills.append(skill)
            except Exception as e:
                print(f"Failed to load skill {skill_file}: {e}")
        
        return skills
    
    async def _load_skill_file(self, skill_file: Path) -> LoadedSkill:
        """加载单个技能文件"""
        with open(skill_file, 'r', encoding='utf-8') as f:
            if skill_file.suffix == '.yaml' or skill_file.suffix == '.yml':
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return LoadedSkill(
            skill_id=data.get("id", skill_file.stem),
            name=data.get("name", skill_file.stem),
            description=data.get("description", ""),
            command=data.get("command", ""),
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {}),
            path=str(skill_file),
        )
    
    def _create_default_skills(self) -> None:
        """创建默认技能目录和示例"""
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # 示例技能
        default_skill = {
            "id": "greet",
            "name": "问候",
            "description": "简单的问候语",
            "command": "echo 'Hello!'",
            "parameters": {},
            "metadata": {
                "keywords": ["hello", "hi", "你好", "问候"],
                "version": "1.0.0",
            }
        }
        
        skill_file = self.skills_dir / "greet.skill"
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(default_skill, f, ensure_ascii=False, indent=2)