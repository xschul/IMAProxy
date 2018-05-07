import email, re, imaplib, time
from io import BytesIO
from kittengroomer_email import KittenGroomerMail

UID_Fetch = re.compile(r'(?P<tag>[A-Z]*[0-9]+)'
    r'\s(UID)'
    r'\s(FETCH)'
    r'\s(?P<uid>[0-9:,]+)'
    r'\s(?P<flags>.*)', flags=re.IGNORECASE)

'''Fetch = re.compile(r'(?P<tag>[A-Z]*[0-9]+)'
    r'\s(UID)'
    r'\s(FETCH)'
    r'\s(?P<uid>[0-9:,]+)'
    r'\s(?P<flags>.*)', flags=re.IGNORECASE)'''

FLAGS = (
    'BODY.PEEK[]',
    'RFC822.TEXT'
    )

def process(request, IMAP_client):
    match = UID_Fetch.match(request)

    # Email is fetched using UID fetch command
    if match:
        print('IIIN')
        tag = match.group('tag')
        uid = match.group('uid')
        flags = match.group('flags')
    else:
        return

    print(uid, flags)
    conn_server = IMAP_client.conn_server
    folder = IMAP_client.current_folder.upper()

    if 'SENT' in folder:
        # Don't sanitize sent emails
        return

    if not any(flag in flags for flag in FLAGS):
        # The user don't want to fetch the body of an email
        print('Dont want to fetch netire email:', flags)
        return 
    
    print('WANTS TO FETCH ENTIRE BODY')

    # TODO: if fetch 1:* ??
    if uid.isdigit():
        print('Fetch 1 email: ', uid)
        sanitize(uid, flags, conn_server)
    else:
        print('Fetch multiple email: ', uid)
        sanitize_list(uid, flags, conn_server)

def sanitize_list(list_uid, flags, conn_server):
    uids = []
    raw_uids = list_uid.split(',')

    # Get the uids
    for u in raw_uids:
        if ':' in u:
            (start, end) = u.split(':')
            [uids.append(uid) for uid in range(int(start), int(end)+1)]
        else:
            uids.append(int(u))

    print("To sanitize: ", uids)

    # Sanitize the uids
    for uid in uids:
        sanitize(str(uid), flags, conn_server)

def sanitize(uid, flags, conn_server):
    conn_server.state = 'SELECTED'
    print(uid, flags)
    result, msg_data = conn_server.uid('fetch', uid, flags)

    print('Result', result, 'with flags: ', flags)

    if not msg_data[0]: # Email no longer exists
        return

    bmail = msg_data[0][1]
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
        conn_server.append('Quarantine', '', date, str(mail).encode())

        # Sanitized
        sanitized_email = email.message_from_string(content.getvalue().decode('utf-8'))
        sanitized_email.add_header('CIRCL-Sanitizer', 'Sanitized')
        conn_server.append('Inbox', '', date, str(sanitized_email).encode())

        # Delete original
        mov, data = conn_server.uid('STORE', uid, '+FLAGS', '(\Deleted)')
        conn_server.expunge()