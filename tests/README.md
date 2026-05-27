# Tests Directory

## Overview

This directory contains all test files for the Handsome Agent project, organized by test type and module following industry best practices.

## Directory Structure

```
tests/
├── unit/                    # Unit tests - test individual components in isolation
│   ├── adapter/            # Adapter module tests
│   ├── brain/             # Brain module tests
│   ├── brain_curator/     # Curator self-evolution tests
│   ├── executor/           # Executor module tests
│   └── tools/             # Tools module tests
├── integration/            # Integration tests
├── performance/            # Performance tests
├── conftest.py             # pytest configuration
└── __init__.py             # Test package initialization
```

## Test Types

### Unit Tests (`unit/`)
- **Purpose**: Test individual functions, classes, and methods in isolation
- **Speed**: Fast execution (milliseconds)
- **Dependencies**: Mocked or minimal dependencies
- **Coverage**: High coverage of edge cases and error conditions

### Integration Tests (`integration/`)
- **Purpose**: Test how different modules work together
- **Speed**: Moderate execution (seconds)
- **Dependencies**: Real dependencies between modules

### Performance Tests (`performance/`)
- **Purpose**: Measure response times, memory usage, and caching effectiveness
- **Speed**: Varies based on test complexity

## Running Tests

### Using pytest

```bash
# Run all tests
pytest tests/unit/ -v

# Run specific test module
pytest tests/unit/brain_curator/ -v

# Run Curator tests
pytest tests/unit/brain_curator/ -v

# Run with coverage
pytest tests/unit/ --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/brain_curator/test_curator.py -v
```

## Curator & Self-Evolution Tests

### TrajectoryRecorder Tests

```python
# Test trajectory recording
trajectory_id = recorder.start_trajectory("test input")
recorder.record_thought("reasoning", confidence=0.9)
recorder.record_action("tool_name", {"param": "value"})
recorder.record_observation("result", success=True)
trajectory = recorder.end_trajectory("final response", TrajectoryStatus.SUCCESS)
```

### Curator Tests

```python
# Test curator evaluation
curator = Curator(trajectory_recorder, skill_writer)
report = await curator.evaluate(trajectory)
skill = await curator.process_trajectory(trajectory)
```

## Test Coverage

| Module | Tests | Status |
|--------|--------|--------|
| brain_curator | 19 | ✅ All Passing |
| TrajectoryRecorder | 11 | ✅ |
| Curator | 4 | ✅ |
| CuratorEvaluate | 3 | ✅ |
| SynthesizedSkill | 1 | ✅ |

---

*Handsome Agent - Hermes-Brain + OpenClaw-Body*
