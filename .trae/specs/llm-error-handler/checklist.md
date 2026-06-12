# Checklist

## Task 1: error/ 目录结构
- [x] agent/error/ 目录已创建
- [x] agent/error/__init__.py 已创建并正确导出
- [x] agent/error/exceptions.py 包含所有自定义异常
- [x] agent/error/retry_utils.py 包含退避重试策略

## Task 2: error_classifier.py
- [x] FailoverReason 枚举包含所有必要错误类型（auth、billing、rate_limit、timeout、context_overflow、model_not_found、server_error、format_error、unknown 等）
- [x] ClassifiedError 数据类包含所有必要字段（reason、status_code、provider、model、message、retryable、should_compress、should_rotate_credential、should_fallback）
- [x] 错误模式列表包含英文和中文匹配项
- [x] classify_api_error 函数能正确分类常见错误场景
- [x] _extract_status_code 能正确提取 HTTP 状态码
- [x] _extract_error_body 能正确提取错误响应体
- [x] _extract_message 能正确提取错误消息

## Task 3: helpers.py
- [x] _summarize_api_error 能处理 JSON body 错误
- [x] _summarize_api_error 能处理 Cloudflare HTML 错误
- [x] _extract_api_error_context 能正确提取错误上下文
- [x] _mask_api_key_for_logs 能正确脱敏 API Key

## Task 4: BaseProvider 集成
- [x] BaseProvider._log_request_error 方法集成错误分类器
- [x] 错误日志包含完整的分类信息和恢复建议
- [x] 日志格式符合规范

## Task 5: React Loop 集成
- [x] react/loop.py 工具执行错误处理使用分类器
- [x] 提供结构化错误结果字典
- [x] 错误日志包含完整信息

## Task 6: Rails Manager 集成
- [x] rails/manager.py on_error 回调处理正确
- [x] 统一日志输出格式

## Task 7: Provider 实现
- [x] minimax.py 正确使用统一错误处理
- [x] 其他 Provider 正确使用统一错误处理

## Task 8: 验证
- [x] 日志输出格式符合规范（包含 provider、model、reason、status_code、recovery hints）
- [x] 各错误类型分类正确
- [x] 错误摘要生成正确
- [x] Rails Manager 中的 logger 引用 bug 已修复