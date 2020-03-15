import time
import RPi.GPIO as R
import os
#import matplotlib as plt

data = open("sensor_data.txt","w")
i = 1
while i > 0:
	timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
	tfile1 = open("/sys/bus/w1/devices/28-01160052a1ff/w1_slave")
	temp1 = tfile1.read()
	tfile1.close()
	secondline = temp1.split("\n")[1] 
	temperaturedata = secondline.split(" ")[9]
	temperature = float(temperaturedata[2:])
	temperature = temperature / 1000 
	print i
	#print temp1
	#print secondline
	#print temperaturedata
	print timestamp
	print temperature
	data.write(str(i) + "," + str(timestamp) + "," + str(temperature) + "\n")
        i = i + 1
	time.sleep(0)
        continue
#        plt.plot(timestamp,temperature)
data.close()
