import os, logging
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.patches as patches
from PyQt5 import QtCore
from ._Threading import Threading

class FrameViewClass(FigureCanvas):
    '''
    
    '''
    #Signals
    #fv_sig_frameChange = QtCore.pyqtSignal(str)
    
    def __init__(self, iniPar, parent=None):
        #FigureCanvas.__init__(self, self.fig)
        self.fig = Figure()
        super(self.__class__, self).__init__(self.fig)
        self.log = logging.getLogger('HuberControl.' + __name__)
        self.log.info('Called')
        #FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        #FigureCanvas.updateGeometry(self)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_visible(False)#no white background
        self.axes.set_axis_off()#no axis
        self.fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)#no margins
        
        self.iniPar = iniPar
        self.display_poi = True
        
        # matplotlib imshow toolbar
        self.toolbar = NavigationToolbar(self, parent=None)
        self.toolbar.hide()#pan/zoom/home functions are used
        
        # show an empty placeholder frame (np.array)
        self.frameInit()

    def frameInit(self):
        self.log.debug('Called')
        # add colorbar?
        ##self.fig.colorbar(self.imframeDraw)
        # adjust the limits
        self.intMin = self.iniPar['fv_int_min']
        self.intMax = self.iniPar['fv_int_max']
        self.cmap = self.iniPar['fv_colormap']
        self.frameName = 'test_00_0000.raw'
        self.frameIndex = 0
        self.framePath = ''
        self.framePathList = []
        self.frameNameList = []
        self.frame_data = np.ndarray(shape=(1024, 768), dtype=np.int32)
        self.frame_data.fill(self.iniPar['fv_int_def'])
        self.imframeDraw = self.axes.imshow(self.frame_data, interpolation='none')
        self.imframeDraw.set_cmap(self.cmap)
        self.imframeDraw.set_clim(vmin=self.intMin, vmax=self.intMax)
        self.draw()
    
    def frameRedraw(self, cmap=None, vmin=None, vmax=None):
        self.log.debug('Called')
        if cmap:
            self.cmap = cmap
            self.imframeDraw.set_cmap(self.cmap)
        if vmin:
            self.intMin = vmin
            self.imframeDraw.set_clim(vmin=self.intMin)
        if vmax:
            self.intMax = vmax
            self.imframeDraw.set_clim(vmax=self.intMax)
        if any([cmap, vmin, vmax]):
            self.draw()
    
    def frameUpdate(self, aPathToFrame):
        self.log.debug('Called')
        if aPathToFrame is None:
            return False
        elif aPathToFrame and os.access(aPathToFrame, os.R_OK):
            try:
                # open the file
                f = open(aPathToFrame, 'rb')
                # translate the bytecode to the bytes per pixel
                bpp = len(np.array(0, np.int32).tostring())
                # determine the image size
                size = 1024 * 768 * bpp
                # read the image (bytestream)
                rawData = f.read(size)
                # File not completely transferred
                if len(rawData) < size:
                    self.log.debug('frameUpdate: Frame incomplete {}!'.format(os.path.split(aPathToFrame)[1]))
                    return False
                # reshape the image into 2d array (dim1, dim2)
                # dtype = bytecode
                data = np.fromstring(rawData, np.int32).reshape((1024, 768))
                self.frame_data = data
                #self.frame_data = read_raw_frame(aPathToFrame, 1024, 768, np.int32)
                self.imframeDraw.set_data(self.frame_data)
            # These are the errors that i'd like to track
            except PermissionError:
                self.log.error('frameUpdate: Error accessing {}!'.format(os.path.split(aPathToFrame)[1]))
                return False
            except FileNotFoundError:
                self.log.error('frameUpdate: Error {} not found!'.format(os.path.split(aPathToFrame)[1]))
                return False
            except ValueError:
                self.log.error('frameUpdate: Error reading {}!'.format(os.path.split(aPathToFrame)[1]))
                raise
                return False
        else:
            # File not yet transferred
            self.log.debug('frameUpdate: Error in {}!'.format(os.path.split(aPathToFrame)[1]))
            return False

        self.imframeDraw.set_cmap(self.cmap)
        self.imframeDraw.set_clim(vmin=self.intMin, vmax=self.intMax)
        return True
    
    def remove_poi(self, draw=False):
        self.log.debug('Called')
        # delete all patches and texts
        # using .remove() doesn't work!
        # no idea why, guess threading
        # is the problem -> lock?
        self.axes.patches = []
        self.axes.texts = []
        # redraw?
        if draw:
            self.draw()
    
    def draw_poi(self, det_bc, det_dist, det_tth, color='springgreen', size=7, max_pks=5, min_dist=75, thresh_res=1.0, thresh_int=800.0):
        self.log.debug('Called')
        
        if det_dist == None or det_tth == None:
            self.log.error('det_bc: {}, det_dist: {}, det_tth: {}'.format(det_bc, det_dist, det_tth))
            return False
        
        if not self.display_poi:
            # delete all patches and texts
            self.remove_poi(draw=True)
            return False
        
        # delete all patches and texts
        self.remove_poi(draw=False)
        # detector distance is positive
        # face to grid/phosphor distance: 0.01004 m
        det_dist = abs(det_dist) / 1000.0 + 0.01004
        # tth in radians
        det_tth = np.radians(det_tth)
        [self.axes.add_patch(patches.Circle(xy[::-1], 2, linewidth=0, edgecolor='steelblue', facecolor='steelblue'))for xy in np.argwhere(self.frame_data == self.frame_data.min())]
        # find max
        if self.frame_data.max() > thresh_int:
            #cond = self.frame_data >= self.frame_data.max()/5
            # where is the data larger than threshhold
            cond = self.frame_data >= thresh_int
            # combine x y intensity in new array
            max_loc = np.hstack([np.argwhere(cond), np.atleast_2d(self.frame_data[cond]).T])
            # sort array by intensity
            #  - weak  : np.argsort( max_loc[:,2])
            #  - strong: np.argsort(-max_loc[:,2])
            # we want to find the *strongest* part of a spot!
            xys = np.fliplr(max_loc[np.argsort(-max_loc[:,2]),:2])
            # store coordinates of already marked
            # spots to prevent overlap
            marked_xy = np.array([[0,0]])
            for idx,xy in enumerate(xys):
                # calculate distance to already marked spots
                d = np.linalg.norm(marked_xy - xy, axis=1)
                # skip coordinate if circles get too close
                if (d < min_dist).any():
                    continue
                # intensity and 2-theta
                tth = self.get_tth_from_xy(xy, det_bc, det_dist, det_tth)
                # calculate d-spacing
                dsp = np.round((0.56086)/(2*(np.sin(np.radians(tth/2)))), 2)
                # do not draw if the resolution (d-spacing) is too low
                if dsp >= thresh_res:
                    continue
                # draw circle around max xy
                self.axes.add_patch(patches.Circle(xy, size, linewidth=1, edgecolor=color, facecolor='none', label=idx))
                # add intensity and resolution text
                x,y = xy
                self.axes.text(x, y-size, '{}\n{}Å'.format(self.frame_data[y,x], dsp),
                                            ha='center', va='bottom', color=color, size=size,
                                            family='monospace', weight='bold', label=idx)
                # append xy to marked spots
                marked_xy = np.vstack([marked_xy,xy])
                # break if we painted enough
                if len(marked_xy) >= max_pks:
                    break
        # beamcenter
        rbc = self.get_bc_pos(det_bc, det_dist, det_tth)
        self.axes.add_patch(patches.Circle(rbc, 2, linewidth=1, edgecolor=color, fc=color, label='bc'))
        # draw the patches
        self.draw()
        return True
    
    def rot_010(self, a):
        self.log.debug('Called')
        # return rotation matrix
        # - rotate around y
        # - counter-clockwise
        ca = np.cos(a)
        sa = np.sin(a)
        return np.array([[ ca, 0,-sa],
                        [  0, 1,  0],
                        [ sa, 0, ca]])
    
    def get_bc_pos(self, det_bc, det_dist, det_tth, det_pxs=135E-6):
        self.log.debug('Called')
        kd = np.matmul(np.array([0, 0, det_dist]), self.rot_010(det_tth))
        kd = kd / np.linalg.norm(kd)
        px = (np.sign(kd[0]) * det_dist * np.tan(np.arccos(kd[-1] / np.linalg.norm(kd[[0,2]])))) / det_pxs + det_bc[0]
        py = (np.sign(kd[1]) * det_dist * np.tan(np.arccos(kd[-1] / np.linalg.norm(kd[[1,2]])))) / det_pxs + det_bc[1]
        return np.array([px,py])
    
    def get_tth_from_xy(self, xy, det_bc, det_dist, det_tth, det_pxs=135E-6):
        self.log.debug('Called')
        '''
         det_bc  : beamcenter [array, xy]
         det_dist: distance [m]
         det_tth : 2-Theta [degrees]
         det_pxs : pixelsize [m]
        '''
        ki = np.matmul(np.array([0.0, 0.0, 1.0]), self.rot_010(det_tth))
        kd = np.hstack([(xy - det_bc) * det_pxs, det_dist])
        kd = kd / np.linalg.norm(kd)
        tth = np.arccos(np.sum(kd*ki) / (np.linalg.norm(kd)*np.linalg.norm(ki)))
        return np.round(np.degrees(tth), 2)
    
    def frameToolHome(self):
        self.log.debug('Called')
        self.toolbar.home()
        
    def frameToolZoom(self):
        self.log.debug('Called')
        self.toolbar.zoom()
        
    def frameToolPan(self):
        self.log.debug('Called')
        self.toolbar.pan()
