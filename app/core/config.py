import os
from datetime import timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)


class Settings:
    app_name = "edu_cockpit"

    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = int(os.getenv("DB_PORT", "3306"))
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "edu_admin")

    jwt_secret = os.getenv("JWT_SECRET", "sane")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    llm_model_intent = os.getenv("LLM_MODEL_INTENT", "gpt-4o-mini")
    intent_confidence_threshold = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.7"))
    node_io_log_dir = os.getenv("NODE_IO_LOG_DIR", "local_logs/node_io")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def access_token_expires(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)


settings = Settings()
