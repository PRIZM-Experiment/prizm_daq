import numpy,scio
from matplotlib import pyplot as plt

aa=scio.read('pol1_1490380508.scio')
dd=aa.copy()
nu=((numpy.arange(dd.shape[1])+0.5)/(1.0*dd.shape[1]))*250;
tvec=(numpy.arange(dd.shape[0]))*5.0

short_spec=numpy.median(aa,0)

bb=scio.read('pol1_1490378695.scio');
load_spec=numpy.median(bb,0);


aa=scio.read('pol1_1490375185.scio')
bb=scio.read('pol1_1490376086.scio')
cc=scio.read('pol1_1490376991.scio')
dd=numpy.vstack((aa,bb,cc))
sky_spec=numpy.median(dd,0)




plt.ion()

plt.clf();
plt.plot(nu[1:],short_spec[1:]);
plt.plot(nu[1:],load_spec[1:]);
plt.plot(nu[1:],sky_spec[1:]);
plt.yscale('log')

plt.legend(['Short','50 Ohm load','Antenna']);
plt.ylabel('power')
plt.xlabel('Frequency (MHz)')

plt.savefig('lab_short_load_sky_spectra.png')



#plt.imshow(numpy.log10(dd),aspect='auto',extent=(0, 250, 5.0*dd.shape[0],0))
#plt.xlabel('Frequency')
#plt.colorbar()
#plt.title('Log10(Power)')
#plt.savefig('durban_70mhz.png')

#plt.imshow(numpy.log10(dd),aspect='auto')

#ii=dd[:,1166]>2e11
#ii2=dd[:,1166]<2e11

#spec1=numpy.median(dd[ii,:],axis=0)
#spec2=numpy.median(dd[ii2,:],axis=0)
