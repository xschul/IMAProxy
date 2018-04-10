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
                print("Plain: ", response)
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

            print('response: ', response, " + ", client_command)

            if client_command == 'CAPABILITY':
                # Get the tag (without the digits) of the client
                self.alpha_tag = re.search(_alpha, client_tag).group(0)
                print("Alpha =     ", self.alpha_tag)

                capability_command = '* CAPABILITY ' + ' '.join(cap for cap in capability_flags) + ' +' 
                print("cap: ", capability_command)
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
        hostname = email_hostname[domain]
        print(username, password, domain, hostname)


        self.conn_server = imaplib.IMAP4_SSL(hostname)
        self.conn_server.login(username, password)

        log_info('Logged in')

        return True

    def serve(self):
        # Listen requests from the client
        while True:
            client_request = self.recv_from_client()
            client_request = self.handle_multiple_requests(client_request)

            server_tag = self.conn_server._new_tag().decode()
            self.send_to_server(self.convert_request(client_request, server_tag)[1])

            while client_request[0]:
                server_response = self.recv_from_server()

                print(server_response)

                # If the request contains no tag and no command
                if not server_response[0]:
                    self.send_to_client(server_response[1])

                    if server_response[1][0] and server_response[1][0] == '+':
                        # Request from client incoming
                        print("REQUEST FROM CLIENT INCOMING")
                        break

                    else:
                        # Response from server incoming
                        print("RESPONSE FROM SERVER INCOMING")

                # The request contains a tag and a command
                else:
                    print("COMMAND --")

                    server_tag = server_response[0][0]
                    server_command = server_response[0][1]
                    server_flags = server_response[0][2]

                    if server_command == 'BYE':
                        # Client stopped connection
                        self.send_to_client(server_response[1])
                        return

                    elif server_command == 'BAD':
                        # Bad command
                        self.send_to_client(server_response[1])
                        log_error("Bad command: " + client_request[1])

                    else:
                        # Last response from server
                        print("LAST RESPONSE FROM SERVER")
                        converted_server_response = self.convert_request(server_response, self.last_tag)
                        self.send_to_client(converted_server_response[1])
                        break


    def convert_request(self, request, new_tag):
        
        if request[0]:
            tag = request[0][0]
            command = request[0][1]
            flags = request[0][2]
            str_request = request[1]

            new_str_request = self.list_to_str([new_tag, command] + flags)

            new_request = ((new_tag, request[0][1], request[0][2]), new_str_request)
            print("newrequest: ", new_request)
            return new_request

        else: #necessary ?
            return request

    def handle_multiple_requests(self, client_request):
        ''' Some requests could contain mutliple request '''
        client_tag = client_request[0][0]
        flags = client_request[0][2]
        curr_num_tag = re.search(_digit, client_tag).group(0)

        next_num_tag = int(curr_num_tag) + 1
        next_client_tag = self.alpha_tag + str(next_num_tag)
        print("Next tag = ", next_client_tag)

        if next_client_tag in flags:
            print("TWO REQUESTS")
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
        self.conn_client.sendall(b_data)

        if self.verbose: 
            print("[<--]: ", str_data)

    def recv_from_client(self):
        str_response = self.conn_client.recv().decode().replace('\r\n', '')

        if self.verbose: 
            print("[-->]: ", str_response)

        # 2 cases: with ou without tag/command
        if bool(_request.search(str_response)):
            args_response = str_response.split(' ')
            tag = args_response[0]
            self.last_tag = tag
            command = args_response[1]
            flags = args_response[2:]

            return ((tag, command, flags), str_response)

        return (None, str_response)

    def send_to_server(self, str_data):
        b_data = str_data.encode() + CRLF
        self.conn_server.send(b_data)

        if self.verbose: 
            print("  [-->]: ", str_data)

    def recv_from_server(self):
        str_response = str(self.conn_server._get_line().decode()).replace('\r\n', '')

        if self.verbose: 
            print("  [<--]: ", str_response)

        # 2 cases : Request with a tag and request without tag
        if bool(_request.search(str_response)):
            print("Good response")
            args_response = str_response.split(' ')
            tag = args_response[0]
            command = args_response[1]
            flags = args_response[2:]

            return ((tag, command, flags), str_response)

        print("Not a command")
        return (None, str_response)

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