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
from typing import Final

import file_utils
import utils

# fmt: on

executable_folder = file_utils.App_Path()

file_sep = file_utils.File().ossep

PROGRAM_NAME: Final[str] = "Black DVD Archiver"
PROGRAM_VERSION: Final[str] = "0.5"
AUTHOR: Final[str] = "David Worboys"
LICENCE: Final[str] = "GNU V3 GPL"


# Needs Callable to keep MyPy happy. Returns a string that is either 2020 or 2020-<current year>
def COPYRIGHT_YEAR() -> str:
    return (
        f"{'2022' if str(datetime.date.today().year) == '2022' else '2022-' + str(datetime.date.today().year)}"
    )


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
PAL_FRAMERATE: Final[int] = 25
NTSC_FRAMERATE: Final[float] = 29.97
AVERAGE_BITRATE: Final[int] = 5500  # kilobits/sec
SINGLE_SIDED_DVD_SIZE: Final[int] = 40258730  # kb ~ 4.7GB DVD5
DOUBLE_SIDED_DVD_SIZE: Final[int] = 72453177  # kb ~ 8.5GB DVD9

# fmt: off
VIDEO_FILE_EXTNS = ("mp4", "avi", "mkv", "vob",'mod','mov','webm',"m4v","3gp", 
                    "3g2", "mj2","mkv","mpg","mpeg","ts", "m2ts", "mts","qt",
                    "wmv", "asf","flv","f4v","ogg","ogv","rm", "rmvb","divx","mxf",
                    "dv")
# fmt: on

COMPOSITE: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}composite"
CONVERT: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}magick"
DVDAUTHOR: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}dvdauthor"
FFMPG: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}ffmpeg"
FFPROBE: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}ffprobe"
IDENTIFY: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}identify"
MEDIAINFO: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}mediainfo"
MPEG2ENC: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}mpeg2enc"
MPLEX: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}mplex"
PPMTOY4M: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}ppmtoy4m"
SPUMUX: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}spumux"
XORRISO: Final[str] = f"{executable_folder}{file_sep}tools{file_sep}xorriso"

ICON_PATH: Final[str] = f"{executable_folder}{file_sep}icons"

# Database tables
PRODUCT_LINE: Final[str] = "product_line"

# Database Setting Keys
ARCHIVE_FOLDER: Final[str] = "archive_folder"
DVD_BUILD_FOLDER: Final[str] = "dvd_build_folder"
VIDEO_GRID_DB: Final[str] = "video_grid"

PERCENT_SAFTEY_BUFFER: Final[int] = (
    1  # Used to limit DVD size so that it never exceeds 100%
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
