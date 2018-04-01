import yaml
import os
import io
import sys
import copy
import os.path
import tabulate as t

resultsRoot = None
configDir = os.path.dirname(os.path.realpath(__file__))
configDef = configDir + "/sfit_mc_elastic-default.yml"
parmaFilePaths = [configDef]

import pynumwrap as nw
import parSmat as psm
import stelempy as sp
import pynumutil as nu

import numpy as np

##### Some internal properties (mainly for testing) #####

allCoeffsLoaded = False
allRootsLoaded = False

##### General file and string Functions #####

def _ropen(fileName):
    return io.open(fileName, 'r', newline='\n', encoding="utf-8")
def _wopen(fileName):
    return io.open(fileName, 'w', newline='\n', encoding="utf-8")
def _w(f, o):
    f.write(unicode(o))

def _getInputDescStr(N, ris0):
    return "N="+str(N)+"_"+"S="+str(ris0[0])+"_E="+str(ris0[1])

def _getNumHeader(asymCal):
    return ["k","E ("+asymCal.getUnits()+")"]

def _getkERow(val, asymCal):
    kstr = str(val).replace('(','').replace(')','').replace(' ','')
    Estr = str(asymCal.ke(val)).replace('(','').replace(')','').replace(' ','')
    return [kstr, Estr]

##### Coefficient File #####

def _fixNumpyFile(fileName):
    f1 = _ropen(fileName)
    f2 = _wopen(fileName+"_temp")
    for line in f1:
        _w(f2, line.replace("+-", '-').replace("\r\n", '\n'))
    f1.close()
    f2.close()
    os.remove(fileName)
    os.rename(fileName + "_temp", fileName)

def _getCoeffPath(N, ris0):
    return resultsRoot+"coeffs"+os.sep+_getInputDescStr(N, ris0)

def _getCoeffFileName(path, typeStr, i):
    return path+os.sep+typeStr+"_"+str(i)+".dat"

def _saveCoeff(coeff, path, typeStr):
    for i,cmat in enumerate(coeff):
        fileName = _getCoeffFileName(path, typeStr, i)
        if nw.mode == nw.mode_python:
            np.savetxt(fileName, cmat, delimiter=",", newline='\n')
            _fixNumpyFile(fileName)
        else:
            with _wopen(fileName) as f:
                _w(f, cmat)

def _saveCoeffs(coeffs, N, ris0):
    if resultsRoot is not None:
        path = _getCoeffPath(N, ris0)
        if not os.path.isdir(path):
            os.makedirs(path)
        _saveCoeff(coeffs[0], path, "A")
        _saveCoeff(coeffs[1], path, "B")

def _splitmpRows(s):
    if "(" in s:
        return s.split("(")[1:]
    else:
        return s.split("  ")

def _fixmpMathMatStr(s):
    return s.replace("[","").replace("]","").replace("[","").replace(")","")

def _loadCoeff(N, path, typeStr):
    coeffs = []
    for i in range(psm.getNumCoeffForN(N)):
        fileName = _getCoeffFileName(path, typeStr, i)
        if not os.path.isfile(fileName):
            return None
        try:
            if nw.mode == nw.mode_python:
                coeff = np.asmatrix(np.loadtxt(fileName, dtype=np.complex128,
                                               delimiter=","))
                coeffs.append(coeff)
            else:
                with _ropen(fileName) as f:
                    s1 = f.read()
                    l1 = s1.split("\n")
                    l2 = [_splitmpRows(s) for s in l1]
                    l3 = [map(lambda s:_fixmpMathMatStr(s),l) for l in l2]
                    coeff = nw.mpmath.matrix(l3)
                    coeffs.append(coeff)
        except Exception as inst:
            # TODO log
            return None
    return coeffs

def _loadCoeffs(N, ris0):
    if resultsRoot is not None:
        path = _getCoeffPath(N, ris0)
        if os.path.isdir(path):
            coeffA = _loadCoeff(N, path, "A")
            coeffB = _loadCoeff(N, path, "B")
            if coeffA is not None and coeffB is not None:
                return coeffA, coeffB
    return None

def _getCoefficients(dSmat, N, ris0):
    global allCoeffsLoaded
    allCoeffsLoaded = True
    dSmat2 = dSmat[ris0[0]:ris0[1]:ris0[2]]
    coeffs = _loadCoeffs(N, ris0)
    if coeffs is None:
        coeffs = psm.calculateCoefficients(dSmat2, dSmat2.asymCal)
        _saveCoeffs(coeffs, N, ris0)
        allCoeffsLoaded = False
    return coeffs

##### Root File #####

def _getRootFileHeaderStr(N, ris, asymCal):
    Nstr = "N="+str(N)
    EminStr = "Emin="+str(ris[0][0])+"("+str(ris[1][0])+")"
    EmaxStr = "Emax="+str(ris[0][1])+"("+str(ris[1][1])+")"
    stepStr = "step="+str(ris[0][2])
    return Nstr+", "+EminStr+", "+EmaxStr+", "+stepStr+"\n\n"

def _getRootName(path, N, ris0):
    return path+os.sep+_getInputDescStr(N, ris0)+".dat"

def _saveRoots(N, ris, roots, asymCal):
    if resultsRoot is not None:
        path = resultsRoot+"roots"
        if not os.path.isdir(path):
            os.makedirs(path)

        header = _getNumHeader(asymCal)
        rows = []
        for root in roots:
            rows.append(_getkERow(root, asymCal))

        fileName = _getRootName(path, N, ris[0])
        with _wopen(fileName) as f:
            _w(f, _getRootFileHeaderStr(N, ris, asymCal))
            _w(f, t.tabulate(rows,header))
            _w(f, "\ncomplete")

def _loadRoots(N, ris):
    if resultsRoot is not None:
        path = resultsRoot+"roots"
        if os.path.isdir(path):
            fileName = _getRootName(path, N, ris[0])
            if not os.path.isfile(fileName):
                return None
            try:
                with _ropen(fileName) as f:
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
                        # TODO log
                        return None
                    return roots
            except Exception as inst:
                # TODO log
                return None
    return None

def _getRoots(p, cFin, asymCal):
    global allRootsLoaded
    allRootsLoaded = True
    roots = _loadRoots(cFin.fitInfo[0], cFin.fitInfo[1])
    if roots is None:
        cVal = cFin.determinant(**p["cPolyMat_determinant"])
        roots = cVal.findRoots(**p["cPolyVal_findRoots"])
        _saveRoots(cFin.fitInfo[0], cFin.fitInfo[1], roots, asymCal)
        allRootsLoaded = False
    return roots

##### Pole Save #####

def _getPoleInfoPath(nList):
    return resultsRoot+"poles"+os.sep+str(nList).replace(' ','')+os.sep

def _getPoleFileHeaderStr(numPoles, asymCal):
    return str(numPoles)+" poles, "+asymCal.getUnits()+"\n\n"

def _getPoleRow(N, pole, status, asymCal):
    return [str(N), status] + _getkERow(pole, asymCal)

def _savePoleData(nList, poleData, asymCal):
    if resultsRoot is not None:
        path = _getPoleInfoPath(nList)
        if not os.path.isdir(path):
            os.makedirs(path)

        for i,dk in enumerate(poleData[2]):
            header = ["N","status"] + _getNumHeader(asymCal)
            rows = []
            for pole in poleData[0][i]:
                for j in sorted(pole.keys()):
                    row = _getPoleRow(nList[j], pole[j][0], pole[j][2], asymCal)
                    rows.append(row)
                rows.append(["","","",""])

            fileName = path+os.sep+"dk"+nu.sciStr(dk)+".dat"
            with _wopen(fileName) as f:
                _w(f, _getPoleFileHeaderStr(len(poleData[0][i]), asymCal))
                _w(f, t.tabulate(rows,header))

##### QI Save #####

def _getQIFileHeaderStr(numPoles, asymCal):
    return str(numPoles)+" poles, "+asymCal.getUnits()+"\n\n"

def _getQIRow(poleQI, asymCal):
    return _getkERow(poleQI[0], asymCal) + [str(poleQI[1]), str(poleQI[2])]

def _saveQIdata(nList, QIdat, asymCal):
    if resultsRoot is not None:
        header = _getNumHeader(asymCal) + ["^dk","ENk"]
        rows = []
        for poleQI in QIdat[0]:
            rows.append(_getQIRow(poleQI, asymCal))
        
        fileName = _getPoleInfoPath(nList)+os.sep+"QIs.dat"
        with _wopen(fileName) as f:
                _w(f, _getQIFileHeaderStr(len(QIdat[0]), asymCal))
                _w(f, t.tabulate(rows,header))

##### Public API #####

def getElasticSmat(dMat, N):
    dSmat = dMat.to_dSmat()
    ris = dSmat.getSliceIndices(0,len(dSmat)-1,N)
    coeffs = _getCoefficients(dSmat, N, ris[0])
    with _ropen(parmaFilePaths[0]) as f:
        config = yaml.load(f.read())
        return psm.getElasticSmatFun(coeffs, dSmat.asymCal,
                                     **config["getElasticSmat"])

def getElasticFins(dMat, Nlist):
    dSmat = dMat.to_dSmat()
    cFins = []
    for N in Nlist:
        ris = dSmat.getSliceIndices(0,len(dSmat)-1,N)
        coeffs = _getCoefficients(dSmat, N, ris[0])
        cFin = psm.getElasticFinFun(coeffs, dSmat.asymCal)
        cFin.fitInfo = (N,ris)
        cFins.append(cFin)
    return cFins

def calculateQIs(cFins):
    if len(cFins) > 0:
        with _ropen(parmaFilePaths[0]) as f:
            config = yaml.load(f.read())
            p = config["calculateQIs"]
            allRoots = []
            nList = []
            asymCal = None
            for cFin in cFins:
                if asymCal is not None:
                    assert asymCal == cFin.asymCal
                asymCal = cFin.asymCal
                roots = _getRoots(p, cFin, asymCal)
                allRoots.append(roots)
                nList.append(cFin.fitInfo[0])

            p = p["stelempy"]
            poleData = sp.calculateConvergenceGroupsRange(allRoots, 
                            p["startingDistThres"], p["endDistThres"], p["cfSteps"])
            _savePoleData(nList, poleData, asymCal)
            QIdat = sp.calculateQIsFromRange(poleData, p["amalgThres"])
            _saveQIdata(nList, QIdat, asymCal)
            return QIdat
        return None, None
