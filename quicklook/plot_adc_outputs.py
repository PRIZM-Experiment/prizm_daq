import corr
import iadc
import time
import struct
import pylab
from optparse import OptionParser
import sys,os
import numpy as np

p = OptionParser()
p.set_usage('python plot_adcs.py <specify IP address of the snap-pi, specify the boffile>')
p.set_description(__doc__)
p.add_option('-i', '--ip', dest='ip', type='str',default='', help='IP address of the raspberry pi')
p.add_option('-b', '--bof', dest='boffile',type='str', default='extadc_snap_spec_2017-03-24_1035.bof', help='Specify the bof file to load')
opts, args = p.parse_args(sys.argv[1:])

SNAPHOST = opts.ip
BOFFILE = opts.boffile

print 'Connecting to', SNAPHOST
r = corr.katcp_wrapper.FpgaClient(SNAPHOST)
time.sleep(0.05)

print 'Programming with', BOFFILE
#r.progdev(BOFFILE)

#adc = iadc.Iadc(r)

# set up for dual-channel (non-interleaved) mode
#adc.set_dual_input()

print 'Board clock is', r.est_brd_clk()

#adc.set_data_mode()

xraw = r.snapshot_get('snapshot_ADC0', man_trig=True, man_valid=True)
x = struct.unpack('%db' % xraw['length'], xraw['data'])
yraw = r.snapshot_get('snapshot_ADC1', man_trig=True, man_valid=True)
y = struct.unpack('%db' % yraw['length'], yraw['data'])

print 'x_rms:', np.std(x)
print 'y_rms:', np.std(y)

np.savez(open("adc_dump_100MHz_20170430_set5.npz","w"),Xpol=x, Ypol=y)

pylab.figure()
pylab.title('Output of 2 ADC blocks on the external ADC card')
pylab.subplot(2,1,1)
pylab.title('Channel 0')
pylab.plot(x)
pylab.subplot(2,1,2)
pylab.title('Channel 1')
pylab.plot(y)
pylab.show()


