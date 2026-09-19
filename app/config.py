from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM providers
    groq_api_key: str
    openai_api_key: str

    # Vector DB
    qdrant_api_key: str
    qdrant_cluster_endpoint: str
    cohere_api_key: str
    tavily_api_key: str
    langsmith_api_key: str
    langsmith_tracing: bool = True
    langsmith_project: str = "kubernetes-rag"

    # Added later: jina_api_key, portkey_api_key, langsmith_api_key, logfire_token


@lru_cache
def get_settings() -> Settings:
    return Settings()

import os


def configure_langsmith():
    settings = get_settings()
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project