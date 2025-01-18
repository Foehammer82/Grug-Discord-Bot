from pathlib import Path

from pydantic import PostgresDsn, SecretStr, computed_field
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

    # AI Agent Settings
    ai_agent_name: str = "Grug"
    ai_agent_openai_model: str = "gpt-4o"
    ai_agent_base_instructions: str = "\n".join(
        [
            f"- your name is {ai_agent_name}.",
            "- You should ALWAYS talk as though you are a barbarian orc with low intelligence but high charisma.",
            "- When asked about tabletop RPGs, you should assume the party is playing pathfinder 2E.",
            "- When providing information, you should try to reference or link to the source of the information.",
        ]
    )

    # Database Settings
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("postgres")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_apscheduler_schema: str = "apscheduler"

    @computed_field
    @property
    def root_dir(self) -> Path:
        """Get the root directory of the project."""
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
