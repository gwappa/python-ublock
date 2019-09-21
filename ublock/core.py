from collections import OrderedDict

"""the core model layer of ublock."""

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
    ALL         = '' # wildcard used for not filtering responses

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

class Results:
    """a class that is used inside the Model instance
    to store the model of result messages.
    """

    def __init__(self, status=(), values=(), arrays=(),
                plotted=dict(), counted=(), rewarded=()):
        self.status     = list(status)
        self.values     = list(values)
        self.arrays     = list(arrays)
        self.plotted    = OrderedDict()
        for name, kwargs in plotted.items():
            self.plot(name, **kwargs)
        self.counted    = list(counted)
        self.rewarded   = list(rewarded)

    def plot(self, item, **kwargs):
        if isinstance(item, ResultPlot):
            for lab, ls in (("status", self.status),
                            ("value",  self.values),
                            ("array",  self.arrays)):
                if item.category == lab:
                    if item.name not in ls:
                        raise ValueError(f"name '{item.name}' not found as a result {lab}")
                    else:
                        self.plotted[item.name] = item
                        return
            raise ValueError(f"unknown result category: {item.category}")
        elif not isinstance(item, str):
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
    def __init__(self, name, category='none',
                 color='k', markersize=8, align='origin'):
        """
        'name' refers to one of status/values/arrays in the result message.
        """
        self.name       = name
        self.category   = category
        self.color      = color
        self.markersize = markersize
        self.align      = align

class StatusPlot(ResultPlot):
    """configuration used to generate plots for result status."""
    def __init__(self, name, color='k', markersize=8, align='origin'):
        super().__init__(name, category='status',
                        color=color, markersize=markersize, align=align)

class ArrayPlot(ResultPlot):
    """configuration used to generate plots for array-type results."""
    def __init__(self, name, color='k', markersize=8, align='origin'):
        super().__init__(name, category='array',
                        color=color, markersize=markersize, align=align)

class ValuePlot(ResultPlot):
    """configuration used to generate plots for value-type results."""
    def __init__(self, name, color='k', width=8, align='origin', start='none', stop='none'):
        super().__init__(name, category='value',
                        color=color, markersize=width, align=align)
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
#
# class Responder:
#     """the base class for those that respond to messages from the serial line."""
#     def __init__(self, name, category=protocol.ALL):
#         self.name     = name
#         if isinstance(category, str):
#             self.category = (category,)
#         else:
#             self.category = tuple(category)

class Logger:
    def __init__(self, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log"):
        self.name   = name
        self.label  = label
        self.fmt    = fmt

# class Feature:
#     """"the class that represents an extra feature on the interface."""
#     def __init__(self, label='', desc=''):
#         self.label = label
#         self.desc  = desc
#
# class RawInput(Feature):
#     """the class that represents the raw-input UI."""
#     def __init__(self, label="Command", desc="raw command input"):
#         super().__init__(self, label, desc)
#
# class RunningNote(Feature):
#     """"the class that represents the running-note UI."""
#     def __init__(self, label="Running note", desc="running note"):
#         super().__init__(self, label, desc)

def _checked_add(cmd, namedict, commands, label='item', task='task'):
    if cmd.name in namedict.keys():
        raise ValueError(f"duplicate name found for {label} in '{task}': {cmd.name}")
    else:
        dup = [item for item in commands if item.command == cmd.command]
        if len(dup) > 0:
            raise ValueError(f"duplicate command found for '{task}': {cmd.name} and {dup[0].name} ({cmd.command})")
    namedict[cmd.name] = cmd
    _fine(f"...loaded {label} for '{task}': {cmd.name}({cmd.command})")

class Task:
    """a class for construction of a serial communication model.
    it does not do anything per se, but it helps generate the UI
    through e.g. ublock.app.fromTask(task) or ublock.tty.fromTask(task).
    """

    def __init__(self, name,
                    controls=True,
                    echoed=True,
                    rawcommand=False,
                    note=True):
        """name: the name of this task"""
        self.name       = name
        self._modes     = OrderedDict()
        self._configs   = OrderedDict()
        self._actions   = OrderedDict()
        self._loggers   = OrderedDict()

        self._results   = None
        self.controls   = controls
        self.echoed     = echoed
        self.rawcommand = rawcommand
        self.note       = note

    def __getattr__(self, name):
        if name in ('modes', 'actions', 'loggers', 'results'):
            return getattr(self, '_'+name)
        elif name == 'configs':
            # order by groups
            out = OrderedDict()
            for cfg in self._configs.values():
                if cfg.group not in out.keys():
                    out[cfg.group] = OrderedDict()
                out[cfg.group][cfg.name] = cfg
            return out
        elif name == 'commands':
            return sum([list(m.values()) for m in (self._modes,
                                                   self._configs,
                                                   self._actions)],
                        [])
        else:
            raise AttributeError(name)

    def add(self, item):
        if isinstance(item, Results):
            if self._results is None:
                self._results = item
            else:
                raise ValueError("cannot set two Results instance!")
        elif isinstance(item, Mode):
            _checked_add(item, self._modes, self.commands, label='mode', task=self.name)
        elif isinstance(item, Config):
            _checked_add(item, self._configs, self.commands, label='config', task=self.name)
        elif isinstance(item, Action):
            _checked_add(item, self._actions, self.commands, label='action', task=self.name)
        elif isinstance(item, Logger):
            if item.name in self._loggers:
                raise ValueError(f"duplicate name found for {self.name}/logger: {item.name}")
            self._loggers[item.name] = item

        return self

    # def addMode(self, name, command, label=None, desc=None,
    #             defaultindex=0):
    #     self.modes[name] = Mode(name, command, label=label, desc=desc,
    #                             defaultindex=defaultindex)
    #
    # def addConfig(self, name, command, label=None, desc=None, group=None,
    #               defaultvalue=0):
    #     self.configs[name] = Config(name, command, label=label,
    #                                 desc=desc, group=group,
    #                                 defaultvalue=defaultvalue)
    #
    # def addAction(self, name, command, label=None, desc=None,
    #               returns='result', repeats=True, criteria=None, strict=None):
    #     self.actions[name] = Action(name, command, label=label,
    #                                 desc=desc, repeats=repeats,
    #                                 returns=returns, criteria=criteria, strict=strict)
    #
    # def setResult(self, status=(), values=(), arrays=()):
    #     self.result = Result(status, values, arrays)
    #
    # def addLogger(self, name, label=None, fmt="{}_%Y-%m-%d_%H%M%S.log"):
    #     self.loggers[name] = Logger(name, label=label, fmt=fmt)
    #
    # def addFeatures(self, *features):
    #     """current set of features: see Task.available_features"""
    #     for feature in features:
    #         feature = feature.strip()
    #         if feature in self.available_features:
    #             self.features.append(feature)
    #
    # def addView(self, name, **configs):
    #     """adds a result view with the type 'name' to this model.
    #     contents of 'configs' vary according to the view type."""
    #     if name in self.available_views:
    #         self.views[name] = configs

from .app import _debug, _fine
