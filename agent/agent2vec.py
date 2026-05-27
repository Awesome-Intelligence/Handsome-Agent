"""
思维向量Agent - 概念嵌入、语义相似度
"""

class ThoughtVectorAgent:
    def __init__(self):
        self.thought_vectors = {}
        self.dimension = 128
    
    def encode(self, concept):
        vector = [0.0] * self.dimension
        for i, c in enumerate(concept):
            vector[i % self.dimension] = ord(c) / 255.0
        self.thought_vectors[concept] = vector
        return vector
    
    def similarity(self, c1, c2):
        if c1 not in self.thought_vectors:
            self.encode(c1)
        if c2 not in self.thought_vectors:
            self.encode(c2)
        v1 = self.thought_vectors[c1]
        v2 = self.thought_vectors[c2]
        return sum(a * b for a, b in zip(v1, v2))
