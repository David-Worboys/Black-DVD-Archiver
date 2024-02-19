"""
This module provides file based utilities and a wrapper around commonly used os and Path methods that make
using them more concise whilst providing better error handling

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
import enum
import os
import pathlib
import shutil
import sys

import titlecase

# fmt: on


@dataclasses.dataclass(slots=True)
class File_Result:
    files: list[str]
    path: str
    error_code: enum.IntEnum
    error_message: str


def App_Path(file_name: str = "", trailing_slash=False) -> str:
    """Returns the full app directory path for the supplied file_name.  Handles pyinstaller.Nuitka runtime directory
    Args:
        file_name (str, optional): Defaults to "". file name that needs to be prepended with the app path
        trailing_slash(bool): Whether to append a platform appropriate trailing slash to the end of the path.
    Returns:
        str: Expanded app directory path if the file name is supplied. The app directory path if the file name is not supplied
    """

    assert isinstance(file_name, str), f"file_name <{file_name}> must be str"

    if (
        getattr(sys, "frozen", False)
        and hasattr(sys, "_MEIPASS")
        or globals().get("__compiled__", False)
    ):  # Pyinstaller handling
        if globals().get("__compiled__", False) and globals().get("__spec__", False):
            application_path = globals()["__spec__"].origin
            application_path = os.path.dirname(application_path)
        elif globals().get("__compiled__", False):
            application_path = os.getcwd()
        else:
            application_path: str = sys._MEIPASS  # type: ignore
        # running_mode = 'Frozen/executable'
        # print("Running Frozen")
    else:
        try:
            app_full_path = os.path.abspath(
                __file__
            )  # realpath does not work with symbolic links
            application_path = os.path.dirname(app_full_path)
            # running_mode = "Non-interactive
        except NameError:
            application_path = os.getcwd()
            # running_mode = 'Interactive'

    if file_name.strip() == "":
        return (
            f"{application_path}{os.pathsep}"
            if trailing_slash
            else f"{application_path}"
        )

    return (
        f"{os.path.join(application_path, file_name)}{os.pathsep}"
        if trailing_slash
        else f"{os.path.join(application_path, file_name)}"
    )


def Special_Path(special_path_name: str) -> str:
    """Translates a special path name to a path (Desktop, Documents, Pictures etc.)
    Args:
        special_path_name (str): The special path name
    Returns:
        str : Either a full path in linux or a location sourced from the registery in windows
    """
    special_paths: dict[str, tuple[str, str]] = {
        "Desktop": (
            "Desktop",
            "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
        ),
        "Documents": (
            "Documents",
            "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
        ),
        "Downloads": (
            "Downloads",
            "{374DE290-123F-4565-9164-39C4925E467B}",
        ),
        "Music": ("Music", "{4BD8D571-6D19-48D3-BE97-422220080E43}"),
        "Pictures": (
            "Pictures",
            "{A990AE9F-A03B-4E80-94BC-9912D7504104}",
        ),
        "Videos": ("Videos", "{file_handler}"),
    }

    special_names = ""

    for path_name in special_paths:
        special_names += f"{path_name},"

    if special_path_name not in special_paths:
        return ""

    if os.name == "nt":  # windows
        import winreg

        sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, special_paths[special_path_name][1])[0]
        return location

    # Linux or Mac
    return os.path.join(os.path.expanduser("~"), special_paths[special_path_name][0])


class File:
    class Path_Error(enum.IntEnum):
        """File class methods provide an easy-to-use wrapper around file info/manipulation calls"""

        OK = 1
        EXCEPTION = -1
        NOTEXIST = -2
        NOTIMPLEMENTED = -3
        NOTWRITEABLE = -4

    Error_Dict = {
        Path_Error.OK: "OK",
        Path_Error.EXCEPTION: "",
        Path_Error.NOTEXIST: "Path Does Not Exist",
        Path_Error.NOTIMPLEMENTED: "Not Implemented",
        Path_Error.NOTWRITEABLE: "Path Not Writeable",
    }

    @property
    def ossep(self) -> str:
        """Returns the OS file path seperator - Window = \\  Linux/Mac = /
        Returns:
            str: The OS seperator character
        """
        return os.path.sep

    def extract_title(self, name: str, excluded_words: list | None = None) -> str:
        """
        Extracts the title from a given file name by removing the file extension, replacing unwanted characters,
        and formatting the resulting string into title case.

        Args:
            name (str): The file name to extract the title from.
            excluded_words (list[str]) : The words to exclude
        Returns:
            str: The extracted title or the name if a title could not be extracted.
        """

        if excluded_words is None:
            excluded_words = []

        assert (
            isinstance(name, str) and name.strip() != ""
        ), f"{name=}. Must be a non-empty str"
        assert all(isinstance(word, str) for word in excluded_words)

        words = []
        numbers = []

        for token in name.replace("_", " ").replace(".", " ").split(" "):
            word = []
            number = []

            for char in token:
                if char == "-":
                    number.append(char)
                elif char.isalpha():
                    word.append(char)
                elif char.isdigit():
                    number.append(char)
            if word:
                words.append("".join(word))

            if number:
                numbers.append("".join(number))

        title = " ".join([
            titlecase.titlecase(text)
            for text in words
            if text.upper() not in [excluded.upper() for excluded in excluded_words]
        ])

        if not title.strip():
            title = name

        return title

    def copy_file(self, source: str, destination_path: str) -> tuple[int, str]:
        """
        Copy a file from the source path to the destination path.
        Args:
            source (str): The source path of the file to copy.
            destination_path (str): The destination path where the file will be copied.
        Returns:
            tuple[int, str]:
                - arg1: 1 for success, -1 for failure.
                - arg2: An error message, or an empty string if successful.
        """

        assert (
            isinstance(source, str) and source.strip()
        ), f"Invalid source path: {source}"
        assert (
            isinstance(destination_path, str) and destination_path.strip()
        ), f"Invalid destination path: {destination_path}"

        if not os.path.exists(source):
            return -1, f"File not found: {source}"
        if os.path.isdir(source):
            return -1, f"Source path is a directory: {source}"

        if not os.path.exists(os.path.dirname(destination_path)):
            return (
                -1,
                f"Destination path does not exist: {os.path.dirname(destination_path)}",
            )

        if os.path.abspath(source) == os.path.abspath(destination_path):
            return -1, "Source and destination paths cannot be the same."

        try:
            shutil.copy2(source, destination_path)
            return 1, ""
        except Exception as e:
            return -1, f"Error copying file: {e}"

    def copy_dir(self, src_folder: str, dest_folder: str) -> tuple[int, str]:
        """
        Copies the folder structure and files from the source folder to the destination folder.
        Args:
            src_folder (str): The path of the source folder to copy.
            dest_folder (str): The path of the destination folder to copy to.
        Returns:
            tuple[int,str]:
            - arg1 1: ok, -1: fail
            - arg2: error message or "" if ok
        """
        assert (
            isinstance(src_folder, str) and src_folder.strip() != ""
        ), f"{src_folder=}. Must be a non-empty str"
        assert (
            isinstance(dest_folder, str) and dest_folder.strip() != ""
        ), f"{dest_folder=}. Must be a non-empty str"

        if not os.path.isdir(src_folder):
            return -1, f"{src_folder} Is Not A Valid Directory Path."

        if os.path.exists(dest_folder):
            return -1, f"{dest_folder} Already Exists."

        if os.path.abspath(src_folder) == os.path.abspath(dest_folder):
            return -1, "Source And Destination Folder Cannot Be The same."

        try:
            os.makedirs(dest_folder)
        except OSError as e:
            return -1, f"Error Creating {dest_folder}. {e}"

        for dirpath, dirnames, filenames in os.walk(src_folder):
            # create the corresponding subdirectories in the destination folder
            for dirname in dirnames:
                src_path = os.path.join(dirpath, dirname)
                dst_path = os.path.join(
                    dest_folder, os.path.relpath(src_path, src_folder)
                )

                try:
                    os.makedirs(dst_path, exist_ok=True)
                except OSError as e:
                    return -1, f"Error Creating Directory {dst_path}. {e}"

            # copy the files to the corresponding subdirectories in the destination folder
            for filename in filenames:
                src_path = os.path.join(dirpath, filename)
                dst_path = os.path.join(
                    dest_folder, os.path.relpath(src_path, src_folder)
                )
                try:
                    shutil.copy2(src_path, dst_path)
                except OSError as e:
                    return -1, f"Error Copying File {src_path} To {dst_path}. {e}"

        return 1, ""

    @staticmethod
    def file_exists(
        directory_path: str, file_name: str = "", file_extension: str = ""
    ) -> bool:
        """Determines if a file exists and is a regular file
        Args:
            directory_path (str): The path to the directory containing the file
            file_name (str): The name of the file
            file_extension (str): The extension of the file
        Returns:
            bool: True if file exists, False if not
        """
        assert (
            isinstance(directory_path, str) and directory_path.strip() != ""
        ), f"{directory_path=} must be a non-empty str"
        assert isinstance(file_name, str), f"{file_name=} must be a str"
        assert isinstance(file_extension, str), f"{file_extension=} must be a str"

        if file_name == "":
            directory_path, file_name = os.path.split(directory_path)
            file_name, file_extension = os.path.splitext(file_name)

        file_suffix = (
            "." + file_extension
            if file_extension and not file_extension.startswith(".")
            else file_extension
        )
        file_path = os.path.join(directory_path, file_name + file_suffix)

        try:
            return os.path.isfile(file_path)
        except FileNotFoundError:
            return False

    def file_join(self, dir_path: str, file_name: str, ext: str = "") -> str:
        """Join a directory, filename, and extension string to construct a file path.

        Args:
            dir_path (str): A string representing the directory path where the file will be saved.
            file_name (str): A string representing the name of the file.
            ext (str): An optional string representing the extension of the file, including the leading dot.
                If not provided, the resulting file path will not have a proper file extension.
        Returns:
            A string representing the full file path constructed from the directory, filename, and extension.
        """
        assert (
            isinstance(dir_path, str) and dir_path.strip() != ""
        ), f"{dir_path=}. Must be a non-empty str"
        assert (
            isinstance(file_name, str) and dir_path.strip() != ""
        ), f"{file_name=}. Must be a non-empty str"
        assert isinstance(ext, str), f"{ext=}. Must be a str"

        if ext and not ext.startswith("."):
            ext = "." + ext

        file_path = os.path.join(dir_path, file_name + ext)

        if not self.filename_validate(file_name):
            raise RuntimeError(f"{file_name=}. Is Invalid")

        return file_path

    def filename_validate(self, file_name: str) -> bool:
        """
        Basic check to see if file name is valid. Might need beefing up later
        Args:
            file_name (str): The file name to check for validity.
        Returns:
            bool: True if the file name is valid, False otherwise.
        """
        assert (
            isinstance(file_name, str) and file_name.strip() != ""
        ), f"{file_name=}. Must be a non-empty str"

        # Check if the file name is empty or too long
        if not file_name or len(file_name) > os.pathconf("/", "PC_NAME_MAX"):
            return False

        # Check for invalid characters
        for char in file_name:
            if char in r'\/:*?"<>|,':
                return False

        # Check for reserved file names on Windows
        if os.name == "nt":
            # fmt: off
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3',
                            'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6',
                            'LPT7', 'LPT8', 'LPT9']
            # fmt: on
            if file_name.upper() in reserved_names:
                return False

        # All checks passed, the file name is valid
        return True

    def filelist(
        self, path: str, extensions: list[str] | tuple[str, ...]
    ) -> File_Result:
        """
        Returns a list of files found in the path location. If the path is a file then all files matching the
        extension(s) in that files directory are returned.
        Args:
            path (str): File system path.
            extensions (list[str] | tuple[str, ...]): A list or tuple of file extensions.
        Returns:
            File_Result: A dataclass containing a list of files, the path, and any errors encountered.
        """
        assert (
            isinstance(path, str) and path.strip() != ""
        ), f"{path=}. Must be a non-empty str"
        assert isinstance(
            extensions, (list, tuple)
        ), f"{extensions=}. Must be a list or tuple of str"
        assert all(
            isinstance(extension, str) for extension in extensions
        ), f"{extensions=}.All elements must be str"

        file_extensions = [extension.lower() for extension in extensions]

        try:
            if os.path.exists(path):
                path_ptr = os.path.abspath(path)

                if os.path.isfile(path_ptr):
                    path_ptr = os.path.dirname(path_ptr)

                file_list = [
                    file
                    for file in os.listdir(path_ptr)
                    if os.path.isfile(os.path.join(path_ptr, file))
                    and (
                        not file_extensions
                        or os.path.splitext(file)[1][1:].lower() in file_extensions
                    )
                ]

                return File_Result(
                    files=file_list,
                    path=path_ptr,
                    error_code=self.Path_Error.OK,
                    error_message=self.Error_Dict[self.Path_Error.OK],
                )

            return File_Result(
                files=[],
                path=path,
                error_code=self.Path_Error.NOTEXIST,
                error_message=self.Error_Dict[self.Path_Error.NOTEXIST],
            )
        except OSError as error:
            return File_Result(
                files=[],
                path=path,
                error_code=self.Path_Error.EXCEPTION,
                error_message=str(error),
            )

    @staticmethod
    def make_dir(file_path: str) -> int:
        """Makes a directory (folder) in the file path
        Args:
            file_path (str): The file path housing the new folder
        Returns:
            int : 1 if successful, -1 if failed to create directory
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=} must be a non-empty str"

        try:
            os.makedirs(file_path)
            return 1
        except FileExistsError:
            return 1  # folder already exists
        except Exception:
            return -1

    @staticmethod
    def path_exists(file_path: str) -> bool:
        """Determines if a file path exists
        Args:
            file_path (str): The file path to check
        Returns:
            bool: True - The file path exists, False - it does not
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=} must be a non-empty str"

        try:
            path = pathlib.Path(file_path)

            if path.is_dir() or path.is_file():
                return True

            return False
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError)):
                return False
        return False

    @staticmethod
    def path_writeable(file_path: str) -> bool:
        """Checks if a file path can be written to
        Args:
            file_path (str): The file path to check for write ability
        Returns:
            bool : True - Can write to file path, False - Cannot Write to file path
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a non-empty str"

        if os.access(file_path, os.W_OK):
            return True
        return False

    def rename_file(self, old_file_path: str, new_file_path: str):
        """
        Renames a file
        Args:
            old_file_path: A string representing the path of the file to be renamed.
            new_file_path: A string representing the new path of the renamed file.
        Returns:
            Returns 1 if the file was successfully renamed, and -1 if an error occurred.
        """
        assert (
            isinstance(old_file_path, str) and old_file_path.strip() != ""
        ), f"{old_file_path=}. Must be a non-empty str"
        assert (
            isinstance(new_file_path, str) and new_file_path.strip() != ""
        ), f"{new_file_path=}. Must be a non-empty str"

        old_path, old_name, old_extension = self.split_file_path(old_file_path)
        new_path, _, _ = self.split_file_path(new_file_path)

        if (
            self.file_exists(old_path, old_name, old_extension)
            and self.path_exists(new_path)
            and self.path_writeable(new_path)
        ):
            try:
                os.rename(old_file_path, new_file_path)
                return 1
            except OSError:
                return -1
        return -1

    def split_head_tail(self, file_path_name: str) -> tuple[str, str]:
        """Takes a full file path - including the file name and splits it into the file path and the file name
        Note: Deprecated use split_file_path
        Args:
            file_path_name (str): The full file path - including the file name
        Returns:
            tuple[str,str] : First element is the file path, second element is the file name.
            - Both are empty strings if something goes wrong
        """
        assert (
            isinstance(file_path_name, str) and file_path_name.strip() != ""
        ), f"{file_path_name=}. Must be a non-empty str"

        if os.path.isdir(file_path_name):
            return file_path_name, ""
        elif os.path.isfile(file_path_name):
            path, file = os.path.split(file_path_name)

            file_prefix, file_suffix = os.path.splitext(file)
            if self.file_exists(
                directory_path=path, file_name=file_prefix, file_extension=file_suffix
            ):
                return path, file
            else:
                return "", ""

        return "", ""

    def split_file_path(
        self, file_path_name: str, no_path_check: bool = False
    ) -> tuple[str, str, str]:
        """Splits a file path into its directory path, file name , and file extension.
        Args:
            file_path_name (str): The file path to split.
            no_path_check (bool): Processes file_path_name without checking if it exists. Assumes it is a file name!
        Returns:
            tuple: A tuple of three strings - directory path, file name , and file extension.
        """
        assert (
            isinstance(file_path_name, str) and file_path_name.strip() != ""
        ), f"{file_path_name=}. Must be a non-empty str"

        if not no_path_check and os.path.isdir(file_path_name):
            return file_path_name, "", ""
        elif not no_path_check or os.path.isfile(file_path_name):
            path, file = os.path.split(file_path_name)

            file_prefix, file_suffix = os.path.splitext(file)
            if not no_path_check or self.file_exists(
                directory_path=path, file_name=file_prefix, file_extension=file_suffix
            ):
                return path, file_prefix, file_suffix
            else:
                return "", "", ""

        return "", "", ""

    def remove_dir_contents(self, file_path: str, keep_parent=False) -> tuple[int, str]:
        """Removes a directory and all its contents - specified by file_path.

        Args:
            file_path (str): The file path of the directory to be removed.
            keep_parent (bool): True - Keeps the parent file_path, removes sub-folders and files, False otherwise blow
                                the file_path away and all sub-folders and files

        Returns:
            tuple[int,str]:
            - arg1 1: ok, -1: fail
            - arg2: error message or "" if ok
        """

        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=}. Must be a non-empty str"

        if not os.path.exists(file_path):
            return -1, f"{file_path} Does Not Exist."
        elif not os.access(file_path, os.W_OK):
            return -1, f"No Write Access To {file_path}."

        try:
            # Iterate through all the entries within the directory and delete them
            with os.scandir(file_path) as entries:
                for entry in entries:
                    if entry.is_dir() and not entry.is_symlink():
                        # Recursively delete directories using shutil.rmtree()
                        shutil.rmtree(entry.path)
                    else:
                        # Delete files using os.remove()
                        os.remove(entry.path)

                if not keep_parent:
                    # Remove the parent directory
                    shutil.rmtree(file_path)

        except (OSError, PermissionError, FileNotFoundError) as error:
            return -1, f"Failed To Remove Dir/Contents: {str(error)}"

        return 1, ""

    def remove_file(self, file_path: str) -> int:
        """Removes a file at the specified path.
        Args:
            file_path (str): The path of the file to remove.
        Returns:
            int: 1 if the file was successfully removed, -1 otherwise.
        """
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=} must be a non-empty string."
        assert (
            isinstance(file_path, str) and file_path.strip() != ""
        ), f"{file_path=} must be a non-empty string."

        try:
            path = pathlib.Path(file_path)

            if path.exists():
                path.unlink()
                if not path.exists():
                    return 1  # File was successfully removed.
                else:
                    return -1  # File still exists after unlinking.
            else:
                return -1  # File does not exist.
        except FileNotFoundError:
            return -1  # File does not exist at the given path.
        except PermissionError:
            return -1  # Permission error occurred during removal.
        except OSError:
            return -1  # Other OS-related error occurred during removal.
        except Exception:
            return (
                -1
            )  # Catching any other unexpected exception for logging and debugging.

    def write_list_to_txt_file(
        self, str_list: list[str], text_file: str
    ) -> tuple[int, str]:
        """Writes a list of strings to a text file.
        Args:
            str_list (List[str]): The list of strings to write to the text file.
            text_file (str): The file path to the text file.
        Returns:
            tuple[int, str]: A tuple containing an integer status code and a string error message, if any.
                The status code is 1 if the write was successful, and -1 if there was an error.
        """
        assert isinstance(str_list, list) and all(
            isinstance(item, str) for item in str_list
        ), f"{str_list=} must be a list of str"
        assert (
            isinstance(text_file, str) and text_file.strip() != ""
        ), f"{text_file=} must be a non-empty str"

        try:
            with open(text_file, "w") as f:
                for text in str_list:
                    f.write(f"{text}\n")
            return 1, ""
        except IOError as e:
            return -1, f"Error writing file list to {text_file}: {e}"
