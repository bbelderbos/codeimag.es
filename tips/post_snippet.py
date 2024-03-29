"""
Script to post a code snippet to Pybites Codeimag.es ->
https://pybites-codeimages.herokuapp.com
"""
from pprint import pprint as pp
import sys

import requests
from decouple import config

CODEIMAGES_USER = config("CODEIMAGES_USER")
CODEIMAGES_PASSWORD = config("CODEIMAGES_PASSWORD")
DEBUG = config("DEBUG", cast=bool, default=False)
LIVE_SITE = "https://pybites-codeimages.herokuapp.com"
BASE_URL = "http://localhost:8000" if DEBUG else LIVE_SITE
TOKEN_URL = f"{BASE_URL}/token"
CREATE_TIP_URL = f"{BASE_URL}/create"


def _write_multiline_input(action):
    print(f"{action}, enter <enter>+qq to finish: ")
    lines = []
    exit_mark = "qq"
    while True:
        line = input()
        if line.strip().lower() == exit_mark:
            break
        lines.append(line)
    return "\n".join(lines)


def get_token(user, password):
    payload = {"username": user, "password": password}
    resp = requests.post(TOKEN_URL, data=payload)
    data = resp.json()

    if "access_token" not in data:
        sys.exit(data["detail"])

    return data["access_token"]


def main(args):
    try:
        user, password, *_ = args
    except ValueError:
        user, password = CODEIMAGES_USER, CODEIMAGES_PASSWORD

    token = get_token(user, password)

    while True:
        title = input("Add a title: ")
        code = _write_multiline_input("Paste your code snippet")
        description = _write_multiline_input("Add an optional description")

        payload = {
            "title": title.strip(),
            "code": code.lstrip(),
            "description": description.strip(),
        }
        print("Posting tip ...")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(CREATE_TIP_URL, json=payload, headers=headers)
        if str(resp.status_code).startswith("2"):
            print(f"Code snippet posted to CodeImag.es: {BASE_URL}")
        else:
            print(f"Something went wrong, API returned status code {resp.status_code}")
        print()
        print("API response:")
        pp(resp.json())

        if input("Press enter to post another tip, 'q' to exit: ") == "q":
            print("Bye")
            break


if __name__ == "__main__":
    main(sys.argv[1:])
