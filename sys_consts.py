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
from typing import Callable

import file_utils
import utils

# fmt: on

executable_folder = file_utils.App_Path()

file_sep = file_utils.File().ossep

PROGRAM_NAME = "Black DVD Archiver"
PROGRAM_VERSION = "0.2"
AUTHOR = "David Worboys"
LICENCE = "GNU V3 GPL"


# Needs Callable to keep MyPy happy. Returns a string that is either 2020 or 2020-<current year>
COPYRIGHT_YEAR: Callable[[], str] = (
    lambda: (
        f"{'2022' if str(datetime.date.today().year) == '2022' else '2022-'+str(datetime.date.today().year) }"
    )
)

VERSION_TAG = (
    f"{PROGRAM_VERSION} {LICENCE} (c){COPYRIGHT_YEAR()} {AUTHOR} (-:alumnus Moyhu"
    " Primary School et al.:-)"
)

SEED = "9d392b49808544f7bc5b93b935b76ced"
SDELIM = (  # Used to delimit strings - particularly non-translatable sections of strings
    "||"
)
PAL = "PAL"
NTSC = "NTSC"
AR169 = "16:9"
AR43 = "4:3"
PAL_FRAMERATE = 25
NTSC_FRAMERATE = 29.97
AVERAGE_BITRATE = 5500  # kilobits/sec
SINGLE_SIDED_DVD_SIZE = 40258730  # kb ~ 4.7GB DVD5
DOUBLE_SIDED_DVD_SIZE = 72453177  # kb ~ 8.5GB DVD9

# fmt: off
VIDEO_FILE_EXTNS = ("mp4", "avi", "mkv", "vob",'mod','mov','webm',"m4v","3gp", 
                    "3g2", "mj2","mkv","mpg","mpeg","ts", "m2ts", "mts","qt",
                    "wmv", "asf","flv","f4v","ogg","ogv","rm", "rmvb","divx","mxf",
                    "dv")
# fmt: on

COMPOSITE = f"{executable_folder}{file_sep}tools{file_sep}composite"
CONVERT = f"{executable_folder}{file_sep}tools{file_sep}magick"
DVDAUTHOR = f"{executable_folder}{file_sep}tools{file_sep}dvdauthor"
FFMPG = f"{executable_folder}{file_sep}tools{file_sep}ffmpeg"
FFPROBE = f"{executable_folder}{file_sep}tools{file_sep}ffprobe"
IDENTIFY = f"{executable_folder}{file_sep}tools{file_sep}identify"
MEDIAINFO = f"{executable_folder}{file_sep}tools{file_sep}mediainfo"
MPEG2ENC = f"{executable_folder}{file_sep}tools{file_sep}mpeg2enc"
MPLEX = f"{executable_folder}{file_sep}tools{file_sep}mplex"
PPMTOY4M = f"{executable_folder}{file_sep}tools{file_sep}ppmtoy4m"
SPUMUX = f"{executable_folder}{file_sep}tools{file_sep}spumux"
XORRISO = f"{executable_folder}{file_sep}tools{file_sep}xorriso"

# Database tables
PRODUCT_LINE = "product_line"

# Database Setting Keys
ARCHIVE_FOLDER = "archive_folder"
DVD_BUILD_FOLDER = "dvd_build_folder"


class SPECIAL_PATH(utils.strEnum):
    """Contains a enums for strings that represent special paths on the user's computer"""

    DESKTOP = "Desktop"
    DOCUMENTS = "Documents"
    DOWNLOADS = "Downloads"
    MUSIC = "Music"
    PICTURES = "Pictures"
    VIDEOS = "Videos"
