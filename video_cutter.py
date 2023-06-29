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
from time import sleep
from typing import Callable

import psutil
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
from configuration_classes import (DVD_Archiver_Base, Video_Data,
                                   Video_File_Settings)
from dvdarch_popups import File_Renamer_Popup

# fmt: on


@dataclasses.dataclass
class Video_Editor(DVD_Archiver_Base):
    processed_files_callback: Callable
    display_height: int = 576  # // 2
    display_width: int = 720  # // 2

    # Private instance variables
    _aspect_ratio: str = sys_consts.AR43
    _archive_manager: Archive_Manager | None = None
    _background_task_manager = Task_Manager()
    _current_frame: int = -1
    _display_height: int = -1
    _display_width: int = -1
    _edit_list_grid: qtg.Grid | None = None
    _file_system_init: bool = False
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _frame_rate: float = 25  # Default to 25 frames per second
    _frame_width: int = 720
    _frame_height: int = 576
    _frame_count: int = -1
    _output_folder: str = ""
    _video_cutter_container: qtg.HBoxContainer | None = None
    _video_display: qtg.Label | None = None
    _video_slider: qtg.Slider | None = None
    _frame_display: qtg.LCD | None = None
    _menu_frame: qtg.LineEdit | None = None
    _menu_title: qtg.LineEdit | None = None
    _progress_bar: qtg.ProgressBar | None = None
    _video_editor: qtg.HBoxContainer | None = None
    _video_filter_container: qtg.HBoxContainer | None = None
    _sliding: bool = False
    _source_state = "no_media"
    _step_value: int = 1
    _video_handler: qtg.Video_Player | None = None
    _edit_folder: str = sys_consts.EDIT_FOLDER
    _transcode_folder: str = sys_consts.TRANSCODE_FOLDER
    _video_file_input: list[Video_Data] = dataclasses.field(default_factory=list)

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

        self._background_task_manager.start()

        self._video_handler.frame_changed_handler.connect(self._frame_handler)
        self._video_handler.media_status_changed_handler.connect(
            self._media_status_change
        )
        self._video_handler.position_changed_handler.connect(self._position_changed)

        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        if archive_folder:
            self._archive_manager = Archive_Manager(archive_folder=archive_folder)

    def shutdown(self) -> int:
        """
        Shuts down the instance

        Returns:
            int: 1:Ok, -1 Shutdown terminated
        """
        if self._background_task_manager.list_running_tasks():
            if (
                popups.PopYesNo(
                    title="Background Tasks Running...",
                    message="Kill Background Tasks And Exit?",
                ).show()
                == "no"
            ):
                return -1
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
            case qtg.Sys_Events.EDITCHANGED:
                match event.tag:
                    case "video_slider":
                        pass
                        # self._seek(event.value)
            case qtg.Sys_Events.MOVED:
                match event.tag:
                    case "video_slider":
                        self._seek(event.value)
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
                    case "video_sliderx":
                        self._seek(event.value)

    def is_available(self) -> bool:
        """Checks if the media player is supported on the platform
        Returns:
            bool: True if the media player is supported, False otherwise.
        """
        return self._video_handler.available()

    def set_source(
        self, video_file_input: list[Video_Data], output_folder: str
    ) -> None:
        """Sets the source of the media player
        Args:
            video_file_input (list[Video_Data]): The input video information
            output_folder (str): The folder in which processed video files are placed
        """
        assert isinstance(video_file_input, list), f"{video_file_input=}. Must be list"
        assert all(
            isinstance(video_file, Video_Data) for video_file in video_file_input
        ), f"{video_file_input=}. Must be list of Video_Data"

        assert (
            isinstance(output_folder, str) and output_folder.strip() != ""
        ), f"{output_folder=}. Must be non-empty str"

        self._output_folder = output_folder

        if self._video_file_input:
            self.archive_edit_list_write()
            self._get_dvd_settings()
            self.processed_files_callback(self._video_file_input)

        self._edit_list_grid.clear()

        self._video_file_input = video_file_input

        self._archive_edit_list_read()

        self._aspect_ratio = self._video_file_input[0].encoding_info.video_ar
        self._frame_width = self._video_file_input[0].encoding_info.video_width
        self._frame_height = self._video_file_input[0].encoding_info.video_height
        self._frame_rate = self._video_file_input[0].encoding_info.video_frame_rate
        self._frame_count = self._video_file_input[0].encoding_info.video_frame_count

        if not self._file_system_init:
            result = self._video_file_system_maker()

            if result == -1:
                return None

        self._video_slider.value_set(0)
        self._video_slider.range_max_set(self._frame_count)

        self._set_dvd_settings()

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="white_balance",
        ).value_set(self._video_file_input[0].video_file_settings.white_balance)

        if self._frame_count > 0:
            self._video_handler.set_source(
                self._video_file_input[0].video_path, self._frame_rate
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

        if self._menu_title.modified:
            self._video_file_input[0].video_file_settings.button_title = (
                self._menu_title.value_get()
            )

        if self._menu_frame.modified:
            self._video_file_input[0].video_file_settings.menu_button_frame = (
                int(self._menu_frame.value_get())
            )    

        self._video_file_input[0].video_file_settings.normalise = (
            self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="normalise",
            ).value_get()
        )

        self._video_file_input[0].video_file_settings.normalise = (
            self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="denoise",
            ).value_get()
        )
        self._video_file_input[0].video_file_settings.auto_bright = (
            self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="auto_levels",
            ).value_get()
        )

        self._video_file_input[0].video_file_settings.sharpen = (
            self._video_filter_container.widget_get(
                container_tag="video_filters",
                tag="sharpen",
            ).value_get()
        )

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
            self._menu_frame.value_set(str(self._video_file_input[0].video_file_settings.menu_button_frame))

        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="normalise",
        ).value_set(self._video_file_input[0].video_file_settings.normalise)
        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="denoise",
        ).value_set(self._video_file_input[0].video_file_settings.normalise)
        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="auto_levels",
        ).value_set(self._video_file_input[0].video_file_settings.auto_bright)
        self._video_filter_container.widget_get(
            container_tag="video_filters",
            tag="sharpen",
        ).value_set(self._video_file_input[0].video_file_settings.sharpen)

    def _archive_edit_list_read(self) -> None:
        """Reads edit cuts from the archive manager and populates the edit list grid with the data.
        If both the archive manager and the edit list grid exist, reads edit cuts for the input file from the archive
        manager using the `read_edit_cuts` method. Then, for each cut tuple in the edit cuts list, sets the `mark_in` and
        `mark_out` values of the corresponding row in the edit list grid using the `value_set` method.
        """

        if self._archive_manager and self._edit_list_grid:
            edit_cuts = self._archive_manager.read_edit_cuts(
                self._video_file_input[0].video_path
            )

            if not edit_cuts:
                if self._archive_manager.get_error_code == -1:
                    popups.PopError(
                        title="Archive Edit List",
                        message=f"Read Failed : {self._archive_manager.get_error}",
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
                result, message = self._archive_manager.write_edit_cuts(
                    self._video_file_input[0].video_path, edit_list
                )
            else:
                result, message = self._archive_manager.delete_edit_cuts(
                    self._video_file_input[0].video_path
                )

            if result == -1:
                popups.PopError(
                    title="Archive Edit List", message=f"Write Failed : {message}"
                ).show()

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
                options=("As A Single File", "As Individual Files"),
            ).show()

            if result == "As Individual Files":
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
                            video_file_settings.button_title = (
                                file_handler.extract_title(video_file)
                            )

                            video_data.append(
                                Video_Data(
                                    video_folder=video_path,
                                    video_file=video_file,
                                    video_extension=video_extension,
                                    encoding_info=dvdarch_utils.get_file_encoding_info(
                                        video_file_path
                                    ),
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

            elif result == "As A Single File":
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
                        result, message = dvdarch_utils.concatenate_videos(
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

                        self._video_file_input.append(
                            Video_Data(
                                video_folder=assembled_path,
                                video_file=assembled_filename,
                                video_extension=assembled_extension,
                                encoding_info=dvdarch_utils.get_file_encoding_info(
                                    video_files_string
                                ),
                                video_file_settings=self._video_file_input[
                                    0
                                ].video_file_settings,
                            )
                        )

                        self.processed_files_callback(self._video_file_input)
            else:
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
        self._task_errored = False
        self._task_status = -1
        self._task_message = ""
        self._tasks_submitted = 0

        # ===== Helper
        def notification_call_back(status: int, message: str, output: str, name):
            if status == -1:
                self._task_status = status
                self._task_message = message
                self._task_errored = True

            self._tasks_submitted -= 1

            self._progress_bar.value_set((len(edit_list) - 1) - self._tasks_submitted)

        def transform_cut_in_to_cut_out(
            edit_list: list[tuple[int, int, str]], frame_count: int
        ) -> list[tuple[int, int, str]]:
            """
            Transforms a list of cut in points to cut out points.

            Args:
                edit_list (list[Tuple[int, int, str]]): A list of tuples representing the cut in. cut out points and clip name of a video.
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

        result, message = dvdarch_utils.get_codec(input_file)

        if result == -1:
            return -1, message
        codec = message

        temp_files = []

        if cut_out:
            edit_list = transform_cut_in_to_cut_out(
                edit_list=edit_list, frame_count=self._frame_count
            )

        self._progress_bar.range_set(0, len(edit_list))
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

            # Calculate the start and end times of the segment based on the frame numbers
            start_time = start_frame / self._frame_rate
            end_time = end_frame / self._frame_rate

            # Calculate the nearest key frames before and after the cut
            result, before_key_frame = dvdarch_utils.get_nearest_key_frame(
                input_file, start_time, "prev"
            )

            if result == -1:
                return -1, "Failed To Get Before Key Frame"

            result, after_key_frame = dvdarch_utils.get_nearest_key_frame(
                input_file, end_time, "next"
            )

            if result == -1:
                return -1, "Failed To Get After Key Frame"

            # Set the start time and duration of the segment to re-encode
            segment_start = (
                before_key_frame if before_key_frame is not None else start_time
            )

            segment_duration = (
                after_key_frame - segment_start
                if after_key_frame is not None
                else end_time - segment_start
            )

            # command = [sys_consts.FFMPG,"-v","debug", "-i", input_file] #DBG
            command = [sys_consts.FFMPG, "-i", input_file]

            # Check if re-encoding is necessary
            command += ["-map", "0:v", "-map", "0:a"]

            if before_key_frame is not None and after_key_frame is not None:
                # Re-encode the segment
                if not utils.Is_Complied():
                    print(f"DBG Re-Encode Seg {before_key_frame=} {after_key_frame=}")

                command += ["-force_key_frames", f"{before_key_frame}+1"]
                command += ["-tune", "fastdecode"]
                command += ["-ss", str(segment_start)]
                command += ["-t", str(segment_duration)]
                command += ["-avoid_negative_ts", "make_zero"]
                command += ["-c:v", codec]
                command += ["-c:a", "copy"]
                command += [
                    "-threads",
                    str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
                ]
                command += [temp_file, "-y"]
            else:
                # Copy the segment
                if not utils.Is_Complied():
                    print("DBG Copy Seg")

                command += ["-ss", str(segment_start)]
                command += ["-t", str(segment_duration)]
                command += ["-avoid_negative_ts", "make_zero"]
                command += ["-c", "copy"]
                command += [
                    "-threads",
                    str(psutil.cpu_count() - 1 if psutil.cpu_count() > 1 else 1),
                ]
                command += [temp_file, "-y"]

            self._tasks_submitted += 1
            self._background_task_manager.add_task(
                name=f"cut_video_{cut_index}",
                command=command,
                callback=notification_call_back,
            )

        while self._tasks_submitted > 0 and not self._task_errored:
            if self._task_errored:
                self._progress_bar.reset()
                return -1, self._task_message
            sleep(0.5)
        self._progress_bar.reset()

        if cut_out:  # Concat temp file for final file and remove the temp files
            result, message = dvdarch_utils.concatenate_videos(
                temp_files=temp_files, output_file=output_file, delete_temp_files=False
            )

            if result == -1:
                return -1, message

            for temp_file in temp_files:
                if file_handler.remove_file(temp_file) == -1:
                    return -1, f"Failed To Remove File <{temp_file}>"

        else:
            # We keep the temp files, as they are the new videos, and build an output file str where each video is
            # delimitered by a ','
            output_file = ",".join(temp_files)

        return 1, output_file

    def _delete_segments(self, event: qtg.Action) -> None:
        """
        Deletes the specified segments from the input file.

        Note: Pop_Container set_result is called here and not in the _process_ok method

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
                    self._edit_folder, f"{dvd_menu_title}", extension
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
                            encoding_info=dvdarch_utils.get_file_encoding_info(
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
        value: qtg.Grid_Col_Value = event.value

        assert isinstance(
            value, qtg.Grid_Col_Value
        ), f"{value=} must be a qtg.Grid_Col_Value"

        if value.value < 0:
            self._video_handler.seek(0)
        elif value.value >= self._frame_count:
            self._video_handler.seek(self._frame_count - 1)  # frame count is zero based
        else:
            self._video_handler.seek(value.value)

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
        self._video_display.guiwidget_get.setPixmap(frame)

    def _position_changed(self, frame: int) -> None:
        """
        A method that is called when the position of the media player changes.
        Converts the current position in milliseconds to the corresponding frame number,
        updates the video slider if necessary, and emits a signal indicating that the position has changed.
        Args:
            frame (int): The currentmedia player frame.
        """
        self._sliding = True

        if self._sliding and self._video_slider is not None:
            self._video_slider.value_set(frame)
        self._frame_display.value_set(frame)    

    def _seek(self, frame: int) -> None:
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
        end_time = self._frame_num_to_ffmpeg_time(frame)

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

        start_time = self._frame_num_to_ffmpeg_time(frame)

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
        select_start: qtg.Button = event.widget_get(
            container_tag="video_buttons", tag="selection_start"
        )
        select_end: qtg.Button = event.widget_get(
            container_tag="video_buttons", tag="selection_end"
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

    def _frame_num_to_ffmpeg_time(self, frame_num: int) -> str:
        """
        Converts a frame number to an FFmpeg offset time string in the format "hh:mm:ss.mmm".

        Args:
            frame_num: An integer representing the frame number to convert.

        Returns:
            A string representing the FFmpeg offset time in the format "hh:mm:ss.mmm".

        """
        offset_time = frame_num / self._frame_rate
        hours = int(offset_time / 3600)
        minutes = int((offset_time % 3600) / 60)
        seconds = int(offset_time % 60)
        milliseconds = int((offset_time % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

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
            print(f"DBG {self._step_value=} {value=}")

    def _video_file_system_maker(self) -> int:
        """
        Create the necessary folders for video processing, and checks if the input file exists.

        Returns:
            int : 1 OK, -1 error occured


        Side effects:
            Creates folders as necessary for the video processing task.

        """
        file_handler = file_utils.File()

        print(f"DBG {self._output_folder=} {self._edit_folder=}")

        if not file_handler.path_exists(self._output_folder):
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
            self._output_folder, self._edit_folder
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
                height=40,
                callback=self.event_handler,
                range_max=1,
                range_min=0,
                pixel_unit=True,
                single_step=1,
            )
            video_cutter_container = qtg.VBoxContainer(
                tag="video_cutter",
                text="Video Cutter",
                align=qtg.Align.CENTER,
            ).add_row(
                self._video_display,
                self._video_slider,
                video_button_container,
            )

            return video_cutter_container

        def assemble_edit_list_container() -> qtg.VBoxContainer:
            """
            Create a VBoxContainer containing the editing list.
            TODO : Pull into its own class
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
                height=self.display_height,
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

            self._progress_bar = qtg.ProgressBar(tag="file_progress")

            edit_file_list = qtg.VBoxContainer(align=qtg.Align.TOPLEFT).add_row(
                qtg.HBoxContainer(margin_left=4).add_row(
                    qtg.Checkbox(
                        text="Select All",
                        tag="bulk_select",
                        callback=self.event_handler,
                        tooltip="Select All Edit Points",
                        width=11,
                    ),
                    qtg.Spacer(width=12, tune_hsize=-13),
                    self._progress_bar,
                ),
                qtg.VBoxContainer(align=qtg.Align.BOTTOMRIGHT).add_row(
                    self._edit_list_grid, edit_list_buttons
                ),
            )

            edit_list_container = qtg.VBoxContainer(
                tag="edit_list",
                text="Edit List",
                align=qtg.Align.LEFT,
            ).add_row(edit_file_list)

            return edit_list_container

        # ===== Maint
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
