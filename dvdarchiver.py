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

import datetime

# Tell Black to leave this block alone (realm of isort)
# fmt: off
import appdirs

import dvdarch_utils
import qtgui as qtg
import sqldb
import sys_consts
import utils
from dvd import DVD, DVD_Config, File_Def
from video_file_picker import video_file_picker_popup

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

        self._data_path: str = appdirs.user_data_dir(sys_consts.PROGRAM_NAME)

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
            case qtg.SYSEVENTS.APPINIT:
                pass
            case qtg.SYSEVENTS.APPCLOSED:
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
            case qtg.SYSEVENTS.APPPOSTINIT:
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

            case qtg.SYSEVENTS.CLICKED:
                match event.tag:
                    case "dvd_folder_select":
                        self._dvd_folder_select(event)
                    case "exit_app":
                        self._DVD_Arch_App.app_exit()
                    case "make_dvd":
                        self._make_dvd(event)
            case qtg.SYSEVENTS.INDEXCHANGED:
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

    def _dvd_folder_select(self, event):
        """Select a DVD build folder and update the settings in the database with the selected folder.

        Args:
            event (Event): The triggering event

        Returns:
            None.

        Variables:
            folder (str): The folder path retrieved from the database settings or the default videos folder if it is not set.
            folder (str): The selected folder path obtained from the PopFolderGet dialog.

        Note:
            The selected folder is saved in the database settings for future use.

        """
        folder = self._db_settings.setting_get("dvd_build_folder")

        if folder is None or folder.strip() == "":
            folder = utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)

        folder = qtg.PopFolderGet(
            title=f"Select A DVD Buld Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()

        if folder.strip() != "":
            self._db_settings.setting_set("dvd_build_folder", folder)

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

        dvd_folder = self._db_settings.setting_get("dvd_build_folder")

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

        with qtg.sys_cursor(qtg.CURSOR.hourglass):
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
        error_message = ""

        with qtg.sys_cursor(qtg.CURSOR.hourglass):
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
                self._dvd.dvd_title = dvd_title

                result, error_message = self._dvd.build()

        if result == -1:
            qtg.PopError(
                title="DVD Build Error...",
                message=f"Failed To Create A DVD!!\n{error_message}",
            ).show()

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
        combo_data: qtg.COMBO_DATA = event.value

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
        dvd_build_folder = self._db_settings.setting_get("dvd_build_folder")

        if dvd_build_folder is None or dvd_build_folder.strip() == "":
            dvd_build_folder = utils.Special_Path(sys_consts.SPECIAL_PATH.VIDEOS)
            self._db_settings.setting_set("dvd_build_folder", dvd_build_folder)

        color_list = [
            qtg.COMBO_ITEM(display=color, data=color, icon=None, user_data=color)
            for color in dvdarch_utils.get_color_names()
        ]
        font_list = [
            qtg.COMBO_ITEM(display=font[0], data=font[1], icon=None, user_data=font)
            for font in dvdarch_utils.get_fonts()
        ]

        info_panel = qtg.HBoxContainer().add_row(
            qtg.Label(
                tag="project_duration",
                label="Duration (H:M:S)",
                width=8,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.FRAMESTYLE.PANEL,
                    frame=qtg.FRAME.SUNKEN,
                    line_width=2,
                ),
            ),
            qtg.Label(
                tag="avg_bitrate",
                label="Avg Bitrate",
                text=f"{sys_consts.AVERAGE_BITRATE / 1000:.1f} Mb/s",
                width=9,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.FRAMESTYLE.PANEL,
                    frame=qtg.FRAME.SUNKEN,
                    line_width=2,
                ),
            ),
            qtg.Label(
                tag="percent_of_dvd",
                label="DVD Used",
                width=3,
                frame=qtg.Widget_Frame(
                    frame_style=qtg.FRAMESTYLE.PANEL,
                    frame=qtg.FRAME.SUNKEN,
                    line_width=2,
                ),
                buddy_control=qtg.Label(text="%", translate=False, width=6),
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
                    frame_style=qtg.FRAMESTYLE.PANEL,
                    frame=qtg.FRAME.SUNKEN,
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
                    icon=qtg.SYSICON.dir.get(),
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
            align=qtg.ALIGN.TOPLEFT,
            width=60,  # text="DVD Options"
        ).add_row(
            dvd_properties,
            # qtg.Spacer(),
            dvd_menu_properties,
            self._file_control.layout(),
        )

        buttons_container = qtg.HBoxContainer().add_row(
            qtg.Button(
                tag="make_dvd", text="Make DVD", callback=self.event_handler, width=9
            ),
            qtg.Spacer(width=90),
            qtg.Button(
                tag="exit_app", text="Exit", callback=self.event_handler, width=9
            ),
        )

        screen_container = qtg.VBoxContainer(
            tag="main", align=qtg.ALIGN.RIGHT, width=80
        ).add_row(main_control_container, qtg.Spacer(), buttons_container)

        return screen_container

    def run(self) -> None:
        """Starts the application and gets the show on the road"""
        self._DVD_Arch_App.run(self.layout())


class file_control:
    """This class implements the file handling of the Black Archiver ui"""

    def __init__(self):
        self.project_video_standard = ""  # PAL or NTSC
        self.project_duration = ""
        self.dvd_percent_used = 0  # TODO Make A selection of DVD5 and DVD9
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

    def grid_events(self, event: qtg.Action):
        """Process Grid Events

        Args:
            event (Action): Action
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        if event.event == qtg.SYSEVENTS.CLICKED:
            if event.value.row >= 0 and event.value.col >= 0:
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

    def event_handler(self, event: qtg.Action):
        """Handles  application events

        Args:
            event (Action): The triggering event
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        match event.event:
            case qtg.SYSEVENTS.CLICKED:
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
                        folder = self._db_settings.setting_get("dvd_build_folder")

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

        selected_files = video_file_picker_popup(title="Choose Video Files").show()

        if selected_files.strip() != "":
            file_handler = utils.File()
            file_grid: qtg.Grid = event.widget_get(
                container_tag="video_file_controls",
                tag="video_input_files",
            )

            rows_loaded = file_grid.row_count
            row_index = 0
            rejected = ""

            with qtg.sys_cursor(qtg.CURSOR.hourglass):
                # Ugly splits here because video_file_picker can only return a string
                for file_tuple_str in selected_files.split("|"):
                    file_tuple = file_tuple_str.split(",")

                    file = file_tuple[2]
                    file_folder = file_tuple[3]

                    # Check if file already loade in grid
                    for check_row_index in range(file_grid.row_count):
                        check_file = file_grid.value_get(row=check_row_index, col=0)
                        check_folder = file_grid.userdata_get(
                            row=check_row_index, col=0
                        )

                        if check_file == file and check_folder == file_folder:
                            break
                    else:  # File not in grid already
                        encoding_info = dvdarch_utils.get_file_encoding_info(
                            f"{file_folder}{file_handler.ossep}{file}"
                        )

                        if encoding_info["video_tracks"][1] == 0:
                            rejected += f"{sys_consts.SDELIM}{file} : {sys_consts.SDELIM}No Video Track \n"
                            continue

                        duration = str(
                            datetime.timedelta(
                                seconds=encoding_info["video_duration"][1]
                            )
                        ).split(".")[0]

                        file_grid.value_set(
                            value=file,
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

                        row_index += 1

            if file_grid.row_count > 0:
                # First file sets project encoding standard - Files Can be PAL or NTSC not both
                encoding_info = file_grid.userdata_get(row=0, col=4)
                project_video_standard = encoding_info["video_standard"][1]

                for row_index in reversed(range(file_grid.row_count)):
                    # encoding_info = file_grid.userdata_get(row=row_index, col=4)
                    video_standard = encoding_info["video_standard"][1]
                    if project_video_standard != video_standard:
                        file = file_grid.value_get(row=row_index, col=4)
                        rejected += (
                            f"{sys_consts.SDELIM}{file} : {sys_consts.SDELIM} Not Project Video Standard "
                            f"{sys_consts.SDELIM}{project_video_standard}{sys_consts.SDELIM} \n"
                        )
                        file_grid.row_delete(row_index)

            self._set_project_standard_duration(event)

            if rejected != "":
                qtg.PopMessage(
                    title="These Files Are Not Permitted...", message=rejected, width=80
                ).show()

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
        control_container = qtg.VBoxContainer(
            tag="control_container", text="Video Input Files", align=qtg.ALIGN.TOPRIGHT
        )
        button_container = qtg.HBoxContainer(
            tag="control_buttons", align=qtg.ALIGN.RIGHT
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
            qtg.COL_DEF(
                label="Video File",
                tag="video_file",
                width=70,
                editable=False,
                checkable=True,
            ),
            qtg.COL_DEF(
                label="Width",
                tag="width",
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.COL_DEF(
                label="Height",
                tag="height",
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.COL_DEF(
                label="Encoder",
                tag="encoder",
                width=7,
                editable=False,
                checkable=False,
            ),
            qtg.COL_DEF(
                label="Standard",
                tag="Standard",
                width=10,
                editable=False,
                checkable=False,
            ),
            qtg.COL_DEF(
                label="Duration",
                tag="Duration",
                width=7,
                editable=False,
                checkable=False,
            ),
        )
        file_control_container = qtg.VBoxContainer(
            tag="video_file_controls", align=qtg.ALIGN.TOPLEFT
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

        control_container.add_row(file_control_container, button_container)

        return control_container


if __name__ == "__main__":
    DVD_Archiver(sys_consts.PROGRAM_NAME).run()
