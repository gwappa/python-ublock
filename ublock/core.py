import time
import threading
from traceback import print_tb
import serial

class protocol:
    """used for discriminating between line messages
    other than the `DELIMITER`, usages are completely
    up to the implementor."""
    DEBUG       = '.'
    INFO        = '>'
    CONFIG      = '@'
    RESULT      = '+'
    ERROR       = '*'
    OUTPUT      = '<'
    DELIMITER   = ';'
    HELP        = '?'

class iothread(threading.Thread):
    def __init__(self, port, delegate, waitfirst=0, initialcmd=None):
        super().__init__()
        self.port       = port
        self.quitreq    = False
        self.buf        = b''
        self.delegate   = delegate
        self.connected  = False
        self.waitfirst  = waitfirst
        self.initialcmd = initialcmd
        self.port.timeout = 1
        self.start()

    def writeLine(self, msg):
        self.port.write((msg + "\r\n").encode())

    def interrupt(self):
        self.quitreq = True
        self.port.close()

    def run(self):
        time.sleep(self.waitfirst)
        if self.initialcmd is not None:
            self.writeLine(self.initialcmd)
        try:
            while not self.quitreq:
                try:
                    ch = self.port.read()
                except serial.SerialTimeoutException:
                    continue
                if self.connected == False:
                    self.connected = True
                    self.delegate.connected()
                self.buf += ch
                if ch == b'\n':
                    self.delegate.handleLine(self.buf[:-2].decode().strip())
                    self.buf = b''
        except serial.SerialException:
            pass # just finish the thread
        print(">port closed")
        self.delegate.closed()

class baseclient:
    def __init__(self, addr, baud=9600, waitfirst=0, initialcmd=None):
        self.port       = serial.Serial(port=addr, baudrate=baud)
        self.io         = iothread(self.port, self, initialcmd=initialcmd, waitfirst=waitfirst)

    def __enter__(self):
        return self

    def __exit__(self, exc, *args):
        if exc is not None:
            print_tb()
        self.close()

    def connected(self):
        pass

    def closed(self):
        pass

    def close(self):
        if self.io is not None:
            self.io.interrupt()
            self.io.join()
            self.io = None

    def request(self, cmd):
        if self.io is not None and self.io.connected == True:
            self.io.writeLine(cmd)
        else:
            print("***port not connected: {}".format(self.addr))

    def handleLine(self,line):
        pass

class eventhandler:
    """the interface class for receiving events from CUISerial protocol.
    except for `connected` and `closed`, the meaning of each type of messages
    is up to the user."""

    def connected(self, client):
        """called when a serial port is opened (does not necessarily mean
        that the port is ready for receiving commands).
        
        `client` stands for the corresponding `client` object."""
        pass

    def closed(self):
        """called when the connected serial port is closed."""
        pass
    
    def received(self, line):
        """called with a raw line that arrived at the serial port."""
        pass

    def debug(self, line):
        pass

    def info(self, line):
        pass

    def config(self, line):
        pass

    def result(self, line):
        pass

    def error(self, line):
        pass

    def output(self, line):
        pass

    def message(self, line):
        """called with a line that does not fall into any of the other
        categories"""
        pass
        
def tokenize(line, ch=protocol.DELIMITER, has_header=True):
    """a utility function to split an input line into a chunk of tokens.
    it yields a token a time until it reaches the end of line."""

    if has_header == True:
        line = line[1:]
    elems = line.split(ch)

    # stripping on the right hand side
    while len(elems[-1].strip()) == 0:
        elems = elems[:-1]

    if len(elems) == 0:
        yield line
    else:
        for elem in elems:
            if len(elem) == 0:
                yield elem

class client(baseclient):
    """a client for serial communication that conforms to the CUISerial protocol."""
    def __init__(self, addr, handler=None, baud=9600, waitfirst=0, initialcmd=None):
        super().__init__(addr, baud=baud, waitfirst=waitfirst, initialcmd=initialcmd)
        if handler is None:
            handler = eventhandler()
        self.handler = handler

    @classmethod
    def Uno(cls, addr, handler=None, baud=9600, initialcmd=None):
        """default call signatures for Uno-type boards."""
        return cls(addr, handler=handler, baud=baud, waitfirst=1.2, initialcmd=initialcmd)

    @classmethod
    def Leonardo(cls, addr, handler=None, baud=9600, initialcmd=protocol.HELP):
        """default call signatures for Leonardo-type boards."""
        return cls(addr, handler=handler, baud=baud, waitfirst=0, initialcmd=initialcmd)

    def connected(self):
        self.handler.connected(self)

    def closed(self):
        self.handler.closed()

    def handleLine(self, line):
        """calls its handler's method(s) in turn, based on its first character."""
        if self.handler is None:
            return
        self.handler.received(line)

        line = line.strip()
        if line.startswith(protocol.DEBUG):
            self.handler.debug(line)
        elif line.startswith(protocol.INFO):
            self.handler.info(line)
        elif line.startswith(protocol.CONFIG):
            self.handler.config(line)
        elif line.startswith(protocol.RESULT):
            self.handler.result(line)
        elif line.startswith(protocol.ERROR):
            self.handler.error(line)
        elif line.startswith(protocol.OUTPUT):
            self.handler.output(line)
        else:
            self.handler.message(line)
    
    def close(self):
        if self.io is not None:
            super().close()
            if self.handler is not None:
                self.handler.closed()

class loophandler:
    """the interface for classes that receive messages from `loop`."""

    def starting(self, command, number, counter):
        """invoked when single loop with index being `counter`,
        out of total number `number`, is starting"""
        pass

    def evaluate(self, result):
        """should return a boolean value whether or not to increment
        the counter, given the `result` message."""
        return True

    def request(self, command):
        """proxy for serial I/O to dispatch a request."""
        raise RuntimeError("no IO linked to: {}".format(self))

    def done(self, command, number, counter):
        """invoked when the whole loop is ending."""
        pass

class loop:
    """class that handles loop structures.
    
    `io` can be any `client`-type instance (that accepts `request()`).
    `handler` is supposed to be a `loophandler` object.
    both `io` and `handler` can be set later, but before calling the
    `start()` (or `run()`) method.

    note that its `run()` method by itself only specifies 
    the procedure itself, and it does not run in another thread.

    by calling its `start()` method, instead, it returns a new loop
    execution thread.
    """

    def __init__(self, command, number, interval=0,
                    io=None, handler=None):
        super().__init__()
        self.command  = command
        self.io       = io
        self.number   = number
        self.interval = interval
        self.handler  = loophandler() if handler is None else handler
        self.update   = threading.Condition()
        self.result   = None
        self.toabort  = False

    def start(self, init=threading.Thread):
        """starts a new thread that has this instance's `run()`
        as the target.

        the callable responsible for the thread generation
        can be specified via the `init` keyword argument
        (note that the callable must take the `target` option
        to be compatible with the threading.Thread initializer).
        
        returns the started thread.
        """
        thread = init(target=self.run)
        thread.start()
        return thread

    def run(self):
        counter = 0
        self.toabort = False
        while counter < self.number:
            self.handler.starting(self.command,self.number,counter)
            self.update.acquire()
            try:
                if self.io is not None:
                    self.io.request(self.command)
                    self.update.wait()
                    if self.handler.evaluate(self.result) == True:
                        counter += 1
                    if self.toabort == True:
                        break
                else:
                    print("***no IO linked to: {}".format(self))
                    break
            finally:
                self.update.release()
            if (self.number > 1) and (self.interval > 0):
                time.sleep(self.interval)
        self.handler.done(self.command,self.number,counter)

    def abort(self):
        self.update.acquire()
        self.toabort = True
        self.update.release()

    def updateWithMessage(self, msg):
        self.update.acquire()
        self.result = msg
        self.update.notify_all()
        self.update.release()

