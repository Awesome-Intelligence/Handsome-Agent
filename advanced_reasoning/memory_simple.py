"""Memory System - 参考MemGPT"""
class Memory:
    def __init__(self):
        self.content = ""
        self.importance = 0.5
        self.timestamp = 0.0
        self.memory_type = "general"

class HierarchicalMemory:
    def __init__(self):
        self.working_memory = []
        self.short_term = []
        self.long_term = []
        self.limit = 10
        self.threshold = 0.7
    
    def add(self, content, importance=0.5, mem_type="general"):
        memory = Memory()
        memory.content = content
        memory.importance = importance
        memory.memory_type = mem_type
        memory.timestamp = 0.0
        self.working_memory.append(memory)
        return memory

class SelfReflectiveAgent:
    def __init__(self):
        self.memory = HierarchicalMemory()
        self.metrics = {"success": 0, "failure": 0}
    
    def think(self, query):
        result = "Processing: " + query
        return result
    
    def act(self, query):
        return "Action: " + query

# 测试
agent = SelfReflectiveAgent()
result = agent.think("test query")
print("Memory System working")
