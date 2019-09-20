from collections import OrderedDict
from .core import protocol as _proto

"""the model layer of ublock."""

class Command:
    """the base class for command-based parameters."""

    def __init__(self, name, command, label=None, desc=None):
        if name is None:
            raise ValueError("'name' cannot be None for a {} instance".format(self.__class__.__name__))
        elif command is None:
            raise ValueError("'command' cannot be None for a {} instance".format(self.__class__.__name__))
        elif desc is None:
            desc = name
        if label is None:
            label = name

        self.name       = name
        self.command    = command
        self.label      = label
        self.desc       = desc

class Mode(Command):
    """a class that represents the task mode."""

    def __init__(self, name, command, label=None, desc=None):
        super().__init__(name, command, label=label, desc=desc)

class Config(Command):
    """a class that represents the configuration parameters for the task."""

    def __init__(self, name, command, label=None, desc=None, group=None,
                 defaultvalue=0):
        super().__init__(name, command, label=label, desc=desc)
        self.group = str(group)
        self.defaultvalue = int(defaultvalue)

class Action(Command):
    """a class that represents the task action."""

    def __init__(self, name, command, label=None, desc=None,
                 repeats=True, returns='result', criteria=None,
                 strict=None):
        super().__init__(name, command, label=label, desc=desc)
        self.returns    = returns
        self.repeats    = bool(repeats)
        self.criteria   = criteria
        self.strict     = strict

class Result:
    """a class that is used inside the Model instance
    to store the model of result messages.
    """

    def __init__(self, status=(), values=(), arrays=()):
        self.status     = list(status)
        self.values     = list(values)
        self.arrays     = list(arrays)
        self.plotted    = OrderedDict()
        self.counted    = []
        self.rewarded   = []

    def plot(self, item, **kwargs):
        if not isinstance(item, str):
            raise ValueError(f"expected a string, but got {item.__class__.__name__}")
        if item in self.status:
            self.plotted[item] = StatusPlot(item, **kwargs)
        elif item in self.values:
            self.plotted[item] = ValuePlot(item, **kwargs)
        elif item in self.arrays:
            self.plotted[item] = ArrayPlot(item, **kwargs)
        else:
            raise ValueError(f"Result.plot() only accepts the status/value/array names")

    def count(self, item):
        if not isinstance(item, str):
            raise ValueError(f"expected a string, but got {item.__class__.__name__}")
        elif item not in self.status:
            raise ValueError(f"Result.count() only accepts names of a status")
        self.counted.append(item)

    def reward(self, item):
        if not isinstance(item, str):
            raise ValueError(f"expected a string, but got {item.__class__.__name__}")
        elif item not in self.status:
            raise ValueError(f"Result.reward() only accepts names of a status")
        self.rewarded.append(item)

    def as_dict(self):
        return dict(status=self.status, values=self.values, arrays=self.arrays)

class ResultPlot:
    """a base configuration class for plotting results"""
    def __init__(self, name, color='k', markersize=8, align='origin'):
        """
        'name' refers to one of status/values/arrays in the result message.
        """
        self.name       = name
        self.color      = color
        self.markersize = markersize
        self.align      = align

class StatusPlot(ResultPlot):
    """configuration used to generate plots for result status."""
    def __init__(self, name, color='k', markersize=8, align='origin'):
        super().__init__(name, color=color, markersize=markersize, align=align)

class ArrayPlot(ResultPlot):
    """configuration used to generate plots for array-type results."""
    def __init__(self, name, color='k', markersize=8, align='origin'):
        super().__init__(name, color=color, markersize=markersize, align=align)

class ValuePlot(ResultPlot):
    """configuration used to generate plots for value-type results."""
    def __init__(self, name, color='k', width=8, align='origin', start='none', stop='none'):
        super().__init__(name, color=color, markersize=width, align=align)
        self.start = start
        self.stop  = stop

    def __getattr__(self, name):
        if name == 'width':
            return self.markersize
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == 'width':
            super().__setattr__('markersize', value)
        else:
            super().__setattr__(name, value)

class Responder:
    """the base class for those that respond to messages from the serial line."""
    def __init__(self, name, category=_proto.ALL):
        self.name     = name
        if isinstance(category, str):
            self.category = (category,)
        else:
            self.category = tuple(category)

class Logger(Responder):
    def __init__(self, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log"):
        super().__init__(name, category=_proto.ALL)
        self.label  = label
        self.fmt    = fmt

class Feature:
    """"the class that represents an extra feature on the interface."""
    def __init__(self, label='', desc=''):
        self.label = label
        self.desc  = desc

class RawInput(Feature):
    """the class that represents the raw-input UI."""
    def __init__(self, label="Command", desc="raw command input"):
        super().__init__(self, label, desc)

class RunningNote(Feature):
    """"the class that represents the running-note UI."""
    def __init__(self, label="Running note", desc="running note"):
        super().__init__(self, label, desc)

class Task:
    """a class for construction of a serial communication model.
    it does not do anything per se, but it helps generate the UI
    through e.g. ublock.app.fromTask(task) or ublock.tty.fromTask(task).
    """
    available_features = ('control', 'raw', 'note', 'echo')
    available_views    = ('stats', 'session', 'histogram')

    def __init__(self, name,
                    controls=True,
                    echoed=True,
                    rawcommand=False,
                    note=True):
        """name: the name of this task"""
        self.name           = name
        self.modes          = OrderedDict()
        self.configs        = OrderedDict()
        self.actions        = OrderedDict()
        self.loggers        = OrderedDict()
        self.result         = None
        self.features       = []
        self.views          = {}

    def addMode(self, name, command, label=None, desc=None,
                defaultindex=0):
        self.modes[name] = Mode(name, command, label=label, desc=desc,
                                defaultindex=defaultindex)

    def addConfig(self, name, command, label=None, desc=None, group=None,
                  defaultvalue=0):
        self.configs[name] = Config(name, command, label=label,
                                    desc=desc, group=group,
                                    defaultvalue=defaultvalue)

    def addAction(self, name, command, label=None, desc=None,
                  returns='result', repeats=True, criteria=None, strict=None):
        self.actions[name] = Action(name, command, label=label,
                                    desc=desc, repeats=repeats,
                                    returns=returns, criteria=criteria, strict=strict)

    def setResult(self, status=(), values=(), arrays=()):
        self.result = Result(status, values, arrays)

    def addLogger(self, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log"):
        self.loggers[name] = Logger(name, label=label, fmt=fmt)

    def addFeatures(self, *features):
        """current set of features: see Task.available_features"""
        for feature in features:
            feature = feature.strip()
            if feature in self.available_features:
                self.features.append(feature)

    def addView(self, name, **configs):
        """adds a result view with the type 'name' to this model.
        contents of 'configs' vary according to the view type."""
        if name in self.available_views:
            self.views[name] = configs
