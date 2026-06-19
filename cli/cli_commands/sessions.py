#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sessions command - Session management

🚪 Access - 💬 CLI - 会话管理

提供会话列表和浏览功能。
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def list_sessions(json_output: bool = False) -> None:
    """List all sessions.
    
    Args:
        json_output: Output as JSON
    """
    from agent.session import session_manager
    from cli.components.colors import Colors, color
    
    sessions = session_manager.list_sessions()
    
    if not sessions:
        print("No sessions found.")
        return
    
    if json_output:
        import json
        print(json.dumps({"sessions": sessions}, indent=2))
        return
    
    print()
    print(color("  ID", Colors.BOLD), end="")
    print(" " * 40, end="")
    print(color("Created", Colors.DIM))
    print(color("-" * 70, Colors.DIM))
    
    for session_id in sessions:
        # Get session info
        session = session_manager.get_session(session_id)
        created = getattr(session, 'created_at', None)
        if created:
            created_str = created.strftime("%Y-%m-%d %H:%M")
        else:
            created_str = "Unknown"
        
        # Truncate ID for display
        display_id = session_id[:40] + "..." if len(session_id) > 40 else session_id
        
        print(f"  {display_id}  {color(created_str, Colors.DIM)}")
    
    print()


def browse_sessions(tui: bool = False) -> Optional[str]:
    """Browse sessions interactively.
    
    Args:
        tui: Use TUI picker if available
        
    Returns:
        Selected session ID or None
    """
    from agent.session import session_manager
    from cli.components.colors import Colors, color
    
    sessions = session_manager.list_sessions()
    
    if not sessions:
        print("No sessions found.")
        return None
    
    if tui:
        # Try to use TUI picker
        try:
            from tui.core.curses_ui import curses_radiolist
            index = curses_radiolist(
                question="Select a session:",
                choices=[(s[:50], s) for s in sessions],
            )
            if index >= 0:
                return sessions[index]
            return None
        except Exception:
            pass
    
    # Fallback to simple numbered list
    print()
    print(color("  Select a session:", Colors.BOLD))
    print()
    
    for i, session_id in enumerate(sessions[:20], 1):
        display_id = session_id[:60]
        print(f"  {i}. {display_id}")
    
    if len(sessions) > 20:
        print()
        print(color(f"  ... and {len(sessions) - 20} more", Colors.DIM))
    
    print()
    try:
        choice = input(color("  Enter number (or Enter to cancel): ", Colors.DIM)).strip()
        if not choice:
            return None
        
        index = int(choice) - 1
        if 0 <= index < len(sessions):
            return sessions[index]
    except (ValueError, EOFError):
        pass
    
    return None


def export_session(session_id: str, path: Path) -> None:
    """Export a session to a file.
    
    Args:
        session_id: Session ID to export
        path: Output file path
    """
    from agent.session import session_manager
    import json
    
    session = session_manager.get_session(session_id)
    if not session:
        print(f"Session not found: {session_id}")
        return
    
    data = {
        "session_id": session_id,
        "messages": [
            {"role": m.get("role"), "content": m.get("content")}
            for m in getattr(session, 'messages', [])
        ],
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Session exported to: {path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Session management")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    list_parser = subparsers.add_parser("list", help="List all sessions")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    browse_parser = subparsers.add_parser("browse", help="Browse sessions")
    browse_parser.add_argument("--tui", action="store_true", help="Use TUI picker")
    
    export_parser = subparsers.add_parser("export", help="Export a session")
    export_parser.add_argument("session_id", help="Session ID")
    export_parser.add_argument("output", help="Output file path")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_sessions(json_output=args.json)
    elif args.command == "browse":
        session = browse_sessions(tui=args.tui)
        if session:
            print(f"Selected: {session}")
    elif args.command == "export":
        export_session(args.session_id, Path(args.output))
    else:
        parser.print_help()