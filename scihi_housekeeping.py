#!/usr/bin/python
import datetime, time, os, sys, thread, re, logging
import numpy as nm
import RPi.GPIO as GPIO
from optparse import OptionParser
import scio
import subprocess

# Code for SCI-HI housekeeping that does the following:
# - Switch control.  Automatically cycle between sources by
#   turning on appropriate Raspberry Pi GPIO pins for user-specified
#   lengths of time.
# - Temperature logging.  Dump temperature readings at specified intervals

#=======================================================================
def seq_callback(option, opt, value, parser):
        """Deal with user-specified sequence selection in the option parser."""
        setattr(parser.values, option.dest, [str(v) for v in value.split(',')])
        return

#=======================================================================
def src_callback(option, opt, value, parser):
        """Deal with user-specified source params in the option parser."""
        vals = [v for v in value.split(',')]
        if len(vals) != 2:
            print 'Source',option.dest,': need two and only two values (GPIO pin, # minutes)'
            exit(0)
        setattr(parser.values, option.dest, [int(vals[0]), float(vals[1])])
        return
                                                        
#=======================================================================
def run_switch(opts, start_time=None):
        """Run the switch.  Cycle between sources by turning on appropriate
        Raspberry Pi GPIO pins for user-specified lengths of time.
        - opts : options from parser
        - start_time : optional starting time stamp for the log file
        """

        # Define dictionary of sources to switch between.  For each
        # source, specify a two-element list consisting of GPIO pin number
        # and number of MINUTES for source to remain selected.
        srcs = {'antenna' : opts.antenna,
                'res100' : opts.res100,
                'res50' : opts.res50,
                'short' : opts.short}
#                'noise' : opts.noise}

        # Set GPIO mode for all selected sources
        GPIO.setmode(GPIO.BCM)
        for src in opts.seq:
                pin = srcs[src][0]
                GPIO.setup(pin, GPIO.OUT)  # Define the pins as outputs
                GPIO.output(pin, GPIO.LOW) # All pins set to LOW i.e. 0V
                print 'GPIO pin', pin, 'set to output. Initial state:LOW'
        # Open log file
        if start_time is None:
                start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        while True:
                tstart = time.time()
                starttime = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                if (tstart>1e5):
                        tfrag=repr(tstart)[:5]
                else:
                        print 'warning in run_switch - tstart seems to be near zero.  Did you set your clock?'
                        tfrag='00000'
                outsubdir = opts.outdir + '/' + tfrag + '/' + str(nm.int64(tstart))
                if not os.path.exists(outsubdir):
                        os.makedirs(outsubdir)
                compress=opts.compress
                antenna =  scio.scio(outsubdir+'/antenna.scio',compress=compress)
                res50 =  scio.scio(outsubdir+'/res50.scio',compress=compress)
                res100 =  scio.scio(outsubdir+'/res100.scio',compress=compress)
                short =  scio.scio(outsubdir+'/short.scio',compress=compress)
                        
                while time.time()-tstart < opts.tfile*60:
                        for src in opts.seq:
                                if src == 'antenna': arr=antenna
                                if src == 'res50': arr=res50
                                if src == 'res100': arr=res100
                                if src == 'short': arr=short
                                
                                pin = srcs[src][0]
                                ontime = float(srcs[src][1]) * 60.   # Convert to seconds
                                starttime = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                                GPIO.output(pin,1)
                                t_start=time.time()
                                arr.append(nm.array([1,t_start]))
                                starttxt = starttime + ' : ' + src + ' on'
                                print starttxt
                                time.sleep(ontime)
                                GPIO.output(pin,0)
                                t_stop=time.time()
                                arr.append(nm.array([0,t_stop]))
                                stoptime = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                                stoptxt = stoptime + ' : ' + src + ' off'
                                print stoptxt
                                
                                
#        GPIO.cleanup() 
        return

#=======================================================================
def read_temperatures(opts, start_time=None):

        """Read temperatures and log to file at specified time intervals
        - opts : options from parser, including time interval
        - start_time : optional starting time stamp for the log file
        """

        # Open a log file and write some header information
        if start_time is None:
                start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Do an infinite loop over temperature reads
        while True:
                tstart = time.time()
                #starttime = datetime.datetime.utcnow()#.strftime('%Y%m%d_%H%M%S')
                if (tstart>1e5):
                        tfrag=repr(tstart)[:5]
                else:
                        print 'warning in run_switch - tstart seems to be near zero.\
  Did you set your clock?'
                        tfrag='00000'
                outsubdir = opts.outdir+'/'+tfrag +'/' + str(nm.int64(tstart))
                if not os.path.isdir(outsubdir):
                        os.makedirs(outsubdir)
                f_pi_temp =  open(outsubdir+'/pi_temp.raw','w')
                f_snapbox_temp = open(outsubdir + '/snapbox_temp.raw','w')
		f_pi_time = open(outsubdir + '/pi_time.raw','w')
        	f_snapbox_time = open(outsubdir + '/snapbox_time.raw','w')

                # In the device name, 28-XXX is the serial number, and w1_slave
                # contains temperature in the serial number
                while time.time()-tstart < opts.tfile*60:
                        time_start = time.time()
                        #tstamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
			nm.array(time_start).tofile(f_pi_time)	
			pi_temperature = subprocess.check_output('cat /sys/class/thermal/thermal_zone0/temp',shell=True)
                        my_tmp = nm.int32(pi_temperature)
			nm.array(my_tmp).tofile(f_pi_temp)
			dfile = open(opts.tdev)
                        temp = dfile.read()
                        dfile.close()

                        # Search for e.g. "t=25345" string for temperature reading
                        s = re.search(r't=(\d+)', temp)
                        
                        #s = re.search(r't=(\d+)', temp.split('\n')[-1])
                        if s is not None:
                                snapbox_temperature = float(s.group(1)) / 1000
				tstart_snapbox = time.time()
				tstamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
				print tstamp , ': ' , snapbox_temperature 
                                nm.array(snapbox_temperature).tofile(f_snapbox_temp)
				nm.array(tstart).tofile(f_snapbox_time)

			f_pi_temp.flush()
			f_pi_time.flush()
			f_snapbox_temp.flush()
			f_snapbox_time.flush()
                        time.sleep(opts.temptime*60)
        return
        
#=======================================================================
if __name__ == '__main__':
    
    # Parse options
    parser = OptionParser()
    parser.set_usage('switch_control.py [options]')
    parser.set_description(__doc__)
    #parser.add_option('-l', '--logdir', dest='logdir',type='str', default='/data/housekeeping',help='Log directory [default: %default]')
    parser.add_option('-o', '--order', dest='seq',type='string', default=['antenna','res100','res50','short','noise'],
        	      help='Desired switch sequence of sources, options are "antenna", "res100", "res50", "short", "noise" [default: %default]',
                      action='callback', callback=seq_callback)
    parser.add_option('-a', '--antenna', dest='antenna', type='string',default=[1,60],
		      help='Antenna: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-R', '--res100', dest='res100', type='string',default=[2,1],
		      help='100 ohm resistor: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-r', '--res50', dest='res50', type='string',default=[3,1],
		      help='50 ohm resistor: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-s', '--short', dest='short', type='string',default=[4,1],
		      help='Short: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-n', '--noise', dest='noise', type='string',default=[5,1],
		      help='Noise: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-d', '--device', dest='tdev',type='str', default='/sys/bus/w1/devices/28-021600a744ff/w1_slave',
		      help='Temperature sensor device location [default: %default]')
    parser.add_option('-t', '--temptime', dest='temptime',type='float', default=1,
		      help='Number of minutes to wait between temperature sensor readings [default: %default]')
    parser .add_option('-z','--compress',dest='compress',type='str',default='',help='Command to use to compress data files, if desired')

    parser.add_option('-u', '--outdir', dest='outdir',type='str', default='/home/pi/switch_data', help='Output directory [default: %default]')
    parser.add_option('-f', '--tfile', dest='tfile', type='int',default=120,
                                                help='Number of minutes of data in each file subdirectory [default: %default]')
    parser.add_option('-l', '--logdir', dest='logdir',type='str', default='/home/pi/switch_data/log',help='Log directory [default: %default]')
    opts, args = parser.parse_args(sys.argv[1:])

    if not os.path.exists(opts.logdir):
        os.makedirs(opts.logdir)
        print 'Created directory',opts.logdir
                      
    t_start=nm.int64(time.time())
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(name)-12s %(message)s',datefmt='%m-%d %H:%M',filename=opts.logdir+'/'+str(time.time()) + '.log',filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
                                            
    logging.info('===================================\n')
    logging.info('Switch settings \n')
    logging.info('Sequence: '+str(opts.seq)+'\n')
    logging.info('Antenna - pin, # minutes: '+str(opts.antenna)+'\n')
    logging.info('100 ohm resistor - pin, # minutes: '+str(opts.res100)+'\n' )
    logging.info('50 ohm resistor - pin, # minutes: '+str(opts.res50)+'\n')
    logging.info('Short - pin, # minutes: '+str(opts.short)+'\n')   
    logging.info('Temperature sensor device: '+opts.tdev+'\n')
    logging.info('===================================\n')
    logging.info('Observation started: %s'%str(time.time()))    
                                    
    try:
            # Start up switch operations and temperature logging, use same starting time stamp for both
            start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            p1 = thread.start_new_thread( run_switch, (opts, start_time) )
            p2 = thread.start_new_thread( read_temperatures, (opts, start_time))
            # Arbitrary infinite sleep to keep the above threads running
            while True:
                    time.sleep(10)
    finally:
            logging.info('Observation ended: %s'%str(time.time()))


