"""HTTP/WebSocket 适配器"""
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from ..gateway import BaseAdapter, GatewayConfig, BaseGateway, Gateway
from ..message import StandardMessage, MessageChannel


class HTTPAdapter(BaseAdapter):
    """HTTP/WebSocket 适配器"""
    
    def __init__(self, gateway: BaseGateway, config: GatewayConfig):
        super().__init__(gateway, MessageChannel.HTTP)
        self.config = config
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self._websocket_connections: list[WebSocket] = []
    
    async def start(self) -> None:
        """启动 HTTP 服务器"""
        self.app = FastAPI(title="Handsome Agent Gateway")
        
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        @self.app.post("/api/v1/process")
        async def process_message(message: StandardMessage) -> StandardMessage:
            """处理来自任意渠道的消息"""
            return await self.gateway._handle_message(message)
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket 端点"""
            await websocket.accept()
            self._websocket_connections.append(websocket)
            try:
                while True:
                    data = await websocket.receive_json()
                    message = StandardMessage.model_validate(data)
                    response = await self.gateway._handle_message(message)
                    await websocket.send_json(response.model_dump())
            except WebSocketDisconnect:
                self._websocket_connections.remove(websocket)
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        self.server = uvicorn.Server(config)
        asyncio.create_task(self.server.serve())
        
        self.logger.info(f"HTTP server started on {self.config.host}:{self.config.port}")
    
    async def stop(self) -> None:
        """停止 HTTP 服务器"""
        if self.server:
            self.server.should_exit = True
        self._websocket_connections.clear()
    
    async def send(self, message: StandardMessage) -> StandardMessage:
        """发送消息 - 通过 WebSocket"""
        if self._websocket_connections:
            for ws in self._websocket_connections:
                await ws.send_json(message.model_dump())
        return message
    
    async def receive(self) -> StandardMessage:
        """接收消息 - WebSocket 会自动处理"""
        raise NotImplementedError("Use WebSocket endpoint instead")