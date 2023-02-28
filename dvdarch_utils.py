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
from typing import Generator

import psutil
import xmltodict

import sys_consts
import utils

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
    "darkgray": "#A9A9A9",
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
    "rosybrown": "#bc8f8f",
    "saddlebrown": "#8b4513",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
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
    "turquoise": "#40e0d0",
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
        return (usage.free, "")
    except Exception as e:
        return (-1, str(e))


def get_color_names() -> list:
    """Return a list of color names in the colors dictionary.

    Returns:
        list[str]: A list of color names as strings.
    """
    return sorted(list(colors.keys()), key=lambda x: x[0].upper())


def get_hex_color(color: str) -> str:
    """This function returns the hexadecimal value for a given color name.

    Args:
        color_name (str): The name of the color to look up.

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
) -> bytes:
    """Returns a png byte string an example of what a font looks like

    Args:
        font_file (str): The font file path
        pointsize (int): The text point size. Optional -1 autocalcs
        text(str): The example text placed in the png
        text_color(str): The example text color in the png
        background_color(str): The background color of the png
        width(int): Width of png in pixels. Optional -1 autocalcs
        height(int): Height of png in pixels. Optional -1 autocalcs

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

    if not os.path.exists(font_file):
        return b""

    try:
        if pointsize == -1:
            # Find the optimal font size to fit the text within the bounding box
            # Determine the initial bounds for the binary search
            low, high = 1, 200
            text_width, text_height = get_text_dims(
                text=text, font=font_file, pointsize=10
            )

            # If the text dimensions are larger than the bounding box, return an empty string
            if (width > 0 and text_width > width) or (
                height > 0 and text_height > height
            ):
                return b""

            # Binary search for the optimal font size
            while low <= high:
                mid = (low + high) // 2

                text_width, text_height = get_text_dims(
                    text=text, font=font_file, pointsize=mid
                )

                if (width > 0 and text_width > width) or (
                    height > 0 and text_height > height
                ):
                    high = mid - 1
                else:
                    pointsize = mid
                    low = mid + 1
        command = [
            sys_consts.CONVERT,
            "-size",
            f"{width}x{height}",
            f"xc:{background_color}",
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


def execute_check_output(
    commands: list[str],
    env: dict = dict(),
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
                f'DBG Call commands shlex split  ***   {shlex.split(" ".join(commands))}'
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
    except subprocess.CalledProcessError as call_error:
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
        - arg1: > 0 OK, -1 Error,
        - arg2: > 0 OK, -1 Error,
        - arg3: Error message ot "" if ok

    """
    # TODO: Test this, do not think I have used it yet
    assert (
        isinstance(image_file, str) and image_file.strip() != ""
    ), f"{image_file=}. Must be a path to a file"
    assert os.path.exists(image_file), f"{image_file=}. Does not exits"

    commands = [sys_consts.IDENTIFY, "-format", "%w %h", image_file]

    result, message = execute_check_output(commands=commands)

    if result == -1:
        return -1, -1, message

    return int(message.strip()), ""


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

    file_handler = utils.File()

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

    image_file = f"{out_folder}{file_handler.ossep}{video_file_name}.jpg"

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


def get_file_encoding_info(video_file: str) -> dict:
    """Returns the pertinent file encoding information as required for DVD creation

    Args:
        video_file (str): The video file being checked

    Returns:
        dict: Dict of key value pairs describing the various encoding parameters.
            Value is a list, Indices 0: Group, 1 the value, 2 Description
            Check video_details["error"][1] if it is not an empty string an error occurred

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

    debug = False

    fmt = "--output=XML"

    video_details = {
        "error": ["Error", "", "error"],
        "audio_tracks": ["General", 0, "AudioCount"],
        "video_tracks": ["General", 0, "VideoCount"],
        "audio_format": ["Audio", "", "Format"],
        "audio_channels": ["Audio", 0, "Channels"],
        "video_format": ["Video", "", "Format"],
        "video_width": ["Video", 0, "Width"],
        "video_height": ["Video", 0, "Height"],
        "video_ar": ["Video", 0.0, ""],
        "video_par": ["Video", 0.0, "PixelAspectRatio"],
        "video_dar": ["Video", 0, 0, "DisplayAspectRatio"],
        "video_duration": ["Video", 0.0, "Duration"],
        "video_scan_order": ["Video", "", "ScanOrder_Original"],
        "video_scan_type": ["Video", "", "ScanType_Original"],
        "video_frame_rate": ["Video", 0.0, "FrameRate"],
        "video_standard": ["Video", "", "Standard"],
        "video_frame_count": ["Video", 0, "FrameCount"],
    }

    try:
        mi = subprocess.check_output(
            [sys_consts.MEDIAINFO, fmt, video_file],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
        ).strip()

        video_info = xmltodict.parse(mi)

        if debug:
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

                    for track_def in video_details.values():
                        if track_def[0] == track_type and key == track_def[2]:
                            if type(track_def[1]) is int:
                                track_def[1] = int(value)
                            elif type(track_def[1]) is float:
                                track_def[1] = float(value)
                            else:
                                track_def[1] = value

        if (
            video_details["video_width"][1] > 0
            and video_details["video_height"][1] > 0
            and video_details["video_par"][1] > 0
        ):
            video_details["video_ar"][1] = (
                video_details["video_width"][1] / video_details["video_height"][1]
            ) * video_details["video_par"][1]

    except subprocess.CalledProcessError as call_error:
        video_details["error"][1] = f"{call_error}"
        print(f"{call_error=}")

        if call_error.returncode == 127:  # Should not happen
            video_details["error"][1] = f"{sys_consts.MEDIAINFO} Not Found"
        elif call_error.returncode <= 125:
            video_details["error"][
                1
            ] = f" {call_error.returncode} {sys_consts.MEDIAINFO} Failed!\n {fmt}"
        else:
            video_details["error"][
                1
            ] = f" {call_error.returncode} {sys_consts.MEDIAINFO} Crashed!\n {fmt}"
    except OSError as call_error:
        video_details["error"][1] = f"{sys_consts.MEDIAINFO} Failed! To Run\n {fmt}"

    if debug:
        print(f"=========== video_details Debug {video_file} ===========")
        pprint.pprint(video_details)
        print("=========== video_details Debug ===========")

    return video_details


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
