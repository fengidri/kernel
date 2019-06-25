# -*- coding: utf-8 -*
'''
	A very simple raw socket implementation in Python
'''

import os
import sys, socket
from struct import *
import random
import time


class g:
    via = None
    raw = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                socket.IPPROTO_RAW)

def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def checksum(msg):
    s = 0
    for i in range(0, len(msg), 2):
        w = (ord(msg[i]) << 8 ) + ord(msg[i+1])
        s = carry_around_add(s, w)
    return ~s & 0xffff




class PacketIP(object):
    def __init__(self, packet = None):

        if packet:
            self.ip_decode(packet)

    def ip_decode(self, packet):
        res = unpack('!BBHHHBBH4s4s', packet[14:34])

        t     = res[0]
        self.ip_dscp        = res[1]
        self.ip_total_len   = res[2]
        self.ip_id          = res[3]
        self.ip_frag_offset = res[4]
        self.ip_ttl         = res[5]
        self.ip_protocol    = res[6]
        self.ip_checksum    = res[7]
        self.ip_saddr       = res[8]
        self.ip_daddr       = res[9]

        self.ip_saddr = socket.inet_ntoa(self.ip_saddr)
        self.ip_daddr = socket.inet_ntoa(self.ip_daddr)

        self.ip_ver = t >> 4
        self.ip_hl  = (t << 4) >> 4

    def ip(self, src, dst):
        self.saddr = src
        self.daddr = dst
        ip_saddr = socket.inet_pton(socket.AF_INET, src)	# 两边的ip地址
        ip_daddr = socket.inet_pton(socket.AF_INET, dst)

        self.ip_src = ip_saddr
        self.ip_dst = ip_daddr

    def ip_packet(self, protocol, length = 0):
        ip_ver = 4			# ipv4
        ip_ihl = 5			# Header Length =5, 表示无options部分
        ip_dscp = 0			# 以前叫tos，现在叫dscp
        ip_total_len = 0		# left for kernel to fill
        ip_id = 22222			# fragment相关，随便写个
        ip_frag_offset = 0		# fragment相关
        ip_ttl = 255			# *nix下TTL一般是255
        ip_protocol = protocol	# 表示后面接的是tcp数据
        ip_checksum = 0			# left for kernel to fill

        ip_ver_ihl = (ip_ver << 4) + ip_ihl	# 俩4-bit数据合并成一个字节

        # 按上面描述的结构，构建ip header。
        return pack('!BBHHHBBH4s4s' , ip_ver_ihl, ip_dscp,
                ip_total_len, ip_id, ip_frag_offset, ip_ttl,
                ip_protocol, ip_checksum, self.ip_src, self.ip_dst)

    def send(self):

        if g.via:
            via = g.via
        else:
            via = self.daddr

        msg = self.packet()
        g.raw.sendto(msg, (via, 0))


class PacketICMP(PacketIP):
    def __init__(self, packet = None):
        PacketIP.__init__(self, packet)

    def packet(self):

        cs = 0
        mtu = 1000

        packet = pack('!BBHI', 2, 0, cs, mtu)
        cs = checksum(packet)
        packet = pack('!BBHI', 2, 0, cs, mtu)

        ip_header = self.ip_packet(socket.IPPROTO_ICMP)
        return ip_header + packet




class PacketTcp(PacketIP):
    def __init__(self, packet = None):
        PacketIP.__init__(self, packet)

        self.ip_header = None
        self.tcp_header = None
        self.mss = 1460
        self.payload = ''
        self.sack = []

        self.ip_protocol = socket.IPPROTO_TCP

        self.tcp_flag_urg = 0
        self.tcp_flag_ack = 0
        self.tcp_flag_psh = 0
        self.tcp_flag_rst = 0
        self.tcp_flag_syn = 0
        self.tcp_flag_fin = 0

        self.tcp_seq = 0	# 32-bit sequence number，这里随便指定个
        self.tcp_ack_seq = 0	# 32-bit ACK number。这里不准备构建ack包，故设为0

        if packet:
            self.decode_tcp(packet)


    def decode_tcp(self, packet):
        res = unpack('!HHLLBBHHH' , packet[34:54])

        self.tcp_sport         = res[0]
        self.tcp_dport         = res[1]
        self.tcp_seq           = res[2]
        self.tcp_ack_seq       = res[3]
        self.tcp_offset_reserv = res[4]
        self.tcp_flags         = res[5]
        self.tcp_window_size   = res[6]
        self.tcp_checksum      = res[7]
        self.tcp_urgent_ptr    = res[8]

        l = (self.tcp_offset_reserv >> 4) * 4
        self.payload_size = len(packet) - 34 - l

        self.tcp_flag_fin = self.tcp_flags & 0x1
        self.tcp_flag_syn = self.tcp_flags & 0x2
        self.tcp_flag_rst = self.tcp_flags & 0x4
        self.tcp_flag_rst = self.tcp_flags & 0x8
        self.tcp_flag_psh = self.tcp_flags & 0x16
        self.tcp_flag_ack = self.tcp_flags & 0x32
        self.tcp_flag_urg = self.tcp_flags & 0x64




    def tcp(self, sport, dport, payload = ''):
        self.tcp_sport = sport
        self.tcp_dport = dport
        self.payload   = payload

    def tcp_checksum(self, payload):
        tcp_header = self.tcp_gen_header(0)

        psh_reserved = 0
        psh_protocol = self.ip_protocol
        psh_tcp_len = len(tcp_header) + len(payload)

        psh = pack('!4s4sBBH',
                self.ip_src,
                self.ip_dst,
                psh_reserved,
                psh_protocol,
                psh_tcp_len)

        chk = psh + tcp_header + payload

        # 必要时追加1字节的padding
        if len(chk) % 2 != 0:
        	chk += '\0'

        tcp_checksum = checksum(chk)
        return tcp_checksum

    def tcp_gen_header(self, tcp_checksum = 0):
        tcp_window_size = 229
        tcp_urgent_ptr = 0
        tcp_data_offset = 5	# 和ip header一样，没option field

        tcp_flag_urg = self.tcp_flag_urg
        tcp_flag_ack = self.tcp_flag_ack
        tcp_flag_psh = self.tcp_flag_psh
        tcp_flag_rst = self.tcp_flag_rst
        tcp_flag_syn = self.tcp_flag_syn
        tcp_flag_fin = self.tcp_flag_fin

        tcp_ack_seq  = self.tcp_ack_seq
        tcp_seq      = self.tcp_seq
        tcp_ack_seq  = self.tcp_ack_seq


        opts = self.tcp_opts()
        opts_l = len(opts) / 4 * 4
        if opts_l < len(opts):
            opts_l += 4
            opts += '\0' * (opts_l - len(opts))

        # 继续合并small fields
        tcp_offset_reserv = (((len(opts) + 20 )/4)  << 4)
        tcp_flags = tcp_flag_fin + \
                (tcp_flag_syn << 1) + \
                (tcp_flag_rst << 2) + \
                (tcp_flag_psh <<3) + \
                (tcp_flag_ack << 4) + \
                (tcp_flag_urg << 5)

        # 按上面描述的结构，构建tcp header。
        tcp_header = pack('!HHLLBBHHH' , self.tcp_sport, self.tcp_dport,
                tcp_seq,
                tcp_ack_seq, tcp_offset_reserv, tcp_flags,
                tcp_window_size, tcp_checksum, tcp_urgent_ptr)

        tcp_header += opts
        return tcp_header

    def tcp_opts(self):
        opts = ''
        if self.tcp_flag_syn:
            """truct tcp_option_mss {
                  uint8_t kind; /* 2 */
                  uint8_t len; /* 4 */
                  uint16_t mss;
              } __attribute__((packed));
            """
            # mss
            opts += pack('!BBH', 2, 4, self.mss)

            #  window scale
            opts += pack('!BBBB', 3, 3, 7, 1)



            ## sack perm
            #opts += pack('!BB', 4, 2)



        # sack
        if self.sack:
            # nop
            opts += pack('!BB', 1, 1)
            opts += pack('!BB', 5, len(self.sack) * 2 * 4 + 2)

            for s, e in self.sack:
                opts += pack('!II', s, e)

        return opts



    def packet(self):
        ip_header = self.ip_packet(socket.IPPROTO_TCP)

        tcp_checksum = self.tcp_checksum(self.payload)

        tcp_header = self.tcp_gen_header(tcp_checksum)

        # 最终的tcp/ip packet！
        return ip_header + tcp_header + self.payload



class TcpCon(object):
    def __init__(self, saddr, sport, daddr, dport, net):
        self.l_seq_num = 0
        self.p_seq_num = None
        self.mss = 48

        if not sport:
            sport = int(random.random() * 65535)
            print "local port: %d" % sport

        cmd = 'iptables -A INPUT -p tcp --sport %s -s %s -j DROP'
        cmd = cmd % (dport, daddr)
        os.system(cmd)

        self.saddr = saddr
        self.sport = sport
        self.daddr = daddr
        self.dport = dport

        self.recv = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                socket.htons(0x800))

        self.recv.bind((net, 0))

    def mk_packet(self, payload = ''):
        p = PacketTcp()
        p.mss = self.mss

        if self.p_seq_num:
            p.tcp_ack_seq = self.p_seq_num + 1
            p.tcp_flag_ack = 1
        else:
            p.tcp_flag_syn = 1

        p.tcp_seq = self.l_seq_num

        p.ip(self.saddr, self.daddr)
        p.tcp(self.sport, self.dport, payload)

        return p

    def send_packet(self, packet):
        packet.send()


    def _send(self, payload = ''):
        p = self.mk_packet(payload)

        p.send()

        self.l_seq_num += len(payload)

        if p.tcp_flag_syn:
            self.l_seq_num += 1

        if p.tcp_flag_fin:
            self.l_seq_num += 1

    def wait_one(self):
        s = time.time()
        while True:
            if time.time() - s > 3:
                break

            pa =  self.recv.recv(1024)
            packet = PacketTcp(pa)
            if packet.ip_saddr == self.daddr and packet.tcp_dport == self.sport:
                print packet.tcp_seq, packet.payload_size
                if packet.tcp_seq > self.p_seq_num:
                    self.p_seq_num = packet.tcp_seq + packet.payload_size - 1

                    if packet.tcp_flag_syn:
                        self.p_seq_num += 1
                    if packet.tcp_flag_fin:
                        self.p_seq_num += 1

                    print self.p_seq_num

                return packet

    def wait_n(self, n):
        for i in range(n):
            if not self.wait_one():
                break


    def connect(self):
        self._send()

        self.wait_one()

        self._send()

    def write(self, data):
        i = 0
        while True:
            d = data[i: i + 8]
            if not d:
                break
            i += 8

            self._send(d)



http_request = "GET /1M HTTP/1.1\r\n" \
        "Host: test.com\r\n" \
        "Accept: */*\r\n" \
        "\r\n"



def main():
    #g.via = '10.0.0.130'

    saddr = sys.argv[1]
    sport = int(sys.argv[2])
    daddr = sys.argv[3]
    dport = int(sys.argv[4])

    c = TcpCon(saddr, sport, daddr, dport, sys.argv[5])
    c.mss = 48
    c.connect()


    seq = c.p_seq_num
    print 'mss: ', c.mss
    print seq

    c.write(http_request)

    for i in range(10):
        c.wait_one()
        p = c.mk_packet()
        c.send_packet(p)


    #icmp = PacketICMP()
    #icmp.ip(saddr, daddr)
    #icmp.send()

    #time.sleep(1)
    #c.wait_n(500)

    #p = c.mk_packet()
    #p.tcp_ack_seq = seq
    #p.sack.append((seq + 8, seq + 8 * 2))
    #c.send_packet(p)




main()








