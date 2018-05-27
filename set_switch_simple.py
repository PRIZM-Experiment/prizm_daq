#!/usr/bin/env /usr/bin/python
import datetime, time, os, sys
import numpy as nm
import RPi.GPIO as GPIO
from optparse import OptionParser

# Stripped down version of housekeeping code that just sets the switch state
# For example, to set the switch to the antenna for an infinite amount of time, do
# ./set_switch_simple.py -o "antenna" -a 12,-1

#=======================================================================
def seq_callback(option, opt, value, parser):
        """Deal with user-specified sequence selection in the option parser."""
        setattr(parser.values, option.dest, [str(v) for v in value.split(',')])
        return

#=======================================================================
def src_callback(option, opt, value, parser):
        """Deal with user-specified source params in the option parser."""
        vals = [v for v in value.split(',')]
        if len(vals) != 2:
            print 'Source',option.dest,': need two and only two values (GPIO pin, # minutes)'
            exit(0)
        setattr(parser.values, option.dest, [int(vals[0]), float(vals[1])])
        return

#=======================================================================
def run_switch(opts, start_time=None):
        """Run the switch.  Cycle between sources by turning on appropriate
        Raspberry Pi GPIO pins for user-specified lengths of time.
        - opts : options from parser
        - start_time : optional starting time stamp for the log file
        """

        # Define dictionary of sources to switch between.  For each
        # source, specify a two-element list consisting of GPIO pin number
        # and number of MINUTES for source to remain selected.
        srcs = {'antenna' : opts.antenna,
                'res100' : opts.res100,
                'res50' : opts.res50,
                'short' : opts.short,
                'noise' : opts.noise,
                'open' : opts.open}

        # Set GPIO mode for all selected sources
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(opts.reset, GPIO.OUT)   
        GPIO.output(opts.reset, GPIO.LOW)
        GPIO.setup(opts.mosfet, GPIO.OUT)
        GPIO.output(opts.mosfet, GPIO.LOW)
        for src in opts.seq:
                pin = srcs[src][0]
                GPIO.setup(pin, GPIO.OUT)  # Define the pins as outputs
                GPIO.output(pin, GPIO.LOW) # All pins set to LOW i.e. 0V
                print 'GPIO pin', pin, 'set to output. Initial state:LOW'

	while True:
                for src in opts.seq:
                        pin = srcs[src][0]
                        ontime = float(srcs[src][1]) * 60.   # Convert to seconds
                        # Reset all solenoids
                        print 'Reset On'
                        GPIO.output(opts.reset,1)
                        time.sleep(0.20)
                        GPIO.output(opts.reset,0);time.sleep(0.20);print 'Reset off'
                        # Special case for noise source: need to turn mosfet on as well
                        if src == 'noise': GPIO.output(opts.mosfet,1); print 'mosfet on'
                        # Set switch to the appropriate
                        # source.  These are latching
                        # switches, so just need to pulse the
                        # pin...
                        GPIO.output(pin,1);print '%s Src On'%src
                        time.sleep(0.20)
                        # ...and then immediately turn off again
                        print '%s Src Off'%src
                        GPIO.output(pin,0)
                        # Wait for specified period of time
                        if ontime >=0:
                                time.sleep(ontime)
                        else:
                                print 'You have specified infinite time for source', src
                                print 'Switch is set, exiting now.  Enjoy your calibrating.'
                                if src == 'noise':
                                        print 'REMEMBER THE NOISE DIODE IS POWERED ON RIGHT NOW'
                                exit(0)
                        if src == 'noise': GPIO.output(opts.mosfet,0); print 'mosfet off'
                        sys.stdout.flush()
        return

#=======================================================================
if __name__ == '__main__':
    
# Parse options
    parser = OptionParser()
    parser.set_usage('set_switch_simple.py [options]')
    parser.set_description(__doc__)
    parser.add_option('-o', '--order', dest='seq',type='string', default=['antenna','res50','short','noise','res100','open'],
        	      help='Desired switch sequence of sources, options are "antenna", "res100", "res50", "short", "noise", "open" [default: %default]',
                      action='callback', callback=seq_callback)
    parser.add_option('--reset', dest='reset', type='int', default=18, 
		      help='Reset GPIO pin [default: %default]')
    parser.add_option('-a', '--antenna', dest='antenna', type='string',default=[12,100],
		      help='Antenna: GPIO pin \# and \# of minutes (-1 = infinite) [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-R', '--res100', dest='res100', type='string',default=[26,100],
		      help='100 ohm resistor: GPIO pin \# and \# of minutes (-1 = infinite) [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-r', '--res50', dest='res50', type='string',default=[24,100],
		      help='50 ohm resistor: GPIO pin \# and \# of minutes (-1 = infinite) [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-s', '--short', dest='short', type='string',default=[25,100],
		      help='Short: GPIO pin \# and \# of minutes (-1 = infinite) [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-n', '--noise', dest='noise', type='string',default=[5,100],
		      help='Noise: GPIO pin \# and \# of minutes (-1 = infinite) [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-O', '--open', dest='open', type='string',default=[23,100],
		      help='Open: GPIO pin \# and \# of minutes (-1 = infinite) [default: %default]', action='callback', callback=src_callback)
    parser.add_option('-m', '--mosfet', dest='mosfet', type='int', default=21,
		      help='Mosfet GPIO pin [default: %default]')
    opts, args = parser.parse_args(sys.argv[1:])

    #------------------------------------------------------
    try:
            run_switch(opts, None)

    except KeyboardInterrupt:
            print '==================================================='
            print 'Keyboard Interrupt : All used GPIOs will be cleaned'
    finally:
            GPIO.cleanup()
            print 'All used GPIOs cleaned'
            print '==================================================='
