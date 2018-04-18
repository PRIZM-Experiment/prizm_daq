#!/usr/bin/python
import datetime, time, os, sys, thread, re, logging
import numpy as nm
import RPi.GPIO as GPIO
from optparse import OptionParser
import scio
import subprocess

# Code for PRIZM housekeeping that does the following:
# - Switch control.  Automatically cycle between sources by
#   turning on appropriate Raspberry Pi GPIO pins for user-specified
#   lengths of time.
# - Temperature logging for 9 sensors x 2 antennas + 1 SNAP box
#   sensor.  Dump temperature readings at specified intervals.

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
                'short' : opts.short,
                'noise' : opts.noise,
                'open' : opts.open}

        # Set GPIO mode for all selected sources
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(opts.reset, GPIO.OUT)   
        GPIO.output(opts.reset, GPIO.LOW)
        GPIO.setup(opts.mosfet, GPIO.OUT)
        GPIO.output(opts.mosfet, GPIO.LOW)
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
                noise =  scio.scio(outsubdir+'/noise.scio',compress=compress)
                open =  scio.scio(outsubdir+'/open.scio',compress=compress)
                while time.time()-tstart < opts.tfile*60:
                        for src in opts.seq:
                                if src == 'antenna': arr=antenna
                                if src == 'res50': arr=res50
                                if src == 'res100': arr=res100
                                if src == 'short': arr=short
                                if src == 'noise' : arr=noise
				if src == 'open' : arr=open
                                
                                pin = srcs[src][0]
                                ontime = float(srcs[src][1]) * 60.   # Convert to seconds
                                starttime = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                                print 'Reset On'
                                GPIO.output(opts.reset,1)
                                time.sleep(0.20)
                                GPIO.output(opts.reset,0);time.sleep(0.20);print 'Reset off'
                                if src == 'noise': GPIO.output(21,1); print 'mosfet on'
                                GPIO.output(pin,1);print '%s Src On'%src
                                time.sleep(0.20)
                                print '%s Src Off'%src
                                GPIO.output(pin,0)
                               # if src == 'noise': GPIO.output(21,0); print 'mosfet off'
                                t_start=time.time()
                                arr.append(nm.array([1,t_start])) 
                                time.sleep(ontime)
                                if src == 'noise': GPIO.output(21,0); print 'mosfet off'
                                t_stop=time.time()
                                arr.append(nm.array([0,t_stop]))
                                
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

        # Get temperature sensor info from config file
        f = open(opts.tconf, 'r')
        txt = f.readlines()
        tempsensors = []
        for line in txt:
                # Check if leading character is a comment tag
                s = re.search(r'^\s*\#', line)
                if s is not None:
                        continue
                # Otherwise assume that there are three fields: sensor
                # ID, tag, long descriptor; skip everything else
                fields = line.split(',')
                if len(fields) != 3:
                        continue
                id = fields[0].strip()
                tag = fields[1].strip()
                desc = fields[2].strip()  # unused for now, useful for print debugging
                tempsensors.append((id, tag))  # use list instead of dict to preserve order
        f.close()
                
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
                # One wire sensors take some time to read, so record
                # both start and stop times for each logging cycle
		f_pi_time = open(outsubdir + '/time_pi.raw','w')
        	f_therms_time_start = open(outsubdir + '/time_start_therms.raw','w')
        	f_therms_time_stop = open(outsubdir + '/time_stop_therms.raw','w')
                # File for Pi temperature
                f_pi_temp =  open(outsubdir+'/temp_pi.raw','w')
                # Files for one-wire sensors: specified in config file
                f_therms_temp = []
                for tempsensor in tempsensors:
                        tag = tempsensor[1]
                        f = open(outsubdir + '/temp_'+tag+'.raw','w')
                        f_therms_temp.append(f)

                # Start reading sensors
                while time.time()-tstart < opts.tfile*60:

                        # Read Pi temperature
                        time_start = time.time()
                        #tstamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
			nm.array(time_start).tofile(f_pi_time)	
			pi_temperature = subprocess.check_output('cat '+opts.ptemp,shell=True)
                        my_tmp = nm.int32(pi_temperature)
			nm.array(my_tmp).tofile(f_pi_temp)

                        # Read one-wire sensors
			tstamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
			print 'Starting one-wire read : ', tstamp
			time_start = time.time()
			nm.array(time_start).tofile(f_therms_time_start)
                        for i,tempsensor in enumerate(tempsensors):
                                id = tempsensor[0]
                                tag = tempsensor[1]
                                # Replace device wildcard with actual sensor ID and do a read
				try:
                                	dfile = open(opts.tdev.replace('*', id))
                                	txt = dfile.read()
                                	dfile.close()
				except:
					txt = None
                                # Search for e.g. "t=25345" string for temperature reading
				temperature = nm.NAN
				if txt is not None:
                                	s = re.search(r't=(\d+)', txt)
                                	if s is not None:
                                        	temperature = float(s.group(1)) / 1000
                                        	nm.array(temperature).tofile(f_therms_temp[i])
                                print tag, '\t', temperature
			time_stop = time.time()
			nm.array(time_stop).tofile(f_therms_time_stop)

			f_pi_temp.flush()
			f_pi_time.flush()
			f_therms_time_start.flush()
			f_therms_time_stop.flush()
                        for f in f_therms_temp:
                                f.flush()
                        time.sleep(opts.temptime*60)

                # Hmm, we weren't closing the files properly last year?
                f_pi_temp.close()
                f_pi_time.close()
                f_therms_time_start.close()
                f_therms_time_stop.close()
                for f in f_therms_temp:
                        f.close()
        return
        
#=======================================================================
if __name__ == '__main__':
    
    # Parse options
    parser = OptionParser()
    parser.set_usage('switch_control.py [options]')
    parser.set_description(__doc__)
    #parser.add_option('-l', '--logdir', dest='logdir',type='str', default='/data/housekeeping',help='Log directory [default: %default]')
    parser.add_option('-o', '--order', dest='seq',type='string', default=['antenna','res50','short','noise','res100','open'],
        	      help='Desired switch sequence of sources, options are "antenna", "res100", "res50", "short", "noise", "open" [default: %default]',
                      action='callback', callback=seq_callback)
    parser.add_option('--reset', dest='reset', type='int', help='Reset GPIO pin # : 18')
    parser.add_option('-a', '--antenna', dest='antenna', type='string',default=[23,10],
		      help='Antenna: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-R', '--res100', dest='res100', type='string',default=[26,1],
		      help='100 ohm resistor: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-r', '--res50', dest='res50', type='string',default=[24,1],
		      help='50 ohm resistor: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-s', '--short', dest='short', type='string',default=[25,1],
		      help='Short: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-n', '--noise', dest='noise', type='string',default=[5,1],
		      help='Noise: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-O', '--open', dest='open', type='string',default=[12,1],
		      help='Open: GPIO pin # and # of minutes [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-m', '--mosfet', dest='mosfet', type='int', help='Mosfet GPIO pin #: 21')
    parser.add_option('-p', '--ptemp', dest='ptemp',type='str', default='/sys/class/thermal/thermal_zone0/temp',
		      help='Pi temperature read location [default: %default]')
    parser.add_option('-d', '--device', dest='tdev',type='str', default='/sys/bus/w1/devices/w1_bus_master1/*/w1_slave',
		      help='Temperature sensor device location [default: %default]')
    parser.add_option('-c', '--configtemp', dest='tconf',type='str', default='config_tempsensor.txt',
		      help='Temperature sensor configuration / lookup table [default: %default]')
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
    logging.info('Noise - pin, # minutes: '+str(opts.noise)+'\n')
    logging.info('Open - pin, # minutes: '+str(opts.open)+'\n')   
    logging.info('Pi temperature location: '+opts.ptemp+'\n')
    logging.info('One-wire temp sensor device location: '+opts.tdev+'\n')
    logging.info('One-wire temp sensor config file: '+opts.tconf+'\n')
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

    except KeyboardInterrupt:
            print 'Keyboard Interrupt : Cleaning all used GPIOs'
            GPIO.cleanup()
            print 'All used GPIOs cleaned'

    finally:
            logging.info('Observation ended: %s'%str(time.time()))
