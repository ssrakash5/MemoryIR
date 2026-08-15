from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


_LOCAL_HACKATHON_ROOT = Path(__file__).resolve().parents[2]
HACKATHON_ROOT = (
    _LOCAL_HACKATHON_ROOT
    if (_LOCAL_HACKATHON_ROOT / "MemoryIR_End_to_End_Hackathon_Blueprint.md").exists()
    else Path(__file__).resolve().parents[1]
)
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if ENV_KEY_RE.match(key):
            os.environ.setdefault(key, value)


_load_env_file(HACKATHON_ROOT / "creds.env")
_load_env_file(HACKATHON_ROOT / ".env")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    env: str = os.environ.get("MEMORYIR_ENV", "local")
    provider: str = os.environ.get("MEMORYIR_PROVIDER", "mock")
    database_backend: str = os.environ.get("MEMORYIR_DATABASE_BACKEND") or (
        "cockroach" if os.environ.get("DATABASE_URL") else "memory"
    )
    database_url: str | None = os.environ.get("DATABASE_URL") or None
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    bedrock_embed_model_id: str = os.environ.get(
        "BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"
    )
    bedrock_agent_model_id: str = os.environ.get(
        "BEDROCK_AGENT_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
    )
    bedrock_max_tokens: int = int(os.environ.get("BEDROCK_MAX_TOKENS", "700"))
    mcp_endpoint: str = os.environ.get("MCP_ENDPOINT", "https://cockroachlabs.cloud/mcp")
    mcp_api_key: str | None = os.environ.get("MCP_API_KEY") or None
    mcp_cluster_id: str | None = os.environ.get("MCP_CLUSTER_ID") or None
    default_top_k: int = int(os.environ.get("DEFAULT_TOP_K", "5"))
    cors_origins: tuple[str, ...] = tuple(
        _csv(os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
    )
    frontend_dist: str = os.environ.get("FRONTEND_DIST", "static")

    @property
    def repo_root(self) -> Path:
        return HACKATHON_ROOT

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def frontend_dist_path(self) -> Path:
        path = Path(self.frontend_dist)
        if path.is_absolute():
            return path
        return self.backend_root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
