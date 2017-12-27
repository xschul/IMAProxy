# IMAP Proxy

Imap Proxy to sanitize attachments.

## Getting Started

This project runs with Python 3 and virtualizes a network using [Mininet](http://mininet.org/). 

### Installing

First, you have to download and install a Mininet VM. A tutorial can be found [here](http://mininet.org/download/#option-1-mininet-vm-installation-easy-recommended). Then, if you want to use Wireshark or other tools with a GUI, I suggest you using a graphical interface inside the VM (installation tutorial available [here](https://github.com/mininet/mininet/wiki/FAQ#vm-console-gui)).

## Running

### Run the network

First, clone this repository in the mininet folder.

```
cd /home/mininet/mininet/
git clone https://github.com/xschul/IMAProxy.git
```

Now, you can create the network using:

```
cd IMAProxy/
sudo python topo.py
```

Three hosts (h1, h2 and h3) are connected to a linux router (r0). In this topology, we will consider h3 as the proxy and h1 and2 as the users.

If you want to retrieve emails from h2, use:

```
h2 python3 imapcommands.py $hotmailAccount $password
```

At this moment, the main method of this script fetches the second email inside the "INBOX" folder of the account. This script won't work with a gmail account as it needs an additional security with Oauth.

The requests will be redirected to h3 (the proxy) but this proxy doesn't work yet.

## Built With

* [Python](https://www.python.org/download/releases/3.0/) - Python 3.0
* [imaplib](https://docs.python.org/2/library/imaplib.html) - IMAP4 protocol client
* [Mininet](https://http://mininet.org/) - Virtual network
* [iptables](http://ipset.netfilter.org/iptables.man.html) - Administration tool for IPv4 packet filtering and NAT   

## Authors

* **Xavier Schul** - *UCL Student*
* **CIRCL** - *Computer Incident Response Center Luxembourg* - [CIRCL](https://www.circl.lu/)

