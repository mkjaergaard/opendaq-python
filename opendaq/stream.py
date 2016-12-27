#!/usr/bin/env python

# Copyright 2015
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

from opendaq.experiment import DAQExperiment
from collections import deque
from threading import Lock


class DAQStream(DAQExperiment):
    """
    Stream experiment.

    :param mode: Define data source or destination (use :class:`.ExpMode`).
    :param period: Period of the stream experiment (milliseconds) [1:65536]
    :param npoints: Total number of points for the experiment
            [0:65536] (0 indicates continuous acquisition).
    :param continuous: Indicates if experiment is continuous (True) or
        one-shot (False).
    :param buffersize: Buffer size.
    :raises: LengthError (too many experiments at the same time),
        ValueError (values out of range)
    """
    def __init__(self, mode, number, period,
                 npoints=10, continuous=False, buffersize=1000):
        if not 1 <= number <= 4:
            raise ValueError('Invalid number')

        if mode == 1 and number != 4:
            raise ValueError('Analog output must use DataChannel 4')

        if not 1 <= period <= 65535:
            raise ValueError('Invalid period')

        if type(mode) == int and not 0 <= mode <= 5:
            raise ValueError('Invalid mode')

        if not 0 <= npoints < 65536:
            raise ValueError('npoints out of range')

        if not 1 <= buffersize <= 20000:
            raise ValueError('Invalid buffer size')

        self.number = number
        self.period = period
        self.mode = mode
        self.npoints = npoints
        self.continuous = continuous

        self.ring_buffer = deque(maxlen=buffersize)
        self.mutex_ring_buffer = Lock()
        self.analog_setup()
        self.trigger_setup()
