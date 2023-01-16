import socket
from rich.prompt import Prompt


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(('127.0.0.1', 5000))

        while True:
            client_id = Prompt.ask("Client id")
            command = Prompt.ask("Command")

            sock.sendall(f"{client_id} {command}\r\n".encode())


if __name__ == '__main__':
    main()
