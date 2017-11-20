#!/usr/bin/python

"""
Example to create a Mininet topology and connect it to the internet via NAT
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
