from sqlalchemy import create_engine, MetaData, Column, Integer, String, Table, DateTime, ForeignKey 
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import *
from sqlalchemy.sql import *
from sqlalchemy.orm import sessionmaker, relationship, scoped_session

Base = declarative_base()
class Files(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key = True)

    fileName = Column(String(120))
    fileId = Column(String(120), unique = True)

    lastModDate = Column(DateTime)
    parent_id = Column(String(120), ForeignKey('owner.name'))
    parent = relationship("Owner", back_populates = "children")

    children = relationship("Dates", back_populates = "parent")

    def __repr__(self):
        return f"Files\n"

class Owner(Base):
    __tablename__ = "owner"
    id = Column(Integer, primary_key = True)
    name = Column(String(120), unique = True)
    children = relationship("Files", back_populates = "parent")
    def __repr__(self):
        return f"Owner \n"
class Dates(Base):
    __tablename__ = "dates"
    id = Column(Integer, primary_key = True)
    parent_id = Column(String(120), ForeignKey('files.fileId'))
    moddate = Column(DateTime)

    parent = relationship("Files", back_populates = "children")

    def __repr__(self):
        return f"Date \n"

class Closure(Base):
    __tablename__='closure'
    id = Column(Integer, primary_key=True)
    parent = Column(String(120))
    child = Column(String(120))
    owner_id = Column(String(120), ForeignKey('owner.name'))
    depth = Column(Integer)


def create(engine, sess):
    print("creating"*100)
    Base.metadata.create_all(bind=engine)
    sess.commit()
