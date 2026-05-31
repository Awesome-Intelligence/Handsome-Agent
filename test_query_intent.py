import asyncio
import warnings
warnings.filterwarnings('ignore')

from core.agent import CustomAgent, AgentConfig

async def test_query_intent():
    print("测试查询意图检测（"你刚才打开的是什么浏览器"）...")
    
    agent = CustomAgent(AgentConfig(enable_detailed_logs=True))
    
    # 先执行一个命令
    print("\n1. 先执行命令：打开IE浏览器")
    await agent.respond("帮我打开IE浏览器")
    
    # 再查询
    print("\n2. 查询：你刚才打开的是什么浏览器")
    response = await agent.respond("你刚才打开的是什么浏览器")
    print(f"\n响应: {response}")
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    asyncio.run(test_query_intent())
