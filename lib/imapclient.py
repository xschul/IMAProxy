from lib import imaplib_noCA as imaplib
import email
import sys

"""
IMAP library which is able to retrieve emails, move an email to another folder and download the attachments
"""
class IMAPClient:
    def __init__(self, hostname, username, password, verbose = False):
        self.verbose = verbose
        self.c = self.open_connection(hostname, username, password)

    def open_connection(self, hostname, username, password):
        ''' 
        Open a connection to a hostname with the identifiers (username, password) 
        '''

        # Connect to hostname
        if self.verbose:
            print('[INFO] Connecting to', hostname)

        connection = imaplib.IMAP4_SSL(hostname)    # --------- No certificat

        if self.verbose:
            print('[INFO] Logging in as', username)

        # Connect to account(username, password)
        try:
            connection.login(username, password)
            if self.verbose: 
                print('[INFO] Logged in')
        except Exception as err:
            print('[ERROR]', err)

        return connection

    def search_message_id(self, mailbox, uid):
        '''
        From a connection "c", search an email with the id "uid" inside the mailbox "mailbox"
        '''

        if self.verbose:
            print('[INFO] Searching message_id ', uid, ' into ', mailbox)

        self.c.select(mailbox, readonly=True)
        typ, msg_data = self.c.fetch(str(uid), '(BODY.PEEK[HEADER] FLAGS)')

        if msg_data != [b'The specified message set is invalid.']:
            if self.verbose: 
                print('[INFO] Message', uid, 'exists')
            return True
        else:
            if self.verbose: 
                print('[INFO] Message', uid, "doesn't exist")
            return False

    def create_quarantine(self):
        '''
        From a connection "c", create a folder named "Quarantine"
        '''

        typ, create_response = self.c.create('Quarantine')
        if self.verbose:
            print('[INFO] Quarantine:', create_response)

    def move_to_quarantine(self, src_mailbox, uid):
        '''
        From a connection "c", move the email insde "src_mailobx" with id "uid" to the folder "Quarantine"
        '''

        quar_mailbox = 'Quarantine'

        # Copy this email to Quarantine
        self.copy(uid, quar_mailbox)

        # Delete the email in the src_mailbox
        self.c.select(src_mailbox)

        # Current flags of uid
        if self.verbose: 
            typ, response = self.c.fetch(str(uid), '(FLAGS)')
            print('[INFO] Flags before:', response)

        # Add deleted flag for uid 
        typ, response = self.c.store(str(uid), '+FLAGS', "\\Deleted")
        if self.verbose:
            print('[INFO] Add deleted flag:', response)

        # New flags of uid
        if self.verbose:
            typ, response = self.c.fetch(str(uid), '(FLAGS)')
            print('[INFO] Flags after:', response)

        self.c.expunge()

    def copy(self, uid, dst_mailbox):
        '''
        From a connection "c", copy the email with id "uid" from the current mailbox to "dst_mailbox"
        '''

        self.c.copy(str(uid), dst_mailbox)
        if self.verbose:
            print('[INFO] Message', uid, 'copied in ', dst_mailbox)

    def download_attachments(self, uid, src_mailbox):
        '''
        STILL IN DEVELOPMENT
        From a connection "c", download the attachments of the email with id "uid" inside the "src_mailbox"
        '''

        self.c.select(src_mailbox)
        outputdir = "../../"

        resp, data = self.c.fetch(str(uid), "(BODY.PEEK[])")
        email_body = str(data[0][1])
        print(email_body)
        mail = email.message_from_string(email_body)
        print(mail.get_content_maintype())
        if not mail.is_multipart():
            if self.verbose:
                print("Not multipart")
            return
        for part in mail.walk():
            if self.verbose:
                print("Multipart")

            if part.get_content_maintype() != 'multipart' and part.get('Content-Disposition') is not None:
                open(outputdir + part.get_filename(), 'wb').write(part.get_payload(decode=True))

    def close(self):
        self.c.close()
        self.c.logout()