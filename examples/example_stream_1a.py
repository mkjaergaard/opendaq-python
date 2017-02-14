"""Creat two streams and wait until they finish"""

from __future__ import print_function
import time
from opendaq import DAQ, ExpMode, Gains

# Connect to the device
# Change here the serial port in which the openDAQ is connected
daq = DAQ("COM3")

# Set Analog voltage
daq.set_analog(0.9)

stream1 = daq.create_stream(ExpMode.ANALOG_IN, 1, 10, continuous=False)
stream1.analog_setup(pinput=8, gain=Gains.M.x1)

stream2 = daq.create_stream(ExpMode.ANALOG_IN, 1, 20, continuous=False)
stream2.analog_setup(pinput=7, ninput=8, gain=Gains.M.x1)

daq.start()

while daq.is_measuring:
    time.sleep(0.1)

data1 = stream1.read()
data2 = stream2.read()

daq.stop()
daq.close()

print("data1:", data1)
print("data2:", data2)
