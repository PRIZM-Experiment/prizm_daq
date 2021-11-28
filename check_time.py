import lbtools_l
import ds3231
import smbus
import time
import datetime
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--set-gps-time-to-rtc", action="store_true", default=False, help="Set gps time to RTC")
    parser.add_argument("-m", "--monitor", action="store_true", default=False, help="Monitor the output of the time, rtc, and gps every 5 seconds")
    args = parser.parse_args()

    bus = smbus.SMBus(1)
    rtc = ds3231.DS3231(bus)
    lbtools_l.lb_set()

    if args.set_gps_time_to_rtc:
        print("Setting RTC to GPS time")
        rtc.set_datetime(lbtools_l.lb_read()[2])

    if args.monitor:
        while True:
            lt = datetime.datetime.now()
            rt = rtc.get_datetime()
            gt = lbtools_l.lb_read()[2]
            print("Local:", lt.strftime("%Y-%m-%d %H:%M:%S"))
            print("RTC:", rt.strftime("%Y-%m-%d %H:%M:%S"))
            print("GPS:", gt.strftime("%Y-%m-%d %H:%M:%S"))
            print("Diff (Local-RTC):", (lt-rt).total_seconds())
            print("Diff (RTC-GPS):", (rt-gt).total_seconds())
            time.sleep(5)

    lt = datetime.datetime.now()
    rt = rtc.get_datetime()
    gt = lbtools_l.lb_read()[2]

    print("Local current time:", lt.strftime("%Y-%m-%d %H:%M:%S"))
    print("RTC current time:", rt.strftime("%Y-%m-%d %H:%M:%S"))
    print("GPS current time:", gt.strftime("%Y-%m-%d %H:%M:%S"))
