import argparse

from .db import create_user


def main():
    parser = argparse.ArgumentParser("Create a user")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-e", "--email", required=True)
    parser.add_argument("-p", "--password", required=True)
    args = parser.parse_args()
    create_user(args.username, args.email, args.password)


if __name__ == "__main__":
    main()
