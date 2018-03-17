import email

def process_request_client(attr_request_client, conn_server):
    """attr_request_client is a lsit of the arguments of the request
    """
    print(attr_request_client)
    if (len(attr_request_client) < 5): return
    if (attr_request_client[1] == 'UID' and attr_request_client[2] == 'fetch' and attr_request_client[4] == '(UID'):
        print("-------------------------------")
        # UID Fetch request format: 8 UID fetch 678 (UID RFC ...)

        uid = attr_request_client[3]
        print("uid:", uid)
        flags_list = attr_request_client[4:]
        flags = ' '.join(str(flag) for flag in flags_list)
        print("flags:", flags)

        if('RFC822' in flags):
            conn_server.state = 'SELECTED'
            msg_data = conn_server.uid('fetch', uid, flags)
            raw_email = msg_data[0][1]

            print("=============================")

            '''f = open('%s.eml' %(uid), 'w')
            f.write(raw_email)'''

            # Copy the email in Quaratine
            '''msg_data = conn_server.uid('copy', uid, 'Quarantine') #TODO: check the output
            mov, data = conn_server.uid('STORE', uid , '+FLAGS', '(\Deleted)')
            conn_server.expunge()'''