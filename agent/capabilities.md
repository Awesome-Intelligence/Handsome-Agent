# Capabilities Specification - 能力清单

> **文件位置**: `agent/capabilities.md`  
> **用途**: 详细列出 Agent 的所有能力和限制  
> **灵感来源**: Hermes Agent Capabilities、OpenClaw Skill System

---

## 🎯 能力概览

Agent 具备以下核心能力域：

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Capabilities                          │
├─────────────────────────────────────────────────────────────┤
│  1. Intent Recognition (意图识别) ✅ LLM-powered              │
│  2. Task Execution (任务执行) ✅ Tool-powered                │
│  3. Information Retrieval (信息检索) ✅ Web-enabled          │
│  4. Code Processing (代码处理) ✅ Multi-language             │
│  5. File Operations (文件操作) ✅ Cross-platform             │
│  6. System Control (系统控制) ✅ Windows/macOS/Linux        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 1. Intent Recognition (意图识别)

### 能力描述
理解用户的自然语言输入，识别真实意图和提取关键参数。

### 技术实现
- **方法**: 100% LLM 驱动
- **无硬编码**: 不使用关键词匹配或规则 fallback
- **优势**: 理解各种表达方式，包括口语化和模糊表达

### 支持的意图类型

| 意图类型 | 描述 | 示例 |
|---------|------|------|
| browser_search | 浏览器搜索 | "帮我搜索 Python 教程" |
| terminal_command | 终端命令 | "打开计算器" |
| file_operation | 文件操作 | "读取 config.json" |
| web_fetch | 网页获取 | "获取百度首页内容" |
| code_execution | 代码执行 | "运行这段 Python 代码" |
| general_query | 一般问答 | "解释一下什么是 AI" |

### 意图识别流程

```
用户输入
    ↓
[LLM Intent Service]
    - 纯 LLM 理解
    - 无规则 fallback
    ↓
结构化意图
{
    "intent_type": "...",
    "action_type": "...",
    "target": "...",
    "parameters": {...}
}
    ↓
任务执行
```

---

## 🔧 2. Task Execution (任务执行)

### 能力描述
通过工具系统执行各种任务，从简单的命令到复杂的多步骤操作。

### 核心工具

#### 浏览器操作
```python
✅ open_browser(browser_name, url)
✅ detect_browsers()
✅ list_browsers()
```

#### 终端命令
```python
✅ execute_terminal(command, workdir, timeout)
✅ run_python(code, timeout)
✅ get_system_info()
```

#### 文件操作
```python
✅ read_file(path, encoding)
✅ write_file(path, content, mode)
✅ list_directory(path, recursive)
✅ search_files(directory, pattern)
✅ patch_file(path, operations)
```

#### 网络操作
```python
✅ web_search(query, engine, limit)
✅ fetch_url(url, extract)
✅ web_extract(url, selector)
```

#### 代码处理
```python
✅ execute_code(code, language, timeout)
✅ analyze_code(code, language)
✅ format_json(json_str, indent)
✅ validate_syntax(code, language)
```

---

## 🌐 3. Information Retrieval (信息检索)

### 能力描述
从互联网获取信息和知识。

### 支持的操作

#### 搜索引擎查询
```python
web_search(query, engine="baidu", limit=5)
```

**支持的引擎**:
- 百度 (baidu) - 默认
- Google (google)
- Bing (bing)
- DuckDuckGo (duckduckgo)

#### 网页内容提取
```python
fetch_url(url, extract="text")
```

**提取模式**:
- text - 纯文本
- html - 原始 HTML
- markdown - Markdown 格式
- links - 所有链接

#### 智能搜索
```python
# 搜索 + 提取 + 总结
results = web_search("Python 教程")
content = fetch_url(results[0].url)
summary = llm_summarize(content)
```

---

## 💻 4. Code Processing (代码处理)

### 能力描述
编写、分析和执行代码。

### 支持的语言

| 语言 | 编写 | 执行 | 分析 |
|------|------|------|------|
| Python | ✅ | ✅ | ✅ |
| JavaScript | ✅ | ✅ | ✅ |
| TypeScript | ✅ | ❌ | ✅ |
| Java | ✅ | ❌ | ✅ |
| C/C++ | ✅ | ❌ | ✅ |
| Go | ✅ | ❌ | ✅ |
| Rust | ✅ | ❌ | ✅ |
| Shell | ✅ | ✅ | ✅ |
| PowerShell | ✅ | ✅ | ✅ |
| SQL | ✅ | ❌ | ✅ |

### 代码工具

```python
# 1. 执行代码
execute_code(code, language="python")

# 2. 分析代码
analyze_code(code, language="python")
# 返回: 结构分析、复杂度、潜在问题

# 3. 代码格式化
format_json(json_str, indent=2)
validate_syntax(code, language="python")
```

### 示例

```
用户: 帮我写一个 Python 函数来计算斐波那契数列
Agent:
  生成代码:
  ```python
  def fibonacci(n):
      if n <= 1:
          return n
      return fibonacci(n-1) + fibonacci(n-2)
  ```
  
  可选: 执行代码
  > fibonacci(10)
  55
```

---

## 📁 5. File Operations (文件操作)

### 能力描述
读写、搜索和管理文件系统。

### 支持的操作

#### 读取文件
```python
content = read_file("readme.md")
```

#### 写入文件
```python
write_file("output.txt", "Hello World")
```

#### 目录操作
```python
files = list_directory(".", recursive=True)
```

#### 文件搜索
```python
py_files = search_files("src/", "*.py")
```

#### 文件修改
```python
patch_file("config.json", [
    {"op": "replace", "path": "/key", "value": "new_value"}
])
```

### 权限限制

```
✅ 读取: 用户目录下的文件
✅ 写入: 用户目录下的文件
⚠️ 需要确认: 系统目录
❌ 禁止: 系统关键文件
```

---

## 🎮 6. System Control (系统控制)

### 能力描述
执行系统命令和控制应用程序。

### 支持的操作

#### 启动应用
```python
execute_terminal("start notepad")      # Windows
execute_terminal("open -a Safari")    # macOS
execute_terminal("xdg-open firefox")  # Linux
```

#### 系统命令
```python
execute_terminal("dir")               # Windows
execute_terminal("ls -la")            # Unix
execute_terminal("ps aux")           # 查看进程
```

#### 文件管理器
```python
# 打开特定文件夹
execute_terminal("start explorer shell:desktop")  # 桌面
execute_terminal("start explorer shell:personal")  # 文档
```

### 安全限制

```
❌ 禁止的命令:
   - 格式化磁盘
   - 删除系统文件
   - 修改系统配置 (需确认)
   - 网络攻击工具

⚠️ 需要确认:
   - 安装软件
   - 关机/重启
   - 用户管理
```

---

## 🧩 7. 高级能力 (Advanced Capabilities)

### Multi-Agent Collaboration (多 Agent 协作) [待实现]
- Agent 角色分配
- 任务分解
- 结果汇总

### Memory-Enhanced (增强记忆) [待实现]
- 跨会话记忆
- 用户偏好学习
- 上下文推断

### Tool Chaining (工具链) [待实现]
- 自动工具选择
- 复杂任务分解
- 执行计划生成

---

## ❌ 能力限制

### 当前不支持

| 限制类型 | 说明 | 替代方案 |
|---------|------|----------|
| 实时数据 | 无法获取实时股票、天气 | 使用工具调用 |
| 物理操作 | 无法控制物理设备 | 提供指导 |
| 长时间任务 | 不适合数小时任务 | 建议其他方案 |
| 图像处理 | 有限的图像理解 | 描述图像内容 |
| 音视频 | 无法处理 | 转换后处理 |

### 技术限制

```
1. 上下文窗口: ~4K-128K tokens (取决于 LLM)
2. 执行超时: 默认 60 秒
3. 文件大小: 单文件 < 10MB
4. 并发任务: 单用户 1 个会话
```

---

## 📊 能力矩阵

| 能力域 | 成熟度 | LLM 依赖 | 工具依赖 |
|--------|--------|----------|----------|
| Intent Recognition | ⭐⭐⭐⭐⭐ | 100% | 无 |
| Task Execution | ⭐⭐⭐⭐ | 中等 | 100% |
| Information Retrieval | ⭐⭐⭐⭐ | 低 | 高 |
| Code Processing | ⭐⭐⭐⭐ | 中等 | 中等 |
| File Operations | ⭐⭐⭐⭐⭐ | 低 | 100% |
| System Control | ⭐⭐⭐⭐ | 低 | 100% |

---

## 🎓 能力提升路径

### 短期 (1-2 周)
- [ ] 完善错误处理
- [ ] 增强工具链
- [ ] 添加更多工具

### 中期 (1 个月)
- [ ] 实现 Memory System
- [ ] 添加 Tool Chaining
- [ ] 优化 Intent Recognition

### 长期 (3 个月+)
- [ ] Multi-Agent 支持
- [ ] 跨平台增强
- [ ] 自定义工具加载

---

## 📝 使用示例

### 示例 1: 复杂任务

```
用户: 帮我搜索最新的 AI 新闻，保存到文件，然后在浏览器打开

Agent:
  步骤 1:
    工具: web_search(query="最新 AI 新闻", limit=10)
    结果: 获取新闻列表
  
  步骤 2:
    工具: write_file(
        path="ai_news.txt",
        content=格式化后的新闻内容
    )
    结果: 已保存到文件
  
  步骤 3:
    工具: open_browser(
        url="https://www.google.com/search?q=最新AI新闻"
    )
    结果: 已打开浏览器
  
  完成: 所有任务已执行
```

### 示例 2: 代码开发

```
用户: 写一个 Python 程序来处理 CSV 文件，然后运行它

Agent:
  步骤 1:
    工具: analyze_code(分析需求)
    结果: 确定实现方案
  
  步骤 2:
    生成代码:
    ```python
    import csv
    
    def process_csv(file_path):
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                print(row)
    ```
  
  步骤 3:
    工具: execute_code(code=上面代码, language="python")
    结果: 程序执行成功
  
  完成: 代码已编写并执行
```

---

## 📌 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2026-05-25 | 初始版本，定义完整能力清单 |

---

## 🔗 相关文档

- [agent.md](agent.md) - Agent 角色定义
- [memory.md](memory.md) - 记忆系统定义
- [tools.md](tools.md) - 工具使用规范
- [../docs/llm_intent_architecture.md](../docs/llm_intent_architecture.md) - LLM 意图识别架构
- [../advanced_reasoning/multi_agent.py](../advanced_reasoning/multi_agent.py) - 多 Agent 协作 [待实现]