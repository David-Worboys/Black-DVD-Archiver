"""
    DVD archiver specic utility functions.

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
import os
import os.path
import platform
import pprint
import shlex
import subprocess
from typing import Generator, Optional

import psutil
import xmltodict

import file_utils
import sys_consts
import utils
from configuration_classes import Encoding_Details

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
class dvd_dims:
    storage_width: int = -1
    storage_height: int = -1
    display_width: int = -1
    display_height: int = -1


def concatenate_videos(
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
    result, message = execute_check_output(
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
        ],
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


def create_dvd_iso(input_dir: str, output_file: str) -> tuple[int, str]:
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

    return execute_check_output(command)


def get_space_available(path: str) -> tuple[int, str]:
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


def get_color_names() -> list:
    """Return a list of color names in the colors dictionary.

    Returns:
        list[str]: A list of color names as strings.
    """
    return sorted(list(colors.keys()), key=lambda x: x[0].upper())


def get_hex_color(color: str) -> str:
    """This function returns the hexadecimal value for a given color name.

    Args:
        color (str): The name of the color to look up.

    Returns:
        str: The hexadecimal value for the given color name or "" if color unknown.

    """
    assert (
        isinstance(color, str) and color.strip() != "" and color in get_color_names()
    ), f"{color=}. Must be string  in {', '.join(get_color_names())} "

    color = color.lower()

    if color in colors:
        hex_value = colors[color]
    else:
        hex_value = ""

    return hex_value


def get_colored_rectangle_example(width: int, height: int, color: str) -> bytes:
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
    ), f"{color=} must be a string in {', '.join(get_color_names())}"

    size = f"{width}x{height}"
    command = ["convert", "-size", size, f"xc:{color}", "png:-"]

    try:
        return subprocess.check_output(command, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        return b""


def get_font_example(
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
    ), f"{text_color=} must be a string in {', '.join(get_color_names())}"
    assert (
        isinstance(background_color, str) and background_color in colors
    ), f"{background_color=} must be a string in {', '.join(get_color_names())}"
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
            text_width, text_height = get_text_dims(
                text=text, font=font_file, pointsize=10
            )

            # If the text dimensions are larger than the bounding box, return an empty string
            if (0 < width < text_width) or (0 < height < text_height):
                return -1, b""

            # Binary search for the optimal font size
            while low <= high:
                mid = (low + high) // 2

                text_width, text_height = get_text_dims(
                    text=text, font=font_file, pointsize=mid
                )

                if (0 < width < text_width) or (0 < height < text_height):
                    high = mid - 1
                else:
                    pointsize = mid
                    low = mid + 1

        result, background_hex = make_opaque(color=background_color, opacity=opacity)

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
        return -1, b""


def get_fonts() -> list[tuple[str, str]]:
    """Returns a list of built-in fonts

    Returns:
        list[tuple[str, str]]: A list of tuples, where each tuple contains the font name as the first
        element and font file path as the second element.

    """
    font_list = []

    # Directories to search for font files
    font_dirs = [
        "/usr/share/fonts/",
        "/usr/local/share/fonts/",
        os.path.expanduser("~/.fonts/"),
        "/Library/Fonts/",
        ".",
        os.path.expanduser("~/Library/Fonts/"),
    ]

    # Windows font directory
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


def make_opaque(color: str, opacity: float) -> tuple[int, str]:
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
    ), f"{color=} must be a string in {', '.join(get_color_names())}"
    assert 0.0 <= opacity <= 1.0, "Opacity must be between 0.0 and 1.0"

    hex_color = get_hex_color(color)

    if hex_color == "":
        return -1, f"Invalid System Color {color}"

    opacity_hex = hex(int(255 * opacity)).lstrip("0x").rjust(2, "0").upper()

    return 1, hex_color + opacity_hex


def create_transparent_file(width: int, height: int, out_file: str, border_color=""):
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

    return execute_check_output(commands=command)


def overlay_file(
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

    return execute_check_output(commands=command)


def overlay_text(
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

    background_color_hex = get_hex_color(background_color)

    if background_color_hex == "":
        return -1, f"Unknown color {background_color}"

    result, text_hex = make_opaque(color=text_color, opacity=1)

    if result == -1:
        return -1, f"Invalid System Color {text_color}"

    result, background_hex = make_opaque(color=background_color, opacity=opacity)

    if result == -1:
        return -1, f"Invalid System Color {text_color}"

    text_width, text_height = get_text_dims(
        text=text, font=text_font, pointsize=text_pointsize
    )

    if text_width == -1:
        return -1, "Could Not Get Text Width"

    image_width, message = get_image_width(in_file)

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

    return execute_check_output(commands=command)


def Transcode_H26x(
    input_file: str,
    output_folder: str,
    frame_rate: float,
    width: int,
    height: int,
    interlaced: bool = True,
    bottom_field_first: bool = True,
    h265: bool = False,
    high_quality = True
) -> tuple[int, str]:
    """Converts an input video to H.264/5 at supplied resolution and frame rate.
    The video is transcoded to a file in the output folder.

    Args:
        input_file (str): The path to the input video file.
        output_folder (str): The path to the output folder.
        frame_rate (float): The frame rate to use for the output video.
        width (int) : The width of the video
        height (int) : The height of the cideo
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
        result, message = execute_check_output(commands=command, debug=False)

        if result == -1:
            return -1, message

    return 1, output_file


def write_text_on_file(
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

    return execute_check_output(commands=command)


def get_text_dims(text: str, font: str, pointsize: int) -> tuple[int, int]:
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
    result, message = execute_check_output(
        [
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
        ]
    )

    if result == -1:
        return -1, -1

    # Convert the message to width and height
    dimensions = message.strip().split("x")
    width = int(dimensions[0])
    height = int(dimensions[1])

    return width, height


def get_codec(input_file: str) -> tuple[int, str]:
    """
    Get the codec name of the video file using FFprobe.

    Args:
        input_file (str): Path to the input video file.

    Returns:
        tuple[int, str]:
        - arg 1: Status code. Returns 1 if the codec name was obtained successfully, -1 otherwise.
        - arg 2: Codec name if obtained successfully, otherwisr error message

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

    result, output = execute_check_output(commands)

    if result == -1:
        return -1, "Failed To Get Codec Name!"

    return 1, output.strip()


def stream_optimise(output_file: str) -> tuple[int, str]:
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
    result, message = execute_check_output(command)

    if result == -1:
        return -1, message

    return 1, ""


def get_nearest_key_frame(
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

    result, output = execute_check_output(commands, debug=False)

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


def execute_check_output(
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
            output = subprocess.check_output(
                commands if not execute_as_string else " ".join(commands),
                universal_newlines=True,
                shell=shell,
                env=env,
            )
        else:
            output = subprocess.check_output(
                commands if not execute_as_string else " ".join(commands),
                universal_newlines=True,
                shell=shell,
                stderr=subprocess.STDOUT,
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
        return -1, message

    return 1, output


def get_dvd_dims(aspect_ratio: str, dvd_format: str) -> dvd_dims:
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
            return dvd_dims(
                storage_width=720,
                storage_height=480,
                display_width=853,
                display_height=480,
            )

        else:  # 4:3
            return dvd_dims(
                storage_width=720,
                storage_height=480,
                display_width=720,
                display_height=540,
            )
    else:  # PAL
        if aspect_ratio.upper() == sys_consts.AR169:
            return dvd_dims(
                storage_width=720,
                storage_height=576,
                display_width=1024,
                display_height=576,
            )
        else:  # 4:3
            return dvd_dims(
                storage_width=720,
                storage_height=576,
                display_width=720,
                display_height=576,
            )


def get_image_width(image_file: str) -> tuple[int, str]:
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

    result, message = execute_check_output(commands=commands)

    if result == -1:
        return -1, message

    return int(message.strip()), ""


def get_image_height(image_file: str) -> tuple[int, str]:
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

    result, message = execute_check_output(commands=commands)

    if result == -1:
        return -1, message

    return int(message.strip()), ""


def get_image_size(image_file: str) -> tuple[int, int, str]:
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

    result, message = execute_check_output(commands=commands)

    if result == -1:
        return -1, -1, message

    width, height = message.strip().split()

    return int(width), int(height), ""


def generate_menu_image_from_file(
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

    video_file_path, video_file_name = file_handler.split_head_tail(video_file)

    if "." in video_file_name:
        extn = video_file_name.split(".")[-1]
        video_file_name = ".".join(video_file_name.split(".")[0:-1])
    else:
        extn = ""

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

    result, message = execute_check_output(commands=commands)

    if result == -1:
        return result, message

    return 1, image_file


def get_file_encoding_info(video_file: str) -> Encoding_Details:
    """Returns the pertinent file encoding information as required for DVD creation

    Args:
        video_file (str): The video file being checked

    Returns:
        Video_Details: Check video_details.error if it is not an empty string an error occurred

    """

    def find_keys(node: list[str] | dict, key_value: str) -> Generator:
        """Find an XML key based on a key value

        Args:
            node (list[str] | dict): The XML node
            key_value: (str) : Value key being matched against

        Returns:
            Generator:
        """
        if isinstance(node, list):
            for i in node:
                for x in find_keys(i, key_value):
                    yield x
        elif isinstance(node, dict):
            if key_value in node:
                yield node[key_value]
            for j in node.values():
                for x in find_keys(j, key_value):
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
            stderr=subprocess.STDOUT,
        ).strip()

        video_info = xmltodict.parse(mi)

        if debug and not utils.Is_Complied():
            print(f"=========== Video Info Debug {video_file} ===========")
            pprint.pprint(video_info)
            print("=========== Video Info Debug ===========")

        video_details: dict[str, list[str, int, str]]
        track_info = list(find_keys(video_info, "track"))

        for tracks in track_info:
            for track_dict in tracks:
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

    if debug and not utils.Is_Complied():
        print(f"=========== video_details Debug {video_file} ===========")
        pprint.pprint(video_file_details)
        print("=========== video_details Debug ===========")

    return video_file_details  # video_details


def resize_image(
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
        result, colors = execute_check_output(
            [
                sys_consts.CONVERT,
                input_file,
                "-unique-colors",
                out_file,
            ]
        )

        if result == -1:  # colurs contains the eror message in this case
            return result, colors

        cmd += ["-remap", colors]

    result, _ = execute_check_output(commands=cmd + [out_file])

    if result == -1:
        return -1, "Could Not Resize Image"

    return 1, ""
