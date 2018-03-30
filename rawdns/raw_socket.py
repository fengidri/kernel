# -*- coding:utf-8 -*-
#    author    :   丁雪峰
#    time      :   2018-03-29 16:19:52
#    email     :   fengidri@yeah.net
#    version   :   1.0.1

import socket
import struct

import time

import socket
import os
import struct
import StringIO
import re
import array
import socket
import struct
from random import randint

if struct.pack("H",1) == "\x00\x01": # big endian
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += "\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return s & 0xffff
else:
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += "\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return (((s>>8)&0xff)|s<<8) & 0xffff

# OCTET 1,2     ID
# OCTET 3,4    QR(1 bit) + OPCODE(4 bit)+ AA(1 bit) + TC(1 bit) + RD(1 bit)+ RA(1 bit) +
#         Z(3 bit) + RCODE(4 bit)
# OCTET 5,6    QDCOUNT
# OCTET 7,8    ANCOUNT
# OCTET 9,10    NSCOUNT
# OCTET 11,12    ARCOUNT

class DnsHeader:
    def __init__(self):
        self.id = os.getpid()
        self.bits = 0x0100 # recursion desired
        self.qdCount = 0
        self.anCount = 0
        self.nsCount = 0
        self.arCount = 0

    def toBinary(self):
        return struct.pack('!HHHHHH',
            self.id,
            self.bits,
            self.qdCount,
            self.anCount,
            self.nsCount,
            self.arCount);

class DnsQuestion:
    def __init__(self):
        self.labels = []
        self.qtype = 1  # A-record
        self.qclass = 1 # the Internet

    def toBinary(self):
        bin = '';
        for label in self.labels:
            assert len(label) <= 63
            bin += struct.pack('B', len(label))
            bin += label
        bin += '\0' # Labels terminator
        bin += struct.pack('!HH', self.qtype, self.qclass)
        return bin

class DnsPacket:
    def __init__(self, header = None):
        self.header = header
        self.questions = []
        self.answers = []

    def addQuestion(self, question):
        self.header.qdCount += 1
        self.questions.append(question)

    def toBinary(self):
        bin = self.header.toBinary()
        for question in self.questions:
            bin += question.toBinary()
        return bin




def dns(domain):
    header = DnsHeader()
    bin = header.toBinary()

    question = DnsQuestion()
    question.labels = domain.split('.')

    packet = DnsPacket(header)
    packet.addQuestion(question)

    return packet.toBinary()




class IP(object):
    def __init__(self, source, destination, payload='', proto=socket.IPPROTO_TCP):
        self.version  = 4
        self.ihl      = 5  # Internet Header Length
        self.tos      = 0  # Type of Service
        self.tl       = 0
        self.id       = randint(0, 65535)
        self.flags    = 0  # Don't fragment
        self.offset   = 0
        self.ttl      = 64
        self.protocol = proto
        self.checksum = 2  # will be filled by kernel

        self.source      = socket.inet_aton(source)
        self.destination = socket.inet_aton(destination)

    def pack(self):
        ver_ihl = (self.version << 4) + self.ihl
        flags_offset = (self.flags << 13) + self.offset
        ip_header = struct.pack("!BBHHHBBH4s4s",
                                ver_ihl,
                                self.tos,
                                self.tl,
                                self.id,
                                flags_offset,
                                self.ttl,
                                self.protocol,
                                self.checksum,
                                self.source,
                                self.destination)
        self.checksum = checksum(ip_header)
        ip_header = struct.pack("!BBHHHBBH4s4s",
                                ver_ihl,
                                self.tos,
                                self.tl,
                                self.id,
                                flags_offset,
                                self.ttl,
                                self.protocol,
                                socket.htons(self.checksum),
                                self.source,
                                self.destination)
        return ip_header


class UDP(object):
    def __init__(self, src, dst, payload=''):
        self.src      = src
        self.dst      = dst
        self.payload  = payload
        self.checksum = 0
        self.length   = 8  # UDP Header length

    def pack(self, src, dst, proto=socket.IPPROTO_UDP):
        length = self.length + len(self.payload)

        pseudo_header = struct.pack('!4s4s' 'HBB' 'HHHH',
                                    socket.inet_aton(src),
                                    socket.inet_aton(dst),
                                    length, 0, 0x11,
                                    self.src, self.dst, length, 0)
        sm =  checksum(pseudo_header + self.payload)
        return struct.pack('!HHHH', self.src, self.dst, length, sm)


def send(s, domain, dst, src):
    msg = dns(domain)

    port = randint(10240, 55535)

    udp = UDP(port, 53, msg).pack(src, dst)
    ip = IP(src, dst, udp, 17).pack()

    s.sendto(ip + udp + msg, (dst, port))




s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)


send(s, "b-yp-test.appsimg.com", "223.5.5.5", "10.0.2.15")

