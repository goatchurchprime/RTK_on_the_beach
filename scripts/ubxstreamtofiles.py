
# Script to connect to Hanglog3 through 3 socket connections and receive and log
# streamed UBX binary data to a file

import argparse

parser = argparse.ArgumentParser(description='Hanglog3 stream log UBX files')
parser.add_argument('-t','--time', default=10, help='Time in seconds')
parser.add_argument("fdir")
args = parser.parse_args()
tseconds = float(args.time)
datadir = args.fdir

import socket, time, threading, os

hanglogaddr = socket.getaddrinfo("192.168.43.1", 9042)[0][-1]
endthreads = False
filesizes = { }

def readstream(identletter):
    identheader = ("-%s%s%s\n" % (identletter,identletter,identletter)).encode()
    datafilename = os.path.join(datadir, "data%s.ubx" % identletter)
    
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.1)
    s = ss.makefile('rwb', 0)
    try:
        row = s.readline()
    except socket.timeout:
        print("socket", ident, "failed")
        return
    print(row)
    print("sending", identheader)
    ss.send(identheader)
    fout = None
    while not endthreads:
        try:
            b = ss.recv(100)
        except socket.timeout:
            continue
        if fout is None and b:
            fout = open(datafilename, "wb")
            print("writing file", datafilename)
            filesizes[identletter] = 0
        if b:
            fout.write(b)
            filesizes[identletter] += len(b)
    print("thread", identletter, "ended")

for x in "ABC":
    threading.Thread(target=readstream, args=(x,), daemon=True).start()
    time.sleep(0.2)
for i in range(int(tseconds)+1):
    time.sleep(1)
    print(i, filesizes)
endthreads = True
time.sleep(0.5)
