from datetime import date, datetime, timedelta
import hashlib
import secrets

from sqlmodel import Session, SQLModel, create_engine, select, or_
from passlib.context import CryptContext
from sqlalchemy import Date, cast, func

from .config import DATABASE_URL, DEBUG, FREE_DAILY_TIPS
from .exceptions import UserExists
from .models import User, UserCreate, Tip

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = create_engine(DATABASE_URL, echo=DEBUG)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def _generate_activation_key(username):
    'https://stackoverflow.com/a/24936834/1128469'
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    secret_key = ''.join(secrets.choice(chars) for i in range(20))
    return hashlib.sha256((secret_key + username).encode('utf-8')).hexdigest()


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_activation_key(key):
    with Session(engine) as session:
        query = select(User).where(User.activation_key == key)
        user = session.exec(query).first()
        return user


def activate_user(user):
    with Session(engine) as session:
        user.verified = True
        user.activation_key = ""
        session.add(user)
        session.commit()
        session.refresh(user)
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
        db_user.activation_key = _generate_activation_key(username)
        db_user.key_expires = datetime.utcnow() + timedelta(days=2)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


def get_tips_by_user(user):
    with Session(engine) as session:
        query = select(Tip).where(
            Tip.user == user,
            cast(Tip.added, Date) == date.today()
        )
        return session.exec(query).all()


def user_is_exceeding_rate_limit(user):
    num_tips = len(get_tips_by_user(user))
    if user.premium and num_tips >= user.premium_day_limit:
        return True
    else:
        return num_tips >= FREE_DAILY_TIPS
    return False


def get_tip_by_id(tip_id):
    with Session(engine) as session:
        tip = session.get(Tip, tip_id)
        return tip


def delete_this_tip(tip):
    with Session(engine) as session:
        session.delete(tip)
        session.commit()


def get_tip_by_title(title, user):
    with Session(engine) as session:
        query = select(Tip).where(
            Tip.title == title,
            Tip.user == user
        )
        tip = session.exec(query).first()
        return tip


def create_new_tip(tip, url, user):
    with Session(engine) as session:
        db_tip = Tip.from_orm(tip)
        db_tip.url = url
        db_tip.user = user
        db_tip.language = db_tip.language.lower()
        session.add(db_tip)
        session.commit()
        session.refresh(db_tip)
        return db_tip


def get_all_tips(offset, limit, term=None):
    with Session(engine) as session:
        statement = select(Tip)
        if term is not None:
            term = term.lower()
            statement = statement.where(
                or_(
                    func.lower(Tip.title).contains(term),
                    func.lower(Tip.code).contains(term),
                    func.lower(Tip.description).contains(term)
                )
            )
        statement = statement.offset(offset).limit(limit)
        statement = statement.order_by(Tip.added.desc())
        tips = session.exec(statement).all()
        return tips
