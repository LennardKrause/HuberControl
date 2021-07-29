import logging
from PyQt5 import QtCore

class Threading(QtCore.QRunnable):
    class Signals(QtCore.QObject):
        '''
         Custom signals can only be defined on objects derived from QObject
        '''
        finished = QtCore.pyqtSignal(bool)

    def __init__(self, fn_funct, fn_args, fn_kwargs):
        '''
         fn_funct:  Conversion function
         fn_args:   Arguments to pass to the function
         fn_kwargs: Keywords to pass to the function
        '''
        QtCore.QRunnable.__init__(self)
        self.log = logging.getLogger('HuberControl.' + __name__)
        self.log.debug('Called')
        self.funct = fn_funct
        self.args = fn_args
        self.kwargs = fn_kwargs
        self.signals = self.__class__.Signals()
    
    def run(self):
        self.log.debug('Called')
        # funct: returns True/False
        self.signals.finished.emit(self.funct(*self.args, **self.kwargs))