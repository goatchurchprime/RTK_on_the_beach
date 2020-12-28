import numpy, pandas
import datetime, math, re 

# find digital terrain models at https://dds.cr.usgs.gov/srtm/version2_1/SRTM3/Eurasia/

def linfuncF(lin):
    t = int(lin[2:10], 16)
    p = int(lin[11:17], 16)
    return t, p
    
def s16(sx):  
    x = int(sx, 16)
    return x - 65536 if x >= 32768 else x
def linfuncZ(line):
    t = int(line[2:10], 16)
    ax, ay, az = s16(line[11:15])*0.01, s16(line[16:20])*0.01, s16(line[21:25])*0.01        # acceleration
    gx, gy, gz = s16(line[26:30])*0.01, s16(line[31:35])*0.01, s16(line[36:40])*0.01        # gravity
    q0, q1, q2, q3 = s16(line[41:45]), s16(line[46:50]), s16(line[51:55]), s16(line[56:60]) # quaternion 
    s = int(line[61:63], 16)
    if q0 == 0 and q1 == 0 and q2 == 0 and q3 == 0:  
        raise ValueError()
    #if max(abs(ax), abs(ay), abs(az))>50:
    #    raise ValueError()
    return (t, ax, ay, az, gx, gy, gz, q0, q1, q2, q3, s)

def processZquat(pZ):
    pZ["iqsq"] = 1/((pZ.q0**2 + pZ.q1**2 + pZ.q2**2 + pZ.q3**2))  # quaternion unit factor
    pZ["pitch"] = numpy.degrees(numpy.arcsin((pZ.q2*pZ.q3 + pZ.q0*pZ.q1)*2 * pZ.iqsq))
    pZ["roll"] = numpy.degrees(numpy.arcsin((pZ.q1*pZ.q3 - pZ.q0*pZ.q2)*2 * pZ.iqsq))
    a00 = (pZ.q0**2 + pZ.q1**2)*2 * pZ.iqsq - 1
    a01 = (pZ.q1*pZ.q2 + pZ.q0*pZ.q3)*2 * pZ.iqsq
    heading = 180 - numpy.degrees(numpy.arctan2(a00, -a01))
    #pZ["heading"] = heading  # below is code to unwind the heading.  get back to original by doing mod 360
    pZ["heading"] = heading + 360*numpy.cumsum((heading.diff() < -180)*1 - (heading.diff() > 180)*1)
    pZ["bad"] = (abs(pZ.ax)>50) | (abs(pZ.ay)>50) | (abs(pZ.az)>50)
    return pZ
    
def processZquatA(pZ):  # the sensor from the phone
    pZ["q0"] = numpy.sqrt(1 - pZ.q1**2 - pZ.q2**2 - pZ.q3**2)
    pZ["roll"] = numpy.degrees(numpy.arcsin((pZ.q2*pZ.q3 + pZ.q0*pZ.q1)*2))
    pZ["pitch"] = numpy.degrees(numpy.arcsin((pZ.q1*pZ.q3 - pZ.q0*pZ.q2)*2))
    a00 = (pZ.q0**2 + pZ.q1**2)*2 - 1
    a01 = (pZ.q1*pZ.q2 + pZ.q0*pZ.q3)*2
    heading = 180 - numpy.degrees(numpy.arctan2(a00, -a01))
    #pZ["heading"] = heading  # below is code to unwind the heading.  get back to original by doing mod 360
    pZ["heading"] = heading + 360*numpy.cumsum((heading.diff() < -180)*1 - (heading.diff() > 180)*1)
    return pZ

def linfuncE(line):
    t = int(line[2:10], 16)
    m = int(line[11:13], 16)
    d = int(line[14:18], 16)
    return (t, m, d)

Fkphmpsfac = 0.01*1000/3600

def linfuncV(line):
    t = int(line[2:10], 16)
    v = int(line[11:15], 16)
    d = int(line[16:22], 16)
    if d > 65000:
        d -= 65536
    devno = int(1 if len(line) == 23 else (ord(line[22])-65))  # ord('A')
    return (t, v*Fkphmpsfac, d*0.01, devno)

def TimeFlightStartEndV(pV):  
    avgsecs, clearsamples = 3, 4
    k = pV.vel.resample("%dms" % avgsecs*1000).max()
    backoffset = pandas.Timedelta(seconds=avgsecs*clearsamples)
    return k[k>5].index[clearsamples] - backoffset, k[k>5].index[-1-clearsamples] + backoffset

def linfuncN(line):
    t = int(line[2:10], 16)
    s = int(line[11:17], 16)
    return (t, s)

def linfuncG(line):
    t = int(line[2:10], 16)
    h = int(line[11:15], 16)
    d = int(line[16:20], 16)
    return (t, h*(125.25/65536) - 6, d*(175.25/65536) - 46.85)

def linfuncS(line):
    t = int(line[2:10], 16)
    h = int(line[11:15], 16)
    d = int(line[16:20], 16)
    return (t, h*(100.0/65535), d*(175.0/65535) - 45.0)

def linfuncI(line):
    t = int(line[2:10], 16)
    dI = int(line[11:15], 16)
    dIA = int(line[16:20], 16)
    return (t, dI*0.02 - 273.15, dIA*0.02 - 273.15)

def linfuncB(line):
    t = int(line[2:10], 16)
    p = int(line[11:17], 16)
    c = int(line[18:22], 16)
    return (t, p, c*0.01)

def linfuncX(line):
    t = int(line[2:10], 16)
    dp8 = int(line[11:19], 16)
    dp = dp8*(3/2)/8   # missing factor and 8 fold sum
    c = int(line[20:24], 16)
    wn = int(line[25:29], 16)
    wr = int(line[30:38], 16)
        # if the wind duration extends back by more than the sample rate, then we can fill the average value into that spot too by backdating it and over-writing its zero
    return (t, (dp/(0x3FFF*0.4) - 1.25)*6894.75728, c*(200.0/0x7FF) - 50, (80000*wn/wr if wr != 0 else 0))

def linfuncL(lin):
    t = int(lin[2:10], 16)
    l = int(lin[11:17], 16)
    return t, l

def linfuncU(lin):
    t = int(lin[2:10], 16)
    u = int(lin[11:17], 16)
    return t, u

def s32(sx):  
    x = int(sx, 16)
    return x - 0x100000000 if x >= 0x80000000 else x
def linfuncQ(lin):
    if not 43 <= len(lin) <= 44:  # (includes \n)
        raise ValueError()
    t = int(lin[2:10], 16)
    u = int(lin[11:19], 16)    # this is milliseconds since midnight
    if u == 0:
        raise ValueError()     # this can be useful as an index for merging
    y = s32(lin[20:28])
    x = s32(lin[29:37])
    a = int(lin[38:42], 16)
    if a == 0xFFFF or a <= 50:
        raise ValueError()
    devno = int(1 if len(lin) == 43 else (ord(lin[42])-65))  # ord('A')
    return t, u, x/600000, y/600000, a*0.1, devno

def linfuncR(lin):
    t = int(lin[2:10], 16)
    d = lin[12:35]
    epochd = datetime.datetime.strptime(d[:19], "%Y-%m-%dT%H:%M:%S")
    e = int(lin[36:45], 16)
    n = int(lin[46:54], 16)
    f = int(lin[55:63], 16)
    o = int(lin[64:72], 16)
    print("linfuncR", t, d)
    devno = int(1 if len(lin) == 73 else (ord(lin[72])-65))  # ord('A')
    return t, epochd.timestamp(), e, n, f, o, devno

# if the plot looks wrong, don't forget to check the aspect ratio and force it like this:
#plt.figure(figsize=(10, 20))
#plt.subplot(111, aspect="equal")
lng0, lat0 = 0, 0  # make things easier, we don't want different origins really
# set them with processQaddrelEN("setorigin", (lng, lat))
nyfac0, exfac0 = 0, 0  # multiply by 1/60000 to find the precision of the IGC file

def processQaddrelEN(pQ, fd=None):
    global lng0, lat0, nyfac0, exfac0
    if type(pQ) == str and pQ == "setorigin":
        lng0, lat0 = fd
        return
    if fd is None:
        if len(pQ) != 0 and lng0 == 0 and lat0 == 0:
            ph = pQ.iloc[min(10, len(pQ)-1)]    # set the origin we use for all the conversions
            lng0, lat0 = ph.lng, ph.lat
    else: 
        if len(pQ) != 0 and fd.lng0 == 0 and fd.lat0 == 0:
            if lng0 == 0 and lat0 == 0:
                ph = pQ.iloc[min(10, len(pQ)-1)]    # set the origin we use for all the conversions
                fd.lng0, fd.lat0 = ph.lng, ph.lat
            else:
                fd.lng0, fd.lat0 = lng0, lat0
        lng0, lat0 = fd.lng0, fd.lat0
    earthrad = 6378137
    nyfac = 2*math.pi*earthrad/360
    exfac = nyfac*math.cos(math.radians(lat0))
    if fd:
        fd.nyfac = nyfac
        fd.exfac = exfac
    nyfac0 = nyfac
    exfac0 = exfac
        
    # vector computations
    pQ["x"] = (pQ.lng - lng0)*exfac  
    pQ["y"] = (pQ.lat - lat0)*nyfac
    
    pQmean = pQ.mean()
    lenpQ = len(pQ)
    pQ = pQ[(abs(pQ.lat - pQmean.lat)<1) & (abs(pQ.lng - pQmean.lng)<1)]
    if lenpQ != len(pQ):
        print("despiked", lenpQ-len(pQ), "points from Q")
    return pQ
    
        
def linfuncW(lin):  
    t = int(lin[2:10], 16)
    w = int(lin[11:15], 16)
    n = int(lin[16:24], 16)
    if w == 0xFFFF:
        raise ValueError()
    return t, w, n
    
def linfuncAF(lin):
    t = int(lin[3:11], 16)
    p = int(lin[12:18], 16)
    return t, p
    
def linfuncAZ(line):
    t = int(line[3:11], 16)
    q1, q2, q3 = s16(line[12:16])/32768, s16(line[17:21])/32768, s16(line[22:26])/32768        # quaternion 
    return (t, q1, q2, q3)

def linfuncAQ(lin):
    t = int(lin[3:11], 16)
    u = int(lin[12:20], 16)
    y = s32(lin[21:29])
    x = s32(lin[30:38])
    a = int(lin[39:43], 16)
    if a == 0xFFFF or a <= 50:
        raise ValueError()
    return t, u, x/600000, y/600000, a*0.1

def linfuncAV(line):
    t = int(line[3:11], 16)
    v = int(line[12:16], 16)
    d = int(line[17:21], 16)
    return (t, v*0.01, d*0.1)

def linfuncAU(lin):
    t = int(lin[3:11], 16)
    u = int(lin[12:18], 16)
    return t, u

def linfuncAA(lin):
    t = int(lin[3:11], 16)
    ax, ay, az = s16(line[12:16])/32768, s16(line[17:21])/32768, s16(line[22:26])/32768
    return (t, ax, ay, az)

recargsE = ('E', linfuncE, ["m", "d"])
recargsW = ('W', linfuncW, ["w", "n"]) 
recargsR = ('R', linfuncR, ["epoch", "e", "n", "f", "o", "devno"]) 
recargsF = ('F', linfuncF, ["Pr"]) 
recargsZ = ('Z', linfuncZ, ["ax", "ay", "az", "gx", "gy", "gz", "q0", "q1", "q2", "q3", "s"]) 
recargsY = ('Y', linfuncZ, ["ax", "ay", "az", "gx", "gy", "gz", "q0", "q1", "q2", "q3", "s"]) 
recargsV = ('V', linfuncV, ["vel", "deg", "devno"])    # Vt000717A0v0050d002EE0
recargsG = ('G', linfuncG, ["hG", "tG"])   # si7021Humidity meter
recargsS = ('S', linfuncS, ["hS", "tS"])   # Humidity31 meter
recargsI = ('I', linfuncI, ["tI", "tIA"]) 
recargsB = ('B', linfuncB, ["Prb", "tB"]) 
recargsL = ('L', linfuncL, ["Lg"]) 
recargsU = ('U', linfuncU, ["Dust"]) 
recargsQ = ('Q', linfuncQ, ["u", "lng", "lat", "alt", "devno"]) 
recargsX = ('X', linfuncX, ["Dmb", "tX", "wms"]) 
recargsN = ('N', linfuncN, ["sN"])   # nickel wire
recargsAF = ('aF', linfuncAF, ["Pr"])
recargsAZ = ('aZ', linfuncAZ, ["q1", "q2", "q3"])
recargsAQ = ('aQ', linfuncAQ, ["u", "lng", "lat", "alt"])
recargsAV = ('aV', linfuncAV, ["vel", "deg"])
recargsAU = ('aU', linfuncAU, ["b"]) 
recargsAA = ('aA', linfuncAA, ["ax", "ay", "az"])


# Grab the function lookups from above (hacky, should put into own object)
recargsDict = { }
for k, v in globals().copy().items():
    if 8 <= len(k) <= 9 and k[:7] == "recargs" and k[-1] == v[0][-1]:
        recargsDict[v[0]] = v
        

rectypes = 'EDFLQRVWYZUCPHISGNMOBX*'
phrectypes = set('FZQVUA')

def GLoadIGC(fname):
    fin = open(fname, "rb")   # sometimes get non-ascii characters in the header
    IGCdatetime0 = None
    recs, tind = [ ], [ ]
    hfcodes = { }
    for l in fin:
        if l[:5] == b'HFDTE':    #  HFDTE090317
            l = l.decode("utf8") 
            if l.find(":") != -1:
                l = l[l.find(":")+1:]
            else:
                l = l[5:]
            hfcodes["HFDTE"] = l
            IGCdatetime0 = pandas.Timestamp("20"+l[4:6]+"-"+l[2:4]+"-"+l[0:2])
        elif l[:2] == b'HF' and l.find(b":") != -1:
            k, v = l[2:].split(b":", 1)
            if v.strip():
                hfcodes[k.decode()] = v.decode().strip()
        elif l[0] == ord("B"):   #  B1523345257365N00308169WA0030800393000
            utime = int(l[1:3])*3600+int(l[3:5])*60+int(l[5:7])
            latminutes1000 = int(l[7:9])*60000+int(l[9:11])*1000+int(l[11:14])
            lngminutes1000 = (int(l[15:18])*60000+int(l[18:20])*1000+int(l[20:23]))*(l[23]==ord('E') and 1 or -1) 
            s = int(l[35:]) if len(l) >= 40 else 0
            recs.append((latminutes1000/60000, lngminutes1000/60000, int(l[25:30]), int(l[30:35]), s, utime*1000))
            tind.append(IGCdatetime0 + pandas.Timedelta(seconds=utime))
    w = pandas.DataFrame.from_records(recs, columns=["lat", "lng", "alt", "altb", "s", "u"], index=tind)
    if max(w.alt) == 0:
        w.drop(["alt"], 1, inplace=True)
    if max(w.altb) == 0:
        w.drop(["altb"], 1, inplace=True)
    return w, hfcodes

def GLoadRTKpos(fname): # made by RTKLIB as output
    GPS_UTC_SECONDS_DIFFERENCE = -18
    for sr, l in enumerate(open(fname)):
        if l[0] != "%":
            break
    w = pandas.read_csv(fname, skiprows=sr-1, sep="\s+")
    w.rename(columns={"latitude(deg)":"lat", "longitude(deg)":"lng", "height(m)":"alt"}, inplace=True)
    if 'UTC' in w.columns:
        w["time"] = pandas.to_datetime(w["%"]+" "+w["UTC"])
        w.drop(["%", "UTC"], 1, inplace=True)
    else:
        w["time"] = pandas.to_datetime(w["%"]+" "+w["GPST"]) + pandas.Timedelta(seconds=GPS_UTC_SECONDS_DIFFERENCE)
        w.drop(["%", "GPST"], 1, inplace=True)
    w["sd"] = numpy.sqrt(w["sdn(m)"]**2 + w["sde(m)"]**2 + w["sdu(m)"]**2)
    w.set_index("time", inplace=True)
    w.index.name = None
    return w


class FlyDat:
    "Flight data object; use LoadC() to actually load the data from the file"
    def __init__(self, fname=None, fdother=None, knowndate=None, lc="QV"):
        # set the origin for the latlng offsets
        self.lng0, self.lat0 = 0, 0
        self.ft0, self.ft1 = None, None  # flight time start and end
        self.t0, self.t1 = self.ft0, self.ft1
        self.Rdatetime0 = None   # approx UTC time of milliseconds=0, used to offset sensor timestamps to match GPS
        self.aRdatetime0 = None  # UTC time of milliseconds=0 used in android phone values
        self.Rdatetime0byinterleave = None  # derived time on sensor from phone times 
        self.pIGCs = [ ]
        self.pPOSs = [ ]
        self.varioFfilter = 0.02
        
        if fname and knowndate is None:
            mdates = list(re.finditer("\d\d\d\d-\d\d-\d\d", fname))
            if mdates:
                mdate = mdates[-1]  # last element because directory name can be wrong
                knowndate = mdate.group(0)
                print("Extracting knowndate from filename:", knowndate)
        if knowndate is not None:
            self.timestampmidnight = pandas.Timestamp(knowndate)
        elif fdother is not None:
            self.timestampmidnight = fdother.timestampmidnight
            self.lng0, self.lat0 = fdother.lng0, fdother.lat0
        else:
            self.timestampmidnight = None

        self.fname = fname
        if self.fname is None:
            return
            
        # initiating with IGC type
        if self.fname[-4:].lower() == ".igc":
            pIGC, hfcodes = GLoadIGC(self.fname)
            self.pIGC = processQaddrelEN(pIGC, self)
            self.timestampmidnight = pandas.Timestamp(self.pIGC.index[0].date())
            self.ft0, self.ft1 = self.pIGC.index[0], self.pIGC.index[-1] 
            self.t0, self.t1 = self.ft0, self.ft1
            self.bnoLOG = True
            self.pQ = self.pIGC
            self.pIGCs.append(self.pIGC)
            return
            
        # initiating with IGC type
        if self.fname[-4:].lower() == ".pos":
            pPOS = GLoadRTKpos(fname)
            self.timestampmidnight = pandas.Timestamp(pPOS.index[0].date())
            pPOS["u"] = (pPOS.index - self.timestampmidnight)/pandas.Timedelta(milliseconds=1)
            self.pPOS = processQaddrelEN(pPOS, self)
            self.ft0, self.ft1 = self.pPOS.index[0], self.pPOS.index[-1] 
            self.t0, self.t1 = self.ft0, self.ft1
            self.bnoLOG = True
            self.pQ = self.pPOS
            self.pPOSs.append(self.pPOS)
            return
            
        # load the log file
        self.bnoLOG = False
        self.reccounts = dict((r, 0)  for r in rectypes)
        self.reccounts.update(dict(("a"+r, 0)  for r in phrectypes))

        # skip past the header part of the flydat file
        self.fin = open(self.fname)  # file is kept open and we use seek to go back to start of data to rescan for another data record type
        while self.fin.readline().strip():  
            pass
        self.headerend = self.fin.tell()
        prev2lin = None
        prev1linA = None
        linAdiffsum = 0
        linAdiffcount = 0
        try:
            for lin in self.fin:
                #Rt[ms]d"[isodate]"e[latdE]n[latdN]f[lngdE]o[lngdN] GPS cooeffs
                if lin[0] == "R":  # R-type was the intro to first GPS record setting the origin
                    print("undebugged R record", lin)
                    rms = int(lin[2:10], 16)
                    rdd = pandas.to_datetime(lin[12:35])
                    self.timestampmidnight = pandas.Timestamp(lin[12:22])
                    Rdatetime0 = rdd - pandas.Timedelta(milliseconds=rms)
                    if self.Rdatetime0 is None or abs(Rdatetime0 - self.Rdatetime0).value > 1e9:
                        self.Rdatetime0 = Rdatetime0
                        print("Rdatetime0", self.Rdatetime0, "at", rms*0.001)
                elif lin[1] == "R":  # aR-type was the intro to first GPS record setting the origin
                    rms = int(lin[3:11], 16)
                    self.aRdatetime0 = pandas.to_datetime(lin[13:36])
                    aRdatetime0midnight = pandas.Timestamp(lin[13:23])
                    if self.timestampmidnight is None:
                        self.timestampmidnight = aRdatetime0midnight
                    elif self.timestampmidnight != aRdatetime0midnight:
                        print("Error: Should be same midnight stamps", self.timestampmidnight, aRdatetime0midnight)
                        
                elif lin[0] in self.reccounts:
                    self.reccounts[lin[0]] += 1
                    if prev1linA is not None and prev2lin:  # find sequence of 3 values to fit the timing between
                        lin2t = int(prev2lin[2:10], 16)
                        lin1At = int(prev1linA[3:11], 16)
                        lint = int(lin[2:10], 16)
                        linAdiffsum += lin1At - (lint + lin2t)/2
                        linAdiffcount += 1
                    prev2lin = lin
                    prev1linA = None
                    
                elif lin[0] == "a" and lin[1] in phrectypes:
                    self.reccounts[lin[:2]] += 1
                    prev1linA = lin
                else:
                    print("badline", lin)

        except KeyError:
            print("Bad line", lin, "at post header line", sum(self.reccounts.values()))
            raise
        #if self.Rdatetime0 is None:
        #    self.Rdatetime0 = self.timestampmidnight or pandas.to_datetime("2000")
        print(", ".join("%s:%d"%(c, d)  for c, d in self.reccounts.items()  if d != 0))

        if linAdiffcount != 0:
            print("linAdifftime", linAdiffsum/linAdiffcount, "count", linAdiffcount)
            self.Rdatetime0byinterleave = self.aRdatetime0 + pandas.Timedelta(milliseconds=linAdiffsum/linAdiffcount)
        
        if lc is not None and lc:
            nloaded = self.LoadA(lc)
                
        if self.t0 is None:
            if self.Rdatetime0byinterleave is not None:
                self.t0 = self.Rdatetime0byinterleave
                print("Missing GPS data, so setting t0 to", self.Rdatetime0byinterleave)
            else:
                self.t0 = pandas.Timestamp("2000-01-01")
                print("No absolute time found", self.t0)
            

    def LoadLType(self, c, linfunc, columns):
        if isinstance(columns, int):
            width = columns
            columns = None
        else:
            width = len(columns)+1
        k = numpy.zeros((self.reccounts[c], width))
        self.fin.seek(self.headerend)
        i = 0
        badvalues = [ ]
        if len(c) == 1:
            for lin in self.fin:
                if lin[0] == c:
                    try:
                        k[i] = linfunc(lin)
                        i += 1
                    except ValueError:
                        badvalues.append((i, lin))
        else: # (above is to make it faster in single character case; this is a[QVF] case)
            for lin in self.fin:
                if lin[:len(c)] == c:
                    try:
                        k[i] = linfunc(lin)
                        i += 1
                    except ValueError:
                        badvalues.append((i, lin))
                    
        if badvalues:
            print("BAD VALUES", len(badvalues), badvalues[:3])
        print("Made for", c, self.reccounts[c], "last index", i)
        if not columns:
            return k
        if c[0] == "a":
            ld0 = self.aRdatetime0
        elif self.Rdatetime0 is not None:
            ld0 = self.Rdatetime0
        elif c == "Q":
            ld0 = self.timestampmidnight   # incorrect midnight offset worked on later when Rdatetime0 gets set
        elif self.Rdatetime0byinterleave: 
            if len(k) != 0:
                print("Warning, using guessed (not GPS) timing corrected value on", c, len(k))
            ld0 = self.Rdatetime0byinterleave
        else:
            ld0 = pandas.Timestamp("2000-01-01")
            
        tsindex = pandas.DatetimeIndex(ld0 + pandas.Timedelta(milliseconds=dt)  for dt in k[:i,0])
        res = pandas.DataFrame(k[:i,1:], columns=columns, index=tsindex)  # generate the dataframe from the numpy thing
        if c == "Q":
            res["t_ms"] = k[:i,0]
        return res
        
    
    def LoadC(self, lc=None):
        "Load category of flight data: DFLQRVWYZUCPHISGNMOBX"
        if lc is None:
            print("Specify which data to load")
            for r, n in self.reccounts.items():
                print("%s(n=%d) %s" % (r, n, recargsDict.get(r, ["","","unknown"])[2]))
            return 0
        
        prevandroid = False
        nloaded = 0
        for c in lc:
            if c == "a":
                prevandroid = True
                continue
            pCattrname = ("a" if prevandroid else "p")+c
            if hasattr(self, pCattrname):
                if len(self.__getattribute__(pCattrname)) != 0:
                    nloaded += 1
                continue

            Lc, linfunc, columns = recargsDict["a"+c  if prevandroid else c]
            pC = self.LoadLType(Lc, linfunc, columns)
            
            # reset the pQ type to use true GPS times in the u parameter, and improve the microcontroller timestamps offset
            if pC.size != 0:
                print("pCattrname", pCattrname)
                if pCattrname == 'aQ':
                    pC = processQaddrelEN(pC, self)
                    aQ = pC
                    aQ["t_ms"] = (aQ.index - self.aRdatetime0)/pandas.Timedelta(1e6)  # recover the original numbers
                    aQ["uT"] = self.timestampmidnight + aQ.u*pandas.Timedelta(1e6)
                    aQ.set_index(["uT"], inplace=True)
                    aQ.index.name = None
                    gpstimestampdiff = (aQ.index - self.timestampmidnight).astype(int)/1e6 - aQ.t_ms
                    #gpstimestampdiff = gpstimestampdiff.to_series()
                    orgaRdatetime0 = self.aRdatetime0
                    self.aRdatetime0 = self.timestampmidnight + pandas.Timedelta(gpstimestampdiff.mean()*1e6)
                    print("Setting aRdatetime0 %s from %s with std %.2f" % (str(self.aRdatetime0), str(orgaRdatetime0), gpstimestampdiff.std()))
                
                if pCattrname == 'pQ':
                    pQ = pC
                    pQ["uT"] = self.timestampmidnight + pQ.u*pandas.Timedelta(1e6)
                    pQ = processQaddrelEN(pC, self)

                    # recalculate the Rdatetime0 by using the average offset, removing any outliers, made complicated by the outliers pulling the mean far away
                    # (Possibly bad values from corrupt data of bluefly badly interleaving GPS and PRS data without enough checksum checking)
                    if pQ.size != 0:
                        gpstimestampdiff1 = pQ.u - pQ.t_ms
                        gpstimestampdiff1mean = gpstimestampdiff1.mean()
                        gpstimestampdiff1meandiff = (gpstimestampdiff1 - gpstimestampdiff1mean).values
                        gpstimestampdiff1meandiff.sort()
                        nthird = len(gpstimestampdiff1meandiff)//3
                        gpstimestampdiff1meandiffmean = gpstimestampdiff1meandiff[nthird:-nthird].mean()
                        gpstimestampdiff2 = gpstimestampdiff1[numpy.abs(gpstimestampdiff1 - gpstimestampdiff1mean - gpstimestampdiff1meandiffmean) < 1000]  # filter spikes
                        gpstimestampdiff2mean = gpstimestampdiff2.mean()
                        gpstimestampdiff1mean, gpstimestampdiff2mean

                        self.Rdatetime0 = self.timestampmidnight + pandas.Timedelta(gpstimestampdiff2mean*1e6)
                        print("Setting new Rdatetime0 %s with std %.2f" % (str(self.Rdatetime0), gpstimestampdiff2.std()))
                        
                        Qudiff = abs(gpstimestampdiff1 - gpstimestampdiff2mean)
                        pQ = pQ[Qudiff<200]  # really filter any disagreement between microtime and GPS time of more than 200ms
                        
                        Ndiscards, Nbacktimes = len(pC) - len(pQ), sum(pQ.u.diff()<0)
                        if Ndiscards:
                            print("Discarding %d points due to time/GPStime disagreements" % Ndiscards)
                        if Nbacktimes:
                            print("Warning %d points go back in GPStime" % Nbacktimes)
                        
                        pQ.set_index(["uT"], inplace=True)
                        pQ.index.name = None

                    pC = pQ
                    
                
                if self.ft0 is None:
                    self.ft0, self.ft1 = pC.index[0], pC.index[-1]
                    self.t0, self.t1 = self.ft0, self.ft1
                if pCattrname == "pV":
                    try:
                        self.ft0, self.ft1 = TimeFlightStartEndV(pC)
                    except IndexError:
                        print("timeflightindexerror")
                        self.ft0, self.ft1 = pC.index[0], pC.index[-1]
                    self.t0, self.t1 = self.ft0, self.ft1
                    pC.deg = pC.deg + 360*numpy.cumsum((pC.deg.diff() < -180)*1 - (pC.deg.diff() > 180)*1) # unwrap the circular winding

            if pCattrname in ["pQ", "pR", "pV"]:  # devno type for secondary GPS to split out
                pC0 = pC[pC.devno == 0].drop("devno", 1)  # top shelf spare gps
                pC = pC[pC.devno == 1].drop("devno", 1)   # lower shelf bluefly device
                if len(pC0):
                    self.__setattr__(pCattrname+"0", pC0)
            if pCattrname == "pZ" or pCattrname == "pY":
                pC = processZquat(pC)
            if pCattrname == "aZ":
                pC = processZquatA(pC)

            self.__setattr__(pCattrname, pC)
            if len(pC) != 0:
                nloaded += 1
        return nloaded

    def LoadA(self, lc):
        nloaded = self.LoadC(lc)
        if lc[0] != "p" and nloaded == 0:
            print("Loading a%s as no p%s records" % (lc, lc))
            self.LoadC("a"+lc)
            if "Q" in lc:
                self.pQ = self.aQ
            if "F" in lc:
                self.pF = self.aF
            if "Z" in lc:
                self.pF = self.aF


    def LoadIGC(self, fname):
        pIGC, hfcodes = GLoadIGC(fname)
        pIGC = processQaddrelEN(pIGC, self)
        self.pIGC = pIGC
        self.pIGCs.append(self.pIGC)
        return pIGC
        
    def LoadPOS(self, fname):
        pPOS = GLoadRTKpos(fname)
        pPOS["u"] = (pPOS.index - self.timestampmidnight)/pandas.Timedelta(milliseconds=1)
        pPOS = processQaddrelEN(pPOS, self)
        self.pPOS = pPOS
        if self.ft0 is None:
            self.ft0, self.ft1 = pPOS.index[0], pPOS.index[-1]
            self.t0, self.t1 = self.ft0, self.ft1
        self.pPOSs.append(self.pPOS)
        
    def saveslicedfileforreplay(self, t0, t1, fname="REPLAY.TXT"):
        fout = open(fname, "w")
        fout.write("replay sliced file %s %s\n\n" % (t0, t1))
        self.fin.seek(self.headerend)
        mt0, mt1 = (t0 - self.Rdatetime0).value/1000000, (t1 - self.Rdatetime0).value/1000000
        for lin in self.fin:
            if mt0 <= int(lin[2:10], 16) < mt1:
                fout.write(lin)
        fout.close()

    # quick way to make timeseries indexes
    def ts(self, hour, minute, second=0):
        if self.Rdatetime0 is not None:
            dt0 = self.Rdatetime0
        elif hasattr(self, "pIGC"):
            dt0 = self.pIGC.index[0]
        else:
            assert False, "No date to use relatively (no data has been loaded)"
        return pandas.Timestamp(dt0.year, dt0.month, dt0.day, hour, minute, second)
    def dts(self, second):
        return pandas.Timedelta(seconds=second)
        
# try self-calibrating the anemometer using GPS and orientation

