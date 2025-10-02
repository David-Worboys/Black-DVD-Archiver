"""
Provides archive management of video artefacts - dvd_image, video source files etc

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

import dataclasses
import inspect
import os
from datetime import datetime
from typing import Final, Any, Callable

import dvdarch_utils
import QTPYGUI.file_utils as file_utils
import sys_consts

from break_circular import Task_Def
from dvdarch_utils import Get_File_Encoding_Info
from sys_config import Video_Data
from QTPYGUI.utils import Text_To_File_Name, Get_Unique_Id

from background_task_manager import Task_Dispatcher, Unpack_Result_Tuple

# THe Following constants are used in the archive_dvd_build the method below - changes here mean changes there!
DVD_IMAGE: Final[str] = "dvd_image"
ISO_IMAGE: Final[str] = "iso_image"
VIDEO_SOURCE: Final[str] = "video_source"
ARCHIVE: Final[str] = "archive"
STREAMING: Final[str] = "streaming"  # Used in archival mode only
PRESERVATION_MASTER: Final[str] = "preservation_master"  # Used in archival mode only
MISC: Final[str] = "misc"

OP_ARCHIVE: Final[str] = ARCHIVE
OP_STREAMING: Final[str] = STREAMING
OP_TYPE: Final[str] = "type"

TRANSCODE: Final[str] = "transcode"
TRANSCOPY: Final[str] = "trans_copy"
TRANSCODE_PREFIX: Final[str] = "AM_TR"
STREAMING_PREFIX: Final[str] = "AM_ST"
ARCHIVING_PREFIX: Final[str] = "AM_AR"

DEBUG: Final[bool] = False


@dataclasses.dataclass
class Archive_Manager:
    """Manages archiving of video artefacts - dvd_image, video source files etc"""

    archive_folder: str
    streaming_folder: str = ""
    archive_size: str = sys_consts.DVD_ARCHIVE_SIZE
    transcode_type: str = sys_consts.TRANSCODE_NONE

    # Private instance variables
    _error_messages: list[str] = dataclasses.field(default_factory=list)
    _error_message: str = ""
    _error_code: int = -1
    _file_handler: file_utils.File = file_utils.File()
    _backup_folders: tuple[str, ...] = (DVD_IMAGE, ISO_IMAGE, VIDEO_SOURCE, MISC)
    _submitted_tasks: list[Task_Def] = dataclasses.field(default_factory=list)
    _session_id: str = ""

    _streaming_complete: bool = False
    _transcoding_complete: bool = False
    _archiving_complete: bool = False
    _final_report_triggered: bool = False
    _errored: bool = False

    _component_event_handler: Callable = None

    def __post_init__(self) -> None:
        """
        Validates and sets default values for the Archive_Manager instance.

        Ensures that the archive_folder, streaming_folder, archive_size, and
        transcode_type are valid and assigns default values if necessary.
        Creates the folder structure for archiving and initializes error
        messages if folder creation fails.

        """
        assert (
            isinstance(self.archive_folder, str) and self.archive_folder.strip() != ""
        ), f"{self.archive_folder=}. Must Be non-empty str"
        assert isinstance(self.streaming_folder, str), (
            f"{self.streaming_folder=}. Must be str"
        )
        assert isinstance(self.archive_size, str) and self.archive_size in (
            sys_consts.BLUERAY_ARCHIVE_SIZE,
            sys_consts.DVD_ARCHIVE_SIZE,
        ), f"{self.archive_size=}, Must be BLUERAY_ARCHIVE_SIZE | DVD_ARCHIVE_SIZE"

        assert isinstance(self.transcode_type, str) and self.transcode_type in (
            sys_consts.TRANSCODE_NONE,
            sys_consts.TRANSCODE_FFV1ARCHIVAL,
            sys_consts.TRANSCODE_H264,
            sys_consts.TRANSCODE_H265,
        ), (
            f"{self.transcode_type=}, Must be Be TRANSCODE_NONE |"
            " TRANSCODE_FFV1ARCHIVAL | TRANSCODE_H264 | TRANSCODE_H265"
        )

        self._session_id: str = Get_Unique_Id()

        self._reset_new_state()

        if self.streaming_folder.strip() == "":
            self.streaming_folder = self.archive_folder

        error_message = self._make_folder_structure()

        if error_message:
            self._error_messages.append(error_message)
            self._errored = True
            self._error_code = -1

    @property
    def component_event_handler(self) -> Callable:
        """Returns the component_event_handler method

        Returns:
            Callable: The component_event_handler method
        """
        return self._component_event_handler

    @component_event_handler.setter
    def component_event_handler(self, value: Callable) -> None:
        """Sets the component_event_handler method

        Args:
            value (qtg.Label): The system notifications label
        """
        assert isinstance(value, Callable), f"{value=}. Must be an instance of Callable"

        signature = inspect.signature(value)
        parameters = list(signature.parameters.values())

        # Check number of arguments
        assert len(parameters) == 2, f"{value=}. Must have 2 parameters"

        arg_1 = parameters[0]
        arg_2 = parameters[1]

        assert (
            arg_1.annotation is not inspect.Parameter.empty and arg_1.annotation is int
        ), (
            f"First argument '{arg_1.name}' must be annotated as 'int'. Found: {arg_1.annotation}"
        )

        assert (
            arg_2.annotation is not inspect.Parameter.empty and arg_2.annotation is str
        ), (
            f"Second argument '{arg_2.name}' must be annotated as 'str'. Found: {arg_2.annotation}"
        )

        self._component_event_handler = value

    @property
    def get_error(self) -> str:
        """
        Returns the last error message encountered during archive folder creation.

        Returns:
            str: The last error message encountered. Empty string if no errors.
        """
        return self._error_message

    @property
    def get_error_code(self) -> int:
        """
        Returns the last error code encountered during archive folder creation.

        Returns:
            int: The last error code encountered. -1 if no errors.
        """
        return self._error_code

    def _reset_new_state(self) -> None:
        """
        Resets flags and error messages for a new archiving operation.
        """
        self._error_messages = []
        self._errored = False
        self._error_code = 1
        self._error_message = ""
        self._streaming_complete = False
        self._transcoding_complete = False
        self._archiving_complete = False
        self._final_report_triggered = False

        return None

    def _make_folder_structure(self) -> str:
        """
        Makes the archive folder structure

        Returns:
            str : An error message if the folder structure could not be created
        """
        self._error_code = 1

        if not self._file_handler.path_exists(self.archive_folder):
            if self._file_handler.make_dir(self.archive_folder) == -1:
                self._error_message = (
                    "Failed To Create Archive Folder"
                    f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return self._error_message

            now = datetime.now()
            readme_file = self._file_handler.file_join(
                self.archive_folder, "README", "txt"
            )

            try:
                with open(readme_file, "w") as file:
                    file.write(
                        f"{now} \n Video Archive Folder Created By"
                        f"{sys_consts.PROGRAM_NAME} - {sys_consts.VERSION_TAG} \n Do"
                        " Not Delete Folder!"
                    )
            except (FileNotFoundError, PermissionError, IOError) as e:
                self._error_message = (
                    "Failed To Write"
                    f" {sys_consts.SDELIM}{readme_file} {e}{sys_consts.SDELIM} "
                )
                self._error_code = -1

        if not self._file_handler.path_exists(self.streaming_folder):
            if self._file_handler.make_dir(self.streaming_folder) == -1:
                self._error_message = (
                    "Failed To Create Streaming Folder"
                    f" {sys_consts.SDELIM}{self.streaming_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return self._error_message

            now = datetime.now()
            readme_file = self._file_handler.file_join(
                self.streaming_folder, "README", "txt"
            )

            try:
                with open(readme_file, "w") as file:
                    file.write(
                        f"{now} \n Video Streaming Folder Created By"
                        f"{sys_consts.PROGRAM_NAME} - {sys_consts.VERSION_TAG} \n Do"
                        " Not Delete Folder!"
                    )
            except (FileNotFoundError, PermissionError, IOError) as e:
                self._error_message = (
                    "Failed To Write"
                    f" {sys_consts.SDELIM}{readme_file} {e}{sys_consts.SDELIM} "
                )
                self._error_code = -1

        return ""

    def _check_all_groups_completed(self) -> None:
        """
        Checks if all major task groups (streaming, transcoding, archiving) have
        signaled completion. If so, triggers the final status report.
        """
        if self._final_report_triggered:  # Prevent multiple final popups
            return None

        if (
            self._streaming_complete
            and self._transcoding_complete
            and self._archiving_complete
        ):
            if DEBUG:
                print(
                    f"DBG AM: All major task groups are reported complete. Triggering final status. {self._session_id=}"
                )

            self._show_final_status()

        return None

    def _show_final_status(self) -> None:
        """
        Displays a summary of errors encountered during processing, if any.
        This method should only be called once when all major task groups are complete.
        """
        if self._final_report_triggered:
            return None

        final_popup_messages = []

        if self._error_code == -1:
            final_popup_messages.append("Initial setup failed. See details below.")

        unique_error_messages = list(
            set(self._error_messages)
        )  # set removes dupe messages

        if unique_error_messages:
            final_popup_messages.extend(unique_error_messages)

        if self._errored and not final_popup_messages:  # No messages for some reason
            final_popup_messages.append(
                "One or more tasks encountered an unspecified error."
            )

        if self.component_event_handler:
            self.component_event_handler(sys_consts.NOTIFICATION_EVENT, "")

        if self._errored and final_popup_messages:
            message = ""
            for error_message in final_popup_messages:
                message += f"{error_message} \n"

            self._error_message = "DVD Build Error(s) Summary:\n\n" + "\n\n" + message

            if self.component_event_handler:
                self.component_event_handler(
                    sys_consts.NOTIFICATION_ERROR_EVENT, self._error_message
                )

        else:
            if self.component_event_handler:
                self.component_event_handler(
                    sys_consts.NOTIFICATION_MESSAGE_EVENT,
                    "DVD Archiving completed successfully!",
                )

        self._final_report_triggered = True

        return None

    def archive_dvd_build(
        self,
        dvd_name: str,
        dvd_folder: str,
        iso_folder: str,
        menu_layout: list[tuple[str, list[Video_Data]]],
        overwrite_existing: bool = True,
    ) -> tuple[int, str]:
        """
        Archives a DVD build and its source video files.

        Args:
            dvd_name (str): The name of the DVD.
            iso_folder (str): The file path of the folder where the ISO build was created.
            dvd_folder (str): The file path of the folder where the DVD build was created.
            menu_layout (list[tuple[str, list[Video_Data]]]): A list of tuples (menu title,Video_Data) representing the
            DVD folder/file names
            overwrite_existing (bool): Whether to overwrite existing DVD backup folder

        Returns:
            tuple(int,str)
                arg 1: 1 if ok, -1 failed
                arg 2: Empty string if ok, error message if failed
        """

        ##### Helper functions
        def _get_video_file_paths(
            preservation_master_folder: str, streaming_folder: str
        ) -> list[dict[str, dict[str, Any]]]:
            """Returns the video file paths and associated metadata derived from the menu layout.

            This function processes the global 'menu_layout' to generate a structured list
            of paths and data for both preservation master files and their streaming
            counterparts. For each menu entry, it determines temporary working directories
            and final destination directories, along with the menu's title and its
            associated video data.

            Args:
                preservation_master_folder (str): The base directory where preservation
                                                  master video files will be temporarily
                                                  processed and eventually stored.
                streaming_folder (str): The base directory where streaming video files
                                        will be temporarily processed and eventually stored.

            Returns:
                list[dict[str, dict[str, Any]]]: A list of dictionaries, where each dictionary
                corresponds to a menu entry. Each dictionary contains two main keys:
                    - 'archive' (Dict): A dictionary holding information for the
                                         preservation master:
                        - 'preservation_master_menu_path_temp' (str): The temporary
                                                                  working directory for
                                                                  archive-related files.
                        - 'preservation_master_menu_path' (str): The final intended
                                                                 directory for archive files.
                        - 'menu_title' (str): The cleaned title of the menu.
                        - 'menu_video_data' (List[Video_Data]): A list of Video_Data objects
                                                                 associated with this menu.
                    - 'streaming' (Dict): A dictionary holding information for the
                                          streaming copy:
                        - 'streaming_path_temp' (str): The temporary working directory
                                                       for streaming-related files.
                        - 'streaming_path' (str): The final intended directory for
                                                  streaming files.
                        - 'menu_title' (str): The cleaned title of the menu.
                        - 'menu_video_data' (List[Video_Data]): A list of Video_Data objects
                                                                 associated with this menu.
            """
            assert isinstance(preservation_master_folder, str), (
                f"{preservation_master_folder=}. Must be a str"
            )
            assert isinstance(streaming_folder, str), (
                f"{streaming_folder=}. Must be a str"
            )
            video_folders = []

            for menu_index, menu in enumerate(menu_layout):
                menu_index: int  # Type Hint
                menu: tuple[str, list[Video_Data]]

                menu_title = menu[0]
                menu_video_data = menu[1]

                if menu_title.strip():
                    menu_title = f"{menu_index + 1:02}_{Text_To_File_Name(menu_title)}"

                    preservation_master_menu_path = self._file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=Text_To_File_Name(menu_title),
                    )
                    preservation_master_menu_path_temp = self._file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=f"{Text_To_File_Name(menu_title)}_temp",
                    )

                    streaming_path = self._file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=Text_To_File_Name(menu_title),
                    )
                    streaming_path_temp = self._file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=f"{Text_To_File_Name(menu_title)}_temp",
                    )
                else:  # If no menu title, then use the menu number
                    menu_title = f"{menu_index + 1:02}_Untitled_Menu"

                    preservation_master_menu_path = self._file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=menu_title,
                    )
                    preservation_master_menu_path_temp = self._file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=menu_title,
                    )

                    streaming_path = self._file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=menu_title,
                    )
                    streaming_path_temp = self._file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=menu_title,
                    )

                video_folders.append({
                    ARCHIVE: {
                        "preservation_master_menu_path_temp": preservation_master_menu_path_temp,
                        "preservation_master_menu_path": preservation_master_menu_path,
                        "menu_title": menu_title,
                        "menu_video_data": menu_video_data,
                    },
                    STREAMING: {
                        "streaming_path_temp": streaming_path_temp,
                        "streaming_path": streaming_path,
                        "menu_title": menu_title,
                        "menu_video_data": menu_video_data,
                    },
                })

            return video_folders

        def _setup_folders(
            dvd_folder: str,
            iso_folder: str,
            archive_folder: str,  # This is the specific project archive folder (e.g., /path/to/Archive/DVDName)
            streaming_folder: str,  # This is the specific project streaming folder (e.g., /path/to/Streaming/DVDName)
            overwrite_existing: bool,
        ) -> tuple[int, str, str, str]:
            """Sets up the archive folder structure for a specific DVD project.

            This function performs safety checks on provided input paths (DVD & ISO sources)
            and output root paths (global archive/streaming folders). It then handles overwriting
            existing project folders if `overwrite_existing` is True, and creates the
            necessary subdirectories for DVD images, ISO files, preservation masters
            (transcoded video), and streaming video for the current DVD project.

            Args:
                dvd_folder (str): The path to the source folder containing the generated DVD image structure
                (e.g., VIDEO_TS, AUDIO_TS).
                iso_folder (str): The path to the source folder containing the generated DVD ISO image file.
                archive_folder (str): The specific root path for the current DVD project's archive content.
                This is a subfolder of `self.archive_folder`.
                streaming_folder (str): The specific root path for the current DVD project's streaming video files.
                This is a subfolder of `self.streaming_folder`.
                overwrite_existing (bool): If True, existing contents of the `archive_folder` and `streaming_folder` *
                for this specific project* will be removed before setup.

            Returns:
                tuple[int, str, str, str]: A tuple containing:
                    - int: 1 if the setup is successful, -1 if an error occurred.
                    - str: An empty string "" on success, otherwise an error message describing the failure.
                    - str: The resolved absolute path to the *created* streaming video output folder (which might be a
                    sub-subfolder if global archive and streaming roots are the same).
                    - str: The resolved absolute path to the *created* preservation master output folder.
            """
            assert isinstance(dvd_folder, str) and dvd_folder.strip() != "", (
                f"{dvd_folder=}. Must be a non-empty str"
            )
            assert isinstance(iso_folder, str) and iso_folder.strip() != "", (
                f"{iso_folder=}. Must be a non-empty str"
            )
            assert isinstance(archive_folder, str) and archive_folder.strip() != "", (
                f"{archive_folder=}. Must be a non-empty str"
            )
            assert (
                isinstance(streaming_folder, str) and streaming_folder.strip() != ""
            ), f"{streaming_folder=}. Must be a non-empty str"

            assert isinstance(overwrite_existing, bool), (
                f"{overwrite_existing=}. Must be a bool"
            )

            resolved_preservation_master_output_folder = ""
            resolved_streaming_video_output_folder = ""

            if not self._file_handler.path_exists(dvd_folder):
                self._error_message = (
                    "Can Not Access DVD Source Folder :"
                    f" {sys_consts.SDELIM}{dvd_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if not self._file_handler.path_exists(iso_folder):
                self._error_message = (
                    "Can Not Access ISO Source Folder :"
                    f" {sys_consts.SDELIM}{iso_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if not self._file_handler.path_exists(self.archive_folder):
                self._error_message = (
                    "Can Not Access Global Archive Root Folder :"
                    f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if not self._file_handler.path_writeable(self.archive_folder):
                self._error_message = (
                    "Can Not Write To Global Archive Root Folder :"
                    f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if not self._file_handler.path_exists(self.streaming_folder):
                self._error_message = (
                    "Can Not Access Global Streaming Root Folder :"
                    f" {sys_consts.SDELIM}{self.streaming_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if not self._file_handler.path_writeable(self.streaming_folder):
                self._error_message = (
                    "Can Not Write To Global Streaming Root Folder :"
                    f" {sys_consts.SDELIM}{self.streaming_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if (
                self._file_handler.path_exists(archive_folder)
                and not overwrite_existing
            ):
                self._error_message = (
                    "Specific Project Archive Folder Already Exists and Overwrite is False :"
                    f" {sys_consts.SDELIM}{archive_folder}{sys_consts.SDELIM}"
                )

                self._error_messages.append(self._error_message)

                self._error_code = -1

                return -1, self._error_message, "", ""

            if (
                self._file_handler.path_exists(streaming_folder)
                and not overwrite_existing
            ):
                self._error_message = (
                    "Specific Project Streaming Folder Already Exists and Overwrite is False :"
                    f" {sys_consts.SDELIM}{streaming_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return -1, self._error_message, "", ""

            if self._file_handler.path_exists(archive_folder) and overwrite_existing:
                self._error_code, message = self._file_handler.remove_dir_contents(
                    archive_folder
                )
                if self._error_code == -1:
                    self._error_message = str(message).replace(
                        archive_folder,
                        f"{sys_consts.SDELIM}{archive_folder}{sys_consts.SDELIM}",
                    )

                    return -1, self._error_message, "", ""

            if self._file_handler.path_exists(streaming_folder) and overwrite_existing:
                self._error_code, message = self._file_handler.remove_dir_contents(
                    streaming_folder
                )
                if self._error_code == -1:
                    self._error_message = str(message).replace(
                        streaming_folder,
                        f"{sys_consts.SDELIM}{streaming_folder}{sys_consts.SDELIM}",
                    )

                    return -1, self._error_message, "", ""

            for folder_type_constant in self._backup_folders:
                if folder_type_constant == DVD_IMAGE:
                    if (
                        not self._file_handler.path_exists(archive_folder)
                        and self._file_handler.make_dir(archive_folder) == -1
                    ):
                        self._error_code = -1
                        return (
                            -1,
                            f"Failed to create project archive folder: {archive_folder}",
                            "",
                            "",
                        )

                    self._error_code, self._error_message = self._file_handler.copy_dir(
                        src_folder=dvd_folder,  # Source of DVD structure (VIDEO_TS, AUDIO_TS)
                        dest_folder=self._file_handler.file_join(
                            archive_folder, folder_type_constant
                        ),
                    )
                    if self._error_code == -1:
                        return -1, self._error_message, "", ""

                elif folder_type_constant == ISO_IMAGE:
                    if (
                        not self._file_handler.path_exists(archive_folder)
                        and self._file_handler.make_dir(archive_folder) == -1
                    ):
                        self._error_code = -1
                        return (
                            -1,
                            f"Failed to create project archive folder: {archive_folder}",
                            "",
                            "",
                        )

                    self._error_code, self._error_message = self._file_handler.copy_dir(
                        src_folder=iso_folder,  # Source of ISO file
                        dest_folder=self._file_handler.file_join(
                            archive_folder, folder_type_constant
                        ),
                    )

                    if self._error_code == -1:
                        return -1, self._error_message, "", ""

                elif folder_type_constant == MISC:
                    pass  # No action for MISC folder type

                elif folder_type_constant == VIDEO_SOURCE:
                    if self.transcode_type.lower() in ("h264", "h265"):
                        transcode_title = (
                            f"{self.transcode_type.lower()}_10bit_iframe_only"
                        )
                    else:
                        transcode_title = self.transcode_type.lower()

                    # Make the video source folders - preservation master and streaming folders
                    resolved_preservation_master_output_folder = self._file_handler.file_join(
                        archive_folder,  # This is the specific project archive root, good.
                        f"{PRESERVATION_MASTER}_{transcode_title}",
                    )

                    # If the *global root* archive and streaming paths are identical,
                    # Then the specific project archive_folder and streaming_folder arguments will also be identical.
                    # In this case, we place streaming content in a sub-subfolder named "STREAMING" to avoid mixing.
                    if self.archive_folder == self.streaming_folder:
                        resolved_streaming_video_output_folder = self._file_handler.file_join(
                            streaming_folder,  # This is the specific project streaming root (same as archive_folder)
                            f"{STREAMING}",  # Add the specific subfolder name for streaming content
                        )
                    else:
                        # If the global root archive and streaming paths are different (e.g., separate drives/shares)
                        # Then the specific project streaming_folder argument is the final destination.
                        resolved_streaming_video_output_folder = streaming_folder

                    if (
                        not self._file_handler.path_exists(
                            resolved_preservation_master_output_folder
                        )
                        and self._file_handler.make_dir(
                            resolved_preservation_master_output_folder
                        )
                        == -1
                    ):
                        self._error_code = -1
                        self._error_message = (
                            "Failed To Create Preservation Master Folder :"
                            f" {sys_consts.SDELIM}{resolved_preservation_master_output_folder}{sys_consts.SDELIM}\n"
                        )

                        return (
                            -1,
                            self._error_message,
                            "",
                            "",
                        )

                    if (
                        not self._file_handler.path_exists(
                            resolved_streaming_video_output_folder
                        )
                        and self._file_handler.make_dir(
                            resolved_streaming_video_output_folder
                        )
                        == -1
                    ):
                        self._error_code = -1
                        self._error_message = (
                            "Failed To Create Streaming Folder :"
                            f" {sys_consts.SDELIM}{resolved_streaming_video_output_folder}{sys_consts.SDELIM}\n"
                        )

                        return (
                            -1,
                            self._error_message,
                            "",
                            "",
                        )

            return (
                1,
                "",
                resolved_streaming_video_output_folder,
                resolved_preservation_master_output_folder,
            )

        def _create_streaming_file(
            video_data: Video_Data,
            streaming_menu_path: str,
            streaming_path: str,
            button_file_name: str,
            button_index: int,
        ) -> tuple[Task_Def | None, list]:
            """Prepares a video file for streaming, either by transcoding or copying.

            This function determines if the input video needs transcoding to H.264
            (for streaming compatibility). If transcoding is required, it initiates
            an asynchronous H.264 transcoding task. Otherwise, it simply copies the
            existing H.264 file. It registers the task with the application's
            multi-threaded task manager for background execution and uses callbacks
            to handle task lifecycle events (start, error, finish, abort).

            Args:
                video_data (Video_Data): An object containing detailed information about the source video file
                (e.g., path, encoding info, dimensions).
                streaming_menu_path (str): The destination folder path where the streaming-ready video file will
                eventually be placed after menu generation. This path is used by the finished callback for final placement.
                streaming_path (str): The temporary or staging folder path where the transcoded/copied streaming video
                file is initially output.
                button_file_name (str): The base filename for the output streaming video file (e.g., derived from the
                DVD menu button title).
                button_index (int): Index of button

            Returns:
                Returns:
                    tuple[Task_Def | None, list] : Returns the task definition or None if an error and a list of the task
                                                   dispatch methods. An empty list if an error occurs
            """
            assert isinstance(video_data, Video_Data), (
                f"{video_data=}. Must be instance of Video_Data"
            )
            assert isinstance(streaming_menu_path, str), (
                f"{streaming_menu_path=}. Must be str"
            )
            assert isinstance(streaming_path, str) and streaming_path != "", (
                f"{streaming_path=}. Must be str"
            )
            assert isinstance(button_file_name, str) and button_file_name != "", (
                f"{button_file_name=}. Must be str"
            )

            file_extension = "mp4"

            task_id = f"{STREAMING_PREFIX}_{button_file_name}_{self._session_id}"
            task_prefix = f"P_{STREAMING_PREFIX}_{self._session_id}"
            task_dispatcher_name = f"D_{STREAMING_PREFIX}_{self._session_id}"

            encoding_info = Get_File_Encoding_Info(video_data.video_path)

            if encoding_info.error:
                self._errored = True
                self._error_code = -1
                self._error_message = encoding_info.error
                self._error_messages.append(encoding_info.error)
                return None, []

            task_def = Task_Def(
                task_id=task_id,
                task_prefix=task_prefix,
            )

            if (
                encoding_info.all_I_frames
                or "h264" not in encoding_info.video_format.lower()
            ):  # Check if we need to transcode
                task_def.worker_function = dvdarch_utils.Transcode_H26x
                task_def.kwargs = {
                    "input_file": video_data.video_path,
                    "output_folder": streaming_menu_path,
                    "width": encoding_info.video_width,
                    "height": encoding_info.video_height,
                    "frame_rate": encoding_info.video_frame_rate,
                    "interlaced": (
                        True
                        if encoding_info.video_scan_type.lower() == "interlaced"
                        else False
                    ),
                    "bottom_field_first": (
                        True
                        if encoding_info.video_scan_order.lower() == "bff"
                        else False
                    ),
                    "h265": False,
                    "high_quality": True,
                    "black_border": True,
                    "auto_bright": video_data.video_file_settings.auto_bright,
                    "normalise": video_data.video_file_settings.normalise,
                    "white_balance": video_data.video_file_settings.white_balance,
                    "denoise": video_data.video_file_settings.denoise,
                    "sharpen": video_data.video_file_settings.sharpen,
                    "filters_off": video_data.video_file_settings.filters_off,
                }

                task_def.cargo = {
                    OP_TYPE: OP_STREAMING,
                    "task_def": task_def,
                    "output_file": "",
                    "streaming_menu_path": streaming_menu_path,
                    "streaming_path": streaming_path,
                    "button_file_name": button_file_name,
                    "file_extension": file_extension,
                }

                return task_def, [
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "start",
                        "operation": OP_STREAMING,
                        "method": _start_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "finish",
                        "operation": OP_STREAMING,
                        "method": _finish_streaming_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "error",
                        "operation": OP_STREAMING,
                        "method": _error_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "abort",
                        "operation": OP_STREAMING,
                        "method": _abort_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                ]

            else:  # Copy
                streaming_file = self._file_handler.file_join(
                    streaming_menu_path,
                    button_file_name,
                    file_extension,
                )

                task_def.worker_function = self._file_handler.copy_file
                task_def.kwargs = {
                    "source": video_data.video_path,
                    "destination_path": streaming_file,
                }

                return task_def, [
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "start",
                        "operation": OP_STREAMING,
                        "method": _start_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "finish",
                        "operation": OP_STREAMING,
                        "method": _finish_streaming_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "error",
                        "operation": OP_STREAMING,
                        "method": _error_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                        "callback": "abort",
                        "operation": OP_STREAMING,
                        "method": _abort_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                ]

        def _transcode_video(
            video_data: Video_Data,
            preservation_master_path: str,
            button_file_name: str,
            file_extension: str,
            button_index: int,
        ) -> tuple[Task_Def | None, list]:
            """Transcodes a video file to a different format (e.g., h264 to h265).

            Args:
                video_data (Video_Data): The video data to transcode.
                preservation_master_path (str): The destination folder path where the transcoded video file will
                eventually be placed after transcoding. This path is used by the finished callback for final placement.
                button_file_name (str): The base filename for the output transcoded video file (e.g., derived from the
                DVD menu button title).
                file_extension (str): The desired file extension for the output transcoded video (e.g., "mp4"). This
                will be overridden to "mp4" if transcoding occurs.
                button_index (int): Index of button

            Returns:
                tuple[Task_Def | None, list] : Returns the task definition or None if an error and a list of the task
                                               dispatch methods. An empty list if an error occurs
            """
            assert isinstance(video_data, Video_Data), (
                f"{video_data=}. Must be instance of Video_Data"
            )
            assert (
                isinstance(preservation_master_path, str)
                and preservation_master_path != ""
            ), f"{preservation_master_path=}. Must be str"
            assert isinstance(button_file_name, str) and button_file_name != "", (
                f"{button_file_name=}. Must be str"
            )
            assert isinstance(file_extension, str) and file_extension != "", (
                f"{file_extension=}. Must be str"
            )

            assert isinstance(button_index, int) and button_index >= 0, (
                f"{button_index=}. Must be int > 0"
            )

            task_id = f"{TRANSCODE_PREFIX}_{button_file_name}_{self._session_id}"
            task_prefix = f"P_{TRANSCODE_PREFIX}_{self._session_id}"
            task_dispatcher_name = f"D_{TRANSCODE_PREFIX}_{self._session_id}"

            task_def = Task_Def(
                task_id=task_id,
                task_prefix=task_prefix,
                cargo={
                    OP_TYPE: TRANSCODE,
                    "preservation_master_path": preservation_master_path,
                    "button_file_name": button_file_name,
                    "file_extension": file_extension,
                    "preservation_master_folder": preservation_master_folder,
                },
            )

            if self.transcode_type == sys_consts.TRANSCODE_NONE:
                video_dir, video_file, video_extension = (
                    self._file_handler.split_file_path(video_data.video_path)
                )
                output_file = self._file_handler.file_join(
                    preservation_master_path, video_file, video_extension
                )

                task_def.worker_function = self._file_handler.copy_file
                task_def.kwargs = {
                    "source": video_data.video_path,
                    "destination_path": output_file,
                }

                task_def.cargo[OP_TYPE] = TRANSCOPY
                task_def.cargo["output_file"] = output_file

                return (
                    task_def,
                    [
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "start",
                            "operation": TRANSCOPY,
                            "method": _start_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "finish",
                            "operation": TRANSCOPY,
                            "method": _finish_transcoding_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "error",
                            "operation": TRANSCOPY,
                            "method": _error_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "abort",
                            "operation": TRANSCOPY,
                            "method": _abort_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                    ],
                )

            elif (
                self.transcode_type == sys_consts.TRANSCODE_H264
                or self.transcode_type == sys_consts.TRANSCODE_H265
            ):
                encoding_info = Get_File_Encoding_Info(video_data.video_path)

                if encoding_info.error:
                    self._errored = True
                    self._error_code = -1
                    self._error_message = encoding_info.error
                    self._error_messages.append(encoding_info.error)

                    return None, []

                if (
                    encoding_info.all_I_frames
                    and (
                        (
                            "h264" not in encoding_info.video_format.lower()
                            and self.transcode_type == sys_consts.TRANSCODE_H264
                        )
                        or (
                            "h265" not in encoding_info.video_format.lower()
                            and self.transcode_type == sys_consts.TRANSCODE_H265
                        )
                    )
                ) or not encoding_info.all_I_frames:  # Check if we need to transcode
                    file_extension = "mkv"

                    task_def.cargo[OP_TYPE] = TRANSCODE

                    task_def.worker_function = dvdarch_utils.Transcode_H26x
                    task_def.kwargs = {
                        "input_file": video_data.video_path,
                        "output_folder": preservation_master_path,
                        "width": encoding_info.video_width,
                        "height": encoding_info.video_height,
                        "frame_rate": encoding_info.video_frame_rate,
                        "interlaced": (
                            True
                            if encoding_info.video_scan_type.lower() == "interlaced"
                            else False
                        ),
                        "bottom_field_first": (
                            True
                            if encoding_info.video_scan_order.lower() == "bff"
                            else False
                        ),
                        "h265": False
                        if self.transcode_type == sys_consts.TRANSCODE_H264
                        else True,
                        "high_quality": True,
                        "iframe_only": True,
                        "encode_10bit": True,
                        "mkv_container": True,
                        "black_border": False,
                    }

                    task_def.cargo["file_extension"] = file_extension

                    return task_def, [
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "start",
                            "operation": self.transcode_type,
                            "method": _start_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "finish",
                            "operation": self.transcode_type,
                            "method": _finish_transcoding_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "error",
                            "operation": self.transcode_type,
                            "method": _error_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "abort",
                            "operation": self.transcode_type,
                            "method": _abort_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                    ]

                else:
                    video_dir, video_file, video_extension = (
                        self._file_handler.split_file_path(video_data.video_path)
                    )
                    output_file = self._file_handler.file_join(
                        preservation_master_path, video_file, video_extension
                    )

                    task_def.worker_function = self._file_handler.copy_file
                    task_def.kwargs = {
                        "source": video_data.video_path,
                        "destination_path": output_file,
                    }

                    task_def.cargo[OP_TYPE] = TRANSCOPY
                    task_def.cargo["output_file"] = output_file

                    return task_def, [
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "start",
                            "operation": TRANSCOPY,
                            "method": _start_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "finish",
                            "operation": TRANSCOPY,
                            "method": _finish_transcoding_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "error",
                            "operation": TRANSCOPY,
                            "method": _error_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                        {
                            "task_dispatch_name": f"{task_dispatcher_name}_{button_index}",
                            "callback": "abort",
                            "operation": TRANSCOPY,
                            "method": _abort_task,
                            "kwargs": {
                                "task_def": task_def,
                            },
                        },
                    ]

            elif self.transcode_type == sys_consts.TRANSCODE_FFV1ARCHIVAL:
                file_extension = "mkv"

                task_def.worker_function = dvdarch_utils.Transcode_ffv1_archival
                task_def.kwargs = {
                    "input_file": video_data.video_path,
                    "output_folder": preservation_master_path,
                    "width": video_data.encoding_info.video_width,
                    "height": video_data.encoding_info.video_height,
                    "frame_rate": video_data.encoding_info.video_frame_rate,
                }

                task_def.cargo["file_extension"] = file_extension

                return task_def, [
                    {
                        "task_dispatch_name": f"{TRANSCODE_PREFIX}_{button_index}",
                        "callback": "start",
                        "operation": self.transcode_type,
                        "method": _start_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{TRANSCODE_PREFIX}_{button_index}",
                        "callback": "finish",
                        "operation": self.transcode_type,
                        "method": _finish_transcoding_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{TRANSCODE_PREFIX}_{button_index}",
                        "callback": "error",
                        "operation": self.transcode_type,
                        "method": _error_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                    {
                        "task_dispatch_name": f"{TRANSCODE_PREFIX}_{button_index}",
                        "callback": "abort",
                        "operation": self.transcode_type,
                        "method": _abort_task,
                        "kwargs": {
                            "task_def": task_def,
                        },
                    },
                ]

            else:
                raise RuntimeError(f"Unknown transcode type {self.transcode_type}")

        ##### Task Callbacks
        def _start_task(task_def: Task_Def) -> None:
            """
            Callback executed when a task is submitted to the Task Dispatcher.

            This function adds the task's definition to the internal list of
            submitted tasks.

            Args:
                task_def (Task_Def): The task definition instance that is being started.

            Returns:
                None
            """
            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if DEBUG:
                print(f"DBG AM ST Started {task_def.task_id=}")
            if self.component_event_handler:
                self.component_event_handler(
                    sys_consts.NOTIFICATION_EVENT,
                    f"Started Task {sys_consts.SDELIM} {task_def.cargo[OP_TYPE]} :{task_def.task_id}{sys_consts.SDELIM}",
                )

            self._submitted_tasks.append(task_def)

        def _finish_streaming_task(task_def: Task_Def) -> None:
            """
            Callback executed when a streaming encode task completes.

            This function processes the result tuple from the completed task,
            attempts to rename the output file, and updates error messages if the
            rename fails.

            Args:
                task_def (Task_Def): The task definition instance for the completed
                                     streaming encode task.

            Returns:
                None
            """
            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if DEBUG:
                print(f"DBG AM FST Completed {task_def.task_id=}")

            self.component_event_handler(
                sys_consts.NOTIFICATION_EVENT,
                f"Finished Streaming Task {sys_consts.SDELIM}{task_def.task_id}{sys_consts.SDELIM}",
            )

            task_error_no, task_message, worker_error_no, worker_message = (
                Unpack_Result_Tuple(task_def)
            )

            file_extension = task_def.cargo["file_extension"]
            button_file_name = task_def.cargo["button_file_name"]
            streaming_menu_path = task_def.cargo["streaming_menu_path"]

            # worker_message contains the temporary output file path
            output_file_path = worker_message

            new_output_file_path = self._file_handler.file_join(
                streaming_menu_path,
                button_file_name,
                file_extension,
            )

            if (
                self._file_handler.rename_file(output_file_path, new_output_file_path)
                == -1
            ):
                self._errored = True
                self._error_messages.append(
                    (
                        f"Failed To Rename {sys_consts.SDELIM}{output_file_path}{sys_consts.SDELIM} To "
                        f"{sys_consts.SDELIM}{new_output_file_path}{sys_consts.SDELIM}"
                    )
                )

            if (
                task_error_no == 1
                and worker_error_no == 1
                and task_message.lower() == "all done"
            ):
                self._streaming_complete = True

                if DEBUG:
                    print(
                        f"DBG AM FST: Streaming (prefix '{STREAMING_PREFIX}') is complete."
                    )

            elif task_error_no != 1 or worker_error_no != 1:
                self._error_messages.append(
                    f"Streaming task {task_def.task_id} reported an error: TaskError={task_error_no}, "
                    f"WorkerError={worker_error_no}, Message='{task_message}'"
                )
                self._errored = True

            self._check_all_groups_completed()

            return None

        def _finish_video_copying_task(task_def: Task_Def):
            """
            Callback executed when a video copying task completes.

            This function processes the task's when finished and, upon successful completion,
            removes the temporary source folder and its contents.

            Args:
                task_def (Task_Def): The task definition instance for the completed
                                     video copying task.

            Returns:
                None
            """
            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if DEBUG:
                print(f"DBG AM FVCT Completed {task_def.task_id=}")

            self.component_event_handler(
                sys_consts.NOTIFICATION_EVENT,
                f"Finished Video Copying Task {sys_consts.SDELIM}{task_def.task_id}{sys_consts.SDELIM}",
            )

            task_error_no, task_message, worker_error_no, worker_message = (
                Unpack_Result_Tuple(task_def)
            )

            if DEBUG:
                print(f"DBG AM FVCT: Remove temp folder for {task_def.task_id}!")

            # self._archiving_complete = True

            preservation_master_menu_path_temp = task_def.cargo[
                "preservation_master_path"
            ]

            # Remove temporary folders and associated sub-folders/files
            if self._file_handler.path_exists(preservation_master_menu_path_temp):
                result, message = self._file_handler.remove_dir_contents(
                    preservation_master_menu_path_temp
                )

                if DEBUG:
                    print(f"DBG AM FVCT {result=} {message=} ")

                if result == -1:
                    self._error_messages.append(
                        f"Failed to remove temp folder {preservation_master_menu_path_temp}: {message}"
                    )
                    self._errored = True
                    self._error_code = -1

            if (
                task_error_no == 1
                and worker_error_no == 1
                and task_message.lower() == "all done"
            ):
                self._archiving_complete = True

                if DEBUG:
                    print(
                        f"DBG AM FVCT: Archiving (prefix '{ARCHIVING_PREFIX}') is complete."
                    )

            elif task_error_no != 1 or worker_error_no != 1:
                self._error_messages.append(
                    f"Video copying task {task_def.task_id} reported an error: TaskError={task_error_no}, "
                    f"WorkerError={worker_error_no}, Message='{task_message}'"
                )
                self._errored = True

            self._check_all_groups_completed()

            return None

        def _finish_transcoding_task(task_def: Task_Def):
            """
            Callback executed when a video transcoding task completes.

            This function processes the result of the completed transcoding task,
            stores its worker-generated output file path in cargo, and then
            processes all submitted transcode tasks in the current batch to
            rename their output files.

            If no errors occur during renaming, it proceeds to submit subsequent
            video copying tasks based on predefined menu paths.

            Args:
                task_def (Task_Def): The task definition instance for the completed
                                     transcoding task.

            Returns:
                None
            """
            assert isinstance(task_def, Task_Def), (
                f"{task_def=}. Must be an instance of Task_Def"
            )

            if DEBUG:
                print(f"DBG AM FTT Completed {task_def.task_id=}")

            self.component_event_handler(
                sys_consts.NOTIFICATION_EVENT,
                f"Finished Video Copying Task {sys_consts.SDELIM}{task_def.task_id}{sys_consts.SDELIM}",
            )

            task_error_no, task_message, worker_error_no, worker_message = (
                Unpack_Result_Tuple(task_def)
            )

            if task_error_no == 1 and worker_error_no == 1:
                task_def.cargo["worker_message_file"] = worker_message
            else:
                message = (
                    f"Transcoding task {task_def.task_id} completed with non-success code: "
                    f"error_no={task_error_no}, worker_error_no={worker_error_no}, worker_message='{task_message}'"
                )

                self._error_messages.append(message)
                self._errored = True

                if DEBUG:
                    print(f"DBG AM FT {message}")

            if (
                not self._errored
                and task_error_no == 1
                and worker_error_no == 1
                and task_message.lower() == "all done"
            ):
                self._transcoding_complete = True

                if DEBUG:
                    print(
                        f"DBG AM Transcoding (prefix '{ARCHIVING_PREFIX}') is complete."
                    )

                submitted_transcodes = [
                    task_def
                    for task_def in self._submitted_tasks
                    if task_def.task_prefix.startswith(f"P_{TRANSCODE_PREFIX}")
                ]

                for current_transcode_task_def in submitted_transcodes:
                    if DEBUG:
                        print(
                            f"DBG AM FT {current_transcode_task_def.task_id=} {current_transcode_task_def.task_prefix=} \n"
                            f"{task_def.worker_function=} {task_def.kwargs=}"
                            # f" {current_transcode_task_def.cargo=}"
                        )

                    if current_transcode_task_def.cargo[OP_TYPE] in (
                        TRANSCODE,
                        TRANSCOPY,
                    ):
                        assert (
                            "worker_message_file" in current_transcode_task_def.cargo
                        ), (
                            "Dev Error, worker_message_file not set for task "
                            + current_transcode_task_def.task_id
                        )

                        if current_transcode_task_def.cargo[OP_TYPE] == TRANSCODE:
                            output_file_path = current_transcode_task_def.cargo[
                                "worker_message_file"
                            ]
                        else:
                            output_file_path = current_transcode_task_def.cargo[
                                "output_file"
                            ]

                        file_extension = current_transcode_task_def.cargo[
                            "file_extension"
                        ]
                        button_file_name = current_transcode_task_def.cargo[
                            "button_file_name"
                        ]
                        preservation_master_path = current_transcode_task_def.cargo[
                            "preservation_master_path"
                        ]

                        new_output_file_path = self._file_handler.file_join(
                            preservation_master_path,
                            button_file_name,
                            file_extension,
                        )

                        if (
                            self._file_handler.rename_file(
                                output_file_path, new_output_file_path
                            )
                            == -1
                        ):
                            message = (
                                f"Failed To Rename {sys_consts.SDELIM}{output_file_path}{sys_consts.SDELIM} To "
                                f"{sys_consts.SDELIM}{new_output_file_path}{sys_consts.SDELIM}"
                            )

                            if DEBUG:
                                print(f"DBG AM FT Errored {message=}")

                            self._error_code = -1
                            self._error_messages.append(message)
                            self._errored = True

                if (
                    not self._errored
                ):  # No errors during renaming of current batch's transcoded files
                    # Copy the transcoded video files to their final location
                    for menu_index, menu_dict in enumerate(menu_paths):
                        archive = menu_dict[ARCHIVE]
                        # streaming = menu_dict[STREAMING] # Unused

                        preservation_master_menu_path_temp = archive[
                            "preservation_master_menu_path_temp"
                        ]

                        preservation_master_menu_path = archive[
                            "preservation_master_menu_path"
                        ]

                        _, preservation_master_tail_os = os.path.split(
                            preservation_master_menu_path
                        )

                        menu_title = archive["menu_title"]
                        task_id = f"{ARCHIVING_PREFIX}_{menu_title}_{self._session_id}"
                        task_prefix = f"P_{ARCHIVING_PREFIX}_{self._session_id}"
                        task_dispatcher_name = (
                            f"D_{ARCHIVING_PREFIX}_{self._session_id}"
                        )

                        task_def = Task_Def(
                            task_id=task_id,
                            task_prefix=task_prefix,
                            worker_function=video_file_copier.copy_folder_into_folders,
                            kwargs={
                                "source_folder": preservation_master_menu_path_temp,
                                "destination_root_folder": preservation_master_menu_path,
                                "menu_title": menu_title,
                                "folder_size_gb": (
                                    4
                                    if self.archive_size == sys_consts.DVD_ARCHIVE_SIZE
                                    else 25
                                ),  # sys_consts.BLUERAY_ARCHIVE_SIZE
                            },
                        )

                        task_def.cargo = {
                            OP_TYPE: "video_archive",
                            "task_def": task_def,
                            "preservation_master_path": preservation_master_menu_path_temp,
                        }

                        task_dispatcher.submit_task(
                            task_def,
                            task_dispatch_methods=[
                                {
                                    # button_index from enumerate 'i'
                                    "task_dispatch_name": f"{task_dispatcher_name}_{menu_index}",
                                    "callback": "start",
                                    "operation": "archive_videos",
                                    "method": _start_task,
                                    "kwargs": {
                                        "task_def": task_def,
                                    },
                                },
                                {
                                    "task_dispatch_name": f"{task_dispatcher_name}_{menu_index}",
                                    "callback": "finish",
                                    "operation": "archive_videos",
                                    "method": _finish_video_copying_task,
                                    "kwargs": {
                                        "task_def": task_def,
                                    },
                                },
                                {
                                    "task_dispatch_name": f"{task_dispatcher_name}_{menu_index}",
                                    "callback": "error",
                                    "operation": "archive_videos",
                                    "method": _error_task,
                                    "kwargs": {
                                        "task_def": task_def,
                                    },
                                },
                                {
                                    "task_dispatch_name": f"{task_dispatcher_name}_{menu_index}",
                                    "callback": "abort",
                                    "operation": "archive_videos",
                                    "method": _abort_task,
                                    "kwargs": {
                                        "task_def": task_def,
                                    },
                                },
                            ],
                        )

            self._check_all_groups_completed()

            return None

        def _error_task(task_def: Task_Def):
            if DEBUG:
                print(f"DBG AM ET {task_def.task_id=}")

            self._error_code = -1
            self._errored = True

            if "message" in task_def.cargo:
                self._error_messages.append(
                    f"Task '{task_def.task_id} Error {task_def.cargo['message']}"
                )

        def _abort_task(task_def: Task_Def):
            if DEBUG:
                print(f"DBG AM AT {task_def.task_id=}")

            self._error_code = -1
            self._errored = True

            if "message" in task_def.cargo:
                self._error_messages.append(
                    f"Task '{task_def.task_id} Error {task_def.cargo['message']}"
                )

        ##### Main
        assert isinstance(dvd_name, str) and dvd_name.strip() != "", (
            f"{dvd_name=}. Must be a non-empty str"
        )
        assert isinstance(dvd_folder, str) and dvd_folder.strip() != "", (
            f"{dvd_folder=}. Must be a non-empty str"
        )
        assert isinstance(iso_folder, str) and iso_folder.strip() != "", (
            f"{iso_folder=}. Must be a non-empty str"
        )
        assert isinstance(menu_layout, list), (
            f"{menu_layout=} must be a list of tuples of str,Video_Data"
        )

        self._reset_new_state()
        task_dispatcher = Task_Dispatcher()
        video_file_copier = dvdarch_utils.Video_File_Copier()

        self._file_handler = file_utils.File()
        self._submitted_tasks = []

        dvd_name = Text_To_File_Name(dvd_name)

        archive_path = self._file_handler.file_join(self.archive_folder, dvd_name)
        streaming_path = self._file_handler.file_join(self.streaming_folder, dvd_name)

        result, message, streaming_folder, preservation_master_folder = _setup_folders(
            dvd_folder, iso_folder, archive_path, streaming_path, overwrite_existing
        )

        if preservation_master_folder != "" and streaming_folder != "":
            menu_paths = _get_video_file_paths(
                preservation_master_folder, streaming_folder
            )

            # Iterate through the DVD menu and transcode the source video files
            for menu_dict in menu_paths:
                archive = menu_dict[ARCHIVE]
                streaming = menu_dict[STREAMING]

                preservation_master_menu_path_temp = archive[
                    "preservation_master_menu_path_temp"
                ]
                menu_video_data = archive["menu_video_data"]
                streaming_menu_path = streaming["streaming_path"]

                if (
                    not self._file_handler.path_exists(
                        preservation_master_menu_path_temp
                    )
                    and self._file_handler.make_dir(preservation_master_menu_path_temp)
                    == -1
                ):
                    self._error_code = -1
                    self._error_message = (
                        "Failed To Create Preservation Master Folder"
                        f" :{sys_consts.SDELIM}{preservation_master_menu_path_temp}{sys_consts.SDELIM}\n"
                    )

                    return -1, self._error_message

                if (
                    not self._file_handler.path_exists(streaming_menu_path)
                    and self._file_handler.make_dir(streaming_menu_path) == -1
                ):
                    self._error_code = -1
                    self._error_message = (
                        "Failed To Create Streaming Folder"
                        f" :{sys_consts.SDELIM}{streaming_menu_path}{sys_consts.SDELIM}"
                    )
                    return -1, self._error_message

                task_list = []

                for button_index, video_data in enumerate(menu_video_data):
                    (
                        _,
                        _,
                        file_extension,
                    ) = self._file_handler.split_file_path(video_data.video_path)
                    preservation_master_menu_path_temp = archive[
                        "preservation_master_menu_path_temp"
                    ]
                    streaming_menu_path = streaming["streaming_path"]

                    button_file_name = (
                        Text_To_File_Name(video_data.video_file_settings.button_title)
                        if video_data.video_file_settings.button_title.strip() != ""
                        else video_data.video_file
                    )

                    button_file_name = f"{button_index + 1:02}_{button_file_name}"

                    task_list.append(
                        _create_streaming_file(
                            video_data=video_data,
                            streaming_menu_path=streaming_menu_path,
                            streaming_path=streaming_path,
                            button_file_name=button_file_name,
                            button_index=button_index,
                        )
                    )

                    task_list.append(
                        _transcode_video(
                            video_data=video_data,
                            preservation_master_path=preservation_master_menu_path_temp,
                            button_file_name=button_file_name,
                            file_extension=file_extension,
                            button_index=button_index,
                        )
                    )

                for task in task_list:  # This avoids a race condition that bit me.
                    if task[0] is not None:  # No error occurred so submit task
                        task_def: Task_Def = task[0]
                        task_dispatch_methods: list[dict] = task[1]
                        task_dispatcher.submit_task(
                            task_def=task_def,
                            task_dispatch_methods=task_dispatch_methods,
                        )

        return 1, ""
