"""Basic configuration for loading a signal,
generate it through the analog output"""

from __future__ import print_function
import time
from opendaq.daq import DAQ, ExpMode, PGAGain

# Connect to the device
# Change here the serial port in which the openDAQ is connected
daq = DAQ('/dev/ttyUSB0')

stream1 = daq.create_stream(ExpMode.ANALOG_IN, 300, npoints=16)
stream1.analog_setup(pinput=8, gain=PGAGain.S_X1)

# create a ramp signal with 4 samples
signal = list(range(4))

stream2 = daq.create_stream(ExpMode.ANALOG_OUT, 300, npoints=len(signal))
stream2.load_signal(signal, clear=True)

daq.start()

while daq.is_measuring:
    time.sleep(1)

print("data1", stream1.read())

daq.stop()
