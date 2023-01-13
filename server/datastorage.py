from dataclasses import dataclass
import base64
import binascii


@dataclass(frozen=True)
class DataStorage:
    head: str
    body: str


class ClientStorage:

    def __init__(self, client_id: int):
        self.__client_id = client_id
        self._storage = []

        self._current_head = []
        self._current_body = []

    def _store_current(self):
        head = b"".join(self._current_head)
        body = b"".join(self._current_body)

        try:
            head = base64.b32decode(head).decode('utf-8')
        except binascii.Error:
            pass
        try:
            body = base64.b32decode(body).decode('utf-8')
        except binascii.Error:
            pass

        self._storage.append(DataStorage(head, body))
        self._current_head = []
        self._current_body = []

    def store_head(self, head: str):
        self._current_head.append(head)

    def store_body(self, body: str, done: bool):
        self._current_body.append(body)

        if done:
            self._store_current()

    @property
    def client_id(self):
        return self.__client_id

    def print_latest_storage(self):
        if self._storage:
            print(self._storage[-1])
        else:
            print("STORAGE IS EMPTY!")
