from sqlalchemy import create_engine, MetaData, Column, Integer, String, Table, DateTime, ForeignKey, PrimaryKeyConstraint, Boolean, \
        PickleType, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Files(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    fileId = Column(String(300), unique=True)

    lastModDate = Column(DateTime)

    isFile = Column(Boolean)

    dates = relationship("Dates", back_populates="files", lazy="select")
    name = relationship("Filename", back_populates="files", lazy="select")

    def __repr__(self):
        return f"Files\n"


class Dates(Base):
    __tablename__ = "dates"
    id = Column(Integer, primary_key=True, autoincrement=True)

    fileId = Column(Integer, ForeignKey('files.id'))

    date = Column(Float)
    adds = Column(Integer)
    deletes = Column(Integer)
    bin_width = Column(Float)

    #Relationships
    files = relationship("Files", back_populates="dates")

    __table_args__ = (PrimaryKeyConstraint(name='dates_pk',
                                           mssql_clustered=False), )

    def __repr__(self):
        return f"Dates Object: {self.date}, {self.adds}, {self.deletes}"


class Closure(Base):
    __tablename__ = 'closure'
    id = Column(Integer, primary_key=True, autoincrement=True)

    parent = Column(Integer, ForeignKey('files.id'))
    child = Column(Integer, ForeignKey('files.id'))
    depth = Column(Integer)

    child_r = relationship("Files", foreign_keys=[child])
    parent_r = relationship("Files", foreign_keys=[parent])

    __table_args__ = (PrimaryKeyConstraint(name='closure_pk',
                                           mssql_clustered=False), )


class Filename(Base):
    __tablename__ = 'filename'

    id = Column(Integer, primary_key=True, autoincrement=True)

    fileId = Column(Integer, ForeignKey('files.id'))
    fileName = Column(String(600))

    files = relationship("Files", back_populates="name", foreign_keys=[fileId])

    __table_args__ = (PrimaryKeyConstraint(name='filename_pk',
                                           mssql_clustered=False), )


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
