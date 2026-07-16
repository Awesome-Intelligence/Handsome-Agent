# 意图识别系统配置指南

> ⚠️ **已废弃**: 此文档仅供参考。意图识别层已在 v2.0 中完全移除，不再使用 `config/intents.yaml`。

## 📋 概述

Agent-Z 支持三种意图识别模式：

1. **Keyword 模式** - 仅使用关键词匹配（快速但不智能）
2. **LLM 模式** - 仅使用大语言模型（智能但需要 API）
3. **Hybrid 模式** - 混合模式（关键词优先，LLM 辅助，**推荐生产环境使用**）

## 🔧 配置文件位置

```
config/intents.yaml
```

## 📝 配置文件结构

### 1. 意图关键词配置

每个意图（intent）包含：

```yaml
intents:
  <intent_name>:
    keywords:
      - keyword1
      - keyword2
      - ...
    priority: <数字越小优先级越高>
    description: "意图描述"
```

**示例**：

```yaml
intents:
  conversation:
    keywords:
      - hello
      - 你好
      - 嗨
    priority: 1
    description: "问候、寒暄、闲聊对话"
```

### 2. 意图识别配置

```yaml
intent_classification:
  # 模式选择
  mode: "hybrid"  # keyword | llm | hybrid
  
  # 置信度阈值（仅 hybrid 模式）
  confidence_threshold: 0.3
  
  # 是否启用详细日志
  enable_detailed_logs: true
  
  # 默认语言
  default_language: "zh"
```

## 🎯 如何选择模式

### 模式对比

| 模式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **keyword** | 快速、无需 API | 不够智能 | 简单场景、离线环境 |
| **llm** | 智能、语义理解 | 需要 API、可能有延迟 | 有 API 预算的场景 |
| **hybrid** | 平衡速度和智能 | 配置稍复杂 | **生产环境推荐** |

### 推荐配置

#### 开发/测试环境
```yaml
intent_classification:
  mode: "keyword"
  enable_detailed_logs: true
```

#### 生产环境（有 LLM API）
```yaml
intent_classification:
  mode: "hybrid"
  confidence_threshold: 0.3
  enable_detailed_logs: false
```

#### 生产环境（无 LLM API）
```yaml
intent_classification:
  mode: "keyword"
  enable_detailed_logs: false
```

## 📖 添加自定义意图

### 步骤 1：编辑配置文件

在 `config/intents.yaml` 中添加新意图：

```yaml
intents:
  # ... 其他意图 ...
  
  # 自定义意图示例：音乐控制
  music_control:
    keywords:
      - 播放音乐
      - 暂停
      - 下一首
      - 上一首
      - 播放
      - pause
      - next
      - previous
      - play music
    priority: 3
    description: "音乐播放控制"
```

### 步骤 2：添加处理器

在 `core/router_handlers.py` 中添加对应的处理器：

```python
@route_handler(
    'music_control',
    'Music Control Handler',
    'Handles music playback control',
    keywords=['播放音乐', '暂停', '下一首', 'play music', 'pause', 'next'],
    intent_types=['music_control'],
    priority=3
)
async def music_control_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    # 实现音乐控制逻辑
    pass
```

### 步骤 3：重启服务

修改配置后需要重启 Agent 服务。

## 🔍 测试意图识别

### 方法 1：查看日志

启动 Agent 时启用详细日志：

```bash
python cli.py --debug
```

日志中会显示：

```
关键词分类: file_operation (置信度: 0.45)
```

### 方法 2：编写测试脚本

```python
from core.router import IntentClassifier

# 创建分类器（会自动加载 config/intents.yaml）
classifier = IntentClassifier()

# 测试
test_inputs = [
    "查看桌面文件",
    "今天天气怎么样",
    "帮我写一段Python代码"
]

for text in test_inputs:
    intent = classifier.classify(text)
    print(f"输入: {text}")
    print(f"意图: {intent}")
    print("-" * 50)
```

## 💡 自定义提示词模板

在 hybrid 或 llm 模式下，可以自定义 LLM 提示词：

```yaml
intent_classification:
  mode: "hybrid"
  llm_prompt_template: |
    你是一个意图分类专家。

    可用的意图类型：
    {intents_list}

    用户输入："{user_input}"

    请返回最匹配的意图类型名称。
    如果是打开应用或运行程序，分类为 "terminal"。
    如果不确定，分类为 "conversation"。
```

**模板变量**：
- `{intents_list}` - 意图列表描述
- `{user_input}` - 用户输入文本

## 🛠️ 高级配置

### 调整置信度阈值

**阈值含义**：
- `0.0` - 所有输入都经过 LLM 分类
- `1.0` - 所有输入都使用关键词分类
- `0.3` - 关键词匹配度 < 30% 时调用 LLM

**调整建议**：
- 如果误识别多 → 提高阈值（如 0.4）
- 如果 LLM 调用太多 → 降低阈值（如 0.2）

### 多语言支持

修改默认语言：

```yaml
intent_classification:
  default_language: "en"
```

支持的的语言：`zh`（中文）、`en`（英文）、`ja`（日语）、`ko`（韩语）

## ⚠️ 注意事项

1. **关键词冲突**：避免在不同意图间使用相同的关键词
2. **优先级**：数字越小优先级越高，相同关键词可能匹配多个意图
3. **性能**：关键词匹配非常快（< 1ms），LLM 调用较慢（100-500ms）
4. **成本**：LLM 模式会产生 API 调用费用

## 📚 相关文档

- [架构设计文档](ARCHITECTURE.md) - 了解整体架构
- [路由处理器文档](router_handlers.md) - 了解如何添加自定义处理器
- [技能系统文档](../skills/README.md) - 了解技能注册和使用
