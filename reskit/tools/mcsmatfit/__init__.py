import yaml
import os
import tabulate as t
import numpy as np

import pynumwrap as nw
import parsmat as psm
import stelempy as sp
import pynumutil as nu

import toolhelper as th

toolDir = os.path.dirname(os.path.realpath(__file__))
toolName = "mcsmatfit"

QI_file_name = "QIs"
QI_file_ext = ".dat"

QI_file_real = "real"
QI_file_imag = "imag"
QI_file_wdk = "^dk"
QI_file_ENk = "ENk"

class MCSMatFit(th.tool):
    def __init__(self, data, archive_root, param_file_path, silent):
        th.tool.__init__(self, data, archive_root, param_file_path, toolDir,
                         silent)
        #Two internal properties (mainly for testing):
        self.all_coeffs_loaded = False
        self.all_roots_loaded = False
        self._verify_param_caches()

    class RootsList(list):
        def __init__(self, lst=None, n_list=None, asymcalc=None):
            if lst:
                list.__init__(self, lst)
            else:
                list.__init__(self)
            if n_list:
                self.n_list = n_list
            else:
                self.n_list = []
            if asymcalc:
                self.asymcalc = asymcalc
            else:
                self.asymcalc = None

    def _verify_param_caches(self):
        self._verify_param_cache(self._get_root_config_dir(), 
                                 "find_Fin_roots")
        self._verify_param_cache(self._get_pole_config_dir(), 
                                 "find_stable_Smat_poles")
        
    def _check_elastic(self):
        if not self.data.asymcalc.is_elastic():
            msg = "Function not compatible with inelastic systems."
            self.log.write_err(msg)
            raise Exception(msg)

    ##### General file and string Functions #####

    def _get_coeff_dir_base(self):
        return self.archive_root+"coeffs"+os.sep
    def _get_root_config_dir_base(self):
        return self.archive_root+"roots"+os.sep
    def _get_pole_dir_base(self):
        return self.archive_root+"poles"+os.sep

    def _get_root_config_dir(self):
        return self._get_root_config_dir_base()+th.cfg_name(self.param_file_path)
    def _get_pole_config_dir(self):
        return self._get_pole_dir_base()+th.cfg_name(self.param_file_path)

    def _get_root_config_path(self):
        return self._get_root_config_dir()+os.sep+self._get_config_cache_name()
    def _get_pole_config_path(self):
        return self._get_pole_config_dir()+os.sep+self._get_config_cache_name()

    def _get_input_desc_str(self, Npts, ris0):
        return "Npts="+str(Npts)+"_"+"S="+str(ris0[0])+"_E="+str(ris0[1]-1)

    def _get_num_header(self, asymcalc):
        return ["k","E ("+asymcalc.get_units()+")"]

    def _get_kE_row(self, val, asymcalc):
        k_str = str(val).replace('(','').replace(')','').replace(' ','')
        e_str = str(asymcalc.ke(val)).replace('(','').replace(')','')
        e_str = e_str.replace(' ','')
        return [k_str, e_str]

    def _get_kE_row_split(self, val, asymcalc):
        k_str = [str(val.real),str(val.imag)]
        e_str = [str(asymcalc.ke(val).real), str(asymcalc.ke(val).imag)]
        return [k_str, e_str]

    ##### Coefficient File #####

    def _get_coeff_dir(self, Npts, ris0):
        a = self._get_coeff_dir_base()+th.cfg_name(self.param_file_path)
        b = os.sep+self._get_input_desc_str(Npts, ris0)
        return a + b

    def _get_coeff_path(self, coeff_dir, type_str, i):
        return coeff_dir+os.sep+type_str+"_"+str(i)+".dat"

    def _fix_numpy_file(self, file_name):
        f1 = th.fropen(file_name)
        f2 = th.fwopen(file_name+"_temp")
        for line in f1:
            th.fw(f2, line.replace("+-", '-').replace("\r\n", '\n'))
        f1.close()
        f2.close()
        os.remove(file_name)
        os.rename(file_name + "_temp", file_name)

    def _save_coeff(self, coeff, path, type_str):
        for i,cmat in enumerate(coeff):
            coeff_path = self._get_coeff_path(path, type_str, i)
            if nw.mode == nw.mode_python:
                np.savetxt(coeff_path, cmat, delimiter=",", newline='\n')
                self._fix_numpy_file(coeff_path)
            else:
                with th.fwopen(coeff_path) as f:
                    th.fw(f, cmat)

    def _save_coeffs(self, coeffs, Npts, ris0):
        if self.archive_root is not None:
            coeff_dir = self._get_coeff_dir(Npts, ris0)
            if not os.path.isdir(coeff_dir):
                os.makedirs(coeff_dir)
            self._save_coeff(coeffs[0], coeff_dir, "A")
            self._save_coeff(coeffs[1], coeff_dir, "B")
            self.log.write_msg("Coeffs saved to: "+coeff_dir)

    def _split_mp_rows(self, s):
        if "(" in s:
            return s.split("(")[1:]
        else:
            return s.split("  ")

    def _fix_mp_mat_str(self, s):
        return s.replace("[","").replace("]","").replace("[","").replace(")","")

    def _load_coeff(self, Npts, path, type_str):
        coeffs = []
        for i in range(psm.get_num_coeff_for_Npts(Npts)):
            coeff_path = self._get_coeff_path(path, type_str, i)
            if not os.path.isfile(coeff_path):
                return None
            try:
                if nw.mode == nw.mode_python:
                    coeff = np.asmatrix(np.loadtxt(coeff_path,
                                                   dtype=np.complex128,
                                                   delimiter=","))
                    coeffs.append(coeff)
                else:
                    with th.fropen(coeff_path) as f:
                        s1 = f.read()
                        l1 = s1.split("\n")
                        l2 = [self._split_mp_rows(s) for s in l1]
                        l3 = [map(lambda s:self._fix_mp_mat_str(s),l) for l in l2]
                        coeff = nw.mpmath.matrix(l3)
                        coeffs.append(coeff)
            except Exception as inst:
                self.log.write_err(str(inst))
                raise
        return coeffs

    def _load_coeff_set(self, Npts, coeff_dir):
        coeffA = self._load_coeff(Npts, coeff_dir, "A")
        coeffB = self._load_coeff(Npts, coeff_dir, "B")
        if coeffA is not None and coeffB is not None:
            self.log.write_msg("Coefficients loaded from: "+coeff_dir)
            return coeffA, coeffB
        return None

    def _load_coeffs(self, Npts, ris0):
        if self.archive_root is not None:
            # First try the supplied config.
            coeff_dir = self._get_coeff_dir(Npts, ris0)
            if os.path.isdir(coeff_dir):
                return self._load_coeff_set(Npts, coeff_dir)
            # Now look for other configs that have compatible coeffs.
            coeff_base_dir = self._get_coeff_dir_base()
            if os.path.isdir(coeff_base_dir):
                for coeff_config_dir_name in th.get_sub_dirs(coeff_base_dir):
                    coeff_config_dir = coeff_base_dir+os.sep+coeff_config_dir_name
                    for coeffDirName in th.get_sub_dirs(coeff_config_dir):
                        if "Npts="+str(Npts)+"_" in coeffDirName:
                            coeff_dir = coeff_config_dir+os.sep+coeffDirName
                            return self._load_coeff_set(Npts, coeff_dir)
        return None

    def _get_coefficients(self, Npts, ris0):
        coeffs = self._load_coeffs(Npts, ris0)
        if coeffs is None:
            dsmat = self.data[ris0[0]:ris0[1]:ris0[2]].to_dSmat()
            coeffs = psm.calculate_coefficients(dsmat, dsmat.asymcalc)
            self.log.write_msg("Coefficients calculated")
            self._save_coeffs(coeffs, Npts, ris0)
            self.all_coeffs_loaded = False
        return coeffs

    ##### Root File #####

    def _get_root_path(self, root_dir, Npts, ris0):
        return root_dir+os.sep+self._get_input_desc_str(Npts, ris0)+".dat"

    def _save_root_config(self, p):
        with th.fwopen(self._get_root_config_path()) as f:
            th.fw(f, str(p))

    def _get_root_file_header_str(self, Npts, ris):
        N_str = "Npts="+str(Npts)
        Emin_str = "Emin="+str(ris[0][0])+"("+str(ris[1][0])+")"
        Emax_str = "Emax="+str(ris[0][1]-1)+"("+str(ris[1][1])+")"
        step_str = "step="+str(ris[0][2])
        return N_str+", "+Emin_str+", "+Emax_str+", "+step_str+"\n\n"

    def _save_roots(self, Npts, ris, roots, asymcalc, p):
        if self.archive_root is not None:
            root_dir = self._get_root_config_dir()
            if not os.path.isdir(root_dir):
                os.makedirs(root_dir)

            header = self._get_num_header(asymcalc)
            rows = []
            for root in roots:
                rows.append(self._get_kE_row(root, asymcalc))

            root_path = self._get_root_path(root_dir, Npts, ris[0])
            with th.fwopen(root_path) as f:
                th.fw(f, self._get_root_file_header_str(Npts, ris))
                th.fw(f, t.tabulate(rows,header))
                th.fw(f, "\ncomplete")
                self.log.write_msg("Roots saved to: "+root_path)

            self._save_root_config(p)

    def _get_root_path_if_exists(self, root_dir, Npts, ris0):
        root_path = self._get_root_path(root_dir, Npts, ris0)
        if os.path.isfile(root_path):
            return root_path
        return None

    def _find_compatible_root_dir(self, Npts, ris):
        # First try the supplied config.
        rootConfigDir = self._get_root_config_dir()
        if os.path.isdir(rootConfigDir):
            root_path = self._get_root_path_if_exists(rootConfigDir, Npts,
                                                      ris[0])
            if root_path is not None:
                return root_path
        # Now look for other configs that have compatible roots.
        rootBaseDir = self._get_root_config_dir_base()
        if os.path.isdir(rootBaseDir):
            for rootConfigDirName in th.get_sub_dirs(rootBaseDir):
                rootConfigDir = rootBaseDir+os.sep+rootConfigDirName
                if self._does_param_cache_match(rootConfigDir,
                                                "find_Fin_roots"):
                    root_path = self._get_root_path_if_exists(rootConfigDir, 
                                                              Npts, ris[0])
                    if root_path is not None:
                        return root_path
        return None

    def _load_roots(self, Npts, ris):
        if self.archive_root is not None:
            root_path = self._find_compatible_root_dir(Npts, ris)
            if root_path is not None:
                try:
                    with th.fropen(root_path) as f:
                        fndStart = False
                        roots = []
                        for l in f:
                            if not fndStart:
                                if "---" in l:
                                    fndStart = True
                                continue
                            elif "complete" not in l:
                                roots.append(nw.complex(l.split()[0]))
                        if "complete" not in l:
                            self.log.write_err("Incomplete root file")
                            return None
                        self.log.write_msg("Roots loaded from: "+root_path)
                        return roots
                except Exception as inst:
                    self.log.write_err(str(inst))
                    raise
        return None

    def _get_roots(self, p, cfin, asymcalc):
        self.log.write_call("_get_roots("+str(cfin.fitInfo[0])+")", True)
        roots = self._load_roots(cfin.fitInfo[0], cfin.fitInfo[1])
        if roots is None:
            csca = cfin.determinant(**p["cSympyPolyMat_determinant"])
            self.log.write_msg("Determinant calculated")
            roots = csca.find_roots(**p["cSympyPolySca_find_roots"])
            self.log.write_msg("Roots calculated")
            self._save_roots(cfin.fitInfo[0], cfin.fitInfo[1], roots, asymcalc,
                             p)
            self.all_roots_loaded = False
        self.log.write_call_end("_get_roots")
        return roots

    ##### Pole Save #####

    def _get_pole_dir(self, n_list):
        return self._get_pole_config_dir() + os.sep+str(n_list).replace(' ','')

    def _get_pole_path(self, pole_dir, dk):
        return pole_dir+os.sep+"dk"+nu.sci_str(dk)+".dat"

    def _save_pole_config(self, p):
        with th.fwopen(self._get_pole_config_path()) as f:
            th.fw(f, str(p))

    def _get_pole_file_header_str(self, num_poles, asymcalc):
        return str(num_poles)+" poles, "+asymcalc.get_units()+"\n\n"

    def _get_pole_row(self, Npts, pole, status, asymcalc):
        return [str(Npts), status] + self._get_kE_row(pole, asymcalc)

    def _save_pole_data(self, n_list, poleData, asymcalc, p):
        if self.archive_root is not None:
            pole_dir = self._get_pole_dir(n_list)
            if not os.path.isdir(pole_dir):
                os.makedirs(pole_dir)

            for i,dk in enumerate(poleData[2]):
                header = ["Npts","status"] + self._get_num_header(asymcalc)
                rows = []
                for pole in poleData[0][i]:
                    for j in sorted(pole.keys()):
                        m = self._get_pole_row(n_list[j], pole[j][0],
                                               pole[j][2], asymcalc)
                        rows.append(m)
                    rows.append(["","","",""])

                pole_path = self._get_pole_path(pole_dir, dk)
                with th.fwopen(pole_path) as f:
                    th.fw(f, self._get_pole_file_header_str(len(poleData[0][i]),
                                                            asymcalc))
                    th.fw(f, t.tabulate(rows,header))
                    self.log.write_msg("Poles saved to: "+pole_path)
            self._save_pole_config(p)

    ##### QI Save #####

    def _get_QI_path(self, pole_dir):
        return pole_dir+os.sep+QI_file_name

    def _get_QI_file_header_str(self, num_poles, asymcalc):
        return str(num_poles)+" poles, "+asymcalc.get_units()+"\n\n"

    def _get_QI_row(self, poleQI, asymcalc):
        return self._get_kE_row_split(poleQI[0], asymcalc) + [str(poleQI[1]),
                                                              str(poleQI[2])]

    def _save_QI_data_file(self, QI_path, pole_dat, asymcalc, type_str, index):
        path = QI_path + "_" + type_str + QI_file_ext
        with th.fwopen(path) as f:
            th.fw(f, self._get_QI_file_header_str(len(pole_dat[0]), asymcalc))
            for i,poleQI in enumerate(pole_dat[0]):
                row = self._get_QI_row(poleQI, asymcalc)
                pid = type_str+"["+str(i)+"]."
                th.fw(f, pid+QI_file_real+"="+row[index][0]+"\n")
                th.fw(f, pid+QI_file_imag+"="+row[index][1]+"\n")
                th.fw(f, QI_file_wdk+"="+row[2]+"\n")
                th.fw(f, QI_file_ENk+"="+row[3]+"\n\n")
        return path

    def _save_QI_data(self, n_list, pole_dat, asymcalc):
        if self.archive_root is not None:
            rows = []
            QI_path = self._get_QI_path(self._get_pole_dir(n_list))
            path = self._save_QI_data_file(QI_path, pole_dat, asymcalc, "k", 0)
            self.log.write_msg("QI data saved to: " + path)
            path = self._save_QI_data_file(QI_path, pole_dat, asymcalc, "E", 1)
            self.log.write_msg("QI data saved to: " + path)

    def _update_container_strings(self, Npts, cont, chart_title=None):
        cont.set_source_str(self.data.get_source_str())
        cont.append_hist_str(self.data.get_hist_str())
        cont.append_hist_str("sfit_mc_rat_N="+str(Npts))
        if chart_title is not None:
            cont.set_chart_title("Fin")

    ##### Formattted Tables #####

    def _get_table_format_parameters(self):
        with th.fropen(self.param_file_path) as f:
            config = yaml.load(f.read())
            p = config["create_formatted_QI_tables"]["num_format"]
            return p["strip_zeros"], p["min_fixed"], p["max_fixed"], \
                   p["show_zero_exponent"], float(p["ztol"])

    def _get_formatted_lines(self, subdir, file_name, sig_digits,
                             col_delim="$$", row_delim=None):
        strip_zeros, min_fixed, max_fixed, show_zero_exponent, ztol = \
                self._get_table_format_parameters()
        desc = ""
        new_lines = []
        file_path = subdir + os.sep + file_name
        with th.fropen(file_path) as f:
            new_line = ""
            for i,l in enumerate(f):
                if i == 0:
                    desc = l
                elif "=" in l:
                    num_str = l.split('=')[1]
                    if QI_file_real in l or QI_file_imag in l:
                        num_str = nw.num_str_real(num_str, sig_digits,
                                                  strip_zeros, min_fixed,
                                                  max_fixed, show_zero_exponent,
                                                  ztol)
                    elif QI_file_wdk in l:
                        num_str = nw.num_str_real(num_str, 1, True, 1, 1, False)
                        num_str = num_str.replace(".0","")
                    new_line += num_str
                    if QI_file_ENk in l:
                        if row_delim is not None:
                            new_line += row_delim
                            new_lines.append(new_line)
                        else:
                            new_lines.append(new_line.split("$$"))
                        new_line = ""
                    else:
                        if QI_file_imag in l:
                            if new_line[0] == "+":
                                new_line = new_line[1:]
                        new_line += col_delim
        return desc, new_lines

    def _formatted_QI_table_name(self, sig_digits, use_energies, type_str):
        if use_energies:
            name = "_E_"
        else:
            name = "_k_"
        return name + type_str + "_sf" + str(sig_digits)

    def _write_formatted_QI_table(self, start, new_lines, end, subdir,
                                  sig_digits, use_energies, tab_type):
        name = self._formatted_QI_table_name(sig_digits, use_energies, tab_type)
        save_path = subdir+os.sep+"QIs"+name+".dat"
        with th.fwopen(save_path) as f:
            th.fw(f, start)
            for l in new_lines:
                th.fw(f, l)
            th.fw(f, end)
            self.log.write_msg("Formatted QI table saved to: " + save_path)

    def _create_latex_QI_table(self, use_energies, subdir, orig_file_name,
                               sig_digits):

        start = "\\begin{table}[h!]\n"+\
                "\\begin{center}\n"+\
                "\\begin{tabular}{c c c c}\n"+\
                "\\hline\n"+\
                "\\textbf{Real energy} & \\textbf{Imag energy} & $\\wedge dk$ & $\\Sigma Nk$ \\\\\n"+\
                "\\hline\n"

        desc, new_lines = self._get_formatted_lines(subdir, orig_file_name, 
                                                    sig_digits,
                                                    " & ", "\\\\\n\\hline\n")

        end =   "\\end{tabular}\n"+\
                "\end{center}\n"+\
                "\caption{}\n"+\
                "\label{}\n"+\
                "\end{table}"

        self._write_formatted_QI_table(start, new_lines, end, subdir,
                                       sig_digits, use_energies, "latex")

    def _create_raw_QI_table(self, use_energies, subdir, file_name, sig_digits):
        header = ["real", "imag", "^dk", "ENk"]
        desc, new_lines = self._get_formatted_lines(subdir, file_name,
                                                    sig_digits)
        name = self._formatted_QI_table_name(sig_digits, use_energies, "raw")
        save_path = subdir+os.sep+"QIs"+name+".dat"
        with th.fwopen(save_path) as f:
            th.fw(f, desc)    
            th.fw(f, t.tabulate(new_lines, header, 
                                floatfmt="."+str(sig_digits)+"g"))
            self.log.write_msg("Formatted QI table saved to: " + save_path)

    ##### Others #####

    def _check_for_fit_plot(self, csmat):
        try:
            csmat.MCSMatFit_SplotCompatible
        except Exception:
            self.log.write_err("Not a csmat")
            raise

    def _filterRoots(self, all_roots, point, atol):
        f = lambda v : not (    abs(v.real) <= point.real + atol.real \
                            and abs(v.real) >= point.real - atol.real \
                            and v.imag <= point.imag + atol.imag \
                            and v.imag >= point.imag - atol.imag)
        lst = [[root for root in filter(f,all_root)] for all_root in all_roots]
        return MCSMatFit.RootsList(lst, all_roots.n_list, all_roots.asymcalc)

    ##### Public API #####

    def get_elastic_Fin(self, Npts):
        """
        Performs an Fin fit using the specified number of fit points and 
        returns a cPolykmat.

        Parameters
        ----------
        Npts : int
            Number of points to use in the fit. Must be an even number.

        Returns
        -------
        cfin : cPolykmat
        """
        self.log.write_call("get_elastic_Fin("+str(Npts)+")")
        self._check_elastic()
        ris = self.data.get_slice_indices(num_points=Npts)
        self.log.write_msg("Calculating for Npts="+str(Npts)+",slice:"+str(ris))
        self.all_coeffs_loaded = True
        coeffs = self._get_coefficients(Npts, ris[0])
        cfin = psm.get_elastic_Fin_fun(coeffs, self.data.asymcalc)
        cfin.fitInfo = (Npts,ris)
        self._update_container_strings(Npts, cfin, "Fin")
        self.log.write_msg("cfin calculated")
        self.log.write_call_end("get_elastic_Fin")
        return cfin

    def get_elastic_Fins(self, Npts_list):
        """
        Performs Fin fits using the specified list of fit points and returns a 
        list of cPolykmat.

        Parameters
        ----------
        Npts_list : list of ints
            List of fit points, each of which will be used to produce a fit.

        Returns
        -------
        cfins : list of cPolykmat
        """
        self.log.write_call("get_elastic_Fins("+str(Npts_list)+")")
        self._check_elastic()
        cfins = []
        for Npts in Npts_list:
            cfins.append(self.get_elastic_Fin(Npts))
        self.log.write_call_end("get_elastic_Fins")
        return cfins

    def find_Fin_roots(self, cfins, internal=False):
        """
        Finds the roots of a list of parameterised Fins returning as a list of 
        complex or mpmath.mpc. There are additional advanced parameters in the
        tool yml file.

        Parameters
        ----------
        cfins : list of cPolykmat
            Container representing the parameterised Fins.

        Returns
        -------
        all_roots : list of float or mpmath.mpc
        """
        self.log.write_call("find_Fin_roots("+str(map(lambda x: x.fitInfo[0],
                                                     cfins))+")", internal)

        all_roots = MCSMatFit.RootsList()
        if len(cfins) > 0:
            with th.fropen(self.param_file_path) as f:
                config = yaml.load(f.read())
                p = config["find_Fin_roots"]
                self.log.write_parameters(p)
                self.all_roots_loaded = True
                for cfin in cfins:
                    if all_roots.asymcalc is not None:
                        assert all_roots.asymcalc == cfin.asymcalc
                    all_roots.asymcalc = cfin.asymcalc
                    roots = self._get_roots(p, cfin, all_roots.asymcalc)
                    all_roots.append(roots)
                    all_roots.n_list.append(cfin.fitInfo[0])
        self.log.write_call_end("find_Fin_roots")
        return all_roots

    def find_stable_Smat_poles(self, cfins_or_roots):
        """
        Finds the S-matrix poles as the stable roots of the Fins from either
        a list of Fins or from a list of Fin roots returning as a tuple of 
        lists of pole data. There are additional advanced parameters in the tool
        yml file.

        Parameters
        ----------
        cfins_or_roots : list of either cfins or list of floats
            As returned from either get_elastic_Fins or find_Fin_roots.

        Returns
        -------
        pole_dat : list of lists.
            List of poles and their calculated quality indicators.
        amalgPoleDat : list of lists.
            List of poles that had been combined according to the amalgamation
            threshold specified in the paramFile.
        """
        try:
            param_str = str(map(lambda x: x.fitInfo[0], cfins_or_roots))
        except AttributeError:
            param_str = str(cfins_or_roots.n_list)

        self.log.write_call("find_stable_Smat_poles("+param_str+")")
        if len(cfins_or_roots) > 0:
            try:
                cfins_or_roots.n_list # Test for the parameter type.
                all_roots = cfins_or_roots
            except AttributeError:
                all_roots = self.find_Fin_roots(cfins_or_roots, True)
            if len(all_roots) > 0:
                with th.fropen(self.param_file_path) as f:
                    config = yaml.load(f.read())
                    p = config["find_stable_Smat_poles"]
                    self.log.write_parameters(p)
                    if "zero_filt_thres" in p:
                        pp = p["zero_filt_thres"]
                        all_roots = self._filterRoots(all_roots, 
                                                      nw.complex(pp["point"]),
                                                      nw.complex(pp["atol"]))
                    pp = p["stelempy"]
                    end_rtol = None
                    try:
                        end_rtol = float(pp["end_rtol"])
                    except TypeError:
                        pass

                    ztol = float(pp["ztol"])
                    ratcmp = sp.num.RationalCompare1(ztol=ztol)
                    poleData = sp.calculate_convergence_groups_range(all_roots,
                                                ratcmp, float(pp["start_rtol"]),
                                                end_rtol, int(pp["cfsteps"]))
                    self.log.write_msg("Convergence groups calculated")
                    self._save_pole_data(all_roots.n_list, poleData,
                                         all_roots.asymcalc, p)

                    amalg_ratcmp = None
                    amalg_rtol = float(pp["amalg_rtol"])
                    if amalg_rtol != 0.:
                        amalg_ratcmp = sp.num.RationalCompare1(amalg_rtol, ztol)
                    pole_dat = sp.calculate_QIs_from_range(poleData,
                                                           amalg_ratcmp)
                    self.log.write_msg("QIs calculated")
                    self._save_QI_data(all_roots.n_list, pole_dat, 
                                       all_roots.asymcalc)
                    self.log.write_call_end("find_stable_Smat_poles")
                    return pole_dat
        self.log.write_call_end("find_stable_Smat_poles")
        return None, None

    def create_formatted_QI_tables(self, table_type="latex_E",
                                   sig_digits=10):
        """
        Creates and formats all the QIs.dat tables in the current archive.
        Numbers are formatted according to the supplied parameters. There are
        additional advanced parameters in the tool yml file.

        Parameters
        ----------
        table_type : string
            The table type to create and whether to use energies or wavenumbers.
            The string should contain the table type (latex, raw) and the
            quantity k, E). eg latex_E.
        sig_digits : int
            The number of significant digits to represent the numeric values.
        """
        para_str = table_type +", " + str(sig_digits)
        self.log.write_call("create_formatted_QI_tables("+para_str+")")
        indic = "_k"
        if "E" in table_type:
            indic = "_E"
        QI_file = QI_file_name + indic + QI_file_ext
        for subdir, _, files in os.walk("."):
            for orig_file_name in files:
                if orig_file_name == QI_file:
                    if "latex" in table_type:
                        self._create_latex_QI_table("E" in table_type, subdir,
                                                    orig_file_name, sig_digits)
                    elif "raw" in table_type:
                        self._create_raw_QI_table("E" in table_type, subdir,
                                                  orig_file_name, sig_digits)
        self.log.write_call_end("create_formatted_QI_tables")

    def get_elastic_Smat(self, Npts):
        """
        Performs S-matrix fits using the specified number of fit points and 
        returns a cSmat.

        Parameters
        ----------
        Npts : int
            Number of points to use in the fit. Must be an even number.

        Returns
        -------
        csmat : cSmat
        """
        self.log.write_call("get_elastic_Smat("+str(Npts)+")")
        self._check_elastic()
        ris = self.data.get_slice_indices(num_points=Npts)
        self.log.write_msg("Calculating for slice:"+str(ris))
        self.all_coeffs_loaded = True
        coeffs = self._get_coefficients(Npts, ris[0])
        csmat = psm.get_elastic_Smat_fun(coeffs, self.data.asymcalc)
        csmat.fitInfo = (Npts,ris)
        csmat.MCSMatFit_SplotCompatible = True
        self._update_container_strings(Npts, csmat)
        self.log.write_msg("Calculation completed")
        self.log.write_call_end("get_elastic_Smat")
        return csmat

    def plot_Smat_fit(self, csmat, num_plot_points=None, units=None, i=None,
                      j=None, logx=False, logy=False, imag=False, show=True):
        """
        Plots the original data, the fit points used and the resultant S-matrix
        for the specified element/s. There are additional advanced parameters
        in the tool yml file.

        Parameters
        ----------
        csmat : cSmat
            Fitted S-matrix returned from get_elastic_Smat.
        num_plot_points, units, i, j, logx, logy, imag, show
            Refer to the chart tool for description.
        """
        Npts = csmat.fitInfo[0]
        self.log.write_call("plot_Smat_fit("+str(Npts)+")")
        self._check_for_fit_plot(csmat)
        ret = self._prepare_for_fit_plot(num_plot_points)  
        if ret is not None:
            p, ln, orig = ret

            orig = orig.to_dSmat()
            orig = self._reduceDimensions(orig, i, j)

            ris0 = csmat.fitInfo[1][0]
            fit_pnts = self.data[ris0[0]:ris0[1]:ris0[2]]
            fit_pnts = fit_pnts.to_dSmat()
            fit_pnts = self._reduceDimensions(fit_pnts, i, j)

            rng = orig.get_range()
            dsmat = csmat.discretise(rng[0], rng[1], ln)
            fit = self._reduceDimensions(dsmat, i, j)

            title = "S matrix fit for Npts="+str(Npts)
            if i and j:
                title += ", m="+str(i+1)+", n="+str(j+1)
            elif i:
                title += ", m="+str(i+1)
            elif j:
                title += ", n="+str(j+1)

            self._plot_fit(p, title, orig, fit_pnts, fit, num_plot_points, units,
                          logx, logy, imag, show)

        self.log.write_call_end("plot_Smat_fit")

    def plot_totXS_fit(self, csmat, num_plot_points=None, units=None,
                       logx=False, logy=False, show=True):
        """
        Plots total cross section conversions from the original S-matrix data,
        the fit points used and the resultant S-matrix. Refer to the chart tool
        for a description of the parameters. There are additional advanced
        parameters in the tool yml file.

        Parameters
        ----------
        csmat : cSmat
            Fitted S-matrix returned from get_elastic_Smat.
        num_plot_points, units, logx, logy, show
            Refer to the chart tool for description.
        """
        Npts = csmat.fitInfo[0]
        self.log.write_call("plot_totXS_fit("+str(Npts)+")")
        self._check_for_fit_plot(csmat)
        ret = self._prepare_for_fit_plot(num_plot_points)  
        if ret is not None:
            p, ln, orig = ret

            orig = orig.to_dXSmat().to_dTotXSsca()

            ris0 = csmat.fitInfo[1][0]
            fit_pnts = self.data[ris0[0]:ris0[1]:ris0[2]]
            fit_pnts = fit_pnts.to_dXSmat().to_dTotXSsca()

            rng = orig.get_range()
            dsmat = csmat.discretise(rng[0], rng[1], ln)
            fit = dsmat.to_dXSmat().to_dTotXSsca()

            title = "Total Cross Section fit for Npts="+str(Npts)

            self._plot_fit(p, title, orig, fit_pnts, fit, num_plot_points, units,
                          logx, logy, False, show)

        self.log.write_call_end("plot_totXS_fit")
