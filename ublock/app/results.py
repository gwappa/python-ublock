from traceback import print_exc
from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore

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
        if debug == True:
            print(f"token({token})")
        for s in self.status:
            if debug == True:
                print(f"testing status: {s}...")
            if token == s:
                self.resultStatusReceived.emit(s)
                return
        for val in self.values:
            if debug == True:
                print(f"testing value: {val}...")
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
            if debug == True:
                print(f"testing array: {arr}...")
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
        tokens = line[1:].split(protocol.DELIMITER)
        for token in tokens:
            self.__parseSingleResult(token)
        self.endParsing.emit()

class ResultStatsUI(QtWidgets.QGroupBox):
    """a display widget for summarizing the result status"""

    @classmethod
    def build(cls, model, results=None):
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
        return ui

    def __init__(self, summarized=(), rewarded=(), parent=None):
        """summarized: the status messages that are to be counted,
        rewarded: the status messages that are to be counted as 'rewarded'."""
        QtWidgets.QGroupBox.__init__(self, "Result statistics", parent=parent)
        self.summarized     = list(summarized)
        self.rewarded       = list(rewarded)
        self.rewardLabel    = '(reward)'
        self.fields         = OrderedDict()
        self.clearButton    = QtWidgets.QPushButton("Clear")
        self.clearButton.clicked.connect(self.clearCounts)

        self.layout     = QtWidgets.QGridLayout()
        status = self.rewardLabel
        self.layout.addWidget(QtWidgets.QLabel(status), 0, 0)
        self.fields[status] = QtWidgets.QLabel("0")
        self.layout.addWidget(self.fields[status], 1, 0)
        for i, status in enumerate(self.summarized):
            self.layout.addWidget(QtWidgets.QLabel(status), 0, i+1)
            self.fields[status] = QtWidgets.QLabel("0")
            self.layout.addWidget(self.fields[status], 1, i+1)
        self.layout.addWidget(self.clearButton, 1, len(self.summarized)+1)
        self.setLayout(self.layout)

    def setResultParser(self, parser):
        parser.resultStatusReceived.connect(self.addStatus)

    def clearCounts(self):
        for field in self.fields.values():
            field.setText("0")

    def __incrementField(self, field):
        prev = int(field.text())
        field.setText(str(prev+1))

    def addStatus(self, status):
        if status in self.summarized:
            self.__incrementField(self.fields[status])
        if status in self.rewarded:
            self.__incrementField(self.fields[self.rewardLabel])
