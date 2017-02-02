#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
import logging

from data import SessionGen, create_db, User, Phase, Statement

def handle_start(bot, update):
    with SessionGen(True) as session:
        db_user = User.get_from_telegram_user(session, update.message.from_user)
        phase = Phase.get_current(session)
        bot.send_message(chat_id=update.message.chat_id, text="Hello {}!".format(db_user.get_pretty_name()))
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
