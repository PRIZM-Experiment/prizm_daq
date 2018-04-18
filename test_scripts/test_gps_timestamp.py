#Code to read NMEA sentences from the GPS RTC
import numpy as np
import serial
import string
from pynmea import nmea

s = serial.Serial()
#s.port = "/dev/ttyAMA0"
s.port = "/dev/ttyUSB0"
s.baudrate = 9600
s.timeouti = 1
s.open()
#Defining the required NMEA sentences
gpgga = nmea.GPGGA() 
gprmc = nmea.GPRMC()

while True:
    
    data = s.readline()
#    print data
    if data[0:6] == '$GPGGA': #header check
        gpgga.parse(data)
        time = []
        time_stamp = gpgga.timestamp
        time.append(time_stamp)
    

    if data[0:6] == '$GPRMC':  
        gprmc.parse(data)
        date_stamp = gprmc.datestamp
        print 'GPS time:',time[0], str(date_stamp)
        time = []
#	break
