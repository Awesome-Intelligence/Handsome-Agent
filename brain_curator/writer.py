"""
技能写入器
将新技能写入 Skill DB
"""

import json
from pathlib import Path
from typing import Optional
from .synthesizer import SynthesizedSkill


class SkillWriter:
    """技能写入器"""
    
    def __init__(self, skills_dir: str = "~/.skills"):
        self.skills_dir = Path(skills_dir).expanduser()
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    async def write(self, skill: SynthesizedSkill, dry_run: bool = False) -> str:
        """
        写入技能到文件系统
        
        Args:
            skill: 要写入的技能
            dry_run: 如果为 True，不实际写入，只返回路径
        """
        # 生成技能文件名
        skill_file = self.skills_dir / f"{skill.name}.skill"
        
        # 转换为可写入格式
        skill_data = {
            "id": skill.name,
            "name": skill.name,
            "description": skill.description,
            "command": skill.action_template,
            "parameters": {},
            "metadata": {
                "keywords": skill.trigger_patterns,
                "confidence": skill.confidence,
                "synthesized": True,
            }
        }
        
        if not dry_run:
            with open(skill_file, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        return str(skill_file)
    
    async def update(self, skill_id: str, updates: dict) -> bool:
        """更新已有技能"""
        skill_file = self.skills_dir / f"{skill_id}.skill"
        
        if not skill_file.exists():
            return False
        
        # 读取现有数据
        with open(skill_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 更新字段
        data.update(updates)
        
        # 写回
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    
    async def delete(self, skill_id: str) -> bool:
        """删除技能"""
        skill_file = self.skills_dir / f"{skill_id}.skill"
        
        if skill_file.exists():
            skill_file.unlink()
            return True
        
        return False