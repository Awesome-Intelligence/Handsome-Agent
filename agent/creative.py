"""
推理Agent - 因果推理、逻辑分析
"""

class ReasoningAgent:
    def __init__(self):
        self.premises = []
        self.conclusions = []
    
    def reason(self, statement):
        if "because" in statement.lower():
            return self._causal(statement)
        elif "if" in statement.lower():
            return self._conditional(statement)
        return self._deductive(statement)
    
    def _causal(self, statement):
        return "Causal: " + statement[:30]
    
    def _conditional(self, statement):
        return "Conditional: " + statement[:30]
    
    _deductive = lambda self, s: "Deductive: " + s[:30]
