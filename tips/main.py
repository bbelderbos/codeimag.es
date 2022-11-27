from datetime import datetime, timedelta
import base64
import os
from typing import Optional

from fastapi import Depends, Form, FastAPI, HTTPException, Query, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from jose import JWTError, jwt
from carbon.carbon import create_code_image

from .aws import upload_to_s3
from .config import (
    BASE_URL,
    CHROME_DRIVER,
    USER_DIR,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    FROM_EMAIL,
)
from .db import (
    get_session,
    activate_user,
    create_db_and_tables,
    create_user,
    email_used_by_user,
    verify_password,
    delete_this_tip,
    get_user_by_username,
    get_user_by_activation_key,
    get_tip_by_id,
    get_tip_by_title,
    get_tips_posted_today,
    get_all_tips,
    create_new_tip,
)
from .models import (
    Tip,
    TipCreate,
    User,
    UserCreate,
    Token,
    TokenData,
)
from .mail import send_email

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
templates = Jinja2Templates(directory="templates")


def authenticate_user(session, username: str, password: str):
    user = get_user_by_username(session, username)
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


def get_current_user(
    session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)
):
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
    user = get_user_by_username(session, token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/activate/{key}")
def activate(*, key: str, session: Session = Depends(get_session)):
    user = get_user_by_activation_key(session, key)
    if not user:
        raise HTTPException(status_code=400, detail="No account found for this key")

    if not user.active:
        raise HTTPException(status_code=400, detail="Inactive account")

    if user.verified:
        raise HTTPException(status_code=400, detail="Account already verified")

    if datetime.now() > user.key_expires:
        raise HTTPException(status_code=400, detail="Activation key expired")

    activate_user(session, user)
    return {"account_active": True}


@app.post("/create", status_code=201, response_model=Tip)
def create_tip(
    *,
    tip: TipCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tips_posted_today = get_tips_posted_today(session, current_user)
    if len(tips_posted_today) >= current_user.max_daily_snippets:
        msg = (
            f"Cannot exceed daily post rate of ({current_user.max_daily_snippets})"
            f" snippets. Do you need more? Contact us: {FROM_EMAIL}"
        )
        raise HTTPException(status_code=400, detail=msg)

    if get_tip_by_title(session, tip.title, current_user) is not None:
        raise HTTPException(status_code=400, detail="You already posted this tip")

    # to not clash with other users
    user_dir = USER_DIR.format(user_id=current_user.id)
    os.makedirs(user_dir, exist_ok=True)

    expected_carbon_outfile = os.path.join(user_dir, "carbon.png")
    options = {
        "language": tip.language,
        "background": tip.background,
        "theme": tip.theme,
        "wt": tip.wt,
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

    os.remove(unique_user_filename)
    os.rmdir(user_dir)

    tip = create_new_tip(session, tip, url, current_user)
    return tip


@app.delete("/{tip_id}")
def delete_tip(
    *,
    tip_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tip = get_tip_by_id(session, tip_id)
    if tip is None:
        raise HTTPException(status_code=404, detail="Tip not found")
    if tip.user != current_user:
        raise HTTPException(status_code=404, detail="Tip not owned by you")
    delete_this_tip(session, tip)
    return {"ok": True}


@app.get("/tips", response_model=list[Tip])
def get_tips(
    *,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    session: Session = Depends(get_session),
):
    tips = get_all_tips(session, offset, limit)
    return tips


@app.get("/", response_model=list[Tip])
def get_tips_web(
    *,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    session: Session = Depends(get_session),
    request: Request,
):
    tips = get_all_tips(session, offset, limit)
    return templates.TemplateResponse("tips.html", {"request": request, "tips": tips})


@app.post("/search", response_model=list[Tip])
def get_tips_search(
    *,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    session: Session = Depends(get_session),
    request: Request,
    term: str = Form(...),
):
    tips = get_all_tips(session, offset, limit, term=term)
    return templates.TemplateResponse(
        "tips.html", {"request": request, "tips": tips, "term": term}
    )


@app.post("/token", response_model=Token)
def login_for_access_token(
    *,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = authenticate_user(session, form_data.username, form_data.password)

    error = ""
    if not user:
        error = "Incorrect username or password"

    elif not user.active:
        error = "Inactive account"

    elif not user.verified:
        error = "User not verified"

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users", status_code=201, response_model=User)
def signup(*, payload: UserCreate, session: Session = Depends(get_session)):
    """Create a new user in the database"""
    username = payload.username
    email = payload.email
    password = payload.password
    password2 = payload.password2

    user = get_user_by_username(session, username)
    if user is not None:
        raise HTTPException(
            status_code=400,
            detail="User already exists",
        )

    if email_used_by_user(session, email):
        raise HTTPException(
            status_code=400,
            detail="Email already in use",
        )

    if password != password2:
        raise HTTPException(
            status_code=400,
            detail="The two passwords should match",
        )

    user = create_user(session, username, email, password)

    subject = "Please verify your CodeImag.es account"
    msg = f"{BASE_URL}/activate/{user.activation_key}"
    send_email(email, subject, msg)

    return user
