import pytest
from sqlmodel import Session, create_engine, SQLModel, select

from tips.models import User
from tips.user import main


def test_cli(capfd, session: Session):
    args = ["-u", "peter", "-e", "peter@gmail.com", "-p", "some-pass"]
    engine = create_engine("sqlite:///")
    SQLModel.metadata.create_all(engine)
    main(args, engine=engine)

    with Session(engine) as session:
        users = session.exec(select(User)).all()
    assert len(users) == 1
    user = users[0]
    assert user.email == "peter@gmail.com"
    assert user.active is True
    assert user.username == "peter"
    assert user.verified is False
    assert user.premium is False

    # cannot make same user again
    with pytest.raises(SystemExit):
        main(args, engine=engine)

    assert capfd.readouterr().out.rstrip() == "peter already exists"
