"""
多语言Agent - 翻译、文化适配
"""

class MultilingualAgent:
    def __init__(self):
        self.languages = ["en", "zh", "es", "fr"]
        self.current_lang = "en"
    
    def translate(self, text, target_lang):
        if target_lang in self.languages:
            return f"[{target_lang}] {text}"
        return "Language not supported"
    
    def detect_language(self, text):
        if any(ord(c) > 127 for c in text):
            return "zh"
        return "en"
