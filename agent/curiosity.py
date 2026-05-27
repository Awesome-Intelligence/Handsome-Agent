"""
好奇心驱动Agent - 主动探索、信息增益
"""

class CuriousAgent:
    def __init__(self):
        self.questions = []
        self.information_gain = {}
    
    def ask_question(self, topic):
        question = {"topic": topic, "gain": self.information_gain.get(topic, 0.5)}
        self.questions.append(question)
        return question
    
    def explore(self, topic):
        return {"explored": topic, "information_gain": 0.8}
