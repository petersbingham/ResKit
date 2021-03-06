## Installation Issues
  - `ImportError: No module named reskit`
    - This arises if the interpreter cannot find the module in the PYTHONPATH. Possible causes if you are using a virtulenv:
      - You haven't installed reskit at all (see [README.md](https://github.com/petersbingham/reskit/blob/master/README.md)).
      - You have not activated your virtulenv before invoking the interpreter (see [README.md](https://github.com/petersbingham/reskit/blob/master/README.md)).
      - You did not activate the virtulenv prior to intalling reskit and its dependencies. In this case the dependencies will likely have been installed into your global python location (see [README.md](https://github.com/petersbingham/reskit/blob/master/README.md) for correct sequence of commands).

  - `ERROR: virtualenv is not compatible with this system or executable`
    - This will arise if you try and use virtualenv with an anaconda distribution.

  - With Anaconda on Linux: `conda Error: Package missing in current linux-64 channels:`
    - Try adding the channel with the command: `conda config --add channels anaconda`

  - With Anaconda on Linux: `conda Error: Package missing in current linux-64 channels:` with the `reskit` dependencies
    - Try installing `pip` and `git` and piping the dependencies: `conda install git pip` and `pip install -r requirements.txt`

  - Errors containing things like `There was a problem confirming the ssl certificate:` or `InsecurePlatformWarning` after executing pip.
    - You need to use a more recent version of python. If on Linux and you can't install into the root see: http://thelazylog.com/install-python-as-local-user-on-linux/. In this case you may not have the required libtk dependencies. See the bullet below on how to resolve this.

  - `ImportError: libtk8.5.so: cannot open shared object file: No such file or directory`
    - libtk8.5 is a runtime included as part of the standard python installation that is required by Matplotlib. If this exception occurs then it can't be found. Either libtk is not present in the path or an incorrect version has been installed into the virtualenv. The installed version needs to be compatible with the Matplotlib version specified in the [requirements.txt](https://github.com/petersbingham/reskit/blob/master/requirements.txt). Possible fixes: 
      - virtualenv will setup using the default python version or that specified in the virtualenv script shebang. Use the version of python suggested in [README.md](https://github.com/petersbingham/reskit/blob/master/README.md). This will have proper support for the Matplotlib version specified in [requirements.txt](https://github.com/petersbingham/reskit/blob/master/requirements.txt).
      - Install a version of Matplotlib that supports your libtk. If you've already installed your virtualenv as instructed then `pip uninstall Matplotlib` and `pip install Matplotlib==VERSION_NUM` or change the version number in the [requirements.txt](https://github.com/petersbingham/reskit/blob/master/requirements.txt) prior to setting up your virtualenv.
      - If you are compiling python from source and then creating a virtualenv against this then you will need to ensure that you separately build the libtk. Either that or as a workaround you can add a location of the libtk dependencies to the library path (eg `export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/csoft/epd-7.3.2full/lib"`). You might want to do this if you only have older python distributions in your root (which you don't have sudo for) and are therefore forced to build a recent version in your user space and don't want to go to the effort of also building the libtk.

  - `ImportError: /home/path/.local/lib/python2.7/site-packages/kiwisolver.so: undefined symbol: PyUnicodeUCS2_AsUTF8String`
    - This arises from unicode incompatibilities between python and dependent libraries.
    - Firstly check your virtual env path that the dependencies aren't being picked up somewhere other than the virtualenv.
    - http://effbot.org/pyfaq/when-importing-module-x-why-do-i-get-undefined-symbol-pyunicodeucs2.htm

## General Usage Issues
  - `IOError: [Errno 2] No such file or directory: 'test-configuration-1.yaml'` when running the reskit examples.
    - The examples look for their configuration files in the working directory. You need to invoke the interpreter from within the examples directory.
  - `RuntimeError: Invalid DISPLAY variable` when showing plots on Linux.
    - Can occur when you're running from an ssh to another machine. To fix ssh with the X option: `ssh -X remote_host`
  - Other exceptions.
    - Check you are using the correct version of python and that all the dependencies are correctly installed with the recommended versions ([requirements.txt](https://github.com/petersbingham/reskit/blob/master/requirements.txt)).
    
## mcsmatfit Tool Issues
  - `mpmath.libmp.libhyper.NoConvergence: convergence to root failed; try n < 100 or maxsteps > 5000`
    - Make the suggested changes to the parameters.
    - Alternatively try moving or extending the energy range of your input data-set.
  - `ValueError: matrix is numerically singular`
    - Use mpmath types and/or increase the precision. eg `rk.use_mpmath_types(dps=200)`.
