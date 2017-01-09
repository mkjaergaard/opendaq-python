from __future__ import print_function
from opendaq import DAQ

daq = DAQ('/dev/ttyUSB0')
daq.set_analog(1)
print(daq)
print(daq.read_all())
