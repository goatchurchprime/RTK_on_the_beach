
# handy interactive things
#from ipywidgets import interact, Layout, interactive, fixed, interact_manual
#idgets import interact, interactive, fixed, interact_manual
import pandas, numpy
import ipywidgets as widgets
from IPython.display import display
from matplotlib.collections import LineCollection
from matplotlib import pyplot as plt
from . import utils
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


def plotvalcolour(pQx, pQy, pval, badditional=False):
    points = numpy.array([pQx, pQy]).T.reshape(-1, 1, 2)
    segments = numpy.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=plt.get_cmap('cool'), norm=plt.Normalize(min(pval), max(pval)))
    lc.set_array(pval)
    cs = plt.gca().add_collection(lc)
    if not badditional:
        plt.xlim(min(pQx), max(pQx))  # why is this necessary to set the dimensions?
        plt.ylim(min(pQy), max(pQy))
        plt.colorbar(cs)
    else:
        xlo, xhi = plt.xlim()
        plt.xlim(min(xlo, min(pQx)), max(xhi, max(pQx)))
        ylo, yhi = plt.ylim()
        plt.ylim(min(ylo, min(pQy)), max(yhi, max(pQy)))

def plotwhiskers(pQx, pQy, vel, deg, velfac, col):
    spQx = pQx.iloc[::int(len(pQx)/500+1)]
    spQy = pQy.iloc[::int(len(pQy)/500+1)]
    svel = utils.InterpT(spQx, vel)
    if col == "green":
        svel = -(40-svel)*(velfac/4)
    else:
        svel = svel*velfac
    sdeg = utils.InterpT(spQx, deg)
    srad = numpy.radians(sdeg)
    svx = numpy.sin(srad)*svel
    svy = numpy.cos(srad)*svel
    segments = numpy.array([spQx, spQy, spQx+svx, spQy+svy]).T.reshape(-1,2,2)
    lc = LineCollection(segments, color=col)
    plt.gca().add_collection(lc)
    
def CalcVario(fd):
    fd.LoadA("F")
    pF = fd.pF
    baro = pF[fd.t0-pandas.Timedelta(seconds=30):fd.t1+pandas.Timedelta(seconds=30)].Pr
    timestep = numpy.mean((baro.index[1:]-baro.index[:-1]).astype(int)*1e-9)
    fbaro = utils.FiltFiltButter(baro, f=0.01, n=3)
    vario = fbaro.diff()*(-0.09/timestep)
    return vario.dropna()

def CalcVarioA(alt, varioFfilter):
    vario = alt.diff()/(alt.index.to_series().diff()/pandas.Timedelta(seconds=1))
    vario = vario.dropna()
    fvario = utils.FiltFiltButter(vario, f=varioFfilter, n=3)
    return fvario

    
outputfigure = None
t0t1Label = None

def rescaletsval(val, brescale, lo=None, hi=None):
    if not brescale:
        return val
    if lo is None:
        lo, hi = min(val), max(val)
    return (val - (hi+lo)/2)*(2/(hi-lo))


def plottimeseriesAlt(hangspottimeslider, cbvario, cbaccellerations, cborientations, cbhangspot, secos, fd):
    plt.figure(figsize=(13,8))
    if secos != 'POS only':
        pQ = fd.pQ[fd.t0:fd.t1]
        if fd.bnoLOG:
            if pQ.get("altb") is not None:
                plt.plot(pQ.altb, label="barometric alt")  # pQ === pIGC
            if pQ.get("alt") is not None:
                plt.plot(pQ.alt, label="gps alt")
        else:
            fd.LoadA("F")
            baro = fd.pF[fd.t0:fd.t1].Pr
            if len(fd.pQ):
                balt = utils.BaroToAltComplete(baro, pQ.alt, gpsoffset=None, plt=None)
                plt.plot(pQ.alt, label="GPS altitude")
            else:
                balt = (102726 - baro)*0.037867
            plt.plot(balt, label="barometric alt")
            if hasattr(fd, "aF") and (fd.aF is not fd.pF):
                aQ = fd.aQ[fd.t0:fd.t1]
                baroA = fd.pF[fd.t0:fd.t1].Pr
                if len(fd.pQ):
                    baltA = utils.BaroToAltComplete(baroA, aQ.alt, gpsoffset=None, plt=None)
                    plt.plot(aQ.alt, label="GPSA altitude")
                else:
                    baltA = (102726 - baro)*0.037867
                plt.plot(baltA, label="barometricA alt")
                
    if secos == 'POS only' or secos == 'all GPS':
        for llpQ in fd.pPOSs:
            lpQ = llpQ[fd.t0:fd.t1]
            plt.plot(lpQ.alt+100, label="GPS POS altitude")
                
    plt.gca().xaxis.tick_top()
    plt.legend()
    #plt.show()
    
def plottimeseriesG(hangspottimeslider, cbvario, cbaccellerations, cborientations, cbhangspot, secos, fd):
    fig = plt.figure(figsize=(13,8))
    fig.patch.set_facecolor('white')

    cbcount = cbvario + cbaccellerations + cborientations + cbhangspot
    print("cbcount", cbcount)
    if cbcount == 0:
        cbvario = True
    brescale = (cbcount >= 2)  # more than one value; so scale them all
    nplots = 0
    if cbvario and not fd.bnoLOG:
        if secos != 'POS only':
            vario = CalcVario(fd)
            vario = rescaletsval(vario, brescale)
            plt.plot(vario, label="Vario")
            nplots += 1
    if secos == 'POS only' or secos == 'all GPS':
        for llpQ in fd.pPOSs:
            lpQ = llpQ[fd.t0:fd.t1]
            vario = CalcVarioA(lpQ.alt, fd.varioFfilter)
            vario = rescaletsval(vario, brescale)
            plt.plot(vario, label="Vario A")
            nplots += 1
        
    if (cbaccellerations or cborientations) and not fd.bnoLOG:
        fd.LoadC("Z")
        pZ = fd.pZ[fd.t0:fd.t1]
        if cbaccellerations:
            lo, hi = min(min(pZ.ax), min(pZ.ay), min(pZ.az)), max(max(pZ.ax), max(pZ.ay), max(pZ.az))
            plt.plot(rescaletsval(pZ.ax, brescale, lo, hi))
            plt.plot(rescaletsval(pZ.ay, brescale, lo, hi))
            plt.plot(rescaletsval(pZ.az, brescale, lo, hi))
            nplots += 1
        if cborientations:
            lo, hi = min(min(pZ.pitch), min(pZ.roll)), max(max(pZ.pitch), max(pZ.roll))
            plt.plot(rescaletsval(pZ.pitch, brescale, lo, hi))
            plt.plot(rescaletsval(pZ.roll, brescale, lo, hi))
            plt.plot(rescaletsval(pZ.heading, brescale))
            nplots += 1
            
    if cbhangspot:
        td = pandas.Timedelta(seconds=hangspottimeslider)
        fy = fd.fy[fd.t0-td:fd.t1-td]
        lo, hi = min(min(fy.x), min(fy.y)), max(max(fy.x), max(fy.y))
        fyx = rescaletsval(fy.x, brescale)
        fyy = rescaletsval(fy.y, brescale)
        plt.plot(fy.index+td, fyx, label="hangspotx")
        plt.plot(fy.index+td, fyy, label="hangspoty")
        nplots += 1

    if nplots != 0:
        plt.gca().xaxis.tick_top()
        plt.legend()
        plt.show()
    else:
        print("Nothing to plot.  Try 'TZ'")


    
def plotfigure(t0s, dts, colos, figureheight, velwhisker, headingwhisker, wx, wy, 
               hangspottimeslider, cbvario, cbaccellerations, cborientations, cbhangspot, secos, 
               fd):
    if outputfigure:
        outputfigure.layout.height = figureheight

    t0 = pandas.Timestamp(t0s*3600*1e9 + fd.timestampmidnight.value)
    t1 = pandas.Timedelta(dts*60*1e9) + t0
    t0t1Label.value = "%s %s-%s" % (t0.isoformat()[:10], t0.isoformat()[11:19], t1.isoformat()[11:19])
    fd.t0, fd.t1 = t0, t1

    # timewise plots
    if colos[:1] == "T":
        if colos == "TZ":
            plottimeseriesAlt(hangspottimeslider, cbvario, cbaccellerations, cborientations, cbhangspot, secos, fd)
        else:  # "TSeries"
            plottimeseriesG(hangspottimeslider, cbvario, cbaccellerations, cborientations, cbhangspot, secos, fd)
        return

    
    # xy plots
    fig = plt.figure(figsize=(11, 11))
    fig.patch.set_facecolor('white')

    plt.subplot(111, aspect="equal")
    plt.gca().xaxis.tick_top()

    pQs = [ ]
    if secos != "POS only":
        pQs.append(fd.pQ[fd.t0:fd.t1])
    if secos == 'all GPS':
        for llpQ in fd.pIGCs:
            if llpQ is not fd.pQ:
                pQs.append(llpQ[fd.t0:fd.t1])
    if secos == 'POS only' or secos == 'all GPS':
        for llpQ in fd.pPOSs:
            if llpQ is not fd.pQ:
                pQs.append(llpQ[fd.t0:fd.t1])
    
    
    pQ = pQs[0]
    if secos == "terrain":
        print("terrain")
        tp = utils.TerrainPlot(pQ, tiledirectory="/home/julian/hgstuff/hgtterrains")
        tp.plotterrainxy(plt, fd)

    if wx == 0 and wy == 0:
        pQx, pQy = pQ.x, pQ.y
    else:  # wind added
        ts = (pQ.index - fd.t0).astype(int)*1e-9
        pQx, pQy = pQ.x - ts*wx, pQ.y - ts*wy
    
    if colos == "altitude":
        alt = pQ.alt if "alt" in pQ.columns else pQ.altb
        plotvalcolour(pQx, pQy, alt)
        plt.scatter(pQx.iloc[-2:], pQy.iloc[-2:])
        for lpQ in pQs[1:]:
            alt = lpQ.alt if "alt" in lpQ.columns else lpQ.altb
            plotvalcolour(lpQ.x, lpQ.y, alt, True)
        
    elif colos == "velocity":
        # warning, velocity not changed by wind vector
        velmag = utils.InterpT(pQ, fd.pV.vel)
        if wx != 0 or wy != 0:
            veldeg = utils.InterpT(pQ, fd.pV.deg)
            velrad = numpy.radians(veldeg)
            velvx = numpy.sin(velrad)*velmag
            velvy = numpy.cos(velrad)*velmag
            velmag = numpy.hypot(velvx - wx, velvy - wy)
        plotvalcolour(pQx, pQy, velmag)
        plt.scatter(pQx.iloc[-2:], pQy.iloc[-2:])
    
    elif colos == "vario":    
        # heavily filter so we can use adjacent samples
        vario = CalcVario(fd)
        varioQ = utils.InterpT(pQ, vario)
        plotvalcolour(pQx, pQy, varioQ)
        plt.scatter(pQx.iloc[-2:], pQy.iloc[-2:])
        
    elif colos == "YZ":
        plt.plot(pQy, pQ.alt)
        plt.scatter(pQy.iloc[-5:], pQ.alt.iloc[-5:])
    else:  # XY case
        plt.plot(pQx, pQy)
        plt.scatter(pQx.iloc[-5:], pQy.iloc[-5:])
        for lpQ in pQs[1:]:
            plt.plot(lpQ.x, lpQ.y)
    
    if velwhisker != 0:
        # warning, velocity not changed by wind vector
        plotwhiskers(pQx, pQy, fd.pV.vel, fd.pV.deg, velwhisker, "pink")
    if headingwhisker != 0:
        fd.LoadC("Z")
        plotwhiskers(pQx, pQy, fd.pZ.pitch, fd.pZ.heading, headingwhisker, "green")
    
    #plt.show()

    
def plotinteractivegpstrack(fd):
    global outputfigure, t0t1Label
    t0hour = (fd.ft0-fd.timestampmidnight).value/1e9/3600
    t1hour = (fd.ft1-fd.timestampmidnight).value/1e9/3600
    dtminutes = (fd.ft1 - fd.ft0).value/1e9/60

    scolwidth = "300px"
    t0t1Label = widgets.Label(value="t0")
    t0t1Label.layout.width = "300px"
    t0slider = widgets.FloatSlider(description="starthour", step=1/3600, min=t0hour, max=t1hour, continuous_update=False)
    dtslider = widgets.FloatSlider(description="minutes", value=3, step=1/60, max=dtminutes, continuous_update=False)
    figureheightSelection = widgets.SelectionSlider(options=['300px', '400px', '500px', '600px', '800px'], value='400px', description='display height', continuous_update=False)

    coloptions = widgets.Dropdown(options=['Tseries', 'TZ', 'XY', 'altitude', 'velocity', 'vario', 'YZ'])

    cbvario = widgets.Checkbox(description="vario", value=False, indent=False)
    cbaccellerations = widgets.Checkbox(description="accel", value=False, indent=False)
    cborientations = widgets.Checkbox(description="orient", value=False, indent=False)
    cbhangspot = widgets.Checkbox(description="hangspot", value=False, indent=False)

    hangspottimeslider = widgets.FloatSlider(description="hangspot_t", step=0.01, min=-10, max=10, start=0, continuous_update=False)
    secoptions = widgets.Dropdown(options=['blank', 'terrain', 'all GPS', 'POS only'])

    velwhisker = widgets.IntSlider(min=0, max=5, description="velocity whiskers", continuous_update=False)
    headingwhisker = widgets.IntSlider(min=0, max=5, description="heading whiskers", continuous_update=False)

    windxslider = widgets.FloatSlider(description="windx", step=0.01, min=-10, max=10, start=0, continuous_update=False, indent=False)
    windyslider = widgets.FloatSlider(description="windy", step=0.01, min=-10, max=10, start=0, continuous_update=False, indent=False)

    # build up the panels of components
    uipaneleft = widgets.VBox([t0slider, dtslider, t0t1Label, figureheightSelection])
    
    uicboxes = widgets.HBox([cbvario, cbaccellerations, cborientations, cbhangspot])
    uipaneright = widgets.VBox([uicboxes, coloptions, velwhisker, headingwhisker], layout=widgets.Layout(width=scolwidth))
    
    uicboxes2 = widgets.HBox([secoptions])
    uipanefarright = widgets.VBox([windxslider, windyslider, uicboxes2, hangspottimeslider])
    
    
    ui = widgets.HBox([uipaneleft, uipaneright, uipanefarright])

    params = {'t0s': t0slider, 'dts': dtslider, 
              "velwhisker":velwhisker, "headingwhisker":headingwhisker, 
              "colos":coloptions, 
              "figureheight":figureheightSelection, 
              "wx":windxslider, "wy":windyslider, "hangspottimeslider":hangspottimeslider, 
              "cbvario":cbvario, "cbaccellerations":cbaccellerations, "cborientations":cborientations, "cbhangspot":cbhangspot, "secos":secoptions, 
              'fd':widgets.fixed(fd) }
    outputfigure = widgets.interactive_output(plotfigure, params)
    outputfigure.layout.height = '400px'
    display(ui, outputfigure);
    
