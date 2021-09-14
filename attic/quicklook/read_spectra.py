import scihi_tools as st
import pylab
import numpy
import optparse 
import datetime

#=======================================================================
def plot_waterfall(pol,log10=True):
	"""
	Function to plot 2D waterfall plot

	- pol: data to plot
	"""
	if log10:
		waterfall = numpy.log10(pol)
	else:
		waterfall = pol
        median = numpy.median(waterfall)
       	std = numpy.std(waterfall)
        vmin , vmax = median-std , median+std
        nu=((numpy.arange(waterfall.shape[1])+0.5)/(1.0*waterfall.shape[1]))*250; # frequency range in MHz               
	im = pylab.imshow(waterfall,aspect='auto',extent=[0,nu[-1],waterfall.shape[0],0],vmin=vmin,vmax=vmax)
	pylab.colorbar(im)

#=======================================================================
def plot_run(scihi_dat, plot_70=True, plot_100=True,utc=True, median=True , mean=True):
	"""
	Plot waterfall plot for the entires= observation a/o individual calibrators
	
	- scihi_dat: SCI-HI data dictionary with appropriate antenna and switch entries
	- run: plot whole observation of SCIHI data, without splitting the calibrators
	- antenna: plot antenna data only
	- res50: plot res50 data only
	- res100: plot res100 data only
	- short: plot short data only
	- plot_70: plot 70 MHz data	
	- plot_100: plot 100 MHz data
	"""

	if plot_70:
              # Read pol0 and pol1 from 70 MHz data
	      pol0 = scihi_dat['70']['pol0']
	      pol1 = scihi_dat['70']['pol1']
	      cross_real = scihi_dat['70']['cross_real']
	      cross_imag = scihi_dat['70']['cross_imag']
	      cross = cross_real + 1j*cross_imag
              timestart = scihi_dat['70']['time_start']
	      timestop = scihi_dat['70']['time_stop']
	      time_utc = []
              timestamps = numpy.linspace(timestart[0],timestop[-1],20)
              [time_utc.append(str(datetime.datetime.utcfromtimestamp(t)).split('.')[0]) for t in timestamps]

	      nu=((numpy.arange(pol0.shape[1])+0.5)/(1.0*pol0.shape[1]))*250; # frequency range in MHz 
      	      tt = numpy.linspace(0,pol0.shape[0],20)
	      fig = pylab.figure()
	      pylab.suptitle('70 MHz data',fontsize=15)

	      # pol0
	      pylab.subplot(221)
	      pylab.title('Pol0 (log)')
	      plot_waterfall(pol0,log10=True)
	      if utc:
                 pylab.yticks(tt,time_utc,fontsize=6)
      
	      # pol1
	      pylab.subplot(222)
	      pylab.title('Pol1 (log)')
	      plot_waterfall(pol1,log10=True)
	      if utc:
                 pylab.yticks(tt,time_utc,fontsize=6)

	      # cross_real
	      pylab.subplot(223)
	      pylab.title('Cross amplitude (log)')
	      plot_waterfall(numpy.abs(cross),log10=True)
	      if utc:
                 pylab.yticks(tt,time_utc,fontsize=6)

	      # cross_imag
	      pylab.subplot(224)
	      pylab.title('Cross phase (deg)')
	      plot_waterfall(numpy.rad2deg(numpy.angle(cross)),log10=False)
	      if utc:
	      	 pylab.yticks(tt,time_utc,fontsize=6)

	      fig.text(0.46, 0.02,'Frequency [MHz]', ha='center',size=12)
	      if utc:
 	   	 fig.text(0.04, 0.56,'UTC', rotation='vertical',ha='center',size=12)
	      else:
		 fig.text(0.07, 0.56,'Timestamps', rotation='vertical',ha='center',size=12)

              print 'Plotting Average spectra'
	      fig = pylab.figure()
	      pylab.suptitle('70 MHz data',fontsize=15)

	      pylab.subplot(211)
              pylab.title('Pol0')
              if mean:
                 pylab.plot(nu,numpy.mean(pol0,axis=0),'r-',linewidth=2, label='mean',alpha=0.7)
              if median:
                 pylab.plot(nu,numpy.median(pol0,axis=0),'g-',linewidth=2, label='median',alpha=0.7)

	      pylab.subplot(212)
              pylab.title('Pol1')
              if mean:
                 pylab.plot(nu,numpy.mean(pol1,axis=0),'r-',linewidth=2, label='mean',alpha=0.7)
              if median:
                 pylab.plot(nu,numpy.median(pol1,axis=0),'g-',linewidth=2, label='median',alpha=0.7)
              pylab.legend()
              pylab.xlabel('Frequency [MHz]')            

 	if plot_100:
              # Read pol0 and pol1 from 100 MHz data
	      pol0 = scihi_dat['100']['pol0']	
	      pol1 = scihi_dat['100']['pol1']
	      cross_real = scihi_dat['100']['cross_real']
              cross_imag = scihi_dat['100']['cross_imag']
	      cross = cross_real  + 1j*cross_imag
              timestart = scihi_dat['100']['time_start']
              timestop = scihi_dat['100']['time_stop']
	      time_utc = []
 	      timestamps = numpy.linspace(timestart[0],timestop[-1],20)
              [time_utc.append(str(datetime.datetime.utcfromtimestamp(t)).split('.')[0]) for t in timestamps]

	      nu=((numpy.arange(pol0.shape[1])+0.5)/(1.0*pol0.shape[1]))*250; # frequency range in MHz 
	      tt = numpy.linspace(0,pol0.shape[0],20)
	      fig = pylab.figure()
	      pylab.suptitle('100 MHz data',fontsize=15)

	      # pol0
              pylab.subplot(221)
	      pylab.title('Pol0 (log)')
              plot_waterfall(pol0,log10=True)
	      if utc:
	         pylab.yticks(tt,time_utc,fontsize=6)

              # pol1
              pylab.subplot(222)
              pylab.title('Pol1 (log)')
              plot_waterfall(pol1,log10=True)
	      if utc:
		 pylab.yticks(tt,time_utc,fontsize=6)


              # cross_real
              pylab.subplot(223)
              pylab.title('Cross amplitude (log)')
              plot_waterfall(numpy.abs(cross),log10=True)
	      if utc:
                 pylab.yticks(tt,time_utc,fontsize=6)

              # cross_imag
              pylab.subplot(224)
              pylab.title('Cross_Phase (deg)')
              plot_waterfall(numpy.rad2deg(numpy.angle(cross)),log10=False)
              if utc:
                 pylab.yticks(tt,time_utc,fontsize=6)

		
              fig.text(0.46, 0.02,'Frequency [MHz]', ha='center',size=12)
              if utc:
                 fig.text(0.04, 0.56,'UTC', rotation='vertical',ha='center',size=12)
              else:
                 fig.text(0.07, 0.56,'Timestamps', rotation='vertical',ha='center',size=12)           
	      print 'Plotting averaged spectra'
              fig = pylab.figure()
	      pylab.suptitle('100 MHz data',fontsize=15)
	      pylab.subplot(211)
	      pylab.title('Pol0')
	      if mean:
		 pylab.plot(nu,numpy.mean(pol0,axis=0),'r-',linewidth=2, label='mean',alpha=0.7)
	      if median:
		 pylab.plot(nu,numpy.median(pol0,axis=0),'g-',linewidth=2, label='median',alpha=0.7)

              pylab.subplot(212)
	      pylab.title('Pol1')
	      if mean:
                 pylab.plot(nu,numpy.mean(pol1,axis=0),'r-',linewidth=2, label='mean',alpha=0.7)
              if median:
                 pylab.plot(nu,numpy.median(pol1,axis=0),'g-',linewidth=2, label='median',alpha=0.7)
	      pylab.legend()
	      pylab.xlabel('Frequency [MHz]')

	pylab.show()

#=======================================================================
def plot_calibrators(scihi_dat,run=True, antenna=True, res50=True, res100=True, short=True, plot_70=True, plot_100=True,utc=True, median=False, mean=False):
        """
        Plot waterfall plot for the entires= observation a/o individual calibrators
        
        - scihi_dat: SCI-HI data dictionary with appropriate antenna and switch entries
	- run: plot whole set of run
	- antenna: extract antenna data
	- res50: extract res50 data
	- res100: extract res100 data
	- short: extract short data
	- plot_70: plot 70 MHz data
	- plot_100: plot 100 MHz data
        - utc: display time in UTC
	- mean: plot mean over all the timestamps
        - median: plot median over all the timestamps
        """       
       
	if plot_70:
	    if antenna:
           	select_calibrators(scihi_dat,calibrator='antenna',frequency='70',mean=mean, median=median)	  
	    if res50:
                select_calibrators(scihi_dat,calibrator='res50',frequency='70',mean=mean, median=median)
	    if short:
                select_calibrators(scihi_dat,calibrator='short',frequency='70',mean=mean, median=median)
	    if res100:
                select_calibrators(scihi_dat,calibrator='res100',frequency='70',mean=mean, median=median)
	    if run:
		select_calibrators(scihi_dat,run=True,frequency='70',mean=mean, median=median)

        if plot_100:
            if antenna:
                select_calibrators(scihi_dat,calibrator='antenna',frequency='100',mean=mean, median=median,utc=utc)
            if res50:
                select_calibrators(scihi_dat,calibrator='res50',frequency='100',mean=mean, median=median,utc=utc)
            if short:
                select_calibrators(scihi_dat,calibrator='short',frequency='100',mean=mean, median=median,utc=utc)
            if res100:
                select_calibrators(scihi_datrun=run,calibrator='res100',frequency='100',mean=mean, median=median,utc=utc)
	    if run:
                select_calibrators(scihi_dat,run=True,frequency='100',mean=mean, median=median)

	pylab.show()
   
   
#=======================================================================
def select_calibrators(scihi_dat,run=True,calibrator=None,frequency=None,utc=True,mean=False,median=False):
        """
	Select the calibrator to plot

	- scihi_dat: SCI-HI data dictionary with appropriate antenna and switch entries
	- run: select the whole set of run
        - calibrator: calibrator data you want to extract [e.g 'antenna','res50','res100','short']
        - frequency: frquency of the antenna [either '70' or '100']
	- utc: display time in UTC
	- mean: plot mean over all the timestamps
	- median: plot median over all the timestamps
	"""
	pol0 = scihi_dat[frequency]['pol0']
        pol1 = scihi_dat[frequency]['pol1']
        cross_real = scihi_dat[frequency]['cross_real']
        cross_imag = scihi_dat[frequency]['cross_imag']
        cross = cross_real  + 1j*cross_imag
        timestart = scihi_dat[frequency]['time_start']
        timestop = scihi_dat[frequency]['time_stop']
	nu=((numpy.arange(pol0.shape[1])+0.5)/(1.0*pol0.shape[1]))*250; # frequency range in MHz

	if run:
           pol0_cal = pol0
	   pol1_cal = pol1
           cross_cal = cross
           time_utc = []
           timestamps = numpy.linspace(timestart[0],timestop[-1],20)
           [time_utc.append(str(datetime.datetime.utcfromtimestamp(t)).split('.')[0]) for t in timestamps]
	   calibrator = 'run'        

        else:
           st.add_switch_flag(scihi_dat, antennas=[frequency])
           switch_flags = scihi_dat[frequency]['switch_flag']
           if calibrator == 'antenna': bits = 2**0
       	   if calibrator == 'res100': bits = 2**1
	   if calibrator == 'short': bits = 2**2
           if calibrator == 'res50': bits = 2**3

           pol0_cal = pol0[switch_flags==bits]
           pol1_cal = pol1[switch_flags==bits]
           cross_real_cal = cross_real[switch_flags==bits]
	   cross_imag_cal = cross_imag[switch_flags==bits]
	   cross_cal = cross_real_cal + 1j*cross_imag_cal
	   timestart_cal = timestart[switch_flags==bits]
	   timestop_cal = timestop[switch_flags==bits]
	   time_utc = []
           timestamps = numpy.linspace(timestart_cal[0],timestop_cal[-1],20)
           [time_utc.append(str(datetime.datetime.utcfromtimestamp(t)).split('.')[0]) for t in timestamps]
 

        fig  = pylab.figure()
        pylab.suptitle('%s MHz %s data'%(frequency,calibrator),fontsize=15)
	
        # pol 0
        pylab.subplot(221)
        pylab.title('Pol0 (log)')
        plot_waterfall(pol0_cal,log10=True)
        tt = numpy.linspace(0,pol0_cal.shape[0],20)
        if utc:
            pylab.yticks(tt,time_utc,fontsize=6)

        # pol 1
        pylab.subplot(222)
        pylab.title('Pol1 (log)')
        plot_waterfall(pol1_cal,log10=True)
        tt = numpy.linspace(0,pol1_cal.shape[0],20)
        if utc:
            pylab.yticks(tt,time_utc,fontsize=6)

        # cross amplitude
        pylab.subplot(223)
        pylab.title('Cross amplitude (log)')
        plot_waterfall(numpy.abs(cross_cal),log10=True)
        tt = numpy.linspace(0,cross_cal.shape[0],20)
        if utc:
            pylab.yticks(tt,time_utc,fontsize=6)

        # cross phase
        pylab.subplot(224)
        pylab.title('Cross Phase (deg)')
        plot_waterfall(numpy.rad2deg(numpy.angle(cross_cal)),log10=False)

        tt = numpy.linspace(0,cross_cal.shape[0],20)
        if utc:
            pylab.yticks(tt,time_utc,fontsize=6)


        fig.text(0.46, 0.02,'Frequency [MHz]', ha='center',size=12)
        if utc:
             fig.text(0.04, 0.56,'UTC', rotation='vertical',ha='center',size=12)
        else:
             fig.text(0.07, 0.56,'Timestamps', rotation='vertical',ha='center',size=12)

        print 'Plotting averaged spectra'
        fig = pylab.figure()
        pylab.suptitle('%s MHz %s data'%(frequency,calibrator),fontsize=15)
        pylab.subplot(211)
        pylab.title('Pol0')
        if mean:
            pylab.plot(nu,numpy.mean(pol0_cal,axis=0),'r-',linewidth=2, label='mean',alpha=0.7)
        if median:
            pylab.plot(nu,numpy.median(pol0_cal,axis=0),'g-',linewidth=2, label='median',alpha=0.7)

        pylab.subplot(212)
        pylab.title('Pol1')
        if mean:
             pylab.plot(nu,numpy.mean(pol1_cal,axis=0),'r-',linewidth=2, label='mean',alpha=0.7)
        if median:
             pylab.plot(nu,numpy.median(pol1_cal,axis=0),'g-',linewidth=2, label='median',alpha=0.7)
        pylab.legend()
        pylab.xlabel('Frequency [MHz]')


#=======================================================================
if '__name__==__main__':
	time_start = '20170503_000000'
	time_stop = '20170503_050000'

	t0 = st.timestamp2ctime(time_start)
	t1 = st.timestamp2ctime(time_stop)

	scihi_dat = st.read_scihi_data(t0, t1, dir_top='/media/scihi/SCIHI_DISK1/marion2017', subdir_switch='switch_data',subdir_temp='switch_data',read_100=True, read_70=True,read_switch=False, read_temp=False, verbose=True)
	#st.add_switch_flag(scihi_dat, antennas=['100'])

	#plot_run(scihi_dat, run=True, antenna=False, res50=False, res100=False, short=False, plot_70=True, plot_100=True)

        plot_calibrators(scihi_dat, run=True ,antenna=False, res50=False, res100=False, short=False, plot_70=False, plot_100=True,utc=True, median=True, mean=True)

