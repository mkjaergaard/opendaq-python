#!/usr/bin/env python

from opendaq import *
import time
import sys
import numpy as np
from distutils.util import strtobool

def user_yes_no_query(question):
    print '%s [y/n]\n' % question
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            print "Please respond with \'y\' or \'n\'.\n"


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

new_corr, new_offset = np.polyfit(x, y, 1)



dq = DAQ("COM3")
time.sleep(.05)

print "## OPENDAQ [N] FULL TEST ##\n"
dq.device_info()

refserial = dq.model.serial_str

outputname = './REPORT_'+refserial+'_'+time.strftime('%y%m%d')+'.txt'
outputfile = open(outputname,'w')

outputfile.write("### CALIBRATION REPORT ###\r\n")
outputfile.write(time.strftime('Date: %d/%m/%Y\nTime: %X\r\n'))

outputfile.write("Serial number: %s\r\n"%refserial)
outputfile.write("Hardware Version: %s\n"%dq.model.model_str)
outputfile.write("Firmware Version: %d\r\n"%dq.model.fw_ver)



print "\n------------------------------\n"
print "Resetting calibrations..."

dac_corr = [1.0] * dq.model.dac_slots
dac_offset = [0] * dq.model.dac_slots
adc_corrs = [1.0] * dq.model.adc_slots
adc_offsets = [0] * dq.model.adc_slots

dq.set_dac_cal(dac_corr,dac_offset)
dq.set_adc_cal(adc_corrs,adc_offsets,'SE')
dq.set_adc_cal(adc_corrs,adc_offsets,'DE')
time.sleep(1)
dq.get_adc_cal()




print "\n------------------------------\n"
print "Load DAC calibration from file:"

dac_corr, dac_offset = dq.get_dac_cal()

dac_corr[channel] *= new_corr
dac_offset[channel] += new_offset

dq.set_dac_cal(dac_corr,dac_offset)
dq.get_dac_cal()

outputfile.write("\r\nLoad values from file:\nx=")
for i in range(len(x)):
    outputfile.write("%1.1f "%x[i])
outputfile.write("\ny=")
for i in range(len(y)):
    outputfile.write("%1.4f "%y[i])

print "DAC:\nm=%1.3f\n"%new_corr
print "b=%1.3f\r\n"%new_offset



print "\n------------------------------\n"
print "ADC CALIBRATION - Offset calculation:\n"

dq.set_analog(0)
print "0 Volts -->\n"

offsets_chp = []
offsets_ampli = []

for canal in dq.model.pinput_range:
    print "\nAIN",canal, ":"
    a = []
    b = []
    c = []
    for i in dq.model.adc_gain_range():
        gain = i
        dq.conf_adc(canal,0,gain)
        dq.read_adc()
        time.sleep(0.05)
        a.append(dq.model.adc_base_ampli[i])
        b.append(dq.read_adc())
        c.append(dq.read_analog())
        print "x%0.2f"%a[i], b[i], "%0.4f"%c[i]

    new_corr, new_offset = np.polyfit(a, b, 1)
    print "\r\n%0.2f"%new_corr, "%0.2f"%new_offset
    offsets_chp.append(new_offset)
    offsets_ampli.append(new_corr)


adc_offsets = offsets_ampli + offsets_chp
adc_corrs = [1.0]*dq.model.adc_slots

dq.set_adc_cal(adc_corrs, adc_offsets)

adc_corrs, adc_offsets = dq.get_adc_cal()
print "b= ", adc_offsets, "\n"

print "\n------------------------------\n"
print "ADC CALIBRATION - Gain calculation:\n"


dq.set_analog(1)
for i in dq.model.pinput_range:
    dq.conf_adc(i,0,0)
    dq.read_adc()
    time.sleep(0.05)
    value = dq.read_analog()
    adc_corrs[i-1] = value
    print i,"-->", "%0.4f"%value

print adc_corrs
dq.set_adc_cal(adc_corrs, adc_offsets)
dq.get_adc_cal()

adc_corrs, adc_offsets = dq.get_adc_cal()

print "ADC calibration:\nm= ", adc_corrs, "\n"
print "b= ", adc_offsets, "\n"

outputfile.write("\r\n\nADC calibration:\nm= [")
for i in range(dq.model.adc_slots):
    outputfile.write("%1.4f "%adc_corrs[i])
outputfile.write("]\nb= [")
for i in range(dq.model.adc_slots):
    outputfile.write("%1.1f "%adc_offsets[i])
outputfile.write("]\r\n")


print "\n------------------------------\n"
print "DAC CALIBRATION TEST\n"

outputfile.write("\r\nDAC CALIBRATION TEST:\n")

for i in [-3, -1, 1, 3]:
    dq.set_analog(i)
    print "\n Setting",i," Volts..."
    outputfile.write("\nSet DAC= %1.1fV -> "%i)
    time.sleep(.5)
    if user_yes_no_query("Is the voltage correct?"):
        outputfile.write("OK")
    else:
        outputfile.write("ERROR")        

print "\n------------------------------\n"
print "ADC CALIBRATION TEST\n"

outputfile.write("\r\n\nADC CALIBRATION TEST:\n")

for ampli in dq.model.adc_gain_range():
    print "\nGain range:",ampli, "-> x", "%0.3f"%dq.model.adc_base_ampli[ampli], "\n"
    outputfile.write("\nGain range: x%0.2f\n"%dq.model.adc_base_ampli[ampli])
    volts = 2./dq.model.adc_base_ampli[ampli]
    max_reference = 12./dq.model.adc_base_ampli[ampli]
    # volts = 0
    print "%0.2f"%volts, "Volts -->\n"
    outputfile.write("V set =  %1.3f\n"%volts)
    dq.set_analog(volts)
    for i in dq.model.pinput_range:
        dq.conf_adc(i,0,ampli)
        dq.read_adc()
        time.sleep(0.05)
        value = dq.read_analog()
        print i, "-->", "%0.4f"%value, "## Error:","%0.2f"%(abs(100*(value-volts)/max_reference)),"%"
        outputfile.write("A%d:  "%i)
        outputfile.write("%1.3f V read ## Error:"%value)
        outputfile.write("%0.2f%%\n"%(abs(100*(value-volts)/max_reference)))

print "\n------------------------------\n"
print "\r\nPIO TEST:\r\n"
outputfile.write("\nPIO TEST:\r\n")

dq.set_port_dir(0)
for i in range(1,7):
    dq.set_pio_dir(i,1)
    dq.set_pio(i,0)
    port_down = dq.read_port()
    dq.set_pio(i,1)
    port_up = dq.read_port()
    dq.set_pio_dir(i,0)
    if (port_down == 0) and (port_up == 63):
        print "PIO",i,"OK"
        outputfile.write("PIO%d OK\n"%i)
    else:
        print "PIO",i,"ERROR -> 0 |",port_down," 63 |",port_up
        outputfile.write("PIO%d ERROR\n"%i)

outputfile.close()

dq.close()
