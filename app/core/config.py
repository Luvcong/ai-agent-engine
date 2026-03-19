from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class OpikSettings(BaseSettings):
    """Opik configuration."""

    ENABLED: bool = Field(default=True, description="Enable Opik tracing")
    URL_OVERRIDE: str | None = Field(default=None, description="Opik base URL")
    # Optional if you are using Opik Cloud:
    API_KEY: str | None = Field(default=None, description="opik cloud api key here")
    WORKSPACE: str | None = Field(default=None, description="your workspace name")
    PROJECT: str | None = Field(default=None, description="your project name")


class Settings(BaseSettings):
    # API 설정
    API_V1_PREFIX: str

    CORS_ORIGINS: List[str] = ["*"]
    
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    
    # 공공데이터포털 serviceKey와 HTTP timeout 설정
    PUBLIC_DATA_API_KEY: str = ""
    PUBLIC_DATA_TIMEOUT: int = 20

    # Elasticsearch 조회용 설정
    ELASTICSEARCH_URL: str = ""
    ELASTICSEARCH_USERNAME: str = ""
    ELASTICSEARCH_PASSWORD: str = ""
    ELASTICSEARCH_INDEX: str = "edu-collection"
    ELASTICSEARCH_TIMEOUT: int = 20

    # API 조회 limit 수 설정
    DRUG_SEARCH_LIMIT: int = 5
    DISEASE_SEARCH_LIMIT: int = 5
    HOSPITAL_SEARCH_LIMIT: int = 5
    PHARMACY_SEARCH_LIMIT: int = 5
    ELASTICSEARCH_DISEASE_SEARCH_LIMIT: int = 5

    # LangGraph checkpointer의 SQLite 파일 저장 위치
    SQLITE_CHECKPOINTER_PATH: str = "app/data/checkpoints.db"

    # 한 요청에서 모델/tool 반복 횟수 상한값
    DEEPAGENT_RECURSION_LIMIT: int = 10

    OPIK: OpikSettings | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
