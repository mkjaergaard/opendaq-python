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


from __future__ import division
from collections import namedtuple
from enum import IntEnum
import time


CalibReg = namedtuple('CalibReg', ['gain', 'offset'])
DAC = namedtuple('DAC', ['bits', 'vmin', 'vmax'])
ADC = namedtuple('ADC', ['bits', 'vmin', 'vmax', 'pga_gains',
                         'pinputs', 'ninputs'])


class PGAGains(IntEnum):
    """A wrapper around IntEnum for defining the gain values of a PGA."""
    @classmethod
    def new(cls, values):
        def val_str(val):
            if 0 < val < 1:
                return 'x0%s' % str(val)[2:4]
            return 'x%d' % val

        a = cls('Gains', [val_str(v) for v in values], start=0)
        a.values = values
        return a


class DAQModel(object):
    """Base class for defining OpenDAQ models by inheritance."""
    _id = 0

    def __init__(self, fw_ver, serial, model_str='', serial_fmt='%d',
                 adc=None, dac=None, adc_slots=0, dac_slots=0,
                 npios=0, nleds=0):
        assert type(adc) is ADC, "adc argument must be an instance of ADC class"
        assert type(dac) is DAC, "dac argument must be an instance of DAC class"

        self.fw_ver = fw_ver
        self.serial = serial
        self.model_str = model_str
        self.serial_fmt = serial_fmt
        self.npios = npios
        self.nleds = nleds
        self.dac = dac
        self.adc = adc

        # Create the calibration slots
        self.adc_calib = [CalibReg(1., 0.)]*adc_slots
        self.dac_calib = [CalibReg(1., 0.)]*dac_slots

        if self.fw_ver < 130:
            raise ValueError('Invalid firmware version. Please update the firmware!')

    @property
    def serial_str(self):
        return self.serial_fmt % self.serial

    # def dac_coef_range(self):
        # return list(range(self.dac_slots))

    # def adc_coef_range(self, flag):
        # return list(range(self.dac_slots, self.dac_slots + self.adc_slots))

    def load_calibration(self, read_slot):
        """Load calibration values.
        :param read_slot: Callback function that returns the raw
            calibration values (gain and offset) of a slot, given its index.
        """

        time.sleep(.05)
        # print "DAC slots read:"
        for i in range(len(self.dac_calib)):
            s, gain, offset = read_slot(i)
            # print i, "<<", gain, offset
            self.dac_calib[i] = CalibReg(1. + gain/2.**16, offset/2.**16)

        time.sleep(.05)
        # print "ADC slots read:"
        for i in range(len(self.adc_calib)):
            s, gain, offset = read_slot(i + len(self.dac_calib))
            # print i, "<<", gain, offset            
            self.adc_calib[i] = CalibReg(1. + gain/2.**16, offset/2.**5)

    def save_calibration(self, write_slot, flag):
        """Save calibration values in device EEPROM.
        :param write_slot: Callback function that executes the writing of the 
            calibration values (gain and offset) in a slot, given its index.
        """
        if flag != 'ADC':
            time.sleep(.05)
            # print "DAC slots write:"
            for i in range(len(self.dac_calib)):
                valuem = int(round((self.dac_calib[i].gain - 1) * (2.**16)))
                valueb = int(round(self.dac_calib[i].offset * (2.**16)))
                # print i, ">>", valuem, valueb
                write_slot(i, valuem, valueb)

        if flag != 'DAC':
            time.sleep(.05)
            # print "ADC slots write:"
            for i in range(len(self.adc_calib)):
                valuem = int(round((self.adc_calib[i].gain - 1) * (2.**16)))
                valueb = int(round(self.adc_calib[i].offset * (2.**5)))
                # print i, ">>", valuem, valueb
                write_slot(i + len(self.dac_calib), valuem, valueb)


    def check_pio(self, number):
        if not (1 <= number <= self.npios):
            raise ValueError("PIO number out of range")

    def check_port(self, value):
        if not (0 <= value < 2**(self.npios + 1)):
            raise ValueError("Port number out of range")

    def check_adc_settings(self, pinput, ninput, gain):
        if pinput not in self.adc.pinputs:
            raise ValueError("Invalid positive input selection")
        if ninput not in self.adc.ninputs:
            raise ValueError("Invalid negative input selection")
        if not gain in range(len(self.adc.pga_gains)):
            raise ValueError("Invalid gain selection")

    def _get_adc_slots(self, gain_id, pinput, ninput):
        """Return the indexes of the two ADC's calibration slots.
        The second one is affected by the PGA gain.
        :param gain_id: ID of the analog configuration setup.
        :param pinput: Positive input.
        :param ninput: Negative input.
        :returns: Value in volts.
        """
        raise NotImplementedError

    def raw_to_volts(self, raw, gain_id, pinput, ninput=0):
        """
        Convert a raw value to a value in volts.
        Device calibration values are used for the calculation.

        :param raw: Value to convert to volts.
        :param gain_id: ID of the analog configuration setup.
        :param pinput: Positive input.
        :param ninput: Negative input.
        :returns: Value in volts.
        """
        # obtain the calibration gains and offsets
        slot1, slot2 = self._get_adc_slots(gain_id, pinput, ninput)
        gain1, offs1 = (1., 0.) if slot1 < 0 else self.adc_calib[slot1]
        gain2, offs2 = (1., 0.) if slot2 < 0 else self.adc_calib[slot2]

        adc_gain = 2.**(self.adc.bits-1)/self.adc.vmax
        pga_gain = self.adc.pga_gains[gain_id]

        gain = adc_gain*pga_gain*gain1*gain2
        offset = offs1*pga_gain + offs2
        return (raw - offset)/gain


    def __check_dac_value(self, volts):
        if not (self.dac.vmin <= volts <= self.dac.vmax):
            raise ValueError("DAC voltage out of range")

    def volts_to_raw(self, volts, number):
        """Convert a value in volts to a raw value.
        Device calibration values are used for the calculation.

        :param volts: Value to convert to raw.
        :param number: Calibration slot of the DAC.
        :returns: Raw value.
        :raises: ValueError: DAC voltage out of range
        """
        self.__check_dac_value(volts)

        try:
            gain, offset = self.dac_calib[number]
        except IndexError:
            raise IndexError('Invalid DAC number')

        base_gain = self.dac.vmax/2**(self.dac.bits-1)
        raw = int(round((volts-offset)/(gain*base_gain)))

        # clamp value between DAC limits
        return max(-1<<(self.dac.bits-1), min(raw, (1<<(self.dac.bits-1))-1))

    @classmethod
    def new(cls, model_id, fw_ver, serial):
        """Factory method for instantiating subclasses of DAQModel."""
        for model in cls.__subclasses__():
            if model._id == model_id:
                return model(fw_ver, serial)
        raise ValueError("Unknown model ID")
