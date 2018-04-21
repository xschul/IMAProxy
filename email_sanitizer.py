import email
import re
import imaplib
import time

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

    raw_email = msg_data[0][1]
    raw_email_string = raw_email.decode('utf-8')

    print(raw_email_string)

    email_message = email.message_from_string(raw_email_string)

    already_sanitized = False

    for part in email_message.walk():
        # WARNING attachments/html
        signature = part.get('Sanitizer module')

        if(signature):
            print("SIGNATURE: ", signature)
            already_sanitized = True
    
    if not already_sanitized:
        print('need to sanitize')
        # Original
        email_original = email_message
        email_original.add_header('Sanitizer module', 'Original')
        conn_server.append('Quaratine', '', imaplib.Time2Internaldate(time.time()), str(email_original).encode())

        # Sanitized
        email_sanitized = email_message
        email_sanitized.add_header('Sanitizer module', 'Sanitized')
        conn_server.append('INBOX', '', imaplib.Time2Internaldate(time.time()), str(email_sanitized).encode())

        # Delete origininal
        mov, data = conn_server.uid('STORE', uid , '+FLAGS', '(\Deleted)')
        conn_server.expunge()