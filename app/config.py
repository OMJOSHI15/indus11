from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret"

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


settings = Settings()
