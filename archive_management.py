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
from datetime import datetime

import sys_consts
import utils

# fmt: on

# Following used in archive_dvd_build method below - changes here mean changes there!
DVD_IMAGE = "dvd_image"
ISO_IMAGE = "iso_image"
VIDEO_SOURCE = "video_source"
MISC = "misc"


@dataclasses.dataclass
class Archive_Manager:
    """Manages archiving of video artefacts - dvd_image, video source files etc"""

    archive_folder: str

    # Private instance variables
    _error_message: str = ""
    _backup_folders: tuple[str] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        assert (
            isinstance(self.archive_folder, str) and self.archive_folder.strip() != ""
        ), f"{self.archive_folder=}. Must Be non-empty str"

        self._backup_folders = (DVD_IMAGE, ISO_IMAGE, VIDEO_SOURCE, MISC)
        self._error_message = self._make_folder_structure()

    @property
    def get_error(self) -> str:
        return self._error_message

    def _make_folder_structure(self) -> str:
        """Makes the archive folder structure

        Returns:
            str : An error message if the folder structure caould not be created
        """
        file_handler = utils.File()

        if not file_handler.path_exists(self.archive_folder):
            if file_handler.make_dir(self.archive_folder) == -1:
                self._error_message = f"Failed To Create Archive Folder {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
                return self._error_message

            now = datetime.now()
            readme_file = f"{self.archive_folder}{file_handler.ossep}README.txt"

            try:
                with open(readme_file, "w") as file:
                    file.write(
                        f"{now} \n Video Archive Folder Created By {sys_consts.PROGRAM_NAME} - {sys_consts.VERSION_TAG} \n Do Not Delete!"
                    )
            except:
                self._error_message = f"Failed To Write {readme_file} "

    def archive_dvd_build(
        self,
        dvd_name: str,
        dvd_folder: str,
        iso_folder: str,
        source_video_files: list[str],
        overwrite_existing: bool = True,
    ) -> tuple[int, str]:
        """
        Archives a DVD build and its source video files.

        Args:
            dvd_name (str): The name of the DVD.
            dvd_folder (str): The file path of the folder where the DVD build was created.
            source_video_files (list[str]): A list of file paths for the source video files to be included in the DVD.
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
        assert (
            isinstance(source_video_files, list) and source_video_files != []
        ), f"{source_video_files=}. Must be a non-empty list of str"
        assert all(
            isinstance(file_path, str) for file_path in source_video_files
        ), "source_video_files list must only contain strings"

        file_handler = utils.File()

        backup_path = f"{self.archive_folder}{file_handler.ossep}{dvd_name}"

        if not file_handler.path_exists(dvd_folder):
            self._error_message = f"Can Not Access DVD Folder : {sys_consts.SDELIM}{dvd_folder}{sys_consts.SDELIM}"
            return -1, self._error_message

        if not file_handler.path_exists(iso_folder):
            self._error_message = f"Can Not Access ISO Folder : {sys_consts.SDELIM}{iso_folder}{sys_consts.SDELIM}"
            return -1, self._error_message

        if not file_handler.path_exists(self.archive_folder):
            self._error_message = f"Can Not Access Archive Folder : {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
            return -1, self._error_message

        if not file_handler.path_writeable(self.archive_folder):
            self._error_message = f"Can Not Write To Archive Folder : {sys_consts.SDELIM}{self.archive_folder}{sys_consts.SDELIM}"
            return -1, self._error_message

        if file_handler.path_exists(backup_path) and not overwrite_existing:
            self._error_message = f"Backup Folder Already Exists : {sys_consts.SDELIM}{sys_consts.SDELIM}{sys_consts.SDELIM}"

            return -1, self._error_message

        if file_handler.path_exists(backup_path):
            result, message = file_handler.remove_dir_contents(backup_path)

            if result == -1:
                self._error_message = str(message).replace(
                    backup_path,
                    f"{sys_consts.SDELIM}{sys_consts.SDELIM}{sys_consts.SDELIM}",
                )
                return -1, self._error_message

        if file_handler.make_dir(dvd_name) == -1:
            return (
                -1,
                f"Failed To Create Backup Folder : {sys_consts.SDELIM}{dvd_name}{sys_consts.SDELIM}",
            )

        for folder in self._backup_folders:
            backup_item_folder = f"{backup_path}{file_handler.ossep}{folder}"

            if folder == DVD_IMAGE:
                result, message = file_handler.copy_dir(
                    src_folder=dvd_folder, dest_folder=backup_item_folder
                )

                if result == -1:
                    return -1, message
            elif folder == ISO_IMAGE:
                result, message = file_handler.copy_dir(
                    src_folder=iso_folder, dest_folder=backup_item_folder
                )
            elif folder == MISC:
                pass
            elif folder == VIDEO_SOURCE:
                if file_handler.make_dir(backup_item_folder) == -1:
                    return -1, f"Failed To Create Backup Folder : {backup_item_folder}"

                for source_file in source_video_files:
                    result, message = file_handler.copy_file(
                        source_file, backup_item_folder
                    )

        return 1, ""
