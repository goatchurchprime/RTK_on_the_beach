#!python

# 
# Use this code for post-processing the UBX files from base and two rovers
# Where esp32s have Future-Hangglider/hangspotdetection/esp32code/HangUBXM8TWingtip.ipynb
# and Android phone is running Hangspot3
#

# Copy the .ubx files across from the phone(s) to a directory 
# and process into .pos files
# against settings in the config files


import argparse

parser = argparse.ArgumentParser(description='Post-process ABC UBX files')
parser.add_argument('-f','--force', help='Force recompute', action='store_true')
parser.add_argument('-s','--single', help='Single file processing', action='store_true')
parser.add_argument("fdir")
args = parser.parse_args()
fdir = args.fdir
bforce = args.force
bsingle = args.single

#
# Do the conversions from ubx to pos and nav
#
convbinexe = "/home/julian/extrepositories/RTKLIB-rtkexplorer/app/convbin/gcc/convbin"
import os, subprocess
fubxletters = { }
for f in os.listdir(fdir):
    if os.path.splitext(f)[1] == '.ubx' :
        fubx = os.path.join(fdir, f)
        froot = os.path.splitext(fubx)[0]
        fubxletters[froot[-1]] = froot
        fobs = froot + ".obs"
        if bforce or not os.path.exists(fobs):
            print("\nconvbin on", f)
            k = subprocess.run([convbinexe, fubx], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(k.stderr.decode())
            print(k.stdout.decode())
            if not os.path.exists(fobs):
                print("\nWARNING: %s not created (ubx file probably empty)\n" % fobs)

for l, froot in fubxletters.items():
    print(l, froot)

#
# Process the base station C file to get its fixed GPS position
#
import pandas
from ubxpostutils import genconfig, readposfile

rnx2rtkpexe = "/home/julian/extrepositories/RTKLIB-rtkexplorer/app/rnx2rtkp/gcc/rnx2rtkp"

if "C" in fubxletters:
    fbaseC = fubxletters["C"]
    fbaseCobs = fbaseC+".obs"
    fbaseCnav = fbaseC+".nav"
    fbaseCpos = fbaseC+".pos"
    if bforce or not os.path.exists(fbaseCpos):
        fconfig = genconfig(fdir, ["out-solformat      =llh", "pos1-posmode       =single"])
        print("processing", fbaseCpos)
        k = subprocess.run([rnx2rtkpexe, "-k", fconfig, "-o", fbaseCpos, fbaseCobs, fbaseCnav], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(k.stderr.decode())
        print(k.stdout.decode())

    print("\ninitial fixed station position guess:")
    w = readposfile(fbaseCpos)
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
    baselatstd, baselngstd, basealtstd = wwindow.lat.std(), wwindow.lng.std(), wwindow.alt.std()
    print("lng %f (std %f)\nlat %f (std %f)\nalt %f (std %f)\nfrom %d points" % \
          (baselat, baselatstd, baselng, baselngstd, basealt, basealtstd, len(wwindow)))


#
# Finally process each of the A and B values to make their pos files
#
if bsingle:
    clines = ["out-solformat      =llh", 
              "pos1-posmode       =single" ]
else:
    clines = ["out-solformat      =llh", 
              "pos1-posmode       =kinematic", 
              "pos1-soltype       =combined",
              "ant2-postype       =llh",
              "ant2-pos1          =%s" % baselat, 
              "ant2-pos2          =%s" % baselng, 
              "ant2-pos3          =%s" % basealt ]
#stats-prnaccelh    =10.0       # (m/s^2)
#stats-prnaccelv    =10.0       # (m/s^2)
    
fconfig = genconfig(fdir, clines)

for L in "AB":
    if L not in fubxletters:
        continue
    fbaseL = fubxletters[L]
    fposL = fbaseL+".pos"
    fobsL = fbaseL+".obs"
    if os.path.exists(fobsL):
        print("\nprocessing", ("single" if bsingle else "kinematic"), fposL)
        popenargs = [ rnx2rtkpexe, "-k", fconfig, "-o", fposL, fobsL ]
        if bsingle:
            popenargs.append(fbaseL+".nav")
        else:
            popenargs.extend([fbaseCobs, fbaseCnav])
        k = subprocess.run(popenargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(k.stderr.decode())
        print(k.stdout.decode())
        w = readposfile(fposL)
