from sqlalchemy import create_engine, MetaData, Column, Integer, String, Table, DateTime, ForeignKey, PrimaryKeyConstraint, Boolean, \
        PickleType, Float
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import *
from sqlalchemy.sql import *
from sqlalchemy.orm import sessionmaker, relationship, scoped_session

Base = declarative_base()


class Files(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    fileId = Column(String(300),unique=True)

    lastModDate = Column(DateTime)

    parent_id = Column(Integer, ForeignKey('owner.id'))
    isFile = Column(Boolean)

    owner = relationship("Owner", back_populates="files")
    dates = relationship("Dates", back_populates="files", lazy = "select")
    name = relationship("Filename", back_populates="files", lazy = "select")


    def __repr__(self):
        return f"Files\n"


class Owner(Base):
    __tablename__ = "owner"
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    name = Column(String(50), unique=True)

    files = relationship("Files", back_populates="owner")

    def __repr__(self):
        return f"Owner \n"


class Dates(Base):
    __tablename__ = "dates"
    id = Column(Integer, primary_key=True, autoincrement=True)

    fileId = Column(Integer, ForeignKey('files.id'))

    bins = Column(Float)
    values = Column(Integer)



    #Relationships
    files= relationship("Files", back_populates="dates")
    __table_args__ = (
        PrimaryKeyConstraint(name='dates_pk', mssql_clustered=False),
    )

    def __repr__(self):
        return f"Date \n"


class Closure(Base):
    __tablename__ = 'closure'
    id = Column(Integer, primary_key=True, autoincrement=True)

    parent = Column(Integer, ForeignKey('files.id'))
    child = Column(Integer, ForeignKey('files.id'))
    owner_id = Column(Integer, ForeignKey('owner.id'))
    depth = Column(Integer)

    files_relationship = relationship("Files", foreign_keys=[child])
    parent_relationship = relationship("Files", foreign_keys=[parent])
    owner = relationship("Owner", foreign_keys=[owner_id])

    __table_args__ = (
        PrimaryKeyConstraint(name='closure_pk', mssql_clustered=False),
    )


class Filename(Base):
    __tablename__ = 'filename'
    id = Column(Integer, primary_key=True, autoincrement=True)

    fileId = Column(Integer, ForeignKey('files.id'))
    fileName = Column(String(600))
    owner_id = Column(Integer, ForeignKey('owner.id'))

    files = relationship("Files", back_populates="name", foreign_keys = [fileId])
    owner = relationship("Owner", foreign_keys=[owner_id])


    __table_args__ = (
        PrimaryKeyConstraint(name='filename_pk', mssql_clustered=False),
    )


class Tasks(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String(600))
    creds = Column(PickleType)
    fileid = Column(String(600))
    userid = Column(String(600))

def create(engine, sess):
    print("creating" * 100)
    Base.metadata.create_all(bind=engine)
    sess.commit()
