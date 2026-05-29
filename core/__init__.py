"""
Core module for the Handsome Agent.

This package contains the foundational components of the agent system,
including configuration management, response structuring, exception handling,
task routing, skill management, and session management.
"""

from .agent import (
    CustomAgent,
    BaseAgentModule,
    ExplanationModule,
    AgentConfig,
    AgentResponse
)

from .exceptions import (
    AgentError,
    InputValidationError,
    ResponseGenerationError,
    ConfigurationError,
    TimeoutError,
    ModuleNotFoundError
)

from .cache import LRUCache, create_cache_key, hash_config

from .router import (
    TaskRouter,
    IntentClassifier,
    RouteConfig,
    RouteMatch,
    router,
    route_handler
)

from .skill_manager import (
    SkillManager,
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    skill_manager,
    skill
)

from .session import (
    SessionManager,
    Session,
    Message,
    SessionConfig,
    session_manager
)

from .i18n import I18n, i18n, get_i18n

from .memory_provider import MemoryProvider
from .memory_manager import MemoryManager
from .builtin_memory import BuiltinMemoryProvider, builtin_memory_provider
from .trajectory_recorder import TrajectoryRecorder, trajectory_recorder
from .self_improvement import SelfImprovementEngine, self_improvement_engine

from .layer_logger import (
    LayerLogger,
    get_layer_logger,
    user_logger,
    control_logger,
    reasoning_logger,
    llm_logger,
    tools_logger,
    storage_logger,
    LAYER_EMOJI,
    LAYER_NAMES,
    configure_logging as configure_layer_logging
)

from .logging_manager import (
    LogManager,
    LogConfig,
    get_logger,
    get_access_logger,
    get_decision_logger,
    get_execution_logger,
    get_llm_logger,
    get_tool_logger,
    configure_logging,
    set_log_level,
    get_log_level,
    setup_logging_from_config,
    LOG_LAYERS
)

__version__ = "0.0.1"
__author__ = "Handsome Agent Team"

__all__ = [
    # Agent
    'CustomAgent',
    'BaseAgentModule',
    'ExplanationModule',
    'AgentConfig',
    'AgentResponse',
    
    # Exceptions
    'AgentError',
    'InputValidationError',
    'ResponseGenerationError',
    'ConfigurationError',
    'TimeoutError',
    'ModuleNotFoundError',
    
    # Cache
    'LRUCache',
    'create_cache_key',
    'hash_config',
    
    # Router
    'TaskRouter',
    'IntentClassifier',
    'RouteConfig',
    'RouteMatch',
    'router',
    'route_handler',
    
    # Skill Manager
    'SkillManager',
    'BaseSkill',
    'SkillMetadata',
    'SkillParameter',
    'SkillResult',
    'skill_manager',
    'skill',
    
    # Session
    'SessionManager',
    'Session',
    'Message',
    'SessionConfig',
    'session_manager',
    
    # i18n
    'I18n',
    'i18n',
    'get_i18n',
    
    # Memory
    'MemoryProvider',
    'MemoryManager',
    'BuiltinMemoryProvider',
    'builtin_memory_provider',
    
    # Trajectory & Self-Improvement
    'TrajectoryRecorder',
    'trajectory_recorder',
    'SelfImprovementEngine',
    'self_improvement_engine',
    
    # Layer Logger (Legacy)
    'LayerLogger',
    'get_layer_logger',
    'user_logger',
    'control_logger',
    'reasoning_logger',
    'llm_logger',
    'tools_logger',
    'storage_logger',
    'LAYER_EMOJI',
    'LAYER_NAMES',
    'configure_layer_logging',
    
    # Logging Manager (New)
    'LogManager',
    'LogConfig',
    'get_logger',
    'get_access_logger',
    'get_decision_logger',
    'get_execution_logger',
    'get_llm_logger',
    'get_tool_logger',
    'configure_logging',
    'set_log_level',
    'get_log_level',
    'setup_logging_from_config',
    'LOG_LAYERS'
]
