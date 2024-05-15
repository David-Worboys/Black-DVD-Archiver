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

# Tell Black to leave this block alone (realm of isort)
# fmt: off
import dataclasses
import glob
import hashlib
import json
import math
import os
import os.path
import platform
import pprint
import shlex
import shutil
import subprocess
import textwrap
from typing import Final

import psutil

import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups
import sys_consts
import QTPYGUI.utils as utils
from sys_config import Encoding_Details, DVD_Menu_Page

# fmt: on

colors = {
    "white": "#ffffff",
    "black": "#000000",
    "gray": "#808080",
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "purple": "#800080",
    "orange": "#ffa500",
    "pink": "#ffc0cb",
    "brown": "#a52a2a",
    "cyan": "#00FFFF",
    "lightblue": "#add8e6",
    "lightgreen": "#90ee90",
    "lightgray": "#d3d3d3",
    "darkgray": "#696969",
    "darkred": "#8b0000",
    "darkblue": "#00008b",
    "darkgreen": "#006400",
    "beige": "#f5f5dc",
    "maroon": "#800000",
    "turquoise": "#40e0d0",
    "lightyellow": "#ffffe0",
    "lavender": "#e6e6fa",
    "navy": "#000080",
    "olive": "#808000",
    "teal": "#008080",
    "silver": "#c0c0c0",
    "transparent": "#00000000",
    "gainsboro": "#DCDCDC",
    "floralwhite": "#FFFAF0",
    "oldlace": "#FDF5E6",
    "linen": "#FAF0E6",
    "antiquewhite": "#FAEBD7",
    "papayawhip": "#FFEFD5",
    "blanchedalmond": "#FFEBCD",
    "bisque": "#FFE4C4",
    "peachpuff": "#FFDAB9",
    "navajowhite": "#FFDEAD",
    "moccasin": "#FFE4B5",
    "cornsilk": "#FFF8DC",
    "ivory": "#FFFFF0",
    "lemonchiffon": "#FFFACD",
    "seashell": "#FFF5EE",
    "honeydew": "#F0FFF0",
    "mintcream": "#F5FFFA",
    "azure": "#F0FFFF",
    "aliceblue": "#F0F8FF",
    "lavenderblush": "#FFF0F5",
    "mistyrose": "#FFE4E1",
    "rosybrown": "#bc8f8f",
    "saddlebrown": "#8b4513",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "sienna": "#a0522d",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "whitesmoke": "#f5f5f5",
    "yellowgreen": "#9acd32",
}

valid_gravities = [
    "center",
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
    "static",
    "forget",
]


@dataclasses.dataclass(slots=True)
class Dvd_Dims:
    storage_width: int = -1
    storage_height: int = -1
    display_width: int = -1
    display_height: int = -1


@dataclasses.dataclass(slots=True)
class Cut_Video_Def:
    input_file: str = ""
    output_file: str = ""
    start_cut: int = 0  # Frame
    end_cut: int = 0  # Frame
    frame_rate: float = 0.0
    tag: str = ""

    def __post_init__(self) -> None:
        assert (
            isinstance(self.input_file, str) and self.input_file.strip() != ""
        ), f"{self.input_file=}. Must be a non-empty str"
        assert (
            isinstance(self.output_file, str) and self.output_file.strip() != ""
        ), f"{self.output_file=}. Must be a non-empty str"
        assert (
            isinstance(self.start_cut, int) and self.start_cut >= 0
        ), f"{self.start_cut=}. Must be a int >= 0"
        assert (
            isinstance(self.end_cut, int) and self.end_cut >= 0
        ), f"{self.end_cut=}. Must be a int >= 0"

        assert (
            isinstance(self.frame_rate, float) and self.frame_rate >= 24
        ), f"{self.end_cut_secs=}. Must be a float >= 24"

        assert (
            self.end_cut > self.start_cut
        ), f"{self.end_cut=} must be > {self.start_cut} "

        assert isinstance(self.tag, str), f"{self.tag=}. Must be str"

    @property
    def start_cut_secs(self) -> float:
        return self.start_cut / self.frame_rate

    @property
    def end_cut_secs(self) -> float:
        return self.end_cut / self.frame_rate


def DVD_Percent_Used(total_duration: float, pop_error_message: bool = True):
    """Calculates the percentage of the DVD used based on the total duration of the videos assigned to that DVD.
    If the percentage used is > 100 then an error Popup is opened if pop_error_message is True

    Args:
        total_duration (float): total duration in seconds
        pop_error_message (bool): if True popup an error message if the percentage used is > 100

    Returns:
        int: percentage of DVD used

    """
    assert (
        isinstance(total_duration, float) and total_duration >= 0.0
    ), f"{total_duration=}. Must be >= 0.0"
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
    have been getting thermal related crashes

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
            "copy",
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
            Get_Thread_Count(),
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
            Get_Thread_Count(),
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
    temp_files: list[str],
    output_file: str,
    audio_codec: str = "",
    delete_temp_files: bool = False,
    transcode_format: str = "",
    debug: bool = False,
) -> tuple[int, str]:
    """
    Concatenates video files using ffmpeg.

    Args:
        temp_files (list[str]): List of input video files to be concatenated
        output_file (str): The joined (concatenated) output file name.
            Note Transcode concats will use the folder and file name but will have the transcode_format extension
        audio_codec (str): The audio codec to checked against (aac is special)
        delete_temp_files (bool): Whether to delete the temp files, defaults to False
        transcode_format (str): Transcode files as per the transcode_format and then joins (concatenates) the files.
            Note: Transcodes are slow, defaults to "". legal values are h264 | h265 | mpg | mjpeg
        debug (bool): True, print debug info, otherwise do not

    Returns:
        tuple[int, str]:
            - arg 1: 1 if success, -1 if error
            - arg 2: "" if success otherwise and error message
    """
    assert isinstance(
        temp_files, list
    ), f"{temp_files} Must be a list of input video files"
    assert all(
        isinstance(file, str) for file in temp_files
    ), "all elements in temp_files must str"
    assert isinstance(output_file, str), f"{output_file=}. Must be str"
    assert isinstance(audio_codec, str), f"{audio_codec=}. Must be a str"
    assert isinstance(delete_temp_files, bool), f"{delete_temp_files=}. Must be a bool"
    assert isinstance(transcode_format, str) and transcode_format in (
        "",
        "h264",
        "h265",
        "mpg",
        "mjpeg",
        "ffv1",
    ), f"{transcode_format=}. Must be str - h264 | h265 | mpg | mjpeg | ffv1"

    if debug and not utils.Is_Complied():
        print(f"DBG CV {temp_files=} {output_file=} {audio_codec=} {delete_temp_files}")

    file_handler = file_utils.File()
    out_path, _, _ = file_handler.split_file_path(output_file)
    file_list_txt = file_handler.file_join(
        out_path, f"video_data_list_{utils.Get_Unique_Id()}", "txt"
    )

    if not file_handler.path_writeable(out_path):
        return -1, f"Can Not Be Write To {out_path}!"

    for video_file in temp_files:
        if not file_handler.file_exists(video_file):
            return -1, f"File {video_file} Does Not Exist!"

    transcode_file_list = []

    if transcode_format:  # Very slow on a AMD2400G with 1GB of RAM :-)
        if transcode_format in ("h264", "h265"):
            container_format = "mp4"
        elif transcode_format == "mpg":
            container_format = "mpg"
        elif (
            transcode_format == "mjpeg"
        ):  # Note I use H264 instead, but mjpeg is still an option
            container_format = "mkv"  # mkv if use MJPEG
        elif transcode_format == "ffv1":
            container_format = "mkv"
        else:
            raise RuntimeError(f"Unknown transcode_concat {transcode_format=}")

        out_path, out_name, _ = file_handler.split_file_path(output_file)
        output_file = file_handler.file_join(out_path, out_name, container_format)
        # audio_codec = "aac"  # H26x Transcode uses aac

        temp_path, temp_name, _ = file_handler.split_file_path(
            temp_files[0]
        )  # Must exist
        transcode_path = file_handler.file_join(temp_path, "transcode_temp_files")

        if file_handler.path_exists(transcode_path):
            result, message = file_handler.remove_dir_contents(
                file_path=transcode_path, keep_parent=False
            )

            if result == -1:
                return -1, message

        if file_handler.make_dir(transcode_path) == -1:
            return -1, f"Failed To Create {transcode_path}"

        for video_file in temp_files:
            temp_path, temp_name, _ = file_handler.split_file_path(video_file)
            transcode_path = file_handler.file_join(temp_path, "transcode_temp_files")
            encoding_info: Encoding_Details = Get_File_Encoding_Info(video_file)

            if encoding_info.error.strip():
                return (
                    -1,
                    (
                        "Failed To Get Encoding Details :"
                        f" {sys_consts.SDELIM}{video_file}{sys_consts.SDELIM}"
                    ),
                )
            else:
                match transcode_format:
                    case "ffv1":
                        transcode_file = file_handler.file_join(
                            transcode_path, temp_name, "mkv"
                        )
                        result, message = Transcode_ffv1_archival(
                            input_file=video_file,
                            output_folder=transcode_path,
                            frame_rate=encoding_info.video_frame_rate,
                            width=encoding_info.video_width,
                            height=encoding_info.video_height,
                        )

                        if result == -1:
                            return -1, message

                    case "h264":
                        transcode_file = file_handler.file_join(
                            transcode_path, temp_name, "mp4"
                        )

                        result, message = Transcode_H26x(
                            input_file=video_file,
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
                        )

                        if result == -1:
                            return -1, message
                    case "h265":
                        transcode_file = file_handler.file_join(
                            transcode_path, temp_name, "mp4"
                        )

                        result, message = Transcode_H26x(
                            input_file=video_file,
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
                        )

                        if result == -1:
                            return -1, message
                    case "mpg":
                        transcode_file = file_handler.file_join(
                            transcode_path, temp_name, "mpg"
                        )

                        result, message = Transcode_MPEG2_High_Bitrate(
                            input_file=video_file,
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
                        )

                        if result == -1:
                            return -1, message

                    case "mjpeg":
                        transcode_file = file_handler.file_join(
                            transcode_path,
                            temp_name,
                            "mkv",  # avi if use MJPEG
                        )
                        # Set mjpeg argument to true and make the mkv/avi changes above to switch to MJPEG
                        result, message = Transcode_Mezzanine(
                            input_file=video_file,
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
                        )

                        if result == -1:
                            return -1, message

                    case _:  # Stream Copy
                        transcode_file = file_handler.file_join(
                            transcode_path, temp_name, container_format
                        )

                        commands = [
                            sys_consts.FFMPG,
                            "-fflags",
                            "+genpts",  # generate presentation timestamps
                            "-threads",
                            Get_Thread_Count(),
                            "-i",
                            video_file,
                            "-map",
                            "0",
                            "-c",
                            "copy",
                            "-sn",  # Remove titles
                            "-movflags",
                            "+faststart",
                            "-threads",
                            Get_Thread_Count(),
                            transcode_file,
                        ]

                        result, message = Execute_Check_Output(
                            commands=commands, stderr_to_stdout=True
                        )

                        if result == -1:
                            return -1, message

                transcode_file_list.append(transcode_file)

        temp_files = transcode_file_list

    # Generate a file list for ffmpeg
    result, message = file_handler.write_list_to_txt_file(
        str_list=[f"file '{file}'" for file in temp_files], text_file=file_list_txt
    )

    if result == -1:
        return -1, message

    if file_handler.file_exists(output_file):
        result = file_handler.remove_file(output_file)

        if result == -1:
            return -1, f"Failed To Remove File {output_file}"

    aac_audio = []
    if audio_codec == "aac":
        aac_audio = [
            "-bsf:a",
            "aac_adtstoasc",
        ]

    # Concatenate the video files using ffmpeg
    result, message = Execute_Check_Output(
        commands=[
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            # "+igndts",
            "-f",
            "concat",
            "-safe",
            "0",
            "-auto_convert",
            "1",
            "-threads",
            Get_Thread_Count(),
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
            Get_Thread_Count(),
            "-y",
        ],
        debug=debug,
    )

    if debug and not utils.Is_Complied():
        print(f"CONCAT {result=} {message=}")

    if result == -1:
        if not debug:
            file_handler.remove_file(file_list_txt)
        return -1, message

    # Remove the file list and temp files
    if not debug and file_handler.remove_file(file_list_txt) == -1:
        return -1, f"Failed to delete text file: {file_list_txt}"

    if not debug and delete_temp_files:
        for file in temp_files:
            if file_handler.file_exists(file):
                if file_handler.remove_file(file) == -1:
                    return -1, f"Failed to delete temp file: {file}"

    if transcode_file_list:  # always delete these
        transcode_path, _, _ = file_handler.split_file_path(
            transcode_file_list[0]
        )  # Must have at least 1

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
            )

    return 1, output_file


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
    assert (
        isinstance(input_dir, str) and input_dir.strip() != ""
    ), f"{input_dir}. Must be a non-empty str"
    assert (
        isinstance(output_file, str) and output_file.strip() != ""
    ), f"{output_file}. Must be a non-empty str"
    # ffmpeg -i VIDEO_TS -i AUDIO_TS -c copy -map 0:0 -map 1:0 "-dvd-video",
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
) -> tuple[int, bytes]:
    """
    Creates a DVD case insert image with DVD title, menu titles, and using ImageMagick.

    Args:
        title (str): Title of the DVD.
        menu_pages list[DVD_Menu_Page]: List of menu pages to be displayed on the insert.
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

    Returns:
        - arg 1 : Status code. Returns 1 if the iso image was created, -1 otherwise.
        - arg 2 : bytes: The generated DVD case insert image data.
    """
    assert (
        isinstance(title, str) and title.strip() != ""
    ), f"{title=}. Must be a non-empty str"
    assert (
        isinstance(menu_pages, list) and len(menu_pages) > 0
    ), f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    assert all(
        isinstance(page, DVD_Menu_Page) for page in menu_pages
    ), f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    assert (
        isinstance(insert_width, int) and insert_width > 0
    ), f"{insert_width=}. Must be an int >"
    assert (
        isinstance(insert_height, int) and insert_height > 0
    ), f"{insert_height=}. Must be an int > 0"
    assert (
        isinstance(resolution, int) and resolution > 0
    ), f"{resolution=}. Must be an int > 0"
    assert (
        isinstance(menu_font_size, int) and menu_font_size > 0
    ), f"{menu_font_size=}. Must be an int > 0"
    assert (
        isinstance(menu_font_path, str) and menu_font_path.strip() != ""
    ), f"{menu_font_path=}. Must be a non-empty str"
    assert (
        isinstance(insert_colour, str) and insert_colour.strip() != ""
    ), f"{insert_colour=}. Must be a non-empty str"
    assert (
        isinstance(menu_font_colour, str) and menu_font_colour.strip() != ""
    ), f"{menu_font_colour=}. Must be a non-empty str"

    assert (
        isinstance(opacity, float) and 0 <= int(opacity) <= 1
    ), f"{opacity=}. Must be a float between 0.0 and 1.0"

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

    debug = True
    dpm = resolution / 25.4  # Convert DPI to DPMM

    background_canvas_width = insert_width * dpm
    background_canvas_height = insert_height * dpm

    title_char_width, title_char_height = Get_Text_Dims(
        text="W", font=title_font_path, pointsize=title_font_size
    )  # In English at least and in most fonts W is the widest

    menu_char_width, menu_char_height = Get_Text_Dims(
        text="W", font=menu_font_path, pointsize=menu_font_size
    )  # In English at least and in most fonts W is the widest

    dvd_text = []

    max_text_column_width = (background_canvas_width // 2) - 20  # Padding
    max_char_width = int(max_text_column_width // menu_char_width)

    for menu_index, menu_title in enumerate(menu_pages):
        if menu_title.menu_title.strip():
            dvd_text.append(f"* {menu_title.menu_title}")
        else:
            dvd_text.append(f"* Menu {menu_index + 1}")

        for button_item in menu_title.get_button_titles.values():
            button_title = f"\  - {button_item[0]}"  # Button titles are indented 4 spaces (\ required!)

            width, _ = Get_Text_Dims(
                text=f"{button_title}", font=menu_font_path, pointsize=menu_font_size
            )

            if width > max_text_column_width:
                wrapped_text = textwrap.wrap(
                    button_title,
                    width=max_char_width,
                    subsequent_indent="    ",
                )

                for line_index, button_line in enumerate(wrapped_text):
                    dvd_text.append(
                        f"{button_line}" if line_index == 0 else f"\ {button_line}"
                    )

            else:
                dvd_text.append(f"{button_title}")

        dvd_text.append(" ")

    dvd_text.pop(len(dvd_text) - 1)  # Remove the last blank line

    # Get the length of the longest line in the menu/button text
    max_menu_length = 0
    for line in dvd_text:
        if len(line) > max_menu_length:
            max_menu_length = len(line)

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

        left_y1 = 50  # Padding
        left_y2 = background_canvas_height - 20  # Padding

        left_y2 = left_y1 + left_y2
        left_x1 = 50  # Padding

        # left_x2 = max_text_column_width - 20 # Padding
        right_x1 = max_text_column_width + 20  # Padding
        right_x1 = right_x1 + max_text_column_width - 20  # Padding

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
                f"Menu Title Is {len(title_wrapped_text)} Lines Long And Only {MAX_TITLE_LINES} Are Allowed! Reduce "
                f"Title Font Size Or Change Title Font".encode("utf-8"),
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
                return -1, image_data.decode("utf-8")

        # Write menu titles
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
                return -1, image_data.decode("utf-8")

            line_num += 1

        if debug and not utils.Is_Complied():
            with open("cddvd_insert.png", "wb") as png_file:
                png_file.write(image_data)

        return 1, image_data
    except subprocess.CalledProcessError as e:
        return -1, f"Error Generating DVD Insert Image - {e}".encode("utf-8")


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

    Returns:
        tuple[int, bytes]
        - arg 1 : Status code. Returns 1 if the png image was created, -1 otherwise.
        - arg 2 : bytes: The generated DVD label image data as a PNG byte  string.
    """

    assert isinstance(title, str), f"{title=}. Must be a str"
    assert (
        isinstance(menu_pages, list) and len(menu_pages) > 0
    ), f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    assert all(
        isinstance(page, DVD_Menu_Page) for page in menu_pages
    ), f"{menu_pages=}. Must be a non-empty list of DVD_Menu_Page"
    assert (
        isinstance(disk_diameter, (int, float)) and disk_diameter > 0
    ), f"{disk_diameter=}. Must be a float > 0"
    assert (
        isinstance(resolution, int) and resolution > 0
    ), f"{resolution=}. Must be an int > 0"
    assert (
        isinstance(title_font_colour, str) and title_font_colour.strip() != ""
    ), f"{title_font_colour=}. Must be a non-empty str"
    assert (
        isinstance(title_font_size, int) and title_font_size > 0
    ), f"{title_font_size=}. Must be an int > 0"
    assert (
        isinstance(menu_font_colour, str) and menu_font_colour.strip() != ""
    ), f"{menu_font_colour=}. Must be a non-empty str"
    assert (
        isinstance(menu_font_size, int) and menu_font_size > 0
    ), f"{menu_font_size=}. Must be an int > 0"
    assert isinstance(title_font_path, str), f"{title_font_path=}. Must be a str"
    assert isinstance(menu_font_path, str), f"{menu_font_path=}. Must be a str"
    assert (
        isinstance(spindle_diameter, (int, float)) and 21 <= spindle_diameter <= 36
    ), f"{spindle_diameter=}. Must be a float >= 21 and <= 36"
    assert (
        isinstance(opacity, float) and 0 <= int(opacity) <= 1
    ), f"{opacity=}. Must be a float between 0.0 and 1.0"

    assert disk_colour in [
        colour for colour in colors.keys()
    ], f"{disk_colour=}. Must be one of {colors}"
    assert title_font_colour in [
        colour for colour in colors.keys()
    ], f"{title_font_colour=}. Must be one of {colors}"
    assert menu_font_colour in [
        colour for colour in colors.keys()
    ], f"{menu_font_colour=}. Must be one of {colors}"

    debug = True
    MAX_TITLE_LINES: Final[int] = 4
    result, disk_hex = Make_Opaque(color=disk_colour, opacity=opacity)

    if result == -1:
        return -1, f"Invalid System Color {disk_colour}".encode("utf-8")

    if title_font_path.strip() == "":
        fonts = Get_Fonts()
        for font in fonts:
            if font[0].lower().startswith("ubuntu") or "arial" in font[0].lower():
                title_font_path = font[1]
                break
        else:
            return -1, b"A Default Title Font Could Not Be Found "

    if menu_font_path.strip() == "":
        fonts = Get_Fonts()
        for font in fonts:
            if font[0].lower().startswith("ubuntu"):
                menu_font_path = font[1]
                break
        else:
            return -1, b"A Default Menu Font Could Not Be Found "

    if not os.path.exists(title_font_path):
        return -1, f"Title Font file not found: {menu_font_path}".encode("utf-8")

    if not os.path.exists(menu_font_path):
        return -1, f"Menu Font file not found: {menu_font_path}".encode("utf-8")

    dpm = resolution / 25.4  # Convert DPI to DPMM

    disk_diameter = round(disk_diameter * dpm)
    spindle_diameter = round(spindle_diameter * dpm)

    disk_radius = disk_diameter // 2
    spindle_radius = spindle_diameter // 2
    background_canvas_width = disk_diameter
    background_canvas_height = disk_diameter
    label_x = background_canvas_width // 2
    label_y = background_canvas_height // 2

    # Get the largest square that fits in the circle
    disk_square_size = round(disk_radius * math.sqrt(2))
    spindle_square_size = round(spindle_radius * math.sqrt(2))
    label_square_width = (
        disk_square_size // 2 - spindle_square_size // 2 - 20  # Padding
    )  # Take into account spindle hole

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

    # Extract text to place on the DVD image
    dvd_text = []

    menu_char_width, menu_char_height = Get_Text_Dims(
        text="W", font=menu_font_path, pointsize=menu_font_size
    )  # In English at least and in most fonts W is the widest

    for menu_index, menu_title in enumerate(menu_pages):
        if menu_title.menu_title.strip():
            dvd_text.append(f"* {menu_title.menu_title}")
        else:
            dvd_text.append(f"* Menu {menu_index + 1}")

        for button_item in menu_title.get_button_titles.values():
            button_title = f"\  - {button_item[0]}"  # Button titles are indented 4 spaces (\ required!)

            width, _ = Get_Text_Dims(
                text=f"{button_title}", font=menu_font_path, pointsize=menu_font_size
            )

            if width > label_square_width:
                wrapped_text = textwrap.wrap(
                    button_title,
                    width=label_square_width // menu_char_width,
                    subsequent_indent="    ",
                )

                for line_index, button_line in enumerate(wrapped_text):
                    dvd_text.append(
                        f"{button_line}" if line_index == 0 else f"\ {button_line}"
                    )

            else:
                dvd_text.append(f"{button_title}")

        dvd_text.append(" ")

    dvd_text.pop(len(dvd_text) - 1)  # Remove the last blank line

    # Get the length of the longest line in the menu/button text
    max_menu_length = 0
    for line in dvd_text:
        if len(line) > max_menu_length:
            max_menu_length = len(line)

    # Calculate co-ordinates for 2 rectangles on the left and right side of the spindle hole
    left_sq_x1 = 80  # Fixed

    right_sq_x1 = (
        label_x + spindle_square_size + 20  # Padding
    )

    left_sq_y1 = background_canvas_height - disk_square_size
    # right_sq_y1 = background_canvas_height - disk_square_size
    left_sq_y2 = disk_square_size

    x_offset = left_sq_x1

    # Now write the text on the DVD image
    if title:  # First up deal with the title - Max 4 lines allowed
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

    if debug and not utils.Is_Complied():
        with open("cddvd_label.png", "wb") as png_file:
            png_file.write(image_data)

    return 1, image_data


def Get_Space_Available(path: str) -> tuple[int, str]:
    """Returns the amount of available disk space in bytes for the specified file system path.

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


def Get_Color_Names() -> list:
    """Return a list of color names in the colors dictionary.

    Returns:
        list[str]: A list of color names as strings.
    """
    return sorted(list(colors.keys()), key=lambda x: x[0].upper())


def Get_Hex_Color(color: str) -> str:
    """This function returns the hexadecimal value for a given color name.

    Args:
        color (str): The name of the color to look up.

    Returns:
        str: The hexadecimal value for the given color name or "" if color unknown.

    """
    assert (
        isinstance(color, str) and color.strip() != "" and color in Get_Color_Names()
    ), f"{color=}. Must be string  in {', '.join(Get_Color_Names())} "

    color = color.lower()

    if color in colors:
        hex_value = colors[color]
    else:
        hex_value = ""

    return hex_value


def Get_Colored_Rectangle_Example(width: int, height: int, color: str) -> bytes:
    """Generates a PNG image of a colored rectangle.

    Args:
        width (int): The width of the rectangle in pixels.
        height (int): The height of the rectangle in pixels.
        color (str): The color of the rectangle in any ImageMagick-supported color format.

    Returns:
        A bytes object containing the generated PNG image or b"" if an error.

    """
    # Check input arguments
    assert isinstance(width, int) and width > 0, f"{width}. Must be a positive integer."
    assert (
        isinstance(height, int) and height > 0
    ), f"{height}. Must be a positive integer."
    assert (
        isinstance(color, str) and color in colors
    ), f"{color=} must be a string in {', '.join(Get_Color_Names())}"

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
    """Returns a png byte string an example of what a font looks like

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
    assert (
        isinstance(pointsize, int) and pointsize == -1 or pointsize > 0
    ), f"{pointsize=}. Must be -1 to autocalc or int > 0"
    assert isinstance(text, str), (
        f"{text=}. Must be non-empty str" and text.strip() != ""
    )
    assert (
        isinstance(text_color, str) and text_color in colors
    ), f"{text_color=} must be a string in {', '.join(Get_Color_Names())}"
    assert (
        isinstance(background_color, str) and background_color in colors
    ), f"{background_color=} must be a string in {', '.join(Get_Color_Names())}"
    assert (
        isinstance(width, int) and width == -1 or width > 0
    ), f"{width=}. Must be int > 0 or -1 to autocalc"
    assert (
        isinstance(height, int) and height == -1 or height > 0
    ), f"{height=}. Must be int > 0 or -1 to autocalc"
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
    """Returns a list of built-in fonts

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
    """Makes a hex color value partially opaque.

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
    assert (
        isinstance(color, str) and color in colors
    ), f"{color=} must be a string in {', '.join(Get_Color_Names())}"
    assert 0.0 <= opacity <= 1.0, "Opacity must be between 0.0 and 1.0"

    hex_color = Get_Hex_Color(color)

    if hex_color == "":
        return -1, f"Invalid System Color {color}"

    opacity_hex = hex(int(255 * opacity)).lstrip("0x").rjust(2, "0").upper()

    return 1, hex_color + opacity_hex


def Create_Transparent_File(
    width: int, height: int, out_file: str, border_color=""
) -> tuple[int, str]:
    """Creates a transparent file of a given width and height.
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
    """Places the overlay_file on the input file at a given x,y co-ord
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
    out_file: str = "",
) -> tuple[int, str]:
    """Overlays text onto an image.

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
        out_file (str,optional): The path to the output file. Optional, sam as in_file if not supplied


    Returns:
        tuple[int, str]:
        - arg1: Ok, -1, Error,
        - arg2: Error message or "" if ok
    """
    assert isinstance(in_file, str), f"{in_file=} must be a string"
    assert isinstance(text, str), f"{text=} must be a string"
    assert (
        isinstance(text_font, str) and text_font.strip() != ""
    ), f"{text_font=} must be a non-empty str {type(text_font)=}"
    assert isinstance(text_pointsize, int), f"{text_pointsize=} must be an integer"
    assert (
        isinstance(text_color, str) and text_color in colors
    ), f"{text_color=} must be a string"
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

    text_width, text_height = Get_Text_Dims(
        text=text, font=text_font, pointsize=text_pointsize
    )

    if text_width == -1:
        return -1, "Could Not Get Text Width"

    image_width, message = Get_Image_Width(in_file)

    if image_width == -1:
        return -1, message

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


def Transcode_ffv1_archival(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
) -> tuple[int, str]:
    """
    Converts an input vile file into a lossless ffv1 compressed video suitable for permanent archival storage.

    ffv1 is a permanent archival format widely accepted by archival institutions worldwide

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int): The width of the video
        height (int): The height of the video

    Returns:
        tuple[int, str]:
            - arg 1: 1 if ok, -1 if error
            - arg 2: error message if error (-1) else output file path (1)

    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a non-empty str"
    assert (
        isinstance(output_folder, str) and output_folder.strip() != ""
    ), f"{output_folder=}. Must be a non-empty str"
    assert (
        isinstance(frame_rate, float) and frame_rate > 0
    ), f"{frame_rate=}. Must be float > 0"
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"

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
    passlog_del_file = file_handler.file_join(
        output_folder, f"{input_file_name}-0.log"
    )  # FFMPEG tacks on video stream

    # Command 1
    pass_1 = [
        sys_consts.FFMPG,
        "-threads",
        Get_Thread_Count(),
        "-i",
        input_file,
        "-max_muxing_queue_size",
        "9999",
        "-pass",
        "1",
        "-passlogfile",
        passlog_file,
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
        "-s",
        f"{width}x{height}",
        "-r",
        str(frame_rate),
        "-c:a",
        "flac",
        "-threads",
        Get_Thread_Count(),
        output_file,
        "-y",
    ]

    # Command 2
    pass_2 = [
        sys_consts.FFMPG,
        "-threads",
        Get_Thread_Count(),
        "-i",
        input_file,
        "-max_muxing_queue_size",
        "9999",
        "-pass",
        "2",
        "-passlogfile",
        passlog_file,
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
        "-s",
        f"{width}x{height}",
        "-r",
        f"{frame_rate}",
        "-c:a",
        "flac",
        "-threads",
        Get_Thread_Count(),
        output_file,
        "-y",
    ]

    result, message = Execute_Check_Output(commands=pass_1, debug=False)

    if result == -1:
        return -1, message

    result, message = Execute_Check_Output(commands=pass_2, debug=False)

    if result == -1:
        return -1, message

    if file_handler.remove_file(passlog_del_file) == -1:
        return -1, f"Failed To Delete {passlog_del_file}"

    return 1, output_file


def Create_SD_Intermediate_Copy(input_file: str, output_folder: str) -> tuple[int, str]:
    """Creates an intermediate edit copy in SD resolution.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.

    Returns:
        tuple[int, str]:
            - arg 1: 1 if successful, -1 if an error occurred
            - arg 2: error message if error (-1) else output file path (1)
    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a non-empty str"

    assert (
        isinstance(output_folder, str) and output_folder.strip() != ""
    ), f"{output_folder=}. Must be a non-empty str"

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"

    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"

    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)
    output_file = file_handler.file_join(
        output_folder, f"{input_file_name}_sd_intermediate.mpg"
    )

    command = [
        sys_consts.FFMPG,
        "-threads",
        Get_Thread_Count(),
        "-i",
        input_file,
        "-max_muxing_queue_size",
        "9999",
        "-vf",
        "scale=720:-1",  # Change 720 to your desired width for SD
        "-c:v",
        "mpeg2video",
        # "-r",
        # str(frame_rate),  # set frame rate
        "-b:v",
        f"{sys_consts.AVERAGE_BITRATE}k",  # average video bitrate is kilobits/sec
        "-maxrate:v",
        "9000k",  # maximum video rate is 9000 kilobits/sec
        "-minrate:v",
        "0",  # minimum video rate is 0
        "-bufsize:v",
        "1835008",  # video buffer size is 1835008 bits
        "-packetsize",
        "2048",  # packet size is 2048 bits
        "-muxrate",
        "10080000",  # mux rate is 10080000 bits/sec
        "-g",
        "15",
        "-force_key_frames",
        "expr:if(isnan(prev_forced_n),1,eq(n,prev_forced_n+15))",
        # set key frame expression (Closes each GOP)
        "-pix_fmt",
        "yuv420p",  # use YUV 420p pixel format
        "-c:a",
        "pcm_s16le",
        "-y",
        "-threads",
        Get_Thread_Count(),
        output_file,
    ]

    if not file_handler.file_exists(output_file):
        result, message = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, message

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
) -> tuple[int, str]:
    """Converts an input video to MJPEG or H264 at supplied resolution and frame rate to make an edit copy that minimises
    generational losses. The video is transcoded to a file in the output folder.

       Args:
           input_file (str): The path to the input video file.
           output_folder (str): The path to the output folder.
           frame_rate (float): The frame rate to use for the output video.
           width (int): The width of the video
           height (int): The height of the video
           interlaced (bool, optional): Whether to use interlaced video. Defaults to True.
           bottom_field_first (bool, optional): Whether to use bottom field first. Defaults to True.
           mjpeg (bool, optional): True use MJPEG video as a Mezzanine video, False use H264.

       Returns:
           tuple[int, str]:
               - arg 1: 1 if ok, -1 if error
               - arg 2: error message if error (-1) else output file path (1)
    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a non-empty str"

    assert (
        isinstance(output_folder, str) and output_folder.strip() != ""
    ), f"{output_folder=}. Must be a non-empty str"
    assert (
        isinstance(frame_rate, float) and frame_rate > 0
    ), f"{frame_rate=}. Must be float > 0"
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(mjpeg, bool), f"{mjpeg=}. Must be bool"

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"

    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"

    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)

    black_border_size = 12
    field_order = []

    if interlaced:
        # black_box_filter, most likely dealing with analogue video, head switching noise best removed, and edges
        # are best covered for optimal compression
        filter_commands = [
            f"drawbox=x=0:y=0:w=iw:h={black_border_size}:color=black:t=fill",
            f"drawbox=x=0:y=ih-{black_border_size}:w=iw:h={black_border_size}:color=black:t=fill",
            (
                f"drawbox=x=0:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size * 2}:color=black:t=fill"
            ),
            (
                f"drawbox=x=iw-{black_border_size}:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size * 2}:color=black:t=fill"
            ),
        ]
        black_box_filter = ",".join(filter_commands)

        field_order = ["-top"]
        field_order.extend(f"{'0' if bottom_field_first else '1'}")
        video_filter = [
            "-vf",
            f"{black_box_filter},scale={width}x{height}",
        ]
    else:
        video_filter = []

    # Set bit rate based on video height
    if height <= 576:
        bit_rate = 25  # Set a lower bit rate for SD
    else:
        bit_rate = 35  # Set a higher bit rate for HD ~ 40

    if mjpeg:
        output_file = file_handler.file_join(output_folder, f"{input_file_name}.avi")

        command = [
            sys_consts.FFMPG,
            "-fflags",  # set ffmpeg flags
            "+genpts",  # generate presentation timestamps
            "-threads",
            Get_Thread_Count(),
            "-i",
            input_file,
            "-max_muxing_queue_size",
            "9999",
            *video_filter,
            "-c:v",
            "mjpeg",
            *field_order,
            "-q:v",
            "3",  # Adjust quality (lower is higher quality)
            "-b:v",
            f"{bit_rate}M",  # Set a high bit rate suitable for an edit master
            "-maxrate",
            f"{int(float(bit_rate) * 2)}M",
            "-bufsize",
            f"{int(float(bit_rate) * 5)}M",
            "-sn",  # Remove titles, causes problems sometimes
            "-r",
            str(frame_rate),  # set frame rate
            "-pix_fmt",
            "yuvj420p",  # use YUV 420p pixel format
            "-c:a",
            "aac",
            "-threads",
            Get_Thread_Count(),
            output_file,
            "-y",
        ]
    else:
        output_file = file_handler.file_join(output_folder, f"{input_file_name}.mkv")

        command = [
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            "-threads",
            Get_Thread_Count(),
            "-i",
            input_file,
            "-vsync",
            "cfr",
            "-max_muxing_queue_size",
            "9999",
            *video_filter,
            "-r",
            str(frame_rate),
            "-c:v",
            "libx264",
            "-sn",  # Remove titles
            "-pix_fmt",
            "yuv420p",  # Ensure the pixel format is compatible with Blu-ray
            "-crf",
            "17",  # Visually Lossless
            "-preset",
            "ultrafast",
            "-qp",
            "0",
            "-b:v",
            f"{bit_rate}M",
            "-maxrate",
            f"{int(float(bit_rate) * 2.5)}M",
            "-bufsize",
            f"{int(float(bit_rate) * 5)}M",
            "-g",
            f"{1}",  # Set the GOP size to match the DVD standard
            "-keyint_min",
            f"{1}",  # Set the minimum key frame interval to Match DVD (same as GOP size for closed GOP)
            "-sc_threshold",
            "0",  # Set the scene change threshold to 0 for frequent key frames
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-threads",
            Get_Thread_Count(),
            output_file,
            "-y",
        ]

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
) -> tuple[int, str]:
    """Converts an input video to MPEG2 at supplied resolution and frame rate at a high bit rate to make an edit
    copy that minimises generational losses. The video is transcoded to a file in the output folder.

        Args:
            input_file (str): The path to the input video file.
            output_folder (str): The path to the output folder.
            frame_rate (float): The frame rate to use for the output video.
            width (int) : The width of the video
            height (int) : The height of the video
            interlaced (bool, optional): Whether to use interlaced video. Defaults to True.
            bottom_field_first (bool, optional): Whether to use bottom field first. Defaults to True.
            iframe_only: (bool, optional): Generate iframe only. Defaults to False.

        Returns:
            tuple[int, str]:
                - arg 1: 1 if ok, -1 if error
                - arg 2: error message if error (-1) else output file path (1)
    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a non-empty str"

    assert (
        isinstance(output_folder, str) and output_folder.strip() != ""
    ), f"{output_folder=}. Must be a non-empty str"
    assert (
        isinstance(frame_rate, float) and frame_rate > 0
    ), f"{frame_rate=}. Must be float > 0"
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"

    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"

    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)

    output_file = file_handler.file_join(output_folder, f"{input_file_name}.mpg")

    black_border_size = 12

    if interlaced:
        # black_box_filter, most likely dealing with analogue video, head switching noise best removed, and edges
        # are best covered for optimal compression
        filter_commands = [
            f"drawbox=x=0:y=0:w=iw:h={black_border_size}:color=black:t=fill",
            f"drawbox=x=0:y=ih-{black_border_size}:w=iw:h={black_border_size}:color=black:t=fill",
            (
                f"drawbox=x=0:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size * 2}:color=black:t=fill"
            ),
            (
                f"drawbox=x=iw-{black_border_size}:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size * 2}:color=black:t=fill"
            ),
        ]
        black_box_filter = ",".join(filter_commands)

        field_order = f"fieldorder={'bff' if bottom_field_first else 'tff'}"
        video_filter = [
            "-vf",
            f"{black_box_filter},scale={width}x{height},{field_order}",
            "-flags:v:0",  # video flags for the first video stream
            "+ilme+ildct",  # include interlaced motion estimation and interlaced DCT
            "-alternate_scan:v:0",  # set alternate scan for the first video stream (interlace)
            "1",  # alternate scan value is 1,
        ]
    else:
        video_filter = []

    gop_size = 1 if iframe_only else 15

    # Set bit rate based on video height
    if height <= 576:
        bit_rate = 9  # Set a lower bit rate for SD
    else:
        bit_rate = 50  # Set a higher bit rate for HD

    command = [
        sys_consts.FFMPG,
        "-fflags",  # set ffmpeg flags
        "+genpts",  # generate presentation timestamps
        # "+igndts",
        "-threads",
        Get_Thread_Count(),
        "-i",
        input_file,
        "-max_muxing_queue_size",
        "9999",
        "mpeg2video",
        *video_filter,
        "-c:v",
        "-b:v",
        f"{bit_rate}M",  # Set a high bit rate suitable for an edit master
        "-maxrate",
        f"{int(float(bit_rate) * 2)}M",
        "-bufsize",
        f"{int(float(bit_rate) * 10)}M",
        "-sn",  # Remove titles
        "-r",
        str(frame_rate),  # set frame rate
        "-g",
        f"{gop_size}",
        "-force_key_frames",
        f"expr:if(isnan(prev_forced_n),1,eq(n,prev_forced_n+{gop_size}))",  # set key frame expression (Closes each GOP)
        "-pix_fmt",
        "yuv420p",  # use YUV 420p pixel format
        "-bf",
        "2",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-threads",
        Get_Thread_Count(),
        output_file,
    ]

    if not file_handler.file_exists(output_file):
        result, message = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, message

    return 1, output_file


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
) -> tuple[int, str]:
    """Converts an input video to H.264/5 at supplied resolution and frame rate.
    The video is transcoded to a file in the output folder.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int) : The width of the video
        height (int) : The height of the video
        interlaced (bool): Whether to use interlaced video. Defaults to True.
        bottom_field_first (bool): Whether to use bottom field first. Defaults to True.
        h265 (bool): Whether to use H.265. Defaults to False.
        high_quality (bool): Use a high quality encode. Defaults to True.
        iframe_only (bool): True id no GOP and all iframe desired else False. Defaults to False

    Returns:
        tuple[int, str]:
            - arg 1: 1 if ok, -1 if error
            - arg 2: error message if error (-1) else output file path (1)
    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a non-empty str"

    assert (
        isinstance(output_folder, str) and output_folder.strip() != ""
    ), f"{output_folder=}. Must be a non-empty str"
    assert (
        isinstance(frame_rate, float) and frame_rate > 0
    ), f"{frame_rate=}. Must be float > 0"
    assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
    assert isinstance(height, int) and height > 0, f"{height=}. Must be int > 0"
    assert isinstance(interlaced, bool), f"{interlaced=}. Must be bool"
    assert isinstance(bottom_field_first, bool), f"{bottom_field_first=}. Must be bool"
    assert isinstance(h265, bool), f"{h265=}. Must be bool"
    assert isinstance(high_quality, bool), f"{high_quality=}. Must be bool"

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"

    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"

    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, _ = file_handler.split_file_path(input_file)

    output_file = file_handler.file_join(output_folder, f"{input_file_name}.mp4")

    if not utils.Is_Complied():
        print(
            "DBG Trans_H26x"
            f" {input_file=} {frame_rate=} {width=} {height=} {interlaced=} {bottom_field_first=} ER"
            f" {'5M' if height <= 576 else '35M'=}"
        )

    gop_size = 1 if iframe_only else 15

    # Construct the FFmpeg command
    if h265:
        encoder = "libx265"
    else:
        encoder = "libx264"

    if high_quality:
        quality_preset = "slow"
    else:
        quality_preset = "superfast"

    black_border_size = 12

    if interlaced:
        # black_box_filter, most likely dealing with analogue video, head switching noise best removed, and edges
        # are best covered for optimal compression
        filter_commands = [
            f"drawbox=x=0:y=0:w=iw:h={black_border_size}:color=black:t=fill",
            f"drawbox=x=0:y=ih-{black_border_size}:w=iw:h={black_border_size}:color=black:t=fill",
            f"drawbox=x=0:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size * 2}:color=black:t=fill",
            f"drawbox=x=iw-{black_border_size}:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size * 2}:color=black:t=fill",
        ]
        black_box_filter = ",".join(filter_commands)

        field_order = f"fieldorder={'bff' if bottom_field_first else 'tff'}"
        video_filter = [
            "-vf",
            f"{black_box_filter},scale={width}x{height},{field_order}",
            "-flags:v:0",  # video flags for the first video stream
            "+ilme+ildct",  # include interlaced motion estimation and interlaced DCT
            "-alternate_scan:v:0",  # set alternate scan for first video stream (interlace)
            "1",  # alternate scan value is 1,
        ]
    else:
        video_filter = []

    command = [
        sys_consts.FFMPG,
        "-fflags",
        "+genpts",  # generate presentation timestamps
        "-threads",
        Get_Thread_Count(),
        "-i",
        input_file,
        "-vsync",
        "cfr",
        "-max_muxing_queue_size",
        "9999",
        *video_filter,
        "-r",
        str(frame_rate),
        "-c:v",
        encoder,
        "-sn",  # Remove titles
        "-pix_fmt",
        "yuv420p",  # Ensure the pixel format is compatible with Blu-ray
        "-crf",
        "17" if not h265 else "23",
        "-preset",
        quality_preset,
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-b:v",
        (
            "5M" if height <= 576 else "25M"
        ),  # SD Get low-bit rate everything else gets Blu-ray rate. Black Choice for now
        "-muxrate",
        "25M",  # Maximum Blu-ray mux rate in bits per second
        "-bufsize",
        "30M",
        "-g",
        f"{gop_size}",  # Set the GOP size to match the DVD standard
        "-keyint_min",
        f"{gop_size}",  # Set the minimum key frame interval to Match DVD (same as GOP size for closed GOP)
        "-sc_threshold",
        "0",  # Set the scene change threshold to 0 for frequent key frames
        "-threads",
        Get_Thread_Count(),
        output_file,
        "-y",
    ]

    if not file_handler.file_exists(output_file):
        result, message = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, message

    return 1, output_file


def Convert_To_PNG_Stream(
    image_filename: str, width: int, height: int, keep_aspect_ratio: bool = True
) -> (int, bytes):
    """
    Converts an image file to PNG format,  resizing it, and returns the PNG data as bytes.

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
    assert (
        isinstance(image_filename, str) and image_filename.strip() != ""
    ), f"{image_filename=}. Must be a non-empty str"
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
    print(f"DBG {' '.join(command)} ")
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
    gravity: str = "northwest",
) -> (int, bytes):
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
    assert (
        isinstance(base_image_data, bytes) and base_image_data.strip() != ""
    ), f"{base_image_data=}. Must be a non-empty bytes"
    assert (
        isinstance(overlay_image_data, bytes) and base_image_data.strip() != ""
    ), f"{base_image_data=}. Must be a non-empty bytes"
    assert isinstance(x, int) and x >= 0, f"{x=}. Must be a non-negative int"
    assert isinstance(y, int) and y >= 0, f"{y=}. Must be a non-negative int"
    assert (
        isinstance(gravity.lower(), str) and gravity.lower() in valid_gravities
    ), f"{gravity=} must be a gravity str"

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
    gravity: str = "northwest",
) -> (int, bytes):
    """Writes text on an image (provided as bytes) and returns the modified image as a byte string (PNG format).

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

    assert (
        isinstance(gravity.lower(), str) and gravity.lower() in valid_gravities
    ), f"{gravity=} must be a gravity str"

    assert (
        isinstance(image_data, bytes) and image_data != b""
    ), f"{image_data=}. Must be non-empty bytes"
    assert isinstance(text, str), f"{text=}. Must be str"
    assert (
        isinstance(font, str) and font.strip() != ""
    ), f"{font=}. Must be non-empty str"
    assert isinstance(x, int) and x > 0, f"{x=}. Must be int > 0"
    assert (
        isinstance(pointsize, int) and pointsize > 0
    ), f"{pointsize=}. Must be int > 0"
    assert isinstance(y, int) and y > 0, f"{y=}. Must be int > 0"

    assert isinstance(color, str) and color in colors, f"{color=} must be a string"

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
    """Writes text on a file

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
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be non-empty str"
    assert isinstance(text, str), f"{text=}. Must be str"
    assert (
        isinstance(font, str) and font.strip() != ""
    ), f"{font=}. Must be non-empty str"
    assert isinstance(x, int) and x > 0, f"{x=}. Must be int > 0"
    assert (
        isinstance(pointsize, int) and pointsize > 0
    ), f"{pointsize=}. Must be int > 0"
    assert isinstance(y, int) and y > 0, f"{y=}. Must be int > 0"

    assert isinstance(color, str) and color in colors, f"{color=} must be a string"

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
    """Gets the text dimensions in pixels

    Args:
        text (str): The text string to be measured
        font (str): The font of the text
        pointsize (int): The text point size

    Returns:
        tuple[int,int]: The width and height of the text. Both are -1 if there is an error
    """
    assert isinstance(text, str), f"{text=}. Must be str"
    assert (
        isinstance(font, str) and font.strip() != ""
    ), f"{font=}. Must be noon-empty str"
    assert (
        isinstance(pointsize, int) and pointsize > 0
    ), f"{pointsize=}. Must be int > 0"

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
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), "Input file must be a string."

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
    Cut and join a video based on start and end cut frames.

    Args:
        cut_video_def(Cut_Video_Def): Cut video definition file


    Returns:
        tuple[int, str]:
        - arg 1: Status code. Returns 1 if cut_video was successful, -1 otherwise.
        - arg 2: Empty string if all good, otherwise error message
    """

    ##### Helper
    def get_frame_dict(
        input_file: str, start_frame: int, frame_rate: float, time_window: int = 60
    ) -> tuple[int, dict]:
        """
        Uses FFProbe to get a GOP (Group Of Pictures) frame dictionary centered on the start time.

        Args:
            input_file (str): Path to input video file.
            start_frame (int): The frame we want the GOP dict for
            frame_rate (float): The frame rate of the video
            time_window (int): The time window in seconds centred around the start_frame in which we do a GOP search

        Returns:
            tuple[int, Optional[float]]: tuple containing result code and
            - arg 1: Result code 1 indicates success and -1 indicates failure.
            - arg 2: GOP Dict centered on the start time (has error entry when error occurs)

        """
        assert (
            isinstance(input_file, str) and input_file.strip() != ""
        ), "Input file path must be a string."
        assert (
            isinstance(start_frame, int) and start_frame >= 0
        ), f"{start_frame=} must be an int > 0"
        assert (
            isinstance(frame_rate, float) and frame_rate > 0
        ), f"{frame_rate=}. Must be a float"
        assert (
            isinstance(time_window, int) and time_window > 0
        ), f"{time_window=}. Must be int"

        start_time = 0 if start_frame == 0 else start_frame / frame_rate

        # Centre start time in the time window (start a bit before in case we are in the middle of a GO0!P)
        if start_time > time_window // 2:
            start_time -= time_window // 2

        commands = [
            sys_consts.FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=pkt_pts_time,pkt_duration_time,coded_picture_number,pict_type,best_effort_timestamp_time",
            "-of",
            "csv=print_section=0",
            "-read_intervals",
            f"{start_time}%+{time_window}",
            input_file,
        ]

        result, output = Execute_Check_Output(
            commands, debug=True, stderr_to_stdout=True
        )

        if result == -1:
            return -1, {"error": output}

        lines = output.strip().split("\n")
        frame_dict = {}
        start_frame_offset = int(start_time * frame_rate)
        absolute_frame_number = -1

        # Parse lines to get the frame info needed loaded into the frame_dict
        for line in lines:
            if line.strip() == "":
                continue

            line_items = line.split(",")

            if len(line_items) < 3:
                continue

            if absolute_frame_number == -1:
                absolute_frame_number = int(float(line_items[0]) * frame_rate) + 1

            computed_frame = float(line_items[0]) * frame_rate
            pts_time = line_items[1]
            pict_type = line_items[2]
            coded_picture_number = line_items[3]

            duration = float(pts_time) / frame_rate
            offset_frame = int(coded_picture_number) + start_frame_offset

            frame_dict[absolute_frame_number] = (
                pict_type,
                pts_time,
                duration,
                computed_frame,
                offset_frame,
                coded_picture_number,
                absolute_frame_number,
                float(line_items[0]),
            )

            absolute_frame_number += 1

        frame_list = sorted(frame_dict.items(), key=lambda x: x[0])

        for index in range(0, len(frame_list)):
            (
                frame_no,
                (
                    pict_type,
                    pts_time,
                    duration,
                    computed_frame,
                    offset_frame,
                    coded_picture_number,
                    frame_offset,
                    time_offset,
                ),
            ) = frame_list[index]

            if start_frame == frame_no or frame_no > start_frame:
                # Initialize frame_dict
                frame_dict = {}
                start_index = index
                if (
                    index > 0 and pict_type == "I" and frame_no > start_frame
                ):  # Have to use previous GOP, possible dropped frame issue
                    start_index = index - 1

                # Iterate backward to find the previous I-frame
                for backward_index in range(start_index, -1, -1):
                    (
                        backward_frame_no,
                        (
                            backward_pict_type,
                            backward_pts_time,
                            backward_duration,
                            backward_computed_frame,
                            backward_offset_frame,
                            backward_coded_picture_number,
                            backward_frame_offset,
                            backward_time_offset,
                        ),
                    ) = frame_list[backward_index]

                    frame_dict[backward_frame_no] = (
                        backward_pict_type,
                        backward_pts_time,
                        backward_duration,
                        backward_computed_frame,
                        backward_offset_frame,
                        backward_coded_picture_number,
                        backward_frame_offset,
                        backward_time_offset,
                    )

                    # Break if an I-frame is found
                    if backward_pict_type == "I":
                        break

                # Iterate forward to find frames until the next I-frame
                for forward_index in range(start_index + 1, len(frame_list)):
                    (
                        forward_frame_no,
                        (
                            forward_pict_type,
                            forward_pts_time,
                            forward_duration,
                            forward_computed_frame,
                            forward_offset_frame,
                            forward_coded_picture_number,
                            forward_frame_offset,
                            forward_time_offset,
                        ),
                    ) = frame_list[forward_index]

                    frame_dict[forward_frame_no] = (
                        forward_pict_type,
                        forward_pts_time,
                        forward_duration,
                        forward_computed_frame,
                        forward_offset_frame,
                        forward_coded_picture_number,
                        forward_frame_offset,
                        forward_time_offset,
                    )

                    # Break if an I-frame is found
                    if forward_pict_type == "I":
                        break

                return 1, frame_dict

        return -1, {"error ": "GOP Not Found"}

    def stream_copy_segment(
        input_file: str,
        output_file: str,
        start_frame: int,
        duration: float,
        frame_rate: float,
    ) -> tuple[int, str]:
        """
        Extracts a segment from an input video file using stream copy.

        Args:
            input_file (str): The input video file to extract the segment from.
            output_file (str): The output file where the segment will be saved.
            start_frame (inr): The start frame of the segment.
            duration (float): The duration of the segment (in seconds).
            frame_rate (float): The frame rate of the video.

        Returns:
            tuple[int, Optional[float]]: tuple containing result code and

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.

        """

        assert (
            isinstance(input_file, str) and input_file.strip() != ""
        ), f"{input_file=}. Must be a non-empty str"
        assert (
            isinstance(output_file, str) and output_file.strip() != ""
        ), f"{output_file=}. Must be a non-empty str"
        assert (
            isinstance(start_frame, int) and start_frame >= 0
        ), f"{start_frame=}. Must be int >= 0"
        assert (
            isinstance(duration, float) and duration > 0
        ), f"{duration=}. Must be float > 0"
        assert (
            isinstance(frame_rate, float) and frame_rate > 0
        ), f"{frame_rate=}. Must be float > 0"

        command = [
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            "-i",
            input_file,
            "-max_muxing_queue_size",  # Attempt to stop buffer issues on playback
            "9999",
            "-ss",
            Frame_Num_To_FFMPEG_Time(frame_num=start_frame, frame_rate=frame_rate),
            "-t",
            str(duration),
            "-avoid_negative_ts",
            "make_zero",
            "-c",
            "copy",
            output_file,
            "-y",
        ]

        result, output = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, output  # Output has error message

        return 1, ""

    def reencode_segment(
        input_file: str,
        output_file: str,
        start_frame: int,
        duration: float,
        frame_rate: float,
        gop_size: int,
        codec: str,
        encoding_details: Encoding_Details,
    ) -> tuple[int, str]:
        """
        Reencodes a segment from an input video file with specific settings.

        Args:
            input_file (str): The input video file to extract the segment from.
            output_file (str): The output file where the segment will be saved.
            start_frame (int): The start frame of the segment.
            duration (float): The duration of the segment (in seconds).
            frame_rate (float): The frame rate of the video.
            gop_size (int): The desired GOP (Group of Pictures) size.
            codec (str): The codec to use for reencoding.
            encoding_details (Encoding_Details): An instance containing encoding details.

        Returns:
            Tuple[int, str]: A tuple containing the status code and a message.

            - If the status code is 1, the operation was successful.
            - If the status code is -1, an error occurred, and the message provides details.
        """

        assert (
            isinstance(input_file, str) and input_file.strip() != ""
        ), f"{input_file=}. Must be a non-empty  str"
        assert (
            isinstance(output_file, str) and output_file.strip() != ""
        ), f"{output_file=}. Must be a non-empty str"
        assert (
            isinstance(start_frame, int) and start_frame >= 0
        ), f"{start_frame=}. Must be int > 0"
        assert (
            isinstance(duration, float) and duration > 0
        ), f"{duration=}. Must be float > 0"
        assert (
            isinstance(frame_rate, float) and frame_rate > 0
        ), f"{frame_rate=}. Must be float > 0"
        assert (
            isinstance(gop_size, int) and gop_size > 0
        ), f"{gop_size=}. Must be int > 0"
        assert (
            isinstance(codec, str) and codec.strip() != ""
        ), f"{codec=}. Must be a non-empty str"
        assert isinstance(
            encoding_details, Encoding_Details
        ), f"{encoding_details=}. Must Encoding_Details instance"

        video_filter = []  # Might be needed later
        command = [
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            # "+igndts",
            "-threads",
            Get_Thread_Count(),
            "-i",
            input_file,
            "-vsync",
            "cfr",
            *video_filter,
            "-tune",
            "fastdecode",
            "-ss",
            Frame_Num_To_FFMPEG_Time(frame_num=start_frame, frame_rate=frame_rate),
            "-t",
            str(duration),
            "-avoid_negative_ts",
            "make_zero",
            "-r",
            str(frame_rate),  # Set the output frame rate
            "-g",
            str(gop_size),  # Set the GOP size to match the input file
            "-keyint_min",
            str(gop_size),  # Set the minimum key frame interval to match input file
            "-sc_threshold",
            "0",  # Set the scene change threshold to 0 for frequent key frames
            "-c:v",
            codec,
            "-crf",
            "18",
            "-preset",
            "slow",
            "-b:v",
            str(encoding_details.video_bitrate),
            "-s",
            f"{encoding_details.video_width}x{encoding_details.video_height}",
            "-c:a",
            "copy",
            "-threads",
            Get_Thread_Count(),
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
    assert isinstance(
        cut_video_def, Cut_Video_Def
    ), f"{cut_video_def=}. Must be an instance of Cut_Video_Def"

    file_handler = file_utils.File()

    encoding_info: Encoding_Details = Get_File_Encoding_Info(cut_video_def.input_file)

    if encoding_info.error:
        return -1, encoding_info.error

    result, codec = Get_Codec(cut_video_def.input_file)

    if result == -1:  # codec carries error message
        return -1, codec

    _, _, input_extension = file_handler.split_file_path(cut_video_def.input_file)
    output_dir, _, _ = file_handler.split_file_path(cut_video_def.output_file)

    for time_window in range(
        10, 91, 10
    ):  # Iterate with time_window values from 10 to 90 in steps of 10 to try and get a gop dict - long gops might
        # need this
        result, start_frame_dict = get_frame_dict(
            input_file=cut_video_def.input_file,
            start_frame=cut_video_def.start_cut,
            frame_rate=cut_video_def.frame_rate,
            time_window=time_window,
        )

        if result == 1:
            break
    else:
        start_frame_dict = {}

    if result == -1:  # Going to Force a stream copy
        pass
        # return -1, "Failed To Get Start GOP"

    for time_window in range(
        10, 91, 10
    ):  # Iterate with time_window values from 10 to 90 in steps of 10 to try and get a gop dict - long gops might
        # need this
        result, end_frame_dict = get_frame_dict(
            input_file=cut_video_def.input_file,
            start_frame=cut_video_def.end_cut,
            frame_rate=cut_video_def.frame_rate,
            time_window=time_window,
        )

        if result == 1:
            break
    else:
        end_frame_dict = {}

    if result == -1:  # Going to Force a stream copy
        pass
        # return -1, "Failed To Get End GOP"

    # All iframes (e.g.: DV) means we can stream copy the video which is far more likely to process without issues
    # and has no reencoded start/end GOP so no quality hit (mind you who is going to notice a gop size encode!)
    stream_copy = False
    i_frame_count = sum(
        1
        for value in {**start_frame_dict, **end_frame_dict}.values()
        if value[0] == "I"
    )
    if i_frame_count == len({**start_frame_dict, **end_frame_dict}):
        stream_copy = True

    if (
        not stream_copy and start_frame_dict and end_frame_dict
    ):  # Got to have GOP blocks for frame accurate video cuts of compressed video
        # Note: sorting is required because sometimes the dicts unpacked unsorted!
        start_gop_block = []
        for key, item in start_frame_dict.items():
            if key >= cut_video_def.start_cut:
                # break
                start_gop_block.append((key, item))

        start_gop_block = sorted(start_gop_block, key=lambda x: x[0])

        end_gop_block = []

        for key, item in end_frame_dict.items():
            if key > cut_video_def.end_cut:
                break

            end_gop_block.append((key, item))

        end_gop_block = sorted(end_gop_block, key=lambda x: x[0])

        start_gop_block_start_frame = 0
        # start_gop_block_end_frame = 0
        start_gop_block_duration = 0.0

        stream_start_frame = 0
        stream_end_frame = 0

        end_gop_block_start_frame = 0
        # end_gop_block_end_frame = 0
        end_gop_block_duration = 0.0

        if start_gop_block:
            start_gop_block_start_frame = start_gop_block[0][0] + 1
            start_gop_block_end_frame = start_gop_block[-1][0]
            start_gop_block_duration = (
                start_gop_block_end_frame / cut_video_def.frame_rate
            ) - (start_gop_block_start_frame / cut_video_def.frame_rate)

            stream_start_frame = start_gop_block_end_frame - 3

        if end_gop_block:
            end_gop_block_start_frame = end_gop_block[0][0]
            end_gop_block_end_frame = end_gop_block[-1][0]
            end_gop_block_duration = (
                end_gop_block_end_frame / cut_video_def.frame_rate
            ) - (end_gop_block_start_frame / cut_video_def.frame_rate)
            stream_end_frame = end_gop_block_start_frame - 3

        stream_duration = (
            stream_end_frame - stream_start_frame
        ) / cut_video_def.frame_rate

        concat_files = []

        if start_gop_block_duration > 0:
            reencode_start_seg_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"reencode_start_segment_{cut_video_def.tag}",
                ext=input_extension,
            )

            result, message = reencode_segment(
                input_file=cut_video_def.input_file,
                output_file=reencode_start_seg_file,
                start_frame=start_gop_block_start_frame,
                duration=start_gop_block_duration,
                frame_rate=cut_video_def.frame_rate,
                gop_size=1,  # Force all frames to I frame in the GOP block, so we can cut in and out where we want,
                codec=codec,
                encoding_details=encoding_info,
            )

            if result == -1:
                return -1, message

            concat_files.append(reencode_start_seg_file)

        if stream_duration > 0:
            streamcopy_seg_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"stream_copy_segment_{cut_video_def.tag}",
                ext=input_extension,
            )

            result, message = stream_copy_segment(
                input_file=cut_video_def.input_file,
                output_file=streamcopy_seg_file,
                start_frame=stream_start_frame,
                duration=stream_duration,
                frame_rate=cut_video_def.frame_rate,
            )

            if result == -1:
                return -1, message

            concat_files.append(streamcopy_seg_file)

        if end_gop_block_duration > 0:
            reencode_end_seg_file = file_handler.file_join(
                dir_path=output_dir,
                file_name=f"reencode_end_segment_{cut_video_def.tag}",
                ext=input_extension,
            )

            result, message = reencode_segment(
                input_file=cut_video_def.input_file,
                output_file=reencode_end_seg_file,
                start_frame=end_gop_block_start_frame,
                duration=end_gop_block_duration,
                frame_rate=cut_video_def.frame_rate,
                gop_size=1,  # Force all frames to I frame in the GOP block, so we can cut in and out where we want,
                codec=codec,
                encoding_details=encoding_info,
            )

            if result == -1:
                return -1, message
            concat_files.append(reencode_end_seg_file)

        if concat_files:
            # Join re-encoded_start segment, stream_copy segment and re-encoded end segment to make the final frame
            # accurate cut file with nearly no loss
            result, message = Concatenate_Videos(
                temp_files=concat_files,
                output_file=cut_video_def.output_file,
                delete_temp_files=False,
                debug=False,
            )

            if result == -1:
                return -1, message

    else:
        # If video comprised of all I frames it will cut accurately, but compressed video with no key frames is not
        # going to cut accurately
        stream_duration = (
            cut_video_def.end_cut - cut_video_def.start_cut  # -1
        ) / cut_video_def.frame_rate

        try:
            result, message = stream_copy_segment(
                input_file=cut_video_def.input_file,
                output_file=cut_video_def.output_file,
                start_frame=cut_video_def.start_cut + 1,
                duration=stream_duration,
                frame_rate=cut_video_def.frame_rate,
            )

            if result == -1:
                return -1, message
        except Exception as e:
            return -1, f"Cut Video Failed - {sys_consts.SDELIM}{e}{sys_consts.SDELIM}"

    return 1, ""


def Frame_Num_To_FFMPEG_Time(frame_num: int, frame_rate: float) -> str:
    """
    Converts a frame number to an FFmpeg offset time string in the format "hh:mm:ss.mmm".

    Args:
        frame_num: An integer representing the frame number to convert.
        frame_rate: The video frame rate t

    Returns:
        A string representing the FFmpeg offset time in the format "hh:mm:ss.mmm".

    """
    assert (
        isinstance(frame_num, int) and frame_num >= 0
    ), f"{frame_num=}. Must be int > 0"
    assert (
        isinstance(frame_rate, float) and frame_rate > 0
    ), f"{frame_rate=}. Must be float > 0"

    offset_time = frame_num / frame_rate
    hours = int(offset_time / 3600)
    minutes = int((offset_time % 3600) / 60)
    seconds = int(offset_time % 60)
    milliseconds = int((offset_time % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def Split_Large_Video(
    source: str, output_folder: str, desired_chunk_size_gb: int
) -> tuple[int, str]:
    """
    Splits a large video file into smaller chunks using FFmpeg (stream copy).

    Args:
        source (str): The source path of the video file to split.
        output_folder (str): The folder where the split video files will be saved.
        desired_chunk_size_gb (int): The maximum size (in GB) for each split video chunk.

    Returns:
        tuple[int, str]:
            - arg1: 1 for success, -1 for failure.
            - arg2: An error message, or a list of chunk files delimitered by | if arg 1 is 1.
    """
    assert (
        isinstance(source, str) and source.strip()
    ), f"Invalid source video path: {source}"
    assert (
        isinstance(output_folder, str) and output_folder.strip()
    ), f"Invalid output folder: {output_folder}"
    assert (
        isinstance(desired_chunk_size_gb, int) and desired_chunk_size_gb > 0
    ), "Invalid max_size_gb"

    if not os.path.exists(source):
        return -1, f"Video file not found: {source}"

    if os.path.isdir(source):
        return -1, "Source path is a directory: {source}"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    chunk_file_list = []

    min_chunk_duration_s = 180  # Minimum chunk duration is 3 minutes

    file_handler = file_utils.File()

    _, source_name, source_extn = file_handler.split_file_path(source)

    encoding_info = Get_File_Encoding_Info(source)

    if encoding_info.error:
        return -1, encoding_info.error

    file_size = os.path.getsize(source)

    num_chunks = math.ceil(
        file_size / (desired_chunk_size_gb * (1024**3))
    )  # Convert GB to bytes

    chunk_duration = encoding_info.video_duration / num_chunks
    chunk_frames = chunk_duration * encoding_info.video_frame_rate // 1

    chunk_adjust = True

    while chunk_adjust:  # Need to make sure our last chunk is a good size
        for chunk_index in range(num_chunks):
            if chunk_index == num_chunks - 1:  # Last chunk
                start_frame = int(chunk_index * chunk_frames)
                end_frame = int(
                    (chunk_index + 1) * chunk_frames
                    if chunk_index < num_chunks - 1
                    else encoding_info.video_frame_count
                )

                num_frames = end_frame - start_frame
                duration = num_frames * encoding_info.video_frame_rate

                if duration < min_chunk_duration_s:
                    num_chunks += 1
                    break
        else:
            chunk_adjust = False

    for chunk_index in range(num_chunks):
        start_frame = int(chunk_index * chunk_frames)

        end_frame = int(
            (chunk_index + 1) * chunk_frames
            if chunk_index < num_chunks - 1
            else encoding_info.video_frame_count
        )

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
            return -1, message

    return 1, "|".join(chunk_file_list)


def Stream_Optimise(output_file: str) -> tuple[int, str]:
    """Optimizes a video file for streaming.

    Args:
        output_file (str): The path to the video file to be optimized.

    Returns:
        tuple[int, str]:
        - arg 1:  1 if the optimization was successful, and -1 otherwise
        - arg 2: If the optimization fails, the message will contain an error otherwise "".
    """
    assert (
        isinstance(output_file, str) and output_file.strip() != ""
    ), f"{output_file=}. Must be a non-empty string."

    command = [
        sys_consts.FFMPG,
        "-y",
        "-i",
        output_file,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
    ]

    # Run the FFmpeg command
    result, message = Execute_Check_Output(command)

    if result == -1:
        return -1, message

    return 1, ""


def Execute_Check_Output(
    commands: list[str],
    env: dict | None = None,
    execute_as_string: bool = False,
    debug: bool = False,
    shell: bool = False,
    stderr_to_stdout: bool = False,
    buffer_size: int = 1000000,
) -> tuple[int, str]:
    """Executes the given command(s) with the subprocess.run method.

    This wrapper provides better error and debug handling

    Args:
        commands (list[str]): non-empty list of commands and options to be executed.
        env (dict | None): A dictionary of environment variables to be set for the command. Defaults to None
        execute_as_string (bool): If True, the commands will be executed as a single string. Defaults to False
        debug (bool): If True, debug information will be printed. Defaults to False
        shell (bool): If True,  the command will be executed using the shell. Defaults to False
        stderr_to_stdout (bool): If True, the command will feed the stderr to stdout. Defaults to False.
        buffer_size (int): The size of the output buffer

    Returns:
        tuple[int, str]: A tuple containing the status code and the output of the command.

        - arg1: 1 if the command is successful, -1 if the command fails.
        - arg2: "" if the command is successful, if the command fails, an error message.
    """
    if env is None:
        env = dict()

    assert (
        isinstance(commands, list) and len(commands) > 0
    ), f"{commands=} must be a non-empty list of commands and options"
    assert isinstance(execute_as_string, bool), f"{execute_as_string=} must be bool"
    assert isinstance(debug, bool), f"{debug=} must be bool"
    assert isinstance(env, dict), f"{env=} must be dict"
    assert isinstance(shell, bool), f"{shell=} must be bool"
    assert isinstance(stderr_to_stdout, bool), f"{stderr_to_stdout=}. Must be bool"
    assert (
        isinstance(buffer_size, int) and buffer_size > 0
    ), f"{buffer_size=}. Must be int > 0"

    if debug and not utils.Is_Complied():
        print(f'DBG Call command ***   {" ".join(commands)}')
        print(f"DBG Call commands command list ***   {commands}")
        print(f"DBG Call commands shlex split  ***   {shlex.split(' '.join(commands))}")
        print("DBG Lets Do It!")

    # Define subprocess arguments
    subprocess_args = {
        "args": commands if not execute_as_string else shlex.split(" ".join(commands)),
        "shell": shell,
        "universal_newlines": True,
        "env": env,
        "bufsize": buffer_size,
    }

    if stderr_to_stdout:  # A ffmpeg special - stderr output is sometimes good stuff
        subprocess_args["stderr"] = subprocess.STDOUT
    else:
        # Redirect stderr to /dev/null (Unix-like) or nul (Windows)
        subprocess_args["stderr"] = (
            open("/dev/null", "w") if "posix" in os.name else open("nul", "w")
        )

    try:
        output = subprocess.check_output(**subprocess_args)
        return 1, output

    except subprocess.CalledProcessError as e:
        output = e.output

        if e.returncode == 1:
            return (
                1,
                output,
            )  # ffmpeg is special..again..sometimes return code 1 is a good thing
        else:
            if e.returncode == 127:
                message = (
                    f"Program Not Found Or Exited Abnormally \n {' '.join(commands)} ::"
                    f" {output}"
                )
            elif e.returncode <= 125:
                message = (
                    f"{e.returncode} Command Failed!\n {' '.join(commands)} :: {output}"
                )
            else:
                message = (
                    f"{e.returncode} Command Crashed!\n {' '.join(commands)} ::"
                    f" {output}"
                )

            if debug and not utils.Is_Complied():
                print(f"DBG {message} {e.returncode=} :: {output}")

            return -1, message  # Return -1 to indicate failure


def Get_DVD_Dims(aspect_ratio: str, dvd_format: str) -> Dvd_Dims:
    """Returns the DVD image dimensions. The hard-coded values are  mandated by the dvd_format and the
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
    """Returns the width of an image file in pixels.

    Args:
        image_file (str): The path to the image file.

    Returns:
        tuple[int,str]:
        - arg1: > 0 OK, -1 Error,
        - arg2: Error message ot "" if ok

    """
    assert (
        isinstance(image_file, str) and image_file.strip() != ""
    ), f"{image_file=}. Must be a path to a file"
    assert os.path.exists(image_file), f"{image_file=}. Does not exist"

    commands = [sys_consts.IDENTIFY, "-format", "%w", image_file]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return -1, message

    return int(message.strip()), ""


def Get_Image_Height(image_file: str) -> tuple[int, str]:
    """Returns the height of an image file in pixels.

    Args:
        image_file (str): The path to the image file.

    Returns:
        tuple[int,str]:
        - arg1: > 0 OK, -1 Error,
        - arg2: Error message ot "" if ok

    """
    assert (
        isinstance(image_file, str) and image_file.strip() != ""
    ), f"{image_file=}. Must be a path to a file"
    assert os.path.exists(image_file), f"{image_file=}. Does not exits"

    commands = [sys_consts.IDENTIFY, "-format", "%h", image_file]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return -1, message

    return int(message.strip()), ""


def Get_Image_Size(image_file: str) -> tuple[int, int, str]:
    """Returns the width and height of an image file in pixels.

    Args:
        image_file (str): The path to the image file.

    Returns:
        tuple[int,int,str]:
        - arg1: > 0 OK, -1 Error, width
        - arg2: > 0 OK, -1 Error, height
        - arg3: Error message ot "" if ok

    """
    assert (
        isinstance(image_file, str) and image_file.strip() != ""
    ), f"{image_file=}. Must be a path to a file"
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
    """Generate the image at the specified frame number from the video file.

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
    assert (
        isinstance(video_file, str) and video_file.strip() != ""
    ), f"{video_file=}. Must be non-empty str"
    assert (
        isinstance(frame_number, int) and frame_number >= 0
    ), f"{frame_number=}. Must be int >= 0"
    assert (
        isinstance(out_folder, str) and out_folder.strip() != ""
    ), f"{out_folder=}. Must be non-empty str"
    assert isinstance(button_height, int), f"{button_height=}. Must be int > 0"

    file_handler = file_utils.File()

    video_file_path, video_file_name, extn = file_handler.split_file_path(video_file)

    if (
        not file_handler.file_exists(video_file_path, video_file_name, extn)
        or not file_handler.path_exists(out_folder)
        or not file_handler.path_writeable(out_folder)
    ):
        return -1, ""

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
        f"select=eq(n\,{frame_number}) , scale=-1:{str(button_height)}",
        "-vframes",
        "1",
        image_file,
    ]

    result, message = Execute_Check_Output(commands=commands)

    if result == -1:
        return result, message

    return 1, image_file


def Get_File_Encoding_Info(video_file: str) -> Encoding_Details:
    """Returns the pertinent file encoding information as required for DVD creation

    Args:
        video_file (str): The video file being checked

    Returns:
        Video_Details: Check video_details.error if it is not an empty string an error occurred

    """
    debug = False
    video_file_details = Encoding_Details()

    if utils.Is_Complied():
        debug = False

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
        "%+1",
        video_file,
    ]

    result, message = Execute_Check_Output(
        commands=commands, debug=False, stderr_to_stdout=True
    )

    if result == -1:
        video_file_details.error = message
        return video_file_details

    json_string = message
    json_data = {}

    try:
        json_data = json.loads(json_string)

        audio_track_count = 0
        video_track_count = 0
        video_scan_type = ""

        video_file_details.video_duration = float(json_data["format"]["duration"])

        for frame in json_data["frames"]:
            if (
                "media_type" in frame
                and frame["media_type"] == "video"
                and video_scan_type == ""
            ):
                if video_scan_type == "" and "interlaced_frame" in frame:
                    video_scan_type = (
                        "interlaced"
                        if frame["interlaced_frame"] == 1
                        else "progressive"
                    )

                if video_scan_type == "interlaced" and "top_field_first" in frame:
                    if (
                        frame["top_field_first"] == "1"
                        and video_file_details.video_scan_order == ""
                    ):
                        video_file_details.video_scan_order = "tff"
                    else:
                        video_file_details.video_scan_order = "bff"
                break

        for stream in json_data["streams"]:
            if "codec_type" in stream and stream["codec_type"] == "video":
                video_track_count += 1

                if "codec_name" in stream:
                    video_file_details.video_format = stream["codec_name"]

                if "width" in stream:
                    video_file_details.video_width = int(stream["width"])

                if "height" in stream:
                    video_file_details.video_height = int(stream["height"])

                if "r_frame_rate" in stream and "/" in stream["r_frame_rate"]:
                    float_fr = int(stream["r_frame_rate"].split("/")[0]) / int(
                        stream["r_frame_rate"].split("/")[1]
                    )
                    video_file_details.video_frame_rate = [
                        math.floor(float_fr * 10**i) / 10**i for i in range(3)
                    ][-1]

                if (
                    "display_aspect_ratio" in stream
                    and ":" in stream["display_aspect_ratio"]
                ):
                    float_dar = int(stream["display_aspect_ratio"].split(":")[0]) / int(
                        stream["display_aspect_ratio"].split(":")[1]
                    )
                    video_file_details.video_dar = [
                        math.floor(float_dar * 10**i) / 10**i for i in range(3)
                    ][-1]

                if (
                    "sample_aspect_ratio" in stream
                    and ":" in stream["sample_aspect_ratio"]
                ):
                    float_par = int(stream["sample_aspect_ratio"].split(":")[0]) / int(
                        stream["sample_aspect_ratio"].split(":")[1]
                    )
                    video_file_details.video_par = [
                        math.floor(float_par * 10**i) / 10**i for i in range(3)
                    ][-1]

                if "display_aspect_ratio" in stream:
                    video_file_details.video_ar = stream["display_aspect_ratio"]

                if "field_order" in stream:
                    if stream["field_order"] in ("interlaced", "progressive"):
                        video_file_details.video_scan_type = stream["field_order"]

                if "nb_frames" in stream:
                    video_file_details.video_frame_count = int(stream["nb_frames"])

                if "bit_rate" in stream:
                    video_file_details.video_bitrate = int(stream["bit_rate"])

            elif "codec_type" in stream and stream["codec_type"] == "audio":
                audio_track_count += 1
                if "codec_name" in stream:
                    video_file_details.audio_format = stream["codec_name"]

                if "channels" in stream:
                    video_file_details.audio_channels = int(stream["channels"])

        video_file_details.audio_tracks = audio_track_count
        video_file_details.video_tracks = video_track_count

        # Attempted fix-ups
        if video_file_details.video_frame_count == 0:
            video_file_details.video_frame_count = math.floor(
                video_file_details.video_duration * video_file_details.video_frame_rate
            )

        if video_file_details.video_scan_type == "" and video_scan_type != "":
            video_file_details.video_scan_type = video_scan_type

        if video_file_details.video_scan_type == "" and (
            video_file_details.video_scan_order == "tff"
            or video_file_details.video_scan_order == "bff"
        ):
            video_file_details.video_scan_type = "interlaced"

        if video_file_details.video_bitrate == 0:
            if "bit_rate" in json_data["format"]:
                video_file_details.video_bitrate = int(json_data["format"]["bit_rate"])

        if (
            video_file_details.video_frame_rate == sys_consts.PAL_FRAME_RATE
            or video_file_details.video_frame_rate == sys_consts.PAL_FIELD_RATE
        ):
            video_file_details.video_standard = sys_consts.PAL
        elif (
            video_file_details.video_frame_rate == sys_consts.NTSC_FRAME_RATE
            or video_file_details.video_frame_rate == sys_consts.NTSC_FIELD_RATE
            or video_file_details.video_frame_rate == 30
        ):
            video_file_details.video_standard = sys_consts.NTSC

        if video_file_details.video_duration == 0:
            video_file_details.error = "Failed To Determine Duration"
        elif video_file_details.video_dar == 0:
            video_file_details.error = "Failed To Determine Display Aspect Ratio"
        elif video_file_details.video_par == 0:
            video_file_details.error = "Failed To Determine Pixel Aspect Ratio"
        elif video_file_details.video_ar == "":
            video_file_details.error = "Failed To Determine Aspect Ratio"
        elif video_file_details.video_frame_rate == 0:
            video_file_details.error = "Failed To Determine Frame Rate"
        elif video_file_details.video_bitrate == 0:
            video_file_details.error = "Failed To Determine Video Bit Rate"
        elif video_file_details.video_frame_count == 0:
            video_file_details.error = (
                "Failed To Determine The Number f Frames In The Video"
            )
        elif video_file_details.video_height == 0:
            video_file_details.error = "Failed To Determine The Video Height"
        elif video_file_details.video_width == 0:
            video_file_details.error = "Failed To Determine The Video Width"
        elif video_file_details.video_standard == 0:
            video_file_details.error = "Failed To Determine The Video Standard"
        elif video_file_details.audio_tracks == 0:
            video_file_details.error = "Failed To Determine The Number Of Audio Tracks"
        elif video_file_details.audio_format == "":
            video_file_details.error = "Failed To Determine The Audio Format"
        elif video_file_details.audio_channels == 0:
            video_file_details.error = (
                "Failed To Determine The Number Of Audio Channels"
            )
    except Exception as e:
        video_file_details.error = (
            f"Failed To Parse File {video_file} Error is {str(e)}"
        )

    if debug:
        print(f"==== File Encoding Details {video_file=} ")
        print("==== JSON DATA")
        pprint.pprint(json_data)
        print("==== Vide File details ")
        pprint.pprint(video_file_details)
        print("==== File Encoding Details End ")

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
    """Resizes an image to a specified size.

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
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a path to a file"
    assert (
        isinstance(out_file, str) and out_file.strip() != ""
    ), f"{out_file=}. Must be a path to a file"
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
    """Copies video file folders to an archive location. Files are checksumed to ensure copy is correct"""

    def __init__(self):
        pass

    def verify_files_integrity(self, folder_path: str, hash_algorithm="sha256") -> bool:
        """
        Verify the integrity of files in a folder by comparing their checksums with stored checksum files.

        Args:
            folder_path (str): The path of the folder containing files and checksum files.
            hash_algorithm (str): The hash algorithm to use (e.g., "md5", "sha256").
        Returns:
            bool: True if all files' checksums match the stored checksums, False otherwise.
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return False

        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)

                # Check if the file has a corresponding checksum file
                checksum_file_path = f"{file_path}.{hash_algorithm}"
                if not os.path.exists(checksum_file_path):
                    return False

                # Read the stored checksum from the checksum file
                with open(checksum_file_path, "r") as checksum_file:
                    expected_checksum = checksum_file.read()

                # Calculate the checksum of the file
                actual_checksum = self.calculate_checksum(file_path, hash_algorithm)

                # Compare the expected and actual checksums
                if actual_checksum != expected_checksum:
                    return False

        # All files have matching checksums
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
        if not os.path.exists(file_path):
            return ""

        hasher = hashlib.new(hash_algorithm)

        with open(file_path, "rb") as f:
            while True:
                data = f.read(65536)  # Read in 64K chunks
                if not data:
                    break
                hasher.update(data)

        return hasher.hexdigest()

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
        try:
            with open(file_path, "w") as f:
                f.write(checksum)
            return 1, ""
        except Exception as e:
            return -1, f"Error writing checksum file: {e}"

    def copy_folder_into_folders(
        self,
        source_folder: str,
        destination_root_folder: str,
        menu_title: str,
        folder_size_gb: int,
        hash_algorithm="sha256",
    ) -> tuple[int, str]:
        """
        Copy the contents of a source folder into subfolders of a specified size (in GB), verify checksum,
        and check disk space.

        Args:
            source_folder (str): The source folder whose contents will be copied.
            destination_root_folder (str): The root folder where subfolders will be created to store the copied contents.
            menu_title (str): The menu title is used in archive folder naming
            folder_size_gb (int): The maximum size (in GB) of each subfolder.
            hash_algorithm (str): The hash algorithm to use for checksum calculation (e.g., "md5", "sha256").

        Returns:
            tuple[int, str]:
                - arg1: 1 for success, -1 for failure.
                - arg2: An error message, or an empty string if successful.
        """
        assert (
            isinstance(source_folder, str) and source_folder.strip()
        ), f"Invalid source folder path: {source_folder}"
        assert (
            isinstance(destination_root_folder, str) and destination_root_folder.strip()
        ), f"Invalid destination root folder: {destination_root_folder}"
        assert (
            isinstance(menu_title, str) and menu_title.strip() != ""
        ), f"{menu_title=}. Must be non-empty str"
        assert (
            isinstance(folder_size_gb, int) and folder_size_gb > 0.5
        ), f"{folder_size_gb=}. Must be > 0.5"

        file_handler = file_utils.File()

        if not os.path.exists(source_folder):
            return -1, f"Source folder not found: {source_folder}"
        if not os.path.isdir(source_folder):
            return -1, f"Source path is not a directory: {source_folder}"

        if not os.path.exists(destination_root_folder):
            os.makedirs(destination_root_folder)

        if os.path.abspath(source_folder) == os.path.abspath(destination_root_folder):
            return -1, "Source and destination paths cannot be the same."

        try:
            # Calculate disk space required for copy
            folder_size_bytes = folder_size_gb * 1024**3  # Convert GB to bytes

            # Check if there's enough free space on the destination disk
            destination_disk_path = os.path.abspath(destination_root_folder)
            free_space, message = Get_Space_Available(destination_disk_path)

            if free_space == -1:
                return -1, message

            if free_space < folder_size_bytes:
                return -1, "Not enough free space on the destination disk."

            subfolder_index = 0
            current_subfolder_size_bytes = 0

            all_files = []
            for root, _, files in os.walk(source_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_creation_time = os.path.getctime(
                        file_path
                    )  # Get creation time
                    all_files.append((file_path, file_creation_time))

            all_files.sort(key=lambda x: x[1])  # Sort by creation time (second element)

            for file_path, _ in all_files:
                chunked_files = []
                delete_chunked = False

                # Check if the file is larger than max_chunk_size_gb and split it if needed
                if os.path.getsize(file_path) > folder_size_gb * 1024**3:
                    result, message = Split_Large_Video(
                        file_path, destination_root_folder, folder_size_gb
                    )

                    if result == -1:
                        return -1, message  # message is error

                    chunked_files = message.split(
                        "|"
                    )  # message is a list off chunked files delimitered by |
                    delete_chunked = True
                else:
                    chunked_files.append(file_path)

                for chunked_file in chunked_files:
                    source_checksum_before = self.calculate_checksum(
                        chunked_file, hash_algorithm
                    )

                    # Create disk_folder, if adding the file to the current subfolder would exceed the size limit
                    if (
                        subfolder_index == 0  # Always want disk 1 folder
                        or current_subfolder_size_bytes + os.path.getsize(chunked_file)
                        > folder_size_bytes
                    ):
                        subfolder_index += 1
                        current_subfolder_size_bytes = 0
                        destination_folder = os.path.join(
                            destination_root_folder,
                            f"{menu_title} - Disk_{subfolder_index:02}",
                        )

                        if file_handler.make_dir(destination_folder) == -1:
                            return (
                                -1,
                                "Failed to create directory: {destination_folder}",
                            )

                    # Copy the file to the current subfolder
                    destination_file_path = file_handler.file_join(
                        destination_folder, os.path.basename(chunked_file)
                    )
                    shutil.copy2(chunked_file, destination_file_path)

                    destination_checksum_after = self.calculate_checksum(
                        destination_file_path, hash_algorithm
                    )

                    if source_checksum_before != destination_checksum_after:
                        return -1, "File copy resulted in corruption."

                    checksum_file_path = f"{destination_file_path}.{hash_algorithm}"

                    result, message = self.write_checksum_file(
                        checksum_file_path, destination_checksum_after
                    )
                    if result == -1:
                        return -1, message

                    current_subfolder_size_bytes += os.path.getsize(
                        destination_file_path
                    )

                    if (
                        delete_chunked
                    ):  # Only chunked files created by file splitting are deleted.
                        result = file_handler.remove_file(chunked_file)

                        if result == -1:
                            return -1, f"Failed to delete chunked file : {chunked_file}"

            return 1, ""

        except Exception as e:
            return -1, f"Error copying folder into sub-folders: {e}"

    def write_checksum_file(self, checksum_file_path, checksum):
        checksum_file = open(checksum_file_path, "w")
        checksum_file.write(checksum)
        checksum_file.close()
        return 1, ""
