import socket
import dns.message
import dns.flags
import dns.query
import dns.rrset
import dns.rdata
from enum import Enum
from server_state import ServerState, ServerStateResponseHandler
from cli import CommandLineInterface
from command_socket import CommandSocket


class OldTransactionIDException(ValueError):
    pass


class CommandsEnum(Enum):
    UNKNOWN = 'unknown'
    REQUEST_ID = 'requestid'
    DATA = 'data'
    DATA_HEAD = 'head'
    DATA_BODY = 'body'
    POLL = 'poll'
    CONTINUE = 'continue'
    CURL = 'curl'


class Nameserver:

    def __init__(self, nameserver_ip: str = None):
        self.server_state = ServerState()
        self.response_handler = ServerStateResponseHandler(self.server_state)

        self.command_socket = CommandSocket(server_state=self.server_state)
        self.cli = CommandLineInterface(server_state=self.server_state)
        self.cli.start()

        port = 53
        ip = '127.0.0.1' if nameserver_ip is None else nameserver_ip

        # AF_INET = ipv4, SOCK_DGRAM = datagram (udp)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))

        while True:
            message, time, sender_addr = dns.query.receive_udp(sock)
            try:
                response = self.build_response(message)
                dns.query.send_udp(sock, response, destination=sender_addr)
            except OldTransactionIDException:
                pass

    @staticmethod
    def unpack_request(request: dns.message.Message) -> dict[str, any]:
        request_name = request.question[0].name

        # decode subdomains
        subdomains = list(request_name.labels[:-3])     # instead of question .section[0] can be used
        d_subdomains = []

        # filter zero terminator
        zero_terminator = subdomains[0] == b'0'
        if zero_terminator:
            subdomains = subdomains[1:]

        # reverse subdomains for easier analysis
        subdomains.reverse()

        # filter client id
        try:
            d_subdomains.append(int(subdomains[0]))
            subdomains = subdomains[1:]
        except ValueError:
            pass

        for sub in subdomains:
            if sub in [e.value.encode('utf-8') for e in CommandsEnum]:
                d_subdomains.append(sub.decode('utf-8'))
            else:
                d_subdomains.append(sub)

        return {'subdomains': d_subdomains,
                'transaction_id': request.id,
                'request_type': dns.rdatatype.to_text(request.question[0].rdtype),
                'request_name': request_name,
                'request_url': b".".join(request_name.labels).decode('utf-8'),
                'zero_terminator': zero_terminator}

    @staticmethod
    def analyze_subdomain(subdomains: list[str], zero_terminator: bool) -> dict[str, any]:

        match subdomains:
            case ['requestid']:
                return {'command': CommandsEnum.REQUEST_ID}
            case [client_id, 'data', 'head', *data]:
                return {'command': CommandsEnum.DATA_HEAD,
                        'client_id': client_id,
                        'data': b"".join(data),
                        'done': zero_terminator}
            case [client_id, 'data', 'body', *data]:
                return {'command': CommandsEnum.DATA_BODY,
                        'client_id': client_id,
                        'data': b"".join(data),
                        'done': zero_terminator}
            case [client_id, 'poll']:
                return {'command': CommandsEnum.POLL,
                        'client_id': client_id}
            case [client_id, 'continue']:
                return {'command': CommandsEnum.CONTINUE,
                        'client_id': client_id}
            case [client_id, 'curl', *webpage]:
                return {'command': CommandsEnum.CURL,
                        'client_id': client_id,
                        'data': b"".join(webpage),
                        'done': zero_terminator}
            case _:
                return {'command': CommandsEnum.UNKNOWN}

    def build_a_response_data(self, analyzed_request: dict[str, any]) -> str:
        match analyzed_request:
            case {'command': CommandsEnum.REQUEST_ID}:
                return self.response_handler.request_id_response()
            case {'command': CommandsEnum.DATA_HEAD,
                  'client_id': client_id,
                  'data': data, 'done': done}:
                return self.response_handler.data_response(client_id=client_id, data=data, is_head=True, done=done)
            case {'command': CommandsEnum.DATA_BODY,
                  'client_id': client_id,
                  'data': data, 'done': done}:
                return self.response_handler.data_response(client_id=client_id, data=data, is_head=False, done=done)

    def build_txt_response_data(self, analyzed_request: dict[str, any]) -> str:
        match analyzed_request:
            case {'command': CommandsEnum.POLL,
                  'client_id': client_id}:
                return self.response_handler.poll_response(client_id=client_id)
            case {'command': CommandsEnum.CONTINUE,
                  'client_id': client_id}:
                return self.response_handler.continue_response(client_id=client_id)
            case {'command': CommandsEnum.CURL,
                  'client_id': client_id,
                  'data': webpage, 'done': done}:
                return self.response_handler.curl_response(client_id=client_id, webpage=webpage, done=done)

    def build_response_data(self, unpacked_request: dict[str, any], analyzed_request: dict[str, any]) -> str:
        if unpacked_request['request_type'] == dns.rdatatype.A.name:
            return self.build_a_response_data(analyzed_request)
        elif unpacked_request['request_type'] == dns.rdatatype.TXT.name:
            return self.build_txt_response_data(analyzed_request)

    def build_response(self, request: dns.message.Message) -> dns.message.Message:
        # - request - #
        # -- unpack relevant request parameters -- #
        unpacked_request = self.unpack_request(request)
        self.server_state.add_request(unpacked_request['request_url'])

        # -- check if request is already getting handled --#
        if not self.server_state.is_new_transaction(unpacked_request['transaction_id']):
            raise OldTransactionIDException

        # -- analyze request -- #
        analyzed_request = self.analyze_subdomain(unpacked_request['subdomains'], zero_terminator=unpacked_request['zero_terminator'])

        # - response - #
        # -- build base response -- #
        response = dns.message.make_response(request, recursion_available=False)

        # -- build relevant response data -- #
        response_data = self.build_response_data(unpacked_request, analyzed_request)
        self.server_state.add_response(response_data)

        # -- build full response -- #
        rdata = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.from_text(unpacked_request['request_type']),
                                    response_data, unpacked_request['request_name'], relativize=True)
        rrset = dns.rrset.from_rdata(unpacked_request['request_name'], 1, rdata)

        response.answer.append(rrset)

        return response


def main():
    dns_server = Nameserver()


if __name__ == '__main__':
    main()
