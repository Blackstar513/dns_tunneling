FROM python:3-alpine

RUN apk add curl bind-tools

WORKDIR /usr/src/client

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "/bin/sh", "entrypoint.sh" ]