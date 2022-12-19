import socket
import dns.message
import dns.flags
import dns.query


def decode_request(request: dns.message.Message) -> dict:
    return {}


def build_response(request: dns.message.Message) -> dns.message.Message:
    decoded_request = decode_request(request)

    response = dns.message.make_response(request, recursion_available=False)

    return response


def main():
    port = 53
    ip = '127.0.0.1'

    # AF_INET = ipv4, SOCK_DGRAM = datagram (udp)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))

    while True:
        message, time, sender_addr = dns.query.receive_udp(sock)
        dns.query.send_udp(sock, build_response(message), destination=sender_addr)


if __name__ == '__main__':
    main()
