#!/usr/bin/env /usr/bin/python

import os, subprocess

# Just a simple script to find the supervisord process ID and send a
# SIGTERM signal to kill both supervisord and all child processes

#------------------------------------
def killpid(pid):
    # cmd = 'kill -s SIGTERM '+pid  # For some reason SIGERM doesn't work, but code 15 is equivalent
    cmd = 'kill -s 15 '+pid
    print 'Killing process:', cmd
    os.system(cmd)
    return

#------------------------------------
if __name__ == '__main__':

    # Look in the standard location first
    pidfile = '/home/pi/supervisord_logs/supervisord.pid'
    if os.path.exists(pidfile):
        f = open(pidfile, 'r')
        pid = f.readline()
        pid = pid.strip()
        print 'Found supervisord process ID', pid, 'from', pidfile
        killpid(pid)
    # As a reality check, do a process search on the whole system to
    # find/kill extraneous processes
    print 'Searching for extraneous supervisord processes'
    txt = subprocess.Popen(['ps','-C','supervisord','-o','pid='], stdout=subprocess.PIPE).communicate()[0]
    lines = txt.split('\n')
    for line in lines:
        pid = line.strip()
        if len(pid) > 0:
            print 'Looks like extraneous supervisord is running under process ID',txt
            killpid(pid)
    # If there are any DAQ copies floating around, kill those too
    print 'Searching for extraneous DAQ processes'
    for daq in ['prizm_daq_2018.py', 'prizm_housekeeping.py']:
        txt = subprocess.Popen(['pgrep','-f',daq], stdout=subprocess.PIPE).communicate()[0]
        lines = txt.split('\n')
        for line in lines:
            pid = line.strip()
            if len(pid) > 0:
                print 'Looks like extraneous DAQ is running under process ID',txt
                killpid(pid)
