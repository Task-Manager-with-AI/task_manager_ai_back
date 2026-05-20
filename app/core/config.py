from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the AI service.

    AI_PROVIDER controls which backend powers transcription and LLM calls:
      - "openai": uses OpenAI APIs (whisper-1 + gpt-4o-mini). Requires OPENAI_API_KEY.
      - "local":  uses faster-whisper (local) + Ollama (local LLM).
                  Requires `faster-whisper` and `ollama` Python packages installed,
                  and a running Ollama server with the configured model pulled.
    """

    AI_PROVIDER: Literal["openai", "local"] = "openai"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_WHISPER_MODEL: str = "whisper-1"
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"

    # Local (faster-whisper + Ollama)
    LOCAL_WHISPER_MODEL: str = "base"  # tiny|base|small|medium|large-v3
    LOCAL_WHISPER_DEVICE: str = "cpu"  # cpu|cuda
    LOCAL_WHISPER_COMPUTE_TYPE: str = "int8"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.1:8b"

    DEFAULT_LANGUAGE: str = "es"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
