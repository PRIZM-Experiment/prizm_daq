#!/usr/bin/env /usr/bin/python

# A dummy script to automatically execute the correct rsync command
# for copying SCI-HI data.  Looks for existence of external backup
# drive by default, but also gives an option to copy to the laptop.
# Checks each of the three Pi IP addresses for connection.

import os

if __name__ == '__main__':

    # Start by looking for existence of external drive
    try_laptop = False
    extdrive = '/media/scihi/SCIHI_DISK1'
    if os.path.exists(extdrive):
        print 'Detected external drive', extdrive
        extpath = extdrive+'/marion2017'
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
        extpath = '/data/marion2017'
        ret = raw_input('Copy to laptop path '+extpath+'? (y/n) ')
        if ret.lower() == 'y':
            dest = extpath
        else:
            print 'I have failed to find a path that makes you happy.'
            dest = raw_input('Enter the data destination path that you want. [e/E to escape] ')
            if dest.lower() == 'e':
                print 'Goodbye...'
                exit(0)

    # Now try to autodetect which Pi is connected
    ip_front = '146.230.92.'
    ip_ends = ['186','187','188']
    data_dir = {'186':'data_100MHz',
                '187':'data_70MHz',
                '188':'switch_data'}
    for ip_end in ip_ends:
        ip = ip_front + ip_end
        print 'Checking for connection to', ip
        ret = os.system('ping -c 1 -W 2 '+ip)
        if ret == 0:
            print 'Found live connection to', ip, ': initializing data transfer'	    
            cmd = 'rsync -auv --ignore-existing --progress pi@'+ip+':' + data_dir[ip_end] +' '+dest
            print cmd
            os.system(cmd)
        else:
            print 'Failed to detect connection to', ip
