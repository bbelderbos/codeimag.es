from sqlmodel import Session, SQLModel, create_engine, select
from passlib.context import CryptContext

from .config import DATABASE_URL, DEBUG
from .exceptions import UserExists
from .models import User, UserCreate, Tip

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


def get_user_by_id(user_id):
    with Session(engine) as session:
        user = session.get(User, user_id)
        return user


def get_user_by_username(username):
    with Session(engine) as session:
        query = select(User).where(User.username == username)
        user = session.exec(query).first()
        return user


def email_used_by_user(email):
    with Session(engine) as session:
        query = select(User).where(User.email == email)
        return len(session.exec(query).all()) > 0


def create_user(username, email, password):
    encrypted_pw = get_password_hash(password)
    with Session(engine) as session:
        user = UserCreate(username=username, email=email, password=encrypted_pw)
        db_user = User.from_orm(user)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


def get_tip_by_id(tip_id):
    with Session(engine) as session:
        tip = session.get(Tip, tip_id)
        return tip


def delete_this_tip(tip):
    with Session(engine) as session:
        session.delete(tip)
        session.commit()


def get_tip_by_title(title):
    with Session(engine) as session:
        query = select(Tip).where(Tip.title == title)
        tip = session.exec(query).first()
        return tip


def create_new_tip(tip, user):
    with Session(engine) as session:
        db_tip = Tip.from_orm(tip)
        db_tip.user = user
        db_tip.language = db_tip.language.lower()
        session.add(db_tip)
        session.commit()
        session.refresh(db_tip)
        return db_tip


def get_all_tips(offset, limit):
    with Session(engine) as session:
        tips = session.exec(select(Tip).offset(offset).limit(limit)).all()
        return tips
