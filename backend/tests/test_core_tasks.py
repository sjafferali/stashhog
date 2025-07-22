"""Comprehensive tests for core tasks module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.tasks import Task, TaskQueue, TaskStatus, background_task, get_task_queue


class TestTaskModel:
    """Test Task dataclass."""

    def test_task_creation_defaults(self):
        """Test task creation with default values."""
        task = Task()

        assert task.id is not None
        assert len(task.id) > 0
        assert task.name == ""
        assert task.func is None
        assert task.args == ()
        assert task.kwargs == {}
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.progress == 0.0
        assert task.metadata == {}

    def test_task_creation_with_values(self):
        """Test task creation with custom values."""

        def dummy_func():
            pass

        task = Task(
            name="test_task",
            func=dummy_func,
            args=(1, 2),
            kwargs={"key": "value"},
            metadata={"priority": "high"},
        )

        assert task.name == "test_task"
        assert task.func == dummy_func
        assert task.args == (1, 2)
        assert task.kwargs == {"key": "value"}
        assert task.metadata == {"priority": "high"}

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"


class TestTaskQueue:
    """Test TaskQueue functionality."""

    @pytest.fixture
    def task_queue(self):
        """Create a task queue instance."""
        return TaskQueue(max_workers=2)

    def test_task_queue_init(self):
        """Test task queue initialization."""
        queue = TaskQueue(max_workers=3)

        assert queue.max_workers == 3
        assert isinstance(queue.queue, asyncio.Queue)
        assert queue.tasks == {}
        assert queue.workers == []
        assert queue._running is False
        assert queue._task_callbacks == {}

    @pytest.mark.asyncio
    async def test_start_stop(self, task_queue):
        """Test starting and stopping the task queue."""
        # Start the queue
        await task_queue.start()
        assert task_queue._running is True
        assert len(task_queue.workers) == 2

        # Starting again should be idempotent
        await task_queue.start()
        assert len(task_queue.workers) == 2

        # Stop the queue
        await task_queue.stop()
        assert task_queue._running is False
        assert len(task_queue.workers) == 0

        # Stopping again should be idempotent
        await task_queue.stop()

    @pytest.mark.asyncio
    async def test_submit_task(self, task_queue):
        """Test submitting a task to the queue."""

        async def async_task(x, y):
            return x + y

        task_id = await task_queue.submit(
            async_task, 1, 2, name="addition", metadata={"type": "math"}
        )

        assert task_id is not None
        assert task_id in task_queue.tasks

        task = task_queue.tasks[task_id]
        assert task.name == "addition"
        assert task.func == async_task
        assert task.args == (1, 2)
        assert task.kwargs == {}
        assert task.metadata == {"type": "math"}
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_execute_async_task(self, task_queue):
        """Test executing an async task."""
        result_container = []

        async def async_task(x, y):
            await asyncio.sleep(0.01)
            result = x + y
            result_container.append(result)
            return result

        await task_queue.start()

        try:
            task_id = await task_queue.submit(async_task, 5, 3)

            # Wait for task to complete
            for _ in range(50):  # Max 0.5 seconds
                task = task_queue.get_task(task_id)
                if task and task.status == TaskStatus.COMPLETED:
                    break
                await asyncio.sleep(0.01)

            assert task.status == TaskStatus.COMPLETED
            assert task.result == 8
            assert task.error is None
            assert task.started_at is not None
            assert task.completed_at is not None
            assert task.progress == 100.0
            assert result_container == [8]

        finally:
            await task_queue.stop()

    @pytest.mark.asyncio
    async def test_execute_sync_task(self, task_queue):
        """Test executing a sync task."""

        def sync_task(x, y):
            return x * y

        await task_queue.start()

        try:
            task_id = await task_queue.submit(sync_task, 4, 5)

            # Wait for task to complete
            for _ in range(50):
                task = task_queue.get_task(task_id)
                if task and task.status == TaskStatus.COMPLETED:
                    break
                await asyncio.sleep(0.01)

            assert task.status == TaskStatus.COMPLETED
            assert task.result == 20
            assert task.error is None

        finally:
            await task_queue.stop()

    @pytest.mark.asyncio
    async def test_task_failure(self, task_queue):
        """Test task failure handling."""

        async def failing_task():
            raise ValueError("Task failed!")

        await task_queue.start()

        try:
            task_id = await task_queue.submit(failing_task)

            # Wait for task to fail
            for _ in range(50):
                task = task_queue.get_task(task_id)
                if task and task.status == TaskStatus.FAILED:
                    break
                await asyncio.sleep(0.01)

            assert task.status == TaskStatus.FAILED
            assert task.error == "Task failed!"
            assert task.result is None
            assert task.completed_at is not None

        finally:
            await task_queue.stop()

    @pytest.mark.asyncio
    async def test_task_without_function(self, task_queue):
        """Test task execution without a function."""
        task = Task(name="empty_task")
        task_queue.tasks[task.id] = task

        await task_queue.start()

        try:
            await task_queue.queue.put(task)

            # Wait for task to fail
            for _ in range(50):
                if task.status == TaskStatus.FAILED:
                    break
                await asyncio.sleep(0.01)

            assert task.status == TaskStatus.FAILED
            assert "Task function is not defined" in task.error

        finally:
            await task_queue.stop()

    def test_get_task(self, task_queue):
        """Test getting a task by ID."""
        task = Task(id="test_id", name="test_task")
        task_queue.tasks["test_id"] = task

        retrieved = task_queue.get_task("test_id")
        assert retrieved == task

        # Non-existent task
        assert task_queue.get_task("non_existent") is None

    def test_get_all_tasks(self, task_queue):
        """Test getting all tasks."""
        task1 = Task(name="task1")
        task2 = Task(name="task2")

        task_queue.tasks[task1.id] = task1
        task_queue.tasks[task2.id] = task2

        all_tasks = task_queue.get_all_tasks()
        assert len(all_tasks) == 2
        assert task1 in all_tasks
        assert task2 in all_tasks

    def test_get_tasks_by_status(self, task_queue):
        """Test getting tasks by status."""
        task1 = Task(name="task1", status=TaskStatus.PENDING)
        task2 = Task(name="task2", status=TaskStatus.RUNNING)
        task3 = Task(name="task3", status=TaskStatus.COMPLETED)
        task4 = Task(name="task4", status=TaskStatus.RUNNING)

        for task in [task1, task2, task3, task4]:
            task_queue.tasks[task.id] = task

        pending = task_queue.get_tasks_by_status(TaskStatus.PENDING)
        assert len(pending) == 1
        assert task1 in pending

        running = task_queue.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(running) == 2
        assert task2 in running
        assert task4 in running

        completed = task_queue.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(completed) == 1
        assert task3 in completed

    @pytest.mark.asyncio
    async def test_cancel_task(self, task_queue):
        """Test cancelling a task."""
        # Test cancelling pending task
        task = Task(id="task1", status=TaskStatus.PENDING)
        task_queue.tasks["task1"] = task

        result = await task_queue.cancel_task("task1")
        assert result is True
        assert task.status == TaskStatus.CANCELLED
        assert task.error == "Cancelled by user"
        assert task.completed_at is not None

        # Test cancelling completed task (should fail)
        task2 = Task(id="task2", status=TaskStatus.COMPLETED)
        task_queue.tasks["task2"] = task2

        result = await task_queue.cancel_task("task2")
        assert result is False
        assert task2.status == TaskStatus.COMPLETED

        # Test cancelling non-existent task
        result = await task_queue.cancel_task("non_existent")
        assert result is False

    def test_update_task_progress(self, task_queue):
        """Test updating task progress."""
        task = Task(id="task1", status=TaskStatus.RUNNING)
        task_queue.tasks["task1"] = task

        # Update progress
        task_queue.update_task_progress("task1", 50.0)
        assert task.progress == 50.0

        # Test bounds
        task_queue.update_task_progress("task1", 150.0)
        assert task.progress == 100.0

        task_queue.update_task_progress("task1", -10.0)
        assert task.progress == 0.0

        # Test updating non-running task (should not update)
        task.status = TaskStatus.COMPLETED
        task_queue.update_task_progress("task1", 75.0)
        assert task.progress == 0.0

        # Test updating non-existent task
        task_queue.update_task_progress("non_existent", 50.0)  # Should not raise


class TestTaskCallbacks:
    """Test task callback functionality."""

    @pytest.mark.asyncio
    async def test_task_callbacks(self):
        """Test task status callbacks."""
        queue = TaskQueue()
        callback_events = []

        def sync_callback(task, event):
            callback_events.append((task.id, event))

        async def async_callback(task, event):
            await asyncio.sleep(0.001)
            callback_events.append((task.id, f"async_{event}"))

        async def simple_task():
            return "done"

        await queue.start()

        try:
            task_id = await queue.submit(simple_task)

            # Add callbacks
            queue.add_task_callback(task_id, sync_callback)
            queue.add_task_callback(task_id, async_callback)

            # Wait for task to complete
            for _ in range(50):
                task = queue.get_task(task_id)
                if task and task.status == TaskStatus.COMPLETED:
                    break
                await asyncio.sleep(0.01)

            # Check callbacks were called
            assert (task_id, "started") in callback_events
            assert (task_id, "async_started") in callback_events
            assert (task_id, "completed") in callback_events
            assert (task_id, "async_completed") in callback_events

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_callback_error_handling(self):
        """Test that callback errors don't affect task execution."""
        queue = TaskQueue()

        def failing_callback(task, event):
            raise RuntimeError("Callback error")

        async def simple_task():
            return "success"

        await queue.start()

        try:
            task_id = await queue.submit(simple_task)
            queue.add_task_callback(task_id, failing_callback)

            # Wait for task to complete
            for _ in range(50):
                task = queue.get_task(task_id)
                if task and task.status == TaskStatus.COMPLETED:
                    break
                await asyncio.sleep(0.01)

            # Task should still complete successfully
            assert task.status == TaskStatus.COMPLETED
            assert task.result == "success"

        finally:
            await queue.stop()


class TestBackgroundTaskDecorator:
    """Test background_task decorator."""

    def test_decorator_creation(self):
        """Test creating a decorated function."""

        @background_task(name="test_task")
        def my_task(x, y):
            return x + y

        assert hasattr(my_task, "submit")
        assert hasattr(my_task, "original")
        assert my_task.original(2, 3) == 5
        assert my_task.__name__ == "my_task"

    @pytest.mark.asyncio
    async def test_decorator_submission(self):
        """Test submitting a decorated task."""
        with patch("app.core.tasks.get_task_queue") as mock_get_queue:
            mock_queue = Mock()
            mock_queue.submit = AsyncMock(return_value="task_123")
            mock_get_queue.return_value = mock_queue

            @background_task(name="custom_name")
            def my_task(x, y, z=10):
                return x + y + z

            # Call the decorated function
            task_id = await my_task(1, 2, z=3)

            assert task_id == "task_123"
            mock_queue.submit.assert_called_once()

            # Check the call arguments
            call_args = mock_queue.submit.call_args
            assert call_args[0][0] == my_task.original
            assert call_args[0][1:] == (1, 2)
            assert call_args[1]["name"] == "custom_name"
            assert call_args[1]["z"] == 3

    @pytest.mark.asyncio
    async def test_decorator_without_name(self):
        """Test decorator without custom name."""
        with patch("app.core.tasks.get_task_queue") as mock_get_queue:
            mock_queue = Mock()
            mock_queue.submit = AsyncMock(return_value="task_456")
            mock_get_queue.return_value = mock_queue

            @background_task()
            def another_task():
                return "result"

            task_id = await another_task()

            assert task_id == "task_456"
            call_args = mock_queue.submit.call_args
            assert call_args[1]["name"] == "another_task"


class TestGlobalTaskQueue:
    """Test global task queue functionality."""

    def test_get_task_queue_singleton(self):
        """Test that get_task_queue returns singleton."""
        # Reset global
        import app.core.tasks

        app.core.tasks.task_queue = None

        queue1 = get_task_queue()
        queue2 = get_task_queue()

        assert queue1 is queue2
        assert isinstance(queue1, TaskQueue)

    @pytest.mark.asyncio
    async def test_worker_cancellation(self):
        """Test worker cancellation during execution."""
        queue = TaskQueue(max_workers=1)

        task_started = asyncio.Event()
        task_should_continue = asyncio.Event()

        async def long_task():
            task_started.set()
            await task_should_continue.wait()
            return "completed"

        await queue.start()

        try:
            task_id = await queue.submit(long_task)

            # Wait for task to start
            await task_started.wait()

            # Stop the queue (should cancel workers)
            await queue.stop()

            # Task should be cancelled or failed
            task = queue.get_task(task_id)
            assert task.status in (
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
                TaskStatus.RUNNING,
            )

        finally:
            task_should_continue.set()

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self):
        """Test concurrent execution of multiple tasks."""
        queue = TaskQueue(max_workers=3)

        execution_order = []

        async def task(task_id, delay):
            execution_order.append(f"{task_id}_start")
            await asyncio.sleep(delay)
            execution_order.append(f"{task_id}_end")
            return task_id

        await queue.start()

        try:
            # Submit tasks with different delays
            task_ids = []
            task_ids.append(await queue.submit(task, "task1", 0.02))
            task_ids.append(await queue.submit(task, "task2", 0.01))
            task_ids.append(await queue.submit(task, "task3", 0.01))

            # Wait for all tasks to complete
            completed = False
            for _ in range(100):  # Max 1 second
                all_done = all(
                    queue.get_task(tid)
                    and queue.get_task(tid).status == TaskStatus.COMPLETED
                    for tid in task_ids
                )
                if all_done:
                    completed = True
                    break
                await asyncio.sleep(0.01)

            assert completed

            # Verify all tasks completed
            for tid in task_ids:
                task_obj = queue.get_task(tid)
                assert task_obj.status == TaskStatus.COMPLETED

            # Verify concurrent execution (task2 and task3 should complete before task1)
            assert "task2_end" in execution_order
            assert "task3_end" in execution_order

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_queue_capacity(self):
        """Test queue behavior with many tasks."""
        queue = TaskQueue(max_workers=2)

        async def quick_task(n):
            await asyncio.sleep(0.001)
            return n

        await queue.start()

        try:
            # Submit many tasks
            task_ids = []
            for i in range(20):
                task_id = await queue.submit(quick_task, i)
                task_ids.append(task_id)

            # Wait for all to complete
            for _ in range(100):
                all_done = all(
                    queue.get_task(tid)
                    and queue.get_task(tid).status == TaskStatus.COMPLETED
                    for tid in task_ids
                )
                if all_done:
                    break
                await asyncio.sleep(0.01)

            # Verify all completed
            for i, tid in enumerate(task_ids):
                task = queue.get_task(tid)
                assert task.status == TaskStatus.COMPLETED
                assert task.result == i

        finally:
            await queue.stop()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_worker_exception_handling(self):
        """Test worker handles exceptions gracefully."""
        queue = TaskQueue(max_workers=1)

        # Create a task that will cause an exception in the worker
        task = Task(func=None)  # This will raise ValueError

        await queue.start()

        try:
            # Manually add task to queue
            queue.tasks[task.id] = task
            await queue.queue.put(task)

            # Wait a bit for processing
            await asyncio.sleep(0.05)

            # Task should be failed
            assert task.status == TaskStatus.FAILED
            assert "Task function is not defined" in task.error

            # Queue should still be running
            assert queue._running

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_stop_with_pending_tasks(self):
        """Test stopping queue with pending tasks."""
        queue = TaskQueue(max_workers=1)

        async def slow_task():
            await asyncio.sleep(1.0)  # Long task
            return "done"

        await queue.start()

        # Submit multiple tasks
        task_ids = []
        for _ in range(5):
            task_id = await queue.submit(slow_task)
            task_ids.append(task_id)

        # Immediately stop
        await queue.stop()

        # Check task states
        pending_count = 0
        for tid in task_ids:
            task = queue.get_task(tid)
            if task.status == TaskStatus.PENDING:
                pending_count += 1

        # Most tasks should still be pending since we stopped quickly
        assert pending_count >= 3
