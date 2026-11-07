FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app/ ./app/
COPY data/sources/ ./data/sources/
COPY static/ ./static/
COPY --from=frontend /frontend/dist/ ./frontend/dist/
EXPOSE 8765
CMD ["/app/.venv/bin/python", "-m", "app.docker_start"]
