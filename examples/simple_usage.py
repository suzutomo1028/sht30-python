#!/usr/bin/env python3

import sys, os
sys.path.append(os.pardir)
from sc18im700 import SC18IM700
from sht30 import SHT30
import time

def main():
    with SC18IM700('COM4') as sc18:
        sht30 = SHT30(sc18)
        sht30.begin()
        try:
            while True:
                temp, humi = sht30.singleshot_measure()
                tc = sht30.temperature_C(temp)
                tf = sht30.temperature_F(temp)
                rh = sht30.relative_humidity(humi)
                print('{:.2f} degC / {:.2f} degF / {:.2f} %RH'.format(tc, tf, rh))
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()
