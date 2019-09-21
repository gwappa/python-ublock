import ublock
from ublock.app import fromTask, getApp

if __name__ == "__main__":
    # a task model that works as a recipe for building a UI widget
    # (this is turned into a QWidget later, using ublock.app.fromTask())
    #
    # 'controls'   -- adds 'clear plots' & 'quit' buttons at the bottom
    # 'note'       -- adds running-note editor UI (you can write comments into the log files)
    # 'rawcommand' -- adds raw-command dispatcher UI
    # 'echoed'     -- responses from the serial 'echos' out in the standard output
    task = ublock.Task("Sample", controls=True, note=True,
                        rawcommand=True, echoed=True)

    # add logger UI
    task.add(ublock.Logger("samplesession"))

    # add task modes
    task.add(ublock.Mode('Pair', 'P'))\
        .add(ublock.Mode('Test', 'T'))

    # add config parameters
    task.add(ublock.Config('stim_dur_ms', 'd', label='Stimulus duration (ms)'))\
        .add(ublock.Config('resp_dur_ms', 'f', label='Response window with (ms)'))

    # add result parameters
    task.add(ublock.Results(status=('hit', 'miss', 'catch', 'reject', 'noresp'),
                   values=('wait',),
                   arrays=('lick',),
                   plotted=dict(wait=dict(), lick=dict()),
                   counted=('hit', 'reject'),
                   rewarded=('hit',)))

    # add 'repeatable' actions
    task.add(ublock.Action('runTask', 'X', label="Run task"))\
        .add(ublock.Action('querySettings', '?',
                    label='Current settings', repeats=False,
                    returns='config'))\
        .add(ublock.Action('clearIndex', 'C',
                    label='Reset trial index', repeats=False))

    # add result views: this feature has not been implemented
    # task.addView('stats', summarized=('hit', 'miss', 'catch', 'reject', 'noresp'),
    #                       rewarded=('hit',))
    # status = StatusPlot({'hit':'b', 'miss': 'k',
    #                      'catch': 'r', 'reject': 'efefef',
    #                      'noresp': 'efefef'}, markersize=8)
    # events = ArrayPlot({'lick': '8888'}, markersize=6)
    # task.addView('session', items=[status, events], xwidth=5000)


    # build the UI widget from the task model
    widget = fromTask(task, 'uno')

    # show the widget as a window
    widget.setWindowTitle(task.name)
    widget.show()
    getApp().exec()
