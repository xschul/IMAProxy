from lib import imapclient
import sys

""" Tests for IMAP clients """

def search_message_1_inbox(client):
    search_message_id(client, 'INBOX', 1)

def search_message_id(client, src_mailbox, uid):
    client.search_message_id(src_mailbox, uid)

def copy_message_1_indox_to_quar(client):
    copy_to_quarantine(client, 'INBOX', 1)

def copy_to_quarantine(client, src_mailbox, uid):
    if client.search_message_id(src_mailbox, uid):
        client.move_to_quarantine(src_mailbox, uid)
        # Search message in quarantine
        client.search_message_id('Quarantine', uid)

def create_quarantine(client):
    #client.create_quarantine(c, verbose = True)
    pass

if __name__ == '__main__':
    hostname = '192.168.1.100'
    #hostname = 'imap-mail.outlook.com'
    username = sys.argv[1]
    password = sys.argv[2]

    client = imapclient.IMAPClient(hostname, username, password, verbose = True)

    search_message_1_inbox(client)
    #copy_to_quarantine(client, 'INBOX', 1)

    client.close()