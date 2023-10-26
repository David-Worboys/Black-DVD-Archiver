"""
    Provides archive management of video artefacts - dvd_image, video source files etc

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
import json
from datetime import datetime
from typing import Final

import dvdarch_utils
import file_utils
import sys_consts
from sys_config import Video_Data
from utils import Text_To_File_Name

# fmt: on

# THe Following constants are used in the archive_dvd_build the method below - changes here mean changes there!
DVD_IMAGE: Final[str] = "dvd_image"
ISO_IMAGE: Final[str] = "iso_image"
VIDEO_SOURCE: Final[str] = "video_source"
MISC: Final[str] = "misc"


@dataclasses.dataclass
class Archive_Manager:
    """Manages archiving of video artefacts - dvd_image, video source files etc"""

    archive_folder: str
    archive_size: str = sys_consts.DVD_ARCHIVE_SIZE
    transcode_type: str = sys_consts.TRANSCODE_NONE

    # Private instance variables
    _error_message: str = ""
    _error_code: int = -1
    _backup_folders: tuple[str, ...] = (DVD_IMAGE, ISO_IMAGE, VIDEO_SOURCE, MISC)
    _json_edit_cuts_file: str = "edit_cuts"

    def __post_init__(self) -> None:
        assert (
            isinstance(self.archive_folder, str) and self.archive_folder.strip() != ""
        ), f"{self.archive_folder=}. Must Be non-empty str"
        assert isinstance(self.archive_size, str) and self.archive_size in (
            sys_consts.BLUERAY_ARCHIVE_SIZE,
            sys_consts.DVD_ARCHIVE_SIZE,
        ), f"{self.archive_size=}, Must be BLUERAY_ARCHIVE_SIZE | DVD_ARCHIVE_SIZE"

        assert isinstance(self.transcode_type, str) and self.transcode_type in (
            sys_consts.TRANSCODE_NONE,
            sys_consts.TRANSCODE_H264,
            sys_consts.TRANSCODE_H265,
        ), (
            f"{self.transcode_type=}, Must be Be TRANSCODE_NONE | TRANSCODE_H264 |"
            " TRANSCODE_H265"
        )

        self._error_message = self._make_folder_structure()

    @property
    def get_error(self) -> str:
        return self._error_message

    @property
    def get_error_code(self) -> int:
        return self._error_code

    def _make_folder_structure(self) -> str:
        """Makes the archive folder structure

        Returns:
            str : An error message if the folder structure could not be created
        """
        file_handler = file_utils.File()
        self._error_code = 1

        if not file_handler.path_exists(self.archive_folder):
            if file_handler.make_dir(self.archive_folder) == -1:
                self._error_message = (
                    "Failed To Create Archive Folder"
                    f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1
                return self._error_message

            now = datetime.now()
            readme_file = file_handler.file_join(self.archive_folder, "README", "txt")

            try:
                with open(readme_file, "w") as file:
                    file.write(
                        f"{now} \n Video Archive Folder Created By"
                        f"{sys_consts.PROGRAM_NAME} - {sys_consts.VERSION_TAG} \n Do"
                        " Not Delete Folder!"
                    )
            except (FileNotFoundError, PermissionError, IOError) as e:
                self._error_message = (
                    "Failed To Write"
                    f" {sys_consts.SDELIM}{readme_file} {e}{sys_consts.SDELIM} "
                )
                self._error_code = 1

        return ""

    def archive_dvd_build(
        self,
        dvd_name: str,
        dvd_folder: str,
        iso_folder: str,
        menu_layout: list[tuple[str, list[Video_Data]]],
        overwrite_existing: bool = True,
    ) -> tuple[int, str]:
        """
        Archives a DVD build and its source video files.

        Args:
            dvd_name (str): The name of the DVD.
            iso_folder (str) : The file path of the folder where the ISO build was created.
            dvd_folder (str): The file path of the folder where the DVD build was created.
            menu_layout (list[tuple[str, list[Video_Data]]]): A list of tuples (menu title,Video_Data) representing the
            DVD folder/file names
            overwrite_existing (bool): Whether to overwrite existing DVD backup folder

        Returns:
            None
        """
        assert (
            isinstance(dvd_name, str) and dvd_name.strip() != ""
        ), f"{dvd_name=}. Must be a non-empty str"
        assert (
            isinstance(dvd_folder, str) and dvd_folder.strip() != ""
        ), f"{dvd_folder=}. Must be a non-empty str"
        assert (
            isinstance(iso_folder, str) and iso_folder.strip() != ""
        ), f"{iso_folder=}. Must be a non-empty str"
        assert isinstance(
            menu_layout, list
        ), f"{menu_layout=} must be a list of tuples of str,Video_Data"

        for menu in menu_layout:
            assert isinstance(menu[0], str), f"{menu[0]=} must be a str"
            assert isinstance(menu[1], list), f"{menu[1]=} must be a list"
            assert all(
                isinstance(video_item, Video_Data) for video_item in menu[1]
            ), f"All elements in {menu[1]=} must be Video_Data"

        self._error_code = 1

        file_handler = file_utils.File()
        video_file_copier = dvdarch_utils.Video_File_Copier()

        dvd_name = Text_To_File_Name(dvd_name)

        backup_path = file_handler.file_join(self.archive_folder, dvd_name)
        video_folders = []

        if not file_handler.path_exists(dvd_folder):
            self._error_message = (
                "Can Not Access DVD Folder :"
                f" {sys_consts.SDELIM}{dvd_folder}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return -1, self._error_message

        if not file_handler.path_exists(iso_folder):
            self._error_message = (
                "Can Not Access ISO Folder :"
                f" {sys_consts.SDELIM}{iso_folder}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return -1, self._error_message

        if not file_handler.path_exists(self.archive_folder):
            self._error_message = (
                "Can Not Access Archive Folder :"
                f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return -1, self._error_message

        if not file_handler.path_writeable(self.archive_folder):
            self._error_message = (
                "Can Not Write To Archive Folder :"
                f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return -1, self._error_message

        if file_handler.path_exists(backup_path) and not overwrite_existing:
            self._error_message = (
                "Backup Folder Already Exists :"
                f" {sys_consts.SDELIM}{sys_consts.SDELIM}{sys_consts.SDELIM}"
            )
            self._error_code = -1

            return -1, self._error_message

        if file_handler.path_exists(backup_path):
            self._error_code, message = file_handler.remove_dir_contents(backup_path)

            if self._error_code == -1:
                self._error_message = str(message).replace(
                    backup_path,
                    f"{sys_consts.SDELIM}{backup_path}{sys_consts.SDELIM}",
                )
                return -1, self._error_message

        if file_handler.make_dir(dvd_name) == -1:
            self._error_code = -1
            self._error_message = (
                "Failed To Create Backup Folder :"
                f" {sys_consts.SDELIM}{dvd_name}{sys_consts.SDELIM}"
            )
            return -1, self._error_message

        for folder in self._backup_folders:
            backup_item_folder = file_handler.file_join(backup_path, folder)

            if folder == DVD_IMAGE:
                self._error_code, self._error_message = file_handler.copy_dir(
                    src_folder=dvd_folder, dest_folder=backup_item_folder
                )

                if self._error_code == -1:
                    return -1, self._error_message

            elif folder == ISO_IMAGE:
                self._error_code, self._error_message = file_handler.copy_dir(
                    src_folder=iso_folder, dest_folder=backup_item_folder
                )
                if self._error_code == -1:
                    return -1, self._error_message
            elif folder == MISC:
                pass
            elif folder == VIDEO_SOURCE:
                if file_handler.make_dir(backup_item_folder) == -1:
                    self._error_code = -1
                    return (
                        -1,
                        (
                            "Failed To Create Backup Folder :"
                            f" {sys_consts.SDELIM}{backup_item_folder}{sys_consts.SDELIM}"
                        ),
                    )
                for menu_index, menu in enumerate(menu_layout):
                    menu_index: int
                    menu: tuple[str, list[Video_Data]]

                    menu_title = menu[0]

                    if menu_title.strip():
                        menu_title = Text_To_File_Name(menu_title)

                        menu_dir = file_handler.file_join(
                            dir_path=backup_item_folder,
                            file_name=Text_To_File_Name(menu_title),
                        )
                        menu_dir_temp = file_handler.file_join(
                            dir_path=backup_item_folder,
                            file_name=f"{Text_To_File_Name(menu_title)}_temp",
                        )
                    else:  # If no menu title, then use the menu number
                        menu_title = f"menu_{menu_index + 1:02}"
                        menu_dir = file_handler.file_join(
                            dir_path=backup_item_folder,
                            file_name=menu_title,
                        )
                        menu_dir_temp = file_handler.file_join(
                            dir_path=backup_item_folder,
                            file_name=menu_title,
                        )

                    video_folders.append((menu_dir_temp, menu_dir, menu_title))

                    if not file_handler.path_exists(menu_dir_temp):
                        if file_handler.make_dir(menu_dir_temp) == -1:
                            self._error_code = -1
                            return (
                                -1,
                                (
                                    "Failed To Create Backup Folder"
                                    f" :{sys_consts.SDELIM}{menu_dir_temp}{sys_consts.SDELIM}"
                                ),
                            )

                    for menu_video_data in menu[1]:
                        backup_file_name = (
                            Text_To_File_Name(
                                menu_video_data.video_file_settings.button_title
                            )
                            if menu_video_data.video_file_settings.button_title.strip()
                            else menu_video_data.video_file
                        )

                        backup_path = file_handler.file_join(
                            dir_path=menu_dir_temp,
                            file_name=backup_file_name,
                            ext=menu_video_data.video_extension,
                        )

                        if (
                            self.transcode_type == sys_consts.TRANSCODE_NONE
                        ):  # Smile, no quality loss
                            (
                                self._error_code,
                                self._error_message,
                            ) = file_handler.copy_file(
                                menu_video_data.video_path, backup_path
                            )

                            if self._error_code == -1:
                                return -1, self._error_message
                        else:  # Grit teeth, have to lower quality with a transcode
                            if self.transcode_type == sys_consts.TRANSCODE_H264:
                                transcoding = "h264"
                            else:
                                transcoding = "h265"

                            if (
                                transcoding
                                not in menu_video_data.encoding_info.video_format.lower()
                            ):
                                print(
                                    "DBG Transcoding"
                                    f" {transcoding=} {menu_video_data.encoding_info.video_format.lower()=}"
                                )
                                print(
                                    f"DBG {menu_video_data.video_path=} {backup_path=}"
                                )
                                (
                                    self._error_code,
                                    output_file,
                                ) = dvdarch_utils.Transcode_H26x(
                                    input_file=menu_video_data.video_path,
                                    output_folder=menu_dir_temp,
                                    width=menu_video_data.encoding_info.video_width,
                                    height=menu_video_data.encoding_info.video_height,
                                    frame_rate=menu_video_data.encoding_info.video_frame_rate,
                                    interlaced=(
                                        True
                                        if menu_video_data.encoding_info.video_scan_type.lower()
                                        == "interlaced"
                                        else False
                                    ),
                                    bottom_field_first=(
                                        True
                                        if menu_video_data.encoding_info.video_scan_order.lower()
                                        == "bff"
                                        else False
                                    ),
                                    h265=True if transcoding == "h265" else False,
                                    high_quality=True,
                                )

                                if (
                                    self._error_code == -1
                                ):  # output_file container error message
                                    self._error_message = output_file
                                    return -1, self._error_message
                            else:
                                print(
                                    f"DBG Copy As  {transcoding=} =="
                                    f" {menu_video_data.encoding_info.video_format.lower()=} "
                                )
                                (
                                    self._error_code,
                                    self._error_message,
                                ) = file_handler.copy_file(
                                    menu_video_data.video_path, backup_path
                                )

                                if self._error_code == -1:
                                    return -1, self._error_message

        if video_folders:
            for video_folder_tuple in video_folders:
                result, message = video_file_copier.copy_folder_into_folders(
                    video_folder_tuple[0],
                    video_folder_tuple[1],
                    video_folder_tuple[2],
                    (
                        4 if self.archive_size == sys_consts.DVD_ARCHIVE_SIZE else 25
                    ),  # sys_consts.BLUERAY_ARCHIVE_SIZE
                )

                if result == -1:
                    return -1, message

            for video_folders in video_folders:  # Remove temp folders
                result, message = file_handler.remove_dir_contents(video_folders[0])

                if result == -1:
                    return -1, message

        return 1, ""

    def delete_edit_cuts(self, file_path: str) -> tuple[int, str]:
        """
        Deletes all edit cuts associated with the given file that are stored in the edit cuts JSON file

        Args:
            file_path (str): The path of the video file.

        Returns:
            tuple[int,str]:
                arg 1 - error_code
                arg 2 - error message
        """
        self._error_message = ""
        self._error_code = 1

        file_handler = file_utils.File()
        json_cuts_file = file_handler.file_join(
            self.archive_folder, self._json_edit_cuts_file, "json"
        )

        if not file_handler.path_exists(self.archive_folder):
            self._error_message = (
                f"{sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM} does not"
                " exist"
            )
            self._error_code = -1
            return self._error_code, self._error_message

        if not file_handler.path_writeable(self.archive_folder):
            self._error_message = (
                f"{sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM} is not"
                " writable"
            )
            self._error_code = -1
            return self._error_code, self._error_message

        if not file_handler.file_exists(json_cuts_file):
            self._error_message = (
                f"{sys_consts.SDELIM}{json_cuts_file}{sys_consts.SDELIM} does not exist"
            )
            self._error_code = 1  # May not be an actual error
            return self._error_code, self._error_message

        try:
            with open(json_cuts_file, "r") as json_file:
                json_data_dict = json.load(json_file)
        except (
            FileNotFoundError,
            PermissionError,
            IOError,
            json.decoder.JSONDecodeError,
        ) as e:
            self._error_message = (
                f"Can not read {sys_consts.SDELIM}{json_cuts_file}."
                f" {e}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return self._error_code, self._error_message

        if file_path in json_data_dict:
            del json_data_dict[file_path]

            # Write the JSON file
            try:
                with open(json_cuts_file, "w") as json_file:
                    json.dump(json_data_dict, json_file)
            except (
                FileNotFoundError,
                PermissionError,
                IOError,
                json.decoder.JSONDecodeError,
            ) as e:
                self._error_message = (
                    "Unable to write to JSON file:"
                    f" {sys_consts.SDELIM}{e}{sys_consts.SDELIM}"
                )
                self._error_code = -1

                return self._error_code, self._error_message

        return 1, ""

    def read_edit_cuts(self, file_path: str) -> tuple[(int, int, str)] | tuple:
        """
        Read edit cuts for a video file from a JSON file.

        Args:
            file_path (str): The path of the video file.

        Returns:
            tuple[(int,int,str)]: A tuple containing the edit cuts for the file_path,
            or an empty tuple if the file_path is not stored or an error occurs.
            Each cut is represented by a tuple with the cut_in value, cut_out value,
            and cut_name string.
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a str"

        self._error_message = ""
        self._error_code = 1

        file_handler = file_utils.File()
        json_cuts_file = file_handler.file_join(
            self.archive_folder, self._json_edit_cuts_file, "json"
        )

        if not file_handler.path_exists(self.archive_folder):
            self._error_message = (
                f"{sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM} does not"
                " exist"
            )
            self._error_code = -1
            return ()

        if not file_handler.path_writeable(self.archive_folder):
            self._error_message = (
                f"{sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM} is not"
                " writable"
            )
            self._error_code = -1
            return ()

        if not file_handler.file_exists(json_cuts_file):
            self._error_message = (
                f"{sys_consts.SDELIM}{json_cuts_file}{sys_consts.SDELIM} does not exist"
            )
            self._error_code = 1  # May not be an actual error
            return ()

        # Read JSON data from file
        try:
            with open(json_cuts_file, "r") as json_file:
                json_data_dict = json.load(json_file)
        except (
            FileNotFoundError,
            PermissionError,
            IOError,
            json.decoder.JSONDecodeError,
        ) as e:
            self._error_message = (
                f"Can not read {sys_consts.SDELIM}{json_cuts_file}."
                f" {e}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return ()

        if not isinstance(json_data_dict, dict):
            self._error_message = "Invalid JSON file format"
            self._error_code = -1
            return ()

        edit_cuts = []
        if file_path in json_data_dict:
            for edit_point in json_data_dict[file_path]:
                if (
                    len(edit_point) != 3
                    or not isinstance(edit_point[0], int)
                    or not isinstance(edit_point[1], int)
                    or not isinstance(edit_point[2], str)
                ):
                    self._error_message = (
                        "Invalid JSON format for"
                        f" {sys_consts.SDELIM}{file_path}{sys_consts.SDELIM}"
                    )
                    edit_cuts = ()
                    break
                edit_cuts.append(tuple(edit_point))
        return tuple(edit_cuts)

    def write_edit_cuts(
        self,
        file_path: str,
        file_cuts: list[(int, int, str)],
    ) -> tuple[int, str]:
        """Store files and cuts in the archive json_file.

        Args:
            file_path (str): The path of the video file that owns the cuts.
            file_cuts (list[(int,int,str)]): A  list of cuts for the file_path.
                Each cut is represented by a tuple with the cut_in value, cut_out value, and cut_name string.

        Returns:
            int, str: Error code (1 Ok, -1 Fail) and Error Message ("" if all good otherwise an error message)
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a str"
        assert isinstance(file_cuts, list), f"{file_cuts=}. Must be a list"

        for cut in file_cuts:
            assert isinstance(cut, tuple), f"{cut=}. Must be a tuple"
            assert len(cut) == 3, f"{cut=}. Must have Mark_In, Mark_Out, Cut Name"
            assert isinstance(cut[0], int), f"{cut[0]=}. Must be int"
            assert isinstance(cut[1], int), f"{cut[1]=}. Must be int"
            assert isinstance(cut[2], str), f"{cut[2]=}. Must be str"

        self._error_message = ""
        self._error_code = 1

        file_handler = file_utils.File()

        json_cuts_file = file_handler.file_join(
            self.archive_folder, self._json_edit_cuts_file, "json"
        )

        if not file_handler.path_exists(self.archive_folder):
            self._error_message = (
                f"{sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM} Does Not"
                " Exist"
            )
            self._error_code = -1
            return self._error_code, self._error_message

        if not file_handler.path_writeable(self.archive_folder):
            self._error_message = (
                f"{sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM} Is Not"
                " Writable"
            )
            self._error_code = -1
            return self._error_code, self._error_message

        json_data_dict = {}

        if file_handler.file_exists(json_cuts_file):
            # Read the JSON file. if it exists, so we update the file_path entry
            try:
                with open(json_cuts_file, "r") as json_file:
                    json_data_dict = json.load(json_file)
            except (
                FileNotFoundError,
                PermissionError,
                IOError,
                json.decoder.JSONDecodeError,
            ) as e:
                # Ignore errors as the file might be empty or corrupt. The write statement below will catch
                # real file OS errors.
                pass

        json_data_dict[file_path] = (
            file_cuts  # Update or make new entry in the json_data_dict.
        )

        # Write the JSON file
        try:
            with open(json_cuts_file, "w") as json_file:
                json.dump(json_data_dict, json_file)
        except (
            FileNotFoundError,
            PermissionError,
            IOError,
            json.decoder.JSONDecodeError,
        ) as e:
            self._error_message = (
                "Unable to write to JSON file:"
                f" {sys_consts.SDELIM}{e}{sys_consts.SDELIM}"
            )
            self._error_code = -1

        return self._error_code, self._error_message
