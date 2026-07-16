# SPEC: CLI/TUI 入口优化

> 简化 TUI 进入方式，默认使用 TUI，提供 `--cli` 回退选项

## 1. 背景与目标

### 问题
当前进入 TUI 需要显式指定 `--textual` 标志，用户体验不够直观：
```bash
# 当前（需要记 flag）
python -m cli.main --textual

# 理想（直觉式）
python -m cli.main  # 默认进入 TUI
```

### 目标
- **默认进入 TUI**，无需任何标志
- 提供 `--cli` 选项保留传统 CLI 模式
- **最小改动原则**：保持现有架构不变

---

## 2. 详细设计

### 2.1 命令行接口变更

| 命令 | Before | After |
|------|--------|-------|
| 进入 TUI | `--textual` | 默认行为 |
| 进入 CLI | 默认行为 | `--cli` |
| 单次查询 | `-q` / `--query` | `-q` / `--query` |
| 设置向导 | `setup` | `setup` |

### 2.2 使用示例

```bash
# 默认进入 TUI（新版默认行为）
agentz

# 回到传统 CLI
agentz --cli

# 单次查询（保持不变）
agentz -q "你好"

# 设置向导（保持不变）
agentz setup
```

### 2.3 参数变更

#### 移除
- `--textual` - 不再需要，TUI 已是默认
- `--no-textual` - 不再需要

#### 新增
- `--cli` - 显式使用传统 CLI 界面

---

## 3. 实现细节

### 3.1 文件变更

| 文件 | 改动 |
|------|------|
| `cli/_parser.py` | 移除 `--textual`/`--no-textual`，新增 `--cli` |
| `cli/main.py` | 修改 `should_use_textual()` 默认返回 `True` |

### 3.2 核心逻辑

```python
def should_use_textual(args: argparse.Namespace) -> bool:
    """Determine if Textual UI should be used.

    默认使用 TUI，除非显式指定 --cli
    """
    # 1. 显式 --cli 使用传统 CLI
    if getattr(args, 'cli', False):
        return False

    # 2. 检查 TUI 可用性
    try:
        from tui import TEXTUAL_AVAILABLE
        if not TEXTUAL_AVAILABLE:
            return False
    except ImportError:
        return False

    # 3. 非 TTY 环境回退
    if not sys.stdout.isatty():
        return False

    # 4. 默认使用 TUI
    return True
```

### 3.3 帮助信息

```
$ agentz --help
usage: agentz [-h] [--version] [--cli] [-q PROMPT] [--setup] ...

Agent-Z - AI assistant with tool-calling capabilities

optional arguments:
  --version          Show version and exit
  --cli              使用传统 CLI 界面代替 TUI
  -q, --query        单次查询模式
  --interactive      Run in interactive mode
  ...

subcommands:
  setup              运行设置向导
  sessions           会话管理
  config             配置管理
  ...
```

---

## 4. 测试计划

### 4.1 功能测试

| 场景 | 预期结果 |
|------|----------|
| `agentz` | 启动 TUI |
| `agentz --cli` | 启动传统 CLI |
| `agentz -q "test"` | 单次查询（TUI） |
| `agentz --cli -q "test"` | 单次查询（CLI） |

### 4.2 兼容性测试

- 现有 `--query` 用法保持兼容
- 现有子命令（setup, config, sessions 等）保持兼容
- 配置文件保持兼容

---

## 5. 回滚计划

如需回滚：
1. 恢复 `--textual` 参数
2. 移除 `--cli` 参数
3. 恢复 `should_use_textual()` 默认返回 `False`

---

## 6. 版本与日期

- **版本**: 1.0.0
- **日期**: 2026-06-23
- **状态**: 实施中
