import socket, ssl

HOST, PORT, CERT = '172.16.0.100', 993, 'cert.pem'

def handle(conn):
    print('handle connection')
    print(conn.recv().decode())

def main():
    sock = socket.socket(socket.AF_INET)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

    conn = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_NONE)
    try:
        conn.connect((HOST, PORT))
        handle(conn)
    finally:
        conn.close()

if __name__ == '__main__':
    main()