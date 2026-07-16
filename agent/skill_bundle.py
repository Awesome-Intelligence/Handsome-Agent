#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Bundle - 技能导入/导出/打包工具

提供技能批量操作功能：
- 导出技能到压缩包
- 从压缩包导入技能
- 技能打包和分发

🚪 Access - 📋 Skills - 导入导出
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile

from common.config import get_skills_dir
from common.logging_manager import get_execution_logger

logger = get_execution_logger("SkillBundle")

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".md", ".py", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json", ".txt", ".toml"}
# 允许的目录
ALLOWED_DIRS = {"references", "templates", "scripts", "assets"}
# 最大打包大小 (100MB)
MAX_BUNDLE_SIZE = 100 * 1024 * 1024


@dataclass
class BundleEntry:
    """打包条目"""
    skill_name: str
    skill_data: Dict[str, Any]  # {file_path: content}
    metadata: Dict[str, Any]  # 打包元数据


@dataclass
class BundleManifest:
    """打包清单"""
    version: str = "1.0"
    created_at: str = ""
    created_by: str = "Agent-Z"
    skills: List[Dict[str, Any]] = field(default_factory=list)
    total_size: int = 0
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "skills": self.skills,
            "total_size": self.total_size,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BundleManifest:
        return cls(
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", ""),
            created_by=data.get("created_by", "Agent-Z"),
            skills=data.get("skills", []),
            total_size=data.get("total_size", 0),
            checksum=data.get("checksum", ""),
        )


@dataclass
class ExportOptions:
    """导出选项"""
    include_metadata: bool = True  # 包含元数据
    include_lock_info: bool = True  # 包含锁定信息
    compress: bool = True  # 压缩
    exclude_patterns: List[str] = field(default_factory=list)  # 排除模式


@dataclass
class ImportOptions:
    """导入选项"""
    overwrite: bool = False  # 覆盖已存在的技能
    skip_validation: bool = False  # 跳过验证
    dry_run: bool = False  # 预览模式
    target_category: Optional[str] = None  # 目标分类


class SkillBundle:
    """
    技能打包工具

    支持：
    - 导出技能到 .zip 文件
    - 从 .zip 文件导入技能
    - 批量操作
    """

    def __init__(self):
        self._skills_dir = get_skills_dir()

    def export_skill(
        self,
        skill_name: str,
        output_path: Path,
        options: Optional[ExportOptions] = None,
    ) -> bool:
        """
        导出单个技能

        Args:
            skill_name: 技能名称
            output_path: 输出文件路径
            options: 导出选项

        Returns:
            是否成功
        """
        options = options or ExportOptions()

        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            logger.error(f"Skill not found: {skill_name}")
            return False

        # 获取技能文件
        skill_data = self._collect_skill_files(skill_dir, options.exclude_patterns)
        if not skill_data:
            logger.error(f"No files found for skill: {skill_name}")
            return False

        # 创建打包清单
        manifest = self._create_manifest([skill_name], skill_data, options)

        # 写入 zip 文件
        return self._write_bundle(output_path, {skill_name: skill_data}, manifest, options)

    def export_skills(
        self,
        skill_names: List[str],
        output_path: Path,
        options: Optional[ExportOptions] = None,
    ) -> bool:
        """
        批量导出技能

        Args:
            skill_names: 技能名称列表
            output_path: 输出文件路径
            options: 导出选项

        Returns:
            是否成功
        """
        options = options or ExportOptions()

        # 收集所有技能数据
        all_data = {}
        for name in skill_names:
            skill_dir = self._skills_dir / name
            if not skill_dir.exists():
                logger.warning(f"Skill not found, skipping: {name}")
                continue

            skill_data = self._collect_skill_files(skill_dir, options.exclude_patterns)
            if skill_data:
                all_data[name] = skill_data

        if not all_data:
            logger.error("No skills to export")
            return False

        # 创建打包清单
        manifest = self._create_manifest(skill_names, all_data, options)

        # 写入 zip 文件
        return self._write_bundle(output_path, all_data, manifest, options)

    def export_all(self, output_path: Path, options: Optional[ExportOptions] = None) -> bool:
        """
        导出所有技能

        Args:
            output_path: 输出文件路径
            options: 导出选项

        Returns:
            是否成功
        """
        # 获取所有技能
        skill_names = []
        if self._skills_dir.exists():
            for item in self._skills_dir.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    skill_names.append(item.name)

        return self.export_skills(skill_names, output_path, options)

    def _collect_skill_files(
        self,
        skill_dir: Path,
        exclude_patterns: List[str] = None,
    ) -> Dict[str, str]:
        """收集技能文件"""
        data = {}

        for file_path in skill_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # 检查是否为允许的文件
            if file_path.suffix not in ALLOWED_EXTENSIONS and file_path.suffix != "":
                continue

            # 检查是否在允许的目录中
            rel_path = file_path.relative_to(skill_dir)
            if len(rel_path.parts) > 1 and rel_path.parts[0] not in ALLOWED_DIRS:
                continue

            # 检查排除模式
            if exclude_patterns:
                skip = False
                for pattern in exclude_patterns:
                    if pattern in str(rel_path):
                        skip = True
                        break
                if skip:
                    continue

            try:
                content = file_path.read_text(encoding="utf-8")
                data[str(rel_path)] = content
            except Exception as e:
                logger.warning(f"Failed to read {rel_path}: {e}")

        return data

    def _create_manifest(
        self,
        skill_names: List[str],
        all_data: Dict[str, Dict[str, str]],
        options: ExportOptions,
    ) -> BundleManifest:
        """创建打包清单"""
        manifest = BundleManifest(
            version="1.0",
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by="Agent-Z",
        )

        for name in skill_names:
            if name not in all_data:
                continue

            skill_data = all_data[name]

            # 计算技能大小
            skill_size = sum(len(content.encode()) for content in skill_data.values())

            skill_info = {
                "name": name,
                "files": list(skill_data.keys()),
                "file_count": len(skill_data),
                "size": skill_size,
            }

            # 添加元数据
            if options.include_metadata and "SKILL.md" in skill_data:
                from agent.skill_utils import parse_frontmatter
                frontmatter, _ = parse_frontmatter(skill_data["SKILL.md"])
                skill_info["metadata"] = {
                    "name": frontmatter.get("name", name),
                    "description": frontmatter.get("description", ""),
                    "version": frontmatter.get("version", "1.0.0"),
                    "author": frontmatter.get("author", ""),
                    "category": frontmatter.get("category", ""),
                }

            # 添加锁定信息
            if options.include_lock_info:
                try:
                    from agent.skill_lock import get_skill_lock_info
                    lock_info = get_skill_lock_info(name)
                    if lock_info:
                        skill_info["lock"] = {
                            "source": lock_info.source,
                            "identifier": lock_info.identifier,
                            "installed_at": lock_info.installed_at,
                        }
                except Exception:
                    pass

            manifest.skills.append(skill_info)
            manifest.total_size += skill_size

        return manifest

    def _write_bundle(
        self,
        output_path: Path,
        all_data: Dict[str, Dict[str, str]],
        manifest: BundleManifest,
        options: ExportOptions,
    ) -> bool:
        """写入打包文件"""
        try:
            # 计算清单的 checksum
            manifest_json = json.dumps(manifest.to_dict(), sort_keys=True)
            manifest.checksum = hashlib.sha256(manifest_json.encode()).hexdigest()

            # 写入 zip 文件
            with zipfile.ZipFile(
                output_path,
                "w",
                compression=zipfile.ZIP_DEFLATED if options.compress else zipfile.ZIP_STORED,
            ) as zf:
                # 写入清单
                zf.writestr(
                    "manifest.json",
                    json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
                )

                # 写入每个技能的文件
                for skill_name, skill_data in all_data.items():
                    for file_path, content in skill_data.items():
                        arcname = f"skills/{skill_name}/{file_path}"
                        zf.writestr(arcname, content.encode("utf-8"))

            logger.info(f"Bundle exported: {output_path} ({manifest.total_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to write bundle: {e}")
            return False

    def import_bundle(
        self,
        bundle_path: Path,
        options: Optional[ImportOptions] = None,
    ) -> Dict[str, Any]:
        """
        导入打包文件

        Args:
            bundle_path: 打包文件路径
            options: 导入选项

        Returns:
            导入结果
        """
        options = options or ImportOptions()

        result = {
            "success": True,
            "imported": [],
            "skipped": [],
            "errors": [],
        }

        try:
            # 读取 zip 文件
            with zipfile.ZipFile(bundle_path, "r") as zf:
                # 读取清单
                manifest_data = json.loads(zf.read("manifest.json"))
                manifest = BundleManifest.from_dict(manifest_data)

                # 预览模式
                if options.dry_run:
                    result["manifest"] = manifest.to_dict()
                    return result

                # 导入每个技能
                for skill_info in manifest.skills:
                    skill_name = skill_info["name"]

                    # 检查是否已存在
                    if (self._skills_dir / skill_name).exists() and not options.overwrite:
                        result["skipped"].append({
                            "name": skill_name,
                            "reason": "already exists",
                        })
                        continue

                    # 收集技能文件
                    skill_data = {}
                    for file_path in skill_info.get("files", []):
                        arcname = f"skills/{skill_name}/{file_path}"
                        try:
                            content = zf.read(arcname).decode("utf-8")
                            skill_data[file_path] = content
                        except Exception as e:
                            result["errors"].append({
                                "name": skill_name,
                                "file": file_path,
                                "error": str(e),
                            })

                    # 验证技能
                    if not options.skip_validation and "SKILL.md" in skill_data:
                        validation = self._validate_skill_data(skill_data["SKILL.md"])
                        if not validation["valid"]:
                            result["errors"].append({
                                "name": skill_name,
                                "error": f"Validation failed: {validation['errors']}",
                            })
                            continue

                    # 写入技能文件
                    if not self._write_skill_files(skill_name, skill_data, options):
                        result["errors"].append({
                            "name": skill_name,
                            "error": "Failed to write files",
                        })
                        continue

                    result["imported"].append(skill_name)
                    logger.info(f"Imported skill: {skill_name}")

        except Exception as e:
            result["success"] = False
            result["errors"].append({"error": str(e)})
            logger.error(f"Failed to import bundle: {e}")

        return result

    def _validate_skill_data(self, content: str) -> Dict[str, Any]:
        """验证技能内容"""
        from agent.skill_utils import parse_frontmatter

        errors = []
        frontmatter, body = parse_frontmatter(content)

        if not frontmatter.get("name"):
            errors.append("Missing 'name' in frontmatter")

        if not frontmatter.get("description"):
            errors.append("Missing 'description' in frontmatter")

        if not body or len(body.strip()) < 10:
            errors.append("Content is too short")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def _write_skill_files(
        self,
        skill_name: str,
        skill_data: Dict[str, str],
        options: ImportOptions,
    ) -> bool:
        """写入技能文件"""
        try:
            skill_dir = self._skills_dir / skill_name

            # 如果存在且覆盖，删除旧目录
            if skill_dir.exists() and options.overwrite:
                shutil.rmtree(skill_dir)

            # 创建目录
            skill_dir.mkdir(parents=True, exist_ok=True)

            # 写入文件
            for file_path, content in skill_data.items():
                target = skill_dir / file_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            return True

        except Exception as e:
            logger.error(f"Failed to write skill files: {e}")
            return False

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出自带模板"""
        # 内置模板
        templates = [
            {
                "id": "basic",
                "name": "基础技能",
                "description": "最基础的技能模板，包含基本结构",
                "category": "template",
            },
            {
                "id": "api-client",
                "name": "API 客户端",
                "description": "用于调用外部 API 的技能模板",
                "category": "network",
            },
            {
                "id": "data-processor",
                "name": "数据处理",
                "description": "用于数据处理和转换的技能模板",
                "category": "data",
            },
            {
                "id": "automation",
                "name": "自动化脚本",
                "description": "用于自动化任务的脚本模板",
                "category": "automation",
            },
        ]
        return templates

    def create_from_template(
        self,
        template_id: str,
        skill_name: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从模板创建技能

        Args:
            template_id: 模板 ID
            skill_name: 新技能名称
            category: 可选分类

        Returns:
            创建结果
        """
        result = {
            "success": False,
            "skill_name": skill_name,
            "message": "",
        }

        # 检查技能是否已存在
        if (self._skills_dir / skill_name).exists():
            result["message"] = f"Skill '{skill_name}' already exists"
            return result

        # 获取模板内容
        template_content = self._get_template_content(template_id)
        if not template_content:
            result["message"] = f"Template not found: {template_id}"
            return result

        # 创建技能
        try:
            skill_dir = self._skills_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(template_content, encoding="utf-8")

            result["success"] = True
            result["message"] = f"Skill '{skill_name}' created from template '{template_id}'"
            logger.info(result["message"])

        except Exception as e:
            result["message"] = f"Failed to create skill: {e}"

        return result

    def _get_template_content(self, template_id: str) -> Optional[str]:
        """获取模板内容"""
        templates = {
            "basic": """---
name: {skill_name}
description: 在此添加技能描述
version: 1.0.0
author: 
category: general
platforms:
  - linux
  - macos
  - windows
triggers:
  - 
tags:
  - 
---

# {skill_name}

在这里添加技能的详细说明。

## 使用场景

描述这个技能的使用场景。

## 使用方法

1. 步骤一
2. 步骤二
3. 步骤三

## 示例

```bash
# 示例命令
example command
```

## 注意事项

- 注意事项一
- 注意事项二
""",
            "api-client": """---
name: {skill_name}
description: API 客户端技能模板
version: 1.0.0
author: 
category: network
platforms:
  - linux
  - macos
  - windows
triggers:
  - api
  - http
  - request
tags:
  - api
  - http
  - client
---

# {skill_name}

API 客户端技能模板。

## 环境变量

```bash
# 必需的环境变量
export API_KEY="your-api-key"
export API_BASE_URL="https://api.example.com"
```

## 使用方法

### 初始化客户端

```python
import requests

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("API_BASE_URL")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
```

### 发送请求

```python
# GET 请求
response = requests.get(f"{BASE_URL}/endpoint", headers=headers)

# POST 请求
data = {{"key": "value"}}
response = requests.post(f"{BASE_URL}/endpoint", json=data, headers=headers)
```

## 错误处理

```python
if response.status_code != 200:
    print(f"API Error: {{response.status_code}}")
    print(response.text)
```

## 速率限制

描述 API 的速率限制和重试策略。
""",
            "data-processor": """---
name: {skill_name}
description: 数据处理技能模板
version: 1.0.0
author: 
category: data
platforms:
  - linux
  - macos
  - windows
triggers:
  - data
  - process
  - transform
tags:
  - data
  - processing
  - etl
---

# {skill_name}

数据处理技能模板。

## 支持的格式

- CSV
- JSON
- XML
- Excel (.xlsx)

## 使用方法

### 数据加载

```python
import pandas as pd

# 加载 CSV
df = pd.read_csv("data.csv")

# 加载 JSON
df = pd.read_json("data.json")
```

### 数据转换

```python
# 选择列
df = df[["col1", "col2"]]

# 过滤行
df = df[df["column"] > value]

# 添加计算列
df["new_column"] = df["col1"] + df["col2"]
```

### 数据保存

```python
# 保存为 CSV
df.to_csv("output.csv", index=False)

# 保存为 JSON
df.to_json("output.json", orient="records")
```

## 性能优化

- 使用 chunk 处理大文件
- 使用向量化操作代替循环
- 合理使用数据类型
""",
            "automation": """---
name: {skill_name}
description: 自动化脚本技能模板
version: 1.0.0
author: 
category: automation
platforms:
  - linux
  - macos
  - windows
triggers:
  - automation
  - script
  - schedule
tags:
  - automation
  - script
  - scheduled
---

# {skill_name}

自动化脚本技能模板。

## 功能说明

描述这个自动化脚本的功能。

## 前置条件

- 条件一
- 条件二

## 使用方法

### 直接运行

```bash
python scripts/main.py
```

### 定时执行

```bash
# 使用 cron
0 * * * * /path/to/script.sh

# 使用 Windows Task Scheduler
schtasks /create /tn "TaskName" /tr "script.bat" /sc hourly
```

## 脚本内容

```bash
#!/bin/bash
# 自动化脚本内容

echo "Starting automation..."

# 步骤一
step_one

# 步骤二
step_two

echo "Automation completed."
```

## 日志记录

脚本应该记录执行日志，便于排查问题。

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="automation.log",
)
```
""",
        }

        return templates.get(template_id)


# 全局实例
_bundle: Optional[SkillBundle] = None


def get_bundle() -> SkillBundle:
    """获取全局打包工具实例"""
    global _bundle
    if _bundle is None:
        _bundle = SkillBundle()
    return _bundle


# 便捷函数

def export_skill(skill_name: str, output_path: Path) -> bool:
    """导出单个技能"""
    return get_bundle().export_skill(skill_name, output_path)


def export_all_skills(output_path: Path) -> bool:
    """导出所有技能"""
    return get_bundle().export_all(output_path)


def import_bundle(bundle_path: Path, overwrite: bool = False) -> Dict[str, Any]:
    """导入打包文件"""
    options = ImportOptions(overwrite=overwrite)
    return get_bundle().import_bundle(bundle_path, options)


def create_from_template(
    template_id: str,
    skill_name: str,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """从模板创建技能"""
    return get_bundle().create_from_template(template_id, skill_name, category)


if __name__ == "__main__":
    bundle = get_bundle()

    # 测试列出模板
    print("Available templates:")
    for t in bundle.list_templates():
        print(f"  - {t['id']}: {t['name']} - {t['description']}")
