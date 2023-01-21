from rich.live import Live
from rich.align import Align
from rich.panel import Panel
from rich.console import Console
from rich.layout import Layout
from rich.syntax import Syntax
from threading import Thread, main_thread
from time import sleep
from client_state import ClientState, ClientStateReader, StateEnum
from bs4 import BeautifulSoup
import base64
import binascii
import math
import textwrap


COLOR_LIST = [
    'yellow',
    'bright_green',
    'bright_white',
    'magenta',
]


class RichOutput(Thread):

    def __init__(self, client_state: ClientState):
        super().__init__(daemon=True)

        self._state_reader = ClientStateReader(client_state=client_state)
        self._console = Console()
        self._update_per_second = 10
        self._sleep_seconds = 1 / self._update_per_second

        self._update_method = None
        self._layout = self.initialize_layout()
        self.update_layout()

        self._scroll_seconds = 0.25
        self._scroll_seconds_counter = 0
        self._raw_scroller_line_index = 0
        self._data_scroller_line_index = 0

        self.start()

    def run(self) -> None:
        with Live(self._layout) as live:
            while True:
                sleep(self._sleep_seconds)

                self._scroll_seconds_counter += self._sleep_seconds
                if self._scroll_seconds_counter > self._scroll_seconds:
                    self._raw_scroller_line_index += 1
                    self._data_scroller_line_index += 1
                    self._scroll_seconds_counter = 0

                self.update_layout()
                # if not main_thread().is_alive() and self._data_scroller_line_index == 0:
                #     break

    def initialize_layout(self) -> Layout:
        layout = Layout()

        layout.split_column(
            Layout(name='upper', ratio=2),
            Layout(name='raw', ratio=3),
            Layout(name='data', ratio=3),
        )

        layout['upper'].split_row(
            Layout(name='traffic', ratio=3),
            Layout(name='state')
        )

        return layout

    def update_layout(self) -> Layout:
        client_id = self._state_reader.read_client_id()
        color = COLOR_LIST[(client_id - 1) % len(COLOR_LIST)] if client_id else 'red'

        traffic = self._state_reader.read_transmission_data()
        self._layout['upper']['traffic'].update(Panel(Align(traffic, 'right', vertical='bottom'), title="Remaining Request Data", style=f"cyan bold"))

        state = self._state_reader.read_state()
        self._layout['upper']['state'].update(Panel(Align(state.name, 'center', vertical='middle'), title="State", style=f"{color} bold"))

        match state:
            case StateEnum.RECEIVING_CURL_DATA:
                self._update_method = self._update_curl_data
            case StateEnum.RECEIVING_DATA:
                self._update_method = self._update_arbitrary_data
            case StateEnum.RECEIVING_SHELL:
                self._update_method = self._update_shell_data
            case StateEnum.REQUESTING_ID:
                self._update_method = self._update_request_id_data
            case StateEnum.SENDING_DATA | StateEnum.CURL:
                self._update_method = self._update_send_data
            case StateEnum.POLL:
                self._update_method = self._update_poll_data
            case _:
                if self._update_method is None:
                    self._update_method = self._update_empty_data

        self._update_method(color)

        return self._layout

    def _update_curl_data(self, color: str) -> None:
        self._set_receiving_data_ratio(self._layout)

        raw = self._state_reader.read_current_data()
        try:
            data = base64.b64decode(f"{raw}==".encode('utf-8')).decode('utf-8', errors='ignore')
        except binascii.Error:
            data = ""

        # ----- prettify raw data ----- #
        raw, raw_lines = self._breakup_singe_line_data(raw, ratio=1, full_ratio=1)

        panel_height = self._calc_panel_height('raw')
        if raw_lines <= panel_height:
            self._raw_scroller_line_index = 0
        else:
            raw = self._scroll_data(raw, self._raw_scroller_line_index)
            self._raw_scroller_line_index = self._raw_scroller_line_index % (raw_lines - panel_height)

        # ----- prettify decoded data ----- #
        data = BeautifulSoup(data, 'html.parser').prettify()

        data_lines = len(data.split('\n'))
        panel_height = self._calc_panel_height('data')
        if data_lines <= panel_height:
            self._data_scroller_line_index = 0
        else:
            self._data_scroller_line_index = self._data_scroller_line_index % (data_lines - panel_height +2)

        self._layout['raw'].update(Panel(Align(raw, 'left', vertical='top'), title="Raw Data", style=f"{color} bold"))
        self._layout['data'].update(Panel(Syntax(data, 'html', line_numbers=True, line_range=(self._data_scroller_line_index, None), word_wrap=True), title="Decoded Data", style=f"{color} bold"))

    def _update_shell_data(self, color: str) -> None:
        self._set_receiving_data_ratio(self._layout)

        raw = self._state_reader.read_command()
        try:
            data = base64.b64decode(raw.encode('utf-8')).decode('utf-8')
        except binascii.Error:
            data = ""

        self._layout['raw'].update(Panel(Align(raw, 'left', vertical='top'), title="Raw Data", style=f"{color} bold"))
        self._layout['data'].update(Panel(Syntax(data, 'shell'), title="Decoded Data", style=f"{color} bold"))

    def _update_request_id_data(self, color: str):
        self._set_receiving_data_ratio(self._layout)

        raw = self._state_reader.read_latest_response()
        try:
            data = raw[raw.rindex('.') + 1:]
        except IndexError:
            data = ""

        self._update_centered_data(raw, data, color)

    def _update_send_data(self, color: str):
        self._set_sending_data_ratio(self._layout)
        raw = data = self._state_reader.read_latest_response()
        self._update_centered_data(raw, data, color)

    def _update_poll_data(self, color: str):
        self._set_receiving_data_ratio(self._layout)

        raw = data = self._state_reader.read_latest_response()
        self._update_centered_data(raw, data, color)

    def _update_centered_data(self, raw: str, data: str, color: str) -> None:
        self._layout['raw'].update(Panel(Align(raw, 'center', vertical='middle'), title="Raw Data", style=f"{color} bold"))
        self._layout['data'].update(Panel(Align(data, 'center', vertical='middle'), title="Decoded Data", style=f"{color} bold"))

    def _update_arbitrary_data(self, color: str) -> None:
        self._set_receiving_data_ratio(self._layout)

        raw = self._state_reader.read_current_data()
        try:
            data = base64.b64decode(raw.encode('utf-8')).decode('utf-8')
        except binascii.Error:
            data = ""

        self._layout['raw'].update(Panel(Align(raw, 'left', vertical='top'), title="Raw Data", style=f"{color} bold"))
        self._layout['data'].update(Panel(data, title="Decoded Data", style=f"{color} bold"))

    def _update_empty_data(self, color: str) -> None:
        self._set_receiving_data_ratio(self._layout)

        self._layout['raw'].update(Panel("", title="Raw Data", style=f"{color} bold"))
        self._layout['data'].update(Panel("", title="Decoded Data", style=f"{color} bold"))

    def _set_receiving_data_ratio(self, layout: Layout):
        layout['upper'].ratio = 2
        layout['raw'].ratio = 3
        layout['data'].ratio = 3

    def _set_sending_data_ratio(self, layout: Layout):
        layout['upper'].ratio = 3
        layout['raw'].ratio = 1
        layout['data'].ratio = 1

    def _calc_panel_height(self, layout_key: str) -> int:
        full_ratio = self._layout['upper'].ratio + self._layout['raw'].ratio + self._layout['data'].ratio
        ratio = self._layout[layout_key].ratio
        return math.floor(self._console.height * (ratio / full_ratio) - 2)

    def _breakup_singe_line_data(self, data: str, ratio: int, full_ratio: int) -> tuple[str, int]:
        width = math.floor(self._console.width * (ratio / full_ratio)) - 4  # panel box
        wrapped = textwrap.wrap(data, width)
        return "\n".join(wrapped), len(wrapped)

    def _scroll_data(self, data: str, index: int) -> str:
        list_data = data.split('\n')
        # remove empty last newline
        if data and not list_data[-1]:
            list_data = list_data[:-1]
        scrolled_data = list_data[index:]

        return '\n'.join(scrolled_data)
