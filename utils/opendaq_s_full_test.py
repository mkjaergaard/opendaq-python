 #!/usr/bin/env python

from opendaq import *
import time
import sys
import numpy as np

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
f.close()


dq = DAQ("COM3")
time.sleep(.05)

print "## OPENDAQ [S] FULL TEST ##\n"
dq.device_info()

refserial = dq.model.serial_str()

outputname = './REPORT_'+refserial+'_'+time.strftime('%y%m%d')+'.txt'
outputfile = open(outputname,'w')

outputfile.write("### CALIBRATION REPORT ###\r\n")
outputfile.write(time.strftime('Date: %d/%m/%Y\nTime: %X\r\n'))

outputfile.write("Serial number: %s\r\n"%refserial)
outputfile.write("Hardware Version: %s\n"%dq.model.hw_ver())
outputfile.write("Firmware Version: %d\r\n"%dq.model.fw_ver())



print "\n------------------------------\n"
print "Resetting calibrations..."

dac_corr = [1.0] * dq.model.dac_slots
dac_offset = [0] * dq.model.dac_slots
adc_corrs = [1.0] * len(dq.model.adc_coef_range('SE'))
adc_offsets = [0] * len(dq.model.adc_coef_range('SE'))

dq.set_dac_cal(dac_corr,dac_offset)
dq.set_adc_cal(adc_corrs,adc_offsets,'SE')
dq.set_adc_cal(adc_corrs,adc_offsets,'DE')
time.sleep(1)
dq.get_adc_cal()




print "\n------------------------------\n"
print "Load DAC calibration from file:"

dac_corr, dac_offset = dq.get_dac_cal()

print new_corr, new_offset

dac_corr[channel] *= new_corr
dac_offset[channel] += new_offset

dq.set_dac_cal(dac_corr,dac_offset)
dq.get_dac_cal()

outputfile.write("DAC:\nm=%1.3f\n"%new_corr)
outputfile.write("b=%1.3f\r\n"%new_offset)




print "\n------------------------------\n"
print "ADC CALIBRATION - SE mode:\n"

volts = [ 1, 2, 3, 4]

for i in dq.model.pinput_range:
    print "\nAIN",i, ":"
    dq.conf_adc(i,0)
    a = []
    b = []
    c = []
    dq.set_analog(0)
    dq.read_adc()
    for j in volts:
        dq.set_analog(j)
        dq.read_adc()
        raw = dq.read_adc()
        value = dq.read_analog()
        a.append(raw)
        b.append(value)
        print j, "V-->", raw, " == ", value
    new_corr, new_offset = np.polyfit(volts, b, 1)
    print "m:",new_corr
    adc_corrs[i-1] = new_corr
    new_corr, new_offset = np.polyfit(volts, a, 1)
    print "b:",new_offset
    adc_offsets[i-1] = new_offset

dq.set_adc_cal(adc_corrs, adc_offsets,'SE')
print "\nNew ADC coefficients (SE): \n", dq.get_adc_cal()

outputfile.write("ADC /SE mode:\nm= [")
for i in dq.model.pinput_range:
    outputfile.write("%1.4f "%adc_corrs[i-1])
outputfile.write("]\nb= [")
for i in dq.model.pinput_range:
    outputfile.write("%1.1f "%adc_offsets[i-1])
outputfile.write("]\r\n")

print "\n------------------------------\n"
print "ADC CALIBRATION - DE mode:\n"

adc_corrs = [1.0] * len(dq.model.adc_coef_range('DE'))
adc_offsets = [0] * len(dq.model.adc_coef_range('DE'))

mycal,myoff = dq.get_adc_cal()


pinputs = [1, 2, 3, 4, 5, 6, 7, 8]
ninputs = [2, 1, 4, 3, 6, 5, 8, 7]

dq.set_analog(0)

for i in range(len(pinputs)):
    dq.conf_adc(pinputs[i],ninputs[i])
    print "\nAIN", pinputs[i], ninputs[i], ":"
    dq.read_adc()
    raw = dq.read_adc()
    adc_offsets[i] = raw
    adc_corrs[i] = mycal[i]
    print "b:",raw

dq.set_adc_cal(adc_corrs, adc_offsets,'DE')
print "\nNew ADC coefficients (DE): \n", dq.get_adc_cal()

outputfile.write("ADC /DE mode:\nm= [")
for i in range(len(pinputs)):
    outputfile.write("%1.4f "%adc_corrs[i])
outputfile.write("]\nb= [")
for i in range(len(pinputs)):
    outputfile.write("%1.1f "%adc_offsets[i])
outputfile.write("]\r\n")

print "\n------------------------------\n"
print "CALIBRATION TEST\n"

outputfile.write("CALIBRATION TEST:\n")
for i in dq.model.pinput_range:
    dq.conf_adc(i,0)
    print "\n",i
    outputfile.write("\nA%d:\n"%i)
    for j in [0, 1, 2, 3, 4]:
        dq.set_analog(j)
        dq.read_adc()
        value = dq.read_analog()
        print j*1.0, "--> ", value, "## Error:","%0.2f"%(abs(100*(value-j)/12.)),"%"
        outputfile.write("%1.1f V set --> "%j)
        outputfile.write("%1.3f V read ## Error:"%value)
        outputfile.write("%0.2f%%\n"%(abs(100*(value-j)/12.)))

print "\nPIO TEST:\r\n"
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
