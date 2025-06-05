# First, build the application in the `/app` directory.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter across both
# images.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

ARG PACKAGE

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --group ${PACKAGE}

COPY src/${PACKAGE} ${PACKAGE}
COPY src/shared shared

COPY .python-version .python-version
COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group ${PACKAGE} 

# Then, use a final image without uv.
# It is important to use the image that matches the builder, as the path to the Python
# executable must be the same, e.g., using `python:3.11-slim-bookworm` will fail.
FROM python:3.13-slim-bookworm

WORKDIR /app

ARG PACKAGE

# Copy the application from the builder.
COPY --from=builder --chown=app:app /app/${PACKAGE} ${PACKAGE}
COPY --from=builder --chown=app:app /app/shared shared

COPY --from=builder --chown=app:app /app/.venv .venv

# Place executables in the environment at the front of the path.
ENV PATH=".venv/bin:$PATH"

# Pass the command at runtime with helm.
