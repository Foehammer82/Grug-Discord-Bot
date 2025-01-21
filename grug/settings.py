import os
from pathlib import Path

from loguru import logger
from pydantic import Field, PostgresDsn, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).parent.parent.resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / "config" / "secrets.env",),
        extra="ignore",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    discord_token: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # Discord Settings
    discord_bot_enable_contextual_responses: bool = Field(
        default=True,
        description=(
            "This will enable the messaging bot to respond in group chats without being @mentioned.  It evaluates "
            "the last message and chat history to determine if it should respond."
        ),
    )

    # AI Agent Settings
    ai_name: str = "Grug"
    ai_openai_model: str = "gpt-4o"
    ai_enable_duckduckgo_search: bool = False
    ai_base_instructions: str = "\n".join(
        [
            f"- your name is {ai_name}.",
            "- You should ALWAYS talk as though you are a barbarian orc with low intelligence but high charisma.",
            "- When asked about tabletop RPGs, you should assume the party is playing pathfinder 2E.",
            "- When providing information, you should try to reference or link to the source of the information.",
            "- When providing links to images, make sure to format them as markdown links so the image shows up.",
        ]
    )
    ai_image_generation_enabled: bool = True
    ai_image_daily_generation_limit: int | None = Field(
        default=25, description="The daily limit of image generations. If None, there is no limit."
    )
    ai_image_default_size: str = "1024x1024"
    ai_image_default_quality: str = "standard"
    ai_image_default_model: str = "dall-e-3"

    # Database Settings
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("postgres")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_apscheduler_schema: str = "apscheduler"
    postgres_genai_schema: str = "genai"

    @computed_field
    @property
    def root_dir(self) -> Path:
        """Get the root directory of the project."""
        logger.info(f"Root dir: {_ROOT_DIR}")
        return _ROOT_DIR

    @computed_field
    @property
    def postgres_dsn(self) -> str:
        """Get the Postgres DSN."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                host=self.postgres_host,
                port=self.postgres_port,
                username=self.postgres_user,
                password=self.postgres_password.get_secret_value(),
                path=self.postgres_db,
            )
        )


settings = Settings()

# used to set the environment variables for the OpenAI API key for local development
os.environ["OPENAI_API_KEY"] = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
