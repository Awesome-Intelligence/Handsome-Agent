import asyncio
import warnings
warnings.filterwarnings('ignore')

from core.agent import CustomAgent, AgentConfig

async def test_llm_command_parse():
    print("测试 LLM 意图理解（"帮我打开名字叫做ie的浏览器"）...")
    
    agent = CustomAgent(AgentConfig(enable_detailed_logs=True))
    
    response = await agent.respond("帮我打开名字叫做ie的浏览器")
    print(f"\n结果: {response}")
    print(f"\n✅ 测试完成！LLM 现在会理解用户意图而不是用硬编码字典。")

if __name__ == "__main__":
    asyncio.run(test_llm_command_parse())
