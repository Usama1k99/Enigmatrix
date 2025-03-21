from PyQt6.QtCore import QRunnable, pyqtSignal, QObject

class WorkerSignals(QObject):
    """Defines signals available from a running worker thread."""
    update_terminal = pyqtSignal([str],[str,bool])
    command_started = pyqtSignal()
    command_finished = pyqtSignal()
    confirmed = pyqtSignal(bool)
    msg_box = pyqtSignal(str,str)
    start_pb = pyqtSignal()
    stop_pb = pyqtSignal()
    time1 = pyqtSignal()
    time2 = pyqtSignal()
    load_rsa = pyqtSignal(bool,bool)
    nblock_update = pyqtSignal(int,int)
    p_time = pyqtSignal()
    terminal_progress = pyqtSignal(int,int)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()

class ParallelWorker(QRunnable):
    """General-purpose worker for running any function in a background thread."""
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """Execute the worker function, handling command execution state via signals."""
        self.signals.command_started.emit()
        try:
            self.function(self.signals, *self.args, **self.kwargs)
        finally:
            self.signals.command_finished.emit()
            self.signals.update_terminal.emit("\n>>> ")
