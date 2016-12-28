from __future__ import print_function
from opendaq import DAQ

dq = DAQ('/dev/ttyUSB0')
dq.set_analog(1)
dq.device_info()
print(dq.read_all())
