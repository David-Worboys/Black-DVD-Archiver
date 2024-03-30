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

from PySide6.QtGui import QImage, QPainter
from PySide6.QtPrintSupport import QPrinterInfo, QPrinter, QPrintDialog, QAbstractPrintDialog

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from dvdarch_utils import Create_DVD_Label
from sys_config import DVD_Menu_Page
# fmt: on


@dataclasses.dataclass
class Print_DVD_Label_Popup(qtg.PopContainer):
    """Prints DVD Labels/Inserts"""

    # Public instance variables
    disk_title: str = ""
    dvd_menu_pages: list[DVD_Menu_Page] = dataclasses.field(default_factory=list)

    # Private instance variables
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _window_init: bool = False
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
        # print(f"DBG {event.event=} {event.container_tag=} {event.tag=} {event.value=}")
        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                self._post_open_handler(event)

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "cancel":
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

            case qtg.Sys_Events.INDEXCHANGED:
                if event.tag == "available_printers":
                    selected_printer: str = event.value.data
                    self._set_printer_status(event, selected_printer)

    def _post_open_handler(self, event: qtg.Action) -> None:
        """Sets the default print folder and file values in the printer controls

        Args:
            event (qtg.Action): The triggering event

        Returns:
                None

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        self._window_init = True

        folder = sys_consts.SPECIAL_PATH.DOCUMENTS
        if self._db_settings.setting_exist("print_folder"):
            folder = self._db_settings.setting_get("print_folder")

        event.value_set(
            container_tag="printer_controls",
            tag="print_folder",
            value=folder,
        )

        print_file = ""
        if self._db_settings.setting_exist("print_file"):
            print_file = self._db_settings.setting_get("print_file")

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
        if self._db_settings.setting_exist("print_folder"):
            folder = self._db_settings.setting_get("print_folder")
        folder = popups.PopFolderGet(
            title="Select A Print Folder....",
            root_dir=folder,
            create_folder=True,
            folder_edit=False,
        ).show()
        if folder.strip() != "":
            self._db_settings.setting_set("print_folder", folder)

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
        if self._db_settings.setting_exist("print_file"):
            print_file = self._db_settings.setting_get("print_file")
        print_file = popups.PopTextGet(
            title="Enter A Print File Name....",
            default_txt=print_file,
            label="Enter A Print File Name:",
        ).show()
        if print_file.strip() != "":
            _, print_file, _ = file_handler.split_file_path(print_file)
            if file_handler.filename_validate(print_file):
                self._db_settings.setting_set("print_file", print_file)
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

        if not self._window_init:
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

        if self._printer_status == "Error":
            event.value_set(
                container_tag="printer_controls", tag="print_to_file", value=True
            )

        print(
            f"DBG {printer_info=} {self._printer_status=} {printer_info.state()=} {printer_info.defaultPrinter()=}"
        )

        return None

    def _print(self, event: qtg.Action) -> None:
        """Handles  print event
        Args:
            event (qtg.Action): The triggering event
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
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

            result, png_bytes = Create_DVD_Label(
                title=self.disk_title,
                title_font_path="/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
                menu_pages=self.dvd_menu_pages,
                menu_font_path="/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
                # menu_font_size=22,
                resolution=printer.logicalDpiX(),
            )

            if result == -1:
                print(f"DBG {result=}, {png_bytes.decode()=}")

            # with open("dvd_label.png", "wb") as png_file:
            #    png_file.write(png_bytes)
            image = QImage()
            image.loadFromData(png_bytes)
            painter = QPainter(printer)
            painter.drawImage(0, 0, image)
            painter.end()

        return None

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        print_folder = sys_consts.SPECIAL_PATH.DOCUMENTS
        if self._db_settings.setting_exist("print_folder"):
            print_folder = self._db_settings.setting_get("print_folder")

        print_file = ""
        if self._db_settings.setting_exist("print_file"):
            print_file = self._db_settings.setting_get("print_file")

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

        control_container = qtg.VBoxContainer(
            tag="printer_controls", align=qtg.Align.TOPRIGHT, margin_right=20
        )

        control_container.add_row(
            qtg.VBoxContainer().add_row(
                qtg.FormContainer().add_row(
                    printer_combo,
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
                ),
            ),
            qtg.Spacer(),
            qtg.HBoxContainer(margin_right=18).add_row(
                qtg.Button(
                    text="&Print", tag="print", callback=self.event_handler, width=10
                ),
                qtg.Button(
                    text="&Cancel", tag="cancel", callback=self.event_handler, width=10
                ),
            ),
        )
        return control_container
