"""
    Contains classes that are used to store and retrieve configuration data.

    Copyright (C) 2023  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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

import file_utils
import sqldb
import sys_consts

# fmt: on


@dataclasses.dataclass
class DVD_Menu_Settings:
    """Stores/Retrieves the DVD menu settings from the database."""

    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

    @property
    def menu_background_color(self) -> str:
        if not self._db_settings.setting_exist("menu_background_color"):
            self._db_settings.setting_set("menu_background_color", "blue")
        return self._db_settings.setting_get("menu_background_color")

    @menu_background_color.setter
    def menu_background_color(self, value: str):
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("menu_background_color", value)

    @property
    def menu_font_color(self) -> str:
        if not self._db_settings.setting_exist("menu_font_color"):
            self._db_settings.setting_set("menu_font_color", "yellow")
        return self._db_settings.setting_get("menu_font_color")

    @menu_font_color.setter
    def menu_font_color(self, value: str):
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("menu_font_color", value)

    @property
    def menu_font_point_size(self) -> int:
        if not self._db_settings.setting_exist("menu_font_point_size"):
            self._db_settings.setting_set("menu_font_point_size", 24)
        return self._db_settings.setting_get("menu_font_point_size")

    @menu_font_point_size.setter
    def menu_font_point_size(self, value: int):
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set("menu_font_point_size", value)

    @property
    def menu_font(self) -> str:
        if not self._db_settings.setting_exist("menu_font"):
            self._db_settings.setting_set("menu_font", sys_consts.DEFAULT_FONT)
        return self._db_settings.setting_get("menu_font")

    @menu_font.setter
    def menu_font(self, value: str):
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("menu_font", value)

    @property
    def button_background_color(self) -> str:
        if not self._db_settings.setting_exist("button_background_color"):
            self._db_settings.setting_set("button_background_color", "darkgray")
        return self._db_settings.setting_get("button_background_color")

    @button_background_color.setter
    def button_background_color(self, value: str):
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("button_background_color", value)

    @property
    def button_background_transparency(self) -> int:
        if not self._db_settings.setting_exist("button_background_transparency"):
            self._db_settings.setting_set("button_background_transparency", 90)
        return self._db_settings.setting_get("button_background_transparency")

    @button_background_transparency.setter
    def button_background_transparency(self, value: int):
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set("button_background_transparency", value)

    @property
    def button_font(self) -> str:
        if not self._db_settings.setting_exist("menu_font"):
            self._db_settings.setting_set("menu_font", sys_consts.DEFAULT_FONT)
        return self._db_settings.setting_get("button_font")

    @button_font.setter
    def button_font(self, value: str):
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("button_font", value)

    @property
    def button_font_color(self) -> str:
        if not self._db_settings.setting_exist("button_font_color"):
            self._db_settings.setting_set("button_font_color", "white")
        return self._db_settings.setting_get("button_font_color")

    @button_font_color.setter
    def button_font_color(self, value: str):
        self._db_settings.setting_set("button_font_color", value)

    @property
    def button_font_point_size(self) -> int:
        if not self._db_settings.setting_exist("button_font_point_size"):
            self._db_settings.setting_set("button_font_point_size", 12)
        return self._db_settings.setting_get("button_font_point_size")

    @button_font_point_size.setter
    def button_font_point_size(self, value: int):
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set("button_font_point_size", value)


@dataclasses.dataclass(slots=True)
class Video_File_Settings:
    """Class to hold video file settings for each file comprising the DVD menu buttons"""

    _normalise: bool = True
    _denoise: bool = True
    _white_balance: bool = True
    _sharpen: bool = True
    _auto_bright: bool = True
    _button_title: str = ""
    _menu_button_frame: int = -1

    def __post_init__(self) -> None:
        """Post init to check the file settings are valid"""
        assert isinstance(self._normalise, bool), f"{self._normalise=}. Must be a bool"
        assert isinstance(self._denoise, bool), f"{self._denoise=}. Must be a bool"
        assert isinstance(
            self._white_balance, bool
        ), f"{self._white_balance=}. Must be a bool"
        assert isinstance(self._sharpen, bool), f"{self._sharpen=}. Must be a bool"
        assert isinstance(
            self._auto_bright, bool
        ), f"{self._auto_bright=}. Must be a bool"
        assert isinstance(self._button_title, str), f"{self._button_title=} must be str"
        assert (
            isinstance(self._menu_button_frame, int)
            and self._menu_button_frame == -1
            or self._menu_button_frame >= 0
        ), f"{self._menu_button_frame=}. Must be int"

    @property
    def filters_off(self) -> bool:
        """Return True if all the filter settings are off"""
        return not any(
            value
            for value in [
                self._normalise,
                self._denoise,
                self._white_balance,
                self._sharpen,
                self._auto_bright,
            ]
        )

    @property
    def normalise(self) -> bool:
        return self._normalise

    @normalise.setter
    def normalise(self, value: bool) -> None:
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._normalise = value

    @property
    def denoise(self) -> bool:
        return self._denoise

    @denoise.setter
    def denoise(self, value: bool) -> None:
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._denoise = value

    @property
    def white_balance(self) -> bool:
        return self._white_balance

    @white_balance.setter
    def white_balance(self, value: bool) -> None:
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._white_balance = value

    @property
    def sharpen(self) -> bool:
        return self._sharpen

    @sharpen.setter
    def sharpen(self, value: bool) -> None:
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._sharpen = value

    @property
    def auto_bright(self) -> bool:
        return self._auto_bright

    @auto_bright.setter
    def auto_bright(self, value: bool) -> None:
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._auto_bright = value

    @property
    def button_title(self) -> str:
        return self._button_title

    @button_title.setter
    def button_title(self, value: str) -> None:
        assert isinstance(value, str), f"{value=}. Must be a str"

        self._button_title = value

    @property
    def menu_button_frame(self) -> int:
        return self._menu_button_frame

    @menu_button_frame.setter
    def menu_button_frame(self, value: int) -> None:
        assert (
            isinstance(value, int) and value == -1 or value >= 0
        ), f"{value=}. Must be an int == -1 or >= 0"
        self._menu_button_frame = value


@dataclasses.dataclass(slots=True)
class Video_Data:
    """
    video data container class.
    Attributes:
        video_folder (str): The path to the folder containing the video.
        video_file (str): The name of the video file.
        video_extension (str): The file extension of the video file.
        encoding_info (dict): Information about the encoding of the video.
    """

    video_folder: str
    video_file: str
    video_extension: str
    encoding_info: dict
    video_file_settings: Video_File_Settings
    vd_id: int = -1

    def __post_init__(self) -> None:
        assert (
            isinstance(self.video_folder, str) and self.video_folder.strip() != ""
        ), f"{self.video_folder=} must be str"
        assert (
            isinstance(self.video_file, str) and self.video_file.strip() != ""
        ), f"{self.video_file=} must be str"
        assert (
            isinstance(self.video_extension, str) and self.video_extension.strip() != ""
        ), f"{self.video_extension=} must be str"
        assert isinstance(
            self.encoding_info, dict
        ), f"{self.encoding_info=}. Must be dict"
        assert isinstance(
            self.video_file_settings, Video_File_Settings
        ), f"{self.video_file_settings=}. Must be an instance of Video_Filter_Settings"

        assert (
            isinstance(self.vd_id, int) and self.vd_id == -1 or self.vd_id >= 0
        ), f"{self.vd_id=}. Must be an int == -1 or >= 0"

        if self.vd_id == -1:
            self.vd_id = id(self)

    @property
    def video_path(self) -> str:
        """
        Gets the full path to the video file.
        Returns:
            str: The full path to the video file
        """
        video_path = file_utils.File().file_join(
            self.video_folder, self.video_file, self.video_extension
        )

        return video_path


@dataclasses.dataclass
class File_Def:
    _path: str = ""
    _file_name: str = ""
    _menu_image_file_path: str = ""
    _file_info: dict = dataclasses.field(default_factory=dict)
    _video_file_settings: Video_File_Settings = dataclasses.field(
        default_factory=Video_File_Settings
    )

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file path"

        assert file_utils.File().path_exists(value), f"{value=}. Path does not exist"

        self._path = value

    @property
    def file_name(self) -> str:
        return self._file_name

    @file_name.setter
    def file_name(self, value: str) -> None:
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file name"

        self._file_name = value

    @property
    def file_info(self) -> dict:
        return self._file_info

    @file_info.setter
    def file_info(self, value: dict) -> None:
        assert isinstance(value, dict), f"{value=}. Must be a dict of file properties"

        self._file_info = value

    @property
    def menu_image_file_path(self) -> str:
        return self._menu_image_file_path

    @menu_image_file_path.setter
    def menu_image_file_path(self, value: str) -> None:
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file path"

        assert file_utils.File().file_exists(value), f"{value=}. Path does not exist"

        self._menu_image_file_path = value

    @property
    def file_path(self) -> str:
        assert (
            self.path != "" and self.file_name != ""
        ), f"{self.path=}, {self.file_name=}. Must be set"

        return file_utils.File().file_join(self.path, self.file_name)

    @property
    def video_file_settings(self) -> Video_File_Settings:
        return self._video_file_settings

    @video_file_settings.setter
    def video_file_settings(self, value: Video_File_Settings) -> None:
        assert isinstance(
            value, Video_File_Settings
        ), f"{value=}. Must be an instance Video_Filter_Settings"

        self._video_file_settings = value
