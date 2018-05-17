import sys, socket, ssl, imaplib, re, base64, threading, oauth2, argparse
from modules import pycircleanmail, misp

# Default maximum number of client supported by the proxy
MAX_CLIENT = 5  
# Default ports
IMAP_PORT, IMAP_SSL_PORT = 143, 993
CRLF = b'\r\n'

# Tagged request from the client
Request = re.compile(r'(?P<tag>[A-Z]*[0-9]+)'
    r'(\s(UID))?'
    r'\s(?P<command>[A-Z]*)'
    r'(\s(?P<flags>.*))?', flags=re.IGNORECASE)
# Tagged response from the server
Response= re.compile(r'\A(?P<tag>[A-Z]*[0-9]+)'
    r'\s(OK)'
    r'(\s\[(?P<flags>.*)\])?'
    r'\s(?P<command>[A-Z]*)'
    r'\s(completed)', flags=re.IGNORECASE)

# Capabilities of the proxy
CAPABILITIES = ( 
    'IMAP4',
    'IMAP4rev1',
    'AUTH=PLAIN',
#    'AUTH=XOAUTH2', 
    'SASL-IR',
    'UIDPLUS',
    'MOVE',
    'ID',
    'UNSELECT', 
    'CHILDREN', 
    'NAMESPACE',
    'LITERAL'
    )

# Authorized email addresses with hostname TODO: check with mx record
email_hostname = {
    'hotmail': 'imap-mail.outlook.com',
    'outlook': 'imap-mail.outlook.com',
    'yahoo': 'imap.mail.yahoo.com'
}

class IMAP_Proxy:
    
    r""" Implementation of the proxy.

    Instantiate with: IMAP_Proxy([port[, host[, certfile[, max_client[, verbose]]]]])

            port - port number (default: None. Standard IMAP4 / IMAP4 SSL port will be selected);
            host - host's name (default: localhost);
            certfile - PEM formatted certificate chain file (default: None);
                Note: if certfile is provided, the connection will be secured over
                SSL/TLS. Otherwise, it won't be secured.
            max_client - Maximum number of client supported by the proxy (default: global variable MAX_CLIENT);
            verbose - Display the IMAP payload (default: False)
    
    The proxy listens on the given host and port and creates an object IMAP4_Client (or IMAP4_Client_SSL for
    secured connections) for each new client. These socket connections are asynchronous and non-blocking.
    """

    def __init__(self, port=None, host='', certfile=None, max_client=MAX_CLIENT, verbose=False):
        self.verbose = verbose
        self.certfile = certfile

        if not port: # Set default port
            if not certfile: # Without SSL/TLS
                port = IMAP_PORT
            else: # With SSL/TLS
                port = IMAP_SSL_PORT

        if not max_client:
            max_client = MAX_CLIENT

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', port))
        self.sock.listen(max_client)
        self.listen()


    def listen(self):
        """ Wait and create a new IMAP_Client for each client.
        """
        def new_client(ssock):
            if not self.certfile: # Connection without SSL/TLS
                IMAP_Client(ssock, self.verbose)
            else: # Connection with SSL/TLS
                IMAP_Client_SLL(ssock, self.certfile, self.verbose)

        while True:
            try:
                ssock, addr = self.sock.accept()
                threading.Thread(target = new_client, args = (ssock,)).start()
            except KeyboardInterrupt:
                break
            
        if self.sock:
            self.sock.close()

class IMAP_Client:

    r""" IMAP_Client class.

    Instantiate with: IMAP_Client([ssock[, verbose]])

        ssock - Socket with the client;
        verbose - Display the IMAP payload (default: False)

    1. Connect the client and the proxy using connect_client() method
    2. Connect the proxy and the server using connect_server() method
    3. Transmit commands and responses from the client to the server.
    Each time a command is received from the client, process it by the
    pycircleanmail and misp modules.
    """

    def __init__(self, ssock, verbose = False):
        self.verbose = verbose
        self.listen_client = False # True if the proxy is connected to the client and proxy
        self.conn_client = ssock

        try:
            if self.connect_server(self.connect_client()):
                self.listen_client = True
                self.serve()
        except ValueError as e:
            print('[ERROR]', e)

        self.close()

    def connect_client(self):
        """ Connect the client with the proxy.
        First, exchange capabilities in the CAPABILITIES global variable. 
        Second, retrieve the credentials of the client using AUTHENTICATE and/or LOGIN
        commands sent by the client.

        Return the credentials (tuple of string (username, password)) of the client.

        Raise an error if the request received is not a command or if the command is not
        supported (different from CAPABILITY, AUTHENTICATE or LOGIN).
        """

        def success(tag, command):
            # Build the OK response to a specific command with the corresponding tag
            return tag + ' OK ' + command + ' completed.'

        def get_credentials(request, auth_type):
            # Return the credentials contained in the request depending the authentication type
            if auth_type == "LOGIN":
                args_response = request.split(' ')
                username = args_response[2]
                password = args_response[3]

            elif auth_type == "PLAIN":
                dec_response = base64.b64decode(request).split(b'\x00')
                username = dec_response[1].decode()
                password = dec_response[2].decode()

            elif auth_type == "XOAUTH2":
                pass # TODO

            if username.startswith('"') and username.endswith('"'):
                username = username[1:-1]

            if password.startswith('"') and password.endswith('"'):
                password = password[1:-1]

            return (username, password)

        self.send_to_client('* OK Service Ready.')

        while True:
            request = self.recv_from_client()
            match = Request.match(request)

            if not match:
                # Not a correct request
                raise ValueError('Error while connecting to the client: '
                    + request, ' contains no tag and/or no command')

            client_tag = match.group('tag')
            client_command = match.group('command').upper()

            if client_command == 'CAPABILITY':
                capability_command = '* CAPABILITY ' + ' '.join(cap for cap in CAPABILITIES) + ' +' 
                self.send_to_client(capability_command)
                self.send_to_client(success(client_tag, client_command))

            elif client_command == 'AUTHENTICATE':
                auth_type = match.group('flags')
                self.send_to_client('+')
                request = self.recv_from_client()
                self.send_to_client(success(client_tag, client_command))
                return get_credentials(request, auth_type)

            elif client_command == 'LOGIN':
                auth_type = client_command
                self.send_to_client(success(client_tag, client_command))
                return get_credentials(request, auth_type)

            else:
                raise ValueError('Error while connecting to the client: '
                    + 'The command', client_command, 'not supported.')

    def connect_server(self, credentials):
        """ Connect the proxy with the server using the credentials.

            credentials - Tuple of string containing an username and a password

        Return True if the proxy is correctly connected to the server.

        Raise a ValueError if the credentials are invalid.
        """

        if not credentials:
            return False

        username = credentials[0]
        password = credentials[1]
        domains = username.split('@')[1].split('.')[:-1] # Remove before '@' and remove '.com' / '.be' / ...
        domain = ' '.join(str(d) for d in domains) 

        try:
            hostname = email_hostname[domain]
        except KeyError:
            return False

        print("Trying to connect ", username)
        self.conn_server = imaplib.IMAP4_SSL(hostname)

        try:
            self.conn_server.login(username, password)
        except imaplib.IMAP4.error:
            raise ValueError('Invalid credentials')

        return True

    def serve(self):
        """ Listen requests from the client, transmit to the server, listen response
        from the server and transmit to the client.

        Raise a ValueError if the client sends an incorrect request.
        """

        def listen_request_client():
            # Handle a request from the client

            def process_client_command(command, flags):
                # Handle particular commands from the client

                if command == 'LOGOUT':
                    self.listen_client = False

                elif command == 'SELECT':
                    self.set_current_folder(flags)


            requests = self.recv_from_client()
            for request in requests.split('\r\n'): # Handle multiple requests in one

                request_match = Request.match(request)
                if not request_match:
                    raise ValueError('Error while serving: '
                        + 'The request contains no tag and/or no command')

                client_tag = request_match.group('tag')
                client_command = request_match.group('command').upper()
                client_flags = request_match.group('flags')

                process_client_command(client_command, client_flags)

                # External modules
                pycircleanmail.process(request, self)
                misp.process(request, self)

                # Replace the client tag by the next server tag
                server_tag = self.conn_server._new_tag().decode()
                self.send_to_server(request.replace(client_tag, server_tag, 1))
                
                listen_response_server(client_tag, client_command, server_tag)

        def listen_response_server(client_tag, client_command, server_tag):
            # Handle the response from the server

            def client_sequence():
                # Listen client requests when the server response starts with '+'
                client_sequence = self.recv_from_client()
                while client_sequence != '': # Client sequence ends with empty request
                    self.send_to_server(client_sequence)
                    client_sequence = self.recv_from_client()
                self.send_to_server(client_sequence)

            listen_server = True
            while listen_server:
                response = self.recv_from_server()
                response_match = Response.match(response)

                if response_match: # success response
                    server_response_tag = response_match.group('tag')
                    server_command = response_match.group('command').upper()
                    if (client_command == server_command) and (server_tag == server_response_tag):
                        # Transmit tag response and listen next client command
                        self.send_to_client(response.replace(server_response_tag, client_tag, 1))
                        listen_server = False
                    else:
                        # Counter injection attempt 
                        # (the server sent a response but the command and/or the tag don't match
                        # with the client request)
                        self.send_to_client(response)

                else:
                    # Transmit untagged response
                    self.send_to_client(response)

                if response.startswith('+') and client_command != 'FETCH':
                    # The response starts with '+' -> the client will send a sequence of request
                    # Don't start the client sequence if an email is fetched (the '+' is contained in an email)
                    client_sequence()

        # Listen requests from the client
        while self.listen_client:
            listen_request_client()

    def set_current_folder(self, folder):
        """ Set the current folder of the client """
        if folder.startswith('"') and folder.endswith('"'):
            folder = folder[1:-1]
        self.current_folder = folder

    def send_to_client(self, str_data):
        """ Send request to the client

            str_data - String without CRLF

        Stop listening the client if the connection with the client is broken/reset
        """

        b_data = str_data.encode() + CRLF

        try:
            self.conn_client.send(b_data)
        except (BrokenPipeError, ConnectionResetError):
            self.listen_client = False

        if self.verbose: 
            print("[<--]: ", b_data)

    def recv_from_client(self):
        """ Return the last request (str format) from the client """

        b_request = self.conn_client.recv(1024)
        str_request = b_request.decode('utf-8', 'replace')[:-2] # decode and remove CRLF

        if self.verbose: 
            print("[-->]: ", b_request)

        return str_request

    def send_to_server(self, str_data):
        """ Send request to the server

            str_data - String without CRLF

        Stop listening the client if the connection with the server is broken/reset
        """

        b_data = str_data.encode() + CRLF

        try:
            self.conn_server.send(b_data)
        except (BrokenPipeError, ConnectionResetError):
            self.listen_client = False

        if self.verbose: 
            print("  [-->]: ", b_data)

    def recv_from_server(self):
        """ Return the last response (str format) from the server """

        b_response = self.conn_server._get_line()
        str_response = b_response.decode('utf-8', 'replace')    

        if self.verbose: 
            print("  [<--]: ", b_response)

        return str_response

    def logout_server(self):
        self.listen_server = False
        if self.conn_server:
            conn_server.close()
            conn_server.logout()

    def bye_client(self):
        self.listen_client = False
        if self.conn_client:
            send_to_client('* BYE IMAP4rev1 Proxy logging out')
            self.conn_client.close()

    def close(self):
        logout_server()
        bye_client()

class IMAP_Client_SLL(IMAP_Client):
    r""" IMAP_Client class over SSL connection

    Instantiate with: IMAP_Client([ssock[, certfile[, verbose]]])
    
        ssock - Socket with the client;
        certfile - PEM formatted certificate chain file;
        verbose - Display the IMAP payload (default: False)

    for more documentation see the docstring of the parent class IMAP_Client.
    """

    def __init__(self, ssock, certfile, verbose = False):
        try:
            self.conn_client = ssl.wrap_socket(ssock, certfile=certfile, server_side=True)
        except ssl.SSLError as e:
            raise

        IMAP_Client.__init__(self, self.conn_client, verbose)

if __name__ == '__main__':
    # Parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certfile', help='Enable SSL/TLS connection over port 993 (by default) with the certfile given. '
        + 'Without this argument, the connection will not use SSL/TLS over port 143 (by default)')
    parser.add_argument('-p', '--port', type=int, help='Listen on the given port')
    parser.add_argument('-n', '--nclient', type=int, help='Maximum number of client supported by the proxy')
    parser.add_argument('-v', '--verbose', help='Echo IMAP payload', action='store_true')
    args = parser.parse_args()

    # Start proxy
    IMAP_Proxy(port=args.port, certfile=args.certfile, max_client=args.nclient, verbose=args.verbose)