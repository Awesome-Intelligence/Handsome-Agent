"""
持续学习Agent - 增量学习、灾难性遗忘防护
"""

class ContinualLearner:
    def __init__(self):
        self.knowledge = {}
        self.importance = {}
    
    def learn(self, concept, data):
        self.knowledge[concept] = data
        self.importance[concept] = self.importance.get(concept, 0) + 1
    
    def forget_low_importance(self, threshold=1):
        to_remove = [k for k, v in self.importance.items() if v < threshold]
        for k in to_remove:
            del self.knowledge[k]
            del self.importance[k]
    
    def replay(self):
        return list(self.knowledge.keys())
