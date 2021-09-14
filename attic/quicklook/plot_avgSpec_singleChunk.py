#!/usr/bin/python
import corr,time,struct,sys,logging,pylab
import matplotlib.pyplot as plt
import os
import sys
import numpy as np
import iadc #Jack's spell

def get_data():	
    ep0 = np.array(struct.unpack('>2048Q', fpga.read('even_pol0',2048*8,0)))
    #print ep0
    op0 = np.array(struct.unpack('>2048Q', fpga.read('odd_pol0',2048*8,0)))
    #print op0
    ep1 = np.array(struct.unpack('>2048Q', fpga.read('even_pol1',2048*8,0))) 	
    op1 = np.array(struct.unpack('>2048Q', fpga.read('odd_pol1',2048*8,0)))
    even_real = np.array(struct.unpack('>2048q', fpga.read('even_real',2048*8,0)))
    even_imaginary = np.array(struct.unpack('>2048q', fpga.read('even_imaginary',2048*8,0)))
    odd_real = np.array(struct.unpack('>2048q', fpga.read('odd_real',2048*8,0)))
    odd_imaginary = np.array(struct.unpack('>2048q', fpga.read('odd_imaginary',2048*8,0)))
    
    pol0,pol1, real, imaginary = [],[],[],[]
    for i in range(len(ep0)):
      pol0.append(ep0[i])
      pol0.append(op0[i])
      pol1.append(ep1[i])
      pol1.append(op1[i])
      real.append(even_real[i])
      real.append(odd_real[i])
      imaginary.append(even_imaginary[i])
      imaginary.append(odd_imaginary[i])  
    #print 'pol0=', pol0
    #print 'pol1=',len(pol1)
    #print 'real=',len(real)
    #print 'imaginary=',len(imaginary)

    return pol0,pol1, np.asarray(real)+ 1j* np.asarray(imaginary)

def plot_spectrum():
    
    pol0, pol1, crossmult = get_data()
    freq = np.arange(0,250,0.1220703125)
    plt.subplot(311)
    plt.plot(freq,pol0,'r')
    plt.grid()
    plt.subplots_adjust(hspace = 1.2)
    plt.xlabel('frequency(MHz)')
    plt.ylabel('Power')
    plt.title('Power Spectra of pol0')
    plt.subplot(312)
    plt.plot(freq,pol1,'k')
    plt.grid()
    plt.title('Power Spectra of pol1')
    plt.xlabel('frequency(MHz)')
    plt.ylabel('Power')
    plt.subplot(313)
    plt.plot(freq,np.angle(crossmult),'b')
    plt.title('Crossmult angle signal')
    plt.ylabel('Phase(radians)')
    plt.xlabel('frequency(MHz)')
    plt.grid()
    plt.show()

if __name__ == '__main__':
    from optparse import OptionParser
    

    p = OptionParser()
    p.set_usage('scihi_spec.py <SNAP_HOSTNAME_or_IP> [options]')
    p.set_description(__doc__)
    p.add_option('-i', '--ip', dest='ip', type='str',default='',
        help='IP address of the raspberry pi')
    p.add_option('-l', '--acc_len', dest='acc_len', type='int',default=2*(2**28)/2048,
        help='Set the number of vectors to accumulate between dumps. default is 2((2^28)/2048, or just under 2 seconds.')
    p.add_option('-b', '--bof', dest='boffile',type='str', default='extadc_snap_spec_2017-03-24_1035.bof', help='Specify the bof file to load')
    opts, args = p.parse_args(sys.argv[1:])

snaphost = opts.ip
bof = opts.boffile

print('Connecting to snapboard at %s \n'%(snaphost)),
fpga = corr.katcp_wrapper.FpgaClient(snaphost)
time.sleep(0.05)

print('Programming with %s \n' %(bof)),
fpga.progdev(bof)
adc = iadc.Iadc(fpga) #Initialize the ADC object
adc.set_dual_input() #Set up for dual-pol (non-interleaved) mode
print 'Board clock is', fpga.est_brd_clk() #Board clock should be 1/4 of the sampling clock (board clock=125 MHz)
adc.set_data_mode() #Turn of the test ramp mode, if active

print '-------------------'

print 'Configuring accumulation period...'
fpga.write_int('acc_len', opts.acc_len)
fpga.write_int('fft_shift', 0xFFFFFFFF)
print 'done'
time.sleep(5)
fpga.stop
print 'List of registers: \n',fpga.listdev() #Lists all the registers
plot_spectrum()
print 'Success'
