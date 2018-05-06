import sys, socket, ssl, imaplib, re, base64, threading
from modules import pycircleanmail, misp

# Global variables
MAX_CLIENT = 5
HOST, IMAP_PORT, IMAP_PORT_SSL = '', 143, 993
CRLF = b'\r\n'
Request = re.compile(r'(?P<tag>(?P<tag_alpha>[A-Z]*)(?P<tag_digit>[0-9]+))(\s(UID))?\s(?P<command>[A-Z]*)(\s(?P<flags>.*))*', flags=re.IGNORECASE)
Response= re.compile(r'\A(?P<tag>[A-Z]*[0-9]+)\s(OK)(\s\[(?P<flags>[A-Z-]*)\])?\s(?P<command>[A-Z]*)\s(completed)', flags=re.IGNORECASE)

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

# Authorized email addresses with hostname
email_hostname = {
    'hotmail': 'imap-mail.outlook.com',
    'outlook': 'imap-mail.outlook.com',
    'yahoo': 'imap.mail.yahoo.com'
}

class IMAP_Proxy:

    def __init__(self, port, host=HOST, certfile=None, verbose=False):
        self.verbose = verbose
        self.certfile = certfile

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(MAX_CLIENT)
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
            except Exception as e:
                log_error(str(e))

        if self.sock:
            self.sock.close()

class IMAP_Client:

    def __init__(self, ssock, verbose = False):
        self.verbose = verbose
        self.state = 'LOGOUT'
        # TODO: know the current folder

        self.conn_client = ssock

        if self.auth_server(self.auth_client()):
            log_info("Link between server and client done")
            self.state = 'LOGIN'
            self.serve()

        self.close()

    def auth_client(self):
        
        def ok(tag, command):
            """
                Build the OK response to a specific command with the corresponding tag
            """
            return tag + ' OK ' + command + ' completed.'

        def get_credentials(response, auth_type):
            
            if auth_type == "LOGIN":
                # TODO: verify working
                args_response = response.split(' ')
                print(args_response)
                username = flags[2]
                password = flags[3]

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

            return (username, password)

        self.send_to_client('* OK Service Ready.')

        while True:
            request = self.recv_from_client()

            if not bool(Request.search(request)):
                # Not a correct request
                log_error('Incorrect request: ' + request)
                return None

            match = Request.match(request)
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
                print('auth: ', auth_type)
                self.send_to_client('+')
                request = self.recv_from_client()
                self.send_to_client(ok(client_tag, client_command))
                return get_credentials(request, auth_type)

            elif client_command == 'LOGIN':
                auth_type = client_command
                self.send_to_client(ok(client_tag, client_command))
                return get_credentials(request, auth_type)

            else:
                log_error('Unknown request: ' + request)
                return None

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
            log_error('Unknown hostname')
            return False

        print("Trying to connect ", username)

        self.conn_server = imaplib.IMAP4_SSL(hostname)

        try:
            self.conn_server.login(username, password)
        except Exception:
            log_error('Invalid credentials')
            return False

        log_info('Logged in')

        return True

    def serve(self):
        # Listen requests from the client
        while self.state == 'LOGIN':
            request = self.recv_from_client()
            request = self.handle_multiple_requests(request)

            request_match = Request.match(request)
            client_tag = request_match.group('tag')
            client_command = request_match.group('command').upper()

            # External modules
            print("Request to be processed: " + request)
            #pycircleanmail.process(request, self.conn_server)
            #misp.process(request, self.conn_server)

            server_tag = self.conn_server._new_tag().decode()
            self.send_to_server(request.replace(client_tag, server_tag))
            
            server_command = None
            server_response_tag = None

            # Listen responses from the server
            while (client_command != server_command) and (server_tag != server_response_tag):
                response = self.recv_from_server()

                if bool(Response.search(response)): # ok response
                    response_match = Response.match(response)
                    server_response_tag = response_match.group('tag')
                    server_command = response_match.group('command').upper()

                    self.send_to_client(response.replace(server_response_tag, client_tag))

                else:
                    self.send_to_client(response)

                print(client_command, server_command, server_tag, server_response_tag)

    def handle_multiple_requests(self, request):
        ''' Some requests contain mutliple requests '''

        first_request = Request.search(request)
        if not first_request:
            log_error('bad command') #TODO: replace by error

        first_match = Request.match(request)
        flags = first_match.group('flags')

        if bool(Request.search(flags)): # Request is in flags -> 2 requests
            second_match = Request.match(flags)
            first_digit = int( first_match.group('tag_digit'))
            second_digit= int(second_match.group('tag_digit'))

            # Verify the second tag is the first tag + 1
            if second_digit == (first_digit + 1):
                self.send_to_server(first_request.group(0))
                second_request = Request.search(flags)
                return handle_multiple_requests(second_request)

        return request

    def send_to_client(self, str_data):
        b_data = str_data.encode() + CRLF

        try:
            self.conn_client.send(b_data)
        except (BrokenPipeError, ConnectionResetError):
            log_info('Connection reset by peer')
            self.state = 'LOGOUT'

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
            log_info('Connection reset by peer')
            self.state = 'LOGOUT'

        if self.verbose: 
            print("  [-->]: ", b_data)

    def recv_from_server(self):
        # TODO: Handle '+'
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
            log_error(e)
            raise

        IMAP_Client.__init__(self, self.conn_client, verbose)

def log_info(s):
    print("[INFO]: ", s)

def log_error(s):
    RED = '\033[91m'
    ENDC = '\033[0m'
    print(RED, "[ERROR]: ", s, ENDC) #TODO: repalce by raise error

if __name__ == '__main__':
    verbose = True
    if len(sys.argv) <= 1:
        IMAP_Proxy(port=IMAP_PORT,verbose = verbose)
    else:
        CERT = sys.argv[1]
        IMAP_Proxy(certfile=CERT, port=IMAP_PORT_SSL, verbose = verbose)
    