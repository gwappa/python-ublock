from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore

class ActionUI(QtWidgets.QWidget):
    @classmethod
    def build(cls, model, serial=None, output=True):
        actions   = model.actions
        if len(actions) == 0:
            return None

        uiactions = OrderedDict()
        for name, action in actions.items():
            # uitype = RepeatUI if action.repeats == True else ActionUI
            uiobj = ActionRunner(action.label, action.command, returns=action.returns,
                            criteria=action.criteria, strict=action.strict)
            # uiobj.setSerialIO(widget.serial, output=True)
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

    def __init__(self, label, command, returns='result', criteria=None,
                strict=None, parent=None):
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
