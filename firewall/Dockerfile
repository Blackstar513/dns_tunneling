FROM python:3-alpine

RUN apk add iptables tcpdump fail2ban

WORKDIR /usr/src/firewall

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "/bin/sh", "entrypoint.sh" ]