#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
import logging
import datetime

from data import SessionGen, create_db, User, Phase, Statement, Circle, Moment

def main():
    create_db()

if __name__ == '__main__':
    main()
