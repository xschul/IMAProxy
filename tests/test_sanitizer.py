import imaplib, email, sys, argparse

""" Tests for proxy.py combined with the PyCIRCLeanMail module """

def run_tests(conn_proxy, username, password):
    test_mesg = ('From: IMAP proxy\nSubject: IMAP4 test\n\nEmail generated by ' \
                + 'IMAProxy + PyCIRCLeanMail tests\n').encode()
    test_seq1 = (
        ('login', (username, password)),
        ('create', ('/tmp/xxx',)),
        ('append', ('/tmp/xxx', None, None, test_mesg)),
        ('select', ('/tmp/xxx',)),
        ('search', (None, 'SUBJECT', 'test')),
        ('fetch', ('1', '(FLAGS INTERNALDATE RFC822)')),
        ('uid', ('SEARCH', 'ALL')),
        ('response', ('EXISTS',)),
        ('select', ('Quarantine',)),
        ('uid', ('SEARCH', 'ALL')),
        ('response', ('EXISTS',)),
        ('expunge', ()),
        ('delete', ('/tmp/xxx',)),
        ('logout', ()))

    failed_tests = []

    def run(cmd, args):
        print("["+cmd+"]")
        typ, dat = getattr(conn_proxy, cmd)(*args)
        
        if typ == 'NO': 
            failed_tests.append('%s => %s %s' % (cmd, typ, dat))

        return dat

    for cmd,args in test_seq1:
        dat = run(cmd, args)

        if (cmd,args) != ('uid', ('SEARCH', 'ALL')):
            continue

        uid = dat[-1].split()
        if not uid: 
            continue

        # uid[-1] is the last email received
        result = run('uid', ('FETCH', '%s' % uid[-1].decode(),
                '(FLAGS INTERNALDATE RFC822.SIZE RFC822.HEADER RFC822.TEXT)'))
        mail = result[0][1]
        if 'CIRCL-Sanitizer' not in mail.decode():
            failed_tests.append('Email not sanitized')
        else:
            run('uid', ('STORE', '%s' % uid[-1].decode(), '+FLAGS', '(\Deleted)'))

    # Display results
    if not failed_tests:
        print('TESTS SUCCEEDED')
    else:
        print('SOME TESTS FAILED:')
        for test in failed_tests:
            print(test)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='Email address of the user')
    parser.add_argument('password', help='Password of the user')
    parser.add_argument('ip_proxy', help='Ip address of the proxy')
    args = parser.parse_args()

    try:
        print("Try to connect to the proxy without SSL/TLS")
        run_tests(imaplib.IMAP4(args.ip_proxy), args.username, args.password)
    except ConnectionRefusedError:
        print("Port 143 blocked")
        print("Try to connect to the proxy with SSL/TLS")
        try:
            run_tests(imaplib.IMAP4_SSL(args.ip_proxy), args.username, args.password)
        except ConnectionRefusedError:
            print("Ports 143 and 993 blocked")
            print("Please verify if the proxy on ports 143/993 are up")
    