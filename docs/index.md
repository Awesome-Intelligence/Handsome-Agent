# 📚 Documentation Index - Handsome Agent 文档索引

> 项目文档目录结构

---

## 📁 文档结构

```
docs/
├── index.py                    # 本文档索引
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
│   ├── migration-guide.md      # 移除意图识别层迁移指南
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
└── modules/                     # 模块文档
    ├── core/                    # 核心模块
    │   └── README.md
    ├── agent/                   # Agent 模块
    │   └── README.md
    ├── tools/                   # 工具模块
    │   └── README.md
    ├── gateway/                 # Gateway 模块
    │   └── README.md
    ├── lightweight/             # 轻量版模块
    │   └── README.md
    ├── plugins/                 # 插件模块
    │   └── README.md
    ├── advanced_reasoning/      # 高级推理模块
    │   └── README.md
    ├── tests/                   # 测试文档
    │   └── README.md
    ├── cli/                     # CLI 模块
    │   └── README.md
    ├── brain/                   # Brain 模块
    │   ├── README.md            # Brain 概述
    │   ├── agent-loop.md        # Brain Agent（ReAct Loop）
    │   └── skills.md            # Brain Skills（技能系统）
    └── brain_curator/          # Curator 模块
        └── README.md           # Curator 自我进化
```

---

## 🚀 快速导航

### 新手入门
| 文档 | 内容 | 预计时间 |
|------|------|----------|
| [Quick Start](guides/quick-start.md) | 5分钟快速上手 | 5min |
| [System Design](guides/system-design.md) | 系统设计概览 | 10min |

### 核心架构
| 文档 | 内容 |
|------|------|
| [Architecture](architecture/architecture.md) | 三层架构设计（Hermes-Brain + OpenClaw-Body） |
| [Architecture Overview](architecture/overview.md) | 轻量版架构概览 |
| [LLM Tool Selection](architecture/llm-tool-selection.md) | LLM 驱动的工具选择（已废弃） |
| [Migration Guide](guides/migration-guide.md) | 移除意图识别层迁移指南 |

### 开发参考
| 文档 | 内容 |
|------|------|
| [Quick Reference](guides/quick-reference.md) | 命令、API、最佳实践快速参考 |
| [API Reference](guides/api-reference.md) | 完整 API 文档 |
| [Testing Summary](development/testing-summary.md) | 测试覆盖报告 |
| [Contributing](guides/contributing.md) | 贡献指南 |

### 模块文档
| 文档 | 内容 |
|------|------|
| [Core Module](modules/core/README.md) | 核心模块（会话、路由、缓存） |
| [Agent Module](modules/agent/README.md) | Agent 模块（系统提示词、决策引擎） |
| [Tools Module](modules/tools/README.md) | 工具模块（工具注册、执行） |
| [Brain Module](modules/brain/README.md) | Brain 模块（LLM、记忆、轨迹） |
| [Brain Agent](modules/brain/agent-loop.md) | ReAct 模式的 Agent Loop |
| [Brain Skills](modules/brain/skills.md) | 技能系统（匹配、加载、生命周期） |
| [Curator Module](modules/brain_curator/README.md) | Curator 自我进化 |
| [Gateway Module](modules/gateway/README.md) | Gateway 模块（认证、限流） |
| [Lightweight Module](modules/lightweight/README.md) | 轻量版（<30MB，零依赖） |
| [CLI Module](modules/cli/README.md) | CLI 终端界面 |
| [Plugins Module](modules/plugins/README.md) | 插件系统 |
| [Advanced Reasoning](modules/advanced_reasoning/README.md) | 高级推理模块 |

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
# 轻量版
python -m lightweight

# Gateway
python -m gateway --no-auth

# 带认证
python -m gateway --api-key KEY --rate-limit 100

# 运行测试
python tests/run_all_tests.py

# 代码覆盖率
python -m pytest tests/unit/ --cov=. --cov-report=term-missing
```

---

## 🔗 相关文档

- [项目 README](../README.md) - 项目概览
- [TODO.md](../TODO.md) - 开发计划
- [编码规范](../.trae/rules/rule.md) - 编码规范文档

---

**最后更新**: 2026-06-01
**版本**: v2.2.0 - 文档命名统一为 kebab-case