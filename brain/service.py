"""
Brain Service - 决策层核心服务
封装 Hermes Core 为 HTTP/RPC 服务
集成自我进化能力（TrajectoryRecorder + Curator）
"""

from typing import Optional, AsyncIterator, List
from dataclasses import dataclass
import logging
import uuid

from pydantic import BaseModel, Field
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from adapter.message import StandardMessage, MessageChannel
from adapter.protocols import MessageProtocol
from .agent.agent_loop import AgentLoop, AgentConfig as LoopConfig
from .trajectory import TrajectoryRecorder, Trajectory, TrajectoryStatus
from brain_curator import Curator, EvaluationReport


logger = logging.getLogger(__name__)


@dataclass
class BrainServiceConfig:
    """Brain Service 配置"""
    name: str = "HandsomeAgentBrain"
    host: str = "0.0.0.0"
    port: int = 8001
    max_iterations: int = 10
    timeout_seconds: float = 60.0
    enable_curator: bool = True
    enable_trajectory: bool = True
    executor_url: str = "http://localhost:8002"
    trajectory_storage_path: str = ".trajectories"
    api_key: Optional[str] = None


class ProcessRequest(BaseModel):
    """处理请求"""
    message: StandardMessage
    context: dict = Field(default_factory=dict)


class ProcessResponse(BaseModel):
    """处理响应"""
    message_id: str
    status: str
    response: Optional[str] = None
    tool_calls: list = Field(default_factory=list)
    trajectory_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ExecutionRequest(BaseModel):
    """执行请求"""
    tool_name: str
    parameters: dict = Field(default_factory=dict)


class ExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: str
    status: str
    tool_name: str = ""
    result: Optional[dict] = None
    error_message: Optional[str] = None


class TrajectoryStatsResponse(BaseModel):
    """轨迹统计响应"""
    total_trajectories: int
    success_count: int
    failure_count: int
    partial_count: int
    with_feedback_count: int
    success_rate: float


class BrainService:
    """
    Brain Service 主类
    
    严格参考 Hermes 实现，集成自我进化能力：
    - TrajectoryRecorder: 记录每个执行轨迹
    - Curator: 评估轨迹，合成技能，自动学习
    """
    
    def __init__(self, config: BrainServiceConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self._agent_loop: Optional[AgentLoop] = None
        self._trajectory_recorder: Optional[TrajectoryRecorder] = None
        self._curator: Optional[Curator] = None
        self._running = False
    
    def initialize(self) -> None:
        """初始化 Brain Service"""
        self.logger.info(f"Initializing Brain Service: {self.config.name}")
        
        # 初始化轨迹记录器
        if self.config.enable_trajectory:
            self._trajectory_recorder = TrajectoryRecorder(
                storage_path=self.config.trajectory_storage_path
            )
            self.logger.info("TrajectoryRecorder initialized")
        
        # 初始化 Curator
        if self.config.enable_curator and self._trajectory_recorder:
            from brain_curator import SkillWriter
            skill_writer = SkillWriter()
            self._curator = Curator(
                trajectory_recorder=self._trajectory_recorder,
                skill_writer=skill_writer,
                enable_auto_learn=True,
            )
            self.logger.info("Curator initialized")
        
        # 初始化 Agent Loop
        loop_config = LoopConfig(
            max_iterations=self.config.max_iterations,
            timeout_seconds=self.config.timeout_seconds,
            enable_curator=self.config.enable_curator,
            enable_trajectory=self.config.enable_trajectory,
        )
        self._agent_loop = AgentLoop(
            config=loop_config,
            trajectory_recorder=self._trajectory_recorder,
            curator=self._curator,
        )
        
        # 加载已学习的技能
        self._agent_loop.load_learned_skills()
        
        # 创建 FastAPI 应用
        self.app = FastAPI(title="Handsome Agent Brain Service")
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册 API 路由
        self._register_routes()
        
        self.logger.info("Brain Service initialized")
    
    def _register_routes(self) -> None:
        """注册 API 路由"""
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy", 
                "service": self.config.name,
                "curator_enabled": self.config.enable_curator,
                "learned_skills": self._agent_loop.get_learned_skills_count() if self._agent_loop else 0,
            }
        
        @self.app.post(MessageProtocol.ENDPOINTS["process"])
        async def process_message(request: ProcessRequest) -> ProcessResponse:
            """处理来自 Gateway 的消息"""
            return await self._handle_process_request(request)
        
        @self.app.post(MessageProtocol.ENDPOINTS["execute"])
        async def execute_tool(request: ExecutionRequest) -> ExecutionResponse:
            """直接执行工具调用"""
            return await self._handle_execution_request(request)
        
        @self.app.post("/api/v1/stream")
        async def stream_process(request: ProcessRequest) -> AsyncIterator[dict]:
            """流式处理消息"""
            async for chunk in self._handle_stream_request(request):
                yield chunk
        
        @self.app.get("/api/v1/trajectories")
        async def get_trajectories(limit: int = 10):
            """获取最近的轨迹"""
            if not self._trajectory_recorder:
                return {"trajectories": []}
            trajectories = self._trajectory_recorder.get_recent_trajectories(limit)
            return {
                "trajectories": [t.to_dict() for t in trajectories]
            }
        
        @self.app.get("/api/v1/trajectories/stats")
        async def get_trajectory_stats() -> TrajectoryStatsResponse:
            """获取轨迹统计"""
            if not self._trajectory_recorder:
                return TrajectoryStatsResponse(
                    total_trajectories=0, success_count=0,
                    failure_count=0, partial_count=0,
                    with_feedback_count=0, success_rate=0.0
                )
            stats = self._trajectory_recorder.get_statistics()
            return TrajectoryStatsResponse(**stats)
        
        @self.app.post("/api/v1/trajectories/{trajectory_id}/feedback")
        async def add_feedback(trajectory_id: str, feedback: str):
            """添加用户反馈"""
            if not self._trajectory_recorder or not self._curator:
                return {"success": False, "message": "Curator not enabled"}
            
            success = self._trajectory_recorder.add_feedback(trajectory_id, feedback)
            if success:
                skill = await self._curator.learn_from_feedback(trajectory_id, feedback)
                if skill:
                    self._agent_loop._learned_skills[skill.name] = skill
                return {"success": True, "skill_learned": skill is not None}
            return {"success": False}
        
        @self.app.get("/api/v1/skills/learned")
        async def get_learned_skills():
            """获取已学习的技能"""
            if not self._curator:
                return {"skills": []}
            skills = self._curator.get_learned_skills()
            return {
                "skills": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "trigger_patterns": s.trigger_patterns,
                        "confidence": s.confidence,
                    }
                    for s in skills
                ]
            }
    
    async def _handle_process_request(self, request: ProcessRequest) -> ProcessResponse:
        """处理消息请求"""
        self.logger.info(f"Processing message: {request.message.user_id}")
        
        try:
            result = await self._agent_loop.run(
                user_input=request.message.content.text or "",
                context=request.context,
            )
            
            return ProcessResponse(
                message_id=request.message.message_id,
                status="success",
                response=result["response"],
                tool_calls=result.get("tool_calls", []),
                trajectory_id=result.get("trajectory_id"),
                metadata=result.get("metadata", {}),
            )
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            return ProcessResponse(
                message_id=request.message.message_id,
                status="error",
                error_message=str(e),
            )
    
    async def _handle_execution_request(self, request: ExecutionRequest) -> ExecutionResponse:
        """处理工具执行请求"""
        self.logger.info(f"Executing tool: {request.tool_name}")
        
        return ExecutionResponse(
            execution_id=str(uuid.uuid4()),
            status="pending",
            tool_name=request.tool_name,
        )
    
    async def _handle_stream_request(self, request: ProcessRequest) -> AsyncIterator[dict]:
        """流式处理请求"""
        yield {"type": "start", "message_id": request.message.message_id}
        
        yield {"type": "end"}
    
    async def start(self) -> None:
        """启动 Brain Service"""
        if self.app is None:
            self.initialize()
        
        self.logger.info(f"Starting Brain Service on {self.config.host}:{self.config.port}")
        
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        self.server = uvicorn.Server(config)
        self._running = True
        asyncio.create_task(self.server.serve())
        
        self.logger.info("Brain Service started")
    
    async def stop(self) -> None:
        """停止 Brain Service"""
        self.logger.info("Stopping Brain Service...")
        if self.server:
            self.server.should_exit = True
        self._running = False
        self.logger.info("Brain Service stopped")
    
    async def run(self) -> None:
        """运行服务（阻塞）"""
        await self.start()
        while self._running:
            await asyncio.sleep(1)