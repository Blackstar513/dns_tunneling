# Client

Client that can send data over the DNS protocol to a server that speaks the same protocol.

## How to use

The client can be used by executing the `client.py` file. The `--help` option 
lists all possible commands and options. For options for a specific command 
```shell
python3.10 client.py <COMMAND> --help 
```
can be used. For all commands except for `auto` an id needs to be requested first.

### Automated client

To use a client that automatically polls commands from a locally running server 
every 15 seconds use:
```shell
python3.10 client.py --nameserver 127.0.0.1 --lag 1 --live auto --poll 15
```

### ID Request
```shell
python3.10 client.py --nameserver 127.0.0.1 id
```

### HTTP GET

To get results of a http get request of `google.com` use:
```shell
python3.10 client.py --id <CLIENT_ID> --nameserver 127.0.0.1 --lag 1 --live curl http://www.google.com
```
Be sure to include `http` and `www`.