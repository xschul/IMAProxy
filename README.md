# Python IMAP proxy server

IMAP Proxy to sanitize attachments.

## Features

* The proxy acts transparently and interprets every IMAP command
* Support TLS/SSL for both client and server connections
* Works with email application [Thunderbird](https://www.mozilla.org/en-US/thunderbird/)
* Multiple tests
* Asynchronous, non-blocking socket connections
* Possibility to display IMAP payload
* **[TODO]** Inspect emails, sanitize the malicious ones and keep a copy in a Quarantine folder
* **[TODO]** Make it compatible with Gmail accounts (OAUTH2 authenticate)
* Proxy detects the hostname requested from the user's account (works with Hotmail, Outlook, Yahoo)

## Try it using Mininet

Mininet creates a realistic virtual network, running real kernel, switch and application code, on a single machine (VM, cloud or native), in seconds, with a single command.

If you want to try this implementation in this virtualized environment, you can download and install a Mininet VM. A tutorial can be found [here](http://mininet.org/download/#option-1-mininet-vm-installation-easy-recommended). Then, if you want to use Wireshark or other tools with a GUI, I suggest you using a graphical interface inside the VM (installation tutorial available [here](https://github.com/mininet/mininet/wiki/FAQ#vm-console-gui)).

### Installation

Clone this repository in the mininet folder.

```
cd /home/mininet/mininet/
git clone https://github.com/xschul/IMAProxy.git
```

### Run the network

You can create the network using:

```
cd IMAProxy/
sudo python topo.py
```

Three hosts (h1, h2 and h3) are connected to a linux router (r0). In this topology, we will consider h1 as the proxy and h2 as the user.

### Run the proxy

First, start the proxy on h1. Then, you can launch [Thunderbird](https://www.mozilla.org/en-US/thunderbird/) on the host h2 or you can run the tests:

```
h1 python3 proxy.py
h2 python3 tests.py $userAccount $password
```

## Built With

* [Python3](https://www.python.org/download/releases/3.0/)
* [imaplib](https://docs.python.org/2/library/imaplib.html) - IMAP4 protocol client
* [Mininet](https://http://mininet.org/) - Virtual network

## Authors

* **Xavier Schul**
* **CIRCL** - *Computer Incident Response Center Luxembourg* - [CIRCL](https://www.circl.lu/)

