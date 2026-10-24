# The whole helpdesk in one image: FastAPI serves the API and the built React app.
# Build: docker compose build    Run: docker compose up    (see compose.yaml)
# Base images are pinned to a digest (a tag can be republished; a digest cannot change).

# ---- Stage 1: build the web app (Node is only needed here, not in the final image)
FROM node:24.21.0-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the running app (Python, runtime libraries only)
FROM python:3.15.0-slim@sha256:f5b92f2a669a4c347044f29367f31983280b648250ca94dea66f98c53bc87e58
COPY --from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    LOG_FORMAT=json \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Libraries first (this layer is reused until uv.lock changes): exactly uv.lock, runtime only
# (no dev tools, no Streamlit panel), using this image's own Python.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-default-groups --no-install-project

# The app: code, the documents and search index, the label rulebook, the built web app.
COPY src/ src/
COPY docs/labels.md docs/labels.md
COPY data/knowledge_base/ data/knowledge_base/
COPY data/kb_index.json data/kb_index.json
COPY data/demo_tickets.json data/demo_tickets.json
COPY --from=web /web/dist frontend/dist
COPY tools/add_staff.py tools/add_staff.py

# Run as a normal user, not root: if the app were ever broken into, the attacker gets little.
# (The data lives in Postgres, set by DATABASE_URL: nothing in this image needs writing.)
RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["uvicorn", "api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
