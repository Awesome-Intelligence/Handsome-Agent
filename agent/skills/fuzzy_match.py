#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuzzy Match Module - 模糊查找并替换文本

提供模糊匹配功能，支持空白符规范化和缩进差异容忍。
"""

import re
from typing import Tuple, Optional


def _normalize_whitespace(text: str) -> str:
    """
    规范化空白符：将多个空格合并为一个，移除首尾空白
    
    Args:
        text: 输入文本
    
    Returns:
        规范化后的文本
    """
    # 移除首尾空白
    text = text.strip()
    # 将多个空格/制表符合并为一个空格
    text = re.sub(r'[ \t]+', ' ', text)
    # 将换行符统一为空格
    text = re.sub(r'\n+', ' ', text)
    return text


def _normalize_indent(text: str) -> str:
    """
    规范化缩进：统一 tab 和 spaces 差异
    
    将所有 tab 转换为 4 个空格，然后去除行首缩进差异
    
    Args:
        text: 输入文本
    
    Returns:
        规范化缩进后的文本
    """
    # 将 tab 转换为 4 个空格
    text = text.expandtabs(4)
    # 分割成行
    lines = text.split('\n')
    
    if len(lines) <= 1:
        return text
    
    # 找出非空行的最小缩进
    min_indent = float('inf')
    for line in lines:
        if line.strip():
            # 计算行首空格数
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)
    
    if min_indent == float('inf'):
        min_indent = 0
    
    # 去除所有行的公共最小缩进
    normalized_lines = []
    for line in lines:
        if line.strip():
            normalized_lines.append(line[min_indent:])
        else:
            normalized_lines.append('')
    
    return '\n'.join(normalized_lines)


def _normalize_text(text: str) -> str:
    """
    完全规范化文本：空白符 + 缩进
    
    Args:
        text: 输入文本
    
    Returns:
        规范化后的文本
    """
    # 先规范化缩进
    text = _normalize_indent(text)
    # 再规范化空白符
    text = _normalize_whitespace(text)
    return text


def _find_similar_lines(content: str, old_string: str, limit: int = 3) -> list[str]:
    """
    查找相似内容行（用于提示）
    
    Args:
        content: 原始内容
        old_string: 要查找的字符串
        limit: 返回的最大行数
    
    Returns:
        相似内容行列表
    """
    old_normalized = _normalize_text(old_string)
    old_lines = [l.strip() for l in old_string.split('\n') if l.strip()]
    
    if not old_lines:
        return []
    
    similar = []
    content_lines = content.split('\n')
    
    for i, line in enumerate(content_lines):
        line_normalized = _normalize_text(line)
        
        # 检查行是否相似
        matched = False
        for old_line in old_lines:
            if old_line in line_normalized or line_normalized in old_line:
                similar.append(f"Line {i + 1}: {line.strip()[:60]}")
                matched = True
                break
        
        # 单行模式：计算相似度
        if not matched and len(old_lines) == 1:
            if _calculate_similarity(old_normalized, line_normalized) > 0.6:
                similar.append(f"Line {i + 1}: {line.strip()[:60]}")
    
    return similar[:limit]


def _calculate_similarity(s1: str, s2: str) -> float:
    """
    计算两个字符串的相似度（简单实现）
    
    Args:
        s1: 字符串1
        s2: 字符串2
    
    Returns:
        相似度 (0-1)
    """
    if not s1 or not s2:
        return 0.0
    
    # 转换为小写比较
    s1_lower = s1.lower()
    s2_lower = s2.lower()
    
    if s1_lower == s2_lower:
        return 1.0
    
    # 计算公共子序列长度
    common = 0
    s2_chars = list(s2_lower)
    for char in s1_lower:
        if char in s2_chars:
            common += 1
            s2_chars.remove(char)
    
    return common / max(len(s1_lower), len(s2_lower))


def fuzzy_find_and_replace(
    content: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False
) -> Tuple[str, int, str, Optional[str]]:
    """
    模糊查找并替换文本
    
    支持空白符规范化和缩进差异容忍。
    首先尝试精确匹配，失败后进行模糊匹配。
    
    Args:
        content: 原始内容
        old_string: 要替换的字符串
        new_string: 替换后的字符串
        replace_all: 是否替换所有匹配（默认 False，只替换第一个）
    
    Returns:
        Tuple[str, int, str, Optional[str]]:
        - new_content: 替换后的内容
        - match_count: 匹配次数
        - strategy: 使用的匹配策略 ("exact", "fuzzy", "none")
        - error_message: 错误信息（如果有）
    """
    # 参数验证
    if not content:
        return "", 0, "none", "Content is empty"
    
    if not old_string:
        return content, 0, "none", "old_string is empty"
    
    # 策略1: 尝试精确匹配
    if old_string in content:
        if replace_all:
            new_content = content.replace(old_string, new_string)
            match_count = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            match_count = 1
        return new_content, match_count, "exact", None
    
    # 策略2: 模糊匹配
    old_normalized = _normalize_text(old_string)
    
    # 按行分割处理
    content_lines = content.split('\n')
    old_lines = old_string.split('\n')
    old_line_count = len(old_lines)
    
    # 计算 old_string 的缩进基准
    old_indent_base = 0
    for line in old_lines:
        if line.strip():
            old_indent_base = len(line) - len(line.lstrip())
            break
    
    matches = []
    new_content_lines = []
    i = 0
    
    while i < len(content_lines):
        line = content_lines[i]
        line_normalized = _normalize_text(line)
        
        # 单行模糊匹配
        if old_line_count == 1:
            if _calculate_similarity(old_normalized, line_normalized) > 0.8:
                matches.append(i)
                new_content_lines.append(new_string)
                if not replace_all:
                    # 只替换第一个，剩余行直接添加
                    new_content_lines.extend(content_lines[i + 1:])
                    return '\n'.join(new_content_lines), 1, "fuzzy", None
            else:
                new_content_lines.append(line)
        else:
            # 多行模糊匹配
            if i + old_line_count <= len(content_lines):
                # 尝试匹配连续的多行
                block = '\n'.join(content_lines[i:i + old_line_count])
                block_normalized = _normalize_text(block)
                
                # 计算相似度
                similarity = _calculate_similarity(old_normalized, block_normalized)
                
                if similarity > 0.8:
                    matches.append(i)
                    new_content_lines.append(new_string)
                    i += old_line_count - 1
                    if not replace_all:
                        new_content_lines.extend(content_lines[i + 1:])
                        return '\n'.join(new_content_lines), 1, "fuzzy", None
                else:
                    new_content_lines.append(line)
            else:
                new_content_lines.append(line)
        
        i += 1
    
    # 如果模糊匹配成功
    if matches:
        match_count = len(matches)
        return '\n'.join(new_content_lines), match_count, "fuzzy", None
    
    # 未找到匹配
    similar = _find_similar_lines(content, old_string)
    if similar:
        error_msg = f"No match found. Similar content:\n" + "\n".join(similar)
    else:
        error_msg = "No match found"
    
    return content, 0, "none", error_msg