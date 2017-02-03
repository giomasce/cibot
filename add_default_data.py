#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
import logging
import datetime

from data import SessionGen, create_db, User, Phase, Statement, Circle, Moment

def main():
    create_db()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    with SessionGen(True) as session:
        circle = Circle()
        circle.name = "Famiglia"
        session.add(circle)
        for x in [('cena', 15), ('pranzo', 22)]:
            moment = Moment()
            moment.circle = circle
            moment.name = x[0]
            moment.time = datetime.time(hour=x[1])
            session.add(moment)

if __name__ == '__main__':
    main()
