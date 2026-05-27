#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Document: LLM-Powered Intent Recognition

## Overview

This document describes the pure LLM-based intent recognition architecture.
**NO HARDCODED RULES** - All intent recognition relies on LLM.

## Core Principle

> "If LLM fails, the system fails gracefully with clear error messages,
> instead of falling back to hardcoded rules."

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Input                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Intent Service (llm_intent_service.py)     │
│  - Unified intent recognition for all domains               │
│  - NO hardcoded rules                                        │
│  - Returns structured IntentResult                           │
│  - Clear error messages on failure                          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ web_search   │  │ terminal_    │  │ general_     │
    │ handler      │  │ command      │  │ question     │
    │              │  │ handler      │  │ handler      │
    └──────────────┘  └──────────────┘  └──────────────┘
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Skill        │  │ Skill        │  │ Skill        │
    │ Manager      │  │ Manager      │  │ Manager      │
    └──────────────┘  └──────────────┘  └──────────────┘
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Tool         │  │ Tool         │  │ Tool         │
    │ Execution    │  │ Execution    │  │ Execution    │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## LLM Intent Domains

### 1. Browser Search (`browser_search`)

**Prompt Design:**
```python
{
    "intent_type": "browser_search",
    "action_type": "open_browser | search | visit_url",
    "target": "浏览器名称或 null",
    "parameters": {
        "url": "完整网址",
        "search_query": "搜索关键词",
        "search_engine": "baidu | google"
    }
}
```

**Example:**
- Input: "用百度查一下今天天气"
- Output: `{"intent_type": "browser_search", "action_type": "search", "parameters": {"search_query": "今天天气", "search_engine": "baidu"}}`

### 2. Terminal Command (`terminal_command`)

**Prompt Design:**
```python
{
    "intent_type": "terminal_command",
    "action_type": "open_app | open_folder | open_file | execute_command",
    "target": "应用/文件夹/文件/命令名",
    "command": "完整终端命令",
    "parameters": {
        "path": "路径",
        "url": "网址",
        "app_name": "应用名"
    }
}
```

**Example:**
- Input: "打开我的电脑"
- Output: `{"intent_type": "terminal_command", "action_type": "open_folder", "target": "我的电脑", "command": "start explorer shell:mycomputer"}`

### 3. General Query (`general_query`)

**Prompt Design:**
```python
{
    "intent_type": "general_query",
    "query_type": "question | conversation | creation | analysis | configuration",
    "topic": "主题领域",
    "parameters": {}
}
```

## Error Handling Strategy

### Traditional Approach (DEPRECATED)
```
LLM Intent → LLM Fail → Fallback to Hardcoded Rules → Continue
```

### New Approach (PURE LLM)
```
LLM Intent → LLM Fail → Return Error → System Stops Gracefully
```

## Benefits of Pure LLM Approach

1. **Consistency**: All intent recognition uses the same LLM model
2. **Maintainability**: No scattered hardcoded rules to maintain
3. **Flexibility**: LLM can understand novel expressions
4. **Transparency**: Clear error messages when LLM fails
5. **Extensibility**: Easy to add new domains

## Migration Status

| Handler | Status | Notes |
|---------|--------|-------|
| web_search | ✅ Pure LLM | No fallback |
| terminal_command | ✅ Pure LLM Module | Ready for integration |
| general_question | ⚠️ Needs Update | Currently uses rules |
| conversation | ⚠️ Needs Update | Currently uses rules |
| file_operations | ⚠️ Needs Update | Currently uses rules |
| coding_assistant | ⚠️ Needs Update | Currently uses rules |

## Configuration

To enable pure LLM intent recognition:

1. Configure LLM provider in agent initialization
2. Set `enable_llm_fallback=False` to disable any fallback behavior
3. Monitor error logs for LLM failures

## Future Enhancements

1. **Intent Chaining**: Chain multiple LLM calls for complex queries
2. **Context Awareness**: Use conversation history for better understanding
3. **Feedback Loop**: Learn from user corrections
4. **Multi-language**: Native support for multiple languages
5. **Domain Adaptation**: Fine-tune prompts for specific domains

## Conclusion

The pure LLM approach ensures that ALL intent recognition is powered by LLM,
with NO hardcoded fallback rules. This provides:
- Unified intent understanding
- Consistent behavior across domains
- Clear error handling
- Easy maintenance and extension
"""