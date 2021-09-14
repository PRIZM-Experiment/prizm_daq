import glob
import os
import argparse
import time

if __name__=="__main__":
    parser = argparse.ArgumentParser(description = "Script to interact with DS18B20 sensors")
    #parser.add_argument("bus", type=str, help = "Userspace location for w1 interface")
    parser.add_argument("-f", "--find-sensors", action = "store_true", help = "Find DS18B20 sensors attached to w1 bus")
    parser.add_argument("-r", "--read-specific-sensor", type = str, help = "Read sensor with specified address")
    parser.add_argument("-R", "--read-all-sensors", action = "store_true", help = "Read all DS18B20 sensors of specified w1 bus")
    parser.add_argument("-t", "--read-interval", type = int, default = 10, help = "Continuously read sensors every specified seconds")
    args = parser.parse_args()

    bus = "/sys/bus/w1/devices/w1_bus_master1"

    if os.path.exists(bus):
        print("one wire interface is running")
    else:
        print("check if one wire interface is enabled")
        exit(1)

    if args.find_sensors:
        sensors = glob.glob(bus+"/28-*")
        sensors.sort()
        print("Found %d sensors:"%(len(sensors)))
        for sensor in sensors:
            print("Address: %s"%(sensor[sensor.rfind("/")+1:-1]))

    if args.read_all_sensors:
        if args.read_interval == None:
            sensors = glob.glob(bus+"/28-*/w1_slave")
            sensors.sort()
            for sensor in sensors:
                temp = open(sensor, 'r')
                data = temp.read()
                print(sensor, round(int(data[data.find('t=')+2:-1])/1000.0, 2))
                temp.close()
        else:
            while True:
                sensors = glob.glob(bus+"/28-*/w1_slave")
                sensors.sort()
                for sensor in sensors:
                    temp = open(sensor, 'r')
                    data = temp.read()
                    print(sensor, round(int(data[data.find('t=')+2:-1])/1000.0, 2))
                    temp.close()
                time.sleep(args.read_interval)
                print(time.time())

