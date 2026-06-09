"""TUI Gateway - WebSocket 流式事件网关

将流式事件通过 WebSocket 推送到 Web 前端。
"""

import json
import asyncio
import uuid
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    """消息类型"""
    # 客户端 → 服务端
    SESSION_CREATE = "session.create"
    SESSION_CLOSE = "session.close"
    PROMPT_SUBMIT = "prompt.submit"
    PROMPT_CANCEL = "prompt.cancel"
    
    # 服务端 → 客户端
    SESSION_CREATED = "session.created"
    STREAM_DELTA = "stream.delta"
    STREAM_TOOL_START = "stream.tool_start"
    STREAM_TOOL_END = "stream.tool_end"
    STREAM_COMPLETE = "stream.complete"
    STREAM_ERROR = "stream.error"
    ERROR = "error"


@dataclass
class Session:
    """会话"""
    id: str
    websocket: Any  # WebSocket 连接
    created_at: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class StreamMessage:
    """流式消息"""
    type: str
    session_id: str
    data: Dict = field(default_factory=dict)


class TUIGateway:
    """
    TUI 网关 - WebSocket 流式事件服务器
    
    提供 WebSocket 接口，将流式事件推送到 Web 前端。
    
    用法::
    
        gateway = TUIGateway(host="0.0.0.0", port=8765)
        
        # 注册流式事件处理器
        async def on_stream(session_id, event):
            print(f"[{session_id}] {event.type}: {event.data}")
        
        gateway.set_stream_handler(on_stream)
        
        # 启动服务
        await gateway.start()
        
        # 在 Agent 中推送事件
        await gateway.emit_delta(session_id, "Hello, world!")
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
    ):
        self.host = host
        self.port = port
        self._sessions: Dict[str, Session] = {}
        self._stream_handler: Optional[Callable] = None
        self._server = None
        self._running = False
    
    @property
    def running(self) -> bool:
        return self._running
    
    def set_stream_handler(self, handler: Callable):
        """设置流式事件处理器"""
        self._stream_handler = handler
    
    async def start(self):
        """启动网关"""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        self._running = True
        print(f"TUI Gateway started on {self.host}:{self.port}")
    
    async def stop(self):
        """停止网关"""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._sessions.clear()
    
    async def _handle_client(self, reader, writer):
        """处理客户端连接"""
        session_id = str(uuid.uuid4())[:8]
        session = Session(
            id=session_id,
            websocket=WebSocketWrapper(reader, writer),
            created_at=asyncio.get_event_loop().time()
        )
        self._sessions[session_id] = session
        
        try:
            await self._send_json(session, {
                "type": "session.created",
                "session_id": session_id
            })
            
            async for data in session.websocket:
                await self._handle_message(session, data)
                
        except Exception as e:
            print(f"Session {session_id} error: {e}")
        finally:
            self._sessions.pop(session_id, None)
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
    async def _handle_message(self, session: Session, data: bytes):
        """处理客户端消息"""
        try:
            msg = json.loads(data.decode())
            msg_type = msg.get("type")
            params = msg.get("params", {})
            
            if msg_type == "prompt.submit":
                prompt = params.get("prompt", "")
                metadata = params.get("metadata", {})
                
                # 调用流式处理器
                if self._stream_handler:
                    await self._stream_handler(
                        session.id,
                        StreamMessage(
                            type="prompt",
                            session_id=session.id,
                            data={"prompt": prompt, "metadata": metadata}
                        )
                    )
                    
            elif msg_type == "prompt.cancel":
                if self._stream_handler:
                    await self._stream_handler(
                        session.id,
                        StreamMessage(
                            type="cancel",
                            session_id=session.id,
                            data={}
                        )
                    )
                    
            elif msg_type == "session.close":
                self._sessions.pop(session.id, None)
                
        except json.JSONDecodeError:
            await self._send_error(session, "Invalid JSON")
        except Exception as e:
            await self._send_error(session, str(e))
    
    async def _send_json(self, session: Session, data: dict):
        """发送 JSON 到客户端"""
        try:
            await session.websocket.send(json.dumps(data))
        except Exception as e:
            print(f"Failed to send to {session.id}: {e}")
    
    async def _send_error(self, session: Session, error: str):
        """发送错误到客户端"""
        await self._send_json(session, {
            "type": "error",
            "error": error
        })
    
    # ==================== 事件发射接口 ====================
    
    async def emit_delta(self, session_id: str, text: str):
        """发射增量文本"""
        session = self._sessions.get(session_id)
        if session:
            await self._send_json(session, {
                "type": "stream.delta",
                "data": {"text": text}
            })
    
    async def emit_reasoning(self, session_id: str, text: str):
        """发射推理内容"""
        session = self._sessions.get(session_id)
        if session:
            await self._send_json(session, {
                "type": "stream.reasoning",
                "data": {"text": text}
            })
    
    async def emit_tool_start(self, session_id: str, tool_name: str, params: dict):
        """发射工具开始"""
        session = self._sessions.get(session_id)
        if session:
            await self._send_json(session, {
                "type": "stream.tool_start",
                "data": {"tool_name": tool_name, "tool_input": params}
            })
    
    async def emit_tool_end(self, session_id: str, tool_name: str, result: dict):
        """发射工具结束"""
        session = self._sessions.get(session_id)
        if session:
            await self._send_json(session, {
                "type": "stream.tool_end",
                "data": {"tool_name": tool_name, "tool_output": result}
            })
    
    async def emit_complete(self, session_id: str, text: str = "", reasoning: str = None):
        """发射完成"""
        session = self._sessions.get(session_id)
        if session:
            await self._send_json(session, {
                "type": "stream.complete",
                "data": {"text": text, "reasoning": reasoning}
            })
    
    async def emit_error(self, session_id: str, message: str, error_type: str = "Error"):
        """发射错误"""
        session = self._sessions.get(session_id)
        if session:
            await self._send_json(session, {
                "type": "stream.error",
                "data": {"message": message, "error_type": error_type}
            })
    
    async def broadcast(self, event_type: str, data: dict, exclude: Set[str] = None):
        """广播到所有会话"""
        exclude = exclude or set()
        for session_id, session in self._sessions.items():
            if session_id not in exclude:
                await self._send_json(session, {
                    "type": event_type,
                    "data": data
                })


class WebSocketWrapper:
    """WebSocket 包装器（兼容 asyncio 流）"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer
    
    async def send(self, data: str):
        """发送数据"""
        self._writer.write(data.encode())
        await self._writer.drain()
    
    def close(self):
        """关闭连接"""
        self._writer.close()
    
    def __aiter__(self):
        return self
    
    async def __anext__(self) -> bytes:
        """异步迭代"""
        line = await self._reader.readline()
        if not line:
            raise StopAsyncIteration
        return line.strip()


async def create_gateway(
    host: str = "0.0.0.0",
    port: int = 8765,
    stream_emitter = None
) -> TUIGateway:
    """
    创建 TUI 网关
    
    Args:
        host: 监听地址
        port: 监听端口
        stream_emitter: 可选的 StreamEmitter，用于自动转发事件
        
    Returns:
        TUIGateway 实例
    """
    gateway = TUIGateway(host=host, port=port)
    
    # 如果提供了 StreamEmitter，自动转发事件
    if stream_emitter:
        # 保存 session_id 到 emitter 的映射
        session_map: Dict[str, Any] = {}
        
        async def on_stream(session_id: str, message: StreamMessage):
            if message.type == "prompt":
                # 新请求开始，存储 session_id
                session_map[id(stream_emitter)] = session_id
        
        gateway.set_stream_handler(on_stream)
        
        # 注意：完整的集成需要修改 StreamEmitter 来支持 gateway
        # 这里只是一个示例框架
    
    return gateway


__all__ = [
    "TUIGateway",
    "Session",
    "StreamMessage",
    "MessageType",
    "create_gateway",
]
