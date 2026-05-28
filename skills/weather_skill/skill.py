#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weather Skill Implementation
"""

from core.skill_manager import BaseSkill, SkillResult, SkillMetadata, SkillParameter


class WeatherSkill(BaseSkill):
    """Skill for weather queries."""
    
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="weather",
            name="Weather",
            description="查询指定城市的天气信息",
            category="tools",
            parameters=[
                SkillParameter(
                    name="city",
                    type=str,
                    description="城市名称",
                    required=True,
                    prompt="请告诉我你想查询哪个城市的天气"
                ),
                SkillParameter(
                    name="days",
                    type=int,
                    description="预报天数",
                    required=False,
                    default=1
                )
            ],
            aliases=["weather", "查询天气", "获取天气"],
            examples=[
                "查询北京天气",
                "北京今天天气怎么样",
                "上海未来3天天气预报"
            ],
            source="user"
        )
    
    async def execute(self, city: str, days: int = 1) -> SkillResult:
        """Execute weather query."""
        try:
            # 模拟天气查询
            weather_data = {
                "北京": {"temperature": "25°C", "condition": "晴", "wind": "微风"},
                "上海": {"temperature": "28°C", "condition": "多云", "wind": "东北风"},
                "广州": {"temperature": "32°C", "condition": "阵雨", "wind": "东风"}
            }
            
            if city in weather_data:
                data = weather_data[city]
                output = f"{city}天气：{data['condition']}，温度 {data['temperature']}，{data['wind']}"
                if days > 1:
                    output += f"，预报未来{days}天天气稳定"
                return SkillResult(success=True, output=output)
            else:
                return SkillResult(
                    success=True,
                    output=f"抱歉，暂不支持查询{city}的天气信息"
                )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))


# 创建技能实例供注册
weather_skill = WeatherSkill()
