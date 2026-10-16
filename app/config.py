"""Application settings.

Secrets are NEVER written in this file. They are read at startup from, in order:
  1. A file in SECRETS_DIR (Kubernetes mounts secrets there, see helm/)
  2. An environment variable (handy for local development)
If a required secret is missing, the app refuses to start rather than
silently falling back to a weak default.
"""
import os
from typing import Optional

SECRETS_DIR = os.environ.get("SECRETS_DIR", "/run/secrets/vulntracker")


def _read_secret(name: str, default: Optional[str] = None) -> str:
    path = os.path.join(SECRETS_DIR, name.lower())
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    value = os.environ.get(name, default)
    if not value:
        raise RuntimeError(f"Required secret '{name}' is not set (file {path} or env var {name})")
    return value


SECRET_KEY = _read_secret("JWT_SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./vulntracker.db")
NOTIFY_SERVICE_URL = os.environ.get("NOTIFY_SERVICE_URL", "http://localhost:3001")

# Base URL used to build share links. Hard-coded default for the prototype.
# We deliberately do NOT build it from the incoming Host header (host-header injection).
SHARE_BASE_URL = os.environ.get("SHARE_BASE_URL", "http://localhost:8000").rstrip("/")

# Browser origins allowed to call the API (comma separated). Empty = none.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]