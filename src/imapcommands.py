import imaplib
import pprint

def open_connection(hostname, username, password, verbose = False):
    """ Return connection (UNSECURED FOR NOW)
    """

    # Connect to hostname
    if verbose:
        print('Connecting to', hostname)
    connection = imaplib.IMAP4_SSL(hostname)

    if verbose:
        print('Logging in as', username)

    # Connect to account(username, password)
    try:
        connection.login(username, password)
    except Exception as err:
        print('ERROR:', err)

    return connection

def search_message_id(c, mailbox, uid, verbose = False):
    if verbose:
        print('Searching message_id ', uid, ' into ', mailbox)

    c.select(mailbox, readonly=True)
    typ, msg_data = c.fetch(str(uid), '(BODY.PEEK[HEADER] FLAGS)')

    if msg_data != [b'The specified message set is invalid.']:
        print('MESSAGE', uid, 'EXISTS')
        #pprint.pprint(msg_data)
        return True
    else:
        print('MESSAGE', uid, "DOESN'T EXISTS")
        return False

def create_quarantine(c, verbose = False):
    typ, create_response = c.create('Quarantine')
    if verbose:
        print('CREATED Quarantine:', create_response)

def move_to_quarantine(c, src_mailbox, uid, verbose = False):
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
    c.copy(str(uid), dst_mailbox)
    if verbose:
        print('MSG ', uid, ' COPIED IN ', dst_mailbox)

def sanitize():
    pass


if __name__ == '__main__':
    hostname = 'imap-mail.outlook.com'
    username = 'mt2017pr@hotmail.com'
    password = 'ImapProxy'

    # Open connection
    with open_connection(hostname, username, password, verbose = True) as c:
        print(c)

        uid = 1
        src_mailbox = 'INBOX'
        dst_mailbox = 'Quarantine'

        if search_message_id(c, src_mailbox, uid, verbose=True):
            #create_quarantine(c, verbose = True)
            move_to_quarantine(c, src_mailbox, uid, verbose=True)

        # Search message in quarantine
        #search_message_id(c, dst_mailbox, uid, verbose=True)

        c.close()
        c.logout()
        

    