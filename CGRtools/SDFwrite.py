#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2014-2016 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of cgrtools.
#
#  cgrtools is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
from .CGRrw import CGRWrite


class SDFwrite(CGRWrite):
    def __init__(self, output, oldformat=False):
        CGRWrite.__init__(self)
        self.__file = output

        def tooldformat(x, y):
            if x[2] == '8':
                for i in y:
                    if i['type'] == 'dynbond' and x[:2] == i['atoms']:
                        x = tuple(list(x[:2]) + [i['value'].replace('>', '').replace('0', '8')])
            return x
        self.__format = tooldformat if oldformat else lambda x, _: x

    def close(self):
        self.__file.close()

    def writedata(self, data):
        data = self.getformattedcgr(data)
        self.__file.write(
            "\n  SDF generated by CGRtools. (c) Ramil I. Nugmanov\n"
            "\n%3s%3s  0  0  0  0            999 V2000\n" % (len(data['atoms']), len(data['bonds'])))

        for i in data['atoms']:
            self.__file.write("%(x)10.4f%(y)10.4f%(z)10.4f %(element)-3s 0%(charge)3s  0  0  0  0  "
                              "0%(mark)3s  0%(map)3s  0  0\n" % i)
        for i in data['bonds']:
            self.__file.write("%3d%3d%3s  0  0  0  0\n" % self.__format(i, data['CGR_DAT']))

        self.__file.write(self.getformattedtext(data))

        self.__file.write("M  END\n")
        for i in list(data['meta'].items()):
            self.__file.write(">  <%s>\n%s\n" % i)
        self.__file.write("$$$$\n")
