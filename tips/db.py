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


def create_user(username, email, password):
    encrypted_pw = get_password_hash(password)
    with Session(engine) as session:
        query = select(User).where(User.username == username)
        existing_user = session.exec(query).first()

        if existing_user is not None:
            raise UserExists(f"Username {username} already exists")

        user = UserCreate(username=username, email=email, password=encrypted_pw)
        db_user = User.from_orm(user)
        session.add(db_user)
        session.commit()


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
        tip = Tip.from_orm(tip)
        tip.user = user
        session.add(tip)
        session.commit()
        session.refresh(tip)
        return tip


def get_all_tips(offset, limit):
    with Session(engine) as session:
        tips = session.exec(select(Tip).offset(offset).limit(limit)).all()
        return tips
