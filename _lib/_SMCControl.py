from PyQt5 import QtCore
import numpy as np
import logging, socket

class SMC_Connection(QtCore.QThread):
    # Signal to disable GUI input and enable red STOP button
    signal_IAmBusy = QtCore.pyqtSignal()
    # Signal to enable GUI buttons
    signal_IAmReady = QtCore.pyqtSignal()
    # Position established
    signal_IAmInPos = QtCore.pyqtSignal()
    # Home position established
    signal_IAmHome = QtCore.pyqtSignal()
    # Data collection finished
    # Set flag_data to True
    signal_IAmData = QtCore.pyqtSignal()
    # Special signal, use as wildcard
    # Set flag_special to True
    signal_IAmSpecial = QtCore.pyqtSignal()
    # Negative limit switch active
    signal_ELNegative = QtCore.pyqtSignal()
    # Positive limit switch active
    signal_ELPositive = QtCore.pyqtSignal()
    # Parsing error reading the SMC message
    signal_SMCError = QtCore.pyqtSignal()
    # Update the GUI with new positions
    signal_SMCUpdate = QtCore.pyqtSignal(dict, dict)
    
    def __init__(self, parent, ADDRESS_SMC, PORT_SMC):
        QtCore.QThread.__init__(self, parent)
        self.log = logging.getLogger('HuberControl.' + __name__)
        self.log.debug('Called')
        self.log.debug(ADDRESS_SMC)
        self.log.debug(PORT_SMC)
        # set flags
        self.flag_special = False
        self.flag_data = False
        self.note_ELPos = False
        self.note_ELNeg = False
        self.note_Home = False
        self.axisToHome = None
        # setup the connection
        self.SMC_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.SMC_socket.settimeout(1)
        self.SMC_socket.connect((ADDRESS_SMC, PORT_SMC))
        self.log.info('Connected: {}'.format(self.SMC_socket.recv(1024).decode('ascii').strip()))
    
    def send_to_SMC(self, command, receive=False, buffer=1024):
        #self.log.debug(command)
        '''
        Write to SMC
        '''
        self.SMC_socket.send('{}\r\n'.format(command).encode())
        if receive:
            return self.SMC_socket.recv(buffer)
    
    def to_dict(self, s, tk=int, tv=float, s1=';', s2=':') -> dict:
        d = {}
        for i in s.split(s1):
            k,v = i.split(s2)
            d[tk(k)] = tv(v)
        return d
    
    def uat_readAxsSMC(self, command:str, datatype=float):
        #self.log.debug('> uat_readAxsSMC: {}'.format(axsCurPos))
        try:
            # clear the buffer
            _ = self.send_to_SMC('?ccb', receive=True)
            # query of the current status
            # format: <axis>:<state>;<axis>:<state>; ...
            msg = self.send_to_SMC(command, receive=True).decode('ascii').strip(';\r\n')
            # ?s: axsStatus: dictionary containing axis:state as int:int
            # {1: 145, 2: 129, 3: 129, 4: 129, 5: 32913, 6: 129, 7: 129, 8: 129}
            # ?p: axsPositions: dictionary containing axis:position as int:float
            # {1: 0.0, 2: 0.0, 3: 0.0, 4: 20.0, 5: -176.0, 6: 0.0, 7: 0.0, 8: 0.0}
            status = self.to_dict(msg, tv=datatype)
            # returns wrong format (24 instead of 8 entries) after homing has finished!
            if len(status.keys()) == 8:
                return status
            else:
                self.log.warning('else: {} {} {}'.format(msg,command,datatype))
                self.signal_SMCError.emit()
                return False
        except ValueError:
            self.log.debug('ValueError: {} {} {}'.format(msg,command,datatype))
            return False
        except socket.timeout:
            self.log.debug('timeout: {} {}'.format(command,datatype))
            return False
        except:
            self.log.warning('other: {} {} {}'.format(msg,command,datatype))
            self.signal_SMCError.emit()
            return False
    
    def uat_stopped(self, status:dict) -> bool:
        '''
         status: dictionary containing axis:state as int:int
          {1: 145, 2: 129, 3: 129, 4: 129, 5: 32913, 6: 129, 7: 129, 8: 129}
         query return value (+:used, -:unused):
          +  bit0:    1 axis ready
          +  bit1:    2 reference position installed
          +  bit2:    4 end/limit switch EL- active
          +  bit3:    8 end/limit switch EL+ active
          -  bit4:   16 reserved
          -  bit5:   32 reserved
          -  bit6:   64 program execution in progress
          +  bit7:  128 controller ready (all axis idle!)
          +  bit8:  256 oscillation in progress
          -  bit9:  512 oscillation positioning error
          - bit10: 1024 encoder reference installed
          
         Axes names: 1:'Phi', 2:'Chi', 3:'Omega', 4:'2-Theta',
                     5:'Distance',6:'X', 7:'Y', 8:'Z'
        '''
        # check if any axis shows end/limit switch EL- active
        status_values_array = np.asarray(list(status.values()))
        if bool(any(status_values_array & 4)) is True:
            self.note_ELNeg = True
        # check if any axis shows end/limit switch EL+ active
        if bool(any(status_values_array & 8)) is True:
            self.note_ELPos = True
        # Homing protocols
        if self.axisToHome is not None:
            # DXT Homing: Axis number 5
            # move until negative limit switch is inactive and stop!
            # this is the new 'home' position
            if self.axisToHome == 5 and bool(status[self.axisToHome] & 4) is False:
                self.axisToHome = None
                self.send_to_SMC('stop')
                pass
            # check if axisToHome has its reference position installed
            if self.axisToHome in [1,2,3,4] and bool(status[self.axisToHome] & 2) is True:
                self.axisToHome = None
                self.note_Home = True
                pass
        # all axis have stopped if an axis has bit7 set
        if bool(any(status_values_array & 128)) is True:
            return True
        # not all axes are idle
        return False
        
    def run(self):
        self.log.debug('Called')
        '''
         
        '''
        # tell the GUI that we're rolling
        self.signal_IAmBusy.emit()
        # - constantly send queries to the Goniometer and ask
        #   about the axes status and updated positions
        # - break if all axes are idle
        while True:
            axsStatus = self.uat_readAxsSMC('?s', int)
            axsPositions = self.uat_readAxsSMC('?p', float)
            # uat_readAxsSMC returns either a dict or False
            # if both are not False we can continue ...
            if axsPositions and axsStatus:
                # ... and emit the new axes status/
                # positions to the main GUI
                self.signal_SMCUpdate.emit(axsPositions, axsStatus)
                # if uat_stopped is True the Goniometer is idle
                if self.uat_stopped(axsStatus) is True:
                    # emit signal that the negative
                    # end/limit switch (EL-) is active
                    if self.note_ELNeg is True:
                        self.note_ELNeg = False
                        self.signal_ELNegative.emit()
                    # emit signal that the positive
                    # end/limit switch (EL+) is active
                    if self.note_ELPos is True:
                        self.note_ELPos = False
                        self.signal_ELPositive.emit()
                    # emit signal that the reference position installed
                    if self.note_Home is True:
                        self.note_Home = False
                        self.axisToHome = None
                        self.signal_IAmHome.emit()
                    # if a special was issued emit the signal
                    if self.flag_special is True:
                        self.flag_special = False
                        self.signal_IAmSpecial.emit()
                    # if data collection was issued emit the signal
                    if self.flag_data is True:
                        self.flag_data = False
                        self.signal_IAmData.emit()
                    # emit ready signal
                    if self.axisToHome == None:
                        self.signal_IAmReady.emit()
                        self.signal_IAmInPos.emit()
                        break
            # wait a little
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(25, loop.quit)
            loop.exec_()
