import dataclasses

from PySide6.QtGui import QImage, QPainter
from PySide6.QtPrintSupport import QPrinterInfo, QPrinter

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from dvdarch_utils import Create_DVD_Label
from sys_config import DVD_Menu_Page


@dataclasses.dataclass
class Print_DVD_Label_Popup(qtg.PopContainer):
    """Prints DVD Labels/Inserts Popup"""

    disk_title: str = ""
    dvd_menu_pages: list[DVD_Menu_Page] = dataclasses.field(default_factory=list)

    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _printer_info: QPrinterInfo = QPrinterInfo()

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
                pass
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
                                value=f"{sys_consts.SDELIM}{folder}{sys_consts.SDELIM}",
                            )
                    case "print_file_select":
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
                            if file_handler.filename_validate(print_file):
                                self._db_settings.setting_set("print_file", print_file)
                                event.value_set(
                                    container_tag="printer_controls",
                                    tag="print_file",
                                    value=f"{sys_consts.SDELIM}{print_file}{sys_consts.SDELIM}",
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
            case qtg.Sys_Events.INDEXCHANGED:
                if event.tag == "available_printers":
                    print(f"DBG IC {event.value=}")
                    selected_printer: str = event.value.data
                    printer_info = self._printer_info.printerInfo(selected_printer)
                    print(f"DBG IC {selected_printer=} {printer_info.state()=}")

    def _print(self, event: qtg.Action) -> None:
        """Handles  print event
        Args:
            event (qtg.Action): The triggering event
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            selected_printer: qtg.Combo_Data = event.value_get(
                container_tag="printer_controls", tag="available_printers"
            )
            printer_info = self._printer_info.printerInfo(selected_printer.data)

            print(f"DBG {selected_printer=} {printer_info.state()=}")
            printer = QPrinter(printer_info)
            # printer.setPrinterName(selected_printer.data)
            printer.setResolution(300)
            printer.setColorMode(QPrinter.Color)
            # printer.setOutputFileName("test.pdf")

            if printer_info.state() == QPrinter.Idle:
                state = "Idle"
            elif printer_info.state() == QPrinter.Active:
                state = "Active"
            elif printer_info.state() == QPrinter.Aborted:
                state = "Aborted"
            elif printer_info.state() == QPrinter.Error:
                state = "Error"
            else:
                state = "Unknown"

            print(
                f"DBG {state=} {printer.isValid()=} {printer_info.printerName()=} {printer.printerState()=} {printer.printerName()=} {printer.width()=} {printer.height()=} {printer.widthMM()=}  {printer.logicalDpiX()=} {printer.logicalDpiY()=}"
            )

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

            with open("dvd_label.png", "wb") as png_file:
                png_file.write(png_bytes)
            image = QImage()
            image.loadFromData(png_bytes)
            # image = QPixmap(png_bytes).toImage()
            print(f"DBG {image.width()} {image.height()}")
            painter = QPainter(printer)
            # painter.begin(image)
            painter.drawImage(0, 0, image)
            painter.end()

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
                        label="Print File",
                        tag="print_file",
                        text=print_file,
                        callback=self.event_handler,
                        editable=False,
                        width=60,
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
