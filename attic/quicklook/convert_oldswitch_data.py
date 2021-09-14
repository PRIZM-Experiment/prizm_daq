import scihi_tools_20170426 as st
import numpy
import os,sys
import glob
import scio

def move_switch_data():
	"""
	Moving chunk of switch data stored in switch previously to switch_data
	"""
	switch_dirs = glob.glob('/data/marion2017/switch_data/switch/*')
	for subdir in switch_dirs:
	   future_dir = '/data/marion2017/switch_data/' + subdir.split('/')[-1]
	   os.system('mv %s %s'%(subdir,future_dir))
	

def move_temperatre_data():
	"""
	Moving chunk of temperaure data stored in switch previously to switch_data and change scio to raw files
	"""
	temp_dirs = glob.glob('/data/marion2017/switch_data/temperatures/*')
	for subdir in temp_dirs: 
	   fields = glob.glob(subdir + '/*')
           for f in fields:
	       try:
	       	  pi_data = scio.read(f + '/pi_temp.scio')
	          snapbox_data = scio.read(f + '/snapbox_temp.scio')
	          f_pi_temp = open(f + '/pi_temp.raw','w')
	          f_pi_time = open(f + '/pi_time.raw','w')
                  f_snapbox_temp = open(f + '/snapbox_temp.raw','w')
                  f_snapbox_time = open(f + '/snapbox_time.raw','w')

	          pi_temp = numpy.int32(pi_data[:,1])
	          pi_temp.tofile(f_pi_time)
	          pi_data[:,1].tofile(f_pi_temp)
	          snapbox_data[:,0].tofile(f_snapbox_time)
	          snapbox_data[:,1].tofile(f_snapbox_temp)

	          f_pi_temp.flush()
	          f_pi_time.flush()
	          f_snapbox_time.flush()
	          f_snapbox_time.flush()
	       except IOError:
        	  print 'tempearatures files not found'
		  continue

	       future_dir = '/data/marion2017/switch_data/' +'/' + f.split('/')[-2] + '/' + f.split('/')[-1]
               os.system('mv %s/*.raw %s/'%(f,future_dir))
	       os.system('rm %s/*.scio'%future_dir)
	   

if '__name__==__main__':
	move_switch_data()
	move_temperatre_data()

