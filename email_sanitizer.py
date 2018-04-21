import email
import re
import imaplib
import time
import copy

_fetchUID_request = re.compile(r'\A[A-Z]*[0-9]+\s(UID)\s(fetch)|(FETCH)\s[0-9]+')

def process(request, conn_server):
    str_request = request[1]

    # Email is fetched using UID fetch command
    if bool(_fetchUID_request.search(str_request)):
        tag = request[0][0]
        command = request[0][1]
        uid_flag = request[0][2][1]
        flags = request[0][2][2:]
        str_flags = ' '.join(str(flag) for flag in flags)

        print("uid_flag ", uid_flag, " flags ", str_flags)

        # User wants to fetch an entire email ? TODO: check all possiblities
        if 'BODY.PEEK[]' in str_flags:
            sanitize(uid_flag, str_flags, conn_server)
            

def sanitize(uid, flags, conn_server):
    conn_server.state = 'SELECTED'
    result, msg_data = conn_server.uid('fetch', uid, flags)

    str_original_email = msg_data[0][1].decode('utf-8')
    original_email = email.message_from_string(str_original_email)
    
    if not original_email.get('CIRCL-Sanitizer'):
        

        # Original TODO: insert hashcode + note
        original_email.add_header('CIRCL-Sanitizer', 'Original')
        conn_server.append('Quarantine', '', imaplib.Time2Internaldate(time.time()), str(original_email).encode())

        # Sanitized
        sanitized_email = email.message_from_string(str_original_email)
        sanitized_email.add_header('CIRCL-Sanitizer', 'Sanitized')
        conn_server.append('Inbox', '', imaplib.Time2Internaldate(time.time()), str(sanitized_email).encode())

        # Delete original
        mov, data = conn_server.uid('STORE', uid, '+FLAGS', '(\Deleted)')
        conn_server.expunge()