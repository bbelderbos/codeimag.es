from datetime import datetime, timedelta
import base64
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pybites_tools.aws import upload_to_s3
from carbon.carbon import create_code_image

from .config import (
    CHROME_DRIVER,
    USER_DIR,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .db import (
    create_db_and_tables,
    create_user,
    email_used_by_user,
    verify_password,
    delete_this_tip,
    get_user_by_username,
    get_tip_by_id,
    get_tip_by_title,
    get_all_tips,
    create_new_tip,
)
from .models import (
    TipRead,
    TipCreate,
    User,
    UserCreate,
    Token,
    TokenData,
)

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
templates = Jinja2Templates(directory="templates")


def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    if not user or not verify_password(password, user.password):
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
    user = get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.post("/create", response_model=TipRead)
def create_tip(*, tip: TipCreate, current_user: User = Depends(get_current_user)):
    if get_tip_by_title(tip.title) is not None:
        raise HTTPException(status_code=400, detail="Tip already exists")

    # to not clash with other users
    user_dir = USER_DIR.format(user_id=current_user.id)
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

    byte_str = f"{current_user.username}_{tip.title}".encode("utf-8")
    key = base64.b64encode(byte_str)
    encrypted_filename = key.decode("utf-8") + ".png"

    unique_user_filename = os.path.join(user_dir, encrypted_filename)
    os.rename(expected_carbon_outfile, unique_user_filename)

    url = upload_to_s3(unique_user_filename)
    tip.url = url

    os.remove(unique_user_filename)
    os.rmdir(user_dir)

    tip = create_new_tip(tip, current_user)
    return tip


@app.delete("/{tip_id}")
def delete_tip(*, current_user: User = Depends(get_current_user), tip_id: int):
    tip = get_tip_by_id(tip_id)
    if tip is None:
        raise HTTPException(status_code=404, detail="Tip not found")
    if tip.user != current_user:
        raise HTTPException(status_code=404, detail="Tip not owned by you")
    delete_this_tip(tip)
    return {"ok": True}


@app.get("/tips", response_model=list[TipRead])
def get_tips(*, offset: int = 0, limit: int = Query(default=100, le=100)):
    tips = get_all_tips(offset, limit)
    return tips


@app.get("/", response_model=list[TipRead])
def get_tips_web(
    *, offset: int = 0, limit: int = Query(default=100, le=100), request: Request
):
    tips = get_all_tips(offset, limit)
    return templates.TemplateResponse("tips.html", {"request": request, "tips": tips})


@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
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
    email = payload.email
    password = payload.password
    password2 = payload.password2

    user = get_user_by_username(username)
    if user is not None:
        raise HTTPException(
            status_code=400,
            detail="User already exists",
        )

    if email_used_by_user(email):
        raise HTTPException(
            status_code=400,
            detail="Email already in use",
        )

    if password != password2:
        raise HTTPException(
            status_code=400,
            detail="The two passwords should match",
        )

    user = create_user(username, email, password)
    return user
