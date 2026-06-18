#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助工具模块

提供兼容层和辅助类。
"""

from __future__ import annotations

# 创建一个兼容的 log 对象来替代 Textual 的 log
# Textual 8.x 的 log 是一个 callable


class CompatibleLog:
    """兼容 Textual 8.x 的 Log 对象."""
    
    def __call__(self, *args, **kwargs):
        """Textual 8.x log 是 callable."""
        pass
    
    def system(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass


# 全局单例实例
_COMPATIBLE_LOG = CompatibleLog()


# Descriptor 来覆盖 App.log property
class LogDescriptor:
    """覆盖 App.log 属性的 descriptor."""
    def __get__(self, obj, objtype=None):
        return _COMPATIBLE_LOG
    
    def __set__(self, obj, value):
        pass  # 忽略设置，只用于读取
