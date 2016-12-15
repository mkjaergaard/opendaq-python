"""Creating two streams and allowing them to end"""

import time
from opendaq.daq import DAQ, ANALOG_INPUT, GAIN_S_X1

# Connect to the device
dq = DAQ("COM3")  # change for the Serial port in which openDAQ is connected

# Set Analog voltage
dq.set_analog(0.9)

stream1 = dq.create_stream(ANALOG_INPUT, 200, continuous=False)
stream1.analog_setup(pinput=8, gain=GAIN_S_X1)

stream2 = dq.create_stream(ANALOG_INPUT, 300, continuous=False)
stream2.analog_setup(pinput=7, ninput=8, gain=GAIN_S_X1)


dq.start()

while dq.is_measuring():
    time.sleep(1)

print "data1", stream1.read()
print "data2", stream2.read()

dq.stop()
