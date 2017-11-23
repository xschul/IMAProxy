#!/usr/bin/python

"""
Mininet topology connected to the internet via NAT
This topology is composed by 2 hosts (h1 and h2) linked to a switch (s1)
h1 (10.0.0.1) is considered as the proxy and h2 (10.0.0.2) as the user.
"""

from mininet.cli import CLI
from mininet.log import lg
from mininet.topolib import TreeNet

if __name__ == '__main__':
    lg.setLogLevel( 'info')
    net = TreeNet( depth=1, fanout=2 )
    # Add NAT connectivity
    net.addNAT().configDefault()
    net.start()
    
    h1 = net.get('h1') 
    h2 = net.get('h2')  
    #h1.cmd('sudo python3 /home/mininet/mininet/IMAProxy/hosts/proxy.py &')

    CLI( net )
    # Shut down NAT
    net.stop()
