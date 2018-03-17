import sys
import socket
import ssl
import imaplib
import re
import base64
import threading
import proxy_sanitizer

# Global variables
HOST, PORT, CERT = '', 993, 'cert.pem'
CRLF = b'\r\n'
_digits = re.compile(r'\d+')
last_tag_client = None

# Capabilities of the proxy
capabilities = ( 
    'IMAP4',
    'IMAP4rev1',
    'AUTH=PLAIN',
#    'AUTH=XOAUTH2', # TODO
    'SASL-IR',
#    'IDLE',
    'UIDPLUS',
    'MOVE',
    'ID',
    'UNSELECT', 
    'CHILDREN', 
    'NAMESPACE',
    'LITERAL'
    )

# Authorized email addresses with hostname
email_hostname = {
    'hotmail': 'imap-mail.outlook.com',
    'outlook': 'imap-mail.outlook.com',
    'yahoo': 'imap.mail.yahoo.com'
}


def process(conn_client):
    """Process the connection with the client and with the server.
    It first connect_to_client(), then it connect_to_server() and, 
    finally, serve() the requests between the client and the server
    """ 

    def get_attr(request):
        """Returns a list of the words contained in the byte-encoded request argument
        """
        lst = request.decode(encoding = 'ISO-8859-1').split()
        return ([s.replace('\r\n', '') for s in lst])

    def connect_to_client():
        """Connect the proxy with the client.
        The proxy first sends a "Service ready" to the client.
        Then, it exchanges the Capabilities and the authentication attributes.
        Finally, it gets the login of the client
        """

        def ok_command(tag, command):
            """Build the OK response to a specific command with the corresponding tag
            """
            ok_command = tag + ' OK ' + command + ' completed.' + '\r\n'
            return ok_command.encode()

        def get_login(request, auth_type):
            """ From a given request and authentication type,
            retrieve the username and password of the client
            """

            log(INFO+"Input login is "+str(request))
            if auth_type == "LOGIN":
                # Login is not encoded
                username = get_attr(request)[2]
                password = get_attr(request)[3]

            elif auth_type == "PLAIN":
                # Login is encoded in base64
                decoded_req = base64.b64decode(request).split(b'\x00')
                username = decoded_req[1].decode()
                password = decoded_req[2].decode()

            elif auth_type == "XOAUTH2":
                pass # TODO

            # Remove the quotation mark
            if username.startswith('"') and username.endswith('"'):
                username = username[1:-1]
            if password.startswith('"') and password.endswith('"'):
                password = password[1:-1]

            log(INFO+"Output login is "+str(username)+" / "+str(password))
            return username, password

        # Start service
        service_ready = ('* OK Service Ready.').encode() + CRLF
        conn_client.sendall(service_ready)
        log(SEND_CL + str(service_ready))

        while True: 
            request = conn_client.recv()
            log(RECV_CL + str(request))

            if not get_attr(request):
                # Not a login procedure
                return

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

    def connect_to_server(username, password):
        """Connect the proxy with the server
        """
        domain = username.split('@')[1].split('.')[0]
        hostname = email_hostname.get(domain, None)

        if hostname:
            connection = imaplib.IMAP4_SSL(hostname)
            connection.login(username, password)

            log(INFO+'Logged in')
            return connection
        else:
            log(RED+ERROR+'Unknown domain')
            return

    def serve(conn_client, conn_server):
        """Get the request from the client/server and transmit it to the server/client
        """
        def build_request(list_attr):
            """Convert a list to a request
            """
            request = ' '.join(str(attr) for attr in list_attr)
            return request.encode() +CRLF

        def handle_multiple_requests(request):
            """If the request in argument contains multiple requets,
            it treats all the requests except the last one.
            """
            attrs = get_attr(request)
            
            if attrs and bool(_digits.search(attrs[0])):
                # Get the first tag of the request
                tag = attrs[0]
                num_tag = re.findall(r'\d+', tag)[0]
                prefix_tag = tag.replace(num_tag, '')

                next_tag = prefix_tag + str(int(num_tag)+1)
                if next_tag in attrs:
                    # Two requests spotted - Send the first request
                    first_request = convert_request(build_request(attrs[0:attrs.index(next_tag)]), tag)[0]
                    log(SEND_SR+str(first_request))
                    conn_server.send(first_request)
                    # Handle the second request
                    last_request = build_request(attrs[attrs.index(next_tag):])
                    return handle_multiple_requests(last_request)

            # No multiple requests
            return request

        def convert_request(request, tag):
            """Replace the tag of the request by the tag in argument
            """
            attrs = get_attr(request)

            if not attrs:
                # Empty request --> end of a client sending sequence
                return request, 'EMPTY'

            received_tag = attrs[0]

            if not bool(_digits.search(received_tag)):
                # The request contains not tag --> client sending sequence
                return request, None

            attrs[0] = tag
            converted_request = build_request(attrs)

            return converted_request, received_tag

        def transmit(request_client):
            """Transmit the request of the client to the server
            """
            request_client = handle_multiple_requests(request_client)
            log(RECV_CL+str(request_client))
            tag_server = conn_server._new_tag().decode()
            request_server, tag_client = convert_request(request_client, tag_server)
            if tag_client and tag_client != 'EMPTY':
                global last_tag_client
                last_tag_client = tag_client

            # Sanitizer (TODO: improve conditionnal to cover all cases)
            proxy_sanitizer.process_request_client(get_attr(request_client), conn_server)

            # Send the request from the client to the server
            conn_server.send(request_server)
            log(SEND_SR+str(request_server))

            while tag_client:
                """ Listen response(s) from the server
                """
                response_server = conn_server.readline()
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
#                    log(SEND_CL+"Server seq: "+str(response_server))

        def wait_request():
            """Wait for a request from the client
            """
            while True:
                request_client = conn_client.recv()
                
                if request_client:
                    transmit(request_client)
                            
                else:
                    break

        wait_request()

    # Get the credentials of the client
    username, password = connect_to_client()
    
    if username and password:
        # Connect with the real server
        conn_server = connect_to_server(username, password)
        if conn_server:
            # Transmit data between client and server
            serve(conn_client, conn_server)


def connection(ssock):
    """Make the connection with the client
    """
    try:
        conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
        process(conn)
    except ssl.SSLError as e:
        log(RED+ERROR+str(e)+ENDC)
    finally:
        if conn:
            conn.close()

def listening():
    """Listen on a socket for a connection with a client
    """
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
    verbose = False
    listening()