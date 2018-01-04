import socket, ssl, imaplib, sys, struct

# Global variables
HOST, PORT, CERT = '', 993, 'cert.pem'
CRLF = b'\r\n'

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
        return ([s.replace('\r\n', '').replace('"', '') for s in lst])

    def connect_to_client():

        def ok_command(tag, command):
            ok_command = tag + ' OK ' + command + ' completed.' + '\r\n'
            return ok_command.encode()

        service_ready = ('* OK Service Ready').encode() + CRLF
        conn_client.sendall(service_ready)
        print(SEND_CL, service_ready)

        while True: 
            request = conn_client.recv()
            print(RECV_CL, request)

            tag = get_attr(request)[0]
            command = get_attr(request)[1]

            if command.upper() == 'CAPABILITY': # TODO: add IDLE + make request cleaner
                capability_command = b'* CAPABILITY IMAP4 IMAP4rev1 AUTH=PLAIN AUTH=XOAUTH2 SASL-IR UIDPLUS MOVE ID UNSELECT CHILDREN NAMESPACE LITERAL+\r\n'
                conn_client.sendall(capability_command)
                print(SEND_CL, capability_command)
                conn_client.sendall(ok_command(tag, command))
                print(SEND_CL, ok_command(tag, command))

            elif command.upper() == 'AUTHENTICATE':
                conn_client.sendall(b'+\r\n')
                print(SEND_CL, b'+\r\n')
                response = conn_client.recv()
                print(RECV_CL, response)
                conn_client.sendall(ok_command(tag, command))
                print(SEND_CL, ok_command(tag, command))

            elif command.upper() == 'LOGIN':
                username = get_attr(request)[2]
                password = get_attr(request)[3]
                hostname = 'imap-mail.outlook.com' # TODO: get the hostname
                conn_client.sendall(ok_command(tag, command))
                print(SEND_CL, ok_command(tag, command))

                return username, password, hostname

            elif command.upper() == 'LOGOUT':
                conn_client.sendall(ok_command(tag, command))

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
                response_server = conn_server._get_line()+CRLF
                attr_response = get_attr(response_server)
                print(RECV_SR, response_server)

                tag = None if len(attr_response) < 1 else attr_response[0]
                command = None if len(attr_response) <= 1 else attr_response[1]

                if command == "BYE":
                    # Client stopped connection
                    conn_client.send(response_server)
                    print(SEND_CL, response_server)
                    return

                if tag_server == tag:
                    # Last response to transmit from the initial request
                    response_server, server_tag = convert_request(response_server, tag_client)
                    conn_client.send(response_server)
                    print(SEND_CL, response_server)
                    break

                else:
                    # Transmit answer from the server to the client
                    conn_client.send(response_server)
                    print(SEND_CL, response_server)

        def wait_request():
            # Listen requests from the user
            while True:
                request_client = conn_client.recv()
                
                if request_client:
                    transmit(request_client)
                            
                else:
                    break

        wait_request()

    username, password, hostname = connect_to_client()
    conn_server = connect_to_server(username, password, hostname)
    serve(conn_client, conn_server)


def connection(ssock):
    try:
        conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
        process(conn)

    except ssl.SSLError as e:
        print(ERROR, e, ENDC)

    finally:
        if conn:
            conn.close()

def listening():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen(1)

    while True:
        try:
            conn = None
            ssock, addr = sock.accept()

            if verbose:
                print(GREENBOLD, INFO, "New connection from", addr, ENDC)

            connection(ssock)
            if verbose:
                print(GREENBOLD, INFO, "No more data from", addr, ENDC)

        except KeyboardInterrupt:
            if verbose:
                print(GREENBOLD, INFO,"Socket closed", ENDC)
            break

        '''except Exception as e:
            sock.close()
            print(RED, ERROR, e, ENDC)
            break'''

    sock.close()

if __name__ == '__main__':
    verbose = True
    listening()