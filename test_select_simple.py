#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单测试交互式选择器"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.interactive_select import select_option

print("开始测试交互式选择器...")
print("请使用键盘上下键选择，按 Enter 确认\n")

options = [
    "第一个选项",
    "第二个选项",
    "第三个选项",
    "第四个选项",
    "第五个选项"
]

try:
    result = select_option(options, title="测试菜单")
    
    if result is not None:
        print(f"\n✅ 选择了第 {result + 1} 项: {options[result]}")
    else:
        print("\n❌ 取消了选择")
        
except Exception as e:
    print(f"\n❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()
