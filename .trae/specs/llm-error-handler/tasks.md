# Tasks

- [x] Task 1: 创建 error/ 目录结构和基础模块
  - [x] SubTask 1.1: 创建 agent/error/ 目录
  - [x] SubTask 1.2: 创建 agent/error/__init__.py
  - [x] SubTask 1.3: 创建 agent/error/exceptions.py - 定义自定义异常层次
  - [x] SubTask 1.4: 创建 agent/error/retry_utils.py - 退避重试策略

- [x] Task 2: 实现 error_classifier.py 核心模块
  - [x] SubTask 2.1: 实现 FailoverReason 枚举（auth、billing、rate_limit、timeout、context_overflow 等，包含中文）
  - [x] SubTask 2.2: 实现 ClassifiedError 数据类
  - [x] SubTask 2.3: 实现错误模式列表（BILLING_PATTERNS、RATE_LIMIT_PATTERNS、CONTEXT_OVERFLOW_PATTERNS 等，包含中文）
  - [x] SubTask 2.4: 实现 classify_api_error 分类函数
  - [x] SubTask 2.5: 实现 _extract_status_code、_extract_error_body、_extract_message 等辅助函数

- [x] Task 3: 实现 helpers.py 辅助函数
  - [x] SubTask 3.1: 实现 _summarize_api_error() - 生成用户友好的错误摘要
  - [x] SubTask 3.2: 实现 _extract_api_error_context() - 提取错误上下文
  - [x] SubTask 3.3: 实现 _mask_api_key_for_logs() - 日志脱敏

- [x] Task 4: 集成到 BaseProvider
  - [x] SubTask 4.1: 在 base.py 中导入 error_classifier
  - [x] SubTask 4.2: 重构 _log_request_error 方法，使用错误分类器
  - [x] SubTask 4.3: 添加统一的错误处理日志格式

- [x] Task 5: 更新 React Loop 工具执行错误处理
  - [x] SubTask 5.1: 在 react/loop.py 中导入 error_classifier
  - [x] SubTask 5.2: 重构工具执行错误处理，使用分类器
  - [x] SubTask 5.3: 添加结构化错误结果字典

- [x] Task 6: 更新 Rails Manager 错误回调
  - [x] SubTask 6.1: 在 rails/manager.py 中添加错误回调处理
  - [x] SubTask 6.2: 统一日志输出格式

- [x] Task 7: 更新各 Provider 实现
  - [x] SubTask 7.1: 更新 minimax.py 使用统一的错误处理
  - [x] SubTask 7.2: 检查其他 Provider（如果有）并更新

- [x] Task 8: 验证和测试
  - [x] SubTask 8.1: 验证日志输出格式正确
  - [x] SubTask 8.2: 验证各错误类型分类正确
  - [x] SubTask 8.3: 修复 Rails Manager 中的 logger 引用 bug

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1 和 Task 2
- Task 4 依赖 Task 2
- Task 5 依赖 Task 2
- Task 6 依赖 Task 2
- Task 7 依赖 Task 4
- Task 8 依赖 Task 7