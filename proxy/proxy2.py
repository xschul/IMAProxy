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
    'yahoo': 'imap.mail.yahoo.com',
    'gmail': 'imap.gmail.com'
}

Commands = (
    'authenticate',
    'capability',
    'login',
    'logout',
    'select',
    'fetch'
)

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
        """ Wait and create a new IMAP_Client for each client. """

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

    def __init__(self, ssock, verbose = False):
        self.verbose = verbose
        self.conn_client = ssock
        self.conn_server = None

        try:
            self.send_to_client('* OK Service Ready.')
            self.listen_client()
        except ValueError as e:
            print('[ERROR]', e)

    def listen_client(self):
        while self.listen_client:
            request = self.recv_from_client()
            match = Request.match(request)

            print(request)

            if not match:
                # Not a correct request
                self._error('Incorrect request')
                raise ValueError('Error while connecting to the client: '
                    + request, ' contains no tag and/or no command')

            self.client_tag = match.group('tag')
            self.client_command = match.group('command').lower()
            self.client_flags = match.group('flags')
            self.request = request

            print('Request: ' + request)

            if self.client_command in Commands: 
                getattr(self, self.client_command)()
            else:
                self.transmit()

            print('DONE')

    def capability(self):
        self.send_to_client('* CAPABILITY ' + ' '.join(cap for cap in CAPABILITIES) + ' +')
        self.send_to_client(self._success())

    def authenticate(self):
        auth_type = self.client_flags.lower()
        self.send_to_client('+')
        request = self.recv_from_client()
        getattr(self, self.client_command+"_"+auth_type)(request)

    def authenticate_plain(self, request):
        (empty, busername, bpassword) = base64.b64decode(request).split(b'\x00')
        username = busername.decode()
        password = bpassword.decode()
        self.connect_server(username, password)

    def login(self):
        #self.send_to_client(client_success())
        (username, password) = self.client_flags.split(' ')
        self.connect_server(username, password)

    def logout(self):
        self.listen_client = False
        self.transmit()

    def select(self):
        self.set_current_folder(self.client_flags)
        self.transmit()

    def fetch(self):
        # modules
        self.transmit()

    def set_current_folder(self, folder):
        """ Set the current folder of the client """
        if folder.startswith('"') and folder.endswith('"'):
            folder = folder[1:-1]
        self.current_folder = folder

    def connect_server(self, username, password):
        if username.startswith('"') and username.endswith('"'):
            username = username[1:-1]
        if password.startswith('"') and password.endswith('"'):
            password = password[1:-1]

        domains = username.split('@')[1].split('.')[:-1] # Remove before '@' and remove '.com' / '.be' / ...
        domain = ' '.join(str(d) for d in domains) 

        try:
            hostname = email_hostname[domain]
        except KeyError:
            self._error('Unknown hostname')
            raise ValueError('Error while connecting to the server: '
                    + 'Invalid domain name ', domain)

        print("Trying to connect ", username)
        self.conn_server = imaplib.IMAP4_SSL(hostname)

        try:
            self.conn_server.login(username, password)
        except imaplib.IMAP4.error:
            self._failure('Incorrect credentials')
            raise ValueError('Error while connecting to the server: '
                    + 'Invalid credentials: ', username, " / ", password)

        self.send_to_client(self._success())

    def transmit(self):
        server_tag = self.conn_server._new_tag().decode()
        self.send_to_server(self.request.replace(self.client_tag, server_tag, 1))
        self.listen_server(server_tag)
        print('done transmit')
                
    def listen_server(self, server_tag):
        def client_sequence():
            # Listen client requests when the server response starts with '+'
            client_sequence = self.recv_from_client()
            while client_sequence != '': # Client sequence ends with empty request
                self.send_to_server(client_sequence)
                client_sequence = self.recv_from_client()
            self.send_to_server(client_sequence)

        response = self.recv_from_server()
        response_match = Response.match(response)

        if response_match: # success response
            server_response_tag = response_match.group('tag')
            server_command = response_match.group('command').lower()
            if (self.client_command == server_command) and (server_tag == server_response_tag):
                # Transmit tag response and listen next client command
                self.send_to_client(response.replace(server_response_tag, self.client_tag, 1))
                return 
        
        self.send_to_client(response)

        if response.startswith('+') and client_command != 'FETCH':
            # The response starts with '+' -> the client will send a sequence of request
            # Don't start the client sequence if an email is fetched (the '+' is contained in an email)
            client_sequence()

        return self.listen_server(server_tag)

        print('server done')

    def send_to_client(self, str_data):

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

    def _success(self):
        """ Success command completing response of the command with the corresponding tag """
        return self.client_tag + ' OK ' + self.client_command + ' completed.'

    def _failure(self, msg):
        """ Failure command completing response """
        return self.client_tag + ' NO ' + self.client_command + ' failed.'

    def _error(self, msg):
        """ Error command completing response """
        return self.client_tag + ' BAD ' + msg
    

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