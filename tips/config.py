from pathlib import Path

from decouple import config


DATABASE_URL = config("DATABASE_URL")
if "postgresql" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres", "postgresql")

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
FREE_DAILY_TIPS = config("FREE_DAILY_TIPS", default=3, cast=int)
PREMIUM_DAY_LIMIT = config("PREMIUM_DAY_LIMIT", default=10, cast=int)
BASE_URL = config("BASE_URL")
FROM_EMAIL = config("FROM_EMAIL")  # notification email
ADMIN_EMAIL = config("ADMIN_EMAIL")  # admin email
