"""Esto de acá simplemente configura parámetros para que OLlama no consuma más recursos de los que debería"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5-coder:1.5b"
    ollama_temperature: float = 0.2
    ollama_timeout: float = 600.0
    generated_dir: Path = Path("/data/generated")
    cors_origins: str = "*"


settings = Settings()
