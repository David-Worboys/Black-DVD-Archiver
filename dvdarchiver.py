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

import dvdarch_utils
import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from archive_management import Archive_Manager
from configuration_classes import DVD_Menu_Settings, File_Def, Video_Data
from dvd import DVD, DVD_Config
from dvdarch_popups import Menu_Page_Title_Popup
from video_file_grid import Video_File_Grid

# fmt: on


class DVD_Archiver:
    """
    Class for archiving DVDs.
    """

    def __init__(self, args) -> None:
        self._DVD_Arch_App = qtg.QtPyApp(
            display_name=sys_consts.PROGRAM_NAME,
            callback=self.event_handler,
            height=600,
            icon=file_utils.App_Path("gitlogo.jpg"),
            width=800,
        )

        self._startup = True
        self._shutdown = False

        self._data_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

        self._file_control = Video_File_Grid()
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
                if not self._shutdown:
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
                        return 1
                    else:
                        self._shutdown = False
                        return -1
            case qtg.Sys_Events.APPPOSTINIT:
                self._startup = False

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "archive_folder_select":
                        self._archive_folder_select(event)
                    case "dvd_folder_select":
                        self._dvd_folder_select(event)
                    case "exit_app":
                        self._DVD_Arch_App.app_exit()
                    case "make_dvd":
                        self._make_dvd(event)

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
            title=f"Select A DVD Buld Folder....",
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

        if (
            self._file_control.dvd_percent_used + sys_consts.PERCENT_SAFTEY_BUFFER
            >= 100
        ):
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

        checked_items = file_grid.checkitems_get

        if not checked_items:
            popups.PopMessage(
                title="No Video Files Selected...",
                message="Please Select Video Files For The DVD!",
            ).show()
            return None

        dvd_title = Menu_Page_Title_Popup(
            title="DVD Menu Title",
            video_data_list=[file.user_data for file in checked_items],
        ).show()

        if dvd_title.strip() == "":
            popups.PopMessage(
                title="DVD Menu Title Not Entered...",
                message="A Menu Title Must Be Entered!",
            ).show()
            return None

        video_file_defs = []
        menu_labels = []
        dvd_menu_settings = DVD_Menu_Settings()

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            for checked_item in checked_items:
                checked_item: qtg.Grid_Item
                user_data: Video_Data = checked_item.user_data

                file_def = File_Def()
                file_def.path = user_data.video_folder
                file_def.file_name = (
                    f"{user_data.video_file}{user_data.video_extension}"
                )
                file_def.file_info = user_data.encoding_info
                file_def.video_file_settings = user_data.video_file_settings

                video_file_defs.append(file_def)

                if user_data.video_file_settings.button_title.strip() == "":
                    menu_labels.append(user_data.video_file)
                else:
                    menu_labels.append(user_data.video_file_settings.button_title)

        result = -1
        message = ""

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            if video_file_defs:
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

                dvd_config.input_videos = video_file_defs

                dvd_config.menu_labels = menu_labels

                dvd_config.menu_title = dvd_title.split("|")
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
                    result, message = self.archive_dvd_files(video_file_defs)

        if result == -1:
            popups.PopError(
                title="DVD Build Error...",
                message=f"Failed To Create A DVD!!\n{message}",
            ).show()

    def archive_dvd_files(self, video_file_defs: list[File_Def]) -> tuple[int, str]:
        """
        Archives the specified video files into a DVD image and saves the ISO image to the specified folder.

        Args:
            video_file_defs: A list of `File_Def` objects representing the video files to be archived.

        Returns:
            tuple[int, str]:
            - arg 1:1 Ok . -1 otherwise.
            - arg 2: "" if ok, otherwise an error message

        """
        assert isinstance(
            video_file_defs, list
        ), f"{video_file_defs} must be a list of File_Def instances"
        assert all(
            isinstance(fd, File_Def) for fd in video_file_defs
        ), f"All elements in {video_file_defs} must be instances of File_Def"

        file_handler = file_utils.File()
        dvd_image_folder = self._dvd.dvd_image_folder
        iso_folder = self._dvd.iso_folder
        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        source_files = []
        for file_def in video_file_defs:
            file_def: File_Def

            source_files.append(
                file_handler.file_join(file_def.path, file_def.file_name)
            )

        if source_files:
            archive_manager = Archive_Manager(archive_folder=archive_folder)

            result, message = archive_manager.archive_dvd_build(
                dvd_name=self._dvd.dvd_setup.serial_number,
                dvd_folder=dvd_image_folder,
                iso_folder=iso_folder,
                source_video_files=source_files,
            )

            if result == -1:
                return -1, message
        return 1, ""

    def layout(self) -> qtg.VBoxContainer:
        """Returns the Black DVD Archiver application ui layout

        Returns:
            VBoxContainer: The application layout
        """
        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)
        dvd_build_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if archive_folder is None or archive_folder.strip() == "":
            archive_folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
            self._db_settings.setting_set(sys_consts.ARCHIVE_FOLDER, archive_folder)

        if dvd_build_folder is None or dvd_build_folder.strip() == "":
            dvd_build_folder = file_utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
            self._db_settings.setting_set(sys_consts.DVD_BUILD_FOLDER, dvd_build_folder)

        color_list = [
            qtg.Combo_Item(display=color, data=color, icon=None, user_data=color)
            for color in dvdarch_utils.get_color_names()
        ]
        font_list = [
            qtg.Combo_Item(display=font[0], data=font[1], icon=None, user_data=font)
            for font in dvdarch_utils.get_fonts()
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

        archive_properties = qtg.FormContainer(
            tag="archive_properties", text="Archive Properties"
        ).add_row(
            qtg.LineEdit(
                text=f"{sys_consts.SDELIM}{archive_folder}{sys_consts.SDELIM}",
                action="edit_action",
                tag="archive_path",
                label=f"Archive Folder",
                width=66,
                tooltip=f"The Folder Where The DVD Archive Is Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="archive_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip=f"Select The  DVD Archive Folder",
                ),
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
                label=f"Archive Folder",
                width=66,
                tooltip=f"The Folder Where The DVD Archive Is Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="archive_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip=f"Select The  DVD Archive Folder",
                ),
            ),
            qtg.LineEdit(
                text=f"{sys_consts.SDELIM}{dvd_build_folder}{sys_consts.SDELIM}",
                action="edit_action",
                tag="dvd_path",
                label=f"DVD Build Folder",
                width=66,
                tooltip=f"The Folder Where The DVD Image Is Stored",
                editable=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="dvd_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip=f"Select The  DVD Build Folder",
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

        buttons_container = qtg.HBoxContainer(margin_right=9).add_row(
            qtg.Button(
                tag="make_dvd", text="Make DVD", callback=self.event_handler, width=9
            ),
            qtg.Spacer(width=97),
            qtg.Button(
                tag="exit_app", text="Exit", callback=self.event_handler, width=9
            ),
        )

        screen_container = qtg.VBoxContainer(
            tag="main",
            align=qtg.Align.RIGHT,  # width=80
        ).add_row(main_control_container, buttons_container)

        return screen_container

    def run(self) -> None:
        """Starts the application and gets the show on the road"""
        self._DVD_Arch_App.run(layout=self.layout(), windows_ui=False)


if __name__ == "__main__":
    DVD_Archiver(sys_consts.PROGRAM_NAME).run()
