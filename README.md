# RTK_on_the_beach
Scripts, workflows and notebooks to guide a person on a sandy beach

This code depends on the Android App https://github.com/Future-Hangglider/Hanglog3 to connect to the ESP32s 
on the UBX M8T units and either record the data streams to files or forward to sockets on a PC 
where rtkrcv is running.


To run:

/home/julian/extrepositories/RTKLIB-rtkexplorer/app/rtkrcv/gcc/rtkrcv -t 5 -s -o /home/julian/repositories/RTK_on_the_beach/conf/ackinematic.conf

This does everything from the command line.

Or to do the postprocessing, first convert with:

/home/julian/extrepositories/RTKLIB-rtkexplorer/app/convbin/gcc/convbin /home/julian/data/hanglog/22105842/hdata-2019-03-22_10-58-42B.ubx

Then use the RTKPOST 

Need to go through building the RTKlib from source again, as too many edits done to it to make it work.

