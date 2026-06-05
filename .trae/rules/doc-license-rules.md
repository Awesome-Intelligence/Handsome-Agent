---
alwaysApply: false
description: |
  开源与许可证规范 - 适用于以下场景自动加载：
  - 引入新的开源组件或依赖
  - 审查许可证兼容性
  - 编写 DEPENDENCIES.md 或 NOTICE 文件
  - 编写代码许可证头注释

  如涉及许可证要求、依赖审查等，请查阅此规范。
---

# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

被加载时，输出："许可证规则生效！！！"

## 一、开源组件使用要求

> **强制要求**: 使用任何开源组件前必须审查其许可证。

### 1.1 许可证兼容矩阵

| 许可证类型 | 商业使用 | 修改源码 | 分发开源 | 示例 |
|------------|---------|----------|---------|------|
| **MIT** | ✓ | ✓ | ✓ | React, Rails |
| **Apache 2.0** | ✓ | ✓ | ✓ | Android, Spring |
| **BSD 3-Clause** | ✓ | ✓ | ✓ | NumPy |
| **GPL v3** | ⚠️ 需要许可 | ✗ | ✗ | GCC |
| **AGPL v3** | ✗ | ✗ | ✗ | MongoDB |
| **闭源** | ✗ | ✗ | ✗ | 商业库 |

### 1.2 推荐许可证优先级

1. **首选**: MIT, Apache 2.0, BSD 3-Clause
2. **可选**: Python (PSF), CC BY
3. **禁止**: GPL v3, AGPL v3, 闭源组件

---

## 二、依赖审查流程

```
1. 引入新依赖
   ↓
2. 检查许可证类型 (使用 pip-audit, license-check)
   ↓
3. 评估许可证兼容性
   ↓
4. 记录到 DEPENDENCIES.md
   ↓
5. 更新 pyproject.toml / package.json
```

---

## 三、必需文件

| 文件 | 内容 | 更新时机 |
|------|------|----------|
| `LICENSE` | 项目主许可证 | 每次发布 |
| `NOTICE` | 第三方组件版权声明 | 每次添加依赖 |
| `DEPENDENCIES.md` | 依赖列表（含许可证） | 添加/移除依赖时 |

---

## 四、许可证头模板

### 4.1 Python 文件

```python
# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件
```

### 4.2 TypeScript 文件

```typescript
/**
 * Copyright (c) 2026 Handsome Agent Contributors
 *
 * 本项目采用 MIT 许可证开源
 * 详细信息请参见 LICENSE 文件
 */
```

---

*本文档版本: v2.0.0 | 最后更新: 2026-06-05*