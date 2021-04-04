from machine import UART, Pin, ADC
import time, socket, urandom
from BNO055_class import BNO055
from UDPblackviewphone import connectActivePhone
from scani2cdevices import readi2cdevices

fconfig = dict(x.strip().split(None, 1)  for x in open("config.txt"))
pinled = Pin(int(fconfig["pinled"]), Pin.OUT)

def MakeBNO055(dev):
    d = dev.split(",")
    u = UART(int(d[0]), baudrate=115200, rx=int(d[1][2:]), tx=int(d[2][2:]))
    for i in range(5):
        try:
            print(u, d[3])
            return BNO055(u, d[3])
        except OSError as e:
            print(e)
        print("fail", i, d)
        time.sleep(0.5)
dev1 = MakeBNO055(fconfig["dev1"])


# PWM detector (for the prop anemometer)
p27 = Pin(27, Pin.IN, Pin.PULL_DOWN)
if p27 is not None:
    from machine import mem32
    import esp32
    entry = 4
    ulp = esp32.ULP()
    ulp.load_binary(0, open("measure_windprop.ulp", "rb").read())
    ulp.set_wakeup_period(0, 1000000)
    ulp.run(entry*4)
    countpin27 = 0
    fanbladedivider = int(fconfig.get("fanbladedivider", 15))
    mem32[0x50000000+3*4] = fanbladedivider&0xFFFF
    def readulpdata(r):
        return mem32[0x50000000+r]&0xFFFF
    print("fanbladedivider", readulpdata(3*4))
    wbs = bytearray("Wt00000000w0000n0000\n")
    mwbs = memoryview(wbs)

nbs = None
if "analogreadpin" in fconfig:
    pinanalogread = ADC(Pin(int(fconfig["analogreadpin"]), Pin.IN))
    pinanalogread.atten(ADC.ATTN_11DB)
    pinanalogread.width(ADC.WIDTH_12BIT)
    nbs = bytearray("Nt00000000s000000\n")
    mnbs = memoryview(nbs)
    analogreadrate = int(fconfig.get("analogreadrate", 1000))
    tstampanalogread = 0

deviceletter = fconfig["deviceletter"]
c = fconfig["connection0"].split(",")
hotspots = { c[0].encode(): (c[1].encode(), c[2], int(c[3])) }
androidipnumber = c[2]
portnumber = int(c[3])
print("deviceletter", deviceletter)

while not connectActivePhone(pinled, hotspots):
    for j in range(3):
        for i in range(7):
            pinled.value(i%2)
            time.sleep_ms(100)
        time.sleep_ms(800)

import socket, urandom
prevflushstamp = 0
nextledonstamp = 0

ubs = bytearray("Ut00000000i00\n")
mubs = memoryview(ubs)

while True:
    try:
        print("making socket")
        ss = socket.socket()
        ss.settimeout(1)
        print("socket is", ss)
        ss.connect(socket.getaddrinfo(androidipnumber, portnumber)[0][-1])
        s = ss.makefile('rwb', 0)
        print(s.readline())
        s.write(b"%c%c%c%c"%(deviceletter,deviceletter,deviceletter,deviceletter))
        dwrite = s.write
        while True:
            tstamp = time.ticks_ms()
            if tstamp > nextledonstamp:
                pv = (0 if pinled.value() else 1)
                pinled.value(pv)
                mubs[2:10] = b"%08X" % tstamp
                mubs[12] = 48+pv #'0'or'1'
                dwrite(ubs)
                nextledonstamp = tstamp + urandom.randint(5000, 10000)//(10 if pv else 1)
            if dev1 is not None:
                b1 = dev1.readhexlifyBNO055(10)
                if b1 is not None:
                    dwrite(b1)

            try:
                bs = readi2cdevices(tstamp)
                if bs is not None:
                    dwrite(bs)
            except OSError:
                pass
            
            if p27 is not None:
                lcountpin27 = readulpdata(8)
                if lcountpin27 != countpin27:
                    countpin27 = lcountpin27
                    timepin27 = readulpdata(4)
                    mwbs[2:10] = b"%08X" % tstamp
                    mwbs[11:15] = b"%04X" % timepin27
                    mwbs[16:20] = b"%04X" % countpin27
                    dwrite(wbs)

            if nbs != 0 and tstamp > tstampanalogread:
                tstampanalogread = tstamp + analogreadrate
                mnbs[2:10] = b"%08X" % tstamp
                mnbs[11:17] = b"%06X" % pinanalogread.read()
                dwrite(nbs)
                
                    
    except OSError as e:
        msg = str(e)
        if e.args[0] == 118:
            msg = "wifi not connected"
        elif e.args[0] == 23:
            msg = "socket error"
        print("OSError", msg)
        time.sleep(2)
