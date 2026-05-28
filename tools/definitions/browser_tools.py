"""浏览器操作工具定义 - 浏览器自动化"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


BROWSER_TOOLS = [
    UnifiedToolSchema(
        name="browser_navigate",
        description="导航到指定 URL",
        source=ToolSource.HERMES,
        source_name="browser_navigate",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "目标 URL"
                },
                "new_tab": {
                    "type": "boolean",
                    "description": "是否在新标签页打开",
                    "default": False
                },
                "wait_after": {
                    "type": "number",
                    "description": "导航后等待秒数",
                    "default": 2
                }
            },
            "required": ["url"]
        },
        safety_level="medium",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_snapshot",
        description="获取当前页面截图",
        source=ToolSource.HERMES,
        source_name="browser_snapshot",
        parameters={
            "type": "object",
            "properties": {
                "full_page": {
                    "type": "boolean",
                    "description": "是否截取整页",
                    "default": False
                },
                "element": {
                    "type": "string",
                    "description": "指定元素选择器"
                }
            },
            "required": []
        },
        returns={
            "type": "object",
            "properties": {
                "image_base64": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"}
            }
        },
        safety_level="low",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_click",
        description="点击页面元素",
        source=ToolSource.HERMES,
        source_name="browser_click",
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS 选择器或元素索引"
                },
                "x": {
                    "type": "integer",
                    "description": "X 坐标（相对于元素）"
                },
                "y": {
                    "type": "integer",
                    "description": "Y 坐标（相对于元素）"
                },
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "鼠标按钮",
                    "default": "left"
                }
            },
            "required": ["selector"]
        },
        safety_level="medium",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_type",
        description="在输入框中输入文本",
        source=ToolSource.HERMES,
        source_name="browser_type",
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "输入框选择器"
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文本"
                },
                "clear_first": {
                    "type": "boolean",
                    "description": "是否先清空现有内容",
                    "default": True
                },
                "press_enter": {
                    "type": "boolean",
                    "description": "输入后是否按回车",
                    "default": False
                }
            },
            "required": ["selector", "text"]
        },
        safety_level="medium",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_scroll",
        description="滚动页面",
        source=ToolSource.HERMES,
        source_name="browser_scroll",
        parameters={
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "description": "滚动方向",
                    "default": "down"
                },
                "amount": {
                    "type": "integer",
                    "description": "滚动量（像素）",
                    "default": 500
                },
                "selector": {
                    "type": "string",
                    "description": "滚动到指定元素"
                }
            },
            "required": []
        },
        safety_level="low",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_press",
        description="按键盘按键",
        source=ToolSource.HERMES,
        source_name="browser_press",
        parameters={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "按键名称: Enter, Escape, Tab, Backspace, ArrowUp, ArrowDown 等"
                },
                "modifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "组合键修饰符: Control, Alt, Shift, Command/Meta"
                }
            },
            "required": ["key"]
        },
        safety_level="low",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_back",
        description="浏览器后退",
        source=ToolSource.HERMES,
        source_name="browser_back",
        parameters={},
        safety_level="low",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_vision",
        description="使用 AI 视觉分析当前页面",
        source=ToolSource.HERMES,
        source_name="browser_vision",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "要分析的内容"
                },
                "model": {
                    "type": "string",
                    "description": "视觉模型"
                }
            },
            "required": ["prompt"]
        },
        safety_level="low",
        category="browser",
    ),
    UnifiedToolSchema(
        name="browser_console",
        description="执行 JavaScript 代码获取页面信息",
        source=ToolSource.HERMES,
        source_name="browser_console",
        parameters={
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "JavaScript 代码"
                }
            },
            "required": ["script"]
        },
        safety_level="medium",
        category="browser",
    ),
]
