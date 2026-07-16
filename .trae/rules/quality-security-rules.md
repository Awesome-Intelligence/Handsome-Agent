---
alwaysApply: false
description: |
  安全规范 - 适用于以下场景自动加载：
  - 编写涉及用户认证、数据存储的代码
  - 配置环境变量、密钥管理
  - 审查代码安全性
  - 处理外部输入、API 请求
  - 文件操作、命令执行

  如涉及安全编码、密钥管理、输入验证等，请查阅此规范。
---

# Copyright (c) 2026 Agent-Z Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："安全规则生效！！！"

## 一、核心原则：安全零信任

- **输入验证**：白名单机制，禁止信任用户输入
- **敏感信息**：从环境变量获取，日志中脱敏
- **路径安全**：防止路径遍历攻击
- **命令执行**：白名单 + 危险模式检测

---

## 二、密钥与敏感信息

### 2.1 禁止硬编码

```python
# ✗ 禁止: 硬编码密钥
API_KEY = "sk-1234567890abcdef"

# ✓ 正确: 从环境变量读取
import os
API_KEY = os.environ.get("API_KEY")
```

### 2.2 必须加入 .gitignore

```
.env
*.log
secrets/
credentials.json
```

---

## 三、输入验证

### 3.1 白名单验证

```python
# ✓ 正确：白名单验证
ALLOWED_COMMANDS = {"ls", "pwd", "cd", "cat"}
if cmd not in ALLOWED_COMMANDS:
    raise ValueError(f"Command not allowed: {cmd}")
```

### 3.2 类型约束

```python
# ✓ 正确: 显式类型注解 + 类型检查
def process_items(items: Sequence[str | int]) -> dict[str, Any]:
    for item in items:
        if not isinstance(item, (str, int)):
            raise TypeError(f"Expected str or int, got {type(item)}")
```

---

## 四、路径安全

```python
# ✓ 正确：使用 pathlib + 遍历检测
from pathlib import Path

def safe_read(path: Path, base_dir: Path) -> str:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(base_dir):
        raise ValueError("Path traversal detected")
    return resolved.read_text()
```

---

## 五、命令执行安全

```python
# ✓ 正确：使用 subprocess + 白名单
import subprocess

ALLOWED_COMMANDS = {"ls", "pwd", "cat", "grep", "find"}

def safe_execute(command: str, args: list[str]) -> str:
    if command not in ALLOWED_COMMANDS:
        raise PermissionError(f"Command not allowed: {command}")

    # 使用 shell=False 避免 shell 注入
    result = subprocess.run(
        [command] + args,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout

# ✗ 禁止：shell=True 容易注入
subprocess.run(f"ls {user_input}", shell=True)  # 危险！
```

---

## 六、安全检查清单

- [ ] 无敏感信息硬编码
- [ ] 用户输入已验证
- [ ] 路径用 pathlib
- [ ] 命令执行有白名单
- [ ] 日志中敏感信息脱敏
- [ ] .env 已加入 .gitignore
- [ ] 使用 subprocess 时 shell=False

---

*本文档版本: v2.0.0 | 最后更新: 2026-06-05*