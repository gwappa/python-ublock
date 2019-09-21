from collections  import OrderedDict
from threading    import Lock
from pyqtgraph.Qt import QtWidgets, QtCore

from serial.tools import list_ports
from eventcalls import EventHandler, Routine
from eventcalls.io import SerialIO as SerialTerm

from ..core import protocol
from . import _debug, getApp as _getApp

class SerialIO(QtWidgets.QWidget, EventHandler, protocol):
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
    resultElementReceived   = QtCore.pyqtSignal(str)
    errorMessageReceived    = QtCore.pyqtSignal(str)
    outputMessageReceived   = QtCore.pyqtSignal(str)
    #    rawMessageReceived      = QtCore.pyqtSignal(str)

    def __init__(self, clienttype='leonardo', handler=None,
             label="Port: ", acqByResp=True, parent=None, **kwargs):
        super(QtWidgets.QWidget, self).__init__(parent=parent)
        super(EventHandler, self).__init__()
        if clienttype not in ('leonardo', 'uno'):
            raise ValueError(f"client type must be one of ('leonardo', 'uno'), got {clienttype}")

        _getApp().aboutToQuit.connect(self.closePort)
        self.portEnumerator = QtWidgets.QComboBox()
        self.enumeratePorts()
        self.portEnumerator.currentIndexChanged.connect(self.updateSelection)
        self.label = QtWidgets.QLabel(label)
        self.connector = ConnectorButton(self)

        #        self.serialclient   = serialclient  # the "function" that is used to open serial port
        #        self.clientkw       = kwargs   # the arguments used to call "handler"
        #        self.clientkw['handler'] = self if handler is None else handler
        #
        #        self.acqByResp  = acqByResp
        #        self.io     = None
        #        self.reader = None
        self.clienttype = clienttype
        self.term       = None
        self.routine    = None
        self.active     = False     # whether or not this IO is "connected"
        self.transact   = Lock()

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
        _debug(f"...openPort({addr})")
        self.term    = SerialTerm.open(addr)
        self.routine = Routine(self.term, self, start=True)

    def closePort(self):
        _debug("...closePort()")
        if self.routine is not None:
            self.routine.stop()
            self.routine = None
            self.serialClosed.emit()
            self.active = False

    def initialized(self, evt=None):
        """EventHandler callback."""
        _debug("...initialized() callback")
        if self.clienttype == 'leonardo':
            self.active = True

    def done(self, evt=None):
        """EventSource callback."""
        _debug("...done() callback")
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
        """called when the user changes the combobox selection."""
        _debug(f"...selected({idx})")
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
        """responds to a click on the Connect/Disconnect button."""
        if value == True:
            self.openPort(self.selectedPort.device)
        else:
            self.closePort()

    def request(self, line):
        """sends a line of command (not having the newline character(s))
        through the serial port."""
        _debug(f"...request('{line}')")
        if self.io is not None:
            with self.transact:
                self.io.request(line)

    def _handle_for(self, line, ch, sig, esig):
        if line.startswith(ch):
            sig.emit(line[1:])
            if esig is not None:
                elems = [v.strip() for v in line[1:].split(self.DELIMITER) \
                            if len(v.strip()) > 0]
                for elem in elems:
                    esig.emit(elem)

    def handle(self, line):
        """re-implementing EventHandler's `received`"""
        _debug(f"...handle('{line}')")
        with self.transact:
            self.messageReceived.emit(line)
            self._handle_for(line, self.DEBUG,  self.debugMessageReceived,  None)
            self._handle_for(line, self.INFO,   self.infoMessageReceived,   None)
            self._handle_for(line, self.CONFIG, self.configMessageReceived, self.configElementReceived)
            self._handle_for(line, self.RESULT, self.resultMessageReceived, self.resultElementReceived)
            self._handle_for(line, self.ERROR,  self.errorMessageReceived,  None)
            self._handle_for(line, self.OUTPUT, self.outputMessageReceived, None)

#    def message(self, line):
#        """re-implementing eventhandler's `message`"""
#        self.rawMessageReceived.emit(line)


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
