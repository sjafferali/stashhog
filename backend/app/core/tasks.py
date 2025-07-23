"""
Background task queue implementation.

This provides a simple in-memory task queue using asyncio.
For production, consider using Celery, RQ, or similar.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a background task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskQueue:
    """Simple in-memory task queue using asyncio."""

    def __init__(self, max_workers: int = 5):
        """
        Initialize task queue.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.max_workers = max_workers
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, Task] = {}
        self.workers: List[asyncio.Task] = []
        self._running = False
        self._task_callbacks: Dict[str, List[Callable]] = {}

    async def start(self) -> None:
        """Start the task queue workers."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting task queue with {self.max_workers} workers")

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

    async def stop(self) -> None:
        """Stop the task queue workers."""
        if not self._running:
            return

        logger.info("Stopping task queue")
        self._running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def _worker(self, worker_id: str) -> None:
        """
        Worker coroutine that processes tasks from the queue.

        Args:
            worker_id: Unique worker identifier
        """
        logger.info(f"{worker_id} started")

        while self._running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                await self._execute_task(task, worker_id)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"{worker_id} cancelled")
                break
            except Exception as e:
                logger.exception(f"{worker_id} error: {e}")

        logger.info(f"{worker_id} stopped")

    async def _execute_task(self, task: Task, worker_id: str) -> None:
        """
        Execute a single task.

        Args:
            task: Task to execute
            worker_id: Worker executing the task
        """
        logger.info(f"{worker_id} executing task {task.id}: {task.name}")

        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await self._notify_callbacks(task.id, "started")

        try:
            # Execute the task function
            if not task.func:
                raise ValueError("Task function is not defined")

            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, task.func, *task.args, **task.kwargs
                )

            # Update task with result
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            task.progress = 100.0

            logger.info(f"Task {task.id} completed successfully")
            await self._notify_callbacks(task.id, "completed")

        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled"
            task.completed_at = datetime.utcnow()
            logger.warning(f"Task {task.id} cancelled")
            await self._notify_callbacks(task.id, "cancelled")
            raise

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            logger.error(f"Task {task.id} failed: {e}")
            await self._notify_callbacks(task.id, "failed")

    async def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            name: Optional task name
            metadata: Optional task metadata
            **kwargs: Keyword arguments for the function

        Returns:
            Task ID
        """
        task = Task(
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            metadata=metadata or {},
        )

        self.tasks[task.id] = task
        await self.queue.put(task)

        logger.info(f"Task {task.id} submitted: {task.name}")
        return task.id

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None
        """
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        return [task for task in self.tasks.values() if task.status == status]

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False

        task.status = TaskStatus.CANCELLED
        task.error = "Cancelled by user"
        task.completed_at = datetime.utcnow()

        await self._notify_callbacks(task_id, "cancelled")
        return True

    def add_task_callback(self, task_id: str, callback: Callable[..., Any]) -> None:
        """
        Add a callback for task status changes.

        Args:
            task_id: Task ID
            callback: Callback function
        """
        if task_id not in self._task_callbacks:
            self._task_callbacks[task_id] = []
        self._task_callbacks[task_id].append(callback)

    async def _notify_callbacks(self, task_id: str, event: str) -> None:
        """
        Notify callbacks about task status change.

        Args:
            task_id: Task ID
            event: Event type
        """
        callbacks = self._task_callbacks.get(task_id, [])
        task = self.tasks.get(task_id)

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task, event)
                else:
                    callback(task, event)
            except Exception as e:
                logger.error(f"Callback error for task {task_id}: {e}")

    def update_task_progress(self, task_id: str, progress: float) -> None:
        """
        Update task progress.

        Args:
            task_id: Task ID
            progress: Progress percentage (0-100)
        """
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.progress = max(0, min(100, progress))


# Global task queue instance
task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get the global task queue instance."""
    global task_queue
    if task_queue is None:
        task_queue = TaskQueue()
    return task_queue


# Task decorator for easy registration
def background_task(
    name: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to mark a function as a background task.

    Args:
        name: Optional task name

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> str:
            queue = get_task_queue()
            task_id = await queue.submit(
                func, *args, name=name or func.__name__, **kwargs
            )
            return task_id

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.submit = wrapper  # type: ignore[attr-defined]  # Alias for clarity
        wrapper.original = func  # type: ignore[attr-defined]  # Keep reference to original

        return wrapper

    return decorator
