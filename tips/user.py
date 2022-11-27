import argparse
import sys

from sqlmodel import Session

from .db import engine as default_engine, create_user, get_user_by_username


def main(args, *, engine=None):
    engine = engine or default_engine

    parser = argparse.ArgumentParser("Create a user")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-e", "--email", required=True)
    parser.add_argument("-p", "--password", required=True)

    args = parser.parse_args(args)

    with Session(engine) as session:
        user = get_user_by_username(session, args.username)
        if user is not None:
            print(f"{args.username} already exists")
            sys.exit(1)

        create_user(session, args.username, args.email, args.password)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
