FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-editable

# Copy the project into the intermediate image
ADD grug /app/grug
ADD alembic /app/alembic
ADD alembic.ini /app/almebic.ini

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable


FROM python:3.12-slim

WORKDIR /app

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:${PATH}"

# Run the application
CMD ["python", "-m", "grug"]

# TODO: build a healthcheck into the application
# HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
#  CMD poetry run python grug health || exit 1
