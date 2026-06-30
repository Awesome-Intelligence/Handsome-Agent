"""
Provider 基类
🧠 Decision - 🤖 LLM - Provider 抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, AsyncIterator
from pydantic import BaseModel, Field
from datetime import datetime
import time

import httpx

from agent.error import classify_api_error, FailoverReason


@dataclass
class ProviderConfig:
    """Provider 配置"""
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: float = 60.0
    stream: bool = False


class Message(BaseModel):
    """对话消息"""
    role: str
    content: str
    name: Optional[str] = None

    def model_dump(self, **kwargs):
        """兼容 Pydantic v1/v2"""
        try:
            return super().model_dump(**kwargs)
        except AttributeError:
            return self.dict(**kwargs)


class ProviderResponse(BaseModel):
    """Provider 响应"""
    content: str
    model: str
    finish_reason: str = "stop"
    usage: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    function_call: Optional[Dict[str, Any]] = Field(default=None, description="函数调用信息 (用于 function calling)")

    class Config:
        extra = "allow"

    def model_dump(self, **kwargs):
        """兼容 Pydantic v1/v2"""
        try:
            return super().model_dump(**kwargs)
        except AttributeError:
            return self.dict(**kwargs)


class StreamChunk(BaseModel):
    """流式响应块"""
    content: str = ""
    delta: str = ""
    finish: bool = False
    usage: Optional[Dict[str, int]] = None


class BaseProvider(ABC):
    """Provider 抽象基类"""

    # Provider 标识符
    provider_name: str = "base"
    # Provider 显示名称
    provider_display_name: str = "Base Provider"
    # 支持的模型列表
    supported_models: List[str] = []

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._message_history: List[Message] = []
        self.logger = None  # 子类初始化时设置
        self._on_llm_call = None  # LLM 调用回调
        self._client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def _get_default_limits() -> httpx.Limits:
        """获取默认的 httpx 连接限制，避免 Windows 事件循环问题
        
        配置 max_keepalive_connections=0 禁用连接重用，
        避免在跨线程运行 asyncio 时出现 "Event loop is closed" 错误。
        """
        return httpx.Limits(max_keepalive_connections=0, max_connections=1)

    def register_llm_call_callback(self, callback):
        """注册 LLM 调用回调，每次 generate() 成功调用后触发"""
        self._on_llm_call = callback

    def _notify_llm_call(self):
        """通知 LLM 调用"""
        if self._on_llm_call:
            self._on_llm_call()

    def _log_request_started(self, model: str = None):
        """记录请求开始（INFO级别）"""
        if self.logger:
            model = model or self.config.model or "unknown"
            self.logger.info(f"▶️ {self.provider_display_name} request started - model: {model}")

    def _log_request_completed(self, latency_ms: float):
        """记录请求完成（INFO级别）"""
        if self.logger:
            self.logger.info(f"⏹️ {self.provider_display_name} request completed - latency: {latency_ms:.2f}ms")
        self._notify_llm_call()

    def _log_request_body(self, body: Dict[str, Any]):
        """记录请求体（DEBUG级别）- 只保留前50和后50字符"""
        if self.logger:
            body_str = str(body)
            if len(body_str) > 120:
                body_str = body_str[:50] + " ... " + body_str[-50:]
            self.logger.debug(f"{self.provider_display_name} request body: {body_str}")

    def _log_input_messages(self, messages: List[Dict[str, Any]], prompt_meta: Dict = None):
        """记录输入消息（DEBUG级别）
        
        特殊处理：
        - system 消息：分层显示，包含各层信息和提示词变量名
        - 其他消息：显示截断格式
        """
        if self.logger:
            self.logger.debug(f"{self.provider_display_name} Input Messages ({len(messages)} messages):")
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                # 防御性检查：确保 content 不是 None
                if content is None:
                    content = ""
                
                if role == "system":
                    # 使用传入的 prompt_meta 或消息中的 _prompt_meta
                    meta = prompt_meta or msg.get("_prompt_meta")
                    # 分层显示 system 消息
                    self._log_system_message分层(i, content, meta)
                elif role == "assistant":
                    tool_calls = msg.get("tool_calls", [])
                    if tool_calls:
                        tool_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
                        preview = f"[tool_calls: {', '.join(tool_names)}]"
                        self.logger.info(f"⬆️  [{i}] {role}: {preview}")
                    else:
                        preview = self._format_message_for_log(role, content)
                        self.logger.info(f"⬆️  [{i}] {role}: {preview}")
                else:
                    preview = self._format_message_for_log(role, content)
                    self.logger.info(f"⬆️  [{i}] {role}: {preview}")
    
    def _log_system_message分层(self, index: int, content: str, prompt_meta: Dict = None):
        """分层显示 system 消息
        
        格式：
        ⬆️  [0] system: Agent Definition
            ├─ stable: 3.5k chars (AGENT_IDENTITY, CAPABILITIES...)
            ├─ context: 0.2k chars (user_profile)
            └─ volatile: 0.1k chars (memory_context)
        """
        SYSTEM_COLOR = "\033[38;5;146m"
        RESET = "\033[0m"
        
        # 提取标题
        lines = content.split('\n')
        first_line = lines[0].strip() if lines else ""
        if first_line.startswith('#'):
            title = first_line.lstrip('#').strip()
        else:
            title = first_line[:40] if len(first_line) > 40 else first_line
        
        # 主标题
        self.logger.info(f"⬆️  [{index}] system: {SYSTEM_COLOR}{title}{RESET}")
        
        # 如果有 prompt_meta，显示分层信息
        if prompt_meta:
            stable_chars = prompt_meta.get("stable_chars", 0)
            context_chars = prompt_meta.get("context_chars", 0)
            volatile_chars = prompt_meta.get("volatile_chars", 0)
            stable_keys = prompt_meta.get("stable_keys", [])
            
            # 格式化字符数（转换为 k 单位）
            def format_chars(n):
                if n >= 1000:
                    return f"{n/1000:.1f}k"
                return str(n)
            
            # stable 层
            stable_info = f"{format_chars(stable_chars)} chars"
            if stable_keys:
                if len(stable_keys) <= 4:
                    keys_str = ", ".join(stable_keys)
                else:
                    keys_str = ", ".join(stable_keys[:4]) + f" +{len(stable_keys)-4}"
                stable_info += f" ({keys_str})"
            self.logger.info(f"    ├─ stable: {stable_info}")
            
            # context 层（上下文文件：AGENTS.md、项目规则等）
            volatile_sources = prompt_meta.get("volatile_sources", [])
            context_sources = prompt_meta.get("context_sources", [])
            if context_chars > 0:
                if context_sources:
                    sources_str = ", ".join(context_sources)
                    self.logger.info(f"    ├─ context: {format_chars(context_chars)} chars ({sources_str})")
                else:
                    self.logger.info(f"    ├─ context: {format_chars(context_chars)} chars (context files)")
            else:
                self.logger.info(f"    ├─ context: 0 chars (no context files)")
            
            # volatile 层（记忆快照 + 时间戳）
            volatile_label = ", ".join(volatile_sources) if volatile_sources else "memory snapshot"
            if volatile_chars > 0:
                self.logger.info(f"    └─ volatile: {format_chars(volatile_chars)} chars ({volatile_label} + timestamp)")
            else:
                self.logger.info(f"    └─ volatile: 0 chars (no memory)")
        else:
            # 没有 prompt_meta，显示总字符数
            total_chars = len(content)
            if total_chars >= 1000:
                self.logger.info(f"    └─ total: {total_chars/1000:.1f}k chars")
            else:
                self.logger.info(f"    └─ total: {total_chars} chars")
    
    def _extract_system_prompt_meta(self, messages: List) -> Optional[Dict]:
        """从消息列表中提取 system prompt 的 _prompt_meta
        
        用于在 _build_messages 处理后仍然能获取原始的 _prompt_meta。
        
        Returns:
            _prompt_meta 字典或 None
        """
        if not messages:
            return None
        
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                return msg.get("_prompt_meta")
            elif hasattr(msg, "role") and msg.role == "system":
                # Pydantic 模型等
                meta = getattr(msg, "_prompt_meta", None)
                if meta:
                    return meta
        return None

    def _log_output_content(self, content: str):
        """记录输出内容（INFO级别）"""
        if self.logger:
            preview = self._format_message_for_log("assistant", content)
            self.logger.info(f"⬇️ {self.provider_display_name} Output Content: {preview}")

    def _log_streaming_started(self):
        """记录流式输出开始（DEBUG级别）"""
        if self.logger:
            self.logger.debug(f"{self.provider_display_name} Streaming Output started")

    def _log_streaming_output(self, content: str):
        """记录流式输出内容（DEBUG级别）"""
        if self.logger:
            preview = self._format_message_for_log("assistant", content)
            self.logger.debug(f"{self.provider_display_name} Streaming Output: {preview}")

    def _log_request_error(self, error: Exception, context: str = "request"):
        """记录请求错误（ERROR级别）- 包含完整错误信息和分类结果
        
        使用 error_classifier 对错误进行结构化分类，并输出详细的恢复建议。
        """
        if self.logger:
            error_type = type(error).__name__
            error_msg = str(error)
            
            # 当 error_msg 包含类型名或为空时，尝试获取更详细的信息
            if not error_msg or error_msg == error_type:
                # 尝试从 error.args 获取消息
                if hasattr(error, 'args') and error.args:
                    error_msg = " ".join(str(arg) for arg in error.args if arg)
                # 尝试从 error.message 获取
                if not error_msg and hasattr(error, 'message'):
                    error_msg = str(error.message)
                # 尝试从 error.request 获取 URL
                if not error_msg:
                    request = getattr(error, 'request', None)
                    if request:
                        error_msg = f"Request to {getattr(request, 'url', 'unknown')} failed"
            
            # 如果仍然没有有用的消息，提供默认描述
            if not error_msg or error_msg == error_type:
                error_msg = f"{error_type} occurred"
            
            # 获取状态码
            status_code = getattr(error, "status_code", None)
            if status_code is None:
                current = error
                for _ in range(5):
                    code = getattr(current, "status_code", None)
                    if isinstance(code, int):
                        status_code = code
                        break
                    cause = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
                    if cause is None or cause is current:
                        break
                    current = cause
            
            # 使用错误分类器
            classified = classify_api_error(
                error,
                provider=self.provider_display_name,
                model=self.config.model or "",
            )
            
            # 构建详细日志消息
            log_parts = [
                f"{self.provider_display_name} {context} failed",
                f"reason={classified.reason.value}",
            ]
            
            if status_code:
                log_parts.append(f"status={status_code}")
            
            log_parts.append(f"type={error_type}")
            
            # 添加恢复建议
            recovery = []
            if classified.should_compress:
                recovery.append("compress")
            if classified.should_rotate_credential:
                recovery.append("rotate_credential")
            if classified.should_fallback:
                recovery.append("fallback")
            
            if recovery:
                log_parts.append(f"recovery=[{', '.join(recovery)}]")
            
            # 使用更有信息量的消息
            display_msg = error_msg if error_msg else classified.message
            if display_msg:
                # 截断长消息
                msg = display_msg[:200] + "..." if len(display_msg) > 200 else display_msg
                log_parts.append(f"msg={msg}")
            
            self.logger.error(" | ".join(log_parts))
            
            # 返回详细的错误消息，供调用者使用
            return f"{error_type}: {error_msg}"

    def _raise_for_status(self, response: httpx.Response) -> None:
        """检查响应状态码，非 200 时抛出携带 response 的 HTTPStatusError
        
        使用此方法替代直接调用 response.raise_for_status()，
        确保异常携带完整的 response 对象供 error_classifier 分析。
        
        子类可覆盖此方法以添加 provider 特定的错误处理逻辑。
        """
        if response.status_code == 200:
            return
        
        # 记录错误日志
        if self.logger:
            self.logger.error(
                f"{self.provider_display_name} API error - "
                f"status: {response.status_code}, detail: {response.text}"
            )
        
        # 对于认证错误，可以抛出带有友好消息的异常
        if response.status_code == 401:
            raise httpx.HTTPStatusError(
                f"{self.provider_display_name} API Key 无效或已过期。",
                request=response.request,
                response=response,
            )
        
        # 其他错误直接让 httpx 抛出 HTTPStatusError，携带完整 response
        response.raise_for_status()

    def _validate_api_key(self):
        """验证 API Key 是否配置（子类可覆盖）

        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.config.api_key:
            return False, f"{self.provider_display_name} API Key 未配置。请设置环境变量或在配置中指定。"
        return True, None

    def _get_request_body_extra(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """获取额外的请求体参数（子类可覆盖）

        用于添加 tools 等 Provider 特定参数。
        默认返回空字典，子类可覆盖添加参数。
        """
        return {}

    def _should_handle_function_call(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查并处理 function_call/tool_calls（子类可覆盖）

        默认使用 schema_registry 中的统一提取逻辑。
        子类可覆盖此方法以处理特定格式。

        Returns:
            function_call 字典或 None
        """
        from tools.schema_registry import extract_tool_from_response
        return extract_tool_from_response(message)

    def _log_response_debug(self, message: Dict[str, Any], function_call: Optional[Dict[str, Any]] = None):
        """记录响应调试日志（子类可覆盖）

        在 output content 日志之后调用，用于记录调试信息。
        """
        if self.logger:
            self.logger.debug(f"{self.provider_display_name} message keys: {list(message.keys())}")
            if function_call:
                preview = self._format_function_call_for_log(function_call)
                self.logger.info(f"⬇️ {self.provider_display_name} → {preview}")
            else:
                self.logger.debug(f"{self.provider_display_name} function_call: {function_call}")

    def _format_function_call_for_log(self, function_call: Any) -> str:
        """格式化函数调用用于日志输出 - 简化参数，长字段截断，敏感字段脱敏

        处理多种格式：
        - OpenAI tool_calls: [{"id": "...", "type": "function", "function": {"name": "...", "arguments": "{...}"}}]
        - MiniMax function_call: {"name": "...", "arguments": "{...}"}
        - Claude tool_use: {"name": "...", "input": {...}}

        字段处理策略：
        - 敏感字段 (api_key, token, password, secret, authorization) → "***"
        - 长字符串 (>50字符) → 保留前30+后10字符
        - ID类字段 (board_id, task_id) → 保留前8+后4字符
        """
        import json

        SENSITIVE_KEYS = {"api_key", "token", "password", "secret", "authorization", "key", "pwd"}
        LONG_STRING_THRESHOLD = 50
        ID_TRUNCATE_BEFORE = 8
        ID_TRUNCATE_AFTER = 4

        def _truncate_long_string(s: str) -> str:
            if len(s) > LONG_STRING_THRESHOLD:
                return s[:30] + "..." + s[-10:]
            return s

        def _truncate_id(s: str) -> str:
            if len(s) > ID_TRUNCATE_BEFORE + ID_TRUNCATE_AFTER + 3:
                return s[:ID_TRUNCATE_BEFORE] + "..." + s[-ID_TRUNCATE_AFTER:]
            return s

        def _sanitize_value(v: Any, key: str) -> Any:
            key_lower = key.lower()
            # 敏感字段
            if key_lower in SENSITIVE_KEYS:
                return "***"
            # ID 类字段
            if "id" in key_lower and len(str(v)) > 20:
                return _truncate_id(str(v))
            # 普通字符串
            if isinstance(v, str):
                return _truncate_long_string(v)
            return v

        def _format_single_call(fc: Any) -> str:
            if not isinstance(fc, dict):
                return str(fc)

            # 提取函数名
            name = fc.get("function", {}).get("name") if isinstance(fc.get("function"), dict) else None
            if not name:
                name = fc.get("name", "unknown")

            # 提取参数
            arguments = fc.get("function", {}).get("arguments") if isinstance(fc.get("function"), dict) else None
            if arguments is None:
                arguments = fc.get("input", {})  # Claude 格式

            # 解析 arguments
            if isinstance(arguments, str):
                try:
                    args_dict = json.loads(arguments)
                except (json.JSONDecodeError, TypeError):
                    args_dict = {"raw": arguments}
            elif isinstance(arguments, dict):
                args_dict = arguments
            else:
                args_dict = {"raw": str(arguments)}

            # 清理参数
            safe_args = {k: _sanitize_value(v, k) for k, v in args_dict.items()}
            args_str = json.dumps(safe_args, ensure_ascii=False, separators=(", ", ":"))
            return f"{name}({args_str})"

        try:
            fc_list = function_call if isinstance(function_call, list) else [function_call]
            return " | ".join(_format_single_call(fc) for fc in fc_list)
        except Exception:
            return str(function_call)

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """生成文本响应"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """计算 token 数量"""
        pass

    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史"""
        self._message_history.append(Message(role=role, content=content))

    def clear_history(self) -> None:
        """清空历史"""
        self._message_history.clear()

    def get_history(self) -> List[Message]:
        """获取历史"""
        return self._message_history.copy()

    def set_history(self, messages: List[Message]) -> None:
        """设置历史"""
        self._message_history = messages.copy()

    def _build_messages(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None
    ) -> tuple[Optional[str], List[Dict[str, Any]], Optional[Dict]]:
        """构建消息列表

        Returns:
            (system_prompt, messages_list, prompt_meta)
            prompt_meta: system 消息的 _prompt_meta 元数据（如果有）
        """
        system = system_prompt or ""
        msg_list: List[Dict[str, Any]] = []
        prompt_meta: Optional[Dict] = None

        if messages:
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        system = (system + "\n" + msg.get("content", "")) if system else msg.get("content", "")
                        # 保存 _prompt_meta（只取第一个 system 消息的）
                        if prompt_meta is None and msg.get("_prompt_meta"):
                            prompt_meta = msg["_prompt_meta"]
                    else:
                        msg_dict = {"role": msg.get("role"), "content": msg.get("content")}
                        # 保留 tool_calls（assistant 消息需要）
                        if msg.get("tool_calls"):
                            msg_dict["tool_calls"] = msg["tool_calls"]
                        # 保留 tool_call_id（tool 消息需要）
                        if msg.get("tool_call_id"):
                            msg_dict["tool_call_id"] = msg["tool_call_id"]
                        # 保留 _prompt_meta（system 消息的元数据，用于日志分层显示）
                        if msg.get("_prompt_meta"):
                            msg_dict["_prompt_meta"] = msg["_prompt_meta"]
                        msg_list.append(msg_dict)
                else:
                    if msg.role == "system":
                        system = (system + "\n" + msg.content) if system else msg.content
                        # 保存 _prompt_meta
                        if prompt_meta is None and getattr(msg, "_prompt_meta", None):
                            prompt_meta = msg._prompt_meta
                    else:
                        msg_dict = {"role": msg.role, "content": msg.content}
                        # 保留 tool_calls
                        if getattr(msg, "tool_calls", None):
                            msg_dict["tool_calls"] = msg.tool_calls
                        # 保留 tool_call_id
                        if getattr(msg, "tool_call_id", None):
                            msg_dict["tool_call_id"] = msg.tool_call_id
                        # 保留 _prompt_meta
                        if getattr(msg, "_prompt_meta", None):
                            msg_dict["_prompt_meta"] = msg._prompt_meta
                        msg_list.append(msg_dict)

        # 只有当 prompt 非空时才添加用户消息
        # 避免在消息列表已包含用户消息时添加空消息
        if prompt:
            msg_list.append({"role": "user", "content": prompt})
        return (system if system else None, msg_list, prompt_meta)

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量（简化实现）"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        return int(chinese_chars * 2 + english_chars * 0.25)
    
    def _format_message_for_log(self, role: str, content: str) -> str:
        """格式化消息用于日志输出（开头100字符+省略+结尾100字符）"""
        # ANSI 256 色代码（低调配色方案：雾霾色调 - 低饱和度灰彩）
        COLORS = {
            "system": "\033[38;5;146m",    # 灰紫 - 系统提示词（信息说明）
            "user": "\033[38;5;180m",      # 灰橘 - 用户输入（操作意图）
            "assistant": "\033[38;5;109m", # 灰绿 - AI 回复（生成内容）
        }
        RESET = "\033[0m"

        color = COLORS.get(role, "")

        # 防御性检查：确保 content 不是 None
        if content is None:
            content = ""
        
        if len(content) > 200:
            preview = content[:100] + " ... " + content[-100:]
        else:
            preview = content

        return f"{color}{preview}{RESET}"
    
    def _format_system_prompt_name(self, content: str, prompt_meta: Dict = None) -> str:
        """格式化系统提示词名称：提取标题，附加额外信息
        
        规则：
        - 如果是第一行是 Markdown 标题（# 开头），提取标题文本作为名称
        - 如果有 prompt_meta.stable_keys，显示模板变量名列表
        - 如果有 prompt_meta，显示各层信息（如 [stable:100, context:50, volatile:30]）
        - 如果没有 prompt_meta 但有多行内容，附加 "(+N chars)"
        - 如果只有一行，直接显示
        
        颜色：使用 system 专用色（灰紫）
        """
        SYSTEM_COLOR = "\033[38;5;146m"  # 灰紫 - 系统提示词
        RESET = "\033[0m"
        
        if not content:
            return f"{SYSTEM_COLOR}[Empty System Prompt]{RESET}"
        
        lines = content.split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # 尝试提取 Markdown 标题
        if first_line.startswith('#'):
            # 去掉 # 和可能的空格
            name = first_line.lstrip('#').strip()
        else:
            # 非标题格式，取第一行前 60 字符
            name = first_line[:60] if len(first_line) > 60 else first_line
        
        # 构建额外信息
        if prompt_meta:
            stable_keys = prompt_meta.get("stable_keys", [])
            if stable_keys:
                # 显示模板变量名
                extra_info = f" [{', '.join(stable_keys)}]"
            else:
                # 显示各层信息
                stable = prompt_meta.get("stable_chars", 0)
                context = prompt_meta.get("context_chars", 0)
                volatile = prompt_meta.get("volatile_chars", 0)
                extra_info = f" [stable:{stable}, context:{context}, volatile:{volatile}]"
        else:
            # 计算额外字符数
            first_line_len = len(first_line)
            total_len = len(content)
            extra_chars = total_len - first_line_len
            
            if extra_chars > 0:
                extra_info = f" (+{extra_chars} chars)"
            else:
                extra_info = ""
        
        return f"{SYSTEM_COLOR}{name}{extra_info}{RESET}"
