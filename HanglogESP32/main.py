import time, machine, os
from ubxm8t import uartUBX, initUBX
from utils import deviceletter, connectActivePhone, initledflashtimer, setledflashtime
from machine import Pin, reset_cause, SPI
import socket, uselect

fconfig = dict(x.strip().split(None, 1)  for x in open("config.txt"))

# delay long enough for Ctrl-C before the wlan bricks it for debugging
# reset_cause=1:PWRON_RESET, 2:HARD, 5:SOFT (brownout detected)
pinled = Pin(int(fconfig["pinled"]), Pin.OUT)
for i in range(2*(machine.reset_cause())):
    pinled.value(1-(i%2))
    time.sleep_ms(400)  

# connect to SDCard if one exists
sddir = None
if "sdcard" in fconfig:
    from sdcard import SDCard
    vsdcard = fconfig["sdcard"].split(",")
    spisd = SPI(-1, sck=Pin(int(vsdcard[2])), mosi=Pin(int(vsdcard[3])), miso=Pin(int(vsdcard[4])))
    try:
        sd = SDCard(spisd, Pin(int(vsdcard[1])))
        sddir = '/'+vsdcard[0]
        os.mount(sd, sddir)
        print(os.listdir(sddir))
    except OSError as e:
        print("No SD card", e)
        for i in range(21):
            pinled.value(i%2)
            time.sleep_ms(780 if (i%4) == 1 else 80)
        sddir = None
        
# Set up flashing LED timer (better control than PWM)
pingled = Pin(int(fconfig["pingled"]))  if "pingled" in fconfig  else None
if pingled:
    initledflashtimer(pingled)

# Serial connection to the UBlox GPS device
print("Initializing UBX")
initUBX()
for i in range(11):
    pinled.value(i%2)
    time.sleep_ms(200)

print("RESET_CAUSE", reset_cause())

for k in range(2 if sddir else 10000):
    androidipnumber, portnumber = connectActivePhone(fconfig, pinled)
    if androidipnumber is not None:
        break
## Replace this with single loop!              
    for j in range(3):
        for i in range(7):
            pinled.value(i%2)
            time.sleep_ms(100)
        time.sleep_ms(800)

for i in range(21):
    pinled.value(i%2)
    time.sleep_ms(80)

ubxbuffer = bytearray(1000)
mubxbuffer = memoryview(ubxbuffer)
timelastledsignal = 0
totalbytes = 0
obj = None
while True:
    setledflashtime(50, 2000, 4000) 
    try:
        ss = socket.socket()
        ss.settimeout(1)
        print(ss)
        ss.connect(socket.getaddrinfo(androidipnumber, portnumber)[0][-1])
        s = ss.makefile('rwb', 0)
        print(s.readline())
        s.write(b"%c%c%c%c"%(deviceletter,deviceletter,deviceletter,deviceletter))
        poller = uselect.poll()
        poller.register(uartUBX, uselect.POLLIN)
        poller.register(s, uselect.POLLIN)
        while True:
            for obj, evt in poller.ipoll(100):
                if obj == uartUBX and evt == uselect.POLLIN:
                    n = uartUBX.readinto(ubxbuffer)
                    if n is not None:
                        s.write(mubxbuffer[:n])
                        pinled.value(1-pinled.value())
                        totalbytes += n
                    if time.ticks_ms() - timelastledsignal > 2000:
                        setledflashtime(50, 1500, 3000)  # slow down signal to show it's broken

                if obj == s and evt == uselect.POLLIN:
                    timelastledsignal = time.ticks_ms()
                    setledflashtime(50, 200, 1000) 
                    timermax = 1000
                    setledflashtime(1000, 100) 
                    l = s.readline()
                    try:
                        print(l)
                        setledflashtime(*list(map(int, l.split())))
                    except ValueError as e:
                        print("ValueError", e)
    except OSError as e:
        print("OSError", e, obj)
        time.sleep_ms(2000)
