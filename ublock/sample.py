from ublock.model   import Task, StatusPlot, ArrayPlot
from ublock.app     import fromTask, mainapp

if __name__ == "__main__":
    # a task model that works as a recipe for building a UI widget
    # (this can be turned into a QWidget later, using ublock.app.fromTask())
    task = Task("Sample")

    # add task modes
    task.addMode('Pair', 'P')
    task.addMode('Test', 'T')

    # add config parameters
    task.addConfig('stim_dur_ms', 'd', label='Stimulus duration (ms)')
    task.addConfig('resp_dur_ms', 'f', label='Response window with (ms)')

    # add result parameters
    task.setResult(status=('hit', 'miss', 'catch', 'reject', 'noresp'),
                   values=('wait',),
                   arrays=('lick',))

    # add 'repeatable' actions
    task.addAction('runTask', 'X', label="Run task")

    # add 'non-repeatable' actions
    task.addAction('querySettings', '?', label='Current settings', repeats=False,
                   returns='config')
    task.addAction('clearIndex', 'C', label='Reset trial index', repeats=False)

    # add features
    # 'control' -- adds 'clear plots' & 'quit' buttons at the bottom
    # 'note'    -- adds running-note editor UI (you can write comments into the log files)
    # 'raw'     -- adds raw-command dispatcher UI
    # 'echo'    -- responses from the serial 'echos' out in the standard output
    task.addFeatures('control', 'note', 'raw', 'echo')

    # add result views
    task.addView('stats', summarized=('hit', 'miss', 'catch', 'reject', 'noresp'),
                          rewarded=('hit',))
    status = StatusPlot({'hit':'b', 'miss': 'k', 
                         'catch': 'r', 'reject': 'efefef',
                         'noresp': 'efefef'}, markersize=8)
    events = ArrayPlot({'lick': '8888'}, markersize=6) 
    task.addView('session', items=[status, events], xwidth=5000)

    # to be added: this feature has not been implemented
    task.addView('histogram', xwidth=1000)

    # add logger UI
    task.addLogger("samplesession")

    # build the UI widget from the task model
    widget = fromTask(task, 'uno')

    # show the widget as a window
    widget.setWindowTitle(task.name)
    widget.show()
    mainapp.exec()

