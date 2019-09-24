from collections import OrderedDict
from _threading import Thread, Lock
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

class ActionUI(QtWidgets.QWidget):
    @classmethod
    def build(cls, model, serial=None, output=True):
        actions   = model.actions
        if len(actions) == 0:
            return None

        uiactions = OrderedDict()
        for name, action in actions.items():
            uiobj = ActionRunner(action.label, action.command, returns=action.returns)
            uiactions[name] = uiobj
        return cls(uiactions, serial=serial, output=output)

    def __init__(self, actions, serial=None, output=True, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent=parent)
        self.__mapping  = OrderedDict()
        self.__layout   = QtWidgets.QHBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.addStretch()
        for name, ui in actions.items():
            self.__mapping[name] = ui
            self.__layout.addWidget(ui)
            if serial is not None:
                ui.setSerialIO(serial, output=output)

    def __getitem__(self, key):
        return self.__mapping[key]

class ActionRunner(QtWidgets.QPushButton):
    """the GUI class for managing an action (that does not accept any repeats)"""
    activated = QtCore.pyqtSignal(str)

    def __init__(self, label, command, returns='result', parent=None):
        """currently `strict` has no effect"""
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
            self.activated.connect(serial.requestAction)
            serial.requestStatusChanged.connect(self.updateWithRequestStatus)
            serial.requestAbandoned.connect(self.re_enable)
        if self.returns is not None:
            if self.returns == 'result':
                serial.resultMessageReceived.connect(self.checkResults)
            elif self.returns == 'config':
                serial.configMessageReceived.connect(self.checkResults)
        serial.serialStatusChanged.connect(self.setEnabled)

    def updateWithRequestStatus(self, value):
        self.setEnabled(not value)

    def re_enable(self):
        self.setEnabled(True)

    def dispatchCommand(self):
        self.activated.emit(self.command)
        self.waiting = True

    def checkResults(self, msg):
        if self.evaluate(msg) == True:
            if self.waiting == True:
                self.waiting = False
        self.setEnabled(True)

    def evaluate(self, result):
        return True

LABEL_RUN   = "Run"
LABEL_ABORT = "Abort"

COL_LABEL   = 0
COL_CURRENT = 1
COL_OFLABEL = 2
COL_TOTAL   = 3
COL_ACTION  = 4

class LoopUI(QtWidgets.QWidget):
    @classmethod
    def build(cls, model, serial=None, output=True):
        actions   = model.actions
        if len(actions) == 0:
            return None

        loops = []
        for action in actions.values():
            if action.repeats == False:
                continue
            loops.append(LoopRunner(action.label, action.command,
                                returns=action.returns, strict_criteria=action.strict_criteria))
        return cls(loops, serial=serial, output=output)

    def __init__(self, loops=(), serial=None, output=True, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent=parent)
        self._loops = OrderedDict()
        for loop in loops:
            self._loops[loop.name] = loop
        self._layout = QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        offset = 0
        for loop in self._loops.values():
            self._layout.addWidget(loop.label,   COL_LABEL,   offset)
            self._layout.addWidget(loop.current, COL_CURRENT, offset)
            self._layout.addWidget(loop.oflabel, COL_OFLABEL, offset)
            self._layout.addWidget(loop.total,   COL_TOTAL,   offset)
            self._layout.addWidget(loop.action,  COL_ACTION,  offset)
            if loop.strict is not None:
                self._layout.addWidget(loop.strict, COL_STRICT, offset)
            if serial is not None:
                loop.setSerialIO(serial, output=output)
            offset += 1

    def __getattr__(self, key):
        return self._loops[key]

    def __len__(self):
        return len(self._loops)

class LoopRunner(QtCore.QObject):
    def __init__(self, name, command, returns='result', strict_criteria=(), parent=None):
        super(QtCore.QObject, self).__init__(parent=parent)
        self.name      = name
        self.command   = command
        self.returns   = returns
        self.strict_criteria  = strict_criteria
        self._runner   = QtCore.QThread()
        self.moveToThread(self._runner)
        self._runner.started.connect(self.runLoop)
        self._running  = False
        self._response = Lock()

        self._label    = QtWidgets.QLabel(f"Loop \"{self.name}\":")
        self._current  = QtWidgets.QLineEdit()
        self._oflabel  = QtWidgets.QLabel(f"of")
        self._total    = QtWidgets.QLineEdit()
        self._total.setValidator(QtGui.QIntValidator(0, 1000))
        self._action   = QtWidgets.QPushButton(LABEL_RUN)
        self._action.clicked.connect(self.toggleLoop)
        if len(strict_criteria) > 0:
            self._strict = QtWidgets.QCheckBox("strict mode")
        else:
            self._strict = None

    def __getattr__(self, name):
        if name in ('label', 'current', 'oflabel', 'total', 'action', 'strict'):
            return getattr(self, '_'+name)
        else:
            return super().__getattr__(name)

    def setSerialIO(self, serial, output=True):
        if output == True:
            # self.activated.connect(serial.requestAction)
            # serial.requestStatusChanged.connect(self.updateWithRequestStatus)
            # serial.requestAbandoned.connect(self.re_enable)
            pass
        if self.returns is not None:
            if self.returns == 'result':
                serial.resultMessageReceived.connect(self.updateWithResponse)
            elif self.returns == 'config':
                serial.configMessageReceived.connect(self.updateWithResponse)
        serial.serialStatusChanged.connect(self.setEnabled)

    def updateWithResponse(self, msg):
        pass

    def toggleLoop(self):
        pass

    def runLoop(self):
        self._runner.quit()
