import sys
import socket
import ssl
import imaplib
import re
import base64
import threading
import proxy_sanitizer

# Global variables
IMAP4_PORT, CERT = 993, 'cert.pem'
CRLF = b'\r\n'
_request = re.compile(r'\A[A-Z]*[0-9]+\s[a-zA-Z]\s*')
_tag = re.compile(r'[A-Z]*[0-9]+\s*')
_alpha = re.compile(r'[A-Z]*')
_digit = re.compile(r'[0-9]+')

# Capabilities of the proxy
capability_flags = ( 
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

class IMAP_Proxy:

    def __init__(self, host='', port=IMAP4_PORT, verbose = False):
        self.max_client = 5
        self.verbose = verbose

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(self.max_client)
        self.listen(host, port)


    def listen(self, host, port):
        def new_client(ssock):
            IMAP_Client(ssock, self.verbose)

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

        try:
            self.conn_client = ssl.wrap_socket(ssock, certfile=CERT, server_side=True) # TODO: remove cert
        except ssl.SSLError as e:
            log_error(e)
            self.close()

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
                flags = response[0][2]
                username = flags[0]
                password = flags[1]

            elif auth_type == "PLAIN":
                dec_response = base64.b64decode(response[1]).split(b'\x00')
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
            response = self.recv_from_client()

            if not response[0]:
                # Not a correct request
                log_error('Incorrect request: ' + str(response[1]))
                return None

            client_tag = response[0][0]
            client_command = response[0][1].upper()

            if client_command == 'CAPABILITY':
                # Get the tag (without the digits) of the client
                self.alpha_tag = re.search(_alpha, client_tag).group(0)

                capability_command = '* CAPABILITY ' + ' '.join(cap for cap in capability_flags) + ' +' 
                self.send_to_client(capability_command)
                self.send_to_client(ok(client_tag, client_command))

            elif client_command == 'AUTHENTICATE':
                auth_type = response[0][2][0]
                flags = response[0][2]
                self.send_to_client('+')
                response = self.recv_from_client()
                self.send_to_client(ok(client_tag, client_command))
                return get_credentials(response, auth_type)

            elif client_command == 'LOGIN':
                auth_type = client_command
                flags = response[0][2]
                self.send_to_client(ok(client_tag, client_command))
                return get_credentials(response, auth_type)

            else:
                log_error('Unknown request: ' + str(response[1]))
                return None

    def auth_server(self, credentials):
        if not credentials:
            return False

        username = credentials[0]
        password = credentials[1]
        domain = username.split('@')[1].split('.')[0] # TODO: Should work with multiple dots after '@'

        try:
            hostname = email_hostname[domain]
        except KeyError:
            log_error('Unknown hostname')
            return False

        print("connect with ", username, password)

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
            client_request = self.recv_from_client()
            client_request = self.handle_multiple_requests(client_request)

            server_tag = self.conn_server._new_tag().decode()
            self.send_to_server(self.swap_tag(client_request, server_tag)[1])

            # Listen responses from the server
            while self.listen_server:
                server_response = self.recv_from_server()
                self.send_to_client(self.swap_tag(server_response, self.last_tag)[1])
                    
    def swap_tag(self, request, new_tag):
        
        # If there is a tag and a command
        if request[0]:
            tag = request[0][0]
            command = request[0][1]
            flags = request[0][2]
            str_request = request[1]

            new_str_request = self.list_to_str([new_tag, command] + flags)

            new_request = ((new_tag, request[0][1], request[0][2]), new_str_request)
            return new_request

        # No tag or command, no need to convert
        return request

    def handle_multiple_requests(self, client_request):
        ''' Some requests contain mutliple requests '''

        if not client_request[0]:
            # Not a request
            return client_request

        client_tag = client_request[0][0]
        flags = client_request[0][2]
        curr_num_tag = re.search(_digit, client_tag).group(0)

        next_num_tag = int(curr_num_tag) + 1
        next_client_tag = self.alpha_tag + str(next_num_tag)

        if next_client_tag in flags:
            str_request = client_request[1]
            list_data = str_request.split(" ")
            index_next_request = list_data.find(next_client_tag)
            first_request = list_data[:index_next_request-1]
            second_request= list_data[index_next_request:]

            self.send_to_server(self.list_to_str(first_request))

            new_client_tag = second_request[0]
            new_client_command = second_request[1]
            new_flags = second_request[2:]
            new_str_request = self.list_to_str(second_request)
            return self.handle_multiple_requests((new_client_tag, new_client_command, new_flags),new_str_request)

        return client_request

    def list_to_str(self, list_data):
        return ' '.join(str(attr) for attr in list_data)

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
        b_response = self.conn_client.recv()
        str_response = b_response.decode('utf-8')[:-2] # decode and remove CRLF

        if self.verbose: 
            print("[-->]: ", b_response)

        # 2 cases: with ou without tag/command
        if bool(_request.search(str_response)):
            (tag, command, flags) = self.get_tag_command_flags(str_response)
            self.last_tag = tag
            self.listen_server = True

            if command == 'LOGOUT':
                self.state = 'LOGOUT'

            return ((tag, command, flags), str_response)

        if not str_response:
            self.listen_server = True

        return (None, str_response)

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
        b_response = self.conn_server._get_line()
        
        str_response = b_response.decode('utf-8', 'replace')    

        if self.verbose: 
            print("  [<--]: ", b_response)

        # 2 cases : Request with a tag and request without tag
        if bool(_request.search(str_response)):
            self.listen_server = False

            return (self.get_tag_command_flags(str_response), str_response)

        if str_response.startswith('+ '): # TODO: could generate problem (if the request begins with +)
            self.listen_server = False

        return (None, str_response)

    def get_tag_command_flags(self, str_request):
        args_response = str_request.split(' ')
        tag = args_response[0]
        command = args_response[1]
        flags = args_response[2:]
        return (tag, command, flags)

    def close(self):
        if self.conn_client:
            self.conn_client.close()


def log_info(s):
    print("[INFO]: ", s)

def log_error(s):
    RED = '\033[91m'
    ENDC = '\033[0m'
    print(RED, "[ERROR]: ", s, ENDC)

if __name__ == '__main__':
    IMAP_Proxy(verbose = True)