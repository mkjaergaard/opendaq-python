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
print new_corr, new_offset

		
dq = DAQ("COM3")
time.sleep(.05)

print "## OPENDAQ [M] FULL TEST ##\n"
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
print new_corr, new_offset

dac_corr[channel] *= new_corr
dac_offset[channel] += new_offset 

dq.set_dac_cal(dac_corr,dac_offset)
dq.get_dac_cal()

outputfile.write("DAC:\nm=%1.3f\n"%new_corr)
outputfile.write("b=%1.3f\r\n"%new_offset)




print "\n------------------------------\n"
print "ADC CALIBRATION - Offset calculation:\n"

dq.set_analog(0)
print "0 Volts -->\n"

offsets_chp = []
offsets_ampli = []
temp = []
for canal in dq.model.pinput_range:
    print "\nAIN",canal, ":"
    a = []
    b = []
    c = []
    for i in dq.model.adc_gain_range():
        gain = i
        dq.conf_adc(canal,0,gain)
        time.sleep(0.05)
        a.append(dq.model.adc_base_ampli[i])
        b.append(dq.read_adc())
        c.append(dq.read_analog())
        print i, a[i], b[i], "%0.4f"%c[i]

    new_corr, new_offset = np.polyfit(a, b, 1)
    print "%0.2f"%new_corr, "%0.2f"%new_offset
    offsets_chp.append(new_offset)
    temp.append(new_corr)

offsets_ampli = [np.mean(temp)]*len(dq.model.adc_gain_range())

adc_offsets = offsets_chp + offsets_ampli
adc_corrs = [1.0]*dq.model.adc_slots

dq.set_adc_cal(adc_corrs, adc_offsets)
    
dq.get_adc_cal()

print "\n------------------------------\n"
print "ADC CALIBRATION - Gain calculation:\n"

gains_chp = []
gains_ampli = [1]*len(dq.model.pinput_range)

for ampli in dq.model.adc_gain_range():
    print "\nGain range",ampli, "-> x", "%0.2f"%dq.model.adc_base_ampli[ampli], "\n"
    volts = 1./dq.model.adc_base_ampli[ampli]
    print "%0.2f"%volts, "Volts -->\n"
    dq.set_analog(volts)
    a = []
    for i in dq.model.pinput_range:
        dq.conf_adc(i,0,ampli)
        time.sleep(0.05)
        raw = dq.read_adc()
        value = dq.read_analog()
        a.append(value/volts)
        print i, raw, "-->", "%0.4f"%value, "##", "%0.4f"%(value/volts)
    gains_chp.append(np.mean(a))

print gains_chp

adc_corrs = gains_ampli + gains_chp

dq.set_adc_cal(adc_corrs, adc_offsets)

adc_corrs, adc_offsets = dq.get_adc_cal()

outputfile.write("ADC calibration:\nm= [")
for i in dq.model.adc_slots:
    outputfile.write("%1.4f "%adc_corrs[i])
outputfile.write("]\nb= [")
for i in dq.model.adc_slots:
    outputfile.write("%1.1f "%adc_offsets[i])
outputfile.write("]\r\n") 

    
print "\n------------------------------\n"
print "CALIBRATION TEST\n"

outputfile.write("CALIBRATION TEST:\n")

for ampli in dq.model.adc_gain_range():
    print "\nGain range:",ampli, "-> x", "%0.2f"%dq.model.adc_base_ampli[ampli], "\n"
    outputfile.write("\nGain range:"%ampli)
    volts = 1./dq.model.adc_base_ampli[ampli]
    print "%0.2f"%volts, "Volts -->\n"
    dq.set_analog(volts)
    for i in dq.model.pinput_range:
        dq.conf_adc(i,0,ampli)
        time.sleep(0.05)
        value = dq.read_analog()
        print i, "-->", "%0.4f"%value, "## Error:","%0.2f"%(abs(100*(value-volts)/volts)),"%"
        outputfile.write("\nA%d:\n"%i)
        outputfile.write("%1.1f V set --> "%volts)
        outputfile.write("%1.3f V read ## Error:"%value)
        outputfile.write("%0.2f%%\n"%(abs(100*(value-j)/12.))

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
