from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    # No usable default. A shared secret that ships with the source is not a
    # secret, and "dev-secret" was previously both the code default and the
    # dashboard's fallback, so the guard could be passed by reading the repo.
    # Development keeps a known key for convenience; anything else must set one.
    app_secret_key: str = ""

    @model_validator(mode="after")
    def _secret_key_must_be_set(self) -> "Settings":
        if self.app_env == "development":
            self.app_secret_key = self.app_secret_key or "dev-secret"
            return self
        # Outside development the published key is refused as firmly as no key:
        # copying .env.example and changing only APP_ENV must not pass.
        if self.app_secret_key == "dev-secret":
            raise ValueError(
                f"APP_SECRET_KEY is still the published development key while APP_ENV={self.app_env!r}. "
                "It is printed in the README and bundled into the dashboard. Set a real one."
            )
        if self.app_secret_key:
            return self
        raise ValueError(
            "APP_SECRET_KEY is not set. It guards every write route "
            "(/analyze, decision overrides, blacklist, label propagation). "
            "Set it in .env, or run with APP_ENV=development to accept the known dev key."
        )

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "indus11"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # LLM
    llm_provider: str = "openai"  # "openai" or "ollama"
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # Thresholds
    review_threshold: int = 40
    block_threshold: int = 70

    # Rate limiting — disable only for local benchmarking (scripts/evaluate.py),
    # which would otherwise trip the per-IP limit against its own machine.
    rate_limit_enabled: bool = True

    # Comma-separated allowed origins for the dashboard. A "*" wildcard here
    # would let any website's browser script this API — the dashboard's own
    # dev ports are the only legitimate callers.
    cors_origins: str = "http://localhost:5173,http://localhost:5175"


settings = Settings()
