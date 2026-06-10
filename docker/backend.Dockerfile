# syntax=docker/dockerfile:1
#
# Backend image — FastAPI on Python 3.11-slim.
# Build context is the repository root (see docker-compose.yml / CI).
#
# Base image is digest-pinned for a reproducible baseline (FedRAMP CM-2).
# To update: docker pull python:3.11-slim && re-pin the new sha256 below.
FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0

# Create an unprivileged user to run the app (CM-7 least functionality).
RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install pinned runtime dependencies first for better layer caching.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY backend/app ./app

USER app

EXPOSE 8000

# Container-level readiness signal (no extra tools — uses the stdlib).
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
