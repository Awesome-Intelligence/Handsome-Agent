"""
伦理Agent - 道德推理、价值对齐
"""

class EthicalAgent:
    def __init__(self):
        self.principles = ["fairness", "harm_prevention"]
    
    def evaluate_action(self, action):
        score = 0.8
        for principle in self.principles:
            if principle in action.lower():
                score += 0.1
        return min(score, 1.0)
    
    def recommend_action(self, options):
        scores = [self.evaluate_action(a) for a in options]
        return options[scores.index(max(scores))]
