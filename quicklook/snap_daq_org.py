#!/usr/bin/python
import corr, time, struct, sys, logging, pylab, os
import numpy as nm
from optparse import OptionParser

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
        """Deal with user-specified ADC channel selection."""
        setattr(parser.values, option.dest, [int(v) for v in value.split(',')])
        return

#=======================================================================
def initialize_snap(snap_ip, opts, timeout=10):
        """Connect to SNAP board, configure settings"""

        # Set up SNAP logger
        lh = corr.log_handlers.DebugLogHandler()
        logger = logging.getLogger(snap_ip)
        logger.addHandler(lh)
        logger.setLevel(10)

        # Connect to the SNAP board configure spectrometer settings
        logger.info('Connecting to server %s on port %i... '%(snap_ip, opts.port))
        fpga = corr.katcp_wrapper.FpgaClient(snap_ip, opts.port, timeout=timeout, logger=logger)
        time.sleep(1)

        if fpga.is_connected():
	        logger.info('Connected!')
        else:
	        logger.error('ERROR connecting to %s on port %i.' %(snap,opts.port))
	        exit_fail()

        logger.info('Configuring accumulation period...')
        fpga.write_int('acc_len', opts.acc_len)
        fpga.write_int('fft_shift', 0xFFFFFFFF)
        logger.info('Done configuring')

        time.sleep(2)

        return fpga

#=======================================================================
def acquire_data(fpga, opts, ndat=4096, nbit=8):

        # ACQUIRE ALL THE DATAS!!!!
        while True:

                # Get current time stamp and use that for the output directory
                tstart = time.time()
                outsubdir = opts.outdir+'/'+str(tstart)
                os.makedirs(outsubdir)
                logging.info('Writing current data to %s' %(outsubdir))

                # Initialize data arrays
                nchan = len(opts.channel)
                timestamps = []
                aa = [[] for i in range(nchan)]
                bb = [[] for i in range(nchan)]
                ab_real = [[] for i in range(nchan)]
                ab_imag = [[] for i in range(nchan)]

                # Save data for specified time length
                while time.time()-tstart < opts.tfile*60:
                
                        t1 = time.time()
                        # Read data from the actual SNAP board...
                        if opts.sim is None:
                                for ic,c in enumerate(opts.channel):
                                        field = 'pol'+str(c)+'a'+str(c)+'a_snap'
                                        val = nm.array(struct.unpack('>'+str(ndat)+'Q', fpga.read(field,ndat*nbit,0)))
                                        aa[ic].append(val)

                                        field = 'pol'+str(c)+'b'+str(c)+'b_snap'
                                        val = nm.array(struct.unpack('>'+str(ndat)+'Q', fpga.read(field,ndat*nbit,0)))
                                        bb[ic].append(val)

                                        field = 'pol'+str(c)+'a'+str(c)+'b_snap_real'
                                        val = nm.array(struct.unpack('>'+str(ndat)+'q', fpga.read(field,ndat*nbit,0)))
                                        ab_real[ic].append(val)

                                        field = 'pol'+str(c)+'a'+str(c)+'b_snap_imag'
                                        val = nm.array(struct.unpack('>'+str(ndat)+'q', fpga.read(field,ndat*nbit,0)))
                                        ab_imag[ic].append(val)
                        # ...or generate random numbers for testing purposes
                        else:
                                for ic,c in enumerate(opts.channel):
                                        aa[ic].append( nm.random.random(ndat)*(ic+1) )
                                        bb[ic].append( nm.random.random(ndat)*(ic+1) )
                                        ab_real[ic].append( nm.random.random(ndat)*(ic+1) )
                                        ab_imag[ic].append( nm.random.random(ndat)*(ic+1) )
                                
                        t2 = time.time()
                        timestamps.append( 0.5*(t1+t2) )

                        time.sleep(opts.wait)
                # End while loop over file chunk size

                # Write data to disk
                nm.save(outsubdir+'/time.npy', nm.asarray(timestamps))
                nm.save(outsubdir+'/aa.npy', nm.squeeze(nm.asarray(aa)))
                nm.save(outsubdir+'/bb.npy', nm.squeeze(nm.asarray(bb)))
                nm.save(outsubdir+'/ab_real.npy', nm.squeeze(nm.asarray(ab_real)))
                nm.save(outsubdir+'/ab_imag.npy', nm.squeeze(nm.asarray(ab_imag)))

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
	parser.add_option('-w', '--wait', dest='wait', type='int',default=10,
		          help='Number of seconds to wait between taking spectra [default: %default]')
	parser.add_option('-s', '--sim', dest='sim', action='store_true',
		          help='Simulate incoming data [default: %default]')
	opts, args = parser.parse_args(sys.argv[1:])

	if args==[]:
                if opts.sim is None:
		        print 'Please specify a SNAP board. Run with the -h flag to see all options.\nExiting.'
		        exit()
	else:
		snap_ip = args[0]

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
        logging.info('================================')
        
        # Connect to SNAP board and initialize if not in sim mode
        fpga = None
        if opts.sim is None:
                fpga = initialize_snap(snap_ip, opts)

        # Acquire data
        logging.info('Writing data to top level location %s' %(opts.outdir))
        if not os.path.exists(opts.outdir):
                os.makedirs(opts.outdir)
                print 'Created directory', opts.outdir
        acquire_data(fpga, opts)
