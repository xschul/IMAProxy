import email, re, imaplib, time
from .utils import parse_ids
from io import BytesIO
from kittengroomer_email import KittenGroomerMail

Fetch = re.compile(r'(?P<tag>[A-Z0-9]+)'
    r'(\s(UID))?'
    r'\s(FETCH)'
    r'\s(?P<ids>[0-9:,]+)'
    r'\s(?P<flags>.*)', flags=re.IGNORECASE)

# Default Quarantine folder
QUARANTINE_FOLDER = 'Quarantine'

# Sanitizer header and values
SIGNATURE = 'X-CIRCL-Sanitizer'
VALUE_ORIGINAL = 'Original'
VALUE_SANITIZED= 'Sanitized'
VALUE_ERROR= 'Error'

# Message data used to get the flags and sanitizer header
MSG_DATA_FS = '(FLAGS BODY.PEEK[HEADER.FIELDS (' + SIGNATURE + ')])'
# Message data used to get the entire mail
MSG_DATA = 'BODY.PEEK[]'

def process(client):
    """ Apply the PyCIRCLeanMail module if the request match with a Fetch request

        request - Request from the cleint (str format)
        client - IMAP_Client object

    """
    request = client.request
    conn_server = client.conn_server
    folder = client.current_folder

    # Don't sanitize sent or quarantine emails
    if 'SENT' in folder.upper() or QUARANTINE_FOLDER in folder or 'Deleted' in folder: return

    uidc = True if 'UID' in request else False

    match = Fetch.match(request)
    if not match: return # Client discovers new emails
    ids = match.group('ids')

    if ids.isdigit(): 
        # Only one email fetched
        sanitize(ids, conn_server, folder, uidc)
    else:
        # Multiple emails are fetched (ids format: [0-9,:])
        for id in parse_ids(ids):
            sanitize(str(id), conn_server, folder, uidc) 
            

def sanitize(id, conn_server, folder, uidc):
    """ Sanitize, if necessary, an email.

        ids - String containing the ids of the email;
        conn_server - Socket to the server;
        folder - Current folder of the client;
        uidc - True if command contains UID flag

    If the email is not sanitized yet, make a sanitized copy if the same folder
    and an unsanitized copy if the Quarantine folder. The original email is deleted
    """

    conn_server.state = 'SELECTED'
    result, response = conn_server.uid('fetch', id, MSG_DATA_FS) if uidc else conn_server.fetch(id, MSG_DATA_FS)

    print('In folder', folder)
    print('Result1: ', response)

    if result == 'OK' and response[0]:
        try:
            [(flags, signature), ids] = response
        except ValueError:
            # Not correct answer
            return

        if SIGNATURE.encode() in signature:
            print('Already sanitized')
            return

    print('Not sanitized')
    # Message unseen or no CIRCL header
    conn_server.select(folder)
    result, response = conn_server.uid('fetch', id, MSG_DATA) if uidc else conn_server.fetch(id, MSG_DATA)

    if result == 'OK' and response != [b'The specified message set is invalid.'] and response != [None]:
        bmail = response[0][1]
    else:
        return

    # Get the DATE of the email
    mail = email.message_from_bytes(bmail)
    date_str = mail.get('Date')
    date = imaplib.Internaldate2tuple(date_str.encode()) if date_str else imaplib.Time2Internaldate(time.time())

    # Process email with the module
    try:
        t = KittenGroomerMail(bmail)
        m = t.process_mail()
        content = BytesIO(m.as_bytes())
    except Exception:
        # Often ValueError in BytesIO
        smail = email.message_from_bytes(bmail)
        print("-- Can't sanitize this email: --")
        print(smail)
        print("--------------------------------")
        smail.add_header(SIGNATURE, VALUE_ERROR)
        conn_server.append(folder, '', date, str(smail).encode())
        return

    # Copy of the sanitized email
    try:
        smail = email.message_from_bytes(content.getvalue())
        smail.add_header(SIGNATURE, VALUE_SANITIZED)
        conn_server.append(folder, '', date, str(smail).encode())
    except Exception as e:
        # Often KeyError in content.getvalue()
        print("-- Error: ", e, " --")
        print(content.getvalue())
        print("--------------------------------")
        smail = email.message_from_bytes(bmail)
        smail.add_header(SIGNATURE, VALUE_ERROR)
        conn_server.append(folder, '', date, str(smail).encode())

    # Copy of the original email
    mail.add_header(SIGNATURE, VALUE_ORIGINAL)
    conn_server.append(QUARANTINE_FOLDER, '', date, bmail)

    # Delete original
    conn_server.uid('STORE', id, '+FLAGS', '(\Deleted)') if uidc else conn_server.store(id, '+FLAGS', '(\Deleted)')
    conn_server.expunge()