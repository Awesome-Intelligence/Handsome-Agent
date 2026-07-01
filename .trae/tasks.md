# Tasks

## Pinned 技能保护功能

### Task 1.1: 修改 SkillMetadata 数据结构
- [x] 在 SkillMetadata dataclass 中新增以下字段
  - `pinned: bool = False` - 是否固定
  - `pinned_at: Optional[str] = None` - 固定时间戳
  - `pinned_by: str = ""` - 固定操作者
- 状态: ✅ 完成

### Task 1.2: 实现 pin_skill / unpin_skill 方法
- [x] 添加 `pin_skill(self, skill_id: str, pinned_by: str = "user") -> bool` 方法
- [x] 添加 `unpin_skill(self, skill_id: str) -> bool` 方法
- 状态: ✅ 完成

### Task 1.3: 修改 unregister_skill 添加安全检查
- [x] 修改 `unregister_skill` 方法，添加 `force: bool = False` 参数
- [x] 在删除前检查 pinned 状态
- [x] 如果 pinned=True 且 force=False，抛出 PermissionError
- 状态: ✅ 完成

### Task 1.4: 实现 list_pinned_skills 方法
- [x] 添加 `list_pinned_skills(self) -> List[SkillMetadata]` 方法
- [x] 添加 `is_pinned(self, skill_id: str) -> bool` 方法
- 状态: ✅ 完成

## 跨 Profile 技能管理

### Task 4.1: 扩展配置支持 Profile
- [x] 在 `common/config.py` 中添加以下函数:
  - `get_profiles_dir()` - 获取 profiles 目录
  - `get_current_profile()` - 获取当前 profile (支持环境变量 HANDSOME_PROFILE 和符号链接)
  - `get_profile_skills_dir(profile)` - 获取指定 profile 的技能目录
  - `get_profile_dir(profile)` - 获取指定 profile 的配置目录
- 状态: ✅ 完成

### Task 4.2: 修改 SkillManager 支持 Profile
- [x] 修改 `SkillManager.__init__` 构造函数添加 `profile` 参数
- [x] 添加 `profile` 和 `skills_dir` 属性
- [x] 修改 `import_skill_from_directory_structure` 方法使用 profile 技能目录
- 状态: ✅ 完成

### Task 4.3: 添加 Profile CLI 命令
- [x] 在 `cli/_parser.py` 的 `skills` 命令中添加 `--profile` 参数
- [x] 更新 `cmd_skills_list` 函数支持 profile 参数
- [x] 更新 `list_skills` 函数接受 profile 参数并显示 profile 信息
- 状态: ✅ 完成

## Bundle CLI 命令支持

### Task 3.3: 实现 BundleCommands 类
- [x] 创建 `cli/cli_commands/bundle.py` 模块
- [x] 实现 `BundleCommands` 类处理命令
- [x] 使用 `agent.skills.skill_bundle.SkillBundleManager`
- 状态: ✅ 完成

### Task 3.4: 添加 bundle 子命令
- [x] 添加 `bundle list` 命令 - 列出所有技能包
- [x] 添加 `bundle create <name> <skills...>` 命令 - 创建新的技能包
- [x] 添加 `bundle delete <name>` 命令 - 删除技能包
- [x] 添加 `bundle info <name>` 命令 - 查看技能包详情
- [x] 在 `_parser.py` 中注册子命令解析器
- [x] 在 `main.py` 中添加命令处理器
- 状态: ✅ 完成

### Task 3.5: 更新帮助文档和示例
- [x] 输出格式清晰美观（使用 Emoji 符号）
- [x] 完善的错误处理
- [x] 交互式确认删除操作
- 状态: ✅ 完成

---

## 技能内容修补功能

### Task 2.1: 模糊匹配模块
- [x] 实现 fuzzy_match.py 模块
- [x] 提供 fuzzy_find_and_replace 函数
- 状态: ✅ 完成

### Task 2.1.1: 模糊匹配单元测试
- [x] 创建 `tests/unit/agent/test_fuzzy_match.py`
- [x] 测试精确匹配功能
- [x] 测试空白符规范化
- [x] 测试缩进差异容忍
- [x] 测试匹配失败场景
- [x] 测试全部替换功能
- 状态: ✅ 完成

### Task 2.2: 实现 patch_skill 方法
- [x] 在 SkillManager 类中添加 `patch_skill` 方法
- [x] 支持精确匹配和模糊匹配
- [x] 支持 replace_all 参数
- [x] 使用原子写入确保文件安全
- [x] 返回详细的操作结果
- 状态: ✅ 完成

### Task 2.3: 集成 fuzzy_match 模块
- [x] 在 skill_manager.py 中导入 fuzzy_match.py
- [x] patch_skill 方法调用 fuzzy_find_and_replace
- 状态: ✅ 完成

## Bundle 单元测试

### Task 5.3: 创建 Bundle 单元测试
- [x] 创建 `tests/unit/agent/test_skill_bundle.py` 测试文件
- [x] 实现 create_bundle 测试
- [x] 实现 load_bundle 测试
- [x] 实现 delete_bundle 测试
- [x] 实现 list_bundles 测试
- [x] 实现 _slugify 测试
- [x] 实现 get_bundle_info 测试
- [x] 添加集成测试
- 状态: ✅ 完成

### Task 5.1: 创建 Pinned 功能单元测试
- [x] 创建 `tests/unit/agent/test_skill_pinned.py` 测试文件
- [x] 实现 test_pin_skill 测试
- [x] 实现 test_unpin_skill 测试
- [x] 实现 test_delete_pinned_skill_fails 测试
- [x] 实现 test_delete_pinned_skill_with_force 测试
- [x] 实现 test_list_pinned_skills 测试
- [x] 实现 test_is_pinned 测试
- 状态: ✅ 完成

### Task 5.4: 创建 Profile 功能集成测试
- [x] 创建 `tests/integration/test_profile_skills.py` 测试文件
- [x] 实现 test_get_profiles_dir 测试
- [x] 实现 test_get_current_profile 测试
- [x] 实现 test_get_profile_skills_dir 测试
- [x] 实现 test_skill_manager_profile_isolation 测试
- [x] 实现 test_profile_switch 测试（通过环境变量）
- [x] 添加多个 Profile 技能目录隔离测试
- [x] 添加 Profile 列表操作测试
- 状态: ✅ 完成