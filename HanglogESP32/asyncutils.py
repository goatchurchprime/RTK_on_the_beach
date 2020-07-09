import uasyncio as asyncio
import uasyncio.stream
import network, time, ustruct, os
from machine import Pin, UART, SPI, ADC

fconfig = dict(x.strip().split(None, 1)  for x in open("config.txt"))
pinled = Pin(int(fconfig["pinled"]), Pin.OUT)

if "pinbatteryadc" in fconfig:
    s = fconfig["pinbatteryadc"].split(",")
    pinbatteryadc = ADC(Pin(int(s[0])))
    pinbatteryadc.atten(ADC.ATTN_11DB)  # 3.6V
    pinbatteryadc.width(ADC.WIDTH_12BIT)
    batteryR1, batteryR2 = float(s[1]), float(s[2])
else:
    pinbatteryadc = None

def batteryvoltage():
    if pinbatteryadc is None:
        return 0.0
    return pinbatteryadc.read()/4096.0*3.6/batteryR2*(batteryR1+batteryR2)
    
uartUBX = UART(1, baudrate=9600, rx=16, tx=17)
streamUBX = uasyncio.stream.Stream(uartUBX)
fdatebasedname = None  # SimpleDateFormat("'hdata-'yyyy-MM-dd'_'HH-mm-ss") extracted from GPS 

si = network.WLAN(network.STA_IF)
si.active(True)

def mountsd():
    import sdcard
    s = fconfig["sdcard"].split(",")
    spisd = SPI(-1, sck=Pin(int(s[1])), mosi=Pin(int(s[2])), miso=Pin(int(s[3])))
    sd = sdcard.SDCard(spisd, Pin(int(s[0])))
    try:
        os.mount(sd, s[4])
    except OSError:
        print("Failed to mount sd", s)
        return None
    return s[4]


async def flashseq(seq):
    for i, d in enumerate(seq):
        pinled.value(i%2)
        await asyncio.sleep_ms(d)
    pinled.value(0)


#    
# repeat connecting to wifi until giving up (if there is an SD card)    
#
async def wificonnect():
    t0 = time.time()
    while True:
        print("Enter wificonnect at", time.time() - t0, "seconds")
        if "wifi2sdtimeout" in fconfig and time.time() - t0 > int(fconfig["wifi2sdtimeout"]):
            if fdatebasedname is not None:
                print("Quitting wifi in favour of SD card")
                return None, None
            else:
                print("No fdatebasedname yet")

        await flashseq((100,200,100,200,300))
        cdelimeter = fconfig.get("cdelimeter", ",")
        hotspots = { }
        for i in range(100):
            l = fconfig.get("connection%d" % i)
            if not l:   break
            s = l.split(cdelimeter)
            hotspots[s[0].encode()] = (s[1], s[2], int(s[3]))

        siscanned = si.scan()
        siscanned.sort(key=lambda X:X[3])
        while siscanned:
            wc = siscanned.pop()
            wconn = wc[0]
            if wconn in hotspots:
                wpass, host, port = hotspots[wconn]
                break
        else:
            continue  # try connection again

        print("Choosing to connect to", wconn)
        si.connect(wconn, wpass)
        while si.status() == network.STAT_CONNECTING:
            await flashseq((100,100))

        await asyncio.sleep(1)
        if si.isconnected():
            print("Wifi connected")
            return hotspots[wconn][1:]

#
# Functions for handling the GPS modes and getting the fdatebasedname
#
async def sendNMEA(comm):
    s = 0
    for c in comm:
        s ^= c
    await streamUBX.awrite(b"${:s}*{:02x}\r\n".format(comm, s))

async def extractdatermc():
    await sendNMEA(b"PUBX,40,{:s},0,{:d},0,0,0,0".format("RMC", 1))
    while True:
        try:
            mline = await streamUBX.readline()
            while b"$" in mline[1:]:  # filter out binary junk
                mline = mline[mline.find(b"$"):]
            if mline[:1] == b"$" and mline[3:6] == b"RMC":
                mline = mline.decode()
                m = mline.split(",")
                if len(m) >= 10:
                    mt, md = m[1], m[9]
                    if len(mt) >= 6 and float(mt) and len(md) == 6 and int(md):
                        return 'hdata-20%s-%s-%s_%s-%s-%s' % (md[4:], md[2:4], md[:2], mt[:2], mt[2:4], mt[4:6])
        except UnicodeError as e:
            pass
        except ValueError as e:
            pass
        except TypeError as e:
            pass
    
def encodeUBX(clsID, msgID, payload):  # look up on p138
    comm = bytearray((0xb5, 0x62, clsID, msgID, len(payload) & 0xFF, (len(payload)>>8) & 0xFF))
    comm.extend(payload)
    ca, cb = 0, 0
    for c in comm[2:]:
        ca = (ca + c) & 0xFF
        cb = (cb + ca) & 0xFF
    comm.append(ca)
    comm.append(cb)
    return comm

async def setbaud(baudrate):
    await sendNMEA(b"PUBX,41,1,0007,0003,%d,0" % baudrate)
    uartUBX.init(baudrate=baudrate)
    
async def initUBX():
    global fdatebasedname
    await asyncio.sleep_ms(1000)
    await setbaud(115200)
    await asyncio.sleep_ms(1000)
    fdatebasedname = await extractdatermc()
    print("fdatebasedname", fdatebasedname)
    for msgId in ["GLL", "GSV", "GSA", "GGA", "VTG", "RMC", "ZDA"]:
        await sendNMEA(b"PUBX,40,{:s},0,{:d},0,0,0,0".format(msgId, 0))
        await asyncio.sleep_ms(100)
    await streamUBX.awrite(encodeUBX(0x06, 0x08, ustruct.pack("<HHH", 200, 1, 0)))  # UBX-CFG-RATE
    await asyncio.sleep_ms(100)
    await streamUBX.drain()
    
    # Request record stream of type (b0, b1) at rate b2
    await streamUBX.awrite(encodeUBX(0x06, 0x01, b"\x02\x15\x01"))  # UBX-RXM-RAWX
    await streamUBX.awrite(encodeUBX(0x06, 0x01, b"\x02\x13\x01"))  # UBX-RXM-SFRBX
    await streamUBX.awrite(encodeUBX(0x06, 0x01, b"\x01\x22\x01"))  # UBX-NAV-CLOCK
    await streamUBX.awrite(encodeUBX(0x06, 0x01, b"\x01\x30\x01"))  # UBX-NAV-SVINFO

    print("000", (await streamUBX.read(-1))[:10])
    print("111", (await streamUBX.read(-1))[:10])
    return fdatebasedname
