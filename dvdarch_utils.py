"""
DVD archiver specific utility functions.

Copyright (C) 2022  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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
import fractions
import glob
import hashlib
import json
import math
import os
import os.path
import platform
import pprint
import shutil
import subprocess
import textwrap
from enum import Enum
from time import sleep
from typing import Final, Union, Optional, Callable
from itertools import filterfalse

import psutil

import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups

import sys_consts
import QTPYGUI.utils as utils

from background_task_manager import Task_QManager, Task_Dispatcher, Unpack_Result_Tuple
from bkp.utils import Get_Unique_Id
from break_circular import Execute_Check_Output, Task_Def
from sys_config import Encoding_Details, DVD_Menu_Page


class Color(Enum):
    """
    A class that represents different colors as RGB values.
    """

    WHITE = "#ffffff"
    BLACK = "#000000"
    GRAY = "#808080"
    RED = "#ff0000"
    GREEN = "#00ff00"
    BLUE = "#0000ff"
    YELLOW = "#ffff00"
    PURPLE = "#800080"
    ORANGE = "#ffa500"
    PINK = "#ffc0cb"
    BROWN = "#a52a2a"
    CYAN = "#00FFFF"
    LIGHTBLUE = "#add8e6"
    LIGHTGREEN = "#90ee90"
    LIGHTGRAY = "#d3d3d3"
    DARKGRAY = "#696969"
    DARKRED = "#8b0000"
    DARKBLUE = "#00008b"
    DARKGREEN = "#006400"
    BEIGE = "#f5f5dc"
    MAROON = "#800000"
    TURQUOISE = "#40e0d0"
    LIGHTYELLOW = "#ffffe0"
    LAVENDER = "#e6e6fa"
    NAVY = "#000080"
    OLIVE = "#808000"
    TEAL = "#008080"
    SILVER = "#c0c0c0"
    TRANSPARENT = "#00000000"
    GAINSBORO = "#DCDCDC"
    FLORALWHITE = "#FFFAF0"
    OLDLACE = "#FDF5E6"
    LINEN = "#FAF0E6"
    ANTIQUEWHITE = "#FAEBD7"
    PAPAYAWHIP = "#FFEFD5"
    BLANCHEDALMOND = "#FFEBCD"
    BISQUE = "#FFE4C4"
    PEACHPUFF = "#FFDAB9"
    NAVAJOWHITE = "#FFDEAD"
    MOCCASIN = "#FFE4B5"
    CORNSILK = "#FFF8DC"
    IVORY = "#FFFFF0"
    LEMONCHIFFON = "#FFFACD"
    SEASHELL = "#FFF5EE"
    HONEYDEW = "#F0FFF0"
    MINTCREAM = "#F5FFFA"
    AZURE = "#F0FFFF"
    ALICEBLUE = "#F0F8FF"
    LAVENDERBLUSH = "#FFF0F5"
    MISTYROSE = "#FFE4E1"
    ROSYBROWN = "#bc8f8f"
    SADDLEBROWN = "#8b4513"
    SANDYBROWN = "#f4a460"
    SEAGREEN = "#2e8b57"
    SIENNA = "#a0522d"
    SKYBLUE = "#87ceeb"
    SLATEBLUE = "#6a5acd"
    SLATEGRAY = "#708090"
    SNOW = "#fffafa"
    SPRINGGREEN = "#00ff7f"
    STEELBLUE = "#4682b4"
    TAN = "#d2b48c"
    THISTLE = "#d8bfd8"
    TOMATO = "#ff6347"
    VIOLET = "#ee82ee"
    WHEAT = "#f5deb3"
    WHITESMOKE = "#f5f5f5"
    YELLOWGREEN = "#9acd32"


class Gravity(Enum):
    """
    A class that represents different gravity values.
    """

    CENTER = "center"
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"
    STATIC = "static"
    FORGET = "forget"


@dataclasses.dataclass(slots=True)
class Dvd_Dims:
    """Dimensions of a DVD"""

    storage_width: int = -1
    storage_height: int = -1
    display_width: int = -1
    display_height: int = -1


@dataclasses.dataclass(slots=True)
class Cut_Video_Def:
    """Definition of a cut video"""

    input_file: str = ""
    output_file: str = ""
    start_cut: int = 0  # Frame
    end_cut: int = 0  # Frame
    frame_rate: float = 0.0
    tag: str = ""

    def __post_init__(self) -> None:
        assert isinstance(self.input_file, str) and self.input_file.strip() != "", (
            f"{self.input_file=}. Must be a non-empty str"
        )
        assert isinstance(self.output_file, str) and self.output_file.strip() != "", (
            f"{self.output_file=}. Must be a non-empty str"
        )
        assert isinstance(self.start_cut, int) and self.start_cut >= 0, (
            f"{self.start_cut=}. Must be a int >= 0"
        )
        assert isinstance(self.end_cut, int) and self.end_cut >= 0, (
            f"{self.end_cut=}. Must be a int >= 0"
        )

        assert isinstance(self.frame_rate, float) and self.frame_rate >= 24, (
            f"{self.end_cut_secs=}. Must be a float >= 24"
        )

        assert self.end_cut > self.start_cut, (
            f"{self.end_cut=} must be > {self.start_cut} "
        )

        assert isinstance(self.tag, str), f"{self.tag=}. Must be str"

    @property
    def start_cut_secs(self) -> float:
        """Returns the start cut in seconds"""

        return self.start_cut / self.frame_rate

    @property
    def end_cut_secs(self) -> float:
        """Returns the end cut in seconds"""

        return self.end_cut / self.frame_rate


def DVD_Percent_Used(total_duration: float, pop_error_message: bool = True):
    """
    Calculates the percentage of the DVD used based on the total duration of the videos assigned to that DVD.
    If the percentage used is > 100 then an error Popup is opened if pop_error_message is True

    Args:
        total_duration (float): total duration in seconds
        pop_error_message (bool): if True popup an error message if the percentage used is > 100

    Returns:
        int: percentage of DVD used

    """
    assert isinstance(total_duration, float) and total_duration >= 0.0, (
        f"{total_duration=}. Must be >= 0.0"
    )
    assert isinstance(pop_error_message, bool), f"{pop_error_message=}. Must be bool"

    dvd_percent_used = (
        round(
            (
                (sys_consts.AVERAGE_BITRATE * total_duration)
                / sys_consts.SINGLE_SIDED_DVD_SIZE
            )
            * 100
        )
        + sys_consts.PERCENT_SAFTEY_BUFFER
    )

    if pop_error_message and dvd_percent_used > 100:
        popups.PopError(
            title="DVD Build Error...",
            message="Selected Files Will Not Fit On A DVD!",
        ).show()
    return dvd_percent_used


def Get_Thread_Count() -> str:
    """
    Returns the number of threads we can use for processing video. This is a bit of a performance killer because I
    have been getting thermal-related crashes

    Returns:
        str : Number of threads we can use for processing video
    """
    if (
        psutil.cpu_count() is not None
        and psutil.cpu_count(logical=False) > 1  # Number of cores not threads
        and psutil.sensors_temperatures() is not None
        and psutil.sensors_temperatures()
    ):
        max_temp = 0

        for name, entries in psutil.sensors_temperatures().items():
            for entry in entries:
                if (
                    entry is not None
                    and entry.current is not None
                    and entry.current > max_temp
                ):
                    max_temp = entry.current

        if (
            max_temp > 85  # Try and keep temp below 85C
        ):  # Make usable thread count half the number of physical cores in the system (performance killer)
            thread_count = str(psutil.cpu_count(logical=False) // 2)
        else:
            thread_count = str(
                psutil.cpu_count(logical=True) // 2 + 1
            )  # Half the available thread count + 1
    else:
        thread_count = "1"

    return thread_count


def Mux_Demux_Video(
    input_file: str = "",
    output_file: str = "",
    audio_file_demuxed: str = "",
    video_file_demuxed: str = "",
    demux: bool = True,
    debug: bool = False,
) -> tuple[int, str, str, str]:
    """
    Performs demuxing or muxing of a video file using ffmpeg.

    Args:
        input_file (str): Path to the input video file.
        output_file (str): Path to the output video file.
        audio_file_demuxed (str): Path to the demuxed audio file (used for demuxing).
        video_file_demuxed (str): Path to the demuxed video file (used for demuxing).
        demux (bool): Flag indicating whether to demux (True) or mux (False).
        debug (bool): Flag for enabling debug output.

    Returns:
        A tuple of:
            - Result code (1 for success, -1 for error)
            - Error message ("" if none)
            - Path to the demuxed audio file (if demuxing)
            - Path to the demuxed video file (if demuxing)

    """
    assert isinstance(input_file, str), f"{input_file=}. Must be str"
    assert isinstance(output_file, str), f"{output_file=}. Must be str"
    assert isinstance(audio_file_demuxed, str), f"{audio_file_demuxed=}. Must be str"
    assert isinstance(video_file_demuxed, str), f"{video_file_demuxed=}. Must be str"
    assert isinstance(demux, bool), f"{demux=}. Must be bool"
    assert isinstance(debug, bool), f"{debug=}. Must be bool"

    file_handler = file_utils.File()

    if demux:
        out_path, _, _ = file_handler.split_file_path(input_file)

        if not file_handler.path_exists(input_file):
            return -1, f"File Does Not Exist: {input_file}", "", ""

        audio_file_demuxed = file_handler.file_join(
            out_path, f"{utils.Get_Unique_Id()}.ac3"
        )
        video_file_demuxed = file_handler.file_join(
            out_path, f"{utils.Get_Unique_Id()}.ts"
        )

        commands = [
            sys_consts.FFMPG,
            "-i",
            input_file,
            "-map",
            "0:a",
            "-c",
            "copy",
            "-threads",
            "0",
            audio_file_demuxed,
        ]
        result, message = Execute_Check_Output(commands=commands)

        if result == -1:
            return -1, message, "", ""

        commands = [
            sys_consts.FFMPG,
            "-i",
            input_file,
            "-map",
            "0:v",
            "-c",
            "copy-threads",
            "0",
            video_file_demuxed,
        ]
        result, message = Execute_Check_Output(commands=commands)

        if result == -1:
            return -1, message, "", ""

        return 1, "", audio_file_demuxed, video_file_demuxed
    else:  # Mux
        if not file_handler.path_exists(audio_file_demuxed):
            return -1, f"File Does Not Exist: {audio_file_demuxed}", "", ""

        if not file_handler.path_exists(video_file_demuxed):
            return -1, f"File Does Not Exist: {video_file_demuxed}", "", ""

        commands = [
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            "-i",
            video_file_demuxed,
            "-threads",
            "0",
            "-i",
            audio_file_demuxed,
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            output_file,
            "-threads",
            "0",
            "-y",
        ]

        result, message = Execute_Check_Output(commands=commands, debug=debug)

        if result == -1:
            return -1, message, "", ""

        if not debug and file_handler.remove_file(audio_file_demuxed) == -1:
            return (
                -1,
                f"Failed to delete demuxed audio file: {audio_file_demuxed}",
                "",
                "",
            )

        if not debug and file_handler.remove_file(video_file_demuxed) == -1:
            return (
                -1,
                f"Failed to delete demuxed video file: {video_file_demuxed}",
                "",
                "",
            )

        return 1, "", "", ""


def Concatenate_Videos(
    video_files: list[str],
    output_file: str,
    audio_codec: str = "",
    delete_temp_files: bool = True,
    transcode_format: str = "",
    debug: bool = False,
) -> tuple[int, str, str]:
    """
    Concatenates video files using ffmpeg.

    Args:
        video_files (list[str]): List of input video files to be concatenated
        output_file (str): The joined (concatenated) output file name.
            Note Transcode concats will use the folder and file name but will have the transcode_format extension
        audio_codec (str): The audio codec to checked against (aac is special)
        delete_temp_files (bool): Whether to delete the temp files, defaults to False
        transcode_format (str): Transcode files as per the transcode_format and then joins (concatenates) the files.
            Note: Transcodes are slow, defaults to "". legal values are dv | h264 | h265 | mpg | mjpeg
        debug (bool): True, print debug info, otherwise do not

    Returns:
        tuple[int, str, str]:
            - arg 1: 1 if success, -1 if error
            - arg 2: "" if success otherwise and error message
            - arg 3: container_format  if success otherwise ""
    """

    #### Helper functions
    def _transcode_video(
        input_file: str,
        transcode_path: str,
        encoding_info: Encoding_Details,
        transcode_format: str,
    ) -> tuple[int, str]:
        """
        Transcodes a single video file to a specified format.

        Args:
            input_file (str): The path to the input video file.
            transcode_path (str): The path to the directory where the transcoded file will be stored.
            encoding_info (Encoding_Details): An object containing the encoding information of the input video.
            transcode_format (str): The desired output format for transcoding. Valid values are:
                                    "dv", "ffv1", "h264", "h265", "mpg", "mjpeg", or "" for stream copy.

        Returns:
            tuple[int, str]:
                - int: 1 if transcoding was successful, -1 if an error occurred.
                - str: The path to the transcoded file if successful, or an error message if an error occurred.
        """
        assert isinstance(input_file, str) and input_file.strip(), (
            "input_file must be a non-empty string."
        )
        assert isinstance(transcode_path, str) and transcode_path.strip(), (
            "transcode_path must be a non-empty string."
        )
        assert isinstance(encoding_info, Encoding_Details), (
            "encoding_info must be an Encoding_Details object."
        )
        assert isinstance(transcode_format, str) and (
            transcode_format := transcode_format.strip()  # Note assignment
        ) in (
            "dv",
            "ffv1",
            "h264",
            "h265",
            "mpg",
            "mjpeg",
            "",
        ), "transcode_format must be a valid format string."

        file_handler = file_utils.File()
        _, file_name, file_ext = file_handler.split_file_path(input_file)

        match str(transcode_format):  # Keeps Pycharm happy
            case "dv":
                transcode_file = file_handler.file_join(
                    transcode_path, file_name, "avi"
                )

                result, message = Transcode_DV(
                    input_file=input_file,
                    output_folder=transcode_path,
                    frame_rate=encoding_info.video_frame_rate,
                    width=encoding_info.video_width,
                    height=encoding_info.video_height,
                    black_border=False,
                )

                if result == -1:
                    return -1, message

            case "ffv1":
                transcode_file = file_handler.file_join(
                    transcode_path, file_name, "mkv"
                )

                result, message = Transcode_ffv1_archival(
                    input_file=input_file,
                    output_folder=transcode_path,
                    frame_rate=encoding_info.video_frame_rate,
                    width=encoding_info.video_width,
                    height=encoding_info.video_height,
                )

                if result == -1:
                    return -1, message

            case "h264":
                transcode_file = file_handler.file_join(
                    transcode_path, file_name, "mp4"
                )

                result, message = Transcode_H26x(
                    input_file=input_file,
                    output_folder=transcode_path,
                    frame_rate=encoding_info.video_frame_rate,
                    width=encoding_info.video_width,
                    height=encoding_info.video_height,
                    interlaced=(
                        True
                        if encoding_info.video_scan_type.lower() == "interlaced"
                        else False
                    ),
                    bottom_field_first=(
                        True
                        if encoding_info.video_scan_order.lower() == "bff"
                        else False
                    ),
                    h265=False,
                    high_quality=True,
                    black_border=False,
                )

                if result == -1:
                    return -1, message
            case "h265":
                transcode_file = file_handler.file_join(
                    transcode_path, file_name, "mp4"
                )

                result, message = Transcode_H26x(
                    input_file=input_file,
                    output_folder=transcode_path,
                    frame_rate=encoding_info.video_frame_rate,
                    width=encoding_info.video_width,
                    height=encoding_info.video_height,
                    interlaced=(
                        True
                        if encoding_info.video_scan_type.lower() == "interlaced"
                        else False
                    ),
                    bottom_field_first=(
                        True
                        if encoding_info.video_scan_order.lower() == "bff"
                        else False
                    ),
                    h265=True,
                    high_quality=True,
                    black_border=False,
                )

                if result == -1:
                    return -1, message
            case "mpg":
                transcode_file = file_handler.file_join(
                    transcode_path, file_name, "mpg"
                )

                result, message = Transcode_MPEG2_High_Bitrate(
                    input_file=input_file,
                    output_folder=transcode_path,
                    frame_rate=encoding_info.video_frame_rate,
                    width=encoding_info.video_width,
                    height=encoding_info.video_height,
                    interlaced=(
                        True
                        if encoding_info.video_scan_type.lower() == "interlaced"
                        else False
                    ),
                    bottom_field_first=(
                        True
                        if encoding_info.video_scan_order.lower() == "bff"
                        else False
                    ),
                    black_border=False,
                )

                if result == -1:
                    return -1, message

            case "mjpeg":
                transcode_file = file_handler.file_join(
                    transcode_path,
                    file_name,
                    "mkv",  # avi if use MJPEG
                )
                # Set mjpeg argument to true and make the mkv/avi changes above to switch to MJPEG

                result, message = Transcode_Mezzanine(
                    input_file=input_file,
                    output_folder=transcode_path,
                    frame_rate=encoding_info.video_frame_rate,
                    width=encoding_info.video_width,
                    height=encoding_info.video_height,
                    interlaced=(
                        True
                        if encoding_info.video_scan_type.lower() == "interlaced"
                        else False
                    ),
                    bottom_field_first=(
                        True
                        if encoding_info.video_scan_order.lower() == "bff"
                        else False
                    ),
                    black_border=False,
                    encode_10bit=True,
                )

                if result == -1:
                    return -1, message

            case _:  # Stream Copy
                transcode_file = file_handler.file_join(
                    transcode_path,
                    file_name,
                    file_ext,  # Use input_ext here
                )

                commands = [
                    sys_consts.FFMPG,
                    "-fflags",
                    "+genpts",  # generate presentation timestamps
                    "-i",
                    input_file,
                    "-map",
                    "0",
                    "-c",
                    "copy",
                    "-sn",  # Remove titles
                    "-movflags",
                    "+faststart",
                    "-threads",
                    "0",
                    transcode_file,
                ]

                result, message = Execute_Check_Output(
                    commands=commands, stderr_to_stdout=True, debug=debug
                )

                if result == -1:
                    return -1, message

        return 1, transcode_file

    def _transcoder(
        transcode_format: str, video_files: list[str], transcode_path: str
    ) -> tuple[int, str, list[str]]:
        """
        Transcodes a list of video files to a specified format.

        Args:
            transcode_format (str): The desired output format for transcoding. Valid values are:
                                    "dv", "ffv1", "h264", "h265", "mpg", "mjpeg", or "" for stream copy.
            video_files (list[str]): A list of paths to the input video files to be transcoded.
            transcode_path (str): The path to the directory where transcoded files will be stored.

        Returns:
            tuple[int, str, list[str]]:
                - int: 1 if transcoding was successful, -1 if an error occurred.
                - str: An error message if an error occurred (return code -1), or an empty string if successful.
                - list[str]: A list of paths to the transcoded files if successful, or an empty list if an error occurred.
        """
        assert isinstance(video_files, list), (
            f"{video_files} Must be a list of input video files"
        )
        assert all(isinstance(file, str) for file in video_files), (
            "all elements in video_files must be strings"
        )
        assert isinstance(transcode_path, str), f"{transcode_path} Must be a string"

        transcode_file_list = []

        #### transcoder Helper
        def _start_transcode_task(task_def: Task_Def) -> None:
            """
            Handles the start of a transcode task

            Args:
                task_def (Task_Def): Task Definition object

            Returns:

            """

            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if debug:
                print(f"DBG CV T ST Started {task_def.task_id=}")

            return None

        def _finish_transcode_task(task_def: Task_Def) -> None:
            """
            Handles the end of a transcode task

            Args:
                task_def (Task_Def): Task Definition object

            Returns:

            """
            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            # Used in a parent wait loop to determine when all transcoding tasks are done
            nonlocal transcode_file_list
            nonlocal transcode_done
            nonlocal errored

            if debug:
                print(f"DBG CV T FT {task_def.task_id=}")

            task_error_no, task_message, worker_error_no, worker_message = (
                Unpack_Result_Tuple(task_def)
            )

            if task_error_no == 1 and worker_error_no == 1:
                transcode_file_list.append((
                    task_def,
                    worker_message,
                ))  # Worker message has transcoded file name

            if (
                task_error_no == 1
                and worker_error_no == 1
                and task_message.lower() == "all done"
            ):
                if debug:
                    print(f"DBG CV T : (prefix '{task_def.task_prefix}' is complete.")

                transcode_done = True

            elif task_error_no != 1 or worker_error_no != 1:
                if debug:
                    print(f"DBG CV TT Errored! {task_def.task_id=}")

                error_messages.append(
                    f"task {task_def.task_id} reported an error: TaskError={task_error_no}, "
                    f"WorkerError={worker_error_no}, Message='{task_message}'"
                )

                transcode_done = True
                errored = True

            return None

        def _error_task(task_def: Task_Def) -> None:
            """
            Handles the Error task

            Args:
                task_def (Task_Def): Task Definition object

            Returns:

            """

            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if debug:
                print(f"DBG CV T ET {task_def.task_id=}")

            nonlocal transcode_done
            nonlocal errored

            transcode_done = True
            errored = True

            if "message" in task_def.cargo:
                error_messages.append(
                    f"Task '{task_def.task_id} Error {task_def.cargo['message']}"
                )

            return None

        def _abort_task(task_def: Task_Def) -> None:
            """
            Handles the abort task

            Args:
                task_def (Task_Def): Task Definition object

            Returns:
                None

            """
            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if debug:
                print(f"DBG CV T AT {task_def.task_id=}")

            nonlocal transcode_done
            nonlocal errored

            transcode_done = True
            errored = True

            if "message" in task_def.cargo:
                error_messages.append(
                    f"Task '{task_def.task_id} Error {task_def.cargo['message']}"
                )

            return None

        #### transcoder Main
        session_id = Get_Unique_Id()

        transcode_file_list = []

        error_messages = []
        errored = False
        transcode_done = False

        for video_index, video_file in enumerate(video_files):
            encoding_info: Encoding_Details = Get_File_Encoding_Info(video_file)

            if encoding_info.error.strip():
                return (
                    -1,
                    (
                        "Failed To Get Encoding Details :"
                        f" {sys_consts.SDELIM}{video_file}{sys_consts.SDELIM}"
                    ),
                    [],
                )
            else:
                operation = "transcode_video"

                task_def = Task_Def(
                    task_id=f"CT_V_{video_index}_{video_file}_{session_id}",
                    task_prefix=operation,
                    worker_function=_transcode_video,
                    kwargs={
                        "input_file": video_file,
                        "transcode_path": transcode_path,
                        "encoding_info": encoding_info,
                        "transcode_format": transcode_format,
                    },
                    cargo={"index": video_index},
                )

                task_dispatch_name = f"CT_DN_{operation}_{session_id}"

                Task_Dispatcher().submit_task(
                    task_def=task_def,
                    task_dispatch_methods=[
                        {
                            "task_dispatch_name": task_dispatch_name,
                            "callback": "start",
                            "operation": operation,
                            "method": _start_transcode_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": task_dispatch_name,
                            "callback": "finish",
                            "operation": operation,
                            "method": _finish_transcode_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": task_dispatch_name,
                            "callback": "error",
                            "operation": operation,
                            "method": _error_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": task_dispatch_name,
                            "callback": "abort",
                            "operation": operation,
                            "method": _abort_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                    ],
                )

        # Not optimal, but I do not want to change the structure of Concatenate_Videos, so I spawn multiple trancodes and
        # wait for them to complete.
        while not transcode_done and not errored:
            sleep(1)

        if errored:
            error_message = ""

            for error in error_messages:
                error_message += f"{error}\n"

            return -1, error_message, []

        # Return transcoded_file list in the order it was submitted
        return (
            1,
            "",
            [
                item_tuple[1]
                for item_tuple in sorted(
                    transcode_file_list, key=lambda item: item[0].cargo["index"]
                )
            ],
        )

    #### Main
    assert isinstance(video_files, list), (
        f"{video_files} Must be a list of input video files"
    )
    assert all(isinstance(file, str) for file in video_files), (
        f"all elements in {video_files=} must be str"
    )
    assert isinstance(output_file, str), f"{output_file=}. Must be str"
    assert isinstance(audio_codec, str), f"{audio_codec=}. Must be a str"
    assert isinstance(delete_temp_files, bool), f"{delete_temp_files=}. Must be a bool"
    assert isinstance(transcode_format, str) and (
        transcode_format := transcode_format.strip()  # Note assignment
    ) in (
        "",
        "dv",
        "h264",
        "h265",
        "mpg",
        "mjpeg",
        "ffv1",
    ), f"{transcode_format=}. Must be str - dv | h264 | h265 | mpg | mjpeg | ffv1"

    if debug and not utils.Is_Complied():
        print(
            f"DBG CV {video_files=} {output_file=} {audio_codec=} {delete_temp_files}"
        )

    file_handler = file_utils.File()

    out_path, _, container_format = file_handler.split_file_path(output_file)
    transcode_path = file_handler.file_join(out_path, "transcode_temp_files")

    container_format = container_format.replace(".", "")
    file_list_txt = file_handler.file_join(
        out_path, f"video_data_list_{utils.Get_Unique_Id()}", "txt"
    )

    if not file_handler.path_writeable(out_path):
        return -1, f"Can Not Be Write To {out_path}!", ""

    for video_file in video_files:
        if not file_handler.file_exists(video_file):
            return -1, f"File {video_file} Does Not Exist!", ""

    transcode_file_list = []

    if transcode_format:
        if transcode_format == "dv":
            container_format = "avi"
        elif transcode_format in ("h264", "h265"):
            container_format = "mp4"
        elif transcode_format == "mpg":
            container_format = "mpg"
        elif (
            transcode_format == "mjpeg"
        ):  # Note I use H264 instead, but mjpeg is still an option
            container_format = "mkv"  # avi if use MJPEG
        elif transcode_format == "ffv1":
            container_format = "mkv"
        else:
            raise RuntimeError(f"Unknown transcode_concat {transcode_format=}")

        if file_handler.path_exists(transcode_path):
            result, message = file_handler.remove_dir_contents(
                file_path=transcode_path, keep_parent=False
            )

            if result == -1:
                return -1, message, ""

        if file_handler.make_dir(transcode_path) == -1:
            return -1, f"Failed To Create {transcode_path}", ""

        result, message, video_files = _transcoder(
            transcode_format=transcode_format,
            video_files=video_files,
            transcode_path=transcode_path,
        )

        if result == -1:
            return -1, message, ""

    temp_file_list = []
    for file in video_files:
        temp_file_list.append(f"file '{file}'")

    # Generate a file list for ffmpeg
    result, message = file_handler.write_list_to_txt_file(
        str_list=temp_file_list, text_file=file_list_txt
    )

    if result == -1:
        return -1, message, ""

    temp_folder, temp_file, temp_ext = file_handler.split_file_path(output_file)

    if temp_ext.strip(".").lower() in ("mod", "tod"):  # MPG2 Proprietary formats
        output_file = file_handler.file_join(temp_folder, temp_file, "mpg")

    if file_handler.file_exists(output_file):
        result = file_handler.remove_file(output_file)

        if result == -1:
            return -1, f"Failed To Remove File {output_file}", ""

    aac_audio = []

    if audio_codec == "aac":
        aac_audio = ["-bsf:a", "aac_adtstoasc"]

    # Concatenate the video files using ffmpeg
    result, message = Execute_Check_Output(
        commands=[
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            "-f",
            "concat",
            "-safe",
            "0",
            "-auto_convert",
            "1",
            "-threads",
            "0",
            "-i",
            file_list_txt,
            "-c",
            "copy",
        ]
        + aac_audio
        + [
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            output_file,
            "-threads",
            "0",
            "-y",
        ]
    )

    if debug and not utils.Is_Complied():
        print(f"CONCAT {result=} {message=}")

    if result == -1:
        if not debug:
            if file_handler.file_exists(file_list_txt):
                file_handler.remove_file(file_list_txt)
        return -1, message, ""

    # Remove the file list and temp files
    if not debug and file_handler.remove_file(file_list_txt) == -1:
        return -1, f"Failed to delete text file: {file_list_txt}", ""

    if not debug and transcode_file_list:  # always delete these
        result, message = file_handler.remove_dir_contents(
            file_path=transcode_path, keep_parent=False
        )

        if result == -1:
            return (
                -1,
                (
                    "Failed To Delete Transcode Temp Files And/Or Folder :"
                    f" {sys_consts.SDELIM}{transcode_path}{sys_consts.SDELIM}"
                ),
                "",
            )

    return 1, output_file, container_format


def Create_DVD_Iso(input_dir: str, output_file: str) -> tuple[int, str]:
    """
    Create a DVD-Video compliant ISO image file from a directory containing VIDEO_TS and AUDIO_TS directories.

    Args:
        input_dir (str): The path to the input directory containing VIDEO_TS and AUDIO_TS directories.
        output_file (str): The name of the output ISO file.

    Returns:
        tuple[int, str]:
        - arg 1: Status code. Returns 1 if the iso image was created, -1 otherwise.
        - arg 2: "" if ok, otherwise an error message
    """
    assert isinstance(input_dir, str) and input_dir.strip() != "", (
        f"{input_dir}. Must be a non-empty str"
    )
    assert isinstance(output_file, str) and output_file.strip() != "", (
        f"{output_file}. Must be a non-empty str"
    )

    command = [
        sys_consts.GENISOIMAGE,
        # "-dvd-video",
        "-udf",
        "-o",
        output_file,
        "-V",
        "DVD_VIDEO",
        "-volset",
        "DVD_VIDEO",
        "-J",
        "-r",
        "-v",
        "-graft-points",
        f"AUDIO_TS={input_dir}/AUDIO_TS",
        f"VIDEO_TS={input_dir}/VIDEO_TS",
    ]

    return Execute_Check_Output(command)


def Create_DVD_Case_Insert(
    title: str,
    menu_pages: list[DVD_Menu_Page],
    insert_width=120,  # 130 # Standard DVD case insert width in millimeters (One side)
    insert_height=120,  # 184 # Standard DVD case insert height in millimeters (One side)
    insert_colour="white",
    resolution=300,  # Standard resolution for print quality
    title_font_path: str = "",
    title_font_colour: str = "black",
    title_font_size: int = 48,
    menu_font_size=24,
    menu_font_path="",
    menu_font_colour="black",
    opacity: float = 1.0,
    debug: bool = False,
) -> tuple[int, bytes]:
    """
    Creates a DVD case insert image with DVD title, menu titles, and using ImageMagick.

    Args:
        title (str): Title of the DVD.
        menu_pages (list[DVD_Menu_Page]): List of menu pages to be displayed on the insert.
        insert_width (int): Width of the DVD case insert.
        insert_height (int): Height of the DVD case insert.
        insert_colour (str): Background colour of the insert.
        resolution (int): Resolution of the image.
        title_font_colour (str): Colour of the title text.
        title_font_size (int): Font size of the title.
        title_font_path (str): Path to the title font file.
        menu_font_size (int): Font size.
        menu_font_path (str): Path to the font file.
        menu_font_colour (str): Color of the text.
        opacity (float): The opacity level to be set for the color,
                        where 0.0 is fully transparent and 1.0 is fully opaque.
        debug (bool): Whether to print debug messages.

    Returns:
        - arg 1 : Status code. Returns 1 if the iso image was created, -1 otherwise.
        - arg 2 : bytes: The generated DVD case insert image data.
    """
    assert isinstance(title, str) and title.strip() != "", (
        f"{title=}. Must be a non-empty str"
    )
    assert isinstance(menu_pages, list) and len(menu_pages) > 0, (
        f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    )
    assert all(isinstance(page, DVD_Menu_Page) for page in menu_pages), (
        f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    )
    assert isinstance(insert_width, int) and insert_width > 0, (
        f"{insert_width=}. Must be an int >"
    )
    assert isinstance(insert_height, int) and insert_height > 0, (
        f"{insert_height=}. Must be an int > 0"
    )
    assert isinstance(resolution, int) and resolution > 0, (
        f"{resolution=}. Must be an int > 0"
    )
    assert isinstance(menu_font_size, int) and menu_font_size > 0, (
        f"{menu_font_size=}. Must be an int > 0"
    )
    assert isinstance(menu_font_path, str) and menu_font_path.strip() != "", (
        f"{menu_font_path=}. Must be a non-empty str"
    )
    assert isinstance(insert_colour, str) and insert_colour.strip() != "", (
        f"{insert_colour=}. Must be a non-empty str"
    )
    assert isinstance(menu_font_colour, str) and menu_font_colour.strip() != "", (
        f"{menu_font_colour=}. Must be a non-empty str"
    )

    assert isinstance(opacity, float) and 0.0 <= opacity <= 1.0, (
        f"{opacity=}. Must be a float between 0.0 and 1.0"
    )
    assert isinstance(debug, bool), f"{debug=}. Must be a bool"

    #### Helper
    def _get_label_text(
        background_canvas_width: int,
        menu_font_path: str,
        menu_font_size: int,
        menu_pages: list[DVD_Menu_Page],
    ) -> tuple[list[str], int]:
        """
        Generates the text content for the DVD label, including menu titles and button titles, with wrapping.

        This function prepares the text content to be written on the DVD label image, handling text wrapping
        to ensure it fits within the specified label area. It processes menu titles and button titles from
        the provided menu pages, formatting them appropriately for display.

        Args:
            background_canvas_width (float): The width of the background  where the text will be placed, in pixels.
            menu_font_path (str): The path to the font file used for rendering the menu and button text.
            menu_font_size (int): The font size, in points, used for rendering the menu and button text.
            menu_pages (list[DVD_Menu_Page]): A list of DVD_Menu_Page objects, each representing a menu page.
                Each DVD_Menu_Page object should contain a 'menu_title' attribute (str) and a
                'get_button_titles' attribute (which returns a dictionary of button titles).

        Returns:
            tuple[List[str], int]: A tuple containing:
                - A list of strings, where each string represents a line of text to be written on the label.
                - The maximum width of the text column, in pixels.
        """

        assert (
            isinstance(background_canvas_width, int) and background_canvas_width > 0
        ), f"{background_canvas_width=} must > 0"
        assert isinstance(menu_font_path, str), f"{menu_font_path=} must be a string."
        assert isinstance(menu_font_size, int) and menu_font_size > 0, (
            f"{menu_font_size=} must be > 0."
        )
        assert isinstance(menu_pages, list) and all(
            isinstance(page, DVD_Menu_Page) for page in menu_pages
        ), "menu_pages must be a list of DVD_Menu_Page objects "

        dvd_text = []
        max_text_column_width = (background_canvas_width // 2) - 20  # Padding
        max_char_width = int(max_text_column_width // menu_char_width)

        for menu_index, menu_title in enumerate(menu_pages):
            if menu_title.menu_title.strip():
                menu_title_text = f"* {menu_title.menu_title}"
            else:
                menu_title_text = f"* Menu {menu_index + 1}"

            wrapped_text = textwrap.wrap(
                menu_title_text,
                width=max_char_width,
                subsequent_indent="    ",
            )

            for line_index, menu_line in enumerate(wrapped_text):
                dvd_text.append(
                    f"{menu_line}" if line_index == 0 else rf"\ {menu_line}"
                )

            for button_item in menu_title.get_button_titles.values():
                button_title = rf"\  - {button_item[0]}"  # Button titles are indented 4 spaces (\ required!)

                width, _ = Get_Text_Dims(
                    text=f"{button_title}",
                    font=menu_font_path,
                    pointsize=menu_font_size,
                )

                if width > max_text_column_width:
                    wrapped_text = textwrap.wrap(
                        button_title,
                        width=max_char_width,
                        subsequent_indent="    ",
                    )

                    for line_index, button_line in enumerate(wrapped_text):
                        dvd_text.append(
                            f"{button_line}" if line_index == 0 else rf"\ {button_line}"
                        )

                else:
                    dvd_text.append(f"{button_title}")

            dvd_text.append(" ")
        dvd_text.pop(len(dvd_text) - 1)  # Remove the last blank line

        return dvd_text, max_text_column_width

    def _get_background_insert_image(
        background_canvas_width: int,
        background_canvas_height: int,
        insert_colour: str,
        opacity: float,
    ) -> tuple[int, bytes]:
        """
        Generates a PNG image with a solid color background, intended for use as a DVD insert.

        Args:
            background_canvas_width (int): The width of the image canvas in pixels.
            background_canvas_height (int): The height of the image canvas in pixels.
            insert_colour (str): The color of the background.  Must be a valid ImageMagick color string.
            opacity (float): The opacity level of the color, where 0.0 is fully transparent and 1.0 is fully opaque.

        Returns:
            Tuple[int, bytes]: A tuple containing the status code and the image data.
                - int: 1 if the image was generated successfully, -1 otherwise.
                - bytes: The generated PNG image data as a byte string, or an error message as a byte encoded string if an error occurred.
        """
        assert (
            isinstance(background_canvas_width, int) and background_canvas_width > 0
        ), "background_canvas_width must be a positive integer."
        assert (
            isinstance(background_canvas_height, int) and background_canvas_height > 0
        ), "background_canvas_height must be a positive integer."
        assert isinstance(insert_colour, str), "insert_colour must be a string."
        assert isinstance(opacity, float) and 0 <= opacity <= 1, (
            "opacity must be a float between 0.0 and 1.0"
        )

        result, insert_hex = Make_Opaque(color=insert_colour, opacity=opacity)

        if result == -1:
            return -1, f"Invalid System Color {insert_colour}".encode("utf-8")

        command = [
            sys_consts.CONVERT,
            "-size",
            f"{background_canvas_width}x{background_canvas_height}",
            "xc:none",
            "-fill",
            insert_hex,
            "-draw",
            f"'rectangle' 0,0 {background_canvas_width},{background_canvas_height}'",
            "PNG:-",  # Output to standard output (pipe)
        ]

        try:
            image_data = subprocess.check_output(command, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            return -1, f"Error Generating DVD Insert Image - {e}".encode("utf-8")

        return 1, image_data

    def _write_title_on_background(
        image_data: bytes,
        background_canvas_width: int,
        title: str,
        title_char_width: int,
        title_font_path: str,
        title_font_size: int,
        title_font_colour: str,
        left_y1: int,
        max_title_lines: int,
    ) -> tuple[int, bytes, int]:
        """
        Writes a title onto a given image background, handling text wrapping and manual spacing.

        This function takes image data, title information, and font settings to write a title onto the image.
        It supports both automatic and manual title wrapping using '|' as a manual line break delimiter.
        Only 4 lines are allowed.

        Args:
            image_data (bytes): The image data in bytes format.
            background_canvas_width (int): The width of the image canvas in pixels.
            title (str): The title text to write onto the image.
            title_char_width (int): The width of a single character in the title font.
            title_font_path (str): The path to the font file used for the title.
            title_font_size (int): The font size for the title in points.
            title_font_colour (str): The color of the title text.
            left_y1 (int): The starting y-coordinate for the title text.
            max_title_lines (int): The maximum number of title lines allowed.

        Returns:
            tuple[int, bytes]: A tuple containing the status code and the modified image data.
                - int: 1 if the title was written successfully, -1 otherwise.
                - bytes: The modified image data in bytes, or an error message as a byte encoded string if an error occurred.
                - int: The title height
        """
        assert isinstance(image_data, bytes), "image_data must be bytes."
        assert (
            isinstance(background_canvas_width, int) and background_canvas_width > 0
        ), "background_canvas_width must be a positive integer."
        assert isinstance(title, str), "title must be a string."
        assert isinstance(title_char_width, int) and title_char_width > 0, (
            "title_char_width must be a positive integer."
        )
        assert isinstance(title_font_path, str), "title_font_path must be a string."
        assert isinstance(title_font_size, int) and title_font_size > 0, (
            "title_font_size must be a positive integer."
        )
        assert isinstance(title_font_colour, str), "title_font_colour must be a string."
        assert isinstance(left_y1, int), "left_y1 must be an integer."
        assert isinstance(max_title_lines, int) and max_title_lines > 0, (
            "max_title_lines must be a positive integer."
        )

        # Write title
        if "|" in title:  # Manual spacing of title text
            title_wrapped_text = []
            temp_wrapped_text = title.split("|")

            max_title_length = 0
            max_title_text = ""
            for line in temp_wrapped_text:
                if len(line) > max_title_length:
                    max_title_length = len(line)
                    max_title_text = line

            _, title_height = Get_Text_Dims(
                text=max_title_text, font=title_font_path, pointsize=title_font_size
            )

            for title_text in temp_wrapped_text:
                title_wrapped_text += textwrap.wrap(
                    text=title_text,
                    width=round((background_canvas_width - 40) // title_char_width),
                    subsequent_indent="    ",
                )

        else:  # Automatic spacing of the title text
            _, title_height = Get_Text_Dims(
                text=title, font=title_font_path, pointsize=title_font_size
            )

            title_wrapped_text = textwrap.wrap(
                text=title,
                width=round((background_canvas_width - 40) // title_char_width),
                subsequent_indent="    ",
            )

        if len(title_wrapped_text) > 4:
            return (
                -1,
                f"Menu Title Is {len(title_wrapped_text)} Lines Long And Only {max_title_lines} Are Allowed! Reduce "
                f"Title Font Size Or Change Title Font".encode("utf-8"),
                -1,
            )

        for line_num, title_line in enumerate(title_wrapped_text):
            result, image_data = Write_Text_On_Image(
                image_data=image_data,
                text=title_line,
                x=20,
                y=left_y1 + (line_num * title_char_height),
                color=title_font_colour,
                font=title_font_path,
                pointsize=title_font_size,
                gravity="north",
            )

            if result == -1:  # Image data will contain the error message in this case
                return -1, image_data.encode("utf-8"), -1

        return 1, image_data, title_height

    def _write_menu_titles(
        image_data: bytes,
        dvd_text: list[str],
        left_x1: int,
        left_y1: int,
        left_y2: int,
        right_x1: int,
        menu_char_height: int,
        menu_font_colour: str,
        menu_font_path: str,
        menu_font_size: int,
        MAX_TITLE_LINES: int,
        title_height: int,
    ) -> tuple[int, bytes]:
        """
        Writes menu titles onto a given image, handling line wrapping and side switching.

        This function iterates through the provided DVD text lines, writing them onto the image at specified
        positions. It handles switching between left and right sides of the image if the text exceeds
        the left side's boundary.

        Args:
            image_data (bytes): The image data in bytes format.
            dvd_text (List[str]): A list of strings, each representing a line of text to write.
            left_x1 (int): The starting x-coordinate for the left side text.
            left_y1 (int): The starting y-coordinate for the text.
            left_y2 (int): The maximum y-coordinate for the left side text.
            right_x1 (int): The starting x-coordinate for the right side text.
            menu_char_height (int): The height of a single character in the menu font.
            menu_font_colour (str): The color of the menu text.
            menu_font_path (str): The path to the font file used for the menu text.
            menu_font_size (int): The font size for the menu text in points.
            MAX_TITLE_LINES (int): The maximum number of title lines allowed per side.
            title_height (int): The height of the title text.

        Returns:
            tuple[int, bytes]: A tuple containing the status code and the modified image data.
                - int: 1 if the titles were written successfully, -1 otherwise.
                - bytes: The modified image data in bytes, or an error message as a byte encoded string if an error occurred.
        """
        assert isinstance(image_data, bytes), f"{image_data=} must be bytes."
        assert isinstance(dvd_text, list) and all(
            isinstance(line, str) for line in dvd_text
        ), "dvd_text must be a list of strings."
        assert isinstance(left_x1, int), f"{left_x1=} must be an integer."
        assert isinstance(left_y1, int), f"{left_y1=} must be an integer."
        assert isinstance(left_y2, int), f"{left_y2=} must be an integer."
        assert isinstance(right_x1, int), f"{right_x1=} must be an integer."
        assert isinstance(menu_char_height, int), (
            f"{menu_char_height=} must be an integer."
        )
        assert isinstance(menu_font_colour, str), (
            f"{menu_font_colour=} must be a string."
        )
        assert isinstance(menu_font_path, str), f"{menu_font_path=} must be a string."
        assert isinstance(menu_font_size, int), f"{menu_font_size=} must be an integer."
        assert isinstance(MAX_TITLE_LINES, int), (
            f"{MAX_TITLE_LINES=} must be an integer."
        )
        assert isinstance(title_height, int), f"{title_height=} must be an integer."

        line_num = 0
        side = 0
        x_offset = left_x1
        left_y1 = left_y1 + ((MAX_TITLE_LINES + 1) * title_height) + 20  # Padding

        for line in dvd_text:
            y_position = left_y1 + (line_num * menu_char_height)

            if y_position > left_y2:  # Switch to right side
                side += 1
                if side > 2:
                    return (
                        -1,
                        "Too Many Menu Titles To Print! Reduce Menu Font Size Or Change Font".encode(
                            "utf-8"
                        ),
                    )

                line_num = 0
                x_offset = right_x1
                if line.strip() == "":
                    continue

                y_position = left_y1 + (line_num * menu_char_height)

            result, image_data = Write_Text_On_Image(
                image_data=image_data,
                text=line,
                x=x_offset,
                y=y_position,
                color=menu_font_colour,
                font=menu_font_path,
                pointsize=menu_font_size,
            )

            if result == -1:  # Image data will contain the error message in this case
                return -1, image_data.encode("utf-8")

            line_num += 1

        return 1, image_data

    #### Main
    MAX_TITLE_LINES: Final[int] = 4

    if menu_font_path.strip() == "":
        fonts = Get_Fonts()
        for font in fonts:
            if font[0].lower().startswith("ubuntu"):
                menu_font_path = font[1]
                break
        else:
            return -1, b"A Default Menu Font Could Not Be Found "

    # Check if font file exists
    if not os.path.exists(menu_font_path):
        return -1, b""

    dpmm = resolution / 25.4  # Convert DPI to DPMM

    background_canvas_width = round(insert_width * dpmm)
    background_canvas_height = round(insert_height * dpmm)

    left_y1 = 50  # Padding
    left_y2 = background_canvas_height - 20  # Padding

    left_y2 = left_y1 + left_y2
    left_x1 = 50  # Padding

    title_char_width, title_char_height = Get_Text_Dims(
        text="W", font=title_font_path, pointsize=title_font_size
    )  # In English at least and in most fonts W is the widest

    menu_char_width, menu_char_height = Get_Text_Dims(
        text="W", font=menu_font_path, pointsize=menu_font_size
    )  # In English at least and in most fonts W is the widest

    dvd_text, max_text_column_width = _get_label_text(
        background_canvas_width,
        menu_font_path,
        menu_font_size,
        menu_pages,
    )

    # left_x2 = max_text_column_width - 20 # Padding
    right_x1 = max_text_column_width + 20  # Padding
    right_x1 = right_x1 + max_text_column_width - 20  # Padding

    result, image_data = _get_background_insert_image(
        background_canvas_height, background_canvas_width, insert_colour, opacity
    )

    if result == -1:
        return -1, image_data

    result, image_data, title_height = _write_title_on_background(
        image_data,
        background_canvas_width,
        title,
        title_char_width,
        title_font_path,
        title_font_size,
        title_font_colour,
        left_y1,
        MAX_TITLE_LINES,
    )

    if result == -1:  # Image data will contain the error message in this case
        return -1, image_data

    result, image_data = _write_menu_titles(
        image_data,
        dvd_text,
        left_x1,
        left_y1,
        left_y2,
        right_x1,
        menu_char_height,
        menu_font_colour,
        menu_font_path,
        menu_font_size,
        MAX_TITLE_LINES,
        title_height,
    )

    if result == -1:  # Image data will contain the error message in this case
        return -1, image_data

    if debug and not utils.Is_Complied():
        with open("cddvd_insert.png", "wb") as png_file:
            png_file.write(image_data)

    return 1, image_data


def Create_DVD_Label(
    title: str,
    menu_pages: list[DVD_Menu_Page],
    disk_diameter: float = 115.0,  # 120mm standard, make DVD label a little smaller
    disk_colour: str = "white",
    resolution: int = 300,  # Standard resolution for print quality
    title_font_path: str = "",
    title_font_colour: str = "black",
    title_font_size: int = 48,
    menu_font_path: str = "",
    menu_font_colour: str = "black",
    menu_font_size: int = 24,
    spindle_diameter: float = 36,  # 15mm standard make a little larger (Verbatim guide 36)
    opacity: float = 1.0,
    debug: bool = True,
) -> tuple[int, bytes]:
    """
    Creates a DVD label image with menu titles and a central hole.
    Note:
        - The title can be manually split into separate lines using the | character placed where line breaks are required
        - There is a maximum of four lines in a title, more than that generates an error
        - Text is auto-wrapped to fit within the label and a manually split label may exceed the four lines allowed


    Args:
        title (str): Title of the DVD.
        menu_pages (list[DVD_Menu_Page]): List of menu pages.
        disk_diameter (float): Diameter of the DVD label.
        disk_colour (str): Colour of the DVD label.
        resolution (int): Resolution of the image.
        title_font_colour (str): Colour of the title text.
        title_font_size (int): Font size of the title.
        title_font_path (str): Path to the title font file.
        menu_font_colour (str): Colour of the menu text.
        menu_font_size (int): Font size.
        menu_font_path (str): Path to the menu font file.
        spindle_diameter (float): diameter of the central hole.
        opacity (float): The opacity level to be set for the color,
                        where 0.0 is fully transparent and 1.0 is fully opaque.
        debug (bool): If True, debug information will be printed.

    Returns:
        tuple[int, bytes]
        - arg 1 : Status code. Returns 1 if the png image was created, -1 otherwise.
        - arg 2 : bytes: The generated DVD label image data as a PNG byte  string.
    """

    assert isinstance(title, str), f"{title=}. Must be a str"
    assert isinstance(menu_pages, list) and len(menu_pages) > 0, (
        f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    )
    assert all(isinstance(page, DVD_Menu_Page) for page in menu_pages), (
        f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    )
    assert isinstance(disk_diameter, (int, float)) and disk_diameter > 0, (
        f"{disk_diameter=}. Must be a float > 0"
    )
    assert isinstance(resolution, int) and resolution > 0, (
        f"{resolution=}. Must be an int > 0"
    )
    assert isinstance(title_font_colour, str) and title_font_colour.strip() != "", (
        f"{title_font_colour=}. Must be a non-empty str"
    )
    assert isinstance(title_font_size, int) and title_font_size > 0, (
        f"{title_font_size=}. Must be an int > 0"
    )
    assert isinstance(menu_font_colour, str) and menu_font_colour.strip() != "", (
        f"{menu_font_colour=}. Must be a non-empty str"
    )
    assert isinstance(menu_font_size, int) and menu_font_size > 0, (
        f"{menu_font_size=}. Must be an int > 0"
    )
    assert isinstance(title_font_path, str), f"{title_font_path=}. Must be a str"
    assert isinstance(menu_font_path, str), f"{menu_font_path=}. Must be a str"
    assert (
        isinstance(spindle_diameter, (int, float)) and 21 <= spindle_diameter <= 45
    ), f"{spindle_diameter=}. Must be a float >= 21 and <= 45"
    assert isinstance(opacity, float) and 0.0 <= opacity <= 1.0, (
        f"{opacity=}. Must be a float between 0.0 and 1.0"
    )

    assert isinstance(disk_colour, str) and disk_colour.upper() in Color.__members__, (
        f"{disk_colour=}. Must be one of {[member.name for member in Color]}"
    )

    assert (
        isinstance(title_font_colour, str)
        and title_font_colour.upper() in Color.__members__
    ), f"{title_font_colour=}. Must be one of {[member.name for member in Color]}"

    assert (
        isinstance(menu_font_colour, str)
        and menu_font_colour.upper() in Color.__members__
    ), f"{menu_font_colour=}. Must be one of {[member.name for member in Color]}"

    assert isinstance(debug, bool), f"{debug=}. Must be a bool"

    #### Helper functions
    def _get_default_font() -> tuple[int, str]:
        """Gets a default font file path

        Returns:
            tuple[int, str]
            - arg 1 : Status code. Returns 1 if the font was found, -1 otherwise.
            - arg 2 : str: The font path or an error message if not found

        """
        fonts = Get_Fonts()

        for font in fonts:
            if font[0].lower().startswith("ubuntu") or "arial" in font[0].lower():
                return 1, font[1]
        else:
            return -1, "A Default Font Could Not Be Found "

    def _get_label_image(
        background_canvas_width: int,
        background_canvas_height: int,
        label_x: float,
        label_y: float,
        disk_radius: float,
        spindle_radius: float,
    ) -> tuple[int, bytes]:
        """Generates the DVD label image

        Args:
            background_canvas_width (int): width of the background canvas
            background_canvas_height (int): height of the background canvas
            label_x (float): x position of the label
            label_y (float): y position of the label
            disk_radius (float): radius of the disk
            spindle_radius (float): radius of the spindle

        Returns:
            tuple[int, bytes]
            - arg 1 : Status code. Returns 1 if the png image was created, -1 otherwise.
            - arg 2 : bytes: The generated DVD label image data as a PNG byte  string or the error message if not created.
        """
        result, disk_hex = Make_Opaque(color=disk_colour, opacity=opacity)

        if result == -1:
            return -1, f"Invalid System Color {disk_colour}".encode("utf-8")

        # Generate the background CD/DVD label image
        command = [
            sys_consts.CONVERT,
            "-size",
            f"{background_canvas_width}x{background_canvas_height}",
            "xc:none",
            "-fill",
            disk_hex,
            "-draw",
            f"'circle' {label_x - 0.5},{label_y - 0.5} {disk_radius - 0.5},{0}'",
            "(",
            "-size",
            f"{background_canvas_width}x{background_canvas_height}",
            "xc:none",
            "-fill",
            "black",
            "-draw",
            f"'circle' {label_x},{label_y} {label_x + spindle_radius},{label_y + spindle_radius}'",
            ")",
            "-alpha",
            "Set",
            "-compose",
            "Dst_Out",
            "-composite",
            "PNG:-",  # Output to standard output (pipe)
        ]
        try:
            image_data = subprocess.check_output(command, stderr=subprocess.DEVNULL)

        except subprocess.CalledProcessError:
            return -1, "Error Generating DVD Label Image".encode("utf-8")

        return 1, image_data

    def _get_label_text(
        label_square_width: int,
        menu_font_path: str,
        menu_font_size: int,
        menu_pages: list[DVD_Menu_Page],
    ) -> tuple[list[str], int]:
        """Generates the DVD label text

        Args:
            label_square_width (int): width of the label square
            menu_font_path (str): path to the font file
            menu_font_size (int): font size
            menu_pages (list[DVD_Menu_Page]): list of menu pages

        Returns:
            tuple[list[str],int]
            - arg 1 : list of text lines
            - arg 2 : int: The number of lines
        """
        assert isinstance(label_square_width, int) and label_square_width > 0, (
            f"{label_square_width=}. Must > 0"
        )
        assert isinstance(menu_font_path, str) and menu_font_path.strip() != "", (
            f"{menu_font_path=}. Must be a non-empty str"
        )
        assert isinstance(menu_font_size, int) and menu_font_size > 0, (
            f"{menu_font_size=}. Must be > 0"
        )
        assert isinstance(menu_pages, list), f"{menu_pages=}. Must be a list"

        for menu_page in menu_pages:
            assert isinstance(menu_page, DVD_Menu_Page), (
                f"{menu_page=}. Must be a DVD_Menu_Page"
            )

        # Extract text to place on the DVD image
        dvd_text = []

        menu_char_width, menu_char_height = Get_Text_Dims(
            text="W", font=menu_font_path, pointsize=menu_font_size
        )  # In English at least and in most fonts W is the widest

        for menu_index, menu_title in enumerate(menu_pages):
            if menu_title.menu_title.strip():
                menu_text = f"* {menu_title.menu_title}"
            else:
                menu_text = f"* Menu {menu_index + 1}"

            wrapped_text = textwrap.wrap(
                menu_text,
                width=label_square_width // menu_char_width,
                subsequent_indent="    ",
            )

            # leading \ is required for menu line!
            for line_index, menu_line in enumerate(wrapped_text):
                dvd_text.append(menu_line if line_index == 0 else rf"\ {menu_line}")

            # menu button title text is indented 4 spaces and leading \ is required!
            for button_item in menu_title.get_button_titles.values():
                button_title = rf"\  - {button_item[0]}"

                wrapped_text = textwrap.wrap(
                    button_title,
                    width=label_square_width // menu_char_width,
                    subsequent_indent="    ",
                )

                # leading \ is required for button line!
                for line_index, button_line in enumerate(wrapped_text):
                    dvd_text.append(
                        f"{button_line}" if line_index == 0 else rf"\ {button_line}"
                    )

            dvd_text.append(" ")

        dvd_text.pop(len(dvd_text) - 1)  # Remove the last blank line

        return dvd_text, menu_char_height

    def _write_label_title(
        image_data: bytes,
        title: str,
        title_font_path: str,
        title_font_size: int,
        label_x: int,
        left_sq_y1: int,
        disk_square_size: int,
        left_sq_x1: int,
        title_font_colour: str,
    ) -> tuple[int, bytes]:
        """
        Writes the DVD label title onto the provided image data.

        Args:
            image_data (bytes): The image data to write the title onto.
            title (str): The title text.
            title_font_path (str): The path to the title font file.
            title_font_size (int): The font size of the title.
            label_x (int): The x-coordinate of the label's center.
            left_sq_y1 (int): The y-coordinate of the top edge of the left square.
            disk_square_size (int): The size of the square that fits within the DVD label circle.
            left_sq_x1 (int): The x-coordinate of the left side of the left square.
            title_font_colour (str): The colour of the title text.

        Returns:
            tuple[int, bytes]: A tuple containing the status code and the modified image data.
                - int: 1 if successful, -1 if an error occurred.
                - bytes: The modified image data with the title written on it, or an error message as byte encoded string
                if an error occurred.
        """

        assert isinstance(image_data, bytes), "image_data must be bytes."
        assert isinstance(title, str), "title must be a string."
        assert isinstance(title_font_path, str), "title_font_path must be a string."
        assert isinstance(title_font_size, int) and title_font_size > 0, (
            "title_font_size must be a positive integer."
        )
        assert isinstance(label_x, int), "label_x must be an integer."
        assert isinstance(left_sq_y1, int), "left_sq_y1 must be an integer."
        assert isinstance(disk_square_size, int), "disk_square_size must be an integer."
        assert isinstance(left_sq_x1, int), "left_sq_x1 must be an integer."
        assert isinstance(title_font_colour, str), "title_font_colour must be a string."

        MAX_TITLE_LINES: Final[int] = 4

        title_char_width, title_char_height = Get_Text_Dims(
            text="W", font=title_font_path, pointsize=title_font_size
        )

        title_px_width = math.sqrt(
            (left_sq_x1 - (disk_square_size * 2)) ** 2
            + (left_sq_y1 - (left_sq_y1 - MAX_TITLE_LINES * title_char_height)) ** 2
        )  # Pythagoras is your friend

        if "|" in title:  # Manual spacing of title text
            title_wrapped_text = []
            temp_wrapped_text = title.split("|")

            max_title_length = 0
            max_title_text = ""
            for line in temp_wrapped_text:
                if len(line) > max_title_length:
                    max_title_length = len(line)
                    max_title_text = line

            _, title_height = Get_Text_Dims(
                text=max_title_text, font=title_font_path, pointsize=title_font_size
            )

            for title_text in temp_wrapped_text:
                title_wrapped_text += textwrap.wrap(
                    text=title_text,
                    width=round((title_px_width // 2 - 50) // title_char_width),
                    subsequent_indent="    ",
                )

        else:  # Automatic spacing of the title text
            _, title_height = Get_Text_Dims(
                text=title, font=title_font_path, pointsize=title_font_size
            )

            title_wrapped_text = textwrap.wrap(
                text=title,
                width=round((title_px_width // 2 - 50) // title_char_width),
                subsequent_indent="    ",
            )

        if len(title_wrapped_text) > 4:
            return (
                -1,
                f"Menu Title Is {len(title_wrapped_text)} Lines Long And Only {MAX_TITLE_LINES} Are Allowed! Reduce "
                f"Title Font Size Or Change Title Font".encode("utf-8"),
            )

        for line_num, title_line in enumerate(title_wrapped_text):
            result, image_data = Write_Text_On_Image(
                image_data=image_data,
                text=title_line,
                x=round(title_px_width // label_x),
                y=left_sq_y1
                - ((MAX_TITLE_LINES + 1) * title_height)
                + (line_num * title_char_height),
                color=title_font_colour,
                font=title_font_path,
                pointsize=title_font_size,
                gravity="north",
            )

            if result == -1:  # Image data will contain the error message in this case
                return -1, image_data.decode("utf-8")

        return 1, image_data

    def _write_label_text(
        image_data: bytes,
        dvd_text: list[str],
        menu_font_path: str,
        menu_font_size: int,
        menu_font_colour: str,
        x_offset: int,
        left_sq_y1: int,
        left_sq_y2: int,
        left_sq_x1: int,
        right_sq_x1: int,
        menu_char_height: int,
    ) -> tuple[int, bytes]:
        """
        Writes the menu and button text onto the DVD label image.

        Args:
            image_data (bytes): The image data to write the text onto.
            dvd_text (list[str]): A list of strings containing the menu and button text.
            menu_font_path (str): The path to the menu font file.
            menu_font_size (int): The font size of the menu text.
            menu_font_colour (str): The colour of the menu text.
            x_offset (int): The x-coordinate offset for the menu text.
            left_sq_y1 (int): The y-coordinate of the top edge of the left square.
            left_sq_y2 (int): The y-coordinate of the bottom edge of the left square.
            left_sq_x1 (int): The x-coordinate of the left side of the left square.
            right_sq_x1 (int): The x-coordinate of the left side of the right square.
            menu_char_height (int): The height of a single character in the menu font.

        Returns:
            tuple[int, bytes]: A tuple containing the status code and the modified image data.
                - int: 1 if successful, -1 if an error occurred.
                - bytes: The modified image data with the menu text written on it, or an error message as byte encoded string if an error occurred.
        """

        assert isinstance(image_data, bytes), "image_data must be bytes."
        assert isinstance(dvd_text, list) and all(
            isinstance(line, str) for line in dvd_text
        ), "dvd_text must be a list of strings."
        assert isinstance(menu_font_path, str), "menu_font_path must be a string."
        assert isinstance(menu_font_size, int) and menu_font_size > 0, (
            "menu_font_size must be a positive integer."
        )
        assert isinstance(menu_font_colour, str), "menu_font_colour must be a string."
        assert isinstance(left_sq_y1, int), "left_sq_y1 must be an integer."
        assert isinstance(left_sq_y2, int), "left_sq_y2 must be an integer."
        assert isinstance(left_sq_x1, int), "left_sq_x1 must be an integer."
        assert isinstance(right_sq_x1, int), "right_sq_x1 must be an integer."
        assert isinstance(menu_char_height, int), "menu_char_height must be an integer."

        # Now write the menu and button text on the DVD image
        line_num = 0
        side = 1

        for line in dvd_text:
            y_position = left_sq_y1 + (line_num * menu_char_height)

            if y_position > left_sq_y2:  # Switch to right side
                side += 1
                if side > 2:
                    return (
                        -1,
                        "Too Many Menu Titles To Print! Reduce Menu Font Size Or Change Font".encode(
                            "utf-8"
                        ),
                    )

                line_num = 0
                x_offset = right_sq_x1

                if line.strip() == "":
                    continue

                y_position = left_sq_y1 + (line_num * menu_char_height)

            result, image_data = Write_Text_On_Image(
                image_data=image_data,
                text=line,
                x=x_offset,
                y=y_position,
                color=menu_font_colour,
                font=menu_font_path,
                pointsize=menu_font_size,
            )

            if result == -1:  # Image data will contain the error message in this case
                return -1, image_data.decode("utf-8")

            line_num += 1

        return 1, image_data

    #### Main
    LABEL_HORIZONTAL_PADDING: Final[int] = 25
    LEFT_SQUARE_X_OFFSET: Final[int] = 80
    SQUARE_ROOT_OF_2: Final[float] = math.sqrt(2)

    if title_font_path.strip() == "":
        result, title_font_path = _get_default_font()
        if result == -1:
            return -1, title_font_path.encode("utf-8")

    if menu_font_path.strip() == "":
        result, menu_font_path = _get_default_font()
        if result == -1:
            return -1, menu_font_path.encode("utf-8")

    if not os.path.exists(title_font_path):
        return -1, f"Title Font file not found: {menu_font_path}".encode("utf-8")

    if not os.path.exists(menu_font_path):
        return -1, f"Menu Font file not found: {menu_font_path}".encode("utf-8")

    # Calculate the required variables
    dpmm = resolution / 25.4

    disk_diameter = round(disk_diameter * dpmm)
    spindle_diameter = round(spindle_diameter * dpmm)

    disk_radius = disk_diameter // 2
    spindle_radius = spindle_diameter // 2
    background_canvas_width = disk_diameter
    background_canvas_height = disk_diameter
    label_x = background_canvas_width // 2
    label_y = background_canvas_height // 2

    disk_square_size = round(disk_radius * SQUARE_ROOT_OF_2)
    spindle_square_size = round(spindle_radius * SQUARE_ROOT_OF_2)
    label_square_width = (
        disk_square_size // 2 - spindle_square_size // 2 - LABEL_HORIZONTAL_PADDING
    )

    left_sq_x1 = LEFT_SQUARE_X_OFFSET
    right_sq_x1 = label_x + spindle_square_size + LABEL_HORIZONTAL_PADDING
    left_sq_y1 = background_canvas_height - disk_square_size
    left_sq_y2 = disk_square_size

    x_offset = left_sq_x1

    # Get the label image for the DVD
    result, image_data = _get_label_image(
        background_canvas_width,
        background_canvas_height,
        label_x,
        label_y,
        disk_radius,
        spindle_radius,
    )
    if result == -1:
        return -1, image_data

    # Get the text for the DVD label
    dvd_text, menu_char_height = _get_label_text(
        label_square_width, menu_font_path, menu_font_size, menu_pages
    )

    if title:  # Write the label title text on the DVD label
        result, image_data = _write_label_title(
            image_data,
            title,
            title_font_path,
            title_font_size,
            label_x,
            left_sq_y1,
            disk_square_size,
            left_sq_x1,
            title_font_colour,
        )

        if result == -1:
            return -1, image_data

    # Write the menu text on the DVD label
    result, image_data = _write_label_text(
        image_data,
        dvd_text,
        menu_font_path,
        menu_font_size,
        menu_font_colour,
        x_offset,
        left_sq_y1,
        left_sq_y2,
        left_sq_x1,
        right_sq_x1,
        menu_char_height,
    )

    if result == -1:
        return -1, image_data

    if debug and not utils.Is_Complied():
        with open("cddvd_label.png", "wb") as png_file:
            png_file.write(image_data)

    return 1, image_data


def Get_Space_Available(path: str) -> tuple[int, str]:
    """
    Returns the amount of available disk space in bytes for the specified file system path.

    Args:
        path (str): A string representing the file system path for which the available disk space is to be determined.

    Returns:
        tuple[int, str]:
        - arg 1 : A tuple containing the available disk space in bytes
            The status code is:
            -1: An error occurred while retrieving disk space information.
            0: The disk space information was successfully retrieved.
        - arg 2: error message (if any).
    """
    try:
        usage = psutil.disk_usage(path)
        return usage.free, ""
    except Exception as e:
        return (
            -1,
            f"Failed To Get Space Available - {sys_consts.SDELIM}{e}{sys_consts.SDELIM}",
        )


def Get_Color_Names() -> list[str]:
    """
    Return a sorted list of color names from the Color Enum.

    Returns:
        list[str]: A sorted list of color names as strings.
    """
    return sorted([member.name.lower() for member in Color])


def Get_Hex_Color(color: str) -> str:
    """
    This function returns the hexadecimal value for a given color name.

    Args:
        color (str): The name of the color to look up.

    Returns:
        str: The hexadecimal value for the given color name or "" if color unknown.

    """
    assert (
        isinstance(color, str) and color.strip() != "" and color in Get_Color_Names()
    ), f"{color=}. Must be string  in {', '.join(Get_Color_Names())} "

    assert isinstance(color, str) and color.upper() in Color.__members__, (
        f"{color=}. Must be one of {[member.name for member in Color]}"
    )

    color = color.lower()

    for member in Color:
        if member.name.lower() == color:
            return member.value
    else:
        return ""


def Get_Colored_Rectangle_Example(width: int, height: int, color: str) -> bytes:
    """
    Generates a PNG image of a colored rectangle.

    Args:
        width (int): The width of the rectangle in pixels.
        height (int): The height of the rectangle in pixels.
        color (str): The color of the rectangle in any ImageMagick-supported color format.

    Returns:
        A bytes object containing the generated PNG image or b"" if an error.

    """
    # Check input arguments
    assert isinstance(width, int) and width > 0, f"{width}. Must be a positive integer."
    assert isinstance(height, int) and height > 0, (
        f"{height}. Must be a positive integer."
    )
    assert isinstance(color, str) and color.upper() in Color.__members__, (
        f"{color=}. Must be one of {[member.name for member in Color]}"
    )

    size = f"{width}x{height}"
    command = ["convert", "-size", size, f"xc:{color}", "png:-"]

    try:
        return subprocess.check_output(command, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return b""


def Get_Font_Example(
    font_file: str,
    pointsize: int = -1,
    text: str = "Example Text",
    text_color: str = "black",
    background_color: str = "wheat",
    width: int = -1,
    height: int = -1,
    opacity: float = 1.0,
) -> tuple[int, bytes]:
    """
    Returns a png byte string an example of what a font looks like

    Args:
        font_file (str): The font file path
        pointsize (int): The text point size. Optional -1 autocalcs
        text(str): The example text placed in the png
        text_color(str): The example text color in the png
        background_color(str): The background color of the png
        width(int): Width of png in pixels. Optional -1 autocalcs
        height(int): Height of png in pixels. Optional -1 autocalcs
        opacity (float): The opacity level to be set for the color ,
                        where 0.0 is fully transparent and 1.0 is fully opaque.

    Returns:
        tuple[int,bytes]:
        - arg 1: point size or -1 if error.
        - arg 2: A png byte string or an empty byte sttring if an error occurs
    """
    assert isinstance(font_file, str), f"{font_file=}. Must be str"
    assert isinstance(pointsize, int) and pointsize == -1 or pointsize > 0, (
        f"{pointsize=}. Must be -1 to autocalc or int > 0"
    )
    assert isinstance(text, str), (
        f"{text=}. Must be non-empty str" and text.strip() != ""
    )

    assert isinstance(text_color, str) and text_color.upper() in Color.__members__, (
        f"{text_color=}. Must be one of {[member.name for member in Color]}"
    )

    assert (
        isinstance(background_color, str)
        and background_color.upper() in Color.__members__
    ), f"{background_color=}. Must be one of {[member.name for member in Color]}"

    assert isinstance(width, int) and width == -1 or width > 0, (
        f"{width=}. Must be int > 0 or -1 to autocalc"
    )
    assert isinstance(height, int) and height == -1 or height > 0, (
        f"{height=}. Must be int > 0 or -1 to autocalc"
    )
    assert 0.0 <= opacity <= 1.0, "Opacity must be between 0.0 and 1.0"

    if not os.path.exists(font_file):
        return -1, b""

    try:
        if pointsize == -1:
            # Find the optimal font size to fit the text within the bounding box
            # Determine the initial bounds for the binary search
            low, high = 1, 200
            text_width, text_height = Get_Text_Dims(
                text=text, font=font_file, pointsize=10
            )

            # If the text dimensions are larger than the bounding box, return an empty string
            if (0 < width < text_width) or (0 < height < text_height):
                return -1, b""

            # Binary search for the optimal font size
            while low <= high:
                mid = (low + high) // 2

                text_width, text_height = Get_Text_Dims(
                    text=text, font=font_file, pointsize=mid
                )

                if text_width == -1 and text_height == -1:
                    return -1, b""

                if (0 < width < text_width) or (0 < height < text_height):
                    high = mid - 1
                else:
                    pointsize = mid
                    low = mid + 1

        result, background_hex = Make_Opaque(color=background_color, opacity=opacity)

        if result == -1:
            return -1, b""

        command = [
            sys_consts.CONVERT,
            "-size",
            f"{width}x{height}",
            f"xc:{background_hex}",
            "-fill",
            text_color,
            "-font",
            font_file,
            "-pointsize",
            f"{pointsize}",
            "-gravity",
            "center",
            "-draw",
            f"text 0,0 ' {text} '",
            "png:-",
        ]

        return pointsize, subprocess.check_output(command, stderr=subprocess.DEVNULL)

    except subprocess.CalledProcessError:
        return -1, b""


def Get_Fonts() -> list[tuple[str, str]]:
    """
    Returns a list of built-in fonts

    Returns:
        list[tuple[str, str]]: A list of tuples, where each tuple contains the font name as the first
        element and font file path as the second element.

    """
    font_list = []
    font_dirs = []

    # Directories to search for font files
    if platform.system() == "Linux":
        font_dirs = [
            "/usr/share/fonts/",
            "/usr/local/share/fonts/",
            os.path.expanduser("~/.fonts/"),
            "/Library/Fonts/",
            ".",
            os.path.expanduser("~/Library/Fonts/"),
        ]

    if platform.system() == "Windows":
        windows_font_dir = os.getenv("WINDIR")
        if windows_font_dir is not None:
            font_dirs.append(windows_font_dir + "\\Fonts\\")

    # Add Mac font directory if the platform is Mac
    if platform.system() == "Darwin":
        font_dirs.append("/System/Library/Fonts/")

    # Supported font file extensions
    font_extensions = ["*.ttf", "*.otf"]

    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            for root, _, _ in os.walk(font_dir):
                for font_extension in font_extensions:
                    font_files = glob.glob(os.path.join(root, font_extension))
                    for font_file in font_files:
                        font_list.append((os.path.basename(font_file), font_file))

    return sorted(font_list, key=lambda x: x[0].upper())


def Make_Opaque(color: str, opacity: float) -> tuple[int, str]:
    """
    Makes a hex color value partially opaque.

    Args:
        color (str): The color to be made partially opaque.
        opacity (float): The opacity level to be set for the color ,
                        where 0.0 is fully transparent and 1.0 is fully opaque.

    Returns:
        str: The hex color value with the specified opacity level.
        tuple[int, str] :
        - arg1: 1 Ok, -1, Error
        - arg2: Error message or hex color value with the specified opacity level. if ok

    """
    assert isinstance(color, str) and color.upper() in Color.__members__, (
        f"{color=}. Must be one of {[member.name for member in Color]}"
    )

    assert 0.0 <= opacity <= 1.0, "Opacity must be between 0.0 and 1.0"

    hex_color = Get_Hex_Color(color)

    if hex_color == "":
        return -1, f"Invalid System Color {color}"

    opacity_hex = hex(int(255 * opacity)).lstrip("0x").rjust(2, "0").upper()

    return 1, hex_color + opacity_hex


def Create_Transparent_File(
    width: int, height: int, out_file: str, border_color=""
) -> tuple[int, str]:
    """
    Creates a transparent file of a given width and height.
    If a border color is provided, a rectangle of that color is drawn
    around the edge of the file

    Args:
        width (int): Width of the new file
        height (int): Height of the new file
        out_file (str): The path for the new transparent file
        border_color (str, optional): The border color of the transparent
        file. Defaults to "".

    Returns:
        tuple[int,str]:
        - arg1 1: ok, -1: fail,
        - arg2: error message or "" if ok
    """
    border_width = 10

    if border_color == "":
        command = [
            sys_consts.CONVERT,
            "-size",
            f"{width}x{height}",
            "xc:none",
            out_file,
        ]
    else:
        command = [
            sys_consts.CONVERT,
            "-size",
            f"{width}x{height}",
            "xc:transparent",
            "-fill",
            "none",
            "-stroke",
            border_color,
            "-strokewidth",
            f"{border_width}",
            "-draw",
            f"rectangle 0,0,{width},{height}",
            out_file,
        ]

    return Execute_Check_Output(commands=command)


def Overlay_File(
    in_file: str, overlay_file: str, out_file: str, x: int, y: int
) -> tuple[int, str]:
    """
    Places the overlay_file on the input file at a given x,y co-ord
    saves the combined file to the output file

    Args:
        in_file (str): File which will have the overlay_file placed on it
        overlay_file (str): File which will be overlaid on the in_file
        out_file (str): File which will be saved as the combined file in_file and overlay_file
        x (int): x co-ord of overlay_file
        y (int): y co-ord of overlay_file

    Returns:
        tuple[int,str]:
        - arg1 1: ok, -1: fail
        - arg2: error message or "" if ok
    """
    # Image magick V6 Composite works magick V7 magick composite does not
    command = [
        sys_consts.COMPOSITE,
        "-geometry",
        f"+{x}+{y}",
        overlay_file,
        in_file,
        out_file,
    ]

    return Execute_Check_Output(commands=command)


def Overlay_Text(
    in_file: str,
    text: str,
    text_font: str,
    text_pointsize: int,
    text_color: str,
    position: str = "bottom",
    justification: str = "center",
    background_color: str = "grey",
    opacity: float = 0.5,
    x_offset: int = 0,
    y_offset: int = 0,
    pixel_line_spacing: int = 0,
    out_file: str = "",
) -> tuple[int, str]:
    """
    Overlays text onto an image.

    Args:
        in_file (str): The path to the image file.
        text (str): The text to overlay on the image.
        text_font (str): The font to use for the text.
        text_pointsize (int): The font size to use for the text.
        text_color (str): The color to use for the text.
        position (str, optional): The position of the text on the image. Defaults to "bottom".
        justification (str, optional): The justification of the text on the image. Defaults to "center".
        background_color (str, optional): The color of the background for the text. Defaults to "grey".
        opacity (float, optional): The opacity of the background for the text. Defaults to 0.5.
            0.0 is fully transparent and 1.0 is fully opaque.
        x_offset (int,optional) : The x offset of the text from the center of the text box
        y_offset (int,optional) : The y offset of the text from the center of the text box
        pixel_line_spacing (int,optional) : The spacing between lines in pixels
        out_file (str,optional): The path to the output file. Optional, sam as in_file if not supplied


    Returns:
        tuple[int, str]:
        - arg1: Ok, -1, Error,
        - arg2: Error message or "" if ok
    """
    assert isinstance(in_file, str), f"{in_file=} must be a string"
    assert isinstance(text, str), f"{text=} must be a string"
    assert isinstance(text_font, str) and text_font.strip() != "", (
        f"{text_font=} must be a non-empty str {type(text_font)=}"
    )
    assert isinstance(text_pointsize, int), f"{text_pointsize=} must be an integer"
    assert isinstance(text_color, str) and text_color.upper() in Color.__members__, (
        f"{text_color=}. Must be one of {[member.name for member in Color]}"
    )
    assert position.lower() in [
        "top",
        "bottom",
        "center",
    ], f"{position=} must be 'top', 'bottom', or 'center'"
    assert justification.lower() in [
        "left",
        "center",
        "right",
    ], f"{justification=} must be 'left', 'center', 'right' "
    assert isinstance(background_color, str), f"{background_color=} must be a string"
    assert 0 <= opacity <= 1, f"{opacity=} must be a value between 0 and 1"
    assert isinstance(x_offset, int), f"{x_offset=}. Must be int"
    assert isinstance(y_offset, int), f"{y_offset=}. Must be int"
    assert isinstance(pixel_line_spacing, int), f"{pixel_line_spacing=}. Must be int"
    assert isinstance(out_file, str), f"{out_file=} must be a string"

    if y_offset == 0:  # So text does not sit right on the edge
        y_offset += 10

    if out_file == "":
        out_file = in_file

    if not os.path.exists(in_file):
        return -1, f"{in_file} Does Not Exist "

    gravity = {"top": "North", "bottom": "South", "center": "Center"}[position.lower()]
    justification = {"left": "West", "center": "Center", "right": "East"}[
        justification.lower()
    ]

    background_color_hex = Get_Hex_Color(background_color)

    if background_color_hex == "":
        return -1, f"Unknown color {background_color}"

    result, text_hex = Make_Opaque(color=text_color, opacity=1)

    if result == -1:
        return -1, f"Invalid System Color {text_color}"

    result, background_hex = Make_Opaque(color=background_color, opacity=opacity)

    if result == -1:
        return -1, f"Invalid System Color {text_color}"

    image_width, message = Get_Image_Width(in_file)

    if image_width == -1:
        return -1, message

    if "\n" in text:
        text_lines = text.split("\n")
        text_width, text_height = Get_Text_Dims(
            text=text_lines[0], font=text_font, pointsize=text_pointsize
        )

        y_offset = y_offset

        for line_index, text_line in enumerate(text_lines):
            result, message = Overlay_Text(
                in_file=in_file,
                text=text_line,
                text_font=text_font,
                text_pointsize=text_pointsize,
                text_color=text_color,
                position=position,
                background_color=background_color,
                opacity=opacity,
                x_offset=x_offset,
                y_offset=y_offset,
                out_file=out_file,
            )

            if result == -1:
                return -1, message

            y_offset += text_height + pixel_line_spacing
        return result, message
    else:
        text_width, text_height = Get_Text_Dims(
            text=text, font=text_font, pointsize=text_pointsize
        )

        if text_width == -1:
            return -1, "Could Not Get Text Width"

        command = [
            sys_consts.CONVERT,
            "-density",
            "72",
            "-units",
            "pixelsperinch",
            in_file,
            "-background",
            background_hex,
            "-fill",
            text_hex,
            "-gravity",
            justification,
            "-font",
            text_font,
            "-pointsize",
            f"{text_pointsize}",
            "-size",
            f"{image_width}x",
            f"caption:{text}",
            "-gravity",
            gravity,
            "-geometry",
            f"+{x_offset}+{y_offset}",
            "-composite",
            out_file,
        ]

        return Execute_Check_Output(commands=command)


def Build_Video_Filters(
    auto_bright: bool,
    normalise: bool,
    white_balance: bool,
    denoise: bool,
    sharpen: bool,
    filters_off: bool,
    black_border: bool,
    target_width: int = -1,
    target_height: int = -1,
    deinterlace_video: bool = False,
    include_dvd_interlacing: bool = False,
    apply_spp: bool = False,
    dehalo: bool = False,
    input_video_frame_rate: Optional[float] = None,
    video_interlaced: Optional[bool] = None,
    dvd_standard: Optional[str] = None,
) -> list[str]:
    """
    Constructs the list of FFmpeg video filter arguments, with an option
    to include DVD-specific interlacing logic.

    Args:
        auto_bright (bool): Whether to apply auto-brightening (pp=dr/al).
        normalise (bool): Whether to apply video normalization.
        white_balance (bool): Whether to apply color correction (white balance).
        denoise (bool): Whether to apply video denoising.
        sharpen (bool): Whether to apply unsharp mask.
        filters_off (bool): If True, only scaling, deinterlacing, and black borders are applied (if requested),
                            no other aesthetic filters.
        black_border (bool): Whether to add black borders to the video for aesthetic masking.
        target_width (int): The desired output width. If -1, no specific scale is forced.
        target_height (int): The desired output height. If -1, no specific scale is forced.
        deinterlace_video (bool): If True, applies a general deinterlacing filter (e.g., yadif). Defaults to False.
        include_dvd_interlacing (bool): If True, DVD-specific interlacing logic is applied
                                        to *progressive* input to make it interlaced for DVD. Defaults to False.
        apply_spp (bool): If True, applies the spp deblocking/denoising filter.
        dehalo (bool): If True, applies the dehalo filter to reduce halos/ringing.
        input_video_frame_rate (Optional[float]): The frame rate of the input video.
                                                    Required if include_dvd_interlacing is True.
        video_interlaced (Optional[bool]): True if the input video is interlaced.
                                            Required if include_dvd_interlacing is True.
        dvd_standard (Optional[str]): The target DVD standard (sys_consts.PAL or sys_consts.NTSC).
                                        Required if include_dvd_interlacing is True.

    Returns:
        list[str]: A list containing the "-vf" argument and the joined filter string,
                   or an empty list if no filters are applied.
    """
    # --- Input Validation (Assertions) ---
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert isinstance(target_width, int) and (target_width > 0 or target_width == -1), (
        f"{target_width=}. Must be int > 0 or -1"
    )
    assert isinstance(target_height, int) and (
        target_height > 0 or target_height == -1
    ), f"{target_height=}. Must be int > 0 or -1"
    assert isinstance(deinterlace_video, bool), f"{deinterlace_video=}. Must be bool"
    assert isinstance(include_dvd_interlacing, bool), (
        f"{include_dvd_interlacing=}. Must be bool"
    )
    assert isinstance(apply_spp, bool), f"{apply_spp=}. Must be bool"
    assert isinstance(dehalo, bool), f"{dehalo=}. Must be bool"

    if include_dvd_interlacing:
        assert input_video_frame_rate is not None and isinstance(
            input_video_frame_rate, float
        ), (
            "input_video_frame_rate must be provided and be a float if include_dvd_interlacing is True"
        )
        assert video_interlaced is not None and isinstance(video_interlaced, bool), (
            "video_interlaced must be provided and be a bool if include_dvd_interlacing is True"
        )
        assert dvd_standard in [sys_consts.PAL, sys_consts.NTSC], (
            "dvd_standard must be PAL or NTSC if include_dvd_interlacing is True"
        )

    normalise_video_filter = (
        "normalize=blackpt=black:whitept=white:smoothing=11:independence=0.5"
    )

    tv_normalise_video_filter = "normalize=16:235:smoothing=11:independence=0.5"  # "scale=in_range=full:out_range=tv"  # "normalize=16:235:smoothing=11:independence=0.5"

    # "nlmeans=s=5:p=10:pc=10:r=15:rc=15"  # "nlmeans=1.0:7:5:3:3"

    video_denoise_filter = (
        "nlmeans=s=5:p=15:pc=15:r=5:rc=5"  # s=20 # "nlmeans=1.0:7:5:3:3"
    )
    color_correct_filter = "colorcorrect=analyze='median'"

    # "unsharp=7:7:2.5"  # "unsharp=luma_amount=0.2"
    usharp_filter = "unsharp=luma_amount=0.3"

    spp_filter = "spp=quality=4:qp=6"
    dehalo_filter = "dehalo=ls=1.5:ld=0.0:es=1.0:ed=0.0"

    black_border_size_lr = 12
    black_border_size_tb = 12

    black_box_filter_commands = [
        f"drawbox=x=0:y=0:w=iw:h={black_border_size_tb}:color=black:t=fill",
        f"drawbox=x=0:y=ih-{black_border_size_tb}:w=iw:h={black_border_size_tb}:color=black:t=fill",
        (
            f"drawbox=x=0:y={black_border_size_tb}:w={black_border_size_lr}:"
            f"h=ih-{black_border_size_tb * 2}:color=black:t=fill"
        ),
        (
            f"drawbox=x=iw-{black_border_size_lr}:y={black_border_size_tb}:w={black_border_size_lr}:"
            f"h=ih-{black_border_size_tb * 2}:color=black:t=fill"
        ),
    ]
    black_box_filter_str = ",".join(black_box_filter_commands)

    video_filter_options = []

    if deinterlace_video:
        video_filter_options.append("yadif=0:-1:-1")

    if not filters_off:  # Only apply these if filters are not off
        if apply_spp:
            video_filter_options.append(spp_filter)

        if dehalo:
            video_filter_options.append(dehalo_filter)

        if denoise:
            video_filter_options.append(video_denoise_filter)

        # Color/Levels Correction
        if normalise:
            video_filter_options.append(normalise_video_filter)
        if white_balance:
            video_filter_options.append(color_correct_filter)
        if auto_bright:
            video_filter_options.append("pp=dr/al")  # normalize can replace pp=dr/al,

    if target_width > 0 and target_height > 0:
        if (target_width, target_height) not in Standard_Resolutions():
            resolved_scale_width, resolved_scale_height = min(
                Standard_Resolutions(),
                key=lambda res_pair: math.sqrt(
                    (target_width - res_pair[0]) ** 2
                    + (target_height - res_pair[1]) ** 2
                ),
            )
            video_filter_options.append(
                f"scale={resolved_scale_width}:{resolved_scale_height}:flags=lanczos"
            )

    if not filters_off:  # Only apply if filters are not off
        if sharpen:
            video_filter_options.append(usharp_filter)

        # if normalise:
        #    video_filter_options.append(tv_normalise_video_filter)

    if include_dvd_interlacing:
        if not video_interlaced:  # Only interlace if input is progressive
            frame_rate_delta = 0.001
            if dvd_standard == sys_consts.PAL:
                if math.isclose(
                    input_video_frame_rate,
                    sys_consts.PAL_FIELD_RATE,
                    rel_tol=frame_rate_delta,
                ):
                    video_filter_options.append(
                        f"fps={sys_consts.PAL_FRAME_RATE},tinterlace=interleave_bottom"
                    )
                elif math.isclose(
                    input_video_frame_rate,
                    sys_consts.PAL_FRAME_RATE,
                    rel_tol=frame_rate_delta,
                ):
                    video_filter_options.append("tinterlace=interleave_bottom")
                else:
                    print(
                        f"WARNING: Input frame rate {input_video_frame_rate} not standard PAL progressive/field rate for"
                        f" DVD interlacing. Skipping interlacing."
                    )
            elif dvd_standard == sys_consts.NTSC:
                if math.isclose(
                    input_video_frame_rate,
                    sys_consts.NTSC_FIELD_RATE,
                    rel_tol=frame_rate_delta,
                ):
                    video_filter_options.append(
                        f"fps={sys_consts.NTSC_FRAME_RATE},tinterlace=interleave_bottom"
                    )
                elif math.isclose(
                    input_video_frame_rate,
                    sys_consts.NTSC_FRAME_RATE,
                    rel_tol=frame_rate_delta,
                ):
                    video_filter_options.append("tinterlace=interleave_bottom")
                else:
                    print(
                        f"WARNING: Input frame rate {input_video_frame_rate} not standard NTSC progressive/field rate "
                        f"for DVD interlacing. Skipping interlacing."
                    )

    if black_border:
        video_filter_options.append(black_box_filter_str)

    vf_string = ",".join(filterfalse(lambda x: not x, video_filter_options))

    return ["-vf", vf_string] if vf_string else []


def Transcode_DVD_VOB(
    input_file: str,
    output_folder: str,
    input_video_width: int,
    input_video_height: int,
    input_video_ar: str,  # e.g., "4:3", "16:9"
    input_video_scan_type: str,  # "interlaced" or "progressive"
    input_video_frame_rate: float,  # Actual frame rate of the input video
    auto_bright: bool,
    normalise: bool,
    white_balance: bool,
    denoise: bool,
    sharpen: bool,
    filters_off: bool,
    black_border: bool = False,
    dvd_standard: str = "",
    task_def: Task_Def = None,
) -> tuple[int, str]:
    """
    Encodes the input video file as a DVD VOB (mpeg2) file.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        input_video_width (int): Original width of the input video.
        input_video_height (int): Original height of the input video.
        input_video_ar (str): Original aspect ratio of the input video (e.g., "4:3", "16:9").
        input_video_scan_type (str): Scan type of the input video ("interlaced" or "progressive").
        input_video_frame_rate (float): Frame rate of the input video.
        auto_bright (bool): Whether to apply auto-brightening filter.
        normalise (bool): Whether to apply video normalization filter.
        white_balance (bool): Whether to apply color correction filter.
        denoise (bool): Whether to apply denoise filter.
        sharpen (bool): Whether to apply a sharpen filter.
        filters_off (bool): If True, skips all video processing filters except black borders.
        black_border (bool, optional): Whether to add black borders to the video. Defaults to False.
        dvd_standard (str): The target DVD standard (e.s., sys_consts.PAL, sys_consts.NTSC).
        task_def (Task_Def, optional): The task definition. If supplied, this becomes a background task. Defaults to None.

    Returns:
        tuple[int, str]:
            - arg 1: 1 if ok, -1 if error, 0 if task_def supplied and this becomes a background task.
            - arg 2: error message if error (-1) else output file path (1 or 0).
    """

    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a non-empty str"
    )
    assert isinstance(output_folder, str) and output_folder.strip() != "", (
        f"{output_folder=}. Must be a non-empty str"
    )
    assert isinstance(input_video_width, int) and input_video_width > 0, (
        f"{input_video_width=}. Must be int > 0"
    )
    assert isinstance(input_video_height, int) and input_video_height > 0, (
        f"{input_video_height=}. Must be int > 0"
    )
    assert isinstance(input_video_ar, str) and input_video_ar.strip() != "", (
        f"{input_video_ar=}. Must be a non-empty str"
    )
    assert (
        isinstance(input_video_scan_type, str) and input_video_scan_type.strip() != ""
    ), f"{input_video_scan_type=}. Must be a non-empty str"
    assert (
        isinstance(input_video_frame_rate, (float, int)) and input_video_frame_rate > 0
    ), f"{input_video_frame_rate=}. Must be float/int > 0"
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert dvd_standard in [sys_consts.PAL, sys_consts.NTSC], (
        f"{dvd_standard=}. Must be sys_consts.PAL or sys_consts.NTSC"
    )
    assert isinstance(task_def, Task_Def) or task_def is None, (
        f"{task_def=}. Must be Task_Def or None"
    )

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"

    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"

    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name_base, _ = file_handler.split_file_path(input_file)

    vob_file = file_handler.file_join(output_folder, f"{input_file_name_base}.vob")

    interlaced_video = input_video_scan_type.lower().startswith("interlaced")

    if input_video_width <= 0 or input_video_height <= 0:
        return (
            -1,
            f"Input video {input_file=} does not specify valid height and/or width.",
        )

    if not input_video_ar:
        return -1, f"Unrecognised Aspect Ratio : {input_video_ar} for {input_file=}"

    if dvd_standard == sys_consts.PAL:
        target_frame_rate = f"{sys_consts.PAL_FRAME_RATE}"
        target_width = sys_consts.PAL_SPECS.width_43  # PAL DVD width is 720
        target_height = sys_consts.PAL_SPECS.height_43  # PAL DVD height is 576
        target_video_size = f"{target_width}x{target_height}"

        if input_video_ar not in ["4:3", "16:9"]:
            return (
                -1,
                f"Video {input_video_width=}x{input_video_height=} with AR {input_video_ar} does not conform to PAL "
                f"specifications for DVD.",
            )

    else:  # NTSC
        target_frame_rate = f"{sys_consts.NTSC_FRAME_RATE}"
        target_width = sys_consts.NTSC_SPECS.width_43
        target_height = sys_consts.NTSC_SPECS.height_43
        target_video_size = f"{target_width}x{target_height}"

    video_filters = Build_Video_Filters(
        auto_bright=auto_bright,
        normalise=normalise,
        white_balance=white_balance,
        denoise=denoise,
        sharpen=sharpen,
        filters_off=filters_off,
        black_border=black_border,
        target_width=-1 if target_width == input_video_width else target_width,
        target_height=-1 if target_height == input_video_height else target_height,
        include_dvd_interlacing=True,
        input_video_frame_rate=input_video_frame_rate,
        video_interlaced=interlaced_video,
        dvd_standard=dvd_standard,
    )

    average_bit_rate = sys_consts.AVERAGE_BITRATE

    interlaced_flags = []

    if interlaced_video:
        interlaced_flags = [
            "-flags:v:0",
            "+ilme+ildct",
            "-alternate_scan:v:0",
            "1",
        ]

    command = [
        sys_consts.FFMPG,
        "-fflags",
        "+genpts",
        "-i",
        input_file,
        *interlaced_flags,
        "-f",
        "dvd",
        "-c:v:0",
        "mpeg2video",
        "-aspect",
        input_video_ar,
        "-s",
        target_video_size,
        "-r",
        target_frame_rate,
        "-g",
        "15",
        "-pix_fmt",
        "yuv420p",
        "-b:v",
        f"{average_bit_rate}k",
        "-maxrate:v",
        "9000k",
        "-minrate:v",
        "0",
        "-bufsize:v",
        "1835008",
        "-packetsize",
        "2048",
        "-muxrate",
        "10080000",
        "-force_key_frames",
        "expr:if(isnan(prev_forced_n),1,eq(n,prev_forced_n + 15))",
        *video_filters,
        "-b:a",
        "192000",
        "-ar",
        "48000",
        "-c:a:0",
        "ac3",
        "-filter:a:0",
        "loudnorm=I=-16:LRA=11:TP=-1.5",
        "-map",
        "0:V",
        "-map",
        "0:a",
        "-map",
        "-0:s",
        "-threads",
        "0",
        vob_file,
    ]

    if task_def:  # Run as a background task
        background_task_qmanager = Task_QManager()

        background_task_qmanager.submit_task(
            worker_function=Execute_Check_Output,
            commands=command,
            debug=False,
            stderr_to_stdout=False,
            task_id=task_def.task_id,
            started_callback=task_def.started_callback,
            progress_callback=task_def.progress_callback,
            finished_callback=task_def.finished_callback,
            error_callback=task_def.error_callback,
            aborted_callback=task_def.aborted_callback,
        )
        return 0, vob_file

    else:  # Run in the foreground
        result, message = Execute_Check_Output(
            commands=command, debug=False, stderr_to_stdout=False
        )

        if result == -1:
            return -1, message

    return 1, vob_file


def Transcode_DV(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    deinterlace: bool = False,
    auto_bright: bool = False,
    normalise: bool = False,
    white_balance: bool = False,
    denoise: bool = False,
    sharpen: bool = False,
    filters_off: bool = False,
    black_border: bool = False,
    task_def: Task_Def = None,
) -> tuple[int, str]:
    """
    Converts an input video file into a DV AVI file, adhering to standard PAL/NTSC DV specifications.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video (will be adjusted to DV standard).
        width (int): The target width of the output DV video (must be DV standard resolution).
        height (int): The target height of the output DV video (must be DV standard resolution).
        interlaced (bool, optional): True if the input video is interlaced, False if progressive. Defaults to True.
        bottom_field_first (bool, optional): Whether to use bottom field first for interlaced output. Defaults to True.
        deinterlace (bool, optional): If True, forces deinterlacing of the input video, making the output progressive. Defaults to False.
        auto_bright (bool): Whether to use auto brightness. Defaults to False.
        normalise (bool): Whether to use normalise. Defaults to False.
        white_balance (bool): Whether to use white balance. Defaults to False.
        denoise (bool): Whether to use denoise. Defaults to False.
        sharpen (bool): Whether to use sharpen. Defaults to False.
        filters_off (bool): Whether to disable all filters except scaling and black borders. Defaults to False.
        black_border (bool, optional): Whether to add black borders to the video. Defaults to False.
        task_def (Task_Def, optional): The task definition. If supplied, this becomes a background task. Defaults to None.

    Returns:
        tuple[int, str]:
            - arg 1: 1 if ok, -1 if error, 0 if task_def supplied and this becomes a background task.
            - arg 2: error message if error (-1) else output file path (1 or 0).
    """

    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a non-empty str"
    )
    assert isinstance(output_folder, str) and output_folder.strip() != "", (
        f"{output_folder=}. Must be a non-empty str"
    )
    assert isinstance(frame_rate, float) and frame_rate > 0, (
        f"{frame_rate=}. Must be float > 0"
    )
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(deinterlace, bool), f"{deinterlace=}. Must be bool"
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert isinstance(task_def, Task_Def) or task_def is None, (
        f"{task_def=}. Must be Task_Def or None"
    )

    if deinterlace and not interlaced:
        return (
            -1,
            "Cannot force deinterlace when input video is progressive. Input is already progressive.",
        )

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"
    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"
    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)
    output_file = file_handler.file_join(output_folder, f"{input_file_name}.avi")

    # DV resolutions are fixed based on standard
    if (
        width == sys_consts.PAL_SPECS.width_43
        and height == sys_consts.PAL_SPECS.height_43
    ) or (
        width == sys_consts.PAL_SPECS.width_169
        and height == sys_consts.PAL_SPECS.height_43
    ):  # Anamorphic PAL
        adjusted_frame_rate = sys_consts.PAL_SPECS.frame_rate
    elif (
        width == sys_consts.NTSC_SPECS.width_43
        and height == sys_consts.NTSC_SPECS.height_43
    ) or (
        width == sys_consts.NTSC_SPECS.width_169
        and height == sys_consts.NTSC_SPECS.height_43
    ):  # Anamorphic NTSC
        adjusted_frame_rate = sys_consts.NTSC_SPECS.frame_rate
    else:
        return (
            -1,
            f"{width=}x{height=} Does Not Meet Standard PAL/NTSC DV specs (e.g., 720x576, 720x480)",
        )

    # If the provided frame_rate is significantly different from the adjusted DV standard, warn or error
    if (
        abs(frame_rate - adjusted_frame_rate) > 0.01
    ):  # Use a small tolerance for float comparison
        print(
            f"Warning: Input frame rate {frame_rate} does not match DV standard {adjusted_frame_rate}. Adjusting."
        )

    video_filters_arg = Build_Video_Filters(
        auto_bright=auto_bright,
        normalise=normalise,
        white_balance=white_balance,
        denoise=denoise,
        sharpen=sharpen,
        filters_off=filters_off,
        black_border=black_border,
        target_width=width,
        target_height=height,
        deinterlace_video=deinterlace,
        include_dvd_interlacing=False,
    )

    field_order_filter = f"fieldorder={'bff' if bottom_field_first else 'tff'}"

    # DV output is ALWAYS interlaced. So, these flags and field order filter should always be applied.
    interlaced_flags = [
        "-flags:v:0",
        "+ilme+ildct",
        "-alternate_scan:v:0",
        "1",
    ]

    if video_filters_arg:
        video_filters_arg[1] = f"{field_order_filter},{video_filters_arg[1]}"
    else:
        video_filters_arg = ["-vf", field_order_filter]

    command = [
        sys_consts.FFMPG,
        "-i",
        input_file,
        "-vsync",
        "1",  # Preserve input timestamps (or 'cfr' for constant frame rate)
        *video_filters_arg,
        *interlaced_flags,
        "-r",
        str(adjusted_frame_rate),  # Use the adjusted DV standard frame rate
        "-c:v",
        "dvvideo",  # DV video codec
        "-c:a",
        "pcm_s16le",  # Uncompressed audio for DV
        "-threads",
        "0",
        "-y",
        output_file,
    ]

    if task_def:  # Run as a background task
        background_task_qmanager = Task_QManager()

        background_task_qmanager.submit_task(
            worker_function=Execute_Check_Output,
            commands=command,
            debug=False,
            stderr_to_stdout=False,
            task_id=task_def.task_id,
            started_callback=task_def.started_callback,
            progress_callback=task_def.progress_callback,
            finished_callback=task_def.finished_callback,
            error_callback=task_def.error_callback,
            aborted_callback=task_def.aborted_callback,
        )

        return 0, output_file
    else:  # Run in the foreground
        result, message = Execute_Check_Output(
            commands=command, debug=False, stderr_to_stdout=False
        )

        if result == -1:
            return -1, message

    return 1, output_file


def Transcode_ffv1_archival(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    deinterlace: bool = False,
    auto_bright: bool = False,
    normalise: bool = False,
    white_balance: bool = False,
    denoise: bool = False,
    sharpen: bool = False,
    filters_off: bool = False,
    black_border: bool = False,
    apply_spp: bool = False,
    dehalo: bool = False,
    task_def: Task_Def = None,
) -> tuple[int, str]:
    """
    Converts an input video file into a lossless FFV1 compressed video suitable for permanent archival storage.

    FFV1 is a permanent archival format widely accepted by archival institutions worldwide.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int): The target width of the output video.
        height (int): The target height of the output video.
        interlaced (bool, optional): True if the input video is interlaced, False if progressive. Defaults to True.
        bottom_field_first (bool, optional): Whether to use bottom field first for interlaced output. Defaults to True.
        deinterlace (bool, optional): If True, forces deinterlacing of the input video, making the output progressive. Defaults to False.
        auto_bright (bool): Whether to use auto brightness. Defaults to False.
        normalise (bool): Whether to use normalise. Defaults to False.
        white_balance (bool): Whether to use white balance. Defaults to False.
        denoise (bool): Whether to use denoise. Defaults to False.
        sharpen (bool): Whether to use sharpen. Defaults to False.
        filters_off (bool): Whether to disable all filters except scaling and black borders. Defaults to False.
        black_border (bool, optional): Whether to add black borders to the video. Defaults to False.
        apply_spp (bool): Whether to apply the spp deblocking/denoising filter. Defaults to False.
        dehalo (bool): Whether to apply the dehalo filter to reduce halos/ringing. Defaults to False.
        task_def (Task_Def): The task definition, if this is supplied, then this becomes a background task. Defaults to None.

    Returns:
        tuple[int, str]:
            - arg 1: 1 if ok, -1 if error, 0 if task_def supplied and this becomes a background task
            - arg 2: error message if error (-1) else output file path (1 or 0)
    """

    # Helper functions for background task management
    def _started_callback(task_id: str):
        """
        Called when pass 1 or pass 2 starts in the background

        Args:
            task_id (str): Task ID
        """
        assert isinstance(task_id, str), f"{task_id=}. Must be str"

        task_def.started_callback(task_def.task_id)

    def _progress_callback(task_id: str, percentage: float, message: str):
        """
        Called when pass 1 or pass 2 makes progress in the background

        Args:
            task_id (str): Task ID
            percentage (float): Percentage complete
            message (str): Message
        """
        assert isinstance(task_id, str), f"{task_id=}. Must be str"
        assert isinstance(percentage, float), f"{percentage=}. Must be float"
        assert isinstance(message, str), f"{message=}. Must be str"

        if task_def.progress_callback:
            task_def.progress_callback(task_def.task_id, percentage, message)

    def _finished_callback(task_id: str, result: tuple[int, str]):
        """
        Called when pass 1 or pass 2 finishes in the background

        Args:
            task_id (str): Task ID
            result (tuple[int, str]): Result tuple
        """
        assert isinstance(task_id, str), f"{task_id=}. Must be str"
        assert isinstance(result, tuple), f"{result=}. Must be tuple"

        if task_id.endswith("_pass1"):
            background_task_qmanager.submit_task(
                worker_function=Execute_Check_Output,
                commands=pass_2,
                debug=False,
                stderr_to_stdout=False,
                task_id=f"{task_def.task_id}_pass2",
                started_callback=_started_callback,
                error_callback=_error_callback,
                finished_callback=_finished_callback,
                # progress_callback=_progress_callback,
                aborted_callback=_aborted_callback,
            )

        elif task_id.endswith("_pass2"):
            if file_handler.remove_file(passlog_del_file) == -1:
                task_def.finished_callback(
                    task_def.task_id, (-1, f"Failed To Delete {passlog_del_file}")
                )
            else:
                task_def.finished_callback(task_def.task_id, result)

        return None

    def _error_callback(task_id: str, message: str):
        """
        Called when an error occurs in pass 1 or pass 2

        Args:
            task_id (str): Task ID
            message (str): Error Message
        """
        assert isinstance(task_id, str), f"{task_id=}. Must be str"
        assert isinstance(message, str), f"{message=}. Must be str"

        path, name, ext = file_handler.split_file_path(passlog_del_file)

        if (
            file_handler.file_exists(path, name, ext)
            and file_handler.remove_file(passlog_del_file) == -1
        ):
            task_def.finished_callback(
                task_def.task_id,
                (-1, f"Failed To Delete {passlog_del_file} \n {message}"),
            )
        else:
            task_def.finished_callback(task_def.task_id, (-1, message))

        task_def.error_callback(task_id, (-1, message))

    def _aborted_callback(task_id: str, message: str):
        """
        Called when pass 1 or pass 2 is aborted

        Args:
            task_id (str): Task ID
            message (str): Error Message
        """
        assert isinstance(task_id, str), f"{task_id=}. Must be str"
        assert isinstance(message, str), f"{message=}. Must be str"

        path, name, ext = file_handler.split_file_path(passlog_del_file)
        if (
            file_handler.file_exists(path, name, ext)
            and file_handler.remove_file(passlog_del_file) == -1
        ):
            task_def.aborted_callback(
                task_def.task_id,
                (-1, f"Failed To Delete {passlog_del_file} \n {message}"),
            )
        else:
            task_def.aborted_callback(task_def.task_id, message)

    #### Main

    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a non-empty str"
    )
    assert isinstance(output_folder, str) and output_folder.strip() != "", (
        f"{output_folder=}. Must be a non-empty str"
    )
    assert isinstance(frame_rate, float) and frame_rate > 0, (
        f"{frame_rate=}. Must be float > 0"
    )
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(deinterlace, bool), f"{deinterlace=}. Must be bool"
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert isinstance(apply_spp, bool), f"{apply_spp=}. Must be bool"  # NEW: Assertion
    assert isinstance(dehalo, bool), f"{dehalo=}. Must be bool"  # NEW: Assertion
    assert isinstance(task_def, Task_Def) or task_def is None, (
        f"{task_def=}. Must be Task_Def or None"
    )

    if deinterlace and not interlaced:
        return (
            -1,
            "Cannot force deinterlace when input video is progressive. Input is already progressive.",
        )

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"
    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"
    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)

    output_file = file_handler.file_join(output_folder, f"{input_file_name}.mkv")
    passlog_file = file_handler.file_join(output_folder, f"{input_file_name}")
    passlog_del_file = file_handler.file_join(output_folder, f"{input_file_name}-0.log")

    video_filters_arg = Build_Video_Filters(
        auto_bright=auto_bright,
        normalise=normalise,
        white_balance=white_balance,
        denoise=denoise,
        sharpen=sharpen,
        filters_off=filters_off,
        black_border=black_border,
        target_width=width,
        target_height=height,
        deinterlace_video=deinterlace,
        include_dvd_interlacing=False,
        apply_spp=apply_spp,
        dehalo=dehalo,
    )

    interlaced_output_flags = []
    field_order_filter_str = ""

    if interlaced and not deinterlace:
        field_order_filter_str = f"fieldorder={'bff' if bottom_field_first else 'tff'}"
        interlaced_output_flags = [
            "-flags:v",
            "+ilme+ildct",
            "-alternate_scan:v",
            "1",
        ]
    all_filters = []
    if field_order_filter_str:
        if (
            video_filters_arg and video_filters_arg[1]
        ):  # Check if the filter string part exists
            video_filters_arg[1] = f"{field_order_filter_str},{video_filters_arg[1]}"
        else:
            video_filters_arg = ["-vf", field_order_filter_str]

    # Command 1 (Pass 1)
    pass_1 = [
        sys_consts.FFMPG,
        "-i",
        input_file,
        "-vsync",
        "cfr",
        "-max_muxing_queue_size",
        "9999",
        "-pass",
        "1",
        "-passlogfile",
        passlog_file,
        *video_filters_arg,
        *interlaced_output_flags,
        "-r",
        str(frame_rate),
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-coder",
        "1",  # Golomb Rice
        "-context",
        "1",  # Small context
        "-g",
        "1",  # All I-frames
        "-slices",
        "16",  # More slices for parallel processing
        "-slicecrc",
        "1",  # CRC checks for slices
        "-c:a",
        "flac",  # Lossless audio
        "-f",
        "null",  # Output to null device for pass 1
        "-threads",
        "0",
        str(os.devnull),
    ]

    # Command 2 (Pass 2)
    pass_2 = [
        sys_consts.FFMPG,
        "-i",
        input_file,
        "-vsync",
        "cfr",
        "-max_muxing_queue_size",
        "9999",
        "-pass",
        "2",
        "-passlogfile",
        passlog_file,
        *video_filters_arg,
        *interlaced_output_flags,
        "-r",
        str(frame_rate),
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-coder",
        "1",
        "-context",
        "1",
        "-g",
        "1",
        "-slices",
        "16",
        "-slicecrc",
        "1",
        "-c:a",
        "flac",
        "-threads",
        "0",
        "-y",
        output_file,
    ]

    if task_def:  # Run in the background
        background_task_qmanager = Task_QManager()

        # Pass 1 submission
        background_task_qmanager.submit_task(
            worker_function=Execute_Check_Output,
            commands=pass_1,
            debug=False,
            stderr_to_stdout=False,
            task_id=f"{task_def.task_id}_pass1",
            started_callback=_started_callback,
            error_callback=_error_callback,
            finished_callback=_finished_callback,
            # progress_callback=_progress_callback,
            aborted_callback=_aborted_callback,
        )

        return 0, output_file

    else:  # Run in the foreground
        result, message = Execute_Check_Output(
            commands=pass_1, debug=False, stderr_to_stdout=False
        )

        if result == -1:
            return -1, message

        result, message = Execute_Check_Output(
            commands=pass_2, debug=False, stderr_to_stdout=False
        )

        if result == -1:
            return -1, message

        # Delete passlog file only after successful completion of both passes
        if file_handler.remove_file(passlog_del_file) == -1:
            return -1, f"Failed To Delete {passlog_del_file}"

    return 1, output_file


def Transcode_Mezzanine(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    mjpeg: bool = False,
    deinterlace: bool = False,
    auto_bright: bool = False,
    normalise: bool = False,
    white_balance: bool = False,
    denoise: bool = False,
    sharpen: bool = False,
    filters_off: bool = False,
    black_border: bool = False,
    encode_10bit: bool = False,
    task_def: Task_Def = None,
) -> tuple[int, str]:
    """
    Converts an input video to MJPEG or H264 at supplied resolution and frame rate to make an edit copy that minimises
    generational losses. The video is transcoded to a file in the output folder.

       Args:
           input_file (str): The path to the input video file.
           output_folder (str): The path to the output folder.
           frame_rate (float): The frame rate to use for the output video.
           width (int): The target width of the output video
           height (int): The target height of the output video
           interlaced (bool, optional): True if the input video is interlaced, False if progressive. Defaults to True.
           bottom_field_first (bool, optional): Whether to use bottom field first for interlaced output. Only relevant
           if the output remains interlaced (i.e., `deinterlace` is False and `interlaced` is True). Defaults to True.
           mjpeg (bool, optional): True use MJPEG video as a Mezzanine video, False use H264.
           deinterlace (bool, optional): If True, forces deinterlacing of the input video, making the output progressive.
           Defaults to False.
           auto_bright (bool): Whether to use auto brightness. Defaults to False.
           normalise (bool): Whether to use normalise. Defaults to False.
           white_balance (bool): Whether to use white balance. Defaults to False.
           denoise (bool): Whether to use denoise. Defaults to False.
           sharpen (bool): Whether to use sharpen. Defaults to False.
           filters_off (bool): Whether to disable all filters except scaling and black borders. Defaults to False.
           black_border (bool, optional): Whether to add black borders to the video. Defaults to False.
           encode_10bit (bool, optional): If True, encode video to 10-bit YUV 4:2:2 (yuv422p10le). Defaults to False.
           task_def (Task_Def): The task definition, if this is supplied, then this becomes a background task. Defaults to None.

       Returns:
           tuple[int, str]:
               - arg 1: 1 if ok, -1 if error, 0 if task_def supplied and this becomes a background task
               - arg 2: error message if error (-1) else output file path (1 or 0)
    """
    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a non-empty str"
    )
    assert isinstance(output_folder, str) and output_folder.strip() != "", (
        f"{output_folder=}. Must be a non-empty str"
    )
    assert isinstance(frame_rate, float) and frame_rate > 0, (
        f"{frame_rate=}. Must be float > 0"
    )
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(mjpeg, bool), f"{mjpeg=}. Must be bool"
    assert isinstance(deinterlace, bool), f"{deinterlace=}. Must be bool"
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert isinstance(encode_10bit, bool), f"{encode_10bit=}. Must be bool"
    assert isinstance(task_def, Task_Def) or task_def is None, (
        f"{task_def=}. Must be Task_Def or None"
    )

    if deinterlace and not interlaced:
        return (
            -1,
            "Cannot force deinterlace when input video is progressive. Input is already progressive.",
        )

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"
    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"
    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)

    if encode_10bit:
        pixel_format = "yuv422p10le"  # 10-bit 4:2:2
    else:
        pixel_format = "yuv420p"  # Default to 8-bit 4:2:0

    if mjpeg:
        output_file = file_handler.file_join(output_folder, f"{input_file_name}.avi")

        if input_file == output_file:
            output_file = file_handler.file_join(
                output_folder, f"{input_file_name}_out.avi"
            )

        video_codec = "mjpeg"

        # MJPEG specific quality/bitrate settings
        q_v = "3"
        crf = None  # CRF not used for MJPEG
        preset = None  # Preset not used for MJPEG
        gop_size = 1  # MJPEG is typically I-frame only
        keyint_min = 1
        sc_threshold = 0

    else:  # H264 Mezzanine
        output_file = file_handler.file_join(output_folder, f"{input_file_name}.mkv")

        if input_file == output_file:
            output_file = file_handler.file_join(
                output_folder, f"{input_file_name}_out.mkv"
            )

        video_codec = (
            "libx264"  # Default for H264. If using H265, you'd change this here
        )
        q_v = None  # Q:v not used for H264
        crf = "17"  # Good quality for mezzanine H264
        preset = "medium"  # Medium preset for good balance
        gop_size = 1  # Mezzanine is I-frame only
        keyint_min = 1
        sc_threshold = 0

    # Set bit rate based on video height (common to both MJPEG and H264 Mezzanine)
    if height <= 576:  # SD
        bit_rate = 25
    else:  # HD
        bit_rate = 50

    if (width, height) in Standard_Resolutions():
        scale_width = -1
        scale_height = -1
    else:
        scale_width = width
        scale_height = height

    video_filters_arg = Build_Video_Filters(
        auto_bright=auto_bright,
        normalise=normalise,
        white_balance=white_balance,
        denoise=denoise,
        sharpen=sharpen,
        filters_off=filters_off,
        black_border=black_border,
        target_width=scale_width,
        target_height=scale_height,
        deinterlace_video=deinterlace,
    )

    interlaced_flags = []

    if not deinterlace and interlaced:
        interlaced_flags = [
            "-flags:v:0",
            "+ilme+ildct",
            "-alternate_scan:v:0",
            "1",
        ]

        field_order_filter = f"fieldorder={'bff' if bottom_field_first else 'tff'}"
        if video_filters_arg:
            video_filters_arg[1] = f"{field_order_filter},{video_filters_arg[1]}"
        else:
            video_filters_arg = ["-vf", field_order_filter]

    command = [
        sys_consts.FFMPG,
        "-fflags",
        "+genpts",  # generate presentation timestamps
        "-i",
        input_file,
        "-vsync",
        "cfr",
        "-max_muxing_queue_size",
        "9999",
        *video_filters_arg,
        *interlaced_flags,
        "-r",
        str(frame_rate),
        "-c:v",
        video_codec,
        "-b:v",
        f"{bit_rate}M",  # High bitrate for edit copy
        "-maxrate",
        f"{int(float(bit_rate) * 2)}M",
        "-bufsize",
        f"{int(float(bit_rate) * 5)}M",  # Adjusted bufsize for mezzanine
        "-sn",  # Remove titles
        "-pix_fmt",
        pixel_format,
    ]

    # Add codec-specific arguments
    if q_v:  # For MJPEG
        command.extend(["-q:v", q_v])
    if crf:  # For H264
        command.extend(["-crf", crf])
    if preset:  # For H264
        command.extend(["-preset", preset])

    command.extend([
        "-g",
        f"{gop_size}",
        "-keyint_min",
        f"{keyint_min}",
        "-sc_threshold",
        f"{sc_threshold}",
        "-c:a",
        "pcm_s16le",  # Uncompressed audio for mezzanine
        "-threads",
        "0",
        "-y",
        output_file,
    ])

    if task_def:  # Run in the background
        background_task_qmanager = Task_QManager()

        background_task_qmanager.submit_task(
            worker_function=Execute_Check_Output,
            commands=command,
            debug=False,
            stderr_to_stdout=False,
            task_id=task_def.task_id,
            started_callback=task_def.started_callback,
            progress_callback=task_def.progress_callback,
            finished_callback=task_def.finished_callback,
            error_callback=task_def.error_callback,
            aborted_callback=task_def.aborted_callback,
        )

        return 0, output_file

    else:  # Run in the foreground
        result, message = Execute_Check_Output(
            commands=command, debug=False, stderr_to_stdout=False
        )

        if result == -1:
            return -1, message

    return 1, output_file


def Transcode_MPEG2_High_Bitrate(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    iframe_only: bool = False,
    deinterlace: bool = False,
    auto_bright: bool = False,
    normalise: bool = False,
    white_balance: bool = False,
    denoise: bool = False,
    sharpen: bool = False,
    filters_off: bool = False,
    black_border: bool = False,
    task_def: Task_Def = None,
) -> tuple[int, str]:
    """
    Converts an input video to MPEG2 at supplied resolution and frame rate at a high bit rate to make an edit
    copy that minimises generational losses. The video is transcoded to a file in the output folder.

        Args:
            input_file (str): The path to the input video file.
            output_folder (str): The path to the output folder.
            frame_rate (float): The frame rate to use for the output video.
            width (int) : The target width of the output video
            height (int) : The target height of the output video
            interlaced (bool, optional): True if the input video is interlaced, False if progressive. Defaults to True.
            bottom_field_first (bool, optional): Whether to use bottom field first for interlaced output. Only relevant
            if the output remains interlaced (i.e., `deinterlace` is False and `input_video_is_interlaced` is True). Defaults to True.
            iframe_only (bool, optional): Generate iframe only. Defaults to False.
            deinterlace (bool, optional): If True, forces deinterlacing of the input video, making the output progressive. Defaults to False.
            auto_bright (bool): Whether to use auto brightness. Defaults to False.
            normalise (bool): Whether to use normalise. Defaults to False.
            white_balance (bool): Whether to use white balance. Defaults to False.
            denoise (bool): Whether to use denoise. Defaults to False.
            sharpen (bool): Whether to use sharpen. Defaults to False.
            filters_off (bool): Whether to disable all filters except scaling and black borders. Defaults to False.
            black_border (bool, optional): Whether to add black borders to the video. Defaults to False.
            task_def (Task_Def): The task definition, if this is supplied, then this becomes a background task. Defaults to None.

        Returns:
            tuple[int, str]:
                - arg 1: 1 if ok, -1 if error, 0 if task_def supplied and this becomes a background task
                - arg 2: error message if error (-1) else output file path (1 or 0)
    """
    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a non-empty str"
    )
    assert isinstance(output_folder, str) and output_folder.strip() != "", (
        f"{output_folder=}. Must be a non-empty str"
    )
    assert isinstance(frame_rate, float) and frame_rate > 0, (
        f"{frame_rate=}. Must be float > 0"
    )
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(iframe_only, bool), f"{iframe_only=}. Must be bool"
    assert isinstance(deinterlace, bool), f"{deinterlace=}. Must be bool"
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert isinstance(task_def, Task_Def) or task_def is None, (
        f"{task_def=}. Must be Task_Def or None"
    )

    if deinterlace and not interlaced:
        return (
            -1,
            "Cannot force deinterlace when input_video_is_interlaced is False. Input is already progressive.",
        )

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"
    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"
    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)
    output_file = file_handler.file_join(output_folder, f"{input_file_name}.mpg")

    gop_size = 1 if iframe_only else (15 if frame_rate == 25 else 18)

    if height <= 576:  # SD
        bit_rate = 9
    else:  # HD
        bit_rate = 50

    if (width, height) in Standard_Resolutions():
        scale_width = -1
        scale_height = -1
    else:
        scale_width = width
        scale_height = height

    video_filters_arg = Build_Video_Filters(
        auto_bright=auto_bright,
        normalise=normalise,
        white_balance=white_balance,
        denoise=denoise,
        sharpen=sharpen,
        filters_off=filters_off,
        black_border=black_border,
        target_width=scale_width,
        target_height=scale_height,
        deinterlace_video=deinterlace,
        include_dvd_interlacing=False,
    )

    interlaced_flags = []

    if not deinterlace and interlaced:
        interlaced_flags = [
            "-flags:v:0",
            "+ilme+ildct",
            "-alternate_scan:v:0",
            "1",
        ]

        field_order_filter = f"fieldorder={'bff' if bottom_field_first else 'tff'}"

        if video_filters_arg:
            video_filters_arg[1] = f"{field_order_filter},{video_filters_arg[1]}"
        else:
            video_filters_arg = ["-vf", field_order_filter]

    command = [
        sys_consts.FFMPG,
        "-fflags",
        "+genpts",  # generate presentation timestamps
        "-i",
        input_file,
        "-vsync",
        "cfr",
        "-max_muxing_queue_size",
        "9999",
        *video_filters_arg,
        *interlaced_flags,
        "-r",
        str(frame_rate),
        "-c:v",
        "mpeg2video",  # MPEG2 video codec
        "-b:v",
        f"{bit_rate}M",  # High bitrate for edit copy
        "-maxrate",
        f"{int(float(bit_rate) * 2)}M",
        "-bufsize",
        f"{int(float(bit_rate) * 10)}M",
        "-sn",  # Remove titles
        "-g",
        f"{gop_size}",
        "-force_key_frames",
        f"expr:if(isnan(prev_forced_n),1,eq(n,prev_forced_n+{gop_size}))",
        "-pix_fmt",
        "yuv420p",  # Standard pixel format for MPEG2
        "-bf",
        "2",  # Max B-frames for MPEG2
        "-c:a",
        "ac3",  # Assuming AC3 audio for MPEG2 output
        "-b:a",
        "256k",
        "-threads",
        "0",
        "-y",
        output_file,
    ]

    if task_def:  # Run in the background
        background_task_qmanager = Task_QManager()

        background_task_qmanager.submit_task(
            worker_function=Execute_Check_Output,
            commands=command,
            debug=False,
            stderr_to_stdout=False,
            task_id=task_def.task_id,
            started_callback=task_def.started_callback,
            progress_callback=task_def.progress_callback,
            finished_callback=task_def.finished_callback,
            error_callback=task_def.error_callback,
            aborted_callback=task_def.aborted_callback,
        )

        return 0, output_file
    else:  # Run in the foreground
        result, message = Execute_Check_Output(
            commands=command, debug=False, stderr_to_stdout=False
        )
        if result == -1:
            return -1, message

    return 1, output_file


def Standard_Resolutions() -> set:
    """
    Returns a list of standard resolutions

    Returns:
        set: List of standard resolutions
    """
    return {
        (
            sys_consts.PAL_SPECS.width_43,
            sys_consts.PAL_SPECS.height_43,
        ),  # 720x576 (PAL 4:3)
        (
            sys_consts.PAL_SPECS.width_169,
            sys_consts.PAL_SPECS.height_169,
        ),  # 720x576 (PAL 16:9 anamorphic)
        (
            sys_consts.NTSC_SPECS.width_43,
            sys_consts.NTSC_SPECS.height_43,
        ),  # 720x480 (NTSC 4:3)
        (
            sys_consts.NTSC_SPECS.width_169,
            sys_consts.NTSC_SPECS.height_169,
        ),  # 720x480 (NTSC 16:9 anamorphic)
        (1920, 1080),  # Full HD
        (1280, 720),  # HD
    }


def Transcode_H26x(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    h265: bool = False,
    high_quality: bool = True,
    iframe_only: bool = False,
    deinterlace: bool = False,
    auto_bright: bool = False,
    normalise: bool = False,
    white_balance: bool = False,
    denoise: bool = False,
    sharpen: bool = False,
    filters_off: bool = False,
    black_border: bool = False,
    encode_10bit: bool = False,
    mkv_container: bool = False,
    task_def: Task_Def = None,
) -> tuple[int, str]:
    """
    Converts an input video to H.264/5 at supplied resolution and frame rate.
    The video is transcoded to a file in the output folder.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int) : The target width of the output video
        height (int) : The target height of the output video
        interlaced (bool): True if the input video is interlaced, False if progressive. Defaults to True.
        bottom_field_first (bool): Whether to use bottom field first for interlaced output. Only relevant if the output
        remains interlaced (i.e., `deinterlace` is False and `interlaced` is True). Defaults to True.
        h265 (bool): Whether to use H.265. Defaults to False.
        high_quality (bool): Use a high quality encode. Defaults to True.
        iframe_only (bool): True if no GOP and all I-frames desired else False. Defaults to False.
        deinterlace (bool): If True, forces deinterlacing of the input video, making the output progressive. Defaults to False.
        auto_bright (bool): Whether to use auto brightness. Defaults to False.
        normalise (bool): Whether to use normalise. Defaults to False.
        white_balance (bool): Whether to use white balance. Defaults to False.
        denoise (bool): Whether to use denoise. Defaults to False.
        sharpen (bool): Whether to use sharpen. Defaults to False.
        filters_off (bool): Whether to disable all filters except scaling and black borders. Defaults to False.
        black_border (bool, optional): Whether to add black borders to the video. Defaults to False.
        encode_10bit (bool, optional): Encode videos as 10 bit. Defaults to False
        mkv_container: (bool, optional): Place output file in a mkv container, Otherwise a mp4 container. Defaults to False,
        task_def (Task_Def): The task definition, if this is supplied, then this becomes a background task. Defaults to None.

    Returns:
        tuple[int, str]:
            - arg 1: 1 if ok, -1 if error, 0 if task_def supplied and this becomes a background task
            - arg 2: error message if error (-1) else output file path (1)
    """
    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a non-empty str"
    )
    assert isinstance(output_folder, str) and output_folder.strip() != "", (
        f"{output_folder=}. Must be a non-empty str"
    )
    assert isinstance(frame_rate, float) and frame_rate > 0, (
        f"{frame_rate=}. Must be float > 0"
    )
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(h265, bool), f"{h265=}. Must be bool"
    assert isinstance(high_quality, bool), f"{high_quality=}. Must be bool"
    assert isinstance(iframe_only, bool), f"{iframe_only=}. Must be bool"
    assert isinstance(deinterlace, bool), f"{deinterlace=}. Must be bool"
    assert isinstance(auto_bright, bool), f"{auto_bright=}. Must be bool"
    assert isinstance(normalise, bool), f"{normalise=}. Must be bool"
    assert isinstance(white_balance, bool), f"{white_balance=}. Must be bool"
    assert isinstance(denoise, bool), f"{denoise=}. Must be bool"
    assert isinstance(sharpen, bool), f"{sharpen=}. Must be bool"
    assert isinstance(filters_off, bool), f"{filters_off=}. Must be bool"
    assert isinstance(black_border, bool), f"{black_border=}. Must be bool"
    assert isinstance(encode_10bit, bool), f"{encode_10bit=}, Must be bool"
    assert isinstance(mkv_container, bool), f"{mkv_container=}. Must be bool"
    assert isinstance(task_def, Task_Def) or task_def is None, (
        f"{task_def=}. Must be Task_Def or None"
    )

    if deinterlace and not interlaced:
        return (
            -1,
            "Cannot force deinterlace when input video is progressive. Input is already progressive.",
        )

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"
    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"
    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    file_extension = "mkv" if mkv_container else "mp4"
    _, input_file_name, _ = file_handler.split_file_path(input_file)
    output_file = file_handler.file_join(
        output_folder, f"{input_file_name}.{file_extension}"
    )

    if output_file == input_file:
        output_file = file_handler.file_join(
            output_folder, f"{input_file_name}_out.{file_extension}"
        )

    if not utils.Is_Complied():
        print(
            "DBG Trans_H26x"
            f" {input_file=} {frame_rate=} {width=} {height=} {interlaced=} {bottom_field_first=} ER"
            f" {'5M' if height <= 576 else '35M'=}"
        )

    gop_size = 1 if iframe_only else (15 if frame_rate == 25 else 18)

    encoder = "libx265" if h265 else "libx264"
    quality_preset = "slow" if high_quality else "superfast"

    if (width, height) in Standard_Resolutions():
        scale_width = -1
        scale_height = -1
    else:
        scale_width = width
        scale_height = height

    video_filters_arg = Build_Video_Filters(
        auto_bright=auto_bright,
        normalise=normalise,
        white_balance=white_balance,
        denoise=denoise,
        sharpen=sharpen,
        filters_off=filters_off,
        black_border=black_border,
        target_width=scale_width,
        target_height=scale_height,
        deinterlace_video=deinterlace,
        include_dvd_interlacing=False,
    )

    interlaced_flags = []

    if not deinterlace and interlaced:
        interlaced_flags = [
            "-flags:v:0",
            "+ilme+ildct",
            "-alternate_scan:v:0",
            "1",
        ]

        field_order_filter = f"fieldorder={'bff' if bottom_field_first else 'tff'}"

        if video_filters_arg:
            video_filters_arg[1] = f"{field_order_filter},{video_filters_arg[1]}"
        else:
            video_filters_arg = ["-vf", field_order_filter]

    pixel_format = "yuv422p10le" if encode_10bit else "yuv420p"

    command = [
        sys_consts.FFMPG,
        "-fflags",
        "+genpts",
        "-i",
        input_file,
        "-vsync",
        "cfr",
        "-max_muxing_queue_size",
        "9999",
        *video_filters_arg,
        *interlaced_flags,
        "-r",
        str(frame_rate),
        "-c:v",
        encoder,
        "-sn",  # Remove titles
        "-pix_fmt",
        pixel_format,
        "-crf",
        "19" if not h265 else "25",
        "-preset",
        quality_preset,
        "-c:a",
        "ac3",
        "-b:a",
        "256k",
        "-muxrate",
        "48M",
        "-bufsize",
        "48M",
        "-g",
        f"{gop_size}",
        "-keyint_min",
        f"{gop_size}",
        "-sc_threshold",
        "0",
        "-threads",
        "0",
        output_file,
        "-y",
    ]

    if task_def:  # Run in the background
        background_task_qmanager = Task_QManager()

        background_task_qmanager.submit_task(
            worker_function=Execute_Check_Output,
            commands=command,
            debug=False,
            stderr_to_stdout=False,
            task_id=task_def.task_id,
            started_callback=task_def.started_callback,
            progress_callback=task_def.progress_callback,
            finished_callback=task_def.finished_callback,
            error_callback=task_def.error_callback,
            aborted_callback=task_def.aborted_callback,
        )

        return 0, output_file

    else:
        result, message = Execute_Check_Output(
            commands=command, debug=True, stderr_to_stdout=False
        )
        if result == -1:
            return -1, message

    return 1, output_file


def Convert_To_PNG_Stream(
    image_filename: str, width: int, height: int, keep_aspect_ratio: bool = True
) -> tuple[int, bytes]:
    """
    Converts an image file to PNG format, resizing it, and returns the PNG data as bytes.

    Args:
        image_filename (str): The filename of the input image.
        width (int): The width for resizing.
        height (int): The height for resizing.
        keep_aspect_ratio (bool): Whether to keep the aspect ratio.

    Returns:
        tuple(int, bytes):
            - arg1: 1 (ok) or -1 (error)
            - arg2: The image data as a byte string (PNG format) on success, empty bytes on error
    """
    assert isinstance(image_filename, str) and image_filename.strip() != "", (
        f"{image_filename=}. Must be a non-empty str"
    )
    assert isinstance(width, int) and width > 0, f"{width=} . Must be an int > 0"
    assert isinstance(height, int) and height > 0, f"{height=} . Must be an int > 0"
    assert isinstance(keep_aspect_ratio, bool), f"{keep_aspect_ratio=}. Must be a bool"

    file_handler = file_utils.File()

    if not file_handler.file_exists(image_filename):
        return -1, f"File not found: {image_filename}".encode("utf-8")

    command = [
        sys_consts.CONVERT,
        image_filename,
        "-resize",
        f"{width}x{height} {'>' if keep_aspect_ratio else ''}>",
        "png:-",
    ]

    try:
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                return 1, stdout
            else:
                print(f"Error converting image: {stderr.decode()}")
                return -1, f"Error converting image: {stderr.decode()}".encode("utf-8")
    except Exception as e:
        return -1, f"Unexpected error: {e}".encode("utf-8")


def Write_Image_On_Image(
    base_image_data: bytes,
    overlay_image_data: bytes,
    x: int,
    y: int,
    gravity: str = Gravity.NORTHWEST.value,
) -> tuple[int, bytes]:
    """
    Overlays an image (provided as bytes) onto another base image (provided as bytes)
    using ImageMagick and returns the modified image as a byte string (PNG format).

    Args:
        base_image_data (bytes): The base image data in bytes format
        overlay_image_data (bytes): The overlay image data in bytes format
        x (int): The x-coordinate
        y (int): The y-coordinate
        gravity (str): The gravity positioning of the overlay image ('northwest', 'center', etc.)

    Returns:
        tuple(int, bytes):
            - arg1: 1 (ok) or -1 (error)
            - arg2: The modified image data as a byte string (PNG format) on success, empty bytes on error
    """
    assert isinstance(base_image_data, bytes) and base_image_data.strip() != "", (
        f"{base_image_data=}. Must be a non-empty bytes"
    )
    assert isinstance(overlay_image_data, bytes) and base_image_data.strip() != "", (
        f"{base_image_data=}. Must be a non-empty bytes"
    )
    assert isinstance(x, int) and x >= 0, f"{x=}. Must be a non-negative int"
    assert isinstance(y, int) and y >= 0, f"{y=}. Must be a non-negative int"
    assert isinstance(gravity, str) and gravity.strip().lower() in [
        member.value for member in Gravity
    ], (
        f"{gravity=} must be a valid gravity string from {[member.value for member in Gravity]}"
    )

    try:
        SEPARATOR: Final[bytes] = b"##ImageSeparator##"

        stdin_data = base_image_data + SEPARATOR + overlay_image_data

        command = [
            sys_consts.CONVERT,
            "-gravity",
            gravity,
            "-page",
            f"+{x}+{y}",
            "-",
            "png:-",
        ]

        # Execute the command with input and output pipes
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=stdin_data)

        if process.returncode == 0:
            return 1, stdout
        else:
            return -1, f"Failed To Overlay An Image (Err 1) {stderr.decode()}".encode(
                "utf-8"
            )
    except Exception as e:
        return -1, f"Failed To Overlay An Image (Err 2) {e}".encode("utf-8")


def Write_Text_On_Image(
    image_data: bytes,
    text: str,
    x: int,
    y: int,
    font: str,
    pointsize: int,
    color: str,
    gravity: str = Gravity.NORTHWEST.value,
) -> tuple[int, bytes]:
    """
    Writes text on an image (provided as bytes) and returns the modified image as a byte string (PNG format).

    Args:
        image_data (bytes): The image data in bytes format (e.g., from reading a file)
        text (str): The text to be written
        x (int): The x co-ordinate
        y (int): The y co-ordinate
        font (str): The font of the text
        pointsize (int): The point size of the text
        color (str): The color of the text
        gravity: (str): The gravity positioning of the text

    Returns:
        tuple(int, bytes):
            - arg1: 1, ok, -1, error.
            - arg2: The modified image data as a byte string (PNG format) on success empty bytes on error.
    """

    assert isinstance(gravity, str) and gravity.strip().lower() in [
        member.value for member in Gravity
    ], (
        f"{gravity=} must be a valid gravity string from {[member.value for member in Gravity]}"
    )

    assert isinstance(image_data, bytes) and image_data != b"", (
        f"{image_data=}. Must be non-empty bytes"
    )
    assert isinstance(text, str), f"{text=}. Must be str"
    assert isinstance(font, str) and font.strip() != "", (
        f"{font=}. Must be non-empty str"
    )
    assert isinstance(x, int) and x > 0, f"{x=}. Must be int > 0"
    assert isinstance(pointsize, int) and pointsize > 0, (
        f"{pointsize=}. Must be int > 0"
    )
    assert isinstance(y, int) and y > 0, f"{y=}. Must be int > 0"

    assert isinstance(color, str) and color.upper() in Color.__members__, (
        f"{color=}. Must be one of {[member.name for member in Color]}"
    )

    try:
        # Construct ImageMagick command (pipe image data as input)
        command = [
            sys_consts.CONVERT,
            "-",  # Read input from standard input (pipe)
            "-background",
            "none",  # Transparent background
            "-fill",
            color,
            "-gravity",
            gravity,
            "-font",
            font,
            "-pointsize",
            f"{pointsize}",
            "-annotate",
            f"+{x}+{y}",
            f"{text}",
            "PNG:-",  # Output to standard output (pipe)
        ]

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Send the image data directly
        stdout, stderr = process.communicate(input=image_data)

        if process.returncode != 0:
            return -1, stderr

        return 1, stdout

    except Exception as e:
        return -1, f"Error processing image: {str(e)}".encode("utf-8")


def Write_Text_On_File(
    input_file: str, text: str, x: int, y: int, font: str, pointsize: int, color: str
) -> tuple[int, str]:
    """
    Writes text on a file

    Args:
        input_file (str): The file on which the text will be written
        text (str): The text to be written
        x (int): The x co-ordinate
        y (int): The y co-ordinate
        font (str): The font of the text
        pointsize (int): The point size of the text
        color (str): The color of the text

    Returns:
        tuple[int,str]:
        - arg1: 1 OK, -1 Error,
        - arg2: Error message or "" if ok
    """
    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be non-empty str"
    )
    assert isinstance(text, str), f"{text=}. Must be str"
    assert isinstance(font, str) and font.strip() != "", (
        f"{font=}. Must be non-empty str"
    )
    assert isinstance(x, int) and x > 0, f"{x=}. Must be int > 0"
    assert isinstance(pointsize, int) and pointsize > 0, (
        f"{pointsize=}. Must be int > 0"
    )
    assert isinstance(y, int) and y > 0, f"{y=}. Must be int > 0"

    assert isinstance(color, str) and color.upper() in Color.__members__, (
        f"{color=}. Must be one of {[member.name for member in Color]}"
    )

    if not os.path.exists(input_file):
        return -1, f"{input_file} Does Not Exist!"

    command = [
        sys_consts.CONVERT,
        input_file,
        "-fill",
        color,
        "-gravity",
        "NorthWest",
        "-font",
        font,
        "-pointsize",
        f"{pointsize}",
        "-annotate",
        f"+{x}+{y}",
        text,
        input_file,
    ]

    return Execute_Check_Output(commands=command)


def Get_Text_Dims(text: str, font: str, pointsize: int) -> tuple[int, int]:
    """
    Gets the text dimensions in pixels

    Args:
        text (str): The text string to be measured
        font (str): The font of the text
        pointsize (int): The text point size

    Returns:
        tuple[int,int]: The width and height of the text. Both are -1 if there is an error
    """
    assert isinstance(text, str), f"{text=}. Must be str"
    assert isinstance(font, str) and font.strip() != "", (
        f"{font=}. Must be noon-empty str"
    )
    assert isinstance(pointsize, int) and pointsize > 0, (
        f"{pointsize=}. Must be int > 0"
    )

    # Run the ImageMagick command to measure the text
    result, message = Execute_Check_Output(
        commands=[
            sys_consts.CONVERT,
            "-background",
            "none",
            "-fill",
            "black",
            "-font",
            font,
            "-pointsize",
            str(pointsize),
            "label:" + text,
            "-format",
            "%[fx:w]x%[fx:h]",
            "info:",
        ],
        debug=False,
    )

    if result == -1:
        return -1, -1

    # Convert the message to width and height
    dimensions = message.strip().split("x")

    if (
        not dimensions
        or len(dimensions) != 2
        or dimensions[0].strip() == ""
        or dimensions[1].strip() == ""
    ):  # Very rare error cases
        return -1, -1

    width = int(dimensions[0])
    height = int(dimensions[1])

    return width, height


def Get_Codec(input_file: str) -> tuple[int, str]:
    """
    Get the codec name of the video file using FFprobe.

    Args:
        input_file (str): Path to the input video file.

    Returns:
        tuple[int, str]:
        - arg 1: Status code. Returns 1 if the codec name was obtained successfully, -1 otherwise.
        - arg 2: Codec name if obtained successfully, otherwise error message

    """
    assert isinstance(input_file, str) and input_file.strip() != "", (
        "Input file must be a string."
    )

    commands = [
        sys_consts.FFPROBE,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        input_file,
    ]

    result, output = Execute_Check_Output(commands)

    if result == -1:
        return -1, "Failed To Get Codec Name!"

    return 1, output.strip()


def Cut_Video(cut_video_def: Cut_Video_Def) -> tuple[int, str]:
    """
    Attempts a frame accurate cut and join of a video based on start and end cut frames.

    Args:
        cut_video_def(Cut_Video_Def): Cut video definition


    Returns:
        tuple[int, str]:
        - arg 1: Status code. Returns 1 if cut_video was successful, -1 otherwise.
        - arg 2: Empty string if all good, otherwise error message
    """

    ##### Helper
    def _get_GOP_info(
        input_file: str,
        start_time: float,
    ) -> tuple[int, str, float, float]:
        """Get the GOP Block I frame start and end times around the start time video file

        Args:
            input_file (str): The input file
            start_time (float): The start time

        Returns:
            tuple[int, str, float, float]: The result (1 if ok, -1 if not),
                                            the message ("" or "stream" if all iframes, if ok, error message if not )
                                            the start time of the GOP
                                            the end time of the GOP
        """

        assert isinstance(input_file, str) and input_file.strip() != "", (
            f"{input_file=}. Must be non-empty str"
        )
        assert isinstance(start_time, float) and start_time >= 0.0, (
            f"{start_time=}. Must be int >= 0"
        )

        search_window = 5  # Initial search window (seconds)
        current_search_start = max(0.0, start_time - search_window)
        found_iframe = False
        start_i_time = -1.0
        end_i_time = -1.0
        stream_copy = False
        max_searches = (
            10  # Works out at 50 seconds if no I-frames found not likely to find any
        )
        search_count = 0

        # Find the nearest I-frame before start_time
        while (
            not found_iframe
            and current_search_start >= 0.0
            and search_count < max_searches
        ):
            commands = [
                sys_consts.FFPROBE,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_frames",
                "-of",
                "json",
                "-read_intervals",
                f"{current_search_start}%+{search_window}",
                input_file,
            ]

            result, message = Execute_Check_Output(
                commands, debug=False, stderr_to_stdout=True
            )

            if result == -1:
                return -1, message, -1.0, -1.0

            try:
                iframe_data = json.loads(message)
            except json.JSONDecodeError:
                return -1, "JSON Decode Error!", -1.0, -1.0

            try:
                i_frames = [
                    frame
                    for frame in iframe_data["frames"]
                    if frame["pict_type"] == "I" and frame["key_frame"] == 1
                ]

                if not i_frames:
                    break

                i_frame = i_frames[0]
                I_Pos = float(i_frame["pkt_pos"])
                I_Pts = float(i_frame["pts"])

                for frame in reversed(iframe_data["frames"]):  # Search backwards
                    if (
                        frame["pict_type"] == "I"
                        and frame["key_frame"] == 1
                        and float(frame["pts_time"]) <= start_time
                    ):
                        start_i_time = float(frame["pts_time"])
                        found_iframe = True

                        stream_copy = all(
                            frame["pict_type"] == "I" and frame["key_frame"] == 1
                            for frame in iframe_data["frames"]
                        )

                        break
                    elif frame["pict_type"] == "B":
                        B_pos = float(frame["pkt_pos"])
                        B_pts = float(frame["pts"])

                        if B_pos > I_Pos and B_pts < I_Pts:
                            return (
                                -1,
                                "Open GOP detected!",
                                -1.0,
                                -1.0,
                            )  # Open GOP detected

                    current_search_start = max(
                        0.0, current_search_start - search_window
                    )
            except (KeyError, KeyError):
                return -1, "Failed to get head I-frame!", -1.0, -1.0

            search_count += 1

        # Get video duration
        commands = [
            sys_consts.FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            input_file,
        ]

        result, message = Execute_Check_Output(
            commands, debug=False, stderr_to_stdout=True
        )

        if result == -1:
            return -1, message, -1.0, -1.0

        try:
            video_duration = float(json.loads(message)["format"]["duration"])
        except json.JSONDecodeError:
            return -1, "JSON Decode Error!", -1.0, -1.0
        except (ValueError, KeyError):
            return -1, "Failed to get video duration!", -1.0, -1.0

        found_iframe = False
        current_search_start = start_i_time

        # Find the nearest I-frame after the start_time
        while not found_iframe and current_search_start < video_duration:
            commands = [
                sys_consts.FFPROBE,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_frames",
                "-of",
                "json",
                "-read_intervals",
                f"{current_search_start}%+{search_window}",
                input_file,
            ]

            result, message = Execute_Check_Output(
                commands, debug=False, stderr_to_stdout=True
            )

            if result == -1:
                return -1, message, -1.0, -1.0

            try:
                iframe_data = json.loads(message)
            except json.JSONDecodeError:
                return -1, "JSON Decode Error!", -1.0, -1.0

            try:
                i_frames = [
                    frame
                    for frame in iframe_data["frames"]
                    if frame["pict_type"] == "I" and frame["key_frame"] == 1
                ]

                if not i_frames:
                    break

                i_frame = i_frames[0]
                I_Pos = float(i_frame["pkt_pos"])
                I_Pts = float(i_frame["pts"])

                for frame in iframe_data["frames"]:  # Search forwards
                    if (
                        frame["pict_type"] == "I"
                        and frame["key_frame"] == 1
                        and float(frame["pts_time"]) > start_time
                    ):
                        end_i_time = float(frame["pts_time"])
                        found_iframe = True
                        stream_copy = all(
                            frame["pict_type"] == "I" and frame["key_frame"] == 1
                            for frame in iframe_data["frames"]
                        )

                        break

                    elif frame["pict_type"] == "B":
                        B_pos = float(frame["pkt_pos"])
                        B_pts = float(frame["pts"])

                        if B_pos > I_Pos and B_pts < I_Pts:
                            return (
                                -1,
                                "Open GOP detected!",
                                -1.0,
                                -1.0,
                            )  # Open GOP detected

                if found_iframe:
                    break
            except (KeyError, ValueError):
                return -1, "Failed to get tail I-frame!", -1.0, -1.0

            current_search_start += search_window

        if end_i_time > 0 and start_i_time < 0:
            start_i_time = 0.0

        return (
            1,
            "stream" if stream_copy else "",
            start_i_time,
            end_i_time,
        )

    def stream_copy_segment(
        input_file: str,
        output_file: str,
        start_time: float,
        end_time: float,
    ) -> tuple[int, str]:
        """
        Extracts a segment from an input video file using stream copy.

        Args:
            input_file (str): The input video file to extract the segment from.
            output_file (str): The output file where the segment will be saved.
            start_time (float): The start time of the segment.

        Returns:
            tuple[int, Optional[float]]: tuple containing result code and

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.

        """

        assert isinstance(input_file, str) and input_file.strip() != "", (
            f"{input_file=}. Must be a non-empty str"
        )
        assert isinstance(output_file, str) and output_file.strip() != "", (
            f"{output_file=}. Must be a non-empty str"
        )
        assert isinstance(start_time, float) and start_time >= 0, (
            f"{start_time=}. Must be float >= 0"
        )
        assert (
            isinstance(end_time, float) and end_time >= 0.0 and end_time > start_time
        ), f"{end_time=}. Must be float >= 0.0 and > {start_time=}"

        command = [
            sys_consts.FFMPG,
            "-i",
            input_file,
            "-ss",
            f"{start_time}",
            "-t",
            f"{end_time - start_time}",
            "-c",
            "copy",
            "-threads",
            "0",
            output_file,
            "-y",
        ]

        result, output = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, output  # Output has an error message

        return 1, ""

    def reencode_segment(
        input_file: str,
        output_file: str,
        encoder_settings: Encoding_Details,
        start_time: float,
        end_time: float,
        gop_size: int,
    ) -> tuple[int, str]:
        """
        Reencodes a segment from an input video file with specific settings.

        Args:
            input_file (str): The input video file to extract the segment from.
            output_file (str): The output file where the segment will be saved.
            encoder_settings (Encoding_Details): The encoding settings used in the segment.
            start_time (float): The start time of the segment.
            end_time (float): The end time of the segment.
            gop_size (int): The desired GOP (Group of Pictures) size.

        Returns:
            Tuple[int, str]: A tuple containing the status code and a message.

            - If the status code is 1, the operation was successful.
            - If the status code is -1, an error occurred, and the message provides details.
        """

        assert isinstance(input_file, str) and input_file.strip() != "", (
            f"{input_file=}. Must be a non-empty  str"
        )
        assert isinstance(output_file, str) and output_file.strip() != "", (
            f"{output_file=}. Must be a non-empty str"
        )
        assert isinstance(encoder_settings, Encoding_Details), (
            f"{encoder_settings=}. Must be Encoding_Details"
        )
        assert isinstance(start_time, float) and start_time >= 0.0, (
            f"{start_time=}. Must be float >= 0.0"
        )
        assert (
            isinstance(end_time, float) and end_time > 0.0 and end_time > start_time
        ), f"{end_time=}. Must be float > 0.0 and > {start_time=}"
        assert isinstance(gop_size, int) and gop_size > 0, (
            f"{gop_size=}. Must be int > 0"
        )

        if encoder_settings.video_scan_type == "interlaced":
            field_order = f"fieldorder={encoder_settings.video_scan_order}"

            video_filter = [
                "-vf",
                f"{field_order}",
                "-flags:v:0",  # video flags for the first video stream
                "+ilme+ildct",  # include interlaced motion estimation and interlaced DCT
                "-alternate_scan:v:0",  # set alternate scan for first video stream (interlace)
                "1",  # alternate scan value is 1,
            ]
        else:
            video_filter = []

        command = [
            sys_consts.FFMPG,
            "-ss",
            f"{start_time}",
            "-fflags",
            "+genpts",
            "-i",
            input_file,
            "-vsync",
            "cfr",
            *video_filter,
            "-tune",
            "fastdecode",
            "-t",
            f"{end_time - start_time}",
            "-r",
            str(encoder_settings.video_frame_rate),
            "-g",
            str(gop_size),
            "-keyint_min",
            str(gop_size),
            "-sc_threshold",
            "0",
            "-c:v",
            encoder_settings.video_codec,
            "-crf",
            "18",
            "-preset",
            "slow",
            "-b:v",
            str(encoder_settings.video_bitrate),
            "-pix_fmt",
            encoder_settings.video_pix_fmt,
            "-s",
            f"{encoder_settings.video_width}x{encoder_settings.video_height}",
            "-c:a",
            "copy",
            "-threads",
            "0",
            output_file,
            "-y",
        ]

        result, message = Execute_Check_Output(
            commands=command, debug=False, stderr_to_stdout=True
        )

        if result == -1:
            return -1, f"Failed to Transcode ({message=}): {input_file=}"

        return 1, ""

    ##### Main
    assert isinstance(cut_video_def, Cut_Video_Def), (
        f"{cut_video_def=}. Must be an instance of Cut_Video_Def"
    )

    file_handler = file_utils.File()
    encoder_settings = Get_File_Encoding_Info(cut_video_def.input_file)
    if encoder_settings.error:
        return -1, f"Failed to get encoder settings: {encoder_settings.error}"

    if encoder_settings.video_frame_rate not in (
        sys_consts.PAL_SPECS.frame_rate,
        sys_consts.NTSC_SPECS.frame_rate,
        sys_consts.PAL_SPECS.field_rate,
        sys_consts.NTSC_SPECS.field_rate,
        30,
    ):
        return -1, f"Frame Rate Error: {encoder_settings.video_frame_rate}"

    start_time = cut_video_def.start_cut / cut_video_def.frame_rate
    end_time = cut_video_def.end_cut / cut_video_def.frame_rate
    frame_time = 1 / cut_video_def.frame_rate
    cut_duration = end_time - start_time

    result, message, start_start_rencode_time, start_end_rencode_time = _get_GOP_info(
        input_file=cut_video_def.input_file,
        start_time=start_time,
    )

    if result == -1:
        return result, message

    result, message, end_start_rencode_time, end_end_rencode_time = _get_GOP_info(
        input_file=cut_video_def.input_file,
        start_time=end_time,
    )

    # Need to snap to the nearest I frames around the rencode start and end times - hence 2 frame offset
    # Note: 2 frames may not always be enough, and this may need revisiting.
    stream_start = (
        0.0
        if start_end_rencode_time - (2 * frame_time) < 0
        else start_end_rencode_time - (2 * frame_time)
    )

    stream_end = end_start_rencode_time - (2 * frame_time)

    if result == -1:
        return result, message

    if message == "stream":  # All i frames like DV video make for a stream copy cut
        result, message = stream_copy_segment(
            input_file=cut_video_def.input_file,
            output_file=cut_video_def.output_file,
            start_time=start_time,
            end_time=end_time,
        )

        if result == -1:
            return -1, message
    else:  # We have GOPS with I,P,B frames and need to reencode start and end GOP blocks to cut accurately
        concat_files = []
        _, _, input_extension = file_handler.split_file_path(cut_video_def.input_file)
        output_dir, output_file_name, _ = file_handler.split_file_path(
            cut_video_def.output_file
        )

        start_offset = (start_time - start_start_rencode_time) + frame_time

        if start_offset < 0:
            return -1, f"Did not find start I frame  {start_offset} "

        ##### Reencode Start GOP Block
        if start_end_rencode_time - start_start_rencode_time > 0:
            reencode_start_seg_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"reencode_start_segment_{cut_video_def.tag}",
                ext=input_extension,
            )

            result, message = reencode_segment(
                input_file=cut_video_def.input_file,
                output_file=reencode_start_seg_file,
                encoder_settings=encoder_settings,
                start_time=start_start_rencode_time,
                end_time=start_end_rencode_time,
                gop_size=1,  # Force all frames to I frame in the GOP block, so we can cut in and out where we want,
            )

            if result == -1:
                return -1, message

            concat_files.append(reencode_start_seg_file)
        else:
            print("Warning: Skipping zero-duration re-encode start segment.")

        ##### Make a stream copy of the untouched oart of the file
        if end_start_rencode_time - start_end_rencode_time > 0:
            streamcopy_seg_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"stream_copy_segment_{cut_video_def.tag}",
                ext=input_extension,
            )

            result, message = stream_copy_segment(
                input_file=cut_video_def.input_file,
                output_file=streamcopy_seg_file,
                start_time=stream_start,
                end_time=stream_end,
            )

            if result == -1:
                return -1, message

            concat_files.append(streamcopy_seg_file)
        else:
            print("Warning: Skipping zero-duration stream copy segment.")

        ##### Reencode End GOP Block
        if end_end_rencode_time - end_start_rencode_time > 0:
            reencode_end_seg_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"reencode_end_segment_{cut_video_def.tag}",
                ext=input_extension,
            )

            result, message = reencode_segment(
                input_file=cut_video_def.input_file,
                output_file=reencode_end_seg_file,
                encoder_settings=encoder_settings,
                start_time=end_start_rencode_time,
                end_time=end_end_rencode_time,
                gop_size=1,  # Force all frames to I frame in the GOP block, so we can cut in and out where we want,
            )

            if result == -1:
                return -1, message

            concat_files.append(reencode_end_seg_file)
        else:
            print("Warning: Skipping zero-duration re-encode end segment.")

        if concat_files:
            temp_output_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"{output_file_name}_temp",
                ext=input_extension,
            )

            # Join re-encoded_start segment, stream_copy segment and re-encoded end segment to make the final frame
            # accurate cut file with nearly no loss
            result, message, _ = Concatenate_Videos(
                video_files=concat_files,
                output_file=temp_output_file,
                delete_temp_files=True,
                debug=False,
            )

            if result == -1:
                return -1, message

            result, message = stream_copy_segment(
                input_file=temp_output_file,
                output_file=cut_video_def.output_file,
                start_time=start_offset,
                end_time=start_offset + cut_duration + frame_time,
            )

            if result == -1:
                return -1, message

            if file_handler.remove_file(temp_output_file) == -1:
                return -1, f"Failed to remove {temp_output_file}"

    return 1, ""


def Frame_Num_To_FFMPEG_Time(frame_num: int, frame_rate: float) -> str:
    """
    Converts a frame number to an FFmpeg offset time string in the format "hh:mm:ss.mmm".

    Args:
        frame_num: An integer representing the frame number to convert.
        frame_rate: The video frame rate.

    Returns:
        A string representing the FFmpeg offset time in the format "hh:mm:ss.mmm".
    """

    assert isinstance(frame_num, int) and frame_num >= 0, (
        f"{frame_num=}. Must be int >= 0"
    )
    assert isinstance(frame_rate, float) and frame_rate > 0, (
        f"{frame_rate=}. Must be float > 0"
    )

    seconds = frame_num / frame_rate
    milliseconds = int(seconds * 1000)

    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    seconds = milliseconds // 1000
    milliseconds %= 1000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def Seconds_To_FFMPEG_Time(seconds: float) -> str:
    """Converts seconds to the FFMPEG offset format HH:MM:SS.mmm

    Args:
        seconds (float): The number of seconds to convert

    Returns:
        A string representing the FFmpeg offset time in the format "hh:mm:ss.mmm".

    """
    assert isinstance(seconds, float) and seconds >= 0.0, (
        f"{seconds=}. Must be float >= 0.0"
    )

    milliseconds = int(seconds * 1000)
    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds %= 60
    hours = minutes // 60
    minutes %= 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def Split_Large_Video(
    source: str, output_folder: str, desired_chunk_size_gb: int
) -> tuple[int, str]:
    """
    Splits a large video file into smaller chunks.

    Args:
        source (str): The source path of the video file to split.
        output_folder (str): The folder where the split video files will be saved.
        desired_chunk_size_gb (int): The maximum size (in GB) for each split video chunk.

    Returns:
        tuple[int, str]:
            - arg1: 1 for success, -1 for failure.
            - arg2: An error message, or a list of chunk files delimitered by | if arg 1 is 1.
    """
    assert isinstance(source, str) and source.strip(), (
        f"Invalid source video path: {source}"
    )
    assert isinstance(output_folder, str) and output_folder.strip(), (
        f"Invalid output folder: {output_folder}"
    )
    assert isinstance(desired_chunk_size_gb, int) and desired_chunk_size_gb > 0, (
        "Invalid max_size_gb"
    )

    if not os.path.exists(source):
        return -1, f"Video file not found: {source}"

    if os.path.isdir(source):
        return -1, f"Source path is a directory: {source}"

    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        chunk_file_list = []

        min_chunk_duration_s = 180  # Minimum chunk duration is 3 minutes

        file_handler = file_utils.File()

        _, source_name, source_extn = file_handler.split_file_path(source)

        encoding_info = Get_File_Encoding_Info(source)

        if encoding_info.error:
            return -1, encoding_info.error

        if not encoding_info.video_duration or encoding_info.video_duration <= 0:
            return (
                -1,
                f"Invalid or zero video duration detected for {source}. Cannot split.",
            )
        if not encoding_info.video_frame_rate or encoding_info.video_frame_rate <= 0:
            return (
                -1,
                f"Invalid or zero video frame rate detected for {source}. Cannot split.",
            )
        if not encoding_info.video_frame_count or encoding_info.video_frame_count <= 0:
            return (
                -1,
                f"Invalid or zero video frame count detected for {source}. Cannot split.",
            )

        file_size = os.path.getsize(source)

        num_chunks = math.ceil(
            file_size / (desired_chunk_size_gb * (1024**3))
        )  # Convert GB to bytes

        # Ensure at least one chunk even for small files
        if num_chunks == 0:
            num_chunks = 1

        # Adjust chunking to ensure the last chunk isn't too short.

        chunk_adjust = True

        frames_per_min_chunk = encoding_info.video_frame_rate * min_chunk_duration_s

        if frames_per_min_chunk > 0:
            max_possible_chunks = (
                encoding_info.video_frame_count // frames_per_min_chunk
            )

            if max_possible_chunks == 0:  # If video is shorter than min_chunk_duration
                max_possible_chunks = 1
            else:
                max_possible_chunks += 2  # Add buffer

        else:  # Should not happen if video_frame_rate check passed
            max_possible_chunks = 1

        while chunk_adjust and num_chunks <= max_possible_chunks:
            chunk_frames_per_chunk = encoding_info.video_frame_count / num_chunks

            # Calculate duration of the very last chunk based on adjusted num_chunks
            last_chunk_start_frame = int((num_chunks - 1) * chunk_frames_per_chunk)
            last_chunk_end_frame = (
                encoding_info.video_frame_count
            )  # Always goes to end of video

            last_chunk_num_frames = last_chunk_end_frame - last_chunk_start_frame

            # Ensure last_chunk_num_frames is not negative or zero if division resulted in weirdness
            if last_chunk_num_frames <= 0:
                last_chunk_duration = 0.0
            else:
                last_chunk_duration = (
                    last_chunk_num_frames / encoding_info.video_frame_rate
                )

            if (
                last_chunk_duration < min_chunk_duration_s
                and num_chunks
                < max_possible_chunks  # Only increment if we haven't hit max allowed chunks
            ):
                num_chunks += 1
            else:
                chunk_adjust = False  # Condition met or max chunks reached

        if num_chunks < 1:
            num_chunks = 1  # Ensure at least one chunk if video is valid

        # Recalculate exact chunk_frames for final iteration based on adjusted num_chunks
        chunk_frames = encoding_info.video_frame_count / num_chunks

        for chunk_index in range(num_chunks):
            start_frame = int(chunk_index * chunk_frames)

            # Ensure end_frame does not exceed total frames for the last chunk
            end_frame = int(
                (chunk_index + 1) * chunk_frames
                if chunk_index < num_chunks - 1
                else encoding_info.video_frame_count
            )

            if (
                start_frame >= end_frame and chunk_index < num_chunks - 1
            ):  # Check for zero-length chunk
                continue

            chunk_file = file_handler.file_join(
                output_folder, f"{source_name}_{chunk_index + 1}", source_extn
            )

            chunk_file_list.append(chunk_file)

            result, message = Cut_Video(
                Cut_Video_Def(
                    input_file=source,
                    output_file=chunk_file,
                    start_cut=start_frame,
                    end_cut=end_frame,
                    frame_rate=encoding_info.video_frame_rate,
                    tag=f"chunk_{chunk_index}",
                )
            )

            if result == -1:
                # Clean up any already created chunks if one fails
                for created_chunk in chunk_file_list:
                    if os.path.exists(created_chunk):
                        os.remove(created_chunk)
                return -1, f"Failed to cut video chunk {chunk_index + 1}: {message}"

        if not chunk_file_list:
            return -1, "No video chunks were created."

        return 1, "|".join(chunk_file_list)

    except Exception as e:
        return -1, f"An unexpected error occurred during video splitting: {e}"


def Stream_Optimise(output_file: str) -> tuple[int, str]:
    """
    Optimizes a video file for streaming.

    Args:
        output_file (str): The path to the video file to be optimized.

    Returns:
        tuple[int, str]:
        - arg 1:  1 if the optimization was successful, and -1 otherwise
        - arg 2: If the optimization fails, the message will contain an error otherwise "".
    """
    assert isinstance(output_file, str) and output_file.strip() != "", (
        f"{output_file=}. Must be a non-empty string."
    )

    command = [
        sys_consts.FFMPG,
        "-y",
        "-i",
        output_file,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        "-threads",
        "0",
    ]

    result, message = Execute_Check_Output(command)

    if result == -1:
        return -1, message

    return 1, ""


def Get_DVD_Dims(aspect_ratio: str, dvd_format: str) -> Dvd_Dims:
    """
    Returns the DVD image dimensions. The hard-coded values are  mandated by the dvd_format and the
    aspect ratio and must not be changed.  PAL is 720 x 576, and NTSC is 720 x 480 and is always stored
    that way on a DVD. But the display aspect ratio can be flagged on a DVD (PAL is 1024 x 576 and NTSC is
    850x480), but it is not stored that way on the DVD

    Args:
        aspect_ratio (str): Must be AR43 | AR 169 from sys_consts
        dvd_format (str): Must be PAL or NTSC from sys_consts

    Returns:
        dvd_dims : Dimensions of the DVD

    """
    assert isinstance(aspect_ratio, str) and aspect_ratio.upper() in (
        sys_consts.AR43,
        sys_consts.AR169,
    ), f"{aspect_ratio=}. Must be AR43 | AR169"
    assert isinstance(dvd_format, str) and dvd_format.upper() in (
        sys_consts.PAL,
        sys_consts.NTSC,
    )

    if dvd_format.upper() == sys_consts.NTSC:
        if aspect_ratio.upper() == sys_consts.AR169:
            return Dvd_Dims(
                storage_width=sys_consts.NTSC_SPECS.width_43,
                storage_height=sys_consts.NTSC_SPECS.height_43,
                display_width=sys_consts.NTSC_SPECS.width_169,
                display_height=sys_consts.NTSC_SPECS.height_169,
            )

        else:  # 4:3
            return Dvd_Dims(
                storage_width=sys_consts.NTSC_SPECS.width_43,
                storage_height=sys_consts.NTSC_SPECS.height_43,
                display_width=sys_consts.NTSC_SPECS.width_43,
                display_height=sys_consts.NTSC_SPECS.height_43,
            )
    else:  # PAL
        if aspect_ratio.upper() == sys_consts.AR169:
            return Dvd_Dims(
                storage_width=sys_consts.PAL_SPECS.width_43,
                storage_height=sys_consts.PAL_SPECS.height_43,
                display_width=sys_consts.PAL_SPECS.width_169,
                display_height=sys_consts.PAL_SPECS.height_169,
            )
        else:  # 4:3
            return Dvd_Dims(
                storage_width=sys_consts.PAL_SPECS.width_43,
                storage_height=sys_consts.PAL_SPECS.height_43,
                display_width=sys_consts.PAL_SPECS.width_43,
                display_height=sys_consts.PAL_SPECS.height_43,
            )


def Get_Image_Width(image_file: str) -> tuple[int, str]:
    """
    Returns the width of an image file in pixels.

    Args:
        image_file (str): The path to the image file.

    Returns:
        tuple[int,str]:
        - arg1: > 0 OK, -1 Error,
        - arg2: Error message ot "" if ok

    """
    assert isinstance(image_file, str) and image_file.strip() != "", (
        f"{image_file=}. Must be a path to a file"
    )
    assert os.path.exists(image_file), f"{image_file=}. Does not exist"

    commands = [sys_consts.IDENTIFY, "-format", "%w", image_file]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return -1, message

    return int(message.strip()), ""


def Get_Image_Height(image_file: str) -> tuple[int, str]:
    """
    Returns the height of an image file in pixels.

    Args:
        image_file (str): The path to the image file.

    Returns:
        tuple[int,str]:
        - arg1: > 0 OK, -1 Error,
        - arg2: Error message ot "" if ok

    """
    assert isinstance(image_file, str) and image_file.strip() != "", (
        f"{image_file=}. Must be a path to a file"
    )
    assert os.path.exists(image_file), f"{image_file=}. Does not exits"

    commands = [sys_consts.IDENTIFY, "-format", "%h", image_file]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return -1, message

    return int(message.strip()), ""


def Get_Image_Size(image_file: str) -> tuple[int, int, str]:
    """
    Returns the width and height of an image file in pixels.

    Args:
        image_file (str): The path to the image file.

    Returns:
        tuple[int,int,str]:
        - arg1: > 0 OK, -1 Error, width
        - arg2: > 0 OK, -1 Error, height
        - arg3: Error message ot "" if ok

    """
    assert isinstance(image_file, str) and image_file.strip() != "", (
        f"{image_file=}. Must be a path to a file"
    )
    assert os.path.exists(image_file), f"{image_file=}. Does not exits"

    commands = [sys_consts.IDENTIFY, "-format", "%w %h", image_file]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return -1, -1, message

    width, height = message.strip().split()

    return int(width), int(height), ""


def Generate_Menu_Image_From_File(
    video_file: str, frame_number: int, out_folder: str, button_height: int = 500
) -> tuple[int, str]:
    """
    Generate the image at the specified frame number from the video file.

    Args:
        video_file (str): The input video file
        frame_number (int): The desired video frame r to be saved as an image. Must be >= 0
        out_folder (str): The folder to save the image to
        button_height: (int): Height of button pixels - maintains aspect ratio

    Returns:
        tuple[int,str]:
            - arg1: > 0 OK, -1 Error,
            - arg2: Error message ot "" if ok
    """
    assert isinstance(video_file, str) and video_file.strip() != "", (
        f"{video_file=}. Must be non-empty str"
    )
    assert isinstance(frame_number, int) and frame_number >= 0, (
        f"{frame_number=}. Must be int >= 0"
    )
    assert isinstance(out_folder, str) and out_folder.strip() != "", (
        f"{out_folder=}. Must be non-empty str"
    )
    assert isinstance(button_height, int), f"{button_height=}. Must be int > 0"

    file_handler = file_utils.File()

    video_file_path, video_file_name, extn = file_handler.split_file_path(video_file)

    if (
        not file_handler.file_exists(video_file_path, video_file_name, extn)
        or not file_handler.path_exists(out_folder)
        or not file_handler.path_writeable(out_folder)
    ):
        return -1, f"{video_file} or {out_folder} does not exist or is not writeable"

    image_file = file_handler.file_join(out_folder, video_file_name, "jpg")

    if file_handler.file_exists(out_folder, video_file_name, "jpg"):
        os.remove(image_file)

        if file_handler.file_exists(out_folder, video_file_name, "jpg"):
            return -1, ""

    commands = [
        sys_consts.FFMPG,
        "-i",
        video_file,
        "-vf",
        f"select=eq(n\\,{frame_number}),scale=-1:{button_height}",
        "-vframes",
        "1",
        "-update",
        "1",
        image_file,
    ]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return result, message

    return 1, image_file


def Get_File_Encoding_Info(video_file: str) -> Encoding_Details:
    """
    Returns the pertinent file encoding information

    Args:
        video_file (str): The video file being checked

    Returns:
        Video_Details: Check video_details.error if it is not an empty string an error occurred

    """

    #### Helper functions
    def _calculate_frame_rate(stream: dict, video_scan_type: str = "") -> float:
        """
        Calculates frame rate, prioritizing avg_frame_rate and adjusts for interlaced field rates.

        Args:
            stream (dict): The video stream dictionary
            video_scan_type (str): The scan type of the video stream (e.g., 'interlaced', 'progressive').
                                    Defaults to empty string if not provided.

        Returns:
            float: The calculated and adjusted frame rate
        """

        def _extract_frame_rate_val(stream: dict, key: str) -> float:
            """
            Extracts and rounds frame rate from a stream key.

            Args:
                stream (dict): The video stream dictionary
                key (str): The key to extract the frame rate from.

            Returns:
                float: The extracted frame rate
            """
            assert isinstance(stream, dict), f"{stream=}. Must be a dict"
            assert isinstance(key, str) and key.strip() != "", (
                f"{key=}. Must be a non-empty str"
            )

            frame_rate_value = stream.get(key)

            if isinstance(frame_rate_value, str) and "/" in frame_rate_value:
                try:
                    num, den = map(int, frame_rate_value.split("/"))
                    # Added a sanity check for extremely large numerators which might indicate non-frame-rate values
                    if num > 100000 and den == 1:
                        return 0.0  # Force to zero to trigger fallback calculation
                    return round(num / den, 3)
                except (ValueError, ZeroDivisionError):
                    return 0.0

            if isinstance(frame_rate_value, (int, float)):
                return float(frame_rate_value)

            return 0.0

        def _get_standardized_frame_rate(raw_frame_rate: float) -> float:
            """
            Returns standard or adjusted near-standard frame rate,or 0.0 if the raw rate is outside expected video
            ranges.

            Args:
                raw_frame_rate (float): The raw frame rate value.

            Returns:
                float: The adjusted or standard frame rate
            """
            assert isinstance(raw_frame_rate, float) and raw_frame_rate >= 0.0, (
                f"{raw_frame_rate=}. Must be float >= 0.0"
            )

            # Insanity check: If frame rate is excessively high, it's likely wrong.
            if raw_frame_rate > 1000.0:
                return 0.0

            if raw_frame_rate > 0.0:
                if 24 < raw_frame_rate < 25:  # For 23.976 (NTSC film) to 25.0 (PAL)
                    return float(sys_consts.PAL_FRAME_RATE)
                elif 49 < raw_frame_rate < 50:  # For 49.95 to 50.0 (PAL field)
                    return float(sys_consts.PAL_FIELD_RATE)
                elif (
                    29 < raw_frame_rate < 30
                    and raw_frame_rate != sys_consts.NTSC_FRAME_RATE
                ):  # For 29.97
                    return float(sys_consts.NTSC_FRAME_RATE)
                elif (
                    59 < raw_frame_rate < 60
                    and raw_frame_rate != sys_consts.NTSC_FIELD_RATE
                ):  # For 59.94
                    return float(sys_consts.NTSC_FIELD_RATE)

                # Check for exact standard values or common integers
                if raw_frame_rate in (
                    sys_consts.NTSC_FRAME_RATE,
                    sys_consts.NTSC_FIELD_RATE,
                    sys_consts.PAL_FRAME_RATE,
                    sys_consts.PAL_FIELD_RATE,
                    24.0,  # Common for film
                    30.0,  # Common integer NTSC-like frame rate
                    60.0,  # Common integer NTSC-like field rate
                ):
                    return float(raw_frame_rate)

                return float(
                    raw_frame_rate
                )  # Return as is if not near a standard or exact match

            return 0.0

        assert isinstance(stream, dict), f"{stream=}. Must be a dict"
        assert isinstance(video_scan_type, str) and video_scan_type in (
            "interlaced",
            "progressive",
        ), f"{video_scan_type=}. Must be 'interlaced' or 'progressive'"

        average_frame_rate = _get_standardized_frame_rate(
            _extract_frame_rate_val(stream, "avg_frame_rate")
        )
        raw_frame_rate = _get_standardized_frame_rate(
            _extract_frame_rate_val(stream, "r_frame_rate")
        )

        # Prioritize avg_frame_rate, then raw_frame_rate
        calculated_fr = (
            average_frame_rate if average_frame_rate > 0.0 else raw_frame_rate
        )

        # Apply the interlaced adjustment
        if video_scan_type == "interlaced" and calculated_fr in (
            sys_consts.PAL_FIELD_RATE,
            60.0,
            sys_consts.NTSC_FIELD_RATE,
        ):
            # If it's interlaced and the rate is a field rate, divide by 2 for the frame rate
            return calculated_fr / 2.0

        return calculated_fr

    def _calculate_aspect_ratio(aspect_ratio: str) -> float:
        """
        Calculates aspect ratio from string.

        Args:
            aspect_ratio (str): The aspect ratio as a string in the form of "16:9" or "4:3"

        Returns:
            float: The calculated aspect ratio
        """
        assert isinstance(aspect_ratio, str), f"{aspect_ratio=}. Must be a string"

        if aspect_ratio and ":" in aspect_ratio:
            try:
                num, den = map(int, aspect_ratio.split(":"))
                float_ar = num / den
                return round(float_ar, 3)
            except (ValueError, ZeroDivisionError):
                return 0.0
        return 0.0

    def _get_standard_aspect_ratio_string(
        width: int, height: int, dar_float: float = 0.0
    ) -> str:
        """
        Returns a standard "X:Y" aspect ratio string based on width, height, or a provided DAR float.
        Prioritizes a lookup table for common problematic or standard resolutions.

        Args:
            width (int) : Video width
            height (int): Video height
            dar_float (float): The video display aspect ratio

        """
        if width == 0 or height == 0:
            return ""

        delta = 0.01

        # First up try comparing with standard resolutions
        standard_resolution_dar_map = {
            (720, 576): "4:3",  # Common PAL 4:3 (PAR 16:15)
            (768, 576): "4:3",  # Square pixel PAL 4:3
            (1024, 576): "16:9",  # Square pixel PAL 16:9
            (720, 480): "4:3",  # Common NTSC 4:3 (PAR 8:9)
            (640, 480): "4:3",  # Square pixel NTSC 4:3
            (854, 480): "16:9",  # Wide NTSC
        }

        if (width, height) in standard_resolution_dar_map:
            return standard_resolution_dar_map[(width, height)]

        # Next try extracting from first principles
        calculated_float_ar = dar_float if dar_float > 0 else (width / height)

        if abs(calculated_float_ar - (16 / 9)) < delta:
            return "16:9"
        elif abs(calculated_float_ar - (4 / 3)) < delta:
            return "4:3"
        elif abs(calculated_float_ar - (21 / 9)) < delta:  # Ultrawide
            return "21:9"
        elif abs(calculated_float_ar - 1.85) < delta:  # Common theatrical
            return "1.85:1"
        elif abs(calculated_float_ar - 2.35) < delta:  # Common anamorphic widescreen
            return "2.35:1"
        elif abs(calculated_float_ar - 2.39) < delta:  # Common anamorphic widescreen
            return "2.39:1"

        # Finally desperation sets in
        try:
            fraction_ar = fractions.Fraction(calculated_float_ar).limit_denominator(100)

            if fraction_ar.denominator > 0:
                return f"{fraction_ar.numerator}:{fraction_ar.denominator}"
        except (ValueError, ZeroDivisionError, OverflowError):
            pass

        # If all else fails probably stuffed but return the rounded decimal:1
        return f"{round(calculated_float_ar, 2)}:1" if calculated_float_ar > 0 else ""

    #### Main
    debug = False  # Set to False for production

    video_file_details = Encoding_Details()

    assert isinstance(video_file, str) and video_file.strip() != "", (
        f"{video_file=}. Must be a path to a file"
    )
    if not os.path.exists(video_file):
        video_file_details.error = f"{video_file=}. Does not exist"
        return video_file_details

    commands = [
        sys_consts.FFPROBE,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-show_frames",
        "-read_intervals",
        "%+2",  # Read first 2 seconds for frame analysis
        video_file,
    ]

    result, message = Execute_Check_Output(
        commands=commands, debug=False, stderr_to_stdout=True
    )

    if result == -1:
        video_file_details.error = message
        return video_file_details

    json_string = message
    representative_frame = None
    all_video_i_frames = []

    try:
        json_data = json.loads(json_string)

        audio_track_count = 0
        video_track_count = 0

        # Safely get duration, default to 0.0 if not found
        format_data = json_data.get("format", {})
        video_file_details.video_duration = float(format_data.get("duration", 0.0))

        # Frame Analysis and Representative Frame Selection
        all_video_i_frames = [
            frame
            for frame in json_data.get("frames", [])
            if frame.get("media_type") == "video"
            and frame.get("pict_type") == "I"
            and frame.get("key_frame") == 1
            and frame.get("width") is not None
            and frame.get("height") is not None
            and frame.get("width") > 0
            and frame.get("height") > 0
        ]

        total_video_frames_read = len([
            frame
            for frame in json_data.get("frames", [])
            if frame.get("media_type") == "video"
        ])

        video_file_details.all_I_frames = (
            total_video_frames_read > 0
            and total_video_frames_read == len(all_video_i_frames)
        )

        for frame in all_video_i_frames:
            if frame.get("sample_aspect_ratio", "") != "":
                representative_frame = frame
                break  # Found a good one, use it!

        # Fallback if no frame with sample_aspect_ratio was found, but we have other I-frames
        if representative_frame is None and all_video_i_frames:
            representative_frame = all_video_i_frames[0]

        video_file_details.video_scan_type = "progressive"

        if representative_frame:
            if representative_frame.get("interlaced_frame") == 1:
                video_file_details.video_scan_type = "interlaced"
                video_file_details.video_scan_order = (
                    "tff"
                    if representative_frame.get("top_field_first") == "1"
                    else "bff"
                )

        video_streams = [
            stream
            for stream in json_data.get("streams", [])
            if stream.get("codec_type") == "video"
        ]

        audio_streams = [
            stream
            for stream in json_data.get("streams", [])
            if stream.get("codec_type") == "audio"
        ]

        if not video_streams:
            video_file_details.error = "No Video Stream found"
            if debug:
                print(f"==== File Encoding Details {video_file=} ")
                print("==== JSON DATA")
                pprint.pprint(json_data)
            return video_file_details

        last_processed_video_stream = None

        # Process the first video stream
        for stream in video_streams:
            last_processed_video_stream = stream
            video_track_count += 1
            video_file_details.video_codec = stream.get("codec_name", "")
            video_file_details.video_format = stream.get("codec_name", "")

            if (
                representative_frame
                and representative_frame.get("width", 0) > 0
                and representative_frame.get("height", 0) > 0
            ):
                video_file_details.video_width = int(representative_frame["width"])
                video_file_details.video_height = int(representative_frame["height"])
            else:
                video_file_details.video_width = int(stream.get("width", 0))
                video_file_details.video_height = int(stream.get("height", 0))

            video_file_details.video_frame_rate = _calculate_frame_rate(
                stream, video_file_details.video_scan_type
            )

            # Aspect Ratio (DAR/PAR/AR_string) Determination
            stream_display_aspect_ratio_str = stream.get("display_aspect_ratio", "")
            stream_sample_aspect_ratio_str = stream.get("sample_aspect_ratio", "")

            if representative_frame and representative_frame.get(
                "sample_aspect_ratio", ""
            ):
                video_file_details.video_par = _calculate_aspect_ratio(
                    representative_frame["sample_aspect_ratio"]
                )

            if video_file_details.video_par == 0.0 and stream_sample_aspect_ratio_str:
                video_file_details.video_par = _calculate_aspect_ratio(
                    stream_sample_aspect_ratio_str
                )

            if (
                video_file_details.video_par == 0.0
                and video_file_details.video_width > 0
                and video_file_details.video_height > 0
            ):
                video_file_details.video_par = 1.0  # Default to square pixels

            if stream_display_aspect_ratio_str:
                video_file_details.video_dar = _calculate_aspect_ratio(
                    stream_display_aspect_ratio_str
                )
                video_file_details.video_ar = stream_display_aspect_ratio_str
            else:
                # Fallback: Calculate DAR from (width / height) * PAR
                if (
                    video_file_details.video_width > 0
                    and video_file_details.video_height > 0
                    and video_file_details.video_par > 0
                ):
                    calculated_dar_float = (
                        video_file_details.video_width / video_file_details.video_height
                    ) * video_file_details.video_par
                    video_file_details.video_dar = round(calculated_dar_float, 3)

                    video_file_details.video_ar = _get_standard_aspect_ratio_string(
                        video_file_details.video_width,
                        video_file_details.video_height,
                        video_file_details.video_dar,
                    )

                    # If the standard string maps to a slightly different float, use that for precision
                    if (
                        video_file_details.video_ar
                        and ":" in video_file_details.video_ar
                    ):
                        updated_dar_float = _calculate_aspect_ratio(
                            video_file_details.video_ar
                        )

                        if updated_dar_float != 0:
                            video_file_details.video_dar = updated_dar_float

                # If all else fails and we have dimensions, try to derive from just W/H (square pixel assumption)
                elif (
                    video_file_details.video_width > 0
                    and video_file_details.video_height > 0
                ):
                    calculated_dar_float = (
                        video_file_details.video_width / video_file_details.video_height
                    )
                    video_file_details.video_dar = round(calculated_dar_float, 3)
                    video_file_details.video_ar = _get_standard_aspect_ratio_string(
                        video_file_details.video_width,
                        video_file_details.video_height,
                        calculated_dar_float,
                    )

            raw_num_frames = int(stream.get("nb_frames", 0))
            video_file_details.video_frame_count = raw_num_frames

            # Adjust frame count for interlaced video if raw_num_frames looks like field count
            if (
                video_file_details.video_scan_type == "interlaced"
                and video_file_details.video_frame_rate > 0
                and video_file_details.video_duration > 0
                and raw_num_frames > 0
            ):
                expected_frame_count_if_progressive = (
                    video_file_details.video_duration
                    * video_file_details.video_frame_rate
                )

                # Check if raw_num_frames is approximately double the expected frame count for interlaced
                if abs(raw_num_frames - (expected_frame_count_if_progressive * 2)) < 2:
                    video_file_details.video_frame_count = math.floor(
                        raw_num_frames / 2
                    )

            # Fallback/recalculation if video_frame_count is still 0
            if (
                video_file_details.video_frame_count == 0
                and video_file_details.video_frame_rate > 0
                and video_file_details.video_duration > 0
            ):
                video_file_details.video_frame_count = math.floor(
                    video_file_details.video_duration
                    * video_file_details.video_frame_rate
                )

            video_file_details.video_bitrate = int(stream.get("bit_rate", 0))
            video_file_details.video_profile = stream.get("profile", "")
            video_file_details.video_pix_fmt = stream.get("pix_fmt", "yuv420p")
            video_file_details.video_level = str(stream.get("level", "-99"))

            break  # Only the first video stream is relevant

        # --- Audio Stream Processing ---
        for stream in audio_streams:
            audio_track_count += 1
            video_file_details.audio_codec = stream.get("codec_name", "")
            video_file_details.audio_format = stream.get("codec_name", "")
            video_file_details.audio_sample_rate = int(stream.get("sample_rate", 0))
            video_file_details.audio_channels = int(stream.get("channels", 0))
            video_file_details.audio_bitrate = int(stream.get("bit_rate", 0))
            break  # Only the first audio stream is relevant

        video_file_details.audio_tracks = audio_track_count
        video_file_details.video_tracks = video_track_count

        # --- Post-Processing and Final Checks ---

        # Recalculate frame rate if initial determination was 0 but we have count/duration
        if (
            video_file_details.video_frame_rate == 0
            and video_file_details.video_frame_count > 0
            and video_file_details.video_duration > 0
            and last_processed_video_stream is not None
        ):
            derived_raw_frame_rate = (
                video_file_details.video_frame_count / video_file_details.video_duration
            )

            stream_for_recalc = {
                "avg_frame_rate": str(derived_raw_frame_rate),
                "r_frame_rate": str(derived_raw_frame_rate),
            }

            video_file_details.video_frame_rate = _calculate_frame_rate(
                stream_for_recalc, video_file_details.video_scan_type
            )

        # Check format-level bitrate if stream bitrate is 0 (final fallback for bitrate)
        if video_file_details.video_bitrate == 0:
            if "bit_rate" in format_data:  # Use format_data directly
                video_file_details.video_bitrate = int(format_data["bit_rate"])

        # Determine video standard
        if (
            video_file_details.video_frame_rate == sys_consts.PAL_FRAME_RATE
            or video_file_details.video_frame_rate == sys_consts.PAL_FIELD_RATE
        ):
            video_file_details.video_standard = sys_consts.PAL
        elif (
            video_file_details.video_frame_rate == sys_consts.NTSC_FRAME_RATE
            or video_file_details.video_frame_rate == sys_consts.NTSC_FIELD_RATE
            or (29 < video_file_details.video_frame_rate < 30)
            or (59 < video_file_details.video_frame_rate < 60)
            or video_file_details.video_frame_rate == 30
            or video_file_details.video_frame_rate == 60
        ):
            video_file_details.video_standard = sys_consts.NTSC

        # Secondary standard detection based on resolution (more definitive for DV than anyting else)
        if (
            video_file_details.video_width == 720
            and video_file_details.video_height == 576
        ):
            video_file_details.video_standard = sys_consts.PAL

            if not (
                (24.0 < video_file_details.video_frame_rate < 30.0)
                or (48.0 < video_file_details.video_frame_rate < 60.0)
            ):
                video_file_details.video_frame_rate = sys_consts.PAL_FRAME_RATE

                if video_file_details.video_duration > 0:
                    video_file_details.video_frame_count = math.floor(
                        video_file_details.video_duration
                        * video_file_details.video_frame_rate
                    )
        elif (
            video_file_details.video_width == 720
            and video_file_details.video_height == 480
        ):
            video_file_details.video_standard = sys_consts.NTSC

            if not (
                (24.0 < video_file_details.video_frame_rate < 30.0)
                or (48.0 < video_file_details.video_frame_rate < 60.0)
            ):
                video_file_details.video_frame_rate = sys_consts.NTSC_FRAME_RATE

                if video_file_details.video_duration > 0:
                    video_file_details.video_frame_count = math.floor(
                        video_file_details.video_duration
                        * video_file_details.video_frame_rate
                    )

        if video_file_details.video_standard == "":
            video_file_details.video_standard = "Unknown"

        # Final validation checks
        errors = []
        if video_file_details.video_duration == 0:
            errors.append("Failed To Determine Duration")
        if video_file_details.video_dar == 0:
            errors.append("Failed To Determine Display Aspect Ratio")
        if video_file_details.video_par == 0:
            errors.append("Failed To Determine Pixel Aspect Ratio")
        if video_file_details.video_ar == "":
            errors.append("Failed To Determine Aspect Ratio String")
        if video_file_details.video_width == 0 or video_file_details.video_height == 0:
            errors.append("Failed To Determine Video Dimensions")
        if video_file_details.video_frame_rate == 0:
            errors.append("Failed To Determine Video Frame Rate")
        if video_file_details.video_bitrate == 0:
            errors.append("Failed To Determine Video Bitrate")
        if video_file_details.video_codec == "":
            errors.append(
                "Failed To Determine Video Codec"
            )  # This one is often "unknown" rather than an error for missing codecs
        if video_file_details.video_frame_count == 0:
            errors.append("Failed To Determine The Number Of Frames In The Video")
        if video_file_details.video_standard == "Unknown":
            errors.append("Failed To Determine The Video Standard")

        # Audio specific checks
        if video_file_details.audio_tracks > 0:
            if video_file_details.audio_format == "":
                errors.append("Failed To Determine The Audio Format")
            if video_file_details.audio_channels == 0:
                errors.append("Failed To Determine The Number Of Audio Channels")

        if errors:
            video_file_details.error = "; ".join(errors)

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        video_file_details.error = (
            f"Error parsing ffprobe output or processing data: {e}. "
            f"Raw message start: {json_string[:500]}..."
        )

        if debug:
            print(f"Error: {e}")
            print(f"JSON String start: {json_string[:500]}...")

    if debug and video_file_details.error:
        print(f"Error processing {video_file}: {video_file_details.error}")

    # Debug print the overall results before returning
    if debug:
        print(f"==== File Encoding Details for {video_file} ====")
        # print("==== JSON DATA (first 500 chars) ====")
        # try:
        #    pprint.pprint(json.loads(json_string))
        # except json.JSONDecodeError:
        #    print("Failed to parse JSON for debug printing. Printing raw string.")
        #    print(json_string[:500])
        print("==== Video File Details ====")
        print(f"DBG = {video_file_details.error=}")
        print(f"DBG = {video_file_details.video_codec=}")
        print(f"DBG = {video_file_details.video_level=}")
        print(f"DBG = {video_file_details.video_format=}")
        print(f"DBG = {video_file_details.video_tracks=}")
        print(f"DBG = {video_file_details.video_profile=}")
        print(f"DBG = {video_file_details.all_I_frames=}")
        print(f"DBG = {video_file_details.video_frame_count=}")
        print(f"DBG = {video_file_details.video_frame_rate=}")
        print(f"DBG = {video_file_details.video_duration=}")
        print(f"DBG = {video_file_details.video_height=}")
        print(f"DBG = {video_file_details.video_width=}")
        print(f"DBG = {video_file_details.video_ar=}")
        print(f"DBG = {video_file_details.video_dar=}")
        print(f"DBG = {video_file_details.video_par=}")
        print(f"DBG = {video_file_details.video_bitrate=}")
        print(f"DBG = {video_file_details.video_pix_fmt=}")
        print(f"DBG = {video_file_details.video_scan_order=}")
        print(f"DBG = {video_file_details.video_scan_type=}")
        print(f"DBG = {video_file_details.video_standard=}")
        print(f"DBG = {video_file_details.audio_tracks=}")
        print(f"DBG = {video_file_details.audio_format=}")
        print(f"DBG = {video_file_details.audio_bitrate=}")
        print(f"DBG = {video_file_details.audio_channels=}")
        print(f"DBG = {video_file_details.audio_codec=}")
        print(f"DBG = {video_file_details.audio_sample_rate=}")
        # pprint.pprint(video_file_details.__dir__)  # Access dict for easier viewing
        print("==== All Video I-Frames (first 2) ====")
        pprint.pprint(all_video_i_frames[:2])  # Print only a few for brevity
        if representative_frame:
            print("==== Representative Frame ====")
            pprint.pprint(representative_frame)
        else:
            print("==== No Representative Frame found ====")
        print("==== File Encoding Details End ====")

    return video_file_details


def Resize_Image(
    width: int,
    height: int,
    input_file: str,
    out_file: str,
    ignore_aspect: bool = False,
    no_antialias: bool = False,
    no_dither: bool = False,
    colors: str = "",
    remap: bool = False,
) -> tuple[int, str]:
    """
    Resizes an image to a specified size.

    Args:
        width (int): The desired width of the output image in pixels.
        height (int): The desired height of the output image in pixels.
        input_file (str): The path to the input image file.
        out_file (str): The path to the output image file.
        ignore_aspect (bool, optional): If True, the aspect ratio of the image will be ignored when resizing. Default is False.
        no_antialias (bool, optional): If True, antialiasing will be disabled. Default is False.
        no_dither (bool, optional): If True, dithering will be disabled. Default is False.
        colors (str, optional): The maximum number of colors to use when resizing the image. Default is "" (unlimited).
        remap (bool, optional): If True, color remapping will be applied to the image after resizing. Default is False.

    Returns:
        tuple[int,str]:
            - arg1: > 0 OK, -1 Error,
            - arg2: Error message ot "" if ok

    """
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(input_file, str) and input_file.strip() != "", (
        f"{input_file=}. Must be a path to a file"
    )
    assert isinstance(out_file, str) and out_file.strip() != "", (
        f"{out_file=}. Must be a path to a file"
    )
    assert isinstance(ignore_aspect, bool), f"{ignore_aspect=}. Must be bool"
    assert isinstance(no_antialias, bool), f"{no_antialias=}. Must be bool"
    assert isinstance(no_dither, bool), f"{no_dither=}. Must be bool"
    assert isinstance(colors, str), f"{colors=}. Must be str"
    assert isinstance(remap, bool), f"{remap=}. Must be bool"

    file_handler = file_utils.File()
    if not file_handler.file_exists(input_file):
        return -1, f"{input_file=} does not exist"

    file_path, _, _ = file_handler.split_file_path(out_file)

    if not file_handler.path_exists(file_path):
        return -1, f"{file_path=} does not exist"

    if not file_handler.path_writeable(file_path):
        return -1, f"{file_path=} not writeable"

    flags = ""
    if ignore_aspect:
        flags = "!"

    size = f"{width}x{height}{flags}"

    cmd = [sys_consts.CONVERT, input_file, "-resize", size]

    if no_antialias:
        cmd += ["+antialias"]
    if no_dither:
        cmd += ["+dither"]
    if colors != "":
        cmd += ["-colors", colors]

    if remap:
        result, colors = Execute_Check_Output([
            sys_consts.CONVERT,
            input_file,
            "-unique-colors",
            out_file,
        ])

        if result == -1:  # colors contain the error message in this case
            return result, colors

        cmd += ["-remap", colors]

    result, _ = Execute_Check_Output(commands=cmd + [out_file])

    if result == -1:
        return -1, "Could Not Resize Image"

    return 1, ""


class Video_File_Copier:
    """Copies video file folders to an archive location. Files are checksummed to ensure copy is correct"""

    def __init__(self):
        """Initialize the Video_File_Copier class."""

        self._file_handler = file_utils.File()

    def verify_files_integrity(self, folder_path: str, hash_algorithm="sha256") -> bool:
        """
        Verify the integrity of files in a folder by comparing their checksums with stored checksum files.

        Args:
            folder_path (str): The path of the folder containing files and checksum files.
            hash_algorithm (str): The hash algorithm to use (e.g., "md5", "sha256").
        Returns:
            bool: True if all files' checksums match the stored checksums, False otherwise.
        """
        assert isinstance(folder_path, str) and folder_path.strip() != "", (
            f"{folder_path=}. Must be a non-empty str"
        )

        assert isinstance(hash_algorithm, str) and hash_algorithm.strip().lower() in (
            "md5",
            "sha256",
        ), f"{hash_algorithm=}. Must be a non-empty str md5 or sha256"

        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return False

        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)

                if os.path.isfile(file_path):
                    checksum_file_path = f"{file_path}.{hash_algorithm}"

                    if not os.path.exists(checksum_file_path):
                        print(
                            f"Verification Failed: Checksum file not found for {file_path}"
                        )
                        return False

                    try:
                        with open(
                            checksum_file_path, "r", encoding="utf-8"
                        ) as checksum_file:
                            expected_checksum = (
                                checksum_file.read().strip()
                            )  # .strip() to remove potential newlines

                        actual_checksum = self.calculate_checksum(
                            file_path, hash_algorithm
                        )

                        if actual_checksum != expected_checksum:
                            print(
                                f"Verification Failed: Checksum mismatch for {file_path}"
                            )
                            print(f"  Expected: {expected_checksum}")
                            print(f"  Actual:   {actual_checksum}")
                            return False
                    except Exception as e:
                        print(
                            f"Verification Failed: Error reading/calculating checksum for {file_path}: {e}"
                        )
                        return False

        return True

    def calculate_checksum(self, file_path: str, hash_algorithm="sha256") -> str:
        """
        Calculate the checksum of a file.

        Args:
            file_path (str): The path of the file to calculate the checksum for.
            hash_algorithm (str): The hash algorithm to use (e.g., "md5", "sha256").

        Returns:
            str: The checksum value.
        """
        assert isinstance(file_path, str) and file_path.strip() != "", (
            f"{file_path=}. Must be a non-empty str"
        )

        assert isinstance(hash_algorithm, str) and hash_algorithm.strip().lower() in (
            "md5",
            "sha256",
        ), f"{hash_algorithm=}. Must be a non-empty str md5 or sha256"

        if not os.path.exists(file_path):
            print(f"Checksum calculation failed: File not found {file_path}")
            return ""

        try:
            hasher = hashlib.new(hash_algorithm)

            with open(file_path, "rb") as f:
                while True:
                    data = f.read(65536)  # Read in 64K chunks
                    if not data:
                        break
                    hasher.update(data)

            return hasher.hexdigest()
        except Exception as e:
            print(f"Checksum calculation failed for {file_path}: {e}")
            return ""

    def write_checksum_file(self, file_path: str, checksum: str) -> tuple[int, str]:
        """
        Write the checksum value to a checksum file.

        Args:
            file_path (str): The path of the checksum file.
            checksum (str): The checksum value.

        Returns:
            tuple[int, str]:
                - arg1: 1 for success, -1 for failure.
                - arg2: An error message, or an empty string if successful.
        """
        assert isinstance(file_path, str) and file_path.strip() != "", (
            f"{file_path=}. Must be a non-empty str"
        )
        assert isinstance(checksum, str) and checksum.strip() != "", (
            f"{checksum=}. Must be a non-empty str"
        )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(checksum)
            return 1, ""
        except Exception as e:
            return -1, f"Error writing checksum file {file_path}: {e}"

    def copy_folder_into_folders(
        self,
        source_folder: str,
        destination_root_folder: str,
        menu_title: str,
        folder_size_gb: Union[int, float],
        hash_algorithm="sha256",
        progress_callback: Callable[[str, float, str], None] = None,
        task_id: str = "",
    ) -> tuple[int, str]:
        """
        Copy the contents of a source folder into subfolders of a specified size (in GB), verify checksum,
        and check disk space.

        Args:
            source_folder (str): The source folder whose contents will be copied.
            destination_root_folder (str): The root folder where subfolders will be created to store the copied contents.
            menu_title (str): The menu title is used in archive folder naming
            folder_size_gb (Union[int, float]): The maximum size (in GB) of each subfolder.
            hash_algorithm (str): The hash algorithm to use for checksum calculation (e.g., "md5", "sha256").
            progress_callback (Callable): Callback function for progress updates (task_id, percentage, message).
            task_id (str): The ID of the task, used for progress callbacks.

        Returns:
            tuple[int, str]:
                - arg1: 1 for success, -1 for failure.
                - arg2: An error message, or an empty string if successful.
        """
        assert isinstance(source_folder, str) and source_folder.strip(), (
            f"Invalid source folder path: {source_folder}"
        )
        assert (
            isinstance(destination_root_folder, str) and destination_root_folder.strip()
        ), f"Invalid destination root folder: {destination_root_folder}"
        assert isinstance(menu_title, str) and menu_title.strip() != "", (
            f"{menu_title=}. Must be non-empty str"
        )
        assert isinstance(folder_size_gb, (int, float)) and folder_size_gb > 0.5, (
            f"{folder_size_gb=}. Must be > 0.5"
        )
        assert isinstance(hash_algorithm, str) and hash_algorithm.strip().lower() in (
            "md5",
            "sha256",
        ), f"{hash_algorithm=}. Must be a non-empty str md5 or sha256"

        if not os.path.exists(source_folder):
            return -1, f"Source folder not found: {source_folder}"
        if not os.path.isdir(source_folder):
            return -1, f"Source path is not a directory: {source_folder}"

        if not os.path.exists(destination_root_folder):
            try:
                os.makedirs(destination_root_folder)
            except Exception as e:
                return (
                    -1,
                    f"Failed to create destination root folder {destination_root_folder}: {e}",
                )

        if os.path.abspath(source_folder) == os.path.abspath(destination_root_folder):
            return -1, "Source and destination paths cannot be the same."

        try:
            total_source_folder_size_bytes = 0
            all_files_with_size = []

            for root, _, files in os.walk(source_folder):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        total_source_folder_size_bytes += file_size
                        file_creation_time = os.path.getctime(file_path)
                        all_files_with_size.append((
                            file_path,
                            file_creation_time,
                            file_size,
                        ))

            destination_disk_path = os.path.abspath(destination_root_folder)
            free_space, message = Get_Space_Available(destination_disk_path)

            if free_space == -1:
                return -1, message

            if free_space < total_source_folder_size_bytes:
                if total_source_folder_size_bytes > folder_size_gb * 1024**3:
                    return -1, (
                        f"Not enough free space on the destination disk ({free_space / 1024**3:.2f} GB "
                        f"available) for the total source data ({total_source_folder_size_bytes / 1024**3:.2f} GB). "
                        "Individual chunks may fit, but total storage is insufficient."
                    )
                else:
                    return -1, (
                        f"Not enough free space on the destination disk ({free_space / 1024**3:.2f} GB "
                        f"available) for the source data ({total_source_folder_size_bytes / 1024**3:.2f} GB)."
                    )

            # Sort files by creation time
            all_files_with_size.sort(key=lambda x: x[1])

            subfolder_index = 0
            current_subfolder_size_bytes = 0
            copied_bytes_total = 0  # For progress reporting
            destination_folder = ""

            for file_path, _, original_file_size in all_files_with_size:
                chunked_files = []
                delete_chunked = False

                if original_file_size > folder_size_gb * 1024**3:
                    if progress_callback:
                        progress_callback(
                            task_id,
                            (copied_bytes_total / total_source_folder_size_bytes) * 100,
                            f"Splitting large file: {os.path.basename(file_path)}",
                        )

                    result, message = Split_Large_Video(
                        file_path, destination_root_folder, folder_size_gb
                    )

                    if result == -1:
                        return -1, message  # message is error

                    chunked_files = message.split("|") if "|" in message else [message]
                    delete_chunked = True
                else:
                    chunked_files.append(file_path)

                for chunked_file in chunked_files:
                    source_checksum = self.calculate_checksum(
                        chunked_file, hash_algorithm
                    )
                    if not source_checksum:  # Check if checksum calculation failed
                        return (
                            -1,
                            f"Failed to calculate checksum for source file: {chunked_file}",
                        )

                    current_chunk_size = os.path.getsize(chunked_file)

                    # Create new disk_folder, if adding the file to the current subfolder would exceed the size limit
                    if (
                        subfolder_index == 0  # Always want disk 1 folder initially
                        or current_subfolder_size_bytes + current_chunk_size
                        > folder_size_gb * 1024**3  # Use folder_size_gb directly
                    ):
                        subfolder_index += 1
                        current_subfolder_size_bytes = 0
                        destination_folder = os.path.join(
                            destination_root_folder,
                            f"{menu_title} - Disk_{subfolder_index:02}",
                        )

                        if self._file_handler.make_dir(destination_folder) == -1:
                            return (
                                -1,
                                f"Failed to create directory: {destination_folder}",
                            )

                    if not destination_folder:
                        return (
                            -1,
                            f"Failed to determine destination folder for {chunked_file}.",
                        )

                    # Note: The destination_folder is always set on the first iteration of the loop for a new disk.
                    destination_file_path = (
                        self._file_handler.file_join(  # Use instance _file_handler
                            destination_folder, os.path.basename(chunked_file)
                        )
                    )

                    if progress_callback:
                        progress_message = f"Copying: {os.path.basename(chunked_file)} to Disk_{subfolder_index:02}"
                        progress_callback(
                            task_id,
                            (copied_bytes_total / total_source_folder_size_bytes) * 100,
                            progress_message,
                        )

                    shutil.copy2(chunked_file, destination_file_path)

                    destination_checksum = self.calculate_checksum(
                        destination_file_path, hash_algorithm
                    )

                    if not destination_checksum:
                        return (
                            -1,
                            f"Failed to calculate checksum for destination file: {destination_file_path}",
                        )

                    if (
                        source_checksum != destination_checksum
                    ):  # Attempt to clean up the partially copied/corrupted file
                        if os.path.exists(destination_file_path):
                            os.remove(destination_file_path)
                        return -1, (
                            f"File copy resulted in corruption for {os.path.basename(chunked_file)}. "
                            "Source/Destination checksum mismatch."
                        )

                    checksum_file_name = (
                        f"{os.path.basename(destination_file_path)}.{hash_algorithm}"
                    )
                    checksum_file_path = self._file_handler.file_join(
                        destination_folder, checksum_file_name
                    )

                    result, message = self.write_checksum_file(
                        checksum_file_path, destination_checksum
                    )

                    if result == -1:
                        # Attempt to clean up the copied file if checksum file cannot be written
                        if os.path.exists(destination_file_path):
                            os.remove(destination_file_path)
                        return (
                            -1,
                            f"Failed to write checksum file for {os.path.basename(destination_file_path)}: {message}",
                        )

                    current_subfolder_size_bytes += current_chunk_size
                    copied_bytes_total += current_chunk_size

                    if (
                        delete_chunked
                    ):  # Only chunked files created by file splitting are deleted.
                        result = self._file_handler.remove_file(chunked_file)

                        if result == -1:
                            # This is a cleanup failure, not a primary copy failure.
                            return (
                                -1,
                                f"Failed to delete temporary chunked file : {chunked_file}",
                            )

            if progress_callback:
                progress_callback(task_id, 100.0, "Copying complete.")

            return 1, ""

        except Exception as e:
            if progress_callback:
                progress_callback(task_id, 0.0, f"Error: {e}")

            return -1, f"Error copying folder into sub-folders: {e}"
