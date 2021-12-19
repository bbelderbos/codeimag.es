from decouple import config
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = config("DATABASE_URL")
DEBUG = config("DEBUG", default=False, cast=bool)


engine = create_engine(DATABASE_URL, echo=DEBUG)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
