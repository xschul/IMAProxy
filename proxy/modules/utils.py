""" Methods used by the modules """

def convert_uids_str_to_list(str_uids):
    """ Convert string of uids to a list of uids

        str_uids - uids of format "1:6" or "1,3:5" or "1,4"

    If str_uids = "1:10", return (1,2,3,4,5,6).
    If str_uids = "1,3:5", return (1,3,4,5).
    If str_uids = "1,4", return (1,4).
    """

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
    """ Return encoded email.

        uid - String containing the uid of the email;
        conn_server - Socket to the server;
        folder - Only necessary if uid_command is False (default: None);
        uid_command - True if command contains UID flag

    """

    if not uid_command: # without UID
        conn_server.select(folder)
        result, msg_data = conn_server.fetch(uid, 'BODY.PEEK[]')
    else: # UID method
        conn_server.state = 'SELECTED'
        result, msg_data = conn_server.uid('fetch', uid, 'BODY.PEEK[]')

    return msg_data[0][1]