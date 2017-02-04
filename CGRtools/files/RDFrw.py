# -*- coding: utf-8 -*-
#
#  Copyright 2014-2017 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of CGRtools.
#
#  CGRtools is free software; you can redistribute it and/or modify
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
import time
from itertools import chain, repeat
from .CGRrw import CGRread, CGRwrite, fromMDL
from . import MoleculeContainer


class RDFread(CGRread):
    def __init__(self, file, remap=True, stereo=None):
        self.__RDFfile = file
        self.__stereo = stereo and iter(stereo) or repeat(None)
        self.__data = self.__reader()
        CGRread.__init__(self, remap)

    def read(self):
        return list(self.__data)

    def __iter__(self):
        return self.__data

    def __next__(self):
        return next(self.__data)

    def __reader(self):
        ir = -1
        im = -1
        atomcount = -1
        bondcount = -1
        failkey = True
        reaction = None
        isreaction = True
        mkey = None
        mend = False
        for n, line in enumerate(self.__RDFfile):
            if failkey and not line.startswith(("$RFMT", "$MFMT")):
                continue
            elif line.startswith("$RFMT"):
                if reaction:
                    try:
                        yield self.get_reaction(reaction, stereo=next(self.__stereo)) if isreaction \
                            else self.get_molecule(reaction, stereo=next(self.__stereo))
                    except:
                        pass
                reaction = {'substrats': [], 'products': [], 'meta': {}, 'colors': {}}
                isreaction = True
                mkey = None
                ir = n + 5
                failkey = False
            elif line.startswith("$MFMT"):
                if reaction:
                    try:
                        yield self.get_reaction(reaction, stereo=next(self.__stereo)) if isreaction \
                            else self.get_molecule(reaction, stereo=next(self.__stereo))
                    except:
                        pass
                reaction = {'substrats': [], 'products': [], 'meta': {}, 'colors': {}}
                molecule = {'atoms': [], 'bonds': [], 'CGR_DAT': {}}
                isreaction = False
                substrats, products = 1, 0
                mkey = None
                mend = False
                im = n + 4
                ir = -1
                failkey = False
            elif n == ir:
                try:
                    substrats, products = int(line[:3]), int(line[3:6])
                except ValueError:
                    failkey = True
                    reaction = None
            elif line.startswith("$MOL"):
                molecule = {'atoms': [], 'bonds': [], 'CGR_DAT': {}}
                im = n + 4
                mend = False
            elif n == im:
                try:
                    atomcount = int(line[:3]) + im
                    bondcount = int(line[3:6]) + atomcount
                except ValueError:
                    failkey = True
                    reaction = None
            elif n <= atomcount:
                molecule['atoms'].append(dict(element=line[31:34].strip(), isotope=int(line[34:36]),
                                              charge=fromMDL.get(int(line[38:39]), 0),
                                              map=int(line[60:63]), mark=line[54:57].strip(),
                                              x=float(line[:10]), y=float(line[10:20]), z=float(line[20:30])))
            elif n <= bondcount:
                try:
                    molecule['bonds'].append((int(line[:3]), int(line[3:6]), int(line[6:9])))
                except:
                    failkey = True
                    reaction = None

            elif line.startswith("M  END"):
                mend = True
                molecule['CGR_DAT'] = self.getdata()
                if len(reaction['substrats']) < substrats:
                    reaction['substrats'].append(molecule)
                elif len(reaction['products']) < products:
                    reaction['products'].append(molecule)

            elif n > bondcount:
                try:
                    if not mend:
                        self.collect(line)
                    elif line.startswith('$DTYPE'):
                        mkey = line[7:].strip()
                        if mkey.split('.')[0] in ('PHTYP', 'FFTYP', 'PCTYP', 'EPTYP', 'HBONDCHG', 'CNECHG', 'dynPHTYP',
                                                  'dynFFTYP', 'dynPCTYP', 'dynEPTYP', 'dynHBONDCHG', 'dynCNECHG'):
                            target = 'colors'
                        else:
                            target = 'meta'
                        reaction[target][mkey] = []
                    elif mkey:
                        data = line.lstrip("$DATUM").strip()
                        if data:
                            reaction[target][mkey].append(data)
                except:
                    failkey = True
                    reaction = None
        else:
            if reaction:
                try:
                    yield self.get_reaction(reaction, stereo=next(self.__stereo)) if isreaction \
                        else self.get_molecule(reaction, stereo=next(self.__stereo))
                except:
                    pass

    def get_molecule(self, reaction, stereo=None):
        molecule = reaction['substrats'][0]
        molecule['meta'] = reaction['meta']
        molecule['colors'] = reaction['colors']
        return super(RDFread, self).get_molecule(molecule, stereo=stereo)


class RDFwrite(CGRwrite):
    def __init__(self, file, extralabels=False, mark_to_map=False):
        CGRwrite.__init__(self, extralabels=extralabels, mark_to_map=mark_to_map)
        self.__file = file
        self.write = self.__initwrite

    def close(self):
        self.__file.close()

    def __initwrite(self, data):
        self.__file.write(time.strftime("$RDFILE 1\n$DATM    %m/%d/%y %H:%M\n"))
        self.__writedata(data)
        self.write = self.__writedata

    def __writedata(self, data):
        if isinstance(data, MoleculeContainer):
            m = self.getformattedcgr(data)
            self.__file.write('$MFMT\n')
            self.__file.write(m['CGR'])
            self.__file.write("M  END\n")
            colors = m['colors']
        else:
            self.__file.write('$RFMT\n$RXN\n\n  CGRtools. (c) Dr. Ramil I. Nugmanov\n\n%3d%3d\n' %
                              (len(data.substrats), len(data.products)))
            colors = {}
            for cnext, m in enumerate(chain(data.substrats + data.products), start=1):
                m = self.getformattedcgr(m)
                self.__file.write('$MOL\n')
                self.__file.write(m['CGR'])
                self.__file.write("M  END\n")
                colors.update({'%s.%d' % (k, cnext): v for k, v in m['colors'].items()})

        for p in chain(colors.items(), data.meta.items()):
            self.__file.write('$DTYPE %s\n$DATUM %s\n' % p)