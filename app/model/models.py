from sqlalchemy import Column, Integer, String, DateTime, Enum
from datetime import datetime
from app.model.database import Base
from enum import Enum as PyEnum
import pytz

KST = pytz.timezone('Asia/Seoul')

class Status(PyEnum):
    PENDING = "대기 중"
    APPROVED = "승인됨"
    REJECTED = "거절됨"
    EXIT = "퇴입"

class User(Base):
    __tablename__ = 'users'
    uno = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    aname = Column(String(50), nullable=True)
    job = Column(String(100), nullable=True)
    ob = Column(String(100), nullable=True)
    status = Column(Enum(Status), default=Status.PENDING)
    regdate = Column(DateTime, default=lambda: datetime.now(KST).replace(microsecond=0))


class Admin(Base):
    __tablename__ = 'admins'
    ano = Column(Integer, primary_key=True, index=True, autoincrement=True)
    aname = Column(String(50), nullable=False)
    id = Column(String(50), nullable=False, unique=True)
    passwd = Column(String(50), nullable=False)

class EntryExitLog(Base):
    __tablename__ = 'entry_exit_logs'
    no = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    aname = Column(String(50), nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    entry_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    exit_time = Column(DateTime, nullable=True)
