"""
    Implements a popup dialog that allows the user to control project settings 
    - create/select/detete a project

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

import file_utils
import popups
import qtgui as qtg
import sqldb
import sys_consts
from utils import Text_To_File_Name

# fmt: on


@dataclasses.dataclass
class Project_Settings_Popup(qtg.PopContainer):
    """Project Settings configuration popup"""

    current_project: str = ""
    project_path: str = ""
    extn: str = ""
    ignored_project: str = ""

    # Private instance variable
    _db_settings: sqldb.App_Settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

    def __post_init__(self) -> None:
        """Sets-up the form"""

        assert isinstance(
            self.current_project, str
        ), f"{self.current_project=}. Must be a string"
        assert (
            isinstance(self.project_path, str) and self.project_path.strip() != ""
        ), f"{self.project_path=}. Must be a non-empty string"
        assert (
            isinstance(self.extn, str) and self.extn != ""
        ), f"{self.extn=}. Must be a non-empty str"
        assert isinstance(
            self.ignored_project, str
        ), f"{self.ignored_project=}. Must be a string"

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
                project_combo: qtg.ComboBox = event.widget_get(
                    container_tag="project_controls", tag="existing_projects"
                )

                if self.current_project:
                    project_combo.select_text(self.current_project, partial_match=True)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "delete_project":
                        self._delete_project(event)
                    case "new_project":
                        self._new_project(event)
                    case "ok":
                        if self._process_ok(event) == 1:
                            super().close()
                    case "cancel":
                        if self._process_cancel(event) == 1:
                            super().close()

            case qtg.Sys_Events.INDEXCHANGED:
                event.value_set(
                    container_tag="project_controls",
                    tag="current_project",
                    value=event.value.display,
                )

    def _new_project(self, event: qtg.Action):
        """Create a new project
        Args:
            event:qtg.Action: The triggering event
        """

        project_name = popups.PopTextGet(
            title="Enter Project Name",
            label="Project Name:",
            label_above=False,
        ).show()

        if project_name.strip():
            project_combo: qtg.ComboBox = event.widget_get(
                container_tag="project_controls",
                tag="existing_projects",
            )

            if project_combo.select_text(project_name, partial_match=False) >= 0:
                popups.PopMessage(
                    title="Invalid Project Name",
                    message="A Project Wih That Name Already Exists!",
                ).show()
            else:
                project_combo.value_set(
                    qtg.Combo_Data(
                        index=-1,
                        display=Text_To_File_Name(project_name).replace("_", " "),
                        data=Text_To_File_Name(project_name),
                        user_data=None,
                    )
                )

    def _delete_project(self, event: qtg.Action) -> None:
        """Deletes a project by removing the corrosponding python shelf files

        Args:
            event (qtg.Action): Triggering event
        """

        file_handler = file_utils.File()

        db_extn = self.extn.split(".")[1]
        project: str = event.value_get(
            container_tag="project_controls", tag="current_project"
        )
        project_file = Text_To_File_Name(project)

        project_combo: qtg.ComboBox = event.widget_get(
            container_tag="project_controls",
            tag="existing_projects",
        )

        delete_file = False

        for extn in ("dir", "dat", "bak"):
            dir_path, _, _ = file_handler.split_file_path(self.ignored_project)

            project_path = file_handler.file_join(
                dir_path, f"{project_file}.{db_extn}", extn
            )

            if file_handler.file_exists(dir_path, f"{project_file}.{db_extn}", extn):
                if extn == "dir":
                    if (
                        popups.PopYesNo(
                            title="Delete Project...",
                            message=(
                                "Delete Project"
                                f" {sys_consts.SDELIM}{project}{sys_consts.SDELIM}?"
                                " \nWarning All Project Data Except Source Video Files"
                                " Will Be Lost!"
                            ),
                        ).show()
                        == "yes"
                    ):
                        delete_file = True

                if delete_file and file_handler.remove_file(project_path) == 1:
                    project_combo: qtg.ComboBox = event.widget_get(
                        container_tag="project_controls",
                        tag="existing_projects",
                    )

                    combo_data: qtg.Combo_Data = project_combo.value_get()

                    if combo_data.display == project and combo_data.index >= 0:
                        project_combo.value_remove(combo_data.index)
                else:
                    popups.PopError(
                        title="Failed To Delete Project...",
                        message=(
                            "Failed To Delete Project"
                            f" {sys_consts.SDELIM}{project}{sys_consts.SDELIM}!"
                        ),
                    ).show()
                    break
            else:
                project: str = event.value_get(
                    container_tag="project_controls", tag="current_project"
                )

            if self._db_settings.setting_exist("latest_project"):
                if project_combo.count_items > 0:
                    self._db_settings.setting_set("latest_project", project)
                else:
                    self._db_settings.setting_set("latest_project", "")

    def _process_ok(self, event: qtg.Action) -> int:
        """
        Handles processing the ok button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if the ok process id good, -1 otherwise
        """
        project: str = event.value_get(
            container_tag="project_controls", tag="current_project"
        )

        self.set_result(project)

        return 1

    def _process_cancel(self, event: qtg.Action) -> int:
        """
        Handles processing the ok button.
        Args:
            event (qtg.Action): The triggering event.
        Returns:
            int: Returns 1 if the ok process is good, -1 otherwise
        """
        project: str = event.value_get(
            container_tag="project_controls", tag="current_project"
        )
        if project != self.current_project:
            if (
                popups.PopYesNo(
                    title="Project Changed...",
                    message=(
                        "Discard Project Change To "
                        f" {sys_consts.SDELIM}{project}{sys_consts.SDELIM}?"
                    ),
                ).show()
                == "yes"
            ):
                return 1
            else:
                return -1

        return 1

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        project_control_container = qtg.VBoxContainer(
            tag="project_controls", align=qtg.Align.TOPRIGHT, margin_right=0
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.BOTTOMRIGHT, margin_right=9
        )

        file_handler = file_utils.File()

        file_extn = self.extn.split(".")[-1].lstrip(".")

        file_list: file_utils.File_Result = file_handler.filelist(
            path=self.project_path,
            extensions=(file_extn,),
        )

        combo_items = []

        for item in file_list.files:
            if item.rstrip(self.extn).rstrip(".") not in self.ignored_project:
                combo_items.append(
                    qtg.Combo_Item(
                        display=item.replace("_", " ").rstrip(self.extn).rstrip("."),
                        data=item,
                        icon=None,
                        user_data=None,
                    )
                )

        project_control_container.add_row(
            qtg.VBoxContainer(text="Select Project", align=qtg.Align.TOPRIGHT).add_row(
                qtg.Label(
                    tag="current_project",
                    label="Current Project",
                    width=40,
                    text=self.current_project,
                    frame=qtg.Widget_Frame(
                        frame_style=qtg.Frame_Style.PANEL,
                        frame=qtg.Frame.SUNKEN,
                        line_width=2,
                    ),
                    translate=False,
                ),
                qtg.ComboBox(
                    tag="existing_projects",
                    width=40,
                    items=combo_items,
                    translate=False,
                    display_na=False,
                    callback=self.event_handler,
                ),
            )
        )

        control_container.add_row(
            project_control_container,
            qtg.HBoxContainer().add_row(
                qtg.Button(
                    icon=file_utils.App_Path("x.svg"),
                    tag="delete_project",
                    callback=self.event_handler,
                    tooltip="Delete Selected Project",
                    width=2,
                ),
                qtg.Button(
                    icon=file_utils.App_Path("file-edit.svg"),
                    tag="new_project",
                    callback=self.event_handler,
                    tooltip="Create A New Project",
                    width=2,
                ),
            ),
            qtg.Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            ),
        )

        return control_container
