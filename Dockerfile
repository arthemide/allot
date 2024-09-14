###############################################
# Builder Image
###############################################
FROM alpine AS builder

ENV POETRY_VERSION=1.8.2  \
    POETRY_HOME="/etc/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/home/k8s" \
    VENV_PATH="/home/k8s/.venv" \
    SHELL="/bin/bash"


RUN apk add --no-cache \
    make \
    curl \
    git \
    bash \
    build-base \
    libffi-dev \
    openssl-dev \
    bzip2-dev \
    zlib-dev \
    readline-dev \
    sqlite-dev

# Set the default shell to bash
SHELL ["/bin/bash", "-c"]

# Install pyenv
RUN curl https://pyenv.run | bash && \
    export PYENV_ROOT="$HOME/.pyenv" && \
    [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH" && \
    eval "$(pyenv init -)"

# Set environment variables for pyenv
ENV PYENV_ROOT /root/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# Copy .python-version into the Docker image
COPY .python-version ./

# # Install the Python version specified in .python-version
RUN pyenv install $(cat .python-version) && \
    pyenv global $(cat .python-version)

# Install Poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY ./pyproject.toml ./poetry.lock ./Makefile ./

RUN make install

COPY ./src/ $PYSETUP_PATH/src/
COPY ./README.md $PYSETUP_PATH/README.md

# ###############################################
# # Production Image
# ###############################################
FROM python:3.11-slim AS production

ENV POETRY_VERSION=1.8.2  \
    POETRY_HOME="/etc/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/home/k8s" \
    VENV_PATH="/home/k8s/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH:$PYSETUP_PATH/.venv/bin"

WORKDIR $PYSETUP_PATH

COPY --from=builder /home/k8s/.venv /home/k8s/.venv

COPY --from=builder $PYSETUP_PATH/src ./src
COPY --from=builder $PYSETUP_PATH/README.md .

# Mount the config.json file to the container
VOLUME ./config.json

# Run app as non root and expost it to port 5000
USER 999
RUN make run
