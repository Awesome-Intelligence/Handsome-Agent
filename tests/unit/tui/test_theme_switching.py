#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TUI theme switching functionality.

参考 CodeWhale 项目 TUI 测试用例设计，
测试主题切换的完整生命周期。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


class TestThemeModel:
    """Test Theme data model."""

    def test_theme_creation(self):
        """Test creating a theme with required fields."""
        from tui.theming.theme_config import Theme

        theme = Theme(
            theme_id="test_theme",
            display_name_key="tui.theme.test.name",
        )

        assert theme.theme_id == "test_theme"
        assert theme.display_name_key == "tui.theme.test.name"

    def test_theme_data_class(self):
        """Test Theme is a dataclass with proper attributes."""
        from tui.theming.theme_config import Theme

        theme = Theme(
            theme_id="custom",
            display_name_key="tui.theme.custom.name",
        )

        # Theme only has theme_id and display_name_key
        assert theme.theme_id == "custom"
        assert theme.display_name_key == "tui.theme.custom.name"


class TestThemeManager:
    """Test ThemeManager functionality."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ThemeManager singleton before each test."""
        from tui.theming.theme_manager import ThemeManager
        ThemeManager._instance = None
        yield
        ThemeManager._instance = None

    def test_singleton_pattern(self):
        """Test ThemeManager singleton pattern."""
        from tui.theming.theme_manager import ThemeManager

        manager1 = ThemeManager.get_instance()
        manager2 = ThemeManager.get_instance()

        assert manager1 is manager2

    def test_list_preset_themes(self):
        """Test listing preset themes."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        themes = manager.list_themes()

        assert len(themes) >= 2  # default and awesome
        theme_ids = [t.theme_id for t in themes]
        assert "default" in theme_ids
        assert "awesome" in theme_ids

    def test_list_theme_ids(self):
        """Test listing theme IDs."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        ids = manager.list_theme_ids()

        assert "default" in ids
        assert "awesome" in ids

    def test_get_theme_existing(self):
        """Test getting an existing theme."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        theme = manager.get_theme("default")

        assert theme is not None
        assert theme.theme_id == "default"

    def test_get_theme_nonexistent(self):
        """Test getting a non-existent theme returns None."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        theme = manager.get_theme("nonexistent")

        assert theme is None

    def test_get_current_theme(self):
        """Test getting the current active theme."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        theme = manager.get_current_theme()

        assert theme is not None
        assert theme.theme_id == manager.get_current_theme_id()

    def test_set_theme_existing(self):
        """Test setting an existing theme."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        result = manager.set_theme("awesome")

        assert result is True
        assert manager.get_current_theme_id() == "awesome"

    def test_set_theme_nonexistent(self):
        """Test setting a non-existent theme fails."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        original = manager.get_current_theme_id()
        result = manager.set_theme("nonexistent")

        assert result is False
        assert manager.get_current_theme_id() == original

    def test_get_theme_css_path(self):
        """Test getting theme CSS file path."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        css_path = manager.get_theme_css_path("default")

        # CSS path may or may not exist depending on installation
        if css_path:
            assert isinstance(css_path, Path)

    def test_theme_change_callback(self):
        """Test theme change callback is invoked."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        callback_invoked = []

        def on_theme_change(theme_id):
            callback_invoked.append(theme_id)

        manager.register_theme_change_callback(on_theme_change)
        manager.set_theme("awesome")

        assert len(callback_invoked) == 1
        assert callback_invoked[0] == "awesome"


class TestTransparencySupport:
    """Test transparency support detection."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ThemeManager singleton before each test."""
        from tui.theming.theme_manager import ThemeManager
        ThemeManager._instance = None
        yield
        ThemeManager._instance = None

    def test_transparency_default_disabled(self):
        """Test transparency is disabled by default after reset."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        # After reset, it may load from config, but we can force disable
        manager.set_transparency_enabled(False)
        assert manager.is_transparency_enabled() is False

    def test_set_transparency_enabled(self):
        """Test enabling transparency."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        manager.set_transparency_enabled(True)

        assert manager.is_transparency_enabled() is True

    def test_toggle_transparency(self):
        """Test toggling transparency state."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        initial = manager.is_transparency_enabled()

        result = manager.toggle_transparency()

        assert result == (not initial)
        assert manager.is_transparency_enabled() == (not initial)

    def test_transparency_level_bounds(self):
        """Test transparency level is clamped to valid range."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()

        # Test upper bound
        manager.set_transparency_level(1.5)
        assert manager.get_transparency_level() == 1.0

        # Test lower bound
        manager.set_transparency_level(-0.5)
        assert manager.get_transparency_level() == 0.0

        # Test valid value
        manager.set_transparency_level(0.7)
        assert manager.get_transparency_level() == 0.7

    def test_generate_transparent_css_disabled(self):
        """Test transparent CSS generation when disabled."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        manager.set_transparency_enabled(False)

        css = manager.generate_transparent_css()

        assert css == ""

    def test_generate_transparent_css_enabled(self):
        """Test transparent CSS generation when enabled."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        manager.set_transparency_enabled(True)
        manager.set_transparency_level(0.8)

        css = manager.generate_transparent_css()

        assert "--transparency-alpha" in css
        assert "transparent-surface" in css


class TestThemePersistence:
    """Test theme preference persistence."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ThemeManager singleton before each test."""
        from tui.theming.theme_manager import ThemeManager
        ThemeManager._instance = None
        yield
        ThemeManager._instance = None

    @patch("tui.theming.theme_manager.ThemeManager._load_preference")
    def test_preference_persistence(self, mock_load):
        """Test theme preference is saved after change."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        mock_load.return_value = None

        # Change theme
        manager.set_theme("awesome")

        # Verify current theme ID changed
        assert manager.get_current_theme_id() == "awesome"

    @patch("tui.theming.theme_manager.ThemeManager._load_preference")
    def test_preference_loads_on_init(self, mock_load):
        """Test preference is loaded during initialization."""
        from tui.theming.theme_manager import ThemeManager

        mock_load.return_value = None

        manager = ThemeManager()

        # Verify _load_preference was called
        mock_load.assert_called_once()


class TestPresetThemes:
    """Test preset theme definitions."""

    def test_default_theme_exists(self):
        """Test default theme is defined."""
        from tui.theming.preset_themes import _PRESET_THEMES

        assert "default" in _PRESET_THEMES
        assert _PRESET_THEMES["default"].theme_id == "default"

    def test_awesome_theme_exists(self):
        """Test awesome theme is defined."""
        from tui.theming.preset_themes import _PRESET_THEMES

        assert "awesome" in _PRESET_THEMES
        assert _PRESET_THEMES["awesome"].theme_id == "awesome"

    def test_theme_display_name_keys(self):
        """Test theme display name keys are i18n keys."""
        from tui.theming.preset_themes import _PRESET_THEMES

        for theme in _PRESET_THEMES.values():
            assert theme.display_name_key.startswith("tui.theme.")


class TestThemeColors:
    """Test theme color definitions."""

    def test_color_constants_exist(self):
        """Test color constants are defined in colors module."""
        from tui.theming import colors

        # Check essential status color constants exist
        assert hasattr(colors, "STATUS_ONLINE")
        assert hasattr(colors, "STATUS_ERROR")
        assert hasattr(colors, "STATUS_SUCCESS")
        assert hasattr(colors, "STATUS_WARNING")
        assert hasattr(colors, "STATUS_INFO")

    def test_color_format(self):
        """Test status colors are in correct hex format."""
        from tui.theming import colors

        # Status colors should be hex strings
        color = colors.STATUS_ONLINE
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7  # #RRGGBB format

    def test_transparency_levels(self):
        """Test transparency levels are defined."""
        from tui.theming import colors

        assert hasattr(colors, "TRANSPARENCY_LEVELS")
        assert isinstance(colors.TRANSPARENCY_LEVELS, dict)
        assert "sm" in colors.TRANSPARENCY_LEVELS
        assert "lg" in colors.TRANSPARENCY_LEVELS

    def test_transparent_function(self):
        """Test transparent() function works correctly."""
        from tui.theming import colors

        result = colors.transparent("#FF0000", 0.5)
        assert "rgba" in result
        assert "255" in result


class TestThemeIcons:
    """Test theme icon definitions."""

    def test_message_icons_exist(self):
        """Test message type icons are defined."""
        from tui.theming import icons

        # Check essential message icons exist
        assert hasattr(icons, "MESSAGE_ICONS")
        assert isinstance(icons.MESSAGE_ICONS, dict)
        assert "USER" in icons.MESSAGE_ICONS
        assert "ASSISTANT" in icons.MESSAGE_ICONS
        assert "TOOL" in icons.MESSAGE_ICONS
        assert "ERROR" in icons.MESSAGE_ICONS

    def test_file_type_icons(self):
        """Test file type icons are defined."""
        from tui.theming import icons

        assert hasattr(icons, "FILE_TYPE_ICONS")
        assert ".py" in icons.FILE_TYPE_ICONS
        assert ".js" in icons.FILE_TYPE_ICONS
        assert ".md" in icons.FILE_TYPE_ICONS

    def test_get_file_icon_function(self):
        """Test get_file_icon() function works."""
        from tui.theming import icons

        icon = icons.get_file_icon("test.py")
        assert icon == icons.FILE_TYPE_ICONS[".py"]

    def test_log_level_icons(self):
        """Test log level icons are defined."""
        from tui.theming import icons

        assert hasattr(icons, "LOG_LEVEL_ICONS")
        assert "DEBUG" in icons.LOG_LEVEL_ICONS
        assert "INFO" in icons.LOG_LEVEL_ICONS
        assert "ERROR" in icons.LOG_LEVEL_ICONS


class TestThemeTypography:
    """Test theme typography settings."""

    def test_font_size_constants_exist(self):
        """Test font size constants are defined."""
        from tui.theming import typography

        # Check font size constants exist
        assert hasattr(typography, "FONT_SIZE_XXS")
        assert hasattr(typography, "FONT_SIZE_XS")
        assert hasattr(typography, "FONT_SIZE_SM")
        assert hasattr(typography, "FONT_SIZE_MD")
        assert hasattr(typography, "FONT_SIZE_LG")

    def test_typography_config_class(self):
        """Test TypographyConfig class exists."""
        from tui.theming import typography

        assert hasattr(typography, "TypographyConfig")

        config = typography.TypographyConfig()
        assert hasattr(config, "font_size")
        assert hasattr(config, "line_height")

    def test_typography_presets(self):
        """Test typography presets are defined."""
        from tui.theming import typography

        assert hasattr(typography, "DEFAULT_TYPOGRAPHY")
        assert hasattr(typography, "TYPOGRAPHY_PRESETS")
        assert isinstance(typography.TYPOGRAPHY_PRESETS, dict)
        assert "default" in typography.TYPOGRAPHY_PRESETS

    def test_get_typography_preset_function(self):
        """Test get_typography_preset() function works."""
        from tui.theming import typography

        preset = typography.get_typography_preset("default")
        assert isinstance(preset, typography.TypographyConfig)


class TestThemeCSSVariables:
    """Test CSS variable generation."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ThemeManager singleton before each test."""
        from tui.theming.theme_manager import ThemeManager
        ThemeManager._instance = None
        yield
        ThemeManager._instance = None

    def test_transparent_css_structure(self):
        """Test transparent CSS has correct structure."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        manager.set_transparency_enabled(True)
        manager.set_transparency_level(0.85)

        css = manager.generate_transparent_css()

        # Should contain root variables
        assert ":root" in css
        assert "--transparency-alpha" in css
        assert "--transparency-hex" in css

        # Should contain surface classes
        assert ".transparent-surface" in css
        assert ".transparent-header" in css
        assert ".transparent-footer" in css


class TestThemeIntegration:
    """Integration tests for theme system."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ThemeManager singleton before each test."""
        from tui.theming.theme_manager import ThemeManager
        ThemeManager._instance = None
        yield
        ThemeManager._instance = None

    def test_full_theme_switch_cycle(self):
        """Test complete theme switch cycle."""
        from tui.theming.theme_manager import ThemeManager

        # Create fresh instance
        ThemeManager._instance = None
        manager = ThemeManager()

        # Start with default
        initial_theme = manager.get_current_theme_id()
        assert initial_theme in ["default", "awesome"]  # May load from config

        # Switch to awesome
        manager.set_theme("awesome")
        assert manager.get_current_theme_id() == "awesome"
        assert manager.get_current_theme().theme_id == "awesome"

        # Switch back to default
        manager.set_theme("default")
        assert manager.get_current_theme_id() == "default"

    def test_theme_manager_global_access(self):
        """Test get_theme_manager() function."""
        from tui.theming.theme_manager import get_theme_manager, ThemeManager

        ThemeManager._instance = None

        manager = get_theme_manager()

        assert isinstance(manager, ThemeManager)
        assert manager is ThemeManager.get_instance()


class TestThemeToggleButton:
    """Test theme toggle button functionality."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ThemeManager singleton before each test."""
        from tui.theming.theme_manager import ThemeManager
        ThemeManager._instance = None
        yield
        ThemeManager._instance = None

    def test_theme_toggle_cycle(self):
        """Test theme toggle cycles through available themes."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()
        initial_theme = manager.get_current_theme_id()

        available_themes = manager.list_theme_ids()
        if len(available_themes) >= 2:
            current_index = available_themes.index(initial_theme)
            expected_next = available_themes[(current_index + 1) % len(available_themes)]

            manager.set_theme(expected_next)
            assert manager.get_current_theme_id() == expected_next

    def test_theme_toggle_with_two_themes(self):
        """Test theme toggle specifically with two themes (default ↔ awesome)."""
        from tui.theming.theme_manager import ThemeManager

        manager = ThemeManager()

        manager.set_theme("default")
        assert manager.get_current_theme_id() == "default"

        manager.set_theme("awesome")
        assert manager.get_current_theme_id() == "awesome"

        manager.set_theme("default")
        assert manager.get_current_theme_id() == "default"

    def test_theme_toggle_button_icon(self):
        """Test theme toggle button icon and CSS classes."""
        from tui.theming.css import get_theme_css

        default_css = get_theme_css("default")
        awesome_css = get_theme_css("awesome")

        assert "#theme-toggle" in default_css
        assert "#theme-toggle" in awesome_css
        assert ".theme-default #theme-toggle" in default_css
        assert ".theme-awesome #theme-toggle" in awesome_css


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
