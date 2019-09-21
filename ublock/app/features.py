from collections import OrderedDict
from pyqtgraph.Qt import QtWidgets, QtCore

class RawCommandUI(QtWidgets.QWidget):
    """a widget class that provides functionality to send
    a line of command out to the device."""

    dispatchingRequest = QtCore.pyqtSignal(str)

    @classmethod
    def build(cls, model, serial=None, output=True):
        if model.rawcommand == True:
            ui = cls()
            if serial is not None:
                ui.setEnabled(False)
                ui.setSerialIO(serial, output=output)
            return ui
        else:
            return None

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
        self.editor.setText("")

class NoteUI(QtWidgets.QGroupBox):
    runningNoteAdded = QtCore.pyqtSignal(str)

    @classmethod
    def build(cls, model, serial=None, output=True):
        if model.note == True:
            return cls()
        else:
            return None

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

class ControlUI(QtWidgets.QWidget):
    quitRequested  = QtCore.pyqtSignal()
    clearRequested = QtCore.pyqtSignal()

    @classmethod
    def build(cls, model, widget=None):
        if model.controls == True:
            ui = cls()
            if widget is not None:
                ui.quitRequested.connect(widget.quitApplication)
        else:
            return None

    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent=parent)
        self.clearButton = QtWidgets.QPushButton("Clear plots")
        self.clearButton.setEnabled(False)
        self.clearButton.clicked.connect(self.promptClear)
        self.quitButton  = QtWidgets.QPushButton("Quit")
        self.quitButton.clicked.connect(self.promptQuit)

        self.__layout     = QtWidgets.QHBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.addStretch()
        self.__layout.addWidget(self.clearButton)
        self.__layout.addWidget(self.quitButton)

    def promptClear(self):
        ret = QtWidgets.QMessageBox.warning(self,
                                            "Clear plots",
                                            "Are you sure you want to clear the session view?",
                                            QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                                            QtWidgets.QMessageBox.Yes)
        if ret == QtWidgets.QMessageBox.Yes:
            self.clearRequested.emit()


    def promptQuit(self):
        """ask user whether or not to quit the app."""
        ret = QtWidgets.QMessageBox.warning(self,
                                            "About to quit",
                                            "Are you sure you want to quit?",
                                            QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                                            QtWidgets.QMessageBox.Yes)
        if ret == QtWidgets.QMessageBox.Yes:
            self.quitRequested.emit()
