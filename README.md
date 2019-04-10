### RTK_on_the_beach

Scripts, workflows and notebooks to guide a person on a sandy beach

This code depends on the Android App https://github.com/Future-Hangglider/Hanglog3 to connect to the ESP32s 
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

