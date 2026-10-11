# Multi-stage Dockerfile for Kredibel (Single image deployed to web and worker)
# See docs/16-infrastructure-and-deployment.md §5

# ==============================================================================
# Stage 1: Build Frontend SPA
# ==============================================================================
FROM node:22-slim AS web-builder

WORKDIR /fe

# Build-time public variables for Firebase
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_APP_VERSION

ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY \
    VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN \
    VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID \
    VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID \
    VITE_APP_VERSION=$VITE_APP_VERSION

COPY contracts/ /contracts/
COPY frontend/package.json frontend/package-lock.json* ./

RUN npm ci

COPY frontend/ ./

# docs/16 §5: API types come from the contract (/contracts/openapi.yaml), never from a checkout.
RUN npm run gen:api && npm run build

# ==============================================================================
# Stage 2: Runtime Backend (FastAPI + Workers)
# ==============================================================================
FROM python:3.12-slim AS app-runtime

# The version is a property of the image, so web, worker and the migrate job all report it.
ARG APP_VERSION=dev

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=$APP_VERSION \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install backend dependencies
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

# Copy application source code and contracts
COPY contracts/ /app/contracts/
COPY backend/app/ /app/app/
COPY backend/migrations/ /app/migrations/
COPY backend/scripts/ /app/scripts/

# Copy built frontend SPA assets to static directory
COPY --from=web-builder /fe/dist /app/static

# Run as non-root user
RUN adduser --disabled-password --gecos "" kredibel && \
    chown -R kredibel:kredibel /app

USER kredibel

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
