"""
安全Agent - 内容过滤、伦理检查
"""

class SafetyAgent:
    def __init__(self):
        self.blocked_words = ["harmful", "illegal"]
        self.trusted_sources = []
    
    def check(self, content):
        for word in self.blocked_words:
            if word in content.lower():
                return "BLOCKED"
        return "SAFE"
    
    def add_trusted_source(self, source):
        self.trusted_sources.append(source)
