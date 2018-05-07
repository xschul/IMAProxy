import re
from .utils import convert_uids_str_to_list, fetch

MISP_FOLDER = 'Misp'

UID_Move = re.compile(r'\A(?P<tag>[A-Z]*[0-9]+)'
    r'\s(UID)'
    r'\s(MOVE)'
    r'\s(?P<uid>[0-9]+)'
    r'\s' + re.escape(MISP_FOLDER), flags=re.IGNORECASE)

Move = re.compile(r'\A(?P<tag>[A-Z]*[0-9]+)'
    r'\s(MOVE)'
    r'\s(?P<uid>[0-9]+)'
    r'\s' + re.escape(MISP_FOLDER), flags=re.IGNORECASE)

def process(request, IMAP_client):
    match = Move.match(request)
    match_uid = UID_Move.match(request)
    uid_command = False

    # Email is moved to "MISP" folder using UID moved command
    if match:
        tag = match.group('tag')
    elif match_uid:
        tag = match_uid.group('tag')
        uid = match_uid.group('uid')
        uid_command = True
    else:
        return

    conn_server = IMAP_client.conn_server
    folder = IMAP_client.current_folder

    if uid.isdigit():
        forward_to_misp(uid, conn_server, folder, uid_command)
    else:
        uids = convert_uids_str_to_list(uid)
        for uid in uids:
            forward_to_misp(uid, conn_server, folder, uid_command)

def forward_to_misp(uid, conn_server, folder, uid_command):
    bmail = fetch(uid, conn_server, folder, uid_command)