""" 
    This module implements various common popup message boxes.

    Split from qtgui.py

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
import os
import pathlib
import shelve
import types
from dataclasses import field
from typing import Callable, Optional, Union, cast

import fs
import platformdirs
# import translators # 2023-09-30 # David Worboys removed auto translation because of connection and stability issues
from pathvalidate import ValidationError, validate_filepath
from PySide6 import QtCore as qtC
from PySide6 import QtGui as qtG

import file_utils
import sqldb
from file_utils import App_Path
from qtgui import (Action, Align, Button, Col_Def, Combo_Data, Combo_Item,
                   ComboBox, Command_Button_Container, Cursor, FolderView,
                   Font, Frame, Frame_Style, Grid, Grid_Col_Value,
                   GridContainer, HBoxContainer, Image, Label, LineEdit,
                   PopContainer, RadioButton, Spacer, Sys_Events, Sys_Icon,
                   TextEdit, VBoxContainer, Widget_Frame, sys_cursor)
from sys_consts import PROGRAM_NAME, SDELIM
from utils import Countries, Text_To_File_Name

# fmt: on


@dataclasses.dataclass
class PopAbout(PopContainer):
    """Instantiates a Popup About dialogue"""

    # Defining the variables that will be used in the class.
    app_text: str = ""
    informative_text: str = ""
    # noinspection PyTypeChecker
    informative_font: Font = field(default_factory=Font(size=12))
    width: int = 40
    height: int = 15
    # noinspection PyTypeChecker
    border: Widget_Frame = field(default_factory=Widget_Frame())
    icon: Union[str, qtG.QPixmap, qtG.QIcon] = None

    def __post_init__(self):
        """Sets up the PopAbout dialog - checks variables  and sets instance variables

        Creates a VBoxContainer, adds a Label, an Image, a TextEdit, and a Ok Button to the VBoxContainer, and
        then adds the VBoxContainer to the container attribute of the About class
        """
        super().__post_init__()

        assert isinstance(self.app_text, str), f"{self.app_text=}. Must be str"
        assert isinstance(
            self.informative_text, str
        ), f"{self.informative_text=}. Must be str"
        assert isinstance(
            self.informative_font, Font
        ), f"{self.informative_font=}. Must be Font"
        assert isinstance(self.border, Widget_Frame), f"{self.border=}. Must be Frame"

        container = VBoxContainer(
            tag="app_about",
            align=Align.CENTER,
            width=self.width,
            height=self.height,
            colpad=False,
        )

        if self.app_text.strip() != "":
            container.add_row(
                Label(
                    text=self.app_text,
                    tag="app_text",
                    width=self.width,
                    txt_align=Align.CENTER,
                    txt_font=Font(size=16),
                )
            )
            # container.add_row(Spacer())

        if self.icon is not None:
            container.add_row(Image(image=self.icon, tag="app_logo", width=20))
            # container.add_row(Spacer())

        if self.informative_text.strip() != "":
            container.add_row(
                TextEdit(
                    text=self.informative_text,
                    tag="info_text",
                    width=self.width - 2,
                    height=self.height - 3,
                    editable=False,
                    txt_align=Align.CENTER,
                    txt_font=self.informative_font,
                )  # border=self.border)
            )

        container.add_row(Spacer())

        container.add_row(
            Button(
                # container_tag=self.container_tag,
                tag="ok",
                text="&Ok",
                width=10,
                height=1,
                tune_vsize=7,
                callback=self.callback,
            )
        )

        self.container.add_row(container)

    def event_handler(self, event: Action):
        """Handles control event processing for the PopAbout class

        Args:
            event (Action): The event that triggered the control event.
        """

        # Closes the dialog box when the user clicks the OK button.
        if event.event == Sys_Events.CLICKED:
            if event.tag == "ok":
                self._result = event.tag
                self.dialog.close()


@dataclasses.dataclass
class PopFolderGet(PopContainer):
    """A pop-up dialogue that allows the user to select a folder."""

    title: str = "Select Folder"
    root_dir: str = ""
    create_folder: bool = False
    folder_edit: bool = False
    container_tag: str = "pop_folder"
    tag: str = "pop_folder"

    def __post_init__(self):
        """Checks the arguments and sets up the PopFolderGet class instance variables.

        The function adds a folder view and a line edit to the dialog with appropriate controls to drive the folder view.
        """
        super().__post_init__()

        assert isinstance(self.root_dir, str), f"{self.root_dir=}. Must be of type str"
        assert isinstance(
            self.create_folder, bool
        ), f"{self.create_folder=}. Must be bool"
        assert isinstance(self.folder_edit, bool), f"{self.folder_edit=}. Must be bool"

        if self.root_dir.strip() == "":
            self.root_dir = qtC.QDir.homePath()  # Default To User Home Folder

        if self.tooltip.strip() == "" and not self.folder_edit:
            self.tooltip = (
                "Use The Folder View (Below) Or The Button (Right) To Select Folders"
            )

        # Create a GUI for the user to select a folder.
        folder_buttons = HBoxContainer()
        folder_buttons.add_row(
            Button(
                callback=self.event_handler,
                tag="up_folder",
                height=1,
                width=1,
                icon=Sys_Icon.arrowup.get(),
                tooltip="Select The Parent Folder",
            )
        )

        if self.create_folder:
            folder_buttons.add_row(
                Button(
                    callback=self.event_handler,
                    tag="create_folder",
                    height=1,
                    width=1,
                    icon=App_Path("folder-plus.svg"),
                    tooltip="Create A New Folder",
                )
            )

        folder_container = HBoxContainer(tag="folder_edit")
        folder_container.add_row(
            LineEdit(
                text=f"{SDELIM}{self.root_dir}{SDELIM}",
                callback=self.event_handler,
                tag="folder",
                width=50,
                char_length=255,
                editable=True if self.folder_edit else False,
                tooltip=self.tooltip,
                buddy_control=folder_buttons,
            )
        )

        screen_container = VBoxContainer(tag="dir_container")
        screen_container.add_row(folder_container)
        screen_container.add_row(
            FolderView(
                tag="dir_view",
                callback=self.event_handler,
                dir_only=True,
                root_dir=self.root_dir.strip(),
                tooltip="Doubleclick On The Folder To Select or Open",
                click_expand=True,
                height=30,
            ),
        )
        screen_container.add_row(Spacer())

        self.container.add_row(screen_container)
        self.container.add_row(
            Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            ),
        )

    def event_handler(self, event: Action):
        """Process control events

        The function processes the event, and if the event is a click, double click, or a folder expansion or collapse,
        it updates the folder edit widget with the current folder

        Args:
            event (Action): Action

        Returns:
            int : 1, Ok, -1 is returned to indicate that the event has been handled and should not be processed further.
        """
        match int(event.event):  # Need int on matches for Nuitka to work
            case int(Sys_Events.CLICKED):
                match event.tag:
                    case "ok":
                        folder: str = event.value_get(
                            container_tag="folder_edit", tag="folder"
                        )

                        if folder is None or folder.strip() == "":
                            folder = self.root_dir

                        self._result = folder
                        self.close()

                    case "cancel":
                        self._result = ""
                        self.close()

                    case "dir_view":
                        folderview_widget: FolderView = cast(
                            FolderView,
                            event.widget_get(
                                container_tag="dir_container", tag="dir_view"
                            ),
                        )

                        if folderview_widget.expand_on_click:  # Ignore
                            current_folder = event.value_get(
                                container_tag="folder_edit", tag="folder"
                            ).strip()

                            if (
                                current_folder is None or current_folder.strip() == ""
                            ):  # Use supplied default
                                current_folder = self.root_dir

                            if (
                                current_folder is not None
                                and current_folder.strip() != ""
                            ):
                                folderview_widget.change_folder(current_folder)
                        else:
                            folders = ""
                            # Generate folder str, delim by ;. action.value contains list of folder items
                            for index, file_data in enumerate(event.value):
                                if 0 < index < len(event.value):
                                    folders += ";"

                                folders += file_data.path.strip()

                            event.value_set(
                                container_tag="folder_edit",
                                tag="folder",
                                value=f"{SDELIM}{folders}{SDELIM}",
                            )

                    case "create_folder":
                        self._create_folder(event)

                    case "up_folder":
                        folderview_widget = cast(
                            FolderView,
                            event.widget_get(
                                container_tag="dir_container", tag="dir_view"
                            ),
                        )

                        folder_sle_widget: LineEdit = cast(
                            LineEdit,
                            event.widget_get(container_tag="folder_edit", tag="folder"),
                        )

                        # Get text in single line edit
                        current_folder = folder_sle_widget.value_get().strip()

                        # Try placeholder text if no text #2021/06/30 DAW fix
                        if current_folder is None or current_folder.strip() == "":
                            current_folder = folder_sle_widget.text

                        if (
                            current_folder is None or current_folder.strip() == ""
                        ):  # Use supplied default
                            current_folder = self.root_dir

                        if current_folder is not None and current_folder.strip() != "":
                            parent_dir = fs.path.dirname(current_folder).strip()

                            folderview_widget.change_folder(parent_dir)  # Ignore
                            event.value_set(
                                container_tag="folder_edit",
                                tag="folder",
                                value=f"{SDELIM}{parent_dir}{SDELIM}",
                            )
            case int(Sys_Events.DOUBLECLICKED):
                if event.tag == "dir_view":
                    folder = event.value_get(container_tag="folder_edit", tag="folder")

                    if folder is None or folder.strip() == "":
                        folder = self.root_dir

                    self._result = folder.strip()
                    self.close()

            case int(Sys_Events.EXPANDED) | int(Sys_Events.COLLAPSED):
                if event.tag == "dir_view":
                    folders = ""
                    # Generate folder str, delim by ;. action.value contains list of folder items
                    for index, file_data in enumerate(event.value):
                        if 0 < index < len(event.value):
                            folders += ";"

                        folders += file_data.path.strip()

                    event.value_set(
                        container_tag="folder_edit",
                        tag="folder",
                        value=f"{SDELIM}{folders}{SDELIM}",
                    )

            case int(Sys_Events.FOCUSIN):
                pass
            case int(Sys_Events.FOCUSOUT):
                pass
            case int(
                Sys_Events.PRESSED
            ):  # Currently, not allowing user entry of folder
                if event.tag == "folder":
                    folderview_widget = cast(
                        FolderView,
                        event.widget_get(container_tag="dir_container", tag="dir_view"),
                    )
                    entered_folder = pathlib.Path(event.value).expanduser().resolve()

                    if (
                        entered_folder.is_file()
                    ):  # Only interested in folders in this pop-up
                        entered_folder = (
                            entered_folder.parent
                        )  # Strips file out if path

                    if entered_folder.exists():
                        if entered_folder.is_dir():
                            folderview_widget.change_folder(str(entered_folder))
                        else:
                            PopError(
                                title="Folder Object Not Supported...",
                                message=(
                                    f"{SDELIM}<{event.value}>{SDELIM} Object Is Not"
                                    " Supported!"
                                ),
                            ).show()
                    else:
                        PopError(
                            title="Folder Does Not Exist...",
                            message=(
                                f"{SDELIM}<{event.value}>{SDELIM} Is Not A Valid"
                                " Folder!"
                            ),
                        ).show()

                    return -1
        return 1

    def _create_folder(self, event: Action) -> None:
        """Creates a folder, via a user entered folder name

        Args:
            event: The action that triggered the callback.
        """

        current_folder = event.value_get(container_tag="folder_edit", tag="folder")

        if current_folder is None or current_folder.strip() == "":
            current_folder = self.root_dir

        folder_name = PopTextGet(title="Enter Folder Name").show()

        if (
            folder_name is not None
            and isinstance(folder_name, str)
            and folder_name.strip() != ""
        ):
            try:
                validate_filepath(folder_name, "auto")
                new_path = (
                    pathlib.Path(current_folder, folder_name).expanduser().resolve()
                )

                try:
                    if new_path.exists():
                        PopError(
                            title="Folder Already Exists...",
                            message=(
                                "Folder or File"
                                f" {SDELIM}<{folder_name}>{SDELIM} Already Exists!"
                            ),
                        ).show()
                    else:
                        if (
                            os.access(current_folder, os.W_OK)
                            and pathlib.Path(current_folder).is_dir()
                        ):
                            new_path.mkdir(parents=True)
                        else:
                            PopError(
                                title="Failed To Create Folder...",
                                message=(
                                    "No Write Access To Folder"
                                    f" {SDELIM}<{current_folder}>{SDELIM}"
                                ),
                            ).show()
                except OSError as e:
                    PopError(
                        title="Failed To Create Folder...",
                        message=(
                            f"Could Not Create Folder {SDELIM}<{folder_name}>{SDELIM}"
                        )
                        + f" {SDELIM}{current_folder}{SDELIM}  {SDELIM}{e}{SDELIM}",
                    ).show()

            except ValidationError as e:
                PopError(
                    title="Folder Name Not Valid...",
                    message=(
                        f"Folder Name {SDELIM}<{folder_name}>{SDELIM} Is Not Valid"
                        f" {SDELIM}{e.description}{SDELIM}"
                    ),
                ).show()


@dataclasses.dataclass
class PopMessage(PopContainer):
    """A PopMessage is a pop-up dialogue that displays a message to the user."""

    message: str = ""
    default_button: str = "ok"
    buttons: None | list[Button] | tuple[Button, ...] = None
    width: int = 40
    height: int = 3

    def __post_init__(self):
        """Initializes the PopMessage, checks arguments are Ok and sets instance variables."""

        super().__post_init__()

        assert (
            isinstance(self.message, str) and self.message.strip() != ""
        ), f"{self.message=}. Must be str"

        assert isinstance(self.default_button, str), f"{self.default_button=}. Must str"
        assert (
            isinstance(self.width, int) and self.width > 0
        ), f"{self.width=}. Must be int > 0"
        assert (
            isinstance(self.height, int) and self.height > 0
        ), f"{self.height=}. Must be int > 0"

        text_height = self.height
        text_width = self.width

        if "<" in self.message and ">" in self.message:
            self.message = self.message.replace("<", SDELIM)
            self.message = self.message.replace(">", SDELIM)

        # Make text fit
        if "\n" in self.message:
            self.message = f"\n".join(
                f"{s : ^{self.width}}" for s in self.message.split("\n")
            )
        else:
            self.message = self.message.center(self.width, " ")

        # Creates a GUI with a grid container, a text edit and appropriate buttons.
        container = GridContainer(
            align=Align.CENTER, width=self.width, height=self.height
        )

        if self.icon is not None:
            container.add_row(
                Image(
                    image=self.icon,
                    tag="message_logo",
                    width=48,
                    height=48,
                    pixel_unit=True,
                    frame=Widget_Frame(frame=Frame.PLAIN, frame_style=Frame_Style.NONE),
                ),
                TextEdit(
                    text=self.message,
                    tag="informative_text",
                    txt_font=Font(backcolor="LightYellow"),
                    width=text_width,
                    height=text_height,
                    editable=False,
                    frame=Widget_Frame(
                        frame=Frame.SUNKEN, frame_style=Frame_Style.STYLED
                    ),
                    txt_align=Align.CENTER,
                ),
            )
        else:
            container.add_row(
                TextEdit(
                    text=self.message,
                    tag="informative_text",
                    txt_font=Font(backcolor="LightYellow"),
                    width=text_width,
                    height=text_height + 1,
                    editable=False,
                    frame=Widget_Frame(
                        frame=Frame.SUNKEN, frame_style=Frame_Style.STYLED
                    ),
                    txt_align=Align.CENTER,
                )
            )

        button_container = HBoxContainer(
            align=Align.RIGHT, width=self.width, margin_right=9
        )

        if self.buttons is None:
            button_container.add_row(
                Button(
                    container_tag=self.container_tag,
                    tag="ok",
                    text="&Ok",
                    width=10,
                    # height=2,
                    # tune_vsize=7,
                    callback=self.callback,
                )
            )
        else:
            for button in self.buttons:
                assert isinstance(
                    button, Button
                ), f"{button=}. Must be an instance of Button"

                button_container.add_row(
                    Button(
                        container_tag=self.container_tag,
                        tag=button.tag,
                        text=button.text,
                        # width=button.width,
                        # height= button.height,
                        tune_vsize=button.tune_vsize,
                        tune_hsize=button.tune_hsize,
                        icon=button.icon,
                        callback=(
                            self.callback
                            if button.callback is None
                            else button.callback
                        ),
                    )
                )

        self.container.add_row(container)
        self.container.add_row(button_container)

    def event_handler(self, event: Action):
        """Processes the control events and performs appropriate actions. Sets the _result attribute. Overridden in
        decedent classes

        Args:
            event (Action): The event that was triggered.

        Returns:
            int: 1
        """
        # Closes the window when the user clicks the OK button.
        if event.event == Sys_Events.CLICKED:
            if event.tag == "ok":
                self._result = event.tag
                self.close()
        return 1


@dataclasses.dataclass
class PopError(PopMessage):
    """Pop-up error dialogue.

    Subclass of the PopMessage class, used to display error messages
    """

    title: str = "Error"

    def __post_init__(self):
        # Constructor for the PopMessage class
        # Sets the icon of the message box to a critical icon.
        self.icon: Union[qtG.QIcon, qtG.QPixmap, str, None] = (
            Sys_Icon.messagecritical.get(iconformat=False)
        )
        super().__post_init__()


@dataclasses.dataclass
class PopOKCancel(PopMessage):
    """Pop-up OK Cancel dialogue.

    Subclass of the `PopMessage` class which adds a `cancel_callback` attribute and a `cancel`button to the `PopMessage
    class"""

    cancel_callback: Optional[
        Union[Callable, types.FunctionType, types.MethodType, types.LambdaType]
    ] = None

    def __post_init__(self):
        """Constructor for the PopOKCancel class.
        If the buttons attribute is None, then set it to a tuple of two Button objects - Ok and Cancel
        """
        if self.buttons is None:
            self.buttons = (
                Button(text="&Ok", tag="ok"),
                Button(
                    text="&Cancel",
                    tag="cancel",
                    callback=(
                        self.callback
                        if self.cancel_callback is None
                        else self.cancel_callback
                    ),
                ),
            )
        super().__post_init__()

    def event_handler(self, event: Action):
        """Processes the control events and performs appropriate actions. Sets the _result attribute. Overridden in
        descendants

        Args:
            event (Action): Calling event.
        """
        match int(event.event):
            case int(Sys_Events.CLICKED):
                match event.tag:
                    case "ok":
                        self._result = event.tag
                        self.close()

                    case "cancel":
                        button: Button = cast(
                            Button, event.widget_get(event.container_tag, event.tag)
                        )
                        result = button.callback(event)

                        assert isinstance(result, int) and result in (
                            -1,
                            1,
                        ), f"{result=}. Must be int 1 : Ok, -1 : Failed"

                        if result == 1:
                            self._result = event.tag

                            self.close()


@dataclasses.dataclass
class PopOKCancelApply(PopOKCancel):
    """Pop-up OK Cancel Apply dialogue ."""

    apply_callback: Optional[
        Union[Callable, types.FunctionType, types.MethodType, types.LambdaType]
    ] = None

    def __post_init__(self):
        """Constructor for the PopOKCancelApply class.

        If the user didn't specify any buttons, then set Ok, Cancel and Apply buttons
        """
        if self.buttons is None:
            self.buttons = (
                Button(text="&Ok", tag="ok"),
                Button(text="&Cancel", tag="cancel", callback=self.cancel_callback),
                Button(text="&Apply", tag="apply", callback=self.apply_callback),
            )
        super().__post_init__()

        assert isinstance(
            self.apply_callback, Callable
        ), f"{self.apply_callback=}. Must be function | method | lambda"

    def event_handler(self, event: Action):
        """Processes the control events and performs appropriate actions. Sets the _result attribute. Overridden in
        descendants.

        Args:
            event (Action): Calling event.
        """
        match int(event.event):
            case int(Sys_Events.CLICKED):
                match event.tag:
                    case "ok":
                        self._result = event.tag
                        self.close()
                    case "cancel":
                        if self.cancel_callback is not None:
                            result = self.cancel_callback(event)
                        else:
                            result = 1

                        assert isinstance(result, int) and result in (
                            -1,
                            1,
                        ), f"{result=}. Must be int 1 : Ok, -1 : Failed"

                        if result == 1:
                            self._result = event.tag
                            self.close()
                    case "apply":
                        self.apply_callback(event)


@dataclasses.dataclass
class PopOptions(PopContainer):
    """Pop-up Options dialogue that displays a list of options in a radio button format and returns the
    selected option"""

    message: str = ""
    options: Optional[dict[str, str]] = field(default_factory=dict)
    translate: bool = True

    def __post_init__(self):
        """Constructor for the PopOptions class that checks the arguments and sets instance variables.

        The function creates a radio button for each item in the list of options, and then adds a button container with
        an OK and Cancel button
        """
        super().__post_init__()
        assert isinstance(
            self.options, (dict)
        ), f"{self.options=}. Must be a dict dict[text:tag]"
        assert (
            len(self.options) > 0
        ), f"{self.options=}. Must be a dict with at least one item in it"
        assert isinstance(self.message, str), f"{self.message=}. Mut be str"

        self.original_option: str = ""
        self._options: dict = {}
        max_width: int = 0
        radio_selection_width: int = len(self.trans_str(self.message))

        # Creates a GUI for the dialog box with a list of options.
        option_container = VBoxContainer(tag="option_container", text=self.message)

        # for index, option in enumerate(self.options):
        index = 0
        for option, tag in self.options.items():
            if index == 0:
                self.original_option = option

            tag = f"{tag}|{index}".strip().replace(" ", "")

            if len(option) > max_width:
                max_width = len(option) + 5

            option_container.add_row(
                RadioButton(
                    text=f"{SDELIM}{option}{SDELIM}",
                    callback=self.event_handler,
                    tag=tag,
                    checked=True if index == 0 else False,
                    translate=self.translate,
                )
            )

            if len(self.trans_str(option)) > radio_selection_width:
                radio_selection_width = len(self.trans_str(option))

            self._options[tag] = option

            index += 1

        option_container.width = radio_selection_width

        self.container.add_row(option_container)
        self.container.add_row(Spacer())
        self.container.add_row(
            Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            )
        )

    def event_handler(self, event: Action):
        """Control event handler for the PopOptions dialogue.

        If the user clicks the "ok" button, then the value of the selected option is saved to the _result variable and
        the dialogue is closed. If the user clicks the "cancel" button, then the dialogue is closed and the _result
        variable is set to an empty string

        Args:
            event (Action): Calling event
        """
        match int(event.event):
            case int(Sys_Events.CLICKED):
                match event.tag:
                    case "ok":
                        for tag, option in self._options.items():
                            if event.value_get(
                                container_tag="option_container", tag=tag
                            ):
                                self._result = tag.split("|")[0]
                                break

                        self.close()
                    case "cancel":
                        for key, value in self._options.items():
                            if event.value_get(
                                container_tag="option_container", tag=key
                            ):
                                if value != self.original_option:
                                    if (
                                        PopYesNo(
                                            container_tag="selection_changed",
                                            title="Selection Changed..",
                                            message="Save Changes?",
                                        ).show()
                                        == "yes"
                                    ):
                                        self._result = value
                                        self.close()

                        self._result = ""
                        self.close()


@dataclasses.dataclass
class PopTextGet(PopContainer):
    """PopTextGet dialogue that has a text entry field and Ok and Cancel buttons"""

    title: str = "Enter Text"
    default_txt: str = ""
    mask: str = ""
    width: int = 32
    char_length: int = 255
    label: str = "Enter Text"
    label_above: bool = True

    def __post_init__(self):
        """Constructor for the PopTextGet dialogue that checks arguments and sets instance variables."""
        super().__post_init__()

        assert isinstance(self.label_above, bool), f"{self.label_above=}. Must be bool"

        # Create a GUI with a text box, and a label .
        layout_container = VBoxContainer(tag="text")

        if self.label_above:
            layout_container.add_row(Label(text=self.label))

        layout_container.add_row(
            LineEdit(
                text=self.default_txt,
                tag="text",
                label=self.label if not self.label_above else "",
                width=self.width,
                char_length=self.char_length,
                input_mask=self.mask,
                tooltip=self.tooltip,
            )
        )

        self.container.add_row(layout_container)
        # self.container.add_row(Spacer())
        self.container.add_row(
            Command_Button_Container(
                ok_callback=self.event_handler,
                cancel_callback=self.event_handler,
                margin_right=9,
            )
        )

    def event_handler(self, event: Action):
        """Control event handler for the PopTextGet dialogue.

        If the user clicks the OK button, the text in the text box is returned and is set in the _result variable.
        If the user clicks the Cancel button, an empty string is returned in the _result variable.

        Args:
            event (Action): Action
        """
        if event.event == Sys_Events.CLICKED:
            if event.tag == "ok":
                self._result = event.value_get(container_tag="text", tag="text").strip()
                self.close()
            else:
                self._result = ""
                self.close()


@dataclasses.dataclass
class PopYesNo(PopMessage):
    """A PopYesNo dialogue that has Yes and No buttons"""

    def __post_init__(self):
        """Constructor for the PopYesNo dialogue that checks arguments and sets instance variables."""
        if self.icon is None:
            self.icon: Union[qtG.QIcon, qtG.QPixmap, str, None] = (
                Sys_Icon.messagequestion.get(iconformat=False)
            )

        # Add  Yes and No Buttons to the  GUI if none supplied.
        if self.buttons is None:
            self.buttons = (
                Button(text="&Yes", tag="yes"),
                Button(text="&No", tag="no"),
            )
        super().__post_init__()

    def event_handler(self, event: Action):
        """Control event handler for the PopYesNo dialogue.

        Sets the _result variable to the tag of the button that was clicked.

        Args:
            event (Action): Action
        """
        match int(event.event):
            case int(Sys_Events.CLICKED):
                match event.tag:
                    case "yes":
                        self._result = event.tag
                        self.close()
                    case "no":
                        self._result = event.tag
                        self.close()
                    case _:
                        super(event)


@dataclasses.dataclass
class PopWarn(PopYesNo):
    """A Pop-up Warning dialogue that has a warning icon and a default button of "Ok" if yesno is False"""

    yesno: bool = True

    def __post_init__(self):
        """Constructor for the PopWarn dialogue that checks arguments and sets instance variables.

        Sets the icon, checks if the yesno argument is a bool, and if it is not, it sets the buttons to a tuple with a
        single Ok Button
        """
        self.icon: Union[qtG.QIcon, qtG.QPixmap, str, None] = (
            Sys_Icon.messagewarning.get(iconformat=False)
        )

        assert isinstance(self.yesno, bool), f"{self.yesno=}. Must be bool"

        if not self.yesno:
            if self.buttons is None:
                self.buttons = (Button(text="&Ok", tag="ok"),)

        super().__post_init__()


@dataclasses.dataclass
class Langtran_Popup(PopContainer):
    """Allow users to provide translations - should be in langtran.py but got circular import error"""

    tag: str = "langtran_popup"

    # Private instance variable
    _db_settings: sqldb.App_Settings | None = None
    _db_file: str = "lang_tran"
    _path = platformdirs.user_data_dir(appname=PROGRAM_NAME)

    def __post_init__(self) -> None:
        """Sets-up the form"""

        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(PROGRAM_NAME)
        self.DB = sqldb.SQLDB(
            appname=PROGRAM_NAME,
            dbpath=self._path,
            dbfile=self._db_file,
            suffix=".db",
            dbpassword="",
        )

        error_status = self.DB.get_error_status()

        self._error_code = error_status.code
        self._error_msg = error_status.message

        super().__post_init__()  # This statement must be last

    def _get_language_code(self, event: Action) -> str:
        """Gets the language code from the country combo-box

        Args:
            event (Action): Triggering event

        Returns:
            str: The country code in 2 char  ISO language code
        """
        assert isinstance(event, Action), f"{event=}. Must be Action"

        combo_value: Combo_Data = event.value_get(
            container_tag="langtran_controls", tag="countries"
        )

        return combo_value.data

    def event_handler(self, event: Action) -> None:
        """Handles  form events
        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, Action), f"{event=}. Must be Action"
        if "|" in event.tag:  # Grid control tag
            tag = event.tag.split("|")[1]
            row_unique_id = int(
                event.tag.split("|")[0]
            )  # Grid button tag has the row_id embedded as the 1st element and delimitered by |
        else:
            row_unique_id = -1
            tag = event.tag

        match event.event:
            case Sys_Events.WINDOWPOSTOPEN:
                self._windows_open_handler(event)

            case Sys_Events.CLICKED:
                match tag:
                    case "auto_trans":
                        self._auto_translate(event)
                    case "copy_text":
                        phrase_grid: Grid = cast(
                            Grid,
                            event.widget_get(
                                container_tag="langtran_controls",
                                tag="phrase_grid",
                            ),
                        )
                        row = phrase_grid.row_from_item_id(row_unique_id)

                        if row >= 0:
                            base_phrase = phrase_grid.value_get(
                                row=row, col=phrase_grid.colindex_get("base_phrase")
                            )
                            clipboard = self.parent_app.app_get.clipboard()
                            clipboard.setText(base_phrase)
                    case "export":
                        self._export_handler(event)
                    case "import":
                        self._import_handler(event)
                    case "ok":
                        if self._process_ok(event) == 1:
                            self.set_result(event.tag)
                            super().close()
                    case "save":
                        self._save_handler(event)

            case Sys_Events.CLEAR_TYPING_BUFFER:
                if isinstance(event.value, Grid_Col_Value):
                    grid_col_value: Grid_Col_Value = event.value

                    grid_col_value.grid = self

                    phrase: str = grid_col_value.value
                    row = grid_col_value.row
                    col = grid_col_value.col
                    user_data = grid_col_value.user_data

                    phrase_grid: Grid = cast(
                        Grid,
                        event.widget_get(
                            container_tag="langtran_controls",
                            tag="phrase_grid",
                        ),
                    )

                    phrase_grid.value_set(
                        value=phrase, row=row, col=col, user_data=user_data
                    )
                    phrase_grid.changed = True

            case Sys_Events.INDEXCHANGED:
                match event.tag:
                    case "countries":
                        self._country_combo_handler(event)

    def _import_handler(self, event: Action):
        """Imports into the phrase grid the user selected language translation file located in the users document folder

        Args:
            event (Action): Triggering event
        """
        assert isinstance(event, Action), f"{event=}. Must be Action"

        db_path: str = platformdirs.user_documents_dir()
        file_handler = file_utils.File()
        db_path = file_handler.file_join(dir_path=db_path, file_name="langtran")

        if not file_handler.file_exists(db_path):
            if file_handler.make_dir(db_path) == -1:
                PopError(
                    title="Failed To Create Folder...",
                    message=f"Failed To Create Language  Folder : {db_path}",
                ).show()
                return None

        phrase_grid: Grid = cast(
            Grid,
            event.widget_get(
                container_tag="langtran_controls",
                tag="phrase_grid",
            ),
        )
        country_combo: ComboBox = cast(
            ComboBox,
            event.widget_get(
                container_tag="langtran_controls",
                tag="countries",
            ),
        )

        langtran_files = file_handler.filelist(db_path, ("dat",))
        if not langtran_files.files:
            PopMessage(
                title="No Language Files Available...",
                message=f"There are no language files in : {db_path}!",
            ).show()
            return None

        langtran_dict = {}
        langtran_names = {}

        for file in langtran_files.files:
            _, name, _ = file_handler.split_file_path(file)

            langtran_dict[name] = file_handler.file_join(db_path, name)
            langtran_names[name] = name

        result = PopOptions(
            title="Choose Language File...",
            message="Please Choose Language File",
            options=langtran_names,
            translate=False,
        ).show()

        if result in langtran_dict:
            file = langtran_dict[result]
            country = result.replace("_", " ").split(".langtran")[0]
            result = country_combo.select_text(
                select_text=country,
                case_sensitive=False,
                partial_match=False,
            )

            phrase_grid.clear()

            try:
                with shelve.open(file) as db:
                    db_data = db.get("lang_tran")

                    for row_index, grid_row in enumerate(db_data):
                        for col_index, grid_col_item in enumerate(grid_row):
                            grid_item_value = grid_col_item[0]
                            grid_item_user_data = grid_col_item[1]

                            phrase_grid.value_set(
                                row=row_index,
                                col=col_index,
                                value=grid_item_value,
                                user_data=grid_item_user_data,
                            )

            except Exception as e:
                PopError(
                    title="Failed To Import...",
                    message=(
                        f"Failed To Import {SDELIM}{file} -"
                        f" {e if e is not None else ''}{SDELIM}"
                    ),
                ).show()
                return None

    def _export_handler(self, event: Action) -> None:
        """Exports the phrase grid as a language translation file to the users document folder under langtran

        Args:
            event (Action): Triggering event
        """
        assert isinstance(event, Action), f"{event=}. Must be Action"

        db_path: str = platformdirs.user_documents_dir()
        file_handler = file_utils.File()
        db_path = file_handler.file_join(dir_path=db_path, file_name="langtran")

        if not file_handler.file_exists(db_path):
            if file_handler.make_dir(db_path) == -1:
                PopError(
                    title="Failed To Create Folder...",
                    message=f"Failed To Create Language  Folder : {db_path}",
                ).show()
                return None

        phrase_grid: Grid = cast(
            Grid,
            event.widget_get(
                container_tag="langtran_controls",
                tag="phrase_grid",
            ),
        )
        country_combo: ComboBox = cast(
            ComboBox,
            event.widget_get(
                container_tag="langtran_controls",
                tag="countries",
            ),
        )

        country_data: Combo_Data = country_combo.value_get()

        project_file_name = file_handler.file_join(
            dir_path=db_path,
            file_name=Text_To_File_Name(country_data.display),
            ext="langtran",
        )

        row_data = []

        for row in range(phrase_grid.row_count):
            grid_col_values = []

            for col in range(phrase_grid.col_count):
                grid_value = phrase_grid.value_get(row=row, col=col)
                grid_user_data = phrase_grid.userdata_get(row=row, col=col)

                grid_col_values.append((grid_value, grid_user_data))

            row_data.append(grid_col_values)

        try:
            with shelve.open(project_file_name) as db:
                db["lang_tran"] = row_data

        except Exception as e:
            PopError(
                title="Failed To Export...",
                message=f"Failed to export {SDELIM}{project_file_name} - {e}{SDELIM}",
            ).show()
            return None

        PopMessage(
            title="Exported...",
            message=f"Exported {SDELIM}{project_file_name}{SDELIM}",
        ).show()
        return None

    def _country_combo_handler(self, event: Action):
        """Handles the change of country in the country combo box

        Args:
            event (Action): Triggering event
        """

        if event.widget_exist(
            container_tag="langtran_controls",
            tag="phrase_grid",
        ):
            trans_table = self._get_trans_table(event)

            phrase_grid: Grid = cast(
                Grid,
                event.widget_get(
                    container_tag="langtran_controls",
                    tag="phrase_grid",
                ),
            )

            size_warning_label = event.widget_get(
                container_tag="langtran_controls",
                tag="phrase_too_long",
            )

            size_warning_label.visible_set(False)

            for row_index in range(phrase_grid.row_count):
                result_row = phrase_grid.userdata_get(
                    row=row_index, col=phrase_grid.colindex_get("base_phrase")
                )
                base_lang_id = result_row[0]
                base_phrase = result_row[1]

                if (
                    base_lang_id in trans_table
                ):  # Populate with translated phrases if available
                    lang_phrase = trans_table[base_lang_id][1]

                    if len(lang_phrase) > len(base_phrase):
                        phrase_grid.checkitemrow_set(
                            row=row_index,
                            col=phrase_grid.colindex_get("lang_phrase"),
                            checked=True,
                        )

                        size_warning_label.visible_set(True)

                    phrase_grid.value_set(
                        value=lang_phrase,
                        row=row_index,
                        col=phrase_grid.colindex_get("lang_phrase"),
                        user_data=trans_table[base_lang_id],
                    )
                else:
                    phrase_grid.value_set(
                        value="",
                        row=row_index,
                        col=phrase_grid.colindex_get("lang_phrase"),
                        user_data=(),
                    )

            phrase_grid.changed = False

    def _windows_open_handler(self, event: Action) -> None:
        """Performs the tasks needed when the window opnes

        Args:
            event (Action): Triggering event
        """
        trans_table: dict = {}
        phrase_grid: Grid = cast(
            Grid,
            event.widget_get(
                container_tag="langtran_controls",
                tag="phrase_grid",
            ),
        )

        # Default country combo to the country specified in the application-selected country
        if self._db_settings.setting_exist(
            setting_name="app_country",
        ):
            app_country = self._db_settings.setting_get(
                setting_name="app_country",
            )

            if app_country:
                country_combo: ComboBox = cast(
                    ComboBox,
                    event.widget_get(
                        container_tag="langtran_controls",
                        tag="countries",
                    ),
                )

                result = country_combo.select_text(
                    select_text=app_country,
                    case_sensitive=False,
                    partial_match=False,
                )

        trans_table = self._get_trans_table(event)

        # Populate the phrase table with base phrases and, if any, translated phrases from the app selected country
        trans_sql = (
            f"{sqldb.SQL.SELECT} id, word {sqldb.SQL.FROM} lang_tran"
            f" {sqldb.SQL.WHERE} language_code {sqldb.SQL.IS_NULL}"
        )

        result = self.DB.sql_execute(trans_sql, debug=False)
        error = self.DB.get_error_status()

        size_warning_label = event.widget_get(
            container_tag="langtran_controls",
            tag="phrase_too_long",
        )

        size_warning_label.visible_set(False)

        if error.code == 1 and result:  # Have base words
            for row_index, result_row in enumerate(result):
                base_lang_id = result_row[0]
                base_phrase = result_row[1]

                phrase_grid.row_widget_set(
                    row=row_index,
                    col=phrase_grid.colindex_get("copy"),
                    widget=Button(
                        tag="copy_text",
                        width=1,
                        height=1,
                        icon=file_utils.App_Path("text.svg"),
                        tooltip="Copy Text To Clipboard",
                        callback=self.event_handler,
                    ),
                )

                phrase_grid.value_set(
                    value=base_phrase,
                    row=row_index,
                    col=phrase_grid.colindex_get("base_phrase"),
                    user_data=result_row,
                )

                if base_lang_id in trans_table:
                    lang_phrase = trans_table[base_lang_id][1]

                    if len(lang_phrase) > len(base_phrase):
                        phrase_grid.checkitemrow_set(
                            row=row_index,
                            col=phrase_grid.colindex_get("lang_phrase"),
                            checked=True,
                        )

                        size_warning_label.visible_set(True)

                    phrase_grid.value_set(
                        value=lang_phrase,
                        row=row_index,
                        col=phrase_grid.colindex_get("lang_phrase"),
                        user_data=trans_table[base_lang_id],
                    )
        phrase_grid.changed = False

    def _get_trans_table(self, event) -> dict[str, tuple[str, str]]:
        """Get a dict loaded with translations, if any, for the current language in the combobox

        Args:
            event (Action): The triggering event

        Returns:
            dict[str,tuple[str,str]]: A dict loaded with translations, if any, for the current language
                - key is base_lag_id tuple is (trans_lang_id, translated_phrase)
        """
        trans_table = {}

        trans_sql = (
            f"{sqldb.SQL.SELECT} base_lang_id, id, word"
            f" {sqldb.SQL.FROM} lang_tran"
            f" {sqldb.SQL.WHERE} language_code ="
            f" '{self._get_language_code(event)}'"
        )
        result = self.DB.sql_execute(trans_sql, debug=False)
        error = self.DB.get_error_status()

        if error.code == 1 and result:  # Have translated words for language
            for row_index, result_row in enumerate(result):
                base_lang_id = result_row[0]
                trans_id = result_row[1]
                trans_phrase = result_row[2]

                trans_table[base_lang_id] = (trans_id, trans_phrase)

        return trans_table

    def _auto_translate(self, event: Action):
        """Attempts to automatically translate the base phrases
        2023-09-30 David Worboys removed auto translation because of connection and stability issues

        Args:
            event (Action): The triggering event

        Returns:

        """
        assert isinstance(event, Action), f"{event=}. Must be Action"

        if (
            PopYesNo(
                title="Access The Internet...",
                message="Auto-Translation Will Use The Internet!  Continue?",
            ).show()
            == "yes"
        ):
            phrase_grid: Grid = cast(
                Grid,
                event.widget_get(
                    container_tag="langtran_controls",
                    tag="phrase_grid",
                ),
            )
            language_code = self._get_language_code(event).lower()

            with sys_cursor(Cursor.hourglass):
                try:
                    # 2023-09-30 David Worboys removed auto translation because of connection and stability issues
                    # if language_code not in translators.get_languages():
                    #    PopError(
                    #        title="Language Is Not Supported...",
                    #        message=(
                    #            "MS Bing Does Not Support  Translating That Language!"
                    #        ),
                    #    ).show()
                    #    return None

                    for row in range(phrase_grid.row_count):
                        base_phrase = phrase_grid.value_get(row=row, col=0)
                        # 2023-09-30 David Worboys removed auto translation because of connection and stability issues
                        # trans_text = translators.translate_text(
                        #    query_text=base_phrase,
                        #    to_language=language_code,
                        # )

                        # if trans_text:
                        #    phrase_grid.value_set(
                        #        value=trans_text,
                        #        row=row,
                        #        col=1,
                        #        user_data=None,
                        #    )
                except Exception as e:
                    PopError(
                        title="Language Translation Failed...",
                        message=f"Language Translation Failed!{SDELIM}\n {e} {SDELIM}",
                    ).show()

    def _save_handler(self, event: Action) -> int:
        """Saves the translated text to the database

        Args:
            event (Action): The triggering event

        Returns:
            int : 1 Saved Ok, -1 Save Failed

        """
        assert isinstance(event, Action), f"{event=}. Must be Action"

        phrase_grid: Grid = cast(
            Grid,
            event.widget_get(
                container_tag="langtran_controls",
                tag="phrase_grid",
            ),
        )
        language_code = self._get_language_code(event).lower()

        with sys_cursor(Cursor.hourglass):
            for row in range(phrase_grid.row_count):
                base_phrase = phrase_grid.value_get(
                    row=row, col=phrase_grid.colindex_get("base_phrase")
                )
                trans_phrase = phrase_grid.value_get(
                    row=row, col=phrase_grid.colindex_get("lang_phrase")
                )

                if trans_phrase.strip():
                    trans_sql = (
                        f"{sqldb.SQL.SELECT} id, word"
                        f" {sqldb.SQL.FROM} lang_tran"
                        f" {sqldb.SQL.WHERE} word = '{base_phrase}'"
                        f" {sqldb.SQL.AND} language_code"
                        f" {sqldb.SQL.IS_NULL}"
                    )

                    result = self.DB.sql_execute(trans_sql, debug=False)
                    error = self.DB.get_error_status()

                    if error.code == 1 and result:  # Have a base word
                        base_lang_id = result[0][0]

                        trans_sql = (
                            f"{sqldb.SQL.SELECT} id, word"
                            f" {sqldb.SQL.FROM} lang_tran"
                            f" {sqldb.SQL.WHERE} base_lang_id ="
                            f" '{base_lang_id}'"
                            f" {sqldb.SQL.AND} language_code ="
                            f" '{language_code}'"
                        )

                        result = self.DB.sql_execute(trans_sql, debug=False)
                        error = self.DB.get_error_status()

                        if error.code == 1:
                            trans_phrase = trans_phrase.replace("'", "''")
                            if result:  # Have a translated phrase (update)
                                trans_sql = (
                                    f"{sqldb.SQL.UPDATE} lang_tran"
                                    f" {sqldb.SQL.SET} word ="
                                    f" '{trans_phrase}'"
                                    f" {sqldb.SQL.WHERE} base_lang_id ="
                                    f" '{base_lang_id}'"
                                    f" {sqldb.SQL.AND} language_code ="
                                    f" '{language_code}'"
                                )
                            else:  # insert
                                trans_sql = (
                                    f"{sqldb.SQL.INSERTINTO} lang_tran"
                                    " (base_lang_id,word,language_code)"
                                    f" {sqldb.SQL.VALUES} ('{base_lang_id}','{trans_phrase}','{language_code}')"
                                )

                            result = self.DB.sql_execute(trans_sql, debug=False)
                            error = self.DB.get_error_status()

                        if error.code == -1:
                            PopError(
                                title="Database Error...",
                                message=f"{SDELIM}{error.message}{SDELIM}",
                            ).show()
                            return -1

            if self.DB.sql_commit == -1:
                error = self.DB.get_error_status()
                PopError(
                    title="Database Error...",
                    message=f"{SDELIM}{error.message}{SDELIM}",
                ).show()
                return -1
            else:
                phrase_grid.changed = False
        return 1

    def _process_ok(self, event: Action) -> int:
        """
        Handles processing the ok button.

        Args:
            event (Action): The triggering event.
        Returns:
            int: Returns 1 if the ok process id good, -1 otherwise
        """
        assert isinstance(event, Action), f"{event=}. Must be Action"

        phrase_grid: Grid = cast(
            Grid,
            event.widget_get(
                container_tag="langtran_controls",
                tag="phrase_grid",
            ),
        )

        changed = False

        for row_index in range(phrase_grid.row_count):
            if (
                phrase_grid.valueorig_get(
                    row=row_index, col=phrase_grid.colindex_get("lang_phrase")
                )
                is None
            ):
                orig_value = ""
            else:
                orig_value = phrase_grid.valueorig_get(
                    row=row_index, col=phrase_grid.colindex_get("lang_phrase")
                ).strip()

            current_value = phrase_grid.value_get(row=row_index, col=1).strip()

            if orig_value != current_value:
                changed = True
                break

        if changed:
            if (
                PopYesNo(
                    title="Save Changes...", message="Save Translated Text Changes?"
                ).show()
                == "yes"
            ):
                if self._save_handler(event) == -1:
                    return -1

        self.set_result("")

        return 1

    def layout(self) -> VBoxContainer:
        """Generate the form UI layout"""

        country_combo_items = [
            Combo_Item(
                display=f"{country.flag} {country.normal_name}",
                data=country.language,
                icon=None,
                user_data=None,
            )
            for country in Countries().get_countries
            if country.language != "en"  # English is my base language!
        ]

        country_combo = ComboBox(
            tag="countries",
            width=30,
            items=country_combo_items,
            translate=False,
            display_na=False,
            callback=self.event_handler,
            buddy_control=HBoxContainer(width=70).add_row(
                Spacer(width=3),
                Label(
                    text="Checked Phrases Are Too Long And Will Cause Layout Issues!",
                    tag="phrase_too_long",
                    width=60,
                    visible=False,
                    txt_font=Font(forecolor="red"),
                ),
            ),
            # 2023-09-30 David Worboys removed auto translation because of connection and stability issues
            # buddy_control=Button(
            #    text="Auto-Translate",
            #    tag="auto_trans",
            #    callback=self.event_handler,
            #    height=1,
            #    tooltip="Automatically translate with MS Bing",
            # ),
        )

        langtran_control_container = VBoxContainer(
            tag="langtran_controls", align=Align.TOPLEFT
        )

        phrase_col_def = (
            Col_Def(
                label="",
                tag="copy",
                width=2,
                editable=False,
                checkable=False,
            ),
            Col_Def(
                label="Base Phrase",
                tag="base_phrase",
                width=50,
                editable=False,
                checkable=False,
            ),
            Col_Def(
                label="Language Phrase",
                tag="lang_phrase",
                width=50,
                editable=True,
                checkable=True,
            ),
        )

        phrase_grid = Grid(
            tag="phrase_grid",
            noselection=True,
            height=15,
            col_def=phrase_col_def,
            callback=self.event_handler,
        )

        langtran_control_container.add_row(
            country_combo,
            phrase_grid,
        )

        control_container = VBoxContainer(tag="form_controls", align=Align.TOPRIGHT)

        control_container.add_row(
            langtran_control_container,
            HBoxContainer(margin_right=5).add_row(
                Button(tag="save", text="&Save", callback=self.event_handler, width=10),
                Button(
                    tag="export", text="&Export", callback=self.event_handler, width=10
                ),
                Button(
                    tag="import", text="&Import", callback=self.event_handler, width=10
                ),
                Spacer(width=71),
                Button(tag="ok", text="&Ok", callback=self.event_handler, width=10),
            ),
        )

        return control_container
