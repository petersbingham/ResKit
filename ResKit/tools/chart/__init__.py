import yaml
import os

import toolhelper as th

toolDir = os.path.dirname(os.path.realpath(__file__))
toolName = "chart"

class chart(th.tool):
    def __init__(self, data, archiveRoot, paramFilePath, silent):
        th.tool.__init__(self, data, archiveRoot, paramFilePath, toolDir,
                         silent)

    def _writeCall(self, start, end, numPoints, units, m, n, logx, logy, imag,
                   show, funName):
        self.log.writeCall(funName+"("+str(start)+","+str(end)+","\
                           +str(numPoints)+","+str(units)+","+str(m)+","\
                           +str(n)+","+str(logx)+","+str(logy)+","+str(imag)\
                           +","+str(show)+")")

    def _setChartParameters(self, dmat):
        with open(self.paramFilePath, 'r') as f:
            config = yaml.load(f.read())
            self.log.writeParameters(config)
            dmat.setChartParameters(colourCycle=config["colourCycle"])
            dmat.setChartParameters(legPrefix=config["legPrefix"])
            dmat.setChartParameters(useMarker=config["useMarker"])
            dmat.setChartParameters(xsize=config["xsize"])
            dmat.setChartParameters(ysize=config["ysize"])

    def _getSaveString(self, start, end, numPoints, logx, logy, units):
        ret = " " + str(start) + "_" + str(end) + "_" + str(numPoints) +\
              "_" + units
        if logx:
            ret += "_logx"
        if logy:
            ret += "_logy"
        return ret + ".png"

    def _getdmat(self, start, end, numPoints, units):
        if self.data.isDiscrete():
            if end is None:
                end = len(self.data)-1
            if numPoints is None:
                numPoints = end - start + 1
            dmat = self.data.createReducedLength(start, end, numPoints)
        else:
            if end is None:
                end = 10.
            if numPoints is None:
                numPoints = 100
            dmat = self.data.discretise(start, end, numPoints)
    
        if units is not None:
            dmat = dmat.convertUnits(units)
        else:
            units = dmat.units
        return dmat, start, end, numPoints

    def _plot(self, dmat, start, end, numPoints, m, n, logx, logy, imag, show):
        if m is not None and n is not None:
            dmat = dmat.createReducedDim(m).createReducedDim(n)
        elif m is not None:
            dmat = dmat.createReducedDim(m)
        elif n is not None:
            dmat = dmat.createReducedDim(m, True)
        self._setChartParameters(dmat)
        savePath = None
        if self.archiveRoot is not None:
            savePath = self.archiveRoot+dmat.chartTitle
            savePath += self._getSaveString(start, end, numPoints, logx, logy,
                                            dmat.units)
            self.log.writeMsg("Chart saved to: "+savePath)
        dmat.plot(logx, logy, imag, show, savePath)

    ##### Public API #####

    def plotSmatrix(self, start=0, end=None, numPoints=None, units=None, m=None,
                    n=None, logx=False, logy=False, imag=False, show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotSmatrix")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        dmat = dmat.to_dSmat()
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotSmatrix")

    def plotKmatrix(self, start=0, end=None, numPoints=None, units=None, m=None,
                    n=None, logx=False, logy=False, imag=False, show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotKmatrix")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        dmat = dmat.to_dKmat()
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotKmatrix")

    def plotTmatrix(self, start=0, end=None, numPoints=None, units=None, m=None,
                    n=None, logx=False, logy=False, imag=False, show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotTmatrix")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        dmat = dmat.to_dTmat()
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotTmatrix")

    def plotXS(self, start=0, end=None, numPoints=None, units=None, m=None,
               n=None, logx=False, logy=False, imag=False, show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotXS")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        dmat = dmat.to_dXSmat()
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotXS")

    def plotEPhase(self, start=0, end=None, numPoints=None, units=None, m=None,
                   n=None, logx=False, logy=False, imag=False, show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotEPhase")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        dmat = dmat.to_dEPhaseMat()
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotEPhase")

    def plotUniOpMat(self, start=0, end=None, numPoints=None, units=None, 
                     m=None, n=None, logx=False, logy=False, imag=False,
                     show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotUniOpMat")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        dmat = dmat.to_dUniOpMat()
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotUniOpMat")

    def plotRaw(self, start=0, end=None, numPoints=None, units=None, m=None,
                n=None, logx=False, logy=False, imag=False, show=True):
        self._writeCall(start, end, numPoints, units, m, n, logx, logy, imag,
                        show, "plotRaw")
        dmat,start,end,numPoints = self._getdmat(start, end, numPoints, units)
        self._plot(dmat, start, end, numPoints, m, n, logx, logy, imag, show)
        self.log.writeCallEnd("plotRaw")
