"""测试推理内容过滤功能"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.streaming import (
    StreamingThinkScrubber,
    StreamingOutput,
    strip_thinking_tags,
    extract_thinking_content,
    extract_thinking_tags,
)


def test_basic_scrubber():
    """测试基础推理标签过滤"""
    print("=" * 60)
    print("测试 1: 基础推理标签过滤")
    print("=" * 60)
    
    scrubber = StreamingThinkScrubber()
    
    # 测试1: think 标签
    print("\n测试 think 标签:")
    text = "<think>Let me think. The answer is 42.</think>"
    print(f"原文: {repr(text)}")
    visible, thinking = scrubber.feed(text)
    print(f"可见: '{visible}'")
    print(f"推理: '{thinking}'")
    # 验证关闭标签被移除
    assert "</think>" not in visible, f"Close tag should be removed from visible"
    assert "Let me think" in thinking, "Thinking content should be extracted"
    print("✅ 通过")
    
    # 测试2: 中文XML标签
    print("\n测试中文XML标签:")
    scrubber.reset()
    text = "<推理>我需要分析这个问题</推理>答案是42"
    visible, thinking = scrubber.feed(text)
    print(f"原文: {text}")
    print(f"可见: '{visible}'")
    print(f"推理: '{thinking}'")
    assert visible == "答案是42"
    assert thinking == "我需要分析这个问题"
    print("✅ 通过")
    
    # 测试3: 无标签文本
    print("\n测试无标签文本:")
    scrubber.reset()
    text = "这是一个普通的回复"
    visible, thinking = scrubber.feed(text)
    print(f"原文: {text}")
    print(f"可见: '{visible}'")
    print(f"推理: '{thinking}'")
    assert visible == "这是一个普通的回复"
    assert thinking is None
    print("✅ 通过")


def test_streaming_scrubber():
    """测试流式推理标签过滤"""
    print("\n" + "=" * 60)
    print("测试 2: 流式推理标签过滤")
    print("=" * 60)
    
    scrubber = StreamingThinkScrubber()
    all_visible = []
    all_thinking = []
    
    # 模拟流式输入
    chunks = [
        "<think>",
        "Let me ",
        "think about ",
        "this.",
        "",
        " The answer is",
        " 42.</think>",
    ]
    
    print("\n流式输入测试:")
    for chunk in chunks:
        visible, thinking = scrubber.feed(chunk)
        if visible:
            all_visible.append(visible)
            print(f"  chunk={repr(chunk)} → visible={repr(visible)}")
        if thinking:
            all_thinking.append(thinking)
            print(f"  chunk={repr(chunk)} → thinking={repr(thinking)}")
    
    # 刷新剩余内容
    visible, thinking = scrubber.flush()
    if visible:
        all_visible.append(visible)
        print(f"  flush → visible={repr(visible)}")
    if thinking:
        all_thinking.append(thinking)
        print(f"  flush → thinking={repr(thinking)}")
    
    full_visible = "".join(all_visible)
    full_thinking = "".join(all_thinking)
    
    print(f"\n完整可见内容: '{full_visible}'")
    print(f"完整推理内容: '{full_thinking}'")
    
    assert "</think>" not in full_visible, "Close tag should be removed"
    print("✅ 流式过滤测试通过")


def test_streaming_output():
    """测试 StreamingOutput 集成"""
    print("\n" + "=" * 60)
    print("测试 3: StreamingOutput 集成")
    print("=" * 60)
    
    output = StreamingOutput(console_consumer=True, show_thinking=True)
    output.start()
    
    print("\n模拟流式输入（含推理标签）:")
    
    # 模拟流式输入
    chunks = [
        "<think>",
        " 分析问题中...",
        "",
        " 最终答案是42</think>",
    ]
    
    for chunk in chunks:
        output.emit_delta(chunk)
    
    output.complete()
    
    import time
    time.sleep(0.3)
    
    print(f"\n累积推理内容: {output.get_thinking()}")
    
    output.stop()
    print("✅ StreamingOutput 测试完成")


def test_non_streaming_helpers():
    """测试非流式辅助函数"""
    print("\n" + "=" * 60)
    print("测试 4: 非流式辅助函数")
    print("=" * 60)
    
    text = "<think>第一步分析第二步最终结果</think>"
    
    print(f"\n原文: {text}")
    
    # strip_thinking_tags
    stripped = strip_thinking_tags(text)
    print(f"strip_thinking_tags: '{stripped}'")
    assert "</think>" not in stripped, "Close tag should be removed"
    print("✅ strip_thinking_tags 通过")
    
    # extract_thinking_content
    thinking = extract_thinking_content(text)
    print(f"extract_thinking_content: '{thinking}'")
    assert thinking is not None and "第一步分析" in thinking
    print("✅ extract_thinking_content 通过")


def test_mixed_content():
    """测试混合内容"""
    print("\n" + "=" * 60)
    print("测试 5: 混合内容场景")
    print("=" * 60)
    
    scrubber = StreamingThinkScrubber()
    
    # 多个推理块，中间有内容
    text = "<think>第一次推理</think>正常内容<think>第二次推理</think>更多内容"
    visible, thinking = scrubber.feed(text)
    remaining_visible, remaining_thinking = scrubber.flush()
    
    print(f"原文: {text}")
    print(f"可见: '{visible + remaining_visible}'")
    print(f"推理: '{thinking}'")
    
    full_visible = visible + remaining_visible
    assert "</think>" not in full_visible, "Close tag should be removed"
    assert "正常内容更多内容" in full_visible, "Normal content should be in visible"
    print("✅ 混合内容测试通过")


if __name__ == "__main__":
    try:
        test_basic_scrubber()
        test_streaming_scrubber()
        test_streaming_output()
        test_non_streaming_helpers()
        test_mixed_content()
        
        print("\n" + "=" * 60)
        print("✅ 所有推理过滤测试完成!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {e}")
        traceback.print_exc()