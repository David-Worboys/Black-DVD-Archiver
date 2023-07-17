"""
    Contains classes and function that are used to store and retrieve configuration data.

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
import shelve

import platformdirs

import file_utils
import popups
import sqldb
import sys_consts
from qtgui import Action
from utils import Text_To_File_Name

# fmt: on


def Get_DVD_Build_Folder() -> str:
    """Gets the DVD build folder

    Returns:
        str: The DVD build folder
    """
    file_handler = file_utils.File()
    db = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    dvd_folder = db.setting_get(sys_consts.DVD_BUILD_FOLDER)

    if dvd_folder is None or dvd_folder.strip() == "":
        popups.PopError(
            title="DVD Build Folder Error...",
            message="A DVD Build Folder Must Be Entered Before Making A Video Edit!",
        ).show()
        return ""

    dvd_folder = file_handler.file_join(
        dvd_folder, f"{sys_consts.PROGRAM_NAME} Video Editor"
    )
    return dvd_folder


def Get_Shelved_DVD_Menu_Layout(
    project_name: str,
) -> tuple[list[tuple[str, list[list["Video_Data"]]]], str]:
    """Gets the DVD menu layout from the shelved project file.

    Args:
        project_name (str): The name of the shelved project file.

    Returns:
        tuple[list[tuple[str, list[list["Video_Data"]]]],str]:
            The DVD menu layout and no error message if no issue.
            Empty DVD menu layout and error message if there is an issue
    """
    assert (
        isinstance(project_name, str) and project_name.strip() != ""
    ), f"{project_name=}. Must be a non-empty str"

    db_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

    file_handler = file_utils.File()
    project_file_name = file_handler.file_join(
        dir_path=db_path,
        file_name=Text_To_File_Name(project_name),
        ext="dvdmenu",
    )

    dvd_menu_layout: list[tuple[str, list[Video_Data]]] = []

    try:
        with shelve.open(project_file_name) as db:
            db_data = db.get("dvd_menu_grid")
            menu_pages: list[list[Video_Data]] = []

            if db_data:
                for grid_row in db_data:
                    menu_title = ""

                    for col_index, grid_col_item in enumerate(grid_row):
                        grid_value: str = grid_col_item[0]
                        grid_user_data = grid_col_item[1]
                        menu_pages = []

                        if menu_title.strip() == "" and grid_value.strip() != "":
                            menu_title = grid_value

                        if col_index == 1:  # 2nd Col houses button menu titles
                            menu_page: list[Video_Data] = []
                            for row_grid_item in grid_col_item[2]:
                                row_grid_item_value = row_grid_item[0]
                                row_grid_item_user_data: Video_Data = row_grid_item[1]
                                menu_page.append(row_grid_item_user_data)

                            menu_pages.append(menu_page)
                    dvd_menu_layout.append((menu_title, menu_pages))
    except Exception as e:
        return [], str(e)

    return dvd_menu_layout, ""


def Set_Shelved_DVD_Layout(
    project_name: str, dvd_menu_layout: list[tuple[str, list[list["Video_Data"]]]]
) -> str:
    """Saves the DVD menu layout to the shelved project file.

    Args:
        project_name (str): The name of the shelved project.
        dvd_menu_layout (list[tuple[str, list[list[Video_Data]]]]): The DVD menu layout to save.

    Returns:
        str: Empty string if successful, or an error message if there is an issue.
    """
    assert (
        isinstance(project_name, str) and project_name.strip() != ""
    ), f"{project_name=}. Must be a non-empty str"
    assert isinstance(dvd_menu_layout, list), f"{dvd_menu_layout=}. Must be a list"

    db_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

    file_handler = file_utils.File()
    project_file_name = file_handler.file_join(
        dir_path=db_path,
        file_name=Text_To_File_Name(project_name),
        ext="dvdmenu",
    )

    try:
        with shelve.open(project_file_name) as db:
            db["dvd_menu_grid"] = dvd_menu_layout
    except Exception as e:
        return str(e)

    return ""


@dataclasses.dataclass
class DVD_Archiver_Base:
    def event_handler(self, event: Action) -> None:
        """
        The event_handler methodused to handle GUI events.

        Args:
            event (Action): The event that was triggered

        Returns:
            None
        """
        pass


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
class Encoding_Details:
    """
    The Encoding_Details class is used to store the details of a video. as well as the error message associated
    with the video.
    """

    _error: str = ""
    _audio_tracks: int = 0
    _video_tracks: int = 0
    _audio_format: str = ""
    _audio_channels: int = 0
    _video_format: str = ""
    _video_width: int = 0
    _video_height: int = 0
    _video_ar: str = ""
    _video_par: float = 0.0
    _video_dar: float = 0.0
    _video_duration: float = 0.0
    _video_scan_order: str = ""
    _video_scan_type: str = ""
    _video_frame_rate: float = 0.0
    _video_standard: str = ""
    _video_frame_count: int = 0

    def __post_init__(self) -> None:
        pass

    @property
    def error(self) -> str:
        """
        The error method returns the error message associated with a video.

        Returns:
            str: The error message from the video

        """
        return self._error

    @error.setter
    def error(self, value: str) -> None:
        """
        The error method sets the error message associated with a video.

        Args:
            value (str): Set the error message for the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._error = value

    @property
    def audio_tracks(self) -> int:
        """
        The audio_tracks method returns the number of audio tracks in a video.

        Returns:
            int: The number of audio tracks in the video

        """
        return self._audio_tracks

    @audio_tracks.setter
    def audio_tracks(self, value: int) -> None:
        """
        The audio_tracks method sets the number of audio tracks in a video.

        Args:
            value (int): Set the number of audio tracks in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._audio_tracks = value

    @property
    def audio_format(self) -> str:
        """
        The audio_format method returns the audio format of a video.

        Returns:
            str: The audio format of the video

        """
        return self._audio_format

    @audio_format.setter
    def audio_format(self, value: str) -> None:
        """
        The audio_format method sets the audio format of a video.

        Args:
            value (str): Set the audio format of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._audio_format = value

    @property
    def audio_channels(self) -> int:
        """
        The audio_channels method returns the number of audio channels in a video.

        Returns:
            int: The number of audio channels in the video

        """
        return self._audio_channels

    @audio_channels.setter
    def audio_channels(self, value: int) -> None:
        """
        The audio_channels method sets the number of audio channels in a video.

        Args:
            value (int): Set the number of audio channels in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._audio_channels = value

    @property
    def video_tracks(self) -> int:
        """
        The video_tracks method returns the number of video tracks in a video.

        Returns:
            int: The number of video tracks in the video

        """
        return self._video_tracks

    @video_tracks.setter
    def video_tracks(self, value: int) -> None:
        """
        The video_tracks method sets the number of video tracks in a video.

        Args:
            value (int): Set the number of video tracks in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_tracks = value

    @property
    def video_format(self) -> str:
        """
        The video_format method returns the video format of a video.

        Returns:
            str: The video format of the video

        """
        return self._video_format

    @video_format.setter
    def video_format(self, value: str) -> None:
        """
        The video_format method sets the video format of a video.

        Args:
            value (str): Set the video format of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_format = value

    @property
    def video_width(self) -> int:
        """
        The video_width method returns the width of a video.

        Returns:
            int: The width of the video

        """
        return self._video_width

    @video_width.setter
    def video_width(self, value: int) -> None:
        """
        The video_width method sets the width of a video.

        Args:
            value (int): Set the width of the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_width = value

    @property
    def video_height(self) -> int:
        """
        The video_height method returns the height of a video.

        Returns:
            int: The height of the video

        """
        return self._video_height

    @video_height.setter
    def video_height(self, value: int) -> None:
        """
        The video_height method sets the height of a video.

        Args:
            value (int): Set the height of the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_height = value

    @property
    def video_ar(self) -> str:
        """
        The video_ar method returns the aspect ratio of a video.

        Returns:
            str: The aspect ratio of the video

        """
        return self._video_ar

    @video_ar.setter
    def video_ar(self, value: str) -> None:
        """
        The video_ar method sets the aspect ratio of a video.

        Args:
            value (str): Set the aspect ratio of the video

        """
        assert isinstance(value, str) and value in (
            sys_consts.AR43,
            sys_consts.AR169,
        ), f"{value=}. Must be either {sys_consts.AR43} or  {sys_consts.AR169}"

        self._video_ar = value

    @property
    def video_par(self) -> float:
        """
        The video_par method returns the pixel aspect ratio of a video.

        Returns:
            float: The pixel aspect ratio of the video

        """
        return self._video_par

    @video_par.setter
    def video_par(self, value: float):
        """
        The video_par method sets the pixel aspect ratio of a video.

        Args:
            value (float): Set the pixel aspect ratio of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_par = value

    @property
    def video_dar(self) -> float:
        """
        The video_dar method returns the display aspect ratio of a video.

        Returns:
            float: The display aspect ratio of the video

        """
        return self._video_dar

    @video_dar.setter
    def video_dar(self, value: float) -> None:
        """
        The video_dar method sets the display aspect ratio of a video.

        Args:
            value (float): Set the display aspect ratio of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_dar = value

    @property
    def video_duration(self) -> float:
        """
        The video_duration method returns the duration of a video.

        Returns:
            float: The duration of the video

        """
        return self._video_duration

    @video_duration.setter
    def video_duration(self, value: float) -> None:
        """
        The video_duration method sets the duration of a video.

        Args:
            value (float): Set the duration of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_duration = value

    @property
    def video_frame_rate(self) -> float:
        """
        The video_frame_rate method returns the frame rate of a video.

        Returns:
            float: The frame rate of the video

        """
        return self._video_frame_rate

    @video_frame_rate.setter
    def video_frame_rate(self, value: float) -> None:
        """
        The video_frame_rate method sets the frame rate of a video.

        Args:
            value (float): Set the frame rate of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_frame_rate = value

    @property
    def video_standard(self) -> str:
        """
        The video_standard method returns the video standard of a video PAL/NTSC.

        Returns:
            str: The video standard of the video

        """
        return self._video_standard

    @video_standard.setter
    def video_standard(self, value: str) -> None:
        """
        The video_standard method sets the video standard of a video PAL/NTSC.

        Args:
            value (str): Set the video standard of the video

        """
        assert isinstance(value, str) and value.upper() in (
            sys_consts.PAL,
            sys_consts.NTSC,
        ), f"{value=}. Must be PAL or NTSC"

        self._video_standard = value.upper()

    @property
    def video_frame_count(self) -> int:
        """
        The video_frame_count method returns the number of frames in a video.

        Returns:
            int: The number of frames in the video

        """
        return self._video_frame_count

    @video_frame_count.setter
    def video_frame_count(self, value: int) -> None:
        """
        The video_frame_count method sets the number of frames in a video.

        Args:
            value (int): Set the number of frames in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_frame_count = value

    @property
    def video_scan_order(self) -> str:
        """
        The video_scan_order method returns the scan order of an interlaced video.

        Returns:
            str: The scan order of the video

        """
        return self._video_scan_order

    @video_scan_order.setter
    def video_scan_order(self, value: str) -> None:
        """
        The video_scan_order method sets the scan order of an interlaced video.

        Args:
            value (str): Set the scan order of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_scan_order = value

    @property
    def video_scan_type(self) -> str:
        """
        The video_scan_type method returns the scan type of an interlaced video.

        Returns:
            str: The scan type of the video

        """
        return self._video_scan_type

    @video_scan_type.setter
    def video_scan_type(self, value: str) -> None:
        """
        The video_scan_type method sets the scan type of an interlaced video.

        Args:
            value (str): Set the scan type of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_scan_type = value


@dataclasses.dataclass(slots=True)
class Video_File_Settings:
    """Class to hold video file settings for each file comprising the DVD menu buttons"""

    _deactivate_filters: bool = False

    _normalise: bool = False
    _denoise: bool = False
    _white_balance: bool = False
    _sharpen: bool = False
    _auto_bright: bool = False
    _button_title: str = ""
    _menu_button_frame: int = -1
    _menu_group: int = -1

    def __post_init__(self) -> None:
        """Post init to check the file settings are valid"""

        assert isinstance(
            self._deactivate_filters, bool
        ), f"{self._deactivate_filters=}. Must be a bool"
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
    def deactivate_filters(self) -> bool:
        """
        The deactivate_filters method overrides  the individual filter settings.

        Args:

        Returns:
            bool : True if deactivating all filters, otherwise False

        """
        return self._deactivate_filters

    @deactivate_filters.setter
    def deactivate_filters(self, value: bool) -> None:
        """
        The deactivate_filters method overrides  the individual filter settings..

        Args:
            value (bool): True to deactivate all filters via override

        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._deactivate_filters = value

    @property
    def filters_off(self) -> bool:
        """
        The filters_off method returns True if all the filter settings are off.

        Args:

        Returns:
            bool : True if all the filter settings are off otherwise False

        """
        if self.deactivate_filters:
            return True
        else:
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
        encoding_info (Video_Details): Information about the encoding of the video.
        video_file_settings (Video_File_Settings): The video file settings.
        vd_id (int): The id of the video data. Defaults to -1.
    """

    video_folder: str
    video_file: str
    video_extension: str
    encoding_info: Encoding_Details
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
            self.encoding_info, Encoding_Details
        ), f"{self.encoding_info=}. Must be Encoding_Details"
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
    _encoding_info: Encoding_Details = dataclasses.field(
        default_factory=Encoding_Details
    )
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
    def encoding_info(self) -> Encoding_Details:
        """
        The file_info method is used to get the video file information.

        Returns:
            Video_Details: The file information
        """

        return self._encoding_info

    @encoding_info.setter
    def encoding_info(self, value: Encoding_Details) -> None:
        """
        The file_info method is used to set the video file information.

        Args:
            value: (Video_Details): The file information

        """
        assert isinstance(
            value, Encoding_Details
        ), f"{value=}. Must be a dict of file properties"

        self._encoding_info = value

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
