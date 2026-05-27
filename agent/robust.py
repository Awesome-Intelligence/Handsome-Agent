"""
鲁棒Agent - 对抗训练、分布外检测
"""

class RobustAgent:
    def __init__(self):
        self.entropy_threshold = 0.5
    
    def detect_ood(self, input_data):
        entropy = len(set(input_data)) / len(input_data)
        if entropy < self.entropy_threshold:
            return "OOD_DETECTED"
        return "IN_DISTRIBUTION"
    
    def train_adversarial(self, adversarial_examples):
        return len