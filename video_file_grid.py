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

import dataclasses
import datetime
from typing import cast, Final

import platformdirs

import dvdarch_utils
import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups
import QTPYGUI.qtpygui as qtg
import QTPYGUI.sqldb as sqldb
import sys_consts
import QTPYGUI.utils as utils

from background_task_manager import Task_Manager
from dvd_menu_configuration import DVD_Menu_Config_Popup
from reencode_options_popup import Reencode_Options
from sys_config import (
    DVD_Archiver_Base,
    Get_Video_Editor_Folder,
    Video_Data,
    Get_Project_Files,
    Get_Project_Layout_Names,
    Remove_Project_Files,
)
from video_file_picker import Video_File_Picker_Popup

# These global functions and variables are only used by the hy the multi-thread task_manager process and exist by
# necessity as this seems the only way to communicate the variable values to rest of the dvdarchiver code
gi_task_error_code = -1
gi_thread_status = -1
gs_thread_error_message = ""
gs_task_error_message = ""
gs_thread_status = ""
gs_thread_message = ""
gs_thread_output = ""
gs_thread_task_name = ""

gb_task_errored = False
gi_tasks_completed = -1


def Run_Video_Trancode(arguments: tuple) -> tuple[int, str]:
    """This is a wrapper function used hy the multi-thread task_manager to run the Execute_Check_Output process

    Args:
        arguments (tuple): Defines video cut parameters

    Returns:
        tuple[int, str]:
        - arg1 1: ok, -1: fail
        - arg2: error message or "" if ok
    """
    global gi_task_error_code
    global gs_task_error_message

    if not utils.Is_Complied():
        print(f"DBG {arguments=}")

    transcode_container = arguments[0]
    video_data: Video_Data = arguments[1]
    operation_action: str = arguments[2]
    transcode_folder: str = arguments[3]

    gi_task_error_code, gs_task_error_message = dvdarch_utils.Transcode_DV(
        input_file=video_data.video_path,
        frame_rate=video_data.encoding_info.video_frame_rate,
        output_folder=transcode_folder,
        width=video_data.encoding_info.video_width,
        height=video_data.encoding_info.video_height,
    )

    if not utils.Is_Complied():
        print(f"DBG Run_Video Transcode {gi_task_error_code=} {gs_task_error_message=}")

    return gi_task_error_code, gs_task_error_message


@dataclasses.dataclass(slots=True)
class Video_File_Grid(DVD_Archiver_Base):
    """This class implements the file handling of the Black DVD Archiver ui"""

    parent: DVD_Archiver_Base

    # Private instance variables
    _common_words: list[str] = dataclasses.field(default_factory=list)
    _display_filename: bool = True
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _db_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)
    _dvd_percent_used: int = 0  # TODO Make A selection of DVD5 and DVD9
    _file_grid: qtg.Grid = None
    _project_duration: str = ""
    _project_name: str = ""
    _project_video_standard: str = ""  # PAL or NTSC
    _row_checked: dict[int, bool] = dataclasses.field(default_factory=dict)
    _shutdown: bool = False
    _task_dict: dict = dataclasses.field(default_factory=dict)

    # Constants
    VIDEO_FILE_COL: Final[str] = "video_file"
    WIDTH_COL: Final[str] = "width"
    HEIGHT_COL: Final[str] = "height"
    ENCODER_COL: Final[str] = "encoder"
    DURATION_COL: Final[str] = "duration"
    STANDARD_COL: Final[str] = "standard"
    GROUP_COL: Final[str] = "group"
    SETTINGS_COL: Final[str] = "settings"

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

    def notification_call_back(
        self, status: int, message: str, output: str, name
    ) -> None:
        """
        The notification_call_back function is called by the multi-thread task_manager when a task completes


        Args:
            status: int: Determine if the task was successful or not
            message: str: Pass a message to the user
            output: str: Return the output of the task
            name: Identify the task that has completed

        """
        global gs_thread_status
        global gs_thread_message
        global gs_thread_output
        global gs_thread_task_name

        global gi_tasks_completed
        global gb_task_errored

        gs_thread_status = status
        gs_thread_message = "" if message is None else message
        gs_thread_output = "" if gs_thread_output is None else gs_thread_output
        gs_thread_task_name = name

        operation = gs_thread_task_name.split("_")[0]
        vd_id = int(gs_thread_task_name.split("_")[-1])
        print(f"DBG notification_call_back {vd_id=} {operation=}")
        print(f"DBG {self._task_dict[vd_id]=}")
        if status == -1:
            gb_task_errored = True
        else:
            gi_tasks_completed += 1

            if operation == "transcode":
                video_data: Video_Data = self._task_dict[vd_id][0]
                transcode_folder: str = self._task_dict[vd_id][1]

                for row in range(self._file_grid.row_count):
                    user_data: Video_Data = self._file_grid.userdata_get(
                        row=row, col=self._file_grid.colindex_get(self.VIDEO_FILE_COL)
                    )

                    if user_data and user_data.vd_id == vd_id:
                        result, message = self._processed_trimmed(
                            vd_id,
                            transcode_folder,
                            video_data.video_file_settings.button_title,
                        )
                        print(f"DBG {result=} {message=}")
                        if result == -1:
                            gi_thread_status = -1
                            gs_task_error_message = message
                            gb_task_errored = True

        self._task_dict.pop(vd_id)
        if not utils.Is_Complied():
            print(
                "DBG notification_call_back"
                f" {gs_thread_status=} {gs_thread_message=} {gs_thread_output=} {gs_thread_task_name=}"
            )

        return None

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
        assert isinstance(self.parent, DVD_Archiver_Base), (
            f"{self.parent=}. Must be an instance of DVD_Archiver_Base"
        )

        self._background_task_manager: Task_Manager = Task_Manager()
        self._background_task_manager.start()

        if self._db_settings.setting_exist(sys_consts.LATEST_PROJECT_DBK):
            self.project_name = self._db_settings.setting_get(
                sys_consts.LATEST_PROJECT_DBK
            )
        else:
            self.project_name = sys_consts.DEFAULT_PROJECT_NAME_DBK
            self._db_settings.setting_set(
                sys_consts.LATEST_PROJECT_DBK, self.project_name
            )

        return None

    def grid_events(self, event: qtg.Action) -> None:
        """Process Grid Events
        Args:
            event (Action): Action
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        if event.event == qtg.Sys_Events.CLICKED:
            col_index = self._file_grid.colindex_get(self.VIDEO_FILE_COL)

            if event.tag.startswith("grid_button"):
                row_unique_id = int(
                    event.container_tag.split("|")[0]
                )  # Grid button container tag has the row_id embedded as the 1st element and delimitered by |
                row = self._file_grid.row_from_item_id(row_unique_id)
                self._edit_video(event)
                self._file_grid.select_col(row, col_index)
            elif event.value.row >= 0 and event.value.col >= 0:
                self.set_project_standard_duration(event)
                row_checked = self._row_checked.get(event.value.row, False)

                if row_checked:
                    self._file_grid.checkitemrow_set(
                        row=event.value.row, col=col_index, checked=False
                    )
                    self._row_checked[event.value.row] = False
                    self._file_grid.select_col(event.value.row, col_index)
                else:
                    self._row_checked[event.value.row] = True
                    self._file_grid.select_col(event.value.row, col_index)
                    self._file_grid.checkitemrow_set(
                        row=event.value.row, col=col_index, checked=True
                    )

        return None

    def process_edited_video_files(self, video_file_input: list[Video_Data]) -> None:
        """
        Called in DVD Archiver to handle the edited video files and place in the file list grid

        Args:
            video_file_input (list[Video_Data]): THhe edited video file list
        """

        #### Helper Functions
        def _select_row(desired_file_path: str) -> None:
            """
            Selects the row and column in the file grid for the given video file path.

            Args:
                desired_file_path (str): The video file name to find in the grid and select.

            Returns:
                None

            """
            assert (
                isinstance(desired_file_path, str) and desired_file_path.strip() != ""
            ), f"{desired_file_path=}. Must be str"

            col_index = self._file_grid.colindex_get(self.VIDEO_FILE_COL)

            for row in range(self._file_grid.row_count):
                user_data: Video_Data = self._file_grid.userdata_get(row=row, col=0)

                if user_data and desired_file_path == user_data.video_path:
                    self._file_grid.select_col(row, col_index)
                    self._file_grid.guiwidget_get.setFocus()

                    break
            return None

        #### Main
        assert isinstance(video_file_input, list), f"{video_file_input=}. Must be list"
        assert all(
            isinstance(video_file, Video_Data) for video_file in video_file_input
        ), f"{video_file_input=}. Must be list of Video_Data"

        if (
            len(video_file_input) == 1
        ):  # Original, only user entered file title text might have changed
            self._processed_trimmed(
                video_file_input[0].vd_id,
                video_file_input[0].video_path,
                video_file_input[0].video_file_settings.button_title,
            )

            _select_row(video_file_input[0].video_path)
        elif (
            len(video_file_input) == 2
        ):  # Original & one edited file (cut/assemble). The edited file replaces the orginal
            self._processed_trimmed(
                video_file_input[0].vd_id,
                video_file_input[1].video_path,
                video_file_input[0].video_file_settings.button_title,
            )

            _select_row(video_file_input[1].video_path)
        elif (
            len(video_file_input) > 2
        ):  # Original and multiple edited files that replace the original
            # TODO Make user configurable perhaps
            self._delete_file_from_grid(video_file_input[0].vd_id)

            # Insert Assembled Children Files
            rejected = self._insert_files_into_grid(
                selected_files=[
                    video_file_data for video_file_data in video_file_input[1:]
                ],
                debug=False,
            )

            if rejected:
                popups.PopError(title="Video File Error...", message=rejected).show()

        return None

    def _edit_video(self, event: qtg.Action) -> None:
        """
        Edits a video file.
        Args:
            event (qtg.Action): The event that triggered the video edit.
        """

        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        video_editor_folder = Get_Video_Editor_Folder()

        if not video_editor_folder:
            return None

        col_index = self._file_grid.colindex_get(self.VIDEO_FILE_COL)
        row_unique_id = int(
            event.container_tag.split("|")[0]
        )  # Grid button container tag has the row_id embedded as the 1st element and delimitered by |
        row = self._file_grid.row_from_item_id(row_unique_id)

        if row == -1:
            popups.PopError(
                title="Edit Video Error...",
                message="Failed To Get Edit Row..",
            ).show()

            return None

        user_data: Video_Data = self._file_grid.userdata_get(row=row, col=col_index)
        video_file_input: list[Video_Data] = [user_data]

        self._aspect_ratio = video_file_input[0].encoding_info.video_ar
        self._frame_width = video_file_input[0].encoding_info.video_width
        self._frame_height = video_file_input[0].encoding_info.video_height
        self._frame_rate = video_file_input[0].encoding_info.video_frame_rate
        self._frame_count = video_file_input[0].encoding_info.video_frame_count

        event.tag = "video_editor"
        event.value = video_file_input
        self.parent.event_handler(event)  # Processed in DVD Archiver!
        self._file_grid.select_col(row, col_index)

        return None

    def check_file(self, vd_id: int, checked: bool) -> None:
        """Checks the file (identified by vd_id) in the file grid.

        Args:
            vd_id (int): The Video_Data ID of the source file that is to be checked.
            checked (bool): True Checked, False Unchecked
        """
        assert isinstance(vd_id, int), f"{vd_id=}. Must be an int"
        assert isinstance(checked, bool), f"{checked=}. Must be a bool"

        col_index = self._file_grid.colindex_get(self.VIDEO_FILE_COL)

        for row in range(self._file_grid.row_count):
            user_data: Video_Data = self._file_grid.userdata_get(row=row, col=col_index)

            if user_data and user_data.vd_id == vd_id:
                self._file_grid.checkitemrow_set(
                    row=row, col=col_index, checked=checked
                )
            self._row_checked[row] = checked
            self._file_grid.select_col(row, col_index)

        return None

    def _delete_file_from_grid(
        self,
        vd_id: int,
    ) -> None:
        """Deletes the source file from the file grid.
        Args:
            vd_id (int): The Video_Data ID of the source file that is to be deleted.
        """
        assert isinstance(self._file_grid, qtg.Grid), (
            f"{self._file_grid}. Must be a Grid instance"
        )

        for row in range(self._file_grid.row_count):
            user_data: Video_Data = self._file_grid.userdata_get(
                row=row, col=self._file_grid.colindex_get(self.VIDEO_FILE_COL)
            )

            if user_data and user_data.vd_id == vd_id:
                self._file_grid.row_delete(row)

        return None

    def _processed_trimmed(
        self,
        vd_id: int,
        updated_file: str,
        button_title: str = "",
    ) -> tuple[int, str]:
        """
        Updates the file_grid with the trimmed_file detail, after finding the corresponding grid entry.
        Args:
            vd_id (int): The Video_Data ID of the source file.
            updated_file (str): The trimmed file to update the grid details with.
            button_title (str): The button title to update the grid details with.

        Returns:
            int: 1 if successful, -1 if failed
            str: error message or "" if ok
        """
        assert isinstance(vd_id, int) and vd_id >= 0, f"{vd_id=}. Must be an int >= 0"
        assert isinstance(updated_file, str) and updated_file.strip() != "", (
            f"{updated_file=}. Must be non-empty str"
        )
        assert isinstance(button_title, str) and button_title.strip() != "", (
            f"{button_title=}. Must be non-empty str"
        )

        file_handler = file_utils.File()

        (
            trimmed_folder,
            trimmed_file_name,
            trimmed_extension,
        ) = file_handler.split_file_path(updated_file)

        col_index = self._file_grid.colindex_get(self.VIDEO_FILE_COL)

        # Scan looking for a source of trimmed file
        for row in range(self._file_grid.row_count):
            user_data: Video_Data = self._file_grid.userdata_get(row=row, col=col_index)

            if user_data and vd_id == user_data.vd_id:
                encoding_info = dvdarch_utils.Get_File_Encoding_Info(updated_file)
                if encoding_info.error:  # Error Occurred
                    return -1, encoding_info.error

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
                    vd_id=user_data.vd_id,
                )

                duration = str(
                    datetime.timedelta(
                        seconds=updated_user_data.encoding_info.video_duration
                    )
                ).split(".")[0]

                self._populate_grid_row(
                    row_index=row,
                    video_data=updated_user_data,
                    duration=duration,
                )

                for col in range(0, self._file_grid.col_count):
                    self._file_grid.userdata_set(
                        row=row, col=col, user_data=updated_user_data
                    )

                break  # Only one trimmed file
        else:
            return -1, f"Failed To Find {vd_id} In Grid. {updated_file=}"
        return 1, ""

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  application events
        Args:
            event (Action): The triggering event
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        match event.event:
            case qtg.Sys_Events.APPINIT:
                if self._db_settings.setting_exist(sys_consts.LATEST_PROJECT_DBK):
                    self.project_name = self._db_settings.setting_get(
                        sys_consts.LATEST_PROJECT_DBK
                    )
                else:
                    self.project_name = sys_consts.DEFAULT_PROJECT_NAME_DBK

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
                                sys_consts.LATEST_PROJECT_DBK, project_name
                            )

                    else:  # Project might be changed
                        self._db_settings.setting_set(
                            sys_consts.LATEST_PROJECT_DBK, self.project_name
                        )
                self._save_grid(event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "bulk_select":
                        self._file_grid.checkitems_all(
                            checked=event.value, col_tag=self.VIDEO_FILE_COL
                        )

                        for row_index in range(self._file_grid.row_count):
                            self._row_checked[row_index] = event.value

                        self.set_project_standard_duration(event)
                    case "normalise":
                        self._db_settings.setting_set(
                            sys_consts.VF_NORMALISE_DBK, event.value
                        )
                    case "denoise":
                        self._db_settings.setting_set(
                            sys_consts.VF_DENOISE_DBK, event.value
                        )
                    case "white_balance":
                        self._db_settings.setting_set(
                            sys_consts.VF_WHITE_BALANCE_DBK, event.value
                        )
                    case "sharpen":
                        self._db_settings.setting_set(
                            sys_consts.VF_SHARPEN_DBK, event.value
                        )
                    case "auto_levels":
                        self._db_settings.setting_set(
                            sys_consts.VF_AUTO_LEVELS_DBK, event.value
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
                        self._db_settings.setting_set(
                            sys_consts.DISPLAY_FILE_NAMES_DBK, self._display_filename
                        )

                        if self._display_filename:
                            self._display_filename = False
                        else:
                            self._display_filename = True

                        self._toggle_file_button_names(event)
                    case "ungroup_files":
                        self._ungroup_files(event)

        return None

    def project_changed(
        self, event: qtg.Action, project_name: str, save_existing: bool
    ) -> None:
        """Handles the change of a project

        Args:
            event (qtg.Action): The triggering event
            project_name (str): The name of the project
            save_existing (bool): If True saves the existing project, else does not
        """
        assert isinstance(project_name, str) and project_name.strip() != "", (
            f"{project_name=}. Must be non-empty str"
        )

        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        if save_existing and self._file_grid.changed:
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

        self._db_settings.setting_set(sys_consts.LATEST_PROJECT_DBK, self.project_name)

        if self.project_name in project_names:  # Existing Project
            self._file_grid.clear()
            self._load_grid(event)
        else:
            self._file_grid.clear()

        self._save_grid(event)

        event.event = qtg.Sys_Events.CUSTOM
        event.container_tag = ""
        event.tag = "project_changed"
        event.value = self.project_name
        self.parent.event_handler(event=event)

        return None

    def postinit_handler(self, event: qtg.Action) -> None:
        """
        The postinit_handler method is called after the GUI has been created.
        It is used to set default values for widgets

        Args:
            event (qtg.Action) : The triggering event

        Returns:
            None

        """

        self._load_grid(event)

        if self._db_settings.setting_exist(sys_consts.VF_NORMALISE_DBK):
            event.value_set(
                container_tag="default_video_filters",
                tag="normalise",
                value=self._db_settings.setting_get(sys_consts.VF_NORMALISE_DBK),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="normalise",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_DENOISE_DBK):
            event.value_set(
                container_tag="default_video_filters",
                tag="denoise",
                value=self._db_settings.setting_get(sys_consts.VF_DENOISE_DBK),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="denoise",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_WHITE_BALANCE_DBK):
            event.value_set(
                container_tag="default_video_filters",
                tag="white_balance",
                value=self._db_settings.setting_get(sys_consts.VF_WHITE_BALANCE_DBK),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="white_balance",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_SHARPEN_DBK):
            event.value_set(
                container_tag="default_video_filters",
                tag="sharpen",
                value=self._db_settings.setting_get(sys_consts.VF_SHARPEN_DBK),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="sharpen",
                value=False,
            )

        if self._db_settings.setting_exist(sys_consts.VF_AUTO_LEVELS_DBK):
            event.value_set(
                container_tag="default_video_filters",
                tag="auto_levels",
                value=self._db_settings.setting_get(sys_consts.VF_AUTO_LEVELS_DBK),
            )
        else:
            event.value_set(
                container_tag="default_video_filters",
                tag="auto_levels",
                value=False,
            )

        self._display_filename = True
        if self._db_settings.setting_exist(sys_consts.DISPLAY_FILE_NAMES_DBK):
            self._display_filename = cast(
                bool, self._db_settings.setting_get(sys_consts.DISPLAY_FILE_NAMES_DBK)
            )

        # Hot wire to display title names or file names as required
        event.event = qtg.Sys_Events.CLICKED
        event.tag = "toggle_file_button_names"
        self.event_handler(event)

        return None

    def _join_files(self, event: qtg.Action) -> None:
        """
        Joins selected files. The joined files are concatenated onto the first selected file

        Args:
            event (qtg.Action): The event triggering the ungrouping.

        Returns:
            None
        """
        # HD Camcorder MTS files gave me no end of trouble, so have to reencode to mezzanine
        # The same applies to the mod/tod files which are proprietary mpg formats
        proprietary_extensions = ("mod", "tod")  # , "mts")

        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        message = ""

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
            video_editor_folder, sys_consts.EDIT_FOLDER_NAME
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
            sys_consts.TRANSCODE_FOLDER_NAME,
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
        checked_items = self._file_grid.checkitems_get

        if not checked_items:
            popups.PopError(
                title="No Files Selected",
                message="Please Select Files To Join/Transcode",
            ).show()
            return None

        copy_method = ""
        dv_option = False
        stream_copy = False
        join_options = {}
        file_extension = checked_items[0].user_data.video_extension.lower().strip(".")

        if all(
            item.user_data.encoding_info.video_height
            in (sys_consts.PAL_SPECS.height_43, sys_consts.NTSC_SPECS.height_43)
            and item.user_data.encoding_info.video_width
            in (sys_consts.PAL_SPECS.width_43, sys_consts.NTSC_SPECS.width_43)
            for item in checked_items
        ):
            dv_option = True

        if file_extension not in proprietary_extensions and all(
            item.user_data.video_path.lower().endswith(file_extension)
            for item in checked_items
        ):  # All files of the same type can stream copy
            stream_copy = True

        reencode_options = {
            "Make Edit File - Slow   :: Transcode File Into An Intermediate Edit File Format Suitable For Editing": "reencode_edit"
        }
        if dv_option:
            reencode_options.update({
                "Re-Encode DV   - Slow  :: Transcode File Into The Common DV Format. Files Are Large": "reencode_dv"
            })

        reencode_options.update({
            "Re-Encode H264 - Slower :: Transcode File Into The Common H264 Format": "reencode_h264",
            "Re-Encode H265 - Slowest ::Transcode File Into The Common H264 Format": "reencode_h265",
        })

        if len(checked_items) > 1:  # More than one file, so can transcode or join
            if stream_copy:
                join_options.update({
                    "Stream Copy            - Fast :: Use Where There Is No Problem Joining Files ": "stream_copy"
                })

            if dv_option:
                join_options.update({
                    "Re-Encode As DV File   - Very Large :: Use Where There Is A Problem Joining Files & The Joined "
                    "Files Needs To Be Edited   ": "transjoin_dv"
                })

            join_options.update({
                "Reencode As Edit File  - Slow       :: Use Where There Is A Problem Joining Files & The Joined File Needs "
                "To Be Edited": "transjoin_edit",
                "Re-Encode As H264 File - Slower     ::  Use To Join Files Into The Common H264 Format": "transjoin_h264",
                "Re-Encode As H265 File - Slowest    ::  Use To Join Files Into The Newer H265 Format": "transjoin_h265",
            })

        result = Reencode_Options(
            transcode_options=reencode_options,
            join_options=join_options,
        ).show()

        if result.strip() == "":
            return None

        operation_option = result.split("|")[0]
        operation_action = result.split("|")[1]

        concatenating_files = []
        video_file_data = []
        removed_files = []
        output_file = ""
        # vd_id = -1
        # button_title = ""
        transcode_format = "mp4"  # TODO Make user selectable - mpg, mp4

        for item in checked_items:
            item: qtg.Grid_Item
            video_data: Video_Data = item.user_data

            if not output_file:  # Happens on first iteration
                # vd_id = video_data.vd_id
                # button_title = video_data.video_file_settings.button_title
                output_file = file_handler.file_join(
                    dir_path=transcode_folder,
                    file_name=f"{video_data.video_file}_joined",
                    ext=(
                        transcode_format
                        if copy_method == "transcode_copy"
                        else video_data.video_extension
                    ),
                )
            else:
                removed_files.append(video_data)

            concatenating_files.append(video_data.video_path)
            video_file_data.append(video_data)

        transcoded_files = []

        if concatenating_files and output_file:
            with qtg.sys_cursor(qtg.Cursor.hourglass):
                match operation_option:
                    case "transcode":
                        for video_data in video_file_data:
                            match operation_action:
                                case "reencode_edit":
                                    transcode_format = "mkv"  # "avi" if mjpeg arg is true for Transcode_Mezzanine

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

                                    if result == -1:
                                        return None
                                case "reencode_dv":
                                    # Example on how to transcode in background TODO Implement this
                                    # transcode_format = "avi"
                                    # task_tuple = (
                                    #     video_data.vd_id,
                                    #     (
                                    #         "avi",
                                    #         video_data,
                                    #         operation_action,
                                    #         transcode_folder,
                                    #     ),
                                    # )
                                    #
                                    # self._background_task_manager.add_task(
                                    #     name=f"transcode_video_{task_tuple[0]}",
                                    #     method=Run_Video_Trancode,
                                    #     arguments=(task_tuple[1],),
                                    #     callback=self.notification_call_back,
                                    # )
                                    # self._task_dict[video_data.vd_id] = (
                                    #     video_data,
                                    #     transcode_file,
                                    # )
                                    transcode_format = "avi"

                                    result, message = dvdarch_utils.Transcode_DV(
                                        input_file=video_data.video_path,
                                        frame_rate=video_data.encoding_info.video_frame_rate,
                                        output_folder=transcode_folder,
                                        width=video_data.encoding_info.video_width,
                                        height=video_data.encoding_info.video_height,
                                    )
                                case "reencode_h264":
                                    transcode_format = "mp4"
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
                                case "reencode_h265":
                                    transcode_format = "mp4"
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

                            if result == -1:
                                break

                            transcoded_files.append((
                                video_data.vd_id,
                                video_data.video_file_settings.button_title,
                                file_handler.file_join(
                                    dir_path=transcode_folder,
                                    file_name=video_data.video_file,
                                    ext=transcode_format,
                                ),
                            ))

                        if transcoded_files:
                            for (
                                vd_id,
                                button_title,
                                transcoded_file,
                            ) in transcoded_files:
                                result, message = self._processed_trimmed(
                                    vd_id=vd_id,
                                    updated_file=transcoded_file,
                                    button_title=button_title,
                                )

                    case "join":
                        video_data = checked_items[0].user_data

                        match operation_action:
                            case "stream_copy":  # No transcoding
                                transcode_format = ""
                            case "transjoin_dv":
                                transcode_format = "dv"  # lives in an avi file
                            case "transjoin_edit":
                                transcode_format = "mjpeg"
                            case "transjoin_h264":
                                transcode_format = "h264"
                            case "transjoin_h265":
                                transcode_format = "h265"

                        if (
                            video_data.video_extension.strip(".").lower()
                            in proprietary_extensions
                        ):
                            file_extension = "avi"
                        elif video_data.video_extension.strip(".").lower() in "mts":
                            file_extension = "mkv"

                        output_file = file_handler.file_join(
                            dir_path=transcode_folder,
                            file_name=f"{video_data.video_file}_joined",
                            ext=file_extension,
                        )

                        print(concatenating_files)
                        result, message, _ = dvdarch_utils.Concatenate_Videos(
                            temp_files=concatenating_files,
                            output_file=output_file,
                            transcode_format=transcode_format,
                            debug=True,
                        )

                        if result == 1:
                            video_data = checked_items[0].user_data
                            vd_id = video_data.vd_id
                            button_title = video_data.video_file_settings.button_title

                            result, message = self._processed_trimmed(
                                vd_id=vd_id,
                                updated_file=output_file,
                                button_title=button_title,
                            )

                            for item in reversed(checked_items):
                                if item.user_data and vd_id != item.user_data.vd_id:
                                    self._file_grid.row_delete(item.row_index)

        if result == -1:
            popups.PopError(
                title="Error Joining Files..."
                if operation_option == "join"
                else "Error Transcoding Files...",
                message=f" Failed!\n{sys_consts.SDELIM}{message}{sys_consts.SDELIM}",
            ).show()

            return None
        else:
            # If all good message has the output file name. A reencode concat will have a different extension. A
            # stream concat will have the same extension as the inpt file. This will be the only delta
            output_file = message

        return None

    def _remove_files(self, event: qtg.Action) -> None:
        """Removes the selected files

        Args:
            event (qtg.Action) : Calling event
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        if (
            self._file_grid.row_count > 0
            and self._file_grid.checkitems_get
            and popups.PopYesNo(
                title="Remove Selected...",
                message="Remove The Selected Files?",
            ).show()
            == "yes"
        ):
            for item in reversed(self._file_grid.checkitems_get):
                item: qtg.Grid_Item
                self._file_grid.row_delete(item.row_index)
            self._save_grid(event)

        self.set_project_standard_duration(event)

        if event.value_get(container_tag="video_file_controls", tag="bulk_select"):
            event.value_set(
                container_tag="video_file_controls", tag="bulk_select", value=False
            )

        return None

    def _move_video_file(self, event: qtg.Action, up: bool) -> None:
        """
        Move the selected video file up or down in the file list grid.

        Args:
            event (qtg.Action): Calling event
            up (bool): True to move the video file up, False to move it down.
        """

        assert isinstance(up, bool), f"{up=}. Must be bool"

        checked_items: tuple[qtg.Grid_Item] = (
            self._file_grid.checkitems_get
            if up
            else tuple(reversed(self._file_grid.checkitems_get))
        )

        assert all(isinstance(item, qtg.Grid_Item) for item in checked_items), (
            f"{checked_items=}. Must be a list of 'qtg.Grid_Item_Tuple'"
        )

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
                if checked_item.row_index == self._file_grid.row_count - 1:
                    break

            self._file_grid.checkitemrow_set(
                False,
                checked_item.row_index,
                self._file_grid.colindex_get(self.VIDEO_FILE_COL),
            )
            self._file_grid.select_row(checked_item.row_index)

            current_row = checked_item.row_index
            group_disp = self._file_grid.value_get(
                current_row, self._file_grid.colindex_get(self.GROUP_COL)
            )
            group_id = int(group_disp) if group_disp else -1
            current_video_data: Video_Data = self._file_grid.userdata_get(
                current_row, self._file_grid.colindex_get(self.GROUP_COL)
            )

            if up and current_row > 1:
                # look backward for group id to use if no group id is found in the current row
                look_backward_group_id = ""
                if current_row > 2:
                    look_backward_group_id = self._file_grid.value_get(
                        current_row - 2, self._file_grid.colindex_get(self.GROUP_COL)
                    )

                prev_group_id = self._file_grid.value_get(
                    current_row - 1, self._file_grid.colindex_get(self.GROUP_COL)
                )
                if not prev_group_id and look_backward_group_id:
                    prev_group_id = look_backward_group_id

                if prev_group_id:
                    prev_video_data: Video_Data = self._file_grid.userdata_get(
                        current_row - 1, self._file_grid.colindex_get(self.GROUP_COL)
                    )
                    group_id = int(prev_group_id)
                    current_video_data.video_file_settings.menu_group = (
                        prev_video_data.video_file_settings.menu_group
                    )
                else:
                    group_id = -1

            elif not up and current_row < self._file_grid.row_count - 1:
                # look ahead for group id to use if no group id is found in the current row
                look_forward_group_id = ""
                if current_row < self._file_grid.row_count - 2:
                    look_forward_group_id = self._file_grid.value_get(
                        current_row + 2, self._file_grid.colindex_get(self.GROUP_COL)
                    )

                next_group_id = self._file_grid.value_get(
                    current_row + 1, self._file_grid.colindex_get(self.GROUP_COL)
                )
                if not next_group_id and look_forward_group_id:
                    next_group_id = look_forward_group_id

                if next_group_id:
                    next_video_data: Video_Data = self._file_grid.userdata_get(
                        current_row + 1, self._file_grid.colindex_get(self.GROUP_COL)
                    )
                    group_id = int(next_group_id)
                    current_video_data.video_file_settings.menu_group = (
                        next_video_data.video_file_settings.menu_group
                    )
                else:
                    group_id = -1

            self._file_grid.value_set(
                row=current_row,
                col=self._file_grid.colindex_get(self.GROUP_COL),
                value=str(group_id) if group_id >= 0 else "",
                user_data=current_video_data,
            )

            for col in range(self._file_grid.col_count):
                self._file_grid.userdata_set(
                    row=current_row,
                    col=col,
                    user_data=current_video_data,
                )

            new_row = (
                self._file_grid.move_row_up(current_row)
                if up
                else self._file_grid.move_row_down(current_row)
            )

            if new_row >= 0:
                self._file_grid.checkitemrow_set(
                    True, new_row, self._file_grid.colindex_get(self.VIDEO_FILE_COL)
                )
                self._file_grid.select_col(
                    new_row, self._file_grid.colindex_get(self.VIDEO_FILE_COL)
                )
            else:
                self._file_grid.checkitemrow_set(
                    True,
                    checked_items[0].row_index,
                    self._file_grid.colindex_get(self.VIDEO_FILE_COL),
                )
                self._file_grid.select_col(
                    checked_items[0].row_index,
                    self._file_grid.colindex_get(self.VIDEO_FILE_COL),
                )

        return None

    def _load_grid(self, event: qtg.Action) -> None:
        """Loads the grid from the database

        Args:
            event (qtg.Action): Calling event
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        file_handler = file_utils.File()

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
                    or shelf_item[self.DURATION_COL] is None
                ):  # This is an error and should not happen
                    continue

                if not file_handler.file_exists(shelf_item["video_data"].video_path):
                    removed_files.append(shelf_item["video_data"].video_path)
                    continue

                video_data: Video_Data = shelf_item["video_data"]
                duration: str = shelf_item[self.DURATION_COL]

                if video_data is None or duration is None:
                    continue

                self._populate_grid_row(
                    row_index=grid_row,
                    video_data=video_data,
                    duration=duration,
                    italic=True
                    if "dvdmenu" in shelf_item
                    else False,  # Item comes from a dvd layout button
                    tooltip=f"{sys_consts.SDELIM} {shelf_item['dvdmenu']} {video_data.video_path}{sys_consts.SDELIM}"
                    if "dvdmenu" in shelf_item
                    else "",
                )
                toolbox = self._get_toolbox(shelf_item["video_data"])
                self._file_grid.row_widget_set(
                    row=grid_row,
                    col=self._file_grid.colindex_get(self.SETTINGS_COL),
                    widget=toolbox,
                )

                grid_row += 1

            self._file_grid.row_scroll_to(0)
            self.set_project_standard_duration(event)

            # Cleanup pass to ensure correctness of grid
            for check_row_index in reversed(range(self._file_grid.row_count)):
                grid_video_data: Video_Data = self._file_grid.userdata_get(
                    row=check_row_index,
                    col=self._file_grid.colindex_get(self.VIDEO_FILE_COL),
                )

                # If grid_video_data is None, something went off the rails badly
                if grid_video_data is None:
                    self._file_grid.row_delete(check_row_index)
                    continue

                if check_row_index > 0:
                    prior_grid_video_data: Video_Data = self._file_grid.userdata_get(
                        row=check_row_index - 1,
                        col=self._file_grid.colindex_get(self.VIDEO_FILE_COL),
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
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        error_title: Final[str] = "File Grid Save Error..."

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
            for row in range(self._file_grid.row_count):
                if (
                    self._file_grid.userdata_get(row=row, col=0) is None
                    or self._file_grid.colindex_get(self.DURATION_COL) is None
                ):
                    continue  # This is an error and should not happen

                row_data.append({
                    "row_index": row,
                    "video_data": self._file_grid.userdata_get(row=row, col=0),
                    "duration": self._file_grid.value_get(
                        row=row, col=self._file_grid.colindex_get(self.DURATION_COL)
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

        for row_index in range(self._file_grid.row_count):
            grid_video_data: Video_Data = self._file_grid.userdata_get(
                row=row_index, col=self._file_grid.colindex_get(self.VIDEO_FILE_COL)
            )

            if grid_video_data is None:  # Error loading grid
                continue

            if grid_video_data.video_file_settings.button_title.strip() == "":
                grid_video_data.video_file_settings.button_title = (
                    file_handler.extract_title(grid_video_data.video_file)
                )

            if self._display_filename:
                self._file_grid.value_set(
                    row=row_index,
                    col=self._file_grid.colindex_get(self.VIDEO_FILE_COL),
                    value=(
                        f"{grid_video_data.video_file}{grid_video_data.video_extension}"
                    ),
                    user_data=grid_video_data,
                )
            else:
                self._file_grid.value_set(
                    row=row_index,
                    col=self._file_grid.colindex_get(self.VIDEO_FILE_COL),
                    value=grid_video_data.video_file_settings.button_title,
                    user_data=grid_video_data,
                )

            for col in range(self._file_grid.col_count):
                self._file_grid.userdata_set(
                    row=row_index, col=col, user_data=grid_video_data
                )

        return None

    def _get_max_group_num(self) -> int:
        """
        Scan all items in the file_grid and return the maximum menu_group number.

        Args:

        Returns:
            int: The maximum menu_group number.
        """
        assert isinstance(self._file_grid, qtg.Grid), (
            f"{self._file_grid=}. Must be an instance of qtg.Grid"
        )

        max_group_num = 0

        for row in range(self._file_grid.row_count):
            video_item = self._file_grid.userdata_get(
                row=row, col=self._file_grid.colindex_get(self.VIDEO_FILE_COL)
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

        checked_items = self._file_grid.checkitems_get

        if not checked_items:
            popups.PopError(
                title="No Files Selected", message="Please Select Files To Group"
            ).show()
            return None

        grouped = []
        ungrouped = []
        group_id = -1
        group_aspect_ratio = ""  # All group members must be the same aspect ratio
        max_group_val = self._get_max_group_num()

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
            self._file_grid.value_set(
                row=item.row_index,
                col=self._file_grid.colindex_get(self.GROUP_COL),
                value=f"{group_value}",
                user_data=video_item,
            )
        self._file_grid.checkitems_all(checked=False)
        for row in range(self._file_grid.row_count):
            self._row_checked[row] = False
        event.value_set(
            container_tag="video_file_controls", tag="bulk_select", value=False
        )

        return None

    def _ungroup_files(self, event: qtg.Action) -> None:
        """
        Ungroups selected files by setting their menu_group to -1.

        Args:
            event (qtg.Action): The event triggering the ungrouping.

        Returns:
            None
        """

        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        checked_items = self._file_grid.checkitems_get

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
                self._file_grid.value_set(
                    row=item.row_index,
                    col=self._file_grid.colindex_get(self.GROUP_COL),
                    value="",
                    user_data=video_item,
                )

        self._file_grid.checkitems_all(checked=False)
        for row in range(self._file_grid.row_count):
            self._row_checked[row] = False
        event.value_set(
            container_tag="video_file_controls", tag="bulk_select", value=False
        )

        return None

    def load_video_input_files(self, event: qtg.Action) -> None:
        """Loads video files into the video input grid
        Args:
            event (qtg.Acton) : Calling event
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        video_file_list: list[Video_Data] = []

        Video_File_Picker_Popup(
            title="Choose Video Files",
            container_tag="video_file_picker",
            video_file_list=video_file_list,  # Pass by ref
        ).show()

        if video_file_list:
            with qtg.sys_cursor(qtg.Cursor.hourglass):
                # Performs grid cleansing
                rejected = self._insert_files_into_grid(video_file_list)

            if self._file_grid.row_count > 0:
                loaded_files = []
                for row_index in reversed(range(self._file_grid.row_count)):
                    grid_video_data: Video_Data = self._file_grid.userdata_get(
                        row=row_index,
                        col=self._file_grid.colindex_get(self.SETTINGS_COL),
                    )

                    if grid_video_data is None:
                        continue

                    loaded_files.append(grid_video_data.video_path)
                self._save_grid(event)

                # Keep a list of words common to all file names
                self._common_words = utils.Find_Common_Words(loaded_files)

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
        debug: bool = False,
    ) -> str:
        """
        Inserts files into the file grid widget.

        Args:
            selected_files (list[Video_Data]): list of video file data
            debug (bool): Whether to print debug information

        Returns:
            str: A string containing information about any rejected files.
        """
        assert isinstance(selected_files, list), (
            f"{selected_files=}.  Must be a list of Video_Data objects"
        )
        assert all(isinstance(item, Video_Data) for item in selected_files), (
            f"{selected_files=}.  Must be a list of Video_Data objects"
        )

        rejected = ""
        rows_loaded = self._file_grid.row_count
        row_index = 0
        video_standard = ""

        # Get video_standard - PAL/NTSC
        while self._file_grid.row_count > 0:
            grid_video_data = self._file_grid.userdata_get(
                row=0, col=self._file_grid.colindex_get(self.VIDEO_FILE_COL)
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
                    row=check_row_index,
                    col=self._file_grid.colindex_get(self.VIDEO_FILE_COL),
                )

                if grid_video_data is None:  # Invalid row so remove it
                    self._file_grid.row_delete(row=int(check_row_index))
                    continue

                if grid_video_data.video_path == file_video_data.video_path:
                    break
            else:  # File not in the grid
                if debug and not utils.Is_Complied():
                    print(f"DBG FNIG {file_video_data}")

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
                    if debug and not utils.Is_Complied():
                        print(f"DBG FE {file_video_data}")
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
                    if debug and not utils.Is_Complied():
                        print(f"DBG VSB {file_video_data}")
                    continue

                if file_video_data.encoding_info.video_standard != video_standard:
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} ({file_video_data.encoding_info.video_standard}) :"
                        f" {sys_consts.SDELIM} Is Not {video_standard} The Project Video Standard  \n"
                    )
                    if debug and not utils.Is_Complied():
                        print(f"DBG VSM {file_video_data}")
                    continue

                if file_video_data.encoding_info.video_tracks == 0:
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} :"
                        f" {sys_consts.SDELIM}No Video Track \n"
                    )
                    if debug and not utils.Is_Complied():
                        print(f"DBG NVT {file_video_data}")
                    continue

                if file_video_data.encoding_info.video_frame_rate not in (
                    sys_consts.PAL_FRAME_RATE,
                    sys_consts.PAL_FIELD_RATE,
                    sys_consts.NTSC_FRAME_RATE,
                    sys_consts.NTSC_FIELD_RATE,
                    30,
                ):
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} :"
                        f" {sys_consts.SDELIM}Frame Rate Not Pal Or NTSC \n"
                    )
                    if debug and not utils.Is_Complied():
                        print(f"DBG FRE {file_video_data}")
                    continue

                # Set default filter settings from database
                if (
                    self._db_settings.setting_exist(sys_consts.VF_NORMALISE_DBK)
                    and self._db_settings.setting_get(sys_consts.VF_NORMALISE_DBK)
                    is not None
                ):
                    file_video_data.video_file_settings.normalise = (
                        self._db_settings.setting_get(sys_consts.VF_NORMALISE_DBK)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_DENOISE_DBK)
                    and self._db_settings.setting_get(sys_consts.VF_DENOISE_DBK)
                    is not None
                ):
                    file_video_data.video_file_settings.denoise = (
                        self._db_settings.setting_get(sys_consts.VF_DENOISE_DBK)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_WHITE_BALANCE_DBK)
                    and self._db_settings.setting_get(sys_consts.VF_WHITE_BALANCE_DBK)
                    is not None
                ):
                    file_video_data.video_file_settings.white_balance = (
                        self._db_settings.setting_get(sys_consts.VF_WHITE_BALANCE_DBK)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_SHARPEN_DBK)
                    and self._db_settings.setting_get(sys_consts.VF_SHARPEN_DBK)
                    is not None
                ):
                    file_video_data.video_file_settings.sharpen = (
                        self._db_settings.setting_get(sys_consts.VF_SHARPEN_DBK)
                    )

                if (
                    self._db_settings.setting_exist(sys_consts.VF_AUTO_LEVELS_DBK)
                    and self._db_settings.setting_get(sys_consts.VF_AUTO_LEVELS_DBK)
                    is not None
                ):
                    file_video_data.video_file_settings.auto_bright = (
                        self._db_settings.setting_get(sys_consts.VF_AUTO_LEVELS_DBK)
                    )

                toolbox = self._get_toolbox(file_video_data)

                duration = str(
                    datetime.timedelta(
                        seconds=file_video_data.encoding_info.video_duration
                    )
                ).split(".")[0]

                if debug and not utils.Is_Complied():
                    print(f"DBG PGR {file_video_data}")

                self._populate_grid_row(
                    row_index=rows_loaded + row_index,
                    video_data=file_video_data,
                    duration=duration,
                )

                self._file_grid.row_widget_set(
                    row=rows_loaded + row_index,
                    col=self._file_grid.colindex_get(self.SETTINGS_COL),
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
        assert isinstance(video_user_data, Video_Data), (
            f"{video_user_data=}. Must be an instance of Video_Data"
        )

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
        row_index: int,
        video_data: Video_Data,
        duration: str,
        italic: bool = False,
        tooltip: str = "",
    ) -> None:
        """Populates the grid row with the video information.

        Args:
            row_index (int): The index of the row to populate.
            video_data (File_Control.Video_Data): The video data to populate.
            duration (str): The duration of the video.
            italic (bool): Whether the text should be italic. Defaults to False.
            tooltip (str): The tooltip text. Defaults to "".
        """
        assert isinstance(video_data, Video_Data), (
            f"{video_data=}. Must be an instance of File_Control.Video_Data"
        )
        assert isinstance(duration, str), f"{duration=}. Must be str."
        assert isinstance(italic, bool), f"{italic=}. Must be bool."
        assert isinstance(tooltip, str), f"{tooltip=}. Must be str."

        if tooltip.strip() != "":
            value_tooltip = tooltip
        else:
            value_tooltip = (
                f"{sys_consts.SDELIM}{video_data.video_path}{sys_consts.SDELIM}"
            )

        self._file_grid.value_set(
            value=(
                f"{video_data.video_file}{video_data.video_extension}"
                if self._display_filename
                else video_data.video_file_settings.button_title
            ),
            row=row_index,
            col=self._file_grid.colindex_get(self.VIDEO_FILE_COL),
            user_data=video_data,
            tooltip=value_tooltip,
            italic=italic,
        )

        self._file_grid.value_set(
            value=str(video_data.encoding_info.video_width),
            row=row_index,
            col=self._file_grid.colindex_get(self.WIDTH_COL),
            user_data=video_data,
        )

        self._file_grid.value_set(
            value=str(video_data.encoding_info.video_height),
            row=row_index,
            col=self._file_grid.colindex_get(self.HEIGHT_COL),
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

        cur_value = self._file_grid.trans_get
        self._file_grid.trans_set(False)

        self._file_grid.value_set(
            value=encoder_str,
            tooltip=encoder_str,
            row=row_index,
            col=self._file_grid.colindex_get(self.ENCODER_COL),
            user_data=video_data,
        )
        self._file_grid.trans_set(cur_value)

        self._file_grid.value_set(
            value=duration,
            row=row_index,
            col=self._file_grid.colindex_get(self.DURATION_COL),
            user_data=video_data,
        )

        self._file_grid.value_set(
            value=video_data.encoding_info.video_standard,
            row=row_index,
            col=self._file_grid.colindex_get(self.STANDARD_COL),
            user_data=video_data,
        )

        self._file_grid.value_set(
            value=(
                f"{video_data.video_file_settings.menu_group}"
                if video_data.video_file_settings.menu_group >= 0
                else ""
            ),
            row=row_index,
            col=self._file_grid.colindex_get(self.GROUP_COL),
            user_data=video_data,
        )

        self._file_grid.userdata_set(
            row=row_index,
            col=self._file_grid.colindex_get(self.SETTINGS_COL),
            user_data=video_data,
        )

        return None

    def set_project_standard_duration(self, event: qtg.Action) -> None:
        """
        Sets the duration and video standard for the current project based on the selected
        input video files.

        Args:
            event (qtg.Action): The calling event.
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        total_duration = 0.0
        self.project_video_standard = ""
        self._project_duration = ""
        self.dvd_percent_used = 0

        if self._file_grid.row_count > 0:
            for checked_item in self._file_grid.checkitems_get:
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
                self._file_grid.row_count > 0
                and self._file_grid.userdata_get(
                    row=0, col=self._file_grid.colindex_get(self.SETTINGS_COL)
                )
                is None
            ):
                self._file_grid.row_delete(0)

            user_data = self._file_grid.userdata_get(
                row=0, col=self._file_grid.colindex_get(self.SETTINGS_COL)
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

        return None

    def shutdown(self) -> int:
        """
        Shuts down the instance

        Returns:
            int: 1:Ok, -1 Shutdown terminated
        """
        self._background_task_manager.throw_errors = False

        if self._background_task_manager.list_running_tasks():
            if (
                popups.PopYesNo(
                    title="Background Tasks Running...",
                    message="Kill Background Tasks And Exit?",
                ).show()
                == "no"
            ):
                return -1

            self._background_task_manager.stop()

        return 1

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
                tag=self.SETTINGS_COL,
                width=1,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Grp",
                tag=self.GROUP_COL,
                width=3,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Video File",
                tag=self.VIDEO_FILE_COL,
                width=80,
                editable=False,
                checkable=True,
            ),
            qtg.Col_Def(
                label="Width",
                tag=self.WIDTH_COL,
                width=6,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Height",
                tag=self.HEIGHT_COL,
                width=6,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Encoder",
                tag=self.ENCODER_COL,
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="System",
                tag=self.STANDARD_COL,
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Duration",
                tag=self.DURATION_COL,
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
