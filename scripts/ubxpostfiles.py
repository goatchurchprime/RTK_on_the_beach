
import argparse, os, subprocess
from ubxpostutils import genconfig, readposfile

# 
# Use this code for post-processing the UBX files either individually or as RTK
#

parser = argparse.ArgumentParser(description='Post-process ABC UBX files')
parser.add_argument('-b','--base', help='Base station [C]', default='C')
parser.add_argument('-f','--force', help='Rerun conversions', default=False, action="store_true")
parser.add_argument("fdir")

convbinexe = "/home/julian/extrepositories/RTKLIB-rtkexplorer/app/convbin/gcc/convbin"
rnx2rtkpexe = "/home/julian/extrepositories/RTKLIB-rtkexplorer/app/rnx2rtkp/gcc/rnx2rtkp"

# Copy the .ubx files across from the phone(s) to a directory 
# and process into .pos files
# against settings in the config files

def runconvbin(froot, bforce):
    fubx = froot + ".ubx"
    fobs = froot + ".obs"
    if bforce or not os.path.exists(fobs):
        print("\nconvbin on", fubx)
        k = subprocess.run([convbinexe, fubx], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(k.stderr.decode())
        print(k.stdout.decode())
        if not os.path.exists(fobs):
            print("\nWARNING: %s not created (ubx file probably empty)\n" % fobs)
    else:
        print("\n", fobs, "exists")
        

def makertkconfig(basepos=None):
    if basepos is None:
        return ["out-solformat      =llh", 
                "pos1-posmode       =single" ]
    
    baselat, baselng, basealt = basepos
    return ["out-solformat      =llh", 
            "pos1-posmode       =kinematic", 
            "pos1-soltype       =combined",
            "ant2-postype       =llh",
            "ant2-pos1          =%s" % baselat, 
            "ant2-pos2          =%s" % baselng, 
            "ant2-pos3          =%s" % basealt ]
              #stats-prnaccelh    =10.0       # (m/s^2)
              #stats-prnaccelv    =10.0       # (m/s^2)
        
        
def processrtktopos(fbaseL, fbaseC=None, basepos=None):
    fposL = fbaseL+".pos"
    fobsL = fbaseL+".obs"
    fnavL = fbaseL+".nav"
    fconfig = genconfig(fdir, makertkconfig(basepos))
    if os.path.exists(fobsL):
        print("\nprocessing", fposL, "against", fbaseC)
        popenargs = [ rnx2rtkpexe, "-k", fconfig, "-o", fposL, fobsL ]
        if fbaseC is None:
            popenargs.append(fnavL)
        else:
            fbaseCobs = fbaseC+".obs"
            fbaseCnav = fbaseC+".nav"
            popenargs.extend([fbaseCobs, fbaseCnav])
        k = subprocess.run(popenargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(k.stderr.decode())
        print(k.stdout.decode())


# Find the files in the directory
args = parser.parse_args()
fdir = args.fdir
print(args, fdir)

fubxfiles = dict((froot[-1], os.path.join(fdir, froot))  \
                 for froot in (os.path.splitext(f)[0]  for f in os.listdir(fdir)  if f[-4:] == '.ubx'))
for L in fubxfiles:
    runconvbin(fubxfiles[L], args.force)

# Process the basestation GPS unit   
if args.base in fubxfiles:
    print("Extracting average point for base station")
    fbaseC = fubxfiles[args.base]
    processrtktopos(fbaseC)
    w = readposfile(fbaseC+".pos")
    baselat, baselng, basealt = w.lat.mean(), w.lng.mean(), w.alt.mean()
    baselatstd, baselngstd, basealtstd = w.lat.std(), w.lng.std(), w.alt.std()
    print("lng %f (std %f)\nlat %f (std %f)\nalt %f (std %f)\nfrom %d points" % \
          (baselat, baselatstd, baselng, baselngstd, basealt, basealtstd, len(w)))
    baselatwindow, baselngwindow, basealtwindow = max(0.001, baselatstd), max(0.001, baselngstd), max(50, basealtstd) 
    wwindow = w[(w.lat>baselat-baselatwindow) & (w.lat<baselat+baselatwindow) & \
                (w.lng>baselng-baselngwindow) & (w.lng<baselng+baselngwindow) & \
                (w.alt>basealt-basealtwindow) & (w.alt<basealt+basealtwindow)]
    print("\nnew fixed station position guess (after filtering outliers):")
    baselat, baselng, basealt = wwindow.lat.mean(), wwindow.lng.mean(), wwindow.alt.mean()
    basepos = (baselat, baselng, basealt)
    baselatstd, baselngstd, basealtstd = wwindow.lat.std(), wwindow.lng.std(), wwindow.alt.std()
    print("lng %f (std %f)\nlat %f (std %f)\nalt %f (std %f)\nfrom %d points" % \
          (baselat, baselatstd, baselng, baselngstd, basealt, basealtstd, len(wwindow)))
else:
    fbaseC, basepos = None, None

    
# Now do RTK calculations for other GPS devices against this base station (if it exists)
for L in fubxfiles:
    if L != args.base:
        fbaseL = fubxfiles[L]
        processrtktopos(fbaseL, fbaseC, basepos)

