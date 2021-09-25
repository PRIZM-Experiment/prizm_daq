#!/usr/bin/env /usr/bin/python

import os, sys, datetime

def write_stdout(s):
    # only eventlistener protocol messages may be sent to stdout
    sys.stdout.write(s)
    sys.stdout.flush()

def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def main():

    event_logfile = 'found_events.txt'   # File for recorded crash events
    max_crash = 5    # Max number of crashes before reboot
    
    f=open(event_logfile,'w')
    ncrash=0
    while 1:
        # transition from ACKNOWLEDGED to READY
        write_stdout('READY\n')

        # read header line and print it to stderr
        line = sys.stdin.readline()
        write_stderr(line)
        if line.find('PROCESS_STATE_EXITED')>-1:
            ncrash=ncrash+1

            # read event payload and print it to stderr
            headers = dict([ x.split(':') for x in line.split() ])
            data = sys.stdin.read(int(headers['len']))
            write_stderr(data)
            f.write('ncrash=' + repr(ncrash) + ' with event  ' + line)
            #f.write('event was ' + line)
            f.flush()
            # transition from READY to ACKNOWLEDGED
            write_stdout('RESULT 2\nOK')

            if ncrash==max_crash:
                f.write('ncrash=' + repr(ncrash) + ' with event  ' + line)
                f.write('Reached maximum number of allowed crashes, time to reboot\n')
                f.write('Current time is '+datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')+' \n')
                f.flush()
                f.close()
                cmd = 'sudo reboot'  # Need to test this and see if we can do as not root
                os.system(cmd)

if __name__ == '__main__':
    main()
