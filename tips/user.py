import argparse

from sqlmodel import select, Session

from .db import engine, get_password_hash
from .models import User, UserCreate


class UserExists(Exception):
    pass


def create_user(args):
    encrypted_pw = get_password_hash(args.password)
    with Session(engine) as session:
        query = select(User).where(User.username == args.username)
        existing_user = session.exec(query).first()

        if existing_user is not None:
            raise UserExists(f"Username {args.username} already exists")

        user = UserCreate(
            username=args.username, email=args.email, password=encrypted_pw
        )
        db_user = User.from_orm(user)
        session.add(db_user)
        session.commit()


def main():
    parser = argparse.ArgumentParser("Create a user")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-e", "--email", required=True)
    parser.add_argument("-p", "--password", required=True)
    args = parser.parse_args()
    create_user(args)


if __name__ == "__main__":
    main()
