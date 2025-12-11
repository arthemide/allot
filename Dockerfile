###############################################
# Builder Image
###############################################
FROM python:3.12-slim AS builder

ENV PYSETUP_PATH="/home/k8s" \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.cargo/bin:$PATH"

# Copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY ./pyproject.toml ./uv.lock ./Makefile ./

# Install dependencies
RUN uv sync --frozen

COPY ./src/ $PYSETUP_PATH/src/
COPY ./README.md $PYSETUP_PATH/README.md

###############################################
# Production Image
###############################################
FROM python:3.12-slim AS production

ENV PYSETUP_PATH="/home/k8s" \
    UV_SYSTEM_PYTHON=1

WORKDIR $PYSETUP_PATH

# Copy the virtual environment from builder
COPY --from=builder /root/.cargo/bin/uv /usr/local/bin/uv
COPY --from=builder $PYSETUP_PATH/.venv $PYSETUP_PATH/.venv
COPY --from=builder $PYSETUP_PATH/src ./src
COPY --from=builder $PYSETUP_PATH/README.md .

ENV PATH="$PYSETUP_PATH/.venv/bin:$PATH"

# Mount the config.json file to the container
VOLUME ./config.json

# Run app as non root and expose it to port 5000
USER 999

CMD ["python", "-m", "src.server"]
