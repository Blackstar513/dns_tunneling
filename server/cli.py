from server_state import ServerState, ServerStateReader
from threading import Thread
from time import sleep
from rich.live import Live
from rich.columns import Columns
from rich.align import Align
from rich.panel import Panel
from rich.console import Console
from rich.layout import Layout


COLOR_LIST = [
    'yellow',
    'bright_green',
    'bright_white',
    'magenta',
]


class CommandLineInterface(Thread):

    def __init__(self, server_state: ServerState) -> None:
        super().__init__(daemon=True)

        self._state_reader = ServerStateReader(server_state)
        self._console = Console()
        self._client_switch_seconds = 10
        self._client_switch_counter = 0
        self._update_per_second = 3
        self._sleep_seconds = 1 / self._update_per_second
        self._client_id = 0

        self._data_scroll_seconds = 2
        self._data_scroll_seconds_counter = 0
        self._data_scroller_line_index = 0

    def run(self) -> None:
        with Live(self.make_layout()) as live:
            while True:

                sleep(self._sleep_seconds)
                self._client_switch_counter += self._sleep_seconds
                self._data_scroll_seconds_counter += self._sleep_seconds

                if self._data_scroll_seconds_counter > self._data_scroll_seconds:
                    self._data_scroller_line_index += 1

                if self._client_switch_counter > self._client_switch_seconds:
                    self._update_client_id()
                    self._client_switch_counter = 0
                live.update(self.make_layout())

    def make_layout(self):
        layout = Layout()

        layout.split_column(
            Layout(name='upper'),
            Layout(name='lower')
        )

        layout['upper'].split_column(
            Layout(name='traffic'),
            Layout(name='status')
        )

        layout['upper']['traffic'].split_row(
            Layout(name='in'),
            Layout(name='out')
        )

        layout['lower'].split_row(
            Layout(name='data'),
            Layout(name='commands')
        )

        layout['lower']['data'].ratio = 2

        layout['upper']['traffic']['in'].update(Panel(Align(self._state_reader.get_latest_request(), 'center', vertical='middle'), title="Incoming Traffic", style="orange1 bold"))
        layout['upper']['traffic']['out'].update(Panel(Align(self._state_reader.get_latest_response(), 'center', vertical='middle'), title="Outgoing Traffic", style="cyan bold"))

        if self._client_id == 0:
            layout['upper']['status'].update(Panel(Align("NO CLIENT YET", 'center', vertical='middle'), title=f"Client Status", style="red bold"))
            layout['lower']['data'].update(Panel("NO CLIENT YET", title=f"Client Data", style="red bold"))
            layout['lower']['commands'].update(Panel("NO CLIENT YET",title=f"Client Commands", style="red bold"))

        else:
            color = COLOR_LIST[(self._client_id - 1) % len(COLOR_LIST)]

            data = self._state_reader.get_latest_client_data(self._client_id)
            head = data.head
            body = self._handle_special_header(head=head, body=data.body)
            layout['upper']['status'].update(Panel(Align(self._state_reader.get_client_status(self._client_id), 'center', vertical='middle'), title=f"Status Client {self._client_id}", style=f"{color} bold"))
            layout['lower']['data'].update(Panel(body, title=f"Data Client {self._client_id}: {head}", style=f"{color} bold"))
            layout['lower']['commands'].update(Panel(self._make_numbered_list(self._state_reader.get_next_x_client_commands(self._client_id, 5)), title=f"Client {self._client_id} Commands", style=f"{color} bold"))

        return layout

    def _handle_special_header(self, head: str, body: str) -> any:
        if head.startswith('ls') or head.startswith('ls '):
            return Columns(body.split('\n'), expand=True, equal=True, column_first=True)
        else:
            return self._scroll_data(body, infinite=True)

    def _scroll_data(self, data: str, infinite: bool = False) -> str:
        list_data = data.split('\n')
        scrolled_data = list_data[self._data_scroller_line_index:]

        if infinite:
            if data:
                scrolled_data += [f"[red]{'-'*10}LOOP{'-'*10}[/red]"]
            scrolled_data += list_data[:self._data_scroller_line_index]
            self._data_scroller_line_index = self._data_scroller_line_index % len(scrolled_data)
        else:
            self._data_scroller_line_index = self._data_scroller_line_index % len(list_data)

        return '\n'.join(scrolled_data)

    def _make_numbered_list(self, data: list[str]) -> str:
        markdown_list = []
        for i, item in enumerate(data):
            markdown_list.append(f"{i+1}. {item}")

        return "\n".join(markdown_list)

    def _update_client_id(self) -> None:
        n_clients = self._state_reader.get_number_of_clients()
        if n_clients:
            self._client_id = (self._client_id % n_clients) + 1
