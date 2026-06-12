# Agent 报错管理体系 Spec

## Why
当前项目的错误处理分散在各处，没有统一的分类和恢复策略。参考 Hermes 项目的完整错误处理体系，需要实现一套覆盖 LLM、工具执行、Rails 等全链路的结构化错误处理系统。

## What Changes
- 新增 `agent/error/error_classifier.py` - LLM API 错误分类器
- 新增 `agent/error/exceptions.py` - 自定义异常定义
- 新增 `agent/error/helpers.py` - 错误处理辅助函数
- 新增 `agent/error/retry_utils.py` - 重试策略工具
- 修改 `agent/llm/providers/base.py` 集成错误分类
- 修改 `agent/react/loop.py` 工具执行错误处理
- 修改 `agent/rails/manager.py` Rails 错误回调

## Impact
- Affected specs: agent/llm/providers/*, agent/react/*, agent/rails/*
- Affected code:
  - 新增 `agent/error/` 目录
  - 修改各 Provider、React Loop、Rails Manager

## ADDED Requirements

### Requirement: 错误分类核心（LLM API）
系统 SHALL 提供结构化的 LLM API 错误分类能力。

#### Scenario: HTTP 认证错误
- **WHEN** LLM API 返回 401/403 状态码
- **THEN** 分类为 `auth`，标记 `retryable=False`，建议轮换凭证和回退

#### Scenario: 计费/配额错误
- **WHEN** 错误消息包含 "insufficient credits"、"配额" 等
- **THEN** 分类为 `billing`，立即轮换凭证

#### Scenario: 速率限制
- **WHEN** 错误消息包含 "rate limit"、"请求过于频繁" 等
- **THEN** 分类为 `rate_limit`，应用退避后重试

#### Scenario: 上下文溢出
- **WHEN** 错误消息包含 "context length"、"上下文长度" 等
- **THEN** 分类为 `context_overflow`，标记 `should_compress=True`

#### Scenario: 服务端错误
- **WHEN** HTTP 状态码为 500/502/503/529
- **THEN** 分类为 `server_error` 或 `overloaded`，应用退避重试

#### Scenario: 超时错误
- **WHEN** 异常类型为 TimeoutError 或消息包含 "timed out"
- **THEN** 分类为 `timeout`，重建客户端重试

### Requirement: 错误分类核心（工具执行）
系统 SHALL 提供结构化的工具执行错误分类能力。

#### Scenario: 工具执行失败
- **WHEN** 工具执行抛出异常
- **THEN** 分类为 `tool_error`，记录错误并返回工具结果

#### Scenario: Rails 拦截
- **WHEN** Rails 在工具调用前后拦截
- **THEN** 记录 `rail.on_error()` 回调，分类为 `rail_blocked`

### Requirement: 自定义异常层次
系统 SHALL 提供以下自定义异常：
- `AgentError` - 基础异常类
- `LLMError` - LLM 相关错误基类
- `LLMAuthError` - 认证错误
- `LLMBillingError` - 计费错误
- `LLMRateLimitError` - 速率限制错误
- `LLMContextOverflowError` - 上下文溢出错误
- `LLMServerError` - 服务端错误
- `ToolExecutionError` - 工具执行错误
- `RailBlockedError` - Rails 拦截错误

### Requirement: 错误摘要生成
系统 SHALL 提供 `_summarize_api_error()` 方法，生成用户友好的错误摘要：
- 优先从 JSON body 提取消息
- 处理 Cloudflare HTML 错误页面，提取 `<title>` 标签
- 处理 Provider 流式响应错误
- 截断并添加 HTTP 状态码前缀

### Requirement: 错误上下文提取
系统 SHALL 提供 `_extract_api_error_context()` 方法，提取错误上下文：
- 错误类型名称
- HTTP 状态码
- 错误消息（前500字符）
- Provider 名称
- Model 名称

### Requirement: 恢复建议
分类结果 SHALL 包含以下恢复建议字段：
- `retryable`: 是否可重试
- `should_compress`: 是否应压缩上下文
- `should_rotate_credential`: 是否应轮换凭证
- `should_fallback`: 是否应回退到备选模型

### Requirement: 统一日志输出
错误日志 SHALL 包含：
- Provider 和 Model 信息
- 错误分类原因（FailoverReason）
- HTTP 状态码
- 错误类型和消息
- 恢复建议（retryable、compress、rotate、fallback）

## MODIFIED Requirements

### Requirement: BaseProvider 错误处理
**Modified**: `agent/llm/providers/base.py` 的 `_log_request_error` 方法

原方法仅记录错误日志，新方法 SHALL：
1. 使用 error_classifier 分类错误
2. 输出详细的分类结果（reason、status_code、recovery hints）
3. 根据分类结果决定是否需要特殊处理

### Requirement: React Loop 工具执行错误处理
**Modified**: `agent/react/loop.py` 工具执行部分

原实现直接记录错误，新实现 SHALL：
1. 分类工具执行错误
2. 提供结构化的错误结果字典
3. 支持错误恢复建议

### Requirement: Rails Manager 错误回调
**Modified**: `agent/rails/manager.py` Rails 回调

原实现无结构化错误处理，新实现 SHALL：
1. 在 on_error 回调中记录详细错误
2. 包含 rail 名称、checkpoint 名称
3. 统一日志输出格式

## Architecture

```
agent/error/
├── __init__.py           # 导出公共接口
├── error_classifier.py   # LLM API 错误分类器
├── exceptions.py         # 自定义异常定义
├── helpers.py           # 错误处理辅助函数
└── retry_utils.py       # 重试策略工具

FailoverReason 枚举:
├── auth                    # 认证问题
├── auth_permanent          # 永久认证失败
├── billing                 # 计费/配额问题
├── rate_limit             # 速率限制
├── overloaded             # 服务器过载
├── server_error           # 500/502 错误
├── timeout                # 连接超时
├── context_overflow       # 上下文溢出
├── payload_too_large      # 请求体过大
├── image_too_large        # 图片过大
├── model_not_found        # 模型未找到
├── format_error           # 格式错误
├── multimodal_tool_content_unsupported  # 多模态内容不支持
├── thinking_signature     # 思考签名错误
├── oauth_long_context_beta_forbidden    # OAuth 上下文限制
├── llama_cpp_grammar_pattern           # llama.cpp 语法错误
├── provider_policy_blocked             # Provider 策略阻止
└── unknown                 # 未知错误
```