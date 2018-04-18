import numpy,scio
from matplotlib import pyplot as plt

aa=scio.read('pol0_1490282305.scio')
bb=scio.read('pol0_1490283209.scio')
cc=scio.read('pol0_1490284113.scio')
dd=numpy.vstack((aa,bb,cc))

nu=(numpy.arange(dd.shape[1])/(1.0*dd.shape[1]-1)+0.5)*250;
tvec=(numpy.arange(dd.shape[0]))*5.0


plt.ion()
plt.imshow(numpy.log10(dd),aspect='auto',extent=(0, 250, 5.0*dd.shape[0],0))
plt.xlabel('Frequency')
plt.colorbar()
plt.title('Log10(Power)')
plt.savefig('sweep.png')

#plt.imshow(numpy.log10(dd),aspect='auto')

