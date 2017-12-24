import socket
import sys

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('172.16.0.100', 993)
print('connecting to,s port,s', server_address)
sock.connect(server_address)

try:
    # Send data
    message = b'This is the message.  It will be repeated.'
    print('sending ', message)
    sock.sendall(message)

    # Look for the response
    amount_received = 0
    amount_expected = len(message)
    
    while amount_received < amount_expected:
        data = sock.recv(16)
        amount_received += len(data)
        print('received ', data)

finally:
    print('closing socket')
    sock.close()