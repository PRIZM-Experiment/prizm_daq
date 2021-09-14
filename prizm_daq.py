#!/usr/bin/python
import time
import datetime
import struct
import sys
import logging
import os
import subprocess
import serial
import casperfpga
import smbus
import ds3231
import mcp23017
import thread
import yaml
import scio
import iadc
import re
import numpy as nm
import RPi.GPIO as GPIO
from argparse import ArgumentParser
import lbtools_l

#=======================================================================
def initialize(parameters):
    """Connect to SNAP board, configure settings"""
    # Connect to the SNAP board configure spectrometer settings
    logging.info('Connecting to server %s:%d'%(parameters['snap-board']['ip'], parameters['snap-board']['port']))
    fpga = casperfpga.CasperFpga(host=parameters['snap-board']['ip'], port=parameters['snap-board']['port'])
    time.sleep(1)  # important for live connection reporting
    if fpga.is_connected():
        logging.info('Connected!')
    else:
        logging.error('ERROR connecting to %s .' %(snap_ip))
        exit(1)
    logging.info('Programming SNAP Board')
    fpga.upload_to_ram_and_program(parameters['snap-board']['firmware'])
    # Configure iADC
    adc=iadc.Iadc(fpga)
    adc.set_dual_input()
    logging.info('Board clock is %f'%(fpga.estimate_fpga_clock())) #Board clock should be 1/4 of the sampling clock (board clock=125 MHz)
    # Deal with FFT shift, accumulation length, and sync trigger
    logging.info('Setting fft shift, accumulation length...')
    # fpga.write_int('fft_shift', 0x00000000)  # verified fft_of = 1 all the time
    # fpga.write_int('fft_shift', 0xF0F0F0F0)  # fft_of = 1 ~80% of the time
    # fpga.write_int('fft_shift', 0xFFF0F0FF)  # fft_of = 0 100% of the time
    # fpga.write_int('fft_shift', 0xF0F0F0FF)  # fft_of = 0 100% of the time
    # fpga.write_int('fft_shift', 0xF0F0F0F8)  # fft_of = 0 90% of the time
    # fpga.write_int('fft_shift', 0x80808088)  # fft_of = 1 100% of the time
    # fpga.write_int('fft_shift', 0xC0C0C0C8)  # fft_of = 1 100% of the time
    # fpga.write_int('fft_shift', 0xE0E0E0E8)  # fft_of = 1 100% of the time
    # fpga.write_int('fft_shift', 0xF0F0F0FF)  # fft_of = 0 90% of the time
    # As of 4 May 2017, above value is dead to us.
    # fpga.write_int('fft_shift', 0xFFFFFFFF)  # fft_of = 0 90% of the time
    fpga.write_int('fft_shift', parameters['snap-board']['fft-shift'])
    fpga.write_int('acc_len', parameters['snap-board']['accumulation-length'])
    logging.info('Done configuring')
    time.sleep(2)
    return fpga
#=======================================================================
def get_adc_stats(fpga):
    adc_stats={}
    for i in [0, 1]:
        data = fpga.snapshots['snapshot_ADC%d'%(i)].read(man_valid=True, man_trig=True)['data']['data']
        data = nm.asarray(data)
        d1 = nm.bitwise_and(data, 0xff000000)
        d2 = nm.bitwise_and(data, 0x00ff0000)
        d3 = nm.bitwise_and(data, 0x0000ff00)
        d4 = nm.bitwise_and(data, 0x000000ff)
        data=nm.array([d1, d2, d3, d4]).flatten()
        data[data>2**7]=data[data>2**7]-2**8
        mean=nm.mean(data)
        rms=nm.sqrt(nm.mean(data**2))
        bits_used=nm.log2(rms)
        adc_stats['ADC%d'%(i)]={'raw':data, 'mean':mean, 'rms':rms, 'bits_used':bits_used}
    return adc_stats
#=======================================================================
def get_fpga_temp(fpga):
    # returns fpga core temperature
    TEMP_OFFSET = 0x0
    reg = 'xadc'
    x = fpga.read_int(reg,TEMP_OFFSET)
    return (x >> 4) * 503.975 / 4096. - 273.15
#=======================================================================
def read_data(fpga, parameters):
    nn=parameters['snap-board']['fft-channels']/2;
    #assert(nn==1024) #if we fail this, we need to update a whole bunch of sizes below...
    bram_fmt_auto = '>%dQ'%(nn)
    bram_fmt_cross = '>%dq'%(nn)
    ep0 = nm.array(struct.unpack(bram_fmt_auto, fpga.read('even_pol0',nn*8,0)))
    op0 = nm.array(struct.unpack(bram_fmt_auto, fpga.read('odd_pol0',nn*8,0)))
    ep1 = nm.array(struct.unpack(bram_fmt_auto, fpga.read('even_pol1',nn*8,0)))
    op1 = nm.array(struct.unpack(bram_fmt_auto, fpga.read('odd_pol1',nn*8,0)))
    # Forcing type casting to int64 because numpy tries to be
    # "smart" about casting to int32 if there are no explicit long
    # ints.
    even_real = nm.array(struct.unpack(bram_fmt_cross, fpga.read('even_real',nn*8,0)),dtype='int64')
    even_imaginary = nm.array(struct.unpack(bram_fmt_cross, fpga.read('even_imaginary',nn*8,0)),dtype='int64')
    odd_real = nm.array(struct.unpack(bram_fmt_cross, fpga.read('odd_real',nn*8,0)),dtype='int64')
    odd_imaginary = nm.array(struct.unpack(bram_fmt_cross, fpga.read('odd_imaginary',nn*8,0)),dtype='int64')
    pol0=nm.ravel(nm.column_stack((ep0,op0)))
    pol1=nm.ravel(nm.column_stack((ep1,op1)))
    real_cross=nm.ravel(nm.column_stack((even_real,odd_real)))
    im_cross=nm.ravel(nm.column_stack((even_imaginary,odd_imaginary)))
    return pol0, pol1, real_cross, im_cross
#=======================================================================
def acquire_data(fpga, parameters, wait_for_new=True):
    # nn=parameters["fft-channels"]/2;
    # assert(nn==1024) #if we fail this, we need to update a whole bunch of sizes below...
    while True:
        tstart = time.time()
        outsubdir = parameters['directories']['top']+'/'+str(tstart)[:5]+'/'+str(nm.int64(tstart))
        if not os.path.isdir(outsubdir):
            os.makedirs(outsubdir)
        logging.info('Writing pol data to %s' %(outsubdir))

        hk_p = {}
        for hk_f in ['time_sys_start.raw', 'time_sys_stop.raw', 'time_gps_start.raw', 'time_gps_stop.raw',
                     'time_rtc_start.raw', 'time_rtc_stop.raw', 'fft_shift.raw', 'fft_of_cnt.raw',
                     'acc_cnt1.raw', 'acc_cnt2.raw', 'sys_clk1.raw', 'sys_clk2.raw', 'sync_cnt1.raw', 'sync_cnt2.raw']:
            hk_p[hk_f[:-4]] = open(outsubdir+'/'+hk_f,'w')

        scio_p = {}
        for scio_f in ['pol0.scio', 'pol1.scio', 'cross_real.scio', 'cross_imag.scio']:
            scio_p[scio_f[:-5]] = scio.scio(outsubdir+'/'+scio_f,
                                            diff=parameters['scio-files']['diff'],
                                            compress=parameters['scio-files']['compress'])

        while time.time()-tstart < parameters['scio-files']['file-time']:
            if wait_for_new:
                acc_cnt_old = fpga.read_int('acc_cnt')
                while True:
                    acc_cnt_new = fpga.read_int('acc_cnt')
                    # Ryan's paranoia: avoid possible reinitialization
                    # crap from first spectrum accumulation
                    if acc_cnt_new > acc_cnt_old:
                        break
            #time.sleep(0.1)
            # Time stamp at beginning of read commands.
            # Reading takes a long time (and there are
            # sometimes timeouts), so keep track of time
            # stamps for both start and end of reads.
            
            t1_sys = time.time()
            try:
                t1_gps = lbtools_l.lb_read()[0]
            except:
                logging.error("Failed to read time from gps")
                t1_gps = 0
            t1_rtc = rtc.timestamp()
            fft_shift = fpga.read_uint('fft_shift')
            fft_of_cnt = fpga.read_int('fft_of')  #this used to be fft_of_cnt
            sys_clk1 = fpga.read_int('sys_clkcounter')
            sync_cnt1 = fpga.read_int('sync_cnt')

            pol0, pol1, cross_real, cross_imag = read_data(fpga, parameters)

            acc_cnt_end = fpga.read_int('acc_cnt')
            t2_sys = time.time()
            try:
                t2_gps = lbtools_l.lb_read()[0]
            except:
                logging.error("Failed to read time from gps")
                t2_gps = 0
            t2_rtc = rtc.timestamp()
            sys_clk2 = fpga.read_int('sys_clkcounter') 
            sync_cnt2 = fpga.read_int('sync_cnt')
            logging.debug('Elapsed system time is %f'%(t2_sys-t1_sys))
            if acc_cnt_new != acc_cnt_end:
                logging.warning('Accumulation changed during data read')
            scio_p['pol0'].append(pol0)
            scio_p['pol1'].append(pol1)
            scio_p['cross_real'].append(cross_real)
            scio_p['cross_imag'].append(cross_imag)

            nm.array(t1_sys).tofile(hk_p["time_sys_start"])
	    nm.array(t2_sys).tofile(hk_p["time_sys_stop"])
            nm.array(t1_gps).tofile(hk_p["time_gps_start"])
            nm.array(t2_gps).tofile(hk_p["time_gps_stop"])
            nm.array(t1_rtc).tofile(hk_p["time_rtc_start"])
            nm.array(t2_rtc).tofile(hk_p["time_rtc_stop"])
            nm.array(fft_shift).tofile(hk_p["fft_shift"])
            nm.array(fft_of_cnt).tofile(hk_p["fft_of_cnt"])
            nm.array(sys_clk1).tofile(hk_p["sys_clk1"])
            nm.array(sys_clk2).tofile(hk_p["sys_clk2"])
            nm.array(sync_cnt1).tofile(hk_p["sync_cnt1"])
            nm.array(sync_cnt2).tofile(hk_p["sync_cnt2"])
            nm.array(acc_cnt_end).tofile(hk_p["acc_cnt2"])
            nm.array(acc_cnt_new).tofile(hk_p["acc_cnt1"])

            for hk_f in hk_p.keys():
                hk_p[hk_f].flush()
    return None
#=======================================================================
def run_switch(parameters, start_time=None):

    """Run the switch.  Cycle between sources by turning on appropriate
    Raspberry Pi GPIO pins for user-specified lengths of time.
    - parameters : options from parser
    - start_time : optional starting time stamp for the log file
    """

    # Open log file
    if start_time is None:
        start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    # Setup MCP23017 GPIO's as outputs
    logging.info("Configuring Switch Control Circuit")
    gpios=mcp23017.MCP23017(i2c_bus, 0x20)
    for switch in parameters['switch-control']['switches'].keys():
        for gpio in sorted(parameters['switch-control']['switches'][switch]['gpios'].keys()):
            port = parameters['switch-control']['switches'][switch]['gpios'][gpio][0]
            pin = parameters['switch-control']['switches'][switch]['gpios'][gpio][1:]
            logging.info('Setting port %s, pin %s to output'%(port, pin))
            gpios.set_gpio_direction(port, pin, False)
    for aux_gpio in parameters['switch-control']['aux-gpios'].keys():
        port = parameters['switch-control']['aux-gpios'][aux_gpio][0]
        pin = parameters['switch-control']['aux-gpios'][aux_gpio][1:]
        logging.info('Setting port %s, pin %s to output'%(port, pin))
        gpios.set_gpio_direction(port, pin, False)

    seq_list = parameters['switch-control']['sequence']

    while True:
        tstart = time.time()
        tfrag=repr(tstart)[:5]
        #starttime = datetime.datetime.utcnow()#.strftime('%Y%m%d_%H%M%S')
        outsubdir = parameters['directories']['top']+'/'+parameters['directories']['switch']+'/'+tfrag+'/'+str(nm.int64(tstart))
        if not os.path.isdir(outsubdir):
            os.makedirs(outsubdir)
        
        pos_scio_files = {}
        for pos in parameters['switch-control']['sequence']:
            pos_scio_files[pos] = scio.scio(outsubdir+'/%s.scio'%(pos),
                                            compress=parameters['scio-files']['compress'])
            
        while time.time()-tstart < parameters['scio-files']['file-time']:
            seq = seq_list.pop(0)
            which_switch = parameters['switch-control'][seq]['switch']
            which_pos = str(parameters['switch-control'][seq]['position'])
            ontime = parameters['switch-control'][seq]['ontime']
            port = parameters['switch-control']['switches'][which_switch]['gpios'][which_pos][0]
            pin = parameters['switch-control']['switches'][which_switch]['gpios'][which_pos][1:]
            starttime = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            if parameters['switch-control']['switches'][which_switch]['gpios']['r'] != 'None':
                logging.info('Reset On')
                reset_port = parameters['switch-control']['switches'][which_switch]['gpios']['r'][0]
                reset_pin = parameters['switch-control']['switches'][which_switch]['gpios']['r'][1:]
                gpios.set_output_latch(reset_port, reset_pin, True)
                time.sleep(0.30)
                gpios.set_output_latch(reset_port, reset_pin, False)
                time.sleep(0.01)
                logging.info('Reset off')
                # Special case for noise source: need to turn mosfet on as well
                if parameters['switch-control'][seq]['aux'] != 'None':
                    aux = parameters['switch-control'][seq]['aux']
                    aux_port = parameters['switch-control']['aux-gpios'][aux][0]
                    aux_pin = parameters['switch-control']['aux-gpios'][aux][1:]
                    gpios.set_output_latch(aux_port, aux_pin, True)
                    logging.info('AUX %s on'%(aux))
                # Set switch to the appropriate
                # source.  These are latching
                # switches, so just need to pulse the
                # pin...
                gpios.set_output_latch(port, pin, True)
                logging.info('%s source On'%(seq))
                time.sleep(0.20)
                # ...and then immediately turn off again
                logging.info('%s source Off'%(seq))
                gpios.set_output_latch(port, pin, False)
                # Record time stamps for how long
                # we're on this switch position.  Note
                # that we're using system time here,
                # will need to correct with RTC time
                # in post-processing.
                t_start=time.time()
                pos_scio_files[seq].append(nm.array([1,t_start]))
                time.sleep(ontime)
                if parameters['switch-control'][seq]['aux'] != 'None':
                    aux = parameters['switch-control'][seq]['aux']
                    aux_port = parameters['switch-control']['aux-gpios'][aux][0]
                    aux_pin = parameters['switch-control']['aux-gpios'][aux][1:]
                    gpios.set_output_latch(aux_port, aux_pin, False)
                    logging.info('AUX %s off'%(aux))
            t_stop=time.time()
            pos_scio_files[seq].append(nm.array([0,t_stop]))
            seq_list.append(seq)
    return None
#=======================================================================
def read_temperatures(fpga, parameters, start_time=None):
    """Read temperatures and log to file at specified time intervals
    - opts : options from parser, including time interval
    - start_time : optional starting time stamp for the log file
    """
    if start_time is None:
        start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    # Do an infinite loop over temperature reads
    while True:
        tstart = time.time()
        tfrag=repr(tstart)[:5]
        #starttime = datetime.datetime.utcnow()#.strftime('%Y%m%d_%H%M%S')
        outsubdir = parameters['directories']['top']+'/'+parameters['directories']['temperatures']+'/'+tfrag+'/'+str(nm.int64(tstart))
        if not os.path.isdir(outsubdir):
            os.makedirs(outsubdir)
        # One wire sensors take some time to read, so record
        # both start and stop times for each logging cycle.
        # Do this for both system time and attempted RTC
        # reads.

        f_therms = {}
        for i in ["time_start_gps_therms", "time_start_rtc_therms", "time_start_sys_therms",
                  "time_stop_gps_therms", "time_stop_rtc_therms", "time_stop_sys_therms",
                  "temp_pi", "temp_fpga"]:
            f_therms[i] = open(outsubdir + '/'+i+'.raw','w')

        # Files for one-wire sensors: specified in config file
        for i in parameters["temperature-sensors"]["sensors"].keys():
            f_therms[i] = open(outsubdir + '/temp_'+i+'.raw','w')

        # Start reading sensors
        while time.time()-tstart < parameters['scio-files']['file-time']:
            # Read Pi time (system and RTC) and temperature
            time_start_sys = time.time()
            time_start_gps = 0
            try:
	        time_start_gps = lbtools_l.lb_read()[0]
            except:
	        logging.error("Failed to read time from gps")
            time_start_rtc = rtc.timestamp()
            pi_temperature = subprocess.check_output(['cat', '/sys/class/thermal/thermal_zone0/temp'])
            pi_temp = nm.int32(pi_temperature)/1000.0
            logging.debug('%s = %f'%("RPi", pi_temp))
            fpga_temp = get_fpga_temp(fpga)
            logging.debug('%s = %f'%("FPGA", fpga_temp))

            # Read one-wire sensors
	    logging.debug('Starting one-wire read')
            for i in parameters["temperature-sensors"]["sensors"].keys():
                # Replace device wildcard with actual sensor ID and do a read
	 	try:
                    dfile = open("/sys/bus/w1/devices/w1_bus_master1/"+parameters["temperature-sensors"]["sensors"][i]["id"]+"/w1_slave")
                    txt = dfile.read()
                    dfile.close()
                except:
		    txt = None
		temperature = nm.NAN
		if txt is not None:
                    s = re.search(r't=(\d+)', txt)
                    if s is not None:
                        temperature = float(s.group(1)) / 1000
                        nm.array(temperature).tofile(f_therms[i])
                        logging.debug('%s = %f'%(i, temperature))
		    else:
	                logging.warning('%s, %s not found'%(parameters["temperature-sensors"]["sensors"][i]["id"], i))
            time_stop_sys = time.time()
            time_stop_gps = 0
            try:
	        time_stop_gps = lbtools_l.lb_read()[0]
            except:
	        logging.error("Failed to read time from gps, failing back to RTC")
            time_stop_rtc = rtc.timestamp()
            
            nm.array(time_start_sys).tofile(f_therms["time_start_sys_therms"])
            nm.array(time_start_gps).tofile(f_therms["time_start_gps_therms"])
	    nm.array(time_start_rtc).tofile(f_therms["time_start_rtc_therms"])
	    nm.array(pi_temp).tofile(f_therms["temp_pi"])
            nm.array(fpga_temp).tofile(f_therms["temp_fpga"])
            nm.array(time_stop_sys).tofile(f_therms["time_stop_sys_therms"])
            nm.array(time_stop_gps).tofile(f_therms["time_stop_gps_therms"])
	    nm.array(time_stop_rtc).tofile(f_therms["time_stop_rtc_therms"])

            for i in f_therms.keys():
                f_therms[i].flush()
            
	    time.sleep(parameters['temperature-sensors']['read_interval'])
        # Hmm, we weren't closing the files properly last year?
        for i in f_therms.keys():
            f_therms[i].close()

    return None
#=======================================================================
if __name__ == '__main__':
    # Parse config file with software parameters
    parser = ArgumentParser()
    parser.add_argument('configfile', type=str, help='yaml file with configuration options for PRIZMs DAQ')
    args = parser.parse_args()

    parameters=None
    with open(args.configfile, 'r') as cf:
        parameters=yaml.load(cf.read())

    # Intialise I2C bus and DS3231 RTC
    i2c_bus=smbus.SMBus(1)
    rtc=ds3231.DS3231(i2c_bus)

    # Check if the directory exists. If not, make it.
    if not os.path.exists(parameters['directories']['top']):
        os.makedirs(parameters['directories']['top']+"/logs")

    # Setup file logger
    logger = logging.getLogger()
    logger.setLevel(parameters['logging']["level"])
    f_handler = logging.FileHandler(parameters['directories']['top']+'/logs/prizm_daq_'+str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))+".log")
    f_format = logging.Formatter('%(asctime)s %(name)-12s %(levelname)s %(message)s')
    f_handler.setFormatter(f_format)
    f_handler.setLevel(parameters["logging"]["level"])
    logger.addHandler(f_handler)

    # Log run-time options
    logging.info('======= Run-time options =======')
    logging.info('SNAP-BOARD:')
    logging.info('%s%s = %s'%(' '*4, 'IP', parameters['snap-board']['ip']))
    logging.info('%s%s = %s'%(' '*4, 'PORT', parameters['snap-board']['port']))
    logging.info('%s%s = %s'%(' '*4, 'FIRMWARE', parameters['snap-board']['firmware']))
    logging.info('%s%s = %s'%(' '*4, 'FFT-CHANNELS', parameters['snap-board']['fft-channels']))
    logging.info('%s%s = %s'%(' '*4, 'FFT-SHIFT', parameters['snap-board']['fft-shift']))
    logging.info('%s%s = %s'%(' '*4, 'ACCUMULATION-LENGTH', parameters['snap-board']['accumulation-length']))
    logging.info('SWITCH-CONTROL:')
    logging.info('%s%s = %s'%(' '*4, 'SEQUENCE', " ".join(parameters["switch-control"]['sequence'])))
    logging.info('%s%s:'%(" "*4, 'SWITCHES'))
    for key in parameters["switch-control"]["switches"].keys():
        logging.info('%s%s:'%(' '*4, key.upper()))
        logging.info('%s%s:'%(' '*8, 'GPIOS'))
        for gpio_key in parameters["switch-control"]["switches"][key]["gpios"].keys():
            logging.info('%s%s = %s'%(' '*12, gpio_key, parameters["switch-control"]["switches"][key]["gpios"][gpio_key]))
    logging.info('%s%s:'%(" "*4, 'AUX_GPIOS'))
    for key in parameters["switch-control"]["aux-gpios"].keys():
        logging.info("%s%s = %s"%(' '*8, key, parameters["switch-control"]["aux-gpios"][key]))
    for seq in parameters["switch-control"]["sequence"]:
        logging.info('%s%s:'%(' '*4, seq))
        logging.info("%s%s = %s"%(' '*8, 'SWITCH', parameters["switch-control"][seq]["switch"]))
        logging.info("%s%s = %s"%(' '*8, 'POSITION', parameters["switch-control"][seq]["position"]))
        logging.info("%s%s = %s"%(' '*8, 'ONTIME', parameters["switch-control"][seq]["ontime"]))
        logging.info("%s%s = %s"%(' '*8, 'AUX', parameters["switch-control"][seq]["aux"]))
    logging.info("TEMPERATURE-SENSORS:")
    logging.info('%s%s = %s'%(' '*4, 'READ-INTERVAL', parameters["temperature-sensors"]["read_interval"]))
    temp_keys = parameters["temperature-sensors"].keys()
    temp_keys.sort()
    for key in temp_keys:
        if key[:5] == "temp_":
            logging.info("%s%s:"%(' '*4, key))
            logging.info('%s%s = %s'%(' '*8, 'ID', parameters["temperature-sensors"][key]["id"]))
            logging.info('%s%s = %s'%(' '*8, 'TAG', parameters["temperature-sensors"][key]["tag"]))
            logging.info('%s%s = %s'%(' '*8, 'DESCRIPTION', parameters["temperature-sensors"][key]["description"]))
    logging.info('SCIO-FILES:')
    logging.info('%s%s = %s'%(' '*4, 'DIFF', parameters['scio-files']['diff']))
    logging.info('%s%s = %s'%(' '*4, 'COMPRESS', parameters['scio-files']['compress']))
    logging.info('%s%s = %s'%(' '*4, 'FILE-TIME', parameters['scio-files']['file-time']))
    logging.info('LOGGING:')
    logging.info('%s%s = %s'%(' '*4, 'LEVEL', parameters['logging']['level']))
    logging.info('DIRECTORIES:')
    logging.info('%s%s = %s'%(' '*4, 'TOP', parameters['directories']['top']))
    #logging.info('%s%s = %s'%(' '*4, 'LOGS', parameters['directories']['logs']))
    logging.info('%s%s = %s'%(' '*4, 'TEMPERATURES', parameters['directories']['temperatures']))
    #logging.info('%s%s = %s'%(' '*4, 'HOUSEKEEPING', parameters['directories']['housekeeping']))
    logging.info('%s%s = %s'%(' '*4, 'SWITCH', parameters['directories']['switch']))
    logging.info('============= end ==============')

    try:
        # Setup Leo Bodnar GPSDO for sending nav packets
        logging.info("Setting up LeoBodnar GPSDO to send nav packets")
        if lbtools_l.lb_set():
            logging.info("LeoBodnar GPSDO set")
        else:
            logging.error("Failed to set LeoBodnar GPSDO")
        # MCP23017 reset pin is wired to RPI GPIO Pin 21. Needs to be high for normal operation
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(21, GPIO.OUT, initial=GPIO.LOW)
        GPIO.output(21, GPIO.HIGH)
        # Connect to SNAP board and initialize
        fpga = initialize(parameters)
        time.sleep(0.5)
        adc_bits = get_adc_stats(fpga)
        logging.info("Bits used: ADC0=%.2f, ADC1=%.2f"%(adc_bits["ADC0"]["bits_used"], adc_bits["ADC1"]["bits_used"]))
        # Start up switch operations and temperature logging, use same starting time stamp for both
        start_time = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        p1 = thread.start_new_thread(run_switch, (parameters, start_time))
        p2 = thread.start_new_thread(read_temperatures, (fpga, parameters, start_time))
        acquire_data(fpga, parameters)
    except Exception as e:
        logging.error('An exception has occured:')
        logging.error(e.message)
    finally:
        GPIO.cleanup()
        logging.info('Terminating DAQ script at %s'%(str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))))
