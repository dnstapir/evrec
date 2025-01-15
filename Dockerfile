FROM python:3.13 AS builder
RUN pip3 install poetry
WORKDIR /src
ADD . /src
RUN poetry build

FROM python:3.13
WORKDIR /tmp
COPY --from=builder /src/dist/*.whl .
RUN pip3 install *.whl && rm *.whl
RUN useradd -u 1000 -m -s /sbin/nologin evrec
USER evrec
ENTRYPOINT ["evrec_server", "--log-json"]
