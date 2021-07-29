import os, sys, socket, glob, multiprocessing, collections, logging, serial
import numpy as np
from datetime import datetime
from copy import copy, deepcopy
from PyQt5 import QtCore, QtGui, QtWidgets, uic

from _lib._SMCControl import SMC_Connection
from _lib._P2Control import P2_Connection
from _lib._SHControl import SH_Connection
from _lib._Browser import Browser
from _lib._CameraDevice import cameraDevice
from _lib._IniHandler import save_ini, read_ini
from _lib._FrameView import FrameViewClass
from _lib._CrashHandler import CrashEngine
from _lib._Threading import Threading
from _lib._ConvertUtility import convert_frame

##-----align-----align-----align-----align-----align-----align-----align-----align-----##
# 2021-02-11: 3px right 1px down, distance -80.0 to -176.0.
##-----align-----align-----align-----align-----align-----align-----align-----align-----##


##-----todo-----todo-----todo-----todo-----todo-----todo-----todo-----todo-----##
# needed for _MainWindow.ui icons import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '_lib'))
# - make stop calls synchronized and wait for response!
# - make the exit call synchronized and wait for response!
# - CRASH: SystemError: <built-in method exec_ of QApplication object at
#          0x000000000C037438> returned a result with an error set
# - see lab notes!
# - LINK THE INPUT
#   self.btn_cmp_chi_1.clicked.connect(lambda: self.smc_control_goto(2, float(self.inp_chi.value()) - 20.0))
#   self.btn_cmp_phi_0.setText('Phi\n{:}'.format(float(self.inp_phi.text())))
# - unify the way connections are handled (P2Control, SHControl, SMCControl)
##-----todo-----todo-----todo-----todo-----todo-----todo-----todo-----todo-----##

########################
##    Main Window     ##
########################
class mainWindow(QtWidgets.QMainWindow, uic.loadUiType(os.path.join(os.path.dirname(__file__), '_lib/_MainWindow.ui'))[0]):
    def __init__(self):
        super(mainWindow, self).__init__()
        self.version = 'v2021-02-08'
        self.name = 'HuberControl'
        
        logging.basicConfig(format='{levelname:7} {module:>14}.{funcName:<22}: {message}', style='{')
        self.log = logging.getLogger('HuberControl')
        self.log.info(self.version)
        
        #----------------------#
        # Read ini Parameters  #
        #----------------------#
        self.iniPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instrument.ini')
        self.gui_ini_reload(self.iniPath, update_gui=False)
        
        #---------------#
        # Init Logging  #
        #---------------#
        # warning(), error() and critical()
        if self.iniPar['use_debugging_mode']:
            self.log.setLevel(logging.DEBUG)
            
        else:
            self.log.setLevel(logging.INFO)
        
        #----------#
        # Init UI  #
        #----------#
        self.setupUi(self)
        
        #----------------------#
        #    Crash Control     #
        #----------------------#
        if self.iniPar['use_crash_engine'] == True:
            CrashEngine.register(self.name, self.version)
        
        #-------------------------#
        #  GUI - GENERAL BUTTONS  #
        #-------------------------#
        # enabled/disabled with signal_IAmReady/signal_IAmBusy
        self.generalButtons = [self.btn_cmp_chi_0,
                               self.btn_cmp_chi_1,
                               self.btn_cmp_chi_2,
                               self.btn_cmp_chi_3,
                               self.btn_cmp_phi_0,
                               self.btn_cmp_phi_1,
                               self.btn_cmp_phi_2,
                               self.btn_cmp_phi_3,
                               self.btn_cmp_phi_inc,
                               self.send_btn,
                               self.cbx_SMCsendText,
                               self.btn_home_axis,
                               self.btn_home_dxt,
                               self.btn_sax_stp_bck,
                               self.btn_sax_run_bck,
                               self.btn_sax_run_stp,
                               self.btn_sax_run_fwd,
                               self.btn_sax_stp_fwd,
                               self.btn_sax_con_bck,
                               self.btn_sax_con_fwd,
                               self.btn_sax_got,
                               self.inp_sax_got,
                               self.btn_xyz_right,
                               self.btn_xyz_left_1,
                               self.btn_xyz_left_2,
                               self.btn_cnt_chi_1,
                               self.btn_cnt_chi_2,
                               self.btn_cnt_chi_3,
                               self.btn_cnt_chi_4,
                               self.btn_cnt_phi_1,
                               self.btn_cnt_phi_2,
                               self.btn_cnt_phi_3,
                               self.btn_cnt_phi_4,
                               self.btn_cnt_inc_1,
                               ]
        
        #----------------------#
        #  GUI - STOP BUTTONS  #
        #----------------------#
        # Add generic STOP buttons here!
        # disabled/enabled with signal_IAmReady/signal_IAmBusy
        self.stop_buttons = [self.btn_stop_01, 
                             self.btn_stop_02,
                             self.btn_stop_03,
                             self.btn_stop_04,
                             self.btn_stop_05,
                             #self.btn_stop_06,# CURRENTLY UNUSED, WAS USED IN CRYO TAB
                             self.btn_stop_07,
                             self.btn_stop_08,
                             ]
        for stp in self.stop_buttons:
            stp.clicked.connect(self.gen_stop)
        
        #-----------------------#
        # GUI - Data Collection #
        #-----------------------#
        # disabled/enabled with dc_setup_pre/dc_setup_post
        self.dc_buttons = [self.action_SMC_disconnect,
                           self.action_SMC_idle,
                           self.action_SMC_home,
                           self.action_P2_disconnect,
                           self.action_P2_stop,
                           self.action_P2_collect_darks,
                           self.action_gui_change_user,
                           self.action_gui_change_project,
                           self.action_gui_change_folder,
                           self.action_dc_save_current,
                           self.tbl_scn_mat,
                           ]
        
        #--------------------------------#
        # Axes Numbers, Names and Limits #
        #--------------------------------#
        self.init_axes()
        #----------------------#
        #      Frame View      #
        #----------------------#
        self.init_frameview()
        #----------------------#
        # GUI - CENTRING PANEL #
        #----------------------#
        self.init_dc_centring()
        #----------------------#
        #  GUI - HOMING PANEL  #
        #----------------------#
        self.init_homing_panel()
        #----------------------#
        #   GUI - SINGLE AXIS  #
        #----------------------#
        self.init_single_axis()
        #-----------------------#
        # GUI - SIMPLE PHI SCAN #
        #-----------------------#
        self.init_simple_scan()
        #----------------------#
        #    GUI - XYZ-Stage   #
        #----------------------#
        self.init_xyzStage()
        #---------------#
        # GUI - General #
        #---------------#
        self.init_main()
        #----------------------------#
        #  SCAN - default strategies #
        #----------------------------#
        self.init_dc_scan()
        self.init_styles()
        self.init_var_states()
        self.gui_toggle_buttons(False)
        self.init_buttons()
        #----------------------#
        #  CRYO and ALIGN TABS #
        #----------------------#
        self.init_special_tabs()
        
        #----------------------#
        # PhotonII - Interface #
        #----------------------#
        self.btn_p2SendText.clicked.connect(lambda: self.p2_send_cbx(self.cbx_p2sendText))
        self.btn_p2ClearLog.clicked.connect(lambda: self.p2_saveToLogFile())
        
        #--------------------#
        #  FRAME CONVERSION  #
        #--------------------#
        self.progressBarFrameConvert.hide()
        self.btn_scn_con_start.clicked.connect(lambda: self.fc_prepare())
        
        #----------------#
        #  GUI - Camera  #
        #----------------#
        self.tW_camera.currentChanged.connect(self.cam_toggle)
        
        # maximize FrameView on startup
        # setStretchFactor(int index, int stretch)
        self.splitter.setStretchFactor(0,10)
        self.splitter.setStretchFactor(1,1)
        self.splitter_2.setStretchFactor(0,1)
        self.splitter_2.setStretchFactor(1,10)
        
        #----------------------#
        #     GUI - STARTUP    #
        #----------------------#
        # Strategy table section
        self.dc_table_build()
        # ask for current user on startup
        #self.setEnabled(False)
        if self.iniPar['startup_connect']:
            self.smc_connect()
            self.sh_connect()
            self.cam_connect()
            self.p2_connect()
        self.usr_ch_user(None)
        
        ##-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----##
        self.action_emit_01.triggered.connect(lambda: self.sh_disconnect())
        self.action_emit_01.setText('call: sh_disconnect')
        self.action_emit_02.triggered.connect(lambda: self.sh_open())
        self.action_emit_02.setText('call: sh_open')
        self.action_emit_03.triggered.connect(lambda: self.sh_close())
        self.action_emit_03.setText('call: sh_close')
        ##-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----##
    
    #---------------#
    #    Startup    #
    #---------------#
    
    def init_styles(self):
        self.log.debug('Called')
        #----------------------#
        #  GUI - FONT COLOURS  #
        #----------------------#
        self.brushDisabled = QtGui.QBrush(QtGui.QColor(75,75,74))
        self.brushDisabled.setStyle(QtCore.Qt.NoBrush)
        self.brushEnabled = QtGui.QBrush(QtGui.QColor(0,69,67))
        self.brushEnabled.setStyle(QtCore.Qt.NoBrush)
        self.brushError = QtGui.QBrush(QtGui.QColor(91,12,12))
        self.brushError.setStyle(QtCore.Qt.NoBrush)
        
        #---------------------#
        #  GUI - STOP Buttons #
        #---------------------#
        style_btn_cmp_stp = ('QToolButton          {background-color: rgb(226,   0,  26); color: rgb(250, 250, 250); border: 2px solid rgb(200, 200, 200); border-radius: 2px}'
                             'QToolButton:hover    {background-color: rgb(236,   0,  36); color: rgb(250, 250, 250); border: 2px solid rgb(200, 200, 200)}'
                             'QToolButton:pressed  {background-color: rgb( 91,  12,  12); color: rgb(250, 250, 250); border: 2px solid rgb(200, 200, 200)}'
                             'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        for stp in self.stop_buttons:
            stp.setStyleSheet(style_btn_cmp_stp)
        
        #-----------------------#
        #  GUI - SMC Connection #
        #-----------------------#
        self.style_btn_ls_disconnected = ('QToolButton:disabled {background-color: rgb(240, 245, 240); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 5px}')
        self.style_btn_ls_ready        = ('QToolButton:disabled {background-color: rgb(  0, 255,   0); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 5px}')
        self.style_btn_ls_reference    = ('QToolButton:disabled {background-color: rgb(  0, 255, 255); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 5px}')
        self.style_btn_ls_moving       = ('QToolButton:disabled {background-color: rgb(255, 255,   0); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 5px}')
        self.style_btn_ls_error        = ('QToolButton:disabled {background-color: rgb(240,   0,   0); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 5px}')
        self.btn_ls_phi.setStyleSheet(self.style_btn_ls_disconnected)
        self.btn_ls_chi.setStyleSheet(self.style_btn_ls_disconnected)
        self.btn_ls_omg.setStyleSheet(self.style_btn_ls_disconnected)
        self.btn_ls_tth.setStyleSheet(self.style_btn_ls_disconnected)
        self.btn_ls_dxt.setStyleSheet(self.style_btn_ls_disconnected)
        
        #-----------------#
        #  GUI - Start DC #
        #-----------------#
        self.style_btn_start = ('QToolButton          {background-color: rgb(230, 230, 230); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75); border-radius: 20px}'
                                'QToolButton:hover    {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                                'QToolButton:pressed  {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                                'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        self.btn_scn_sim_start.setStyleSheet(self.style_btn_start)
        self.btn_scn_mat_start.setStyleSheet(self.style_btn_start)
        self.btn_scn_con_start.setStyleSheet(self.style_btn_start)
        
        #-------------------#
        #  GUI - P2 Section #
        #-------------------#
        self.style_btn_p2_disconnected = ('QToolButton:disabled {background-color: rgb(240,   0,   0); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 7px}')
        self.style_btn_p2_pending      = ('QToolButton:disabled {background-color: rgb(255, 255,   0); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 7px}')
        self.style_btn_p2_connected    = ('QToolButton:disabled {background-color: rgb(  0, 255,   0); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 7px}')
        # Startup State
        self.btn_p2IsConnected.setStyleSheet(self.style_btn_p2_disconnected)
        style_btn_p2_send = ('QToolButton          {background-color: rgb(240, 240, 240); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 2px}'
                             'QToolButton:hover    {background-color: rgb(255, 255, 255); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}'
                             'QToolButton:pressed  {background-color: rgb(200, 225, 200); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}'
                             'QToolButton:checked  {background-color: rgb(200, 200, 200); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}'
                             'QToolButton:disabled {background-color: rgb(220, 200, 200); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}')
        self.btn_p2SendText.setStyleSheet(style_btn_p2_send)
        self.btn_p2ClearLog.setStyleSheet(style_btn_p2_send)
    
    def init_var_states(self):
        self.log.debug('Called')
        # username and projectname
        self.username = None
        self.userpath = None
        self.projname = None
        self.projpath = None
        self.dataname = None
        self.datapath = None
        self.rawpath = None
        self.p2rawpath = None
        self.rawdir = '_raw'
        self.raw_files = []
        self.display_img = None
        
        # instrument is idle
        self.instrumentIsIdle = True
        # run number being collected
        self.dc_activeRun = None
        
        # xyz stage / cryostat 
        self.inCenteringPosition = False
        
        # try to read file
        self.scn_strat_active = None
        self.scn_strat_custom = None
        self.scn_strat_default = [collections.OrderedDict([('', True), (self.gon_name_from_num[1], 0.0), (self.gon_name_from_num[2], -30.0), (self.gon_name_from_num[3], -30.0), (self.gon_name_from_num[4], -30.0), (self.gon_name_from_num[5], -75.0), ('Exposure', 10.0), ('Width', 0.5), ('Range', 360.0)]),
                                  collections.OrderedDict([('', True), (self.gon_name_from_num[1], 0.0), (self.gon_name_from_num[2], -60.0), (self.gon_name_from_num[3], -30.0), (self.gon_name_from_num[4], -30.0), (self.gon_name_from_num[5], -75.0), ('Exposure', 10.0), ('Width', 0.5), ('Range', 360.0)]),
                                  collections.OrderedDict([('', True), (self.gon_name_from_num[1], 0.0), (self.gon_name_from_num[2], -30.0), (self.gon_name_from_num[3], -15.0), (self.gon_name_from_num[4], -15.0), (self.gon_name_from_num[5], -75.0), ('Exposure', 10.0), ('Width', 0.5), ('Range', 360.0)]),
                                  collections.OrderedDict([('', True), (self.gon_name_from_num[1], 0.0), (self.gon_name_from_num[2], -60.0), (self.gon_name_from_num[3], -15.0), (self.gon_name_from_num[4], -15.0), (self.gon_name_from_num[5], -75.0), ('Exposure', 10.0), ('Width', 0.5), ('Range', 360.0)]),
                                  collections.OrderedDict([('', True), (self.gon_name_from_num[1], 0.0), (self.gon_name_from_num[2],   0.0), (self.gon_name_from_num[3],   0.0), (self.gon_name_from_num[4],   0.0), (self.gon_name_from_num[5], -75.0), ('Exposure', 10.0), ('Width', 0.5), ('Range', 360.0)]),
                                 ]
        
        self.scn_strat_matrix = [collections.OrderedDict([('', True), (self.gon_name_from_num[1],    0.0),
                                                                      (self.gon_name_from_num[2],    0.0),
                                                                      (self.gon_name_from_num[3],    0.0),
                                                                      (self.gon_name_from_num[4],  -10.0),
                                                                      (self.gon_name_from_num[5],  -75.0),
                                                                      ('Exposure', 5.0), ('Width',   0.5), ('Range', 25.0)]),
                                 collections.OrderedDict([('', True), (self.gon_name_from_num[1],   60.0),
                                                                      (self.gon_name_from_num[2],  -30.0),
                                                                      (self.gon_name_from_num[3],    0.0),
                                                                      (self.gon_name_from_num[4],  -10.0),
                                                                      (self.gon_name_from_num[5],  -75.0),
                                                                      ('Exposure', 5.0), ('Width',   0.5), ('Range', 25.0)]),
                                 collections.OrderedDict([('', True), (self.gon_name_from_num[1],  120.0),
                                                                      (self.gon_name_from_num[2],  -60.0),
                                                                      (self.gon_name_from_num[3],    0.0),
                                                                      (self.gon_name_from_num[4],  -10.0),
                                                                      (self.gon_name_from_num[5],  -75.0),
                                                                      ('Exposure', 5.0), ('Width',   0.5), ('Range', 25.0)]),
                                ]
        
        
        self.display_poi = True
        self.display_tth = None
        self.display_dxt = None
        self.display_bc = None
        
        #-----------------------#
        # CAMERA - INITIALIZING #
        #-----------------------#
        # show camera on startup?
        self.cameraIsConnected = False
        self.SMCIsConnected = False
        self.p2IsConnected = False
        self.SHIsConnected = False
        self.SHIsOpen = False
        self.scanParameterValid = {'sca_spn_rot':True,
                                   'sca_spn_row':True,
                                   'sca_spn_scw':True,
                                   'sca_spn_tot':True,
                                   'sca_spn_fin':True,
                                   'sca_spn_fre':True,
                                   'sca_spn_frw':True,
                                   'sca_spn_frn':True}
    
    def init_main(self):
        self.log.debug('Called')
        #---------------#
        # GUI - General #
        #---------------#
        self.action_gui_exit.triggered.connect(self.gen_exit_app)
        # SMC
        self.action_SMC_connect.triggered.connect(self.smc_connect)
        self.action_SMC_disconnect.triggered.connect(self.smc_disconnect)
        self.action_SMC_idle.triggered.connect(self.smc_go_home)
        self.action_SMC_home.triggered.connect(self.smc_find_home)
        # P2
        self.action_P2_connect.triggered.connect(self.p2_connect)
        self.action_P2_disconnect.triggered.connect(self.p2_disconnect)
        # Camera
        self.action_gui_connect_camera.triggered.connect(self.cam_connect)
        self.action_gui_connect_shutter.triggered.connect(self.sh_connect)
        self.action_gui_help.triggered.connect(self.gui_win_about)
        self.action_gui_about.triggered.connect(self.gui_win_about)
        self.action_gui_settings.triggered.connect(self.gui_win_about)
        # Change User/Project
        self.action_gui_change_user.triggered.connect(self.usr_ch_user_win)
        self.action_gui_change_project.triggered.connect(self.usr_ch_proj_win)
        self.action_gui_change_folder.triggered.connect(self.usr_ch_data_win)
        
        self.action_gui_reload_ini.triggered.connect(lambda: self.gui_ini_reload(self.iniPath, update_gui=True))
        self.action_fv_toggle_toolbar.triggered.connect(lambda: self.fv_toolbar_visible())
        self.action_P2_collect_darks.triggered.connect(lambda: self.p2_collectNewDarkFrames())
        self.action_P2_stop.triggered.connect(lambda: self.p2_stop())
        
        self.action_cmap_hot.triggered.connect(lambda: self.fv_update_params(cmap='hot', save=True))
        self.action_cmap_viridis.triggered.connect(lambda: self.fv_update_params(cmap='viridis', save=True))
        self.action_cmap_magma.triggered.connect(lambda: self.fv_update_params(cmap='magma', save=True))
        self.action_cmap_inferno.triggered.connect(lambda: self.fv_update_params(cmap='inferno', save=True))
        
        ##-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----##
        # make this toggle the overlay
        #self.action_fv_draw_poi.triggered.connect(self.fv_draw_POI)
        self.action_fv_draw_poi.triggered.connect(self.fv_toggle_poi)
        ##-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----DEBUG-----##
        
        self.action_dc_save_current.triggered.connect(lambda: self.dc_table_save(self.projpath, '{}_preferred'.format(self.projname), show_popup=True))
        self.action_dc_load_matrix.triggered.connect(lambda: self.dc_table_change(deepcopy(self.scn_strat_matrix)))
        self.action_dc_load_custom.triggered.connect(lambda: self.dc_table_change(self.dc_table_load(self.projpath, '*', return_default=False)))
        self.action_dc_load_default.triggered.connect(lambda: self.dc_table_change(self.scn_strat_default))
        
        # Add copy to clipboard button
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        self.tb_clipboard = QtWidgets.QToolButton()
        self.tb_clipboard.setText('*')
        self.tb_clipboard.setToolTip('Copy Framepath to Clipboard')
        self.menubar.setCornerWidget(self.tb_clipboard, QtCore.Qt.TopRightCorner)
        self.tb_clipboard.clicked.connect(lambda: cb.setText('{}_01_0001.sfrm'.format(os.path.normpath(os.path.join(self.datapath, self.projname))), mode=cb.Clipboard))
        
        # Add QSliders to QMenu
        minBox = QtWidgets.QHBoxLayout()
        minLabel = QtWidgets.QLabel('Minimum:')
        minSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        minSlider.setMinimum(-100)
        minSlider.setMaximum(100)
        minSlider.setSingleStep(10)
        minSlider.setPageStep(10)
        minSlider.setValue(0)
        minValue = QtWidgets.QLabel(str(minSlider.value()))
        minSlider.valueChanged.connect(lambda: self.fv_update_params(vmin=minSlider.value(), save=False))
        minSlider.valueChanged.connect(lambda: minValue.setText(str(minSlider.value())))
        minSlider.setValue(self.iniPar['fv_int_min'])
        minBox.addWidget(minLabel)
        minBox.addWidget(minSlider)
        minBox.addWidget(minValue)
        minWidget = QtWidgets.QWidget()
        minWidget.setLayout(minBox)
        minAction = QtWidgets.QWidgetAction(self)
        minAction.setDefaultWidget(minWidget)
        self.menu_fv_set_intensity.addAction(minAction)
        
        maxBox = QtWidgets.QHBoxLayout()
        maxLabel = QtWidgets.QLabel('Maximum:')
        maxSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        maxSlider.setMinimum(200)
        maxSlider.setMaximum(1000)
        maxSlider.setSingleStep(100)
        maxSlider.setPageStep(100)
        maxSlider.setValue(200)
        maxValue = QtWidgets.QLabel(str(maxSlider.value()))
        maxSlider.valueChanged.connect(lambda: self.fv_update_params(vmax=maxSlider.value(), save=False))
        maxSlider.valueChanged.connect(lambda: maxValue.setText(str(maxSlider.value())))
        maxSlider.setValue(self.iniPar['fv_int_max'])
        maxBox.addWidget(maxLabel)
        maxBox.addWidget(maxSlider)
        maxBox.addWidget(maxValue)
        maxWidget = QtWidgets.QWidget()
        maxWidget.setLayout(maxBox)
        maxAction = QtWidgets.QWidgetAction(self)
        maxAction.setDefaultWidget(maxWidget)
        self.menu_fv_set_intensity.addAction(maxAction)
    
    def init_special_tabs(self):
        #----------------------#
        #  Allow Special Tabs  #
        #----------------------#
        if self.iniPar['enable_tab_cryo'] == True:
            self.tW_general.setTabEnabled(1, True)
        else:
            self.tW_general.setTabEnabled(1, False)
            
        if self.iniPar['enable_tab_align'] == True:
            self.tW_general.setTabEnabled(2, True)
        else:
            self.tW_general.setTabEnabled(2, False)
    
    def init_axes(self):
        self.log.debug('Called')
        #--------------------------------#
        # Axes Numbers, Names and Limits #
        #--------------------------------#
        self.gon_name_from_num = {1:'Phi',
                                  2:'Chi',
                                  3:'Omega',
                                  4:'2-Theta',
                                  5:'Distance',
                                  6:'X',
                                  7:'Y',
                                  8:'Z'}
        self.gon_num_from_name = {v:k for k,v in self.gon_name_from_num.items()}
        
        self.gon_ax_ls_from_num = {1:(self.btn_ls_phi),
                                   2:(self.btn_ls_chi),
                                   3:(self.btn_ls_omg),
                                   4:(self.btn_ls_tth),
                                   5:(self.btn_ls_dxt),
                                   6:(None),
                                   7:(None),
                                   8:(None)}
        
        # goniometer limits dict
        # number:(minimum, maximum)
        self.gon_limits = {1:(  None,  None),
                           2:( -60.0,   0.0),
                           3:( -35.0,   0.0),
                           4:( -35.0,   0.0),
                           5:(-176.0, -75.0),
                           6:(  None,  None),
                           7:(  None,  None),
                           8:(  None,  None)}
        # coupled goniometer limits dict
        # key : value
        # key <= value, ax1 <= ax2
        # 2-Theta [4] must be equal or smaller than Omega [3]
        self.gon_limits_coupled = {4:3}
    
    def init_frameview(self):
        self.log.debug('Called')
        self.FrameView = FrameViewClass(self.iniPar)
        #self.fv_thread = QtCore.QThread()
        #self.FrameView.moveToThread(self.fv_thread)
        #self.fv_thread.start()
        self.FrameContainer.insertWidget(0, self.FrameView)
        
        # p2 send a signal when a new image is ready
        # it takes a second to transfer the image
        # the image path is added to a threadpool that
        # tries to load the image and once finished closes
        # for short exposure times this ensures that an
        # image is displayed. If the exposure time is lower
        # than the transfer time no image would ever be displayed
        # fv_process_queue tries to load the first image in frame_queue
        # and pop() it if successful and waits timeout if
        # unsuccessful. it will retry until max_retries is reached
        # and quit. This is to prevent endless loops if a corrupted
        # frame was stored. If no thread is running when a new
        # image arrives (is added to the queue via fv_process_queue_add)
        # a new is started.
        self.fv_pool = QtCore.QThreadPool()
        self.fv_pool.setMaxThreadCount(1)
        self.frameQueueThread = Threading(self.fv_process_queue, fn_args={}, fn_kwargs={})
        #frameQueueThread.signals.finished.connect(lambda: print('>>> fv_process_queue thread done <<<'))
        self.fv_pool.start(self.frameQueueThread)
        
        # queue to display frames
        self.frame_queue = []
        
        # hide frame toolbar on startup
        self.widgetFrameToolbar.hide()
        self.widgetFrameToolbar.setEnabled(False)
        if self.iniPar['show_fv_toolbar'] == True:
            self.widgetFrameToolbar.show()
            self.widgetFrameToolbar.setEnabled(True)
        
        self.btn_frm_home.clicked.connect(self.fv_toolbar_home)
        self.btn_frm_zoom.clicked.connect(self.fv_toolbar_zoom)
        self.btn_frm_pan.clicked.connect(self.fv_toolbar_pan)
        self.btn_frm_fwd.clicked.connect(lambda: self.fv_toolbar_browse(1))
        self.btn_frm_bwd.clicked.connect(lambda: self.fv_toolbar_browse(-1))
    
    def init_dc_scan(self):
        self.log.debug('Called')
        #----------------------------#
        #  SCAN - default strategies #
        #----------------------------#
        ####################################
        ##          RUN DICT KEYS         ##
        ##      DO NOT CHANGE THE KEYS    ##
        ##      USED BY dc_collect_data   ##
        ####################################
        #'Phi'     : Phi angle [deg]
        #'Chi'     : Chi angle [deg]
        #'Omega'   : Omega angle [deg]
        #'2-Theta' : 2-Theta angle [deg]
        #'Distance': Detector distance
        #'Exposure': Exposure time [s]
        #'Width'   : Frame width [deg/frame]
        #'Range'   : Scan range [deg]
        ####################################

        # Strategy section buttons
        self.tbl_scn_mat.itemChanged.connect(self.dc_table_on_changed)
        self.btn_scn_mat_start.clicked.connect(self.dc_collect_data)
    
    def init_dc_centring(self):
        self.log.debug('Called')
        #----------------------#
        #   GUI - ADJUST POS   #
        #----------------------#
        phi_align_pos = self.iniPar['align_pos_phi']
        
        self.btn_cnt_phi_1.setText('Phi\n{:}'.format(phi_align_pos +   0.0))
        self.btn_cnt_phi_2.setText('Phi\n{:}'.format(phi_align_pos +  90.0))
        self.btn_cnt_phi_3.setText('Phi\n{:}'.format(phi_align_pos + 180.0))
        self.btn_cnt_phi_4.setText('Phi\n{:}'.format(phi_align_pos -  90.0))
        
        self.btn_cnt_phi_1.clicked.connect(lambda: self.smc_control_goto(1, phi_align_pos +   0.0))
        self.btn_cnt_phi_2.clicked.connect(lambda: self.smc_control_goto(1, phi_align_pos +  90.0))
        self.btn_cnt_phi_3.clicked.connect(lambda: self.smc_control_goto(1, phi_align_pos + 180.0))
        self.btn_cnt_phi_4.clicked.connect(lambda: self.smc_control_goto(1, phi_align_pos -  90.0))
        self.btn_cnt_chi_1.clicked.connect(lambda: self.smc_control_goto(2,   0.0))
        self.btn_cnt_chi_2.clicked.connect(lambda: self.smc_control_goto(2, -20.0))
        self.btn_cnt_chi_3.clicked.connect(lambda: self.smc_control_goto(2, -40.0))
        self.btn_cnt_chi_4.clicked.connect(lambda: self.smc_control_goto(2, -60.0))
        self.btn_cnt_inc_1.clicked.connect(lambda: self.smc_control_move(1,  45.0))
        
        style_btn_cnt_inc = ('QToolButton          {background-color: rgb(230, 235, 230); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75); border-radius: 50px}'
                             'QToolButton:hover    {background-color: rgb(220, 230, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                             'QToolButton:pressed  {background-color: rgb(220, 225, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                             'QToolButton:disabled {background-color: rgb(240, 245, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        
        style_btn_cnt_chi = ('QToolButton          {background-color: rgb(235, 230, 230); color: rgb( 75,  75,  75); border: 2px solid rgb(200, 200, 200); border-radius: 10px}'
                             'QToolButton:hover    {background-color: rgb(230, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb(200, 200, 200)}'
                             'QToolButton:pressed  {background-color: rgb(225, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb(200, 200, 200)}'
                             'QToolButton:disabled {background-color: rgb(245, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
                             
        
        style_btn_cnt_phi = ('QToolButton          {background-color: rgb(230, 230, 230); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75); border-radius: 20px}'
                             'QToolButton:hover    {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                             'QToolButton:pressed  {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                             'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        
        self.btn_cnt_chi_1.setStyleSheet(style_btn_cnt_chi)
        self.btn_cnt_chi_2.setStyleSheet(style_btn_cnt_chi)
        self.btn_cnt_chi_3.setStyleSheet(style_btn_cnt_chi)
        self.btn_cnt_chi_4.setStyleSheet(style_btn_cnt_chi)
        self.btn_cnt_phi_1.setStyleSheet(style_btn_cnt_phi)
        self.btn_cnt_phi_2.setStyleSheet(style_btn_cnt_phi)
        self.btn_cnt_phi_3.setStyleSheet(style_btn_cnt_phi)
        self.btn_cnt_phi_4.setStyleSheet(style_btn_cnt_phi)
        self.btn_cnt_inc_1.setStyleSheet(style_btn_cnt_inc)
    
    def adjust_phi_speed(self):
        if self.SMCIsConnected:
            if self.iniPar['enable_tab_cryo'] == True:
                self.SMC.send_to_SMC('acc1:{}'.format(self.iniPar['dpx_phi_acc']))
                self.SMC.send_to_SMC('dec1:{}'.format(self.iniPar['dpx_phi_dec']))
                self.SMC.send_to_SMC('frun1:{}'.format(self.iniPar['dpx_phi_frun']))
                self.SMC.send_to_SMC('ffast1:{}'.format(self.iniPar['dpx_phi_ffast']))
            else:
                self.SMC.send_to_SMC('acc1:{}'.format(self.iniPar['ax_phi_acc']))
                self.SMC.send_to_SMC('dec1:{}'.format(self.iniPar['ax_phi_dec']))
                self.SMC.send_to_SMC('frun1:{}'.format(self.iniPar['ax_phi_frun']))
                self.SMC.send_to_SMC('ffast1:{}'.format(self.iniPar['ax_phi_ffast']))
    
    def init_xyzStage(self):
        self.log.debug('Called')
        #----------------------#
        #    GUI - XYZ-Stage   #
        #----------------------#
        self.xyz_edges = [self.btn_xyz_edge_00,
                          self.btn_xyz_edge_11, self.btn_xyz_edge_12, self.btn_xyz_edge_13, self.btn_xyz_edge_14,
                          self.btn_xyz_edge_21, self.btn_xyz_edge_22, self.btn_xyz_edge_23, self.btn_xyz_edge_24,
                          self.btn_xyz_edge_31, self.btn_xyz_edge_32, self.btn_xyz_edge_33, self.btn_xyz_edge_34,
                          self.btn_xyz_edge_41, self.btn_xyz_edge_42, self.btn_xyz_edge_43, self.btn_xyz_edge_44]
                          
        self.xy_buttons = [self.btn_xyz_l_1, self.btn_xyz_r_1,
                           self.btn_xyz_l_2, self.btn_xyz_r_2,
                           self.btn_xyz_l_3, self.btn_xyz_r_3]
        self.z_buttons = [self.btn_xyz_u_1, self.btn_xyz_d_1,
                          self.btn_xyz_u_2, self.btn_xyz_d_2,
                          self.btn_xyz_u_3, self.btn_xyz_d_3]
        
        self.btn_xyz_right.clicked.connect(lambda: self.xyz_align_pos(6))
        self.btn_xyz_left_1.clicked.connect(lambda: self.xyz_align_pos(7))
        self.btn_xyz_left_2.clicked.connect(lambda: self.xyz_align_pos(-7))
        self.btn_xyz_u_1.clicked.connect(lambda: self.smc_control_move(8,  5.0))
        self.btn_xyz_d_1.clicked.connect(lambda: self.smc_control_move(8, -5.0))
        self.btn_xyz_u_2.clicked.connect(lambda: self.smc_control_move(8, 25.0))
        self.btn_xyz_d_2.clicked.connect(lambda: self.smc_control_move(8,-25.0))
        self.btn_xyz_u_3.clicked.connect(lambda: self.smc_control_fast_pos(8))
        self.btn_xyz_d_3.clicked.connect(lambda: self.smc_control_fast_neg(8))
        
        #----------------------#
        #  GUI - BUTTON STYLES #
        #----------------------#
        style_btn_xyz_edges = ('QToolButton          {background-color: rgb(230, 230, 230); color: rgb( 75,  75,  75); border: 0px solid rgb( 75,  75,  75); border-radius: 5px}'
                               'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(225, 225, 225); border: 0px solid rgb(240, 240, 240)}')
        
        for b in self.xyz_edges:
            b.setStyleSheet(style_btn_xyz_edges)
        
        style_btn_xyz = ('QToolButton          {background-color: rgb(230, 230, 230); color: rgb( 75,  75,  75); border: 1px solid rgb( 75,  75,  75); border-radius: 5px}'
                         'QToolButton:hover    {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 1px solid rgb( 75,  75,  75)}'
                         'QToolButton:pressed  {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 1px solid rgb( 75,  75,  75)}'
                         'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(200, 200, 200); border: 1px solid rgb(220, 220, 220)}')
                         
        self.btn_xyz_left_1.setStyleSheet(style_btn_xyz)
        self.btn_xyz_left_2.setStyleSheet(style_btn_xyz)
        self.btn_xyz_right.setStyleSheet(style_btn_xyz)
        for b in self.xy_buttons:
            b.setStyleSheet(style_btn_xyz)
        for b in self.z_buttons:
            b.setStyleSheet(style_btn_xyz)
    
    def init_homing_panel(self):
        self.log.debug('Called')
        #----------------------#
        #  GUI - HOMING PANEL  #
        #----------------------#
        self.btn_home_axis.clicked.connect(lambda: self.smc_control_home(*self.smc_align_home_select()))
        self.btn_home_dxt.clicked.connect(lambda: self.smc_control_home_DXT(5, self.iniPar['ax_dxt_offset']))
        
        self.group_rdo_dir = QtWidgets.QButtonGroup()
        self.group_rdo_dir.addButton(self.home_pos_rdo)
        self.group_rdo_dir.addButton(self.home_neg_rdo)
        
        self.group_rdo_axs = QtWidgets.QButtonGroup()
        self.group_rdo_axs.addButton(self.home_phi_rdo)
        self.group_rdo_axs.addButton(self.home_chi_rdo)
        self.group_rdo_axs.addButton(self.home_omg_rdo)
        self.group_rdo_axs.addButton(self.home_tth_rdo)
    
        #----------------------#
        #  GUI - BUTTON STYLES #
        #----------------------#
        style_btn_align_home = ('QToolButton          {background-color: rgb(230, 230, 230); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75); border-radius: 20px}'
                                'QToolButton:hover    {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                                'QToolButton:pressed  {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                                'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        self.btn_home_axis.setStyleSheet(style_btn_align_home)
        self.btn_home_dxt.setStyleSheet(style_btn_align_home)
    
    def init_single_axis(self):
        self.log.debug('Called')
        #----------------------#
        #   GUI - SINGLE AXIS  #
        #----------------------#
        self.group_rdo_sax = QtWidgets.QButtonGroup()
        self.group_rdo_sax.addButton(self.rdo_sax_phi)
        self.group_rdo_sax.addButton(self.rdo_sax_chi)
        self.group_rdo_sax.addButton(self.rdo_sax_omg)
        self.group_rdo_sax.addButton(self.rdo_sax_tth)
        self.group_rdo_sax.addButton(self.rdo_sax_dxt)

        self.btn_sax_stp_bck.clicked.connect(lambda: self.smc_control_step_neg(self.smc_align_axis_select()))
        self.btn_sax_con_bck.pressed.connect(lambda: self.smc_control_fast_neg(self.smc_align_axis_select()))
        self.btn_sax_run_bck.pressed.connect(lambda: self.smc_control_run_neg(self.smc_align_axis_select()))
        self.btn_sax_run_bck.released.connect(lambda: self.SMC.send_to_SMC('stop'))
        self.btn_sax_run_stp.clicked.connect(self.gen_stop)
        self.btn_sax_run_fwd.pressed.connect(lambda: self.smc_control_run_pos(self.smc_align_axis_select()))
        self.btn_sax_run_fwd.released.connect(lambda: self.SMC.send_to_SMC('stop'))
        self.btn_sax_con_fwd.pressed.connect(lambda: self.smc_control_fast_pos(self.smc_align_axis_select()))
        self.btn_sax_stp_fwd.clicked.connect(lambda: self.smc_control_step_pos(self.smc_align_axis_select()))
        self.btn_sax_got.clicked.connect(lambda:  self.smc_control_goto(self.smc_align_axis_select(), float(self.inp_sax_got.value())))
        
        #----------------------#
        #  GUI - INITIALIZING  #
        #----------------------#
        self.smc_align_relabel(1)
        self.smc_align_relabel(2)
        self.smc_align_relabel(3)
        self.smc_align_relabel(4)
        self.smc_align_relabel(5)
        self.smc_align_relabel(-1)
        
        #----------------------#
        #   GUI - ADJUST POS   #
        #----------------------#
        self.btn_cmp_phi_0.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.value())))
        self.btn_cmp_phi_1.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.value()) + 90.0))
        self.btn_cmp_phi_2.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.value()) + 180.0))
        self.btn_cmp_phi_3.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.value()) - 90.0))
        self.btn_cmp_chi_0.clicked.connect(lambda: self.smc_control_goto(2, float(self.inp_chi.value())))
        self.btn_cmp_chi_1.clicked.connect(lambda: self.smc_control_goto(2, float(self.inp_chi.value()) - 20.0))
        self.btn_cmp_chi_2.clicked.connect(lambda: self.smc_control_goto(2, float(self.inp_chi.value()) - 40.0))
        self.btn_cmp_chi_3.clicked.connect(lambda: self.smc_control_goto(2, float(self.inp_chi.value()) - 60.0))
        
        self.btn_cmp_phi_inc.clicked.connect(lambda: self.smc_control_move(1, float(self.inp_pls.value())))
        
        self.send_btn.clicked.connect(self.smc_control_send)
        
        self.inp_phi.valueChanged.connect(lambda: self.smc_align_relabel(1))
        self.inp_chi.valueChanged.connect(lambda: self.smc_align_relabel(2))
        self.inp_omg.valueChanged.connect(lambda: self.smc_align_relabel(3))
        self.inp_tth.valueChanged.connect(lambda: self.smc_align_relabel(4))
        self.inp_dxt.valueChanged.connect(lambda: self.smc_align_relabel(5))
        self.inp_pls.valueChanged.connect(lambda: self.smc_align_relabel(-1))
        
        #----------------------#
        #  GUI - BUTTON STYLES #
        #----------------------#
        style_btn_cmp_phi = ('QToolButton          {background-color: rgb(230, 230, 230); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75); border-radius: 20px}'
                             'QToolButton:hover    {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                             'QToolButton:pressed  {background-color: rgb(220, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                             'QToolButton:disabled {background-color: rgb(240, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        self.btn_cmp_phi_0.setStyleSheet(style_btn_cmp_phi)
        self.btn_cmp_phi_1.setStyleSheet(style_btn_cmp_phi)
        self.btn_cmp_phi_2.setStyleSheet(style_btn_cmp_phi)
        self.btn_cmp_phi_3.setStyleSheet(style_btn_cmp_phi)
        
        style_btn_cmp_chi = ('QToolButton          {background-color: rgb(235, 230, 230); color: rgb( 75,  75,  75); border: 2px solid rgb(200, 200, 200); border-radius: 10px}'
                             'QToolButton:hover    {background-color: rgb(230, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb(200, 200, 200)}'
                             'QToolButton:pressed  {background-color: rgb(225, 220, 220); color: rgb( 75,  75,  75); border: 2px solid rgb(200, 200, 200)}'
                             'QToolButton:disabled {background-color: rgb(245, 240, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        self.btn_cmp_chi_0.setStyleSheet(style_btn_cmp_chi)
        self.btn_cmp_chi_1.setStyleSheet(style_btn_cmp_chi)
        self.btn_cmp_chi_2.setStyleSheet(style_btn_cmp_chi)
        self.btn_cmp_chi_3.setStyleSheet(style_btn_cmp_chi)
        
        style_btn_cmp_phi_inc = ('QToolButton          {background-color: rgb(230, 235, 230); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75); border-radius: 50px}'
                                 'QToolButton:hover    {background-color: rgb(220, 230, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                                 'QToolButton:pressed  {background-color: rgb(220, 225, 220); color: rgb( 75,  75,  75); border: 2px solid rgb( 75,  75,  75)}'
                                 'QToolButton:disabled {background-color: rgb(240, 245, 240); color: rgb(200, 200, 200); border: 2px solid rgb(220, 220, 220)}')
        self.btn_cmp_phi_inc.setStyleSheet(style_btn_cmp_phi_inc)
        
        style_btn_sax = ('QToolButton          {background-color: rgb(240, 240, 240); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75); border-radius: 2px}'
                         'QToolButton:hover    {background-color: rgb(255, 255, 255); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}'
                         'QToolButton:pressed  {background-color: rgb(200, 225, 200); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}'
                         'QToolButton:checked  {background-color: rgb(200, 200, 200); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}'
                         'QToolButton:disabled {background-color: rgb(200, 200, 200); color: rgb(0, 0, 0); border: 1px solid rgb( 75,  75,  75)}')
        self.btn_sax_stp_bck.setStyleSheet(style_btn_sax)
        self.btn_sax_con_bck.setStyleSheet(style_btn_sax)
        self.btn_sax_run_bck.setStyleSheet(style_btn_sax)
        self.btn_sax_run_stp.setStyleSheet(style_btn_sax)
        self.btn_sax_run_fwd.setStyleSheet(style_btn_sax)
        self.btn_sax_con_fwd.setStyleSheet(style_btn_sax)
        self.btn_sax_stp_fwd.setStyleSheet(style_btn_sax)
        self.btn_sax_got.setStyleSheet(style_btn_sax)
    
    def init_simple_scan(self):
        self.log.debug('Called')
        #-----------------------#
        # GUI - SIMPLE PHI SCAN #
        #-----------------------#
        # who is who
        # sca_spn_rot = Rotation Time s/*
        # sca_spn_row = Rotation Width */s
        # sca_spn_scw = Scan Width *
        # sca_spn_tot = Total Time s
        # sca_spn_fin = Finished in hh:mm:ss
        # sca_spn_fre = Frame Exposure s/f
        # sca_spn_frw = Frame Width */f
        # sca_spn_frn = # Frames
        # set limits
        self.sca_spn_rot.setMinimum(0.1)
        self.sca_spn_rot.setMaximum(999.9)
        self.sca_spn_row.setMinimum(0.001)
        self.sca_spn_row.setMaximum(999.999)
        self.sca_spn_scw.setMinimum(-360.0)
        self.sca_spn_scw.setMaximum(360.0)
        self.sca_spn_tot.setMinimum(1.0)
        self.sca_spn_tot.setMaximum(9999999.0)
        self.sca_spn_fre.setMinimum(0.1)
        self.sca_spn_fre.setMaximum(999.9)
        self.sca_spn_frw.setMinimum(0.01)
        self.sca_spn_frw.setMaximum(360.0)
        self.sca_spn_frn.setMinimum(1.0)
        self.sca_spn_frn.setMaximum(999999.0)
        # change dependent values
        self.sca_spn_rot.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_tot, self.sca_spn_scw.value(), self.sca_spn_rot.value(), '*'))
        self.sca_spn_rot.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_row,                      1.0, self.sca_spn_rot.value(), '/', 'float'))
        self.sca_spn_rot.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_frw, self.sca_spn_row.value(), self.sca_spn_fre.value(), '*', 'float'))
        self.sca_spn_rot.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_frn, self.sca_spn_tot.value(), self.sca_spn_fre.value(), '/', 'int'))
        self.sca_spn_scw.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_tot, self.sca_spn_scw.value(), self.sca_spn_rot.value(), '*', 'float'))
        self.sca_spn_scw.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_frn, self.sca_spn_tot.value(), self.sca_spn_fre.value(), '/', 'int'))
        self.sca_spn_fre.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_frn, self.sca_spn_tot.value(), self.sca_spn_fre.value(), '/', 'int'))
        self.sca_spn_fre.valueChanged.connect(lambda: self.smc_on_dependent(self.sca_spn_frw, self.sca_spn_row.value(), self.sca_spn_fre.value(), '*', 'float'))
        self.sca_spn_tot.valueChanged.connect(lambda: self.sca_spn_fin.setText(self.gen_conv_to_time(self.sca_spn_tot.value())))
        self.btn_scn_sim_start.clicked.connect(lambda: self.dc_collect_simple())
        
        #----------------------#
        #  GUI - BUTTON STYLES #
        #----------------------#
        style_sca_spn = ('QDoubleSpinBox       {background-color: rgb(250, 250, 250)}'
                         'QDoubleSpinBox:hover {background-color: rgb(250, 250, 250); border-width: 2px; border-style: solid; border-color: rgb(100, 255, 100)}'
                         'QSpinBox             {background-color: rgb(250, 250, 250)}'
                         'QSpinBox:hover       {background-color: rgb(250, 250, 250); border-width: 2px; border-style: solid; border-color: rgb(100, 255, 100)}'
                         'QLineEdit            {background-color: rgb(250, 250, 250)}'
                         'QLineEdit:hover      {background-color: rgb(250, 250, 250); border-width: 2px; border-style: solid; border-color: rgb(100, 255, 100)}')
        self.sca_spn_rot.setStyleSheet(style_sca_spn)
        self.sca_spn_scw.setStyleSheet(style_sca_spn)
        self.sca_spn_fre.setStyleSheet(style_sca_spn)
        self.sca_spn_bsn.setStyleSheet(style_sca_spn)
        self.sca_spn_run.setStyleSheet(style_sca_spn)
    
    def init_buttons(self):
        self.log.debug('Called')
        self.action_P2_collect_darks.setEnabled(False)
        self.action_P2_stop.setEnabled(False)
        self.btn_sax_run_stp.setEnabled(False)
        self.action_SMC_home.setEnabled(False)
        self.action_SMC_idle.setEnabled(False)
        self.action_SMC_disconnect.setEnabled(False)
        self.action_P2_disconnect.setEnabled(False)
        self.btn_p2SendText.setEnabled(False)
        self.cbx_p2sendText.setEnabled(False)
        self.btn_scn_mat_start.setEnabled(False)
        self.btn_scn_sim_start.setEnabled(False)
        # XYZ centering buttons
        self.btn_xyz_right.setEnabled(False)
        self.btn_xyz_left_1.setEnabled(False)
        self.btn_xyz_left_2.setEnabled(False)
        for b in self.xy_buttons:
            b.setEnabled(False)
        for b in self.z_buttons:
            b.setEnabled(False)
        # STOP buttons
        for stp in self.stop_buttons:
            stp.setEnabled(False)
    
    #-----------#
    #    GUI    #
    #-----------#
    
    def gui_on_smc_update(self, axsPositions, axsStatus):
        #self.log.debug('{}'.format(new_position_dict))
        '''
         This function is linked to SMC_Connection signal_SMCUpdate
         signal_SMCUpdate = QtCore.pyqtSignal(dict, dict)
         Axes names:
         1:'Phi',2:'Chi',3:'Omega',4:'2-Theta',5:'Distance',6:'X',7:'Y',8:'Z'
         axsStatus: dictionary containing axis:state as type int:int
         {1:145, 2:129, 3:129, 4:129, 5:32913, 6:129, 7:129, 8:129}
         axsPositions: dictionary containing axis:position as type int:float
         {1:0.0, 2:0.0, 3:0.0, 4:20.0, 5:-176.0, 6:0.0, 7:0.0, 8:0.0}
        '''
        # 
        self.gon_current_pos = axsPositions
        self.lcd_phi.display('{: 8.5f}'.format(axsPositions[1]))
        self.lcd_chi.display('{: 8.5f}'.format(axsPositions[2]))
        self.lcd_omg.display('{: 8.5f}'.format(axsPositions[3]))
        self.lcd_tth.display('{: 8.5f}'.format(axsPositions[4]))
        self.lcd_dxt.display('{: 8.5f}'.format(axsPositions[5]))
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
        self.instrumentIsIdle = False
        if axsStatus[1]&128 == 128:
            self.instrumentIsIdle = True
        for ax_num, ax_status in axsStatus.items():
            indicator_widget = self.gon_ax_ls_from_num[ax_num]
            if indicator_widget is None:
                continue
            if ax_status&8 == 8 or ax_status&4 == 4:
                indicator_widget.setStyleSheet(self.style_btn_ls_error)
            elif ax_status&2 == 2:
                indicator_widget.setStyleSheet(self.style_btn_ls_reference)
            elif   ax_status&1 == 1:
                indicator_widget.setStyleSheet(self.style_btn_ls_ready)
            #elif ax_status&128 == 128:
            #    indicator_widget.setStyleSheet(self.style_btn_ls_ready)
            else:
                indicator_widget.setStyleSheet(self.style_btn_ls_moving)
    
    def gui_toggle_buttons(self, toggle):
        self.log.debug('Called')
        # general buttons
        for btn in self.generalButtons:
            btn.setEnabled(toggle)
        # XYZ centering buttons
        self.btn_xyz_right.setEnabled(toggle)
        self.btn_xyz_left_1.setEnabled(toggle)
        self.btn_xyz_left_2.setEnabled(toggle)
        # Don't enable x/y buttons here!
        # Do it with: xyz_align_pos
        if self.inCenteringPosition:
            for btn in self.xy_buttons:
                btn.setEnabled(toggle)
        for btn in self.z_buttons:
            btn.setEnabled(toggle)
        # Do not enable STOP buttons
        for btn in self.stop_buttons:
            btn.setDisabled(toggle)
    
    def gui_toggle_dc_buttons(self, toggle):
        self.log.debug('Called')
        for btn in self.dc_buttons:
            btn.setEnabled(toggle)
    
    def gui_check_scan_enable(self):
        self.log.debug('Called')
        '''
         Check upon P2 and SMC (dis-)connection if buttons can be enabled
         during data collection the buttons are disabled "manually" in "dc_setup_pre"
         and dc_setup_post calls this function again to check if enable is allowed
        '''
        # data collection buttons
        if all([self.p2IsConnected, self.SMCIsConnected, self.SHIsConnected]):#, self.instrumentIsIdle]):
            self.log.debug('True')
            self.btn_scn_mat_start.setEnabled(True)
            self.btn_scn_sim_start.setEnabled(True)
        else:
            self.log.debug('False')
            self.btn_scn_mat_start.setEnabled(False)
            self.btn_scn_sim_start.setEnabled(False)
    
    def gui_stop_disable(self):
        self.log.debug('Called')
        self.btn_sax_run_stp.setEnabled(False)
        for stp in self.stop_buttons:
            stp.setEnabled(False)
    
    def gui_ini_reload(self, iniPath, update_gui=False):
        self.log.debug('Called')
        '''
         this is called on startup (update_gui=False)
         and upon menu action (update_gui=True)
         The inits are not called upon startup as the
         gui is not yet initializes when the ini file
         is read. Add inits here to update them on call.
        '''
        if not os.path.exists(iniPath):
            save_ini(iniPath)
        self.iniPar = read_ini(iniPath)
        [self.log.debug('{:<16}:{}'.format(k,v)) for k,v in self.iniPar.items()]
        # add inits to update
        if update_gui:
            self.init_dc_centring()
            self.init_special_tabs()
            self.adjust_phi_speed()
    
    def gui_popup(self, _case='Information', _title='Title', _text='Text', _info='Info', show_cancel=False, blocking=True):
        self.log.debug('Called')
        '''
         _icon:
            QtWidgets.QMessageBox.NoIcon      0 the message box does not have any icon.
            QtWidgets.QMessageBox.Information 1 an icon indicating that the message is nothing out of the ordinary.
            QtWidgets.QMessageBox.Warning     2 an icon indicating that the message is a warning, but can be dealt with.
            QtWidgets.QMessageBox.Critical    3 an icon indicating that the message represents a critical problem.
            QtWidgets.QMessageBox.Question    4 an icon indicating that the message is asking a question.
        '''
        if _case.casefold() == 'information'.casefold():
            #self.ic_MessageBoxInformation = self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_MessageBoxInformation'))
            #_wicon = self.ic_MessageBoxInformation
            _icon = QtWidgets.QMessageBox.Information
        elif _case.casefold() == 'warning'.casefold():
            #self.ic_MessageBoxWarning = self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_MessageBoxWarning'))
            #_wicon = self.ic_MessageBoxWarning
            _icon = QtWidgets.QMessageBox.Warning
        elif _case.casefold() == 'critical'.casefold():
            #self.ic_MessageBoxCritical = self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_MessageBoxCritical'))
            #_wicon = self.ic_MessageBoxCritical
            _icon = QtWidgets.QMessageBox.Critical
        elif _case.casefold() == 'question'.casefold():
            #self.ic_MessageBoxQuestion = self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_MessageBoxQuestion'))
            #_wicon = self.ic_MessageBoxQuestion
            _icon = QtWidgets.QMessageBox.Question
        else:
            _icon = QtWidgets.QMessageBox.NoIcon
        
        # use default icon
        self.windowIcon = QtGui.QIcon()
        self.windowIcon.addPixmap(QtGui.QPixmap(':/icons/logo.png'), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        _wicon = self.windowIcon
        
        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowIcon(_wicon)
        msgBox.setIcon(_icon)
        msgBox.setWindowTitle(_title)
        msgBox.setText(_text)
        msgBox.setInformativeText(_info)
        
        if show_cancel:
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        else:
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        
        if blocking:
            return msgBox.exec_()
        else:
            return msgBox.show()
    
    def gui_update_title(self):
        self.log.debug('Called')
        self.setWindowTitle('Huber Diffractometer Control ({}) - User: {} - Project: {} - Data: {}'.format(self.version, self.username, self.projname, self.dataname))
    
    def gui_win_about(self):
        self.log.debug('Called')
        msgBox = QtWidgets.QMessageBox()
        windowIcon = QtGui.QIcon()
        windowIcon.addPixmap(QtGui.QPixmap(':/icons/logo.png'), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        msgBox.setWindowIcon(windowIcon)
        msgBox.setIconPixmap(QtGui.QPixmap(':/icons/aulogo.png'))
        msgBox.setWindowTitle('About')
        msgBox.setText('')
        msgBox.setInformativeText('')
        msgBox.setDetailedText('Huber Diffractometer Control\n{}'.format(self.version))
        msgBox.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        msgBox.exec_()
    
    def gui_win_error(self):
        #self.log.debug('Called')
        # pop up a message box asking to continue
        msgBox = QtWidgets.QMessageBox()
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/question_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        msgBox.setWindowIcon(icon)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setWindowTitle('Limit switch active')
        msgBox.setText('Manually drive the axis!')
        # SAY WHICH AXIS IT IS
        msgBox.setInformativeText('')
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        btnPressed = msgBox.exec()
        # quit the app!
        sys.exit()
    
    #------------#
    #    User    #
    #------------#
    
    def usr_ch_user_win(self):
        self.log.debug('Called')
        # todo:
        #  - merge functions
        aList = [(os.path.basename(i.rstrip(os.sep)), datetime.fromtimestamp(os.path.getmtime(i)).strftime('%Y-%m-%d %H:%M:%S'), datetime.fromtimestamp(os.path.getctime(i)).strftime('%Y-%m-%d %H:%M:%S')) for i in glob.glob(os.path.join(self.iniPar['path_SMC'], '*', '')) if not os.path.basename(i).startswith('_') and ' ' not in os.path.basename(i)]
        self.userBrowserWindow = Browser(aList, 'Change User', 'ch_user', 'add_user', 'User')
        self.userBrowserWindow.pBsig_selectedItem.connect(self.usr_ch_user)
    
    def usr_ch_proj_win(self):
        self.log.debug('Called')
        # todo:
        #  - merge functions
        aList = [(os.path.basename(i.rstrip(os.sep)), datetime.fromtimestamp(os.path.getmtime(i)).strftime('%Y-%m-%d %H:%M:%S'), datetime.fromtimestamp(os.path.getctime(i)).strftime('%Y-%m-%d %H:%M:%S')) for i in glob.glob(os.path.join(self.iniPar['path_SMC'], self.username, '*', '')) if not os.path.basename(i).startswith('_') and ' ' not in os.path.basename(i)]
        self.projectBrowserWindow = Browser(aList, 'Project Browser', 'ch_project', 'add_project', 'Project')
        self.projectBrowserWindow.pBsig_selectedItem.connect(self.usr_ch_proj)
    
    def usr_ch_data_win(self):
        self.log.debug('Called')
        # todo:
        #  - merge functions
        aList = [(os.path.basename(i.rstrip(os.sep)), datetime.fromtimestamp(os.path.getmtime(i)).strftime('%Y-%m-%d %H:%M:%S'), datetime.fromtimestamp(os.path.getctime(i)).strftime('%Y-%m-%d %H:%M:%S')) for i in glob.glob(os.path.join(self.iniPar['path_SMC'], self.username, self.projname, '*', '')) if not os.path.basename(i).startswith('_') and ' ' not in os.path.basename(i)]
        self.dataBrowserWindow = Browser(aList, 'Data Browser', 'ch_data', 'add_folder', 'Folder')
        self.dataBrowserWindow.pBsig_selectedItem.connect(self.usr_ch_data)
    
    def usr_ch_user(self, aUserName):
        self.log.debug('{}'.format(aUserName))
        '''
         
        '''
        if not aUserName:
            self.usr_ch_user_win()
            return
        
        # set vars
        self.username = aUserName
        self.userpath = os.path.join(self.iniPar['path_SMC'], self.username)
        self.projname = None
        self.projpath = None
        self.dataname = None
        self.datapath = None
        self.rawpath = None
        self.p2rawpath = None
        self.scn_strat_custom = None
        
        # create user folder
        if not os.path.exists(self.userpath):
            try:
                os.makedirs(self.userpath)
            except FileNotFoundError:
                self.gui_popup('critical', 'Error!', 'Create user data:', 'Invalid path!')
                self.log.error('Invalid path!')
                self.gen_exit_app()
                raise SystemExit
        
        # update GUI
        self.log.info('{}'.format(aUserName))
        self.gui_update_title()
        self.usr_ch_proj_win()
    
    def usr_ch_proj(self, aProjectName):
        self.log.debug('{}'.format(aProjectName))
        
        if not aProjectName or not self.userpath:
            self.usr_ch_user_win()
            return
        
        # set vars
        self.projname = aProjectName
        self.projpath = os.path.join(self.userpath, self.projname)
        self.dataname = None
        self.datapath = None
        self.rawpath = None
        self.p2rawpath = None
        self.scn_strat_custom = None
        
        # create project folder
        # a subdirectory is assumed to be valid
        # as usr_ch_user checked self.userpath
        if not os.path.exists(self.projpath):
            os.makedirs(self.projpath)
        
        # update GUI
        self.log.info('{}'.format(aProjectName))
        self.gui_update_title()
        self.usr_ch_data_win()
        self.scn_strat_custom = self.dc_table_load(self.projpath, '*', return_default=False)
    
    def usr_ch_data(self, aDataFolder):
        self.log.debug('{}'.format(aDataFolder))
        
        if not aDataFolder or not self.userpath or not self.projpath:
            self.usr_ch_proj_win()
            return
        
        # set vars
        self.dataname = aDataFolder
        self.datapath = os.path.join(self.projpath, self.dataname)
        self.rawpath = os.path.join(self.datapath, self.rawdir)
        self.p2rawpath = os.path.join(self.iniPar['path_PH2'], self.username, self.projname, self.dataname, self.rawdir)
        
        # create data folders
        # a subdirectory is assumed to be valid
        # as usr_ch_user checked self.userpath
        if not os.path.exists(self.datapath):
            os.makedirs(self.datapath)
        if not os.path.exists(self.rawpath):
            os.makedirs(self.rawpath)
        
        # update GUI
        self.log.info('{}'.format(aDataFolder))
        self.gui_update_title()
        self.fv_process(None)
        
        # load strategy
        aStrategy = self.dc_table_load(self.rawpath, self.projname, return_default=True)
        if aStrategy:
            self.dc_table_change(aStrategy)
    
    #----------------#
    #     General    #
    #----------------#
    
    def gen_stop(self):
        self.log.info('Called')
        self.flagStopDataCollection = True
        
        if self.SHIsConnected and self.SHIsOpen:
            self.log.info(' - Shutter')
            self.sh_close()
        
        if self.SMCIsConnected:
            self.log.info(' - SMC')
            self.smc_control_stop()
        
        if self.p2IsConnected:
            self.log.info(' - P2')
            self.p2_stop()
    
    def gen_wait(self, interval):
        self.log.debug('{}'.format(interval))
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(interval*1000, loop.quit)
        loop.exec_()
    
    def gen_conv_to_time(self, t):
        #self.log.debug('Called')
        '''
        '''
        m, s = divmod(t, 60)
        h, m = divmod(m, 60)
        if h > 0:
            x = 'h'
        elif m > 0:
            x = 'm'
        else:
            x = 's'
        return '%d:%02d:%02d %s' % (h, m, s, x)
    
    def gen_find_next_folder(self, suffix):
        self.log.debug('Called')
        counter = 1
        temp = '{}_{:>02}'.format(suffix, counter)
        while 1:
            counter += 1
            if counter > 99:
                self.gui_popup('Warning', 'Storage problem', 'So many folders!', 'Don\'t you think it\'s time to start a new project?')
                return
            if os.path.exists(os.path.join(self.projpath, temp)):
                temp = '{}_{:>02}'.format(suffix, counter)
            else:
                os.makedirs(os.path.join(self.projpath, temp))
                self.usr_ch_data(temp)
                return temp
    
    def gen_exit_app(self):
        self.log.debug('Called')
        '''
        Stops the motor and exit the application
        '''
        self.gen_stop()
        if self.SHIsConnected:
            self.sh_disconnect()
        if self.SMCIsConnected:
            self.smc_disconnect()
        if self.p2IsConnected:
            self.p2_disconnect()
        if self.cameraIsConnected:
            self.cam_disconnect()
        quit()
    
    def keyPressEvent(self, e):
        self.log.debug('{} {}'.format(e.key(), QtGui.QKeySequence(e.key()).toString()))
        '''
        '''
        if e.key() == QtCore.Qt.Key_Right:
            self.btn_cmp_phi_0.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.text())))
        elif e.key() == QtCore.Qt.Key_Left:
            self.btn_cmp_phi_1.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.text()) + 90.0))
        elif e.key() == QtCore.Qt.Key_Up:
            self.btn_cmp_phi_2.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.text()) + 180.0))
        elif e.key() == QtCore.Qt.Key_Down:
            self.btn_cmp_phi_3.clicked.connect(lambda: self.smc_control_goto(1, float(self.inp_phi.text()) - 90.0))
        elif e.key() == QtCore.Qt.Key_Space:
            self.btn_cmp_phi_inc.clicked.connect(lambda: self.smc_control_move(1, float(self.inp_pls.text())))
        #Return sends commands to SMC or P2 if widget is in focus
        if (e.key() == QtCore.Qt.Key_Enter or e.key() == QtCore.Qt.Key_Return) and QtWidgets.QApplication.focusWidget().objectName() == 'cbx_p2sendText':
            self.p2_send_cbx(self.cbx_p2sendText)
        elif (e.key() == QtCore.Qt.Key_Enter or e.key() == QtCore.Qt.Key_Return) and QtWidgets.QApplication.focusWidget().objectName() == 'cbx_SMCsendText':
            self.smc_control_send()
    
    def closeEvent(self, event):
        self.log.debug('Called')
        '''
        User clicks the 'x' mark in window
        '''
        self.gen_exit_app()
    
    #-----------------#
    #    Frameview    #
    #-----------------#
    
    def fv_update_params(self, cmap=None, vmin=None, vmax=None, save=False):
        self.FrameView.frameRedraw(cmap, vmin, vmax)
        self.log.debug('Called')
        if cmap:
            self.iniPar['fv_colormap'] = cmap
        if vmin:
            self.iniPar['fv_int_min'] = vmin
        if vmax:
            self.iniPar['fv_int_max'] = vmax
        if save:
            save_ini(self.iniPath, p=self.iniPar)
    
    def fv_process(self, aFrame=None):
        self.log.debug('Called')
        '''
         Is called by p2_imageReady
         this function only adds to a queue
        '''
        if self.username and self.projname and self.dataname:
            if aFrame is None:
                self.raw_files = glob.glob(os.path.normpath(os.path.join(self.rawpath, '*.raw')))
                if len(self.raw_files) > 0:
                    aPath = max(self.raw_files, key=os.path.getctime)
                    self.fv_process_queue_add(aPath)
                    # load exp_info
                    exp_info = self.fv_info_to_dict(aPath)
                    # check if exp_info has the keys
                    if {'axis_tth', 'axis_dxt', 'det_beam_x', 'det_beam_y'} <= exp_info.keys():
                        self.display_tth = float(exp_info['axis_tth'])
                        self.display_dxt = float(exp_info['axis_dxt'])
                        self.display_bc = np.array([int(exp_info['det_beam_x']), int(exp_info['det_beam_y'])])
                    else:
                        self.display_tth = None
                        self.display_dxt = None
                        self.display_bc = None
                else:
                    self.FrameView.frameInit()
                    self.groupBoxImage.setTitle('None')
            else:
                aPath = os.path.normpath(os.path.join(self.rawpath, aFrame))
                self.fv_process_queue_add(aPath)
    
    def fv_info_to_dict(self, framePath):
        infoPath = '{}.info'.format(framePath[::-1].split('_', 1)[1][::-1])
        if os.path.exists(infoPath):
            with open(infoPath) as of:
                return {k:v for k,v in (item.split(':') for item in of.readlines())}
        else:
            return False
    
    def fv_process_queue_add(self, aFrame):
        self.log.debug('Called')
        # add frame to queue
        self.frame_queue.append(aFrame)
        # if frameQueueThread is not running start it
        if self.fv_pool.activeThreadCount() == 0:
            self.frameQueueThread = Threading(self.fv_process_queue, fn_args=[], fn_kwargs={})
            self.fv_pool.start(self.frameQueueThread)
        #print(self.frameQueueThread)
    
    def fv_process_queue(self, timeout=500, max_retries=20):
        self.log.debug('Called')
        '''
         Try to read/process an image, the transfer
         delay from the Photon2 to the Server varies
         but 5 seconds (timeout*max_retries) should
         be more than enough. Unfinished images
         (by stopping the data acquisition) need to
         be kicked out of the image queue, hence the
         limit.
        '''
        retries = 0
        # process the queue until empty or max_retries reached
        while len(self.frame_queue) > 0 and retries <= max_retries:
            aFrame = self.frame_queue[0]
            # frameUpdate() returns True if image is successfully read
            if self.FrameView.frameUpdate(aFrame):
                aFrame = self.frame_queue.pop(0)
                self.FrameView.draw_poi(self.display_bc, self.display_dxt, self.display_tth,
                                        size=self.iniPar['fv_poi_size'],
                                        max_pks=self.iniPar['fv_poi_num'],
                                        min_dist=self.iniPar['fv_poi_dist'],
                                        thresh_res=self.iniPar['fv_poi_res'],
                                        thresh_int=self.iniPar['fv_poi_int'])
                self.display_img = aFrame
                self.groupBoxImage.setTitle(os.path.basename(aFrame))
                if self.iniPar['use_conversion']:
                    fn_kwargs = {'cutoff':-64, 'overwrite':True}
                    fn_args = [aFrame, self.datapath]
                    convert_frame(*fn_args, **fn_kwargs)
                    retries = 0
                self.log.debug(os.path.basename(aFrame))
            else:
                # wait a little and try again
                loop = QtCore.QEventLoop()
                QtCore.QTimer.singleShot(timeout, loop.quit)
                loop.exec_()
                retries += 1
        # empty the queue, get rid of corrupted remainders
        self.frame_queue = []
        return True
    
    def fv_toolbar_visible(self):
        self.log.debug('Called')
        if self.widgetFrameToolbar.isVisible():
            self.widgetFrameToolbar.hide()
        else:
            self.widgetFrameToolbar.setEnabled(True)
            self.widgetFrameToolbar.show()
    
    def fv_toolbar_home(self):
        self.log.debug('Called')
        self.FrameView.toolbar.home()
    
    def fv_toolbar_zoom(self):
        self.log.debug('Called')
        self.fv_toggle_toolbar(self.btn_frm_zoom)
        self.btn_frm_pan.setChecked(False)
        self.FrameView.toolbar.zoom()
    
    def fv_toolbar_pan(self):
        self.log.debug('Called')
        self.fv_toggle_toolbar(self.btn_frm_pan)
        self.btn_frm_zoom.setChecked(False)
        self.FrameView.toolbar.pan()
    
    def fv_toolbar_browse(self, idx):
        self.log.debug('Called')
        '''
         1 - if current image is in image list -> use fwd and bwd to
             find the next/previous index and load the image
         2 - if not, read the .raw data in self.rawpath and goto 1
        '''
        # if img not in current list of images
        # read in the folder
        if self.display_img not in self.raw_files:
            self.raw_files = glob.glob(os.path.normpath(os.path.join(self.rawpath, '*.raw')))
        try:
            # display image at new index
            current_idx = self.raw_files.index(self.display_img)
            if 0 <= idx + current_idx < len(self.raw_files):
                self.fv_process_queue_add(self.raw_files[idx+current_idx])
            return True
        except ValueError:
            # image is not in list
            return False
    
    def fv_toggle_poi(self):
        self.log.debug('Called')
        if self.display_poi:
            self.display_poi = False
            self.FrameView.display_poi = False
        else:
            self.display_poi = True
            self.FrameView.display_poi = True
        self.FrameView.draw_poi(self.display_bc, self.display_dxt, self.display_tth,
                                size=self.iniPar['fv_poi_size'],
                                max_pks=self.iniPar['fv_poi_num'],
                                min_dist=self.iniPar['fv_poi_dist'],
                                thresh_res=self.iniPar['fv_poi_res'],
                                thresh_int=self.iniPar['fv_poi_int'])
    
    def fv_toggle_toolbar(self, buttonObject):
        self.log.debug('Called')
        if buttonObject.isChecked():
            buttonObject.setChecked(True)
        else:
            buttonObject.setChecked(False)
    
    #-----------------------#
    #    Data Collection    #
    #-----------------------#
    
    def dc_table_build(self):
        self.log.debug('Called')
        '''
         - CANNOT HANDLE MISSING HEADER ITEMS!
         - REQUIRES SYMMETRIC DICT!
        '''
        # general table setup
        self.tbl_scn_mat.setAlternatingRowColors(True)
        self.tbl_scn_mat.horizontalHeader().setVisible(True)
        #self.tbl_scn_mat.horizontalHeader().setCascadingSectionResizes(True)
        self.tbl_scn_mat.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        #self.tbl_scn_mat.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tbl_scn_mat.horizontalHeader().setDefaultSectionSize(55)
        #self.tbl_scn_mat.horizontalHeader().setMinimumSectionSize(20)
        self.tbl_scn_mat.horizontalHeader().setSortIndicatorShown(False)
        self.tbl_scn_mat.horizontalHeader().setStretchLastSection(False)
        self.tbl_scn_mat.horizontalHeader().sectionDoubleClicked.connect(lambda: self.dc_table_setcol())
        self.tbl_scn_mat.verticalHeader().setVisible(True)
        self.tbl_scn_mat.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        #self.tbl_scn_mat.verticalHeader().setCascadingSectionResizes(True)
        #self.tbl_scn_mat.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        #self.tbl_scn_mat.verticalHeader().setDefaultSectionSize(20)
        #self.tbl_scn_mat.verticalHeader().setMinimumSectionSize(20)
        self.tbl_scn_mat.verticalHeader().setSortIndicatorShown(False)
        self.tbl_scn_mat.verticalHeader().setStretchLastSection(False)
        self.tbl_scn_mat.verticalHeader().sectionDoubleClicked.connect(lambda: self.dc_table_setrow())
        self.dc_table_update()
    
    def dc_table_update(self):
        self.log.debug('Called')
        
        # check if there is a strategy
        if not self.scn_strat_active:
            return False
        
        # block table while writing
        self.tbl_scn_mat.blockSignals(True)
        
        # font definitions
        font_bold = QtGui.QFont()
        font_bold.setStrikeOut(False)
        font_bold.setBold(True)
        font_bold.setWeight(75)
        
        font_error = QtGui.QFont()
        font_error.setStrikeOut(True)
        font_error.setBold(True)
        font_error.setWeight(75)

        # build generic table from dict
        # - rows: len( dict.keys() )
        # - cols: len( list(dict.valus())[0] )
        self.tbl_scn_mat.setRowCount(len(self.scn_strat_active))
        if len(self.scn_strat_active) > 0:
            self.tbl_scn_mat.setColumnCount(len(self.scn_strat_active[0]))
        else:
            self.tbl_scn_mat.setColumnCount(0)
        
        runTimeList = []
        
        # fill table, rows first
        for row, parDict in enumerate(self.scn_strat_active):
            run_num = row + 1
            # set row header, name = run
            item = QtWidgets.QTableWidgetItem()
            self.tbl_scn_mat.setVerticalHeaderItem(row, item)
            # runs should start with 1 not 0
            self.tbl_scn_mat.verticalHeaderItem(row).setText('{:>02}'.format(run_num))
            self.tbl_scn_mat.verticalHeaderItem(row).setFont(font_bold)
            self.tbl_scn_mat.verticalHeaderItem(row).setTextAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
            self.tbl_scn_mat.verticalHeaderItem(row).setToolTip('Double click to copy and append the current line if checked.\nRemove line on double click if unchecked.')
            # fill table, columns
            for col, nam in enumerate(parDict):
                # set row header, name = nam
                item = QtWidgets.QTableWidgetItem()
                self.tbl_scn_mat.setHorizontalHeaderItem(col, item)
                self.tbl_scn_mat.horizontalHeaderItem(col).setText(nam)
                self.tbl_scn_mat.horizontalHeaderItem(col).setFont(font_bold)
                self.tbl_scn_mat.horizontalHeaderItem(col).setTextAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
                # generate cell entry, value = self.scn_strat_active[row][nam]
                entry = QtWidgets.QTableWidgetItem()
                entry.setText(str(parDict[nam]))
                entry.setFont(font_bold)
                entry.setForeground(self.brushEnabled)
                entry.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsDropEnabled|QtCore.Qt.ItemIsEnabled)
                self.tbl_scn_mat.horizontalHeaderItem(col).setToolTip('Double click on header to change column.')
                if nam == '':
                    entry.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
                    if type(parDict[nam]) == bool and parDict[nam]:
                        entry.setCheckState(QtCore.Qt.Checked)
                        row_is_active = True
                    else:
                        entry.setCheckState(QtCore.Qt.Unchecked)
                        row_is_active = False
                    entry.setTextAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
                    self.tbl_scn_mat.setColumnWidth(col, 20)
                else:
                    entry.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                # mark invalid entries
                if nam in self.gon_num_from_name and not self.smc_validate_pos(self.gon_num_from_name[nam], entry.text(), show_popup=False):
                    entry.setData(QtCore.Qt.ForegroundRole, QtGui.QColor(220,20,60,255))
                    entry.setFont(font_error)
                # mark active run
                if run_num == self.dc_activeRun:
                    entry.setData(QtCore.Qt.BackgroundRole, QtGui.QBrush(QtGui.QColor(0,171,164,50)))
                if row_is_active and nam in ['Exposure', 'Range']:
                    runTimeList.append(float(entry.text()))
                # set cell value at row, col to entry
                self.tbl_scn_mat.setItem(row, col, entry)
        expTimeInSecs = int(np.sum(np.array(runTimeList[::2])*np.array(runTimeList[1::2])))
        self.dc_table_update_time(expTimeInSecs)
        # clear selection
        self.tbl_scn_mat.clearSelection()
        # unblock table
        self.tbl_scn_mat.blockSignals(False)
        return True
    
    def dc_table_update_time(self, seconds):
        self.log.debug('Called')
        '''
         - current date/time is only updated when called
        '''
        exptime = QtCore.QTime(0,0,0)
        self.dc_expTotalTime.setText(exptime.addSecs(seconds).toString(QtCore.Qt.ISODate))
        self.dc_expTotalTime.adjustSize()
        datetime = QtCore.QDateTime.currentDateTime().addSecs(seconds)
        self.dc_expEndTimeDate.setDateTime(datetime)
        self.dc_expEndTimeDate.adjustSize()
    
    def dc_table_setcol(self):
        self.log.debug('Called')
        header = self.tbl_scn_mat.horizontalHeaderItem(self.tbl_scn_mat.currentColumn()).text()
        value = self.tbl_scn_mat.currentItem().text()
        try:
            value, okPressed = QtWidgets.QInputDialog.getDouble(self, 'Set {}'.format(header),'Value:', float(value), decimals=2, flags=QtCore.Qt.WindowSystemMenuHint)# find reasonable: min=0.0, max=1000
            if okPressed:
                for run in self.scn_strat_active:
                    run[header] = float(value)
                self.dc_table_update()
        except ValueError:
            self.log.error('not a float: {}'.format(value))
            return
    
    def dc_table_setrow(self):
        self.log.debug('Called')
        row = self.tbl_scn_mat.currentItem().row()
        if self.scn_strat_active[row]['']:
            self.scn_strat_active.append(deepcopy(self.scn_strat_active[row]))
        elif len(self.scn_strat_active) > 1:
            self.scn_strat_active.pop(row)
        else:
            return
        self.dc_table_update()
    
    def dc_table_on_changed(self, item):
        self.log.debug('Called')
        new_val, row, col = item.text(), item.row(), item.column()
        run = self.scn_strat_active[row]
        nam, val = list(run.items())[col]
        if item.flags() & QtCore.Qt.ItemIsUserCheckable:
            if item.checkState() & QtCore.Qt.Checked:
                run[nam] = True
            else:
                run[nam] = False
        try:
            if new_val.upper() == 'NAN':
                raise ValueError
            run[nam] = float(new_val)
        except ValueError:
            pass
        self.dc_table_update()
    
    def dc_table_to_dict(self):
        self.log.debug('Called')
        # lock table while reading
        self.tbl_scn_mat.blockSignals(True)
        runDict = collections.OrderedDict()
        for row_num in range(self.tbl_scn_mat.rowCount()):
            current_run = collections.OrderedDict()
            is_active_run = True
            for col_num in range(self.tbl_scn_mat.columnCount()):
                hCol = self.tbl_scn_mat.horizontalHeaderItem(col_num).text()
                item = self.tbl_scn_mat.item(row_num, col_num)
                iText = item.text()
                if item.flags() & QtCore.Qt.ItemIsUserCheckable:
                    if item.checkState() & QtCore.Qt.Checked:
                        # don't add ('':True) to the list 
                        continue
                    # skip if row is not flagged
                    is_active_run = False
                    break
                current_run[hCol] = float(iText)
            if is_active_run:
                # runs should start with 1 not 0
                runDict[row_num+1] = current_run
        # unlock table
        self.tbl_scn_mat.blockSignals(False)
        return runDict
    
    def dc_table_validate(self, runDict, show_popup=True):
        self.log.debug('Called')
        #----------------------#
        #   Axes and Limits    #
        #----------------------#
        #self.gon_name_from_num = {1:'Phi',
        #                          2:'Chi',
        #                          3:'Omega',
        #                          4:'2-Theta',
        #                          5:'Distance',
        #                          6:'X',
        #                          7:'Y',
        #                          8:'Z'}
        #                 
        #self.gon_limits = {1:(  None,  None),
        #                   2:( -60.0,   0.0),
        #                   3:( -35.0,   0.0),
        #                   4:( -35.0,   0.0),
        #                   5:(-176.0, -80.0),
        #                   6:(  None,  None),
        #                   7:(  None,  None),
        #                   8:(  None,  None)}
        #
        # coupled goniometer limits
        # key : value
        # ax1 <= ax2
        #self.gon_limits_coupled = {4:3}
        
        req_pos = {}
        self.gon_num_from_name = {v:k for k,v in self.gon_name_from_num.items()}
        for (run_num, run) in runDict.items():
            self.log.debug('> {}'.format(run_num))
            for ax_nam, ax_val in run.items():
                self.log.debug('   {} {}'.format(ax_nam, ax_val))
                if ax_nam in self.gon_num_from_name.keys():
                    ax_num = self.gon_num_from_name[ax_nam]
                    limits = self.gon_limits[ax_num]
                    if None in limits:
                        continue
                    ax_val = float(ax_val)
                    lim_min = float(min(limits))
                    lim_max = float(max(limits))
                    if not lim_min <= ax_val <= lim_max:
                        if show_popup:
                            self.gui_popup('Warning', 'Positioning', 'Positioning error in run #{}!'.format(run_num), 'Target {} position is out of limits: {} [{}, {}]'.format(ax_nam, ax_val, lim_min, lim_max))
                        return False
                    req_pos[ax_num] = ax_val
            for (ax1, ax2) in self.gon_limits_coupled.items():
                if not req_pos[ax1] <= req_pos[ax2]:
                    if show_popup:
                        self.gui_popup('Warning', 'Positioning', 'Positioning error in run #{}!'.format(run_num), 'Target {0} position violates the coupled limit: {0} <= {1}'.format(self.gon_name_from_num[ax1], self.gon_name_from_num[ax2]))
                    return False
        # all fine
        return True
    
    def dc_table_save(self, aPath, aName, show_popup=True):
        self.log.debug('Called')
        
        myStratFile = '{}.runs'.format(os.path.join(aPath, aName))
        # pop up a message box asking to continue
        if show_popup and os.path.exists(myStratFile):
            self.gui_popup('Information', 'Save the current strategy to the project folder?', 'A strategy file already exists, overwrite?')
            
        with open(myStratFile, 'w') as ofile:
            ofile.write('#{}\n'.format(';'.join(map('{:>8}'.format, self.scn_strat_active[0].keys()))))
            for run in self.scn_strat_active:
                ofile.write(' {}\n'.format(';'.join(map('{:>8}'.format, run.values()))))
    
    def dc_table_load(self, lookupPath, fname, return_default=True):
        self.log.debug('Called')
        fnames = glob.glob('{}.runs'.format(os.path.join(lookupPath, fname)))
        if len(fnames) > 0 and os.path.exists(fnames[0]):
            myStratFile = fnames[0]
            myStrategy = []
            with open(myStratFile) as ofile:
                aList = ofile.readlines()
            for line in aList:
                d = collections.OrderedDict()
                if line.startswith('#'):
                    # line[1:] -> skip the '#'
                    headerItems = list(map(str.strip, line[1:].split(';')))
                    continue
                elif line.isspace():
                    continue
                else:
                    items = line.strip().split(';')
                    for num, item in enumerate(items):
                        value = item.strip()
                        if num == 0:
                            d[headerItems[num]] = bool(int(value))
                        else:
                            d[headerItems[num]] = float(value)
                    myStrategy.append(d)
            return myStrategy
        elif return_default and self.scn_strat_custom:
            return self.scn_strat_custom
        elif return_default:
            return self.scn_strat_default
        else:
            return None
    
    def dc_table_change(self, aStrategy):
        if aStrategy:
            self.scn_strat_active = aStrategy
            self.dc_table_update()
            return True
        else:
            aStrat = self.dc_table_load(self.projpath, '*', return_default=False)
            if aStrat:
                self.scn_strat_custom = aStrat
                self.dc_table_update()
                return True
            else:
                self.log.error('Error loading strategy!')
                return False
    
    def dc_info_save(self, run_nam, run_num, exp_info):
        self.log.debug('Called')
        '''
         
        '''
        with open('{}_{:02}.info'.format(os.path.join(self.rawpath, run_nam), run_num), 'w') as infoFile:
            l = ['{}:{}\n'.format(k, exp_info[k]) for k in exp_info]
            for i in sorted(l):
                infoFile.write(i)
    
    def dc_info_add(self, run_nam, run_num, exp_info):
        '''
         
        '''
        with open('{}_{:02}.info'.format(os.path.join(self.rawpath, run_nam), run_num), 'a') as infoFile:
            for i in sorted(['{}:{}\n'.format(k, exp_info[k]) for k in exp_info]):
                infoFile.write(i)
    
    def dc_remove_existing(self, runDict):
        # check folder for existing data
        for (run_num, run) in runDict.items():
            tmp = '{}_{:02}.info'.format(os.path.normpath(os.path.join(self.rawpath, self.projname)), run_num)
            if os.path.exists(tmp):
                tmp_case = 'Warning'
                tmp_title = 'Existing data conflict'
                tmp_text = 'The target folder contains data for the requested run #{:>02}.'.format(run_num)
                tmp_info = 'The respective data will be removed!'
                choice = self.gui_popup(tmp_case, tmp_title, tmp_text, tmp_info, show_cancel=True)
                
                if choice == QtWidgets.QMessageBox.Cancel:
                    # clean up since no data collection
                    # is like finished data collection
                    self.dc_setup_post()
                    return False
                else:
                    for entry in glob.glob('{}*'.format(os.path.splitext(tmp)[0])):
                        os.remove(entry)
                        self.log.warning('rem {}'.format(os.path.basename(entry)))
        return True
    
    def dc_collect_data(self):
        '''
         
        '''
        self.log.debug('Called')
        
        # read the run list into a dict
        runDict = self.dc_table_to_dict()
        
        # check the limits
        if not self.dc_table_validate(runDict, show_popup=True):
            return False
        
        #############################################
        ##                                         ##
        ## LAST CHANCE TO PREVENT DATA COLLECTION! ##
        ##                                         ##
        #############################################
        # if you RETURN from this function you MUST
        # call 'self.dc_setup_post()' to set the
        # GUI back to full functionality!
        if not self.dc_setup_pre():
            # clean up since no data collection
            # is like finished data collection
            self.dc_setup_post()
            return False
        #############################################
        
        # delete existing data
        # returns True if ok
        if not self.dc_remove_existing(runDict):
            self.dc_setup_post()
            return False
        
        # iterate over the runs
        for (run_num, run) in runDict.items():
            
            # break if stop button is pressed
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break

            ####################################
            ##          RUN DICT KEYS         ##
            ####################################
            #'Phi'     : Phi angle [deg]
            #'Chi'     : Chi angle [deg]
            #'Omega'   : Omega angle [deg]
            #'2-Theta' : 2-Theta angle [deg]
            #'Distance': Detector distance
            #'Exposure': Exposure time [s]
            #'Width'   : Frame width [deg/frame]
            #'Range'   : Scan range [deg]
            ####################################
            
            sec_deg = float(run['Exposure'])      # sec/deg
            deg_frm = float(run['Width'])         # deg/frame
            sec_frm = round(sec_deg * deg_frm, 2) # sec/frame
            sca_wth = float(run['Range'])         # deg
            frm_num = int((sec_deg * sca_wth) / sec_frm)
            
            # store distance and tth to draw correct
            # POI on the frame
            self.display_dxt = run['Distance']
            self.display_tth = run['2-Theta']
            self.display_bc = np.array([self.iniPar['det_beam_x'],self.iniPar['det_beam_y']])
            
            # set current run as active
            self.dc_activeRun = run_num
            # update the scanTable to
            # highlight the active run
            self.dc_table_update()
            
            # move Phi
            self.smc_control_goto_sync(1, run['Phi'], self.SMC.signal_IAmInPos)
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break
                
            # move Chi
            self.smc_control_goto_sync(2, run['Chi'], self.SMC.signal_IAmInPos)
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break

            # move Omega
            self.smc_control_goto_sync(3, run['Omega'], self.SMC.signal_IAmInPos)
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break

            # move 2-Theta
            self.smc_control_goto_sync(4, run['2-Theta'], self.SMC.signal_IAmInPos)
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break

            # move Detector
            self.smc_control_goto_sync(5, run['Distance'], self.SMC.signal_IAmInPos)
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break

            # if positioning is ready start a phi scan for every run in the table!
            # wait for the detector signal (p2sigAcquisitionDone)
            loop = QtCore.QEventLoop()
            #self.SMC.flag_special = True
            #self.SMC.signal_IAmSpecial.connect(loop.quit)
            self.p2Server.p2sigAcquisitionDone.connect(loop.quit)
            self.dc_setup_init(sec_frm, sec_deg, sca_wth, frm_num, run_num, self.projname, self.p2rawpath)
            self.log.debug('Waiting for p2sigAcquisitionDone')
            loop.exec_()
            
            # Bring the axes back
            # !!! Omega moves before 2-Theta !!!
            # This can crash if the axis are
            # not home after each run
            self.smc_go_home()
            
            # do not update the run list if it was aborted!
            if self.flagStopDataCollection:
                self.log.warning('flagStopDataCollection!')
                self.dc_setup_post()
                break
            
            # run finished
            # uncheck the completed row
            self.scn_strat_active[run_num-1][''] = False
            # update the scanTable to
            self.dc_table_update()
            # save data collection progress
            self.dc_table_save(self.rawpath, self.projname, show_popup=False)
            
            ## ADD THE P2 READY TRIGGER IN A WAIT LOOP
            # wait for one exposure time
            #self.gen_wait(float(sec_frm))
            
        # clean up after data collection
        self.dc_setup_post()
        
        # all done
        return True
    
    def dc_collect_simple(self):
        self.log.debug('Called')
        '''
         
        '''
        if all(self.scanParameterValid.values()) and self.p2IsConnected and self.SMCIsConnected and self.SHIsConnected:
            
            #############################################
            ##                                         ##
            ## LAST CHANCE TO PREVENT DATA COLLECTION! ##
            ##                                         ##
            #############################################
            if not self.dc_setup_pre():
                return False
            #############################################
            
            
            raw_dest = os.path.join(self.gen_find_next_folder('simple'), self.rawdir)
            # sca_spn_fre = Frame Exposure s/f
            sec_frm = self.sca_spn_fre.value()
            # sca_spn_rot = Rotation Time s/*
            sec_deg = self.sca_spn_rot.value()
            # sca_spn_scw = Scan Width *
            sca_wth = self.sca_spn_scw.value()
            # sca_spn_frn = # Frames
            frm_num = int(self.sca_spn_frn.value())
            # sca_spn_run = run number
            run_num = int(self.sca_spn_run.value())
            # sca_spn_bsn = run name
            run_nam = self.sca_spn_bsn.text()
            # let's go
            
            # if positioning is ready start a phi scan for every run in the table!
            loop = QtCore.QEventLoop()
            self.SMC.flag_special = True
            self.SMC.signal_IAmSpecial.connect(loop.quit)
            self.dc_setup_init(sec_frm, sec_deg, sca_wth, frm_num, run_num, run_nam, self.p2rawpath)
            self.log.debug('mW: wait for signal_IAmSpecial')
            loop.exec_()
            
            # Bring the axes back
            self.smc_go_home()
            
            # clean up after data collection
            self.dc_setup_post()
            
            # all done
            return True
        
        else:
            msgBox = QtWidgets.QMessageBox()
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(":/icons/question_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            msgBox.setWindowIcon(icon)
            msgBox.setIcon(QtWidgets.QMessageBox.Information)
            msgBox.setWindowTitle('Data Collection')
            msgBox.setText('Scan not allowed!')
            msgBox.setInformativeText('Check scan parameters and the connection to SMC / Photon2')
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            btnPressed = msgBox.exec()
            return False
    
    def dc_setup_pre(self):
        '''
         
        '''
        #############################################
        ##                                         ##
        ## LAST CHANCE TO PREVENT DATA COLLECTION! ##
        ##                                         ##
        #############################################
        # if there is no User yet, ask for a name
        if not self.username:
            self.usr_ch_user_win()
            return False
        
        # if there is no Project yet, ask for a name
        if not self.projname:
            self.usr_ch_proj_win()
            return False
        
        # check if todays logfile is present
        #################################
        ## WE'RE NOT USING A CRYO NOW  ##
        ## SET UP A INI FLAG TO TOGGLE ##
        #################################
        #self.cryoLogPath = os.path.join(self.iniPar['path_CRY'], 'log_811450_{}.csv'.format(datetime.now().strftime('%d%b%Y')))
        #if not self.cy_check_log(self.cryoLogPath):
        #    return False
        
        # set a flag to allow to stop a data collection
        self.flagStopDataCollection = False
        
        # pop up a message box asking to continue
        msgBox = QtWidgets.QMessageBox()
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/question_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        msgBox.setWindowIcon(icon)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setWindowTitle('Information')
        msgBox.setText('Start data collection?')
        msgBox.setInformativeText('Make sure to set the shutter switch to REMOTE CONTROL!')
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        btnPressed = msgBox.exec()
        
        if btnPressed == QtWidgets.QMessageBox.Cancel:
            return False
        
        # save current data collection strategy
        self.dc_table_save(self.rawpath, self.projname, show_popup=False)
        
        # disable scan table editing
        self.gui_toggle_dc_buttons(False)
        # disable data collection buttons
        # manually disable as the check function
        # gui_check_scan_enable would enable
        # when both P2 and SMC are connected
        self.btn_scn_mat_start.setEnabled(False)
        self.btn_scn_sim_start.setEnabled(False)
        
        # if no check returns False we're good
        return True
    
    def dc_setup_init(self, sec_frm, sec_deg, sca_wth, frm_num, run_num, run_nam, p2_raw_dest):
        self.log.debug('Called')
        # we need to store it for now
        # as dc_setup_on_trigger gets called by p2
        # and doesn't have this information
        # put the scan width into the
        # signal emitted by p2 when ready!
        self.scanWidth = sca_wth
        self.frameTime = 25600.0 / float(sec_deg)
        
        # send photon2 info
        self.p2_send_sync('SET EXPTIME {}'.format(float(sec_frm)), self.p2Server.p2sigMsgReceived)
        self.p2_send_sync('SET NUMFRAMES {}'.format(int(frm_num)), self.p2Server.p2sigMsgReceived)
        self.p2_send_sync('SET RUNNUMBER {}'.format(int(run_num)), self.p2Server.p2sigMsgReceived)
        self.p2_send_sync('SET BASENAME {}'.format(run_nam), self.p2Server.p2sigMsgReceived)
        self.p2_send_sync('SET DSTDIR {}'.format(p2_raw_dest), self.p2Server.p2sigMsgReceived)
        
        # save experiment info
        fra_wth = float((1.0 / sec_deg) * sec_frm)
        exp_info = {'scan_user':self.username,
                'scan_exposure':sec_frm,
                  'scan_frames':int(frm_num),
                     'scan_run':int(run_num),
                    'scan_name':run_nam,
                   'scan_range':float(sca_wth),
                   'scan_width':float(fra_wth),
                     'axis_phi':self.lcd_phi.value(),
                     'axis_chi':self.lcd_chi.value(),
                     'axis_omg':self.lcd_omg.value(),
                     'axis_tth':self.lcd_tth.value(),
                     'axis_dxt':self.lcd_dxt.value(),
                   'det_beam_x':self.iniPar['det_beam_x'],
                   'det_beam_y':self.iniPar['det_beam_y'],
                 'det_cor_roll':self.iniPar['det_cor_roll'],
                'det_cor_pitch':self.iniPar['det_cor_pitch'],
                  'det_cor_yaw':self.iniPar['det_cor_yaw'],
                 'det_cor_dist':self.iniPar['det_cor_dist']}
        self.dc_info_save(run_nam, run_num, exp_info)
        
        # stop?
        if self.flagStopDataCollection:
            self.log.warning('flagStopDataCollection!')
            self.dc_setup_post()
            return

        '''
         dc_setup_on_trigger gets called by a signal emitted from p2 when it is ready!
        '''
        self.p2_send_sync('START', self.p2Server.p2sigMsgReceived)
        self.log.info('Data collection initialized')
    
    def dc_setup_on_trigger(self):
        self.log.debug('Called')
        '''
         this gets called by a signal emitted from p2 when it is ready!
         connected to signal_IAmData
         can finish before P2 finished writing data (for short frame exposures)!
         Yes, this is bad! I do not know what causes the P2 to be too slow.
         sets the slew speed back to default after the signal arrived.
        '''
        self.log.info('Data collection started')
        # SMC: 25600 steps / degree
        # SMD: 25600 steps / second
        # NO ACCELERATION RAMP!
        # frun1 = ffast1 -> no acceleration
        # frun is able to speed-up without 
        # losing steps up to 4 degree/second
        # or maybe even more
        self.SMC.send_to_SMC('frun1:{}'.format(self.frameTime))
        self.SMC.send_to_SMC('ffast1:{}'.format(self.frameTime))
        
        # open the shutter
        self.sh_open()
        
        # Zero Go!
        self.SMC.flag_data = True
        self.smc_control_move_sync(axis=1, distance=float(self.scanWidth), anySignal=self.SMC.signal_IAmData)
        
        # close the shutter
        self.sh_close()
        
        # Set Phi slew speed to default
        #self.SMC.send_to_SMC('frun1:{}'.format(self.iniPar['ax_phi_frun']))
        #self.SMC.send_to_SMC('ffast1:{}'.format(self.iniPar['ax_phi_ffast']))
        self.adjust_phi_speed()
        
        # we're done
        if self.flagStopDataCollection:
            self.log.info('Data collection aborted')
        else:
            self.log.info('Data collection finished')
    
    def dc_setup_post(self):
        self.log.debug('Called')
        # set current run as active
        self.dc_activeRun = None
        # update the scanTable to
        # highlight the active run
        self.dc_table_update()
        # enable scan table editing
        self.gui_toggle_dc_buttons(True)
        # check if data collection buttons are allowed
        self.gui_check_scan_enable()
    
    #---------------#
    #    Shutter    #
    #---------------#
    
    def sh_connect(self):
        self.log.debug('Called')
        '''
         sh_open/close call the open/close function of SH_Connection
         the functions emit a signal, sh_on_status interprets 
        '''
        try:
            self.SHC = SH_Connection(self, self.iniPar['con_port_SHC'])
            # connect signals
            self.SHC.signal_shc_connection.connect(self.sh_on_connection)
            self.SHC.signal_shc_shutter.connect(self.sh_on_status)
            # open the connection
            self.SHC.run()
        except serial.serialutil.SerialException:
            self.gui_popup('critical', 'Error!', 'Shutter Connection:', 'Failed to establish the connection!')
            self.log.error('Error connecting to Shutter!')
    
    def sh_disconnect(self):
        self.log.debug('Called')
        if self.SHIsConnected:
            self.SHC.disconnect()
    
    def sh_open(self):
        self.log.debug('Called')
        if self.SHIsConnected:
            self.SHC.shutter_open()
    
    def sh_close(self):
        self.log.debug('Called')
        if self.SHIsConnected:
            self.SHC.shutter_close()
    
    def sh_on_connection(self, status):
        self.log.debug('Called')
        if status:
            self.log.info('Connected: Shutter')
            # set is connected flag
            self.SHIsConnected = True
        else:
            self.log.info('Disconnected: Shutter')
            # set is not connected flag
            self.SHIsConnected = False
        # check if scans are allowed
        self.gui_check_scan_enable()
    
    def sh_on_status(self, status):
        self.log.debug('Called')
        if status:
            self.log.warning('Shutter opened')
            # set shutter status flag
            self.SHIsOpen = True
        else:
            self.log.warning('Shutter closed')
            # set shutter status flag
            self.SHIsOpen = False
    
    #-----------#
    #    SMC    #
    #-----------#
    
    def smc_connect(self):
        self.log.debug('Called')
        '''
        '''
        try:
            self.SMC = SMC_Connection(self, self.iniPar['con_address_SMC'], self.iniPar['con_port_SMC'])
            self.SMCIsConnected = True
            self.SMC.signal_SMCUpdate.connect(self.gui_on_smc_update)
            self.SMC.signal_IAmReady.connect(lambda: self.gui_toggle_buttons(True))
            self.SMC.signal_IAmBusy.connect(lambda: self.gui_toggle_buttons(False))
            self.SMC.signal_SMCError.connect(self.smc_on_error)
            # Check that no axis is at a limit switch on startup
            self.SMC.signal_ELNegative.connect(self.gui_win_error)
            self.SMC.signal_ELPositive.connect(self.gui_win_error)
            self.SMC.run()
            self.SMC.signal_ELNegative.disconnect()
            self.SMC.signal_ELPositive.disconnect()
            # the EL signals need to be disconnected before initialize is ran
            # they are used for the limit-switch homing
            
            self.SMC.send_to_SMC('fn1:Phi')
            self.SMC.send_to_SMC('acc1:{}'.format(self.iniPar['ax_phi_acc']))
            self.SMC.send_to_SMC('dec1:{}'.format(self.iniPar['ax_phi_dec']))
            self.SMC.send_to_SMC('frun1:{}'.format(self.iniPar['ax_phi_frun']))
            self.SMC.send_to_SMC('ffast1:{}'.format(self.iniPar['ax_phi_ffast']))
            self.SMC.send_to_SMC('fn2:Chi')
            self.SMC.send_to_SMC('acc2:{}'.format(self.iniPar['ax_chi_acc']))
            self.SMC.send_to_SMC('dec2:{}'.format(self.iniPar['ax_chi_dec']))
            self.SMC.send_to_SMC('frun2:{}'.format(self.iniPar['ax_chi_frun']))
            self.SMC.send_to_SMC('ffast2:{}'.format(self.iniPar['ax_chi_ffast']))
            self.SMC.send_to_SMC('fn3:Omega')
            self.SMC.send_to_SMC('acc3:{}'.format(self.iniPar['ax_omg_acc']))
            self.SMC.send_to_SMC('dec3:{}'.format(self.iniPar['ax_omg_dec']))
            self.SMC.send_to_SMC('frun3:{}'.format(self.iniPar['ax_omg_frun']))
            self.SMC.send_to_SMC('ffast3:{}'.format(self.iniPar['ax_omg_ffast']))
            self.SMC.send_to_SMC('fn4:2-Theta')
            self.SMC.send_to_SMC('acc4:{}'.format(self.iniPar['ax_tth_acc']))
            self.SMC.send_to_SMC('dec4:{}'.format(self.iniPar['ax_tth_dec']))
            self.SMC.send_to_SMC('frun4:{}'.format(self.iniPar['ax_tth_frun']))
            self.SMC.send_to_SMC('ffast4:{}'.format(self.iniPar['ax_tth_ffast']))
            self.SMC.send_to_SMC('fn5:Distance')
            self.SMC.send_to_SMC('acc5:{}'.format(self.iniPar['ax_dxt_acc']))
            self.SMC.send_to_SMC('dec5:{}'.format(self.iniPar['ax_dxt_dec']))
            self.SMC.send_to_SMC('frun5:{}'.format(self.iniPar['ax_dxt_frun']))
            self.SMC.send_to_SMC('ffast5:{}'.format(self.iniPar['ax_dxt_ffast']))
            self.SMC.send_to_SMC('fn6:CrX')
            self.SMC.send_to_SMC('fn7:CrY')
            self.SMC.send_to_SMC('fn8:CrZ')
            
            self.SMC.send_to_SMC('blp1:{}'.format(self.iniPar['ax_phi_blp']))
            self.SMC.send_to_SMC('bln1:{}'.format(self.iniPar['ax_phi_bln']))
            self.SMC.send_to_SMC('blp2:{}'.format(self.iniPar['ax_chi_blp']))
            self.SMC.send_to_SMC('bln2:{}'.format(self.iniPar['ax_chi_bln']))
            self.SMC.send_to_SMC('blp3:{}'.format(self.iniPar['ax_omg_blp']))
            self.SMC.send_to_SMC('bln3:{}'.format(self.iniPar['ax_omg_bln']))
            self.SMC.send_to_SMC('blp4:{}'.format(self.iniPar['ax_tth_blp']))
            self.SMC.send_to_SMC('bln4:{}'.format(self.iniPar['ax_tth_bln']))
            self.SMC.send_to_SMC('blp5:{}'.format(self.iniPar['ax_dxt_blp']))
            self.SMC.send_to_SMC('bln5:{}'.format(self.iniPar['ax_dxt_bln']))
            
            self.btn_ls_phi.setStyleSheet(self.style_btn_ls_ready)
            self.btn_ls_chi.setStyleSheet(self.style_btn_ls_ready)
            self.btn_ls_omg.setStyleSheet(self.style_btn_ls_ready)
            self.btn_ls_tth.setStyleSheet(self.style_btn_ls_ready)
            self.btn_ls_dxt.setStyleSheet(self.style_btn_ls_ready)
            
            # slow down phi is xys stage is mounted
            self.adjust_phi_speed()
            
            # home all axis on connection
            if self.iniPar['startup_home']:
                self.smc_find_home(show_popup=False)
            else:
                self.smc_go_home()
            
            # set initial button state
            self.action_SMC_connect.setEnabled(False)
            self.action_SMC_disconnect.setEnabled(True)
            self.action_SMC_home.setEnabled(True)
            self.action_SMC_idle.setEnabled(True)
            self.gui_check_scan_enable()
        except socket.timeout:
            self.gui_popup('critical', 'Error!', 'SMC Connection:', 'Timeout while trying to establish connection!')
            self.log.error('Timeout while trying to establish connection!')
        except OSError:
            self.gui_popup('critical', 'Error!', 'SMC Connection:', 'OSError while trying to establish connection!')
            self.log.error('OSError while trying to establish connection!')
    
    def smc_disconnect(self):
        self.log.debug('Called')
        '''
         
        '''
        try:
            if self.SMCIsConnected:
                self.SMC.send_to_SMC('stop')
                #go back to home positions
                #self.smc_find_home()
                self.smc_go_home()
                #self.SMC.wait()
                self.SMC.terminate()
                self.SMC.SMC_socket.close()
            self.SMCIsConnected = False
            self.action_SMC_connect.setEnabled(True)
            self.action_SMC_disconnect.setEnabled(False)
            self.action_SMC_home.setEnabled(False)
            self.action_SMC_idle.setEnabled(False)
            self.btn_ls_phi.setStyleSheet(self.style_btn_ls_disconnected)
            self.btn_ls_chi.setStyleSheet(self.style_btn_ls_disconnected)
            self.btn_ls_omg.setStyleSheet(self.style_btn_ls_disconnected)
            self.btn_ls_tth.setStyleSheet(self.style_btn_ls_disconnected)
            self.btn_ls_dxt.setStyleSheet(self.style_btn_ls_disconnected)
            self.gui_toggle_buttons(False)
            self.gui_stop_disable()
            self.gui_check_scan_enable()
            self.log.info('Disconnected: SMC')
        except socket.timeout:
            self.gui_popup('Warning', 'Connection', 'SMC connection: timeout')
        except OSError:
            self.gui_popup('Warning', 'Connection', 'SMC connection: OSError')
    
    def smc_validate_axis(self, axis=0):
        try:
            axis = int(axis)
            return True
        except ValueError:
            self.log.warning('Axis numbers need to be integers!'.format(axis))
        if axis not in self.gon_name_from_num.keys():
            self.log.warning('Invalid axis: {}'.format(axis))
            return False
    
    def smc_on_dependent(self, target, val1, val2, op, isType = None):
        #self.log.debug('Called')
        '''
        '''
        if op == '/':
            result = float(val1) / float(val2)
        elif op == '*':
            result = float(val1) * float(val2)
        
        typeIsValid = True
        if isType == 'float':
            if not isinstance(result, float):
                typeIsValid = False
        elif isType == 'int':
            """
             round to 6 digits and check if its an integer!
            """
            if not round(result, 6).is_integer():
                typeIsValid = False
        
        if result > target.maximum() or result < target.minimum() or not typeIsValid:
            target.setStyleSheet('QDoubleSpinBox {background-color: rgb(250, 250, 250); color: rgb(255, 120, 120)}')
            target.setValue(result)
            self.scanParameterValid[target.objectName()] = False
        else:
            target.setStyleSheet('QDoubleSpinBox {background-color: rgb(250, 250, 250); color: rgb(  120, 120, 120)}')
            target.setValue(result)
            self.scanParameterValid[target.objectName()] = True
    
    def smc_validate_pos(self, ax_num, ax_val, show_popup=True):
        self.log.debug('{} {}'.format(ax_num, ax_val))
        ax_val = float(ax_val)
        limits = self.gon_limits[ax_num]
        if None in limits:
            return True
        lim_min = min(limits)
        lim_max = max(limits)
        if not lim_min <= ax_val <= lim_max:
            if show_popup:
                ax_nam = self.gon_name_from_num[ax_num]
                self.gui_popup('Warning', 'Positioning error!', 'Target {} position is out of limits: {} [{}, {}]'.format(ax_nam, ax_val, lim_min, lim_max))
            return False
        return True
    
    def smc_find_home(self, show_popup=True):
        self.log.info('Called')
        #######################################################
        ## !!! ALWAYS HOME 2-THETA IN POSITIVE DIRECTION !!! ##
        ##          home omega in positive direction         ##
        ##      home chi (negative), home phi (positive)     ##
        ##                   4 -> 3 -> 2 -> 1                ##
        #######################################################
        if show_popup:
            notify = self.gui_popup('Information', 'Positioning', 'Finding my way home!', blocking=False)
        # DXT
        self.log.info(' - Distance')
        self.smc_control_home_DXT(5, self.iniPar['ax_dxt_offset'], show_popup=False)
        #self.gen_wait(0.25)
        # TTH
        self.log.info(' - 2-Theta')
        self.smc_control_home_AXS(4, '+', self.iniPar['ax_tth_offset'])
        #self.gen_wait(0.25)
        # OMG
        self.log.info(' - Omega')
        self.smc_control_home_AXS(3, '+', 0.0)
        #self.gen_wait(0.25)
        # CHI
        self.log.info(' - Chi')
        self.smc_control_home_AXS(2, '-', 0.0)
        #self.gen_wait(0.25)
        # PHI
        self.log.info(' - Phi')
        self.smc_control_home_AXS(1, '+', 0.0)
        #self.gen_wait(0.25)
    
    def smc_go_home(self, show_popup=False):
        self.log.info('Called')
        # Bring axes back
        if show_popup:
            notify = self.gui_popup('Information', 'Positioning', 'Going home!', blocking=False)
        # Distance
        self.smc_control_goto_sync(5, self.iniPar['ax_dxt_offset'], self.SMC.signal_IAmInPos)
        # 2-Theta
        self.smc_control_goto_sync(4, self.iniPar['ax_tth_offset'], self.SMC.signal_IAmInPos)
        # Omega
        self.smc_control_goto_sync(3, self.iniPar['ax_omg_offset'], self.SMC.signal_IAmInPos)
        # Chi
        self.smc_control_goto_sync(2, self.iniPar['ax_chi_offset'], self.SMC.signal_IAmInPos)
        # Phi
        self.smc_control_goto_sync(1, self.iniPar['ax_phi_offset'], self.SMC.signal_IAmInPos)
    
    def smc_on_error(self):
        self.log.debug('Called')
        # pop up a message box asking to continue
        msgBox = QtWidgets.QMessageBox()
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/question_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        msgBox.setWindowIcon(icon)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setWindowTitle('SMC REPORTS ERROR')
        msgBox.setText('CALL FOR PETER, LOUD AND FAST!!!')
        # SAY WHICH AXIS IT IS
        msgBox.setInformativeText('')
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        btnPressed = msgBox.exec()
    
    def smc_align_home_select(self, direction='-', axis=0):
        self.log.debug('{}{}'.format(direction, axis))
        '''
        '''
        if self.home_pos_rdo.isChecked():
            direction = '+'
        elif self.home_neg_rdo.isChecked():
            direction = '-'
        
        if self.home_phi_rdo.isChecked():
            axis = 1
        elif self.home_chi_rdo.isChecked():
            axis = 2
        elif self.home_omg_rdo.isChecked():
            axis = 3
        elif self.home_tth_rdo.isChecked():
            axis = 4
        return axis, direction
    
    def smc_align_axis_select(self):
        self.log.debug('Called')
        '''
        '''
        if self.rdo_sax_phi.isChecked():
            activeAxis = 1
        elif self.rdo_sax_chi.isChecked():
            activeAxis = 2
        elif self.rdo_sax_omg.isChecked():
            activeAxis = 3
        elif self.rdo_sax_tth.isChecked():
            activeAxis = 4
        elif self.rdo_sax_dxt.isChecked():
            activeAxis = 5
        return activeAxis
    
    def smc_align_relabel(self, axis):
        self.log.debug('{}'.format(axis))
        '''
        '''
        try:
            if axis == 1:
                self.btn_cmp_phi_0.setText('Phi\n{:}'.format(float(self.inp_phi.text())))
                self.btn_cmp_phi_1.setText('Phi\n{:}'.format(float(self.inp_phi.text()) + 90.0))
                self.btn_cmp_phi_2.setText('Phi\n{:}'.format(float(self.inp_phi.text()) + 180.0))
                self.btn_cmp_phi_3.setText('Phi\n{:}'.format(float(self.inp_phi.text()) - 90.0))     
            elif axis == 2:
                self.btn_cmp_chi_0.setText('Chi\n{:}'.format(float(self.inp_chi.text())))
                self.btn_cmp_chi_1.setText('Chi\n{:}'.format(float(self.inp_chi.text()) - 20.0))
                self.btn_cmp_chi_2.setText('Chi\n{:}'.format(float(self.inp_chi.text()) - 40.0))
                self.btn_cmp_chi_3.setText('Chi\n{:}'.format(float(self.inp_chi.text()) - 60.0))
            elif axis == 3:
                pass
            elif axis == 4:
                pass
            elif axis == 5:
                pass
            elif axis == -1:
                self.btn_cmp_phi_inc.setText('Phi\n{:+}'.format(float(self.inp_pls.text())))
        except ValueError:
            return
    
    #---------------------#
    #    SMC - Control    #
    #---------------------#
    # - goto and goto_sync are limit checked
    # - move and move_sync are currently NOT
    
    def smc_control_stop(self):
        self.log.debug('Called')
        # stop the motors
        self.SMC.send_to_SMC('stop')
        # reset phi slew speed
        #self.SMC.send_to_SMC('frun1:{}'.format(self.iniPar['ax_phi_frun']))
        #self.SMC.send_to_SMC('ffast1:{}'.format(self.iniPar['ax_phi_ffast']))
        self.adjust_phi_speed()
        # do the after data collection cleanup!
        self.dc_setup_post()
    
    def smc_control_run_pos(self, axis=0):
        self.log.debug('{}'.format(axis))
        '''
        Run motor forward (positive)
        '''
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('run {} forward'.format(self.gon_name_from_num[axis]))
        self.SMC.send_to_SMC('run{}+'.format(axis))
        self.SMC.start()
    
    def smc_control_run_neg(self, axis=0):
        self.log.debug('{}'.format(axis))
        '''
        Run motor forward (positive)
        '''
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('run {} backward'.format(self.gon_name_from_num[axis]))
        self.SMC.send_to_SMC('run{}-'.format(axis))
        self.SMC.start()
    
    def smc_control_fast_pos(self, axis=0):
        self.log.debug('{}'.format(axis))
        '''
        Run motor forward (positive)
        '''
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('fast {} forward'.format(self.gon_name_from_num[axis]))
        self.SMC.send_to_SMC('fast{}+'.format(axis))
        self.SMC.start()
    
    def smc_control_fast_neg(self, axis=0):
        self.log.debug('{}'.format(axis))
        '''
        Run motor backward (negative)
        '''
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('fast {} backward'.format(self.gon_name_from_num[axis]))
        self.SMC.send_to_SMC('fast{}-'.format(axis))
        self.SMC.start()
    
    def smc_control_step_pos(self, axis=0):
        self.log.debug('{}'.format(axis))
        '''
        Move motor one increment forward
        '''
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('step {} forward (+)'.format(self.gon_name_from_num[axis]))
        self.SMC.send_to_SMC('step{}:1'.format(axis))
        self.SMC.start()
    
    def smc_control_step_neg(self, axis=0):
        self.log.debug('{}'.format(axis))
        '''
        Move motor one increment backward
        '''
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('step {} backward (-)'.format(self.gon_name_from_num[axis]))
        self.SMC.send_to_SMC('step{}:-1'.format(axis))
        self.SMC.start()
    
    def smc_control_goto(self, axis=0, position=0.0):
        self.log.debug('Called')
        # Check if target position is allowed
        if self.smc_validate_pos(axis, position, show_popup=True) is not True:
            return False
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Check target position
        position = float(position)
        # Start positioning
        self.log.debug('{} {} {}'.format(axis, self.gon_name_from_num[axis], position))
        self.SMC.send_to_SMC('goto{}:{}'.format(axis, position))
        self.SMC.start()
    
    def smc_control_move(self, axis=0, distance=0.0):
        self.log.debug('{} {} {}'.format(axis, self.gon_name_from_num[axis], distance))
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Check distance
        distance = float(distance)
        # Start positioning
        self.SMC.send_to_SMC('move{}:{}'.format(axis, distance))
        self.SMC.start()
    
    def smc_control_home(self, axis=0, direction='-'):
        self.log.debug('{} {}'.format(axis, direction))
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Check direction
        direction = str(direction)
        if direction not in ['-', '+']:
            self.log.error('Invalid direction [+,-]: {}'.format(direction))
            return False
        # Start positioning
        self.log.debug('smc_control_home {}, direction {}'.format(self.gon_name_from_num[axis], direction))
        self.SMC.send_to_SMC('org{}{}'.format(axis, direction))
        self.SMC.start()
    
    def smc_control_move_sync(self, axis=0, distance=0.0, anySignal=None):
        self.log.debug('{} {} {}'.format(axis, self.gon_name_from_num[axis], distance))
        '''
         - wrap a QEventLoop around smc_control_goto()
         - connect the loop.quit to anySignal
         - success: returns 0 if the positioning
                    finished successfully and 1
                    if interrupted by a Stop command
        '''
        # Check signal
        if anySignal is None:
            return False
        # connect signal and QEventLoop
        loop = QtCore.QEventLoop()
        anySignal.connect(loop.exit)
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Check distance
        ########################
        ## ADD CHECKFUNC HERE ##
        ########################
        distance = float(distance)
        ########################
        # Start positioning
        self.log.debug('move{}:{}'.format(axis, distance))
        self.SMC.send_to_SMC('move{}:{}'.format(axis, distance))
        self.SMC.start()
        self.log.debug('waiting for signal')
        success = loop.exec_()
        # Positioning done
        anySignal.disconnect()
        self.log.debug('signal arrived')
        return success
    
    def smc_control_goto_sync(self, axis=0, position=0.0, anySignal=None):
        self.log.debug('Called')
        '''
         - wrap a QEventLoop around smc_control_goto()
         - connect the loop.quit to anySignal
         - success: returns 0 if the positioning
                    finished successfully and 1
                    if interrupted by a Stop command
        '''
        # Check if target position is allowed
        if self.smc_validate_pos(axis, position, show_popup=True) is not True:
            return False
        # Check signal
        if anySignal is None:
            return False
        # connect signal and QEventLoop
        loop = QtCore.QEventLoop()
        anySignal.connect(loop.exit)
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Start positioning
        self.log.debug('goto{}:{}'.format(axis, float(position)))
        self.SMC.send_to_SMC('goto{}:{}'.format(axis, float(position)))
        self.SMC.start()
        self.log.debug('waiting for signal')
        success = loop.exec_()
        # Positioning done
        anySignal.disconnect()
        self.log.debug('signal arrived')
        return True
    
    def smc_control_home_sync(self, axis=0, direction='-', anySignal=None):
        self.log.debug('Called')
        # Check signal
        if anySignal is None:
            return False
        # connect signal and QEventLoop
        loop = QtCore.QEventLoop()
        anySignal.connect(loop.exit)
        # Check axis
        if self.smc_validate_axis(axis) is not True:
            return False
        # Check direction
        direction = str(direction)
        if direction not in ['-', '+']:
            self.log.error('Invalid direction [+,-]: {}'.format(direction))
            return False
        # Start positioning
        self.log.debug('Home {}, direction {}'.format(self.gon_name_from_num[axis], direction))
        self.SMC.send_to_SMC('org{}{}'.format(axis, direction))
        self.SMC.start()
        self.SMC.axisToHome = axis
        self.log.debug('waiting for signal')
        success = loop.exec_()
        # Positioning done
        anySignal.disconnect()
        self.log.debug('signal arrived')
        return success
    
    def smc_control_home_AXS(self, axis, direction, offset):
        self.log.debug('Called')
        if self.SMCIsConnected:
            #######################################################
            ## !!! ALWAYS HOME 2-THETA IN POSITIVE DIRECTION !!! ##
            ##          home omega in positive direction         ##
            ##                  home chi, home phi               ##
            ##                   4 -> 3 -> 2 -> 1                ##
            #######################################################
            
            # connect signal and QEventLoop
            loop = QtCore.QEventLoop()
            self.SMC.signal_IAmHome.connect(loop.exit)
            
            self.SMC.signal_ELPositive.connect(lambda: self.smc_control_home(axis, '-'))
            self.SMC.signal_ELNegative.connect(lambda: self.smc_control_home(axis, '+'))
            # Start positioning
            self.log.debug('LS-Home {}, direction {}'.format(self.gon_name_from_num[axis], direction))
            self.SMC.send_to_SMC('org{}{}'.format(axis, direction))
            self.SMC.axisToHome = axis
            self.SMC.start()
            self.log.debug('waiting for signal')
            success = loop.exec_()
            self.log.debug('signal arrived')
            
            # disconnect the EL-switch signals
            self.SMC.signal_ELPositive.disconnect()
            self.SMC.signal_ELNegative.disconnect()
            
            # update the position, no motion should be performed
            self.SMC.send_to_SMC('pos{}:{}'.format(axis, offset))
            self.log.debug('pos{}:{}'.format(axis, offset))
            
            return success
    
    def smc_control_home_DXT(self, axis, zeroOffset, show_popup=True):
        self.log.debug('Called')
        '''
         - axis: integer, zeroOffset: float
        '''
        # only allowed if connected to the goniometer
        if self.SMCIsConnected:
            if show_popup == True:
                # pop up a message box asking to continue
                msgBox = QtWidgets.QMessageBox()
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/icons/question_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
                msgBox.setWindowIcon(icon)
                msgBox.setIcon(QtWidgets.QMessageBox.Information)
                msgBox.setWindowTitle('Limit-Switch Homing')
                msgBox.setText('Start the limit-switch homing of the detector?')
                msgBox.setInformativeText('')
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
                btnPressed = msgBox.exec()
                
                if btnPressed == QtWidgets.QMessageBox.Cancel:
                    return
            
            # slow down frun and ffast -> start and slew speed
            self.SMC.send_to_SMC('frun{}:{}'.format(axis, self.iniPar['ax_dxt_frun']))
            self.SMC.send_to_SMC('ffast{}:{}'.format(axis, self.iniPar['ax_dxt_home_fast']))
            # set the current position to zero
            self.SMC.send_to_SMC('pos{}:0.0'.format(axis))
            self.gen_wait(0.25)
            # move backwards until limit switch is active
            self.smc_control_move_sync(axis, -200.0, self.SMC.signal_ELNegative)
            # set the current position to 0.0
            #self.SMC.send_to_SMC('pos{}:0.0'.format(axis))
            self.gen_wait(0.25)
            # giving 'axisToHome' the axis number (5:Distance)
            # calls a routine in 'SMC' to stop the axis
            # motion as soon as the limit switch is no longer active
            self.SMC.axisToHome = axis
            # slow down frun and ffast -> start and slew speed
            self.SMC.send_to_SMC('frun{}:{}'.format(axis, self.iniPar['ax_dxt_frun']))
            self.SMC.send_to_SMC('ffast{}:{}'.format(axis, self.iniPar['ax_dxt_home_slow']))
            self.gen_wait(0.25)
            # move forward until the limit switch is no longer active
            # and wait till all axis have stopped (signal_IAmSpecial)
            self.SMC.flag_special = True
            self.smc_control_move_sync(axis, 10.0, self.SMC.signal_IAmSpecial)
            # update the position, no motion should be performed
            self.SMC.send_to_SMC('pos{}:{}'.format(axis, zeroOffset))
            # set slew speed back to default
            self.gen_wait(0.25)
            self.SMC.send_to_SMC('frun{}:{}'.format(axis, self.iniPar['ax_dxt_frun']))
            self.SMC.send_to_SMC('ffast{}:{}'.format(axis, self.iniPar['ax_dxt_ffast']))
            self.SMC.start()
            self.log.debug('homing completed!')
    
    def smc_control_send(self):
        self.log.debug('Called')
        '''
        Send direct command to SMC
        '''
        self.log.debug('Command: {} sent...'.format(self.cbx_SMCsendText.currentText()))
        self.SMC.send_to_SMC(self.cbx_SMCsendText.currentText())
        self.cbx_SMCsendText.clearEditText()
        self.SMC.start()
    
    #----------------#
    #    PhotonII    #
    #----------------#
    
    def p2_connect(self):
        self.log.debug('Called')
        self.p2IsConnected = False
        self.p2Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.btn_p2IsConnected.setStyleSheet(self.style_btn_p2_pending)
        
        try:
            self.p2Socket.connect((self.iniPar['con_address_PH2'], self.iniPar['con_port_PH2']))
            whoIsIt = self.p2Socket.recv(4096).decode('ascii').strip()
            self.p2IsConnected = True
            #first msg is interpreted as 'who are you'!
            self.lne_p2IsConnected.setText(whoIsIt)
            #following msg is handled here
            #tell them who I am!
            self.p2Socket.send('ControlUnit'.encode())
            # p2Server
            self.p2Server = P2_Connection(self.p2Socket)
            # Signals
            #  interClass
            self.p2Server.p2sigDisconnected.connect(self.p2_disconnect)
            self.p2Server.p2sigMessage.connect(self.p2_onRecv)
            self.p2Server.p2sigImageReady.connect(self.p2_imageReady)
            self.p2Server.p2sigTriggerReady.connect(self.dc_setup_on_trigger)
            self.p2Server.p2sigError.connect(self.p2_error)
            self.p2Server.start()
            # Enable/Disable Buttons
            # Switch Connect/Disconnect buttons, layout
            self.btn_p2IsConnected.setStyleSheet(self.style_btn_p2_connected)
            self.action_P2_connect.setEnabled(False)
            self.action_P2_disconnect.setEnabled(True)
            self.action_P2_collect_darks.setEnabled(True)
            self.action_P2_stop.setEnabled(True)
            self.cbx_p2sendText.setEnabled(True)
            self.btn_p2SendText.setEnabled(True)
            self.gui_check_scan_enable()
            # write current time to log screen
            self.txt_p2Log.append('Connection established: {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            self.log.info('Connected: {}'.format(whoIsIt))
        except ConnectionRefusedError:
            self.log.error('Connection refused')
            self.gui_popup('critical', 'Error!','Photon-II Connection', 'Connection refused')
        except socket.timeout:
            self.log.error('Socket timeout')
            self.gui_popup('critical', 'Error!','Photon-II Connection', 'Socket timeout')
        except OSError:
            self.log.error('Attempted to close blocking socket')
            self.gui_popup('critical', 'Error!','Photon-II Connection', 'Attempted to close blocking socket')
    
    def p2_disconnect(self):
        self.log.debug('Called')
        '''
        '''
        try:
            if self.p2IsConnected:
                try:
                    self.p2_send('QUIT')
                    self.p2Socket.close()
                    self.p2Server.terminate()
                    self.p2Server.wait()
                except socket.error:
                    # connection is already dead
                    pass
            self.p2IsConnected = False
            self.action_P2_connect.setEnabled(True)
            self.action_P2_disconnect.setEnabled(False)
            self.action_P2_collect_darks.setEnabled(False)
            self.action_P2_stop.setEnabled(False)
            self.gui_check_scan_enable()
            self.btn_p2IsConnected.setStyleSheet(self.style_btn_p2_disconnected)
            self.lne_p2IsConnected.setText('None')
            self.btn_p2SendText.setEnabled(False)
            self.cbx_p2sendText.setEnabled(False)
            self.cbx_p2sendText.clearEditText()
            self.p2_saveToLogFile()
            self.log.info('Disconnected: P2')
        except ConnectionRefusedError:
            self.gui_popup('Error', 'Connection', 'P2 connection: refused')
        except socket.timeout:
            self.gui_popup('Error', 'Connection', 'P2 connection: timeout')
        except OSError:
            self.gui_popup('Error', 'Connection', 'P2 connection: OSError')
    
    def p2_send(self, aStr):
        self.log.debug('{}'.format(aStr))
        self.p2Socket.send('{}'.format(aStr).encode())
    
    def p2_send_sync(self, aStr, aSignal):
        self.log.debug('{}'.format(aStr))
        '''
         - Uses a QEventLoop to synchronize!
         - 'p2sigMsgReceived' is the default
           response signal and is ALWAYS send by P2!
        '''
        loop = QtCore.QEventLoop()
        aSignal.connect(loop.quit)
        self.p2Socket.send('{}'.format(aStr).encode())
        loop.exec_()
    
    def p2_send_cbx(self, anyQComboBox):
        self.log.debug('Called')
        '''
         - a simple send text
         - currently used by:
           anySendFunction: self.p2Server.p2s_sendString
           anyQComboBox: self.cbx_p2sendText
        '''
        txtToSend = anyQComboBox.currentText()
        if not txtToSend or txtToSend.isspace():
            return
        self.p2Socket.send(anyQComboBox.currentText().encode())
        anyQComboBox.clearEditText()
    
    def p2_imageReady(self, aFrame):
        self.log.debug('{}'.format(aFrame))
        self.txt_p2Log.append('> {}'.format(aFrame))
        self.fv_process(aFrame)
    
    def p2_onRecv(self, anyString):
        self.log.debug('{}'.format(anyString))
        self.txt_p2Log.append('> {}'.format(anyString))
    
    def p2_error(self):
        self.log.debug('Called')
        # stop all
        self.gen_stop()
        # popup error message
        self.gui_popup('Error', 'Connection', 'Error in P2Util!', 'Please check/restart the P2Server')
        # bring the axes back home
        self.smc_go_home()
    
    def p2_stop(self):
        self.log.debug('Called')
        self.p2_send('STOP')
    
    def p2_collectNewDarkFrames(self):
        self.log.debug('Called')
        self.p2_send_sync('COLLECT_DARK_FRAMES', self.p2Server.p2sigMsgReceived)
    
    def p2_saveToLogFile(self):
        self.log.debug('Called')
        '''
        '''
        if len(self.txt_p2Log.toPlainText()) > 51:
            with open('p2Server.log', 'a') as logFile:
                logFile.write('# log file from {}\n{}\n\n'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.txt_p2Log.toPlainText()))
            self.txt_p2Log.setPlaceholderText('Log saved to file!')
        self.txt_p2Log.clear()
    
    #------------------------#
    #    Frame conversion    #
    #------------------------#
    
    def fc_getFramePathList(self):
        self.log.debug('Called')
        try:
            return sorted(glob.glob(os.path.join(self.rawpath, '*_*_*.raw'), recursive=True))
        except TypeError:
            return []
    
    def fc_prepare(self):
        self.log.debug('Called')
        '''
        
        '''

        ###############################
        ##   SLOPPY IMPLEMENTATION   ##
        ##  WILL CRASH IF 1st ENTRY  ##
        ##    IS MISSING FROM LOG    ##
        ###############################
        #frame_bdyHMS = datetime.fromtimestamp(os.path.getmtime(fname)).strftime('%b %d %Y %H:%M:%S')
        #frame_dby = datetime.fromtimestamp(os.path.getmtime(fname)).strftime('%d%b%Y')
        #if current_dby == frame_dby:
        #    pass
        #else:
        #    current_dby = frame_dby
        #    newPathToLog = os.path.join(self.iniPar['path_CRY'], 'log_811450_{}.csv'.format(frame_dby))
        #    if not os.path.exists(newPathToLog):
        #        frameTemp = 300.0
        #    else:
        #        cryoLog = self.cy_read_log(newPathToLog)
        #
        #try:
        #    frameTemp = float(cryoLog[cryoLog[:,0] == frame_bdyHMS][0][1])
        #    lastTemp = frameTemp
        #except IndexError:# TypeError not initialized, IndexError: TIMESTAMP NOT IN THERE
        #        frameTemp = lastTemp
        ##defaultHeader['LOWTEMP'] = [1, int((frameTemp - 273.15) * 100.0), -6000] # Low temp flag; experiment temperature*100; detector temp*100
        #if frameTemp:
        #    defaultHeader['LOWTEMP'] = [1, int((-273.15 + frameTemp) * 100.0), -6000] # Low temp flag; experiment temperature*100; detector temp*100
        #else:
        #    self.log.debug('Error reading temperature: {}'.format(fname))
            

        if not self.username:
            self.usr_ch_user_win()
            return
            
        if not self.projname:
            self.usr_ch_proj_win()
            return
        
        if not self.dataname:
            self.usr_ch_data_win()
            return
        
        framePathList = self.fc_getFramePathList()
                
        # needed to track the conversion progress
        self.num_to_convert = len(framePathList)
        self.converted = []
        
        # check if there are any files
        if self.num_to_convert == 0:
            self.gui_popup('Information', 'Information', 'No suitable image files found.', 'Please check path.')
            return
            
        path_to, frame_name = os.path.split(framePathList[0])
        sfrmdir, rawdir = os.path.split(path_to)
        
        # check if the output directory exists
        if not os.path.exists(sfrmdir):
            os.mkdir(sfrmdir)
        
        self.progressBarFrameConvert.show()
        self.btn_scn_con_start.hide()
        
        fn_kwargs = {'cutoff':-64, 'overwrite':self.cbx_overWrite.isChecked()}
        # Now uses QRunnable and QThreadPool instead of multiprocessing.pool()
        self.pool = QtCore.QThreadPool()
        for fname in framePathList:
            fn_args = [fname, sfrmdir]
            worker = Threading(convert_frame, fn_args, fn_kwargs)
            worker.signals.finished.connect(self.fc_toolbar_toggle)
            self.pool.start(worker)
    
    def fc_toolbar_toggle(self, finished):
        self.converted.append(finished)
        num_converted = len(self.converted)
        progress = float(num_converted) / float(self.num_to_convert) * 100.0
        self.progressBarFrameConvert.setValue(progress)
        ##self.status = QtWidgets.QLabel()
        ##self.status.setAlignment(QtCore.Qt.AlignCenter)
        ##self.statusBar.addWidget(self.status, 1)
        ##self.status.setText('{}'.format(os.path.basename(self.datanameList[num_converted-1])))
        # conversion finished
        if num_converted == self.num_to_convert:
            self.currentFrameNameConvert.setText('Converted {} frames.'.format(np.count_nonzero(self.converted)))
            self.progressBarFrameConvert.hide()
            self.btn_scn_con_start.show()
    
    #--------------#
    #    Camera    #
    #--------------#
    
    def cam_connect(self):
        self.log.debug('Called')
        if self.cameraIsConnected:
            self.log.warning('Camera already initialized!')
            return
        
        try:
            self.camera = cameraDevice()
            self.log.info('Connected: Camera')
        except ValueError:
            self.cameraWidget.setText('Device not found!\n\nIs FFMPEG available?')
            self.log.error('Camera error!')
            return
        
        self.cam_thread = QtCore.QThread()
        self.camera.moveToThread(self.cam_thread)
        self.camera.frameReady.connect(self.cam_update)
        self.cam_thread.start()
        self.cameraIsConnected = True
    
    def cam_disconnect(self):
        self.log.debug('Called')
        self.camera.disconnect()
        self.cam_thread.exit()
        self.cameraIsConnected = False
        self.log.info('Disconnected: Camera')
    
    def cam_toggle(self, idx):
        self.log.debug('called: {}'.format(idx))
        if not self.cameraIsConnected:
            self.log.warning('No camera initialized!')
            return
        
        if idx == 1:
            self.camera.timer.start()
            self.log.debug('Camera started')
        else:
            self.camera.timer.stop()
            self.log.debug('Camera stopped')
    
    def cam_update(self, image):
        #self.log.debug('Called')
        pixmap = QtGui.QPixmap.fromImage(image).scaled(self.cameraWidget.size(), QtCore.Qt.KeepAspectRatio)
        self.cameraWidget.setPixmap(pixmap)
    
    #------------------#
    #    Cryostream    #
    #------------------#
    
    def cy_get_temp(self, cryoLogPath, timeStamp):
        self.log.debug('Called')
        # Read the Cryostream logfile
        # Return temperature
        # timeStamp format: Apr 18 2018 00:00:00
        # '{}'.format(datetime.now().strftime('%b %d %Y %H:%M:%S'))
        # column 0: timestamp, 44:sample temperature, 45:temperature error
        self.gen_wait(1.0)
        truncLog = np.genfromtxt(cryoLogPath, dtype=str, delimiter=',', skip_header=2, usecols=(0,44))
        if timeStamp in truncLog[:,0]:
            temp = truncLog[truncLog[:,0] == timeStamp][0][1]
            return temp
    
    def cy_check_log(self, cryoLogPath):
        self.log.debug('Called')
        '''
         CHECK TIMESTAMP WHEN EXPERIMENTS IS STARTED!
        '''
        if not os.path.exists(cryoLogPath):
            msgBox = QtWidgets.QMessageBox()
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(":/icons/question_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            msgBox.setWindowIcon(icon)
            msgBox.setIcon(QtWidgets.QMessageBox.Warning)
            msgBox.setWindowTitle('WARNING!')
            msgBox.setText('Cryostream logfile not found!')
            msgBox.setInformativeText('Please start the CryoConnector software.')
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgBox.exec()
            return False
        return True
    
    def cy_read_log(self, cryoLogPath):
        self.log.debug('Called')
        ##################################
        ## WHEN FRAME CONV WINDOW OPENS ##
        ## GET TIMESTAMP FROM FIRST AND ##
        ## LAST FRAME, READ ALL NEEDED  ##
        ##     LOGFILES IN AN ARRAY     ##
        ##          TIME, TEMP          ##
        ##################################
        # Read the Cryostream logfile
        # Return temperature
        # timeStamp format: Apr 18 2018 00:00:00
        # '{}'.format(datetime.datetime.now().strftime('%b %d %Y %H:%M:%S'))
        # column 0: timestamp, 44:sample temperature, 45:temperature error
        cryoLog = np.genfromtxt(cryoLogPath, dtype=str, delimiter=',', skip_header=2, usecols=(0,44))
        return cryoLog
    
    #-----------------#
    #    XYZ-STAGE    #
    #-----------------#
    
    def xyz_align_pos(self, ax):
        self.log.debug('Called')
        '''
         To do: Manual axis positioning does not disable xy-buttons
         - hack to allow 2 left positions -7 is the ;other' left
           manually adjust the values
        '''
        print('1',self.inCenteringPosition)
        small_step = 5.0
        large_step = 25.0
        if ax == 6:
            if self.smc_control_goto_sync(1, float(-7.0), self.SMC.signal_IAmInPos) is True:
                self.inCenteringPosition = True
            else:
                self.inCenteringPosition = False
        elif ax == 7:
            if self.smc_control_goto_sync(1, float(83.0), self.SMC.signal_IAmInPos) is True:
                self.inCenteringPosition = True
            else:
                self.inCenteringPosition = False
        elif ax == -7:
            if self.smc_control_goto_sync(1, float(-83.0), self.SMC.signal_IAmInPos) is True:
                self.inCenteringPosition = True
                small_step = -5.0
                large_step = -25.0
                ax = 7
            else:
                self.inCenteringPosition = False
        else:
            self.gui_popup('Error', 'Positioning', 'ERROR: undefined axis ({}) for xyz_align_pos!'.format(ax))
            return False
        self.xyz_check_xyphi(ax, small_step, large_step)
        return True
    
    def xyz_check_xyphi(self, ax, small_step, large_step):
        self.log.debug('Called')
        print('3',self.inCenteringPosition)
        if self.inCenteringPosition:
            for b in self.xy_buttons:
                b.disconnect()
                b.setEnabled(True)
            self.btn_xyz_l_1.clicked.connect(lambda: self.smc_control_move(ax, -small_step))
            self.btn_xyz_r_1.clicked.connect(lambda: self.smc_control_move(ax,  small_step))
            self.btn_xyz_l_2.clicked.connect(lambda: self.smc_control_move(ax, -large_step))
            self.btn_xyz_r_2.clicked.connect(lambda: self.smc_control_move(ax,  large_step))
            self.btn_xyz_l_3.clicked.connect(lambda: self.smc_control_fast_neg(ax))
            self.btn_xyz_r_3.clicked.connect(lambda: self.smc_control_fast_pos(ax))
        else:
            for b in self.xy_buttons:
                b.setEnabled(False)
    
########################
##        END         ##
########################

def main():
    global app
    app = QtWidgets.QApplication(sys.argv)
    ui = mainWindow()
    ui.show()
    sys.exit(app.exec())
    
if __name__ == '__main__':
    main()