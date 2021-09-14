#!/usr/bin/python
import corr, time, struct, sys, logging, pylab, os
import numpy as nm
from optparse import OptionParser
import scio,iadc



#date;python scihi_daq_2017.py --bof dual_pol_extadc_fftWrap.bof -o ./data -l ./log -t 15;date
#date;python scihi_daq_2017.py --bof extadc_snap_spec_2017-03-23_2111.bof --nchan 4096 -o ./data -l ./log -t 15;date


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

#=======================================================================
def initialize_snap(snap_ip, opts, timeout=10, loglevel=20):
        """Connect to SNAP board, configure settings"""

        # Set up SNAP logger
        lh = corr.log_handlers.DebugLogHandler()
        logger = logging.getLogger(snap_ip)
        logger.addHandler(lh)
        logger.setLevel(loglevel)

        # Connect to the SNAP board configure spectrometer settings
        #logger.info('Connecting to server %s on port %i... '%(snap_ip, opts.port))
        logger.info('Connecting to server %s ... '%(snap_ip))
	fpga=corr.katcp_wrapper.FpgaClient(snap_ip)
        #fpga = corr.katcp_wrapper.FpgaClient(snap_ip, opts.port, timeout=timeout, logger=logger)
        time.sleep(1)

        if fpga.is_connected():
	        logger.info('Connected!')
        else:
	        #logger.error('ERROR connecting to %s on port %i.' %(snap,opts.port))
	        logger.error('ERROR connecting to %s .' %(snap))
	        exit_fail()
	bof=opts.boffile
	fpga.progdev(bof)
	adc=iadc.Iadc(fpga)
	adc.set_dual_input()
	print 'Board clock is', fpga.est_brd_clk() #Board clock should be 1/4 of the sampling clock (board clock=125 MHz)                                                                                         adc.set_data_mode() 


        logger.info('Configuring accumulation period...')
        fpga.write_int('acc_len', opts.acc_len)
        fpga.write_int('fft_shift', 0xFFFFFFFF)
        logger.info('Done configuring')

        time.sleep(2)

        return fpga

#=======================================================================
def get_tail(mylist):
	#data get appended to the end of a list of lists
	#for writing, pull the tail ends and return as an array that can be written
	tmp=[]
	for ii in mylist:
		tmp.append(ii[-1])
	return nm.array(tmp)


#=======================================================================
def read_pol_data_test(fpga,ndat):
	nn=ndat/2;
        assert(nn==1024) #if we fail this, we need to update a whole bunch of sizes below...                                                                                                              

	t1=time.time()
	ep0_raw=fpga.read('even_pol0',1024*8,0)
	op0_raw=fpga.read('odd_pol0',1024*8,0)
	ep1_raw=fpga.read('even_pol1',1024*8,0)
	op1_raw=fpga.read('odd_pol1',1024*8,0)
	
	even_real_raw=fpga.read('even_real',1024*8,0)
	even_im_raw=fpga.read('even_imaginary',1024*8,0)
	odd_real_raw=fpga.read('odd_real',1024*8,0)
	odd_im_raw=fpga.read('odd_imaginary',1024*8,0)
	t2=time.time()

	ep0= nm.array(struct.unpack('>1024Q',ep0_raw))
	op0= nm.array(struct.unpack('>1024Q',op0_raw))

	ep1= nm.array(struct.unpack('>1024Q',ep1_raw))
	op1= nm.array(struct.unpack('>1024Q',op1_raw))
	even_real=nm.array(struct.unpack('>1024q',even_real_raw))
	odd_real=nm.array(struct.unpack('>1024q',odd_real_raw))

	even_imaginary=nm.array(struct.unpack('>1024q',even_im_raw))
	odd_imaginary=nm.array(struct.unpack('>1024q',odd_im_raw))

	pol0=nm.ravel(nm.column_stack((ep0,op0)))
	pol1=nm.ravel(nm.column_stack((ep1,op1)))
	real_cross=nm.ravel(nm.column_stack((even_real,odd_real)))
	im_cross=nm.ravel(nm.column_stack((even_imaginary,odd_imaginary)))
	t3=time.time()
	print 'elapsed times in read are ',t2-t1,t3-t2
	return pol0,pol1,real_cross,im_cross
#=======================================================================
def read_pol_data(fpga,ndat):
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
	even_real = nm.array(struct.unpack(mystrq, fpga.read('even_real',nn*8,0)))
	even_imaginary = nm.array(struct.unpack(mystrq, fpga.read('even_imaginary',nn*8,0)))
	odd_real = nm.array(struct.unpack(mystrq, fpga.read('odd_real',nn*8,0)))
	odd_imaginary = nm.array(struct.unpack(mystrq, fpga.read('odd_imaginary',nn*8,0)))
	pol0=nm.ravel(nm.column_stack((ep0,op0)))
	pol1=nm.ravel(nm.column_stack((ep1,op1)))
	real_cross=nm.ravel(nm.column_stack((even_real,odd_real)))
	im_cross=nm.ravel(nm.column_stack((even_imaginary,odd_imaginary)))

	return pol0,pol1,real_cross,im_cross

#=======================================================================
def acquire_data_2017(fpga,opts,ndat=2048,wait_for_new=True):
	nn=ndat/2;
	#assert(nn==1024) #if we fail this, we need to update a whole bunch of sizes below...
	while True:
		tstart = time.time()
		if (tstart>1e5):
			tfrag=repr(tstart)[:5]
		else:
			print 'warning in acquire_data - tstart seems to be near zero.  Did you set your clock?'
			tfrag='00000'
		#outsubdir = opts.outdir+'/'+str(tstart)
		outsubdir = opts.outdir+'/'+tfrag +'/' + str(tstart)
		print outsubdir
		


                os.makedirs(outsubdir)
                logging.info('Writing current data to %s' %(outsubdir))

		f_timestamp1 = open(outsubdir+'/time_start.raw','w')
		f_timestamp2 = open(outsubdir+'/time_stop.raw','w')
		f_fft_shift = open(outsubdir+'/fft_shift.raw','w')
		f_fft_of_cnt = open(outsubdir+'/fft_of_cnt.raw','w')
		f_acc_cnt1 = open(outsubdir+'/acc_cnt1.raw','w')
		f_acc_cnt2 = open(outsubdir+'/acc_cnt2.raw','w')
		f_sys_clk1 = open(outsubdir+'/sys_clk1.raw','w')
		f_sys_clk2 = open(outsubdir+'/sys_clk2.raw','w')
		f_sync_cnt1 = open(outsubdir+'/sync_cnt1.raw','w')
		f_sync_cnt2 = open(outsubdir+'/sync_cnt2.raw','w')

		diff=not(opts.diff==0)
                f_aa=scio.scio(outsubdir+'/pol0.scio',diff=diff)
                f_bb=scio.scio(outsubdir+'/pol1.scio',diff=diff)
                f_ab_real=scio.scio(outsubdir+'/cross_real.scio',diff=diff)
                f_ab_imag=scio.scio(outsubdir+'/cross_imag.scio',diff=diff)

                while time.time()-tstart < opts.tfile*60:		
                        if wait_for_new and opts.sim is None:
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
                        t1 = time.time()
			if opts.sim is None:

                                fft_shift=fpga.read_uint('fft_shift')
                                fft_of_cnt= fpga.read_int('fft_of')  #this used to be fft_of_cnt
                                sys_clk1= fpga.read_int('sys_clkcounter')
                                sync_cnt1=fpga.read_int('sync_cnt')
				pol0,pol1,cross_real,cross_im=read_pol_data(fpga,ndat)

				#print nm.sum(nm.abs(pol0)),nm.sum(nm.abs(pol1)),nm.sum(nm.abs(cross_real)),nm.sum(nm.abs(cross_im))
				
				acc_cnt_end = fpga.read_int('acc_cnt')
				sys_clk2=fpga.read_int('sys_clkcounter') 
				sync_cnt2=fpga.read_int('sync_cnt') 
			t2=time.time()
			print 'elapsed time is ',t2-t1
			if acc_cnt_new != acc_cnt_end:
				logging.warning('Accumulation changed during data read')
			f_aa.append(pol0)
			f_bb.append(pol1)
			f_ab_real.append(cross_real)
			f_ab_imag.append(cross_im)
			nm.array(t1).tofile(f_timestamp1)
			nm.array(t2).tofile(f_timestamp2)
			nm.array(fft_shift).tofile(f_fft_shift)
			nm.array(fft_of_cnt).tofile(f_fft_of_cnt)
			nm.array(sys_clk1).tofile(f_sys_clk1)
			nm.array(sys_clk2).tofile(f_sys_clk2)
			nm.array(sync_cnt1).tofile(f_sync_cnt1)
			nm.array(sync_cnt2).tofile(f_sync_cnt2)
			nm.array(acc_cnt_end).tofile(f_acc_cnt2)
			nm.array(acc_cnt_new).tofile(f_acc_cnt1)
			f_timestamp1.flush()
			f_timestamp2.flush()
                        f_fft_shift.flush()
                        f_fft_of_cnt.flush()
                        f_acc_cnt1.flush()
			f_acc_cnt2.flush()
                        f_sys_clk1.flush()
                        f_sys_clk2.flush()
                        f_sync_cnt1.flush()
			f_sync_cnt2.flush()

                        time.sleep(opts.wait)
			


		#return


#=======================================================================
def acquire_data(fpga, opts, ndat=4096, nbit=8, wait_for_new=True):

	if opts.sim is None:
		try:
			regdict=spifpga.read_core_info('core_info.tab')
			fd=spifpga.config_spi()
			if (fd<0):
				print 'configuration failure in spifpga.  reverting to slower read'
				read_fast=False
			read_fast=True
		except:
			read_fast=False
        # ACQUIRE ALL THE DATAS!!!!
        while True:

                # Get current time stamp and use that for the output directory
                tstart = time.time()
		if (tstart>1e5):
			tfrag=repr(tstart)[:5]
		else:
			print 'warning in acquire_data - tstart seems to be near zero.  Did you set your clock?'
			tfrag='00000'
		#outsubdir = opts.outdir+'/'+str(tstart)
		outsubdir = opts.outdir+'/'+tfrag +'/' + str(tstart)
                os.makedirs(outsubdir)
                logging.info('Writing current data to %s' %(outsubdir))

                # Initialize data arrays
                nchan = len(opts.channel)
                timestamps1 = []
                timestamps2 = []
                fft_shift = []
                fft_of_cnt = []
                acc_cnt1 = []
                acc_cnt2 = []
                sys_clk1 = []
                sys_clk2 = []
                sync_cnt1 = []
                sync_cnt2 = []
                aa = [[] for i in range(nchan)]
                bb = [[] for i in range(nchan)]
                ab_real = [[] for i in range(nchan)]
                ab_imag = [[] for i in range(nchan)]

                # Open raw files for scio
		f_timestamp1 = open(outsubdir+'/time_start.raw','w')
		f_timestamp2 = open(outsubdir+'/time_stop.raw','w')
		f_fft_shift = open(outsubdir+'/fft_shift.raw','w')
		f_fft_of_cnt = open(outsubdir+'/fft_of_cnt.raw','w')
		f_acc_cnt1 = open(outsubdir+'/acc_cnt1.raw','w')
		f_acc_cnt2 = open(outsubdir+'/acc_cnt2.raw','w')
		f_sys_clk1 = open(outsubdir+'/sys_clk1.raw','w')
		f_sys_clk2 = open(outsubdir+'/sys_clk2.raw','w')
		f_sync_cnt1 = open(outsubdir+'/sync_cnt1.raw','w')
		f_sync_cnt2 = open(outsubdir+'/sync_cnt2.raw','w')
		f_aa=scio.scio(outsubdir+'/aa.scio')
		f_bb=scio.scio(outsubdir+'/bb.scio')
		f_ab_real=scio.scio(outsubdir+'/ab_real.scio')
		f_ab_imag=scio.scio(outsubdir+'/ab_imag.scio')
                # Save data in this subdirectory for specified time length
                while time.time()-tstart < opts.tfile*60:

                        # Wait for a new accumulation if we're reading
                        # from the FPGA
                        if wait_for_new and opts.sim is None:
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
                        t1 = time.time()
                        timestamps1.append(t1)
                        
                        # Read data from the actual SNAP board...
                        if opts.sim is None:

                                # Start with housekeeping registers
                                acc_cnt1.append( acc_cnt_new )
                                fft_shift.append( fpga.read_uint('fft_shift') )
                                fft_of_cnt.append( fpga.read_int('fft_of_cnt') )
                                sys_clk1.append( fpga.read_int('sys_clkcounter') )
                                sync_cnt1.append( fpga.read_int('sync_cnt') )

                                # Now read the actual data
                                for ic,c in enumerate(opts.channel):
                                        field = 'pol'+str(c)+'a'+str(c)+'a_snap'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'Q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'uint64')
                                        aa[ic].append(val)

                                        field = 'pol'+str(c)+'b'+str(c)+'b_snap'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'Q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'uint64')
                                        bb[ic].append(val)

                                        field = 'pol'+str(c)+'a'+str(c)+'b_snap_real'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'int64')
                                        ab_real[ic].append(val)

                                        field = 'pol'+str(c)+'a'+str(c)+'b_snap_imag'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'int64')
                                        ab_imag[ic].append(val)
                                        
                                # Check that new accumulation hasn't started during
                                # the previous read commands
                                acc_cnt_end = fpga.read_int('acc_cnt')
                                if acc_cnt_new != acc_cnt_end:
                                        logging.warning('Accumulation changed during data read')
                                acc_cnt2.append( acc_cnt_end )
                                sys_clk2.append( fpga.read_int('sys_clkcounter') )
                                sync_cnt2.append( fpga.read_int('sync_cnt') )
                                        
                        # ...or generate random numbers for testing purposes
                        else:
                                fft_shift.append( nm.random.random(1) )
                                fft_of_cnt.append( nm.random.random(1) )
                                acc_cnt1.append( nm.random.random(1) )
                                acc_cnt2.append( nm.random.random(1) )
                                sys_clk1.append( nm.random.random(1) )
                                sys_clk2.append( nm.random.random(1) )
                                sync_cnt1.append( nm.random.random(1) )
                                sync_cnt2.append( nm.random.random(1) )
                                for ic,c in enumerate(opts.channel):
                                        aa[ic].append( nm.random.random(ndat)*(ic+1) )
                                        bb[ic].append( nm.random.random(ndat)*(ic+1) )
                                        ab_real[ic].append( nm.random.random(ndat)*(ic+1) )
                                        ab_imag[ic].append( nm.random.random(ndat)*(ic+1) )

                        # Time stamp again after read commands are finished
                        t2 = time.time()
                        timestamps2.append(t2)
                        
                        # Write data with scio -- append to files
			nm.array(timestamps1[-1]).tofile(f_timestamp1)
			nm.array(timestamps2[-1]).tofile(f_timestamp2)
			nm.array(fft_shift[-1]).tofile(f_fft_shift)
			nm.array(fft_of_cnt[-1]).tofile(f_fft_of_cnt)
			nm.array(acc_cnt1[-1]).tofile(f_acc_cnt1)
			nm.array(acc_cnt2[-1]).tofile(f_acc_cnt2)
			nm.array(sys_clk1[-1]).tofile(f_sys_clk1)
			nm.array(sys_clk2[-1]).tofile(f_sys_clk2)
			nm.array(sync_cnt1[-1]).tofile(f_sync_cnt1)
			nm.array(sync_cnt2[-1]).tofile(f_sync_cnt2)
			f_timestamp1.flush()
			f_timestamp2.flush()
			f_fft_shift.flush()
			f_fft_of_cnt.flush()
			f_acc_cnt1.flush()
			f_acc_cnt2.flush()
			f_sys_clk1.flush()
			f_sys_clk2.flush()
			f_sync_cnt1.flush()
			f_sync_cnt2.flush()
			
			#scio.append(get_tail(aa),outsubdir+'/aa.scio')
			#scio.append(get_tail(bb),outsubdir+'/bb.scio')
			#scio.append(get_tail(ab_real),outsubdir+'/ab_real.scio')
			#scio.append(get_tail(ab_imag),outsubdir+'/ab_imag.scio')
			f_aa.append(get_tail(aa))
			f_bb.append(get_tail(bb))
			f_ab_real.append(get_tail(ab_real))
			f_ab_imag.append(get_tail(ab_imag))


			time.sleep(opts.wait)

                # End while loop over file chunk size

                # As a backup, write data to numpy files (should get
                # rid of this after testing).  This dumps just once at
                # the end of every chunk.
                nm.save(outsubdir+'/time_start.npy', nm.asarray(timestamps1))
                nm.save(outsubdir+'/time_stop.npy', nm.asarray(timestamps2))
                nm.save(outsubdir+'/fft_shift.npy', nm.asarray(fft_shift))
                nm.save(outsubdir+'/fft_of_cnt.npy', nm.asarray(fft_of_cnt))
                nm.save(outsubdir+'/acc_cnt1.npy', nm.asarray(acc_cnt1))
                nm.save(outsubdir+'/acc_cnt2.npy', nm.asarray(acc_cnt2))
                nm.save(outsubdir+'/sys_clk1.npy', nm.asarray(sys_clk1))
                nm.save(outsubdir+'/sys_clk2.npy', nm.asarray(sys_clk2))
                nm.save(outsubdir+'/sync_cnt1.npy', nm.asarray(sync_cnt1))
                nm.save(outsubdir+'/sync_cnt2.npy', nm.asarray(sync_cnt2))
                nm.save(outsubdir+'/aa.npy', nm.asarray(aa))
                nm.save(outsubdir+'/bb.npy', nm.asarray(bb))
                nm.save(outsubdir+'/ab_real.npy', nm.asarray(ab_real))
                nm.save(outsubdir+'/ab_imag.npy', nm.asarray(ab_imag))

        # End infinite loop

	return
        
#=======================================================================
if __name__ == '__main__':

        # Parse options
	parser = OptionParser()
	parser.set_usage('snap_daq.py <SNAP_HOSTNAME_or_IP> [options]')
	parser.set_description(__doc__)
	parser.add_option('-o', '--outdir', dest='outdir',type='str', default='/data/snap/raw',
		          help='Output directory [default: %default]')
	parser.add_option('-d', '--diff', dest='diff',type='int', default=0,
                          help='Write diffs - non-zero for yes [default 0]')
	
	parser.add_option('-l', '--logdir', dest='logdir',type='str', default='/data/snap/log',
		          help='Log directory [default: %default]')
	parser.add_option('-p', '--port', dest='port',type='int', default=7147,
		          help='Port number [default: %default]')
	parser.add_option('-c', '--channel', dest='channel',type='string', default=[0,1],
		          help='ADC channels as comma separated list [default: %default]',
                          action='callback', callback=channel_callback)
	parser.add_option('-a', '--acc_len', dest='acc_len', type='int',default=2*(2**28)/2048,
		          help='Number of vectors to accumulate between dumps [default: %default]')
	parser.add_option('-t', '--tfile', dest='tfile', type='int',default=15,
		          help='Number of minutes of data in each file subdirectory [default: %default]')
	parser.add_option('-n', '--nchan', dest='nchan', type='int',default=2048,
		          help='Number of minutes of data in each file subdirectory [default: %default]')
	parser.add_option('-w', '--wait', dest='wait', type='int',default=0,
		          help='Number of seconds to wait between taking spectra [default: %default]')
	parser.add_option('-s', '--sim', dest='sim', action='store_true',
		          help='Simulate incoming data [default: %default]')
	parser.add_option('-i', '--ip', dest='ip', type='str',default='146.230.231.73',
			  help='IP address of the raspberry pi')
	parser.add_option('-b', '--bof', dest='boffile',type='str', default='',
			  help='Specify the bof file to load')
	parser.add_option('-C','--comment',dest='comment',type='str',default='',help='Comment for log')
	opts, args = parser.parse_args(sys.argv[1:])

	#print ' comment is ' + opts.comment
	#print type(opts.comment)
	#print len(opts.comment)
	#assert(1==0)
	if (True):
		if opts.sim is None:
			snap_ip=opts.ip

	else:
		if args==[]:
			if opts.sim is None:
				print 'Please specify a SNAP board. Run with the -h flag to see all options.\nExiting.'
				exit()
		else:
		        #snap_ip = args[0]
			snap_ip=opts.ip

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
        logging.info('ADC channel selection: %s' %(opts.channel))
        logging.info('Accumulate length: %d' %(opts.acc_len))
        logging.info('Minutes per file: %d' %(opts.tfile))
        logging.info('Seconds between spectra: %d' %(opts.wait))
        logging.info('Simulation mode: %s' %(opts.sim))
	logging.info('Comment: %s' % (opts.comment))
        logging.info('================================')

        # Connect to SNAP board and initialize if not in sim mode
        fpga = None
        if opts.sim is None:
                fpga = initialize_snap(snap_ip, opts)


	time.sleep(5)
	nchan=opts.nchan
	print 'nchan is ' + repr(nchan)
	acquire_data_2017(fpga,opts,nchan)
	fpga.stop

	print 'List of registers: \n',fpga.listdev()  #Lists all the registers
	assert(1==0)   

        # Acquire data
        logging.info('Writing data to top level location %s' %(opts.outdir))
        if not os.path.exists(opts.outdir):
                os.makedirs(opts.outdir)
                print 'Created directory', opts.outdir
	try:
		acquire_data(fpga, opts)
	finally:
		logging.info('Terminating DAQ script at %s' % str(time.time()))
