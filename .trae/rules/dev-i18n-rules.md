---
alwaysApply: false
description: |
  多语言国际化 (i18n) 规范 - 适用于以下场景自动加载：
  - 设计或实现用户界面文本
  - 添加新的用户可见消息或提示
  - 修改现有文本内容
  - 添加新的语言支持
  - 审查文本硬编码问题

  如涉及多语言文本处理、语言切换、国际化和本地化等，请查阅此规范。
---

# Copyright (c) 2026 Agent-Z Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："多语言国际化规则生效！！！"

---

## 一、强制约束 ⭐

| 约束 | 违规表现 | 正确做法 |
|------|---------|---------|
| 禁止文本硬编码 | `return "你好"` | 使用 `i18n.t("greeting.hello")` |
| 禁止语言判断硬编码 | `if lang == "zh"` | 使用 i18n 模块 |
| 文本必须可配置 | 静态文本直接写代码 | 外部化到语言资源文件 |
| UI 文本必须支持 RTL | 假设左到右布局 | 使用 CSS logical properties |
| 新增翻译键 | 只在一个语言文件添加 | **所有语言文件同步添加** |
| 禁止修改 i18n 架构 | 自行实现新的 i18n 模块 | 使用 `common/i18n.py` |

---

## 二、现有实现架构

> **重要**: Handsome Agent 已使用 `common/i18n.py` 实现多语言支持，禁止自行实现新的 i18n 模块。

### 2.1 核心模块

- **模块位置**: `common/i18n.py`
- **导出接口**: `i18n.t()`, `t()`, `get_language()`, `I18n` 类
- **支持语言**: `zh`, `en`, `ja`, `ko`
- **默认语言**: `zh`（中文）

### 2.2 存储位置

```
common/
├── i18n.py              # 核心模块（禁止修改架构）
└── locales/
    ├── en.yaml          # 英语（基准语言）
    ├── zh.yaml          # 中文
    ├── ja.yaml          # 日语
    └── ko.yaml          # 韩语
```

**命名规范**：
- 文件名：`ISO 639-1` 小写 + `.yaml`
- 嵌套键使用点号分隔（如 `setup.banner.title`）
- 值使用 `{placeholder}` 作为 `str.format` 占位符

### 2.3 语言检测优先级

1. 显式参数：`t(key, lang="en")`
2. 环境变量：`HERMES_LANGUAGE` 或 `HANDSOME_LANGUAGE`
3. 配置文件：`~/.handsome_agent/config.json` 的 `language` 字段
4. 默认语言：`zh`

### 2.4 回退机制

```
目标语言 → 默认语言(zh) → 原始键
```

### 2.5 语言别名

| 别名 | 映射到 |
|------|--------|
| `chinese`, `mandarin`, `zh-cn` | `zh` |
| `english`, `en-us`, `en-gb` | `en` |
| `japanese`, `jp` | `ja` |
| `korean`, `한국어` | `ko` |

---

## 三、代码规范

### 3.1 文本获取

```python
# ✅ 正确：使用 i18n 模块
from common.i18n import i18n, t, I18n, get_language

# 方法 1：使用全局实例（推荐）
message = i18n.t("setup.banner.title", name="Xiao Ming")

# 方法 2：使用函数
message = t("setup.banner.title", name="Xiao Ming")

# 方法 3：指定语言
message = t("greeting.hello", lang="en", name="Xiao Ming")

# 方法 4：使用 I18n 类
i18n_instance = I18n("zh")
message = i18n_instance.t("greeting.hello", name="小明")

# 获取当前语言
current_lang = get_language()

# ❌ 错误：禁止硬编码
return "你好"  # ❌
return f"共 {n} 个项目"  # ❌
```

### 3.2 占位符规范

| 类型 | 语法 | 示例 |
|------|------|------|
| 命名参数 | `{name}` | `"你好，{name}！"` |
| 默认值 | `{name:游客}` | `"你好，{name:游客}！"` |

### 3.3 格式化数字

```python
# ✅ 正确：使用 Python 格式化
price = 1234.56
message = f"{i18n.t('cart.price')} ¥{price:,.2f}"
```

### 3.4 动态语言切换

```python
# ✅ 正确：创建 I18n 实例
i18n_zh = I18n("zh")
i18n_en = I18n("en")

# ❌ 错误：禁止全局状态切换
# 不推荐：set_locale("en") 会影响全局状态
```

---

## 四、YAML 目录文件规范

### 4.1 文件结构

```yaml
# 注释说明用途
setup:
  banner:
    title: "◆ Handsome Agent 设置向导 ◆"
    subtitle: "你的全能 AI 助手"
  language:
    title: "🌐 语言设置"
    prompt: "请选择显示语言："
    selected: "语言已设置为 {language}"
```

### 4.2 添加新键的规则

> **强制**: 新增翻译键时，必须在 **所有语言文件** 中同步添加。

```bash
# 添加新键的流程
1. 在 en.yaml 添加英文原文
2. 在 zh.yaml 添加中文翻译
3. 在 ja.yaml 添加日文翻译
4. 在 ko.yaml 添加韩文翻译
5. 同步提交所有文件
```

### 4.3 命名空间建议

| 命名空间 | 用途 | 示例 |
|----------|------|------|
| `setup.*` | 设置向导 | setup.banner.title |
| `llm.*` | 大模型配置 | llm.title |
| `errors.*` | 错误消息 | errors.server_internal |
| `common.*` | 通用文本 | common.yes_no_yes |

---

## 五、可扩展性要求

### 5.1 添加新语言

1. 在 `common/locales/` 创建语言文件（如 `fr.yaml`）
2. 参考 `en.yaml` 结构添加翻译
3. 更新 `common/i18n.py` 中的 `SUPPORTED_LANGUAGES` 元组
4. 确保回退机制正常工作

### 5.2 RTL 语言支持

```css
/* ✅ 正确：使用 logical properties */
.container {
  margin-inline-start: 1rem;  /* 而不是 margin-left */
  padding-inline-end: 1rem;  /* 而不是 padding-right */
}

.text {
  text-align: start;  /* 而不是 text-align: left */
}

/* ❌ 错误：硬编码方向 */
.container {
  margin-left: 1rem;  # ❌ 不支持 RTL
}
```

---

## 六、测试要求

### 6.1 翻译完整性测试

```python
def test_all_keys_translated():
    """验证所有语言包含相同的键"""
    from common.i18n import SUPPORTED_LANGUAGES
    from pathlib import Path

    locales_dir = Path(__file__).parent.parent / "common" / "locales"
    en_keys = set(load_yaml(locales_dir / "en.yaml").keys())

    for lang in SUPPORTED_LANGUAGES:
        if lang == "en":
            continue
        lang_keys = set(load_yaml(locales_dir / f"{lang}.yaml").keys())
        missing = en_keys - lang_keys
        assert not missing, f"Missing keys in {lang}: {missing}"
```

### 6.2 运行时语言切换测试

```python
def test_locale_switch():
    """验证语言切换正常工作"""
    from common.i18n import I18n

    for lang in ["zh", "en", "ja", "ko"]:
        i18n_instance = I18n(lang)
        assert i18n_instance.get_language() == lang
```

---

## 七、自检清单

- [ ] 无用户可见文本硬编码
- [ ] 所有文本通过 `i18n.t()` 或 `t()` 获取
- [ ] 占位符格式统一且正确
- [ ] 新增键已添加到所有语言文件
- [ ] 翻译结构完整（YAML 嵌套 + 点号键）
- [ ] 支持 RTL 语言布局（CSS logical properties）
- [ ] 回退机制正常工作

---

## 八、常见错误示例

```python
# ❌ 错误：硬编码中文
def get_error_message():
    return "服务器内部错误"

# ✅ 正确：使用翻译
def get_error_message():
    return i18n.t("errors.server_internal")

# ❌ 错误：硬编码语言判断
def greet_user(user):
    if user.lang == "zh":
        return f"欢迎, {user.name}"
    else:
        return f"Welcome, {user.name}"

# ✅ 正确：使用翻译
def greet_user(user):
    user_i18n = I18n(user.lang)
    return user_i18n.t("greeting.welcome", name=user.name)

# ❌ 错误：拼接文本
def format_price(price):
    return "价格: ¥" + str(price)

# ✅ 正确：使用翻译 + 格式化
def format_price(price):
    return f"{i18n.t('cart.price')} ¥{price:,.2f}"
```

---

*本文档版本: v1.0.0 | 最后更新: 2026-06-05*
