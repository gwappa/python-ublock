from ublock.model   import Task, StatusPlot, ArrayPlot
from ublock.app     import fromTask, mainapp

if __name__ == "__main__":
    task = Task("Sample")
    task.addMode('Pair', 'P')
    task.addMode('Test', 'T')

    task.addConfig('stim_dur_ms', 'd', label='Stimulus duration (ms)')
    task.addConfig('resp_dur_ms', 'f', label='Response window with (ms)')
    task.addAction('runTask', 'X', label="Run task")
    task.addAction('clearIndex', 'C', label='Reset trial index', repeats=False)
    task.addFeatures('note', 'raw', 'echo')
    task.setResult(status=('hit', 'miss', 'catch', 'reject', 'noresp'),
                   values=('wait',),
                   arrays=('lick',))
    task.addView('stats', summarized=('hit', 'miss', 'catch', 'reject', 'noresp'),
                          rewarded=('hit',))
    status = StatusPlot({'hit':'b', 'miss': 'k', 
                         'catch': 'r', 'reject': 'w',
                         'noresp': 'w'})
    events = ArrayPlot({'lick': 'k'}) 
    task.addView('session', items=[status, events], xwidth=5000)
    task.addLogger("samplesession")

    widget = fromTask(task, 'uno')
    widget.setWindowTitle(task.name)
    widget.show()
    mainapp.exec()

