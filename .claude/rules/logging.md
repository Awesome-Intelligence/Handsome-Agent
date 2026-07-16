# 日志规范

> 适用于：添加日志记录点、配置日志系统、排查问题、性能监控

---

## 一、核心原则

**必须使用统一日志系统**：`common.logging_manager`

```python
# ✅ 正确：使用统一日志
from common.logging_manager import get_decision_logger

# 无子层
self.logger = get_decision_logger(self.__class__.__name__)

# 有子层
self.logger = get_decision_logger(self.__class__.__name__, sublayer="memory")
```

**禁止**：
- ❌ `logging.getLogger(__name__)`
- ❌ `print()` 用于生产环境

---

## 二、日志级别

| 级别 | 场景 | 示例 |
|------|------|----------|
| DEBUG | 调试信息 | "进入 execute_workflow 方法" |
| INFO | 正常运行 | "工作流执行成功" |
| WARNING | 警告但可继续 | "配置缺失，使用默认值" |
| ERROR | 可恢复错误 | "工具调用失败，重试中" |
| CRITICAL | 严重错误 | "数据库连接完全失败" |

---

## 三、日志格式

```
INFO - [🚪MainLayer] - [/💾SublayerName] - (ModuleName) message
```

**示例**：
```
INFO - [🧠Decision] - [/💾Memory] - (SessionManager) 会话创建成功
INFO - [🏃Execution] - [/🐚ShellExec] - (ShellExecutor) 命令执行完成
INFO - [🚪Access] - [/💬CLI] - (MainCLI) 收到用户输入
```

---

## 四、模块-层级映射

| 目录 | Logger 函数 | Sublayer |
|------|-------------|----------|
| `agent/` | `get_decision_logger()` | 根据子模块 |
| `executor/` | `get_execution_logger()` | 根据类型 |
| `gateway/`, `cli/` | `get_access_logger()` | 根据模块 |
| `common/` | `get_system_logger()` | 无 |

---

## 五、敏感信息脱敏

| 字段类型 | 脱敏方式 |
|---------|---------|
| 密码 | `****` |
| API Key | 前4后4：`sk-xx...xxxx` |
| 邮箱 | `u***@example.com` |

```python
# ✅ 禁止：记录敏感信息
logger.info(f"用户登录成功: {password}")  # 禁止！
```

---

## 六、日志输出配置

- **开发环境**: DEBUG 级别，输出到控制台
- **生产环境**: INFO 级别，输出到文件
- **日志文件**: 按天切割，保留30天
- **日志路径**: `logs/Agent-Z-{date}.log`

---

## 七、禁止的模式

```python
# ❌ 禁止：使用标准 logging.getLogger
logger = logging.getLogger(__name__)

# ❌ 禁止：含糊消息
logger.info("Done")
logger.error("Error")
```