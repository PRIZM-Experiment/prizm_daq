#!/usr/bin/env /usr/bin/python

import os, subprocess

# Before doing anything, check if supervisord is running already.  If
# yes, then cry for help and don't do anything.
txt = subprocess.Popen(['ps','-C','supervisord','-o','pid='], stdout=subprocess.PIPE).communicate()[0]
txt = txt.strip()
if len(txt) > 0:
    print 'Looks like supervisord is already running under process ID',txt
    print 'Quitting here and not starting DAQ.'
    exit(0)

# Check if we're on one of the SNAP Pis first
for freq in ['70', '100']:
    path = '/home/pi/data_'+freq+'MHz'
    if os.path.exists(path):
        print 'Found data path', path
        print 'Running DAQ for', freq, 'MHz antenna'
        cmd = 'supervisord -c /home/pi/daq_2018/supervisord/supervisord_'+freq+'.conf'
        os.system(cmd)
        print 'Started supervised DAQ process'
        exit(0)

# Check if we're on the switch control / housekeeping pi
path = '/home/pi/switch_data'
if os.path.exists(path):
    print 'Found data path', path
    print 'Running switch control and housekeeping script'
    cmd = 'supervisord -c /home/pi/daq_2018/supervisord/supervisord_housekeeping.conf'
    os.system(cmd)
    print 'Started supervised DAQ process'
    exit(0)

# We shouldn't get to this point
print 'Failed to autodetect data path, no DAQ/housekeeping started.  Halp!'
