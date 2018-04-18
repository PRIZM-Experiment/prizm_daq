#!/usr/bin/env /usr/bin/python

import os

# Bzip output SNAP files?
compress = True

# Check if we're on one of the SNAP Pis first
for freq in ['70', '100']:
    path = '/home/pi/data_'+freq+'MHz'
    if os.path.exists(path):
        print 'Found data path', path
        print 'Running DAQ for', freq, 'MHz antenna'
        if compress:
            print 'Output data file compression is ON'
            cmd = 'python scihi_daq_2017.py --bof extadc_snap_spec_2017-03-24_1035.bof --nchan 4096 -o '+path+' -l '+path+'/log -t 15 --compress bzip2 --diff 1 --ip localhost'
        else:
            print 'Output data file compression is OFF'
            cmd = 'python scihi_daq_2017.py --bof extadc_snap_spec_2017-03-24_1035.bof --nchan 4096 -o '+path+' -l '+path+'/log -t 15 --ip localhost'
        os.system(cmd)
        exit(0)

# Check if we're on the switch pi
path = '/home/pi/switch_data'
if os.path.exists(path):
    print 'Found data path', path
    print 'Running switch control and housekeeping script'
    os.system('python prizm_housekeeping.py -o "antenna,res100,short,res50" -a 24,60 -R 25,1 -r 23,1 -s 18,1 -t 1 -c config_tempsensor.txt')
    exit(0)

# We shouldn't get to this point
print 'Failed to autodetect data path, no DAQ/housekeeping started.  Halp!'
