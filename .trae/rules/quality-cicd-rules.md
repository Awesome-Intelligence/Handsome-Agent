---
alwaysApply: false
description: |
  CI/CD 规范 - 适用于以下场景自动加载：
  - 配置 CI/CD 工作流
  - 提交代码、创建 Pull Request
  - 运行测试、构建项目
  - 配置代码检查工具

  如涉及提交检查、PR 合并、测试要求等，请查阅此规范。
---

# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："CI/CD 规则生效！！！"

## 一、提交前检查清单

- [ ] `black .` && `ruff check .`
- [ ] `mypy .`
- [ ] `pytest tests/unit/`
- [ ] 更新相关文档（如果有架构变更）

---

## 二、测试强制要求

> **强制要求**: 未写测试用例/未通过 CI 的代码不允许合并。

| 开发类型 | 必须条件 |
|----------|----------|
| 新增功能 | 编写测试用例 |
| Bug修复 | 复现 Bug 测试 + 修复验证测试 |
| 重构 | 测试覆盖率不能降低 |

---

## 三、PR 合并要求

- 至少 1 人 Code Review
- CI 所有检查通过
- 无未解决警告
- 无敏感信息硬编码

---

## 四、代码检查工具配置

### 4.1 Python

```bash
# 格式化
black .

# Linting
ruff check .

# 类型检查
mypy .
```

### 4.2 TypeScript

```bash
# 格式化
prettier --write .

# Linting
eslint .

# 类型检查
tsc --noEmit
```

---

## 五、测试分层

| 类型 | 位置 | 运行命令 |
|------|------|----------|
| 单元测试 | `tests/unit/` | `pytest tests/unit/` |
| 集成测试 | `tests/integration/` | `pytest tests/integration/` |
| E2E测试 | `tests/e2e/` | `playwright test` |

---

*本文档版本: v2.0.0 | 最后更新: 2026-06-05*