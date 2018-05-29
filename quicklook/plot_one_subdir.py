import numpy as nm
import scio, pylab, datetime, sys, os

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
if __name__ == '__main__':

    args = sys.argv[1:]
    if len(args) != 1:
        print 'Usage: python plot_one_subdir.py <directory name>'
        print 'Directory should contain scio and raw files'
        exit(0)
    d = args[0]

    # Output directory for plots
    plot_dir = '/home/scihi/quicklook_plots'
    # Some convenient directory and antenna names
    antnames = {'data_70MHz':'70MHz',
                'data_100MHz':'100MHz',
                'data_singlesnap':'LWA'}
    
    # Try to guess antenna name from the path
    antname = None
    fields = d.split('/')
    for field in fields:
        for key in antnames.keys():
            if field == key:
                antname = antnames[key]
                break
    if antname is None:
        print 'Failed to autodetect antenna name from path'
        antname = raw_input('Please manually enter an antenna name for the file: ')
        print antname
    lastsubdir = fields[-1]
    # If there's a trailing slash, strip it
    for field in fields[-1::-1]:
        if field != '':
            lastsubdir = field
            break
    print lastsubdir

    # Deal with time stamps
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
            
    print 'Wrote', outfile
    cmd = 'eog '+outfile+' &'
    os.system(cmd)
