---
alwaysApply: false
description: |
  测试规范 - 适用于以下场景自动加载：
  - 编写单元测试、集成测试或 E2E 测试
  - 修改测试目录结构或测试配置
  - 新增功能需要编写测试用例
  - Bug 修复需要编写复现测试
  - 运行测试或配置测试框架 (pytest/playwright)
  - 查看测试覆盖率要求

  如涉及测试用例编写、测试框架配置、覆盖率要求等，请查阅此规范。
---

# Copyright (c) 2026 AgentZoo/Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："测试规则生效！！！"

## 一、测试覆盖率要求

| 模块 | 最低覆盖率 |
|------|-----------|
| 核心引擎 (agent/) | 85% |
| 工具系统 (tools/) | 80% |
| 网关层 (gateway/) | 75% |
| 执行器 (executor/) | 75% |
| 整体 | 80% |

---

## 二、测试分层

### 2.1 单元测试 (Unit Tests)

- **位置**: `tests/unit/`
- **运行**: `pytest tests/unit/ -v`
- **要求**:
  - 每个函数/方法必须有测试用例
  - Mock 外部依赖
  - 目录结构与源码一一对应

### 2.2 集成测试 (Integration Tests)

- **位置**: `tests/integration/`
- **运行**: `pytest tests/integration/ -v`
- **要求**:
  - 测试模块间协作
  - 使用真实存储或轻量替代
  - 测试完整的工作流

### 2.3 E2E 测试

- **位置**: `tests/e2e/` 或前端目录
- **运行**: `playwright test`
- **覆盖**: 关键用户流程

---

## 三、测试命名约定

```python
def test_<模块>_<场景>_<预期结果>():
    """中文描述测试场景"""
```

---

## 四、测试组织结构

```
tests/
├── unit/                       # 单元测试
│   ├── conftest.py            # pytest 配置
│   ├── agent/
│   ├── tools/
│   ├── gateway/
│   └── common/
├── integration/                 # 集成测试
├── e2e/                        # E2E 测试
└── fixtures/                    # 测试数据
```

---

## 五、测试强制要求

> **强制要求**: 未写测试用例的代码不允许合并。

| 开发类型 | 必须条件 |
|----------|----------|
| 新增功能 | 编写对应的测试用例 |
| Bug修复 | 复现Bug的测试 + 修复验证测试 |
| 重构代码 | 测试覆盖率不能降低 |

---

## 六、CI 命令

```bash
# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行所有测试
pytest tests/ -v

# 覆盖率检查
pytest tests/ --cov=agent --cov=tools --cov=gateway --cov-report=html
```

---

## 七、最佳实践

1. **独立性**: 每个测试独立运行，不依赖其他测试
2. **可重复性**: 结果一致，重复运行结果相同
3. **快速执行**: 单元测试应快速完成 (<100ms)
4. **清晰命名**: 测试名描述场景和预期结果
5. **单一职责**: 每个测试只验证一个行为

---

*本文档版本: v2.0.0 | 最后更新: 2026-06-05*