#!/usr/bin/env /usr/bin/python

# A dummy script to automatically execute the correct rsync command
# for copying PRIZM data.  Looks for existence of external backup
# drive by default, but also gives an option to copy to the laptop.
# Checks each of the three Pi IP addresses for connection.

import os

if __name__ == '__main__':

    # We have more than one year now!
    year = '2018'
    #year = '2017'
    
    # Start by looking for existence of external drive
    try_laptop = False
    extdrive = '/media/scihi/SCIHI_DISK1'
    if os.path.exists(extdrive):
        print 'Detected external drive', extdrive
        extpath = extdrive+'/marion'+year
        ret = raw_input('Copy to external drive path '+extpath+'? (y/n) ')
        if ret.lower() == 'y':
            dest = extpath
        else:
            try_laptop = True
    else:
        print 'No external drive detected'
        try_laptop = True
    # See if the human wants to copy to the laptop instead
    if try_laptop:
        extpath = '/data/marion'+year
        ret = raw_input('Copy to laptop path '+extpath+'? (y/n) ')
        if ret.lower() == 'y':
            dest = extpath
        else:
            print 'I have failed to find a path that makes you happy.'
            dest = raw_input('Enter the data destination path that you want. [e/E to escape] ')
            if dest.lower() == 'e':
                print 'Goodbye...'
                exit(0)

    # Now try to autodetect which Pi is connected.  This will work
    # seamlessly with our new network switch too.

    # Start by asking if the human wants to copy everything or if the
    # human wants to interactively specify which Pis to copy from.
    interactive = False
    ret = raw_input('Copy data from all three RPis (if n, then code will ask interactively)? (y/n)')
    if ret.lower() == 'n':
        interactive = True
        print 'Ok, I will ask you to confirm the data copy from each RPi individually.'
    ip_front = '146.230.92.'
    ip_ends = ['186','187','188','189']
    data_dir = {'186':'data_100MHz',
                '187':'data_70MHz',
                '188':'switch_data',
		'189':'data_singlesnap'}
    for ip_end in ip_ends:
        do_copy = True
        ip = ip_front + ip_end
        if interactive:
            ret = raw_input('Do you want data from '+ip+'/'+data_dir[ip_end]+'? (y/n)')
            if ret.lower() == 'n':
                do_copy = False
                print 'Your wish is my command -- skipping data copy for '+ip
        if do_copy:
            print 'Checking for connection to', ip
            ret = os.system('ping -c 1 -W 2 '+ip)
            if ret == 0:
                print 'Found live connection to', ip, ': initializing data transfer'	    
                cmd = 'rsync -auv --ignore-existing --progress pi@'+ip+':' + data_dir[ip_end] +' '+dest
                print cmd
                os.system(cmd)
            else:
                print 'Failed to detect connection to', ip
