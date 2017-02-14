"""Plotting a chart from a stream type experiment
and use another experiment to generate the signal"""

import time
import matplotlib.pyplot as plt
from opendaq import DAQ, ExpMode, Gains

# Change to the serial port in wich openDAQ is actually connected
dq = DAQ('COM3')

# Configure the first experiment, the one that will be plotted
data_rate = 20
stream1 = dq.create_stream(ExpMode.ANALOG_IN, data_rate, continuous=True)
stream1.analog_setup(pinput=8, gain=Gains.S.x1)

# Configure the second experiment, a custom signal generated from a stream
preload_buffer = [-2.5, -1, 0, 1, 2.5]
stream2 = dq.create_stream(ExpMode.ANALOG_OUT, period=500,
                           npoints=len(preload_buffer), continuous=True)
stream2.load_signal(preload_buffer)

# Initiate lists and variables
t0 = 0.0
t = []
data = []

# Initiate the plot
fig = plt.figure()
plt.ion()
plt.show()

# start the experiment
dq.start()

while dq.is_measuring:
    try:
        time.sleep(1)
        a = stream1.read()
        l = len(a)
        # append values list with new points from the stream
        data.extend(a)
        # append time list with the same number of elements
        t.extend([t0+(data_rate*x)/1000.0 for x in range(l)])
        t0 += (l*data_rate)/1000.0  # increase the time reference
        plt.plot(t, data, color="blue", linewidth=1.0, linestyle="-")
        plt.draw()
    except KeyboardInterrupt:
        plt.close()
        # stop the experiment
        dq.stop()
        dq.close()
        break
