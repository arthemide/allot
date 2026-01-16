###############################################
# Builder Image
###############################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV PYSETUP_PATH="/app"

# Copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH

# Copy shared package first (dependency)
COPY shared /app/shared

# Copy API files
COPY api/pyproject.toml ./
COPY uv.lock ./

# Install dependencies (including shared package)
RUN uv sync --frozen --no-dev && \
    uv pip install -e /app/shared

COPY api/src/ $PYSETUP_PATH/src/

###############################################
# Production Image
###############################################
FROM python:3.12-slim-bookworm AS production

ENV PYSETUP_PATH="/app"

WORKDIR $PYSETUP_PATH

# Copy the virtual environment and shared package from builder
COPY --from=builder $PYSETUP_PATH/.venv $PYSETUP_PATH/.venv
COPY --from=builder $PYSETUP_PATH/shared $PYSETUP_PATH/shared
COPY --from=builder $PYSETUP_PATH/src ./src

ENV PATH="$PYSETUP_PATH/.venv/bin:$PATH"


CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
