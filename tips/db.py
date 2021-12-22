from decouple import config
from sqlmodel import Session, SQLModel, create_engine, select
from passlib.context import CryptContext

from .models import User, Tip

DATABASE_URL = config("DATABASE_URL")
DEBUG = config("DEBUG", default=False, cast=bool)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

if "postgresql" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres", "postgresql")

engine = create_engine(DATABASE_URL, echo=DEBUG)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_all_users(offset, limit):
    with Session(engine) as session:
        users = session.exec(select(User).offset(offset).limit(limit)).all()
        return users


def get_user_by_id(user_id):
    with Session(engine) as session:
        user = session.get(User, user_id)
        return user


def get_user_by_username(username):
    with Session(engine) as session:
        query = select(User).where(User.username == username)
        user = session.exec(query).first()
        return user


def get_tip_by_title(title):
    with Session(engine) as session:
        query = select(Tip).where(Tip.title == title)
        tip = session.exec(query).first()
        return tip


def create_tip(tip):
    with Session(engine) as session:
        tip = Tip.from_orm(tip)
        session.add(tip)
        session.commit()
        return tip


def get_all_tips(offset, limit):
    with Session(engine) as session:
        tips = session.exec(select(Tip).offset(offset).limit(limit)).all()
        return tips
