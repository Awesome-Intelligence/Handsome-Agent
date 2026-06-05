---
alwaysApply: false
description: |
  日志规范 - 适用于以下场景自动加载：
  - 添加日志记录点
  - 配置日志系统
  - 排查问题、分析日志
  - 性能监控
  - 自定义日志处理器

  如涉及日志级别、格式、记录要求等，请查阅此规范。
---

# Copyright (c) 2026 AgentZoo/Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："日志规则生效！！！"

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
|------|------|------|
| DEBUG | 调试信息 | "进入 execute_workflow 方法" |
| INFO | 正常运行 | "工作流执行成功" |
| WARNING | 警告但可继续 | "配置缺失，使用默认值" |
| ERROR | 可恢复错误 | "工具调用失败，重试中" |
| CRITICAL | 严重错误 | "数据库连接完全失败" |

---

## 三、日志格式

```
[时间戳] [级别] [模块名] [请求ID] - 消息
2026-06-04 10:30:00 INFO workflow_engine req_abc123 - 工作流执行完成
```

### Handsome Agent 专属格式

详见：[project-architecture-rules.md](project-architecture-rules.md) - 层级 Emoji 速查表

```
INFO - [🚪MainLayer] - [/💾SublayerName] - (ModuleName) message
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
- **日志路径**: `logs/handsome-agent-{date}.log`

---

## 七、禁止的模式

```python
# ❌ 禁止：使用标准 logging.getLogger
logger = logging.getLogger(__name__)

# ❌ 禁止：含糊消息
logger.info("Done")
logger.error("Error")

# ❌ 禁止：日志中出现中文（生产环境）
logger.info("处理完成")
```

---

*本文档版本: v3.0.0 | 最后更新: 2026-06-05*