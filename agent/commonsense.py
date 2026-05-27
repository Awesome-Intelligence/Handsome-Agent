"""
常识Agent - 常识推理、物理直觉
"""

class CommonsenseAgent:
    def __init__(self):
        self.physical_knowledge = {}
        self.social_knowledge = {}
    
    def add_physical_rule(self, rule, outcome):
        self.physical_knowledge[rule] = outcome
    
    def add_social_rule(self, rule, outcome):
        self.social_knowledge[rule] = outcome
    
    def reason(self, query):
        for rule, outcome in self.physical_knowledge.items():
            if rule in query:
                return outcome
        for rule, outcome in self.social_knowledge.items():
            if rule in query:
                return outcome
        return "No commonsense rule found"
