from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from tips.db import get_password_hash
from tips.main import app, get_session
from tips.models import User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="user")
def user1(session: Session):
    encrypted_pw = get_password_hash("some_pass1")
    user = User(
        username="bob",
        email="bob@pybit.es",
        password=encrypted_pw,
        password2=encrypted_pw,
    )
    user.active
    session.add(user)
    session.commit()
    yield user
    session.delete(user)


@pytest.fixture(name="inactive_user")
def user2(session: Session, user: User):
    user.active = False
    session.add(user)
    session.commit()
    yield user


def test_signup(session: Session, client: TestClient):
    response = client.post(
        "/users/",
        json={
            "username": "bob",
            "email": "bob@pybit.es",
            "password": "some_pass1",
            "password2": "some_pass1",
        },
    )
    assert response.status_code == 201
    user = session.exec(select(User)).one()
    assert user.username == "bob"
    assert user.email == "bob@pybit.es"
    assert user.active is True
    assert user.verified is False
    assert user.premium is False
    assert user.premium_day_limit == 10
    assert (user.key_expires.date() - user.added.date()).days == 2


def test_signup_username_already_in_use(
    session: Session, client: TestClient, user: User
):
    response = client.post(
        "/users/",
        json={
            "username": "bob",
            "email": "bob@pybit.es",
            "password": "some_pass1",
            "password2": "some_pass1",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "User already exists"}


def test_signup_email_already_used(session: Session, client: TestClient, user: User):
    response = client.post(
        "/users/",
        json={
            "username": "frank",
            "email": "bob@pybit.es",
            "password": "some_pass1",
            "password2": "some_pass1",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already in use"}


def test_signup_non_matching_password(session: Session, client: TestClient, user: User):
    response = client.post(
        "/users/",
        json={
            "username": "frank",
            "email": "frank@pybit.es",
            "password": "some_pass1",
            "password2": "some_pass2",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "The two passwords should match"}


def test_inactive_user_cannot_obtain_token(inactive_user: User, client: TestClient):
    response = client.post(
        "/token",
        data={
            "username": "bob",
            "password": "some_pass1",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == ["Inactive account"]
