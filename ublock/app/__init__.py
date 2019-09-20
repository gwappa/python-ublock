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

from .model import StatusPlot, ArrayPlot

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
                return False
            if (separate == True) and (not self.__isempty):
                layout.addWidget(HorizontalSeparator())
            layout.addWidget(obj)
            self.__isempty = False
            return True

        # add SerialIO
        __add(self._serialUI)

        # add status bar
        __add(self.status)

        # add raw command UI (if any)
        __add(self._rawCommandUI)

        # add ModeConfigUI
        # if self.modes is not None:
        #     if isempty == False:
        #         layout.addWidget(HorizontalSeparator())
        #     modeLayout = QtWidgets.QHBoxLayout()
        #     modeHeader = QtWidgets.QLabel("Mode: ")
        #     modeHeader.setEnabled(False)
        #     self.serial.serialStatusChanged.connect(modeHeader.setEnabled)
        #     modeLayout.addWidget(modeHeader)
        #     modeLayout.addWidget(self.modes)
        #     layout.addLayout(modeLayout)
        __add(self._modeUI, separate=True)

        # add LineConfigUI's
        # if len(self.configs) == 0:
        #     pass
        # elif len(self.configs) == 1:
        #     if isempty == False:
        #         layout.addWidget(HorizontalSeparator())
        #     isempty = False
        #     configLayout = QtWidgets.QFormLayout()
        #     for group in self.configs.values():
        #         for config in group.values():
        #             configLayout.addRow(config.label, config.editor)
        #     layout.addLayout(configLayout)
        # else:
        #     if isempty == False:
        #         layout.addWidget(HorizontalSeparator())
        #     isempty = False
        #     configWidget = QtWidgets.QTabWidget()
        #     for groupname in self.configs.keys():
        #         page = QtWidgets.QWidget()
        #         pageLayout = QtWidgets.QFormLayout()
        #         for config in self.configs[groupname].values():
        #             pageLayout.addRow(config.label, config.editor)
        #         page.setLayout(pageLayout)
        #         configWidget.addTab(page, groupname)
        #     layout.addWidget(configWidget)
        __add(self._configUI, separate=True)

        # add actions
        # if len(self.actions) > 0:
        #     if isempty == False:
        #         layout.addWidget(HorizontalSeparator())
        #     isempty = False
        #     repeatables = [action for action in self.actions.values() if isinstance(action, RepeatUI)]
        #     singles     = [action for action in self.actions.values() if isinstance(action, ActionUI)]
        #     for repeatable in repeatables:
        #         layout.addWidget(repeatable)
        #
        #     if len(singles) > 0:
        #         singlesLayout = QtWidgets.QHBoxLayout()
        #         singlesLayout.addStretch()
        #         for single in singles:
        #             singlesLayout.addWidget(single)
        #         layout.addLayout(singlesLayout)
        __add(self._actionUI, separate=True)

        # add 'stats' view
        __add(self._statsUI)
        # if (self.result is not None) and ('stats' in self.views.keys()):
        #     isempty = False
        #     layout.addWidget(self.views['stats'])

        # add noteUI (if any)
        __add(self._noteUI)

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
        if model.echo == True:
            widget._serialUI.messageReceived.connect(LoggerUI.echo)

        # widget.features = OrderedDict()
        # if 'note' in model.features:
        #     widget.features['note'] = NoteUI()
        #     widget.features['note'].setEnabled(False)

        # add NoteUI
        # set "echo" feature
        # if 'echo' in model.features:
        #     widget.serial.messageReceived.connect(LoggerUI.echo)

        # if 'raw'  in model.features:
        #     widget.features['raw']  = RawCommandUI()
        #     widget.features['raw'].setEnabled(False)
        #     widget.features['raw'].setSerialIO(widget.serial, output=True)

        # set "control" feature
        # widget.clearPlot = QtWidgets.QPushButton("Clear plots")
        # widget.clearPlot.setEnabled(False)
        # widget.quitApp   = QtWidgets.QPushButton("Quit")
        # widget.quitApp.clicked.connect(widget.promptQuit)
        # if 'control' in model.features:
        #     controlbox     = QtWidgets.QHBoxLayout()
        #     controlbox.addStretch()
        #     controlbox.addWidget(widget.clearPlot)
        #     controlbox.addWidget(widget.quitApp)
        #     widget.features['control'] = controlbox
        widget._controls = ControlUI.build(model, widget=widget)

        # add ModeConfigUI
        # if len(model.modes) > 0:
        #     widget.modes    = ModeConfigUI(model.modes)
        #     widget.modes.setSerialIO(widget.serial, output=True)

        # add LineConfigUI's
        # widget.configs  = OrderedDict()
        # for name, config in model.configs.items():
        #     if config.group not in widget.configs.keys():
        #         widget.configs[config.group] = OrderedDict()
        #     uiobj = LineConfigUI(config.label, config.command)
        #     uiobj.setSerialIO(widget.serial, output=True)
        #     widget.configs[config.group][name] = uiobj

        # add Actions
        # widget.actions  = OrderedDict()
        # for name, action in model.actions.items():
        #     uitype = RepeatUI if action.repeats == True else ActionUI
        #     uiobj = uitype(action.label, action.command, returns=action.returns,
        #                     criteria=action.criteria, strict=action.strict)
        #     uiobj.setSerialIO(widget.serial, output=True)
        #     widget.actions[name] = uiobj

        for cls in (ModeUI, ConfigUI, ActionUI, NoteUI, RawCommandUI):
            attrname = '_'+cls.__name__.lower()[0] + cls.__name__[1:]
            setattr(widget, attrname, cls.build(model, serial=widget._serialUI, output=True))

        # add ResultParser
        # if model.result is not None:
        #     widget.result   = ResultParser(**(model.result.as_dict()))
        #     widget.result.setSerialIO(widget.serial)
        #     widget.views    = OrderedDict()
        #
        #     # add view(s)
        #     if 'stats' in model.views.keys():
        #         widget.views['stats'] = ResultStatsView(**model.views['stats'])
        #         widget.views['stats'].setResultParser(widget.result)
        #     if 'session' in model.views.keys():
        #         items  = model.views['session'].get('items', ())
        #         xwidth = model.views['session'].get('xwidth', None)
        #         view   = SessionView(xwidth=xwidth)
        #         for item in items:
        #             if isinstance(item, StatusPlot):
        #                 plotter = StatusPlotItem(item.colormappings,
        #                                          markersize=item.markersize,
        #                                          align=item.align)
        #                 view.addPlotter(plotter)
        #             elif isinstance(item, ArrayPlot):
        #                 plotter = ArrayPlotItem(item.colormappings,
        #                                         markersize=item.markersize)
        #                 view.addPlotter(plotter)
        #             else:
        #                 print("***unknown plotter type: {}".format(type(item)))
        #         view.setResultParser(widget.result)
        #         widget.views['session'] = view
        #
        # else:
        #     widget.result = None
        widget._results     = ResultParser.build(model, serial=widget._serialUI, output=True)
        widget._statsUI     = ResultStatsUI.build(model, results=widget._results)
        widget._sessionView = SessionView.build(model, results=widget._results)

        # add loggerUI
        widget._loggers  = LoggerUI.build(model,
                                serial=widget._serialUI, note=widget._noteUI)
        # for name, logger in model.loggers.items():
        #     uiobj = LoggerUI.get(logger.name, label=logger.label, fmt=logger.fmt)
        #     uiobj.attachSerialIO(widget.serial)
        #     if 'note' in model.features:
        #         uiobj.attachNoteUI(widget.features['note'])
        #     widget.loggers[name] = uiobj

        widget.__layout()
        return widget

fromTask = TaskWidget.fromTask
