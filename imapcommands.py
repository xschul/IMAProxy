import imaplib
import pprint
import email
import sys


import socket
import ssl
class IMAP4_SSL_CA_CHECKER(imaplib.IMAP4_SSL):
    def open(self, host = '', port = imaplib.IMAP4_SSL_PORT, ca_certs = None):
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port))
        self.sslobj = ssl.wrap_socket(self.sock, ca_certs=ca_certs)
        self.file = self.sslobj.makefile('rb')

"""
IMAP library which is able of retrieve emails, move an email to another folder and download the attachments
"""

def open_connection(hostname, username, password, verbose = False):
    ''' 
    Open a connection to a hostname with the identifiers (username, password) 
    '''

    # Connect to hostname
    if verbose:
        print('Connecting to', hostname)

    #connection = imaplib.IMAP4_SSL(hostname)     --------- No certificat
    connection = IMAP4_SSL_CA_CHECKER(host = hostname)


    if verbose:
        print('Logging in as', username)

    # Connect to account(username, password)
    try:
        connection.login(username, password)
        print('Logged in')
    except Exception as err:
        print('ERROR:', err)

    return connection

def search_message_id(c, mailbox, uid, verbose = False):
    '''
    From a connection "c", search an email with the id "uid" inside the mailbox "mailbox"
    '''

    if verbose:
        print('Searching message_id ', uid, ' into ', mailbox)

    c.select(mailbox, readonly=True)
    typ, msg_data = c.fetch(str(uid), '(BODY.PEEK[HEADER] FLAGS)')

    if msg_data != [b'The specified message set is invalid.']:
        print('MESSAGE', uid, 'EXISTS')
        return True
    else:
        print('MESSAGE', uid, "DOESN'T EXIST")
        return False

def create_quarantine(c, verbose = False):
    '''
    From a connection "c", create a folder named "Quarantine"
    '''

    typ, create_response = c.create('Quarantine')
    if verbose:
        print('CREATED Quarantine:', create_response)

def move_to_quarantine(c, src_mailbox, uid, verbose = False):
    '''
    From a connection "c", move the email insde "src_mailobx" with id "uid" to the folder "Quarantine"
    '''

    quar_mailbox = 'Quarantine'

    # Copy this email to Quarantine
    copy(c, uid, quar_mailbox, verbose)

    # Delete the email in the src_mailbox
    c.select(src_mailbox)

    # Current flags of uid
    if verbose: 
        typ, response = c.fetch(str(uid), '(FLAGS)')
        print('Flags before:', response)

    # Add deleted flag for uid 
    typ, response = c.store(str(uid), '+FLAGS', "\\Deleted")
    if verbose:
        print('Add deleted flag:', response)

    # New flags of uid
    if verbose:
        typ, response = c.fetch(str(uid), '(FLAGS)')
        print('Flags after:', response)

    c.expunge()

def copy(c, uid, dst_mailbox, verbose = False):
    '''
    From a connection "c", copy the email with id "uid" from the current mailbox to "dst_mailbox"
    '''

    c.copy(str(uid), dst_mailbox)
    if verbose:
        print('MSG', uid, 'COPIED IN ', dst_mailbox)

def download_attachments(c, uid, src_mailbox, verbose = False):
    '''
    STILL IN DEVELOPMENT
    From a connection "c", download the attachments of the email with id "uid" inside the "src_mailbox"
    '''

    c.select(src_mailbox)
    outputdir = "../../"

    resp, data = c.fetch(str(uid), "(BODY.PEEK[])")
    email_body = str(data[0][1])
    print(email_body)
    mail = email.message_from_string(email_body)
    print(mail.get_content_maintype())
    if not mail.is_multipart():
        if verbose:
            print("Not multipart")
        return
    for part in mail.walk():
        if verbose:
            print("Multipart")

        if part.get_content_maintype() != 'multipart' and part.get('Content-Disposition') is not None:
            open(outputdir + part.get_filename(), 'wb').write(part.get_payload(decode=True))

def sanitize():
    pass


if __name__ == '__main__':
    '''
    Retrieve email with id = 2 inside the INBOX folder
    '''
    
    hostname = '40.97.41.114' # IP of imap-mail.outlook.com
    username = sys.argv[1]
    password = sys.argv[2]

    # Open connection
    c = open_connection(hostname, username, password, verbose = True)

    uid = 2
    src_mailbox = 'INBOX'
    dst_mailbox = 'Quarantine'

    if search_message_id(c, src_mailbox, uid, verbose=True):
        pass
        #create_quarantine(c, verbose = True)
        #move_to_quarantine(c, src_mailbox, uid, verbose=True)
        #download_attachments(c, uid, src_mailbox, verbose = True)

        # Search message in quarantine
        #search_message_id(c, dst_mailbox, uid, verbose=True)

    c.close()
    c.logout()