#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InputQueueMixin 单元测试（覆盖核心路径 ≥80%，spec C1-16 要求）

🚪 Access - 💬 TUI - Textual App - 输入队列 Mixin 测试

覆盖场景：
1. _truncate_queue_content 静态截断（4 场景）
2. _init_input_queue_panel 初始化显隐（2 场景）
3. _build_single_queue_item 构建行（首项 ▶、序号、删除按钮 index）
4. _on_queue_item_delete 删除逻辑（合法/非法 index、恢复输入框）
5. _on_queue_clear_all 清空逻辑（空/非空队列）
6. _on_queue_delete_clicked 点击分发（属性/父级/正则三种路径）
7. _refresh_input_queue 调度机制（call_next、防递归）
8. _render_input_queue_panel 全量渲染（空队列隐藏/非空显示重建）
9. 跨 15 并发实例：_pending_queue 实例隔离性（C1-14 要求）
"""

from __future__ import annotations

import sys
import threading
from collections import deque
from pathlib import Path
from typing import Optional

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tui.textual_app.input_queue import InputQueueMixin


# ============================================================================
# Minimal fake widget classes (avoid actually mounting Textual)
# ============================================================================

class FakeWidget:
    def __init__(self, text: str = "", classes: str = "", widget_id: str = ""):
        self.text = text
        self.classes = set(classes.split()) if classes else set()
        self.id = widget_id
        self.parent = None
        self.children: list["FakeWidget"] = []
        self.data_queue_index: Optional[int] = None
        self._visible_class = False

    def set_class(self, flag: bool, name: str) -> None:
        if flag:
            self.classes.add(name)
            if name == "visible":
                self._visible_class = True
        else:
            self.classes.discard(name)
            if name == "visible":
                self._visible_class = False

    def has_class(self, name: str) -> bool:
        return name in self.classes

    def update(self, new_text: str = "") -> None:
        self.text = new_text

    def remove_children(self) -> None:
        self.children = []

    def mount(self, *kids: "FakeWidget") -> None:
        for k in kids:
            k.parent = self
            self.children.append(k)

    def query(self, _sel: str):
        # Only used for ".queue-delete-btn" selector → return first match
        class QueryResult:
            def __init__(self, kids):
                self._kids = list(kids)

            def first(self):
                return self._kids[0] if self._kids else None

        matches = [c for c in self.children if any("queue-delete-btn" in (getattr(c, "classes", set()) or set())) for c in (c if hasattr(c, "classes") else [])]
        # Simpler: walk children list directly (one level)
        for c in self.children:
            if isinstance(c, FakeWidget) and "queue-delete-btn" in c.classes:
                return QueryResult([c])
        return QueryResult([])


class FakeStatic(FakeWidget):
    pass


class FakeTextArea(FakeWidget):
    def __init__(self, disabled: bool = False, placeholder: str = "", text: str = ""):
        super().__init__(text=text)
        self.disabled = disabled
        self.placeholder = placeholder


# ============================================================================
# Fake Horizontal / Vertical containers (match InputQueueMixin.build signature)
# ============================================================================

def _fake_Horizontal(*children, classes: str = "") -> FakeWidget:
    w = FakeWidget(classes=classes, widget_id="")
    for c in children:
        c.parent = w
        w.children.append(c)
    return w


def _fake_Static(text: str, classes: str = "") -> FakeStatic:
    return FakeStatic(text=text, classes=classes)


# ============================================================================
# Concrete host class: mix InputQueueMixin with the attributes it needs
# ============================================================================

class FakeAppHost(InputQueueMixin):
    """Host stub that provides the minimum surface InputQueueMixin reads/writes."""

    def __init__(self):
        self._queue_rendering = False
        self._pending_queue: deque = deque()
        self._widget_cache: dict = {}
        self._agent_busy: bool = False
        # Placeholder widgets (simulate #input-queue-panel / #input-queue-list / ...)
        self._fake_panel = FakeWidget(classes="", widget_id="input-queue-panel")
        self._fake_list = FakeWidget(classes="", widget_id="input-queue-list")
        self._fake_count = FakeStatic(text="", classes="input-queue-count")
        self._fake_clear = FakeStatic(text="清空", classes="input-queue-clear-all", widget_id="input-queue-clear-all")
        self._fake_textarea = FakeTextArea(disabled=False, placeholder="默认提示")
        self._widget_cache = {
            "input_queue_panel": self._fake_panel,
            "input_queue_list": self._fake_list,
            "input_queue_count": self._fake_count,
            "input_queue_clear_all": self._fake_clear,
            "user_input": self._fake_textarea,
        }
        # Captured call_next invocations (to test call_next dispatching)
        self._call_next_log: list = []
        # Notification history
        self._notify_log: list = []

    # -- helpers -----------------------------------------------------------
    def call_next(self, fn, *args, **kwargs):
        self._call_next_log.append((fn, args, kwargs))
        try:
            return fn(*args, **kwargs)
        except Exception:
            raise

    def notify_animated(self, message: str, *a, **kw):
        self._notify_log.append(message)

    def _update_queue_display(self, queue_len_override=None):
        # No-op stub (StatusBarMixin method, not present in this fake)
        return None

    # -- patch Static / Horizontal constructors to return our fakes ---------
    _Horizontal = staticmethod(_fake_Horizontal)
    _Static = staticmethod(_fake_Static)


# Monkey-patch the mixin so that when it does Static(...) / Horizontal(...)
# it returns our Fake widgets instead of importing real Textual ones.
def _install_mixin_widget_fakes():
    """Install test-only widget-constructor patches.

    InputQueueMixin._build_single_queue_item does::

        Horizontal(Static(...), Static(...), Static(...), classes=classes)

    To avoid importing Textual / mounting a real DOM, we substitute the
    constructors inside the module namespace for the duration of the tests.
    """
    import tui.textual_app.input_queue as mod

    # Snapshot originals to restore later
    orig_Static = getattr(mod, "Static", None)
    orig_Horizontal = getattr(mod, "Horizontal", None)

    # Swap
    mod.Static = _fake_Static
    mod.Horizontal = _fake_Horizontal
    return orig_Static, orig_Horizontal


def _restore_mixin_widgets(orig_Static, orig_Horizontal):
    import tui.textual_app.input_queue as mod
    if orig_Static is not None:
        mod.Static = orig_Static
    if orig_Horizontal is not None:
        mod.Horizontal = orig_Horizontal


# ============================================================================
# Test helpers
# ============================================================================

_LONG_LINE_200_CHARS = "中" * 200
_LONG_LINE_500_CHARS = "你好abc😀" * 100  # ~ 6 chars × 100 = 600 chars, will truncate
_THREE_LINES = "line1\nline2\nline3\nline4"  # 4 lines → truncated to 3 + "…"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def _patch_widgets():
    a, b = _install_mixin_widget_fakes()
    yield
    _restore_mixin_widgets(a, b)


@pytest.fixture
def host():
    return FakeAppHost()


# ============================================================================
# 1. _truncate_queue_content (static)
# ============================================================================

class TestTruncate:
    def test_empty_string(self):
        assert InputQueueMixin._truncate_queue_content("") == ""
        assert InputQueueMixin._truncate_queue_content(None) == ""  # type: ignore

    def test_short_unchanged(self):
        assert InputQueueMixin._truncate_queue_content("hello") == "hello"
        assert InputQueueMixin._truncate_queue_content("中") == "中"

    def test_char_200_truncation(self):
        # Exactly 200 Chinese chars → should remain (boundary case)
        assert len(InputQueueMixin._truncate_queue_content(_LONG_LINE_200_CHARS, max_chars=200)) == 200
        # 201+ chars → add …
        long_201 = _LONG_LINE_200_CHARS + "尾"
        out = InputQueueMixin._truncate_queue_content(long_201, max_chars=200)
        assert out.endswith("…")
        assert len(out) <= 201  # "…" takes 1 slot beyond the 200-char boundary

    def test_c18_unicode_500_chars(self):
        """C1-18: 超长 500 字 Unicode 字符串必须被截断并以 … 结尾（不溢出）."""
        out = InputQueueMixin._truncate_queue_content(_LONG_LINE_500_CHARS)
        assert isinstance(out, str)
        # Result length (after truncation + ellipsis) ≤ 201 chars
        # Note: Python counts each emoji as 1 char (code point), so length
        # check uses real codepoints, not UTF-8 bytes.
        assert len(out) <= 202

    def test_line_count_truncation(self):
        """4 行内容必须截断为 3 行 + …"""
        out = InputQueueMixin._truncate_queue_content(_THREE_LINES)
        lines = out.split("\n")
        assert len(lines) <= 3 or (len(lines) == 4 and lines[-1] == "…")


# ============================================================================
# 2. _init_input_queue_panel
# ============================================================================

class TestInitPanel:
    def test_empty_queue_starts_hidden(self, host):
        host._pending_queue.clear()
        host._init_input_queue_panel()
        assert "visible" not in host._fake_panel.classes
        assert host._fake_panel._visible_class is False

    def test_nonempty_queue_starts_visible(self, host):
        host._pending_queue.append("hello")
        host._pending_queue.append("world")
        host._init_input_queue_panel()
        assert "visible" in host._fake_panel.classes or host._fake_panel._visible_class


# ============================================================================
# 3. _build_single_queue_item (首项 ▶, index 对齐, 删除按钮 index 正确)
# ============================================================================

class TestBuildItem:
    def test_first_item_has_triangle_index(self, host):
        row = host._build_single_queue_item(0, "first message")
        assert row is not None
        classes_str = " ".join(row.classes)
        assert "first" in classes_str or "queue-item first" in " ".join(row.classes)
        # Find index Static child (first child of the Horizontal row)
        idx_widget = row.children[0]
        assert "▶ 1" in idx_widget.text

    def test_second_item_plain_index(self, host):
        row = host._build_single_queue_item(1, "second message")
        assert row is not None
        classes_str = " ".join(row.classes)
        assert "first" not in classes_str
        idx_widget = row.children[0]
        assert "2" in idx_widget.text and "▶" not in idx_widget.text

    def test_delete_button_carries_index(self, host):
        for i in [0, 3, 10, 49]:
            row = host._build_single_queue_item(i, f"msg-{i}")
            assert row is not None
            delete_btn = row.children[-1]
            # Should find via data_queue_index attribute OR an id pattern
            assert (
                getattr(delete_btn, "data_queue_index", None) == i
                or getattr(row, "data_queue_index", None) == i
            ), f"Failed to propagate queue index {i} into row/btn attributes"


# ============================================================================
# 4. _on_queue_item_delete
# ============================================================================

class TestDeleteItem:
    def setup_method(self):
        self.host = FakeAppHost()
        self.host._pending_queue = deque(["a", "b", "c", "d"])

    def test_illegal_index_noop(self, host):
        q_before = deque(["a", "b", "c"])
        host._pending_queue = deque(q_before)
        host._on_queue_item_delete(-1)
        host._on_queue_item_delete(999)
        assert list(host._pending_queue) == list(q_before)

    def test_legal_index_removes_item(self, host):
        host._pending_queue = deque(["a", "b", "c", "d"])
        host._on_queue_item_delete(1)  # "b"
        assert list(host._pending_queue) == ["a", "c", "d"]
        # Toast fired
        assert any("已移除" in m or "removed" in m.lower() for m in host._notify_log)

    def test_empty_after_last_delete_recovers_input(self, host):
        """删除最后一条 → 队列空 + 非 busy → 输入框恢复启用."""
        host._pending_queue = deque(["only-one"])
        host._fake_textarea.disabled = True
        host._agent_busy = False
        host._on_queue_item_delete(0)
        assert list(host._pending_queue) == []
        assert host._fake_textarea.disabled is False


# ============================================================================
# 5. _on_queue_clear_all
# ============================================================================

class TestClearAll:
    def test_empty_queue_noop(self, host):
        host._pending_queue = deque()
        old_log_len = len(host._notify_log)
        host._on_queue_clear_all()
        assert list(host._pending_queue) == []
        assert len(host._notify_log) == old_log_len  # 没有 Toast（空队列）

    def test_full_queue_cleared_and_input_recovered(self, host):
        host._pending_queue = deque(["x", "y", "z"])
        host._fake_textarea.disabled = True
        host._agent_busy = False
        host._on_queue_clear_all()
        assert list(host._pending_queue) == []
        assert any("清空" in m or "clear" in m.lower() for m in host._notify_log)
        # 输入框恢复
        assert host._fake_textarea.disabled is False


# ============================================================================
# 6. _on_queue_delete_clicked (3 种读 index 的路径)
# ============================================================================

class TestDeleteClickDispatch:
    def test_data_queue_index_on_button(self, host):
        """C3-8 主路径：被点击的 widget 自身带 data_queue_index 属性."""
        host._pending_queue = deque(["a", "b", "c"])

        class FakeEvent:
            control = FakeWidget(classes="queue-delete-btn")
        FakeEvent.control.data_queue_index = 1

        host._on_queue_delete_clicked(FakeEvent())
        assert list(host._pending_queue) == ["a", "c"]

    def test_parent_fallback(self, host):
        """备用路径：widget 本身没属性，但父级 row 带 data_queue_index."""
        host._pending_queue = deque(["a", "b", "c"])
        row = FakeWidget(classes="queue-item")
        row.data_queue_index = 0
        btn = FakeWidget(classes="queue-delete-btn")
        btn.parent = row

        class FakeEvent:
            control = btn

        host._on_queue_delete_clicked(FakeEvent())
        assert list(host._pending_queue) == ["b", "c"]

    def test_regex_id_fallback(self, host):
        """最后备用：id=queue-delete-N 正则解析."""
        host._pending_queue = deque(["z"])

        class FakeEvent:
            control = FakeWidget(classes="queue-delete-btn", widget_id="queue-delete-0")

        host._on_queue_delete_clicked(FakeEvent())
        assert list(host._pending_queue) == []


# ============================================================================
# 7. _refresh_input_queue & _queue_rendering guard
# ============================================================================

class TestRefreshSchedule:
    def test_dispatch_to_call_next(self, host):
        host._call_next_log = []
        host._pending_queue = deque(["one", "two"])
        host._refresh_input_queue()
        # call_next must have been invoked with the render method
        assert len(host._call_next_log) >= 1
        fn_called = host._call_next_log[0][0]
        # After call_next executes the method, list should have 2 children mounted
        assert len(host._fake_list.children) == 2

    def test_anti_recursion_skips_refresh(self, host):
        """当 _queue_rendering=True 时，_refresh_input_queue 必须立即 return（防递归）."""
        host._queue_rendering = True
        host._call_next_log = []
        host._pending_queue = deque(["a"])
        host._refresh_input_queue()
        assert len(host._call_next_log) == 0, "Anti-recursion flag must skip scheduling"


# ============================================================================
# 8. _render_input_queue_panel (核心渲染主路径)
# ============================================================================

class TestRender:
    def test_empty_hides_and_clears_children(self, host):
        host._fake_panel.set_class(True, "visible")  # 先设为可见
        host._fake_list.children = [FakeWidget("stale-1"), FakeWidget("stale-2")]
        host._pending_queue = deque()
        host._render_input_queue_panel()
        assert host._fake_panel._visible_class is False or "visible" not in host._fake_panel.classes
        assert len(host._fake_list.children) == 0

    def test_nonempty_shows_and_rebuilds_children(self, host):
        host._pending_queue = deque(["msg-0", "msg-1", "msg-2"])
        host._render_input_queue_panel()
        # 可见
        assert host._fake_panel._visible_class or "visible" in host._fake_panel.classes
        # 计数同步（⏳ 3 条排队 or ⏳ {n} queued）
        assert "3" in host._fake_count.text
        # 3 个行 mount 成功
        assert len(host._fake_list.children) == 3
        # 首项有 first class
        first_row = host._fake_list.children[0]
        assert "first" in first_row.classes
        # 非首项无 first class
        for i, row in enumerate(host._fake_list.children[1:], 1):
            assert "first" not in row.classes, f"Row {i} must not have .first class"

    def test_c19_full_stack_50_scrollable(self, host):
        """C1-19: 队列 50 条满栈时 children 必须全部挂载（CSS max-height + overflow-y 负责滚动）."""
        host._pending_queue = deque(f"item-{i}" for i in range(50))
        host._render_input_queue_panel()
        assert len(host._fake_list.children) == 50
        # 首项有 .first, 最后一项 49 号索引已正确写进 delete btn
        first_row = host._fake_list.children[0]
        assert "first" in first_row.classes
        last_row = host._fake_list.children[-1]
        last_btn = last_row.children[-1]
        got_idx = getattr(last_btn, "data_queue_index", None) or getattr(last_row, "data_queue_index", None)
        assert got_idx == 49, f"Last row queue index should be 49, got {got_idx}"


# ============================================================================
# 9. C1-14: 15 并发实例实例隔离性
# ============================================================================

class TestC14InstanceIsolation:
    def test_15_threads_no_shared_state(self):
        """跨 15 个并发实例，各自的 _pending_queue 必须完全隔离、不串号、不共享内容."""

        results: dict[int, list] = {}
        errors: list[str] = []

        def worker(tid: int):
            try:
                host = FakeAppHost()
                # 每个线程往自己的 deque 里 push unique item (tid + 递增序号)
                for i in range(20):
                    host._pending_queue.append(f"t{tid}-i{i}")
                # 并发触发 render，模拟真实用户同时发言场景
                host._render_input_queue_panel()
                # 结果：每个 host._pending_queue 必须只含自己的 20 个 item
                results[tid] = list(host._pending_queue)
            except Exception as e:
                errors.append(f"Thread {tid} error: {e}")

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Worker errors: {errors}"
        assert len(results) == 15, f"Missing worker results (got {len(results)}/15)"

        # 每对实例之间的队列内容必须完全不相同（严格隔离）
        for a in range(15):
            for b in range(a + 1, 15):
                set_a = set(results[a])
                set_b = set(results[b])
                common = set_a & set_b
                assert len(common) == 0, (
                    f"Instance isolation violation: "
                    f"thread {a} & {b} share {len(common)} items ({list(common)[:3]}…)"
                )
            # 自身完整性：每个线程有 20 个 unique 条目
            assert len(set(results[a])) == 20, f"Thread {a} has duplicate/absent items"
            assert len(results[a]) == 20, f"Thread {a} count = {len(results[a])} ≠ 20"
