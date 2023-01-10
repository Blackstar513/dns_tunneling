import dns.message
import dns.flags
import dns.query
import dns.name
import dns.rdatatype
import dns.resolver
import base64


def encoded_subdomain(subdomains: list[str]):
    e_subdomains = []

    for sub in subdomains:
        e_sub = base64.b32encode(sub.encode('utf-8')).decode('utf-8')
        if len(e_sub) > 63:
            raise ValueError(f"Subdomain {sub} too long to fit in single subdomain when encoded")
        e_subdomains.append(e_sub)

    return '.'.join(e_subdomains)


def encoded_domain() -> str:
    # subdomain = ['MY', 'Test', 'path']
    subdomain = ['ping']
    domain = 'google.com'
    e_domain = f"{encoded_subdomain(subdomain)}.{domain}"

    if len(e_domain) > 255:
        raise ValueError(f"Domain {'.'.join(subdomain)}.{domain} to long when encoded")

    return e_domain


def main():
    name_server = '127.0.0.1'
    domain = dns.name.from_text(encoded_domain())

    request = dns.message.make_query(domain, dns.rdatatype.TXT)
    response = dns.query.udp(request, name_server)

    print(f"{response}")


if __name__ == '__main__':
    main()
