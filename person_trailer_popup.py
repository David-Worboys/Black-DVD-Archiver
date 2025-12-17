"""
Implements a popup dialog that allows users to enter a persons details for a trailer video.

Copyright (C) 2025  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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
import pprint
import uuid
from typing import Final

import PySide6.QtCore as qtC
import PySide6.QtGui as qtG

import QTPYGUI.file_utils as file_utils
import QTPYGUI.popups as popups
import QTPYGUI.qtpygui as qtg
import QTPYGUI.sqldb as sqldb
import QTPYGUI.utils as utils
import sys_consts

from QTPYGUI.qtpygui import Combo_Item, Combo_Data

from dvdarch_utils import (
    Get_Fonts,
    Get_Color_Names,
    Overlay_Text,
    Generate_People_Trailer,
)

NEW_PERSON: Final[str] = "New Person"


@dataclasses.dataclass
class Trailer_Person:
    """
    Represents a person associated with a trailer video.
    """

    # Private Variables
    _unique_id: str = str(uuid.uuid4())

    _surname: str = ""
    _first_name: str = ""
    _other_names: str = ""
    _maiden_name: str = ""
    _dob: str = ""
    _dod: str = ""
    _comment: str = ""

    @property
    def surname(self) -> str:
        """
        The primary family name of the person.

        Returns:
            str : The persons surname
        """
        return self._surname.strip()

    @surname.setter
    def surname(self, value: str):
        """
        The primary family name of the person.

        Args:
            value(str): The primary family name

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._surname = value

    @property
    def first_name(self) -> str:
        """
        The primary given name of the person.

        Returns:
            str: The persons first name
        """
        return self._first_name.strip()

    @first_name.setter
    def first_name(self, value: str):
        """
        The primary given name of the person.

        Args:
            value(str): The primary given name

        """

        self._first_name = value

    @property
    def other_names(self) -> str:
        """
        Any middle names or other given names.

        Returns:
            str: The persons other names
        """
        return self._other_names.strip()

    @other_names.setter
    def other_names(self, value: str):
        """
        Any middle names or other given names.

        Args:
            value(str): Middle names or other given names

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._other_names = value

    @property
    def maiden_name(self) -> str:
        """
        The person's maiden name (birth name), if applicable.

        Returns:
            str : Persons maiden name
        """
        return self._maiden_name.strip()

    @maiden_name.setter
    def maiden_name(self, value: str):
        """
        The persons maiden name (birth name), if applicable

        Args:
            value(str): maiden name (birth name), if applicable

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._maiden_name = value

    @property
    def comment(self) -> str:
        """

        Returns:
            str: The comment value

        """
        return self._comment

    @comment.setter
    def comment(self, value: str):
        assert isinstance(value, str), f"{value=}. Must be str"

        self._comment = value

    @property
    def dob(self) -> str:
        """
        The person's date of birth (DOB). Format is typically YYYY-MM-DD.

        Returns:
            str: The date of birth
        """
        return self._dob.strip().replace("//", "")

    @dob.setter
    def dob(self, value: str):
        """
        The person's date of birth (DOB). Format is typically YYYY-MM-DD.

        Args:
            value(str): persons date of birth

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._dob = value

    @property
    def dod(self) -> str:
        """
        The person's date of death (DOD). Format is typically YYYY-MM-DD.

        Returns:
            str : The date of death
        """
        return self._dod.strip().replace("//", "")

    @dod.setter
    def dod(self, value: str):
        """
        The person's date of death (DOD). Format is typically YYYY-MM-DD.

        Args:
            value(str): persons date of death

        """
        assert isinstance(value, str), f"{value=}. Must be str"

        self._dod = value

    @property
    def date_label(self) -> str:
        """
        Generates a concise date label for the individual.

        Returns:
            str: Date label of individual (e.g., "1920-01-01 - 2000-12-31" or "DOB 1980-05-15").
        """
        if self.dob and self.dod:
            return f"{self.dob} - {self.dod}"
        elif self.dob:
            return f"DOB {self.dob}"
        elif self.dod:
            return f"DOD {self.dod}"

        return ""

    @property
    def details(self) -> str:
        """
        Get the trailer persons formatted details

        Returns:
            str: Person details

        """
        details = ""

        if self.first_name:
            details += f"{self.first_name} "

        if self.other_names:
            details += f"{self.other_names} "

        if self.surname:
            details += f"{self.surname.upper()}"

        # Trim leading/trailing whitespace from names
        details = details.strip()

        if self.maiden_name:
            # We add it on a new line and ensure it has a space before the parenthesis
            details += f"\n(née {self.maiden_name.upper()})"

        if self.date_label:
            # Add the date range on a new line
            details += f"\n{self.date_label}"
        if self.comment:
            details += f"\n{self.comment}"

        return details.strip()

    @property
    def unique_id(self) -> str:
        """
        Returns the persons unique id

        Returns:
            str : Unique_id

        """

        return self._unique_id


@dataclasses.dataclass
class Person_Trailer_Popup(qtg.PopContainer):
    """Generates a persons image for a trailer video"""

    person_image: qtG.QPixmap = None
    output_folder: str = ""
    tag: str = "Person_Trailer_Popup"
    project_name: str = ""
    frame_rate: float = -1.0
    aspect_ratio: str = ""

    # Private instance variables
    # DB stuff
    _db_settings: sqldb.App_Settings = None
    _sql_shelf: sqldb.SQL_Shelf = None
    _open_flag: bool = False

    ## Controls
    _existing_image_combo: qtg.ComboBox = None
    _text_font_combo: qtg.ComboBox = None
    _text_colour_combo: qtg.ComboBox = None
    _text_background_colour_combo: qtg.ComboBox = None
    _text_font_size_spin: qtg.Spinbox = None
    _text_background_transparency_spin: qtg.Spinbox = None
    _trailer_people_combo: qtg.ComboBox = None

    _text_font_size: int = -1
    _text_background_transparency: int = -1
    _text_font: str = ""
    _text_colour: str = ""
    _text_background_colour: str = ""

    _person_image: qtg.Image = None

    _surname: qtg.LineEdit = None
    _first_name: qtg.LineEdit = None
    _other_names: qtg.LineEdit = None
    _maiden_name: qtg.LineEdit = None
    _comment: qtg.LineEdit = None
    _dob: qtg.LineEdit = None
    _dod: qtg.LineEdit = None

    _trailer_people: dict = dataclasses.field(default_factory=dict)
    _current_trailer_person_id: str = ""
    _file_handler: file_utils.File = file_utils.File()

    def __post_init__(self) -> None:
        """Sets-up the form"""
        assert isinstance(self.person_image, qtG.QPixmap), (
            f"{self.person_image=}. Must be a QPixmap"
        )
        assert isinstance(self.output_folder, str) and self.output_folder != "", (
            f"{self.output_folder=}.  Must be a non-empty str"
        )
        assert isinstance(self.project_name, str) and self.project_name != "", (
            f"{self.project_name=}.  Must be a non-empty str"
        )
        assert isinstance(self.frame_rate, float) and self.frame_rate in (
            sys_consts.PAL_FRAME_RATE,
            sys_consts.NTSC_FRAME_RATE,
            sys_consts.PAL_FIELD_RATE,
            sys_consts.NTSC_FIELD_RATE,
        ), f"{self.frame_rate=}.  Must be PAL or NTSC frame rates"
        assert isinstance(self.aspect_ratio, str) and self.aspect_ratio in (
            sys_consts.AR43,
            sys_consts.AR169,
        ), (
            f"{self.aspect_ratio=}. Must be either {sys_consts.AR43=} or {sys_consts.AR169=}"
        )

        self.container = self.layout()

        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
        self._sql_shelf = sqldb.SQL_Shelf(db_name=sys_consts.PROGRAM_NAME)

        # self._error_message = sql_shelf.error.message
        # self._error_code = sql_shelf.error.code

        if self._db_settings.setting_exist(sys_consts.PERSON_FONT_DBK):
            self._text_font = self._db_settings.setting_get(sys_consts.PERSON_FONT_DBK)

        if self._db_settings.setting_exist(sys_consts.PERSON_FONT_COLOUR_DBK):
            self._text_colour = self._db_settings.setting_get(
                sys_consts.PERSON_FONT_COLOUR_DBK
            )
        if self._db_settings.setting_exist(sys_consts.PERSON_BACKGROUND_COLOUR_DBK):
            self._text_background_colour = self._db_settings.setting_get(
                sys_consts.PERSON_BACKGROUND_COLOUR_DBK
            )

        if self._db_settings.setting_exist(sys_consts.PERSON_FONT_POINT_SIZE_DBK):
            self._text_font_size = int(
                self._db_settings.setting_get(sys_consts.PERSON_FONT_POINT_SIZE_DBK)
            )
        else:  # default
            self._text_font_size = 12

        if self._db_settings.setting_exist(
            sys_consts.PERSON_BACKGROUND_TRANSPARENCY_DBK
        ):
            self._text_background_transparency = int(
                self._db_settings.setting_get(
                    sys_consts.PERSON_BACKGROUND_TRANSPARENCY_DBK
                )
            )
        else:  # default
            self._text_background_transparency = 0

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  form events

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    if self._text_font:
                        text = ""

                        # text_font has a file path
                        if "/" in self._text_font:  # Linux
                            text = self._text_font.split("/")[-1]
                        elif "\\" in self._text_font:  # Windows
                            text = self._text_font.split("\\")[-1]

                        if text:
                            self._text_font_combo.select_text(text, partial_match=False)

                    if self._text_colour:
                        self._text_colour_combo.select_text(
                            self._text_colour, partial_match=False
                        )
                    else:
                        self._text_colour_combo.select_text("blue", partial_match=False)

                    if self._text_background_colour:
                        self._text_background_colour_combo.select_text(
                            self._text_background_colour, partial_match=False
                        )
                    else:
                        self._text_background_colour_combo.select_text(
                            "wheat", partial_match=False
                        )
                    if self._text_font_size > 0:
                        self._text_font_size_spin.value_set(self._text_font_size)

                    if self._text_background_transparency > 0:
                        self._text_background_transparency_spin.value_set(
                            self._text_background_transparency
                        )

                    self._trailer_people = self._sql_shelf.open(
                        sys_consts.TRAILER_PEOPLE_SHELF
                    )

                    self._load_trailer_people_combo()
                    self._load_existing_images_combo()

                    self._open_flag = True
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        if self._process_ok(event) == 1:
                            self.set_result(event.tag)
                            super().close()
                    case "delete_image":
                        image_data = self._existing_image_combo.value_get()

                        if image_data.data and self._file_handler.path_exists(
                            image_data.data
                        ):
                            if (
                                popups.PopYesNo(
                                    title="Delete File...",
                                    message=f"Delete {sys_consts.SDELIM}{image_data.display}{sys_consts.SDELIM}?",
                                ).show()
                                == "yes"
                            ):
                                if self._file_handler.remove_file(image_data.data) == 1:
                                    self._existing_image_combo.value_remove(
                                        image_data.index
                                    )
                                else:
                                    popups.PopError(
                                        title="Failed To Delete File...",
                                        message=f"Could Not Delete {sys_consts.SDELIM}{image_data.display}{sys_consts.SDELIM}!",
                                    ).show()
                        else:
                            popups.PopMessage(
                                title="Image Not Selected...",
                                message="Please Select An Image From The Dropdown!",
                            ).show()

                    case "delete_person":
                        combo_data = self._trailer_people_combo.value_get()

                        if combo_data.user_data is not None:
                            if (
                                popups.PopYesNo(
                                    title="Delete Trailer Person...",
                                    message="Delete This Trailer Person?",
                                ).show()
                                == "yes"
                            ):
                                trailer_person: Trailer_Person = combo_data.user_data

                                if trailer_person.unique_id:
                                    pprint.pprint(self._trailer_people)
                                    deleted_person = self._trailer_people.pop(
                                        trailer_person.unique_id
                                    )
                                    self._load_trailer_people_combo()
                                    self._clear_trailer_person()

                    case "save_person":
                        self._save_trailer_person()

                    case "save_image":
                        self._save_trailer_image()

                    case "gen_trailer":
                        with qtg.sys_cursor(qtg.Cursor.hourglass):
                            self._load_existing_images_combo()
                            result, message = Generate_People_Trailer(
                                project_name=self.project_name,
                                frame_rate=self.frame_rate,
                                aspect_ratio=self.aspect_ratio,
                            )

                        if result == -1:
                            popups.PopError(
                                title="Error Generating Trailer...",
                                message=f"{sys_consts.SDELIM}{message}{sys_consts.SDELIM}",
                            ).show()
                        else:
                            popups.PopMessage(
                                title="Generated Person Trailer...",
                                message="Person Trailer Generated!",
                            ).show()

            case qtg.Sys_Events.EDITCHANGED:
                match event.tag:
                    case "font_size":
                        if self._open_flag:
                            self._text_font_size = event.value

                            self._db_settings.setting_set(
                                sys_consts.PERSON_FONT_POINT_SIZE_DBK,
                                self._text_font_size,
                            )
                    case "transparency":
                        if self._open_flag:
                            self._text_background_transparency = event.value
                            self._db_settings.setting_set(
                                sys_consts.PERSON_BACKGROUND_TRANSPARENCY_DBK,
                                self._text_background_transparency,
                            )
            case qtg.Sys_Events.INDEXCHANGED:
                match event.tag:
                    case "title_font":
                        if self._open_flag:
                            self._text_font = event.value.user_data[1]

                            self._db_settings.setting_set(
                                sys_consts.PERSON_FONT_DBK, self._text_font
                            )
                    case "text_color":
                        if self._open_flag:
                            self._text_colour = event.value.user_data

                            self._db_settings.setting_set(
                                sys_consts.PERSON_FONT_COLOUR_DBK, self._text_colour
                            )
                    case "background_color":
                        if self._open_flag:
                            self._text_background_colour = event.value.user_data

                            self._db_settings.setting_set(
                                sys_consts.PERSON_BACKGROUND_COLOUR_DBK,
                                self._text_background_colour,
                            )
                    case "existing_images":
                        if self._open_flag:
                            combo_item: Combo_Item = event.value
                            if combo_item.data:
                                self._person_image.image_set(image=combo_item.data)
                            else:
                                self._person_image.image_set(image=self.person_image)

                    case "trailer_people":
                        if self._open_flag:
                            combo_item: Combo_Item = event.value

                            self._existing_image_combo.select_index(0)

                            if (
                                combo_item.user_data is None
                                or combo_item.data == NEW_PERSON
                            ):
                                self._clear_trailer_person()
                            else:
                                trailer_person = combo_item.user_data
                                self._set_trailer_person(trailer_person)
                                self._write_text_on_image(trailer_person)

    def _clear_trailer_person(self) -> None:
        """
        Clears the trailer person details from the screen

        Returns:
            None

        """
        self._surname.clear()
        self._first_name.clear()
        self._other_names.clear()
        self._maiden_name.clear()
        self._comment.clear()
        self._dob.clear()
        self._dod.clear()
        self._person_image.image_set(self.person_image)

        return None

    def _load_existing_images_combo(self) -> None:
        people_trailer_folder = self._file_handler.file_join(
            self.output_folder, sys_consts.PEOPLE_TRAILER_FOLDER_NAME
        )

        if people_trailer_folder:
            self._existing_image_combo.clear()
            file_list = self._file_handler.filelist(people_trailer_folder, ["jpg"])
            self._existing_image_combo.value_set(
                Combo_Data(
                    display="Click To View Existing Images...",
                    data="",
                    user_data="",
                    index=-1,
                )
            )

            for file in sorted(file_list.files):
                self._existing_image_combo.value_set(
                    Combo_Data(
                        display=file,
                        data=self._file_handler.file_join(file_list.path, file),
                        user_data=self._file_handler.file_join(file_list.path, file),
                        index=-1,
                    )
                )
            self._existing_image_combo.select_index(0)

    def _load_trailer_people_combo(self) -> None:
        combo_items = []

        for unique_id, trailer_person in self._trailer_people.items():
            if trailer_person.surname:
                maiden_name = (
                    f"(née {trailer_person.maiden_name})"
                    if trailer_person.maiden_name
                    else ""
                )
                display_name = (
                    f"{trailer_person.surname.upper()} {trailer_person.first_name} "
                    f"{trailer_person.other_names} {maiden_name} {trailer_person.date_label}"
                )
                combo_items.append(
                    Combo_Item(
                        display=display_name,
                        data=trailer_person.details,
                        icon=None,
                        user_data=trailer_person,
                    )
                )
        combo_items.sort(key=lambda item: item.display)

        self._trailer_people_combo.clear()

        self._trailer_people_combo.load_items(combo_items, na_string=NEW_PERSON)

        return None

    def _save_trailer_image(self) -> None:
        """

        Saves A trailer image to the person trailer folder

        Returns:
            None

        """
        people_trailer_folder = self._file_handler.file_join(
            self.output_folder, sys_consts.PEOPLE_TRAILER_FOLDER_NAME
        )

        self._load_existing_images_combo()

        if people_trailer_folder:
            if not self._file_handler.path_exists(people_trailer_folder):
                if self._file_handler.make_dir(people_trailer_folder) == -1:  # Error
                    popups.PopError(
                        title="Error Making folder...",
                        message=f"Could Not Make Folder: {sys_consts.SDELIM}{people_trailer_folder}{sys_consts.SDELIM}",
                    ).show()

            if self._file_handler.path_exists(people_trailer_folder):
                if self._file_handler.path_writeable(people_trailer_folder):  # Ok
                    trailer_person = Trailer_Person()
                    trailer_person.surname = self._surname.value_get()
                    trailer_person.first_name = self._first_name.value_get()
                    trailer_person.other_names = self._other_names.value_get()
                    trailer_person.maiden_name = self._maiden_name.value_get()
                    trailer_person.comment = self._comment.value_get()

                    trailer_person.dob = self._dob.value_get()
                    trailer_person.dod = self._dod.value_get()

                    if (
                        not trailer_person.surname.strip()
                        and not trailer_person.first_name.strip()
                    ):
                        popups.PopError(
                            title="Person Details Not Entered...",
                            message="A Persons Surname And First Name Must Be Entered",
                        ).show()
                        return None

                    self._update_person_trailer_db()
                    self._load_trailer_people_combo()

                    self._write_text_on_image(trailer_person)

                    file = utils.Text_To_File_Name(
                        (
                            f"{trailer_person.surname.upper()}_{trailer_person.first_name}_"
                            f"{trailer_person.other_names}_{trailer_person.maiden_name}"
                        )
                    )

                    file_name = self._file_handler.file_join(
                        people_trailer_folder, file, "jpg"
                    )

                    if self._file_handler.path_exists(file_name):
                        self._file_handler.remove_file(file_name)

                    with qtg.sys_cursor(qtg.Cursor.hourglass):
                        byte_array = qtC.QByteArray()
                        buffer = qtC.QBuffer(byte_array)
                        buffer.open(qtC.QIODevice.WriteOnly)
                        self.person_image.save(buffer, "BMP")

                        result, image_data = Overlay_Text(
                            in_file=bytes(byte_array),
                            text=trailer_person.details,
                            text_font=self._text_font,
                            text_pointsize=self._text_font_size,
                            text_color=self._text_colour,
                            background_color=self._text_background_colour,
                            out_file=file_name,
                        )

                    if result == -1:  # Image data will be str and have error message
                        popups.PopError(
                            title="Error Saving Image...",
                            message=f"Could Not Save Image: {sys_consts.SDELIM}{image_data}{sys_consts.SDELIM}",
                        ).show()
                    else:
                        self._load_existing_images_combo()
                        popups.PopMessage(
                            title="Image Saved...",
                            message=f"Saved Image: {sys_consts.SDELIM}{file}{sys_consts.SDELIM}",
                        ).show()

                else:  # Error
                    popups.PopError(
                        title="Folder Does Not Exits...",
                        message=f"Folder Path Does Not Exist: {sys_consts.SDELIM}{people_trailer_folder}{sys_consts.SDELIM}",
                    ).show()

        return None

    def _save_trailer_person(self) -> None:
        """
        Saves trailer person changes to the database

        Returns:
            None

        """
        self._load_existing_images_combo()

        new_person = False
        combo_data = self._trailer_people_combo.value_get()
        if combo_data.data == "N/A":
            new_person = True

        display_person = Trailer_Person()
        display_person.surname = self._surname.value_get()
        display_person.first_name = self._first_name.value_get()
        display_person.other_names = self._other_names.value_get()
        display_person.maiden_name = self._maiden_name.value_get()
        display_person.comment = self._comment.value_get()
        display_person.dob = self._dob.value_get()
        display_person.did = self._dob.value_get()

        maiden_name = (
            f"(née {display_person.maiden_name})" if display_person.maiden_name else ""
        )

        display_name = (
            f"{display_person.surname.upper()} {display_person.first_name} "
            f"{display_person.other_names} {maiden_name} {display_person.date_label}"
        )

        if new_person:
            found_index = -1
            for combo_index, combo_item in enumerate(
                self._trailer_people_combo.get_items
            ):
                if display_name == combo_item.display:
                    found_index = combo_index
                    break

            if found_index >= 0:
                popups.PopMessage(
                    title="Person Already Exists...",
                    message="A Person With That Name Already Exists",
                ).show()
                return None

        if self._update_person_trailer_db() == 1:
            self._load_trailer_people_combo()

            self._trailer_people_combo.select_text(
                select_text=display_name, partial_match=False
            )

        return None

    def _set_trailer_person(self, trailer_person: Trailer_Person) -> None:
        """
        Sets the trailer person details on the screen

        Args:
            trailer_person (Trailer_Person): The trailer person object

        Returns:
            None

        """
        assert isinstance(trailer_person, Trailer_Person), (
            f"{trailer_person=}. Must be an instance of Trailer_Person"
        )

        self._surname.value_set(trailer_person.surname)
        self._first_name.value_set(trailer_person.first_name)
        self._other_names.value_set(trailer_person.other_names)
        self._maiden_name.value_set(trailer_person.maiden_name)
        self._comment.value_set(trailer_person.comment)
        self._dob.value_set(trailer_person.dob)
        self._dod.value_set(trailer_person.dod)

        return None

    def _update_person_trailer_db(self) -> int:
        surname = self._surname.value_get().strip()
        first_name = self._first_name.value_get().strip()
        other_names = self._other_names.value_get().strip()
        maiden_name = self._maiden_name.value_get().strip()
        comment = self._comment.value_get().strip()
        dob = self._dob.value_get().strip()
        dod = self._dod.value_get().strip()

        if not surname or not first_name:
            popups.PopError(
                title="Trailer Person Details Not Complete...",
                message="A Trailer Persons Surname and First Name Must Be Entered",
            ).show()
            return -1
        else:
            combo_data = self._trailer_people_combo.value_get()
            if combo_data.data == "N/A":
                trailer_person = Trailer_Person()
                print(f"New Person {trailer_person.unique_id=} {trailer_person=}")
            else:
                trailer_person = combo_data.user_data
                print(f"Existing Person {trailer_person.unique_id=} {trailer_person=}")

            trailer_person.surname = surname
            trailer_person.first_name = first_name
            trailer_person.other_names = other_names
            trailer_person.maiden_name = maiden_name
            trailer_person.comment = comment
            trailer_person.dob = dob
            trailer_person.dod = dod

            self._trailer_people[trailer_person.unique_id] = trailer_person

            self._sql_shelf.update(
                sys_consts.TRAILER_PEOPLE_SHELF, self._trailer_people
            )

        return 1

    def _process_ok(self, event: qtg.Action) -> int:
        """
        Handles processing the ok button.

        Args:
            event (qtg.Action): The triggering event.

        Returns:
            int: Returns 1 if the ok process id good, -1 otherwise
        """

        self.set_result("")

        return 1

    def _write_text_on_image(self, trailer_person: Trailer_Person) -> tuple[int, str]:
        """
        Write the trailer persons details onto the image

        Args:
            trailer_person (Trailer_Person): The trailer person

        Returns:
            tuple[int,str]:
                - arg 1 (int) : 1 if Ok, -1 if not
                - arg 2 (str) : "" if Ok, Otherwise the error message

        """
        assert isinstance(trailer_person, Trailer_Person), (
            f"{trailer_person=}. Must be an instance of Trailer Person"
        )

        ba = qtC.QByteArray()
        buffer = qtC.QBuffer(ba)
        buffer.open(qtC.QIODevice.WriteOnly)
        self.person_image.save(buffer, "BMP")

        result, image_data = Overlay_Text(
            in_file=bytes(ba),
            text=trailer_person.details,
            text_font=self._text_font,
            text_pointsize=self._text_font_size,
            text_color=self._text_colour,
            background_color=self._text_background_colour,
        )

        if result == 1:  # Ok - image in image_data
            self._person_image.image_set(image=image_data)
            return 1, ""
        else:  # Error, error message in image_data
            print(f"DBG {result=}")
            return -1, image_data

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""

        font_list = [
            qtg.Combo_Item(display=font[0], data=font[1], icon=None, user_data=font)
            for font in Get_Fonts()
        ]

        color_list = [
            qtg.Combo_Item(display=color, data=color, icon=None, user_data=color)
            for color in Get_Color_Names()
        ]

        self._existing_image_combo = qtg.ComboBox(
            tooltip="Select An Existing Image To View",
            tag="existing_images",
            width=47,
            callback=self.event_handler,
            display_na=False,
            translate=False,
            buddy_control=qtg.HBoxContainer(margin_left=0, margin_right=0).add_row(
                qtg.Spacer(
                    width=1,
                    height=1,
                ),
                qtg.Button(
                    tag="delete_image",
                    callback=self.event_handler,
                    icon=file_utils.App_Path("x.svg"),
                    tooltip="Delete Image",
                    width=1,
                    height=1,
                ),
            ),
        )

        self._trailer_people_combo = qtg.ComboBox(
            tag="trailer_people",
            width=43,
            callback=self.event_handler,
            display_na=False,
            translate=False,
            buddy_control=qtg.HBoxContainer(margin_left=0, margin_right=0).add_row(
                qtg.Spacer(
                    width=1,
                    height=1,
                ),
                qtg.Button(
                    tag="delete_person",
                    callback=self.event_handler,
                    icon=file_utils.App_Path("x.svg"),
                    tooltip="Delete Trailer Person",
                    width=1,
                    height=1,
                    buddy_control=qtg.Button(
                        tag="save_person",
                        callback=self.event_handler,
                        icon=file_utils.App_Path("check.svg"),
                        tooltip="Save Trailer Person",
                        width=1,
                        height=1,
                    ),
                ),
            ),
        )

        self._text_font_combo = qtg.ComboBox(
            tag="title_font",
            label="Font",
            width=30,
            callback=self.event_handler,
            items=font_list,
            display_na=False,
            translate=False,
        )

        self._text_colour_combo = qtg.ComboBox(
            tag="text_color",
            label="Text Color",
            width=20,
            callback=self.event_handler,
            items=color_list,
            display_na=False,
            translate=False,
        )

        self._text_background_colour_combo = qtg.ComboBox(
            tag="background_color",
            label="Background Color",
            width=20,
            callback=self.event_handler,
            items=color_list,
            display_na=False,
            translate=False,
        )

        self._text_background_transparency_spin = qtg.Spinbox(
            label="Transparency",
            tag="transparency",
            range_min=0,
            range_max=100,
            width=4,
            callback=self.event_handler,
            buddy_control=qtg.Label(text="%", width=1),
        )

        self._text_font_size_spin = qtg.Spinbox(
            label="Font Size",
            tag="font_size",
            range_min=7,
            range_max=48,
            width=4,
            callback=self.event_handler,
            buddy_control=self._text_background_transparency_spin,
        )

        self._person_image = qtg.Image(image=self.person_image, height=50)

        self._surname = qtg.LineEdit(
            label="Surname",
            tag="surname",
            callback=self.event_handler,
            width=40,
            char_length=40,
        )
        self._first_name = qtg.LineEdit(
            label="First Name",
            tag="first_name",
            callback=self.event_handler,
            width=40,
            char_length=40,
        )
        self._other_names = qtg.LineEdit(
            label="Other Names",
            tag="other_names",
            callback=self.event_handler,
            width=40,
            char_length=40,
        )
        self._maiden_name = qtg.LineEdit(
            label="Maiden Name",
            tag="maiden_name",
            callback=self.event_handler,
            width=40,
            char_length=40,
        )
        self._comment = qtg.LineEdit(
            label="Comment",
            tag="comment",
            callback=self.event_handler,
            width=40,
            char_length=40,
        )

        self._dob = qtg.LineEdit(
            label="Date Of Birth",
            tag="dob",
            tooltip="Date Of Birth - YYYY/MM/DD",
            callback=self.event_handler,
            input_mask="9999/99/99",
            width=10,
        )
        self._dod = qtg.LineEdit(
            label="Date Of Death",
            tag="dod",
            tooltip="Date Of Death - YYYY/MM/DD",
            callback=self.event_handler,
            input_mask="9999/99/99",
            width=10,
        )

        person_image_container = qtg.VBoxContainer(
            text="Image", align=qtg.Align.LEFT
        ).add_row(self._existing_image_combo, self._person_image)
        self._dob.buddy_control = self._dod

        person_details_container = qtg.FormContainer(text="Details").add_row(
            self._surname,
            self._first_name,
            self._other_names,
            self._maiden_name,
            self._comment,
            qtg.Spacer(),
            self._dob,
        )

        control_container = qtg.VBoxContainer(
            text="Person", tag="form_controls", align=qtg.Align.RIGHT
        )

        control_container.add_row(
            qtg.VBoxContainer(align=qtg.Align.LEFT).add_row(
                qtg.VBoxContainer(text="Select Trailer Person").add_row(
                    self._trailer_people_combo
                ),
                person_details_container,
                qtg.Spacer(),
                qtg.FormContainer(text="Text Font").add_row(
                    self._text_font_combo,
                    self._text_colour_combo,
                    self._text_background_colour_combo,
                    self._text_font_size_spin,
                ),
                qtg.Spacer(),
                person_image_container,
            ),
            qtg.HBoxContainer(margin_left=0, margin_right=0).add_row(
                qtg.Button(
                    text="&Save Image",
                    tag="save_image",
                    callback=self.event_handler,
                ),
                qtg.Button(
                    text="&Generate Trailer",
                    tag="gen_trailer",
                    callback=self.event_handler,
                ),
                qtg.Spacer(width=8),
                qtg.Command_Button_Container(
                    ok_callback=self.event_handler, margin_right=10
                ),
            ),
        )

        return control_container
