import numpy,pylab
import scio
import optparse
import os,sys
import time

def ct_to_utc(ctime):
        ''' Converting from ctime to UTC '''
        gtime = time.gmtime(ctime)
        gtime_str = str(gtime.tm_mday) + '/' + str(gtime.tm_mon) + '/' + str(gtime.tm_year) + ':' + str(gtime.tm_min) + ':' + str(gtime.tm_sec)

        return gtime_str

if '__name__==__main__':
        o = optparse.OptionParser()
        o.set_usage('python plot_spectra.py [options] *.directories')
        o.set_description(__doc__)
        o.add_option('--spectra',dest='spectra',action='store_true',help='Set to output 2D spetctra')
        o.add_option('--mean',dest='mean',action='store_true',help='Set to output averaged spectra')
        o.add_option('--temp',dest='temp',action='store_true',help='Set to output temperature plots')
        o.add_option('--acc',dest='acc',action='store_true',help='Set to output accumulation plots')
        o.add_option('--phys',dest='phys',action='store_true',help='To display time in UTC')
        opts,args = o.parse_args(sys.argv[1:])

        f_aa , f_bb = None, None
        f_cross_real , f_cross_imag, f_cross = None, None, None
        f_t_start, f_t_stop = numpy.array([]), numpy.array([])
        f_acc_cnt1, f_acc_cnt2 = numpy.array([]), numpy.array([])
        f_fft_of_cnt, f_fft_shift = numpy.array([]), numpy.array([])
        f_sys_clk1, f_sys_clk2 = numpy.array([]), numpy.array([])
        f_sync_cnt1, f_sync_cnt2 = numpy.array([]), numpy.array([])
        f_pi_temp, f_fpga_temp = numpy.array([]), numpy.array([])
        utctime = []
        for dname in args:
                try:
                        ctime = dname.split('/')[-1]
                        utctime.append(ct_to_utc(float(ctime)))
                        print 'Opening ', dname
                        print 'Uncompressing files'
                        os.system('bzip2 -dk ' + dname + '/pol0.scio.bz2')
                        os.system('bzip2 -dk ' + dname + '/pol1.scio.bz2')
                        os.system('bzip2 -dk ' + dname + '/cross_real.scio.bz2')
                        os.system('bzip2 -dk ' + dname + '/cross_imag.scio.bz2')
                        print 'Reading scio files'
                        pol0 = scio.read(dname + '/pol0.scio')
                        pol1 = scio.read(dname + '/pol1.scio')
                        cross_real = scio.read(dname + '/cross_real.scio')
                        cross_imag = scio.read(dname + '/cross_imag.scio')
                        cross = cross_real + 1j*cross_imag

                        print 'Reading raw files'
                        t_start = numpy.fromfile(dname + '/time_start.raw')
                        t_stop = numpy.fromfile(dname + '/time_stop.raw')
                        acc_cnt1 = numpy.fromfile(dname + '/acc_cnt1.raw',dtype='int32')
                        acc_cnt2 = numpy.fromfile(dname + '/acc_cnt2.raw',dtype='int32')
                        fft_of_cnt = numpy.fromfile(dname + '/fft_of_cnt.raw',dtype='int32')
                        fft_shift = numpy.fromfile(dname + '/fft_shift.raw',dtype='int32')
                        sys_clk1 = numpy.fromfile(dname + '/sys_clk1.raw',dtype='int32')
                        sys_clk2 = numpy.fromfile(dname + '/sys_clk2.raw',dtype='int32')
			f_sync_cnt1 = numpy.append(f_sync_cnt1,sync_cnt1)
                        f_sync_cnt2 = numpy.append(f_sync_cnt2,sync_cnt2)
                        f_pi_temp = numpy.append(f_pi_temp,pi_temp/1000.)
                        f_fpga_temp = numpy.append(f_fpga_temp,fpga_temp)
                except:
                        continue
