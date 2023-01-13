FROM alpine:3

RUN apk add dnsmasq iptables tcpdump

COPY . .

ENTRYPOINT [ "/bin/sh", "entrypoint.sh" ]