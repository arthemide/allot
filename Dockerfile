# Five builds, one image. Two of them are pinned to $BUILDPLATFORM so they run
# natively on the CI runner instead of under emulation: the front compiles to
# static files and uv only resolves a lockfile, so neither output depends on the
# target architecture. Only the runtime stage is built for the target -- which
# matters, because that target is a 32-bit Raspberry Pi.

FROM --platform=$BUILDPLATFORM node:26-alpine AS front
WORKDIR /front
COPY front/package.json front/package-lock.json ./
RUN npm ci
COPY front/ ./
RUN npm run build

# uv resolves uv.lock into a pinned, hashed requirements.txt. Doing it here
# rather than in the runtime stage keeps uv off the target architecture
# entirely; uv.lock stays the single source of truth either way.
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o requirements.txt

# curl_cffi ships an armv7 wheel; its own dependency cffi does not, and has to
# be compiled. Doing it in a throwaway stage keeps gcc and the headers out of
# the image that actually ships.
FROM python:3.14-slim AS wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=deps /app/requirements.txt ./
RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt

# Litestream publishes a binary per architecture but an image for only two of
# them, so the binary is what gets used. Fetched on the build platform and
# picked by target, which keeps this stage off the emulator.
FROM --platform=$BUILDPLATFORM alpine:3.21 AS litestream
ARG LITESTREAM_VERSION=0.5.16
ARG TARGETARCH
ARG TARGETVARIANT
# The alpine base carries no CA bundle, and busybox wget over HTTPS fails
# without one -- with a message that says nothing about certificates.
RUN apk add --no-cache ca-certificates
RUN set -eu; \
    case "${TARGETARCH}${TARGETVARIANT}" in \
        amd64) asset=x86_64 ;; \
        arm64) asset=arm64  ;; \
        armv7) asset=armv7  ;; \
        armv6) asset=armv6  ;; \
        *) echo "no Litestream build for ${TARGETARCH}${TARGETVARIANT}" >&2; exit 1 ;; \
    esac; \
    wget -qO /tmp/litestream.tar.gz \
        "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-${asset}.tar.gz"; \
    tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream

FROM python:3.14-slim
WORKDIR /app

COPY --from=wheels /install /usr/local
COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream

COPY app.py schema.sql docker-entrypoint.sh ./
COPY litestream.yml /etc/litestream.yml
COPY src/ ./src/
COPY --from=front /front/dist ./front/dist

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALLOT_HOST=0.0.0.0 \
    ALLOT_PORT=8000 \
    ALLOT_DB_PATH=/data/allot.db

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=120s --timeout=20s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["./docker-entrypoint.sh"]
