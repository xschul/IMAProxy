import imaplib, email, sys, argparse

""" Tests for proxy.py """

def run_tests(conn_proxy, username, password):
    test_mesg = ('From: IMAP proxy\nSubject: IMAP4 test\n\nEmail generated by ' \
                + 'IMAProxy tests\n').encode()
    test_seq1 = (
        ('login', (username, password)),
        ('create', ('tmp/xxx',)),
        ('rename', ('tmp/xxx', 'tmp/yyy')),
        ('CREATE', ('tmp/yyz',)),
        ('append', ('tmp/yyz', None, None, test_mesg)),
        ('list', ('tmp', 'yy*')),
        ('select', ('tmp/yyz',)),
        ('search', (None, 'SUBJECT', 'test')),
        ('fetch', ('1', '(FLAGS INTERNALDATE RFC822)')),
        ('uid', ('SEARCH', 'ALL')),
        ('response', ('EXISTS',)),
        ('store', ('1', 'FLAGS', '(\Deleted)')),
        ('namespace', ()),
        ('expunge', ()),
        ('recent', ()),
        ('response',('UIDVALIDITY',)),
        ('uid', ('SEARCH', 'ALL')),
        ('response', ('EXISTS',)),
        ('recent', ()),
        ('close', ()),
        ('delete', ('tmp/yyz',)),
        ('DELETE', ('tmp/yyy',)),
        ('logout', ()))

    failed_tests = []

    def run(cmd, args):
        print("["+cmd+"]")
        typ, dat = getattr(conn_proxy, cmd)(*args)
        print(typ)
        
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

    # Display results
    if not failed_tests:
        print('TESTS SUCCEEDED')
    else:
        print('SOME TESTS FAILED:')
        for test in failed_tests:
            print(test)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='Email address of the user')
    parser.add_argument('password', help='Password of the user')
    parser.add_argument('ip_proxy', help='Ip address of the proxy')
    parser.add_argument('-s', '--ssl', help='Enable SSL/TLS connection')
    parser.add_argument('-p', '--port', type=int, help='Talk on the given port (Default: 143 or 993 with SSL/TLS enabled)')
    args = parser.parse_args()

    try:
        if args.ssl:
            if args.port:
                run_tests(imaplib.IMAP4_SSL(args.ip_proxy, args.port), args.username, args.password)
            else:
                run_tests(imaplib.IMAP4_SSL(args.ip_proxy), args.username, args.password)

        else:
            if args.port:
                run_tests(imaplib.IMAP4(args.ip_proxy, args.port), args.username, args.password)
            else:
                run_tests(imaplib.IMAP4(args.ip_proxy), args.username, args.password)
    except ConnectionRefusedError:
        print('Port blocked')
    