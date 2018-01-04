import sys
import socket, ssl, imaplib
import base64
from multiprocessing.dummy import Pool as ThreadPool 

# Global variables
HOST, PORT, CERT = '', 993, 'cert.pem'
CRLF = b'\r\n'

# Capabilities of the proxy
capabilities = ( 
    'IMAP4',
    'IMAP4rev1',
    'AUTH=PLAIN',
    #'AUTH=XOAUTH2', 
    'SASL-IR',
    #'IDLE',
    'UIDPLUS',
    'MOVE',
    'ID',
    'UNSELECT', 
    'CHILDREN', 
    'NAMESPACE',
    'LITERAL'
    )

# Verbose variables
RECV_CL = "[-->]:"
SEND_CL = "[<--]:"
RECV_SR = "  [<--]:"
SEND_SR = "  [-->]:"
INFO = "[INFO]:"
ERROR= "[ERROR]:"
verbose = False

# Colors
RED = '\033[91m'
GREENBOLD = '\033[92m\033[1m'
ENDC = '\033[0m'

def process(conn_client):
    def get_attr(request):
        lst = request.decode().split()
        return ([s.replace('\r\n', '') for s in lst])

    def connect_to_client():

        def ok_command(tag, command):
            ok_command = tag + ' OK ' + command + ' completed.' + '\r\n'
            return ok_command.encode()

        def get_login(request, auth_type):
            #
            if auth_type == "LOGIN":
                username = get_attr(request)[2]
                password = get_attr(request)[3]

            elif auth_type == "PLAIN":
                decoded_req = base64.b64decode(request).split(b'\x00')
                username = decoded_req[1].decode()
                password = decoded_req[2].decode()

            elif auth_type == "XOAUTH2":
                pass 

            if username.startswith('"') and username.endswith('"'):
                username = username[1:-1]

            if password.startswith('"') and password.endswith('"'):
                password = password[1:-1]

            return username, password

        # Start service
        service_ready = ('* OK Service Ready.').encode() + CRLF
        conn_client.sendall(service_ready)
        print(SEND_CL, service_ready)

        while True: 
            request = conn_client.recv()
            print(RECV_CL, request)

            tag = get_attr(request)[0]
            command = get_attr(request)[1].upper()

            if command == 'CAPABILITY':
                capability_command = '* CAPABILITY ' + ' '.join(cap for cap in capabilities) + ' +' 
                print(capability_command)

                conn_client.sendall(capability_command.encode()+ CRLF)
                conn_client.sendall(ok_command(tag, command))

            elif command == 'AUTHENTICATE':
                auth_type = get_attr(request)[2]
                conn_client.sendall(b'+\r\n')
                request = conn_client.recv()
                conn_client.sendall(ok_command(tag, command))
                return get_login(request, auth_type)

            elif command == 'LOGIN':
                conn_client.sendall(ok_command(tag, command))
                return get_login(request, command)

            else:
                print(RED, ERROR, 'Unknown command for request', request, ENDC)
                return

    def connect_to_server(username, password, hostname):
        connection = imaplib.IMAP4_SSL(hostname)
        connection.login(username, password)

        if verbose:
            print(INFO, 'Logged in')

        return connection

    def serve(conn_client, conn_server):
        def convert_request(request, tag):
            attrs = get_attr(request)
            received_tag = attrs[0]
            attrs[0] = tag
            new_request = ' '.join(str(attr) for attr in attrs)

            return new_request.encode()+CRLF, received_tag

        def transmit(request_client):
            print(RECV_CL, request_client)
            tag_server = conn_server._new_tag().decode()
            request_server, tag_client = convert_request(request_client, tag_server)


            conn_server.send(request_server)
            print(SEND_SR, request_server)

            while True:
                # Listen response from the server
                print("Wait for server")
                response_server = conn_server._get_line()+CRLF
                print("Received from server")
                attr_response = get_attr(response_server)

                tag = None if len(attr_response) < 1 else attr_response[0]
                command = None if len(attr_response) <= 1 else attr_response[1]

                if command == "BYE":
                    # Client stopped connection
                    conn_client.send(response_server)
                    print(SEND_CL, response_server)
                    return

                if command == "BAD":
                    # Bad command
                    print(RED, ERROR, "Bad command:", response_server, ENDC)

                if tag_server == tag:
                    # Last response to transmit from the initial request
                    response_server, server_tag = convert_request(response_server, tag_client)
                    conn_client.send(response_server)
                    print(SEND_CL, response_server)
                    break

                else:
                    # Transmit answer from the server to the client
                    conn_client.send(response_server)

        def wait_request():
            # Listen requests from the user
            while True:
                print("Wait for client")
                request_client = conn_client.recv()
                print("Received from client")
                
                if request_client:
                    transmit(request_client)
                            
                else:
                    break

        wait_request()

    # Get the credentials of the client
    username, password = connect_to_client()
    hostname = 'imap-mail.outlook.com' # TODO: get the hostname
    
    if username and password:
        # Connect with the real server
        conn_server = connect_to_server(username, password, hostname)
        # Transmit data between client and server
        serve(conn_client, conn_server)


def connection(ssock):
    conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
    process(conn)
    conn.close()

def listening():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))

    sock.listen(5)
    pool = ThreadPool(5)

    while True:
        try:
            conn = None
            ssock, addr = sock.accept()

            if verbose:
                print(GREENBOLD, INFO, "New connection from", addr, ENDC)

            pool.map(connection, (ssock,))
            if verbose:
                print(GREENBOLD, INFO, "No more data from", addr, ENDC)

        except KeyboardInterrupt:
            if sock:
                sock.close()

            if verbose:
                print(GREENBOLD, INFO,"Socket closed", ENDC)
            break

        '''except Exception as e:
            sock.close()
            print(RED, ERROR, e, ENDC)
            break'''

    if sock:
        sock.close()

if __name__ == '__main__':
    verbose = True
    listening()