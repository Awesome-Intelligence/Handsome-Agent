#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n 模块测试脚本
验证 Handsome Agent 多语言实现的功能
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_import():
    """测试 i18n 模块导入"""
    print("=" * 60)
    print("测试 1: 模块导入")
    print("=" * 60)
    
    try:
        from common.i18n import (
            t, i18n, I18n, get_language, 
            SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE,
            reset_language_cache
        )
        print(f"✅ 导入成功")
        print(f"   - 支持的语言: {SUPPORTED_LANGUAGES}")
        print(f"   - 默认语言: {DEFAULT_LANGUAGE}")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_basic_translation():
    """测试基础翻译功能"""
    print("\n" + "=" * 60)
    print("测试 2: 基础翻译功能")
    print("=" * 60)
    
    from common.i18n import t, I18n
    
    test_cases = [
        ("setup.banner.title", None, "setup banner title"),
        ("setup.language.title", None, "setup language title"),
        ("cli.welcome", None, "cli welcome"),
        ("menu.root.title", None, "menu root title"),
    ]
    
    all_passed = True
    for key, lang, description in test_cases:
        result = t(key, lang=lang)
        status = "✅" if result != key else "❌"
        print(f"   {status} {description}: '{result}'")
        if result == key:
            all_passed = False
    
    return all_passed


def test_language_switch():
    """测试语言切换"""
    print("\n" + "=" * 60)
    print("测试 3: 语言切换")
    print("=" * 60)
    
    from common.i18n import t, I18n, SUPPORTED_LANGUAGES
    
    key = "setup.banner.title"
    
    all_passed = True
    for lang in SUPPORTED_LANGUAGES:
        result = t(key, lang=lang)
        status = "✅" if result != key else "❌"
        print(f"   {status} {lang}: '{result}'")
        if result == key:
            all_passed = False
    
    return all_passed


def test_placeholder():
    """测试占位符替换"""
    print("\n" + "=" * 60)
    print("测试 4: 占位符替换")
    print("=" * 60)
    
    from common.i18n import t
    
    test_cases = [
        ("setup.language.selected", {"language": "English"}, None, "language selected"),
        ("setup.llm.api_key_masked", {"prefix": "sk-", "suffix": "1234"}, None, "api key masked"),
        ("setup.questions.out_of_range", {"max": "10"}, None, "out of range"),
    ]
    
    all_passed = True
    for key, kwargs, lang, description in test_cases:
        result = t(key, lang=lang, **kwargs)
        status = "✅" if result != key else "❌"
        print(f"   {status} {description}: '{result}'")
        if result == key:
            all_passed = False
    
    return all_passed


def test_language_alias():
    """测试语言别名"""
    print("\n" + "=" * 60)
    print("测试 5: 语言别名解析")
    print("=" * 60)
    
    from common.i18n import I18n, _normalize_lang
    
    aliases = [
        ("chinese", "zh"),
        ("english", "en"),
        ("japanese", "ja"),
        ("korean", "ko"),
        ("zh-CN", "zh"),
        ("en-US", "en"),
        ("中文", "zh"),  # 注意：这个可能不工作
    ]
    
    all_passed = True
    for alias, expected in aliases:
        result = _normalize_lang(alias)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{alias}' -> '{result}' (expected: '{expected}')")
        if result != expected:
            all_passed = False
    
    return all_passed


def test_fallback():
    """测试回退机制"""
    print("\n" + "=" * 60)
    print("测试 6: 回退机制")
    print("=" * 60)
    
    from common.i18n import t
    
    # 测试不存在的键是否回退到默认值
    nonexistent_key = "nonexistent.key.test"
    result = t(nonexistent_key, lang="en")
    print(f"   不存在的键 'nonexistent.key.test' -> '{result}'")
    
    # 测试非默认语言缺失时回退到默认语言
    # zh.yaml 有这个键但 ja.yaml 可能没有
    key = "setup.banner.title"
    result_ja = t(key, lang="ja")
    result_zh = t(key, lang="zh")
    print(f"   回退测试: ja='{result_ja}', zh='{result_zh}'")
    
    return True


def test_i18n_class():
    """测试 I18n 类"""
    print("\n" + "=" * 60)
    print("测试 7: I18n 类")
    print("=" * 60)
    
    from common.i18n import I18n
    
    all_passed = True
    
    # 测试创建不同语言的实例
    for lang in ["zh", "en", "ja", "ko"]:
        i18n_instance = I18n(lang)
        result = i18n_instance.t("setup.banner.title")
        status = "✅" if result != "setup.banner.title" else "❌"
        print(f"   {status} I18n('{lang}').t('setup.banner.title'): '{result}'")
        if result == "setup.banner.title":
            all_passed = False
    
    # 测试获取支持的语言
    supported = I18n.get_supported_languages()
    print(f"   ✅ 支持的语言列表: {supported}")
    
    return all_passed


def test_yaml_structure():
    """测试 YAML 文件结构"""
    print("\n" + "=" * 60)
    print("测试 8: YAML 文件结构")
    print("=" * 60)
    
    from common.i18n import _load_catalog, SUPPORTED_LANGUAGES
    from pathlib import Path
    
    locales_dir = Path(__file__).parent.parent / "common" / "locales"
    
    all_passed = True
    
    for lang in SUPPORTED_LANGUAGES:
        yaml_path = locales_dir / f"{lang}.yaml"
        catalog = _load_catalog(lang)
        
        exists = yaml_path.exists()
        has_keys = len(catalog) > 0
        
        status = "✅" if (exists and has_keys) else "❌"
        print(f"   {status} {lang}.yaml: exists={exists}, keys={len(catalog)}")
        
        if not (exists and has_keys):
            all_passed = False
    
    return all_passed


def test_legacy_translations():
    """测试内嵌翻译（legacy translations）"""
    print("\n" + "=" * 60)
    print("测试 9: 内嵌翻译 (I18n.TRANSLATIONS)")
    print("=" * 60)
    
    from common.i18n import I18n
    
    all_passed = True
    
    # 测试 flow_start 键（在 YAML 中可能不存在，但在内嵌翻译中存在）
    flow_keys = ["flow_start", "validation_pass", "skill_execute"]
    
    for key in flow_keys:
        result_zh = I18n("zh").t(key)
        result_en = I18n("en").t(key)
        print(f"   {key}:")
        print(f"      zh: '{result_zh}'")
        print(f"      en: '{result_en}'")
        
        # 检查是否有实际翻译内容
        if result_zh == key or result_en == key:
            print(f"      ⚠️  可能回退到默认值")
    
    return True


def test_multilingual_user():
    """模拟多语言用户场景"""
    print("\n" + "=" * 60)
    print("测试 10: 多语言用户场景模拟")
    print("=" * 60)
    
    from common.i18n import I18n
    
    # 模拟不同语言偏好的用户
    users = [
        {"name": "小明", "lang": "zh"},
        {"name": "John", "lang": "en"},
        {"name": "토르", "lang": "ko"},
        {"name": "太朗", "lang": "ja"},
    ]
    
    all_passed = True
    for user in users:
        user_i18n = I18n(user["lang"])
        greeting = user_i18n.t("cli.welcome")
        print(f"   {user['name']} ({user['lang']}): '{greeting}'")
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 Handsome Agent i18n 模块测试")
    print("=" * 60)
    
    tests = [
        ("模块导入", test_import),
        ("基础翻译", test_basic_translation),
        ("语言切换", test_language_switch),
        ("占位符", test_placeholder),
        ("语言别名", test_language_alias),
        ("回退机制", test_fallback),
        ("I18n 类", test_i18n_class),
        ("YAML 结构", test_yaml_structure),
        ("内嵌翻译", test_legacy_translations),
        ("多语言用户", test_multilingual_user),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")
    
    print(f"\n总计: {passed_count}/{total_count} 通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！i18n 模块工作正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total_count - passed_count} 个测试失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
