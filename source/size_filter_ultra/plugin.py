#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic-plugins.plugin.py

    Written by:               AudioscavengeR <dev@derewonko.com>
    Date:                     24 September 2026

    Copyright:
        Copyright (C) 2021 Josh Sunnex

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

import humanfriendly
from unmanic.libs.unplugins.settings import PluginSettings

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.ignore_over_size")


class Settings(PluginSettings):
    settings = {
        "min_file_size": '0',
        "max_file_size": '0',
    }
    form_settings = {
        "min_file_size": {
            "label": "Minimum file size (0 to disable)",
            "description": "Sizes can be written as: 34 MB, 10GB, etc",
        },
        "max_file_size": {
            "label": "Maximum file size (0 to disable)",
            "description": "Sizes can be written as: 34 MB, 10GB, etc",
        },
    }


def check_file_size_over_max_file_size(path, max_file_size):
    """
    Returns True if the file at 'path' is larger than 'max_file_size'.
    A 'max_file_size' of 0 disables this check (always returns False).

    :param path:
    :param max_file_size:
    :return:
    """
    max_bytes = int(humanfriendly.parse_size(max_file_size))
    if max_bytes == 0:
        return False

    file_size = os.stat(path).st_size

    return file_size > max_bytes


def check_file_size_under_min_file_size(path, min_file_size):
    """
    Returns True if the file at 'path' is smaller than 'min_file_size'.
    A 'min_file_size' of 0 disables this check (always returns False).

    :param path:
    :param min_file_size:
    :return:
    """
    min_bytes = int(humanfriendly.parse_size(min_file_size))
    if min_bytes == 0:
        return False

    file_size = os.stat(path).st_size

    return file_size < min_bytes


def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    path = data.get('path')
    max_file_size = settings.get_setting('max_file_size')
    min_file_size = settings.get_setting('min_file_size')

    if check_file_size_over_max_file_size(path, max_file_size):
        # Ignore this file - it's too large
        data['add_file_to_pending_tasks'] = False
        data['issues'].append({
            'id':      'Ignore files by size on disk',
            'message': "File '{}' should be ignored because it is over the configured maximum size '{}'.".format(
                path, max_file_size),
        })

    if check_file_size_under_min_file_size(path, min_file_size):
        # Ignore this file - it's too small
        data['add_file_to_pending_tasks'] = False
        data['issues'].append({
            'id':      'Ignore files by size on disk',
            'message': "File '{}' should be ignored because it is under the configured minimum size '{}'.".format(
                path, min_file_size),
        })

    return data
