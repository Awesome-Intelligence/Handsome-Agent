#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Bundle Module - 技能包管理机制

提供技能包的创建、加载、删除和批量执行功能。
技能包是一组预定义的技能集合，可通过单个命令批量加载。

日志子层：📋 SkillBundle
"""

import re
from pathlib import Path

from common.file_utils import atomic_replace
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Tuple

import yaml

from dataclasses import dataclass, field
from common.logging_manager import get_execution_logger

if TYPE_CHECKING:
    from agent.skills.skill_manager import SkillManager, SkillResult

logger = get_execution_logger("SkillBundle")


@dataclass
class SkillBundle:
    """技能包定义"""
    name: str
    slug: str
    description: str = ""
    skills: List[str] = field(default_factory=list)
    instruction: str = ""
    path: str = ""


class SkillBundleManager:
    """技能包管理器"""
    
    def __init__(self, bundles_dir: Optional[str] = None):
        """
        初始化技能包管理器
        
        Args:
            bundles_dir: bundles 目录路径，默认为 ~/.agent_z/skill-bundles/
        """
        self._bundles_dir = self._get_bundles_dir(bundles_dir)
        self._ensure_bundles_dir()
        self._cache: Dict[str, SkillBundle] = {}
    
    @staticmethod
    def _get_bundles_dir(bundles_dir: Optional[str] = None) -> Path:
        """
        获取 bundles 目录
        
        Args:
            bundles_dir: 自定义路径，如果为 None 则使用默认路径
        
        Returns:
            Path: bundles 目录路径
        """
        if bundles_dir:
            return Path(bundles_dir)
        return Path.home() / ".agent_z" / "skill-bundles"
    
    def _ensure_bundles_dir(self) -> None:
        """确保 bundles 目录存在"""
        self._bundles_dir.mkdir(parents=True, exist_ok=True)
    
    def _slugify(self, name: str) -> str:
        """
        将名称转换为 URL 友好格式
        
        Args:
            name: 原始名称
        
        Returns:
            str: URL 友好格式的 slug
        """
        slug = name.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'^-+|-+$', '', slug)
        return slug
    
    def _get_bundle_path(self, bundle_name: str) -> Path:
        """获取 Bundle 文件路径"""
        slug = self._slugify(bundle_name)
        return self._bundles_dir / f"{slug}.yaml"
    
    def load_bundle(self, bundle_name: str) -> Optional[SkillBundle]:
        """
        加载指定 Bundle
        
        Args:
            bundle_name: Bundle 名称
        
        Returns:
            Optional[SkillBundle]: 加载的 Bundle，未找到则返回 None
        """
        slug = self._slugify(bundle_name)
        
        if slug in self._cache:
            return self._cache[slug]
        
        bundle_path = self._bundles_dir / f"{slug}.yaml"
        
        if not bundle_path.exists():
            logger.warning(f"Bundle 未找到: {bundle_name}")
            return None
        
        try:
            with open(bundle_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Bundle 文件为空: {bundle_path}")
                return None
            
            bundle = SkillBundle(
                name=data.get('name', bundle_name),
                slug=slug,
                description=data.get('description', ''),
                skills=data.get('skills', []),
                instruction=data.get('instruction', ''),
                path=str(bundle_path)
            )
            
            self._cache[slug] = bundle
            logger.info(f"加载 Bundle: {bundle.name} (包含 {len(bundle.skills)} 个技能)")
            return bundle
            
        except yaml.YAMLError as e:
            logger.error(f"解析 YAML 失败 {bundle_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载 Bundle 失败 {bundle_name}: {e}")
            return None
    
    def create_bundle(
        self,
        name: str,
        skills: List[str],
        description: str = "",
        instruction: str = ""
    ) -> bool:
        """
        创建 Bundle（保存为 YAML）
        
        Args:
            name: Bundle 名称
            skills: 引用的技能列表
            description: Bundle 描述
            instruction: 额外指令
        
        Returns:
            bool: 创建是否成功
        """
        slug = self._slugify(name)
        bundle_path = self._bundles_dir / f"{slug}.yaml"
        
        if bundle_path.exists():
            logger.warning(f"Bundle 已存在: {name}")
            return False
        
        bundle_data = {
            'name': name,
            'description': description,
            'skills': skills,
            'instruction': instruction
        }
        
        try:
            yaml_content = yaml.dump(
                bundle_data,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
            
            content = f"# Skill Bundle: {name}\n# 自动生成\n\n{yaml_content}"
            
            tmp_path = bundle_path.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            atomic_replace(tmp_path, bundle_path)
            
            bundle = SkillBundle(
                name=name,
                slug=slug,
                description=description,
                skills=skills,
                instruction=instruction,
                path=str(bundle_path)
            )
            self._cache[slug] = bundle
            
            logger.info(f"创建 Bundle: {name} (包含 {len(skills)} 个技能)")
            return True
            
        except Exception as e:
            logger.error(f"创建 Bundle 失败 {name}: {e}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            return False
    
    def delete_bundle(self, name: str) -> bool:
        """
        删除 Bundle
        
        Args:
            name: Bundle 名称
        
        Returns:
            bool: 删除是否成功
        """
        slug = self._slugify(name)
        bundle_path = self._bundles_dir / f"{slug}.yaml"
        
        if not bundle_path.exists():
            logger.warning(f"Bundle 不存在: {name}")
            return False
        
        try:
            bundle_path.unlink()
            
            if slug in self._cache:
                del self._cache[slug]
            
            logger.info(f"删除 Bundle: {name}")
            return True
            
        except Exception as e:
            logger.error(f"删除 Bundle 失败 {name}: {e}")
            return False
    
    def list_bundles(self) -> List[SkillBundle]:
        """
        列出所有 Bundle
        
        Returns:
            List[SkillBundle]: 所有已加载的 Bundle 列表
        """
        bundles = []
        
        if not self._bundles_dir.exists():
            return bundles
        
        for yaml_file in self._bundles_dir.glob("*.yaml"):
            slug = yaml_file.stem
            if slug in self._cache:
                bundles.append(self._cache[slug])
            else:
                bundle = self._load_bundle_from_file(yaml_file)
                if bundle:
                    self._cache[slug] = bundle
                    bundles.append(bundle)
        
        logger.debug(f"列出 {len(bundles)} 个 Bundle")
        return bundles
    
    def _load_bundle_from_file(self, bundle_path: Path) -> Optional[SkillBundle]:
        """从文件加载 Bundle（不缓存）"""
        try:
            with open(bundle_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = re.sub(r'^#.*\n', '', content, flags=re.MULTILINE)
            
            data = yaml.safe_load(content)
            
            if not data:
                return None
            
            return SkillBundle(
                name=data.get('name', bundle_path.stem),
                slug=bundle_path.stem,
                description=data.get('description', ''),
                skills=data.get('skills', []),
                instruction=data.get('instruction', ''),
                path=str(bundle_path)
            )
            
        except Exception as e:
            logger.warning(f"从文件加载 Bundle 失败 {bundle_path}: {e}")
            return None
    
    def invoke_bundle(
        self,
        bundle_name: str,
        skill_manager: "SkillManager",
        context: Optional[Dict[str, Any]] = None
    ) -> List["SkillResult"]:
        """
        执行 Bundle，加载所有引用的技能
        
        Args:
            bundle_name: Bundle 名称
            skill_manager: 技能管理器实例
            context: 执行上下文
        
        Returns:
            List[SkillResult]: 所有技能执行结果列表
        """
        bundle = self.load_bundle(bundle_name)
        
        if not bundle:
            logger.error(f"Bundle 不存在: {bundle_name}")
            return []
        
        logger.info(f"执行 Bundle: {bundle.name}")
        
        if bundle.instruction:
            logger.debug(f"Bundle 指令: {bundle.instruction[:100]}...")
        
        results = []
        
        for skill_id in bundle.skills:
            skill = skill_manager.get_skill(skill_id)
            
            if not skill:
                logger.warning(f"Bundle 中引用的技能不存在: {skill_id}")
                from agent.skills.skill_manager import SkillResult
                results.append(SkillResult(
                    success=False,
                    output="",
                    error=f"Skill not found: {skill_id}"
                ))
                continue
            
            try:
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    skill.execute(**(context or {}))
                )
                results.append(result)
                
                if result.success:
                    logger.debug(f"技能执行成功: {skill_id}")
                else:
                    logger.warning(f"技能执行失败: {skill_id} - {result.error}")
                    
            except Exception as e:
                logger.error(f"执行技能异常 {skill_id}: {e}")
                from agent.skills.skill_manager import SkillResult
                results.append(SkillResult(
                    success=False,
                    output="",
                    error=str(e)
                ))
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Bundle 执行完成: {success_count}/{len(results)} 个技能成功")
        
        return results
    
    def validate_bundle_skills(
        self,
        bundle_name: str,
        skill_manager: "SkillManager"
    ) -> Dict[str, bool]:
        """
        验证 Bundle 中引用的技能是否存在
        
        Args:
            bundle_name: Bundle 名称
            skill_manager: 技能管理器实例
        
        Returns:
            Dict[str, bool]: 技能ID -> 是否存在
        """
        bundle = self.load_bundle(bundle_name)
        
        if not bundle:
            return {}
        
        validation = {}
        for skill_id in bundle.skills:
            validation[skill_id] = skill_manager.get_skill(skill_id) is not None
        
        return validation
    
    def get_bundle_info(self, bundle_name: str) -> Optional[Dict[str, Any]]:
        """
        获取 Bundle 详细信息
        
        Args:
            bundle_name: Bundle 名称
        
        Returns:
            Optional[Dict[str, Any]]: Bundle 信息字典
        """
        bundle = self.load_bundle(bundle_name)
        
        if not bundle:
            return None
        
        return {
            'name': bundle.name,
            'slug': bundle.slug,
            'description': bundle.description,
            'skills': bundle.skills,
            'skills_count': len(bundle.skills),
            'instruction': bundle.instruction,
            'path': bundle.path
        }
    
    def activate_bundle(
        self,
        bundle_name: str,
        skill_manager: "SkillManager",
    ) -> Dict[str, Any]:
        """
        批量激活 Bundle 中的所有技能
        
        Args:
            bundle_name: Bundle 名称
            skill_manager: 技能管理器实例
        
        Returns:
            激活结果字典
        """
        bundle = self.load_bundle(bundle_name)
        
        if not bundle:
            return {
                'success': False,
                'error': f"Bundle not found: {bundle_name}",
                'activated': [],
                'failed': [],
            }
        
        logger.info(f"激活 Bundle: {bundle.name} (包含 {len(bundle.skills)} 个技能)")
        
        activated = []
        failed = []
        
        for skill_id in bundle.skills:
            skill = skill_manager.get_skill(skill_id)
            
            if not skill:
                logger.warning(f"Bundle 中引用的技能不存在: {skill_id}")
                failed.append({
                    'skill_id': skill_id,
                    'reason': 'Skill not found',
                })
                continue
            
            # 注册到技能管理器（如果尚未注册）
            if skill_id not in skill_manager.skills:
                try:
                    skill_manager.register_skill(skill)
                    activated.append(skill_id)
                    logger.debug(f"激活技能: {skill_id}")
                except Exception as e:
                    logger.error(f"激活技能失败 {skill_id}: {e}")
                    failed.append({
                        'skill_id': skill_id,
                        'reason': str(e),
                    })
            else:
                logger.debug(f"技能已激活: {skill_id}")
                activated.append(skill_id)
        
        return {
            'success': len(failed) == 0,
            'bundle_name': bundle.name,
            'total': len(bundle.skills),
            'activated': activated,
            'failed': failed,
        }
    
    def resolve_bundle_dependencies(
        self,
        bundle_name: str,
    ) -> List[str]:
        """
        解析 Bundle 的技能依赖（递归）
        
        Args:
            bundle_name: Bundle 名称
        
        Returns:
            按依赖顺序排列的技能列表
        """
        visited = set()
        result = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            bundle = self.load_bundle(name)
            if bundle:
                for skill_id in bundle.skills:
                    visit(skill_id)
                result.append(name)
        
        visit(bundle_name)
        return result


bundle_manager = SkillBundleManager()


def get_bundle_manager() -> SkillBundleManager:
    """获取全局 Bundle 管理器实例"""
    return bundle_manager


# =============================================================================
# 兼容层 - 为了向后兼容 agent.skill_bundles 的函数式 API
# =============================================================================

# 延迟导入，避免循环依赖
_bundle_instance: Optional["SkillBundleManager"] = None


def _get_instance() -> "SkillBundleManager":
    """获取兼容层实例"""
    global _bundle_instance
    if _bundle_instance is None:
        _bundle_instance = SkillBundleManager()
    return _bundle_instance


def build_bundle_invocation_message(
    cmd_key: str,
    user_instruction: str = "",
    session_id: Optional[str] = None,
) -> Optional[Tuple[str, List[str], List[str]]]:
    """构建 bundle slash 命令调用的用户消息内容（兼容函数）"""
    bundles = get_skill_bundles()
    info = bundles.get(cmd_key)
    if not info:
        return None

    loaded_names: List[str] = []
    missing: List[str] = []
    skill_blocks: List[str] = []
    seen: set = set()

    bundle_name = info["name"]
    skills = info["skills"]
    extra_instruction = info.get("instruction") or ""

    # 加载每个技能
    for skill_id in skills:
        identifier = (skill_id or "").strip()
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)

        # 尝试从技能加载器获取技能内容
        loaded = _load_skill_payload_compat(identifier, session_id=session_id)
        if not loaded:
            missing.append(identifier)
            continue

        loaded_skill, skill_dir, skill_name = loaded
        loaded_names.append(skill_name)

        activation_note = f'[Loaded as part of the "{bundle_name}" skill bundle.]'
        skill_blocks.append(f"{activation_note}\n\n{loaded_skill}")

    if not skill_blocks:
        return None

    # 构建头部
    header_lines = [
        f'[IMPORTANT: The user has invoked the "{bundle_name}" skill bundle, '
        f"loading {len(loaded_names)} skills together. Treat every skill below "
        "as active guidance for this turn.]",
        "",
        f"Bundle: {bundle_name}",
        f"Skills loaded: {', '.join(loaded_names)}",
    ]
    if missing:
        header_lines.append(f"Skills missing (skipped): {', '.join(missing)}")
    if extra_instruction:
        header_lines.extend(["", f"Bundle instruction: {extra_instruction}"])
    if user_instruction:
        header_lines.extend(["", f"User instruction: {user_instruction}"])

    header = "\n".join(header_lines)
    return ("\n\n".join([header, *skill_blocks]), loaded_names, missing)


def _load_skill_payload_compat(skill_id: str, session_id: Optional[str] = None) -> Optional[Tuple[str, Path, str]]:
    """加载技能内容（兼容函数）"""
    try:
        from agent.skill_utils import get_skill_by_name
        skill = get_skill_by_name(skill_id)
        if skill:
            return (skill.get("content", ""), Path(skill.get("path", ".")), skill_id)
    except Exception:
        pass

    # 尝试从文件系统加载
    try:
        from agent.skill_utils import iter_skill_index_files, parse_frontmatter
        from common.config import get_config_dir

        skills_dir = get_config_dir() / "skills"
        for skill_md in iter_skill_index_files(skills_dir, "SKILL.md"):
            try:
                content = skill_md.read_text(encoding="utf-8")
                fm, _ = parse_frontmatter(content)
                name = fm.get("name", "")
                if name == skill_id or skill_md.parent.name == skill_id:
                    return (content, skill_md.parent, name or skill_md.parent.name)
            except Exception:
                continue
    except Exception:
        pass

    return None


def _build_skill_message(content: str, skill_dir: Path, activation_note: str) -> str:
    """构建技能消息（兼容函数）"""
    return f"{activation_note}\n\n{content}"


def bundle_path_for(name: str) -> Path:
    """获取 bundle 文件路径（兼容函数）"""
    return _get_instance()._get_bundle_path(name)


def save_bundle(
    name: str,
    skills: List[str],
    description: str = "",
    instruction: str = "",
    overwrite: bool = False,
) -> Path:
    """保存 bundle 到磁盘（兼容函数）"""
    manager = _get_instance()
    # SkillBundleManager.create_bundle 返回 bool，这里需要返回 Path
    success = manager.create_bundle(name, skills, description, instruction)
    if success:
        return bundle_path_for(name)
    raise FileExistsError(f"Bundle already exists: {name}")


def delete_bundle(name: str) -> Path:
    """删除 bundle（兼容函数）"""
    manager = _get_instance()
    manager.delete_bundle(name)
    return bundle_path_for(name)


def get_bundle(name: str) -> Optional[Dict[str, Any]]:
    """按名称查找 bundle（兼容函数）"""
    info = _get_instance().get_bundle_info(name)
    return info
