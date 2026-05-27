"""
知识图谱Agent - 实体关系、知识推理
"""

class KnowledgeGraphAgent:
    def __init__(self):
        self.graph = {}
    
    def add_entity(self, entity, relations):
        self.graph[entity] = relations
    
    def query(self, entity):
        return self.graph.get(entity, [])
    
    def infer(self, entity1, relation, entity2):
        if entity1 in self.graph:
            rels = self.graph[entity1]
            if relation in rels:
                return rels[relation]
        return []
