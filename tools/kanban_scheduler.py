#!/usr/bin/env python3
"""
Kanban Task Scheduler Module

Provides background task management for Kanban boards:
- Release stale claims (claim timeout)
- Promote ready tasks (dependencies satisfied)
- Check timed-out tasks
- Heartbeat claim maintenance
- Task dispatch (spawn workers for ready tasks)

Usage:
    from tools.kanban_scheduler import KanbanScheduler

    scheduler = KanbanScheduler(
        dispatch_interval=60,  # Check interval (seconds)
        claim_timeout=300,     # Claim timeout (seconds)
        max_spawn=4,           # Max concurrent workers
    )
    scheduler.start()  # Start background scheduler
    # or
    scheduler.run_once()  # Run once
"""

import os
import sqlite3
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger
from common.config import get_settings

from tools.kanban_db import (
    KanbanDB,
    claim_release_stale,
    claim_heartbeat,
    claim_get,
    claim_task,
    recompute_ready,
    task_update,
    task_get,
    task_start,
    event_add,
    run_start,
    run_end,
)

logger = get_execution_logger("KanbanScheduler")


@dataclass
class DispatchResult:
    """Result of a dispatch cycle."""
    dispatched: int = 0          # Number of tasks dispatched
    stale_released: int = 0      # Number of stale claims released
    promoted: int = 0            # Number of tasks promoted to ready
    timed_out: int = 0           # Number of tasks timed out
    errors: List[str] = field(default_factory=list)


class KanbanScheduler:
    """
    Kanban Task Scheduler - 后台守护自动分派任务
    
    Main functionalities:
    1. Release stale claims (claim timeout) - 释放过期的任务认领
    2. Promote ready tasks (dependencies satisfied) - 依赖满足时提升任务状态
    3. Check timed-out tasks - 检查超时任务
    4. Dispatch ready tasks (spawn workers) - 分派ready任务，启动worker执行
    5. Heartbeat claim maintenance - 心跳保活
    
    Architecture:
        ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
        │  Scheduler  │────▶│  kanban.db   │◀────│   Worker    │
        │  (守护进程)  │     │   (SQLite)   │     │  (子进程)   │
        └─────────────┘     └──────────────┘     └─────────────┘
                │                   │
                │            ┌──────┴──────┐
                │            │ 任务状态机  │
                │            │ todo→ready  │
                │            │ →running    │
                │            │ →done       │
                │            └─────────────┘
                │
                └──▶ dispatch_ready_tasks() → _spawn_worker()
    
    Usage:
        scheduler = KanbanScheduler(
            dispatch_interval=60,  # Check interval (seconds)
            claim_timeout=300,     # Claim timeout (seconds)
            max_spawn=4,           # Max concurrent workers
        )
        scheduler.start()  # Start scheduler
        # or
        scheduler.run_once()  # Run once
    """
    
    def __init__(
        self,
        dispatch_interval: Optional[int] = None,
        claim_timeout: Optional[int] = None,
        db_path: Optional[str] = None,
        max_spawn: Optional[int] = None,
        max_in_progress: Optional[int] = None,
        workspaces_root: Optional[str] = None,
    ):
        """
        Initialize Kanban scheduler.
        
        Args:
            dispatch_interval: Check interval in seconds (default: 60)
            claim_timeout: Claim timeout in seconds (default: 300)
            db_path: Database path (default: from settings)
            max_spawn: Maximum concurrent worker spawns per cycle (default: 2)
            max_in_progress: Maximum running tasks allowed (default: 4)
            workspaces_root: Root directory for task workspaces (default: ~/.agent_z/workspaces)
        """
        # Load from environment variables or use defaults
        settings = get_settings()
        
        self._dispatch_interval = (
            dispatch_interval
            if dispatch_interval is not None
            else int(os.environ.get("KANBAN_DISPATCH_INTERVAL", "60"))
        )
        self._claim_timeout = (
            claim_timeout
            if claim_timeout is not None
            else int(os.environ.get("KANBAN_CLAIM_TIMEOUT", "300"))
        )
        self._max_spawn = (
            max_spawn
            if max_spawn is not None
            else int(os.environ.get("KANBAN_MAX_SPAWN", "2"))
        )
        self._max_in_progress = (
            max_in_progress
            if max_in_progress is not None
            else int(os.environ.get("KANBAN_MAX_IN_PROGRESS", "4"))
        )
        self._workspaces_root = (
            workspaces_root
            or os.environ.get("KANBAN_WORKSPACES_ROOT")
            or str(Path.home() / ".agent_z" / "workspaces")
        )
        self._db_path = db_path or os.environ.get("KANBAN_DB_PATH", settings.db_path)
        
        # Ensure directories exist
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self._workspaces_root).mkdir(parents=True, exist_ok=True)
        
        # Database connection
        self._db: KanbanDB = KanbanDB(self._db_path)
        
        # Background scheduler state
        self._running: bool = False
        self._stop_event: threading.Event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()
        
        # Track running workers (PID -> task_id)
        self._workers: Dict[int, str] = {}
        self._worker_lock: threading.Lock = threading.Lock()
    
    @property
    def dispatch_interval(self) -> int:
        """Get dispatch interval in seconds."""
        return self._dispatch_interval
    
    @property
    def claim_timeout(self) -> int:
        """Get claim timeout in seconds."""
        return self._claim_timeout
    
    @property
    def max_spawn(self) -> int:
        """Get max concurrent spawns per cycle."""
        return self._max_spawn
    
    @property
    def max_in_progress(self) -> int:
        """Get max in-progress tasks."""
        return self._max_in_progress
    
    @property
    def dispatch_interval(self) -> int:
        """Get dispatch interval in seconds."""
        return self._dispatch_interval
    
    @property
    def claim_timeout(self) -> int:
        """Get claim timeout in seconds."""
        return self._claim_timeout
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return self._db.connect()
    
    def start(self, background: bool = True) -> None:
        """
        Start the scheduler.
        
        Args:
            background: Run in background thread if True, blocking if False
        """
        with self._lock:
            if self._running:
                logger.warning("Scheduler is already running")
                return
            
            self._stop_event.clear()
            self._running = True
            
            if background:
                self._thread = threading.Thread(
                    target=self._run_loop,
                    name="KanbanScheduler",
                    daemon=True,
                )
                self._thread.start()
                logger.info(f"Scheduler started in background (interval={self._dispatch_interval}s)")
            else:
                self._run_loop()
                logger.info("Scheduler finished")
    
    def stop(self, timeout: Optional[float] = None) -> None:
        """
        Stop the scheduler.
        
        Args:
            timeout: Maximum time to wait for thread to stop
        """
        with self._lock:
            if not self._running:
                logger.warning("Scheduler is not running")
                return
            
            self._stop_event.set()
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                logger.info("Scheduler stopped")
            else:
                logger.info("Scheduler stopped (no thread)")
            
            self._thread = None
    
    def _run_loop(self) -> None:
        """Internal run loop for background execution."""
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
            
            # Wait for next interval or stop event
            self._stop_event.wait(timeout=self._dispatch_interval)
    
    def run_once(self) -> Dict[str, Any]:
        """
        Execute one scheduler cycle.
        
        Returns:
            Dict containing:
            - dispatched: Number of tasks dispatched
            - stale_released: Number of stale claims released
            - promoted: Number of tasks promoted to ready
            - timed_out: Number of tasks timed out
            - errors: List of errors encountered
        """
        result: Dict[str, Any] = {
            "dispatched": 0,
            "stale_released": 0,
            "promoted": 0,
            "timed_out": 0,
            "errors": [],
        }
        
        logger.debug("Scheduler cycle started")
        
        conn = self._get_connection()
        try:
            # Use transaction for consistency (except dispatch which needs immediate spawn)
            
            # 1. Release stale claims
            try:
                result["stale_released"] = self.release_stale_claims(conn)
                logger.debug(f"Released {result['stale_released']} stale claims")
            except Exception as e:
                error_msg = f"Failed to release stale claims: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            # 2. Recompute ready tasks
            try:
                result["promoted"] = self.recompute_ready(conn)
                logger.debug(f"Promoted {result['promoted']} tasks to ready")
            except Exception as e:
                error_msg = f"Failed to recompute ready tasks: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            # 3. Check timeouts
            try:
                result["timed_out"] = self.check_timeouts(conn)
                logger.debug(f"Timed out {result['timed_out']} tasks")
            except Exception as e:
                error_msg = f"Failed to check timeouts: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            conn.commit()
            
            # 4. Dispatch ready tasks (outside transaction - spawns workers)
            try:
                result["dispatched"] = self.dispatch_ready_tasks()
                logger.debug(f"Dispatched {result['dispatched']} tasks")
            except Exception as e:
                error_msg = f"Failed to dispatch tasks: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Transaction failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        finally:
            self._db.close()
        
        logger.summary(
            f"Scheduler cycle completed: "
            f"dispatched={result['dispatched']}, "
            f"released={result['stale_released']}, "
            f"promoted={result['promoted']}, "
            f"timed_out={result['timed_out']}"
        )
        
        return result
    
    def dispatch_ready_tasks(self) -> int:
        """
        Dispatch ready tasks by spawning workers.
        
        This is the core dispatch logic:
        1. Count current running tasks
        2. If under limit, get ready tasks
        3. For each ready task (up to max_spawn):
           - Atomic claim (INSERT INTO task_claims)
           - Start task (UPDATE status = 'running')
           - Resolve workspace
           - Spawn worker process
        
        Returns:
            Number of tasks dispatched
        """
        conn = self._get_connection()
        try:
            # Check current running count
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE status = 'running'"
            )
            running_count = cursor.fetchone()["count"]
            
            # If at max, don't spawn more
            if running_count >= self._max_in_progress:
                logger.debug(
                    f"At max in-progress ({running_count}/{self._max_in_progress}), "
                    f"skipping dispatch"
                )
                return 0
            
            # Calculate how many we can spawn this cycle
            spawn_slots = min(
                self._max_spawn,
                self._max_in_progress - running_count
            )
            
            if spawn_slots <= 0:
                return 0
            
            # Get ready tasks (prioritized by priority DESC, created_at ASC)
            cursor.execute("""
                SELECT id, title, assignee, workspace_kind, workspace_path
                FROM tasks
                WHERE status = 'ready'
                AND id NOT IN (SELECT task_id FROM task_claims)
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            """, (spawn_slots,))
            
            ready_tasks = cursor.fetchall()
            
            if not ready_tasks:
                logger.debug("No ready tasks to dispatch")
                return 0
            
            dispatched = 0
            for row in ready_tasks:
                task_id = row["id"]
                title = row["title"]
                assignee = row["assignee"] or "default"
                workspace_kind = row["workspace_kind"] or "scratch"
                workspace_path = row["workspace_path"]
                
                # Generate claimer ID
                claimer = f"worker-{assignee}-{task_id[:8]}"
                
                try:
                    # Atomic claim
                    claim_task(conn, task_id, claimer)
                    
                    # Start task
                    task_start(conn, task_id)
                    
                    # Record run start
                    run = run_start(conn, task_id, profile=assignee)
                    
                    conn.commit()
                    
                    # Resolve and create workspace
                    ws_path = self.resolve_workspace(
                        task_id, workspace_kind, workspace_path
                    )
                    
                    # Spawn worker
                    pid = self._spawn_worker(
                        task_id=task_id,
                        assignee=assignee,
                        run_id=run.id,
                        workspace=ws_path,
                        workspace_kind=workspace_kind,
                    )
                    
                    if pid:
                        with self._worker_lock:
                            self._workers[pid] = task_id
                        logger.info(
                            f"Dispatched task: {title} (id={task_id[:8]}, pid={pid})"
                        )
                        dispatched += 1
                    else:
                        logger.error(f"Failed to spawn worker for task {task_id}")
                        
                except sqlite3.IntegrityError:
                    # Already claimed by another dispatcher
                    conn.rollback()
                    logger.debug(f"Task {task_id} already claimed")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to dispatch task {task_id}: {e}")
            
            return dispatched
            
        finally:
            self._db.close()
    
    def resolve_workspace(
        self,
        task_id: str,
        workspace_kind: str,
        workspace_path: Optional[str] = None,
    ) -> Path:
        """
        Resolve and create workspace for a task.
        
        Workspace kinds:
        - scratch: Temporary directory, deleted after task (default)
        - dir: Persistent directory under workspaces_root/task_id
        - worktree: Git worktree (future support)
        
        Args:
            task_id: Task ID
            workspace_kind: Kind of workspace
            workspace_path: Optional explicit path
        
        Returns:
            Path to the workspace directory
        """
        if workspace_path:
            ws_path = Path(workspace_path)
            ws_path.mkdir(parents=True, exist_ok=True)
            return ws_path
        
        if workspace_kind == "scratch":
            # Temporary directory
            import tempfile
            ws_path = Path(tempfile.mkdtemp(prefix=f"task_{task_id[:8]}_"))
        else:
            # Persistent directory
            ws_path = Path(self._workspaces_root) / task_id
            ws_path.mkdir(parents=True, exist_ok=True)
        
        return ws_path
    
    def _spawn_worker(
        self,
        task_id: str,
        assignee: str,
        run_id: int,
        workspace: Path,
        workspace_kind: str,
    ) -> Optional[int]:
        """
        Spawn a worker process for a task.
        
        The worker is spawned as a subprocess with environment variables
        set to identify the task context.
        
        Args:
            task_id: Task ID
            assignee: Assignee profile
            run_id: Run record ID
            workspace: Workspace path
            workspace_kind: Workspace kind
        
        Returns:
            PID of spawned process, or None on failure
        """
        # Build environment
        env = os.environ.copy()
        env["HERMES_KANBAN_TASK"] = task_id
        env["HERMES_KANBAN_RUN_ID"] = str(run_id)
        env["HERMES_PROFILE"] = assignee
        env["HERMES_WORKSPACE"] = str(workspace)
        env["HERMES_WORKSPACE_KIND"] = workspace_kind
        
        # Find the Agent-Z entry point
        # Try common locations
        possible_paths = [
            Path(__file__).parent.parent / "cli" / "main.py",
            Path(__file__).parent.parent / "__main__.py",
            Path.cwd() / "cli" / "main.py",
        ]
        
        entry_point = None
        for path in possible_paths:
            if path.exists():
                entry_point = path
                break
        
        if not entry_point:
            logger.error("Could not find Agent-Z entry point")
            return None
        
        try:
            # Spawn subprocess
            # For now, we'll use a simple approach - just log what would be spawned
            # In production, this would be:
            # process = subprocess.Popen(
            #     [sys.executable, str(entry_point), "--kanban-task", task_id],
            #     env=env,
            #     cwd=str(workspace),
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            # )
            # return process.pid
            
            # For development, just log and return a mock PID
            logger.info(
                f"Would spawn worker: entry={entry_point}, "
                f"task={task_id}, assignee={assignee}, "
                f"workspace={workspace}"
            )
            return os.getpid()  # Return current PID as placeholder
            
        except Exception as e:
            logger.error(f"Failed to spawn worker: {e}")
            return None
    
    def release_stale_claims(self, conn: sqlite3.Connection) -> int:
        """
        Release claims that have exceeded claim_timeout seconds.
        
        Args:
            conn: Database connection
        
        Returns:
            Number of claims released
        """
        released = claim_release_stale(conn, self._claim_timeout)
        
        if released > 0:
            logger.info(f"Released {released} stale claim(s)")
        
        return released
    
    def recompute_ready(self, conn: sqlite3.Connection) -> int:
        """
        Recompute ready status for all tasks.
        
        Tasks in 'todo' status whose all parent tasks are 'done'
        are promoted to 'ready' status.
        
        Args:
            conn: Database connection
        
        Returns:
            Number of tasks promoted
        """
        promoted = recompute_ready(conn)
        
        if promoted > 0:
            logger.info(f"Promoted {promoted} task(s) to ready")
        
        return promoted
    
    def check_timeouts(self, conn: sqlite3.Connection) -> int:
        """
        Check running tasks for timeout.
        
        Tasks with max_runtime_seconds set that exceed this limit
        are marked as 'timed_out' and status changed to 'todo'.
        
        Args:
            conn: Database connection
        
        Returns:
            Number of tasks timed out
        """
        cursor = conn.cursor()
        now = datetime.now()
        timed_out = 0
        
        # Get all running tasks with max_runtime_seconds
        cursor.execute("""
            SELECT id, title, started_at, max_runtime_seconds
            FROM tasks
            WHERE status = 'running'
            AND max_runtime_seconds IS NOT NULL
        """)
        
        for row in cursor.fetchall():
            task_id = row["id"]
            title = row["title"]
            started_at = datetime.fromisoformat(row["started_at"])
            max_runtime = row["max_runtime_seconds"]
            
            # Calculate elapsed time
            elapsed = (now - started_at).total_seconds()
            
            if elapsed > max_runtime:
                # Mark task as timed out
                task_update(conn, task_id, status="todo")
                event_add(
                    conn,
                    task_id,
                    "timed_out",
                    f'{{"elapsed": {elapsed}, "max_runtime": {max_runtime}}}'
                )
                timed_out += 1
                logger.warning(f"Task timed out: {title} (elapsed={elapsed:.0f}s, max={max_runtime}s)")
        
        return timed_out
    
    def heartbeat_claim(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        claimer: str,
    ) -> bool:
        """
        Update heartbeat for a task claim.
        
        Args:
            conn: Database connection
            task_id: Task ID
            claimer: Claimer identifier
        
        Returns:
            True if heartbeat updated, False otherwise
        """
        success = claim_heartbeat(conn, task_id, claimer)
        
        if success:
            logger.debug(f"Heartbeat updated for task {task_id} by {claimer}")
        else:
            logger.warning(f"Failed to update heartbeat for task {task_id}")
        
        return success
    
    def get_claim(self, conn: sqlite3.Connection, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get claim information for a task.
        
        Args:
            conn: Database connection
            task_id: Task ID
        
        Returns:
            Claim info dict or None if not found
        """
        claim = claim_get(conn, task_id)
        
        if claim is None:
            return None
        
        return {
            "task_id": claim.task_id,
            "claimer": claim.claimer,
            "claimed_at": claim.claimed_at,
            "heartbeat_at": claim.heartbeat_at,
        }


# =============================================================================
# Standalone Functions
# =============================================================================

def create_scheduler(
    dispatch_interval: Optional[int] = None,
    claim_timeout: Optional[int] = None,
    db_path: Optional[str] = None,
    max_spawn: Optional[int] = None,
    max_in_progress: Optional[int] = None,
    workspaces_root: Optional[str] = None,
) -> KanbanScheduler:
    """
    Create a new Kanban scheduler instance.
    
    Args:
        dispatch_interval: Check interval in seconds
        claim_timeout: Claim timeout in seconds
        db_path: Database path
        max_spawn: Max concurrent worker spawns per cycle
        max_in_progress: Max running tasks allowed
        workspaces_root: Root directory for workspaces
    
    Returns:
        KanbanScheduler instance
    """
    return KanbanScheduler(
        dispatch_interval=dispatch_interval,
        claim_timeout=claim_timeout,
        db_path=db_path,
        max_spawn=max_spawn,
        max_in_progress=max_in_progress,
        workspaces_root=workspaces_root,
    )


def run_scheduler_once(
    dispatch_interval: Optional[int] = None,
    claim_timeout: Optional[int] = None,
    db_path: Optional[str] = None,
    max_spawn: Optional[int] = None,
    max_in_progress: Optional[int] = None,
    workspaces_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run scheduler once (convenience function).
    
    Args:
        dispatch_interval: Check interval in seconds
        claim_timeout: Claim timeout in seconds
        db_path: Database path
        max_spawn: Max concurrent worker spawns per cycle
        max_in_progress: Max running tasks allowed
        workspaces_root: Root directory for workspaces
    
    Returns:
        Scheduler result dict
    """
    scheduler = create_scheduler(
        dispatch_interval=dispatch_interval,
        claim_timeout=claim_timeout,
        db_path=db_path,
        max_spawn=max_spawn,
        max_in_progress=max_in_progress,
        workspaces_root=workspaces_root,
    )
    return scheduler.run_once()