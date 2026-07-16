# 📚 Documentation Index - Agent-Z 文档索引

> 项目文档目录结构

---

## 📁 文档结构

```
docs/
├── index.md                    # 本文档索引
├── CHANGELOG.md               # 变更日志
│
├── architecture/               # 架构文档
│   ├── architecture.md         # 三层架构设计（Hermes-Brain + OpenClaw-Body）
│   ├── overview.md             # 架构概览（轻量版）
│   ├── restructure-plan.md     # 目录结构重构计划 ⭐
│   ├── llm-tool-selection.md   # LLM 驱动的工具选择（已废弃，保留参考）
│   └── compliance-report.md    # 架构合规性分析报告
│
├── guides/                      # 使用指南
│   ├── quick-start.md           # 5分钟快速上手
│   ├── quick-reference.md       # 命令/API 速查
│   ├── system-design.md         # 系统设计文档
│   ├── migration-guide.md      # 移除意图识别层迁移指南（已废弃）
│   ├── api-reference.md        # 完整 API 文档
│   ├── deployment.md            # Docker/云平台部署指南
│   ├── mobile-integration.md    # iOS/Android/Flutter 集成
│   └── contributing.md          # 贡献指南
│
├── references/                  # 参考资料
│   ├── llm-integration.md       # LLM 集成模块（25+ 提供商）
│   ├── state-of-art-research.md # 业界 Agent 系统架构研究
│   ├── capabilities-overview.md # Agent 能力完整清单
│   ├── acknowledgements.md      # 参考项目与致谢
│   └── feature-verification.md  # 功能验证报告
│
├── development/                # 开发文档
│   ├── testing-summary.md       # 测试覆盖报告（277 测试，85%+ 覆盖率）
│   └── intent-classification-config.md  # 意图识别配置（**已废弃**，仅供参考）
│
├── modules/                     # 模块文档
│   ├── agent/                   # Agent 模块（核心）
│   │   └── README.md
│   ├── skills/                   # 技能系统
│   │   └── README.md
│   ├── gateway/                 # Gateway 模块
│   │   └── README.md
│   ├── executor/                # 执行层
│   │   └── README.md
│   ├── tools/                   # 工具定义
│   │   └── README.md
│   ├── common/                  # 基础设施
│   │   └── README.md
│   ├── cli/                     # CLI 模块
│   │   └── README.md
│   └── tests/                   # 测试文档
│       └── README.md
│   └── context-compression.md    # 上下文压缩模块 ⭐
│
├── design/                      # 技术设计文档 ⭐
│   ├── README.md                # 技术设计索引
│   ├── technical/
│   │   └── detailed-design.md   # 详细设计（类图、时序图、状态机）
│   ├── database/
│   │   └── database-design.md   # 数据库设计
│   ├── api/
│   │   └── api-spec.md          # API 规范
│   └── discovery/
│       └── agent-discovery.md    # Agent 发现机制
│
├── product/                     # 产品文档 ⭐
│   ├── product-design.md        # 产品设计书
│   └── user-stories.md          # 用户故事
│
├── test/                        # 测试文档 ⭐
│   ├── test-plan.md             # 测试计划
│   └── test-cases.md            # 测试用例
│
├── user/                        # 用户手册 ⭐
│   └── user-manual.md           # 用户使用手册
│
└── ops/                         # 运维手册 ⭐
    └── ops-manual.md            # 部署与运维指南
```

---

## 🚀 快速导航

### 新手入门
| 文档 | 内容 | 预计时间 |
|------|------|----------|
| [Quick Start](guides/quick-start.md) | 5分钟快速上手 | 5min |
| [System Design](guides/system-design.md) | 系统设计概览 | 10min |
| [User Manual](user/user-manual.md) | 用户使用手册 | 15min |

### 核心架构
| 文档 | 内容 |
|------|------|
| [Architecture](architecture/architecture.md) | 三层架构设计（Hermes-Brain + OpenClaw-Body） |
| [Architecture Overview](architecture/overview.md) | 架构概览 |
| [Restructure Plan](architecture/restructure-plan.md) | 目录结构重构计划 |
| [LLM Tool Selection](architecture/llm-tool-selection.md) | LLM 驱动的工具选择（已废弃） |

### 技术设计
| 文档 | 内容 |
|------|------|
| [Design Index](design/README.md) | 技术设计文档索引 |
| [Detailed Design](design/technical/detailed-design.md) | 详细设计（类图、时序图、状态机） |
| [Database Design](design/database/database-design.md) | 数据库设计 |
| [API Spec](design/api/api-spec.md) | API 规范 |
| [Agent Discovery](design/discovery/agent-discovery.md) | Agent 发现机制 |

### 产品文档
| 文档 | 内容 |
|------|------|
| [Product Design](product/product-design.md) | 产品设计书 |
| [User Stories](product/user-stories.md) | 用户故事与用例 |

### 测试文档
| 文档 | 内容 |
|------|------|
| [Test Plan](test/test-plan.md) | 测试计划 |
| [Test Cases](test/test-cases.md) | 测试用例 |
| [Testing Summary](development/testing-summary.md) | 测试覆盖报告 |

### 运维文档
| 文档 | 内容 |
|------|------|
| [Ops Manual](ops/ops-manual.md) | 部署与运维指南 |

### 模块文档
| 模块 | 文档 |
|------|------|
| [Agent](modules/agent/README.md) | Agent 核心（AgentLoop, Curator, LLM） |
| [Skills](modules/skills/README.md) | 技能系统（匹配、加载、生命周期） |
| [Gateway](modules/gateway/README.md) | 网关（认证、限流） |
| [Executor](modules/executor/README.md) | 执行层（Shell/Docker） |
| [Tools](modules/tools/README.md) | 工具定义 |
| [Common](modules/common/README.md) | 基础设施（配置、日志、异常） |
| [CLI](modules/cli/README.md) | 命令行界面 |
| [Tests](modules/tests/README.md) | 测试文档 |

### 开发参考
| 文档 | 内容 |
|------|------|
| [Quick Reference](guides/quick-reference.md) | 命令、API、最佳实践快速参考 |
| [API Reference](guides/api-reference.md) | 完整 API 文档 |
| [Contributing](guides/contributing.md) | 贡献指南 |

### 参考资料
| 文档 | 内容 |
|------|------|
| [LLM Integration](references/llm-integration.md) | LLM 集成模块（25+ 提供商） |
| [State of Art](references/state-of-art-research.md) | 业界最佳实践 |
| [Capabilities](references/capabilities-overview.md) | 能力清单 |
| [Acknowledgements](references/acknowledgements.md) | 参考来源与致谢 |

---

## 💡 快速命令

```bash
# CLI 交互
python -m cli.main chat

# Gateway
python -m gateway --no-auth

# 带认证
python -m gateway --api-key KEY --rate-limit 100

# 运行测试
python -m pytest tests/unit/ -v

# 代码覆盖率
python -m pytest tests/unit/ --cov=. --cov-report=term-missing
```

---

## 🔗 相关文档

- [项目 README](../README.md) - 项目概览
- [TODO.md](../TODO.md) - 开发计划
- [编码规范](../.trae/rules/rule.md) - 开发规范文档

---

**最后更新**: 2026-06-09
**版本**: v3.1.0 - 新增产品/技术设计/测试/运维文档