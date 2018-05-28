import re, imaplib, smtplib, email, email.mime.application, email.mime.multipart, email.mime.text
from email import policy
from email.message import EmailMessage
from io import BytesIO
from email import message_from_bytes
from .utils import parse_ids

MISP_FOLDER = '\"MISP\"'
DST_ADDR = 'mail2misp@freeblind.net'
#DST_ADDR = 'schul.x@hotmail.com'

Move = re.compile(r'\A(?P<tag>[A-Z0-9]+)'
    r'(\s(UID))?'
    r'\s(MOVE)'
    r'\s(?P<ids>[0-9:,]+)'
    r'\s' + re.escape(MISP_FOLDER), flags=re.IGNORECASE)

# Message data used to get the entire mail
MSG_DATA = 'BODY.PEEK[]'

def process(client):
    request = client.request
    match = Move.match(request)
    conn_server = client.conn_server
    folder = client.current_folder

    uidc = True if (('UID' in request) or ('uid' in request)) else False

    match = Move.match(request)
    if not match: return 
    ids = match.group('ids')

    
    if ids.isdigit():
        forward_to_misp(ids, conn_server, folder, uidc)
    else:
        # Multiple emails
        for id in parse_ids(ids):
            forward_to_misp(str(id), conn_server, folder, uidc)

def forward_to_misp(id, conn_server, folder, uidc):

    conn_server.select(folder)
    result, response = conn_server.uid('fetch', id, MSG_DATA) if uidc else conn_server.fetch(id, MSG_DATA)

    if result == 'OK' and response != [b'The specified message set is invalid.'] and response != [None]:
        print(response[0][1])
        bmail = message_from_bytes(response[0][1])
    else:
        return

    msg = EmailMessage()
    msg['Subject'] = 'IMAP proxy email'
    msg['From'] = 'mt2018pr@hotmail.com'
    msg['To'] = DST_ADDR

    msg.set_content("""m2m:attach_original_mail:1""")
    
    msg.add_attachment(bmail, filename='email.eml')    #  

    print(msg.as_string())

    s = smtplib.SMTP('freeblind.net')
    #s = smtplib.SMTP('imap-mail.outlook.com')
    #s.starttls()
    #s.login('mt2018pr@hotmail.com', 'ProxyImap')
    s.send_message(msg)
    s.quit()

    print('sent !')