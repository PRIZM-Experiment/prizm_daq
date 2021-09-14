import corr
import iadc
import time
import struct
import pylab
from optparse import OptionParser
import sys,os

p = OptionParser()
p.set_usage('python plot_test_ramp.py <specify IP address of the snap-pi, specify the boffile>')
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
r.progdev(BOFFILE)

adc = iadc.Iadc(r)

# set up for dual-channel (non-interleaved) mode
adc.set_dual_input()

print 'Board clock is', r.est_brd_clk()

adc.set_ramp_mode()

xraw = r.snapshot_get('snapshot_ADC0', man_trig=True, man_valid=True)
x = struct.unpack('%dB' % xraw['length'], xraw['data'])
yraw = r.snapshot_get('snapshot_ADC1', man_trig=True, man_valid=True)
y = struct.unpack('%dB' % yraw['length'], yraw['data'])

pylab.figure()
pylab.title('Ramp is excellent!, otherwise FPGA is unhappy with the external ADC')
pylab.subplot(4,1,1)
pylab.plot(x[0:1024:2])
pylab.subplot(4,1,2)
pylab.plot(x[1:1024:2])
pylab.subplot(4,1,3)
pylab.plot(y[0:1024:2])
pylab.subplot(4,1,4)
pylab.plot(y[1:1024:2])
pylab.show()
