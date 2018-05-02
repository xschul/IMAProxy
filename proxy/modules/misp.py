import re

_moveUID_request = re.compile(r'\A[A-Z]*[0-9]+\s(uid)\s(move)\s[0-9]+\s("MISP")', flags=re.IGNORECASE)

def process(request, conn_server):
    str_request = request[1]

    # Email is moved to "MISP" folder using UID moved command
    if bool(_moveUID_request.search(str_request)):
        tag = request[0][0]
        command = request[0][1]
        uid_flag = request[0][2][1]
        flags = request[0][2][2:]
        str_flags = ' '.join(str(flag) for flag in flags)

        print("IN MISP MODULE: ", request[1])