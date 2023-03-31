"""This module implements a video folder picker form.

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

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts

# fmt: on


@dataclasses.dataclass
class Video_File_Picker_Popup(qtg.PopContainer):
    """This class is a popup that allows the user to select video files"""

    title: str = ""

    def __post_init__(self):
        """Sets-up the form"""

        assert (
            isinstance(self.title, str) and self.title.strip() != ""
        ), f"{self.title=}. Must be a non-empty str"

        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action):
        """Handles  form events

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWOPEN:
                video_folder = self._db_settings.setting_get("video_import_folder")

                if video_folder is None or video_folder.strip() == "":
                    video_folder = file_utils.Special_Path(
                        sys_consts.SPECIAL_PATH.VIDEOS
                    )
                    self._db_settings.setting_set("video_import_folder", video_folder)

                self.load_files(video_folder=video_folder, event=event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        if self._process_ok(event) == 1:
                            super().close()

                    case "cancel":
                        super().close()
                    case "bulk_select":
                        file_grid: qtg.Grid = event.widget_get(
                            container_tag="file_controls",
                            tag="video_input_files",
                        )

                        file_grid.checkitems_all(
                            checked=event.value, col_tag="video_file"
                        )

                    case "video_import_folder":
                        video_folder = self._db_settings.setting_get(
                            "video_import_folder"
                        )

                        video_folder = popups.PopFolderGet(
                            title="Select A Video Folder....",
                            root_dir=(
                                f"{sys_consts.SDELIM}{video_folder}{sys_consts.SDELIM}"
                            ),
                            create_folder=False,
                            folder_edit=False,
                        ).show()

                        if video_folder.strip() != "":
                            self._db_settings.setting_set(
                                "video_import_folder", video_folder
                            )
                            file_grid: qtg.Grid = event.widget_get(
                                container_tag="file_controls",
                                tag="video_input_files",
                            )

                            file_grid.clear()

                            self.load_files(video_folder=video_folder, event=event)

    def load_files(self, video_folder: str, event: qtg.Action):
        """Loads the file grid with video files found in folder

        Args:
            video_folder (str): The video folder where the video files hang-out
            event (qtg.Action): The calling event
        """
        assert (
            isinstance(video_folder, str) and video_folder.strip() != ""
        ), f"{video_folder=}. Must be a non-empty str"
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        file_handler = file_utils.File()

        if file_handler.path_exists(
            video_folder
        ):  # Catch case where folder is not accessible
            video_folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)

        if video_folder.strip() != "":
            with qtg.sys_cursor(qtg.Cursor.hourglass):
                result = file_handler.filelist(
                    path=video_folder,
                    extensions=sys_consts.VIDEO_FILE_EXTNS,
                )

                if result.error_code == file_handler.Path_Error.OK and result.files:
                    file_grid: qtg.Grid = event.widget_get(
                        container_tag="file_controls",
                        tag="video_input_files",
                    )

                    for row_index, file in enumerate(result.files):
                        file_grid.value_set(
                            value=file,
                            row=row_index,
                            col=0,
                            user_data=video_folder,
                        )

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPLEFT
        )
        file_control_container = qtg.FormContainer(
            tag="file_controls", align=qtg.Align.TOPLEFT
        )

        button_container = qtg.HBoxContainer(
            align=qtg.Align.RIGHT, tag="command_buttons"
        ).add_row(
            qtg.Button(
                text="&Select Video Folder",
                tag="video_import_folder",
                callback=self.event_handler,
            ),
            qtg.Spacer(width=37),
            qtg.Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            ),
        )

        file_col_def = (
            qtg.Col_Def(
                label="Video File",
                tag="video_file",
                width=80,
                editable=False,
                checkable=True,
            ),
        )

        video_input_files = qtg.Grid(
            tag="video_input_files",
            noselection=True,
            height=15,
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
            video_input_files,
            button_container,
        )

        control_container.add_row(file_control_container)

        return control_container

    def _process_ok(self, event: qtg.Action) -> int:
        """Processes the ok selection

        Args:
            event (qtg.Action): The event that triggered the function.

        Returns:
            int: 1 all good, close the window. -1 keep window open
        """
        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls",
            tag="video_input_files",
        )

        selected_files = file_grid.checkitems_get
        self.set_result("")

        if selected_files:
            # This is ugly,pop-up returns a str so have to transform selected files to a string!
            file_str = ""
            for file_tuple in selected_files:
                file_tuple: qtg.Grid_Item_Tuple  # Type hine

                row = file_tuple.row_index
                tag = file_tuple.tag
                value = file_tuple.current_value
                user_data = file_tuple.user_data

                file_str += f"{row},{tag},{value},{user_data}|"

            file_str = file_str[:-1]  # Strip trailing | delim

            self.set_result(file_str)
        return 1

    def grid_events(self, event: qtg.Action):
        """Process Grid Events

        Args:
            event (Action): Action
        """
        if event.event == qtg.Sys_Events.CLICKED:
            if event.value.row >= 0 and event.value.col >= 0:
                # When the user clicks on a row in the grid, toggle the switch in that row
                file_grid: qtg.Grid = event.widget_get(
                    container_tag="file_controls", tag="video_input_files"
                )

                if file_grid.checkitemrow_get(event.value.row, col=0):
                    file_grid.checkitemrow_set(
                        row=event.value.row, col=0, checked=False
                    )
                else:
                    file_grid.checkitemrow_set(row=event.value.row, col=0, checked=True)
