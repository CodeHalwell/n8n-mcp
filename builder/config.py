from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    n8n_api_url: HttpUrl
    n8n_api_key: str
    n8n_env: str = Field(default="staging", pattern="^(staging|prod)$")
    http_timeout: int = 30

    @staticmethod
    def from_env() -> "Settings":
        url = os.getenv("N8N_API_URL")
        key = os.getenv("N8N_API_KEY")
        env = os.getenv("N8N_ENV", "staging")
        timeout = int(os.getenv("HTTP_TIMEOUT", "30"))
        if not url or not key:
            raise RuntimeError("Missing N8N_API_URL or N8N_API_KEY in environment.")
        return Settings(n8n_api_url=url, n8n_api_key=key, n8n_env=env, http_timeout=timeout)
