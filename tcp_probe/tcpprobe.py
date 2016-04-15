# -*- coding:utf-8 -*-
#    author    :   丁雪峰
#    time      :   2016-04-15 01:42:32
#    email     :   fengidri@yeah.net
#    version   :   1.0.1


if __name__ == "__main__":
    pass

import sys
import signal
import os

class G:
    output = None
    recv = 0
    handle=[0]



def receive_signal(signum, stack):
    print 'Received: %s' % G.recv
    sys.exit(0)



signal.signal(signal.SIGINT, receive_signal)


def handle_print(data):
    print data,
    sys.stdout.flush()


def handle_write(data):
    G.output.write(data)



def read():
    f = open('/proc/net/tcpprobe')
    while True:
        d = f.read(200)
        if not d:
            break
        G.recv += len(d)
        G.handle[0](d)

def main():
    G.handle[0] = handle_print
    if len(sys.argv) > 1:
        G.output = open(sys.argv[1], 'w')
        G.handle[0] = handle_write
    read()
main()



