FROM alpine:3

RUN apk add iptables tcpdump

COPY . .

ENTRYPOINT [ "/bin/sh", "entrypoint.sh" ]