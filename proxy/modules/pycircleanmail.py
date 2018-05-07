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

QUARANTINE_FOLDER = 'Quarantine'

def process(request, IMAP_client):
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

    conn_server = IMAP_client.conn_server
    folder = IMAP_client.current_folder

    create_quarantine_folder(conn_server)

    if 'SENT' in folder.upper():
        # Don't sanitize sent emails
        return

    if uid.isdigit():
        sanitize(uid, conn_server, folder, uid_command)
    else:
        uids = convert_uids_str_to_list(uid)
        for uid in uids:
            sanitize(str(uid), conn_server, folder, uid_command)

def sanitize(uid, conn_server, folder, uid_command):
    bmail = fetch(uid, conn_server, folder, uid_command)
    mail = email.message_from_string(bmail.decode('utf-8'))
    if not mail.get('CIRCL-Sanitizer'):
        date_str = mail.get('Date')
        if date_str:
            date = imaplib.Internaldate2tuple(date_str.encode())
        else:
            date = imaplib.Time2Internaldate(time.time())

        # Process email with the module
        t = KittenGroomerMail(bmail)
        m = t.process_mail()
        content = BytesIO(m.as_bytes())

        # Original 
        # TODO: insert hash
        mail.add_header('CIRCL-Sanitizer', 'Original')
        conn_server.append(QUARANTINE_FOLDER, '', date, str(mail).encode())

        # Sanitized
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
    typ, create = conn_server.create(QUARANTINE_FOLDER)