#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kanban CLI Module

🚪 Access - 💬 CLI - Kanban 命令

Command-line interface for Kanban task management:
- kanban init      - Initialize board
- kanban create    - Create task
- kanban list      - List tasks
- kanban show      - Show task details
- kanban complete  - Complete task
- kanban block     - Block task
- kanban unblock   - Unblock task
- kanban comment   - Add comment
- kanban daemon    - Start scheduler

Usage:
    python -m cli.cli_commands.kanban init
    python -m cli.cli_commands.kanban create "Task Title" --assignee developer
    python -m cli.cli_commands.kanban list --status running
"""

import argparse
import json
import sys
from typing import Any, Dict, List

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color_success(msg: str) -> str:
    """Format success message with green color."""
    return f"{GREEN}✓ {msg}{RESET}"


def color_error(msg: str) -> str:
    """Format error message with red color."""
    return f"{RED}✗ {msg}{RESET}"


def color_warning(msg: str) -> str:
    """Format warning message with yellow color."""
    return f"{YELLOW}⚠ {msg}{RESET}"


def color_info(msg: str) -> str:
    """Format info message with blue color."""
    return f"{BLUE}ℹ {msg}{RESET}"


def print_success(msg: str) -> None:
    """Print success message."""
    print(color_success(msg))


def print_error(msg: str) -> None:
    """Print error message."""
    print(color_error(msg), file=sys.stderr)


def print_warning(msg: str) -> None:
    """Print warning message."""
    print(color_warning(msg))


def print_info(msg: str) -> None:
    """Print info message."""
    print(color_info(msg))


def format_table(headers: List[str], rows: List[List[str]]) -> str:
    """
    Format data as ASCII table.

    Args:
        headers: Column headers
        rows: Data rows

    Returns:
        Formatted table string
    """
    if not rows:
        # Print headers only with no data
        col_widths = [max(len(h), 10) for h in headers]
        header_line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        header_cells = "|".join(f" {h: <{col_widths[i]}} " for i, h in enumerate(headers))
        return f"{header_line}\n|{header_cells}|\n{header_line}"
    else:
        col_widths = [max(len(h), *[len(str(row[i])) for row in rows]) for i, h in enumerate(headers)]
        header_line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        header_cells = "|".join(f" {h: <{col_widths[i]}} " for i, h in enumerate(headers))

        lines = [header_line, f"|{header_cells}|", header_line]
        for row in rows:
            row_cells = "|".join(f" {str(row[i]): <{col_widths[i]}} " for i in range(len(row)))
            lines.append(f"|{row_cells}|")
        lines.append(header_line)

        return "\n".join(lines)


def parse_result(result_str: str) -> Dict[str, Any]:
    """
    Parse JSON result from kanban tool.

    Args:
        result_str: JSON string result

    Returns:
        Parsed dict

    Raises:
        json.JSONDecodeError: If parsing fails
    """
    return json.loads(result_str)


# =============================================================================
# Command Handlers
# =============================================================================


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new board."""
    from tools.kanban_tool import kanban_create_board

    result_str = kanban_create_board(args.name or "default")
    try:
        data = parse_result(result_str)
        if data.get("success"):
            board_id = data.get("board_id", "unknown")
            print_success(f"Board created: {data.get('name', args.name or 'default')}")
            print_info(f"Board ID: {board_id}")
        else:
            print_error(f"Failed to create board: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new task."""
    from tools.kanban_tool import kanban_create

    if not args.title:
        print_error("Title is required")
        sys.exit(1)

    result_str = kanban_create(
        board_id=args.board,
        title=args.title,
        assignee=args.assignee,
        body=args.body,
        priority=args.priority or 0,
        workspace_kind=args.workspace or "scratch",
        initial_status=args.status or "running",
    )

    try:
        data = parse_result(result_str)
        if data.get("success"):
            task_id = data.get("task_id", "unknown")
            print_success(f"Task created: {data.get('title', args.title)}")
            print_info(f"Task ID: {task_id}")
        else:
            print_error(f"Failed to create task: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List tasks with optional filters."""
    from tools.kanban_tool import kanban_list

    result_str = kanban_list(
        assignee=args.assignee,
        status=args.status,
        limit=args.limit or 50,
        board=args.board,
    )

    try:
        data = parse_result(result_str)
        if data.get("success"):
            tasks = data.get("tasks", [])
            total = data.get("total", 0)

            if not tasks:
                print_info("No tasks found")
                return

            # Format as table
            headers = ["ID", "Title", "Status", "Assignee", "Priority"]
            rows = []
            for task in tasks:
                rows.append([
                    str(task.get("id", ""))[:8],
                    (task.get("title", "") or "")[:30],
                    task.get("status", ""),
                    task.get("assignee", "-") or "-",
                    str(task.get("priority", 0)),
                ])

            print(format_table(headers, rows))
            print()
            print_info(f"Total: {total} task(s)")
        else:
            print_error(f"Failed to list tasks: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_show(args: argparse.Namespace) -> None:
    """Show task details."""
    from tools.kanban_tool import kanban_show

    result_str = kanban_show(task_id=args.task_id)

    try:
        data = parse_result(result_str)
        if data.get("success"):
            task = data.get("task", {})
            comments = data.get("comments", [])
            events = data.get("events", [])
            deps = data.get("dependencies", {})

            # Print task header
            print(f"{BOLD}Task Details{RESET}")
            print("=" * 50)
            print(f"ID:          {task.get('id', '')}")
            print(f"Title:       {task.get('title', '')}")
            print(f"Status:      {task.get('status', '')}")
            print(f"Priority:    {task.get('priority', 0)}")
            print(f"Assignee:    {task.get('assignee', '-') or '-'}")
            print(f"Blocked:     {task.get('blocked_reason', 'No') or 'No'}")
            print(f"Created:     {task.get('created_at', '')}")
            print(f"Updated:     {task.get('updated_at', '')}")

            if task.get("body"):
                print()
                print(f"{BOLD}Description:{RESET}")
                print(task.get("body", ""))

            # Dependencies
            parents = deps.get("parents", [])
            children = deps.get("children", [])
            if parents or children:
                print()
                print(f"{BOLD}Dependencies:{RESET}")
                if parents:
                    print(f"  Parents: {', '.join(parents)}")
                if children:
                    print(f"  Children: {', '.join(children)}")

            # Comments
            if comments:
                print()
                print(f"{BOLD}Comments ({len(comments)}):{RESET}")
                for comment in comments[-5:]:  # Show last 5 comments
                    author = comment.get("author", "unknown")
                    body = comment.get("body", "")
                    created = comment.get("created_at", "")[:19]
                    print(f"  [{created}] {author}: {body[:50]}")

            # Recent events
            if events:
                print()
                print(f"{BOLD}Recent Events:{RESET}")
                for event in events[-5:]:  # Show last 5 events
                    kind = event.get("kind", "")
                    created = event.get("created_at", "")[:19]
                    print(f"  [{created}] {kind}")

            print()
        else:
            print_error(f"Failed to show task: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_complete(args: argparse.Namespace) -> None:
    """Complete a task."""
    from tools.kanban_tool import kanban_complete

    result_str = kanban_complete(
        task_id=args.task_id,
        summary=args.summary,
        metadata=json.loads(args.metadata) if args.metadata else None,
        artifacts=args.artifacts,
    )

    try:
        data = parse_result(result_str)
        if data.get("success"):
            print_success(f"Task completed: {data.get('message', 'Done')}")
        else:
            print_error(f"Failed to complete task: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_block(args: argparse.Namespace) -> None:
    """Block a task."""
    from tools.kanban_tool import kanban_block

    result_str = kanban_block(task_id=args.task_id, reason=args.reason)

    try:
        data = parse_result(result_str)
        if data.get("success"):
            print_success(f"Task blocked: {data.get('message', args.reason)}")
        else:
            print_error(f"Failed to block task: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_unblock(args: argparse.Namespace) -> None:
    """Unblock a task."""
    from tools.kanban_tool import kanban_unblock

    result_str = kanban_unblock(task_id=args.task_id)

    try:
        data = parse_result(result_str)
        if data.get("success"):
            print_success(f"Task unblocked: {data.get('message', 'Done')}")
        else:
            print_error(f"Failed to unblock task: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_comment(args: argparse.Namespace) -> None:
    """Add a comment to a task."""
    from tools.kanban_tool import kanban_comment

    if not args.body:
        print_error("Comment body is required")
        sys.exit(1)

    result_str = kanban_comment(task_id=args.task_id, body=args.body)

    try:
        data = parse_result(result_str)
        if data.get("success"):
            print_success(f"Comment added: {data.get('message', 'Done')}")
        else:
            print_error(f"Failed to add comment: {data.get('error', 'Unknown error')}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse result: {e}")
        sys.exit(1)


def cmd_daemon(args: argparse.Namespace) -> None:
    """Start the Kanban scheduler daemon."""
    from tools.kanban_scheduler import KanbanScheduler

    scheduler = KanbanScheduler(
        dispatch_interval=args.interval or 60,
        claim_timeout=args.timeout or 300,
    )

    print_success(f"Kanban scheduler started")
    print_info(f"Dispatch interval: {args.interval or 60}s")
    print_info(f"Claim timeout: {args.timeout or 300}s")
    print()

    if args.foreground:
        print_info("Running in foreground. Press Ctrl+C to stop...")
        try:
            scheduler.start(background=False)
        except KeyboardInterrupt:
            print()
            print_info("Stopping scheduler...")
            scheduler.stop()
            print_success("Scheduler stopped")
    else:
        scheduler.start(background=True)
        print_success("Scheduler running in background")
        print_info("Use 'python -m cli.cli_commands.kanban daemon --foreground' to run in foreground")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Kanban task management CLI",
        prog="python -m cli.cli_commands.kanban",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -------------------------------------------------------------------------
    # init - Initialize board
    # -------------------------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new board",
        description="Create a new Kanban board",
    )
    init_parser.add_argument(
        "--name",
        "-n",
        type=str,
        default="default",
        help="Board name (default: default)",
    )
    init_parser.set_defaults(func=cmd_init)

    # -------------------------------------------------------------------------
    # create - Create task
    # -------------------------------------------------------------------------
    create_parser = subparsers.add_parser(
        "create",
        help="Create a new task",
        description="Create a new Kanban task",
    )
    create_parser.add_argument(
        "title",
        type=str,
        help="Task title",
    )
    create_parser.add_argument(
        "--board",
        "-b",
        type=str,
        default=None,
        help="Board ID",
    )
    create_parser.add_argument(
        "--assignee",
        "-a",
        type=str,
        default=None,
        help="Assignee",
    )
    create_parser.add_argument(
        "--body",
        "-d",
        type=str,
        default=None,
        help="Task description",
    )
    create_parser.add_argument(
        "--priority",
        "-p",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Priority (0=low, 1=medium, 2=high)",
    )
    create_parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        default="scratch",
        help="Workspace kind",
    )
    create_parser.add_argument(
        "--status",
        "-s",
        type=str,
        default="running",
        choices=["triage", "todo", "ready", "running", "done"],
        help="Initial status",
    )
    create_parser.set_defaults(func=cmd_create)

    # -------------------------------------------------------------------------
    # list - List tasks
    # -------------------------------------------------------------------------
    list_parser = subparsers.add_parser(
        "list",
        help="List tasks",
        description="List tasks with optional filters",
    )
    list_parser.add_argument(
        "--board",
        "-b",
        type=str,
        default=None,
        help="Board ID",
    )
    list_parser.add_argument(
        "--assignee",
        "-a",
        type=str,
        default=None,
        help="Filter by assignee",
    )
    list_parser.add_argument(
        "--status",
        "-s",
        type=str,
        default=None,
        help="Filter by status",
    )
    list_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=50,
        help="Maximum number of tasks to show",
    )
    list_parser.set_defaults(func=cmd_list)

    # -------------------------------------------------------------------------
    # show - Show task details
    # -------------------------------------------------------------------------
    show_parser = subparsers.add_parser(
        "show",
        help="Show task details",
        description="Show detailed information about a task",
    )
    show_parser.add_argument(
        "task_id",
        type=str,
        help="Task ID",
    )
    show_parser.set_defaults(func=cmd_show)

    # -------------------------------------------------------------------------
    # complete - Complete task
    # -------------------------------------------------------------------------
    complete_parser = subparsers.add_parser(
        "complete",
        help="Complete a task",
        description="Mark a task as completed",
    )
    complete_parser.add_argument(
        "task_id",
        type=str,
        help="Task ID",
    )
    complete_parser.add_argument(
        "--summary",
        type=str,
        default=None,
        help="Completion summary",
    )
    complete_parser.add_argument(
        "--metadata",
        type=str,
        default=None,
        help="Metadata as JSON string",
    )
    complete_parser.add_argument(
        "--artifacts",
        "-a",
        type=str,
        nargs="+",
        default=None,
        help="Artifacts list",
    )
    complete_parser.set_defaults(func=cmd_complete)

    # -------------------------------------------------------------------------
    # block - Block task
    # -------------------------------------------------------------------------
    block_parser = subparsers.add_parser(
        "block",
        help="Block a task",
        description="Block a task with a reason",
    )
    block_parser.add_argument(
        "task_id",
        type=str,
        help="Task ID",
    )
    block_parser.add_argument(
        "reason",
        type=str,
        help="Blocking reason",
    )
    block_parser.set_defaults(func=cmd_block)

    # -------------------------------------------------------------------------
    # unblock - Unblock task
    # -------------------------------------------------------------------------
    unblock_parser = subparsers.add_parser(
        "unblock",
        help="Unblock a task",
        description="Unblock a task",
    )
    unblock_parser.add_argument(
        "task_id",
        type=str,
        help="Task ID",
    )
    unblock_parser.set_defaults(func=cmd_unblock)

    # -------------------------------------------------------------------------
    # comment - Add comment
    # -------------------------------------------------------------------------
    comment_parser = subparsers.add_parser(
        "comment",
        help="Add a comment to a task",
        description="Add a comment to a task",
    )
    comment_parser.add_argument(
        "task_id",
        type=str,
        help="Task ID",
    )
    comment_parser.add_argument(
        "body",
        type=str,
        help="Comment content",
    )
    comment_parser.set_defaults(func=cmd_comment)

    # -------------------------------------------------------------------------
    # daemon - Start scheduler
    # -------------------------------------------------------------------------
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Start the Kanban scheduler",
        description="Start the background task scheduler",
    )
    daemon_parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=60,
        help="Dispatch interval in seconds (default: 60)",
    )
    daemon_parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=300,
        help="Claim timeout in seconds (default: 300)",
    )
    daemon_parser.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="Run in foreground instead of background",
    )
    daemon_parser.set_defaults(func=cmd_daemon)

    # Parse and execute
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Execute the command handler
    args.func(args)


if __name__ == "__main__":
    main()
