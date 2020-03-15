import numpy,scio
from matplotlib import pyplot as plt

aa=scio.read('pol0_1490282305.scio')
bb=scio.read('pol0_1490283209.scio')
cc=scio.read('pol0_1490284113.scio')
ee=scio.read('pol0_1490298177.scio') #this one has the filter over the Valon output
ff=scio.read('pol0_1490299078.scio') #this one has the filter over the Valon output
tmp=0*ee[0:10,:]
dd=numpy.vstack((aa,bb,cc,tmp,ee,ff))
delt=aa[107,:]-ee[103,:] #this is a pair of nearly-matched before/after scans at same frequency

nu=((numpy.arange(dd.shape[1])+0.5)/(1.0*dd.shape[1]))*250;
tvec=(numpy.arange(dd.shape[0]))*5.0


plt.ion()
plt.imshow(numpy.log10(dd),aspect='auto',extent=(0, 250, 5.0*dd.shape[0],0),vmin=7.0,vmax=8.0)
plt.xlabel('Frequency')
plt.colorbar()
plt.title('Log10(Power)')
plt.savefig('sweep_wfilter.png')





#plt.imshow(numpy.log10(dd),aspect='auto')

