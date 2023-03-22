"""
    Implements a basic video cutter

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
import subprocess
from tempfile import NamedTemporaryFile

import PySide6.QtCore as qtC
import PySide6.QtGui as qtG
import PySide6.QtMultimedia as qtM

import dvdarch_utils
import qtgui as qtg
import sqldb
import sys_consts
import utils

# fmt: on


@dataclasses.dataclass
class Video_Handler:
    aspect_ratio: str
    input_file: str
    output_edit_folder: str
    encoding_info: dict
    video_display: qtg.Label
    video_slider: qtg.Slider
    frame_display: qtg.LCD
    display_width: int
    display_height: int
    update_slider: bool = True

    # Private instance variables
    _frame_count: int = 0
    _frame_rate: int = 25  # Default to 25 frames per second
    _frame_num: int = 0
    _frame_width: int = 720
    _frame_height: int = 576
    _media_player: qtM.QMediaPlayer | None = None
    _video_sink: qtM.QVideoSink | None = None

    def __post_init__(self):
        """Sets-up the instance"""
        assert isinstance(self.aspect_ratio, str) and self.aspect_ratio in (
            sys_consts.AR169,
            sys_consts.AR43,
        ), f"{self.aspect_ratio=}. Must be a AR169 | AR43"

        assert (
            isinstance(self.input_file, str) and self.input_file.strip() != ""
        ), f"{self.input_file=}. Must be a non-empty str"

        assert (
            isinstance(self.output_edit_folder, str)
            and self.output_edit_folder.strip() != ""
        ), f"{self.output_edit_folder=}. Must be a non-empty str"

        assert isinstance(
            self.encoding_info, dict
        ), f"{self.encoding_info=}. Must be a dict"

        assert isinstance(
            self.video_display, qtg.Label
        ), f"{self.video_display=}. Must be a qtg.Label"

        assert isinstance(
            self.video_slider, qtg.Slider
        ), f"{self.video_slider=}. Must be a qtg.Slider"

        assert isinstance(
            self.frame_display, qtg.LCD
        ), f"{self.frame_display=}. Must be a qtg.Slider"

        assert isinstance(
            self.display_width, int
        ), f"{self.display_width=}. Must be an int"

        assert isinstance(
            self.display_height, int
        ), f"{self.display_height=}. Must be an int"

        assert isinstance(
            self.update_slider, bool
        ), f"{self.update_slider=}. Must be a bool"

        if "video_width" in self.encoding_info:
            self._frame_width = self.encoding_info["video_width"][1]

        if "video_height" in self.encoding_info:
            self._frame_height = self.encoding_info["video_height"][1]

        if "video_frame_rate" in self.encoding_info:
            self._frame_rate = self.encoding_info["video_frame_rate"][1]

        if "video_frame_count" in self.encoding_info:
            self._frame_count = self.encoding_info["video_frame_count"][1]

        media_format = qtM.QMediaFormat()

        self._media_player = qtM.QMediaPlayer()
        self._video_sink = qtM.QVideoSink()

        # Hook up sink signals
        self._video_sink.videoFrameChanged.connect(self._frame_handler)

        self._media_player.setVideoSink(self._video_sink)
        self._media_player.setSource(qtC.QUrl.fromLocalFile(self.input_file))

        # Hook up media player signals
        self._media_player.mediaStatusChanged.connect(self._media_status_change)
        self._media_player.durationChanged.connect(self._duration_changed)
        self._media_player.seekableChanged.connect(self._seekable_changed)
        self._media_player.positionChanged.connect(self._position_changed)

        # Check if the player can read the media content
        if self._media_player.isAvailable():
            print("The file is supported.")
            print(self._media_player.mediaStatus())
            print(self._media_player.hasAudio())
            print(self._media_player.hasAudio())
            print(self._media_player.isSeekable())
        else:
            print("The file is not supported.")

    def test(self, *args):
        print(f"DBG {args=}")
        print(self._media_player.mediaStatus())
        print(self._media_player.hasAudio())
        print(self._media_player.hasAudio())
        print(self._media_player.isSeekable())

    def _duration_changed(self, duration: int):
        pass

    def _frame_handler(self, frame: qtM.QVideoFrame):
        if frame.isValid():
            image = frame.toImage().scaled(self.display_width, self.display_height)
            pixmap = qtG.QPixmap.fromImage(image)

            self.video_display.guiwidget_get.setPixmap(pixmap)

    def _media_status_change(media_status: qtM.QMediaPlayer.mediaStatus):
        match media_status:
            case qtM.QMediaPlayer.MediaStatus.NoMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.LoadingMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.LoadedMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.StalledMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.BufferingMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.BufferedMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.EndOfMedia:
                pass
            case qtM.QMediaPlayer.MediaStatus.InvalidMedia:
                pass

    def _position_changed(self, position_milliseconds: int) -> None:
        """
        A callback function that is called when the position of the media player changes.
        Converts the current position in milliseconds to the corresponding frame number,
        updates the video slider if necessary, and emits a signal indicating that the position has changed.

        Args:
            position_milliseconds (int): The current position of the media player in milliseconds.
        """
        frame_number = int(position_milliseconds * self._frame_rate // 1000)

        if self.update_slider and self.video_slider is not None:
            self.video_slider.value_set(frame_number)
        self.frame_display.value_set(frame_number)

    def _seekable_changed(self, seekable: bool) -> None:
        """
        A callback function that is called when the seekable status of the media player changes.
        Currently does nothing, but can be used to enable or disable seek controls based on this status.

        Args:
            seekable (bool): True if the media player is seekable, False otherwise.
        """
        # TODO enable/disable seek controls based on this
        pass

    def get_current_frame(self) -> int:
        """
        Returns the current frame number based on the current position of the media player and the frame rate of the video.

        Returns:
            int: The current frame number.
        """
        return int(self._media_player.position() / (1000 / self._frame_rate))

    def play(self) -> None:
        """
        Starts playing the media.
        """
        self._media_player.play()

    def pause(self) -> None:
        """
        Pauses the media.
        """
        self._media_player.pause()

    def seek(self, frame: int) -> None:
        """
        Seeks to the specified frame number.

        Args:
            frame (int): The frame number to seek to.
        """
        if self._media_player.isSeekable():
            time_offset = int((1000 / self._frame_rate) * frame)
            self._media_player.setPosition(time_offset)

    def stop(self) -> None:
        """
        Stops playing the media and resets the player's position to the beginning.
        """
        self._media_player.stop()

    def state(self) -> str:
        """
        Returns the current playback state of the media player.

        Returns:
            str: The current playback state
                - "playing": The media player is currently playing.
                - "paused": The media player is currently paused.
                - "stop": The media player is currently stopped.
        """
        playback_state = self._media_player.playbackState()

        print(f"DBG {playback_state=}")

        if playback_state == qtM.QMediaPlayer.PlaybackState.PlayingState:
            return "playing"
        elif playback_state == qtM.QMediaPlayer.PlaybackState.PausedState:
            return "paused"
        elif playback_state == qtM.QMediaPlayer.PlaybackState.StoppedState:
            return "stop"

    def qt_makeeditable_transcode(self) -> tuple[int, str]:
        """Converts an input video to H.264 at supplied resolution and frame rate.

        Returns:
            tuple[int, str]:
                arg 1: 1 if ok, -1 if error
                arg 2: error message if error else ""
        """
        file_handler = utils.File()

        if not file_handler.path_exists(self.output_edit_folder):
            return -1, f"{self.output_edit_folder} Does not exist"

        if not file_handler.path_writeable(self.output_edit_folder):
            return -1, f"{self.output_edit_folder} Cannot Be Written To"

        if not file_handler.file_exists(self.input_file):
            return -1, f"File Does Not Exist {self.input_file}"

        input_file_name = os.path.splitext(os.path.basename(self.input_file))[0]
        input_file_extn = os.path.splitext(os.path.basename(self.input_file))[1]

        output_file = (
            f"{self.output_edit_folder}{os.sep}{input_file_name}_edit{input_file_extn}"
        )

        # Construct the FFmpeg command
        command = [
            "ffmpeg",
            "-i",
            self.input_file,
            "-vf",
            f"scale={self._frame_width}x{self._frame_height}",
            "-r",
            self._frame_rate,
            "-c:v",
            "libx264",
            output_file,
        ]

        try:
            # Start the process in the background
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Check for errors
            _, stderr = process.communicate()
            if process.returncode != 0:
                print(f"DBG Error occurred during conversion: {stderr.decode()}")
                return -1, f"Error occurred during conversion: {stderr.decode()}"
        except subprocess.SubprocessError as e:
            print(f"DBG Error starting conversion process: {str(e)}")
            return 1, f"Error starting conversion process: {str(e)}"

        return 1, ""


@dataclasses.dataclass
class Video_Cutter_Popup(qtg.PopContainer):
    """This class is a popup that allows the user cut a video"""

    tag = "Video_Cutter_Popup"

    title: str = ""
    aspect_ratio: str = sys_consts.AR43
    width: int = 40
    input_file: str = ""
    output_folder: str = ""
    encoding_info: dict = dataclasses.field(default_factory=dict)

    # Private instance variables
    _frame_rate: int = 25  # Default to 25 frames per second
    _frame_width: int = 720
    _frame_height: int = 576
    _video_display: qtg.Label | None = None
    _video_slider: qtg.Slider | None = None
    _frame_display: qtg.LCD | None = None
    _sliding: bool = False
    _display_height: int = -1
    _display_width: int = -1
    _step_value: int = 1
    _media_source: Video_Handler | None = None
    _edit_folder: str = "edits"
    _transcode_folder: str = "transcodes"
    _edit_files: list[str] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        """Sets-up the form"""

        assert (
            isinstance(self.title, str) and self.title.strip() != ""
        ), f"{self.title=}. Must be a non-empty str"

        assert isinstance(self.aspect_ratio, str) and self.aspect_ratio in (
            sys_consts.AR169,
            sys_consts.AR43,
        ), f"{self.aspect_ratio=}. Must be a AR169 | AR43"

        assert (
            isinstance(self.width, int) and self.width > 10
        ), f"{self.width=}. Must be an int > 10"

        assert (
            isinstance(self.input_file, str) and self.input_file.strip() != ""
        ), f"{self.input_file=}. Must be a non-empty str"

        assert (
            isinstance(self.output_folder, str) and self.output_folder.strip() != ""
        ), f"{self.output_folder=}. Must be a non-empty str"

        assert isinstance(
            self.encoding_info, dict
        ), f"{self.encoding_info=}. Must be a dict"

        if "video_width" in self.encoding_info:
            self._frame_width = self.encoding_info["video_width"][1]

        if "video_height" in self.encoding_info:
            self._frame_height = self.encoding_info["video_height"][1]

        if "video_frame_rate" in self.encoding_info:
            self._frame_rate = self.encoding_info["video_frame_rate"][1]

        if "video_frame_count" in self.encoding_info:
            self._frame_count = self.encoding_info["video_frame_count"][1]

        # Group the video cutter working folders togethr and seperate from the DVD Build
        self.output_folder = f"{self.output_folder}{utils.File().ossep}{sys_consts.PROGRAM_NAME} Video Editor"

        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        super().__post_init__()

    def _video_file_system_maker(self):
        """
        Create the necessary folders for video processing, and checks if the input file exists.

        Raises:
            PopError: if the input file or output folders do not exist, or if the output folder is not writable.

        Side effects:
            Creates folders as necessary for the video processing task.

        """
        file_handler = utils.File()

        if not file_handler.path_exists(self.output_folder):
            file_handler.make_dir(self.output_folder)

        if not file_handler.path_exists(self.output_folder):
            qtg.PopError(
                title="Video Output Folder Does Not Exist",
                message=f"The output folder {sys_consts.SDELIM}'{self.output_folder}'{sys_consts.SDELIM} does not exist. Please create the folder and try again.",
            ).show()
            self.close()

        self._edit_folder = (
            f"{self.output_folder}{file_handler.ossep}{self._edit_folder}"
        )
        self._transcode_folder = (
            f"{self.output_folder}{file_handler.ossep}{self._transcode_folder}"
        )

        if not file_handler.file_exists(self.input_file):
            # This should never happen, unless dev error or mount/drive problems
            qtg.PopError(
                title="Video File Does Not Exist",
                message=f"The input video file {sys_consts.SDELIM}'{self.input_file}'{sys_consts.SDELIM} does not exist. Please ensure the file exists and try again.",
            ).show()
            self.close()

        if not file_handler.path_writeable(self.output_folder):
            qtg.PopError(
                title="Video Output Folder Write Error",
                message=f"The output folder {sys_consts.SDELIM}'{self.output_folder}'{sys_consts.SDELIM} is not writeable. Please ensure you have write permissions for the folder and try again.",
            ).show()
            self.close()

        if not file_handler.path_exists(self._edit_folder):
            if file_handler.make_dir(self._edit_folder) == -1:
                qtg.PopError(
                    title="Video Edit Folder Creation Error",
                    message=f"Failed to create the video edit folder {sys_consts.SDELIM}'{self._edit_folder}'.{sys_consts.SDELIM} Please ensure you have write permissions for the folder and try again.",
                ).show()

        if not file_handler.path_exists(self._transcode_folder):
            if file_handler.make_dir(self._transcode_folder) == -1:
                qtg.PopError(
                    title="Video Transcode Folder Creation Error",
                    message=f"Failed to create the video transcode folder {sys_consts.SDELIM}'{self._transcode_folder}'.{sys_consts.SDELIM} Please ensure you have write permissions for the folder and try again.",
                ).show()

    def event_handler(self, event: qtg.Action):
        """Handles  form events

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"
        # print(
        #   f"DBG EH {event.container_tag=} {event.tag=} {event.action=} {event.event=} {event.value=}"
        # )
        # print(f"DBG VC {event.event=} {event.action=} {event.container_tag=} {event.tag=} {self.container_tag=} {self.tag=}")
        match event.event:
            case qtg.Sys_Events.WINDOWOPEN:
                self.window_open_handler(event)
                self.set_result("")
            case qtg.Sys_Events.WINDOWCLOSED:
                if self._media_source is not None:
                    self._media_source.stop()
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        if self._process_ok(event=event) == 1:
                            super().close()
                    case "backward":
                        self._step_backward()
                    case "bulk_select":
                        edit_list_grid: qtg.Grid = event.widget_get(
                            container_tag="edit_list", tag="edit_list_grid"
                        )

                        edit_list_grid.checkitems_all(
                            checked=event.value, col_tag="mark_in"
                        )
                    case "cancel":
                        if self._process_cancel(event=event) == 1:
                            super().close()
                    case "assemble_segments":
                        self._assemble_segments(event)
                    case "delete_segements":
                        self._delete_segments(event)
                    case "forward":
                        self._step_forward()
                    case "play":
                        self._sliding = True
                        self._media_source.play()
                    case "pause":
                        self._media_source.pause()
                    case "remove_edit_points":
                        self._remove_edit_points(event)
                    case "selection_start":
                        self._selection_start(event)
                    case "selection_end":
                        self._selection_end(event)

            case qtg.Sys_Events.INDEXCHANGED:
                match event.tag:
                    case "step_unit":
                        self._step_unit(event)
            case qtg.Sys_Events.EDITCHANGED:
                match event.tag:
                    case "video_slider":
                        # self._media_source.update_slider = False
                        self._media_source.seek(event.value)
            case qtg.Sys_Events.MOVED:
                match event.tag:
                    case "video_slider":
                        # self._media_source.update_slider = False
                        self._media_source.seek(event.value)
            case qtg.Sys_Events.PRESSED:
                match event.tag:
                    case "video_slider":
                        self._sliding = True
                        self._media_source.update_slider = False

            case qtg.Sys_Events.RELEASED:
                match event.tag:
                    case "video_slider":
                        self._media_source.update_slider = True
                        self._sliding = False

    def window_open_handler(self, event):
        self._video_file_system_maker()  # Might close winw if file system issues

        self._media_source = Video_Handler(
            aspect_ratio=self.aspect_ratio,
            input_file=self.input_file,
            output_edit_folder=self.output_folder,
            encoding_info=self.encoding_info,
            video_display=self._video_display,
            video_slider=self._video_slider,
            frame_display=self._frame_display,
            display_width=self._display_width,
            display_height=self._display_height,
        )

        with qtg.sys_cursor(qtg.Cursor.hourglass):
            self._media_source.play()
            self._media_source.pause()
            self._selection_button_toggle(event=event, init=True)
            self._media_source.update_slider = True

    def _assemble_segments(self, event: qtg.Action):
        """
        Takes the specified segments from the input file and makes new video files from them.

        Note: Pop_Container set_result is called here and not in the _process_ok meothd

        Args:
            event (qtg.Action): The event that triggered this method.

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be type qtg.Action"

        file_handler = utils.File()
        edit_list_grid: qtg.Grid = event.widget_get(
            container_tag="edit_list", tag="edit_list_grid"
        )

        edit_list = [
            (
                edit_list_grid.value_get(row=row_index, col=0),
                edit_list_grid.value_get(row=row_index, col=1) or self._frame_count,
            )
            for row_index in range(edit_list_grid.row_count)
        ]

        if edit_list:
            _, filename, extension = file_handler.split_file_path(self.input_file)

            output_file = (
                f"{self._edit_folder}{file_handler.ossep}{filename}_{extension}"
            )

            video_files = []

            with qtg.sys_cursor(qtg.Cursor.hourglass):
                result, video_files_string = self.cut_video_with_editlist(
                    input_file=self.input_file,
                    output_file=output_file,
                    edit_list=edit_list,
                    cut_out=False,
                )

                if (
                    result == -1
                ):  # video_files_string is the error meesage and not the ',' delimtered file list
                    qtg.PopError(
                        title="Error Cutting File...",
                        message=f"<{video_files_string}>",
                    ).show()
                else:
                    video_files = video_files_string.split(",")

            if video_files:
                result = File_Renamer_Popup(
                    file_list=video_files, container_tag="file_renamer"
                ).show()

                file_str = ""

                if result:
                    for file_detail in result.split("|"):
                        (
                            user_entered_file_name,
                            orig_rename_file_path,
                            user_rename_file_path,
                        ) = file_detail.split(",")

                        if not user_entered_file_name.strip():
                            continue  # Probably an error

                        file_str += f"{self.input_file},{user_entered_file_name},{orig_rename_file_path},{user_rename_file_path},A|"

                    # Strip the trailing "|" delimiter from the file_str
                    file_str = file_str[:-1]

                    self.set_result(file_str)
        else:
            qtg.PopMessage(
                title="No Entries In The Edit List...",
                message="Please Mark Some Edit List Entries With The [ and ] Buttone!",
            ).show()

    def _delete_segments(self, event: qtg.Action):
        """
        Deletes the specified segments from the input file.

        Note: Pop_Container set_result is called here and not in the _process_ok meothd

        Args:
            event (qtg.Action): The event that triggered this method.

        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be type qtg.Action"

        file_handler = utils.File()
        edit_list_grid: qtg.Grid = event.widget_get(
            container_tag="edit_list", tag="edit_list_grid"
        )

        edit_list = [
            (
                edit_list_grid.value_get(row=row_index, col=0),
                edit_list_grid.value_get(row=row_index, col=1) or self._frame_count,
            )
            for row_index in range(edit_list_grid.row_count)
        ]

        if edit_list:
            _, filename, extension = file_handler.split_file_path(self.input_file)

            output_file = (
                f"{self._edit_folder}{file_handler.ossep}{filename}_trimmed{extension}"
            )

            with qtg.sys_cursor(qtg.Cursor.hourglass):
                result, trimmed_file = self.cut_video_with_editlist(
                    input_file=self.input_file,
                    output_file=output_file,
                    edit_list=edit_list,
                )

                if (
                    result == -1
                ):  # trimmed file is the error meesage and not the file name
                    qtg.PopError(
                        title="Error Cutting File...",
                        message=f"<{trimmed_file}>",
                    ).show()
                else:
                    self._edit_files.append(f"{self.input_file},{trimmed_file},T")

                    self.set_result("|".join(self._edit_files))
        else:
            qtg.PopMessage(
                title="No Entries In The Edit List...",
                message="Please Mark Some Edit List Entries With The [ and ] Buttone!",
            ).show()

    def _remove_edit_points(self, event: qtg.Action) -> None:
        """
        Remove checked edit points from a grid widget.

        Args:
            event (qtg.Action): The triggering event

        Raises:
            AssertionError: If the event parameter is not of type qtg.Action


        """

        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)}"

        edit_list_grid: qtg.Grid = event.widget_get(
            container_tag="edit_list", tag="edit_list_grid"
        )

        if (
            edit_list_grid.row_count > 0
            and edit_list_grid.checkitems_get
            and qtg.PopYesNo(
                title="Remove Checked...", message="Remove the Checked Edit Points?"
            ).show()
            == "yes"
        ):
            for item in reversed(edit_list_grid.checkitems_get):
                edit_list_grid.row_delete(item.row_index)

    def _step_unit(self, event: qtg.Action):
        """
        Sets the value of `self._step_value` based on the value of the `event` argument.

        Args:
            event (qtg.Action): The triggering event

        Returns:
            None.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"

        if event.widget_exist(container_tag=event.container_tag, tag=event.tag):
            value: qtg.Combo_Data = event.value_get(
                container_tag=event.container_tag, tag=event.tag
            )

            step_values = {
                "frame": 1,
                "0.5s": self._frame_rate // 2,
                "1s": int(self._frame_rate),
                "15s": int(self._frame_rate * 15),
                "30s": int(self._frame_rate * 30),
                "60s": int(self._frame_rate * 60),
                "300s": int(self._frame_rate * 300),
            }
            self._step_value = step_values[value.data]

    def _step_backward(self):
        """
        Seeks the media source backwards by `_step_value` frames.

        This function first calculates the frame to seek to by subtracting `_step_value` frames from the current frame.
        If the calculated frame is within the bounds of the media source, the media source is paused and seeks to the calculated frame.
        If the calculated frame is less than 0, the media source is seeked to frame 0 instead.

        Args:
            None.

        Returns:
            None.
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            seek_frame = self._media_source.get_current_frame() - self._step_value
            if seek_frame < 0:
                seek_frame = 0

            if 0 <= seek_frame < self._frame_count:
                self._media_source.pause()
                self._media_source.seek(seek_frame)

    def _step_forward(self):
        """
        Seeks the media source forwards by `_step_value` frames.

        This function first calculates the frame to seek to by adding `_step_value` frames to the current frame.
        If the calculated frame is within the bounds of the media source, the media source is paused and seeks to the calculated frame.
        If the calculated frame is greater than or equal to the total number of frames, the media source is seeked to the final frame instead.

        Args:
            None.

        Returns:
            None.
        """
        with qtg.sys_cursor(qtg.Cursor.hourglass):
            seek_frame = self._media_source.get_current_frame() + self._step_value

            if seek_frame >= self._frame_count:
                seek_frame = self._frame_count - 1

            if 0 <= seek_frame < self._frame_count:
                self._media_source.pause()
                self._media_source.seek(seek_frame)

    def _selection_end(self, event: qtg.Action) -> None:
        """Handler function for selecting the end of a media clip.

        Args:
            event (qtg.Action): The triggering event

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"
        assert hasattr(self, "_media_source"), "Media source not set"

        frame = self._media_source.get_current_frame()
        end_time = self.frame_num_to_ffmpeg_time(frame)

        edit_list_grid: qtg.Grid = event.widget_get(
            container_tag="edit_list", tag="edit_list_grid"
        )

        if edit_list_grid.row_count <= 0:
            return None

        current_row = edit_list_grid.row_count - 1

        start_frame = edit_list_grid.value_get(row=current_row, col=0)

        if start_frame >= frame:
            qtg.PopMessage(
                title="Invalid End Select...",
                message="End Frame Must Be Greater Than The Start Frame!",
            ).show()
        else:
            edit_list_grid.value_set(
                row=current_row, col=1, value=frame, user_data=end_time
            )
            self._selection_button_toggle(event=event)

    def _selection_start(self, event: qtg.Action) -> None:
        """Handler function for selecting the start of a media clip.

        Args:
            event (qtg.Action): The triggering event

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"
        assert hasattr(self, "_media_source"), "Media source not set"

        frame = self._media_source.get_current_frame()

        start_time = self.frame_num_to_ffmpeg_time(frame)

        edit_list_grid: qtg.Grid = event.widget_get(
            container_tag="edit_list", tag="edit_list_grid"
        )

        new_row = edit_list_grid.row_count + 1

        edit_list_grid.value_set(row=new_row, col=0, value=frame, user_data=start_time)
        self._selection_button_toggle(event=event)

    def _selection_button_toggle(self, event: qtg.Action, init=False) -> None:
        """Toggles the state of the selection buttons for selecting the start and end of a media clip.

        Args:
            event (qtg.Action): The triggering event
            init (bool): True if initialising the button state fo first use, oherwise false

        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be of type qtg.Action but got {type(event)} instead"

        select_start: qtg.Button = event.widget_get(
            container_tag="video_buttons", tag="selection_start"
        )
        select_end: qtg.Button = event.widget_get(
            container_tag="video_buttons", tag="selection_end"
        )

        if init:  # Initial button state
            select_start.enable_set(True)
            select_end.enable_set(False)
        else:
            if select_start.enable_get:
                select_start.enable_set(False)
                select_end.enable_set(True)
            elif select_end.enable_get:
                select_start.enable_set(True)
                select_end.enable_set(False)
            else:
                select_start.enable_set(True)
                select_end.enable_set(False)

    def frame_num_to_ffmpeg_time(self, frame_num: int) -> str:
        """
        Converts a frame number to an FFmpeg offset time string in the format "hh:mm:ss.mmm".

        Args:
            frame_num: An integer representing the frame number to convert.

        Returns:
            A string representing the FFmpeg offset time in the format "hh:mm:ss.mmm".

        """
        offset_time = frame_num / self._frame_rate
        hours = int(offset_time / 3600)
        minutes = int((offset_time % 3600) / 60)
        seconds = int(offset_time % 60)
        milliseconds = int((offset_time % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    from typing import List

    def create_ffmpeg_editlist(
        self, input_file: str, frames: List[tuple], fps: float, output_file: str
    ) -> tuple[int, str]:
        """
        Creates an edit list string in ffmpeg's format based on a list of frame ranges.

        Args:
            frames (List[tuple]): A list of (start_frame, end_frame) tuples representing
                the frame ranges to include in the edit list.
            fps (float): The frame rate of the input video file, in frames per second.
            output_file (str): The name of the output file to write the edit list to.

        Returns:
            tuple[int, str]:
                arg 1: 1 if ok, -1 if error
                arg 2: error message if error else ""
        """
        assert isinstance(frames, list), "frames must be a list"
        assert all(
            isinstance(frame, tuple) and len(frame) == 2 for frame in frames
        ), "frames must be a list of (start_frame, end_frame) tuples"
        assert all(
            isinstance(frame[0], int) and isinstance(frame[1], int) for frame in frames
        ), "start_frame and end_frame must be integers"
        assert (
            isinstance(fps, (int, float)) and fps > 0
        ), "fps must be a positive number"
        assert isinstance(output_file, str) and output_file.endswith(
            ".txt"
        ), "output_file must be a string ending in '.txt'"

        editlist = "ffconcat version 1.0\n"
        for i, (start_frame, end_frame) in enumerate(frames):
            start_time = start_frame / fps
            end_time = end_frame / fps
            editlist += f"file '{input_file}'\n"
            editlist += f"inpoint {start_time:.3f}\n"
            editlist += f"outpoint {end_time:.3f}\n"

        try:
            with open(output_file, "w") as f:
                f.write(editlist)
        except IOError:
            print(f"Error: Could not open file '{output_file}' for writing.")

            return -1, f"Error: Could not open file '{output_file}' for writing."

        return 1, ""

    def cut_video_with_editlist(
        self,
        input_file: str,
        output_file: str,
        edit_list: list[tuple[int, int]],
        cut_out: bool = True,
    ) -> tuple[int, str]:
        """
        Cuts a video file based on a given edit list of start and end frames.

        Args:
            input_file (str): Path of the input video file.
            output_file (str): Path of the output video file.
            edit_list (List[Tuple[int, int]]): List of tuples containing start and end frames of each segment to cut.
            cut_out (bool, optional): Whether to cut out the edit points of the video. Defaults to True.

        Returns:
            tuple[int, str]: A tuple containing the following elements:
            - If the operation was successful:
                - arg 1 (int): 1
                - arg 2 (str): If cut_out is True, the path of the output video file;
                if cut_out is False, a ',' delimited string of output file paths.
            - If the operation failed:
                - arg 1 (int): -1
                - arg 2 (str): An error message.
        """

        # ===== Helper
        def transform_cut_in_to_cut_out(
            edit_list: list[tuple[int, int]], frame_count: int
        ) -> list[tuple[int, int]]:
            """
            Transforms a list of cut in points to cut out points.

            Args:
                edit_list (List[Tuple[int, int]]): A list of tuples representing the cut in and cut out points of a video.
                frame_count (int): The total number of frames in the video.

            Returns:
            - edit_list_2 (List[Tuple[int, int]]): A new list of tuples representing the cut out points of the video.

            Raises:
            - TypeError: If edit_list is not a list or frame_count is not an integer.
            - ValueError: If edit_list is empty or any tuple in edit_list has start frame greater than end frame.

            """
            if not isinstance(edit_list, list):
                raise TypeError("edit_list should be a list of tuples")
            if not all(isinstance(x, tuple) and len(x) == 2 for x in edit_list):
                raise TypeError("edit_list should contain tuples of size 2")
            if not isinstance(frame_count, int):
                raise TypeError("frame_count should be an integer")
            if not edit_list:
                raise ValueError("edit_list should not be empty")
            if any(start_frame >= end_frame for start_frame, end_frame in edit_list):
                raise ValueError(
                    "start_frame should be less than end_frame in every tuple of edit_list"
                )

            prev_start = 0
            cut_out_list = []

            for cut_index, (start_frame, end_frame) in enumerate(edit_list):
                if start_frame != end_frame:
                    new_tuple = (prev_start, start_frame)
                    cut_out_list.append(new_tuple)
                prev_start = end_frame

                # check for overlapping frames between consecutive tuples
                # Note: We consider it an overlap if tuple overlap within 0.5 seconds!
                if cut_index < len(edit_list) - 1:
                    _, next_start_frame = edit_list[cut_index + 1]
                    if (
                        end_frame >= next_start_frame
                        and end_frame <= next_start_frame + (self._frame_rate // 2)
                    ):
                        # merge the two tuples into a single tuple
                        cut_out_list[-1] = (cut_out_list[-1][0], next_start_frame)

            # add the last tuple
            if prev_start != frame_count:
                cut_out_list.append((prev_start, frame_count))

            return cut_out_list

        # ===== Main
        assert isinstance(input_file, str), f"{input_file=}. Must be str"
        assert isinstance(output_file, str), f"{output_file=} must be str"
        assert isinstance(edit_list, list), f"{edit_list=}. Must be a list"
        assert all(
            isinstance(edit, tuple) for edit in edit_list
        ), "Each edit in edit_list must be a tuple"
        assert all(
            len(edit) == 2 for edit in edit_list
        ), "Each edit tuple in edit_list must have exactly two elements"
        assert all(
            isinstance(edit[0], int) for edit in edit_list
        ), "The start frame in each edit tuple must be an integer"
        assert all(
            isinstance(edit[1], int) for edit in edit_list
        ), "The end frame in each edit tuple must be an integer"
        assert isinstance(cut_out, bool), f"{cut_out=}. Must be a bool"

        file_handler = utils.File()

        out_path, out_file, out_extn = file_handler.split_file_path(output_file)

        result, message = dvdarch_utils.get_codec(input_file)

        if result == -1:
            return -1, message
        codec = message

        temp_files = []

        if cut_out:
            edit_list = transform_cut_in_to_cut_out(
                edit_list=edit_list, frame_count=self._frame_count
            )

        for cut_index, (start_frame, end_frame) in enumerate(edit_list):
            if end_frame - start_frame <= 0:  # Probably should not happen
                continue

            if cut_out:
                temp_file = f"{out_path}{file_handler.ossep}{file_handler.extract_title(out_file)}({cut_index}){out_extn}"
            else:
                temp_file = f"{out_path}{file_handler.ossep}{file_handler.extract_title(out_file)}_{cut_index:03d}{out_extn}"

            temp_files.append(temp_file)

            # Calculate the start and end times of the segment based on the frame numbers
            start_time = start_frame / self._frame_rate
            end_time = end_frame / self._frame_rate

            # Calculate the nearest key frames before and after the cut
            result, before_key_frame = dvdarch_utils.get_nearest_key_frame(
                input_file, start_time, "prev"
            )

            if result == -1:
                return -1, "Failed To Get Before Key Frame"

            result, after_key_frame = dvdarch_utils.get_nearest_key_frame(
                input_file, end_time, "next"
            )

            if result == -1:
                return -1, "Failed To Get After Key Frame"

            # Set the start time and duration of the segment to re-encode
            segment_start = (
                before_key_frame if before_key_frame is not None else start_time
            )

            segment_duration = (
                after_key_frame - segment_start
                if after_key_frame is not None
                else end_time - segment_start
            )

            command = [sys_consts.FFMPG, "-i", input_file]

            # Check if re-encoding is necessary
            if before_key_frame is None or after_key_frame is None:
                # Re-encode the segment
                command += ["-ss", str(segment_start)]
                command += ["-t", str(segment_duration)]
                command += ["-avoid_negative_ts", "make_zero"]
                command += ["-map", "0:v", "-map", "0:a"]
                command += ["-c:v", codec]
                command += ["-c:a", "copy"]
                if before_key_frame is not None:
                    command += ["-force_key_frames", f"{before_key_frame}+1"]
                if after_key_frame is not None:
                    command += ["-tune", "fastdecode"]
                command += [temp_file, "-y"]
            else:
                # Copy the segment
                if before_key_frame is not None:
                    command += ["-ss", str(segment_start)]
                command += [
                    "-t",
                    str(segment_duration),
                    "-avoid_negative_ts",
                    "make_zero",
                ]
                command += ["-map", "0:v", "-map", "0:a", "-c", "copy"]
                if before_key_frame is not None:
                    command += ["-force_key_frames", f"{before_key_frame}+1"]
                if after_key_frame is not None:
                    command += ["-force_key_frames", f"{after_key_frame}"]
                command += [temp_file, "-y"]

            result, message = dvdarch_utils.execute_check_output(command, debug=False)

            if result == -1:
                return -1, message

        if cut_out:  # Concat temp file for final file and remove the temp files
            result, message = dvdarch_utils.concatenate_videos(
                temp_files=temp_files, output_file=output_file, delete_temp_files=False
            )

            if result == -1:
                return -1, message

            for temp_file in temp_files:
                if file_handler.remove_file(temp_file) == -1:
                    return -1, f"Faied To Remove File <{temp_file}>"
        else:
            # We keep the temp files, as they are the new videos, and build an output file str where each video is
            # delimitered by a ','
            output_file = ",".join(temp_files)

        return 1, output_file

    def _process_cancel(self, event: qtg.Action) -> int:
        """Processes the cancel selection

        Args:
            event (qtg.Action): The triggering event

        Returns:
            int: 1 all good, close the window. -1 keep window open
        """
        if self.get_result:
            if (
                qtg.PopYesNo(
                    title="Files Edited...",
                    message="Video Edits Have Been Made, Discard Changes and Delete The Edited Files?",
                ).show()
                == "yes"
            ):
                return 1
            else:
                return -1

        return 1

    def _process_ok(self, event: qtg.Action) -> int:
        """Processes the ok selection

        Args:
            event (qtg.Action): The event that triggered the function.

        Returns:
            int: 1 all good, close the window. -1 keep window open
        """

        return 1

    def layout(self) -> qtg.VBoxContainer:
        # ===== Helper
        def assemble_video_cutter_container() -> qtg.HBoxContainer:
            """
            Creates a  horizontal box container housing the video cutter.

            Returns:
                qtg.HBoxContainer: A horizontal box container for the video cutter.
            """

            step_unit_list = [
                qtg.Combo_Item(
                    display="Frame", data="frame", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="0.5 Sec", data="0.5s", icon=None, user_data=None
                ),
                qtg.Combo_Item(display="1   Sec", data="1s", icon=None, user_data=None),
                qtg.Combo_Item(
                    display="15  Sec", data="15s", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="30  Sec", data="30s", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="1   Min", data="60s", icon=None, user_data=None
                ),
                qtg.Combo_Item(
                    display="5   Min", data="300s", icon=None, user_data=None
                ),
            ]

            # self._video_display = qtg.Label(width=edit_width -6, height=edit_height)
            self._video_display = qtg.Label(
                width=self._display_width, height=self._display_height, pixel_unit=True
            )
            self._video_slider = qtg.Slider(
                tag="video_slider",
                width=self._display_width,
                height=20,
                callback=self.event_handler,
                range_max=self._frame_count,
                pixel_unit=True,
            )

            self._frame_display = qtg.LCD(
                tag="frame_display",
                label="Frame",
                width=6,
                height=1,
                txt_fontsize=14,
            )

            video_button_container = qtg.HBoxContainer(
                tag="video_buttons", align=qtg.Align.CENTER
            ).add_row(
                qtg.HBoxContainer().add_row(
                    qtg.Button(
                        tag="selection_start",
                        icon=utils.App_Path("bracket-left.svg"),
                        callback=self.event_handler,
                        tooltip="Mark In Edit Point",
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="selection_end",
                        icon=utils.App_Path("bracket-right.svg"),
                        callback=self.event_handler,
                        tooltip="Mark Out Edit Point",
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="backward",
                        tooltip="Step Back",
                        icon=qtg.Sys_Icon.mediabackward.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="play",
                        tooltip="Play",
                        icon=qtg.Sys_Icon.mediaplay.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                    ),
                    qtg.Button(
                        tag="forward",
                        tooltip="Step Forward",
                        icon=qtg.Sys_Icon.mediaforward.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                    ),
                    # qtg.Spacer(width=1),
                    qtg.Button(
                        tag="pause",
                        tooltip="Pause Play",
                        icon=qtg.Sys_Icon.mediapause.get(),
                        callback=self.event_handler,
                        width=2,
                        height=1,
                    ),
                    # qtg.Spacer(width=1),
                    qtg.ComboBox(
                        tag="step_unit",
                        tooltip="Choose The Step Unit",
                        label="Step",
                        width=10,
                        callback=self.event_handler,
                        items=step_unit_list,
                        display_na=False,
                        translate=False,
                    ),
                    # qtg.Spacer(width=1),
                    # qtg.Button(tag="stop",icon=qtg.SYSICON.mediastop.get(), callback=self.event_handler, width=2, height=1),
                )
            )

            video_cutter_container = qtg.VBoxContainer(
                tag="video_cutter",
                text="Video Cutter",
                align=qtg.Align.CENTER,
            ).add_row(
                self._video_display,
                self._video_slider,
                video_button_container,
                # qtg.Spacer(),
                qtg.HBoxContainer().add_row(self._frame_display),
            )

            return video_cutter_container

        def assemble_edit_list_container() -> qtg.FormContainer:
            """
            Create a FormContainer containg the editing list.

            Returns:
                qtg.FormContainer: A form container that houses the edit list.
            """
            edit_list_cols = [
                qtg.Col_Def(
                    tag="mark_in",
                    label="Frame In",
                    width=10,
                    editable=False,
                    checkable=True,
                ),
                qtg.Col_Def(
                    tag="mark_out",
                    label="Frame Out",
                    width=10,
                    editable=False,
                    checkable=False,
                ),
                # qtg.COL_DEF(
                #     tag="controls",
                #     label="",
                #     width=2,
                #     editable=False,
                #     checkable=False,
                # ),
            ]

            edit_list_buttons = qtg.HBoxContainer(align=qtg.Align.BOTTOMCENTER).add_row(
                qtg.Button(
                    icon=utils.App_Path("film.svg"),
                    tag="assemble_segments",
                    callback=self.event_handler,
                    tooltip="Assemble Edit Points Into New Videos",
                    width=3,
                ),
                qtg.Button(
                    icon=utils.App_Path("scissors.svg"),
                    tag="delete_segements",
                    callback=self.event_handler,
                    tooltip="Delete Edit Points From Video",
                    width=3,
                ),
                qtg.Spacer(width=1),
                qtg.Button(
                    icon=utils.App_Path("x.svg"),
                    tag="remove_edit_points",
                    callback=self.event_handler,
                    tooltip="Delete Edit Points From Edit List",
                    width=3,
                ),
            )

            edit_file_list = qtg.VBoxContainer(align=qtg.Align.TOPLEFT).add_row(
                qtg.Checkbox(
                    text="Select All",
                    tag="bulk_select",
                    callback=self.event_handler,
                    tooltip="Select All Edit Points",
                    width=11,
                ),
                qtg.Grid(
                    tag="edit_list_grid",
                    height=self._display_height,
                    col_def=edit_list_cols,
                    pixel_unit=True,
                ),
                edit_list_buttons,
            )

            edit_list_container = qtg.VBoxContainer(
                tag="edit_list",
                text="Edit List",
                align=qtg.Align.LEFT,
            ).add_row(edit_file_list)

            return edit_list_container

        # ===== Main
        """Generate the form UI layout"""
        self._display_height = (
            self._frame_height
        )  # // 2 # Black Choice, TODO Make settable
        self._display_width = self._frame_width  # // 2

        video__cutter_container = assemble_video_cutter_container()
        edit_list_continer = assemble_edit_list_container()

        video_controls_container = qtg.HBoxContainer().add_row(
            video__cutter_container,
            edit_list_continer,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )

        control_container.add_row(
            video_controls_container,
            qtg.Spacer(),
            qtg.Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            ),
        )

        return control_container


@dataclasses.dataclass
class File_Renamer_Popup(qtg.PopContainer):
    "Renames video files sourced from the video cutter"
    file_list: list[str] | tuple[str] = dataclasses.field(default_factory=list)
    tag = "File_Renamer_Popup"
    file_validated: bool = True

    # Private instance variable
    _db_settings: sqldb.App_Settings | None = None

    def __post_init__(self):
        """Sets-up the form"""
        assert (
            isinstance(self.file_list, (list, tuple)) and len(self.file_list) > 0
        ), f"{self.file_list=}. Must be a non-empty list or tuple of str"
        assert all(
            isinstance(file, str) and file.strip() != "" for file in self.file_list
        ), f"All elements must be str"

        self.container = self.layout()
        self._db_settings = sqldb.App_Settings(sys_consts.PROGRAM_NAME)

        super().__post_init__()  # This statement must be last

    def event_handler(self, event: qtg.Action):
        """Handles  form events

        Args:
            event (qtg.Action): The triggering event
        """
        assert isinstance(event, qtg.Action), f"{event=}. Must be an Action instance"

        match event.event:
            case qtg.Sys_Events.WINDOWOPEN:
                self._load_files(event)
            case qtg.Sys_Events.CLICKED:
                match event.tag:
                    case "ok":
                        if self._process_ok(event) == 1:
                            super().close()
                    case "cancel":
                        if self._process_cancel(event) == 1:
                            super().close()
            case qtg.Sys_Events.CLEAR_TYPING_BUFFER:
                if isinstance(event.value, qtg.Grid_Col_Value):
                    grid_col_value: qtg.Grid_Col_Value = event.value

                    user_file_name = grid_col_value.value
                    row = grid_col_value.row
                    col = grid_col_value.col
                    user_data = grid_col_value.user_data

                    file_grid: qtg.Grid = event.widget_get(
                        container_tag="file_controls",
                        tag="video_input_files",
                    )

                    file_grid.value_set(
                        value=user_file_name, row=row, col=col, user_data=user_data
                    )

    def _is_changed(self, event: qtg.Action) -> bool:
        """
        Check if any file names in the video_input_files Grid have been changed.

        Args:
            event (qtg.Action): The event that triggered this method.

        Returns:
            bool: True if any file names have been changed, False otherwise.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=}. Must be an instance of qtg.Action"

        file_handler = utils.File()

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls", tag="video_input_files"
        )

        col_index = file_grid.colindex_get("new_file_name")

        for row_index in range(0, file_grid.row_count):
            file_name = file_grid.value_get(row_index, col_index)
            old_file: str = file_grid.userdata_get(row_index, col_index)
            _, old_file_name, _ = file_handler.split_file_path(old_file)

            if file_name is not None and file_name.strip() != old_file_name.strip():
                return True

        return False

    def _load_files(self, event: qtg.Action) -> int:
        """
        Load the list of video input files into the GUI file controls grid.

        Args:
            event (qtg.Action): The event that triggered the method.

        Returns:
            int: The number of files loaded.

        """
        assert isinstance(event, qtg.Action), "event must be an instance qtg.Action"

        file_handler = utils.File()

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls",
            tag="video_input_files",
        )

        col_index = file_grid.colindex_get("new_file_name")

        for row_index, file_path in enumerate(self.file_list):
            _, file_name, _ = file_handler.split_file_path(file_path)

            file_grid.value_set(
                value=file_name,
                row=row_index,
                col=col_index,
                user_data=(file_path),
            )

        return row_index

    def _package_files(self, event: qtg.Action) -> str:
        """
        Package the video input files into a string format and sets the result.

        Args:
            event (qtg.Action): The event that triggered this method.

        Returns:
            str: A string representation of the video input files, with each file's original name and new name
            separated by a comma, and each file separated by a vertical bar.
        """
        assert isinstance(
            event, qtg.Action
        ), f"{event=} must be an instance of qtg.Action"

        file_handler = utils.File()

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls", tag="video_input_files"
        )

        col_index = file_grid.colindex_get("new_file_name")

        file_str = ""
        for row_index in range(file_grid.row_count):
            user_entered_file_name = file_grid.value_get(row_index, col_index)
            orig_rename_file_path: str = file_grid.userdata_get(row_index, col_index)

            renamed_path, _, extension = file_handler.split_file_path(
                orig_rename_file_path
            )

            user_rename_file_path = (
                f"{renamed_path}{file_handler.ossep}{user_entered_file_name}{extension}"
            )

            file_str += f"{user_entered_file_name},{orig_rename_file_path},{user_rename_file_path}|"

        # Strip the trailing "|" delimiter from the file_str
        file_str = file_str[:-1]

        self.set_result(file_str)

        return file_str

    def _process_cancel(self, event: qtg.Action) -> int:
        """
        Handles processing the cancel button.

        Args:
            event (qtg.Action): The triggering event.

        Returns:
            int: Returns 1 if cancel process is ok, -1 otherwise.
        """
        self.set_result("")

        if self._is_changed(event):
            if (
                qtg.PopYesNo(
                    title="Files Renamed...",
                    message="Discard Renamed Files And Close Window?",
                ).show()
                == "yes"
            ):
                return 1
            else:
                result = self._rename_files(event)

                if result == 1:
                    qtg.PopMessage(
                        title="Rename Files...", message="Files Renamed Successfully"
                    ).show()
                    self._package_files(event)

                return result
        else:
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

        if self._is_changed(event):
            if (
                qtg.PopYesNo(title="Rename Files...", message="Rename Files?").show()
                == "yes"
            ):
                result = self._rename_files(event)

                if result == 1:
                    qtg.PopMessage(
                        title="Rename Files...", message="Files Renamed Successfully"
                    ).show()
                    self._package_files(event)

                return result

        return 1

    def _rename_files(self, event: qtg.Action) -> int:
        """
        Handles renaing of video file if needed.

        Args:
            event (qtg.Action): The triggering event.

        Returns:
            int: Returns 1 if all file names are valid and files are, if needed, renamed successfully, -1 otherwise.

        """
        assert isinstance(event, qtg.Action), "event must be an instance qtg.Action"

        file_handler = utils.File()

        file_grid: qtg.Grid = event.widget_get(
            container_tag="file_controls",
            tag="video_input_files",
        )

        col_index = file_grid.colindex_get("new_file_name")

        for row_index in range(0, file_grid.row_count):
            file_name = file_grid.value_get(row_index, col_index)
            old_file: str = file_grid.userdata_get(row_index, col_index)

            if file_name is None:  # Probably an error occurred
                continue

            if file_name.strip() != "" and not file_handler.filename_validate(
                file_name
            ):
                error_msg = f"{sys_consts.SDELIM}{file_name!r}{sys_consts.SDELIM} is not a valid file name! Please reenter."
                qtg.PopError(title="Invalid File Name...", message=error_msg).show()
                file_grid.row_scroll_to(row_index, col_index)
                return -1

            old_file_path, old_file_name, extension = file_handler.split_file_path(
                old_file
            )
            new_file_path = f"{old_file_path}{file_handler.ossep}{file_name}{extension}"

            if file_name.strip() != old_file_name.strip():
                if file_handler.rename_file(old_file, new_file_path) == -1:
                    error_msg = f"Failed to rename file {sys_consts.SDELIM}{old_file_path!r}{sys_consts.SDELIM} to {sys_consts.SDELIM}{new_file_path!r}{sys_consts.SDELIM}"

                    qtg.PopError(
                        title="Failed To Rename File...", message=error_msg
                    ).show()

                    file_grid.row_scroll_to(row_index, col_index)
                    return -1
        return 1

    def layout(self) -> qtg.VBoxContainer:
        """Generate the form UI layout"""
        file_control_container = qtg.VBoxContainer(
            tag="file_controls", align=qtg.Align.TOPLEFT
        )

        file_col_def = (
            qtg.Col_Def(
                label="New File Name",
                tag="new_file_name",
                width=80,
                editable=True,
                checkable=False,
            ),
        )

        video_input_files = qtg.Grid(
            tag="video_input_files",
            noselection=True,
            height=15,
            col_def=file_col_def,
            callback=self.event_handler,
        )

        file_control_container.add_row(
            video_input_files,
        )

        control_container = qtg.VBoxContainer(
            tag="form_controls", align=qtg.Align.TOPRIGHT
        )

        control_container.add_row(
            file_control_container,
            qtg.Command_Button_Container(
                ok_callback=self.event_handler, cancel_callback=self.event_handler
            ),
        )

        return control_container
