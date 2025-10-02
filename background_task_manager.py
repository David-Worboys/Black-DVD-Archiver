"""
This module contains a class that implements a background task manager.

Copyright (C) 2023  David Worboys (-:alumnus Moyhu Primary School et al.:-)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import dataclasses
import functools
import pprint
import threading
# import traceback # for debug

from typing import Callable, Optional, cast, Any

import QTPYGUI.popups as popups
import QTPYGUI.qtpygui as qtg
import QTPYGUI.sqldb as sqldb
import sys_consts

import uuid

from PySide6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    Signal,
    Slot,
    QMutex,
    QMutexLocker,
)

from QTPYGUI.utils import Singleton

from break_circular import Cancel_Task, Execute_Check_Output, Task_Def

DEBUG = False
QOBJECT_METACLASS = type(QObject)


def Unpack_Result_Tuple(task_def: Task_Def) -> tuple[int, str, int, str]:
    """
    Unpacks the 'result_tuple' from a Task_Def's cargo, which contains
    the outcome of a worker function's execution.

    Args:
        task_def (Task_Def): The task definition instance whose cargo
                             contains the 'result_tuple'.

    Returns:
        tuple[int, str, int, str]: A tuple containing:
            - task_error_no (int): The error code from the task manager's perspective (usually 1 for success).
            - task_message (str): A message from the task manager's perspective.
            - worker_error_no (int): The error code returned by the worker function (0 for error, 1 for success).
            - worker_message (str): A message/result (e.g., output file path) from the worker function.

    """
    assert isinstance(task_def, Task_Def), (
        f"{task_def=}. Must be an instance of Task_Def"
    )

    if "result_tuple" not in task_def.cargo:
        message = f"Error processing task {task_def.task_id=}: 'result_tuple' missing from cargo."
        if DEBUG:
            print(f"DBG AM unpack_result_tuple: {message}")

        raise RuntimeError(message)

    result = task_def.cargo["result_tuple"]

    assert isinstance(result, tuple) and len(result) == 4, (
        f"{task_def.cargo['result_tuple']=}. Must be a tuple of 4 elements "
        f"for task_id={task_def.task_id}"
    )

    task_error_no, task_message, worker_error_no, worker_message = result

    if DEBUG:
        print(
            f"DBG unpack_result_tuple: Task {task_def.task_id=} result unpacked: "
            f"error_no={task_error_no}, msg='{task_message}', "
            f"worker_error_no={worker_error_no}, worker_msg='{worker_message}'"
        )

    return task_error_no, task_message, worker_error_no, worker_message


@dataclasses.dataclass
class Task_Data:
    """Encapsulates a function call and its associated data, including custom callbacks."""

    # The actual function to be executed by the worker
    worker_function: Callable[..., Any]

    # Arguments for the worker_function
    args: tuple[Any, ...] = dataclasses.field(default_factory=tuple)
    kwargs: dict[str, Any] = dataclasses.field(default_factory=dict)

    task_id: str = ""
    task_def: Optional[Task_Def] = None

    # Callbacks for task-specific handling (will be called on the main thread) ---
    on_started_callback: Optional[Callable[[str], None]] = None
    on_progress_callback: Optional[Callable[[str, float, str], None]] = None
    on_finished_callback: Optional[Callable[[str, Any], None]] = None
    on_error_callback: Optional[Callable[[str, str], None]] = None
    on_aborted_callback: Optional[Callable[[str, str], None]] = None

    _short_task_id: bool = False

    # This callback is for the *worker_function itself* to report progress back to the WorkerRunnable
    # (which then funnels it through WorkerSignals to ThreadPoolExecutor's main-thread slot)
    internal_progress_callback: Optional[Callable[[float, str], None]] = None

    def __post_init__(self):
        """
        Post-initialization for validation.
        """
        assert isinstance(self.worker_function, Callable), (
            f"'{self.worker_function=}' must be a callable."
        )
        assert isinstance(self.args, tuple), f"'{self.args=}' must be a tuple."
        assert isinstance(self.kwargs, dict), f"'{self.kwargs=}' must be a dict."
        assert isinstance(self.task_id, str), f"'{self.task_id=}' must be a string."
        assert isinstance(self.task_def, Task_Def) or self.task_def is None, (
            f"'{self.task_def=}' must be a Task_Def object or None."
        )
        assert (
            isinstance(self.on_started_callback, Callable)
            or self.on_started_callback is None
        ), f"'{self.on_started_callback=}' must be a callable or None."
        assert (
            isinstance(self.on_progress_callback, Callable)
            or self.on_progress_callback is None
        ), f"'{self.on_progress_callback=}' must be a callable or None."
        assert (
            isinstance(self.on_finished_callback, Callable)
            or self.on_finished_callback is None
        ), f"'{self.on_finished_callback=}' must be a callable or None."
        assert (
            isinstance(self.on_error_callback, Callable)
            or self.on_error_callback is None
        ), f"'{self.on_error_callback=}' must be a callable or None."
        assert (
            isinstance(self.on_aborted_callback, Callable)
            or self.on_aborted_callback is None
        ), f"'{self.on_aborted_callback=}' must be a callable. or None."

        if self.task_id == "":
            self._short_task_id = True
            self.task_id = str(uuid.uuid4())

    def __repr__(self) -> str:
        """Returns a string representation of the Task_Data object.

        Returns(str): A  string representation of the Task_Data object.
        """
        if self._short_task_id:
            task_id = self.task_id[:8] if self.task_id else "N/A"
        else:
            task_id = self.task_id

        return f"Task(ID: {task_id}..., Func: {self.worker_function.__name__})"


class Worker_Signals(QObject):
    """
    Defines the signals available from a running worker thread.
    """

    started = Signal(str)  # task_id
    progress = Signal(str, float, str)  # task_id, percentage, message
    finished = Signal(str, object)  # task_id, result (or None on error)
    error = Signal(str, str)  # task_id, error_message
    aborted = Signal(str, str)  # task_id, reason (if cancellation is implemented)


class Worker_Runnable(QRunnable):
    """
    A QRunnable that executes a Task_Data object and emits signals via Worker_Signals.
    """

    def __init__(self, task: Task_Data, signals: Worker_Signals):
        """
        Initializes the Worker_Runnable class.

        Args:
            task (Task_Data): The task to be executed.
            signals (Worker_Signals): The signals instance to emit signals.
        """
        assert isinstance(task, Task_Data), f"{task=}. Must be a Task_Data object"
        assert isinstance(signals, Worker_Signals), (
            f"{signals=}. Must be a Worker_Signals object"
        )

        super().__init__()

        self._task = task
        self._signals = signals
        self._is_cancelled = False

    @Slot()
    def run(self) -> None:
        """
        Executes the task and emits signals via Worker_Signals.
        """

        task_id = self._task.task_id

        if DEBUG:
            print(f"--> DBG Worker_Runnable: ENTERING run() for task {task_id[:8]}...")

        try:
            self._signals.started.emit(task_id)

            if DEBUG:
                print(
                    f"    DBG Worker_Runnable: Emitting started signal for task {task_id[:8]}..."
                )

            worker_facing_progress_callback = None

            if (
                self._task.on_progress_callback is not None
            ):  # Check if a GUI progress callback was requested
                # This lambda is created here, in the WorkerRunnable,
                # so it can access self._signals and task_id.
                worker_facing_progress_callback = (
                    lambda parameter, message: self._signals.progress.emit(
                        task_id, parameter, message
                    )
                )

            task_kwargs = self._task.kwargs.copy()

            if worker_facing_progress_callback:
                task_kwargs["progress_callback"] = (
                    worker_facing_progress_callback  # Pass it to the worker_function as 'progress_callback' keyword
                )

            if DEBUG:
                print(
                    f"    DBG Worker_Runnable: Calling worker_function '{self._task.worker_function.__name__}'"
                    f" for task {task_id[:8]}..."
                )

            # Task_Dispatcher is wrapping things a bit different, so remove 'args' and 'kwargs' from task_kwargs
            if "args" in task_kwargs:
                del task_kwargs["args"]

            if "kwargs" in task_kwargs:
                task_kwargs = task_kwargs["kwargs"]
            # try:
            result = self._task.worker_function(*self._task.args, **task_kwargs)
            # except Exception as e:
            #    raise RuntimeError(
            #        f"DBG_ERROR: {e} \n {self._task.worker_function}  \n {task_kwargs} \n {self._task}"
            #    )

            if self._is_cancelled:
                # If the task was cancelled and the result is a tuple of (-1, "message") or (-2, "message") then
                # we can refine the cancellation message.
                mid_execution_cancellation = (
                    isinstance(result, tuple)
                    and len(result) >= 1
                    and isinstance(result[0], int)
                    and result[0] in [-1, -2]
                )

                if mid_execution_cancellation:
                    message = f"Task {task_id[:8]} cancelled mid execution by user."

                    if DEBUG:
                        print(f"    DBG Worker_Runnable: {message}")
                else:
                    message = f"Task {task_id[:8]} cancelled after execution by user."

                    if DEBUG:
                        print(f"    DBG Worker_Runnable: Task {message}")

                if self._signals:
                    self._signals.aborted.emit(task_id, message)

                return None

            if DEBUG:
                print(
                    f"    DBG Worker_Runnable: Emitting finished signal for task {task_id[:8]}..."
                )

            if self._signals:
                self._signals.finished.emit(task_id, result)

        except Exception as e:
            if DEBUG:
                print(f"!!! DBG WorkerRunnable: ERROR in task {task_id[:8]} !!!")
                # traceback.print_exc()

            if self._signals:
                self._signals.error.emit(task_id, str(e))
        finally:
            if DEBUG:
                print(
                    f"--> DBG WorkerRunnable: EXITING run() for task {task_id[:8]}..."
                )

    def cancel(self):
        """
        Marks the task for cancellation. The task's function must check this flag.
        """
        self._is_cancelled = True


class Thread_Pool_Executor(QObject):
    """
    This class manages the QThreadPool and provides the public API for submitting tasks.
    It runs on the main (GUI) thread and handles signal connections.
    """

    task_started = Signal(str)
    task_progress = Signal(str, float, str)
    task_finished = Signal(str, object)
    task_error = Signal(str, str)
    task_aborted = Signal(str, str)

    def __init__(self, max_threads: int = 0, parent: Optional[QObject] = None):
        """
        Initializes the Thread_Pool_Executor class.

        Args:
            max_threads (int, optional): The maximum number of threads to use. Defaults to 0.
            parent (Optional[QObject], optional): The parent object. Defaults to None.
        """

        assert isinstance(max_threads, int) and max_threads >= 0, (
            f"{max_threads =} must be an int >= 0"
        )
        assert isinstance(parent, QObject) or parent is None, (
            f"{parent =} must be a QObject Or None"
        )

        super().__init__(parent)

        thread_expiry_timeout = 5000

        self._pool = (
            QThreadPool.globalInstance() if max_threads == 0 else QThreadPool(self)
        )

        if max_threads > 0:
            self._pool.setMaxThreadCount(max_threads)

        self._pool.setExpiryTimeout(thread_expiry_timeout)

        self._shared_worker_signals = Worker_Signals()
        self._active_tasks_data: dict[str, Task_Data] = {}
        self._active_runnables: dict[str, Worker_Runnable] = {}
        self._task_data_mutex: QMutex = QMutex()

        # Connections - These ensure the _task_*_handler methods are called
        # on the main thread, allowing safe execution of user-provided callbacks.
        self._shared_worker_signals.started.connect(self._task_started_handler)
        self._shared_worker_signals.progress.connect(self._task_progress_handler)
        self._shared_worker_signals.finished.connect(self._task_finished_handler)
        self._shared_worker_signals.error.connect(self._task_error_handler)
        self._shared_worker_signals.aborted.connect(self._task_aborted_handler)

        self._active_task_cancel_callbacks = {}

    @Slot(str)
    def _task_started_handler(self, task_id: str) -> None:
        """
        Handles a task start by emitting a task_started signal.

        Args:
            task_id (str): The ID of the task that has started.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )

        if DEBUG:
            print(f"DBG: TPE TS Max threads: {self._pool.maxThreadCount()}")

        # The executor's own signal is emitted, but Task_QManager won't be listening to it directly.
        self.task_started.emit(task_id)  # Remains as internal plumbing.

        with QMutexLocker(self._task_data_mutex):
            task_data = self._active_tasks_data.get(task_id)

        if task_data and task_data.on_started_callback:
            task_data.on_started_callback(task_id)

        return None

    @Slot(str, float, str)
    def _task_progress_handler(
        self, task_id: str, percentage: float, message: str
    ) -> None:
        """
        Handles a task progress update by emitting a task_progress signal.

        Args:
            task_id (str): The ID of the task that is in progress.
            percentage (float): The progress percentage.
            message (str): The progress message.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(percentage, float), f"{percentage=}. Must be a float"
        assert isinstance(message, str), f"{message=}. Must be a string"

        self.task_progress.emit(
            task_id, percentage, message
        )  # Remains as internal plumbing.

        with QMutexLocker(self._task_data_mutex):
            task_data = self._active_tasks_data.get(task_id)

        if task_data and task_data.on_progress_callback:
            task_data.on_progress_callback(task_id, percentage, message)

        return None

    @Slot(str, object)
    def _task_finished_handler(self, task_id: str, result: Any) -> None:
        """
        Handles a task completion by removing it from the active tasks list and emits a task_finished signal.

        Args:
            task_id (str): The ID of the task that completed.
            result (Any): The result of the task.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )

        if DEBUG:
            print(f"DBG: TPE TF {task_id=} {result=}")

        with QMutexLocker(self._task_data_mutex):
            task_data = self._active_tasks_data.pop(task_id, None)
            self._active_runnables.pop(task_id, None)

        self.task_finished.emit(task_id, result)  # Remains as internal plumbing.

        if task_data and task_data.on_finished_callback:
            task_data.on_finished_callback(task_id, result)

        if task_id in self._active_task_cancel_callbacks:
            self._active_task_cancel_callbacks.pop(task_id)

        return None

    @Slot(str, str)
    def _task_error_handler(self, task_id: str, error_message: str) -> None:
        """
        Handles a task error by removing it from the active tasks list and emits a task_error signal.

        Args:
            task_id (str): The ID of the task that encountered an error.
            error_message (str): The error message associated with the task.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(error_message, str), f"{error_message=}. Must be a string"

        with QMutexLocker(self._task_data_mutex):
            task_data = self._active_tasks_data.pop(task_id, None)
            self._active_runnables.pop(task_id, None)

        self.task_error.emit(task_id, error_message)  # Remains as internal plumbing.

        if task_data and task_data.on_error_callback:
            task_data.on_error_callback(task_id, error_message)

        if task_id in self._active_task_cancel_callbacks:
            self._active_task_cancel_callbacks.pop(task_id)

        return None

    @Slot(str, str)
    def _task_aborted_handler(self, task_id: str, reason: str) -> None:
        """
        Removes a task from the active tasks list and emits the task_aborted signal.

        Args:
            task_id (str): The ID of the task that was aborted.
            reason (str): The reason for the task being aborted.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(reason, str), f"{reason=}. Must be a string"

        with QMutexLocker(self._task_data_mutex):
            task_data = self._active_tasks_data.pop(task_id, None)
            self._active_runnables.pop(task_id, None)

        self.task_aborted.emit(task_id, reason)  # Remains as internal plumbing.

        if task_data and task_data.on_aborted_callback:
            task_data.on_aborted_callback(task_id, reason)

        if task_id in self._active_task_cancel_callbacks:
            self._active_task_cancel_callbacks.pop(task_id)

        return None

    def submit_task(
        self,
        worker_function: Callable,
        *args: Any,
        started_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        finished_callback: Optional[Callable[[str, Any], None]] = None,
        error_callback: Optional[Callable[[str, str], None]] = None,
        aborted_callback: Optional[Callable[[str, str], None]] = None,
        task_id: str = "",
        task_def: Optional[Task_Def] = None,
        **kwargs: Any,
    ) -> str:
        """
        Submits a function to be executed in a separate worker thread.

        Args:
            worker_function (Callable): The function to run in the background thread.
            *args (Any): Positional arguments to pass to the `worker_function`.
            started_callback (Optional[Callable[[str], None]], optional): A callback function (executed on the main
             thread) that's invoked when the task officially begins. Receives the task ID. Defaults to None.
            progress_callback (Optional[Callable[[str, float, str], None]], optional): A callback function (executed on
             the main thread) for progress updates. Receives the task ID, percentage (0.0-100.0), and an optional message.
             Defaults to None.
            finished_callback (Optional[Callable[[str, Any], None]], optional): A callback function (executed on the
             main thread) that's called upon successful task completion. Receives the task ID and the result of `
             worker_function`. Defaults to None.
            error_callback (Optional[Callable[[str, str], None]], optional): A callback function (executed on the main
             thread) invoked if the task encounters an error. Receives the task ID and an error message. Defaults to None.
            aborted_callback (Optional[Callable[[str, str], None]], optional): A callback function (executed on the main
             thread) called if the task is explicitly aborted/cancelled. Receives the task ID and a reason string. Defaults to None.
            task_id (str, optional): A unique identifier for the task. If not provided, a random UUID will be generated.
            task_def (Optional[Task_Def], optional): A Task_Def object containing information about the task.
             Defaults to None.
            **kwargs (Any): Keyword arguments to pass to the `worker_function`.

        Returns:
            str: The unique identifier (task ID) for the submitted task.
        """
        assert isinstance(worker_function, Callable), (
            f"{worker_function=}. Must be a Callable."
        )
        assert isinstance(started_callback, Callable) or started_callback is None, (
            f"{started_callback=}. Must be a Callable or None."
        )
        assert isinstance(progress_callback, Callable) or progress_callback is None, (
            f"{progress_callback=}. Must be a Callable or None."
        )
        assert isinstance(finished_callback, Callable) or finished_callback is None, (
            f"{finished_callback=}. Must be a Callable or None."
        )
        assert isinstance(error_callback, Callable) or error_callback is None, (
            f"{error_callback=}. Must be a Callable or None."
        )
        assert isinstance(aborted_callback, Callable) or aborted_callback is None, (
            f"{aborted_callback=}. Must be a Callable or None."
        )
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string."
        )
        assert isinstance(task_def, Task_Def) or task_def is None, (
            f"{task_def=}. Must be a Task_Def or None."
        )
        assert isinstance(kwargs, dict), f"{kwargs=}. Must be a dict."

        modified_kwargs = kwargs.copy()
        add_cancellation_callback = "cancellation_callback" not in kwargs
        cancel_task: Cancel_Task | None = None

        if worker_function is Execute_Check_Output:
            if add_cancellation_callback:
                cancel_task = Cancel_Task()
                modified_kwargs["cancellation_callback"] = (
                    cancel_task.is_cancellation_requested
                )
                if DEBUG:
                    print(
                        f"DBG: Injected task-specific cancellation for {worker_function.__name__} (Task ID: {task_id})."
                    )
            else:
                if DEBUG:
                    print(
                        f"DBG: Task-specific cancellation already provided for {worker_function.__name__}"
                        f" (Task ID: {task_id})."
                    )
        task = Task_Data(
            worker_function=worker_function,
            args=args,
            on_started_callback=started_callback,
            on_progress_callback=progress_callback,
            on_finished_callback=finished_callback,
            on_error_callback=error_callback,
            on_aborted_callback=aborted_callback,
            task_id=task_id,
            task_def=task_def,
            kwargs=modified_kwargs,
        )

        if cancel_task and add_cancellation_callback:
            self._active_task_cancel_callbacks[task.task_id] = cancel_task

        runnable = Worker_Runnable(task, self._shared_worker_signals)

        with QMutexLocker(self._task_data_mutex):
            self._active_tasks_data[task.task_id] = task
            self._active_runnables[task.task_id] = runnable

        self._pool.start(runnable)

        return task.task_id

    def cancel_tasks_by_prefix(self, prefix: str) -> bool:
        """
        Cancels tasks with the given prefix.

        Args:
            prefix (str): The prefix of the tasks to cancel.
        """
        assert isinstance(prefix, str) and prefix.strip() != "", (
            f"{prefix=}. Must be a non-empty string"
        )

        tasks_to_cancel_ids = []

        with QMutexLocker(self._task_data_mutex):
            for task_id, task_data in self._active_tasks_data.items():
                if task_data.task_def and hasattr(task_data.task_def, "task_prefix"):
                    if task_data.task_def.task_prefix.startswith(prefix):
                        tasks_to_cancel_ids.append(task_id)

        cancelled = True

        for task_id in tasks_to_cancel_ids:
            cancelled = self.cancel_task(task_id)

            if not cancelled:  # The Task was not cancelled but continue anyway
                cancelled = False

        return cancelled

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancels a task by its task ID.

        Args:
            task_id (str): The unique identifier (task ID) of the task to cancel.

        Returns:
            bool: True if the task was successfully cancelled, False otherwise.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )

        if task_id in self._active_task_cancel_callbacks:
            self._active_task_cancel_callbacks[task_id].request_cancellation()

        with QMutexLocker(self._task_data_mutex):
            runnable = self._active_runnables.get(task_id)

            if runnable:
                runnable.cancel()

                return True

        return False

    def active_tasks(self) -> dict[str, Task_Data]:
        """
        Returns a dictionary of active tasks.

        Returns: dict[str, Task_Data]: A dictionary of active tasks.
        """

        with QMutexLocker(self._task_data_mutex):
            return self._active_tasks_data.copy()

    def wait_for_finished(self) -> None:
        """
        Wait for all tasks to finish.
        """

        self._pool.waitForDone()

        return None


# Define a new metaclass that inherits from both the Singleton and QObject's metaclass.
class QSingleton(Singleton, QOBJECT_METACLASS):
    """
    A combined metaclass that provides both Singleton behavior and
    Qt's Meta-Object System capabilities.
    """

    pass


class Task_QManager(QObject, metaclass=QSingleton):
    """
    A singleton manager for submitting background tasks using QThreadPool.
    All task-related events are handled via custom callbacks passed during submission.
    No global signals are emitted from this manager.
    """

    def __init__(self, parent: Optional[QObject] = None):
        """
        Initializes the Task_QManager class.

        Args:
            parent (Optional[QObject], optional): The parent object. Defaults to None.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__(parent)

        self._thread_pool_executor = Thread_Pool_Executor(parent=self)

        self._initialized = True

    def submit_task(
        self,
        worker_function: Callable,
        *args: Any,
        started_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        finished_callback: Optional[Callable[[str, Any], None]] = None,
        error_callback: Optional[Callable[[str, str], None]] = None,
        aborted_callback: Optional[Callable[[str, str], None]] = None,
        task_id: str = "",
        task_def: Optional[Task_Def] = None,
        **kwargs: Any,
    ) -> str:
        """
        Submits a task for thread pool execution

        Args:
            worker_function (Callable): The function to be executed as a task.
            started_callback (Optional[Callable[[str], None]], optional): A callback function (executed on the main
             thread) called when the task starts. Receives the task ID. Defaults to None.
            progress_callback (Optional[Callable[[str, float, str], None]], optional): A callback function (executed on
             the main thread) for progress updates. Receives the task ID, percentage (0.0-100.0), and an optional message.
             Defaults to None.
            finished_callback (Optional[Callable[[str, Any], None]], optional): A callback function (executed on the
             main thread) that's called upon successful task completion. Receives the task ID and the result of `
             worker_function`. Defaults to None.
            error_callback (Optional[Callable[[str, str], None]], optional): A callback function (executed on the main
             thread) invoked if the task encounters an error. Receives the task ID and an error message. Defaults to None.
            aborted_callback (Optional[Callable[[str, str], None]], optional): A callback function (executed on the main
             thread) invoked if the task is aborted (e.g., by the user). Receives the task ID and an optional message.
             Defaults to None.
            task_id (str, optional): A unique identifier for the task. If not provided, a random UUID will be generated.
            task_def (Optional[Task_Def], optional): An instance of the Task_Def class containing task details.
            **kwargs (Any): Keyword arguments to pass to the `worker_function`.

        Returns:
            str: The task ID.
        """
        return self._thread_pool_executor.submit_task(
            worker_function=worker_function,
            *args,
            started_callback=started_callback,
            progress_callback=progress_callback,
            finished_callback=finished_callback,
            error_callback=error_callback,
            aborted_callback=aborted_callback,
            task_id=task_id,
            task_def=task_def,
            **kwargs,
        )

    def cancel_task_by_prefix(self, prefix: str) -> None:
        """
        Cancel tasks with the given prefix.

        Args:
            prefix (str): The prefix of the tasks to cancel.
        """
        assert isinstance(prefix, str) and prefix.strip() != "", (
            f"{prefix=}. Must be a non-empty string"
        )

        self._thread_pool_executor.cancel_tasks_by_prefix(prefix)

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task by its ID.

        Args:
            task_id (str): The ID of the task to cancel.

        Returns:
            bool: True if the task was successfully canceled, False otherwise.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )

        return self._thread_pool_executor.cancel_task(task_id)

    def active_tasks(self) -> dict[str, Task_Data]:
        """
        Get a list of currently active tasks.

        Returns:
            list[Task_Data]: A list of active tasks.
        """

        return self._thread_pool_executor.active_tasks()

    def wait_for_finished(self) -> None:
        """
        Wait for all tasks to finish.
        """

        self._thread_pool_executor.wait_for_finished()

        return None


def decorator_singleton(cls):
    """
    K, for some very odd reason GUI framework Singleton breaks only on Task_Dispatch, so here is a class decorator to
    make a class into a Singleton by wrapping the class's constructor to ensure only one instance is created.
    """
    instances = {}

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@decorator_singleton
@dataclasses.dataclass()
class Task_Dispatcher:
    """
    A high level class for handling task submission and execution used to simplify mult-thread handling of tasks.

    Note: This is a asingleton class so only one instance is ever created.
    """

    # Dictionary where keys are composite strings: "task_id|callback_type|task_dispatch_name"
    _dispatch_methods: dict[str, dict] = dataclasses.field(default_factory=dict)
    _background_task_qmanager = Task_QManager()
    _stack_lock = threading.Lock()
    _task_stack: dict[str, "Task_Def"] = dataclasses.field(default_factory=dict)
    _aborted_stack: dict[str, "Task_Def"] = dataclasses.field(default_factory=dict)
    _error_stack: dict[str, "Task_Def"] = dataclasses.field(default_factory=dict)
    _completed_stack: dict[str, "Task_Def"] = dataclasses.field(default_factory=dict)
    _submitted_task: Task_Def = None

    def __post_init__(self):
        pass

    def submit_task(
        self,
        task_def: Task_Def,
        task_dispatch_methods: list[dict] = None,
    ) -> None:
        """
        Submits a task for thread pool execution and registers multiple custom dispatch methods for its events.

        This method allows a developer to define how the system should react to various
        lifecycle events of a submitted task (e.g., when it starts, progresses, finishes, errors, or aborts).
        It can register multiple custom actions for different or even the same event type
        for the given task in a single call.

        Args:
            task_def (Task_Def): An instance of `Task_Def` containing comprehensive details
                about the task to be executed, including its unique `task_id`, the worker function,
                arguments, and optional default callbacks.

            task_dispatch_methods (list[dict], optional): A list of dictionaries, where each
                dictionary defines a single custom dispatch method to be executed when a
                specific task lifecycle event occurs. This list is optional; if empty,
                the task will still run, but no custom dispatches will be registered via
                this mechanism for it.

                Each dictionary in the list *must* contain the following keys:
                -   **"task_dispatch_name"** (`str`): A unique identifier for this specific
                    dispatch method within the context of its `task_id` and `callback` type.
                    For example, "LoggerForStart", "UIUpdaterForProgress". This name is
                    also used to determine the execution order of multiple methods
                    registered for the same task and callback type (they will be sorted
                    alphabetically by this name). Must be a non-empty string.
                -   **"operation"** (`str`): A descriptive name for the operation this
                    dispatch method performs (e.g., "Log", "UpdateUI", "SendEmail", "NotifyUser").
                    This is primarily for documentation and debugging. Must be a non-empty string.
                -   **"method"** (`Callable`): The callable (function or method) to be
                    executed when the specified `callback` event occurs. This callable
                    will receive `task_id`, `task_def`, and event-specific arguments
                    (like `percentage`, `message`, `result_tuple`) as keyword arguments,
                    in addition to any `kwargs` provided in this dictionary.
                    `functools.partial` can be used here to pre-bind arguments to the method.
                -   **"callback"** (`str`): Specifies which task lifecycle event this
                    dispatch method should respond to. Valid values are:
                    -   "start": When the task execution begins.
                    -   "progress": When the task reports progress.
                    -   "finish": When the task completes successfully.
                    -   "error": When the task encounters an unhandled exception.
                    -   "abort": When the task is explicitly aborted.
                    Must be one of these exact string values.
                -   **"kwargs"** (`dict`): A dictionary of additional keyword arguments
                    to be passed to the "method" callable when it's invoked. These will
                    be merged with the dynamically provided arguments (`task_id`, `task_def`,
                    and event-specific args).

        Notes:
            -   All modifications to internal state (`_task_stack`, `_dispatch_methods`) are
                protected by `self._stack_lock` to ensure thread safety.
            -   The actual execution of the worker function is delegated to `_background_task_qmanager`.
            -   If multiple dispatch methods are registered for the same task_id and callback type,
                their execution order is determined by the alphabetical sorting of their
                "task_dispatch_name" values.

        Returns:
            None
        """
        assert isinstance(task_def, Task_Def), f"{task_def=}. Must be Task_Def"
        assert task_dispatch_methods is None or isinstance(
            task_dispatch_methods, list
        ), f"{task_dispatch_methods=}. Must be a list of dicts Or None"

        with self._stack_lock:
            if task_def.started_callback is None:
                task_def.started_callback = self._started_callback
            if task_def.progress_callback is None:
                task_def.progress_callback = self._progress_callback
            if task_def.finished_callback is None:
                task_def.finished_callback = self._finished_callback
            if task_def.error_callback is None:
                task_def.error_callback = self._error_callback
            if task_def.aborted_callback is None:
                task_def.aborted_callback = self._aborted_callback

            self._task_stack[task_def.task_id] = task_def

            if task_dispatch_methods is not None:
                for dispatch_config in task_dispatch_methods:
                    assert isinstance(dispatch_config, dict), (
                        f"Each item in task_dispatch_methods must be a dict: {dispatch_config=}"
                    )

                    # Validate the structure of each individual dispatch_config
                    required_keys = [
                        "task_dispatch_name",
                        "operation",
                        "method",
                        "callback",
                        "kwargs",
                    ]
                    for key in required_keys:
                        assert key in dispatch_config, (
                            f"{dispatch_config=}. Must contain '{key}' key"
                        )

                    assert (
                        isinstance(dispatch_config["task_dispatch_name"], str)
                        and dispatch_config["task_dispatch_name"].strip() != ""
                    ), (
                        f"{dispatch_config['task_dispatch_name']=}. Must be non-empty string"
                    )
                    assert (
                        isinstance(dispatch_config["operation"], str)
                        and dispatch_config["operation"].strip() != ""
                    ), f"{dispatch_config['operation']=}. Must be non-empty string"
                    assert isinstance(dispatch_config["method"], Callable), (
                        f"{dispatch_config['method']=}. Must be Callable"
                    )
                    assert (
                        isinstance(dispatch_config["callback"], str)
                        and dispatch_config["callback"].strip() != ""
                    ), f"{dispatch_config['callback']=}. Must be non-empty string"
                    assert dispatch_config["callback"] in [
                        "start",
                        "progress",
                        "finish",
                        "error",
                        "abort",
                    ], (
                        f"{dispatch_config['callback']=}. Must be 'start', 'progress', 'finish', 'error' or 'abort'"
                    )
                    assert isinstance(dispatch_config["kwargs"], dict), (
                        f"{dispatch_config['kwargs']=}. Must be dict"
                    )

                    # Construct the unique composite key for this dispatch method
                    task_dispatch_key = (
                        f"{task_def.task_id}|"
                        f"{dispatch_config['callback']}|"
                        f"{dispatch_config['task_dispatch_name']}"
                    )

                    assert task_dispatch_key not in self._dispatch_methods, (
                        f"Duplicate dispatch method : '{dispatch_config['task_dispatch_name']}' "
                        f"for task '{task_def.task_id}' and callback '{dispatch_config['callback']}'."
                    )

                    # Store a copy to prevent external modification
                    self._dispatch_methods[task_dispatch_key] = dispatch_config.copy()
        self._submitted_task = task_def

        self._background_task_qmanager.submit_task(
            worker_function=task_def.worker_function,
            args=task_def.args,
            started_callback=task_def.started_callback,
            progress_callback=task_def.progress_callback,
            finished_callback=task_def.finished_callback,
            error_callback=task_def.error_callback,
            aborted_callback=task_def.aborted_callback,
            task_id=task_def.task_id,
            task_def=task_def,
            kwargs=task_def.kwargs,
        )

    def _execute_dispatch_method(self, method: Callable, dynamic_kwargs: dict) -> Any:
        """
        Executes a callable method with a combination of its pre-defined keyword
        arguments (if it's a functools.partial object) and dynamically provided kwargs.

        Args:
            method (Callable): The callable method to execute.
            dynamic_kwargs (dict): The dynamic keyword arguments to be passed to the method.

        Returns:
            Any: The return value of the executed method.
        """
        assert isinstance(method, Callable), f"{method=}. Must be Callable"
        assert isinstance(dynamic_kwargs, dict), f"{dynamic_kwargs=}. Must be dict"

        final_kwargs = {**dynamic_kwargs}
        callable_to_execute = method

        if isinstance(method, functools.partial):
            final_kwargs = {**method.keywords, **final_kwargs}
            callable_to_execute = method.func

        try:
            return callable_to_execute(**final_kwargs)

        except TypeError as e:
            text = (
                f"DBG_ERROR: TypeError when executing dispatch method '{callable_to_execute.__name__}' with kwargs:"
                f" {final_kwargs}. Original error: {e}"
            )
            if DEBUG:
                pprint.pprint(text)

            raise RuntimeError(text) from e
        except Exception as e:
            text = (
                f"DBG_ERROR: An unexpected error occurred executing dispatch method '{callable_to_execute.__name__}'"
                f" with kwargs: {final_kwargs}. Original error: {e}"
            )

            if DEBUG:
                print(text)

            raise RuntimeError(text)

    def _process_callbacks_for_event(
        self, task_id: str, callback_type: str, event_args
    ) -> None:
        """
        Processes dispatch methods for a given event type.

        Args:
            task_id (str): The ID of the task.
            callback_type (str): The type of callback (start, progress, finish, error, abort).
            event_args (tuple): The arguments associated with the event.
        """
        assert isinstance(task_id, str), f"{task_id=}. Must be str"
        assert isinstance(callback_type, str) and callback_type in [
            "start",
            "progress",
            "finish",
            "error",
            "abort",
        ], (
            f"{callback_type=}. Must be 'start', 'progress', 'finish', 'error' or 'abort'"
        )

        task_def = None

        with self._stack_lock:
            task_def = self._get_task_def_from_stacks(task_id)

        if not task_def:
            if DEBUG:
                print(
                    f"DBG_WARN: {callback_type} callback for unknown/missing task_id: {task_id}. No task_def found."
                )

            return None

        if callback_type == "progress" and len(event_args) == 2:
            task_def.cargo["percentage"] = event_args[0]
            task_def.cargo["message"] = event_args[1]

        elif callback_type == "finish" and (
            len(event_args) == 2 or len(event_args) == 4
        ):
            task_def.cargo["result_tuple"] = event_args

        elif callback_type in ["error", "abort"] and len(event_args) == 2:
            task_def.cargo["message"] = event_args[1]

        relevant_dispatch_configs = []
        keys_to_clear_for_task = []  # Only for terminal events

        with self._stack_lock:  # Acquire lock to read/modify _dispatch_methods
            dispatch_prefix = f"{task_id}|{callback_type}|"

            for dispatch_key, config_data in self._dispatch_methods.items():
                if dispatch_key.startswith(dispatch_prefix):
                    relevant_dispatch_configs.append(config_data)

                # If it's a terminal event, we want to clear ALL dispatch methods for this task_id
                if callback_type in [
                    "finish",
                    "error",
                    "abort",
                ] and dispatch_key.startswith(f"{task_id}|"):
                    keys_to_clear_for_task.append(dispatch_key)

            relevant_dispatch_configs.sort(
                key=lambda x: x.get("task_dispatch_name", "")
            )

            # Clean up dispatch methods while lock is held for terminal events
            if callback_type in ["finish", "error", "abort"]:
                for key in keys_to_clear_for_task:
                    if key in self._dispatch_methods:
                        del self._dispatch_methods[key]

                if DEBUG:
                    print(
                        f"DBG: Cleared dispatch methods for task_id {task_id} due to '{callback_type}' event."
                    )

        for config in relevant_dispatch_configs:
            callback_method = config["method"]
            callback_args_from_config = config.get("kwargs", {})

            try:
                if DEBUG:
                    print(
                        f"DBG: Executing '{callback_type}' dispatch method \
                         ('{config.get('task_dispatch_name', 'N/A')}') for {task_id}"
                    )

                self._execute_dispatch_method(
                    callback_method, callback_args_from_config
                )

            except Exception as e:
                if DEBUG:
                    print(
                        f"DBG_ERROR: Custom '{callback_type}' dispatch method \
                        ('{config.get('task_dispatch_name', 'N/A')}') for {task_id} failed: {e}"
                    )
        return None

    def _started_callback(self, task_id: str) -> None:
        """
        Handles the 'started' event for a task.

        Args:
            task_id (str): The ID of the task.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )

        if DEBUG:
            print(f"DBG TD Started {task_id=} ")

        task_def = self._get_task_def_from_stacks(task_id)

        if task_def:
            self._process_callbacks_for_event(task_id, "start", ())

        return None

    def _progress_callback(self, task_id: str, percentage: float, message: str) -> None:
        """
        Handles the 'progress' event for a task.

        Args:
            task_id (str): The ID of the task.
            percentage (float): The progress percentage.
            message (str): The progress message.
        """

        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(percentage, float), f"{percentage=}. Must be a float"
        assert isinstance(message, str), f"{message=}. Must be a string"

        if DEBUG:
            print(f"DBG TD Progress {task_id=} {percentage=} {message=}")

        task_def = self._get_task_def_from_stacks(task_id)

        if task_def:
            self._process_callbacks_for_event(
                task_id, "progress", (percentage, message)
            )

        return None

    def _finished_callback(self, task_id: str, result_tuple: tuple[int, str]) -> None:
        """
        Handles the 'finished' event for a task.

        Args:
            task_id (str): The ID of the task.
            result_tuple (tuple[int, str]): The result tuple.
        """

        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(result_tuple, tuple), f"{result_tuple=}. Must be a tuple"

        if DEBUG:
            print(f"DBG  Finish {task_id=} {result_tuple=}")

        task_def = None

        with self._stack_lock:
            task_def = self._task_stack.pop(task_id, None)

            if task_def:
                self._completed_stack[task_id] = task_def
                task_def.cargo["result_tuple"] = result_tuple
            else:
                if DEBUG:
                    print(
                        f"DBG_WARN: _finished_callback called for unknown or already moved task_id: {task_id}. "
                        f"No task_def to process."
                    )
                return

        final_result_tuple = (
            1 if result_tuple[0] == 1 else -1,
            "" if result_tuple[0] == 1 else "worker function failed!",
            result_tuple[0],
            result_tuple[1],
        )

        if result_tuple[0] == 1 and task_def and task_def.task_prefix:
            task_stack, completed_stack, error_stack, aborted_stack = (
                self._get_task_stacks(task_def.task_prefix)
            )

            if not task_stack and not error_stack and not aborted_stack:
                if DEBUG:
                    print(f"DBG All tasks with prefix {task_def.task_prefix} processed")

                final_result_tuple = (
                    1,
                    "All Done",
                    result_tuple[0],
                    result_tuple[1],
                )

        self._process_callbacks_for_event(
            task_id,
            "finish",
            final_result_tuple,
        )

        self._clear_stacks(task_id)

    def _error_callback(self, task_id: str, message: str) -> None:
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(message, str), f"{message=}. Must be a string"

        if DEBUG:
            print(f"DBG TD Error {task_id=} {message=}")

        task_def = None

        with self._stack_lock:
            task_def = self._task_stack.pop(task_id, None)

            if task_def:
                self._error_stack[task_id] = task_def
                task_def.cargo["error_code"] = -1
                task_def.cargo["error_message"] = message  #
            else:
                if DEBUG:
                    print(
                        f"DBG_WARN: _error_callback called for unknown or already moved task_id: {task_id}. "
                        f"No task_def to process."
                    )
                return None

        self._process_callbacks_for_event(task_id, "error", (-1, message))

        self._clear_stacks(task_id)

        return None

    def _aborted_callback(self, task_id: str, message: str) -> None:
        """
        Handles the 'aborted' event for a task.

        Args:
            task_id (str): The ID of the task.
            message (str): The abort message.
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )
        assert isinstance(message, str), f"{message=}. Must be a string"

        if DEBUG:
            print(f"DBG TR Abort {task_id=} {message=}")

        task_def = None

        with self._stack_lock:
            task_def = self._task_stack.pop(task_id, None)

            if task_def:
                self._aborted_stack[task_id] = task_def
                task_def.cargo["aborted_message"] = message
            else:
                if DEBUG:
                    print(
                        f"DBG_WARN: _aborted_callback called for unknown or already moved task_id: {task_id}. No "
                        f"task_def to process."
                    )
                return None

        self._process_callbacks_for_event(task_id, "abort", (-1, message))

        self._clear_stacks(task_id)

        return None

    def _get_task_def_from_stacks(self, task_id: str) -> Task_Def | None:
        """
        Gets task_def from any of the relevant stacks.

        Args:
            task_id (str): The task_id to lookup
        Returns:
            Task_Def | None: The task_def if found, else None
        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty string"
        )

        # This method is called from _process_callbacks_for_event, which acquires _stack_lock.
        # So, it doesn't need its own lock if only called from there.
        if task_id in self._task_stack:
            return self._task_stack[task_id]
        elif task_id in self._completed_stack:
            return self._completed_stack[task_id]
        elif task_id in self._error_stack:
            return self._error_stack[task_id]
        elif task_id in self._aborted_stack:
            return self._aborted_stack[task_id]
        else:
            if DEBUG:
                print(f"DBG {task_id=}. Not Found In any stacks during lookup.")
            return None

    def _get_task_stacks(self, task_prefix: str) -> tuple[dict, dict, dict, dict]:
        """
        Returns dictionaries containing only tasks whose IDs start with the given prefix.

        Args:
            task_prefix (str): The task_id starting task prefix

        Returns:
            task_stack (dict): Dict of pending tasks in the task_stack that start with the prefix
            completed_stack (dict): Dict of completed tasks in the completed_stack that start with the prefix
            error_stack (dict): Dict of errored tasks in the error_stack that start with the prefix
            aborted_stack (dict): Dict of aborted tasks in the aborted_stack that start with the prefix
        """
        assert isinstance(task_prefix, str) and task_prefix.strip() != "", (
            f"{task_prefix=}. Must be a non-empty str "
        )

        with self._stack_lock:
            task_stack = {
                key: value
                for key, value in self._task_stack.items()
                if value.task_prefix == task_prefix
            }

            completed_stack = {
                key: value
                for key, value in self._completed_stack.items()
                if value.task_prefix == task_prefix
            }

            error_stack = {
                key: value
                for key, value in self._error_stack.items()
                if value.task_prefix == task_prefix
            }

            aborted_stack = {
                key: value
                for key, value in self._aborted_stack.items()
                if value.task_prefix == task_prefix
            }

        return task_stack, completed_stack, error_stack, aborted_stack

    def _clear_stacks(self, task_id: str) -> None:
        """
        Clears entries from global stacks that match the given task id.
        Also clears related entries from _dispatch_methods.

        Args:
            task_id (str): The task_id to clear

        """
        assert isinstance(task_id, str) and task_id.strip() != "", (
            f"{task_id=}. Must be a non-empty str"
        )

        with self._stack_lock:
            # Filter and update the main task stacks
            self._task_stack = {
                key: value
                for key, value in self._task_stack.items()
                if not key.startswith(task_id)
            }

            self._completed_stack = {
                key: value
                for key, value in self._completed_stack.items()
                if not key.startswith(task_id)
            }

            self._error_stack = {
                key: value
                for key, value in self._error_stack.items()
                if not key.startswith(task_id)
            }

            self._aborted_stack = {
                key: value
                for key, value in self._aborted_stack.items()
                if not key.startswith(task_id)
            }

            keys_to_remove = [
                key for key in self._dispatch_methods.keys() if key.startswith(task_id)
            ]

            for key in keys_to_remove:
                del self._dispatch_methods[key]

        if DEBUG:
            print(
                f"DBG: TD Cleared stacks for prefix {task_id}. Current _completed_stack:"
                f" {list(self._completed_stack.keys())}"
            )
            print(
                f"DBG: TD Cleared dispatch methods for prefix {task_id}. Current _dispatch_methods tasks:"
                f" {list(k.split('|')[0] for k in self._dispatch_methods.keys())}"
            )
        return None


@dataclasses.dataclass
class Task_Manager_Popup(qtg.PopContainer):
    """Allows management of background tasks"""

    task_qmanager: Task_QManager = Task_QManager()

    tag: str = "Task_Manager_Popup"

    # Private instance variable
    _db_settings: sqldb.App_Settings | None = None

    def __post_init__(self) -> None:
        """Sets-up the form"""
        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  form events
        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                task_grid = cast(
                    qtg.Grid,
                    event.widget_get(
                        container_tag="task_controls", tag="task_manager_grid"
                    ),
                )

                col_index: int = task_grid.colindex_get("task_name")

                for row_index, task in enumerate(
                    self.task_qmanager.active_tasks().keys()
                ):
                    task_grid.value_set(
                        value=task,
                        row=row_index,
                        col=col_index,
                        user_data=task,
                    )

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "kill_tasks":
                        task_grid = cast(
                            qtg.Grid,
                            event.widget_get(
                                container_tag="task_controls", tag="task_manager_grid"
                            ),
                        )

                        checked_items = task_grid.checkitems_get
                        if checked_items:
                            with qtg.sys_cursor(qtg.Cursor.hourglass):
                                for item in checked_items:
                                    task_name = item.current_value

                                    self.task_qmanager.cancel_task(task_name)

                                self.task_qmanager.wait_for_finished()

                                task_grid.clear()

                                col_index: int = task_grid.colindex_get("task_name")

                                for row_index, task in enumerate(
                                    self.task_qmanager.active_tasks().keys()
                                ):
                                    task_grid.value_set(
                                        value=task,
                                        row=row_index,
                                        col=col_index,
                                        user_data=task,
                                    )
                        else:
                            popups.PopMessage(
                                title="Please Select Tasks...",
                                message="Please Select Tasks To Kill!",
                            ).show()
                    case "ok":
                        if self._process_ok(event) == 1:
                            self.set_result(event.tag)
                            super().close()
                    case "select_all":
                        task_grid = cast(
                            qtg.Grid,
                            event.widget_get(
                                container_tag="task_controls", tag="task_manager_grid"
                            ),
                        )

                        task_grid.checkitems_all(
                            checked=event.value, col_tag="task_name"
                        )

    def _process_ok(self, event: qtg.Action) -> int:
        """
        Handles processing the ok button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if the ok process id good, -1 otherwise
        """

        self.set_result("")

        return 1

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        task_control_container = qtg.VBoxContainer(
            tag="task_controls", align=qtg.Align.TOPLEFT
        )

        task_col_def = (
            qtg.Col_Def(
                label="Task Name",
                tag="task_name",
                width=40,
                editable=False,
                checkable=True,
            ),
        )

        running_tasks = qtg.Grid(
            tag="task_manager_grid",
            noselection=True,
            height=15,
            col_def=task_col_def,
            callback=self.event_handler,
        )

        task_control_container.add_row(
            qtg.Checkbox(
                text="Select All",
                tag="select_all",
                callback=self.event_handler,
                tooltip="Select All Tasks",
                width=10,
            ),
            running_tasks,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )
        control_container.add_row(
            task_control_container,
            qtg.HBoxContainer(tag="command_buttons", margin_right=5).add_row(
                qtg.Button(
                    tag="kill_tasks",
                    text="Kill Tasks",
                    callback=self.event_handler,
                    width=10,
                ),
                qtg.Spacer(width=24),
                qtg.Command_Button_Container(
                    ok_callback=self.event_handler,
                ),
            ),
        )
        return control_container
