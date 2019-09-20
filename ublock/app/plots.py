from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore

class SessionView(pg.PlotWidget):
    """an aligned multi-trial view, that is designed to show
    a complete set of trials during one session."""

    resultStatusReceived    = QtCore.pyqtSignal(int,str)
    resultArrayReceived     = QtCore.pyqtSignal(int,str,list)
    refreshing              = QtCore.pyqtSignal(object)

    plotted     = False
    index       = 0
    plotters    = None

    @classmethod
    def build(cls, model, results=None, controls=None):
        ui = cls()
        
        # items  = model.views['session'].get('items', ())
        # xwidth = model.views['session'].get('xwidth', None)
        # view   = SessionView(xwidth=xwidth)
        # for item in items:
        #     if isinstance(item, StatusPlot):
        #         plotter = StatusPlotItem(item.colormappings,
        #                                  markersize=item.markersize,
        #                                  align=item.align)
        #         view.addPlotter(plotter)
        #     elif isinstance(item, ArrayPlot):
        #         plotter = ArrayPlotItem(item.colormappings,
        #                                 markersize=item.markersize)
        #         view.addPlotter(plotter)
        #     else:
        #         print("***unknown plotter type: {}".format(type(item)))
        # view.setResultParser(widget.result)
        # widget.views['session'] = view

        if controls is not None:
            controls.clearButton.setEnabled(True)
            controls.clearButton.clicked.connect(ui.clearPlots)
        pass

    def __init__(self, parent=None, xwidth=None, **kwargs):
        super().__init__(parent=parent, background='w', **kwargs)
        self.enableAutoRange(pg.ViewBox.YAxis)
        self.getPlotItem().invertY(True)
        if xwidth is not None:
            self.xwidth = xwidth
        self.plotters = []

    def __setattr__(self, name, value):
        if name == 'xwidth':
            self.setXRange(-value, value)
        else:
            super().__setattr__(name, value)

    def setResultParser(self, parser):
        parser.beginParsing.connect(self.initPlotting)
        parser.resultStatusReceived.connect(self.plotResultStatus)
        parser.resultArrayReceived.connect(self.plotResultArray)
        parser.endParsing.connect(self.finalizePlotting)

    def addPlotter(self, item):
        self.plotters.append(item)
        item.setView(self)

    def clearPlots(self):
        if debug == True:
            print("SessionView: clearPlots")
        # to force-repaint the plots,
        # we first `clear` the plot items
        # and then urge the items to add themselves again
        # using the `refreshing` signal
        self.getPlotItem().clear()
        self.index = 0
        self.refreshing.emit(self)

    def initPlotting(self):
        self.plotted = False

    def finalizePlotting(self):
        if self.plotted == True:
            self.index += 1

    def plotResultStatus(self, status):
        self.resultStatusReceived.emit(self.index, status)

    def plotResultArray(self, name, values):
        if self.plotted == True:
            self.resultArrayReceived.emit(self.index, name, values)

    def scheduleFurtherPlotting(self):
        self.plotted = True

class StatusPlotItem(pg.ScatterPlotItem):
    """the class used for plotting result status"""
    acceptStatus = QtCore.pyqtSignal()

    def __init__(self, colormappings, markersize=5, align='origin', parent=None):
        """colormappings: (status, color) dictionary
        align: currently only allows 'origin'
        """
        pg.ScatterPlotItem.__init__(self, parent=parent)
        self.penmapping     = {}
        self.brushmapping   = {}
        self.setSize(markersize)
        for status, value in colormappings.items():
            self.penmapping[status]     = pg.mkPen(color=value)
            self.brushmapping[status]   = pg.mkBrush(color=value)

    def setView(self, view):
        """currently only SessionView is supported"""
        view.addItem(self)
        view.resultStatusReceived.connect(self.addResultStatus)
        view.refreshing.connect(self.clearWithView)
        self.acceptStatus.connect(view.scheduleFurtherPlotting)

    def clearWithView(self, view):
        if debug == True:
            print(f"StatusPlotItem: clear")
        self.clear()
        view.addItem(self)

    def addResultStatus(self, index, status):
        if debug == True:
            print(f"addResultStatus({index}, {status})")
        if status in self.penmapping.keys():
            self.addPoints(x=(0,), y=(index,),
                           pen=self.penmapping[status],
                           brush=self.brushmapping[status])
            self.acceptStatus.emit()

class ArrayPlotItem(QtCore.QObject):
    """the class used for plotting result array items"""

    def __init__(self, colormappings, markersize=5, parent=None):
        """colormappings: (name, color) dictionary"""
        QtCore.QObject.__init__(self, parent=parent)
        self.plotters       = {}
        for name, value in colormappings.items():
            plotter = pg.ScatterPlotItem()
            plotter.setPen(pg.mkPen(color=value))
            plotter.setBrush(pg.mkBrush(color=value))
            plotter.setSize(markersize)
            self.plotters[name] = plotter

    def setView(self, view):
        """currently only SessionView is supported"""
        for plotter in self.plotters.values():
            view.addItem(plotter)
        view.resultArrayReceived.connect(self.addResultArray)
        view.refreshing.connect(self.clearWithView)

    def clearWithView(self, view):
        if debug == True:
            print(f"ArrayPlotItem: clear")
        for plotter in self.plotters.values():
            plotter.clear()
            view.addItem(plotter)

    def addResultArray(self, index, name, values):
        if debug == True:
            print(f"addResultArray({index}, {name})")
        if name in self.plotters.keys():
            self.plotters[name].addPoints(x=values, y=(index,)*len(values))
