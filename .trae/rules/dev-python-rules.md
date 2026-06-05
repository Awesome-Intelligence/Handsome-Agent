---
alwaysApply: false
description: |
  Python 代码风格规范 - 适用于以下场景自动加载：
  - 编写或修改 Python 代码
  - 代码审查、格式化、lint 检查
  - 配置代码检查工具 (black, ruff, pylint, mypy)
  - 类型注解、文档字符串编写

  如涉及 Python 代码风格、类型注解、导入规范等，请查阅此规范。
---

# Copyright (c) 2026 AgentZoo/Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

> **参考规范**: [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

被加载时，输出："Python 代码风格规则生效！！！"

---

## 一、基本规范

### 1.1 Lint

- 使用 `pylint` 检查代码
- 压制警告示例：`# pylint: disable=invalid-name`
- 未使用参数：删除变量并加注释说明

### 1.2 导入 (Imports)

```python
# ✅ 正确：按模块导入
import os
import sys
from typing import Any, NewType

# ✅ 使用别名避免冲突
from mymodule import utils as my_utils

# ❌ 错误：一行多个
import os, sys
```

**导入顺序**：
1. `from __future__ import` (future imports)
2. 标准库
3. 第三方库
4. 项目内部导入

### 1.3 异常 (Exceptions)

```python
# ✅ 正确：使用内置异常类
raise ValueError(f"Invalid value: {value}")

# ❌ 错误：禁止使用 assert 验证业务逻辑
assert user is not None  # ❌

# ✅ 异常命名以 Error 结尾
class ValidationError(Exception):
    """Raised when validation fails."""
```

**禁止**：
- `except:` 捕获所有异常
- `except Exception` 除非重新抛出

### 1.4 包和模块

```python
# ✅ 正确：使用完整包路径
from doctor.who import jodie  # 在 doctor/who/ 目录下

# ❌ 错误：相对导入
from . import module
```

---

## 二、风格规则

### 2.1 分号

- **禁止**在一行末尾加分号
- **禁止**用分号连接两个语句

### 2.2 行长度

- 最大行长：**80 字符**
- 例外：URL、路径、长字符串常量、pylint 压制注释
- 使用括号实现隐式换行，**禁止**使用反斜杠 `\`

```python
# ✅ 正确
foo_bar(
    width, height, color='black',
    design=None, x='foo'
)

# ❌ 错误
foo_bar(width, height, color='black', \
    design=None, x='foo')
```

### 2.3 缩进

- **4 空格**缩进
- **禁止**使用 Tab
- 函数参数换行时与 `(` 对齐

### 2.4 空行

- 顶级定义之间：**2 个空行**
- 方法定义之间：**1 个空行**
- 函数内部：按需使用空行分隔逻辑

### 2.5 字符串

```python
# ✅ 使用 f-string 或 format
x = f'name: {name}; score: {n}'
x = 'name: {}; score: {}'.format(name, n)

# ❌ 避免在循环中用 += 拼接
employee_table = '<table>'
for last_name, first_name in employee_list:
    employee_table += '<tr>...'  # ❌ 性能差
```

### 2.6 TODO 注释

```python
# ✅ 正确：包含链接
# TODO: https://example.com/issue - Describe the task

# ❌ 错误：不要包含用户名
# TODO: @username - Fix this
```

---

## 三、命名约定

### 3.1 通用规则

| 类型 | 规则 | 示例 |
|------|------|------|
| 模块 | `snake_case.py` | `session_manager.py` |
| 类 | `CapWords` | `SessionManager` |
| 异常 | `CapWordsError` | `ValidationError` |
| 函数/变量 | `snake_case` | `get_session()` |
| 常量 | `UPPER_SNAKE` | `MAX_RETRY_COUNT` |
| 私有成员 | `_prefix` | `_private_method()` |
| 类型别名 | `CapWords` | `LossAndGradient` |

### 3.2 命名禁止

- ❌ 单字符名称（除 `i, j, k` 循环变量，`e` 异常，`f` 文件句柄）
- ❌ 包含类型信息的名称如 `id_to_name_dict`
- ❌ `__dunder__` 名称（保留给 Python）
- ❌ 中划线 `-` 在模块名中

---

## 四、类型注解

### 4.1 基本规则

```python
# ✅ 函数参数和返回值
def func(a: int) -> list[int]:
    ...

# ✅ 使用 None 而不是 Optional
def modern_or_union(a: str | None) -> str:
    ...
```

### 4.2 类型别名

```python
from typing import TypeAlias

# 公开类型别名用 CapWords
ComplexTFMap: TypeAlias = Mapping[str, tuple[float, float]]

# 内部类型别名用 _ 前缀
_LossAndGradient: TypeAlias = tuple[tf.Tensor, tf.Tensor]
```

---

## 五、禁止的硬编码模式 ⭐

| 违规类型 | 检测模式 | 正确做法 |
|---------|---------|---------|
| 意图理解硬编码 | `if "关键词" in text` | 使用 LLM 判断 |
| 敏感信息硬编码 | `password = "xxx"` | 从环境变量读取 |
| 路径分隔符硬编码 | `path.replace("/", "\\")` | 使用 `pathlib.Path` |
| 相对导入 | `from . import x` | 使用完整包路径 |
| 捕获所有异常 | `except:` | 指定具体异常类型 |

---

## 六、自检清单

- [ ] 代码通过 pylint 检查
- [ ] 导入顺序正确（future → 标准库 → 第三方 → 项目）
- [ ] 行长不超过 80 字符
- [ ] 使用 4 空格缩进
- [ ] 命名符合规范（模块 snake_case、类 CapWords）
- [ ] 类型注解完整（公开 API）
- [ ] 无敏感信息硬编码
- [ ] 无意图理解硬编码
- [ ] 路径使用 pathlib.Path

---

*本文档版本: v3.0.0 | 最后更新: 2026-06-05*