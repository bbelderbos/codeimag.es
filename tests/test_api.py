from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tips.db import get_password_hash, _generate_activation_key
from tips.models import User, Tip

S3_FAKE_URL = "https://carbon-bucket.s3.us-east-2.amazonaws.com/beautiful-code.png"


@pytest.fixture(name="user")
def user1(session: Session):
    encrypted_pw = get_password_hash("some_pass1")
    user = User(
        username="bob",
        email="bob@pybit.es",
        password=encrypted_pw,
        password2=encrypted_pw,
        activation_key=_generate_activation_key("some-key"),
        key_expires=datetime.utcnow() + timedelta(days=2),
    )
    session.add(user)
    session.commit()
    yield user
    session.delete(user)


@pytest.fixture(name="other_user")
def user2(session: Session):
    encrypted_pw = get_password_hash("some_pass1")
    user = User(
        username="julian",
        email="julian@pybit.es",
        password=encrypted_pw,
        password2=encrypted_pw,
    )
    session.add(user)
    session.commit()
    yield user
    session.delete(user)


@pytest.fixture(name="inactive_user")
def user3(session: Session, user: User):
    user.active = False
    session.add(user)
    session.commit()
    yield user


@pytest.fixture(name="verified_user")
def user4(session: Session, user: User):
    user.verified = True
    session.add(user)
    session.commit()
    yield user


@pytest.fixture(name="limited_user")
def user5(session: Session, verified_user: User):
    verified_user.premium = True
    # not "real" but easy to test validation
    verified_user.premium_day_limit = 1
    session.add(verified_user)
    session.commit()
    yield verified_user


@pytest.fixture
def tip(session: Session, user: User):
    tip = Tip(
        title="hello world",
        code="print('hello world')",
        description="some description",
        user=user,
    )
    session.add(tip)
    session.commit()
    yield tip
    session.delete(tip)


@pytest.fixture
def tip_other_user(session: Session, other_user: User):
    tip = Tip(
        title="f-string debugging",
        code="f'{var=}')",
        description="another description",
        user=other_user,
    )
    session.add(tip)
    session.commit()
    yield tip
    session.delete(tip)


@pytest.fixture(name="token")
def get_token(verified_user: User, session: Session, client: TestClient):
    response = client.post("/token", data={"username": "bob", "password": "some_pass1"})
    return response.json()["access_token"]


@pytest.fixture(name="limited_token")
def get_token_limited_user(limited_user: User, session: Session, client: TestClient):
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
    assert (user.key_expires.date() - user.added.date()).days == 2  # type: ignore


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


@patch("tips.main.create_code_image")
@patch("tips.main.upload_to_s3", side_effect=[S3_FAKE_URL])
@patch("tips.main.os")
def test_create_tip_logged_in(
    os_mock: MagicMock,
    s3_mock: MagicMock,
    carbon_mock: MagicMock,
    session: Session,
    client: TestClient,
    token: str,
):
    """
    This test mocks out external dependencies in the create_tip endpoint.
    1. pybites-carbon that uses selenium to make the image on carbon.now.sh
    2. pybites-tools that uploads the image to S3
    3. os module stuff
    """
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
    assert response.status_code == 201

    tmp_path = "/tmp/1"
    os_mock.makedirs.assert_called_with(tmp_path, exist_ok=True)
    os_mock.rmdir.assert_called_with(tmp_path)

    tip = session.exec(select(Tip)).one()
    assert tip.description == "some description"
    assert tip.background == "#ABB8C3"
    assert tip.wt == "sharp"
    assert tip.url == S3_FAKE_URL
    assert tip.code == "print('hello world')"
    assert tip.title == "hello world"
    assert tip.language == "python"
    assert tip.theme == "seti"
    assert tip.public is True
    assert tip.user_id == 1


def test_create_tip_out_of_credits(
    session: Session,
    client: TestClient,
    tip: Tip,
    limited_token: str,
):
    """
    We need limited token + tip fixutres here
    -> limited token - links to limited_user which has
       a premium of max 1 token per day
    -> tip - triggers one tip already posted by user so
       the next attempt will exceed daily post rage
    """
    headers = {"Authorization": f"Bearer {limited_token}"}
    response = client.post(
        "/create",
        json={
            "title": "hello world",
            "code": "print('hello world')",
            "description": "some description",
        },
        headers=headers,
    )
    assert response.status_code == 400
    expected_msg_substr = (
        "Cannot exceed daily post rate of (1) snippets. Do you need more? Contact us"
    )
    assert expected_msg_substr in response.json()["detail"]


def test_create_tip_cannot_same_one_twice(
    session: Session,
    client: TestClient,
    tip: Tip,
    token: str,
):
    """
    We need limited user + tip fixutres here
    -> limited = premium of 1 token
    -> tip = one tip posted so next tip will exceed daily post rage
    """
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
    assert response.status_code == 400
    assert response.json() == {"detail": "You already posted this tip"}


def test_delete_tip(client: TestClient, tip: Tip, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete(
        "/1",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_delete_tip_loggedout(client: TestClient):
    response = client.delete("/1")
    assert response.status_code == 401


def test_delete_non_existing_tip_loggedin(user: User, client: TestClient, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete(
        "/1",
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Tip not found"}


def test_delete_existing_tip_not_owned_by_you(
    tip_other_user: Tip, client: TestClient, token: str
):
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete(
        "/1",
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Tip not owned by you"}


def test_get_all_tips(tip: Tip, tip_other_user: Tip, client: TestClient):
    response = client.get("/tips")
    # removing added column as it's not predictable (datetime)
    exclude_keys = {"added"}
    actual = [
        {k: row[k] for k in row.keys() - set(exclude_keys)} for row in response.json()
    ]
    expected = [
        {
            "description": "another description",
            "language": "python",
            "background": "#ABB8C3",
            "theme": "seti",
            "wt": "sharp",
            "id": 2,
            "user_id": 2,
            "public": True,
            "url": None,
            "title": "f-string debugging",
            "code": "f'{var=}')",
        },
        {
            "description": "some description",
            "language": "python",
            "background": "#ABB8C3",
            "theme": "seti",
            "wt": "sharp",
            "id": 1,
            "user_id": 1,
            "public": True,
            "url": None,
            "title": "hello world",
            "code": "print('hello world')",
        },
    ]
    assert actual == expected


def test_search(tip: Tip, tip_other_user: Tip, client: TestClient):
    response = client.post("/search", data={"term": "f-string"})
    assert response.text.count("<h2>") == 1
    assert "f-string debugging" in response.text
    assert "hello world" not in response.text
