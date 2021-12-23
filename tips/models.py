from datetime import datetime
from typing import List, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from .config import FREE_DAILY_TIPS, PREMIUM_DAY_LIMIT


class UserBase(SQLModel):
    username: str
    email: str
    password: str


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tips: List["Tip"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all,delete"}
    )
    activation_key: str = ""
    key_expires: datetime = datetime.now()
    verified: bool = False
    active: bool = True
    premium: bool = False
    premium_day_limit: int = PREMIUM_DAY_LIMIT
    added: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow
        )
    )

    @property
    def max_daily_snippets(self):
        if self.premium:
            return self.premium_day_limit
        else:
            return FREE_DAILY_TIPS


class UserCreate(UserBase):
    password2: Optional[str]


class UserRead(UserBase):
    id: int


class TipBase(SQLModel):
    title: str
    code: str
    description: Optional[str]
    language: Optional[str] = "python"
    background: Optional[str] = "#ABB8C3"
    theme: Optional[str] = "seti"


class Tip(TipBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(
        back_populates="tips",
        sa_relationship_kwargs={"lazy": "subquery"}
    )
    public: bool = True
    added: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow
        )
    )
    url: Optional[str]


class TipCreate(TipBase):
    pass


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: Optional[str] = None
