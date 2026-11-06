from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    vault_path: Path = Path("D:/PRJ/AI-MindNet/vault")
    db_path: Path = Path("D:/PRJ/AI-MindNet/backend/mindnet.db")
    port: int = 8765
    git_debounce_seconds: int = 30
    git_remote: str = "https://github.com/guodage000/Mind-Net.git"
    git_branch: str = "main"

    class Config:
        env_file = ".env"
        env_prefix = "MINDNET_"


settings = Settings()
