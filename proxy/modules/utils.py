def convert_uids_str_to_list(str_uids):
    uids = []
    raw_uids = str_uids.split(',')

    # Get the uids
    for u in raw_uids:
        if ':' in u:
            (start, end) = u.split(':')
            [uids.append(uid) for uid in range(int(start), int(end)+1)]
        else:
            uids.append(int(u))

    return uids

def fetch(uid, conn_server, folder=None, uid_command=True):
    if not uid_command: # without UID
        conn_server.select(folder)
        result, msg_data = conn_server.fetch(uid, 'BODY.PEEK[]')
    else: # UID method
        conn_server.state = 'SELECTED'
        result, msg_data = conn_server.uid('fetch', uid, 'BODY.PEEK[]')

    if not msg_data[0]: # Email no longer exists
        return None

    return msg_data[0][1]