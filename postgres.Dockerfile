# TODO: look into splitting this into a build image and a runtime image to reduce the size of the runtime image
FROM postgres:17-alpine

ENV PGUSER=postgres

RUN apk --no-cache add python3 pipx make gcc musl-dev clang19 llvm

# INSTALL: pgvector
# docs: https://github.com/pgvector/pgvector?tab=readme-ov-file#pgvector
RUN pipx run pgxnclient install vector

# INSTALL: pgmq
# docs: https://github.com/tembo-io/pgmq?tab=readme-ov-file#postgres-message-queue-pgmq
RUN pipx run pgxnclient install pgmq

# Enable Container Healthcheck
HEALTHCHECK --interval=30s --timeout=60s --retries=5 --start-period=80s \
  CMD pg_isready -d db_prod || exit 1
