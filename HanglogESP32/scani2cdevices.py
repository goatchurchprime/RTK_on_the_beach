from machine import I2C, Pin
import time

px4readrate = 400
sht31readrate = 350
bme280readrate = 500

i2c = I2C(scl=Pin(15, Pin.OUT, Pin.PULL_UP), sda=Pin(4, Pin.OUT, Pin.PULL_UP), freq=450000)
i2cdevices = i2c.scan()
print("i2cdevices", i2cdevices)

# Pitot tube sensor
xbs = None
if 0x28 in i2cdevices:
    xbs = bytearray("Xt00000000d0000r0000\n")
    mxbs = memoryview(xbs)
    tstamppx4 = 0
    print("PX4 pitot found")
else:
    print("PX4 pitot not found")


# Humidity temperature sensor
sbs = None
def crc8(b0, b1):
    crc = 0xFF
    crc ^= b0;
    for i in range(8):
        crc = (((crc << 1) ^ 0x31) if (crc & 0x80) else (crc << 1)) & 0xFF
    crc ^= b1
    for i in range(8):
        crc = (((crc << 1) ^ 0x31) if (crc & 0x80) else (crc << 1)) & 0xFF
    return crc
    
if 0x44 in i2cdevices:
    try:
        i2c.writeto(0x44, b'\xF3\x2D')    # SHT31_READSTATUS
        k = i2c.readfrom(0x44, 3)
        print(k, hex(crc8(k[0], k[1])))
        i2c.writeto(0x44, b'\x30\xA2')    # SHT31_SOFTRESET
        time.sleep(0.1)
        i2c.writeto(0x44, b'\x27\x37')    # read 10Hz?
        time.sleep(0.1)
        i2c.writeto(0x44, b'\xF3\x2D')    # SHT31_READSTATUS
        k = i2c.readfrom(0x44, 3)
        print(k, hex(crc8(k[0], k[1])))
    except OSError:
        pass
    print("SHT31D found")
    sbs = bytearray("St00000000r0000a0000\n")
    msbs = memoryview(sbs)
    tstampsht31 = 0
else:
    print("SHT31D not found")


# bme280 temp, humid, baro meter    
mbs = None
if 0x77 in i2cdevices:
    try:
        from bme280 import bme280gen
        bme280iter = bme280gen(i2c)
    except OSError:
        pass
    mbs = bytearray("Mt00000000t0000h0000b000000\n")
    mmbs = memoryview(mbs)
    tstampbme280 = 0
    print("BME280 found")
else:
    print("BME280 not found")

    
def readi2cdevices(tstamp):
    global tstamppx4, tstampsht31, tstampbme280
    if xbs != None:
        if tstamppx4 == 0:
            tstamppx4 = tstamp + px4readrate
            x = i2c.readfrom(0x28, 4)
            #status = x[0] & 0xC0  # should be zero
            rawpress = ((x[0] & 0xFF) << 8) | (x[1])
            #rawpress = ((x[0] & 0x3F) << 8) | (x[1])
            rawtemp = (x[2] << 3) | (x[3] >> 5)
            mxbs[2:10] = b"%08X" % tstamp
            mxbs[11:15] = b"%04X" % rawpress
            mxbs[16:20] = b"%04X" % rawtemp
            return xbs
            #psi = rawpress*(1.0/(0x3FFF*0.4)) - 1.25
            #temp = rawtemp*200.0/0x7FF - 50
        elif tstamp > tstamppx4:
            tstamppx4 = 0
            i2c.writeto(0x28, b"")

    if sbs != None and tstamp > tstampsht31:
        tstampsht31 = tstamp + sht31readrate
        i2c.writeto(0x44, b'\xE0\x00')
        k = i2c.readfrom(0x44, 6)
        if k[2] == crc8(k[0], k[1]) and k[5] == crc8(k[3], k[4]):
            rawtemp = (k[0]<<8) | k[1]
            rawhumid = (k[3]<<8) | k[4]
            msbs[2:10] = b"%08X" % tstamp
            msbs[11:15] = b"%04X" % rawhumid
            msbs[16:20] = b"%04X" % rawtemp

            stemp = (rawtemp * 175)/0xFFFF - 45
            shumid = (rawhumid*100)/0xFFFF
            print(stemp, shumid)
            return sbs

    if mbs != None and tstamp > tstampbme280:
        tstampbme280 = tstamp + bme280readrate
        temp, baro, humid = next(bme280iter)
        mmbs[2:10] = b"%08X" % tstamp
        mmbs[11:15] = b"%04X" % (int(temp/100*0x8000)&0xFFFF)
        mmbs[16:20] = b"%04X" % (int(humid/100*0x8000)&0xFFFF)
        mmbs[21:27] = b"%06X" % (int(baro*100)&0xFFFFFF)
        return mbs
            
    return None


