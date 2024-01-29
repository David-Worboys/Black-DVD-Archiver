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
import dataclasses
import multiprocessing.dummy as multiprocessing
import signal
import threading
from multiprocessing.shared_memory import SharedMemory
from time import sleep
from typing import Callable, Optional, cast

import popups
import qtgui as qtg
import sqldb
import sys_consts

# fmt: on


@dataclasses.dataclass
class _Task:
    """
    Represents a task to be executed by the task manager.

    Note:
        The `stop` method can be used to forcefully terminate a task's associated process.
        It is important to handle task termination carefully to prevent resource leaks.

    """

    name: str
    method: Callable
    arguments: any
    callback: Callable[[int, str, str, str], None]
    crashed: bool = False
    kill_signal: bool = False
    process: Optional[multiprocessing.Process] = None

    def __post_init__(self):
        assert isinstance(self.name, str), f"{self.name=}. Must be a string"
        assert isinstance(self.method, Callable), f"{self.method=}. Must be a callable"
        assert isinstance(
            self.callback, Callable
        ), f"{self.callback=}. Must be a callable"


class Task_Manager:
    """
    A class that represents a background task manager.

    Attributes:
        error_callback (Callable[[str], None]): The callback to call when the task manager crashes.
    """

    def __init__(self):
        self.error_callback = None
        self._throw_errors = True
        self._task_queue = multiprocessing.Queue()
        self._task_list = []
        self._running_tasks_dict = {}
        self._thread = None
        self._crash_event = None
        self._lock = threading.Lock()

        self._stop_event = threading.Event()
        self._running_tasks_updated = multiprocessing.Event()
        self._manager = multiprocessing.Manager()
        self._running_tasks = multiprocessing.Queue()
        self._update_event = multiprocessing.Event()

    @property
    def throw_errors(self) -> bool:
        return self._throw_errors

    @throw_errors.setter
    def throw_errors(self, value: bool):
        assert isinstance(value, bool), f"{value=}. Must be bool"
        self._throw_errors = value

    def _handle_crash(self, signum, frame):
        """
        Handles a SIGSEGV (signal 9) signal and call the error_callback if it is registered.

        Args:
            signum (int): Is the signal number.
            frame (any): Is frame

        """
        print("Task Manager has crashed with SIGSEGV (signal 9)")

        self._crash_event.set()

        if self.error_callback is not None and self.throw_errors:
            self.error_callback("Task Manager has crashed with SIGSEGV (signal 9)")

    def _process_task(self, task: _Task, args):
        """
        The _process_task method executes the command in the task asynchronously.
        It runs this function in a separate process to avoid blocking the main program.
        It handles errors and crashes gracefully and terminates the process when needed.

        Args:
            task (_Task): The task object to be executed.
        """

        shared_mem_name = task.name

        if self._crash_event.is_set():
            task.crashed = True

        try:
            task.process = multiprocessing.Process(
                target=task.method, args=(task.arguments,)
            )

            status, output = task.method(*task.arguments)

            if task.crashed:
                if self.throw_errors:
                    self._write_to_shared_memory(
                        shared_mem_name=shared_mem_name,
                        message=f"{task.name}|crash",
                    )
                    task.callback(-1, "crash", "", task.name)
            else:
                self._write_to_shared_memory(
                    shared_mem_name=shared_mem_name, message=f"{task.name}|ok"
                )
                task.callback(status, "ok", "" if output is None else output, task.name)

        except Exception as e:
            self._write_to_shared_memory(
                shared_mem_name=shared_mem_name, message=f"{task.name}|exception"
            )
            task.callback(-1, "error", "" if e is None else e, task.name)

        with self._lock:
            self._running_tasks_updated.set()  # Signal the update event

    def _task_handler(self):
        """
        The _task_handler method is the main loop of the background task handler.
        It runs until the _stop_event is set and the _task_queue is empty.
        """
        debug = False

        while not self._stop_event.is_set():
            if self._update_event.wait(timeout=1):  # Wait for up to 1 second
                while (
                    not self._task_queue.empty()
                ):  # Check if there are tasks in the queue
                    with self._lock:
                        task = self._task_queue.get_nowait()

                    with self._lock:
                        self._running_tasks.put(task.name)
                        self._update_event.set()

                    # This might look superfluous, but it is very necessary if I am to determine what task is done
                    try:
                        shared_mem = SharedMemory(name=task.name)
                    except FileNotFoundError:
                        # Shared memory with the given name doesn't exist; create a new one
                        shared_mem = SharedMemory(name=task.name, create=True, size=512)

                    task.process = multiprocessing.Process(
                        target=self._process_task,
                        args=(task, task.arguments),
                        name=task.name,
                    )

                    try:
                        self._running_tasks_dict[task.name] = task

                        task_names = list(self._running_tasks_dict.keys())
                        with self._lock:
                            for task_name in task_names:
                                self._running_tasks.put(
                                    task_name
                                )  # Put updated task names into the Queue
                                self._update_event.set()  # Signal the update event

                        task.process.start()
                    except Exception as e:
                        print(f"_Task_Handler Error {e}")

            sleep(0.1)

            if self._running_tasks_updated.wait(timeout=1):  # Wait for up to 1 second
                for task_name in self._running_tasks_dict.copy().keys():
                    with self._lock:
                        try:
                            with SharedMemory(name=task_name) as shared_mem:
                                content = shared_mem.buf.tobytes().decode("utf-8")

                                if debug:
                                    print(
                                        f"Shared Memory Block Found {task_name=} {content=}"
                                    )
                        except FileNotFoundError:
                            del self._running_tasks_dict[task_name]
                            self._running_tasks_updated.clear()

                            if debug:
                                print(
                                    f"Shared Memory Block Not Found {task_name=} And Deleted From {self._running_tasks_dict.keys()=}"
                                )
                        except Exception as e:
                            if debug:
                                print(f"Ignoring memory block '{task_name}'  {e}")
                            else:
                                pass
            try:
                for task_name, task in list(self._running_tasks_dict.items()):
                    if task.kill_signal:
                        if task_name in self._running_tasks_dict:
                            del self._running_tasks_dict[task_name]

                            task_names = list(self._running_tasks_dict.keys())

                            with self._lock:
                                self._running_tasks.put(
                                    task_names
                                )  # Put updated task names into the Queue
                                self._update_event.set()  # Signal the update event

            except Exception as e:
                print(f"_Task_Handler {e=}")

    def _write_to_shared_memory(self, shared_mem_name: str, message: str):
        """Writes a message to a shared memory block, creating it if necessary.

        Args:
            shared_mem_name (str): Name of the shared memory block.
            message (str): Message to write to the shared memory.
        """

        assert (
            isinstance(shared_mem_name, str) and shared_mem_name.strip() != ""
        ), f"{shared_mem_name=}. Must be non-empty str"
        assert isinstance(message, str), f"{message=}. Must be str"

        try:
            data_bytes = message.encode("ascii")

            # Check for existing shared memory block, creating if needed
            try:
                shared_mem = SharedMemory(name=shared_mem_name)
            except FileNotFoundError:
                shared_mem = SharedMemory(
                    create=True, name=shared_mem_name, size=len(data_bytes)
                )

            shared_mem.buf[: len(data_bytes)] = data_bytes

        except Exception as e:
            print(f"Unexpected error writing to shared memory: {e}")
        finally:
            shared_mem.close()
            if not shared_mem.name.startswith("__"):  # Avoid unlinking temporary blocks
                shared_mem.unlink()  # Release system resources

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

        with self._lock:
            self._task_queue.put(task)
            self._update_event.set()  # Signal the update event

    def list_running_tasks(self) -> list[str]:
        """
        Returns a list of names of the currently running tasks.

        Returns:
            list[str]: The list of names of the currently running tasks.
        """
        return list(self._running_tasks_dict.keys())

    def kill_task(self, name: str):
        """Kills the running task with the specified name."""
        with self._lock:
            task = self._running_tasks_dict.get(name)

        if task is not None:
            task.kill_signal = True

    def set_error_callback(self, callback: Callable[[str], None]):
        """
        Sets the error callback function.

        Args:
            callback (Callable[[str], None]): The callback function to be called when an error occurs.
        """
        assert isinstance(callback, Callable), f"{callback=}. Must be a callable"

        self.error_callback = callback

    def start(self):
        """The _start_task_handler method starts the task handler."""
        if self._thread is None or not self._thread.is_alive():
            self._crash_event = threading.Event()
            signal.signal(signal.SIGSEGV, self._handle_crash)
            self._thread = threading.Thread(target=self._task_handler, daemon=True)
            self._thread.start()

    def stop(self):
        """Stops the background task handler."""

        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()

            for task_name, task in self._running_tasks_dict.items():
                task.kill_signal = True

                if self.throw_errors:
                    task.crashed = True
                    task.callback(-1, "killed", "", task.name)

            self._task_queue = []
            self._running_tasks_dict = {}


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
                                sleep(0.5)

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
