from collections import OrderedDict

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

    def __init__(self, name, command, label=None, desc=None, defaultindex=0):
        super().__init__(name, command, label=label, desc=desc)
        self.defaultindex = defaultindex

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
                 repeats=True, returns='result', criteria=None):
        super().__init__(name, command, label=label, desc=desc)
        self.returns = returns
        self.repeats = bool(repeats)
        self.criteria = None

class Logger:
    def __init__(self, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log"):
        self.name   = name
        self.label  = label
        self.fmt    = fmt

class Result:
    """a class that is used inside the Model instance
    to store the model of result messages.
    """

    def __init__(self, status=(), values=(), arrays=()):
        self.status = list(status)
        self.values = list(values)
        self.arrays = list(arrays)

    def as_dict(self):
        return dict(status=self.status, values=self.values, arrays=self.arrays)

class ResultPlot:
    """a base configuration class for plotting results"""
    def __init__(self, colormappings, markersize=8):
        """
        colormappings: (value, color) dictionary,
        with 'value' being one of status/values/arrays in the result message.
        """
        self.colormappings  = colormappings
        self.markersize     = markersize

class StatusPlot(ResultPlot):
    """configuration used to generate plots for result status"""

    def __init__(self, colormappings, markersize=8, align='origin'):
        """colormappings: (status, color) dictionary
        align: currently only allows 'origin'
        """
        super().__init__(colormappings, markersize=markersize)
        self.align    = align

class ArrayPlot(ResultPlot):
    """configuration used to generate plots for array-type results"""

    def __init__(self, colormappings, markersize=8):
        """colormappings: (arrayname, color) dictionary"""
        super().__init__(colormappings, markersize=markersize)

class Task:
    """a class for construction of a serial communication model.
    it does not do anything per se, but it helps generate the UI
    through e.g. ublock.app.fromTask(task) or ublock.tty.fromTask(task).
    """
    available_features = ('control', 'raw', 'note', 'echo')
    available_views    = ('stats', 'session', 'histogram')

    def __init__(self, name):
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
                  returns='result', repeats=True, criteria=None):
        self.actions[name] = Action(name, command, label=label,
                                    desc=desc, repeats=repeats,
                                    returns=returns, criteria=None)

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








