# Handsome Agent 技术设计文档

**版本**: v1.0.0  
**最后更新**: 2026-06-09

---

> **提示**: 产品需求文档请查看 [产品设计书](../product/product-design.md) 和 [用户故事](../product/user-stories.md)

## 目录结构

```
docs/
├── product/                 # 产品需求文档
│   ├── product-design.md   # 产品设计书
│   └── user-stories.md     # 用户故事
│
├── design/                  # 技术设计文档
│   ├── README.md           # 本文件
│   ├── technical/          # 详细设计
│   │   └── detailed-design.md
│   ├── database/           # 数据库设计
│   │   └── database-design.md
│   ├── api/                # API 设计
│   │   └── api-spec.md
│   └── discovery/          # 自动发现设计
│       └── agent-discovery.md
│
├── test/                   # 测试文档
│   ├── test-plan.md       # 测试计划
│   └── test-cases.md     # 测试用例
│
├── ops/                   # 运维文档
│   └── ops-manual.md     # 运维手册
│
└── user/                  # 用户文档
    └── user-manual.md    # 用户手册
```

---

## 文档说明

| 文档 | 说明 | 主要读者 |
|------|------|----------|
| **技术设计文档 (docs/design/)** |
| [详细设计](technical/detailed-design.md) | 类图、时序图、状态机、核心流程 | 后端开发者 |
| [数据库设计](database/database-design.md) | 表结构、索引、数据模型 | 后端开发者 |
| [API 规范](api/api-spec.md) | REST API、错误码 | 全栈开发者 |
| [自动发现设计](discovery/agent-discovery.md) | Agent 自动发现机制 | 后端开发者 |
| **测试文档 (docs/test/)** |
| [测试计划](test/test-plan.md) | 测试范围、策略、资源、进度安排 | 测试工程师 |
| [测试用例](test/test-cases.md) | 功能测试用例、集成测试用例 | 测试工程师 |
| **运维文档 (docs/ops/)** |
| [运维手册](ops/ops-manual.md) | 部署、监控、备份、故障处理 | 运维工程师 |
| **用户文档 (docs/user/)** |
| [用户手册](user/user-manual.md) | 快速开始、操作指南、常见问题 | 最终用户 |

---

## 快速导航

### 详细设计
- [Agent 模块类图](technical/detailed-design.md#二核心模块类图) - Agent/ReAct/Tool 类图
- [对话处理时序图](technical/detailed-design.md#三时序图) - 对话执行流程
- [ReAct 循环状态机](technical/detailed-design.md#五状态机设计) - 循环状态定义

### 数据库设计
- [Schema 概览](database/database-design.md#三数据库-schema) - 所有数据表
- [会话表](database/database-design.md#31-会话表-sessions) - sessions 表
- [消息表](database/database-design.md#32-消息表-messages) - messages 表

### API 规范
- [对话 API](api/api-spec.md#四对话-api) - 对话接口
- [会话 API](api/api-spec.md#五会话-api) - 会话管理接口
- [错误码](api/api-spec.md#六错误码) - 所有错误码说明

### 自动发现
- [发现机制](discovery/agent-discovery.md#一概述) - 自动发现设计

### 测试文档
- [测试范围](test/test-plan.md#二测试范围) - 功能/非功能测试范围
- [测试策略](test/test-plan.md#三测试策略) - 测试分层、方法论
- [测试用例列表](test/test-cases.md#一概述) - 所有测试用例索引

### 运维文档
- [部署指南](ops/ops-manual.md#二部署指南) - Docker 部署
- [监控告警](ops/ops-manual.md#三监控告警) - 监控指标
- [故障处理](ops/ops-manual.md#五故障处理) - 常见问题排查

### 用户文档
- [快速开始](user/user-manual.md#一快速开始) - 系统访问、界面布局
- [CLI 使用](user/user-manual.md#二cli-使用) - 命令行工具使用

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本，完整文档体系 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09