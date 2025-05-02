"""
Contains classes and functions that are used to store and retrieve configuration data.

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
import shelve
import datetime
from typing import cast

import platformdirs

import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups
import QTPYGUI.sqldb as sqldb
import sys_consts
import QTPYGUI.utils as utils
from QTPYGUI.qtpygui import Action


def Get_Video_Editor_Folder(suppress_error: bool = False) -> str:
    """Gets the video editor folder

    Args:
        suppress_error (bool, optional): If True, suppresses the error popup.

    Returns:
        str: The video editor folder or an empty sting if an error occurs.
    """
    file_handler = file_utils.File()
    db = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    dvd_build_folder = db.setting_get(sys_consts.DVD_BUILD_FOLDER_DBK)

    if dvd_build_folder is None or dvd_build_folder.strip() == "":
        if not suppress_error:
            popups.PopError(
                title="DVD Build Folder Error...",
                message="A DVD Build Folder Must Be Entered Before Making A Video Edit/Transcode Or Join!",
            ).show()

        return ""

    video_editor_folder = file_handler.file_join(
        dvd_build_folder, sys_consts.VIDEO_EDITOR_FOLDER_NAME
    )

    return video_editor_folder


def Get_Transcode_Folder(suppress_error: bool = False) -> str:
    """Gets the video transcode folder

    Args:
        suppress_error (bool, optional): If True, suppresses the error popup.

    Returns:
        str: The video transcode folder or an empty sting if an error occurs.
    """
    file_handler = file_utils.File()
    db = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    dvd_build_folder = db.setting_get(sys_consts.DVD_BUILD_FOLDER_DBK)

    if dvd_build_folder is None or dvd_build_folder.strip() == "":
        if not suppress_error:
            popups.PopError(
                title="DVD Build Folder Error...",
                message="A DVD Build Folder Must Be Entered Before Making A Video Edit/Transcode Or Join!",
            ).show()

        return ""

    video_transcode_folder = file_handler.file_join(
        dvd_build_folder, sys_consts.TRANSCODE_FOLDER_NAME
    )

    return video_transcode_folder


def Migrate_Shelves_To_DB() -> tuple[int, str]:
    """This is a temporary function to migrate existing shelved data to the new SQL-shelved data
    TODO: Removed in later release

    Returns:
        tuple[list[str, tuple[tuple[str, "Video_Data"], ...], dict[str, str]],str]:
            The DVD menu layout and no error message if no issue.
            Empty DVD menu layout and error message if there is an issue

    """
    file_handler = file_utils.File()
    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    if not file_handler.path_writeable(
        platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)
    ):
        return (
            -1,
            f"Path Not Writeable {platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)}",
        )

    backup_path = f"{platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)}{file_handler.ossep}backup"

    if not file_handler.path_exists(backup_path):
        if file_handler.make_dir(backup_path) == -1:
            return -1, f"Failed To Create Backup Path {backup_path}"

    file_list: file_utils.File_Result = file_handler.filelist(
        path=platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
        extensions=sys_consts.SHELVE_FILE_EXTNS,
    )

    project_dict = {}
    dvd_layout_dict = {}
    files_migrated = []

    for item in file_list.files:
        type = item.split(".")[-2]
        extn = item.split(".")[-1]

        if extn not in ("dir", "project_files", "dvdmenu"):
            continue

        if (
            type == "project_files"
            or extn == "project_files"
            or item.endswith("project_files")
        ):
            file = ".".join(item.split(".")[0:-1])
            project = ".".join(item.split(".")[0:1])

            for file_extn in sys_consts.SHELVE_FILE_EXTNS:
                files_migrated.append((
                    file_handler.file_join(
                        dir_path=platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                        file_name=file,
                        ext=file_extn,
                    ),
                    file_handler.file_join(
                        dir_path=platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                        file_name=file,
                        ext=file_extn,
                    ),
                ))

            with shelve.open(
                f"{platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)}{file_handler.ossep}{file}"
            ) as db:
                db_data = db.get("video_grid")
                video_grid_data = []
                if db_data:
                    for row_index, row in enumerate(db_data):
                        for item in row:
                            if item[1]:
                                video_data: Video_Data = item[1]

                                if (
                                    video_data is None
                                ):  # This is an error and should not happen
                                    continue

                                if not file_handler.file_exists(video_data.video_path):
                                    break

                                duration = str(
                                    datetime.timedelta(
                                        seconds=video_data.encoding_info.video_duration
                                    )
                                ).split(".")[0]

                                video_grid_data.append({
                                    "row_index": row_index,
                                    "video_data": video_data,
                                    "duration": duration,
                                })
                db.close()

                if video_grid_data:
                    shelf_dict = sql_shelf.open(shelf_name=sys_consts.VIDEO_GRID_SHELF)
                    if sql_shelf.error.code == -1:
                        return -1, sql_shelf.error.message

                    result, message = sql_shelf.update(
                        shelf_name=sys_consts.VIDEO_GRID_SHELF,
                        shelf_data=shelf_dict
                        | {project.replace("_", " "): video_grid_data},
                    )

                    if result == -1:
                        return -1, message

        elif type == "dvdmenu" or extn == "dvdmenu" or item.endswith("dvdmenu"):
            project_name, layout_name = item.split(".")[0:2]

            project_name = project_name.replace("_", " ")
            layout_name = layout_name.replace("_", " ")

            if project_name not in project_dict:
                project_dict[project_name] = []

            project_dict[project_name].append(layout_name)
            file = ".".join(item.split(".")[0:-1])

            for file_extn in sys_consts.SHELVE_FILE_EXTNS:
                files_migrated.append((
                    file_handler.file_join(
                        dir_path=platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                        file_name=file,
                        ext=file_extn,
                    ),
                    file_handler.file_join(
                        dir_path=platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                        file_name=file,
                        ext=file_extn,
                    ),
                ))

                dvd_layout_key = f"{project_name}.{layout_name}"

                with shelve.open(
                    f"{platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)}{file_handler.ossep}{file}"
                ) as db:
                    db_data = db.get("dvd_menu_grid")
                    dvd_menu_layout = []
                    if db_data:
                        try:
                            for grid_index, grid_row in enumerate(db_data):
                                if (
                                    len(grid_row) == 2
                                ):  # old layouts where I made an implementation error:
                                    menu_page = DVD_Menu_Page()

                                    if grid_index == 0:
                                        menu_page.menu_title = grid_row[0][0]
                                        menu_page.user_data = {
                                            "disk_title": "",
                                            "layout_style": "old",
                                        }

                                    for item_index, item in enumerate(grid_row[1][2]):
                                        new_encoding_details = Encoding_Details()
                                        new_attrs = [
                                            attr
                                            for attr in dir(new_encoding_details)
                                            if attr.startswith("_")
                                            and not attr.startswith("__")
                                        ]  # Want to assign values directly to bypass variable checks

                                        for attr in new_attrs:  # #Encoding Details has changed so have to map values
                                            if hasattr(item[1].encoding_info, attr):
                                                setattr(
                                                    new_encoding_details,
                                                    attr,
                                                    getattr(
                                                        item[1].encoding_info, attr
                                                    ),
                                                )

                                        item[1].encoding_info = new_encoding_details

                                        menu_page.add_button_title(
                                            button_index=item_index,
                                            button_title=item[0],
                                            button_video_data=item[1],
                                        )

                                    dvd_menu_layout.append(menu_page)

                                else:  # New layouts
                                    menu_page = DVD_Menu_Page()
                                    menu_page.menu_title = grid_row[0][0]
                                    menu_page.user_data = grid_row[0][2] | {
                                        "layout_style": "new"
                                    }
                                    for button_index, button_item in enumerate(
                                        grid_row[0][1]
                                    ):
                                        menu_page.add_button_title(
                                            button_index=button_index,
                                            button_title=button_item[0],
                                            button_video_data=button_item[1],
                                        )

                                    dvd_menu_layout.append(menu_page)

                        except Exception as e:
                            print(f"Migrate_Shelves_To_DB Failed : {e=}")

                    db.close()

                    dvd_layout_dict[dvd_layout_key] = dvd_menu_layout

    if project_dict:
        sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
        if sql_shelf.error.code == -1:
            return -1, sql_shelf.error.message

        result, message = sql_shelf.update(
            shelf_name=sys_consts.PROJECTS_SHELF, shelf_data=project_dict
        )

        if result == -1:
            return -1, message

    if dvd_layout_dict:
        shelf_dict = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)

        result, message = sql_shelf.update(
            shelf_name=sys_consts.DVD_MENU_SHELF, shelf_data=dvd_layout_dict
        )

        if result == -1:
            return -1, message

    # TODO remove shelf files when testing finished
    for file_tuple in files_migrated:
        if file_handler.path_exists(file_tuple[0]):
            result, message = file_handler.copy_file(
                source=file_tuple[0], destination_path=backup_path
            )
            if result == -1:
                return -1, message

            file_handler.remove_file(file_tuple[0])

    return 1, ""


def Delete_DVD_Layout(project_name: str, layout_name: str) -> tuple[int, str]:
    """Deletes a DVD Layout

    Args:
        project_name (str): The project name
        layout_name (str): The name of the DVD layout which will be deleted

    Returns:
        tuple[int, str]: tuple containing result code and message

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:

    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )
    assert isinstance(layout_name, str) and layout_name.strip() != "", (
        f"{layout_name=}. Must be a non-empty str"
    )

    dvd_menu_key = f"{project_name}.{layout_name}"

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    if project_name in shelf_dict:
        shelf_dict[project_name] = [
            item for item in shelf_dict[project_name] if item != layout_name
        ]

    result, message = sql_shelf.update(
        shelf_name=sys_consts.PROJECTS_SHELF, shelf_data=shelf_dict
    )

    if result == -1:
        return -1, message

    shelf_dict = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    if dvd_menu_key in shelf_dict:
        shelf_dict.pop(dvd_menu_key)

    result, message = sql_shelf.update(
        shelf_name=sys_consts.DVD_MENU_SHELF, shelf_data=shelf_dict
    )

    if result == -1:
        return -1, message

    return 1, ""


def Delete_Project(project_name: str) -> tuple[int, str]:
    """Deletes a project and associated records

    Args:
        project_name (str): The project name

    Returns:
        tuple[int, str]: tuple containing result code and message

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:

    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )

    # Remove Project Folder
    file_handler = file_utils.File()

    video_editor_folder = Get_Video_Editor_Folder(suppress_error=True)

    if video_editor_folder.strip() and file_handler.path_exists(video_editor_folder):
        project_folder = file_handler.file_join(
            video_editor_folder, utils.Text_To_File_Name(project_name)
        )

        if file_handler.path_exists(project_folder):
            result, message = file_handler.remove_dir_contents(
                file_path=project_folder, keep_parent=False
            )

            if result == -1:
                return -1, message

    # Remove project from DB
    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)

    if (
        sql_shelf.error.code == -1
    ):  # This should not happen unless the system goes off the rails
        return -1, sql_shelf.error.message

    project_shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    dvdmenu_shelf_dict = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    video_grid_shelf_dict = sql_shelf.open(shelf_name=sys_consts.VIDEO_GRID_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    # Perform cleansing pass
    for project_key in video_grid_shelf_dict.copy().keys():
        if project_key not in project_shelf_dict:
            video_grid_shelf_dict.pop(project_key)

    if project_name in video_grid_shelf_dict:
        video_grid_shelf_dict.pop(project_name)

    if project_name in project_shelf_dict:
        dvd_layout_names = project_shelf_dict[project_name]

        for dvd_layout_name in dvd_layout_names:
            dvd_layout_key = f"{project_name}.{dvd_layout_name}"

            if dvd_layout_key in dvdmenu_shelf_dict:
                dvdmenu_shelf_dict.pop(dvd_layout_key)

        project_shelf_dict.pop(project_name)

    result, message = sql_shelf.update(
        shelf_name=sys_consts.VIDEO_GRID_SHELF, shelf_data=video_grid_shelf_dict
    )
    if result == -1:
        return -1, message

    result, message = sql_shelf.update(
        shelf_name=sys_consts.DVD_MENU_SHELF, shelf_data=dvdmenu_shelf_dict
    )
    if result == -1:
        return -1, message

    result, message = sql_shelf.update(
        shelf_name=sys_consts.PROJECTS_SHELF, shelf_data=project_shelf_dict
    )
    if result == -1:
        return -1, message

    return 1, ""


def Remove_Project_Files(project_name: str, file_paths: list[str]) -> tuple[int, str]:
    """Removes project files

    Args:
        project_name (str): The project name
        file_paths (list[str]): List of video file paths

    Returns:
    tuple[int, str]: tuple containing result code and

        - arg 1: If the status code is 1, the operation was successful otherwise it failed.
        - arg 2: If the status code is -1, an error occurred, and the message provides details.:

    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )
    assert isinstance(file_paths, list), f"{file_paths=}. Must be a list"
    assert all(isinstance(item, str) and item.strip() != "" for item in file_paths), (
        f"{file_paths=}. Must be a list of non-empty str"
    )

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if (
        sql_shelf.error.code == -1
    ):  # This should not happen unless the system goes off the rails
        return -1, sql_shelf.error.message

    project_shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    video_grid_shelf_dict = sql_shelf.open(shelf_name=sys_consts.VIDEO_GRID_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    dvdmenu_shelf_dict = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    for file_path in file_paths:
        if project_name in video_grid_shelf_dict:
            for video_data in video_grid_shelf_dict[project_name]:
                if video_data["video_data"] is None:  # Off the rails error
                    continue

                if video_data["video_data"].video_path == file_path:
                    if video_data["row_index"] in video_grid_shelf_dict[project_name]:
                        video_grid_shelf_dict[project_name].pop(video_data["row_index"])

        if project_name in project_shelf_dict:
            for dvd_layout in project_shelf_dict[project_name]:
                dvd_layout_key = f"{project_name}.{dvd_layout}"

                if dvd_layout_key not in dvdmenu_shelf_dict:
                    continue

                for dvd_page in dvdmenu_shelf_dict[dvd_layout_key]:
                    dvd_page: DVD_Menu_Page

                    for button_index, button_item in reversed(
                        dvd_page.get_button_titles.copy().items()
                    ):
                        # button_item[1]: Video_Data
                        if button_item[1].video_path == file_path:
                            dvd_page.get_button_titles.pop(button_index)

    result, message = sql_shelf.update(
        shelf_name=sys_consts.VIDEO_GRID_SHELF, shelf_data=video_grid_shelf_dict
    )
    if result == -1:
        return -1, message

    result, message = sql_shelf.update(
        shelf_name=sys_consts.DVD_MENU_SHELF, shelf_data=dvdmenu_shelf_dict
    )

    if result == -1:
        return -1, message

    return 1, ""


def Get_Project_Files(
    project_name: str,
) -> tuple[int, list[dict]]:
    """
    Retrieves video files associated with a given project, removing duplicates and updating relevant data sources.

    Args:
        project_name (str): The name of the project to retrieve files for.

    Returns:
        tuple[int, list[dict]]:
            - int: Indicates success (1) or failure (-1).
            - list[dict]:
                A list of video data dictionaries, with updated row indices and the following keys:
                    row_index
                    duration
                    video_data
                    dvdmenu [optional]

    """

    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if sql_shelf.error.code == -1:
        return -1, []

    project_shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
    if sql_shelf.error.code == -1:
        return -1, []

    video_grid_shelf_dict = sql_shelf.open(shelf_name=sys_consts.VIDEO_GRID_SHELF)
    if sql_shelf.error.code == -1:
        return -1, []

    dvdmenu_shelf_dict = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)
    if sql_shelf.error.code == -1:
        return -1, []

    dvd_layout_videos = []
    if project_name in project_shelf_dict:
        for dvd_layout in project_shelf_dict[project_name]:
            dvd_layout_key = f"{project_name}.{dvd_layout}"

            if dvd_layout_key in dvdmenu_shelf_dict:
                for dvd_page in dvdmenu_shelf_dict[dvd_layout_key]:
                    dvd_page: DVD_Menu_Page

                    for button_index, button_item in dvd_page.get_button_titles.items():
                        button_video_data: Video_Data = button_item[1]
                        button_video_duration: float = button_item[
                            1
                        ].encoding_info.video_duration

                        dvd_layout_videos.append({
                            "row_index": button_index,
                            "duration": str(
                                datetime.timedelta(seconds=button_video_duration)
                            ).split(".")[0],
                            "video_data": button_video_data,
                            "dvdmenu": dvd_layout,
                        })

    # Perform cleansing pass
    deleted_project_key = False
    for project_key in video_grid_shelf_dict.copy().keys():
        if project_key not in project_shelf_dict:
            deleted_project_key = True
            video_grid_shelf_dict.pop(project_key)

    if deleted_project_key:
        result, _ = sql_shelf.update(
            shelf_name=sys_consts.VIDEO_GRID_SHELF, shelf_data=video_grid_shelf_dict
        )
        if result == -1:
            return -1, []

    if project_name in video_grid_shelf_dict:
        seen_paths = set()
        updated_grid_videos = []

        for video_data in video_grid_shelf_dict[project_name]:
            if video_data["video_data"] is None:  # Off the rails error
                continue

            seen_paths.add(video_data["video_data"].video_path)
            updated_grid_videos.append(video_data)

        for dvd_layout_video in dvd_layout_videos:
            if dvd_layout_video["video_data"] is None:  # Off the rails error
                continue

            video_path = dvd_layout_video["video_data"].video_path
            if video_path not in seen_paths:
                seen_paths.add(video_path)
                updated_grid_videos.append(dvd_layout_video)

        video_grid_shelf_dict[project_name] = updated_grid_videos

        for row_count, video_item in enumerate(video_grid_shelf_dict[project_name]):
            video_item["row_index"] = row_count

        return 1, video_grid_shelf_dict[project_name]
    else:
        return 1, dvd_layout_videos


def Get_Project_Layout_Names(project_name: str) -> tuple[list[str], list[str], int]:
    """Get a list of all project names and a list of the dvd layout names associated with the project name parameter

    Args:
        project_name (str): The project name

    Returns:
        tuple[list[str],list[str],int]:
         - arg 1 - List of all project names
         - arg 2 - List of DVD layouts associated with the project name parameter
         - arg 3 - Error code, 1 if Ok. -1 if an error occurred,


    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if sql_shelf.error.code == -1:
        return [], [], -1

    shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
    if sql_shelf.error.code == -1:
        return [], [], -1

    project_items = []
    layout_items = []

    for key, value in shelf_dict.items():
        if key == project_name:
            layout_items = value

        project_items.append(key)

    project_items.sort()
    layout_items.sort()

    return project_items, layout_items, 1


def Get_Shelved_DVD_Layout(
    project_name: str,
    dvd_layout_name: str,
) -> tuple[list["DVD_Menu_Page"], str]:
    """Gets the DVD menu layout from the shelf database.

    Args:
        dvd_layout_name (str): The name of the shelved project file.

    Returns:
        list[DVD_Menu_Page]: The DVD menu layout and no error message if no issue. Empty DVD menu layout and
            error message if there is an issue
    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )
    assert isinstance(dvd_layout_name, str) and dvd_layout_name.strip() != "", (
        f"{dvd_layout_name=}. Must be a non-empty str"
    )

    key = f"{project_name}.{dvd_layout_name}"

    dvd_menu_layout = []

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if sql_shelf.error.code == -1:
        return dvd_menu_layout, sql_shelf.error.message

    dvd_shelf = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)

    if sql_shelf.error.code == -1:
        return dvd_menu_layout, sql_shelf.error.message

    if dvd_shelf and key in dvd_shelf:
        dvd_menu_layout = dvd_shelf[key]

    if not all(
        isinstance(page, DVD_Menu_Page) for page in dvd_menu_layout
    ):  # Old dict format
        temp_menu_pages: list[DVD_Menu_Page] = []

        for row_index, menu_item in enumerate(dvd_menu_layout):
            menu_page = DVD_Menu_Page()
            menu_page.menu_title = menu_item[0]
            menu_page.user_data = menu_item[2]

            for button_index, button_item in enumerate(menu_item[1]):
                menu_page.add_button_title(
                    button_index=button_index,
                    button_title=button_item[0],
                    button_video_data=button_item[1],
                )

            temp_menu_pages.append(menu_page)

        dvd_menu_layout = temp_menu_pages

        # pprint.pprint(dvd_menu_layout)

    return dvd_menu_layout, ""


def Set_Shelved_Project(
    project_name: str, dvd_menu_layout_names: list[str]
) -> tuple[int, str]:
    """Saves a Project name and associated DVD menu layout names to the shelved project file.

    Args:
        project_name (str): The Project name
        dvd_menu_layout_names: The DVD layout names associated with the project

    Returns:
        tuple[int, Optional[float]]: tuple containing result code and

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:

    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be a non-empty str"
    )
    assert isinstance(dvd_menu_layout_names, list), (
        f"{dvd_menu_layout_names=}. Must be a list of str"
    )
    assert all(isinstance(element, str) for element in dvd_menu_layout_names), (
        f"{dvd_menu_layout_names=}. Must be a list of str"
    )

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)

    if (
        sql_shelf.error.code == -1
    ):  # This should not happen unless the system goes off the rails
        RuntimeError(f"{sql_shelf.error.code} {sql_shelf.error.message}")

    shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)

    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    if project_name not in shelf_dict:
        shelf_dict[project_name] = dvd_menu_layout_names
    else:
        shelf_dict[project_name] = list(
            set(shelf_dict[project_name])
            | set(dvd_menu_layout_names)  # Using sets removes duplicates
        )

    result, message = sql_shelf.update(
        shelf_name=sys_consts.PROJECTS_SHELF, shelf_data=shelf_dict
    )

    return result, message


def Set_Shelved_DVD_Layout(
    project_name: str,
    dvd_layout_name: str,
    dvd_menu_layout: list["DVD_Menu_Page"],
) -> tuple[int, str]:
    """Saves the DVD menu layout to the shelved project file.

    Args:
        project_name (str): The name of the project
        dvd_layout_name (str): The name of the dvd_layout.
        dvd_menu_layout (list[DVD_Menu_Page]): The DVD menu layout to save.

    Returns:
        str: Empty string if successful, or an error message if there is an issue.
    """
    assert isinstance(project_name, str) and project_name.strip() != "", (
        f"{project_name=}. Must be non-empty str"
    )
    assert isinstance(dvd_layout_name, str) and dvd_layout_name.strip() != "", (
        f"{dvd_layout_name=}. Must be a non-empty str"
    )
    assert isinstance(dvd_menu_layout, list), f"{dvd_menu_layout=}. Must be a list"
    assert all(
        isinstance(dvd_menu_page, DVD_Menu_Page) for dvd_menu_page in dvd_menu_layout
    ), "All elements must be DVD_Menu_Page instances"

    sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    shelf_dict = sql_shelf.open(shelf_name=sys_consts.PROJECTS_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    if project_name in shelf_dict:
        if dvd_layout_name not in shelf_dict[project_name]:
            shelf_dict[project_name].append(dvd_layout_name)
    else:  # New Project
        shelf_dict[project_name] = [dvd_layout_name]

    result, message = sql_shelf.update(
        shelf_name=sys_consts.PROJECTS_SHELF, shelf_data=shelf_dict
    )

    if result == -1:
        return -1, message

    shelf_dict = sql_shelf.open(shelf_name=sys_consts.DVD_MENU_SHELF)
    if sql_shelf.error.code == -1:
        return -1, sql_shelf.error.message

    shelf_dict[f"{project_name}.{dvd_layout_name}"] = dvd_menu_layout

    result, message = sql_shelf.update(
        shelf_name=sys_consts.DVD_MENU_SHELF, shelf_data=shelf_dict
    )

    return result, message


@dataclasses.dataclass
class DVD_Archiver_Base:
    def event_handler(self, event: Action) -> None:
        """
        The event_handler method used to handle GUI events.

        Args:
            event (Action): The event that was triggered

        Returns:
            None
        """
        pass


@dataclasses.dataclass(slots=True)
class DVD_Menu_Page:
    """
    Represents a page within a DVD menu.

    Attributes:
        _menu_title (str): The title of the menu page.
        _user_data (dict): A dictionary for storing arbitrary user-defined data associated with the page.
        _button_title (dict[int, tuple[str, Video_Data]]): A dictionary mapping button indices to tuples
            containing the button title and its associated Video_Data.
    """

    _menu_title: str = ""
    _user_data: dict = dataclasses.field(default_factory=dict)
    _button_title: dict[int, tuple[str, "Video_Data"]] = dataclasses.field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Initializes the DVD_Menu_Page object.  This method is automatically called after the dataclass's
        __init__ method.  Currently, it performs no actions.
        """
        pass

        return None

    @property
    def menu_title(self) -> str:
        """
        Gets the title of the menu page.

        Returns:
            str: The menu title.
        """
        return self._menu_title

    @menu_title.setter
    def menu_title(self, menu_title: str) -> None:
        """
        Sets the title of the menu page.

        Args:
            menu_title (str): The menu title to set.

        Raises:
            AssertionError: If the provided menu_title is not a string.
        """
        assert isinstance(menu_title, str), f"{menu_title=}. Must be str"

        self._menu_title = menu_title

    @property
    def get_button_titles(self) -> dict[int, tuple[str, "Video_Data"]]:
        """
        Gets the dictionary of button titles and their associated Video_Data.

        Returns:
            dict[int, tuple[str, Video_Data]]: A dictionary where keys are button indices (integers)
                and values are tuples containing the button title (string) and the associated
                Video_Data object.
        """
        return self._button_title

    @property
    def user_data(self) -> dict:
        """
        Gets the user-defined data associated with the menu page.

        Returns:
            dict: The user-defined data dictionary.
        """
        return self._user_data

    @user_data.setter
    def user_data(self, user_data: dict) -> None:
        """
        Sets the user-defined data associated with the menu page.

        Args:
            user_data (dict): The user-defined data dictionary to set.

        """
        assert isinstance(user_data, dict), f"{user_data=}. Must be dict"

        self._user_data = user_data

    def add_button_title(
        self, button_index: int, button_title: str, button_video_data: "Video_Data"
    ) -> None:
        """
        Adds a button title and its associated Video_Data to the menu page.

        Args:
            button_index (int): The index of the button.
            button_title (str): The title of the button.
            button_video_data (Video_Data): The Video_Data object associated with the button.

        """
        assert isinstance(button_index, int) and button_index >= 0, (
            f"{button_index=}. Must be int >= 0"
        )
        assert isinstance(button_title, str), f"{button_title=}. Must be str"
        assert isinstance(button_video_data, Video_Data), (
            f"{button_video_data=}. Must be Video_Data"
        )

        self._button_title[button_index] = (button_title, button_video_data)

        return None


@dataclasses.dataclass
class DVD_Menu_Settings:
    """Stores/Retrieves the DVD menu settings from the database."""

    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

    @property
    def menu_background_color(self) -> str:
        """
        The menu_background_color method returns the background color of the menu.
        If no setting exists, it will create one with a default value of blue.

        Args:

        Returns:
            str : The background color of the menu

        """
        if not self._db_settings.setting_exist(sys_consts.MENU_BACKGROUND_COLOUR_DBK):
            self._db_settings.setting_set(sys_consts.MENU_BACKGROUND_COLOUR_DBK, "blue")
        return self._db_settings.setting_get(sys_consts.MENU_BACKGROUND_COLOUR_DBK)

    @menu_background_color.setter
    def menu_background_color(self, value: str) -> None:
        """
        The menu_background_color method sets the background color of the menu.

        Args:
            value (str): The value of the menu_background_color setting

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.MENU_BACKGROUND_COLOUR_DBK, value)

    @property
    def menu_font_color(self) -> str:
        """
        The menu_font_color method returns the color of the font used in menus.
        If no value is set, it will return yellow as a default.

        Args:

        Returns:
            str : The color of the font used in menus
        """
        if not self._db_settings.setting_exist(sys_consts.MENU_FONT_COLOUR_DBK):
            self._db_settings.setting_set(sys_consts.MENU_FONT_COLOUR_DBK, "yellow")
        return self._db_settings.setting_get(sys_consts.MENU_FONT_COLOUR_DBK)

    @menu_font_color.setter
    def menu_font_color(self, value: str) -> None:
        """
        The menu_font_color method sets the color of the font in the menu.

        Args:
            value (str): The value of the menu_font_color setting

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.MENU_FONT_COLOUR_DBK, value)

    @property
    def menu_font_point_size(self) -> int:
        """
        The menu_font_point_size method returns the point size of the font used in menus.

        Args:

        Returns:
            The menu font point size

        """
        if not self._db_settings.setting_exist(sys_consts.MENU_FONT_POINT_SIZE_DBK):
            self._db_settings.setting_set(sys_consts.MENU_FONT_POINT_SIZE_DBK, 24)
        return int(self._db_settings.setting_get(sys_consts.MENU_FONT_POINT_SIZE_DBK))

    @menu_font_point_size.setter
    def menu_font_point_size(self, value: int) -> None:
        """
        The menu_font_point_size method sets the font size of the menu text.

        Args:
            value (int): The value of the menu_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(sys_consts.MENU_FONT_POINT_SIZE_DBK, value)

    @property
    def menu_font(self) -> str:
        """
        The menu_font method returns the font used for menu items.
        If no font has been set, it will return the default app font.

        Args:

        Returns:
            str: The font used in the menu

        """
        if not self._db_settings.setting_exist(sys_consts.MENU_FONT_DBK):
            self._db_settings.setting_set(
                sys_consts.MENU_FONT_DBK, sys_consts.DEFAULT_FONT
            )
        return self._db_settings.setting_get(sys_consts.MENU_FONT_DBK)

    @menu_font.setter
    def menu_font(self, value: str) -> None:
        """
        The menu_font method sets the font for the menu.

        Args:
            value (str): The value of the menu_font setting

        Returns:

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.MENU_FONT_DBK, value)

    @property
    def page_pointer_left(self) -> str:
        """
        Returns the left page pointer file

        Args:

        Returns:
            str: The left page pointer file

        """

        if not self._db_settings.setting_exist(sys_consts.PAGE_POINTER_LEFT_DBK):
            file_handler = file_utils.File()
            if file_handler.file_exists(
                directory_path=sys_consts.ICON_PATH,
                file_name="pointer.black.left",
                file_extension="png",
            ):
                self._db_settings.setting_set(
                    sys_consts.PAGE_POINTER_LEFT_DBK, "pointer.black.left.png"
                )

        return self._db_settings.setting_get(sys_consts.PAGE_POINTER_LEFT_DBK)

    @page_pointer_left.setter
    def page_pointer_left(self, value: str) -> None:
        """
        Sets the left page pointer.

        Args:
            value (str): The left page pointer file

        Returns:

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.PAGE_POINTER_LEFT_DBK, value)

    @property
    def page_pointer_right(self) -> str:
        """
        Returns the right page pointer file

        Args:

        Returns:
            str: The right page pointer file

        """

        if not self._db_settings.setting_exist(sys_consts.PAGE_POINTER_RIGHT_DBK):
            file_handler = file_utils.File()

            if file_handler.file_exists(
                directory_path=sys_consts.ICON_PATH,
                file_name="pointer.black.right",
                file_extension="png",
            ):
                self._db_settings.setting_set(
                    sys_consts.PAGE_POINTER_RIGHT_DBK, "pointer.black.right.png"
                )

        return self._db_settings.setting_get(sys_consts.PAGE_POINTER_RIGHT_DBK)

    @page_pointer_right.setter
    def page_pointer_right(self, value: str) -> None:
        """
        Sets the right page pointer file.

        Args:
            value (str): The right page pointer file

        Returns:

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.PAGE_POINTER_RIGHT_DBK, value)

    @property
    def button_background_color(self) -> str:
        """
        The button_background_color method returns the background color of the buttons in the GUI.
        If no setting exists, it creates one and sets it to darkgray.

        Args:

        Returns:
            str: The background color of the buttons

        """
        if not self._db_settings.setting_exist(sys_consts.BUTTON_BACKGROUND_COLOUR_DBK):
            self._db_settings.setting_set(
                sys_consts.BUTTON_BACKGROUND_COLOUR_DBK, "darkgray"
            )
        return self._db_settings.setting_get(sys_consts.BUTTON_BACKGROUND_COLOUR_DBK)

    @button_background_color.setter
    def button_background_color(self, value: str) -> None:
        """
        The button_background_color method sets the background color of the buttons in the GUI.

        Args:
            value (str): Set the button background color

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.BUTTON_BACKGROUND_COLOUR_DBK, value)

    @property
    def button_background_transparency(self) -> int:
        """
        The button_background_transparency method returns the transparency of the button background.
            If it does not exist, it is set to 90.

        Args:

        Returns:
            int : Percentage transparency of the button background

        """
        if not self._db_settings.setting_exist(
            sys_consts.BUTTON_BACKGROUND_TRANSPARENCY_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.BUTTON_BACKGROUND_TRANSPARENCY_DBK, 90
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.BUTTON_BACKGROUND_TRANSPARENCY_DBK
            ),
        )

    @button_background_transparency.setter
    def button_background_transparency(self, value: int) -> None:
        """
        The button_background_transparency method sets the transparency of the button background.

        Args:
            value (int): The percentage transparency of the button background

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.BUTTON_BACKGROUND_TRANSPARENCY_DBK, value
        )

    @property
    def button_font(self) -> str:
        """
        The button_font method is used to set the font of the buttons in the menu.
        The function first checks if a setting for button_font exists, and if it does not,
        then it sets one with the app default font. Then, it returns that value.

        Returns:
            str : The font used for button text

        """
        if not self._db_settings.setting_exist(sys_consts.BUTTON_FONT_DBK):
            self._db_settings.setting_set(
                sys_consts.BUTTON_FONT_DBK, sys_consts.DEFAULT_FONT
            )
        return self._db_settings.setting_get(sys_consts.BUTTON_FONT_DBK)

    @button_font.setter
    def button_font(self, value: str) -> None:
        """
        The button_font method sets the font for all buttons in the application.

        Args:
            value (str): Sets the button_font

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.BUTTON_FONT_DBK, value)

    @property
    def button_font_color(self) -> str:
        """
        The button_font_color method returns the color of the font on buttons.
        If no button_font_color setting exists, it creates one with a default value of white.

        Returns:
            str : The value of the button_font_color setting

        """
        if not self._db_settings.setting_exist(sys_consts.BUTTON_FONT_COLOUR_DBK):
            self._db_settings.setting_set(sys_consts.BUTTON_FONT_COLOUR_DBK, "white")
        return self._db_settings.setting_get(sys_consts.BUTTON_FONT_COLOUR_DBK)

    @button_font_color.setter
    def button_font_color(self, value: str) -> None:
        """
        The button_font_color method sets the font color of the buttons in the DVD menu.

        Args:
            value (str): Set the button_font_color setting

        """
        self._db_settings.setting_set(sys_consts.BUTTON_FONT_COLOUR_DBK, value)

    @property
    def button_font_point_size(self) -> int:
        """
        The button_font_point_size method returns the point size of the font used for buttons.
        If no value is stored in the database, it will be set to 12 and returned.

        Args:

        Returns:
            int : The point size of the font used for buttons

        """
        if not self._db_settings.setting_exist(sys_consts.BUTTON_FONT_POINT_SIZE_DBK):
            self._db_settings.setting_set(sys_consts.BUTTON_FONT_POINT_SIZE_DBK, 12)
        return cast(
            int, self._db_settings.setting_get(sys_consts.BUTTON_FONT_POINT_SIZE_DBK)
        )

    @button_font_point_size.setter
    def button_font_point_size(self, value: int) -> None:
        """
        The button_font_point_size method sets the font size of the buttons in the DVD Menu.

        Args:
            value (int): Sets the button_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(sys_consts.BUTTON_FONT_POINT_SIZE_DBK, value)

    @property
    def buttons_across(self) -> int:
        """
        The buttons_across method returns the number of buttons across the DVD menu.

        Args:

        Returns:
            int : The number of buttons across the screen

        """
        if not self._db_settings.setting_exist(sys_consts.BUTTONS_ACROSS_DBK):
            self._db_settings.setting_set(sys_consts.BUTTONS_ACROSS_DBK, 2)
        return cast(int, self._db_settings.setting_get(sys_consts.BUTTONS_ACROSS_DBK))

    @buttons_across.setter
    def buttons_across(self, value: int) -> None:
        """
        The buttons_across method sets the number of buttons across the DVD menu.

        Args:
            value (int): Set the value of buttons_across to an integer
        """
        assert isinstance(value, int) and 1 <= value <= 4, f"{value=}. Must be int"

        self._db_settings.setting_set(sys_consts.BUTTONS_ACROSS_DBK, value)

    @property
    def buttons_per_page(self) -> int:
        """
        The buttons_per_page method returns the number of buttons per DVD Menu page.
        If the setting does not exist, it is created and set to 4.

        Args:

        Returns:
            int : The number of buttons per page
        """
        if not self._db_settings.setting_exist(sys_consts.BUTTONS_PER_PAGE_DBK):
            self._db_settings.setting_set(sys_consts.BUTTONS_PER_PAGE_DBK, 4)
        return cast(int, self._db_settings.setting_get(sys_consts.BUTTONS_PER_PAGE_DBK))

    @buttons_per_page.setter
    def buttons_per_page(self, value: int) -> None:
        """
        The buttons_per_page method sets the number of buttons per DVD Menu page.
        The value must be an integer between 1 and 6, inclusive.

        Args:
            value (int) Set the number of buttons per page
        """
        assert isinstance(value, int) and 1 <= value <= 6, f"{value=}. Must be int"

        self._db_settings.setting_set(sys_consts.BUTTONS_PER_PAGE_DBK, value)


@dataclasses.dataclass(slots=True)
class DVD_Print_Settings:
    """Stores/Retrieves the DVD print settings from the database."""

    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

    @property
    def insert_title_background_color(self) -> str:
        """
        The insert_title_background_color method returns the background color of the DVD case insert title.
        If no setting exists, it creates one and sets it to white.

        Args:

        Returns:
            str: The background color of the buttons

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_TITLE_BACKGROUND_COLOUR_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_TITLE_BACKGROUND_COLOUR_DBK, "white"
            )
        return self._db_settings.setting_get(
            sys_consts.DVD_INSERT_TITLE_BACKGROUND_COLOUR_DBK
        )

    @insert_title_background_color.setter
    def insert_title_background_color(self, value: str) -> None:
        """
        The insert_title_background_color method sets the background color of the DVD case insert title.

        Args:
            value (str): Set the insert background title color

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(
            sys_consts.DVD_INSERT_TITLE_BACKGROUND_COLOUR_DBK, value
        )

    @property
    def insert_title_background_transparency(self) -> int:
        """
        The insert_title_background_transparency method returns the transparency of the DVD case insert title background.
            If it does not exist, it is set to 0.

        Args:

        Returns:
            int : Percentage transparency of the DVD case insert title background

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_TITLE_BACKGROUND_TRANSPARENCY_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_TITLE_BACKGROUND_TRANSPARENCY_DBK, 100
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.DVD_INSERT_TITLE_BACKGROUND_TRANSPARENCY_DBK
            ),
        )

    @insert_title_background_transparency.setter
    def insert_title_background_transparency(self, value: int) -> None:
        """
        The insert_title_background_transparency method sets the transparency of the insert title background.

        Args:
            value (int): The percentage transparency of the insert title background

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.DVD_INSERT_TITLE_BACKGROUND_TRANSPARENCY_DBK, value
        )

    @property
    def insert_title_font(self) -> str:
        """
        The insert_title_font method is used to set the font of the DVD case insert title.
        The function first checks if a setting for insert_title_font exists, and if it does not,
        then it sets one with the app default font. Then, it returns that value.

        Returns:
            str : The font used for DVD case insert title text

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_INSERT_TITLE_FONT_DBK):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_TITLE_FONT_DBK, sys_consts.DEFAULT_FONT
            )
        return self._db_settings.setting_get(sys_consts.DVD_INSERT_TITLE_FONT_DBK)

    @insert_title_font.setter
    def insert_title_font(self, value: str) -> None:
        """
        The insert_title_font method sets the font for the text in the DVD case insert title.

        Args:
            value (str): Sets the insert_title_font

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.DVD_INSERT_TITLE_FONT_DBK, value)

    @property
    def insert_title_font_color(self) -> str:
        """
        The insert_title_font_color method returns the color of the DVD case insert title font.
        If no insert_title_font_color setting exists, it creates one with a default value of black.

        Returns:
            str : The value of the insert_title_font_color setting

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_TITLE_FONT_COLOUR_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_TITLE_FONT_COLOUR_DBK, "black"
            )
        return self._db_settings.setting_get(
            sys_consts.DVD_INSERT_TITLE_FONT_COLOUR_DBK
        )

    @insert_title_font_color.setter
    def insert_title_font_color(self, value: str) -> None:
        """
        The insert_title_font_color method sets the font color of the DVD case insert title text.

        Args:
            value (str): Set the insert_title_font_color setting

        """
        self._db_settings.setting_set(
            sys_consts.DVD_INSERT_TITLE_FONT_COLOUR_DBK, value
        )

    @property
    def insert_title_font_point_size(self) -> int:
        """
        The insert_title_font_point_size method returns the point size of the font used in the DVD case insert title text.
        If no value is stored in the database, it will be set to 24 and returned.

        Args:

        Returns:
            int : The point size of the font used for DVD case insert title text

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_TITLE_FONT_POINT_SIZE_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_TITLE_FONT_POINT_SIZE_DBK, 24
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.DVD_INSERT_TITLE_FONT_POINT_SIZE_DBK
            ),
        )

    @insert_title_font_point_size.setter
    def insert_title_font_point_size(self, value: int) -> None:
        """
        The insert_title_font_point_size method sets the font size of the text on the DVD case insert title text.

        Args:
            value (int): Sets the insert_title_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.DVD_INSERT_TITLE_FONT_POINT_SIZE_DBK, value
        )

    @property
    def insert_background_color(self) -> str:
        """
        The insert_background_color method returns the background color of the DVD case insert.
        If no setting exists, it creates one and sets it to white.

        Args:

        Returns:
            str: The background color of the DVD case insert text

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_BACKGROUND_COLOUR_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_BACKGROUND_COLOUR_DBK, "white"
            )
        return self._db_settings.setting_get(
            sys_consts.DVD_INSERT_BACKGROUND_COLOUR_DBK
        )

    @insert_background_color.setter
    def insert_background_color(self, value: str) -> None:
        """
        The insert_background_color method sets the background color of the DVD case insert.

        Args:
            value (str): Set the insert background color

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(
            sys_consts.DVD_INSERT_BACKGROUND_COLOUR_DBK, value
        )

    @property
    def insert_background_transparency(self) -> int:
        """
        The insert_background_transparency method returns the transparency of the DVD case insert background.
            If it does not exist, it is set to 0.

        Args:

        Returns:
            int : Percentage transparency of the DVD case insert background

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_BACKGROUND_TRANSPARENCY_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_BACKGROUND_TRANSPARENCY_DBK, 100
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.DVD_INSERT_BACKGROUND_TRANSPARENCY_DBK
            ),
        )

    @insert_background_transparency.setter
    def insert_background_transparency(self, value: int) -> None:
        """
        The button_background_transparency method sets the transparency of the DVD case insert text background.

        Args:
            value (int): The percentage transparency of the DVD case insert text background

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.DVD_INSERT_BACKGROUND_TRANSPARENCY_DBK, value
        )

    @property
    def insert_font(self) -> str:
        """
        The insert_font method is used to set the font of the DVD case insert.
        The function first checks if a setting for insert_font exists, and if it does not,
        then it sets one with the app default font. Then, it returns that value.

        Returns:
            str : The font used for DVD case insert text

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_INSERT_FONT_DBK):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_FONT_DBK, sys_consts.DEFAULT_FONT
            )
        return self._db_settings.setting_get(sys_consts.DVD_INSERT_FONT_DBK)

    @insert_font.setter
    def insert_font(self, value: str) -> None:
        """
        The insert_font method sets the font for all the text in the DVD case insert.

        Args:
            value (str): Sets the insert_font of the DVD case insert

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.DVD_INSERT_FONT_DBK, value)

    @property
    def insert_font_color(self) -> str:
        """
        The insert_font_color method returns the color of the DVD case insert font.
        If no insert_font_color setting exists, it creates one with a default value of black.

        Returns:
            str : The value of the insert_font_color setting

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_INSERT_FONT_COLOUR_DBK):
            self._db_settings.setting_set(
                sys_consts.DVD_INSERT_FONT_COLOUR_DBK, "black"
            )
        return self._db_settings.setting_get(sys_consts.DVD_INSERT_FONT_COLOUR_DBK)

    @insert_font_color.setter
    def insert_font_color(self, value: str) -> None:
        """
        The insert_font_color method sets the font color of the text on the DVD case insert.

        Args:
            value (str): Set the insert_font_color setting

        """
        self._db_settings.setting_set(sys_consts.DVD_INSERT_FONT_COLOUR_DBK, value)

    @property
    def insert_font_point_size(self) -> int:
        """
        The insert_font_point_size method returns the point size of the font used in the DVD case insert.
        If no value is stored in the database, it will be set to 12 and returned.

        Args:

        Returns:
            int : The point size of the font used for DVD case insert text

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_INSERT_FONT_POINT_SIZE_DBK
        ):
            self._db_settings.setting_set(sys_consts.DVD_INSERT_FONT_POINT_SIZE_DBK, 12)
        return cast(
            int,
            self._db_settings.setting_get(sys_consts.DVD_INSERT_FONT_POINT_SIZE_DBK),
        )

    @insert_font_point_size.setter
    def insert_font_point_size(self, value: int) -> None:
        """
        The insert_font_point_size method sets the font size of the text on the DVD case insert.

        Args:
            value (int): Sets the insert_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(sys_consts.DVD_INSERT_FONT_POINT_SIZE_DBK, value)

    @property
    def disk_title_background_color(self) -> str:
        """
        The disk_title_background_color method returns the background color of the DVD disk title.
        If no setting exists, it creates one and sets it to white.

        Args:

        Returns:
            str: The background color of the DVD disk title

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_DISK_TITLE_BACKGROUND_COLOUR_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_TITLE_BACKGROUND_COLOUR_DBK, "white"
            )
        return self._db_settings.setting_get(
            sys_consts.DVD_DISK_TITLE_BACKGROUND_COLOUR_DBK
        )

    @disk_title_background_color.setter
    def disk_title_background_color(self, value: str) -> None:
        """
        The disk_background_color method sets the background color of the DVD disk title.

        Args:
            value (str): Set the disk background color

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(
            sys_consts.DVD_DISK_TITLE_BACKGROUND_COLOUR_DBK, value
        )

    @property
    def disk_title_background_transparency(self) -> int:
        """
        The disk_title_background_transparency method returns the transparency of the DVD disk title background.
            If it does not exist, it is set to 0.

        Args:

        Returns:
            int : Percentage transparency of the DVD disk title background

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_DISK_TITLE_BACKGROUND_TRANSPARENCY_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_TITLE_BACKGROUND_TRANSPARENCY_DBK, 0
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.DVD_DISK_TITLE_BACKGROUND_TRANSPARENCY_DBK
            ),
        )

    @disk_title_background_transparency.setter
    def disk_title_background_transparency(self, value: int) -> None:
        """
        The disk_title_background_transparency method sets the transparency of the DVD disk title background.

        Args:
            value (int): The percentage transparency of the DVD disk title background

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.DVD_DISK_TITLE_BACKGROUND_TRANSPARENCY_DBK, value
        )

    @property
    def disk_title_font(self) -> str:
        """
        The disk_title_font method is used to set the font of the DVD disk title.
        The function first checks if a setting for dvd_titel_font exists, and if it does not,
        then it sets one with the app default font. Then, it returns that value.

        Returns:
            str : The font used for DVD disk title text

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_DISK_TITLE_FONT_DBK):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_TITLE_FONT_DBK, sys_consts.DEFAULT_FONT
            )
        return self._db_settings.setting_get(sys_consts.DVD_DISK_TITLE_FONT_DBK)

    @disk_title_font.setter
    def disk_title_font(self, value: str) -> None:
        """
        The disk_title_font method sets the font for all the DVD disk title text.

        Args:
            value (str): Sets the disk_title_font

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.DVD_DISK_TITLE_FONT_DBK, value)

    @property
    def disk_title_font_color(self) -> str:
        """
        The disk_title_font_color method returns the color of the DVD disk title font.
        If no disk_title_font_color setting exists, it creates one with a default value of black.

        Returns:
            str : The value of the disk_title_font_color setting

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_DISK_TITLE_FONT_COLOUR_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_TITLE_FONT_COLOUR_DBK, "black"
            )
        return self._db_settings.setting_get(sys_consts.DVD_DISK_TITLE_FONT_COLOUR_DBK)

    @disk_title_font_color.setter
    def disk_title_font_color(self, value: str) -> None:
        """
        The disk_title_font_color method sets the font color of the DVD disk title text.

        Args:
            value (str): Set the disk_title_font_color setting

        """
        self._db_settings.setting_set(sys_consts.DVD_DISK_TITLE_FONT_COLOUR_DBK, value)

    @property
    def disk_title_font_point_size(self) -> int:
        """
        The disk_title_font_point_size method returns the point size of the font used on the DVD disk title text.
        If no value is stored in the database, it will be set to 24 and returned.

        Args:

        Returns:
            int : The point size of the font used on the DVD disk title text

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_DISK_TITLE_FONT_POINT_SIZE_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_TITLE_FONT_POINT_SIZE_DBK, 24
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.DVD_DISK_TITLE_FONT_POINT_SIZE_DBK
            ),
        )

    @disk_title_font_point_size.setter
    def disk_title_font_point_size(self, value: int) -> None:
        """
        The disk_title_font_point_size method sets the font size of the text on the DVD disk title.

        Args:
            value (int): Sets the disk_title_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.DVD_DISK_TITLE_FONT_POINT_SIZE_DBK, value
        )

    @property
    def disk_background_color(self) -> str:
        """
        The disk_background_color method returns the background color of the DVD disk.
        If no setting exists, it creates one and sets it to white.

        Args:

        Returns:
            str: The background color of the DVD disk

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_DISK_BACKGROUND_COLOUR_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_BACKGROUND_COLOUR_DBK, "white"
            )
        return self._db_settings.setting_get(sys_consts.DVD_DISK_BACKGROUND_COLOUR_DBK)

    @disk_background_color.setter
    def disk_background_color(self, value: str) -> None:
        """
        The disk_background_color method sets the background color of the DVD disk.

        Args:
            value (str): Set the disk background color

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.DVD_DISK_BACKGROUND_COLOUR_DBK, value)

    @property
    def disk_background_transparency(self) -> int:
        """
        The disk_background_transparency method returns the transparency of the DVD disk background.
            If it does not exist, it is set to 0.

        Args:

        Returns:
            int : Percentage transparency of the DVD disk background

        """
        if not self._db_settings.setting_exist(
            sys_consts.DVD_DISK_BACKGROUND_TRANSPARENCY_DBK
        ):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_BACKGROUND_TRANSPARENCY_DBK, 0
            )
        return cast(
            int,
            self._db_settings.setting_get(
                sys_consts.DVD_DISK_BACKGROUND_TRANSPARENCY_DBK
            ),
        )

    @disk_background_transparency.setter
    def disk_background_transparency(self, value: int) -> None:
        """
        The disk_background_transparency method sets the transparency of the DVD disk background.

        Args:
            value (int): The percentage transparency of the DVD disk background

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(
            sys_consts.DVD_DISK_BACKGROUND_TRANSPARENCY_DBK, value
        )

    @property
    def disk_font(self) -> str:
        """
        The disk_font method is used to set the font of the DVD disk insert.
        The function first checks if a setting for dvd_font exists, and if it does not,
        then it sets one with the app default font. Then, it returns that value.

        Returns:
            str : The font used for DVD disk insert text

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_DISK_FONT_DBK):
            self._db_settings.setting_set(
                sys_consts.DVD_DISK_FONT_DBK, sys_consts.DEFAULT_FONT
            )
        return self._db_settings.setting_get(sys_consts.DVD_DISK_FONT_DBK)

    @disk_font.setter
    def disk_font(self, value: str) -> None:
        """
        The disk_font method sets the font for all the text on the DVD disk.

        Args:
            value (str): Sets the disk_font

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._db_settings.setting_set(sys_consts.DVD_DISK_FONT_DBK, value)

    @property
    def disk_font_color(self) -> str:
        """
        The disk_font_color method returns the color of the DVD disk font.
        If no disk_font_color setting exists, it creates one with a default value of black.

        Returns:
            str : The value of the disk_font_color setting

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_DISK_FONT_COLOUR_DBK):
            self._db_settings.setting_set(sys_consts.DVD_DISK_FONT_COLOUR_DBK, "black")
        return self._db_settings.setting_get(sys_consts.DVD_DISK_FONT_COLOUR_DBK)

    @disk_font_color.setter
    def disk_font_color(self, value: str) -> None:
        """
        The disk_font_color method sets the font color of the text on the DVD disk.

        Args:
            value (str): Set the disk_font_color setting

        """
        self._db_settings.setting_set(sys_consts.DVD_DISK_FONT_COLOUR_DBK, value)

    @property
    def disk_font_point_size(self) -> int:
        """
        The disk_font_point_size method returns the point size of the font used on the DVD disk.
        If no value is stored in the database, it will be set to 12 and returned.

        Args:

        Returns:
            int : The point size of the font used on the DVD disk

        """
        if not self._db_settings.setting_exist(sys_consts.DVD_DISK_FONT_POINT_SIZE_DBK):
            self._db_settings.setting_set(sys_consts.DVD_DISK_FONT_POINT_SIZE_DBK, 12)
        return cast(
            int,
            self._db_settings.setting_get(sys_consts.DVD_DISK_FONT_POINT_SIZE_DBK),
        )

    @disk_font_point_size.setter
    def disk_font_point_size(self, value: int) -> None:
        """
        The disk_font_point_size method sets the font size of the text on the DVD disk.

        Args:
            value (int): Sets the disk_font_point_size setting

        """
        assert isinstance(value, int) and 0 <= value <= 100, f"{value=}. Must be int"

        self._db_settings.setting_set(sys_consts.DVD_DISK_FONT_POINT_SIZE_DBK, value)


@dataclasses.dataclass(slots=True)
class Encoding_Details:
    """
    The Encoding_Details class is used to store the details of a video. as well as the error message associated
    with the video.
    """

    _error: str = ""
    _audio_tracks: int = 0
    _video_tracks: int = 0
    _audio_format: str = ""
    _audio_channels: int = 0
    _audio_bitrate: int = 0
    _audio_codec: str = ""
    _audio_sample_rate: int = 0
    _video_codec: str = ""
    _video_pix_fmt: str = ""
    _video_profile: str = ""
    _video_level: str = ""
    _video_format: str = ""
    _video_width: int = 0
    _video_height: int = 0
    _video_ar: str = ""
    _video_par: float = 0.0
    _video_dar: float = 0.0
    _video_duration: float = 0.0
    _video_scan_order: str = ""
    _video_scan_type: str = ""
    _video_frame_rate: float = 0.0
    _video_standard: str = ""
    _video_frame_count: int = 0
    _video_bitrate: int = 0

    def __post_init__(self) -> None:
        pass

    @property
    def error(self) -> str:
        """
        The error method returns the error message associated with a video.

        Returns:
            str: The error message from the video

        """
        return self._error

    @error.setter
    def error(self, value: str) -> None:
        """
        The error method sets the error message associated with a video.

        Args:
            value (str): Set the error message for the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._error = value

    @property
    def audio_tracks(self) -> int:
        """
        The audio_tracks method returns the number of audio tracks in a video.

        Returns:
            int: The number of audio tracks in the video

        """
        return self._audio_tracks

    @audio_tracks.setter
    def audio_tracks(self, value: int) -> None:
        """
        The audio_tracks method sets the number of audio tracks in a video.

        Args:
            value (int): Set the number of audio tracks in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._audio_tracks = value

    @property
    def audio_codec(self) -> str:
        """
        The audio_codec method returns the audio codec of a video.

        Returns:
            str: The audio codec of the video

        """
        return self._audio_codec

    @audio_codec.setter
    def audio_codec(self, value: str) -> None:
        """
        The audio_codec method sets the audio codec of a video.

        Args:
            value (str): Set the audio codec of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._audio_codec = value

    @property
    def audio_format(self) -> str:
        """
        The audio_format method returns the audio format of a video.

        Returns:
            str: The audio format of the video

        """
        return self._audio_format

    @audio_format.setter
    def audio_format(self, value: str) -> None:
        """
        The audio_format method sets the audio format of a video.

        Args:
            value (str): Set the audio format of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._audio_format = value

    @property
    def audio_channels(self) -> int:
        """
        The audio_channels method returns the number of audio channels in a video.

        Returns:
            int: The number of audio channels in the video

        """
        return self._audio_channels

    @audio_channels.setter
    def audio_channels(self, value: int) -> None:
        """
        The audio_channels method sets the number of audio channels in a video.

        Args:
            value (int): Set the number of audio channels in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._audio_channels = value

    @property
    def audio_bitrate(self) -> int:
        """
        The audio_bitrate method returns the audio bitrate of a video.

        Returns:
            int: The audio bitrate of the video

        """
        return self._audio_bitrate

    @audio_bitrate.setter
    def audio_bitrate(self, value: int) -> None:
        """
        The audio_bitrate method sets the audio bitrate of a video.

        Args:
            value (int): Set the audio bitrate of the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._audio_bitrate = value

    @property
    def audio_sample_rate(self) -> int:
        """
        The audio_sample_rate method returns the audio sample rate of a video.

        Returns:
            int: The audio sample rate of the video

        """
        return self._audio_sample_rate

    @audio_sample_rate.setter
    def audio_sample_rate(self, value: int) -> None:
        """
        The audio_sample_rate method sets the audio sample rate of a video.

        Args:
            value (int): Set the audio sample rate of the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._audio_sample_rate = value

    @property
    def video_tracks(self) -> int:
        """
        The video_tracks method returns the number of video tracks in a video.

        Returns:
            int: The number of video tracks in the video

        """
        return self._video_tracks

    @video_tracks.setter
    def video_tracks(self, value: int) -> None:
        """
        The video_tracks method sets the number of video tracks in a video.

        Args:
            value (int): Set the number of video tracks in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_tracks = value

    @property
    def video_codec(self) -> str:
        """
        The video_codec method returns the video codec of a video.

        Returns:
            str: The video codec of the video

        """
        return self._video_codec

    @video_codec.setter
    def video_codec(self, value: str) -> None:
        """
        The video_codec method sets the video codec of a video.

        Args:
            value (str): Set the video codec of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_codec = value

    @property
    def video_pix_fmt(self) -> str:
        """
        The video_pix_fmt method returns the pixel format of a video.

        Returns:
            str: The pixel format of the video

        """
        return self._video_pix_fmt

    @video_pix_fmt.setter
    def video_pix_fmt(self, value: str) -> None:
        """
        The video_pix_fmt method sets the pixel format of a video.

        Args:
            value (str): Set the pixel format of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_pix_fmt = value

    @property
    def video_profile(self) -> str:
        """
        The video_profile method returns the profile of a video.

        Returns:
            str: The profile of the video

        """
        return self._video_profile

    @video_profile.setter
    def video_profile(self, value: str) -> None:
        """
        The video_profile method sets the profile of a video.

        Args:
            value (str): Set the profile of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_profile = value

    @property
    def video_level(self) -> str:
        """
        The video_level method returns the level of a video.

        Returns:
            str: The level of the video

        """
        return self._video_level

    @video_level.setter
    def video_level(self, value: str) -> None:
        """
        The video_level method sets the level of a video.

        Args:
            value (str): Set the level of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_level = value

    @property
    def video_format(self) -> str:
        """
        The video_format method returns the video format of a video.

        Returns:
            str: The video format of the video

        """
        return self._video_format

    @video_format.setter
    def video_format(self, value: str) -> None:
        """
        The video_format method sets the video format of a video.

        Args:
            value (str): Set the video format of the video

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._video_format = value

    @property
    def video_width(self) -> int:
        """
        The video_width method returns the width of a video.

        Returns:
            int: The width of the video

        """
        return self._video_width

    @video_width.setter
    def video_width(self, value: int) -> None:
        """
        The video_width method sets the width of a video.

        Args:
            value (int): Set the width of the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_width = value

    @property
    def video_height(self) -> int:
        """
        The video_height method returns the height of a video.

        Returns:
            int: The height of the video

        """
        return self._video_height

    @video_height.setter
    def video_height(self, value: int) -> None:
        """
        The video_height method sets the height of a video.

        Args:
            value (int): Set the height of the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_height = value

    @property
    def video_ar(self) -> str:
        """
        The video_ar method returns the aspect ratio of a video.

        Returns:
            str: The aspect ratio of the video

        """
        return self._video_ar

    @video_ar.setter
    def video_ar(self, value: str) -> None:
        """
        The video_ar method sets the aspect ratio of a video.

        Args:
            value (str): Set the aspect ratio of the video

        """
        assert isinstance(value, str) and value in (
            sys_consts.AR43,
            sys_consts.AR169,
        ), f"{value=}. Must be either {sys_consts.AR43} or  {sys_consts.AR169}"

        self._video_ar = value

    @property
    def video_bitrate(self) -> int:
        """
        The video_bitrate method returns the bitrate of the video.

        Returns:
            int: Video bitrate

        """
        return self._video_bitrate

    @video_bitrate.setter
    def video_bitrate(self, value: int) -> None:
        """
        The video_bitrate method sets the bitrate of the video.

        Args:
            value (int): Set the number of frames in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_bitrate = value

    @property
    def video_par(self) -> float:
        """
        The video_par method returns the pixel aspect ratio of a video.

        Returns:
            float: The pixel aspect ratio of the video

        """
        return self._video_par

    @video_par.setter
    def video_par(self, value: float):
        """
        The video_par method sets the pixel aspect ratio of a video.

        Args:
            value (float): Set the pixel aspect ratio of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_par = value

    @property
    def video_dar(self) -> float:
        """
        The video_dar method returns the display aspect ratio of a video.

        Returns:
            float: The display aspect ratio of the video

        """
        return self._video_dar

    @video_dar.setter
    def video_dar(self, value: float) -> None:
        """
        The video_dar method sets the display aspect ratio of a video.

        Args:
            value (float): Set the display aspect ratio of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_dar = value

    @property
    def video_duration(self) -> float:
        """
        The video_duration method returns the duration of a video.

        Returns:
            float: The duration of the video

        """
        return self._video_duration

    @video_duration.setter
    def video_duration(self, value: float) -> None:
        """
        The video_duration method sets the duration of a video.

        Args:
            value (float): Set the duration of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_duration = value

    @property
    def video_frame_rate(self) -> float:
        """
        The video_frame_rate method returns the frame rate of a video.

        Returns:
            float: The frame rate of the video

        """
        return self._video_frame_rate

    @video_frame_rate.setter
    def video_frame_rate(self, value: float) -> None:
        """
        The video_frame_rate method sets the frame rate of a video.

        Args:
            value (float): Set the frame rate of the video

        """
        assert isinstance(value, float), f"{value=}. Must be float"

        self._video_frame_rate = value

    @property
    def video_standard(self) -> str:
        """
        The video_standard method returns the video standard of a video PAL/NTSC.

        Returns:
            str: The video standard of the video

        """
        if self._video_standard not in (sys_consts.PAL, sys_consts.NTSC):
            if (
                self.video_width == sys_consts.PAL_SPECS.width_43
                and self.video_height == sys_consts.PAL_SPECS.height_43
                and self.video_frame_rate == sys_consts.PAL_SPECS.frame_rate
            ):
                self._video_standard = sys_consts.PAL
            elif (
                self.video_width == sys_consts.NTSC_SPECS.width_43
                and self.video_height == sys_consts.NTSC_SPECS.height_43
                and self.video_frame_rate == sys_consts.NTSC_SPECS.frame_rate
            ):
                self._video_standard = sys_consts.NTSC

        return self._video_standard

    @video_standard.setter
    def video_standard(self, value: str) -> None:
        """
        The video_standard method sets the video standard of a video PAL/NTSC.

        Args:
            value (str): Set the video standard of the video

        """
        assert isinstance(value, str) and value.upper() in (
            sys_consts.PAL,
            sys_consts.NTSC,
            "N/A",
        ), f"{value=}. Must be PAL or NTSC"
        if value.upper() == "N/A":
            if (
                self.video_width == sys_consts.PAL_SPECS.width_43
                and self.video_height == sys_consts.PAL_SPECS.height_43
                and self.video_frame_rate == sys_consts.PAL_SPECS.frame_rate
            ):
                value = sys_consts.PAL
            elif (
                self.video_width == sys_consts.NTSC_SPECS.width_43
                and self.video_height == sys_consts.NTSC_SPECS.height_43
                and self.video_frame_rate in (sys_consts.NTSC_SPECS.frame_rate, 30)
            ):
                value = sys_consts.NTSC

        self._video_standard = value.upper()

    @property
    def video_frame_count(self) -> int:
        """
        The video_frame_count method returns the number of frames in a video.

        Returns:
            int: The number of frames in the video

        """
        return self._video_frame_count

    @video_frame_count.setter
    def video_frame_count(self, value: int) -> None:
        """
        The video_frame_count method sets the number of frames in a video.

        Args:
            value (int): Set the number of frames in the video

        """
        assert isinstance(value, int), f"{value=}. Must be int"

        self._video_frame_count = value

    @property
    def video_scan_order(self) -> str:
        """
        The video_scan_order method returns the scan order of an interlaced video.

        Returns:
            str: The scan order of the video, bff (bottom field first) ot tff (top field first)

        """
        return self._video_scan_order

    @video_scan_order.setter
    def video_scan_order(self, value: str) -> None:
        """
        The video_scan_order method sets the scan order of an interlaced video.

        Args:
            value (str): Set the scan order of the video

        """
        assert isinstance(value, str) and value.lower() in (
            "bff",
            "tff",
        ), f"{value=}. Must be 'bff' | 'tff''"

        self._video_scan_order = value

    @property
    def video_scan_type(self) -> str:
        """
        The video_scan_type method returns the scan type of the video.

        Returns:
            str: The scan type of the video, interlaced or prgressive

        """
        return self._video_scan_type

    @video_scan_type.setter
    def video_scan_type(self, value: str) -> None:
        """
        The video_scan_type method sets the scan type of an interlaced video.

        Args:
            value (str): Set the scan type of the video

        """
        assert isinstance(value, str) and value.lower() in (
            "interlaced",
            "progressive",
        ), f"{value=}. Must be interlaced or progressive"

        self._video_scan_type = value


@dataclasses.dataclass(slots=True)
class Video_File_Settings:
    """Class to hold video file settings for each file comprising the DVD menu buttons"""

    _deactivate_filters: bool = False

    _normalise: bool = False
    _denoise: bool = False
    _white_balance: bool = False
    _sharpen: bool = False
    _auto_bright: bool = False
    _button_title: str = ""
    _menu_button_frame: int = -1
    _menu_group: int = -1

    def __post_init__(self) -> None:
        """Post init to check the file settings are valid"""

        assert isinstance(self._deactivate_filters, bool), (
            f"{self._deactivate_filters=}. Must be a bool"
        )
        assert isinstance(self._normalise, bool), f"{self._normalise=}. Must be a bool"
        assert isinstance(self._denoise, bool), f"{self._denoise=}. Must be a bool"
        assert isinstance(self._white_balance, bool), (
            f"{self._white_balance=}. Must be a bool"
        )
        assert isinstance(self._sharpen, bool), f"{self._sharpen=}. Must be a bool"
        assert isinstance(self._auto_bright, bool), (
            f"{self._auto_bright=}. Must be a bool"
        )
        assert isinstance(self._button_title, str), f"{self._button_title=} must be str"
        assert (
            isinstance(self._menu_button_frame, int)
            and self._menu_button_frame == -1
            or self._menu_button_frame >= 0
        ), f"{self._menu_button_frame=}. Must be int"
        assert (
            isinstance(self._menu_group, int)
            and self._menu_group == -1
            or self._menu_group >= 0
        ), f"{self._menu_group=}. Must be int >= 0 or == -1"

    @property
    def deactivate_filters(self) -> bool:
        """
        The deactivate_filters method overrides  the individual filter settings.

        Args:

        Returns:
            bool : True if deactivating all filters, otherwise False

        """
        return self._deactivate_filters

    @deactivate_filters.setter
    def deactivate_filters(self, value: bool) -> None:
        """
        The deactivate_filters method overrides  the individual filter settings..

        Args:
            value (bool): True to deactivate all filters via override

        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._deactivate_filters = value

    @property
    def filters_off(self) -> bool:
        """
        The filters_off method returns True if all the filter settings are off.

        Args:

        Returns:
            bool : True if all the filter settings are off otherwise False

        """
        if self.deactivate_filters:
            return True
        else:
            return not any(
                value
                for value in [
                    self._normalise,
                    self._denoise,
                    self._white_balance,
                    self._sharpen,
                    self._auto_bright,
                ]
            )

    @property
    def normalise(self) -> bool:
        """
        The normalise method is used to normalise the video image.
        The function returns a boolean value indicating whether video normalisation is set to be performed.

        Args:

        Returns:
            bool : A boolean value
        """
        return self._normalise

    @normalise.setter
    def normalise(self, value: bool) -> None:
        """
        The normalise method is used to get the video normalisation setting.

        Args:
            value (bool): True to normalise the video otherwise False

        Returns:
            None


        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._normalise = value

    @property
    def denoise(self) -> bool:
        """
        The denoise method is used to get the video denoising setting.

        Args:

        Returns:
            bool : True to denoise the video otherwise False
        """
        return self._denoise

    @denoise.setter
    def denoise(self, value: bool) -> None:
        """
        The denoise method is used to set the video denoising setting.

        Args:
            value (bool): True to denoise the video otherwise False
        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._denoise = value

    @property
    def white_balance(self) -> bool:
        """
        The white_balance method is used to get the video white balance setting.

        Args:

        Returns:
            bool : True to white balance the video otherwise False
        """

        return self._white_balance

    @white_balance.setter
    def white_balance(self, value: bool) -> None:
        """
        The white_balance method is used to set the video white balance setting.

        Args:
            value (bool): True to white balance the video otherwise False
        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._white_balance = value

    @property
    def sharpen(self) -> bool:
        """
        The sharpen method is used to get the video sharpening setting.

        Args:

        Returns:
            bool : True to sharpen the video otherwise False
        """
        return self._sharpen

    @sharpen.setter
    def sharpen(self, value: bool) -> None:
        """
        The sharpen method is used to set the video sharpening setting.

        Args:
            value (bool): True to sharpen the video otherwise False
        """

        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._sharpen = value

    @property
    def auto_bright(self) -> bool:
        """
        The auto_bright method is used to get the video auto brightness setting.

        Args:

        Returns:
            bool : True to auto brightness the video otherwise False
        """
        return self._auto_bright

    @auto_bright.setter
    def auto_bright(self, value: bool) -> None:
        """
        The auto_bright method is used to set the video auto brightness setting.

        Args:
            value (bool): True to auto brightness the video otherwise False
        """
        assert isinstance(value, bool), f"{value=}. Must be a bool"

        self._auto_bright = value

    @property
    def button_title(self) -> str:
        """
        The button_title method is used to get the title of the button.

        Args:

        Returns:
            str : The title of the button
        """
        assert isinstance(self._button_title, str), (
            f"{self._button_title=}. Must be a str"
        )

        return self._button_title

    @button_title.setter
    def button_title(self, value: str) -> None:
        """
        The button_title method is used to set the title of the button.

        Args:
            value (str): The title of the button
        """
        assert isinstance(value, str), f"{value=}. Must be a str"

        self._button_title = value

    @property
    def menu_button_frame(self) -> int:
        """
        The menu_button_frame method is used to get the frame number of the menu button.
        if -1 then a menu button frame has not been set and will be extracted automatically

        Args:

        Returns:
            int : The frame number of the menu button
        """
        assert (
            isinstance(self._menu_button_frame, int)
            and self._menu_button_frame == -1
            or self._menu_button_frame >= 0
        ), f"{self._menu_button_frame=}. Must be int >= 0 or == -1"

        return self._menu_button_frame

    @menu_button_frame.setter
    def menu_button_frame(self, value: int) -> None:
        """
        The menu_button_frame method is used to set the frame number of the menu button.

        Args:
            value: (int): Check if the value is an integer and that it's greater than or equal to 0 or equal -1 (auto set)

        Returns:
            None

        """
        assert isinstance(value, int) and value == -1 or value >= 0, (
            f"{value=}. Must be an int == -1 or >= 0"
        )
        self._menu_button_frame = value

    @property
    def menu_group(self) -> int:
        """
        The menu_group method is used to get the menu group number.
        if -1 then a menu group has not been set

        Args:

        Returns:
            int : The menu group number
        """
        assert (
            isinstance(self._menu_group, int)
            and self._menu_group == -1
            or self._menu_group >= 0
        ), f"{self._menu_group=}. Must be int >= 0 or == -1"

        return self._menu_group

    @menu_group.setter
    def menu_group(self, value: int) -> None:
        """
        The menu_group method is used to set the menu group number.

        Args:
            value: (int): Check if the value is an integer and that it's greater than or equal to 0 or equal -1 (not set)

        """
        assert isinstance(value, int) and value == -1 or value >= 0, (
            f"{value=}. Must be an int == -1 or >= 0"
        )
        self._menu_group = value


@dataclasses.dataclass(slots=True)
class Video_Data:
    """
    video data container class.
    Attributes:
        video_folder (str): The path to the folder containing the video.
        video_file (str): The name of the video file.
        video_extension (str): The file extension of the video file.
        encoding_info (Video_Details): Information about the encoding of the video.
        video_file_settings (Video_File_Settings): The video file settings.
        vd_id (int): The id of the video data. Defaults to -1.
    """

    # Public instance variables
    video_folder: str
    video_file: str
    video_extension: str
    encoding_info: Encoding_Details
    video_file_settings: Video_File_Settings
    dvd_page: int = -1
    vd_id: int = -1

    # Private instance variables
    _menu_image_file_path: str = ""

    def __post_init__(self) -> None:
        """
        The __post_init__ method is used to set the video data.
        """
        assert isinstance(self.video_folder, str) and self.video_folder.strip() != "", (
            f"{self.video_folder=} must be str"
        )
        assert isinstance(self.video_file, str) and self.video_file.strip() != "", (
            f"{self.video_file=} must be str"
        )
        assert (
            isinstance(self.video_extension, str) and self.video_extension.strip() != ""
        ), f"{self.video_extension=} must be str"
        assert isinstance(self.encoding_info, Encoding_Details), (
            f"{self.encoding_info=}. Must be Encoding_Details"
        )
        assert isinstance(self.video_file_settings, Video_File_Settings), (
            f"{self.video_file_settings=}. Must be an instance of Video_Filter_Settings"
        )

        assert (
            isinstance(self.dvd_page, int) and self.dvd_page == -1 or self.dvd_page >= 0
        ), f"{self.dvd_page=}. Must be an int == -1 or >= 0"

        assert isinstance(self.vd_id, int) and self.vd_id == -1 or self.vd_id >= 0, (
            f"{self.vd_id=}. Must be an int == -1 or >= 0"
        )

        if self.vd_id == -1:
            self.vd_id = id(self)

    @property
    def video_path(self) -> str:
        """
        Gets the full path to the video file.
        Returns:
            str: The full path to the video file
        """
        video_path = file_utils.File().file_join(
            self.video_folder, self.video_file, self.video_extension
        )

        return video_path

    @property
    def menu_image_file_path(self) -> str:
        """
        The menu_image_file_path method is used to get the menu image file path.

        Returns:
            str: The menu image file path
        """
        assert file_utils.File().file_exists(self._menu_image_file_path), (
            f"{self._menu_image_file_path=}. Path does not exist"
        )

        return self._menu_image_file_path

    @menu_image_file_path.setter
    def menu_image_file_path(self, value: str) -> None:
        """
        The menu_image_file_path method is used to set the menu image file path.

        Args:
            value: (str): The menu image file path

        """
        assert isinstance(value, str) and value.strip() != "", (
            f"{value=}. Must be a file path"
        )

        assert file_utils.File().file_exists(value), f"{value=}. Path does not exist"

        self._menu_image_file_path = value
