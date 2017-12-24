import ssl
from imaplib import IMAP4, IMAP4_SSL, IMAP4_PORT, IMAP4_SSL_PORT
from socks import sockssocket, PROXY_TYPE_SOCKS4, PROXY_TYPE_SOCKS5, PROXY_TYPE_HTTP

class SocksIMAP4SSL(IMAP4_SSL):
    def open(self, host, port=IMAP4_SSL_PORT):
        self.host = host
        self.port = port
        #actual privoxy default setting, but as said, you may want to parameterize it
        self.sock = create_connection((host, port), PROXY_TYPE_HTTP, "127.0.0.1", 8118)
        self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile)
        self.file = self.sslobj.makefile('rb')

if __name__ == '__main__':
    sock = SocksIMAP4SSL()
    sock.open()