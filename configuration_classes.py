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
        """
        The menu_background_color method returns the background color of the menu.
        If no setting exists, it will create one with a default value of blue.

        Args:

        Returns:
            str : The background color of the menu

        """
        if not self._db_settings.setting_exist("menu_background_color"):
            self._db_settings.setting_set("menu_background_color", "blue")
        return self._db_settings.setting_get("menu_background_color")

    @menu_background_color.setter
    def menu_background_color(self, value: str) -> None:
        """
        The menu_background_color method sets the background color of the menu.

        Args:
            value (str): The value of the menu_background_color setting

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("menu_background_color", value)

    @property
    def menu_font_color(self) -> str:
        """
        The menu_font_color method returns the color of the font used in menus.
        If no value is set, it will return yellow as a default.

        Args:

        Returns:
            str : The color of the font used in menus
        """
        if not self._db_settings.setting_exist("menu_font_color"):
            self._db_settings.setting_set("menu_font_color", "yellow")
        return self._db_settings.setting_get("menu_font_color")

    @menu_font_color.setter
    def menu_font_color(self, value: str) -> None:
        """
        The menu_font_color method sets the color of the font in the menu.

        Args:
            value (str): The value of the menu_font_color setting

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("menu_font_color", value)

    @property
    def menu_font_point_size(self) -> int:
        """
        The menu_font_point_size method returns the point size of the font used in menus.

        Args:

        Returns:
            The menu font point size

        """
        if not self._db_settings.setting_exist("menu_font_point_size"):
            self._db_settings.setting_set("menu_font_point_size", 24)
        return self._db_settings.setting_get("menu_font_point_size")

    @menu_font_point_size.setter
    def menu_font_point_size(self, value: int) -> None:
        """
        The menu_font_point_size method sets the font size of the menu text.

        Args:
            value (int): The value of the menu_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set("menu_font_point_size", value)

    @property
    def menu_font(self) -> str:
        """
        The menu_font method returns the font used for menu items.
        If no font has been set, it will return the default app font.

        Args:

        Returns:
            str: The font used in the menu

        """
        if not self._db_settings.setting_exist("menu_font"):
            self._db_settings.setting_set("menu_font", sys_consts.DEFAULT_FONT)
        return self._db_settings.setting_get("menu_font")

    @menu_font.setter
    def menu_font(self, value: str) -> None:
        """
        The menu_font method sets the font for the menu.

        Args:
            value (str): The value of the menu_font setting

        Returns:

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("menu_font", value)

    @property
    def button_background_color(self) -> str:
        """
        The button_background_color method returns the background color of the buttons in the GUI.
        If no setting exists, it creates one and sets it to darkgray.

        Args:

        Returns:
            str: The background color of the buttons

        """
        if not self._db_settings.setting_exist("button_background_color"):
            self._db_settings.setting_set("button_background_color", "darkgray")
        return self._db_settings.setting_get("button_background_color")

    @button_background_color.setter
    def button_background_color(self, value: str) -> None:
        """
        The button_background_color method sets the background color of the buttons in the GUI.

        Args:
            value (str): Set the button background color

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("button_background_color", value)

    @property
    def button_background_transparency(self) -> int:
        """
        The button_background_transparency method returns the transparency of the button background.
            If it does not exist, it is set to 90.

        Args:

        Returns:
            int : Percentage transparency of the button background

        """
        if not self._db_settings.setting_exist("button_background_transparency"):
            self._db_settings.setting_set("button_background_transparency", 90)
        return self._db_settings.setting_get("button_background_transparency")

    @button_background_transparency.setter
    def button_background_transparency(self, value: int) -> None:
        """
        The button_background_transparency method sets the transparency of the button background.

        Args:
            value (int): The percentage transparency of the button background

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set("button_background_transparency", value)

    @property
    def button_font(self) -> str:
        """
        The button_font method is used to set the font of the buttons in the menu.
        The function first checks if a setting for button_font exists, and if it does not,
        then it sets one with the app default font. Then, it returns that value.

        Returns:
            str : The font used for button text

        """
        if not self._db_settings.setting_exist("menu_font"):
            self._db_settings.setting_set("menu_font", sys_consts.DEFAULT_FONT)
        return self._db_settings.setting_get("button_font")

    @button_font.setter
    def button_font(self, value: str) -> None:
        """
        The button_font method sets the font for all buttons in the application.

        Args:
            value (str): Sets the button_font

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set("button_font", value)

    @property
    def button_font_color(self) -> str:
        """
        The button_font_color method returns the color of the font on buttons.
        If no button_font_color setting exists, it creates one with a default value of white.

        Returns:
            str : The value of the button_font_color setting

        """
        if not self._db_settings.setting_exist("button_font_color"):
            self._db_settings.setting_set("button_font_color", "white")
        return self._db_settings.setting_get("button_font_color")

    @button_font_color.setter
    def button_font_color(self, value: str) -> None:
        """
        The button_font_color method sets the font color of the buttons in the DVD menu.

        Args:
            value (str): Set the button_font_color setting

        """
        self._db_settings.setting_set("button_font_color", value)

    @property
    def button_font_point_size(self) -> int:
        """
        The button_font_point_size method returns the point size of the font used for buttons.
        If no value is stored in the database, it will be set to 12 and returned.

        Args:

        Returns:
            int : The point size of the font used for buttons

        """
        if not self._db_settings.setting_exist("button_font_point_size"):
            self._db_settings.setting_set("button_font_point_size", 12)
        return self._db_settings.setting_get("button_font_point_size")

    @button_font_point_size.setter
    def button_font_point_size(self, value: int) -> None:
        """
        The button_font_point_size method sets the font size of the buttons in the DVD Menu.

        Args:
            value (int): Sets the button_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set("button_font_point_size", value)

    @property
    def buttons_across(self) -> int:
        """
        The buttons_across method returns the number of buttons across the DVD menu.

        Args:

        Returns:
            int : The number of buttons across the screen

        """
        if not self._db_settings.setting_exist("buttons_across"):
            self._db_settings.setting_set("buttons_across", 2)
        return self._db_settings.setting_get("buttons_across")

    @buttons_across.setter
    def buttons_across(self, value: int) -> None:
        """
        The buttons_across method sets the number of buttons across the DVD menu.

        Args:
            value (int): Set the value of buttons_across to an integer
        """
        assert isinstance(value, int) and 1 <= value <= 4, f"{value=}. Must be int"

        self._db_settings.setting_set("buttons_across", value)

    @property
    def buttons_per_page(self) -> int:
        """
        The buttons_per_page method returns the number of buttons per DVD Menu page.
        If the setting does not exist, it is created and set to 4.

        Args:

        Returns:
            int : The number of buttons per page
        """
        if not self._db_settings.setting_exist("buttons_per_page"):
            self._db_settings.setting_set("buttons_per_page", 4)
        return self._db_settings.setting_get("buttons_per_page")

    @buttons_per_page.setter
    def buttons_per_page(self, value: int) -> None:
        """
        The buttons_per_page method sets the number of buttons per DVD Menu page.
        The value must be an integer between 1 and 6, inclusive.

        Args:
            value (int) Set the number of buttons per page
        """
        assert isinstance(value, int) and 1 <= value <= 6, f"{value=}. Must be int"

        self._db_settings.setting_set("buttons_per_page", value)


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
    _menu_group: int = -1

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
        assert (
            isinstance(self._menu_group, int)
            and self._menu_group == -1
            or self._menu_group >= 0
        ), f"{self._menu_group=}. Must be int >= 0 or == -1"

    @property
    def filters_off(self) -> bool:
        """
        The filters_off method returns True if all the filter settings are off.

        Args:

        Returns:
            bool : True if all the filter settings are off otherwise False

        """
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
        """
        The normalise method is used to normalise the video image.
        The function returns a boolean value indicating whether video normalisation is set to be performed.

        Args:

        Returns:
            bool : A boolean value
        """
        return self._normalise

    @normalise.setter
    def normalise(self, value: bool) -> None:
        """
        The normalise method is used to get the video normalisation setting.

        Args:
            value (bool): True to normalise the video otherwise False

        Returns:
            None


        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._normalise = value

    @property
    def denoise(self) -> bool:
        """
        The denoise method is used to get the video denoising setting.

        Args:

        Returns:
            bool : True to denoise the video otherwise False
        """
        return self._denoise

    @denoise.setter
    def denoise(self, value: bool) -> None:
        """
        The denoise method is used to set the video denoising setting.

        Args:
            value (bool): True to denoise the video otherwise False
        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._denoise = value

    @property
    def white_balance(self) -> bool:
        """
        The white_balance method is used to get the video white balance setting.

        Args:

        Returns:
            bool : True to white balance the video otherwise False
        """

        return self._white_balance

    @white_balance.setter
    def white_balance(self, value: bool) -> None:
        """
        The white_balance method is used to set the video white balance setting.

        Args:
            value (bool): True to white balance the video otherwise False
        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._white_balance = value

    @property
    def sharpen(self) -> bool:
        """
        The sharpen method is used to get the video sharpening setting.

        Args:

        Returns:
            bool : True to sharpen the video otherwise False
        """
        return self._sharpen

    @sharpen.setter
    def sharpen(self, value: bool) -> None:
        """
        The sharpen method is used to set the video sharpening setting.

        Args:
            value (bool): True to sharpen the video otherwise False
        """

        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._sharpen = value

    @property
    def auto_bright(self) -> bool:
        """
        The auto_bright method is used to get the video auto brightness setting.

        Args:

        Returns:
            bool : True to auto brightness the video otherwise False
        """
        return self._auto_bright

    @auto_bright.setter
    def auto_bright(self, value: bool) -> None:
        """
        The auto_bright method is used to set the video auto brightness setting.

        Args:
            value (bool): True to auto brightness the video otherwise False
        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._auto_bright = value

    @property
    def button_title(self) -> str:
        """
        The button_title method is used to get the title of the button.

        Args:

        Returns:
            str : The title of the button
        """
        assert isinstance(
            self._button_title, str
        ), f"{self._button_title=}. Must be a str"

        return self._button_title

    @button_title.setter
    def button_title(self, value: str) -> None:
        """
        The button_title method is used to set the title of the button.

        Args:
            value (str): The title of the button
        """
        assert isinstance(value, str), f"{value=}. Must be a str"

        self._button_title = value

    @property
    def menu_button_frame(self) -> int:
        """
        The menu_button_frame method is used to get the frame number of the menu button.
        if -1 then a menu button frame has not been set and will be extracted automatically

        Args:

        Returns:
            int : The frame number of the menu button
        """
        assert (
            isinstance(self._menu_button_frame, int)
            and self._menu_button_frame == -1
            or self._menu_button_frame >= 0
        ), f"{self._menu_button_frame=}. Must be int >= 0 or == -1"

        return self._menu_button_frame

    @menu_button_frame.setter
    def menu_button_frame(self, value: int) -> None:
        """
        The menu_button_frame method is used to set the frame number of the menu button.

        Args:
            value: (int): Check if the value is an integer and that it's greater than or equal to 0 or equal -1 (auto set)

        Returns:
            None

        """
        assert (
            isinstance(value, int) and value == -1 or value >= 0
        ), f"{value=}. Must be an int == -1 or >= 0"
        self._menu_button_frame = value

    @property
    def menu_group(self) -> int:
        """
        The menu_group method is used to get the menu group number.
        if -1 then a menu group has not been set

        Args:

        Returns:
            int : The menu group number
        """
        assert (
            isinstance(self._menu_group, int)
            and self._menu_group == -1
            or self._menu_group >= 0
        ), f"{self._menu_group=}. Must be int >= 0 or == -1"

        return self._menu_group

    @menu_group.setter
    def menu_group(self, value: int) -> None:
        """
        The menu_group method is used to set the menu group number.

        Args:
            value: (int): Check if the value is an integer and that it's greater than or equal to 0 or equal -1 (not set)

        """
        assert (
            isinstance(value, int) and value == -1 or value >= 0
        ), f"{value=}. Must be an int == -1 or >= 0"
        self._menu_group = value


@dataclasses.dataclass(slots=True)
class Video_Data:
    """
    video data container class.
    Attributes:
        video_folder (str): The path to the folder containing the video.
        video_file (str): The name of the video file.
        video_extension (str): The file extension of the video file.
        encoding_info (dict): Information about the encoding of the video.
        video_file_settings (Video_File_Settings): The video file settings.
        vd_id (int): The id of the video data. Defaults to -1.
    """

    video_folder: str
    video_file: str
    video_extension: str
    encoding_info: dict
    video_file_settings: Video_File_Settings
    vd_id: int = -1

    def __post_init__(self) -> None:
        """
        The __post_init__ method is used to set the video data.
        """
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
    """
    Class to hold video file related information
    """

    _path: str = ""
    _file_name: str = ""
    _menu_image_file_path: str = ""
    _file_info: dict = dataclasses.field(default_factory=dict)
    _video_file_settings: Video_File_Settings = dataclasses.field(
        default_factory=Video_File_Settings
    )

    @property
    def path(self) -> str:
        """
        The path method is used to get the path to the file.

        Returns:
            str: The path to the file
        """
        assert (
            isinstance(self._path, str) and self._path.strip() != ""
        ), f"{self._path=} must be str"

        return self._path

    @path.setter
    def path(self, value: str) -> None:
        """
        The path method is used to set the path to the file.

        Args:
            value: (str): Check if the value is a string and that it's not empty

        """
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file path"

        self._path = value
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file path"

        assert file_utils.File().path_exists(value), f"{value=}. Path does not exist"

        self._path = value

    @property
    def file_name(self) -> str:
        """
        The file_name method is used to get the file name.

        Returns:
            str: The file name
        """
        assert (
            isinstance(self._file_name, str) and self._file_name.strip() != ""
        ), f"{self._file_name=} must be str"

        return self._file_name

    @file_name.setter
    def file_name(self, value: str) -> None:
        """
        The file_name method is used to set the file name.

        Args:
            value: (str): The file name

        """
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file name"

        self._file_name = value

    @property
    def file_info(self) -> dict:
        """
        The file_info method is used to get the video file information.

        Returns:
            dict: The file information
        """

        return self._file_info

    @file_info.setter
    def file_info(self, value: dict) -> None:
        """
        The file_info method is used to set the video file information.

        Args:
            value: (dict): The file information

        """
        assert isinstance(value, dict), f"{value=}. Must be a dict of file properties"

        self._file_info = value

    @property
    def menu_image_file_path(self) -> str:
        """
        The menu_image_file_path method is used to get the menu image file path.

        Returns:
            str: The menu image file path
        """
        assert file_utils.File().file_exists(
            self._menu_image_file_path
        ), f"{self._menu_image_file_path=}. Path does not exist"

        return self._menu_image_file_path

    @menu_image_file_path.setter
    def menu_image_file_path(self, value: str) -> None:
        """
        The menu_image_file_path method is used to set the menu image file path.

        Args:
            value: (str): The menu image file path

        """
        assert (
            isinstance(value, str) and value.strip() != ""
        ), f"{value=}. Must be a file path"

        assert file_utils.File().file_exists(value), f"{value=}. Path does not exist"

        self._menu_image_file_path = value

    @property
    def file_path(self) -> str:
        """
        The file_path method is used to get the full path to the file.

        Returns:
            str: The full path to the file
        """
        return file_utils.File().file_join(self.path, self.file_name)

    @property
    def video_file_settings(self) -> Video_File_Settings:
        """
        The video_file_settings method is used to get the video file settings.

        Returns:
            Video_File_Settings: The video file settings
        """
        assert isinstance(
            self._video_file_settings, Video_File_Settings
        ), f"{self._video_file_settings=}. Must be an instance of Video_Filter_Settings"

        return self._video_file_settings

    @video_file_settings.setter
    def video_file_settings(self, value: Video_File_Settings) -> None:
        """
        The video_file_settings method is used to set the video file settings.

        Args:
            value: (Video_File_Settings): The video file settings instance

        """
        assert isinstance(
            value, Video_File_Settings
        ), f"{value=}. Must be an instance Video_Filter_Settings"

        self._video_file_settings = value