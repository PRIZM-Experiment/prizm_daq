import numpy,scio
n=50
m=100;
x=numpy.random.randn(n,m)
f=scio.scio('test1.scio')
ff=scio.scio('test2.scio',diff=True)
for i in range(n):
    f.append(x[i,:])
    ff.append(x[i,:])
f.close()
ff.close()


print x.shape

xx=scio.read('test1.scio')
xx2=scio.read('test2.scio')
