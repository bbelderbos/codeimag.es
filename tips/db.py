from datetime import date, datetime, timedelta
import hashlib
import secrets

from sqlmodel import Session, SQLModel, create_engine, select, or_
from passlib.context import CryptContext
from sqlalchemy import func

from .config import DATABASE_URL, DEBUG
from .models import User, UserCreate, Tip

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = create_engine(DATABASE_URL, echo=DEBUG)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def _generate_activation_key(username):
    """
    Generate a random activation key
    See https://stackoverflow.com/a/24936834/1128469
    """
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    secret_key = "".join(secrets.choice(chars) for i in range(20))
    return hashlib.sha256((secret_key + username).encode("utf-8")).hexdigest()


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_activation_key(session, key):
    query = select(User).where(User.activation_key == key)
    user = session.exec(query).first()
    return user


def activate_user(session, user):
    user.verified = True
    user.activation_key = ""
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_username(session, username):
    query = select(User).where(User.username == username)
    user = session.exec(query).first()
    return user


def email_used_by_user(session, email):
    query = select(User).where(User.email == email)
    return len(session.exec(query).all()) > 0


def create_user(session, username, email, password):
    encrypted_pw = get_password_hash(password)
    user = UserCreate(username=username, email=email, password=encrypted_pw)
    db_user = User.from_orm(user)
    db_user.activation_key = _generate_activation_key(username)
    db_user.key_expires = datetime.utcnow() + timedelta(days=2)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_tips_posted_today(session, user):
    today = date.today()
    tomorrow = date.today() + timedelta(days=1)
    # where is 'and' by default, for or use sqlmodel.or_
    #
    # test revealed that this did not work:
    # cast(Tip.added, Date) == date.today()
    #
    # 'between' does - https://stackoverflow.com/a/8898533
    query = select(Tip).where(Tip.user == user, Tip.added.between(today, tomorrow))
    return session.exec(query).all()


def get_tip_by_id(session, tip_id):
    tip = session.get(Tip, tip_id)
    return tip


def delete_this_tip(session, tip):
    session.delete(tip)
    session.commit()


def get_tip_by_title(session, title, user):
    query = select(Tip).where(Tip.title == title, Tip.user == user)
    tip = session.exec(query).first()
    return tip


def create_new_tip(session, tip, url, user):
    db_tip = Tip.from_orm(tip)
    db_tip.url = url
    db_tip.user = user
    db_tip.language = db_tip.language.lower()
    session.add(db_tip)
    session.commit()
    session.refresh(db_tip)
    return db_tip


def get_all_tips(session, offset, limit, term=None):
    statement = select(Tip)
    if term is not None:
        term = term.lower()
        statement = statement.where(
            or_(
                func.lower(Tip.title).contains(term),
                func.lower(Tip.code).contains(term),
                func.lower(Tip.description).contains(term),
            )
        )
    statement = statement.offset(offset).limit(limit)
    statement = statement.order_by(Tip.added.desc())
    tips = session.exec(statement).all()
    return tips
