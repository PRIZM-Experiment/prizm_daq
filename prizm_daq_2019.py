#!/usr/bin/python
import time, datetime, struct, sys, logging, os, subprocess, serial
import corr, scio, iadc
import numpy as nm
from optparse import OptionParser
from pynmea import nmea

#=======================================================================
def exit_fail(lh):
	print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
	try:
		fpga.stop()
	except: pass
	raise
	exit()

#=======================================================================
def channel_callback(option, opt, value, parser):
        """Deal with user-specified ADC channel selection in the option parser."""
        setattr(parser.values, option.dest, [int(v) for v in value.split(',')])
        return

#=========================================================
def read_rtc_datetime(port="/dev/ttyUSB0", ctime=True):
    """Read date and time from the RTC from a serial connection
    """
    # Open a serial connection
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 9600
    ser.timeout = 1
    try:
            ser.open()
    except:
            # I'm guessing this function will fail occasionally
            # because of collisions between the 3 RPis.  As long as we
            # get an occasional heartbeat, we can use system time to
            # interpolate.
            return nm.NAN

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
    if ctime:
            epoch = datetime.datetime.utcfromtimestamp(0)
            return (dtstamp - epoch).total_seconds() * 1000.0
    else:
            return dtstamp

#=======================================================================
def initialize_snap(snap_ip, opts, timeout=10, loglevel=40):
        """Connect to SNAP board, configure settings"""

        # Set up SNAP logger
        lh = corr.log_handlers.DebugLogHandler()
        logger = logging.getLogger(snap_ip)
        logger.addHandler(lh)
        logger.setLevel(loglevel)
        # Log level notes: 20 = moar spewage, 30 = warning, 40 = error, 50 = critical
        # Connect to the SNAP board configure spectrometer settings
        logger.info('Connecting to server %s ... '%(snap_ip))
	fpga=corr.katcp_wrapper.FpgaClient(snap_ip)
        #fpga = corr.katcp_wrapper.FpgaClient(snap_ip, opts.port, timeout=timeout, logger=logger)
        fpga._logger.setLevel(logging.ERROR)  # this cuts down on katcp spewage
	time.sleep(1)  # important for live connection reporting
        if fpga.is_connected():
	        logger.info('Connected!')
        else:
	        logger.error('ERROR connecting to %s .' %(snap_ip))
	        exit_fail(logger)
	bof=opts.boffile
	fpga.progdev(bof)
	print 'Board clock is', fpga.est_brd_clk() #Board clock should be 1/4 of the sampling clock (board clock=125 MHz)
        # Use iadc only if we're running PRIZM firmware, not single SNAP
        adc=iadc.Iadc(fpga)
	adc.set_dual_input()
        # Deal with FFT shift, accumulation length, and sync trigger
        logger.info('Setting fft shift, accumulation length...')
        # fpga.write_int('fft_shift', 0x00000000)  # verified fft_of = 1 all the time
        # fpga.write_int('fft_shift', 0xF0F0F0F0)  # fft_of = 1 ~80% of the time
        # fpga.write_int('fft_shift', 0xFFF0F0FF)  # fft_of = 0 100% of the time
        # fpga.write_int('fft_shift', 0xF0F0F0FF)  # fft_of = 0 100% of the time
        # fpga.write_int('fft_shift', 0xF0F0F0F8)  # fft_of = 0 90% of the time
        # fpga.write_int('fft_shift', 0x80808088)  # fft_of = 1 100% of the time
        # fpga.write_int('fft_shift', 0xC0C0C0C8)  # fft_of = 1 100% of the time
        # fpga.write_int('fft_shift', 0xE0E0E0E8)  # fft_of = 1 100% of the time
        # fpga.write_int('fft_shift', 0xF0F0F0FF)  # fft_of = 0 90% of the time
        # As of 4 May 2017, above value is dead to us.
        # fpga.write_int('fft_shift', 0xFFFFFFFF)  # fft_of = 0 90% of the time
        fpga.write_int('fft_shift', opts.fftshift)
	fpga.write_int('acc_len', opts.acc_len)
        logger.info('Done configuring')
        time.sleep(2)
        return fpga

#=======================================================================
def get_fpga_temp(fpga):
        # returns fpga core temperature
        TEMP_OFFSET = 0x0
        reg = 'xadc'
        x = fpga.read_int(reg,TEMP_OFFSET)
        return (x >> 4) * 503.975 / 4096. - 273.15

#=======================================================================
def read_data(fpga,ndat):
	nn=ndat/2;
        #assert(nn==1024) #if we fail this, we need to update a whole bunch of sizes below...
	mystr='>'+repr(nn)
	#print mystr
	mystrq=mystr+'q'
	#mystrQ=mystr+'Q'
	mystrQ=mystr+'q' #write signed data so the diff format will work

	ep0 = nm.array(struct.unpack(mystrQ, fpga.read('even_pol0',nn*8,0)))
	op0 = nm.array(struct.unpack(mystrQ, fpga.read('odd_pol0',nn*8,0)))

	ep1 = nm.array(struct.unpack(mystrQ, fpga.read('even_pol1',nn*8,0)))
	op1 = nm.array(struct.unpack(mystrQ, fpga.read('odd_pol1',nn*8,0)))
        # Forcing type casting to int64 because numpy tries to be
        # "smart" about casting to int32 if there are no explicit long
        # ints.
	even_real = nm.array(struct.unpack(mystrq, fpga.read('even_real',nn*8,0)),dtype="int64")
	even_imaginary = nm.array(struct.unpack(mystrq, fpga.read('even_imaginary',nn*8,0)),dtype="int64")
	odd_real = nm.array(struct.unpack(mystrq, fpga.read('odd_real',nn*8,0)),dtype="int64")
	odd_imaginary = nm.array(struct.unpack(mystrq, fpga.read('odd_imaginary',nn*8,0)),dtype="int64")
	pol0=nm.ravel(nm.column_stack((ep0,op0)))
	pol1=nm.ravel(nm.column_stack((ep1,op1)))
	real_cross=nm.ravel(nm.column_stack((even_real,odd_real)))
	im_cross=nm.ravel(nm.column_stack((even_imaginary,odd_imaginary)))

	return pol0,pol1,real_cross,im_cross

#=======================================================================
def acquire_data(fpga,opts,ndat=2048,wait_for_new=True):
	nn=ndat/2;
	#assert(nn==1024) #if we fail this, we need to update a whole bunch of sizes below...
	while True:
		tstart = time.time()
		if (tstart>1e5):
			tfrag=repr(tstart)[:5]
		else:
			print 'warning in acquire_data - tstart seems to be near zero.  Did you set your clock?'
			tfrag='00000'
		outsubdir = opts.outdir+'/'+tfrag +'/' + str(nm.int64(tstart))
                os.makedirs(outsubdir)
                logging.info('Writing current data to %s' %(outsubdir))

		f_sys_timestamp1 = open(outsubdir+'/time_sys_start.raw','w')
		f_sys_timestamp2 = open(outsubdir+'/time_sys_stop.raw','w')
		f_rtc_timestamp1 = open(outsubdir+'/time_rtc_start.raw','w')
		f_rtc_timestamp2 = open(outsubdir+'/time_rtc_stop.raw','w')
		f_fft_shift = open(outsubdir+'/fft_shift.raw','w')
		f_fft_of_cnt = open(outsubdir+'/fft_of_cnt.raw','w')
		f_acc_cnt1 = open(outsubdir+'/acc_cnt1.raw','w')
		f_acc_cnt2 = open(outsubdir+'/acc_cnt2.raw','w')
		f_sys_clk1 = open(outsubdir+'/sys_clk1.raw','w')
		f_sys_clk2 = open(outsubdir+'/sys_clk2.raw','w')
		f_sync_cnt1 = open(outsubdir+'/sync_cnt1.raw','w')
		f_sync_cnt2 = open(outsubdir+'/sync_cnt2.raw','w')
                f_pi_temp = open(outsubdir+'/pi_temp.raw','w')                
		f_fpga_temp = open(outsubdir+'/fpga_temp.raw','w')

		diff=not(opts.diff==0)
                compress=opts.compress
                f_aa=scio.scio(outsubdir+'/pol0.scio',diff=diff,compress=compress)
                f_bb=scio.scio(outsubdir+'/pol1.scio',diff=diff,compress=compress)
                f_ab_real=scio.scio(outsubdir+'/cross_real.scio',diff=diff,compress=compress)
                f_ab_imag=scio.scio(outsubdir+'/cross_imag.scio',diff=diff,compress=compress)

                while time.time()-tstart < opts.tfile*60:		
                        if wait_for_new:
                                acc_cnt_old = fpga.read_int('acc_cnt')
                                while True:
                                        acc_cnt_new = fpga.read_int('acc_cnt')
                                        # Ryan's paranoia: avoid possible reinitialization
                                        # crap from first spectrum accumulation
                                        if acc_cnt_new >= acc_cnt_old + 2:
                                                break
                                        time.sleep(0.1)

                        # Time stamp at beginning of read commands.
                        # Reading takes a long time (and there are
                        # sometimes timeouts), so keep track of time
                        # stamps for both start and end of reads.
                        t1_sys = time.time()
                        t1_rtc = read_rtc_datetime()

                        fft_shift=fpga.read_uint('fft_shift')
                        fft_of_cnt= fpga.read_int('fft_of')  #this used to be fft_of_cnt
                        sys_clk1= fpga.read_int('sys_clkcounter')
                        sync_cnt1=fpga.read_int('sync_cnt')
			pol0,pol1,cross_real,cross_im=read_data_prizm(fpga,ndat)
			acc_cnt_end = fpga.read_int('acc_cnt')
			sys_clk2=fpga.read_int('sys_clkcounter') 
			sync_cnt2=fpga.read_int('sync_cnt') 

			t2_sys = time.time()
			t2_rtc = read_rtc_datetime()
			print 'elapsed system time is ',t2_sys-t1_sys
			if acc_cnt_new != acc_cnt_end:
				logging.warning('Accumulation changed during data read')
			f_aa.append(pol0)
			f_bb.append(pol1)
			f_ab_real.append(cross_real)
			f_ab_imag.append(cross_im)
                        temperature=subprocess.check_output('cat /sys/class/thermal/thermal_zone0/temp',shell=True)
                        fpga_tmp = get_fpga_temp(fpga)
			my_tmp=nm.int32(temperature)
                        nm.array(my_tmp).tofile(f_pi_temp)
                        nm.array(fpga_tmp).tofile(f_fpga_temp)
			nm.array(t1_sys).tofile(f_sys_timestamp1)
			nm.array(t2_sys).tofile(f_sys_timestamp2)
			nm.array(t1_rtc).tofile(f_rtc_timestamp1)
			nm.array(t2_rtc).tofile(f_rtc_timestamp2)
			nm.array(fft_shift).tofile(f_fft_shift)
			nm.array(fft_of_cnt).tofile(f_fft_of_cnt)
			nm.array(sys_clk1).tofile(f_sys_clk1)
			nm.array(sys_clk2).tofile(f_sys_clk2)
			nm.array(sync_cnt1).tofile(f_sync_cnt1)
			nm.array(sync_cnt2).tofile(f_sync_cnt2)
			nm.array(acc_cnt_end).tofile(f_acc_cnt2)
			nm.array(acc_cnt_new).tofile(f_acc_cnt1)
			f_sys_timestamp1.flush()
			f_sys_timestamp2.flush()
			f_rtc_timestamp1.flush()
			f_rtc_timestamp2.flush()
                        f_fft_shift.flush()
                        f_fft_of_cnt.flush()
                        f_pi_temp.flush()
                        f_fpga_temp.flush()
                        f_acc_cnt1.flush()
			f_acc_cnt2.flush()
                        f_sys_clk1.flush()
                        f_sys_clk2.flush()
                        f_sync_cnt1.flush()
			f_sync_cnt2.flush()

                        time.sleep(opts.wait)
		#return

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
                if not os.path.isdir(outsubdir):
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
                                # Special case for noise source: need to turn mosfet on as well
                                if src == 'noise': GPIO.output(opts.mosfet,1); print 'mosfet on'
                                # Set switch to the appropriate
                                # source.  These are latching
                                # switches, so just need to pulse the
                                # pin...
                                GPIO.output(pin,1);print '%s Src On'%src
                                time.sleep(0.20)
                                # ...and then immediately turn off again
                                print '%s Src Off'%src
                                GPIO.output(pin,0)
                                # Record time stamps for how long
                                # we're on this switch position.  Note
                                # that we're using system time here,
                                # will need to correct with RTC time
                                # in post-processing.
                                t_start=time.time()
                                arr.append(nm.array([1,t_start])) 
                                time.sleep(ontime)
                                if src == 'noise': GPIO.output(opts.mosfet,0); print 'mosfet off'
                                t_stop=time.time()
                                arr.append(nm.array([0,t_stop]))
                                sys.stdout.flush()
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
                # both start and stop times for each logging cycle.
                # Do this for both system time and attempted RTC
                # reads.
		f_pi_time_sys = open(outsubdir + '/time_sys_pi.raw','w')
		f_pi_time_rtc = open(outsubdir + '/time_rtc_pi.raw','w')
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

                        # Read Pi time (system and RTC) and temperature
                        time_start_sys = time.time()
                        time_start_rtc = read_rtc_datetime()
                        #tstamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
			nm.array(time_start_sys).tofile(f_pi_time_sys)
			nm.array(time_start_rtc).tofile(f_pi_time_rtc)
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
			f_pi_time_sys.flush()
			f_pi_time_rtc.flush()
			f_therms_time_start.flush()
			f_therms_time_stop.flush()
                        for f in f_therms_temp:
                                f.flush()
			sys.stdout.flush()
                        time.sleep(opts.temptime*60)

                # Hmm, we weren't closing the files properly last year?
                f_pi_temp.close()
                f_pi_time_sys.close()
                f_pi_time_rtc.close()
                f_therms_time_start.close()
                f_therms_time_stop.close()
                for f in f_therms_temp:
                        f.close()
        return

if __name__ == '__main__':

        # Parse options
	parser = OptionParser()
	parser.set_usage('snap_daq.py <SNAP_HOSTNAME_or_IP> [options]')
	parser.set_description(__doc__)
	parser.add_option('-o', '--outdir', dest='outdir',type='str', default='/data/raw',
		          help='Output directory [default: %default]')
	parser.add_option('-d', '--diff', dest='diff',type='int', default=0,
                          help='Write diffs - non-zero for yes [default 0]')
	parser .add_option('-z','--compress',dest='compress',type='str',default='',help='Command to use to compress data files, if desired')
	parser.add_option('-l', '--logdir', dest='logdir',type='str', default='/data/log',
		          help='Log directory [default: %default]')
	parser.add_option('-p', '--port', dest='port',type='int', default=7147,
		          help='Port number [default: %default]')
	# parser.add_option('-c', '--channel', dest='channel',type='string', default=[0,1],
	# 	          help='ADC channels as comma separated list [default: %default]',
        #                   action='callback', callback=channel_callback)
	parser.add_option('-a', '--acc_len', dest='acc_len', type='int',default=2*(2**28)/2048,
		          help='Number of vectors to accumulate between dumps [default: %default]')
        parser.add_option('-f', '--fftshift', dest='fftshift', type=int, default=0xFFFFFFFF,
                            help='FFT shift schedule as an integer. Default:0xFFFFFFFF')
	parser.add_option('-t', '--tfile', dest='tfile', type='int',default=15,
		          help='Number of minutes of data in each file subdirectory [default: %default]')
        parser.add_option('-T','--tar',dest='tar',type='int',default=0,help='Tar up directories at end (non-zero for true)')
	parser.add_option('-n', '--nchan', dest='nchan', type='int',default=2048,
		          help='Spectrum length [default: %default]')
	parser.add_option('-w', '--wait', dest='wait', type='int',default=0,
		          help='Number of seconds to wait between taking spectra [default: %default]')
	parser.add_option('-i', '--ip', dest='ip', type='str',default=None,
			  help='IP address of the raspberry pi')
	parser.add_option('-b', '--bof', dest='boffile',type='str', default='',
			  help='Specify the bof file to load')
	parser.add_option('-C','--comment',dest='comment',type='str',default='',help='Comment for log')
	opts, args = parser.parse_args(sys.argv[1:])

	if opts.ip is None:
		print 'Please specify a SNAP board. Run with the -h flag to see all options.\nExiting.'
		exit()

        #--------------------------------------------------------------

        # Create log file
        if not os.path.exists(opts.logdir):
                os.makedirs(opts.logdir)
                print 'Created directory',opts.logdir
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filename=opts.logdir+'/'+str(time.time())+'.log',
                            filemode='w')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)-12s: %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        # Save run-time options to file
        logging.info('======= Run-time options =======')
	logging.info('Boffile: %s' % (opts.boffile))
        logging.info('Accumulate length: %d' %(opts.acc_len))
        logging.info('# channels: %d' %(opts.nchan))
        logging.info('Minutes per file: %d' %(opts.tfile))
        logging.info('Seconds between spectra: %d' %(opts.wait))
	logging.info('Comment: %s' % (opts.comment))
        logging.info('================================')

        # Connect to SNAP board and initialize
        fpga = None
        fpga = initialize_snap(opts.ip, opts)
	time.sleep(5)

        # Try to figure out what kind of DAQ we should run
        # Acquire data
        logging.info('Writing data to top level location %s' %(opts.outdir))
	try:
                # Start up switch operations and temperature logging, use same starting time stamp for both
                start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                p1 = thread.start_new_thread( run_switch, (opts, start_time) )
                # Tiny sleep statement to avoid directory creation collision
                time.sleep(2)
                p2 = thread.start_new_thread( read_temperatures, (opts, start_time))
	        acquire_data_prizm(fpga, opts, ndat=opts.nchan)
	finally:
		logging.info('Terminating DAQ script at %s' % str(time.time()))
