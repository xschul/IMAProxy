import socket
import sys
import ssl

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# WRAP SOCKET
wrappedSocket = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1)

# Connect the socket to the port where the server is listening
server_address = ('172.16.0.100', 993)
print('connecting to,s port,s', server_address)
wrappedSocket.connect(server_address)

try:
    # Send data
    message = b'This is the message.  It will be repeated.'
    print('sending ', message)
    wrappedSocket.sendall(message)

    # Look for the response
    data = wrappedSocket.recv(16)
    amount_received += len(data)
    print('received ', data)

finally:
    print('closing socket')
    wrappedSocket.close()