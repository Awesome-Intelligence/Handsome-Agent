# Handsome Agent 编码规范

> 打造 Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

---

## 目录

1. [设计哲学](#1-设计哲学)
2. [代码风格](#2-代码风格)
3. [命名约定](#3-命名约定)
4. [模块与文件组织](#4-模块与文件组织)
5. [文档字符串](#5-文档字符串)
6. [类型提示](#6-类型提示)
7. [异常处理](#7-异常处理)
8. [日志规范](#8-日志规范)
9. [测试规范](#9-测试规范)
10. [安全规范](#10-安全规范)
11. [性能规范](#11-性能规范)
12. [跨平台兼容性](#12-跨平台兼容性)
13. [Git 提交规范](#13-git-提交规范)
14. [代码审查清单](#14-代码审查清单)

---

## 1. 设计哲学

### 1.1 核心原则

| 原则 | 描述 | 实践 |
|------|------|------|
| **模块化** | 高内聚、低耦合 | 每个模块有明确职责，通过接口交互 |
| **可扩展性** | 插件化架构 | 使用注册表模式、工厂模式 |
| **容错性** | 优雅降级 | 降级方案：LLM → 关键词 → 规则 |
| **安全性** | 零信任设计 | 输入验证、白名单机制 |
| **可观测性** | 分层日志 | DEBUG/INFO/WARNING/ERROR 四级 |

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────┐
│                  🚪 接入层 (Adapter)                  │
│  - 消息协议转换                                      │
│  - 鉴权与限流                                       │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  🧠 决策层 (Brain)                   │
│  - 意图识别 (Intent Classifier)                     │
│  - 任务路由 (Task Router)                           │
│  - 工具选择 (Skill Manager)                         │
│  - 记忆管理 (Memory Manager)                         │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  📝 后处理层 (Curator)                │
│  - 轨迹评估                                         │
│  - 技能合成                                         │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  🏃 执行层 (Executor)                │
│  - Shell 执行器 (白名单保护)                        │
│  - Docker 隔离执行                                  │
└─────────────────────────────────────────────────────┘
```

### 1.3 设计模式应用

- **工厂模式**: `LLMFactory` 创建不同 LLM Provider
- **注册表模式**: `SkillRegistry` 技能注册与发现
- **适配器模式**: `HermesAdapter` / `OpenClawAdapter` 统一工具 Schema
- **策略模式**: 意图分类支持关键词/LLM/混合三种模式
- **装饰器模式**: `@route_handler` 注册路由

---

## 2. 代码风格

### 2.1 基础规范

- **遵循 PEP 8** 标准
- **缩进**: 4 个空格（不使用 Tab）
- **行长限制**: 100 字符（软限制 120）
- **文件编码**: UTF-8
- **行尾符**: Unix 风格 (`\n`)

### 2.2 导入规范

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块说明（必须包含）
"""

# 标准库
import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# 第三方库
import yaml
from pydantic_settings import BaseSettings

# 本地导入（按相对路径排序）
from shared.config import get_settings
from shared.exceptions import HandsomeAgentError
from core.router import TaskRouter


# 裸导入（仅在类型检查时使用）
if TYPE_CHECKING:
    from brain.agent import AgentLoop
```

### 2.3 空白规范

```python
# ✅ 正确：在二元运算符两侧加空格
total = a + b
result = (x > 0) and (y < 10)

# ❌ 错误：紧贴括号
total=a+b

# ✅ 正确：函数参数列表中紧贴括号
def func(a, b, c):
    pass

# ✅ 正确：函数调用中紧贴括号
func(a, b, c)

# ✅ 正确：函数定义签名（参数列表断行）
def long_function_name(
    param1: str,
    param2: int,
    param3: List[str],
) -> Dict[str, Any]:
    pass
```

### 2.4 行长度与断行

```python
# 字典断行
config = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
}

# 函数调用断行（对齐第一个参数）
result = some_long_function_name(
    argument1,
    argument2,
    argument3,
)

# 条件表达式断行
if (
    condition1
    and condition2
    or condition3
):
    pass
```

---

## 3. 命名约定

### 3.1 通用规则

| 类型 | 规则 | 示例 |
|------|------|------|
| **模块名** | 小写下划线 | `session_manager.py` |
| **类名** | 大驼峰 | `SessionManager` |
| **函数名** | 小写下划线 | `get_session()` |
| **变量名** | 小写下划线 | `session_id` |
| **常量** | 全大写下划线 | `MAX_RETRY_COUNT` |
| **私有成员** | 前缀下划线 | `_private_method()` |
| **保护成员** | 单下划线 | `_protected_var` |

### 3.2 命名风格映射

```python
# 类名 (CamelCase)
class SessionManager:
    pass

class IntentClassifier:
    pass

class BrainServiceError(Exception):
    pass

# 函数和方法 (snake_case)
def get_session(session_id: str) -> Optional[Session]:
    pass

def classify_intent(text: str) -> str:
    pass

# 变量 (snake_case)
user_id = "12345"
session_list = []
is_enabled = True

# 常量 (UPPER_SNAKE_CASE)
MAX_HISTORY_LENGTH = 50
DEFAULT_TIMEOUT = 30.0

# 私有属性
class Agent:
    def __init__(self):
        self._config = {}  # 单下划线：受保护
        self.__cache = {}  # 双下划线：类私有
```

### 3.3 命名禁忌

```python
# ❌ 避免：单字母变量（循环变量除外）
# ✅ 正确
for index in range(10):
    pass

# ✅ 正确：简短循环
for i in range(10):
    pass

# ❌ 避免：中文拼音
# ✅ 正确
ji_ci_chang_du = "基词长度"
keyword_intent = "关键词意图"

# ❌ 避免：与内置函数同名
# ✅ 正确
list_items = []  # 而非 items = []
dict_config = {}  # 而非 config = {}

# ❌ 避免：过于通用的名字
# ✅ 正确：具体化
http_response = fetch_data()
json_payload = parse_message()
```

---

## 4. 模块与文件组织

### 4.1 文件结构

```
handsome_agent/
├── adapter/              # 🚪 接入层
│   ├── __init__.py      # 导出公共接口
│   ├── gateway.py       # Gateway 核心
│   ├── message.py       # 消息格式定义
│   ├── adapters/        # 渠道适配器
│   └── protocols/       # 通信协议
│
├── brain/               # 🧠 决策层
│   ├── __init__.py
│   ├── agent/           # Agent 核心
│   ├── llm/             # LLM 集成
│   ├── memory/          # 记忆存储
│   └── skills/          # 技能管理
│
├── core/                # 核心模块
│   ├── __init__.py
│   ├── agent.py         # 主 Agent 类
│   ├── router.py        # 任务路由
│   ├── session.py       # 会话管理
│   └── cache.py         # 缓存
│
├── shared/              # 📦 共享模块
│   ├── __init__.py
│   ├── config.py        # 配置管理
│   ├── exceptions.py    # 公共异常
│   ├── logging.py       # 日志配置
│   └── models.py        # 数据模型
│
├── tests/               # 🧪 测试
│   ├── unit/
│   ├── integration/
│   └── conftest.py      # pytest 配置
│
└── config/              # 配置文件
    └── intents.yaml     # 意图关键词配置
```

### 4.2 `__init__.py` 规范

```python
# adapter/__init__.py
"""Adapter Layer - 接入层模块"""

from .gateway import Gateway
from .message import Message, MessageType

__all__ = [
    "Gateway",
    "Message",
    "MessageType",
]
```

### 4.3 模块职责划分

| 模块 | 职责 | 依赖规则 |
|------|------|----------|
| `shared/` | 公共工具，无项目依赖 | 禁止依赖其他模块 |
| `core/` | 核心业务逻辑 | 依赖 `shared/` |
| `adapter/` | 接入层 | 依赖 `core/` |
| `brain/` | 决策层 | 依赖 `core/` |
| `executor/` | 执行层 | 依赖 `core/` |
| `tools/` | 工具定义 | 可依赖所有层 |

---

## 5. 文档字符串

### 5.1 文档字符串类型

```python
class SessionManager:
    """
    Session Manager - 会话管理器
    
    负责管理用户会话的创建、存储和检索。
    支持内存缓存和文件持久化两种模式。
    
    Attributes:
        session_store: 会话存储后端
        max_history_length: 最大历史记录长度
        auto_save_interval: 自动保存间隔（秒）
    
    Example:
        >>> manager = SessionManager()
        >>> session = manager.create_session("user_001")
        >>> session.add_message("user", "Hello")
    """
    
    def __init__(
        self,
        storage_path: str = "./sessions",
        max_history: int = 50,
    ):
        """
        初始化会话管理器
        
        Args:
            storage_path: 会话文件存储路径
            max_history: 单个会话最大消息数
        """
        pass


def classify_intent(text: str) -> str:
    """
    分类用户意图
    
    使用关键词匹配或 LLM 辅助分类用户输入的意图。
    
    Args:
        text: 用户输入文本
        
    Returns:
        意图类型字符串 (conversation | operation | coding)
        
    Raises:
        ValueError: 当输入文本为空时
        
    Example:
        >>> classify_intent("帮我写一段代码")
        'coding'
    """
    pass
```

### 5.2 Google 风格文档示例

```python
def process_data(
    data: List[Dict[str, Any]],
    config: Optional[Config] = None,
) -> List[ProcessedItem]:
    """
    Process raw data with optional configuration.
    
    Args:
        data: List of raw data dictionaries to process.
        config: Optional configuration object. If None, uses default settings.
        
    Returns:
        List of processed items with normalized fields.
        
    Raises:
        DataValidationError: If data contains invalid entries.
        ProcessingError: If processing fails due to system error.
        
    Example:
        >>> raw = [{"id": 1, "value": "test"}]
        >>> result = process_data(raw)
        >>> len(result)
        1
    """
    pass
```

---

## 6. 类型提示

### 6.1 必需类型提示

```python
# ✅ 正确：函数必须标注返回类型
def get_session(session_id: str) -> Optional[Session]:
    ...

# ✅ 正确：公共类属性必须标注
class Agent:
    name: str
    config: Dict[str, Any]
    is_running: bool = False

# ✅ 正确：复杂泛型
from typing import TypeVar, Generic, Union

T = TypeVar("T")
Result = Union[T, None]

def get_result() -> Result[str]:
    return "success"
```

### 6.2 类型别名

```python
# 常用类型别名定义在 types.py
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

# 消息类型
MessageDict = Dict[str, Any]
SessionData = Dict[str, Any]

# 回调类型
EventHandler = Callable[[Event], None]
Validator = Callable[[Any], bool]

# 路径类型
PathLike = Union[str, Path]
```

---

## 7. 异常处理

### 7.1 异常层次结构

```python
# shared/exceptions.py

class HandsomeAgentError(Exception):
    """基础异常 - 所有异常的基类"""
    
    def __init__(self, message: str, code: int = 1000):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BrainServiceError(HandsomeAgentError):
    """Brain Service 异常"""
    
    def __init__(self, message: str, code: int = 2000):
        super().__init__(message, code)


class ExecutorError(HandsomeAgentError):
    """执行器异常"""
    
    def __init__(self, message: str, code: int = 3000):
        super().__init__(message, code)


class ToolError(HandsomeAgentError):
    """工具异常"""
    
    def __init__(self, message: str, tool_name: str = "", code: int = 4000):
        self.tool_name = tool_name
        super().__init__(message, code)


class SecurityError(HandsomeAgentError):
    """安全异常 - 包含敏感信息时的异常"""
    
    def __init__(self, message: str, code: int = 6000):
        super().__init__(message, code)
```

### 7.2 异常使用规范

```python
# ✅ 正确：具体异常类型
raise ToolError(
    message=f"Tool execution failed: {tool_name}",
    tool_name=tool_name,
    code=4001,
)

# ✅ 正确：异常链
try:
    result = process_data()
except ValueError as e:
    raise ProcessingError(f"Failed to process data: {e}") from e

# ✅ 正确：捕获具体异常
try:
    config = load_config()
except FileNotFoundError:
    logger.warning("Config file not found, using defaults")
    config = DEFAULT_CONFIG
except json.JSONDecodeError as e:
    raise ConfigError(f"Invalid config format: {e}") from e

# ❌ 错误：裸 except
try:
    risky_operation()
except:
    pass

# ❌ 错误：过于宽泛的异常
except Exception as e:
    print("Error occurred")
```

---

## 8. 日志规范

### 8.1 日志配置

```python
# shared/logging.py

import logging
import sys
from pathlib import Path

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    enable_console: bool = True,
) -> None:
    """配置日志系统"""
    
    handlers = []
    
    # 控制台输出
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        handlers.append(console_handler)
    
    # 文件输出
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        handlers.append(file_handler)
    
    # 根日志配置
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )
```

### 8.2 日志使用规范

```python
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False  # 避免重复日志
    
    def classify(self, text: str) -> str:
        self.logger.debug(f"Classifying text: {text[:50]}...")
        
        if not text:
            self.logger.warning("Empty text received")
            return "conversation"
        
        try:
            result = self._classify_impl(text)
            self.logger.info(f"Classification result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Classification failed: {e}", exc_info=True)
            raise


# ✅ 正确：使用 f-string（Python 3.6+）
logger.info(f"Processing {count} items")

# ✅ 正确：避免日志注入
user_input = sanitize(user_input)  # 先清理
logger.info(f"User input: {user_input}")  # 再记录

# ❌ 错误：字符串格式化在日志中
logger.info("User input: " + user_input)

# ✅ 正确：长日志分多行
logger.info(
    "Processing request: "
    f"user_id={user_id}, "
    f"intent={intent}, "
    f"confidence={confidence:.2f}"
)
```

### 8.3 日志级别使用

| 级别 | 使用场景 |
|------|----------|
| **DEBUG** | 开发调试：变量值、函数调用、循环进度 |
| **INFO** | 正常流程：配置加载、服务启动、任务完成 |
| **WARNING** | 异常但可处理：配置缺失、默认值使用、降级执行 |
| **ERROR** | 异常且不可处理：API 失败、文件损坏、认证失败 |
| **CRITICAL** | 系统级错误：数据库不可用、内存耗尽 |

---

## 9. 测试规范

### 9.1 测试文件组织

```
tests/
├── unit/                    # 单元测试
│   ├── core/
│   │   ├── __init__.py
│   │   ├── test_router.py
│   │   └── test_session.py
│   ├── brain/
│   │   └── test_agent_loop.py
│   └── conftest.py          # 共享 fixture
│
├── integration/             # 集成测试
│   └── test_full_flow.py
│
└── conftest.py              # 全局配置
```

### 9.2 测试命名

```python
# test_session.py

import pytest
from core.session import Session, SessionManager


class TestSession:
    """Session 类的单元测试"""
    
    def test_create_session_with_valid_id(self):
        """测试有效 session_id 创建会话"""
        session = Session(session_id="test_001")
        assert session.session_id == "test_001"
        assert session.messages == []
    
    def test_add_message_increments_count(self):
        """测试添加消息后计数增加"""
        session = Session(session_id="test_001")
        session.add_message("user", "Hello")
        assert session.get_message_count() == 1
    
    def test_add_message_trims_old_history(self):
        """测试超长历史被修剪"""
        session = Session(
            session_id="test_001",
            config=SessionConfig(max_history_length=3)
        )
        for i in range(5):
            session.add_message("user", f"Message {i}")
        assert session.get_message_count() == 3


class TestSessionManager:
    """SessionManager 类的单元测试"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """提供测试用 SessionManager"""
        config = SessionConfig(history_path=str(tmp_path))
        return SessionManager(config)
    
    def test_create_session_returns_new_session(self, manager):
        """测试创建会话返回新会话实例"""
        session = manager.create_session("new_session")
        assert isinstance(session, Session)
        assert session.session_id == "new_session"
    
    def test_get_session_returns_existing_session(self, manager):
        """测试获取已存在会话"""
        session1 = manager.create_session("test")
        session2 = manager.get_session("test")
        assert session1 is session2  # 同一对象
```

### 9.3 测试覆盖率要求

| 模块类型 | 最低覆盖率 |
|----------|------------|
| 核心模块 (`core/`) | 90% |
| Brain 模块 (`brain/`) | 85% |
| 工具模块 (`tools/`) | 80% |
| Adapter 模块 | 75% |
| 整体项目 | 80% |

### 9.4 Mock 使用规范

```python
from unittest.mock import Mock, patch, MagicMock
import pytest


class TestIntentClassifier:
    
    @patch("core.router.YAML_CONFIG", TEST_CONFIG)
    def test_classify_with_mock_llm(self):
        """测试使用 Mock LLM 的分类"""
        mock_llm = Mock()
        mock_llm.generate.return_value = "conversation"
        
        classifier = IntentClassifier(llm_provider=mock_llm)
        result = classifier.classify("Hello")
        
        assert result == "conversation"
        mock_llm.generate.assert_called_once()
    
    def test_classify_fallback_on_llm_error(self):
        """测试 LLM 失败时的降级处理"""
        mock_llm = Mock()
        mock_llm.generate.side_effect = LLMError("API timeout")
        
        classifier = IntentClassifier(
            llm_provider=mock_llm,
            mode="llm",  # LLM 优先模式
        )
        
        # 应该降级到关键词模式
        result = classifier.classify("帮我查天气")
        assert result == "operation"
```

---

## 10. 安全规范

### 10.1 输入验证

```python
# ✅ 正确：严格验证输入
def execute_command(command: str) -> str:
    # 白名单验证
    allowed_commands = ["git", "npm", "pip", "python"]
    cmd_parts = command.strip().split()
    
    if not cmd_parts:
        raise SecurityError("Empty command")
    
    base_cmd = cmd_parts[0]
    if base_cmd not in allowed_commands:
        raise SecurityError(f"Command not allowed: {base_cmd}")
    
    # 危险模式检测
    dangerous_patterns = [
        "rm -rf /",
        "curl | sh",
        "; rm ",
        "&& rm ",
    ]
    for pattern in dangerous_patterns:
        if pattern in command:
            raise SecurityError(f"Dangerous pattern detected")
    
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        timeout=30,
    )


# ❌ 错误：信任用户输入
def execute_command(command: str) -> str:
    return os.system(command)  # 危险！
```

### 10.2 敏感信息处理

```python
import os

# ✅ 正确：从环境变量获取密钥
api_key = os.environ.get("API_KEY")
if not api_key:
    raise SecurityError("API_KEY not configured")

# ✅ 正确：日志中脱敏
def log_credentials(key: str):
    # 只记录首尾字符
    masked = f"{key[:4]}...{key[-4:]}"
    logger.info(f"Using API key: {masked}")

# ❌ 错误：硬编码密钥
API_KEY = "sk-xxxxx"  # 禁止！

# ❌ 错误：日志中暴露密钥
logger.info(f"API_KEY={api_key}")  # 危险！
```

### 10.3 文件路径安全

```python
from pathlib import Path
import os


def safe_read_file(base_path: Path, user_path: str) -> str:
    """安全读取文件，防止路径遍历攻击"""
    
    # 解析用户路径
    target = (base_path / user_path).resolve()
    
    # 检查是否在允许目录内
    if not str(target).startswith(str(base_path.resolve())):
        raise SecurityError("Path traversal attempt detected")
    
    # 检查文件存在
    if not target.exists():
        raise FileNotFoundError(f"File not found: {user_path}")
    
    return target.read_text()


# ✅ 正确：使用 temp directory
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    temp_file = Path(tmpdir) / "output.json"
    process(temp_file)
# 临时文件自动清理
```

---

## 11. 性能规范

### 11.1 缓存策略

```python
from functools import lru_cache
from typing import Optional
import time


# ✅ 正确：LRU 缓存热点数据
@lru_cache(maxsize=128)
def parse_intent_config(config_path: str) -> Dict[str, Any]:
    """意图配置解析（缓存避免重复解析）"""
    with open(config_path) as f:
        return yaml.safe_load(f)


# ✅ 正确：TTL 缓存
class TTLCache:
    """简单的 TTL 缓存实现"""
    
    def __init__(self, ttl: float = 300.0):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        self.cache[key] = (value, time.time())


# ❌ 错误：在循环中重复创建对象
for item in items:
    parser = Parser()  # 每次循环创建新实例
    parser.parse(item)
```

### 11.2 异步编程

```python
import asyncio
from typing import List


# ✅ 正确：并发执行 I/O 操作
async def fetch_all(urls: List[str]) -> List[str]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_url(url)) for url in urls]
    return [task.result() for task in tasks]


# ✅ 正确：异步生成器
async def stream_results(items: List[str]):
    for item in items:
        result = await process_item(item)
        yield result


# ❌ 错误：阻塞调用在异步函数中
async def bad_example():
    data = requests.get(url)  # 阻塞！
    return data.json()
```

### 11.3 内存管理

```python
# ✅ 正确：使用生成器处理大文件
def process_large_file(filepath: str):
    with open(filepath) as f:
        for line in f:  # 逐行读取，不加载整个文件
            yield parse_line(line)


# ✅ 正确：及时释放资源
def process_data(data: List[str]):
    try:
        result = heavy_processing(data)
        return result
    finally:
        # 清理大型中间变量
        del data
```

---

## 12. 跨平台兼容性

### 12.1 路径处理

```python
from pathlib import Path
import os


# ✅ 正确：使用 pathlib
config_dir = Path.home() / ".handsome_agent"
config_dir.mkdir(parents=True, exist_ok=True)

# ✅ 正确：跨平台路径拼接
user_file = config_dir / "user_data.json"

# ✅ 正确：获取用户目录
home = Path.home()  # Windows: C:\Users\xxx, Linux: /home/xxx

# ❌ 错误：硬编码路径分隔符
config_path = "/home/user/.config"  # Windows 不兼容
```

### 12.2 系统检测

```python
import sys
import platform


# ✅ 正确：检测操作系统
IS_WINDOWS = platform.system() == "Windows"
IS_UNIX = not IS_WINDOWS


# ✅ 正确：平台特定代码
if IS_WINDOWS:
    import msvcrt  # Windows 特有
    def get_key():
        return msvcrt.getch()
else:
    import tty, termios  # Unix 特有
    def get_key():
        return get_char()


# ✅ 正确：使用 os.name
if os.name == "nt":  # Windows
    os.system("cls")
else:  # Unix
    os.system("clear")
```

### 12.3 命令执行

```python
import subprocess


# ✅ 正确：跨平台命令
result = subprocess.run(
    ["python", "script.py"],
    capture_output=True,
    text=True,
    timeout=30,
)

# ✅ 正确：Shell 命令（注意跨平台兼容）
if IS_WINDOWS:
    result = subprocess.run(
        ["cmd", "/c", "dir"],
        capture_output=True,
    )
else:
    result = subprocess.run(
        ["ls", "-la"],
        capture_output=True,
    )
```

---

## 13. Git 提交规范

### 13.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 13.2 类型标识

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构（不是新功能或修复） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具相关 |

### 13.3 提交示例

```
feat(session): 添加会话持久化功能

- 实现 FileSessionStore 支持 JSON 文件存储
- 添加 SessionManager 自动保存机制
- 支持会话历史裁剪

Closes #123

---

fix(llm): 修复 OpenAI provider 超时处理

之前超时异常未被正确捕获，导致进程崩溃。
现在添加了超时处理和重试逻辑。

---

docs(readme): 更新架构图和快速开始指南
```

### 13.4 分支命名

```
feature/session-persistence      # 功能分支
fix/intent-classification        # 修复分支
refactor/router-module           # 重构分支
docs/api-reference               # 文档分支
```

---

## 14. 代码审查清单

### 14.1 功能完整性

- [ ] 功能实现与需求一致
- [ ] 边界条件和错误情况已处理
- [ ] 单元测试覆盖新代码
- [ ] 集成测试通过（如适用）

### 14.2 代码质量

- [ ] 代码风格符合本规范
- [ ] 命名清晰、有意义
- [ ] 文档字符串完整
- [ ] 类型提示正确
- [ ] 无硬编码值

### 14.3 安全检查

- [ ] 用户输入已验证
- [ ] 无敏感信息泄露
- [ ] SQL/命令注入防护
- [ ] 权限检查正确

### 14.4 性能检查

- [ ] 无明显性能问题
- [ ] 资源正确释放
- [ ] 缓存使用合理
- [ ] 异步使用正确

### 14.5 可维护性

- [ ] 代码结构清晰
- [ ] 模块边界合理
- [ ] 易于扩展
- [ ] 无重复代码

---

## 附录 A：常用配置

### A.1 EditorConfig

```ini
# .editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100

[*.{yaml,yml}]
indent_style = space
indent_size = 2
```

### A.2 Pre-commit 配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        args: ["--line-length", "100"]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length", "100"]
```

---

## 附录 B：速查表

### B.1 文件头模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<Module Name>

<简短描述>

Features:
- 功能1
- 功能2
"""

__author__ = "Your Name"
__version__ = "1.0.0"
```

### B.2 类模板

```python
class MyClass:
    """
    类描述
    
    Attributes:
        attr1: 属性1描述
        attr2: 属性2描述
    """
    
    def __init__(self, param1: str, param2: int = 10):
        """
        初始化方法
        
        Args:
            param1: 参数1描述
            param2: 参数2描述，默认 10
        """
        self.attr1 = param1
        self.attr2 = param2
```

### B.3 异常处理模板

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.warning(f"Specific error handled: {e}")
    result = fallback()
except OtherError as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise MyCustomError("Operation failed") from e
finally:
    cleanup()
```

---

> 本规范基于 PEP 8、Google Python Style Guide 和行业最佳实践制定。
> 最后更新：2026-05-30
