import time, machine
from ubxm8t import uartUBX, initUBX
from utils import connectActivePhone
import socket, uselect


# delay long enough for Ctrl-C before the wlan bricks it for debugging
# reset_cause=1:PWRON_RESET, 2:HARD, 5:SOFT (brownout detected)
pled = machine.Pin(2, machine.Pin.OUT)
for i in range(2*(machine.reset_cause())):
    pled.value(1-(i%2))
    time.sleep_ms(400)  

# Set up flashing LED timer (better control than PWM)
pgled = machine.Pin(23, machine.Pin.OUT)
timeracc = 0
timermax = 1000
timerlight = 100
timeradd = 50
def timercallback(t):
    global timeracc
    timeracc = (timeracc + timeradd)%timermax
    pgled.value(int(timeracc<timerlight))
timer = machine.Timer(-1)
timer.init(period=50, mode=machine.Timer.PERIODIC, callback=timercallback)

# Serial connection to the UBlox GPS device
print("Initializing UBX")
initUBX()
for i in range(11):
    pled.value(i%2)
    time.sleep_ms(200)

print("RESET_CAUSE", machine.reset_cause())
deviceletter = open("deviceletter.txt", "r").read()
print("deviceletter", deviceletter)

while True:
    androidipnumber, portnumber = connectActivePhone(pled)
    if androidipnumber is not None:
        break
    for j in range(3):
        for i in range(7):
            pled.value(i%2)
            time.sleep_ms(100)
        time.sleep_ms(800)

for i in range(21):
    pled.value(i%2)
    time.sleep_ms(80)


ubxbuffer = bytearray(1000)
mubxbuffer = memoryview(ubxbuffer)
timelastledsignal = 0
totalbytes = 0
obj = None
while True:
    timermax = 4000  # slow down signal to show it's broken
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
                        pled.value(1-pled.value())
                        totalbytes += n
                    if time.ticks_ms() - timelastledsignal > 2000:
                        timermax = 3000  # slow down signal to show it's broken

                if obj == s and evt == uselect.POLLIN:
                    timelastledsignal = time.ticks_ms()
                    timermax = 1000
                    l = s.readline()
                    try:
                        print(l)
                        timeradd, timerlight = list(map(int, l.split()))
                    except ValueError as e:
                        print("ValueError", e)
    except OSError as e:
        print("OSError", e, obj)
        time.sleep_ms(2000)
