# -*- coding:utf-8 -*-
#    author    :   丁雪峰
#    time      :   2018-03-29 16:19:52
#    email     :   fengidri@yeah.net
#    version   :   1.0.1

import socket
import struct


import socket
import struct
import StringIO
import re
import array
import socket
import struct
from random import randint


class DnsResourceRecord:
	pass

class DnsAnswer(DnsResourceRecord):
	pass

class BinReader(StringIO.StringIO):
	def unpack(self, fmt):
		size = struct.calcsize(fmt)
		bin = self.read(size)
		print bin.encode('hex')
		return struct.unpack(fmt, bin)

class DnsPacketConverter:
	def fromBinary(self, bin):
		reader = BinReader(bin)
		header = DnsHeader().fromBinary(reader)
		packet = DnsPacket(header)
		for qi in range(header.qdCount):
			q = self.readQuestion(reader)
			packet.questions.append(q)
		for ai in range(header.anCount):
			a = self.readAnswer(reader)
			packet.answers.append(a)
		return packet
	def readQuestion(self, reader):
		question = DnsQuestion()
		question.labels = self.readLabels(reader)
		(question.qtype, question.qclass) = reader.unpack('!HH')
		return question
	def readAnswer(self, reader):
		print "reading answer"
		answer = DnsAnswer()
		answer.name = self.readLabels(reader)
		(type, rrclass, ttl, rdlength) = reader.unpack('!HHiH')
		answer.rdata = reader.read(rdlength)
		print answer.rdata
	def readLabels(self, reader):
		labels = []
		while True:
			(length,) = reader.unpack('B')
			if length == 0: break

			# Compression
			compressionMask = 0b11000000;
			if length & compressionMask:
				byte1 = length & ~compressionMask;
				(byte2,) = reader.unpack('B')
				offset = byte1 << 8 | byte2
				oldPosition = reader.tell()
				result = self.readLabels(reader)
				reader.seek(oldPosition)
				return result

			label = reader.read(length)
			labels.append(label)
		return labels
	



# OCTET 1,2 	ID
# OCTET 3,4	QR(1 bit) + OPCODE(4 bit)+ AA(1 bit) + TC(1 bit) + RD(1 bit)+ RA(1 bit) +
# 		Z(3 bit) + RCODE(4 bit)
# OCTET 5,6	QDCOUNT
# OCTET 7,8	ANCOUNT	
# OCTET 9,10	NSCOUNT	
# OCTET 11,12	ARCOUNT

class DnsHeader:
	def __init__(self):
		self.id = 0x1234
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
	def fromBinary(self, bin):
		if bin.read:
			bin = bin.read(12)
		(self.id,
		 self.bits,
		 self.qdCount,
		 self.anCount,
		 self.nsCount,
		 self.arCount) = struct.unpack('!HHHHHH', bin)
		return self

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
	def __repr__(self):
		return '<DnsPacket %s>' % (self.header)



def dns(domain, dst = None):
	header = DnsHeader()
	bin = header.toBinary()
	print 'header', bin.encode('hex')

	question = DnsQuestion()
	question.labels = domain.split('.')
	print 'question', question.toBinary().encode('hex')

	packet = DnsPacket(header)
	packet.addQuestion(question)
	print 'packet', packet.toBinary().encode('hex')

        return packet.toBinary()

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	# dest = ('127.0.0.1', 5353)
	dest = (dst, 53)
        sock.bind(('0.0.0.0', 3456))
	sock.sendto(packet.toBinary(), dest)
	(response, address) = sock.recvfrom(1024)
	print 'respon', response.encode('hex')

	conv = DnsPacketConverter()
	packet = conv.fromBinary(response)
	print packet
def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)







def checksum(data):
    s = 0
    n = len(data) % 2
    for i in range(0, len(data) - n, 2):
        s += ord(data[i]) + (ord(data[i + 1]) << 8)
    if n:
        s += ord(data[i + 1])
    while (s >> 16):
        s = (s & 0xFFFF) + (s >> 16)
    s = ~s & 0xffff
    return s

def checksum(msg):
    s = 0
    for i in range(0, len(msg), 2):
        w = (ord(msg[i]) << 8 ) + ord(msg[i+1])
        s = carry_around_add(s, w)
    return ~s & 0xffff


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

class IP(object):
    def __init__(self, source, destination, payload='', proto=socket.IPPROTO_TCP):
        self.version = 4
        self.ihl = 5  # Internet Header Length
        self.tos = 0  # Type of Service
        #self.tl = 20 + len(payload)
        self.tl = 0
        self.id = 0x3205# random.randint(0, 65535)
        self.flags = 0  # Don't fragment
        self.offset = 0
        self.ttl = 64
        self.protocol = proto
        self.checksum = 2  # will be filled by kernel
        self.source = socket.inet_aton(source)
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
    # def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.payload = payload
        self.checksum = 0
        self.length = 8  # UDP Header length

    def pack(self, src, dst, proto=socket.IPPROTO_UDP):
        length = self.length + len(self.payload)
        pseudo_header = struct.pack('!4s4s' 'HBB' 'HHHH',
                                    socket.inet_aton(src),
                                    socket.inet_aton(dst),
                                    length, 0, 0x11,
                                    self.src, self.dst, length, 0
                                    )
        sm =  checksum(pseudo_header + self.payload)
        return struct.pack('!HHHH',
                 self.src, self.dst, length, sm)




src = '10.0.2.15'
dst = '114.114.114.114'
dst = '223.5.5.5'
port =3456
msg = dns("baidu.com", dst)

udp = UDP(port, 53, msg).pack(src, dst)
ip = IP(src, dst, udp, 17).pack()


s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
s.sendto(ip + udp + msg, ('', port))
#s.sendto(ip + udp + msg, (dst, port))
