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
            cmd = 'python prizm_daq_2018.py --bof extadc_snap_spec_2017-03-24_1035.bof --nchan 4096 -o '+path+' -l '+path+'/log -t 15 --compress bzip2 --diff 1 --ip localhost'
        else:
            print 'Output data file compression is OFF'
            cmd = 'python prizm_daq_2018.py --bof extadc_snap_spec_2017-03-24_1035.bof --nchan 4096 -o '+path+' -l '+path+'/log -t 15 --ip localhost'
        os.system(cmd)
        exit(0)

# Check if we're on the switch pi
path = '/home/pi/switch_data'
if os.path.exists(path):
    print 'Found data path', path
    print 'Running switch control and housekeeping script'
    os.system('python prizm_housekeeping.py -o "antenna","res50","short","noise","res100","open" -a 23,0.05 -r 24,0.05 -s 25,0.05 -n 5,0.05 -R 26,1 -O 12,0.05 --reset 18 -m 21 -t 1 -c config_tempsensor.txt')
    exit(0)

# We shouldn't get to this point
print 'Failed to autodetect data path, no DAQ/housekeeping started.  Halp!'
