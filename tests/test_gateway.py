"""测试 TUI Gateway"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from common.streaming.gateway import TUIGateway, Session


async def test_gateway_basic():
    """测试网关基本功能"""
    print("=" * 60)
    print("测试 TUI Gateway 基本功能")
    print("=" * 60)
    
    gateway = TUIGateway(host="127.0.0.1", port=18765)
    
    print("\n创建测试会话...")
    
    # 模拟会话
    class MockWebSocket:
        def __init__(self):
            self.messages = []
        
        async def send(self, data):
            self.messages.append(data)
            print(f"  发送: {data[:80]}...")
        
        def close(self):
            pass
    
    # 创建模拟会话
    session = Session(
        id="test-session-1",
        websocket=MockWebSocket()
    )
    gateway._sessions[session.id] = session
    
    print("\n测试发射增量文本...")
    await gateway.emit_delta(session.id, "Hello")
    await gateway.emit_delta(session.id, ", ")
    await gateway.emit_delta(session.id, "World!")
    
    print("\n测试发射推理内容...")
    await gateway.emit_reasoning(session.id, "Let me think...")
    
    print("\n测试发射工具事件...")
    await gateway.emit_tool_start(session.id, "search", {"query": "test"})
    await gateway.emit_tool_end(session.id, "search", {"results": []})
    
    print("\n测试发射完成...")
    await gateway.emit_complete(session.id, "Final response", "My reasoning")
    
    print("\n" + "-" * 40)
    print(f"发送的消息数量: {len(session.websocket.messages)}")
    print("\n✅ 基本功能测试完成")


async def test_gateway_protocol():
    """测试协议格式"""
    print("\n" + "=" * 60)
    print("测试网关协议格式")
    print("=" * 60)
    
    gateway = TUIGateway()
    
    # 测试消息格式
    test_cases = [
        ("delta", gateway.emit_delta("s1", "text")),
        ("reasoning", gateway.emit_reasoning("s1", "thinking")),
        ("tool_start", gateway.emit_tool_start("s1", "tool", {})),
        ("tool_end", gateway.emit_tool_end("s1", "tool", {"ok": True})),
        ("complete", gateway.emit_complete("s1", "done")),
        ("error", gateway.emit_error("s1", "Failed")),
    ]
    
    print("\n支持的协议消息类型:")
    for name, coro in test_cases:
        print(f"  - {name}")
    
    print("\n✅ 协议格式测试完成")


async def test_server():
    """测试服务器启动（需要在另一个进程中运行）"""
    print("\n" + "=" * 60)
    print("测试 TUI Gateway 服务器")
    print("=" * 60)
    
    print("\n启动网关服务器...")
    print("注意: 请使用 WebSocket 客户端连接到 ws://127.0.0.1:18765")
    print("按 Ctrl+C 停止")
    
    gateway = TUIGateway(host="127.0.0.1", port=18765)
    
    try:
        await gateway.start()
        print("\n网关已启动，等待连接...")
        print("WebSocket 连接地址: ws://127.0.0.1:18765")
        print("\n发送测试事件...")
        
        # 等待一段时间，期间可以测试连接
        for i in range(3):
            await asyncio.sleep(1)
            print(f"  模拟事件 {i+1}...")
    
    except KeyboardInterrupt:
        print("\n收到停止信号...")
    finally:
        await gateway.stop()
        print("网关已停止")
    
    print("\n✅ 服务器测试完成")


async def main():
    """主测试函数"""
    try:
        await test_gateway_basic()
        await test_gateway_protocol()
        
        # 询问是否启动服务器测试
        print("\n" + "=" * 60)
        print("是否启动服务器测试？")
        print("这将启动一个 WebSocket 服务器，你可以用浏览器连接测试")
        print("=" * 60)
        
        choice = input("\n启动服务器测试？(y/N): ").strip().lower()
        if choice == 'y':
            await test_server()
        
        print("\n" + "=" * 60)
        print("✅ 所有 TUI Gateway 测试完成!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
