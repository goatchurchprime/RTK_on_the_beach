import socket, time, os

#
# Script for connecting to Hanglog3 on the android device and 
# listing, downloading or erasing directories of logged data
#
# Simply execute when connected to the androind device, since it 
# has it's own Command Line User Interface
#

hanglogaddr = socket.getaddrinfo("192.168.43.1", 9042)[0][-1]
print("Script to download files from Android device through Hanglog3")

def hanglog3listdir(fdir):
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.9)
    s = ss.makefile('rwb', 0)
    row = s.readline()
    print("Hanglog:", row)
    ss.send(("-DRL\n%s\n" % fdir).encode())
    row = s.readline()
    print("Hanglog:", row)
    res = [ ]
    while True:
        row = s.readline().decode().strip()
        if row == '.':
            break
        res.append(row)
    ss.close()
    return res

def hanglog3download(hfile):
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.9)
    s = ss.makefile('rwb', 0)
    row = s.readline()
    print("Hanglog:", row)
    ss.send(("-DRR\n%s\n" % hfile).encode())
    nbytes = int(s.readline().decode().strip())
    print("Reading %d bytes of %s" % (nbytes, hfile))    
    fout = open(hfile, "wb")
    while nbytes > 0:
        b = s.read(100)
        fout.write(b)
        nbytes -= len(b)
    fout.close()
    ss.close()

def hanglog3erase(hfile):
    ss = socket.socket()
    ss.connect(hanglogaddr)
    ss.settimeout(0.9)
    s = ss.makefile('rwb', 0)
    row = s.readline()
    print("Hanglog:", row)
    ss.send(("-DRE\n%s\n" % hfile).encode())
    row = s.readline()
    print("Hanglog:", row)
    row = s.readline()
    print("Hanglog:", row)
    ss.close()

if __name__ == "__main__":
    while True:
        fdirs = hanglog3listdir("hanglog")
        print("\n\nhanglog directories:")
        for i, fd in enumerate(fdirs):
            print(" ", i, fd)
        print()
        choice = input("Choose directory: ")
        if choice == "":
            break
        fdir = fdirs[int(choice)]

        while True:
            ffiles = hanglog3listdir("hanglog/%s" % fdir)
            print("\n\n files:")
            print("\n".join(ffiles))
            print()
            choice = input("Download, erase or go up [d/e/u]: ")
            if choice == "d":
                if not os.path.exists("hanglog"):
                    print("Making hanglog directory")
                    os.mkdir("hanglog")
                ffdir = os.path.join("hanglog", fdir)
                if not os.path.exists(ffdir):
                    print("Making %s directory" % ffdir)
                    os.mkdir(ffdir)
                for ffile in ffiles:
                    hanglog3download("hanglog/%s/%s" % (fdir, ffile))

            elif choice == "e":
                for ffile in ffiles:
                    hanglog3erase("hanglog/%s/%s" % (fdir, ffile))
                hanglog3erase("hanglog/%s" % (fdir))
                break

            elif choice == "u":
                break
            else:
                break

        if choice == "":
            break



    
    