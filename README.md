# Python IMAP proxy server

IMAP Proxy to sanitize attachments.

## Features

* The proxy acts transparently and interprets every IMAP command
* Support TLS/SSL for both client and server connections
* Works with email application [Thunderbird](https://www.mozilla.org/en-US/thunderbird/)
* Asynchronous, non-blocking socket connections
* Possibility to display IMAP payload
* Sanitize emails and keep a copy in a Quarantine folder

## Installation and run

Clone this repository, install and run the proxy.

```
git clone https://github.com/xschul/IMAProxy.git
pip3 install -r requirements.txt
python3 proxy/proxy.py
```

### Run with Thunderbird

First, open [Thunderbird](https://www.mozilla.org/en-US/thunderbird/), right-click on your email address and select "Settings". In "Server Settings", modify the "Server Name" by the IP address of the proxy.

### Run the tests

```
python3 tests/test.py $userAccount $password $ip_proxy
```

## Built With

* [Python3.6](https://www.python.org/download/releases/3.0/)
* [imaplib](https://docs.python.org/2/library/imaplib.html) - IMAP4 protocol client

## Authors

* **Xavier Schul**
* **CIRCL** - *Computer Incident Response Center Luxembourg* - [CIRCL](https://www.circl.lu/)

