"""Tool Schema Registry 测试"""
import pytest
from tools.schema_registry import SchemaRegistry, UnifiedToolSchema, ToolSource
from tools.definitions import FILE_TOOLS, SHELL_TOOLS, WEB_TOOLS


class TestUnifiedToolSchema:
    """UnifiedToolSchema 测试"""
    
    def test_schema_creation(self):
        """测试 Schema 创建"""
        schema = UnifiedToolSchema(
            name="test_tool",
            description="A test tool",
            source=ToolSource.HERMES,
            source_name="original_tool",
            parameters={"type": "object"},
        )
        
        assert schema.name == "test_tool"
        assert schema.source == ToolSource.HERMES
        assert schema.category == "general"
        assert schema.safety_level == "medium"
    
    def test_schema_with_examples(self):
        """测试带示例的 Schema"""
        schema = UnifiedToolSchema(
            name="example_tool",
            description="A tool with examples",
            source=ToolSource.OPENCLAW,
            source_name="oc_tool",
            examples=[
                {"description": "Example 1", "params": {"key": "value"}}
            ],
        )
        
        assert len(schema.examples) == 1


class TestSchemaRegistry:
    """SchemaRegistry 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.registry = SchemaRegistry()
    
    def test_registry_initialization(self):
        """测试注册表初始化"""
        assert self.registry._schemas == {}
        assert self.registry._adapters == {}
    
    def test_register_schema(self):
        """测试注册 Schema"""
        schema = UnifiedToolSchema(
            name="test_tool",
            description="Test",
            source=ToolSource.CUSTOM,
            source_name="custom_tool",
        )
        
        self.registry.register(schema)
        
        assert "test_tool" in self.registry._schemas
        assert self.registry.get("test_tool") == schema
    
    def test_get_nonexistent_schema(self):
        """测试获取不存在的 Schema"""
        result = self.registry.get("nonexistent")
        
        assert result is None
    
    def test_list_all(self):
        """测试列出所有 Schema"""
        schema1 = UnifiedToolSchema(name="tool1", description="Tool 1", source=ToolSource.HERMES, source_name="t1")
        schema2 = UnifiedToolSchema(name="tool2", description="Tool 2", source=ToolSource.OPENCLAW, source_name="t2")
        
        self.registry.register(schema1)
        self.registry.register(schema2)
        
        tools = self.registry.list_all()
        
        assert len(tools) == 2
    
    def test_list_by_category(self):
        """测试按类别列出工具"""
        schema1 = UnifiedToolSchema(
            name="file_tool", 
            description="File tool", 
            source=ToolSource.HERMES,
            source_name="ft",
            category="file"
        )
        schema2 = UnifiedToolSchema(
            name="shell_tool",
            description="Shell tool",
            source=ToolSource.HERMES,
            source_name="st",
            category="shell"
        )
        
        self.registry.register(schema1)
        self.registry.register(schema2)
        
        file_tools = self.registry.list_by_category("file")
        
        assert len(file_tools) == 1
        assert file_tools[0].name == "file_tool"
    
    def test_list_by_source(self):
        """测试按来源列出工具"""
        schema1 = UnifiedToolSchema(name="hermes_tool", description="H", source=ToolSource.HERMES, source_name="ht")
        schema2 = UnifiedToolSchema(name="openclaw_tool", description="O", source=ToolSource.OPENCLAW, source_name="ot")
        
        self.registry.register(schema1)
        self.registry.register(schema2)
        
        hermes_tools = self.registry.list_by_source(ToolSource.HERMES)
        
        assert len(hermes_tools) == 1
        assert hermes_tools[0].name == "hermes_tool"


class TestToolDefinitions:
    """工具定义测试"""
    
    def test_file_tools_loaded(self):
        """测试文件工具已加载"""
        assert len(FILE_TOOLS) > 0
        
        for tool in FILE_TOOLS:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.source == ToolSource.HERMES or tool.source == ToolSource.OPENCLAW
    
    def test_shell_tools_loaded(self):
        """测试 Shell 工具已加载"""
        assert len(SHELL_TOOLS) > 0
        
        for tool in SHELL_TOOLS:
            assert tool.name is not None
            assert tool.category == "shell"
    
    def test_web_tools_loaded(self):
        """测试 Web 工具已加载"""
        assert len(WEB_TOOLS) > 0
        
        for tool in WEB_TOOLS:
            assert tool.name is not None
            assert tool.category == "web"