#!/usr/bin/env python

from opendaq import *
import time
import sys


dq = DAQ("COM3")
time.sleep(.05)

volts = float(sys.argv[1])
print "Voltage Set: ",volts

dq.set_analog(volts)

dq.close()


