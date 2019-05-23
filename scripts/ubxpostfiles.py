# Copy the .ubx files across from the phone(s) to a directory and process into .pos files
# against settings in the config files

import argparse

parser = argparse.ArgumentParser(description='Post-process ABC UBX files')
parser.add_argument('-f','--force', help='Force recompute', action='store_true')
parser.add_argument("fdir")
args = parser.parse_args()
fdir = args.fdir
bforce = args.force

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
from utils import genconfig, readposfile

rnx2rtkpexe = "/home/julian/extrepositories/RTKLIB-rtkexplorer/app/rnx2rtkp/gcc/rnx2rtkp"

fbaseCfixedpos = os.path.join(fdir, "baseCpos.txt")
fbaseC = fubxletters["C"]
fbaseCobs = fbaseC+".obs"
fbaseCnav = fbaseC+".nav"
if bforce or not os.path.exists(fbaseCfixedpos):
    fposC = fbaseC+".pos"
    fconfig = genconfig(fdir, ["out-solformat      =llh", "pos1-posmode       =single"])
    print("processing", fposC) 
    k = subprocess.run([rnx2rtkpexe, "-k", fconfig, "-o", fposC, fbaseCobs, fbaseCnav], 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(k.stderr.decode())
    print(k.stdout.decode())
    
    w = readposfile(fposC)
    baselat, baselng, basealt = w.lat.mean(), w.lng.mean(), w.alt.mean()
    print("lng %f (%f)\nlat %f (%f)\nalt %f (%f)\nfrom %d points" % \
          (baselat, w.lat.std(), baselng, w.lng.std(), basealt, w.alt.std(), len(w)))
    fsout = open(fbaseCfixedpos, "w")
    fsout.write("%%\n%.8f %.8f %.3f REF Base\n" % (baselat, baselng, basealt))
    fsout.close()


#
# Finally process each of the A and B values to make their pos files
#
fconfig = genconfig(fdir, ["out-solformat      =llh", 
                           "pos1-posmode       =kinematic", 
                           "file-staposfile    =%s"%fbaseCfixedpos])

for L in "AB":
    if L not in fubxletters:
        continue
    fbaseL = fubxletters[L]
    fposL = fbaseL+".pos"
    fobsL = fbaseL+".obs"
    if os.path.exists(fobsL):
        print("processing", fposL)
        k = subprocess.run([rnx2rtkpexe, "-k", fconfig, "-o", fposL, fobsL, fbaseCobs, fbaseCnav], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(k.stderr.decode())
        print(k.stdout.decode())
        w = readposfile(fposL)
    
