"""URL 技能来源"""

import re
import zipfile
import tarfile
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, unquote
import logging

from .base import SkillSource, SourceResult, SourceSkillInfo

logger = logging.getLogger(__name__)


class UrlSource(SkillSource):
    """URL 技能来源"""
    
    SOURCE_TYPE = "url"
    
    # 匹配格式: https://... 或 http://...
    PATTERN = re.compile(r'^https?://')
    
    def __init__(self):
        super().__init__("URL")
    
    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE
    
    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        if self.PATTERN.match(ref):
            return {'url': ref}
        return None
    
    async def search(self, query: str) -> List[SourceSkillInfo]:
        """URL 来源不支持搜索"""
        return []
    
    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """从 URL 安装技能"""
        parsed = self.parse_ref(skill_ref)
        if not parsed:
            return SourceResult(
                success=False,
                skill_name="",
                error=f"Invalid URL: {skill_ref}",
                source_name=self.name,
            )
        
        url = parsed['url']
        skill_name = _extract_filename(url)
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return SourceResult(
                            success=False,
                            skill_name=skill_name,
                            error=f"Download failed: {resp.status}",
                            source_name=self.name,
                        )
                    
                    data = await resp.read()
            
            # 检测文件类型并解压
            skill_dir = target_dir / skill_name
            
            if url.endswith('.zip'):
                self._extract_zip(data, skill_dir)
            elif url.endswith('.tar.gz') or url.endswith('.tgz'):
                self._extract_tar(data, skill_dir)
            else:
                # 单文件，直接保存为 SKILL.md
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_bytes(data)
            
            return SourceResult(
                success=True,
                skill_name=skill_name,
                skill_data=data,
                metadata={'path': str(skill_dir)},
                source_name=self.name,
            )
            
        except ImportError:
            return SourceResult(
                success=False,
                skill_name=skill_name,
                error="aiohttp not available",
                source_name=self.name,
            )
        except Exception as e:
            logger.error(f"URL install failed: {e}")
            return SourceResult(
                success=False,
                skill_name=skill_name,
                error=str(e),
                source_name=self.name,
            )
    
    def _extract_zip(self, data: bytes, target_dir: Path):
        """解压 ZIP 文件"""
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(target_dir)
    
    def _extract_tar(self, data: bytes, target_dir: Path):
        """解压 TAR.GZ 文件"""
        target_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tf:
            tf.extractall(target_dir)


def _extract_filename(url: str) -> str:
    """从 URL 提取文件名"""
    path = urlparse(url).path
    name = unquote(path.split('/')[-1])
    return name.rsplit('.', 1)[0] if '.' in name else name
