#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
import logging

from data import SessionGen, create_db, User, Phase, Statement

def handle_start(bot, update):
    with SessionGen(True) as session:
        db_user = User.get_from_telegram_user(session, update.message.from_user)
        bot.send_message(chat_id=update.message.chat_id, text="Hello {}!".format(db_user.get_pretty_name()))
        circle = db_user.circle
        if circle is None:
            bot.send_message(chat_id=update.message.chat_id, text="You do not have a circle yet!")
        else:
            phase = circle.get_current_phase()
            bot.send_message(chat_id=update.message.chat_id, text="Your circle is {}".format(circle.name))
            bot.send_message(chat_id=update.message.chat_id, text="Now is {}".format(phase.get_pretty_name()))

def main():
    create_db()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    token = open('telegram_token').read().strip()
    updater = Updater(token=token)

    start_handler = CommandHandler('start', handle_start)
    updater.dispatcher.add_handler(start_handler)

    # Start main cycle
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
