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

Three hosts (h1, h2 and h3) are connected to a linux router (r0). In this topology, we will consider h1 as the proxy and h2 as the user.

First, start the proxy on h1:

```
h1 python3 proxy.py
```

If you want to retrieve the first email inside your INBOX:

```
h2 python3 client.py $outlookAccount $password
```

With these commands, every requests from h2 will be send to h1. Then, h1 will transmit these requests to "imap-mail.outlook.com" and send the reponses back to h2.

## Built With

* [Python](https://www.python.org/download/releases/3.0/) - Python 3.0
* [imaplib](https://docs.python.org/2/library/imaplib.html) - IMAP4 protocol client
* [Mininet](https://http://mininet.org/) - Virtual network
* [iptables](http://ipset.netfilter.org/iptables.man.html) - Administration tool for IPv4 packet filtering and NAT   

## Authors

* **Xavier Schul** - *UCL Student*
* **CIRCL** - *Computer Incident Response Center Luxembourg* - [CIRCL](https://www.circl.lu/)

