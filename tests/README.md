# Tests Directory

## Overview
This directory contains all test files for the Handsome Agent project, organized by test type and module following industry best practices.

## Directory Structure

```
tests/
├── unit/                    # Unit tests - test individual components in isolation
│   ├── core/               # Core module unit tests
│   ├── advanced_reasoning/ # Advanced Reasoning module unit tests  
│   └── cli/                # CLI module unit tests
├── integration/            # Integration tests - test component interactions
├── performance/            # Performance tests - measure speed, memory, and efficiency
├── conftest.py             # pytest configuration with shared fixtures
└── __init__.py             # Test package initialization
```

## Test Types

### Unit Tests (`unit/`)
- **Purpose**: Test individual functions, classes, and methods in isolation
- **Scope**: Single module or component testing
- **Speed**: Fast execution (milliseconds)
- **Dependencies**: Mocked or minimal dependencies
- **Coverage**: High coverage of edge cases and error conditions

### Integration Tests (`integration/`)
- **Purpose**: Test how different modules work together
- **Scope**: Multi-component interaction testing
- **Speed**: Moderate execution (seconds)
- **Dependencies**: Real dependencies between modules
- **Coverage**: End-to-end workflows and integration points

### Performance Tests (`performance/`)
- **Purpose**: Measure response times, memory usage, and caching effectiveness
- **Scope**: System-level performance characteristics
- **Speed**: Varies based on test complexity
- **Dependencies**: Real system components
- **Coverage**: Performance benchmarks and optimization validation

## Running Tests

### Using pytest (Recommended)
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only  
pytest tests/integration/

# Run performance tests only
pytest tests/performance/

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/core/test_agent.py
```

### Using Python directly
```bash
# Run specific test file
python -m tests.unit.core.test_agent

# Run integration tests
python -m tests.integration.test_integration

# Run performance tests
python -m tests.performance.test_performance
```

## Test Fixtures

The `conftest.py` file provides shared fixtures for all tests:

- `basic_agent`: Pre-configured basic agent instance
- `advanced_agent`: Pre-configured advanced agent instance  
- `test_config`: Standard test configuration
- `sample_queries`: Common test queries for consistency

## Testing Guidelines

### Unit Tests
- Test one thing at a time
- Use descriptive test names (`test_function_behavior`)
- Include edge cases and error conditions
- Mock external dependencies when possible
- Keep tests fast and independent

### Integration Tests
- Test real component interactions
- Verify data flow between modules
- Test error propagation across boundaries
- Include realistic usage scenarios
- Ensure backward compatibility

### Performance Tests
- Measure baseline performance metrics
- Test caching effectiveness
- Validate timeout handling
- Monitor memory usage patterns
- Establish performance thresholds

## Quality Standards

All tests must adhere to these quality standards:

- **Comprehensive Coverage**: Test both success and failure paths
- **Clear Assertions**: Use descriptive assertion messages
- **Consistent Naming**: Follow `test_` prefix convention
- **Proper Setup/Teardown**: Clean up resources after tests
- **Documentation**: Include docstrings explaining test purpose

## Adding New Tests

When adding new functionality, follow these steps:

1. **Create appropriate test file** in the relevant subdirectory
2. **Write tests before implementation** (TDD approach when possible)
3. **Use existing fixtures** from `conftest.py` when applicable
4. **Follow naming conventions** and testing guidelines
5. **Verify test passes** with the new implementation
6. **Update documentation** if test patterns change

## Continuous Integration

This test structure is designed to work with CI/CD pipelines:

- **Fast feedback**: Unit tests run quickly for immediate feedback
- **Comprehensive validation**: Integration tests ensure system correctness  
- **Performance monitoring**: Performance tests catch regressions
- **Parallel execution**: Tests can run in parallel for faster CI cycles

---

This test directory structure ensures high-quality, maintainable, and comprehensive test coverage for the Handsome Agent project, following OpenClaw-inspired principles of clarity and thoroughness.