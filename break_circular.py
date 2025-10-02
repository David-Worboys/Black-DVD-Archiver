"""
This miserable module exists to break circular dependencies

Copyright (C) 2025  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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
import os
import subprocess
import threading
import shlex
import traceback
from time import sleep
from typing import Callable, Any, Optional

from QTPYGUI.utils import Singleton, Is_Complied


#### Start From dvdarch_utils
def Execute_Check_Output(
    commands: list[str],
    env: dict | None = None,
    execute_as_string: bool = False,
    debug: bool = False if Is_Complied() else True,
    shell: bool = False,
    stderr_to_stdout: bool = False,
    cancellation_callback: Optional[Callable[[], bool]] = None,
) -> tuple[int, str]:
    """
    Executes the given command(s) with the subprocess.Popen method.

    This wrapper provides better error and debug handling

    Args:
        commands (list[str]): non-empty list of commands and options to be executed.
        env (dict | None): A dictionary of environment variables to be set for the command. Defaults to None
        execute_as_string (bool): If True, the commands will be executed as a single string. Defaults to False
        debug (bool): If True, debug information will be printed. Defaults to False
        shell (bool): If True,  the command will be executed using the shell. Defaults to False
        stderr_to_stdout (bool): If True, the command will feed the stderr to stdout. Defaults to False.

    Returns:
        tuple[int, str]: A tuple containing the status code and the output of the command.

        - arg1: 1 if the command is successful, -1 if the command fails.
        - arg2: "" if the command is successful, if the command fails, an error message.
    """
    final_result: int = -1
    final_message: str = "Command did not execute or an unexpected error occurred."

    if env is None:
        env = {}

    assert isinstance(commands, list) and len(commands) > 0, (
        f"{commands=} must be a non-empty list of commands and options"
    )
    assert isinstance(execute_as_string, bool), f"{execute_as_string=} must be bool"
    assert isinstance(debug, bool), f"{debug=} must be bool"
    assert isinstance(env, dict), f"{env=} must be dict"
    assert isinstance(shell, bool), f"{shell=} must be bool"
    assert isinstance(stderr_to_stdout, bool), f"{stderr_to_stdout=}. Must be bool"
    assert callable(cancellation_callback) or cancellation_callback is None, (
        f"{cancellation_callback=}. Must be a function or None"
    )

    if cancellation_callback is None:
        cancellation_callback = Cancel_All_Tasks().is_cancellation_requested

    if debug and not Is_Complied():
        print(f"DBG Call command *** {' '.join(commands)}")
        print(f"DBG Call commands command list *** {commands}")
        if execute_as_string:
            print(
                f"DBG Call commands shlex split  *** {shlex.split(' '.join(commands))}"
            )
        print("DBG Lets Do It!")

    subprocess_args = {
        "args": commands if not execute_as_string else shlex.split(" ".join(commands)),
        "shell": shell,
        "universal_newlines": True,
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT if stderr_to_stdout else subprocess.PIPE,
    }

    process = None
    stdout_fd = None
    stderr_fd = None

    communicated_already = False

    try:
        process = subprocess.Popen(**subprocess_args)

        if debug and not Is_Complied():
            print(
                f"DBG Popen: Started process with PID {process.pid} for {' '.join(commands)}"
            )

        stdout_buffer = []
        stderr_buffer = []

        if process.stdout:
            stdout_fd = process.stdout.fileno()
            os.set_blocking(stdout_fd, False)

        if process.stderr and not stderr_to_stdout:
            stderr_fd = process.stderr.fileno()
            os.set_blocking(stderr_fd, False)

        # Polling loop for cooperative cancellation and incremental output capture
        while process.poll() is None:
            if (
                cancellation_callback and cancellation_callback()
            ) or Cancel_All_Tasks().is_cancellation_requested():
                if debug and not Is_Complied():
                    print(
                        f"DBG ECO: Cancellation detected for PID {process.pid}. Terminating..."
                    )

                process.terminate()

                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if debug and not Is_Complied():
                        print(
                            f"DBG ECO: Process {process.pid} did not terminate gracefully. Killing it."
                        )
                    process.kill()
                    process.wait()

                stdout_rem, stderr_rem = process.communicate()

                if stdout_rem:
                    stdout_buffer.append(stdout_rem)
                if not stderr_to_stdout and stderr_rem:
                    stderr_buffer.append(stderr_rem)
                communicated_already = True

                final_result = -2
                final_message = "".join(stdout_buffer).strip()
                break

            # Read non-blocking output
            if process.stdout:
                try:
                    chunk = process.stdout.read(4096)
                    if chunk:
                        stdout_buffer.append(chunk)
                except BlockingIOError:
                    pass
                except ValueError:
                    pass

            if process.stderr and not stderr_to_stdout:
                try:
                    chunk = process.stderr.read(4096)
                    if chunk:
                        stderr_buffer.append(chunk)
                except BlockingIOError:
                    pass
                except ValueError:
                    pass

            sleep(0.01)

        if (
            not communicated_already
        ):  # Process completed normally or due to external factors.
            stdout_final, stderr_final = process.communicate()

            if stdout_final:
                stdout_buffer.append(stdout_final)

            if not stderr_to_stdout and stderr_final:
                stderr_buffer.append(stderr_final)

            communicated_already = True

            output = "".join(stdout_buffer).strip()
            final_stderr_output = "".join(stderr_buffer).strip()

            return_code = process.returncode

            if return_code == 0 or return_code == 1:  # ffmpeg special case
                final_result = 1
                final_message = str(output)
            else:
                if return_code == 127:
                    message = (
                        f"Program Not Found Or Exited Abnormally \n {' '.join(commands)} ::"
                        f" {final_stderr_output or output}"
                    )
                elif return_code <= 125:
                    message = f"{return_code} Command Failed!\n {' '.join(commands)} :: {final_stderr_output or output}"
                else:
                    message = (
                        f"{return_code} Command Crashed!\n {' '.join(commands)} ::"
                        f" {final_stderr_output or output}"
                    )
                if debug and not Is_Complied():
                    print(f"DBG {message} {return_code=} :: {output}")

                final_result = -1
                final_message = message

    except FileNotFoundError:
        message = f"Command not found: '{commands[0]}'. Check your PATH."

        if debug and not Is_Complied():
            print(f"DBG {message}")

        final_result = -1
        final_message = message
    except Exception as e:
        message = f"Error executing command {' '.join(commands)}: {e}"

        if debug and not Is_Complied():
            print(f"DBG {message}")
            traceback.print_exc()

        final_result = -1
        final_message = message
    finally:  # Clean up
        if stdout_fd is not None:
            try:
                os.set_blocking(stdout_fd, True)
            except OSError:
                pass
        if stderr_fd is not None:
            try:
                os.set_blocking(stderr_fd, True)
            except OSError:
                pass

        if process and process.poll() is None and not communicated_already:
            if debug and not Is_Complied():
                print(
                    f"DBG Execute_Check_Output: Ensuring process {process.pid} is terminated in finally block."
                )

            process.terminate()

            try:
                process.wait(timeout=1)
                return final_result, final_message

            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

                return final_result, final_message

    return final_result, final_message


#### End From dvdarch_utils


#### Start From background_task_manager
@dataclasses.dataclass
class Task_Def:
    """A class that defines a task to be processed by a Background Task Manager"""

    task_id: str
    task_prefix: str = ""
    worker_function: Callable = None
    args: dict[str, Any] = dataclasses.field(default_factory=dict)
    kwargs: dict[str, Any] = dataclasses.field(default_factory=dict)
    started_callback: Callable = None
    error_callback: Callable = None
    finished_callback: Callable = None
    aborted_callback: Callable = None
    progress_callback: Callable = None
    cargo: dict = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        assert isinstance(self.task_id, str) and self.task_id.strip() != "", (
            f"{self.task_id=}.Must be a non-empty str"
        )
        assert isinstance(self.task_prefix, str), f"{self.task_prefix=}.Must be a str"
        assert (
            isinstance(self.worker_function, Callable) or self.worker_function is None
        ), f"{self.worker_function=}.Must be callable or None"
        assert isinstance(self.args, dict), f"{self.args=}.Must be a dict"
        assert isinstance(self.kwargs, dict), f"{self.kwargs=}.Must be a dict"
        assert (
            isinstance(self.started_callback, Callable) or self.started_callback is None
        ), f"{self.started_callback=}.Must be callable or None"
        assert (
            isinstance(self.error_callback, Callable) or self.error_callback is None
        ), f"{self.error_callback=}.Must be callable or None"
        assert (
            isinstance(self.finished_callback, Callable)
            or self.finished_callback is None
        ), f"{self.finished_callback=}.Must be callable or None"
        assert (
            isinstance(self.aborted_callback, Callable) or self.aborted_callback is None
        ), f"{self.aborted_callback=}.Must be callable or None"
        assert (
            isinstance(self.progress_callback, Callable)
            or self.progress_callback is None
        ), f"{self.progress_callback=}.Must be callable or None"

        assert isinstance(self.cargo, dict), f"{self.cargo=} Must be dict"


class Cancel_Task:
    """ " Manages a cancellation signal for a specific task."""

    def __init__(self):
        # threading.Event is thread-safe and efficient for signaling
        self._cancel_event = threading.Event()

    def request_cancellation(self):
        """Sets the internal flag to indicate cancellation is requested."""

        self._cancel_event.set()  # Set the event, signaling cancellation

    def reset_cancellation(self):
        """Clears the internal flag, allowing new tasks to run without immediate cancellation."""
        self._cancel_event.clear()  # Clear the event

    def is_cancellation_requested(self) -> bool:
        """Checks if cancellation has been requested."""
        return self._cancel_event.is_set()


class Cancel_All_Tasks(Cancel_Task, metaclass=Singleton):
    """Manages a global cancellation signal for all tasks."""

    def __init__(self):
        super().__init__()


#### End From background_task_manager
