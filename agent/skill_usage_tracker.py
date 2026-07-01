#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Usage Tracker - 技能使用追踪系统

追踪每个技能的使用元数据，存储在 .usage.json sidecar 文件中。
支持 bump_use、bump_view、bump_patch 等操作。

设计原则：
- Sidecar 存储：保持 SKILL.md 内容纯净
- 原子写入：tempfile + os.replace
- 静默失败：追踪失败不影响主流程

生命周期状态：
- active: 默认状态
- stale: 未使用超过 stale_after_days
- archived: 未使用超过 archive_after_days，移动到 .archive/

🧠 Decision - 📋 Skills - 使用追踪
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from common.config import get_config_dir, get_settings

logger = logging.getLogger(__name__)

# 生命周期状态常量
STATE_ACTIVE = "active"
STATE_STALE = "stale"
STATE_ARCHIVED = "archived"
VALID_STATES = {STATE_ACTIVE, STATE_STALE, STATE_ARCHIVED}

# 锁定文件支持（Windows 使用 msvcrt）
msvcrt = None
try:
    import fcntl
except ImportError:  # Windows fallback
    fcntl = None
    try:
        import msvcrt
    except ImportError:
        pass


def _skills_dir() -> Path:
    """获取技能目录"""
    return Path(get_settings().skills_dir)


def _usage_file() -> Path:
    """获取使用追踪文件路径"""
    return _skills_dir() / ".usage.json"


@contextmanager
def _usage_file_lock():
    """序列化 .usage.json 的读写操作"""
    lock_path = _usage_file().with_suffix(".json.lock")

    if fcntl is None and msvcrt is None:
        yield
        return

    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if msvcrt and (not lock_path.exists() or lock_path.stat().st_size == 0):
        try:
            lock_path.write_text(" ", encoding="utf-8")
        except OSError:
            pass

    fd = None
    try:
        fd = open(lock_path, "r+" if msvcrt else "a+", encoding="utf-8")
        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_EX)
        elif msvcrt:
            fd.seek(0)
            msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
        yield
    finally:
        if fd:
            try:
                if fcntl:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                elif msvcrt:
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
            try:
                fd.close()
            except OSError:
                pass


def _archive_dir() -> Path:
    """获取归档目录"""
    return _skills_dir() / ".archive"


def _now_iso() -> str:
    """获取当前 UTC 时间戳"""
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_timestamp(value: Any) -> Optional[datetime]:
    """安全解析 ISO 时间戳"""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def latest_activity_at(record: Dict[str, Any]) -> Optional[str]:
    """获取最近的活动时间戳（use/view/patch 中的最新）"""
    latest_dt: Optional[datetime] = None
    latest_raw: Optional[str] = None
    for key in ("last_used_at", "last_viewed_at", "last_patched_at"):
        raw = record.get(key)
        dt = _parse_iso_timestamp(raw)
        if dt is None:
            continue
        if latest_dt is None or dt > latest_dt:
            latest_dt = dt
            latest_raw = str(raw)
    return latest_raw


def activity_count(record: Dict[str, Any]) -> int:
    """获取总活动次数"""
    total = 0
    for key in ("use_count", "view_count", "patch_count"):
        try:
            total += int(record.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _empty_record() -> Dict[str, Any]:
    """创建空的追踪记录"""
    return {
        "created_by": None,
        "use_count": 0,
        "view_count": 0,
        "last_used_at": None,
        "last_viewed_at": None,
        "patch_count": 0,
        "last_patched_at": None,
        "created_at": _now_iso(),
        "state": STATE_ACTIVE,
        "pinned": False,
        "archived_at": None,
    }


def load_usage() -> Dict[str, Dict[str, Any]]:
    """读取整个 .usage.json 文件"""
    path = _usage_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.debug("Failed to read %s: %s", path, e)
        return {}
    if not isinstance(data, dict):
        return {}
    # 清理：确保所有值都是 dict
    clean: Dict[str, Dict[str, Any]] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            clean[str(k)] = v
    return clean


def save_usage(data: Dict[str, Dict[str, Any]]) -> None:
    """原子写入 usage 文件"""
    path = _usage_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), prefix=".usage_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        logger.debug("Failed to write %s: %s", path, e)


def get_record(skill_name: str) -> Dict[str, Any]:
    """获取技能追踪记录，不存在则创建新的"""
    data = load_usage()
    rec = data.get(skill_name)
    if not isinstance(rec, dict):
        return _empty_record()
    # 填充缺失的键
    base = _empty_record()
    for k, v in base.items():
        rec.setdefault(k, v)
    return rec


def _mutate(skill_name: str, mutator) -> None:
    """加载、应用变更、保存"""
    if not skill_name:
        return
    try:
        with _usage_file_lock():
            data = load_usage()
            rec = data.get(skill_name)
            if not isinstance(rec, dict):
                rec = _empty_record()
            mutator(rec)
            data[skill_name] = rec
            save_usage(data)
    except Exception as e:
        logger.debug("skill_usage_tracker._mutate(%s) failed: %s", skill_name, e)


def bump_view(skill_name: str) -> None:
    """增加查看计数"""
    def _apply(rec: Dict[str, Any]) -> None:
        rec["view_count"] = int(rec.get("view_count") or 0) + 1
        rec["last_viewed_at"] = _now_iso()
    _mutate(skill_name, _apply)


def bump_use(skill_name: str) -> None:
    """增加使用计数"""
    def _apply(rec: Dict[str, Any]) -> None:
        rec["use_count"] = int(rec.get("use_count") or 0) + 1
        rec["last_used_at"] = _now_iso()
    _mutate(skill_name, _apply)


def bump_patch(skill_name: str) -> None:
    """增加修改计数"""
    def _apply(rec: Dict[str, Any]) -> None:
        rec["patch_count"] = int(rec.get("patch_count") or 0) + 1
        rec["last_patched_at"] = _now_iso()
    _mutate(skill_name, _apply)


def mark_agent_created(skill_name: str) -> None:
    """标记技能为 Agent 创建"""
    def _apply(rec: Dict[str, Any]) -> None:
        rec["created_by"] = "agent"
    _mutate(skill_name, _apply)


def set_state(skill_name: str, state: str) -> None:
    """设置生命周期状态"""
    if state not in VALID_STATES:
        logger.debug("set_state: invalid state %r for %s", state, skill_name)
        return
    def _apply(rec: Dict[str, Any]) -> None:
        rec["state"] = state
        if state == STATE_ARCHIVED:
            rec["archived_at"] = _now_iso()
        elif state == STATE_ACTIVE:
            rec["archived_at"] = None
    _mutate(skill_name, _apply)


def set_pinned(skill_name: str, pinned: bool) -> None:
    """设置置顶状态"""
    def _apply(rec: Dict[str, Any]) -> None:
        rec["pinned"] = bool(pinned)
    _mutate(skill_name, _apply)


def forget(skill_name: str) -> None:
    """删除技能的追踪记录"""
    if not skill_name:
        return
    try:
        with _usage_file_lock():
            data = load_usage()
            if skill_name in data:
                del data[skill_name]
                save_usage(data)
    except Exception as e:
        logger.debug("skill_usage_tracker.forget(%s) failed: %s", skill_name, e)


def archive_skill(skill_name: str) -> Tuple[bool, str]:
    """将技能移动到归档目录"""
    skill_dir = _find_skill_dir(skill_name)
    if skill_dir is None:
        return False, f"skill '{skill_name}' not found"

    archive_root = _archive_dir()
    try:
        archive_root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"failed to create archive dir: {e}"

    # 防止重名冲突
    dest = archive_root / skill_dir.name
    if dest.exists():
        dest = archive_root / f"{skill_dir.name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    try:
        skill_dir.rename(dest)
    except OSError:
        import shutil
        try:
            shutil.move(str(skill_dir), str(dest))
        except Exception as e2:
            return False, f"failed to archive: {e2}"

    set_state(skill_name, STATE_ARCHIVED)
    return True, f"archived to {dest}"


def restore_skill(skill_name: str) -> Tuple[bool, str]:
    """从归档目录恢复技能"""
    archive_root = _archive_dir()
    if not archive_root.exists():
        return False, "no archive directory"

    # 精确匹配或前缀匹配（时间戳重复）
    candidates = [p for p in archive_root.rglob("*") if p.is_dir() and p.name == skill_name]
    if not candidates:
        candidates = sorted(
            [p for p in archive_root.rglob("*")
             if p.is_dir() and p.name.startswith(f"{skill_name}-")],
            reverse=True,
        )
    if not candidates:
        return False, f"skill '{skill_name}' not found in archive"

    src = candidates[0]
    dest = _skills_dir() / skill_name
    if dest.exists():
        return False, f"destination already exists: {dest}"

    try:
        src.rename(dest)
    except OSError:
        import shutil
        try:
            shutil.move(str(src), str(dest))
        except Exception as e:
            return False, f"failed to restore: {e}"

    set_state(skill_name, STATE_ACTIVE)
    return True, f"restored to {dest}"


def _find_skill_dir(skill_name: str) -> Optional[Path]:
    """查找技能目录"""
    base = _skills_dir()
    if not base.exists():
        return None
    for skill_md in base.rglob("SKILL.md"):
        if _read_skill_name(skill_md, fallback=skill_md.parent.name) == skill_name:
            return skill_md.parent
    return None


def _read_skill_name(skill_md: Path, fallback: str) -> str:
    """从 SKILL.md 解析技能名称"""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return fallback

    in_frontmatter = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip().strip("\"'")
            if value:
                return value
    return fallback


def agent_created_report() -> list[Dict[str, Any]]:
    """生成 Agent 创建技能的报告"""
    data = load_usage()
    rows: list[Dict[str, Any]] = []
    for name, rec in data.items():
        if not isinstance(rec, dict):
            continue
        if rec.get("created_by") != "agent":
            continue
        if not isinstance(rec, dict):
            rec = _empty_record()
        base = _empty_record()
        for k, v in base.items():
            rec.setdefault(k, v)
        row = {"name": name, **rec}
        row["last_activity_at"] = latest_activity_at(row)
        row["activity_count"] = activity_count(row)
        rows.append(row)
    return rows


# ============================================================================
# 兼容层: SkillTelemetry 类 (兼容 skills.telemetry.SkillTelemetry 接口)
# ============================================================================

class SkillTelemetry:
    """
    技能遥测类 (兼容层)

    提供与 skills.telemetry.SkillTelemetry 相同的接口，
    内部使用 agent.skill_usage_tracker 的底层函数。

    此兼容层确保从 skills 模块迁移的代码无需修改即可工作。
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            from common.config import get_data_dir
            self.skills_dir: Path = get_data_dir() / "skills"
        else:
            self.skills_dir = Path(skills_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _ensure_cache(self) -> None:
        """确保缓存是最新的"""
        self._cache = load_usage()

    def get_record(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能记录"""
        self._ensure_cache()
        return self._cache.get(skill_id)

    def get_all_records(self) -> List[Dict[str, Any]]:
        """获取所有记录"""
        self._ensure_cache()
        return list(self._cache.values())

    def get_agent_created_skills(self) -> List[Dict[str, Any]]:
        """获取 Agent 创建的技能"""
        self._ensure_cache()
        return [
            rec for rec in self._cache.values()
            if rec.get("created_by") == "agent"
        ]

    def get_active_skills(self) -> List[Dict[str, Any]]:
        """获取活跃技能"""
        self._ensure_cache()
        return [rec for rec in self._cache.values() if rec.get("state") == STATE_ACTIVE]

    def get_stale_skills(self) -> List[Dict[str, Any]]:
        """获取陈旧技能"""
        self._ensure_cache()
        return [rec for rec in self._cache.values() if rec.get("state") == STATE_STALE]

    def get_archived_skills(self) -> List[Dict[str, Any]]:
        """获取归档技能"""
        self._ensure_cache()
        return [rec for rec in self._cache.values() if rec.get("state") == STATE_ARCHIVED]

    def record_use(self, skill_id: str) -> None:
        """记录技能使用"""
        bump_use(skill_id)
        self._cache = {}  # 使缓存失效

    def record_view(self, skill_id: str) -> None:
        """记录技能查看"""
        bump_view(skill_id)
        self._cache = {}  # 使缓存失效

    def record_patch(self, skill_id: str) -> None:
        """记录技能修改"""
        bump_patch(skill_id)
        self._cache = {}  # 使缓存失效

    def create_skill_record(
        self,
        skill_id: str,
        created_by: str = "agent",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建技能记录"""
        self._ensure_cache()
        record = self._cache.get(skill_id) or _empty_record()
        record["created_by"] = created_by
        record["tags"] = tags or []
        record["skill_id"] = skill_id
        self._cache[skill_id] = record

        # 保存到文件
        data = load_usage()
        data[skill_id] = record
        save_usage(data)

        return record

    def set_state(self, skill_id: str, state: str) -> bool:
        """设置技能状态"""
        set_state(skill_id, state)
        self._cache = {}  # 使缓存失效
        return True

    def set_pinned(self, skill_id: str, pinned: bool = True) -> bool:
        """设置技能置顶状态"""
        set_pinned(skill_id, pinned)
        self._cache = {}  # 使缓存失效
        return True

    def archive_skill(self, skill_id: str) -> bool:
        """归档技能"""
        ok, _ = archive_skill(skill_id)
        self._cache = {}  # 使缓存失效
        return ok

    def restore_skill(self, skill_id: str) -> bool:
        """恢复技能"""
        ok, _ = restore_skill(skill_id)
        self._cache = {}  # 使缓存失效
        return ok

    def get_latest_activity(self, skill_id: str) -> Optional[datetime]:
        """获取技能最新活动时间"""
        record = self.get_record(skill_id)
        if not record:
            return None
        timestamp = latest_activity_at(record)
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            return None

    def get_activity_count(self, skill_id: str) -> int:
        """获取技能活动计数"""
        record = self.get_record(skill_id)
        if not record:
            return 0
        return activity_count(record)

    def delete_skill_record(self, skill_id: str) -> bool:
        """删除技能记录"""
        forget(skill_id)
        self._cache = {}  # 使缓存失效
        return True


# 全局遥测实例
_telemetry_instance: Optional[SkillTelemetry] = None


def get_skill_telemetry() -> SkillTelemetry:
    """获取全局 SkillTelemetry 实例 (兼容 skills.telemetry.get_skill_telemetry)"""
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = SkillTelemetry()
    return _telemetry_instance
