#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import Intf

class NetworkTopo( Topo ):

    def build( self, **_opts ):

        user1_ip = '10.0.0.2'
        proxy_ip = '10.0.0.1'

        user1 = self.addNode( 'u1' )
        user2 = self.addNode( 'u2' )
        proxy = self.addNode( 'p1' )

        switch= self.addSwitch('s1')

        self.addLink(user1, proxy)
        self.addLink(user2, proxy)
        #self.addLink(proxy, switch)

def start_commands(net):
    u1 = net.get('u1')
    u2 = net.get('u2')
    p1 = net.get('p1')
    s1 = net.get('s1')
    Intf( 'eth0', node=s1 )

    s1.cmd( 'sysctl net.ipv4.ip_forward=1' )
    u1.cmd( 'sysctl net.ipv4.ip_forward=1' )
    u2.cmd( 'sysctl net.ipv4.ip_forward=1' )
    p1.cmd( 'sysctl net.ipv4.ip_forward=1' )

    # Clean tables
    s1.cmd( 'iptables -F')
    s1.cmd( 'iptables -t nat -F')

    '''s1.cmd( 'iptables -A INPUT -p tcp -j DROP' )
    s1.cmd( 'iptables -A FORWARD -p tcp -j DROP' )
    s1.cmd( 'iptables -A OUTPUT -p tcp -j DROP' )'''

    # Redirection
    s1.cmd( 'iptables -t nat -A PREROUTING -p tcp --dport 1030 -j DNAT --to-destination 10.0.0.1:1030' )
    s1.cmd( 'iptables -t nat -A POSTROUTING -j MASQUERADE' )

    # Clean tables
    u2.cmd( 'iptables -F')
    u2.cmd( 'iptables -t nat -F')

    # Redirection
    u2.cmd( 'iptables -t nat -A PREROUTING -p tcp --dport 1030 -j DNAT --to-destination 10.0.0.1:1030' )
    u2.cmd( 'iptables -t nat -A POSTROUTING -j MASQUERADE' )

def run():
    "Test linux router"
    topo = NetworkTopo()
    net = Mininet( topo=topo )  

    net.start()
    start_commands(net)
    
    #u1.cmdPrint('dhclient '+u1.defaultIntf().name)

    CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()
