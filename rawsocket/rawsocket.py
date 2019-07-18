# -*- coding: utf-8 -*

import os
import sys, socket
from struct import *
import random
import time
import threading
import multiprocessing


class g:
    exit = False
    raw = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                socket.IPPROTO_RAW)

    via       = None
    interface = None

    src_ip    = None
    dst_ip    = None
    sport     = None
    dport     = None
    mss       = None
    cwnd      = None
    mtu       = None
    protocol  = None

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
        mtu = g.mtu

        _type = 3 # Network Unreachable
        code = 4  # Fragmentation needed but no frag. bit set

        packet = pack('!BBHI', _type, code, cs, mtu)
        cs = checksum(packet)
        packet = pack('!BBHI', _type, code, cs, mtu)

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
        header = packet[34:54]
        if len(header) < 20:
            return

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
        tcp_window_size = 65535
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



            # sack perm
            opts += pack('!BB', 4, 2)

        # timestamp
        opts += pack('!BBIIBB', 8, 10,
                int(time.time()), 0,
                1, 1 # nop
                )



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
        self.num = 0
        self.e_num = 0

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

    def _send(self, payload = ''):
        p = self.mk_packet(payload)

        p.send()

        self.l_seq_num += len(payload)

        if p.tcp_flag_syn:
            self.l_seq_num += 1

        if p.tcp_flag_fin:
            self.l_seq_num += 1

    def decode_packet(self, pa):
        packet = PacketTcp(pa)

        if packet.ip_saddr != self.daddr:
            return

        if packet.tcp_dport != self.sport:
            return

        self.num += 1


        if packet.tcp_seq <= self.p_seq_num:
            return

        if packet.tcp_flag_rst:
            return

        self.p_seq_num = packet.tcp_seq + packet.payload_size - 1

        self.e_num += 1

        if packet.tcp_flag_syn:
            self.p_seq_num += 1

        if packet.tcp_flag_fin:
            self.p_seq_num += 1

        return packet

    def wait_one(self):
        while True:
            pa =  self.recv.recv(1500)
            pa =  self.decode_packet(pa)
            if pa:
                return pa


    def recv_packet_start(self):
        q = multiprocessing.Queue()

        def recv_packet(q):
            while True:
                pa =  self.recv.recv(1500)
                q.put(pa)

        def loop(q):
            while True:
                    pa = q.get()
                    self.decode_packet(pa)
            print "thread exit"


        p = multiprocessing.Process(target = recv_packet, args=(q,))
        p.start()

        x = threading.Thread(target = loop, args=(q,))
        x.start()



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
        "Host: cdn.fengidri.me\r\n" \
        "Accept: */*\r\n" \
        "\r\n"
http_request = "GET /100M HTTP/1.1\r\n" \
        "Host: test.com\r\n" \
        "Accept: */*\r\n" \
        "\r\n"


def init_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-s")
    parser.add_argument("-d")
    parser.add_argument("-r")
    parser.add_argument("-i")
    parser.add_argument("-p", default='tcp')
    parser.add_argument("--sport", type = int, default=0)
    parser.add_argument("--dport", type=int, default=80)
    parser.add_argument("--mss", type=int, default=1460)
    parser.add_argument("--mtu", type=int, default=1500)
    parser.add_argument("--cwnd", type=int, default=100 * 1024)


    args = parser.parse_args()


    g.via       = args.r
    g.interface = args.i

    g.src_ip    = args.s
    g.dst_ip    = args.d
    g.sport     = args.sport
    g.dport     = args.dport
    g.mss       = args.mss
    g.cwnd      = args.cwnd
    g.mtu       = args.mtu
    g.protocol  = args.p

def send_sack(c, s, offset, e):
    p = c.mk_packet()

    p.tcp_ack_seq = s

    p.sack.append((s + offset, e))

    print p.sack
    p.send()





def main():
    c = TcpCon(g.src_ip, g.sport, g.dst_ip, g.dport, g.interface)
    c.mss = g.mss
    c.connect()

    seq = c.p_seq_num
    print 'mss: ', c.mss

    c.write(http_request)

    # 发送不连接的包, 让服务器返回的时带上 sack
    for i in range(3):
        p = c.mk_packet('0' * 8)
        p.tcp_seq  += 8 * (i  + 1) * 3
        p.send()

    time.sleep(5)

    c.recv_packet_start()


    print "+++++++++++++++++++++"

    num = 0
    c_num = 0
    c_enum = 0
    s = c.p_seq_num
    while True:

        time.sleep(1)

        print 'recv: %d  %d  %d num: %d enum: %d' % ((c.p_seq_num - s), c.p_seq_num,
                    s, c.num  - c_num, c.e_num - c_enum)

        if c.p_seq_num - s > g.cwnd:
            break

        p = c.mk_packet()
        s = p.tcp_ack_seq
        c_num = c.num
        c_enum = c.e_num

        p.send()


    print "================"

    e = s + 8 * 65536

    e += 5 * 1024

    send_sack(c, s, 5 * 1024, e)
    send_sack(c, s, 3 * 1024, e)

    sys.exit(0)



init_args()

if g.protocol == 'tcp':
    main()
    g.exit = True
elif g.protocol == 'icmp':
    p = PacketICMP()
    p.ip(g.src_ip, g.dst_ip)
    p.send()








