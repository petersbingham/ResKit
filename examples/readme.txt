1: Install reskit and all of the dependencies (see README.md).
2: Run the activate script (see README.md).
3: Type at a command prompt in this directory:

python reskit_examples.py system output_produced Npts
where:
 system: Scattering system. Either:
  radwell, pyrazine, uracil or pbq (para-benzoquinone)
 output_produced: Command. Either:
  poles, plotSmat, plotXS or createLatex
 Npts: Either max Npts (if output_produced==poles) or plot Npts (if output_produced==plotSmat or output_produced==plotXS)
  optional. Default 40 (if output_produced==poles) or 20 (if output_produced==plotSmat or output_produced==plotXS)

Eg: python reskit_examples.py radwell poles

The path to the log file will be displayed on the screen. 
The location of all results are detailed in this file. 

The coefficients of the expansion of the S-matrix will be in a subdirectory named coeffs.
The roots of the S-matrix obtained for each step of the calculation will be in a subdirectory named roots.
Finally, the poles identified for each M will will be in a subdirectory named poles. The final result,
that is, the poles identified with their corresponding quality indicators, will be listed in a file called
QIs.dat located in the poles subdirectory.
