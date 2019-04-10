import threading, socket, queue
import numpy, pandas
import math, time, datetime, random

# Connect to RTKNAVI_Qt-x86_64.AppImage, 
# For running from phone:
#   * Rover TCP client 192.168.43.1 9042 cmd -AAA
#   * Base TCP client 192.168.43.1 9042 cmd -CCC
# Click on "O" and set:
#   * TCP Server, (127.0.0.1) option port 9060

# Connect using command line server,
#   /home/julian/extrepositories/RTKLIB-rtkexplorer/app/rtkrcv/gcc/rtkrcv -s -o /home/julian/repositories/RTK_on_the_beach/conf/csingle.conf


columnnames = "%  GPST                  latitude(deg) longitude(deg)  height(m)   Q  ns   sdn(m)   sde(m)   sdu(m)  sdne(m)  sdeu(m)  sdun(m) age(s)  ratio".split()

class PositionBank(threading.Thread):
    def __init__(self, port=9063):
        threading.Thread.__init__(self, daemon=True)

        self.lng0, self.lat0 = None, None
        self.earthrad = 6378137
        self.nyfac = 2*math.pi*self.earthrad/360
        
        self.Narrsize = 300
        self.pdposarrays = [ ]
        self.pdposarray = None
        self.n = 0
        self.t, self.x, self.y, self.z = 0, 0, 0, 0
        self.port = port
        
        self.socketconnected = None
        self.sockerrfile = None
        self.srow = None
        self.lastexception = None
        
        self.queuepoints = queue.Queue(1)
        
    def parsexyz(self, row):
        srow = row.split()
        t = pandas.to_datetime(srow[0]+" "+srow[1])
        lat, lng, height = float(srow[2]), float(srow[3]), float(srow[4])
        if self.lng0 is None:
            self.lng0, self.lat0 = lng, lat
        exfac = self.nyfac*math.cos(math.radians(self.lat0))
        return t, (lng - self.lng0)*exfac, (lat - self.lat0)*self.nyfac, height
    
    def newposition(self, t, x, y, z):
        self.t, self.x, self.y, self.z = t, x, y, z
        if self.n == self.Narrsize:
            self.pdposarrays.append(self.pdposarray)
            self.pdposarray = None
        if self.pdposarray is None:
            self.pdposarray = pandas.DataFrame(index=range(self.Narrsize))
            self.pdposarray["t"] = pandas.to_datetime("")
            self.pdposarray["x"] = 0
            self.pdposarray["y"] = 0
            self.pdposarray["z"] = 0
            self.n = 0
        self.pdposarray.iloc[self.n] = (t, x, y, z)
        self.n += 1
        if not self.queuepoints.full():
            self.queuepoints.put_nowait((x, y))
        
    def generaterandomposforever(self):
        rpm = 0
        rad = 15
        sd = 1
        t0 = time.time()
        zfac = 0.1
        while True:
            theta = 360*(time.time() - t0)/60
            t = pandas.to_datetime(datetime.datetime.now().isoformat())
            x = math.cos(math.radians(theta))*rad + random.gauss(0, sd)
            y = math.sin(math.radians(theta))*rad + random.gauss(0, sd)
            z = math.cos(math.radians(theta*3))*rad*zfac + random.gauss(0, sd*zfac) + 100
            self.newposition(t, x, y, z)
            time.sleep(0.2)
        
    def connectreadfromportforever(self):
        self.socketconnected = socket.socket()
        print("connecting to port", self.port)
        self.socketconnected.connect(socket.getaddrinfo("127.0.0.1", self.port)[0][-1])
        self.sockerrfile = self.socketconnected.makefile('rwb', 0)
        print("port", self.port, "open")
        self.srow = self.sockerrfile.readline()
        print(self.srow)
        while True:
            self.srow = self.sockerrfile.readline()  # hangs
            p = self.parsexyz(self.srow.decode())
            self.newposition(p[0], p[1], p[2], p[3])
            time.sleep(0.05)
            

    def run(self):
        while True:
            try:
                if self.port == "random":
                    self.generaterandomposforever()
                else:
                    self.connectreadfromportforever()
            except ConnectionRefusedError as e:
                print(e, type(e))
                self.lastexception = e
                time.sleep(2)
            except ValueError as e:
                print(e, type(e))
                self.lastexception = e
            except Exception as e:
                self.lastexception = e
                print(e, type(e))
                break  # might be a syntax error
                

                
# socket for sending PWM instructons back to the device
class DarknessMeasureFlash(threading.Thread):
    
    def __init__(self, queuepoints, imgplot, port=9042):
        threading.Thread.__init__(self, daemon=True)
        self.queuepoints = queuepoints
        self.imgplot = imgplot
        self.port = port
        self.socketconnectedFlash = None
        self.sockerrfileFlash = None
        self.lastexception = None
        self.tprevflash = 0
    
    def getunderpixelQ(self, wx, wy):
        if self.imgplot is None:
            return -1
        def wpix(w, wextlo, wexthi, imgw):
            wl = (w - wextlo)/(wexthi - wextlo)
            iw = int(math.floor(wl*imgw + 0.5))
            return iw
        ext = self.imgplot.get_extent()
        imgshape = self.imgplot._A.shape
        ix = wpix(wx, ext[0], ext[1], imgshape[1])
        iy = imgshape[0] - wpix(wy, ext[2], ext[3], imgshape[0])
        if 0 <= ix < imgshape[1] and 0 <= iy < imgshape[0]:
            return self.imgplot._A[iy][ix].mean()
        return -1
    
    def sendflash(self, fp):
        if fp == -1:
            freq, duty = 1, 800
        elif fp < 0.5:
            freq, duty = 1, 500*(fp*2)
        else:
            freq, duty = int(1 + (fp-0.4999)*10), 500
            
        # quick hack to avoid PWMs being before they have done a proper flash
        tflash = time.time()
        tsecdiff = tflash - self.tprevflash
        tsecdiff = tsecdiff - math.floor(tsecdiff)
        time.sleep(tsecdiff*0.95)
        
        self.socketconnectedFlash.send(b"%d %d\n" % (freq, duty))
    

    def run(self):
        while True:
            try:
                self.socketconnectedFlash = socket.socket()
                print("flash connecting")
                self.socketconnectedFlash.connect(socket.getaddrinfo("192.168.43.1", self.port)[0][-1])
                self.sockerrfileFlash = self.socketconnectedFlash.makefile('rwb', 0)
                row = self.sockerrfileFlash.readline()
                print("flash", row)
                self.socketconnectedFlash.send(b"+AAA")
                while True:
                    wx, wy = self.queuepoints.get()
                    fp = self.getunderpixelQ(wx, wy)
                    self.sendflash(fp)
                    
            except ConnectionRefusedError as e:
                print(e, type(e))
                self.lastexception = e
                time.sleep(2)
            except ValueError as e:
                print(e, type(e))
                self.lastexception = e
            except Exception as e:
                self.lastexception = e
                print(e, type(e))
                break  # might be a syntax error

