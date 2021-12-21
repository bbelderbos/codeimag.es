from datetime import datetime, timedelta
import base64
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlmodel import Session, select
from pybites_tools.aws import upload_to_s3
from carbon.carbon import create_code_image
from decouple import config

from .db import engine, create_db_and_tables, get_session, get_password_hash, verify_password
from .models import Tip, TipRead, TipCreate, User, UserRead, UserCreate, Token, TokenData
from .user import create_user

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# buildpack
CHROME_DRIVER = ".chromedriver/bin/chromedriver"
USER_DIR = "/tmp/{user_id}"
ENCODING = "utf-8"
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/users/", response_model=list[UserRead])
def get_users(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100)
):
    users = session.exec(select(User).offset(offset).limit(limit)).all()
    return users


@app.get("/users/{user_id}", response_model=UserRead)
def get_user(*, session: Session = Depends(get_session), user_id: int):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/", response_model=TipRead)
def create_tip(*, session: Session = Depends(get_session), tip: TipCreate):
    query = select(Tip).where(Tip.title == tip.title)
    existing_tip = session.exec(query).first()
    if existing_tip is not None:
        raise HTTPException(status_code=400, detail="Tip already exists")

    user = session.get(User, tip.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Not a valid user id")

    # to not clash with other users
    user_dir = USER_DIR.format(user_id=tip.user_id)
    os.makedirs(user_dir, exist_ok=True)

    expected_carbon_outfile = os.path.join(user_dir, "carbon.png")
    options = {
        "language": tip.language,
        "background": tip.background,
        "theme": tip.theme,
        "driver_path": CHROME_DRIVER,
        "destination": user_dir,
    }
    create_code_image(tip.code, **options)

    byte_str = f"{user.username}_{tip.title}".encode(ENCODING)
    key = base64.b64encode(byte_str)
    encrypted_filename = key.decode(ENCODING) + ".png"

    unique_user_filename = os.path.join(user_dir, encrypted_filename)
    os.rename(expected_carbon_outfile, unique_user_filename)

    url = upload_to_s3(unique_user_filename)
    tip.url = url

    os.remove(unique_user_filename)
    os.rmdir(user_dir)

    db_tip = Tip.from_orm(tip)
    session.add(db_tip)
    session.commit()
    session.refresh(db_tip)
    return db_tip


@app.get("/", response_model=list[TipRead])
def get_tips(*, session: Session = Depends(get_session)):
    query = select(Tip)
    return session.exec(query).all()


@app.delete("/{tip_id}")
def delete_tip(*, session: Session = Depends(get_session), tip_id: int):
    tip = session.get(Tip, tip_id)
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    session.delete(tip)
    session.commit()
    return {"ok": True}


def get_user(username):
    with Session(engine) as session:
        query = select(User).where(User.username == username)
        user = session.exec(query).first()
        if user is not None:
            raise HTTPException(status_code=400, detail="User already exists")
        return user


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users", status_code=201, response_model=User)
def signup(payload: UserCreate):
    """Create a new user in the database"""
    username = payload.username
    password = payload.password
    password2 = payload.password2

    user = get_user(username)
    if user is not None:
        raise HTTPException(
            status_code=400,
            detail="User already exists",
        )

    if password != password2:
        raise HTTPException(
            status_code=400,
            detail="The two passwords should match",
        )

    ret = create_user(username, password)
    return ret
