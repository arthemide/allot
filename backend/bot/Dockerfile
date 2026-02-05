###############################################
# Builder Image
###############################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV PYSETUP_PATH="/app"

WORKDIR $PYSETUP_PATH

# Copy shared package first (dependency)
COPY shared /app/shared

# Copy bot files
COPY bot/pyproject.toml ./
COPY uv.lock ./

# Install dependencies (including shared package)
RUN uv sync --frozen --no-dev && \
    uv pip install -e /app/shared

COPY bot/dca/ $PYSETUP_PATH/dca/

###############################################
# Production Image
###############################################
FROM python:3.12-slim-bookworm AS production

ENV PYSETUP_PATH="/app"

WORKDIR $PYSETUP_PATH

# Copy the virtual environment and shared package from builder
COPY --from=builder $PYSETUP_PATH/.venv $PYSETUP_PATH/.venv
COPY --from=builder $PYSETUP_PATH/shared $PYSETUP_PATH/shared
COPY --from=builder $PYSETUP_PATH/dca ./dca

ENV PATH="$PYSETUP_PATH/.venv/bin:$PATH"

# Default command: start scheduler
CMD ["python", "-m", "dca.main"]
