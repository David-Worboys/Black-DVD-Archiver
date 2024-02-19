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

# Tell Black to leave this block alone (realm of isort)
# fmt: off
import datetime
from collections import namedtuple
from typing import Final

import file_utils
import utils

# fmt: on

executable_folder = file_utils.App_Path()

file_sep = file_utils.File().ossep

PROGRAM_NAME: Final[str] = "Black DVD Archiver"
PROGRAM_VERSION: Final[str] = "β4.0.0"
AUTHOR: Final[str] = "David Worboys"
LICENCE: Final[str] = "GNU V3 GPL"


def COPYRIGHT_YEAR() -> str:
    """
    The COPYRIGHT_YEAR function returns the current year if it is 2022, otherwise it returns a string of the
    form '2022-&lt;current_year&gt;'.

    Returns:
        str: The current year, or the current year and the next if it's 2022

    """
    return f"{'2022' if str(datetime.date.today().year) == '2022' else '2022-' + str(datetime.date.today().year)}"


VERSION_TAG = (
    f"{PROGRAM_VERSION} {LICENCE} (c){COPYRIGHT_YEAR()} {AUTHOR} (-:alumnus Moyhu"
    " Primary School et al.:-)"
)

SEED = "9d392b49808544f7bc5b93b935b76ced"
SDELIM = (  # Used to delimit strings - particularly non-translatable sections of strings
    "||"
)
PAL: Final[str] = "PAL"
NTSC: Final[str] = "NTSC"
AR169: Final[str] = "16:9"
AR43: Final[str] = "4:3"
PAL_FRAME_RATE: Final[int] = 25
PAL_FIELD_RATE: Final[int] = 50
NTSC_FRAME_RATE: Final[float] = 29.97
NTSC_FIELD_RATE: Final[float] = 59.94
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
    ["width_43", "height_43", "width_169", "height_169", "frame_rate", "field_rate"],
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
    ["width_43", "height_43", "width_169", "height_169", "frame_rate", "field_rate"],
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
XORRISO: Final[str] = f"{tool_app_folder}xorriso"

ICON_PATH: Final[str] = f"{executable_folder}{file_sep}icons"

# Database tables
PRODUCT_LINE: Final[str] = "product_line"

# Database Setting Keys
ARCHIVE_FOLDER: Final[str] = "archive_folder"
STREAMING_FOLDER: Final[str] = "streaming_folder"
DVD_BUILD_FOLDER: Final[str] = "dvd_build_folder"
DEFAULT_PROJECT_NAME: Final[str] = "Default"
DEFAULT_DVD_LAYOUT_NAME: Final[str] = "DVD 1"
EDIT_FOLDER: Final[str] = "edits"
TRANSCODE_FOLDER: Final[str] = "transcodes"
DVD_BUILD_FOLDER_NAME: Final[str] = f"{PROGRAM_NAME} DVD Builder"
VIDEO_EDITOR_FOLDER_NAME = f"{PROGRAM_NAME} Video Editor"

PERCENT_SAFTEY_BUFFER: Final[int] = (
    5  # Used to limit DVD size so that it never exceeds 100%
)
DEFAULT_FONT: Final[str] = "IBMPlexMono-SemiBold.ttf"  # Packaged with DVD Archiver


class SPECIAL_PATH(utils.strEnum):
    """Contains enums for strings that represent special paths on the user's computer"""

    DESKTOP: Final[str] = "Desktop"
    DOCUMENTS: Final[str] = "Documents"
    DOWNLOADS: Final[str] = "Downloads"
    MUSIC: Final[str] = "Music"
    PICTURES: Final[str] = "Pictures"
    VIDEOS: Final[str] = "Videos"
