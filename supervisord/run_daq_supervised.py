#!/usr/bin/env /usr/bin/python

import os
import subprocess
import argparse

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("config_file", type=str, help="Path to supervisord configuration file")
	args=parser.parse_args()
	# Before doing anything, check if supervisord is running already.  If
	# yes, then cry for help and don't do anything.
	txt = subprocess.Popen(['ps','-C','supervisord','-o','pid='], stdout=subprocess.PIPE).communicate()[0]
	txt = txt.strip()
	if len(txt) > 0:
    		print 'Looks like supervisord is already running under process ID',txt
    		print 'Quitting here and not starting DAQ.'
    		exit(0)

	cmd = 'supervisord -c '+args.config_file
        print 'Running cmd: '+cmd
	os.system(cmd)
	print 'Started supervised DAQ process'
	exit(0)
