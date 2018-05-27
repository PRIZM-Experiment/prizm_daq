import numpy as nm
import scio, pylab, datetime

#============================================================
def ctime2timestamp(ctimes, string=False):
    """Given a (list of) ctime, convert to human friendly format.  - ctime
    = ctime(s) in desired text format Returns the time stamps (or list
    of time stamps) in human friendly format.

    If string is True, then return string formatted date, otherwise
    return datetime object.
    """
    if isinstance(ctimes, (int, float)):
        if string:
            return str(datetime.datetime.utcfromtimestamp(ctimes))
        else:
            return datetime.datetime.utcfromtimestamp(ctimes)
    else:
        if string:
            return [ str(datetime.datetime.utcfromtimestamp(c)) for c in ctimes ]
        else:
            return [ datetime.datetime.utcfromtimestamp(c) for c in ctimes ]

#============================================================
# d = '/media/scihi/SCIHI_DISK1/marion2018/data_singlesnap/15274/1527456780'
# lastsubdir = '1527456780'
# antname = 'LWA'
# d = '/media/scihi/SCIHI_DISK1/marion2018/data_70MHz/15274/1527403741'
# lastsubdir = '1527403741'
# antname = '70MHz'
d = '/media/scihi/SCIHI_DISK1/marion2018/data_100MHz/15273/1527332452'
lastsubdir = '1527332452'
antname = '100MHz'

plot_dir = '/home/scihi/quicklook_plots'

tstamp = ctime2timestamp(int(lastsubdir))
tstamp_outfile = tstamp.strftime('%Y%m%d_%H%M%S')  # YYYYMMMDD_HHMMSS format for outfile
# Plotting routines for PRIZM antennas
if antname == '100MHz' or antname == '70MHz':
    # Deal with time stamps
    t1 = nm.fromfile(d+'/time_sys_start.raw')
    t2 = nm.fromfile(d+'/time_sys_stop.raw')
    time = 0.5*(t1+t2)
    time = nm.asarray(ctime2timestamp(time, string=True))

    fields = ['pol0.scio', 'pol1.scio']
    pylab.figure(figsize=(15,10))
    for ifig,field in enumerate(fields):
        ps = scio.read(d+'/'+field)
        freq = nm.arange(nm.shape(ps)[1])*250./nm.shape(ps)[1]
        # Plot waterfall
        pylab.subplot(2,2,ifig*2+1)
        ps10 = nm.log10(ps)
        med = nm.median(ps10[~nm.isnan(ps10)])
        std = nm.std(ps10[~nm.isnan(ps10)])
        vmin = med - std
        vmax = med + std
        # pylab.imshow(ps10, vmin=vmin, vmax=vmax, extent=[0, freq[-1], 0, nm.shape(ps10)[0]])
        pylab.imshow(ps10, aspect='auto', vmin=vmin, vmax=vmax, extent=[0, freq[-1], 0, nm.shape(ps10)[0]])
        if len(time) >= 15:
            nticks = 10
        if len(time) < 15 and len(time) >= 5:
            nticks = 5
        else:
            nticks = 1
        pylab.yticks(nm.linspace(0,len(time),nticks), time[::len(time)/nticks], fontsize=6)
        pylab.xlabel('Frequency (MHz)')
        pylab.title(field)
        pylab.colorbar()
        # Plot median, average, min, max
        pylab.subplot(2,2,ifig*2+2)
        pylab.semilogy(freq, nm.min(ps, axis=0), 'b-', label='Min')
        pylab.semilogy(freq, nm.max(ps, axis=0), 'r-', label='Max')
        pylab.semilogy(freq, nm.mean(ps, axis=0), 'k--', label='Mean')
        pylab.semilogy(freq, nm.median(ps, axis=0), 'k-', label='Median')
        pylab.xlabel('Frequency (MHz)')
        pylab.ylabel('log10(amplitude)')
        pylab.legend(loc='upper right')
        pylab.title(field)

    pylab.subplots_adjust(hspace=0.3, wspace=0.3)
    pylab.suptitle(antname + ' : ' + str(tstamp))
    outfile = plot_dir + '/' + antname + '_' + tstamp_outfile + '.png'
    pylab.savefig(outfile)
        
# Plotting routines for LWA antennas                
elif antname == 'LWA':
    # Deal with time stamps
    t1 = nm.fromfile(d+'/time_sys_start.raw')
    t2 = nm.fromfile(d+'/time_sys_stop.raw')
    time = 0.5*(t1+t2)
    time = nm.asarray(ctime2timestamp(time, string=True))
    
    fields = ['pol00.scio', 'pol11.scio', 'pol22.scio', 'pol33.scio']
    pylab.figure(figsize=(15,15))
    ifig = 0
    for field in fields:
        ps = scio.read(d+'/'+field)
        freq = nm.arange(nm.shape(ps)[1])*125./nm.shape(ps)[1]
        # Plot waterfall
        ifig = ifig + 1
        pylab.subplot(4,2,ifig)
        ps10 = nm.log10(ps)
        med = nm.median(ps10[~nm.isnan(ps10)])
        std = nm.std(ps10[~nm.isnan(ps10)])
        vmin = med - std
        vmax = med + std
        pylab.imshow(ps10, aspect='auto', vmin=vmin, vmax=vmax, extent=[0, freq[-1], 0, nm.shape(ps10)[0]])
        if len(time) >= 15:
            nticks = 10
        if len(time) < 15 and len(time) >= 5:
            nticks = 5
        else:
            nticks = 1
        pylab.yticks(nm.linspace(0,len(time),nticks), time[::len(time)/nticks], fontsize=6)
        if ifig == 7:
            pylab.xlabel('Frequency (MHz)')
        pylab.title(field)
        pylab.colorbar()
        # Plot median, average, min, max
        ifig = ifig + 1
        pylab.subplot(4,2,ifig)
        pylab.semilogy(freq, nm.min(ps, axis=0), 'b-', label='Min')
        pylab.semilogy(freq, nm.max(ps, axis=0), 'r-', label='Max')
        pylab.semilogy(freq, nm.mean(ps, axis=0), 'k--', label='Mean')
        pylab.semilogy(freq, nm.median(ps, axis=0), 'k-', label='Median')
        if ifig == 8:
            pylab.xlabel('Frequency (MHz)')
        pylab.ylabel('log10(amplitude)')
        pylab.legend(loc='upper right')
        pylab.title(field)

    pylab.suptitle(antname + ' : ' + str(tstamp))
    outfile = plot_dir + '/' + antname + '_' + tstamp_outfile + '.png'
    pylab.savefig(outfile)

else:
    print 'Unrecognized antenna name, giving up'
    exit(0)
            
