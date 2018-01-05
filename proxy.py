import sys
import socket, ssl, imaplib
import re
import base64
import threading

# Global variables
HOST, PORT, CERT = '', 993, 'cert.pem'
CRLF = b'\r\n'
_digits = re.compile('\d')
last_tag_client = None

# Capabilities of the proxy
capabilities = ( 
    'IMAP4',
    'IMAP4rev1',
    'AUTH=PLAIN',
    #'AUTH=XOAUTH2', # TODO
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
                pass # TODO

            if username.startswith('"') and username.endswith('"'):
                username = username[1:-1]

            if password.startswith('"') and password.endswith('"'):
                password = password[1:-1]

            return username, password

        # Start service
        service_ready = ('* OK Service Ready.').encode() + CRLF
        conn_client.sendall(service_ready)
        log(SEND_CL + str(service_ready))

        while True: 
            request = conn_client.recv()
            log(RECV_CL + str(request))

            tag = get_attr(request)[0]
            command = get_attr(request)[1].upper()

            if command == 'CAPABILITY':
                capability_command = '* CAPABILITY ' + ' '.join(cap for cap in capabilities) + ' +' 
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
                log(RED+ERROR+'Unknown command from request '+str(request)+ENDC)
                return

    def connect_to_server(username, password, hostname):
        connection = imaplib.IMAP4_SSL(hostname)
        connection.login(username, password)

        log(INFO+'Logged in')

        return connection

    def serve(conn_client, conn_server):
        def convert_request(request, tag):
            attrs = get_attr(request)

            if not attrs:
                # Empty request --> end of a client sending sequence
                return request, 'EMPTY'

            received_tag = attrs[0]

            if not bool(_digits.search(received_tag)):
                # The request contains not tag --> client sending sequence
                return request, None

            attrs[0] = tag
            new_request = ' '.join(str(attr) for attr in attrs)

            return new_request.encode()+CRLF, received_tag

        def transmit(request_client):
            log(RECV_CL+str(request_client))
            tag_server = conn_server._new_tag().decode()
            request_server, tag_client = convert_request(request_client, tag_server)
            if tag_client and tag_client != 'EMPTY':
                global last_tag_client
                last_tag_client = tag_client


            conn_server.send(request_server)
            log(SEND_SR+str(request_server))

            while tag_client:
                # Listen response from the server
                response_server = conn_server._get_line()+CRLF
                log(RECV_SR+str(response_server))
                attr_response = get_attr(response_server)

                tag = None if len(attr_response) < 1 else attr_response[0]
                command = None if len(attr_response) <= 1 else attr_response[1]

                if command == 'BYE':
                    # Client stopped connection
                    conn_client.send(response_server)
                    log(SEND_CL+str(response_server))
                    return

                if command == 'BAD':
                    # Bad command
                    conn_client.send(response_server)
                    print(RED+ERROR+"Bad command: "+str(request_client)+ENDC)

                if tag == '+':
                    # Request from client incoming
                    conn_client.send(response_server)
                    log(SEND_CL+"Client seq: "+str(response_server))
                    break

                if tag == tag_server or tag_client == 'EMPTY' and tag != '*':
                    # Last response from server
                    response_server, server_tag = convert_request(response_server, last_tag_client)
                    conn_client.send(response_server)
                    log(SEND_CL+"Last: "+str(response_server))
                    break

                else:
                    # Response from server incoming
                    conn_client.send(response_server)
                    log(SEND_CL+"Server seq: "+str(response_server))

        def wait_request():
            # Listen requests from the user
            while True:
                request_client = conn_client.recv()
                
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
    try:
        conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
        process(conn)
    except ssl.SSLError as e:
        log(RED+ERROR+e+ENDC)
    finally:
        if conn:
            conn.close()

def listening():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))

    sock.listen(5)

    while True:
        try:
            conn = None
            ssock, addr = sock.accept()

            print(GREENBOLD+INFO+'New connection from '+str(addr[0])+':'+str(addr[1])+ENDC)
            threading.Thread(target = connection, args = (ssock,)).start()
            print(GREENBOLD+INFO+'No more data from '+str(addr[0])+':'+str(addr[1])+ENDC)

        except KeyboardInterrupt:
            if sock:
                sock.close()

            print(GREENBOLD+INFO+"Socket closed"+ENDC)
            break

        '''except Exception as e:
            sock.close()
            print(RED, ERROR, e, ENDC)
            break'''

    if sock:
        sock.close()

''' VERBOSE '''
# Verbose variables
RECV_CL = "[-->]: "
SEND_CL = "[<--]: "
RECV_SR = "  [<--]: "
SEND_SR = "  [-->]: "
INFO = "[INFO]: "
ERROR= "[ERROR]: "
verbose = False

# Colors
RED = '\033[91m'
GREENBOLD = '\033[92m\033[1m'
ENDC = '\033[0m'

# Verbose method
def log(s):
    if verbose:
        print(s.replace('\r\n', ''))
''' END VERBOSE '''

if __name__ == '__main__':
    verbose = True
    listening()