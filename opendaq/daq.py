# !/usr/bin/env python

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
import time
import struct
import serial
import threading
from enum import IntEnum
from .common import check_crc, check_stream_crc, mkcmd
from .common import LengthError, CRCError
from .experiment import Trigger, ExpMode, DAQStream, DAQBurst, DAQExternal
from .simulator import DAQSimulator
from .models import DAQModel, Gains

BAUDS = 115200
NAK = mkcmd(160, '')
MAX_CHANNELS = 4


class LedColor(IntEnum):
    """Valid LED colors."""
    OFF = 0
    GREEN = 1
    RED = 2
    ORANGE = 3


class DAQ(threading.Thread):
    """This class represents an OpenDAQ device."""

    def __init__(self, port, debug=False):
        """Class constructor
        :param port: Serial port.
        :param debug: Turn on serial echoing to sdout.
        """
        threading.Thread.__init__(self)
        self.__port = port
        self.__debug = debug
        self.__simulate = (port == 'sim')

        self.__running = False
        self.__measuring = False
        self.__stopping = False
        self.__gain = 0
        self.__pinput = 1
        self.__ninput = 0
        self.__exp = []     # list of experiments

        self.open()

        self.model = DAQModel.new(*self.get_info())
        self.hw_ver = self.model.model_str
        self.fw_ver = self.model.fw_ver
        self.model.load_calibration(self.__read_calib_slot)

    def open(self):
        """Open the serial port."""
        if self.__simulate:
            self.ser = DAQSimulator(self.__port, BAUDS, timeout=1)
        else:
            self.ser = serial.Serial(self.__port, BAUDS, timeout=1)
            self.ser.setRTS(0)
            time.sleep(2)

    def close(self):
        """Close the serial port."""
        self.ser.close()

    def send_command(self, command, ret_fmt):
        """Build a command packet, send it to the openDAQ and process the
        response.

        :param command: Command string.
        :param ret_fmt: Payload format of the response using python 'struct'
            format characters.
        :returns: Command ID and arguments of the response.
        :raises: LengthError: The legth of the response is not the expected.
        """
        fmt = '!BB' + ret_fmt
        ret_len = 2 + struct.calcsize(fmt)
        self.ser.write(command)
        ret = self.ser.read(ret_len)
        if self.__debug:
            print("Command:  ", end=" ")
            for c in command:
                print("%02X" % ord(c), end=" ")
            print()
            print("Response: ", end=' ')
            for c in ret:
                print("%02X" % ord(c), end=" ")
            print()

        if ret == NAK:
            raise IOError("NAK response received")

        if len(ret) != ret_len:
            raise LengthError("Bad packet length %d (it should be %d)" %
                              (len(ret), ret_len))

        data = struct.unpack(fmt, check_crc(ret))
        if data[1] != ret_len - 4:
            raise LengthError("Bad body length %d (it should be %d)" %
                              (ret_len - 4, data[1]))
        # Strip 'command' and 'length' values from returned data
        return data[2:]

    def enable_crc(self, on):
        """Enable/Disable the cyclic redundancy check.

        :param on: Enable/disable CRC checking (bool).
        """
        return self.send_command(mkcmd(55, 'B', int(bool(on))), 'B')[0]

    def __read_calib_slot(self, slot):
        """Read device calibration for a given gain.

        :param slot: Calibration slot number.
        :returns:
            - Slot number
            - Gain raw correction
            - Offset raw correction
        :raises: ValueError
        """
        return self.send_command(mkcmd(36, 'B', slot), 'Bhh')

    def __write_calib_slot(self, slot, corr, offset):
        """Write device calibration for a given slot.

        :param slot: Calibration slot number.
        :param corr: Gain raw correction
        :param offset: Offset raw correction
        :returns:
            - Slot number
            - Gain raw correction
            - Offset raw correction
        :raises: ValueError
        """
        return self.send_command(mkcmd(37, 'Bhh', slot, corr, offset), 'Bhh')

    def get_dac_cal(self):
        """Read DAC calibration.

        :returns: List of DAC calibration registers
        """
        return self.model.dac_calib

    def get_adc_cal(self):
        """Read ADC calibration values for all the available device
        configurations.

        :returns: List of ADC calibration registers
        """
        return self.model.adc_calib
    
    def load_calibration(self):
        """Recall calibration values from device's memory.

        :returns: Nothing
        """
        self.model.load_calibration(self.__read_calib_slot)

    def save_calibration(self, flag='ALL'):
        """Recall calibration values from device's memory.
        :param flag: Save 'ALL', 'DAC' or 'ADC' registers
        :returns: Nothing
        """
        self.model.save_calibration(self.__write_calib_slot, flag)

    '''
    def __set_calibration(self, slot_id, corr, offset):
        """Set device calibration.

        :param gain_id: ID of the analog configuration setup.
        :param corr: Gain correction: G = Gbase*(1 + corr/100000).
        :param offset: Offset raw value (-32768 to 32767).
        :raises: ValueError
        """
        if (slot_id not in self.model.dac_coef_range() and
                slot_id not in self.model.adc_coef_range('ALL')):
            raise ValueError("gain_id out of range")

        return self.send_command(mkcmd(37, 'Bhh', slot_id, corr, offset), 'Bhh')

    def set_dac_cal(self, corrs, offsets):
        """Set the DAC calibration.

        :param corrs: Gain corrections (0.9 to 1.1).
        :param offset: Offset value in volts(-32768 to 32767).
        :raises: ValueError
        """

        valuesm = [int(round((c - 1)*(2**16))) for c in corrs]
        valuesb = [int(round(c*(2**16))) for c in offsets]

        for i in self.model.dac_coef_range():
            self.__set_calibration(i, valuesm[i], valuesb[i])

    def set_adc_cal(self, corrs, offsets, flag='ALL'):
        """Set the ADC calibration.

        :param corrs: Gain corrections (0.9 to 1.1).
        :param offsets: Offset raw value (-32768 to 32767).
        :param flag: 'ALL', 'SE' or 'DE' (only for 'S' model).
        :raises: ValueError
        """

        valuesm = [int(round((c - 1)*(2**16))) for c in corrs]
        valuesb = [int(c*(2**5)) for c in offsets]

        for i, j in enumerate(self.model.adc_coef_range(flag)):
            self.__set_calibration(j, valuesm[i], valuesb[i])
    '''

    def set_id(self, id):
        """Identify openDAQ device.

        :param id: id number of the device [000:999]
        :raises: ValueError
        """
        if not 0 <= id < 1000:
            raise ValueError("id out of range")

        return self.send_command(mkcmd(39, 'I', id), 'BBI')

    def get_info(self):
        """Read device information.

        :returns: [hardware_version, firmware_version, device_id]
        """
        return self.send_command(mkcmd(39, ''), 'BBI')

    def __str__(self):
        return ("Hardware version: %s\n"
                "Firmware version: %s\n"
                "Serial number: %s" %
                (self.model.model_str, self.model.fw_ver,
                 self.model.serial_str))

    def read_eeprom(self, pos):
        """Read a byte from the EEPROM.

        :param val: value to write.
        :param pos: position in memory.
        :raises: ValueError
        """
        if not 0 <= pos < 254:
            raise ValueError("pos out of range")

        return self.send_command(mkcmd(31, 'BB', pos, 1), 'BBB')[2]

    def write_eeprom(self, pos, val):
        """Write a byte in the EEPROM.

        :param id: id number of the device [000:999].
        :raises: ValueError
        """
        if not 0 <= pos < 254:
            raise ValueError("pos out of range")

        return self.send_command(mkcmd(30, 'BBB', pos, 1, val), 'BBB')

    def set_dac(self, raw, number=1):
        """Set DAC output (raw value).
        Set the raw value of the DAC.

        "param raw: Raw ADC value.
        :raises: ValueError
        """
        self.send_command(mkcmd(13, 'hB', int(round(raw)), number), 'hB')[0]

    def set_analog(self, volts, number=1):
        """Set DAC output (volts).
        Set the output voltage of the DAC.

        :param volts: DAC output value in volts.
        :raises: ValueError
        """
        self.set_dac(self.model.volts_to_raw(volts, number-1), number)

    def read_adc(self):
        """Read data from ADC and return the raw value.

        :returns: Raw ADC value.
        """
        return self.send_command(mkcmd(1, ''), 'h')[0]

    def read_analog(self):
        """Read data from ADC in volts.

        :returns: Voltage value.
        """
        value = self.send_command(mkcmd(1, ''), 'h')[0]
        return self.model.raw_to_volts(value, self.__gain,
                                       self.__pinput, self.__ninput)

    def read_all(self, nsamples=20, gain=0):
        """Read data from all analog inputs

        :param nsamples: Number of samples per data point [0-255] (default=20)
        :param gain: Analog gain (default=1)
        :returns: Values[0:7]: List of the analog reading on each input
        """
        if self.model.fw_ver < 120:
            raise Warning("Function not implemented in this FW. Try updating")

        values = self.send_command(mkcmd(4, 'BB', nsamples, gain), '8h')
        return [self.model.raw_to_volts(v, gain, i, 0) for i, v in enumerate(values)]

    def conf_adc(self, pinput=8, ninput=0, gain=0, nsamples=20):
        """Configure the analog-to-digital converter.

        Get the parameters for configure the analog-to-digital converter.

        :param pinput: Positive input [1:8].
        :param ninput: Negative input.
        :param gain: Analog gain.
        :param nsamples: Number of samples per data point [0-255).
        :raises: ValueError
        """

        self.model.check_adc_settings(pinput, ninput, int(gain))

        if not 0 <= nsamples < 255:
            raise ValueError("samples number out of range")
        
        self.__gain = int(gain)
        self.__pinput = pinput
        self.__ninput = ninput

        self.send_command(mkcmd(2, 'BBBB', pinput, ninput, int(gain),
                                nsamples), 'hBBBB')

    def set_led(self, color, number=1):
        """Choose LED status.
        LED switch on (green, red or orange) or switch off.

        :param color: LED color (use :class:`.LedColor`).
        :raises: ValueError
        """
        if not type(color) is LedColor:
            raise ValueError("Invalid color value")

        if not 1 <= number <= 4:
            raise ValueError("Invalid led number")

        self.send_command(mkcmd(18, 'BB', color.value, number), 'BB')[0]

    def set_pio(self, number, value):
        """Write PIO output value.
        Set the value of the PIO terminal (0: low, 1: high).

        :param number: PIO number.
        :param value: digital value (0: low, 1: high)
        :raises: ValueError
        """
        self.model.check_pio(number)

        if value not in [0, 1]:
            raise ValueError("digital value out of range")

        self.send_command(mkcmd(3, 'BB', number, int(bool(value))), 'BB')[1]

    def read_pio(self, number):
        """Read PIO input value (0: low, 1: high).

        :param number: PIO number.
        :returns: Read value.
        :raises: ValueError
        """
        self.model.check_pio(number)

        return self.send_command(mkcmd(3, 'B', number), 'BB')[1]

    def set_pio_dir(self, number, output):
        """Configure PIO direction.
        Set the direction of a specific PIO terminal (D1-D6).

        :param number: PIO number.
        :param output: PIO direction (0 input, 1 output).
        :raises: ValueError
        """
        self.model.check_pio(number)

        if output not in [0, 1]:
            raise ValueError("PIO direction out of range")

        self.send_command(mkcmd(5, 'BB', number, int(bool(output))), 'BB')

    def set_port(self, value):
        """Write all PIO values.
        Set the value of all Dx terminals.

        :param value: Port output byte (bits: 0:low, 1:high).
        :raises: ValueError
        """
        self.model.check_port(value)
        self.send_command(mkcmd(7, 'B', value), 'B')[0]

    def read_port(self):
        """Read all PIO values.

        :returns: Binary value of the port.
        """
        return self.send_command(mkcmd(7, ''), 'B')[0]

    def set_port_dir(self, output):
        """Configure all PIOs directions.
        Set the direction of all D1-D6 terminals.

        :param output: Port directions byte (bits: 0:input, 1:output).
        :raises: ValueError
        """
        self.model.check_port(output)
        self.send_command(mkcmd(9, 'B', output), 'B')

    def spi_config(self, cpol, cpha):
        """Bit-Bang SPI configure (clock properties).

        :param cpol: Clock polarity (clock pin state when inactive).
        :param cpha: Clock phase (leading 0, or trailing 1 edges read).
        :raises: ValueError
        """
        if not 0 <= cpol <= 1 or not 0 <= cpha <= 1:
            raise ValueError("Invalid spisw_config values")

        self.send_command(mkcmd(26, 'BB', cpol, cpha), 'BB')

    def spi_setup(self, nbytes, sck=1, mosi=2, miso=3):
        """Bit-Bang SPI setup (PIO numbers to use).

        :param nbytes: Number of bytes.
        :param sck: Clock pin.
        :param mosi: MOSI pin (master out / slave in).
        :param miso: MISO pin (master in / slave out).
        :raises: ValueError
        """
        if not 0 <= nbytes <= 3:
            raise ValueError("Invalid number of bytes")
        if not 1 <= sck <= 6 or not 1 <= mosi <= 6 or not 1 <= miso <= 6:
            raise ValueError("Invalid spisw_setup values")

        self.send_command(mkcmd(28, 'BBB', sck, mosi, miso), 'BBB')

    def spi_write(self, value, word=False):
        """Bit-bang SPI transfer (send+receive) a byte or a word.

        :param value: Data to send (byte/word to transmit).
        :param word: send a 2-byte word, instead of a byte.
        :raises: ValueError
        """
        if not 0 <= value <= 65535:
            raise ValueError("Value out of range")

        if word:
            ret = self.send_command(mkcmd(29, 'H', value), 'H')[0]
        else:
            ret = self.send_command(mkcmd(29, 'B', value), 'B')[0]
        return ret

    def init_counter(self, edge):
        """Initialize the edge counter and configure which edge increments the
        count.

        :param edge: high-to-low (False) or low-to-high (True).
        """
        self.send_command(mkcmd(41, 'B', int(bool(edge))), 'B')[0]

    def get_counter(self, reset):
        """Get the counter value.

        :param reset: reset the counter after perform reading (boolean).
        """
        return self.send_command(mkcmd(42, 'B', int(bool(reset))), 'I')[0]

    def init_capture(self, period):
        """Start Capture Mode around a given period.

        :param period: Estimated period of the wave (in microseconds).
        :raises: ValueError
        """
        if not 0 <= period <= 2**32:
            raise ValueError("Period value out of range")

        self.send_command(mkcmd(14, 'I', period), 'I')[0]

    def stop_capture(self):
        """Stop Capture mode."""
        self.send_command(mkcmd(15, ''), '')

    def get_capture(self, mode):
        """Get Capture reading for the period length.

        :param mode: Period length (0: Low cycle, 1: High cycle,
            2: Full period)
        :returns:
            - mode
            - period: The period length in microseconds
        :raises: ValueError
        """
        if mode not in [0, 1, 2]:
            raise ValueError("mode value out of range")

        return self.send_command(mkcmd(16, 'B', mode), 'BI')

    def init_encoder(self, resolution):
        """Start Encoder function.

        :param resolution: Maximum number of ticks per round [0:65535].
        :raises: ValueError
        """
        if not 0 <= resolution <= 2**32:
            raise ValueError("resolution value out of range")

        self.send_command(mkcmd(50, 'I', resolution), 'I')[0]

    def get_encoder(self):
        """Get current encoder relative position.

        :returns: Position: The actual encoder value.
        """
        return self.send_command(mkcmd(52, ''), 'I')[0]

    def stop_encoder(self):
        """Stop encoder"""
        self.send_command(mkcmd(51, ''), '')

    def init_pwm(self, duty, period):
        """Start PWM output with a given period and duty cycle.

        :param duty: High time of the signal [0:1023](0 always low, 1023 always
            high).
        :param period: Period of the signal (microseconds) [0:65535].
        :raises: ValueError
        """
        if not 0 <= duty < 1024:
            raise ValueError("duty value out of range")

        if not 0 <= period <= 65535:
            raise ValueError("period value out of range")

        self.send_command(mkcmd(10, 'HH', duty, period), 'HH')

    def stop_pwm(self):
        """Stop PWM"""
        self.send_command(mkcmd(11, ''), '')

    def __trigger_setup(self, number, mode, value):
        """Change the trigger mode of the DataChannel.

        :param number: Number of the DataChannel.
        :param mode: Trigger mode (use :class:`.Trigger`).
        :param value: Value of the trigger mode.
        :raises: ValueError
        """

        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        if not type(mode) is Trigger:
            raise ValueError("Invalid trigger mode")

        if 1 <= mode <= 6 and value not in [0, 1]:
            raise ValueError("Invalid value of digital trigger")

        self.send_command(mkcmd(33, 'BBH', number, mode, value), 'BBH')

    def trigger_mode(self, number):
        """Get the trigger mode of the DataChannel.

        :param number: Number of the DataChannel.
        :raises: ValueError
        """

        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        mode = self.send_command(mkcmd(34, 'B', number), 'H')[0]
        return Trigger(mode)

    def get_state_ch(self, number):
        """Get state of the DataChannel.

        :param number: Number of the DataChannel.
        :raises: ValueError
        """

        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        return self.send_command(mkcmd(35, 'B', number), 'H')[0]

    def __conf_channel(self, number, mode, pinput=1, ninput=0, gain=1,
                       nsamples=1):
        """Configure a channel for a generic stream experiment
        (Stream/External/Burst).

        :param number: Select a DataChannel number for this experiment
        :param mode: Define data source or destination (use :class:`.ExpMode`).
        :param pinput: Select Positive/SE analog input [1:8]
        :param ninput: Select Negative analog input.
        :param gain: Select PGA multiplier.
        :param nsamples: Number of samples to calculate the mean for each point
            [0:255].
        :raises: ValueError
        """
        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        if not type(mode) is ExpMode:
            raise ValueError("Invalid mode")

        self.model.check_adc_settings(pinput, ninput, int(gain))

        if not 0 <= nsamples < 255:
            raise ValueError("samples number out of range")

        return self.send_command(
            mkcmd(22, 'BBBBBB', number, mode.value, pinput, ninput, int(gain),
                  nsamples), 'BBBBBB')

    def __setup_channel(self, number, npoints, continuous=False):
        """Configure the experiment's number of points.

        :param number: Select a DataChannel number for this experiment.
        :param npoints: Total number of points for the experiment
            [0:65536] (0 indicates continuous acquisition).
        :param continuous: Indicates if the experiment is continuous
            - False: run once
            - True: continuous
        :raises: ValueError
        """
        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        if not 0 <= npoints < 65536:
            raise ValueError("npoints out of range")

        return self.send_command(mkcmd(32, 'BHb', number,
                                       npoints, int(not continuous)), 'BHB')

    def remove_experiment(self, experiment):
        """Delete a single experiment.

        :param experiment: reference of the experiment to remove.
        :raises: ValueError
        """
        nb = experiment.get_parameters()[3]
        if not 1 <= nb <= 4:
            raise ValueError("Invalid reference")
        self.__destroy_channel(nb)
        for i in range(len(self.__exp))[::-1]:
            if self.__exp[i].number == nb:
                del(self.__exp[i])

    def clear_experiments(self):
        """Delete the whole experiment list."""
        for i in range(len(self.__exp))[::-1]:
            self.__destroy_channel(i + 1)
            del(self.__exp[i])

    def __dchanindex(self):
        """Check which internal DataChannels are used or available.

        :returns:
            - available: list of free DataChannels.
            - used: list of asigned DataChannels.
        """
        used = [e.number for e in self.__exp]
        available = [i for i in range(1, 5) if i not in used]
        return available, used

    def flush_channel(self, number):
        """Flush the channel.

        :param number: Number of DataChannel to flush.
        :returns: ValueError
        """
        if not 1 <= number <= MAX_CHANNELS:
                raise ValueError("Invalid DataChannel number")

        self.send_command(mkcmd(45, 'B', number), 'B')

    def __destroy_channel(self, number):
        """Command firmware to clear a Datachannel structure.

        :param number: Number of DataChannel structure to clear [0:4] (0: reset
            all DataChannels)
        :raises: ValueError
        """
        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        return self.send_command(mkcmd(57, 'B', number), 'B')[0]

    def create_stream(self, mode, *args, **kwargs):
        """Create Stream experiment.

        See the :class:`.DAQStream` class constructor for more info.
        """
        if not type(mode) is ExpMode:
            raise ValueError("Invalid mode")

        index = len(self.__exp)
        if index > 0 and self.__exp[0].__class__ is DAQBurst:
            raise LengthError("Device is configured for a Burst experiment")

        available, _ = self.__dchanindex()
        if len(available) == 0:
            raise LengthError("Maximum value of experiments has been reached")

        if mode == ExpMode.ANALOG_OUT:
            chan = 4  # DAC_OUTPUT is fixed at DataChannel 4
            for i in range(index):
                if self.__exp[i].number == chan:
                    if type(self.__exp[i]) is DAQStream:
                        self.__exp[i].number = available[0]
                    else:
                        raise ValueError("DataChannel 4 is being used")
        else:
            chan = available[0]

        self.__exp.append(DAQStream(mode, chan, *args, **kwargs))
        return self.__exp[index]

    def __create_stream(self, number, period):
        """Send a command to the firmware to create a Stream experiment.

        :param number: Assign a DataChannel number for this experiment [1:4].
        :param period: Period of the stream experiment (ms) [1:65536].
        :raises: ValueError
        """
        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")
        if not 1 <= period <= 65535:
            raise ValueError("Invalid period")

        self.send_command(mkcmd(19, 'BH', number, period), 'BH')

    def create_external(self, mode, clock_input, *args, **kwargs):
        """Create External experiment.

        See the :class:`.DAQExternal` class constructor for more info.
        """
        if not type(mode) is ExpMode:
            raise ValueError("Invalid mode")

        index = len(self.__exp)
        if index > 0 and self.__exp[0].__class__ is DAQBurst:
            raise LengthError("Device is configured for a Burst experiment")

        available, _ = self.__dchanindex()
        if len(available) == 0:
            raise LengthError("Maximum value of experiments has been reached")

        for i in range(index):
            if self.__exp[i].number == clock_input:
                if type(self.__exp[i]) is DAQStream:
                    self.__exp[i].number = available[0]
                else:
                    raise ValueError("Clock_input is being used by another experiment")

        self.__exp.append(DAQExternal(mode, clock_input, *args, **kwargs))
        return self.__exp[index]

    def __create_external(self, number, edge):
        """Send a command to the firmware to create an External experiment.

        :param number: Assign a DataChannel number for this experiment [1:4].
        :param edge: New data on rising (1) or falling (0) edges [0:1].
        :raises: ValueError
        """
        if not 1 <= number <= MAX_CHANNELS:
            raise ValueError("Invalid DataChannel number")

        if edge not in [0, 1]:
            raise ValueError("Invalid edge")

        return self.send_command(mkcmd(20, 'BB', number, edge), 'BB')

    def create_burst(self, *args, **kwargs):
        """Create Burst experiment.

        See the :class:`.DAQBurst` class constructor for more info.
        """

        if len(self.__exp) > 0:
            raise LengthError("Only one experiment allowed when using burst")

        self.__exp.append(DAQBurst(*args, **kwargs))
        return self.__exp[0]

    def __create_burst(self, period):
        """Send a command to the firmware to create a Burst experiment.

        :param period: Period of the burst experiment (microseconds)
            [100:65535]
        :raises: ValueError
        """
        if not 100 <= period <= 65535:
            raise ValueError("Invalid period")

        return self.send_command(mkcmd(21, 'H', period), 'H')

    def __load_signal(self, pr_of, pr_data):
        """Load an array of values in volts to preload DAC output.

        :raises: LengthError: Invalid dada length.
        """
        if not 1 <= len(pr_data) <= 400:
            raise LengthError("Invalid data length")
        values = []
        self.set_analog(pr_data[0])
        for volts in pr_data:
            raw = self.model.volts_to_raw(volts, 0)
            values.append(raw)
        return self.send_command(mkcmd(23, 'h%dH' % len(values),
                                       pr_of, *values), 'Bh')

    def flush(self):
        """Flush internal buffers."""
        self.ser.flushInput()

    def __get_stream(self, data, channel):
        """Low-level function for stream data collecting.

        :param data: Buffer for data points.
        :param channel: Buffer for assigned experiment number.

        :returns:
            - 0 if there is not any incoming data.
            - 1 if data stream was processed.
            - 2 if no data stream received.
        """
        #TODO: refactor this method

        self.header = []
        self.data = []
        ret = self.ser.read(1)
        if not ret:
            return 0
        head = struct.unpack('!b', ret)
        if head[0] != 0x7E:
            data.append(head[0])
            return 2
        # Get header
        while len(self.header) < 8:
            ret = self.ser.read(1)
            char = struct.unpack('!B', ret)
            if char[0] == 0x7D:
                ret = self.ser.read(1)
                char = struct.unpack('!B', ret)
                tmp = char[0] | 0x20
                self.header.append(tmp)
            else:
                self.header.append(char[0])
            if len(self.header) == 3 and self.header[2] == 80:
                # openDAQ sent a stop command
                ret = self.ser.read(2)
                char, ch = struct.unpack('!BB', ret)
                channel.append(ch - 1)
                return 3
        self.data_length = self.header[3] - 4
        while len(self.data) < self.data_length:
            ret = self.ser.read(1)
            char = struct.unpack('!B', ret)
            if char[0] == 0x7D:
                ret = self.ser.read(1)
                char = struct.unpack('!B', ret)
                tmp = char[0] | 0x20
                self.data.append(tmp)
            else:
                self.data.append(char[0])
        for i in range(0, self.data_length, 2):
            value = (self.data[i] << 8) | self.data[i + 1]
            if value >= 32768:
                value -= 65536
            data.append(int(value))
            channel.append(self.header[4] - 1)
        check_stream_crc(self.header, self.data)
        return 1

    @property
    def is_measuring(self):
        """True if any experiment is going on."""
        return self.__measuring

    def start(self):
        """Start all available experiments."""
        for s in self.__exp:
            if s.__class__ is DAQBurst:
                self.__create_burst(s.period)
            elif s.__class__ is DAQStream:
                self.__create_stream(s.number, s.period)
            else:  # External
                self.__create_external(s.number, s.edge)
            self.__setup_channel(s.number, s.npoints, s.continuous)
            self.__conf_channel(s.number, s.mode, s.pinput,
                                s.ninput, s.gain, s.nsamples)
            self.__trigger_setup(s.number, s.trg_mode, s.trg_value)

            if (s.get_mode() == ExpMode.ANALOG_OUT):
                pr_data, pr_offset = s.get_preload_data()
                for i in range(len(pr_offset)):
                    self.__load_signal(pr_offset[i], pr_data[i])
                break

        self.send_command(mkcmd(64, ''), '')

        if not self.__running:
            threading.Thread.start(self)

        self.__running = True
        self.__measuring = True

    def stop(self):
        """Stop all running experiments and exit threads.

        It clears the experiment list. The experiments will no longer be
        available. Call it just before quitting program!
        """
        self.__measuring = False
        self.__running = False
        self.__stopping = True
        while True:
            try:
                self.send_command(mkcmd(80, ''), '')
                self.clear_experiments()
                break
            except CRCError:
                time.sleep(0.2)
                self.flush()

    def halt(self, clear=False):
        """Stop running experiments but keep threads active to start new
        experiments.

        :param clear: Clear experiment list.
        """
        self.__measuring = False
        while True:
            try:
                self.send_command(mkcmd(80, ''), '')
                time.sleep(1)
                break
            except CRCError:
                time.sleep(0.2)
                self.flush()
        if clear:
            self.clear_experiments()

    def run(self):
        """Thread loop.

        The procedure stores the experiment data automatically sent from the
        device after start().
        """
        while True:
            while self.__running:
                if self.__measuring:
                    data = []
                    channel = []
                    result = self.__get_stream(data, channel)
                    if result == 1:
                        # data available
                        available, used = self.__dchanindex()
                        for i in range(len(channel)):
                            exp = self.__exp[used.index(channel[i] + 1)]
                            gain_id, pinput, ninput, _ = exp.get_parameters()
                            exp.add_point(self.model.raw_to_volts(
                                data[i], gain_id, pinput, ninput))

                    elif result == 3:
                        self.halt()
                else:
                    time.sleep(0.2)

            if self.__stopping:
                break
