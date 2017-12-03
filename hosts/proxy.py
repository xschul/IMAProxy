import socket
import sys

# Create a TCP/IP socket
sock_user = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket with the user
user_address = ('', 1030)
print ('starting up on %s port %s' % user_address)
sock_user.bind(user_address)

# Connect the socket to the port where the server is listening
server_address = ('40.97.41.114', 993)

# Listen for incoming connections
sock_user.listen(1)

while True:
    # Wait for a connection
    print ('waiting for a connection')
    connection, client_address = sock_user.accept()

    try:
        print ('connection from', client_address)

        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(128)
            print ('received data from user' + data)
            if data:
                print ('connecting to %s port %s' % server_address)
                sock_server.connect(server_address)
                sock_server.sendall(data)
            else:
                print ('no more data from', client_address)
                break
            	
    finally:
        # Clean up the connection
        connection.close()
