# coding: utf-8
from __future__ import print_function, division, unicode_literals, absolute_import

import numpy as np
import pymatgen.io.abinit.netcdf as ionc

from monty.functools import lazy_property
from .xsf import *
from .visualizer import *


as_etsfreader = ionc.as_etsfreader


class ETSF_Reader(ionc.ETSF_Reader):
    """
    Provides high-level API to read data from netcdf files written
    folloing the ETSF-IO specifications described in :cite:`Caliste2008`
    """

    def read_structure(self):
        """
        Overrides the ``read_structure`` method so that we always return
        an instance of AbiPy |Structure| object
        """
        from abipy.core.structure import Structure
        return Structure.from_file(self.path)

    # Must overwrite implementation of pymatgen.io.abinit.netcdf
    # due to a possible bug introduced by initial whitespaces in symbol
    @lazy_property
    def chemical_symbols(self):
        """Chemical symbols char [number of atom species][symbol length]."""
        charr = self.read_value("chemical_symbols")
        symbols = []
        for v in charr:
            s = "".join(c.decode("utf-8") for c in v)
            # Strip to avoid possible whitespaces.
            symbols.append(s.strip())

        return symbols

    def read_string(self, varname):
        """
        Args:
            varname: Name of the variable
        """
        b = self.rootgrp.variables[varname][:]
        #print(type(b))
        import netCDF4
        try:
            value = netCDF4.chartostring(b)[()].decode('utf-8')
        except Exception:
            try:
                value = netCDF4.chartostring(b)[()]
            except Exception:
                try:
                    value = "".join(c for c in self.read_value(varname))
                except TypeError as exc:
                    value = "".join(c.decode("utf-8") for c in self.read_value(varname))

        return value.strip()

    def none_if_masked_array(self, arr):
        """Return None if arr is a MaskedArray else None."""
        return arr if not isinstance(arr, np.ma.MaskedArray) else None
