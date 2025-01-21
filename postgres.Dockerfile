# TODO: look into splitting this into a build image and a runtime image to reduce the size of the runtime image
FROM postgres:17-alpine

ENV PGUSER=postgres

RUN apk --no-cache add python3 pipx make gcc musl-dev clang19 llvm

RUN pipx run pgxnclient install vector

# TODO: planned feature to utilze postgres as a message queue to offload data pipelining from within python
#   - check it out: https://github.com/tembo-io/pgmq/tree/main/tembo-pgmq-python
#RUN pipx run pgxnclient install pgmq
