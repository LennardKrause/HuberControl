import logging
from datetime import datetime as dt
log = logging.getLogger('HuberControl.' + __name__)

# #################################################### #
#                  DEFAULT PARAMETERS                  #
# #################################################### #
iniHandlerVersion = 'v2019-12-12'

# #################################################### #
# HOW TO:
# 1 - Add key:value
# 2 - Register the key to one of the following lists:
#      - iniBool  : True/False
#      - iniString: a String
#      - iniTuple : a Tuple
#      - iniInt   : an Integer
#      - iniFloat : a Float
# 3 - the key will be rejected if not registered!
# #################################################### #

defaultDict = {
               'path_PH2':'//home/bruker/p2client/link_to_share/Huber_Frames/',
               'path_SMC':'d:/frames/Huber_Frames/',
               'path_CRY':'d:/frames/CryoConnector/811450/logs/',
        'con_address_PH2':'172.16.111.101',
           'con_port_PH2':9001,
        'con_address_SMC':'172.16.111.201',
           'con_port_SMC':1234,
           'con_port_SHC':'COM2',
       'use_crash_engine':True,
     'use_debugging_mode':False,
         'use_conversion':True,
       'enable_tab_align':False,
        'enable_tab_cryo':False,
        'show_fv_toolbar':True,
           'startup_home':True,
        'startup_connect':True,
             'det_beam_x':384,
             'det_beam_y':511,
           'det_cor_roll':-0.4661,
          'det_cor_pitch':0.0478,
            'det_cor_yaw':0.3173,
           'det_cor_dist':0.0350,
            'fv_colormap':'hot',
             'fv_int_min':-100,
             'fv_int_max':600,
             'fv_int_def':100,
             'fv_poi_res':1.4,
             'fv_poi_int':800.0,
             'fv_poi_num':5,
            'fv_poi_dist':100,
            'fv_poi_size':7,
          'align_pos_phi':-50.0,
       'ax_dxt_home_fast':50000,
       'ax_dxt_home_slow':1000,
           'ax_phi_ffast':500000,
           'ax_chi_ffast':90000,
           'ax_omg_ffast':90000,
           'ax_tth_ffast':75000,
           'ax_dxt_ffast':90000,
            'ax_phi_frun':2000,
            'ax_chi_frun':500,
            'ax_omg_frun':500,
            'ax_tth_frun':500,
            'ax_dxt_frun':500,
             'ax_phi_acc':1000,
             'ax_chi_acc':400,
             'ax_omg_acc':400,
             'ax_tth_acc':400,
             'ax_dxt_acc':400,
             'ax_phi_dec':1000,
             'ax_chi_dec':400,
             'ax_omg_dec':400,
             'ax_tth_dec':400,
             'ax_dxt_dec':400,
            'dpx_phi_acc':400,
            'dpx_phi_dec':400,
          'dpx_phi_ffast':200000,
           'dpx_phi_frun':500,
             'ax_phi_blp':-1.8,
             'ax_chi_blp':-0.5,
             'ax_omg_blp':-0.5,
             'ax_tth_blp':-0.5,
             'ax_dxt_blp':0.0,
             'ax_phi_bln':0.0,
             'ax_chi_bln':0.0,
             'ax_omg_bln':0.0,
             'ax_tth_bln':0.0,
             'ax_dxt_bln':0.0,
          'ax_phi_offset':0.0,
          'ax_chi_offset':0.0,
          'ax_omg_offset':0.0,
          'ax_tth_offset':-10.0,
          'ax_dxt_offset':-176.0}

# #################################################### #
#                     INI HANDLER                      #
# #################################################### #
# do not write entries to .ini
iniNoSave = []
# do not load entries from .ini
iniNoLoad = []
# predefined variable types, assume the value to be of the following type:
# boolean True/False
iniBool = ['use_crash_engine','startup_home','use_conversion','use_debugging_mode',
           'enable_tab_align', 'enable_tab_cryo', 'show_fv_toolbar','startup_connect']
# string
iniString = ['con_address_SMC','con_address_PH2','con_port_SHC',
             'path_PH2','path_SMC','path_CRY',
             'fv_colormap']
# string
iniTuple = []
# integer
iniInt = ['con_port_SMC','con_port_PH2',
          'ax_dxt_home_fast','ax_dxt_home_slow',
          'ax_phi_ffast','ax_chi_ffast','ax_omg_ffast','ax_tth_ffast','ax_dxt_ffast',
          'ax_phi_frun','ax_chi_frun','ax_omg_frun','ax_tth_frun','ax_dxt_frun',
          'ax_phi_acc','ax_chi_acc','ax_omg_acc','ax_tth_acc','ax_dxt_acc',
          'ax_phi_dec','ax_chi_dec','ax_omg_dec','ax_tth_dec','ax_dxt_dec',
          'dpx_phi_acc','dpx_phi_dec','dpx_phi_ffast','dpx_phi_frun',
          'det_beam_x','det_beam_y',
          'fv_int_min','fv_int_max','fv_int_def',
          'fv_poi_num','fv_poi_size','fv_poi_dist']
# float
iniFloat = ['ax_phi_offset','ax_chi_offset','ax_omg_offset','ax_tth_offset','ax_dxt_offset',
            'ax_phi_blp','ax_chi_blp','ax_omg_blp','ax_tth_blp','ax_dxt_blp',
            'ax_phi_bln','ax_chi_bln','ax_omg_bln','ax_tth_bln','ax_dxt_bln',
            'det_cor_roll','det_cor_pitch','det_cor_yaw','det_cor_dist','align_pos_phi',
            'fv_poi_res','fv_poi_int']

def save_ini(PathToFile, p=defaultDict):
    log.info('Called')
    with open(PathToFile, 'w') as ini:
        ini.write('#{:-^{width}}#\n#{: ^{width}}#\n#{: ^{width}}#\n#{: ^{width}}#\n#{: ^{width}}#\n#{: ^{width}}#\n#{:-^{width}}#\n'.format('-',' Parameter File',iniHandlerVersion,'to change defaults','edit _iniHandler.py', dt.now().strftime('Created: %d/%m/%y %H:%M:%S'),'-', width=30))
        [ini.write('{}: {}\n'.format(i, p[i])) for i in sorted(p) if not i in iniNoSave]

def read_ini(PathToFile):
    log.info('Called')
    # floats: raise an error if there is no '.' or 'E' in value.upper()!
    temp = {}
    call_error = False
    force_write = False
    
    with open(PathToFile) as ofile:
        ini = ofile.readlines()
     
    for line in ini:
        if line.startswith('#') or line.isspace():
            continue
        # .replace('=',':') if = is wanted
        
        kvp = list(map(str.strip, line.split(':', 1)))
        if not len(kvp) == 2:
            log.error('INI_ERROR > \'{}\' is not a valid ini entry!'.format(kvp))
            force_write = True
            continue
        else:
            key, val = kvp
            
        if key in iniNoLoad:
            continue
        #elif val == 'None':
        #    continue
        elif key in iniBool:
            if val.upper() in ['TRUE','T']:
                temp[key] = True
            elif val.upper() in ['FALSE','F']:
                temp[key] = False
            else:
                log.error('INI_ERROR > \'{}\' must be boolean (is: \'{}\')!'.format(key, val))
                call_error = True
        elif key in iniString:
            temp[key] = str(val)
        elif key in iniTuple:
            try:
                tempTuple = [float(i) for i in val.strip('()').split(',')]
                if len(tempTuple) == 3:
                    temp[key] = tuple(tempTuple)
                else:
                    log.error('INI_ERROR > \'{}\' must be an rgba tuple (is: \'{}\')!'.format(key, val))
                    call_error = True
            except ValueError:
                log.error('INI_ERROR > \'{}\' rgba tuple must be given as floats (is: \'{}\')!'.format(key, val))
                call_error = True
        elif key in iniInt:
            try:
                temp[key] = int(val)
            except ValueError:
                log.error('INI_ERROR > \'{}\' must be an integer (is: \'{}\')!'.format(key, val))
                call_error = True
        elif key in iniFloat:
            try:
                if '.' in val or 'E' in val.upper():
                    temp[key] = float(val)
                else:
                    raise ValueError
            except ValueError:
                log.error('INI_ERROR > \'{}\' must be a float (is: \'{}\')!'.format(key, val))
                call_error = True
        else:
            log.error('INI_ERROR > unknown parameter: \'{}\' (=\'{}\')!'.format(key, val))
            force_write = True
    if call_error:
        raise SystemExit
    
    # Update current ini with missing items from defaultDict
    missing = set(defaultDict.keys()) - set(temp.keys())
    if len(missing) > 0 or force_write:
        for k in missing:
            log.error('INI_ERROR > parameter missing: \'{}\'!'.format(k))
            temp[k] = defaultDict[k]
        save_ini(PathToFile, temp)
    return temp