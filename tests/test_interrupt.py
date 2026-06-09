"""测试中断机制功能"""
import sys
import os
from pathlib import Path
import threading
import time

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.streaming import (
    ConsoleConsumer, 
    StreamEmitter, 
    ConsumerRegistry
)


def test_interrupt_emitter():
    """测试 StreamEmitter 中断"""
    print("=" * 60)
    print("测试 1: StreamEmitter 中断功能")
    print("=" * 60)
    
    registry = ConsumerRegistry()
    console = ConsoleConsumer()
    registry.register(console)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟长时间操作...")
    print("-" * 40)
    
    # 模拟发送多个增量
    for i in range(5):
        if emitter.is_interrupted:
            print("\n⚠️ 检测到中断，停止发送")
            break
        emitter.emit_delta(f"chunk_{i}_")
        time.sleep(0.2)
    
    # 模拟中断
    print("\n>>> 模拟中断请求...")
    emitter.interrupt()
    emitter.emit_error("用户请求中断", "InterruptedError")
    
    # 尝试继续发送（应该被忽略）
    print("尝试继续发送...")
    emitter.emit_delta("这不应该被发送")
    
    time.sleep(0.5)
    emitter.stop()
    
    print("\n" + "=" * 60)
    print("✅ 中断功能测试完成")


def test_interrupted_flag():
    """测试中断标志"""
    print("\n" + "=" * 60)
    print("测试 2: 中断标志状态")
    print("=" * 60)
    
    registry = ConsumerRegistry()
    emitter = StreamEmitter(registry)
    
    print(f"初始状态: is_interrupted = {emitter.is_interrupted}")
    
    print("请求中断...")
    emitter.interrupt()
    print(f"中断后: is_interrupted = {emitter.is_interrupted}")
    
    print("清除中断...")
    emitter.clear_interrupt()
    print(f"清除后: is_interrupted = {emitter.is_interrupted}")
    
    print("\n" + "=" * 60)
    print("✅ 标志测试完成")


def test_console_interrupt_display():
    """测试控制台中断显示"""
    print("\n" + "=" * 60)
    print("测试 3: 控制台中断显示")
    print("=" * 60)
    
    registry = ConsumerRegistry()
    console = ConsoleConsumer()
    registry.register(console)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n模拟正常输出...")
    for char in "正在处理中...":
        emitter.emit_delta(char)
        time.sleep(0.05)
    
    # 发射错误事件
    print("\n")
    emitter.emit_error("操作被用户中断", "UserInterrupt")
    
    time.sleep(0.3)
    emitter.stop()
    
    print("\n" + "=" * 60)
    print("✅ 控制台中断显示测试完成")


if __name__ == "__main__":
    try:
        test_interrupt_emitter()
        test_interrupted_flag()
        test_console_interrupt_display()
        
        print("\n" + "=" * 60)
        print("✅ 所有中断机制测试完成!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {e}")
        traceback.print_exc()