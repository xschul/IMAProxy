# Python IMAP transparent proxy server

Complete IMAP Transparent Proxy easy to modulate.

## Features

* The proxy acts transparently and interprets every IMAP command
* Support TLS/SSL for both client and server connections
* Works with email applications as [Thunderbird](https://www.mozilla.org/en-US/thunderbird/), [Outlook](https://outlook.live.com/owa/)
* Asynchronous, non-blocking socket connections
* Possibility to display IMAP payload
* Easy to modulate and to handle IMAP commands

## Integrated modules

Modules are easy to integrated and easy to remove (just remove their calls in the proxy.py file).

* Sanitize emails and keep a copy in a Quarantine folder using the [PyCIRCLeanMail](https://github.com/CIRCL/PyCIRCLeanMail)
* Forward emails to [MISP](https://github.com/misp)

## Installation and run

Clone this repository, install and run the proxy.

```
git clone https://github.com/xschul/IMAProxy.git
cd IMAProxy
pip3 install -r requirements.txt
python3 proxy/proxy.py -h
```

### Run with Thunderbird

First, open [Thunderbird](https://www.mozilla.org/en-US/thunderbird/), right-click on your email address and select "Settings". In "Server Settings", modify the "Server Name" by the IP address of the proxy.

### Run the tests

```
python3 tests/test_proxy.py -h
python3 tests/test_proxy.py $username $password $ip_proxy
python3 tests/test_sanitizer.py -h
python3 tests/test_sanitizer.py $username $password $ip_proxy
```

## Authors

* **Xavier Schul**
* **CIRCL** - *Computer Incident Response Center Luxembourg* - [CIRCL](https://www.circl.lu/)