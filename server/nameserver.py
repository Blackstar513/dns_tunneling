import socket
import dns.message
import dns.flags
import dns.query


def decode_request(request: bytes) -> dns.message.Message:
    message = dns.message.from_wire(request)

    return message


def build_response(request: bytes) -> bytes:
    decoded_request = decode_request(request)

    response = dns.message.make_response(decoded_request, recursion_available=False)

    return response.to_wire()


def main():
    port = 53
    ip = '127.0.0.1'

    # AF_INET = ipv4, SOCK_DGRAM = datagram (udp)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))

    while True:
        message, time, sender_addr = dns.query.receive_udp(sock)
        dns.query.send_udp(sock, dns.message.make_response(message, recursion_available=False), destination=sender_addr)


if __name__ == '__main__':
    main()
