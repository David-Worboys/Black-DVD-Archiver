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
import math
import os
import os.path
import platform
import pprint
import shlex
import shutil
import subprocess
from typing import Generator

import psutil
import xmltodict

import file_utils
import sys_consts
import utils
from sys_config import Encoding_Details

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
            str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
    transcode_concat: str = "",
    debug: bool = True,
) -> tuple[int, str]:
    """
    Concatenates video files using ffmpeg.

    Args:
        temp_files (list[str]): List of input video files to be concatenated
        output_file (str): The output file name
        audio_codec (str): The audio codec to checked against (aac is special)
        delete_temp_files (bool): Whether to delete the temp files, defaults to False
        transcode_concat (str): Transcode temp_files as per format and then join files - Use only for problem files,
            as slow, defaults to False
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
    assert isinstance(transcode_concat, str) and transcode_concat in (
        "",
        "h264",
        "h265" "mpg",
        "mjpeg",
    ), f"{transcode_concat=}. Must be str - h264 | h265 | mpg | mjpeg"

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

    if transcode_concat:  # Very slow on a AMD2400G with 1GB of RAM :-)
        if transcode_concat in ("h264", "h265"):
            container_format = "mp4"
        elif transcode_concat == "mpg":
            container_format = "mpg"
        elif transcode_concat == "mjpeg":
            container_format = "avi"
        else:
            raise RuntimeError(f"Unknown transcode_concat {transcode_concat=}")

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
            transcode_file = file_handler.file_join(
                transcode_path, temp_name, container_format
            )

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
                match transcode_concat:
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
                            transcode_path, temp_name, "avi"
                        )
                        result, message = Transcode_MJPEG(
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
                            "-i",
                            video_file,
                            "-map",
                            "0",
                            "-c",
                            "copy",
                            "-sn",  # Remove titles
                            "-movflags",
                            "+faststart",
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
            str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
            "-y",
        ],
        debug=debug,
    )

    if debug:
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

    command = [
        sys_consts.XORRISO,
        "-as",
        "mkisofs",
        "-o",
        output_file,
        "-J",
        "-r",
        "-v",
        "-V",
        "DVD_VIDEO",
        "-graft-points",
        f"AUDIO_TS={input_dir}/AUDIO_TS",
        "VIDEO_TS=" + input_dir,
    ]

    return Execute_Check_Output(command)


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
        return -1, str(e)


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
    Converts an input vile file into a ffv1 compressed video suitable for permanent archival storage.

    ffv1 is a permanent archival format widely accepted by archival institutions world wode

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int) : The width of the video
        height (int) : The height of the video

    Returns:
        tuple[int, str]:
            arg 1: 1 if ok, -1 if error
            arg 2: error message if error else ""

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
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
        output_file,
        "-y",
    ]

    # Command 2
    pass_2 = [
        sys_consts.FFMPG,
        "-threads",
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
            arg 1: 1 if successful, -1 if an error occurred
            arg 2: error message if an error occurred, else an empty string
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
        output_file,
    ]

    if not file_handler.file_exists(output_file):
        result, message = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, message

    return 1, output_file


def Transcode_MJPEG(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
) -> tuple[int, str]:
    """Converts an input video to MPEG2 at supplied resolution and frame rate at a really high bit rate to make an edit
    copy that minimises generational losses. The video is transcoded to a file in the output folder.

        Args:
            input_file (str): The path to the input video file.
            output_folder (str): The path to the output folder.
            frame_rate (float): The frame rate to use for the output video.
            width (int) : The width of the video
            height (int) : The height of the video
            interlaced (bool, optional): Whether to use interlaced video. Defaults to True.
            bottom_field_first (bool, optional): Whether to use bottom field first. Defaults to True.

        Returns:
            tuple[int, str]:
                arg 1: 1 if ok, -1 if error
                arg 2: error message if error else ""
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

    output_file = file_handler.file_join(output_folder, f"{input_file_name}.avi")

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
        bit_rate = 9  # Set a lower bit rate for SD
    else:
        bit_rate = 25  # Set a higher bit rate for HD ~ 50

    command = [
        sys_consts.FFMPG,
        "-fflags",  # set ffmpeg flags
        "+genpts",  # generate presentation timestamps
        "-threads",
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
        f"{int(float(bit_rate) * 4)}M",
        "-bufsize",
        f"{int(float(bit_rate) * 2)}M",
        "-sn",  # Remove titles, causes problems sometimes
        "-r",
        str(frame_rate),  # set frame rate
        "-pix_fmt",
        "yuvj420p",  # use YUV 420p pixel format
        "-c:a",
        "mp3",
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
    """Converts an input video to MPEG2 at supplied resolution and frame rate at a really high bit rate to make an edit
    copy that minimises generational losses. The video is transcoded to a file in the output folder.

        Args:
            input_file (str): The path to the input video file.
            output_folder (str): The path to the output folder.
            frame_rate (float): The frame rate to use for the output video.
            width (int) : The width of the video
            height (int) : The height of the video
            interlaced (bool, optional): Whether to use interlaced video. Defaults to True.
            bottom_field_first (bool, optional): Whether to use bottom field first. Defaults to True.

        Returns:
            tuple[int, str]:
                arg 1: 1 if ok, -1 if error
                arg 2: error message if error else ""
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
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
            arg 1: 1 if ok, -1 if error
            arg 2: error message if error else ""
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
            f"drawbox=x=0:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size*2}:color=black:t=fill",
            f"drawbox=x=iw-{black_border_size}:y={black_border_size}:w={black_border_size}:h=ih-{black_border_size*2}:color=black:t=fill",
        ]
        black_box_filter = ",".join(filter_commands)

        field_order = f"fieldorder={'bff' if bottom_field_first else 'tff' }"
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
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
        "17",
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
        output_file,
        "-y",
    ]

    if not file_handler.file_exists(output_file):
        result, message = Execute_Check_Output(commands=command, debug=False)

        if result == -1:
            return -1, message

    return 1, output_file


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
            "-max_muxing_queue_size", # Attempt to stop buffer issues on playback
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

        video_filter = [] # Might be needed later
        command = [
            sys_consts.FFMPG,
            "-fflags",
            "+genpts",  # generate presentation timestamps
            # "+igndts",
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
            str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
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
        start_gop_block_end_frame = 0
        start_gop_block_duration = 0.0

        stream_start_frame = 0
        stream_end_frame = 0

        end_gop_block_start_frame = 0
        end_gop_block_end_frame = 0
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
            cut_video_def.end_cut - cut_video_def.start_cut - 1
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
        except Exception:
            pass

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

    def _find_keys(node: list[str] | dict, key_value: str) -> Generator:
        """Find an XML key based on a key value

        Args:
            node (list[str] | dict): The XML node
            key_value: (str) : Value key being matched against

        Returns:
            Generator:
        """
        if isinstance(node, list):
            for node_list in node:
                for xml_key in _find_keys(node_list, key_value):
                    yield xml_key
        elif isinstance(node, dict):
            if key_value in node:
                yield node[key_value]

            for node_dict in node.values():
                for xml_key in _find_keys(node_dict, key_value):
                    yield xml_key

    assert (
        isinstance(video_file, str) and video_file.strip() != ""
    ), f"{video_file=}. Must bbe a non-empy str"

    debug = True

    if utils.Is_Complied():
        debug = False

    fmt = "--output=XML"

    video_file_details = Encoding_Details()

    try:
        media_xml = subprocess.check_output(
            [sys_consts.MEDIAINFO, fmt, video_file],
            universal_newlines=True,
            stderr=subprocess.STDOUT if debug else subprocess.DEVNULL,
        ).strip()

        video_info = xmltodict.parse(media_xml)

        if debug:
            print(f"=========== Video Info Debug {video_file} ===========")
            pprint.pprint(video_info)
            print("=========== Video Info Debug ===========")

        track_info = list(_find_keys(video_info, "track"))

        for tracks in track_info:
            for track_dict in tracks:
                if not isinstance(track_dict, dict):
                    video_file_details.error = (
                        f"Failed To Get Encoding Details : {video_file}"
                    )

                    return video_file_details

                track_type = ""

                for key, value in track_dict.items():
                    if not isinstance(value, str) or not value.strip():
                        continue

                    if key == "@type":
                        track_type = value

                    if track_type == "General":
                        match key:
                            case "AudioCount":
                                video_file_details.audio_tracks = int(value)
                            case "VideoCount":
                                video_file_details.video_tracks = int(value)
                    if track_type == "Video":
                        match key:
                            case "BitRate":
                                video_file_details.video_bitrate = int(value)
                            case "Format":
                                video_file_details.video_format = value
                            case "Width":
                                video_file_details.video_width = int(value)
                            case "Height":
                                video_file_details.video_height = int(value)
                            case "PixelAspectRatio":
                                video_file_details.video_par = float(value)
                            case "DisplayAspectRatio":
                                video_file_details.video_dar = float(value)

                                if value.startswith("1.33"):
                                    video_file_details.video_ar = sys_consts.AR43
                                else:
                                    video_file_details.video_ar = sys_consts.AR169

                            case "Duration":
                                video_file_details.video_duration = float(value)
                            case (
                                "ScanType_Original"
                                | "ScanOrder"
                                | "ScanType"
                                | "ScanOrder_Original"
                            ):
                                if (
                                    value == "MBAFF"
                                ):  # H264/H25 adaptive interlaced indication
                                    video_file_details.video_scan_type = "Interlaced"
                                else:
                                    if key.lower() in (
                                        "ScanOrder_Original",
                                        "ScanOrder",
                                        "ScanType",
                                    ):
                                        if (
                                            video_file_details.video_scan_type.strip()
                                            == ""
                                        ):
                                            video_file_details.video_scan_type = value

                                if (
                                    value.strip()
                                    and "bff" in value.lower()
                                    or "tff" in value.lower()
                                ):
                                    video_file_details.video_scan_order = value
                                    video_file_details.video_scan_type = (  # Only TFF and BFF are interlaced
                                        "Interlaced"
                                    )

                            case (
                                "FrameRate"
                                | "FrameRate_Maximum"
                                | "FrameRate_Original"
                            ):
                                video_file_details.video_frame_rate = float(value)
                            case "Standard":
                                if value.upper() in (sys_consts.PAL, sys_consts.NTSC):
                                    video_file_details.video_standard = value
                            case "FrameCount":
                                video_file_details.video_frame_count = int(value)
                    if track_type == "Audio":
                        match key:
                            case "Format":
                                video_file_details.audio_format = value
                            case "Channels":
                                video_file_details.audio_channels = int(value)

                    if key == "@type":
                        track_type = value

    except subprocess.CalledProcessError as call_error:
        if call_error.returncode == 127:  # Should not happen
            video_file_details.error = f"{sys_consts.MEDIAINFO} Not Found"
        elif call_error.returncode <= 125:
            video_file_details.error = (
                f" {call_error.returncode} {sys_consts.MEDIAINFO} Failed!\n {fmt}"
            )
        else:
            video_file_details.error = (
                f" {call_error.returncode} {sys_consts.MEDIAINFO} Crashed!\n {fmt}"
            )
    except OSError as call_error:
        video_file_details.error = (
            f"{sys_consts.MEDIAINFO} Failed! To Run\n {fmt} \n {call_error}"
        )

    result, codec = Get_Codec(video_file)

    if result == -1:
        video_file_details.error = "Failed To Get Video Codec"
        return video_file_details

    video_file_details.video_format = codec  # Decided to use FFMPEG codec extraction as it is different from Mediainfo

    # Emergency measures were key info is missing information try ffprobe
    if video_file_details.video_scan_type.strip() == "":
        video_file_details.video_scan_type = "Progressive"

    if (
        video_file_details.video_frame_rate == 0
        or video_file_details.video_frame_count == 0
    ):
        ffprobe_command = [
            sys_consts.FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "v:0",  # Select only the video stream
            "-show_entries",
            "stream=duration,r_frame_rate,nb_frames",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_file,
        ]

        try:
            result, output = Execute_Check_Output(commands=ffprobe_command, debug=False)

            if result == -1 or output.strip() == "":
                video_file_details.error = (
                    f"Failed To Get Encoding Details : {video_file}"
                )
                return video_file_details

            values = output.strip().split("\n")

            # Comes out in this order - who knows why
            frame_rate = values[0]
            duration = values[1]
            frame_count = values[2]

        except subprocess.CalledProcessError as e:
            # Handle any errors or exceptions here
            print(f"Error: {e}")
            video_file_details.error = (
                f"Failed To Get Encoding Details : {video_file} : {e}"
            )
            return video_file_details

        if video_file_details.video_duration == 0:
            if duration != "N/A":
                video_file_details.video_duration = float(duration)

            if video_file_details.video_duration == 0:
                video_file_details.error = (
                    f"Failed To Get Video_Duration Encoding Details : {video_file} "
                )
                return video_file_details

        if video_file_details.video_frame_rate == 0:
            if "/" in frame_rate:
                nominator = float(frame_rate.split("/")[0])
                denominator = float(frame_rate.split("/")[1])
                video_file_details._video_frame_rate = nominator / denominator
            else:
                video_file_details._video_frame_rate = float(frame_rate.strip())

            if video_file_details.video_frame_rate == 0:
                video_file_details.error = (
                    f"Failed To Get Video_Frame_Rate Encoding Details : {video_file} "
                )
                return video_file_details

        if video_file_details.video_frame_count == 0:
            if frame_count == "N/A":
                video_file_details.video_frame_count = int(
                    video_file_details.video_duration
                    * video_file_details.video_frame_rate
                )
            else:
                video_file_details.video_frame_count = int(frame_count)

            if video_file_details.video_frame_count == 0:
                video_file_details.error = (
                    f"Failed To Get Video_Frame_Count Encoding Details : {video_file} "
                )
                return video_file_details

    if (
        not video_file_details.video_standard
    ):  # Emergency measures to try and determine if video is PAL or NTSC
        if (
            video_file_details.video_width == sys_consts.PAL_SPECS.width_43
            and video_file_details.video_height == sys_consts.PAL_SPECS.height_43
            and video_file_details.video_frame_rate == sys_consts.PAL_SPECS.frame_rate
        ):
            video_file_details.video_standard = sys_consts.PAL
        elif (
            video_file_details.video_width == sys_consts.NTSC_SPECS.width_43
            and video_file_details.video_height == sys_consts.NTSC_SPECS.height_43
            and video_file_details.video_frame_rate == sys_consts.NTSC_SPECS.frame_rate
        ):
            video_file_details.video_standard = sys_consts.NTSC
        # At this point it is the wild wild west, se take a punt on field rates to determine DVD standard
        # Most likely dealing with HD def video
        elif video_file_details.video_frame_rate == sys_consts.PAL_SPECS.field_rate:
            video_file_details.video_standard = sys_consts.PAL
        elif video_file_details.video_frame_rate == sys_consts.NTSC_SPECS.field_rate:
            video_file_details.video_standard = sys_consts.NTSC
        else:  # At this point, I will need to think of something better!
            video_file_details.video_standard = "N/A"

    if debug:
        print(f"=========== video_details Debug {video_file} ===========")
        pprint.pprint(video_file_details)
        print("=========== video_details Debug ===========")

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
