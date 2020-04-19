from sqlalchemy import create_engine, MetaData, Column, Integer, String, Table, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import *
from sqlalchemy.sql import *
from sqlalchemy.orm import sessionmaker, relationship, scoped_session

Base = declarative_base()


class Files(Base):
    __tablename__ = "files"
    fileId = Column(String(40), primary_key=True, unique=True)
    lastModDate = Column(DateTime)
    parent_id = Column(String(40), ForeignKey('owner.name'))

    parent = relationship("Owner", back_populates="children")
    children = relationship("Dates", back_populates="parent")


    def __repr__(self):
        return f"Files\n"


class Owner(Base):
    __tablename__ = "owner"

    name = Column(String(40), unique=True, primary_key=True)

    children = relationship("Files", back_populates="parent")

    def __repr__(self):
        return f"Owner \n"


class Dates(Base):
    __tablename__ = "dates"
    id = Column(Integer, primary_key=True, autoincrement=True)

    fileId = Column(String(40), ForeignKey('files.fileId'))
    moddate = Column(DateTime)

    parent = relationship("Files", back_populates="children")


    def __repr__(self):
        return f"Date \n"


class Closure(Base):
    __tablename__ = 'closure'
    id = Column(Integer, primary_key=True, autoincrement=True)

    parent = Column(String(45))
    child = Column(String(45), ForeignKey('files.fileId'))
    owner_id = Column(String(40), ForeignKey('owner.name'))
    depth = Column(Integer)

    __table_args__ = (
        PrimaryKeyConstraint(name='closure_pk', mssql_clustered=False),
    )


class Filename(Base):
    __tablename__ = 'filename'
    id = Column(Integer, primary_key=True, autoincrement=True)

    fileId = Column(String(40), ForeignKey('files.fileId'))
    fileName = Column(String(300))
    owner_id = Column(String(40), ForeignKey('owner.name'))


    __table_args__ = (
        PrimaryKeyConstraint(name='filename_pk', mssql_clustered=False),
    )


def create(engine, sess):
    print("creating" * 100)
    Base.metadata.create_all(bind=engine)
    sess.commit()
