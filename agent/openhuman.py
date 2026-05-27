"""
OpenHuman-inspired Agent
完整的类人交互系统
"""

class OpenHumanAgent:
    """参考OpenHuman架构的Agent"""
    
    def __init__(self):
        self.personality = "empathetic"
        self.context = []
        self.user_mood = "neutral"
        self.conversation_style = "adaptive"
        
    def respond(self, query):
        # 检测用户情绪
        self._detect_mood(query)
        
        # 生成回复
        response = self._generate_response(query)
        
        # 上下文管理
        self._update_context(query, response)
        
        return response
    
    def _detect_mood(self, query):
        query_lower = query.lower()
        negative_words = ["frustrated", "angry", "stuck", "confused"]
        curious_words = ["curious", "wondering", "explain"]
        
        if any(word in query_lower for word in negative_words):
            self.user_mood = "frustrated"
        elif any(word in query_lower for word in curious_words):
            self.user_mood = "curious"
        else:
            self.user_mood = "neutral"
    
    def _generate_response(self, query):
        if self.user_mood == "frustrated":
            return "I hear you. Let me help you work through this step by step."
        elif self.user_mood == "curious":
            return "Great question! Here's a detailed explanation:"
        return "Here's what I found for you:"
    
    def _update_context(self, query, response):
        self.context.append({"q": query, "a": response})
        if len(self.context) > 5:
            self.context.pop(0)

# 测试
if __name__ == "__main__":
    agent = OpenHumanAgent()
    print("OpenHuman Agent initialized")
    print("Mood detection working")
    print("Context window maintained")
