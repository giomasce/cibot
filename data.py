# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, Column, Integer, ForeignKey, DateTime, UniqueConstraint, Boolean, Date, Unicode, Time, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.schema import Index
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import session as sessionlib
from sqlalchemy.orm.session import object_session

import datetime

db = create_engine(open('database_url').read().strip(), echo=False)
Session = sessionmaker(db)
Base = declarative_base(db)

def create_db():
    Base.metadata.create_all(db)

class Circle(Base):
    __tablename__ = 'circles'
    __table_args__ = (
        UniqueConstraint('name', name="const_circle_name"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(Unicode, nullable=False)
    can_join = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    join_code = Column(Unicode, nullable=True, default=None, server_default=text('null'))
    bottom_line = Column(Unicode, nullable=True, default=None, server_default=text('null'))

    def get_current_phase(self, when=None, successive=False):
        if when is None:
            when = datetime.datetime.now()
        if successive:
            moment = self.moments[0]
            prev_date = False
        else:
            moment = self.moments[-1]
            prev_date = True
        for moment2 in self.moments:
            if moment2.time <= when.time():
                if not successive:
                    moment = moment2
                    prev_date = False
            else:
                if successive:
                    moment = moment2
                    prev_date = False
                break
        date = when.date()
        if prev_date:
            date -= datetime.timedelta(days=1)
        session = object_session(self)
        try:
            phase = session.query(Phase).filter(Phase.date == date). \
                filter(Phase.moment == moment).one()
        except NoResultFound:
            phase = Phase()
            phase.date = date
            phase.moment = moment
            session.add(phase)

        return phase

    def get_current_statements(self, when=None):
        if when is None:
            when = datetime.datetime.now()
        phase = self.get_current_phase(when=when)
        session = object_session(self)
        statements = session.query(Statement).join(User).filter(User.circle == self).filter(Statement.phase == phase).all()
        #statements = session.query(User).outerjoin(Statement).filter(User.circle == self).filter(Statement.phase == phase).all()
        return statements

    def get_current_nonvoters(self, when=None):
        if when is None:
            when = datetime.datetime.now()
        phase = self.get_current_phase(when=when)
        session = object_session(self)
        # TODO - Use a real query
        users = session.query(User).filter(User.circle == self).all()
        nonvoters = []
        for user in users:
            if user.get_current_statement(when=when) is None:
                nonvoters.append(user)
        return nonvoters

class Moment(Base):
    __tablename__ = 'moments'
    __table_args__ = (
        UniqueConstraint('circle_id', 'name', name="const_moment_circle_name"),
        UniqueConstraint('circle_id', 'time', name="const_moment_circle_time"),
    )

    id = Column(Integer, primary_key=True)
    circle_id = Column(Integer, ForeignKey(Circle.id, onupdate="CASCADE", ondelete="CASCADE", name="fk_moment_circle"), nullable=True)
    name = Column(Unicode)
    time = Column(Time)
    reminder_time = Column(Time)

    circle = relationship(Circle, backref=backref("moments", order_by="Moment.time"))

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('tid', name="const_user_tid"),
    )

    id = Column(Integer, primary_key=True)
    circle_id = Column(Integer, ForeignKey(Circle.id, onupdate="CASCADE", ondelete="CASCADE", name="fk_user_circle"), nullable=True)
    tid = Column(Integer, nullable=False)
    first_name = Column(Unicode)
    last_name = Column(Unicode)
    username = Column(Unicode)
    enabled = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    default_choice = Column(Boolean, nullable=True, default=None, server_default=text('null'))
    reminder = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    loud = Column(Boolean, nullable=False, default=False, server_default=text('false'))

    circle = relationship(Circle, backref="members")

    def get_pretty_name(self):
        return self.first_name + ' ' + self.last_name

    def get_current_statement(self, when=None, for_update=False, successive=False):
        if when is None:
            when = datetime.datetime.now()
        if self.circle is None:
            return None
        phase = self.circle.get_current_phase(when=when, successive=successive)
        session = object_session(self)
        try:
            statement = session.query(Statement).filter(Statement.user == self).filter(Statement.phase == phase).one()
        except NoResultFound:
            if for_update:
                statement = Statement()
                statement.user = self
                statement.phase = phase
                session.add(statement)
            else:
                statement = None

        if for_update:
            statement.time = when

        return statement

    @classmethod
    def get_from_telegram_user(cls, session, tg_user):
        try:
            user = session.query(User).filter(User.tid == tg_user.id).one()
        except NoResultFound:
            user = User()
            user.tid = tg_user.id
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.username = tg_user.username
            user.enabled = True
            session.add(user)

        return user

class Phase(Base):
    __tablename__ = 'phases'
    __table_args__ = (
        UniqueConstraint('date', 'moment_id', name="const_phase_date_moment"),
        )

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    moment_id = Column(Integer, ForeignKey(Moment.id, onupdate="CASCADE", ondelete="CASCADE", name="fk_phase_moment"), nullable=False)

    moment = relationship(Moment)

    def get_pretty_name(self):
        return self.moment.name + ' ' + self.date.strftime('%d/%m/%Y')

class Statement(Base):
    __tablename__ = 'statements'
    __table_args__ = (
        UniqueConstraint('user_id', 'phase_id', name="const_statement_user_phase"),
        )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, onupdate="CASCADE", ondelete="CASCADE", name="fk_statement_user"), nullable=False)
    phase_id = Column(Integer, ForeignKey(Phase.id, onupdate="CASCADE", ondelete="CASCADE", name="fk_statement_phase"), nullable=False)
    time = Column(DateTime, nullable=False)
    comment = Column(Unicode, nullable=True, default=None, server_default=text('null'))
    choice = Column(Integer, nullable=True, default=None, server_default=text('null'))

    user = relationship(User)
    phase = relationship(Phase)

    def get_pretty_name(self):
        return self.user.get_pretty_name() + (('+{}'.format(self.choice-1)) if self.choice is not None and self.choice > 1 else '') + ((' (' + self.comment + ')') if self.comment is not None else '')

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
