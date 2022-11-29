from pathlib import Path

from decouple import config


DATABASE_URL = config("DATABASE_URL")
DEBUG = config("DEBUG", default=False, cast=bool)

if DEBUG:
    CHROME_DRIVER = str(Path.home() / "bin" / "chromedriver")
else:  # pragma: no cover
    # from Heroku buildpack
    CHROME_DRIVER = ".chromedriver/bin/chromedriver"
    # SQLAlchemy + Heroku
    # https://help.heroku.com/ZKNTJQSK/why-is-sqlalchemy-1-4-x-not-connecting-to-heroku-postgres
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
ADMIN_EMAIL = config("ADMIN_EMAIL")
SENDGRID_API_KEY = config("SENDGRID_API_KEY", default="")
AWS_S3_BUCKET = config("AWS_S3_BUCKET", default="")
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = config("AWS_REGION", default="")
