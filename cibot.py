#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext.jobqueue import Job
import logging
import datetime

from data import SessionGen, create_db, User, Phase, Statement, Circle, Moment

def get_user(session, update):
    user = User.get_from_telegram_user(session, update.message.from_user)
    if not user.enabled:
        return None
    return user

def get_user_and_statement(session, update, for_update=False, successive=False):
    user = get_user(session, update)
    if user is None:
        return None, None
    statement = user.get_current_statement(for_update=for_update, successive=successive)
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
        bot.sendMessage(chat_id=update.message.chat_id, reply_markup=reply_markup, text="Welcome!")

def handle_join(bot, update, args):
    with SessionGen(True) as session:
        user = get_user(session, update)
        if user is None:
            return

        if len(args) < 1:
            bot.send_message(chat_id=update.message.chat_id, text="You have to specify a circle")
            return
        circle_name = args[0]

        circle = session.query(Circle).filter(Circle.name == circle_name).first()
        if circle is None:
            bot.send_message(chat_id=update.message.chat_id, text="Circle {} does not exist!".format(circle_name))
            return

        # Verify authorization
        if not circle.can_join:
            bot.send_message(chat_id=update.message.chat_id, text="Circle {} cannot be joined".format(circle_name))
            return
        if circle.join_code is not None:
            if len(args) < 2:
                bot.send_message(chat_id=update.message.chat_id, text="You have to specify a code to join circle {}".format(circle_name))
                return
            code = args[1]
            if code != circle.join_code:
                bot.send_message(chat_id=update.message.chat_id, text="The code is invalid".format(circle_name))
                return

        # Verify positively authorization as a precaution
        if circle.can_join and (circle.join_code is None or circle.join_code == code):
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

        statement.choice = 1
        bot.send_message(chat_id=update.message.chat_id, text="We'll be happy to see you!")

        if False:
            for user2 in user.circle:
                if user2.loud and user2 != user:
                    bot.send_message(chat_id=user2.tid, text="{} just reported to be present".format(user.get_pretty_name()))

def handle_absent(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.choice = 0
        bot.send_message(chat_id=update.message.chat_id, text="So sorry you won't be dining with us!")

        if False:
            for user2 in user.circle:
                if user2.loud and user2 != user:
                    bot.send_message(chat_id=user2.tid, text="{} just reported to be absent".format(user.get_pretty_name()))

def handle_next_present(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True, successive=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.choice = 1
        bot.send_message(chat_id=update.message.chat_id, text="We'll be happy to see you!")

def handle_next_absent(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True, successive=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.choice = 0
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
        presents = [st for st in statements if st.choice is not None and st.choice > 0]
        absents = [st for st in statements if st.choice is not None and st.choice == 0]
        unknowns = [st for st in statements if st.choice is None]

        nonvoters = circle.get_current_nonvoters()

        def send_list(desc, statements, users=None):
            if users is None:
                users = []
            message = "{} ({})".format(desc, len(statements) + len(users))
            if len(statements) + len(users) > 0:
                message += ":"
                if len(statements) > 0:
                    message += "\n"
                    message += "\n".join([st.get_pretty_name() for st in statements])
                if len(users) > 0:
                    message += "\n"
                    message += "\n".join([u.get_pretty_name() for u in users])
            bot.send_message(chat_id=update.message.chat_id, text=message)

        bot.send_message(chat_id=update.message.chat_id, text="Known total is {}".format(sum([st.choice for st in presents])))
        send_list('Present', presents)
        send_list('Absent', absents)
        send_list('Unknown', unknowns, nonvoters)
        if circle.bottom_line is not None:
            bot.send_message(chat_id=update.message.chat_id, text=circle.bottom_line)

def handle_message(bot, update):
    with SessionGen(True) as session:
        user, statement = get_user_and_statement(session, update, for_update=True)
        if user is None:
            return

        if statement is None:
            bot.send_message(chat_id=update.message.chat_id, text="You have to join a circle before expressing your presence!")
            return

        statement.comment = update.message.text
        bot.send_message(chat_id=update.message.chat_id, text="Thanks for your precious message!")

def handle_reminder_job(bot, job):
    with SessionGen(False) as session:
        moment = session.query(Moment).filter(Moment.id == job.context).one()
        circle = moment.circle
        for user in circle.members:
            if user.reminder and user.get_current_statement() is None:
                bot.send_message(chat_id=user.tid, text="We would REALLY like to know if you'll be eating with us or not!")

def main():
    create_db()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    token = open('telegram_token').read().strip()
    updater = Updater(token=token)

    # Install handlers
    handlers = [
        ('start', handle_start, {}),
        ('join', handle_join, {"pass_args": True}),
        ('leave', handle_leave, {}),
        ('present', handle_present, {}),
        ('absent', handle_absent, {}),
        ('next_present', handle_next_present, {}),
        ('next_absent', handle_next_absent, {}),
        ('status', handle_status, {}),
    ]
    for handler_data in handlers:
        handler = CommandHandler(handler_data[0], handler_data[1], **handler_data[2])
        updater.dispatcher.add_handler(handler)
    message_handler = MessageHandler(Filters.text, handle_message)
    updater.dispatcher.add_handler(message_handler)

    # Install jobs
    # TODO: update jobs when database is modified
    with SessionGen(False) as session:
        for circle in session.query(Circle):
            for moment in circle.moments:
                job = Job(handle_reminder_job, interval=datetime.timedelta(days=1), repeat=True, context=moment.id)
                next_datetime = datetime.datetime.combine(datetime.date.today(), moment.reminder_time)
                if datetime.datetime.now() > next_datetime:
                    next_datetime += datetime.timedelta(days=1)
                next_t = (next_datetime - datetime.datetime.now()).total_seconds()
                updater.job_queue.put(job, next_t=next_t)

    # Start main cycle
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
