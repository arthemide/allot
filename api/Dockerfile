###############################################
# Builder Image
###############################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV PYSETUP_PATH="/app"

# Copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY ./pyproject.toml ./uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

COPY ./src/ $PYSETUP_PATH/src/
COPY ./README.md $PYSETUP_PATH/README.md

###############################################
# Production Image
###############################################
FROM python:3.12-slim-bookworm AS production

ENV PYSETUP_PATH="/app"

WORKDIR $PYSETUP_PATH

# Copy the virtual environment from builder
COPY --from=builder $PYSETUP_PATH/.venv $PYSETUP_PATH/.venv
COPY --from=builder $PYSETUP_PATH/src ./src
COPY --from=builder $PYSETUP_PATH/README.md .

ENV PATH="$PYSETUP_PATH/.venv/bin:$PATH"

# Mount the config.json file to the container
VOLUME ./config.json

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
