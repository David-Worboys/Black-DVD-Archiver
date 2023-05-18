"""
    Qt library gui wrapper intended to make Qt easier to use in applications

    Copyright (C) 2020  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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
# TODO Split file into multiple files - well this is bigger than Ben Hur now, needs its own git project,
# doco, examples etc. Code needs review as well...sigh, where to find the time!

# Tell Black to leave this block alone (realm of isort)
# fmt: off
import copy
import dataclasses
import datetime
import functools
import math
import os
import pathlib
import platform
import random
import re
import string
import sys
import time
import types
import uuid
from collections import deque, namedtuple
from contextlib import contextmanager
from dataclasses import field
from enum import Enum, IntEnum
from typing import (Callable, ClassVar, Literal, NoReturn, Optional, Union,
                    cast, overload)

import numpy as np
import PySide6.QtCore as qtC
import PySide6.QtGui as qtG
import PySide6.QtWidgets as qtW
import shiboken6  # type: ignore
from attrs import define
from PySide6.QtGui import QCloseEvent

from file_utils import App_Path
from langtran import Lang_Tran
from sys_consts import SDELIM
from utils import Coords, Is_Complied, amper_length, country_date_formatmask

# fmt: on

g_application = None

# Constants
DEFAULT_FONT_SIZE = 10
MAX_CHARS = 32767
MENU_SEPERATOR = "---"


def Command_Button_Container(
    ok_callback: Callable,
    cancel_callback: Callable = None,
    apply_callback: Callable = None,
    button_width=10,
    margin_left: int = -1,
    margin_right: int = -1,
) -> "HBoxContainer":
    """
    Creates a horizontal box container for buttons, following platform UX guidelines.

    Args:
        ok_callback (function): Callback function for the "Ok" button.
        cancel_callback (function, optional): Callback function for the "Cancel" button. Defaults to None.
        apply_callback (function, optional): Callback function for the "Apply" button. Defaults to None.
        button_width (int): Width of the command buttons
        margin_left (int) : Left margin
        margin_right (int) : Right margin

    Raises:
        AssertionError: If the callbacks are not callable.

    Returns:
        HBoxContainer: A horizontal box container for buttons.
    """

    # Assert that the callbacks are callable
    assert ok_callback is None or callable(ok_callback), "Invalid  callback"
    assert cancel_callback is None or callable(
        cancel_callback
    ), "Invalid Cancel callback"
    assert apply_callback is None or callable(apply_callback), "Invalid Apply callback"
    assert (
        isinstance(button_width, int) and button_width >= 7
    ), f"{button_width=}. Must be int > 7"
    assert (
        isinstance(margin_left, int) and margin_left == -1 or margin_left >= 0
    ), f"{margin_left=}. Must be int == -1 or >= 0"
    assert (
        isinstance(margin_right, int) and margin_right == -1 or margin_right >= 0
    ), f"{margin_right=}. Must be int == -1 or >= 0"

    platform_name = platform.system()

    button_container = HBoxContainer(
        align=Align.RIGHT,
        tag="command_buttons",
        margin_left=margin_left,
        margin_right=margin_right,
    )

    if platform_name == "Windows":
        button_container.add_row(
            Button(text="Ok", tag="ok", callback=ok_callback, width=button_width)
        )

        if cancel_callback:
            button_container.add_row(
                Button(
                    text="Cancel",
                    tag="cancel",
                    callback=cancel_callback,
                    width=button_width,
                )
            )

        if apply_callback:
            button_container.add_row(
                Button(
                    text="Apply",
                    tag="apply",
                    callback=apply_callback,
                    width=button_width,
                )
            )

    elif platform_name == "Linux":
        button_container.add_row(
            Button(text="Ok", tag="ok", callback=ok_callback, width=button_width)
        )

        if apply_callback:
            button_container.add_row(
                Button(
                    text="Apply",
                    tag="apply",
                    callback=apply_callback,
                    width=button_width,
                )
            )

        if cancel_callback:
            button_container.add_row(
                Button(
                    text="Cancel",
                    tag="cancel",
                    callback=cancel_callback,
                    width=button_width,
                )
            )

    elif platform_name == "Darwin":  # macOS
        if cancel_callback:
            button_container.add_row(
                Button(
                    text="Cancel",
                    tag="cancel",
                    callback=cancel_callback,
                    width=button_width,
                )
            )

        if apply_callback:
            button_container.add_row(
                Button(
                    text="Apply",
                    tag="apply",
                    callback=apply_callback,
                    width=button_width,
                )
            )

        button_container.add_row(
            Button(text="Ok", tag="ok", callback=ok_callback, width=button_width)
        )

    return button_container


def Question_Button_Container(
    yes_callback: Callable,
    no_callback: Callable,
    margin_left: int = -1,
    margin_right: int = -1,
) -> "HBoxContainer":
    """
    Displays a message box with a question prompt, following platform UX guidelines.

    Args:
        yes_callback (Callable): Callback function for the "Yes" button.
        no_callback (Callable): Callback function for the "No" button.
        margin_left (int) : Left margin
        margin_right (int) : Right margin

    Returns:
        qtg.HBoxContainer: A horizontal box container for buttons.
    """
    assert callable(yes_callback), "Invalid 'yes' callback."
    assert callable(no_callback), "Invalid 'no' callback."
    assert (
        isinstance(margin_left, int) and margin_left == -1 or margin_left >= 0
    ), f"{margin_left=}. Must be int == -1 or >= 0"
    assert (
        isinstance(margin_right, int) and margin_right == -1 or margin_right >= 0
    ), f"{margin_right=}. Must be int == -1 or >= 0"

    button_container = HBoxContainer(
        align=Align.RIGHT,
        tag="question_buttons",
        margin_left=margin_left,
        margin_right=margin_right,
    )

    platform_name = platform.system()

    if platform_name == "Windows":
        button_container.add_row(Button(tag="yes", text="Yes", callback=yes_callback))
        button_container.add_row(Button(tag="no", text="No", callback=no_callback))

    elif platform_name == "Linux":
        button_container.add_row(Button(tag="no", text="No", callback=no_callback))
        button_container.add_row(Button(tag="yes", text="Yes", callback=yes_callback))

    elif platform_name == "Darwin":  # macOS
        button_container.add_row(Button(tag="yes", text="Yes", callback=yes_callback))
        button_container.add_row(Button(tag="no", text="No", callback=no_callback))

    return button_container


def Get_Window_ID(
    parent_app: "QtPyApp",
    parent: qtW.QWidget | qtW.QFrame | None,
    self_item: Union[
        "_Container", "_qtpyBase_Control", "_qtpySDI_Frame", "_Dialog", None
    ],
) -> int:
    """
    Get the window id (winId) of the parent Qt widget.

    Args:
        - parent_app (QtPyApp): The parent QtPy application object.
        - parent (qtW.QWidget | qtW.QFrame | None): The parent widget/frame of the target widget.
        - self_item (Union["_Container" , "_qtpyBase_Control","_qtpySDI_Frame", "_Dialog", None]):
        The target widget to get the winId from.

    Returns:
        int: The winId of the target widget.

    """
    assert isinstance(
        parent_app, QtPyApp
    ), f"{parent_app=}. {type(parent_app)=}. Must be a QtPyApp object"
    assert parent is None or isinstance(
        parent, (qtW.QWidget, qtW.QFrame)
    ), f"{parent=}. {type(parent)=}. Must be a None, QWidget or QFrame object"
    assert self_item is None or isinstance(
        self_item, (_Dialog, _Container, _qtpyBase_Control, _qtpySDI_Frame)
    ), (
        f"{self_item=}. {type(self_item)=}.  Must be a None, _Container or"
        " _qtpyBase_Control object"
    )

    if self_item is not None and hasattr(self_item, "dialog"):
        window_id = self_item.dialog.window().winId()
    elif self_item is not None and hasattr(self_item, "window"):
        window_id = self_item.window().winId()
    elif (
        self_item is not None
        and hasattr(self_item, "_widget")
        and self_item._widget is not None
    ):  # Cannot use guiwidget_get in the if because if it is None then a runtime error is triggered
        window_id = self_item.guiwidget_get.window().winId()
    elif parent is not None and hasattr(parent, "dialog"):
        window_id = parent.dialog.window().winId()
    elif parent is not None and hasattr(parent, "window"):
        window_id = parent.window().winId()
    elif (
        parent is not None and hasattr(parent, "_widget") and parent._widget is not None
    ):  # Cannot use guiwidget_get in the if because if it is None then a runtime error is triggered
        window_id = parent.guiwidget_get.window().winId()
    else:
        window_id = parent_app.main_frame_window_id

    return window_id


@dataclasses.dataclass(slots=True)
class Grid_Item:
    row_index: int
    tag: str
    current_value: any
    user_data: any


# An enumeration of all the application events that can be handled by the GUI.
class Sys_Events(IntEnum):
    """This is used to determine which event handler type is ro be passed to the event handler call when a GUI event is
    triggered.
    """

    APPINIT = 0  #: The application is being initialised
    APPPOSTINIT = 1  #: The application just finished initialising
    APPCLOSED = 2  #: The application is being closed
    APPEXIT = 3  #: The application is exiting
    BADINPUT = 4  #: The input is not valid
    ACTIVATED = 5  #: The widget has been activated
    CHANGED = 6  #: The widget has changed
    CLEAR_TYPING_BUFFER = 7  # A Grid widget has is about to cleat the type buffer
    CLICKED = 8  #: The widget has been clicked
    COLLAPSED = 9  #: A node has been collapsed
    CLOSED = 10  #: The widget has been closed
    CURSORCHANGED = 11  #: The cursor has changed
    DATECHANGED = 12  #: The date has changed
    EDITCHANGED = 13  #: The text has changed
    ENTERED = 14  #: The widget has been entered
    EXPANDED = 15  #: A node has been expanded
    DOUBLECLICKED = 16  #: The widget has been double-clicked
    FOCUSIN = 17  #: The widget has gained focus
    FOCUSOUT = 18  #: The widget has lost focus
    GROUPINIT = 19  #: The group has been initialised
    HIGHLIGHTED = 20  #: The widget has been highlighted
    INDEXCHANGED = 21  #: The index has changed
    MAXCHARS = 22  #: The maximum number of characters has been reached
    MENUCLICKED = 23  #: The menu has been clicked
    MOVED = 24  #: A control generated a moved event
    PRESSED = 25  #: The widget has been pressed
    RELEASED = 26  #: The widget has been released
    POPUP = 27  #: The popup has been shown
    POPCAL = 28  #: The popup calendar has been shown
    POSTINIT = 28  #: The post init event has been triggered
    SCROLLH = 30  #: The horizontal scroll bar has been moved
    SCROLLV = 31  #: The vertical scroll bar has been moved
    SELECTIONCHANGED = 32  #: The selection has changed
    TEXTCHANGED = 33  #: The text has changed
    TEXTEDIT = 34  #: The text has been edited
    TIMECHANGED = 35  #: The time has changed
    TOGGLED = 36  #: The widget has been toggled
    TRIGGERED = 37  #: The widged has triggered
    WINDOWCLOSED = 38  #: The window has been closed
    WINDOWOPEN = 39  #: The window has been opened
    WINDOWPOSTOPEN = 40  #: Triggered after the window has been opened


# Tell Black to leave this block alone
# fmt: off
# A set of HTML colours.
TEXT_COLORS = \
    ("Aliceblue", "Antiquewhite", "Aqua", "Aquamarine", "Azure", "Beige", "Bisque", "Black", "BlanchedAlmond",
        "Blue", "BlueViolet", "Brown", "BurlyWood", "CadetBlue", "Chartreuse", "Chocolate", "Coral", "CornflowerBlue",
        "Cornsilk", "Crimson", "Cyan", "DarkBlue", "DarkCyan", "DarkGoldenRod", "DarkGray", "DarkGrey", "DarkGreen",
        "DarkKhaki", "DarkMagenta", "DarkOliveGreen", "DarkOrange", "DarkOrchid", "DarkRed", "DarkSalmon",
        "DarkSeaGreen", "DarkSlateBlue", "DarkSlateGray", "DarkSlateGrey", "DarkTurquoise", "DarkViolet", "DeepPink",
        "DeepSkyBlue", "DimGray", "DimGrey", "DodgerBlue", "FireBrick", "FloralWhite", "ForestGreen", "Fuchsia",
        "Gainsboro", "GhostWhite", "Gold", "GoldenRod", "Gray", "Grey", "Green", "GreenYellow", "HoneyDew", "HotPink",
        "IndianRed", "Indigo", "Ivory", "Khaki", "Lavender", "LavenderBlush", "LawnGreen", "LemonChiffon", "LightBlue",
        "LightCoral", "LightCyan", "LightGoldenRodYellow", "LightGray", "LightGrey", "LightGreen", "LightPink",
        "LightSalmon", "LightSeaGreen", "LightSkyBlue", "LightSlateGray", "LightSlateGrey", "LightSteelBlue",
        "LightYellow", "Lime", "LimeGreen", "Linen", "Magenta", "Maroon", "MediumAquaMarine", "MediumBlue",
        "MediumOrchid", "MediumPurple", "MediumSeaGreen", "MediumSlateBlue", "MediumSpringGreen", "MediumTurquoise",
        "MediumVioletRed", "MidnightBlue", "MintCream", "MistyRose", "Moccasin", "NavajoWhite", "Navy", "OldLace",
        "Olive", "OliveDrab", "Orange", "OrangeRed", "Orchid", "PaleGoldenRod", "PaleGreen", "PaleTurquoise",
        "PaleVioletRed", "PapayaWhip", "PeachPuff", "Peru", "Pink", "Plum", "PowderBlue", "Purple", "Red", "RosyBrown",
        "RoyalBlue", "SaddleBrown", "Salmon", "SandyBrown", "SeaGreen", "SeaShell", "Sienna", "Silver", "SkyBlue",
        "SlateBlue", "SlateGray", "SlateGrey", "Snow", "SpringGreen", "SteelBlue", "Tan", "Teal", "Thistle", "Tomato",
        "Turquoise", "Violet", "Wheat", "White", "WhiteSmoke", "Yellow", "YellowGreen"
        )
# fmt: on


# `Layout` is an enumeration of the possible layout types for a `Form` or `Grid` object
class Layout(IntEnum):
    FORM = 0
    GRID = 1
    HORZ = 2
    VERT = 3


@dataclasses.dataclass(slots=True)
# A Char_Pixel_Size is a class that used by widgets to determine char size, it has two attributes: height and width
class Char_Pixel_Size:
    height: int
    width: int

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.height, int) and self.height >= 0
        ), f"{self.height=}. Must be int >= 0"
        assert (
            isinstance(self.width, int) and self.width >= 0
        ), f"{self.width=}. Must be int >= 0"


@dataclasses.dataclass(slots=True)
# `Size` is a class used by widget controls that has two attributes, `height` and `width`
class Size:
    height: int
    width: int

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.height, int) and self.height >= 0
        ), f"{self.height=}. Must be int >= 0"
        assert (
            isinstance(self.width, int) and self.width >= 0
        ), f"{self.width=}. Must be int >= 0"


@dataclasses.dataclass(slots=True)
# `Col_Def` is a class used by combo boxes that has four attributes: `label`, `tag`, `width`, and `editable`
class Col_Def:
    label: str
    tag: str
    width: int
    editable: bool
    checkable: bool

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert isinstance(self.label, str), f"{self.label=}. Must be a str"
        assert isinstance(self.tag, str), f"{self.tag=}. Must be a str"
        assert isinstance(self.width, int), f"{self.width=}. Must be a int"
        assert isinstance(self.editable, bool), f"{self.editable=}. Must be bool"
        assert isinstance(self.checkable, bool), f"{self.checkable=}. Must be bool"


@dataclasses.dataclass(slots=True)
# `Combo_Data` is a class used by combo boxes that contains an index, a display string, and a data value
class Combo_Data:
    index: int
    display: str
    data: None | str | int | float | bytes | bool
    user_data: None | str | int | float | bytes | bool

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.index, int) and self.index >= 0
        ), f"{self.index=}. Must be int >= 0"
        assert isinstance(self.display, str), f"{self.display=}. Must be str"
        assert (
            isinstance(self.data, (str, int, float, bytes, bool)) or self.data is None
        ), f"{self.data=}. Must be None | str | int | float | bytes | bool"
        assert (
            isinstance(self.user_data, (str, int, float, bytes, bool))
            or self.user_data is None
        ), f"{self.user_data=}. Must be None | str | int | float | bytes | bool"


@dataclasses.dataclass(slots=True)
# `Combo_Item` is a class used by combo boxes that holds a display string, a data value, an icon, and a user data value.
class Combo_Item:
    display: str
    data: None | str | int | float | bytes | bool
    icon: None | str | qtG.QPixmap | qtG.QIcon
    user_data: None | str | int | float | bytes | bool

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert isinstance(self.display, str), f"{self.display=}. Must be str"
        assert (
            isinstance(self.data, (str, int, float, bytes, bool)) or self.data is None
        ), f"{self.data=}. Must be None | str | int | float | bytes | bool"
        assert (
            isinstance(self.icon, (str, qtG.QPixmap, qtG.QIcon)) or self.icon is None
        ), f"{self.icon=}. Must be None | str | qtG.QPixmap | qtG.QIcon"
        assert (
            isinstance(self.user_data, (str, int, float, bytes, bool))
            or self.user_data is None
        ), f"{self.user_data=}. Must be None | str | int | float | bytes | bool"


@dataclasses.dataclass(slots=True)
# `Rect_Changed` is a class used byy rectangles to that has two attributes, `rect_id` and `coords`
class Rect_Changed:
    rect_id: str
    coords: Coords

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.rect_id, str) and self.rect_id.strip() != ""
        ), f"{self.rect_id=}. Must be a non-empty string"
        assert isinstance(
            self.coords, Coords
        ), f"{self.coords=}. Must be a an of type Coords"


@dataclasses.dataclass(slots=True)
# `Overlap_Rect` is a class that represents the overlap between two rectangles
class Overlap_Rect:
    a_rect_id: str
    a_coords: Coords
    b_rect_id: str
    b_coords: Coords

    def __post_init__(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.a_rect_id, str) and self.a_rect_id.strip() != ""
        ), f"{self.a_rect_id}. Must be a non-empty str"
        assert isinstance(self.a_coords, Coords), f"{self.a_coords=}. Must be Coords"
        assert (
            isinstance(self.b_rect_id, str) and self.b_rect_id.strip() != ""
        ), f"{self.b_rect_id}. Must be a non-empty str"
        assert isinstance(self.b_coords, Coords), f"{self.b_coords=}. Must be Coords"


# By default, widgets are 10 chars wide by 1 char high
WIDGET_SIZE = Size(height=1, width=10)  # In CHARACTERS
BUTTON_SIZE = Size(height=2, width=10)  # In CHARACTERS
CHECKBOX_SIZE = Size(height=1, width=10)  # In CHARACTERS
COMBOBOX_SIZE = Size(height=2, width=10)  # In CHARACTERS
LINEEDIT_SIZE = Size(height=1, width=19)  # In CHARACTERS
RADIOBUTTON_SIZE = Size(height=1, width=10)  # In CHARACTERS


# Widget alignment
class Align(Enum):
    LEFT = qtC.Qt.AlignLeft
    CENTER = qtC.Qt.AlignCenter
    CENTERLEFT = qtC.Qt.AlignCenter | qtC.Qt.AlignLeft
    CENTERRIGHT = qtC.Qt.AlignCenter | qtC.Qt.AlignRight
    RIGHT = qtC.Qt.AlignRight
    TOP = qtC.Qt.AlignTop
    TOPCENTER = qtC.Qt.AlignTop
    TOPLEFT = qtC.Qt.AlignTop | qtC.Qt.AlignLeft
    TOPRIGHT = qtC.Qt.AlignTop | qtC.Qt.AlignRight
    BOTTOM = qtC.Qt.AlignBottom
    VCENTER = qtC.Qt.AlignVCenter
    HCENTER = qtC.Qt.AlignHCenter
    BOTTOMCENTER = qtC.Qt.AlignBottom | qtC.Qt.AlignCenter
    BOTTOMLEFT = qtC.Qt.AlignBottom | qtC.Qt.AlignLeft
    BOTTOMRIGHT = qtC.Qt.AlignBottom | qtC.Qt.AlignRight


# Creates a dictionary with the keys being the values of the enum ALIGN and the values being the corresponding CSS
# values.
Align_SS_Text = {
    Align.LEFT: "text-align:left",
    Align.CENTER: "text-align:center",
    Align.RIGHT: "text-align:right",
    Align.TOP: "text-align:top",
    Align.BOTTOM: "text-align:bottom",
}


# Font Properties
class Font_Weight(Enum):
    THIN = qtG.QFont.Thin
    EXTRALIGHT = qtG.QFont.ExtraLight
    LIGHT = qtG.QFont.Light
    NORMAL = qtG.QFont.Normal
    MEDIUM = qtG.QFont.Medium
    DEMIBOLD = qtG.QFont.DemiBold
    BOLD = qtG.QFont.Bold
    EXTRABOLD = qtG.QFont.ExtraBold
    BLACK = qtG.QFont.Black


# Creating a dictionary that maps the font weight to a string.
Font_Weight_Text = {
    Font_Weight.THIN: "thin",
    Font_Weight.EXTRALIGHT: "extralight",
    Font_Weight.LIGHT: "light",
    Font_Weight.NORMAL: "normal",
    Font_Weight.MEDIUM: "medium",
    Font_Weight.DEMIBOLD: "demibold",
    Font_Weight.BOLD: "bold",
    Font_Weight.EXTRABOLD: "extrabold",
    Font_Weight.BLACK: "black",
}


# The `FONTSTYLE` class is an enumeration of the possible font styles
class Font_Style(IntEnum):
    NORMAL = 0
    ITALIC = 1
    OBLIQUE = 2


# Widget frame appearance
class Frame(Enum):
    PLAIN = qtW.QFrame.Plain
    RAISED = qtW.QFrame.Raised
    SUNKEN = qtW.QFrame.Sunken


# Widget frame style
class Frame_Style(Enum):
    BOX = qtW.QFrame.Box
    PANEL = qtW.QFrame.Panel
    HLINE = qtW.QFrame.HLine
    NONE = qtW.QFrame.NoFrame
    VLINE = qtW.QFrame.VLine
    WPANEL = qtW.QFrame.WinPanel
    STYLED = qtW.QFrame.StyledPanel


# The `CURSOR` class is an enumeration of the different types of cursors that can be used in a `Qt` application
class Cursor(Enum):
    arrow = qtC.Qt.ArrowCursor
    arrowup = qtC.Qt.UpArrowCursor
    bitmap = qtC.Qt.BitmapCursor
    busy = qtC.Qt.BusyCursor
    crosshair = qtC.Qt.CrossCursor
    diagleft = qtC.Qt.SizeFDiagCursor
    diagright = qtC.Qt.SizeBDiagCursor
    dragmove = qtC.Qt.DragMoveCursor
    dragcopy = qtC.Qt.DragCopyCursor
    draglink = qtC.Qt.DragLinkCursor
    forbidden = qtC.Qt.ForbiddenCursor
    handpointer = qtC.Qt.PointingHandCursor
    handclosed = qtC.Qt.ClosedHandCursor
    handopen = qtC.Qt.OpenHandCursor
    hourglass = qtC.Qt.WaitCursor
    invisible = qtC.Qt.BlankCursor
    question = qtC.Qt.WhatsThisCursor
    sizeall = qtC.Qt.SizeAllCursor
    sizehoriz = qtC.Qt.SizeHorCursor
    sizevert = qtC.Qt.SizeVerCursor
    splith = qtC.Qt.SplitHCursor
    splitv = qtC.Qt.SplitVCursor


# `SYSICON` is a class that contains all the system icons that can be used in a `a `Qt` application
class Sys_Icon(Enum):
    arrowback = qtW.QStyle.SP_ArrowBack
    arrowdown = qtW.QStyle.SP_ArrowDown
    arrowforward = qtW.QStyle.SP_ArrowForward
    arrowleft = qtW.QStyle.SP_ArrowLeft
    arrowright = qtW.QStyle.SP_ArrowRight
    arrowup = qtW.QStyle.SP_ArrowUp
    browserreload = qtW.QStyle.SP_BrowserReload
    browserstop = qtW.QStyle.SP_BrowserStop
    commandlink = qtW.QStyle.SP_CommandLink
    computericon = qtW.QStyle.SP_ComputerIcon
    custombase = qtW.QStyle.SP_CustomBase
    desktopitcon = qtW.QStyle.SP_DesktopIcon
    dialogapply = qtW.QStyle.SP_DialogApplyButton
    dialogcancel = qtW.QStyle.SP_DialogCancelButton
    dialogclose = qtW.QStyle.SP_DialogCloseButton
    dialogdiscard = qtW.QStyle.SP_DialogDiscardButton
    dialoghelp = qtW.QStyle.SP_DialogHelpButton
    dialogno = qtW.QStyle.SP_DialogNoButton
    dialogok = qtW.QStyle.SP_DialogOkButton
    dialogopen = qtW.QStyle.SP_DialogOpenButton
    dialogreset = qtW.QStyle.SP_DialogResetButton
    dialogsave = qtW.QStyle.SP_DialogSaveButton
    dialogyes = qtW.QStyle.SP_DialogYesButton
    dirclosed = qtW.QStyle.SP_DirClosedIcon
    dirhome = qtW.QStyle.SP_DirHomeIcon
    dir = qtW.QStyle.SP_DirIcon
    dirlink = qtW.QStyle.SP_DirLinkIcon
    diropen = qtW.QStyle.SP_DirOpenIcon
    dockclose = qtW.QStyle.SP_DockWidgetCloseButton
    drivecd = qtW.QStyle.SP_DriveCDIcon
    drivedvd = qtW.QStyle.SP_DriveDVDIcon
    drivefd = qtW.QStyle.SP_DriveFDIcon
    drivehd = qtW.QStyle.SP_DriveHDIcon
    drivenetwork = qtW.QStyle.SP_DriveNetIcon
    fileback = qtW.QStyle.SP_FileDialogBack
    filecontents = qtW.QStyle.SP_FileDialogContentsView
    filedetailed = qtW.QStyle.SP_FileDialogDetailedView
    fileend = qtW.QStyle.SP_FileDialogEnd
    fileinfo = qtW.QStyle.SP_FileDialogInfoView
    filelist = qtW.QStyle.SP_FileDialogListView
    filenew = qtW.QStyle.SP_FileDialogNewFolder
    filestart = qtW.QStyle.SP_FileDialogStart
    fileparent = qtW.QStyle.SP_FileDialogToParent
    file = qtW.QStyle.SP_FileIcon
    filelink = qtW.QStyle.SP_FileLinkIcon
    mediapause = qtW.QStyle.SP_MediaPause
    mediaplay = qtW.QStyle.SP_MediaPlay
    mediabackward = qtW.QStyle.SP_MediaSeekBackward
    mediaforward = qtW.QStyle.SP_MediaSeekForward
    medianext = qtW.QStyle.SP_MediaSkipForward
    mediaprevious = qtW.QStyle.SP_MediaSkipBackward
    mediastop = qtW.QStyle.SP_MediaStop
    mediavol = qtW.QStyle.SP_MediaVolume
    mediavolmute = qtW.QStyle.SP_MediaVolumeMuted
    messagecritical = qtW.QStyle.SP_MessageBoxCritical
    messageinformation = qtW.QStyle.SP_MessageBoxInformation
    messagequestion = qtW.QStyle.SP_MessageBoxQuestion
    messagewarning = qtW.QStyle.SP_MessageBoxWarning
    titlebarclose = qtW.QStyle.SP_TitleBarCloseButton
    titlebarhelp = qtW.QStyle.SP_TitleBarContextHelpButton
    titlebarmax = qtW.QStyle.SP_TitleBarMaxButton
    titlebarmin = qtW.QStyle.SP_TitleBarMinButton
    titlebarnormal = qtW.QStyle.SP_TitleBarNormalButton
    titlebarshade = qtW.QStyle.SP_TitleBarShadeButton
    titlebarunshade = qtW.QStyle.SP_TitleBarUnshadeButton
    toolbarhorz = qtW.QStyle.SP_ToolBarHorizontalExtensionButton
    toolbarvert = qtW.QStyle.SP_ToolBarVerticalExtensionButton
    trash = qtW.QStyle.SP_TrashIcon

    @overload
    def get(
        self, iconformat: bool = True, width: int = 48, height: int = 48
    ) -> qtG.QIcon:
        ...

    @overload
    def get(
        self, iconformat: bool = True, width: int = 48, height: int = 48
    ) -> qtG.QIcon | qtG.QPixmap:
        ...

    def get(
        self, iconformat: bool = True, width: int = 48, height: int = 48
    ) -> qtG.QIcon | qtG.QPixmap:
        """Returns the system icon - in either icon format (default) or pixmap.
        If `iconformat` is False, then the `width`and `height` of the pixmap can be set.

        Args:
            iconformat (bool): A flag indicating whether to return the icon in icon format (default) or pixmap.
            width (int): The width of the pixmap if `iconformat` is `False`. Defaults to 48.
            height (int): The height of the pixmap if `iconformat` is `False`. Defaults to 48.

        Returns:
            Union[qtGui.QIcon, qtG.QPixmap]: The system icon, either as a `QtGui.QIcon` or `QtGui.QPixmap`,
            depending on the value of the `iconformat` parameter.
        """
        assert isinstance(iconformat, bool), f"{iconformat=}. Must be bool"
        assert isinstance(width, int), f"{width=}. Must be int"
        assert isinstance(height, int), f"{height=}. Must be int"

        try:
            if iconformat:
                return qtW.QApplication.instance().style().standardIcon(self.value)
            else:
                return (
                    qtW.QApplication.instance()
                    .style()
                    .standardIcon(self.value)
                    .pixmap(qtC.QSize(width, height))
                )
        except Exception as e:
            raise AssertionError(f"Application Not Running {e} ")


@contextmanager
def sys_cursor(cursor: Cursor):
    """
    Sets the cursor to the cursor passed in, and then restores the cursor to the original cursor.

    Args:
        cursor (CURSOR): CURSOR
    """
    assert isinstance(cursor, Cursor), f"{cursor=}. Must Be CURSOR"
    try:
        qtW.QApplication.setOverrideCursor(qtG.QCursor(cursor.value))
        yield
    finally:
        qtW.QApplication.restoreOverrideCursor()


def cursor_on(cursor: Cursor):
    """
    Sets the cursor to the specified cursor type

    Args:
        cursor (CURSOR): CURSOR
    """
    assert isinstance(cursor, Cursor), f"{cursor=}. Must Be CURSOR"
    if qtW.QApplication is not None and qtW.QApplication.instance() is not None:
        qtW.QApplication.setOverrideCursor(qtG.QCursor(cursor.value))


def cursor_off():
    """
    Restores the cursor to its default state
    """
    if qtW.QApplication is not None and qtW.QApplication.instance() is not None:
        qtW.QApplication.restoreOverrideCursor()


@dataclasses.dataclass(slots=True)
# `tags` is a class used by _Container
class tags:
    container_tag: str
    tag: str
    value: any
    valid: bool

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.container_tag, str) and self.container_tag.strip() != ""
        ), f"{self.container_tag=}. Must be a non-empty str"
        assert (
            isinstance(self.tag, str) and self.tag.strip() != ""
        ), f"{self.tag=}. Must be a non-empty str"
        assert isinstance(self.valid, bool), f"{self.valid=}. Must bool"


@dataclasses.dataclass(slots=True)
# Used by _Container to store the data for scroll widgets
class widget_def:
    widget: "_qtpyBase_Control"
    gui_widget: qtW.QWidget

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert isinstance(
            self.widget, _qtpyBase_Control
        ), f"{self.widget=}. Must be type _qtpyBase_Control"
        assert isinstance(
            self.gui_widget, qtW.QWidget
        ), f"{self.gui_widget=}. Must be type qtW.QWidget"


@dataclasses.dataclass(slots=True)
# Used by _Dateedit to store the data.
class _Date_Tuple:
    year: int
    month: int
    day: int

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert (
            isinstance(self.year, int) and self.year > 0
        ), f"{self.year=}. Must be an int > 0"
        assert (
            isinstance(self.month, int) and 1 >= self.month <= 12
        ), f"{self.month=}. Must be an int between 1 and 12"
        assert (
            isinstance(self.day, int) and 1 >= self.day <= 28
            if self.month == 2
            else 1 >= self.day <= 31
        ), f"{self.day=}. Must be an int between 1 and 28/31 depending on month"


@dataclasses.dataclass(slots=True)
# This class is used by the _Container to store the values of a snapshot before and after it is modified
class _Snapshot_Modified_Values:
    snap1: any
    snap1_valid: bool
    snap2: any
    snap2_valid: bool

    def _post_init(self):
        # Checking the arguments passed to the constructor are of the correct type.
        assert isinstance(self.snap1_valid, bool), f"{self.snap1_valid=}. Must be bool"
        assert isinstance(self.snap2_valid, bool), f"{self.snap2_valid=}. Must be bool"


class _qtpyBase:
    """Private Base Class For All Qtpy classes"""

    parent: object
    _lang_tran: ClassVar[Lang_Tran] = Lang_Tran()

    def __init__(self, parent: object):
        """Configures the base class for all qtpy classes.

        If the parent is not an instance of _qtpyBase, raise a RuntimeError

        Args:
            parent (object): The parent object.
        """
        if not isinstance(parent, _qtpyBase):
            raise RuntimeError(f"{parent=} is not an instance of _qtpyBase")

        self._parent = parent
        window_id = -1

    def dump(self) -> None:
        """Prints all the attributes of an object"""
        for attr in dir(self):
            if hasattr(self, attr):
                print("obj.%s = %s" % (attr, getattr(self, attr)))

    @property
    def parent_get(self) -> Optional["_qtpyBase"]:
        """Returns the parent object.

        If the object has a parent, return the parent. Otherwise, return None

        Returns:
            The parent of the object.
        """
        if hasattr(self, "_parent"):
            return self._parent
        else:
            return None


@define(slots=True)
# class Colors(_qtpyBase): # Removed to get a Nuitka Compile
class Colors:
    """A class used to handle colors used in the application"""

    def __init__(self, parent):
        pass
        # super().__init__(parent=parent) # Removed to get a Nitka Compile

    def rand_colours(self, num_cols: int):
        """Generates a list of random colour names pulled from TEXT_COLORS. It avoids light coloured colours and
        dupes if possible.

        Args:
            num_cols (int): The number of different colours required

        Returns:
            list[str]: List of colours
        """
        colour_max = len(TEXT_COLORS) - 1

        assert (
            isinstance(num_cols, int) and 0 <= num_cols <= colour_max
        ), f"{num_cols=}. Must be int >= 0 and <= {colour_max}"

        colour_list = []

        index = 0
        loop_count = 0

        # Try and fill out list with no dupes and no undesired colours
        while index < colour_max and loop_count < colour_max:
            loop_count += 1
            colour_index = random.randint(0, colour_max)

            if TEXT_COLORS[colour_index] not in colour_list and bool(
                "gray" not in TEXT_COLORS[colour_index].lower()
                or "grey" not in TEXT_COLORS[colour_index].lower()
                or "light" not in TEXT_COLORS[colour_index].lower()
                or "white" not in TEXT_COLORS[colour_index].lower()
                or "snow" not in TEXT_COLORS[colour_index].lower()
            ):
                colour_list.append(TEXT_COLORS[colour_index])
            else:
                continue

            index += 1

        # Just to make sure we have entered all required elements in the colour list - but might have dupes or
        # undesirable colours.
        if len(colour_list) != num_cols:
            for index in range(len(colour_list), num_cols):
                colour_index = random.randint(0, colour_max)
                colour_list.append(TEXT_COLORS[colour_index])

        return colour_list

    @property
    def legal_colour_string(self) -> str:
        """
        This function returns a string of all the legal colours that can be used in the `colour` parameter of the
        `print_colour` function

        Returns:
            str: A string of all the legal colours.
        """

        legal_colours = "<"

        for colour in TEXT_COLORS:
            legal_colours += "'" + colour + "'|"

        legal_colours += ">"

        return legal_colours

    def color_string_get(self, color: Union[str, tuple, list]) -> str:
        """This function returns a colour string  that can be used in the `colour` arguments/parameters


        Args:
            color (Union[str, tuple, list]): The color to be processed.
        """

        match color:
            case str():
                return self._process_colour_string(color)
            case tuple() | list():
                assert (
                    len(color) == 3
                ), "only rgb(99,99,99), 3 numeric arguments supported"

                text = "rgb("

                for arg_count, arg in enumerate(color):
                    assert isinstance(arg, int), str(arg) + " : must be a number"
                    text += str(arg)

                    if arg_count < len(color) - 1:
                        text += ","
                text += ")"

                return self.color_string_get(text)
            case _:
                text = ""

                assert text != "", str(color) + " Not A Valid Color Format"
        return text

    def _process_colour_args(
        self, color_function_string: str, args: list, hsvcheck: bool
    ):
        """
        This function checks that the arguments passed to the color functions are valid

        Args:
            color_function_string (str): The string that is passed to the color function.
            args (list): a list of the arguments passed to the function
            hsvcheck (bool): True if the function is hsv, False if it's rgb
        """
        color_dict = {0: "red", 1: "blue", 2: "Green"}
        arg_count = 0
        percent_count = 0

        for arg_count, arg in enumerate(args):
            if arg_count == 3:
                assert "%" in arg, color_function_string + " :4th arg must be %"

            if "%" in arg:
                percent_count += 1

                assert all(char in string.digits for char in arg[: len(arg) - 1]), (
                    arg + " : is not a valid percentage"
                )

                assert (
                    isinstance(int(arg[: len(arg) - 1]), int)
                    and 0 <= int(arg[: len(arg) - 1]) <= 100
                ), (arg + " must be between 0% and 100%")
            else:
                assert all(char in string.digits for char in arg), (
                    arg + " : is not a number"
                )

                if hsvcheck and arg_count == 0:
                    assert isinstance(int(arg), int) and 0 <= int(arg) <= 359, (
                        color_function_string + " : h value must be between 0 and 359"
                    )
                else:
                    assert isinstance(int(arg), int) and 0 <= int(arg) <= 255, (
                        color_function_string
                        + color_dict[arg_count]
                        + " must be between 0 and 255"
                    )

        if arg_count == 2 and percent_count > 0:
            # rgb function check, one % arg means all must be % args
            assert (percent_count - 1) == arg_count, (
                color_function_string + " : all arguments must be percent"
            )

    def _process_colour_functions(self, color_function_string: str) -> str:
        """
        Parses a CSS-style color function string and validates its format.

        Args:
            color_function_string (str): The color function string to process.

        Returns:
            str: The name of the color function if valid, otherwise an empty string.

        """

        args = []
        hcheck = False

        if "rgb(" in color_function_string:
            args = color_function_string[4 : len(color_function_string) - 1].split(",")

            assert len(args) == 3, (
                color_function_string + " : rgb function must have 3 arguments"
            )
        elif "rgba(" in color_function_string:
            args = color_function_string[5 : len(color_function_string) - 1].split(",")

            assert len(args) == 4, (
                color_function_string + " : rgba function must have 4 arguments"
            )
        elif "hsv(" in color_function_string:
            hcheck = True
            args = color_function_string[4 : len(color_function_string) - 1].split(",")

            assert len(args) == 3, (
                color_function_string + " : hsv function must have 3 arguments"
            )
        elif "hsva(" in color_function_string:
            hcheck = True
            args = color_function_string[5 : len(color_function_string) - 1].split(",")

            assert len(args) == 4, (
                color_function_string + " : hsva function must have 4 arguments"
            )
        else:
            color_function_string = ""

        assert color_function_string != "", (
            color_function_string
            + " : Only functions rgb ,rgba, hsv, hsva are supported and"
            " color_function_string names: "
            + self.legal_colour_string
        )

        self._process_colour_args(color_function_string, args, hcheck)

        return color_function_string

    def _process_colour_string(self, colour: str) -> str:
        """
        Takes a string, checks if it's a legal colour name, if not, checks if it's a hex number, if not, it checks if
        it's a function and if so, returns a colour str.

        Args:
            colour (str): The colour to be processed.

        Returns:
            str: The colour text after processing.
        """

        colour_text = "".join(colour.split())  # take out white spaces

        if self.color_text_legal(colour_text):
            return colour_text.lower()
        elif colour_text[0:1] == "#":  # Hex Number
            hex_number = colour_text[1:]

            assert len(hex_number) == 6, (
                colour_text + " : must be a hex number in this format #999999"
            )

            assert all(char in string.hexdigits for char in hex_number), (
                colour_text + " colour tag does not contain valid hex"
            )

            return colour_text
        else:
            return self._process_colour_functions(colour_text)

    def color_text_legal(self, text: str) -> bool:
        """
        Checks if the colour word is legal CSS

        Args:
            text (str): The text to be displayed

        Returns:
            bool: A boolean value
        """
        for colour in TEXT_COLORS:
            if colour.lower() == text.lower():
                return True
        return False


@define(slots=True)
class Widget_Frame(_qtpyBase):
    """Widget_Frame` is a class that defines the style of the frame around a widget"""

    frame_style: Frame_Style = Frame_Style.WPANEL
    frame: Frame = Frame.SUNKEN
    line_width: int = 3
    midline_width: int = 0

    def __post_init__(self):
        """
        Checks that the values of the attributes `frame_style`, `frame`, `line_width`, and `midline_width` are of the
        correct type and that the values of `line_width` and `midline_width` are greater than or equal to zero
        """
        assert isinstance(
            self.frame_style, Frame_Style
        ), f"frame_style <{self.frame_style}> must be of type FRAMESTYLE"
        assert isinstance(
            self.frame, Frame
        ), f"frame <{self.frame}> must be of type FRAME"

        assert (
            isinstance(self.line_width, int) and self.line_width >= 0
        ), f"line_width <{self.line_width}> must be int >= 0"

        assert (
            isinstance(self.midline_width, int) and self.midline_width >= 0
        ), f"line_width <{self.midline_width}> must be int >= 0"


class Validator(_qtpyBase, qtG.QValidator):
    """Validator class that calls a function when the user enters text into text edit widgets"""

    def __init__(
        self,
        validate_callback: Union[
            types.FunctionType, types.MethodType, types.LambdaType
        ],
        parent: qtW.QWidget,
    ):
        assert callable(
            validate_callback
        ), f"{validate_callback=}. Must be a function | method | lambda"

        assert isinstance(
            parent, qtW.QWidget
        ), f"{parent=}. Must be an instance of a QWidget"

        _qtpyBase.__init__(self, parent)
        qtG.QValidator.__init__(self, parent)

        self._validate_action: Union[None, Callable] = validate_callback

        self.parent_set(parent)

    def validate(self, s: str, pos: int) -> qtG.QValidator.State:
        """
        The function returns  a QValidator.Acceptable or QValidator.Invalid value depending on whether the string is valid

        Args:
            s (str): The string to validate
            pos (int): The position in the string where the validation is to be performed.

        Returns:
            qtG.QValidator.State: The return value is a QValidator.Acceptable or QValidator.Invalid.
        """
        assert isinstance(s, str), f"{s=}. Must be a string"
        assert isinstance(pos, int), f"{pos=}. Must be an int"

        test_ok: bool = self._validate_action(s, pos)

        assert isinstance(test_ok, bool), (
            "validate_callback function/method must return a boolean true when valid"
            " and a false if not valid"
        )

        if test_ok:
            return qtG.QValidator.Acceptable
        else:
            return qtG.QValidator.Invalid

    def fixup(self, fixup_string: str):
        """
        Virtual method to implement fixing the string in descendants.

        Args:
            fixup_string (str): The string to be fixed up.
        """
        pass


# @dataclasses.dataclass
@define(slots=True)
class Font(_qtpyBase):
    """Font` is a class that defines the font attributes of `Text` objects"""

    font_name: str = ""
    size: int = DEFAULT_FONT_SIZE
    weight: Font_Weight = Font_Weight.NORMAL
    style: Font_Style = Font_Style.NORMAL
    backcolor: str = ""
    forecolor: str = ""
    selectback: str = ""
    selectfore: str = ""

    def __post_init__(self):
        """
        Checks that the values of the attributes `are of the correct type
        """
        assert isinstance(self.font_name, str), f"{self.font_name=}. Must be a str"
        assert (
            isinstance(self.size, int) and self.size > 0
        ), f"{self.size=}. Must be int > 0"

        assert isinstance(
            self.weight, Font_Weight
        ), f"{self.weight=}. Is not a valid FONTWEIGHT"  # and self.weight in FONTWEIGHT

        assert isinstance(
            self.style, Font_Style
        ), f"{self.style=}. Is not a valid FONTSTYLE"
        assert isinstance(self.backcolor, str), f"{self.backcolor=}. Must be str"
        assert isinstance(self.forecolor, str), f"{self.forecolor=}. Must be str"
        assert isinstance(self.selectback, str), f"{self.selectback=}. Must be str"
        assert isinstance(self.selectfore, str), f"{self.selectfore=}. Must be str"


# Private Classes
class _qtpyBaseFrame(qtW.QMainWindow):  # , _qtpyBase): # QT 6.5.0 change
    """The _qtyBaseFrame class is a base class for SDI aND MDI frames # TODO: Add MDI support"""

    def __init__(self):
        super().__init__()

    @property
    def parent_get(self):  # QT 6.5.0 change
        return g_application


# TODO MDI frame
class _qtpyFrame(_qtpyBaseFrame):
    """A class that creates an ancestral frame that can be used to create a GUI with either an SDI or MDI frame."""

    parent_app: "QtPyApp"
    title: str = ""
    callback: Optional[Callable] = None
    tag: str = ""
    max_height: int = 1080
    max_width: int = 1920
    maximized: bool = False

    def __init__(
        self,
        parent_app: "QtPyApp",
        title: str = "",
        callback: Optional[Callable] = None,
        tag: str = "",
        max_height: int = 1080,
        max_width: int = 1920,
        maximized: bool = False,
    ):
        """
        A constructor for the class that performs suitable argument checks.

        Args:
            parent_app (QtPyApp): The parent app that this frame is a part of.
            title (str): str = ""
            callback (Optional[Callable]): This method is called when some event is propagated to the frame.
            tag (str): str = ""
            max_height (int): int = 1080,. Defaults to 1080
            max_width (int): int = 1920,. Defaults to 1920
            maximized (bool): bool = False. Defaults to False
        """
        self.parent_app = parent_app
        self.title = title
        self.callback = callback
        self.tag = tag
        self.max_height = max_height
        self.max_width = max_width
        self.maximized = maximized

        super().__init__()

        assert isinstance(
            self.parent_app, QtPyApp
        ), f"{self.parent_app=}. Must be an instance of QtPyApp"

        _qtpyBase.__init__(self, parent=self.parent_app)

        assert (
            isinstance(self.title, str) and self.title.strip() != ""
        ), f"{self.title=}. Must be a non-empty str"

        assert isinstance(self.callback, Callable) or self.callback is None, (
            f"{self.callback=}. Must be None | types.FunctionType, types.LambdaType,"
            " types.MethodType"
        )

        assert isinstance(self.tag, str), f"{self.tag=}. Must be str"

        assert isinstance(self.max_height, int), f"{self.max_height=}. Must be int"
        assert isinstance(self.max_width, int), f"{self.max_width=}. Must be int"
        assert isinstance(self.maximized, bool), f"{self.maximized=}. Must be bool"

        self.parent_app.available_width = self.screen().availableSize().width()
        self.parent_app.available_height = self.screen().availableSize().height()

        # Force frame to fit on available screen
        if self.screen().availableSize().width() <= self.max_width:
            self.max_width = self.screen().availableSize().width()

        if self.screen().availableSize().height() <= self.max_height:
            self.max_height = self.screen().availableSize().height()

        if self.maximized:
            self.showMaximized()

        # TODO Needs modifying for resizing
        self.setMaximumHeight(self.max_height)
        self.setMaximumWidth(self.max_width)
        self.setMinimumHeight(self.max_height)
        self.setMinimumWidth(self.max_width)
        self.resize(self.max_width, self.max_height)

    def closeEvent(self, event: QCloseEvent):
        """
        The function is called when the sheet is closed. Overrides the closeEvent method of QWidget.
        - If the window has a callback method, then the callback function is called.
        - If the callback method returns 1, then the window is closed.
        - If the callback method returns 0, then the window is not closed.
        - If the window does not have a callback method, then the window is closed.
        Args:
            event (QCloseEvent): The event that was trigger of the closeEvent.
        """
        if self.callback is not None:
            qtpyevent: Sys_Events = Sys_Events.APPCLOSED

            assert (
                self.callback.__code__.co_argcount <= 2
            ), "action events have 1 argument - action"

            window_id = Get_Window_ID(self.parent_app, None, self)

            result = _Event_Handler(parent_app=self.parent_app).event(
                window_id=window_id,
                callback=self.callback,
                container_tag="",
                tag=self.tag,
                event=qtpyevent,
                action=self.callback.__name__,
                value=None,
                widget_dict=self.parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.title
                ),
                parent=self.parent_get,
                control_name=self.__class__.__name__,
            )

            if result == 1:  # Allow window to close
                event.accept()
            else:
                event.ignore()

        else:
            event.accept()

    def open_sheet(
        self,
        main_frame: "_qtpyFrame",
        sheet_layout: "_qtpyBase_Control",
        callback: list[types.FunctionType | types.MethodType | types.LambdaType] = None,
    ):
        """Called when a sheet is opened and creates a widget from the sheet layout.

        Args: main_frame ("_qtpyFrame"): The main frame that the sheet will be attached to.
        sheet_layout (_qtpyBase_Control): _Container callback types.FunctionType | types.MethodType | types.LambdaType:
            This is a method that is called when the sheet is opened.
        """
        assert isinstance(
            main_frame, _qtpyFrame
        ), f"{main_frame=}>. Must be an instance of _qtpyBaseFrame"

        assert isinstance(sheet_layout, _Container), (
            f"{sheet_layout=}. Must be an instance of VBoxContainer,"
            " HBoxContainer,GridContainer"
        )

        assert callback is None or callable(
            callback
        ), f"{callback=} is a <function|method|labda> called when a sheet opens"

        widget = sheet_layout._create_widget(
            parent_app=self.parent_app,
            parent=self,
            container_tag=str(uuid.uuid1()) if self.tag.strip() == "" else self.tag,
        )


class _qtpySDI_Frame(_qtpyFrame):
    """A subclass of the _qtpyFrame class. It is used to create a single document interface (SDI) window."""

    def __init__(
        self,
        parent_app: "QtPyApp",
        title: str = "",
        callback: Optional[Callable] = None,
        tag: str = "",
        max_height: int = 1000,
        max_width: int = 1920,
        maximized: bool = False,
    ):
        """Constructor for the class. It performs a correctness checks on the input parameters and sets innstance
        variables as needed.
        Args:
            parent_app (QtPyApp): The parent application.
            title (str): The title of the window.
            callback (Optional[Callable]): This is the method that will be called when an event is passed to the frame.
            tag (str): tag name of the SDI window.
            max_height (int): int = 1000,. Defaults to 1000
            max_width (int): int = 1920,. Defaults to 1920
            maximized (bool): bool = False,. Defaults to False
        """
        assert isinstance(
            parent_app, QtPyApp
        ), f"{parent_app=}. Must be an instance of QtPyApp"
        assert isinstance(title, str), f"{title=}. Must be str"
        assert callback is None or isinstance(
            callback, Callable
        ), f"{callback=}. Must be None|func|method|lambda"
        assert isinstance(tag, str), f"{tag=}. Must be str"
        assert (
            isinstance(max_height, int) and max_height > 0
        ), f"{max_height=}. Must be int > 0"
        assert (
            isinstance(max_width, int) and max_width > 0
        ), f"{max_height=}. Must be int > 0"
        assert isinstance(maximized, bool), f"{maximized=}. Must be bool"

        super().__init__(
            parent_app=parent_app,
            title=title,
            callback=callback,
            tag=tag,
            max_height=max_height,
            max_width=max_width,
            maximized=maximized,
        )

        parent_app.main_frame_window_id = self.window().winId()

        self.setWindowTitle(self.title)

        self.parent_app.widget_add(
            window_id=parent_app.main_frame_window_id,
            container_tag=title,
            tag=tag,
            widget=self,
        )


class _Event_Filter(qtC.QObject):
    """This class is a Qt event filter that emits signals when certain events occur."""

    focusIn: qtC.Signal = qtC.Signal(qtC.QEvent)
    focusOut: qtC.Signal = qtC.Signal(qtC.QEvent)
    mousePressed: qtC.Signal = qtC.Signal(qtC.QEvent)
    popupSignal: qtC.Signal = qtC.Signal(qtC.QEvent)
    returnPressed: qtC.Signal = qtC.Signal(qtC.QEvent)

    def __init__(
        self,
        parent_app: "QtPyApp",
        owner_widget: "_qtpyBase_Control",
        container_tag: str,
    ):
        qtC.QObject.__init__(self)
        self._parent_app = parent_app
        self._owner_widget = owner_widget
        self._container_tag = container_tag

    def eventFilter(self, obj: qtC.QObject, event: qtC.QEvent) -> bool:
        """
        The function emits signals when certain events occur.

        Args:
            obj (qtC.QObject): The object that the event is being sent to.
            event (qtC.QEvent): The event that occurred.

        Returns:
            bool: The return value is a boolean that indicates whether the event was handled (true) or not (false).
        """
        try:
            match event.type():
                case qtC.QEvent.FocusIn:
                    self.focusIn.emit(event)  # type: ignore
                    return False
                case qtC.QEvent.FocusOut:
                    self.focusOut.emit(event)  # type: ignore
                    return False
                case qtC.QEvent.MouseButtonPress:
                    if isinstance(obj, _Image):
                        obj.clicked.emit()
                        return True
                case qtC.QEvent.Show:
                    # if self.calendarWidget() is obj:
                    self.popupSignal.emit(event)  # type: ignore
                    return True
                case qtC.QEvent.Type.KeyPress:
                    if not isinstance(obj, _Grid_TableWidget):
                        # print(f"{obj=} {event.key()= } {type(obj)=} {isinstance(obj,LineEdit)=} ")
                        # TODO - Matbe tab should be processed separately?
                        if (
                            event.key() == qtC.Qt.Key_Return
                            or event.key() == qtC.Qt.Key_Down
                        ):
                            obj.focusNextChild()
                            return True
        except Exception as e:
            raise AssertionError(f"Event Filter Failed {e=}")
        return False


@dataclasses.dataclass(slots=True)
# Using slots for better performance. But had to remove some inheritance to do so
class _Widget_Registry:
    """Widget Registry Class: Stores a reference to all Qtpy GUI widgets"""

    # ===== Helper Class
    @dataclasses.dataclass(slots=True)
    class _widget_entry:
        # `_widget_entry` is a class that stores the widget details.
        container_tag: str
        tag: str
        widget: _qtpyBase | _qtpySDI_Frame  # QT 6.5.0

    # ===== Main
    _widget_dict: dict = field(default_factory=dict)

    def __init__(self):
        """Sets up the _Widget_Registry class instance"""
        self._widget_dict = {}

    def widget_add(
        self, window_id: int, container_tag: str, tag: str, widget: _qtpyBase
    ):
        """Adds a widget to the container
        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): Tag name of container
            tag (str): Tag name of Tag
            widget (_qtpyBase_Control): Parent widget that the new widget will be assigned to
        """
        assert (
            isinstance(window_id, int) and window_id > 0
        ), f"{window_id=}. Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"
        assert isinstance(
            widget, (_qtpyBase, _qtpySDI_Frame)  # QT 6.5.0
        ), f"{widget=}. Must be an instance of _qtpyBase"

        container_tag = f"{window_id}_{container_tag}"

        if container_tag in self._widget_dict:
            if tag in self._widget_dict[container_tag]:
                self.widget_del(
                    window_id=window_id, container_tag=container_tag, tag=tag
                )

        if container_tag not in self._widget_dict:
            self._widget_dict[container_tag] = {}

        self._widget_dict[container_tag].update(
            {
                tag: self._widget_entry(
                    container_tag=container_tag, tag=tag, widget=widget
                )
            }
        )

    def widget_del(
        self, window_id: int, container_tag: str, tag: str, level: int = 0
    ) -> None:
        """Deletes a widget from the widget stack. If it is the last widget in the container then the container is
        deleted
        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The container tag name
            tag (str): The widget tag name
            level (int): Used for debug, no need for user to set
        Returns:
        """

        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}.Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        container_tag = f"{window_id}_{container_tag}"

        # Dev Note DAW 2022/12/02: This code is very sensitive to changes..tried half-way to sunday to improve,  but
        # even the smallest change eventually leads to problems (C++ object not found, segv etc.)
        if container_tag in self._widget_dict:
            for item in reversed(tuple(self._widget_dict[container_tag].values())):
                if f"{window_id}_{item.tag}" == container_tag:
                    continue

                if isinstance(item.widget, (_Container, Grid)):
                    # Down the rabbit hole and and blow it all away
                    self.widget_del(
                        window_id=window_id,
                        container_tag=item.tag,
                        tag="-",
                        level=level + 1,
                    )

                    if shiboken6.isValid(item.widget._widget):
                        item.widget._widget.deleteLater()

                    self._widget_dict[container_tag].pop(item.tag)

                elif tag == "-" or container_tag == tag:  # Delete every item
                    if shiboken6.isValid(item.widget._widget):
                        item.widget._widget.deleteLater()
                    self._widget_dict[container_tag].pop(item.tag)

                    continue
                elif tag == item.tag:  # Delete only this item
                    if shiboken6.isValid(item.widget._widget):
                        item.widget._widget.deleteLater()

                    self._widget_dict[container_tag].pop(item.tag)

                    return None

            if len(self._widget_dict[container_tag]) <= 1:
                self._widget_dict.pop(container_tag)

        return None

    def widget_gui_controls_get(
        self, window_id: int, container_tag: str
    ) -> list["_qtpyBase_Control"]:
        """Returns a list of all _qtpyBase_Control widgets in a given container.

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The tag name of the container to search.

        Returns:
            list[_qtpyBase_Control]: A list of _qtpyBase_Control widgets that match the container tag.

        Raises:
            AssertionError: If container_tag is not a non-empty string.
        """

        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}.Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str."

        container_tag = f"{window_id}_{container_tag}"

        if container_tag not in self._widget_dict:
            return []

        return [
            item.widget
            for item in self._widget_dict[container_tag].values()
            if isinstance(item.widget, _qtpyBase_Control)
        ]

    def widget_dict_get(
        self, window_id: int, container_tag: str
    ) -> dict[str, types.FunctionType | types.LambdaType | types.MethodType]:
        """Returns the dictionary associated with the provided container tag
        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str) : Tag of the container object
        Returns:
            Dict (Dict[str, Union[types.FunctionType, types.LambdaType, types.MethodType]]) : Dictionary of container object
        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}.Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}>. Must be a non-empty str"

        container_tag = f"{window_id}_{container_tag}"

        assert (
            container_tag in self._widget_dict
        ), (  # {self.print_dict()}"  # <{self._widget_dict}>"
            f"{container_tag=}> is not in widget_dict! "
        )

        return self._widget_dict[container_tag]

    def widget_exist(self, window_id: int, container_tag: str, tag: str) -> bool:
        """Determines if a widget exists in the container
        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The container tag of the container widget that you want to check if the widget exists in.
            tag (str): The tag of the widget to be added.
        Returns:
            A boolean value.
        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}.Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str"

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        container_tag = f"{window_id}_{container_tag}"

        if container_tag not in self._widget_dict:
            return False
        elif tag in self._widget_dict[container_tag]:
            return True
        else:
            found = any(  # Tag Check
                value.tag == tag
                and key != value.container_tag  # Same as container tag, Ignore
                for key, value in tuple(self._widget_dict[container_tag].items())
            ) or any(  # Container Check
                self.widget_exist(window_id=window_id, container_tag=key, tag=tag)
                for key, value in tuple(self._widget_dict[container_tag].items())
                if isinstance(value.widget, _Container)
            )

            if found:
                return True

        return False

    def widget_get(
        self, window_id: int, container_tag: str = "", tag: str = ""
    ) -> "_qtpyBase_Control":
        """Recursively searches through the widget_dict for the widget with the given tag and container_tag.
        If it doesn't find it, it raises an AssertionError. If it does find it, it returns the widget.

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The name of the container that the widget is in.
            tag (str): The tag name  of the widget you want to get.
        Returns:
            _qtpyBase_Control : The wanted widget .
        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}.Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        container_tag = f"{window_id}_{container_tag}"

        assert (
            container_tag in self._widget_dict
        ), f"{container_tag=} is not in widget_dict! {tag=} "

        if tag in self._widget_dict[container_tag]:
            return self._widget_dict[container_tag][tag].widget
        else:
            # First Search the container and it sub-containers for the tag
            for key, value in tuple(self._widget_dict[container_tag].items()):
                if key == value.container_tag:  # Same container, Ignore
                    continue

                if isinstance(value.widget, _Container):
                    return self.widget_get(
                        window_id=window_id, container_tag=key, tag=tag
                    )
                else:
                    if value.tag == tag:
                        return self._widget_dict[value.container_tag][value.tag]

            # If that fails, ferret through the widget_dict and see if we can find the tag
            for key in tuple(self._widget_dict.keys()):
                if key == container_tag:
                    continue

                if tag in self._widget_dict[key]:
                    return self._widget_dict[key][tag].widget

        raise AssertionError(
            f"{container_tag=} {tag=}. {tag=} Not Found In {container_tag=} or"
            " sub-containers "
        )

    def print_dict(
        self,
        _widget_items: dict | None = None,
        _delim: str = "*",
        file: str = "widget_dict_dump.txt",
    ) -> str:
        """Prints the contents of a dictionary, and if the value is a dictionary, it will recursively print the
        contents of that dictionary. Used for debugging.

        Args:
            _widget_items (dict | None): This is the dictionary that you want to print. If you don't pass one, it
                will print the entire widget dictionary.
            _delim (str): This is the delimiter that will be used to print the dictionary. Defaults to "*".
            file (str): The name of the file to write the output to. If None, it will only print to the console.

        Returns:
            str: The output string that was printed or written to a file.

        Raises:
            AssertionError: If the type of the _widget_items argument is not a dictionary or None, or if the type of the
                _delim argument is not a string.

        Examples:
            To print the entire widget dictionary to the console:
            >>> my_widget = MyWidget()
            >>> my_widget.print_dict()

            To print a specific dictionary to a file:
            >>> my_widget = MyWidget()
            >>> my_dict = {"key1": {"key2": "value1"}, "key3": "value2"}
            >>> my_widget.print_dict(_widget_items=my_dict, file="output.txt")
        """

        assert isinstance(
            _widget_items, (type(None), dict)
        ), f"{_widget_items=}. Must be a Dict or None"
        assert isinstance(_delim, str), f"{_delim=}. Must be a str"

        if _widget_items is None:
            _widget_items = self._widget_dict

        output = ""
        for key, value in _widget_items.items():
            if isinstance(value, dict):
                output += f"{_delim} {key} [\n"
                output += self.print_dict(
                    _widget_items=value, _delim=_delim + "*", file=None
                )
                output += f"{_delim} ]\n"
            else:
                if hasattr(value.widget, "_widget") and shiboken6.isValid(
                    value.widget._widget
                ):
                    output += f"{_delim} {key} : {value}\n"
                else:
                    output += f"{_delim} {key} She broken!\n"

        if file:
            with open(file, "w") as f:
                f.write(output)
        else:
            print(output)

        return output


@dataclasses.dataclass
class _qtpyBase_Control(_qtpyBase):
    """Base control of qypy gui controls"""

    text: str = ""
    action: str = ""
    tag: str = ""
    tooltip: str = ""
    callback: Optional[Callable] = None
    width: int = -1
    height: int = -1
    align: Align = Align.LEFT
    txt_align: Align = Align.LEFT
    txt_font: Optional[Font] = None
    txt_fontsize: int = DEFAULT_FONT_SIZE
    tune_vsize: int = 0  # In pixels, 0 is Arbitrary
    tune_hsize: int = 0  # In pixels, 0 is Arbitrary
    icon: Union[None, qtG.QIcon, qtG.QPixmap, str] = None
    translate: bool = True
    text_pad: int = 0
    frame: Optional[Widget_Frame] = None
    enabled: bool = True
    label: str = ""
    label_align: Align = Align.RIGHT
    editable: bool = True
    label_pad: int = -1
    label_font: Optional[Font] = None
    buddy_control: Optional["_qtpyBase_Control"] = None
    buddy_callback: Optional[Callable] = None
    validate_callback: Optional[Callable] = None
    container_tag: str = ""
    bold: bool = False
    italic: bool = False
    # available_width:int = g_application.available_width
    # available_height:int = g_application.available_height

    pixel_unit: bool = False
    user_data: any = None
    control_name: str = ""
    allow_clear: bool = True
    size_fixed: bool = True
    visible: bool = True

    _widget: Optional[qtW.QWidget] = None
    _event_filter: Optional[_Event_Filter] = None
    __doc__: str = ""
    # _focusIn = qtC.Signal()
    # _focusOut = qtC.Signal()

    def __post_init__(self):
        """
        Checks that the values of the attributes of the class are of the correct type and that they are valid
        """
        assert (
            isinstance(self.control_name, str) and self.control_name == ""
        ), f"{self.control_name=}. Can not be set by dev!"
        self.control_name: str = self.__class__.__name__

        assert isinstance(self.text, str), f"{self.text=} <{self.text}> must be str"
        assert isinstance(
            self.action, str
        ), f"{self.action=} <{self.action}> must be str"
        assert isinstance(self.tag, str), f"{self.tag=} <{self.tag}> must be str"
        assert isinstance(
            self.tooltip, str
        ), f"{self.tooltip=} <{self.tooltip}> must be a str"
        assert self.callback is None or callable(self.callback), (
            f"{self.callback=}. Must be a  None | types.FunctionType | types.MethodType"
            " | types.LambdaType "
        )
        assert (
            isinstance(self.width, int) and self.width > 0 or self.width == -1
        ), f"{self.width=}  <{self.width}> must be int > 0 or -1"
        assert (
            isinstance(self.height, int) and self.height > 0 or self.height == -1
        ), f"{self.height=}  <{self.height}> must be int > 0"

        assert isinstance(self.align, Align), f"{self.align=}. Must be of type ALIGN"

        assert isinstance(
            self.txt_align, Align
        ), f"{self.txt_align=}. Must be of type ALIGN"

        assert (
            isinstance(self.txt_font, Font) or self.txt_font is None
        ), f"{self.txt_font=} <{self.txt_font}> must be an instance of Font"

        assert (
            isinstance(self.txt_fontsize, int) and self.txt_fontsize > 0
        ), f"{self.txt_fontsize=} <{self.txt_fontsize}> must be an int"

        assert isinstance(
            self.tune_vsize, (float, int)
        ), f"{self.tune_vsize=} <{self.tune_vsize}> is an int or float"
        assert isinstance(
            self.tune_hsize, (float, int)
        ), f"{self.tune_hsize=} <{self.tune_hsize}> is an int or float"

        if self.tag.strip() == "":  # Try and default tag to text
            # & is shortcut on controls and MENU_SEPARATOR is not unique
            if (
                self.text.strip().replace("&", "") == ""
                or self.text.strip() == MENU_SEPERATOR
            ):
                self.tag = str(id(self))
            else:
                # remove  & and replace ' ' wth _.
                self.tag = self.text.strip().replace("&", "").replace(" ", "_").lower()
        self.tag = self.tag.strip(
            SDELIM
        )  # Translate delimiters should never be in a tag

        assert self.icon is None or isinstance(
            self.icon, (str, qtG.QPixmap, qtG.QIcon)
        ), f" {self.icon=}. Must be None | str (file name)| QPixmap | QIcon"

        assert isinstance(self.translate, bool), f"{self.translate=}. Must be bool"
        assert (
            isinstance(self.text_pad, int) and self.text_pad >= 0
        ), f"{self.text_pad=}. Must be an int >= 0"

        assert (
            isinstance(self.frame, Widget_Frame) or self.frame is None
        ), f"{self.frame=}. Must be Widget_Frame or None"
        assert isinstance(self.enabled, bool), f"{self.enabled=}. Must be bool"

        assert isinstance(self.label, str), f"{self.label=}. Must be str"
        assert isinstance(self.editable, bool), f"{self.editable=}. Must be bool"
        assert isinstance(
            self.label_align, Align
        ), f"{self.label_align=}. Must be of type ALIGN"
        assert isinstance(
            self.label_font, (type(None), Font)
        ), f"{self.label_font=}. Must be an instance of Font"

        assert isinstance(self.label_pad, int) and (
            self.label_pad == -1 or self.label_pad >= 0
        ), f"{self.label_pad=}. Must be an int > 0 or  -1"

        if (
            self.label.strip() != "" and self.label_pad == -1
        ):  # Change 29 3 2021 - add strip
            self.label_pad = amper_length(self.trans_str(self.label))

        assert isinstance(
            self.buddy_control, (type(None), _qtpyBase_Control)
        ), f"{self.buddy_control}. Must be an descendant of _qtpyBase_Control or None"
        assert self.buddy_callback is None or callable(self.buddy_callback), (
            f"{self.buddy_callback=}. Must be None | types.FunctionType |"
            " types.MethodType | types.LambdaType "
        )

        assert self.validate_callback is None or callable(self.validate_callback), (
            f"{self.validate_callback=}. Must be None | types.FunctionType |"
            " types.MethodType | types.LambdaType "
        )

        if callable(self.validate_callback):
            assert (
                self.validate_callback.__code__.co_argcount <= 3
            ), "validate_callback must have 3 arguments - container_tag, tag, value"

        assert isinstance(self.pixel_unit, bool), f"{self.pixel_unit=}. Must be bool"

        assert isinstance(self.allow_clear, bool), f"{self.allow_clear=}. Must be bool"
        assert isinstance(self.size_fixed, bool), f"{self.size_fixed=}. Must be bool"
        assert isinstance(self.visible, bool), f"{self.visible}. Must be bool"

        if self.container_tag == "":
            self.container_tag = f"{id(self)}"

        assert isinstance(self.bold, bool), f"{self.bold=}. Must be bool"
        assert isinstance(self.italic, bool), f"{self.italic=}. Must be bool"

        # print(f"@@A {self.available_width=}")
        # print(f"@@@ {self.available_height=}")

        if self.label_font is None:
            self.label_font = self.txt_font

        self.text = self.trans_str(self.text)

        # self._trans_txt = self.trans_str(self.text)
        # self._text = self.text.rjust(self.text_pad)

        # TODO Make an Option
        # if not isinstance(self,(Menu,Menu_Element)) and self.width == -1 and self.text.strip() != "":
        #    self.width = len(self.text.strip()) + 2
        # print(f"B####{self.tag=} {self.text=} {self.width} {type(self)=}")

    def _event_handler(
        self,
        *args,
    ) -> int:
        """Handles events generated by the low level GUI object created in _create_widget

        Args:
            *args (SYSEVENTS): Arguments passed to the event handler. First arg is always SYSVENTS

        Returns (int): 1 OK, -1 Issue

        """
        event: Sys_Events = args[0]
        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        # Check if widget exists as it sometimes is destroyed before event is fired
        if callable(self.callback) and self.parent_app.widget_exist(
            window_id=window_id,
            container_tag=self.container_tag,
            tag=self.tag,
        ):
            if self.parent_app.widget_exist(
                window_id=window_id,
                container_tag=self.container_tag,
                tag=self.tag,
            ):
                result = _Event_Handler(parent_app=self.parent_app, parent=self).event(
                    window_id=window_id,
                    callback=self.callback,
                    action=event.name,
                    container_tag=self.container_tag,
                    tag=self.tag,
                    event=event,
                    value=self.value_get(),
                    widget_dict=self.parent_app.widget_dict_get(
                        window_id=window_id, container_tag=self.container_tag
                    ),
                    control_name=self.__class__.__name__,
                    parent=self,
                )

                if isinstance(result, int) and result == 1 or result == -1:
                    return result
                else:
                    raise AssertionError(
                        f"{result=}. Must be an int and have the value of 1 or -1"
                    )

        return 1

    @property
    def guiwidget_get(self) -> qtW.QWidget:
        """Returns the QT gui widget
            If the widget is not created yet, raise an error

        Returns:
            qtW.QWidget : The QT GUI widget.
        """
        if self._widget is None:
            raise RuntimeError(
                f"{self.container_tag=} {self.tag=} {self._widget=}. Widget not created"
                " yet!"
            )

        return self._widget

    def guiwidget_set(self, widget: qtW.QWidget | qtG.QAction):
        """Sets the QT GUI widget

        Args:
            widget (qtW.QWidget | qtG.QAction): The QT GUI widget.
        """
        assert isinstance(
            widget, (qtG.QAction, qtW.QWidget)
        ), f"{widget=}. Must be type qtW.QAction | QWidget"

        self._widget = widget

    def _install_event_handlers(self):
        """Attaches events to the low level GUI object created in _Create_Widger"""
        if callable(self.callback) and hasattr(self._widget, "connect"):
            # try:
            if hasattr(self._widget, "clicked") and hasattr(
                self._widget.clicked, "connect"
            ):
                self._widget.clicked.connect(
                    lambda *args: self._event_handler(Sys_Events.CLICKED, args)
                )
            if hasattr(self._widget, "cellActivated") and hasattr(
                self._widget.cellActivated, "connect"
            ):
                self._widget.cellActivated.connect(
                    lambda *args: self._event_handler(Sys_Events.ACTIVATED, args)
                )
            if hasattr(self._widget, "cellChanged") and hasattr(
                self._widget.cellChanged, "connect"
            ):
                self._widget.cellChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CHANGED, args)
                )
            if hasattr(self._widget, "cellClicked") and hasattr(
                self._widget.cellClicked, "connect"
            ):
                self._widget.cellClicked.connect(
                    lambda *args: self._event_handler(Sys_Events.CLICKED, args)
                )
            if hasattr(self._widget, "cellDoubleClicked") and hasattr(
                self._widget.cellDoubleClicked, "connect"
            ):
                self._widget.cellDoubleClicked.connect(
                    lambda *args: self._event_handler(Sys_Events.DOUBLECLICKED, args)
                )
            if hasattr(self._widget, "cellEntered") and hasattr(
                self._widget.cellEntered, "connect"
            ):
                self._widget.cellEntered.connect(
                    lambda *args: self._event_handler(Sys_Events.ENTERED, args)
                )
            if hasattr(self._widget, "cellPressed") and hasattr(
                self._widget.cellPressed, "connect"
            ):
                self._widget.cellPressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )
            if hasattr(self._widget, "typeBufferCleared") and hasattr(
                self._widget.typeBufferCleared, "connect"
            ):
                self._widget.typeBufferCleared.connect(
                    lambda *args: self._event_handler(
                        Sys_Events.CLEAR_TYPING_BUFFER, args
                    )
                )
            if hasattr(self._widget, "currentItemChanged") and hasattr(
                self._widget.currentItemChanged, "connect"
            ):
                self._widget.typeBufferCleared.connect(
                    lambda *args: self._event_handler(Sys_Events.TEXTCHANGED, args)
                )
            if hasattr(self._widget, "collapsed") and hasattr(
                self._widget.collapsed, "connect"
            ):
                self._widget.collapsed.connect(
                    lambda *args: self._event_handler(Sys_Events.COLLAPSED, args)
                )
            if hasattr(self._widget, "currentCellChanged") and hasattr(
                self._widget.currentCellChanged, "connect"
            ):
                self._widget.currentCellChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CHANGED, args)
                )
            if hasattr(self._widget, "currentChanged") and hasattr(
                self._widget.currentChanged, "connect"
            ):
                self._widget.currentChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CHANGED, args)
                )
            if hasattr(self._widget, "currentIndexChanged") and hasattr(
                self._widget.currentIndexChanged, "connect"
            ):
                self._widget.currentIndexChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.INDEXCHANGED, args)
                )
            if hasattr(self._widget, "currentTextChanged") and hasattr(
                self._widget.currentTextChanged, "connect"
            ):
                self._widget.currentTextChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.TEXTCHANGED, args)
                )
            if hasattr(self._widget, "cursorPositionChanged") and hasattr(
                self._widget.cursorPositionChanged, "connect"
            ):
                self._widget.cursorPositionChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CURSORCHANGED, args)
                )
            if hasattr(self._widget, "dateChanged") and hasattr(
                self._widget.dateChanged, "connect"
            ):
                self._widget.dateChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.DATECHANGED, args)
                )
            if hasattr(self._widget, "editTextChanged") and hasattr(
                self._widget.editTextChanged, "connect"
            ):
                self._widget.editTextChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.EDITCHANGED, args)
                )
            if hasattr(self._widget, "editingFinished") and hasattr(
                self._widget.editingFinished, "connect"
            ):
                self._widget.editingFinished.connect(
                    lambda *args: self._event_handler(Sys_Events.EDITCHANGED, args)
                )
            if hasattr(self._widget, "expanded") and hasattr(
                self._widget.expanded, "connect"
            ):
                self._widget.expanded.connect(
                    lambda *args: self._event_handler(Sys_Events.EXPANDED, args)
                )
            if hasattr(self._event_filter, "focusIn") and hasattr(
                self._event_filter.focusIn, "connect"
            ):
                self._event_filter.focusIn.connect(
                    lambda *args: (self.focusInEvent(args))
                )

            if hasattr(self._event_filter, "focusOut") and hasattr(
                self._event_filter.focusOut, "connect"
            ):
                self._event_filter.focusOut.connect(
                    lambda *args: (self.focusOutEvent(args))
                )

            if hasattr(self._widget, "highlighted") and hasattr(
                self._widget.highlighted, "connect"
            ):
                self._widget.highlighted.connect(
                    lambda *args: self._event_handler(Sys_Events.HIGHLIGHTED, args)
                )
            if hasattr(self._widget, "inputRejected"):
                if hasattr(self._widget.inputRejected, "connect"):
                    self._widget.inputRejected.connect(
                        lambda *args: self._event_handler(Sys_Events.BADINPUT, args)
                    )
            if hasattr(self._widget, "itemActivated") and hasattr(
                self._widget.itemActivated, "connect"
            ):
                self._widget.itemActivated.connect(
                    lambda *args: self._event_handler(Sys_Events.ACTIVATED, args)
                )
            if hasattr(self._widget, "itemCollapsed") and hasattr(
                self._widget.itemCollapsed, "connect"
            ):
                self._widget.itemCollapsed.connect(
                    lambda *args: self._event_handler(Sys_Events.COLLAPSED, args)
                )
            if hasattr(self._widget, "itemChanged") and hasattr(
                self._widget.itemChanged, "connect"
            ):
                self._widget.itemChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CHANGED, args)
                )
            if hasattr(self._widget, "itemClicked") and hasattr(
                self._widget.itemClicked, "connect"
            ):
                self._widget.itemClicked.connect(
                    lambda *args: self._event_handler(Sys_Events.CLICKED, args)
                )
            if hasattr(self._widget, "itemDoubleClicked") and hasattr(
                self._widget.itemDoubleClicked, "connect"
            ):
                self._widget.itemDoubleClicked.connect(
                    lambda *args: self._event_handler(Sys_Events.DOUBLECLICKED, args)
                )
            if hasattr(self._widget, "itemEntered") and hasattr(
                self._widget.itemEntered, "connect"
            ):
                self._widget.itemEntered.connect(
                    lambda *args: self._event_handler(Sys_Events.ENTERED, args)
                )
            if hasattr(self._widget, "itemExpanded") and hasattr(
                self._widget.itemExpanded, "connect"
            ):
                self._widget.itemExpanded.connect(
                    lambda *args: self._event_handler(Sys_Events.EXPANDED, args)
                )
            if hasattr(self._widget, "itemPressed") and hasattr(
                self._widget.itemPressed, "connect"
            ):
                self._widget.itemPressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )
            if hasattr(self._widget, "itemSelectionChanged") and hasattr(
                self._widget.itemSelectionChanged, "connect"
            ):
                self._widget.itemSelectionChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.SELECTIONCHANGED, args)
                )
            if hasattr(self._event_filter, "mousePressed") and hasattr(
                self._event_filter.mousePressed, "connect"
            ):
                self._event_filter.mousePressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )

            # if hasattr(self._widget, "popupSignal"):
            # if (
            #     hasattr(self._event_filter, "popupSignal")
            #     and self.popup_callback is not None
            # ):
            #     print(f"AB?????? {self.popup_callback=}")
            #     # self._event_filter.popupSignal.connect(lambda: self.popup_callback)
            #     # self._event_filter.popupSignal.connect(lambda *args: self._event_handler(SYSEVENTS.PRESSED, args))
            if hasattr(self._widget, "pressed") and hasattr(
                self._widget.pressed, "connect"
            ):
                self._widget.pressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )
            if hasattr(self._widget, "released") and hasattr(
                self._widget.released, "connect"
            ):
                self._widget.released.connect(
                    lambda *args: self._event_handler(Sys_Events.RELEASED, args)
                )
            if hasattr(self._widget, "returnPressed") and hasattr(
                self._widget.returnPressed, "connect"
            ):
                self._widget.returnPressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )
            if hasattr(self._event_filter, "returnPressed") and hasattr(
                self._event_filter.mousePressed, "connect"
            ):
                self._event_filter.returnPressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )
            if hasattr(self._widget, "selectionChanged") and hasattr(
                self._widget.selectionChanged, "connect"
            ):
                self._widget.selectionChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.SELECTIONCHANGED, args)
                )
            if hasattr(self._widget, "stateChanged") and hasattr(
                self._widget.stateChanged, "connect"
            ):
                self._widget.stateChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CHANGED, args)
                )
            if hasattr(self._widget, "tabBarClicked") and hasattr(
                self._widget.tabBarClicked, "connect"
            ):
                self._widget.tabBarClicked.connect(
                    lambda *args: self._event_handler(Sys_Events.CLICKED, args)
                )
            if hasattr(self._widget, "tabBarDoubleClicked") and hasattr(
                self._widget.tabBarDoubleClicked, "connect"
            ):
                self._widget.tabBarDoubleClicked.connect(
                    lambda *args: self._event_handler(Sys_Events.DOUBLECLICKED, args)
                )
            if hasattr(self._widget, "tabCloseRequested") and hasattr(
                self._widget.tabCloseRequested, "connect"
            ):
                self._widget.tabCloseRequested.connect(
                    lambda *args: self._event_handler(Sys_Events.CLOSED, args)
                )
            if hasattr(self._widget, "textChanged") and hasattr(
                self._widget.textChanged, "connect"
            ):
                self._widget.textChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.TEXTCHANGED, args)
                )
            if hasattr(self._widget, "textEdited") and hasattr(
                self._widget.textEdited, "connect"
            ):
                self._widget.textEdited.connect(
                    lambda *args: self._event_handler(Sys_Events.TEXTEDIT, args)
                )
            if hasattr(self._widget, "timeChanged") and hasattr(
                self._widget.timeChanged, "connect"
            ):
                self._widget.toggled.connect(
                    lambda *args: self._event_handler(Sys_Events.TIMECHANGED, args)
                )
            if hasattr(self._widget, "toggled") and hasattr(
                self._widget.toggled, "connect"
            ):
                self._widget.toggled.connect(
                    lambda *args: self._event_handler(Sys_Events.TOGGLED, args)
                )

            if hasattr(self._widget, "actionTriggered") and hasattr(
                self._widget.actionTriggered, "connect"
            ):
                self._widget.actionTriggered.connect(
                    lambda *args: self._event_handler(Sys_Events.TRIGGERED, args)
                )

            if hasattr(self._widget, "sliderMoved") and hasattr(
                self._widget.sliderMoved, "connect"
            ):
                self._widget.sliderMoved.connect(
                    lambda *args: self._event_handler(Sys_Events.MOVED, args)
                )
            if hasattr(self._widget, "rangeChanged") and hasattr(
                self._widget.rangeChanged, "connect"
            ):
                self._widget.rangeChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.CHANGED, args)
                )
            if hasattr(self._widget, "sliderPressed") and hasattr(
                self._widget.sliderPressed, "connect"
            ):
                self._widget.sliderPressed.connect(
                    lambda *args: self._event_handler(Sys_Events.PRESSED, args)
                )
            if hasattr(self._widget, "sliderReleased") and hasattr(
                self._widget.sliderReleased, "connect"
            ):
                self._widget.sliderReleased.connect(
                    lambda *args: self._event_handler(Sys_Events.RELEASED, args)
                )
            if hasattr(self._widget, "valueChanged") and hasattr(
                self._widget.valueChanged, "connect"
            ):
                self._widget.valueChanged.connect(
                    lambda *args: self._event_handler(Sys_Events.EDITCHANGED, args)
                )

            # keyPressevent #TODO implement event if needed

            if hasattr(self._widget, "itemExpanded") and hasattr(
                self._widget.itemExpanded, "connect"
            ):
                self._widget.itemExpanded.connect(
                    lambda *args: self._event_handler(Sys_Events.EXPANDED, args)
                )
        # if isinstance(self, Dateedit):
        #     pass
        #     # action = Action(self._container_tag,tag=self._owner_widget.tag,event=event,action="",value=None.)
        #
        #     # self._fevent_filter.popupSignal.connect(
        #     #    lambda *args: self._event_handler(SYSEVENTS.POPCAL, args)
        #     # )
        #
        # if callable(self.popup_callback):
        #     # if hasattr(self._widget, "popupSignal"):
        #     if (
        #         hasattr(self._event_filter, "popupSignal")
        #         # hasattr(self._widget, "popupSignal")
        #         and self.popup_callback is not None
        #     ):
        #         print(f"BB?????? {self.popup_callback=}")
        #         # self._event_filter.popupSignal.connect(lambda: self.popup_callback)
        #         # self._widget.popupSignal.connect(lambda: self.popup_callback)
        # except Exception as e:
        #    raise AssertionError(
        #        f" ====> {e=} {self._widget=}:{self._widget.dumpObjectInfo()}"
        #    )

    def _create_widget(
        self, parent_app: "QtPyApp", parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates and configures the low level GUI widget based on the qtgui GUI object definition

        Args:
            parent_app (QtPyApp): Parent application owning widget
            parent (qtW.QWidget): Parent widget hosting the owning created widget
            container_tag (str):  Parent container that owns the widget

        Returns (qtw.QWidget): This will be either a low level gui widget or frame

        """
        assert isinstance(
            parent_app, QtPyApp
        ), f"{parent_app=}. Must be an instance of QtPyApp"
        assert isinstance(
            parent, qtW.QWidget
        ), f"{parent=}. Must be an instance of QWidget"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str"

        window_id = Get_Window_ID(parent_app, parent, self)

        parent_app.widget_add(
            window_id=window_id, container_tag=container_tag, tag=self.tag, widget=self
        )

        self.parent_app = parent_app
        self.parent = parent
        self.container_tag = container_tag

        edit_frame: Optional[qtW.QFrame] = None
        buddy_widget: Optional[qtW.QWidget] = None
        label_widget: Optional[qtW.QLabel] = None

        label_height = 0

        match self:
            case Button():
                self._widget = qtW.QPushButton(self.text, parent)
                self._widget.setStyleSheet(Align_SS_Text[self.txt_align])
            case Checkbox():
                self._widget = qtW.QCheckBox(self.text, parent)
            case ComboBox():
                self._widget = qtW.QComboBox(parent)
                self._widget.setStyleSheet(
                    "QComboBox QAbstractItemView  { border: 2px solid darkgray;}"
                    " QComboBox { combobox-popup: 0; } "
                )
            case Dateedit():
                # self._widget = qtW.QDateEdit(parent)
                self._widget = _Custom_Dateedit(parent)
            case Grid():
                self._widget = _Grid_TableWidget(parent)  # qtW.QTableWidget(parent)
            case FolderView():
                self._widget = qtW.QTreeView(parent)
            case Image():
                self._widget = _Image(parent)
            case Label():
                self._widget = qtW.QLabel(self.text.replace("\00", ""), parent)
            case LCD():
                self._widget = qtW.QLCDNumber(parent)
                self._widget.setStyleSheet(Align_SS_Text[self.txt_align])
            case LineEdit():
                self._widget = _Line_Edit(
                    parent, self
                )  # qtW.QLineEdit(parent) #_Line_Edit(parent_app, parent, self, container_tag)
            case RadioButton():
                self._widget = qtW.QRadioButton(self.text, parent)
            case Spacer():
                self._widget = qtW.QLabel(self.text, parent)
            case Slider():
                self._widget = qtW.QSlider(parent)
            case Spinbox():
                self._widget = qtW.QSpinBox(parent)
            case Switch():
                self._widget = _Switch(parent)
            case Tab():
                self._widget: qtW.QTabWidget = qtW.QTabWidget(parent)
                self._widget.setUsesScrollButtons(True)
            case TextEdit():
                self._widget = qtW.QTextEdit(self.text.strip("*"), parent)
            case Timeedit():
                self._widget = qtW.QTimeEdit(parent=parent)
            case Treeview():
                self._widget = qtW.QTreeWidget(parent)

        if self._widget is None:
            raise RuntimeError(
                f"{self.container_tag=} {self.tag=} {self._widget=} . Failed to create"
                " widget!"
            )

        if not shiboken6.isValid(self._widget):
            raise RuntimeError(
                f"{self.container_tag=}-{self.tag=}. Create widget failed!"
            )

        self._widget.setObjectName(self.tag)

        self._event_filter = _Event_Filter(
            parent_app=parent_app, owner_widget=self, container_tag=container_tag
        )

        if self._widget is not None:  # Should not happen, caught above
            self._widget.installEventFilter(self._event_filter)

            widget_font = (
                parent_app.app_font_def if self.txt_font is None else self.txt_font
            )
            widget_font.size = self.txt_fontsize

            if self.bold:
                widget_font.weight = Font_Weight.BOLD

            if self.italic:
                widget_font.style = Font_Style.ITALIC

            self.font_set(app_font=parent_app.app_font_def, widget_font=widget_font)

        char_pixel_size = self.pixel_char_size(1, 1)

        if self.label != "&" and (
            amper_length(self.label.strip()) > 0 or self.label_pad > 0
        ):
            label = Label(
                text=self.label,  # self.label.strip() if self.label_pad == 0 else self.label,
                tag="l_" + self.tag,
                txt_font=self.label_font,
                txt_align=self.label_align,
                text_pad=self.label_pad,
                width=-1 if self.label_pad == 0 else self.label_pad,
            )
            label_widget = label._create_widget(
                parent_app=parent_app, parent=parent, container_tag=container_tag
            )

            if label_widget is None:
                raise AssertionError(
                    f"{label_widget=}. Creation Failed. Programmer Goof"
                )

            label_widget.setBuddy(self._widget)

            label_height = label_widget.height()

        if self.buddy_control is not None or label_widget is not None:
            if self.buddy_control is not None:
                if self.buddy_control.callback is not None:
                    self.buddy_control.callback = self.buddy_control.callback
                else:
                    self.buddy_control.callback = self.buddy_callback

                buddy_widget = self.buddy_control._create_widget(
                    parent_app=parent_app, parent=parent, container_tag=container_tag
                )
                if isinstance(buddy_widget, qtW.QFrame):
                    pass
                # buddy_widget.setFrameShape(qtW.QFrame.Shape.Box)  # Debug

            edit_group = qtW.QHBoxLayout()
            edit_group.setContentsMargins(0, 0, 0, 0)

            if label_widget is not None:
                edit_group.addWidget(label_widget)
            edit_group.addWidget(self._widget)

            if buddy_widget is not None:
                edit_group.addWidget(buddy_widget)

            edit_group.setAlignment(self.align.value)

            edit_frame = qtW.QFrame(parent)
            edit_frame.setLayout(edit_group)
            edit_frame.setContentsMargins(0, 0, 0, 0)

        if self.frame is not None:
            self.frame_style_set(self.frame)

        if self.tooltip.strip() != "":
            self.tooltip_set(self.tooltip)

        if hasattr(self._widget, "enabled"):
            self.enable_set(self.enabled)

        # print(f"DEBUG {self=}")
        pixel_size = self.pixel_char_size(self.height, self.width)

        if self.icon is not None:
            self.icon_set(self.icon)

        # TODO Resizing Stuff If Needed
        # self._widget.setMinimumHeight(pixel_size.height + self.tune_vsize)
        # self._widget.setMinimumWidth(pixel_size.width + self.tune_hsize)
        # self._widget.setMaximumHeight(pixel_size.height + self.tune_vsize)
        # self._widget.setMaximumWidth(pixel_size.width + self.tune_hsize)

        if label_height > pixel_size.height:
            height = label_height + self.tune_vsize
        else:
            height = pixel_size.height

        self._install_event_handlers()

        if self.pixel_unit:
            if self.size_fixed:
                self._widget.setFixedSize(
                    self.width + self.tune_hsize, self.height + self.tune_vsize
                )
            else:
                self._widget.setMinimumSize(
                    self.width + self.tune_hsize, self.height + self.tune_vsize
                )
        else:
            if self.size_fixed:
                self._widget.setFixedSize(
                    (self.width + 1) * (char_pixel_size.width - 1),
                    height + self.tune_vsize,
                )
            else:
                self._widget.setMinimumSize(
                    (self.width + 1) * (char_pixel_size.width - 1),
                    height + self.tune_vsize,
                )

        self.visible_set(self.visible)
        self.ediitable_set(self.editable)

        if buddy_widget is not None:
            if isinstance(buddy_widget, _Image):
                if buddy_widget.height > self._widget.height():
                    self.height = buddy_widget.height
            else:
                self.height = buddy_widget.height() // char_pixel_size.height

        if edit_frame is not None:
            # edit_frame.setFrameShape(qtW.QFrame.Shape.Box)  # Debug
            return edit_frame
        else:
            # print(f"DBG {qtW.QStyleFactory.keys()=}")
            # self._widget.setStyle(qtW.QStyleFactory.create("Windows"))  # Debug
            return self._widget

    def buddy_text_set(self, value: str) -> None:
        """Set the buddy text for the widget.

        Args:
            value (str): The text to set on the buddy widget.
        """

        def _label_set(widget: _qtpyBase_Control, value: str) -> None:
            """Set the label text on the buddy widget.

            Args:
                widget (_qtpyBase_Control): The buddy widget to set the label on.
                value (str): The value to set the label to.
            """
            if isinstance(widget, Label):
                widget.value_set(value)
            elif hasattr(widget, "widget_gui_controls_get"):
                for child_widget in widget.widget_gui_controls_get():
                    _label_set(child_widget, value)

        if self.buddy_control is not None:
            _label_set(self.buddy_control, value)

    def ediitable_set(self, editable: bool = False) -> None:
        """Set the editable state of the widget.

        Args:
            editable (bool): bool = False. Defaults to False
        """

        assert isinstance(editable, bool), f"{editable=}. Must be bool"
        if self._widget is None:
            raise AssertionError(f"{self._widget=}. Not set, Programmer goof")

        if hasattr(self._widget, "setReadOnly"):
            self._widget.setReadOnly(not editable)  # Think about it, lol!

            edit_palette = self.parent_app.app_get.palette()
            non_edit_palette = self.parent_app.app_get.palette()

            if editable:
                self._widget.setPalette(edit_palette)
            else:
                non_edit_back = edit_palette.color(qtG.QPalette.Window)
                non_edit_text = edit_palette.color(qtG.QPalette.WindowText)

                non_edit_palette.setColor(qtG.QPalette.Base, non_edit_back)
                non_edit_palette.setColor(qtG.QPalette.Text, non_edit_text)
                self._widget.setPalette(non_edit_palette)

    def clear(self):
        """Clears the value displayed in the wisget"""
        if self.allow_clear and hasattr(self._widget, "clear"):
            self._widget.clear()

    def focusInEvent(self, gui_event) -> None:
        """Focus in event of the widget.

        If the widget is a FolderView or ComboBox, then call this event handler with the selectedIndexes or
        currentIndex as the argument

        Args:
            gui_event: The event that was triggered.
        """
        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        for control in self.parent_app.widget_dict_get(
            window_id=window_id, container_tag=self.container_tag
        ).values():
            if (
                hasattr(control.widget, "guiwidget_get")
                and hasattr(control.widget.guiwidget_get, "IsDefault")
                and hasattr(control.widget.guiwidget_get, "clearFocus")
            ):
                if control.widget.guiwidget_get.isDefault():
                    if self.tag != control.widget.tag:
                        control.widget.guiwidget_get.clearFocus()

        if isinstance(self, FolderView):  # Bit poxy, have to watch this
            result = self._event_handler(
                Sys_Events.FOCUSIN, self.guiwidget_get.selectedIndexes()
            )
        elif isinstance(self, ComboBox):  # Bit poxy, have to watch this
            result = self._event_handler(
                Sys_Events.FOCUSIN, self.guiwidget_get.currentIndex()
            )
        else:
            result = self._event_handler(Sys_Events.FOCUSIN)

        if result == -1:
            gui_event[0].ignore()
        else:
            if hasattr(self._widget, "focusInEvent"):
                if shiboken6.isValid(self.guiwidget_get):
                    super(type(self.guiwidget_get), self.guiwidget_get).focusInEvent(
                        gui_event[0] if isinstance(gui_event, tuple) else gui_event
                    )

    def focusOutEvent(self, gui_event: "Action") -> None:
        """Focus out event of the widget.

        If the widget is a FolderView or ComboBox, then call the event handler with the selectedIndexes or currentIndex as
        the argument

        Args:
            gui_event (Action): The event that was triggered.
        """
        if isinstance(self, FolderView):  # Bit poxy, have to watch this
            result = self._event_handler(
                Sys_Events.FOCUSOUT, self.guiwidget_get.selectedIndexes()
            )
        elif isinstance(self, ComboBox):  # Bit poxy, have to watch this
            result = self._event_handler(
                Sys_Events.FOCUSOUT, self._widget.currentIndex()
            )
        else:
            result = self._event_handler(Sys_Events.FOCUSOUT)

        if result == -1:
            gui_event[0].ignore()
        else:
            if hasattr(self.guiwidget_get, "focusOutEvent"):
                if shiboken6.isValid(self.guiwidget_get):
                    super(type(self.guiwidget_get), self.guiwidget_get).focusOutEvent(
                        gui_event[0] if isinstance(gui_event, tuple) else gui_event
                    )

    @property
    def enable_get(self) -> bool:
        """Get the enable state of the widget.


        Returns:
            bool: The enable value of the widget.
        """
        if self.guiwidget_get is not None and hasattr(self.guiwidget_get, "isEnabled"):
            return self.guiwidget_get.isEnabled()

        return False

    def enable_set(self, enable: bool) -> int:
        """Set the enable state of the widget.

        Args:
            enable (bool): bool

        Returns:
            int: 1 - set ok, -1 - set failed
        """
        assert isinstance(enable, bool), f"{enable=}. Must be bool"

        if self.guiwidget_get is not None and hasattr(self.guiwidget_get, "setEnabled"):
            self.guiwidget_get.setEnabled(enable)
            return 1

        return -1

    def pixel_str_size(self, text: str) -> Char_Pixel_Size:
        """
        Returns the pixel size of a string.

        Args:
            text (str): str

        Returns:
            CHAR_PIXEL_SIZE : The pixel size of the string in  CHAR_PIXEL_SIZE instance   .
        """
        assert isinstance(text, str), f"{text=}. Must be str"

        # if text.strip() == "":
        #    return CHAR_PIXEL_SIZE(height=0, width=0)

        if self.guiwidget_get is not None:
            font = self.guiwidget_get.font()
        else:
            font = self.parent_app.app_font

        assert isinstance(font, qtG.QFont), f"{font=}. Must be a QFont instance"

        if font is None:
            font = self.parent_app.app_font
            font_metrics = qtG.QFontMetrics(font)
        else:
            font_metrics = qtG.QFontMetrics(font)

        width = font_metrics.boundingRect(text).width()
        height = font_metrics.boundingRect(text).height()

        return Char_Pixel_Size(height=int(height), width=int(width))

    def pixel_char_size(
        self,
        char_height: int,
        char_width: int,
        height_fudge: float = 1.1,
        width_fudge: float = 1.1,
        parent_app: Optional["QtPyApp"] = None,
    ) -> Char_Pixel_Size:
        """Transforms character size (height,width) in pixel size (height, width).
        Fudge factors allow precise adjustment

        Args:
            char_height (int) : Character height in chars
            char_width (int) :  Character width in chars
            height_fudge (float) :  Fudge factor multiplier to provide height adjustment
            width_fudge (float) : Fudge factor multiplier to provide width adjustment

        Returns:
            Char_Pixel_Size: CHAR_PIXEL_SIZE instance

        """
        assert (
            isinstance(char_height, int) and char_height > 0
        ), f"Invalid char_height value: {char_height}. Must be an int > 0"
        assert (
            isinstance(char_width, int) and char_width > 0
        ), f"Invalid char_width value: {char_width}. Must be an int > 0"
        assert (
            isinstance(height_fudge, float) and height_fudge >= 1
        ), f"Invalid height_fudge value: {height_fudge}. Must be a float >= 1"
        assert (
            isinstance(width_fudge, float) and width_fudge >= 1
        ), f"Invalid width_fudge value: {width_fudge}. Must be a float >= 1"

        if self.guiwidget_get is None:
            raise AssertionError(f"guiwidget_get is not set: {self.guiwidget_get}")

        font = self.guiwidget_get.font()
        assert isinstance(
            font, qtG.QFont
        ), f"Invalid font type: {type(font)}. Must be a QFont instance."

        font_metrics = qtG.QFontMetrics(font)

        # Monspaced all the same width, proportional this might not be quite right
        width = math.ceil(
            font_metrics.horizontalAdvance("W" * char_width) * width_fudge
        )
        height = math.ceil(font_metrics.height() * char_height * height_fudge)

        return Char_Pixel_Size(height=height, width=width)

    def text_pixel_size(self, text: str) -> tuple[int, int]:
        """Returns the height and width of a string of text in pixels

        Args:
            text (str): The text to be measured.

        Returns:
            tuple[int, int] : The height and width of the text in pixels.
        """

        if self.guiwidget_get is None:
            raise AssertionError(f"{self.guiwidget_get=}. Not created!")

        font_metrics = qtG.QFontMetrics(self.guiwidget_get.font())
        bounding_rect = font_metrics.boundingRect(text)

        return bounding_rect.height(), bounding_rect.width()

    @property
    def fonts_available_get(self) -> tuple[str]:
        """Returns a tuple of all the fonts available on the system.

        Returns:
            tuple[str] : A tuple of faont name strings.
        """

        available_fonts = tuple(qtG.QFontDatabase().families())

        return available_fonts  # fonts

    def font_set(
        self, app_font: Font, widget_font: Font, widget: Optional[qtW.QWidget] = None
    ) -> None:
        """Set the font for the GUI control

        Args:
            app_font (Font): Application font
            widget_font (Font) : Control font

        Returns:
            None
        """

        # print(f"A==> {app_font=} {widget_font=}") #Debug
        assert isinstance(app_font, Font), f"{app_font=}. Must be an instance of Font "

        if widget_font is None:
            raise RuntimeError(f"{widget_font=}.Must be an instance of Font")

        assert isinstance(
            widget_font, (Font)
        ), f"{widget_font=}. Must be an instance of Font"

        if widget is None:
            widget_instance = self._widget
        else:
            widget_instance = widget

        if widget_instance is None:
            raise RuntimeError(
                f"{widget_instance=} || {self.tag=} can not be None and must be an"
                " instance of QWidget"
            )

        assert isinstance(
            widget_instance, qtW.QWidget
        ), f"{widget_instance=} || {self.tag=} must be an instance of QWidget"

        colour = Colors(self)

        if widget_font.font_name == "":
            widget_font.font_name = app_font.font_name

        if widget_font.size < 0:
            widget_font.size = app_font.size

        if widget_font.backcolor == "":
            widget_font.backcolor = app_font.backcolor

        if widget_font.backcolor != "":
            widget_font.backcolor = colour.color_string_get(widget_font.backcolor)

        if widget_font.forecolor == "":
            widget_font.forecolor = app_font.forecolor

        if widget_font.forecolor != "":
            widget_font.forecolor = colour.color_string_get(widget_font.forecolor)

        if widget_font.selectback == "":
            widget_font.selectback = app_font.selectback

        if widget_font.selectback != "":
            widget_font.selectback = colour.color_string_get(widget_font.selectback)

        if widget_font.selectfore == "":
            widget_font.selectfore = app_font.selectfore

        if widget_font.selectfore != "":
            widget_font.selectfore = colour.color_string_get(widget_font.selectfore)

        system_fonts = self.fonts_available_get

        if widget_font.font_name not in system_fonts:
            print(
                f"\\n{self.tag=}\nwidget_font <{widget_font=}>  is not available on"
                " this system.\n\n"
                + "".join("'" + fontname + "';" for fontname in system_fonts)
            )

            font_family = self.font_system_get().defaultFamily()
            widget_font.font_name = font_family

            print(f"substituting with system widget_font <{font_family}>")

        if hasattr(self._widget, "font"):
            local_widget = self._widget
            control_font = local_widget.font()  # qtG.QFont()
        else:
            control_font = qtG.QFont()

        control_font.setFamily(widget_font.font_name)
        control_font.setWeight(widget_font.weight.value)
        control_font.setPointSize(widget_font.size)

        if widget_font.style == Font_Style.NORMAL:
            pass
        elif widget_font.style == Font_Style.ITALIC:
            control_font.setItalic(True)
        elif widget_font.style == Font_Style.UNDERLINE:
            control_font.setUnderline(True)

        if hasattr(widget_instance, "setFont"):
            widget_instance.setFont(control_font)

        qml_text = ""

        if isinstance(self.guiwidget_get, _Menu_Entry):
            widget_instance = self._widget.parent()  # get_menu_parent(widget_instance)

            if widget_font.selectback != "" and widget_font.selectfore != "":
                qml_text = (
                    "QMenu::item:selected { background-color: "
                    + widget_font.selectback
                    + ";color:"
                    + widget_font.selectfore
                    + "}"
                )
            elif widget_font.selectback != "" and widget_font.selectfore == "":
                qml_text = (
                    "QMenu::item:selected { background-color: "
                    + widget_font.selectback
                    + "}"
                )

            elif widget_font.backcolor != "" and widget_font.forecolor != "":
                qml_text = (
                    "QMenu {background-color:"
                    + widget_font.backcolor
                    + ";color: "
                    + widget_font.forecolor
                    + " }"
                    + qml_text
                )
            elif widget_font.backcolor != "" and widget_font.forecolor == "":
                qml_text = (
                    "QMenu {background-color:" + widget_font.backcolor + "}" + qml_text
                )
            elif widget_font.backcolor == "" and widget_font.forecolor != "":
                qml_text = "QMenu {color:" + widget_font.forecolor + "}" + qml_text

            # Leave here in case can get stylesheets working for menu action items
            # self.guiwidget_get.defaultWidget().setStyleSheet("color: " + forecolor)
            # self.guiwidget_get.setStyleSheet("color: " + forecolor)
        else:
            if widget_font.backcolor != "" and widget_font.forecolor != "":
                qml_text = (
                    "background: "
                    + widget_font.backcolor
                    + ";color:"
                    + widget_font.forecolor
                )
            elif widget_font.backcolor != "" and widget_font.forecolor == "":
                qml_text = "background: " + widget_font.backcolor
            elif widget_font.backcolor == "" and widget_font.forecolor != "":
                qml_text = "color: " + widget_font.forecolor

        if qml_text != "":
            widget_instance.setStyleSheet(qml_text)

    def font_system_get(self, fixed: bool = True) -> qtG.QFont:
        """Returns the system font.

        Args:
            fixed (bool): bool = True. Defaults to True

        Returns:
            qtG.QFont : A QFont object.
        """
        if fixed:
            return qtG.QFontDatabase().systemFont(qtG.QFontDatabase.FixedFont)
        else:
            return qtG.QFontDatabase().systemFont(qtG.QFontDatabase.GeneralFont)

    def frame_style_set(self, frame: Widget_Frame) -> None:
        """Sets the frame style.

        Args:
            frame (Frame): Frame definition object.
        """

        if self._widget is None:
            raise RuntimeError(f"{self=}. Not created yet!")

        assert isinstance(
            frame, Widget_Frame
        ), f"{frame=}. Must ba an instance of Frame"

        if (
            self._widget is not None
            and shiboken6.isValid(self._widget)
            and hasattr(self._widget, "setFrameShape")
        ):  # Other attributes will be there as well
            self._widget.setFrameShape(frame.frame_style.value)
            self._widget.setFrameShadow(frame.frame.value)
            self._widget.setLineWidth(frame.line_width)
            self._widget.setMidLineWidth(frame.midline_width)

    def icon_set(self, icon: Optional[Union[str, qtG.QPixmap, qtG.QIcon]]) -> None:
        """Sets the icon.

        If the widget is a QMenu, set the icon using setIcon. If the icon is a QPixmap or QStyle.StandardPixmap,
        set the icon using setPixmap. Otherwise, set the icon using setIcon

        Args:
            icon (Optional[Union[str, qtG.QPixmap, qtG.QIcon]]): Icon definition object.
        """
        if self._widget is None:
            raise AssertionError(f"{self._widget=}. Not set. Programmer goof")

        assert isinstance(
            self.icon, (type(None), str, qtG.QPixmap, qtG.QIcon)
        ), f" {self.icon=}. Must be None | str (file name)| QPixmap | QIcon"

        if icon is not None:
            if isinstance(icon, str):
                assert qtC.QFile.exists(icon), icon + " : does not exist!"
            elif isinstance(icon, qtG.QPixmap):
                pass  # All Good
            elif isinstance(icon, qtG.QIcon):
                pass  # All Good
            else:
                raise AssertionError(f"{icon=}. Not a valid icon type")

            if isinstance(self._widget, qtW.QMenu):
                if hasattr(self._widget, "setIcon"):
                    self._widget.setIcon(qtG.QIcon(icon))
            else:
                if isinstance(icon, (qtG.QPixmap, qtW.QStyle.StandardPixmap)):
                    if hasattr(self._widget, "setPixmap"):
                        self._widget.setPixmap(icon)
                else:
                    if hasattr(self._widget, "setIcon"):
                        self._widget.setIcon(qtG.QIcon(icon))

    @property
    def tooltip_get(self) -> str:
        """Returns the widget's tooltip

        Returns:
            str: The tooltip text.
        """
        if self._widget is None:
            return ""
        else:
            return self._widget.toolTip()

    def tooltip_set(
        self,
        tooltip: str,
        width: int = 400,
        txt_color: str = "black",
        bg_color: str = "wheat",
        border: str = "1px solid #000000",
    ) -> None:
        """Sets the tooltip for a widget.

        Note: Width setting is still being ignored TODO Find Fix

        Args:
            tooltip (str): The text to display in the tooltip.
            width (int): The width of the tooltip in pixels. Defaults to 200 - currently 400 for testing.
            txt_color (str): The color of the tooltip text. Defaults to black.
            bg_color (str): The background color of the tooltip. Defaults to white.
            border (str): The border style of the tooltip. Defaults to "1px solid #000000".
        """
        assert (
            isinstance(tooltip, str) and tooltip.strip() != ""
        ), f"{tooltip=} must be a non-empty str"
        assert isinstance(width, int) and width > 0, f"{width=}. Must be int > 0"
        assert isinstance(txt_color, str), f"{txt_color=} must be a string"
        assert isinstance(bg_color, str), f"{bg_color=} must be a string"
        assert isinstance(border, str), f"{border=} must be a string"
        assert border in {"none", ""} or re.match(
            r"\d+px .+ .+", border
        ), f"{border=} must be a valid CSS border style"

        color_handler = Colors(self)

        assert color_handler.color_string_get(
            txt_color
        ), f" {txt_color=} Not an HTML color"
        assert color_handler.color_string_get(
            bg_color
        ), f" {bg_color} Not an HTML color"

        # Use HTML formatting to set the style of the tooltip, including its width, text color, background color, and border style
        trans_tip = (
            f'<div style="max-width: {width}px !important; color: {txt_color};'
            f" background-color: {bg_color}; border:"
            f' {border}">{self.trans_str(tooltip)}</div>'
        )

        # Set a stylesheet on the widget to customize the style of the tooltip
        self._widget.setStyleSheet("QToolTip { max-width: 800px; }")

        # Set the tooltip text
        self._widget.setToolTip(trans_tip)

        if isinstance(self, _Menu_Entry):
            self._widget.parent().setToolTipsVisible(True)

    @property
    def tooltipsvisible_get(self) -> bool:
        """Returns a boolean value indicating whether the tooltips are visible or not

        Returns:
            bool : True - visible, False - not visible.
        """
        if self._widget is None:
            raise AssertionError(f"{self._widget=}. Not set!")
        else:
            return self._widget.tooTipsVisible()

    def tooltipsvisible_set(self, visible: bool) -> None:
        """Sets the tooltips visibility of the widget

        Args:
            visible (bool): True - Visible, False - not visible.
        """
        assert isinstance(visible, bool), f"{visible=}. Must be bool"

        if self._widget is None:
            raise AssertionError(f"{self._widget=}. Not set!")

        self._widget.setToolTipsVisible(visible)

    @property
    def trans_get(self) -> bool:
        """Returns the value of the translate attribute of the object

        Returns:
            bool: True - translate, False - do not translate
        """
        return self.translate

    def trans_set(self, no_trans: bool) -> None:
        """Set translate state of the object

        Args:
            no_trans: True - no translation, False - translate
        """
        assert isinstance(no_trans, bool), f"{no_trans=}. Must be bool"

        self.translate = no_trans

    def trans_str(self, text: str, force_translate: bool = False) -> str:
        """Takes a string, and if the translate flag is set, it returns the translated string

        Args:
            text (str): The text to be translated.
            force_translate (bool): bool = False. Defaults to False

        Returns:
            str : The translated text.
        """
        assert isinstance(text, str), f"{text=}. Must be str"

        if self.translate or force_translate:
            return self._lang_tran.translate(text, SDELIM)
        else:
            return text

    def validate(self) -> bool:
        """Performs validation if validate_callback is set.

        Returns:
            bool : True if validation ok, otherwise False
        """
        if callable(self.validate_callback):
            validate_ok = self.validate_callback(
                self.container_tag, self.tag, self, self.value_get()
            )

            assert isinstance(
                validate_ok, bool
            ), f"{validate_ok=}. validate_callback must return bool!"

            return validate_ok

        return True

    def value_get(self) -> any:
        """If the widget has a value attribute, return the value containsd in the widget. Usually overridden by
        subclasses.

        Returns:
            any : The value of the widget.
        """
        if hasattr(self, "value"):
            return self._widget.value()
            # TODO Is there a a group value to return?
            # if isinstance(self, (Check_Group, Radio_Group, Menu)):

    def userdata_get(self) -> any:
        """Returns the user data. Maybe overridden by subclasses.

        Returns:
            The user_data
        """
        return self.user_data

    def userdata_set(self, user_data: any) -> None:
        """Sets the user data of the widget. Maybe overridden by subclasses.

        Args:
            user_data (any): any
        """
        self.user_data = user_data

    @overload
    def value_set(self, value: bool) -> None:
        ...

    @overload
    def value_set(self, value: float) -> None:
        ...

    @overload
    def value_set(self, value: Combo_Data):
        ...

    @overload
    def value_set(self, value: str):
        ...

    def value_set(self, value: datetime.date) -> None:
        ...

    @overload
    def value_set(self, value: datetime.datetime) -> None:
        ...

    @overload
    def value_set(self, value: Union[str, int, float]):
        ...

    # @overload
    # def value_set(self, hour: int = 0, min: int = 0, sec: int = 0, msec: int = 0):
    #     ...

    def value_set(self, value: str = None) -> None:
        """Sets the widget value If the widget has a value_set method

        Args:
            value (str): The value to set the widget value to.
        """
        if value is not None and isinstance(self, Menu):
            pass  # TODO Is there a a group value to set?
        else:
            if self._widget is None:
                raise AssertionError(f"{self._widget=}. Not set!")

            if hasattr(self._widget, "value_set"):
                self._widget.value_set(value)
            else:
                AssertionError(f"{self._widget=}. Has no method value_set")

    @property
    def visible_get(self) -> bool:
        """Returns the visibility of the widget.

        Returns:
            bool: True - widget visible, False - widget hidden.
        """
        if self._widget is None:
            raise AssertionError(f"{self._widget=}. Not set!")
        else:
            if hasattr(self._widget, "isVisible"):
                return self._widget.isVisible()
        return True

    def visible_set(self, visible: bool) -> None:
        """Sets the visibility of the widget.
        Args:
            visible (bool): True - widget visible, False - widget hidden.
        """
        assert isinstance(visible, bool), f"{visible=}. Must be bool"

        if self._widget is None:
            raise AssertionError(f"{self._widget=}. Not set!")

        if hasattr(self._widget, "setVisible"):
            # Belts 'n braces because this fixed an earlier bug else where
            if shiboken6.isValid(self._widget):
                self._widget.setVisible(visible)


# Public classes
class QtPyApp(_qtpyBase):
    """This class implements application level functionality for a qtgui application. Basically sets the application
    up and running
    """

    def __init__(
        self,
        display_name: str,
        callback: Optional[Callable] = None,
        icon: Union[str, qtG.QPixmap, qtG.QIcon] = None,
        mdi_app: bool = False,
        language: str = "English",
        trans_file: str = "trans/fr_FR",
        height: int = 1080,
        width: int = 1920,
        app_font: Font = Font(font_name="IBM Plex Mono", size=DEFAULT_FONT_SIZE),
    ) -> None:
        """
        Checks that the parameters are of the correct type and then sets some private instance variables.

        Args:
            display_name (str): The name of the application.
            callback (Optional[Callable]): A function that will be called when the application is closed.
            icon (Union[str, qtG.QPixmap, qtG.QIcon]): The icon to use for the application.
            mdi_app (bool): If True, the application will be a MDI (Multiple Document Interface) application. Defaults to
                False TODO: Implement MDI
            language (str): The language of the application. Defaults to English
            trans_file (str): str = "trans/fr_FR",. Defaults to trans/fr_FR
            height (int): int = 1080,. Defaults to 1080
            width (int): int = 1920,. Defaults to 1920
          app_font (Font): Font = Font(font_name="IBM Plex Mono", size=DEFAULT_FONT_SIZE),
        """

        # Stop Annoying QT Badwindow debug error messages - that are not supposed to be errors
        os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"

        self._app: qtW.QApplication = qtW.QApplication(sys.argv)

        super().__init__(self)

        global g_application
        g_application = self

        self.available_height: int = -1
        self.available_width: int = -1
        self.main_frame_window_id = -1

        self.frozen = Is_Complied()

        assert (
            isinstance(display_name, str) and display_name.strip() != ""
        ), f"{display_name=}. Must be a non-empty str"

        # TODO This check needs beefing up

        assert callback is None or callable(callback), (
            f"{callback=}. Must be a None | types.FunctionType | types.LambdaType |"
            " types.MethodType "
        )

        assert isinstance(
            icon, (type(None), str, qtG.QPixmap, qtG.QIcon)
        ), f"{icon=}. Must be None | str (file name) | QPixmap | QIcon"

        assert isinstance(mdi_app, bool), f"{mdi_app=}. Must be bool"
        assert isinstance(language, str), f"{language=}. Must be str"
        assert isinstance(trans_file, str), f"{trans_file=}. Must be str"
        assert isinstance(height, int) and height > 0, f"{height=}. Must be > 0"
        assert isinstance(width, int) and width > 0, f"{width=}. Must be > 0"
        assert isinstance(app_font, Font), f"{app_font=}. Must be Font"

        # TODO Add languge, file and icon check

        # Private instance variables
        self.callback: Optional[Callable] = callback
        self.display_name: str = display_name
        self.app_action: str = ""

        self._main_frame: Optional[_qtpySDI_Frame] = None
        self._mdi_app: bool = False
        self.app_font_def: Font = app_font
        self.app_font_size: int = 0
        self.icon = icon
        self.mdi_app = mdi_app
        self._parent = self
        self._widget_registry = _Widget_Registry()

        assert isinstance(mdi_app, bool), f"{mdi_app=}. Must be boolean"
        assert isinstance(app_font, Font), f"{app_font=}. Must be an instance of Font"

        self.font_set(self.app_font_def)

        self._app.setApplicationDisplayName(self.display_name)
        self._fire_appost_init = True  # Post App start event

        screen_dim = qtG.QScreen.availableGeometry(self._app.primaryScreen())
        self.available_width = screen_dim.width()
        self.available_height = screen_dim.height()

        if self.mdi_app:
            self._main_frame = _qtpyBaseFrame()  # TODO Place holder Need _qtpyMDI_Frame

        else:
            if 0 < self.available_height < height:
                height = self.available_height - 10

            if 0 < self.available_width < width:
                width = self.available_width - 10

            if not self.frozen:
                print(
                    "DBG Resolution"
                    f" {height=} {width=} {self.available_height=} {self.available_width=}"
                )

            self._main_frame = _qtpySDI_Frame(
                parent_app=self,
                title=self._app.applicationDisplayName(),
                callback=self.callback,
                tag="SDI_Frame",
                max_height=height,
                max_width=width,
            )

    def font_set(self, requested_font: Font):
        """Sets the application font.  If desired font not on system it attempts to load these fonts in this order:

        Segoe UI, DejaVu Sans Mono, Verdana, Bitstream Vera Sans, Geneva


        Args:
            requested_font (Font): System font definition

        Returns:
            None:
        """
        assert isinstance(
            requested_font, Font
        ), f"{requested_font=}. Must be an instance of FONT"

        # Load IBM-Plex-font
        if qtC.QFileInfo(
            App_Path("IBM-Plex-Mono")
        ).exists():  # Load for Plex Mono fonts if they exist
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-BoldItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Medium.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Bold.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Regular.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-ExtraLightItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-SemiBoldItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-ExtraLight.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-SemiBold.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Italic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-TextItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-LightItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Text.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Light.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-ThinItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-MediumItalic.ttf")
            )
            qtG.QFontDatabase.addApplicationFont(
                App_Path(f"IBM-Plex-Mono{os.path.sep}IBMPlexMono-Thin.ttf")
            )

        app_font = self._app.font()  # type: ignore  # Default System font in this case
        preferred_font = requested_font.font_name

        family_list = [family for family in qtG.QFontDatabase().families()]

        if requested_font.font_name in family_list:
            app_font = qtG.QFont(requested_font.font_name, requested_font.size)
            self._app.setFont(app_font)
        else:
            if "Segoe UI" in family_list:
                app_font = qtG.QFont("Segoe UI", requested_font.size)
            elif "Tahoma" in family_list:
                app_font = qtG.QFont("Tahoma", requested_font.size)
            elif "Geneva" in family_list:
                app_font = qtG.QFont("Geneva", requested_font.size)
            elif "Ubuntu" in family_list:
                app_font = qtG.QFont("Ubuntu", requested_font.size)
            elif "Ref Hat" in family_list:
                app_font = qtG.QFont("Red Hat", requested_font.size)
            elif "DejaVu Sans" in family_list:
                app_font = qtG.QFont("DejaVu Sans", requested_font.size)
            elif "Noto Sans" in family_list:
                app_font = qtG.QFont("Noto Sans", requested_font.size)
            elif "Liberation Sans" in family_list:
                app_font = qtG.QFont("Liberation Sans", requested_font.size)
            elif "Verdana" in family_list:
                app_font = qtG.QFont("Verdana", requested_font.size)
            elif "Bitstream Vera Sans" in family_list:
                app_font = qtG.QFont("Bitstream Vera Sans", requested_font.size)
            elif "San Francisco" in family_list:
                app_font = qtG.QFont("San Francisco", requested_font.size)
            elif "Helvetica Neue" in family_list:
                app_font = qtG.QFont("Helvetica Neue", requested_font.size)
            else:
                app_font = qtG.QFont(app_font.family(), requested_font.size)

            print(
                f"Substituting font <{app_font.family()}> as preferred font"
                f" <{preferred_font}> is not available on this system!"
            )

            # Note this changes font_name in the passed in instance
            requested_font.font_name = app_font.family()

            app_font.setStyleStrategy(
                qtG.QFont.PreferDefault
            )  # Pyside6 modForceIntegerMetrics)
            self._app.setFont(app_font)

    @property
    def app_get(self) -> qtW.QApplication:
        """Returns the QApplication object.

        Returns:
            qtW.QApplication: : The QApplication object.
        """
        return self._app

    def app_exit(self) -> None:
        """Called when the user clicks the "X" button on the top right of the window or selects exit from the menu.
        Could also be called in the application"""

        result = 1

        # check if the app has registered to receive system events
        if self.callback is not None:
            result = _Event_Handler(parent_app=self).event(
                window_id=self.main_frame_window_id,
                callback=self.callback,
                container_tag="",
                tag="",
                event=Sys_Events.APPEXIT,
                action=self.callback.__name__,
                value=None,
                widget_dict=self.widget_dict_get(
                    window_id=self.main_frame_window_id,
                    container_tag=self.app_get.applicationDisplayName(),
                ),
                parent=self._main_frame,  # self.parent_get,
                control_name=self.__class__.__name__,
            )

        if result == 1:  # Allow application to close
            if self._main_frame is not None:
                self._main_frame.close()

            self.app_get.quit()

    def app_title(self) -> str:
        """Returns the display name of the app

        Returns:
            str : The display name of the app.
        """
        return self.display_name

    def open_event(self) -> int:
        """Called when the app is opened. It fires the app's post init event

        Returns:
            int : The result of the open_event handler. 1 - Ok, -1 - Failed.
        """
        result = 1

        if self._fire_appost_init and callable(self.callback):
            self._fire_appost_init = False

            result = _Event_Handler(parent_app=self).event(
                window_id=self.main_frame_window_id,
                callback=self.callback,
                container_tag="",
                tag="",
                event=Sys_Events.APPPOSTINIT,  # type: ignore
                action=self.callback.__name__,
                value=None,
                widget_dict={},  # No widgets registered at this time
                parent=self.parent_get,
                control_name=self.__class__.__name__,
            )

            if result is None:
                result = 1

        return result

    @property
    def app_font(self) -> qtG.QFont:
        """Returns the font of the application.

        Returns:
            qtG.QFont : The font of the application.
        """
        return self.app_get.font()  # type: ignore

    def char_pixel_size(self, font_path: str = "") -> Char_Pixel_Size:
        """Returns the pixel size of a character in the current font

        Args:
            font_path (Optional[str]): Path to a font file to use instead of the current font.

        Returns:
            Char_Pixel_Size: Char_Pixel_Size instance with the height and width of the font.
        """
        assert isinstance(font_path, str), f"{font_path=}. Must be str"

        if font_path:
            if os.path.isfile(font_path):
                new_font = qtG.QFont(font_path)
            else:  # Dodgy font_path TODO Some kind of error handling
                new_font = self.app_font
        else:
            new_font = self.app_font

        font_metrics = qtG.QFontMetrics(new_font)

        rect = font_metrics.boundingRect("W")
        width = rect.width()

        height = font_metrics.height()

        return Char_Pixel_Size(height=height, width=width)

    def run(self, layout: "_Container", windows_ui: bool = False) -> NoReturn:
        """Creates a main window, sets the title & icon, and then shows the window

        Args:
            layout (_Container): The layout container widget.
            window_ui (bool): Attempt to display the UI as Windows XP looked
        """
        assert isinstance(
            layout, _Container
        ), f"{layout=}. Must be a VBoxContainer, HBoxContainer,GridContainer"

        assert isinstance(windows_ui, bool), f"{windows_ui=}. Must be bool"

        if windows_ui:
            self.app_get.setStyle(qtW.QStyleFactory.create("Windows"))

        if callable(self.callback):
            result = _Event_Handler(parent_app=self).event(
                window_id=self.main_frame_window_id,
                callback=self.callback,
                container_tag="",
                tag="",
                event=Sys_Events.APPINIT,  # type: ignore
                action=self.callback.__name__,
                value=None,
                widget_dict={},  # No widgets registered at this time
                parent=self.parent_get,
                control_name=self.__class__.__name__,
            )

            if result == -1:  # Reject application start
                sys.exit()
                # self.app_get.exit()  # type: ignore

        if self._main_frame is None:
            raise AssertionError(f"{self._main_frame=}. Not set")

        if self.mdi_app:
            # TODO MDI Frame needs to have default windows menu option and option_sheet call
            pass

        else:
            self._main_frame.open_sheet(
                self._main_frame,
                sheet_layout=layout,
            )
        if self._main_frame is None:
            raise AssertionError(
                f"{self._main_frame=}. Failed To Create - Programmer Goof"
            )

        self._main_frame.setWindowTitle(self.display_name)

        if (
            isinstance(self.icon, str)
            and self.icon.strip() != ""
            and pathlib.Path(App_Path(self.icon)).exists()
        ):  # Try and load from file
            icon_image = qtG.QPixmap(App_Path(self.icon)).scaledToWidth(256)  # type: ignore

            assert isinstance(
                icon_image, (qtG.QIcon, qtG.QPixmap)
            ), f"{self.icon=} did not resolve to a QIcon or a QPixmap"

            self._main_frame.setWindowIcon(icon_image)
        elif self.icon is None or (
            isinstance(self.icon, str) and self.icon.strip() == ""
        ):
            pass
        elif isinstance(self.icon, (qtG.QIcon, qtG.QPixmap)):
            self._main_frame.setWindowIcon(self.icon)
        else:
            raise AssertionError(
                f"{self.icon=} || <{type(self.icon)}> is not a file str or a QPixmap"
            )

        self._main_frame.show()

        # Lets Ctl-C work
        qtC.QTimer.singleShot(0, self.open_event)

        sys.exit(self._app.exec())

    def widget_add(
        self, window_id: int, container_tag: str, tag: str, widget: _qtpyBase
    ) -> None:
        """Adds a widget to the widget registry

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): This is the container tag name of the container widget that you want to add the widget to.
            tag (str): This is the name of the widget.
            widget (_qtpyBase): the widget to add to the container
        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}. Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be str"
        assert isinstance(tag, str) and tag.strip() != "", f"{tag=}. Must be str"
        assert isinstance(
            widget, (_qtpyBase, _qtpySDI_Frame)  # QT 6.5.0
        ), f"{widget=}. Must be an instance of _qtpyBase"
        # if not isinstance(widget, _qtpyBase): #QT 6.5.0
        #    print(f"DBG {widget=} {type(widget)=}")

        self._widget_registry.widget_add(
            window_id=window_id, container_tag=container_tag, tag=tag, widget=widget
        )

    def widget_gui_controls_get(
        self, window_id: int, container_tag: str
    ) -> list[_qtpyBase_Control]:
        """Returns a list of all the controls in the container with the given tag

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The tag name of the container widget.

        Returns:
            A list of _qtpyBase_Control objects.
        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}. Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be str"

        return self._widget_registry.widget_gui_controls_get(
            window_id=window_id, container_tag=container_tag
        )

    def widget_del(self, window_id: int, container_tag: str, tag: str) -> None:
        """Deletes a widget from the registry

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The tag name of the container widget.
            tag (str): The tag name of the widget to be deleted.
        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}. Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be str"
        assert isinstance(tag, str) and tag.strip() != "", f"{tag=}. Must be str"

        self._widget_registry.widget_del(
            window_id=window_id, container_tag=container_tag, tag=tag
        )

    def widget_dict_get(
        self, window_id: int, container_tag: str
    ) -> dict[str, types.FunctionType | types.MethodType | types.LambdaType]:
        """Returns a dictionary of all the widgets in the container with the given tag

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): Tag name of the container holding the widgets of interest

        Returns: dict[str, types.FunctionType | types.MethodType | types.LambdaType]: Dictionary of all the widgets
        in the container with the given tag  name

        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}. Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be str"

        return self._widget_registry.widget_dict_get(
            window_id=window_id, container_tag=container_tag
        )

    def widget_dict_print(self):
        """Prints the contents of the widget registry to console. Used for debugging"""
        return self._widget_registry.print_dict()

    def widget_exist(self, window_id: int, container_tag: str, tag: str) -> bool:
        """Returns True if a widget with the given container_tag and tag name exists

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The tag name of the container widget that the widget is in.
            tag (str): The tag name of the widget you want to check.

        Returns:
            bool : True if the widget exists, False otherwise.

        """
        assert (
            isinstance(window_id, int) and window_id >= 0
        ), f"{window_id=}. Must be int > 0"
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be str"
        assert isinstance(tag, str) and tag.strip() != "", f"{tag=}. Must be str"

        return self._widget_registry.widget_exist(
            window_id=window_id, container_tag=container_tag, tag=tag
        )

    def widget_get(
        self, window_id: int, container_tag: str, tag: str
    ) -> _qtpyBase_Control:
        """Returns a widget from the widget registry

        Args:
            window_id (int): The WinId (Window Id) of the window housing the widget
            container_tag (str): The tag name of the container widget.
            tag (str): The tag name of the widget you want to get.

        Returns:
            _qtpyBase_Control: The widget you are looking for.
        """

        if self._widget_registry.widget_exist(
            window_id=window_id, container_tag=container_tag, tag=tag
        ):
            return self._widget_registry.widget_get(
                window_id=window_id, container_tag=container_tag, tag=tag
            )
        else:
            print(f" DBG :-( {window_id=} {container_tag=} {tag=}")
            return None


@dataclasses.dataclass
class Action(_qtpyBase):
    """A subclass of the _qtpyBase_Control class. It is used to implement event handling"""

    window_id: int
    parent_app: QtPyApp
    container_tag: str
    tag: str
    event: IntEnum
    action: str
    value: any
    object: Optional[_qtpyBase]
    widget_dict: dict[
        str, Union[types.FunctionType, types.LambdaType, types.MethodType]
    ]
    parent_widget: _qtpyBase_Control
    control_name: str = ""

    def __post_init__(self) -> None:
        """Checks the types of the arguments passed to the class and sets instance variable as needed."""
        assert (
            isinstance(self.window_id, int) and self.window_id > 0
        ), f"{self.window_id=}. Must be int > 0"
        assert isinstance(
            self.parent_app, QtPyApp
        ), f"{self.parent_app=}. Must ba an instance of QtPyApp"
        assert isinstance(
            self.container_tag, (str)
        ), f"{self.container_tag=}. Must be a str"
        assert isinstance(self.tag, (str)), f"{self.tag=}. Must be a str"
        assert isinstance(
            self.event, Sys_Events
        ), f"{self.event=}. Must be an entry in SYSEVENTS"
        assert isinstance(self.action, str), f"{self.action=}. Must be str"
        assert isinstance(self.object, (type(None), _qtpyBase)), (
            f"{self.object=} || {type(self.object)}. Must be None or an instance of"
            " _qtpyBase"
        )
        assert isinstance(self.widget_dict, dict), (
            f"{self.widget_dict=}. Must be a Dic[str, Union[types.FunctionType,"
            " types.LambdaType, types.MethodType]]"
        )
        assert (
            isinstance(self.parent_widget, (_qtpyBase, _qtpySDI_Frame))
            or self.parent_widget is None
        ), (  # QT 6.5.0
            f"{self.parent_widget=}. Must be an instance _qtpyBase, _qtpySDI_Frame or"
            " None"
        )
        assert isinstance(self.control_name, str), f"{self.control_name=}. Must be str"

        self._tag_dict = self.widget_dict
        super().__init__(parent=self)

    def trans_str(self, text: str) -> str:
        """
        It takes a string, translates it, and returns the translated string

        Args:
            text (str): The text to be translated.

        Returns:
            str: The translated text.
        """
        return self._lang_tran.translate(text, SDELIM)

    def value_get(self, container_tag: str = "", tag: str = "") -> any:
        """Returns the value sourced from a widget

        Args:
            container_tag (str): The tag name of the container that the widget is in.
            tag (str): The tag name of the widget you want to get the value of.

        Returns:
            any : The value of the widget.
        """
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        widget = self.widget_get(container_tag, tag)

        if hasattr(widget, "value_get"):
            return widget.value_get()
        else:
            raise AssertionError(f"{container_tag=} {tag=} Does Not Have A value_get")

    def value_set(
        self, container_tag: str = "", tag: str = "", value: any = None
    ) -> None:
        """Sets the value of a widget

        Args:
            container_tag (str): The tag name of the container widget that the widget is in.
            tag (str): The tag name of the widget you want to set the value of.
            value (any): The value to set the widget to.
        """
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        widget = self.widget_get(container_tag, tag)

        if hasattr(widget, "value_set"):
            widget.value_set(value)
        else:
            raise AssertionError(
                f"{container_tag=} {tag=} Does Not Have A value_set method"
            )

    def print_widget_dict(self):
        """Debug use prints the widget dictionary"""
        self.parent_app.widget_dict_print()

    def widget_del(self, container_tag: str, tag: str) -> None:
        """Deletes a widget from a container

        Args:
            container_tag (str): The tag name of the container widget that the widget to be deleted is in.
            tag (str): The tag name of the widget to be deleted.

        Returns:

        """
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        return self.parent_app.widget_del(
            window_id=self.window_id, container_tag=container_tag, tag=tag
        )

    def widget_exist(self, container_tag: str = "", tag: str = "") -> bool:
        """Returns True if the widget with the given tag name exists in the given container

        Args:
            container_tag (str): The tag name of the container widget that contains the widget you want to check.
            tag (str): The tag name of the widget you want to check for.

        Returns:
            bool : True if the widget exists, False otherwise.
        """
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        widget = self.parent_app.widget_exist(
            window_id=self.window_id, container_tag=container_tag, tag=tag
        )

        return widget

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> _qtpyBase_Control:
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Button":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "ComboBox":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "FolderView":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Grid":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "GridContainer":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Image":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "LineEdit":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "FormContainer":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "HBoxContainer":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "VBoxContainer":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "RadioButton":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Slider":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Spinbox":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Switch":
        ...

    @overload
    def widget_get(self, container_tag: str = "", tag: str = "") -> "Tab":
        ...

    def widget_get(self, container_tag: str = "", tag: str = "") -> _qtpyBase_Control:
        """Returns a widget from the parent app's widget dictionary.

        Assumes widget exists. Please use widget_exist call before calling this method

        Args:
            container_tag (str): The tag name of the container widget that holds the widget you want to get. Default: "".
            tag (str): The tag name of the widget to get. Default: "".

        Returns:
            _qtpyBase_Control: The requested widget.

        Raises:
            AssertionError: If container_tag or tag are not non-empty strings.
            RuntimeError: If the requested widget does not exist.
        """

        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str."
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str."

        widget = None

        widget = self.parent_app.widget_get(
            window_id=self.window_id, container_tag=container_tag, tag=tag
        )

        if widget is None:  # Dev Error
            print(
                "DEV Error Shutting Down, Widget Not Found -"
                f" {self.window_id=} {container_tag=} {tag=}"
            )
            sys.exit(1)

        return widget


class _Event_Handler(_qtpyBase):
    """Used to implement event handling."""

    def __init__(self, parent_app: QtPyApp, parent: None | _qtpyBase = None) -> None:
        """Constructor for the Event_Handler class. Checks the arguments and sets instance variables

        Args:
            parent_app (QtPyApp): The parent application. This is an instance of QtPyApp.
            parent (None |_qtpyBase): The parent widget. If no parent is given, the parent will be the parent_app.
        """

        assert isinstance(
            parent_app, QtPyApp
        ), f"{parent_app=}. Must be an insance of QtPyApp"
        assert isinstance(
            parent, (type(None), _qtpyBase_Control)
        ), f"{parent=}. Must be None or an instance of _qtpyBase_Control"

        super().__init__(parent if parent is not None else parent_app)

        # Private instance variables
        self._parent_app = parent_app
        if parent is not None:
            self._parent = parent

    def event(
        self,
        window_id: int,
        callback: Callable,
        container_tag: str,
        tag: str,
        event: IntEnum,
        action: str,
        value: any,
        widget_dict: dict[
            str, types.FunctionType | types.LambdaType | types.MethodType
        ],
        parent: Union[_qtpyBase_Control, QtPyApp],
        control_name: str,
    ) -> int:
        """The event handler method. This is the method that is called when an event is triggered.

        Args:
            callback (Callable): The method that will be called when the event is triggered.
            container_tag (str): The tag name of the container that the control is in.
            tag (str): The tag name of the control that generated the event.
            event (IntEnum): The event that triggered the callback.
            action (str): The action that was taken.  This is a string.
            value (any):  The value sourced from the control that generated the event. If available.
            widget_dict (dict[str, types.FunctionType | types.LambdaType | types.MethodType]): The widget dictionary
            parent (Union[_qtpyBase_Control, QtPyApp]): The parent widget.
            control_name (str): The name of the control that the event is coming from.

        Returns:
            int : 1.  If the event is accepted, -1. If the event is rejected

        """

        assert isinstance(event, Sys_Events), f"{event=} <{event}> must be of SYSEVENTS"

        event_action = Action(
            window_id=window_id,
            parent_app=self._parent_app,
            container_tag=container_tag,
            tag=tag,
            event=event,
            action=action,
            value=value,
            object=self,
            widget_dict=widget_dict,
            parent_widget=parent,
            control_name=control_name,
        )

        if isinstance(callback, dict):
            result = 1
        elif isinstance(callback, Callable):
            callback: Callable
            if callback.__code__.co_argcount == 0:
                raise RuntimeError(
                    f"Dev Error  callback {callback=} must have one Action (event)"
                    " argument only!"
                )

            result = callback(event_action)
        else:
            result = 1

        if (
            result is None
        ):  # or isinstance(result, types.GeneratorType):  # Default accept
            result = 1

        # if isinstance(
        #    result, types.GeneratorType
        # ):  # TODO Fix Generators - if they can be made to work
        #    return 1

        return result


@dataclasses.dataclass
class _Container(_qtpyBase_Control):
    """The _Container class handles the creation and layout of child widgets and containers."""

    align: Align = Align.LEFT
    colpad: bool = True
    scroll: bool = False
    controls_enabled: bool = True
    scroll_frame_off: Optional[Widget_Frame] = None
    scroll_frame_on: Optional[Widget_Frame] = None
    margin_left: int = -1
    margin_right: int = -1
    margin_top: int = -1
    margin_bottom: int = -1

    _scroll_width = -1
    _scroll_height = -1

    _scroll_deque: deque = field(default_factory=deque)

    _layout: list[list[_qtpyBase_Control]] = field(default_factory=list)  # [[]]

    # _layout[0] = []  # 0 Will always be the menu position
    _width: int = -1
    _height: int = -1

    _parent_app: Optional[QtPyApp] = None
    _parent: Optional[qtW.QWidget] = None
    _container_tag: str = ""
    _container: Optional[_qtpyBase_Control] = None
    _current_enable_settings: dict = field(default_factory=dict)  # {}

    _scroll_container: Optional[qtW.QScrollArea] = (
        None  # = qtW.QScrollArea(parent) #None
    )
    _scroll_current_widget: Optional[_qtpyBase_Control] = None

    def __post_init__(self) -> None:
        """Sets up the class variables and makes sure that the variables are of the correct type"""

        super().__post_init__()
        self._snapshots: dict = {}

        assert isinstance(self.colpad, bool), f"{self.colpad=}. Must be bool"
        assert isinstance(self.scroll, bool), f"{self.scroll=}. Must be bool"
        assert isinstance(
            self.controls_enabled, bool
        ), f"{self.controls_enabled=}. Must be bool"
        assert self.scroll_frame_off is None or isinstance(
            self.scroll_frame_off, Widget_Frame
        ), f"{self.scroll_frame_off=}. Must be an instance of widget_frame"
        assert self.scroll_frame_on is None or isinstance(
            self.scroll_frame_on, Widget_Frame
        ), f"{self.scroll_frame_on=}. Must be an instance of widget_frame"
        assert (
            isinstance(self.margin_left, int)
            and self.margin_left == -1
            or self.margin_left >= 0
        ), f"{self.margin_left=}. Must be int == -1 oe >=0"
        assert (
            isinstance(self.margin_right, int)
            and self.margin_right == -1
            or self.margin_right >= 0
        ), f"{self.margin_right=}. Must be int == -1 oe >=0"
        assert (
            isinstance(self.margin_top, int)
            and self.margin_top == -1
            or self.margin_top >= 0
        ), f"{self.margin_top=}. Must be int == -1 oe >=0"
        assert (
            isinstance(self.margin_bottom, int)
            and self.margin_bottom == -1
            or self.margin_bottom >= 0
        ), f"{self.margin_bottom=}. Must be int == -1 oe >=0"

        self._scroll_deque: deque = deque()

        self._layout: list[list[_qtpyBase_Control]] = [[]]
        self._layout[0] = []  # 0 Will always be the menu position

        self._current_enable_settings: dict = {}
        self._scroll_container: Optional[
            qtW.QScrollArea
        ]  # = qtW.QScrollArea(parent) #None

        if self.scroll_frame_off is None:
            self.scroll_frame_off: Widget_Frame = Widget_Frame(
                frame_style=Frame_Style.NONE
            )

        if self.scroll_frame_on is None:
            self.scroll_frame_on: Widget_Frame = Widget_Frame(
                frame_style=Frame_Style.BOX
            )

    def _create_widget(
        self,
        parent_app: QtPyApp,
        parent: qtW.QWidget,
        container_tag: str = "",
        debug: bool = False,
    ) -> qtW.QWidget:
        """Creates a QWidget instance of the container object and all the containers/controls it houses

        Args:
            parent_app (QtPyApp):  The application that owns the container
            parent (QWidget): The QWidget parent object that owns this container
            container_tag (str): The tag name of the container that houses the container object
            debug(bpp) : True Print debug info, False: Do not prnprint debug info


        Returns:
            QWidget: The created QtGui Widget populated with controls.

        """
        assert isinstance(
            parent_app, QtPyApp
        ), f"{parent_app=} <{parent_app}> must be an instance of QtPyApp"

        assert isinstance(
            parent, qtW.QWidget
        ), f"{parent=} <{parent}> must be an instance of qtW.QWidget"

        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=} <{container_tag}> must be a non-empty str"

        # ===== Helper
        def _pad_rows(
            container: "_Container",
            controls_across: int,
            max_text_len: int,
            layout: qtW.QLayout,
        ) -> dict[str, str]:
            """Pad out rows with spacers and set default control width to max_text_len.

            Args:
                container (_Container): The container object containing the layout to be padded.
                controls_across (int): The number of controls across.
                max_text_len (int): The maximum text length for controls.
                layout (qtW.QLayout): The layout object to be padded.

            Returns:
                dict[str, str] : A dictionary mapping form control tags to label texts.
            """
            form_labels: dict[str, str] = {}
            # max_row_height = 0

            for row_index, row_list in enumerate(container._layout):
                if (
                    row_index > 0
                    and len(row_list) < controls_across
                    and container.colpad
                ):
                    row_list.extend(
                        [Spacer(width=1, height=1)] * (controls_across - len(row_list))
                    )

                for col_control in row_list:
                    if col_control.width == -1:
                        col_control.width = max_text_len

                    if isinstance(layout, qtW.QFormLayout):
                        if hasattr(col_control, "label") and col_control.label != "":
                            form_labels[col_control.tag] = self.trans_str(
                                col_control.label.strip()
                            )

                            col_control.label = ""
                            col_control.label_pad = -1
                    elif hasattr(col_control, "label") and col_control.label_pad != -1:
                        col_control.label_pad = (
                            max_text_len - 1
                            if not isinstance(layout, qtW.QHBoxLayout)
                            and not isinstance(layout, qtW.QVBoxLayout)
                            and row_list.index(col_control) == 0
                            else col_control.label_pad - 1
                        )

            return form_labels

        def _add_controls_to_layout(
            parent_app: QtPyApp,
            parent: qtW.QWidget,
            child_container_tag: str,
            controls_across: int,
            layout: qtW.QLayout,
            form_labels: dict[str, str],
        ) -> None:
            """Add controls to a Qt layout.

            This function adds controls to a Qt layout. It is used internally by the `Container` and `DialogBox`
            classes.

            Args:
                parent_app (QtPyApp): The parent application.
                parent (qtW.QWidget): The parent widget.
                child_container_tag (str): The tag of the child container.
                controls_across (int): The number of controls across the layout.
                layout (qtW.QLayout): The Qt layout to add the controls to.
                form_labels (dict[str, str]): A dictionary of form labels for each control.

            Returns:
                None.
            """

            row_ptr = 0
            for row_list in self._layout:
                col_ptr = 0

                for col_control in row_list:
                    if col_control is None:
                        continue

                    if col_control.height <= 0:
                        col_control.height = (
                            BUTTON_SIZE.height if isinstance(col_control, Button) else 1
                        )

                    if isinstance(col_control, _Container):
                        alignment = col_control.align.value
                        self.controls_enabled = col_control.controls_enabled

                        widget = col_control._create_widget(
                            parent_app=parent_app,
                            parent=parent if self._widget is None else self._widget,
                            container_tag=child_container_tag,
                        )
                        col_control.controls_enable(self.controls_enabled)

                    else:
                        alignment = col_control.align.value
                        widget = col_control._create_widget(
                            parent_app=parent_app,
                            parent=(
                                parent
                                if isinstance(col_control, Menu)
                                else self._widget
                            ),
                            container_tag=child_container_tag,
                        )

                    if isinstance(col_control, Menu):
                        assert isinstance(
                            parent, _qtpyFrame
                        ), f"{parent=}. Menu parent must be an instance of _qtpyFrame"
                        parent.setMenuWidget(widget)
                        widget.resize(widget.minimumSizeHint())
                    else:
                        if isinstance(layout, qtW.QFormLayout):
                            if col_control.tag in form_labels:
                                layout.addRow(form_labels[col_control.tag], widget)
                                form_labels.pop(col_control.tag)
                            else:
                                layout.addRow(" ", widget)
                        elif isinstance(layout, qtW.QGridLayout):
                            if isinstance(col_control, _Container):
                                layout.setHorizontalSpacing(
                                    10
                                )  # TODO Add setting Container spacing
                            col_span = (controls_across - len(row_list)) + 1
                            row_span = 1
                            layout.addWidget(
                                widget, row_ptr, col_ptr, row_span, col_span, alignment
                            )
                        else:
                            layout.addWidget(widget, alignment=self.align.value)

                        if col_ptr == len(row_list) - 1:
                            row_ptr += 1

                        col_ptr += 1

        # ===== Main
        window_id = Get_Window_ID(parent_app, parent, self)

        parent_app.widget_add(
            window_id=window_id, container_tag=container_tag, tag=self.tag, widget=self
        )

        container = self
        self.container_tag = container_tag
        child_container_tag = self.tag

        self._parent_app = parent_app
        self._parent = parent
        self._container_tag = container.tag
        self._container = container

        self.txt_font: Font = (
            parent_app.app_font_def
            if self.txt_font is None
            else parent_app.app_font_def
        )

        if self.scroll:
            self._scroll_container = qtW.QScrollArea(parent)
            self._scroll_container.verticalScrollBar().valueChanged.connect(
                lambda *args: self._scroll_handler(Sys_Events.SCROLLV, args)
            )
            self._scroll_container.horizontalScrollBar().valueChanged.connect(
                lambda *args: self._scroll_handler(Sys_Events.SCROLLH, args)
            )

        controls_across: int = container.controls_across
        max_text_len: int = container.max_text_len

        if self.text is None or self.text.strip() == "":  # Frame
            widget_group = qtW.QFrame(parent)

            if debug:
                widget_group.setFrameStyle(1)  # Debug
        else:  # Groupbox
            widget_group = qtW.QGroupBox(self.text, parent)

            if debug:
                widget_group.setStyleSheet(
                    "QGroupBox {border:1px solid"
                    f" cyan;font-weight:{Font_Weight_Text[self.txt_font.weight]}}} "
                )
            else:
                widget_group.setStyleSheet(
                    "QGroupBox"
                    f" {{font-weight:{Font_Weight_Text[self.txt_font.weight]}}} "
                )

        widget_group.setContentsMargins(0, 0, 0, 0)

        # Gets default platform alignment for labels
        if (align := qtW.QFormLayout().labelAlignment()) == Align.LEFT.value:
            label_align = Align.LEFT
        elif align == Align.RIGHT.value:
            label_align = Align.RIGHT
        elif align == Align.TOP.value:
            label_align = Align.TOP
        elif align == Align.BOTTOM.value:
            label_align = Align.BOTTOM
        else:
            label_align = Align.CENTER

        if isinstance(self, FormContainer):
            layout = qtW.QFormLayout()
            margin_left = 4 if self.margin_left == -1 else self.margin_left
            margin_right = 9 if self.margin_right == -1 else self.margin_right
            margin_top = 4 if self.margin_top == -1 else self.margin_top
            margin_bottom = 4 if self.margin_bottom == -1 else self.margin_bottom
        elif isinstance(self, GridContainer):
            layout = qtW.QGridLayout()
            margin_left = 4 if self.margin_left == -1 else self.margin_left
            margin_right = 9 if self.margin_right == -1 else self.margin_right
            margin_top = 4 if self.margin_top == -1 else self.margin_top
            margin_bottom = 4 if self.margin_bottom == -1 else self.margin_bottom

            layout.setHorizontalSpacing(0)  # TODO Add settings for this and alignment
            layout.setVerticalSpacing(3)
        elif isinstance(self, HBoxContainer):
            layout = qtW.QHBoxLayout()
            margin_left = 2 if self.margin_left == -1 else self.margin_left
            margin_right = 2 if self.margin_right == -1 else self.margin_right
            margin_top = 2 if self.margin_top == -1 else self.margin_top
            margin_bottom = 2 if self.margin_bottom == -1 else self.margin_bottom
        else:
            layout = qtW.QVBoxLayout()
            margin_left = 4 if self.margin_left == -1 else self.margin_left
            margin_right = 9 if self.margin_right == -1 else self.margin_right
            margin_top = 4 if self.margin_top == -1 else self.margin_top
            margin_bottom = 4 if self.margin_bottom == -1 else self.margin_bottom

        # layout.setContentsMargins(0, 0, 0, 0) #Debug

        layout.setContentsMargins(margin_left, margin_top, margin_right, margin_bottom)

        widget_group.setLayout(layout)
        self._widget = widget_group

        # Pad out rows with spacers and set default control width to max_text_len
        form_labels = _pad_rows(
            container,
            controls_across,
            max_text_len,
            layout,
        )

        _add_controls_to_layout(
            parent_app,
            parent,
            child_container_tag,
            controls_across,
            layout,
            form_labels,
        )

        self._widget.setObjectName(self.tag)

        char_pixel_size = self.pixel_char_size(char_height=1, char_width=1)

        if (
            isinstance(self, _Container)
            and self.width
            > widget_group.layout().totalMinimumSize().width() // char_pixel_size.width
        ):
            self._width = (char_pixel_size.width * self.width) + self.tune_hsize
        else:
            self._width = (
                widget_group.layout().totalMinimumSize().width()
            ) + self.tune_hsize

        if (
            isinstance(self, _Container)
            and self.height
            > widget_group.layout().totalMinimumSize().height()
            // char_pixel_size.height
        ):
            self._height = round(
                (char_pixel_size.height * self.height) + self.tune_vsize
            )
        else:
            self._height = round(
                widget_group.layout().totalMinimumSize().height()
                + (char_pixel_size.height * 2.3)
                + self.tune_vsize
            )

        if isinstance(widget_group, qtW.QGroupBox):
            pass
        else:
            self._widget.setFrameStyle(Frame_Style.NONE.value)

            if debug:
                self._widget.setFrameStyle(Frame_Style.BOX.value)  # Debug

        if self.scroll:
            # scroll_container.setFrameStyle(1) #Debug

            layout.setSpacing(1)
            # TODO Make user configurable
            layout.setAlignment(qtC.Qt.AlignTop | qtC.Qt.AlignCenter)

            scroll_bar_width = (
                parent_app.app_get.style().pixelMetric(qtW.QStyle.PM_ScrollBarExtent)
                + 12
            )

            if debug:
                widget_group.setFrameStyle(Frame_Style.BOX.value)  # Debug

            self._scroll_container.setWidgetResizable(True)
            self._scroll_container.setWidget(widget_group)
            self._scroll_container.setVerticalScrollBarPolicy(qtC.Qt.ScrollBarAsNeeded)
            self._scroll_container.setHorizontalScrollBarPolicy(
                qtC.Qt.ScrollBarAsNeeded
            )

            self._scroll_container.setFixedSize(
                self._width + scroll_bar_width, self._height + scroll_bar_width
            )
            self._scroll_width = self._scroll_container.width()
            self._scroll_height = self._scroll_container.height()

            return self._scroll_container

        assert self._width > 0, f"Dev Error {self._width=} Must be > 0"
        assert self._height > 0, f"Dev Error {self._height=} Must be > 0"

        if isinstance(parent, (_qtpyFrame)):
            # Get our widgets on the screen
            if parent.centralWidget() is None:
                sheet_widget = qtW.QWidget()
                sheet_widget.setLayout(qtW.QGridLayout())
                parent.setCentralWidget(sheet_widget)
            parent.centralWidget().layout().addWidget(widget_group)

            # TODO Might need Resize policy stuff if I choose to allow resize
            # Fix sheet size
            parent.resize(
                self._width,
                self._height,
            )
            parent.setMinimumSize(
                self._width,
                self._height,
            )

            # Centre sheet
            centerPoint = qtG.QGuiApplication.screens()[0].geometry().center()
            parent.move(centerPoint - parent.frameGeometry().center())
        else:
            if parent.layout() is not None:
                parent.layout().addWidget(widget_group)

                if isinstance(widget_group, qtW.QGroupBox):
                    widget_group.setMaximumSize(
                        # widget_group.setFixedSize(
                        self._width,
                        self._height,
                    )
                else:
                    widget_group.setMaximumSize(
                        # widget_group.setFixedSize(
                        self._width,
                        self._height,
                    )

        # parent.dumpObjectTree() #Debug
        # self.dump() #Debug

        return self._widget

    @overload
    def add_control(
        self, control: _qtpyBase_Control, row: int, col: int
    ) -> "GridContainer":
        ...

    @overload
    def add_control(
        self,
        control: _qtpyBase_Control,
        zero_based: bool = False,
    ) -> "FormContainer":
        ...

    @overload
    def add_control(
        self,
        control: _qtpyBase_Control,
        zero_based: bool = False,
    ) -> "HBoxContainer":
        ...

    @overload
    def add_control(
        self,
        control: _qtpyBase_Control,
        zero_based: bool = False,
    ) -> "VBoxContainer":
        ...

    def add_control(
        self,
        control: _qtpyBase_Control,
        row: int = -1,
        col: int = -1,
        zero_based: bool = False,
    ) -> "_Container":
        """Adds a gui control to the container.

        Args:
            control (_qtpyBase_Control): The gui control added to the container.
            row (int): The row the gui control will be placed in.
            col (int): The col the gui control will be placed in.
            zero_based (bool): Set if row/col addressing is zero based.

        Returns:
            _Container: Reference to the container instance.
        """
        if not isinstance(control, _qtpyBase_Control):
            raise RuntimeError(
                f"{_qtpyBase_Control=} Must be an instance of _qtpyBase_Control!"
            )

        if isinstance(control, Menu):
            self._layout.insert(0, [control])
        else:
            if row == -1 and col == -1:
                zero_based = True
                col = 0
                row = len(self._layout) + 1
            elif row == 1 and col == -1:
                zero_based = True
                row = 0

                if len(self._layout) <= 1:
                    col = 0
                else:
                    col = len(self._layout[row + 1])

            if zero_based:
                assert (
                    isinstance(row, int) and row >= 0
                ), f"{control=}. row <{row}> is an int >= 0"
                assert (
                    isinstance(col, int) and col >= 0
                ), f"{control=}. col <{col}> is an int >= 0"
            else:
                assert (
                    isinstance(row, int) and row > 0
                ), f"{control=}. row <{row}> is an int > 0"
                assert (
                    isinstance(col, int) and col > 0
                ), f"{control=}. col <{col}> is an int > 0"
                row -= 1
                col -= 1

            row += 1
            assert isinstance(
                control, _qtpyBase_Control
            ), f"{control=}. Must be an instance of _qtpyBase_Control"

            max_row = len(self._layout)

            for _ in range(max_row, row + 1):
                self._layout.append([Spacer(width=1, height=1)])

            max_col = len(self._layout[row])
            delta = col - max_col + 1

            for _ in range(max_col, max_col + delta):
                self._layout[row].append(Spacer(width=1, height=1))

            self._layout[row][col] = control

            if self._widget is not None:
                self.widget_add(control)

        return self

    @overload
    def add_row(self, *controls: _qtpyBase_Control, row: int = -1) -> "_Container":
        ...

    @overload
    def add_row(self, *controls: _qtpyBase_Control, row: int = -1) -> "GridContainer":
        ...

    @overload
    def add_row(self, *controls: _qtpyBase_Control, row: int = -1) -> "HBoxContainer":
        ...

    @overload
    def add_row(self, *controls: _qtpyBase_Control, row: int = -1) -> "VBoxContainer":
        ...

    def add_row(
        self, *controls: _qtpyBase_Control, row: int = -1
    ) -> Union[
        "_Container", "GridContainer", "FormContainer", "VBoxContainer", "HBoxContainer"
    ]:
        """Adds a row to the Container. If a HBoxContainer or VBoxContainer only one row is present
        (Horizontal or Vertical respectively) and a second add row call will replace the existing controls

        Args:
            *controls (_qtpyBase_Control): A list of qtGui controls
            row (int): Optional, row where the controls are to be placed. Ignored with HBoxContainers or VBoxContainers

        Returns:
            Union[FormContainer, GridContainer, HBoxContainer, VBoxContainer]: The container instance
        """
        assert isinstance(row, int) and (
            row > 0 or row == -1
        ), f"{row=}. Must be an int > 0"

        if row == -1:
            row = self.controls_down + 1

        # If the container has a parent app and a widget exists, remove the controls in the target row
        if self._parent_app is not None and self._widget is not None:
            for row_index, row_item in enumerate(self._layout):
                if row_index + 1 == row:
                    for col_item in reversed(tuple(row_item)):
                        self.widget_del(
                            container_tag=col_item.container_tag, tag=col_item.tag
                        )
                        row_item.pop()
                    break

        for col_index, control in enumerate(controls):
            assert isinstance(
                control, _qtpyBase_Control
            ), f"{control=}. Must be an instance of _qtpyBase_Control"

            # If the container has a parent app and the control already exists, remove it
            if self._parent_app is not None and self.widget_exist(
                container_tag=self.container_tag, tag=control.tag
            ):
                self.widget_del(container_tag=self.container_tag, tag=control.tag)

            # Add the control to the appropriate type of container
            if isinstance(self, GridContainer):
                self.add_control(control=control, row=row, col=col_index + 1)
            elif isinstance(self, (FormContainer, VBoxContainer, HBoxContainer)):
                self.add_control(control=control)
            else:
                raise AssertionError(
                    f"{self.tag=} is not a suitable container for {control.tag=}"
                )

        return self

    def clear(self) -> None:
        """Clears the values displayed in the gui widgets housed in this container"""

        if self.allow_clear:
            # Iterate over the items in the container, retrieve their widgets and clear them
            for item in reversed(tuple(self.tags_gather())):
                widget = self.widget_get(container_tag=item.container_tag, tag=item.tag)
                if widget.allow_clear and hasattr(widget.guiwidget_get, "clear"):
                    widget.guiwidget_get.clear()

    def dump(self) -> None:
        """Prints the widget dictionaryto console. Used for debugging"""
        self._parent_app.widget_dict_print()

    def pixel_width_height(self) -> tuple[int, int]:
        """Returns the width and height of the container in pixels. Note not tested yet!

        Returns:
            tuple[int,int]: Width and Height in pixels


        """
        height = self.guiwidget_get.height()
        width = self.guiwidget_get.width()

        if self.buddy_control is not None:
            if isinstance(self.buddy_control.guiwidget_get, _Container):
                self.buddy_control: _Container
                width, height = self.buddy_control.pixel_width_height()
            else:
                height += self.buddy_control.guiwidget_get.height()
                width += self.buddy_control.guiwidget_get.width()

        for row_item in self._layout:
            max_col_height = 0
            col_width = 0
            for col_item in row_item:
                assert (
                    col_item.guiwidget_get is not None
                ), f"DEV Error {col_item=} Widget not created yet"

                if isinstance(col_item.guiwidget_get, _Container):
                    container_height, container_width = self.pixel_width_height()
                    if container_height > max_col_height:
                        max_col_height = max_col_height
                    col_width += container_width
                elif col_item.guiwidget_get.height() > max_col_height:
                    max_col_height = col_item.guiwidget_get.height()
                    col_width += col_item.guiwidget_get.width()
            if col_width > width:
                width += col_width
            height += max_col_height

        return width, height

    def widget_add(self, control: _qtpyBase_Control) -> None:
        """Adds a widget to the container

        Args:
            control (_qtpyBase_Control): qtgui control added to the container
        """
        assert isinstance(
            control, _qtpyBase_Control
        ), f"{control=}. Must be an descendant of _qtpyBase_Control"

        assert self._widget is not None, f"Container {self.tag=} is not created yet"

        if self._parent_app is None:
            raise AssertionError(f"{self._parent_app=}. Not Set")

        if control.height <= 0:
            control.height = 1
        if control.width <= 0:
            control.width = 1

        widget = control._create_widget(
            parent_app=self._parent_app,
            parent=self._widget,
            container_tag=self.tag,
        )

        if self.scroll:
            self._scroll_deque.append(widget_def(widget=control, gui_widget=widget))

        self._widget.layout().addWidget(widget)
        delta_height = 0

        char_size = self.pixel_char_size(char_height=1, char_width=1)

        assert control.height > 0, f"Dev Error {control.height=}. Must be > 0"

        widget.setMinimumHeight(control.height * char_size.height)

        if isinstance(self._widget, qtW.QGroupBox):
            if isinstance(self, HBoxContainer):
                self._width += widget.width()
                # self._height = widget.height()

                height = self._height  # self.height * char_size.height

            else:
                self._height += widget.height()
                height = self._height

            assert self._width > 0, f"Dev Error {self._width=}. Must be > 0"
            assert height > 0, f"Dev Error {height + delta_height=}. Must be > 0"

            self._widget.resize(self._width, height)  # char_pixel_size.height)
            # self._widget.setMaximumSize(self._width, height + delta_height)
            self._widget.setFixedSize(self._width, height + delta_height)

        # self._widget.dumpObjectTree()  # Debug

    def widget_gui_controls_get(self) -> list[_qtpyBase_Control]:
        """Returns a list populated with the qtgui controls housed in the container.

        Returns:
            list[_qtpyBase_Control]: list of qtgui control in container

        """
        if self._parent_app is None and g_application is None:
            raise RuntimeError(f"{self._parent_app=}. Not set!")

        if self._parent_app is None:
            self._parent_app = g_application

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        return self._parent_app.widget_gui_controls_get(
            window_id=window_id, container_tag=self.tag
        )

    def widget_del(self, container_tag: str, tag: str) -> None:
        """Deletes a widget from the designated container

        Args:
            container_tag (str): Container tag.
            tag (str): Widget tag.

        Returns:
            None

        """
        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be a non-empty str"
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        if self._parent_app is None:
            raise RuntimeError(f"{self._parent_app=}. Not set!")

        for index, item in enumerate(self._scroll_deque):
            if item.widget.container_tag == container_tag and item.widget.tag == tag:
                del self._scroll_deque[index]
                break

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        self._parent_app.widget_del(
            window_id=window_id, container_tag=container_tag, tag=tag
        )

        return None

    def widget_exist(self, container_tag: str, tag: str) -> bool:
        """Determines if a gui widget exists. Assumes container_tag and tag are correctly spelled and formatted!

        Args:
            container_tag (str): The container name housing the widget
            tag (str): The name of the widget

        Returns:
            bool : True if the widget exists and False if it does not

        """
        if self._parent_app is None:
            raise RuntimeError(f"{self._parent_app=}. Not set!")

        assert (
            isinstance(container_tag, str) and container_tag.strip() != ""
        ), f"{container_tag=}. Must be str"
        assert isinstance(tag, str) and tag.strip() != "", f"{tag=}. Must be str"

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        return self._parent_app.widget_exist(
            window_id=window_id, container_tag=container_tag, tag=tag
        )

    # TODO Keep return type uptodate
    def widget_get(
        self, container_tag: str, tag: str
    ) -> Union[
        _qtpyBase_Control,
        "Button",
        "Checkbox",
        "ComboBox",
        "Dateedit",
        "FolderView",
        "FormContainer",
        "Grid",
        "HBoxContainer",
        "Image",
        "LCD",
        "Label",
        "LineEdit",
        "Spacer",
        "RadioButton",
        "Slider",
        "Spinbox",
        "Switch",
        "Tab",
        "TextEdit",
        "Timeedit",
        "Treeview",
        "VBoxContainer",
    ]:
        """Returns a gui widget. Assumes container_tag and tag are correctly spelled and formatted!

        Args:
            container_tag (str): The container name housing the widget
            tag (str): The name of the widget

        Returns:
            _qtpyBase_Control: One of the qtgui controls

        """
        if self._parent_app is None:
            raise RuntimeError(f"{self._parent_app=}. Not set!")

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        return self._parent_app.widget_get(
            window_id=window_id, container_tag=container_tag, tag=tag
        )

    def widgets_clear(self) -> None:
        """Clears all the widgets from the container

        Returns:

        """
        if self._widget is None:
            return None

        widget_list = []

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        if self.scroll and self.scroll_controls_get:
            for widget in self.scroll_controls_get:
                widget_list.append(widget)
            self._scroll_deque.clear()
            self._scroll_container.resize(self._scroll_width, self._scroll_height)

        for widget in self._parent_app.widget_gui_controls_get(
            window_id=window_id, container_tag=self.tag
        ):
            widget_list.append(widget)

        for widget in reversed(widget_list):
            if self.widget_exist(widget.container_tag, tag=widget.tag):
                # Shiboken check needed because underlying widget might not exist
                if widget.guiwidget_get is not None and shiboken6.isValid(
                    widget.guiwidget_get
                ):
                    widget.guiwidget_get.setVisible(False)

                self._parent_app.widget_del(
                    window_id=window_id,
                    container_tag=widget.container_tag,
                    tag=widget.tag,
                )

        # self._scroll_deque.clear()

        return None

    @property
    def control_list_get(self) -> list[list[_qtpyBase_Control]]:
        """Returns the 2D control layout list for the Container

        Returns:
            list[list[_qtpyBase_Control]]: The 2D layout list

        """
        return self._layout

    def control_get(self, row: int, col: int) -> _qtpyBase_Control:
        """Returns the container control referenced by row and col
            TODO: Make one or zero based

        Args:
            row (int): Row where control is located
            col (int): Col where control is located

        Returns:
            _qtpyBase_Control: The control at row.col

        """
        assert isinstance(row, int) and 0 <= row < len(
            self._layout
        ), f"{row=} is an int  >= 0 and < {len(self._layout)}"

        assert isinstance(col, int) and 0 <= col < len(
            self._layout[row]
        ), f"{col=} is an int  > 0 and < {len(self._layout[row])}"

        return self._layout[row][col]

    @property
    def col_width_max(self) -> int:
        """Returns the max column width for the container control

        Returns:
            int: Max column width

        """
        col_width_max = 0

        for row_list in self.control_list_get:
            col_width_line_max = 0

            for col_control in row_list:
                if col_control is None:
                    continue

                elif col_control.width == -1:
                    if self.max_text_len > col_width_line_max:
                        col_width_line_max = self.max_text_len
                else:
                    if col_control.width > col_width_line_max:
                        col_width_line_max = col_control.width

            if col_width_line_max > col_width_max:
                col_width_max = col_width_line_max

        return col_width_max

    @property
    def col_width_total(self) -> int:
        """Returns the total (summed) maximum column width of all columns for the container control

        Returns:
            (int): Total (summed) maximum column width

        """
        col_width_total = 0

        for row_list in self.control_list_get:
            col_width_line_total = 0

            for col_control in row_list:
                if col_control is None:
                    continue
                elif col_control.width == -1:
                    col_width_line_total += self.max_text_len
                else:
                    if hasattr(col_control, "label"):
                        text_len = amper_length(col_control.label) + col_control.width
                    else:
                        text_len = col_control.width

                    col_width_line_total += text_len

            if col_width_line_total > col_width_total:
                col_width_total = col_width_line_total

        return col_width_total

    def controls_enable_state_save(self) -> None:
        """Saves the current enable state of all widgets in the container"""
        self._current_enable_settings = {}

        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        for item in self.tags_gather():
            widget = self._parent_app.widget_get(window_id=window_id, tag=item.tag)
            if isinstance(widget, _Container):
                continue

            if hasattr(widget, "enable_get"):
                if item.container_tag not in self._current_enable_settings:
                    self._current_enable_settings[item.container_tag] = {}

                if isinstance(widget, Tab):
                    self._current_enable_settings[item.container_tag][item.tag] = (
                        widget.enable_get(item.tag)
                    )
                else:
                    self._current_enable_settings[item.container_tag][
                        item.tag
                    ] = widget.enable_get

    def controls_enable_state_restore(self) -> None:
        """Restores the enable state of all controls in the container"""

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        for container_tag, items in self._current_enable_settings.items():
            for item_tag, enabled in items.items():
                widget = self._parent_app.widget_get(
                    window_id=window_id, container_tag=container_tag, tag=item_tag
                )
                if isinstance(widget, _Container):
                    continue

                if isinstance(widget, Tab):
                    widget.enable_set(item_tag, enabled)
                else:
                    widget.enable_set(enabled)

    def controls_enable(self, enable: bool) -> None:
        """Enables or disables all the widgets in the container.

        Args:
            enable (bool): True, controls enabled or False, controls disabled
        """
        assert isinstance(enable, bool), f"{enable=}. Must be bool"

        if self._parent_app is None:
            raise AssertionError(f"{self._parent_app=}. Not set!")

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        for item in self.tags_gather():
            widget = self._parent_app.widget_get(
                window_id=window_id, container_tag=item.container_tag, tag=item.tag
            )
            if isinstance(widget, _Container):
                continue

            try:
                if hasattr(widget, "enable_set"):
                    if isinstance(widget, Tab):
                        widget.enable_set("", enable)
                    else:
                        widget.enable_set(enable)
            except:
                print(f"Enable Failed {enable=} {widget.tag=} {widget.control_name=}")

    @property
    def row_height_max(self) -> int:
        """Returns the maximum row height in the Container

        Returns:
            (int): The maximum row height

        """
        row_height_max = 0

        for row_index, row_list in enumerate(self.control_list_get):
            row_height = 0

            for col_index, col_control in enumerate(row_list):
                if col_control is None:
                    continue
                if isinstance(col_control, _Container):
                    if (
                        col_control.row_height_max > row_height_max
                    ):  # Might need recursion
                        row_height = col_control.row_height_max
                else:
                    if col_control.height > row_height:
                        row_height = col_control.height

            if row_height > row_height_max:
                row_height_max = row_height

        return row_height_max

    def combobox_parents(self, combobox_tag: str = "") -> list["ComboBox"]:
        """Returns a list of all the parent ComboBoxes of the ComboBox referenced by the combobox_tag

        Args:
            combobox_tag (str): The tag name of the ComboBox that we are seeking the parents of

        Returns:
            list[ComboBox] : A list of parent ComboBox objects.
        """
        combo_dict: dict[str, list[ComboBox]] = {}
        for item in self.tags_gather():
            widget = self.widget_get(container_tag=item.container_tag, tag=item.tag)

            if widget is not None and isinstance(widget, ComboBox):
                combo_dict[widget.tag] = []

                if widget.parent_tag != "":
                    self._combobox_parent_gather(
                        widget.tag, combo_list=combo_dict[widget.tag]
                    )

        if combobox_tag in combo_dict:
            return combo_dict[combobox_tag]
        else:
            return []

    def _combobox_parent_gather(self, child_tag, combo_list: list["ComboBox"]) -> None:
        """Gathers all the ComboBox widgets that are the parents of the ComboBox widget with the tag name of the `
        child_tag`.

        Args:
            child_tag: The tag name of the child combobox.
            combo_list (list["ComboBox"]): list["ComboBox"]: A list of ComboBox objects that are the parents of the child
                combobox. Passed by reference and updated in the method
        """
        for item in self.tags_gather():
            if item.tag == child_tag:
                widget = self.widget_get(container_tag=item.container_tag, tag=item.tag)
                if widget is not None and isinstance(widget, ComboBox):
                    combo_list.append(widget)
                    if widget.parent_tag != "":
                        self._combobox_parent_gather(widget.parent_tag, combo_list)

    def _scroll_handler(self, event: Sys_Events, *args) -> int:
        """Handles scroll events. If the callback function is callable, then it is called and the result returned

        Args:
            event (SYSEVENTS): The event that was triggered.

        Returns:
            int: The return value that is the result of calling the event handler.
        """
        if self._parent_app is None:
            parent_app = g_application
        else:
            parent_app = self._parent_app

        widgets_visible = {}

        for widget_def in self._scroll_deque:
            if not widget_def.widget.guiwidget_get.visibleRegion().isEmpty():
                widgets_visible[widget_def.widget.tag] = widget_def

        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        if callable(self.callback):
            result = _Event_Handler(parent_app=parent_app, parent=self).event(
                window_id=window_id,
                callback=self.callback,
                container_tag="",
                tag=self.tag,
                event=event,
                action=self.callback.__name__,
                value=(widgets_visible, args),
                widget_dict=parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.container_tag
                ),
                parent=self,
                control_name=self.__class__.__name__,
            )

            if result == 1:  # Ok
                return 1  # event.accept()
            else:
                return -1  # event.ignore()
        else:
            return 1  # event.accept()

    @property
    def scroll_control_get(self) -> Optional[_qtpyBase_Control]:
        """Returns the current widget in the scroll area

        Returns:
            Optional[_qtpyBase_Control] : The current widget that is being displayed in the scroll area.
        """
        return self._scroll_current_widget

    @property
    def scroll_controls_get(self) -> tuple[_qtpyBase_Control, ...]:
        """Returns a tuple of containing the widgets in the scroll_deque.

        Returns:
            tuple[_qtpyBase_Control, ...] : A tuple of the widgets in the scroll_deque.
        """
        return tuple(i.widget for i in self._scroll_deque)

    def scroll_first(self) -> Optional[_qtpyBase_Control]:
        """Scrolls to the first widget in the scroll area.

        If the scroll attribute is True, and the scroll queue is not empty, then the current widget is set to the first
        widget in the scroll queue, and the frame style of the current widget is set to the scroll frame  attribute

        Returns:
            Optional[_qtpyBase_Control] : The current widget that was scrolled to.
        """
        if self.scroll and self._scroll_deque:
            if self._scroll_current_widget is not None:
                self._scroll_current_widget.frame_style_set(frame=self.scroll_frame_off)
            self._scroll_container.ensureWidgetVisible(self._scroll_deque[0].gui_widget)
            self._scroll_current_widget: _qtpyBase_Control = self._scroll_deque[
                0
            ].widget
            self._scroll_current_widget.frame_style_set(frame=self.scroll_frame_on)
            self._scroll_container.ensureVisible(1, 1, 1, 1)
            return self._scroll_current_widget
        else:
            return None

    def scroll_last(self) -> Optional[_qtpyBase_Control]:
        """Scrolls to the last widget in the scroll area.

        If there are widgets in the scroll queue, then this method scrolls to the last widget in the queue,
        and sets the frame style of the last item to the scroll frame  attribute

        Returns:
            Optional[_qtpyBase_Control] : The last widget in the scroll queue.
        """
        if self.scroll and len(self._scroll_deque) > 0:
            self._scroll_container.ensureWidgetVisible(
                self._scroll_deque[-1].gui_widget
            )

            if self._scroll_current_widget is not None:
                self._scroll_current_widget.frame_style_set(frame=self.scroll_frame_off)
            self._scroll_current_widget = self._scroll_deque[-1].widget
            self._scroll_current_widget.frame_style_set(frame=self.scroll_frame_on)

            return self._scroll_current_widget
        else:
            return None

    def scroll_next(self) -> Optional[_qtpyBase_Control]:
        """Scrolls to the next widget in the scroll area and sets the frame style of the widget to the scroll frame
        attribute.

        Returns:
            Optional[_qtpyBase_Control] : The current widget that was scrolled to.
        """
        if self.scroll and len(self._scroll_deque) > 0:
            for index, item in enumerate(self._scroll_deque):
                if (
                    item.widget.container_tag
                    == self._scroll_current_widget.container_tag
                    and item.widget.tag == self._scroll_current_widget.tag
                ):
                    ele_index = index + 1

                    if ele_index == len(self._scroll_deque):
                        ele_index = 0

                    if self._scroll_current_widget is not None:
                        self._scroll_current_widget.frame_style_set(
                            frame=self.scroll_frame_off
                        )
                    self._scroll_container.ensureWidgetVisible(
                        self._scroll_deque[ele_index].gui_widget
                    )
                    self._scroll_current_widget = self._scroll_deque[ele_index].widget
                    self._scroll_current_widget.frame_style_set(
                        frame=self.scroll_frame_on
                    )

                    return self._scroll_current_widget

            return None

    def scroll_prev(self) -> Optional[_qtpyBase_Control]:
        """Scrolls to the previous widget in the scroll area and sets the frame style of the wisget to the scroll frame
        attribute.


        Returns:
            Optional[_qtpyBase_Control] : The current widget that was scrolled to.
        """
        if self.scroll and len(self._scroll_deque) > 0:
            for index, item in enumerate(self._scroll_deque):
                if (
                    item.widget.container_tag
                    == self._scroll_current_widget.container_tag
                    and item.widget.tag == self._scroll_current_widget.tag
                ):
                    ele_index = index - 1

                    if ele_index < 0:
                        ele_index = -1

                    if self._scroll_current_widget is not None:
                        self._scroll_current_widget.frame_style_set(
                            frame=self.scroll_frame_off
                        )
                    self._scroll_container.ensureWidgetVisible(
                        self._scroll_deque[ele_index].gui_widget
                    )
                    self._scroll_current_widget = self._scroll_deque[ele_index].widget
                    self._scroll_current_widget.frame_style_set(
                        frame=self.scroll_frame_on
                    )

                    return self._scroll_current_widget

        return None

    def scroll_to(
        self, container_tag: str = "", tag: str = "", index: int = -1
    ) -> Optional[_qtpyBase_Control]:
        """Scrolls to the widget in the scroll area that matches the given container_tag and tag names

        Args:
            container_tag (str): The tag name of the container widget
            tag (str): The tag name of the widget you want to scroll to.
            index (int): The index of the widget to scroll to. If -1, then the widget is searched for. If > 0 This
                overrides the tag and container_tag arguments.

        Returns:
            Optional[_qtpyBase_Control]: The widget that was scrolled to.
        """
        if self.scroll:
            deque_len = len(self._scroll_deque) - 1  # Zero based
            assert (
                isinstance(index, int) and (index == -1) or (0 <= index <= deque_len)
            ), f"{index=}. Must be -1 or >=0 {index=} <= {deque_len=}"

            if index == -1:  # Search for item
                assert (
                    isinstance(container_tag, str) and container_tag.strip() != ""
                ), f"{container_tag=}. Must be a non-empty str"
                assert (
                    isinstance(tag, str) and tag.strip() != ""
                ), f"{tag=}. Must be a non-empty str"

                for item_index, item in enumerate(self._scroll_deque):
                    if (
                        item.widget.container_tag == container_tag
                        and item.widget.tag == tag
                    ):
                        index = item_index
                        break

            if index >= 0:
                gui_widget: qtW.QWidget = self._scroll_deque[index].gui_widget

                if self._scroll_current_widget is not None:
                    self._scroll_current_widget.frame_style_set(
                        frame=self.scroll_frame_off
                    )
                self._scroll_container.ensureWidgetVisible(gui_widget)
                self._scroll_current_widget: _qtpyBase_Control = self._scroll_deque[
                    index
                ].widget
                self._scroll_current_widget.frame_style_set(frame=self.scroll_frame_on)
                self._scroll_container.ensureVisible(
                    gui_widget.x(), gui_widget.y(), 1, 1
                )

                return self._scroll_current_widget
        return None

    def tags_gather(
        self,
        container: Optional["_Container"] = None,
        tag_list: Optional[list[tags]] = None,
    ) -> list[tags]:
        """Serializes all the tags in a container (and its sub-containers) and returns a list of tag instances
        [container_tag,tag,values, valid]. Defaults to the current container and a new list (neither arguments usually
        needs to be provided)

        Args:
            container (_Container) : The container to serialize. Defaults to the current container.
            tag_list (list[tags]) : List of gathered tags. Defaults to a new list.

        Returns:
            list[tags] : list of tag instances [container_tag,tag,values,valid]

        """

        if self._parent_app is None:
            raise RuntimeError(f"{self._parent_app=}. Not Set!")

        if tag_list is None:
            tag_list = []

        if container is None:
            container = self

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        for row_list in container.control_list_get:
            for col_control in row_list:
                if col_control is None:
                    continue

                if isinstance(col_control, _Container):
                    self.tags_gather(container=col_control, tag_list=tag_list)
                else:
                    if self._parent_app is not None and self._parent_app.widget_exist(
                        window_id=window_id,
                        container_tag=container.tag,
                        tag=col_control.tag,
                    ):
                        widget = self._parent_app.widget_get(
                            window_id=window_id,
                            container_tag=container.tag,
                            tag=col_control.tag,
                        )

                        if isinstance(widget, _Container):
                            self.tags_gather(container=widget, tag_list=tag_list)

                        if widget.buddy_control is not None and isinstance(
                            widget.buddy_control, _Container
                        ):
                            self.tags_gather(
                                container=widget.buddy_control, tag_list=tag_list
                            )
                        if widget is not None and isinstance(widget, _qtpyBase_Control):
                            tag_list.append(
                                tags(
                                    container_tag=container.tag,
                                    tag=col_control.tag,
                                    value=widget.value_get(),
                                    valid=widget.validate(),
                                )
                            )

        return tag_list

    def values_clear(self) -> None:
        """Clears the values of all widgets in the container that have a `clear` method"""

        window_id = Get_Window_ID(self._parent_app, self._parent, self)

        for item in self.tags_gather():
            widget = self._parent_app.widget_get(
                window_id=window_id, container_tag=item.container_tag, tag=item.tag
            )
            if hasattr(widget, "clear"):
                widget.clear()

    @property
    def values_get(self) -> list[tags]:
        """Wrapper function around tags gather, returns a tuple list [container_tag,tag,values] of all controls in
        the current container

        Returns:
            list[tags] : list of tag instances [container_tag,tag,values,valid]
        """
        return self.tags_gather()

    def snapshot_values(self, name: str = "") -> None:
        """Creates a named snapshot of all the controls that have values in a container (and its sub-containers)

        Args:
            name (str): Name of snapshot
        """
        self._snapshots = {}

        assert (
            isinstance(name, str) and name.strip() != ""
        ), f"{name=}. Must be a non-empty str"

        if name in self._snapshots:
            AssertionError(f"{name=} Already exists!")

        self._snapshots[name] = self.tags_gather()

    def snapshot_modified(self, snapshot1: str, snapshot2: str = "") -> bool:
        """Compares 2 snapshots to determine if a value has changed

        Args:
            snapshot1 (str): Name of source snapshot
            snapshot2 (str): Name of comparison snapshot (Optional: Defaults to current values)

        Returns:
            bool : True if a value has changed between snapshots

        """
        assert (
            isinstance(snapshot1, str) and snapshot1.strip() != ""
        ), f"{snapshot1=}. Must be a non-empty str"
        assert isinstance(snapshot2, str), f"{snapshot2=}. Must be str"

        assert snapshot1 in self._snapshots, f"{snapshot1=}, Does not exist!"

        if isinstance(snapshot2, str) and snapshot2.strip() != "":
            assert snapshot2 in self._snapshots, f"{snapshot2=}, Does not exist!"
            assert (
                snapshot1 != snapshot2
            ), f"{snapshot1=} must be different to {snapshot2=}"
            snap2 = self._snapshots[snapshot2]
        else:
            snap2 = self.tags_gather()

        snap1 = self._snapshots[snapshot1]

        for snap1_item in snap1:
            for snap2_item in snap2:
                if snap1_item.container_tag == snap2_item.container_tag:
                    if snap1_item.tag == snap2_item.tag:
                        if snap1_item.value != snap2_item.value:
                            return True

        return False

    def snapshot_modified_values(
        self, snapshot1: str, snapshot2: str = ""
    ) -> list[_Snapshot_Modified_Values]:
        """Compares 2 snapshots and returns a list of named tuples comprised of elements where the values have changed
        [snap1, snap2] each snap being a named tuple [container_tag,tag,values]

        Args:
            snapshot1 (str): Name of source snapshot
            snapshot2 (str): Name of comparison snapshot (Optional: Defaults to current values)

        Returns:
            list[_Snapshot_Modified_Values] : list of _Snapshot_Modified_Values instances [snap1, snap2]

        """
        modified_values = []

        assert (
            isinstance(snapshot1, str) and snapshot1.strip() != ""
        ), f"{snapshot1=}. Must be a non-empty str"
        assert isinstance(snapshot2, str), f"{snapshot2=}. Must be str"

        assert snapshot1 in self._snapshots, f"{snapshot1=}, Does not exist!"

        if snapshot2.strip() != "":
            assert snapshot2 in self._snapshots, f"{snapshot2=}, Does not exist!"
            assert (
                snapshot1 != snapshot2
            ), f"{snapshot1=} must be different to {snapshot2=}"
            snap2 = self._snapshots[snapshot2]
        else:
            snap2 = self.tags_gather()

        snap1 = self._snapshots[snapshot1]

        for snap1_item in snap1:
            for snap2_item in snap2:
                if snap1_item.container_tag == snap2_item.container_tag:
                    if snap1_item.tag == snap2_item.tag:
                        if snap1_item.value != snap2_item.value:
                            modified_values.append(
                                _Snapshot_Modified_Values(
                                    snap1_item,
                                    self.widget_get(
                                        container_tag=snap1_item.container_tag,
                                        tag=snap1_item.tag,
                                    ).validate(),
                                    snap2_item,
                                    self.widget_get(
                                        container_tag=snap2_item.container_tag,
                                        tag=snap2_item.tag,
                                    ).validate(),
                                )
                            )

        return modified_values

    @property
    def row_height_total(self) -> int:
        """Returns the total (summed)  of the maximum row height in the container

        Returns:
            int : The total (summed) of the maximum row height :

        """
        row_height_total = 0

        for row_list in self.control_list_get:
            row_height_max = 0

            for col_control in row_list:
                if col_control is None:
                    continue
                if isinstance(col_control, _Container):
                    if (
                        col_control.row_height_max > row_height_max
                    ):  # Might need recursion
                        row_height_max = col_control.row_height_max
                else:
                    if col_control.height > row_height_max:
                        row_height_max = col_control.height

            # if row_height_max > row_height_total:
            row_height_total += row_height_max

        return row_height_total

    @property
    def controls_across(self) -> int:
        """Returns the maximum number of controls across in a Container

        Returns:
            int: The number of controls:

        """
        return self._controls_across(self)

    def _controls_across(self, container: _qtpyBase_Control) -> int:
        """Returns the maximum number of controls across in a Container layout

        Args:
            container (_Container): The container control

        Returns:
            int : The maximum number of controls across in a Container

        """
        assert isinstance(
            container, _Container
        ), f"{_Container=}. Must be an instance of _Container type"
        ctrls_across = 0

        for row_list in container.control_list_get:
            ctrl_count = 0

            for col_control in row_list:
                if col_control is not None and not isinstance(col_control, Menu):
                    if isinstance(col_control, _Container):
                        ctrl_count += 1  # Still experimenting
                        # line_width = self._controls_across(col_control)
                    else:
                        ctrl_count += 1

            if ctrl_count > ctrls_across:
                ctrls_across = ctrl_count

        return ctrls_across

    @property
    def controls_down(self) -> int:
        """Returns the number of controls down in a Container layout

        Returns:
            (int): The number of controls down

        """
        return len(self._layout) - 1  # Menu is at 0,0

    @property
    def max_text_len(self) -> int:
        """THe maximum control text length in the Container controls

        Returns:
            (int): Maximum control text length

        """
        max_text_len = 0

        for row_list in self._layout:
            for col_control in row_list:
                if col_control is None or isinstance(col_control, Menu):
                    continue
                elif isinstance(col_control, _Container):
                    continue
                elif re.search(
                    "<(\"[^\"]*\"|'[^']*'|[^'\">])*>", col_control.text
                ) or re.search("<(\"[^\"]*\"|'[^']*'|[^'\">])*>", col_control.label):
                    # Ugly HTML Check, HTML not considered when calculating max text len
                    continue

                if hasattr(col_control, "label"):
                    if col_control.label == "":
                        txt_len = len(col_control.text)
                    else:
                        txt_len = len(col_control.label) + len(col_control.text)

                        if "&" in col_control.label:  # Ignore accelerator keys
                            txt_len = amper_length(col_control.label)
                            # txt_len -= 1
                else:
                    txt_len = len(col_control.text)

                if txt_len > max_text_len:
                    max_text_len = txt_len

        return max_text_len

    def print_container(
        self, container: _qtpyBase_Control = None, leader: str = "*"
    ) -> None:
        """Dumps the _Container structure to the command line.  Used for debugging

        Args:
            container (_qtpyBase_Control): _Container control that is being dumped. self by default
            leader (str): String that appears at the beginning of each dumpled line.
        """
        assert isinstance(leader, str), f"{leader=}. Must be a str"
        assert isinstance(
            container, (type(None), _Container)
        ), f"{_Container=}. Must be None or an instance of _Container"

        if container is None:  # Defaults to self
            container = self

        layout = container.control_list_get

        print(
            f"{leader}******************** Start _Container <{container.tag}> Dump"
            " *******************"
        )

        for row_index, row_line in enumerate(layout):
            if len(row_line) == 0:
                print(f"{row_index} EL")  # Empty Line
            else:
                for col_index, control in enumerate(row_line):
                    if isinstance(control, _Container):
                        print(f"> {leader} {row_index},{col_index} : {control}")

                        self.print_container(
                            container=control, leader=" " * len(leader) + leader
                        )
                    else:
                        print(f"> {leader} {row_index},{col_index} : {control}")

        print(
            f"{leader}*****************************************************************************"
        )
        print(
            f"{leader}******************** RHT <{container.row_height_total}> RHM"
            f" <{container.row_height_max}>            CA <{container.controls_across}>"
            f" CWT <{container.col_width_total}>             CWM"
            f" <{container.col_width_max}> *******************"
        )
        print(
            f"{leader}******************** End _Container <{container.tag}> Dump"
            " *******************"
        )


@dataclasses.dataclass
class Button(_qtpyBase_Control):
    """Instantiates a Button widget and associated properties"""

    txt_align: Align = Align.CENTER

    def __post_init__(self) -> None:
        """Initializes the button object."""
        super().__post_init__()

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates a Button widget.

        Args:
            parent_app (QtPyApp): The parent app.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag of the container that the widget is in.

        Returns:
            qtW.QWidget : The button widget
        """
        button_amper_length = amper_length(self.trans_str(self.text))

        if self.height <= 0:
            self.height = BUTTON_SIZE.height

        if self.width <= 0:
            self.width = BUTTON_SIZE.width

        self.width = max(self.width, button_amper_length)

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        # TODO Resizing Stuff
        # self._widget.setMinimumHeight(pixel_size.height + self.tune_vsize)
        # self._widget.setMinimumWidth(pixel_size.width + self.tune_hsize)
        # self._widget.setMaximumHeight(pixel_size.height + self.tune_vsize)
        # self._widget.setMaximumWidth(pixel_size.width + self.tune_hsize)

        return widget


@dataclasses.dataclass
class FormContainer(_Container):
    """Creates a`Form Container instance`"""

    def __post_init__(self) -> None:
        """Initialises the form container."""
        super().__post_init__()

    def add_control(
        self,
        control: _qtpyBase_Control,
        zero_based: bool = False,
    ) -> "FormContainer":
        """Adds a control to the form container.

        Args:
            control (_qtpyBase_Control): _qtpyBase_Control added to the form container.
            zero_based (bool): bool = False. Defaults to False

        Returns:
            FormContainer : The Form Container instance.
        """
        assert isinstance(
            control, _qtpyBase_Control
        ), f"{control=}. Must be an instance of _qtpyBase_Control"

        super().add_control(
            control=control, row=len(self._layout), col=1, zero_based=zero_based
        )

        return self


@dataclasses.dataclass
class GridContainer(_Container):
    """Creates a`Grid Container instance`"""

    def __post_init__(self) -> None:
        """Initialises the form container."""
        super().__post_init__()


class _Dialog(qtW.QDialog):
    """Provides the pop-up dialogue used in PopContainer and its descendants.
    Note: This class exists because QT 6.2.2 broke the multiple inheritance used in dataclass PopContainer.
    """

    def __init__(
        self,
        parent_app: QtPyApp,
        owner: "PopContainer",
        callback: Callable,
        container: _Container,
        container_tag: str,
        tag: str,
        title: str,
    ) -> None:
        """Sets up the dialogue box.

        Args:
            parent_app (QtPyApp): The parent application.
            owner ("PopContainer"): The PopContainer that owns this dialogue box.
            callback (Callable): This is the method that will be called when the user clicks the a dialogue button.
            container (_Container): The container that the dialogue box is being called from.
            container_tag (str): The tag name of the container that the dialogue box creates.
            tag (str): This is the tag name of the dialogue box container . It's used to identify the dialogue box.
            title (str): The title of the dialogue box
        """

        super().__init__()

        self.owner: PopContainer = owner
        self.callback: callable = callback
        self.container_tag: str = container_tag
        self.container: _Container = container
        self.tag: str = tag
        self.title: str = title
        self._parent_app: QtPyApp = parent_app
        self._result: str = ""

        assert isinstance(
            self.owner, PopContainer
        ), f"{self.owner=}. Must be instance of PopContainer"
        assert (
            isinstance(self.callback, Callable) or self.callback is None
        ), f"{self.callback=}. Must be func| method| lambda or None"
        assert (
            isinstance(self.container_tag, str) and self.container_tag.strip() != ""
        ), f"{self.container_tag=}. Must be non-empty str"
        assert (
            isinstance(self.tag, str) and self.tag.strip() != ""
        ), f"{self.tag=}. Must be non-empty str"
        assert isinstance(self.title, str), f"{self.title=}. Must be non-empty str"
        assert isinstance(
            self._parent_app, QtPyApp
        ), f"{self._parent_app=}. Must be instance of QtPyApp"

    def set_result(self, value: str) -> None:
        """Sets the return value of the PopContainer

        Args:
            value (str ):The value returned by the PopContainer (or descendant) instance
        """
        assert isinstance(value, str), f"{value} must be str"
        self._result = value

    def keyPressEvent(self, event: qtG.QKeyEvent) -> None:
        """Handles key presses to prevent the PopContainer being closed by anything other than a button

        Args:
            event (qtG.QKeyEvent): The event raised by a key press
        """
        if event.key() == qtC.Qt.Key_Escape:
            pass
        elif event.key() == qtC.Qt.Key_Alt & qtC.Qt.Key_F4:
            # Esc and Alt F4 should not close the dialog!
            event.ignore()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: qtG.QCloseEvent) -> None:
        """Performs close event processing when called.
        Overrides ancestor

        Args:
            event: The event raised by attempting to close the PopContainer or descendants
        """
        self._allow_close = True

        # event.accept()
        # return None

        if self.callback is not None:
            window_id = Get_Window_ID(self._parent_app, None, self)

            if self._parent_app.widget_exist(
                window_id=window_id,
                container_tag=self.container_tag,
                tag=self.container_tag,
            ):
                widget_dict = self._parent_app.widget_dict_get(
                    window_id,
                    container_tag=self.container_tag,
                )
            else:
                widget_dict = {}

            assert (
                self.callback.__code__.co_argcount <= 2
            ), "open callback has 1 argument - Action"

            if callable(self.callback):
                result = _Event_Handler(
                    parent_app=self._parent_app, parent=self.owner
                ).event(
                    window_id=window_id,
                    callback=self.callback,
                    action=Sys_Events.WINDOWCLOSED.name,
                    container_tag=self.container_tag,
                    tag=self.tag,
                    event=Sys_Events.WINDOWCLOSED,
                    value=None,
                    widget_dict=widget_dict,
                    control_name=self.__class__.__name__,
                    parent=self.owner,
                )

                if result == 1:  # Allow window to close
                    self.container.widgets_clear()

                    self.container.widget_del(
                        container_tag=self.container_tag, tag=self.tag
                    )

                    event.accept()
                else:
                    self._allow_close = False
                    event.ignore()

            else:
                self.container.widgets_clear()
                self.container.widget_del(
                    container_tag=self.container_tag,
                    tag=self.container_tag,
                )
                event.accept()
        else:
            self.container.widgets_clear()
            self.container.widget_del(
                container_tag=self.container_tag,
                tag=self.container_tag,
            )
            event.accept()

    def show(self) -> str:
        """Opens and displays the PopContainer or descendant and returns the selected value

        Returns (str) : The value set in the  _result variable

        """

        layout = qtW.QVBoxLayout()
        layout.setObjectName(self.container_tag)

        self.setModal(True)
        self.setWindowTitle(self.owner.trans_str(self.title))
        self.setWindowFlags(qtC.Qt.CustomizeWindowHint | qtC.Qt.WindowTitleHint)

        self._widget = self.container._create_widget(
            self._parent_app, self, self.container_tag
        )

        layout.addWidget(self._widget)

        self.setLayout(layout)

        self.setFixedSize(self._widget.minimumWidth(), self._widget.minimumHeight())

        if self.owner.open_sheet() == 1:
            self.exec()  # Blocks
            while g_application.app_get.processEvents():
                time.sleep(0.05)

        return self._result


@dataclasses.dataclass(slots=True)
class PopContainer(_qtpyBase_Control):
    """The class implements the parent of all dialog controls"""

    title: str = ""
    container: Optional[_Container] = None
    dialog: _Dialog = None
    parent_app: QtPyApp = None  # Changed to public 2023/03/05 because of a very occasional focus_out erroe

    # private instance variables
    _allow_close: bool = False
    _result: str = ""

    def __post_init__(self) -> None:
        """Configures the dialogue for use"""

        _qtpyBase_Control.__post_init__(self)

        if self.container_tag.strip() == "":
            self.container_tag = "pop_container_" + str(uuid.uuid1())
        if self.tag.strip() == "":
            self.tag = "pop_container_" + str(uuid.uuid1())

        assert isinstance(self.title, str), f"{self.title=}. Must be str"
        assert isinstance(
            self.container, (type(None), _Container)
        ), f"{self.container=}. Must be a container instance or None"

        if self.callback is None:
            self.callback = self.event_handler

        if self.container is None:
            self.container = GridContainer(tag=self.container_tag)

        assert g_application is not None, f"{g_application=} is bad"

        self.parent_app: QtPyApp = cast(QtPyApp, g_application)  # TODO avoid global!

        if self.height <= 0:
            self.height = 5

        if self.width <= 0:
            self.width = 20

        self.dialog: _Dialog = _Dialog(
            parent_app=self.parent_app,
            owner=self,
            callback=self.callback,
            container_tag=self.container_tag,
            container=self.container,
            title=self.title,
            tag=self.tag,
        )

        if (
            isinstance(self.parent_app.icon, str)
            and self.parent_app.icon.strip() != ""
            and pathlib.Path(App_Path(self.parent_app.icon)).exists()
        ):  # Try and load from file
            icon_image = qtG.QPixmap(App_Path(self.parent_app.icon)).scaledToWidth(256)  # type: ignore

            assert isinstance(
                icon_image, (qtG.QIcon, qtG.QPixmap)
            ), f"{self.parent_app.icon=} did not resolve to a QIcon or a QPixmap"

            self.dialog.setWindowIcon(icon_image)
        elif self.parent_app.icon is None or (
            isinstance(self.parent_app.icon, str) and self.parent_app.icon.strip() == ""
        ):
            pass
        elif isinstance(self.parent_app.icon, (qtG.QIcon, qtG.QPixmap)):
            self.dialog.setWindowIcon(self.parent_app.icon)
        else:
            raise AssertionError(
                f"{self.icon=} || <{type(self.icon)}> is not a file str or a QPixmap"
            )

    def close(self) -> bool:
        """Closes the dialog and sets the result to the value of the _result variable

        Returns:
            bool : Result of the close operation
        """
        window_id = Get_Window_ID(self.parent_app, None, self)

        self.parent_app.widget_del(
            window_id=window_id,
            container_tag=self.container_tag,
            tag=self.container_tag,
        )
        self.dialog._result = self._result

        return self.dialog.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Method called when the dialog is closed.

        Args:
            QCloseEvent: This is the event that is being passed to the function.
        """
        self.dialog.closeEvent(event)

    def event_handler(self, event: Action) -> int:
        """Processes the control events. Override this method to process the control events.

        Args:
            event (Action): The event that was triggered.

        Returns:
            int : 1 if the event was processed ok, -1 if not.
        """
        return 1

    def show(self) -> str:
        """Opens and displays the dialogue window and returns the result of using the dialogue as a string.

        Returns:
            str : The value set in the _result variable
        """
        return self.dialog.show()

    @property
    def allow_close(self) -> bool:
        """Gets the value of the allow close state of the dialogue .

        Returns:
            bool : True can close the dialog, False cannot close the dialog.
        """
        return self._allow_close

    @property
    def get_result(self) -> str:
        """Gets the result value stored in the _result variable .

        Returns:
            str : The value set in the _result variable
        """

        return self._result

    def set_result(self, result: str) -> None:
        """Sets the result of the dialogs operations into the _result variable.

        Args:
            result (str): The result of using the dialog.
        """
        assert isinstance(result, str), f"{result=}. Must be str!"

        self._result = result

    def open_sheet(self) -> int:
        """Opens the sheet and returns the result of attempting to open the sheet

        Returns:
            int : The result of the callback when an attempt is made to open the dialogue. 1 Ok, -1 if dialogue can not be
                opened.
        """
        result = 1

        if self.callback is not None:
            assert (
                self.callback.__code__.co_argcount <= 2
            ), "open callback has 1 argument - Action"

            handler = _Event_Handler(parent_app=self.parent_app, parent=self)

            window_id = Get_Window_ID(self.parent_app, None, self)

            if callable(self.callback):
                result = handler.event(
                    window_id=window_id,
                    callback=self.callback,
                    action=Sys_Events.WINDOWOPEN.name,
                    container_tag=self.container_tag,
                    tag=self.tag,
                    event=Sys_Events.WINDOWOPEN,
                    value=None,
                    widget_dict=self.parent_app.widget_dict_get(
                        window_id=window_id, container_tag=self.container_tag
                    ),
                    control_name=self.__class__.__name__,
                    parent=self,
                )

            if result == -1:
                self.dialog.close()

                return result

            if callable(self.callback):
                result = handler.event(
                    window_id=window_id,
                    callback=self.callback,
                    action=Sys_Events.WINDOWPOSTOPEN.name,
                    container_tag=self.container_tag,
                    tag=self.tag,
                    event=Sys_Events.WINDOWPOSTOPEN,
                    value=None,
                    widget_dict=self.parent_app.widget_dict_get(
                        window_id=window_id, container_tag=self.container_tag
                    ),
                    control_name=self.__class__.__name__,
                    parent=self,
                )

        return result

    # def keyPressEvent(self, event):  # Esc should not close dialog!
    #     if event.key() == qtC.Qt.Key_Escape:
    #         pass
    #     elif event.key() == qtC.Qt.Key_Alt & qtC.Qt.Key_F4:
    #         event.ignore()
    #     else:
    #         super().keyPressEvent(event)


@dataclasses.dataclass
class HBoxContainer(_Container):
    """A HBoxContainer is a container that lays out its children in a horizontal row. A subclass of _Container."""

    def __post_init__(self) -> None:
        """Constructor for the HBoxContainer that checks arguments and sets instance variables."""
        super().__post_init__()

    def add_control(
        self,
        control: _qtpyBase_Control,
        zero_based: bool = False,
    ) -> "HBoxContainer":
        """Adds a GUI control to the HBoxContainer

        Args:
            control (_qtpyBase_Control): Adds a sub-classed GUI control of the _qtpyBase_Control to the layout
            zero_based (bool): If True, the control will be added to the first row. If False, the control will be added to
            the second row. Defaults to False

        Returns:
            HBoxContainer : The HBoxContainer object.
        """
        assert isinstance(
            control, _qtpyBase_Control
        ), f"{control=}>. Must be an instance of _qtpyBase_Control"

        super().add_control(control=control, row=1, zero_based=zero_based)

        return self


@dataclasses.dataclass
class VBoxContainer(_Container):
    """A VBoxContainer is a container that lays out its children vertically. A subclass of _Container."""

    def __post_init__(self) -> None:
        super().__post_init__()

    def add_control(
        self,
        control: _qtpyBase_Control,
        zero_based: bool = False,
    ) -> "VBoxContainer":
        """Adds a GUI control to the VBoxContainer

        Args:
            control (_qtpyBase_Control): Adds a sub-classed GUI control of the _qtpyBase_Control to the layout
            zero_based (bool): If True, the first row will be 0. If False, the first row will be 1. Defaults to False

        Returns:
            VBoxContainer : The VBoxContainer instance.
        """
        assert isinstance(
            control, _qtpyBase_Control
        ), f"{control=}. Must be an instance of _qtpyBase_Control"

        super().add_control(
            control=control, row=len(self._layout), col=1, zero_based=zero_based
        )

        return self


@dataclasses.dataclass
class Checkbox(_qtpyBase_Control):
    """A Checkbox button that can be toggled on or off. A subclass of _qtpyBase_Control."""

    checked: bool = False
    # tristate:bool = False #Not enabled for now

    def __post_init__(self) -> None:
        """Constructor for the Checkbox that checks arguments and sets instance variables."""
        super().__post_init__()

        assert isinstance(self.checked, bool), f"{self.checked=}. Must be bool"
        # assert isinstance(self.tristate,bool),f"{self.tristate=}. Must be bool"
        # Need to make work with Qt.PartiallyChecked if enable tristate

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the checkbox widget

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): This is the tag name that will be used to identify the widget as belonging to a container.

        Returns:
            qtW.QWidget : The checkbox widget
        """
        if self.height == -1:
            self.height = CHECKBOX_SIZE.height

        if self.width == -1:
            self.width = CHECKBOX_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self.button_toggle(self.checked)

        return widget

    @property
    def button_checked(self) -> bool:
        """Returns the checked state of the checkbox.

        Returns:
            bool : The checked state ofthe checkbox.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QCheckBox
        return self._widget.isChecked()

    def button_toggle(self, value: bool = True) -> None:
        """Toggles the checkbox on or off.

        Args:
            value (bool): True checkbox is checked, False checkbox is unchecked. Defaults to True
        """

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(value, bool), f"{value=}. Must be bool"

        self._widget: qtW.QCheckBox
        self._widget.setChecked(value)

    @property
    def label_get(self) -> str:
        """Returns the label text of the checkbox.

        Returns:
            str: The text of the label.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")
        self._widget: qtW.QCheckBox
        return self._widget.text()

    def value_get(self) -> bool:
        """Returns the current state of the button

        Returns:
            bool : True checked, False not checked
        """

        return self.button_checked

    def value_set(self, value: bool) -> None:
        """Toggles the checkbox on or off.

        Args:
            value (bool): True checkbox is checked, False checkbox is unchecked.

        Returns:

        """
        assert isinstance(value, bool), f"{value=} must be bool"

        self.button_toggle(value)


@dataclasses.dataclass
class ComboBox(_qtpyBase_Control):
    """A ComboBox control that can be used to select a value from a list of options."""

    validate_callback: Optional[
        Union[types.FunctionType, types.MethodType, types.LambdaType]
    ] = None
    dropdown_width: int = 10
    items: Union[
        str,
        list[Combo_Item],
        tuple[Combo_Item, ...],
    ] = ()
    num_visible_items: int = 15
    display_na: bool = True
    parent_tag: str = ""

    @dataclasses.dataclass
    class _USER_DATA:
        data: any
        user_data: any

    @property
    def is_combo_child(self) -> bool:
        """Returns True if this combobox is a child of another combo box.


        Returns:
            bool: True if a child of another combo box. False if not.
        """
        if self.parent_tag.strip() == "":
            return False
        else:
            return True

    def __post_init__(self) -> None:
        """Constructor event that checks arguments and sets internal variables."""
        """Checks class parameter types"""
        super().__post_init__()

        assert self.validate_callback is None or callable(
            self.validate_callback
        ), f"{self.validate_callback=}. Must be None | Function | Method | Lambda"

        assert (
            isinstance(self.dropdown_width, int) and self.dropdown_width > 0
        ), f"{self.dropdown_width=}. Must be an int > 0"
        assert isinstance(
            self.items, (str, list, tuple)
        ), f"f{self.items=}. Must be a str, list or tuple eg.List[COMBO_ITEM,...]"

        if isinstance(self.items, (list, tuple)):
            item: Combo_Item

            for item in self.items:
                assert isinstance(
                    item, Combo_Item
                ), f"combo item {item} must be a COMBO_ITEM"

                item: Combo_Item

                assert isinstance(
                    item.display, str
                ), f"combo item {item.display=} must be str"
                assert isinstance(
                    item.data, (type(None), str, int, float, bool, bytes, list, tuple)
                ), (
                    f"combo item {item.data=} must be None | str | int | float | bool |"
                    " list | tuple"
                )

                assert isinstance(
                    item.icon,
                    (
                        type(None),
                        str,
                        qtG.QIcon,
                        qtG.QPixmap,
                    ),
                ), f"{item.icon=}. Must be None | str | QIcon | QPixmap"

        elif isinstance(self.items, str):
            if pathlib.Path(self.items).exists():
                pass
            else:
                raise RuntimeError(f"Dev Error File {self.items=} Does Not Exist")

        assert (
            isinstance(self.num_visible_items, int) and self.num_visible_items > 0
        ), f"{self.num_visible_items=}. Must be an int > 1"
        assert isinstance(self.display_na, bool), f"{self.display_na=}. Must be bool"

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates a ComboBox widget and loads it with the items specified in the `items` attribute - if provided

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag name for the widget in the parent container.

        Returns:
            QWidget : The widget is being returned.
        """

        self._widget: qtW.QComboBox

        if self.height == -1:
            self.height = 1  # COMBOBOX_SIZE.height

        if self.width == -1:
            self.width = COMBOBOX_SIZE.width + len(self.label) + 2

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget.setModel(qtG.QStandardItemModel())

        enabled = self.enable_get
        self.enable_set(True)

        if len(self.items) > 0:
            if isinstance(self.items, str):
                max_len = self.load_csv_file(self.items)
            else:
                max_len = self.load_items(items=self.items, auto_na=self.display_na)

            if max_len > 0:
                self._widget.view().setMinimumWidth(
                    self.pixel_char_size(char_height=1, char_width=max_len).width
                )

        self.enable_set(enabled)

        self._widget.setMaxVisibleItems(self.num_visible_items)

        return widget

    def display_width_set(self, display_width: int) -> None:
        """
        The function sets the width of the combobox to the width of the text plus the width of the arrow

        Args:
            display_width (int): The number of characters to display in the combobox
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(display_width, int) and display_width > 0
        ), f"{display_width=}. Must Be > 0"

        char_pixel_size = self.pixel_char_size(1, 1)

        self.display_width = (
            display_width + self.tune_hsize
        )  # + self.horizontal_pixel_fiddle

        self._widget.setFixedWidth(
            (display_width * char_pixel_size.width)
            + char_pixel_size.width  # One extra for the arrow
        )

    def icon_set(
        self, combo_index: int, icon: Union[str, qtG.QIcon, qtG.QPixmap]
    ) -> None:  # noqa LISKOV != good
        """Sets an icon at a given row in the combo box

        Args:
            combo_index (int): Row index in the combobox where the icon is to be placed
            icon (Union[str, qtG.QIcon, qtG.QPixmap]): A QPixmap, QIcon or the icon file name
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")
        self._widget: qtW.QComboBox

        assert (
            isinstance(combo_index, int) and 0 <= combo_index <= self._widget.count
        ), f"select_index ({combo_index=}) must be between 0 and {self._widget.count}"

        assert isinstance(
            icon, (str, qtG.QIcon, qtG.QPixmap)
        ), f"{icon=}. Must be str | QIcon | QPixmap"

        if isinstance(icon, str):
            assert qtC.QFile.exists(icon), icon + " : does not exist!"
        elif isinstance(icon, qtG.QPixmap):
            pass  # All Good
        elif isinstance(icon, qtG.QIcon):
            pass  # All Good
        else:
            raise AssertionError(f"{icon=}. Not a valid icon type")

        self._widget.setItemIcon(combo_index, qtG.QIcon(icon))

    def load_csv_file(
        self,
        file_name: str,
        select_text: str = "",
        text_index: int = 1,
        line_start: int = 1,
        data_index: int = 1,
        ignore_header: bool = True,
        delimiter: str = ",",
    ) -> int:
        """
        Loads a CSV file into the combobox

        Args:
            file_name (str) : Name of CSV file (can contain the path)
            select_text (str) : Text to select in combo-box after load
            text_index (int) : col in file to load into display (default: {1})
            line_start (int) : line in file to start loading from (default: {1})
            data_index (int) : col in file to load into user data (default: {1})
            ignore_header (bool) : Set True if the CSV file has a header row (default: {True})
            delimiter (str) : CSV field separator (default: {","})

        Returns:
            int: Length of maximum item
        """

        assert (
            isinstance(file_name, str) and file_name.strip() != ""
        ), f"{file_name=}. Must be a non-empty string"
        assert isinstance(select_text, str), f"f{select_text=}. Must be str"
        assert (
            isinstance(text_index, int) and text_index > 0
        ), f"{text_index=}. Must be int > 0"
        assert (
            isinstance(line_start, int) and line_start > 0
        ), f"{line_start=}. Must be int > 0"
        assert (
            isinstance(data_index, int) and data_index > 0
        ), f"{data_index=}. Must be int > 0"
        assert isinstance(ignore_header, bool), f"{ignore_header=}. Must be bool"
        assert (
            isinstance(delimiter, str) and len(delimiter) == 1
        ), f"{delimiter=} must be a single char"

        if select_text == "":
            select_text = self.text

        assert os.path.isfile(file_name) and os.access(
            file_name, os.R_OK
        ), f"File {file_name} doesn't exist or is not readable"

        line_list = []

        with open(file_name, "r") as csv_file:
            for line_no, line in enumerate(csv_file.readlines()):
                if line_no == 0 and ignore_header:
                    continue
                elif line_no + 1 < line_start:
                    continue

                line_split = line.strip().split(delimiter)
                col_count = len(line_split)

                if col_count < (text_index - 1) or col_count < (data_index - 1):
                    continue

                line_list.append(
                    Combo_Item(
                        display=line_split[text_index - 1],
                        data=line_split[data_index - 1],
                        icon=None,
                        user_data=None,
                    )
                )

        max_len = self.load_items(line_list)

        if select_text.strip() != "":
            self.select_text(select_text)

        return max_len

    @property
    def get_items(self) -> list[Combo_Data]:
        """Returns all the items in the combo_box

        :return:

        Returns:
            List[COMBO_DATA]: List of items in the combo box
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        assert isinstance(
            self._widget, qtW.QComboBox
        ), f"Dev Error {self._widget=} {type(self._widget)=} Must be qtW.QComboBox! "

        return [
            Combo_Data(
                display=self._widget.itemText(i),
                data=self._widget.itemData(i).data,
                user_data=self._widget.itemData(i).user_data,
                index=i,
            )
            for i in range(self._widget.count())
        ]

    def load_items(
        self,
        items: Union[
            str,
            list[Combo_Item],
            tuple[Combo_Item, ...],
        ] = (),
        clear_items: bool = True,
        auto_na: bool = True,
        na_string: str = "N/A",
    ) -> int:
        """Loads items into the combobox dropdown

        Args:
            items (Union[str,list[COMBO_ITEM],tuple[COMBO_ITEM, ...],]): The items placed in the combobox
            clear_items (bool): Clears the items from the combobox (default: {True})
            auto_na (bool): Puts na_str (Not Available) in combobox (default: {True})
            na_string (str): The "Not Available" string (default: {"N/A"})

        Returns: int
            Length of maximum item


        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        assert isinstance(
            items, (str, list, tuple)
        ), f"Items {items=} are a single string, or a list/tuple of COMBO_ITEM "

        if clear_items:
            self._widget.clear()

        max_len = 0

        if isinstance(items, str) and items.strip() != "":  # user_data is None:
            self._widget.addItem(items)
            return len(items)
        elif isinstance(items, (list, tuple)):
            if auto_na:  # Add N/A Not applicable to top of combo list
                self._widget.addItem(
                    na_string, self._USER_DATA(data="N/A", user_data=None)
                )

            for item in items:
                assert isinstance(item, Combo_Item), f"{item=}. Must be COMBO_ITEM"

                item: Combo_Item

                assert isinstance(item.display, str), f"{item.display=}.Must be str"
                assert isinstance(
                    item.data, (str, float, int, bytes, type(None), list, tuple)
                ), f"{item.data=}. Must be str|float|int|bytes|None|lst|tuple)"
                assert isinstance(
                    item.icon, (type(None), str, qtG.QIcon, qtG.QPixmap)
                ), f"{item.icon=}. Must be None| str | QIcon | QPixmap"

                display = self.trans_str(item.display)

                user_data = self._USER_DATA(data=item.data, user_data=item.user_data)

                if len(item.display) > max_len:
                    max_len = len(self.trans_str(item.display))
                if item.icon is None:
                    self._widget.addItem(display, userData=user_data)
                else:
                    if isinstance(item.icon, str):
                        assert qtC.QFile.exists(
                            item.icon
                        ), f" {item.icon=}. Does not exist!"

                    self._widget.addItem(qtG.QIcon(item.icon), display, user_data)

            return max_len
        else:
            AssertionError(f"{items=}. Must be list of str | list of COMBO_ITEM")

    def print_all_to_console(self) -> None:
        """Debug method - prints items to console"""
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        """Prints contents of combobox to the commandline. Used for debugging."""
        combo_items = [self._widget.itemText(i) for i in range(self._widget.count())]

        print(f"{combo_items=}")

    def select_index(self, select_index) -> None:
        """Scrolls to an index in the combobox and  sets the current index of the widget to the select_index argument

        Args:
            select_index (int): The index of the item to select.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        assert (
            isinstance(select_index, int) and 0 <= select_index <= self._widget.count()
        ), f"select_index <{select_index}> must be between 0 and {self._widget.count()}"

        self._widget.setCurrentIndex(select_index)

    def select_text(
        self,
        select_text: str,
        case_sensitive: bool = False,
        partial_match: bool = False,
    ) -> int:
        """Selects the text in the combobox.

        Args:
            select_text (str): The text to select.
            case_sensitive (bool): Whether to perform a case-sensitive match. Defaults to False.
            partial_match (bool): Whether to perform a partial text match. Defaults to False.

        Returns:
            int: The index of the selected text in the dropdown.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        assert (
            isinstance(select_text, str) and select_text.strip() != ""
        ), f"{select_text=}. Must be non-empty str"

        assert isinstance(case_sensitive, bool), f"{case_sensitive=}. Must be bool"
        assert isinstance(partial_match, bool), f"{partial_match=}. Must be bool"

        select_text = self.trans_str(select_text)

        match = qtC.Qt.MatchExactly

        if partial_match:
            match = qtC.Qt.MatchContains

        if case_sensitive:
            match = match | qtC.Qt.MatchCaseSensitive

        if case_sensitive or partial_match:
            text_index = self._widget.findText(select_text.strip(), match)
        else:
            text_index = self._widget.findText(select_text)

        if text_index >= 0:
            self._widget.setCurrentIndex(text_index)

        return text_index

    def value_get(self, index: int = -1) -> Combo_Data:
        """Gets the value displayed in the dropdown

        Returns
            COMBO_DATA : Current row if index = -1, Selected row if row > 0
        """

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set!")
        self._widget: qtW.QComboBox

        assert isinstance(index, int), f"{index=}. Must be int"

        assert index == -1 or (
            0 <= index <= self._widget.count()
        ), f"index <{index}> must be == -1 or >= 0 and <= {self._widget.count()}"

        if index == -1:  # Want current data
            item_data = self._widget.itemData(self._widget.currentIndex())

            if isinstance(item_data, self._USER_DATA):
                data = item_data.data
                user_data = item_data.user_data
            else:
                data = None
                user_data = None

            return Combo_Data(
                index=self._widget.currentIndex(),
                display=self._widget.currentText(),
                data=data,
                user_data=user_data,
            )
        else:  # Want data at index
            item_data = self._widget.itemData(index)

            if isinstance(item_data, self._USER_DATA):
                data = item_data.data
                user_data = item_data.user_data
            else:
                data = None
                user_data = None

            return Combo_Data(
                index=index,
                display=self._widget.itemText(index),
                data=data,
                user_data=user_data,
            )

    def value_remove(self, index: int) -> None:
        """Remove an item from the combobox a the given index.

        Args:
            index (int): The index of the item to remove.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        assert isinstance(index, int), f"{index=}. Must be int"

        assert index == -1 or (
            0 <= index <= self._widget.count()
        ), f"index <{index}> must be == -1 or >= 0 and <= {self._widget.count()}"

        self._widget.removeItem(index)

    def value_set(self, value: Union[str, Combo_Data]) -> None:  # noqa LISKOV != good
        """Sets a value in the dropdown and scrolls to that value. if COMBO_DATA index is -1 then data and display
        values must match for scroll to happen

        value (Union[str,COMBO_DATA]): COMBO_DATA - selected text or int - selected index
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QComboBox

        assert isinstance(
            value, (str, Combo_Data)
        ), f"value {value=}. Must be COMBO_DATA | str"

        if isinstance(value, Combo_Data):
            value: Combo_Data
            combo_value = value
        else:
            combo_value = Combo_Data(
                display=value, data=value, user_data=value, index=-1
            )

        combo_value: Combo_Data
        assert combo_value.index == -1 or (
            0 <= combo_value.index <= self._widget.count()
        ), (
            f"index <{combo_value.index}> must be == -1 or >= 0 and <="
            f" {self._widget.count()}"
        )

        if [
            combo_data
            for combo_data in self.get_items
            if combo_data.display == combo_value.display
        ]:  # If the display value is loaded then no need to set the value (exact match)
            self.select_text(select_text=combo_value.display)

            return None

        if combo_value.index >= 0:
            self.select_index(value.index)
            self._widget.setItemText(combo_value.index, self.trans_str(value.display))
            self._widget.setItemData(
                combo_value.index,
                self._USER_DATA(data=combo_value.data, user_data=combo_value.user_data),
            )
        else:
            self._widget.addItem(
                self.trans_str(combo_value.display),
                self._USER_DATA(data=combo_value.data, user_data=combo_value.user_data),
            )

            if combo_value.data == combo_value.display:
                self.select_text(combo_value.data)
            else:
                index = self._widget.count() - 1
                self._widget.setCurrentIndex(index)

        return None


class _calendar_widget(qtW.QCalendarWidget):
    """A subclass of the QCalendarWidget that overrides the setSelectedDate method to set the current page to the current
    date
    """

    def __init__(self, parent: "Dateedit") -> None:
        """Constructor for the calendar widget.

        Args:
            parent (Dateedit): The parent widget.
        """
        super().__init__()

        self._parent = parent

    def setSelectedDate(self, date: qtC.QDate) -> None:
        """Method that is called when the user clicks on a date in the calendar widget

        Args:
            date (qtC.QDate): The date that was clicked on.
        """
        date_tuple = self._parent.date_get(date_tuple=True)

        if date_tuple[0] == 100 and date_tuple[1] == 1 and date_tuple[2] == 1:
            # If the date is 1/1/100 (minimum date) then set the date to the current date
            default_date = qtC.QDate.currentDate().toString(self._parent.format)
        else:
            default_date = self._parent.date_get()

        # super().setSelectedDate(qtC.QDate.fromString(default_date,self._parent.format))
        the_date = qtC.QDate.fromString(default_date, self._parent.format)
        self.setCurrentPage(the_date.year(), the_date.month())


class SimpleDateValidator(qtG.QValidator):
    """A validator that ensures that the text in the line edit is a valid date, and that the date is greater than
    1/1/100 (the minimum date).
    """

    def validate(self, text, pos):
        if not text:
            # print(f"A OK,{self.parent().format()=}")
            return qtG.QValidator.Acceptable, text, pos
        fmt = self.parent().format()
        _sep = set(fmt.replace("y", "").replace("M", "").replace("d", ""))
        for l in text:
            # ensure that the typed text is either a digit or a separator
            if not l.isdigit() and l not in _sep:
                # print("B Stuffed")
                return qtG.QValidator.Invalid, text, pos
        years = fmt.count("y")
        if len(text) <= years and text.isdigit():
            # print("C Ok")
            return self.qtG.QValidator.Acceptable, text, pos
        if qtC.QDate.fromString(text, fmt).isValid() and qtC.QDate.fromString(
            text, fmt
        ) > qtC.QDate(1, 1, 1):
            return qtG.QValidator.Acceptable, text, pos
        # print("e inter")
        return qtG.QValidator.Intermediate, text, pos


class _Custom_Dateedit(qtW.QWidget):
    """A custom date edit widget that allows the user to select a date using a calendar widget that pops up when the
    user clicks the down arrow.
    """

    # Gets the date format for the country that the user is in.
    _date_format: str = country_date_formatmask(
        qtC.QLocale().system().name().split("_")[1]
    )[0]

    min_date = qtC.QDate(1, 1, 100)  # qtC.QDate(100, 1, 1)

    def __init__(self, parent: qtW.QWidget = None) -> None:
        """Constructor for the custom date edit widget that validates arguments and sets instance variables.
            Sets the input mask for the lineEdit widget to the mask returned by the get_mask() function

        Args:
            parent (qtW.QWidget): The parent widget of the custom date edit widget.
        """
        self.init_done = False
        super().__init__(parent)

        self.setSizePolicy(qtW.QSizePolicy.Preferred, qtW.QSizePolicy.Fixed)

        layout = qtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.lineEdit = qtW.QLineEdit()
        layout.addWidget(self.lineEdit)
        self.lineEdit.setMaxLength(len(self.format()))
        self.validator = SimpleDateValidator(self)
        self.lineEdit.setValidator(self.validator)

        self.dropDownButton = qtW.QToolButton()
        layout.addWidget(self.dropDownButton)
        self.dropDownButton.setIcon(self.style().standardIcon(qtW.QStyle.SP_ArrowDown))
        self.dropDownButton.setMaximumHeight(self.lineEdit.sizeHint().height())
        self.dropDownButton.setCheckable(True)
        self.dropDownButton.setFocusPolicy(qtC.Qt.NoFocus)

        self.calendar = qtW.QCalendarWidget()
        self.calendar.setWindowFlags(qtC.Qt.Popup)
        self.calendar.installEventFilter(self)

        self.dropDownButton.pressed.connect(self.showPopup)
        self.dropDownButton.released.connect(self.calendar.hide)
        self.lineEdit.editingFinished.connect(self.editingFinished)
        self.calendar.clicked.connect(self.setDate)
        self.calendar.activated.connect(self.setDate)

        self.lineEdit.setInputMask(self.get_mask())

    def clear(self) -> None:
        """Clears the text in the lineEdit widget"""
        self.lineEdit.clear()
        self.lineEdit.setText("")

    def editingFinished(self) -> None:
        # Clears the text if the date is not valid when losing focus this will only work if *NO* validator is set
        if self.calendar.isVisible():
            return None
        if not self.isValid():
            self.lineEdit.setText("")

    def format(self) -> str:
        """Returns the date format of the object

        Returns:
            str: The date format.
        """
        return self._date_format

    def setFormat(self, format: str) -> None:
        """Takes a date format string and sets the date format and edit mask for the date picker

        Args:
            format (str): The date format string.
        """
        assert isinstance(
            format, str
        ), f"{format=}. Must a non-empty str and a valid date format"

        date_format = country_date_formatmask(format)[0]
        edit_mask = country_date_formatmask(format)[1]

        self._date_format = date_format
        # self.setDate(self.calendar.selectedDate())
        self.calendar.hide()
        self.lineEdit.setMaxLength(len(edit_mask))
        # self.validator.setFormat(date_format)

        self.lineEdit.setInputMask(edit_mask)

    def get_mask(self) -> str:
        """Returns a mask string that can be used to validate the date format

        Returns:
            str : The mask for the date format.
        """
        return country_date_formatmask(self._date_format)[1]

    def text(self) -> str:
        """Returns the text in the date widget

        Returns:
            str : The date text in the lineEdit.
        """
        return self.lineEdit.text()

    def date(self) -> qtC.QDate:
        """If a date is valid, return it, otherwise return the minimum date

        Returns:
            qtC.QDate : The date.
        """

        if not self.isValid():
            return self.min_date

        date = qtC.QDate.fromString(self.text(), self.format())

        if date.isValid():
            return date

        return qtC.QDate.fromString(self.text(), self.format())

    def setDate(self, date: qtC.QDate) -> None:
        """Sets the date of the calendar widget to the date passed in

        Args:
            date (qtC.QDate): The date to be set.
        """
        assert isinstance(date, qtC.QDate), f"{date=}. Must be QDate"

        if self.init_done:
            self.lineEdit.setText(date.toString(self.format()))
        else:
            self.init_done = True

        self.calendar.setSelectedDate(date)
        self.calendar.hide()

    def setDateRange(self, min: qtC.QDate, max: qtC.QDate) -> None:
        """Sets a valid date range for the calendar.

        Args:
            min (QDate): Minimum date.. > 01/01/100
            max (QDate): Maximum date
        """
        assert isinstance(min, qtC.QDate), f"{min=}. Must be QDate"
        assert isinstance(max, qtC.QDate), f"{max=}. Must be QDate"

        self.calendar.setDateRange(min, max)

    def setMinimumDate(self, min: qtC.QDate) -> None:
        """Sets the minimum date for the date picker

        Args:
            min (qtC.QDate): The minimum date that can be selected.
        """
        assert isinstance(min, qtC.QDate), f"{min=}. Must be QDate"
        self.min_date = min

    def minimumDate(self) -> qtC.QDate:
        """Returns the minimum date for the date picker

        Returns:
            qtC.QDate : The minimum date.
        """
        return self.min_date

    def isValid(self) -> bool:
        """Checks if the text is a valid date.
            - If the text is a valid date, set the date to that date. If the text is a valid year, return True.
            Otherwise, clear the text and return False

        Returns:
            bool: True - date is valid, False - date is not valid.
        """
        text = self.text()
        if not text:
            self.clear()
            return False
        date = qtC.QDate.fromString(text, self.format())
        if date.isValid():
            self.setDate(date)
            return True
        try:
            year = int(text)
            start = self.calendar.minimumDate().year()
            end = self.calendar.maximumDate().year()
            if start <= year <= end:
                return True
        except:
            pass
        self.clear()
        return False

    def hidePopup(self) -> None:
        """Hides the calendar widget when the user clicks on the calendar icon"""
        self.calendar.hide()

    def showPopup(self) -> None:
        """Shows the calendar widget when the user clicks on the calendar icon"""
        pos = self.lineEdit.mapToGlobal(self.lineEdit.rect().bottomLeft())
        pos += qtC.QPoint(0, 1)
        rect = qtC.QRect(pos, self.calendar.sizeHint())
        self.calendar.setGeometry(rect)
        self.calendar.show()
        self.calendar.setFocus()

    def eventFilter(self, source: qtW.QWidget, event: qtC.QEvent) -> bool:
        """Event filter for the calendar widget.
        The eventFilter function is called when the calendar is shown or hidden

        Args:
            source (QWidget): The object that the event is being sent to.
            event (QEvent): The event that was triggered.

        Returns:
            bool : True - event was handled, False - event was not handled.
        """
        # press or release the button when the calendar is shown/hidden
        if event.type() == qtC.QEvent.Hide:
            self.dropDownButton.setDown(False)
        elif event.type() == qtC.QEvent.Show:
            self.dropDownButton.setDown(True)
        return super().eventFilter(source, event)

    def keyPressEvent(self, event: qtC.QEvent) -> None:
        """Processes key press events for the date picker.
            - If the user presses the down arrow or F4, the calendar will pop up. If the user presses the delete or
            backspace key,the date will be cleared

        Args:
            event (QEvent): The event that was triggered.
        """
        if event.key() in (qtC.Qt.Key_Down, qtC.Qt.Key_F4):
            if not self.calendar.isVisible():
                self.showPopup()
        elif event.key() in (qtC.Qt.Key_Delete, qtC.Qt.Key_Backspace):
            self.clear()

        super().keyPressEvent(event)


@dataclasses.dataclass
class Dateedit(_qtpyBase_Control):
    """A Dateedit widget that displays a date in a specified format."""

    label: str = "&"
    date: str = ""
    format: str = ""  # "yyyy-MM-dd"
    min_date: str = ""
    max_date: str = ""

    MINDATE = qtC.QDate(100, 1, 1)
    NODATE = qtC.QDate(1, 1, 1)

    def __post_init__(self) -> None:
        """Constructor for the Dateedit control that validates arguments and sets instance variables.

        - The function checks the `format` and `date` properties of the `DatePicker` class.
        - If the `format` property is empty, the function sets the `format` property to the current locale's date format.
        - If the `date` property is empty, the function sets the `date` property to the current date.
        - The function then checks the `min_date` and `max_date` properties of the `DatePicker` class.
        - If the `min_date` property is empty, the function sets the `min_date` property to the minimum date allowed by
            the DatePicker` class.
        - If the `max_date` property is empty, the function sets the `max_date` property to the current date.
        """
        super().__post_init__()

        if self.format.strip() == "":
            curr_locale = qtC.QLocale().system().name().split("_")[1]
            # print(f"@@#@#@# {self.date_format=} {curr_locale}")
            self.format = country_date_formatmask(curr_locale)[0]

        self._edit_mask = country_date_formatmask(self.format)[1]

        if self.date.strip() == "":
            self.date = qtC.QDate.currentDate().toString(self.format)

        assert isinstance(
            self.min_date, str
        ), f"{self.min_date=}. Must be str that matches {self.format=}"
        assert isinstance(
            self.max_date, str
        ), f"{self.max_date=}. Must be str that matches {self.format=}"

        if self.min_date.strip() == "":
            self.min_date = self.MINDATE.toString(self.format)

        if self.max_date.strip() == "":
            self.max_date = qtC.QDate.currentDate().toString(self.format)

        date_check = qtC.QDate.fromString(self.date, self.format)

        assert (
            date_check.isValid()
        ), f"Date <{self.date}> or Format <{self.format}> is not valid"

        date_check = qtC.QDate.fromString(self.min_date, self.format)

        assert (
            date_check.isValid()
        ), f"Date <{self.min_date}> or Format <{self.format}> is not valid"

        date_check = qtC.QDate.fromString(self.max_date, self.format)

        assert (
            date_check.isValid()
        ), f"Date <{self.max_date}> or Format <{self.format}> is not valid"

        assert qtC.QDate.fromString(self.min_date, self.format) >= self.MINDATE, (
            f"{qtC.QDate.fromString(self.min_date, self.format)=}. Must be >"
            f" {self.MINDATE=}"
        )

        if self.width == -1:
            self.width = len(self.format)
        self.width += 3  # set 3 extra chars for dropdown arrow

        # Buddy checks are in super...bypassed here
        buddy_button = Button(
            tag="derase_" + str(uuid.uuid1()),
            width=2,
            height=1,
            tooltip=f"{self.trans_str('Erase')} {SDELIM}{self.text}{SDELIM}",
            icon=App_Path("backspace.svg"),  # qta.icon("mdi.backspace"),
            txt_font=self.txt_font,
            callback=self._event_handler,  # if self.buddy_callback is None else self.buddy_callback
        )

        if self.buddy_control is None:
            self.buddy_control = buddy_button
        else:
            buddy_control = HBoxContainer(tag=f"bdctrl_{self.tag}")
            buddy_control.add_control(buddy_button)
            buddy_control.add_control(self.buddy_control)
            self.buddy_control = buddy_control

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the dateedit widget.

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): str = ""

        Returns:
            QWidget : The returned widget is actually a QDateEdit or a frame containing it.
        """
        if self.height == -1:
            self.height = WIDGET_SIZE.height  # COMBOBOX_SIZE.height

        if self.width == -1:
            self.width = WIDGET_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Custom_Dateedit
        self._widget.setFormat(self.format)
        self._widget.setDateRange(
            qtC.QDate.fromString(self.min_date, self.format),
            qtC.QDate.fromString(self.max_date, self.format),
        )
        self.line_edit: qtW.QLineEdit = cast(
            qtW.QLineEdit, self._widget.findChild(qtW.QLineEdit)
        )

        self.date_set(self.date, self.format)

        return widget

    def _event_handler(
        self,
        *args,
    ) -> int:
        """Event handler for the dateedit widget.

        Returns:
            int : 1 is OK, -1 is a problem
        """

        event = cast(Action, args[0])  # type: Action

        if event.event == Sys_Events.CLICKED:
            # print(f'{event.tag=} {event.tag.startswith("derase_")}')
            if event.tag.startswith("derase_"):
                self.clear()
        elif event.event == Sys_Events.FOCUSIN:
            pass
        elif event.event == Sys_Events.FOCUSOUT:
            date_widget: _Custom_Dateedit = self._widget

            if date_widget.date() < self.MINDATE:
                self.clear()
                date_widget.setFocus()

                return -1

            # Part of hack to clear displayed date
            # if self.guiwidget_get.date() == self.guiwidget_get.minimumDate():
            #    # minimumdate matching "100,1,1" (Object default)  means first use!
            # also means can not use 100,1,1 as a system date - what are the odds?
            #    if self.guiwidget_get.minimumDate() == qtC.QDate(100, 1, 1):
            #        self.date_set(date_format=self.date_format)
        elif event.event == Sys_Events.POPCAL:
            self._calandar_activated(event)

        if callable(self.callback):
            handler = _Event_Handler(parent_app=self.parent_app, parent=self)

            window_id = Get_Window_ID(self.parent_app, self.parent, self)

            return handler.event(
                window_id=window_id,
                callback=self.callback,
                action=event.event.name,
                container_tag=self.container_tag,
                tag=self.tag,
                event=event.event,
                value=self.value_get(date_tuple=True),
                widget_dict=self.parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.container_tag
                ),
                control_name=self.__class__.__name__,
                parent=self.parent_app.widget_get(
                    window_id=window_id, container_tag=self.container_tag, tag=self.tag
                ),
            )
        else:
            return 1

    def _calandar_activated(self, event: Action) -> int:
        """Processes calendar activated events
        Args:
            event (Action): The event that was triggered.

        Returns:
            int : 1 - OK
        """
        date = self._widget.date()
        date_text = self.line_edit.text()

        # print(f"A>>>>>>>>>>>>>>>>>>>>>@@@@@@@@@@@@@@ {date=}")

        if date == self.MINDATE:
            default_date = qtC.QDate.fromString(date_text, self.format)

            if not default_date.isValid():
                default_date = qtC.QDate.currentDate()

            # self._widget.calendarWidget().setCurrentPage(default_date.year(),default_date.month())
            # self._widget.setSpecialValueText("N/A")

            # cal = _calendar_widget(self)
            # cal.setSelectedDate(default_date)

            # self._widget.calendarWidget().setSelectedDate(default_date)

            # print(f"B>>>>>>>>>>>>>>>>>>>>>@@@@@@@@@@@@@@ {default_date=}")
            # self._widget.calendarWidget().setFirstDayOfWeek(qtC.Qt.DayOfWeek.Wednesday)
            # self._widget.calendarWidget().updateCell(default_date)
            # self._widget.calendarWidget().setCurrentPage(default_date.year(), default_date.month())
            # self._widget.calendarWidget().showToday()
            # self._widget.setSelectedDay(default_date)

            # self._widget.setSpecialValueText("N/A")

            # self._widget.setCalendarWidget(cal)

            # self.line_edit.setText("")
            # self.clear()
        return 1

    def clear(self, default_text: str = "-") -> None:
        """Clears the date displayed  - has to use a nasty hack to clear the date.
            If default_text = "-" then nothing is displayed in the date edit.
            otherwise the default text is displayed in the date edit

        Args:

        default_text (str): Text to place in edit control (must be a valid date string 0r -) (default: {-})

        """

        # Part of hack to clear displayed date as clear does not do the trick
        assert isinstance(default_text, str), f"{default_text=}. Must be str "

        if self.allow_clear:
            self._widget.clear()

        # if default_text == "":
        #    default_text = self.trans_str("N/A")
        # if default_text == "-":
        #    default_text = " "
        # else:
        #    default_text = self.trans_str(default_text)

        # self._widget.setDate(self._widget.minimumDate())

        # self._widget.setSpecialValueText(default_text)

        # Part of hack - means can not use 100,1,1 as a system date
        # self._widget.setMinimumDate(self._min_date)

    @overload
    def date_get(self, date_format: str = "", date_tuple: bool = False) -> str:
        ...

    @overload
    def date_get(self, date_format: str = "", date_tuple: bool = False) -> tuple:
        ...

    def date_get(
        self, date_format: str = "", date_tuple: bool = False
    ) -> str | _Date_Tuple:
        """Gets the date
                If date_format = "" then date is returned as a string formated as control_def date_format
                If date_format = "" and control_def date_format = "" then date is returned as string formatted
                as a system shortformat

                If date_tuple is True date is returned as a tuple(year,month,day)

        date_format(str): Format to return date as (default: {""})
        date_tuple (bool): Return date as tuple (default: {False})

        Returns:
            Union[str,_Date_Tuple]: Date formatted as string or tuple
        """

        date: qtC.QDate = self._widget.date()

        if date == self.NODATE:
            if date_tuple:
                return _Date_Tuple(
                    self.NODATE.year(), self.NODATE.month(), self.NODATE.day()
                )
            else:
                return ""

        if date_tuple:
            return _Date_Tuple(date.year(), date.month(), date.day())

        if self.format.strip() == "" and date_format.strip == "":
            date_format = qtC.QLocale.system().dateFormat(
                qtC.QLocale.system().ShortFormat
            )
        elif date_format.strip() == "":
            format = self.format

        return date.toString(date_format)

    def date_set(self, date: str = "", date_format: str = "", default_text: str = "-"):
        """Sets the date in the control.

        Args:
            date (str): A string representing the date to set, formatted as 'y-m-d'.
            date_format (str): The format of the date string, defaults to an empty string.
            default_text (str): The default text to use if the date string is empty or equals '-'.

        Returns:
            None.
        """
        assert isinstance(date, str), f"date <{date}> must be a non-empty string"
        assert isinstance(
            date_format, str
        ), f"date_format <{date_format}> must be a str"
        assert isinstance(
            default_text, str
        ), f"default_text <{default_text}> must be a str"

        date = date.strip(SDELIM)  # No Translation Happens Here

        if date == "-":
            self.clear(default_text=default_text)
        else:
            if date.strip() == "":
                # date = str(datetime.date.today())
                date = qtC.QDate.currentDate().toString(self.format)

            if date_format.strip() == "":
                date_format = qtC.QLocale.system().dateFormat(
                    qtC.QLocale.system().ShortFormat
                )

            # Follwing does not work in all envs
            actual_date = qtC.QDate.fromString(date, date_format)

            # so had to use hard coded date date_format y-m-d delimited by -
            # date_ele = date.split("-")
            # print(f"{date_ele=}")
            # actual_date = qtC.QDate(
            #    int(date_ele[0]), int(date_ele[1]), int(date_ele[2])
            # )

            assert actual_date.isValid(), (
                f"Date <{date}> Or Format <{format}> is not valid! Converted Date Is"
                f" <{actual_date}>"
            )

            self._widget.setDate(actual_date)

    def date_valid(self, date: str, date_format: str) -> bool:
        """Checks if a date is valid

        Args:
            date (str): date in str format
            date_format (str): The format of the date string.

        Returns:
            bool : True if date is valid, False otherwise
        """
        assert (
            isinstance(date, str) and date.strip() != ""
        ), f"{date=}. Must be a non-empty string"
        assert (
            isinstance(date_format, str) and date_format.strip() != ""
        ), f"{date_format=}. Must be a non-empty str"

        date = date.strip(SDELIM)  # No Translation Happens Here

        return qtC.QDate.fromString(date, date_format).isValid()

    @overload
    def value_get(self, date_format: str = "", date_tuple: bool = False) -> str:
        ...

    @overload
    def value_get(self, date_format: str = "", date_tuple: bool = False) -> tuple:
        ...

    def value_get(self, date_format: str = "", date_tuple: bool = False) -> str | tuple:
        """Gets the date

        Args:
            date_format (str): date format as str
            date_tuple (bool): If True, returns a tuple of (year, month, day). Defaults to False

        Returns:
            str | tuple : The date as a str formatted according to date format or a tuple of (year, month, day)
        """

        return self.date_get(date_format, date_tuple)

    def value_set(
        self, date: str, date_format: str = ""
    ) -> None:  # noqa LISKOV != good
        """Sets the date

        Args:
            date (str): date in str format
            date_format (str): date format as str

        Returns:
            None
        """
        return self.date_set(date, date_format)


@dataclasses.dataclass(init=True)
class FolderView(_qtpyBase_Control):
    """FolderView is a widget that displays a folder path in a tree format"""

    width: int = 40  # In Chars
    height: int = 15  # In  lines
    txt_align: Align = Align.LEFT
    widget_align: Align = Align.LEFT
    root_dir: str = "\\"
    dir_only: bool = False
    multiselect: bool = False
    header_widths: Union[list, tuple] = (40,)  # Column widths in char
    header_font: Optional[Font] = None
    click_expand: bool = False

    def __post_init__(self) -> None:
        """Constructor event that validates arguments and sets instance variables"""
        super().__post_init__()

        assert isinstance(self.width, int), f"{self.width=}. Must beint"
        assert isinstance(self.height, int), f"{self.height=}. Must be int"
        assert isinstance(self.txt_align, Align), f"{self.txt_align=}. Must be ALIGN"
        assert isinstance(
            self.widget_align, Align
        ), f"{self.widget_align=}. Must be ALIGN"
        assert (
            isinstance(self.root_dir, str) and self.root_dir.strip() != ""
        ), f"{self.root_dir=}. Must be a non-empty str"
        assert isinstance(self.dir_only, bool), f"{self.dir_only=}. Must be bool"
        assert isinstance(self.multiselect, bool), f"{self.multiselect=}. Must be bool"

        # Name, Type, Size and Modified are the four mandatory columns. If dir_only size s ignored
        num_cols = 3 if self.dir_only else 4

        assert (
            isinstance(self.header_widths, (list, tuple))
            and len(self.header_widths) <= num_cols
        ), (
            f"{self.header_widths=}. Must be a list or tuple with a max of"
            f" {num_cols=} widths set"
        )

        for index, width in enumerate(self.header_widths):
            assert isinstance(width, int), f"header_widths->{width=}. Must be an int"

        # Default to 20 chars wide for the missing mandatory cols
        header_widths = list(self.header_widths)

        col_index = 0
        # Still have to have  4 cols as size is hidden when control is instantiated
        for index in range(len(header_widths), 4):
            # Size lives in col 2
            if self.dir_only and index == 2:
                col_index += 1
                header_widths.append(20)

            header_widths.append(20)

        self.header_widths = header_widths

        assert self.header_font is None or isinstance(
            self.header_font, Font
        ), f"{self.header_font=}. Must be Font"
        assert isinstance(
            self.click_expand, bool
        ), f"{self.click_expand=}. Must be bool"

        if self.header_font is None:
            self.header_font = Font()

        self._Value = None

    class DirView_Model(qtW.QFileSystemModel):
        """QFileSystemModel subclass that overrides the headerData method to return the translated text headings"""

        def __init__(self, parent_widget: qtW.QWidget, trans_text: tuple):
            """Initializes the file system model.

            Args:
                parent_widget (QWidget): The parent widget.
                trans_text (tuple): The tuple of translated text strings.

            Returns:
                None
            """
            self.trans_text = trans_text
            qtW.QFileSystemModel.__init__(self, parent_widget)

        def headerData(
            self,
            section: int,
            orientation: Union[qtC.Qt.Horizontal, qtC.Qt.Vertical],
            role: qtC.Qt.ItemDataRole,
        ):
            """
            If the orientation is horizontal and the role is display, then return the appropriate translated header text

            Args:
                section (int): The column number.
                orientation (Union[qtC.Qt.Horizontal , qtC.Qt.Vertical]): Qt.Horizontal or Qt.Vertical header
                role (ItemDataRole): The role is used to indicate what kind of data is being requested.

            Returns:
                The header data for the model.
            """
            if orientation == qtC.Qt.Horizontal and role == qtC.Qt.DisplayRole:
                match section:
                    case 0:
                        result = self.trans_text[0]  # File/Folder Name
                    case 1:
                        result = self.trans_text[1]  # Size
                    case 2:
                        result = self.trans_text[2]  # Type
                    case 3:
                        result = self.trans_text[3]  # Date Modified
                    case _:
                        result = None
            else:
                result = super(qtW.QFileSystemModel, self).headerData(
                    section, orientation, role
                )
            return result

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """
        The function creates a file QTreeView widget, sets the model, sets the root directory, sets the column
        widths, sets the header alignment, sets the header font, sets the minimum width and height, and sets the
        widget to not expand on double click

        Args:
            parent_app (QtPyApp): The parent application object.
            parent (qtW.QWidget): The parent widget of the widget being created.
            container_tag (str): str = ""

        Returns:
            qtW.QWidget : The configured file treeview widget.
        """
        if self.height == -1:
            self.height = WIDGET_SIZE.height

        if self.width == -1:
            self.width = WIDGET_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        trans_text = (
            self.trans_str("Name"),
            self.trans_str("Size"),
            self.trans_str("Type"),
            self.trans_str("Modified"),
        )

        self.file_model = self.DirView_Model(widget, trans_text)

        if self.dir_only:
            self.file_model.setFilter(qtC.QDir.AllDirs | qtC.QDir.NoDotAndDotDot)

        if self._widget is None:
            print(f"{self._widget=}. Not Set")
            sys.exit(1)

        self._widget: qtW.QTreeView  # Type hinting

        self._widget.setModel(self.file_model)

        # tran_str is here in case any no trans delimiters have been placed around root dir
        self._widget.setRootIndex(self.file_model.index(self.trans_str(self.root_dir)))
        self._widget.setAnimated(False)
        self._widget.setIndentation(20)
        self._widget.setSortingEnabled(True)

        self._widget.setWindowTitle(self.text)

        if self.multiselect:
            self._widget.setSelectionMode(
                # SingleSelection
                qtW.QAbstractItemView.ExtendedSelection
            )
        else:
            self._widget.setSelectionMode(qtW.QAbstractItemView.SingleSelection)

        pixel_size = self.pixel_char_size(char_height=1, char_width=1)

        for index, width in enumerate(self.header_widths):
            self._widget.setColumnWidth(index, round(width * pixel_size.width) + 10)

        if self.dir_only:  # Hide Size column
            self._widget.hideColumn(1)

        width = 0

        for col_index in range(0, self.file_model.columnCount()):
            width += self._widget.columnWidth(col_index)

        self._widget.header().setDefaultAlignment(Align.CENTER.value)

        self.font_set(
            self.header_font, widget_font=self.header_font, widget=self._widget.header()
        )

        # TODO: Implment background colour settings and altenaterow highlighting - code below works
        # self.guiwidget_get.setAlternatingRowColors(True)
        # style = "QTreeView{alternate-background-color: wheat; background: powderblue;}"
        # self.guiwidget_get.setStyleSheet(style)

        self._widget.setMinimumWidth(width + self.tune_hsize)
        self._widget.setMinimumHeight(self.height * pixel_size.height + self.tune_vsize)

        self._widget.setExpandsOnDoubleClick(False)

        # tran_str is here in case any no trans delimiters have been placed around root dir
        root_index = self.file_model.setRootPath(self.trans_str(self.root_dir))
        self._widget.setRootIndex(root_index)

        return widget

    def _event_handler(self, *args) -> int:
        """Event handler for file view events.

        Args:
            *args: Default args for the event handler processing treeview events.

        Returns:
            int: 1. If the event is accepted, -1. If the event is rejected.

        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")
        self._widget: qtW.QTreeWidget

        event: Sys_Events = args[0]

        if len(args) > 1 and len(args[1]) > 0:
            selected_index = args[1][0]  # It is a tuple

            selected_node = namedtuple(
                "selected_node", "name, path, size, modified, date_modified type, isdir"
            )

            if self.click_expand and event == Sys_Events.CLICKED:  # Open node on click
                if self._widget.isExpanded(selected_index):
                    self._widget.collapse(selected_index)
                else:
                    self._widget.expand(selected_index)

            file = []

            if event == Sys_Events.EXPANDED or event == Sys_Events.COLLAPSED:
                date_modified = (
                    f"{selected_index.model().lastModified(selected_index).toPython():%Y-%m-%d %H:%M:%S%z}"
                )

                file.append(
                    selected_node(
                        name=selected_index.model().fileName(selected_index),
                        path=selected_index.model().filePath(selected_index),
                        size=selected_index.model().size(selected_index),
                        modified=selected_index.model()
                        .lastModified(selected_index)
                        .toPython(),
                        date_modified=date_modified,
                        type=selected_index.model().type(selected_index).split()[0],
                        isdir=selected_index.model().isDir(selected_index),
                    )
                )
            else:
                for selected_index in self._widget.selectedIndexes():
                    selected_index: qtC.QModelIndex

                    if selected_index.column() == 0:
                        date_modified = (
                            f"{selected_index.model().lastModified(selected_index).toPython():%Y-%m-%d %H:%M:%S%z}"
                        )

                        file.append(
                            selected_node(
                                name=selected_index.model().fileName(selected_index),
                                path=selected_index.model().filePath(selected_index),
                                size=selected_index.model().size(selected_index),
                                modified=selected_index.model()
                                .lastModified(selected_index)
                                .toPython(),
                                date_modified=date_modified,
                                type=selected_index.model()
                                .type(selected_index)
                                .split()[0],
                                isdir=selected_index.model().isDir(selected_index),
                            )
                        )

            file = tuple(file)

            self._Value = file

            if self.callback is not None:
                handler = _Event_Handler(parent_app=self.parent_app, parent=self)

                window_id = Get_Window_ID(self.parent_app, self.parent, self)

                return handler.event(
                    window_id=window_id,
                    callback=self.callback,
                    action=event.name,
                    container_tag=self.container_tag,
                    tag=self.tag,
                    event=event,
                    value=file,
                    widget_dict=self.parent_app.widget_dict_get(
                        window_id=window_id, container_tag=self.container_tag
                    ),
                    control_name=self.__class__.__name__,
                    parent=self.parent_app.widget_get(
                        window_id=window_id,
                        container_tag=self.container_tag,
                        tag=self.tag,
                    ),
                )

        else:
            return 1

    def change_folder(self, folder) -> None:
        """Changes the root folder for the directory view, clearing the view in the process.

        Args:
            folder (str): Name of the root folder (folder must exist).

        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(folder, str) and folder.strip() != ""
        ), f"button_action <{folder}> must be a non-empty string"

        self._widget: qtW.QTreeView  # Type hinting
        self._widget.reset()
        self._widget.setRootIndex(self.file_model.index(folder))

    @property
    def expand_on_click(self) -> bool:
        """Returns the expanded on click setting (true == dir node expands when clicked on)

        Returns:
            bool : The expand on click setting (true == dir node expands when clicked on)
        """
        return self.click_expand

    def value_get(self) -> tuple | None:
        """
        Returns the tuple containing the values of the selected row

        Returns:
            tuple : The tuple containing the file values from the selected node
        """

        return self._Value

    def value_set(self, value: str) -> None:
        """Sets the text value of the selected node

        Args:
            value (str): The text to set the text to
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(value, str), f"{value=}. Must be str"

        # TODO Fix this for a dir view - QTreeWidgetItem.settext
        self._widget: qtW.QTreeWidgetItem
        self._widget.setText(self.trans_str(value))


class _ClearTypingBufferEvent(qtC.QEvent):
    """
    Event class used for clearing the typing buffer.
    """

    EVENT_TYPE = qtC.QEvent.Type(qtC.QEvent.registerEventType())

    def __init__(self, data: any) -> None:
        """
        Constructs a _ClearTypingBufferEvent object.

        Args:
            data: The data to be cleared from the typing buffer.
        """
        super().__init__(_ClearTypingBufferEvent.EVENT_TYPE)
        self._data = data

    @property
    def data(self) -> any:
        """
        Returns:
            The data to be cleared from the typing buffer.
        """
        return self._data


@dataclasses.dataclass(slots=True)
class Grid_Col_Value:
    """Used to return a value"""

    value: any
    user_data: any
    row: int
    col: int
    existing_value: any


class _Grid_TableWidget(qtW.QTableWidget):
    typeBufferCleared = qtC.Signal(Grid_Col_Value)

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes a new instance of the Grid_TableWidget class.

        Parameters:
        *args: tuple
            Variable length argument list.
        **kwargs: dict
            Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

        self.typing_buffer = ""
        self.setFocusPolicy(qtC.Qt.StrongFocus)
        self.installEventFilter(self)

    def eventFilter(self, obj: qtC.QObject, event: qtC.QEvent) -> bool:
        """Filters key press events and modifies cell text accordingly.

        Args:
            obj (QObject): The object that triggered the event.
            event (QEvent): The event to filter.

        Returns:
            bool: True if the event was filtered; otherwise False.
        """
        assert isinstance(obj, qtC.QObject), f"{obj=}. Must be QObject."
        assert isinstance(event, qtC.QEvent), f"{event=}. Must be QEvent"

        if event.type() == qtC.QEvent.KeyPress:
            key_event = qtG.QKeyEvent(event)
            key = key_event.key()
            text = key_event.text()

            item = self.currentItem()

            if not item:
                return qtW.QTableView.eventFilter(self, obj, event)

            current_text = item.text()

            if event.key() in (qtC.Qt.Key_Return, qtC.Qt.Key_Enter):
                self.typingBufferCleared()
            elif key == qtC.Qt.Key_Backspace:
                item.setText(current_text[:-1])
            elif text:
                item.setText(current_text + text)
                self.typing_buffer = current_text + text
            return True

        return qtW.QTableView.eventFilter(self, obj, event)

    def focusInEvent(self, event: qtG.QFocusEvent) -> None:
        assert isinstance(event, qtG.QFocusEvent), f"{event=} must be a QFocusEvent"

        # This is here to select the text when focus is setinto the cell by row_scroll_to
        item = self.currentItem()

        if (
            self.item
            and hasattr(self.item, "editItem")
            and item
            and item.flags() & qtC.Qt.ItemIsEditable
        ):
            editor = self.item.editItem(item)

            if editor is not None:
                editor.setSelected(True)

    def focusOutEvent(self, event: qtG.QFocusEvent) -> None:
        """
        Overrides the default focusOutEvent to clear the typing buffer.

        Args:
            event (QFocusEvent): A QFocusEvent object representing the focus out event.
        """
        assert isinstance(event, qtG.QFocusEvent), f"{event=}. Must be a QFocusEvent"

        super().focusOutEvent(event)
        self.typingBufferCleared()

    def focusNextPrevChild(self, next: bool) -> bool:
        """
        Overrides the default focusNextPrevChild to clear the typing buffer.

        Args:
            next (bool): A boolean value indicating whether the focus is moving to the next widget or not.

        Returns:
            bool: Returns the return value from the base class's focusNextPrevChild.
        """
        assert isinstance(next, bool), f"{next=}. Must be bool"

        # Clear typing buffer when tabbing to next cell
        self.typingBufferCleared()

        return super().focusNextPrevChild(next)

    def typingBufferCleared(self) -> None:
        """
        A method to clear the typing buffer and emit a signal with the cleared data.
        """
        if self.typing_buffer:
            item = self.currentItem()

            if item is not None:
                item_data = item.data(qtC.Qt.UserRole)

                grid_col_value = Grid_Col_Value(
                    self.typing_buffer,
                    item_data.user_data if item_data is not None else None,
                    item.row(),
                    item.column(),
                    item_data.current_value if item_data is not None else None,
                )
            else:
                grid_col_value = Grid_Col_Value(self.typing_buffer, None, -1, -1, None)

            event = _ClearTypingBufferEvent(grid_col_value)
            qtW.QApplication.postEvent(self, event)
            self.typing_buffer = ""
            self.typeBufferCleared.emit(grid_col_value)


class _Grid_TableWidget_Item(qtW.QTableWidgetItem):
    """
    Custom QTableWidgetItem class that overrides the less than operator to allow for custom sorting of table cells.
    """

    def __lt__(self, other: any) -> bool:
        """
        Override the less than operator to allow for custom sorting of table cells.

        TODO Nuitka 1.54 really did not like try catch  blocks here, so I dumbed down the sorting that can
        be done. Needs to be revisited to handle dates etc. later



        Args:
            other (any): The other table cell to be compared.

        Returns:
            bool: True if this table cell is less than the other, False otherwise.
        """

        self_text = self.text()
        other_text = other.text()

        # check if both items are integers
        if (
            self_text.replace("-", "", 1).isdigit()
            and other_text.replace("-", "", 1).isdigit()
        ):
            return int(self_text) < int(other_text)

        # check if both items are floats
        elif (
            self_text.replace(".", "", 1).replace("-", "", 1).isdigit()
            and other_text.replace(".", "", 1).replace("-", "", 1).isdigit()
        ):
            return float(self_text) < float(other_text)
        else:
            return self_text < other_text


@dataclasses.dataclass
class Grid(_qtpyBase_Control):
    """Grid widget definition and creation"""

    width: int = 1  # BUTTON_SIZE.width
    height: int = BUTTON_SIZE.height

    col_def: list[Col_Def] | tuple[Col_Def, ...] = ()
    multiselect: bool = False
    noselection: bool = False
    header_sort: bool = True

    @dataclasses.dataclass(slots=True)
    class _Item_Data:
        """Used to store the data for a single item in a grid"""

        current_value: any
        original_value: any
        prev_value: any
        tag: str
        user_data: any
        data_type: IntEnum | None
        first_time: bool
        widget: qtW.QWidget | None
        orig_row: int | None

        def replace(
            self,
            current_value: Optional[any] = None,
            original_value: Optional[any] = None,
            prev_value: Optional[any] = None,
            tag: Optional[str] = None,
            user_data: Optional[any] = None,
            data_type: Optional[IntEnum] = None,
            first_time: Optional[bool] = None,
            widget: Optional[qtW.QWidget] = None,
            orig_row: Optional[int] = None,
        ) -> "_Item_Data":
            """Replaces the values of the item properties if the corresponding argument is not None.

            Args:
                current_value (Any): The current value of the item.
                original_value (Any): The original value of the item.
                prev_value (Any): The value of the item before the current value.
                tag (str): The tag name of an item.
                user_data (Any): User-set data values.
                data_type (IntEnum): The type of data that the item is storing. This is used to determine how to display the data in the table.
                first_time (bool): Indicates whether the item is being used for the first time.
                widget (qtW.QWidget): The widget that is being used to display an item.
                orig_row (int): The original row of the item.

            Returns:
                _Item_Data: The ItemData object itself.
            """
            if current_value is not None:
                self.current_value = current_value
            if original_value is not None:
                self.original_value = original_value
            if prev_value is not None:
                self.prev_value = prev_value
            if tag is not None:
                self.tag = tag
            if user_data is not None:
                self.user_data = user_data
            if data_type is not None:
                self.data_type = data_type
            if first_time is not None:
                self.first_time = first_time
            if widget is not None:
                self.widget = widget
            if orig_row is not None:
                self.orig_row = orig_row

            return self

    class _Data_Type(IntEnum):
        """Enum that represents the data types of items in a grid"""

        BOOL = 0
        DATE = 1
        DATETIME = 2
        FLOAT = 3
        INT = 4
        STR = 5

    def __post_init__(self) -> None:
        """Sets up the grid control. Checks arguments and sets up the grid instance variables"""

        super().__post_init__()  # Checks non grid specific arguments

        assert isinstance(self.multiselect, bool), f"{self.multiselect=}. Must be bool"
        assert isinstance(self.noselection, bool), f"{self.noselection=}. Must be bool"
        assert isinstance(self.header_sort, bool), f"{self.header_sort=}. Must be bool"

        assert isinstance(
            self.col_def, (list, tuple)
        ), f"{self.col_def=}. Must be list[Col_Def] | tuplle[Col_Def]"

        assert (
            len(self.col_def) > 0
        ), f"{self.col_def=}. Must be at least one column definition!"

        assert all(
            isinstance(definition, Col_Def) for definition in self.col_def
        ), f"{self.col_def=}. All items must be instances of Col_Def"

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates a grid gui control

        Args:
            parent_app (QtPyApp):  Application owner of the grid control
            parent (qtW.QWidget):  Parent control that owns  the grid
            container_tag (int):  The tag (name) of the grid control

        Returns:
            qtW.QWidget : The grid control

        """
        assert isinstance(
            parent_app, QtPyApp
        ), f"{parent_app=}. must be an instance of QtPyApp"
        assert isinstance(
            parent, qtW.QWidget
        ), f"{parent=}. Must be an instance of qtW.QWidget"
        assert isinstance(container_tag, str), f"{container_tag=}. Must be a string"

        widget = cast(
            qtW.QTableWidget,
            super()._create_widget(
                parent_app=parent_app, parent=parent, container_tag=container_tag
            ),
        )

        self._widget: qtW.QTableWidget  # Type hinting

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        labels = []
        num_cols = 0

        self._col_widths = {}

        for col_index, definition in enumerate(self.col_def):
            labels.append(self.trans_str(definition.label))

            if len(self.trans_str(definition.label)) > definition.width:
                self._col_widths[col_index] = len(self.trans_str(definition.label))
            else:
                self._col_widths[col_index] = definition.width

        if len(labels) > 0:
            num_cols = len(labels)

        self._widget.setColumnCount(num_cols)

        char_pixel_size = self.pixel_char_size(char_height=1, char_width=1)

        grid_width = 0

        for col_index, definition in enumerate(self.col_def):
            item_data = self._Item_Data(
                tag=definition.tag,
                current_value=None,
                prev_value=None,
                original_value=None,
                user_data=None,
                data_type=None,
                first_time=True,
                widget=None,
                orig_row=None,
            )

            grid_width += self._col_widths[col_index]

            item = _Grid_TableWidget_Item(
                definition.label, qtW.QListWidgetItem.ItemType.Type
            )
            item.setData(qtC.Qt.UserRole, item_data)

            self._widget.setHorizontalHeaderItem(col_index, item)

            self._widget.setColumnWidth(
                col_index, self._col_widths[col_index] * char_pixel_size.width
            )
            self._widget.horizontalHeaderItem(col_index).tag = definition.label

        if self.pixel_unit:
            height = self.height
        else:
            height = self.height * self._widget.verticalHeader().defaultSectionSize()

        self._widget.verticalHeader().setVisible(False)

        self._widget.setSelectionBehavior(qtW.QTableView.SelectRows)

        if self.multiselect:
            self._widget.setSelectionMode(
                # SingleSelection
                qtW.QAbstractItemView.ExtendedSelection
            )
        else:
            self._widget.setSelectionMode(qtW.QAbstractItemView.SingleSelection)

        if self.noselection:
            self._widget.setSelectionMode(qtW.QTableView.NoSelection)

        if self.header_sort:
            self._widget.setSortingEnabled(True)
            self._widget.horizontalHeader().setSectionsClickable(True)
        else:
            self._widget.setSortingEnabled(False)
            self._widget.horizontalHeader().setSectionsClickable(False)

        if self.width <= 1:  # Override auto-calculated grid width
            self.width = grid_width + 3  # Scroll bar space

        self._widget.setMinimumWidth(
            (self.width * char_pixel_size.width) + self.tune_hsize
        )  # Allow for scroll-bar
        self._widget.setMaximumWidth(
            (self.width * char_pixel_size.width) + self.tune_hsize
        )
        self._widget.setMinimumHeight(height + self.tune_vsize)

        return widget

    def _event_handler(self, *args) -> int:
        """Handles events for the grid control.
        Args:
            *args: Default arguments for a grid control.
        Returns:
            int: 1 if the event was handled successfully, -1 otherwise.
        """
        # Initialize variables
        row, col, row_prev, col_prev = -1, -1, -1, -1
        widget_item = None
        event = None

        # Parse arguments
        for index, arg in enumerate(args):
            if index == 0:  # Event type is always first
                event = arg
            else:
                if isinstance(arg, tuple):
                    if len(arg) == 1:
                        widget_item = arg[0]
                    elif len(arg) == 2:
                        row, col = arg
                    elif len(arg) == 4:
                        row_prev, col_prev, row, col = arg

        value = None
        user_data = None
        self._widget: qtW.QTableWidget  # Type hinting
        window_id = Get_Window_ID(self.parent_app, self.parent, self)
        grid_col_value = Grid_Col_Value("", None, row, col, "")

        # Handle event
        if (
            event
            and self.callback
            and (
                (
                    widget_item
                    and isinstance(
                        widget_item, (qtW.QTableWidgetItem, _Grid_TableWidget_Item)
                    )
                )
                or event in (Sys_Events.FOCUSIN, Sys_Events.FOCUSOUT)
            )
            and self.parent_app.widget_exist(
                window_id=window_id, container_tag=self.container_tag, tag=self.tag
            )
        ):
            if row == -1:
                row = self._widget.currentRow()

            if col == -1:
                col = self._widget.currentColumn()

            event: Sys_Events
            if event == Sys_Events.CLEAR_TYPING_BUFFER:
                grid_col_value = widget_item  # Grid_Col_Value
            elif event == Sys_Events.TEXTCHANGED:
                pass
            else:
                if row >= 0 and col >= 0:
                    value = self.value_get(row, col)
                    user_data = self.userdata_get(row, col)
                elif widget_item is not None:
                    if hasattr(widget_item, "text"):
                        value = widget_item.text()
                    user_data = None

                grid_col_value = Grid_Col_Value(value, user_data, row, col, value)

            if col >= 0:
                col_tag = self.coltag_get(col)
            else:
                col_tag = self.tag

            return _Event_Handler(parent_app=self.parent_app, parent=self).event(
                window_id=window_id,
                callback=self.callback,
                action=event.name,
                container_tag=self.container_tag,
                tag=col_tag,
                event=event,
                value=grid_col_value,
                widget_dict=self.parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.container_tag
                ),
                control_name=self.__class__.__name__,
                parent=self.parent_app.widget_get(
                    window_id=window_id, container_tag=self.container_tag, tag=self.tag
                ),
            )
        else:
            return 1

    def checkitemrow_get(self, row: int, col: int) -> Grid_Item | tuple:
        """Returns an named tuple of (row_index, tag, current_value, and user_data) from the row and column specified
        if the item is checked or an empty tuple if not checked.

        Args:
            row (int): The index of the row to retrieve the item from.
            col (int): The index of the column to retrieve the item from.

        Returns:
            Grid_Item_Tuple: A Grid_Item_Tuple tuple containing the row_index, tag, current_value, and user_data of the checked item.
            An empty tuple if the item is not checked.
        """
        assert isinstance(row, int), "row argument must be of type int"
        assert isinstance(col, int), "col argument must be of type int"

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)
        item_data = item.data(qtC.Qt.UserRole)

        if item.checkState() == qtC.Qt.Checked:
            return Grid_Item(
                row_index=row_index,
                tag=item_data.tag,
                current_value=item_data.current_value,
                user_data=item_data.user_data,
            )
        else:
            return ()

    def checkitemrow_set(self, checked: bool, row: int, col: int):
        """Sets the check state of the item at the row and column specified.

        Args:
            checked (bool): True for Checked, False for Unchecked.
            row (int): The index of the row to set the check state for.
            col (int): The index of the column to set the check state for.

        """
        assert isinstance(checked, bool), f"{checked=}. Must be of type bool"
        assert isinstance(row, int), f"{row}. Must be of type int"
        assert isinstance(col, int), f"{col=}. Must be of type int"

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)

        if checked:
            item.setCheckState(qtC.Qt.Checked)
        else:
            item.setCheckState(qtC.Qt.Unchecked)

    def checkitems_all(self, checked: bool = True, col_tag: str = ""):
        """Checks all items in the grid that are checkable.

        Args:
            checked (bool): Whether to check or uncheck the items. True to check, False to uncheck. Defaults to True.
            col_tag (str): The column tag name. Only items in this column will be checked/unchecked. Defaults to "".

        Raises:
            ValueError: If col_tag is not a string.

        """
        assert isinstance(checked, bool), "checked argument must be of type bool."
        assert isinstance(col_tag, str), "col_tag argument must be of type str."

        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError("Widget is not set.")

        col_tag = col_tag.strip()

        for row_index in range(self._widget.rowCount()):
            if col_tag:
                col_index = self.colindex_get(col_tag)
                definition = self.col_def[col_index]
                if definition.checkable:
                    self.checkitemrow_set(checked, row_index, col_index)
            else:
                for col_index, definition in enumerate(self.col_def):
                    if definition.checkable:
                        self.checkitemrow_set(checked, row_index, col_index)

    @property
    def checkitems_get(self) -> tuple:
        """Get the checked items.

        Returns:
            tuple: A tuple of named tuples with the following fields:
                - row_index
                - tag
                - current_value
                - user_data
        """
        assert self._widget is not None, f"{self._widget=} not set"

        checked_items = []

        for row_index in range(self._widget.rowCount()):
            for col_index in range(self._widget.columnCount()):
                item = self._widget.item(row_index, col_index)
                item_data = item.data(qtC.Qt.UserRole)

                if item.checkState() == qtC.Qt.Checked:
                    checked_items.append(self.checkitemrow_get(row_index, col_index))

        return tuple(checked_items)

    def clear(self):
        """Clears the grid the right way leaving the column layout alone"""
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget.setRowCount(0)

    @property
    def col_count(self) -> int:
        """Gets number of colunns in the grid

        Returns:
            int: The number of colunns in the grid

        """

        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        return self._widget.columnCount()

    def colindex_get(self, column_tag: str) -> int:
        """Returns the column index for a given column tag name.

        Args:
            column_tag (str): The column tag name.

        Returns:
            int: The column index for a column tag name.

        """
        assert (
            isinstance(column_tag, str) and column_tag.strip()
        ), "column_tag must be a non-empty string"

        for col_index in range(self._widget.columnCount()):
            item_data = self._widget.horizontalHeaderItem(col_index).data(
                qtC.Qt.UserRole
            )
            if item_data.tag == column_tag:
                return col_index

        raise AssertionError(f"{column_tag=}. Does not exist!")

    def coltag_get(self, column_index: int) -> str:
        """Returns the column tag name for a given column index.

        Args:
            column_index (int): The column index reference.

        Returns:
            str: The column tag name.

        Raises:
            AssertionError: If the column index is invalid.
        """
        assert isinstance(column_index, int), "column_index must be an integer."
        assert (
            0 <= column_index < self._widget.columnCount()
        ), f"{column_index=} is out of range. {self._widget.columnCount()=}"

        item = self._widget.horizontalHeaderItem(column_index)
        item_data = item.data(qtC.Qt.UserRole)

        return item_data.tag

    @property
    def selected_row(self) -> int:
        """Gets the currently selected row

        Returns:
            int: The currently selected row

        """
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        return self._widget.currentRow()

    @property
    def selected_col(self) -> int:
        """Gets the currently selected col

        Returns:
            int: The currently selected col

        """
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        return self._widget.currentColumn()

    def grid_item_get(self, row: int = -1, col: int = -1) -> Grid_Item | None:
        """
        Returns the grid item stored on the given column referred to by row and col.
        If row or col is not specified, it returns the grid item stored in the current row or column.
        If no grid_item is found, returns None.

        Args:
            row (int): Row index reference (default {-1})
            col (int): Column index reference (default {-1})

        Returns:
            Grid_Item: Grid item stored in column referred to by row and col
        """
        assert row == -1 or row >= 0, f"{row=} must be an int == -1 or int >= 0"
        assert col == -1 or col >= 0, f"{col=} must be an int == -1 or int >= 0"

        self._widget: qtW.QTableWidget

        if row == -1:
            row = self._widget.currentRow()
        if col == -1:
            col = self._widget.currentColumn()

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)
        item_data = item.data(qtC.Qt.UserRole)

        return item_data if item_data is not None else None

    def load_csv_file(
        self,
        file_name: str,
        display_col: Union[int, str],
        select_text: str = "",
        text_index: int = 1,
        line_start: int = 1,
        data_index: int = 1,
        ignore_header: bool = True,
        delimiter: str = ",",
    ) -> int:
        """Loads data from a CSV file into the grid.

        Args:
            file_name (str): The name of the CSV file.
            display_col (Union[int, str]): The column in the grid that will display the loaded data.
            select_text (str, optional): The text to select in the combo-box after the data is loaded. Defaults to "".
            text_index (int, optional): The column index in the CSV file containing the text to display in the grid. Defaults to 1.
            line_start (int, optional): The line number in the CSV file to start loading data from. Defaults to 1.
            data_index (int, optional): The column index in the CSV file containing the user data to associate with the loaded data. Defaults to 1.
            ignore_header (bool, optional): Set to True if the CSV file has a header row that should be ignored. Defaults to True.
            delimiter (str, optional): The field separator used in the CSV file. Defaults to ",".

        Returns:
            int: The length of the maximum item loaded or -1 if there is a problem with the file.

        """
        assert (
            isinstance(file_name, str) and file_name.strip()
        ), f"{file_name=}. Must be a non-empty string"
        assert isinstance(
            display_col, (str, int)
        ), f"{display_col=}. Must be a non-empty string or int"
        assert isinstance(
            select_text, str
        ), f"{select_text=}. Must be a non-empty string"
        assert (
            isinstance(text_index, int) and text_index > 0
        ), f"{text_index=}. Must be an int > 0"
        assert (
            isinstance(line_start, int) and line_start > 0
        ), f"{line_start=}. Must be an int > 0"
        assert (
            isinstance(data_index, int) and data_index > 0
        ), f"{data_index=}. Must be an int > 0"
        assert isinstance(ignore_header, bool), f"{ignore_header=}. Must be bool"
        assert (
            isinstance(delimiter, str) and len(delimiter) == 1
        ), f"{delimiter=}. Must be str and 1 char long"

        rowcol = self._rowcol_validate(row=self.row_count, col=display_col)

        if not select_text:
            select_text = self.text

        if not os.path.isfile(file_name) and not os.access(file_name, os.R_OK):
            return -1

        max_len = 0

        with open(file_name, "r") as csv_file:
            for i, line in enumerate(csv_file.readlines()):
                if i == 0 and ignore_header:
                    continue
                elif i + 1 < line_start:
                    continue

                line_split = line.strip().split(delimiter)

                if len(line_split) < max(text_index, data_index):
                    continue

                if len(line_split[text_index - 1]) > max_len:
                    max_len = len(line_split[text_index - 1])

                self.value_set(
                    value=line_split[text_index - 1],
                    row=self.row_count,
                    col=rowcol[1],
                    user_data=line_split[data_index - 1],
                )

        return max_len

    def move_row_up(self, move_row: int) -> int:
        """Move the currently selected row up one position in the table.

        If the currently selected row is already at the top of the table, nothing happens.

        Returns:
            int: The new row or -1 if the row is at the top of the table
        """
        self._widget: qtW.QTableWidget
        column = self._widget.currentColumn()

        if move_row > 0:
            new_row = move_row - 1
            self._widget.insertRow(new_row)

            for col in range(self._widget.columnCount()):
                row_widget: _qtpyBase_Control | None = self.row_widget_get(
                    move_row + 1, col
                )

                self._widget.setItem(
                    new_row, col, self._widget.takeItem(move_row + 1, col)
                )

                if row_widget and "|" in row_widget.tag:
                    row_widget.tag = row_widget.tag.split("|")[1]
                    self.row_widget_set(new_row, col, row_widget)

            self._widget.removeRow(move_row + 1)

            # Row widget items have the row embedded in the tag name and this needs resetting
            for row in range(new_row, self._widget.rowCount()):
                for col in range(self._widget.columnCount()):
                    row_widget: _qtpyBase_Control | None = self.row_widget_get(row, col)

                    if row_widget and "|" in row_widget.tag:
                        row_widget.tag = row_widget.tag.split("|")[1]
                        self.row_widget_set(row, col, row_widget)

            self._widget.setCurrentCell(new_row, column)

            return new_row

        return -1

    def move_row_down(self, move_row: int) -> int:
        """Move the currently selected row down one position in the table.

        If the currently selected row is already at the bottom of the table, nothing happens.

        Returns:
            int: The new row or -1 if the row is not at the bottom of the table
        """
        self._widget: qtW.QTableWidget
        column = self._widget.currentColumn()

        if move_row < self._widget.rowCount() - 1:
            new_row = move_row + 2
            self._widget.insertRow(new_row)

            for col in range(self._widget.columnCount()):
                row_widget: _qtpyBase_Control | None = self.row_widget_get(
                    move_row, col
                )

                self._widget.setItem(new_row, col, self._widget.takeItem(move_row, col))

                if row_widget and "|" in row_widget.tag:
                    row_widget.tag = row_widget.tag.split("|")[1]
                    self.row_widget_set(new_row, col, row_widget)

            self._widget.removeRow(move_row)

            # Row widget items have the row embedded in the tag name and this needs resetting
            for row in range(new_row):
                for col in range(self._widget.columnCount()):
                    row_widget: _qtpyBase_Control | None = self.row_widget_get(row, col)

                    if row_widget and "|" in row_widget.tag:
                        row_widget.tag = row_widget.tag.split("|")[1]
                        self.row_widget_set(row, col, row_widget)

            self._widget.setCurrentCell(new_row, column)

            return move_row + 1

        return -1

    @property
    def row_count(self) -> int:
        """Returns the grid row count

        Returns:
            int: Row Count (number of rows in grid)

        """
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        return self._widget.rowCount()

    @property
    def row_append(self) -> int:
        """Appends a row to the grid

        Returns:
            int : row number inserted

        """
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        row = self._widget.rowCount()
        self._widget.insertRow(row)

        # add a new QTableWidgetItem to each cell in the new row
        for col_index in range(self._widget.columnCount()):
            item_data = self._Item_Data(
                tag=self.col_def[col_index].tag,
                current_value=None,
                prev_value=None,
                original_value=None,
                user_data=None,
                data_type=None,
                first_time=True,
                widget=None,
                orig_row=row,
            )

            item = _Grid_TableWidget_Item("")

            if self.col_def[col_index].editable:
                flags = (
                    qtC.Qt.ItemIsSelectable
                    | qtC.Qt.ItemIsEnabled
                    | qtC.Qt.ItemIsEditable
                )
            else:
                flags = qtC.Qt.ItemIsSelectable | qtC.Qt.ItemIsEnabled

            if self.col_def[col_index].checkable:
                flags = flags | qtC.Qt.ItemIsUserCheckable
                item.setCheckState(qtC.Qt.Unchecked)

            item.setFlags(flags)

            item.setData(qtC.Qt.UserRole, item_data)

            # make sure the QTableWidgetItem is added to the correct cell
            if self._widget.item(row, col_index) is None:
                self._widget.setItem(row, col_index, item)
            else:
                self._widget.takeItem(row, col_index)
                self._widget.setItem(row, col_index, item)

        self.select_row(row)

        for col_index in range(self._widget.columnCount()):
            if self.col_def[col_index].editable:
                self._widget.edit(self._widget.model().index(row, col_index))

        return row

    def row_delete(self, row: int) -> None:
        """Deletes a row

        Args:
            row (int): Row index in the grid
        """
        assert (
            isinstance(row, int) and 0 <= row < self.row_count
        ), f"{row=}. Must be int between 0 and {self.row_count}"

        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(row, int) and 0 <= row < self._widget.rowCount()
        ), f"{row=}. Must be an int >= 0 and < {self._widget.rowCount()}"

        col_count = len(self._col_widths)
        widgets = []

        for col_num in range(0, col_count):
            widgets.append(self.row_widget_get(row, col_num))

        self._widget.removeRow(row)

        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        for widget in widgets:
            if widget is not None and isinstance(widget, _Container):
                for item in widget.tags_gather():
                    if self.tag != item.tag:
                        self.parent_app.widget_del(
                            window_id=window_id,
                            container_tag=item.container_tag,
                            tag=item.tag,
                        )

    def row_widget_tag_delete(
        self, widget_row: int, tag: str = "", container_tag: str = ""
    ) -> int:
        """Deletes a row if the row contains a dev added row widget with a tag that matches the row and tag passed to the
        method

        Args:
            widget_row (int): The row housing the widget
            tag (str): The tag of the widget to be deleted.
            container_tag (str): This is the container tag of the  widget (used only when the widget container tag has
                been set by the dev. Defaults to self.container).

        Returns:
            int: 1 row found and deleted, -1 no row found that matches the tag passed to the method
        """
        assert isinstance(container_tag, str), f"{container_tag=}. Must be str"
        assert isinstance(tag, str) and tag.strip() != "", f"{tag=}. Must be str"

        col_count = len(self._col_widths)
        if container_tag == "":
            container_tag = self.container_tag
        row_tag = f"{widget_row}{tag}"

        for row in reversed(range(0, self.row_count)):
            for col_num in range(0, col_count):
                widget = self.row_widget_get(row, col_num)
                if (
                    widget is not None
                    and widget.container_tag == container_tag
                    and widget.tag == row_tag
                ):
                    self.row_delete(row)
                    return 1
        return -1

    def row_insert(self, row: int, scroll_to: bool = True) -> None:
        """Inserts a row at the given row index. If row is > number of rows then a new row is inserted.

        Args:
            row (int): The row index in the grid.
            scroll_to (bool): Whether to scroll to the inserted row.

        """
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(row, int) and row > 0, f"{row=} must be an int > 0"

        if row > self._widget.rowCount():
            row = self.row_append
        else:
            self._widget.insertRow(row)

        if scroll_to:
            self.select_row(row=row)

    def select_col(self, row: int, col: int) -> None:
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(row, int), f"{row=}. Must be int"
        assert isinstance(col, int), f"{col=}. Must be int"

        assert (
            0 <= row < self._widget.rowCount()
        ), f"{row=}. Must be >= 0 and < {self._widget.rowCount()}"
        assert (
            col == -1 or 0 <= col < self._widget.columnCount()
        ), f"{col=}. Must be >= 0 and < {self._widget.columnCount()}"

        self._widget.setCurrentCell(row, col)

    def row_scroll_to(self, row: int, col: int = -1) -> None:
        """
        Scrolls to the row.

        Note: Deprecated will be removed in a later release. Use select_row
        """
        self.select_row(row, col)

    def select_row(self, row: int, col: int = -1) -> None:
        """Scrolls to the row.

        Args:
            row (int): The row index in the grid.
            col (int): The column index in the grid (defaults to -1 scroll to row only).

        Raises:
            RuntimeError: If the widget is not set.
        """
        self._widget: qtW.QTableWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(row, int), f"{row=}. Must be int"
        assert isinstance(col, int), f"{col=}. Must be int"

        assert (
            0 <= row < self._widget.rowCount()
        ), f"{row=}. Must be >= 0 and < {self._widget.rowCount()}"
        assert (
            col == -1 or 0 <= col < self._widget.columnCount()
        ), f"{col=}. Must be >= 0 and < {self._widget.columnCount()}"

        index = self._widget.model().index(row, 0)
        self._widget.scrollTo(index)

        self._widget.selectRow(row)

        if col >= 0:
            self._widget.setCurrentCell(row, col)
            item = self._widget.item(row, col)

            if item is not None:
                item.setSelected(True)

        self._widget.setFocus()

        if col >= 0 and self.col_def[col].editable:
            self._widget.edit(self._widget.model().index(row, col))

    def userdata_set(self, row: int = -1, col: int = -1, user_data: any = None) -> None:
        """
        Sets the user data stored on the given column referred to by row and col.
        If row is not specified, it sets the user data stored in the current row .
        If col is not specified it sets the user data on all the cols


        Args:
            row (int): Row index reference (default {-1})
            col (int): Column index reference (default {-1})
            user_data (any): User data to be stored (default: None)
        """

        # ====== Helper
        def _set_user_data(user_data: any, item: qtW.QTableWidgetItem) -> None:
            """
            Sets the user data on the given item.

            Args:
                user_data (any): User data to be stored.
                item (QTableWidgetItem): The item to set the user data on.

            """
            # user_data anything so no need to check
            assert isinstance(
                item, qtW.QTableWidgetItem
            ), f"{item=}. Must be QTableWidgetItem"

            item_data = item.data(qtC.Qt.UserRole)

            if item_data.first_time:
                item_data = item_data.replace(
                    current_value=item_data.current_value,
                    prev_value=item_data.prev_value,
                    original_value=item_data.original_value,
                    data_type=self._data_type_encode(item_data.current_value),
                    first_time=False,
                    user_data=user_data,
                    widget=None,
                    orig_row=row_index,
                )
            else:
                item_data = item_data.replace(
                    current_value=item_data.current_value,
                    prev_value=item_data.prev_value,
                    data_type=self._data_type_encode(item_data.current_value),
                    user_data=user_data,
                    widget=item_data.widget,
                )

            item.setData(qtC.Qt.UserRole, item_data)

        # ====== Main
        assert row == -1 or row >= 0, f"{row=} must be an int == -1 or int >= 0"
        assert col == -1 or col >= 0, f"{col=} must be an int == -1 or int >= 0"

        self._widget: qtW.QTableWidget

        if row == -1:
            row = self._widget.currentRow()
        if col == -1:
            col = self._widget.currentColumn()

        row_index, col_index = self._rowcol_validate(row, col)

        if col_index == -1:
            for col_index in range(0, self._widget.columnCount()):
                item = self._widget.item(row_index, col_index)
                _set_user_data(user_data, item)
        else:
            item = self._widget.item(row_index, col_index)
            _set_user_data(user_data, item)

    def userdata_get(self, row: int = -1, col: int = -1) -> any:
        """
        Returns the user data stored on the given column referred to by row and col.
        If row or col is not specified, it returns user data stored in the current row or column.
        If no user data is stored, returns None.

        Args:
            row (int): Row index reference (default {-1})
            col (int): Column index reference (default {-1})

        Returns:
            any: User data stored in column referred to by row and col
        """
        assert row == -1 or row >= 0, f"{row=} must be an int == -1 or int >= 0"
        assert col == -1 or col >= 0, f"{col=} must be an int == -1 or int >= 0"

        self._widget: qtW.QTableWidget

        if row == -1:
            row = self._widget.currentRow()
        if col == -1:
            col = self._widget.currentColumn()

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)

        if not item:
            return None

        item_data = item.data(qtC.Qt.UserRole)

        return item_data.user_data if item_data is not None else None

    def value_get(
        self, row: int = -1, col: int = -1
    ) -> (
        bool
        | datetime.date
        | datetime.datetime
        | datetime.time
        | float
        | int
        | str
        | None
    ):
        """
        Returns the current value stored in the given column referred to by row and col.
        If row or col is not specified, the current row or current column is used as default.

        Args:
            row (int): The row index reference (default: -1).
            col (int): The column index reference (default: -1).

        Returns:
            bool| datetime.date| datetime.datetime| datetime.time| float| int| str: The value stored in the column referred to by row and col.
                Returns None if the item or item data is None.
        """
        assert isinstance(row, int) and row >= -1, f"{row=} must be an int >= -1"
        assert isinstance(col, int) and col >= -1, f"{col=} must be an int >= -1"

        widget = self._widget
        if widget is None:
            raise RuntimeError(f"{widget=} not set")

        if row == -1:
            row = widget.currentRow()
        if col == -1:
            col = widget.currentColumn()

        row, col = self._rowcol_validate(row, col)
        item = widget.item(row, col)

        if item is None:
            return None

        item_data = item.data(qtC.Qt.UserRole)

        current_value = item_data.current_value
        new_value_str = item.text().strip()

        if current_value is None or str(current_value).strip() != new_value_str:
            if current_value is None:
                new_value = new_value_str
            else:
                new_value = type(current_value)(new_value_str)

            item_data = item_data.replace(
                current_value=new_value,
                prev_value=current_value,
                data_type=self._data_type_encode(new_value),
                user_data=item_data.user_data,
                widget=item_data.widget,
            )

            item.setData(qtC.Qt.UserRole, item_data)

        return item_data.current_value if item_data is not None else None

    def valueorig_get(
        self, row: int = -1, col: int = -1
    ) -> (
        bool
        | datetime.date
        | datetime.datetime
        | datetime.time
        | float
        | int
        | str
        | None
    ):
        """Returns the original value stored in the given column referred to by row and col.
        Default returns current row and current column

        Args:
            row (int): Row index reference (default {-1})
            col (int): Column index reference (default {-1})

        Returns:
            -> bool| datetime.date| datetime.datetime| datetime.time| float| int| str | None: The original value stored in the column referred to by row and col
        """
        self._widget: qtW.QTableWidget

        assert isinstance(row, int) and (
            row == -1 or row >= 0
        ), f"{row=}. Must be an int == -1 or int >= 0"
        assert isinstance(col, int) and (
            col == -1 or col >= 0
        ), f"{col=}. Must be an int == -1 or int >= 0"

        if self._widget is None:
            raise RuntimeError(f"{self._widget=} not set")

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)

        if item is None:
            return None

        item_data = item.data(qtC.Qt.UserRole)

        return item_data.original_value if item_data is not None else None

    def get_previous_value(
        self, row: int = -1, col: int = -1
    ) -> (
        bool
        | datetime.date
        | datetime.datetime
        | datetime.time
        | float
        | int
        | str
        | None
    ):
        """Returns the previous value stored in the given column referred to by row and col. Default returns current row
        and current column

        Args:
            row (int): Row index reference (default {-1})
            col (int): Col index reference (default {-1})

        Returns:
            bool| datetime.date| datetime.datetime| datetime.time| float| int| str | None: The previous value stored in column referred to by row and col
        """
        self._widget: qtW.QTableWidget

        assert isinstance(row, int) and (
            row == -1 or row >= 0
        ), f"{row=}. Must be an int == -1 or int >= 0"
        assert isinstance(col, int) and (
            col == -1 or col >= 0
        ), f"{col=}. Must be an int == -1 or int >= 0"

        if self._widget is None:
            raise RuntimeError(f"{self._widget=} Not set")

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)

        if item is None:
            return None

        item_data = item.data(qtC.Qt.UserRole)

        return item_data.previous_value if item_data is not None else None

    @overload
    def value_set(
        self, value: bool, row: int, col: int, user_data: any, tooltip: str = ""
    ) -> None:
        ...

    @overload
    def value_set(
        self,
        value: datetime.date,
        row: int,
        col: int,
        user_data: any,
        tooltip: str = "",
    ) -> NoReturn:
        ...

    @overload
    def value_set(
        self,
        value: datetime.datetime,
        row: int,
        col: int,
        user_data: any,
        tooltip: str = "",
    ) -> NoReturn:
        ...

    @overload
    def value_set(
        self,
        value: datetime.time,
        row: int,
        col: int,
        user_data: any,
        tooltip: str = "",
    ) -> NoReturn:
        ...

    @overload
    def value_set(
        self, value: float, row: int, col: int, user_data: any, tooltip: str = ""
    ) -> None:
        ...

    @overload
    def value_set(
        self, value: int, row: int, col: int, user_data: any, tooltip: str = ""
    ) -> None:
        ...

    @overload
    def value_set(
        self, value: str, row: int, col: int, user_data: any, tooltip: str = ""
    ) -> None:
        ...

    def value_set(
        self,
        value: Union[
            bool, datetime.date, datetime.datetime, datetime.time, float, int, str
        ],
        row: int,
        col: int,
        user_data: any,
        tooltip: str = "",
    ) -> None:
        """
        Sets a display value (and user data if supplied) at a given row and column.

        Args:
            value (bool | datetime.date | datetime.datetime |datetime.time | float | int |str): The value to be displayed.
            row (int): Row index reference.
            col (int): Column index reference.
            user_data (any): User data to be stored.
            tooltip (str): Tooltip to be displayed.

        Returns:
            None.
        """
        self._widget: qtW.QTableWidget

        assert isinstance(
            value,
            (bool, datetime.date, datetime.datetime, datetime.time, float, int, str),
        ), f"{value=}. Must Be base type"
        assert isinstance(row, int) and (
            row == -1 or row >= 0
        ), f"{row=}. Must be an int == -1 or int >= 0"
        assert isinstance(col, int) and (
            col == -1 or col >= 0
        ), f"{col=}. Must be an int == -1 or int >= 0"

        if self._widget is None:
            raise RuntimeError(f"{self._widget=} not set")

        # Append a new row if the specified row is out of range
        if row >= self._widget.rowCount():
            row_index = self.row_append
            row = row_index

        row_index, col_index = self._rowcol_validate(row, col)

        # Convert date and datetime objects to Qt-compatible formats
        if isinstance(value, datetime.date):
            locale = qtC.QLocale()
            value = qtC.QDate.fromString(
                str(value), locale.dateFormat(qtC.QLocale.ShortFormat)
            )
        elif isinstance(value, datetime.datetime):
            locale = qtC.QLocale()
            value = qtC.QDateTime.fromString(
                str(value), locale.dateTimeFormat(qtC.QLocale.ShortFormat)
            )

        item = self._widget.item(row_index, col_index)

        item_data = item.data(qtC.Qt.UserRole)

        item.setText(str(value))

        if tooltip:
            item.setToolTip(self.trans_str(tooltip))

        if item_data.first_time:
            item_data = item_data.replace(
                current_value=value,
                original_value=value,
                data_type=self._data_type_encode(value),
                first_time=False,
                user_data=user_data,
                widget=None,
                orig_row=row_index,
            )
        else:
            item_data = item_data.replace(
                current_value=value,
                prev_value=item_data.current_value,
                data_type=self._data_type_encode(value),
                user_data=user_data,
                widget=item_data.widget,
            )

        item.setData(qtC.Qt.UserRole, item_data)

    def row_widget_get(
        self, row: int, col: int, container_tag: str = "", tag: str = "-"
    ) -> Optional[_qtpyBase_Control]:
        """
        Returns the widget at the specified row and column

        Args:
            row (int): Grid row index. If -1, the current row is used.
            col (int): Grid column index. If -1, the current column is used.
            container_tag (str): Container tag is only needed if the desired widget is in a container
            tag (str): control tag name. If "-" is supplied, the container is returned.

        Returns:
            The widget itself or the widget's container
        """
        self._widget: qtW.QTableWidget

        assert isinstance(row, int) and (
            row == -1 or row >= 0
        ), f"{row=}. Must be an int == -1 or int >= 0"
        assert isinstance(col, int) and (
            col == -1 or col >= 0
        ), f"{col=}. Must be an int == -1 or int >= 0"
        assert isinstance(tag, str) and (
            tag.strip() != "" or tag == "-"
        ), f"{tag=}. Must be a non-empty str or '-'"

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        row_index, col_index = self._rowcol_validate(row, col)

        item = self._widget.item(row_index, col_index)
        item_data = item.data(qtC.Qt.UserRole)

        if item_data is not None and item_data.widget is not None:
            if tag == "-":  # Return container/widget
                return item_data.widget
            else:
                window_id = Get_Window_ID(self.parent_app, self.parent, self)

                if container_tag != "":
                    if self.parent_app.widget_exist(
                        window_id=window_id,
                        container_tag=f"{row_index}{container_tag}",
                        tag=tag,
                    ):
                        return self.parent_app.widget_get(
                            window_id=window_id,
                            container_tag=f"{row_index}{container_tag}",
                            tag=tag,
                        )
                else:
                    return self.parent_app.widget_get(
                        window_id=window_id,
                        container_tag=item_data.widget.container_tag,
                        tag=tag,
                    )

        return None

    def row_widget_set(
        self, row: int, col: int, widget: _qtpyBase_Control, group_text: str = ""
    ) -> None:
        """Sets the widget at the specified row and column

        Args:
            row (int): The row index of the cell you want to set the widget for.
            col (int): The column index of the cell to set the widget for.
            widget (_qtpyBase_Control): The widget to be inserted into the grid
            group_text (str): The text that will be displayed in the group box
        """
        self._widget: qtW.QTableWidget

        assert (
            isinstance(row, int) and row == -1 or row >= 0
        ), f"{row=}. Must be an int == -1 or int >= 0"
        assert (
            isinstance(col, int) and col == -1 or col >= 0
        ), f"{col=}. Must be an int == -1 or int >= 0"
        assert isinstance(
            widget, _qtpyBase_Control
        ), f"{widget=}. Must be an instance of _qtpyBase_Control"
        assert isinstance(group_text, str), f"{group_text=}. Must be str"

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        row_index, col_index = self._rowcol_validate(row, col)

        if row_index >= self._widget.rowCount():
            row_index = self.row_append

        widget.tag = f"{row}|{widget.tag}"

        rowcol_widget = widget._create_widget(
            parent_app=self.parent_app,
            parent=self._widget,
            container_tag=self.container_tag,
        )

        item = self._widget.item(row_index, col_index)

        assert (
            rowcol_widget is not None and item is not None
        ), f"Dev Error {rowcol_widget=} {item=}"

        item_data = item.data(qtC.Qt.UserRole)

        item_data = item_data.replace(
            current_value=item_data.current_value,
            prev_value=item_data.prev_value,
            data_type=item_data.data_type,
            user_data=item_data.user_data,
            widget=widget,
        )

        item.setData(qtC.Qt.UserRole, item_data)

        model = self._widget.model()

        size = self.pixel_char_size(char_height=1, char_width=1)

        assert (
            widget.width > 0 and widget.height > 0
        ), f"Dev Error {widget.width=} {widget.height=} Must be > 0"

        rowcol_widget.setFixedSize(
            (widget.width * size.width), (widget.height * size.height)
        )

        self._widget.setRowHeight(row_index, widget.height * size.height)

        self._widget.setColumnWidth(col_index, widget.width * size.width)
        self._widget.setIndexWidget(model.index(row_index, col_index), rowcol_widget)

    # ----------------------------------------------------------------------------#
    #      Class Private Methods                                                  #
    # ----------------------------------------------------------------------------#
    def _rowcol_validate(self, row: int, col: Union[str, int]) -> tuple[int, int]:
        """
        Validates the row and column references in the grid.

        Args:
            row (int): Row index reference
            col (Union[str, int]): Column index or tag reference

        Returns:
            tuple[int, int]: The validated row and column indices

        """
        if self._widget is None:
            raise RuntimeError("_widget is not set")

        col_index = -1

        assert (
            isinstance(row, int) and row == -1 or (0 <= row <= self._widget.rowCount())
        ), f"row must be an int == -1 or between 0 and {self._widget.rowCount()}"

        if isinstance(col, int):
            col_index = col
        elif isinstance(col, str):
            col_index = self.colindex_get(col)
        else:
            raise AssertionError("col must be an int or a str")

        assert (
            -1 <= col_index < self._widget.columnCount()
        ), f"col must be an int == -1 or between 0 and {self._widget.columnCount()}"

        return row, col_index

    @overload
    def _data_type_decode(self, data_type: _Data_Type, value: str) -> int:
        ...

    @overload
    def _data_type_decode(self, data_type: _Data_Type, value: str) -> float:
        ...

    @overload
    def _data_type_decode(self, data_type: _Data_Type, value: str) -> bool:
        ...

    @overload
    def _data_type_decode(self, data_type: _Data_Type, value: str) -> str:
        ...

    @overload
    def _data_type_decode(self, data_type: _Data_Type, value: str) -> qtC.QDate:
        ...

    @overload
    def _data_type_decode(self, data_type: _Data_Type, value: str) -> qtC.QDateTime:
        ...

    def _data_type_decode(
        self, data_type: _Data_Type, value: str
    ) -> qtC.QDate | qtC.QDateTime | float | int | str | bool:
        """Casts a string value to the selected data_type - Ref: _data_type_encode

        Args:
            data_type (self._DATA_TYPE): The data type the value string will be cast to
            value (str ): THe str value to be cast as the _DATA_TYPE

        Returns:
            Union[int,float,bool,str,qtC.QDate,qtC.QDateTime]: value cast to the correct type
        """
        assert isinstance(value, str), f"{value=}. Must be a str"
        assert isinstance(
            data_type, (self._Data_Type, int)
        ), "data_type is enumerated data_type or an int index into data_type"

        match data_type:
            case self._Data_Type.BOOL:  # bool
                if value == "True" or value == "T":
                    return True
                else:
                    return False
            case self._Data_Type.DATE:
                locale = qtC.QLocale()
                return qtC.QDate.fromString(
                    str(value), locale.dateFormat(qtC.QLocale.ShortFormat)
                )
            case self._Data_Type.DATETIME:
                locale = qtC.QLocale()
                return qtC.QDateTime.fromString(
                    str(value), locale.dateTimeFormat(qtC.QLocale.ShortFormat)
                )
            case self._Data_Type.FLOAT:
                return float(value)
            case self._Data_Type.INT:
                return int(value)
            case self._Data_Type.STR:
                return value

    def _data_type_encode(self, value: any) -> _Data_Type:
        """Returns an  enumerated data_type (_DATA_TYPE) for a given value - Ref: _data_type_decode

        Args:
            value: any
        Returns:
            _DATA_TYPE : Value cast as the selected datatype
        """
        match value:
            case bool():
                return self._Data_Type.BOOL
            case datetime.date():
                return self._Data_Type.DATE
            case datetime.datetime():
                return self._Data_Type.DATETIME
            case float():
                return self._Data_Type.FLOAT
            case int():
                return self._Data_Type.INT
            case str():
                return self._Data_Type.STR


class _Image(qtW.QGraphicsView):
    """A QGraphicsView subclass override that allows for mouse click events over images to be captured and processed"""

    draw = False
    left = -1
    top = -1
    width = -1
    height = -1
    flag = False
    clicked = qtC.Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

        self.draw = False
        self.parent = parent

    def paintEvent(self, event: qtG.QPaintEvent) -> None:
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:
        # self.clicked.emit()
        super().mousePressEvent(event)


class _Resizable_Rectangle(qtW.QGraphicsRectItem):
    """This class instantiates a resizeable rectangle that only moves within the bounds of the scene."""

    EDGE = IntEnum("EDGE", "LEFT,RIGHT,TOP,BOTTOM,NONE")
    HANDLE = IntEnum(
        "HANDLE",
        "TOP_LEFT,TOP_MIDDLE,TOP_RIGHT,MIDDLE_LEFT,MIDDLE_RIGHT,BOTTOM_LEFT,BOTTOM_MIDDLE,BOTTOM_RIGHT,NONE",
    )

    colour: str = ""
    handle_size: float = +8.0
    handle_space: float = -4.0

    handle_cursors = {
        HANDLE.TOP_LEFT: qtC.Qt.SizeFDiagCursor,
        HANDLE.TOP_MIDDLE: qtC.Qt.SizeVerCursor,
        HANDLE.TOP_RIGHT: qtC.Qt.SizeBDiagCursor,
        HANDLE.MIDDLE_LEFT: qtC.Qt.SizeHorCursor,
        HANDLE.MIDDLE_RIGHT: qtC.Qt.SizeHorCursor,
        HANDLE.BOTTOM_LEFT: qtC.Qt.SizeBDiagCursor,
        HANDLE.BOTTOM_MIDDLE: qtC.Qt.SizeVerCursor,
        HANDLE.BOTTOM_RIGHT: qtC.Qt.SizeFDiagCursor,
    }

    def __init__(self, top: int, left: int, height: int, width: int, colour: str):
        """
        Initialise resizeable rect

        Args:
            top (int) : Top point of rectangle
            left (int): Left point of rectangle
            height (int): height of rectangle
            width (int):  Width of rectangle
            colour (int) : Colour of rectangle (Mostly HTML/CSS legal coulour strings)
        """
        super().__init__(top, left, height, width)

        self.colour = colour
        self.handles = {}
        self.handle_selected = self.HANDLE.NONE
        self.selected_edge = self.EDGE.NONE
        self.click_rect = None
        self.mouse_press_pos = None
        self.mouse_press_rect = None

        self.setAcceptHoverEvents(True)
        self.setFlag(qtW.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(qtW.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(qtW.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(qtW.QGraphicsItem.ItemIsFocusable, True)

        self.update_handles_pos()

    def handle_at(self, point: qtC.QPointF):
        """
        Returns the resize handle below the given point.

        Args:
            point (qtC.QPointF): Provided point
        """
        for key, value in self.handles.items():
            if value.contains(point):
                return key

    def hoverMoveEvent(self, event: qtW.QGraphicsSceneHoverEvent) -> None:
        """
        Processes mouse hovering over the shape when not pressed.

        Args:
            event (qtW.QGraphicsSceneHoverEvent): Triggered when the hovering mouse moves over rectangle
        """
        # if self.isSelected(): # Better to not have to click on the beast before resizing
        handle = self.handle_at(event.pos())
        cursor = qtC.Qt.ArrowCursor if handle is None else self.handle_cursors[handle]
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: qtW.QGraphicsSceneHoverEvent) -> None:
        """
        Processes the hovering mouse leaving the shape when not pressed .

        Args:
            event (qtW.QGraphicsSceneHoverEvent): Triggered when the mouse leaves the rectangle
        """
        self.setCursor(qtC.Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: qtW.QGraphicsSceneMouseEvent) -> None:
        """
        Process a mouse button been pressed over the shape.

        Args:
            event (qtW.QGraphicsSceneMouseEvent): Triggered when a mouse button is pressed
        """
        self.mouse_press_pos = event.pos()

        rect = self.rect()

        if abs(rect.left() - self.mouse_press_pos.x()) < 5:
            self.selected_edge = self.EDGE.LEFT
        elif abs(rect.right() - self.mouse_press_pos.x()) < 5:
            self.selected_edge = self.EDGE.RIGHT
        elif abs(rect.top() - self.mouse_press_pos.y()) < 5:
            self.selected_edge = self.EDGE.TOP
        elif abs(rect.bottom() - self.mouse_press_pos.y()) < 5:
            self.selected_edge = self.EDGE.BOTTOM
        else:
            self.selected_edge = self.EDGE.NONE

        self.click_rect = rect
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: qtW.QGraphicsSceneMouseEvent) -> None:
        """
        Processes mouse movements when the button is pressed

        Args:
            event (qtW.QGraphicsSceneMouseEvent): Triggered when the mouse moves
        """
        mouse_pos = event.pos()

        if self.handle_selected != self.HANDLE.NONE:
            self.interactive_resize(mouse_pos)
        else:
            x_diff = mouse_pos.x() - self.mouse_press_pos.x()
            y_diff = mouse_pos.y() - self.mouse_press_pos.y()

            # Rectangle as clicked.
            rect = qtC.QRectF(self.click_rect)

            # Adjust by the distance the mouse moved.
            if self.selected_edge == self.EDGE.NONE:
                rect.translate(x_diff, y_diff)
            elif self.selected_edge == self.EDGE.TOP:
                rect.adjust(0, y_diff, 0, 0)
            elif self.selected_edge == self.EDGE.LEFT:
                rect.adjust(x_diff, 0, 0, 0)
            elif self.selected_edge == self.EDGE.BOTTOM:
                rect.adjust(0, 0, 0, y_diff)
            elif self.selected_edge == self.EDGE.RIGHT:
                rect.adjust(0, 0, x_diff, 0)

            # Set limits of movement.
            scene_rect = self.scene().sceneRect()

            view_left = scene_rect.left()
            view_top = scene_rect.top()
            view_right = scene_rect.right()
            view_bottom = scene_rect.bottom()

            # Rectangle out of bounds check
            if rect.top() < view_top:
                if self.selected_edge == self.EDGE.NONE:
                    rect.translate(0, view_top - rect.top())
                else:
                    rect.setTop(view_top)
            if rect.left() < view_left:
                if self.selected_edge == self.EDGE.NONE:
                    rect.translate(view_left - rect.left(), 0)
                else:
                    rect.setLeft(view_left)
            if view_bottom < rect.bottom():
                if self.selected_edge == self.EDGE.NONE:
                    rect.translate(0, view_bottom - rect.bottom())
                else:
                    rect.setBottom(view_bottom)
            if view_right < rect.right():
                if self.selected_edge == self.EDGE.NONE:
                    rect.translate(view_right - rect.right(), 0)
                else:
                    rect.setRight(view_right)

            # Rectangle inside out check.
            if rect.width() < 5:
                if self.selected_edge == self.EDGE.LEFT:
                    rect.setLeft(rect.right() - 5)
                else:
                    rect.setRight(rect.left() + 5)
            if rect.height() < 5:
                if self.selected_edge == self.EDGE.TOP:
                    rect.setTop(rect.bottom() - 5)
                else:
                    rect.setBottom(rect.top() + 5)

            # Update the rect that is guaranteed to stay in bounds.
            self.setRect(rect)
            self.update_handles_pos()

    def mouseReleaseEvent(self, event: qtW.QGraphicsSceneMouseEvent) -> None:
        """
        Processed the released mouse button event

        Args:
            event (qtW.QGraphicsSceneMouseEvent): Triggered when mouse button released
        """
        super().mouseReleaseEvent(event)
        self.handle_selected = self.HANDLE.NONE
        self.mouse_press_pos = None
        self.mouse_press_rect = None
        self.update()

    def boundingRect(self):
        """
        Returns a shape bounding rect -including the resize handles
        """
        offset = self.handle_size + self.handle_space

        return self.rect().adjusted(-offset, -offset, offset, offset)

    def update_handles_pos(self):
        """
        Updates the current resize handles
        """
        handle_size = self.handle_size
        bounding_rect = self.boundingRect()
        self.handles[self.HANDLE.TOP_LEFT] = qtC.QRectF(
            bounding_rect.left(), bounding_rect.top(), handle_size, handle_size
        )
        self.handles[self.HANDLE.TOP_MIDDLE] = qtC.QRectF(
            bounding_rect.center().x() - handle_size / 2,
            bounding_rect.top(),
            handle_size,
            handle_size,
        )
        self.handles[self.HANDLE.TOP_RIGHT] = qtC.QRectF(
            bounding_rect.right() - handle_size,
            bounding_rect.top(),
            handle_size,
            handle_size,
        )
        self.handles[self.HANDLE.MIDDLE_LEFT] = qtC.QRectF(
            bounding_rect.left(),
            bounding_rect.center().y() - handle_size / 2,
            handle_size,
            handle_size,
        )
        self.handles[self.HANDLE.MIDDLE_RIGHT] = qtC.QRectF(
            bounding_rect.right() - handle_size,
            bounding_rect.center().y() - handle_size / 2,
            handle_size,
            handle_size,
        )
        self.handles[self.HANDLE.BOTTOM_LEFT] = qtC.QRectF(
            bounding_rect.left(),
            bounding_rect.bottom() - handle_size,
            handle_size,
            handle_size,
        )
        self.handles[self.HANDLE.BOTTOM_MIDDLE] = qtC.QRectF(
            bounding_rect.center().x() - handle_size / 2,
            bounding_rect.bottom() - handle_size,
            handle_size,
            handle_size,
        )
        self.handles[self.HANDLE.BOTTOM_RIGHT] = qtC.QRectF(
            bounding_rect.right() - handle_size,
            bounding_rect.bottom() - handle_size,
            handle_size,
            handle_size,
        )

    def interactive_resize(self, mouse_pos: qtC.QPointF) -> None:
        """
        Performs interactive resize.

        Args:
            mouse_pos (qtC.QPointF): The mouse position as a qtC.QPointF instance
        """
        offset = self.handle_size + self.handle_space
        bounding_rect = self.boundingRect()
        rect = self.rect()
        diff = qtC.QPointF(0, 0)

        self.prepareGeometryChange()

        if self.handle_selected == self.HANDLE.TOP_LEFT:
            from_x = self.mouse_press_rect.left()
            from_y = self.mouse_press_rect.top()
            to_x = from_x + mouse_pos.x() - self.mouse_press_pos.x()
            to_y = from_y + mouse_pos.y() - self.mouse_press_pos.y()
            diff.setX(to_x - from_x)
            diff.setY(to_y - from_y)
            bounding_rect.setLeft(to_x)
            bounding_rect.setTop(to_y)
            rect.setLeft(bounding_rect.left() + offset)
            rect.setTop(bounding_rect.top() + offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.TOP_MIDDLE:
            from_y = self.mouse_press_rect.top()
            to_y = from_y + mouse_pos.y() - self.mouse_press_pos.y()
            diff.setY(to_y - from_y)
            bounding_rect.setTop(to_y)
            rect.setTop(bounding_rect.top() + offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.TOP_RIGHT:
            from_x = self.mouse_press_rect.right()
            from_y = self.mouse_press_rect.top()
            to_x = from_x + mouse_pos.x() - self.mouse_press_pos.x()
            to_y = from_y + mouse_pos.y() - self.mouse_press_pos.y()
            diff.setX(to_x - from_x)
            diff.setY(to_y - from_y)
            bounding_rect.setRight(to_x)
            bounding_rect.setTop(to_y)
            rect.setRight(bounding_rect.right() - offset)
            rect.setTop(bounding_rect.top() + offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.MIDDLE_LEFT:
            from_x = self.mouse_press_rect.left()
            to_x = from_x + mouse_pos.x() - self.mouse_press_pos.x()
            diff.setX(to_x - from_x)
            bounding_rect.setLeft(to_x)
            rect.setLeft(bounding_rect.left() + offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.MIDDLE_RIGHT:
            from_x = self.mouse_press_rect.right()
            to_x = from_x + mouse_pos.x() - self.mouse_press_pos.x()
            diff.setX(to_x - from_x)
            bounding_rect.setRight(to_x)
            rect.setRight(bounding_rect.right() - offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.BOTTOM_LEFT:
            from_x = self.mouse_press_rect.left()
            from_y = self.mouse_press_rect.bottom()
            to_x = from_x + mouse_pos.x() - self.mouse_press_pos.x()
            to_y = from_y + mouse_pos.y() - self.mouse_press_pos.y()
            diff.setX(to_x - from_x)
            diff.setY(to_y - from_y)
            bounding_rect.setLeft(to_x)
            bounding_rect.setBottom(to_y)
            rect.setLeft(bounding_rect.left() + offset)
            rect.setBottom(bounding_rect.bottom() - offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.BOTTOM_MIDDLE:
            from_y = self.mouse_press_rect.bottom()
            to_y = from_y + mouse_pos.y() - self.mouse_press_pos.y()
            diff.setY(to_y - from_y)
            bounding_rect.setBottom(to_y)
            rect.setBottom(bounding_rect.bottom() - offset)
            self.setRect(rect)

        elif self.handle_selected == self.HANDLE.BOTTOM_RIGHT:
            from_x = self.mouse_press_rect.right()
            from_y = self.mouse_press_rect.bottom()
            to_x = from_x + mouse_pos.x() - self.mouse_press_pos.x()
            to_y = from_y + mouse_pos.y() - self.mouse_press_pos.y()
            diff.setX(to_x - from_x)
            diff.setY(to_y - from_y)
            bounding_rect.setRight(to_x)
            bounding_rect.setBottom(to_y)
            rect.setRight(bounding_rect.right() - offset)
            rect.setBottom(bounding_rect.bottom() - offset)
            self.setRect(rect)

        self.update_handles_pos()

    def shape(self) -> qtG.QPainterPath:
        """
        Returns the shape of this item as a QPainterPath in local coordinates.
        """
        path = qtG.QPainterPath()
        path.addRect(self.rect())
        if self.isSelected():
            for shape in self.handles.values():
                path.addEllipse(shape)
        return path

    def paint(
        self,
        painter: qtG.QPainter,
        option: qtW.QStyleOptionGraphicsItem,
        widget: Optional[qtW.QWidget] = None,
    ):
        """Paints the rectangle. Overrides ancestor

        Args:
            painter (qtG.QPainter): Painter used for drawing rectangle
            option (qtW.QStyleOptionGraphicsItem): Not used
            widget (Optional[qtW.QWidget]): Not Used
        """
        # Flood fill Sizing Rect
        flood_fill_colour = qtG.QColor(self.colour)
        flood_fill_colour.setAlpha(20)
        painter.setBrush(
            qtG.QBrush(flood_fill_colour)
        )  # qtG.QColor(self.colour, 100)))

        # Sizing rectangle boundary line
        painter.setPen(qtG.QPen(qtG.QColor(self.colour), 1.0, qtC.Qt.SolidLine))
        painter.drawRect(self.rect())

        # Handle dots on the boundary line
        painter.setRenderHint(qtG.QPainter.Antialiasing)
        painter.setBrush(qtG.QBrush(self.colour))
        painter.setPen(
            qtG.QPen(
                qtG.QColor(self.colour),
                1.0,
                qtC.Qt.SolidLine,
                qtC.Qt.RoundCap,
                qtC.Qt.RoundJoin,
            )
        )

        for handle, rect in self.handles.items():
            if (
                self.handle_selected == self.HANDLE.NONE
                or handle == self.handle_selected
            ):
                painter.drawEllipse(rect)


@dataclasses.dataclass
class Image(_qtpyBase_Control):
    # Class that instantiates an  image and its associated properties
    @dataclasses.dataclass
    class rect_cords:
        rect_id: str
        left: int
        top: int
        width: int
        height: int

    image: Optional[Union[str, qtG.QPixmap]] = None
    rotate_degrees: int = 0
    cached_height: int = -1
    cached_width: int = -1
    size_fixed = False

    _cached_pixmap: Optional[qtG.QPixmap] = None
    _pix_width: int = -1
    _pix_height: int = -1
    _user_items: dict[str:_Resizable_Rectangle] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Constructor that checks arguments and sets defaults"""
        super().__post_init__()

        assert isinstance(
            self.image, (type(None), str, qtG.QPixmap)
        ), f"{self.image=}. Must Be None. str (file_path/file_name) or QPixmap"

        assert (
            self.height >= 1 or self.height == -1
        ), f"{self.height=} must be >= 1 or -1 (auto-calc)"

        assert (
            self.width >= 1 or self.width == -1
        ), f"{self.width=} must be >= 1 or -1 (auto-calc)"

        assert (
            isinstance(self.rotate_degrees, int)
            and self.rotate_degrees in (-661, -662, -663, -664)
            or 0 <= abs(self.rotate_degrees) <= 360
        ), (  # TODO remove magic numbers
            f"{self.rotate_degrees=}. Must be int between +- 0 and 360 or in (-661,"
            " -662, -663, -664)"
        )

        assert isinstance(self.cached_height, int) and (
            self.cached_height > 0 or self.cached_height == -1
        ), f"{self.cached_height=}. Must be > 0 or -1 (do not cache)"
        assert isinstance(self.cached_width, int) and (
            self.cached_width > 0 or self.cached_width == -1
        ), f"{self.cached_width=}. Must be > 0 or -1 (do not cache)"

        if self.width == -1 and self.height == -1:
            self.width = 1
            self.height = 1
        elif self.width == -1 and self.height > 0:
            self.width = self.height
        elif self.width > 0 and self.height == -1:
            self.height = 1

        # print(f"AXXXX {self.height=} {self.width=}")
        # self.width = math.floor(scaled[0])
        # self.height = math.floor(scaled[1])
        # print(f"AXXXX {self.height=} {self.width=}")

        self._image_file = ""

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the widget.

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): str = The tag name of the container.

        Returns:
            QWidget : The created image widget.
        """

        # if self.height == -1:
        #   self.height = CHECKBOX_SIZE.height

        # if self.width == -1:
        # self.width = CHECKBOX_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Image
        self._widget.setScene(qtW.QGraphicsScene())
        self._widget.setAlignment(qtC.Qt.AlignVCenter | qtC.Qt.AlignHCenter)

        self._widget.setHorizontalScrollBarPolicy(qtC.Qt.ScrollBarAlwaysOff)
        self._widget.setVerticalScrollBarPolicy(qtC.Qt.ScrollBarAlwaysOff)

        if self.image is not None:
            self.image_set(
                image=self.image,
                height=self.height + self.tune_vsize,
                width=self.width + self.tune_hsize,
                rotate_degrees=self.rotate_degrees,
                cached_height=self.cached_height,
                cached_width=self.cached_width,
                pixel_unit=self.pixel_unit,
            )

        return widget

    def clear(self) -> None:
        """Clears the visible items from the image"""

        self._widget: _Image
        self.rectangle_delete()
        self._widget.scene().clear()

    def get_height_width(self) -> tuple[int, int]:
        """Returns the high and width of the image as a tuple of pixels.

        Returns:
            (tuple) : (Height,Width) in pixels
        """
        assert self._widget is not None, f"{self=}. Widget not set"

        self._widget: _Image

        return (self._pix_height, self._pix_width)

    def rectangle_coords_get(self, rect_id: str) -> rect_cords:
        """Returns an instance of rect_cords  containing the coordinates of a rectangle, given its id

        Args:
            rect_id (str): The ID of the rectangle.

        Returns:
            rect_cords : The coordinates of the rectangle.
                            - rect_id: str
                            - left: int
                            - top: int
                            - width: int
                            - height: int
        """
        assert (
            isinstance(rect_id, str) and rect_id.strip() != ""
        ), f"{rect_id=}. Must be non-empty str"

        if rect_id in self._user_items:
            return self.rect_cords(
                rect_id=rect_id,
                left=self._user_items[rect_id][1],
                top=self._user_items[rect_id][2],
                width=self._user_items[rect_id][3],
                height=self._user_items[rect_id][4],
            )
        return self.rect_cords(rect_id=rect_id, left=-1, top=-1, width=-1, height=-1)

    def rectangle_delete(self, rect_id: str = "") -> bool:
        """Deletes a specific rectangle if the rect_id is provided else deletes all the rectangles in the image

        Args:
            rect_id (str): THe rect_id of the rectangle to be deleted or "" if all rectangles are to be deleted.

        Returns (bool): True if rectangle deleted or False if rectangle not found
        """
        assert isinstance(rect_id, str), f"{rect_id=}. Must be str"

        found = False
        rect_id = rect_id.strip()

        if rect_id != "" and not rect_id in self._user_items:
            return False

        self._widget: _Image

        for image_rect_id, image_rect_tuple in copy.copy(
            reversed(self._user_items.items())
        ):
            rectangle: _Resizable_Rectangle = image_rect_tuple[0]

            if rect_id == "" or rect_id == image_rect_id:
                found = True
                self._widget.scene().removeItem(rectangle)
                self._user_items.pop(image_rect_id)
                if rect_id == image_rect_id:
                    break

        return found

    def rectangle_draw(
        self,
        item_id: str,
        top: int,
        left: int,
        width: int = -1,
        height: int = -1,
        colour: str = "red",
        visible: bool = True,
    ) -> None:
        """Draws a rectangle on the currently loaded image

        Args:
            top (int): Top position in pixels
            left (int):  Left position in pixels
            width (int):  Width of rectangle in pixels
            height (int): Height iof rectangle in pixels
            colour (str): Colour of rectangle line (mostly legal HTML colours)
        """
        assert (
            isinstance(item_id, str) and item_id.strip() != ""
        ), f"{item_id=}. Must be non-empty str"
        assert isinstance(left, int) and left >= 0, f"{left}. Must be int > 0"
        assert isinstance(top, int) and top >= 0, f"{top}. Must be int > 0"
        assert (
            isinstance(width, int) and width > 0 or width == -1
        ), f"{width}. Must be int > 0"
        assert (
            isinstance(height, int) and height > 0 or height == -1
        ), f"{height}. Must be int > 0"

        assert (
            isinstance(colour, str) and colour.islower() and colour.strip != ()
        ), f"{colour=}. Must be non=empty lowercase str"

        assert (
            colour.strip() in qtG.QColor.colorNames()
        ), f"{colour=}. Not a valid colour \n {qtG.QColor.colorNames()}"

        assert isinstance(visible, bool), f"{visible=}. Must be bool"

        if height == -1:
            height = top + 50

        if width == -1:
            width = left + 20

        self._widget: _Image

        self._widget.left = left
        self._widget.top = top
        self._widget.width = width
        self._widget.height = height

        # TODO Currently draws a moveable resizeable rectangle - maybe that should only happen if unlocked
        rect_item = _Resizable_Rectangle(left, top, width, height, colour)
        rect_item.setPen(qtG.QPen(qtG.QColor(colour), 2, qtG.Qt.SolidLine))
        rect_item.setVisible(visible)
        rect_item.setFlag(qtW.QGraphicsItem.ItemIsMovable, True)

        self._user_items[item_id] = (rect_item, left, top, width, height)

        self._widget.scene().addItem(rect_item)

    def rectangle_show(
        self, rect_id: str, visible: bool, suppress_rect_check: bool = False
    ) -> None:
        """Show/Hides a rectangle that has been placed into the image depending on the value of visible.

        Args:
            rect_id (str): The id of the rectangle that will be shown/hidden depending on visible
            visible (bool) : True shows the rectangle, False hides the rectangle
            suppress_rect_check (bool): Used for debugging, suppresses the assert for checking if a rect_id is in the image
        """
        assert (
            isinstance(rect_id, str) and rect_id.strip() != ""
        ), f"{rect_id=}. Must be non-empty str"

        assert isinstance(
            suppress_rect_check, bool
        ), f"{suppress_rect_check=}. Must be bool"

        if not suppress_rect_check:
            assert rect_id in self._user_items, f"{rect_id=}. Not in scene"
        assert isinstance(visible, bool), f"{visible=}. Must be bool"

        if rect_id in self._user_items:
            rectangle: _Resizable_Rectangle = self._user_items[rect_id][0]
            rectangle.setVisible(visible)

    def rectangles_changed(self) -> dict[str, Rect_Changed]:
        """Returns a dict of changed rectangles

        Returns:
            dict[str,RECT_CHANGED] : Dict of changed rectangles.
        """
        changed_rectangles = {}

        for rect_id, rect_tuple in self._user_items.items():
            rectangle: _Resizable_Rectangle = rect_tuple[0]

            if round(rectangle.rect().left()) != round(rect_tuple[1]):
                changed_rectangles[rect_id] = Rect_Changed(
                    rect_id=rect_id,
                    coords=Coords(
                        left=round(rectangle.rect().left()),
                        top=round(rectangle.rect().top()),
                        width=round(rectangle.rect().width()),
                        height=round(round(rectangle.rect().height())),
                    ),
                )
            elif round(rectangle.rect().top()) != round(rect_tuple[2]):
                changed_rectangles[rect_id] = Rect_Changed(
                    rect_id=rect_id,
                    coords=Coords(
                        left=round(rectangle.rect().left()),
                        top=round(rectangle.rect().top()),
                        width=round(rectangle.rect().width()),
                        height=round(round(rectangle.rect().height())),
                    ),
                )
            elif round(rectangle.rect().width()) != round(rect_tuple[3]):
                changed_rectangles[rect_id] = Rect_Changed(
                    rect_id=rect_id,
                    coords=Coords(
                        left=round(rectangle.rect().left()),
                        top=round(rectangle.rect().top()),
                        width=round(rectangle.rect().width()),
                        height=round(round(rectangle.rect().height())),
                    ),
                )
            elif round(rectangle.rect().height()) != round(rect_tuple[4]):
                changed_rectangles[rect_id] = Rect_Changed(
                    rect_id=rect_id,
                    coords=Coords(
                        left=round(rectangle.rect().left()),
                        top=round(rectangle.rect().top()),
                        width=round(rectangle.rect().width()),
                        height=round(round(rectangle.rect().height())),
                    ),
                )
        return changed_rectangles

    def rectangle_id_change(self, old_id: str, new_id: str) -> None:
        """Updates the rectangle id

        Args:
            old_id (str): The old rectangle_id
            new_id (str): The new rectangle_id
        """
        assert (
            isinstance(old_id, str) and old_id.strip() != ""
        ), f"{old_id=}. Must be non-empty str"

        assert (
            isinstance(new_id, str) and new_id.strip() != ""
        ), f"{new_id=}. Must be non-empty str"

        if old_id in self._user_items:
            self._user_items[new_id] = copy.copy(self._user_items[old_id])
            self._user_items.pop(old_id)

    def rectangle_overlaps(self, overlap_ratio: float = 0.3) -> tuple[Overlap_Rect]:
        """Returns a tuple of overlapping rectangles

        Args:
            overlap_ratio: The ratio to determine overlapping. 0 - No overlap to 1 - Complete overlap

        Returns:
            tuple[Overlap_Rect] : A tuple containing the ids and coords of overlapping rectangles.
        """
        self._widget: _Image

        overlapping_rectangles = []
        for a_rect_id, a_rect_tuple in self._user_items.items():
            for b_rect_id, b_rect_tuple in self._user_items.items():
                if a_rect_id == b_rect_id or [
                    item
                    for item in overlapping_rectangles
                    if item.b_rect_id == a_rect_id
                ]:  # Same rectangle or rectangle already included in list, skip
                    continue

                a_rectangle: _Resizable_Rectangle = a_rect_tuple[0]
                b_rectangle: _Resizable_Rectangle = b_rect_tuple[0]
                a_Cords = Coords(
                    left=round(a_rectangle.rect().left()),
                    top=round(a_rectangle.rect().top()),
                    width=round(a_rectangle.rect().width()),
                    height=round(round(a_rectangle.rect().height())),
                )

                b_Cords = Coords(
                    left=round(b_rectangle.rect().left()),
                    top=round(b_rectangle.rect().top()),
                    width=round(b_rectangle.rect().width()),
                    height=round(round(b_rectangle.rect().height())),
                )
                if a_Cords.overlaps(other_cords=b_Cords, overlap_ratio=overlap_ratio):
                    overlapping_rectangles.append(
                        Overlap_Rect(
                            a_rect_id=a_rect_id,
                            a_coords=a_Cords,
                            b_rect_id=b_rect_id,
                            b_coords=b_Cords,
                        )
                    )

        return tuple(overlapping_rectangles)

    @property
    def image_cache_get(self) -> Optional[qtG.QPixmap]:
        """Returns the cached image

        Returns:
            (Optional[qtG.QPixmap]): The cached image if it has been set
        """
        return self._cached_pixmap

    @property
    def image_file_get(self) -> str:
        """

        Returns:
            (str) : The name of the source file - includes the path if provided

        """
        return self._image_file

    def image_cache_set(self, image: qtG.QPixmap) -> None:
        """Sets a cached image - used to speed things up if we do not want to load the image again

        Args:
            image (qtG.QPixmap) : The image to be cached.
        """
        assert isinstance(image, qtG.QPixmap), f"{image=}. Must be a QPixmap"

        if not isinstance(image, qtG.QPixmap):
            raise RuntimeError(f"{image=}. Cannot be None")

        self._widget: _Image

        self._cached_pixmap = image
        self._pix_width = self._cached_pixmap.width()
        self._pix_height = self._cached_pixmap.height()

        self.rectangle_delete()
        self._widget.setContentsMargins(0, 0, 0, 0)
        self._widget.scene().clear()
        self._widget.scene().setSceneRect(0, 0, self._pix_width, self._pix_height)

        self._widget.scene().addItem(qtW.QGraphicsPixmapItem(self._cached_pixmap))

    def clip_get(
        self, x: int, y: int, width: int, height: int
    ) -> Optional[qtG.QPixmap]:
        """Returns a QPixmap clip of the image at the given coordinates of the given size

        Args:
            x (int): The x coordinate of the left corner of the rectangle to be clipped.
            y (int): The y coordinate of top of the rectangle to be clipped.
            width (int): The width of the image to be clipped.
            height (int): The height of the image to be clipped.

        Returns:
            QPixmap : A QPixmap clipped image.
        """
        self._widget: _Image

        assert (
            isinstance(x, int) and 0 < x < self._widget.scene().width()
        ), f"{x=}. Must be > 0 and < {self._widget.scene().width()}"
        assert (
            isinstance(y, int) and 0 < y < self._widget.scene().height()
        ), f"{y=}. Must be > 0 and < {self._widget.scene().height()}"

        assert isinstance(height, int) and height > 0, f"{height=}. Must be > 0"
        assert isinstance(width, int) and width > 0, f"{width=}. Must be > 0"

        # Should not happen but if it does clip to the edge of the image
        if width + x > self._widget.scene().width():
            width = self._widget.scene().width() - x

        if height + y > self._widget.scene().height():
            height = self._widget.scene().height() - y

        self._widget: _Image
        for child in self._widget.scene().items():
            if isinstance(child, qtW.QGraphicsPixmapItem):
                child: qtW.QGraphicsPixmapItem
                return qtG.QPixmap.fromImage(
                    child.pixmap()
                    .copy(x, y, width, height)
                    .toImage()
                    .convertToFormat(qtG.QImage.Format_RGB32)
                )
        return None

    def numpy_array_get(
        self, dlib: bool = False
    ) -> Optional[tuple[int, int, np.ndarray]]:
        """Generates an RGB numpy array suited for dlib (and other libs I imagine) type operations

        Returns (Optional[tuple[int, int, np.ndarray]]): The tuple  (image height (pixels),image width (pixels),
        np.ndarray). The last element is the RGB numpy array that represents the pixmap that is displayed.  Assumes
        only one image is displayed!

        """
        self._widget: _Image
        for child in self._widget.scene().items():
            if isinstance(child, qtW.QGraphicsPixmapItem):
                child: qtW.QGraphicsPixmapItem
                if dlib:
                    # Convert monochrome or colour images to 32bit RGB color - includes alpha channel (4 * 8 = 32). I
                    # could not find a way in QT to avoid the numpy gymnastics below - cost ~ 8MB!
                    image = (
                        child.pixmap()
                        .toImage()
                        .convertToFormat(qtG.QImage.Format_RGB32)
                    )
                    height = image.height()
                    width = image.width()

                    img_size = image.size()
                    buffer = image.constBits()

                    n_bits_buffer = len(buffer) * 8
                    n_bits_image = img_size.width() * img_size.height() * image.depth()

                    # Dev Debug check
                    assert (
                        n_bits_buffer == n_bits_image
                    ), f"DBG Dev size mismatch: {n_bits_buffer=} != {n_bits_image=}"
                    assert (
                        image.depth() == 32
                    ), f"DBG Dev unexpected image depth: {image.depth()}"

                    # Note: image.depth() // 8 because alpha channel makes 4 (rgb and alpha)*8 = 32..
                    np_array = np.ndarray(
                        shape=(img_size.height(), img_size.width(), image.depth() // 8),
                        buffer=buffer,
                        dtype=np.uint8,
                    )

                    # Not sharing memory with copy! I think doing this np slice/dice cuts off the alpha channel and this
                    # means we do not need cv2.cvtColor and the 50 odd MB of files it brings to the show!
                    return (height, width, np_array[:, :, :3].copy())
                else:
                    image = (
                        child.pixmap()
                        .toImage()
                        .convertToFormat(qtG.QImage.Format_RGB32)
                    )

                    ba = qtC.QByteArray()
                    buffer = qtC.QBuffer(ba)
                    buffer.open(qtC.QIODevice.WriteOnly)
                    image.save(buffer, "BMP")

                    height = image.height()
                    width = image.width()

                    np_array = np.asarray(bytearray(buffer.data()), dtype="uint8")

                    return (height, width, np_array.copy())
        return None

    def image_set(
        self,
        image: str | qtG.QPixmap | bytes,
        height: int = -1,
        width: int = -1,
        scaled: bool = True,
        high_quality: bool = False,
        rotate_degrees: int = 0,
        cached_height: int = -1,
        cached_width: int = -1,
        pixel_unit=False,
    ) -> None:
        """Sets an image to be displayed in this control

        Args:
            image (str| qtG.QPixmap| bytes): Image to be displayed
            height (int): Height of image. -1 : scaled to height
            width (int):  Width of image. -1 : scaled to width
            scaled (bool):  Scale the image to fit height and width
            high_quality (bool): Display image in high quality
            rotate_degrees (int): Rotate the image in degrees
            cached_height (int): Create a cached image of a specific height. Aspect ration always maintained
            cached_width (int):Create a cached image of a specific width. Aspect ration always maintained
            pixel_unit (bool): True if working with pixel sizing, False if working with char sizing


        """
        self._widget: _Image

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(
            image, (str, qtG.QPixmap, bytes)
        ), f"{image=}. Must Be str (file_path/file_name) or QPixmap"
        assert isinstance(height, int) and (
            height > 0 or height == -1
        ), f"{height=}. Must be > 0 or -1 (auto-calc)"
        assert isinstance(width, int) and (
            width > 0 or width == -1
        ), f"{width=}. Must be > 0 or -1 (auto-calc)"
        assert isinstance(scaled, bool), f"{scaled=}. Must Be bool"
        assert isinstance(high_quality, bool), f"{high_quality=}. Must Be bool"
        assert isinstance(rotate_degrees, int), f"{rotate_degrees=}. Must be int"
        assert isinstance(cached_height, int) and (
            cached_height > 0 or cached_height == -1
        ), f"{cached_height=}. Must be > 0 or -1 (do not cache)"
        assert isinstance(cached_width, int) and (
            cached_width > 0 or cached_width == -1
        ), f"{cached_width=}. Must be > 0 or -1 (do not cache)"

        if height == -1:
            height = self.height

        if width == -1:
            width = self.width

        if pixel_unit:
            pass
        else:
            char_pixel_size = self.pixel_char_size(char_height=1, char_width=1)

            height = char_pixel_size.height * height
            width = char_pixel_size.width * width

        if isinstance(image, str):  # Attempt to load from file!
            assert qtC.QFile.exists(image), image + " : does not exist!"

            image_reader = qtG.QImageReader()
            # image_reader.setScaledSize(qtC.QSize(width,height))
            image_reader.setAllocationLimit(1000)
            image_reader.setFileName(image)

            pixmap = qtG.QPixmap.fromImageReader(image_reader)
            self._image_file = image
        elif isinstance(image, bytes):
            self._image_file = ""
            pixmap = qtG.QPixmap()
            pixmap.loadFromData(image)

        else:
            self._image_file = ""
            pixmap = image

        if isinstance(pixmap, qtG.QPixmap):  # Image is ok as is
            if cached_height > 0 and cached_width > 0:
                if pixel_unit:
                    pass
                else:
                    char_pixel_size = self.pixel_char_size(char_height=1, char_width=1)

                    cached_height = (
                        char_pixel_size.height * cached_height
                    )  # - 5 if height > 0 else height
                    cached_width = (
                        char_pixel_size.width * cached_width
                    )  # - 5 if width > 0 else width

                if self.cached_width == -1:
                    self._cached_pixmap = pixmap.scaledToHeight(
                        cached_height,
                        (
                            qtC.Qt.SmoothTransformation
                            if high_quality
                            else qtC.Qt.FastTransformation
                        ),
                    )

                elif self.cached_height == -1:
                    self._cached_pixmap = pixmap.scaledToWidth(
                        cached_width,
                        (
                            qtC.Qt.SmoothTransformation
                            if high_quality
                            else qtC.Qt.FastTransformation
                        ),
                    )
                else:
                    self._cached_pixmap = pixmap.scaled(
                        cached_width,
                        cached_height,
                        qtC.Qt.KeepAspectRatio,
                        (
                            qtC.Qt.SmoothTransformation
                            if high_quality
                            else qtC.Qt.FastTransformation
                        ),
                    )

            if self.height == -1:
                pixmap = pixmap.scaledToWidth(
                    width,
                    (
                        qtC.Qt.SmoothTransformation
                        if high_quality
                        else qtC.Qt.FastTransformation
                    ),
                )

                # self.height = pixmap.height()

            elif self.width == -1:
                pixmap = pixmap.scaledToHeight(
                    height,
                    (
                        qtC.Qt.SmoothTransformation
                        if high_quality
                        else qtC.Qt.FastTransformation
                    ),
                )

                # self.width = pixmap.width()
            else:
                pixmap = pixmap.scaled(
                    width,
                    height,
                    qtC.Qt.KeepAspectRatio,
                    (
                        qtC.Qt.SmoothTransformation
                        if high_quality
                        else qtC.Qt.FastTransformation
                    ),
                )

            if rotate_degrees != 0:
                if rotate_degrees == -661:  # Mirror Horizontal
                    if self._cached_pixmap is not None:
                        cached_piximage = self._cached_pixmap.toImage().mirror(
                            True, False
                        )
                        self._cached_pixmap.convertFromImage(cached_piximage)

                    piximage = pixmap.toImage().mirror(True, False)
                    pixmap.convertFromImage(piximage)
                elif rotate_degrees == -662:  # Mirror vertical
                    if self._cached_pixmap is not None:
                        cached_piximage = self._cached_pixmap.toImage().mirror(
                            False, True
                        )
                        self._cached_pixmap.convertFromImage(cached_piximage)

                    piximage = pixmap.toImage().mirror(False, True)
                    pixmap.convertFromImage(piximage)
                elif rotate_degrees == -663:  # Mirror Horizontal And Rotate 270 CW
                    if self._cached_pixmap is not None:
                        cached_piximage = (
                            self._cached_pixmap.transformed(
                                qtG.QTransform().rotate(270)
                            )
                            .toImage()
                            .mirror(True, False)
                        )
                        self._cached_pixmap.convertFromImage(cached_piximage)

                    piximage = (
                        pixmap.toImage()
                        .transformed(qtG.QTransform().rotate(270))
                        .toImage()
                        .mirror(True, False)
                    )
                    pixmap.convertFromImage(piximage)
                elif rotate_degrees == -664:  # "Mirror Vertical And Rotate 90 CW"
                    if self._cached_pixmap is not None:
                        cached_piximage = (
                            self._cached_pixmap.transformed(qtG.QTransform().rotate(90))
                            .toImage()
                            .mirror(False, True)
                        )
                        self._cached_pixmap.convertFromImage(cached_piximage)

                    piximage = (
                        pixmap.toImage()
                        .transformed(qtG.QTransform().rotate(270))
                        .toImage()
                        .mirror(False, True)
                    )
                    pixmap.convertFromImage(piximage)
                else:
                    if self._cached_pixmap is not None:
                        self._cached_pixmap = self._cached_pixmap.transformed(
                            qtG.QTransform().rotate(rotate_degrees)
                        )
                    pixmap = pixmap.transformed(qtG.QTransform().rotate(rotate_degrees))

            self._pix_width = pixmap.width()
            self._pix_height = pixmap.height()

            self.rectangle_delete()
            self._widget.scene().clear()
            self._widget.scene().setSceneRect(0, 0, self._pix_width, self._pix_height)

            self._widget.scene().addPixmap(pixmap)
            self._widget.setFixedSize(self._pix_width, self._pix_height)


@dataclasses.dataclass
class Label(_qtpyBase_Control):
    """Instantiates a label widget."""

    def __post_init__(self) -> None:
        super().__post_init__()

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the label widget

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): str = ""

        Returns:
            QWidget : The label widget or the container housing it.
        """
        # self.width = utils.amper_length(self.text.strip())

        if self.height <= 0:
            self.height = LINEEDIT_SIZE.height

        if self.width <= 0:
            self.width = LINEEDIT_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        return widget

    def value_get(self) -> str:
        """Returns the label text

        Returns:
            str: The label text

        """
        self._widget: qtW.QLabel
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        return self._widget.text()

    def value_set(self, value: str) -> None:
        """Sets the label text

        Args:
            value (str): text value to set in the label

        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(value, str), f"{value=}. Must be str"
        self._widget: qtW.QLabel
        self._widget.setText(self.trans_str(value))


@dataclasses.dataclass
class LCD(_qtpyBase_Control):
    """Instantiates an LCD like number display widget"""

    digit_count: int = 8
    txt_align: Align = Align.RIGHT

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets instance variables"""

        assert isinstance(self.digit_count, int), f"{self.digit_count=}. Must be int"

        super().__post_init__()

        if self.text.strip() == "":
            self.text = "0"

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the LCD widget

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): This is the container tag that will be used to identify the widget

        Returns:
            QWidget : The LCD widget or the container housing it.
        """

        if self.height == -1:
            self.height = BUTTON_SIZE.height

        if self.width == -1:
            self.width = BUTTON_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self._widget: qtW.QLCDNumber

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if self.text.strip() != "":
            self.value_set(self.text)

        self._widget.setSegmentStyle(qtW.QLCDNumber.Flat)

        self._widget.setDigitCount(self.digit_count)
        self._widget.setSmallDecimalPoint(False)

        return widget

    def value_set(self, value: Union[str, int, float]) -> None:
        """Sets the LCD number display

        Args:
            value (Union[str, int, float]): The value to be displayed in the LCD.

        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(
            value, (str, int, float)
        ), f"{value=} must be a str, int or float"

        self._widget: qtW.QLCDNumber

        if isinstance(value, str):  # Check if a valid number (0..9 or .)
            assert re.match(
                "^[0-9\.]*$", value.strip()
            ), f"{value=}. Must be a number"  # pylint: disable=W1401

        return self._widget.display(value)


class _Line_Edit(qtW.QLineEdit):
    """Subclasses a line edit widget to customises the key press and focus event handling"""

    event_ref = None
    owner_widget = None

    def __init__(self, parent, owner_widget) -> None:
        """Constructor that checks parameters and sets instance variables
        Args:
            parent: The parent widget.
            owner_widget: The widget that owns this dialog.
        """
        self.owner_widget = owner_widget
        super().__init__(parent)

    def event(self, event: qtC.QEvent) -> bool:
        """Event handler for the key press event.

        Args:
            event (QEvent): The event that was triggered.

        Returns:
            bool: True if the event was handled, False otherwise.ool
        """
        self.event_ref = event

        if event.type() == qtC.QEvent.Type.KeyPress:
            # TODO - Matbe tab should be processed separatly?
            if (
                event.key() == qtC.Qt.Key_Return
                or event.key() == qtC.Qt.Key_Tab
                or event.key() == qtC.Qt.Key_Down
            ):
                result = self.owner_widget._event_handler(Sys_Events.PRESSED)

                if result == -1:
                    return True  # Consumes Event as super not called
        elif event.type() == qtC.QEvent.Type.MouseButtonPress:
            result = self.owner_widget._event_handler(Sys_Events.CLICKED)

            if result == -1:
                return True  # Consumes Event as super not called

        super().event(event)

        return True

    def focusInEvent(self, *args) -> None:
        """Takes the focusInEvent from the QLineEdit and passes it to the owner QWidget"""
        self.owner_widget.focusInEvent(args)

    def focusOutEvent(self, *args) -> None:
        """Takes the focusOutEvent from the QLineEdit and passes it to the owner QWidget"""
        # print(f"@@@@@@> foe {args=}")
        self.owner_widget.focusOutEvent(args)


@dataclasses.dataclass
class LineEdit(_qtpyBase_Control):
    """Instantiates a LineEdit Widget and its associated properties"""

    width: int = LINEEDIT_SIZE.width
    height: int = LINEEDIT_SIZE.height
    input_mask: str = ""
    validate_callback: Optional[
        Union[types.FunctionType, types.MethodType, types.LambdaType]
    ] = None
    char_length: int = MAX_CHARS
    label_font: Optional[Font] = None
    txt_align: Align = Align.LEFT
    label_align: Align = Align.RIGHT
    widget_align: Align = Align.LEFT

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets instance variables"""
        super().__post_init__()

        self.original_value = ""
        self.total_width = 0

        # Note: text is used as line edit placeholder text

        assert isinstance(self.label, str), f"{self.label=}. Must be str"
        assert isinstance(self.input_mask, str), f"{self.input_mask=}. Must be str"
        assert self.label_font is None or isinstance(
            self.label_font, Font
        ), f"{self.label_font=}. Must be font"
        assert isinstance(self.char_length, int), f"{self.char_length=}. Must be int"
        assert isinstance(self.label_align, Align), f"{self.label_align}. Must be ALGN"
        assert self.validate_callback is None or callable(
            self.validate_callback
        ), f"{self.validate_callback=}. Must be None | Function | Method | Lambda"

        if self.label_font is None:
            self.label_fone = Font(size=DEFAULT_FONT_SIZE, weight=Font_Weight.NORMAL)

        self.mask = ""

        if len(self.input_mask) > self.width:
            self.width = len(self.input_mask)

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates a QLineEdit widget and sets the input mask and placeholder text

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): This is the tag that will be used to identify the widget in the HTML.

        Returns:
            QWidget : The LineEdit widget or the container that houses it.
        """
        self._widget: _Line_Edit

        if self.height == -1:
            self.height = LINEEDIT_SIZE.height

        if self.width == -1:
            self.width = LINEEDIT_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if self.input_mask is not None and self.input_mask.strip() != "":
            # Handle Password Masking
            if self.input_mask.startswith("@") or self.input_mask.startswith("*"):
                password_display = self.input_mask[0:1]
                self.input_mask = self.input_mask[1:]

                assert (
                    password_display == "@"
                    or password_display == "*"
                    or password_display.strip() == ""
                ), (
                    f"password_display char <{password_display}> must be first char of"
                    " mask."
                    + "Valid Chars Are '*': Echo mask chars only, '@' Echo char and"
                    " then mask the char"
                )

                if password_display == "*":
                    self._widget.setEchoMode(qtW.QLineEdit.Password)
                elif password_display == "@":
                    self._widget.setEchoMode(qtW.QLineEdit.PasswordEchoOnEdit)

        if self.input_mask is not None and self.input_mask.strip() != "":
            self.input_mask_set(self.input_mask)

        if len(self.text.strip()) > 0:
            self._widget.setPlaceholderText(self.text)

        return widget

    def _event_handler(
        self,
        *args,
    ) -> int:  # *arg catches any extra args passed to event
        """Event handler for the LineEdit Widget.

        Args:
            *args: Default arguments for this widget type

        Returns:
            int : 1. If the event is accepted, -1. If the event is rejected
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Line_Edit

        event: Sys_Events = args[0]

        if self.callback is not None:
            if event == Sys_Events.CURSORCHANGED:
                try:
                    value = (
                        self._widget.cursorPosition(),
                        self._widget.text()[self._widget.cursorPosition() - 1],
                    )
                except Exception as e:  # Hail Mary Pass
                    # Had very rare errors thrown in Line Edits and this is a fix
                    value = (self._widget.cursorPosition(), " ")
            elif event == Sys_Events.SELECTIONCHANGED:
                value = self._widget.selectedText()
            elif event == Sys_Events.PRESSED:
                if not self._widget.isModified():
                    self.original_value = self.value_get()
                    self._widget.setModified(True)

                value = self._widget.text()

            else:
                value = self._widget.text()

            if callable(self.callback):
                window_id = Get_Window_ID(self.parent_app, self.parent, self)

                if self.parent_app.widget_exist(
                    window_id=window_id, container_tag=self.container_tag, tag=self.tag
                ):
                    try:
                        return _Event_Handler(
                            parent_app=self.parent_app, parent=self
                        ).event(
                            window_id=window_id,
                            callback=self.callback,
                            action=event.name,
                            container_tag=self.container_tag,
                            tag=self.tag,
                            event=event,
                            value=value,
                            widget_dict=self.parent_app.widget_dict_get(
                                window_id=window_id, container_tag=self.container_tag
                            ),
                            control_name=self.__class__.__name__,
                            parent=self.parent_app.widget_get(
                                window_id=window_id,
                                container_tag=self.container_tag,
                                tag=self.tag,
                            ),
                        )
                    except Exception as e:
                        raise RuntimeError(f"Fatal Exception {e}")

        return 1

    def input_mask_set(self, input_mask) -> None:
        """Set the input mask.

        Args:
            input_mask: A string that defines the input mask.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Line_Edit

        assert (
            isinstance(input_mask, str) and input_mask != ""
        ), "input mask must be a non-empty string"

        # Note: if need a blank other than a space need to add ;<blank_char> at end of string
        # Note * and @ at start of mask are password masking chars
        valid_mask_chars = "AaNnXx90Dd#HhBb><![]{}\\-() "

        for index, char in enumerate(input_mask):
            assert (
                char in "*@" + valid_mask_chars if index == 0 else valid_mask_chars
            ), ("Input mask are these valid mask characters " + valid_mask_chars)

        if input_mask != "":
            self.mask = input_mask

            if self._widget is not None:
                self._widget.setInputMask(input_mask)

    @property
    def max_chars_get(self) -> int:
        """Returns the maximum number of characters allowed in the text field

        Returns:
            int :; The max number of characters allowed in the text field.
        """
        return self.char_length

    def max_chars_set(self, max_chars: int) -> None:
        """Sets the `char_length`  property and checks if is > 0 and < MAX_CHARS.

        Args:
            max_chars (int): The maximum number of characters to use in the line edit control.
        """
        assert (
            isinstance(max_chars, int) and 0 < max_chars <= MAX_CHARS
        ), f" 0 < max_chars <{max_chars}> <= {MAX_CHARS}"

        self.char_length = max_chars

    @property
    def modified(self) -> bool:
        """Returns the widget's modified status

        Returns:
            :bool: True - Modified, False - Not Modified
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Line_Edit

        return self._widget.isModified()

    def value_get(self, original_value: bool = False) -> str:
        """Gets the original taxt if `original_value` is `True otherwise the modified text  is returned


        Args:
            original_value (bool): True - Return original value, False return Modified value. Defaults to False

        Returns:
            str : original taxt if `original_value` is `True otherwise the modified text
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Line_Edit

        if original_value:
            return self.original_value
        else:
            return self._widget.text()

    def value_set(self, value: str) -> None:
        """Set the LineEdit widget text to the value string

        Args:
            value (str): The value to set.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Line_Edit

        assert isinstance(value, str), f"value <{value}> must be str"

        if not self._widget.isModified():
            self.original_value = self.value_get()
            self._widget.setModified(True)

        trans_text = self.trans_str(value)

        self._widget.setText(trans_text)

    @property
    def width_get(self) -> int:
        """Returns the value of the `total_width`instance variable

        Returns:
            The total width of the rectangle.
        """
        return self.total_width


@dataclasses.dataclass
class Menu_Element(_qtpyBase_Control):
    """Menu element is a menu control element added to the menu."""

    separator: bool = False

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets defaults"""
        super().__post_init__()

        assert self.width == -1, f"{self.width=}> is ignored by menus"
        assert self.height == -1, f"{self.height=}> is ignored by menus"


@dataclasses.dataclass
# The _Menu_Entry class is a class that is used to create a menu item in a menu
class _Menu_Entry(_qtpyBase_Control):
    """Class instance used  to store menu entry information"""

    parent_tag: str = ""
    tag: str = ""
    element: Menu_Element = None
    element_items: dict[str, any] = field(default_factory=dict)
    menu: Union[None, qtG.QAction] = None

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets defaults"""

        assert isinstance(
            self.menu, (type(None), qtG.QAction)
        ), f"{self.menu=}. Must be None or QAction "

    @property
    def checked_get(self) -> bool:
        """Returns a boolean value whether the menu item is checked or not

        Returns:
            bool : True - Menu Item Checked, False - Menu Item Not Checked
        """
        return self.guiwidget_get.isChecked()

    def checked_set(self, checked: bool) -> None:
        """Sets a menu item to checked or not checked

        Args:
            checked (bool): True - Check menu item, False - Uncheck Menu Item
        """
        assert isinstance(checked, bool), f"{checked=}. Must be bool"

        self.guiwidget_get.setCheckable(checked)


@dataclasses.dataclass
class Menu(_qtpyBase_Control):
    """Instantiates a Menu and associated properties"""

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets properties"""
        super().__post_init__()

        self._menu_items: dict[str, _Menu_Entry] = {}

        assert self.width == -1, f"{self.width=}> is ignored by menus"
        assert self.height == -1, f"{self.height=}> is ignored by menus"

    def _create_widget(
        self,
        parent_app: QtPyApp,
        parent: qtW.QWidget,
        container_tag: str,
        _menu: Union[dict[str, _Menu_Entry], None] = None,
        _depth: int = 0,
    ) -> qtW.QMenuBar:
        """Creates a menu bar widget

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag name of the container that the menu is in.
            _menu (Union[dict[str, _Menu_Entry], None]): This is the menu dictionary that is created. Not set by user
            _depth (int): Recursieve depth. Defaults to 0 and used for debugging.

        Returns:
            qtW.QMenuBar : The created widget or the container housing it.
        """
        if _menu is None or len(_menu) == 0:
            self._widget = qtW.QMenuBar()
            self._widget.setMinimumWidth(parent.width())
            _menu = self._menu_items

        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        for key in _menu.keys():
            if _depth == 0:  # Top Level
                _menu[key].guiwidget_set(self._widget.addMenu(_menu[key].element.text))

                parent_app.widget_add(
                    window_id=window_id,
                    container_tag=container_tag,
                    tag=_menu[key].tag,
                    widget=_menu[key],
                )

                self.container_tag = container_tag

                if _menu[key].element.tooltip.strip() != "":
                    self.tooltip_set(_menu[key].tag, _menu[key].element.tooltip)

            if len(_menu[key].element_items) > 0:
                parent_item: _Menu_Entry = self._element_find(
                    _menu[key].parent_tag, self._menu_items
                )
                menu_item: _Menu_Entry = self._element_find(
                    _menu[key].tag, self._menu_items
                )

                if menu_item.guiwidget_get is None:  # Happens with sub-menus
                    menu_item.guiwidget_set(
                        parent_item.guiwidget_get.addMenu(menu_item.element.text)
                    )

                    parent_app.widget_add(
                        window_id=window_id,
                        container_tag=container_tag,
                        tag=menu_item.tag,
                        widget=menu_item,
                    )

                    self.container_tag = container_tag

                    if menu_item.element.tooltip.strip() != "":
                        self.tooltip_set(menu_item.tag, menu_item.element.tooltip)
                self._create_widget(
                    parent_app=parent_app,
                    parent=parent,
                    container_tag=container_tag,
                    _menu=_menu[key].element_items,
                    _depth=_depth + 1,
                )

                self.container_tag = container_tag
            else:
                parent_item = self._element_find(
                    _menu[key].parent_tag, self._menu_items
                )
                menu_item = self._element_find(_menu[key].tag, self._menu_items)

                if (
                    _menu[key].element.separator
                    or _menu[key].element.text.strip() == MENU_SEPERATOR
                ):
                    menu_item.guiwidget_set(parent_item.guiwidget_get.addSeparator())
                else:
                    menu_item.guiwidget_set(
                        parent_item.guiwidget_get.addAction(_menu[key].element.text)
                    )

                    parent_app.widget_add(
                        window_id=window_id,
                        container_tag=container_tag,
                        tag=menu_item.tag,
                        widget=menu_item,
                    )

                    self.container_tag = container_tag

                    if menu_item.element.tooltip.strip() != "":
                        self.tooltip_set(menu_item.tag, menu_item.element.tooltip)

                    if menu_item.element.callback is not None:
                        event_handler = _Event_Handler(
                            parent_app=parent_app, parent=self
                        )
                        menu_item.guiwidget_get.triggered.connect(
                            functools.partial(
                                event_handler.event,
                                window_id=window_id,
                                callback=menu_item.element.callback,
                                action=menu_item.element.callback.__name__,
                                container_tag=container_tag,
                                tag=menu_item.tag,
                                event=Sys_Events.MENUCLICKED,
                                value=None,
                                widget_dict=parent_app.widget_dict_get(
                                    window_id=window_id,
                                    container_tag=container_tag,
                                ),
                                parent=parent,
                                control_name=self.__class__.__name__,
                            )
                        )
        return self._widget

    def element_add(self, parent_tag: str, menu_element: Menu_Element) -> None:
        """Adds a menu element to the menu object

        Args:
            parent_tag (str): Menu element tag of the parent menu element. "" is the top level parent_tag
            menu_element (Menu_Element): Menu Element instance

        Raises:
            AssertionError: Rasied if the parent_tag does  not exist
        """
        assert isinstance(parent_tag, str), f"{parent_tag=}. Must be str"
        assert isinstance(
            menu_element, Menu_Element
        ), f"{menu_element=}. Must be an instance of Menu_Element"

        menu_item: _Menu_Entry = self._element_find(menu_element.tag, self._menu_items)

        assert (
            menu_item.parent_tag == "" and menu_item.tag == ""
        ), f"{menu_item.tag=} already used!"

        # Top Level Menu has an empty parent_tag
        if parent_tag.strip() == "":
            assert menu_element.tag not in self._menu_items, (
                f"{parent_tag=} is already installed as a top level tag"
                f" <{self._menu_items}>"
            )
            self._menu_items[menu_element.tag] = _Menu_Entry(
                parent_tag=menu_element.tag, tag=menu_element.tag, element=menu_element
            )
        else:
            menu_item = self._element_find(parent_tag, self._menu_items)

            if parent_tag == menu_item.tag:
                menu_item.element_items[menu_element.tag] = _Menu_Entry(
                    parent_tag=parent_tag, tag=menu_element.tag, element=menu_element
                )
            else:
                raise AssertionError(
                    f"{parent_tag=} not found\n <{menu_item}> !\n <{self._menu_items}> "
                )

    def _element_find(
        self, search_tag: str, menu_item: dict[str, _Menu_Entry]
    ) -> _Menu_Entry:
        """Finds and returns a menu element based on the search tag

        Args:
            search_tag (str): [description]
            menu_item (Dict[str,Menu_Entry]): [description]

        Returns:
            _Menu_Entry: Tme _Menu_Entry object.  If not found then both parent_tag and tag are both == ""
        """
        menu_element = _Menu_Entry(parent_tag="", tag="", element=Menu_Element())

        for key in menu_item.keys():
            if menu_item[key].tag == search_tag:
                return menu_item[key]
            elif len(menu_item[key].element_items) > 0:
                menu_element: _Menu_Entry = self._element_find(
                    search_tag, menu_item[key].element_items
                )

                if menu_element.tag == search_tag:
                    return menu_element

        return menu_element

    def print_menu(
        self, menu_item: Union[dict[str, _Menu_Entry], None] = None, delim: str = "*"
    ) -> None:
        """Prints menu structure to command line appropriately indented with leading '*'.  For debug purposes

        Args:
            menu_item (Dict[str,_Menu_Entry], optional): [description]. Defaults to {}.
            delim (str, optional): [description]. Defaults to "*".
        """
        if menu_item is None or len(menu_item) == 0:
            menu_item = self._menu_items

        for key in menu_item.keys():
            if len(menu_item[key].element_items) > 0:
                self.print_menu(menu_item[key].element_items, f"{' '}{delim}*")

    def checked_get(self, tag: str) -> bool:
        """Returns the checked state of a menu item

        Args:
            tag (str): Menu item tag name

        Returns:
            bool : The checked state of the menu item.
        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        menu_item: _Menu_Entry = self._element_find(tag, self._menu_items)

        assert (
            menu_item.parent_tag.strip() != "" and menu_item.tag.strip() != ""
        ), f"menu item <{tag=}> not found!"

        parent_item: _Menu_Entry = self._element_find(
            menu_item.parent_tag, self._menu_items
        )

        assert menu_item.guiwidget_get is not None, f"Menu Not Set On tag <{tag}>!"

        if isinstance(menu_item.guiwidget_get, qtW.QMenu):
            return menu_item.guiwidget_get.menuAction().checked()
        elif isinstance(menu_item.guiwidget_get, qtW.QAction):
            return menu_item.guiwidget_get.checcked()
        else:
            raise AssertionError(
                f"Unknown menu property for menu tag <{tag=}> || <{menu_item}>"
            )

    def checked_set(self, tag: str, checked: bool) -> None:
        """Sets the checked state of a menu item

        Args:
            tag (str): tag name of menu item
            checked (bool): The checked state of the menu item.
        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"
        assert isinstance(checked, bool), f"{checked=}. Must be bool"

        menu_item: _Menu_Entry = self._element_find(tag, self._menu_items)

        assert (
            menu_item.parent_tag.strip() != "" and menu_item.tag.strip() != ""
        ), f"menu item <{tag=}> not found!"

        parent_item: _Menu_Entry = self._element_find(
            menu_item.parent_tag, self._menu_items
        )

        assert menu_item.guiwidget_get is not None, f"Menu Not Set On tag <{tag}>!"

        if isinstance(menu_item.guiwidget_get, qtW.QMenu):
            menu_item.guiwidget_get.menuAction().setChecked(checked)
        elif isinstance(menu_item.guiwidget_get, qtW.QAction):
            menu_item.guiwidget_get.setChecked(checked)
        else:
            raise AssertionError(
                f"Unknown menu property for menu tag <{tag=}> || <{menu_item}>"
            )

    def tooltip_set(self, tag: str, tooltip: str) -> None:
        """Sets a tooltip on a given menu item referenced by the tag

        Args:
            tag (str) : Tag name of menu item that is having the tooltip set
            tooltip (str): The tooltip

        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"
        assert (
            isinstance(tooltip, str) and tooltip.strip() != ""
        ), f"{tooltip=}. Must be a non-empty str"

        menu_item: _Menu_Entry = self._element_find(tag, self._menu_items)

        assert (
            menu_item.parent_tag.strip() != "" and menu_item.tag.strip() != ""
        ), f"menu item <{tag=}> not found!"

        parent_item: _Menu_Entry = self._element_find(
            menu_item.parent_tag, self._menu_items
        )

        assert menu_item.guiwidget_get is not None, f"Menu Not Set On tag <{tag}>!"

        if isinstance(
            menu_item.guiwidget_get, qtW.QMenu
        ):  # TODO These QMenu tooltips are not happening!
            menu_item.guiwidget_get.menuAction().setToolTip(tooltip)
            menu_item.guiwidget_get.setToolTipsVisible(True)

        elif isinstance(menu_item.guiwidget_get, qtG.QAction):
            menu_item.guiwidget_get.setToolTip(tooltip)
            parent_item.guiwidget_get.setToolTipsVisible(True)
        else:
            raise AssertionError(
                f"Unknown menu property for menu tag <{tag=}> || <{menu_item}>"
            )

    def tooltip_visible(self, tag: str, visible: bool) -> None:
        """Sets the tooltip visibility (on or off) of a given menu item tooltip referenced by the tag

        Args:
            tag (str) : Tag name of menu item that is having the tooltip set
            visible (bool) : True - tooltip visible, False - tooltip not visible
        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        assert isinstance(visible, bool), f"{visible=}. Must be a bool"

        menu_item: _Menu_Entry = self._element_find(tag, self._menu_items)

        assert (
            menu_item.parent_tag.strip() != "" and menu_item.tag.strip() != ""
        ), f"menu item <{tag=}> not found!"

        parent_item: _Menu_Entry = self._element_find(
            menu_item.parent_tag, self._menu_items
        )

        assert menu_item.guiwidget_get is not None, f"Menu Not Set On <{tag=}>!"

        if isinstance(
            menu_item.guiwidget_get, qtW.QMenu
        ):  # TODO These QMenu tooltips are not happening!
            menu_item.guiwidget_get.setToolTipsVisible(visible)
        elif isinstance(menu_item.guiwidget_get, qtW.QAction):
            parent_item.guiwidget_get.setToolTipsVisible(visible)
        else:
            raise AssertionError(
                f"Unknown menu property for menu <{tag=}> || <{menu_item}>"
            )


@dataclasses.dataclass
class RadioButton(_qtpyBase_Control):
    """Instantiates a RadioButton widget and associated properties"""

    checked: bool = False

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets properties"""

        super().__post_init__()

        assert isinstance(self.checked, bool), f"{self.checked}. Must be bool."

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the radio button widget and sets the properties

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): str = ""

        Returns:
            QWidget : The radio button widget or the container housing it.
        """

        if self.height <= 0:
            self.height = WIDGET_SIZE.height

        if self.width <= 0:
            self.width = WIDGET_SIZE.width

        self.width = (
            amper_length(self.trans_str(self.text)) + 2
        )  # click circle area + space before label

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QRadioButton
        self._widget.setAutoExclusive(
            False
        )  # When 1 rb in group then cannot check it otherwise!

        self.button_toggle(self.checked)

        self._widget.setAutoExclusive(True)  # Radiobutton groups must be autoexclusive

        return widget

    @property
    def button_checked(self) -> bool:
        """Return  checked state

        Returns:
            bool : True - Checked, False - Not Checked
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: qtW.QRadioButton

        return self._widget.isChecked()

    def button_toggle(self, value: bool = True) -> None:
        """Set the radiobutton to checked or unchecked

        Args:
            value (bool): True - radio button checked. False - radio button not-chedcked. Defaults to True
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(value, bool), f"{value=}. Must be bool"

        self._widget: qtW.QRadioButton

        self._widget.setChecked(value)

    def value_get(self) -> bool:
        """Returns the Raiobutton checked state

        Returns:
            bool : True - Radiobutton Checked, False - Radiobutton not cvhecked
        """

        return self.button_checked

    def value_set(self, value: bool) -> None:
        """Sets the radiobutton to checked or unchecked

        Args:
            value (bool): True - checked. False - not checked.

        """

        assert isinstance(value, bool), f"{value=}. Must be bool"

        self.button_toggle(value)


@dataclasses.dataclass
class Spacer(_qtpyBase_Control):
    """Instantiates a spacer widget and sets the properties"""

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets properties"""
        super().__post_init__()

        assert self.text == "", f"{self.text=} is ignored by space control"

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the spacer widget and sets the properties

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The container tag name.

        Returns:
            QWidget : The spacer widget or its container.
        """
        # Spacers must have a minimum size
        if self.height <= 0:
            self.height = WIDGET_SIZE.height

        if self.width <= 0:
            self.width = WIDGET_SIZE.width

        self.text = " " * self.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )
        # widget.setFrameShape(qtW.QFrame.Shape.Box)  # Used for debug

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if self.height == -1:
            self._widget.setFixedHeight(1)
        return widget


@dataclasses.dataclass
class Switch(_qtpyBase_Control):
    """Instantiates a switch widget and sets the properties"""

    label: str = "&"
    width: int = 4  # RADIOBUTTON_SIZE.width
    height: int = 1  # RADIOBUTTON_SIZE.height
    widget_align: Align = Align.CENTER
    checked: bool = False

    # Pad text with spaces to be all be this size
    txt_pad_size: int = 0
    txt_pad_unit: str = "c"  # c - Char, p - Pixel

    def __post_init__(self) -> None:
        """Constructor that checks parameters and sets properties"""
        super().__post_init__()

        assert isinstance(self.txt_pad_size, int), f"{self.txt_pad_size=}. Must be bool"

        assert isinstance(self.txt_pad_unit, str) and self.txt_pad_unit in (
            "c",
            "p",
        ), f"{self.txt_pad_unit=}. Must be str c | p"

        if self.buddy_control is None:
            self.buddy_control = Label(text=self.text)
        else:
            if self.text.strip() != "":
                self.buddy_control = HBoxContainer().add_row(
                    Label(text=self.text), self.buddy_control
                )

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the switch widget and sets the properties

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The container tag name.

        Returns:
            QWidget : The switch widget or the container housing it.
        """
        # Switches must have a minimum size
        if self.height <= 0:
            self.height = WIDGET_SIZE.height

        if self.width <= 0:
            self.width = WIDGET_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self._widget: _Switch

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget.setAutoExclusive(
            False
        )  # When 1 rb in group then cannot check it otherwise! - Not sure if this applies to switch

        self.button_toggle(self.checked)

        self._widget.setAutoExclusive(False)  # switch groups must not be auto exclusive

        return widget

    def track_colour_set(self, enable: str, disable: str) -> None:
        """Sets the colour of the track.

        Args:
            enable (str): TEXT_COLORS  word
            disable (str): TEXT_COLORS  word
        """
        self._widget: _Switch
        self._widget.track_colour_set(enable=enable, disable=disable)

    @property
    def button_checked(self) -> bool:
        """Returns the widget's checked state

        Returns:
            bool: True - Checked, False - Not Checked.
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._widget: _Switch
        return self._widget.isChecked()

    def button_toggle(self, value: bool = True) -> None:
        """Set the widget's checked state

        Args:
            value (bool): True - Checked, False not Checked. Defaults to True
        """
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(value, bool), f"{value=}. Must be bool"

        self._widget: _Switch
        self._widget.setChecked(value)

    def value_get(self) -> bool:
        """Returns the current state of the button

        Returns:
            bool : True - Checked, False - Not Checked.
        """
        return self.button_checked

    def value_set(self, value: bool) -> None:
        """Sets the Checked state of the Switch.

        Args:
            value (bool): True - Checked, False - Not Checked.
        """
        assert isinstance(value, bool), f"value <{value}> must be bool"

        self.button_toggle(value)


class _Switch(qtW.QAbstractButton):
    """Instantiates a Slider Switch and associates it with a parent widget."""

    def __init__(
        self,
        parent: Optional[qtW.QWidget] = None,
        track_radius: int = 9,
        thumb_radius: int = 9,
    ) -> None:
        """Constructor for the _Switch and associated properties.

        Args:
            parent (Optional[qtW.QWidget]): The parent widget.
            track_radius (int): The radius of the track. Defaults to 9
            thumb_radius (int): The radius of the thumb. Defaults to 9
        """
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setSizePolicy(qtW.QSizePolicy.Fixed, qtW.QSizePolicy.Fixed)

        self._track_radius = track_radius
        self._thumb_radius = thumb_radius

        self._margin = max(0, self._thumb_radius - self._track_radius)
        self._base_offset = max(self._thumb_radius, self._track_radius)
        self._end_offset = {
            True: lambda: self.width() - self._base_offset,
            False: lambda: self._base_offset,
        }
        self._offset = self._base_offset

        palette = self.palette()
        if self._thumb_radius > self._track_radius:
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._thumb_color = {
                True: palette.highlight(),
                False: palette.light(),
            }
            self._text_color = {
                True: palette.highlightedText().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: "",
                False: "",
            }
            self._track_opacity = 0.5
        else:
            self._thumb_color = {
                True: palette.highlightedText(),
                False: palette.light(),
            }
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._text_color = {
                True: palette.highlight().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: "✔",
                False: "✕",
            }
            self._track_opacity = 1

    def read_offset(self) -> int:
        """Returns the value of the offset.

        Returns:
            int : The offset value .
        """

        return self._offset

    def write_offset(self, value: int) -> None:
        """Sets offset value.

        Args:
            value: The value of the property.
        """
        assert isinstance(value, int), f"{value=} must be int"

        self._offset = value
        self.update()

    offset = qtC.Property(int, read_offset, write_offset)

    def sizeHint(self):  # pylint: disable=invalid-name
        """Overrides size hint in the ancestor .

        Returns:
            A QSize object with the width and height of the widget.
        """
        return qtC.QSize(
            4 * self._track_radius + 2 * self._margin,
            2 * self._track_radius + 2 * self._margin,
        )

    def setChecked(self, checked: bool) -> None:
        """Sets the checked  state of the Switch

        Args:
            checked (bool): True - checked, False - unchecked
        """
        super().setChecked(checked)

        self.write_offset(self._end_offset[checked]())

    def resizeEvent(self, event: qtG.QResizeEvent) -> None:
        """Handles the resize event.

        Calls the superclasses resizeEvent function, then calls the write_offset function with the appropriate offset
        value

        Args:
            event (QResizeEvent): The event object that was passed to the function.
        """
        super().resizeEvent(event)

        self.write_offset(self._end_offset[self.isChecked()]())

    def paintEvent(
        self, event: qtC.QEvent
    ) -> None:  # pylint: disable=invalid-name, unused-argument
        """Handles the paint event to paint the switch widget

        Args:
            event (QEvent): The event that triggered the paintEvent.
        """
        painter = qtG.QPainter(self)
        painter.setRenderHint(qtG.QPainter.Antialiasing, True)
        painter.setPen(qtC.Qt.NoPen)
        track_opacity = self._track_opacity
        thumb_opacity = 1.0
        text_opacity = 1.0
        if self.isEnabled():
            track_brush = self._track_color[self.isChecked()]
            thumb_brush = self._thumb_color[self.isChecked()]
            text_color = self._text_color[self.isChecked()]
        else:
            track_opacity *= 0.8
            track_brush = self.palette().shadow()
            thumb_brush = self.palette().mid()
            text_color = self.palette().shadow().color()

        painter.setBrush(track_brush)
        painter.setOpacity(track_opacity)
        painter.drawRoundedRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
            self._track_radius,
            self._track_radius,
        )
        painter.setBrush(thumb_brush)
        painter.setOpacity(thumb_opacity)
        painter.drawEllipse(
            self._offset - self._thumb_radius,
            self._base_offset - self._thumb_radius,
            2 * self._thumb_radius,
            2 * self._thumb_radius,
        )
        painter.setPen(text_color)
        painter.setOpacity(text_opacity)
        font = painter.font()
        font.setPixelSize(1.5 * self._thumb_radius)
        painter.setFont(font)

        # Property offset does not work here - need read_offset call
        painter.drawText(
            qtC.QRectF(
                self.read_offset() - self._thumb_radius,
                self._base_offset - self._thumb_radius,
                2 * self._thumb_radius,
                2 * self._thumb_radius,
            ),
            qtC.Qt.AlignCenter,
            self._thumb_text[self.isChecked()],
        )

    def mouseReleaseEvent(
        self, event: qtG.QMouseEvent
    ) -> None:  # pylint: disable=invalid-name
        """Handles mouse release event and performs a switch animation when the left button is released.

        Args:
            event (QMouseEvent): The mouse event that triggered the function
        """
        super().mouseReleaseEvent(event)

        if event.button() == qtC.Qt.LeftButton:
            self.anim = qtC.QPropertyAnimation(self, b"offset", self)
            self.anim.setDuration(120)
            # self.anim.setStartValue(self.offset) #Offset Property not working as expected
            self.anim.setStartValue(self.read_offset())
            self.anim.setEndValue(self._end_offset[self.isChecked()]())
            self.anim.start()

    def enterEvent(
        self, event: qtG.QEnterEvent
    ) -> None:  # pylint: disable=invalid-name
        """Handles the mouse enter event.

        Changes the cursor to a pointing hand when the mouse enters the widget.

        Args:
            event (qtG.QEnterEvent): The event the triggered the enterEvent
        """
        self.setCursor(qtC.Qt.PointingHandCursor)
        super().enterEvent(event)

    def track_colour_set(self, enable: str, disable: str) -> None:
        """Sets the colour of the switch track.

        Args:
            enable (str): TEXT_COLORS  word
            disable (str): TEXT_COLORS  word
        """
        assert (
            isinstance(enable, str)
            and enable == ""
            or enable.lower() in [colour.lower() for colour in TEXT_COLORS]
        ), f"{enable=}. Must be '' or {TEXT_COLORS}"
        assert (
            isinstance(disable, str)
            and disable == ""
            or disable.lower() in [colour.lower() for colour in TEXT_COLORS]
        ), f"{disable=}. Must be '' or {TEXT_COLORS}"

        palette = self.palette()

        self._track_color = {
            True: palette.highlight() if enable == "" else qtG.QColor(enable),
            False: palette.dark() if disable == "" else qtG.QColor(disable),
        }


@dataclasses.dataclass
class TextEdit(_qtpyBase_Control):
    """Instantiates a text edit widget and associated properties"""

    label: str = "&"
    max_chars: int = -1
    word_wrap: bool = True

    def __post_init__(self) -> None:
        """Constructor checks parameters and sets associated properties"""
        super().__post_init__()

        assert isinstance(self.max_chars, int) and (
            self.max_chars > 0 or self.max_chars == -1
        ), f"{self.max_chars=} Must be int > 0"

        assert isinstance(self.word_wrap, bool), f"{self.word_wrap=}. Must be bool"

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the TextEdit widget and sets associated properties.

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag name of the container that this widget is in.

        Returns:
            QWidget : The TextEdit widget or the container that houses it.
        """

        if self.height <= 0:
            self.height = WIDGET_SIZE.height

        if self.width <= 0:
            self.width = WIDGET_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self._widget: qtW.QTextEdit

        if self.text.strip() != "":
            self._widget.setText(self.trans_str(self.text))

        self._widget.setReadOnly(not self.editable)

        if self.word_wrap:
            self._widget.setWordWrapMode(qtG.QTextOption.WrapMode.WordWrap)
        else:
            self._widget.setWordWrapMode(qtG.QTextOption.WrapMode.NoWrap)

        self._widget.moveCursor(qtG.QTextCursor.End)

        # Bit ugly, nasty regex check for hmtl and then sets alignment for all paragraphs if no HMTL found
        # Assumes HTML controls formatting'
        if not re.search("<(\"[^\"]*\"|'[^']*'|[^'\">])*>", self.text):
            last_position = -1
            curr_position = self._widget.textCursor().position()

            while last_position != curr_position:
                self._widget.setAlignment(self.txt_align.value)
                self._widget.moveCursor(qtG.QTextCursor.Down)
                last_position = curr_position
                curr_position = self._widget.textCursor().position()

            self._widget.moveCursor(qtG.QTextCursor.End)

        return widget

    def _check_max_chars(self) -> None:
        """Checks the max characters and sets the widget to read only if max characters is reached"""
        self._widget: qtW.QTextEdit

        diff = len(self._widget.toPlainText()) - self.max_chars

        if diff > 0:  # Max length exceeded
            self._widget.setText(self._widget.toPlainText()[0 : self.max_chars])
            self._widget.moveCursor(qtG.QTextCursor.End)

    def value_set(self, value: str = "") -> None:
        """Sets the text of the widget to the string value

        Args:
            value (str): The string value to set the TextEdit widget to.
        """
        self._widget: qtW.QTextEdit

        assert isinstance(value, str), f"text <{value=}>. Must be a str"

        self._widget.setText(self.trans_str(value))
        self._widget.moveCursor(qtG.QTextCursor.End)

    def value_get(self, plain_text: bool = True) -> str:
        """Returns the text from the TextEdit` widget as either plain text or HTML

        Args:
            plain_text (bool): True - Returns the text as plain text. False - Returns the text as HTML.

        Returns:
            str : The text in the text box in the selected format.
        """
        self._widget: qtW.QTextEdit

        assert isinstance(plain_text, bool), f"{plain_text=}. Must be bool"

        if plain_text:
            return self._widget.toPlainText()

        return self._widget.toHtml()


@dataclasses.dataclass
class Timeedit(_qtpyBase_Control):
    """Instantiates a Timeedit widget and associated properties
    h 	the hour without a leading zero (0 to 23 or 1 to 12 if AM/PM display)
    hh 	the hour with a leading zero (00 to 23 or 01 to 12 if AM/PM display)
    m 	the minute without a leading zero (0 to 59)
    mm 	the minute with a leading zero (00 to 59)
    s 	the second without a leading zero (0 to 59)
    ss 	the second with a leading zero (00 to 59)
    z 	the milliseconds without leading zeroes (0 to 999)
    zzz 	the milliseconds with leading zeroes (000 to 999)
    AP 	interpret as an AM/PM time. AP must be either “AM” or “PM”.
    ap 	Interpret as an AM/PM time. ap must be either “am” or “pm”.
    """

    label: str = "&"
    display_width: int = 10
    hour: int = -1
    min: int = -1
    sec: int = -1
    msec: int = -1
    display_format: str = ""  # "HH:mm"
    validate_callback: Optional[
        Union[Callable, types.FunctionType, types.MethodType, types.LambdaType]
    ] = None

    @dataclasses.dataclass
    class time_struct:
        hour: int
        min: int
        sec: int
        msec: int

    def __post_init__(self) -> None:
        """Constructor checks argument and sets associated properties"""

        super().__post_init__()

        assert isinstance(
            self.display_width, int
        ), f"{self.display_width=}. Must be int"
        assert isinstance(self.hour, int), f"{self.hour=}. Must be int"
        assert isinstance(self.min, int), f"{self.min=}. Must be int"
        assert isinstance(self.sec, int), f"{self.sec=}. Must be int"
        assert isinstance(self.msec, int), f"{self.msec=}. Must be int"
        assert isinstance(
            self.display_format, str
        ), f"{self.display_format=}. Must be str"
        assert self.validate_callback is None or callable(
            self.validate_callback
        ), f"{self.validate_callback=}. Must be None | Function | Method | Lambda"

        # Buddy checks are in super...bypassed here
        buddy_buton = Button(
            tag="terase_" + str(uuid.uuid1()),
            width=2,
            height=1,
            tooltip=f"{self.trans_str('Erase')} {SDELIM}{self.text}{SDELIM}",
            icon=App_Path("backspace.svg"),  # qta.icon("mdi.backspace"),
            txt_font=self.txt_font,
            callback=self.buddy_event,
        )

        if self.buddy_control is None:
            self.buddy_control = buddy_buton
        else:
            buddy_control = HBoxContainer(tag=f"btctrl_{self.tag}")
            buddy_control.add_control(buddy_buton)
            buddy_control.add_control(self.buddy_control)
            self.buddy_control = buddy_control

        if self.buddy_callback is None:
            self.buddy_callback = self.buddy_event

        if self.hour == -1 and self.min == -1 and self.sec == -1 and self.msec == -1:
            pass
            # now = qtC.QTime.currentTime().toString("hh.mm.ss.zzz").split(".")
            # self.hour = int(now[0])
            # self.min = int(now[1])
            # self.sec = int(now[2])
            # self.msec = int(now[3])
        else:
            assert 0 <= self.hour <= 23, f"hour <{self.hour}> must be >= 0 and <= 23"
            assert 0 <= self.min <= 59, f"min <{self.min}> must be >= 0 and <= 59"
            assert 0 <= self.sec <= 59, f"sec <{self.sec}> must be >= 0 and <= 59"
            assert 0 <= self.msec <= 59, f"sec <{self.msec}> must be >= 0 and <= 999"

        if self.display_format.strip() == "":
            self.display_format = qtC.QLocale.system().timeFormat(
                qtC.QLocale.system().FormatType.ShortFormat
            )

            self.width = len(self.display_format) + 3  # set 3 extra chars for arrow
        else:
            self.width += 3  # set 3 extra chars for arrow

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        if self.height == -1:
            self.height = WIDGET_SIZE.height  # COMBOBOX_SIZE.height

        if self.width == -1:
            self.width = WIDGET_SIZE.width

        if len(self.display_format) > self.width:
            self.width = len(self.display_format)

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self._widget: qtW.QTimeEdit

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        line_edit: qtW.QLineEdit = cast(
            qtW.QLineEdit, self._widget.findChild(qtW.QLineEdit)
        )

        self._widget.setDisplayFormat(self.display_format)
        # line_edit.setInputMask(self.display_format)

        self.time_set(self.hour, self.min, self.sec, self.msec)

        return widget

    def _event_handler(
        self,
        *args,
    ) -> int:
        """Event handler for TimeEdit widget.

        Args:
            *args: Default args for the _event_handler

        Returns:
            int : 1. If the event is accepted, -1. If the event is rejected
        """
        self._widget: qtW.QTimeEdit

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        event = args[0]

        if event == Sys_Events.FOCUSIN:
            # Set default time to now - not minimum time! Part of hack to clear displayed values
            if self._widget.time() == self._widget.minimumTime():
                # If time minimumTime matches midnight then first use! Millisecond is dangerous!
                if self._widget.minimumTime() == qtC.QTime(0, 0, 0, 0):
                    now = datetime.datetime.now()

                    # Millisecond must = 1 so as not to match minimum time at midnight
                    self.time_set(now.hour, now.minute, now.second, 1)

        if callable(self.callback):
            window_id = Get_Window_ID(self.parent_app, self.parent, self)

            handler = _Event_Handler(parent_app=self.parent_app, parent=self)
            return handler.event(
                window_id=window_id,
                callback=self.callback,
                action=event.name,
                container_tag=self.container_tag,
                tag=self.tag,
                event=event,
                value=self.value_get(),
                widget_dict=self.parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.container_tag
                ),
                control_name=self.__class__.__name__,
                parent=self.parent_app.widget_get(
                    window_id=window_id, container_tag=self.container_tag, tag=self.tag
                ),
            )

        return 1

    def buddy_event(self, event: Action) -> int:
        """Event handler for TimeEdit buddy widget.

        Args:
            event (Action): Action instance for the event

        Returns:
            int : 1. If the event is accepted, -1. If the event is rejected
        """
        if event.event == Sys_Events.CLICKED:
            self.clear("-")

        return 1

    def clear(self, default_text: str = "-") -> None:
        """Clears the displayed value - has to use a nasty hack

        If default_text = "-" then nothing is displayed in the date edit.
        otherwise the default text is displayed in the time edit

        Args:
            default_text: The times text string or "-" for no time text to be `displayed
        """
        self._widget: qtW.QTimeEdit

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(default_text, str), f"{default_text=}. Must be str"

        if self.allow_clear:
            self._widget.clear()  # Clear does not clear everything - so hack time

            # Hack to clear displayed values
            if default_text == "":
                default_text = self.trans_str("N/A")
            if default_text == "-":
                default_text = " "

            # This ensures nothing or default text is displayed in date edit
            self._widget.setTime(self._widget.minimumTime())
            self._widget.setSpecialValueText(default_text)

    def time_set(
        self, hour: int = -1, min: int = -1, sec: int = -1, msec: int = -1
    ) -> None:
        """Sets the time

        if hour == -1 and min == -1 and sec == -1 and msec == -1 then the displayed value is cleared

        Args:
            hour (int): Hour value
            min (int): Minute value
            sec (int): Second value
            msec (int): Millisecond value
        """
        self._widget: qtW.QTimeEdit

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(self.hour, int), f"{self.hour=}. Must be int"
        assert isinstance(self.min, int), f"{self.min=}. Must be int"
        assert isinstance(self.sec, int), f"{self.sec=}. Must be int"
        assert isinstance(self.msec, int), f"{self.msec=}. Must be int"

        if hour == -1 and min == -1 and sec == -1 and msec == -1:  # Default
            pass
        else:
            assert 0 <= hour <= 23, f"hour <{hour}> must be >= 0 and <= 23"
            assert 0 <= min <= 59, f"min <{min}> must be >= 0 and <= 59"
            assert 0 <= sec <= 59, f"sec <{sec}> must be >= 0 and <= 59"
            assert 0 <= msec <= 999, f"sec <{msec}> must be >= 0 and <= 999"

        time = qtC.QTime()

        if hour == -1 and min == -1 and sec == -1 and msec == -1:  # Default
            self.clear()
        else:
            time.setHMS(hour, min, sec, msec)

        self._widget.setTime(time)

    @property
    def time_get(self) -> time_struct:
        """Returns the time value as a time_struct (hour,min,sec,msec)

        Returns:
            time_struct: tims_struct (hour,min,sec,msec)
        """
        self._widget: qtW.QTimeEdit

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        time = self._widget.time()

        return self.time_struct(
            hour=time.hour(), min=time.minute(), sec=time.second(), msec=time.msec()
        )

    @overload
    def value_get(self, format: str = "", time_tuple=False) -> tuple:
        ...

    @overload
    def value_get(self, format: str = "", time_tuple=False) -> str:
        ...

    def value_get(self, format: str = "", time_tuple=False) -> time_struct | str:
        """Returns the time value.

            if format is "-" then the time is returned as a string formatted to system short-format.
            if format is "" then a time_tuple from time get is returned
            otherwise the format statement is used and a formatted time string returned

        Args:
            format (str): Format string
            time_tuple (bool): True - Return time as a time_tuple (hour,min,sec,msec), False - Return time as a string
        """
        self._widget: qtW.QTimeEdit

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(format, str), f"{format=}. Must be a str"
        assert isinstance(time_tuple, bool), f"{time_tuple=}. Must be bool"

        if time_tuple:
            return self.time_get

        if format.strip() == "-" or format.strip() == "":
            format = qtC.QLocale.system().timeFormat(
                qtC.QLocale.system().FormatType.ShortFormat
            )

        return self._widget.time().toString(format)

    def value_set(
        self, hour: int = 0, min: int = 0, sec: int = 0, msec: int = 0
    ) -> None:
        """Sets the time

        Args:
            hour (int): Hour
            min (int): Minute
            sec (int): Second
            msec (int): Millisecond
        """
        assert isinstance(hour, int) and hour >= 0, f"hour <{hour}> must be an int >= 0"
        assert isinstance(min, int) and min >= 0, f"min <{min}> must be an int >= 0"
        assert isinstance(sec, int) and sec >= 0, f"sec <{sec}> must be an int >= 0"
        assert isinstance(msec, int) and msec >= 0, f"msec <{msec}> must be an int >= 0"

        return self.time_set(hour, min, sec, msec)


@dataclasses.dataclass
class Tab(_qtpyBase_Control):
    """Instantiates a Tab control and associated properties"""

    @dataclasses.dataclass
    class _Page_Def:
        """Internal page definition class"""

        container: _qtpyBase_Control
        created: bool = False
        tag: str = ""
        title: str = ""
        icon: None | str | qtG.QPixmap | qtG.QIcon = None
        index: int = -1
        tooltip: str = ""
        enabled: bool = True
        visible: bool = True

    def __post_init__(self) -> None:
        """Constructor check parameters ans sets properties"""

        super().__post_init__()

        self._tab_pages: dict = {}

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the tab widget and sets associated properties

        Args:
            parent_app (QtPyApp): The QtPyApp instance that is the parent of this widget.
            parent (qtW.QWidget): The parent widget of the widget being created.
            container_tag (str): This is the container tagname that will be used to reference the Tab widget.
        """

        if self.width < 1:
            self.width = WIDGET_SIZE.width

        if self.height < 1:
            self.height = WIDGET_SIZE.height

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        self._create_pages()

        return widget

    def _create_pages(self) -> None:
        """Creates the tab pages for the Tab widget"""

        self._widget: qtW.QTabWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        for page in self._tab_pages.values():
            if page.created == False:
                tab_widget: qtW.QWidget = page.container._create_widget(
                    parent_app=self.parent_app,
                    parent=self._widget,
                    container_tag=self.tag,
                )

                tab_page_layout = qtW.QFormLayout(self._widget)
                tab_page_layout.addWidget(tab_widget)

                tab_page = qtW.QWidget(self._widget)

                # tab_page.setFixedSize(tab_widget.width(),tab_widget.height())

                tab_page.setLayout(tab_page_layout)
                # tab_page.setFixedWidth(300)

                page.index = self._widget.addTab(
                    tab_page,
                    page.title,
                )

                if page.icon is not None:
                    self.page_icon_set(page.tag, page.icon)

                if page.tooltip != "":
                    self.tooltip_set(page.tag, page.tooltip)

                self.enable_set(page.tag, page.enabled)
                self.page_visible_set(page.tag, page.visible)

                page.created = True

    def _event_handler(
        self,
        *args,
    ) -> int:
        """Handles events for the Tab widget

        Args:
            *args: Default event arguments

        Returns:
            int: 1. If the event is accepted, -1. If the event is rejected
        """
        event = args[0]

        assert isinstance(args[1], tuple), f"{args[1]=}. Must be tuple"
        assert isinstance(args[1][0], int), f"{args[1][0]=}. Must be int"

        tab_index = args[1][0]

        if callable(self.callback):
            tag = ""

            for page in self._tab_pages.values():
                if page.index == tab_index:
                    tag = page.tag
                    break
            if tag.strip() == "":
                return 1

            window_id = Get_Window_ID(self.parent_app, self.parent, self)

            handler = _Event_Handler(parent_app=self.parent_app, parent=self)
            return handler.event(
                window_id=window_id,
                callback=self.callback,
                action=event.name,
                container_tag=self.tag,
                tag=tag,
                event=event,
                value=self.value_get(),
                widget_dict=self.parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.container_tag
                ),
                control_name=self.__class__.__name__,
                parent=self.parent_app.widget_get(
                    window_id=window_id, container_tag=self.container_tag, tag=self.tag
                ),
            )
        else:
            return 1

    def clickable(
        self, widget: qtW.QWidget
    ) -> qtC.Signal | qtC.SignalInstance:  # TODO Integrate in ancestor
        """Makes a widget in the Tab  clickable

        Args:
            widget (QWidget) : The widget to be clicked.

        Returns:
            Signal | SignalInstance : A signal that is emitted when the widget is clicked.
        """

        class Filter(qtC.QObject):
            # A QObject that emits a signal when a key is pressed
            clicked = qtC.Signal()

            def eventFilter(self, obj: any, event: qtC.QEvent) -> bool:
                """Filter on mouse button release events

                If the event is a mouse button release event, and the mouse is over the widget, emit the clicked signal

                Args:
                    obj: The object that the event is being filtered for.
                    event: The event object that was sent to the eventFilter() method.

                Returns:
                    bool : True - Consumes the event, False - Passes the event on
                """
                if obj == widget:
                    if event.type() == qtC.QEvent.MouseButtonRelease:
                        event: qtG.QMouseEvent
                        if obj.rect().contains(event.pos()):
                            self.clicked.emit()

                            return True
                return False

        click_filter = Filter(widget)
        widget.installEventFilter(click_filter)

        return click_filter.clicked

    def enable_get(self, tag: str) -> bool:
        """Returns the tab or the tab pages enable state depending on the tag name property value.

        Args:
            tag (str): The tag name of the tab or tab page depending on which enable state is required.

        Returns:
            The return value is a bool.
        """
        self._widget: qtW.QTabWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        if self.tag == tag:
            return super().enable_get

        assert (
            tag in self._tab_pages
        ), f"{tag=}. Not found in Tab {self.tag=}  or tab pages: {self._tab_pages=}"

        return self._widget.isTabEnabled(self._tab_pages[tag].index)

    def enable_set(self, tag: str = "", enable: bool = True) -> int:
        """Sets the tab or the tab pages enable state depending on the tag name property value.

        If the tag is empty, then enable all the tabs. If the tag is not empty, then enable the tab page with the tag

        Args:
            tag (str): The tag name of the tab or tab page depending on which enable state is required.
            enable (bool): True - Enable the tab or tab page, False - Disable the tab or tab page.

        Returns:
            int : 1 - Success, -1 - Failure
        """
        self._widget: qtW.QTabWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(tag, str), f"{tag=}. Must be astr"
        assert isinstance(enable, bool), f"{enable=}. Must be bool"

        if self.tag == tag:
            return super().enable_set(enable)
        else:
            if tag.strip() == "":
                for page_tag in self._tab_pages.keys():
                    self._widget.setTabEnabled(self._tab_pages[page_tag].index, enable)
            else:
                assert tag in self._tab_pages, (
                    f"{tag=}. Not found in Tab {self.tag=}  or tab pages:"
                    f" {self._tab_pages=}"
                )

                self._widget.setTabEnabled(self._tab_pages[tag].index, enable)
        return 1

    def page_add(
        self,
        tag: str,
        title: str,
        control: Union[_qtpyBase_Control, _Container],
        icon: Optional[Union[str, qtG.QPixmap]] = None,
        tooltip: str = "",
        enabled: bool = True,
        visible: bool = True,
    ) -> "Tab":
        """Creates and adds a new tab page

        Args:
            tag (str): Tab page tag
            title (str): Tab page title
            control (Union[_qtpyBase_Control, _Container]): The qtgui(s) control to be placed on the tab page
            icon (Optional[Union[str, qtG.QPixmap]]): Tab page icon.  Can a str pointing to an icon file or an icon
            tooltip (str): The tab page tooltip
            enabled (bool): Sets the tab page enabled/disabled (default:True)
            visible (bool): Sets the tab page visible/invisible (default:TRue)

        Returns:
            Tab: The Tab control

        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        assert isinstance(title, str), f"{title=}. Must be str"

        assert isinstance(
            control, (_qtpyBase_Control, _Container)
        ), f"{control=}. Must be a descendant of _qtpyBase_Control or _Container"

        tab_page_container = VBoxContainer(
            tag=tag, width=self.width, height=self.height
        )

        if isinstance(control, _Container):
            control.height = self.height + 1  # - 5
            control.width = self.width - 1  # - 8
        elif isinstance(control, Tab):
            control.height = self.height - 3  # - 5
            control.width = self.width - 4  # - 8

        control.scroll = True

        tab_page_container.add_row(control)

        assert isinstance(
            self.icon, (type(None), str, qtG.QPixmap, qtG.QIcon)
        ), f" {self.icon=}. Must be None | str (file name)| QPixmap | QIcon"

        assert isinstance(tooltip, str), f"{tooltip=}. Must be str"
        assert isinstance(enabled, bool), f"{enabled=}. Must be bool"
        assert isinstance(visible, bool), f"{visible=}. Must be bool"

        self._tab_pages[tag] = self._Page_Def(
            container=tab_page_container,
            created=False,
            tag=tag,
            title=self.trans_str(
                title,
            ),
            icon=icon,
            tooltip=self.trans_str(tooltip),
            enabled=enabled,
            visible=visible,
        )

        if self._widget is not None:
            self._create_pages()

        return self

    def page_icon_set(
        self, tag: str, icon: Union[None, str, qtG.QPixmap, qtG.QIcon]
    ) -> None:
        """Sets the tab page icon

        Args:
            tag (str): The tag name of the page whose icon is to be set on.
            icon (Union[None, str, qtG.QPixmap, qtG.QIcon]): The icon to be set
        """
        self._widget: qtW.QTabWidget

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        assert (
            tag in self._tab_pages
        ), f"{tag=}. Not found in tab pages: {self._tab_pages=}"

        assert isinstance(
            self.icon, (type(None), str, qtG.QPixmap, qtG.QIcon)
        ), f" {self.icon=}. Must be None | str (file name)| QPixmap | QIcon"

        if icon is not None:
            if isinstance(icon, str):
                assert qtC.QFile.exists(icon), icon + " : does not exist!"
            elif isinstance(icon, qtG.QPixmap):
                pass  # All Good
            elif isinstance(icon, qtG.QIcon):
                pass  # All Good
            else:
                raise AssertionError(f"{icon=}. Not a valid icon type")

            self._widget.setTabIcon(self._tab_pages[tag].index, qtG.QIcon(icon))

    def pages_remove_all(self) -> None:
        """Removes all the pages from the Tab control"""
        for tab_page in reversed(list(self._tab_pages.values())):
            if tab_page.created:
                self.page_remove(tab_page.tag)
            else:
                self._tab_pages.pop(tab_page.tag)

    def page_remove(self, tag: str) -> None:
        """Removes a tab page from the tab widget

        Args:
            tag (str): tag name of the page to be removed

        """
        self._widget: qtW.QTabWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"
        assert (
            tag in self._tab_pages
        ), f"{tag=}. Not found in tab pages: {self._tab_pages=}"
        assert (
            self._tab_pages[tag].index >= 0
        ), f"{self._tab_pages[tag].index=} {self._tab_pages[tag]=}. Page not created!"

        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        self._tab_pages[tag].container.widgets_clear()
        self.parent_app.widget_del(window_id=window_id, container_tag=self.tag, tag=tag)
        self._widget.removeTab(self._tab_pages[tag].index)

        self._tab_pages.pop(tag)

    def page_visible_get(self, tag: str) -> bool:
        """Determines the visibility of a tab page

        Args:
            tag (str): tag name of the page to be checked

        Returns: `
            bool: True` if the tab page with the given tag name is visible, `False` otherwise

        """
        self._widget: qtW.QTabWidget

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"
        assert (
            tag in self._tab_pages
        ), f"{tag=}. Not found in tab pages: {self._tab_pages=}"

        assert (
            self._tab_pages[tag].index >= 0
        ), f"{self._tab_pages[tag]=}. Page not created!"

        return self._widget.isTabVisible(self._tab_pages[tag].index)

    def page_visible_set(self, tag: str, visible: bool) -> None:
        """Sets the visibility of a tab page

        Args:
            tag (str): tag name of the page to be set
            visible (bool): `True` to make the page visible, `False` to hide it

        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        self._widget: qtW.QTabWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"
        assert (
            tag in self._tab_pages
        ), f"{tag=}. Not found in tab pages: {self._tab_pages=}"

        assert (
            self._tab_pages[tag].index >= 0
        ), f"{self._tab_pages[tag]=}. Page not created!"

        self._widget.setTabVisible(self._tab_pages[tag].index, visible)

    def tooltip_get(self, tag: str) -> str:
        """Get the tooltip text of a tab page

        Args:
            tag (str): The tag name of the tab to get the tooltip from.

        Returns:
            str : The tooltip text for the tab page with the tag name.
        """
        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        self._widget: qtW.QTabWidget
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if self.tag == tag:
            return super().tooltip_get

        assert (
            tag in self._tab_pages
        ), f"{tag=}. Not found in Tab {self.tag=}  or tab pages: {self._tab_pages=}"

        return self._widget.tabToolTip(self._tab_pages[tag].index)

    def tooltip_set(self, tag: str, tooltip: str) -> None:
        """Sets the tooltip for a tab.

        Args:
            tag (str): tag name of the tab page to set the tooltip text
            tooltip (str): The tooltip text
        """
        self._widget: qtW.QTabWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert (
            isinstance(tag, str) and tag.strip() != ""
        ), f"{tag=}. Must be a non-empty str"

        if self.tag == tag:
            super().tooltip_set(tooltip)
        else:
            assert (
                tag in self._tab_pages
            ), f"{tag=}. Not found in Tab {self.tag=}  or tab pages: {self._tab_pages=}"

            self._widget.setTabToolTip(self._tab_pages[tag].index, tooltip)


@dataclasses.dataclass
class Treeview(_qtpyBase_Control):
    """Instantiates a Treeview control and associated properties"""

    width: int = 40
    height: int = 15
    widget_align: Align = Align.LEFT
    multiselect: bool = False
    headers: Union[list[str], tuple[str, ...]] = ()
    header_widths: Union[tuple[int, ...], list[int]] = ()  # Column widths in char
    header_font: Font = field(default_factory=Font())
    header_width_default = 15
    toplevel_items: Union[list[str], tuple[str, ...]] = ()
    _parent_list: list = None

    def __post_init__(self) -> None:
        """Constructor checks arguments and sets properties"""

        super().__post_init__()

        assert isinstance(
            self.headers, (list, tuple)
        ), f"{self.headers=}. Must be a list ot tupe of str"
        assert isinstance(
            self.header_widths, (list, tuple)
        ), f"{self.header_widths=}. Must be a list ot tupe of ints"
        assert isinstance(
            self.header_font, Font
        ), f"{self.header_font=}. Must be a Font"
        assert (
            isinstance(self.header_width_default, int) and self.header_width_default > 0
        ), f"{self.header_width_default=}. Must be an int > 0"

        for title in self.headers:
            assert isinstance(title, str), f"header title <{title}> must be a str"

        assert isinstance(
            self.toplevel_items, (list, tuple)
        ), f"{self.toplevel_items=}. Must be a list of str"

        for item in self.toplevel_items:
            assert isinstance(item, str), f"{item=}. Must be a str"

        header_widths = list(self.header_widths)

        if len(self.header_widths) == 0:
            for col_index in range(len(header_widths), len(self.headers)):
                header_widths.append(self.header_width_default)

        self.header_widths = tuple(header_widths)

        for num in self.header_widths:
            assert (
                isinstance(num, int) and num > 0
            ), f"header_width <{num}> must be int > 0"

        if self.width == -1:
            self.width = 0
            for width in self.header_widths:
                self.width += width

        self._items: dict = {}
        self.parent_list = []
        self._value = None

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates the Treeview widget

        Args:
            parent_app (QtPyApp): The parent application.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag name of the container widget that houses the Treeview.

        Returns:
            QWidget : The Treeview widget or the container housing it.
        """
        self._widget: qtW.QTreeWidget

        if self.width < 1:
            self.width = WIDGET_SIZE.width

        if self.height < 1:
            self.height = WIDGET_SIZE.height

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        char_pixel_size = self.pixel_char_size(char_height=1, char_width=1)

        if len(self.headers) == 0:
            self._widget.header().hide()

        # Add Lines - experimental and removed for now
        # line_style = """QTreeView {
        #                 show-decoration-selected: 1;
        #             }
        #
        #             QTreeView::item {
        #                  border: 1px solid #d9d9d9;
        #                 border-top-color: transparent;
        #                 border-bottom-color: transparent;
        #             }
        #
        #             QTreeView::item:hover {
        #                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #e7effd, stop: 1 #cbdaf1);
        #                 border: 1px solid #bfcde4;
        #             }
        #
        #             QTreeView::item:selected {
        #                 border: 1px solid #567dbc;
        #             }
        #
        #             QTreeView::item:selected:active{
        #                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6ea1f1, stop: 1 #567dbc);
        #             }
        #
        #             QTreeView::item:selected:!active {
        #                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6b9be8, stop: 1 #577fbf);
        #             }"""
        # self.guiwidget_get.setStyleSheet(line_style)

        self._widget.setAnimated(False)
        self._widget.setIndentation(20)
        self._widget.setSortingEnabled(True)

        self._widget.setWindowTitle(self.trans_str(self.text))

        if self.multiselect:
            self._widget.setSelectionMode(
                # SingleSelection
                qtW.QAbstractItemView.ExtendedSelection
            )
        else:
            self._widget.setSelectionMode(qtW.QAbstractItemView.SingleSelection)

        for index, width in enumerate(self.header_widths):
            self._widget.setColumnWidth(index, round(width * char_pixel_size.width))

        labels = []
        for title in self.headers:
            labels.append(self.trans_str(title))

        self._widget.setHeaderLabels(labels)
        self._widget.header().setDefaultAlignment(Align.CENTER.value)

        self.toplevel_add(self.toplevel_items)

        # self.font_set(self.header_font, self.self.calc_pixel_size,height * self.height.header())

        # Todo: Implment background colour settings and altenaterow highlighting - code below works
        # self.guiwidget_get.setAlternatingRowColors(True)
        # style = "QTreeView{alternate-background-color: wheat; background: powderblue;}"
        # self.guiwidget_get.setStyleSheet(style)

        return widget

    def _event_handler(
        self,
        *args,
    ) -> int:
        """Event handler for the TreeView widget.

        Args:
            *args: Default arguments for the TreeView widget.

        Returns:
            int : 1. If the event is accepted, -1. If the event is rejected
        """
        items: list[(str, any)] = []

        event: Action = cast(Action, args[0])

        if len(args) > 1:
            if len(args[1]) == 0:
                pass
            elif len(args[1]) == 1:
                selected_index = args[1][0]
                item_data = selected_index.data(qtC.Qt.UserRole)

                items.append(selected_index.data(qtC.Qt.DisplayRole))
                items.append(item_data)
            elif len(args[1]) == 2:
                selected_index = args[1][0]
                col = args[1][1]

                item_data = selected_index.data(col, qtC.Qt.UserRole)

                items.append(selected_index.data(col, qtC.Qt.DisplayRole))
                items.append(item_data)
            else:
                raise AssertionError(f"Unknown argument {len(args[1])} in {args[1]=}")

            items = tuple(items)

        self._value = items

        window_id = Get_Window_ID(self.parent_app, self.parent, self)

        if callable(self.callback):
            handler = _Event_Handler(parent_app=self.parent_app, parent=self)
            return handler.event(
                window_id=window_id,
                callback=self.callback,
                action=event.name,
                container_tag=self.tag,
                tag=self.tag,
                event=event,
                value=items,
                widget_dict=self.parent_app.widget_dict_get(
                    window_id=window_id, container_tag=self.container_tag
                ),
                control_name=self.__class__.__name__,
                parent=self.parent_app.widget_get(
                    window_id=window_id, container_tag=self.container_tag, tag=self.tag
                ),
            )
        else:
            return 1

    def _child_parent_get(
        self, child_item: qtW.QTreeWidgetItem, first_call: bool = True
    ) -> list[qtW.QTreeWidgetItem]:
        """
        Gets the path from the child TV item to parent TV item.  The path is made up of a lst of QTreeWidgetItem
        from child node to parent

        Args:
            child_item (qtW.QTreeWidgetItem): starting child node
            first_call (list):Path list (composed of QTreeWidgetItem) from child node to parent
        Returns
            list[qtW.QTreeWidgetItem]: Path list (composed of QTreeWidgetItem) from child node to parent
        """

        self.__dict__.setdefault(
            "parent_list", []
        )  # Bogus static var - another way :-)

        if first_call or self._parent_list is None:
            self.parent_list = []

        if child_item is not None:
            self._parent_list.append(child_item)
            self._child_parent_get(child_item.parent(), False)

        return self._parent_list

    def child_add(
        self, treeview_path: Union[str, list, tuple], items: Union[str, list, tuple]
    ) -> int:
        """
        Adds items (new label and treeview nodes) to the treeview node with the corresponding child label

        Args:
            treeview_path (Union[str, list, tuple]): Path from parent to child node
            items (Union[str, list, tuple]): Items to add to the Child node
        Returns:
            int : 1 Succeeded, -1 Failed
        """
        self._widget: qtW.QTreeWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if isinstance(treeview_path, str):
            treeview_path = (treeview_path,)

        assert isinstance(treeview_path, (list, tuple)), (
            f"parent_path <{treeview_path}> is a list | tuple of str.            "
            " Indicating level to insert . E.g. ('level1','level2'..,'leveln')"
        )

        for label in treeview_path:
            assert (
                isinstance(label, str) and label.strip() != ""
            ), f"parent_label <{treeview_path}> must be a non-empty str"

        child_label = treeview_path[-1]

        display_items, user_data = self._extract_items(items)

        parent_route = ", ".join(treeview_path)

        search_hits = self._widget.findItems(
            child_label, qtC.Qt.MatchFixedString | qtC.Qt.MatchRecursive, 0
        )

        for item in search_hits:
            item_tuple = tuple(self._child_parent_get(item))
            item_route = ", ".join((w.text(0) for w in reversed(item_tuple)))

            if parent_route == item_route:
                parent_item = item_tuple[0]
                for index, text in enumerate(display_items):
                    assert (
                        isinstance(text, str) and text.strip() != ""
                    ), f"treeview display item <{text}> must a non-empty str"

                    child_item = qtW.QTreeWidgetItem(parent_item)
                    item_data = self.Item_Data(user_data=user_data[index])  # TODO Fix
                    child_item.setData(0, qtC.Qt.UserRole, item_data)
                    child_item.setText(
                        0,
                        self.trans_str(text),
                    )  # TODO, Translate here?
                    parent_item.addChild(child_item)
                return 1
        return -1

    def child_checked(
        self, treeview_path: Union[str, list, tuple], checked: bool
    ) -> Literal[1, -1]:
        """Checks a child node in the treeview

        Args:
            treeview_path (Union[str, list, tuple]): Path from parent to child node
            checked (bool): True - Checked, False - Unchecked

        Returns:
            int : 1 Succeeded, -1 Failed
        """
        self._widget: qtW.QTreeWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if isinstance(treeview_path, str):
            treeview_path = (treeview_path,)

        assert isinstance(treeview_path, (list, tuple)), (
            f"parent_path <{treeview_path}> is a list | tuple of str.                  "
            "           Indicating level to insert . E.g."
            " ('level1','level2'..,'leveln')"
        )

        for label in treeview_path:
            assert (
                isinstance(label, str) and label.strip() != ""
            ), f"parent_label <{treeview_path}> must be a non-empty str"

        assert isinstance(checked, bool), f"checked <{checked}> must be bool"

        checked_label = treeview_path[-1]

        parent_route = ", ".join(treeview_path)

        search_hits = self._widget.findItems(
            checked_label.strip(),
            qtC.Qt.MatchFixedString | qtC.Qt.MatchRecursive,
            0,
        )

        for item in search_hits:
            item_tuple = tuple(self._child_parent_get(item))

            if len(item_tuple) > 0:
                item_route = ", ".join((w.text(0) for w in reversed(item_tuple)))

                if parent_route == item_route:
                    child_item = item_tuple[0]

                    if checked:
                        child_item.setCheckState(0, qtC.Qt.Checked)
                    else:
                        child_item.setCheckState(0, qtC.Qt.Unchecked)
                    return 1
        return -1

    def toplevel_add(self, items: Union[list[str], tuple[str, ...]]) -> None:
        """Adds items to the top level of the Tree view.

        Args:
            items (Union[list[str], tuple[str, ...]]): The items to add to the tree widget.
        """
        self._widget: qtW.QTreeWidget

        # items, user_data = self._extract_items(items)
        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        for text in items:
            item = qtW.QTreeWidgetItem(self._widget)
            item.setText(0, self.trans_str(text))  # TODO, Translate here?
            self._widget.addTopLevelItem(item)

    def toplevel_items_get(self) -> list[str]:
        """Gets the top level items in the Tree view

        Returns:
            list[str] :A list of strings.
        """

        self._widget: qtW.QTreeWidget

        root = self._widget.invisibleRootItem()
        child_count = root.childCount()

        items = []

        for i in range(child_count):
            items.append = root.child(i).text(
                0
            )  # TODO col should be able to be set by user

        return items

    def value_get(self) -> tuple[(str, any)]:
        """Returns a value tuple of the current node of the the Tree view.

        Returns:
            tuple[(str,any)] : Current Tree view node value tuple (node text, node user value)
        """

        return tuple(self._value)

    def value_set(self, value: str, col: int = 0) -> None:
        """Sets the Tree view col value of the current node

        Args:
            value (str): The value to set.
            col (int): The column to set. Default is 0.
        """
        self._widget: qtW.QTreeWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        assert isinstance(value, str), "value must be str"
        assert isinstance(col, int), f"{col=}. Must be an int"

        self._widget.currentItem().setText(
            0, self.trans_str(value) if self.trans_get else str(value)
        )

    def widget_set(
        self, treeview_path: Union[str, list, tuple], col: int, widget
    ) -> None:
        """Takes a treeview path, column number, a widget and sets the widget in the specified node in the Tree view
        TODO Needs fixing

        Args:
            treeview_path (Union[str, list, tuple]): This is a list of strings that indicate the path to the item in the
                tree view.
            col (int): The column number to place the widget in
            widget (_qtpyBase_Control): The GUI widget to be inserted.
        """
        self._widget: qtW.QTreeWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        if isinstance(treeview_path, str):
            treeview_path = (treeview_path,)

        assert isinstance(treeview_path, (list, tuple)), (
            f"parent_path <{treeview_path}> is a list | tuple of str.                  "
            "   Indicating level to insert . E.g. ('level1','level2'..,'leveln')"
        )

        for label in treeview_path:
            assert (
                isinstance(label, str) and label.strip() != ""
            ), f"parent_label <{treeview_path}> must be a non-empty str"

        child_label = treeview_path[-1]

        assert isinstance(col, int) and col >= 0, f"col <{col}> must be an int >= 0"

        parent_route = ", ".join(treeview_path)

        search_hits = self._widget.findItems(
            child_label, qtC.Qt.MatchFixedString | qtC.Qt.MatchRecursive, 0
        )

        for item in search_hits:
            item_tuple = tuple(self._child_parent_get(item))
            item_route = ", ".join((w.text(0) for w in reversed(item_tuple)))

            if parent_route == item_route:
                # child_item = qtW.QTreeWidgetItem(item_tuple[0])

                tag = str(col)

                if not isinstance(widget, (list, tuple)):
                    widget = (widget,)

                for index, control in enumerate(widget):
                    control.tag_set(control.tag_get + tag + str(index))

                # controls = Ctrlgroup(
                #    controls=widget, orientation=LAYOUT.VERTICAL, tag=tag
                # )
                # controls.app_instance_set(grid_def.app_instance_get)

                # widget_layout = widget_layout._ctrlgroup_control()
                # widget_layout.controldef_set(controls)
                # widget_container = widget_layout.create_widget(self.parent_get, False)

                # item_data = child_item.data(QtCore.Qt.UserRole)
                #
                # item_data = item_data._replace(
                #     current_value=item_data.current_value,
                #     prev_value=item_data.prev_value,
                #     data_type=item_data.data_type,
                #     user_data=item_data.user_data,
                #     widget_dict=widget_layout.control_widgets_get,
                # )
                #
                # child_item.setData(QtCore.Qt.UserRole, item_data)

                # self.guiwidget_get.setItemWidget(child_item, col, widget_container)

    def _extract_items(
        self, items: Union[str, list, tuple, dict]
    ) -> tuple[list[str], list[any]]:
        """Returnsa tuple of two lists, the first list being the display strings, and the second list being the user data

        Args:
            items (Union[str, list, tuple, dict]): The items to display. Can be a list, tuple or dict.

        Returns:
            tuple[list[str], list[any]]: The display strings and user data
        """
        assert isinstance(items, (str, list, tuple, dict)), (
            f"items <{items}> must be a dict {{<str>:<non-str>}},{{<non-str>:<str>}}, a"
            " str, a list or tuple of str"
        )

        if isinstance(items, str):
            return [items], [None]
        if isinstance(items, dict):
            for key, value in items.items():
                if isinstance(key, str):
                    return list(items.keys()), [[None] * len(items.keys())]
                if isinstance(value, str):
                    return list(items.values()), [[None] * len(items.values())]

                raise AssertionError(
                    f"items <{items}> dict must be"
                    " {<str>:<non-str>},{<non-str>:<str>}!"
                )
        elif isinstance(items, (list, tuple)):
            display_items = []
            user_data = []

            for item in items:
                if isinstance(item, str):  # No user data
                    display_items.append(item)
                    user_data.append(None)
                elif isinstance(item, (list, tuple)):  # User data present
                    assert len(item) == 2, (
                        f"The item <{item}> list,tuple must contain 2 elements"
                        " (display_string,user_data)"
                    )
                    display_items.append(item[0])
                    user_data.append(item[1])

            return display_items, user_data
        return [""], [None]

    def _selected_levelitems_get(self):
        """
        Private function to return the selected treeview iteems

        Returns:
            (bool,list,items) -- [description]
        """
        self._widget: qtW.QTreeWidget

        if self._widget is None:
            raise RuntimeError(f"{self._widget=}. Not set")

        items = self._widget.selectedItems()
        levels = set()

        for item in items:
            level = 0
            index = self._widget.indexFromItem(item, 0)

            while index.parent().isValid():
                index = index.parent()
                level += 1

            levels.add(level)

        if len(levels) == 1:
            return (True, list(levels)[0], items)
        return (False, list(levels), items)


@dataclasses.dataclass
class Slider(_qtpyBase_Control):
    """Instantiates a Slider widget and associated properties"""

    range_min: int = 0
    range_max: int = 100
    page_step: int = 10
    single_step: int = 1
    orientation: str = "horizontal"

    def __post_init__(self) -> None:
        """Initializes the slider object."""
        assert (
            isinstance(self.range_min, int) and self.range_min >= 0
        ), f"{self.range_min=}. Must be an int >= 0"
        assert (
            isinstance(self.range_max, int)
            and self.range_max > 0
            and self.range_max > self.range_min
        ), f"{self.range_max=}. Must be an int > 0 and < {self.range_min=}."
        assert (
            isinstance(self.page_step, int) and self.page_step > 0
        ), f"{self.page_step=}. Must be an int > 0"
        assert (
            isinstance(self.single_step, int) and self.single_step > 0
        ), f"{self.single_step=}. Must be an int > 0"
        assert isinstance(self.orientation, str) and self.orientation in [
            "horizontal",
            "vertical",
        ], f"{self.orientation=}. Must be 'horizontal' or'vertical'"

        super().__post_init__()

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates a Slider widget.

        Args:
            parent_app (QtPyApp): The parent app.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag of the container that the widget is in.

        Returns:
            qtW.QWidget : The slider widget
        """
        if self.height == -1:
            self.height = WIDGET_SIZE.height

        if self.width == -1:
            self.width = WIDGET_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self._widget: qtW.QSlider

        self._widget.setMinimum(self.range_min)
        self._widget.setMaximum(self.range_max)
        self._widget.setPageStep(self.page_step)
        self._widget.setSingleStep(self.single_step)

        if self.orientation == "horizontal":
            self._widget.setOrientation(qtC.Qt.Horizontal)
        else:
            self._widget.setOrientation(qtC.Qt.Vertical)

        return widget

    def value_get(self) -> int:
        """Gets the value of the slider.

        Returns:
            int: The value of the slider.
        """
        self._widget: qtW.QSlider

        return self._widget.value()

    def value_set(self, value: int) -> None:
        """Sets the value of the slider.

        Args:
            value (int): The value to set the slider to.
        """
        assert (
            isinstance(value, int)
            and value >= self.range_min
            and value <= self.range_max
        ), f"{value=}. Must be an int >= {self.range_min} and < {self.range_max}."
        self._widget: qtW.QSlider

        self._widget.setValue(value)


@dataclasses.dataclass
class Spinbox(_qtpyBase_Control):
    """Instantiates a Spinbox widget and associated properties"""

    range_min: int = 0
    range_max: int = 100
    single_step: int = 1
    suffix: str = ""
    prefix: str = ""

    def __post_init__(self) -> None:
        """Initializes the spinbox object."""
        assert (
            isinstance(self.range_min, int) and self.range_min >= 0
        ), f"{self.range_min=}. Must be an int >= 0"
        assert (
            isinstance(self.range_max, int)
            and self.range_max > 0
            and self.range_max > self.range_min
        ), f"{self.range_max=}. Must be an int > 0 and < {self.range_min=}."
        assert (
            isinstance(self.single_step, int) and self.single_step > 0
        ), f"{self.single_step=}. Must be an int > 0"
        assert isinstance(self.suffix, str), f"{self.suffix=}. Must be a str"
        assert isinstance(self.prefix, str), f"{self.prefix=}. Must be a str"

        super().__post_init__()

    def _create_widget(
        self, parent_app: QtPyApp, parent: qtW.QWidget, container_tag: str = ""
    ) -> qtW.QWidget:
        """Creates a Spinbox widget.

        Args:
            parent_app (QtPyApp): The parent app.
            parent (qtW.QWidget): The parent widget.
            container_tag (str): The tag of the container that the widget is in.

        Returns:
            qtW.QWidget : The spinbox widget
        """
        if self.height == -1:
            self.height = WIDGET_SIZE.height

        if self.width == -1:
            self.width = WIDGET_SIZE.width

        widget = super()._create_widget(
            parent_app=parent_app, parent=parent, container_tag=container_tag
        )

        self._widget: qtW.QSpinBox

        self._widget.setRange(self.range_min, self.range_max)
        self._widget.setSingleStep(self.single_step)

        if self.suffix != "":
            self._widget.setSuffix(self.suffix)
        if self.prefix != "":
            self._widget.setPrefix(self.prefix)

        return widget

    def value_get(self) -> int:
        """Gets the value of the spinbox.

        Returns:
            int: The value of the spinbox.
        """

        self._widget: qtW.QSpinBox
        return self._widget.value()

    def value_set(self, value: int) -> None:
        """Sets the value of the spinbox.

        Args:
            value (int): The value to set the spinbox to.
        """
        assert (
            isinstance(value, int)
            and value >= self.range_min
            and value <= self.range_max
        ), f"{value=}. Must be an int >= {self.range_min} and < {self.range_max}."
        self._widget: qtW.QSpinBox
        self._widget.setValue(value)
