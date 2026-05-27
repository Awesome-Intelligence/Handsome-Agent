"""
上下文压缩器
当上下文过长时，使用 Summarizer 压缩
"""

from typing import List, Dict, Any


class Summarizer:
    """上下文压缩器"""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self._estimated_chars_per_token = 4  # 中文估算
    
    async def summarize(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        压缩对话历史
        
        策略：
        1. 如果总长度在限制内，直接返回
        2. 如果超出限制，保留最近的消息和重要摘要
        """
        total_chars = sum(len(m.get("content", "")) for m in messages)
        max_chars = self.max_tokens * self._estimated_chars_per_token
        
        if total_chars <= max_chars:
            return messages
        
        # 需要压缩
        # 保留最近的一半消息和关键摘要
        mid = len(messages) // 2
        recent = messages[mid:]
        summarized = messages[:mid]
        
        # 对前半部分生成摘要
        summary_content = self._generate_summary(summarized)
        
        return [
            {
                "role": "system",
                "content": f"[对话历史摘要] {summary_content}"
            }
        ] + recent
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        topics = []
        actions = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            if role == "user":
                # 提取关键主题
                if len(content) > 20:
                    topics.append(content[:50] + "..." if len(content) > 50 else content)
            elif role == "assistant":
                # 检查是否有执行操作
                if "执行" in content or "创建" in content or "修改" in content:
                    actions.append("执行了相关操作")
        
        summary_parts = []
        if topics:
            summary_parts.append(f"讨论了 {len(topics)} 个主题")
        if actions:
            summary_parts.append(f"执行了 {len(actions)} 个操作")
        
        return "; ".join(summary_parts) if summary_parts else "普通对话"
    
    def estimate_tokens(self, text: str) -> int:
        """估算 token 数量"""
        # 简化的中英文混合估算
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        
        return int(chinese_chars * 1.5 + english_chars * 0.25)