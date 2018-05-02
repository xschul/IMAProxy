import email
import re
import imaplib
import time
import datetime
from dateutil import parser

from io import BytesIO
from kittengroomer_email import KittenGroomerMail

_fetchUID_request = re.compile(r'\A[A-Z]*[0-9]+\s(uid)\s(fetch)\s[0-9]+', flags=re.IGNORECASE)

def process(request, conn_server):
    str_request = request[1]

    # Email is fetched using UID fetch command
    if bool(_fetchUID_request.search(str_request)):
        tag = request[0][0]
        command = request[0][1]
        uid_flag = request[0][2][1]
        flags = request[0][2][2:]
        str_flags = ' '.join(str(flag) for flag in flags)

        # User wants to fetch an entire email
        if 'BODY.PEEK[]' in str_flags:
            print("IN SANITIZER MODULE: ", str_request)

            # TODO: if fetch 1:* ??
            if uid_flag.isdigit():
                print('Fetch 1 email: ', uid_flag)
                sanitize(uid_flag, str_flags, conn_server)
            else:
                print('Fetch multiple email: ', uid_flag)
                sanitize_list(uid_flag, str_flags, conn_server)

def sanitize_list(list_uid, flags, conn_server):
    uids = []
    raw_uids = list_uid.split(',')

    # Get the uids
    for u in raw_uids:
        if ':' in u:
            (start, end) = e.split(':')
            [uids.append(uid) for uid in range(int(start), int(end))]
        else:
            uids.append(int(u))

    # Sanitize the uids
    for uid in uids:
        sanitize(uid, flags, conn_server)

def sanitize(uid, flags, conn_server):
    conn_server.state = 'SELECTED'
    result, msg_data = conn_server.uid('fetch', uid, flags)

    if not msg_data[0]: # Email no longer exists
        return

    bmail = msg_data[0][1]
    mail = email.message_from_string(bmail.decode('utf-8'))
    if not mail.get('CIRCL-Sanitizer'):
        date = mail.get('Date')
        date = imaplib.Internaldate2tuple(date.encode())

        # Process email with the module
        t = KittenGroomerMail(bmail)
        m = t.process_mail()
        content = BytesIO(m.as_bytes())

        # Original 
        # TODO: insert hash
        # TODO: correct date
        mail.add_header('CIRCL-Sanitizer', 'Original')
        conn_server.append('Quarantine', '', date, str(mail).encode())

        # Sanitized
        sanitized_email = email.message_from_string(content.getvalue().decode('utf-8'))
        sanitized_email.add_header('CIRCL-Sanitizer', 'Sanitized')
        conn_server.append('Inbox', '', date, str(sanitized_email).encode())

        # Delete original
        mov, data = conn_server.uid('STORE', uid, '+FLAGS', '(\Deleted)')
        conn_server.expunge()