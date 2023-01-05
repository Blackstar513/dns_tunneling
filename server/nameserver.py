import socket
import dns.message
import dns.flags
import dns.query
import dns.rrset
import base64


def decode_request(request: dns.message.Message) -> dict[str, any]:
    # decode subdomains
    subdomains = request.question[0].name.labels[:-3]     # instead of question .section[0] can be used
    d_subdomains = []

    for sub in subdomains:
        d_subdomains.append(base64.b32decode(sub).decode('utf-8'))

    return {'subdomains': d_subdomains,
            'transaction_id': request.id}


def analyze_subdomain(subdomains: list[str]) -> dict[str, any]:

    return {'command': subdomains[0],
            'data': []}


def build_response_data(analyzed_request: dict[str, any]) -> str:
    if analyzed_request['command'] == 'ping':
        return 'pong'
    return 'no-pong'


def build_response(request: dns.message.Message) -> dns.message.Message:
    # - request - #
    # -- decode relevant request parameters -- #
    decoded_request = decode_request(request)

    # -- analyze request -- #
    analyzed_request = analyze_subdomain(decoded_request['subdomains'])

    # - response - #
    # -- build base response -- #
    response = dns.message.make_response(request, recursion_available=False)

    # -- build relevant response data -- #
    response_data = build_response_data(analyzed_request)
    # -- encode response data -- #
    e_response_data = base64.b64encode(response_data.encode('utf-8')).decode('utf-8')
    # -- build full response -- #

    return response


def main():
    port = 53
    ip = '127.0.0.1'

    # AF_INET = ipv4, SOCK_DGRAM = datagram (udp)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))

    while True:
        message, time, sender_addr = dns.query.receive_udp(sock)
        response = build_response(message)
        dns.query.send_udp(sock, response, destination=sender_addr)


if __name__ == '__main__':
    main()
