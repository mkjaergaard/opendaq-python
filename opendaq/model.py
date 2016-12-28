#!/usr/bin/env python

# Copyright 2016
# Ingen10 Ingenieria SL
#
# This file is part of opendaq.
#
# opendaq is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# opendaq is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with opendaq.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division
from enum import IntEnum


class PGAGain(IntEnum):
    """Valid PGA gains."""
    X033 = 0
    X1 = 1
    X2 = 2
    X10 = 3
    X100 = 4
    S_X1 = 0
    S_X2 = 1
    S_X4 = 2
    S_X5 = 3
    S_X8 = 4
    S_X10 = 5
    S_X16 = 6
    S_X20 = 7


class DAQModel(object):
    _id = 0

    def __init__(self, fw_ver, serial):
        self.serial = serial
        self.fw_ver = fw_ver
        if self.fw_ver < 130:
            raise ValueError('Invalid firmware version. Please update device!')

    def device_info(self):
        print("Hardware Version:", self.model_str)
        print("Firmware Version:", self.fw_ver)
        print("Serial number:", self.serial_str)

    def adc_gain_range(self):
        return list(range(len(self.adc_base_ampli)))

    def dac_coef_range(self):
        return list(range(0, self.dac_slots))

    def adc_coef_range(self, flag):
        return list(range(self.dac_slots, self.dac_slots + self.adc_slots))

    def check_valid_pio(self, number):
        if not (1 <= number <= self.pio_slots):
            raise ValueError("PIO number out of range")

    def check_valid_port(self, value):
        if not (0 <= value < 2**(self.pio_slots + 1)):
            raise ValueError("Port number out of range")

    def check_valid_dac_value(self, volts):
        if not (self.min_dac_value <= volts <= self.max_dac_value):
            raise ValueError("DAC voltage out of range")

    def check_valid_adc_settings(self, pinput, ninput, xgain):
        if pinput not in self.pinput_range:
            raise ValueError("Invalid positive input selection")
        if ninput not in self.ninput_range:
            raise ValueError("Invalid negative input selection")
        if xgain not in self.adc_gain_range():
            raise ValueError("Invalid gain selection")

    def volts_to_raw(self, volts, number):
        """Convert a value in volts to a raw value.
        Device calibration values are used for the calculation.

         - openDAQ[M] range: -4.096 V to +4.096 V
         - openDAQ[S] range: 0 V to +4.096 V

        :param volts: Value to convert to raw.
        :returns: Raw value.
        :raises: ValueError: DAC voltage out of range
        """
        self.check_valid_dac_value(volts)

        if number not in self.dac_coef_range():
            raise ValueError('DAC calibration slot out of range')

        corr = self.dac_gains[number]
        offset = self.dac_offsets[number]

        raw = int(round((volts-offset)/(corr*self.dac_base_gain)))
        # print self.dac_gains, self.dac_offsets
        # print raw,"= (",volts,"-",offset,"/(",corr,"*",self.dac_base_gain,")"
        return max(-32768, min(raw, 32767))  # clamp value


class ModelM(DAQModel):
    _id = 1

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(self, fw_ver, serial)
        self.model_str = "[M]"
        self.serial_str = "ODM08%03d7" % self.serial

        self.pio_slots = 6
        self.adc_slots = 13
        self.adc_gains = []
        self.adc_offsets = []
        self.adc_base_ampli = [1. / 3, 1, 2, 10, 100]
        self.adc_base_gain = 32768 / 4.096
        self.min_adc_value = -4.096
        self.max_adc_value = 4.095

        self.pinput_range = list(range(1, 9))
        self.ninput_range = [0, 5, 6, 7, 8, 25]

        self.dac_slots = 1
        self.dac_gains = []
        self.dac_offsets = []
        self.dac_base_gain = 4.096 / 32768.
        self.min_dac_value = -4.096
        self.max_dac_value = 4.095

    def raw_to_volts(self, raw, gain_id, pinput, ninput=0):
        """
        Convert a raw value to a value in volts.

        :param raw: Value to convert to volts.
        :param gain_id: ID of the analog configuration setup.
        """
        base_gain = 1. / (self.adc_base_gain * self.adc_base_ampli[gain_id])

        adc_chp_slot = pinput-1
        adc_gain_slot = len(self.pinput_range)+gain_id

        gain = 1./(self.adc_gains[adc_chp_slot] *
                   self.adc_gains[adc_gain_slot])
        offset = (self.adc_offsets[adc_chp_slot] *
                  self.adc_base_ampli[gain_id] +
                  self.adc_offsets[adc_gain_slot])

        return round((raw - offset) * base_gain * gain, 5)


class ModelS(DAQModel):
    _id = 2

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(self, fw_ver, serial)
        self.model_str = "[S]"
        self.serial_str = "ODS08%03d7" % self.serial

        self.pio_slots = 6
        self.adc_slots = 16
        self.adc_gains = []
        self.adc_offsets = []
        self.adc_base_ampli = [1, 2, 4, 5, 8, 10, 16, 20]
        self.adc_base_gain = 32768 / 12.0
        self.min_adc_value = -12.0
        self.max_adc_value = 12.0

        self.pinput_range = list(range(1, 9))
        self.ninput_range = [0]

        self.dac_slots = 1
        self.dac_gains = []
        self.dac_offsets = []
        self.dac_base_gain = 4.096 / 32768.
        self.min_dac_value = 0
        self.max_dac_value = 4.095

    def raw_to_volts(self, raw, gain_id, pinput, ninput=0):
        """Convert a raw value to a value in volts.

        :param raw: Value to convert to volts.
        :param gain_id: ID of the analog configuration setup.
        """
        adc_chp_slot = pinput-1
        if ninput != 0:
            adc_chp_slot += 8
        base_gain = 1./(self.adc_base_gain * self.adc_base_ampli[gain_id])
        gain = self.adc_gains[adc_chp_slot]
        offset = self.adc_offsets[adc_chp_slot]
        return round((raw - offset) * base_gain / gain, 4)

    def check_valid_adc_settings(self, pinput, ninput, xgain):
        if pinput not in self.pinput_range:
            raise ValueError("Invalid positive input selection")
        if xgain not in self.adc_gain_range():
            raise ValueError("Invalid gain selection")
        if xgain > 0 and ninput == 0:
            raise ValueError("Invalid gain selection")
        if ninput != 0 and (pinput % 2 == 0 and ninput != pinput - 1
                            or pinput % 2 != 0 and ninput != pinput + 1):
                    raise ValueError("Invalid negative input selection")

    def adc_coef_range(self, flag):
        if flag == 'SE':
            return list(range(self.dac_slots, self.dac_slots+self.adc_slots / 2))
        elif flag == 'DE':
            return list(range(self.dac_slots + self.adc_slots / 2,
                              self.dac_slots + self.adc_slots))
        elif flag == 'ALL':
            return list(range(self.dac_slots, self.dac_slots+self.adc_slots))
        else:
            raise ValueError("Invalid flag")


class ModelN(DAQModel):
    _id = 3

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(self, fw_ver, serial)
        self.model_str = "[N]"
        self.serial_str = "ODN08%03d7" % self.serial

        self.pio_slots = 6
        self.adc_slots = 16
        self.adc_gains = []
        self.adc_offsets = []
        self.adc_base_ampli = [1, 2, 4, 5, 8, 10, 16, 32]
        self.adc_base_gain = 32768 / 12.288   # 6 * 2.048
        self.min_adc_value = -4.096
        self.max_adc_value = 4.095

        self.pinput_range = list(range(1, 9))
        self.ninput_range = list(range(0, 9))

        self.dac_slots = 1
        self.dac_gains = []
        self.dac_offsets = []
        self.dac_base_gain = 4.096/32768.
        self.min_dac_value = -4.096
        self.max_dac_value = 4.095

    def raw_to_volts(self, raw, gain_id, pinput, ninput=0):
        """
        Convert a raw value to a value in volts.

        :param raw: Value to convert to volts.
        :param gain_id: ID of the analog configuration setup.
        """
        base_gain = 1. / (self.adc_base_gain * self.adc_base_ampli[gain_id])

        adc_chp_slot = pinput - 1

        gain = 1. / (self.adc_gains[adc_chp_slot])
        offset = (self.adc_offsets[adc_chp_slot] *
                  self.adc_base_ampli[gain_id] +
                  self.adc_offsets[adc_chp_slot + 8])

        return round((raw - offset) * base_gain * gain, 5)


class ModelTP8(DAQModel):
    _id = 10

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(self, fw_ver, serial)
        self.model_str = "TP8x"
        self.serial_str = "TP8x10%04d" % self.serial
        self.pio_slots = 6

        self.adc_slots = 12
        self.adc_gains = []
        self.adc_offsets = []
        self.adc_base_ampli = [1, 2, 4, 8, 16, 32, 64, 128]
        self.adc_base_gain = 32768/23.75
        self.min_adc_value = -23.75
        self.max_adc_value = 23.75

        self.pinput_range = list(range(1, 4))
        self.ninput_range = [0]

        self.dac_slots = 4
        self.dac_gains = []
        self.dac_offsets = []
        self.dac_base_gain = 1.25/32768.
        self.min_dac_value = -1.25
        self.max_dac_value = 1.25

    def raw_to_volts(self, raw, gain_id, pinput, ninput=0):
        """Convert a raw value to a value in volts.

        :param raw: Value to convert to volts.
        :param gain_id: ID of the analog configuration setup.
        """
        base_gain = 1./(self.adc_base_gain * self.adc_base_ampli[gain_id])
        gain = 1./(self.adc_gains[pinput-1] * self.adc_gains[4+gain_id])
        offset = (self.adc_offsets[pinput-1] * self.adc_base_ampli[gain_id] +
                  self.adc_offsets[4+gain_id])
        return (raw - offset)*base_gain*gain


def get_model(model_id, fw_ver, serial):
    for model in DAQModel.__subclasses__():
        if model._id == model_id:
            return model(fw_ver, serial)
    raise ValueError("Unknown model ID")
