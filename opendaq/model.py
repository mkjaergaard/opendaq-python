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
from collections import namedtuple

ADC = namedtuple('ADC', ['bits', 'vmin', 'vmax', 'pga_gains',
                         'pinputs', 'ninputs'])
DAC = namedtuple('ADC', ['bits', 'vmin', 'vmax'])

CalibReg = namedtuple('CalibReg', ['gain', 'offset'])


class MGains(IntEnum):
    """Valid PGA gains in model M."""
    X033 = 0
    X1 = 1
    X2 = 2
    X10 = 3
    X100 = 4

class SGains(IntEnum):
    """Valid PGA gains in model S."""
    X1 = 0
    X2 = 1
    X4 = 2
    X5 = 3
    X8 = 4
    X10 = 5
    X16 = 6
    X20 = 7

class TP04Gains(IntEnum):
    """Valid PGA gains in model TP8."""
    X1 = 0
    X2 = 1
    X4 = 2
    X8 = 3
    X16 = 4
    X32 = 5
    X64 = 6
    X128 = 7

TP04Gains = NGains = SGains


class DAQModel(object):
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
        self.dac = dac
        self.adc = adc
        self.npios = npios
        self.nleds = nleds

        self.adc_calib = [CalibReg(1., 0.)]*adc_slots
        self.dac_calib = [CalibReg(1., 0.)]*adc_slots

        if self.fw_ver < 130:
            raise ValueError('Invalid firmware version. Please update the firmware!')

    @property
    def serial_str(self):
        return self.serial_fmt % self.serial

    # def device_info(self):
        # print("Hardware Version:", self.model_str)
        # print("Firmware Version:", self.fw_ver)
        # print("Serial number:", self.serial_str)

    # def dac_coef_range(self):
        # return list(range(self.dac_slots))

    # def adc_coef_range(self, flag):
        # return list(range(self.dac_slots, self.dac_slots + self.adc_slots))

    # def check_pio(self, number):
        # if not (1 <= number <= self.npios):
            # raise ValueError("PIO number out of range")

    # def check_port(self, value):
        # if not (0 <= value < 2**(self.npios + 1)):
            # raise ValueError("Port number out of range")

    def check_adc_settings(self, pinput, ninput, gain):
        if pinput not in self.adc.pinputs:
            raise ValueError("Invalid positive input selection")
        if ninput not in self.adc.ninputs:
            raise ValueError("Invalid negative input selection")
        if not gain in range(len(self.adc.pga_gains)):
            raise ValueError("Invalid gain selection")

    def _get_adc_slots(self, gain_id, pinput, ninput):
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

        if not 0 < number <= len(self.dac_calib):
            raise ValueError('Invalid DAC number')

        gain, offset = self.dac_calib[number-1]

        base_gain = self.dac.vmax/(1<<self.dac.bits)
        raw = int(round((volts-offset)/(gain*base_gain)))

        # clamp value between DAC limits
        return max(-1<<(self.dac.bits-1), min(raw, (1<<(self.dac.bits-1))-1))


class ModelM(DAQModel):
    _id = 1

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial, model_str='[M]', serial_fmt='ODM08%03d7',
            adc_slots=13, dac_slots=1, npios=6, nleds=1,
            dac=DAC(bits=16, vmin=-4.096, vmax=4.095),
            adc=ADC(bits=16, vmin=-4.096, vmax=4.095,
                    pga_gains=[1./3, 1, 2, 10, 100],
                    pinputs=list(range(1, 9)),
                    ninputs=[0, 5, 6, 7, 8, 25])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        return pinput - 1, len(self.adc.pinputs) + gain_id


class ModelS(DAQModel):
    _id = 2

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial, model_str='[S]', serial_fmt="ODS08%03d7",
            adc_slots=16, dac_slots=1, npios=6, nleds=1,
            dac=DAC(bits=16, vmin=0.0, vmax=4.095),
            adc=ADC(bits=16, vmin=-12.0, vmax=12.0,
                    pga_gains=[1, 2, 4, 5, 8, 10, 16, 20],
                    pinputs=list(range(1, 9)),
                    ninputs=[0])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        offs = 0 if ninput == 0 else 8
        return pinput - 1 + offs, -1


class ModelN(DAQModel):
    _id = 3

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial, model_str='[N]', serial_fmt='ODN08%03d7',
            adc_slots=16, dac_slots=1, npios=6, nleds=1,
            dac=DAC(bits=16, vmin=-4.096, vmax=4.095),
            adc=ADC(bits=16, vmin=-12.288, vmax=12.288,
                    pga_gains=[1, 2, 4, 5, 8, 10, 16, 20],
                    pinputs=list(range(1, 9)),
                    ninputs=list(range(0, 9)))
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        n = pinput - 1
        return n, len(self.adc.pinputs) + n


class ModelTP08(DAQModel):
    _id = 10

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial, model_str='TP08', serial_fmt='TP08x10%04d',
            adc_slots=8, dac_slots=4, npios=4, nleds=8,
            dac=DAC(bits=16, vmin=-1.25, vmax=1.25),
            adc=ADC(bits=16, vmin=-23.75, vmax=23.75,
                    pga_gains=[1, 2, 4, 8, 16, 32, 64, 128],
                    pinputs=[1, 2, 3, 4], ninputs=[0])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        n = pinput - 1
        return n, len(self.adc.pinputs) + n


class ModelTP04(DAQModel):
    _id = 11

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial, model_str='TP04', serial_fmt='TP04x10%04d',
            adc_slots=4, dac_slots=2, npios=2, nleds=4,
            dac=DAC(bits=16, vmin=-1.25, vmax=1.25),
            adc=ADC(bits=16, vmin=-24.0, vmax=24.0,
                    pga_gains=[1, 2, 4, 5, 8, 10, 16, 20],
                    pinputs=[1, 2], ninputs=[0])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        n = pinput - 1
        return n, len(self.adc.pinputs) + n


def get_model(model_id, fw_ver, serial):
    for model in DAQModel.__subclasses__():
        if model._id == model_id:
            return model(fw_ver, serial)
    raise ValueError("Unknown model ID")
