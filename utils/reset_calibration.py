from opendaq import *
import time

dq = DAQ("COM3")
time.sleep(.05)

dac_corrs = [1.0] * dq.model.dac_slots
dac_offsets = [0] * dq.model.dac_slots
adc_corrs = [1.0] * dq.model.adc_slots
adc_offsets = [0] * dq.model.adc_slots

print dq.model.adc_slots

print "\nResetear DAC calibraciones: \n",dq.set_dac_cal(dac_corrs,dac_offsets)
print "\nResetear ADC calibraciones: \n",dq.set_adc_cal(adc_corrs,adc_offsets)
time.sleep(1)

dq.close()
