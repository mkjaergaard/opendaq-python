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


class DAQExternal(DAQExperiment):
    """External experiment.

    :param mode: Define data source or destination (use :class:`.ExpMode`).
    :param clock_input: Digital input used as external clock
    :param edge: New data on rising (1) or falling (0) edges [0:1]
    :param npoints: Total number of points for the experiment [0:65536]
    :param continuous: Indicates if the experiment is continuous
        (False: run once, True: continuous).
    :param buffersize: Buffer size
    :raises: LengthError (too many experiments at the same time,
        ValueError (values out of range)
    """
    def __init__(self, mode, clock_input, edge=1,
                 npoints=10, continuous=False, buffersize=1000):

        if not 1 <= clock_input <= 4:
            raise ValueError('Invalid clock_input')

        if edge not in [0, 1]:
            raise ValueError('Invalid edge')

        if type(mode) == int and not 0 <= mode <= 5:
            raise ValueError('Invalid mode')

        if not 0 <= npoints < 65536:
            raise ValueError('npoints out of range')

        if not 1 <= buffersize <= 20000:
            raise ValueError('Invalid buffer size')

        if mode == 1 and clock_input != 4:
            raise ValueError('Analog output must use DataChannel 4')

        self.number = clock_input
        self.edge = edge
        self.mode = mode
        self.npoints = npoints
        self.continuous = continuous

        self.ring_buffer = deque(maxlen=buffersize)
        self.mutex_ring_buffer = Lock()
        self.analog_setup()
        self.trigger_setup()
