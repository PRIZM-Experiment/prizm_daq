#!/usr/bin/env /usr/bin/python

import os
import subprocess
import argparse
import datetime
import logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", type=str, help="Path to supervisord configuration file")
    parser.add_argument("log_dir", type=str, help = "Directory to output log folders")
    args=parser.parse_args()

    t_start = str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    if not os.path.exists(args.log_dir+"/supervisord_logs/"+t_start):
        print(args.log_dir+"/supervisord_logs/"+t_start)
        os.makedirs(args.log_dir+"/supervisord_logs/"+t_start)

    logger = logging.getLogger()
    logger.setLevel(20)
    f_handler = logging.FileHandler(args.log_dir+"/supervisord_logs/"+t_start+"/run_daq_supervised.log")
    f_format = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
    f_handler.setFormatter(f_format)
    f_handler.setLevel(20)
    logger.addHandler(f_handler)

    logging.info("Starting run_daq_supervised.py script")

    logging.info("Checking if supervisord is running already.")
    txt = subprocess.Popen(['ps','-C','supervisord','-o','pid='], stdout=subprocess.PIPE).communicate()[0]
    txt = txt.strip()
    if len(txt) > 0:
        logging.critical('Looks like supervisord is already running under process ID: '+str(txt))
        logging.critical('Quitting here and not starting DAQ.')
        exit(0)
    else:
        logging.info("Looks like no DAQ process is running, trying to start one now.")
        cmd = 'supervisord -c '+args.config_file+' -d '+args.log_dir+"/supervisord_logs/"+t_start+' -l '+args.log_dir+"/supervisord_logs/"+t_start+"/supervisord.log -j "+args.log_dir+"/supervisord_logs/"+t_start+"/supervisord.pid"
        logging.info('Running cmd: '+cmd)
        os.system(cmd)
        logging.info('Started supervised DAQ process')
        exit(0)
