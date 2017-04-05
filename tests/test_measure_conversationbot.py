#!/usr/bin/env python
# encoding: utf-8
#
# A library that provides a Python interface to the Telegram Bot API
# Copyright (C) 2015-2016
# Misha Panshenskov  <devs@measurebot.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].
"""This module contains an object that represents Tests for Telegram Bot"""

from datetime import datetime
import sys
import unittest
from mock import MagicMock

from flaky import flaky

from telegram import Message
from telegram import Update
from telegram.measurebot.measure_conversationbot import MeasureBot, ADDING_MEASUREMENT_TYPE, ADDING_MEASUREMENT

sys.path.append('.')

import telegram
from telegram.error import BadRequest
from tests.base import BaseTest, timeout


class MeasurementBotTest(BaseTest, unittest.TestCase):
    """This object represents Tests for Telegram Bot."""

    def setUp(self):
        self.result_id = 'result id'
        self.from_user = telegram.User(1, 'First name', None, 'Last name', 'username')
        self.measureBot = MeasureBot("301568247:BBF1GUx2f5Hq7h3drBupUZV-RLzP806jsKo") # NON-EXISTING TOKEN

        self.measureBot.getUserUpdateText = MagicMock(name='getUserUpdateText')
        self.measureBot.replyToUserUpdate = MagicMock(name='replyToUserUpdate')
        self.measureBot.replyToUserUpdate.return_value = None

    def test_add_measurement(self):
        self.validate_add_measurement_for_io("Number of Rooms:8", 'Number of Rooms', '8')
        self.validate_add_measurement_for_io("Number of Rooms :8", 'Number of Rooms', '8')
        self.validate_add_measurement_for_io("Number of Rooms : 8", 'Number of Rooms', '8')
        self.validate_add_measurement_for_io(" Number of Rooms : 8 ", 'Number of Rooms', '8')
        self.validate_add_measurement_for_io("Local Time : 8:23", 'Local Time', '8:23')
        self.validate_add_measurement_for_io("Local Time : 8:23:00", 'Local Time', '8:23:00')

    def validate_add_measurement_for_io(self, user_input, expected_measure_type, expected_measure_value):
        # Given
        user_data = dict()
        self.measureBot.getUserUpdateText.return_value = user_input
        # When
        new_state = self.measureBot.add_measurement(self._bot, None, user_data)
        # Then
        self.assertEqual(new_state, ADDING_MEASUREMENT_TYPE)
        self.assertTrue('current_input' in user_data, "Current input is empty")
        self.assertDictEqual(user_data['current_input'], {'type': expected_measure_type, 'value': expected_measure_value})

    def test_add_measurement_type(self):
        # Given
        current_input = {'type': 'Number of Rooms', 'value': '8'}
        user_data = {'current_input': current_input}
        self.measureBot.lazy_init_user_data(user_data)
        self.measureBot.getUserUpdateText.return_value = current_input['type']
        # When
        new_state = self.measureBot.add_measurement_type(self._bot, None, user_data)
        # Then
        self.assertEqual(new_state, ADDING_MEASUREMENT)
        self.assertTrue('current_input' in user_data, "Current input is empty")

    def test_remove_latest_command(self):
        # Given
        current_input = {'type': 'Number of Rooms', 'value': '8'}
        user_data = {'current_input': current_input, 'values': {'Number of Rooms': ['8']}}
        self.measureBot.lazy_init_user_data(user_data)
        self.measureBot.getUserUpdateText.return_value = current_input['type']
        # When
        new_state = self.measureBot.undo_latest(self._bot, None, user_data)
        # Then
        self.assertEqual(new_state, ADDING_MEASUREMENT)

    def test_start_command(self):
        # Given
        # When
        new_state = self.measureBot.start(self._bot, None)
        # Then
        self.assertEqual(new_state, ADDING_MEASUREMENT)

    def test_list_command(self):
        # Given
        user_data = {'values': {'Number of Rooms': ['8']}}
        # When
        new_state = self.measureBot.list(self._bot, None, user_data=user_data)
        # Then
        self.assertEqual(new_state, ADDING_MEASUREMENT)


if __name__ == '__main__':
    unittest.main()
