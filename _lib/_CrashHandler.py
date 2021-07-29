import sys, time, os, traceback
from PyQt5.QtCore import QProcess

'''
Taken from:
https://stackoverflow.com/questions/49386039/how-to-invoke-method-on-gui-thread-but-without-have-that-method-in-qmainwindow-c
'''

class CrashEngine:
    @staticmethod
    def register(name, version):
        CrashEngine.name = name
        CrashEngine.version = version
        sys.excepthook = CrashEngine._logCrash

    @staticmethod
    def _logCrash(exc_type, exc_value, exc_traceback):
        crash = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(crash)
        with open('crash.log', 'a+') as f:
            f.write(time.ctime() + '\n')
            f.write('Software name: ' + CrashEngine.name + '\n')
            f.write('Software version: ' + CrashEngine.version + '\n')
            f.write('\n')
            f.write(crash)
            f.write('\n')
        CrashEngine._showDialog()

    @staticmethod
    def _showDialog():
        path = sys.executable
        arg = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_CrashHandlerPop.py')
        QProcess.startDetached(path, [arg])
        sys.exit(1)
