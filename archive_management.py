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

import dataclasses
from datetime import datetime
from typing import Final

import dvdarch_utils
import QTPYGUI.file_utils as file_utils
import sys_consts
from sys_config import Video_Data
from QTPYGUI.utils import Is_Complied, Text_To_File_Name

# THe Following constants are used in the archive_dvd_build the method below - changes here mean changes there!
DVD_IMAGE: Final[str] = "dvd_image"
ISO_IMAGE: Final[str] = "iso_image"
VIDEO_SOURCE: Final[str] = "video_source"
STREAMING: Final[str] = "streaming"  # Used in archival mode only
PRESERVATION_MASTER: Final[str] = "preservation_master"  # Used in archival mode only
MISC: Final[str] = "misc"


@dataclasses.dataclass
class Archive_Manager:
    """Manages archiving of video artefacts - dvd_image, video source files etc"""

    archive_folder: str
    streaming_folder: str = ""
    archive_size: str = sys_consts.DVD_ARCHIVE_SIZE
    transcode_type: str = sys_consts.TRANSCODE_NONE

    # Private instance variables
    _error_message: str = ""
    _error_code: int = -1
    _backup_folders: tuple[str, ...] = (DVD_IMAGE, ISO_IMAGE, VIDEO_SOURCE, MISC)

    def __post_init__(self) -> None:
        """
        Validates and sets default values for the Archive_Manager instance.

        Ensures that the archive_folder, streaming_folder, archive_size, and
        transcode_type are valid and assigns default values if necessary.
        Creates the folder structure for archiving and initializes error
        messages if folder creation fails.

        """
        assert (
            isinstance(self.archive_folder, str) and self.archive_folder.strip() != ""
        ), f"{self.archive_folder=}. Must Be non-empty str"
        assert isinstance(self.streaming_folder, str), (
            f"{self.streaming_folder=}. Must be str"
        )
        assert isinstance(self.archive_size, str) and self.archive_size in (
            sys_consts.BLUERAY_ARCHIVE_SIZE,
            sys_consts.DVD_ARCHIVE_SIZE,
        ), f"{self.archive_size=}, Must be BLUERAY_ARCHIVE_SIZE | DVD_ARCHIVE_SIZE"

        assert isinstance(self.transcode_type, str) and self.transcode_type in (
            sys_consts.TRANSCODE_NONE,
            sys_consts.TRANSCODE_FFV1ARCHIVAL,
            sys_consts.TRANSCODE_H264,
            sys_consts.TRANSCODE_H265,
        ), (
            f"{self.transcode_type=}, Must be Be TRANSCODE_NONE |"
            " TRANSCODE_FFV1ARCHIVAL | TRANSCODE_H264 | TRANSCODE_H265"
        )

        if self.streaming_folder.strip() == "":
            self.streaming_folder = self.archive_folder

        self._error_message = self._make_folder_structure()

    @property
    def get_error(self) -> str:
        """
        Returns the last error message encountered during archive folder creation.

        Returns:
            str: The last error message encountered. Empty string if no errors.
        """
        return self._error_message

    @property
    def get_error_code(self) -> int:
        """
        Returns the last error code encountered during archive folder creation.

        Returns:
            int: The last error code encountered. -1 if no errors.
        """
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

        if not file_handler.path_exists(self.streaming_folder):
            if file_handler.make_dir(self.streaming_folder) == -1:
                self._error_message = (
                    "Failed To Create Streaming Folder"
                    f" {sys_consts.SDELIM}{self.streaming_folder}{sys_consts.SDELIM}"
                )
                self._error_code = -1
                return self._error_message

            now = datetime.now()
            readme_file = file_handler.file_join(self.streaming_folder, "README", "txt")

            try:
                with open(readme_file, "w") as file:
                    file.write(
                        f"{now} \n Video Streaming Folder Created By"
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
            iso_folder (str): The file path of the folder where the ISO build was created.
            dvd_folder (str): The file path of the folder where the DVD build was created.
            menu_layout (list[tuple[str, list[Video_Data]]]): A list of tuples (menu title,Video_Data) representing the
            DVD folder/file names
            overwrite_existing (bool): Whether to overwrite existing DVD backup folder

        Returns:
            tuple(int,str)
                arg 1: 1 if ok, -1 failed
                arg 2: Empty string if ok, error message if failed
        """

        ##### Helper functions
        def _get_video_file_paths(
            preservation_master_folder: str, streaming_folder: str
        ) -> list[
            tuple[
                tuple[str, str, str, list[Video_Data]],
                tuple[str, str, str, list[Video_Data]],
            ]
        ]:
            """Returns the video files paths derived from the menu layout

            Args:
                preservation_master_folder (str): The folder where the video file preservation master will be placed
                streaming_folder (str): The folder where the video file streaming copy will be placed

            Returns:
                list[
                    tuple[
                        tuple[str, str, str, list[Video_Data]], # Preservation Master File Tuple
                        tuple[str, str, str, list[Video_Data]], # Streaming file Tuple
                    ]
                ]
            """
            assert isinstance(preservation_master_folder, str), (
                f"{preservation_master_folder=}. Must be a str"
            )
            assert isinstance(streaming_folder, str), (
                f"{streaming_folder=}. Must be a str"
            )
            video_folders = []

            for menu_index, menu in enumerate(menu_layout):
                menu_index: int  # Type Hint
                menu: tuple[str, list[Video_Data]]

                menu_title = menu[0]
                menu_video_data = menu[1]

                if menu_title.strip():
                    menu_title = f"{menu_index + 1:02}_{Text_To_File_Name(menu_title)}"

                    preservation_master_menu_path = file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=Text_To_File_Name(menu_title),
                    )
                    preservation_master_menu_path_temp = file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=f"{Text_To_File_Name(menu_title)}_temp",
                    )

                    streaming_path = file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=Text_To_File_Name(menu_title),
                    )
                    streaming_path_temp = file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=f"{Text_To_File_Name(menu_title)}_temp",
                    )
                else:  # If no menu title, then use the menu number
                    menu_title = f"{menu_index + 1:02}_Untitled_Menu"

                    preservation_master_menu_path = file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=menu_title,
                    )
                    preservation_master_menu_path_temp = file_handler.file_join(
                        dir_path=preservation_master_folder,
                        file_name=menu_title,
                    )

                    streaming_path = file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=menu_title,
                    )
                    streaming_path_temp = file_handler.file_join(
                        dir_path=streaming_folder,
                        file_name=menu_title,
                    )

                video_folders.append((
                    (
                        preservation_master_menu_path_temp,
                        preservation_master_menu_path,
                        menu_title,
                        menu_video_data,
                    ),
                    (streaming_path_temp, streaming_path, menu_title, menu_video_data),
                ))

            return video_folders

        def _transcode_video_file(
            video_data: Video_Data,
            preservation_master_path: str,
            streaming_path: str,
            button_file_name: str,
            button_index: int,
            transcode_type: str,
        ) -> tuple[int, str]:
            """Transcodes the source video file, if needed, and produces a streaming copy in the H264 format.

            Args:
                video_data (Video_Data): The Video_Data of the video file to be transcoded
                preservation_master_path (str): The file path where the video file video preservation master will be placed
                streaming_path (str): The file path where the video file H264 straming copy will be placed
                button_file_name (str): The DVD button file name
                button_index (int): The DVD button index
                transcode_type(str):  The transcode type (TRANSCODE_NONE,TRANSCODE_FFV1ARCHIVAL,TRANSCODE_H264, TRANSCODE_H265)


            Returns:
                tuple(int,str)
                   arg 1: 1 if ok, -1 failed
                   arg 2: Empty string if ok, error message if failed`

            """
            assert isinstance(video_data, Video_Data), (
                f"{video_data=}. Must be instance of Video_Data"
            )
            assert isinstance(preservation_master_path, str), (
                f"{preservation_master_path=}. Must be str"
            )
            assert isinstance(streaming_path, str), f"{streaming_path=}. Must be str"
            assert isinstance(button_file_name, str), (
                f"{button_file_name=}. Must be str"
            )
            assert isinstance(button_index, int), f"{button_index=}. Must be int"
            assert isinstance(transcode_type, str) and transcode_type in (
                sys_consts.TRANSCODE_NONE,
                sys_consts.TRANSCODE_FFV1ARCHIVAL,
                sys_consts.TRANSCODE_H264,
                sys_consts.TRANSCODE_H265,
            ), (
                f"{transcode_type=}. Must be TRANSCODE_NONE,TRANSCODE_FFV1ARCHIVAL,TRANSCODE_H264, TRANSCODE_H265"
            )

            (
                _,
                _,
                file_extension,
            ) = file_handler.split_file_path(video_data.video_path)

            preservation_file = file_handler.file_join(
                preservation_master_path,
                f"{button_index + 1:02}_{button_file_name}",
                file_extension,
            )

            streaming_file = file_handler.file_join(
                streaming_path,
                f"{button_index + 1:02}_{button_file_name}",
                file_extension,
            )

            match transcode_type:
                case sys_consts.TRANSCODE_NONE:
                    (
                        self._error_code,
                        self._error_message,
                    ) = file_handler.copy_file(video_data.video_path, preservation_file)

                    if self._error_code == -1:
                        return -1, self._error_message

                case sys_consts.TRANSCODE_FFV1ARCHIVAL:
                    if (
                        "ffv1" not in video_data.encoding_info.video_format.lower()
                    ):  # Check if we need to transcode
                        (
                            self._error_code,
                            message,
                        ) = dvdarch_utils.Transcode_ffv1_archival(
                            input_file=video_data.video_path,
                            output_folder=preservation_master_path,
                            width=video_data.encoding_info.video_width,
                            height=video_data.encoding_info.video_height,
                            frame_rate=video_data.encoding_info.video_frame_rate,
                        )

                        if self._error_code == -1:
                            self._error_message = message
                            return -1, self._error_message

                        # message has ouput file name
                        output_file_path = message
                        (
                            _,
                            _,
                            file_extension,
                        ) = file_handler.split_file_path(output_file_path)
                        new_output_file_path = file_handler.file_join(
                            preservation_master_path,
                            f"{button_index + 1:02}_{button_file_name}",
                            file_extension,
                        )

                        if (
                            file_handler.rename_file(
                                output_file_path,
                                new_output_file_path,
                            )
                            == -1
                        ):
                            self._error_message = (
                                f"Failed To Rename {sys_consts.SDELIM}{output_file_path}{sys_consts.SDELIM} To "
                                f"{sys_consts.SDELIM}{new_output_file_path}{sys_consts.SDELIM}"
                            )
                            return -1, self._error_message
                    else:  # Just Copy
                        (
                            _,
                            _,
                            file_extension,
                        ) = file_handler.split_file_path(video_data.video_path)
                        new_output_file_path = file_handler.file_join(
                            preservation_master_path,
                            f"{button_index + 1:02}_{button_file_name}",
                            file_extension,
                        )

                        (
                            self._error_code,
                            self._error_message,
                        ) = file_handler.copy_file(
                            video_data.video_path, new_output_file_path
                        )

                        if self._error_code == -1:
                            return -1, self._error_message

                case sys_consts.TRANSCODE_H264 | sys_consts.TRANSCODE_H265:
                    encoding_method = (
                        "h264"
                        if transcode_type == sys_consts.TRANSCODE_H264
                        else "h265"
                    )

                    if (
                        encoding_method
                        not in video_data.encoding_info.video_format.lower()
                    ):  # Check if we need to transcode
                        if not Is_Complied():
                            print(
                                "DBG Transcoding"
                                f" {encoding_method=} {video_data.encoding_info.video_format.lower()=}"
                            )
                            print(f"DBG {video_data.video_path=} {button_file_name=}")

                        (
                            self._error_code,
                            message,
                        ) = dvdarch_utils.Transcode_H26x(
                            input_file=video_data.video_path,
                            output_folder=preservation_master_path,
                            width=video_data.encoding_info.video_width,
                            height=video_data.encoding_info.video_height,
                            frame_rate=video_data.encoding_info.video_frame_rate,
                            interlaced=(
                                True
                                if video_data.encoding_info.video_scan_type.lower()
                                == "interlaced"
                                else False
                            ),
                            bottom_field_first=(
                                True
                                if video_data.encoding_info.video_scan_order.lower()
                                == "bff"
                                else False
                            ),
                            h265=False
                            if transcode_type == sys_consts.TRANSCODE_H264
                            else True,
                            high_quality=True,
                        )

                        if self._error_code == -1:
                            self._error_message = message
                            return -1, self._error_message

                        # message has output file name
                        output_file_path = message
                        (
                            _,
                            _,
                            file_extension,
                        ) = file_handler.split_file_path(output_file_path)
                        new_output_file_path = file_handler.file_join(
                            preservation_master_path,
                            f"{button_index + 1:02}_{button_file_name}",
                            file_extension,
                        )

                        if (
                            file_handler.rename_file(
                                output_file_path,
                                new_output_file_path,
                            )
                            == -1
                        ):
                            self._error_message = (
                                f"Failed To Rename {sys_consts.SDELIM}{output_file_path}{sys_consts.SDELIM} To "
                                f"{sys_consts.SDELIM}{new_output_file_path}{sys_consts.SDELIM}"
                            )
                            return -1, self._error_message
                    else:  # we copy
                        if not Is_Complied():
                            print(
                                f"DBG Copy As  {('h264' if transcode_type == sys_consts.TRANSCODE_H264 else 'h265')=} =="
                                f" {video_data.encoding_info.video_format.lower()=} "
                            )

                        new_output_file_path = file_handler.file_join(
                            preservation_master_path,
                            f"{button_index + 1:02}_{button_file_name}",
                            "mp4",
                        )

                        (
                            self._error_code,
                            self._error_message,
                        ) = file_handler.copy_file(
                            video_data.video_path, new_output_file_path
                        )

                        if self._error_code == -1:
                            return -1, self._error_message

            # Make a streaming file
            if (
                "h264" not in video_data.encoding_info.video_format.lower()
            ):  # Check if we need to transcode
                (
                    self._error_code,
                    message,
                ) = dvdarch_utils.Transcode_H26x(
                    input_file=video_data.video_path,
                    output_folder=streaming_path,
                    width=video_data.encoding_info.video_width,
                    height=video_data.encoding_info.video_height,
                    frame_rate=video_data.encoding_info.video_frame_rate,
                    interlaced=(
                        True
                        if video_data.encoding_info.video_scan_type.lower()
                        == "interlaced"
                        else False
                    ),
                    bottom_field_first=(
                        True
                        if video_data.encoding_info.video_scan_order.lower() == "bff"
                        else False
                    ),
                    h265=False,
                    high_quality=True,
                )

                if self._error_code == -1:
                    self._error_message = message
                    return -1, self._error_message

                # message has output file name
                output_file_path = message
                (
                    _,
                    _,
                    file_extension,
                ) = file_handler.split_file_path(output_file_path)
                new_output_file_path = file_handler.file_join(
                    streaming_menu_path,
                    f"{button_index + 1:02}_{button_file_name}",
                    file_extension,
                )

                if (
                    file_handler.rename_file(output_file_path, new_output_file_path)
                    == -1
                ):
                    self._error_message = (
                        f"Failed To Rename {sys_consts.SDELIM}{output_file_path}{sys_consts.SDELIM} To "
                        f"{sys_consts.SDELIM}{new_output_file_path}{sys_consts.SDELIM}"
                    )
                    return -1, self._error_message
            else:  # Copy
                (
                    self._error_code,
                    self._error_message,
                ) = file_handler.copy_file(video_data.video_path, streaming_file)

                if self._error_code == -1:
                    return -1, self._error_message

            return 1, ""

        ##### Main

        assert isinstance(dvd_name, str) and dvd_name.strip() != "", (
            f"{dvd_name=}. Must be a non-empty str"
        )
        assert isinstance(dvd_folder, str) and dvd_folder.strip() != "", (
            f"{dvd_folder=}. Must be a non-empty str"
        )
        assert isinstance(iso_folder, str) and iso_folder.strip() != "", (
            f"{iso_folder=}. Must be a non-empty str"
        )
        assert isinstance(menu_layout, list), (
            f"{menu_layout=} must be a list of tuples of str,Video_Data"
        )

        self._error_code = 1
        self._error_message = ""

        file_handler = file_utils.File()
        video_file_copier = dvdarch_utils.Video_File_Copier()

        dvd_name = Text_To_File_Name(dvd_name)

        archive_path = file_handler.file_join(self.archive_folder, dvd_name)
        streaming_path = file_handler.file_join(self.streaming_folder, dvd_name)

        # Perform safety checks and setup folders
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

        if not file_handler.path_exists(self.streaming_folder):
            self._error_message = (
                "Can Not Access Streaming Folder :"
                f" {sys_consts.SDELIM}{self.streaming_folder}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return -1, self._error_message

        if not file_handler.path_writeable(self.streaming_folder):
            self._error_message = (
                "Can Not Write To Streaming Folder :"
                f" {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
            )
            self._error_code = -1
            return -1, self._error_message

        if file_handler.path_exists(archive_path) and not overwrite_existing:
            self._error_message = (
                "Archive Folder Already Exists :"
                f" {sys_consts.SDELIM}{archive_path}{sys_consts.SDELIM}"
            )
            self._error_code = -1

            return -1, self._error_message

        if file_handler.path_exists(streaming_path) and not overwrite_existing:
            self._error_message = (
                "Streaming Folder Already Exists :"
                f" {sys_consts.SDELIM}{streaming_path}{sys_consts.SDELIM}"
            )
            self._error_code = -1

            return -1, self._error_message

        if file_handler.path_exists(archive_path):
            self._error_code, message = file_handler.remove_dir_contents(archive_path)

            if self._error_code == -1:
                self._error_message = str(message).replace(
                    archive_path,
                    f"{sys_consts.SDELIM}{archive_path}{sys_consts.SDELIM}",
                )
                return -1, self._error_message

        if file_handler.path_exists(streaming_path):
            self._error_code, message = file_handler.remove_dir_contents(streaming_path)

            if self._error_code == -1:
                self._error_message = str(message).replace(
                    archive_path,
                    f"{sys_consts.SDELIM}{streaming_path}{sys_consts.SDELIM}",
                )
                return -1, self._error_message

        for folder in self._backup_folders:
            if folder == DVD_IMAGE:
                self._error_code, self._error_message = file_handler.copy_dir(
                    src_folder=dvd_folder,
                    dest_folder=file_handler.file_join(archive_path, folder),
                )

                if self._error_code == -1:
                    return -1, self._error_message
            elif folder == ISO_IMAGE:
                self._error_code, self._error_message = file_handler.copy_dir(
                    src_folder=iso_folder,
                    dest_folder=file_handler.file_join(archive_path, folder),
                )

                if self._error_code == -1:
                    return -1, self._error_message
            elif folder == MISC:
                pass
            elif folder == VIDEO_SOURCE:
                # Make the video source folders - preservation master and streaming folders
                preservation_master_folder = file_handler.file_join(
                    archive_path,
                    f"{PRESERVATION_MASTER}_{self.transcode_type.lower()}",
                )

                if self.archive_folder == self.streaming_folder:
                    streaming_folder = file_handler.file_join(
                        streaming_path,
                        f"{STREAMING}",
                    )
                else:
                    streaming_folder = streaming_path

                if (
                    not file_handler.path_exists(preservation_master_folder)
                    and file_handler.make_dir(preservation_master_folder) == -1
                ):
                    self._error_code = -1
                    return (
                        -1,
                        (
                            "Failed To Create Preservation Master Folder :"
                            f" {sys_consts.SDELIM}{preservation_master_folder}{sys_consts.SDELIM}"
                        ),
                    )

                if (
                    not file_handler.path_exists(streaming_folder)
                    and file_handler.make_dir(streaming_folder) == -1
                ):
                    self._error_code = -1
                    return (
                        -1,
                        (
                            "Failed To Create Streaming Folder :"
                            f" {sys_consts.SDELIM}{streaming_folder}{sys_consts.SDELIM}"
                        ),
                    )

                menu_paths = _get_video_file_paths(
                    preservation_master_folder, streaming_folder
                )

                # Iterate through the DVD menu and transcode the source video files
                for menu_path_tuple in menu_paths:
                    preservation_master_tuple = menu_path_tuple[0]
                    streaming_tuple = menu_path_tuple[1]

                    preservation_master_menu_path_temp = preservation_master_tuple[0]
                    menu_video_data = preservation_master_tuple[
                        3
                    ]  # Common to both streaming and preservation master
                    streaming_menu_path = streaming_tuple[1]

                    if (
                        not file_handler.path_exists(preservation_master_menu_path_temp)
                        and file_handler.make_dir(preservation_master_menu_path_temp)
                        == -1
                    ):
                        self._error_code = -1
                        return (
                            -1,
                            (
                                "Failed To Create Preservation Master Folder"
                                f" :{sys_consts.SDELIM}{preservation_master_menu_path_temp}{sys_consts.SDELIM}"
                            ),
                        )

                    if (
                        not file_handler.path_exists(streaming_menu_path)
                        and file_handler.make_dir(streaming_menu_path) == -1
                    ):
                        self._error_code = -1
                        return (
                            -1,
                            (
                                "Failed To Create Streaming Folder"
                                f" :{sys_consts.SDELIM}{streaming_menu_path}{sys_consts.SDELIM}"
                            ),
                        )

                    for index, video_data in enumerate(menu_video_data):
                        button_file_name = (
                            Text_To_File_Name(
                                video_data.video_file_settings.button_title
                            )
                            if video_data.video_file_settings.button_title.strip() != ""
                            else video_data.video_file
                        )

                        self._error_code, self._error_message = _transcode_video_file(
                            video_data=video_data,
                            preservation_master_path=preservation_master_menu_path_temp,
                            streaming_path=streaming_menu_path,
                            transcode_type=self.transcode_type,
                            button_file_name=button_file_name,
                            button_index=index,
                        )

                        if self._error_code == -1:
                            return -1, self._error_message

                # Copy the transcoded video files to their final location
                for menu_path_tuple in menu_paths:
                    preservation_master_tuple = menu_path_tuple[0]
                    preservation_master_menu_path_temp = preservation_master_tuple[0]
                    preservation_master_menu_path = preservation_master_tuple[1]
                    menu_title = preservation_master_tuple[
                        2
                    ]  # Common to both streaming and preservation master

                    result, message = video_file_copier.copy_folder_into_folders(
                        source_folder=preservation_master_menu_path_temp,
                        destination_root_folder=preservation_master_menu_path,
                        menu_title=menu_title,
                        folder_size_gb=(
                            4
                            if self.archive_size == sys_consts.DVD_ARCHIVE_SIZE
                            else 25
                        ),  # sys_consts.BLUERAY_ARCHIVE_SIZE
                    )

                    if result == -1:
                        return -1, message

                    # Remove temporary folders and associated sub folders/files
                    if file_handler.path_exists(preservation_master_menu_path_temp):
                        result, message = file_handler.remove_dir_contents(
                            preservation_master_menu_path_temp
                        )

                        if result == -1:
                            return -1, message
        return 1, ""
