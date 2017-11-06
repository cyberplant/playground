#!/usr/bin/env python

import socket
import sys

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5.0)

server_address = ('192.168.17.145', 8266)

try:
    # Send data
    sent = sock.sendto(b'read\n', server_address)

    # Receive response
    data, server = sock.recvfrom(4096)
    print(data.decode("ascii"))
finally:
    sock.close()
