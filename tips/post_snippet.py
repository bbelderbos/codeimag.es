import sys

# pip install requests python-decouple
import requests
from decouple import config

CODEIMAGES_USER = config("CODEIMAGES_USER", default="")
CODEIMAGES_PASSWORD = config("CODEIMAGES_PASSWORD", default="")

if not CODEIMAGES_USER or not CODEIMAGES_PASSWORD:
    print("Please set your CODEIMAGES_USER and CODEIMAGES_PASSWORD in .env")
    sys.exit(1)

BASE_URL = "https://pybites-codeimages.herokuapp.com"
CREATE_TIP_URL = f"{BASE_URL}/create"
TOKEN_URL = f"{BASE_URL}/token"


def _write_multiline_input(action):
    print(f"{action}, enter <enter>+qq to finish: ")
    lines = []
    exit = "qq"
    while True:
        line = input()
        if line.strip().lower() == exit:
            break
        lines.append(line)
    return "\n".join(lines)


def get_token():
    payload = {"username": CODEIMAGES_USER, "password": CODEIMAGES_PASSWORD}
    resp = requests.post(TOKEN_URL, data=payload)
    token = resp.json()["access_token"]
    return token


def main():
    token = get_token()
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
        resp.raise_for_status()
        print(f"Code snippet posted to CodeImag.es: {BASE_URL}")

        if input("Press enter to post another tip, 'q' to exit: ") == "q":
            print("Bye")
            break


if __name__ == "__main__":
    main()
