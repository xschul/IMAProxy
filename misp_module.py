import email
import re
import imaplib
import time

from io import BytesIO
from kittengroomer_email import KittenGroomerMail

# 15 uid move 904 "MISP"
_moveUID_request = re.compile(r'\A[A-Z]*[0-9]+\s(UID)|(uid)\s(move)|(MOVE)\s[0-9]+\s("MISP")')

def process(request, conn_server):
    str_request = request[1]

    # Email is moved to "MISP" folder using UID moved command
    if bool(_moveUID_request.search(str_request)):
        tag = request[0][0]
        command = request[0][1]
        uid_flag = request[0][2][1]
        flags = request[0][2][2:]
        str_flags = ' '.join(str(flag) for flag in flags)

        print("IN MISP MODULE: uid_flag ", uid_flag, " flags ", str_flags)