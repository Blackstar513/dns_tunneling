FROM python:3-alpine

WORKDIR /usr/src/server

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "/bin/sh", "entrypoint.sh" ]