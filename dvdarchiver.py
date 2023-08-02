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
# Tell Black to leave this block alone (realm of isort)
# fmt: off
import platformdirs

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from archive_management import Archive_Manager
from dvd import DVD, DVD_Config
from menu_page_title_popup import Menu_Page_Title_Popup
from sys_config import (DVD_Archiver_Base, DVD_Menu_Settings,
                        Get_DVD_Build_Folder, Get_Project_Layout_Names,
                        Set_Shelved_DVD_Layout, Video_Data)
from utils import Text_To_File_Name
from video_cutter import Video_Editor
from video_file_grid import Video_File_Grid

# fmt: on


class DVD_Archiver(DVD_Archiver_Base):
    """
    Class for archiving DVDs.

    """

    def __init__(self, program_name) -> None:
        """
        Sets up the instance of the class, and initializes all its attributes.

        Attributes:



        """
        super().__init__()

        self._DVD_Arch_App = qtg.QtPyApp(
            display_name=sys_consts.PROGRAM_NAME,
            callback=self.event_handler,
            height=900,
            icon=file_utils.App_Path("gitlogo.jpg"),
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

        if self._db_settings.setting_get("First_Run"):
            # Do stuff that the application only ever needs to do once on first
            # startup of new installation
            self._db_settings.setting_set("First_Run", False)

        self._menu_title_font_size = 24
        self._timestamp_font_point_size = 9
        self._default_font = sys_consts.DEFAULT_FONT

        self._dvd = DVD()  # Needs DB config to be completed before calling this
        self._video_editor: Video_Editor | None = None
        self._save_existing_project = True

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

        If the tables already exists, this method does nothing.  If an error occurs during table creation
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
        """Handles  application events

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
                            return 1
                        else:
                            self._shutdown = False
                            return -1
                    else:
                        self._shutdown = False
                        return -1
            case qtg.Sys_Events.APPPOSTINIT:
                pass  # Consumed in video_file_grid caught in custom/project_changed below
            case qtg.Sys_Events.CHANGED:  # Tab changed!
                match event.tag:
                    case "control_tab":
                        self._video_editor.video_pause()

                        if self._video_editor.video_file_input:
                            self._file_control.process_edited_video_files(
                                video_file_input=self._video_editor.video_file_input
                            )

                        self._tab_enable_handler(event=event, enable=True)
                    case "video_editor_tab":
                        self._tab_enable_handler(event=event, enable=False)

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "archive_folder_select":
                        self._archive_folder_select(event)
                    case "delete_dvd_layout":
                        self._delete_dvd_layout(event)
                    case "delete_project":
                        self._delete_project(event)
                    case "dvd_folder_select":
                        self._dvd_folder_select(event)
                    case "exit_app":
                        self._DVD_Arch_App.app_exit()
                    case "make_dvd":
                        self._make_dvd(event)
                    case "new_dvd_layout":
                        self._new_dvd_layout(event)
                    case "new_project":
                        self._new_project(event)
                    case "video_editor":  # Signal from file_grid
                        dvd_folder = Get_DVD_Build_Folder()

                        if dvd_folder.strip() != "":
                            video_data: list[Video_Data] = event.value
                            self._video_editor.set_source(
                                video_file_input=video_data, output_folder=dvd_folder
                            )
                            self._control_tab.select_tab(tag_name="video_editor_tab")
                            self._control_tab.enable_set(
                                tag="video_editor_tab", enable=True
                            )

            case qtg.Sys_Events.CUSTOM:
                match event.tag:
                    case "project_changed":
                        if event.widget_exist(
                            container_tag="main_controls", tag="existing_projects"
                        ):
                            project_combo: qtg.ComboBox = event.widget_get(
                                container_tag="main_controls", tag="existing_projects"
                            )

                            project_combo.select_text(
                                self._file_control.project_name, partial_match=False
                            )

                        self._control_tab.select_tab(tag_name="control_tab")
                        self._control_tab.enable_set(
                            tag="video_editor_tab", enable=False
                        )

                        self._startup = False

            case qtg.Sys_Events.INDEXCHANGED:
                match event.tag:
                    case "existing_projects":
                        self._project_combo_change(event)

        return None

    def _tab_enable_handler(self, event: qtg.Action, enable: bool):
        """Enables or disables the tab dependent controls

        Args:
            event (qtg.Action): The triggering event
            enable (bool): True - enables tab sensitive controls, False - disables tab sensitive controls
        """
        if event.widget_exist(
            container_tag="main_controls", tag="existing_projects"
        ):  # Buttons are buddies so must exist
            project_combo: qtg.ComboBox = event.widget_get(
                container_tag="main_controls", tag="existing_projects"
            )

            delete_button: qtg.Button = event.widget_get(
                container_tag="main_controls", tag="delete_project"
            )

            new_button: qtg.Button = event.widget_get(
                container_tag="main_controls", tag="new_project"
            )

            delete_button.enable_set(enable)
            new_button.enable_set(enable)

            project_combo.enable_set(enable)

        if event.widget_exist(container_tag="main_controls", tag="existing_layouts"):
            dvd_layout_combo: qtg.ComboBox = event.widget_get(
                container_tag="main_controls", tag="existing_layouts"
            )
            delete_button: qtg.Button = event.widget_get(
                container_tag="main_controls", tag="delete_dvd_layout"
            )

            new_button: qtg.Button = event.widget_get(
                container_tag="main_controls", tag="new_dvd_layout"
            )
            make_button: qtg.Button = event.widget_get(
                container_tag="main_controls", tag="make_dvd"
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
                project_combo: qtg.ComboBox = event.widget_get(
                    container_tag="main_controls",
                    tag="existing_projects",
                )
                layout_combo: qtg.ComboBox = event.widget_get(
                    container_tag="main_controls",
                    tag="existing_layouts",
                )

                layout_combo.clear()

                project_combo.select_text(
                    self._file_control.project_name, partial_match=False
                )

                _, layout_items = Get_Project_Layout_Names(
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

    def _archive_folder_select(self, event) -> None:
        """Select an archive folder and updates the settings in the database with the selected folder.

        Args:
            event (Event): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        if folder is None or folder.strip() == "":
            folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)

        folder = popups.PopFolderGet(
            title=f"Select An Archive Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()

        if folder.strip() != "":
            self._db_settings.setting_set(sys_consts.ARCHIVE_FOLDER, folder)

            event.value_set(
                container_tag="archive_properties",
                tag="archive_path",
                value=f"{sys_consts.SDELIM}{folder}{sys_consts.SDELIM}",
            )

    def _delete_dvd_layout(self, event: qtg.Action) -> None:
        """Deletes a dvd layout by removing the corresponding python shelf files

        Args:
            event (qtg.Action): Triggering event
        """

        file_handler = file_utils.File()

        dvd_layout_combo: qtg.ComboBox = event.widget_get(
            container_tag="main_controls", tag="existing_layouts"
        )

        layout_data = dvd_layout_combo.value_get()
        layout_filename = f"{Text_To_File_Name(self._file_control.project_name)}.{Text_To_File_Name(layout_data.display)}.dvdmenu"

        delete_file = False

        for extn in sys_consts.SHELVE_FILE_EXTNS:
            dvd_layout_path = file_handler.file_join(
                platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                layout_filename,
                extn,
            )

            if file_handler.file_exists(
                platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                layout_filename,
                extn,
            ):
                if extn == "dir":
                    if (
                        popups.PopYesNo(
                            title="Delete DVD Layout...",
                            message=(
                                "Delete DVD Layout"
                                f" {sys_consts.SDELIM}{layout_data.display}{sys_consts.SDELIM}?"
                            ),
                        ).show()
                        == "yes"
                    ):
                        delete_file = True
                    else:
                        return None

                if delete_file and file_handler.remove_file(dvd_layout_path) == 1:
                    dvd_layout_combo.value_remove(layout_data.index)

                    if dvd_layout_combo.count_items == 0:
                        dvd_layout_combo.value_set(
                            qtg.Combo_Data(
                                index=-1,
                                display=sys_consts.DEFAULT_DVD_LAYOUT_NAME,
                                data=f"{Text_To_File_Name(self._file_control.project_name)}.{Text_To_File_Name(sys_consts.DEFAULT_DVD_LAYOUT_NAME)}",
                                user_data=None,
                            )
                        )
                else:
                    popups.PopError(
                        title="Failed To Delete DVD Layout...",
                        message=(
                            "Failed To Delete DVD Layout"
                            f" {sys_consts.SDELIM}{layout_data.display}{sys_consts.SDELIM}!"
                        ),
                    ).show()
                    break

    def _dvd_folder_select(self, event) -> None:
        """Select a DVD build folder and updates the settings in the database with the selected folder.

        Args:
            event (Event): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if folder is None or folder.strip() == "":
            folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)

        folder = popups.PopFolderGet(
            title="Select A DVD Build Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()

        if folder.strip() != "":
            self._db_settings.setting_set(sys_consts.DVD_BUILD_FOLDER, folder)

            event.value_set(
                container_tag="dvd_properties",
                tag="dvd_path",
                value=f"{sys_consts.SDELIM}{folder}{sys_consts.SDELIM}",
            )

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

        dvd_layout_combo: qtg.ComboBox = event.widget_get(
            container_tag="main_controls", tag="existing_layouts"
        )

        dvd_layout_name = f"{Text_To_File_Name(self._file_control.project_name)}.{Text_To_File_Name(dvd_layout_combo.value_get().display)}"

        if self._file_control.dvd_percent_used + sys_consts.PERCENT_SAFTEY_BUFFER > 100:
            popups.PopError(
                title="DVD Build Error...",
                message="Selected Files Will Not Fit On A DVD!",
            ).show()
            return None

        dvd_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if dvd_folder is None or dvd_folder.strip() == "":
            popups.PopError(
                title="DVD Build Folder Error...",
                message="A DVD Build Folder Must Be Entered Before Making A DVD!",
            ).show()
            return None

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
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
                dvd_layout_name=dvd_layout_name,
            ).show()
            == "cancel"
        ):
            return None

        video_files: list[Video_Data] = []
        menu_labels: list[str] = []
        menu_title: list[str] = []
        dvd_menu_settings = DVD_Menu_Settings()

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            file_grid.checkitems_all(checked=False, col_tag="video_file")
            for menu_item in menu_layout:
                menu_title.append(menu_item[0])
                video_data_items: list[Video_Data] = menu_item[1]

                for video_item in video_data_items:
                    self._file_control.check_file(
                        file_grid=file_grid, vd_id=video_item.vd_id, checked=True
                    )
                    video_files.append(video_item)

                    if video_item.video_file_settings.button_title.strip():
                        menu_labels.append(video_item.video_file_settings.button_title)
                    else:
                        menu_labels.append(video_item.video_file)

        result = -1
        message = ""

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            if video_files:
                dvd_config = DVD_Config()

                # TODO: Move this to the GUI, currently the following is guaranteed as set in DB when created
                sql_result = self._app_db.sql_select(
                    col_str="code,description",
                    table_str=sys_consts.PRODUCT_LINE,
                    where_str="code='HV'",
                )

                if sql_result:  # Expect only one result
                    product_code = sql_result[0][0]
                    product_description = sql_result[0][1]

                    dvd_serial_number = self._dvd.generate_dvd_serial_number(
                        product_code=product_code,
                        product_description=product_description,
                    )
                    dvd_config.serial_number = dvd_serial_number

                dvd_config.input_videos = video_files

                dvd_config.menu_title = menu_title
                dvd_config.menu_background_color = (
                    dvd_menu_settings.menu_background_color
                )
                dvd_config.menu_font = dvd_menu_settings.menu_font
                dvd_config.menu_font_color = dvd_menu_settings.menu_font_color
                dvd_config.menu_font_point_size = dvd_menu_settings.menu_font_point_size
                dvd_config.button_background_color = (
                    dvd_menu_settings.button_background_color
                )
                dvd_config.button_font = dvd_menu_settings.button_font
                dvd_config.button_font_color = dvd_menu_settings.button_font_color
                dvd_config.button_font_point_size = (
                    dvd_menu_settings.button_font_point_size
                )
                dvd_config.button_background_transparency = (
                    dvd_menu_settings.button_background_transparency / 100
                )

                dvd_config.timestamp_font = self._default_font
                dvd_config.timestamp_font_point_size = self._timestamp_font_point_size

                dvd_config.video_standard = self._file_control.project_video_standard

                dvd_config.menu_buttons_across = dvd_menu_settings.buttons_across
                dvd_config.menu_buttons_per_page = dvd_menu_settings.buttons_per_page

                self._dvd.dvd_setup = dvd_config
                self._dvd.working_folder = dvd_folder
                self._dvd.application_db = self._app_db

                result, message = self._dvd.build()

                if result == 1:
                    result, message = self.archive_dvd_files(menu_layout)

        if result == -1:
            popups.PopError(
                title="DVD Build Error...",
                message=(
                    "Failed To Create A"
                    f" DVD!!\n{sys_consts.SDELIM}{message}{sys_consts.SDELIM}"
                ),
            ).show()

    def _new_dvd_layout(self, event: qtg.Action) -> None:
        """
        Creates A New DVD layout.

        Args:
            event (qtg.Action): The triggering event.
        """
        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        dvd_layout_combo: qtg.ComboBox = event.widget_get(
            container_tag="main_controls", tag="existing_layouts"
        )

        layout_name = popups.PopTextGet(
            title="Enter DVD Layout Name...",
            label="DVD Layout Name:",
            label_above=True,
        ).show()

        if layout_name.strip():
            if dvd_layout_combo.select_text(layout_name, partial_match=False) >= 0:
                popups.PopMessage(
                    title="Invalid DVD Layout Name",
                    message="A DVD Layout Wih That Name Already Exists!",
                ).show()
            else:
                dvd_layout_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=Text_To_File_Name(layout_name).replace("_", " "),
                        data=Text_To_File_Name(layout_name),
                        user_data=None,
                    )
                )

                Set_Shelved_DVD_Layout(
                    f"{self._file_control.project_name}.{layout_name}", []
                )

                dvd_layout_combo.select_text(layout_name, partial_match=False)
                file_grid.checkitems_all(checked=False, col_tag="video_file")
                self._file_control.set_project_standard_duration(event)

    def _new_project(self, event: qtg.Action):
        """Create a new project
        Args:
            event:qtg.Action: The triggering event
        """

        project_name = popups.PopTextGet(
            title="Enter Project Name",
            label="Project Name:",
            label_above=True,
        ).show()

        if project_name.strip():
            project_combo: qtg.ComboBox = event.widget_get(
                container_tag="main_controls", tag="existing_projects"
            )

            if project_combo.select_text(project_name, partial_match=False) >= 0:
                popups.PopMessage(
                    title="Invalid Project Name",
                    message="A Project With That Name Already Exists!",
                ).show()
            else:
                project_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=Text_To_File_Name(project_name).replace("_", " "),
                        data=Text_To_File_Name(project_name),
                        user_data=None,
                    )
                )
                file_grid: qtg.Grid = event.widget_get(
                    container_tag="video_file_controls", tag="video_input_files"
                )
                file_grid.clear()

                Set_Shelved_DVD_Layout(
                    f"{Text_To_File_Name(project_name)}.{sys_consts.DEFAULT_DVD_LAYOUT_NAME}",
                    [],
                )

    def _delete_project(self, event: qtg.Action) -> None:
        """Deletes a project by removing the corresponding python shelf files

        Args:
            event (qtg.Action): Triggering event
        """

        file_handler = file_utils.File()

        project_combo: qtg.ComboBox = event.widget_get(
            container_tag="main_controls", tag="existing_projects"
        )

        _, dvd_layouts = Get_Project_Layout_Names(self._file_control.project_name)

        if (
            popups.PopYesNo(
                title="Delete Project...",
                message=(
                    "Delete Project"
                    f" {sys_consts.SDELIM}{self._file_control.project_name}{sys_consts.SDELIM}?"
                    " \nWarning All Project Data Except Source Video Files Will Be"
                    " Lost!"
                ),
            ).show()
            == "no"
        ):
            return None

        for extn in sys_consts.SHELVE_FILE_EXTNS:
            project_path = file_handler.file_join(
                platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                f"{Text_To_File_Name(self._file_control.project_name)}.project_files",
                extn,
            )

            if file_handler.path_exists(project_path):
                if file_handler.remove_file(project_path) == -1:
                    popups.PopError(
                        title="Failed To Delete Project...",
                        message=(
                            "Failed To Delete Project"
                            f" {sys_consts.SDELIM}{self._file_control.project_name}{sys_consts.SDELIM}!"
                        ),
                    ).show()
                    return None

            for dvd_layout in dvd_layouts:
                dvd_layout_name = f"{self._file_control.project_name}.{dvd_layout}"

                layout_path = file_handler.file_join(
                    platformdirs.user_data_dir(sys_consts.PROGRAM_NAME),
                    f"{Text_To_File_Name(dvd_layout_name)}.dvdmenu",
                    extn,
                )

                if file_handler.path_exists(layout_path):
                    if file_handler.remove_file(layout_path) == -1:
                        popups.PopError(
                            title="Failed To Delete Project DVD Layouts...",
                            message=(
                                "Failed To Delete Project DVD Layouts"
                                f" {sys_consts.SDELIM}{self._file_control.project_name}{sys_consts.SDELIM}!"
                            ),
                        ).show()

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

        if self._db_settings.setting_exist("latest_project"):
            if project_combo.count_items > 0:
                self._db_settings.setting_set(
                    "latest_project", self._file_control.project_name
                )
            else:
                project_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=sys_consts.DEFAULT_PROJECT_NAME,
                        data="",
                        user_data=None,
                    )
                )

                Set_Shelved_DVD_Layout(
                    f"{sys_consts.DEFAULT_PROJECT_NAME}.{sys_consts.DEFAULT_DVD_LAYOUT_NAME}",
                    [],
                )
                self._db_settings.setting_set(
                    "latest_project", sys_consts.DEFAULT_PROJECT_NAME
                )

                popups.PopMessage(
                    message="Added Default Project...",
                    text="A Default Project Has Been Created",
                ).show()
        return None

    def archive_dvd_files(
        self, menu_layout: list[tuple[str, list[Video_Data]]]
    ) -> tuple[int, str]:
        """
        Archives the specified video files into a DVD image and saves the ISO image to the specified folder.

        Args:
            menu_layout (list[tuple[str, list[Video_Data]]]): A list of tuples (menu title,Video_Data)
            representing the video files to be archived.

        Returns:
            tuple[int, str]:
            - arg 1:1 Ok . -1 otherwise.
            - arg 2: "" if ok, otherwise an error message

        """
        assert isinstance(
            menu_layout, list
        ), f"{menu_layout=} must be a list of tuples of str,Video_Data"

        for menu in menu_layout:
            assert isinstance(menu[0], str), f"{menu[0]=} must be a str"
            assert isinstance(menu[1], list), f"{menu[1]=} must be a list"
            assert all(
                isinstance(fd, Video_Data) for fd in menu[1]
            ), f"All elements in {menu[1]=} must be Video_Data"

        dvd_image_folder = self._dvd.dvd_image_folder
        iso_folder = self._dvd.iso_folder
        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        if menu_layout:
            archive_manager = Archive_Manager(archive_folder=archive_folder)

            result, message = archive_manager.archive_dvd_build(
                dvd_name=(
                    f"{self._dvd.dvd_setup.serial_number} -"
                    f" {self._file_control.project_name}"
                ),
                dvd_folder=dvd_image_folder,
                iso_folder=iso_folder,
                menu_layout=menu_layout,
            )

            if result == -1:
                return -1, message
        return 1, ""

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
        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)
        dvd_build_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if archive_folder is None or archive_folder.strip() == "":
            archive_folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
            self._db_settings.setting_set(sys_consts.ARCHIVE_FOLDER, archive_folder)

        if dvd_build_folder is None or dvd_build_folder.strip() == "":
            dvd_build_folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
            self._db_settings.setting_set(sys_consts.DVD_BUILD_FOLDER, dvd_build_folder)

        project_name = self._db_settings.setting_get("latest_project")

        if project_name is None or not project_name.strip():
            project_name = sys_consts.DEFAULT_PROJECT_NAME

        project_items, layout_items = Get_Project_Layout_Names(project_name)

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
                action="edit_action",
                tag="archive_path",
                label="Archive Folder",
                width=66,
                tooltip="The Folder Where The DVD Archive Is Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="archive_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip="Select The  DVD Archive Folder",
                ),
            ),
            qtg.LineEdit(
                text=f"{sys_consts.SDELIM}{dvd_build_folder}{sys_consts.SDELIM}",
                action="edit_action",
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
                    tooltip="Select The  DVD Build Folder",
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
        self._control_tab = qtg.Tab(height=47, width=143, callback=self.event_handler)
        self._control_tab.page_add(
            tag="control_tab", title="Files", control=main_control_container
        )
        self._control_tab.page_add(
            tag="video_editor_tab",
            title="Video Editor",
            control=self._video_editor.layout(),
            enabled=False,
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
            qtg.Spacer(width=3),
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
            qtg.Spacer(width=1),
            qtg.Button(
                tag="exit_app", text="Exit", callback=self.event_handler, width=13
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
    # import faulthandler

    # faulthandler.enable()
    # faulthandler.dump_traceback_later(timeout=360, repeat=True)

    DVD_Archiver(sys_consts.PROGRAM_NAME).run()
