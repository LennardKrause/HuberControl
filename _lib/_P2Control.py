import os, logging, socket
from PyQt5 import QtCore

########################
##PhotonII - Interface##
##  Setup the Server  ##
########################
class P2_Connection(QtCore.QThread):
    '''
     
    '''
    # SIGNALS
    # general
    p2sigDisconnected = QtCore.pyqtSignal(str)
    # receive a message
    p2sigMessage = QtCore.pyqtSignal(str)
    # Image saved
    p2sigImageReady = QtCore.pyqtSignal(str)
    # ALWAYS emitted after ANY response of p2
    # use as synchronisation signal
    p2sigMsgReceived = QtCore.pyqtSignal()
    # data collection
    p2sigTriggerReady = QtCore.pyqtSignal()
    p2sigAcquisitionDone = QtCore.pyqtSignal()
    # Error: the framegrabber signaled missed frames
    p2sigError = QtCore.pyqtSignal()
    # p2Server died
    p2sigImDead = QtCore.pyqtSignal()
    
    def __init__(self, p2Socket, parent = None):
        QtCore.QThread.__init__(self)
        self.log = logging.getLogger('HuberControl.' + __name__)
        self.log.debug('Called')
        self.p2Socket = p2Socket
        self.bufferSize = 1024
        
    def run(self):
        self.log.debug('Called')
        while True:
            try:
                msgRecv = self.p2Socket.recv(self.bufferSize).decode()
                if len(msgRecv) > 0:
                    if msgRecv == 'p2signal_msgReceived':
                        self.p2sigMsgReceived.emit()
                    elif msgRecv.split()[0] == 'p2signal_ImageReady':
                        self.p2sigImageReady.emit(os.path.normpath(msgRecv.split()[1]))
                    elif msgRecv == 'p2signal_error':
                        self.p2sigError.emit()
                    elif msgRecv == 'p2signal_TriggerReady':
                        self.p2sigTriggerReady.emit()
                    elif msgRecv == 'p2signal_AcquisitionDone':
                        self.p2sigAcquisitionDone.emit()
                    elif msgRecv == 'p2signal_Close':
                        self.p2sigDisconnected.emit(msgRecv)
                        break
                    elif msgRecv:
                        self.p2sigMessage.emit(msgRecv)
                    else:
                        self.log.debug('ERROR: no Idea!')
                        break
                else:
                    self.log.debug('ERROR: server dead?')
                    self.p2sigDisconnected.emit(msgRecv)
                    break
            except socket.timeout:
                self.log.debug('ERROR: run stopped, timeout!')
                break