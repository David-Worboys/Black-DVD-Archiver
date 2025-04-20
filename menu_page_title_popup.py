"""
Implements a popup dialog that allows users to configure the page and button
titles for a DVD menu.

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
from typing import Optional, cast

import platformdirs

import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups
import QTPYGUI.qtpygui as qtg
import QTPYGUI.sqldb as sqldb
import sys_consts
from dvdarch_utils import DVD_Percent_Used
from print_popup import Print_DVD_Label_Popup
from sys_config import (
    DVD_Menu_Settings,
    Get_Shelved_DVD_Layout,
    Set_Shelved_DVD_Layout,
    Video_Data,
    DVD_Menu_Page,
)


@dataclasses.dataclass
class Menu_Page_Title_Popup(qtg.PopContainer):
    """Gets the Menu Title for Each Page In The DVD Menu"""

    tag: str = "Menu_Title_Popup"

    video_data_list: list[Video_Data] = dataclasses.field(
        default_factory=list
    )  # Pass by reference
    menu_layout: list[tuple[str, list[Video_Data], any]] = dataclasses.field(
        default_factory=list
    )  # Pass by reference
    project_name: str = ""
    dvd_layout_name: str = ""

    # Private instance variable
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _db_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)
    _current_button_grid: Optional[qtg.Grid] = None

    def __post_init__(self) -> None:
        """Sets-up the form"""
        self.container = self.layout()

        assert isinstance(self.video_data_list, list), (
            f"{self.video_data_list=}. Must be a list of Video_Data instances"
        )
        assert all(
            isinstance(video_data, Video_Data) for video_data in self.video_data_list
        ), "All elements must be Video_Data instances"
        assert isinstance(self.project_name, str) and self.project_name.strip() != "", (
            f"{self.project_name=}. Must be non-empty str"
        )

        assert (
            isinstance(self.dvd_layout_name, str) and self.dvd_layout_name.strip() != ""
        ), f"{self.dvd_layout_name=}. Must be non-empty str"

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  form events

        Args:
            event (qtg.Action): The triggering event

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                ok_button: qtg.Button = cast(
                    qtg.Button,
                    event.widget_get(container_tag="command_buttons", tag="ok"),
                )
                ok_button.text_set("Make A DVD")
                ok_button.icon_set(file_utils.App_Path("compact-disc.svg"))

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
                    case "delete_menu_page":
                        self._delete_menu_page(event)
                    case "delete_video_title":
                        if self._current_button_grid is not None:
                            self._remove_video_title(self._current_button_grid)
                    case "menu_43":
                        self._db_settings.setting_set(
                            sys_consts.MENU_ASPECT_RATIO_DBK, sys_consts.AR43
                        )
                    case "menu_169":
                        self._db_settings.setting_set(
                            sys_consts.MENU_ASPECT_RATIO_DBK, sys_consts.AR169
                        )
                    case "move_menu_up":
                        menu_grid: qtg.Grid = cast(
                            qtg.Grid,
                            event.widget_get(
                                container_tag="menu_page_controls", tag="menu_titles"
                            ),
                        )
                        self._move_grid_row(menu_grid, True)

                    case "move_menu_down":
                        menu_grid: qtg.Grid = cast(
                            qtg.Grid,
                            event.widget_get(
                                container_tag="menu_page_controls", tag="menu_titles"
                            ),
                        )
                        self._move_grid_row(menu_grid, False)

                    case "move_button_title_down":
                        if self._current_button_grid is not None:
                            self._move_grid_row(
                                source_grid=self._current_button_grid,
                                up=False,
                            )
                    case "move_button_title_up":
                        if self._current_button_grid is not None:
                            self._move_grid_row(
                                source_grid=self._current_button_grid,
                                up=True,
                            )
                    case "print_disk":
                        disk_title: qtg.LineEdit = cast(
                            qtg.LineEdit,
                            event.widget_get(
                                container_tag="menu_page_controls",
                                tag="disk_title",
                            ),
                        )

                        result = Print_DVD_Label_Popup(
                            disk_title=disk_title.value_get(),
                            dvd_menu_pages=self._get_menu_pages(event=event),
                        ).show()

                    case "save_layout":
                        if (
                            popups.PopYesNo(
                                title="Save DVD Layout...",
                                message="Save The DVD Layout?",
                            ).show()
                            == "yes"
                        ):
                            self._save_dvd_menu(event)

            case qtg.Sys_Events.CLEAR_TYPING_BUFFER:
                if isinstance(event.value, qtg.Grid_Col_Value):
                    grid_col_value: qtg.Grid_Col_Value = event.value

                    menu_title: str = grid_col_value.value
                    row = grid_col_value.row
                    col = grid_col_value.col
                    user_data = grid_col_value.user_data

                    menu_title_grid: qtg.Grid = cast(
                        qtg.Grid,
                        event.widget_get(
                            container_tag="menu_page_controls",
                            tag="menu_titles",
                        ),
                    )

                    menu_title_grid.value_set(
                        value=menu_title, row=row, col=col, user_data=user_data
                    )

    def _post_open_handler(self, event: qtg.Action) -> None:
        """
        The _post_open_handler method is called after the window has opened.
        Creates a new row in the menu_titles grid for each DVD menu page of videos sourced from video_data_list.
        The number of buttons per page is determined by DVD_Menu_Settings().buttons_per_page.
        If there are more videos than buttons_per_page, it will add another row and continue until all videos have been
        added.

        Args:
            event (qtg.Action): The triggering event.
        """

        # #### Helper functions
        def _load_menu_pages(
            menu_title: str,
            menu_dict: dict,
            buttons_per_page: int,
            video_data: list[Video_Data],
            menu_pages: list[list[Video_Data]],
            page_title: list[tuple[str, dict, list[Video_Data]]],
        ):
            """Loads the menu_pages list and page_title with the videos for the button titles and the page titles.

            Args:
                menu_title (str): The title of a DVD menu page
                menu_dict (dict): Dictionary of settings
                buttons_per_page (int): Number of buttons allowed on a DVD page
                video_data (list[Video_Data]): THe video files on a DVD page
                menu_pages (list[list[Video_Data]]): The DVD menu layout
                page_title (list[tuple[str, dict, list[Video_Data]]]): Thr title of each DVD menu page and associated
                    variables

            Returns:

            """
            if len(video_data) >= buttons_per_page:
                page_data_list: list[Video_Data] = []
                title_count = 0
                for video_index, video_item in enumerate(video_data):
                    title_count += 1
                    page_data_list.append(video_item)
                    if (
                        title_count == buttons_per_page
                        or video_index == len(video_data) - 1
                    ):
                        menu_pages.append(page_data_list)
                        page_title.append((
                            menu_title,
                            menu_dict,
                            page_data_list,
                        ))
                        page_data_list = []
                        title_count = 0
            else:
                menu_pages.append(video_data)
                page_title.append((
                    menu_title,
                    menu_dict,
                    video_data,
                ))

            return None

        # #### Main
        menu_title_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="menu_titles",
            ),
        )

        disk_title_lineedit: qtg.LineEdit = cast(
            qtg.LineEdit,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="disk_title",
            ),
        )

        buttons_per_page = DVD_Menu_Settings().buttons_per_page

        dvd_menu_layout: list[DVD_Menu_Page] = self._load_DVD_menu(event)

        files_in_dvd_layout: list[tuple[str, dict, list[Video_Data]]] = []
        files_not_in_dvd_layout: list[tuple[str, dict, list[Video_Data]]] = []

        # Load files details from the stored dvd layout
        for row_index, menu_page in enumerate(dvd_menu_layout):
            if row_index == 0 and "disk_title" in menu_page.user_data:
                disk_title_lineedit.value_set(menu_page.user_data["disk_title"])

            button_videos: list[Video_Data] = []

            for button_item in menu_page.get_button_titles.values():
                button_videos.append(button_item[1])

            files_in_dvd_layout.append((
                menu_page.menu_title,
                menu_page.user_data,
                button_videos,
            ))

        # Find files selected in the file grid which are not in the stored dvd grid layout
        file_grid_videos: list[Video_Data] = []
        ungrouped_file_grid_videos: list[Video_Data] = []
        for video_item in self.video_data_list:
            if not [
                item
                for item in files_in_dvd_layout
                if video_item.video_path
                in [button_item.video_path for button_item in item[2]]
            ]:
                if video_item.video_file_settings.menu_group == -1:
                    ungrouped_file_grid_videos.append(video_item)
                else:
                    file_grid_videos.append(video_item)

        file_grid_videos.sort(key=lambda item: item.video_file_settings.menu_group)
        file_grid_videos.extend(ungrouped_file_grid_videos)

        if file_grid_videos:
            files_not_in_dvd_layout.append((
                "",
                {},
                file_grid_videos,
            ))

        merged_files = []

        # Load grid/dvd layout into merged_files
        for file_in_grid in files_in_dvd_layout:
            menu_title = file_in_grid[0]
            menu_dict = file_in_grid[1]

            merged_files.append((menu_title, menu_dict, file_in_grid[2]))

        # Insert files not in dvd layout into merged files
        for file_not_in_dvd_layout in files_not_in_dvd_layout:
            for video_item in file_not_in_dvd_layout[2]:
                found = False
                for file_in_grid in merged_files:
                    for button_video in file_in_grid[2]:
                        if (
                            button_video.video_file_settings.menu_group
                            == video_item.video_file_settings.menu_group
                            and button_video.encoding_info.video_ar
                            == video_item.encoding_info.video_ar
                        ):
                            file_in_grid[2].append(video_item)

                            found = True
                            break
                    if found:
                        break

                if not found:
                    merged_files.append(("", {}, [video_item]))

        menu_pages: list[list[Video_Data]] = []
        page_title: list[tuple[str, dict, list[Video_Data]]] = []
        item_index = 0
        total_duration = 0.0
        dvd_percent_used = 0

        # Check if the files will fit on the DVD
        for item_index, item in enumerate(merged_files):
            for video_item in item[2]:
                total_duration += video_item.encoding_info.video_duration
                dvd_percent_used = DVD_Percent_Used(
                    total_duration=total_duration,
                    pop_error_message=True,
                )

                if dvd_percent_used > 100:
                    break
            if dvd_percent_used > 100:
                break

        if dvd_percent_used > 100:  # Trim merged files to fit on DVD - bit brutal!
            merged_files = merged_files[:item_index]

        for item in merged_files:
            _load_menu_pages(
                menu_title=item[0],
                menu_dict=item[1],
                buttons_per_page=buttons_per_page,
                video_data=item[2],
                menu_pages=menu_pages,
                page_title=page_title,
            )

        self._insert_video_title_control(
            menu_title_grid=menu_title_grid, menu_pages=menu_pages
        )

        for row_index, item in enumerate(page_title):
            menu_title_grid.value_set(
                row=row_index,
                col=0,
                value=item[0],
                user_data=item[1],
            )

        return None

    def _insert_video_title_control(
        self,
        menu_title_grid: qtg.Grid,
        menu_pages: list[list[Video_Data]],
    ) -> None:
        """Inserts a video title control box into the main menu grid

        Args:
            menu_title_grid (qtg.Grid): The main menu grid that holds menu pages
            menu_pages (list[list[Video_Data]]): The menu pages that populate a video title control box
        """
        assert isinstance(menu_title_grid, qtg.Grid), (
            f"{menu_title_grid=}. Must be an instance of qtg.Grid"
        )
        assert isinstance(menu_pages, list), f"{menu_pages=}. Must be a list"

        file_handler = file_utils.File()
        buttons_per_page: int = DVD_Menu_Settings().buttons_per_page
        video_titles_col_index = menu_title_grid.colindex_get("videos_on_page")

        for row_index, menu_page in enumerate(menu_pages):
            row_grid = qtg.Grid(
                tag="row_grid",
                height=buttons_per_page + 1,
                col_def=[
                    qtg.Col_Def(
                        label="Button Title",
                        tag="button_title_grid",
                        width=33,
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
                qtg.HBoxContainer(
                    tag=f"rg_command_buttons_{row_index}", margin_right=0
                ).add_row(
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-up.svg"),
                        tag="move_button_title_up",
                        callback=self.event_handler,
                        tooltip="Move Selected Button Title Up",
                        width=2,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-down.svg"),
                        tag="move_button_title_down",
                        callback=self.event_handler,
                        tooltip="Move Selected Button Title Down",
                        width=2,
                    ),
                    qtg.Spacer(width=1),
                    qtg.Button(
                        icon=file_utils.App_Path("x.svg"),
                        tag="delete_video_title",
                        callback=self.event_handler,
                        tooltip="Remove Selected Video Title From The DVD Menu",
                        width=2,
                    ),
                ),
            )

            menu_title_grid.row_widget_set(
                row=row_index, col=video_titles_col_index, widget=control_box
            )

            missing_files = []

            for grid_row, video_data in enumerate(menu_page):
                if not file_handler.file_exists(
                    directory_path=video_data.video_folder,
                    file_name=video_data.video_file,
                    file_extension=video_data.video_extension,
                ):
                    missing_files.append(video_data.video_path)
                    continue

                row_grid.value_set(
                    row=grid_row,
                    col=0,
                    value=video_data.video_file_settings.button_title,
                    user_data=video_data,
                )

            if missing_files:
                missing_file_list = "\n".join(missing_files)
                popups.PopMessage(
                    title="Missing DVD Menu Files...",
                    message=(
                        "The Following DVD Menu Source Files Are Missing And Have Been"
                        " Removed:\n"
                        f"{sys_consts.SDELIM}{missing_file_list}{sys_consts.SDELIM}"
                    ),
                    width=80,
                ).show()

            row_grid.changed = False

        menu_title_grid.select_row(0, 0)

        return None

    def _load_DVD_menu(self, event: qtg.Action) -> list[DVD_Menu_Page]:
        """Reads the DVD menu pages Video_Data definitions from the project database shelve file

        Args:
            event (qtg.Action): The event that triggered the load of the DVD menu

        Returns:
            list[DVD_Menu_Page]: The DVD menu page Video_Data definitions loaded from the database
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            dvd_menu_layout, error_message = Get_Shelved_DVD_Layout(
                project_name=self.project_name, dvd_layout_name=self.dvd_layout_name
            )

        if error_message:
            popups.PopError(
                title="DVD Menu Grid Load Error...",
                message=f"{sys_consts.SDELIM}{str(error_message)}{sys_consts.SDELIM}",
            ).show()

        return dvd_menu_layout

    def _move_grid_row(self, source_grid: qtg.Grid, up: bool) -> None:
        """
        Move the selected button title up or down in the button title grid on a given row.

        Args:
            source_grid (qtg.Grid): The grid with the row to move up or down depending on up
            up (bool): True to move the edit point up, False to move it down.
        """
        assert isinstance(up, bool), f"{up=}. Must be bool"

        checked_items: tuple[qtg.Grid_Item] = (
            source_grid.checkitems_get
            if up
            else tuple(reversed(source_grid.checkitems_get))
        )

        assert all(isinstance(item, qtg.Grid_Item) for item in checked_items), (
            f"{checked_items=}. Must be a list of'qtg.Grid_Item_Tuple'"
        )

        if not checked_items:
            popups.PopMessage(
                title="Select An Edit Point...",
                message="Please Check An Edit Point To Move!",
            ).show()
            return None

        checked_indices: list[int] = [item.row_index for item in checked_items]

        index_range: list[int] = (
            list(range(min(checked_indices), max(checked_indices) + 1))
            if up
            else list(range(max(checked_indices), min(checked_indices) - 1, -1))
        )

        if (
            len(checked_indices) > 1 and checked_indices != index_range
        ):  # Contiguous block check failed
            popups.PopMessage(
                title="Selected Rows Not Contiguous...",
                message="Selected Rows Must Be A Contiguous Block!",
            ).show()
            return None

        for checked_item in checked_items:
            if up:
                if checked_item.row_index == 0:
                    break
            else:
                if checked_item.row_index == source_grid.row_count - 1:
                    break

            source_grid.checkitemrow_set(False, checked_item.row_index, 0)
            source_grid.select_row(checked_item.row_index)

            if up:
                new_row = source_grid.move_row_up(checked_item.row_index)
            else:
                new_row = source_grid.move_row_down(checked_item.row_index)

            if new_row >= 0:
                source_grid.checkitemrow_set(True, new_row, 0)
                source_grid.select_col(new_row, 0)
            else:
                source_grid.checkitemrow_set(True, checked_item.row_index, 0)
                source_grid.select_col(checked_item.row_index, 0)

        return None

    def _process_cancel(self, event: qtg.Action) -> int:
        """
        Handles processing the cancel button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if cancel process is ok, -1 otherwise.
        """
        menu_title_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="menu_titles",
            ),
        )
        video_titles_col_index = menu_title_grid.colindex_get("videos_on_page")

        changed = menu_title_grid.changed

        if not changed:
            for row in range(menu_title_grid.row_count):
                row_grid: qtg.Grid | None = menu_title_grid.row_widget_get(
                    row=row,
                    col=video_titles_col_index,
                    container_tag="control_box",
                    tag="row_grid",
                )

                if row_grid is not None and row_grid.changed:
                    changed = True
                    break

        if changed:
            if (
                popups.PopYesNo(
                    title="Discard Changes..",
                    message="Discard Changes & Stop The DVD Build?",
                ).show()
                == "no"
            ):
                return -1
        return 1

    def _process_ok(self, event: qtg.Action) -> int:
        """
        Handles processing the ok button.

        Args:
            event (qtg.Action): The triggering event.

        Returns:
            int: Returns 1 if the ok process is good, -1 otherwise
        """

        self.set_result("")

        menu_title_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="menu_titles",
            ),
        )

        disk_title_lineedit: qtg.LineEdit = cast(
            qtg.LineEdit,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="disk_title",
            ),
        )

        deactivate_switch: qtg.Switch = cast(
            qtg.Switch,
            event.widget_get(container_tag="menu_controls", tag="deactivate_filters"),
        )

        menu_title_col_index = menu_title_grid.colindex_get("menu_title")
        video_titles_col_index = menu_title_grid.colindex_get("videos_on_page")

        if (
            popups.PopYesNo(
                title="Generate DVD..",
                message="Generate And Archive The DVD?",
            ).show()
            == "no"
        ):
            return -1

        for row_index, menu_item in enumerate(self.menu_layout):
            # Keeping pycharm types happy
            row_index: int
            menu_item: tuple[str, list[Video_Data]]

            if not menu_item[0].strip():
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

        for row in range(menu_title_grid.row_count):
            menu_title = menu_title_grid.value_get(row=row, col=menu_title_col_index)
            menu_title_user_data = menu_title_grid.userdata_get(
                row=row,
                col=menu_title_col_index,
            )

            # Popup specific values can be stored here
            if menu_title_user_data is None:
                menu_title_user_data = {"disk_title": disk_title_lineedit.value_get()}
            else:
                menu_title_user_data["disk_title"] = disk_title_lineedit.value_get()

            row_grid: qtg.Grid | None = menu_title_grid.row_widget_get(
                row=row,
                col=video_titles_col_index,
                container_tag="control_box",
                tag="row_grid",
            )

            menu_items = []
            for row_grid_row in range(row_grid.row_count):
                button_title: str = row_grid.value_get(row=row_grid_row, col=0)
                video_data: Video_Data = row_grid.userdata_get(row=row_grid_row, col=0)
                video_data.dvd_page = row

                if (
                    video_data.video_file_settings.button_title.strip()
                    != button_title.strip()
                ):
                    video_data.video_file_settings.button_title = button_title

                video_data.video_file_settings.deactivate_filters = False
                if deactivate_switch.value_get():
                    video_data.video_file_settings.deactivate_filters = True

                menu_items.append(video_data)

            self.menu_layout.append((
                menu_title,
                menu_items.copy(),
                menu_title_user_data,
            ))

        self._save_dvd_menu(event)

        return 1

    def _delete_menu_page(
        self,
        event: qtg.Action,
    ) -> None:
        """Removes the selected video_title

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), (
            f"{event=}. Must be an instance of qtg.Action"
        )

        menu_title_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="menu_titles",
            ),
        )

        if not menu_title_grid.checkitems_get:
            popups.PopMessage(
                title="Select Menu Page...", message="Select Menu Pages To Delete"
            ).show()
            return None

        if (
            menu_title_grid.row_count > 0
            and menu_title_grid.checkitems_get
            and popups.PopYesNo(
                title="Remove Selected...",
                message="Remove The Selected Menu Pages?",
            ).show()
            == "yes"
        ):
            for item in reversed(menu_title_grid.checkitems_get):
                item: qtg.Grid_Item

                menu_title_grid.row_delete(item.row_index)

        return None

    def _remove_video_title(
        self,
        button_title_grid: qtg.Grid,
    ) -> None:
        """Removes the selected video_title

        Args:
            button_title_grid (qtg.Grid): The button title grid on a given row
        """
        assert isinstance(button_title_grid, qtg.Grid), (
            f"{button_title_grid=}. Must be an instance of qtg.Grid"
        )

        if not button_title_grid.checkitems_get:
            popups.PopMessage(
                title="Select Video Title...", message="Select Video Titles To Delete"
            ).show()
            return None

        if (
            button_title_grid.row_count > 0
            and button_title_grid.checkitems_get
            and popups.PopYesNo(
                title="Remove Selected...",
                message="Remove The Selected Video Title?",
            ).show()
            == "yes"
        ):
            for item in reversed(button_title_grid.checkitems_get):
                item: qtg.Grid_Item
                button_title_grid.row_delete(item.row_index)

        return None

    def _get_menu_pages(self, event: qtg.Action) -> list[DVD_Menu_Page]:
        """Returns a list  of menu pages

        Args:
            event (qtg.Action): The triggering event

        Returns:
            list[DVD_Menu_Page]: List of DVD menu pages

        """
        menu_title_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="menu_titles",
            ),
        )

        disk_title_lineedit: qtg.LineEdit = cast(
            qtg.LineEdit,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="disk_title",
            ),
        )

        menu_titles_col_index = menu_title_grid.colindex_get("menu_title")
        video_titles_col_index = menu_title_grid.colindex_get("videos_on_page")

        row_data = []
        menu_pages: list[DVD_Menu_Page] = []
        for row in range(menu_title_grid.row_count):
            menu_page = DVD_Menu_Page()
            menu_list: list[
                tuple[str, tuple[tuple[str, Video_Data], ...], dict[str, str]]
            ] = []
            menu_title = ""
            menu_title_user_data = {}

            for col in range(menu_title_grid.col_count):
                # grid_user_data = menu_title_grid.userdata_get(row=row, col=col)
                if col == menu_titles_col_index:
                    menu_title: str = menu_title_grid.value_get(row=row, col=col)
                    menu_title_user_data: dict[str, str] = menu_title_grid.userdata_get(
                        row=row,
                        col=menu_titles_col_index,
                    )

                    menu_page.menu_title = menu_title
                    menu_page.user_data = menu_title_user_data

                    # Popup specific values can be stored here
                    if menu_title_user_data is None:
                        menu_title_user_data = {
                            "disk_title": disk_title_lineedit.value_get()
                        }
                    else:
                        menu_title_user_data["disk_title"] = (
                            disk_title_lineedit.value_get()
                        )

                elif col == video_titles_col_index:
                    row_grid: qtg.Grid | None = menu_title_grid.row_widget_get(
                        row=row,
                        col=video_titles_col_index,
                        container_tag="control_box",
                        tag="row_grid",
                    )

                    button_list: list[tuple[str, Video_Data]] = []
                    button_index = 0

                    for row_grid_row in range(row_grid.row_count):
                        for row_grid_col in range(row_grid.col_count):
                            button_title: str = row_grid.value_get(
                                row=row_grid_row, col=row_grid_col
                            )

                            button_user_data: Video_Data = row_grid.userdata_get(
                                row=row_grid_row, col=row_grid_col
                            )

                            if (
                                button_user_data.video_file_settings.button_title.strip()
                                != button_title.strip()
                            ):
                                button_user_data.video_file_settings.button_title = (
                                    button_title
                                )
                            menu_page.add_button_title(
                                button_index=button_index,
                                button_title=button_title,
                                button_video_data=button_user_data,
                            )

                            button_index += 1

                            button_list.append((
                                button_title,
                                button_user_data,
                            ))

                    menu_list.append((
                        menu_title,
                        tuple(button_list),
                        menu_title_user_data,
                    ))

                    menu_pages.append(menu_page)
            row_data.append(menu_list)
        return menu_pages

    def _save_dvd_menu(self, event: qtg.Action) -> int:
        """
        Attempts to save the DVD menu layout in a project related shelf

        Args:
            event (qtg.Action): The triggering event.

        Returns:
            int: Returns 1 if ok, -1 otherwise
        """

        menu_title_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="menu_titles",
            ),
        )

        disk_title_lineedit: qtg.LineEdit = cast(
            qtg.LineEdit,
            event.widget_get(
                container_tag="menu_page_controls",
                tag="disk_title",
            ),
        )

        menu_titles_col_index = menu_title_grid.colindex_get("menu_title")
        video_titles_col_index = menu_title_grid.colindex_get("videos_on_page")

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            row_data = []
            menu_pages: list[DVD_Menu_Page] = []
            for row in range(menu_title_grid.row_count):
                menu_page = DVD_Menu_Page()
                menu_list: list[
                    tuple[str, tuple[tuple[str, Video_Data], ...], dict[str, str]]
                ] = []

                for col in range(menu_title_grid.col_count):
                    if col == menu_titles_col_index:
                        menu_title: str = menu_title_grid.value_get(row=row, col=col)
                        menu_title_user_data: dict[str, str] = (
                            menu_title_grid.userdata_get(
                                row=row,
                                col=menu_titles_col_index,
                            )
                        )

                        menu_page.menu_title = menu_title
                        menu_page.user_data = menu_title_user_data

                        # Popup specific values can be stored here
                        if menu_title_user_data is None:
                            menu_title_user_data = {
                                "disk_title": disk_title_lineedit.value_get()
                            }
                        else:
                            menu_title_user_data["disk_title"] = (
                                disk_title_lineedit.value_get()
                            )

                    elif col == video_titles_col_index:
                        row_grid: qtg.Grid | None = menu_title_grid.row_widget_get(
                            row=row,
                            col=video_titles_col_index,
                            container_tag="control_box",
                            tag="row_grid",
                        )

                        button_list: list[tuple[str, Video_Data]] = []
                        button_index = 0

                        for row_grid_row in range(row_grid.row_count):
                            for row_grid_col in range(row_grid.col_count):
                                button_title: str = row_grid.value_get(
                                    row=row_grid_row, col=row_grid_col
                                )

                                button_user_data: Video_Data = row_grid.userdata_get(
                                    row=row_grid_row, col=row_grid_col
                                )

                                if (
                                    button_user_data.video_file_settings.button_title.strip()
                                    != button_title.strip()
                                ):
                                    button_user_data.video_file_settings.button_title = button_title
                                menu_page.add_button_title(
                                    button_index=button_index,
                                    button_title=button_title,
                                    button_video_data=button_user_data,
                                )

                                button_index += 1

                                button_list.append((
                                    button_title,
                                    button_user_data,
                                ))

                        menu_list.append((
                            menu_title,
                            tuple(button_list),
                            menu_title_user_data,
                        ))

                        menu_pages.append(menu_page)
                row_data.append(menu_list)

            result, message = Set_Shelved_DVD_Layout(
                project_name=self.project_name,
                dvd_layout_name=self.dvd_layout_name,
                dvd_menu_layout=menu_pages,
            )

            if result == -1:
                popups.PopError(
                    title="DVD Menu Grid Save Error...",
                    message=f"{sys_consts.SDELIM}{message}{sys_consts.SDELIM}",
                ).show()
                return -1
        return 1

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""

        menu_aspect_ratio = sys_consts.AR43

        if self._db_settings.setting_exist(sys_consts.MENU_ASPECT_RATIO_DBK):
            menu_aspect_ratio = self._db_settings.setting_get(
                sys_consts.MENU_ASPECT_RATIO_DBK
            )
        else:
            self._db_settings.setting_set(
                sys_consts.MENU_ASPECT_RATIO_DBK, menu_aspect_ratio
            )

        menu_page_control_container = qtg.VBoxContainer(
            tag="menu_page_controls", align=qtg.Align.TOPLEFT
        )

        file_col_def = (
            qtg.Col_Def(
                label="Menu Title",
                tag="menu_title",
                width=30,
                editable=True,
                checkable=True,
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
            height=20,
            col_def=file_col_def,
            callback=self.event_handler,
        )

        menu_page_control_container.add_row(
            qtg.LineEdit(
                tag="disk_title",
                label="Disk Title",
                width=50,
            ),
            menu_titles,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )

        control_container.add_row(
            menu_page_control_container,
            qtg.HBoxContainer(tag="menu_controls", align=qtg.Align.BOTTOMLEFT).add_row(
                qtg.HBoxContainer(
                    tag="menu_aspect_ratio", text="Menu Aspect Ratio", width=29
                ).add_row(
                    qtg.RadioButton(
                        text="16:9",
                        tag="menu_169",
                        callback=self.event_handler,
                        checked=(
                            True if menu_aspect_ratio == sys_consts.AR169 else False
                        ),
                    ),
                    qtg.RadioButton(
                        text="4:3",
                        tag="menu_43",
                        callback=self.event_handler,
                        checked=True if menu_aspect_ratio == sys_consts.AR43 else False,
                    ),
                ),
                qtg.Spacer(width=2),
                qtg.Switch(
                    tag="deactivate_filters",
                    buddy_control=qtg.Label(
                        tag="switch_label", text="Deactivate Filters", width=17
                    ),
                    tooltip=(
                        "Switch Video Filters Off - Good For Testing Because It"
                        " Increases Speed"
                    ),
                ),
                qtg.Spacer(width=26),
            ),
            qtg.HBoxContainer(tag="menu_move", margin_right=5).add_row(
                qtg.HBoxContainer().add_row(
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-up.svg"),
                        tag="move_menu_up",
                        callback=self.event_handler,
                        tooltip="Move Selected DVD Menu Page Up",
                        width=2,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("arrow-down.svg"),
                        tag="move_menu_down",
                        callback=self.event_handler,
                        tooltip="Move Selected DVD Menu Page Down",
                        width=2,
                    ),
                    qtg.Spacer(width=1),
                    qtg.Button(
                        icon=file_utils.App_Path("x.svg"),
                        tag="delete_menu_page",
                        callback=self.event_handler,
                        tooltip="Remove Selected Menu Page From The DVD Menu",
                        width=2,
                    ),
                    qtg.Button(
                        icon=qtg.Sys_Icon.dialogsave.get(),
                        tag="save_layout",
                        callback=self.event_handler,
                        tooltip="Saves The DVD Menu Layout",
                        width=2,
                    ),
                    qtg.Spacer(width=1),
                    qtg.Button(
                        tag="print_disk",
                        icon=file_utils.App_Path("print.svg"),
                        callback=self.event_handler,
                        tooltip="Prints Disk Label",
                        width=2,
                    ),
                    qtg.Spacer(width=21),
                ),
                qtg.Command_Button_Container(
                    ok_callback=self.event_handler,
                    cancel_callback=self.event_handler,
                    button_width=13,
                ),
            ),
        )

        return control_container
