# Static firewall rules:
# Only allow forwarding of udp packages on port 53 (=DNS)
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth1 -o eth0 -p udp --dport 53 -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -j DROP

# configuring fail2ban
cp fail2ban/filter.d/dns.conf /etc/fail2ban/filter.d
cp fail2ban/jail.d/dns.conf /etc/fail2ban/jail.d
rm /etc/fail2ban/jail.d/alpine-ssh.conf

# fail2ban reads this config file that will be written to by 
# dns_traffic_monitor.py
# It needs to exist at the start of fai2ban
touch ./dns_traffic_monitor.log

fail2ban-server -b

python -u ./dns_traffic_monitor.py