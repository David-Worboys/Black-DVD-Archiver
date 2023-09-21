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
from typing import Callable, Optional, cast

import popups
import qtgui as qtg
import sqldb
import sys_consts

# fmt: on


@dataclasses.dataclass(slots=True)
class _Task:
    """
    A class that represents a background task.

    Attributes:
        name (str): The name of the task.
        method (Callable): The method to be executed
        arguments (any): The arguments to be passed to the method
        callback (Callable[[int, str, str, str], None]): The callback to call when the task is finished.
    """

    name: str
    method: Callable
    arguments: any
    callback: Callable[[int, str, str, str], None]  # status, message, output, task_name
    crashed: bool = False
    kill_signal: bool = False

    def __post_init__(self):
        """Configures instance for use"""
        assert isinstance(self.name, str), f"{self.name=}. Must be a string"
        assert isinstance(self.method, Callable), f"{self.method=}. Must be a callable"
        # assert isinstance(self.arguments, list), f"{self.arguments=}. Must be a list"
        # assert all(
        #    isinstance(command, str) for command in self.arguments
        # ), f"{self.arguments=}. Must be a str"
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

    _throw_errors: bool = True
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

    @property
    def throw_errors(self) -> bool:
        return self._throw_errors

    @throw_errors.setter
    def throw_errors(self, value: bool):
        assert isinstance(value, bool), f"{value=}. Must be bool"
        self._throw_errors = value

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

        if self.error_callback is not None and self.throw_errors:
            self.error_callback("Task Manager has crashed with SIGSEGV (signal 9)")

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
                executor, task.method, task.arguments
            )

            if task.crashed:
                if self.throw_errors:
                    task.callback(-1, "crash", "", task.name)
            else:
                task.callback(status, "ok", output, task.name)

        except Exception as e:
            if self.error_callback is not None and self.throw_errors:
                self.error_callback(
                    f"Task {task.name} encountered an exception: {str(e)}"
                )

        if task.kill_signal:
            if task.name in self._running_tasks:
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
                # Check if the stop event is set and the task queue is empty
                break

            if self._task_queue:
                task = self._task_queue.pop(0)
                await process_task(task)
            else:
                await asyncio.sleep(0.1)

            # Check for tasks that need to be killed
            for task_name, task in self._running_tasks.items():
                if task.kill_signal:
                    # Set the kill signal for the task
                    task.kill_signal = False  # Reset the kill signal
                    task.crashed = True  # Mark the task as crashed if needed
                    if self.throw_errors:
                        task.callback(-1, "killed", "", task.name)

                    if task_name in self._running_tasks:
                        del self._running_tasks[task_name]

    def add_task(
        self,
        name: str,
        method: Callable,
        arguments: any,
        callback: Callable[[int, str, str, str], None],
    ):
        """
        Adds a task to the task queue.

        Args:
            name (str): The name of the task.
            method: (Callable): The method/function to be called. By default, this is Execute_Check_Output
            arguments (any): The arguments to be passed to the method.
            callback (Callable[[int, str, str, str], None]): The callback function to be called when the task is finished.

        """
        assert (
            isinstance(name, str) and name.strip() != ""
        ), f"{name=}. Must be a non-empty str"
        assert isinstance(method, Callable), f"{method=}. Must be a callable"
        assert isinstance(callback, Callable), f"{callback=}. Must be a callable"

        task = _Task(name=name, method=method, arguments=arguments, callback=callback)
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
            # task.crashed = True
            task.kill_signal = True

            if self.throw_errors:
                task.callback(-1, "killed", "", task.name)

            if name in self._running_tasks:
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
                if self.throw_errors:
                    task.crashed = True
                    task.callback(-1, "killed", "", task.name)

            self._running_tasks = {}

            # Clear the task queue
            self._task_queue = []


@dataclasses.dataclass
class Task_Manager_Popup(qtg.PopContainer):
    """Allows management of background tasks"""

    task_manager: Task_Manager | None = None  # Pass by reference
    tag: str = "Task_Manager_Popup"

    # Private instance variable
    _db_settings: sqldb.App_Settings | None = None

    def __post_init__(self) -> None:
        """Sets-up the form"""
        assert isinstance(
            self.task_manager, Task_Manager
        ), f"{self.task_manager=}. Must be an instance of Task_Manager"

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
                    self.task_manager.list_running_tasks()
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
                            self.task_manager.throw_errors = False

                            with qtg.sys_cursor(qtg.Cursor.hourglass):
                                for item in checked_items:
                                    task_name = item.current_value

                                    self.task_manager.kill_task(task_name)

                                task_grid.clear()

                                col_index: int = task_grid.colindex_get("task_name")

                                for row_index, task in enumerate(
                                    self.task_manager.list_running_tasks()
                                ):
                                    task_grid.value_set(
                                        value=task,
                                        row=row_index,
                                        col=col_index,
                                        user_data=task,
                                    )

                            self.task_manager.throw_errors = True
                        else:
                            popups.PopMessage(
                                title="Please Select Tasks...",
                                message="Please Select Tasks To Kill!",
                            ).show()
                    case "ok":
                        if self._process_ok(event) == 1:
                            self.set_result(event.tag)
                            super().close()

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
        file_control_container = qtg.VBoxContainer(
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

        video_input_files = qtg.Grid(
            tag="task_manager_grid",
            noselection=True,
            height=15,
            col_def=task_col_def,
            callback=self.event_handler,
        )

        file_control_container.add_row(
            video_input_files,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )

        control_container.add_row(
            file_control_container,
            qtg.HBoxContainer(tag="command_buttons").add_row(
                qtg.Button(
                    tag="kill_tasks",
                    text="Kill Tasks",
                    callback=self.event_handler,
                    width=10,
                ),
                qtg.Command_Button_Container(
                    ok_callback=self.event_handler,  # cancel_callback=self.event_handler
                ),
            ),
        )

        return control_container
