# Brain Skills 模块

> 技能层模块 - 管理 Agent 的可扩展技能系统

## 📁 模块结构

```
brain/skills/
├── __init__.py           # 模块导出
├── matcher.py            # 技能匹配器
├── loader.py             # 技能加载器
├── registry.py           # 技能注册表
├── telemetry.py          # 技能使用追踪
├── lifecycle.py          # 技能生命周期管理
├── merger.py             # 技能合并器
└── evolution_manager.py  # 自我进化管理器
```

## 🎯 核心功能

### 1. 技能匹配 (SkillsMatcher)
- 基于用户输入匹配相关技能
- 支持前缀匹配、标签匹配
- 渐进式发现机制

### 2. 技能加载 (SkillsLoader)
- 从文件系统加载技能定义
- 支持 SKILL.md 格式
- 分类和标签解析

### 3. 技能注册表 (SkillsRegistry)
- 管理所有已注册技能
- 支持技能别名
- 按类别和标签组织

### 4. 技能使用追踪 (SkillTelemetry) 🆕
- 记录技能使用、查看、修改事件
- 追踪 use_count, view_count, patch_count
- 持久化到 `.skill_usage.json`
- 支持归档和恢复

### 5. 技能生命周期管理 (SkillLifecycleManager) 🆕
- 自动状态转换: active → stale (30天) → archived (90天)
- 固定技能防止自动管理
- 回调机制支持
- 定期检查后台任务

### 6. 技能合并器 (SkillMerger) 🆕
- 前缀聚类识别
- 伞形技能自动创建
- 相似技能合并
- 合并报告生成

### 7. 自我进化管理器 (SelfEvolutionManager) 🆕
- 统一管理所有自我进化组件
- 启动/停止控制
- 状态查询
- 配置管理

## 🚀 快速开始

### 基本使用

```python
from brain.skills import SkillsLoader, SkillsMatcher

# 加载技能
loader = SkillsLoader()
skills = asyncio.run(loader.load_all())

# 匹配技能
matcher = SkillsMatcher(skills)
matched = matcher.match("搜索 Python 教程")
```

### 技能使用追踪

```python
from brain.skills import get_skill_telemetry

telemetry = get_skill_telemetry()

# 记录使用
telemetry.record_use("web_search")
telemetry.record_view("web_search")
telemetry.record_patch("web_search")

# 获取统计
summary = telemetry.get_usage_summary()
print(f"Total uses: {summary['total_uses']}")
```

### 技能生命周期管理

```python
from brain.skills import get_lifecycle_manager

lifecycle = get_lifecycle_manager()

# 应用自动状态转换
report = lifecycle.apply_automatic_transitions()

# 获取摘要
summary = lifecycle.get_lifecycle_summary()
print(f"Active: {summary['active']}, Stale: {summary['stale']}")
```

### 自我进化管理

```python
from brain.skills import get_self_evolution_manager

manager = get_self_evolution_manager()

# 启动
await manager.start()

# 记录技能使用
manager.record_skill_use("web_search")

# 获取状态
status = manager.get_status()
print(status)

# 停止
await manager.stop()
```

## 📊 数据存储

### 技能目录结构

```
~/.handsome_agent/
└── skills/
    ├── .skill_usage.json      # 使用追踪数据
    ├── .curator_state         # Curator 状态
    ├── web_search/
    │   └── SKILL.md
    ├── code_generator/
    │   └── SKILL.md
    └── .archive/              # 归档的技能
        └── old_skill/
```

## 🔄 自我进化流程

```
用户对话
    ↓
AgentLoop 执行
    ↓
记录使用 → SkillTelemetry
    ↓
周期性检查 → SkillLifecycleManager
    ↓ (每10轮)
Curator 审查 → 轨迹评估 + 技能合成
    ↓
SkillMerger → 相似技能合并
    ↓
新技能生成 → 自动学习
    ↓
越聊越好用 ✨
```

## 📝 API 参考

### SkillTelemetry

| 方法 | 说明 |
|------|------|
| `record_use(skill_id)` | 记录技能使用 |
| `record_view(skill_id)` | 记录技能查看 |
| `record_patch(skill_id)` | 记录技能修改 |
| `get_usage_summary()` | 获取使用统计 |
| `archive_skill(skill_id)` | 归档技能 |
| `restore_skill(skill_id)` | 恢复技能 |

### SkillLifecycleManager

| 方法 | 说明 |
|------|------|
| `apply_automatic_transitions()` | 应用自动状态转换 |
| `archive_skill(skill_id)` | 归档技能 |
| `restore_skill(skill_id)` | 恢复技能 |
| `pin_skill(skill_id)` | 固定技能 |
| `get_lifecycle_summary()` | 获取生命周期摘要 |

### SelfEvolutionManager

| 方法 | 说明 |
|------|------|
| `start()` | 启动自我进化 |
| `stop()` | 停止自我进化 |
| `record_skill_use(skill_id)` | 记录技能使用 |
| `trigger_review()` | 触发审查 |
| `get_status()` | 获取状态 |

## 🧪 测试

```bash
# 运行所有测试
pytest tests/unit/brain/test_skill_*.py -v

# 运行特定测试
pytest tests/unit/brain/test_skill_telemetry.py -v
pytest tests/unit/brain/test_skill_lifecycle.py -v
pytest tests/unit/brain/test_skill_merger.py -v
```

## 📚 相关模块

- [brain/agent](../agent/) - Agent Loop 集成
- [brain_curator](../brain_curator/) - Curator 自我进化核心

## 🔄 更新日志

- **2026-05-31**: 新增 SkillTelemetry, SkillLifecycleManager, SkillMerger, SelfEvolutionManager

---

*最后更新: 2026-05-31*
