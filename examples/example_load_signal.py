"""Basic configuration for loading a signal,
generate it through the analog output and print on screen"""

import time
from opendaq.daq import DAQ, ANALOG_INPUT, ANALOG_OUTPUT, GAIN_S_X1

# Connect to the device
dq = DAQ("COM3")  # change for the Serial port in which openDAQ is connected

stream1 = dq.create_stream(ANALOG_INPUT, 100, npoints=16, continuous=False)
stream1.analog_setup(pinput=8, gain=GAIN_S_X1)

preload_buffer = [0, 1, 2, 3]
stream2 = dq.create_stream(ANALOG_OUTPUT, 300, npoints=len(preload_buffer)+1,
                           continuous=False)
stream2.load_signal(preload_buffer, clear=True)

dq.start()

while dq.is_measuring():
    time.sleep(1)

print "data1", stream1.read()

dq.stop()
