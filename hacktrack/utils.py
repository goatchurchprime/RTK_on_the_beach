import numpy, math
import scipy.signal
import pandas
from matplotlib import pyplot as plt

def WriteGPX(fname, pQ):
    fout = open(fname, "w")
    fout.write("""<?xml version="1.0" encoding="UTF-8"?>
    <gpx
      version="1.0"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xmlns="http://www.topografix.com/GPX/1/0"
      xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
    <trk>
    <trkseg>
    """)

    for t, (lat, lng, alt) in pQ[["lat", "lng", "alt"]].iterrows():
        fout.write("""<trkpt lat="%.8f" lon="%.8f">
        <ele>%f</ele>
    </trkpt>
    """ % (lat, lng, alt))
        
    fout.write("""</trkseg>
    </trk>
    </gpx>
    """)
    fout.close()
    

# you could use the apply function here, but it's WAY (more than 200X) slower than these parallel vector computations!
#df.merge(df.textcol.apply(lambda s: pd.Series({'feature1':s+1, 'feature2':s-1})),  left_index=True, right_index=True)
# much of this function is redundant now
def absorientacceleration(pZ):
    q0, q1, q2, q3 = pZ.q0, pZ.q1, pZ.q2, pZ.q3
    ax, ay, az = pZ.ax, pZ.ay, pZ.az

    iqsq = pZ.iqsq  # 1/((q0**2 + q1**2 + q2**2 + q3**2))

    r00 = q0*q0*2 * iqsq
    r11 = q1*q1*2 * iqsq
    r22 = q2*q2*2 * iqsq
    r33 = q3*q3*2 * iqsq
    r01 = q0*q1*2 * iqsq
    r02 = q0*q2*2 * iqsq
    r03 = q0*q3*2 * iqsq
    r12 = q1*q2*2 * iqsq
    r13 = q1*q3*2 * iqsq
    r23 = q2*q3*2 * iqsq

    m00 = r00 - 1 + r11  # North.x
    m01 = r12 + r03      # -North.y
    m02 = r13 - r02      # =SinAttack
    m10 = r12 - r03
    m11 = r00 - 1 + r22
    m12 = r23 + r01      # =SinRoll
    m20 = r13 + r02
    m21 = r23 - r01
    m22 = r00 - 1 + r33

    pZ["vx"] = m00*ax+m01*ay+m02*az
    pZ["vy"] = m10*ax+m11*ay+m12*az
    pZ["vz"] = m20*ax+m21*ay+m22*az

    # -1*(kingpost axis)
    pZ["m20"] = m20  
    pZ["m21"] = m21
    pZ["m22"] = m22

    
def FiltFiltButter(s, f=0.004, n=3):
    "Butterworth bidirectional filter on series signal"
    b, a = scipy.signal.butter(n, f, 'low')
    res = scipy.signal.filtfilt(b, a, s)
    return pandas.Series(res, s.index)
    
def despikebysmoothfilter(pC, ky, f=0.05, stdfac=5):
    pCv = pC[ky]
    pCvf = FiltFiltButter(pCv, f=f, n=3)
    pCvdiff = pCv - pCvf
    pCvdiffmean, pCvdiffstd = pCvdiff.mean(), pCvdiff.std()
    pCf = pC[abs(pCvdiff-pCvdiffmean) < pCvdiffstd*stdfac]
    print("dropping %d points" % (len(pC) - len(pCf)))
    return pCf

def ValueHistPlot(s):
    "Plot quantized histogram"
    sN.value_counts(sort=False).sort_index().plot()

def AutoCovariance(s, n=400):
    "Covariance of sequence at a range of shifts"
    sm = s.mean()
    return [((s - sm)*(s.shift(i) - sm)).mean()  for i in range(n)]


# Use reset_index(drop=True) to change index to numbers
# series.index.to_series().diff().dt.microseconds.mean() finds step

# tests to see if the temperatures are comparable
#ts = fd.pS.tS.resample("1000ms").mean()
#ti = fd.pI.tIA.resample("1000ms").mean()
#plt.plot(ts.reset_index(drop=True))
#plt.plot(scipy.signal.lfilter([f,0], [1,f-1], ts))
#for f in [0.3, 0.4, 0.5]:
#    d = pd.concat([pd.Series(scipy.signal.lfilter([f,0], [1,f-1], ts)), ti.reset_index(drop=True)], axis=1)
#    d = d.iloc[50:]
#    plt.plot(d[0], d.tIA)

# calculated on loading now
def SinAttack(pZ):
    return (pZ.q1*pZ.q3 - pZ.q0*pZ.q2)*2 * pZ.iqsq 

def SinRoll(pZ):
    return (pZ.q2*pZ.q3 + pZ.q0*pZ.q1)*2 * pZ.iqsq; 
     
def NorthOrient(pZ):
    a00 = (pZ.q0**2 + pZ.q1**2)*2 * pZ.iqsq - 1
    a01 = (pZ.q1*pZ.q2 + pZ.q0*pZ.q3)*2 * pZ.iqsq
    return 180 - numpy.degrees(numpy.arctan2(a00, -a01))


# this needs to calculate the actual delay sequence factor from the half-life value
def ExpFilter(vseries, rE):  # rE = -math.log(0.5)/(half-life in seconds)
    dt = vseries.index.to_series().diff().mean().value*1e-9
    lam = 1 - math.exp(-dt*rE)
    v0 = vseries.iloc[0]
    return pandas.Series(scipy.signal.lfilter((lam, 0), (1, lam-1), vseries, zi=(v0*(1-lam),))[0], vseries.index)

# as above but takes each step individually rather than by average step
def AccurateExpFilterInPlace(vseries, rE):  # rE = -math.log(0.5)/(half-life in seconds)
    for i in range(1, len(vseries)):
        dt = (vseries.index[i] - vseries.index[i-1]).microseconds*1e-6
        vseries[i] += (vseries[i-1] - vseries[i])*math.exp(-dt*rE) 

# very important function for quickly aligning timseries (sometimes you filter slightly before if there are oscillations)
def InterpT(seriestime, seriesother, dts=0):
    vals = numpy.interp(seriestime.index.asi8, seriesother.index.asi8+int(dts*1e9), seriesother)
    return pandas.Series(vals, seriestime.index)
    
def TimeOfClosestPoint(pQ, x, y):
    return ((pQ.x-x)**2 + (pQ.y+y)**2).idxmin()

# works fom a sustained velocity subselected
def TimeFlightStartEnd(pV):  
    avgsecs, clearsamples = 3, 4
    k = pV.vel.resample("%dms" % avgsecs*1000).max()
    backoffset = pandas.Timedelta(seconds=avgsecs*clearsamples)
    return k[k>5].index[clearsamples] - backoffset, k[k>5].index[-1-clearsamples] + backoffset
    
def SaturationVapourPressure(tempseries):
    A, B, C = 8.1332, 1762.39, 235.66
    return 10**(A - B/(tempseries + C))*133.322387415
    
def DewpointTemperature(tempseries, humidseries):
    A, B, C = 8.1332, 1762.39, 235.66
    svp = 10**(A - B/(tempseries + C))*133.322387415
    pvp = svp*humidseries/100
    return -C - B/(numpy.log10(pvp/133.322387415) - A)

# http://en.wikipedia.org/wiki/Density_of_air
def AirDensity(tempseries, humidityseries, pressureseries):
    saturationvapourpressure = SaturationVapourPressure(tempseries)
    PPwatervapour = SaturationVapourPressure(tempseries)*humidityseries/100
    PPdryair = pressureseries - PPwatervapour
    Rdryair = 287.058
    Rwatervapour = 461.495
    tempK = tempseries + 273.15
    return PPdryair/(Rdryair*tempK) + PPwatervapour/(Rwatervapour*tempK)

# should be sliced by several minutes either end of flight and scaled to zero as the absolute number is meaningless
# also can rfilter it back maybe to align it up -log(0.5)/8 for 8 second half-life
def Entropy(tempseries, pressureseries, temp_rE=0.08664339756999316, subtractmean=True):
    fpressureseries = ExpFilter(pressureseries, temp_rE)
    Sfpressureseries = InterpT(tempseries, fpressureseries)
    res = Sfpressureseries**(1-1.4) * (tempseries+273.16)**1.4
    return res - res.mean()  if subtractmean  else res


def PlotWindRose(pV):
    DD = 5
    vD = pV.groupby(numpy.ceil(pV.deg/DD)).mean().vel  # slick groupby use against 5 degree increments
    windroseX = numpy.sin(numpy.radians(vD.index.to_series()*DD))*vD
    windroseY = numpy.cos(numpy.radians(vD.index.to_series()*DD))*vD
    plt.plot(windroseX, windroseY)
    def fun(x):
        cx, cy, r = x
        return sum((numpy.sqrt((windroseX - cx)**2 + (windroseY - cy)**2) - r)**2)
    import scipy.optimize
    x0 = (0,0,1)
    print(fun((0,0,1)), fun(x0))
    g = scipy.optimize.minimize(fun, x0, method=None, bounds=None, options={"maxiter":500}) 
    print(g)
    print(x0)
    print(list(g.x))
    wcx, wcy, was = list(g.x)  # was = average glider air speed
    plt.plot([was*math.sin(math.radians(d))+wcx  for d in range(361)], [was*math.cos(math.radians(d))+wcy  for d in range(361)])
    return wcx, wcy

# How to calculate the wind velocity
#vel = numpy.sqrt((pQ.x.diff()**2 + pQ.y.diff()**2)/(pQ.t.diff()/pandas.Timedelta(seconds=1)))
#deg = 180+numpy.degrees(numpy.arctan2(-pQ.x.diff(), -pQ.y.diff()))
#pV = pandas.DataFrame({"vel":vel, "deg":deg}).dropna()

# How to factor wind into velocity    
#wcx, wcy = PlotWindRose(pV)
#velminuswind = numpy.sqrt((pV.vel*numpy.sin(numpy.radians(pV.deg)) - wcx)**2 + (pV.vel*numpy.cos(numpy.radians(pV.deg)) - wcy)**2)

# How to plot with the wind offset compensated
#wcx, wcy = utils.PlotWindRose(fd.pV[t0:t1])
#q = fd.pQ[t0:t1]
#toffs = ((q.index - t0).seconds + (q.index - t0).microseconds*1e-6)
#plt.plot(q.x - toffs*wcx, q.y - toffs*wcy)

# the two humidity sensors
#DewpointTemperature(fd.pS.tS, fd.pS.hS)[::10].plot()
#DewpointTemperature(fd.pG.tG, fd.pG.hG)[::10].plot()
#AirDensity(fd.pS.tS, fd.pS.hS, InterpT(fd.pS, fd.pF.Pr)).plot()

#t0, t1 = TimeFlightStartEnd(fd.pV)
#ent = Entropy(fd.pS.tS, fd.pF.Pr, -math.log(0.5)/8)
#ent = ent[t0+pd.Timedelta(60, "s"):t1-pd.Timedelta(60, "s")]
#ent = ent - ent.mean()
#ent.plot()

# for replay look in loaders.saveslicedfileforreplay


####  Rough Terrain plotting features
# (resampling and plotting under the GPS xy not yet done)
import os, numpy, struct


def fhf(lng, lat):
    return "%s%s.hgt" % (("S%.02d" % int(1-lat) if lat < 0 else "N%.02d" % int(lat)), ("W%.03d" % int(1-lng) if lng < 0 else "E%.03d" % int(lng)))

class TerrainTile:
    def __init__(self, hfile):  # file of form N52W004.hgt
        hf = os.path.split(hfile)[-1]
        self.sspix = 1200
        
        if not os.path.exists(hfile):  # automatically do the downloading specified in the assert below
            import urllib.request, io, zipfile
            url = "https://dds.cr.usgs.gov/srtm/version2_1/SRTM3/Eurasia/%s.zip"%hf
            print("fetching", url)
            response = urllib.request.urlopen(url)
            data = response.read()
            print(len(data), "bytes downloaded")
            z = zipfile.ZipFile(io.BytesIO(data))
            assert hf in z.namelist(), z.namelist()
            z.extract(hf, path='/home/julian/hgstuff/hgtterrains/')
        assert os.path.exists(hfile), ("Please download and unzip to", hfile, "from", "https://dds.cr.usgs.gov/srtm/version2_1/SRTM3/Eurasia/")
        ft = open(hfile, "rb").read()
        x = y = numpy.arange(0, 1+1/self.sspix, 1/self.sspix)
        self.terrX, Y = numpy.meshgrid(x, y)
        for i in range(self.sspix+1):
            for j in range(self.sspix+1):
                p = (((i) * (self.sspix+1) + (j)) * 2)  # go to the right spot,
                self.terrX[i][j] = struct.unpack('>h', ft[p:p+2])[0]  # ">h" is a signed two byte integer
        self.lngO, self.latO = (-int(hf[4:7]) if hf[3] == "W" else int(hf[4:7])), (int(hf[1:3]) if hf[0] == "N" else 1-int(hf[1:3]))


terraintiles = { }  # hfile: TerrainTile
class TerrainPlot:
    def __init__(self, pQ, pixextra=20, tiledirectory="../hgtterrains"):
        lng, lat = pQ.iloc[0].lng, pQ.iloc[0].lat
        hfs = set(pQ.apply(lambda r: fhf(r.lng, r.lat), axis=1))
        for hf in hfs:
            if hf not in terraintiles:
                terraintiles[hf] = TerrainTile(os.path.join(tiledirectory, hf))

        self.terrXs = [ terraintiles[hf]  for hf in hfs ]
        self.lnglo, self.lnghi = min(pQ.lng), max(pQ.lng)
        self.latlo, self.lathi = min(pQ.lat), max(pQ.lat)
        
        self.tXtrims = [ ]
        for terrX in self.terrXs:
            slng0, slng1 = int(max(0, (self.lnglo - terrX.lngO)*terrX.sspix-pixextra)), int(min((terrX.sspix+1), (self.lnghi - terrX.lngO)*terrX.sspix+pixextra))
            slat0, slat1 = int(max(0, (self.latlo - terrX.latO)*terrX.sspix-pixextra)), int(min((terrX.sspix+1), (self.lathi - terrX.latO)*terrX.sspix+pixextra))
            self.tXtrims.append((slng0, slng1, slat0, slat1))
        
    def plotterrain(self, plt):
        plt.figure(figsize=(11,11))
        lngO, latO, sspix = self.terrXs[0].lngO, self.terrXs[0].latO, self.terrXs[0].sspix
        (slng0, slng1, slat0, slat1) = self.tXtrims[0]
        plt.gcf().set_facecolor("white")
        plt.imshow(self.terrXs[0].terrX[(sspix+1)-slat1:(sspix+1)-slat0 , slng0:slng1])
        #for terrXo in terrXs[1:]:
        #    plt.imshow(self.terrX.terrX[(sspix+1)-self.slat1:(sspix+1)-self.slat0 , self.slng0:self.slng1])

    def plotterrainlatlng(self, plt):
        for i in range(len(self.terrXs)):
            lngO, latO, sspix = self.terrXs[i].lngO, self.terrXs[i].latO, self.terrXs[i].sspix
            (slng0, slng1, slat0, slat1) = self.tXtrims[i]
            plt.imshow(self.terrXs[i].terrX[(sspix+1)-slat1:(sspix+1)-slat0, slng0:slng1], 
                       extent=(slng0/sspix + lngO, slng1/sspix + lngO, -slat0/sspix - latO, -slat1/sspix - latO))        

    def plotterrainxy(self, plt, fd):
        for i in range(len(self.terrXs)):
            lngO, latO, sspix = self.terrXs[i].lngO, self.terrXs[i].latO, self.terrXs[i].sspix
            (slng0, slng1, slat0, slat1) = self.tXtrims[i]
            plt.imshow(self.terrXs[i].terrX[(sspix+1)-slat1:(sspix+1)-slat0, slng0:slng1], 
                       extent=((slng0/sspix + lngO - fd.lng0)*fd.exfac, (slng1/sspix + lngO - fd.lng0)*fd.exfac, 
                               -(-slat0/sspix - latO + fd.lat0)*fd.nyfac, -(-slat1/sspix - latO + fd.lat0)*fd.nyfac))        


    def plotgps(self, plt, pQ, color):
        lngO, latO, sspix = self.terrXs[0].lngO, self.terrXs[0].latO, self.terrXs[0].sspix
        (slng0, slng1, slat0, slat1) = self.tXtrims[0]
        plt.plot((pQ.lng-lngO)*sspix-slng0, slat1-(pQ.lat-latO)*sspix, color=color)

    def scattergps(self, plt, pQ, color):
        lngO, latO, sspix = self.terrXs[0].lngO, self.terrXs[0].latO, self.terrXs[0].sspix
        (slng0, slng1, slat0, slat1) = self.tXtrims[0]
        plt.scatter((pQ.lng-lngO)*sspix-slng0, slat1-(pQ.lat-latO)*sspix, color=color)
        
    def groundlevel(self, pQ):
        def gl(r):
            terrX = terraintiles[fhf(r.lng, r.lat)]
            i, j = (r.lng-terrX.lngO)*terrX.sspix, (terrX.sspix+1)-(r.lat-terrX.latO)*terrX.sspix
            return terrX.terrX[min(terrX.sspix-1, int(j))][min(terrX.sspix-1, int(i))]
        galt = pQ.apply(gl, axis=1)
        return pandas.Series(galt, pQ.index)
        
        
# The code to make the above happen
#tp = TerrainPlot(fd.pQ0)
#tp.plotterrain(plt)
#tp.plotgps(plt, fd.pQ0, "m")
#fd.pQ.alt.plot(); tp.groundlevel(fd.pQ).plot()


# plotting without trailing 0s on the time axis
#plt.axes().xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

# border colour
# plt.gcf().set_facecolor("white")



# Code for correlating the GPS altitude against the barometer 
# and getting the barometer reading, and hopefully giving an accurate and 
# immediate altitude (accounting for the GPS offset) 
# gpsoffset is the additional seconds added to the baro value to make the gps altitude value fit most accurately
# We should be using a curve rather than a linregress

# use as: 
#balt = utils.BaroToAltComplete(fd.pB.Prb, fd.pQ0.alt, plt=plt)
# This is not giving consistent gpsoffset results!

import scipy.optimize, scipy.stats

def BaroToAltLinearK(baro, alt, gpsoffset):
    balt = InterpT(alt, baro, gpsoffset)
    k = scipy.stats.linregress(balt, alt)
    return k

def BaroToAltOffset(baro, alt):
    def fun(X):
        return BaroToAltLinearK(baro, alt, X[0]).stderr
    res = scipy.optimize.minimize(fun=fun, x0=(0,), method="Nelder-Mead")
    return res.x

def BaroToAltComplete(baro, alt, gpsoffset=None, plt=None):
    fbaro = FiltFiltButter(baro, f=0.1, n=3)    # filter the barometer
    if gpsoffset is None:
        gpsoffset = BaroToAltOffset(fbaro, alt)
        print("GPS offset determined by BaroToAltLinear as", gpsoffset)
        offss = [x*0.1  for x in range(0, 50)]
        if plt is not None:
            plt.plot(offss, [ BaroToAltLinearK(baro, alt, x).stderr  for x in offss ])
    k = BaroToAltLinearK(fbaro, alt, gpsoffset)
    print("balt = baro*%f + %f" % (k.slope, k.intercept))
    balt = fbaro*k.slope + k.intercept  # resample down to 200ms samples, like the GPS
    return balt.resample("200ms").mean()
    
# balt = utils.BaroToAltComplete(fd.pB.Prb, fd.pQ0.alt, plt=plt)


# The horizontal acceleration case and comparison
# extract the velocity vector and then derive the acceleration vector
# called with utils.HorizAccelGPScompare(fd.pZ, fd.pV0, plt)
def HorizAccelGPScompare(pZ, pV, plt):
    absorientacceleration(pZ)
    pV["t"] = pV.index.asi8/1e9  # needs to be a member column to get the shift function
    pV["vx"] = numpy.sin(numpy.radians(pV.deg))*pV.vel
    pV["vy"] = numpy.cos(numpy.radians(pV.deg))*pV.vel
    dt = 2
    ax = ((pV.vx.shift(-dt) - pV.vx.shift(dt)) / ((pV.t.shift(-dt) - pV.t.shift(dt)))).dropna()
    ay = ((pV.vy.shift(-dt) - pV.vy.shift(dt)) / ((pV.t.shift(-dt) - pV.t.shift(dt)))).dropna()

    accvx = FiltFiltButter(pZ.vx, 0.01)
    accvy = FiltFiltButter(pZ.vy, 0.01)
    accgvx = FiltFiltButter(ax, 0.08)
    accgvy = FiltFiltButter(ay, 0.08)

    def BaroToAltLinearK(accvx, accgvx, gpsoffset):
        baccvx = InterpT(accgvx, accvx, gpsoffset)
        return (baccvx - accgvx).std()

    offss = [x*0.1  for x in range(-10, 20)]

    def pltoffszero(offss, v, gv):
        voffss = [ BaroToAltLinearK(v, gv, x)  for x in offss ]
        minvoffss = min(voffss)
        plt.plot(offss, [x-minvoffss  for x in voffss])
    
    plt.plot(offss, [ BaroToAltLinearK(accvx, accgvx, x)  for x in offss ])
    plt.plot(offss, [ BaroToAltLinearK(accvy, accgvy, x)  for x in offss ])

    accH = numpy.sqrt(accvx**2 + accvy**2)
    accgH = numpy.sqrt(accgvx**2 + accgvy**2)
    plt.plot(offss, [ BaroToAltLinearK(accH, accgH, x)  for x in offss ])
    #pltoffszero(offss, accH, accgH)  # not great as hides the absolute scale of the error and accenuates the minima


# not done yet
"""
def VertAccelAltcompare(pZ, balt, plt):
    absorientacceleration(pZ)
    offss = [x*0.1  for x in range(-10, 20)]
    plt.plot(offss, [ BaroToAltLinearK(accvx, accgvx, x).stderr  for x in offss ])
dbalt = (balt.shift(-1) - balt.shift(1))/0.4
ddbalt = (dbalt.shift(-1) - dbalt.shift(1))/0.4
    accvx = FiltFiltButter(pZ.vx, 0.01)
    
    accvy = FiltFiltButter(pZ.vy, 0.01)
    accgvx = FiltFiltButter(ax, 0.08)
    accgvy = FiltFiltButter(ay, 0.08)
"""



# pZ = fd.pZ[t0:t1] --> gives angle of about 13degrees
# probably just getting the angle of the wing on average, nothing to do with the forces really
def FindAngleOfWingForce(pZ):
    f = 0.01
    Fx = FiltFiltButter(pZ.ax+pZ.gx, f)
    Fy = FiltFiltButter(pZ.ay+pZ.gy, f)
    Fz = FiltFiltButter(pZ.az+pZ.gz, f)
    def fun(x):
        d = x[0]
        k = Fx[t0:t1]*math.cos(math.radians(d)) + Fz[t0:t1]*math.sin(math.radians(d))
        return sum(k**2)

    import scipy.optimize
    x0 = (0,)
    g = scipy.optimize.minimize(fun, x0, method=None, bounds=None, options={"maxiter":500}) 
    print(g)
    return g.x

# calculate velocity pV trace from GPS pQ trace to match up IGC data with GPS vel data
def GPSVfromQ(pQ, sdt=2):
    avgstep = pQ.u.diff().mean()
    k = max(1, int((sdt/(avgstep/1000))+0.5))
    print("shift step biway", k)
    dt = (pQ.u.shift(-k) - pQ.u.shift(k))/1000
    vx, vy = (pQ.x.shift(-k) - pQ.x.shift(k))/dt, (pQ.y.shift(-k) - pQ.y.shift(k))/dt
    vel = numpy.sqrt(vx**2 + vy**2)
    deg = numpy.mod(numpy.degrees(numpy.arctan2(vx, vy))+360,360)
    if "altb" in pQ.columns:
        vario = (pQ.altb.shift(-k) - pQ.altb.shift(k))/dt
    else:
        vario = (pQ.alt.shift(-k) - pQ.alt.shift(k))/dt
    return pandas.DataFrame(data={"vel":vel, "deg":deg, "vario":vario}, index=pQ.index).dropna()


def tephogram(fd, plt):
    plt.figure(figsize=(8,6))
    t0, t1 = utils.TimeFlightStartEnd(fd.pV0)
    pb = fd.pB[t0:t1].Prb
    t = pb.index.to_series().diff().mean().value*1e-9
    print(t)
    fpb = ExpFilter(pb, -math.log(0.5)/8)
    dpt = DewpointTemperature(fd.pS.tS, fd.pS.hS)
    tt = InterpT(pb, fd.pS.tS)
    dpt = InterpT(pb, dpt)

    #plt.plot(dpt)
    #plt.plot(utils.InterpT(pb, fd.pS.tS))
    #plt.plot(pb)

    b0 = max(fpb)
    btfac = 0.0005
    for i in range(-20, 15, 5):
        plt.plot([i, i+20000*btfac], [-b0, -b0+20000], color="black")
    plt.plot(dpt + (b0-fpb)*btfac, -fpb, color="b", label="dewpoint")
    plt.plot(tt + (b0-fpb)*btfac, -fpb, color="r", label="temperature")
    plt.ylabel("-pressure")
    plt.xlabel("degC")
    plt.legend()
