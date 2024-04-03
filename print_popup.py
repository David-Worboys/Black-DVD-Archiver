"""
Implements a popup dialog that allows users print DVD Labels/Inserts

Copyright (C) 2024  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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
from typing import cast

from PySide6.QtGui import QImage, QPainter
from PySide6.QtPrintSupport import QPrinterInfo, QPrinter, QPrintDialog, QAbstractPrintDialog

import dvdarch_utils
import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from dvdarch_utils import Create_DVD_Label
from sys_config import DVD_Menu_Page, DVD_Print_Settings


# fmt: on


@dataclasses.dataclass
class Print_DVD_Label_Popup(qtg.PopContainer):
    """Prints DVD Labels/Inserts"""

    # Public instance variables
    disk_title: str = ""
    dvd_menu_pages: list[DVD_Menu_Page] = dataclasses.field(default_factory=list)

    # Private instance variables
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _default_font: str = "IBMPlexMono-SemiBold.ttf"  # Packaged with DVD Archiver
    _startup: bool = True
    _printer_info: QPrinterInfo = QPrinterInfo()
    _printer_status: str = "Unknown"

    def __post_init__(self) -> None:
        """Sets-up the form"""
        assert isinstance(self.disk_title, str), f"{self.disk_title=}. Must be str"
        assert isinstance(
            self.dvd_menu_pages, list
        ), f"{self.dvd_menu_pages=}. Must be A list Of DVD_Menu_Page instances"
        assert all(
            isinstance(dvd_menu_page, DVD_Menu_Page)
            for dvd_menu_page in self.dvd_menu_pages
        ), "All elements must be DVD_Menu_Page instances"

        self.container = self.layout()

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action) -> None:
        """Handles  form events
        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                self._post_open_handler(event)

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "cancel":
                        self._save_to_db(event)
                        self.set_result(event.tag)
                        super().close()
                    case "print":
                        if not self.dvd_menu_pages:
                            popups.PopMessage(
                                title="Print Error...",
                                message="No Menu Pages Have Been Added To The DVD Layout And No Labels Can Be Generated",
                            ).show()
                        else:
                            self._print(event)
                    case "print_folder_select":
                        self._print_folder_select(event)
                    case "print_file_select":
                        self._print_file_select(event)
                    case "printer_settings":
                        self._printer_settings(event)
            case qtg.Sys_Events.TEXTCHANGED:
                if not self._startup:
                    if event.tag in (
                        "text_color",
                        "background_color",
                        "title_font",
                        "font_size",
                        "transparency",
                    ):
                        self._font_combo_change(event)
            case qtg.Sys_Events.TOGGLED:
                with qtg.sys_cursor(qtg.Cursor.hourglass):
                    self._toggle_textProperties(event)
            case qtg.Sys_Events.INDEXCHANGED:
                if event.tag == "available_printers":
                    selected_printer: str = event.value.data
                    self._set_printer_status(event, selected_printer)

    def _toggle_textProperties(self, event: qtg.Action) -> None:
        """Toggles the text properties

        Args:
            event (qtg.Action): The triggering event

        Returns:
            None
        """
        if not self._startup and event.tag in ("title_text", "menu_text"):
            if (
                event.value
            ):  # Dealing with radiobutton so that only one can be selected and bool
                dvd_print_settings = DVD_Print_Settings()
                file_handler = file_utils.File()

                item = event.container_tag.replace("_rb", "")

                # Gather the controls
                text_color_combo: qtg.ComboBox = cast(
                    qtg.ComboBox,
                    event.widget_get(
                        container_tag=item,
                        tag="text_color",
                    ),
                )

                background_color_combo: qtg.ComboBox = cast(
                    qtg.ComboBox,
                    event.widget_get(
                        container_tag=item,
                        tag="background_color",
                    ),
                )

                font_combo: qtg.ComboBox = cast(
                    qtg.ComboBox,
                    event.widget_get(
                        container_tag=item,
                        tag="title_font",
                    ),
                )

                font_size: qtg.Spinbox = cast(
                    qtg.Spinbox,
                    event.widget_get(
                        container_tag=item,
                        tag="font_size",
                    ),
                )

                background_transparency: qtg.Spinbox = cast(
                    qtg.Spinbox,
                    event.widget_get(
                        container_tag=item,
                        tag="transparency",
                    ),
                )

                # Now for the tedious bit - setting and saving the text properties
                if event.tag == "title_text":
                    if item == "case_insert_text":
                        # Save menu text properties
                        dvd_print_settings.insert_background_color = event.value_get(
                            container_tag=item,
                            tag="background_color",
                        ).data

                        dvd_print_settings.insert_font_color = event.value_get(
                            container_tag=item,
                            tag="text_color",
                        ).data
                        dvd_print_settings.insert_font = event.value_get(
                            container_tag=item, tag="title_font"
                        ).data
                        dvd_print_settings.insert_font_point_size = event.value_get(
                            container_tag=item,
                            tag="font_size",
                        )
                        dvd_print_settings.insert_background_transparency = (
                            event.value_get(
                                container_tag=item,
                                tag="transparency",
                            )
                        )

                        # Load title text properties

                        _, font_name, extn = file_handler.split_file_path(
                            dvd_print_settings.insert_title_font
                        )

                        if not font_name:
                            font_name = self._default_font

                        background_color_combo.select_text(
                            dvd_print_settings.insert_background_color,
                            partial_match=False,
                        )
                        text_color_combo.select_text(
                            dvd_print_settings.insert_title_font_color,
                            partial_match=False,
                        )
                        font_combo.select_text(
                            f"{font_name}{extn}", partial_match=False
                        )
                        font_size.value_set(
                            dvd_print_settings.insert_title_font_point_size
                        )
                        background_transparency.value_set(
                            dvd_print_settings.insert_title_background_transparency
                        )

                    elif item == "dvd_label_text":
                        # Save menu text properties
                        dvd_print_settings.disk_background_color = event.value_get(
                            container_tag=item,
                            tag="background_color",
                        ).data
                        dvd_print_settings.disk_font_color = event.value_get(
                            container_tag=item,
                            tag="text_color",
                        ).data
                        dvd_print_settings.disk_font = event.value_get(
                            container_tag=item, tag="title_font"
                        ).data
                        dvd_print_settings.disk_font_point_size = event.value_get(
                            container_tag=item,
                            tag="font_size",
                        )
                        dvd_print_settings.disk_background_transparency = (
                            event.value_get(
                                container_tag=item,
                                tag="transparency",
                            )
                        )

                        # Set title text properties
                        _, font_name, extn = file_handler.split_file_path(
                            dvd_print_settings.disk_title_font
                        )

                        if not font_name:
                            font_name = self._default_font

                        background_color_combo.select_text(
                            dvd_print_settings.disk_background_color,
                            partial_match=False,
                        )
                        text_color_combo.select_text(
                            dvd_print_settings.disk_title_font_color,
                            partial_match=False,
                        )
                        font_combo.select_text(
                            f"{font_name}{extn}", partial_match=False
                        )
                        font_size.value_set(
                            dvd_print_settings.disk_title_font_point_size
                        )
                        background_transparency.value_set(
                            dvd_print_settings.disk_title_background_transparency
                        )

                else:  # menu_text
                    if item == "case_insert_text":
                        # Save title text properties
                        dvd_print_settings.insert_background_color = event.value_get(
                            container_tag=item,
                            tag="background_color",
                        ).data
                        dvd_print_settings.insert_title_font_color = event.value_get(
                            container_tag=item,
                            tag="text_color",
                        ).data
                        dvd_print_settings.insert_title_font = event.value_get(
                            container_tag=item, tag="title_font"
                        ).data
                        dvd_print_settings.insert_title_font_point_size = (
                            event.value_get(
                                container_tag=item,
                                tag="font_size",
                            )
                        )
                        dvd_print_settings.insert_title_background_transparency = (
                            event.value_get(
                                container_tag=item,
                                tag="transparency",
                            )
                        )

                        # Load menu properties
                        _, font_name, extn = file_handler.split_file_path(
                            dvd_print_settings.insert_font
                        )

                        if not font_name:
                            font_name = self._default_font

                        background_color_combo.select_text(
                            dvd_print_settings.insert_background_color,
                            partial_match=False,
                        )
                        text_color_combo.select_text(
                            dvd_print_settings.insert_font_color,
                            partial_match=False,
                        )
                        font_combo.select_text(
                            f"{font_name}{extn}", partial_match=False
                        )
                        font_size.value_set(dvd_print_settings.insert_font_point_size)
                        background_transparency.value_set(
                            dvd_print_settings.insert_background_transparency
                        )

                    elif item == "dvd_label_text":
                        # Save title text properties
                        dvd_print_settings.disk_background_color = event.value_get(
                            container_tag=item,
                            tag="background_color",
                        ).data
                        dvd_print_settings.disk_title_font_color = event.value_get(
                            container_tag=item,
                            tag="text_color",
                        ).data
                        dvd_print_settings.disk_title_font = event.value_get(
                            container_tag=item, tag="title_font"
                        ).data
                        dvd_print_settings.disk_title_font_point_size = event.value_get(
                            container_tag=item,
                            tag="font_size",
                        )
                        dvd_print_settings.disk_title_background_transparency = (
                            event.value_get(
                                container_tag=item,
                                tag="transparency",
                            )
                        )

                        # Set Menu text properties
                        _, font_name, extn = file_handler.split_file_path(
                            dvd_print_settings.disk_font
                        )

                        if not font_name:
                            font_name = self._default_font

                        background_color_combo.select_text(
                            dvd_print_settings.disk_background_color,
                            partial_match=False,
                        )
                        text_color_combo.select_text(
                            dvd_print_settings.disk_font_color,
                            partial_match=False,
                        )
                        font_combo.select_text(
                            f"{font_name}{extn}", partial_match=False
                        )
                        font_size.value_set(dvd_print_settings.disk_font_point_size)
                        background_transparency.value_set(
                            dvd_print_settings.disk_background_transparency
                        )

        return None

    def _post_open_handler(self, event: qtg.Action) -> None:
        """Sets the default print folder and file values in the printer controls

        Args:
            event (qtg.Action): The triggering event

        Returns:
                None

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        folder = sys_consts.SPECIAL_PATH.DOCUMENTS
        if self._db_settings.setting_exist(sys_consts.PRINT_FOLDER_DBK):
            folder = self._db_settings.setting_get(sys_consts.PRINT_FOLDER_DBK)

        event.value_set(
            container_tag="printer_controls",
            tag="print_folder",
            value=folder,
        )

        print_file = ""
        if self._db_settings.setting_exist(sys_consts.PRINT_FILE_DBK):
            print_file = self._db_settings.setting_get(sys_consts.PRINT_FILE_DBK)

        event.value_set(
            container_tag="printer_controls",
            tag="print_file",
            value=print_file,
        )

        selected_printer: qtg.Combo_Data = event.value_get(
            container_tag="printer_controls", tag="available_printers"
        )

        if selected_printer is None or selected_printer.data.strip() == "":
            event.value_set(
                container_tag="printer_controls",
                tag="print_to_file",
                value=True,
            )
        else:
            self._set_printer_status(event, selected_printer.data)

        self._font_combo_init(event)

        self._startup = False

    def _font_combo_init(self, event: qtg.Action) -> None:
        """Initializes font combo boxes

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        file_handler = file_utils.File()
        dvd_print_settings = DVD_Print_Settings()

        for item in ("dvd_label_text", "case_insert_text"):
            title_text: bool = cast(
                bool,
                event.value_get(
                    container_tag=item,
                    tag="title_text",
                ),
            )  # Radio Button

            menu_text: bool = cast(
                bool,
                event.value_get(
                    container_tag=item,
                    tag="menu_text",
                ),
            )  # Radio Button

            if title_text and item == "case_insert_text":
                background_color = dvd_print_settings.insert_background_color
                font_color = dvd_print_settings.insert_title_font_color
                font = dvd_print_settings.insert_title_font
                font_point_size = dvd_print_settings.insert_title_font_point_size
                transparency = dvd_print_settings.insert_title_background_transparency
            elif title_text and item == "dvd_label_text":
                background_color = dvd_print_settings.disk_background_color
                font_color = dvd_print_settings.disk_title_font_color
                font = dvd_print_settings.disk_title_font
                font_point_size = dvd_print_settings.disk_title_font_point_size
                transparency = dvd_print_settings.disk_title_background_transparency
            elif menu_text and item == "case_insert_text":
                background_color = dvd_print_settings.insert_background_color
                font_color = dvd_print_settings.insert_font_color
                font = dvd_print_settings.insert_font
                font_point_size = dvd_print_settings.insert_font_point_size
                transparency = dvd_print_settings.insert_title_background_transparency
            elif menu_text and item == "dvd_label_text":
                background_color = dvd_print_settings.disk_background_color
                font_color = dvd_print_settings.disk_font_color
                font = dvd_print_settings.disk_font
                font_point_size = dvd_print_settings.disk_font_point_size
                transparency = dvd_print_settings.disk_title_background_transparency
            else:
                raise AssertionError(f"Unknown item {item=} {title_text=} {menu_text=}")

            _, font_name, extn = file_handler.split_file_path(font)

            if not font_name:
                font_name = self._default_font

            text_color_combo: qtg.ComboBox = cast(
                qtg.ComboBox,
                event.widget_get(
                    container_tag=item,
                    tag="text_color",
                ),
            )

            background_color_combo: qtg.ComboBox = cast(
                qtg.ComboBox,
                event.widget_get(container_tag=item, tag="background_color"),
            )

            font_combo: qtg.ComboBox = cast(
                qtg.ComboBox, event.widget_get(container_tag=item, tag="title_font")
            )

            font_size: qtg.Spinbox = cast(
                qtg.Spinbox, event.widget_get(container_tag=item, tag="font_size")
            )

            background_transparency: qtg.Spinbox = cast(
                qtg.Spinbox,
                event.widget_get(container_tag=item, tag="transparency"),
            )

            background_transparency.value_set(transparency)
            background_color_combo.select_text(background_color, partial_match=False)
            text_color_combo.select_text(font_color, partial_match=False)
            font_combo.select_text(f"{font_name}{extn}", partial_match=False)
            font_size.value_set(font_point_size)

        event.container_tag = "case_insert_text"
        self._font_combo_change(event)
        event.container_tag = "dvd_label_text"
        self._font_combo_change(event)

    def _font_combo_change(self, event: qtg.Action) -> None:
        """Changes the font of the colour patch of the title font text when the font
        selection changes

        Args:
            event (qtg.Action): The triggering event
        """
        if event.container_tag in ("dvd_label_text", "case_insert_text"):
            if event.container_tag == "dvd_label_text":
                example_text = " Disk Text "
                title_text: bool = cast(
                    bool,
                    event.value_get(
                        container_tag=event.container_tag,
                        tag="title_text",
                    ),
                )
                menu_text: bool = cast(
                    bool,
                    event.value_get(
                        container_tag=event.container_tag,
                        tag="menu_text",
                    ),
                )
            else:
                example_text = " Insert Text "
                title_text: bool = cast(
                    bool,
                    event.value_get(
                        container_tag=event.container_tag,
                        tag="title_text",
                    ),
                )
                menu_text: bool = cast(
                    bool,
                    event.value_get(
                        container_tag=event.container_tag,
                        tag="menu_text",
                    ),
                )

            font_size: qtg.Spinbox = cast(
                qtg.Spinbox,
                event.widget_get(container_tag=event.container_tag, tag="font_size"),
            )

            image: qtg.Image = cast(
                qtg.Image,
                event.widget_get(
                    container_tag=event.container_tag,
                    tag="example",
                ),
            )

            transparency = 100

            char_pixel_size = qtg.g_application.char_pixel_size(
                font_path=event.value_get(
                    container_tag=event.container_tag, tag="title_font"
                ).data
            )

            pointsize, png_bytes = dvdarch_utils.Get_Font_Example(
                font_file=event.value_get(
                    container_tag=event.container_tag, tag="title_font"
                ).data,
                # pointsize=font_size.value_get(),
                text=example_text,
                text_color=event.value_get(
                    container_tag=event.container_tag,
                    tag="text_color",
                ).data,
                background_color=event.value_get(
                    container_tag=event.container_tag, tag="background_color"
                ).data,
                width=image.width * char_pixel_size.width,
                height=image.height * char_pixel_size.height,
                # height=144,
                opacity=transparency / 100,
            )

            if png_bytes:
                self._menu_title_font_size = pointsize
                image.image_set(png_bytes)
            else:
                popups.PopError(
                    title="Font Can Not Be Rendered...",
                    message=(
                        "The font"
                        f" {sys_consts.SDELIM} {event.value_get(container_tag=event.container_tag, tag='title_font').display} {sys_consts.SDELIM} Can"
                        " Not Be Rendered!"
                    ),
                ).show()
            return None

    def _print_folder_select(self, event: qtg.Action) -> None:
        """Selects a print folder and updates the settings in the database with the selected folder.

        Args:
            event (qtg.Action): The triggering event

        Note:
            The selected folder is saved in the database settings for future use.

        Returns:
            None

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        folder = sys_consts.SPECIAL_PATH.DOCUMENTS
        if self._db_settings.setting_exist(sys_consts.PRINT_FOLDER_DBK):
            folder = self._db_settings.setting_get(sys_consts.PRINT_FOLDER_DBK)
        folder = popups.PopFolderGet(
            title="Select A Print Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()
        if folder.strip() != "":
            self._db_settings.setting_set(sys_consts.PRINT_FOLDER_DBK, folder)

            event.value_set(
                container_tag="printer_controls",
                tag="print_folder",
                value=folder,
            )

        return None

    def _print_file_select(self, event: qtg.Action) -> None:
        """Selects a print file and updates the settings in the database with the selected file.

        Args:
            event (qtg.Action): The triggering event

        Note:
            The selected file is saved in the database settings for future use.

        Returns:
            None

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        file_handler = file_utils.File()
        print_file = ""
        if self._db_settings.setting_exist(sys_consts.PRINT_FILE_DBK):
            print_file = self._db_settings.setting_get(sys_consts.PRINT_FILE_DBK)
        print_file = popups.PopTextGet(
            title="Enter A Print File Name....",
            default_txt=print_file,
            label="Enter A Print File Name:",
        ).show()
        if print_file.strip() != "":
            _, print_file, _ = file_handler.split_file_path(print_file)
            if file_handler.filename_validate(print_file):
                self._db_settings.setting_set(sys_consts.PRINT_FILE_DBK, print_file)
                event.value_set(
                    container_tag="printer_controls",
                    tag="print_file",
                    value=print_file,
                )
            else:
                error_msg = (
                    f"{sys_consts.SDELIM}{print_file!r}{sys_consts.SDELIM} is not a"
                    " valid file name! Please reenter."
                )
                popups.PopError(
                    title="Invalid File Name...",
                    message=error_msg,
                    width=80,
                ).show()
        return None

    def _printer_settings(self, event: qtg.Action) -> None:
        """Opens the printer settings dialog

        Args:
            event (qtg.Action): The triggering event

        Returns:
            None
        """

        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        selected_printer: qtg.Combo_Data = event.value_get(
            container_tag="printer_controls", tag="available_printers"
        )
        printer_info = self._printer_info.printerInfo(selected_printer.data)
        printer = QPrinter(printer_info)
        print_dialog = QPrintDialog(printer)
        print_dialog.setOption(QAbstractPrintDialog.PrintToFile, False)
        print_dialog.setOption(QAbstractPrintDialog.PrintCollateCopies, False)
        print_dialog.exec()

        return None

    def _save_to_db(self, event: qtg.Action) -> None:
        """Saves the current configuration to the database

        Args:
            event (qtg.Action): The triggering event
        """
        dvd_print_settings = DVD_Print_Settings()

        for item in ("dvd_label_text", "case_insert_text"):
            title_text: bool = cast(
                bool,
                event.value_get(
                    container_tag=item,
                    tag="title_text",
                ),
            )  # Radio Button

            menu_text: bool = cast(
                bool,
                event.value_get(
                    container_tag=item,
                    tag="menu_text",
                ),
            )  # Radio Button

            if title_text and item == "case_insert_text":
                dvd_print_settings.insert_background_color = event.value_get(
                    container_tag=item, tag="background_color"
                ).data
                dvd_print_settings.insert_title_font_color = event.value_get(
                    container_tag=item,
                    tag="text_color",
                ).data
                dvd_print_settings.insert_title_font = event.value_get(
                    container_tag=item, tag="title_font"
                ).data
                dvd_print_settings.insert_title_font_point_size = event.value_get(
                    container_tag=item, tag="font_size"
                )
                dvd_print_settings.insert_title_background_transparency = (
                    event.value_get(container_tag=item, tag="transparency")
                )
            elif title_text and item == "dvd_label_text":
                dvd_print_settings.disk_background_color = event.value_get(
                    container_tag=item, tag="background_color"
                ).data
                dvd_print_settings.disk_title_font_color = event.value_get(
                    container_tag=item,
                    tag="text_color",
                ).data
                dvd_print_settings.disk_title_font = event.value_get(
                    container_tag=item, tag="title_font"
                ).data
                dvd_print_settings.disk_title_font_point_size = event.value_get(
                    container_tag=item, tag="font_size"
                )
                dvd_print_settings.disk_title_background_transparency = event.value_get(
                    container_tag=item, tag="transparency"
                )
            elif menu_text and item == "case_insert_text":
                dvd_print_settings.insert_background_color = event.value_get(
                    container_tag=item, tag="background_color"
                ).data
                dvd_print_settings.insert_font_color = event.value_get(
                    container_tag=item,
                    tag="text_color",
                ).data
                dvd_print_settings.insert_font = event.value_get(
                    container_tag=item, tag="title_font"
                ).data
                dvd_print_settings.insert_font_point_size = event.value_get(
                    container_tag=item, tag="font_size"
                )
                dvd_print_settings.insert_background_transparency = event.value_get(
                    container_tag=item, tag="transparency"
                )
            elif menu_text and item == "dvd_label_text":
                dvd_print_settings.disk_background_color = event.value_get(
                    container_tag=item, tag="background_color"
                ).data
                dvd_print_settings.disk_font_color = event.value_get(
                    container_tag=item,
                    tag="text_color",
                ).data
                dvd_print_settings.disk_font = event.value_get(
                    container_tag=item, tag="title_font"
                ).data
                dvd_print_settings.disk_font_point_size = event.value_get(
                    container_tag=item, tag="font_size"
                )
                dvd_print_settings.disk_background_transparency = event.value_get(
                    container_tag=item, tag="transparency"
                )

        return None

    def _set_printer_status(self, event: qtg.Action, selected_printer: str) -> None:
        """Gets and sets the printer status

        Args:
            event (qtg.Action): The triggering event
            selected_printer (str): The selected printer
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"
        assert (
            isinstance(selected_printer, str) and selected_printer.strip() != ""
        ), f"{selected_printer=}. Must be a non-empty string"

        if self._startup:
            return None

        printer_info = self._printer_info.printerInfo(selected_printer)

        if printer_info.state() == QPrinter.Idle:
            self._printer_status = "Idle"
        elif printer_info.state() == QPrinter.Active:
            self._printer_status = "Active"
        elif printer_info.state() == QPrinter.Aborted:
            self._printer_status = "Aborted"
        elif printer_info.state() == QPrinter.Error:
            self._printer_status = "Error"
        else:
            self._printer_status = "Unknown"

        event.value_set(
            container_tag="printer_controls",
            tag="printer_info",
            value=self._printer_status,
        )

        if self._printer_status in ("Error", "Unknown"):
            event.value_set(
                container_tag="printer_controls", tag="print_to_file", value=True
            )

        return None

    def _print(self, event: qtg.Action) -> None:
        """Handles  print event
        Args:
            event (qtg.Action): The triggering event
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            print_settings = DVD_Print_Settings()
            self._save_to_db(event)
            switch_setting = event.value_get(
                container_tag="printer_controls", tag="print_disk_label"
            )  # Bool as Switch

            selected_printer: qtg.Combo_Data = event.value_get(
                container_tag="printer_controls", tag="available_printers"
            )

            self._set_printer_status(event, selected_printer.data)

            printer_info = self._printer_info.printerInfo(selected_printer.data)

            print_to_file: bool = event.value_get(
                container_tag="printer_controls", tag="print_to_file"
            )

            if print_to_file:
                print_folder = event.value_get(
                    container_tag="printer_controls", tag="print_folder"
                )

                print_file = event.value_get(
                    container_tag="printer_controls", tag="print_file"
                )

                if print_folder is None or print_folder.strip() == "":
                    popups.PopError(
                        title="Error...", message="No Print Folder Selected"
                    ).show()
                    return None

                if print_file is None is print_file.strip() == "":
                    popups.PopError(
                        title="Error...", message="No Print Folder Selected"
                    ).show()
                    return None

                file_handler = file_utils.File()

                file_name = file_handler.file_join(
                    dir_path=print_folder, file_name=print_file, ext="pdf"
                )

                printer = QPrinter()
                printer.setOutputFileName(file_name)
            else:
                printer = QPrinter(printer_info)

            printer.setResolution(300)
            printer.setColorMode(QPrinter.Color)

            if switch_setting:
                result, png_bytes = Create_DVD_Label(
                    title=self.disk_title,
                    title_font_path=print_settings.disk_title_font,
                    title_font_colour=print_settings.disk_title_font_color,
                    title_font_size=print_settings.disk_title_font_point_size,
                    disk_colour=print_settings.disk_background_color,
                    menu_pages=self.dvd_menu_pages,
                    menu_font_path=print_settings.disk_font,
                    menu_font_colour=print_settings.disk_font_color,
                    menu_font_size=print_settings.disk_font_point_size,
                    resolution=printer.logicalDpiX(),
                )
            else:
                result = 1

                popups.PopError(
                    title="Not Implemented...", message="Not Implemented Yet"
                ).show()
                return None

        if result == -1:
            popups.PopError(
                title="Print Error...", message=f"{png_bytes.decode('utf-8')}"
            ).show()
            return None

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            image = QImage()
            image.loadFromData(png_bytes)
            painter = QPainter(printer)
            painter.drawImage(0, 0, image)
            painter.end()

        return None

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""

        def text_settings_container(tag: str, text: str) -> qtg.HBoxContainer:
            assert isinstance(tag, str), f"{tag=}. Must be a string"
            assert isinstance(text, str), f"{text=}. Must be a string"

            color_list = [
                qtg.Combo_Item(display=color, data=color, icon=None, user_data=color)
                for color in dvdarch_utils.Get_Color_Names()
            ]

            font_list = [
                qtg.Combo_Item(display=font[0], data=font[1], icon=None, user_data=font)
                for font in dvdarch_utils.Get_Fonts()
            ]
            title_text_container = qtg.HBoxContainer(tag=f"{tag}_rb").add_row(
                qtg.RadioButton(
                    text="Title Text",
                    tag="title_text",
                    callback=self.event_handler,
                ),
                qtg.RadioButton(
                    text="Menu Text",
                    tag="menu_text",
                    callback=self.event_handler,
                    checked=True,
                ),
            )
            return qtg.HBoxContainer(margin_left=0).add_row(
                qtg.FormContainer(tag=tag, text=text).add_row(
                    title_text_container,
                    qtg.ComboBox(
                        tag="text_color",
                        label="Text Color",
                        width=30,
                        callback=self.event_handler,
                        items=color_list,
                        display_na=False,
                        translate=False,
                    ),
                    qtg.ComboBox(
                        tag="background_color",
                        label="Background Color",
                        width=30,
                        callback=self.event_handler,
                        items=color_list,
                        display_na=False,
                        translate=False,
                    ),
                    qtg.ComboBox(
                        tag="title_font",
                        label="Font",
                        width=30,
                        callback=self.event_handler,
                        items=font_list,
                        display_na=False,
                        translate=False,
                    ),
                    qtg.Spinbox(
                        label="Font Size",
                        tag="font_size",
                        range_min=7,
                        range_max=48,
                        width=4,
                        callback=self.event_handler,
                        buddy_control=(
                            qtg.HBoxContainer().add_row(
                                qtg.Spacer(width=4),
                                qtg.Spinbox(
                                    label="Transparency",
                                    tag="transparency",
                                    range_min=0,
                                    range_max=100,
                                    width=3,
                                    callback=self.event_handler,
                                    buddy_control=qtg.Label(text="%", width=1),
                                ),
                            )
                        ),
                    ),
                    qtg.Image(
                        tag="example",
                        height=4,
                        width=28,
                    ),
                )
            )

        print_folder = sys_consts.SPECIAL_PATH.DOCUMENTS
        if self._db_settings.setting_exist(sys_consts.PRINT_FOLDER_DBK):
            print_folder = self._db_settings.setting_get(sys_consts.PRINT_FOLDER_DBK)

        print_file = ""
        if self._db_settings.setting_exist(sys_consts.PRINT_FILE_DBK):
            print_file = self._db_settings.setting_get(sys_consts.PRINT_FILE_DBK)

        available_printers = self._printer_info.availablePrinterNames()

        available_printer_combo_items = []
        for printer in available_printers:
            available_printer_combo_items.append(
                qtg.Combo_Item(
                    display=printer,
                    data=printer,
                    icon=None,
                    user_data=None,
                )
            )

        printer_combo = qtg.ComboBox(
            label="Available Printers",
            tag="available_printers",
            width=30,
            items=available_printer_combo_items,
            translate=False,
            display_na=False,
            callback=self.event_handler,
            tooltip="Select Available Printers",
            buddy_control=qtg.HBoxContainer().add_row(
                qtg.Button(
                    tag="printer_settings",
                    icon=file_utils.App_Path("wrench.svg"),
                    callback=self.event_handler,
                    width=1,
                    height=1,
                    tooltip="Printer Settings",
                ),
                qtg.Spacer(width=1),
                qtg.Label(tag="printer_info", width=10, label="Status:"),
            ),
        )

        printer_target = qtg.Spacer(
            label="Print Target",
            label_pad=5,
            tag="printer_target",
            width=1,
            buddy_control=qtg.Switch(label="Case Insert", text="DVD Disk"),
            # qtg.HBoxContainer().add_row(
            #     qtg.RadioButton(
            #         text="Case Insert",
            #         tag="dvd_insert",
            #         callback=self.event_handler,
            #         checked=True,
            #     ),
            #     qtg.RadioButton(
            #         text="DVD Disk",
            #         tag="dvd_disk",
            #         callback=self.event_handler,
            #     ),
            # ),
        )

        print_settings_container = qtg.FormContainer(text="Options").add_row(
            printer_combo,
            qtg.Spacer(),
            # printer_target,
            qtg.Switch(
                tag="print_disk_label", label="Print Case Insert", text="Print DVD Disk"
            ),
            qtg.Spacer(),
            qtg.Checkbox(
                label="P&rint To File",
                tag="print_to_file",
                checked=False,
                callback=self.event_handler,
            ),
            qtg.LineEdit(
                label="Folder",
                tag="print_folder",
                text=print_folder,
                callback=self.event_handler,
                editable=False,
                width=60,
                translate=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="print_folder_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip="Select The Print Folder",
                ),
            ),
            qtg.LineEdit(
                label="File Name",
                tag="print_file",
                text=print_file,
                callback=self.event_handler,
                editable=False,
                width=60,
                translate=False,
                buddy_control=qtg.Button(
                    callback=self.event_handler,
                    tag="print_file_select",
                    height=1,
                    width=1,
                    icon=qtg.Sys_Icon.dir.get(),
                    tooltip="Enter The Print File Name",
                ),
            ),
        )

        button_container = qtg.HBoxContainer(margin_right=0).add_row(
            qtg.Button(
                text="&Print", tag="print", callback=self.event_handler, width=10
            ),
            qtg.Button(
                text="&Cancel", tag="cancel", callback=self.event_handler, width=10
            ),
        )

        control_container = qtg.VBoxContainer(
            tag="printer_controls",
            align=qtg.Align.TOPRIGHT,
            margin_right=10,
        )

        control_container.add_row(
            qtg.VBoxContainer(text="Print Settings", margin_right=10).add_row(
                print_settings_container,
                qtg.Spacer(),
                qtg.HBoxContainer().add_row(
                    text_settings_container(
                        tag="case_insert_text", text="DVD Insert Properties"
                    ),
                    text_settings_container(
                        tag="dvd_label_text", text="DVD Disk Properties"
                    ),
                ),
            ),
            button_container,
        )

        return control_container
