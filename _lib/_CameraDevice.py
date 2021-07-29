import logging, cv2
import numpy as np
from PyQt5 import QtCore, QtGui

class cameraDevice(QtCore.QThread):
    #Signals
    frameReady = QtCore.pyqtSignal(QtGui.QImage)

    def __init__(self, device_id=0):
        QtCore.QThread.__init__(self)
        self.log = logging.getLogger('HuberControl.' + __name__)
        self.log.debug('Called')
        '''
        '''
        self.im_width = 1536#3072
        self.im_height = 2048
        self.capture = cv2.VideoCapture(device_id + cv2.CAP_DSHOW)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.im_width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.im_height)
        self.capture.set(cv2.CAP_PROP_FPS, 30)
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        
        if not self.capture.isOpened():
            raise ValueError('Device not found')

        self.timer.timeout.connect(self.readFrame)
        self.timer.setInterval(1000/60)
        #self.timer.start()

    def disconnect(self):
        self.log.debug('Called')
        self.timer.stop()
        self.capture.release()
        #self.terminate()
        #self.wait()

    @property
    def fps(self):
        self.log.debug('Called')
        '''
         Frames per second
        '''
        return int(self.capture.get(cv2.CAP_PROP_FPS))

    @property
    def size(self):
        self.log.debug('Called')
        '''
         Returns the size of the video frames: (width, height)
        '''
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.log.debug('size: {} {}'.format(width, height))
        return (width, height)

    def readFrame(self):
        #self.log.debug('Called')
        '''
         Read frame into QImage and emit it
        '''
        success, frame = self.capture.read()
        
        if success:
            cv2.line(frame, (self.im_width // 2, 0), (self.im_width // 2, self.im_height),(255, 255, 0), 6)
            cv2.line(frame, (0, self.im_height // 2),(self.im_width, self.im_height // 2),(255, 255, 0), 6)
            cv2.circle(img=frame, center=(self.im_width // 2, self.im_height // 2), radius=200, color=(255, 255, 0), thickness=6)
            #frame = cv2.resize(frame, None, fx=0.5, fy=0.5)
            img = self._convert_array_to_qimage(frame)
            self.frameReady.emit(img)
        else:
            self.log.error('Failed to read frame')
            #self.frameReady.emit(self._convert_array_to_qimage(np.zeros((self.im_width, self.im_height, 0))))
            self.timer.stop()
            #raise ValueError('Failed to read frame')

    def _convert_array_to_qimage(self, a):
        #self.log.debug('Called')
        '''
        '''
        height, width, channels = a.shape
        bytes_per_line = channels * width
        #cv2.cvtColor(a, cv2.COLOR_BGR2RGB, a)
        return QtGui.QImage(a.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
