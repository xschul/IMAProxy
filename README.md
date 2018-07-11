# Python IMAP transparent proxy server

[![Build Status](https://travis-ci.org/xschul/IMAProxy.svg?branch=master)](https://travis-ci.org/xschul/IMAProxy)

Python IMAP4rev1 transparent proxy easy to modulate. 

A more advanced version is available in the [PyCIRCLeanIMAP](https://github.com/CIRCL/PyCIRCLeanIMAP) repository. It allows emails to be sanitized before being fetched by the user (using [PyCIRCLeanMail](https://github.com/CIRCL/PyCIRCLeanMail)) and transmits email to [MISP](https://github.com/misp).

## Features

* The proxy acts transparently and interprets every IMAP command
* Support TLS/SSL for both client and server connections
* Support IPv6
* Works with email applications as [Thunderbird](https://www.mozilla.org/en-US/thunderbird/) or [Outlook](https://outlook.live.com/owa/)
* Asynchronous, non-blocking socket connections
* Possibility to display IMAP payload
* Easy to modulate and to handle IMAP commands
* Extensions: [UIDPLUS](https://rfc-editor.org/rfc/rfc4315.txt), [MOVE](https://rfc-editor.org/rfc/rfc6851.txt), [ID](https://rfc-editor.org/rfc/rfc2971.txt), [UNSELECT](https://rfc-editor.org/rfc/rfc3691.txt), [CHILDREN](https://rfc-editor.org/rfc/rfc3348.txt) and [NAMESPACE](https://rfc-editor.org/rfc/rfc2342.txt).

## Installation and run

Clone this repository, install and run the proxy (sudo is required for some ports).

```
git clone https://github.com/xschul/IMAProxy.git
python3 IMAProxy/proxy/proxy.py -h
```

### Run with Thunderbird

First, open [Thunderbird](https://www.mozilla.org/en-US/thunderbird/), right-click on your email address and select "Settings". In "Server Settings", modify the "Server Name" by the IP address of the proxy (or localhost). That's it !

## Authors

* **Xavier Schul**
* **CIRCL** - *Computer Incident Response Center Luxembourg* - [CIRCL](https://www.circl.lu/)
