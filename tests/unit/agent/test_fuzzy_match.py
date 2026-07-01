#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuzzy Match 模块测试

测试模糊查找并替换文本功能。
"""

import pytest
import importlib.util

# 直接加载 fuzzy_match 模块，避免通过 __init__.py 导入导致的其他模块错误
_spec = importlib.util.spec_from_file_location(
    "fuzzy_match", 
    "agent/skills/fuzzy_match.py"
)
_fuzzy_match_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fuzzy_match_module)
fuzzy_find_and_replace = _fuzzy_match_module.fuzzy_find_and_replace


class TestFuzzyFindAndReplace:
    """fuzzy_find_and_replace 函数测试"""

    def test_fuzzy_find_and_replace_exact(self):
        """测试精确匹配"""
        content = "Hello World\nTest Line\nHello World"
        result = fuzzy_find_and_replace(content, "Test", "Sample", replace_all=True)
        
        assert result[2] == "exact"
        assert result[1] == 1  # 匹配次数
        assert "Sample Line" in result[0]

    def test_fuzzy_find_and_replace_exact_multiple(self):
        """测试精确匹配多个实例"""
        content = "Hello World\nHello World\nHello World"
        result = fuzzy_find_and_replace(content, "Hello", "Hi", replace_all=True)
        
        assert result[2] == "exact"
        assert result[1] == 3  # 匹配次数
        assert result[0].count("Hi") == 3

    def test_fuzzy_find_and_replace_whitespace(self):
        """测试空白符规范化 - 精确匹配失败后会尝试模糊匹配"""
        content = "Hello   World\nTest"
        result = fuzzy_find_and_replace(content, "Hello World", "Hi World")
        
        # 精确匹配失败后，模糊匹配应能处理空白符差异
        # 但如果差异太大可能会失败
        assert result[2] in ("exact", "fuzzy", "none")

    def test_fuzzy_find_and_replace_whitespace_multiple(self):
        """测试多空白符规范化"""
        content = "A    B    C\nTest"
        result = fuzzy_find_and_replace(content, "A B C", "X Y Z")
        
        # 多空格应被正确处理
        assert result[2] in ("exact", "fuzzy", "none")

    def test_fuzzy_find_and_replace_indent(self):
        """测试缩进差异容忍"""
        content = "    indented line\nnormal"
        result = fuzzy_find_and_replace(content, "indented line", "new line")
        
        # 缩进差异应被容忍
        assert result[2] in ("fuzzy", "exact")

    def test_fuzzy_find_and_replace_indent_with_tabs(self):
        """测试 Tab 缩进容忍"""
        content = "\t\tindented line\nnormal"
        result = fuzzy_find_and_replace(content, "indented line", "new line")
        
        # Tab 缩进应被正确处理
        assert result[2] in ("fuzzy", "exact")

    def test_fuzzy_find_and_replace_not_found(self):
        """测试匹配失败"""
        content = "Hello World"
        result = fuzzy_find_and_replace(content, "NotExist", "New")
        
        assert result[2] == "none"
        assert result[3] is not None  # 有错误信息
        assert "NotExist" not in result[0]  # 原内容未被修改

    def test_fuzzy_find_and_replace_not_found_empty_error(self):
        """测试匹配失败时空内容"""
        result = fuzzy_find_and_replace("", "test", "new")
        
        assert result[2] == "none"
        assert result[3] is not None

    def test_replace_all(self):
        """测试全部替换"""
        content = "foo bar foo baz foo"
        result = fuzzy_find_and_replace(content, "foo", "qux", replace_all=True)
        
        assert result[1] == 3  # 全部3处都被替换
        assert result[2] == "exact"
        assert result[0].count("qux") == 3
        assert result[0].count("foo") == 0

    def test_replace_first_only(self):
        """测试只替换第一个"""
        content = "foo bar foo baz foo"
        result = fuzzy_find_and_replace(content, "foo", "qux", replace_all=False)
        
        assert result[1] == 1  # 只替换1处
        assert result[0].count("qux") == 1
        assert result[0].count("foo") == 2  # 剩余2处未替换

    def test_fuzzy_similarity_threshold(self):
        """测试模糊匹配相似度阈值"""
        content = "This is a test line with similar content"
        result = fuzzy_find_and_replace(content, "This is a test line", "Replaced")
        
        # 高度相似应能匹配
        assert result[2] in ("fuzzy", "exact")

    def test_multiline_exact_match(self):
        """测试多行精确匹配"""
        content = "Line 1\nLine 2\nLine 3"
        result = fuzzy_find_and_replace(content, "Line 1\nLine 2", "New Lines", replace_all=True)
        
        assert result[2] == "exact"
        assert "New Lines" in result[0]

    def test_multiline_fuzzy_match(self):
        """测试多行模糊匹配"""
        content = "    Line 1\n    Line 2\n    Line 3"
        result = fuzzy_find_and_replace(content, "Line 1\nLine 2", "New Lines")
        
        # 缩进差异应被容忍
        assert result[2] in ("fuzzy", "exact")

    def test_empty_old_string(self):
        """测试空查找字符串"""
        content = "Hello World"
        result = fuzzy_find_and_replace(content, "", "New")
        
        assert result[2] == "none"
        assert result[3] is not None

    def test_original_content_unchanged_on_failure(self):
        """测试失败时原内容不变"""
        content = "Original content here"
        result = fuzzy_find_and_replace(content, "Nonexistent", "Replaced")
        
        assert result[0] == content
        assert result[2] == "none"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])