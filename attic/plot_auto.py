#!/usr/bin/env /usr/bin/python

import os
import glob

def findNewestDir(directory,level):
        '''
	 find the newest or last chunk of dataset

	-directory: top level directory
	-level [1,2]: 1-first newest subdirectory, 2-second newest subdirectory
        ''' 
	os.chdir(directory)
	dirs = {}
	for dir in glob.glob('*'):
	   if os.path.isdir(dir):
	      dirs[dir] = os.path.getctime(dir)
	if 'log' in dirs.keys():
	   del dirs['log']
	lister = sorted(dirs.iteritems())
	if level==1:
	  return lister[-1][0]
	if level==2:
	  return lister[-2][0]

def plot(extpath):
    'Plotting data from ' + extpath
    for freq in ['70','100']:
        plot_path = extpath + '/data_' + freq + 'MHz'
        if os.path.exists(plot_path):
            os.chdir(plot_path)
            # getting the latest directory
            latest_dir = findNewestDir(plot_path,1)
            # getting the latest subdirectory or chunk of data
            latest_subdir = findNewestDir(plot_path + '/' + latest_dir,1)
	    #dir_files = os.listdir(latest_subdir)
	    if ((not os.path.exists(latest_subdir +'/pol0.scio')) and (not os.path.exists(latest_subdir +'/pol0.scio.bz2'))):
		print 'WARNING: NO SCIO FILES FOUND \n NO PLOTS IS PRODUCED FOR ' + freq + 'ANTENNA'
		check = raw_input('Do you want to plot the second latest chunk of data [y/n]?')
		if check.lower() == 'y':
		   latest_subdir = findNewestDir(plot_path + '/' + latest_dir,2)
		   print 'Plotting ' + freq + 'MHz antenna data'
                   cmd = 'python /home/scihi/daq_2017/quicklook/generate_spectra.py ' + plot_path + '/' + latest_dir +'/' + latest_subdir + ' --spectra'
                   os.system(cmd)
                else:
		   print 'Goodbye'
	    else:
                print 'Plotting ' + freq + 'MHz antenna data'
	        cmd = 'python /home/scihi/daq_2017/quicklook/generate_spectra.py ' + plot_path + '/' + latest_dir +'/' + latest_subdir + ' --spectra'
  	        os.system(cmd)


# plotting the last chunk of data set
if __name__=='__main__':
    extdrive = '/media/scihi/SCIHI_DISK1'
    try_laptop = False
    if os.path.exists(extdrive):
        print 'Detected external drive', extdrive
        extpath = extdrive+'/marion2017'
        ret = raw_input('Plot data from external drive path '+extpath+'? (y/n) ')
        if ret.lower() == 'y':
            dest = extpath
	    plot(dest)
        else:
            try_laptop = True
    else:
        print 'No external drive detected'
        try_laptop = True

    if try_laptop:
        extpath = '/data/marion2017'
	ret = raw_input('Plot data from laptop path '+extpath+'? (y/n) ')
	if ret.lower() == 'y':
	    dest = extpath
	    plot(dest)
	else:
	    print 'Goodbye...'
            exit(0)

     
# searching for data_70MHz folder, if the folder does not exists, it will skip to data_100MHz or switch_data
#try:
#        path = '/home/pi/data_70MHz'
#        rsync_path = '/data/marion2017/data_70MHz'
#        cmd = 'rsync -auv pi-70:%s/ %s'%(path,rsync_path)
#        os.system(cmd)
#except: 
#        print 'WARNING: %s not found'%path
#	pass
#try:
#        path = '/home/pi/data_100MHz'
#        rsync_path = '/data/marion2017/data_100MHz'
#        cmd = 'rsync -auv pi-100:%s/ %s'%(path,rsync_path)
#        os.system(cmd)
#except: 
#       print 'WARNING: %s not found'%path
#       pass

#try:
#        path = '/home/pi/switch_data'
#        rsync_path = '/data/marion2017/switch_data'
#        cmd = 'rsync -auv pi-ctrl:%s/ %s'%(path,rsync_path)
#        os.system(cmd)
#except: 
#        print 'WARNING: %s not found'%path
#	pass


# plotting the last chunk of data set

