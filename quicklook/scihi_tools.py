import numpy as nm
import os, pylab, scio, datetime

# e-scratchpaper:
# sys_clk: actual register is int32, do diff, add 2^32 to every negative entry
# to read bzipped files: import bz2, do raw read, convert with numpy.fromstring

#============================================================
def timestamp2ctime(date_strings, time_format='%Y%m%d_%H%M%S'):
    """Given a string time stamp (or list of time stamps) in human-frendly
    format, with default being YYYYMMSS_HHMMSS, convert to datetime
    object and calculate ctime.

    - date_strings = time stamp(s) in desired text format
    - time_format = formatting string for datetime

    Returns the time stamps (or list of time stamps) in ctime.
    """

    t0 = datetime.datetime(1970, 1, 1)
    
    if isinstance(date_strings, basestring):
        return (datetime.datetime.strptime(date_strings, time_format) - t0).total_seconds()
    else:
        return [ (datetime.datetime.strptime(d, time_format) - t0).total_seconds() for d in date_strings ]

#============================================================
def time2dirs(time_start, time_stop, dir_parent, fraglen=5):
    """Given a start and stop ctime, retrieve list of corresponding
    subdirectories.  This function assumes that the parent directory
    has two levels of subdirectories: <dir_parent>/<5-digit
    coarse time fragment>/<10-digit fine time stamp>.

    - time_start, time_stop = start/stop times in ctime
    - dir_parent = parent directory, e.g. /path/to/data_100MHz
    - fraglen = # digits in coarse time fragments

    Returns list of subdirectories in specified time range.
    """

    times_coarse = os.listdir(dir_parent)
    times_coarse.sort()
    dir_list = []
    for time_coarse in times_coarse:
        if int(time_coarse) < int(str(time_start)[:fraglen]) or int(time_coarse) > int(str(time_stop)[:fraglen]):
            continue
        times_fine = os.listdir(dir_parent+'/'+time_coarse)
        times_fine.sort()
        times_fine_num = nm.asarray(times_fine, dtype='float')
        inds = nm.where(times_fine_num - time_start < 0)[0]
        if len(inds) == 0:
            i1 = 0
        else:
            i1 = inds[-1]
        inds = nm.where(times_fine_num - time_stop > 0)[0]
        if len(inds) == 0:
            i2 = len(times_fine_num)
        else:
            i2 = inds[0]
        for time_fine in times_fine[i1:i2+1]:
            dir_list.append(dir_parent+'/'+time_coarse+'/'+str(time_fine))
    dir_list.sort()
    return dir_list

#============================================================
def read_scihi_data(time_start, time_stop, dir_top,
                   subdir_100='data_100MHz', subdir_70='data_70MHz',
                   subdir_switch='switch_data/data/switch',
                   subdir_temp='switch_data/data/temperatures',
                   read_100=True, read_70=True, read_switch=True, read_temp=True,
                   trim=True, verbose=False):
    """Read SCI-HI data within a specified time range.

    - time_start, time_stop = start/stop times in ctime
    - dir_top = top level data directory
    - subdir_100 = 100 MHz subdirectory within the top level directory
    - subdir_70 = 70 MHz subdirectory within the top level directory
    - subdir_switch = switch state subdirectory within the top level directory
    - subdir_temp = temperature data subdirectory within the top level directory
    - read_100, read_70, read_switch, read_temp = Booleans to select which data to (not) read
    - trim = trim data exactly to time range, or read everything in matching subdirectories if false
    - verboase = speak to the human?

    Return dictionaries with all the datas!!!
    """

    scihi_dat = {}
    scio_fields = ['pol0.scio', 'pol1.scio', 'cross_real.scio', 'cross_imag.scio']
    raw_fields = [('acc_cnt1.raw','int32'), ('acc_cnt2.raw','int32'), 
                  ('fft_of_cnt.raw','int32'), ('fft_shift.raw','int64'), 
                  ('fpga_temp.raw','float'), ('pi_temp.raw','int32'), 
                  ('sync_cnt1.raw','int32'), ('sync_cnt2.raw','int32'),
                  ('sys_clk1.raw','int32'), ('sys_clk2.raw','int32'),
                  ('time_start.raw','float'), ('time_stop.raw','float')]

    # Start by reading primary data products for specified antennas
    keys = []
    subdirs = {}
    if read_100:
        key = '100'
        keys.append(key)
        subdirs[key] = subdir_100
    if read_70:
        key = '70'
        keys.append(key)
        subdirs[key] = subdir_70

    for key in keys:
        scihi_dat[key] = {}
        dirs = time2dirs(time_start, time_stop, dir_top+'/'+subdirs[key])
        for d in dirs:

            # Keep track of field lengths just in case there's a mismatch somewhere
            field_lengths = []
            
            # Read scio files, and decompress only if it hasn't been done already
            # Note: might want to add option later to read .bz2 files directly if we're low on disk space
            for field in scio_fields:
                if not os.path.exists(d+'/'+field):
                    if verbose:
                        print 'read_scihi_data: decompressing', d+'/'+field
	                os.system('bzip2 -dk ' + d + '/' + field + '.bz2')
	    if verbose:
                print 'read_scihi_data: reading scio files in', d
            for field in scio_fields:
                dat = scio.read(d + '/' + field)
                field_lengths.append(len(dat))
                if d is dirs[0]:
                    scihi_dat[key][field.split('.')[0]] = dat
                else:
                    scihi_dat[key][field.split('.')[0]] = nm.append(scihi_dat[key][field.split('.')[0]], dat, axis=0)
            # Read raw files
	    if verbose:
                print 'read_scihi_data: reading raw files in', d
            for field in raw_fields:
                dat = nm.fromfile(d+'/'+field[0], dtype=field[1])
                field_lengths.append(len(dat))
                if d is dirs[0]:
                    scihi_dat[key][field[0].split('.')[0]] = dat
                else:
                    scihi_dat[key][field[0].split('.')[0]] = nm.append(scihi_dat[key][field[0].split('.')[0]], dat)
            # Check consistency of field lengths
            if len(nm.where(nm.diff(field_lengths) != 0)[0]) > 0:
                print 'read_scihi_data: warning, found inconsistent field lengths in', d, ' -- OMITTING THIS DATA'
                print 'read_scihi_data: field lengths are', field_lengths
                # Remove the data if it's borked
                subkeys = [field.split('.')[0] for field in scio_fields] + \
                          [field[0].split('.')[0] for field in raw_fields]
                for field_length, subkey in zip(field_lengths, subkeys):
                    scihi_dat[key][subkey] = scihi_dat[key][subkey][:-field_length]
                    
        # Trim to desired time range
        if trim:
            t0 = scihi_dat[key]['time_start']  # Start of FPGA read
            t1 = scihi_dat[key]['time_stop']   # End of FPGA read
            inds = nm.where( (t0 >= time_start) & (t1 <= time_stop) )[0]
            if len(inds) == 0:
                print 'read_scihi_data: warning, found no data in requested time range'
            subkeys = scihi_dat[key].keys()
            for subkey in subkeys:
                scihi_dat[key][subkey] = scihi_dat[key][subkey][inds]
                
    # Now move on to auxiliary data
    if read_switch:
        if verbose:
            print 'read_scihi_data: reading switch data'
        key = 'switch'
        scihi_dat[key] = {}
        dirs = time2dirs(time_start, time_stop, dir_top+'/'+subdir_switch)
        scio_fields = ['antenna.scio','res100.scio','res50.scio','short.scio']
        for d in dirs:
            for field in scio_fields:
                # Switch fields are slow, so sometimes the files are empty.  Check this before reading.
                st = os.stat(d+'/'+field)
                # If file is empty, just move along
                if st.st_size == 0:
                    continue
                dat = scio.read(d+'/'+field)
                if d is dirs[0]:
                    scihi_dat[key][field.split('.')[0]] = dat
                else:
                    scihi_dat[key][field.split('.')[0]] = nm.append(scihi_dat[key][field.split('.')[0]], dat, axis=0)
        # Trim to desired time range
        subkeys = scihi_dat[key].keys()
        for subkey in subkeys:
            inds = nm.where( (scihi_dat[key][subkey][:,1] >= time_start) &
                             (scihi_dat[key][subkey][:,1] <= time_stop) )[0]
            scihi_dat[key][subkey] = scihi_dat[key][subkey][inds]

    if read_temp:
        if verbose:
            print 'read_scihi_data: reading temperature data'
        key = 'temp'
        scihi_dat[key] = {}
        dirs = time2dirs(time_start, time_stop, dir_top+'/'+subdir_temp)
        scio_fields = ['pi_temp.scio','snapbox_temp.scio']
        for d in dirs:
            for field in scio_fields:
                dat = scio.read(d+'/'+field)
                if d is dirs[0]:
                    scihi_dat[key][field.split('.')[0]] = dat
                else:
                    scihi_dat[key][field.split('.')[0]] = nm.append(scihi_dat[key][field.split('.')[0]], dat, axis=0)
        # Trim to desired time range
        # Write this code later, after we have data products that are functioning
        if trim:
            print 'Warning, trimming not implemented for aux temperatures yet'

    return scihi_dat

#============================================================
def add_switch_flag(scihi_dat, antennas=['70', '100']):
    """Convert switch aux data into fast sampled flag fields for specified antenna(s).

    - scihi_dat: SCI-HI data dictionary with appropriate antenna and switch entries
    - antennas: list of antennas for flag generation

    Creates fast sampled bit field flag with the following values:
    bit 0 = antenna
    bit 1 = 100 ohm resistor
    bit 2 = short
    bit 3 = 50 ohm resistor

    Flag is added to the SCI-HI data dictionary as 'switch_flag'.
    """

    keys = scihi_dat['switch'].keys()
    bvals = {'antenna':0,
             'res100':1,
             'short':2,
             'res50':3}
    
    for antenna in antennas:
        flag = nm.zeros_like(scihi_dat[antenna]['time_start'], dtype='int')
        if len(scihi_dat[antenna]['time_start']) == 0:
            print 'add_switch_flag: error, no timestamp data from antenna', antenna
            continue
        t0 = scihi_dat[antenna]['time_start'][0]
        t1 = scihi_dat[antenna]['time_stop'][-1]
        for key in keys:
            times = scihi_dat['switch'][key]
            # Artificially add endpoints here
            if len(times) > 0 and times[0,0] == 0.0:
                times = nm.append([[1.0, t0]], times, axis=0)
            if len(times) > 0 and times[-1,0] == 1.0:
                times = nm.append(times, [[0.0, t1]], axis=0)
            # After dealing with endpoints, we should always have
            # something that turns on at the very beginning and turns
            # off at the very end
            for a,b in zip(times[:-1], times[1:]):
                inds = nm.where( (scihi_dat[antenna]['time_start'] >= a[1]) &
                                 (scihi_dat[antenna]['time_stop'] <= b[1]) )[0]
                # If source was turned on/off at the beginning of the time
                # chunk, set bit accordingly
                if a[0] == 1.0:
                    flag[inds] = ( flag[inds] | nm.array([2**bvals[key]]*len(inds), dtype='int') )
                else:
                    flag[inds] = ( flag[inds] & ~nm.array([2**bvals[key]]*len(inds), dtype='int') )

    scihi_dat[antenna]['switch_flag'] = flag

    return

#============================================================
if __name__ == '__main__':

    # Start by specifying the time stamps you're interested in (or you can use raw ctimes if you want)
    # time_start = '20170422_180000'
    # time_stop = '20170422_220000'
    time_start = '20170421_170000'
    time_stop = '20170422_070000'

    # If you used human-friendly time stamps, convert to ctime
    t0 = timestamp2ctime(time_start)
    t1 = timestamp2ctime(time_stop)

    # Read the datas!  You can specify which of the Mikes and/or aux
    # data you want to snarf into the data dictionary
    # scihi_dat = read_scihi_data(t0, t1, dir_top='marion2017', read_100=True, read_70=False, 
    #                             read_switch=True, read_temp=True, verbose=True)
    scihi_dat = read_scihi_data(t0, t1, dir_top='marion2017', read_100=True, read_70=False, 
                                read_switch=True, read_temp=False, verbose=True)

    # Add flag field to data structure
    add_switch_flag(scihi_dat, antennas=['100'])
    # Do the following line to add flags for both antennas
    # add_switch_flag(scihi_dat, antennas=['100', '70'])
