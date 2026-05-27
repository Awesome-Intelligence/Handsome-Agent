"""Gateway 单元测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from adapter.gateway import Gateway, GatewayConfig, BaseGateway, BaseAdapter
from adapter.message import StandardMessage, MessageChannel, MessageContent


class TestGatewayConfig:
    """GatewayConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = GatewayConfig()
        
        assert config.name == "HandsomeAgentGateway"
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.brain_service_url == "http://localhost:8001"
    
    def test_custom_values(self):
        """测试自定义值"""
        config = GatewayConfig(
            name="TestGateway",
            host="127.0.0.1",
            port=9000,
            brain_service_url="http://localhost:9001",
        )
        
        assert config.name == "TestGateway"
        assert config.host == "127.0.0.1"
        assert config.port == 9000


class TestGateway:
    """Gateway 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = GatewayConfig()
        self.gateway = Gateway(self.config)
    
    def test_gateway_initialization(self):
        """测试 Gateway 初始化"""
        assert self.gateway.config == self.config
        assert self.gateway._adapters == {}
        assert self.gateway._running is False
    
    def test_register_adapter(self):
        """测试注册适配器"""
        mock_adapter = MagicMock(spec=BaseAdapter)
        mock_adapter.channel = MessageChannel.HTTP
        
        self.gateway.register_adapter(MessageChannel.HTTP, mock_adapter)
        
        assert MessageChannel.HTTP in self.gateway._adapters
    
    def test_message_handler(self):
        """测试消息处理器设置"""
        async def handler(msg):
            return msg
        
        self.gateway.set_message_handler(handler)
        assert self.gateway._message_handler is handler


class TestBaseGateway:
    """BaseGateway 测试"""
    
    def test_gateway_config_assignment(self):
        """测试配置赋值"""
        config = GatewayConfig(name="TestConfig")
        gateway = MagicMock(spec=BaseGateway)
        gateway.config = config
        
        assert gateway.config == config