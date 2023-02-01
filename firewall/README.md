# Firewall

Custom firewall configuration that is used in the demo to show how DNS tunneling attacks can be detected and blocked.

uses `iptables` to configure firewall rules, `tcpdump` to monitor DNS traffic and `fail2ban` to dynamically block suspicious clients.

## How to use

### DNS traffic monitor

The traffic monitoring starts automatically at the start of the Docker container.

It could be manually started by executing the provided python script:

```shell
python ./dns_traffic_monitor.py
```

This will start monitoring the FORWARDED DNS traffic on port 53 and report any suspicious behavior. The results are written to the logfile `dns_traffic_monitor.log`.

### fail2ban

Fail2ban has to be started manually, to enable the dynamic firewall adjustment:

```shell
./start_fail2ban.sh
```

This will start `fail2ban` in the background and launch a `watch` session that always outputs the latest `fail2ban` status until exited.

A client will be blocked for 30s when at least 8 suspicious messages have been reported in the last 10s.

Those numbers are intentionally chosen low to allow easy demonstration of the technology. In practice it should be configured with more realistic thresholds and timeouts.