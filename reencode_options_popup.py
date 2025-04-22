"""
Implements a popup dialog that displays a list of video re-encoding/transcoding
and joining options to the user.

Copyright (C) 2025  David Worboys (alumnus of Moyhu Primary School and other institutions)

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
from typing import cast

from QTPYGUI import qtpygui as qtg, popups as popups

import sys_consts


@dataclasses.dataclass
class Reencode_Options(qtg.PopContainer):
    """
    A pop-up dialog that presents the user with a list of re-encoding/transcoding
    and video joining options as radio buttons. The selected option is returned
    when the user clicks "OK".

    The `transcode_options` and `join_options` dictionaries define the available
    choices. The key of each dictionary item is the text displayed to the user,
    and the value is a tag associated with that option.

    Tooltips for options can be provided by separating the option text from the
    tooltip text with " :: ". For example: "High Quality :: Best visual fidelity".

    Attributes:
        message (str): A message displayed above the transcoding options.
        transcode_options (dict[str, str]): A dictionary of transcoding options
            (display text: tag).
        join_options (dict[str, str]): A dictionary of video joining options
            (display text: tag).
        translate (bool): If True, the displayed text will be marked for
            translation (default: True).

    Internal Attributes:
        _transcode_option (str): Stores the tag of the initially selected
            transcode option.
        _join_option (str): Stores the tag of the initially selected join option.
    """

    message: str = ""
    transcode_options: dict[str, str] = dataclasses.field(default_factory=dict)
    join_options: dict[str, str] = dataclasses.field(default_factory=dict)
    translate: bool = True

    _transcode_option: str = ""
    _join_option: str = ""

    def __post_init__(self) -> None:
        """
        Initializes the Reencode_Options dialog.

        This method:
        - Calls the parent class's `__post_init__` method.
        - Validates the types and content of the input arguments.
        - Creates and populates radio buttons for the transcoding and joining options.
        - Adds "OK" and "Cancel" buttons to the dialog.
        - Implements a tabbed interface if both transcoding and joining options are provided,
          allowing the user to switch between them.
        """
        super().__post_init__()
        assert isinstance(self.transcode_options, dict), (
            f"{self.transcode_options=}. Must be a dict [text:tag]"
        )
        assert isinstance(self.join_options, dict), (
            f"{self.join_options=}. Must be a dict [text:tag]"
        )
        assert self.transcode_options or self.join_options, (
            f"{self.transcode_options=} or {self.join_options=}. Must have at least one transcode or join option"
        )
        assert isinstance(self.message, str), f"{self.message=}. Must be str"

        def _Populate_Options(
            options: dict[str, str], container: qtg.VBoxContainer
        ) -> tuple[str, int]:
            """
            Populates the given container with radio buttons based on the provided options.

            This helper function also tracks the maximum width of the options to size
            the dialog appropriately and identifies the initially selected option (the first one).

            Args:
                options (dict[str, str]): A dictionary where the key is the display text
                    and the value is the tag for each option.
                container (qtg.VBoxContainer): The vertical box container to which the
                    radio buttons will be added.

            Returns:
                tuple[str, int]: A tuple containing:
                    - The tag of the initially selected option (the first one).
                    - The maximum width (in characters) of all the displayed options.
            """
            max_width = 0
            original_option_tag = ""

            for index, (option_text, tag) in enumerate(options.items()):
                tooltip = ""
                if "::" in option_text:
                    option_text, tooltip = option_text.split("::")

                if index == 0:
                    original_option_tag = tag

                item_tag = f"{tag}|{index}".strip().replace(" ", "")
                max_width = max(max_width, len(option_text) + 8)

                container.add_row(
                    qtg.RadioButton(
                        text=f"{sys_consts.SDELIM}{option_text}{sys_consts.SDELIM}",
                        callback=self.event_handler,
                        tag=item_tag,
                        checked=True if index == 0 else False,
                        translate=self.translate,
                        tooltip=tooltip,
                    )
                )

            return original_option_tag, max_width

        transcode_option_container = qtg.VBoxContainer(
            tag="transcode_container", text=self.message
        )
        join_option_container = qtg.VBoxContainer(
            tag="join_container", text=self.message
        )

        self._transcode_option, transcode_width = _Populate_Options(
            self.transcode_options, transcode_option_container
        )
        self._join_option, join_width = _Populate_Options(
            self.join_options, join_option_container
        )

        assert transcode_width > 0 or join_width > 0, (
            f"Error: {transcode_width=}, {join_width=}"
        )

        control_container = qtg.VBoxContainer(
            tag="option_controls", align=qtg.Align.TOPLEFT
        )

        self.container.add_row(control_container)

        # Creates a GUI for the dialog box with a list of options, potentially using tabs.
        tab = qtg.Tab(
            tag="option_tab",
            callback=self.event_handler,
            width=max(transcode_width, join_width),
            height=9,
        )

        if self.transcode_options:
            transcode_option_container.width = transcode_width
            tab.page_add(
                tag="transcode_page",
                title="Transcode",
                control=transcode_option_container,
            )

        if self.join_options:
            control_container.add_row(
                qtg.Switch(
                    tag="transcode_join",
                    label="Transcode",
                    text="Join",
                    callback=self.event_handler,
                )
            )

            join_option_container.width = join_width
            tab.page_add(
                tag="join_page",
                title="Join",
                control=join_option_container,
                enabled=False,
            )

        control_container.add_row(tab)
        self.container.add_row(qtg.Spacer())
        self.container.add_row(
            qtg.Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            )
        )

        return None

    def event_handler(self, event: qtg.Action) -> None:
        """
        Handles control events within the PopOptions dialog.

        This method is called when user interacts with widgets in the dialog,
        such as clicking buttons or changing the state of the "Transcode/Join" switch.

        - If the "OK" button is clicked, it retrieves the selected option, stores it
          in the `_result` attribute, and closes the dialog.
        - If the "Cancel" button is clicked, it prompts the user for confirmation
          and closes the dialog with an empty string in `_result` if confirmed.
        - If the "Transcode/Join" switch is toggled, it enables or disables the
          "Join" tab and selects the appropriate tab.

        Args:
            event (Action): The event object containing information about the
                triggered event.
        """
        match event.event:
            case qtg.Sys_Events.WINDOWPOSTOPEN:
                # Initially disable the Join tab if it exists
                if event.widget_exist(
                    container_tag="option_controls", tag="transcode_join"
                ) and event.widget_exist(container_tag="option_tab", tag="join_page"):
                    tab: qtg.Tab = cast(
                        qtg.Tab,
                        event.widget_get(
                            container_tag="option_controls", tag="option_tab"
                        ),
                    )
                    tab.enable_set(tag="join_page", enable=False)

            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        selected_option = self._get_selection_option(event)
                        self._result = selected_option
                        self.close()
                    case "cancel":
                        if (
                            popups.PopYesNo(
                                container_tag="discard_selection",
                                title="Stop Transcode/Join..",
                                message="Stop Transcode/Join?",
                            ).show()
                            == "yes"
                        ):
                            self._result = ""
                            self.close()
                    case "transcode_join":
                        # Handle the toggle of the Transcode/Join switch to show/hide tabs
                        if event.widget_exist(
                            container_tag="option_controls", tag="transcode_join"
                        ) and event.widget_exist(
                            container_tag="option_tab", tag="join_page"
                        ):
                            tab: qtg.Tab = cast(
                                qtg.Tab,
                                event.widget_get(
                                    container_tag="option_controls", tag="option_tab"
                                ),
                            )

                            if event.value:  # True indicates "Join" is selected
                                tab.enable_set(tag="join_page", enable=True)
                                tab.enable_set(tag="transcode_page", enable=False)
                                tab.select_tab(tag_name="join_page")
                            else:  # False indicates "Transcode" is selected
                                tab.enable_set(tag="join_page", enable=False)
                                tab.enable_set(tag="transcode_page", enable=True)
                                tab.select_tab(tag_name="transcode_page")

        return None

    def _get_selection_option(self, event: qtg.Action) -> str:
        """
        Returns a string indicating the selected option ("transcode|tag" or "join|tag").

        This method iterates through the radio buttons in the currently active
        option container (either "transcode_container" or "join_container") and
        returns a formatted string containing the option type and its associated tag.

        Args:
            event (qtg.Action): The event object (used to check the state of the
                "Transcode/Join" switch).

        Returns:
            str: A string in the format "transcode|option_tag" or "join|option_tag"
                if an option is selected; otherwise, an empty string.
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be a qtg.Action"

        # Default to transcode options
        container_tag = "transcode_container"
        options = self.transcode_options
        option_type = "transcode"
        selected_option = ""

        # Check if the Join option is enabled and selected via the switch
        if event.widget_exist(
            container_tag="option_controls", tag="transcode_join"
        ) and event.widget_exist(container_tag="option_tab", tag="join_page"):
            if event.value_get(
                container_tag="option_controls", tag="transcode_join"
            ):  # True means "Join" is active
                container_tag = "join_container"
                option_type = "join"
                options = self.join_options

        # Iterate through the options in the active container to find the selected radio button
        for index, (option_text, tag) in enumerate(options.items()):
            item_tag = f"{tag}|{index}".strip().replace(" ", "")
            if event.value_get(container_tag=container_tag, tag=item_tag):
                selected_option = f"{option_type}|{tag}"
                break

        return selected_option
