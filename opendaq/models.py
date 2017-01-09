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
from .daq_model import DAQModel, ADC, DAC, PGAGains
from collections import namedtuple


class Gains:
    M = PGAGains.new([1./3, 1, 2, 10, 100])
    S = PGAGains.new([1, 2, 4, 5, 8, 10, 16, 20])
    N = PGAGains.new([1, 2, 4, 5, 8, 10, 16, 20])
    TP04 = PGAGains.new([1, 2, 4, 5, 8, 10, 16, 20])
    TP08 = PGAGains.new([1, 2, 4, 8, 16, 32, 64, 128])


class ModelM(DAQModel):
    _id = 1

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial,
            model_str='[M]', serial_fmt='ODM08%03d7',
            adc_slots=13, dac_slots=1, npios=6, nleds=1,
            dac=DAC(bits=16, vmin=-4.096, vmax=4.096),
            adc=ADC(bits=16, vmin=-4.096, vmax=4.096,
                    pga_gains=Gains.M.values,
                    pinputs=list(range(1, 9)),
                    ninputs=[0, 5, 6, 7, 8, 25])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        return pinput - 1, len(self.adc.pinputs) + gain_id


class ModelS(DAQModel):
    _id = 2

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial,
            model_str='[S]', serial_fmt="ODS08%03d7",
            adc_slots=16, dac_slots=1, npios=6, nleds=1,
            dac=DAC(bits=16, vmin=0.0, vmax=4.096),
            adc=ADC(bits=16, vmin=-12.0, vmax=12.0,
                    pga_gains=Gains.S.values,
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
            self, fw_ver, serial,
            model_str='[N]', serial_fmt='ODN08%03d7',
            adc_slots=16, dac_slots=1, npios=6, nleds=1,
            dac=DAC(bits=16, vmin=-4.096, vmax=4.096),
            adc=ADC(bits=16, vmin=-12.288, vmax=12.288,
                    pga_gains=Gains.N.values,
                    pinputs=list(range(1, 9)),
                    ninputs=list(range(0, 9)))
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        return pinput - 1, len(self.adc.pinputs) + pinput - 1


class ModelTP08(DAQModel):
    _id = 10

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial,
            model_str='TP08', serial_fmt='TP08x10%04d',
            adc_slots=8, dac_slots=4, npios=4, nleds=8,
            dac=DAC(bits=16, vmin=-1.25, vmax=1.25),
            adc=ADC(bits=16, vmin=-23.75, vmax=23.75,
                    pga_gains=Gains.TP08.values,
                    pinputs=[1, 2, 3, 4], ninputs=[0])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        return pinput - 1, len(self.adc.pinputs) + pinput - 1


class ModelTP04(DAQModel):
    _id = 11

    def __init__(self, fw_ver, serial):
        DAQModel.__init__(
            self, fw_ver, serial,
            model_str='TP04', serial_fmt='TP04x10%04d',
            adc_slots=4, dac_slots=2, npios=2, nleds=4,
            dac=DAC(bits=16, vmin=-1.25, vmax=1.25),
            adc=ADC(bits=16, vmin=-24.0, vmax=24.0,
                    pga_gains=Gains.TP04.values,
                    pinputs=[1, 2], ninputs=[0])
        )

    def _get_adc_slots(self, gain_id, pinput, ninput):
        return pinput - 1, len(self.adc.pinputs) + pinput - 1
