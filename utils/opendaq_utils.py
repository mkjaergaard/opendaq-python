#!/usr/bin/env python

from opendaq import *
import time
import numpy as np
from distutils.util import strtobool
import argparse


def user_yes_no_query(question):
    print '%s [y/n]\n' % question
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            print "Please respond with \'y\' or \'n\'.\n"


def set_user_voltages(iterations):
    for i in range(iterations):
        print "\n", i + 1, "/", iterations, " Set new voltage:"
        dq.set_analog(float(raw_input()))


def reset_calibration():
    print "\n------------------------------\n"
    print "Resetting calibrations..."

    for i in range(len(dq.model.dac_calib)):
        dq.model.dac_calib[i].gain = 1.0
        dq.model.dac_calib[i].offset = 0

    for i in range(len(dq.model.adc_calib)):
        dq.model.adc_calib[i].gain = 1.0
        dq.model.adc_calib[i].offset = 0

    dq.save_calibration()


def load_dac_from_file():
    print "\n------------------------------\n"
    print "Load DAC calibration from file:"

    x = []
    y = []

    with open(args.dac_file, 'r+') as f:
        for line in f:
            a = [float(s) for s in line.split()]
            if len(a) == 2:
                x.append(a[0])
                y.append(a[1])

    new_corr, new_offset = np.polyfit(x, y, 1)

    dq.model.dac_calib[0].gain *= new_corr
    dq.model.dac_calib[0].offset += new_offset

    dq.save_calibration('DAC')

    file_log("\r\nLoad values from file:\nx=")
    for i in range(len(x)):
        file_log("%1.1f " % x[i])
    file_log("\ny=")
    for i in range(len(y)):
        file_log("%1.4f " % y[i])

    print "DAC:\nm=%1.3f\n" % dq.model.dac_calib[0].gain
    print "b=%1.3f\r\n" % dq.model.dac_calib[0].offset

    file_log("DAC:\nm=%1.3f\n" % dq.model.dac_calib[0].gain)
    file_log("b=%1.3f\r\n" % dq.model.dac_calib[0].offset)


def calculate_adc_offsets():
    print "\n------------------------------\n"
    print "ADC CALIBRATION - Offset calculation:\n"

    dq.set_analog(0)
    print "0 Volts -->\n"

    offsets_ampli = []
    for canal in dq.model.adc.pinputs:
        print "\nAIN", canal, ":"
        a = []
        b = []
        c = []
        for i in range(len(dq.model.adc.pga_gains)):
            dq.conf_adc(canal, 0, i)
            dq.read_adc()
            time.sleep(0.05)
            a.append(dq.model.adc.pga_gains[i])
            b.append(dq.read_adc())
            c.append(dq.read_analog())
            print "x%0.2f" % a[i], b[i], "%0.4f" % c[i]
        new_corr, new_offset = np.polyfit(a, b, 1)
        print "\r\n%0.2f" % new_corr, "%0.2f" % new_offset
        dq.model.adc_calib[canal - 1] = dq.model.adc_calib[canal - 1]._replace(offset=new_offset)
        if dq.hw_ver == "[N]":
            index = len(dq.model.adc.pinputs) + canal - 1
            dq.model.adc_calib[index] = dq.model.adc_calib[index]._replace(offset=new_corr)
        offsets_ampli.append(new_offset)

    if dq.hw_ver == "[M]":
        off_ampli = np.mean(offsets_ampli)
        for gain_range in range(len(dq.model.adc.pga_gains)):
            index = len(dq.model.adc.pinputs) + gain_range - 1
            dq.model.adc_calib[index] = dq.model.adc_calib[index]._replace(offset=off_ampli)

    dq.save_calibration('ADC')


def calculate_adc_gains():
    print "\n------------------------------\n"
    print "ADC CALIBRATION - Gain calculation:\n"

    dq.set_analog(1)
    for i in dq.model.adc.pinputs:
        dq.conf_adc(i, 0, 0)
        dq.read_adc()
        time.sleep(0.05)
        value = dq.read_analog()
        dq.model.adc_calib[i - 1] = dq.model.adc_calib[i - 1]._replace(gain=value)
        print i, "-->", "%0.4f" % value

    for ampli in range(len(dq.model.adc.pga_gains)):
        volts = 1./dq.model.adc.pga_gains[ampli]
        dq.set_analog(volts)
        a = []
        for ch in dq.model.adc.pinputs:
            dq.conf_adc(ch, 0, ampli)
            dq.read_adc()
            time.sleep(0.05)
            value = dq.read_analog()
            a.append(value/volts)
        index = len(dq.model.adc.pinputs) + ampli - 1
        dq.model.adc_calib[index] = dq.model.adc_calib[index]._replace(gain=np.mean(a))

    dq.save_calibration('ADC')


    corrs = [1]*dq.model.adc_slots
    offsets = [1]*dq.model.adc_slots

    for i in range(dq.model.adc_slots):
        corrs[i], offsets[i] = dq.model.adc_calib[i]

    print "ADC calibration:\nm= ", corrs, "\n"
    print "b= ", offsets, "\n"

    file_log("\r\n\nADC calibration:\nm= [")
    for i in range(len(dq.model.adc_slots)):
        file_log("%1.4f " % dq.model.adc_calib[i].gain)
    file_log("]\nb= [")
    for i in range(len(dq.model.adc_slots)):
        file_log("%1.1f " % dq.model.adc_calib[i].offset)
    file_log("]\r\n")


def calculate_se_calibration():
    print "\n------------------------------\n"
    print "ADC CALIBRATION - SE mode:\n"
    volts = [1, 2, 3, 4]

    for i in dq.model.adc.pinputs:
        print "\nAIN", i, ":"
        dq.conf_adc(i, 0)
        a = []
        b = []
        for j in volts:
            dq.set_analog(j)
            dq.read_adc()
            raw = dq.read_adc()
            value = dq.read_analog()
            a.append(raw)
            b.append(value)
            print j, "V-->", raw, " == ", value
        new_corr, new_offset = np.polyfit(volts, b, 1)
        print "m:", new_corr
        dq.model.adc_calib[i - 1] = dq.model.adc_calib[i - 1]._replace(gain=new_corr)
        new_corr, new_offset = np.polyfit(volts, a, 1)
        print "b:", new_offset
        dq.model.adc_calib[i - 1] = dq.model.adc_calib[i - 1]._replace(offset=new_offset)

    dq.save_calibration('ADC')

    file_log("ADC /SE mode:\nm= [")
    for i in dq.model.pinput_range:
        file_log("%1.4f " % adc_corrs[i - 1])
    file_log("]\nb= [")
    for i in dq.model.pinput_range:
        file_log("%1.1f " % adc_offsets[i - 1])
    file_log("]\r\n")


def calculate_de_calibration():
    print "\n------------------------------\n"
    print "ADC CALIBRATION - DE mode:\n"

    pinputs = [1, 2, 3, 4, 5, 6, 7, 8]
    ninputs = [2, 1, 4, 3, 6, 5, 8, 7]

    dq.set_analog(0)

    for i in range(len(pinputs)):
        dq.conf_adc(pinputs[i], ninputs[i])
        print "\nAIN", pinputs[i], ninputs[i], ":"
        dq.read_adc()
        raw = dq.read_adc()
        index = len(self.adc.pinputs) + i - 1
        dq.model.adc_calib[index] = dq.model.adc_calib[index]._replace(offset=raw)

    dq.save_calibration('ADC')
    print "\nNew ADC coefficients (DE): \n", dq.get_adc_cal()

    file_log("ADC /DE mode:\nm= [")
    for i in range(len(pinputs)):
        file_log("%1.4f " % adc_corrs[i])
    file_log("]\nb= [")
    for i in range(len(pinputs)):
        file_log("%1.1f " % adc_offsets[i])
    file_log("]\r\n")


def exec_dac_test():
    print "\n------------------------------\n"
    print "DAC CALIBRATION TEST\n"

    file_log("\r\nDAC CALIBRATION TEST:\n")

    if dq.hw_ver == "[S]":
        volts = [1, 2, 3]
    else:
        volts = [-3, -1, 1, 3]

    for i in volts:
        dq.set_analog(i)
        print "\n Setting", i, " Volts..."
        file_log("\nSet DAC= %1.1fV -> " % i)
        time.sleep(.5)
        if user_yes_no_query("Is the voltage correct?"):
            file_log("OK")
        else:
            file_log("ERROR")


def exec_adc_test():
    print "\n------------------------------\n"
    print "ADC CALIBRATION TEST\n"

    file_log("\r\n\nADC CALIBRATION TEST:\n")

    if dq.hw_ver == "[S]":
        for i in dq.model.adc.pinputs:
            dq.conf_adc(i, 0)
            print "\n", i
            file_log("\nA%d:\n" % i)
            for j in [0, 1, 2, 3, 4]:
                dq.set_analog(j)
                dq.read_adc()
                value = dq.read_analog()
                print j * 1.0, "--> ", value, "## Error:","%0.2f" % (abs(100 * (value - j) / 12.)), "%"
                file_log("%1.1f V set --> " % j)
                file_log("%1.3f V read ## Error:" % value)
                file_log("%0.2f%%\n" % (abs(100 * (value - j) / 12.)))
    elif dq.hw_ver == "[N]":
        for ampli in range(len(dq.model.adc.pga_gains)):
            print "\nGain range:", ampli, "-> x", "%0.3f" % dq.model.adc_base_ampli[ampli], "\n"
            file_log("\nGain range: x%0.2f\n" % dq.model.adc.pga_gains[ampli])
            volts = 2. / dq.model.adc.pga_gains[ampli]
            max_reference = 12. / dq.model.adc.pga_gains[ampli]
            # volts = 0
            print "%0.2f" % volts, "Volts -->\n"
            file_log("V set =  %1.3f\n" % volts)
            dq.set_analog(volts)
            for i in dq.model.adc.pinputs:
                dq.conf_adc(i, 0, ampli)
                dq.read_adc()
                time.sleep(0.05)
                value = dq.read_analog()
                print i, "-->", "%0.4f" % value, "## Error:", "%0.2f" % (abs(100 * (value - volts) / max_reference)), "%"
                ("A%d:  " % i)
                file_log("%1.3f V read ## Error:" % value)
                file_log("%0.2f%%\n" % (abs(100 * (value - volts) / max_reference)))
            file_log("\n")
    else:
        for ampli in range(len(dq.model.adc.pga_gains)):
            print "\nGain range:",ampli, "-> x", "%0.2f" % dq.model.adc.pga_gains[ampli], "\n"
            file_log("\nGain range: x%0.2f\n" % dq.model.adc.pga_gains[ampli])
            volts = 1. / dq.model.adc.pga_gains[ampli]
            max_reference = min(12., 12. / dq.model.adc.pga_gains[ampli])
            print "%0.2f" % volts, "Volts -->\n"
            dq.set_analog(volts)
            for i in dq.model.pinput_range:
                dq.conf_adc(i, 0, ampli)
                dq.read_adc()
                time.sleep(0.05)
                value = dq.read_analog()
                print i, "-->", "%0.4f" % value, "## Error:","%0.2f" % (abs(100 * (value - volts) /  max_reference)), "%"
                file_log("A%d: " % i)
                file_log("%1.3f V set --> " % volts)
                file_log("%1.3f V read ## Error:" % value)
                file_log("%0.2f%%\n" % (abs(100 * (value - volts) / max_reference)))        
            file_log("\n")


def exec_pio_test():
    print "\n------------------------------\n"
    print "\r\nPIO TEST:\r\n"
    file_log("\nPIO TEST:\r\n")

    dq.set_port_dir(0)
    for i in range(1, 7):
        dq.set_pio_dir(i, 1)
        dq.set_pio(i, 0)
        port_down = dq.read_port()
        dq.set_pio(i, 1)
        port_up = dq.read_port()
        dq.set_pio_dir(i, 0)
        if (port_down == 0) and (port_up == 63):
            print "PIO", i, "OK"
            file_log("PIO%d OK\n" % i)
        else:
            print "PIO", i, "ERROR -> 0 |", port_down, " 63 |", port_up
            file_log("PIO%d ERROR\n" % i)



parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("-df", "--dac_file", default="calibration.txt",
                    help="Select file for loading DAC calibration (default calibration.txt)")
parser.add_argument("-p", "--port", default="COM3",
                    help="Select serial port name (default COM3)")
parser.add_argument("-s", "--serial", type=int, help="Set serial number")
parser.add_argument("-r", "--reset", help="Reset calibration", action="store_true")
parser.add_argument("-o", "--report", help="Generate report file", action="store_true")
parser.add_argument("-c", "--calibrate", help="Calculate new device calibration", action="store_true")
parser.add_argument("-t", "--test", help="Test hardware", action="store_true")
group.add_argument("-v", "--set_voltage", help="Test voltages", action="count")


args = parser.parse_args()

dq = DAQ(args.port)
time.sleep(.05)

if args.serial:
    dq.set_id(args.serial)
    dq.close()
    dq = DAQ(args.port)
    time.sleep(.05)

print "## OPENDAQ " + dq.hw_ver + " UTILS ##\n"
print dq 

if args.report:
    outputname = './REPORT_' + dq.model.serial_str + '_' + time.strftime('%y%m%d') + '.txt'
    outputfile = open(outputname, 'w')
    print "\nOutput file: ", outputname

    def file_log(text):
        outputfile.write(text)

else:
    def file_log(text):
        pass

file_log("### CALIBRATION REPORT ###\r\n")
file_log(time.strftime('Date: %d/%m/%Y\nTime: %X\r\n'))
file_log("Serial number: %s\r\n" % dq.model.serial_str)
file_log("Hardware Version: %s\n" % dq.model.model_str)
file_log("Firmware Version: %d\r\n" % dq.model.fw_ver)

if args.reset or args.calibrate:
    reset_calibration()

if args.calibrate:
    load_dac_from_file()
    if dq.hw_ver == "[S]":
        calculate_se_calibration()
        calculate_de_calibration()
    else:
        calculate_adc_offsets()
        calculate_adc_gains()

if args.set_voltage > 0:
    set_user_voltages(args.set_voltage)

if args.test:
    exec_dac_test()
    exec_adc_test()
    exec_pio_test()

if args.report:
    outputfile.close()

dq.close()
