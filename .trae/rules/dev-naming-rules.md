---
alwaysApply: false
description: |
  命名规范 - 适用于以下场景自动加载：
  - 创建新模块、类、函数、变量
  - 命名审查、代码重构
  - 定义数据库表/集合、配置文件
  - 组件命名、前端代码命名

  如涉及命名一致性、命名风格等，请查阅此规范。
---

# Copyright (c) 2026 AgentZoo/Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："命名规则生效！！！"

> **参考规范**: [Google Python Style Guide - Naming](https://google.github.io/styleguide/pyguide.html#s3.16-naming)

---

## 一、命名原则

### 1.1 核心原则

- **描述性**: 名称应具有描述性，表达意图
- **简洁**: 避免不必要的缩写
- **一致**: 整个代码库保持一致的命名风格
- **符合惯例**: 遵循各语言的命名约定

### 1.2 允许的单字符命名

| 场景 | 变量 | 示例 |
|------|------|------|
| 计数器/迭代器 | `i`, `j`, `k`, `v` | `for i in range(n)` |
| 异常捕获 | `e` | `except Exception as e:` |
| 文件句柄 | `f` | `with open(f) as f:` |
| 类型变量（私有） | `_T`, `_P` | `_T = TypeVar("_T")` |

---

## 二、Python 命名规范

### 2.1 命名风格总览

| 类型 | 公共 | 内部/私有 |
|------|------|----------|
| 模块/包 | `lower_with_under` | `_lower_with_under` |
| 类 | `CapWords` | `_CapWords` |
| 异常 | `CapWords` | - |
| 函数 | `lower_with_under()` | `_lower_with_under()` |
| 全局/类常量 | `CAPS_WITH_UNDER` | `_CAPS_WITH_UNDER` |
| 实例变量 | `lower_with_under` | `_lower_with_under` |
| 方法名 | `lower_with_under()` | `_lower_with_under()` |

### 2.2 类名

```python
# 类名: CapWords (PascalCase)
class SessionManager: ...
class WorkflowExecutor: ...
class HTTPError: ...  # 异常也用 CapWords
```

### 2.3 函数与方法

```python
# 函数名: lower_with_under (snake_case)
def execute_workflow(): ...
def get_session_by_id(): ...
def _internal_helper(): ...  # 私有函数
```

### 2.4 常量

```python
# 常量: CAPS_WITH_UNDER (全大写+下划线)
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
```

---

## 三、TypeScript/JavaScript 命名规范

### 3.1 命名风格总览

| 类型 | 规则 | 示例 |
|------|------|------|
| 变量/函数 | camelCase | `userName`, `getUserInfo()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 类/接口/类型 | PascalCase | `UserProfile`, `WorkflowNode` |
| 组件 | PascalCase | `WorkflowCanvas` |

### 3.2 组件

```tsx
// 组件名: PascalCase，文件名与组件名一致
export function WorkflowCanvas() {
  return <div>...</div>
}
```

---

## 四、数据库命名

| 对象 | 规则 | 示例 |
|------|------|------|
| 表名 | snake_case 复数 | `workflow_nodes` |
| 列名 | snake_case | `created_at`, `user_id` |
| 主键 | `id` | `id` |
| 外键 | `表名单数_id` | `workflow_id` |
| 索引名 | `idx_<表>_<列>` | `idx_workflows_user_id` |

---

## 五、Handsome Agent 专属命名

### 5.1 模块目录命名

| 目录 | 命名规则 | 示例 |
|------|----------|------|
| 核心模块 | snake_case | `session_manager.py` |
| 工具模块 | snake_case | `file_reader.py` |
| 网关模块 | snake_case | `http_handler.py` |

### 5.2 日志命名

```python
from common.logging_manager import get_decision_logger

# 无子层
logger = get_decision_logger(__name__)

# 有子层
logger = get_decision_logger(__name__, sublayer="memory")
```

---

*本文档版本: v3.0.0 | 最后更新: 2026-06-05*