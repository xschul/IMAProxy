import socket, ssl, imaplib, sys

# Global variables
HOST, PORT, CERT = '', 993, 'cert.pem'
CRLF = b'\r\n'
verbose = False

# Colors
FAIL = '\033[91m'
GREENBOLD = '\033[92m\033[1m'
ENDC = '\033[0m'

def process(conn_client):
    def connect_to_server(username, password, hostname):
        connection = imaplib.IMAP4_SSL(hostname)
        connection.login(username, password)

        if verbose:
            print('INFO: Logged in')

        return connection

    def serve(conn_client, conn_server):
        def change_tag(request, tag):
            data = request.decode().split(" ")
            tag_removed = data[0]
            data[0] = tag
            new_request = ' '.join(str(x) for x in data)
            new_request = new_request.encode()

            return new_request, tag_removed

        # Listen COMMANDS from the user one by one
        while True:
            request_client = conn_client.recv()
            tag = conn_server._new_tag().decode()
            request_server, client_tag = change_tag(request_client, tag)
            
            if request_client:
                conn_server.send(request_server)

                if verbose:
                    print("[-->]: Request sent ", request_server)

                # Listen RESPONSES from the server
                while True:
                    response_server = conn_server._get_line()
                    split_response = response_server.decode().split(" ")

                    if verbose:
                            print("  [<--]: Response received ", response_server)

                    if len(split_response) > 1:
                        if split_response[1] == "BYE":
                            # Client stopped connection
                            return

                    if split_response[0] == tag:
                        response_server, server_tag = change_tag(response_server, client_tag)
                        conn_client.send(response_server + CRLF)
                        break

                    else:
                        conn_client.send(response_server + CRLF)
                        
            else:
                break


    # Send "OK Service Ready command to the client"
    OK_service_command = b'* OK Service Ready. [Vg==]\r\n'
    conn_client.sendall(OK_service_command)
    response = conn_client.recv()
    client_tag = response.decode().split(" ")[0].encode()

    if verbose:
        print("  [<--]:", OK_service_command)
        print("[-->]:", response)

    # Send CAPABILITY commands
    capability_command = b'* CAPABILITY IMAP4 IMAP4rev1 AUTH=PLAIN AUTH=XOAUTH2 SASL-IR UIDPLUS MOVE ID UNSELECT CHILDREN IDLE NAMESPACE LITERAL+\r\n'
    OK_capability_command = client_tag + b' OK CAPABILITY completed.\r\n'
    conn_client.sendall(capability_command)
    conn_client.sendall(OK_capability_command)

    if verbose:
        print("  [<--]:", capability_command)
        print("  [<--]:", OK_capability_command)

    # Get identifiants and ACK login
    response = conn_client.recv()
    client_tag = response.decode().split(" ")[0].encode()
    OK_login = client_tag + b' OK LOGIN completed.\r\n'
    conn_client.sendall(OK_login)

    if verbose:
        print("[-->]:", response)
        print("  [<--]:", OK_login)

    ids = response.decode().split(' ')
    username = ids[2]
    password = ids[3][1:-3]
    hostname = 'imap-mail.outlook.com' # TODO: get the hostname

    if verbose: 
        print("INFO:", username, "*****")
    
    conn_server = connect_to_server(username, password, hostname)
    serve(conn_client, conn_server)


def connection(ssock):
    try:
        conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
        process(conn)

    except ssl.SSLError as e:
        print("ERROR:", e)

    except Exception as e:
        print(FAIL, "ERROR WHILE CONNECTION:", e, ENDC)

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
                print(GREENBOLD, "INFO: New connection from", addr, ENDC)

            connection(ssock)
            if verbose:
                print(GREENBOLD, "INFO: No more data from", addr, ENDC)

        except KeyboardInterrupt:
            sock.close()
            if verbose:
                print(GREENBOLD, "INFO: Socket closed", ENDC)
            break

        except Exception as e:
            sock.close()
            print(FAIL, "ERROR WHILE LISTENING:", e, ENDC)
            break

if __name__ == '__main__':
    verbose = True
    listening()