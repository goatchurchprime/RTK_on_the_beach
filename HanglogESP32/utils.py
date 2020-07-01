import network, socket, time, machine, os

deviceletter = open("deviceletter.txt", "r").read()
print("deviceletter", deviceletter)

si = network.WLAN(network.STA_IF) 

# Connect to Blackview/S5 (Android) phone
def connectActivePhone(fconfig, pled):
    cdelimeter = fconfig.get("cdelimeter", ",")
    hotspots = { }
    for i in range(100):
        l = fconfig.get("connection%d" % i)
        if not l:   break
        s = l.split(cdelimeter)
        hotspots[s[0].encode()] = (s[1], s[2], int(s[3]))
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


# Set up flashing LED timer (better control than PWM)
timeracc = 0
timermax = 1000
timerlight = 100
timeradd = 50
pgled = None
timer = None
def timercallback(t):
    global timeracc
    timeracc = (timeracc + timeradd)%timermax
    pgled.value(int(timeracc<timerlight))

def initledflashtimer(lpgled):
    global timer, pgled
    pgled = lpgled
    timer = machine.Timer(-1)
    timer.init(period=50, mode=machine.Timer.PERIODIC, callback=timercallback)

def setledflashtime(ltimeradd, ltimerlight, ltimermax=1000):
    global timeradd, timerlight, timermax
    timeradd, timerlight, timermax = ltimeradd, ltimerlight, ltimermax

    
def updateconfig(c="config.txt"):
    while True:
        print("\n\n", c, ":\n")
        with open(c) as fin:
            for x in fin:
                print(x.strip())
        y = input("input line> ")
        ys = y.split()
        if not 1 <= len(ys) <= 2:
            return
        cd = "E"+c
        with open(cd, "w") as fout:
            with open(c) as fin:
                x = None
                for x in fin:
                    xs = x.split()
                    if ys is not None and ys[0] == xs[0]:
                        if len(ys) == 2:
                            fout.write(y)
                            fout.write("\n")
                        ys = None
                    else:
                        fout.write(x)
            if ys is not None and len(ys) == 2:
                if x is not None:
                    fout.write("\n")
                fout.write(y)
                fout.write("\n")
        os.rename(cd, c)
        
        
        