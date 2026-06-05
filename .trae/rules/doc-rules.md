---
alwaysApply: false
description: |
  文档规范 - 适用于以下场景自动加载：
  - 编写或更新项目文档 (README, CHANGELOG)
  - 编写模块文档、API 文档
  - 架构变更或技术调整时更新文档
  - 审查代码注释规范性

  如涉及文档编写要求、注释规范等，请查阅此规范。
---

# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："文档规则生效！！！"

---

## 一、文档编写要求

| 文档 | 必须包含 | 更新时机 |
|------|---------|----------|
| README.md | 简介、快速开始、联系方式 | 每次发布 |
| API文档 | 端点、参数、返回值示例 | 接口变更时 |
| 模块文档 | 设计思路、核心逻辑、依赖 | 新增模块时 |
| CHANGELOG | 版本、变更、升级指南 | 每次发布 |
| 架构文档 | 系统设计、模块关系、技术选型 | 架构或技术调整时 |

---

## 二、架构变更同步要求

> **强制要求**: 涉及架构或技术调整的变更必须同步更新文档，未更新不允许合并。

| 变更类型 | 必须更新 | 示例 |
|----------|----------|------|
| 新增模块 | 架构文档、模块文档 | 添加 Agent 调度器模块 |
| 技术栈变更 | 架构文档、README | SQLite → PostgreSQL |
| API接口变更 | API文档 | REST → MCP |

---

## 三、注释规范

### 3.1 必须添加注释

- 复杂算法、非显而易见逻辑
- 外部系统交互
- 特殊配置说明

### 3.2 Python Docstring 格式 (Google Style)

```python
def execute_workflow(workflow_id: str, context: dict) -> ExecutionResult:
    """执行工作流并返回结果。

    Args:
        workflow_id: 工作流唯一标识
        context: 执行上下文数据

    Returns:
        ExecutionResult: 包含执行状态和输出结果

    Raises:
        WorkflowNotFoundError: 工作流不存在时抛出
    """
    ...
```

### 3.3 类文档

```python
class SessionManager:
    """会话管理器。

    负责管理用户会话的创建、存储和检索。

    Attributes:
        max_sessions: 最大会话数量
        session_timeout: 会话超时时间（秒）
    """
```

---

## 四、Git 提交信息规范

### 4.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.2 Type 类型

| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构 |
| test | 测试相关 |
| chore | 构建/工具相关 |

### 4.3 示例

```
feat(session): 添加会话超时自动清理功能

- 添加 SessionManager.cleanup_expired() 方法
- 添加定时清理任务

Closes #123
```

---

## 五、TODO 注释规范

```python
# ✅ 正确: 必须包含 issue 链接
# TODO: https://github.com/org/repo/issues/123 - 修复此处的内存泄漏问题

# ✗ 禁止
# TODO: 修复这个bug
# TODO: @username - 做某事
```

---

*本文档版本: v2.0.0 | 最后更新: 2026-06-05*