"""测试工具状态回调功能"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.streaming import (
    ConsoleConsumer, 
    StreamEmitter, 
    ConsumerRegistry,
    BufferedConsumer
)


def test_tool_events():
    """测试工具事件"""
    print("=" * 60)
    print("测试工具状态回调功能")
    print("=" * 60)
    
    # 创建注册表和发射器
    registry = ConsumerRegistry()
    console = ConsoleConsumer(compact=False)  # 详细模式
    registry.register(console)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟工具执行...")
    print("-" * 40)
    
    # 模拟工具执行流程
    print("\n>>> 模拟执行 read_file 工具")
    emitter.emit_tool_start("read_file", {"path": "/path/to/file.txt", "lines": 100})
    
    # 模拟工具执行（这里只是等待）
    import time
    time.sleep(0.3)
    
    # 工具执行完成
    emitter.emit_tool_end("read_file", {
        "success": True,
        "content": "File content here...",
        "lines_read": 50
    })
    
    print("\n>>> 模拟执行 write_file 工具")
    emitter.emit_tool_start("write_file", {"path": "/output.txt", "content": "Hello World"})
    time.sleep(0.2)
    emitter.emit_tool_end("write_file", {"success": True})
    
    print("\n>>> 模拟执行 search 工具")
    emitter.emit_tool_start("search", {"query": "Python AI", "limit": 10})
    time.sleep(0.3)
    emitter.emit_tool_end("search", {
        "success": True,
        "results": ["result1", "result2"],
        "total": 2
    })
    
    # 模拟最终响应
    print("\n>>> 生成最终响应...")
    for char in "这是最终的AI响应内容，包含了一些重要的信息。":
        emitter.emit_delta(char)
    
    emitter.emit_complete("这是最终的AI响应内容，包含了一些重要的信息。")
    
    # 等待广播完成
    time.sleep(0.5)
    
    emitter.stop()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")


def test_compact_mode():
    """测试紧凑模式"""
    print("\n" + "=" * 60)
    print("测试紧凑模式")
    print("=" * 60)
    
    registry = ConsumerRegistry()
    console = ConsoleConsumer(compact=True, show_icons=True)
    registry.register(console)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟工具执行（紧凑模式）...")
    print("-" * 40)
    
    import time
    
    # 紧凑模式的工具执行
    emitter.emit_tool_start("read_file", {"path": "/test.txt"})
    time.sleep(0.2)
    emitter.emit_tool_end("read_file", {"success": True})
    
    emitter.emit_tool_start("search", {"query": "test"})
    time.sleep(0.2)
    emitter.emit_tool_end("search", {"success": True, "count": 5})
    
    # 最终响应
    for char in "最终响应":
        emitter.emit_delta(char)
    
    emitter.emit_complete("最终响应")
    
    time.sleep(0.5)
    emitter.stop()
    
    print("\n" + "=" * 60)
    print("✅ 紧凑模式测试完成")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试错误处理")
    print("=" * 60)
    
    registry = ConsumerRegistry()
    console = ConsoleConsumer()
    registry.register(console)
    
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始模拟错误...")
    print("-" * 40)
    
    emitter.emit_tool_start("dangerous_tool", {"action": "delete_all"})
    import time
    time.sleep(0.2)
    emitter.emit_tool_end("dangerous_tool", {"success": False, "error": "Permission denied"})
    
    emitter.emit_error("Connection timeout", "TimeoutError")
    
    time.sleep(0.3)
    emitter.stop()
    
    print("\n" + "=" * 60)
    print("✅ 错误处理测试完成")


if __name__ == "__main__":
    try:
        test_tool_events()
        test_compact_mode()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("✅ 所有工具状态回调测试完成!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {e}")
        traceback.print_exc()