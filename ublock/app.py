from warnings import warn
try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
except ImportError:
    raise RuntimeError("ublock.app submodule is disabled; install the 'pyqtgraph' module to use it.")

import os
from datetime import datetime
from collections import OrderedDict
from traceback import print_exc
from serial.tools import list_ports

from .core import client, protocol, eventhandler, loop, loophandler
from .model import StatusPlot, ArrayPlot

mainapp = QtGui.QApplication([])

# used only for debugging via the console
# to be removed some time in the future
debug = False

class SerialIO(QtWidgets.QWidget, eventhandler):
    """GUI widget for managing a serial connection.

    This class implements `eventhandler`, and converts
    the handler methods to Qt signals.

    You can also change the `handler` to another `eventhandler` object,
    using the keyword argument in the initializer.

    `serialclient` in the initializer command can be
    any callable that takes the "handler" option as the
    keyword argument e.g. `client.Uno`.
    Any extra keyword arguments passed as `**kwargs` will be
    used when calling `serialclient()`.

    The SerialIO class is designed so that the user has the
    control over selecting/opening/closing the serial port.
    The classes that communicates over the serial port
    are supposed to `connect` their slots with SerialIO's
    `xxxReceived` signal(s), and by calling SerialIO's
    `request(line)` method (which is inherited from `baseclient`).
    """

    selectionChanged    = QtCore.pyqtSignal(str)
    serialClosed        = QtCore.pyqtSignal()
    serialStatusChanged = QtCore.pyqtSignal(bool)

    messageReceived         = QtCore.pyqtSignal(str)
    debugMessageReceived    = QtCore.pyqtSignal(str)
    infoMessageReceived     = QtCore.pyqtSignal(str)
    configMessageReceived   = QtCore.pyqtSignal(str)
    configElementReceived   = QtCore.pyqtSignal(str)
    resultMessageReceived   = QtCore.pyqtSignal(str)
    errorMessageReceived    = QtCore.pyqtSignal(str)
    outputMessageReceived   = QtCore.pyqtSignal(str)
    rawMessageReceived      = QtCore.pyqtSignal(str)

    def __init__(self, serialclient=client.Leonardo, handler=None,
                 label="Port: ", acqByResp=True, parent=None, **kwargs):
        super(QtWidgets.QWidget, self).__init__(parent=parent)
        super(eventhandler, self).__init__()

        mainapp.aboutToQuit.connect(self.closePort)
        self.portEnumerator = QtWidgets.QComboBox()
        self.enumeratePorts()
        self.portEnumerator.currentIndexChanged.connect(self.updateSelection)
        self.label = QtWidgets.QLabel(label)
        self.connector = ConnectorButton(self)

        self.serialclient   = serialclient  # the "function" that is used to open serial port
        self.clientkw       = kwargs   # the arguments used to call "handler"
        self.clientkw['handler'] = self if handler is None else handler

        self.acqByResp  = acqByResp
        self.io     = None
        self.reader = None
        self.active = False     # whether or not this IO is "connected"

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.label)
        layout.addWidget(self.portEnumerator)
        layout.addWidget(self.connector)

    def __setattr__(self, name, value):
        if name == 'active':
            super().__setattr__("_active", value)
            self.portEnumerator.setEnabled(not value)
            self.serialStatusChanged.emit(value)
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        if name == 'active':
            return super().__getattr__("_active")
        else:
            return super().__getattr__(name)

    def openPort(self, addr):
        self.io     = self.serialclient(addr, **self.clientkw)
        self.active = True

    def closePort(self):
        if self.io is not None:
            self.io.close()
            self.io = None
            self.serialClosed.emit()
            self.active = False

    def enumeratePorts(self):
        """(re-)enumerate serial ports"""
        ports          = list_ports.comports()
        self.portEnumerator.clear()
        self.ports     = []
        for port in ports:
            if 'Bluetooth' in str(port.device):
                continue
            self.ports.append(port)
            self.portEnumerator.addItem("{0.device} ({0.description})".format(port))
        self.portEnumerator.insertSeparator(len(self.ports))
        self.portEnumerator.addItem("Re-enumerate")
        if len(self.ports) > 0:
            self.selectedPort = self.ports[0]

    @QtCore.pyqtSlot(int)
    def updateSelection(self, idx):
        if debug == True:
            print(f"selected: {idx}")
        if idx > len(self.ports):
            # re-enumerate command
            self.enumeratePorts()
        elif idx < 0:
            # try doing nothing
            pass
        else:
            self.selectedPort = self.ports[idx]
            self.selectionChanged.emit(self.selectedPort.device)

    def toggleConnection(self, value):
        if value == True:
            self.openPort(self.selectedPort.device)
        else:
            self.closePort()

    def request(self, line):
        """sends a line of command (not having the newline character(s))
        through the serial port."""
        if self.io is not None:
            self.io.request(line)

    def connected(self, client):
        """re-implementing eventhandler's `connected`"""
        # self.serialStatusChanged.emit(True)
        # above signal must have been already emitted
        pass

    def received(self, line):
        """re-implementing eventhandler's `received`"""
        self.messageReceived.emit(line)

    def debug(self, line):
        """re-implementing eventhandler's `debug`"""
        self.debugMessageReceived.emit(line)

    def info(self, line):
        """re-implementing eventhandler's `info`"""
        self.infoMessageReceived.emit(line)

    def config(self, line):
        """re-implementing eventhandler's `config`"""
        self.configMessageReceived.emit(line)
        elems = [v.strip() for v in line[1:].split(";") if len(v.strip()) > 0]
        for elem in elems:
            self.configElementReceived.emit(elem)

    def result(self, line):
        """re-implementing eventhandler's `result`"""
        self.resultMessageReceived.emit(line)

    def error(self, line):
        """re-implementing eventhandler's `error`"""
        self.errorMessageReceived.emit(line)

    def output(self, line):
        """re-implementing eventhandler's `output`"""
        self.outputMessageReceived.emit(line)

    def message(self, line):
        """re-implementing eventhandler's `message`"""
        self.rawMessageReceived.emit(line)

class ConnectorButton(QtWidgets.QPushButton):
    """the button that commands the SerialIO to open/close the connection.
    its `delegate` must have the `toggleConnection` method and the
    `serialStatusChanged` signal."""

    statusChanged = QtCore.pyqtSignal(bool)

    def __init__(self, delegate, parent=None):
        super().__init__(parent=parent)
        self.setText("Connect")
        self.clicked.connect(self.dispatchCommand)
        self.statusChanged.connect(delegate.toggleConnection)
        delegate.serialStatusChanged.connect(self.toggleText)

    def dispatchCommand(self):
        if self.text() == "Connect":
            self.statusChanged.emit(True)
        else:
            self.statusChanged.emit(False)

    def toggleText(self, value):
        self.setText("Connect" if value == False else "Disconnect")

def HorizontalSeparator():
    line = QtWidgets.QFrame()
    line.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
    return line

class LineConfigUI(QtCore.QObject):
    configValueChanged = QtCore.pyqtSignal(str)

    def __init__(self, label, command, parent=None):
        super().__init__(parent=parent)
        self.editor  = QtWidgets.QLineEdit()
        self.label   = QtWidgets.QLabel(label)
        self.command = command
        self.editor.editingFinished.connect(self.dispatchRequest)
        self.setEnabled(False)

    def setEnabled(self, value):
        self.editor.setEnabled(value)
        self.label.setEnabled(value)

    def setSerialIO(self, serial, output=True):
        """connects this configUI to a SerialIO.

        output: whether or not to connect update events to SerialIO.
        """
        if output == True:
            self.configValueChanged.connect(serial.request)
        serial.configElementReceived.connect(self.updateConfigValue)
        serial.serialStatusChanged.connect(self.setEnabled)

    def dispatchRequest(self):
        self.configValueChanged.emit(self.command + self.editor.text())

    def updateConfigValue(self, msg):
        if msg.startswith(self.command):
            self.editor.setText(msg[len(self.command):])

class ModeConfigUI(QtWidgets.QComboBox):
    # emitted when the user changed the selection
    configValueChanged = QtCore.pyqtSignal(str)

    # emitted when SerialIO returns a mode selection
    currentModeChanged = QtCore.pyqtSignal(str)

    def __init__(self, options, parent=None):
        """options -- {modestr: modecmd} dict"""
        super().__init__(parent=parent)
        self.loadOptions(options)
        self.setEnabled(False)

    def setSerialIO(self, serial, output=True):
        """connects this configUI to a SerialIO.

        output: whether or not to connect update events to SerialIO.
        """
        if output == True:
            self.configValueChanged.connect(serial.request)
        serial.configElementReceived.connect(self.updateConfigValue)
        serial.serialStatusChanged.connect(self.setEnabled)
        serial.errorMessageReceived.connect(self.updateWithError)

    def loadOptions(self, options):
        self._options = options
        self._abbreviations = ''.join(opt.command for opt in options.values())
        for opt in options.keys():
            self.addItem(opt)
        self.setCurrentIndex(0)
        self.currentIndexChanged.connect(self.updateWithSelection)
        # wait for the config to be loaded first
        # through from the serial port
        self.valueChanging = True

    @QtCore.pyqtSlot(int)
    def updateWithSelection(self, idx):
        if self.valueChanging == False:
            self.valueChanging = True
            self.configValueChanged.emit(self._abbreviations[idx])
        else:
            pass

    def updateConfigValue(self, msg):
        if all(c in msg for c in self._abbreviations):
            idx = msg.index(']') - 2
            # print("mode config: {} (index={})".format(msg, idx))
            self.setCurrentIndex(idx)
            self.currentModeChanged.emit(self.currentText())
            self.prevIndex = idx
            self.valueChanging = False

    def updateWithError(self, msg):
        if self.valueChanging == True:
            self.setCurrentIndex(self.prevIndex)
            self.valueChanging = False

class NoteUI(QtWidgets.QGroupBox):
    runningNoteAdded = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Running note", parent=parent)
        self.histo = QtWidgets.QLabel("")
        self.editor = QtWidgets.QLineEdit()
        self.button = QtWidgets.QPushButton("Apply")

        self.editor.returnPressed.connect(self.applyNote)
        self.button.clicked.connect(self.applyNote)
        self.runningNoteAdded.connect(self.updateHistory)

        rows = QtWidgets.QVBoxLayout()
        self.setLayout(rows)
        rows.addWidget(self.histo)
        form = QtWidgets.QHBoxLayout()
        form.addWidget(self.editor)
        form.addWidget(self.button)
        rows.addLayout(form)

    def updateHistory(self, line):
        self.histo.setText(line[len(protocol.DEBUG):])

    def applyNote(self):
        content = self.editor.text().strip()
        if len(content) > 0:
            self.runningNoteAdded.emit(protocol.DEBUG + content)
            self.editor.setText("")

class ActionUI(QtWidgets.QPushButton):
    """the GUI class for managing an action (that does not accept any repeats)"""
    activated = QtCore.pyqtSignal(str)

    def __init__(self, label, command, returns='result', criteria=None, parent=None):
        QtWidgets.QPushButton.__init__(self, label, parent=parent)
        self.command = command
        if not returns in ('result', 'config'):
            print("*unknown return type for {}: {}".format(label, returns))
            returns = None
        self.returns = returns
        if criteria is not None:
            if callable(criteria):
                self.evaluate = criteria
            else:
                print(f"***criteria '{criteria}' is not callable and hence disabled. try using ublock.testResult()", flush=True)

        self.label = label
        self.waiting = False
        self.clicked.connect(self.dispatchCommand)
        self.setEnabled(False)

    def setSerialIO(self, serial, output=True):
        """connects this ActionUI to a SerialIO.

        output: whether or not to connect update events to SerialIO.
        """
        if output == True:
            self.activated.connect(serial.request)
        if self.returns is not None:
            if self.returns == 'result':
                serial.resultMessageReceived.connect(self.checkResults)
            elif self.returns == 'config':
                serial.configMessageReceived.connect(self.checkResults)
        serial.serialStatusChanged.connect(self.setEnabled)

    def dispatchCommand(self):
        self.activated.emit(self.command)
        self.waiting = True
        self.setEnabled(False)

    def checkResults(self, msg):
        if self.evaluate(msg) == True:
            if self.waiting == True:
                self.waiting = False
                self.setEnabled(True)

    def evaluate(self, result):
        return True

class RepeatUI(QtWidgets.QWidget, loophandler):
    """the GUI class for managing repeat number"""
    dispatchingRequest  = QtCore.pyqtSignal(str)
    repeatStarting      = QtCore.pyqtSignal(str, int, int)
    repeatEnding        = QtCore.pyqtSignal(str, int, int)

    def __init__(self, label, command, header='Repeat',
                 returns='result', criteria=None, parent=None, interval=0):
        QtWidgets.QWidget.__init__(self, parent=parent)
        loophandler.__init__(self)
        self.loop       = loop(command, 1, io=self, interval=interval, handler=self)
        self.loopthread = None

        if not returns in ('result', 'config'):
            print("*unknown return type for {}: {}".format(label, returns))
            returns = None
        self.returns = returns
        if criteria is not None:
            if callable(criteria):
                self.evaluate = criteria
            else:
                print(f"***criteria '{criteria}' is not callable and hence disabled. try using ublock.testResult()", flush=True)

        self.header  = QtWidgets.QLabel(header)
        self.editor  = QtWidgets.QLineEdit()
        self.editor.setText(str(1))
        self.editor.editingFinished.connect(self.parseValue)
        self.button  = QtWidgets.QPushButton(label)
        self.button.clicked.connect(self.runRepeat)
        self.buttonLabel = self.button.text()
        self.status  = QtWidgets.QLabel()

        self.control = QtWidgets.QHBoxLayout()
        self.control.addWidget(self.header)
        self.control.addWidget(self.editor)
        self.control.addWidget(self.button)
        self.layout  = QtWidgets.QGridLayout()
        self.layout.addWidget(self.status,0,0)
        self.layout.addLayout(self.control,0,1)
        self.layout.setColumnStretch(0,2)
        self.layout.setColumnStretch(1,5)
        self.setLayout(self.layout)
        self.setEnabled(False)
        # TODO need a mechanism to allow action group

    def setSerialIO(self, serial, output=True):
        """connects this configUI to a SerialIO.

        output: whether or not to connect update events to SerialIO.
        """
        serial.serialStatusChanged.connect(self.setEnabled)
        if self.returns is not None:
            if self.returns == 'result':
                serial.resultMessageReceived.connect(self.updateWithMessage)
            elif self.returns == 'config':
                serial.configMessageReceived.connect(self.updateWithMessage)
        if output == True:
            self.dispatchingRequest.connect(serial.request)

    def setButtonLabel(self, text):
        self.button.setText(text)
        self.buttonLabel = text

    def setHeaderLabel(self, text):
        self.header.setText(text)

    def setEnabled(self, value):
        self.header.setEnabled(value)
        self.button.setEnabled(value)
        self.editor.setEnabled(value)
        self.status.setEnabled(value)
        if self.loopthread is None:
            self.status.setText("")

    def parseValue(self):
        try:
            self.loop.number = int(self.editor.text())
        except ValueError:
            # TODO
            print("***invalid input: "+self.editor.text())
            self.editor.setText(str(self.loop.number))

    def runRepeat(self):
        self.parseValue()
        if self.loopthread is None:
            # start loop
            self.loopthread = self.loop.start()
        else:
            self.loop.abort()
            self.button.setText("Aborting...")
            self.button.setEnabled(False)

    def updateWithMessage(self, line):
        if self.loopthread is not None:
            self.loop.updateWithMessage(line)

    def request(self, line):
        self.dispatchingRequest.emit(line)

    def evaluate(self, line):
        return True

    def starting(self, cmd, num, idx):
        self.button.setText("Abort")
        self.repeatStarting.emit(cmd, num, idx)
        self.status.setText(f"Running: {idx+1} of {num}...")

    def done(self, cmd, planned, actual):
        self.button.setText(self.buttonLabel)
        self.loopthread = None
        self.status.setText(f"Done: {actual} of {planned}.")
        self.repeatEnding.emit(cmd, planned, actual)
        self.button.setEnabled(True)

class RawCommandUI(QtWidgets.QWidget):
    """a widget class that provides functionality to send
    a line of command out to the device."""

    dispatchingRequest = QtCore.pyqtSignal(str)

    def __init__(self, label=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent=None)
        if label is None:
            label = "Send command"
        self.editor     = QtWidgets.QLineEdit()
        self.button     = QtWidgets.QPushButton(label)
        self.layout     = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.editor)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

        self.button.clicked.connect(self.dispatch)
        self.editor.returnPressed.connect(self.dispatch)

    def setSerialIO(self, serial, output=True):
        serial.serialStatusChanged.connect(self.setEnabled)
        if output == True:
            self.dispatchingRequest.connect(serial.request)

    def setEnabled(self, value):
        self.editor.setEnabled(value)
        self.button.setEnabled(value)

    def dispatch(self):
        line = self.editor.text().strip()
        if len(line) > 0:
            self.dispatchingRequest.emit(line)

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

class ResultStatsView(QtWidgets.QGroupBox):
    """a display widget for summarizing the result status"""

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

class SessionView(pg.PlotWidget):
    """an aligned multi-trial view, that is designed to show
    a complete set of trials during one session."""

    resultStatusReceived    = QtCore.pyqtSignal(int,str)
    resultArrayReceived     = QtCore.pyqtSignal(int,str,list)
    refreshing              = QtCore.pyqtSignal(object)

    plotted     = False
    index       = 0
    plotters    = None

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

class LoggerUI(QtWidgets.QGroupBox):
    """a class that handles generation of (and writing to) the log file."""
    statusChanged = QtCore.pyqtSignal(bool)
    loggers = {}

    @classmethod
    def get(cls, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log"):
        """used for sharing the log file."""
        if name not in cls.loggers.keys():
            cls.loggers[name] = cls(name, label=label, fmt=fmt)
        return cls.loggers[name]

    @classmethod
    def echo(cls, line):
        """used in the 'echo' feature, where all the messages
        from the device show up on the standard output."""
        print(line, flush=True)

    def __init__(self, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log", parent=None):
        if label is None:
            label = "'{}' log file".format(name)
        QtWidgets.QGroupBox.__init__(self, label, parent=parent)
        self.name       = name
        self.baseformat = fmt.format(self.name)
        self.logfile    = None
        self.fileinfo   = None
        self.label      = QtWidgets.QLabel("Format: ")
        self.field      = QtWidgets.QLineEdit(self.baseformat)
        self.button     = QtWidgets.QPushButton("New")
        self.hbox       = QtWidgets.QHBoxLayout()
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.field)
        self.hbox.addWidget(self.button)
        self.setLayout(self.hbox)
        self.button.clicked.connect(self.renew)
        mainapp.aboutToQuit.connect(self.close)

    @staticmethod
    def printStatus(line):
        """a proxy to print the status into the standard output."""
        print(line)

    def attachSerialIO(self, serial):
        """connects this LoggerUI to a SerialIO."""
        serial.messageReceived.connect(self.log)

    def attachNoteUI(self, note):
        """connects this LoggerUI to a NoteUI."""
        self.statusChanged.connect(note.setEnabled)
        note.runningNoteAdded.connect(self.log)

    def close(self):
        """closes the log file that is currently open.
        does nothing if there is no open file."""
        if self.logfile is not None:
            self.logfile.close()
            LoggerUI.printStatus("{}closed: {}".format(protocol.OUTPUT, self.fileinfo))
            self.logfile = None
            self.fileinfo = None

    def renew(self):
        self.close()
        fmt = self.field.text().strip()
        if len(fmt) == 0:
            fmt = self.baseformat
        elif not fmt[-4:] in (".txt", ".log"):
            fmt += ".log"
        now     = datetime.now()
        newname = now.strftime(fmt)
        self.fileinfo = QtWidgets.QFileDialog.getSaveFileName(self,
                            "New log file...",
                            newname,
                            "Log file (*.txt, *.log)")
        if len(self.fileinfo[0]) == 0:
            self.statusChanged.emit(False)
        else:
            self.fileinfo = self.fileinfo[0]
            self.logfile = open(self.fileinfo, 'w')
            self.statusChanged.emit(True)

    def logStatusChange(self, value):
        if value == True:
            print("{}opened: {}".format(protocol.OUTPUT, self.fileinfo))
        else:
            print("{}no log file is attached".format(protocol.OUTPUT))

    def log(self, line):
        """writes a line to the log file.
        warns if there is no open file."""
        if self.logfile is not None:
            print(line, file=self.logfile, flush=True)
        else:
            print("{}no log file is open".format(protocol.ERROR), flush=True)

class TaskWidget(QtWidgets.QWidget):
    """a widget that is used to control the task.
    intended to be automatically generated from a model.Task instance."""

    name        = "task"
    status      = None
    serial      = None
    modes       = None
    configs     = None
    actions     = None
    loggers     = None
    result      = None
    views       = None
    features    = None

    clearPlot   = None
    quitApp     = None

    def __init__(self, name="task", parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.name = name
        self.status = QtWidgets.QLabel()
        self.quitPrompt = QtWidgets.QMessageBox(self)
        self.quitPrompt.setIcon(QtWidgets.QMessageBox.Warning)
        self.quitPrompt.setText("Are you sure you want to quit?")
        

    def updateStatus(self, line):
        """updates the status in response to the line."""
        # TODO: use better formatting as in WhiskingExplorationGUI
        limit = 50
        if len(line) > limit:
            line = line[:limit] + "..."
        self.status.setText(line)

    def promptQuit(self):
        """ask user whether or not to quit the app."""
        ret = QtWidgets.QMessageBox.warning(self,
                                            "About to quit",
                                            "Are you sure you want to quit?",
                                            QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                                            QtWidgets.QMessageBox.Yes)
        if ret == QtWidgets.QMessageBox.Yes:
            mainapp.quit()

    def __layout(self):
        """lays out its components in a new QVBoxLayout."""
        layout = QtWidgets.QVBoxLayout()
        isempty = True

        # add SerialIO
        if self.serial is not None:
            layout.addWidget(self.serial)
            isempty = False

        # add status bar
        if self.status is not None:
            layout.addWidget(self.status)
            isempty = False

        # add raw command UI (if any)
        if 'raw' in self.features.keys():
            layout.addWidget(self.features['raw'])
            isempty = False

        # add ModeConfigUI
        if self.modes is not None:
            if isempty == False:
                layout.addWidget(HorizontalSeparator())
            modeLayout = QtWidgets.QHBoxLayout()
            modeHeader = QtWidgets.QLabel("Mode: ")
            modeHeader.setEnabled(False)
            self.serial.serialStatusChanged.connect(modeHeader.setEnabled)
            modeLayout.addWidget(modeHeader)
            modeLayout.addWidget(self.modes)
            layout.addLayout(modeLayout)

        # add LineConfigUI's
        if len(self.configs) == 0:
            pass
        elif len(self.configs) == 1:
            if isempty == False:
                layout.addWidget(HorizontalSeparator())
            isempty = False
            configLayout = QtWidgets.QFormLayout()
            for group in self.configs.values():
                for config in group.values():
                    configLayout.addRow(config.label, config.editor)
            layout.addLayout(configLayout)
        else:
            if isempty == False:
                layout.addWidget(HorizontalSeparator())
            isempty = False
            configWidget = QtWidgets.QTabWidget()
            for groupname in self.configs.keys():
                page = QtWidgets.QWidget()
                pageLayout = QtWidgets.QFormLayout()
                for config in self.configs[groupname].values():
                    pageLayout.addRow(config.label, config.editor)
                page.setLayout(pageLayout)
                configWidget.addTab(page, groupname)
            layout.addWidget(configWidget)

        # add actions
        if len(self.actions) > 0:
            if isempty == False:
                layout.addWidget(HorizontalSeparator())
            isempty = False
            repeatables = [action for action in self.actions.values() if isinstance(action, RepeatUI)]
            singles     = [action for action in self.actions.values() if isinstance(action, ActionUI)]
            for repeatable in repeatables:
                layout.addWidget(repeatable)

            if len(singles) > 0:
                singlesLayout = QtWidgets.QHBoxLayout()
                singlesLayout.addStretch()
                for single in singles:
                    singlesLayout.addWidget(single)
                layout.addLayout(singlesLayout)

        # add 'stats' view
        if (self.result is not None) and ('stats' in self.views.keys()):
            isempty = False
            layout.addWidget(self.views['stats'])

        # add noteUI (if any)
        if 'note' in self.features.keys():
            isempty = False
            layout.addWidget(self.features['note'])

        # add loggers
        if len(self.loggers) == 0:
            pass
        elif len(self.loggers) == 1:
            isempty = False
            for logger in self.loggers.values():
                layout.addWidget(logger)
        else:
            isempty = False
            for name, logger in self.loggers.items():
                box = QtWidgets.QGroupBox(name)
                boxLayout = QtWidgets.QVBoxLayout()
                boxLayout.addWidget(logger)
                box.setLayout(boxLayout)
                layout.addWidget(box)

        surrounding = QtWidgets.QGridLayout()
        surrounding.addLayout(layout, 0, 0)
        ncol = 1
        
        # add sessionview (if any)
        if (self.result is not None) and ('session' in self.views.keys()):
            ncol = 2
            if self.clearPlot is not None:
                self.clearPlot.setEnabled(True)
                self.clearPlot.clicked.connect(self.views['session'].clearPlots)
            surrounding.addWidget(self.views['session'], 0, 1)
            surrounding.setColumnStretch(1, 2)

        if 'control' in self.features.keys():
            surrounding.addLayout(self.features['control'], 1, 0, 1, 2)
        self.setLayout(surrounding)

    @staticmethod
    def fromTask(model, serialclient='leonardo', baud=9600):
        """generates a (connected) UI from the given model.Task instance."""
        if isinstance(serialclient, str):
            clienttype = serialclient.lower()
            if clienttype == 'leonardo':
                clienttype = client.Leonardo
            elif clienttype == 'uno':
                clienttype = client.Uno
            else:
                raise ValueError("unknown client type: "+serialclient)
            serialclient = clienttype

        widget = TaskWidget(name=model.name)
        # add SerialIO UI
        widget.serial   = SerialIO(serialclient=serialclient, baud=baud,
                                   label="device for '{}': ".format(model.name))
        widget.serial.messageReceived.connect(widget.updateStatus)
        # add NoteUI
        widget.features = OrderedDict()
        if 'note' in model.features:
            widget.features['note'] = NoteUI()
            widget.features['note'].setEnabled(False)
        # set "echo" feature
        if 'echo' in model.features:
            widget.serial.messageReceived.connect(LoggerUI.echo)
        if 'raw'  in model.features:
            widget.features['raw']  = RawCommandUI()
            widget.features['raw'].setEnabled(False)
            widget.features['raw'].setSerialIO(widget.serial, output=True)

        # set "control" feature
        widget.clearPlot = QtWidgets.QPushButton("Clear plots")
        widget.clearPlot.setEnabled(False)
        widget.quitApp   = QtWidgets.QPushButton("Quit")
        widget.quitApp.clicked.connect(widget.promptQuit)
        if 'control' in model.features:
            controlbox     = QtWidgets.QHBoxLayout()
            controlbox.addStretch()
            controlbox.addWidget(widget.clearPlot)
            controlbox.addWidget(widget.quitApp)
            widget.features['control'] = controlbox

        # add ModeConfigUI
        if len(model.modes) > 0:
            widget.modes    = ModeConfigUI(model.modes)
            widget.modes.setSerialIO(widget.serial, output=True)

        # add LineConfigUI's
        widget.configs  = OrderedDict()
        for name, config in model.configs.items():
            if config.group not in widget.configs.keys():
                widget.configs[config.group] = OrderedDict()
            uiobj = LineConfigUI(config.label, config.command)
            uiobj.setSerialIO(widget.serial, output=True)
            widget.configs[config.group][name] = uiobj

        # add Actions
        widget.actions  = OrderedDict()
        for name, action in model.actions.items():
            uitype = RepeatUI if action.repeats == True else ActionUI
            uiobj = uitype(action.label, action.command, returns=action.returns,
                            criteria=action.criteria)
            uiobj.setSerialIO(widget.serial, output=True)
            widget.actions[name] = uiobj

        # add ResultParser
        if model.result is not None:
            widget.result   = ResultParser(**(model.result.as_dict()))
            widget.result.setSerialIO(widget.serial)
            widget.views    = OrderedDict()

            # add view(s)
            if 'stats' in model.views.keys():
                widget.views['stats'] = ResultStatsView(**model.views['stats'])
                widget.views['stats'].setResultParser(widget.result)
            if 'session' in model.views.keys():
                items  = model.views['session'].get('items', ())
                xwidth = model.views['session'].get('xwidth', None)
                view   = SessionView(xwidth=xwidth)
                for item in items:
                    if isinstance(item, StatusPlot):
                        plotter = StatusPlotItem(item.colormappings,
                                                 markersize=item.markersize,
                                                 align=item.align)
                        view.addPlotter(plotter)
                    elif isinstance(item, ArrayPlot):
                        plotter = ArrayPlotItem(item.colormappings,
                                                markersize=item.markersize)
                        view.addPlotter(plotter)
                    else:
                        print("***unknown plotter type: {}".format(type(item)))
                view.setResultParser(widget.result)
                widget.views['session'] = view

        else:
            widget.result = None

        # add loggerUI
        widget.loggers  = OrderedDict()
        for name, logger in model.loggers.items():
            uiobj = LoggerUI.get(logger.name, label=logger.label, fmt=logger.fmt)
            uiobj.attachSerialIO(widget.serial)
            if 'note' in model.features:
                uiobj.attachNoteUI(widget.features['note'])
            widget.loggers[name] = uiobj

        widget.__layout()
        return widget

fromTask = TaskWidget.fromTask
