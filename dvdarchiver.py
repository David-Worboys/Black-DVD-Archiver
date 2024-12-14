"""
Implements the Black DVD archiver UI.

Black because it simplifies the production of a DVD image by making the choices I think are best.
The user choice of the menu button layout is restricted by these choices and will remain so.

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

from typing import cast

import platformdirs

import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups
import QTPYGUI.qtpygui as qtg
import QTPYGUI.utils as utils
import QTPYGUI.sqldb as sqldb
import sys_consts
from background_task_manager import Task_Manager_Popup
from dvd import DVD, DVD_Config
from menu_page_title_popup import Menu_Page_Title_Popup
from sys_config import (
    DVD_Archiver_Base,
    DVD_Menu_Settings,
    Get_Video_Editor_Folder,
    Get_Project_Layout_Names,
    Set_Shelved_DVD_Layout,
    Video_Data,
    Migrate_Shelves_To_DB,
    Set_Shelved_Project,
    Delete_Project,
    Delete_DVD_Layout,
)

from QTPYGUI.utils import Countries, Text_To_File_Name
from video_cutter import Video_Editor
from video_file_grid import Video_File_Grid

# These global functions and variables are only used by the multi-thread task_manager process and exist by
# necessity as this seems the only way to communicate the variable values to the rest of the dvdarchiver code
gi_task_error_code = -1
gi_thread_status = -1
gs_thread_error_message = ""
gs_task_error_message = ""
gs_thread_status = ""
gs_thread_message = ""
gs_thread_output = ""
gs_thread_task_name = ""


def Run_DVD_Build(dvd_instance: DVD) -> tuple[int, str]:
    """This is a wrapper function used hy the multi-thread task_manager to run the DVD build process

    Args:
        dvd_instance (DVD): The DVD instance that creates the DVD files and folders.

    Returns:
        tuple[int, str]:
        - arg1 1: ok, -1: fail
        - arg2: error message or "" if ok
    """
    global gi_task_error_code
    global gs_task_error_message

    gi_task_error_code, gs_task_error_message = dvd_instance.build()

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

    gs_thread_status = status
    gs_thread_message = message
    gs_thread_output = output
    gs_thread_task_name = name

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


class DVD_Archiver(DVD_Archiver_Base):
    """
    Class for archiving DVDs.

    """

    def __init__(self, program_name: str = "") -> None:
        """
        Sets up the instance of the class, and initializes all its attributes.

        Attributes:



        """
        assert isinstance(program_name, str), f"{program_name=}. Must be str"

        super().__init__()

        self._DVD_Arch_App = qtg.QtPyApp(
            display_name=program_name if program_name else sys_consts.PROGRAM_NAME,
            callback=self.event_handler,
            height=900,
            icon=file_utils.App_Path("logo.jpg"),
            width=1200,
        )

        self._startup = True
        self._shutdown = False
        self._control_tab: qtg.Tab | None = None

        self._data_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

        self._file_control = Video_File_Grid(parent=self)
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        # A problem in the next 3 lines can shut down startup as database initialization failed
        if self._db_settings.error_code == -1:
            raise RuntimeError(
                f"Failed To Start {sys_consts.PROGRAM_NAME} -"
                f" {self._db_settings.error_message}"
            )
        self._app_db = self.db_init()
        self._db_tables_create()

        if self._db_settings.new_cfg:
            # Do stuff that the application only ever needs to do once on first
            # startup of a new installation
            Set_Shelved_DVD_Layout(
                project_name=sys_consts.DEFAULT_PROJECT_NAME_DBK,
                dvd_layout_name=sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK,
                dvd_menu_layout=[],
            )
            self._db_settings.new_cfg = False

        self._menu_title_font_size = 24
        self._timestamp_font_point_size = 9
        self._default_font = sys_consts.DEFAULT_FONT

        self._video_editor: Video_Editor | None = None
        self._save_existing_project = True
        self._task_stack = {}  # Used to keep track of running tasks

    def db_init(self) -> sqldb.SQLDB:
        """
        Initializes the application database and returns a SQLDB object.

        Returns:
            sqldb.SQLDB: A SQLDB object representing the application database.

        """
        file_handler = file_utils.File()

        if not file_handler.path_exists(self._data_path):
            print(f"*** Need To Create {self._data_path}")
            file_handler.make_dir(self._data_path)

            if not file_handler.path_exists(self._data_path):
                raise RuntimeError(
                    f"Failed To Create {sys_consts.PROGRAM_NAME} Data Folder"
                )

        app_database = sqldb.SQLDB(
            appname=sys_consts.PROGRAM_NAME,
            dbpath=self._data_path,
            dbfile=sys_consts.PROGRAM_NAME,
            suffix=".db",
            dbpassword="666evil",
        )

        error_status = app_database.get_error_status()

        if error_status.code == -1:
            raise RuntimeError(
                f"Failed To Start {sys_consts.PROGRAM_NAME} - {error_status.message}"
            )
        return app_database

    def _db_tables_create(self) -> None:
        """Create a database tables used by the DVD Archiver in the SQL database using sqldb.

        If the tables already exist, this method does nothing.  If an error occurs during table creation
        or initialization, a RuntimeError is raised with an error message.

        Raises:
            RuntimeError: If an error occurs during table creation or initialization.

        Returns:
            None.
        """
        if not self._app_db.table_exists(sys_consts.PRODUCT_LINE):
            product_line_def = (
                sqldb.ColDef(
                    name="id",
                    description="pk_id",
                    data_type=sqldb.SQL.INTEGER,
                    primary_key=True,
                ),
                sqldb.ColDef(
                    name="code",
                    description="Product Line Code",
                    data_type=sqldb.SQL.VARCHAR,
                    size=5,
                ),
                sqldb.ColDef(
                    name="description",
                    description="Description of DVD Product Line",
                    data_type=sqldb.SQL.VARCHAR,
                    size=80,
                ),
            )

            if (
                self._app_db.table_create(
                    table_name=sys_consts.PRODUCT_LINE, col_defs=product_line_def
                )
                == -1
            ):
                error_status = self._app_db.get_error_status()

                raise RuntimeError(
                    f"Failed To Create {sys_consts.PROGRAM_NAME} Database -"
                    f" {error_status.message}"
                )
            # Load a default product line
            self._app_db.sql_update(
                col_dict={"code": "HV", "description": "Home Video"},
                table_str=sys_consts.PRODUCT_LINE,
            )

            error_status = self._app_db.get_error_status()
            if error_status.code == -1:
                raise RuntimeError(
                    f"Failed To Initialise {sys_consts.PROGRAM_NAME} Database -"
                    f" {error_status.message}"
                )

    def event_handler(self, event: qtg.Action) -> int | None:
        """Handles application events

        Args:
            event (Action): The triggering event
        """
        if self._file_control:
            self._file_control.event_handler(event)

        match event.event:
            case qtg.Sys_Events.APPINIT:
                pass
            case qtg.Sys_Events.APPEXIT | qtg.Sys_Events.APPCLOSED:
                if not self._shutdown:  # Prevent getting called twice
                    self._shutdown = True
                    if (
                        popups.PopYesNo(
                            title="Exit Application...",
                            message=(
                                "Exit The"
                                f" {sys_consts.SDELIM}{sys_consts.PROGRAM_NAME}?{sys_consts.SDELIM}"
                            ),
                        ).show()
                        == "yes"
                    ):
                        if self._video_editor.shutdown() == 1:
                            # Remove the temporary DVD Build Folder subdirectories
                            with qtg.sys_cursor(qtg.Cursor.hourglass):
                                if self._db_settings.setting_exist(
                                    sys_consts.DVD_BUILD_FOLDER_DBK
                                ):
                                    file_handler = file_utils.File()

                                    working_folder = self._db_settings.setting_get(
                                        sys_consts.DVD_BUILD_FOLDER_DBK
                                    )

                                    dvd_working_folder = file_handler.file_join(
                                        working_folder, sys_consts.DVD_BUILD_FOLDER_NAME
                                    )

                                    file_handler.remove_dir_contents(
                                        dvd_working_folder, keep_parent=True
                                    )

                            return 1
                        else:
                            self._shutdown = False
                            return -1
                    else:
                        self._shutdown = False
                        return -1
            case qtg.Sys_Events.APPPOSTINIT:
                pass  # Consumed in video_file_grid caught in CUSTOM/project_changed below
            case qtg.Sys_Events.CHANGED:  # Tab changed!
                match event.tag:
                    case "control_tab":
                        with qtg.sys_cursor(qtg.Cursor.hourglass):
                            self._video_editor.video_pause()
                            self._video_editor.archive_edit_list_write()

                            if self._video_editor.video_file_input:
                                self._file_control.process_edited_video_files(
                                    video_file_input=self._video_editor.video_file_input
                                )

                            self._tab_enable_handler(event=event, enable=True)
                    case "video_editor_tab":
                        with qtg.sys_cursor(qtg.Cursor.hourglass):
                            self._tab_enable_handler(event=event, enable=False)

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "archive_folder_select":
                        self._archive_folder_select(event)
                    case "backup_bluray":
                        self._db_settings.setting_set(
                            sys_consts.ARCHIVE_DISK_SIZE_DBK,
                            sys_consts.BLUERAY_ARCHIVE_SIZE,
                        )
                    case "backup_dvd":
                        self._db_settings.setting_set(
                            sys_consts.ARCHIVE_DISK_SIZE_DBK,
                            sys_consts.DVD_ARCHIVE_SIZE,
                        )
                    case "delete_dvd_layout":
                        self._delete_dvd_layout(event)
                    case "delete_project":
                        self._delete_project(event)
                    case "dvd_folder_select":
                        self._dvd_folder_select(event)
                    case "exit_app":
                        self._DVD_Arch_App.app_exit()
                    case "langtran":
                        popups.Langtran_Popup().show()
                    case "make_dvd":
                        self._make_dvd(event)
                    case "new_dvd_layout":
                        self._new_dvd_layout(event)
                    case "new_project":
                        self._new_project(event)
                    case "streaming_folder_select":
                        self._streaming_folder_select(event)
                    case "task_manager":
                        if self._video_editor.get_task_manager:
                            Task_Manager_Popup(
                                title="Task Manager",
                                task_manager=self._video_editor.get_task_manager,
                            ).show()
                    case "transcode_none":
                        self._db_settings.setting_set(
                            sys_consts.ARCHIVE_DISK_TRANSCODE_DBK,
                            sys_consts.TRANSCODE_NONE,
                        )
                    case "transcode_archival":
                        self._db_settings.setting_set(
                            sys_consts.ARCHIVE_DISK_TRANSCODE_DBK,
                            sys_consts.TRANSCODE_FFV1ARCHIVAL,
                        )
                    case "transcode_h264":
                        self._db_settings.setting_set(
                            sys_consts.ARCHIVE_DISK_TRANSCODE_DBK,
                            sys_consts.TRANSCODE_H264,
                        )
                    case "transcode_h265":
                        self._db_settings.setting_set(
                            sys_consts.ARCHIVE_DISK_TRANSCODE_DBK,
                            sys_consts.TRANSCODE_H265,
                        )
                    case "video_editor":  # Signal from file_grid
                        video_edit_folder = Get_Video_Editor_Folder()
                        video_data: list[Video_Data] = event.value

                        if (
                            video_data[0].encoding_info.video_duration
                            < 5  # ~ ! seconds
                            or video_data[0].encoding_info.error.strip() != ""
                        ):
                            popups.PopError(
                                title="Video File Is Invalid...",
                                message=(
                                    "Selected Video File Is Not  Supported, Corrupt Or"
                                    " Too Short < 5 seconds"
                                    f" ({video_data[0].encoding_info.video_duration} seconds)"
                                    f" : {video_data[0].video_path} "
                                ),
                            ).show()
                            return None

                        if video_edit_folder.strip() == "":
                            popups.PopError(
                                title="DVD Build Folder Not Set...",
                                message=(
                                    "Please Enter The DVD Build Folder To Edit Video"
                                    " Files"
                                ),
                            ).show()
                            return None

                        self._video_editor.set_source(
                            video_file_input=video_data,
                            output_folder=video_edit_folder,
                            project_name=self._file_control.project_name,
                        )
                        self._control_tab.select_tab(tag_name="video_editor_tab")
                        self._control_tab.enable_set(
                            tag="video_editor_tab", enable=True
                        )

            case (
                qtg.Sys_Events.CUSTOM
            ):  # APPPOSTINIT is consumed and CUSTOM is emitted in its place
                match event.tag:
                    case "project_changed":
                        if event.widget_exist(
                            container_tag="main_controls", tag="existing_projects"
                        ):
                            project_combo: qtg.ComboBox = cast(
                                qtg.ComboBox,
                                event.widget_get(
                                    container_tag="main_controls",
                                    tag="existing_projects",
                                ),
                            )

                            project_combo.select_text(
                                self._file_control.project_name, partial_match=False
                            )

                        self._control_tab.select_tab(tag_name="control_tab")
                        self._control_tab.enable_set(
                            tag="video_editor_tab", enable=False
                        )

                        # Because APPPOSTINIT is consumed in the video file grid, this is how we achieve the same thing
                        # as CUSTOM is emitted at startup
                        if self._startup:
                            self._startup_handler(event)

                        self._startup = False

            case qtg.Sys_Events.INDEXCHANGED:  # Combobox changes
                match event.tag:
                    case "existing_projects":
                        self._project_combo_change(event)
                    case "countries":
                        if not self._startup:
                            self._language_setting_handler(event)

        return None

    def _language_setting_handler(self, event: qtg.Action) -> None:
        """Handles the setting of the application language

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        combo_data: qtg.Combo_Data = event.value
        if combo_data.data == "N/A":  # Sets default language - untranslated is English
            self._db_settings.setting_set(
                setting_name=sys_consts.APP_LANG_DBK,
                setting_value="",
            )

            self._db_settings.setting_set(
                setting_name=sys_consts.APP_COUNTRY_DBK,
                setting_value="",
            )
        else:
            self._db_settings.setting_set(
                setting_name=sys_consts.APP_LANG_DBK,
                setting_value=combo_data.data,
            )
            self._db_settings.setting_set(
                setting_name=sys_consts.APP_COUNTRY_DBK,
                setting_value=combo_data.display,
            )

    def _startup_handler(self, event: qtg.Action) -> None:
        """Performs activities that have to happen at startup

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        if event.widget_exist(
            container_tag="app_lang", tag="countries"
        ):  # Selects tha app language
            country_combo: qtg.ComboBox = cast(
                qtg.ComboBox,
                event.widget_get(container_tag="app_lang", tag="countries"),
            )

            if self._db_settings.setting_exist(setting_name=sys_consts.APP_COUNTRY_DBK):
                app_country = self._db_settings.setting_get(
                    setting_name=sys_consts.APP_COUNTRY_DBK
                )

                if app_country:
                    country_combo.select_text(
                        select_text=app_country,
                        case_sensitive=False,
                        partial_match=False,
                    )

    def _tab_enable_handler(self, event: qtg.Action, enable: bool):
        """Enables or disables the tab dependent controls

        Args:
            event (qtg.Action): The triggering event
            enable (bool): True - enables tab sensitive controls, False - disables tab sensitive controls
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"
        assert isinstance(enable, bool), f"{enable=}. Must be bool"

        if event.widget_exist(
            container_tag="main_controls", tag="existing_projects"
        ):  # Buttons are buddies so must exist
            project_combo: qtg.ComboBox = cast(
                qtg.ComboBox,
                event.widget_get(
                    container_tag="main_controls", tag="existing_projects"
                ),
            )

            delete_button: qtg.Button = cast(
                qtg.Button,
                event.widget_get(container_tag="main_controls", tag="delete_project"),
            )

            new_button: qtg.Button = cast(
                qtg.Button,
                event.widget_get(container_tag="main_controls", tag="new_project"),
            )

            delete_button.enable_set(enable)
            new_button.enable_set(enable)

            project_combo.enable_set(enable)

        if event.widget_exist(container_tag="main_controls", tag="existing_layouts"):
            dvd_layout_combo: qtg.ComboBox = cast(
                qtg.ComboBox,
                event.widget_get(container_tag="main_controls", tag="existing_layouts"),
            )
            delete_button: qtg.Button = cast(
                qtg.Button,
                event.widget_get(
                    container_tag="main_controls", tag="delete_dvd_layout"
                ),
            )

            new_button: qtg.Button = cast(
                qtg.Button,
                event.widget_get(container_tag="main_controls", tag="new_dvd_layout"),
            )
            make_button: qtg.Button = cast(
                qtg.Button,
                event.widget_get(container_tag="main_controls", tag="make_dvd"),
            )

            make_button.enable_set(enable)
            delete_button.enable_set(enable)
            new_button.enable_set(enable)

            dvd_layout_combo.enable_set(enable)

    def _project_combo_change(self, event: qtg.Action):
        """Handles the change of a project combo item

        Args:
            event (qtg.Action): Triggering event (INDEXCHANGED in this case)
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        new_project: qtg.Combo_Item = event.value

        if (
            not self._startup
            and new_project.display.strip()
            and self._file_control.project_name.strip() != new_project.display.strip()
        ):
            self._file_control.project_changed(
                event, new_project.display, self._save_existing_project
            )
            if event.widget_exist(
                container_tag="main_controls", tag="existing_projects"
            ) and event.widget_exist(
                container_tag="main_controls", tag="existing_layouts"
            ):
                project_combo: qtg.ComboBox = cast(
                    qtg.ComboBox,
                    event.widget_get(
                        container_tag="main_controls",
                        tag="existing_projects",
                    ),
                )
                layout_combo: qtg.ComboBox = cast(
                    qtg.ComboBox,
                    event.widget_get(
                        container_tag="main_controls",
                        tag="existing_layouts",
                    ),
                )

                layout_combo.clear()

                project_combo.select_text(
                    self._file_control.project_name, partial_match=False
                )

                _, layout_items, _ = Get_Project_Layout_Names(
                    self._file_control.project_name
                )

                layout_combo_items = [
                    qtg.Combo_Data(
                        index=-1,
                        display=item.replace("_", " "),
                        data=item.replace("_", " "),
                        user_data=None,
                    )
                    for item in layout_items
                ]

                for item in layout_combo_items:
                    layout_combo.value_set(item)

    def _archive_folder_select(self, event: qtg.Action) -> None:
        """Select an archive folder and updates the settings in the database with the selected folder.

        Args:
            event (qtg.Action): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER_DBK)

        if folder is None or folder.strip() == "":
            folder = file_utils.Special_Path(qtg.Special_Path.VIDEOS)

        folder = popups.PopFolderGet(
            title="Select An Archive Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()

        if folder.strip() != "":
            self._db_settings.setting_set(sys_consts.ARCHIVE_FOLDER_DBK, folder)

            event.value_set(
                container_tag="dvd_properties",
                tag="archive_path",
                value=f"{sys_consts.SDELIM}{folder}{sys_consts.SDELIM}",
            )

    def _streaming_folder_select(self, event: qtg.Action) -> None:
        """Select a streaming folder and updates the settings in the database with the selected folder.

        Args:
            event (qtg.Action): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        folder = self._db_settings.setting_get(sys_consts.STREAMING_FOLDER_DBK)

        if folder is None or folder.strip() == "":
            folder = file_utils.Special_Path(qtg.Special_Path.VIDEOS)

        folder = popups.PopFolderGet(
            title="Select A Streaming Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()

        if folder.strip() != "":
            self._db_settings.setting_set(sys_consts.STREAMING_FOLDER_DBK, folder)

            event.value_set(
                container_tag="dvd_properties",
                tag="streaming_path",
                value=f"{sys_consts.SDELIM}{folder}{sys_consts.SDELIM}",
            )

    def _delete_dvd_layout(self, event: qtg.Action) -> None:
        """Deletes a dvd layout by removing the corresponding python shelf files

        Args:
            event (qtg.Action): Triggering event
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        dvd_layout_combo: qtg.ComboBox = cast(
            qtg.ComboBox,
            event.widget_get(container_tag="main_controls", tag="existing_layouts"),
        )

        layout_data = dvd_layout_combo.value_get()

        if (
            popups.PopYesNo(
                title="Delete DVD Layout...",
                message=(
                    "Delete DVD Layout"
                    f" {sys_consts.SDELIM}{layout_data.display}{sys_consts.SDELIM} ? "
                ),
            ).show()
            == "no"
        ):
            return None

        if (
            self._file_control.project_name.strip() and layout_data.display.strip()
        ):  # Should always have
            result, message = Delete_DVD_Layout(
                project_name=self._file_control.project_name,
                layout_name=layout_data.display,
            )

            if result == -1:
                popups.PopError(
                    title="DB Error...",
                    message=(
                        "Failed To Delete DVD Layout"
                        f" {sys_consts.SDELIM}{layout_data.display}{sys_consts.SDELIM} - {message}!"
                    ),
                )
                return None

            # Remove from layout combo
            dvd_layout_combo.value_remove(layout_data.index)

            if dvd_layout_combo.count_items == 0:
                dvd_layout_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK,
                        data=f"{self._file_control.project_name}.{sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK}",
                        user_data=None,
                    )
                )
                result, message = Set_Shelved_DVD_Layout(
                    project_name=self._file_control.project_name,
                    dvd_layout_name=sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK,
                    dvd_menu_layout=[],
                )

                if result == -1:
                    popups.PopError(
                        title="DB Error...",
                        message="Failed To Create Default DVD Layout - {message}!",
                    )

        return None

    def _dvd_folder_select(self, event) -> None:
        """Select a DVD build folder and updates the settings in the database with the selected folder.

        Args:
            event (Event): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER_DBK)

        if folder is None or folder.strip() == "":
            folder = file_utils.Special_Path(qtg.Special_Path.VIDEOS)

        folder = popups.PopFolderGet(
            title="Select A DVD Build Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()

        if folder.strip() != "":
            self._db_settings.setting_set(sys_consts.DVD_BUILD_FOLDER_DBK, folder)

            event.value_set(
                container_tag="dvd_properties",
                tag="dvd_path",
                value=f"{sys_consts.SDELIM}{folder}{sys_consts.SDELIM}",
            )

    def _generate_dvd_serial_number(
        self, product_code: str = "HV", product_description="Home Video"
    ) -> str:
        """
        Generates a DVD serial number with the format "DVD-AB-000001-5"

        Parameters:
            product_code (str): A string that identifies the product code, e.g. "HV" for home video.
            product_description (str): A string that describes the product code, e.g. "Home Video" for home video.

        Returns:
            str: A string containing the generated DVD serial number.
        """
        assert (
            isinstance(product_code, str) and product_code.strip() != ""
        ), f"{product_code=}. Must be a non-empty string"
        assert (
            isinstance(product_description, str) and product_description.strip() != ""
        ), f"{product_description=}. Must be a non-empty string"

        # Increment the sequential number for each DVD produced
        if not self._db_settings.setting_exist(sys_consts.SERIAL_NUMBER_DBK):
            self._db_settings.setting_set(sys_consts.SERIAL_NUMBER_DBK, 0)

        serial_number: int = cast(
            int, self._db_settings.setting_get(sys_consts.SERIAL_NUMBER_DBK)
        )
        serial_number += 1
        self._db_settings.setting_set(sys_consts.SERIAL_NUMBER_DBK, serial_number)

        # Generate the serial number string
        serial_number_str = "{:06d}".format(serial_number)

        # TODO: Remove this code, and associated variables, in the future if it proves unnecessary
        # 17/01/2024 DAW On consideration this seems unnecessary and complicates things
        # serial_number_checksum = hashlib.md5(serial_number_str.encode()).hexdigest()[0]
        # serial_number_str = (
        #     f"DVD-{product_code}-{serial_number_str}-{serial_number_checksum}"
        # )

        serial_number_str = f"DVD-{serial_number_str}"

        return serial_number_str

    def _make_dvd(self, event: qtg.Action) -> None:
        """
        Builds a DVD with the given video files and menu attributes.

        Args:
            event (Action): The triggering event

        Returns:
            None.

        Note:
            - The menu attributes are obtained from the ComboBox instances.
            - The video input files and menu labels are obtained from the Grid instance.
            - The DVD is built using the DVD class and the DVD_Config instance created from the inputs.
            - The result and error message are used to show an error dialog if the build fails.

        """

        assert isinstance(
            event, qtg.Action
        ), f"{event} is not an instance of qtg.Action"

        project_combo: qtg.ComboBox = cast(
            qtg.ComboBox,
            event.widget_get(container_tag="main_controls", tag="existing_projects"),
        )

        project_name = project_combo.value_get().display

        dvd_layout_combo: qtg.ComboBox = cast(
            qtg.ComboBox,
            event.widget_get(container_tag="main_controls", tag="existing_layouts"),
        )

        dvd_layout_name = dvd_layout_combo.value_get().display

        if self._file_control.dvd_percent_used + sys_consts.PERCENT_SAFTEY_BUFFER > 100:
            popups.PopError(
                title="DVD Build Error...",
                message="Selected Files Will Not Fit On A DVD!",
            ).show()
            return None

        dvd_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER_DBK)

        if dvd_folder is None or dvd_folder.strip() == "":
            popups.PopError(
                title="DVD Build Folder Error...",
                message="A DVD Build Folder Must Be Entered Before Making A DVD!",
            ).show()
            return None

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        checked_items: tuple[qtg.Grid_Item] = file_grid.checkitems_get

        menu_video_data: list[Video_Data] = [file.user_data for file in checked_items]
        menu_layout: list[tuple[str, list[Video_Data]]] = []
        if (
            Menu_Page_Title_Popup(
                title=(
                    "DVD Layout -"
                    f" {sys_consts.SDELIM}{dvd_layout_combo.value_get().display}{sys_consts.SDELIM}"
                ),
                video_data_list=menu_video_data,  # Pass by reference
                menu_layout=menu_layout,  # Pass by reference
                project_name=project_name,
                dvd_layout_name=dvd_layout_name,
            ).show()
            == "cancel"
        ):
            return None

        video_files: list[Video_Data] = []
        menu_title: list[str] = []
        disk_title = ""
        dvd_menu_settings = DVD_Menu_Settings()

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            file_grid.checkitems_all(checked=False, col_tag="video_file")
            for menu_item in menu_layout:
                menu_title.append(menu_item[0])
                video_data_items: list[Video_Data] = menu_item[1]

                if (
                    len(menu_item) >= 3 and disk_title.strip() == ""
                ):  # Disk title is a later add-on so need this to set it
                    disk_title = menu_item[2]["disk_title"]

                for video_item in video_data_items:
                    video_files.append(video_item)

        if video_files:
            dvd_config = DVD_Config()

            dvd_config.menu_aspect_ratio = self._db_settings.setting_get(
                sys_consts.MENU_ASPECT_RATIO_DBK
            )

            dvd_config.project_name = (
                self._file_control.project_name
                if disk_title.strip() == ""
                else Text_To_File_Name(disk_title)
            )

            if self._db_settings.setting_exist(sys_consts.ARCHIVE_FOLDER_DBK):
                dvd_config.archive_folder = self._db_settings.setting_get(
                    sys_consts.ARCHIVE_FOLDER_DBK
                )
            if self._db_settings.setting_exist(sys_consts.STREAMING_FOLDER_DBK):
                dvd_config.streaming_folder = self._db_settings.setting_get(
                    sys_consts.STREAMING_FOLDER_DBK
                )
            if self._db_settings.setting_exist(sys_consts.ARCHIVE_DISK_SIZE_DBK):
                dvd_config.archive_size = self._db_settings.setting_get(
                    sys_consts.ARCHIVE_DISK_SIZE_DBK
                )
            else:
                dvd_config.archive_size = sys_consts.DVD_ARCHIVE_SIZE

            if self._db_settings.setting_exist(sys_consts.ARCHIVE_DISK_TRANSCODE_DBK):
                dvd_config.transcode_type = self._db_settings.setting_get(
                    sys_consts.ARCHIVE_DISK_TRANSCODE_DBK
                )
            else:
                dvd_config.transcode_type = sys_consts.TRANSCODE_NONE

            # TODO: Remove this code, and associated variables, in the future if it proves unnecessary
            # 17/01/2024 DAW On consideration this seems unnecessary and complicates things
            # sql_result = self._app_db.sql_select(
            #     col_str="code,description",
            #     table_str=sys_consts.PRODUCT_LINE,
            #     where_str="code='HV'",
            # )

            # if sql_result:  # Expect only one result
            #     product_code = sql_result[0][0]
            #     product_description = sql_result[0][1]

            dvd_serial_number = self._generate_dvd_serial_number(
                # product_code=product_code,
                # product_description=product_description,
            )
            dvd_config.serial_number = dvd_serial_number

            dvd_config.input_videos = video_files

            dvd_config.menu_title = menu_title
            dvd_config.menu_background_color = dvd_menu_settings.menu_background_color
            dvd_config.menu_font = dvd_menu_settings.menu_font
            dvd_config.menu_font_color = dvd_menu_settings.menu_font_color
            dvd_config.menu_font_point_size = dvd_menu_settings.menu_font_point_size
            dvd_config.page_pointer_left_file = dvd_menu_settings.page_pointer_left
            dvd_config.page_pointer_right_file = dvd_menu_settings.page_pointer_right
            dvd_config.button_background_color = (
                dvd_menu_settings.button_background_color
            )
            dvd_config.button_font = dvd_menu_settings.button_font
            dvd_config.button_font_color = dvd_menu_settings.button_font_color
            dvd_config.button_font_point_size = dvd_menu_settings.button_font_point_size
            dvd_config.button_background_transparency = (
                dvd_menu_settings.button_background_transparency / 100
            )

            dvd_config.timestamp_font = self._default_font
            dvd_config.timestamp_font_point_size = self._timestamp_font_point_size

            dvd_config.video_standard = self._file_control.project_video_standard

            dvd_config.menu_buttons_across = dvd_menu_settings.buttons_across
            dvd_config.menu_buttons_per_page = dvd_menu_settings.buttons_per_page

            dvd_creator = DVD()
            dvd_creator.dvd_config = dvd_config
            dvd_creator.working_folder = dvd_folder

            if self._video_editor.get_task_manager is None:
                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    result, message = dvd_creator.build()

                    if result == -1:
                        popups.PopError(
                            title="DVD Build Error...",
                            message=(
                                "Failed To Create A"
                                f" DVD!!\n{sys_consts.SDELIM}{message}{sys_consts.SDELIM}"
                            ),
                        ).show()
            else:
                task_name = dvd_config.project_name

                if task_name.strip() == "":  # Should not happen!
                    task_name = dvd_config.serial_number

                if task_name in self._task_stack:
                    for task_index in range(len(self._task_stack.items())):
                        temp_name = f"{task_name}_{task_index}"
                        if temp_name not in self._task_stack:
                            task_name = temp_name
                            break

                self._task_stack[task_name] = (dvd_creator, menu_layout)

                self._video_editor.get_task_manager.set_error_callback(Error_Callback)

                self._video_editor.get_task_manager.add_task(
                    name=task_name,
                    method=Run_DVD_Build,
                    arguments=(dvd_creator,),
                    callback=Notification_Call_Back,
                )

    def _new_dvd_layout(self, event: qtg.Action) -> None:
        """
        Creates A New DVD layout.

        Args:
            event (qtg.Action): The triggering event.
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        file_grid: qtg.Grid = cast(
            qtg.Grid,
            event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            ),
        )

        dvd_layout_combo: qtg.ComboBox = cast(
            qtg.ComboBox,
            event.widget_get(container_tag="main_controls", tag="existing_layouts"),
        )

        layout_name = popups.PopTextGet(
            title="Enter DVD Layout Name...",
            label="DVD Layout Name:",
            label_above=True,
        ).show()

        if self._file_control.project_name.strip() and layout_name.strip():
            if dvd_layout_combo.select_text(layout_name, partial_match=False) >= 0:
                popups.PopMessage(
                    title="Invalid DVD Layout Name",
                    message="A DVD Layout Wih That Name Already Exists!",
                ).show()
            else:
                result, message = Set_Shelved_DVD_Layout(
                    project_name=self._file_control.project_name,
                    dvd_layout_name=layout_name,
                    dvd_menu_layout=[],
                )

                if result == -1:
                    popups.PopError(title="DB Error...", message=message)
                    return None

                dvd_layout_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=layout_name,
                        data=layout_name,
                        user_data=None,
                    )
                )

                dvd_layout_combo.select_text(layout_name, partial_match=False)
                file_grid.checkitems_all(checked=False, col_tag="video_file")
                self._file_control.set_project_standard_duration(event)
        return None

    def _new_project(self, event: qtg.Action):
        """Create a new project
        Args:
            event:qtg.Action: The triggering event
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        project_name = popups.PopTextGet(
            title="Enter Project Name",
            label="Project Name:",
            label_above=True,
        ).show()

        if project_name.strip():
            project_combo: qtg.ComboBox = cast(
                qtg.ComboBox,
                event.widget_get(
                    container_tag="main_controls", tag="existing_projects"
                ),
            )

            if project_combo.select_text(project_name, partial_match=False) >= 0:
                popups.PopMessage(
                    title="Invalid Project Name",
                    message="A Project With That Name Already Exists!",
                ).show()
            else:
                Set_Shelved_Project(
                    project_name=project_name,
                    dvd_menu_layout_names=[sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK],
                )

                project_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=project_name,
                        data=project_name,
                        user_data=None,
                    )
                )
                file_grid: qtg.Grid = cast(
                    qtg.Grid,
                    event.widget_get(
                        container_tag="video_file_controls", tag="video_input_files"
                    ),
                )

                file_grid.clear()

    def _delete_project(self, event: qtg.Action) -> None:
        """Deletes a project by removing the corresponding python sql shelf data

        Args:
            event (qtg.Action): Triggering event
        """
        assert isinstance(event, qtg.Action), f"{qtg.Action=}. Must be a qtg.Action"

        project_combo: qtg.ComboBox = cast(
            qtg.ComboBox,
            event.widget_get(container_tag="main_controls", tag="existing_projects"),
        )

        dvd_layout_combo: qtg.ComboBox = cast(
            qtg.ComboBox,
            event.widget_get(container_tag="main_controls", tag="existing_layouts"),
        )

        if (
            popups.PopYesNo(
                title="Delete Project...",
                message=(
                    "Delete Project"
                    f" {sys_consts.SDELIM}{self._file_control.project_name}{sys_consts.SDELIM} "
                    "And All Project Data Except Source Video Files ?"
                ),
            ).show()
            == "no"
        ):
            return None

        result, message = Delete_Project(project_name=self._file_control.project_name)

        if result == -1:
            popups.PopError(
                title="DB Error...", message=f"Failed To Delete Project : {message}"
            )
            return None

        combo_data: qtg.Combo_Data = project_combo.value_get()

        if (
            combo_data.display == self._file_control.project_name
            and combo_data.index >= 0
        ):
            # A hack to get around the triggered indexchanged event in the combobox control which re-saves the
            # deleted project!
            self._save_existing_project = False
            project_combo.value_remove(combo_data.index)
            self._save_existing_project = True

        if self._db_settings.setting_exist(sys_consts.LATEST_PROJECT_DBK):
            if project_combo.count_items > 0:
                self._db_settings.setting_set(
                    sys_consts.LATEST_PROJECT_DBK, self._file_control.project_name
                )
            else:
                project_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=sys_consts.DEFAULT_PROJECT_NAME_DBK,
                        data="",
                        user_data=None,
                    )
                )

                dvd_layout_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK,
                        data="",
                        user_data=None,
                    )
                )

                Set_Shelved_DVD_Layout(
                    project_name=sys_consts.DEFAULT_PROJECT_NAME_DBK,
                    dvd_layout_name=sys_consts.DEFAULT_DVD_LAYOUT_NAME_DBK,
                    dvd_menu_layout=[],
                )
                self._db_settings.setting_set(
                    sys_consts.LATEST_PROJECT_DBK, sys_consts.DEFAULT_PROJECT_NAME_DBK
                )

                popups.PopMessage(
                    message="Added Default Project...",
                    text="A Default Project Has Been Created",
                ).show()

        return None

    def _processed_files_handler(self, video_file_input: list[Video_Data]):
        assert isinstance(video_file_input, list), f"{video_file_input=}. Must be list"
        assert all(
            isinstance(video_file, Video_Data) for video_file in video_file_input
        ), f"{video_file_input=}. Must be list of Video_Data"

        # Note when changing tabpages I call process_edited_video_files and that makes this call
        # redundant - worse it would fire twice!. TODO Consider This Unintended Consequence!
        # self._file_control.process_edited_video_files(video_file_input=video_file_input)
        self._control_tab.select_tab(tag_name="control_tab")
        self._control_tab.enable_set(tag="video_editor_tab", enable=False)

    def layout(self) -> qtg.FormContainer:
        """Returns the Black DVD Archiver application ui layout

        Returns:
            FormContainer: The application layout
        """

        if self._db_settings.setting_exist(sys_consts.ARCHIVE_DISK_SIZE_DBK):
            archive_disk_size = self._db_settings.setting_get(
                sys_consts.ARCHIVE_DISK_SIZE_DBK
            )
        else:
            archive_disk_size = sys_consts.DVD_ARCHIVE_SIZE
            self._db_settings.setting_set(
                sys_consts.ARCHIVE_DISK_SIZE_DBK, archive_disk_size
            )

        if self._db_settings.setting_exist(sys_consts.ARCHIVE_DISK_TRANSCODE_DBK):
            transcode_type = self._db_settings.setting_get(
                sys_consts.ARCHIVE_DISK_TRANSCODE_DBK
            )
        else:
            transcode_type = sys_consts.TRANSCODE_NONE
            transcode_type = self._db_settings.setting_set(
                sys_consts.ARCHIVE_DISK_TRANSCODE_DBK, transcode_type
            )

        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER_DBK)
        streaming_folder = self._db_settings.setting_get(
            sys_consts.STREAMING_FOLDER_DBK
        )
        dvd_build_folder = self._db_settings.setting_get(
            sys_consts.DVD_BUILD_FOLDER_DBK
        )

        if streaming_folder is None or streaming_folder.strip() == "":
            streaming_folder = file_utils.Special_Path(qtg.Special_Path.VIDEOS)
            self._db_settings.setting_set(
                sys_consts.STREAMING_FOLDER_DBK, streaming_folder
            )

        if archive_folder is None or archive_folder.strip() == "":
            archive_folder = file_utils.Special_Path(qtg.Special_Path.VIDEOS)
            self._db_settings.setting_set(sys_consts.ARCHIVE_FOLDER_DBK, archive_folder)

        if dvd_build_folder is None or dvd_build_folder.strip() == "":
            dvd_build_folder = file_utils.Special_Path(qtg.Special_Path.VIDEOS)
            self._db_settings.setting_set(
                sys_consts.DVD_BUILD_FOLDER_DBK, dvd_build_folder
            )

        project_name = self._db_settings.setting_get(sys_consts.LATEST_PROJECT_DBK)

        if project_name is None or not project_name.strip():
            project_name = sys_consts.DEFAULT_PROJECT_NAME_DBK

        Migrate_Shelves_To_DB()  # Basically, I am moving from shelves to SQL lite TODO Remove In Later Release
        project_items, layout_items, _ = Get_Project_Layout_Names(project_name)

        project_combo_items = [
            qtg.Combo_Item(
                display=item.replace("_", " "),
                data=item.replace("_", " "),
                icon=None,
                user_data=None,
            )
            for item in project_items
        ]

        layout_combo_items = [
            qtg.Combo_Item(
                display=item.replace("_", " "),
                data=item.replace("_", " "),
                icon=None,
                user_data=None,
            )
            for item in layout_items
        ]

        info_panel = qtg.HBoxContainer().add_row(
            qtg.Label(
                tag="project_duration",
                label="Duration (H:M:S)",
                width=8,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.Frame_Style.PANEL,
                    frame=qtg.Frame.SUNKEN,
                    line_width=2,
                ),
            ),
            qtg.Label(
                tag="avg_bitrate",
                label="Avg Bitrate",
                text=f"{sys_consts.AVERAGE_BITRATE / 1000:.1f} Mb/s",
                width=9,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.Frame_Style.PANEL,
                    frame=qtg.Frame.SUNKEN,
                    line_width=2,
                ),
            ),
            qtg.Label(
                tag="percent_of_dvd",
                label="DVD Used",
                width=3,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.Frame_Style.PANEL,
                    frame=qtg.Frame.SUNKEN,
                    line_width=2,
                ),
                buddy_control=qtg.Label(text="%", translate=False, width=1),
            ),
        )

        dvd_properties = qtg.FormContainer(
            tag="dvd_properties", text="DVD Properties"
        ).add_row(
            qtg.Label(
                tag="project_video_standard",
                label="Video Standard",
                buddy_control=info_panel,
                width=4,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.Frame_Style.PANEL,
                    frame=qtg.Frame.SUNKEN,
                    line_width=2,
                ),
            ),
            qtg.LineEdit(
                text=f"{sys_consts.SDELIM}{archive_folder}{sys_consts.SDELIM}",
                tag="archive_path",
                label="Archive Folder",
                width=66,
                tooltip="The Folder Where The Video Archive Is Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="archive_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip="Select The Video Archive Folder",
                ),
            ),
            qtg.LineEdit(
                text=f"{sys_consts.SDELIM}{streaming_folder}{sys_consts.SDELIM}",
                tag="streaming_path",
                label="Streaming Folder",
                width=66,
                tooltip="The Folder Where The Video Streaming Files Are Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="streaming_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip="Select The Video File Streaming Folder",
                ),
            ),
            qtg.LineEdit(
                text=f"{sys_consts.SDELIM}{dvd_build_folder}{sys_consts.SDELIM}",
                tag="dvd_path",
                label="DVD Build Folder",
                width=66,
                tooltip="The Folder Where The DVD Image Is Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="dvd_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip="Select The DVD Build Folder",
                ),
            ),
        )

        main_control_container = qtg.VBoxContainer(
            tag="control_buttons",
            align=qtg.Align.TOPLEFT,
            width=60,  # text="DVD Options"
        ).add_row(
            dvd_properties,
            qtg.Spacer(),
            self._file_control.layout(),
        )

        self._video_editor = Video_Editor(
            processed_files_callback=self._processed_files_handler
        )
        self._control_tab = qtg.Tab(height=47, width=146, callback=self.event_handler)
        self._control_tab.page_add(
            tag="control_tab", title="Files", control=main_control_container
        )
        self._control_tab.page_add(
            tag="video_editor_tab",
            title="Video Editor",
            control=self._video_editor.layout(),
            enabled=False,
        )

        about_text = (
            '<h2 style="text-align: center;"><strong><span style="color: #3366ff;"><a'
            " href='https://github.com/David-Worboys/Black-DVD-Archiver/'> The"
            f" {sys_consts.PROGRAM_NAME} -"
            f' {sys_consts.PROGRAM_VERSION}</span></strong></h2><p style="text-align:'
            ' center;font-size: 15px;">&#169;</a>'
            f" {sys_consts.COPYRIGHT_YEAR()} {sys_consts.AUTHOR}</p><p"
            ' style="text-align: center;"> <br/><img'
            f' src={file_utils.App_Path("logo.jpg")} width="400"  /></p> <p'
            ' style="text-align: center;"> < a  href="https://www.moyhups.vic.edu.au/"'
            " > Alumnus: Moyhu Primary School Et Al. < /a ></p>  </p> <p "
            f' style="text-align: center;">License: {sys_consts.LICENCE}</p>'
        )

        language_codes = self._control_tab.lang_tran_get.get_existing_language_codes()
        country_combo_items = [
            qtg.Combo_Item(
                display=f"{country.flag} {country.normal_name}",
                data=country.language,
                icon=None,
                user_data=None,
            )
            for country in Countries().get_countries
            if country.language != "en"
            and country.language in language_codes  # English is my base language!
        ]

        country_combo = qtg.ComboBox(
            # label="App Language",
            tag="countries",
            width=30,
            items=country_combo_items,
            translate=False,
            display_na=True,
            callback=self.event_handler,
            tooltip="Select Default Language By Country",
        )

        app_lang_container = qtg.VBoxContainer(
            tag="app_lang",
            text=(
                f"{sys_consts.SDELIM}{sys_consts.PROGRAM_NAME}{sys_consts.SDELIM} Language"
            ),
            align=qtg.Align.CENTER,
        ).add_row(
            # qtg.Spacer(),
            qtg.VBoxContainer().add_row(
                qtg.Label(text="Default Language"), country_combo
            ),
            qtg.Spacer(),
            qtg.Button(
                text="Language Translation",
                tag="langtran",
                callback=self.event_handler,
            ),
        )

        backup_disk_size_container = qtg.HBoxContainer(text="Archive Disks", width=20)

        backup_disk_size_container.add_row(
            qtg.VBoxContainer(text="Disk Size", width=20).add_row(
                qtg.RadioButton(
                    text="25 GB Blu-ray",
                    tag="backup_bluray",
                    callback=self.event_handler,
                    checked=(
                        True
                        if archive_disk_size == sys_consts.BLUERAY_ARCHIVE_SIZE
                        else False
                    ),
                ),
                qtg.RadioButton(
                    text="4  GB DVD",
                    tag="backup_dvd",
                    callback=self.event_handler,
                    checked=(
                        True
                        if archive_disk_size == sys_consts.DVD_ARCHIVE_SIZE
                        else False
                    ),
                ),
                qtg.Spacer(),  # Future radio buttons
                qtg.Spacer(),
            )
        )

        backup_disk_size_container.add_row(
            qtg.Spacer(width=1),
            qtg.VBoxContainer(text="Transcode Source", width=20).add_row(
                # qtg.Spacer(),
                qtg.RadioButton(
                    text="No Transcode",
                    tag="transcode_none",
                    tooltip=(
                        "Best Quality As Original Source Format Is Untouched. This Is"
                        " The Preferred Archiving Solution"
                    ),
                    callback=self.event_handler,
                    checked=(
                        True if transcode_type == sys_consts.TRANSCODE_NONE else False
                    ),
                ),
                qtg.RadioButton(
                    text="FFV1 (Archival)",
                    tag="transcode_archival",
                    tooltip=(
                        "Creates A FFV1 Preservation Master And A Streaming H264 Copy."
                        " This option uses a lot of disk space but is the best option"
                        " for long term storage as it uses leading archive institution"
                        " preferred formats (Library Of Congress etc.)"
                    ),
                    callback=self.event_handler,
                    checked=(
                        True
                        if transcode_type == sys_consts.TRANSCODE_FFV1ARCHIVAL
                        else False
                    ),
                ),
                qtg.RadioButton(
                    text="H264 (AVC)",
                    tag="transcode_h264",
                    tooltip=(
                        "Quality Lost As Source Video Is Compressed - Widely"
                        " Supported By DLNA Media Players like Serviio And Used by"
                        " Blu-ray disks"
                    ),
                    callback=self.event_handler,
                    checked=(
                        True if transcode_type == sys_consts.TRANSCODE_H264 else False
                    ),
                ),
                qtg.RadioButton(
                    text="H265 (HEVC)",
                    tag="transcode_h265",
                    tooltip=(
                        "Quality Lost As Source Video Is Compressed - Successor To H264"
                        " With Smaller File Size And Longer Encode Times"
                    ),
                    callback=self.event_handler,
                    checked=(
                        True if transcode_type == sys_consts.TRANSCODE_H265 else False
                    ),
                ),
                # qtg.Spacer(),
            ),
        )

        self._control_tab.page_add(
            tag="about_tab",
            title="About/System",
            control=qtg.VBoxContainer(align=qtg.Align.CENTER).add_row(
                qtg.Label(
                    width=135,
                    height=31,
                    editable=False,
                    text=about_text,
                    translate=False,
                ),
                # qtg.Spacer(),
                qtg.HBoxContainer(
                    text="System Settings",
                    margin_top=10,
                    margin_left=10,
                    margin_right=10,
                    margin_bottom=5,
                ).add_row(
                    backup_disk_size_container, qtg.Spacer(width=2), app_lang_container
                ),
            ),
            enabled=True,
        )

        buttons_container = qtg.HBoxContainer(
            tag="main_controls", margin_right=0
        ).add_row(
            qtg.Button(
                tag="make_dvd",
                text="Make A DVD",
                callback=self.event_handler,
                tooltip="Make A DVD",
                width=13,
                height=2,
                icon=file_utils.App_Path("compact-disc.svg"),
            ),
            qtg.Spacer(width=1),
            qtg.Label(
                text="Project:",
                buddy_control=qtg.HBoxContainer().add_row(
                    qtg.ComboBox(
                        tag="existing_projects",
                        width=30,
                        items=project_combo_items,
                        translate=False,
                        display_na=False,
                        callback=self.event_handler,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("x.svg"),
                        tag="delete_project",
                        callback=self.event_handler,
                        tooltip="Delete Selected Project",
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("file-edit.svg"),
                        tag="new_project",
                        callback=self.event_handler,
                        tooltip="Create A New Project",
                        width=2,
                        height=1,
                    ),
                ),
            ),
            qtg.Spacer(width=1),
            qtg.Label(
                text="DVD Layout:",
                buddy_control=qtg.HBoxContainer().add_row(
                    qtg.ComboBox(
                        tag="existing_layouts",
                        width=30,
                        items=layout_combo_items,
                        translate=False,
                        display_na=False,
                        callback=self.event_handler,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("x.svg"),
                        tag="delete_dvd_layout",
                        callback=self.event_handler,
                        tooltip="Delete Selected DVD Layout",
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        icon=file_utils.App_Path("file-edit.svg"),
                        tag="new_dvd_layout",
                        callback=self.event_handler,
                        tooltip="Create A New DVD Layout",
                        width=2,
                        height=1,
                    ),
                ),
            ),
            qtg.Spacer(width=4),
            qtg.Button(
                tag="exit_app",
                text="Exit",
                callback=self.event_handler,
                width=12,
                buddy_control=qtg.Button(
                    tag="task_manager",
                    callback=self.event_handler,
                    tooltip="Manage Running Tasks/Jobs",
                    icon=file_utils.App_Path("tasks.svg"),
                    width=1,
                ),
            ),
        )

        screen_container = qtg.FormContainer(
            tag="main",
            align=qtg.Align.RIGHT,
        ).add_row(self._control_tab, buttons_container)

        return screen_container

    def run(self) -> None:
        """Starts the application and gets the show on the road"""
        self._DVD_Arch_App.run(layout=self.layout(), windows_ui=False)


if __name__ == "__main__":
    DVD_Archiver().run()
