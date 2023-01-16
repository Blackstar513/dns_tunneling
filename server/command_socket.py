from threading import Thread
from server_state import ServerState, ServerStateCommandWriter
import socket


class CommandSocket(Thread):

    def __init__(self, server_state: ServerState) -> None:
        super().__init__(daemon=True)

        self._command_writer = ServerStateCommandWriter(server_state=server_state)
        self.start()

    def run(self):
        buffer = b''

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 5000))
            sock.listen(1)

            while True:
                conn, addr = sock.accept()
                with conn:
                    closed = False
                    while not closed:
                        while b'\r\n' not in buffer:
                            data = conn.recv(1024)
                            if not data:
                                closed = True
                                break

                            buffer += data

                        buffer = buffer.rstrip()
                        self.write_command(buffer.decode())
                        buffer = b''

    def write_command(self, command_msg: str) -> None:
        command_msg = command_msg.split()
        client_id = int(command_msg.pop(0))
        command = " ".join(command_msg)

        self._command_writer.write_command(client_id, command)
