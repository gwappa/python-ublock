from traceback import print_exc
from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore
from ..core import protocol as _proto
from . import _debug

class ResultParser(QtCore.QObject):
    """helps parsing the result messages.
    you can initialize with:

    + status -- str-only token
    + value  -- (str, int) token
    + array  -- (str, [int]) token
    """
    beginParsing         = QtCore.pyqtSignal()
    endParsing           = QtCore.pyqtSignal()
    resultStatusReceived = QtCore.pyqtSignal(str)
    resultValueReceived  = QtCore.pyqtSignal(str, int)
    resultArrayReceived  = QtCore.pyqtSignal(str, list)
    unknownResultReceived= QtCore.pyqtSignal(str)

    @classmethod
    def build(cls, model, serial=None, output=None):
        results = model.results
        if results is not None:
            ui = cls(status=results.status,
                     values=results.values,
                     arrays=results.arrays)
            if serial is not None:
                ui.setSerialIO(serial)
            return ui
        else:
            return None

    def __init__(self, parent=None, status=(), values=(), arrays=()):
        QtCore.QObject.__init__(self, parent=parent)
        self.status = list(status)
        self.values = list(values)
        self.arrays = list(arrays)

    def setSerialIO(self, serial):
        """serial: the SerialIO instance."""
        if serial is not None:
            serial.resultMessageReceived.connect(self.parseResult)

    def __parseSingleResult(self, token):
        token = token.strip()
        _debug(f"...parseSingleResult({token})")
        for s in self.status:
            _debug(f"...==? status({s})")
            if token == s:
                self.resultStatusReceived.emit(s)
                return
        for val in self.values:
            _debug(f"...==? value({val})")
            try:
                if token.startswith(val):
                    arg = int(token[len(val):])
                    self.resultValueReceived.emit(val, arg)
                    return
            except ValueError:
                print_exc()
                print("***error while parsing value '{}': {}".format(val, token))
                return
        for arr in self.arrays:
            _debug(f"...==? array({arr})")
            try:
                if token.startswith(arr):
                    arg = token[len(arr):]
                    if (arg[0] != '[') or (arg[-1] != ']'):
                        continue
                    args = arg[1:-1].split(',')
                    arglist = []
                    for elem in args:
                        if len(elem.strip()) == 0:
                            continue
                        arglist.append(int(elem))
                    self.resultArrayReceived.emit(arr, arglist)
                    return
            except ValueError:
                print_exc()
                print("***error while parsing array '{}': {}".format(arr, arg))
                return
        # no match
        self.unknownResultReceived.emit(token)

    def parseResult(self, line):
        self.beginParsing.emit()
        tokens = line.split(_proto.DELIMITER)
        for token in tokens:
            self.__parseSingleResult(token)
        self.endParsing.emit()

class ResultStatsUI(QtWidgets.QGroupBox):
    """a display widget for summarizing the result status"""
    sweepStarted = QtCore.pyqtSignal(int)
    sweepEnded   = QtCore.pyqtSignal()
    sweepAborted = QtCore.pyqtSignal()

    @classmethod
    def build(cls, model, serial=None, results=None):
        mres = model.results
        if mres is None:
            return None

        counted  = mres.counted
        rewarded = mres.rewarded
        if len(counted) + len(rewarded) == 0:
            return None

        ui = cls(summarized=counted, rewarded=rewarded)
        if results is not None:
            ui.setResultParser(results)
        if serial is not None:
            ui.setSerialIO(serial)
        return ui

    def __init__(self, summarized=(), rewarded=(), parent=None):
        """summarized: the status messages that are to be counted,
        rewarded: the status messages that are to be counted as 'rewarded'."""
        QtWidgets.QGroupBox.__init__(self, "Result statistics", parent=parent)
        self.summarized     = list(summarized)
        self.rewarded       = list(rewarded)
        self.sweepLabel     = '(sweep)'
        self.sumLabel       = '(result)'
        self.rewardLabel    = '(reward)'
        self.fields         = OrderedDict()
        self.clearButton    = QtWidgets.QPushButton("Clear")
        self.clearButton.clicked.connect(self.clearCounts)

        self.layout     = QtWidgets.QGridLayout()
        offset = 0
        for status in (self.sweepLabel, self.sumLabel, self.rewardLabel):
            self.layout.addWidget(QtWidgets.QLabel(status), 0, offset)
            self.fields[status] = QtWidgets.QLabel("0")
            self.layout.addWidget(self.fields[status], 1, offset)
            offset += 1
        for status in self.summarized:
            self.layout.addWidget(QtWidgets.QLabel(status), 0, offset)
            self.fields[status] = QtWidgets.QLabel("0")
            self.layout.addWidget(self.fields[status], 1, offset)
            offset += 1
        self.layout.addWidget(self.clearButton, 1, offset)
        self.setLayout(self.layout)

    def setResultParser(self, parser):
        parser.resultStatusReceived.connect(self.addStatus)

    def setSerialIO(self, serial):
        serial.requestStatusChanged.connect(self.addSweep)
        serial.requestAbandoned.connect(self.notifyAbort)

    def clearCounts(self):
        for field in self.fields.values():
            field.setText("0")

    def __incrementField(self, field):
        prev = int(field.text())
        field.setText(str(prev+1))

    def addSweep(self, inc):
        if inc == True:
            field = self.fields[self.sweepLabel]
            self.__incrementField(field)
            self.sweepStarted.emit(int(field.text()))

    def addStatus(self, status):
        self.sweepEnded.emit()
        self.__incrementField(self.fields[self.sumLabel])
        if status in self.summarized:
            self.__incrementField(self.fields[status])
        if status in self.rewarded:
            self.__incrementField(self.fields[self.rewardLabel])

    def notifyAbort(self):
        self.sweepAborted.emit()
