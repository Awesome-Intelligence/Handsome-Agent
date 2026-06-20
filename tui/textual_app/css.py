#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSS 样式定义模块

提供 Handsome Agent TUI 的 CSS 样式定义。
使用 Theme 变量实现主题切换。
"""

from __future__ import annotations

# 类级别 CSS 属性
APP_CSS = """
/*
 * Handsome Agent TUI 主样式表
 *
 * CSS 架构说明：
 * - 使用 Textual Theme 变量实现主题切换
 * - 主题颜色在 app.py 的 THEMES 中定义
 * - CSS 中使用 $变量名 引用主题颜色
 *
 * 可用变量：
 * - $primary: 主强调色
 * - $secondary: 次强调色
 * - $accent: 强调色
 * - $background: 背景色
 * - $surface: 表面色
 * - $foreground: 前景/文字色
 * - $success: 成功色
 * - $warning: 警告色
 * - $error: 错误色
 */

/* ========== 整体样式 ========== */

Screen {
    background: $background;
}

/* 聊天区域 */
#chat-area {
    height: 1fr;
    width: 100%;
    background: $background;
    margin: 0;
    padding: 0;
    border: blank;
    overflow: hidden;
}

/* 默认边框样式 */
#chat-area:hover,
#chat-area:focus-within {
    border: solid $primary;
}

/* RichLog 自动换行 - 禁止横向滚动 */
#chat-area RichLog {
    width: 100%;
    overflow-x: hidden;
    overflow-y: auto;
}

/* 确保消息内容自动换行，不产生横向滚动 */
#chat-area RichLog > * {
    max-width: 100%;
    overflow-x: hidden;
}

/* 聊天日志内所有文本自动换行 */
#chat-area RichLog {
    border: blank;
    padding: 1 2;
}

/* 确保 RichText 内容宽度受限 */
#chat-area RichLog .rich-text {
    width: 100%;
    max-width: 100%;
}

/* 自定义 Header - 模型信息显示 + 欢迎横幅 */
#app-header {
    height: auto;
    width: 100%;
    dock: top;
    background: transparent;
    border-bottom: solid $primary;
}

#header-content {
    height: auto;
    width: 100%;
    layout: horizontal;
}

#banner-left {
    height: auto;
    width: auto;
}

#welcome-banner {
    height: auto;
    width: auto;
    padding: 0 2;
    background: transparent;
}

#header-info-right {
    height: 100%;
    width: 1fr;
    align: right middle;
}

.header-info-text {
    height: auto;
    width: 100%;
    padding: 0 2;
    background: transparent;
    align: right middle;
}

.header-content {
    height: 100%;
    layout: horizontal;
    padding: 0 2;
    align: left middle;
}

.header-model {
    color: $accent;
    text-style: bold;
}

.header-context {
    color: #8b949e;
    margin-left: 4;
}

.header-cwd {
    color: #6e7681;
}

.header-status {
    color: $success;
    margin-right: 1;
}

/* 流式输出指示器 - Textual CSS 不支持动画，使用静态样式 */
.streaming-indicator {
    color: #8b949e;
}

/* === 状态栏样式 === */
#status-bar {
    height: 1;
    width: 100%;
    background: $primary;
    padding: 0 2;
}

#status-content {
    height: 100%;
    layout: horizontal;
    padding: 0 0;
    align: left middle;
    color: $background;
}

.status-icon {
    width: auto;
    margin-right: 2;
    color: $success;
}

.status-model {
    width: auto;
    margin-right: 2;
    color: $foreground;
    text-style: bold;
}

.status-tokens {
    width: auto;
    margin-right: 2;
    color: $secondary;
}

#status-progress {
    width: 15;
    margin-right: 2;
}

.status-time {
    width: auto;
    margin-right: 2;
    color: $secondary;
}

.status-tools {
    width: auto;
    color: $accent;
}

/* 聊天日志样式 */
#chat-area {
    padding: 1 2;
}

/* 消息样式 - 用户消息浅色气泡 */
#chat-area .user-message {
    background: $surface;
    color: $foreground;
    padding: 0 1;
    margin: 0;
}

/* 消息样式 - 助手消息 */
#chat-area .assistant-message {
    color: $foreground;
    padding: 0 1;
    margin: 0;
}

/* 消息样式 - 系统消息灰色 */
#chat-area .system-message {
    color: #8b949e;
    padding: 0 1;
    margin: 0;
}

/* 滚动条样式 - 美化为细线 */

/* ========== 焦点样式说明 ========== */
/*
 * Frogmouth 风格焦点指示器设计：
 * - 默认状态：border: blank（无边框，保持简洁）
 * - 焦点状态：border: heavy $accent（粗边框强调色）
 * 这种设计让焦点状态更加清晰醒目
 */

/* 输入区域样式 */
#input-area {
    height: auto;
    width: 100%;
    dock: bottom;
    layout: vertical;
}

#input-area #status-content {
    height: 100%;
    layout: horizontal;
    padding: 0 2;
    align: left bottom;
    color: $background;
}

#input-area #user-input {
    margin: 0;
}

#input-area Footer {
    dock: none;
    height: 1;
}

#input-field {
    border: blank;
    background: $background;
    padding: 0;
}

#input-field:focus {
    border: heavy $accent;
}

/* 发送按钮样式 */
#send-button {
    width: 5;
    background: $success;
    color: $background;
    border: blank;
}

#send-button:hover {
    background: $success;
}

#send-button:focus {
    border: heavy $accent;
}

#input-row {
    height: 100%;
    width: 100%;
    layout: horizontal;
}

.input-field {
    border: blank;
    background: $surface;
    color: $foreground;
    padding: 1 2;
    height: 100%;
    width: 1fr;
}

.input-field:focus {
    border: heavy $accent;
}

/* TextArea (Composer) specific styles */
#user-input {
    background: transparent;
    color: $foreground;
    margin: 0;
    height: 7;
    padding: 0 1;
}

/* 默认边框样式 */
#user-input {
    border: thick $secondary;
}

#user-input:focus,
#user-input:hover {
    border: thick $primary;
}

/* 按钮通用样式 */
Button {
    background: $surface;
    color: $foreground;
    border: blank;
}

Button:hover {
    background: $surface;
}

Button:focus {
    border: heavy $accent;
    background: $surface;
}

/* === 侧边栏样式 === */
#sidebar-container {
    width: 30;
    height: 100%;
    background: transparent;
    border: blank;
    margin: 0;
    padding: 0;
}

/* 默认边框样式 */
#sidebar-container:hover,
#sidebar-container:focus-within {
    border: solid $primary;
}

#sidebar-container-inner {
    width: 100%;
    height: 100%;
}

#sidebar-tabs {
    height: 3;
    background: transparent;
    border-bottom: solid $surface;
    content-align: left bottom;
}

#sidebar-content-inner {
    height: 1fr;
    padding: 1;
}

.sidebar-panel {
    height: 100%;
    display: block;
}

.sidebar-panel.hidden {
    display: none;
}

.panel-title {
    color: $foreground;
    text-style: bold;
    margin-bottom: 1;
}

#log-output {
    height: 100%;
    background: $background;
    color: #8b949e;
}

/* === 主区域布局 === */
#main-area {
    height: 1fr;
    width: 100%;
    margin: 0;
    padding: 0;
}

#chat-area {
    width: 1fr;
    height: 100%;
    margin: 0;
    padding: 0;
}

#file-tree-title,
#tasks-title,
#agent-title,
#context-title {
    color: $foreground;
    text-style: bold;
    margin-bottom: 1;
}

/* ============================================================================
   半透明背景样式 (Frosted Glass Effect)
   支持 Ctrl+Shift+B 快捷键切换
   ============================================================================ */

/* 透明度容器 - 基础样式 */
.transparent-container {
    /* 使用纯色背景作为降级方案 */
}

/* 半透明面板 - 毛玻璃效果 */
.transparent-panel {
    background: rgba(13, 17, 23, 0.75);
    border: solid rgba(48, 54, 61, 0.5);
}

/* 半透明标题栏 */
.transparent-header {
    background: rgba(22, 27, 34, 0.80);
}

/* 半透明状态栏 */
.transparent-status-bar {
    background: rgba(33, 38, 45, 0.80);
}

/* 半透明页脚 */
.transparent-footer {
    background: rgba(33, 38, 45, 0.85);
}

/* 半透明侧边栏 */
.transparent-sidebar {
    background: rgba(22, 27, 34, 0.75);
    border-left: solid rgba(48, 54, 61, 0.5);
}

/* 半透明聊天区域 */
.transparent-chat {
    background: rgba(13, 17, 23, 0.70);
}

/* 半透明输入框 */
.transparent-input {
    background: rgba(13, 17, 23, 0.60);
    border: blank;
}

.transparent-input:focus {
    border: heavy rgba(88, 166, 255, 0.8);
}

/* 半透明欢迎横幅 */
.transparent-welcome {
    background: rgba(22, 27, 34, 0.65);
    border-bottom: solid rgba(48, 54, 61, 0.4);
}

/* 透明度切换指示器 */
.transparency-indicator {
    color: $accent;
    text-style: bold;
}

/* ============================================================================
   通知样式 (Notification Styles)
   ============================================================================ */

/* 通知样式 - 基础 */
.notification-toast {
    background: $surface;
    border: solid $accent;
    padding: 1 2;
}

/* 通知图标样式 */
.notification-icon {
    color: $accent;
}

.notification-icon.success {
    color: $success;
}

.notification-icon.warning {
    color: $warning;
}

.notification-icon.error {
    color: $error;
}

.notification-icon.info {
    color: $accent;
}

/* 进度条样式 */
.progress-bar {
    height: 1;
    background: $surface;
}

.progress-bar-fill {
    height: 100%;
    background: $accent;
}

/* ============================================================================
   打字机效果光标样式
   ============================================================================ */

/* 闪烁光标样式 - 用于流式输出 */
.typewriter-cursor {
    color: $accent;
    text-style: bold;
}

/* 加载动画文字样式 */
.loading-text {
    color: #8b949e;
}

/* 打字机完成后的淡入效果 (使用纯色，不支持 @keyframes 动画) */
.typewriter-complete {
    color: $foreground;
}

/* 加载动画增强样式 */
.loading-indicator {
    color: $success;
}

/* 加载动画帧样式 */
.loading-frame {
    text-style: bold;
}

/* 打字机输出组件样式 */
.typewriter-output {
    width: 1fr;
    height: auto;
    max-width: 100%;
    padding: 0 2;
    background: $background;
}

/* 打字机速度控制 (通过 Python 代码控制，此处仅作标记) */
.typewriter-fast {
    color: $accent;
}

.typewriter-normal {
    color: $accent;
}

.typewriter-slow {
    color: $accent;
}

"""
