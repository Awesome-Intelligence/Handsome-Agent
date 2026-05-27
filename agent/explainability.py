"""
可解释Agent - 决策透明、置信度
"""

class ExplainableAgent:
    def __init__(self):
        self.explanations = []
        self.confidence_threshold = 0.7
    
    def explain(self, decision, context):
        explanation = {
            "decision": decision,
            "confidence": 0.85,
            "reasons": ["Factor 1", "Factor 2", "Factor 3"],
            "context": context
        }
        self.explanations.append(explanation)
        return explanation
    
    def get_history(self):
        return self.explanations
