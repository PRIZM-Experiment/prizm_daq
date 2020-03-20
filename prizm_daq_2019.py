#!/usr/bin/python
import time
import datetime
import struct
import sys
import logging
import os
import subprocess
import serial
#import casperfpga
import smbus
import ds3231
import mcp23017
import thread
import yaml
import scio
import iadc
import numpy as nm
import RPi.GPIO as GPIO
from argparse import ArgumentParser
from pynmea2 import nmea

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
def read_gps_datetime(port="/dev/ttyUSB0", ctime=True):
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
def get_fpga_temp():
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
def run_switch(params, start_time=None):

        """Run the switch.  Cycle between sources by turning on appropriate
        Raspberry Pi GPIO pins for user-specified lengths of time.
        - params : options from parser
        - start_time : optional starting time stamp for the log file
        """

        # Open log file
        if start_time is None:
                start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        # Setup MCP23017 GPIO's as outputs
        gpios=mcp23017.MCP23017(i2c_bus, 0x20)
        for switch in params["switch-control"]["switches"].keys():
                for gpio in params["switch-control"]["switches"][switch]["gpios"].keys():
                        port = None
                        pin = None
                        if params["switch-control"]["switches"][switch]["gpios"][gpio] != "None":
                        	port = params["switch-control"]["switches"][switch]["gpios"][gpio][0]
                        	pin = params["switch-control"]["switches"][switch]["gpios"][gpio][1:]
                                logging.debug("Setting port %s, pin %s to output"%(port, pin))
                                gpios.set_gpio_direction(port, pin, False)

        for aux_gpio in params["switch-control"]["aux-gpios"].keys():
                port = params["switch-control"]["aux-gpios"][aux_gpio][0]
                pin = params["switch-control"]["aux-gpios"][aux_gpio][1:]
                logging.debug("Setting port %s, pin %s to output"%(port, pin))
                gpios.set_gpio_direction(port, pin, False)

        while True:
		tstart = time.time()
                tfrag=repr(tstart)[:5]
                #starttime = datetime.datetime.utcnow()#.strftime('%Y%m%d_%H%M%S')
                outsubdir = params["data_directory"]+'/switch_data/'+tfrag +'/' + str(nm.int64(tstart))
                if not os.path.isdir(outsubdir):
                	os.makedirs(outsubdir)

                pos_scio_files = {}
                for pos in params["switch-control"]["sequence"]:
                        pos_scio_files[pos] = scio.scio(outsubdir+'/%s.scio'%(pos),
                                                        compress=params["scio-files"]["compress"])

                seq_list = params["switch-control"]["sequence"]
                while time.time()-tstart < params["scio-files"]["file_time"]:
                        seq = seq_list.pop(0)
                        which_switch = params["switch-control"][seq]["switch"]
                        which_pos = str(params["switch-control"][seq]["position"])
                        ontime = params["switch-control"][seq]["ontime"]
                        port = params["switch-control"]["switches"][which_switch]["gpios"][which_pos][0]
                        pin = params["switch-control"]["switches"][which_switch]["gpios"][which_pos][1:]
                        starttime = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        logging.debug('Reset On')
                        if params["switch-control"]["switches"][which_switch]["gpios"]["reset"] != "None":
                                reset_port = params["switch-control"]["switches"][which_switch]["gpios"]["reset"][0]
                                reset_pin = params["switch-control"]["switches"][which_switch]["gpios"]["reset"][1:]
                                gpios.set_output_latch(reset_port, reset_pin, True)
                                time.sleep(0.20)
                                gpios.set_output_latch(reset_port, reset_pin, False)
                                time.sleep(0.01)
                        logging.debug('Reset off')
                        # Special case for noise source: need to turn mosfet on as well
                        if params["switch-control"][seq]["aux"] != "None":
                                print(seq)
                                aux = params["switch-control"][seq]["aux"]
                                aux_port = params["switch-control"]["aux-gpios"][aux][0]
                                aux_pin = params["switch-control"]["aux-gpios"][aux][1:]
                                gpios.set_output_latch(aux_port, aux_pin, True)
                                logging.debug('AUX %s on'%(aux))
                        # Set switch to the appropriate
                        # source.  These are latching
                        # switches, so just need to pulse the
                        # pin...
                        gpios.set_output_latch(port, pin, True)
                        logging.debug('%s Source On'%(seq))
                        time.sleep(0.20)
                        # ...and then immediately turn off again
                        logging.debug('%s Source Off'%(seq))
                        gpios.set_output_latch(port, pin, False)
                        # Record time stamps for how long
                        # we're onu this switch position.  Note
                        # that we're using system time here,
                        # will need to correct with RTC time
                        # in post-processing.
                        t_start=time.time()
                        pos_scio_files[seq].append(nm.array([1,t_start]))
                        time.sleep(ontime)
                        if params["switch-control"][seq]["aux"] != "None":
                                aux = params["switch-control"][seq]["aux"]
                                aux_port = params["switch-control"]["aux-gpios"][aux][0]
                                aux_pin = params["switch-control"]["aux-gpios"][aux][1:]
                                gpios.set_output_latch(aux_port, aux_pin, False)
                                logging.debug('AUX %s off'%(aux))
                        t_stop=time.time()
                        pos_scio_files[seq].append(nm.array([0,t_stop]))
                        seq_list.append(seq)
        return None

#=======================================================================
def read_temperatures(params, start_time=None):
        """Read temperatures and log to file at specified time intervals
        - opts : options from parser, including time interval
        - start_time : optional starting time stamp for the log file
        """

        # Open a log file and write some header information
        if start_time is None:
                start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        # Get temperature sensor info from config file
        tempsensors = []
        for key in params["temperature-sensors"].keys():
                if key[:5] == "temp_":
                        # use list instead of dict to preserve order
                        tempsensors.append((params["temperature-sensors"][key]["id"], params["temperature-sensors"][key]["tag"]))
        # Do an infinite loop over temperature reads
        while True:
	        tstart = time.time()
                tfrag=repr(tstart)[:5]
                #starttime = datetime.datetime.utcnow()#.strftime('%Y%m%d_%H%M%S')
                outsubdir = params["data_directory"]+'/temperature-sensors/'+tfrag +'/' + str(nm.int64(tstart))
                if not os.path.isdir(outsubdir):
                	os.makedirs(outsubdir)
                # One wire sensors take some time to read, so record
                # both start and stop times for each logging cycle.
                # Do this for both system time and attempted RTC
                # reads.
	 	f_therms_time_gps_start = open(outsubdir + '/time_start_gps_therms.raw','w')
                f_therms_time_gps_stop = open(outsubdir + '/time_stop_gps_therms.raw','w')
	 	f_therms_time_rtc_start = open(outsubdir + '/time_start_rtc_therms.raw','w')
                f_therms_time_rtc_stop = open(outsubdir + '/time_stop_rtc_therms.raw','w')
         	f_therms_time_sys_start = open(outsubdir + '/time_start_sys_therms.raw','w')
         	f_therms_time_sys_stop = open(outsubdir + '/time_stop_sys_therms.raw','w')
                # File for Pi temperature
                f_pi_temp = open(outsubdir+'/temp_pi.raw','w')
                # File for FPGA temperature
                f_fpga_temp = open(outsubdir+'/temp_fpga.raw','w')
                # Files for one-wire sensors: specified in config file
                f_therms_temp = []
                for tempsensor in tempsensors:
                        tag = tempsensor[1]
                        f = open(outsubdir + '/temp_'+tag+'.raw','w')
                        f_therms_temp.append(f)
                # Start reading sensors
                while time.time()-tstart < params["scio-files"]["file_time"]:
			# Read Pi time (system and RTC) and temperature
			time_start_sys = time.time()
			time_start_gps = read_gps_datetime()
                        time_start_rtc = rtc.get_datetime().timestamp()
                        nm.array(time_start_sys).tofile(f_therms_time_sys_start)
                        nm.array(time_start_gps).tofile(f_therms_time_gps_start)
	 		nm.array(time_start_rtc).tofile(f_therms_time_rtc_start)
                        pi_temperature = subprocess.check_output(["cat", "/sys/class/thermal/thermal_zone0/temp"])
                        pi_temp = nm.int32(pi_temperature)/1000
	 		nm.array(pi_temp).tofile(f_pi_temp)
                        fpga_temp = get_fpga_temp()
                        nm.array(fpga_temp).tofile(f_fpga_tempp)
			# Read one-wire sensors
	 		logging.debug('Starting one-wire read')
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
                                logger.debug("%s = %f"%(tag, temperature))
		        time_stop_sys = time.time()
			time_stop_gps = read_gps_datetime()
                        time_stop_rtc = rtc.get_datetime().timestamp()
                        nm.array(time_stop_sys).tofile(f_therms_time_sys_stop)
                        nm.array(time_stop_gps).tofile(f_therms_time_gps_stop)
	 		nm.array(time_stop_rtc).tofile(f_therms_time_rtc_stop)
			f_pi_temp.flush()
			f_fpga_temp.flush()
                        f_therms_time_sys_stop.flush()
                        f_therms_time_gps_stop.flush()
	 		f_therms_time_rtc_stop.flush()
                        for f in f_therms_temp:
                        	f.flush()
			time.sleep(params["temperature-sensors"]["read_interval"])
                # Hmm, we weren't closing the files properly last year?
                f_pi_temp.close()
		f_fpga_temp.close()
                f_therms_time_sys_start.close()
                f_therms_time_gps_start.close()
	 	f_therms_time_rtc_start.close()
                f_therms_time_sys_stop.close()
                f_therms_time_gps_stop.close()
	 	f_therms_time_rtc_stop.close()
                for f in f_therms_temp:
                        f.close()
        return None
#=======================================================================
if __name__ == '__main__':
        i2c_bus=smbus.SMBus(1)
        rtc=ds3231.DS3231(i2c_bus)
        rtc.set_system_clock_from_rtc()

        # Parse options
	parser = ArgumentParser()
        parser.add_argument("configfile", type=str, help="yaml file with configuration options for PRIZM's DAQ")
	args = parser.parse_args()

        params=None
        with open(args.configfile, "r") as cf:
                params=yaml.load(cf.read(), yaml.FullLoader)

	# Create log file
        log_dir=params["data_directory"]+"/logs"
        if not os.path.exists(log_dir):
                os.makedirs(log_dir)

        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filename=log_dir+'/prizm_daq_'+str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))+'.log',
                            filemode='w')

        # Save run-time options to file
        logging.info('======= Run-time options =======')
	logging.info('================================')

        # Connect to SNAP board and initialize
        # fpga = initialize_snap(opts.ip, opts)
	# time.sleep(5)

        # Acquire data
        logging.info('Writing data to top level location %s' %(params["data_directory"]))
	try:
                # MCP23017 reset pin is wired to RPI GPIO Pin 21. Needs to be high for normal operation
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(21, GPIO.OUT, initial=GPIO.LOW)
                GPIO.output(21, GPIO.HIGH)
                # Start up switch operations and temperature logging, use same starting time stamp for both
                start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                p1 = thread.start_new_thread(run_switch, (params, start_time) )
                # Tiny sleep statement to avoid directory creation collision
                #time.sleep(2)
                #p2 = thread.start_new_thread(read_temperatures, (params, start_time))
	        #acquire_data_prizm(fpga, opts, ndat=opts.nchan)
                time.sleep(10000)
	finally:
		GPIO.cleanup()
		logging.info('Terminating DAQ script at %s'%(str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))))
