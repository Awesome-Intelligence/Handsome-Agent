---
alwaysApply: true
description: |
  Handsome Agent 核心编码规范 - 每次代码开发必须参考：
  - 规则文件架构规范
  - 子规范引用索引
  - 强制约束速查
  - 自检清单
---

# Copyright (c) 2026 Agent-Z Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

# Handsome Agent 开发规范

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

本文档定义 Handsome Agent 项目开发规范，每次写代码前必读。

---

## ⭐ 强制约束

| 约束 | 违规表现 |
|------|---------|
| 禁止意图理解硬编码 | `if "关键词" in text` |
| 禁止敏感信息硬编码 | `api_key = "sk-xxx"` |
| 禁止路径分隔符硬编码 | `path.replace("/", "\\")` |
| 禁止文本硬编码 | `return "你好"` |
| 必须使用统一日志 | 必须用 `common.logging_manager` |
| common/ 只能放基础设施代码 | |

---

## ⭐⭐ 开发流程顺序

> 复杂任务可通过 `.trae/todo.md` 记录分阶段目标，逐步完成。

### 功能代码修改
1. 编写功能代码
2. 更新对应测试用例
3. 运行测试用例验证
4. 更新对应文档

### 测试用例修改
1. 修改测试用例
2. 立即运行测试验证

### 文档修改
1. 修改文档
2. 刷新关联的相关文档

---

## 一、规则分类索引

### dev-* 开发规范
| 规则 | 说明 |
|------|------|
| [dev-python](dev-python-rules.md) | Python 代码风格 |
| [dev-naming](dev-naming-rules.md) | 命名规范 |
| [dev-i18n](dev-i18n-rules.md) | 多语言国际化 (i18n) 规范 |

### doc-* 文档规范
| 规则 | 说明 |
|------|------|
| [doc](doc-rules.md) | 文档与注释规范 |
| [doc-license](doc-license-rules.md) | 开源许可证规范 |

### quality-* 质量规范
| 规则 | 说明 |
|------|------|
| [quality-cicd](quality-cicd-rules.md) | CI/CD 规范 |
| [quality-security](quality-security-rules.md) | 安全规范 |
| [quality-logging](quality-logging-rules.md) | 日志规范 |
| [quality-test](quality-test-rules.md) | 测试规范 |

### project-* 项目规范
| 规则 | 说明 |
|------|------|
| [project-architecture](project-architecture-rules.md) | 架构与目录结构 |

---

## 二、层-子层速查

详见：[project-architecture-rules.md](project-architecture-rules.md) - 层级定义（包含完整 Emoji 速查表）

---

## 三、参考项目

> 当需要参考 Hermes 或 OpenClaw 的实现时，查看以下项目代码
>

| 项目 | 环境变量 |
|------|----------|
| Hermes  | E:/hermes-agent-study/ |
| OpenClaw  | E:/openclaw-study |
| CodeWhale  | E:/CodeWhale-study |
| frogmouth  | E:/frogmouth |
| jiuwenswarm  | E:/jiuwenswarm-study |

---

## 四、意图理解规则

**必须使用 LLM** 理解意图，禁止硬编码关键词/正则。

**降级链**：`LLM → 关键词 → 规则 → 默认值`

---

## 五、自检清单

- [ ] 无意图理解硬编码关键词
- [ ] 无敏感信息硬编码（用环境变量）
- [ ] 路径用 `pathlib.Path`
- [ ] 日志使用统一日志系统
- [ ] 无用户可见文本硬编码（用 i18n）

---

## 六、规则架构约束

> 新增子规则时必须遵循以下规范

### 5.1 四层架构

```
主规则 (rules.md) ─── 索引 + 架构约束
    │
    └── 子规则 (*-rules.md) ─── 实质内容
```

### 5.2 前缀分组

| 前缀 | 类别 |
|------|------|
| `dev-*` | 开发规范 |
| `doc-*` | 文档规范 |
| `quality-*` | 质量规范 |
| `project-*` | 项目规范 |

### 5.3 Front Matter 必须字段

```yaml
---
alwaysApply: false  # 子规则默认 false，主规则使用 true
description: 描述（用于触发加载判断）
---
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `alwaysApply` | 是 | `true`=始终加载，`false`=按需加载 |
| `description` | 是 | 描述触发场景，AI 根据此决定是否加载 |

### 5.4 新增子规则检查清单

- [ ] 文件名符合 `*-rules.md` 格式
- [ ] 包含正确的 Front Matter
- [ ] `alwaysApply` 值合理（大多数为 `false`）
- [ ] `description` 明确触发场景
- [ ] 在主规则 `rules.md` 中添加链接
- [ ] 在 `agent_requestable_workspace_rules` 中注册（如果需要）

---

## 七、工具配置速查

| 工具 | 用途 | 命令 |
|------|------|------|
| Black | 格式化 | `black .` |
| Ruff | Linting | `ruff check .` |
| Pylint | 代码检查 | `pylint your_module.py` |
| MyPy | 类型检查 | `mypy .` |
| Pytest | 测试 | `pytest tests/ -v` |
| Prettier | 前端格式化 | `prettier --write .` |
| ESLint | 前端 Linting | `eslint .` |
| TSC | TypeScript 检查 | `tsc --noEmit` |

---

*本文档版本: v8.0.0 | 最后更新: 2026-06-05*