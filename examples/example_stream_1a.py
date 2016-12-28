"""Creat two streams and wait until they finish"""

from __future__ import print_function
import time
from opendaq.daq import DAQ, ExpMode, PGAGain

# Connect to the device
# Change here the serial port in which the openDAQ is connected
daq = DAQ('/dev/ttyUSB0')

# Set Analog voltage
daq.set_analog(0.9)

stream1 = daq.create_stream(ExpMode.ANALOG_IN, 200, continuous=False)
stream1.analog_setup(pinput=8, gain=PGAGain.S_X1)

stream2 = daq.create_stream(ExpMode.ANALOG_IN, 300, continuous=False)
stream2.analog_setup(pinput=7, ninput=8, gain=PGAGain.S_X1)

daq.start()

while daq.is_measuring:
    time.sleep(1)

print("data1", stream1.read())
print("data2", stream2.read())

daq.stop()
