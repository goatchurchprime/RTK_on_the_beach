#!/usr/bin/env python3

# copy up with:
#  scp serverrelay.py  freesteel@onza.mythic-beasts.com:
# to see what's there, do: netstat -ntpl


import socket, threading, time

host = "localhost"
port = 9076
socketrelays = { }

class socketrelay(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self, daemon=True)
        self.name = name
        self.socketincoming = None
        self.socketsoutgoing = [ ]

    def run(self):
        while True:
            if self.socketincoming is None:
                time.sleep(1)
                continue
            try:
                print("waiting to receive bytes on", self.name)
                x = self.socketincoming.recv(10)
            except Exception as e:
                print("socket incoming error", e, self.socketincoming)
                self.socketincoming = None
                continue
            
            print(self.name, "sending", x)
            for i in range(len(self.socketsoutgoing)-1, -1, -1):
                try:
                    self.socketsoutgoing[i].send(x)
                except Exception as e:
                    print("socket outgoing error", e, self.socketsoutgoing[i])
                    del self.socketsoutgoing[i]
                    
    def addnewconnection(self, conn, r):
        if r == b"-":
            self.socketsoutgoing.append(conn)
            print(self.name, "has", len(self.socketsoutgoing), "outgoing connections")
        if r == b"+":
            if self.socketincoming is not None:
                print(self.name, "removing", "incoming connection")
                try:
                    self.socketincoming.close()
                except Exception as e:
                    print("incoming socket closing error", e, self.socketincoming)
            print(self.name, "added", "incoming connection")
            self.socketincoming = conn
            print(self.name, "socketincoming", self.socketincoming)

                    
def waitallocate(conn):
    r = conn.recv(1)
    u = conn.recv(3)
    print("allocating", r, u)
    if u[0] == u[1] == u[2]:
        if u not in socketrelays:
            socketrelays[u] = socketrelay(u)
            socketrelays[u].start()
            print("new socket relay", u)
        socketrelays[u].addnewconnection(conn, r)
        

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
addr1 = socket.getaddrinfo(host, port)[0][-1]
print("listening on", addr1)
s.bind(addr1)
s.listen()
while 1:
    conn, addr = s.accept()
    print('Connected with ' + addr[0] + ':' + str(addr[1]))
    t = threading.Thread(target=waitallocate, args=(conn,), daemon=True)
    t.start()
    
# --------------
# Use the following to post bytes from one to another

#import socket
#host = "localhost"
#host = "freesteel.co.uk"
#port = 80
#addr = socket.getaddrinfo(host, port)[0][-1]
#print(addr)

# --------------
#s1 = socket.socket()
#s1.connect(addr)
#s1.send(b"+kkk")

#s2 = socket.socket()
#s2.connect(addr)
#s2.send(b"-kkk")

# --------------
#s1.send(b"hi there")

# --------------
#s2.recv(6)


