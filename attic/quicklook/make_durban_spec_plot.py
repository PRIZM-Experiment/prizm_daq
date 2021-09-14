import numpy,scio
from matplotlib import pyplot as plt

aa=scio.read('pol1_1490375185.scio')
bb=scio.read('pol1_1490376086.scio')
cc=scio.read('pol1_1490376991.scio')
dd=numpy.vstack((aa,bb,cc))

nu=(numpy.arange(dd.shape[1])/(1.0*dd.shape[1]-1)+0.5)*250;
tvec=(numpy.arange(dd.shape[0]))*5.0


plt.ion()
plt.imshow(numpy.log10(dd),aspect='auto',extent=(0, 250, 5.0*dd.shape[0],0))
plt.xlabel('Frequency')
plt.colorbar()
plt.title('Log10(Power)')
plt.savefig('durban.png')

#plt.imshow(numpy.log10(dd),aspect='auto')

ii=dd[:,1166]>2e11
ii2=dd[:,1166]<2e11

spec1=numpy.median(dd[ii,:],axis=0)
spec2=numpy.median(dd[ii2,:],axis=0)
