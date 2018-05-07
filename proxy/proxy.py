import sys, socket, ssl, imaplib, re, base64, threading, argparse
from modules import pycircleanmail, misp

MAX_CLIENT = 5
HOST, IMAP_PORT, IMAP_SSL_PORT = '', 143, 993
CRLF = b'\r\n'

Request = re.compile(r'(?P<tag>(?P<tag_alpha>[A-Z]*)(?P<tag_digit>[0-9]+))'
    r'(\s(UID))?'
    r'\s(?P<command>[A-Z]*)'
    r'(\s(?P<flags>.*))?', flags=re.IGNORECASE)
Response= re.compile(r'\A(?P<tag>[A-Z]*[0-9]+)'
    r'\s(OK)'
    r'(\s\[(?P<flags>.*)\])?'
    r'\s(?P<command>[A-Z]*)'
    r'\s(completed)', flags=re.IGNORECASE)

# Capabilities of the proxy
capability_flags = ( 
    'IMAP4',
    'IMAP4rev1',
    'AUTH=PLAIN',
#    'AUTH=XOAUTH2', 
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

# Authorized email addresses with hostname TODO: check with mx record
email_hostname = {
    'hotmail': 'imap-mail.outlook.com',
    'outlook': 'imap-mail.outlook.com',
    'yahoo': 'imap.mail.yahoo.com'
}

class IMAP_Proxy:

    def __init__(self, port=None, host=HOST, certfile=None, max_client=MAX_CLIENT, verbose=False):
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
        self.sock.bind((host, port))
        self.sock.listen(max_client)
        self.listen()


    def listen(self):
        def new_client(ssock):
            if not self.certfile:
                IMAP_Client(ssock, self.verbose)
            else:
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
        self.listen_client = False
        self.conn_client = ssock

        try:
            if self.auth_server(self.auth_client()):
                self.listen_client = True
                self.serve()
        except ValueError as e:
            print('[ERROR]', e)

        self.close()

    def auth_client(self):
        
        def ok(tag, command):
            """
                Build the OK response to a specific command with the corresponding tag
            """
            return tag + ' OK ' + command + ' completed.'

        def get_credentials(response, auth_type):
            
            if auth_type == "LOGIN":
                args_response = response.split(' ')
                username = args_response[2]
                password = args_response[3]

            elif auth_type == "PLAIN":
                dec_response = base64.b64decode(response).split(b'\x00')
                username = dec_response[1].decode()
                password = dec_response[2].decode()

            elif auth_type == "XOAUTH2":
                pass # TODO

            if username.startswith('"') and username.endswith('"'):
                username = username[1:-1]

            if password.startswith('"') and password.endswith('"'):
                password = password[1:-1]

            print(username, password)
            return (username, password)

        self.send_to_client('* OK Service Ready.')

        while True:
            request = self.recv_from_client()
            match = Request.match(request)

            if not match:
                # Not a correct request
                raise ValueError('Error while authenticate to the client: '
                    + request, ' contains no tag and/or no command')

            client_tag = match.group('tag')
            client_command = match.group('command').upper()

            if client_command == 'CAPABILITY':
                # Get the tag (without the digits) of the client
                self.alpha_tag = match.group('tag_alpha')

                capability_command = '* CAPABILITY ' + ' '.join(cap for cap in capability_flags) + ' +' 
                self.send_to_client(capability_command)
                self.send_to_client(ok(client_tag, client_command))

            elif client_command == 'AUTHENTICATE':
                auth_type = match.group('flags')
                self.send_to_client('+')
                request = self.recv_from_client()
                self.send_to_client(ok(client_tag, client_command))
                return get_credentials(request, auth_type)

            elif client_command == 'LOGIN':
                auth_type = client_command
                self.send_to_client(ok(client_tag, client_command))
                return get_credentials(request, auth_type)

            else:
                raise ValueError('Error while authenticate to the client: '
                    + 'The command', client_command, 'not supported.')

    def auth_server(self, credentials):
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
        def listen_request_client():
            def process_client_command(command, flags):
                if command == 'LOGOUT':
                    self.listen_client = False

                elif command == 'SELECT':
                    self.set_current_folder(flags)


            requests = self.recv_from_client()

            for request in requests.split('\r\n'): # Handle multiple requests in one

                request_match = Request.match(request)

                if not request_match:
                    raise ValueError('The request contains no tag and/or no command')

                client_tag = request_match.group('tag')
                client_command = request_match.group('command').upper()
                client_flags = request_match.group('flags')

                process_client_command(client_command, client_flags)

                # External modules
                print("Request to be processed: " + request)
                #pycircleanmail.process(request, self)
                #misp.process(request, self.conn_server)

                server_tag = self.conn_server._new_tag().decode()
                self.send_to_server(request.replace(client_tag, server_tag, 1))
                
                listen_response_server(client_tag, client_command, server_tag)

        def listen_response_server(client_tag, client_command, server_tag):
            def client_sequence():
                client_sequence = self.recv_from_client()
                while client_sequence != '':
                    self.send_to_server(client_sequence)
                    client_sequence = self.recv_from_client()
                self.send_to_server(client_sequence)

            listen_server = True
            while listen_server:
                response = self.recv_from_server()
                response_match = Response.match(response)

                if response_match: # ok response
                    server_response_tag = response_match.group('tag')
                    server_command = response_match.group('command').upper()
                    if (client_command == server_command) and (server_tag == server_response_tag):
                        self.send_to_client(response.replace(server_response_tag, client_tag, 1))
                        listen_server = False
                    else: # Injection attempt
                        self.send_to_client(response)

                else:
                    self.send_to_client(response)

                if client_command != 'FETCH' and response.startswith('+'):
                    # Avoid injection while fetching and listen to client
                    client_sequence()

        # Listen requests from the client
        while self.listen_client:
            listen_request_client()

    def set_current_folder(self, folder):
        if folder.startswith('"') and folder.endswith('"'):
            folder = folder[1:-1]
        self.current_folder = folder

    def send_to_client(self, str_data):
        b_data = str_data.encode() + CRLF

        try:
            self.conn_client.send(b_data)
        except (BrokenPipeError, ConnectionResetError):
            self.listen_client = False

        if self.verbose: 
            print("[<--]: ", b_data)

    def recv_from_client(self):
        b_response = self.conn_client.recv(1024)
        str_response = b_response.decode('utf-8', 'replace')[:-2] # decode and remove CRLF

        if self.verbose: 
            print("[-->]: ", b_response)

        return str_response

    def send_to_server(self, str_data):
        b_data = str_data.encode() + CRLF

        try:
            self.conn_server.send(b_data)
        except (BrokenPipeError, ConnectionResetError):
            self.listen_client = False

        if self.verbose: 
            print("  [-->]: ", b_data)

    def recv_from_server(self):
        b_response = self.conn_server._get_line()
        str_response = b_response.decode('utf-8', 'replace')    

        if self.verbose: 
            print("  [<--]: ", b_response)

        return str_response

    def close(self):
        if self.conn_client:
            self.conn_client.close()

class IMAP_Client_SLL(IMAP_Client):

    def __init__(self, ssock, certfile, verbose = False):
        try:
            self.conn_client = ssl.wrap_socket(ssock, certfile=certfile, server_side=True)
        except ssl.SSLError as e:
            raise

        IMAP_Client.__init__(self, self.conn_client, verbose)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certfile', help='Enable SSL/TLS connection over port 993 (by default) with the certfile given. '
        + 'Without this argument, the connection will not use SSL/TLS over port 143 (by default)')
    parser.add_argument('-p', '--port', type=int, help='Listen on the given port')
    parser.add_argument('-n', '--nclient', type=int, help='Maximum number of client supported by the proxy')
    parser.add_argument('-v', '--verbose', help='Echo IMAP payload', action='store_true')
    args = parser.parse_args()

    IMAP_Proxy(port=args.port, certfile=args.certfile, max_client=args.nclient, verbose=args.verbose)