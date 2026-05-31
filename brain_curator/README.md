# Brain Curator 模块

> 后处理层模块 - Agent 自我进化的核心引擎

## 📁 模块结构

```
brain_curator/
├── __init__.py           # 模块导出
├── curator.py            # 原 Curator 实现
├── enhanced_curator.py   # 增强版 Curator 🆕
├── evaluator.py          # 轨迹评估器
├── synthesizer.py        # 技能合成器
└── writer.py             # 技能写入器
```

## 🎯 核心功能

### 1. 轨迹评估器 (Evaluator)
- 评估 Agent 执行轨迹
- 计算成功率和置信度
- 生成改进建议

### 2. 技能合成器 (Synthesizer)
- 从成功轨迹合成新技能
- 生成技能名称和描述
- 提取触发模式和动作模板

### 3. 技能写入器 (SkillWriter)
- 将合成的技能写入文件系统
- 生成 SKILL.md 文件
- 支持技能版本管理

### 4. Curator (原版)
- 协调评估和合成
- 管理技能生命周期
- 提供反馈闭环

### 5. 增强版 Curator (EnhancedCurator) 🆕
- 后台定期运行机制
- 空闲触发审查
- CuratorState 持久化
- 条件运行检查
- 集成 SkillTelemetry
- 集成 SkillLifecycleManager

## 🚀 快速开始

### 基本使用

```python
from brain_curator import Curator, SkillWriter, TrajectoryRecorder

# 初始化组件
recorder = TrajectoryRecorder()
writer = SkillWriter()
curator = Curator(
    trajectory_recorder=recorder,
    skill_writer=writer
)

# 处理轨迹
trajectory = recorder.load_trajectory("traj-123")
skill = await curator.process_trajectory(trajectory)

if skill:
    print(f"New skill learned: {skill.name}")
```

### 增强版 Curator

```python
from brain_curator.enhanced_curator import EnhancedCurator, CuratorState

# 创建状态持久化
state = CuratorState()

# 创建增强版 Curator
curator = EnhancedCurator(
    curator_state=state,
    interval_hours=168,  # 7天
    min_idle_hours=2.0,
)

# 启动定期审查
await curator.start_periodic_review()

# 手动触发审查
result = await curator.maybe_run(idle_for_seconds=7200)

# 获取状态
status = curator.get_status()
print(f"Last run: {status['last_run_at']}")
print(f"Learned skills: {status['learned_skills_count']}")

# 停止
await curator.stop_periodic_review()
```

### 从反馈学习

```python
# 用户反馈
await curator.learn_from_feedback("traj-123", "good")
# → 自动合成并学习新技能
```

## 📊 Curator 状态

### CuratorState 持久化

```json
{
  "last_run_at": "2026-05-31T10:00:00Z",
  "last_run_duration_seconds": 5.2,
  "last_run_summary": "3 marked stale; 5 total skills",
  "paused": false,
  "run_count": 10
}
```

## 🔄 自我进化流程

```
Agent 执行轨迹
    ↓
TrajectoryRecorder 记录
    ↓
Evaluator 评估轨迹
    ↓
Synthesizer 合成技能 (置信度 > 0.7)
    ↓
SkillWriter 写入文件系统
    ↓
AgentLoop 加载新技能
    ↓
下次使用更智能 ✨
```

### 增强版自动流程

```
定时触发 / 空闲触发
    ↓
EnhancedCurator.run_review()
    ↓
SkillLifecycleManager.apply_automatic_transitions()
    ↓
状态转换: active → stale → archived
    ↓
生成报告和摘要
    ↓
记录到 CuratorState
```

## 📝 API 参考

### EnhancedCurator

| 方法 | 说明 |
|------|------|
| `start_periodic_review()` | 启动定期审查 |
| `stop_periodic_review()` | 停止定期审查 |
| `maybe_run(idle_for_seconds)` | 条件运行审查 |
| `run_review(dry_run)` | 运行一次审查 |
| `process_trajectory(trajectory)` | 处理单个轨迹 |
| `learn_from_feedback(trajectory_id, feedback)` | 从反馈学习 |
| `get_status()` | 获取状态 |

### CuratorState

| 方法 | 说明 |
|------|------|
| `should_run(interval_hours)` | 检查是否应该运行 |
| `update_run(duration, summary)` | 更新运行记录 |
| `set_paused(paused)` | 设置暂停状态 |
| `save()` | 保存到磁盘 |
| `load()` | 从磁盘加载 |

## 🧪 测试

```bash
# 运行所有测试
pytest tests/unit/brain_curator/ -v

# 运行增强版测试
pytest tests/unit/brain_curator/test_enhanced_curator.py -v
```

## 📚 相关模块

- [brain/skills](../brain/skills/) - 技能层集成
- [brain/agent](../brain/agent/) - Agent Loop 集成

## 🔄 更新日志

- **2026-05-31**: 新增 EnhancedCurator, CuratorState, 后台定期运行, 空闲触发

---

*最后更新: 2026-05-31*
