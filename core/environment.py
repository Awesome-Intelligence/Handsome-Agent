#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment detection module for cross-platform support.

Inspired by Hermes Agent's platform detection mechanism.
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PlatformInfo:
    """Platform information container."""
    os_type: str  # 'windows', 'macos', 'linux'
    os_name: str  # sys.platform value
    os_version: Optional[str] = None
    home_dir: str = ""
    desktop_dir: str = ""
    documents_dir: str = ""
    downloads_dir: str = ""
    pictures_dir: str = ""
    music_dir: str = ""
    videos_dir: str = ""


class EnvironmentDetector:
    """Detects and provides platform-specific environment information."""
    
    def __init__(self):
        self.platform_info = self._detect_platform()
        self._special_folders = self._get_special_folders()
    
    def _detect_platform(self) -> PlatformInfo:
        """Detect the current platform and return platform info."""
        os_name = sys.platform
        
        if os_name == 'win32':
            return PlatformInfo(
                os_type='windows',
                os_name=os_name,
                os_version=self._get_windows_version(),
                home_dir=os.path.expanduser('~'),
            )
        elif os_name == 'darwin':
            return PlatformInfo(
                os_type='macos',
                os_name=os_name,
                os_version=self._get_macos_version(),
                home_dir=os.path.expanduser('~'),
            )
        else:  # linux, freebsd, etc.
            return PlatformInfo(
                os_type='linux',
                os_name=os_name,
                os_version=self._get_linux_version(),
                home_dir=os.path.expanduser('~'),
            )
    
    def _get_windows_version(self) -> Optional[str]:
        """Get Windows version information."""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                return winreg.QueryValueEx(key, "ProductName")[0]
        except Exception:
            return None
    
    def _get_macos_version(self) -> Optional[str]:
        """Get macOS version information."""
        try:
            import subprocess
            result = subprocess.run(['sw_vers', '-productVersion'], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return None
    
    def _get_linux_version(self) -> Optional[str]:
        """Get Linux distribution information."""
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=')[1].strip('"')
            return os.uname().release
        except Exception:
            return None
    
    def _get_special_folders(self) -> Dict[str, str]:
        """Get platform-specific special folders."""
        folders = {}
        
        if self.platform_info.os_type == 'windows':
            folders = self._get_windows_special_folders()
        elif self.platform_info.os_type == 'macos':
            folders = self._get_macos_special_folders()
        else:  # linux
            folders = self._get_linux_special_folders()
        
        # Update platform info with detected paths
        for key, value in folders.items():
            if hasattr(self.platform_info, key):
                setattr(self.platform_info, key, value)
        
        return folders
    
    def _get_windows_special_folders(self) -> Dict[str, str]:
        """Get special folders on Windows."""
        home = os.path.expanduser('~')
        
        # Default paths (works on all platforms)
        default_paths = {
            'desktop_dir': os.path.join(home, 'Desktop'),
            'documents_dir': os.path.join(home, 'Documents'),
            'downloads_dir': os.path.join(home, 'Downloads'),
            'pictures_dir': os.path.join(home, 'Pictures'),
            'music_dir': os.path.join(home, 'Music'),
            'videos_dir': os.path.join(home, 'Videos'),
        }
        
        # Try to get paths from environment variables first
        env_paths = {}
        env_mapping = {
            'desktop_dir': 'USERPROFILE',
            'documents_dir': 'USERPROFILE',
            'downloads_dir': 'USERPROFILE',
            'pictures_dir': 'USERPROFILE',
            'music_dir': 'USERPROFILE',
            'videos_dir': 'USERPROFILE',
        }
        
        for key, env_var in env_mapping.items():
            if env_var in os.environ:
                env_paths[key] = os.path.join(os.environ[env_var], 
                                              key.replace('_dir', '').capitalize())
        
        # Merge env paths with defaults
        paths = {**default_paths, **env_paths}
        
        # Try win32com as final fallback (for localized paths and moved folders)
        try:
            from win32com.shell import shell, shellcon
            paths.update({
                'desktop_dir': shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, None, 0),
                'documents_dir': shell.SHGetFolderPath(0, shellcon.CSIDL_DOCUMENTS, None, 0),
                'downloads_dir': shell.SHGetFolderPath(0, shellcon.CSIDL_DOWNLOADS, None, 0),
                'pictures_dir': shell.SHGetFolderPath(0, shellcon.CSIDL_PICTURES, None, 0),
                'music_dir': shell.SHGetFolderPath(0, shellcon.CSIDL_MUSIC, None, 0),
                'videos_dir': shell.SHGetFolderPath(0, shellcon.CSIDL_VIDEOS, None, 0),
            })
        except Exception:
            pass
        
        # Verify paths exist and search common alternatives if not
        for key, path in list(paths.items()):
            if not os.path.exists(path):
                # Try to find the folder in alternative locations
                folder_name = key.replace('_dir', '')
                alternatives = self._find_folder_alternatives(folder_name)
                if alternatives:
                    paths[key] = alternatives[0]
        
        return paths
    
    def _get_macos_special_folders(self) -> Dict[str, str]:
        """Get special folders on macOS."""
        home = os.path.expanduser('~')
        return {
            'desktop_dir': os.path.join(home, 'Desktop'),
            'documents_dir': os.path.join(home, 'Documents'),
            'downloads_dir': os.path.join(home, 'Downloads'),
            'pictures_dir': os.path.join(home, 'Pictures'),
            'music_dir': os.path.join(home, 'Music'),
            'videos_dir': os.path.join(home, 'Movies'),
        }
    
    def _get_linux_special_folders(self) -> Dict[str, str]:
        """Get special folders on Linux (XDG standard)."""
        home = os.path.expanduser('~')
        
        def get_xdg_dir(env_var, fallback):
            return os.environ.get(env_var, os.path.join(home, fallback))
        
        return {
            'desktop_dir': get_xdg_dir('XDG_DESKTOP_DIR', 'Desktop'),
            'documents_dir': get_xdg_dir('XDG_DOCUMENTS_DIR', 'Documents'),
            'downloads_dir': get_xdg_dir('XDG_DOWNLOAD_DIR', 'Downloads'),
            'pictures_dir': get_xdg_dir('XDG_PICTURES_DIR', 'Pictures'),
            'music_dir': get_xdg_dir('XDG_MUSIC_DIR', 'Music'),
            'videos_dir': get_xdg_dir('XDG_VIDEOS_DIR', 'Videos'),
        }
    
    def _find_folder_alternatives(self, folder_name: str) -> list:
        """Find alternative locations for a folder that might have been moved."""
        alternatives = []
        home = os.path.expanduser('~')
        
        # Common alternative drives on Windows
        drives = ['C:\\', 'D:\\', 'E:\\', 'F:\\']
        
        # Possible folder names (case-insensitive)
        possible_names = [
            folder_name,
            folder_name.capitalize(),
            folder_name.upper(),
        ]
        
        for drive in drives:
            if not os.path.exists(drive):
                continue
            for name in possible_names:
                path = os.path.join(drive, name)
                if os.path.exists(path) and os.path.isdir(path):
                    alternatives.append(path)
        
        return alternatives
    
    def get_folder_path(self, folder_name: str) -> Optional[str]:
        """Get the path for a special folder by name."""
        folder_name = folder_name.lower().replace(' ', '_')
        
        # Mapping from common names to internal keys
        name_mapping = {
            'desktop': 'desktop_dir',
            'documents': 'documents_dir',
            'downloads': 'downloads_dir',
            'pictures': 'pictures_dir',
            'music': 'music_dir',
            'videos': 'videos_dir',
            'download': 'downloads_dir',
            'picture': 'pictures_dir',
            'photo': 'pictures_dir',
            'photos': 'pictures_dir',
            'document': 'documents_dir',
            'video': 'videos_dir',
            'home': 'home_dir',
            '~': 'home_dir',
        }
        
        key = name_mapping.get(folder_name)
        if key:
            return getattr(self.platform_info, key, None)
        
        return None
    
    def is_platform_supported(self, platform: str) -> bool:
        """Check if the current platform matches the required platform."""
        platform_mapping = {
            'windows': ['windows', 'win32'],
            'macos': ['macos', 'darwin'],
            'linux': ['linux'],
            'unix': ['linux', 'darwin'],
        }
        
        supported = platform_mapping.get(platform.lower())
        if supported:
            return self.platform_info.os_type in supported or self.platform_info.os_name in supported
        
        return False
    
    def get_environment_context(self) -> Dict[str, any]:
        """Get environment context for injection into handlers."""
        return {
            'platform': self.platform_info.os_type,
            'os_name': self.platform_info.os_name,
            'os_version': self.platform_info.os_version,
            'home_dir': self.platform_info.home_dir,
            'desktop_dir': self.platform_info.desktop_dir,
            'documents_dir': self.platform_info.documents_dir,
            'downloads_dir': self.platform_info.downloads_dir,
            'pictures_dir': self.platform_info.pictures_dir,
            'music_dir': self.platform_info.music_dir,
            'videos_dir': self.platform_info.videos_dir,
        }


# Create singleton instance
env_detector = EnvironmentDetector()