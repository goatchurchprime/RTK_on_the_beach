import shutil, os, pandas, math

def genconfig(fdir, clines):
    fconfigtemplate = "/home/julian/repositories/RTK_on_the_beach/conf/template.conf"
    fconfig = os.path.join(fdir, "temp.conf")
    
    shutil.copy(fconfigtemplate, fconfig)
    fcout = open(fconfig, "a")
    for l in clines:
        fcout.write("\n")
        fcout.write(l)
    fcout.close()
    return fconfig


# w.Q  1:Fixed, solution by carrier-based relative positioning and the integer ambiguity is properly resolved.
#      2:Float, solution by carrier‐based relative positioning but the integer ambiguity is not resolved.
#      3:Reserved
#      4:DGPS, solution by code‐based DGPS solutionsor single point positioning with SBAS corrections 
#      5:Single, solution by single point positioning
# w.ns    Number of satellites
# w.sd()  Standard deviation errors (part of the covariance matrix)
# w.age   Age differential between rover and base
# w.ratio ratio test of integer ambiguity between residuals of best and second best integer vector
                    
def readposfile(fpos, lat0=None, lng0=None):
    for sr, l in enumerate(open(fpos)):
        if l[0] != "%":
            break
    w = pandas.read_csv(fpos, skiprows=sr-1, sep="\s+")
    w.rename(columns={"latitude(deg)":"lat", "longitude(deg)":"lng", "height(m)":"alt"}, inplace=True)
    
    if lat0 is not None:
        earthrad = 6378137
        latfac = 2*math.pi*earthrad/360
        lngfac = latfac*math.cos(math.radians(lat0))
        w["y"] = (w.lat - lat0)*latfac
        w["x"] = (w.lng - lng0)*lngfac
        
    w["time"] = pandas.to_datetime(w["%"]+" "+w["UTC"])
    w.drop(["%", "UTC"], 1, inplace=True)
    w.set_index("time", inplace=True)
    w.index.name = None
    return w
