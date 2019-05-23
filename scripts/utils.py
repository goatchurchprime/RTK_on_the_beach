import shutil, os, pandas

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

def readposfile(fpos):
    for sr, l in enumerate(open(fpos)):
        if l[0] != "%":
            break
    w = pandas.read_csv(fpos, skiprows=sr-1, sep="\s+")
    w.rename(columns={"latitude(deg)":"lat", "longitude(deg)":"lng", "height(m)":"alt"}, inplace=True)
    w["time"] = pandas.to_datetime(w["%"]+" "+w["UTC"])
    w.drop(["%", "UTC"], 1, inplace=True)
    w.set_index("time", inplace=True)
    w.index.name = None
    return w
