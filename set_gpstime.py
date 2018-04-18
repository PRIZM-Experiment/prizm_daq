import numpy as nm
import serial, string, os, datetime, time
from pynmea import nmea

# Set the system time to RTC time, and then monitor drift in time stamps

#=========================================================
def read_rtc_datetime():
    """Read date and time from the RTC from a serial connection, and
    return as a datetime object.
    """
    # Open a serial connection
    ser = serial.Serial()
    ser.port = "/dev/ttyUSB0"  #USB
    ser.baudrate = 9600
    ser.timeouti = 1
    ser.open()

    # Define the required NMEA sentences
    gpgga = nmea.GPGGA()  # time information
    gprmc = nmea.GPRMC()  # date information

    time_stamp = None
    date_stamp = None

    while time_stamp is None or date_stamp is None:
        data = ser.readline()
        if data[0:6] == '$GPGGA':
            gpgga.parse(data)
            time_stamp = str(int(nm.round(float(gpgga.timestamp))))
        if data[0:6] == '$GPRMC':  
            gprmc.parse(data)
            date_stamp = str(gprmc.datestamp)
    ser.close()
    
    dtstamp = datetime.datetime.strptime(time_stamp+' '+date_stamp, '%H%M%S %d%m%y')
    return dtstamp

#=========================================================
if __name__ == '__main__':

    # Set this to True if you want to do testing on RTC vs system time drifts
    test_drift = False
    
    # Read the current time, and check for midnight boundary errors
    delta = datetime.timedelta(seconds=5)  # 5 sec tolerance, although error should be ~24 hrs
    dtstamp_now = read_rtc_datetime()
    while read_rtc_datetime() - dtstamp_now > delta:
        dtstamp_now = read_rtc_datetime()

    # Set system time to RTC
    cmd = 'sudo date -u --set="'+str(dtstamp_now)+'"'
    print 'Setting system time to '+str(dtstamp_now)
    os.system(cmd)

    # If we want to test clock drifts, then monitor both the RTC and
    # system time simultaneously, and write results to a log file once
    # every minute
    
    if test_drift:
        
        logfile = 'time_monitor.log'
        f = open(logfile,'w')

        txt = '# RTC time, system time, time difference\n'+ \
              '--------------------------------------------------'
        print txt
        f.write(txt+'\n')
        f.close()
        while True:
            # Read RTC time
            dtstamp_rtc = read_rtc_datetime()
            # Read system time in UTC
            dtstamp_sys = datetime.datetime.utcnow()
            # Compute time difference
            delta = dtstamp_rtc - dtstamp_sys
    
            txt = str(dtstamp_rtc)+'\t'+str(dtstamp_sys)+'\t'+str(delta)
            print txt
            f = open(logfile,'a')
            f.write(txt+'\n')
            f.close()
            time.sleep(60)
