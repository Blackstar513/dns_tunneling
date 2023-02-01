#!/bin/bash

# This script starts a tmux session and arranges a collection of useful input and output panes that help
# to interact with the system and to understand what is going on.

# docker container names as they are listed in `docker ps`.
export CLIENT_NAME=dns_tunneling-client
export SERVER_NAME=dns_tunneling-server
export FIREWALL_NAME=dns_tunneling-firewall
export DNS_SERVER_NAME=dns_tunneling-dns_server


tmux new-session -d -s dns_tunneling 'docker container logs --follow $(docker ps -aqf "name=$FIREWALL_NAME")'
tmux rename-window 'DNS Tunneling'
tmux select-window -t dns_tunneling:0
tmux set -g pane-border-status top
tmux select-pane -t 0 -T "Firewall (logs)"

tmux split-window -v -t 0 'docker exec -it $(docker ps -aqf "name=$SERVER_NAME") python -u nameserver.py'
tmux select-pane -t 1 -T "Server (logs)"
tmux split-window -v -t 0 'docker container logs --follow $(docker ps -aqf "name=$DNS_SERVER_NAME")'
tmux select-pane -t 1 -T "DNS-Server (logs)"

tmux split-window -hbf -t 0 'docker exec -it $(docker ps -aqf "name=$CLIENT_NAME") sh'
tmux select-pane -t 0 -T "Client"
tmux split-window -v -t 0 'docker exec -it $(docker ps -aqf "name=$FIREWALL_NAME") sh'
tmux select-pane -t 1 -T "Firewall"
tmux split-window -v -t 1 'docker exec -it $(docker ps -aqf "name=$SERVER_NAME") sh -c "sleep 1 && python cli_commander.py"'
tmux select-pane -t 2 -T "Server"

tmux resize-pane -L -t 0 9
tmux resize-pane -D -t 0 2
tmux resize-pane -D -t 2 3
tmux resize-pane -U -t 4 5


tmux select-pane -t 0
tmux -2 attach-session -t dns_tunneling
