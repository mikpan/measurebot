#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Bot to measure and track any use variables.
"""

This Bot uses the Updater class to handle the bot.
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import sys

from telegram import Bot
from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler)

import logging
import argparse
import re


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot States
ADDING_MEASUREMENT, ADDING_MEASUREMENT_TYPE = range(2)

# Static vars
COLUMN_INPUT_PATTERN = re.compile("^[^:]+:.+$")

class MeasureBot(Bot):
    """This object represents a Measure Bot.

    """

    def __init__(self, token):
        super(MeasureBot, self).__init__(token)
        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],

            states={
                ADDING_MEASUREMENT: [RegexHandler('^([^:@]+:[^:@]+|[^@]+@[^@]+)$',
                                                       self.add_measurement,
                                                       pass_user_data=True),
                                          CommandHandler('undo_latest',
                                                         self.undo_latest,
                                                         pass_user_data=True),
                                          CommandHandler('list',
                                                         self.list,
                                                         pass_user_data=True),
                                          RegexHandler('^.*$', self.unrecognised_format),
                                          ],

                ADDING_MEASUREMENT_TYPE: [CommandHandler('cancel', self.start),
                                               MessageHandler(Filters.text,
                                                              self.add_measurement_type,
                                                              pass_user_data=True),
                                               ]
            },

            fallbacks=[RegexHandler('^Check', self.list, pass_user_data=True)]
        )

    def facts_to_str(self, user_data):
        facts = list()

        for key, value in user_data.items():
            facts.append('%s - %s' % (key, value))

        return "\n".join(facts).join(['\n', '\n'])

    def start(self, bot, update):
        message = "Please type a new measurement in a format:\n[measure]: [value]\nFor example,\nMarc weight: 78\nCafe Spending: 4\nRun: 8.5km"
        self.replyToUserUpdate(update, message)

        return ADDING_MEASUREMENT

    def replyToUserUpdate(self, update, message):
        update.message.reply_text(message)

    def add_measurement(self, bot, update, user_data):
        self.lazy_init_user_data(user_data)

        user_text = self.getUserUpdateText(update)
        if COLUMN_INPUT_PATTERN.match(user_text):
            column_index = user_text.index(":")
            measurement = {'type': user_text[:column_index].strip(), 'value': user_text[column_index+1:].strip()}
        else:
            logging.error('Could not recognise user input: %s' % user_text)
            return ADDING_MEASUREMENT
        user_data['current_input'] = measurement

        if measurement['type'] in user_data['known_types']:
            if not user_data['values'][measurement['type']]:
                logging.error('Measurement type "%s" is recorded but no value recorded' % measurement['type'])
                return ADDING_MEASUREMENT
            self.record_measurement(measurement, user_data)
            self.replyToUserUpdate(update,'Measurement added: %s: %s. To undo it use command /undo_latest. To store another one, please type a new measurement in a format [measure]: [value].' % (measurement['type'], measurement['value']))
            return ADDING_MEASUREMENT
        else:
            self.replyToUserUpdate(update,
                                   'Measurement type [%s] for value [%s] is new. To confirm please type it again. To correct it, write the correct value. To cancel, use command /cancel.' %
                                   (measurement['type'], measurement['value']))
            return ADDING_MEASUREMENT_TYPE

    def record_measurement(self, measurement, user_data):
        if measurement['type'] not in user_data['values']: # init with first value
            user_data['values'][measurement['type']] = [measurement['value']]
        else: # append next value
            user_data['values'][measurement['type']].append(measurement['value'])

    def record_measurement_type(self, measurement_type, user_data):
        user_data['known_types'].add(measurement_type)

    def lazy_init_user_data(self, user_data):
        user_data['known_types'] = user_data['known_types'] if 'known_types' in user_data else set()  # lazy-init known_types
        user_data['values'] = user_data['values'] if 'values' in user_data else dict()  # lazy-init values

    def add_measurement_type(self, bot, update, user_data):
        if 'current_input' not in user_data:
            logging.error('Internal state error. No measurement type to record for user: [%s].')
            return ADDING_MEASUREMENT

        user_text = self.getUserUpdateText(update)
        if ':' in self.getUserUpdateText(update):
            self.replyToUserUpdate(update,
                                   'Measurement type value [%s] should not contain separator symbol (:). Measurement type [%s] for value [%s] is new. To confirm please type it again. To correct it, write the correct value. To cancel, use command /cancel.' % (
                                       user_text, user_data['current_input']['type'],
                                       user_data['current_input']['value']))
            return ADDING_MEASUREMENT_TYPE
        elif user_text != user_data['current_input']['type']:
            self.replyToUserUpdate(update,
                                   'Measurement type [%s] for value [%s] is not the same as [%s]. To confirm [%s] please type it again. To correct it, write the correct name. To cancel, use command /cancel.' % (
                                       user_text, user_data['current_input']['type'],
                                       user_data['current_input']['value'], user_text))
            user_data['current_input']['type'] = user_text
            return ADDING_MEASUREMENT_TYPE
        else:
            self.record_measurement_type(user_data['current_input']['type'], user_data)
            self.record_measurement(user_data['current_input'], user_data)
            self.replyToUserUpdate(update,
                                   'Measurement for a new measurement type [%s] with value [%s]. To add more measurements, please type a new measurement in a format [measure]: [value]. To remove the latest use command /undo_latest.' % (
                                       user_data['current_input']['type'], user_data['current_input']['value']))
            return ADDING_MEASUREMENT

    def getUserUpdateText(self, update):
        return update.message.text

    def unrecognised_format(self, bot, update):
        self.replyToUserUpdate(update, '[%s] is in unrecognised format. Please type a new measurement in a format\n[measure]:[value]. For example,\nCafe Spending: 4$\nMarc weight: 78\nRun: 8.5km' % self.getUserUpdateText(update))

        return ADDING_MEASUREMENT

    def list(self, bot, update, user_data):
        self.replyToUserUpdate(update, "Here are the currently recorded measurements: %s\nPlease type a new measurement in a format\n[measure]:[value]. For example,\nCafe Spending: 4$\nMarc weight: 78\nRun: 8.5km" % user_data['values'])

        return ADDING_MEASUREMENT

    def error(self, bot, update, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))

    def undo_latest(self, bot, update, user_data):
        if 'current_input' not in user_data:
            self.replyToUserUpdate(update, 'Nothing is stored as the latest input. To update the dataset please use the web-face or contact the administrator: admin@measurebot.org.')
            return ADDING_MEASUREMENT

        latest_input = user_data['current_input']
        if latest_input['type'] not in user_data['values'] or not user_data['values'][latest_input['type']] or user_data['values'][latest_input['type']][-1] != user_data['current_input']['value']:
            if latest_input['type'] not in user_data['values']:
                message = 'Incorrect state. Current input type [%s] is not among values types: %s' % (latest_input['type'], latest_input['value'].keys())
            elif not user_data['values'][latest_input['type']]:
                message = 'Incorrect state. Current input type [%s] has no recorded values' % (latest_input['type'])
            else:
                message = 'Incorrect state. Current input [%s:%s] is incosistent with the stored value: %s' % (latest_input['type'], latest_input['value'], user_data['values'][latest_input['type']][-1])
            logger.warn(message)
            self.replyToUserUpdate(update, message)
            return ADDING_MEASUREMENT

        user_data['values'][latest_input['type']].pop() # remove latest element
        self.replyToUserUpdate(update, "Latest measurement got removed: [%s]: [%s]. To store correct one, please type a new measurement in a format [measure]: [value]." % (latest_input['type'], latest_input['value']))
        return ADDING_MEASUREMENT


def main(argv):
    # Enable arguments
    parser = argparse.ArgumentParser(description='Measure and track bot service.')
    parser.add_argument("-t", "--token", required=True, type=str, help='Telegram TOKEN')
    args = parser.parse_args()

    # Create the Updater and pass it your bot's token.
    token = args.token
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Create new Measuere Bot instance
    measureBot = MeasureBot(token)

    # Conversation handlers to manage states and transitions between states
    dp.add_handler(measureBot.conv_handler)

    # log all errors
    dp.add_error_handler(measureBot.error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main(sys.argv[1:])
