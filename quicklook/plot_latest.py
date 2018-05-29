import numpy as nm
import pylab, datetime, time, subprocess, re, os
import scio

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

    # This is a grand unified script for plotting the latest chunk of
    # data from whatever pi(s) are connected.  The script does the
    # following:
    # - Loop over 70 MHz, 100 MHz, and single snap pis (pi-ctrl excluded)
    # - Check for live connection
    # - Find most recent data chunk subdirectory
    # - Rsync only that subdirectory to the laptop
    # - Run diagnostic plots on that subdirectory

    # Note that the switch state is ignored here, so this script is
    # most useful for interactive tests when the switch is set to a
    # particular state and you just want to plot all of the things.

    # Subdirectory number within the latest day directory.  If 0, then
    # copy the most recent subdirectory, if 1 then copy second most
    # recent subdirectory, etc.  Sometimes useful to set to >0 to
    # avoid cruft in the most recent subdirectory from connecting
    # laptop, etc.
    subdir_number = 0

    # We have more than one year now!
    year = '2018'

    # By default, copy small chunks of data to the laptop
    data_dir_local = '/data/marion'+year

    # Specify output directory for plots
    plot_dir = '/home/scihi/quicklook_plots'

    # If following is True, then execute eog system calls to show the
    # plots after they're created
    show_plot = True
    
    # Check which pi(s) are connected
    ip_front = '146.230.92.'
    ip_ends = ['186','187','189']
    antnames = ['100MHz', '70MHz', 'LWA']
    data_dir = {'186':'data_100MHz',
                '187':'data_70MHz',
                '189':'data_singlesnap'}
    # Loop over pis
    for ip_end, antname in zip(ip_ends, antnames):
        ip = ip_front + ip_end
        print 'Checking for connection to', ip
        ret = os.system('ping -c 1 -W 2 '+ip)
        if ret != 0:
            print 'Failed to detect connection to', ip
            continue
        print 'Found live connection to', ip
        # List files with newest first
        data_dir_pi = '/home/pi/'+data_dir[ip_end]
        out = subprocess.Popen(['ssh', 'pi@'+ip, 'ls', '-t', data_dir_pi],
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT)
        stdout, stderr = out.communicate()
        dirlist = stdout.strip().split('\n')
        # Find most recent single-day data (not log) directory --
        # search for first one in the list that's a number
        lastdir = None
        for d in dirlist:
            s = re.search(r'\d+', d)
            if s is not None:
                lastdir = d
                break
        if lastdir is None:
            print 'Failed to find most recent data in', data_dir_pi, ': giving up!'
            continue
        # Now look in the most recent day of data to find the most
        # recent subdirectory
        day_dir_pi = '/home/pi/'+data_dir[ip_end]+'/'+lastdir
        out = subprocess.Popen(['ssh', 'pi@'+ip, 'ls', '-t', day_dir_pi],
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT)
        stdout, stderr = out.communicate()
        dirlist = stdout.strip().split('\n')
        # Day directory contents really should only be numbered
        # chunks, so don't bother with regex here.  (If something is
        # wrong, we do actually want catastrophic failure at this
        # point in the script.)
        # lastsubdir = day_dir_pi+'/'+dirlist[subdir_number]
        lastsubdir = data_dir[ip_end]+'/'+lastdir+'/'+dirlist[subdir_number]

        # Copy most recent data subdirectory to the laptop.  Note that
        # -R option in rsync preserves relative path
        cmd = 'rsync -auvR --progress pi@'+ip+':' + lastsubdir +' '+data_dir_local
        print cmd
        os.system(cmd)

        # Plot up diagnostics: just look at autospectra for quicklook purposes
        # xxx: eventually add overflow detectors, and any other important things
	lastsubdir_stripped = lastsubdir.split('/')[-1]
        d = data_dir_local + '/' + data_dir[ip_end] + '/' + lastdir + '/' + lastsubdir_stripped
        tstamp = ctime2timestamp(int(lastsubdir_stripped))
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

            pylab.suptitle(antname + ' : ' + str(tstamp))
            outfile = plot_dir+ '/' + antname + '_' + tstamp_outfile + '.png'
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

        # Show off the plot to the human
        print 'Wrote', outfile
        if show_plot:
            cmd = 'eog '+outfile+' &'
            os.system(cmd)

    # End loop over pis
