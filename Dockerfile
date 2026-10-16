# syntax=docker/dockerfile:1

# Base image pinned by digest so every build uses exactly the same image.
ARG PYTHON_IMAGE=python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce

# ---- Stage 1: install dependencies into a virtual environment ----
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# ---- Stage 2: small runtime image, no build tools ----
FROM ${PYTHON_IMAGE}
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/vulntracker.db

# Unprivileged user. /data is the only directory the app can write to.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && mkdir /data && chown app:app /data

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
# Code is owned by root, so the running app cannot modify itself.
COPY app/ .

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

# No secrets here: JWT_SECRET_KEY is supplied at runtime (env var or mounted file).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]