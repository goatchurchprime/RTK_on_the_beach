### New notes for the components

An Android device serving a hotspot has ipnumber 192.168.43.1  The app https://github.com/Future-Hangglider/Hanglog3 runs in the foreground listening for connections on port 9042.  Multiple ESP32s operating Ublox M8T GPS receivers connect to it with ?code running on them.  On connection the ESP32 sends its identification string AAAA, BBBB or CCCC.  

The app has a display of incoming connections connections, and has onscreen controls to save these streams of data to separate files in the Android device's memory.  There is also an option to forward these streams of data to another server through a socket over the internet if the device has mobile data.

A computer connected to the hotspot can make multiple connections to this app and request to receive any of these streams by sending an identification stream of -AAA, -BBB, -CCC

This interface can be driven from Python scripts or from RTKnavi which can be configured to send these special strings on connection and which is designed to process raw streams of Ublox GPS data. ?note here on which record is being recorded from the M8T datasheet.

> python scripts/ubxstreamtofiles.py -t 10 junkdata





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

