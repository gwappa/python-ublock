from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore

class ConfigUI:
    @classmethod
    def build(self, model, serial=None, output=True):
        configs = model.configs
        if len(configs) == 0:
            return None
        elif len(configs) == 1:
            group = tuple(configs.values())[0]
            return SimpleConfigUI.build(group, serial=serial, output=output)
        else:
            return TabConfigUI.build(configs, serial=serial, output=output)

class SimpleConfigUI(QtWidgets.QWidget, ConfigUI):
    @classmethod
    def build(cls, configs, serial=None, output=True):
        uiconfigs  = OrderedDict()
        for config in configs.values():
            uiconfigs[config.name] = ConfigElement(config.label, config.command)
        if len(uiconfigs) == 0:
            return None
        else:
            return cls(uiconfigs, serial=serial, output=output)

    def __init__(self, configs, serial=None, output=True, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent=parent)
        super(ConfigUI, self).__init__()
        self.__layout  = QtWidgets.QFormLayout()
        self.setLayout(self.__layout)
        self.__mapping = OrderedDict()
        for name, ui in configs.items():
            self.__mapping[name] = ui
            self.__layout.addRow(ui.label, ui.editor)
        if serial is not None:
            self.setSerialIO(serial, output=output)

    def __getitem__(self, key):
        return self.__mapping[key]

    def keys(self):
        return self.__mapping.keys()

    def values(self):
        return self.__mapping.values()

    def items(self):
        return self.__mapping.items()

    def setSerialIO(self, serial, output=True):
        for ui in self.__mapping.values():
            ui.setSerialIO(serial, output=output)


class TabConfigUI(QtWidgets.QTabWidget, ConfigUI):
    @classmethod
    def build(cls, configs, serial=None, output=True):
        uiconfigs = OrderedDict()
        for groupname, group in configs.items():
            uiconfigs[groupname] = OrderedDict()
            for config in group.values():
                uiconfigs[groupname][config.name] = ConfigElement(config.label, config.command)
        if len(uiconfigs) == 0:
            return None
        else:
            return cls(uiconfigs, serial=serial, output=output)

    def __init__(self, configs, serial=None, output=True, parent=None):
        super(QtWidgets.QTabWidget, self).__init__(parent=parent)
        super(ConfigUI, self).__init__()
        self.__mapping = OrderedDict()
        for groupname, group in configs.items():
            page = SimpleConfigUI(group, serial=serial, output=output)
            self.addTab(page, groupname)
            self.__mapping[groupname] = page

    def __getitem__(self, key):
        return self.__mapping[key]

class ConfigElement(QtCore.QObject):
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
