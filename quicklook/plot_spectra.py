import glob
import os,sys

PATH = '/home/scihi/daq_2017/data'
dirnames = glob.glob(PATH + '/*')
args = ''
for dname in dirnames:
        args += '%s/* '%dname
command = 'python generate_spectra.py %s --spectra --mean --acc --temp'%args
os.system(command)
