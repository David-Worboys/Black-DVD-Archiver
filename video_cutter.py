"""
Implements a basic video cutter

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
import functools
import json
from typing import Callable, cast, Literal

import PySide6.QtCore as qtC
import PySide6.QtGui as qtG

import dvdarch_utils
import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
import utils
from archive_management import Archive_Manager
from background_task_manager import Task_Manager
from file_renamer_popup import File_Renamer_Popup
from sys_config import (DVD_Archiver_Base, Encoding_Details, Video_Data,
                        Video_File_Settings)

# fmt: on

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


def Run_Video_Cuts(cut_video_def: dvdarch_utils.Cut_Video_Def) -> tuple[int, str]:
    """This is a wrapper function used hy the multi-thread task_manager to run the Execute_Check_Output process

    Args:
        cut_video_def (dvdarch_utils.Cut_Video_Def): Defines video cut parameters

    Returns:
        tuple[int, str]:
        - arg1 1: ok, -1: fail
        - arg2: error message or "" if ok
    """
    global gi_task_error_code
    global gs_task_error_message

    if not utils.Is_Complied():
        print(f"DBG {cut_video_def=}")

    gi_task_error_code, gs_task_error_message = dvdarch_utils.Cut_Video(
        cut_video_def=cut_video_def
    )

    if not utils.Is_Complied():
        print(f"DBG Run_DVD_Build {gi_task_error_code=} {gs_task_error_message=}")

    return gi_task_error_code, gs_task_error_message


def Notification_Call_Back(status: int, message: str, output: str, name):
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

    if status == -1:
        gb_task_errored = True
    else:
        gi_tasks_completed += 1

    if not utils.Is_Complied():
        print(
            "DBG Notification_Call_Back"
            f" {gs_thread_status=} {gs_thread_message=} {gs_thread_output=} {gs_thread_task_name=}"
        )


# self._tasks_submitted -= 1
def Error_Callback(error_message: str):
    """The Error_Callback function is called by the multi-thread task_manager when a task errors

    Args:
        error_message (str): The error message generated when the calling thread broke
    """
    global gs_thread_error_message

    gs_thread_error_message = error_message

    if not utils.Is_Complied():
        print(f"DBG Error_Callback {gs_thread_error_message=}")


################################
@dataclasses.dataclass(slots=True)
class Edit_List:
    """
    Stores, updates and deletes the edit list
    """

    _error_message: str = ""
    _error_code: int = 1

    _archive_folder: str = ""
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _json_edit_cuts_file: str = "edit_cuts"
    _video_shelf_name: Literal["video_cutter"] = "video_cutter"

    def __post_init__(self):
        if self._db_settings.setting_exist(sys_consts.ARCHIVE_FOLDER):
            self._archive_folder = self._db_settings.setting_get(
                sys_consts.ARCHIVE_FOLDER
            )

    def delete_edit_cuts(
        self,
        file_path: str,
        project: str,
        layout: str,
    ) -> tuple[int, str]:
        """
        Deletes all edit cuts associated with the given file that are stored in the edit cuts SQL Shelve

        Args:
            file_path (str): The path of the video file.
            project (str): The project name
            layout (str): The DVD layout name

        Returns:
            tuple[int,str]:
                arg 1 - error_code
                arg 2 - error message
        """
        assert isinstance(project, str), f"{project=}. Must be a str"
        # Make sure we have a layout with a project and vice versa
        # assert (
        #    not project or layout
        # ), f"{layout=}. Must not be empty if {project=} is provided"
        assert (
            not layout.strip() or project.strip()
        ), f"{project=}. Must not be empty if {layout=} is provided"
        self._error_message = ""
        self._error_code = 1

        sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message

        shelf_dict = sql_shelf.open(shelf_name="video_cutter")
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message

        if file_path in shelf_dict:
            edit_cuts = shelf_dict[file_path]
            if (
                "user_data" in edit_cuts
                and "project_edit_cuts" in edit_cuts["user_data"]
                and project in edit_cuts["user_data"]["project_edit_cuts"]
            ):
                edit_cuts["user_data"]["project_edit_cuts"].pop(project)

                if edit_cuts["user_data"]["project_edit_cuts"]:
                    shelf_dict[file_path] = edit_cuts
                else:
                    shelf_dict.pop(file_path)
            else:
                shelf_dict.pop(file_path)

            result, message = sql_shelf.update(
                shelf_name="video_cutter", shelf_data=shelf_dict
            )

            self._error_message = message
            self._error_code = result

            if sql_shelf.error.code == -1:
                return -1, sql_shelf.error.message

        return self._error_code, self._error_message

    def get_edit_cuts_visibility(
        self, file_path: str, project: str, layout: str
    ) -> tuple[int, str, Literal["global", "project", ""]]:
        """Returns the edit cuts visibility for a project

        Args:
            file_path (str): The path of the video file.
            project (str): The project name
            layout (str): The DVD layout name
        Returns:
           tuple[int, str, Literal["global","project",""]]:
            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.
            - arg 3: If the status code is 1 then "project" or "global" is returned otherwise ""

        """

        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a str"
        assert isinstance(project, str), f"{project=}. Must be a str"
        # Make sure we have a layout with a project and vice versa
        # assert (
        #    not project or layout
        # ), f"{layout=}. Must not be empty if {project=} is provided"
        assert (
            not layout.strip() or project.strip()
        ), f"{project=}. Must not be empty if {layout=} is provided"

        sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message, ""

        shelf_dict = sql_shelf.open(shelf_name="video_cutter")
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message, ""

        if file_path in shelf_dict:
            edit_cuts = shelf_dict[file_path]

            if (
                project
                and "user_data" in edit_cuts
                and "project_edit_cuts" in edit_cuts["user_data"]
            ):
                project_edit_cuts = edit_cuts["user_data"]["project_edit_cuts"]

                if project in project_edit_cuts:
                    return 1, "", "project"

        return 1, "", "global"

    def globalise_edit_cuts(
        self, file_path: str, project: str, layout: str, combine: bool = False
    ) -> tuple[int, str, tuple[tuple[int, int, str], ...]]:
        """
        Make the project edit cuts the global edit cuts for the video file.

        Args:
            file_path (str): The path of the video file.
            project (str): The project name
            layout (str): The DVD layout name
            combine (bool): True : Combine Project and Global List, False : Do not combine

        Returns:
           tuple[int,str,tuple[tuple[int, int, str],...]]:
            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.
            - arg 3: If the status code is 1 then a tuple of edit cut tuples is returned (mark_in,mark_out,clip_name)
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a str"
        assert isinstance(project, str), f"{project=}. Must be a str"
        # Make sure we have a layout with a project and vice versa
        # assert (
        #    not project or layout
        # ), f"{layout=}. Must not be empty if {project=} is provided"
        assert (
            not layout.strip() or project.strip()
        ), f"{project=}. Must not be empty if {layout=} is provided"
        assert isinstance(combine, bool), f"{combine=}. Must be bool"

        sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message, ()

        shelf_dict = sql_shelf.open(shelf_name="video_cutter")
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message, ()

        if file_path in shelf_dict:
            edit_dict = shelf_dict[file_path]

            if (
                "user_data" in edit_dict
                and "project_edit_cuts" in edit_dict["user_data"]
            ):
                project_edit_cuts = edit_dict["user_data"]["project_edit_cuts"]
                if project in project_edit_cuts:
                    project_edit_list = project_edit_cuts.pop(project)

                    if combine:  # Combine Project and Global edit cut lists
                        edit_dict["edit_cuts"] = tuple(
                            set(edit_dict["edit_cuts"]) | set(project_edit_list)
                        )
                    else:  # Make the project edit cuts the global edit cuts
                        edit_dict["edit_cuts"] = project_edit_list

                    shelf_dict[file_path] = edit_dict

                    result, message = sql_shelf.update(
                        shelf_name="video_cutter", shelf_data=shelf_dict
                    )

                    self._error_message = message
                    self._error_code = result

                    if sql_shelf.error.code == -1:
                        return -1, message, ()

                    return self.read_edit_cuts(
                        file_path=file_path, project="", layout=layout
                    )
        return 1, "", ()

    def read_edit_cuts(
        self,
        file_path: str,
        project: str,
        layout: str,
    ) -> tuple[int, str, tuple[tuple[int, int, str], ...]]:
        """
        Read edit cuts for a video file from a JSON file.

        Args:
            file_path (str): The path of the video file.
            project (str): The project name
            layout (str): The DVD layout name

        Returns:
           tuple[int,str,tuple[tuple[int, int, str],...]]:
            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:
            - arg 3: If the status code is 1 then a tuple of edit cut tuples is returned (mark_in,mark_out,clip_name)
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a str"
        assert isinstance(project, str), f"{project=}. Must be a str"
        # Make sure we have a layout with a project and vice versa
        # assert (
        #    not project or layout
        # ), f"{layout=}. Must not be empty if {project=} is provided"
        assert (
            not layout.strip() or project.strip()
        ), f"{project=}. Must not be empty if {layout=} is provided"

        sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message, ()

        shelf_dict = sql_shelf.open(shelf_name="video_cutter")
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message, ()

        if file_path in shelf_dict:
            edit_dict = shelf_dict[file_path]

            # Design oversight fix
            if "user_data" not in edit_dict:
                edit_dict["user_data"] = {}
            if "project_edit_cuts" not in edit_dict["user_data"]:
                edit_dict["user_data"] = {"project_edit_cuts": {}}
                shelf_dict[file_path] = edit_dict

                result, message = sql_shelf.update(
                    shelf_name="video_cutter", shelf_data=shelf_dict
                )

                self._error_message = message
                self._error_code = result

                if sql_shelf.error.code == -1:
                    return -1, message, ()

            # Back to the regular programme
            if project:
                project_edit_cuts = edit_dict["user_data"]["project_edit_cuts"]

                if project in project_edit_cuts:
                    return 1, "", project_edit_cuts[project]

            return 1, "", edit_dict["edit_cuts"]

        # Code below migrates existing JSON file edit cuts  to a SQL shelf. TODO Remove in some future version
        if self._archive_folder:
            self._error_message = ""
            self._error_code = 1

            file_handler = file_utils.File()
            json_cuts_file = file_handler.file_join(
                self._archive_folder, self._json_edit_cuts_file, "json"
            )

            if not file_handler.path_exists(self._archive_folder):
                self._error_message = (
                    f"{sys_consts.SDELIM}{self._archive_folder}{sys_consts.SDELIM} does not"
                    " exist"
                )
                self._error_code = -1
                return -1, self._error_message, ()

            if not file_handler.path_writeable(self._archive_folder):
                self._error_message = (
                    f"{sys_consts.SDELIM}{self._archive_folder}{sys_consts.SDELIM} is not"
                    " writable"
                )
                self._error_code = -1
                return -1, self._error_message, ()

            if not file_handler.file_exists(json_cuts_file):
                self._error_message = f"{sys_consts.SDELIM}{json_cuts_file}{sys_consts.SDELIM} does not exist"
                self._error_code = 1  # May not be an actual error
                return 1, self._error_message, ()

            # Read JSON data from file
            try:
                with open(json_cuts_file, "r") as json_file:
                    json_data_dict = json.load(json_file)
            except (
                FileNotFoundError,
                PermissionError,
                IOError,
                json.decoder.JSONDecodeError,
            ) as e:
                self._error_message = (
                    f"Can not read {sys_consts.SDELIM}{json_cuts_file}."
                    f" {e}{sys_consts.SDELIM}"
                )
                self._error_code = -1
                return -1, self._error_message, ()

            if not isinstance(json_data_dict, dict):
                self._error_message = "Invalid JSON file format"
                self._error_code = -1
                return -1, self._error_message, ()

            edit_cuts = []
            if file_path in json_data_dict:
                for json_edit_cuts in json_data_dict[file_path]:
                    if (
                        len(json_edit_cuts) != 3
                        or not isinstance(json_edit_cuts[0], int)  # Mark In
                        or not isinstance(json_edit_cuts[1], int)  # Mark Out
                        or not isinstance(json_edit_cuts[2], str)  # Clip name
                    ):
                        self._error_code = -1
                        self._error_message = (
                            "Invalid JSON format for"
                            f" {sys_consts.SDELIM}{file_path}{sys_consts.SDELIM}"
                        )

                        edit_cuts = ()
                        break

                    edit_cuts.append(tuple(json_edit_cuts))
                else:  # All good
                    # if utils.Is_Complied():  # Remove file_path from JSON file
                    json_data_dict.pop(file_path)
                    try:
                        with open(json_cuts_file, "w") as json_file:
                            json.dump(json_data_dict, json_file)
                    except (
                        FileNotFoundError,
                        PermissionError,
                        IOError,
                    ) as e:
                        self._error_message = (
                            f"Can not write {sys_consts.SDELIM}{json_cuts_file}."
                            f" {e}{sys_consts.SDELIM}"
                        )
                        self._error_code = -1

                if self._error_code == -1:  # JSON file error occurred
                    return -1, self._error_message, ()

                if edit_cuts:
                    if not utils.Is_Complied():
                        print(
                            f" Migrating [{file_path=}] Edit Points In [{json_cuts_file}]  To A SQL SHELF"
                        )
                    # Add edit_cuts to the SQL shelf
                    shelf_dict[file_path] = {
                        "project": project,
                        "layout": layout,
                        "edit_cuts": edit_cuts,
                    }

                    result, message = sql_shelf.update(
                        shelf_name="video_cutter", shelf_data=shelf_dict
                    )

                    self._error_message = message
                    self._error_code = result

                    if sql_shelf.error.code == -1:
                        return -1, sql_shelf.error.message, ()

                    return 1, "", tuple(edit_cuts)
        return 1, "", ()

    def write_edit_cuts(
        self,
        file_path: str,
        project: str,
        layout: str,
        file_cuts: list[(int, int, str)],
    ) -> tuple[int, str]:
        """Store files and cuts in the archive json_file.

        Args:
            file_path (str): The path of the video file that owns the cuts.
            project (str): The project name
            layout (str): The DVD layout name
            file_cuts (list[(int,int,str)]): A  list of cuts for the file_path.
                Each cut is represented by a tuple with the cut_in value, cut_out value, and cut_name string.

        Returns:
            int, str:
                - arg 1: If the status code is 1, the operation was successful otherwise it failed.
                - arg 2: If the status code is -1, an error occurred, and the message provides details.:
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a str"
        assert isinstance(project, str), f"{project=}. Must be a str"
        assert isinstance(layout, str), f"{layout=}. Must be a str"
        assert isinstance(file_cuts, list), f"{file_cuts=}. Must be a list"

        for cut in file_cuts:
            assert isinstance(cut, tuple), f"{cut=}. Must be a tuple"
            assert len(cut) == 3, f"{cut=}. Must have Mark_In, Mark_Out, Cut Name"
            assert isinstance(cut[0], int), f"{cut[0]=}. Must be int"
            assert isinstance(cut[1], int), f"{cut[1]=}. Must be int"
            assert isinstance(cut[2], str), f"{cut[2]=}. Must be str"

        # Make sure we have a layout with a project and vice versa
        # assert (
        #    not project or layout
        # ), f"{layout=}. Must not be empty if {project=} is provided"
        assert (
            not layout.strip() or project.strip()
        ), f"{project=}. Must not be empty if {layout=} is provided"

        sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message

        shelf_dict = sql_shelf.open(shelf_name="video_cutter")
        self._error_message = sql_shelf.error.message
        self._error_code = sql_shelf.error.code

        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message

        if file_path in shelf_dict:
            edit_dict = shelf_dict[file_path]
            edit_dict["project"] = project
            edit_dict["layout"] = layout

            if "user_data" not in edit_dict:
                edit_dict["user_data"] = {}
            if "project_edit_cuts" not in edit_dict["user_data"]:
                edit_dict["user_data"] = {"project_edit_cuts": {}}

        else:
            edit_dict = {
                "project": project,
                "layout": layout,
                "edit_cuts": tuple(file_cuts),
                "user_data": {"project_edit_cuts": {}},
            }

        if project:  # Project edit cuts
            project_edit_cuts = edit_dict["user_data"]["project_edit_cuts"]
            project_edit_cuts[project] = tuple(file_cuts)
            edit_dict["user_data"]["project_edit_cuts"] = project_edit_cuts
        else:  # Global edit cuts
            edit_dict["edit_cuts"] = tuple(file_cuts)

        shelf_dict[file_path] = edit_dict

        result, message = sql_shelf.update(
            shelf_name="video_cutter", shelf_data=shelf_dict
        )

        self._error_message = message
        self._error_code = result

        if sql_shelf.error.code == -1:
            return -1, message

        return 1, ""


@dataclasses.dataclass(slots=True)
class Video_Editor(DVD_Archiver_Base):
    """Implements a basic video editor"""

    # Public instance variables
    processed_files_callback: Callable
    display_height: int = sys_consts.PAL_SPECS.height_43  # // 2
    display_width: int = sys_consts.PAL_SPECS.width_43  # // 2

    # Private instance variables
    _aspect_ratio: str = sys_consts.AR43
    _archive_manager: Archive_Manager | None = None
    _background_task_manager: Task_Manager | None = None
    _current_frame: int = -1
    _display_height: int = -1
    _display_width: int = -1
    _edit_list_grid: qtg.Grid | None = None
    _edit_list: Edit_List = dataclasses.field(default_factory=Edit_List)
    _file_system_init: bool = False
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _frame_rate: float = sys_consts.PAL_SPECS.frame_rate
    _frame_width: int = sys_consts.PAL_SPECS.width_43
    _frame_height: int = sys_consts.PAL_SPECS.height_43
    _frame_count: int = -1
    _output_folder: str = ""
    _video_cutter_container: qtg.HBoxContainer | None = None
    _video_display: qtg.Label | None = None
    _video_slider: qtg.Slider | None = None
    _frame_display: qtg.LCD | None = None
    _menu_frame: qtg.LineEdit | None = None
    _menu_title: qtg.LineEdit | None = None
    _progress_bar: qtg.ProgressBar | None = None
    _all_projects_rb: qtg.RadioButton | None = None
    _this_project_rb: qtg.RadioButton | None = None
    _source_file_label: qtg.Label | None = None
    _video_editor: qtg.HBoxContainer | None = None
    _video_filter_container: qtg.HBoxContainer | None = None
    _sliding: bool = False
    _source_state = "no_media"
    _step_value: int = 1
    _video_handler: qtg.Video_Player | None = None
    _edit_folder: str = sys_consts.EDIT_FOLDER
    _transcode_folder: str = sys_consts.TRANSCODE_FOLDER
    _video_file_input: list[Video_Data] = dataclasses.field(default_factory=list)
    _project_name: str = ""
    _user_lambda: bool = False

    def __post_init__(self) -> None:
        """Configures the instance"""
        assert isinstance(
            self.processed_files_callback, Callable
        ), f"{self.processed_files_callback= }. Must be method/function lamda"

        assert (
            isinstance(self.display_height, int) and self.display_height > 0
        ), f"{self.display_height=}. Must be int > 0"
        assert (
            isinstance(self.display_width, int) and self.display_width > 0
        ), f"{self.display_width=}. Must be int > 0"

        self._video_handler = qtg.Video_Player(
            display_width=self.display_width, display_height=self.display_height
        )

        self._background_task_manager: Task_Manager = Task_Manager()
        self._background_task_manager.start()

        if self._user_lambda:  # Not really lambda, but same effect, with earlier versions of pyside > 6 5.1 and
            # Nuitka < 1.8.4 == boom! (And nope after a long session finally locked)
            self._video_handler.frame_changed_handler.connect(self._frame_handler)
            self._video_handler.media_status_changed_handler.connect(
                self._media_status_change
            )
            self._video_handler.position_changed_handler.connect(self._position_changed)
        else:  # This saves the day!
            self._video_handler.frame_changed_handler.connect(
                functools.partial(self._frame_handler)
            )

            self._video_handler.media_status_changed_handler.connect(
                functools.partial(self._media_status_change)
            )

            self._video_handler.position_changed_handler.connect(
                functools.partial(self._position_changed)
            )

        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        if archive_folder:
            self._archive_manager = Archive_Manager(archive_folder=archive_folder)

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
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            if self._video_file_input:
                self.archive_edit_list_write()
                self._get_dvd_settings()
                self.processed_files_callback(self._video_file_input)

            self._background_task_manager.stop()
            self._video_handler.stop()

        return 1

    def event_handler(self, event: qtg.Action) -> None:
        """Handles the events of the video editor
        Args:
            event (qtg.Action): The triggering event
        """
        match event.event:
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "backward":
                        self._step_backward()
                    case "bulk_select":
                        self._edit_list_grid.checkitems_all(
                            checked=event.value, col_tag="mark_in"
                        )
                    case "all_projects":
                        copy_method = popups.PopOptions(
                            title="Edit List...",
                            message="Select An Edit List Option",
                            options={
                                "Use The Global Edit List And Delete The Project Edit List:: Deletes The  Project "
                                "Edit List And Uses The Global Edit List": "delete_project",
                                "Make The Edit List Global                                :: Makes The Project Edit "
                                "List The Global Edit List ": "global_project",
                                "Combine Project And Global Edit List                     :: Combines The Project And "
                                "Global Edit List": "combine_project",
                                "Cancel::": "cancel",
                            },
                        ).show()

                        match copy_method:
                            case "delete_project":
                                result, message = self._edit_list.delete_edit_cuts(
                                    file_path=self._video_file_input[0].video_path,
                                    project=self._project_name,
                                    layout="",
                                )

                                if result == -1:
                                    return None

                                result, message, edit_cuts = (
                                    self._edit_list.read_edit_cuts(
                                        file_path=self._video_file_input[0].video_path,
                                        project="",
                                        layout="",
                                    )
                                )
                                if result == -1:
                                    return None

                                self._populate_edit_cuts(edit_cuts)
                            case "global_project":
                                result, message, edit_cuts = (
                                    self._edit_list.globalise_edit_cuts(
                                        file_path=self._video_file_input[0].video_path,
                                        project=self._project_name,
                                        layout="",
                                    )
                                )
                                if result == -1:
                                    return None

                                self._populate_edit_cuts(edit_cuts)
                            case "combine_project":
                                result, message, edit_cuts = (
                                    self._edit_list.globalise_edit_cuts(
                                        file_path=self._video_file_input[0].video_path,
                                        project=self._project_name,
                                        layout="",
                                        combine=True,
                                    )
                                )
                                if result == -1:
                                    return None

                                self._populate_edit_cuts(edit_cuts)
                            case "cancel":
                                return None

                    case "this_project":
                        result, message, edit_cuts = self._edit_list.read_edit_cuts(
                            file_path=self._video_file_input[0].video_path,
                            project=self._project_name,
                            layout="",
                        )

                        if not edit_cuts:
                            result, message, edit_cuts = self._edit_list.read_edit_cuts(
                                file_path=self._video_file_input[0].video_path,
                                project="",
                                layout="",
                            )

                        self._populate_edit_cuts(edit_cuts)

                        # self.archive_edit_list_write()
                    case "assemble_segments":
                        self._assemble_segments(event)
                    case "delete_segments":
                        self._delete_segments(event)
                    case "mark_in" | "mark_out":  # Edit List Seek
                        self._edit_list_seek(event)
                    case "move_edit_point_down":
                        self._move_edit_point(up=False)
                    case "move_edit_point_up":
                        self._move_edit_point(up=True)
                    case "forward":
                        self._step_forward()
                    case "play":
                        self._sliding = True
                        self._video_handler.play()
                    case "pause":
                        self._video_handler.pause()
                    case "remove_edit_points":
                        self._remove_edit_points(event)
                    case "selection_start":
                        self._selection_start(event)
                    case "selection_end":
                        self._selection_end(event)
                    case "set_menu_image":
                        current_frame = str(self._video_handler.current_frame())
                        if current_frame:
                            event.value_set(
                                container_tag=event.container_tag,
                                tag="menu_frame",
                                value=current_frame,
                            )
                            self._video_file_input[
                                0
                            ].video_file_settings.menu_button_frame = int(current_frame)

                    case "menu_frame":
                        current_frame: str = event.value_get(
                            container_tag=event.container_tag, tag=event.tag
                        )
                        if current_frame:
                            self._seek(int(current_frame))
                    case "clear_menu_frame":
                        if (
                            popups.PopYesNo(
                                title="Clear The Button Image `...",
                                message="Clear The DVD Menu Button Image?",
                            ).show()
                            == "yes"
                        ):
                            event.value_set(
                                container_tag=event.container_tag,
                                tag="menu_frame",
                                value="",
                            )
                            self._video_file_input[
                                0
                            ].video_file_settings.menu_button_frame = -1

            case qtg.Sys_Events.INDEXCHANGED:
                match event.tag:
                    case "step_unit":
                        self._step_unit(event)

            case qtg.Sys_Events.MOVED:
                match event.tag:
                    case "video_slider":
                        self._video_handler.blockSignals(True)
                        self._seek(event.value)
                        self._video_handler.blockSignals(False)
            case qtg.Sys_Events.PRESSED:
                match event.tag:
                    case "video_slider":
                        self._sliding = False

            case qtg.Sys_Events.RELEASED:
                match event.tag:
                    case "video_slider":
                        self._sliding = False
                        self._seek(event.value)

            case qtg.Sys_Events.TRIGGERED:
                match event.tag:
                    case "video_slider":
                        self._seek(event.value)

    @property
    def get_task_manager(self) -> Task_Manager:
        """Returns the task manager instance

        Returns:
            Task_Manager : The task manager instance

        """
        return self._background_task_manager

    def is_available(self) -> bool:
        """Checks if the media player is supported on the platform
        Returns:
            bool: True if the media player is supported, False otherwise.
        """
        return self._video_handler.available()

    def set_source(
        self, video_file_input: list[Video_Data], output_folder: str, project_name: str
    ) -> None:
        """Sets the source of the media player

        Args:
            video_file_input (list[Video_Data]): The input video information
            output_folder (str): The folder in which processed video files are placed
            project_name (str): The name of the currently selected project
        """
        assert isinstance(video_file_input, list), f"{video_file_input=}. Must be list"
        assert all(
            isinstance(video_file, Video_Data) for video_file in video_file_input
        ), f"{video_file_input=}. Must be list of Video_Data"

        assert (
            isinstance(output_folder, str) and output_folder.strip() != ""
        ), f"{output_folder=}. Must be non-empty str"
        assert isinstance(project_name, str), f"{project_name=}. Must be str"

        self._frame_display.value_set(0)
        self._output_folder = output_folder
        self._project_name = project_name

        if self._video_file_input:
            self._get_dvd_settings()
            self.processed_files_callback(self._video_file_input)

        self._edit_list_grid.clear()
        self._menu_frame.value_set("")

        self._video_file_input = video_file_input
        self._all_projects_rb.enable_set(False)
        self._this_project_rb.enable_set(False)

        # if not self._file_system_init:
        result = self._video_file_system_maker()

        if result == -1:
            return None

        if self._video_file_input[0].video_path.startswith(self._edit_folder):
            self._this_project_rb.value_set(True)
        else:
            self._all_projects_rb.enable_set(True)
            self._this_project_rb.enable_set(True)

            result, _, edit_list_visibility = self._edit_list.get_edit_cuts_visibility(
                file_path=self._video_file_input[0].video_path,
                project=project_name,
                layout="",
            )

            if result == -1:
                return None

            if edit_list_visibility == "global":
                self._all_projects_rb.value_set(True)
            else:
                self._this_project_rb.value_set(True)

        self._archive_edit_list_read()

        self._aspect_ratio = self._video_file_input[0].encoding_info.video_ar
        self._frame_width = self._video_file_input[0].encoding_info.video_width
        self._frame_height = self._video_file_input[0].encoding_info.video_height
        self._frame_rate = self._video_file_input[0].encoding_info.video_frame_rate
        self._frame_count = self._video_file_input[0].encoding_info.video_frame_count

        self._video_slider.value_set(0)
        self._video_slider.range_max_set(
            round(
                self._video_file_input[0].encoding_info.video_duration
                * self._video_file_input[0].encoding_info.video_frame_rate
            )
            - 1
        )  # Interesting, video_frame_count was not quite accurate on some video files, this seems to be better

        self._set_dvd_settings()

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="white_balance",
        ).value_set(self._video_file_input[0].video_file_settings.white_balance)

        if self._frame_count > 0:
            self._video_handler.set_source(
                self._video_file_input[0].video_path, self._frame_rate
            )

        self._source_file_label.value_set(
            f"{self._video_file_input[0].video_file}{self._video_file_input[0].video_extension}"
        )
        self._source_file_label.tooltip_set(
            f"{sys_consts.SDELIM}{self._video_file_input[0].video_path}{sys_consts.SDELIM}"
        )

    @property
    def video_file_input(self) -> list[Video_Data]:
        """The input video information
        Returns:
            list[Video_Data]: The input video information
        """
        self._get_dvd_settings()

        return self._video_file_input

    def _get_dvd_settings(self):
        """Populates DVD settings with values sourced from self.video_file_input"""
        if self._video_file_input:
            if self._menu_title.modified:
                self._video_file_input[
                    0
                ].video_file_settings.button_title = self._menu_title.value_get()

            if self._menu_frame.modified:
                self._video_file_input[0].video_file_settings.menu_button_frame = int(
                    self._menu_frame.value_get()
                )

            self._video_file_input[
                0
            ].video_file_settings.normalise = self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="normalise",
            ).value_get()

            self._video_file_input[
                0
            ].video_file_settings.denoise = self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="denoise",
            ).value_get()

            self._video_file_input[
                0
            ].video_file_settings.white_balance = (
                self._video_filter_container.widget_get(
                    container_tag="video_filters",
                    tag="white_balance",
                ).value_get()
            )

            self._video_file_input[
                0
            ].video_file_settings.auto_bright = self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="auto_levels",
            ).value_get()

            self._video_file_input[
                0
            ].video_file_settings.sharpen = self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="sharpen",
            ).value_get()

    def video_pause(self):
        """Pause video playback"""
        self._video_handler.pause()

    def _set_dvd_settings(self):
        """Writes DVD settings into the appropriate values of self.video_file_input"""

        file_handler = file_utils.File()

        if (
            self._video_file_input[0].video_file_settings.button_title.strip() == ""
        ):  # Attempt to extract the title from the input file name.
            _, file_name, _ = file_handler.split_file_path(
                self._video_file_input[0].video_path
            )
            dvd_menu_title = file_handler.extract_title(file_name)
        else:
            dvd_menu_title = self._video_file_input[0].video_file_settings.button_title

        self._menu_title.value_set(dvd_menu_title)

        if self._video_file_input[0].video_file_settings.menu_button_frame >= 0:
            self._menu_frame.value_set(
                str(self._video_file_input[0].video_file_settings.menu_button_frame)
            )

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="normalise",
        ).value_set(self._video_file_input[0].video_file_settings.normalise)

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="denoise",
        ).value_set(self._video_file_input[0].video_file_settings.denoise)

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="white_balance",
        ).value_set(self._video_file_input[0].video_file_settings.white_balance)

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="auto_levels",
        ).value_set(self._video_file_input[0].video_file_settings.auto_bright)

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="sharpen",
        ).value_set(self._video_file_input[0].video_file_settings.sharpen)

    def _archive_edit_list_read(self) -> None:
        """Reads edit cuts from the archive manager and populates the edit list grid with the data. If both the
        archive manager and the edit list grid exist, reads edit cuts for the input file from the archive manager
        using the `read_edit_cuts` method. Then, for each cut tuple in the edit cuts list, sets the `mark_in` and
        `mark_out` values of the corresponding row in the edit list grid using the `value_set` method.
        """

        if self._edit_list_grid:
            result, message, edit_cuts = self._edit_list.read_edit_cuts(
                self._video_file_input[0].video_path,
                "" if self._all_projects_rb.value_get() is True else self._project_name,
                layout="",
            )

            if result == -1:
                if self._archive_manager.get_error_code == -1:
                    popups.PopError(
                        title="Archive Edit List",
                        message=f"Read Failed : {message}",
                    ).show()
                    return None

            mark_in = self._edit_list_grid.colindex_get("mark_in")
            mark_out = self._edit_list_grid.colindex_get("mark_out")
            clip_name = self._edit_list_grid.colindex_get("clip_name")

            for row, cut_tuple in enumerate(edit_cuts):
                self._edit_list_grid.value_set(
                    row=row, col=mark_in, value=cut_tuple[0], user_data=cut_tuple
                )

                self._edit_list_grid.value_set(
                    row=row, col=mark_out, value=cut_tuple[1], user_data=cut_tuple
                )

                self._edit_list_grid.value_set(
                    row=row, col=clip_name, value=cut_tuple[2], user_data=cut_tuple
                )
            self._edit_list_grid.select_row(0, clip_name)

    def archive_edit_list_write(self) -> None:
        """Writes the edit list from the GUI grid to the archive manager for the current video file.

        The edit list is read from the GUI grid, which has columns for the mark in, mark out,
        and cut name for each cut in the edit list. These values are extracted from the grid and
        stored in a list of tuples. The list is then written to the archive manager for the current
        video file.

        If the archive manager has not been set up, this method does nothing.

        """
        if self._archive_manager:
            mark_in = self._edit_list_grid.colindex_get("mark_in")
            mark_out = self._edit_list_grid.colindex_get("mark_out")
            clip_name = self._edit_list_grid.colindex_get("clip_name")

            edit_list = [
                (
                    int(self._edit_list_grid.value_get(row=row_index, col=mark_in)),
                    int(
                        self._edit_list_grid.value_get(row=row_index, col=mark_out)
                        or self._frame_count
                    ),
                    self._edit_list_grid.value_get(row=row_index, col=clip_name),
                )
                for row_index in range(self._edit_list_grid.row_count)
            ]

            if edit_list:
                if self._all_projects_rb.value_get():
                    result, message = self._edit_list.write_edit_cuts(
                        file_path=self._video_file_input[0].video_path,
                        project="",
                        layout="",
                        file_cuts=edit_list,
                    )
                else:
                    result, message = self._edit_list.write_edit_cuts(
                        file_path=self._video_file_input[0].video_path,
                        project=self._project_name,
                        layout="",
                        file_cuts=edit_list,
                    )
            elif self._video_file_input:
                result, message = self._edit_list.delete_edit_cuts(
                    self._video_file_input[0].video_path,
                    project=""
                    if self._all_projects_rb.value_get()
                    else self._project_name,
                    layout="",
                )
            else:
                result = 1
                message = ""

            if result == -1:
                popups.PopError(
                    title="Archive Edit List", message=f"Write Failed : {message}"
                ).show()

    def _get_encoding_info(self, video_file_path: str) -> tuple[int, Encoding_Details]:
        """Gets the encoding info for a video file

        Belts and braces because should never need this loopiness unless something goes off the rails in thread handling.
        This meothpd is only useful where thread handling is used to assemble or cut files in threads

        Args:
            video_file_path: This file path to the video file

        Returns:
            int : arg 1 if ok, 0 otherwise
            Encoding_Details: arg 2 encoding details if all good otherwise blank encoding details with the error filled
            out
        """
        assert (
            isinstance(video_file_path, str) and video_file_path.strip() != ""
        ), f"{video_file_path=}. Must be a non-empty string"

        blank_encoding_info = Encoding_Details()

        file_handler = file_utils.File()
        file_path, file_name, file_extn = file_handler.split_file_path(video_file_path)

        if not file_handler.file_exists(
            directory_path=file_path, file_name=file_name, file_extension=file_extn
        ):
            blank_encoding_info.error = f"File does not exist : {video_file_path=}"
            blank_encoding_info.video_duration = 0
            popups.PopError(
                title="Failed to Get Encoding Info...",
                message=(
                    "Failed To Get Encoding Info Or Duration Is 0"
                    f" Secs : {video_file_path=} :"
                    f" {blank_encoding_info.error} :"
                    f" {blank_encoding_info.video_duration}"
                ),
            ).show()

        for i in range(20):  # Loop 20 times with a 3 second sleep = 1 Minute
            encoding_info = dvdarch_utils.Get_File_Encoding_Info(video_file_path)

            if (
                encoding_info.error.strip() == "" and encoding_info.video_duration > 0
            ):  # Should break first time if thread handling did its job!
                return 1, encoding_info

        else:
            blank_encoding_info.error = encoding_info.error
            popups.PopError(
                title="Failed to Get Encoding Info...",
                message=(
                    "Failed To Get Encoding Info Or Duration Is 0"
                    f" Secs : {video_file_path=} :"
                    f" {encoding_info.error} :"
                    f" {encoding_info.video_duration}"
                ),
            ).show()

            return -1, blank_encoding_info

    def _assemble_segments(self, event: qtg.Action) -> None:
        """
        Takes the specified segments from the input file and makes new video files from them.

        Args:
            event (qtg.Action): The event that triggered this method.

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be type qtg.Action"

        file_handler = file_utils.File()

        mark_in = self._edit_list_grid.colindex_get("mark_in")
        mark_out = self._edit_list_grid.colindex_get("mark_out")
        clip_name = self._edit_list_grid.colindex_get("clip_name")

        edit_list: list[tuple[int, int, str]] = [
            (
                self._edit_list_grid.value_get(row=row_index, col=mark_in),
                self._edit_list_grid.value_get(row=row_index, col=mark_out)
                or self._frame_count,
                self._edit_list_grid.value_get(row=row_index, col=clip_name),
            )
            for row_index in range(self._edit_list_grid.row_count)
        ]

        if edit_list:
            result = popups.PopOptions(
                title="Choose Clip Assembly Method...",
                message="Please Choose How To Assemble Clips",
                options={
                    "As A Single File": "As_A_Single_File",
                    "As Individual Files": "As_Individual_Files",
                },
            ).show()

            match result:
                case "As_Individual_Files":
                    _, filename, extension = file_handler.split_file_path(
                        self._video_file_input[0].video_path
                    )

                    assembled_file = file_handler.file_join(
                        self._edit_folder, f"{filename}_", extension
                    )

                    video_data = []

                    with qtg.sys_cursor(qtg.Cursor.hourglass):
                        result, video_files_string = self._cut_video_with_editlist(
                            input_file=self._video_file_input[0].video_path,
                            output_file=assembled_file,
                            edit_list=edit_list,
                            cut_out=False,
                        )

                        if (
                            result == -1
                        ):  # video_files_string is the error message and not the ',' delimitered file list
                            popups.PopError(
                                title="Error Cutting File...",
                                message=f"<{video_files_string}>",
                            ).show()
                        else:
                            for video_file_path in video_files_string.split(","):
                                (
                                    video_path,
                                    video_file,
                                    video_extension,
                                ) = file_handler.split_file_path(video_file_path)

                                video_file_settings = Video_File_Settings()

                                result, encoding_info = self._get_encoding_info(
                                    video_file_path
                                )

                                if result == -1:
                                    return None

                                if self._db_settings.setting_exist("vf_denoise"):
                                    video_file_settings.denoise = (
                                        self._db_settings.setting_get("vf_denoise")
                                    )

                                if self._db_settings.setting_exist("vf_white_balance"):
                                    video_file_settings.white_balance = (
                                        self._db_settings.setting_get(
                                            "vf_white_balance"
                                        )
                                    )

                                if self._db_settings.setting_exist("vf_sharpen"):
                                    video_file_settings.sharpen = (
                                        self._db_settings.setting_get("vf_sharpen")
                                    )

                                if self._db_settings.setting_exist("vf_auto_levels"):
                                    video_file_settings.auto_bright = (
                                        self._db_settings.setting_get("vf_auto_levels")
                                    )

                                video_file_settings.button_title = (
                                    file_handler.extract_title(video_file)
                                )

                                video_data.append(
                                    Video_Data(
                                        video_folder=video_path,
                                        video_file=video_file,
                                        video_extension=video_extension,
                                        encoding_info=encoding_info,
                                        video_file_settings=video_file_settings,
                                    )
                                )
                    if video_data:
                        result = File_Renamer_Popup(
                            video_data_list=video_data, container_tag="file_renamer"
                        ).show()

                        for video_file in video_data:
                            self._video_file_input.append(video_file)

                        self.processed_files_callback(self._video_file_input)

                case "As_A_Single_File":
                    _, filename, extension = file_handler.split_file_path(
                        self._video_file_input[0].video_path
                    )

                    assembled_file = file_handler.file_join(
                        self._edit_folder, f"{filename}_assembled", extension
                    )

                    with qtg.sys_cursor(qtg.Cursor.hourglass):
                        result, video_files_string = self._cut_video_with_editlist(
                            input_file=self._video_file_input[0].video_path,
                            output_file=assembled_file,
                            edit_list=edit_list,
                            cut_out=False,
                        )

                        if (
                            result == -1
                        ):  # video_files_string is the error message and not the ',' delimitered file list
                            popups.PopError(
                                title="Error Cutting File...",
                                message=f"<{video_files_string}>",
                            ).show()
                        else:
                            result, message = dvdarch_utils.Concatenate_Videos(
                                temp_files=video_files_string.split(","),
                                output_file=assembled_file,
                                delete_temp_files=True,
                            )

                            if result == -1:
                                popups.PopError(
                                    title="Error Concatenating Files...",
                                    message=f"<{message}>",
                                ).show()

                                return None

                            (
                                assembled_path,
                                assembled_filename,
                                assembled_extension,
                            ) = file_handler.split_file_path(assembled_file)

                            result, encoding_info = self._get_encoding_info(
                                assembled_file
                            )

                            if result == -1:
                                return None

                            self._video_file_input.append(
                                Video_Data(
                                    video_folder=assembled_path,
                                    video_file=assembled_filename,
                                    video_extension=assembled_extension,
                                    encoding_info=encoding_info,
                                    video_file_settings=self._video_file_input[
                                        0
                                    ].video_file_settings,
                                )
                            )
                            self.processed_files_callback(self._video_file_input)
                case _:
                    popups.PopMessage(
                        title="No Assembly Method Selected...",
                        message="No Output As No Assembly Method Selected!",
                    ).show()
        else:
            popups.PopMessage(
                title="No Entries In The Edit List...",
                message="Please Mark Edit List Entries With The [ and ] Button!",
            ).show()

    def _cut_video_with_editlist(
        self,
        input_file: str,
        output_file: str,
        edit_list: list[tuple[int, int, str]],
        cut_out: bool = True,
    ) -> tuple[int, str]:
        """
        Cuts a video file based on a given edit list of start and end frames.

        Args:
            input_file (str): Path of the input video file.
            output_file (str): Path of the output video file.
            edit_list (list[tuple[int, int, str]]): List of tuples containing start, end frames and clip name of each segment to cut.
            cut_out (bool, optional): Whether to cut out the edit points of the video. Defaults to True.

        Returns:
            tuple[int, str]: A tuple containing the following elements:
            - If the operation was successful:
                - arg 1 (int): 1
                - arg 2 (str): If cut_out is True, the path of the output video file;
                if cut_out is False, a ',' delimited string of output file paths.
            - If the operation failed:
                - arg 1 (int): -1
                - arg 2 (str): An error message.
        """
        # Used for background task information
        global gi_task_error_code
        global gi_thread_status
        global gs_thread_error_message
        global gs_task_error_message
        global gs_thread_status
        global gs_thread_message
        global gs_thread_output
        global gs_thread_task_name

        global gb_task_errored
        global gi_tasks_completed

        # ===== Helper

        def transform_cut_in_to_cut_out(
            edit_list: list[tuple[int, int, str]], frame_count: int
        ) -> list[tuple[int, int, str]]:
            """
            Transforms a list of cut in points to cut out points.

            Args:
                edit_list (list[Tuple[int, int, str]]): A list of tuples representing the cut in & cut out points and
                    clip name of a video.
                frame_count (int): The total number of frames in the video.

            Returns:
                list[tuple[int, int]]: A list of tuples representing the cut in/out points and cut name of the video.

            """
            assert isinstance(
                edit_list, list
            ), f"{edit_list=}. Must be a list of tuples"
            assert edit_list, f"{edit_list=}. Must not be empty"
            assert all(isinstance(x, tuple) and len(x) == 3 for x in edit_list), (
                f"{edit_list=}. Must contain tuples of size 3"
                " [start_frame, end_frame, cut name]"
            )
            assert (
                isinstance(frame_count, int) and frame_count >= 0
            ), f"{frame_count=}. Must be an int >= 0"

            assert all(
                start_frame < end_frame for start_frame, end_frame, _ in edit_list
            ), "start_frame must be less than end_frame in every tuple of edit_list"
            prev_start = 0
            cut_out_list = []

            for cut_index, (start_frame, end_frame, clip_name) in enumerate(edit_list):
                if start_frame != end_frame:
                    new_tuple = (prev_start, start_frame, clip_name)
                    cut_out_list.append(new_tuple)
                prev_start = end_frame

                # Check for overlapping frames between consecutive tuples
                # Note: We consider it an overlap if tuple overlap within 0.5 seconds!
                if cut_index < len(edit_list) - 1:
                    _, next_start_frame, clip_name = edit_list[cut_index + 1]
                    if (
                        next_start_frame
                        <= end_frame
                        <= next_start_frame + (self._frame_rate // 2)
                    ):
                        # merge the two tuples into a single tuple
                        cut_out_list[-1] = (
                            cut_out_list[-1][0],
                            next_start_frame,
                            clip_name,
                        )

            # add the last tuple if needed
            if prev_start != frame_count:
                cut_out_list.append((prev_start, frame_count, ""))

            return cut_out_list

        # ===== Main
        assert isinstance(input_file, str), f"{input_file=}. Must be str"
        assert isinstance(output_file, str), f"{output_file=} must be str"
        assert isinstance(edit_list, list), f"{edit_list=}. Must be a list"
        assert all(
            isinstance(edit, tuple) for edit in edit_list
        ), "Each edit in edit_list must be a tuple"
        assert all(len(edit) == 3 for edit in edit_list), (
            "Each edit tuple in edit_list must have exactly three elements (start"
            " frame, end frame, cut name)"
        )
        assert all(
            isinstance(edit[0], int) for edit in edit_list
        ), "The start frame in each edit tuple must be an integer"
        assert all(
            isinstance(edit[1], int) for edit in edit_list
        ), "The end frame in each edit tuple must be an integer"
        assert isinstance(cut_out, bool), f"{cut_out=}. Must be a bool"

        file_handler = file_utils.File()

        for edit_tuple in edit_list:
            if edit_tuple[2] != "" and not file_handler.filename_validate(
                edit_tuple[2]
            ):
                return (
                    -1,
                    (
                        "Invalid Clip"
                        f" Name:{sys_consts.SDELIM}{edit_tuple[2]}{sys_consts.SDELIM}!"
                    ),
                )

        out_path, out_file, out_extn = file_handler.split_file_path(output_file)

        temp_files = []

        if cut_out:
            edit_list = transform_cut_in_to_cut_out(
                edit_list=edit_list, frame_count=self._frame_count
            )

        self._progress_bar.range_set(0, len(edit_list))
        self._progress_bar.value_set(len(edit_list))

        task_list = []
        for cut_index, (start_frame, end_frame, clip_name) in enumerate(edit_list):
            if end_frame - start_frame <= 0:  # Probably should not happen
                continue

            if clip_name.strip() != "":
                out_file = clip_name
            else:
                out_file = f"{file_handler.extract_title(out_file)}_{cut_index:03d}"

            if cut_out:
                temp_file = file_handler.file_join(
                    out_path,
                    f"{out_file}({cut_index})",
                    out_extn,
                )
            else:
                temp_file = file_handler.file_join(
                    out_path,
                    out_file,
                    out_extn,
                )

            temp_files.append(temp_file)

            if file_handler.file_exists(temp_file):
                result = file_handler.remove_file(temp_file)

                if result == -1:
                    return (
                        -1,
                        (
                            "Failed To Remove"
                            f" {sys_consts.SDELIM}{temp_file}{sys_consts.SDELIM}"
                        ),
                    )

            cut_def = dvdarch_utils.Cut_Video_Def(
                input_file=input_file,
                output_file=temp_file,
                start_cut=start_frame,
                end_cut=end_frame,
                frame_rate=self._frame_rate,
                tag=str(cut_index),
            )

            task_list.append((cut_index, cut_def))

        tasks_submitted = 0
        run_in_background = False

        # Cut_Video is a resource hog and running in the background actually yields worse performance on my dev computer
        # TODO revist when Cut_Video adresses the resource issue
        if run_in_background:
            for task_tuple in task_list:
                self._background_task_manager.add_task(
                    name=f"cut_video_{task_tuple[0]}",
                    method=Run_Video_Cuts,
                    arguments=(task_tuple[1],),
                    callback=Notification_Call_Back,
                )
                tasks_submitted += 1

            current_task = 0
            gi_tasks_completed = 0
            while gi_tasks_completed < tasks_submitted:
                if bool(gb_task_errored):
                    self._progress_bar.reset()
                    error_str = (
                        f" {gi_tasks_completed=}, {gi_task_error_code=},"
                        f" {gi_thread_status=}, {gs_thread_message=},"
                        f" {gs_thread_output=}, {gs_task_error_message=},"
                        f" {gs_thread_task_name=}"
                    )

                    return -1, str(f"Cut Video Failed: {error_str}")

                if current_task != gi_tasks_completed:
                    current_task = gi_tasks_completed
                    self._progress_bar.value_set(tasks_submitted - current_task)
        else:
            self._progress_bar.value_set(tasks_submitted)
            tasks_submitted = len(task_list)
            task_index = tasks_submitted

            for task_tuple in task_list:
                self._progress_bar.value_set(task_index)
                task_index -= 1

                task_error_code, task_error_message = dvdarch_utils.Cut_Video(
                    cut_video_def=task_tuple[1]
                )

                if task_error_code == -1:
                    self._progress_bar.reset()
                    return -1, task_error_message

        self._progress_bar.reset()

        if cut_out:  # Concat temp file for final file and remove the temp files
            result, message = dvdarch_utils.Concatenate_Videos(
                temp_files=temp_files,
                output_file=output_file,
                delete_temp_files=True,
                debug=False,
            )

            if result == -1:
                return -1, message

        else:
            # We keep the temp files, as they are the new videos, and build an output file str where each video is
            # delimitered by a ','
            output_file = ",".join(temp_files)

        return 1, output_file

    def _delete_segments(self, event: qtg.Action) -> None:
        """
        Deletes the specified segments from the input file.

        Args:
            event (qtg.Action): The event that triggered this method.

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be type qtg.Action"

        dvd_menu_title = self._menu_title.value_get()
        file_handler = file_utils.File()

        mark_in = self._edit_list_grid.colindex_get("mark_in")
        mark_out = self._edit_list_grid.colindex_get("mark_out")
        clip_name = self._edit_list_grid.colindex_get("clip_name")

        edit_list = [
            (
                self._edit_list_grid.value_get(row=row_index, col=mark_in),
                self._edit_list_grid.value_get(row=row_index, col=mark_out)
                or self._frame_count,
                self._edit_list_grid.value_get(row=row_index, col=clip_name),
            )
            for row_index in range(self._edit_list_grid.row_count)
        ]

        if edit_list:
            if (
                popups.PopYesNo(
                    title="Cut Edit Points...", message="Cut Edit Points From File?"
                ).show()
                == "yes"
            ):
                _, filename, extension = file_handler.split_file_path(
                    self._video_file_input[0].video_path
                )

                if dvd_menu_title.strip() == "":
                    dvd_menu_title = filename

                output_file = file_handler.file_join(
                    self._edit_folder, f"{dvd_menu_title}_cut", extension
                )

                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    result, trimmed_file = self._cut_video_with_editlist(
                        input_file=self._video_file_input[0].video_path,
                        output_file=output_file,
                        edit_list=edit_list,
                    )

                    if (
                        result == -1
                    ):  # trimmed file is the error message and not the file name
                        popups.PopError(
                            title="Error Cutting File...",
                            message=f"<{trimmed_file}>",
                        ).show()
                    else:
                        (
                            trimmed_path,
                            trimmed_filename,
                            trimmed_extension,
                        ) = file_handler.split_file_path(trimmed_file)

                        trimmed_video = Video_Data(
                            video_folder=trimmed_path,
                            video_file=trimmed_filename,
                            video_extension=trimmed_extension,
                            encoding_info=dvdarch_utils.Get_File_Encoding_Info(
                                trimmed_file
                            ),
                            video_file_settings=self._video_file_input[
                                0
                            ].video_file_settings,
                        )
                        self._video_file_input.append(trimmed_video)
                        self.processed_files_callback(self._video_file_input)
        else:
            popups.PopMessage(
                title="No Entries In The Edit List...",
                message="Please Mark Some Edit List Entries With The [ and ] Button!",
            ).show()

    def _edit_list_seek(self, event: qtg.Action) -> None:
        """
        Seeks on a frame number from the edit list when mark_in or mark_out is clicked

        Args:
            event (qtg.Action): The event that triggered this method.

        """
        grid_col_value: qtg.Grid_Col_Value = event.value

        assert isinstance(
            grid_col_value, qtg.Grid_Col_Value
        ), f"{grid_col_value=} must be a qtg.Grid_Col_Value"

        if grid_col_value.value is None or not isinstance(grid_col_value.value, int):
            return None

        clicked_frame = int(grid_col_value.value)

        if clicked_frame < 0:
            self._video_handler.seek(0)
        elif clicked_frame >= self._frame_count:
            self._video_handler.seek(self._frame_count - 1)  # frame count is zero based
        else:
            self._video_handler.seek(clicked_frame)

    def _remove_edit_points(self, event: qtg.Action) -> None:
        """
        Remove checked edit points from a grid widget.

        Args:
            event (qtg.Action): The triggering event

        Raises:
            AssertionError: If the event parameter is not of type qtg.Action


        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)}"

        if (
            self._edit_list_grid.row_count > 0
            and self._edit_list_grid.checkitems_get
            and popups.PopYesNo(
                title="Remove Checked...", message="Remove the Checked Edit Points?"
            ).show()
            == "yes"
        ):
            for item in reversed(self._edit_list_grid.checkitems_get):
                self._edit_list_grid.row_delete(item.row_index)

            if self._edit_list_grid.row_count == 0:
                self._selection_button_toggle(event=event, init=True)

    def _media_status_change(self, media_status: str) -> None:
        """When the status of the media player changes this methodis called.
        Args:
            media_status (str): The status of the media player
        """
        match media_status:
            case "end_of_media":
                self._video_slider.value_set(0)
                self._video_handler.pause()
            case "invalid_media":
                popups.PopMessage(
                    title="Media Playback Error...",
                    message="Can Not Play/Edit Files Of This Type!",
                ).show()
                # TODO Offer to transcode

    def _move_edit_point(self, up: bool) -> None:
        """
        Move the selected edit point up or down in the edit list grid.

        Args:
            up (bool): True to move the edit point up, False to move it down.

        """
        assert isinstance(up, bool), f"{up=}. Must be bool"

        checked_items: tuple[qtg.Grid_Item] = (
            self._edit_list_grid.checkitems_get
            if up
            else tuple(reversed(self._edit_list_grid.checkitems_get))
        )

        assert all(
            isinstance(item, qtg.Grid_Item) for item in checked_items
        ), f"{checked_items=}. Must be a list of'qtg.Grid_Item_Tuple'"

        if not checked_items:
            popups.PopMessage(
                title="Select An Edit Point...",
                message="Please Check An Edit Point To Move!",
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
                title="Selected Edit Points Not Contiguous...",
                message="Selected Edit Points Must Be A Contiguous Block!",
            ).show()
            return None

        for checked_item in checked_items:
            if up:
                if checked_item.row_index == 0:
                    break
            else:
                if checked_item.row_index == self._edit_list_grid.row_count - 1:
                    break

            self._edit_list_grid.checkitemrow_set(False, checked_item.row_index, 0)
            self._edit_list_grid.select_row(checked_item.row_index)

            if up:
                new_row = self._edit_list_grid.move_row_up(checked_item.row_index)
            else:
                new_row = self._edit_list_grid.move_row_down(checked_item.row_index)

            if new_row >= 0:
                self._edit_list_grid.checkitemrow_set(True, new_row, 0)
                self._edit_list_grid.select_col(new_row, 0)
            else:
                self._edit_list_grid.checkitemrow_set(True, checked_item.row_index, 0)
                self._edit_list_grid.select_col(checked_item.row_index, 0)

    def _frame_handler(self, frame: qtG.QPixmap) -> None:
        """Handles displaying the video frame
        Args:
            frame (qtG.QPixmap): THe video frame to be displayed
        """
        self._video_display.guiwidget_get.setPixmap(
            frame.scaled(
                self.display_width, self.display_height, qtC.Qt.KeepAspectRatio
            )
        )

    def _populate_edit_cuts(
        self,
        edit_cuts: tuple[tuple[int, int, str], ...] | list[tuple[int, int, str], ...],
    ):
        assert isinstance(
            edit_cuts, (list, tuple)
        ), f"{edit_cuts=}. Must be a list or tuple"
        for edit_cut in edit_cuts:
            assert len(edit_cut) == 3, f"{edit_cut=}. Must be (int,int,str)"
            assert isinstance(edit_cut[0], int), f"{edit_cut[0]=}. Must be int"
            assert isinstance(edit_cut[1], int), f"{edit_cut[1]=}. Must be int"
            assert isinstance(edit_cut[2], str), f"{edit_cut[2]=}. Must be str"

        self._edit_list_grid.clear()

        mark_in = self._edit_list_grid.colindex_get("mark_in")
        mark_out = self._edit_list_grid.colindex_get("mark_out")
        clip_name = self._edit_list_grid.colindex_get("clip_name")

        for row, cut_tuple in enumerate(edit_cuts):
            self._edit_list_grid.value_set(
                row=row, col=mark_in, value=cut_tuple[0], user_data=cut_tuple
            )

            self._edit_list_grid.value_set(
                row=row, col=mark_out, value=cut_tuple[1], user_data=cut_tuple
            )

            self._edit_list_grid.value_set(
                row=row, col=clip_name, value=cut_tuple[2], user_data=cut_tuple
            )
        self._edit_list_grid.select_row(0, clip_name)

        return None

    def _position_changed(self, frame: int) -> None:
        """
        A method that is called when the position of the media player changes.
        Converts the current position in milliseconds to the corresponding frame number,
        updates the video slider if necessary, and emits a signal indicating that the position has changed.
        Args:
            frame (int): The current-media player frame.
        """
        self._sliding = True

        if self._video_slider is not None:
            # Want slider to update position without telling the world - so block signals.
            self._video_slider.value_set(frame, block_signals=True)

        self._frame_display.value_set(frame)

    def _seek(self, frame: int) -> None:
        """
        The _seek function seeks to that frame in the video handler.

        Args:
            frame: int: Set the current frame to a specific value

        Returns:
            None

        Doc Author:
            Trelent
        """
        self._current_frame = frame
        self._video_handler.seek(frame)

    def _selection_end(self, event: qtg.Action) -> None:
        """Handler method for selecting the end of a media clip.

        Args:
            event (qtg.Action): The triggering event

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"
        assert hasattr(self, "_video_handler"), "Media source not set"

        frame = self._video_handler.current_frame()
        end_time = dvdarch_utils.Frame_Num_To_FFMPEG_Time(frame, self._frame_rate)

        if self._edit_list_grid.row_count <= 0:
            return None

        current_row = self._edit_list_grid.row_count - 1

        start_frame = self._edit_list_grid.value_get(row=current_row, col=0)

        if start_frame >= frame:
            popups.PopMessage(
                title="Invalid End Select...",
                message="End Frame Must Be Greater Than The Start Frame!",
            ).show()
        else:
            self._edit_list_grid.value_set(
                row=current_row, col=1, value=frame, user_data=end_time
            )
            self._selection_button_toggle(event=event)

    def _selection_start(self, event: qtg.Action) -> None:
        """Handler method for selecting the start of a media clip.

        Args:
            event (qtg.Action): The triggering event

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"
        assert hasattr(self, "_video_handler"), "Media source not set"

        frame = self._video_handler.current_frame()

        start_time = dvdarch_utils.Frame_Num_To_FFMPEG_Time(frame, self._frame_rate)

        new_row = self._edit_list_grid.row_count + 1

        self._edit_list_grid.value_set(
            row=new_row, col=0, value=frame, user_data=start_time
        )
        self._selection_button_toggle(event=event)

    def _selection_button_toggle(self, event: qtg.Action, init=False) -> None:
        """Toggles the state of the selection buttons for selecting the start and end of a media clip.

        Args:
            event (qtg.Action): The triggering event
            init (bool): True if initialising the button state fo first use, otherwise false

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"
        select_start: qtg.Button = cast(
            qtg.Button,
            event.widget_get(container_tag="video_buttons", tag="selection_start"),
        )
        select_end: qtg.Button = cast(
            qtg.Button,
            event.widget_get(container_tag="video_buttons", tag="selection_end"),
        )

        if init:  # Initial button state
            select_start.enable_set(True)
            select_end.enable_set(False)
        else:
            if select_start.enable_get:
                select_start.enable_set(False)
                select_end.enable_set(True)
            elif select_end.enable_get:
                select_start.enable_set(True)
                select_end.enable_set(False)
            else:
                select_start.enable_set(True)
                select_end.enable_set(False)

    def _step_backward(self) -> None:
        """
        Seeks the media source backwards by `_step_value` frames.
        This function first calculates the frame to seek to by subtracting `_step_value` frames from the current frame.
        If the calculated frame is within the bounds of the media source, the media source is paused and seeks to the calculated frame.
        If the calculated frame is less than 0, the media source is seeked to frame 0 instead.
        Args:
            None.
        Returns:
            None.
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            seek_frame = self._video_handler.current_frame() - self._step_value
            if seek_frame < 0:
                seek_frame = 0

            if 0 <= seek_frame < self._frame_count:
                self._video_handler.pause()
                self._video_handler.seek(seek_frame)

    def _step_forward(self) -> None:
        """
        Seeks the media source forwards by `_step_value` frames.
        This method first calculates the frame to seek to by adding `_step_value` frames to the current frame.
        If the calculated frame is within the bounds of the media source, the media source is paused and seeks to the calculated frame.
        If the calculated frame is greater than or equal to the total number of frames, the media source is seeked to the final frame instead.
        Args:
            None.
        Returns:
            None.
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            seek_frame = self._video_handler.current_frame() + self._step_value

            if seek_frame >= self._frame_count:
                seek_frame = self._frame_count - 1

            if 0 <= seek_frame < self._frame_count:
                self._video_handler.pause()
                self._video_handler.seek(seek_frame)

    def _step_unit(self, event: qtg.Action) -> None:
        """
        Sets the value of `self._step_value` based on the value of the `event` argument.
        Args:
            event (qtg.Action): The triggering event
        Returns:
            None.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"

        if event.widget_exist(container_tag=event.container_tag, tag=event.tag):
            value: qtg.Combo_Data = event.value_get(
                container_tag=event.container_tag, tag=event.tag
            )

            step_values = {
                "frame": 1,
                "0.5s": self._frame_rate // 2,
                "1s": int(self._frame_rate),
                "15s": int(self._frame_rate * 15),
                "30s": int(self._frame_rate * 30),
                "60s": int(self._frame_rate * 60),
                "300s": int(self._frame_rate * 300),
            }
            self._step_value = step_values[value.data]

    def _video_file_system_maker(self) -> int:
        """
        Create the necessary folders for video processing, and checks if the input file exists.

        Returns:
            int : 1 OK, -1 error occurred


        Side effects:
            Creates folders as necessary for the video processing task.

        """
        file_handler = file_utils.File()

        if not file_handler.path_exists(self._output_folder):
            file_handler.make_dir(self._output_folder)

        if file_handler.path_exists(self._output_folder):
            self._output_folder = file_handler.file_join(
                self._output_folder, utils.Text_To_File_Name(self._project_name)
            )
            file_handler.make_dir(self._output_folder)

        if not file_handler.path_exists(self._output_folder):
            popups.PopError(
                title="Video Output Folder Does Not Exist",
                message=(
                    "The output folder"
                    f" {sys_consts.SDELIM}'{self._output_folder}'{sys_consts.SDELIM} does"
                    " not exist. Please create the folder and try again."
                ),
            ).show()

            return -1

        self._edit_folder = file_handler.file_join(
            self._output_folder, sys_consts.EDIT_FOLDER
        )

        if self._video_file_input and not file_handler.file_exists(
            self._video_file_input[0].video_path
        ):
            # This should never happen, unless dev error or mount/drive problems
            popups.PopError(
                title="Video File Does Not Exist",
                message=(
                    "The input video file"
                    f" {sys_consts.SDELIM}'{self._video_file_input[0].video_path}'{sys_consts.SDELIM} does"
                    " not exist. Please ensure the file exists and try again."
                ),
            ).show()
            return -1

        if not file_handler.path_writeable(self._output_folder):
            popups.PopError(
                title="Video Output Folder Write Error",
                message=(
                    "The output folder"
                    f" {sys_consts.SDELIM}'{self._output_folder}'{sys_consts.SDELIM} is"
                    " not writeable. Please ensure you have write permissions for the"
                    " folder and try again."
                ),
            ).show()
            return -1

        if not file_handler.path_exists(self._edit_folder):
            if file_handler.make_dir(self._edit_folder) == -1:
                popups.PopError(
                    title="Video Edit Folder Creation Error",
                    message=(
                        "Failed to create the video edit folder"
                        f" {sys_consts.SDELIM}'{self._edit_folder}'.{sys_consts.SDELIM} Please"
                        " ensure you have write permissions for the folder and try"
                        " again."
                    ),
                ).show()
                return -1

        self._transcode_folder = file_handler.file_join(
            self._output_folder, sys_consts.TRANSCODE_FOLDER
        )

        if not file_handler.path_exists(self._transcode_folder):
            if file_handler.make_dir(self._transcode_folder) == -1:
                popups.PopError(
                    title="Video Transcode Folder Creation Error",
                    message=(
                        "Failed to create the video transcode folder"
                        f" {sys_consts.SDELIM}'{self._transcode_folder}'.{sys_consts.SDELIM} Please"
                        " ensure you have write permissions for the folder and try"
                        " again."
                    ),
                ).show()

                return -1

        self._file_system_init = True

        return 1

    def layout(self) -> qtg.VBoxContainer:
        def assemble_video_cutter_container() -> qtg.VBoxContainer:
            """
            The function assembles the video cutter container.

            Args:

            Returns:
                qtg.VBoxContainer: A vboxcontainer housing the video cutter

            """
            step_unit_list = [
                qtg.Combo_Item(
                    display="Frame", data="frame", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="0.5 Sec", data="0.5s", icon=None, user_data=None
                ),
                qtg.Combo_Item(display="1   Sec", data="1s", icon=None, user_data=None),
                qtg.Combo_Item(
                    display="15  Sec", data="15s", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="30  Sec", data="30s", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="1   Min", data="60s", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="5   Min", data="300s", icon=None, user_data=None
                ),
            ]

            self._video_display = qtg.Label(
                width=self.display_width, height=self.display_height, pixel_unit=True
            )

            self._menu_frame = qtg.LineEdit(
                tag="menu_frame",
                width=6,
                height=1,
                char_length=6,
                callback=self.event_handler,
                editable=False,
                buddy_control=qtg.Button(
                    tag="clear_menu_frame",
                    height=1,
                    width=1,
                    callback=self.event_handler,
                    icon=file_utils.App_Path("x.svg"),
                    tooltip="Clear The DVD Menu Button Image",
                ),
            )

            self._frame_display = qtg.LCD(
                tag="frame_display",
                label="Frame",
                width=6,
                height=1,
                txt_fontsize=14,
            )

            video_button_container = qtg.HBoxContainer(
                tag="video_buttons", align=qtg.Align.CENTER
            ).add_row(
                qtg.HBoxContainer().add_row(
                    qtg.Button(
                        tag="selection_start",
                        icon=file_utils.App_Path("bracket-left.svg"),
                        callback=self.event_handler,
                        tooltip="Mark In Edit Point",
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="selection_end",
                        icon=file_utils.App_Path("bracket-right.svg"),
                        callback=self.event_handler,
                        tooltip="Mark Out Edit Point",
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="backward",
                        tooltip="Step Back",
                        icon=qtg.Sys_Icon.mediaprevious.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                        auto_repeat_interval=200,
                    ),
                    qtg.Button(
                        tag="play",
                        tooltip="Play",
                        icon=qtg.Sys_Icon.mediaplay.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="forward",
                        tooltip="Step Forward",
                        icon=qtg.Sys_Icon.medianext.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                        auto_repeat_interval=200,
                    ),
                    # qtg.Spacer(width=1),
                    qtg.Button(
                        tag="pause",
                        tooltip="Pause Play",
                        icon=qtg.Sys_Icon.mediapause.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                    ),
                    # qtg.Spacer(width=1),
                    qtg.ComboBox(
                        tag="step_unit",
                        tooltip="Choose The Step Unit",
                        label="Step",
                        width=10,
                        callback=self.event_handler,
                        items=step_unit_list,
                        display_na=False,
                        translate=False,
                    ),
                    self._frame_display,
                    qtg.Button(
                        tag="set_menu_image",
                        icon=file_utils.App_Path("camera.svg"),
                        tooltip="Set The DVD Menu Button Image",
                        callback=self.event_handler,
                        height=1,
                        width=2,
                    ),
                    self._menu_frame,
                )
            )

            self._video_slider = qtg.Slider(
                tag="video_slider",
                width=self.display_width,
                height=15,
                callback=self.event_handler,
                range_max=1,
                range_min=0,
                pixel_unit=True,
                single_step=1,
            )

            self._source_file_label = qtg.Label(
                tag="source_file",
                label="Source:",
                width=80,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.Frame_Style.PANEL,
                    frame=qtg.Frame.SUNKEN,
                    line_width=2,
                ),
                translate=False,
            )

            video_cutter_container = qtg.VBoxContainer(
                tag="video_cutter",
                text="Video Cutter",
                align=qtg.Align.CENTER,
            ).add_row(
                self._video_display,
                self._video_slider,
                video_button_container,
                self._source_file_label,
            )

            return video_cutter_container

        def assemble_edit_list_container() -> qtg.VBoxContainer:
            """
            Create a VBoxContainer containing the editing list.

            Returns:
                qtg.FormContainer: A form container that houses the edit list.
            """
            edit_list_cols = [
                qtg.Col_Def(
                    tag="mark_in",
                    label="Frame In",
                    width=10,
                    editable=False,
                    checkable=True,
                ),
                qtg.Col_Def(
                    tag="mark_out",
                    label="Frame Out",
                    width=10,
                    editable=False,
                    checkable=False,
                ),
                qtg.Col_Def(
                    tag="clip_name",
                    label="Clip Name",
                    width=10,
                    editable=True,
                    checkable=False,
                ),
            ]

            self._edit_list_grid = qtg.Grid(
                tag="edit_list_grid",
                height=self.display_height - 50,
                col_def=edit_list_cols,
                pixel_unit=True,
                callback=self.event_handler,
                header_sort=False,
                noselection=True,
            )

            edit_list_buttons = qtg.HBoxContainer(align=qtg.Align.BOTTOMCENTER).add_row(
                qtg.Button(
                    icon=file_utils.App_Path("film.svg"),
                    tag="assemble_segments",
                    callback=self.event_handler,
                    tooltip="Assemble Edit Points Into New Videos",
                    width=2,
                ),
                qtg.Button(
                    icon=file_utils.App_Path("scissors.svg"),
                    tag="delete_segments",
                    callback=self.event_handler,
                    tooltip="Delete Edit Points From Video",
                    width=2,
                ),
                qtg.Spacer(width=5),
                qtg.Button(
                    icon=file_utils.App_Path("x.svg"),
                    tag="remove_edit_points",
                    callback=self.event_handler,
                    tooltip="Delete Edit Points From Edit List",
                    width=2,
                ),
                qtg.Button(
                    icon=file_utils.App_Path("arrow-up.svg"),
                    tag="move_edit_point_up",
                    callback=self.event_handler,
                    tooltip="Move This Edit Point Up!",
                    width=2,
                ),
                qtg.Button(
                    icon=file_utils.App_Path("arrow-down.svg"),
                    tag="move_edit_point_down",
                    callback=self.event_handler,
                    tooltip="Move This Edit Point Down!",
                    width=2,
                ),
            )

            self._progress_bar = qtg.ProgressBar(
                tag="file_progress",
                tooltip="Displays % Completion Of File Operations",
                buddy_control=qtg.Label(
                    text="To Cut",
                    width=6,
                ),
            )

            self._all_projects_rb = qtg.RadioButton(
                text="All Projects",
                tag="all_projects",
                tooltip="File Edit List Is Visible To All Projects ",
                checked=True,
                callback=self.event_handler,
            )
            self._this_project_rb = qtg.RadioButton(
                text="This Project Only",
                tag="this_project",
                tooltip="File Edit List Is Only Visible To This Project ",
                callback=self.event_handler,
            )

            edit_list_visibility = qtg.HBoxContainer(
                align=qtg.Align.BOTTOMCENTER, text="Visible To"
            ).add_row(
                self._all_projects_rb,
                self._this_project_rb,
            )

            edit_file_list = qtg.VBoxContainer(align=qtg.Align.TOPLEFT).add_row(
                edit_list_visibility,
                qtg.HBoxContainer(margin_left=4).add_row(
                    qtg.Checkbox(
                        text="Select All",
                        tag="bulk_select",
                        callback=self.event_handler,
                        tooltip="Select All Edit Points",
                        width=11,
                    ),
                    qtg.Spacer(width=5, tune_hsize=-14),
                    self._progress_bar,
                ),
                qtg.VBoxContainer(align=qtg.Align.BOTTOMRIGHT).add_row(
                    self._edit_list_grid,
                    edit_list_buttons,
                ),
            )

            edit_list_container = qtg.VBoxContainer(
                tag="edit_list",
                text="Edit List",
                align=qtg.Align.LEFT,
            ).add_row(edit_file_list)

            return edit_list_container

        # ===== Main
        self._video_filter_container = qtg.HBoxContainer(
            text="Video Filters", tag="video_filters"
        ).add_row(
            qtg.Checkbox(
                tag="normalise",
                text="Normalise",
                checked=True,
                tooltip="Bring Out Shadow Details",
            ),
            qtg.Checkbox(
                tag="denoise",
                text="Denoise",
                checked=True,
                tooltip="Lightly Reduce Video Noise",
            ),
            qtg.Checkbox(
                tag="white_balance",
                text="White Balance",
                checked=True,
                tooltip="Fix White Balance Problems",
                width=16,
            ),
            qtg.Checkbox(
                tag="sharpen",
                text="Sharpen",
                checked=True,
                tooltip="Lightly Sharpen Video",
            ),
            qtg.Checkbox(
                tag="auto_levels",
                text="Auto Levels",
                checked=True,
                tooltip="Improve Exposure",
            ),
        )

        self._video_editor = qtg.HBoxContainer(margin_left=0).add_row(
            assemble_video_cutter_container(), assemble_edit_list_container()
        )

        self._menu_title = qtg.LineEdit(
            tag="menu_title",
            char_length=40,
            width=40,
            translate=False,
        )

        dvd_settings = qtg.HBoxContainer().add_row(
            qtg.HBoxContainer(text="Menu Title").add_row(self._menu_title),
            qtg.Spacer(width=5),
            self._video_filter_container,
            qtg.Spacer(width=4),
        )

        video_controls_container = qtg.VBoxContainer(align=qtg.Align.LEFT).add_row(
            qtg.HBoxContainer(
                tag="dvd_settings", text="DVD Settings", margin_left=10
            ).add_row(
                dvd_settings,
            ),
            self._video_editor,
        )

        return video_controls_container
