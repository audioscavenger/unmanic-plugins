#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Forked from:              Josh.5 <jsunnex@gmail.com>
    Written by:               AudioscavengeR <dev@derewonko.com>
    Date:                     21 September 2026
 
    Copyright:
        Copyright (C) 2021 Josh.5 <jsunnex@gmail.com>
        Copyright (C) 2026 AudioscavengeR <audioscavenger@gmail.com>

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import logging
import os

from unmanic.libs.unplugins.settings import PluginSettings

from codec_type_filter_ultra.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.codec_type_filter_ultra")


class Settings(PluginSettings):
    settings = {
        "keep_video":     True,
        "keep_audio":     True,
        "keep_subtitle":  True,
        "keep_attachment": False,
        "keep_data":      False,
        "keep_unknown":   False,
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)

        self.form_settings = {
            "keep_video":     self.__set_keep_video_form_settings(),
            "keep_audio":     self.__set_keep_audio_form_settings(),
            "keep_subtitle":  self.__set_keep_subtitle_form_settings(),
            "keep_attachment": self.__set_keep_attachment_form_settings(),
            "keep_data":      self.__set_keep_data_form_settings(),
            "keep_unknown":   self.__set_keep_unknown_form_settings(),
        }

    def __set_keep_video_form_settings(self):
        return {
            "label": "Keep video",
            "description": "Keep video streams",
        }

    def __set_keep_audio_form_settings(self):
        return {
            "label": "Keep audio",
            "description": "Keep audio streams",
        }

    def __set_keep_subtitle_form_settings(self):
        return {
            "label": "Keep subtitle",
            "description": "Keep subtitle streams",
        }

    def __set_keep_attachment_form_settings(self):
        return {
            "label": "Keep attachment",
            "description": "Attachment streams are file like movie covers or fonts: 'arial.ttf', and can mess with video transcoding plugins",
        }

    def __set_keep_data_form_settings(self):
        return {
            "label": "Keep data",
            "description": "Data streams can interfere in many transcoding plugins",
        }

    def __set_keep_unknown_form_settings(self):
        return {
            "label": "Keep unknown",
            "description": "God knows what they are. 'unknown' is a catch-all for exotic metadata, that modern video players have no use for",
        }


class PluginStreamMapper(StreamMapper):
    def __init__(self):

        # The 'unknown' additional_stream_specifier is not defined, as seen at https://ffmpeg.org/ffmpeg.html#Stream-specifiers-1
        # There are only 5 stream_type_idents: v,a,s,d and t. not 'u'.
        # Also at https://ffmpeg.org/ffmpeg.html#Automatic-stream-selection it's clear that Data or attachment streams are not automatically selected and can only be included using -map.
        # 'unknown' streams cannot be mapped and ffmpeg simply takes an extra parameter for unknown streams as defined in https://ffmpeg.org/ffmpeg.html#Advanced-options: -ignore_unknown or -copy_unknown
        # Therefore, it's not something StreamMapper should handle since there is no expected transformation mapping at all.
        # Conclusion, plan: we simply add a parameter in the advanced_options.

        #               Unmanic codec_type
        #                       │
        #      ┌────────────────┼─────────────────┐
        #      │                │                 │
        # video/audio/      attachment/data     unknown
        # subtitle              │                 │
        #      │                │                 │
        #   -map 0:v/a/s     -map 0:t/d       -copy_unknown
        #                                         or
        #                                     -ignore_unknown

        super(PluginStreamMapper, self).__init__(logger, ['video', 'audio', 'subtitle', 'attachment', 'data'])
        self.settings = None


    def set_default_values(self, settings, abspath, probe):
        """
        Configure the stream mapper with defaults

        :param settings:
        :param abspath:
        :param probe:
        :return:
        """
        self.abspath = abspath
        # Set the file probe data
        self.set_probe(probe)
        # Set the input file
        self.set_input_file(abspath)
        # Configure settings
        self.settings = settings

        # specific addon for unknown streams, can only be added once and, before the output file parameter
        keep_unknown = '-copy_unknown' if settings.get_setting('unknown') else '-ignore_unknown'

        # If any advanced options are provided, append -ignore_unknown or -copy_unknown
        # Build default options of advanced mode
        if self.settings.get_setting('advanced'):
            # If any advanced options are provided, overwrite them
            advanced_options = settings.get_setting('advanced_options').split()
            if advanced_options:
                # Overwrite all advanced options
                self.advanced_options += [keep_unknown]
        else:
            self.advanced_options = [keep_unknown]


    def test_stream_needs_processing(self, stream_info: dict):
        """Return True when a stream's codec type is not selected to be kept."""
        codec_type = (stream_info.get('codec_type') or '').lower()

        keep_settings = {
            'video': 'keep_video',
            'audio': 'keep_audio',
            'subtitle': 'keep_subtitle',
            'attachment': 'keep_attachment',
            'data': 'keep_data',
            'unknown': 'keep_unknown',
        }

        setting_name = keep_settings.get(codec_type)
        if setting_name is None:
            # Be conservative if ffprobe ever reports a codec_type outside
            # the known set: treat it as unknown.
            setting_name = 'keep_unknown'

        return not self.settings.get_setting(setting_name)


    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        """Do not map streams selected for removal."""
        return {
            'stream_mapping': [],
            'stream_encoding': [],
        }



def on_library_management_file_test(data, task_data_store=None, file_metadata=None):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Get the path to the file
    abspath = data.get('path')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure the mapper with the library's plugin settings.
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    mapper = PluginStreamMapper()
    mapper.set_default_values(settings, abspath, probe)

    if mapper.streams_need_processing():
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams require processing.".format(abspath))

    return data


def on_worker_process(data, task_data_store=None, file_metadata=None):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure the mapper with the library's plugin settings.
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    mapper = PluginStreamMapper()
    mapper.set_default_values(settings, abspath, probe)

    if mapper.streams_need_processing():
        # Set the input file
        mapper.set_input_file(abspath)

        # Set the output file
        # Do not remux the file. Keep the file out in the same container
        mapper.set_output_file(data.get('file_out'))

        # Get generated ffmpeg args
        ffmpeg_args = mapper.get_ffmpeg_args()

        # Apply ffmpeg args to command
        data['exec_command'] = ['ffmpeg']
        data['exec_command'] += ffmpeg_args

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)
        data['command_progress_parser'] = parser.parse_progress

    return data
