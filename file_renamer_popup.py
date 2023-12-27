"""
    Implements a popup dialog that allows users to rename video files if needed.
        
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
from typing import cast

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from sys_config import Video_Data

# fmt: on


@dataclasses.dataclass
class File_Renamer_Popup(qtg.PopContainer):
    """Renames video files sourced from the video cutter"""

    video_data_list: list[Video_Data] = dataclasses.field(
        default_factory=list
    )  # Pass by reference
    tag: str = "File_Renamer_Popup"
    file_validated: bool = True

    # Private instance variable
    _db_settings: sqldb.App_Settings | None = None

    def __post_init__(self) -> None:
        """Sets-up the form"""
        assert (
            isinstance(self.video_data_list, list) and len(self.video_data_list) > 0
        ), f"{self.video_data_list=}. Must be a non-empty list of Video_Data instances"
        assert all(
            isinstance(video_data, Video_Data) for video_data in self.video_data_list
        ), "All elements must be Video_Data instances"

        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  form events
        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                self._load_files(event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        if self._process_ok(event) == 1:
                            self.set_result(event.tag)
                            super().close()
                    case "cancel":
                        if self._process_cancel(event) == 1:
                            self.set_result(event.tag)
                            super().close()
            case qtg.Sys_Events.CLEAR_TYPING_BUFFER:
                if isinstance(event.value, qtg.Grid_Col_Value):
                    grid_col_value: qtg.Grid_Col_Value = event.value
                    grid_col_value.grid = self

                    user_file_name: str = grid_col_value.value
                    row = grid_col_value.row
                    col = grid_col_value.col
                    user_data = grid_col_value.user_data

                    file_grid: qtg.Grid = cast(
                        qtg.Grid,
                        event.widget_get(
                            container_tag="file_controls",
                            tag="video_input_files",
                        ),
                    )

                    file_grid.value_set(
                        value=user_file_name, row=row, col=col, user_data=user_data
                    )

    def _is_changed(self, event: qtg.Action) -> bool:
        """
        Check if any file names in the video_input_files Grid have been changed.
        Args:
            event (qtg.Action): The event that triggered this method.
        Returns:
            bool: True if any file names have been changed, False otherwise.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_handler = file_utils.File()

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(container_tag="file_controls", tag="video_input_files"),
        )

        col_index = file_grid.colindex_get("new_file_name")

        for row_index in range(0, file_grid.row_count):
            file_name: str = file_grid.value_get(row_index, col_index)
            old_file: str = file_grid.userdata_get(row_index, col_index)
            _, old_file_name, _ = file_handler.split_file_path(old_file)

            if file_name is not None and file_name.strip() != old_file_name.strip():
                return True

        return False

    def _load_files(self, event: qtg.Action) -> int:
        """
        Load the list of video input files into the GUI file controls grid.
        Args:
            event (qtg.Action): The event that triggered the method.
        Returns:
            int: The number of files loaded.
        """
        assert isinstance(event, qtg.Action), "event must be an instance qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="file_controls",
                tag="video_input_files",
            ),
        )

        col_index: int = file_grid.colindex_get("new_file_name")
        row_index = 0

        for row_index, video_data in enumerate(self.video_data_list):
            file_grid.value_set(
                value=video_data.video_file,
                row=row_index,
                col=col_index,
                user_data=video_data.video_path,
            )

        return row_index

    def _package_files(self, event: qtg.Action) -> None:
        """
        Package the video input files into the video_data_list.
        Args:
            event (qtg.Action): The event that triggered this method.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=} must be an instance of qtg.Action"

        file_handler = file_utils.File()

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(container_tag="file_controls", tag="video_input_files"),
        )

        col_index: int = file_grid.colindex_get("new_file_name")

        for row_index in range(file_grid.row_count):
            user_entered_file_name: str = file_grid.value_get(row_index, col_index)

            if user_entered_file_name.strip() != "":
                self.video_data_list[row_index].video_file = user_entered_file_name
                self.video_data_list[
                    row_index
                ].video_file_settings.button_title = file_handler.extract_title(
                    user_entered_file_name
                )

        return None

    def _process_cancel(self, event: qtg.Action) -> int:
        """
        Handles processing the cancel button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if cancel process is ok, -1 otherwise.
        """
        self.set_result("")

        if self._is_changed(event):
            if (
                popups.PopYesNo(
                    title="Files Renamed...",
                    message="Discard Renamed Files And Close Window?",
                ).show()
                == "yes"
            ):
                return 1
            else:
                result = self._rename_files(event)

                if result == 1:
                    self._package_files(event)

                return result
        return 1

    def _process_ok(self, event: qtg.Action) -> int:
        """
        Handles processing the ok button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if the ok process id good, -1 otherwise
        """

        self.set_result("")

        if self._is_changed(event):
            if (
                popups.PopYesNo(title="Rename Files...", message="Rename Files?").show()
                == "yes"
            ):
                result = self._rename_files(event)

                self._package_files(event)

                return result
        else:
            self._package_files(event)

        return 1

    def _rename_files(self, event: qtg.Action) -> int:
        """
        Handles renaming of video file if needed.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if all file names are valid and files are, if needed, renamed successfully, -1 otherwise.
        """
        assert isinstance(event, qtg.Action), "event must be an instance qtg.Action"

        file_handler = file_utils.File()

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="file_controls",
                tag="video_input_files",
            ),
        )

        col_index = file_grid.colindex_get("new_file_name")

        for row_index in range(0, file_grid.row_count):
            file_name = file_grid.value_get(row_index, col_index)
            old_file: str = file_grid.userdata_get(row_index, col_index)

            if file_name is None:  # Probably an error occurred
                continue

            if file_name.strip() != "" and not file_handler.filename_validate(
                file_name
            ):
                error_msg = (
                    f"{sys_consts.SDELIM}{file_name!r}{sys_consts.SDELIM} is not a"
                    " valid file name! Please reenter."
                )
                popups.PopError(
                    title="Invalid File Name...", message=error_msg, width=80
                ).show()
                file_grid.select_row(row_index, col_index)

                return -1

            old_file_path, old_file_name, extension = file_handler.split_file_path(
                old_file
            )
            new_file_path: str = file_handler.file_join(
                old_file_path, file_name, extension
            )

            if file_name.strip() != old_file_name.strip():
                if file_handler.rename_file(old_file, new_file_path) == -1:
                    error_msg = (
                        "Failed to rename file"
                        f" {sys_consts.SDELIM}{old_file_path!r}{sys_consts.SDELIM} to"
                        f" {sys_consts.SDELIM}{new_file_path!r}{sys_consts.SDELIM}"
                    )

                    popups.PopError(
                        title="Failed To Rename File...", message=error_msg
                    ).show()

                    file_grid.select_row(row_index, col_index)
                    return -1
        return 1

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        file_control_container = qtg.VBoxContainer(
            tag="file_controls", align=qtg.Align.TOPLEFT
        )

        file_col_def = (
            qtg.Col_Def(
                label="New File Name",
                tag="new_file_name",
                width=80,
                editable=True,
                checkable=False,
            ),
        )

        video_input_files = qtg.Grid(
            tag="video_input_files",
            noselection=True,
            height=15,
            col_def=file_col_def,
            callback=self.event_handler,
        )

        file_control_container.add_row(
            video_input_files,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )

        control_container.add_row(
            file_control_container,
            qtg.Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            ),
        )

        return control_container
