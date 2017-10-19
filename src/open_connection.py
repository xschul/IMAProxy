import imaplib
from pprint import pprint


def open_connection(verbose=False):
    """ Return connection (UNSECURED FOR NOW)
    """

    hostname = 'imap-mail.outlook.com'

    if verbose:
        print('Connecting to', hostname)
    connection = imaplib.IMAP4_SSL(hostname)

    # Login to our account
    username = 'mt2017pr@hotmail.com'
    password = 'ImapProxy'
    if verbose:
        print('Logging in as', username)
    connection.login(username, password)
    return connection

if __name__ == '__main__':
    with open_connection(verbose=True) as c:
        print(c)