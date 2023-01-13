# set default gateway to firewall service
ip route replace default via $GATEWAY_IP dev eth0

# set dns to dns_server service
echo "nameserver $DNS_SERVER_IP" > /etc/resolv.conf

# keep container running
tail -f /dev/null 