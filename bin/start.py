import argparse

from imap-proxy.proxy import IMAP_Proxy

if __name__ == '__main__':
    # Parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certfile', help='Enable SSL/TLS connection over port 993 (by default) with the certfile given. '
        + 'Without this argument, the connection will not use SSL/TLS over port 143 (by default)')
    parser.add_argument('-p', '--port', type=int, help='Listen on the given port')
    parser.add_argument('-n', '--nclient', type=int, help='Maximum number of client supported by the proxy')
    parser.add_argument('-v', '--verbose', help='Echo IMAP payload', action='store_true')
    parser.add_argument('-6', '--ipv6', help='Enable IPv6 connection (the proxy should have an IPv6 address)', action='store_true')
    args = parser.parse_args()

    # Start proxy
    print("Starting proxy")
    IMAP_Proxy(port=args.port, certfile=args.certfile, max_client=args.nclient, ipv6=args.ipv6, verbose=args.verbose)