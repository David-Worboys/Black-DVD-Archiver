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

import utils
# fmt: off

file_sep = utils.File().ossep

PROGRAM_NAME = "DVD Archiver"
PROGRAM_VERSION = "0.1"
AUTHOR = "David Worboys"
LICENCE = "GNU V3 GPL"


# Needs Callable to keep MyPy happy. Returns a string that is either 2020 or 2020-<current year>
COPYRIGHT_YEAR: Callable[
    [], str
] = (
    lambda: f"{'2020' if str(datetime.date.today().year) == '2022' else '2022-'+str(datetime.date.today().year) }"
)

VERSION_TAG = f"{PROGRAM_VERSION} {LICENCE} (c){COPYRIGHT_YEAR()} {AUTHOR} (-:alumnus Moyhu Primary School et al.:-)"

SEED = "9d392b49808544f7bc5b93b935b76ced"
SDELIM = (
    "||"  # Used to delimit strings - particularly non-translatable sections of strings
)
PAL = "PAL"
NTSC = "NTSC"
AR169 = "16:9"
AR43 = "4:3"
PAL_FRAMERATE = 25
NTSC_FRAMERATE = 29.97
AVERAGE_BITRATE = 5500

VIDEO_FILE_EXTNS = ("mp4", "avi", "mkv", "VOB")

EMPTYPALVIDEO = f".{file_sep}audio{file_sep}empty_pal_ac3.mpg"
EMPTYNTSCVIDEO = f".{file_sep}audio{file_sep}empty_ntsc_ac3.mpg"
EMPTYPALAUDIO = f".{file_sep}audio{file_sep}empty_pal_ac3.ac3"
EMPTYNTSCAUDIO = f".{file_sep}audio{file_sep}empty_ntsc_ac3.ac3"

COMPOSITE = f".{file_sep}tools{file_sep}composite"
CONVERT = f".{file_sep}tools{file_sep}magick"
DD = f".{file_sep}tools{file_sep}dd"
DVDAUTHOR = f".{file_sep}tools{file_sep}dvdauthor"
FFMPG = f".{file_sep}tools{file_sep}ffmpeg"
IDENTIFY = f".{file_sep}tools{file_sep}identify"
MEDIAINFO = f".{file_sep}tools{file_sep}mediainfo"
MPEG2ENC = f".{file_sep}tools{file_sep}mpeg2enc"
MPLEX = f".{file_sep}tools{file_sep}mplex"
PPMTOY4M = f".{file_sep}tools{file_sep}ppmtoy4m"
SPUMUX = f".{file_sep}tools{file_sep}spumux"
TWOLAME = f".{file_sep}tools{file_sep}twolame"


class SPECIAL_PATH(utils.strEnum):
    """Contains a list of strings that represent special paths on the user's computer"""

    DESKTOP = ("Desktop",)
    DOCUMENTS = ("Documents",)
    DOWNLOADS = ("Downloads",)
    MUSIC = ("Music",)
    PICTURES = ("Pictures",)
    VIDEOS = "Videos"
