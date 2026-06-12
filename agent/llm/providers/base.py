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

    def _log_input_messages(self, messages: List[Dict[str, Any]]):
        """记录输入消息（DEBUG级别）"""
        if self.logger:
            self.logger.debug(f"{self.provider_display_name} Input Messages ({len(messages)} messages):")
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                preview = self._format_message_for_log(role, content)
                self.logger.info(f"⬆️  [{i}] {role}: {preview}")

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

        默认返回 None 表示不处理 function_call。
        子类（如 MiniMax）可覆盖此方法检查 tool_calls。

        Returns:
            function_call 字典或 None
        """
        return None

    def _log_response_debug(self, message: Dict[str, Any], function_call: Optional[Dict[str, Any]] = None):
        """记录响应调试日志（子类可覆盖）

        在 output content 日志之后调用，用于记录调试信息。
        """
        if self.logger:
            self.logger.debug(f"{self.provider_display_name} message keys: {list(message.keys())}")
            self.logger.debug(f"{self.provider_display_name} function_call: {function_call}")

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
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """构建消息列表

        Returns:
            (system_prompt, messages_list)
        """
        system = system_prompt or ""
        msg_list: List[Dict[str, Any]] = []

        if messages:
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        system = (system + "\n" + msg.get("content", "")) if system else msg.get("content", "")
                    else:
                        msg_list.append({"role": msg.get("role"), "content": msg.get("content")})
                else:
                    if msg.role == "system":
                        system = (system + "\n" + msg.content) if system else msg.content
                    else:
                        msg_list.append({"role": msg.role, "content": msg.content})

        msg_list.append({"role": "user", "content": prompt})
        return (system if system else None, msg_list)

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

        if len(content) > 200:
            preview = content[:100] + " ... " + content[-100:]
        else:
            preview = content

        return f"{color}{preview}{RESET}"
