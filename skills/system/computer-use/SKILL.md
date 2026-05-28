---
name: computer-use
description: "系统操作技能：打开文件夹、浏览器、应用程序等"
version: 1.0.0
author: Handsome Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [system, computer, file, browser, folder, open]
    related_skills: [terminal]
---

# 系统操作技能

提供常用的系统操作功能，如打开文件夹、浏览器、应用程序等。

## 快速参考

| 操作 | 说明 |
|------|------|
| 打开文件夹 | `open_folder(path="路径")` |
| 打开浏览器 | `open_browser(url="网址")` |
| 列出浏览器 | `list_browsers()` |
| 获取系统信息 | `get_system_info()` |

## 使用示例

### 打开文件夹

```bash
# 打开当前目录
open_folder()

# 打开指定目录
open_folder(path="~/Documents")
open_folder(path="D:\Projects")
```

### 打开浏览器

```bash
# 打开默认浏览器
open_browser()

# 打开指定网址
open_browser(url="https://baidu.com")

# 使用指定浏览器打开
open_browser(url="https://google.com", browser="chrome")
```

### 获取系统信息

```bash
# 获取所有系统信息
get_system_info()

# 获取特定信息
get_system_info(info_type="cpu")
get_system_info(info_type="memory")
get_system_info(info_type="disk")
```

## 参数说明

### open_folder
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 否 | 文件夹路径，默认为当前目录 |

### open_browser
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 否 | 要访问的网址 |
| browser | string | 否 | 浏览器名称 (chrome/edge/firefox) |

### get_system_info
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| info_type | string | 否 | 信息类型: os/cpu/memory/disk/all |

## 支持的浏览器

- Chrome
- Edge
- Firefox
- Brave
- Opera
- Vivaldi

## 相关技能

- `terminal` - 执行终端命令
