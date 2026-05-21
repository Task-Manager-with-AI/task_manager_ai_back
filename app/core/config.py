from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the AI service.

    AI_PROVIDER controls which backend powers transcription and LLM calls:
      - "deepseek": uses DeepSeek API for LLM + faster-whisper for transcription.
                    Requires DEEPSEEK_API_KEY.
      - "local":    uses faster-whisper (local) + Ollama (local LLM).
                    Requires `ollama` Python package and a running Ollama server.
    """

    AI_PROVIDER: Literal["deepseek", "local"] = "deepseek"

    # DeepSeek (OpenAI-compatible chat API; no audio transcription endpoint)
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_LLM_MODEL: str = "deepseek-chat"

    # Local (faster-whisper + Ollama)
    LOCAL_WHISPER_MODEL: str = "tiny"  # tiny|base|small|medium|large-v3 — tiny recommended on Render CPU
    LOCAL_WHISPER_DEVICE: str = "cpu"  # cpu|cuda
    LOCAL_WHISPER_COMPUTE_TYPE: str = "int8"
    LOCAL_WHISPER_BEAM_SIZE: int = 1  # 1 = fastest; 5 = default quality
    HF_TOKEN: Optional[str] = None  # optional Hugging Face token for faster model downloads
    WHISPER_PRELOAD_ON_STARTUP: bool = True
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.1:8b"

    DEFAULT_LANGUAGE: str = "es"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
