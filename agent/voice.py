"""
Voice Interface
参考OpenHuman语音交互
"""

class VoiceInterface:
    """语音接口"""
    
    def __init__(self):
        self.enabled = False
        self.language = "en-US"
        
    def enable(self):
        self.enabled = True
        print("Voice interface enabled")
        
    def speak(self, text):
        if self.enabled:
            print(f"[VOICE] {text}")

voice = VoiceInterface()
voice.enable()
voice.speak("Hello!")
