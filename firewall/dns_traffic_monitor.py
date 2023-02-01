import subprocess
import re
import datetime
import click
import io
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

rootLogger = logging.getLogger()
fileHandler = logging.FileHandler("dns_traffic_monitor.log")
rootLogger.addHandler(fileHandler)

tcpdump_regex = re.compile('^(\d{2}:\d{2}:\d{2}.\d{6}) IP (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}).\d+ > (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}).\d+: .* ((A|TXT)\??) (.*) \(\d+\)$')

lookup_history = dict()

@click.command()
@click.option("--interface", default="eth1", help="Ethernet interface that should be monitored")
def monitor(interface):
    """Monitors UDP traffic on the defined interface for potential DNS tunneling activity. Logs suspicious behavior."""
    process = subprocess.Popen(['tcpdump', 'udp', '-ni', interface, '--immediate-mode', '-l'], stdout=subprocess.PIPE)
    for message in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        match = tcpdump_regex.match(message)
        if match:
            time = datetime.time.fromisoformat(match.group(1))
            from_ip = match.group(2)
            to_ip = match.group(3)
            request_type = match.group(4)
            payload = match.group(6)

            client_ip = from_ip if request_type.endswith("?") else to_ip

            long_payload_dected = True if len(payload) > 200 else False
            shortened_message = f'{payload[0:40]}{"…" if len(payload) > 40 else ""}'.ljust(41)

            rootLogger.info(f'{str(time)[:12]} {client_ip} {request_type.ljust(4)} {shortened_message}: {"🛑 " if long_payload_dected else "✅"}')



if __name__ == '__main__':
    monitor()