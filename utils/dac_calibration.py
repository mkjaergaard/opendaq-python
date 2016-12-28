#!/usr/bin/env python

from opendaq import *
import time
import sys
import numpy as np

if len(sys.argv) < 2:
    filename="calibration.txt"
else:
    filename=sys.argv[1]

if len(sys.argv) > 2:
    channel = sys.argv[2] - 1
else:
    channel = 0

x = []
y = []

with open(filename, 'r+') as f:
    for line in f:
        a = [float(s) for s in line.split()]
        if len(a) == 2:
            x.append(a[0])
            y.append(a[1])

print "x ", x
print "y ", y

new_corr, new_offset = np.polyfit(x, y, 1)
print new_corr, new_offset

dq = DAQ("COM3")
time.sleep(.05)

dac_corr, dac_offset = dq.get_dac_cal()

dac_corr[channel] *= new_corr
dac_offset[channel] += new_offset

"""
dac_corrs = [1.0]
dac_offsets = [0]
"""

print "Nuevas calibraciones DAC: \n",dq.set_dac_cal(dac_corr,dac_offset)

dq.close()
