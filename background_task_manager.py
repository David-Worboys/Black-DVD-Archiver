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

# Tell Black to leave this block alone (realm of isort)
# fmt: off
import asyncio
import concurrent.futures
import dataclasses
import signal
import threading
from typing import Callable, Optional

from dvdarch_utils import Execute_Check_Output

# fmt: on


@dataclasses.dataclass(slots=True)
class _Task:
    """
    A class that represents a background task.

    Attributes:
        name (str): The name of the task.
        command (list[str]): The commands to execute.
        callback (Callable[[int, str, str, str], None]): The callback to call when the task is finished.
    """

    name: str
    command: list[str]
    callback: Callable[[int, str, str, str], None]  # status, message, output, task_name
    crashed: bool = False

    def __post_init__(self):
        """Configures instance for use"""
        assert isinstance(self.name, str), f"{self.name=}. Must be a string"
        assert isinstance(self.command, list), f"{self.command=}. Must be a list"
        assert all(
            isinstance(command, str) for command in self.command
        ), f"{self.command=}. Must be a str"
        assert isinstance(
            self.callback, Callable
        ), f"{self.callback=}. Must be a callable"


@dataclasses.dataclass(slots=True)
class Task_Manager:
    """
    A class that represents a background task manager.

    Attributes:
        error_callback (Callable[[str], None]): The callback to call when the task manager crashes.
    """

    error_callback: Optional[Callable[[str], None]] = None

    _task_queue: list[_Task] | None = None
    _running_tasks: dict[str, _Task] | None = None
    _thread: Optional[threading.Thread] | None = None
    _stop_event: Optional[threading.Event] | None = None
    _crash_event: Optional[threading.Event] | None = None

    def __post_init__(self):
        """Configures instance for use"""
        assert isinstance(self.error_callback, (type(None), Callable[[str], None]))
        assert isinstance(
            self.error_callback, (type(None), Callable[[str], None])
        ), f"{self.error_callback=}. Must be a callable or None"

        self._task_queue = []
        self._running_tasks = {}
        self._thread = None
        self._stop_event = None

        self._crash_event = threading.Event()

        signal.signal(signal.SIGSEGV, self._handle_crash)

    def _handle_crash(self, signum: int, frame: any) -> None:
        """
        Handles a SIGSEGV (signal 9) signal and call the error_callback if it is registered.

        Args:
            signum (int): Is the signal number.
            frame (any): Is frame

        """
        assert isinstance(signum, int), f"{signum=}. Must be an integer"
        # assert isinstance(frame, any), f"{frame=}. Must be any"

        print("_Task Manager has crashed with SIGSEGV (signal 9)")
        self._crash_event.set()

        if self.error_callback is not None:
            self.error_callback("_Task Manager has crashed with SIGSEGV (signal 9)")

    async def _process_task(self, task: _Task):
        """
        The _process_task method is a coroutine that executes the command in the task.
        It uses asyncio to run this function in a separate thread, so it doesn't block
        the main event loop. It also handles errors and crashes gracefully.

        Args:
            task: (_Task): The task object to be executed

        """
        if self._crash_event.is_set():
            task.crashed = True

        try:
            loop = asyncio.get_event_loop()
            executor = concurrent.futures.ThreadPoolExecutor()
            status, output = await loop.run_in_executor(
                executor, Execute_Check_Output, task.command
            )

            if not task.crashed:
                task.callback(status, "ok", output, task.name)
            else:
                task.callback(-1, "crash", "", task.name)

        except Exception as e:
            if self.error_callback is not None:
                self.error_callback(
                    f"_Task {task.name} encountered an exception: {str(e)}"
                )

        del self._running_tasks[task.name]

    async def _task_handler(self):
        """
        The _task_handler method is the main loop of the background task handler. It runs until the _stop_event is set
        and the _task_queue is empty.
        """

        async def process_task(task):
            self._running_tasks[task.name] = task
            await self._process_task(task)
            if task.name in self._running_tasks:
                del self._running_tasks[task.name]

        while True:
            if self._stop_event.is_set() and not self._task_queue:
                break

            if self._task_queue:
                task = self._task_queue.pop(0)
                await process_task(task)
            else:
                await asyncio.sleep(0.1)

    def add_task(
        self,
        name: str,
        command: list[str],
        callback: Callable[[int, str, str, str], None],
    ):
        """
        Adds a task to the task queue.

        Args:
            name (str): The name of the task.
            command (list[str]): The command to be executed.
            callback (Callable[[int, str, str, str], None]): The callback function to be called when the task is finished.
        """
        assert isinstance(name, str), f"{name=}. Must be a string"
        assert isinstance(command, list), f"{command=}. Must be a list"
        assert all(
            isinstance(command, str) for command in command
        ), f"{command=}. Must be a list of str"
        assert isinstance(callback, Callable), f"{callback=}. Must be a callable"

        task = _Task(name, command, callback)
        self._task_queue.append(task)

    def list_running_tasks(self) -> list[str]:
        """
        Returns a list of names of the currently running tasks.

        Returns:
            list[str]: The list of names of the currently running tasks.
        """
        return list(self._running_tasks.keys())

    def kill_task(self, name: str):
        """
        Kills the running task with the specified name.
        """
        task = self._running_tasks.get(name)
        if task is not None:
            task.crashed = True
            task.callback(-1, "killed", "", task.name)
            del self._running_tasks[name]

    def set_error_callback(self, callback: Callable[[str], None]):
        """
        Sets the error callback function.

        Args:
            callback (Callable[[str], None]): The callback function to be called when an error occurs.
        """
        assert isinstance(callback, Callable), f"{callback=}. Must be a callable"

        self.error_callback = callback

    def start(self):
        """
        Starts the background task handler.
        """

        if self._thread is None or not self._thread.is_alive():
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._start_task_handler)
            self._thread.start()

    def _start_task_handler(self):
        """
        The _start_task_handler method starts the task handler.
        It creates a new event loop, sets it as the default event loop, and runs until complete.
        The _task_handler method is called to start the task handler.

        """

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._task_handler())
        loop.close()

    def stop(self):
        """
        Stops the background task handler.
        """
        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()
            self._stop_event.clear()

            # Reset the crash event
            self._crash_event.clear()

            # Terminate running tasks
            for task in self._running_tasks.values():
                task.crashed = True
                task.callback(-1, "killed", "", task.name)
            self._running_tasks = {}

            # Clear the task queue
            self._task_queue = []
