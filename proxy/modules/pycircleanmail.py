import email, re, imaplib, time
from .utils import convert_uids_str_to_list, fetch
from io import BytesIO
from kittengroomer_email import KittenGroomerMail

UID_Fetch = re.compile(r'(?P<tag>[A-Z]*[0-9]+)'
    r'\s(UID)'
    r'\s(FETCH)'
    r'\s(?P<uid>[0-9:,]+)'
    r'\s(?P<flags>.*)', flags=re.IGNORECASE)

Fetch = re.compile(r'(?P<tag>[A-Z]*[0-9]+)'
    r'\s(FETCH)'
    r'\s(?P<uid>[0-9:,]+)'
    r'\s(?P<flags>.*)', flags=re.IGNORECASE)

# Default Quarantine folder
QUARANTINE_FOLDER = 'Quarantine'

def process(client):
    """ Apply the PyCIRCLeanMail module if the request match with a Fetch request

        request - Request from the cleint (str format)
        client - IMAP_Client object

    """
    request = client.request
    match_uid = UID_Fetch.match(request)
    match = Fetch.match(request) # without uid
    uid_command = False

    # Email is fetched using UID fetch command
    if match:
        uid = match.group('uid')
    elif match_uid:
        uid = match_uid.group('uid')
        uid_command = True
    else:
        return

    conn_server = client.conn_server
    folder = client.current_folder

    create_quarantine_folder(conn_server)

    if 'SENT' in folder.upper():
        # Don't sanitize sent emails
        print('IN')
        return

    if uid.isdigit(): 
        # Only one email is fetched
        sanitize(uid, conn_server, folder, uid_command)
    else:
        # Multiple emails are fetched (uid format: [0-9,:])
        uids = convert_uids_str_to_list(uid) 
        # (uids is a list of digits)
        for uid in uids:
            sanitize(str(uid), conn_server, folder, uid_command)

def sanitize(uid, conn_server, folder=None, uid_command=True):
    """ Sanitize, if necessary, an email.

        uid - String containing the uid of the email;
        conn_server - Socket to the server;
        folder - Only necessary if uid_command is False (default: None);
        uid_command - True if command contains UID flag

    If the email is not sanitized yet, make a sanitized copy if the same folder
    and an unsanitized copy if the Quarantine folder. The original email is deleted
    """

    bmail = fetch(uid, conn_server, folder, uid_command)

    if not bmail: # Email no longer exists
        return

    mail = email.message_from_string(bmail.decode('utf-8'))

    print(mail)

    if not mail.get('CIRCL-Sanitizer'):
        # Email not yet sanitized

        date_str = mail.get('Date')
        if date_str:
            date = imaplib.Internaldate2tuple(date_str.encode())
        else:
            # Default time is the current time
            date = imaplib.Time2Internaldate(time.time())

        # Process email with the module
        t = KittenGroomerMail(bmail)
        m = t.process_mail()
        content = BytesIO(m.as_bytes())

        # Copy of the original email
        # TODO: insert hash
        mail.add_header('CIRCL-Sanitizer', 'Original')
        conn_server.append(QUARANTINE_FOLDER, '', date, str(mail).encode())

        # Copy of the sanitized email
        sanitized_email = email.message_from_string(content.getvalue().decode('utf-8'))
        sanitized_email.add_header('CIRCL-Sanitizer', 'Sanitized')
        conn_server.append(folder, '', date, str(sanitized_email).encode())

        # Delete original
        if uid_command:
            mov, data = conn_server.uid('STORE', uid, '+FLAGS', '(\Deleted)')
        else:
            mov, data = conn_server.store(uid, '+FLAGS', '(\Deleted)')
        conn_server.expunge()

def create_quarantine_folder(conn_server):
    """ Create the Quarantine folder 

        conn_server - Socket to the server
    """

    typ, create = conn_server.create(QUARANTINE_FOLDER)