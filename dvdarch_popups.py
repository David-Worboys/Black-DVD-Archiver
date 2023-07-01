"""
    Black DVD archiver task popup windows.
        
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
import sys
from typing import Optional, cast

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from configuration_classes import DVD_Menu_Settings, Video_Data

# fmt: on


@dataclasses.dataclass
class Menu_Page_Title_Popup(qtg.PopContainer):
    """Gets the Menu Title for Each Page In The DVD Menu"""

    tag: str = "Menu_Title_Popup"

    video_data_list: list[Video_Data] = dataclasses.field(
        default_factory=list
    )  # Pass by reference
    menu_layout: list[tuple[str, list[Video_Data]]] = dataclasses.field(
        default_factory=list
    )  # Pass by reference

    # Private instance variable
    _db_settings: sqldb.App_Settings | None = None
    _current_button_grid: Optional[qtg.Grid] = None

    def __post_init__(self) -> None:
        """Sets-up the form"""
        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        assert (
            isinstance(self.video_data_list, list) and len(self.video_data_list) > 0
        ), f"{self.video_data_list=}. Must be a non-empty list of Video_Data instances"
        assert all(
            isinstance(video_data, Video_Data) for video_data in self.video_data_list
        ), "All elements must be Video_Data instances"

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  form events
        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                self._post_open_handler(event)

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        if self._process_ok(event) == 1:
                            self.set_result("ok")
                            super().close()
                    case "cancel":
                        if self._process_cancel(event) == 1:
                            self.set_result("cancel")
                            super().close()
                    case "button_title_grid":
                        if hasattr(event.value, "grid"):
                            self._current_button_grid: qtg.Grid = event.value.grid
                    case "move_menu_up":
                        menu_grid: qtg.Grid = event.widget_get(
                            container_tag="menu_page_controls", tag="menu_titles"
                        )

                        new_row = menu_grid.move_row_up(menu_grid.selected_row)

                        if new_row >= 0:
                            menu_grid.select_row(new_row)
                    case "move_menu_down":
                        menu_grid: qtg.Grid = event.widget_get(
                            container_tag="menu_page_controls", tag="menu_titles"
                        )

                        new_row = menu_grid.move_row_down(menu_grid.selected_row)

                        if new_row >= 0:
                            menu_grid.select_row(new_row)
                    case "move_button_title_down":
                        if self._current_button_grid is not None:
                            self._move_button_title(
                                button_title_grid=self._current_button_grid,
                                up=False,
                            )
                    case "move_button_title_up":
                        if self._current_button_grid is not None:
                            self._move_button_title(
                                button_title_grid=self._current_button_grid,
                                up=True,
                            )

            case qtg.Sys_Events.CLEAR_TYPING_BUFFER:
                if isinstance(event.value, qtg.Grid_Col_Value):
                    grid_col_value: qtg.Grid_Col_Value = event.value

                    menu_title: str = grid_col_value.value
                    row = grid_col_value.row
                    col = grid_col_value.col
                    user_data = grid_col_value.user_data

                    menu_title_grid: qtg.Grid = event.widget_get(
                        container_tag="menu_page_controls",
                        tag="menu_titles",
                    )

                    menu_title_grid.value_set(
                        value=menu_title, row=row, col=col, user_data=user_data
                    )

    def _post_open_handler(self, event: qtg.Action) -> None:
        """
        The _post_open_handler method is called after the window has opened.

        Creates a new row in the menu_titles grid for each DVD menu page of videos sourced from video_data_list.

        The number of buttons per page is determined by DVD_Menu_Settings().buttons_per_page, which defaults to 6.
        If there are more videos than buttons_per_page, it will add another row and continue until all videos have been
        added.

        Args:
            event (qtg.Action): The triggering event.

        """
        max_group_id = -1
        min_group_id = sys.maxsize
        temp_video_list = self.video_data_list.copy()

        for item in temp_video_list:
            if item.video_file_settings.menu_group > max_group_id:
                max_group_id = item.video_file_settings.menu_group
            if item.video_file_settings.menu_group < min_group_id:
                min_group_id = item.video_file_settings.menu_group

        if min_group_id >= 0 and max_group_id < sys.maxsize:  # Have groups
            group_id = min_group_id
            start_row = 0
            for row, item in enumerate(temp_video_list):  # Fill in blank groups
                if item.video_file_settings.menu_group == -1:  # Blank group
                    # Fill in blank group with the group_id of the prior non-blank group
                    for inner_row in range(start_row, len(temp_video_list)):
                        temp_item = temp_video_list[inner_row]
                        temp_item.video_file_settings.menu_group = group_id
                        if inner_row == row:
                            start_row = inner_row + 1
                            break
                    group_id += 1
                else:
                    group_id = item.video_file_settings.menu_group

            temp_video_list.sort(key=lambda item: item.video_file_settings.menu_group)

        dvd_menu_settings = DVD_Menu_Settings()
        menu_title_grid: qtg.Grid = event.widget_get(
            container_tag="menu_page_controls",
            tag="menu_titles",
        )

        buttons_per_page = dvd_menu_settings.buttons_per_page
        button_pages = []
        videos = []

        # Allocate videos to a menu page
        for video_index, video in enumerate(temp_video_list):
            videos.append(video)

            # Check if a new page should start or a group break has occurred
            if len(videos) >= buttons_per_page or (
                video_index + 1 < len(temp_video_list)
                and video.video_file_settings.menu_group
                != temp_video_list[video_index + 1].video_file_settings.menu_group
            ):
                button_pages.append(videos)
                videos = []

        # Add any remaining videos if not enough for a full page
        if len(videos) > 0:
            button_pages.append(videos)

        for row, menu_page in enumerate(button_pages):
            row_grid = qtg.Grid(
                tag="row_grid",
                height=buttons_per_page + 1,
                col_def=[
                    qtg.Col_Def(
                        label="Button Title",
                        tag="button_title_grid",
                        width=30,
                        editable=True,
                        checkable=True,
                    )
                ],
                callback=self.event_handler,
            )

            control_box = qtg.VBoxContainer(
                tag="control_box",
                width=10,
                height=buttons_per_page + 3,
                align=qtg.Align.TOPRIGHT,
            ).add_row(
                row_grid,
                qtg.HBoxContainer(tag="command_buttons", margin_right=0).add_row(
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-up.svg"),
                        tag=f"move_button_title_up",
                        callback=self.event_handler,
                        tooltip="Move This Button Title Up!",
                        width=2,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-down.svg"),
                        tag="move_button_title_down",
                        callback=self.event_handler,
                        tooltip="Move This Button Title Down!",
                        width=2,
                    ),
                ),
            )

            menu_title_grid.row_widget_set(row=row, col=1, widget=control_box)

            for grid_row, video_data in enumerate(menu_page):
                row_grid.value_set(
                    row=grid_row,
                    col=0,
                    value=video_data.video_file_settings.button_title,
                    user_data=video_data,
                )

        menu_title_grid.select_row(0, 0)

    def _move_button_title(self, button_title_grid: qtg.Grid, up: bool) -> None:
        """
        Move the selected button title up or down in the button title grid on a given row.

        Args:
            button_title_grid (qtg.Grid): The button title grid on a given row
            up (bool): True to move the edit point up, False to move it down.

        """
        assert isinstance(up, bool), f"{up=}. Must be bool"

        checked_items: tuple[qtg.Grid_Item] = (
            button_title_grid.checkitems_get
            if up
            else tuple(reversed(button_title_grid.checkitems_get))
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
                title="Selected Button Titles Not Contiguous...",
                message="Selected Button Titles Must Be A Contiguous Block!",
            ).show()
            return None

        for checked_item in checked_items:
            if up:
                if checked_item.row_index == 0:
                    break
            else:
                if checked_item.row_index == button_title_grid.row_count - 1:
                    break

            button_title_grid.checkitemrow_set(False, checked_item.row_index, 0)
            button_title_grid.select_row(checked_item.row_index)

            if up:
                new_row = button_title_grid.move_row_up(checked_item.row_index)
            else:
                new_row = button_title_grid.move_row_down(checked_item.row_index)

            if new_row >= 0:
                button_title_grid.checkitemrow_set(True, new_row, 0)
                button_title_grid.select_col(new_row, 0)
            else:
                button_title_grid.checkitemrow_set(True, checked_item.row_index, 0)
                button_title_grid.select_col(checked_item.row_index, 0)

    def _process_cancel(self, event: qtg.Action) -> int:
        """
        Handles processing the cancel button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if cancel process is ok, -1 otherwise.
        """
        if (
            popups.PopYesNo(
                title="Discard Changes..", message="Discard Changes & Stop DVD Build?"
            ).show()
            == "ok"
        ):
            return 1
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

        menu_title_grid: qtg.Grid = event.widget_get(
            container_tag="menu_page_controls",
            tag="menu_titles",
        )

        deactivate_switch: qtg.Switch = event.widget_get(
            container_tag="menu_move", tag="deactivate_filters"
        )

        menu_title_col_index = menu_title_grid.colindex_get("menu_title")
        video_titles_col_index = menu_title_grid.colindex_get("videos_on_page")
        result = ""

        for row in range(menu_title_grid.row_count):
            menu_title = menu_title_grid.value_get(row=row, col=menu_title_col_index)
            row_grid = cast(
                qtg.Grid,
                menu_title_grid.row_widget_get(
                    row=row,
                    col=video_titles_col_index,
                    container_tag="control_box",
                    tag="row_grid",
                ),
            )
            menu_items = []
            for row in range(row_grid.row_count):
                button_title = row_grid.value_get(row=row, col=0)
                video_data = row_grid.userdata_get(row=row, col=0)

                if (
                    video_data.video_file_settings.button_title.strip()
                    != button_title.strip()
                ):
                    video_data.video_file_settings.button_title = button_title

                video_data.video_file_settings.deactivate_filters = False
                if deactivate_switch.value_get():
                    video_data.video_file_settings.deactivate_filters = True

                menu_items.append(video_data)

            self.menu_layout.append((menu_title, menu_items.copy()))

            for row_index, menu_item in enumerate(self.menu_layout):
                if menu_item[0].strip() == "":
                    if (
                        popups.PopYesNo(
                            title="Menu Page Title Not Entered..",
                            message=(
                                "Menu "
                                f" {sys_consts.SDELIM}{row_index + 1}{sys_consts.SDELIM} Title"
                                " Has Not Been Entered. Continue?"
                            ),
                        ).show()
                        == "no"
                    ):
                        menu_title_grid.select_row(row_index, menu_title_col_index)
                        return -1
        return 1

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        menu_page_control_container = qtg.VBoxContainer(
            tag="menu_page_controls", align=qtg.Align.TOPLEFT
        )

        file_col_def = (
            qtg.Col_Def(
                label="Menu Title",
                tag="menu_title",
                width=30,
                editable=True,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Videos On Menu",
                tag="videos_on_page",
                width=35,
                editable=False,
                checkable=False,
            ),
        )

        menu_titles = qtg.Grid(
            tag="menu_titles",
            noselection=True,
            height=15,
            col_def=file_col_def,
            callback=self.event_handler,
        )

        menu_page_control_container.add_row(
            menu_titles,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )

        control_container.add_row(
            menu_page_control_container,
            qtg.HBoxContainer(tag="menu_move", margin_right=5).add_row(
                qtg.HBoxContainer().add_row(
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-up.svg"),
                        tag="move_menu_up",
                        callback=self.event_handler,
                        tooltip="Move This Menu Up!",
                        width=2,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-down.svg"),
                        tag="move_menu_down",
                        callback=self.event_handler,
                        tooltip="Move This Menu Down!",
                        width=2,
                    ),
                    qtg.Spacer(width=2),
                    qtg.Switch(
                        tag="deactivate_filters",
                        buddy_control=qtg.Label(
                            tag="switch_label", text="Deactivate Filters", width=20
                        ),
                    ),
                    qtg.Spacer(width=13),
                ),
                qtg.Command_Button_Container(
                    ok_callback=self.event_handler, cancel_callback=self.event_handler
                ),
            ),
        )

        return control_container


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

                    file_grid: qtg.Grid = event.widget_get(
                        container_tag="file_controls",
                        tag="video_input_files",
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls", tag="video_input_files"
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls",
            tag="video_input_files",
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls", tag="video_input_files"
        )

        col_index: int = file_grid.colindex_get("new_file_name")

        for row_index in range(file_grid.row_count):
            user_entered_file_name: str = file_grid.value_get(row_index, col_index)

            if user_entered_file_name.strip() != "":
                self.video_data_list[row_index].video_file = user_entered_file_name
                self.video_data_list[row_index].video_file_settings.button_title = (
                    file_handler.extract_title(user_entered_file_name)
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

                if result == 1:
                    popups.PopMessage(
                        title="Rename Files...", message="Files Renamed Successfully"
                    ).show()
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

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls",
            tag="video_input_files",
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
                popups.PopError(title="Invalid File Name...", message=error_msg).show()
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
