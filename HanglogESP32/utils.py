import network, socket, time, machine, os

si = network.WLAN(network.STA_IF) 

# Connect to Blackview/S5 (Android) phone
def connectActivePhone(pled):
    hotspots = { }
    for l in open("hotspots.txt", "rb"):
        s = l.split()
        hotspots[s[0]] = (s[1], s[2].decode(), int(s[3]))
    print(hotspots)
    
    si.active(True)
    siscanned = si.scan()
    siscanned.sort(key=lambda X:X[3])
    while siscanned:
        wc = siscanned.pop()
        print(wc)
        wconn = wc[0]
        if wconn in hotspots:
            wpass, host, port = hotspots[wconn]
            break
            
    else:
        return None, None
    print("Choosing to connect to", wconn)
    si.connect(wconn, wpass)
    while not si.isconnected():
        time.sleep_ms(100)
        pled.value(1-pled.value())
    return host, port


def updatehotspots(c="hotspots.txt"):
    while True:
        print("\n\n", c, ":\n")
        with open(c) as fin:
            for x in fin:
                print(x.strip())
        y = input("\ninput line> ")
        ys = y.split()
        if len(ys) != 1 and len(ys) != 4:
            return
        cd = "E"+c
        with open(cd, "w") as fout:
            with open(c) as fin:
                x = None
                for x in fin:
                    xs = x.split()
                    if ys is not None and ys[0] == xs[0]:
                        if len(ys) != 1:
                            fout.write(y)
                            fout.write("\n")
                        ys = None
                    else:
                        fout.write(x)
            if ys is not None and len(ys) != 1:
                if x is not None:
                    fout.write("\n")
                fout.write(y)
                fout.write("\n")
        os.rename(cd, c)