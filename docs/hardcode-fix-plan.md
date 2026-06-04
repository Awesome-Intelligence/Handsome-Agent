# 硬编码修复计划

> 生成时间：2026-06-04
> 总违规数：460 处

---

## 阶段划分

### 阶段一：意图理解硬编码修复（🧠 高优先级）
**影响**：违反核心业务规则，AI 可能被硬编码关键词误导

| 批次 | 文件 | 违规数 | 修复策略 |
|------|------|--------|----------|
| 1.1 | `agent/context/token_estimator.py` | ~25 | 检查 Token 估算逻辑，保留合理逻辑 |
| 1.2 | `agent/rails/task_event_rail.py` | ~8 | 改为 LLM 判断或移除 |
| 1.3 | `agent/task/todo_event_rail.py` | ~6 | 改为 LLM 判断或移除 |
| 1.4 | `agent/tool_selector/llm_tool_selector.py` | ~25 | 保留工具选择器逻辑，移除误报 |
| 1.5 | `agent/skills/skill_manager.py` | ~20 | 检查并改为 LLM 或配置驱动 |
| 1.6 | `common/redact.py` 第 286 行 | ~1 | 检查脱敏逻辑 |
| 1.7 | `agent/memory/markdown_memory.py` | ~5 | 检查记忆处理逻辑 |
| 1.8 | `agent/memory/memory_manager.py` | ~2 | 检查记忆管理逻辑 |
| 1.9 | `agent/memory/memory_system.py` | ~2 | 检查记忆系统逻辑 |
| 1.10 | 其他零散文件 | ~10 | 逐一检查 |

**阶段一预估**：100+ 处 → 预期修复 60-80 处

---

### 阶段二：路径硬编码修复（📁 中优先级）
**影响**：Windows 兼容性问题，需迁移到 `pathlib.Path`

| 批次 | 文件 | 违规数 | 修复策略 |
|------|------|--------|----------|
| 2.1 | `agent/task/task_logger.py` | ~30 | 使用 `pathlib.Path` |
| 2.2 | `agent/context/compression_commands.py` | ~5 | 使用 `pathlib.Path` |
| 2.3 | `agent/context/compression_config.py` | ~2 | 使用 `pathlib.Path` |
| 2.4 | `agent/context/context_builder.py` | ~3 | 使用 `pathlib.Path` |
| 2.5 | `agent/context/context_compressor.py` | ~8 | 使用 `pathlib.Path` |
| 2.6 | `agent/context/token_estimator.py` | ~2 | 使用 `pathlib.Path` |
| 2.7 | `common/redact.py` | ~6 | 使用 `pathlib.Path` |
| 2.8 | `gateway/server.py` | ~2 | 使用 `pathlib.Path` |
| 2.9 | `gateway/adapters/cli_adapter.py` | ~4 | 使用 `pathlib.Path` |
| 2.10 | `skills/loader.py` | ~6 | 使用 `pathlib.Path` |
| 2.11 | `skills/merger.py` | ~4 | 使用 `pathlib.Path` |
| 2.12 | `tools/file_tools.py` | ~8 | 使用 `pathlib.Path` |
| 2.13 | `tools/file_tools_bridge.py` | ~6 | 使用 `pathlib.Path` |
| 2.14 | `tools/memory_tool.py` | ~3 | 使用 `pathlib.Path` |
| 2.15 | `tools/skills_tool.py` | ~6 | 使用 `pathlib.Path` |
| 2.16 | `tools/checkpoint_manager.py` | ~4 | 使用 `pathlib.Path` |
| 2.17 | `tools/tool_calling.py` | ~2 | 使用 `pathlib.Path` |
| 2.18 | `tools/web_tools.py` | ~4 | 使用 `pathlib.Path` |
| 2.19 | `tools/integrated_tools.py` | ~2 | 使用 `pathlib.Path` |
| 2.20 | `tools/code_tools.py` | ~1 | 使用 `pathlib.Path` |
| 2.21 | `tools/todo_tool.py` | ~1 | 使用 `pathlib.Path` |
| 2.22 | `agent/curator/*.py` | ~6 | 使用 `pathlib.Path` |
| 2.23 | `agent/rails/manager.py` | ~2 | 使用 `pathlib.Path` |
| 2.24 | `agent/react/*.py` | ~3 | 使用 `pathlib.Path` |
| 2.25 | `agent/task/todo_toolkit.py` | ~8 | 使用 `pathlib.Path` |
| 2.26 | `agent/task/task_middleware.py` | ~2 | 使用 `pathlib.Path` |
| 2.27 | `agent/task/task_planner.py` | ~2 | 使用 `pathlib.Path` |
| 2.28 | `agent/task/task_executor.py` | ~3 | 使用 `pathlib.Path` |
| 2.29 | `agent/llm/providers/*.py` | ~12 | 使用 `pathlib.Path` |
| 2.30 | `agent/a2a/*.py` | ~2 | 使用 `pathlib.Path` |
| 2.31 | `agent/acp/*.py` | ~4 | 使用 `pathlib.Path` |

**阶段二预估**：150+ 处 → 预期修复 120-140 处

---

### 阶段三：误报优化与白名单（⚙️ 配置完善）
**说明**：优化检测脚本，减少误报

| 批次 | 任务 | 说明 |
|------|------|------|
| 3.1 | 路径检测优化 | 区分合法路径（如 URL 中的 `\`）和真正硬编码 |
| 3.2 | 前缀检测优化 | 保留工具前缀判断等合法场景 |
| 3.3 | 添加白名单 | `scripts/pre_commit_check.py` 忽略合理的硬编码 |
| 3.4 | 规则细化 | 区分 `startswith(".")` 和 `startswith("关键词")` |

**阶段三预估**：减少 100-150 处误报

---

## 执行建议

### 每周修复节奏
```
第 1 周：阶段一 批次 1.1 - 1.3（意图硬编码 40 处）
第 2 周：阶段一 批次 1.4 - 1.6（意图硬编码 40 处）
第 3 周：阶段一 批次 1.7 - 1.10 + 阶段三（意图硬编码收尾 + 误报优化）
第 4 周：阶段二 批次 2.1 - 2.10（路径硬编码 80 处）
第 5 周：阶段二 批次 2.11 - 2.20（路径硬编码 60 处）
第 6 周：阶段二 批次 2.21 - 2.31（路径硬编码收尾 30 处）
```

### 修复原则
1. **意图硬编码**：优先使用 LLM 替代，或移至配置
2. **路径硬编码**：使用 `Path()` 或 `pathlib.Path`
3. **误报处理**：在 `pre_commit_check.py` 添加忽略规则

### 验收标准
- [ ] 每批次修复后运行 `python scripts/pre_commit_check.py` 验证
- [ ] 原有测试用例通过
- [ ] 违规数逐步下降

---

## 进度追踪

| 阶段 | 开始时间 | 完成时间 | 剩余违规数 |
|------|----------|----------|-----------|
| 阶段一 | - | - | ~460 |
| 阶段二 | - | - | ~300 |
| 阶段三 | - | - | ~150 |
| 完成 | - | - | 0 |

---

> ⚠️ 注意：460 处违规中相当部分是 Windows 路径硬编码，在跨平台场景下需要修复，同一路径下多个硬编码可一次性批量替换。