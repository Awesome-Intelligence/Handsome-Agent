"""
个性化Agent - 用户建模、偏好学习
"""

class PersonalizationAgent:
    def __init__(self, user_id):
        self.user_id = user_id
        self.preferences = {}
        self.history = []
    
    def learn_preference(self, interaction):
        topic = interaction["topic"]
        rating = interaction.get("rating", 3)
        self.preferences[topic] = rating
        self.history.append(interaction)
    
    def recommend(self, topics):
        scores = []
        for topic in topics:
            score = self.preferences.get(topic, 2.5)
            scores.append((topic, score))
        return sorted(scores, key=lambda x: x[1], reverse=True)
