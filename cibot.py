#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
import logging

from data import Session, create_db, User

def handle_start(bot, update):
    with SessionGen(True) as session:
        user = update.message.user
        db_user = session.query(User).filter(User.tid == user.id).first()
        if db_user is None:
            db_user = User()
            db_user.tid = user.id
            db_user.first_name = user.first_name
            db_user.last_name = user.last_name
            db_user.username = user.username
            session.add(db_user)
        bot.send_message(chat_id=update.message.chat_id, text="Hello {} {}!".format(db_user.first_name, db_user.last_name))

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
