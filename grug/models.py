from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel
from sqlmodel._compat import SQLModelConfig


class SQLModelValidation(SQLModel):
    """
    Helper class to allow for validation in SQLModel classes with table=True
    """

    model_config = SQLModelConfig(from_attributes=True, validate_assignment=True)


class User(SQLModelValidation, table=True):
    """
    SQLModel class for a user in the system.

    NOTE: the email is intentionally not required, to make it so that a discord user can auto create a user, we
          don't get an email from discord.  so we allow the email to be null and can later set up account linking
          features as needed in the even a multiple user accounts are create for the same person.
    """

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    discord_member_id: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger(), index=True))


class DalleImageRequest(SQLModelValidation, table=True):
    """Model for tracking image requests to the DALLE API."""

    __tablename__ = "dalle_image_requests"

    id: int | None = Field(default=None, primary_key=True)
    request_time: datetime = Field(
        default_factory=datetime.now, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    prompt: str
    model: str
    size: str
    quality: str
    revised_prompt: str | None = None
    image_url: str | None = None

    def __str__(self):
        return f"Dall-E Image {self.id} [{self.request_time}]"
