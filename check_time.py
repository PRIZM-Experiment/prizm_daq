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

    print("Local current time:", datetime.datetime.now())
    print("RTC current time:", rtc.get_datetime())
    print("GPS current time:", lbtools_l.lb_read()[1])

    if args.set_gps_time_to_rtc:
        print("Setting RTC to GPS time")
        rtc.set_datetime(lbtools_l.lb_read()[1])

    if args.monitor:
        while True:
            lt = datetime.datetime.now()
            rt = rtc.get_datetime()
            gt = lbtools_l.lb_read()[1]
            print("Local:", lt, "RTC:", rt, "GPS:", gt, "Diff (Local-RTC):", lt-rt, "DIFF (RTC-GPS):", rt-gt)
            time.sleep(5)
