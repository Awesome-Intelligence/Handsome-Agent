# Tests Directory - 测试目录

> Agent-Z 项目的测试套件

## 目录结构

```
tests/
├── unit/                        # 单元测试 - 隔离测试各个组件
│   ├── adapter/                 # Adapter 模块测试
│   ├── advanced_reasoning/     # 高级推理模块测试
│   ├── brain/                  # Brain 模块测试
│   ├── brain_curator/          # Curator 自我进化测试
│   ├── cli/                    # CLI 模块测试
│   ├── core/                   # Core 模块测试
│   ├── executor/               # Executor 模块测试
│   ├── shared/                 # Shared 模块测试
│   └── tools/                  # Tools 模块测试
├── integration/                 # 集成测试
├── performance/                # 性能测试
├── conftest.py                 # pytest 配置
└── __init__.py                 # 测试包初始化
```

## 测试类型

### 单元测试 (`unit/`)

- **目的**: 隔离测试独立函数、类和方法
- **速度**: 快速执行（毫秒级）
- **依赖**: Mock 或最小依赖
- **覆盖率**: 高覆盖率覆盖边缘情况和错误条件

### 集成测试 (`integration/`)

- **目的**: 测试不同模块如何协同工作
- **速度**: 中等执行时间（秒级）
- **依赖**: 模块之间的真实依赖

### 性能测试 (`performance/`)

- **目的**: 测量响应时间、内存使用和缓存效率
- **速度**: 根据测试复杂度变化

## 运行测试

### 使用 pytest

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试模块
pytest tests/unit/brain_curator/ -v
pytest tests/unit/tools/ -v

# 运行带覆盖率
pytest tests/unit/ --cov=. --cov-report=html

# 运行特定测试文件
pytest tests/unit/brain_curator/test_curator.py -v
```

### Curator & 自我进化测试

```python
# 测试轨迹记录
trajectory_id = recorder.start_trajectory("test input")
recorder.record_thought("reasoning", confidence=0.9)
recorder.record_action("tool_name", {"param": "value"})
recorder.record_observation("result", success=True)
trajectory = recorder.end_trajectory("final response", TrajectoryStatus.SUCCESS)
```

```python
# 测试 Curator 评估
curator = Curator(trajectory_recorder, skill_writer)
report = await curator.evaluate(trajectory)
skill = await curator.process_trajectory(trajectory)
```

## 测试覆盖率

| 模块 | 测试数 | 状态 |
|------|--------|------|
| brain_curator | 19+ | ✅ 通过 |
| TrajectoryRecorder | 11+ | ✅ |
| Curator | 4+ | ✅ |
| CuratorEvaluate | 3+ | ✅ |
| SynthesizedSkill | 1+ | ✅ |

## 测试命令速查

```bash
# 全部测试
pytest tests/ -v

# 快速测试（跳过慢速测试）
pytest tests/ -k "not slow" -v

# 代码覆盖率
pytest tests/unit/ --cov=. --cov-report=term-missing

# 仅运行 brain 模块测试
pytest tests/unit/brain/ -v

# 仅运行 tools 模块测试
pytest tests/unit/tools/ -v
```

## 故障排除

### 测试失败

```bash
# 详细输出
pytest -vv --tb=long

# 仅运行快速测试
pytest -k "not slow" -v
```

### 导入错误

```bash
# 确保在项目根目录
cd Agent-Z

# 检查 Python 路径
python -c "import tests; print('OK')"
```

---

*Agent-Z - Hermes-Brain + OpenClaw-Body*
*最后更新: 2026-06-01*