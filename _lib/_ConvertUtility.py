#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#   convert_utility.py - a collection of image conversion utility functions
#   Copyright (C) 2018, L.Krause <lkrause@chem.au.dk>, Aarhus University, DK
#
#   This program is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free
#   Software Foundation, either version 3 of the License, or (at your option)
#   any later version.
#
#   This program is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#   FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#   more details. <http://www.gnu.org/licenses/>
#
#IMPORTANT:
#   Bruker AXS is not associated with this software and will not support this.
#   Please direct any queries to L.Krause <lkrause@chem.au.dk>
#
def read_raw_frame(fname, dim1, dim2, bytecode):
    '''
     Read a PHOTON-II raw image file
      - endianness unchecked
      - no header, pure data
      - returns None on error
    '''
    import numpy as np
    # translate the bytecode to the bytes per pixel
    bpp = len(np.array(0, bytecode).tostring())
    # determine the image size
    size = dim1 * dim2 * bpp
    # open the file
    with open(fname, 'rb') as f:
        # read the image
        binData = f.read(size)
    # dtype = bytecode
    rawData = np.fromstring(binData, bytecode)
    # reshape the image into 2d array (dim1, dim2)
    if rawData.size < dim1*dim2:
        return None
    else:
        data = rawData.reshape((dim1, dim2))
        return data

def bruker_header():
    '''
     default Bruker header
    '''
    import collections
    import numpy as np
    
    header = collections.OrderedDict()
    header['FORMAT']  = np.array([100], dtype=np.int64)                       # Frame Format -- 86=SAXI, 100=Bruker
    header['VERSION'] = np.array([18], dtype=np.int64)                        # Header version number
    header['HDRBLKS'] = np.array([15], dtype=np.int64)                        # Header size in 512-byte blocks
    header['TYPE']    = ['Some Frame']                                        # String indicating kind of data in the frame
    header['SITE']    = ['Some Site']                                         # Site name
    header['MODEL']   = ['?']                                                 # Diffractometer model
    header['USER']    = ['USER']                                              # Username
    header['SAMPLE']  = ['']                                                  # Sample ID
    header['SETNAME'] = ['']                                                  # Basic data set name
    header['RUN']     = np.array([1], dtype=np.int64)                         # Run number within the data set
    header['SAMPNUM'] = np.array([1], dtype=np.int64)                         # Specimen number within the data set
    header['TITLE']   = ['', '', '', '', '', '', '', '', '']                  # User comments (8 lines)
    header['NCOUNTS'] = np.array([-9999, 0], dtype=np.int64)                  # Total frame counts, Reference detector counts
    header['NOVERFL'] = np.array([-1, 0, 0], dtype=np.int64)                  # SAXI Format: Number of overflows
                                                                              # Bruker Format: #Underflows; #16-bit overfl; #32-bit overfl
    header['MINIMUM'] = np.array([-9999], dtype=np.int64)                     # Minimum pixel value
    header['MAXIMUM'] = np.array([-9999], dtype=np.int64)                     # Maximum pixel value
    header['NONTIME'] = np.array([-2], dtype=np.int64)                        # Number of on-time events
    header['NLATE']   = np.array([0], dtype=np.int64)                         # Number of late events for multiwire data
    header['FILENAM'] = ['unknown.sfrm']                                      # (Original) frame filename
    header['CREATED'] = ['01-Jan-2000 01:01:01']                              # Date and time of creation
    header['CUMULAT'] = np.array([20.0], dtype=np.float64)                    # Accumulated exposure time in real hours
    header['ELAPSDR'] = np.array([10.0, 10.0], dtype=np.float64)              # Requested time for this frame in seconds
    header['ELAPSDA'] = np.array([10.0, 10.0], dtype=np.float64)              # Actual time for this frame in seconds
    header['OSCILLA'] = np.array([0], dtype=np.int64)                         # Nonzero if acquired by oscillation
    header['NSTEPS']  = np.array([1], dtype=np.int64)                         # steps or oscillations in this frame
    header['RANGE']   =  np.array([1.0], dtype=np.float64)                    # Magnitude of scan range in decimal degrees
    header['START']   = np.array([0.0], dtype=np.float64)                     # Starting scan angle value, decimal deg
    header['INCREME'] = np.array([1.0], dtype=np.float64)                     # Signed scan angle increment between frames
    header['NUMBER']  = np.array([1], dtype=np.int64)                         # Number of this frame in series (zero-based)
    header['NFRAMES'] = np.array([1], dtype=np.int64)                         # Number of frames in the series
    header['ANGLES']  = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)      # Diffractometer setting angles, deg. (2Th, omg, phi, chi)
    header['NOVER64'] = np.array([0, 0, 0], dtype=np.int64)                   # Number of pixels > 64K
    header['NPIXELB'] = np.array([1, 2], dtype=np.int64)                      # Number of bytes/pixel; Number of bytes per underflow entry
    header['NROWS']   = np.array([512, 1], dtype=np.int64)                    # Number of rows in frame; number of mosaic tiles in Y; dZ/dY value
                                                                              # for each mosaic tile, X varying fastest
    header['NCOLS']   = np.array([512, 1], dtype=np.int64)                    # Number of pixels per row; number of mosaic tiles in X; dZ/dX
                                                                              # value for each mosaic tile, X varying fastest
    header['WORDORD'] = np.array([0], dtype=np.int64)                         # Order of bytes in word; always zero (0=LSB first)
    header['LONGORD'] = np.array([0], dtype=np.int64)                         # Order of words in a longword; always zero (0=LSW first
    header['TARGET']  = ['Mo']                                                # X-ray target material)
    header['SOURCEK'] = np.array([0.0], dtype=np.float64)                     # X-ray source kV
    header['SOURCEM'] = np.array([0.0], dtype=np.float64)                     # Source milliamps
    header['FILTER']  = ['?']                                                 # Text describing filter/monochromator setting
    header['CELL']    = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64) # Cell constants, 2 lines  (A,B,C,Alpha,Beta,Gamma)
    header['MATRIX']  = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64) # Orientation matrix, 3 lines
    header['LOWTEMP'] = np.array([1, -17300, -6000], dtype=np.int64)          # Low temp flag; experiment temperature*100; detector temp*100
    header['ZOOM']    = np.array([0.0, 0.0, 1.0], dtype=np.float64)           # Image zoom Xc, Yc, Mag
    header['CENTER']  = np.array([256.0, 256.0, 256.0, 256.0], dtype=np.float64) # X, Y of direct beam at 2-theta = 0
    header['DISTANC'] = np.array([5.0], dtype=np.float64)                     # Sample-detector distance, cm
    header['TRAILER'] = np.array([0], dtype=np.int64)                         # Byte pointer to trailer info (unused; obsolete)
    header['COMPRES'] = ['none']                                              # Text describing compression method if any
    header['LINEAR']  = np.array([1.0, 0.0], dtype=np.float64)                # Linear scale, offset for pixel values
    header['PHD']     = np.array([0.0, 0.0], dtype=np.float64)                # Discriminator settings
    header['PREAMP']  = np.array([1,1], dtype=np.int64)                       # Preamp gain setting
    header['CORRECT'] = ['UNKNOWN']                                           # Flood correction filename
    header['WARPFIL'] = ['Linear']                                            # Spatial correction filename
    header['WAVELEN'] = np.array([0.0, 0.0, 0.0], dtype=np.float64)           # Wavelengths (average, a1, a2)
    header['MAXXY']   = np.array([1, 1], dtype=np.int64)                      # X,Y pixel # of maximum counts
    header['AXIS']    = np.array([2], dtype=np.int64)                         # Scan axis (1=2-theta, 2=omega, 3=phi, 4=chi)
    header['ENDING']  = np.array([0.0, 0.5, 0.0, 0.0], dtype=np.float64)      # Setting angles read at end of scan
    header['DETPAR']  = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64) # Detector position corrections (Xc,Yc,Dist,Pitch,Roll,Yaw)
    header['LUT']     = ['lut']                                               # Recommended display lookup table
    header['DISPLIM'] = np.array([0.0, 0.0], dtype=np.float64)                # Recommended display contrast window settings
    header['PROGRAM'] = ['Python Image Conversion']                           # Name and version of program writing frame
    header['ROTATE']  = np.array([0], dtype=np.int64)                         # Nonzero if acquired by rotation (GADDS)
    header['BITMASK'] = ['$NULL']                                             # File name of active pixel mask (GADDS)
    header['OCTMASK'] = np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int64)    # Octagon mask parameters (GADDS) #min x, min x+y, min y, max x-y, max x, max x+y, max y, max y-x
    header['ESDCELL'] = np.array([0.001, 0.001, 0.001, 0.02, 0.02, 0.02], dtype=np.float64) # Cell ESD's, 2 lines (A,B,C,Alpha,Beta,Gamma)
    header['DETTYPE'] = ['Unknown']                                           # Detector type
    header['NEXP']    = np.array([1, 0, 0, 0, 0], dtype=np.int64)             # Number exposures in this frame; CCD bias level*100,;
                                                                              # Baseline offset (usually 32); CCD orientation; Overscan Flag
    header['CCDPARM'] = np.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64) # CCD parameters for computing pixel ESDs; readnoise, e/ADU, e/photon, bias, full scale
    header['CHEM']    = ['?']                                                 # Chemical formula
    header['MORPH']   = ['?']                                                 # CIFTAB string for crystal morphology
    header['CCOLOR']  = ['?']                                                 # CIFTAB string for crystal color
    header['CSIZE']   = ['?']                                                 # String w/ 3 CIFTAB sizes, density, temp
    header['DNSMET']  = ['?']                                                 # CIFTAB string for density method
    header['DARK']    = ['NONE']                                              # Dark current frame name
    header['AUTORNG'] = np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float64) # Autorange gain, time, scale, offset, full scale
    header['ZEROADJ'] = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)      # Adjustments to goniometer angle zeros (tth, omg, phi, chi)
    header['XTRANS']  = np.array([0.0, 0.0, 0.0], dtype=np.float64)           # Crystal XYZ translations
    header['HKL&XY']  = np.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64) # HKL and pixel XY for reciprocal space (GADDS)
    header['AXES2']   = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)      # Diffractometer setting linear axes (4 ea) (GADDS)
    header['ENDING2'] = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)      # Actual goniometer axes @ end of frame (GADDS)
    header['FILTER2'] = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)      # Monochromator 2-theta, roll (both deg)
    header['LEPTOS']  = ['']
    header['CFR']     = ['']
    return header
    
def write_bruker_frame(fname, fheader, fdata):
    '''
     write a bruker image
    '''
    import numpy as np
    
    ########################
    ## write_bruker_frame ##
    ##     FUNCTIONS      ##
    ########################
    def pad_table(table, bpp):
        '''
         pads a table with zeros to a multiple of 16 bytes
        '''
        padded = np.zeros(int(np.ceil(table.size * abs(bpp) / 16)) * 16 // abs(bpp)).astype(_BPP_TO_DT[bpp])
        padded[:table.size] = table
        return padded
        
    def format_bruker_header(fheader):
        '''
         
        '''
        format_dict = {(1,   'int64'): '{:<71d} ',
                       (2,   'int64'): '{:<35d} {:<35d} ',
                       (3,   'int64'): '{:<23d} {:<23d} {:<23d} ',
                       (4,   'int64'): '{:<17d} {:<17d} {:<17d} {:<17d} ',
                       (5,   'int64'): '{:<13d} {:<13d} {:<13d} {:<13d} {:<13d}   ',
                       (6,   'int64'): '{:<11d} {:<11d} {:<11d} {:<11d} {:<11d} {:<11d} ',
                       (1,   'int32'): '{:<71d} ',
                       (2,   'int32'): '{:<35d} {:<35d} ',
                       (3,   'int32'): '{:<23d} {:<23d} {:<23d} ',
                       (4,   'int32'): '{:<17d} {:<17d} {:<17d} {:<17d} ',
                       (5,   'int32'): '{:<13d} {:<13d} {:<13d} {:<13d} {:<13d}   ',
                       (6,   'int32'): '{:<11d} {:<11d} {:<11d} {:<11d} {:<11d} {:<11d} ',
                       (1, 'float64'): '{:<71f} ',
                       (2, 'float64'): '{:<35f} {:<35f} ',
                       (3, 'float64'): '{:<23f} {:<23f} {:<23f} ',
                       (4, 'float64'): '{:<17f} {:<17f} {:<17f} {:<17f} ',
                       (5, 'float64'): '{:<13f} {:<13f} {:<13f} {:<13f} {:<15f} '}
    
        headers = []
        for name, entry in fheader.items():
            # TITLE has multiple lines
            if name == 'TITLE':
                name = '{:<7}:'.format(name)
                number = len(entry)
                for line in range(8):
                    if number < line:
                        headers.append(''.join((name, '{:<72}'.format(entry[line]))))
                    else:
                        headers.append(''.join((name, '{:<72}'.format(' '))))
                continue
    
            # DETTYPE Mixes Entry Types
            if name == 'DETTYPE':
                name = '{:<7}:'.format(name)
                string = '{:<20s} {:<11f} {:<11f} {:<1d} {:<11f} {:<10f} {:<1d} '.format(*entry)
                headers.append(''.join((name, string)))
                continue
            
            # format the name
            name = '{:<7}:'.format(name)
            
            # pad entries
            if type(entry) == list or type(entry) == str:
                headers.append(''.join(name + '{:<72}'.format(entry[0])))
                continue
            
            # fill empty fields
            if entry.shape[0] == 0:
                headers.append(name + '{:72}'.format(' '))
                continue
            
            # if line has too many entries e.g.
            # OCTMASK(8): np.int64
            # CELL(6), MATRIX(9), DETPAR(6), ESDCELL(6): np.float64
            # write the first 6 (np.int64) / 5 (np.float64) entries
            # and the remainder later
            if entry.shape[0] > 6 and entry.dtype == np.int64:
                while entry.shape[0] > 6:
                    format_string = format_dict[(6, str(entry.dtype))]
                    headers.append(''.join(name + format_string.format(*entry[:6])))
                    entry = entry[6:]
            elif entry.shape[0] > 5 and entry.dtype == np.float64:
                while entry.shape[0] > 5:
                    format_string = format_dict[(5, str(entry.dtype))]
                    headers.append(''.join(name + format_string.format(*entry[:5])))
                    entry = entry[5:]
            
            # format line
            format_string = format_dict[(entry.shape[0], str(entry.dtype))]
            headers.append(''.join(name + format_string.format(*entry)))
    
        # add header ending
        if headers[-1][:3] == 'CFR':
            headers = headers[:-1]
        padding = 512 - (len(headers) * 80 % 512)
        end = '\x1a\x04'
        if padding <= 80:
            start = 'CFR: HDR: IMG: '
            padding -= len(start) + 2
            dots = ''.join(['.'] * padding)
            headers.append(start + dots + end)
        else:
            while padding > 80:
                headers.append(end + ''.join(['.'] * 78))
                padding -= 80
            if padding != 0:
                headers.append(end + ''.join(['.'] * (padding - 2)))
        return ''.join(headers)
    ########################
    ## write_bruker_frame ##
    ##   FUNCTIONS END    ##
    ########################
    
    # assign bytes per pixel to numpy integers
    # int8   Byte (-128 to 127)
    # int16  Integer (-32768 to 32767)
    # int32  Integer (-2147483648 to 2147483647)
    # uint8  Unsigned integer (0 to 255)
    # uint16 Unsigned integer (0 to 65535)
    # uint32 Unsigned integer (0 to 4294967295)
    _BPP_TO_DT = {1: np.uint8,
                  2: np.uint16,
                  4: np.uint32,
                 -1: np.int8,
                 -2: np.int16,
                 -4: np.int32}
    
    # read the bytes per pixel
    # frame data (bpp), underflow table (bpp_u)
    bpp, bpp_u = fheader['NPIXELB']
    
    # generate underflow table
    # does not work as APEXII reads the data as uint8/16/32!
    if fheader['NOVERFL'][0] >= 0:
        data_underflow = fdata[fdata <= 0]
        fheader['NOVERFL'][0] = data_underflow.shape[0]
        table_underflow = pad_table(data_underflow, -1 * bpp_u)
        fdata[fdata < 0] = 0

    # generate 32 bit overflow table
    if bpp < 4:
        data_over_uint16 = fdata[fdata >= 65535]
        table_data_uint32 = pad_table(data_over_uint16, 4)
        fheader['NOVERFL'][2] = data_over_uint16.shape[0]
        fdata[fdata >= 65535] = 65535

    # generate 16 bit overflow table
    if bpp < 2:
        data_over_uint8 = fdata[fdata >= 255]
        table_data_uint16 = pad_table(data_over_uint8, 2)
        fheader['NOVERFL'][1] = data_over_uint8.shape[0]
        fdata[fdata >= 255] = 255

    # shrink data to desired bpp
    fdata = fdata.astype(_BPP_TO_DT[bpp])
    
    # write frame
    with open(fname, 'wb') as brukerFrame:
        brukerFrame.write(format_bruker_header(fheader).encode('ASCII'))
        brukerFrame.write(fdata.tobytes())
        if fheader['NOVERFL'][0] >= 0:
            brukerFrame.write(table_underflow.tobytes())
        if bpp < 2 and fheader['NOVERFL'][1] > 0:
            brukerFrame.write(table_data_uint16.tobytes())
        if bpp < 4 and fheader['NOVERFL'][2] > 0:
            brukerFrame.write(table_data_uint32.tobytes())

def convert_frame(fname, sfrmdir, cutoff=-64, overwrite=False):
    '''
     
    '''
    import os,time
    import numpy as np
    from datetime import datetime
    
    # split path, name and extension
    path_to, frame_name = os.path.split(fname)
    basename, ext = os.path.splitext(frame_name)
    # try to get the run and frame number from filename
    # any_name_runNum_frmNum.raw is assumed.
    try:
        _split = basename.split('_')
        frmNum = int(_split.pop())
        runNum = int(_split.pop())
        _stem = '_'.join(_split)
    except ValueError:
        print('ERROR: Wrong filename format [#name#_#run#_#frame#.raw]: {}'.format(frame_name))
        return False
    
    # output file name
    outName = os.path.join(sfrmdir, basename + '.sfrm')
    
    # check if output file already exists
    if os.path.isfile(outName) and not overwrite:
        return False
    
    # Info file name
    infName = os.path.join(path_to, basename[:-5] + '.info')
    
    # check if info file exists
    if not os.path.isfile(infName):
        print('ERROR: Info file is missing for: {}'.format(frame_name))
        return False
    
    # read info file to dict
    runInfo = {}
    with open(infName) as infFile:
        for line in infFile:
            try:
                (key, val) = line.split(':')
                runInfo[key.strip()] = val.strip()
            except ValueError:
                pass
    
    # populate scan variables
    try:
        goni_dxt     =     abs(float(runInfo['axis_dxt']))     # mm
        scan_inc     =       - float(runInfo['scan_width'])    # seconds per degree
        goni_tth     =         float(runInfo['axis_tth'])      # tth
        goni_omg     =         float(runInfo['axis_omg'])      # omega
        goni_phi     =       - float(runInfo['axis_phi'])      # phi
        goni_chi     = 180.0 - float(runInfo['axis_chi'])      # chi
        scan_exp     =         float(runInfo['scan_exposure']) # seconds per frame
        scan_frames  =           int(runInfo['scan_frames'])   # number of frames in run
        scan_name    =           str(runInfo['scan_name'])     # samplename
        scan_user    =           str(runInfo['scan_user'])     # username
        scan_run     =           int(runInfo['scan_run'])      # run number
        detcor_x     =           int(runInfo['det_beam_x'])    # beamcenter x
        detcor_y     =    1024 - int(runInfo['det_beam_y'])    # beamcenter y
        detcor_roll  =         float(runInfo['det_cor_roll'])  # detector roll
        detcor_pitch =         float(runInfo['det_cor_pitch']) # detector pitch
        detcor_yaw   =         float(runInfo['det_cor_yaw'])   # detector yaw
        detcor_dist  =         float(runInfo['det_cor_dist'])  # detector yaw
        goni_sta = goni_phi + frmNum * scan_inc - scan_inc
        goni_end = goni_phi + frmNum * scan_inc
    except KeyError:
        print('Error interpreting the info file: {}'.format(basename))
        return False
    
    # read in the frame
    # returns None on error
    rawData = read_raw_frame(fname, 768, 1024, np.int32)
    
    # error in frame data
    if rawData is None:
        print('ERROR: Incomplete frame data: {}'.format(basename))
        return False
    
    # cut off negative outliers/bad pixels
    # bad pixel intensity: -2147483520
    # why not int32:       -2147483648
    if cutoff < 0:
        rawData[rawData < cutoff] = cutoff
        baseline_offset = abs(cutoff)
    # reset to zero
    else:
        baseline_offset = -1 * rawData.min()
    
    # scale the data to avoid underflow tables
    rawData += baseline_offset
    
    # calculate detector pixel per cm
    # normalised to a 512x512 detector format
    # Photon-II pixel size is 0.1353 mm
    # unused, as I can't reproduce the value 37.037037!
    #pix_per_512 = round((10.0 / 0.1353) * (512.0 / ((1024.0 + 768.0) / 2.0)), 6)
    
    # default bruker header
    header = bruker_header()
    
    # fill known header entries
    header['NCOLS'][:]   = [768, 1]                                  # Number of pixels per row; number of mosaic tiles in X; dZ/dX
    header['NROWS'][:]   = [1024, 1]                                 # Number of rows in frame; number of mosaic tiles in Y; dZ/dY value
    header['CENTER'][:]  = [detcor_x, detcor_y, detcor_x, detcor_y]  # 
    # e/p: 329.3748
    # e/p: 359.8295
    header['CCDPARM'][:] = [1.47398, 36.60, 359.8295, 0.0, 163810.0] # readnoise, electronsperadu, electronsperphoton, bruker_bias, bruker_fullscale
    header['DETPAR'][:]  = [0.0, 0.0, detcor_dist, detcor_pitch, detcor_roll, detcor_yaw] # Detector position corrections (Xc, Yc, Dist, Pitch, Roll, Yaw)
    header['DETTYPE'][:] = ['CMOS-PHOTONII', 37.037037, 1.004, 0, 0.425, 0.035, 1]
    header['SITE']       = ['Aarhus Huber Diffractometer']           # Site name
    header['MODEL']      = ['Microfocus X-ray Source']               # Diffractometer model
    header['TARGET']     = ['Ag Ka']                                 # X-ray target material)
    
    header['USER']       = [scan_user]                               # Username
    header['SAMPLE']     = [scan_name]                               # Samplename
    header['RUN']        = [scan_run]                                # Run number
    header['SOURCEK']    = [50.0]                                    # X-ray source kV
    header['SOURCEM']    = [0.880]                                   # Source milliamps
    header['WAVELEN'][:] = [0.560860, 0.559420, 0.563810]            # Wavelengths (average, a1, a2)
    header['FILENAM']    = [basename]
    header['CUMULAT']    = [scan_exp]                                # Accumulated exposure time in real hours
    header['ELAPSDR']    = [scan_exp]                                # Requested time for this frame in seconds
    header['ELAPSDA']    = [scan_exp]                                # Actual time for this frame in seconds
    header['START'][:]   = [goni_sta]                                # Starting scan angle value, decimal deg
    header['ANGLES'][:]  = [goni_tth, goni_omg, goni_sta, goni_chi]  # Diffractometer setting angles, deg. (2Th, omg, phi, chi)
    header['ENDING'][:]  = [goni_tth, goni_omg, goni_end, goni_chi]  # Setting angles read at end of scan
    header['TYPE']       = ['Generic Phi Scan']                      # String indicating kind of data in the frame
    header['DISTANC']    = [float(goni_dxt) / 10.0]                  # Sample-detector distance, cm
    header['RANGE']      = [abs(scan_inc)]                           # Magnitude of scan range in decimal degrees
    header['INCREME']    = [scan_inc]                                # Signed scan angle increment between frames
    header['NUMBER']     = [frmNum]                                  # Number of this frame in series (zero-based)
    header['NFRAMES']    = [scan_frames]                             # Number of frames in the series
    header['AXIS'][:]    = [3]                                       # Scan axis (1=2-theta, 2=omega, 3=phi, 4=chi)
    header['LOWTEMP'][:] = [1, int((-273.15 + 100.0) * 100.0), -6000]# Low temp flag; experiment temperature*100; detector temp*100
    header['NEXP'][:]    = [1, 0, baseline_offset, 0, 0]             # number of exposures, bruker_adubias, baselineoffset, bruker_orientation, bruker_overscan
    header['MAXXY']      = np.array(np.where(rawData == rawData.max()), np.float)[:, 0]
    header['MAXIMUM']    = [np.max(rawData)]
    header['MINIMUM']    = [np.min(rawData)]
    header['NCOUNTS'][:] = [rawData.sum(), 0]
    header['NOVERFL'][:] = [-1, 0, 0]
    header['NOVER64'][:] = [rawData[rawData > 64000].shape[0], 0, 0]
    header['NSTEPS']     = [1]                                       # steps or oscillations in this frame
    header['NPIXELB'][:] = [1, 1]                                    # bytes/pixel in main image, bytes/pixel in underflow table
    header['COMPRES']    = [0]                                       # compression scheme if any
    header['TRAILER']    = [-1]                                      # byte pointer to trailer info
    header['CORRECT']    = ['INTERNAL, s/n: A110247']                # Flood correction filename
    header['DARK']       = ['INTERNAL, s/n: A110247']                # Dark current frame name
    header['WARPFIL']    = ['LINEAR']                                # Spatial correction filename
    header['LINEAR'][:]  = [1.00, 0.00]                              # bruker_linearscale, bruker_linearoffset
    header['PHD'][:]     = [0.68, 0.051]                             # Phosphor efficiency, phosphor thickness
    header['LUT']        = ['BB.LUT']                                # Recommended display lookup table
    header['DISPLIM'][:] = [100.0, 630.0]                               # Recommended display contrast window settings
    header['OCTMASK'][:] = [0, 0, 0, 767, 767, 1791, 1023, 1023]
    header['CREATED']    = [datetime.fromtimestamp(os.path.getmtime(fname)).strftime('%Y-%m-%d %H:%M:%S')]# use creation time of raw data!

    # write the frame
    write_bruker_frame(outName, header, rawData)
    return True

def bad_pixel_mask(height=1024, width=768, bad_xy='P2_bad_pix.xy', mask_file='P2_bad_pix', mask_vlines=True, flipud=True, fliplr=True, bytecode=None):
    '''
     height:      vertical dimension
     width:       horizontal dimension
     bad_xy:      file containing bad pixels, x y coordinates
     mask_file:   name of new file
     mask_vlines: set vertical chip gaps (at: 64 192 320 448 576 704) to -1
     flipud:      does the vertical coordinate needs to be inverted?
     bytecode:    default is np.int8, we need 0 and -1
    returns:
     aMask:       masked [0,-1] np.array(dim1 * dim2, bytecode)
    '''
    import numpy as np
    
    # if no bytecode is specified use np.int8
    if not bytecode:
        bytecode = np.int8
    
    # empty array
    aMask = np.zeros(height * width, bytecode).reshape((height, width))
    
    # mask vertical gaps
    # 64 192 320 448 576 704
    if mask_vlines:
        aMask[:, [63, 191, 319, 447, 575, 703]] = -1
    
    # read x y coordinates from file
    with open(bad_xy) as ofile:
        lst = list(map(int, ofile.read().split()))
    
    # x: every second item starting with first
    x = np.array(lst[0::2])
    
    # y: every second item starting with second
    y = np.array(lst[1::2])
    
    # if vertical coordinate needs to be inverted
    if flipud:
        y = height - y - 1
    
    # if horizontal coordinate needs to be inverted
    if fliplr:
        x = width - x - 1
    
    # mask xy coordinates
    aMask[y, x] = -1
    
    # write new file
    with open(mask_file, 'wb') as wfile:
        wfile.write(aMask.tobytes())
    
    return aMask