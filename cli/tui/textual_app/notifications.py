#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知动画管理模块

提供通知类型枚举和动画管理器。
"""

from __future__ import annotations


class NotificationType:
    """通知类型枚举."""
    
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    # 动画类型
    ANIM_SLIDE = "slide"
    ANIM_FADE = "fade"
    ANIM_BOUNCE = "bounce"
    ANIM_SHAKE = "shake"
    ANIM_PULSE = "pulse"
    
    @classmethod
    def get_animation_for_type(cls, notification_type: str) -> str:
        """根据通知类型获取对应的动画类名.
        
        Args:
            notification_type: 通知类型 (info/success/warning/error)
            
        Returns:
            动画类名
        """
        animations = {
            cls.INFO: cls.ANIM_SLIDE,
            cls.SUCCESS: cls.ANIM_BOUNCE,
            cls.WARNING: cls.ANIM_PULSE,
            cls.ERROR: cls.ANIM_SHAKE,
        }
        return animations.get(notification_type, cls.ANIM_FADE)
    
    @classmethod
    def get_icon(cls, notification_type: str) -> str:
        """获取通知类型的图标.
        
        Args:
            notification_type: 通知类型
            
        Returns:
            Emoji 图标
        """
        icons = {
            cls.INFO: "ℹ️",
            cls.SUCCESS: "✅",
            cls.WARNING: "⚠️",
            cls.ERROR: "❌",
        }
        return icons.get(notification_type, "ℹ️")


class NotificationAnimationManager:
    """通知动画管理器.
    
    负责：
    - 管理通知动画效果
    - 提供多种动画类型
    - 控制动画时长和缓动函数
    """
    
    # 动画时长配置 (秒)
    ANIMATION_DURATIONS = {
        "fast": 0.2,
        "normal": 0.3,
        "slow": 0.5,
    }
    
    # 动画缓动函数
    EASING_FUNCTIONS = {
        "ease": "ease",
        "ease-in": "ease-in",
        "ease-out": "ease-out",
        "ease-in-out": "ease-in-out",
        "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
        "elastic": "cubic-bezier(0.5, 1.5, 0.5, 1)",
    }
    
    @classmethod
    def get_css_animation(cls, animation_type: str, duration: str = "normal") -> str:
        """获取 CSS 动画字符串.
        
        Args:
            animation_type: 动画类型
            duration: 动画时长 (fast/normal/slow)
            
        Returns:
            CSS animation 属性值
        """
        duration_value = cls.ANIMATION_DURATIONS.get(duration, 0.3)
        easing = cls.EASING_FUNCTIONS.get("ease-out", "ease-out")
        
        animation_map = {
            NotificationType.ANIM_SLIDE: f"slide-in-right {duration_value}s {easing}",
            NotificationType.ANIM_FADE: f"fade-in {duration_value}s {easing}",
            NotificationType.ANIM_BOUNCE: f"bounce-in {duration_value}s {cls.EASING_FUNCTIONS['bounce']}",
            NotificationType.ANIM_SHAKE: f"shake {duration_value}s {easing}",
            NotificationType.ANIM_PULSE: f"pulse {duration_value * 2}s ease-in-out infinite",
        }
        
        return animation_map.get(animation_type, f"fade-in {duration_value}s {easing}")
    
    @classmethod
    def create_animated_notification(
        cls,
        message: str,
        notification_type: str = NotificationType.INFO,
        duration: float = 3.0,
    ) -> tuple[str, str]:
        """创建带动画的通知内容.
        
        Args:
            message: 通知消息
            notification_type: 通知类型
            duration: 显示时长（秒）
            
        Returns:
            (toast CSS类, 格式化消息)
        """
        # 获取动画类型
        anim_type = cls.get_animation_for_type(notification_type)
        icon = cls.get_icon(notification_type)
        
        # 构建 CSS 类
        css_classes = [
            "notification-toast",
            notification_type,
            f"anim-{anim_type}",
        ]
        css_class_str = " ".join(css_classes)
        
        # 格式化消息（带图标）
        formatted_message = f"[bold]{icon}[/] {message}"
        
        return css_class_str, formatted_message
    
    @classmethod
    def get_progress_bar_html(cls, progress: float, animated: bool = True) -> str:
        """生成分带动画的进度条 HTML.
        
        Args:
            progress: 进度 (0.0 - 1.0)
            animated: 是否启用动画
            
        Returns:
            进度条 CSS 类
        """
        base_class = "progress-bar"
        fill_class = "progress-bar-fill"
        if animated:
            fill_class += " progress-bar-animated"
        
        return f"{base_class} {fill_class}"
