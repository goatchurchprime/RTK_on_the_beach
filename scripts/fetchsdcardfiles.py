
#
# This script will be combined with the hanglog file 
# Needs to be on phone hotspot to which the GPS with SD card is connected
#

import socket, time, os

hanglogaddr = socket.getaddrinfo("192.168.43.1", 9042)[0][-1]
print("Script to download files from Android device through Hanglog3")

def hanglog3listdirDevice(fdir, deviceletter):
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.9)
    s = ss.makefile('rwb', 0)
    row = s.readline()
    print("Hanglog:", row)

    ss.send(("+%s%s%s-SDMODE\n" % (deviceletter,deviceletter,deviceletter)).encode())
    time.sleep(0.5)
    ssR = socket.socket()
    ssR.connect(hanglogaddr)
    ssR.settimeout(0.9)
    ssR.send(("-%s%s%s\n" % (deviceletter,deviceletter,deviceletter)).encode())
    sR = ssR.makefile('rwb', 0)
    
    ss.send(("-DRL\n%s\n" % fdir).encode())
    row = sR.readline()
    print("Hanglog:", row)
    row = sR.readline()
    print("Hanglog:", row)
    
    res = [ ]
    while True:
        row = sR.readline().decode().strip()
        if row == '.':
            break
        res.append(row)
    ss.close()
    ssR.close()
    return res


def hanglog3downloadDevice(hfile, deviceletter, hfileout):
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.9)
    s = ss.makefile('rwb', 0)
    row = s.readline()
    print("Hanglog:", row)

    ss.send(("+%s%s%s-SDMODE\n" % (deviceletter,deviceletter,deviceletter)).encode())
    time.sleep(0.5)
    ssR = socket.socket()
    ssR.connect(hanglogaddr)
    ssR.settimeout(30)
    ssR.send(("-%s%s%s\n" % (deviceletter,deviceletter,deviceletter)).encode())
    sR = ssR.makefile('rwb', 0)
    
    ss.send(("-DRR\n%s\n" % hfile).encode())
    row = sR.readline()
    print("Hanglog:", row)
    row = sR.readline()
    print("Hanglog:", row)
    nbytes = int(row.decode().strip())
    print("Reading %d bytes of %s" % (nbytes, hfile))
    
    fout = open(hfileout, "wb")
    while nbytes > 0:
        b = sR.read(500)
        fout.write(b)
        if nbytes//10000 != (nbytes-len(b))//10000:
            print("remaining", nbytes)
        nbytes -= len(b)
    fout.close()
    ss.close()
    ssR.close()
    print("saved as", hfileout)


def hanglog3eraseDevice(hfile, deviceletter):
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.9)
    s = ss.makefile('rwb', 0)
    row = s.readline()
    print("Hanglog:", row)

    ss.send(("+%s%s%s-SDMODE\n" % (deviceletter,deviceletter,deviceletter)).encode())
    time.sleep(0.5)
    ssR = socket.socket()
    ssR.connect(hanglogaddr)
    ssR.settimeout(30)
    ssR.send(("-%s%s%s\n" % (deviceletter,deviceletter,deviceletter)).encode())
    sR = ssR.makefile('rwb', 0)
    
    ss.send(("-DRE\n%s\n" % hfile).encode())
    row = sR.readline()
    print("Hanglog:", row)
    
    
if __name__ == "__main__":
    deviceletter = "C"
    while True:
        ffiles = hanglog3listdirDevice("/sd", deviceletter)
        print("\n\nhanglog files:")
        for i, fd in enumerate(ffiles):
            print(" ", i, fd)
        print()
        choice = input("Choose file: ")
        if choice == "":
            break

        while True:
            ffile, sbytes = ffiles[int(choice)].split()
            nbytes = int(sbytes)
            print("You have chosen file:", ffile, " of length", nbytes, "bytes")
            print()
            choiced = input("Download, erase or go up [d/e/u]: ")
            if choiced == "d":
                if not os.path.exists("hanglog"):
                    print("Making hanglog directory")
                    os.mkdir("hanglog")
                hanglog3downloadDevice("sd/%s"%ffile, deviceletter, os.path.join("hanglog", ffile))
                break
            elif choiced == "e":
                hanglog3eraseDevice("sd/%s"%ffile, deviceletter)
                break
            elif choiced == "u":
                break
            else:
                break
        if choiced == "":
            break
    
    
#print(hanglog3downloadDevice("sd/hdata-2020-07-06_20-35-30C.ubx", "C", "test.ubx"))


