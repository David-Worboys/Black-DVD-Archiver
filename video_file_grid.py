"""
Implements the Video_file_Grid UI control.

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
import datetime
from typing import cast, Final

import platformdirs

import dvdarch_utils
import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
import utils
from dvd_menu_configuration import DVD_Menu_Config_Popup
from sys_config import (DVD_Archiver_Base, Get_Video_Editor_Folder, Video_Data, Get_Project_Files, 
                        Get_Project_Layout_Names, Remove_Project_Files)
from video_file_picker import Video_File_Picker_Popup

# fmt: on


@dataclasses.dataclass(slots=True)
class Video_File_Grid(DVD_Archiver_Base):
    """This class implements the file handling of the Black DVD Archiver ui"""

    parent: DVD_Archiver_Base

    # Private instance variables
    _display_filename: bool = True
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _db_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)
    _dvd_percent_used: int = 0  # TODO Make A selection of DVD5 and DVD9
    _file_grid: qtg.Grid = None
    _project_duration: str = ""
    _project_name: str = ""
    _project_video_standard: str = ""  # PAL or NTSC
    _shutdown: bool = False

    @property
    def dvd_percent_used(self) -> int:
        """Returns the percentage of the DVD used

        Allow > 100% because code checks > 100% and code needs to know total percentage even if greater than 100%

        Returns:
            int: The percentage of the DVD used
        """
        return self._dvd_percent_used

    @dvd_percent_used.setter
    def dvd_percent_used(self, value: int) -> None:
        """Sets the percentage of the DVD used

        Allow > 100% because code checks > 100% and code needs to know total percentage even if greater than 100%

        Args:
            value (int): The percentage of the DVD used >= 0
        """

        assert isinstance(value, int) and 0 >= 0, f"{value=}. Must be int >=0"

        self._dvd_percent_used = value

    @property
    def project_duration(self) -> str:
        """Returns the project duration as a string

        Returns:
            str: The project duration
        """
        return self._project_duration

    @project_duration.setter
    def project_duration(self, value: str) -> None:
        """Sets the project duration as a string

        Args:
            value (str): The project duration
        """
        assert isinstance(value, str), f"{value=}. Must be str"
        self._project_duration = value

    @property
    def project_name(self) -> str:
        """Returns the project name

        Returns:
            str: The project name
        """
        return self._project_name

    @project_name.setter
    def project_name(self, value: str) -> None:
        """Sets the project name

        Args:
            value (str): The project name
        """
        assert isinstance(value, str) and value.strip() != "", f"{value=}. Must be str"

        self._project_name = value

    @property
    def project_video_standard(self) -> str:
        """Returns the project video standard

        Returns:
            str: The project video standard ("", PAL or NTSC)
        """
        return self._project_video_standard

    @project_video_standard.setter
    def project_video_standard(self, value: str) -> None:
        """Sets the project video standard

        Args:
            value (str): The project video standard ("", PAL or NTSC)
        """
        assert isinstance(value, str) and value in (
            "",
            sys_consts.PAL,
            sys_consts.NTSC,
        ), f"{value=}. Must be str PAL Or NTSC"
        self._project_video_standard = value

    def __post_init__(self) -> None:
        """Initializes the instance for use"""
        assert isinstance(
            self.parent, DVD_Archiver_Base
        ), f"{self.parent=}. Must be an instance of DVD_Archiver_Base"

        if self._db_settings.setting_exist(sys_consts.LATEST_PROJECT):
            self.project_name = self._db_settings.setting_get(sys_consts.LATEST_PROJECT)
        else:
            self.project_name = sys_consts.DEFAULT_PROJECT_NAME
            self._db_settings.setting_set(sys_consts.LATEST_PROJECT, self.project_name)

    def grid_events(self, event: qtg.Action) -> None:
        """Process Grid Events
        Args:
            event (Action): Action
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        if event.event == qtg.Sys_Events.CLICKED:
            if event.tag.startswith("grid_button"):
                self._edit_video(event)
            elif event.value.row >= 0 and event.value.col >= 0:
                self.set_project_standard_duration(event)

    def process_edited_video_files(self, video_file_input: list[Video_Data]) -> None:
        """
        Called in DVD Archiver to handle the edited video files and place in the file list grid

        Args:
            video_file_input (list[Video_Data]): THhe edited video file list
        """
        assert isinstance(video_file_input, list), f"{video_file_input=}. Must be list"
        assert all(
            isinstance(video_file, Video_Data) for video_file in video_file_input
        ), f"{video_file_input=}. Must be list of Video_Data"

        if (
            len(video_file_input) == 1
        ):  # Original, only user entered file title text might have changed
            self._processed_trimmed(
                self._file_grid,
                video_file_input[0].vd_id,
                video_file_input[0].video_path,
                video_file_input[0].video_file_settings.button_title,
            )
        elif len(video_file_input) == 2:  # Original & one edited file (cut/assemble)
            self._processed_trimmed(
                self._file_grid,
                video_file_input[0].vd_id,
                video_file_input[1].video_path,
                video_file_input[0].video_file_settings.button_title,
            )
        elif len(video_file_input) > 2:  # Original and multiple edited files
            # TODO Make user configurable perhaps
            self._delete_file_from_grid(self._file_grid, video_file_input[0].vd_id)

            # Insert Assembled Children Files
            self._insert_files_into_grid(
                [video_file_data for video_file_data in video_file_input[1:]],
            )

    def _edit_video(self, event: qtg.Action) -> None:
        """
        Edits a video file.
        Args:
            event (qtg.Action): The event that triggered the video edit.
        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        video_editor_folder = Get_Video_Editor_Folder()

        if not video_editor_folder:
            return None

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls", tag="video_input_files"
            ),
        )

        row_unique_id = int(
            event.container_tag.split("|")[0]
        )  # Grid button container tag has the row_id embedded as the 1st element and delimitered by |
        row = file_grid.row_from_item_id(row_unique_id)

        if row == -1:
            popups.PopError(
                title="Edit Video Error...",
                message="Failed To Get Edit Row..",
            ).show()

            return None

        user_data: Video_Data = file_grid.userdata_get(
            row=row, col=file_grid.colindex_get("video_file")
        )
        video_file_input: list[Video_Data] = [user_data]

        self._aspect_ratio = video_file_input[0].encoding_info.video_ar
        self._frame_width = video_file_input[0].encoding_info.video_width
        self._frame_height = video_file_input[0].encoding_info.video_height
        self._frame_rate = video_file_input[0].encoding_info.video_frame_rate
        self._frame_count = video_file_input[0].encoding_info.video_frame_count

        event.tag = "video_editor"
        event.value = video_file_input
        self.parent.event_handler(event)  # Processed in DVD Archiver!

        return None

    def check_file(self, file_grid: qtg.Grid, vd_id: int, checked: bool) -> None:
        """Checks the file (identified by vd_id) in the file grid.

        Args:
            file_grid (qtg.Grid): An instance of the `Grid` class.
            vd_id (int): The Video_Data ID of the source file that is to be checked.
            checked (bool): True Checked, False Unchecked
        """
        assert isinstance(file_grid, qtg.Grid), f"{file_grid}. Must be a Grid instance"
        assert isinstance(vd_id, int), f"{vd_id=}. Must be an int"
        assert isinstance(checked, bool), f"{checked=}. Must be a bool"

        col_index = file_grid.colindex_get("video_file")

        for row in range(file_grid.row_count):
            user_data: Video_Data = file_grid.userdata_get(row=row, col=col_index)

            if user_data and user_data.vd_id == vd_id:
                file_grid.checkitemrow_set(row=row, col=col_index, checked=checked)

    def _delete_file_from_grid(
        self,
        file_grid: qtg.Grid,
        vd_id: int,
    ) -> None:
        """Delete the source file from the file grid.
        Args:
            file_grid (qtg.Grid): An instance of the `Grid` class.
            vd_id (int): The Video_Data ID of the source file that is to be deleted.
        """
        assert isinstance(file_grid, qtg.Grid), f"{file_grid}. Must be a Grid instance"

        for row in range(file_grid.row_count):
            user_data: Video_Data = file_grid.userdata_get(
                row=row, col=file_grid.colindex_get("video_file")
            )

            if user_data and user_data.vd_id == vd_id:
                file_grid.row_delete(row)

    def _processed_trimmed(
        self,
        file_grid: qtg.Grid,
        vd_id: int,
        trimmed_file: str,
        button_title: str = "",
    ) -> None:
        """
        Updates the file_grid with the trimmed_file detail, after finding the corresponding grid entry.
        Args:
            file_grid (qtg.Grid): The grid to update.
            vd_id (int): The Video_Data ID of the source file.
            trimmed_file (str): The trimmed file to update the grid details with.
            button_title (str): The button title to update the grid details with.
        """
        assert isinstance(file_grid, qtg.Grid), f"{file_grid=}. Must be qtg.Grid,"
        assert isinstance(vd_id, int) and vd_id >= 0, f"{vd_id=}. Must be an int >= 0"

        file_handler = file_utils.File()

        (
            trimmed_folder,
            trimmed_file_name,
            trimmed_extension,
        ) = file_handler.split_file_path(trimmed_file)

        # Scan looking for source of trimmed file
        for row in range(file_grid.row_count):
            user_data: Video_Data = file_grid.userdata_get(
                row=row, col=file_grid.colindex_get("video_file")
            )

            if user_data and vd_id == user_data.vd_id:
                encoding_info = dvdarch_utils.Get_File_Encoding_Info(trimmed_file)
                if encoding_info.error:  # Error Occurred
                    popups.PopError(
                        title="Encoding Read Error...",
                        message=encoding_info.error,
                    ).show()
                    return None

                if (
                    button_title
                    and user_data.video_file_settings.button_title != button_title
                ):
                    user_data.video_file_settings.button_title = button_title

                updated_user_data = Video_Data(
                    video_folder=trimmed_folder,
                    video_file=trimmed_file_name,
                    video_extension=trimmed_extension,
                    encoding_info=encoding_info,
                    video_file_settings=user_data.video_file_settings,
                )

                duration = str(
                    datetime.timedelta(
                        seconds=updated_user_data.encoding_info.video_duration
                    )
                ).split(".")[0]

                self._populate_grid_row(
                    file_grid=file_grid,
                    row_index=row,
                    video_data=updated_user_data,
                    duration=duration,
                )

                for col in range(0, file_grid.col_count):
                    file_grid.userdata_set(
                        row=row, col=col, user_data=updated_user_data
                    )

                break  # Only one trimmed file

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  application events
        Args:
            event (Action): The triggering event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        match event.event:
            case qtg.Sys_Events.APPINIT:
                if self._db_settings.setting_exist(sys_consts.LATEST_PROJECT):
                    self.project_name = self._db_settings.setting_get(
                        sys_consts.LATEST_PROJECT
                    )
                else:
                    self.project_name = sys_consts.DEFAULT_PROJECT_NAME

            case qtg.Sys_Events.APPPOSTINIT:
                self.postinit_handler(event)

                event.event = qtg.Sys_Events.CUSTOM
                event.container_tag = ""
                event.tag = "project_changed"
                event.value = self.project_name
                self.parent.event_handler(event=event)

            case qtg.Sys_Events.APPEXIT | qtg.Sys_Events.APPCLOSED:
                if not self._shutdown:  # Prevent getting called twice
                    self._shutdown = True

                    if not self.project_name.strip():
                        project_name = popups.PopTextGet(
                            title="Enter Project Name",
                            label="Project Name:",
                            label_above=False,
                        ).show()
                        if project_name.strip():
                            self._db_settings.setting_set(
                                sys_consts.LATEST_PROJECT, project_name
                            )

                    else:  # Project might be changed
                        self._db_settings.setting_set(
                            sys_consts.LATEST_PROJECT, self.project_name
                        )
                self._save_grid(event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "bulk_select":
                        file_grid: qtg.Grid = cast(
                            qtg.Grid,
                            event.widget_get(
                                container_tag="video_file_controls",
                                tag="video_input_files",
                            ),
                        )

                        file_grid.checkitems_all(
                            checked=event.value, col_tag="video_file"
                        )

                        self.set_project_standard_duration(event)
                    case "normalise":
                        self._db_settings.setting_set(
                            sys_consts.VF_NORMALISE, event.value
                        )
                    case "denoise":
                        self._db_settings.setting_set(
                            sys_consts.VF_DENOISE, event.value
                        )
                    case "white_balance":
                        self._db_settings.setting_set(
                            sys_consts.VF_WHITE_BALANCE, event.value
                        )
                    case "sharpen":
                        self._db_settings.setting_set(
                            sys_consts.VF_SHARPEN, event.value
                        )
                    case "auto_levels":
                        self._db_settings.setting_set(
                            sys_consts.VF_AUTO_LEVELS, event.value
                        )
                    case "dvd_menu_configuration":
                        DVD_Menu_Config_Popup(title="DVD Menu Configuration").show()
                    case "group_files":
                        self._group_files(event)
                    case "join_files":
                        self._join_files(event)
                    case "move_video_file_down":
                        self._move_video_file(event=event, up=False)
                    case "move_video_file_up":
                        self._move_video_file(event=event, up=True)

                    case "select_files":
                        video_editor_folder = Get_Video_Editor_Folder()

                        if video_editor_folder.strip() == "":
                            return None

                        self.load_video_input_files(event)
                    case "remove_files":
                        self._remove_files(event)

                    case "toggle_file_button_names":
                        if self._display_filename:
                            self._display_filename = False
                        else:
                            self._display_filename = True
                        self._toggle_file_button_names(event)
                    case "ungroup_files":
                        self._ungroup_files(event)

    def project_changed(
        self, event: qtg.Action, project_name: str, save_existing: bool
    ):
        """Handles the change of a project

        Args:
            event (qtg.Action): The triggering event
            project_name (str): The name of the project
            save_existing (bool): If True saves the existing project, else does not
        """
        assert (
            isinstance(project_name, str) and project_name.strip() != ""
        ), f"{project_name=}. Must be non-empty str"

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        if save_existing and file_grid.changed:
            self._save_grid(event)

        self.project_name = project_name

        project_names, _, result = Get_Project_Layout_Names(
            project_name=self.project_name
        )

        if result == -1:
            popups.PopError(
                title="Project Changed Error...", message="Failed to Get Project Files"
            ).show()
            return None

        self._db_settings.setting_set(sys_consts.LATEST_PROJECT, self.project_name)

        if self.project_name in project_names:  # Existing Project
            file_grid.clear()
            self._load_grid(event)
        else:
            file_grid.clear()

        self._save_grid(event)

        event.event = qtg.Sys_Events.CUSTOM
        event.container_tag = ""
        event.tag = "project_changed"
        event.value = self.project_name
        self.parent.event_handler(event=event)

        return None

    def postinit_handler(self, event: qtg.Action):
        """
        The postinit_handler method is called after the GUI has been created.
        It is used to set default values for widgets

        Args:
            event (qtg.Action) : The triggering event

        Returns:
            None

        """

        self._load_grid(event)

        if self._db_settings.setting_exist(sys_consts.VF_NORMALISE):
            event.value_set(
                container_tag="default_video_filters",
                tag="normalise",
                value=self._db_settings.setting_get(sys_consts.VF_NORMALISE),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="normalise",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_DENOISE):
            event.value_set(
                container_tag="default_video_filters",
                tag="denoise",
                value=self._db_settings.setting_get(sys_consts.VF_DENOISE),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="denoise",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_WHITE_BALANCE):
            event.value_set(
                container_tag="default_video_filters",
                tag="white_balance",
                value=self._db_settings.setting_get(sys_consts.VF_WHITE_BALANCE),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="white_balance",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_SHARPEN):
            event.value_set(
                container_tag="default_video_filters",
                tag="sharpen",
                value=self._db_settings.setting_get(sys_consts.VF_SHARPEN),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="sharpen",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_AUTO_LEVELS):
            event.value_set(
                container_tag="default_video_filters",
                tag="auto_levels",
                value=self._db_settings.setting_get(sys_consts.VF_AUTO_LEVELS),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="auto_levels",
                value=False,
            )

        # Hot wire to show title names instead of file names #TODO:  make this user settable
        event.event = qtg.Sys_Events.CLICKED
        event.tag = "toggle_file_button_names"
        self.event_handler(event)

    def _join_files(self, event: qtg.Action) -> None:
        """
        Joins selected files. The joined files are concatenated onto the first selected file

        Args:
            event (qtg.Action): The event triggering the ungrouping.

        Returns:
            None
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        # Get the required file paths
        file_handler = file_utils.File()
        video_editor_folder = Get_Video_Editor_Folder()

        if video_editor_folder.strip() == "":
            return None

        video_editor_folder = file_handler.file_join(
            video_editor_folder, utils.Text_To_File_Name(self.project_name)
        )

        if not file_handler.path_exists(video_editor_folder):
            if file_handler.make_dir(video_editor_folder) == -1:
                popups.PopError(
                    title="Error Creating Project Folder",
                    message=(
                        "Error Creating Project Folder!\n"
                        f"{sys_consts.SDELIM}{video_editor_folder}{sys_consts.SDELIM}"
                    ),
                ).show()
                return None

        edit_folder = file_handler.file_join(
            video_editor_folder, sys_consts.EDIT_FOLDER
        )

        if not file_handler.path_exists(edit_folder):
            if file_handler.make_dir(edit_folder) == -1:
                popups.PopError(
                    title="Error Creating Edit Folder",
                    message=(
                        "Error Creating Edit Folder!\n"
                        f"{sys_consts.SDELIM}{edit_folder}{sys_consts.SDELIM}"
                    ),
                ).show()
                return None

        transcode_folder = file_handler.file_join(
            video_editor_folder,
            sys_consts.TRANSCODE_FOLDER,
        )

        if not file_handler.path_exists(transcode_folder):
            if file_handler.make_dir(transcode_folder) == -1:
                popups.PopError(
                    title="Error Creating Transcode Folder",
                    message=(
                        "Error Creating Transcode Folder!\n"
                        f"{sys_consts.SDELIM}{transcode_folder}{sys_consts.SDELIM}"
                    ),
                ).show()
                return None

        # Transcode or Join the selected files
        checked_items = file_grid.checkitems_get

        if not checked_items:
            popups.PopError(
                title="No Files Selected", message="Please Select Files To Join"
            ).show()
            return None

        copy_method = ""

        if len(checked_items) == 1:  # Only one file selected, so transcode only
            copy_title = "Re-Encode File..."
            copy_message = "Re-Encode Selected File"
            copy_option = {
                "Make Edit File - Slow   :: Transcode File Into An Intermediate Edit File Format Suitable For Editing": "reencode_edit",
                "Re-Encode H264 - Slower :: Transcode File Into The Common H264 Format": "reencode_h264",
                "Re-Encode H265 - Slowest ::Transcode File Into The Common H264 Format": "reencode_h265",
            }
        else:  # Join files
            copy_title = "Join Files..."
            copy_message = "Join Selected Files"

            file_extension = checked_items[0].user_data.video_extension.lower()

            # HD Camcorder MTS files gave me no end of trouble, so have to reencode to mezzanine
            if all(
                item.user_data.video_path.lower().endswith("mts")
                for item in checked_items
            ):
                copy_option = {}
                copy_method = ""

                if (
                    popups.PopYesNo(
                        title="MTS Files Selected...",
                        message="MTS Joins Are Re-encoded As A High Quality Edit File - This Takes Some Time! Continue?",
                    ).show()
                    == "yes"
                ):
                    copy_method = "transjoin_edit"  # Makes a mezzanine edit master
            elif all(
                item.user_data.video_path.lower().endswith("mod")
                for item in checked_items
            ):
                copy_option = {}
                copy_method = "stream_copy"  # At least until tested
            elif all(
                item.user_data.video_path.lower().endswith(file_extension)
                for item in checked_items
            ):  # All files of the same type can stream copy
                copy_option = {
                    "Stream Copy - Fast       :: Use Where There Is No Problem Joining Files ": (
                        "stream_copy"
                    ),
                    "Make Edit File - Slow    :: Use Where There Is A Problem Joining Files & The Joined File Needs "
                    "To Be Edited": "transjoin_edit",
                    "Re-Encode H264 - Slower  ::  Use To Join Files Into The Common H264 Format": "transjoin_h264",
                    "Re-Encode H265 - Slowest ::  Use To Join Files Into The Newer H265 Format": "transjoin_h265",
                }
            else:  # Different file extensions, need a transcode copy
                copy_option = {
                    "Make Edit File - Slow   :: Use Where The Joined Files Needs To Be Edited   ": "transjoin_edit",
                    "Re-Encode H264 - Slower :: Use To Join Files Into The Common H264 Format ": "transjoin_h264",
                    "Re-Encode H265 - Slowest:: Use To Join Files Into The Newer H265 Format": "transjoin_h265",
                }

        if copy_option:
            copy_method = popups.PopOptions(
                title=copy_title,
                message=copy_message,
                options=copy_option,
            ).show()

        if copy_method.strip() == "" or copy_method == "cancel":
            return None
        else:
            concatenating_files = []
            video_file_data = []
            removed_files = []
            output_file = ""
            vd_id = -1
            button_title = ""
            container_format = "mp4"  # TODO Make user selectable - mpg, mp4

            for item in checked_items:
                item: qtg.Grid_Item
                video_data: Video_Data = item.user_data

                if not output_file:  # Happens on first iteration
                    vd_id = video_data.vd_id
                    button_title = video_data.video_file_settings.button_title
                    output_file = file_handler.file_join(
                        dir_path=transcode_folder,
                        file_name=f"{video_data.video_file}_joined",
                        ext=(
                            container_format
                            if copy_method == "transcode_copy"
                            else video_data.video_extension
                        ),
                    )
                else:
                    removed_files.append(video_data)

                concatenating_files.append(video_data.video_path)
                video_file_data.append(video_data)

            if concatenating_files and output_file:
                result = -1
                message = ""

                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    match copy_method:
                        case "reencode_edit":  # Only one file selected with this option
                            video_data = video_file_data[0]

                            result, message = dvdarch_utils.Transcode_Mezzanine(
                                input_file=video_data.video_path,
                                frame_rate=video_data.encoding_info.video_frame_rate,
                                output_folder=transcode_folder,
                                width=video_data.encoding_info.video_width,
                                height=video_data.encoding_info.video_height,
                                interlaced=True
                                if video_data.encoding_info.video_scan_type.lower()
                                == "interlaced"
                                else False,
                                bottom_field_first=True
                                if video_data.encoding_info.video_scan_order.lower()
                                == "bff"
                                else False,
                            )
                        case "reencode_h264":  # Only one file selected  with this option
                            video_data = video_file_data[0]
                            result, message = dvdarch_utils.Transcode_H26x(
                                input_file=video_data.video_path,
                                frame_rate=video_data.encoding_info.video_frame_rate,
                                output_folder=transcode_folder,
                                width=video_data.encoding_info.video_width,
                                height=video_data.encoding_info.video_height,
                                interlaced=True
                                if video_data.encoding_info.video_scan_type.lower()
                                == "interlaced"
                                else False,
                                bottom_field_first=True
                                if video_data.encoding_info.video_scan_order.lower()
                                == "bff"
                                else False,
                                h265=False,
                            )
                        case "reencode_h265":  # Only one file selected  with this option
                            video_data = video_file_data[0]
                            result, message = dvdarch_utils.Transcode_H26x(
                                input_file=video_data.video_path,
                                frame_rate=video_data.encoding_info.video_frame_rate,
                                output_folder=transcode_folder,
                                width=video_data.encoding_info.video_width,
                                height=video_data.encoding_info.video_height,
                                interlaced=True
                                if video_data.encoding_info.video_scan_type.lower()
                                == "interlaced"
                                else False,
                                bottom_field_first=True
                                if video_data.encoding_info.video_scan_order.lower()
                                == "bff"
                                else False,
                                h265=True,
                            )
                        case "stream_copy":  # Multiple files selected from here on
                            result, message = dvdarch_utils.Concatenate_Videos(
                                temp_files=concatenating_files, output_file=output_file
                            )
                        case "transjoin_edit":
                            result, message = dvdarch_utils.Concatenate_Videos(
                                temp_files=concatenating_files,
                                output_file=output_file,
                                transcode_format="mjpeg",
                            )
                        case "transjoin_h264":
                            result, message = dvdarch_utils.Concatenate_Videos(
                                temp_files=concatenating_files,
                                output_file=output_file,
                                transcode_format="h264",
                            )
                        case "transjoin_h265":
                            result, message = dvdarch_utils.Concatenate_Videos(
                                temp_files=concatenating_files,
                                output_file=output_file,
                                transcode_format="h265",
                            )

                if result == -1:
                    popups.PopError(
                        title="Error Joining Files",
                        message=(
                            "File Join"
                            f" Failed!\n{sys_consts.SDELIM}{message}{sys_consts.SDELIM}"
                        ),
                    ).show()

                    return None
                else:
                    # If all good message has the output file name. A reencode concat will have a different extension. A
                    # stream concat will have the same extension as the inpt file. This will be the only delta
                    output_file = message

                self._processed_trimmed(
                    file_grid,
                    vd_id,
                    output_file,
                    button_title,
                )

                removed_file_txt = "\n".join(
                    video_data.video_path for video_data in removed_files
                )

                delete_source = False
                if (
                    popups.PopYesNo(
                        width=80,
                        title="Remove Source Video Files?",
                        message=(
                            "Delete Source Video Files?"
                            f" {sys_consts.SDELIM}\n{removed_file_txt}{sys_consts.SDELIM}"
                        ),
                    ).show()
                    == "yes"
                ):
                    delete_source = True

                failed = []
                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    for video_data in removed_files:
                        self._delete_file_from_grid(file_grid, video_data.vd_id)
                        if delete_source:
                            if file_handler.remove_file(video_data.video_path) == -1:
                                failed.append(video_data.video_path)

                if failed:
                    failed_txt = "\n".join(failed)
                    popups.PopError(
                        width=80,
                        title="Error Removing Video Files...",
                        message=(
                            "Failed To Remove Source Video Files:"
                            f" {sys_consts.SDELIM}{failed_txt}{sys_consts.SDELIM}"
                        ),
                    ).show()

    def _remove_files(self, event: qtg.Action) -> None:
        """Removes the selected files

        Args:
            event (qtg.Action) : Calling event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        if (
            file_grid.row_count > 0
            and file_grid.checkitems_get
            and popups.PopYesNo(
                title="Remove Selected...",
                message="Remove The Selected Files?",
            ).show()
            == "yes"
        ):
            for item in reversed(file_grid.checkitems_get):
                item: qtg.Grid_Item
                file_grid.row_delete(item.row_index)
            self._save_grid(event)

        self.set_project_standard_duration(event)

        if event.value_get(container_tag="video_file_controls", tag="bulk_select"):
            event.value_set(
                container_tag="video_file_controls", tag="bulk_select", value=False
            )

    def _move_video_file(self, event: qtg.Action, up: bool) -> None:
        """
        Move the selected video file up or down in the file list grid.

        Args:
            event (qtg.Action): Calling event
            up (bool): True to move the video file up, False to move it down.
        """

        assert isinstance(up, bool), f"{up=}. Must be bool"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        checked_items: tuple[qtg.Grid_Item] = (
            file_grid.checkitems_get
            if up
            else tuple(reversed(file_grid.checkitems_get))
        )

        assert all(
            isinstance(item, qtg.Grid_Item) for item in checked_items
        ), f"{checked_items=}. Must be a list of 'qtg.Grid_Item_Tuple'"

        if not checked_items:
            popups.PopMessage(
                title="Select A Video file...",
                message="Please Select A Video File To Move!",
            ).show()
            return None

        checked_indices = [item.row_index for item in checked_items]
        index_range = (
            list(range(min(checked_indices), max(checked_indices) + 1))
            if up
            else list(range(max(checked_indices), min(checked_indices) - 1, -1))
        )

        if (
            len(checked_indices) > 1 and checked_indices != index_range
        ):  # Contiguous block check failed
            popups.PopMessage(
                title="Selected Video files Not Contiguous...",
                message="Selected Video files Must Be A Contiguous Block!",
            ).show()
            return None

        for checked_item in checked_items:
            if up:
                if checked_item.row_index == 0:
                    break
            else:
                if checked_item.row_index == file_grid.row_count - 1:
                    break

            file_grid.checkitemrow_set(
                False, checked_item.row_index, file_grid.colindex_get("video_file")
            )
            file_grid.select_row(checked_item.row_index)

            current_row = checked_item.row_index
            group_disp = file_grid.value_get(
                current_row, file_grid.colindex_get("group")
            )
            group_id = int(group_disp) if group_disp else -1
            current_video_data: Video_Data = file_grid.userdata_get(
                current_row, file_grid.colindex_get("group")
            )

            if up and current_row > 1:
                # look backward for group id to use if no group id is found in the current row
                look_backward_group_id = ""
                if current_row > 2:
                    look_backward_group_id = file_grid.value_get(
                        current_row - 2, file_grid.colindex_get("group")
                    )

                prev_group_id = file_grid.value_get(
                    current_row - 1, file_grid.colindex_get("group")
                )
                if not prev_group_id and look_backward_group_id:
                    prev_group_id = look_backward_group_id

                if prev_group_id:
                    prev_video_data: Video_Data = file_grid.userdata_get(
                        current_row - 1, file_grid.colindex_get("group")
                    )
                    group_id = int(prev_group_id)
                    current_video_data.video_file_settings.menu_group = (
                        prev_video_data.video_file_settings.menu_group
                    )
                else:
                    group_id = -1

            elif not up and current_row < file_grid.row_count - 1:
                # look ahead for group id to use if no group id is found in the current row
                look_forward_group_id = ""
                if current_row < file_grid.row_count - 2:
                    look_forward_group_id = file_grid.value_get(
                        current_row + 2, file_grid.colindex_get("group")
                    )

                next_group_id = file_grid.value_get(
                    current_row + 1, file_grid.colindex_get("group")
                )
                if not next_group_id and look_forward_group_id:
                    next_group_id = look_forward_group_id

                if next_group_id:
                    next_video_data: Video_Data = file_grid.userdata_get(
                        current_row + 1, file_grid.colindex_get("group")
                    )
                    group_id = int(next_group_id)
                    current_video_data.video_file_settings.menu_group = (
                        next_video_data.video_file_settings.menu_group
                    )
                else:
                    group_id = -1

            file_grid.value_set(
                row=current_row,
                col=file_grid.colindex_get("group"),
                value=str(group_id) if group_id >= 0 else "",
                user_data=current_video_data,
            )

            for col in range(file_grid.col_count):
                file_grid.userdata_set(
                    row=current_row,
                    col=col,
                    user_data=current_video_data,
                )

            new_row = (
                file_grid.move_row_up(current_row)
                if up
                else file_grid.move_row_down(current_row)
            )

            if new_row >= 0:
                file_grid.checkitemrow_set(
                    True, new_row, file_grid.colindex_get("video_file")
                )
                file_grid.select_col(new_row, file_grid.colindex_get("video_file"))
            else:
                file_grid.checkitemrow_set(
                    True,
                    checked_items[0].row_index,
                    file_grid.colindex_get("video_file"),
                )
                file_grid.select_col(
                    checked_items[0].row_index, file_grid.colindex_get("video_file")
                )

    def _load_grid(self, event: qtg.Action) -> None:
        """Loads the grid from the database

        Args:
            event (qtg.Action): Calling event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_handler = file_utils.File()

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        removed_files = []

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            result, shelf_list = Get_Project_Files(project_name=self.project_name)

            if result == -1:
                popups.PopError(
                    title="File Grid Load Error...", message="Failed To Load Files!"
                ).show()
                return None

            grid_row = 0
            for shelf_item in shelf_list:
                if (
                    shelf_item["video_data"] is None
                ):  # This is an error and should not happen
                    continue

                if not file_handler.file_exists(shelf_item["video_data"].video_path):
                    removed_files.append(shelf_item["video_data"].video_path)
                    continue

                video_data: Video_Data = shelf_item["video_data"]

                self._populate_grid_row(
                    file_grid=file_grid,
                    row_index=grid_row,
                    video_data=shelf_item["video_data"],
                    duration=shelf_item["duration"],
                    italic=True
                    if "dvdmenu" in shelf_item
                    else False,  # Item comes from a dvd layout button
                    tooltip=f"{sys_consts.SDELIM} {shelf_item['dvdmenu']} {video_data.video_path}{sys_consts.SDELIM}"
                    if "dvdmenu" in shelf_item
                    else "",
                )
                toolbox = self._get_toolbox(shelf_item["video_data"])
                file_grid.row_widget_set(
                    row=grid_row,
                    col=file_grid.colindex_get("settings"),
                    widget=toolbox,
                )

                grid_row += 1

            file_grid.row_scroll_to(0)
            self.set_project_standard_duration(event)

            # Cleanup pass to ensure correctness of grid
            for check_row_index in reversed(range(self._file_grid.row_count)):
                grid_video_data: Video_Data = self._file_grid.userdata_get(
                    row=check_row_index,
                    col=self._file_grid.colindex_get("video_file"),
                )

                # If grid_video_data is None, something went off the rails badly
                if grid_video_data is None:
                    self._file_grid.row_delete(check_row_index)
                    continue

                if check_row_index > 0:
                    prior_grid_video_data: Video_Data = self._file_grid.userdata_get(
                        row=check_row_index - 1,
                        col=self._file_grid.colindex_get("video_file"),
                    )

                    if prior_grid_video_data is None:
                        self._file_grid.row_delete(check_row_index)
                        continue

                    if grid_video_data.video_path == prior_grid_video_data.video_path:
                        self._file_grid.row_delete(check_row_index)
        if removed_files:
            removed_file_list = "\n".join(removed_files)
            popups.PopMessage(
                width=120,
                title="Source Files Not Found...",
                message=(
                    "The Following Video Files Do Not Exist And Were Removed"
                    " From The Project Grid:\n\n"
                    f"{sys_consts.SDELIM}{removed_file_list}{sys_consts.SDELIM}"
                ),
            ).show()

            if (
                popups.PopYesNo(
                    title="Remove From Project..",
                    message="Permanently Remove These Files From The Project And Project DVD Layouts?",
                ).show()
                == "yes"
            ):
                result, message = Remove_Project_Files(
                    project_name=self.project_name, file_paths=removed_files
                )

                if result == -1:
                    popups.PopError(
                        title="Project File Error...",
                        message=f"Failed To Remove Files! <{message}>",
                    ).show()
                    return None

        return None

    def _save_grid(self, event: qtg.Action) -> None:
        """Saves the grid to the database

        Args:
            event (qtg.Action) : Calling event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        error_title: Final[str] = "File Grid Save Error..."

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)

        if sql_shelf.error.code == -1:
            popups.PopError(
                title=error_title,
                message=f"Instantiate - {sql_shelf.error.message}",
            ).show()
            return None

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            shelf_dict = sql_shelf.open(shelf_name="video_grid")

            if sql_shelf.error.code == -1:
                popups.PopError(
                    title=error_title,
                    message=f"Open -{sql_shelf.error.message}",
                ).show()
                return None

            row_data = []
            for row in range(file_grid.row_count):
                row_data.append({
                    "row_index": row,
                    "video_data": file_grid.userdata_get(row=row, col=0),
                    "duration": file_grid.value_get(
                        row=row, col=file_grid.colindex_get("duration")
                    ),
                })

            shelf_dict[self.project_name] = row_data

            result, message = sql_shelf.update(
                shelf_name="video_grid",
                shelf_data=shelf_dict,
            )

            if result == -1:
                popups.PopError(title=error_title, message=f"Update - {message}").show()

        return None

    def _toggle_file_button_names(self, event) -> None:
        """Toggles between file name display and button title display depending on the value of self._display_filename

        Args:
            event (qtg.Acton) : Calling event
        """
        file_handler = file_utils.File()

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        for row_index in range(file_grid.row_count):
            grid_video_data: Video_Data = file_grid.userdata_get(
                row=row_index, col=file_grid.colindex_get("video_file")
            )

            if grid_video_data is None:  # Error loading grid
                continue

            if grid_video_data.video_file_settings.button_title.strip() == "":
                grid_video_data.video_file_settings.button_title = (
                    file_handler.extract_title(grid_video_data.video_file)
                )

            if self._display_filename:
                file_grid.value_set(
                    row=row_index,
                    col=file_grid.colindex_get("video_file"),
                    value=(
                        f"{grid_video_data.video_file}{grid_video_data.video_extension}"
                    ),
                    user_data=grid_video_data,
                )
            else:
                file_grid.value_set(
                    row=row_index,
                    col=file_grid.colindex_get("video_file"),
                    value=grid_video_data.video_file_settings.button_title,
                    user_data=grid_video_data,
                )

            for col in range(file_grid.col_count):
                file_grid.userdata_set(
                    row=row_index, col=col, user_data=grid_video_data
                )

    def _get_max_group_num(self, file_grid: qtg.Grid) -> int:
        """
        Scan all items in the file_grid and return the maximum menu_group number.

        Args:
            file_grid (qtg.Grid): The grid containing the items.

        Returns:
            int: The maximum menu_group number.
        """
        assert isinstance(
            file_grid, qtg.Grid
        ), f"{file_grid=}. Must be an instance of qtg.Grid"

        max_group_num = 0

        for row in range(file_grid.row_count):
            video_item = file_grid.userdata_get(
                row=row, col=file_grid.colindex_get("video_file")
            )
            if isinstance(video_item, Video_Data):
                menu_group = video_item.video_file_settings.menu_group
                if menu_group > max_group_num:
                    max_group_num = menu_group

        return max_group_num

    def _group_files(self, event: qtg.Action) -> None:
        """
        Groups selected files by assigning them to the same menu_group.

        Args:
            event (qtg.Action): The event triggering the grouping.
        """

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        checked_items = file_grid.checkitems_get

        if not checked_items:
            popups.PopError(
                title="No Files Selected", message="Please Select Files To Group"
            ).show()
            return None

        grouped = []
        ungrouped = []
        group_id = -1
        group_aspect_ratio = ""  # All group members must be the same aspect ratio
        max_group_val = self._get_max_group_num(file_grid)

        for item in checked_items:
            video_item: Video_Data = item.user_data

            if video_item.video_file_settings.menu_group >= 0:
                grouped.append(video_item)
            else:
                ungrouped.append(item)

        if grouped:
            for video_item in grouped:
                if not group_aspect_ratio:
                    group_aspect_ratio = video_item.encoding_info.video_ar

                if video_item.video_file_settings.menu_group >= 0:
                    if (
                        group_id >= 0
                        and group_id != video_item.video_file_settings.menu_group
                    ):
                        popups.PopError(
                            title="Grouping Error...",
                            message="All Files Must Be In The Same Group",
                        ).show()
                        return None

                    group_id = video_item.video_file_settings.menu_group

        group_value = group_id if group_id >= 0 else max_group_val + 1

        # Add ungrouped to grouped
        for item in ungrouped:
            video_item: Video_Data = item.user_data
            if (
                group_aspect_ratio
                and video_item.encoding_info.video_ar != group_aspect_ratio
            ):  # All group members must be the same aspect ratio
                popups.PopError(
                    title="Aspect Ratio Error..",
                    message=(
                        "Group Aspect ratio"
                        f" {sys_consts.SDELIM}{group_aspect_ratio}{sys_consts.SDELIM} Does"
                        " Not Match"
                        f"{sys_consts.SDELIM}{video_item.video_file} {video_item.encoding_info.video_ar}{sys_consts.SDELIM}"
                    ),
                ).show()

                continue

            video_item.video_file_settings.menu_group = group_value
            file_grid.value_set(
                row=item.row_index,
                col=file_grid.colindex_get("group"),
                value=f"{group_value}",
                user_data=video_item,
            )
        file_grid.checkitems_all(checked=False)

    def _ungroup_files(self, event: qtg.Action) -> None:
        """
        Ungroups selected files by setting their menu_group to -1.

        Args:
            event (qtg.Action): The event triggering the ungrouping.

        Returns:
            None
        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        checked_items = file_grid.checkitems_get

        if not checked_items:
            popups.PopError(
                title="No Files Selected", message="Please Select Files To Ungroup"
            ).show()
            return None

        if (
            popups.PopYesNo(
                title="Ungroup Files", message="Ungroup Selected Files?"
            ).show()
            == "yes"
        ):
            for item in checked_items:
                video_item: Video_Data = item.user_data
                video_item.video_file_settings.menu_group = -1
                file_grid.value_set(
                    row=item.row_index,
                    col=file_grid.colindex_get("group"),
                    value="",
                    user_data=video_item,
                )

    def load_video_input_files(self, event: qtg.Action) -> None:
        """Loads video files into the video input grid
        Args:
            event (qtg.Acton) : Calling event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        video_file_list: list[Video_Data] = []

        Video_File_Picker_Popup(
            title="Choose Video Files",
            container_tag="video_file_picker",
            video_file_list=video_file_list,  # Pass by ref
        ).show()

        if video_file_list:
            file_grid: qtg.Grid = cast(
                qtg.Grid,
                event.widget_get(
                    container_tag="video_file_controls",
                    tag="video_input_files",
                ),
            )

            with qtg.sys_cursor(qtg.Cursor.hourglass):
                # Performs grid cleansing
                rejected = self._insert_files_into_grid(video_file_list)

            if file_grid.row_count > 0:
                loaded_files = []
                for row_index in reversed(range(file_grid.row_count)):
                    grid_video_data: Video_Data = file_grid.userdata_get(
                        row=row_index, col=file_grid.colindex_get("settings")
                    )

                    if grid_video_data is None:
                        continue

                    loaded_files.append(grid_video_data.video_path)
                self._save_grid(event)

                # Keep a list of words common to all file names
                self.common_words = utils.Find_Common_Words(loaded_files)

            self._toggle_file_button_names(event)
            self.set_project_standard_duration(event)

            if rejected != "":
                popups.PopMessage(
                    title="These Files Are Not Permitted...",
                    message=f"The Files Below Failed Acceptability Checks:\n{rejected}",
                    width=80,
                ).show()
        return None

    def _insert_files_into_grid(
        self,
        selected_files: list[Video_Data],
    ) -> str:
        """
        Inserts files into the file grid widget.

        Args:
            selected_files (list[Video_Data]): list of video file data

        Returns:
            str: A string containing information about any rejected files.
        """
        assert isinstance(
            selected_files, list
        ), f"{selected_files=}.  Must be a list of Video_Data objects"
        assert all(
            isinstance(item, Video_Data) for item in selected_files
        ), f"{selected_files=}.  Must be a list of Video_Data objects"

        rejected = ""
        rows_loaded = self._file_grid.row_count
        row_index = 0
        video_standard = ""

        while self._file_grid.row_count > 0:
            grid_video_data = self._file_grid.userdata_get(
                row=0, col=self._file_grid.colindex_get("video_file")
            )

            if grid_video_data is None:  # The First row is invalid, so remove it
                self._file_grid.row_delete(0)
            else:
                video_standard = grid_video_data.encoding_info.video_standard
                break

        for file_video_data in selected_files:
            # Check if file already loaded in grid and cleanse the grid of bad data
            for check_row_index in reversed(range(self._file_grid.row_count)):
                grid_video_data: Video_Data = self._file_grid.userdata_get(
                    row=check_row_index, col=self._file_grid.colindex_get("video_file")
                )

                if grid_video_data is None:  # Invalid row so remove it
                    self._file_grid.row_delete(int(row_index))
                    continue

                if grid_video_data.video_path == file_video_data.video_path:
                    break
            else:  # File not in the grid
                if (
                    file_video_data.encoding_info.video_tracks <= 0
                    or file_video_data.encoding_info.video_standard
                    not in (
                        sys_consts.PAL,
                        sys_consts.NTSC,
                    )
                ):
                    file_video_data.encoding_info = (
                        dvdarch_utils.Get_File_Encoding_Info(file_video_data.video_path)
                    )

                if file_video_data.encoding_info.error:  # Error Occurred
                    rejected += (
                        "File Error"
                        f" {sys_consts.SDELIM}{file_video_data.video_path} :"
                        f"  {file_video_data.encoding_info.error}{sys_consts.SDELIM} \n"
                    )
                    continue

                if video_standard == "":  # Only happens if no rows in grid
                    video_standard = file_video_data.encoding_info.video_standard

                if file_video_data.encoding_info.video_standard not in (
                    sys_consts.PAL,
                    sys_consts.NTSC,
                ):
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} :"
                        f" {sys_consts.SDELIM} Is Not PAL, NTSC \n"
                    )
                    continue

                if file_video_data.encoding_info.video_standard != video_standard:
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} ({file_video_data.encoding_info.video_standard}) :"
                        f" {sys_consts.SDELIM} Is Not {video_standard} The Project Video Standard  \n"
                    )
                    continue

                if file_video_data.encoding_info.video_tracks == 0:
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} :"
                        f" {sys_consts.SDELIM}No Video Track \n"
                    )
                    continue

                # Set default filter settings from database
                if (
                    self._db_settings.setting_exist(sys_consts.VF_NORMALISE)
                    and self._db_settings.setting_get(sys_consts.VF_NORMALISE)
                    is not None
                ):
                    file_video_data.video_file_settings.normalise = (
                        self._db_settings.setting_get(sys_consts.VF_NORMALISE)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_DENOISE)
                    and self._db_settings.setting_get(sys_consts.VF_DENOISE) is not None
                ):
                    file_video_data.video_file_settings.denoise = (
                        self._db_settings.setting_get(sys_consts.VF_DENOISE)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_WHITE_BALANCE)
                    and self._db_settings.setting_get(sys_consts.VF_WHITE_BALANCE)
                    is not None
                ):
                    file_video_data.video_file_settings.white_balance = (
                        self._db_settings.setting_get(sys_consts.VF_WHITE_BALANCE)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_SHARPEN)
                    and self._db_settings.setting_get(sys_consts.VF_SHARPEN) is not None
                ):
                    file_video_data.video_file_settings.sharpen = (
                        self._db_settings.setting_get(sys_consts.VF_SHARPEN)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_AUTO_LEVELS)
                    and self._db_settings.setting_get(sys_consts.VF_AUTO_LEVELS)
                    is not None
                ):
                    file_video_data.video_file_settings.auto_bright = (
                        self._db_settings.setting_get(sys_consts.VF_AUTO_LEVELS)
                    )

                toolbox = self._get_toolbox(file_video_data)

                duration = str(
                    datetime.timedelta(
                        seconds=file_video_data.encoding_info.video_duration
                    )
                ).split(".")[0]

                self._populate_grid_row(
                    file_grid=self._file_grid,
                    row_index=rows_loaded + row_index,
                    video_data=file_video_data,
                    duration=duration,
                )

                self._file_grid.row_widget_set(
                    row=rows_loaded + row_index,
                    col=self._file_grid.colindex_get("settings"),
                    widget=toolbox,
                )

                row_index += 1
        return rejected

    def _get_toolbox(self, video_user_data: Video_Data) -> qtg.HBoxContainer:
        """Generates a GUI toolbox for use in the grid.
        Args:
            video_user_data (Video_Data): The video data to use.

        Returns:
            qtg.HBoxContainer: The toolbox.
        """
        assert isinstance(
            video_user_data, Video_Data
        ), f"{video_user_data=}. Must be an instance of Video_Data"

        toolbox = qtg.HBoxContainer(
            height=1, width=3, align=qtg.Align.CENTER, margin_left=0, margin_right=0
        ).add_row(
            qtg.Button(
                tag="grid_button",
                height=1,
                width=1,
                callback=self.grid_events,
                user_data=video_user_data,
                icon=file_utils.App_Path("wrench.svg"),
                tooltip="Cut Video or Change Settings/Name",
            )
        )
        return toolbox

    def _populate_grid_row(
        self,
        file_grid: qtg.Grid,
        row_index: int,
        video_data: Video_Data,
        duration: str,
        italic: bool = False,
        tooltip: str = "",
    ) -> None:
        """Populates the grid row with the video information.

        Args:
            file_grid (qtg.Grid): The grid to populate.
            row_index (int): The index of the row to populate.
            video_data (File_Control.Video_Data): The video data to populate.
            duration (str): The duration of the video.
            italic (bool): Whether the text should be italic. Defaults to False.
            tooltip (str): The tooltip text. Defaults to "".
        """
        assert isinstance(
            file_grid, qtg.Grid
        ), f"{file_grid=}. Must be an instance of qtg.Grid"
        assert isinstance(
            video_data, Video_Data
        ), f"{video_data=}. Must be an instance of File_Control.Video_Data"
        assert isinstance(duration, str), f"{duration=}. Must be str."
        assert isinstance(italic, bool), f"{italic=}. Must be bool."
        assert isinstance(tooltip, str), f"{tooltip=}. Must be str."

        if tooltip.strip() != "":
            value_tooltip = tooltip
        else:
            value_tooltip = (
                f"{sys_consts.SDELIM}{video_data.video_path}{sys_consts.SDELIM}"
            )

        file_grid.value_set(
            value=(
                f"{video_data.video_file}{video_data.video_extension}"
                if self._display_filename
                else video_data.video_file_settings.button_title
            ),
            row=row_index,
            col=file_grid.colindex_get("video_file"),
            user_data=video_data,
            tooltip=value_tooltip,
            italic=italic,
        )

        file_grid.value_set(
            value=str(video_data.encoding_info.video_width),
            row=row_index,
            col=file_grid.colindex_get("width"),
            user_data=video_data,
        )

        file_grid.value_set(
            value=str(video_data.encoding_info.video_height),
            row=row_index,
            col=file_grid.colindex_get("height"),
            user_data=video_data,
        )

        encoder_str = (
            video_data.encoding_info.video_format
            + f":{video_data.encoding_info.video_scan_order}"
            if video_data.encoding_info.video_scan_order != ""
            else (
                f"{video_data.encoding_info.video_format} :"
                f" {video_data.encoding_info.video_scan_type}"
            )
        )

        file_grid.value_set(
            value=encoder_str,
            tooltip=encoder_str,
            row=row_index,
            col=file_grid.colindex_get("encoder"),
            user_data=video_data,
        )

        file_grid.value_set(
            value=duration,
            row=row_index,
            col=file_grid.colindex_get("duration"),
            user_data=video_data,
        )

        file_grid.value_set(
            value=video_data.encoding_info.video_standard,
            row=row_index,
            col=file_grid.colindex_get("standard"),
            user_data=video_data,
        )

        file_grid.value_set(
            value=(
                f"{video_data.video_file_settings.menu_group}"
                if video_data.video_file_settings.menu_group >= 0
                else ""
            ),
            row=row_index,
            col=file_grid.colindex_get("group"),
            user_data=video_data,
        )

        file_grid.userdata_set(
            row=row_index,
            col=file_grid.colindex_get("settings"),
            user_data=video_data,
        )

    def set_project_standard_duration(self, event: qtg.Action) -> None:
        """
        Sets the duration and video standard for the current project based on the selected
        input video files.

        Args:
            event (qtg.Action): The calling event.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )
        total_duration = 0.0
        self.project_video_standard = ""
        self._project_duration = ""
        self.dvd_percent_used = 0

        if file_grid.row_count > 0:
            for checked_item in file_grid.checkitems_get:
                checked_item: qtg.Grid_Item
                video_data: Video_Data = checked_item.user_data

                if (
                    video_data is None
                ):  # Most likely something broke on grid load and grid data is corrupt so skip
                    continue

                encoding_info = video_data.encoding_info

                total_duration += encoding_info.video_duration

            # If something broke on grid load and grid data is corrupt, then delete those rows
            while (
                file_grid.row_count > 0
                and file_grid.userdata_get(
                    row=0, col=file_grid.colindex_get("settings")
                )
                is None
            ):
                file_grid.row_delete(0)

            user_data = file_grid.userdata_get(
                row=0, col=file_grid.colindex_get("settings")
            )

            if user_data is not None:
                encoding_info = user_data.encoding_info
                self.project_video_standard = encoding_info.video_standard

            self._project_duration = str(
                datetime.timedelta(seconds=total_duration)
            ).split(".")[0]
            self.dvd_percent_used = dvdarch_utils.DVD_Percent_Used(
                total_duration=total_duration, pop_error_message=False
            )

        event.value_set(
            container_tag="dvd_properties",
            tag="project_video_standard",
            value=(
                f"{sys_consts.SDELIM}{self.project_video_standard}{sys_consts.SDELIM}"
            ),
        )

        event.value_set(
            container_tag="dvd_properties",
            tag="project_duration",
            value=f"{sys_consts.SDELIM}{self._project_duration}{sys_consts.SDELIM}",
        )
        event.value_set(
            container_tag="dvd_properties",
            tag="percent_of_dvd",
            value=f"{sys_consts.SDELIM}{self.dvd_percent_used}{sys_consts.SDELIM}",
        )

    def layout(self) -> qtg.VBoxContainer:
        """Generates the file handler ui

        Returns:
            qtg.VBoxContainer: The container that houses the file handler ui layout
        """

        button_container = qtg.HBoxContainer(
            tag="control_buttons", align=qtg.Align.BOTTOMRIGHT, margin_right=0
        ).add_row(
            qtg.HBoxContainer(
                text="Default Video Filters", tag="default_video_filters"
            ).add_row(
                qtg.Checkbox(
                    tag="normalise",
                    text="Normalise",
                    checked=False,
                    tooltip="Bring Out Shadow Details",
                    callback=self.event_handler,
                ),
                qtg.Checkbox(
                    tag="denoise",
                    text="Denoise",
                    checked=False,
                    tooltip="Lightly Reduce Video Noise",
                    callback=self.event_handler,
                ),
                qtg.Checkbox(
                    tag="white_balance",
                    text="White Balance",
                    checked=False,
                    tooltip="Fix White Balance Problems",
                    width=15,
                    callback=self.event_handler,
                ),
                qtg.Checkbox(
                    tag="sharpen",
                    text="Sharpen",
                    checked=False,
                    tooltip="Lightly Sharpen Video",
                    callback=self.event_handler,
                ),
                qtg.Checkbox(
                    tag="auto_levels",
                    text="Auto Levels",
                    checked=False,
                    tooltip="Improve Exposure",
                    callback=self.event_handler,
                ),
            ),
            qtg.Spacer(width=1),
            qtg.Button(
                icon=file_utils.App_Path("grid-2.svg"),
                tag="dvd_menu_configuration",
                callback=self.event_handler,
                tooltip="Configure The DVD Menu",
                width=2,
            ),
            qtg.Spacer(width=1),
            qtg.Button(
                icon=file_utils.App_Path("layer-group.svg"),
                tag="group_files",
                callback=self.event_handler,
                tooltip="Group Selected Video Files On The Same DVD Menu Page",
                width=2,
            ),
            qtg.Button(
                icon=file_utils.App_Path("object-ungroup.svg"),
                tag="ungroup_files",
                callback=self.event_handler,
                tooltip="Ungroup Selected Video Files",
                width=2,
            ),
            qtg.Spacer(width=2),
            qtg.Button(
                icon=file_utils.App_Path("film.svg"),
                tag="join_files",
                callback=self.event_handler,
                tooltip="Join/Transcode The Selected Files",
                width=2,
            ),
            qtg.Button(
                icon=file_utils.App_Path("text.svg"),
                tag="toggle_file_button_names",
                callback=self.event_handler,
                tooltip="Toggle Between Video File Names and Button Title Names",
                width=2,
            ),
            qtg.Spacer(width=1),
            qtg.Button(
                icon=file_utils.App_Path("arrow-up.svg"),
                tag="move_video_file_up",
                callback=self.event_handler,
                tooltip="Move This Video File Up!",
                width=2,
            ),
            qtg.Button(
                icon=file_utils.App_Path("arrow-down.svg"),
                tag="move_video_file_down",
                callback=self.event_handler,
                tooltip="Move This Video File Down!",
                width=2,
            ),
            qtg.Spacer(width=1),
            qtg.Button(
                icon=file_utils.App_Path("x.svg"),
                tag="remove_files",
                callback=self.event_handler,
                tooltip="Remove Selected Video Files From DVD Input Files",
                width=2,
            ),
            qtg.Button(
                icon=file_utils.App_Path("file-video.svg"),
                tag="select_files",
                # text="Select Files",
                callback=self.event_handler,
                tooltip="Select Video Files",
                width=2,
            ),
        )

        file_col_def = (
            qtg.Col_Def(
                label="",
                tag="settings",
                width=1,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Grp",
                tag="group",
                width=3,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Video File",
                tag="video_file",
                width=80,
                editable=False,
                checkable=True,
            ),
            qtg.Col_Def(
                label="Width",
                tag="width",
                width=6,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Height",
                tag="height",
                width=6,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Encoder",
                tag="encoder",
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="System",
                tag="standard",
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Duration",
                tag="duration",
                width=7,
                editable=False,
                checkable=False,
            ),
        )
        file_control_container = qtg.VBoxContainer(
            tag="video_file_controls", align=qtg.Align.TOPLEFT, margin_right=0
        )

        self._file_grid = qtg.Grid(
            tag="video_input_files",
            noselection=True,
            height=17,
            col_def=file_col_def,
            callback=self.grid_events,
        )

        file_control_container.add_row(
            qtg.Checkbox(
                text="Select All",
                tag="bulk_select",
                callback=self.event_handler,
                width=11,
            ),
            self._file_grid,
        )

        control_container = qtg.VBoxContainer(
            tag="control_container",
            text="DVD Input Files",
            align=qtg.Align.CENTER,
            margin_left=9,
        ).add_row(file_control_container, button_container)

        return control_container
