"""Drawing a simple chart using command-response mode"""

from time import sleep
import matplotlib.pyplot as plt
from opendaq import DAQ

# Change  to the serial port in which openDAQ is actually connected
dq = DAQ("COM3")
dq.conf_adc(8)  # Reading in AN8

delaytime = 0.5

# Initiate plot:
fig = plt.figure()
plt.ion()
plt.show()

# initiate lists
t = [0]
data = []
i = 0

while True:
    try:
        dq.set_analog(i/100.0)  # We will plot a ramp line
        data.append(dq.read_analog())   # Add a new point to the plot
        plt.plot(t, data, color="blue", linewidth=2.5, linestyle="-")
        plt.draw()
        sleep(delaytime)    # wait for next point
        t.append(t[i] + delaytime)   # increment time counter
        i += 1
    except KeyboardInterrupt:
        plt.close()
        dq.close()
        break
