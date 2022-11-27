from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

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


@pytest.fixture(name="testuser")
def user_fixture(session: Session):
    user = User(username="bob", email="bob@pybit.es", password="some_pass1")
    session.add(user)
    session.commit()
    yield user
    session.delete(user)


def test_create_user(session: Session, client: TestClient):
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
