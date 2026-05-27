"""Message 单元测试"""
import pytest
from adapter.message import (
    StandardMessage, 
    MessageChannel, 
    MessageContent,
    ExecutionResult
)


class TestMessageChannel:
    """MessageChannel 测试"""
    
    def test_channel_values(self):
        """测试渠道枚举值"""
        assert MessageChannel.HTTP.value == "http"
        assert MessageChannel.WEBSOCKET.value == "websocket"
        assert MessageChannel.CLI.value == "cli"
        assert MessageChannel.TELEGRAM.value == "telegram"


class TestMessageContent:
    """MessageContent 测试"""
    
    def test_text_content(self):
        """测试文本内容"""
        content = MessageContent(type="text", text="Hello, world!")
        
        assert content.type == "text"
        assert content.text == "Hello, world!"
        assert content.media_url is None
    
    def test_with_metadata(self):
        """测试带元数据的内容"""
        content = MessageContent(
            type="text",
            text="Hello",
            metadata={"language": "en"}
        )
        
        assert content.metadata["language"] == "en"


class TestStandardMessage:
    """StandardMessage 测试"""
    
    def test_message_creation(self):
        """测试消息创建"""
        content = MessageContent(type="text", text="Hello")
        message = StandardMessage(
            channel=MessageChannel.CLI,
            user_id="user123",
            session_id="session456",
            content=content,
        )
        
        assert message.channel == MessageChannel.CLI
        assert message.user_id == "user123"
        assert message.session_id == "session456"
        assert message.content.text == "Hello"
        assert message.message_id is not None
    
    def test_to_json(self):
        """测试转换为 JSON"""
        content = MessageContent(type="text", text="Hello")
        message = StandardMessage(
            channel=MessageChannel.HTTP,
            user_id="user1",
            session_id="session1",
            content=content,
        )
        
        json_str = message.to_json()
        
        assert isinstance(json_str, str)
        assert "user1" in json_str
        assert "Hello" in json_str
    
    def test_from_json(self):
        """测试从 JSON 解析"""
        original = StandardMessage(
            channel=MessageChannel.CLI,
            user_id="user1",
            session_id="session1",
            content={"type": "text", "text": "Hello"},
        )
        
        json_str = original.to_json()
        restored = StandardMessage.from_json(json_str)
        
        assert restored.user_id == original.user_id
        assert restored.content.text == original.content.text


class TestExecutionResult:
    """ExecutionResult 测试"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = ExecutionResult(
            status="success",
            result={"output": "test output"},
            logs=["log1", "log2"],
        )
        
        assert result.status == "success"
        assert result.result["output"] == "test output"
        assert len(result.logs) == 2
        assert result.execution_id is not None
    
    def test_error_result(self):
        """测试错误结果"""
        result = ExecutionResult(
            status="error",
            error_message="Something went wrong",
        )
        
        assert result.status == "error"
        assert "Something went wrong" in result.error_message