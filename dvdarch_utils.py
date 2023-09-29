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
from typing import Generator, Optional

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


def Concatenate_Videos(
    temp_files: list[str],
    output_file: str,
    audio_codec: str = "",
    delete_temp_files: bool = False,
) -> tuple[int, str]:
    """
    Concatenates video files using ffmpeg.

    Args:
        temp_files (list[str]): List of input video files to be concatenated
        output_file (str): The output file name
        audio_codec (str, optional): The audio codec to checked against (aac is special)
        delete_temp_files (bool, optional): Whether to delete the temp files, defaults to False

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

    file_handler = file_utils.File()
    out_path, _, _ = file_handler.split_file_path(output_file)
    file_list_txt = file_handler.file_join(out_path, "video_data_list", "txt")

    if not file_handler.path_writeable(out_path):
        return -1, f"Can Not Be Write To {out_path}!"

    for video_file in temp_files:
        if not file_handler.file_exists(video_file):
            return -1, f"File {video_file} Does Not Exist!"

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
            "-f",
            "concat",
            "-safe",
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
            str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
            "-y",
        ]
    )

    if result == -1:
        file_handler.remove_file(file_list_txt)
        return -1, message

    # Remove the file list and temp files
    if file_handler.remove_file(file_list_txt) == -1:
        return -1, f"Failed to delete text file: {file_list_txt}"

    if delete_temp_files:
        for file in temp_files:
            if file_handler.file_exists(file):
                if file_handler.remove_file(file) == -1:
                    return -1, f"Failed to delete temp file: {file}"

    return 1, ""


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
    except subprocess.CalledProcessError as e:
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

    except subprocess.CalledProcessError as e:
        print(f"DBG Render Error {e=}")
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
    If a border color is provided a rectangle of that color is drawn
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


def Transcode_H26x(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    h265: bool = False,
    high_quality=True,
) -> tuple[int, str]:
    """Converts an input video to H.264/5 at supplied resolution and frame rate.
    The video is transcoded to a file in the output folder.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int) : The width of the video
        height (int) : The height of the video
        interlaced (bool, optional): Whether to use interlaced video. Defaults to True.
        bottom_field_first (bool, optional): Whether to use bottom field first. Defaults to True.
        h265 (bool, optional): Whether to use H.265. Defaults to False.
        high_quality (bool, optional): Use a high quality encode. Defaults to True.

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

    file_handler = file_utils.File()

    if not file_handler.path_exists(output_folder):
        return -1, f"{output_folder} Does not exist"

    if not file_handler.path_writeable(output_folder):
        return -1, f"{output_folder} Cannot Be Written To"

    if not file_handler.file_exists(input_file):
        return -1, f"File Does Not Exist {input_file}"

    _, input_file_name, input_file_extn = file_handler.split_file_path(input_file)

    output_file = file_handler.file_join(output_folder, f"{input_file_name}_edit.mp4")

    # Construct the FFmpeg command
    if h265:
        encoder = "libx265"
    else:
        encoder = "libx264"

    if high_quality:
        quality_preset = "slow"
    else:
        quality_preset = "superfast"

    video_filter = [
        "-vf",
        f"scale={width}x{height}",
    ]

    if interlaced:
        video_filter = video_filter + [
            f"fieldorder={'bff' if bottom_field_first else 'tff' }",
            "-flags:v:0",  # video flags for the first video stream
            "+ilme+ildct",  # include interlaced motion estimation and interlaced DCT
            "-alternate_scan:v:0",  # set alternate scan for first video stream (interlace)
            "1",  # alternate scan value is 1
        ]

    command = [
        sys_consts.FFMPG,
        "-i",
        input_file,
        *video_filter,
        "-r",
        str(frame_rate),
        "-c:v",
        encoder,
        "-crf",
        "18",
        "-preset",
        quality_preset,
        "-c:a",
        "pcm_s16le",
        "-threads",
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
        "-y",
        output_file,
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


def Get_File_Cut_Command(
    input_file: str, output_file, start_frame: int, end_frame: int, frame_rate: float
) -> tuple[list, str]:
    """
    Generates an FFmpeg command to cut a segment from the input video file based on frame numbers. The start and end
    frames are specified, along with the frame rate of the video. The resulting FFmpeg command can be used to
    extract the desired segment of the video file and save it to the specified output file.

    Args:
        input_file (str): The path to the input video file.
        output_file (str): The path to the output video file.
        start_frame (int): The frame number to start the segment from.
        end_frame (int): The frame number to end the segment at.
        frame_rate (float): The frame rate of the video.

    Returns:
        tuple[list, str]:
            - A list containing the FFmpeg command arguments or an empty list if an error occurs.
            - An error message as a string, or an empty string if no error occurred.
    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), f"{input_file=}. Must be a non-empty str"
    assert (
        isinstance(output_file, str) and output_file.strip()
    ), f"{output_file=}. Must be a non-empty str"
    assert (
        isinstance(start_frame, int) and start_frame >= 0
    ), f"{start_frame=}. Must be an int >= 0"
    assert (
        isinstance(end_frame, int) and end_frame >= 0 and end_frame > start_frame
    ), f"{end_frame=}. Must be an int >= 0 and > start"
    assert (
        isinstance(frame_rate, float) and frame_rate > 0
    ), f"{frame_rate=}. Must be a float >= 0"

    result, message = Get_Codec(input_file)

    if result == -1:
        return [], message

    codec = message

    # Calculate the start and end times of the segment based on the frame numbers
    start_time = start_frame / frame_rate
    end_time = end_frame / frame_rate

    # Calculate the nearest key frames before and after the cut
    result, before_key_frame = Get_Nearest_Key_Frame(input_file, start_time, "prev")

    if result == -1:
        return [], "Failed To Get Before Key Frame"

    result, after_key_frame = Get_Nearest_Key_Frame(input_file, end_time, "next")

    if result == -1:
        return [], "Failed To Get After Key Frame"

    # Set the start time and duration of the segment to re-encode
    segment_start = before_key_frame if before_key_frame is not None else start_time

    segment_duration = (
        after_key_frame - segment_start
        if after_key_frame is not None
        else end_time - segment_start
    )

    # command = [sys_consts.FFMPG,"-v","debug", "-i", input_file] #DBG
    command = [sys_consts.FFMPG, "-i", input_file]

    # Check if re-encoding is necessary
    command += ["-map", "0:v", "-map", "0:a"]

    if before_key_frame is not None and after_key_frame is not None:
        # Re-encode the segment
        if not utils.Is_Complied():
            print(
                "DBG Re-Encode Seg"
                f" {start_frame=} {end_frame=} {segment_duration=} {before_key_frame=} {after_key_frame=}"
            )

        command += ["-force_key_frames", f"{before_key_frame}+1"]
        command += ["-tune", "fastdecode"]
        command += ["-ss", str(segment_start)]
        command += ["-t", str(segment_duration)]
        command += ["-avoid_negative_ts", "make_zero"]
        command += ["-c:v", codec]
        command += ["-c:a", "copy"]
        command += [
            "-threads",
            str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
        ]
        command += [output_file, "-y"]
    else:
        # Copy the segment
        if not utils.Is_Complied():
            print(
                "DBG Copy Segment"
                f" {start_frame=} {end_frame=} {segment_duration=} {before_key_frame=} {after_key_frame=}"
            )

        command += ["-ss", str(segment_start)]
        command += ["-t", str(segment_duration)]
        command += ["-avoid_negative_ts", "make_zero"]
        command += ["-c", "copy"]
        command += [output_file, "-y"]

    return command, ""


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
        print(f"Source path is a directory: {source}")
        return -1, "Source path is a directory: {source}"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    chunk_file_list = []

    min_chunk_duration_s = 180  # Minimum chunk duration is 3 minutes

    file_handler = file_utils.File()

    source_dir, source_name, source_extn = file_handler.split_file_path(source)

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
        for i in range(num_chunks):
            if i == num_chunks - 1:  # Last chunk
                start_frame = int(i * chunk_frames)
                end_frame = int(
                    (i + 1) * chunk_frames
                    if i < num_chunks - 1
                    else encoding_info.video_frame_count
                )

                num_frames = end_frame - start_frame
                duration = num_frames * encoding_info.video_frame_rate

                if duration < min_chunk_duration_s:
                    num_chunks += 1
                    break
        else:
            chunk_adjust = False

    for i in range(num_chunks):
        start_frame = int(i * chunk_frames)
        end_frame = int(
            (i + 1) * chunk_frames
            if i < num_chunks - 1
            else encoding_info.video_frame_count
        )

        chunk_file = file_handler.file_join(
            output_folder, f"{source_name}_{i + 1}", source_extn
        )
        chunk_file_list.append(chunk_file)

        command, error_message = Get_File_Cut_Command(
            input_file=source,
            output_file=chunk_file,
            start_frame=start_frame,
            end_frame=end_frame,
            frame_rate=encoding_info.video_frame_rate,
        )

        if error_message:
            return -1, error_message

        result, output = Execute_Check_Output(commands=command)

        if result == -1:
            return -1, output  # Output contains error message now
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


def Get_Nearest_Key_Frame(
    input_file: str, time: float, direction: str
) -> tuple[int, Optional[float]]:
    """
    Uses FFprobe to get the position of the nearest key frame before or after the given time.

    Args:
        input_file (str): Path to input video file.
        time (float): Time in seconds for which the nearest key frame is to be found.
        direction (str): Direction of search. "prev" for nearest key frame before time, "next" for after time.

    Returns:
        tuple[int, Optional[float]]: tuple containing result code and
        - arg 1: Result code 1 indicates success and -1 indicates failure.
        - arg 2: Position of nearest key frame if there is one or None if there is no key frame. If error None
    """
    assert (
        isinstance(input_file, str) and input_file.strip() != ""
    ), "Input file path must be a string."
    assert isinstance(time, float), "Time must be a float."
    assert isinstance(direction, str) and direction in [
        "prev",
        "next",
    ], "Direction must be either 'prev' or 'next'."

    # Use FFprobe to get the position of the nearest key frame before or after the given time
    commands = [
        sys_consts.FFPROBE,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-skip_frame",
        "nokey",
        "-show_entries",
        "frame=pkt_pts_time",
        "-of",
        "csv=print_section=0",
        "-read_intervals",
        "%+#10",  # Specify 10 sec frane duration to analyze
        "-threads",
        str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
        input_file,
    ]

    result, output = Execute_Check_Output(commands, debug=False)

    if result == -1:
        return -1, None

    lines = [line.strip().replace("\n", "") for line in output.split("\n")]

    if lines:
        if lines[0] == "":
            return 1, None

    output = output.strip()

    key_frames = [float(t) for t in output.split("\n")]

    if direction == "prev":
        key_frames_before = [t for t in key_frames if t < time]
        if key_frames_before:
            return 1, max(key_frames_before)
        else:
            return -1, None

    elif direction == "next":
        key_frames_after = [t for t in key_frames if t > time]
        if key_frames_after:
            return 1, min(key_frames_after)
        else:
            return -1, None


def Execute_Check_Output(
    commands: list[str],
    env: dict | None = None,
    execute_as_string: bool = False,
    debug: bool = False,
    shell: bool = False,
) -> tuple[int, str]:
    """Executes the given command(s)  with the subprocess.check_output method.
    This wrapper provides better error and debug handling

    Args:
        commands (list[str]): A non-empty list of commands and options to be executed.
        env (dict, optional): A dictionary of environment variables to be set for the command. Defaults to an empty dictionary.
        execute_as_string (bool, optional): If True, the commands will be executed as a single string. Defaults to False.
        debug (bool, optional): If True, debug information will be printed. Defaults to False.
        shell (bool, optional): If True, the command will be executed using the shell. Defaults to False.

    Returns:
        tuple[int, str]: A tuple containing the status code and the output of the command.

        - arg1: 1 if the command is successful, -1 if the command fails.
        - arg2: "" if the command is successful, if the command fails, an error message.
    """
    if env is None:
        env = dict()

    assert (
        isinstance(commands, list) and len(commands) > 0
    ), f"{commands=}. Must be non-empty list of commands and options"
    assert isinstance(execute_as_string, bool), f"{execute_as_string=}. Must be bool"
    assert isinstance(debug, bool), f"{debug=}. Must be bool"
    assert isinstance(env, dict), f"{env=}. Must be dict"
    assert isinstance(shell, bool), f"{shell=}. Must be bool"

    for option in commands:
        assert isinstance(option, str), f"{option=}. Must be str"

    try:
        if debug:
            print(f'DBG Call command ***   {" ".join(commands)}')
            print(f"DBG Call commands command lisr ***   {commands}")
            print(
                "DBG Call commands shlex split  ***  "
                f" {shlex.split(' '.join(commands))}"
            )
            print(f"DBG Lets Do It!")
            output = subprocess.check_output(
                commands if not execute_as_string else " ".join(commands),
                universal_newlines=True,
                shell=shell,
                env=env,
            )
            print(f"DBG And Done {output=}")
        else:
            output = subprocess.check_output(
                commands if not execute_as_string else " ".join(commands),
                universal_newlines=True,
                shell=shell,
                # stderr=subprocess.STDOUT,
                stderr=subprocess.DEVNULL,
                env=env,
            )
    except (subprocess.CalledProcessError, FileNotFoundError) as call_error:
        if debug:
            print(f"DBG Call Error *** {call_error.returncode=} {call_error=}")

        if call_error.returncode == 127:  # Should not happen
            message = f"Program Not Found Or Exited Abnormally \n {' '.join(commands)}"
        elif call_error.returncode <= 125:
            message = f" {call_error.returncode} Command Failed!\n {' '.join(commands)}"
        else:
            message = (
                f" {call_error.returncode} Command  Crashed!\n {' '.join(commands)}"
            )
        print(f"DBG {sys_consts.PROGRAM_NAME} Exception: {message=}")
        return -1, message

    return 1, output


def Get_DVD_Dims(aspect_ratio: str, dvd_format: str) -> Dvd_Dims:
    """Returns the DVD image dimensions. The hard coded values are  mandated by the dvd_format and the
    aspect ratio and must not be changed.  PAL is 720 x 576 and NTSC is 720 x 480 and is always stored
    that way on a DVD. But the display aspect ratio can be flagged on a DVD (PAL is 1024 x 576 and NTSC is
    850x480) but it is not stored that way on the DVD

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
                storage_width=720,
                storage_height=480,
                display_width=853,
                display_height=480,
            )

        else:  # 4:3
            return Dvd_Dims(
                storage_width=720,
                storage_height=480,
                display_width=720,
                display_height=540,
            )
    else:  # PAL
        if aspect_ratio.upper() == sys_consts.AR169:
            return Dvd_Dims(
                storage_width=720,
                storage_height=576,
                display_width=1024,
                display_height=576,
            )
        else:  # 4:3
            return Dvd_Dims(
                storage_width=720,
                storage_height=576,
                display_width=720,
                display_height=576,
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
            for i in node:
                for x in _find_keys(i, key_value):
                    yield x
        elif isinstance(node, dict):
            if key_value in node:
                yield node[key_value]
            for j in node.values():
                for x in _find_keys(j, key_value):
                    yield x

    assert (
        isinstance(video_file, str) and video_file.strip() != ""
    ), f"{video_file=}. Must bbe a non-empy str"

    debug = True

    fmt = "--output=XML"

    video_file_details = Encoding_Details()

    try:
        mi = subprocess.check_output(
            [sys_consts.MEDIAINFO, fmt, video_file],
            universal_newlines=True,
            stderr=subprocess.STDOUT if debug else subprocess.DEVNULL,
        ).strip()

        video_info = xmltodict.parse(mi)

        if debug and not utils.Is_Complied():
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
                            case "ScanOrder_Original" | "ScanOrder":
                                video_file_details.video_scan_order = value
                            case "ScanType_Original" | "ScanType":
                                video_file_details.video_scan_type = value
                            case "FrameRate":
                                video_file_details.video_frame_rate = float(value)
                            case "Standard":
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
        video_file_details.error = f"{sys_consts.MEDIAINFO} Failed! To Run\n {fmt}"

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
        result, colors = Execute_Check_Output(
            [
                sys_consts.CONVERT,
                input_file,
                "-unique-colors",
                out_file,
            ]
        )

        if result == -1:  # colors contains the error message in this case
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
        Copy the contents of a source folder into subfolders of a specified size (in GB), verify checksum, and check disk space.

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
                    result, result = Split_Large_Video(
                        file_path, destination_root_folder, folder_size_gb
                    )

                    if result == -1:
                        return -1, result

                    chunked_files = result.split("|")
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
                            f"Disk_{subfolder_index:02} - {menu_title}",
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
