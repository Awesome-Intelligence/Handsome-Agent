#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Curator - 自动记忆总结模块

参考 Hermes Agent 的 curator 架构设计，提供自动记忆总结能力。

功能：
- 会话结束时自动总结用户偏好到 USER.md
- 自动总结环境信息和项目上下文到 MEMORY.md
- 基于 LLM 智能提取关键信息
- 支持配置触发条件和总结策略

设计参考：
- Hermes Agent 的 curator.py（技能管理）
- Hermes 的 HonchoSessionManager（用户偏好总结）
- Honcho 的 dialectic_query 和 create_conclusion API

触发时机：
1. 会话结束时（on_session_end）
2. 达到 N 条消息后（消息数阈值）
3. 空闲一定时间后（空闲超时）
4. Agent 空闲时（后台运行）
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from common.config import AGENT_Z_HOME
from common.logging_manager import get_decision_logger

if TYPE_CHECKING:
    from agent.session import Session
    from agent.memory.memory_store import MemoryStore
    from common.config import MemoryConfig

logger = get_decision_logger("MemoryCurator")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class CuratorConfig:
    """Curator 配置"""
    # 启用自动总结
    enabled: bool = True
    
    # 触发阈值
    message_threshold: int = 20  # 达到 N 条消息后触发
    idle_threshold_seconds: float = 300  # 空闲 N 秒后触发
    
    # 总结目标
    auto_user_summary: bool = True  # 自动总结用户偏好
    auto_memory_summary: bool = True  # 自动总结环境信息
    
    # 总结限制
    max_entries_per_summary: int = 3  # 每次总结最多添加的条目数
    min_entry_length: int = 20  # 最小条目长度
    max_entry_length: int = 500  # 最大条目长度
    
    # 避免重复
    check_duplicates: bool = True  # 检查重复条目
    
    # LLM 配置
    use_auxiliary_model: bool = True  # 使用辅助模型进行总结
    model: str = ""  # 指定模型（空则使用默认）
    
    # 调试
    verbose: bool = False  # 详细日志


# ============================================================================
# Curator State
# ============================================================================

def _state_file() -> Path:
    """状态文件路径"""
    return AGENT_Z_HOME / "memories" / ".curator_state"


def _default_state() -> Dict[str, Any]:
    """默认状态"""
    return {
        "last_run_at": None,
        "last_run_summary": None,
        "last_run_duration_seconds": None,
        "run_count": 0,
        "total_entries_added": 0,
        "skipped_duplicates": 0,
    }


def load_curator_state() -> Dict[str, Any]:
    """加载 Curator 状态"""
    path = _state_file()
    if not path.exists():
        return _default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            base = _default_state()
            base.update({k: v for k, v in data.items() if k in base or k.startswith("_")})
            return base
    except (OSError, json.JSONDecodeError) as e:
        logger.debug("Failed to read curator state: %s", e)
    return _default_state()


def save_curator_state(data: Dict[str, Any]) -> None:
    """保存 Curator 状态"""
    path = _state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".curator_state_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except Exception as e:
        logger.debug("Failed to save curator state: %s", e, exc_info=True)


# ============================================================================
# User Preference Extraction
# ============================================================================

USER_PREFERENCE_PROMPT = """你是记忆整理助手。请从以下对话中提取用户的重要偏好和信息。

提取要求：
1. 用户偏好：编码风格、工具偏好、沟通习惯等
2. 用户信息：姓名、角色、时区、工作习惯等
3. 重要上下文：项目特点、工作流程、环境信息等

提取规则：
- 只提取用户明确表达或暗示的偏好
- 忽略任务进展、临时状态、已完成的工作
- 忽略可通过网络搜索重新获取的信息
- 忽略已存在于 USER.md 中的信息（我们会检查）

输出格式：
只输出提取到的信息，每行一条，简短描述。

对话内容：
{messages}

只输出用户偏好，不要解释。"""


MEMORY_SUMMARY_PROMPT = """你是记忆整理助手。请从以下对话中提取环境信息和项目上下文。

提取要求：
1. 环境信息：操作系统、已安装工具、项目结构
2. 项目上下文：使用的框架、库、技术栈
3. 重要约定：代码规范、工作流程、配置要求
4. 解决方案：遇到的问题和解决方案（值得保留的）

提取规则：
- 只提取持久有价值的信息
- 忽略任务进展、临时状态
- 忽略可重新发现的原始数据
- 忽略已存在于 MEMORY.md 中的信息

输出格式：
只输出提取到的信息，每行一条，简短描述。

对话内容：
{messages}

只输出环境信息，不要解释。"""


# ============================================================================
# Memory Curator Core
# ============================================================================

class MemoryCurator:
    """
    自动记忆总结器。
    
    基于会话历史自动提取和保存：
    - 用户偏好到 USER.md
    - 环境信息到 MEMORY.md
    
    使用方式：
        curator = MemoryCurator(config=CuratorConfig())
        curator.on_session_end(session)
        
    或使用钩子：
        session.register_hook("on_end", curator.on_session_end)
    """
    
    def __init__(
        self,
        config: CuratorConfig = None,
        memory_store: "MemoryStore" = None,
    ):
        """
        初始化 MemoryCurator。

        Args:
            config: Curator 配置（向后兼容）
            memory_store: MemoryStore 实例
        """
        self.config = config or CuratorConfig()
        self._memory_store = memory_store
        self._state = load_curator_state()

        # LLM可用性检测（延迟到首次使用时，但会记录状态）
        self._llm_available: Optional[bool] = None  # None=未检测, True=可用, False=不可用
        self._llm_checked: bool = False  # 是否已检测

        # 运行时状态
        self._message_counts: Dict[str, int] = {}  # session_id -> count
        self._last_activity: Dict[str, float] = {}  # session_id -> timestamp
        self._pending_sessions: Set[str] = set()  # 待处理 session_id

        # 异步处理
        self._async_queue: List[Dict[str, Any]] = []
        self._async_lock = threading.Lock()
        self._async_thread: threading.Thread = None

    @classmethod
    def from_config(cls, config: "MemoryConfig", memory_store: "MemoryStore" = None) -> "MemoryCurator":
        """
        从 MemoryConfig 创建 MemoryCurator 实例。

        统一的初始化入口，从 MemoryConfig 中提取 Curator 相关配置。

        Args:
            config: MemoryConfig 配置对象（包含 curator_* 字段）
            memory_store: MemoryStore 实例（可选）

        Returns:
            MemoryCurator 实例

        示例:
            from common.config import MemoryConfig
            from agent.memory.memory_curator import MemoryCurator

            config = MemoryConfig(curator_enabled=True, curator_message_threshold=30)
            curator = MemoryCurator.from_config(config)
        """
        # 从 MemoryConfig 中提取 Curator 配置
        curator_config = CuratorConfig(
            enabled=config.curator_enabled,
            message_threshold=config.curator_message_threshold,
            idle_threshold_seconds=config.curator_idle_threshold_seconds,
            auto_user_summary=config.curator_auto_user_summary,
            auto_memory_summary=config.curator_auto_memory_summary,
            max_entries_per_summary=config.curator_max_entries_per_summary,
            min_entry_length=config.curator_min_entry_length,
            max_entry_length=config.curator_max_entry_length,
            check_duplicates=config.curator_check_duplicates,
            use_auxiliary_model=config.curator_use_auxiliary_model,
        )
        return cls(config=curator_config, memory_store=memory_store)

    def update_config(self, config: "MemoryConfig") -> None:
        """
        使用 MemoryConfig 更新 Curator 配置。

        从 MemoryConfig 中提取 Curator 相关配置并更新。

        Args:
            config: MemoryConfig 配置对象
        """
        self.config.enabled = config.curator_enabled
        self.config.message_threshold = config.curator_message_threshold
        self.config.idle_threshold_seconds = config.curator_idle_threshold_seconds
        self.config.auto_user_summary = config.curator_auto_user_summary
        self.config.auto_memory_summary = config.curator_auto_memory_summary
        self.config.max_entries_per_summary = config.curator_max_entries_per_summary
        self.config.min_entry_length = config.curator_min_entry_length
        self.config.max_entry_length = config.curator_max_entry_length
        self.config.check_duplicates = config.curator_check_duplicates
        self.config.use_auxiliary_model = config.curator_use_auxiliary_model
    
    def _check_llm_available(self) -> bool:
        """
        检测 LLM 是否可用。
        
        只在首次调用时检测，之后缓存结果以避免重复导入。
        检测结果会记录到日志中，便于排查问题。
        
        Returns:
            True 如果 LLM 可用，False 否则
        """
        if self._llm_checked:
            return self._llm_available if self._llm_available is not None else False
        
        self._llm_checked = True
        
        try:
            from common.model_client import get_model_client
            client = get_model_client()
            if client is not None:
                self._llm_available = True
                logger.debug("MemoryCurator: LLM client available")
                return True
        except ImportError:
            logger.warning("MemoryCurator: common.model_client not available")
        except Exception as e:
            logger.warning(f"MemoryCurator: Failed to initialize LLM client: {e}")
        
        self._llm_available = False
        logger.warning(
            "MemoryCurator: LLM client not available. "
            "Automatic memory summarization will be skipped. "
            "To enable, ensure common.model_client is properly configured."
        )
        return False
    
    @property
    def is_llm_available(self) -> bool:
        """检查 LLM 是否可用（首次调用会触发检测）"""
        return self._check_llm_available()
    
    @property
    def memory_store(self) -> "MemoryStore":
        """懒加载获取 MemoryStore"""
        if self._memory_store is None:
            from agent.memory.memory_store import MemoryStore
            self._memory_store = MemoryStore()
        return self._memory_store
    
    def on_session_end(
        self,
        session: "Session",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        会话结束钩子 - 触发记忆总结。
        
        在会话结束时调用，分析会话历史并更新记忆。
        
        Args:
            session: Session 实例
            dry_run: 只检查不写入
        
        Returns:
            总结结果
        """
        if not self.config.enabled:
            return {"status": "disabled", "skipped": True}
        
        session_id = getattr(session, "session_id", "unknown")
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"MemoryCurator: Processing session end for {session_id}")
        
        result = {
            "session_id": session_id,
            "started_at": start_time.isoformat(),
            "user_entries_added": 0,
            "memory_entries_added": 0,
            "skipped_duplicates": 0,
            "errors": [],
        }
        
        try:
            # 获取会话消息
            messages = self._extract_messages(session)
            
            if not messages:
                result["status"] = "no_messages"
                return result
            
            # 检查是否需要总结
            if not self._should_summarize(messages, session_id):
                result["status"] = "below_threshold"
                return result
            
            # 执行总结
            if dry_run:
                result["status"] = "dry_run"
            else:
                # 用户偏好总结
                if self.config.auto_user_summary:
                    user_result = self._summarize_user_preferences(messages)
                    result["user_entries_added"] = user_result.get("added", 0)
                    result["skipped_duplicates"] += user_result.get("duplicates", 0)
                
                # 环境信息总结
                if self.config.auto_memory_summary:
                    memory_result = self._summarize_environment(messages)
                    result["memory_entries_added"] = memory_result.get("added", 0)
                    result["skipped_duplicates"] += memory_result.get("duplicates", 0)
                
                result["status"] = "success"
                
                # 更新状态
                self._update_state(result)
        
        except Exception as e:
            logger.error(f"MemoryCurator: Error during summary: {e}")
            result["status"] = "error"
            result["errors"].append(str(e))
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        result["duration_seconds"] = elapsed
        
        return result
    
    def on_message(
        self,
        session: "Session",
        role: str,
        content: str,
    ) -> None:
        """
        消息处理钩子 - 追踪消息数和活动时间。
        
        可以用于：
        - 计数消息触发总结
        - 检测空闲时间
        
        Args:
            session: Session 实例
            role: 消息角色
            content: 消息内容
        """
        if not self.config.enabled:
            return
        
        session_id = getattr(session, "session_id", "unknown")
        current_time = time.time()
        
        # 更新消息计数
        if role == "user":
            self._message_counts[session_id] = self._message_counts.get(session_id, 0) + 1
            self._last_activity[session_id] = current_time
            
            # 检查是否达到阈值
            if self._message_counts[session_id] >= self.config.message_threshold:
                if session_id not in self._pending_sessions:
                    self._pending_sessions.add(session_id)
                    logger.info(f"MemoryCurator: Session {session_id} reached message threshold")
    
    def check_idle_and_summarize(
        self,
        sessions: List["Session"],
        current_time: float = None,
    ) -> List[Dict[str, Any]]:
        """
        检查空闲会话并触发总结。
        
        应该在定时任务或空闲检测时调用。
        
        Args:
            sessions: 当前活跃的 Session 列表
            current_time: 当前时间戳（用于测试）
        
        Returns:
            总结结果列表
        """
        if not self.config.enabled:
            return []
        
        if current_time is None:
            current_time = time.time()
        
        results = []
        
        for session in sessions:
            session_id = getattr(session, "session_id", "unknown")
            
            # 检查空闲时间
            last_activity = self._last_activity.get(session_id, 0)
            idle_time = current_time - last_activity
            
            if idle_time >= self.config.idle_threshold_seconds:
                if session_id in self._pending_sessions or self._message_counts.get(session_id, 0) >= self.config.message_threshold:
                    result = self.on_session_end(session)
                    results.append(result)
                    
                    # 重置状态
                    self._pending_sessions.discard(session_id)
                    self._message_counts[session_id] = 0
                    self._last_activity[session_id] = current_time
        
        return results
    
    def _extract_messages(self, session: "Session") -> List[Dict[str, str]]:
        """从 Session 提取消息"""
        messages = []
        
        # 尝试从 session 获取消息
        if hasattr(session, "messages"):
            for msg in session.messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                elif hasattr(msg, "role") and hasattr(msg, "content"):
                    role = msg.role
                    content = msg.content
                else:
                    continue
                
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        
        return messages
    
    def _should_summarize(
        self,
        messages: List[Dict[str, str]],
        session_id: str,
    ) -> bool:
        """检查是否应该进行总结"""
        # 用户消息数
        user_count = sum(1 for m in messages if m.get("role") == "user")
        
        # 检查阈值
        if user_count < 5:
            return False
        
        # 检查是否在阈值附近（避免频繁总结）
        count = self._message_counts.get(session_id, 0)
        if count > 0 and count < self.config.message_threshold:
            return False
        
        return True
    
    def _summarize_user_preferences(
        self,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """总结用户偏好"""
        result = {"added": 0, "duplicates": 0, "entries": [], "error": None}
        
        # 检查 LLM 可用性
        if not self._check_llm_available():
            result["error"] = "LLM client not available"
            logger.debug("Skipping user preference summary: LLM not available")
            return result
        
        try:
            # 构建提示
            messages_text = self._format_messages_for_summary(messages)
            prompt = USER_PREFERENCE_PROMPT.format(messages=messages_text)
            
            # 调用 LLM
            extracted = self._call_llm(prompt)
            
            if not extracted:
                result["error"] = "No content extracted from LLM"
                return result
            
            # 解析提取的条目
            entries = self._parse_entries(extracted)
            
            # 获取现有条目（用于去重）
            existing_entries = set()
            if self.config.check_duplicates:
                try:
                    existing_entries = set(self.memory_store.user_entries)
                except Exception:
                    pass
            
            # 添加条目
            for entry in entries[:self.config.max_entries_per_summary]:
                if not self._validate_entry(entry):
                    continue
                
                if entry in existing_entries:
                    result["duplicates"] += 1
                    continue
                
                # 写入 USER.md
                add_result = self.memory_store.add("user", entry)
                if add_result.get("success"):
                    result["added"] += 1
                    result["entries"].append(entry)
                    existing_entries.add(entry)
                else:
                    error = add_result.get("error", "")
                    if "duplicate" in error.lower():
                        result["duplicates"] += 1
        
        except Exception as e:
            logger.error(f"Error summarizing user preferences: {e}")
            result["error"] = str(e)
        
        return result
    
    def _summarize_environment(
        self,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """总结环境信息"""
        result = {"added": 0, "duplicates": 0, "entries": [], "error": None}
        
        # 检查 LLM 可用性
        if not self._check_llm_available():
            result["error"] = "LLM client not available"
            logger.debug("Skipping environment summary: LLM not available")
            return result
        
        try:
            # 构建提示
            messages_text = self._format_messages_for_summary(messages)
            prompt = MEMORY_SUMMARY_PROMPT.format(messages=messages_text)
            
            # 调用 LLM
            extracted = self._call_llm(prompt)
            
            if not extracted:
                result["error"] = "No content extracted from LLM"
                return result
            
            # 解析提取的条目
            entries = self._parse_entries(extracted)
            
            # 获取现有条目（用于去重）
            existing_entries = set()
            if self.config.check_duplicates:
                try:
                    existing_entries = set(self.memory_store.memory_entries)
                except Exception:
                    pass
            
            # 添加条目
            for entry in entries[:self.config.max_entries_per_summary]:
                if not self._validate_entry(entry):
                    continue
                
                if entry in existing_entries:
                    result["duplicates"] += 1
                    continue
                
                # 写入 MEMORY.md
                add_result = self.memory_store.add("memory", entry)
                if add_result.get("success"):
                    result["added"] += 1
                    result["entries"].append(entry)
                    existing_entries.add(entry)
        
        except Exception as e:
            logger.error(f"Error summarizing environment: {e}")
            result["error"] = str(e)
        
        return result
    
    def _format_messages_for_summary(
        self,
        messages: List[Dict[str, str]],
        max_chars: int = 8000,
    ) -> str:
        """格式化消息用于总结"""
        lines = []
        total_chars = 0
        
        # 从最近的消息开始（优先使用最新的上下文）
        for msg in reversed(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # 截断过长内容
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            line = f"[{role.upper()}] {content}"
            
            if total_chars + len(line) > max_chars:
                break
            
            lines.append(line)
            total_chars += len(line)
        
        # 反转回时间顺序
        return "\n".join(reversed(lines))
    
    def _parse_entries(self, text: str) -> List[str]:
        """解析 LLM 输出为条目列表"""
        entries = []
        
        for line in text.strip().split("\n"):
            line = line.strip()
            
            # 移除常见前缀
            for prefix in ["- ", "* ", "• ", "• ", "· "]:
                if line.startswith(prefix):
                    line = line[len(prefix):]
            
            # 移除编号前缀
            import re
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            
            line = line.strip()
            
            if line and len(line) >= self.config.min_entry_length:
                entries.append(line)
        
        return entries
    
    def _validate_entry(self, entry: str) -> bool:
        """验证条目是否有效"""
        if not entry or not entry.strip():
            return False
        
        length = len(entry)
        
        if length < self.config.min_entry_length:
            return False
        
        if length > self.config.max_entry_length:
            return False
        
        # 检查是否是有效文本
        if len(entry.strip()) < self.config.min_entry_length:
            return False
        
        # 排除明显无效的内容
        invalid_patterns = [
            r"^[{}\[\]]+$",  # 只有括号
            r"^(yes|no)$",  # 太短
            r"^[\d\.\,\-\+\*\/]+$",  # 只有数字和符号
        ]
        
        import re
        for pattern in invalid_patterns:
            if re.match(pattern, entry.strip()):
                return False
        
        return True
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM 进行总结。
        
        注意：调用前应确保 LLM 可用（通过 _check_llm_available()）。
        此方法仅处理实际的 LLM 调用逻辑。
        """
        try:
            # 优先使用 auxiliary client
            if self.config.use_auxiliary_model:
                return self._call_auxiliary_model(prompt)
            else:
                return self._call_main_model(prompt)
        except Exception as e:
            logger.warning(f"MemoryCurator: LLM call failed: {e}")
            return ""
    
    def _call_auxiliary_model(self, prompt: str) -> str:
        """调用 auxiliary 模型"""
        try:
            # 尝试使用 common 模块中的 auxiliary client
            from common.model_client import get_auxiliary_client
            client = get_auxiliary_client()
            
            if client:
                response = client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.config.model or None,
                    max_tokens=500,
                )
                return response.get("content", "")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Auxiliary model unavailable, falling back: {e}")
        
        # 回退到主模型
        return self._call_main_model(prompt)
    
    def _call_main_model(self, prompt: str) -> str:
        """调用主模型"""
        try:
            from common.model_client import get_model_client
            client = get_model_client()
            
            if client:
                response = client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.config.model or None,
                    max_tokens=500,
                )
                return response.get("content", "")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Main model call failed: {e}")
        
        # 如果没有可用的模型客户端，返回空
        # 注意：此处的警告已在 _check_llm_available() 中发出
        return ""
    
    def _update_state(self, result: Dict[str, Any]) -> None:
        """更新 Curator 状态"""
        state = load_curator_state()
        
        state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        state["last_run_summary"] = (
            f"added {result.get('user_entries_added', 0)} user, "
            f"{result.get('memory_entries_added', 0)} memory entries"
        )
        state["last_run_duration_seconds"] = result.get("duration_seconds", 0)
        state["run_count"] = state.get("run_count", 0) + 1
        state["total_entries_added"] = (
            state.get("total_entries_added", 0) + 
            result.get("user_entries_added", 0) + 
            result.get("memory_entries_added", 0)
        )
        state["skipped_duplicates"] = (
            state.get("skipped_duplicates", 0) + 
            result.get("skipped_duplicates", 0)
        )
        
        save_curator_state(state)
        self._state = state
    
    def get_stats(self) -> Dict[str, Any]:
        """获取 Curator 统计信息"""
        state = load_curator_state()
        return {
            "last_run_at": state.get("last_run_at"),
            "last_run_summary": state.get("last_run_summary"),
            "run_count": state.get("run_count", 0),
            "total_entries_added": state.get("total_entries_added", 0),
            "skipped_duplicates": state.get("skipped_duplicates", 0),
            "pending_sessions": list(self._pending_sessions),
            "message_counts": dict(self._message_counts),
        }


# ============================================================================
# Convenience Functions
# ============================================================================

_default_curator: Optional[MemoryCurator] = None


def get_default_curator(
    config: "MemoryConfig" = None,
    memory_store: "MemoryStore" = None,
) -> MemoryCurator:
    """
    获取默认的 MemoryCurator 实例。

    Args:
        config: MemoryConfig 配置（可选，从配置创建 Curator）
        memory_store: MemoryStore 实例（可选）

    Returns:
        MemoryCurator 实例
    """
    global _default_curator
    if _default_curator is None:
        if config is not None:
            _default_curator = MemoryCurator.from_config(config, memory_store)
        else:
            _default_curator = MemoryCurator()
    return _default_curator


def reset_default_curator() -> None:
    """重置默认的 MemoryCurator 实例（用于测试或重新初始化）"""
    global _default_curator
    _default_curator = None


def curator_on_session_end(session: "Session") -> Dict[str, Any]:
    """快捷函数：在会话结束时调用 Curator"""
    curator = get_default_curator()
    return curator.on_session_end(session)


def curator_on_message(
    session: "Session",
    role: str,
    content: str,
) -> None:
    """快捷函数：在收到消息时调用 Curator"""
    curator = get_default_curator()
    curator.on_message(session, role, content)
