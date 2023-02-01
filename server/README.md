# Server

Server that waits for DNS requests from the client.

## How to use

### Nameserver
The server can be used by executing the `nameserver.py`. To run it locally use the
command:
```shell
python3.10 nameserver.py --ip 127.0.0.1
```

### Command Writer
The command writer can be used to send command for the clients to the nameserver.
It can be executed by using the command:
```shell
python3.10 cli_commander.py
```
The nameserver needs to be executed first.