from warnings import warn
try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
except ImportError:
    raise RuntimeError("ublock.app submodule is disabled; install the 'pyqtgraph' module to use it.")

import sys, os
from datetime import datetime
from collections import OrderedDict
from traceback import print_exc
from eventcalls.io import SerialIO as SerialTerm

# from .model import StatusPlot, ArrayPlot

from .actions  import ActionUI
from .configs  import ConfigUI
from .features import RawCommandUI, NoteUI, ControlUI
from .modes    import ModeUI
from .plots    import SessionView
from .results  import ResultParser, ResultStatsUI
from .serial   import SerialIO

__mainapp = None

# used only for debugging via the console
# to be removed some time in the future
debug = False

def __debug(msg, end='\n'):
    if debug == True:
        print(msg, end=end, file=sys.stderr, flush=True)

def getApp():
    global __mainapp
    if __mainapp is None:
        __mainapp = QtGui.QApplication([])
    return __mainapp

def setApp(app):
    global __mainapp
    if __mainapp is not None:
        raise RuntimeError("an application has been already initialized")
    __mainapp = app

def HorizontalSeparator():
    line = QtWidgets.QFrame()
    line.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
    return line

#class RepeatUI(QtWidgets.QWidget, loophandler):
#    """the GUI class for managing repeat number"""
#    dispatchingRequest  = QtCore.pyqtSignal(str)
#    repeatStarting      = QtCore.pyqtSignal(str, int, int)
#    repeatEnding        = QtCore.pyqtSignal(str, int, int)
#
#    def __init__(self, label, command, header='Repeat',
#                 returns='result', criteria=None, strict=None,
#                 parent=None, interval=0):
#        QtWidgets.QWidget.__init__(self, parent=parent)
#        loophandler.__init__(self)
#        self.loop       = loop(command, 1, io=self, interval=interval, handler=self)
#        self.loopthread = None
#
#        if not returns in ('result', 'config'):
#            print("*unknown return type for {}: {}".format(label, returns))
#            returns = None
#        self.returns = returns
#        self.strict = strict
#        if criteria is not None:
#            if callable(criteria):
#                self.evaluate = criteria
#            else:
#                print(f"***criteria '{criteria}' is not callable and hence disabled. try using ublock.testResult()", flush=True)
#
#        self.header  = QtWidgets.QLabel(header)
#        self.editor  = QtWidgets.QLineEdit()
#        self.editor.setText(str(1))
#        self.editor.editingFinished.connect(self.parseValue)
#        self.button  = QtWidgets.QPushButton(label)
#        self.button.clicked.connect(self.runRepeat)
#        self.buttonLabel = self.button.text()
#        self.status  = QtWidgets.QLabel()
#        if self.strict is not None:
#            self.strictcheck = QtWidgets.QCheckBox(f"Use strict mode for \"{label}\"")
#            self.strictcheck.setChecked(False)
#            self.strictmode  = False
#            self.strictcheck.toggled.connect(self.setStrictMode)
#        else:
#            self.strictmode = None
#
#        self.control = QtWidgets.QHBoxLayout()
#        self.control.addWidget(self.header)
#        self.control.addWidget(self.editor)
#        self.control.addWidget(self.button)
#        self.layout  = QtWidgets.QGridLayout()
#        self.layout.addWidget(self.status,0,0)
#        self.layout.addLayout(self.control,0,1)
#        if self.strictmode is not None:
#            self.layout.addWidget(self.strictcheck, 1,1,
#                                    alignment=QtCore.Qt.AlignRight)
#        self.layout.setColumnStretch(0,2)
#        self.layout.setColumnStretch(1,5)
#        self.setLayout(self.layout)
#        self.setEnabled(False)
#        # TODO need a mechanism to allow action group
#
#    def setStrictMode(self, val):
#        self.strictmode = val
#
#    def setSerialIO(self, serial, output=True):
#        """connects this configUI to a SerialIO.
#
#        output: whether or not to connect update events to SerialIO.
#        """
#        serial.serialStatusChanged.connect(self.setEnabled)
#        if self.returns is not None:
#            if self.returns == 'result':
#                serial.resultMessageReceived.connect(self.updateWithMessage)
#            elif self.returns == 'config':
#                serial.configMessageReceived.connect(self.updateWithMessage)
#        if output == True:
#            self.dispatchingRequest.connect(serial.request)
#
#    def setButtonLabel(self, text):
#        self.button.setText(text)
#        self.buttonLabel = text
#
#    def setHeaderLabel(self, text):
#        self.header.setText(text)
#
#    def setEnabled(self, value):
#        self.header.setEnabled(value)
#        self.button.setEnabled(value)
#        self.editor.setEnabled(value)
#        self.status.setEnabled(value)
#        if self.strict is not None:
#            self.strictcheck.setEnabled(value)
#        if self.loopthread is None:
#            self.status.setText("")
#
#    def parseValue(self):
#        try:
#            self.loop.number = int(self.editor.text())
#        except ValueError:
#            # TODO
#            print("***invalid input: "+self.editor.text())
#            self.editor.setText(str(self.loop.number))
#
#    def runRepeat(self):
#        self.parseValue()
#        if self.loopthread is None:
#            # start loop
#            self.loopthread = self.loop.start()
#        else:
#            self.loop.abort()
#            self.button.setText("Aborting...")
#            self.button.setEnabled(False)
#
#    def updateWithMessage(self, line):
#        if self.loopthread is not None:
#            self.loop.updateWithMessage(line)
#
#    def request(self, line):
#        self.dispatchingRequest.emit(line)
#
#    def evaluate(self, resultline):
#        if self.strictmode == True:
#            return any(resultline[1:].startswith(status) for status in self.strict)
#        else:
#            return True
#
#    def starting(self, cmd, num, idx):
#        self.button.setText("Abort")
#        self.repeatStarting.emit(cmd, num, idx)
#        self.status.setText(f"Running: {idx+1} of {num}...")
#
#    def done(self, cmd, planned, actual):
#        self.button.setText(self.buttonLabel)
#        self.loopthread = None
#        self.status.setText(f"Done: {actual} of {planned}.")
#        self.repeatEnding.emit(cmd, planned, actual)
#        self.button.setEnabled(True)

class LoggerUI(QtWidgets.QGroupBox):
    """a class that handles generation of (and writing to) the log file."""
    statusChanged = QtCore.pyqtSignal(bool)
    loggers = {}

    @classmethod
    def build(cls, model, serial=None, note=None):
        loggers = OrderedDict()
        for name, logger in model.loggers.items():
            uiobj = cls.get(logger.name, label=logger.label, fmt=logger.fmt)
            if serial is not None:
                uiobj.attachSerialIO(serial)
            if note is not None:
                uiobj.attachNoteUI(note)
            loggers[name] = uiobj
        return loggers

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

    def __init__(self, name="task", parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.name = name
        self._status = QtWidgets.QLabel()
        self.quitPrompt = QtWidgets.QMessageBox(self)
        self.quitPrompt.setIcon(QtWidgets.QMessageBox.Warning)
        self.quitPrompt.setText("Are you sure you want to quit?")

    def __getattr__(self, name):
        if name == 'results':
            return self._results
        elif name == 'stats':
            return self._statsUI
        elif name == 'session':
            return self._sessionView
        elif name == 'status':
            return self._status
        elif name == 'serial':
            return self._serialUI
        elif name == 'modes':
            return self._modeUI.selector
        elif name == 'configs':
            return self._configUI
        elif name == 'actions':
            return self._actionUI
        elif name == 'note':
            return self._noteUI
        elif name == 'raw':
            return self._rawCommandUI
        elif name == 'loggers':
            return self._loggers
        elif name == 'quitButton':
            return self._controls.quitButton
        elif name == 'clearButton':
            return self._controls.clearButton
        else:
            super().__getattr__(name)

    def updateStatus(self, line):
        """updates the status in response to the line."""
        # TODO: use better formatting as in WhiskingExplorationGUI
        limit = 50
        if len(line) > limit:
            line = line[:limit] + "..."
        self.status.setText(line)

    def quitApplication(self):
        __mainapp.quit()

    def __layout(self):
        """lays out its components in a new QVBoxLayout."""
        layout = QtWidgets.QVBoxLayout()
        self.__isempty = True

        def __add(obj, separate=False):
            if obj is None:
                return
            if (separate == True) and (not self.__isempty):
                layout.addWidget(HorizontalSeparator())
            layout.addWidget(obj)
            self.__isempty = False

        for uiobj, separate in ((self._serialUI, False),
                                (self.status, False),
                                (self._rawCommandUI, False),
                                (self._modeUI, True),
                                (self._configUI, True),
                                (self._actionUI, True),
                                (self._statsUI, False),
                                (self._noteUI, False)):
            __add(uiobj, separate=separate)

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

        # format "surroundings"
        surrounding = QtWidgets.QGridLayout()
        surrounding.addLayout(layout, 0, 0)
        ncol = 1

        # add sessionview (if any)
        if self._sessionView is not None:
            ncol = 2
            surrounding.addWidget(self._sessionView, 0, 1)
            surrounding.setColumnStretch(1, 2)

        if self._controls is not None:
            surrounding.addLayout(self._controls, 1, 0, 1, 2)
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
        widget._serialUI   = SerialIO(serialclient=serialclient, baud=baud,
                                   label="device for '{}': ".format(model.name))
        widget._serialUI.messageReceived.connect(widget.updateStatus)

        # configure 'echoed'
        if model.echoed == True:
            widget._serialUI.messageReceived.connect(LoggerUI.echo)
        # configure 'controls'
        widget._controls = ControlUI.build(model, widget=widget)

        # configure serial-based variables
        for cls in (ModeUI, ConfigUI, ActionUI, NoteUI, RawCommandUI):
            attrname = '_'+cls.__name__.lower()[0] + cls.__name__[1:]
            setattr(widget, attrname, cls.build(model, serial=widget._serialUI, output=True))

        # configure results
        widget._results     = ResultParser.build(model, serial=widget._serialUI, output=True)
        widget._statsUI     = ResultStatsUI.build(model, results=widget._results)
        widget._sessionView = SessionView.build(model, results=widget._results)

        # add loggerUI
        widget._loggers  = LoggerUI.build(model,
                                serial=widget._serialUI, note=widget._noteUI)

        widget.__layout()
        return widget

fromTask = TaskWidget.fromTask
