"""Tests for electrons.gw module"""
from __future__ import print_function, division, absolute_import, unicode_literals

import os
import collections
import numpy as np
import abipy.data as abidata

from abipy import abilab
from abipy.electrons.gw import *
from abipy.electrons.gw import SigresPlotter
from abipy.core.testing import AbipyTest


class TestQPList(AbipyTest):

    def setUp(self):
        self.sigres = sigres = abilab.abiopen(abidata.ref_file("tgw1_9o_DS4_SIGRES.nc"))
        repr(self.sigres); str(self.sigres)
        assert self.sigres.to_string(verbose=2)
        self.qplist = sigres.get_qplist(spin=0, kpoint=sigres.gwkpoints[0])

    def tearDown(self):
        self.sigres.close()

    def test_qplist(self):
        """Test QPList object."""
        qplist = self.qplist
        assert isinstance(qplist, collections.Iterable)
        self.serialize_with_pickle(qplist, protocols=[-1])

        repr(qplist); str(qplist)
        qplist_copy = qplist.copy()
        assert qplist_copy == qplist

        qpl_e0sort = qplist.sort_by_e0()
        assert qpl_e0sort.is_e0sorted
        e0mesh = qpl_e0sort.get_e0mesh()
        assert e0mesh[-1] > e0mesh[0]
        values = qpl_e0sort.get_field("qpeme0")
        assert len(values) == len(qpl_e0sort)

        qp = qpl_e0sort[2]
        value = qpl_e0sort.get_skb_field(qp.skb, "qpeme0")
        assert qp.qpeme0 == value

        with self.assertRaises(ValueError):
            qplist.get_e0mesh()
        with self.assertRaises(ValueError):
            qplist.merge(qpl_e0sort)
        with self.assertRaises(ValueError):
            qplist.merge(qplist)

        other_qplist = self.sigres.get_qplist(spin=0, kpoint=self.sigres.gwkpoints[1])
        qpl_merge = qplist.merge(other_qplist)

        assert all(qp in qpl_merge for qp in qplist)
        assert all(qp in qpl_merge for qp in other_qplist)

        # Test QPState object.
        qp = qplist[0]
        repr(qp); str(qp)
        #qp.to_string(verbose=verbose, title="QP State")
        print(qp.tips)

        self.assert_almost_equal(qp.e0, -5.04619941555265, decimal=5)
        self.assert_almost_equal(qp.qpe.real, -4.76022137474714)
        self.assert_almost_equal(qp.qpe.imag, -0.011501666037697)
        self.assert_almost_equal(qp.sigxme, -16.549383605401)


class TestSigresFile(AbipyTest):

    def test_readall(self):
        for path in abidata.SIGRES_NCFILES:
            with abilab.abiopen(path) as sigres:
                repr(sigres); str(sigres)
                assert len(sigres.structure)

    def test_base(self):
        """Test SIGRES File."""
        sigres = abilab.abiopen(abidata.ref_file("tgw1_9o_DS4_SIGRES.nc"))
        assert sigres.nsppol == 1
        sigres.print_qps(precision=5, ignore_imag=False)
        assert sigres.params["nsppol"] == sigres.nsppol

        # In this run IBZ = kptgw
        assert len(sigres.ibz) == 6
        assert sigres.gwkpoints == sigres.ibz

        kptgw_coords = np.reshape([
            -0.25, -0.25, 0,
            -0.25, 0.25, 0,
            0.5, 0.5, 0,
            -0.25, 0.5, 0.25,
            0.5, 0, 0,
            0, 0, 0
        ], (-1, 3))

        self.assert_almost_equal(sigres.ibz.frac_coords, kptgw_coords)

        qpgaps = [3.53719151871085, 4.35685250045637, 4.11717896881632,
                  8.71122659251508, 3.29693118466282, 3.125545059031]
        self.assert_almost_equal(sigres.qpgaps, np.reshape(qpgaps, (1, 6)))

        ik = 2
        df = sigres.get_dataframe_sk(spin=0, kpoint=ik)
        same_df = sigres.get_dataframe_sk(spin=0, kpoint=sigres.gwkpoints[ik])

        assert np.all(df["qpe"] == same_df["qpe"])

        # Ignore imaginary part.
        df_real = sigres.get_dataframe_sk(spin=0, kpoint=ik, ignore_imag=True)
        assert np.all(df["qpe"].real == df_real["qpe"])

        full_df = sigres.to_dataframe()

        marker = sigres.get_marker("qpeme0")
        assert marker and len(marker.x)

        if self.has_matplotlib():
            sigres.plot_qps_vs_e0(show=False)
            with self.assertRaises(ValueError):
                sigres.plot_qps_vs_e0(with_fields="qqeme0", show=False)
            sigres.plot_qps_vs_e0(with_fields="qpeme0", show=False)
            sigres.plot_qps_vs_e0(exclude_fields=["vUme"], show=False)
            sigres.plot_ksbands_with_qpmarkers(qpattr="sigxme", e0=None, fact=1000, show=False)

        if self.has_nbformat():
            sigres.write_notebook(nbpath=self.get_tmpname(text=True))

        sigres.close()

    def test_interpolator(self):
        """Test QP interpolation."""
        # Get quasiparticle results from the SIGRES.nc database.
        sigres = abilab.abiopen(abidata.ref_file("si_g0w0ppm_nband30_SIGRES.nc"))

        # Interpolate QP corrections and apply them on top of the KS band structures.
        # QP band energies are returned in r.qp_ebands_kpath and r.qp_ebands_kmesh.

        # Just to test call without ks_ebands.
        r = sigres.interpolate(lpratio=5,
                               ks_ebands_kpath=None,
                               ks_ebands_kmesh=None,
                               verbose=0, filter_params=[1.0, 1.0], line_density=10)

        r = sigres.interpolate(lpratio=5,
                               ks_ebands_kpath=abidata.ref_file("si_nscf_GSR.nc"),
                               ks_ebands_kmesh=abidata.ref_file("si_scf_GSR.nc"),
                               verbose=0, filter_params=[1.0, 1.0], line_density=10)

        assert r.qp_ebands_kpath is not None
        assert r.qp_ebands_kpath.kpoints.is_path
        #print(r.qp_ebands_kpath.kpoints.ksampling, r.qp_ebands_kpath.kpoints.mpdivs_shifts)
        assert r.qp_ebands_kpath.kpoints.mpdivs_shifts == (None, None)

        assert r.qp_ebands_kmesh is not None
        assert r.qp_ebands_kmesh.kpoints.is_ibz
        assert r.qp_ebands_kmesh.kpoints.ksampling is not None
        assert r.qp_ebands_kmesh.kpoints.is_mpmesh
        qp_mpdivs, qp_shifts = r.qp_ebands_kmesh.kpoints.mpdivs_shifts
        assert qp_mpdivs is not None
        assert qp_shifts is not None
        ks_mpdivs, ks_shifts = r.ks_ebands_kmesh.kpoints.mpdivs_shifts
        self.assert_equal(qp_mpdivs, ks_mpdivs)
        self.assert_equal(qp_shifts, ks_shifts)

        # Get DOS from interpolated energies.
        ks_edos = r.ks_ebands_kmesh.get_edos()
        qp_edos = r.qp_ebands_kmesh.get_edos()

        r.qp_ebands_kmesh.to_bxsf(self.get_tmpname(text=True))

        # Plot the LDA and the QPState band structure with matplotlib.
        plotter = abilab.ElectronBandsPlotter()
        plotter.add_ebands("LDA", r.ks_ebands_kpath, dos=ks_edos)
        plotter.add_ebands("GW (interpolated)", r.qp_ebands_kpath, dos=qp_edos)

        if self.has_matplotlib():
            plotter.combiplot(title="Silicon band structure", show=False)
            plotter.gridplot(title="Silicon band structure", show=False)

        sigres.close()


class TestSigresPlotter(AbipyTest):
    def test_sigres_plotter(self):
        """Testing SigresPlotter."""
        filenames = [
            "si_g0w0ppm_nband10_SIGRES.nc",
            "si_g0w0ppm_nband20_SIGRES.nc",
            "si_g0w0ppm_nband30_SIGRES.nc",
        ]
        filepaths = [abidata.ref_file(fname) for fname in filenames]

        with SigresPlotter() as plotter:
            plotter.add_files(filepaths)
            repr(plotter); str(plotter)
            assert len(plotter) == len(filepaths)

            if self.has_matplotlib():
                assert plotter.plot_qpgaps(title="QP gaps vs sigma_nband", hspan=0.05, show=False)
                assert plotter.plot_qpenes(title="QP energies vs sigma_nband", hspan=0.05, show=False)
                assert plotter.plot_qps_vs_e0(show=False)

            plotter.close()


class SigresRobotTest(AbipyTest):

    def test_sigres_robot(self):
        """Testing SIGRES robot."""
        filepaths = abidata.ref_files(
            "si_g0w0ppm_nband10_SIGRES.nc",
            "si_g0w0ppm_nband20_SIGRES.nc",
            "si_g0w0ppm_nband30_SIGRES.nc",
        )
        assert abilab.SigresRobot.class_handles_filename(filepaths[0])
        assert len(filepaths) == 3

        with abilab.SigresRobot.from_files(filepaths) as robot:
            assert robot.start is None
            start = robot.trim_paths(start=None)
            assert robot.start == start
            for p, _ in robot:
                assert p == os.path.relpath(p, start=start)

            assert robot.EXT == "SIGRES"
            repr(robot); str(robot)
            assert robot.to_string(verbose=2)
            assert robot._repr_html_()

            df_params = robot.get_dataframe_params()
            self.assert_equal(df_params["nsppol"].values, 1)

            label_ncfile_param = robot.sortby("nband")
            assert [t[2] for t in label_ncfile_param] == [10, 20, 30]
            label_ncfile_param = robot.sortby(lambda ncfile: ncfile.ebands.nband, reverse=True)
            assert [t[2] for t in label_ncfile_param] == [30, 20, 10]

            df_sk = robot.merge_dataframes_sk(spin=0, kpoint=[0, 0, 0])
            qpdata = robot.get_qpgaps_dataframe(with_geo=True)

            if self.has_nbformat():
                robot.write_notebook(nbpath=self.get_tmpname(text=True))

            robot.pop_label(os.path.relpath(filepaths[0], start=start))
            assert len(robot) == 2
            robot.pop_label("foobar")
            new2old = robot.change_labels(["hello", "world"], dryrun=True)
            assert len(new2old) == 2 and "hello" in new2old
