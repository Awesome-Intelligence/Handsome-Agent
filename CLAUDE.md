# Agent-Z - Claude Code 开发规范

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

---

## ⭐ 核心约束（始终生效）

以下约束**绝对禁止**违反，违规代码不允许合并：

| 约束 | 违规示例 | 正确做法 |
|------|---------|---------|
| 禁止意图理解硬编码 | `if "关键词" in text` | 使用 LLM 判断 |
| 禁止敏感信息硬编码 | `api_key = "sk-xxx"` | 从环境变量读取 |
| 禁止路径分隔符硬编码 | `path.replace("/", "\\")` | 使用 `pathlib.Path` |
| 禁止文本硬编码 | `return "你好"` | 使用 `i18n.t()` |
| 禁止使用标准 logging | `logging.getLogger(__name__)` | 使用 `common.logging_manager` |
| 禁止捕获所有异常 | `except:` | 指定具体异常类型 |

**自检**: 每次提交前确认无以上违规。

---

## 📚 规则索引

需要时查阅对应规则文件：

| 规则 | 文件 | 适用场景 |
|------|------|---------|
| Python 代码风格 | [.claude/rules/python.md](.claude/rules/python.md) | 编写/修改 Python 代码、lint、格式化 |
| 命名规范 | [.claude/rules/naming.md](.claude/rules/naming.md) | 创建模块/类/函数/变量、数据库命名 |
| 日志规范 | [.claude/rules/logging.md](.claude/rules/logging.md) | 添加日志记录点、配置日志系统 |
| 安全规范 | [.claude/rules/security.md](.claude/rules/security.md) | 认证、密钥管理、输入验证、命令执行 |
| 国际化 | [.claude/rules/i18n.md](.claude/rules/i18n.md) | 用户界面文本、多语言支持 |
| 测试规范 | [.claude/rules/testing.md](.claude/rules/testing.md) | 编写测试用例、测试配置 |
| 文档规范 | [.claude/rules/docs.md](.claude/rules/docs.md) | 文档编写、注释规范、Git 提交格式 |
| CI/CD | [.claude/rules/cicd.md](.claude/rules/cicd.md) | 提交检查、PR 合并要求 |
| 架构规范 | [.claude/rules/architecture.md](.claude/rules/architecture.md) | 架构设计、目录结构、层级映射 |

---

## 🏗️ 快速参考

### 目录结构与层级

```
agent/        🧠 Decision  - Agent 核心
tools/        🏃 Execution - 工具定义
skills/       🧠 Decision  - 技能系统
gateway/      🚪 Access   - HTTP 网关
executor/     🏃 Execution - 执行器
common/       🔧 System   - 基础设施（禁止放其他层代码）
cli/          🚪 Access   - 命令行入口
tui/          🚪 Access   - Textual TUI 界面
tests/        🧪 Test     - 测试套件
```

### 日志格式

```
INFO - [🚪MainLayer] - [/💾SublayerName] - (ModuleName) message
```

### 提交前检查

```bash
black . && ruff check . && mypy . && pytest tests/unit/
```

---

**详情**: 参见各规则文件