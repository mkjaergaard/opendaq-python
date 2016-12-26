from opendaq import *
from opendaq.daq import *
import time

# Connect to the device
# change for the Serial port in which openDAQ is connected
dq = DAQ("COM3")


dq.init_capture(12500)
i = 0

while i < 20:
    try:
        time.sleep(1)
        i = i + 1  
        a = dq.get_capture(2)   # 2: full period
        print "T: ", 1 / (a[1] / 1000.)
    except KeyboardInterrupt:
        dq.close()


dq.stop()
