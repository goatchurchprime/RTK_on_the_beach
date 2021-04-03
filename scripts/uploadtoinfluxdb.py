import sys, time, os, datetime
                  
#
# Script for parsing and uploading Hanglog3 log files to 
# the InfluxDB database and putting a record of the file into a separate table
#
# Simply execute after running fetchhanglogfiles and use it's own
# Command line interface
#

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-d", "--devicename", dest="devicename",
                  help="devicename")
(options, args) = parser.parse_args()

sys.path.append("..")
import hacktrack.loaders
import pandas, numpy, math

import influxdb
def makeinfluxdbclient():
    try:
        influxdbconfig = dict(l.split()  for l in open("../influxdb_password.txt").readlines()  if l.strip())
    except FileNotFoundError:
        print("Missing '../influxdb_password.txt' password file, creating blank one to fill in")
        fpass = open("../influxdb_password.txt", "w")
        fpass.write("influxdbuser      hanglog\n")
        fpass.write("influxdbpassword      password-goes-here\n")
        fpass.close()
        influxdbconfig["influxdbpassword"] = "password-goes-here"
    if influxdbconfig["influxdbpassword"] == "password-goes-here":
        print("please set the password in the file '../influxdb_password.txt'")
        sys.exit()
    client = influxdb.InfluxDBClient(host='influxdb.doesliverpool.xyz', port=8086, 
                                     username=influxdbconfig["influxdbuser"], password=influxdbconfig["influxdbpassword"])
    print("databases present", client.get_list_database())
    client.switch_database('hanglogdb')
    return client


def uploadfd(fd, measurement, tags, rectypespresent):
    for k in rectypespresent:
        fieldkeys = None
        precs = None
        if k in "MUZSXYQVGFW":
            fieldkeys = hacktrack.loaders.__getattribute__("recargs"+k)[2]
            precs = fd.__getattribute__("p"+k)
            measurement = "p"+k
        elif k[0] == "a" and k[1] in "ZQFV":
            fieldkeys = hacktrack.loaders.__getattribute__("recargsA"+k[1])[2]
            precs = fd.__getattribute__(k)
            measurement = k
        else:
            print("skipping", k)
            continue
        if k == "Z" or k == "Y":
            precs = precs[~precs["bad"]]
            precs.loc[:,"s"] = precs["s"].astype(int)
            if len(precs) == 0:
                print("skipping all bad Z")
                continue
            if (precs["mx"] == 0).all() and (precs["mx"] == 0).all() and (precs["mz"] == 0).all():
                fieldkeys.remove("mx"); fieldkeys.remove("my"); fieldkeys.remove("mz")
            fieldkeys.extend(["pitch", "roll", "heading"])

        #print(fieldkeys)
        #print(precs.head())

        tags["logchannel"] = k
        records = [ ]
        for idx, row in precs.iterrows():
            #print(row)
            fields = dict((f, row[f])  for f in fieldkeys)
            record = { "measurement":measurement, "tags":tags, "time":idx.isoformat(), "fields":fields }
            #print(record)
            records.append(record)
        print("writing %d records to channel %s" % (len(records), k))
        client.write_points(records)        
        print("  done")
    
    print("all done")


if __name__ == "__main__":
    client = makeinfluxdbclient()
    while True:
        fdirs = os.listdir("hanglog")

        k = client.query("SELECT * FROM hanglog_index")
        pK = pandas.DataFrame(k.get_points())
        pK = pK.drop(columns=["logchannel", "time"], errors="ignore")
        print("\n\nhanglog directories:")
        for i, fdir in enumerate(fdirs):
            alreadyuploaded = (len(pK) != 0) and (pK.fdir==fdir).any()
            print(" ", i, fdir, "[uploaded]" if alreadyuploaded else "")
        print()
        choice = input("Choose directory: ")
        if choice == "":
            break
        fdir = fdirs[int(choice)]
        ffiles = os.listdir(os.path.join("hanglog", fdir))
        print("\n\n files:")
        print("\n".join(ffiles))
        for ffile in ffiles:
            if os.path.splitext(ffile)[1] != ".log":
                continue
            fLog = os.path.join("hanglog", fdir, ffile)
            fd = hacktrack.loaders.FlyDat(fLog, lc='MFLQRVWYZUISGNBXaFaZaQaV')
            
            devicename = options.devicename
            while not devicename:
                devicename = input("Device name: ")
                
            tags = { "fname":ffile, "fdir":fdir }
            rectypespresent = [k for k in fd.reccounts  if fd.reccounts[k] != 0]
            uploadfd(fd, "hanglog", tags, rectypespresent)

            tags["devicename"] = devicename
            tags["uploaddate"] = datetime.datetime.now().isoformat()[:10]
            index_fields = { "ft0":fd.ft0.isoformat(), "ft1":fd.ft1.isoformat(), "rectypespresent":" ".join(rectypespresent) }
            print("indexrecord ", index_fields)
            record = { "measurement":"hanglog_index", "tags":tags, "time":fd.ft0.isoformat(), "fields":index_fields }
            client.write_points([record])
            
            
        print()

        if choice == "":
            break



    
    
