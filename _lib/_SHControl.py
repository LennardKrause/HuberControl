from PyQt5 import QtCore
import numpy as np
import logging, serial

'''
 https://www.pjrc.com/teensy/td_download.html
'''

class SH_Connection(QtCore.QThread):
    signal_shc_connection = QtCore.pyqtSignal(int)
    signal_shc_shutter = QtCore.pyqtSignal(int)
    
    def __init__(self, parent, PORT_SH):
        QtCore.QThread.__init__(self, parent)
        self.log = logging.getLogger('HuberControl.' + __name__)
        #self.log.setLevel(logging.DEBUG)
        self.log.debug('Called')
        self.log.debug(PORT_SH)
        
        # read buffer size
        self.buffer = 128
        
        # init and setup
        self.connection = serial.Serial()
        self.connection.baudrate = 115200
        self.connection.port = PORT_SH
        self.connection.timeout = 0.1
        #self.connection.bytesize = serial.EIGHTBITS
        #self.connection.parity = serial.PARITY_NONE
        #self.connection.stopbits = serial.STOPBITS_ONE
        #self.connection.rtscts = 1
        #self.connection.dsrdtr = 1
        #self.connection.xonxoff = 1
        #self.connection.exclusive = True
    
    def run(self):
        self.log.debug('Called')
        self.connection.open()
        self.signal_shc_connection.emit(1)
    
    def shutter_open(self):
        self.log.debug('Called')
        self.connection.write(b'>shutter 1\r\n')
        self.connection.flush()
        self.connection.read(self.buffer)
        self.signal_shc_shutter.emit(1)
    
    def shutter_close(self):
        self.log.debug('Called')
        self.connection.write(b'>shutter 0\r\n')
        self.connection.flush()
        self.connection.read(self.buffer)
        self.signal_shc_shutter.emit(0)
        
    def shutter_status(self):
        self.log.debug('Called')
        self.connection.write(b'?shutter\r\n')
        self.connection.flush()
        msg = int(self.connection.read(self.buffer).decode().strip('<'))
        self.signal_shc_shutter.emit(msg)
    
    def disconnect(self):
        self.log.debug('Called')
        self.shutter_close()
        self.connection.close()
        self.terminate()
        self.wait()
        self.signal_shc_connection.emit(0)