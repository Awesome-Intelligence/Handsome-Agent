"""模拟流式输出测试（无需 API Key）"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.streaming import ConsoleConsumer, StreamEmitter, ConsumerRegistry, DeltaEvent, CompleteEvent


def test_stream_emitter():
    """测试流式发射器"""
    print("=" * 60)
    print("测试 1: StreamEmitter 基本功能")
    print("=" * 60)
    
    # 创建注册表和发射器
    registry = ConsumerRegistry()
    console = ConsoleConsumer()
    registry.register(console)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟流式输出...")
    print("-" * 40)
    
    # 模拟流式输出
    test_text = "Hello, 这是一个流式输出测试！"
    for char in test_text:
        emitter.emit_delta(char)
    
    emitter.emit_complete(test_text)
    
    # 等待广播完成
    import time
    time.sleep(0.5)
    
    emitter.stop()
    
    print("\n" + "-" * 40)
    print("✅ 测试完成")


def test_buffered_consumer():
    """测试缓冲消费者"""
    print("\n" + "=" * 60)
    print("测试 2: BufferedConsumer 缓冲功能")
    print("=" * 60)
    
    from common.streaming import BufferedConsumer
    
    registry = ConsumerRegistry()
    buffered = BufferedConsumer()
    registry.register(buffered)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟流式输出...")
    print("-" * 40)
    
    # 模拟流式输出
    test_text = "Buffer test content"
    for char in test_text:
        emitter.emit_delta(char)
    
    emitter.emit_complete(test_text)
    
    # 等待广播完成
    import time
    time.sleep(0.5)
    
    emitter.stop()
    
    print("\n" + "-" * 40)
    print(f"缓冲内容: '{buffered.content}'")
    print(f"内容匹配: {buffered.content == test_text}")
    
    if buffered.content == test_text:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")


def test_multiple_consumers():
    """测试多消费者"""
    print("\n" + "=" * 60)
    print("测试 3: 多消费者同时接收")
    print("=" * 60)
    
    from common.streaming import BufferedConsumer
    
    registry = ConsumerRegistry()
    
    # 添加多个消费者（使用不同名称）
    console1 = ConsoleConsumer()
    buffered1 = BufferedConsumer()
    
    # 创建带名称的缓冲消费者
    class NamedBufferedConsumer(BufferedConsumer):
        def __init__(self, name):
            super().__init__()
            self._name = name
        @property
        def name(self):
            return self._name
    
    buffered2 = NamedBufferedConsumer("buffered_2")
    
    registry.register(console1)
    registry.register(buffered1)
    registry.register(buffered2)
    
    print(f"已注册消费者数量: {registry.count}")
    print(f"消费者名称: {registry.names}")
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟流式输出...")
    print("-" * 40)
    
    # 模拟流式输出
    test_text = "Multiple consumers test"
    for char in test_text:
        emitter.emit_delta(char)
    
    emitter.emit_complete(test_text)
    
    # 等待广播完成
    import time
    time.sleep(0.5)
    
    emitter.stop()
    
    print("\n" + "-" * 40)
    print(f"Console1 内容: '{buffered1.content}'")
    print(f"Buffer2 内容: '{buffered2.content}'")
    
    if buffered1.content == test_text and buffered2.content == test_text:
        print("✅ 测试通过 - 两个缓冲消费者都收到了完整内容")
    else:
        print("❌ 测试失败")


def test_callback_consumer():
    """测试回调消费者"""
    print("\n" + "=" * 60)
    print("测试 4: CallbackConsumer 回调功能")
    print("=" * 60)
    
    from common.streaming import CallbackConsumer
    
    # 收集回调数据
    received_deltas = []
    received_complete = []
    
    def on_delta(text, event):
        received_deltas.append(text)
        print(f"  [callback] delta: '{text}'")
    
    def on_complete(event):
        received_complete.append(event)
        print(f"  [callback] complete")
    
    callback_consumer = CallbackConsumer(
        name="test_callback",
        on_delta=on_delta,
        on_complete=on_complete
    )
    
    registry = ConsumerRegistry()
    registry.register(callback_consumer)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟流式输出...")
    print("-" * 40)
    
    # 模拟流式输出
    test_text = "Callback test"
    for char in test_text:
        emitter.emit_delta(char)
    
    emitter.emit_complete(test_text)
    
    # 等待广播完成
    import time
    time.sleep(0.5)
    
    emitter.stop()
    
    print("\n" + "-" * 40)
    print(f"接收到的 deltas 数量: {len(received_deltas)}")
    print(f"接收到的 complete 数量: {len(received_complete)}")
    
    if len(received_deltas) > 0 and len(received_complete) > 0:
        print("✅ 测试通过 - 回调正常工作")
    else:
        print("❌ 测试失败")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Agent-Z 流式输出模块测试")
    print("=" * 60 + "\n")
    
    try:
        test_stream_emitter()
        test_buffered_consumer()
        test_multiple_consumers()
        test_callback_consumer()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {e}")
        traceback.print_exc()