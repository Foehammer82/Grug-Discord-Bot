# TODO: look into splitting this into a build image and a runtime image to reduce the size of the runtime image
FROM postgres:17-alpine

ENV PGUSER=postgres

RUN apk --no-cache add python3 pipx make gcc musl-dev clang19 llvm

# docs: https://github.com/pgvector/pgvector?tab=readme-ov-file#pgvector
RUN pipx run pgxnclient install vector

# docs: https://github.com/tembo-io/pgmq?tab=readme-ov-file#postgres-message-queue-pgmq
RUN pipx run pgxnclient install pgmq
