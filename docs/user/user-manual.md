# Handsome Agent 用户手册

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [快速开始](#一快速开始)
2. [CLI 使用](#二cli-使用)
3. [会话管理](#三会话管理)
4. [工具使用](#四工具使用)
5. [技能系统](#五技能系统)
6. [Gateway 服务](#六gateway-服务)
7. [配置说明](#七配置说明)
8. [常见问题](#八常见问题)

---

## 一、快速开始

### 1.1 环境要求

- Python 3.11+
- pip 包管理器

### 1.2 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/Handsome-Agent.git
cd Handsome-Agent

# 安装依赖
pip install -r requirements.txt
```

### 1.3 首次配置

```bash
# 运行配置向导
python -m cli.main setup

# 或者设置环境变量
export HANDSOME_LLM_PROVIDER=openai
export HANDSOME_LLM_API_KEY=your-api-key
```

### 1.4 启动对话

```bash
# 交互式对话
python -m cli.main chat

# 指定会话继续
python -m cli.main chat --session <session_id>

# 强制新建会话
python -m cli.main chat --new-session
```

---

## 二、CLI 使用

### 2.1 命令结构

```
handsome-agent [command] [subcommand] [options]
```

### 2.2 可用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `chat` | 交互式对话 | `python -m cli.main chat` |
| `setup` | 首次配置 | `python -m cli.main setup` |
| `session list` | 列出会话 | `python -m cli.main session list` |
| `session show` | 查看会话 | `python -m cli.main session show <id>` |
| `session delete` | 删除会话 | `python -m cli.main session delete <id>` |
| `tools list` | 列出工具 | `python -m cli.main tools list` |
| `tools info` | 工具详情 | `python -m cli.main tools info <name>` |
| `skills list` | 列出技能 | `python -m cli.main skills list` |
| `skills add` | 添加技能 | `python -m cli.main skills add <file>` |

### 2.3 Chat 命令选项

| 选项 | 说明 |
|------|------|
| `--new-session` | 强制创建新会话 |
| `--session <id>` | 指定会话 ID |
| `--debug` | 启用调试日志 |

### 2.4 使用示例

```bash
# 基本对话
python -m cli.main chat

# 新建会话
python -m cli.main chat --new-session

# 继续指定会话
python -m cli.main chat --session abc-123

# 查看会话列表
python -m cli.main session list

# 查看会话详情
python -m cli.main session show abc-123

# 列出所有工具
python -m cli.main tools list

# 查看工具详情
python -m cli.main tools info file_read
```

---

## 三、会话管理

### 3.1 会话概述

Handsome Agent 自动管理对话会话：
- 每个会话有唯一 ID
- 按日期组织存储
- 自动保存对话历史
- 支持继续之前的会话

### 3.2 会话存储位置

```
~/.handsome_agent/sessions/{YYYY-MM-DD}/
├── {session_id}.json    # 会话数据
└── {session_id}_messages.json  # 消息记录
```

### 3.3 会话命令

```bash
# 列出所有会话
python -m cli.main session list

# 输出示例：
# Session ID          Created           Last Active      Messages
# abc-123-def          2026-06-09 10:00  2026-06-09 10:30  15
# ghi-456-jkl          2026-06-08 14:00  2026-06-08 15:00  8

# 查看会话详情
python -m cli.main session show abc-123-def

# 删除会话
python -m cli.main session delete abc-123-def
```

### 3.4 自动会话

- 如果不指定会话，默认使用今天的会话
- 如果今天没有会话，自动创建新会话
- 使用 `--new-session` 强制创建新会话

---

## 四、工具使用

### 4.1 工具分类

| 类别 | 工具 | 说明 |
|------|------|------|
| **文件操作** | `file_read`, `file_write`, `file_edit` | 读写编辑文件 |
| **目录操作** | `directory_list`, `directory_create` | 目录管理 |
| **命令执行** | `shell_execute`, `python_execute` | 执行命令和代码 |
| **网络工具** | `web_search`, `web_extract`, `http_request` | 网络请求 |
| **浏览器** | `browser_open`, `browser_click` | 浏览器自动化 |
| **多媒体** | `image_generate`, `text_to_speech` | 图像和语音 |
| **任务管理** | `todo_add`, `todo_list`, `todo_complete` | Todo 列表 |
| **记忆** | `memory_save`, `memory_search` | 记忆存储检索 |
| **技能** | `skill_register`, `skill_execute` | 技能管理 |
| **视觉** | `vision_analyze`, `vision_ocr` | 图像分析 |
| **定时** | `cronjob_create`, `cronjob_list` | 定时任务 |
| **应用** | `app_launch`, `calculator` | 应用启动 |

### 4.2 查看工具

```bash
# 列出所有可用工具
python -m cli.main tools list

# 查看特定工具详情
python -m cli.main tools info file_read

# 输出示例：
# Name: file_read
# Description: 读取文件内容
# Category: file
# Parameters:
#   - path (string, required): 文件路径
#   - max_lines (integer, optional): 最大行数
```

### 4.3 工具使用示例

**文件操作**：
```
用户：读取 /path/to/file.txt 文件内容
Agent：自动调用 file_read 工具
```

**命令执行**：
```
用户：执行 ls -la 命令
Agent：自动调用 shell_execute 工具
```

**网页抓取**：
```
用户：抓取 https://example.com 的标题
Agent：自动调用 web_extract 工具
```

---

## 五、技能系统

### 5.1 技能概述

技能是一段可复用的提示词或代码，可以在特定场景下自动匹配使用。

### 5.2 内置技能

Handsome Agent 提供多个内置技能：

| 技能名称 | 说明 | 触发条件 |
|----------|------|----------|
| `code_assistant` | 代码助手 | 需要编写代码时 |
| `debug_helper` | 调试助手 | 遇到错误时 |
| `documentation_writer` | 文档编写 | 需要写文档时 |
| `test_generator` | 测试生成 | 需要写测试时 |

### 5.3 管理技能

```bash
# 列出所有技能
python -m cli.main skills list

# 添加技能
python -m cli.main skills add my_skill.md

# 查看技能详情
python -m cli.main skills info my_skill
```

### 5.4 技能生命周期

| 状态 | 说明 |
|------|------|
| `active` | 活跃，正在使用 |
| `stale` | 不活跃，需要重新评估 |
| `archived` | 已归档，不再使用 |

---

## 六、Gateway 服务

### 6.1 启动 Gateway

```bash
# 基本启动（无认证）
python -m gateway

# 带认证启动
python -m gateway --api-key your-api-key

# 带限流启动
python -m gateway --api-key your-api-key --rate-limit 100
```

### 6.2 Gateway 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--host` | 监听地址 | `0.0.0.0` |
| `--port` | 监听端口 | `8080` |
| `--api-key` | API 认证密钥 | 无 |
| `--rate-limit` | 每分钟请求限制 | 无限制 |
| `--no-auth` | 禁用认证 | false |

### 6.3 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat` | POST | 对话接口 |
| `/api/v1/sessions` | GET | 会话列表 |
| `/api/v1/sessions/{id}` | GET | 会话详情 |
| `/api/v1/tools` | GET | 工具列表 |
| `/api/v1/health` | GET | 健康检查 |

### 6.4 API 调用示例

```bash
# 对话请求
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"message": "你好", "session_id": "optional-session-id"}'

# 获取工具列表
curl http://localhost:8080/api/v1/tools \
  -H "Authorization: Bearer your-api-key"
```

---

## 七、配置说明

### 7.1 配置文件

配置文件位于 `~/.handsome_agent/config.json`

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key",
    "temperature": 0.7
  },
  "logging": {
    "level": "INFO"
  },
  "session": {
    "auto_save": true,
    "max_context_length": 10
  }
}
```

### 7.2 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `HANDSOME_HOME` | 数据目录 | `~/.handsome_agent` |
| `HANDSOME_LLM_PROVIDER` | LLM 提供商 | `openai` |
| `HANDSOME_LLM_API_KEY` | API Key | `sk-xxx` |
| `HANDSOME_LLM_MODEL` | 模型名称 | `gpt-4` |
| `HANDSOME_LOG_LEVEL` | 日志级别 | `INFO` |

### 7.3 LLM 提供商配置

**OpenAI**:
```bash
export HANDSOME_LLM_PROVIDER=openai
export HANDSOME_LLM_API_KEY=sk-xxx
export HANDSOME_LLM_MODEL=gpt-4
```

**Claude**:
```bash
export HANDSOME_LLM_PROVIDER=claude
export HANDSOME_LLM_API_KEY=sk-ant-xxx
export HANDSOME_LLM_MODEL=claude-3-opus
```

**Gemini**:
```bash
export HANDSOME_LLM_PROVIDER=gemini
export HANDSOME_LLM_API_KEY=xxx
export HANDSOME_LLM_MODEL=gemini-pro
```

---

## 八、常见问题

### 8.1 对话相关

**Q: 对话响应很慢？**
> 检查网络连接和 LLM API 状态。可以尝试切换到更快的模型。

**Q: 如何继续之前的对话？**
> 使用 `--session <session_id>` 参数指定会话 ID，或使用 `--new-session` 创建新会话。

**Q: 如何清除对话历史？**
> 创建新会话即可，历史会话会保留在存储中。

### 8.2 工具相关

**Q: 工具执行失败？**
> 检查工具参数是否正确，确认相关依赖是否安装。

**Q: 如何查看可用工具？**
> 使用 `python -m cli.main tools list` 查看所有工具。

**Q: Shell 命令执行超时？**
> 默认超时时间为 60 秒，可以通过配置调整。

### 8.3 配置相关

**Q: 如何修改 LLM 模型？**
> 设置环境变量 `HANDSOME_LLM_MODEL` 或修改配置文件。

**Q: 如何启用调试日志？**
> 设置 `HANDSOME_LOG_LEVEL=DEBUG` 或使用 `--debug` 参数。

**Q: 数据存储在哪里？**
> 默认在 `~/.handsome_agent/` 目录，可以通过 `HANDSOME_HOME` 环境变量修改。

### 8.4 Gateway 相关

**Q: Gateway 无法启动？**
> 检查端口是否被占用，确认认证参数正确。

**Q: API 请求被限流？**
> 降低请求频率，或联系管理员调整限流配置。

---

## 附录

### A. 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+C` | 退出对话 |
| `Ctrl+D` | 退出对话 |
| `↑/↓` | 查看历史输入 |

### B. 日志级别

| 级别 | 说明 |
|------|------|
| `DEBUG` | 详细调试信息 |
| `INFO` | 一般信息 |
| `WARNING` | 警告信息 |
| `ERROR` | 错误信息 |

### C. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09