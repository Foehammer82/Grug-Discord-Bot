from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel
from sqlmodel._compat import SQLModelConfig


class SQLModelValidation(SQLModel):
    """
    Helper class to allow for validation in SQLModel classes with table=True
    """

    model_config = SQLModelConfig(from_attributes=True, validate_assignment=True)


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
