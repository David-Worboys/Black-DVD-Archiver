"""
System wide constants for dvd archiver.

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

import datetime
from collections import namedtuple
from typing import Final

import QTPYGUI.file_utils as file_utils


def COPYRIGHT_YEAR() -> str:
    """
    The COPYRIGHT_YEAR function returns the current year if it is 2022, otherwise it returns a string of the
    form '2022-&lt;current_year&gt;'.

    Returns:
        str: The current year, or the current year and the next if it's 2022

    """
    return f"{'2022' if str(datetime.date.today().year) == '2022' else '2022-' + str(datetime.date.today().year)}"


executable_folder = file_utils.App_Path()

file_sep = file_utils.File().ossep

PROGRAM_NAME: Final[str] = "Black DVD Archiver"
PROGRAM_VERSION: Final[str] = "β4.0.0"
AUTHOR: Final[str] = "David Worboys"
LICENCE: Final[str] = "GNU V3 GPL"

VERSION_TAG = (
    f"{PROGRAM_VERSION} {LICENCE} (c){COPYRIGHT_YEAR()} {AUTHOR} (-:alumnus Moyhu"
    " Primary School et al.:-)"
)

SDELIM = (  # Used to delimit strings - particularly non-translatable sections of strings
    "||"
)
PAL: Final[str] = "PAL"
NTSC: Final[str] = "NTSC"
AR169: Final[str] = "16:9"
AR43: Final[str] = "4:3"
PAL_FRAME_RATE: Final[int] = 25
PAL_FIELD_RATE: Final[int] = 50
NTSC_FRAME_RATE: Final[float] = 30000 / 1001
NTSC_FIELD_RATE: Final[float] = 60000 / 1001
AVERAGE_BITRATE: Final[int] = 5500  # kilobits/sec
SINGLE_SIDED_DVD_SIZE: Final[int] = 40258730  # kb ~ 4.7GB DVD5
DOUBLE_SIDED_DVD_SIZE: Final[int] = 72453177  # kb ~ 8.5GB DVD9
BLUERAY_ARCHIVE_SIZE: Final[str] = "25GB"
DVD_ARCHIVE_SIZE: Final[str] = "4GB"
TRANSCODE_NONE: Final[str] = "Original"
TRANSCODE_FFV1ARCHIVAL: Final[str] = "ffv1"
TRANSCODE_H264: Final[str] = "H264"
TRANSCODE_H265: Final[str] = "H265"
PAL_SPECS = namedtuple(
    "PAL_SPECS",
    [
        "width_43",
        "height_43",
        "width_169",
        "height_169",
        "frame_rate",
        "field_rate",
    ],
)(
    width_43=720,
    height_43=576,
    width_169=1024,
    height_169=576,
    frame_rate=PAL_FRAME_RATE,
    field_rate=PAL_FIELD_RATE,
)
NTSC_SPECS = namedtuple(
    "NTSC_SPECS",
    [
        "width_43",
        "height_43",
        "width_169",
        "height_169",
        "frame_rate",
        "field_rate",
    ],
)(
    width_43=720,
    height_43=480,
    width_169=1024,
    height_169=480,
    frame_rate=NTSC_FRAME_RATE,
    field_rate=NTSC_FIELD_RATE,
)

SHELVE_FILE_EXTNS = ("dir", "dat", "bak", "project_files", "dvdmenu")
# fmt: off
VIDEO_FILE_EXTNS = ("mp4", "avi", "mkv", "vob",'mod','mov','webm',"m4v","3gp",
                        "3g2", "mj2","mkv","mpg","mpeg","ts", "m2ts", "mts","qt",
                        "wmv", "asf","flv","f4v","ogg","ogv","rm", "rmvb","divx","mxf",
                        "dv","mts")
# fmt: on
tool_app_folder: Final[str] = (
    f"{executable_folder}{file_sep}tool_apps{file_sep}usr{file_sep}bin{file_sep}"
)

COMPOSITE: Final[str] = f"{tool_app_folder}composite"
CONVERT: Final[str] = f"{tool_app_folder}magick"
DVDAUTHOR: Final[str] = f"{tool_app_folder}dvdauthor"
FFMPG: Final[str] = f"{tool_app_folder}ffmpeg"
FFPROBE: Final[str] = f"{tool_app_folder}ffprobe"
IDENTIFY: Final[str] = f"{tool_app_folder}identify"
MPLEX: Final[str] = f"{tool_app_folder}mplex"
SPUMUX: Final[str] = f"{tool_app_folder}spumux"
GENISOIMAGE: Final[str] = f"{tool_app_folder}genisoimage"

ICON_PATH: Final[str] = f"{executable_folder}{file_sep}icons"

# Database tables
PRODUCT_LINE: Final[str] = "product_line"

# Database Setting Keys
APP_LANG_DBK: Final[str] = "app_lang"  # All qtgui apps
APP_COUNTRY_DBK: Final[str] = "app_country"  # All qtgui apps

ARCHIVE_DISK_SIZE_DBK: Final[str] = "archive_disk_size"
ARCHIVE_DISK_TRANSCODE_DBK: Final[str] = "archive_disk_transcode"
ARCHIVE_FOLDER_DBK: Final[str] = "archive_folder"

BUTTON_BACKGROUND_COLOUR_DBK: Final[str] = "button_background_color"
BUTTON_BACKGROUND_TRANSPARENCY_DBK: Final[str] = "button_background_transparency"
BUTTON_FONT_DBK: Final[str] = "button_font"
BUTTON_FONT_COLOUR_DBK: Final[str] = "button_font_color"
BUTTON_FONT_POINT_SIZE_DBK: Final[str] = "button_font_point_size"
BUTTONS_ACROSS_DBK: Final[str] = "buttons_across"
BUTTONS_PER_PAGE_DBK: Final[str] = "buttons_per_page"

DISPLAY_FILE_NAMES_DBK: Final[str] = "display_file_names"

DEFAULT_PROJECT_NAME_DBK: Final[str] = "Default"
DEFAULT_DVD_LAYOUT_NAME_DBK: Final[str] = "DVD 1"
DVD_BUILD_FOLDER_DBK: Final[str] = "dvd_build_folder"

DVD_INSERT_TITLE_BACKGROUND_COLOUR_DBK: Final[str] = "dvd_insert_title_background_color"
DVD_INSERT_TITLE_BACKGROUND_TRANSPARENCY_DBK: Final[str] = (
    "dvd_insert_title_background_transparency"
)
DVD_INSERT_TITLE_FONT_DBK: Final[str] = "dvd_insert_title_font"
DVD_INSERT_TITLE_FONT_COLOUR_DBK: Final[str] = "dvd_insert_title_font_color"
DVD_INSERT_TITLE_FONT_POINT_SIZE_DBK: Final[str] = "dvd_insert_title_font_point_size"

DVD_INSERT_BACKGROUND_COLOUR_DBK: Final[str] = "dvd_insert_background_color"
DVD_INSERT_BACKGROUND_TRANSPARENCY_DBK: Final[str] = (
    "dvd_insert_background_transparency"
)
DVD_INSERT_FONT_DBK: Final[str] = "dvd_insert_font"
DVD_INSERT_FONT_COLOUR_DBK: Final[str] = "dvd_insert_font_color"
DVD_INSERT_FONT_POINT_SIZE_DBK: Final[str] = "dvd_insert_font_point_size"

DVD_DISK_TITLE_BACKGROUND_COLOUR_DBK: Final[str] = "dvd_disk_title_background_color"
DVD_DISK_TITLE_BACKGROUND_TRANSPARENCY_DBK: Final[str] = (
    "dvd_disk_title_background_transparency"
)
DVD_DISK_TITLE_FONT_DBK: Final[str] = "dvd_disk_title_font"
DVD_DISK_TITLE_FONT_COLOUR_DBK: Final[str] = "dvd_disk_title_font_color"
DVD_DISK_TITLE_FONT_POINT_SIZE_DBK: Final[str] = "dvd_disk_title_font_point_size"

DVD_DISK_BACKGROUND_COLOUR_DBK: Final[str] = "dvd_disk_background_color"
DVD_DISK_BACKGROUND_TRANSPARENCY_DBK: Final[str] = "dvd_disk_background_transparency"
DVD_DISK_FONT_DBK: Final[str] = "dvd_disk_font"
DVD_DISK_FONT_COLOUR_DBK: Final[str] = "dvd_disk_font_color"
DVD_DISK_FONT_POINT_SIZE_DBK: Final[str] = "dvd_disk_font_point_size"

FIRST_RUN_DBK: Final[str] = "first_run"
LATEST_PROJECT_DBK: Final[str] = "latest_project"
MENU_ASPECT_RATIO_DBK: Final[str] = "menu_aspect_ratio"
MENU_BACKGROUND_COLOUR_DBK: Final[str] = "menu_background_color"
MENU_FONT_DBK: Final[str] = "menu_font"
MENU_FONT_COLOUR_DBK: Final[str] = "menu_font_color"
MENU_FONT_POINT_SIZE_DBK: Final[str] = "menu_font_point_size"
PAGE_POINTER_LEFT_DBK: Final[str] = "page_pointer_left"
PAGE_POINTER_RIGHT_DBK: Final[str] = "page_pointer_right"
PRINT_FOLDER_DBK: Final[str] = "print_folder"
PRINT_FILE_DBK: Final[str] = "print_file"
SERIAL_NUMBER_DBK: Final[str] = "serial_number"
STREAMING_FOLDER_DBK: Final[str] = "streaming_folder"
VF_AUTO_LEVELS_DBK: Final[str] = "vf_auto_levels"
VF_DENOISE_DBK: Final[str] = "vf_denoise"
VF_NORMALISE_DBK: Final[str] = "vf_normalise"
VF_WHITE_BALANCE_DBK: Final[str] = "vf_white_balance"
VF_SHARPEN_DBK: Final[str] = "vf_sharpen"
VIDEO_IMPORT_FOLDER_DBK: Final[str] = "video_import_folder"

# File Paths
EDIT_FOLDER_NAME: Final[str] = "edits"
TRANSCODE_FOLDER_NAME: Final[str] = "transcodes"
DVD_BUILD_FOLDER_NAME: Final[str] = f"{PROGRAM_NAME} DVD Builder"
VIDEO_EDITOR_FOLDER_NAME: Final[str] = f"{PROGRAM_NAME} Video Editor"

# SQL Shelf keys
DVD_MENU_SHELF: Final[str] = "dvdmenu"
PROJECTS_SHELF: Final[str] = "projects"
VIDEO_CUTTER_SHELF: Final[str] = "video_cutter"
VIDEO_GRID_SHELF: Final[str] = "video_grid"

PERCENT_SAFTEY_BUFFER: Final[int] = (
    5  # Used to limit DVD size so that it never exceeds 100%
)
DEFAULT_FONT: Final[str] = "IBMPlexMono-SemiBold.ttf"  # Packaged with DVD Archiver
