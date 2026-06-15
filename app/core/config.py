from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the AI service.

    AI_PROVIDER controls which backend powers LLM calls:
      - "deepseek": DeepSeek API (requires DEEPSEEK_API_KEY).
      - "local":    Ollama (requires `ollama` package and a running Ollama server).

    TRANSCRIPTION_PROVIDER controls speech-to-text:
      - "groq":   Groq Whisper API (requires GROQ_API_KEY) — fast, free tier available.
      - "openai": OpenAI Whisper API (requires OPENAI_API_KEY).
      - "local":  faster-whisper on this machine (CPU/GPU).
    """

    AI_PROVIDER: Literal["deepseek", "local"] = "deepseek"
    TRANSCRIPTION_PROVIDER: Literal["groq", "openai", "local"] = "groq"

    # DeepSeek (OpenAI-compatible chat API)
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_LLM_MODEL: str = "deepseek-chat"

    # Groq Whisper API (OpenAI-compatible audio endpoint)
    GROQ_API_KEY: Optional[str] = None
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"  # or whisper-large-v3

    # OpenAI Whisper API
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_WHISPER_MODEL: str = "whisper-1"

    # Local faster-whisper
    LOCAL_WHISPER_MODEL: str = "tiny"  # tiny|base|small|medium|large-v3
    LOCAL_WHISPER_DEVICE: str = "cpu"  # cpu|cuda
    LOCAL_WHISPER_COMPUTE_TYPE: str = "int8"
    LOCAL_WHISPER_BEAM_SIZE: int = 1  # 1 = fastest; 5 = default quality
    HF_TOKEN: Optional[str] = None  # optional Hugging Face token for faster model downloads
    WHISPER_PRELOAD_ON_STARTUP: bool = True
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.1:8b"

    DEFAULT_LANGUAGE: str = "es"
    DOCX_MAX_CONTENT_CHARS: int = 200000
    DOCX_CALLBACK_TIMEOUT_SECONDS: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
