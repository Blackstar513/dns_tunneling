FROM python:3-alpine

WORKDIR /usr/src/server

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "-u", "./nameserver.py" ]