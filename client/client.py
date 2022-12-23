import socket
import dns.message
import dns.flags
import dns.query
import dns.name
import dns.rdatatype
import dns.resolver


def main():
    name_server = '127.0.0.1'
    ADDITIONAL_RDCLASS = 65535
    domain = dns.name.from_text('google.com')

    request = dns.message.make_query(domain, dns.rdatatype.ANY)
    request.flags |= dns.flags.AD
    request.rdtype = dns.rdatatype.A
    request.rdclass = dns.rdataclass.IN
    response = dns.query.udp(request, name_server)

    print(f"{response}")


if __name__ == '__main__':
    main()
