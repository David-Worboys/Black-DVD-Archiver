"""
    Implements a popup dialog that allows a user to configure the text and 
    colours of the text on a DVD menu.

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
import copy
import dataclasses

import dvdarch_utils
import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from configuration_classes import DVD_Menu_Settings

# Tell Black to leave this block alone (realm of isort)
# fmt: off


# fmt: on


@dataclasses.dataclass
class DVD_Menu_Config_Popup(qtg.PopContainer):
    title: str = ""

    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)
    _default_font: str = "IBMPlexMono-SemiBold.ttf"  # Packaged with DVD Archiver
    _startup: bool = True

    def __post_init__(self) -> None:
        """Sets-up the form"""

        assert (
            isinstance(self.title, str) and self.title.strip() != ""
        ), f"{self.title=}. Must be a non-empty str"

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
                self._font_combo_init(event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        self._save_to_db(event)
                        super().close()

                    case "cancel":
                        super().close()
            case qtg.Sys_Events.TEXTCHANGED:
                if not self._startup:
                    self._font_combo_change(event)
            case qtg.Sys_Events.INDEXCHANGED:
                if not self._startup:
                    self._font_combo_change(event)

    def _font_combo_init(self, event) -> None:
        """Initializes the font combo boxes

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        file_handler = file_utils.File()
        dvd_menu_settings = DVD_Menu_Settings()

        event.value_set(
            container_tag="menu_properties",
            tag="buttons_per_page",
            value=dvd_menu_settings.buttons_per_page,
        )
        event.value_set(
            container_tag="menu_properties",
            tag="buttons_across",
            value=dvd_menu_settings.buttons_across,
        )

        for item in ("menu_text", "button_text"):
            background_color = (
                dvd_menu_settings.menu_background_color
                if item == "menu_text"
                else dvd_menu_settings.button_background_color
            )
            font_color = (
                dvd_menu_settings.menu_font_color
                if item == "menu_text"
                else dvd_menu_settings.button_font_color
            )
            font = (
                dvd_menu_settings.menu_font
                if item == "menu_text"
                else dvd_menu_settings.button_font
            )

            _, font_name, extn = file_handler.split_file_path(font)

            font_point_size = (
                dvd_menu_settings.menu_font_point_size
                if item == "menu_text"
                else dvd_menu_settings.button_font_point_size
            )

            if not font_name:
                font_name = self._default_font

            text_color_combo: qtg.ComboBox = event.widget_get(
                container_tag=item,
                tag="text_color",
            )

            background_color_combo: qtg.ComboBox = event.widget_get(
                container_tag=item, tag="background_color"
            )

            font_combo: qtg.ComboBox = event.widget_get(
                container_tag=item, tag="title_font"
            )

            font_size: qtg.Spinbox = event.widget_get(
                container_tag=item, tag="font_size"
            )

            if item == "button_text":
                transparency = dvd_menu_settings.button_background_transparency

                background_transparency: qtg.Spinbox = event.widget_get(
                    container_tag=item, tag="transparency"
                )

                background_transparency.value_set(transparency)

            background_color_combo.select_text(background_color, partial_match=False)
            text_color_combo.select_text(font_color, partial_match=False)
            font_combo.select_text(f"{font_name}{extn}", partial_match=False)
            font_size.value_set(font_point_size)

        self._startup = False
        event.container_tag = "menu_text"
        self._font_combo_change(event)
        event.container_tag = "button_text"
        self._font_combo_change(event)

    def _font_combo_change(self, event: qtg.Action) -> None:
        """Changes the font of the colour patch of the title font text when the font
        selection changes

        Args:
            event (qtg.Action): The triggering event
        """
        if event.container_tag in ("menu_text", "button_text"):
            if event.container_tag == "menu_text":
                example_text = " Menu Title "

                text_color_combo: qtg.ComboBox = event.widget_get(
                    container_tag="menu_text",
                    tag="text_color",
                )

                background_color_combo: qtg.ComboBox = event.widget_get(
                    container_tag="menu_text", tag="background_color"
                )

                font_combo: qtg.ComboBox = event.widget_get(
                    container_tag="menu_text", tag="title_font"
                )

                font_size: qtg.Spinbox = event.widget_get(
                    container_tag="menu_text", tag="font_size"
                )

                image: qtg.Image = event.widget_get(
                    container_tag="menu_text",
                    tag="example",
                )

                transparency = 100
            else:
                example_text = " Button Title "

                text_color_combo: qtg.ComboBox = event.widget_get(
                    container_tag="button_text", tag="text_color"
                )

                background_color_combo: qtg.ComboBox = event.widget_get(
                    container_tag="button_text", tag="background_color"
                )

                font_combo: qtg.ComboBox = event.widget_get(
                    container_tag="button_text", tag="title_font"
                )

                font_size: qtg.Spinbox = event.widget_get(
                    container_tag="button_text", tag="font_size"
                )

                transparency: int = event.value_get(
                    container_tag="button_text", tag="transparency"
                )

                image: qtg.Image = event.widget_get(
                    container_tag="button_text",
                    tag="example",
                )

            char_pixel_size = qtg.g_application.char_pixel_size(
                font_path=font_combo.value_get().data
            )

            pointsize, png_bytes = dvdarch_utils.get_font_example(
                font_file=font_combo.value_get().data,
                # pointsize=font_size.value_get(),
                text=example_text,
                text_color=text_color_combo.value_get().data,
                background_color=background_color_combo.value_get().data,
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
                        f" {sys_consts.SDELIM} {font_combo.value_get().display } {sys_consts.SDELIM} Can"
                        " Not Be Rendered!"
                    ),
                ).show()

    def _save_to_db(self, event: qtg.Action) -> None:
        """Saves the current configuration to the database

        Args:
            event (qtg.Action): The triggering event
        """
        dvd_menu_settings = DVD_Menu_Settings()

        dvd_menu_settings.buttons_per_page = event.value_get(
            container_tag="menu_properties", tag="buttons_per_page"
        )
        dvd_menu_settings.buttons_across = event.value_get(
            container_tag="menu_properties", tag="buttons_across"
        )

        for item in ("menu_text", "button_text"):
            text_color_combo: qtg.ComboBox = event.widget_get(
                container_tag=item,
                tag="text_color",
            )

            background_color_combo: qtg.ComboBox = event.widget_get(
                container_tag=item, tag="background_color"
            )

            font_combo: qtg.ComboBox = event.widget_get(
                container_tag=item, tag="title_font"
            )

            font_size: qtg.Spinbox = event.widget_get(
                container_tag=item, tag="font_size"
            )

            if item == "menu_text":
                dvd_menu_settings.menu_font = font_combo.value_get().data
                dvd_menu_settings.menu_font_color = text_color_combo.value_get().data
                dvd_menu_settings.menu_font_point_size = font_size.value_get()
                dvd_menu_settings.menu_background_color = (
                    background_color_combo.value_get().data
                )
            else:
                background_transparency: qtg.Spinbox = event.widget_get(
                    container_tag=item, tag="transparency"
                )
                dvd_menu_settings.button_font = font_combo.value_get().data
                dvd_menu_settings.button_font_color = text_color_combo.value_get().data
                dvd_menu_settings.button_font_point_size = font_size.value_get()
                dvd_menu_settings.button_background_color = (
                    background_color_combo.value_get().data
                )
                dvd_menu_settings.button_background_transparency = (
                    background_transparency.value_get()
                )

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""

        def _text_config(tag: str, title: str) -> qtg.FormContainer:
            return qtg.FormContainer(tag=tag, text=title).add_row(
                qtg.ComboBox(
                    tag="text_color",
                    label="Text Color",
                    width=20,
                    callback=self.event_handler,
                    items=color_list,
                    display_na=False,
                    translate=False,
                ),
                qtg.ComboBox(
                    tag="background_color",
                    label="Background Color",
                    width=20,
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
                        None
                        if tag == "menu_text"
                        else qtg.Spinbox(
                            label="Transparency",
                            tag="transparency",
                            range_min=0,
                            range_max=100,
                            width=4,
                            callback=self.event_handler,
                            buddy_control=qtg.Label(text="%", width=1),
                        )
                    ),
                ),
                qtg.Image(
                    tag="example",
                    height=4,
                    width=20,
                ),
            )

        color_list = [
            qtg.Combo_Item(display=color, data=color, icon=None, user_data=color)
            for color in dvdarch_utils.get_color_names()
        ]

        font_list = [
            qtg.Combo_Item(display=font[0], data=font[1], icon=None, user_data=font)
            for font in dvdarch_utils.get_fonts()
        ]

        dvd_menu_properties = qtg.VBoxContainer(
            tag="menu_properties", text="Menu Properties", align=qtg.Align.LEFT
        ).add_row(
            qtg.HBoxContainer(margin_left=4).add_row(
                qtg.Spinbox(
                    label="Buttons Per Page",
                    tag="buttons_per_page",
                    tooltip="The number of DVD menu buttons on a DVD menu page",
                    range_min=1,
                    range_max=6,
                    width=4,
                    callback=self.event_handler,
                    buddy_control=qtg.Spinbox(
                        label="Buttons Across",
                        tag="buttons_across",
                        tooltip="The number of DVD menu buttons across a DVD menu page",
                        range_min=1,
                        range_max=4,
                        width=4,
                        callback=self.event_handler,
                    ),
                )
            ),
            qtg.HBoxContainer().add_row(
                _text_config("menu_text", "Menu Font"),
                _text_config("button_text", "Button Font"),
            ),
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.BOTTOMRIGHT
        )

        control_container.add_row(
            dvd_menu_properties,
            # image_button_properties,
            qtg.Command_Button_Container(
                ok_callback=self.event_handler,
                cancel_callback=self.event_handler,
                margin_right=0,
            ),
        )

        return control_container
