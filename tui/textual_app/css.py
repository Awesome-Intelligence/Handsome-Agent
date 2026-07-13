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
    margin: 0;
    padding: 0;
}

/* 聊天区域 */
#chat-area {
    height: 1fr;
    width: 1fr;
    background: transparent;
    margin: 0;
    padding: 0;
    border: blank;
    /* #chat-area 就是 ChatContainer(VerticalScroll) 本身，必须允许纵向滚动。
       原来的 overflow: hidden 会禁用它自身的滚动（无滚动条、鼠标滚轮失效）。 */
    overflow-x: hidden;
    overflow-y: auto;
}



/* MessageList (VerticalScroll) 样式 */
#chat-area MessageList {
    width: 100%;
    height: 100%;
    overflow-x: hidden;
    overflow-y: auto;
    border: blank;
    padding: 1 2;
    background: transparent;
}

/* 自定义 Header - 模型信息显示 + 欢迎横幅 */
#app-header {
    height: 3;
    width: 100%;
    dock: top;
    background: rgba(177, 128, 215, 0.2);
    outline-bottom: solid $primary;
    layout: horizontal;
}

#welcome-banner {
    height: auto;
    width: auto;
    padding: 0 2;
    margin-right: 4;
    background: transparent;
}

#header-info-right {
    height: 3;
    width: 1fr;
    align: right middle;
}

#version-info,
#skills-info,
#tools-info {
    height: auto;
    width: 100%;
    padding: 0 2;
    background: transparent;
}

#theme-toggle {
    width: 3;
    height: 3;
    padding: 0;
    margin-left: 2;
    background: $accent;
    color: white;
    content-align: center middle;
}

#theme-toggle:hover {
    background: $primary;
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
    padding: 0;
    margin: 0;
    outline: thick solid $secondary;
}

#status-content {
    height: 100%;
    layout: horizontal;
    padding: 0 0;
    align: left middle;
    color: $foreground;
}

.status-icon {
    width: auto;
    margin-right: 2;
}

.status-model {
    width: 22;
    max-width: 22;
    height: 1;
    margin-right: 2;
    background: $surface;
    color: $foreground;
    text-style: bold;
}

/* Select widget in status bar - compact mode */
#status-model Select {
    height: 1;
    width: 100%;
}

#status-model Select.-textual-compact {
    border: none;
    background: transparent;
}

#status-model Select.-textual-compact > SelectCurrent {
    border: none;
    background: transparent;
    padding: 0 1 0 0;
}

#status-model Select.-textual-compact > SelectCurrent > Static#label {
    color: $foreground;
    width: auto;
}

#status-model Select > SelectOverlay {
    overlay: screen;
    constrain: none inside;
}

.status-tokens {
    width: auto;
    margin-right: 2;
    color: $foreground;
}

.status-queue {
    width: auto;
    margin-right: 2;
    color: $warning;
    display: none;
}

.status-queue.has-queue {
    display: block;
}

#status-progress {
    width: 15;
    margin-right: 2;
}

.status-time {
    width: auto;
    margin-right: 2;
    color: $foreground;
}

.status-tools {
    width: auto;
    color: $accent;
    margin-right: 1;
}

.status-mode-toggle {
    width: auto;
    color: $foreground;
    padding: 0 1;
    min-width: 2;
}

.status-mode-toggle:hover {
    color: $accent;
    background: $surface;
    border: none;
}

#status-right {
    width: 1fr;
    layout: horizontal;
    align: right middle;
}

.status-mode-toggle:focus {
    border: none;
}

/* ponytail: 限制代码块高度，防止长代码撑爆布局 (oterm 做法) */
MarkdownFence {
    max-height: 50;
}

/* 输入区域样式 */
#input-area {
    height: auto;
    width: 100%;
    dock: bottom;
    layout: vertical;
    padding: 0;
    margin: 0;
    border: none;
    background: rgba(177, 128, 215, 0.2);
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
    margin-top: 0;
}

#input-area Footer {
    dock: none;
    height: 1;
}

.input-field {
    border: blank;
    background: $surface;
    color: $foreground;
    padding: 0;
    height: 100%;
    width: 1fr;
}

.input-field:focus {
    border: heavy $accent;
}

#user-input {
    background: transparent;
    color: $foreground;
    margin: 0;
    height: 7;
    padding: 0;
    border: blank;
}

#user-input:focus,
#user-input:hover {
    border: blank;
}

/* === 斜杠命令补全浮层 === */
#slash-completion {
    display: none;
    height: auto;
    max-height: 5;
    background: $surface;
    border: solid $accent;
    padding: 0 1;
    width: 60%;
}

#slash-completion.visible {
    display: block;
}

#slash-completion > ListItem {
    padding: 0 1;
}

#slash-completion > ListItem:hover,
#slash-completion > ListItem.selected {
    background: $primary 20%;
}

/* === 侧边栏样式 === */
#sidebar-container {
    width: 50;
    height: 100%;
    background: transparent;
    border: blank;
    margin: 0;
    padding: 0;
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

/* ============================================================================
   半透明背景样式 (Frosted Glass Effect)
   支持 Ctrl+Shift+B 快捷键切换
   ============================================================================ */

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
    background: transparent;
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

"""
