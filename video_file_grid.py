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
import datetime
import shelve

import platformdirs

import dvdarch_utils
import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
import utils
from configuration_classes import Video_Data
from dvd_menu_configuration import DVD_Menu_Config_Popup
from video_cutter import Video_Cutter_Popup
from video_file_picker import Video_File_Picker_Popup

# fmt: on


class Video_File_Grid:
    """This class implements the file handling of the Black DVD Archiver ui"""

    def __init__(self):
        """Sets up the instance for use"""
        file_handler = file_utils.File()

        self.dvd_percent_used = 0  # TODO Make A selection of DVD5 and DVD9
        self.common_words = []
        self.project_video_standard = ""  # PAL or NTSC
        self.project_duration = ""

        # Private instance variables
        self._display_filename: bool = True
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
        self._db_path = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

        self._grid_db = file_handler.file_join(
            self._db_path, sys_consts.VIDEO_GRID_DB, "db"
        )

    @property
    def _get_dvd_build_folder(self) -> str:
        """Gets the DVD build folder

        Returns:
            str: The DVD build folder
        """
        dvd_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if dvd_folder is None or dvd_folder.strip() == "":
            popups.PopError(
                title="DVD Build Folder Error...",
                message=(
                    "A DVD Build Folder Must Be Entered Before Making A Video Edit!"
                ),
            ).show()
            return ""
        return dvd_folder

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
                self._set_project_standard_duration(event)

    def _edit_video(self, event: qtg.Action) -> None:
        """
        Edits a video file.
        Args:
            event (qtg.Action): The event that triggered the video edit.
        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        dvd_folder = self._get_dvd_build_folder

        if not dvd_folder:
            return None

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls", tag="video_input_files"
        )

        row_unique_id = int(
            event.container_tag.split("|")[0]
        )  # Grid button container tag has the row_id embedded as the 1st element and delimtered by |
        row = file_grid.row_from_item_id(row_unique_id)

        user_data: Video_Data = file_grid.userdata_get(
            row=row, col=file_grid.colindex_get("video_file")
        )
        video_file_input: list[Video_Data] = [user_data]

        Video_Cutter_Popup(
            title="Video File Cutter/Settings",
            video_file_input=video_file_input,  # list :  pass by reference, so that contents can be modified
            output_folder=dvd_folder,
            excluded_word_list=self.common_words,
        ).show()

        if (
            len(video_file_input) == 1
        ):  # Original, only user entered file title text might have changed
            self._processed_trimmed(
                file_grid,
                video_file_input[0].vd_id,
                video_file_input[0].video_path,
                video_file_input[0].video_file_settings.button_title,
            )
        elif len(video_file_input) == 2:  # Original & one edited file (cut/assemble)
            self._processed_trimmed(
                file_grid,
                video_file_input[0].vd_id,
                video_file_input[1].video_path,
                video_file_input[0].video_file_settings.button_title,
            )
        elif len(video_file_input) > 2:  # Original and multiple edited files
            # TODO Make user configurable perhaps
            self._delete_file_from_grid(file_grid, video_file_input[0].vd_id)

            # Insert Assembled Children  Files
            self._insert_files_into_grid(
                event,
                [video_file_data for video_file_data in video_file_input[1:]],
            )

        return None

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
                encoding_info = dvdarch_utils.get_file_encoding_info(trimmed_file)
                if encoding_info.error:  # Error Occurred
                    popups.PopError(
                        title="Encoding Read Error...",
                        message=encoding_info.error,
                    ).show()
                    return
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
                    video_user_data=updated_user_data,
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
            case qtg.Sys_Events.APPPOSTINIT:
                self._load_grid(event)
            case qtg.Sys_Events.APPCLOSED:
                self._save_grid(event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "bulk_select":
                        file_grid: qtg.Grid = event.widget_get(
                            container_tag="video_file_controls",
                            tag="video_input_files",
                        )

                        file_grid.checkitems_all(
                            checked=event.value, col_tag="video_file"
                        )

                        self._set_project_standard_duration(event)
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
                        folder = self._db_settings.setting_get(
                            sys_consts.DVD_BUILD_FOLDER
                        )

                        if folder is None or folder.strip() == "":
                            popups.PopError(
                                title="DVD Build Folder Error...",
                                message=(
                                    "A DVD Build Folder Must Be Entered Before Video"
                                    " Folders Are Selected!"
                                ),
                            ).show()
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        file_handler = file_utils.File()
        dvd_folder = self._get_dvd_build_folder

        if not dvd_folder:
            return None

        edit_folder = file_handler.file_join(dvd_folder, sys_consts.EDIT_FOLDER)
        edit_folder = file_handler.file_join(
            dvd_folder, sys_consts.TRANSCODE_FOLDER
        )  # TODO Remove and same in video_cutter

        if not file_handler.file_exists(edit_folder):
            if file_handler.make_dir(edit_folder) == -1:
                popups.PopError(
                    title="Error Creating Edit Folder",
                    message=(
                        "Error Creating Edit Folder!\n"
                        f"{sys_consts.SDELIM}{edit_folder}{sys_consts.SDELIM}"
                    ),
                ).show()
                return None

        checked_items = file_grid.checkitems_get

        if not checked_items:
            popups.PopError(
                title="No Files Selected", message="Please Select Files To Join"
            ).show()
            return None

        if (
            popups.PopYesNo(title="Join Files", message="Join Selected Files?").show()
            == "yes"
        ):
            concatenating_files = []
            removed_files = []
            output_file = ""
            vd_id = -1
            button_title = ""

            for item in checked_items:
                item: qtg.Grid_Item
                video_data: Video_Data = item.user_data

                if not output_file:  # Happens on first iteration
                    vd_id = video_data.vd_id
                    button_title = video_data.video_file_settings.button_title

                    output_file = file_handler.file_join(
                        dir_path=video_data.video_folder,
                        file_name=f"{video_data.video_file}_joined",
                        ext=video_data.video_extension,
                    )
                else:
                    removed_files.append(video_data)

                concatenating_files.append(video_data.video_path)

            if concatenating_files and output_file:
                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    result, message = dvdarch_utils.concatenate_videos(
                        temp_files=concatenating_files, output_file=output_file
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
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

        self._set_project_standard_duration(event)

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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
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
            return

        if (
            all(
                checked_items[i].row_index == checked_items[i + 1].row_index + 1
                for i in range(len(checked_items) - 1)
            )
            if up
            else all(
                checked_items[i].row_index == checked_items[i + 1].row_index - 1
                for i in range(len(checked_items) - 1)
            )
        ):  # Contiguous block check
            popups.PopMessage(
                title="Selected Video files Not Contiguous...",
                message="Selected Video files Must Be A Contiguous Block!",
            ).show()
            return

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
            event (qtg.Action) : Calling event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        file_handler = file_utils.File()
        removed_files = []

        try:
            with qtg.sys_cursor(qtg.Cursor.hourglass):
                with shelve.open(
                    self._grid_db
                ) as db:  # TODO should this be stored in the app db?
                    db_data = db.get("video_grid")

                    if db_data:
                        for row_index, row in enumerate(db_data):
                            for item in row:
                                if item[1]:
                                    video_data: Video_Data = item[1]

                                    if not file_handler.file_exists(
                                        video_data.video_path
                                    ):
                                        removed_files.append(video_data.video_path)
                                        break

                                    duration = str(
                                        datetime.timedelta(
                                            seconds=video_data.encoding_info.video_duration
                                        )
                                    ).split(".")[0]

                                    self._populate_grid_row(
                                        file_grid=file_grid,
                                        row_index=row_index,
                                        video_user_data=video_data,
                                        duration=duration,
                                    )
                                    toolbox = self._get_toolbox(video_data)
                                    file_grid.row_widget_set(
                                        row=row_index,
                                        col=file_grid.colindex_get("settings"),
                                        widget=toolbox,
                                    )
                file_grid.row_scroll_to(0)
                self._set_project_standard_duration(event)

                if removed_files:
                    removed_file_list = "\n".join(removed_files)
                    popups.PopMessage(
                        width=80,
                        title="Source Files Not Found...",
                        message=(
                            "The following video files do not exist and were removed"
                            " from the project:"
                            f"{sys_consts.SDELIM}{removed_file_list}{sys_consts.SDELIM}"
                        ),
                    ).show()
        except Exception as e:
            popups.PopError(title="File Grid Load Error...", message=str(e)).show()

    def _save_grid(self, event: qtg.Action) -> None:
        """Saves the grid to the database

        Args:
            event (qtg.Action) : Calling event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        try:
            with qtg.sys_cursor(qtg.Cursor.hourglass):
                with shelve.open(
                    self._grid_db
                ) as db:  # TODO should this be stored in the app db?
                    row_data = []
                    file_grid: qtg.Grid = event.widget_get(
                        container_tag="video_file_controls",
                        tag="video_input_files",
                    )
                    for row in range(file_grid.row_count):
                        col_value = []
                        for col in range(file_grid.col_count):
                            value = file_grid.value_get(row=row, col=col)
                            user_data = file_grid.userdata_get(row=row, col=col)

                            col_value.append((value, user_data))

                        row_data.append(col_value)

                    db["video_grid"] = row_data
        except Exception as e:
            popups.PopError(title="File Grid Save Error...", message=str(e)).show()

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
                    tooltip=f"{sys_consts.SDELIM}{grid_video_data.video_path}{sys_consts.SDELIM}",
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
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
        max_group_val = self._get_max_group_num(file_grid)

        for item in checked_items:
            video_item: Video_Data = item.user_data

            if video_item.video_file_settings.menu_group >= 0:
                grouped.append(video_item)
            else:
                ungrouped.append(item)

        if grouped:
            for video_item in grouped:
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

        for item in ungrouped:
            video_item: Video_Data = item.user_data
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
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
            file_grid: qtg.Grid = event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            )

            with qtg.sys_cursor(qtg.Cursor.hourglass):
                rejected = self._insert_files_into_grid(event, video_file_list)

            if file_grid.row_count > 0:
                # First file sets project encoding standard - Project files in toto Can be PAL or NTSC not both
                grid_video_data: Video_Data = file_grid.userdata_get(
                    row=0, col=file_grid.colindex_get("settings")
                )
                project_video_standard = grid_video_data.encoding_info.video_standard

                loaded_files = []
                for row_index in reversed(range(file_grid.row_count)):
                    file_name = file_grid.value_get(row_index, 0)

                    grid_video_data: Video_Data = file_grid.userdata_get(
                        row=row_index, col=file_grid.colindex_get("settings")
                    )

                    video_standard = grid_video_data.encoding_info.video_standard

                    if project_video_standard != video_standard:
                        rejected += (
                            f"{sys_consts.SDELIM}{file_name} : {sys_consts.SDELIM} Not"
                            " Project Video Standard "
                            f"{sys_consts.SDELIM}{project_video_standard}{sys_consts.SDELIM} \n"
                        )

                        file_grid.row_delete(row_index)
                        continue

                    loaded_files.append(file_name)

                # Keep a list of words common to all file names
                self.common_words = utils.Find_Common_Words(loaded_files)
            self._toggle_file_button_names(event)
            self._set_project_standard_duration(event)

            if rejected != "":
                popups.PopMessage(
                    title="These Files Are Not Permitted...", message=rejected
                ).show()
        return None

    def _insert_files_into_grid(
        self,
        event: qtg.Action,
        selected_files: list[Video_Data],
    ) -> str:
        """
        Inserts files into the file grid widget.

        Args:
            event (qrg.Action) : Triggering event
            selected_files (list[Video_Data]): list of video file data
        Returns:
            str: A string containing information about any rejected files.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"
        assert isinstance(
            selected_files, list
        ), f"{selected_files=}.  Must be a list of Video_Data objects"
        assert all(
            isinstance(item, Video_Data) for item in selected_files
        ), f"{selected_files=}.  Must be a list of Video_Data objects"

        file_handler: file_utils.File
        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        rejected = ""
        rows_loaded = file_grid.row_count
        row_index = 0

        for file_video_data in selected_files:
            # Check if file already loaded in grid
            for check_row_index in range(file_grid.row_count):
                grid_video_data: Video_Data = file_grid.userdata_get(
                    row=check_row_index, col=file_grid.colindex_get("video_file")
                )

                if grid_video_data.video_path == file_video_data.video_path:
                    break
            else:  # File not in grid already
                if file_video_data.encoding_info.video_tracks <= 0:
                    file_video_data.encoding_info = (
                        dvdarch_utils.get_file_encoding_info(file_video_data.video_path)
                    )

                    if file_video_data.encoding_info.error:  # Error Occurred
                        rejected += (
                            "File Error"
                            f" {sys_consts.SDELIM}{file_video_data.video_path} :"
                            f" {sys_consts.SDELIM} {file_video_data.encoding_info.error} \n"
                        )
                        continue

                toolbox = self._get_toolbox(file_video_data)

                if file_video_data.encoding_info.video_tracks == 0:
                    rejected += (
                        f"{sys_consts.SDELIM}{file_video_data.video_path} :"
                        f" {sys_consts.SDELIM}No Video Track \n"
                    )
                    continue

                duration = str(
                    datetime.timedelta(
                        seconds=file_video_data.encoding_info.video_duration
                    )
                ).split(".")[0]

                self._populate_grid_row(
                    file_grid=file_grid,
                    row_index=rows_loaded + row_index,
                    video_user_data=file_video_data,
                    duration=duration,
                )

                file_grid.row_widget_set(
                    row=rows_loaded + row_index,
                    col=file_grid.colindex_get("settings"),
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
                # tune_vsize=-5,
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
        video_user_data: Video_Data,
        duration: str,
    ) -> None:
        """Populates the grid row with the video information.

        Args:
            file_grid (qtg.Grid): The grid to populate.
            row_index (int): The index of the row to populate.
            video_user_data (File_Control.Video_Data): The video data to populate.
            duration (str): The duration of the video.
        """
        assert isinstance(
            file_grid, qtg.Grid
        ), f"{file_grid=}. Must be an instance of qtg.Grid"
        assert isinstance(
            video_user_data, Video_Data
        ), f"{video_user_data=}. Must be an instance of File_Control.Video_Data"
        assert isinstance(duration, str), f"{duration=}. Must be str."

        file_grid.value_set(
            value=(
                f"{video_user_data.video_file}{video_user_data.video_extension}"
                if self._display_filename
                else video_user_data.video_file_settings.button_title
            ),
            row=row_index,
            col=file_grid.colindex_get("video_file"),
            user_data=video_user_data,
            tooltip=(
                f"{sys_consts.SDELIM}{video_user_data.video_path}{sys_consts.SDELIM}"
                if self._display_filename
                else ""
            ),
        )

        file_grid.value_set(
            value=str(video_user_data.encoding_info.video_width),
            row=row_index,
            col=file_grid.colindex_get("width"),
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=str(video_user_data.encoding_info.video_height),
            row=row_index,
            col=file_grid.colindex_get("height"),
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=(
                video_user_data.encoding_info.video_format
                + f":{ video_user_data.encoding_info.video_scan_order}"
                if video_user_data.encoding_info.video_scan_order != ""
                else ""
            ),
            row=row_index,
            col=file_grid.colindex_get("encoder"),
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=duration,
            row=row_index,
            col=file_grid.colindex_get("duration"),
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=video_user_data.encoding_info.video_standard,
            row=row_index,
            col=file_grid.colindex_get("standard"),
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=(
                f"{video_user_data.video_file_settings.menu_group}"
                if video_user_data.video_file_settings.menu_group >= 0
                else ""
            ),
            row=row_index,
            col=file_grid.colindex_get("group"),
            user_data=video_user_data,
        )

        file_grid.userdata_set(
            row=row_index,
            col=file_grid.colindex_get("settings"),
            user_data=video_user_data,
        )

    def _set_project_standard_duration(self, event: qtg.Action) -> None:
        """
        Sets the duration and video standard for the current project based on the selected
        input video files.

        Args:
            event (qtg.Action): The calling event.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )
        total_duration = 0
        self.project_video_standard = ""
        self.project_duration = ""
        self.dvd_percent_used = 0

        if file_grid.row_count > 0:
            for row_index, checked_item in enumerate(file_grid.checkitems_get):
                checked_item: qtg.Grid_Item
                video_data: Video_Data = checked_item.user_data

                encoding_info = video_data.encoding_info

                total_duration += encoding_info.video_duration

            encoding_info = file_grid.userdata_get(
                row=0, col=file_grid.colindex_get("settings")
            ).encoding_info
            self.project_video_standard = encoding_info.video_standard

            self.project_duration = str(
                datetime.timedelta(seconds=total_duration)
            ).split(".")[0]
            self.dvd_percent_used = (
                round(
                    (
                        (sys_consts.AVERAGE_BITRATE * total_duration)
                        / sys_consts.SINGLE_SIDED_DVD_SIZE
                    )
                    * 100
                )
                + sys_consts.PERCENT_SAFTEY_BUFFER
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
            value=f"{sys_consts.SDELIM}{self.project_duration}{sys_consts.SDELIM}",
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
            tag="control_buttons", align=qtg.Align.RIGHT, margin_right=0
        ).add_row(
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
            qtg.Button(
                icon=file_utils.App_Path("film.svg"),
                tag="join_files",
                callback=self.event_handler,
                tooltip="Join The Selected Files",
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
                width=64,
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
            tag="video_file_controls", align=qtg.Align.TOPLEFT, margin_right=20
        )

        file_control_container.add_row(
            qtg.Checkbox(
                text="Select All",
                tag="bulk_select",
                callback=self.event_handler,
                width=11,
            ),
            qtg.Grid(
                tag="video_input_files",
                noselection=True,
                height=10,
                col_def=file_col_def,
                callback=self.grid_events,
            ),
        )

        control_container = qtg.VBoxContainer(
            tag="control_container",
            text="DVD Input Files",
            align=qtg.Align.TOPRIGHT,
            margin_left=9,
        ).add_row(file_control_container, button_container)

        return control_container
