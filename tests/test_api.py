from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from tips.db import get_password_hash, _generate_activation_key
from tips.main import app, get_session, get_current_user
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
        activation_key=_generate_activation_key("bob"),
        key_expires=datetime.utcnow() + timedelta(days=2),
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


@pytest.fixture(name="verified_user")
def user3(session: Session, user: User):
    user.verified = True
    session.add(user)
    session.commit()
    yield user


@pytest.fixture(name="token")
def get_token(verified_user: User, session: Session, client: TestClient):
    response = client.post("/token", data={"username": "bob", "password": "some_pass1"})
    return response.json()["access_token"]


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


def test_signup_username_already_in_use(client: TestClient, user: User):
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
    assert response.json()["detail"] == "User already exists"


def test_signup_email_already_used(client: TestClient, user: User):
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
    assert response.json()["detail"] == "Email already in use"


def test_signup_non_matching_password(client: TestClient, user: User):
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
    assert response.json()["detail"] == "The two passwords should match"


def test_activate_user(user: User, client: TestClient):
    response = client.get("/activate/" + user.activation_key)
    assert response.status_code == 200
    assert response.json() == {"account_active": True}


def test_activate_wrong_key(user: User, client: TestClient):
    response = client.get("/activate/nonsense")
    assert response.status_code == 400
    assert response.json()["detail"] == "No account found for this key"


def test_activate_inactive_account(inactive_user: User, client: TestClient):
    response = client.get("/activate/" + inactive_user.activation_key)
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive account"


def test_activate_already_verified_account(verified_user: User, client: TestClient):
    response = client.get("/activate/" + verified_user.activation_key)
    assert response.status_code == 400
    assert response.json()["detail"] == "Account already verified"


def test_activate_expired_key(user: User, client: TestClient, session: Session):
    user.key_expires = datetime.utcnow() - timedelta(days=2)
    session.add(user)
    session.commit()
    response = client.get("/activate/" + user.activation_key)
    assert response.status_code == 400
    assert response.json()["detail"] == "Activation key expired"


def test_token(verified_user: User, client: TestClient):
    response = client.post(
        "/token",
        data={
            "username": "bob",
            "password": "some_pass1",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_token_wrong_password(user: User, client: TestClient):
    response = client.post(
        "/token",
        data={
            "username": "bob",
            "password": "blabla",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_token_inactive_account(inactive_user: User, client: TestClient):
    response = client.post(
        "/token",
        data={
            "username": "bob",
            "password": "some_pass1",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive account"


def test_token_unverified_account(user: User, client: TestClient):
    response = client.post(
        "/token",
        data={
            "username": "bob",
            "password": "some_pass1",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "User not verified"


def test_create_tip_logged_out(user: User, client: TestClient):
    response = client.post(
        "/create",
        json={
            "title": "hello world",
            "code": "print('hello world')",
            "description": "some description",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_tip_logged_in(client: TestClient, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/create",
        json={
            "title": "hello world",
            "code": "print('hello world')",
            "description": "some description",
        },
        headers=headers,
    )
    breakpoint()
