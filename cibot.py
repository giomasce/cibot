#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging

from data import SessionGen, create_db, User, Phase, Statement, Circle, Moment

def get_user(session, update):
    user = User.get_from_telegram_user(session, update.message.from_user)
    if not user.enabled:
        return None
    return user

def get_user_and_statement(session, update, for_update=False):
    user = get_user(session, update)
    if user is None:
        return None, None
    statement = user.get_current_statement(for_update=for_update)
    return user, statement

def handle_start(bot, update):
    with SessionGen(True) as session:
        db_user = get_user(session, update)
        if db_user is None:
            return

        bot.send_message(chat_id=update.message.chat_id, text="Hello {}!".format(db_user.get_pretty_name()))
        circle = db_user.circle
        if circle is None:
            bot.send_message(chat_id=update.message.chat_id, text="You do not have a circle yet!")
        else:
            phase = circle.get_current_phase()
            bot.send_message(chat_id=update.message.chat_id, text="Your circle is {}".format(circle.name))
            bot.send_message(chat_id=update.message.chat_id, text="Now is {}".format(phase.get_pretty_name()))

        custom_keyboard = [['/present', '/absent'],
                           ['/status']]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard)
        bot.sendMessage(chat_id=update.message.chat_id, reply_markup=reply_markup)

def handle_join(bot, update, args):
    with SessionGen(True) as session:
        user = get_user(session, update)
        if user is None:
            return

        if len(args) != 1:
            bot.send_message(chat_id=update.message.chat_id, text="You have to specify a circle")
            return
        circle_name = args[0]

        circle = session.query(Circle).filter(Circle.name == circle_name).first()
        if circle is None:
            bot.send_message(chat_id=update.message.chat_id, text="Circle {} does not exist!".format(circle_name))
            return
        user.circle = circle
        bot.send_message(chat_id=update.message.chat_id, text="You just joined circle {}".format(circle.name))

def handle_leave(bot, update):
    with SessionGen(True) as session:
        user = get_user(session, update)
        if user is None:
            return

        circle = user.circle
        user.circle = None
        if circle is not None:
            bot.send_message(chat_id=update.message.chat_id, text="You just left circle {}".format(circle.name))
        else:
            bot.send_message(chat_id=update.message.chat_id, text="You were not a member of a circle")

def handle_present(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.choice = True
        bot.send_message(chat_id=update.message.chat_id, text="We'll be happy to see you!")

def handle_absent(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.choice = False
        bot.send_message(chat_id=update.message.chat_id, text="So sorry you won't be dining with us!")

def handle_status(bot, update):
    with SessionGen(True) as session:
        user = get_user(session, update)
        if user is None:
            return

        circle = user.circle
        if circle is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before knowing about others' presence!")
            return

        statements = circle.get_current_statements()
        presents = [st for st in statements if st.choice is True]
        absents = [st for st in statements if st.choice is False]
        unknowns = [st for st in statements if st.choice is None]

        def send_list(desc, statements):
            message = "{} ({})".format(desc, len(statements))
            if len(statements) > 0:
                message += ":\n"
                message += "\n".join([st.get_pretty_name() for st in statements])
            bot.send_message(chat_id=update.message.chat_id, text=message)

        send_list('Present', presents)
        send_list('Absent', absents)
        send_list('Unknown', unknowns)

def handle_message(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.value = update.message.text
        bot.send_message(chat_id=update.message.chat_id, text="Thanks for your precious message!")

def main():
    create_db()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    token = open('telegram_token').read().strip()
    updater = Updater(token=token)

    start_handler = CommandHandler('start', handle_start)
    updater.dispatcher.add_handler(start_handler)
    join_handler = CommandHandler('join', handle_join, pass_args=True)
    updater.dispatcher.add_handler(join_handler)
    leave_handler = CommandHandler('leave', handle_leave)
    updater.dispatcher.add_handler(leave_handler)
    present_handler = CommandHandler('present', handle_present)
    updater.dispatcher.add_handler(present_handler)
    absent_handler = CommandHandler('absent', handle_absent)
    updater.dispatcher.add_handler(absent_handler)
    status_handler = CommandHandler('status', handle_status)
    updater.dispatcher.add_handler(status_handler)
    message_handler = MessageHandler(Filters.text, handle_message)
    updater.dispatcher.add_handler(message_handler)

    # Start main cycle
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
