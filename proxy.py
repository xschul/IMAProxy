import socket, ssl, imaplib

HOST, PORT, CERT = '', 993, 'cert.pem' # TODO: change 993 to 1030
CRLF = b'\r\n'
verbose = False

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

                        if split_response[1] == "BAD":
                            # Unknown error
                            print("WARNING: Bad command: ", request_server)

                    if split_response[0] == tag:
                        response_server, server_tag = change_tag(response_server, client_tag)
                        conn_client.send(response_server + CRLF)
                        break

                    else:
                        conn_client.send(response_server + CRLF)
                        
            else:
                break


    # Send "OK Service Ready command to the client"
    conn_client.sendall(b'* OK Service Ready. [Vg==]\r\n')
    response = conn_client.recv()

    # Send negociate commands
    conn_client.sendall(b'* CAPABILITY IMAP4 IMAP4rev1 AUTH=PLAIN AUTH=XOAUTH2 SASL-IR UIDPLUS MOVE ID UNSELECT CHILDREN IDLE NAMESPACE LITERAL+\r\n')
    conn_client.sendall(response[:5] + b' OK CAPABILITY completed.\r\n')
    prefix_client = response[:5]

    # Get identifiants and ACK login
    response = conn_client.recv()
    conn_client.sendall(response[:5] + b' OK LOGIN completed.\r\n')

    ids = response.decode().split(' ')
    username = ids[2]
    password = ids[3][1:-3]
    hostname = 'imap-mail.outlook.com' # TODO: get the hostname

    if verbose: 
        print("INFO:", username, password)
    
    conn_server = connect_to_server(username, password, hostname)
    serve(conn_client, conn_server)


def connection(ssock):
    try:
        conn = ssl.wrap_socket(ssock, certfile=CERT, server_side=True)
        process(conn)
    except ssl.SSLError as e:
        print("Error:", e)
    finally:
        if conn:
            conn.close()

def listening():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen(1)

    while True:
        conn = None
        ssock, addr = sock.accept()
        if verbose:
            print("INFO: New connection from", addr)
        connection(ssock)

if __name__ == '__main__':
    verbose = True
    listening()