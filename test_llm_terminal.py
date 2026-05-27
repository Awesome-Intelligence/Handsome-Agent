#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 LLM 驱动的终端命令处理器
"""

import asyncio
from core.llm_terminal_command import llm_terminal_command_handler
from core.skill_manager import skill_manager


async def test():
    # 模拟 LLM provider
    class MockLLM:
        async def generate(self, prompt):
            print('收到 LLM 请求:')
            print(prompt[:200] + '...')
            print()
            
            # 根据用户输入返回不同的模拟 LLM 响应
            if '桌面' in prompt:
                return '{"action_type": "open_folder", "target": "桌面", "command": "", "parameters": {}}'
            elif '浏览器' in prompt or 'chrome' in prompt:
                return '{"action_type": "open_app", "target": "chrome", "command": "", "parameters": {"url": null}}'
            elif '我的电脑' in prompt:
                return '{"action_type": "open_folder", "target": "我的电脑", "command": "", "parameters": {}}'
            elif '记事本' in prompt:
                return '{"action_type": "open_app", "target": "notepad", "command": "", "parameters": {}}'
            else:
                return '{"action_type": "unknown", "target": "", "command": "", "parameters": {}}'
    
    mock_llm = MockLLM()
    context = {
        'llm_provider': mock_llm,
        'skill_manager': skill_manager
    }
    
    queries = [
        '帮我打开桌面文件夹',
        '打开chrome浏览器',
        '打开我的电脑',
        '启动记事本'
    ]
    
    print('=' * 70)
    print('测试: LLM 驱动的终端命令处理器')
    print('=' * 70)
    
    for i, query in enumerate(queries, 1):
        print(f'\n测试 {i}: {query}')
        print('-' * 70)
        
        response, flow, success = await llm_terminal_command_handler(query, context)
        
        print(f'成功: {success}')
        if response:
            print(f'响应: {response}')
        print(f'执行流程:')
        for step in flow:
            print(f'  {step}')


if __name__ == '__main__':
    asyncio.run(test())