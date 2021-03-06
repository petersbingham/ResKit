import sys

import reskit as rk
import channelutil as cu
import ukrmolmatreader as rmol
import twochanradialwell as tcrw

archive_path = "results"

exceptStr = ("\n\nBad arguments. Should be of form:")+\
'''
python reskit_examples.py 1st 2nd 3rd
where:
 1st: Scattering system. Either:
    radwell, pyrazine, uracil or pbq (para-benzoquinone)
 2nd: Command. Either:
    poles, plotSmat, plotXS, plotQmat, plotQmatEvals or createLatex
 3rd: Max Npts (if 2nd==poles) or plot Npts (if 2nd==plotSmat or 2nd==plotXS)
    optional. Default 40 (if 2nd==poles) or 20 (if 2nd==plotSmat or 2nd==plotXS)
'''

Npts = None
if len(sys.argv) == 4:
    Npts = int(sys.argv[3])
elif len(sys.argv) != 3:
    raise Exception(exceptStr)

input_data_file = None
sl = None
param_path = None
desc_str = sys.argv[1]
num_plot_points = 300

if desc_str == "radwell":
    ang_mom = [0,0]
    param_path = "test_configuration_1.yaml"
elif desc_str == "pyrazine":
    input_data_file = "kmatrix_input_pyrazine.txt"
    ang_mom = [3,5,5]
    sl = slice(0,1200)
    param_path = "test_configuration_2.yaml"
elif desc_str == "uracil":
    input_data_file = "kmatrix_input_uracil.txt"
    ang_mom = [1,2,2,3,3,3]
    param_path = "test_configuration_3.yaml"
elif desc_str == "pbq":
    input_data_file = "kmatrix_input_pbq.txt"
    ang_mom = [1,3,3]
    sl = slice(0,624)
    num_plot_points = 312
    param_path = "test_configuration_2.yaml"
else:
    raise Exception(exceptStr)

rk.use_mpmath_types(dps=100)

if input_data_file is None:
    # System is a radial well
    # Get a calculator with units and channel angular momentum
    calc = rk.get_asym_calc(rk.hartrees, ang_mom)
    # Get a function pointer for the S matrix
    csmat = tcrw.get_Smat_fun(1.0, 2.0, 2.0, calc, 1.0)
    # Initialise the data into the required container
    dmat = rk.get_dmat_from_continuous(rk.Smat, csmat, calc, 1., 8., 1200,
                                       desc_str)
else:
    # System is a molecule
    # Read in the K matrix data
    # Get a calculator with units and channel angular momentum
    calc = rk.get_asym_calc(rk.rydbergs, ang_mom)
    kmatdict,_ = rmol.read_Kmats(input_data_file)
    # Initialise the data into the required container
    dmat = rk.get_dmat_from_discrete(rk.Kmat, kmatdict, calc, desc_str)

# Slice the data set
if sl is not None:
    dmat = dmat[sl]

if sys.argv[2] in ("poles", "plotSmat", "plotXS"):
    sfittool = rk.get_tool(rk.mcsmatfit, dmat, archive_path, param_path)
    if sys.argv[2] == "poles":
        if not Npts:
            Npts = 40
        # Perform the calculation of the poles and the quality indicators
        cfins = sfittool.get_elastic_Fins(range(2,Npts+2,2))
        sfittool.find_stable_Smat_poles(cfins)
    elif sys.argv[2] in ("plotSmat", "plotXS"):
        if not Npts:
            Npts = 20
        # Perform the calculation of the poles and the quality indicators
        csmat = sfittool.get_elastic_Smat(Npts)
        if sys.argv[2] == "plotSmat":
            sfittool.plot_Smat_fit(csmat, num_plot_points=num_plot_points)
        elif sys.argv[1] == "uracil":
            sfittool.plot_XS_fit(csmat, num_plot_points=num_plot_points, logy=True)
        else:
            sfittool.plot_XS_fit(csmat, num_plot_points=num_plot_points)
elif sys.argv[2] in ("plotQmat", "plotQmatEvals"):
    # We use Hartrees here since that is what is used in the UKrmol codes.
    dmat = dmat.convert_ene_units(rk.hartrees)
    sfittool = rk.get_tool(rk.mcsmatfit, dmat, archive_path, param_path)
    if not Npts:
        Npts = 20
    # Perform the calculation of the poles and the quality indicators
    cqmat = sfittool.get_elastic_Qmat(Npts)
    if sys.argv[2] == "plotQmat":
        sfittool.plot_Qmat_fit(cqmat, num_plot_points=num_plot_points, units=rk.eVs)
    elif sys.argv[2] == "plotQmatEvals":
        sfittool.plot_Qmat_evals_fit(cqmat, num_plot_points=num_plot_points, units=rk.eVs)

elif sys.argv[2] == "createLatex":
    sfittool.create_formatted_QI_tables()
else:
    raise Exception(exceptStr)
