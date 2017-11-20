import socket
import sys
import src.imapcommands as Command

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('10.0.0.1', 10000)
print ('connecting to %s port %s' % server_address)
sock.connect(server_address)

try:
    
    # Send data
    print ('sending')
    sock.sendall(Commande)

    # Look for the response
    amount_received = 0
    amount_expected = len(message)
    
    while amount_received < amount_expected:
        data = sock.recv(16)
        amount_received += len(data)
        print ('received "%s"' % data)

finally:
    print ('closing socket')
    sock.close()