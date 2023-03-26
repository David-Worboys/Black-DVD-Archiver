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
import datetime
import os

import platformdirs

import dvdarch_utils
import qtgui as qtg
import sqldb
import sys_consts
import utils
from archive_management import Archive_Manager
from dvd import DVD, DVD_Config, File_Def
from video_cutter import Video_Cutter_Popup
from video_file_picker import Video_File_Picker_Popup

# fmt: on

PERCENT_SAFTEY_BUFFER = 1  # Used to limit DVD size so that it never exceeds 100%


class DVD_Archiver:
    """
    Class for archiving DVDs.
    """

    def __init__(self, args):
        self._DVD_Arch_App = qtg.QtPyApp(
            display_name=sys_consts.PROGRAM_NAME,
            callback=self.event_handler,
            height=768,
            # width=1024,
            width=800,
        )

        self._startup = True

        self._data_path: str = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

        self._file_control = file_control()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        # A problem in the next 3 lines can shutdown startup as daabase initialization failed
        if self._db_settings.error_code == -1:
            raise RuntimeError(
                f"Failed To Start {sys_consts.PROGRAM_NAME} - {self._db_settings.error_message}"
            )
        self._app_db = self.db_init()
        self._db_tables_create()

        if self._db_settings.setting_get("First_Run"):
            # Do stuff that the application only ever needs to do once on first
            # startup of new installation
            self._db_settings.setting_set("First_Run", False)

        self._menu_title_font_size = 24
        self._timestamp_font_point_size = 9
        self._default_font = "IBMPlexMono-SemiBold.ttf"  # Packaged with DVD Archiver

        self._dvd = DVD()  # Needs DB config to be completed before calling this

        if not self._db_settings.setting_exist("menu_background_color"):
            self._db_settings.setting_set("menu_background_color", "blue")

        if not self._db_settings.setting_exist("menu_font_color"):
            self._db_settings.setting_set("menu_font_color", "yellow")

        if not self._db_settings.setting_exist("menu_font_point_size"):
            self._db_settings.setting_set("menu_font_point_size", 24)

        if not self._db_settings.setting_exist("menu_font"):
            self._db_settings.setting_set("menu_font", self._default_font)

    def db_init(self) -> sqldb.SQLDB:
        """
        Initializes the application database and returns a SQLDB object.

        Returns:
            sqldb.SQLDB: A SQLDB object representing the application database.

        Raises:
            RuntimeError: If the application data folder cannot be created or the database cannot be initialized.
        """
        file_handler = utils.File()

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

    def _db_tables_create(self):
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
                    f"Failed To Create {sys_consts.PROGRAM_NAME} Database - {error_status.message}"
                )
            # Load a default product line
            self._app_db.sql_update(
                col_dict={"code": "HV", "description": "Home Video"},
                table_str=sys_consts.PRODUCT_LINE,
            )

            error_status = self._app_db.get_error_status()
            if error_status.code == -1:
                raise RuntimeError(
                    f"Failed To Initialise {sys_consts.PROGRAM_NAME} Database - {error_status.message}"
                )

    def event_handler(self, event: qtg.Action):
        """Handles  application events

        Args:
            event (Action): The triggering event
        """
        match event.event:
            case qtg.Sys_Events.APPINIT:
                pass
            case qtg.Sys_Events.APPCLOSED:
                if (
                    qtg.PopYesNo(
                        title="Exit Application...",
                        message=f"Exit The {sys_consts.SDELIM}{sys_consts.PROGRAM_NAME}?{sys_consts.SDELIM}",
                    ).show()
                    == "yes"
                ):
                    print(f"{sys_consts.PROGRAM_NAME} App Closed")
                    return 1
                else:
                    return -1
            case qtg.Sys_Events.APPPOSTINIT:
                file_handler = utils.File()

                menu_background_color: str = self._db_settings.setting_get(
                    "menu_background_color"
                )
                menu_font_color: str = self._db_settings.setting_get("menu_font_color")
                menu_font_point_size = self._db_settings.setting_get(
                    "menu_font_point_size"
                )
                menu_font = self._db_settings.setting_get("menu_font")

                font_name = file_handler.split_head_tail(menu_font)[1]

                if not font_name:
                    font_name = self._default_font

                menu_color_combo: qtg.ComboBox = event.widget_get(
                    container_tag="menu_properties", tag="menu_color"
                )

                text_color_combo: qtg.ComboBox = event.widget_get(
                    container_tag="menu_properties", tag="text_color"
                )

                font_combo: qtg.ComboBox = event.widget_get(
                    container_tag="menu_properties", tag="title_font"
                )

                menu_color_combo.select_text(menu_background_color, partial_match=False)
                text_color_combo.select_text(menu_font_color, partial_match=False)
                font_combo.select_text(font_name, partial_match=False)

                # Hotwire event to reuse
                event.container_tag = "menu_properties"
                event.tag = "title_font"
                event.value = menu_font
                self._menu_color_combo_change(event)

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
            case qtg.Sys_Events.INDEXCHANGED:
                match event.tag:
                    case "menu_color":
                        if not self._startup and event.widget_exist(
                            container_tag=event.container_tag, tag=event.tag
                        ):
                            self._db_settings.setting_set(
                                "menu_background_color", event.value.data
                            )
                            self._menu_color_combo_change(event)

                    case "text_color":
                        if not self._startup and event.widget_exist(
                            container_tag=event.container_tag, tag=event.tag
                        ):
                            self._db_settings.setting_set(
                                "menu_font_color", event.value.data
                            )
                            self._menu_color_combo_change(event)

                    case "title_font":
                        if not self._startup and event.widget_exist(
                            container_tag=event.container_tag, tag=event.tag
                        ):
                            self._db_settings.setting_set("menu_font", event.value.data)
                            self._title_font_combo_change(event)

    def _archive_folder_select(self, event):
        """Select an archive folder and updates the settings in the database with the selected folder.

        Args:
            event (Event): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        if folder is None or folder.strip() == "":
            folder = utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)

        folder = qtg.PopFolderGet(
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

    def _dvd_folder_select(self, event):
        """Select a DVD build folder and updates the settings in the database with the selected folder.

        Args:
            event (Event): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        """
        folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if folder is None or folder.strip() == "":
            folder = utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)

        folder = qtg.PopFolderGet(
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

    def _make_dvd(self, event: qtg.Action):
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

        if self._file_control.dvd_percent_used + PERCENT_SAFTEY_BUFFER >= 100:
            qtg.PopError(
                title="DVD Build Error...",
                message="Selected Files Will Not Fit On A DVD!",
            ).show()
            return None

        menu_color_combo: qtg.ComboBox = event.widget_get(
            container_tag="menu_properties", tag="menu_color"
        )

        text_color_combo: qtg.ComboBox = event.widget_get(
            container_tag="menu_properties", tag="text_color"
        )

        font_combo: qtg.ComboBox = event.widget_get(
            container_tag="menu_properties", tag="title_font"
        )

        dvd_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if dvd_folder is None or dvd_folder.strip() == "":
            qtg.PopError(
                title="DVD Build Folder Error...",
                message="A DVD Build Folder Must Be Entered Before Making A DVD!",
            ).show()
            return None

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        video_file_defs = []
        menu_labels = []

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            for row_index in range(file_grid.row_count):
                file = file_grid.value_get(row_index, col=0)
                folder = file_grid.userdata_get(row_index, col=0)
                video_properties = file_grid.userdata_get(row_index, col=1)

                file_def = File_Def()
                file_def.path = folder
                file_def.file_name = file
                file_def._file_info = video_properties

                video_file_defs.append(file_def)

                # menu_image_files.append(image_file)
                menu_labels.append(".".join(file.split(".")[0:-1]))

        result = -1
        message = ""

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            if video_file_defs:
                dvd_config = DVD_Config()

                dvd_title: str = event.value_get(
                    container_tag="menu_properties", tag="menu_title"
                )

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

                dvd_config.menu_title = dvd_title
                dvd_config.menu_background_color = menu_color_combo.value_get().data
                dvd_config.menu_font = font_combo.value_get().data
                dvd_config.menu_font_color = text_color_combo.value_get().data
                dvd_config.menu_font_point_size = self._menu_title_font_size

                dvd_config.timestamp_font = self._default_font
                dvd_config.timestamp_font_point_size = self._timestamp_font_point_size

                dvd_config.video_standard = self._file_control.project_video_standard

                self._dvd.dvd_setup = dvd_config
                self._dvd.working_folder = dvd_folder
                self._dvd.application_db = self._app_db
                            
                result, message = self._dvd.build()

                if result == 1:
                    result, message = self.archive_dvd_files(video_file_defs)

        if result == -1:
            qtg.PopError(
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

        file_handler = utils.File()
        dvd_image_folder = self._dvd.dvd_image_folder
        iso_folder = self._dvd.iso_folder
        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)

        source_files = []
        for file_def in video_file_defs:
            file_def: File_Def
            source_files.append(
                f"{file_def.path}{file_handler.ossep}{file_def.file_name}"
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
                return -11, message
        return 1, ""

    def _menu_color_combo_change(self, event: qtg.Action):
        """Changes the menu colour of the colour patch when the menu colour is changed

        Args:
            event (qtg.Action): Triggering event
        """
        if event.widget_exist(container_tag=event.container_tag, tag="title_font"):
            title_combo: qtg.ComboBox = event.widget_get(
                container_tag=event.container_tag, tag="title_font"
            )
            # Hotwire event to reuse
            event.tag = "title_font"
            event.value = title_combo.value_get()

            self._title_font_combo_change(event)

        return None

    def _title_font_combo_change(self, event: qtg.Action):
        """Changes the font of the colour patch of the title font text when the font
        selection changes

        Args:
            event (Action): _description_
        """
        combo_data: qtg.Combo_Data = event.value

        menu_color_combo: qtg.ComboBox = event.widget_get(
            container_tag=event.container_tag, tag="menu_color"
        )

        text_color_combo: qtg.ComboBox = event.widget_get(
            container_tag=event.container_tag, tag="text_color"
        )

        if event.widget_exist(container_tag="menu_properties", tag="title_example"):
            image: qtg.Image = event.widget_get(
                container_tag="menu_properties", tag="title_example"
            )

            char_pixel_size = qtg.g_application.char_pixel_size(
                font_path=combo_data.data
            )

            pointsize, png_bytes = dvdarch_utils.get_font_example(
                font_file=combo_data.data,
                # pointsize=50,
                text=" Title Test ",
                text_color=text_color_combo.value_get().data,
                background_color=menu_color_combo.value_get().data,
                width=image.width * char_pixel_size.width,
                height=image.height * char_pixel_size.height,
                # height=144,
            )

            if png_bytes:
                self._menu_title_font_size = pointsize
                image.image_set(png_bytes)
            else:
                qtg.PopError(
                    title="Font Can Not Be Rendered...",
                    message=f"THe font {sys_consts.SDELIM} {combo_data.display} {sys_consts.SDELIM} Can Not Be Rendered!",
                ).show()

    def layout(self) -> qtg.VBoxContainer:
        """Returns the Black DVD Archiver application ui layout

        Returns:
            VBoxContainer: The application layout
        """
        archive_folder = self._db_settings.setting_get(sys_consts.ARCHIVE_FOLDER)
        dvd_build_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if archive_folder is None or archive_folder.strip() == "":
            archive_folder = utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
            self._db_settings.setting_set(sys_consts.ARCHIVE_FOLDER, archive_folder)

        if dvd_build_folder is None or dvd_build_folder.strip() == "":
            dvd_build_folder = utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
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
                buddy_control=qtg.Label(text="%", translate=False, width=6),
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

        menu_config = qtg.HBoxContainer().add_row(
            qtg.ComboBox(
                tag="menu_color",
                label="Color",
                width=15,
                callback=self.event_handler,
                items=color_list,
                display_na=False,
                translate=False,
            ),
            qtg.ComboBox(
                tag="text_color",
                label="Text Color",
                width=15,
                callback=self.event_handler,
                items=color_list,
                display_na=False,
                translate=False,
            ),
            qtg.ComboBox(
                tag="title_font",
                label="Title Font",
                width=30,
                callback=self.event_handler,
                items=font_list,
                display_na=False,
                translate=False,
            ),
        )

        dvd_menu_properties = qtg.VBoxContainer(
            tag="menu_properties", text="Menu Properties"
        ).add_row(
            qtg.LineEdit(
                tag="menu_title",
                label="Title",
                width=30,
                char_length=80,
            ),
            menu_config,
            qtg.HBoxContainer(text="Menu Example").add_row(
                qtg.Image(
                    tag="title_example",
                    height=4,
                    width=20,
                )
            ),
        )

        main_control_container = qtg.VBoxContainer(
            tag="control_buttons",
            align=qtg.Align.TOPLEFT,
            width=60,  # text="DVD Options"
        ).add_row(
            archive_properties,
            qtg.Spacer(),
            dvd_properties,
            qtg.Spacer(),
            dvd_menu_properties,
            self._file_control.layout(),
        )

        buttons_container = qtg.HBoxContainer().add_row(
            qtg.Button(
                tag="make_dvd", text="Make DVD", callback=self.event_handler, width=9
            ),
            qtg.Spacer(width=85),
            qtg.Button(
                tag="exit_app", text="Exit", callback=self.event_handler, width=9
            ),
        )

        screen_container = qtg.FormContainer(
            tag="main",
            align=qtg.Align.RIGHT,  # width=80
        ).add_row(main_control_container, qtg.Spacer(), buttons_container)

        return screen_container

    def run(self) -> None:
        """Starts the application and gets the show on the road"""
        self._DVD_Arch_App.run(layout=self.layout(), windows_ui=False)


class file_control:
    """This class implements the file handling of the Black DVD Archiver ui"""

    def __init__(self):
        self.project_video_standard = ""  # PAL or NTSC
        self.project_duration = ""
        self.dvd_percent_used = 0  # TODO Make A selection of DVD5 and DVD9
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
        self.common_words = []

    def grid_events(self, event: qtg.Action):
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
                # When the user clicks on a row in the grid, toggle the switch in that row
                file_grid: qtg.Grid = event.widget_get(
                    container_tag="video_file_controls", tag="video_input_files"
                )

                if file_grid.checkitemrow_get(event.value.row, col=0):
                    file_grid.checkitemrow_set(
                        row=event.value.row, col=0, checked=False
                    )
                else:
                    file_grid.checkitemrow_set(row=event.value.row, col=0, checked=True)

    def _edit_video(self, event: qtg.Action):
        """
        Edits a video file.

        Args:
            event (qtg.Action): The event that triggered the video edit.
        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_handler = utils.File()
        dvd_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if dvd_folder is None or dvd_folder.strip() == "":
            qtg.PopError(
                title="DVD Build Folder Error...",
                message="A DVD Build Folder Must Be Entered Before Making A Video Edit!",
            ).show()
            return None

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls", tag="video_input_files"
        )

        tool_button: qtg.Button = event.widget_get(
            container_tag=event.container_tag, tag=event.tag
        )
        user_data = tool_button.userdata_get()

        source_folder = user_data[0]
        source_file = user_data[1]
        encoding_info = user_data[2]

        file = f"{source_folder}{os.path.sep}{source_file}"

        result = Video_Cutter_Popup(
            title="Video File Cutter/Setings",
            aspect_ratio=encoding_info["video_dar"][1],
            input_file=file,
            output_folder=dvd_folder,
            encoding_info=encoding_info,
        ).show()

        # All this hairy string stuff to get the file properties is becaue I can only return a str from the
        # Video Cutter popup
        if result:
            if result.endswith("T"):  # Trimmed File
                # Pretty basic, just a source and a trimmed file
                input_file, trimmed_file, _ = result.split(",")
                source_folder, source_file, _ = file_handler.split_file_path(input_file)

                self._processed_trimmed(
                    file_handler, file_grid, source_folder, source_file, trimmed_file
                )
            else:  # Assemble Multiple Files
                # Splits out the str rows of of the file propertiees; delim '|'
                edit_file_list = result.split("|")
                file_str = ""

                # Have to build up a new string containig the file info required to load the file list display
                for row, edit_file in enumerate(edit_file_list):
                    # Split the file property str into the appropriate vars; delim ','
                    (
                        input_file,
                        user_entered_file_name,
                        orig_rename_file_path,
                        user_rename_file_path,
                        operation,
                    ) = edit_file.split(",")

                    # Split the file paths into the components needed
                    (
                        source_folder,
                        source_file,
                        source_extension,
                    ) = file_handler.split_file_path(input_file)

                    rename_path, _, rename_extension = file_handler.split_file_path(
                        user_rename_file_path
                    )

                    # Assemble the source file name
                    source_file = f"{source_file}{source_extension}"

                    # This is the target str format for loading the file list display
                    file_str += f"{row},-,{user_entered_file_name}{rename_extension},{rename_path}|"

                if file_str:  # Assemble Operation
                    # Strip the trailing "|" delimiter from the file_str
                    file_str = file_str[:-1]

                    self._processed_assembled(
                        file_handler, file_grid, source_folder, source_file, file_str
                    )

    def _processed_assembled(
        self,
        file_handler: utils.File,
        file_grid: qtg.Grid,
        source_folder: str,
        source_file: str,
        file_str: str,
    ):
        """Delete the source file from the file grid and insert its children assembled files.

        Args:
            file_handler (utils.File): An instance of the `File` class.
            file_grid (qtg.Grid): An instance of the `Grid` class.
            source_folder (str): A string representing the source folder of the file to be deleted.
            source_file (str): A string representing the name of the file to be deleted.
            file_str (str): A string representing the contents of the files to be processed.
                File Delim '|', Prop delim ','

        """
        assert isinstance(
            file_handler, qtg.File
        ), f"{file_handler=}/ Must be a File instance "
        assert isinstance(file_grid, qtg.Grid), f"{file_grid}. Must be a Grid instance"
        assert (
            isinstance(source_folder, str) and source_folder.strip() != ""
        ), f"{source_folder=}. Must be a non-empty str"
        assert (
            isinstance(source_file, str) and source_file.strip() != ""
        ), f"{source_file=}. Must be a non-empty str"
        assert (
            isinstance(file_str, str) and file_str.strip() != ""
        ), f"{file_str=}. Must be a non-empty str"

        # Delete Source File as I will be replacing with the aseembled file list
        for row in range(0, file_grid.row_count):
            # File data we want is on the button object
            row_tool_button: qtg.Button = file_grid.row_widget_get(
                row=row, col=6, tag="grid_button"
            )

            user_data = row_tool_button.userdata_get()

            if (
                user_data is not None
                and isinstance(user_data, tuple)
                and len(user_data) == 3
            ):
                row_file_folder = user_data[0]
                row_file_name = user_data[1]
                row_encoding_info = user_data[2]

                if source_folder == row_file_folder and source_file == row_file_name:
                    file_grid.row_delete(row)

        # Insert Children Assembled Files
        self._insert_files_into_grid(file_handler, file_grid, file_str)

    def _processed_trimmed(
        self,
        file_handler: utils.File,
        file_grid: qtg.Grid,
        source_folder: str,
        source_file: str,
        trimmed_file: str,
    ):
        """
        Updates the given file_grid with the trimmed_file, if the source_file matches the specified source_folder.

        Args:
            file_handler (utils.File): The file handler to use.
            file_grid (qtg.Grid): The grid to update.
            source_folder (str): The folder to search for the source_file.
            source_file (str): The name of the source file to match.
            trimmed_file (str): The trimmed file to update the grid with.

        """
        assert isinstance(
            file_handler, utils.File
        ), f"{file_handler=}. Must be utils.File"
        assert isinstance(file_grid, qtg.Grid), f"{file_grid=}. Must br qtg.Grid,"
        assert (
            isinstance(source_folder, str) and source_folder.strip() != ""
        ), f"{source_folder=}. Must be a non-empty str"
        assert (
            isinstance(source_file, str) and source_file.strip() != ""
        ), f"{source_file=}. Must be a non-empty str"
        assert (
            isinstance(trimmed_file, str) and trimmed_file.strip() != ""
        ), f"{trimmed_file=}. Must be a non-empty str."

        trimmed_path, trimmed_name, _ = file_handler.split_file_path(trimmed_file)

        # Scan looking for source of trimmed file
        for row in range(file_grid.row_count):
            # Data we want is on the button object
            row_tool_button: qtg.Button = file_grid.row_widget_get(
                row=row, col=6, tag="grid_button"
            )

            user_data = row_tool_button.userdata_get()

            if (
                user_data is not None
                and isinstance(user_data, tuple)
                and len(user_data) == 3
            ):
                row_file_folder, row_file_name, row_encoding_info = user_data

                if row_file_folder == source_folder and row_file_name == source_file:
                    file_grid.value_set(
                        row=row,
                        col=0,
                        value=trimmed_file,
                        user_data=row_file_folder,
                    )

                    file_grid.value_set(
                        row=row,
                        col=6,
                        value=trimmed_file,
                        user_data=(
                            trimmed_path,
                            trimmed_name,
                            row_encoding_info,
                        ),
                    )

                    break  # Only one trimmed file

    def event_handler(self, event: qtg.Action):
        """Handles  application events

        Args:
            event (Action): The triggering event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        match event.event:
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
                    case "select_files":
                        folder = self._db_settings.setting_get(
                            sys_consts.DVD_BUILD_FOLDER
                        )

                        if folder is None or folder.strip() == "":
                            qtg.PopError(
                                title="DVD Build Folder Error...",
                                message="A DVD Build Folder Must Be Entered Before Video Folders Are Selected!",
                            ).show()
                            return None

                        self.load_video_input_files(event)
                    case "remove_files":
                        file_grid: qtg.Grid = event.widget_get(
                            container_tag="video_file_controls",
                            tag="video_input_files",
                        )

                        if (
                            file_grid.row_count > 0
                            and file_grid.checkitems_get
                            and qtg.PopYesNo(
                                title="Remove Checied...",
                                message="Remove The Checked Files?",
                            ).show()
                            == "yes"
                        ):
                            for item in reversed(file_grid.checkitems_get):
                                file_grid.row_delete(item[0])

                        self._set_project_standard_duration(event)

    def load_video_input_files(self, event: qtg.Action):
        """Loads video files into the video input grid

        Args:
            event (qtg.Acton) : Calling event

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        selected_files = Video_File_Picker_Popup(
            title="Choose Video Files", container_tag="video_file_picker"
        ).show()

        if selected_files.strip() != "":
            file_handler = utils.File()
            file_grid: qtg.Grid = event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            )

            with qtg.sys_cursor(qtg.Cursor.hourglass):
                rejected = self._insert_files_into_grid(
                    file_handler, file_grid, selected_files
                )

            if file_grid.row_count > 0:
                # First file sets project encoding standard - Project files in toto Can be PAL or NTSC not both
                encoding_info = file_grid.userdata_get(row=0, col=4)
                project_video_standard = encoding_info["video_standard"][1]

                loaded_files = []
                for row_index in reversed(range(file_grid.row_count)):
                    file_name = file_grid.value_get(row_index, 0)

                    encoding_info = file_grid.userdata_get(row=row_index, col=4)
                    video_standard = encoding_info["video_standard"][1]

                    if project_video_standard != video_standard:
                        rejected += (
                            f"{sys_consts.SDELIM}{file_name} : {sys_consts.SDELIM} Not Project Video Standard "
                            f"{sys_consts.SDELIM}{project_video_standard}{sys_consts.SDELIM} \n"
                        )

                        file_grid.row_delete(row_index)
                        continue

                    loaded_files.append(file_name)

                # Keep a list of words common to all file names
                self.common_words = utils.Find_Common_Words(loaded_files)

            self._set_project_standard_duration(event)

            if rejected != "":
                qtg.PopMessage(
                    title="These Files Are Not Permitted...", message=rejected
                ).show()

    def _insert_files_into_grid(
        self, file_handler: utils.File, file_grid: qtg.Grid, selected_files: str
    ):
        """
        Inserts files into a the file gird widget.

        Args:
            file_handler (utils.File): An instance of a file handler.
            file_grid (qtg.Grid): The grid widget to insert the files into.
            selected_files (str): A string containing information about the selected files.

        Returns:
            str: A string containing information about any rejected files.

        """
        assert isinstance(
            file_handler, utils.File
        ), f"{file_handler=}. Must be an instance of utils.File"
        assert isinstance(
            file_grid, qtg.Grid
        ), f"{file_grid=}. Must be an instance of qtg.Grid"
        assert isinstance(selected_files, str), f"{selected_files=}/ must be a string."

        rejected = ""
        rows_loaded = file_grid.row_count
        row_index = 0

        # Ugly splits here because video_file_picker/cutter can only return a string
        for file_tuple_str in selected_files.split("|"):
            _, _, video_file, file_folder = file_tuple_str.split(",")

            # Check if file already loade in grid
            for check_row_index in range(file_grid.row_count):
                check_file = file_grid.value_get(row=check_row_index, col=0)
                check_folder = file_grid.userdata_get(row=check_row_index, col=0)

                if check_file == video_file and check_folder == file_folder:
                    break
            else:  # File not in grid already
                encoding_info = dvdarch_utils.get_file_encoding_info(
                    f"{file_folder}{file_handler.ossep}{video_file}"
                )

                toolbox = qtg.HBoxContainer(
                    height=1, width=3, align=qtg.Align.BOTTOMCENTER
                ).add_row(
                    qtg.Button(
                        tag=f"grid_button",
                        height=1,
                        width=1,
                        tune_vsize=-5,
                        callback=self.grid_events,
                        user_data=(
                            file_folder,
                            video_file,
                            encoding_info,
                        ),
                        icon=utils.App_Path("wrench.svg"),
                        tooltip="Cut Video or Change Settings",
                    )
                )

                if encoding_info["video_tracks"][1] == 0:
                    rejected += f"{sys_consts.SDELIM}{video_file} : {sys_consts.SDELIM}No Video Track \n"
                    continue

                duration = str(
                    datetime.timedelta(seconds=encoding_info["video_duration"][1])
                ).split(".")[0]

                file_grid.value_set(
                    value=video_file,
                    row=rows_loaded + row_index,
                    col=0,
                    user_data=file_folder,
                )

                file_grid.value_set(
                    value=str(encoding_info["video_width"][1]),
                    row=rows_loaded + row_index,
                    col=1,
                    user_data=encoding_info,
                )
                file_grid.value_set(
                    value=str(encoding_info["video_height"][1]),
                    row=rows_loaded + row_index,
                    col=2,
                    user_data=encoding_info,
                )

                file_grid.value_set(
                    value=encoding_info["video_format"][1],
                    row=rows_loaded + row_index,
                    col=3,
                    user_data=encoding_info,
                )

                file_grid.value_set(
                    value=encoding_info["video_standard"][1]
                    + f" : {encoding_info['video_scan_order'][1]}"
                    if encoding_info["video_scan_order"] != ""
                    else "",
                    row=rows_loaded + row_index,
                    col=4,
                    user_data=encoding_info,
                ),
                file_grid.value_set(
                    value=duration,
                    row=rows_loaded + row_index,
                    col=5,
                    user_data=encoding_info,
                )

                file_grid.row_widget_set(
                    row=rows_loaded + row_index, col=6, widget=toolbox
                )

                row_index += 1
        return rejected

    def _set_project_standard_duration(self, event: qtg.Action):
        """Sets the  duration and video standard for the current project based on the selected
        input video files.

        Args:
            event (qtg.Action): The calling event .


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
            encoding_info = file_grid.userdata_get(row=0, col=4)
            self.project_video_standard = encoding_info["video_standard"][1]

            for check_row_index in range(file_grid.row_count):
                encoding_info = file_grid.userdata_get(row=check_row_index, col=4)

                total_duration += encoding_info["video_duration"][1]

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
                + PERCENT_SAFTEY_BUFFER
            )

        event.value_set(
            container_tag="dvd_properties",
            tag="project_video_standard",
            value=f"{sys_consts.SDELIM}{self.project_video_standard}{sys_consts.SDELIM}",
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
            qtg.VBoxContainer: THe container that houses the file handler ui layout
        """

        button_container = qtg.HBoxContainer(
            tag="control_buttons", align=qtg.Align.RIGHT
        ).add_row(
            qtg.Button(
                tag="remove_files",
                text="Remove Checked",
                callback=self.event_handler,
                tooltip="Remove Checked Files From Video Input Files",
            ),
            qtg.Spacer(width=1),
            qtg.Button(
                tag="select_files",
                text="Select Files",
                callback=self.event_handler,
                tooltip="Open File Picker Popup To Select Video Files",
            ),
        )

        file_col_def = (
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
                label="Enc",
                tag="encoder",
                width=5,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Standard",
                tag="Standard",
                width=10,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="Duration",
                tag="Duration",
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.Col_Def(
                label="",
                tag="settings",
                width=2,
                editable=False,
                checkable=False,
            ),
        )
        file_control_container = qtg.VBoxContainer(
            tag="video_file_controls", align=qtg.Align.TOPLEFT
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
            tag="control_container", text="Video Input Files", align=qtg.Align.TOPRIGHT
        ).add_row(file_control_container, button_container)

        return control_container


if __name__ == "__main__":
    DVD_Archiver(sys_consts.PROGRAM_NAME).run()
