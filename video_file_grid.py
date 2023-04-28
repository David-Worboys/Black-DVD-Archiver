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
from dvd import Video_Data, Video_File_Settings
from video_cutter import Video_Cutter_Popup
from video_file_picker import Video_File_Picker_Popup

# fmt: on


class Video_File_Grid:
    """This class implements the file handling of the Black DVD Archiver ui"""

    def __init__(self):
        file_handler = file_utils.File()

        self.dvd_percent_used = 0  # TODO Make A selection of DVD5 and DVD9
        self.common_words = []
        self.project_video_standard = ""  # PAL or NTSC
        self.project_duration = ""

        # Private instance variables
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
        self._db_path = platformdirs.user_data_dir(sys_consts.PROGRAM_NAME)

        self._grid_db = file_handler.file_join(
            self._db_path, sys_consts.VIDEO_GRID_DB, "db"
        )

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

    def _edit_video(self, event: qtg.Action) -> None:
        """
        Edits a video file.
        Args:
            event (qtg.Action): The event that triggered the video edit.
        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_handler = file_utils.File()
        dvd_folder = self._db_settings.setting_get(sys_consts.DVD_BUILD_FOLDER)

        if dvd_folder is None or dvd_folder.strip() == "":
            popups.PopError(
                title="DVD Build Folder Error...",
                message=(
                    "A DVD Build Folder Must Be Entered Before Making A Video Edit!"
                ),
            ).show()
            return None

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls", tag="video_input_files"
        )

        tool_button: qtg.Button = event.widget_get(
            container_tag=event.container_tag, tag=event.tag
        )  # Data we want is on the button

        user_data: Video_Data = tool_button.userdata_get()

        video_file_input: list[Video_Data] = [user_data]

        result = Video_Cutter_Popup(
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
                video_file_input[0].video_path,
                video_file_input[0].video_path,
                video_file_input[0].video_file_settings.button_title,
            )
        elif len(video_file_input) == 2:  # Original & one edited file (cut/assemble)
            self._processed_trimmed(
                file_grid,
                video_file_input[0].video_path,
                video_file_input[1].video_path,
                video_file_input[0].video_file_settings.button_title,
            )
        else:  # Original and multiple edited files
            self._processed_trimmed(
                file_grid,
                video_file_input[0].video_path,
                video_file_input[1].video_path,
            )
            file_str = ""
            for file_index, video_data in enumerate(video_file_input):
                if file_index > 0:
                    # This is the target str format for loading the file list display
                    file_str += f"-,-,{video_data.video_file}{video_data.video_extension},{video_data.video_folder}|"

            if file_str:  # Assemble Operation
                # Strip the trailing "|" delimiter from the file_str
                file_str = file_str[:-1]

                # TODO Make user configurable perhape
                self._delete_file_from_grid(file_grid, video_file_input[0].video_path)

                # Insert Assembled Children  Files
                self._insert_files_into_grid(file_handler, file_grid, file_str)
        return None

    def _delete_file_from_grid(
        self,
        file_grid: qtg.Grid,
        source_file_path: str,
    ) -> None:
        """Delete the source file from the file grid.
        Args:
            file_grid (qtg.Grid): An instance of the `Grid` class.
            source_file_path (str): A string representing the source folder path of the file to be deleted.
        """
        assert isinstance(file_grid, qtg.Grid), f"{file_grid}. Must be a Grid instance"
        assert (
            isinstance(source_file_path, str) and source_file_path.strip() != ""
        ), f"{source_file_path=}. Must be a non-empty str"

        file_handler = file_utils.File()

        (
            source_folder,
            source_file,
            source_extension,
        ) = file_handler.split_file_path(source_file_path)

        for row in range(0, file_grid.row_count):
            # File data we want is on the button object
            row_tool_button: qtg.Button = file_grid.row_widget_get(
                row=row, col=6, tag="grid_button"
            )

            user_data = row_tool_button.userdata_get()

            if user_data is not None:
                if (
                    source_folder == user_data.video_folder
                    and source_file == user_data.video_file
                    and source_extension == user_data.video_extension
                ):
                    file_grid.row_delete(row)

    def _processed_trimmed(
        self,
        file_grid: qtg.Grid,
        source_file: str,
        trimmed_file: str,
        button_title: str = "",
    ) -> None:
        """
        Updates the file_grid with the trimmed_file detail, after finding the corresponding grid entry.
        Args:
            file_grid (qtg.Grid): The grid to update.
            source_file (str): The name of the source file to match.
            trimmed_file (str): The trimmed file to update the grid details with.
            button_title (str): The button title to update the grid details with.
        """
        assert isinstance(file_grid, qtg.Grid), f"{file_grid=}. Must br qtg.Grid,"
        assert (
            isinstance(source_file, str) and source_file.strip() != ""
        ), f"{source_file=}. Must be a non-empty str"
        assert (
            isinstance(trimmed_file, str) and trimmed_file.strip() != ""
        ), f"{trimmed_file=}. Must be a non-empty str."

        file_handler = file_utils.File()

        (
            source_folder,
            source_file_name,
            source_extension,
        ) = file_handler.split_file_path(source_file)

        (
            trimmed_folder,
            trimmed_file_name,
            trimmed_extension,
        ) = file_handler.split_file_path(trimmed_file)

        # Scan looking for source of trimmed file
        for row in range(file_grid.row_count):
            # Data we want is on the button object
            row_tool_button: qtg.Button = file_grid.row_widget_get(
                row=row, col=6, tag="grid_button"
            )

            user_data: Video_Data = row_tool_button.userdata_get()

            if user_data is not None:  # Should never happen
                if (
                    user_data.video_folder == source_folder
                    and user_data.video_file == source_file_name
                    and user_data.video_extension == source_extension
                ):
                    encoding_info = dvdarch_utils.get_file_encoding_info(trimmed_file)
                    if encoding_info["error"][1]:  # Error Occurred, should not happen
                        popups.PopError(
                            title="Encoding Read Error...",
                            message=encoding_info["error"][1],
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
                            seconds=updated_user_data.encoding_info["video_duration"][1]
                        )
                    ).split(".")[0]

                    self._populate_grid_row(
                        file_grid=file_grid,
                        row_index=row,
                        video_user_data=updated_user_data,
                        duration=duration,
                    )

                    row_tool_button.userdata_set(updated_user_data)

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
                        file_grid: qtg.Grid = event.widget_get(
                            container_tag="video_file_controls",
                            tag="video_input_files",
                        )

                        if (
                            file_grid.row_count > 0
                            and file_grid.checkitems_get
                            and popups.PopYesNo(
                                title="Remove Checked...",
                                message="Remove The Checked Files?",
                            ).show()
                            == "yes"
                        ):
                            for item in reversed(file_grid.checkitems_get):
                                file_grid.row_delete(item[0])

                        self._set_project_standard_duration(event)
                    case "rename_files":
                        self._generate_button_names(event)

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

        try:
            with shelve.open(self._grid_db) as db:
                db_data = db.get("video_grid")

                if db_data:
                    for row_index, row in enumerate(db_data):
                        for item in row:
                            if item[1]:
                                video_data: Video_Data = item[1]

                                duration = str(
                                    datetime.timedelta(
                                        seconds=video_data.encoding_info[
                                            "video_duration"
                                        ][1]
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
                                    row=row_index, col=6, widget=toolbox
                                )

            self._set_project_standard_duration(event)
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
            with shelve.open(self._grid_db) as db:
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

    def _generate_button_names(self, event) -> None:
        """Tries to generate sensible button names from the file title
        Args:
            event (qtg.Acton) : Calling event
        """
        file_handler = file_utils.File()

        file_grid: qtg.Grid = event.widget_get(
            container_tag="video_file_controls",
            tag="video_input_files",
        )

        if (
            file_grid.row_count > 0
            and popups.PopYesNo(
                title="Auto=Generate Button Names...",
                message="Automatically Generate Button Names?",
            ).show()
            == "yes"
        ):
            for row_index in range(file_grid.row_count):
                user_data: Video_Data = file_grid.userdata_get(row=row_index, col=4)

                button_title = file_handler.extract_title(
                    user_data.video_file, self.common_words
                )

                if button_title.strip() != "":
                    user_data.video_file_settings.button_title = button_title
                    file_grid.value_set(
                        row=row_index, col=0, value=button_title, user_data=user_data
                    )

                    file_grid.userdata_set(row=row_index, user_data=user_data)

    def load_video_input_files(self, event: qtg.Action) -> None:
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
            file_handler = file_utils.File()
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
                user_data: Video_Data = file_grid.userdata_get(row=0, col=4)
                project_video_standard = user_data.encoding_info["video_standard"][1]

                loaded_files = []
                for row_index in reversed(range(file_grid.row_count)):
                    file_name = file_grid.value_get(row_index, 0)

                    user_data: Video_Data = file_grid.userdata_get(row=row_index, col=4)

                    video_standard = user_data.encoding_info["video_standard"][1]

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

            self._set_project_standard_duration(event)

            if rejected != "":
                popups.PopMessage(
                    title="These Files Are Not Permitted...", message=rejected
                ).show()

    def _insert_files_into_grid(
        self, file_handler: file_utils.File, file_grid: qtg.Grid, selected_files: str
    ) -> str:
        """
        Inserts files into the file gird widget.
        Args:
            file_handler (utils.File): An instance of a file handler.
            file_grid (qtg.Grid): The grid widget to insert the files into.
            selected_files (str): A string containing information about the selected files.
        Returns:
            str: A string containing information about any rejected files.
        """
        assert isinstance(
            file_handler, file_utils.File
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
            _, _, video_file_name, video_file_folder = file_tuple_str.split(",")

            video_file_path = file_handler.file_join(video_file_folder, video_file_name)

            (
                video_file_path,
                video_file_name,
                video_extension,
            ) = file_handler.split_file_path(video_file_path)

            # Check if file already loaded in grid
            for check_row_index in range(file_grid.row_count):
                video_user_data: Video_Data = file_grid.userdata_get(
                    row=check_row_index, col=0
                )

                if (
                    video_user_data.video_file == video_file_name
                    and video_user_data.video_folder == video_file_path
                    and video_user_data.video_extension == video_extension
                ):
                    break
            else:  # File not in grid already
                video_user_data = Video_Data(
                    video_folder=video_file_path,
                    video_file=video_file_name,
                    video_extension=video_extension,
                    encoding_info={},
                    video_file_settings=Video_File_Settings(),
                )

                video_user_data.encoding_info = dvdarch_utils.get_file_encoding_info(
                    video_user_data.video_path
                )

                if video_user_data.encoding_info["error"][
                    1
                ]:  # Error Occurred, should not happen
                    rejected += (
                        f"File Error {sys_consts.SDELIM}{video_file_name} :"
                        f" {sys_consts.SDELIM} {video_user_data.encoding_info['error'][1]} \n"
                    )
                    continue

                toolbox = self._get_toolbox(video_user_data)

                if video_user_data.encoding_info["video_tracks"][1] == 0:
                    rejected += (
                        f"{sys_consts.SDELIM}{video_file_name} : {sys_consts.SDELIM}No"
                        " Video Track \n"
                    )
                    continue

                duration = str(
                    datetime.timedelta(
                        seconds=video_user_data.encoding_info["video_duration"][1]
                    )
                ).split(".")[0]

                self._populate_grid_row(
                    file_grid=file_grid,
                    row_index=rows_loaded + row_index,
                    video_user_data=video_user_data,
                    duration=duration,
                )

                file_grid.row_widget_set(
                    row=rows_loaded + row_index, col=6, widget=toolbox
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

        toolbox = qtg.HBoxContainer(height=1, width=3, align=qtg.Align.CENTER).add_row(
            qtg.Button(
                tag=f"grid_button",
                height=1,
                width=1,
                tune_vsize=-5,
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
                video_user_data.video_file
                if video_user_data.video_file_settings.button_title.strip() == ""
                else video_user_data.video_file_settings.button_title
            ),
            row=row_index,
            col=0,
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=str(video_user_data.encoding_info["video_width"][1]),
            row=row_index,
            col=1,
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=str(video_user_data.encoding_info["video_height"][1]),
            row=row_index,
            col=2,
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=video_user_data.encoding_info["video_format"][1],
            row=row_index,
            col=3,
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=(
                video_user_data.encoding_info["video_standard"][1]
                + f" : { video_user_data.encoding_info['video_scan_order'][1]}"
                if video_user_data.encoding_info["video_scan_order"] != ""
                else ""
            ),
            row=row_index,
            col=4,
            user_data=video_user_data,
        )

        file_grid.value_set(
            value=duration,
            row=row_index,
            col=5,
            user_data=video_user_data,
        )

    def _set_project_standard_duration(self, event: qtg.Action) -> None:
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
            encoding_info = file_grid.userdata_get(row=0, col=4).encoding_info
            self.project_video_standard = encoding_info["video_standard"][1]

            for check_row_index in range(file_grid.row_count):
                encoding_info = file_grid.userdata_get(
                    row=check_row_index, col=4
                ).encoding_info

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
            qtg.VBoxContainer: THe container that houses the file handler ui layout
        """

        button_container = qtg.HBoxContainer(
            tag="control_buttons", align=qtg.Align.RIGHT
        ).add_row(
            qtg.Button(
                icon=file_utils.App_Path("text.svg"),
                tag="rename_files",
                callback=self.event_handler,
                tooltip="Auto-Generate DVD Button Titles",
                width=2,
            ),
            qtg.Spacer(width=1),
            qtg.Button(
                icon=file_utils.App_Path("x.svg"),
                tag="remove_files",
                callback=self.event_handler,
                tooltip="Remove Checked Files From DVD Input Files",
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
            tag="control_container", text="DVD Input Files", align=qtg.Align.TOPRIGHT
        ).add_row(file_control_container, button_container)

        return control_container
