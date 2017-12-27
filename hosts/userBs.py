import socket, ssl

HOST, PORT, CERT = '', 1030, 'cert.pem'

def handle(conn):
  print('HANDLE')
  print(conn.recv())
  conn.write(b'OK IMAP4rev1')

def main():
  sock = socket.socket()
  sock.bind((HOST, PORT))
  sock.listen(5)
  context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

  context.set_ciphers('EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')
  while True:
    conn = None
    ssock, addr = sock.accept()
    try:
      conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
      handle(conn)
    except ssl.SSLError as e:
      print(e)
    finally:
      if conn:
        conn.close()
        
if __name__ == '__main__':
  main()