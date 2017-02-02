# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.schema import Index
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import session as sessionlib

import datetime

db = create_engine(open('database_url').read().strip(), echo=False)
Session = sessionmaker(db)
Base = declarative_base(db)

def create_db():
    Base.metadata.create_all(db)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tid = Column(Integer, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String)

class SessionGen(object):
    """This allows us to create handy local sessions simply with:

    with SessionGen() as session:
        session.do_something()

    and at the end the session is automatically rolled back and
    closed. If one wants to commit the session, they have to call
    commit() explicitly.

    """
    def __init__(self, auto_commit=False):
        self.session = None
        self.auto_commit = auto_commit

    def __enter__(self):
        self.session = Session()
        return self.session

    def __exit__(self, unused1, unused2, unused3):
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()
