#!/usr/bin/env python

# Copyright 2012
# Adrian Alvarez <alvarez@ingen10.com> and Juan Menendez <juanmb@ingen10.com>
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

'''
This program allows to modify the openDAQ ID
Arguments:
1: Communications port (ex. COM3)
2: openDAQ ID (ex. 153)
'''

import sys

from daq import DAQ

daq = DAQ(sys.argv[1])
print "ID updated. New ID = ", daq.set_id(int(sys.argv[2]))[2]
