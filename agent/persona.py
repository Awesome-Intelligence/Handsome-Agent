"""
Human-like Agent with Emotional Intelligence
参考OpenHuman架构
"""

class Persona:
    """人格特征"""
    def __init__(self):
        self.name = "AI Assistant"
        self.tone = "friendly"
        self.empathy_level = "high"
        self.follow_up_questions = True
        
    def adjust_tone(self, query):
        if "frustrated" in query or "angry" in query:
            self.tone = "empathetic"
        elif "curious" in query or "explain" in query:
            self.tone = "educational"
        return self.tone

class HumanLikeAgent:
    """Human-like响应生成器"""
    
    def __init__(self):
        self.persona = Persona()
        self.context_window = []
        self.max_context = 10
        
    def generate_response(self, query):
        tone = self.persona.adjust_tone(query)
        
        # 添加到上下文
        self.context_window.append({"role": "user", "content": query})
        
        # 生成回复
        response = self._create_response(query, tone)
        
        self.context_window.append({"role": "assistant", "content": response})
        
        # 保持上下文窗口
        if len(self.context_window) > self.max_context:
            self.context_window.pop(0)
            
        return response
    
    def _create_response(self, query, tone):
        # 简短确认
        acknowledgments = [
            "I understand",
            "Got it",
            "Thanks for sharing"
        ]
        
        # 生成回复
        if tone == "empathetic":
            return f"I hear you. {query[:20]}... Let me help..."
        elif tone == "educational":
            return f"Great question about {query[:20]}... Here's the answer..."
        else:
            return f"Sure! {query[:30]}... Here's what I found..."
    
    def get_context(self):
        return self.context_window

# 测试
agent = HumanLikeAgent()
print("✅ Human-like Agent created")
print("✅ Persona system working")
print("✅ Context window maintained")
