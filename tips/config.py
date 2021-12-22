from pathlib import Path

from decouple import config


DATABASE_URL = config("DATABASE_URL")
DEBUG = config("DEBUG", default=False, cast=bool)
if DEBUG:
    CHROME_DRIVER = Path.home() / "bin" / "chromedriver"
else:
    # from Heroku buildpack
    CHROME_DRIVER = ".chromedriver/bin/chromedriver"
USER_DIR = "/tmp/{user_id}"
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = config(
    "ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int
)
