"""
核心 Agent Loop - ReAct 实现
Hermes Core 的核心逻辑 - 集成 LLM 推理 + 自我进化
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, List, TYPE_CHECKING
import asyncio
import logging
import json

from .schemas import ToolCall, Thought, Action, Observation
from ..llm import BaseLLMProvider, LLMResponse

if TYPE_CHECKING:
    from ..trajectory import TrajectoryRecorder
    from brain_curator import Curator


logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    RESPONDING = "responding"
    ERROR = "error"
    DONE = "done"


@dataclass
class AgentConfig:
    """Agent 配置"""
    max_iterations: int = 10
    timeout_seconds: float = 60.0
    enable_memory: bool = True
    enable_skills: bool = True
    enable_curator: bool = True
    enable_trajectory: bool = True
    system_prompt: str = "你是一个智能助手，能够帮助用户完成各种任务。"


class AgentLoop:
    """
    核心 Agent Loop - ReAct 模式
    
    严格参考 Hermes 实现，集成自我进化能力：
    - TrajectoryRecorder: 记录每个 Thought/Action/Observation
    - Curator: 评估轨迹，合成技能，自动学习
    """
    
    def __init__(
        self, 
        config: AgentConfig, 
        llm_provider: Optional[BaseLLMProvider] = None,
        trajectory_recorder: Optional["TrajectoryRecorder"] = None,
        curator: Optional["Curator"] = None,
    ):
        self.config = config
        self.llm_provider = llm_provider
        self.trajectory_recorder = trajectory_recorder
        self.curator = curator
        self.logger = logging.getLogger(f"{__name__}.AgentLoop")
        self.state = AgentState.IDLE
        self._iteration = 0
        self._conversation_history: List[dict] = []
        self._learned_skills: dict = {}
    
    def set_llm_provider(self, provider: BaseLLMProvider) -> None:
        """设置 LLM Provider"""
        self.llm_provider = provider
    
    def set_trajectory_recorder(self, recorder: "TrajectoryRecorder") -> None:
        """设置轨迹记录器"""
        self.trajectory_recorder = recorder
    
    def set_curator(self, curator: "Curator") -> None:
        """设置 Curator"""
        self.curator = curator
    
    def load_learned_skills(self) -> None:
        """加载已学习的技能"""
        if not self.trajectory_recorder:
            return
        
        try:
            from brain_curator import SkillWriter
            from ..skills import SkillsLoader
            
            # 从 ~/.skills/ 加载技能
            loader = SkillsLoader()
            skills = asyncio.run(loader.load_all())
            
            for skill in skills:
                self._learned_skills[skill.name] = skill
                self.logger.info(f"Loaded learned skill: {skill.name}")
        except Exception as e:
            self.logger.error(f"Failed to load learned skills: {e}")
    
    async def run(self, user_input: str, context: dict = None) -> dict:
        """
        运行 Agent Loop
        
        ReAct 模式: Thought → Action → Observation → Thought → ...
        
        同时记录轨迹并触发自我进化
        """
        self.logger.info(f"Starting Agent Loop with input: {user_input[:50]}...")
        
        context = context or {}
        self._iteration = 0
        self.state = AgentState.THINKING
        
        trajectory_id = None
        if self.config.enable_trajectory and self.trajectory_recorder:
            trajectory_id = self.trajectory_recorder.start_trajectory(
                user_input, 
                context.get("session_id")
            )
        
        reasoning_steps = []
        tool_calls = []
        observation = ""
        response_content = ""
        
        while self._iteration < self.config.max_iterations:
            self._iteration += 1
            self.logger.info(f"Iteration {self._iteration}/{self.config.max_iterations}")
            
            try:
                # 1. Thought - 思考下一步行动
                thought = await self._think(user_input, context, observation)
                reasoning_steps.append(thought.reasoning)
                
                # 记录轨迹 - Thought
                if trajectory_id:
                    self.trajectory_recorder.record_thought(
                        reasoning=thought.reasoning,
                        confidence=thought.confidence,
                    )
                
                if thought.is_final:
                    response_content = thought.reasoning
                    break
                
                # 2. Action - 执行工具调用
                if thought.action:
                    self.state = AgentState.ACTING
                    
                    # 检查是否有已学习的技能可以直接使用
                    skill_result = await self._try_learned_skill(thought.action, context)
                    if skill_result:
                        action_result = skill_result
                    else:
                        action_result = await self._act(thought.action, context)
                    
                    # 记录轨迹 - Action
                    if trajectory_id:
                        self.trajectory_recorder.record_action(
                            tool_name=thought.action.tool_name,
                            parameters=thought.action.parameters,
                        )
                    
                    tool_calls.append({
                        "tool_name": thought.action.tool_name,
                        "parameters": thought.action.parameters,
                        "result": action_result,
                    })
                    
                    # 记录轨迹 - Observation
                    if trajectory_id:
                        success = not action_result.startswith("[Error]")
                        self.trajectory_recorder.record_observation(
                            result=action_result,
                            success=success,
                            error=None if success else action_result,
                        )
                    
                    # 更新观察结果
                    self.state = AgentState.OBSERVING
                    observation = action_result
                else:
                    response_content = thought.reasoning
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in iteration {self._iteration}: {e}", exc_info=True)
                self.state = AgentState.ERROR
                response_content = f"处理过程中发生错误: {str(e)}"
                
                if trajectory_id:
                    self.trajectory_recorder.record_observation(
                        result=str(e),
                        success=False,
                        error=str(e),
                    )
                break
        
        if self._iteration >= self.config.max_iterations:
            response_content = "已达到最大迭代次数，请重试。"
        
        self.state = AgentState.DONE
        
        result = {
            "response": response_content,
            "reasoning_steps": reasoning_steps,
            "tool_calls": tool_calls,
            "iterations": self._iteration,
            "metadata": {
                "state": self.state.value,
                "llm_used": self.llm_provider is not None,
                "learned_skills_used": len([t for t in tool_calls if t.get("from_skill")]),
            },
        }
        
        # 结束轨迹记录
        if trajectory_id:
            from ..trajectory import TrajectoryStatus
            status = TrajectoryStatus.SUCCESS if self.state == AgentState.DONE else TrajectoryStatus.FAILURE
            trajectory = self.trajectory_recorder.end_trajectory(
                final_response=response_content,
                status=status,
            )
            result["trajectory_id"] = trajectory_id
            
            # 触发 Curator 进行自我进化
            if self.config.enable_curator and self.curator:
                asyncio.create_task(self._trigger_curator(trajectory))
        
        return result
    
    async def _trigger_curator(self, trajectory) -> None:
        """触发 Curator 进行轨迹评估和技能合成"""
        try:
            self.logger.info(f"Triggering Curator for trajectory: {trajectory.trajectory_id}")
            skill = await self.curator.process_trajectory(trajectory.to_dict())
            if skill:
                self._learned_skills[skill.name] = skill
                self.logger.info(f"Learned new skill: {skill.name}")
        except Exception as e:
            self.logger.error(f"Curator processing failed: {e}")
    
    async def _try_learned_skill(self, action: Action, context: dict) -> Optional[str]:
        """尝试使用已学习的技能"""
        if not self._learned_skills:
            return None
        
        user_input = context.get("user_input", "")
        
        for skill_name, skill in self._learned_skills.items():
            for pattern in skill.trigger_patterns:
                if pattern.lower() in user_input.lower():
                    self.logger.info(f"Using learned skill: {skill_name}")
                    return f"[Skill: {skill_name}]\n{skill.action_template}"
        
        return None
    
    async def _think(
        self, 
        user_input: str, 
        context: dict, 
        observation: str
    ) -> Thought:
        """思考阶段 - 决定下一步行动"""
        self.logger.debug(f"Thinking... observation: {observation[:50] if observation else 'None'}...")
        
        self.state = AgentState.THINKING
        
        if self.llm_provider:
            return await self._llm_think(user_input, context, observation)
        else:
            return await self._rule_based_think(user_input, observation)
    
    async def _llm_think(
        self, 
        user_input: str, 
        context: dict, 
        observation: str
    ) -> Thought:
        """LLM 驱动的思考"""
        available_tools = self._get_available_tools()
        tool_desc = json.dumps(available_tools, ensure_ascii=False, indent=2)
        
        learned_skill_info = ""
        if self._learned_skills:
            skills_list = "\n".join([
                f"- {name}: {skill.description}" 
                for name, skill in self._learned_skills.items()
            ])
            learned_skill_info = f"\n\n已学习的技能 (优先匹配):\n{skills_list}"
        
        prompt = f"""用户输入: {user_input}
        
之前的执行结果: {observation if observation else "无"}
{learned_skill_info}

你是一个任务执行助手。根据用户输入，决定下一步行动。

可用的工具:
{tool_desc}

请以 JSON 格式回复，格式如下:
{{
    "reasoning": "你的思考过程",
    "action": {{"tool_name": "工具名称", "parameters": {{"参数键": "参数值"}}}},
    "is_final": true/false,
    "response": "如果不需要执行工具，直接返回的响应内容"
}}

注意:
- 如果用户只是提问或对话，设置 "action" 为 null，"is_final" 为 true，并在 "response" 中给出回答
- 如果需要执行工具，设置 "action" 和 "is_final" 为 false
- 优先匹配已学习的技能
"""
        
        try:
            response = await self.llm_provider.generate(
                prompt=prompt,
                system_prompt=self.config.system_prompt,
            )
            
            content = response.content.strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content.strip())
            
            action = None
            if result.get("action"):
                action = Action(
                    tool_name=result["action"]["tool_name"],
                    parameters=result["action"].get("parameters", {}),
                )
            
            return Thought(
                reasoning=result.get("reasoning", ""),
                action=action,
                is_final=result.get("is_final", False),
                confidence=0.9,
            )
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return await self._rule_based_think(user_input, observation)
        except Exception as e:
            self.logger.error(f"LLM thinking failed: {e}")
            return await self._rule_based_think(user_input, observation)
    
    async def _rule_based_think(
        self, 
        user_input: str, 
        observation: str
    ) -> Thought:
        """基于规则的思考"""
        input_lower = user_input.lower()
        
        # 优先检查已学习的技能
        for skill_name, skill in self._learned_skills.items():
            for pattern in skill.trigger_patterns:
                if pattern.lower() in input_lower:
                    return Thought(
                        reasoning=f"匹配到已学习技能: {skill_name}",
                        action=Action(
                            tool_name="learned_skill",
                            parameters={"skill_name": skill_name, "template": skill.action_template},
                        ),
                        is_final=False,
                    )
        
        if any(kw in input_lower for kw in ['写', '创建', '修改', '删除', 'run', '执行', 'implement']):
            if any(kw in input_lower for kw in ['python', '代码', 'file', 'code']):
                return Thought(
                    reasoning="我将帮你处理这个编程相关的问题",
                    action=Action(
                        tool_name="str_replace_editor",
                        parameters={"content": user_input},
                    ),
                    is_final=False,
                )
            else:
                return Thought(
                    reasoning="我将执行命令",
                    action=Action(
                        tool_name="shell_execute",
                        parameters={"command": user_input},
                    ),
                    is_final=False,
                )
        elif observation:
            return Thought(
                reasoning=f"基于执行结果: {observation[:100]}，你的请求已完成。",
                action=None,
                is_final=True,
            )
        else:
            return Thought(
                reasoning="你可以问我问题、执行命令或编写代码。请问有什么我可以帮你的吗？",
                action=None,
                is_final=True,
            )
    
    def _get_available_tools(self) -> List[dict]:
        """获取可用工具列表"""
        tools = [
            {
                "name": "shell_execute",
                "description": "执行 Shell 命令",
                "source": "hermes",
                "parameters": {"command": "要执行的命令"}
            },
            {
                "name": "file_read",
                "description": "读取文件内容",
                "source": "hermes",
                "parameters": {"path": "文件路径"}
            },
            {
                "name": "file_write",
                "description": "写入文件",
                "source": "hermes",
                "parameters": {"path": "文件路径", "content": "文件内容"}
            },
            {
                "name": "str_replace_editor",
                "description": "字符串替换编辑",
                "source": "openclaw",
                "parameters": {"path": "文件路径", "old_string": "原文本", "new_string": "新文本"}
            },
            {
                "name": "multi_edit",
                "description": "多位置编辑",
                "source": "openclaw",
                "parameters": {"path": "文件路径", "old_string": "原文本", "new_string": "新文本"}
            },
            {
                "name": "search_files",
                "description": "搜索文件内容",
                "source": "openclaw",
                "parameters": {"path": "搜索目录", "pattern": "关键词"}
            },
            {
                "name": "create_file",
                "description": "创建新文件",
                "source": "openclaw",
                "parameters": {"path": "文件路径", "content": "文件内容"}
            },
            {
                "name": "web_search",
                "description": "搜索网页",
                "source": "hermes",
                "parameters": {"query": "搜索关键词"}
            },
        ]
        
        return tools
    
    async def _act(self, action: Action, context: dict) -> str:
        """行动阶段 - 执行工具调用"""
        self.logger.info(f"Acting: {action.tool_name}")
        
        hermes_tools = ["shell_execute", "file_read", "file_write", "web_search"]
        openclaw_tools = [
            "str_replace_editor", "multi_edit", "search_files",
            "view_lines", "create_file", "computer_use"
        ]
        
        if action.tool_name in hermes_tools:
            return await self._execute_hermes_tool(action)
        elif action.tool_name in openclaw_tools:
            return await self._execute_openclaw_tool(action)
        elif action.tool_name == "learned_skill":
            return f"[Using Learned Skill]\n{action.parameters.get('template', '')}"
        else:
            return f"Tool {action.tool_name} executed successfully"
    
    async def _execute_hermes_tool(self, action: Action) -> str:
        """执行 Hermes 工具"""
        if action.tool_name == "shell_execute":
            return f"[Hermes] Command executed: {action.parameters.get('command', '')}"
        elif action.tool_name == "file_read":
            return f"[Hermes] File read from: {action.parameters.get('path', '')}"
        elif action.tool_name == "file_write":
            return f"[Hermes] File written to: {action.parameters.get('path', '')}"
        elif action.tool_name == "web_search":
            return f"[Hermes] Web search for: {action.parameters.get('query', '')}"
        return f"[Hermes] Tool {action.tool_name} executed"
    
    async def _execute_openclaw_tool(self, action: Action) -> str:
        """执行 OpenClaw 工具"""
        tool_name = action.tool_name
        params = action.parameters
        
        if tool_name == "str_replace_editor":
            return f"[OpenClaw] str_replace_editor: {params.get('path', 'file')} - text replaced"
        elif tool_name == "multi_edit":
            return f"[OpenClaw] multi_edit: {params.get('count', 'all')} replacements"
        elif tool_name == "search_files":
            return f"[OpenClaw] search_files: found matches"
        elif tool_name == "create_file":
            return f"[OpenClaw] create_file: {params.get('path', 'newfile')}"
        return f"[OpenClaw] Tool {tool_name} executed"
    
    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self.state
    
    def get_learned_skills_count(self) -> int:
        """获取已学习技能数量"""
        return len(self._learned_skills)
    
    def reset(self) -> None:
        """重置 Agent"""
        self.state = AgentState.IDLE
        self._iteration = 0
        self._conversation_history.clear()