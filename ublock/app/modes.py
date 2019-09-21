from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore
from . import _debug

class ModeUI(QtWidgets.QWidget):
    @classmethod
    def build(cls, model, serial=None, output=True):
        selector = ModeSelector.build(model, serial=serial, output=output)
        if selector is None:
            return None
        else:
            return cls(selector, serial=serial)

    def __init__(self, selector, serial=None, parent=None):
        super().__init__(parent=parent)
        self.__layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.__layout)
        self.label    = QtWidgets.QLabel("Mode: ")
        self.label.setEnabled(False)
        self.selector = selector
        if serial is not None:
            self.serial = serial
            self.serial.serialStatusChanged.connect(self.label.setEnabled)
        self.__layout.addWidget(self.label)
        self.__layout.addWidget(self.selector)

class ModeSelector(QtWidgets.QComboBox):
    # emitted when the user changed the selection
    configValueChanged = QtCore.pyqtSignal(str)

    # emitted when SerialIO returns a mode selection
    currentModeChanged = QtCore.pyqtSignal(str)

    @classmethod
    def build(cls, model, serial=None, output=True):
        """builds ModeConfigUI based on a model `model`.
        You can specify a `SerialIO` to `serial`.

        If the model does not have any modes, it returns None."""
        if len(model.modes) > 0:
            ui = cls(model.modes, parent=None)
            if serial is not None:
                ui.setSerialIO(serial, output=output)
            return ui
        else:
            return None

    def __init__(self, options, parent=None):
        """options -- {modestr: modecmd} dict"""
        super().__init__(parent=parent)
        self.loadOptions(options)
        self.setEnabled(False)
        self.prevIndex = -1

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
            _debug(f"...mode->{idx}({self._abbreviations[idx]})")
            self.setCurrentIndex(idx)
            self.currentModeChanged.emit(self.currentText())
            self.prevIndex = idx
            self.valueChanging = False

    def updateWithError(self, msg):
        if self.valueChanging == True:
            self.setCurrentIndex(self.prevIndex)
            self.valueChanging = False
