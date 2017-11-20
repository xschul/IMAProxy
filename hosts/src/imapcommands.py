import imaplib
import pprint
import email

def open_connection(hostname, username, password, port = 0, verbose = False):
    # Connect to hostname
    if verbose:
        print('Connecting to', hostname)

    if port == 0: 
        connection = imaplib.IMAP4_SSL(hostname)
    else:
        connection = imaplib.IMAP4_SSL(hostname, port)

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
        print('MESSAGE', uid, "DOESN'T EXIST")
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
        print('MSG', uid, 'COPIED IN ', dst_mailbox)

def download_attachments(c, uid, src_mailbox, verbose = False):
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


def tag_email(c, uid, src_mailbox, verbose = False):
    c.select(src_mailbox)

    typ, msg_data = c.fetch(str(uid), '(BODY.PEEK[HEADER])')
    #pprint.pprint(msg_data)


def sanitize():
    pass


if __name__ == '__main__':
    #hostname = 'imap-mail.outlook.com'
    hostname = '40.97.145.162'
    username = 'mt2017pr@hotmail.com'
    password = 'ImapProxy'
    port = 10000

    # Open connection
    with open_connection(hostname, username, password, port, verbose = True) as c:
        print(c)

        uid = 2
        src_mailbox = 'INBOX'
        dst_mailbox = 'Quarantine'

        if search_message_id(c, src_mailbox, uid, verbose=True):
            pass
            #create_quarantine(c, verbose = True)
            #move_to_quarantine(c, src_mailbox, uid, verbose=True)
            #tag_email(c, uid, src_mailbox, verbose=True)
            #download_attachments(c, uid, src_mailbox, verbose = True)

        # Search message in quarantine
        #search_message_id(c, dst_mailbox, uid, verbose=True)

        c.close()
        c.logout()