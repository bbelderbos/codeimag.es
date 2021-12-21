import base64
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, select
from pybites_tools.aws import upload_to_s3
from carbon.carbon import create_code_image
from .db import create_db_and_tables, get_session, get_password_hash
from .models import Tip, TipRead, TipCreate, User, UserRead, UserCreate

app = FastAPI()
# buildpack
CHROME_DRIVER = ".chromedriver/bin/chromedriver"
USER_DIR = "/tmp/{user_id}"
ENCODING = "utf-8"


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.post("/users/", response_model=UserRead)
def create_user(*, session: Session = Depends(get_session), user: UserCreate):
    query = select(User).where(User.username == user.username)
    existing_user = session.exec(query).first()
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="User already exists")

    user.password = get_password_hash(user.password)
    db_user = User.from_orm(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@app.get("/users/", response_model=list[UserRead])
def read_users(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100)
):
    users = session.exec(select(User).offset(offset).limit(limit)).all()
    return users


@app.get("/users/{user_id}", response_model=UserRead)
def read_user(*, session: Session = Depends(get_session), user_id: int):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.delete("/users/{user_id}")
def delete_user(*, session: Session = Depends(get_session), user_id: int):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"ok": True}


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
