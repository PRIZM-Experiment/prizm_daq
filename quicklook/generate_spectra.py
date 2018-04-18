import numpy,pylab
import scio
import optparse
import os,sys
import time
import datetime
import re

if '__name__==__main__':
	o = optparse.OptionParser()
	o.set_usage('python plot_spectra.py [options] *.directories')
        o.set_description(__doc__)
	o.add_option('--spectra',dest='spectra',action='store_true',help='Set to output 2D spetctra')
	o.add_option('--mean',dest='mean',action='store_true',help='Set to output averaged spectra')
	o.add_option('--temp',dest='temp',action='store_true',help='Set to output temperature plots')
	o.add_option('--acc',dest='acc',action='store_true',help='Set to output accumulation plots')
	o.add_option('--phys',dest='phys',action='store_true',help='To display time in UTC')
	#o.add_option('spath', dest='spath',default=None, help='Path where files spit by switch are stored')
	opts,args = o.parse_args(sys.argv[1:])

        f_aa , f_bb = None, None
        f_cross_real , f_cross_imag, f_cross = None, None, None
        f_t_start, f_t_stop = numpy.array([]), numpy.array([])
	f_acc_cnt1, f_acc_cnt2 = numpy.array([]), numpy.array([])
	f_fft_of_cnt, f_fft_shift = numpy.array([]), numpy.array([])
	f_sys_clk1, f_sys_clk2 = numpy.array([]), numpy.array([])
	f_sync_cnt1, f_sync_cnt2 = numpy.array([]), numpy.array([])
	f_pi_temp, f_fpga_temp = numpy.array([]), numpy.array([])
	utctime = []
	for dname in args:
		try:
			print 'Opening ', dname
			scio_fields = ['pol0.scio', 'pol1.scio', 'cross_real.scio', 'cross_imag.scio']
		        for field in scio_fields:
			   if not os.path.exists(dname + '/' + field):
			      print 'read_scihi_data: decompressing', dname +'/'+field
			      os.system('bzip2 -dk ' + dname + '/' + field +'.bz2')
                        #os.system('bzip2 -dk ' + dname + '/pol0.scio.bz2')
			#os.system('bzip2 -dk ' + dname + '/pol1.scio.bz2')
			#os.system('bzip2 -dk ' + dname + '/cross_real.scio.bz2')
			#os.system('bzip2 -dk ' + dname + '/cross_imag.scio.bz2')

                        print 'read_scihi_data: reading scio files in', dname 
			pol0 = scio.read(dname + '/pol0.scio')
                	pol1 = scio.read(dname + '/pol1.scio')
			cross_real = scio.read(dname + '/cross_real.scio')
			cross_imag = scio.read(dname + '/cross_imag.scio')
			cross = cross_real + 1j*cross_imag

			print 'Reading raw files'
			t_start = numpy.fromfile(dname + '/time_start.raw')
			t_stop = numpy.fromfile(dname + '/time_stop.raw')
			acc_cnt1 = numpy.fromfile(dname + '/acc_cnt1.raw',dtype='int32')
			acc_cnt2 = numpy.fromfile(dname + '/acc_cnt2.raw',dtype='int32')
			fft_of_cnt = numpy.fromfile(dname + '/fft_of_cnt.raw',dtype='int32')
			fft_shift = numpy.fromfile(dname + '/fft_shift.raw',dtype='int32')
			sys_clk1 = numpy.fromfile(dname + '/sys_clk1.raw',dtype='int32')
			sys_clk2 = numpy.fromfile(dname + '/sys_clk2.raw',dtype='int32')
			sync_cnt1 = numpy.fromfile(dname + '/sync_cnt1.raw',dtype='int32')
			sync_cnt2 = numpy.fromfile(dname + '/sync_cnt2.raw',dtype='int32')
			pi_temp = numpy.fromfile(dname + '/pi_temp.raw',dtype='int32')
		   	fpga_temp = numpy.fromfile(dname + '/fpga_temp.raw')
              
			f_aa = pol0  if f_aa == None else numpy.vstack((f_aa,pol0)) 
			f_bb = pol1  if f_bb == None else numpy.vstack((f_bb,pol1))
			f_cross_real = cross_real  if f_cross_real == None else numpy.vstack((f_cross_real,cross_real))
			f_cross_imag = cross_imag  if f_cross_imag == None else numpy.vstack((f_cross_imag,cross_imag))
			f_cross = cross if f_cross == None else numpy.vstack((f_cross,cross))

			f_t_start = numpy.append(f_t_start,t_start);
			f_t_stop = numpy.append(f_t_stop,t_stop);
			f_acc_cnt1 = numpy.append(f_acc_cnt1,acc_cnt1)
			f_acc_cnt2 = numpy.append(f_acc_cnt2,acc_cnt2)
			f_fft_of_cnt = numpy.append(f_fft_of_cnt,fft_of_cnt)
			f_fft_shift = numpy.append(f_fft_shift,fft_shift)
			f_sys_clk1 = numpy.append(f_sys_clk1,sys_clk1)
			f_sys_clk2 = numpy.append(f_sys_clk2,sys_clk2)
			f_sync_cnt1 = numpy.append(f_sync_cnt1,sync_cnt1)
			f_sync_cnt2 = numpy.append(f_sync_cnt2,sync_cnt2)
			f_pi_temp = numpy.append(f_pi_temp,pi_temp/1000.)
			f_fpga_temp = numpy.append(f_fpga_temp,fpga_temp)
		except:
			continue

	if opts.phys:
	      time_utc = []
              timestamps = numpy.linspace(f_t_start[0],f_t_stop[-1],20)
              [time_utc.append(str(datetime.datetime.utcfromtimestamp(t)).split('.')[0]) for t in timestamps]
	
       
	nu=((numpy.arange(f_aa.shape[1])+0.5)/(1.0*f_aa.shape[1]))*250; # frequency range
        #nu=numpy.arange(f_aa.shape[1])

	if opts.spectra:
                print 'Plotting 2D Spectra'
		tt = numpy.linspace(0,f_aa.shape[0],20)
		fig = pylab.figure()
		pylab.subplot(221)
		pylab.title('Pol0 (log)')
		plotspec = numpy.log10(numpy.abs(f_aa))
                median = numpy.median(plotspec)
		std = numpy.std(plotspec)
		vmin = median-std; vmax = median + std
		im = pylab.imshow(plotspec,aspect='auto',vmin=vmin,vmax=vmax,extent=[0,nu[-1],f_aa.shape[0],0])
		pylab.colorbar(im)
		if opts.phys:
			pylab.yticks(tt,time_utc,fontsize=6)

                pylab.subplot(222)
                pylab.title('Pol1 (log)')
		plotspec = numpy.log10(numpy.abs(f_bb))
		median = numpy.median(plotspec)
                std = numpy.std(plotspec)
                vmin = median-std; vmax = median + std

                im = pylab.imshow(plotspec,aspect='auto',vmin=vmin,vmax=vmax,extent=[0,nu[-1],f_bb.shape[0],0])
		pylab.colorbar(im)
		if opts.phys:
                        pylab.yticks(tt,time_utc,fontsize=6)
		
                pylab.subplot(223)
                pylab.title('Cross Amplitude (log)')
		plotspec = numpy.log10(numpy.abs(f_cross))
                median = numpy.median(plotspec)
                std = numpy.std(plotspec)
                vmin = median-std; vmax = median + std
                im = pylab.imshow(plotspec,aspect='auto',vmin=vmin,vmax=vmax,extent=[0,nu[-1],f_cross_real.shape[0],0])
		pylab.colorbar(im)
		if opts.phys:
                        pylab.yticks(tt,time_utc,fontsize=6)

                pylab.subplot(224)
                pylab.title('Cross Phase (deg)')
		#plotspec = numpy.log10(numpy.abs(f_cross_imag))
		plotspec = numpy.rad2deg(numpy.angle(f_cross))
                median = numpy.median(plotspec)
                std = numpy.std(plotspec)
                vmin = median-std; vmax = median + std
                im = pylab.imshow(plotspec,aspect='auto',vmin=vmin,vmax=vmax,extent=[0,nu[-1],f_cross_imag.shape[0],0])
		pylab.colorbar(im)
		if opts.phys:
                        pylab.yticks(tt,time_utc,fontsize=6)        	 
       
		fig.text(0.46, 0.02,'Frequency [MHz]', ha='center',size=12)
		if opts.phys:
			fig.text(0.04, 0.56,'Time [UTC]', rotation='vertical',ha='center',size=12)
		else:
			fig.text(0.07, 0.56,'Timestamps', rotation='vertical',ha='center',size=12)
	

	if opts.mean:
		print 'Plotting average spectra'
		fig = pylab.figure()
                pylab.subplot(211)
                pylab.title('Pol0')
                pylab.plot(nu,numpy.mean(f_aa,axis=0),'k-',linewidth=2)

		pylab.subplot(212)
                pylab.title('Pol1')
                pylab.plot(nu,numpy.mean(f_bb,axis=0),'k-',linewidth=2)
		pylab.xlabel('Frequency [MHz]')
         
                fig.text(0.07, 0.56,'Amplitude', rotation='vertical',ha='center',size=12)
         
	if opts.temp:
		print 'Plotting temperature'
		fig = pylab.figure()
		pylab.subplot(211)
		pylab.title('Pi Temperature')
   		pylab.plot(f_pi_temp,'k-',linewidth=2)
		pylab.ylabel('Temperature [$^{\circ}$C]')

		pylab.subplot(212)
		pylab.title('FPGA Tempeature')
		pylab.plot(f_fpga_temp,'k-',linewidth=2)
		pylab.xlabel('Timestamps')
		pylab.ylabel('Temperature [$^{\circ}$C]')

	if opts.acc:
		print 'Plot accummulation plots'
		pylab.figure()
		pylab.subplot(321)
		pylab.plot(f_t_stop-f_t_start,'k.',linewidth=2)
		pylab.ylabel('$\Delta$ t (sec)')
		pylab.xlabel('Spectrum number')

		pylab.subplot(322)
		pylab.plot(f_acc_cnt1-f_acc_cnt2,'k.',linewidth=2)
		pylab.ylabel('$\Delta$ (acc)')
		pylab.xlabel('Spectrum number')

		pylab.subplot(323)
		pylab.plot(f_sys_clk2-f_sys_clk1,'k.',linewidth=2)
		pylab.ylabel('$\Delta$ clock (sec)')
		pylab.xlabel('Spectrum number')

		pylab.subplot(324)
		pylab.plot(f_sync_cnt2-f_sync_cnt1,'k.',linewidth=2)
		pylab.ylabel('$\Delta$ sync count')
		pylab.xlabel('Spectrum number')

		pylab.subplot(325)
		pylab.plot(fft_of_cnt,'k.',linewidth=2)
		pylab.ylabel('fft of cnt')
		pylab.xlabel('Spectrum number')

		pylab.subplot(326)
		pylab.plot(f_fft_shift,'k.',linewidth=2)
		pylab.ylabel('fft shift')
		pylab.xlabel('Spectrum number')

	pylab.show()
	
