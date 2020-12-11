### New notes for the components

An Android device serving a hotspot has ipnumber 192.168.43.1  The Android app [Hanglog3](https://github.com/Future-Hangglider/Hanglog3) runs in the foreground listening for TCP connections on port 9042.  Multiple ESP32s operating Ublox M8T GPS receivers and BNO055 accelerometers connect to it with [HanglogESP32](https://github.com/Future-Hangglider/HanglogESP32) code running on them.  On connection the ESP32 sends its identification string AAAA, BBBB, CCCC or @@@@ depending on which GPS or accelerometer device.

The stream of data from the ESP32 device are binary packets of type UBX-RXM-RAWX, UBX-RXM-SFRBX, UBX-NAV-CLOCK and UBX-NAV-SVINFO from the Ublox M8T receiver as described in the document UBX-13003221.  There are no NMEA strings as these are ascii and would clash with the raw binary data required for RTK processing.

The Hanglog3 app displays the incoming connections in a table.  Green is a good connection, and the string shown is (recordnumber#number_of_good_satellites) as extracted from the UBX-NAV-SVINFO records, so you can tell immediately if something is bad with the antenna or GPS configuration.

#### TL;DR instructions

0. You have collected some data by running the ESP32s near a phone with its android hotspot 
enabled while running the Hanglog3 app and recorded a stream of data using the GoLog switch.

1. Connect PC to phone's android hotspot while the phone is running Hanglog3.  Then run:
> python scripts/fetchhanglogfiles.py hanglog
This creates a directory named after the datetime

2. Connect ESP32 base station ('C' with SD card) to Hanglog3 and run:
> python scripts/fetchsdcardfiles.py hanglog/dd_2020_07_26_161026/
This lets you select and download the correct file to this directory

3. Check all three files are present:
> ls -l hanglog/dd_2020_07_26_161026/

4. Perform the RTK on this:
> python scripts/ubxpostfiles.py -bC hanglog/dd_2020_07_26_161026/



#### Acquiring the data into the Android device


There are three options for acquiring the Ublox M8T data streams that are being received by the Hanglog3 app from the ESP32s through the TCP connections.


1) The onscreen control 'GoLog' starts and stops the saving these streams of data as separate files in a directory in the Android device's memory.  The name of the directory is in the top panel.


1A) To download the files without having to connect a USB cable and find where they are in the file system, use the script which creates an interactive user interface:

> python scripts/fetchhanglogfiles.py hanglog


2) There is an option 'DDsock' to forward these streams of data to another server through a socket over the internet, if the device has mobile data.


3) A computer connected by wifi to the Android device hotspot can make multiple TCP connections to the Hanglog3 app and request to receive any of these streams by sending an identification header of -AAA, -BBB, -CCC.

The following script fetches 10 seconds of data from these streams and saves '.ubx' files into the given directory:

> python scripts/ubxstreamtofiles.py -t 10 sparedata


#### Processing the Ublox M8T data with RTK

Post-processing the binary GPS data into positions can be done singly, or in reference to the base station and requires a lot of configuration data.  This has been put into a script that managed generating the '.nav', '.obs' and finally the output '.pos' files from the original .'ubx'.

The '-b' option tells which is the base station.  The default is 'C'.

> python scripts/ubxpostfiles.py -bA hanglog/20200602092356/

(Should make an xy plot preview of the pos files)

This interface can be driven from Python scripts or from RTKnavi which can be configured to send these special strings on connection and which is designed to process raw streams of Ublox GPS data. 








## Old notes insuffient to work out what I was doing

### RTK_on_the_beach

Scripts, workflows and notebooks to guide a person on a sandy beach

This code depends on the Android App to connect to the ESP32s 
on the UBX M8T units and either record the data streams to files or forward to sockets on a PC 
where rtkrcv is running.


Jobs to do:

1) Get matplotlib animation working again (or build it into the interactive callback system with the image underlay)

2) Make a greyscale image which we can underlay on the playing area.  

3) Function which reads this greyscale value from the image for transmission

4) prove a method of socket transmission from PC back to the GPS that is able to flash an LED (maybe one that is on a wire coming down from the helmet).

5) deploy on the beach, probably with a liver bird shape.  





To run:

/home/julian/extrepositories/RTKLIB-rtkexplorer/app/rtkrcv/gcc/rtkrcv -t 5 -s -o conf/ackinematic.conf

This does everything from the command line.

Or to do the postprocessing, first convert with:

/home/julian/extrepositories/RTKLIB-rtkexplorer/app/convbin/gcc/convbin /home/julian/data/hanglog/22105842/hdata-2019-03-22_10-58-42B.ubx

Then use the RTKPOST 

Need to go through building the RTKlib from source again, as too many edits done to it to make it work.

