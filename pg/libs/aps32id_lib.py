'''
    Tomo Scan Lib for Sector 32 ID C
    
'''

import sys
import json
import time
from epics import PV
import h5py
import shutil
import os
import imp
import traceback
import math
import signal
import numpy

import libs.log_lib as log_lib

TESTING_MODE = True
UseShutterA = False
UseShutterB = True

ShutterA_Open_Value = 0
ShutterA_Close_Value = 1
ShutterB_Open_Value = 0
ShutterB_Close_Value = 1

FrameTypeData = 0
FrameTypeDark = 1
FrameTypeWhite = 2

DetectorIdle = 0
DetectorAcquire = 1

TXM = True
EPSILON = 0.1

PG_Trigger_External_Trigger = 1 # Important for the Point Grey (continuous mode as clock issues)
Recursive_Filter_Type = 'RecursiveAve'


def update_variable_dict(variableDict):
    argDic = {}
    if len(sys.argv) > 1:
        strArgv = sys.argv[1]
        argDic = json.loads(strArgv)
    # print('orig variable dict', variableDict)
    for k,v in argDic.iteritems():
        variableDict[k] = v
    # print('new variable dict', variableDict)


#wait on a pv to be a value until max_timeout (default forever)
def wait_pv(pv, wait_val, max_timeout_sec=-1):
    # print 'wait_pv(', pv.pvname, wait_val, max_timeout_sec, ')'
    #delay for pv to change
    time.sleep(.01)
    startTime = time.time()
    while(True):
        pv_val = pv.get()
        if type(pv_val) == float:
            if abs(pv_val - wait_val) < EPSILON:
                return True
        if (pv_val != wait_val):
            if max_timeout_sec > -1:
                curTime = time.time()
                diffTime = curTime - startTime
                if diffTime >= max_timeout_sec:
                    #print 'wait_pv(', pv.pvname, wait_val, max_timeout_sec, ') reached max timeout. Return False'
                    return False
            time.sleep(.01)
        else:
            return True


def init_general_PVs(global_PVs, variableDict):
    log_lib.info(' ')
    log_lib.info('  *** Init general PVs')
    global_PVs['Cam1_ImageMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:ImageMode') # 0=single, 1=multiple, 2=continuous
    global_PVs['Cam1_ArrayCallbacks'] = PV(variableDict['IOC_Prefix'] + 'cam1:ArrayCallbacks')
    global_PVs['Cam1_AcquireTime'] = PV(variableDict['IOC_Prefix'] + 'cam1:AcquireTime')
    global_PVs['Cam1_AcquirePeriod'] = PV(variableDict['IOC_Prefix'] + 'cam1:AcquirePeriod')
    global_PVs['Cam1_FrameRate_on_off'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameRateOnOff')
    global_PVs['Cam1_FrameRate_val'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameRateValAbs')
    global_PVs['Cam1_TriggerMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:TriggerMode')
    global_PVs['Cam1_SoftGlueTrigger'] = PV('32idcTXM:SG3:BUFFER-2_IN_Signal')
    global_PVs['Cam1_SoftwareTrigger'] = PV(variableDict['IOC_Prefix'] + 'cam1:SoftwareTrigger')
    global_PVs['Cam1_FrameRateOnOff'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameRateOnOff')
    global_PVs['Cam1_FrameType'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameType')
    global_PVs['Cam1_Image'] = PV(variableDict['IOC_Prefix'] + 'image1:ArrayData')
    global_PVs['Cam1_NumImages'] = PV(variableDict['IOC_Prefix'] + 'cam1:NumImages')
    global_PVs['Cam1_Acquire'] = PV(variableDict['IOC_Prefix'] + 'cam1:Acquire')
    global_PVs['Cam1_Display'] = PV(variableDict['IOC_Prefix'] + 'image1:EnableCallbacks')
    global_PVs['Cam1_FF_norm'] = PV(variableDict['IOC_Prefix'] + 'Proc1:EnableFlatField')
    global_PVs['Cam1_Recursive_Filter'] = PV('32idcPG3:Proc1:EnableFilter')
    global_PVs['Cam1_Proc1_Port'] = PV(variableDict['IOC_Prefix'] + 'Proc1:NDArrayPort')
    global_PVs['Cam1_Image1_Port'] = PV(variableDict['IOC_Prefix'] + 'Image1:NDArrayPort')
    global_PVs['Cam1_OverLay_Port'] = PV(variableDict['IOC_Prefix'] + 'Over1:NDArrayPort')
    global_PVs['Cam1_Trans_Port'] = PV(variableDict['IOC_Prefix'] + 'Trans1:NDArrayPort')
    global_PVs['nCol'] = PV(variableDict['IOC_Prefix'] + 'cam1:ArraySizeX_RBV')
    global_PVs['nRow'] = PV(variableDict['IOC_Prefix'] + 'cam1:ArraySizeY_RBV')

    #hdf5 writer pv's
    global_PVs['HDF1_LazyOpen'] = PV(variableDict['IOC_Prefix'] + 'HDF1:HDF1_LazyOpen')
    global_PVs['HDF1_AutoSave'] = PV(variableDict['IOC_Prefix'] + 'HDF1:AutoSave')
    global_PVs['HDF1_DeleteDriverFile'] = PV(variableDict['IOC_Prefix'] + 'HDF1:DeleteDriverFile')
    global_PVs['HDF1_EnableCallbacks'] = PV(variableDict['IOC_Prefix'] + 'HDF1:EnableCallbacks')
    global_PVs['HDF1_BlockingCallbacks'] = PV(variableDict['IOC_Prefix'] + 'HDF1:BlockingCallbacks')
    global_PVs['HDF1_FileWriteMode'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileWriteMode')
    global_PVs['HDF1_NumCapture'] = PV(variableDict['IOC_Prefix'] + 'HDF1:NumCapture')
    global_PVs['HDF1_Capture'] = PV(variableDict['IOC_Prefix'] + 'HDF1:Capture')
    global_PVs['HDF1_Capture_RBV'] = PV(variableDict['IOC_Prefix'] + 'HDF1:Capture_RBV')
    global_PVs['HDF1_FileName'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileName')
    global_PVs['HDF1_FullFileName_RBV'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FullFileName_RBV')
    global_PVs['HDF1_FileTemplate'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileTemplate')
    global_PVs['HDF1_ArrayPort'] = PV(variableDict['IOC_Prefix'] + 'HDF1:NDArrayPort')
    global_PVs['HDF1_NextFile'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileNumber')

    #tiff writer pv's
    global_PVs['TIFF1_AutoSave'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:AutoSave')
    global_PVs['TIFF1_DeleteDriverFile'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:DeleteDriverFile')
    global_PVs['TIFF1_EnableCallbacks'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:EnableCallbacks')
    global_PVs['TIFF1_BlockingCallbacks'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:BlockingCallbacks')
    global_PVs['TIFF1_FileWriteMode'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:FileWriteMode')
    global_PVs['TIFF1_NumCapture'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:NumCapture')
    global_PVs['TIFF1_Capture'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:Capture')
    global_PVs['TIFF1_Capture_RBV'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:Capture_RBV')
    global_PVs['TIFF1_FileName'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:FileName')
    global_PVs['TIFF1_FullFileName_RBV'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:FullFileName_RBV')
    global_PVs['TIFF1_FileTemplate'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:FileTemplate')
    global_PVs['TIFF1_ArrayPort'] = PV(variableDict['IOC_Prefix'] + 'TIFF1:NDArrayPort')

    # Sample stage pv's
    if TXM: # TXM
            global_PVs['Motor_SampleX'] = PV('32idcTXM:nf:c0:m1.VAL')
            global_PVs['Motor_SampleY'] = PV('32idcTXM:mxv:c1:m1.VAL') # for the TXM
            global_PVs['Motor_SampleRot'] = PV('32idcTXM:ens:c1:m1.VAL') # Professional Instrument air bearing 0y stage
            global_PVs['Motor_SampleRot_set'] = PV('32idcTXM:ens:c1:m1.SET') # Professional Instrument air bearing 0y stage
            global_PVs['Motor_SampleRot_Speed'] = PV('32idcTXM:ens:c1:m1.VELO') # Professional Instrument air bearing rotary stage
            global_PVs['Motor_SampleRot_Stop'] = PV('32idcTXM:ens:c1:m1.STOP') # PI Micos air bearing rotary stage
            global_PVs['Motor_Sample_Top_X'] = PV('32idcTXM:mcs:c3:m7.VAL') # Smaract XZ TXM set
            global_PVs['Motor_Sample_Top_X_RBV'] = PV('32idcTXM:mcs:c3:m7.RBV')
            global_PVs['Motor_Sample_Top_X_STATUS'] = PV('32idcTXM:mcs:c3:m7.MSTA') 
            global_PVs['Motor_Sample_Top_X_MIP'] = PV('32idcTXM:mcs:c3:m7.MIP') 
            global_PVs['Motor_Sample_Top_X_RETRY'] = PV('32idcTXM:mcs:c3:m7.RCNT')
            global_PVs['Motor_Sample_Top_X_StopAndGo'] = PV('32idcTXM:mcs:c3:m7.SPMG')
            global_PVs['Motor_Sample_Top_Z'] = PV('32idcTXM:mcs:c3:m8.VAL')
            global_PVs['Motor_Sample_Top_Z_StopAndGo'] = PV('32idcTXM:mcs:c3:m8.SPMG') # =0 --> Stop; =3 --> go
#           global_PVs['Motor_X_Tile'] = PV('32idc01:m33.VAL')
#           global_PVs['Motor_Y_Tile'] = PV('32idc02:m15.VAL')
    else: # micro-CT
            global_PVs['Motor_SampleX'] = PV('32idc01:m33.VAL')
            global_PVs['Motor_SampleY'] = PV('32idc02:m15.VAL') # for the micro-CT system
            global_PVs['Motor_SampleRot'] = PV('32idcTXM:hydra:c0:m1.VAL') # PI Micos air bearing rotary stage
            global_PVs['Motor_SampleRot_Stop'] = PV('32idcTXM:hydra:c0:m1.STOP') # PI Micos air bearing rotary stage
            global_PVs['Motor_SampleZ'] = PV('32idcTXM:mcs:c1:m1.VAL')
            global_PVs['Motor_Sample_Top_X'] = PV('32idcTXM:mcs:c1:m1.VAL') # Smaract XZ micro-CT set
            global_PVs['Motor_Sample_Top_X_RBV'] = PV('32idcTXM:mcs:c1:m1.RBV') # 
            global_PVs['Motor_Sample_Top_X_STATUS'] = PV('32idcTXM:mcs:c1:m1.MSTA')
            global_PVs['Motor_Sample_Top_X_MIP'] = PV('32idcTXM:mcs:c1:m1.MIP')
            global_PVs['Motor_Sample_Top_X_RETRY'] = PV('32idcTXM:mcs:c1:m1.RCNT')
            global_PVs['Motor_Sample_Top_Z'] = PV('32idcTXM:mcs:c1:m2.VAL') # Smaract XZ micro-CT set
            global_PVs['Motor_X_Tile'] = PV('32idc01:m33.VAL')
            global_PVs['Motor_Y_Tile'] = PV('32idc02:m15.VAL')
            global_PVs['Focus_10X'] = PV('32idcMCS2:c0:m1.VAL')
            global_PVs['Focus_5X'] = PV('32idcMCS2:c0:m2.VAL')

    #Zone plate:
    global_PVs['zone_plate_x'] = PV('32idcTXM:mcs:c2:m1.VAL')
    global_PVs['zone_plate_y'] = PV('32idcTXM:mcs:c2:m2.VAL')
    global_PVs['zone_plate_z'] = PV('32idcTXM:mcs:c2:m3.VAL')
    global_PVs['zone_plate_x_StopAndGo'] = PV('32idcTXM:mcs:c2:m1.SPMG')
    global_PVs['zone_plate_y_StopAndGo'] = PV('32idcTXM:mcs:c2:m2.SPMG')
    global_PVs['zone_plate_z_StopAndGo'] = PV('32idcTXM:mcs:c2:m3.SPMG')

    #Phase ring:
    global_PVs['phase_ring_x'] = PV('32idcSOFT:mmc:c1:m2.VAL')
    global_PVs['phase_ring_y'] = PV('32idcSOFT:mmc:c1:m1.VAL')

    # MST2 = vertical axis
#   global_PVs['Smaract_mode'] = PV('32idcTXM:mcsAsyn1.AOUT') # pv.Smaract_mode.put(':MST3,100,500,100')
#   global_PVs['zone_plate_2_x'] = PV('32idcTXM:mcs:c0:m3.VAL')
#   global_PVs['zone_plate_2_y'] = PV('32idcTXM:mcs:c0:m1.VAL')
#   global_PVs['zone_plate_2_z'] = PV('32idcTXM:mcs:c0:m2.VAL')

    # Condenser:
    global_PVs['condenser_x'] = PV('32idcTXM:mcs:c3:m1.VAL')
    global_PVs['condenser_y'] = PV('32idcTXM:mcs:c3:m5.VAL')
    global_PVs['condenser_z'] = PV('32idcTXM:mxv:c1:m5.VAL')
    global_PVs['condenser_yaw'] = PV('32idcTXM:mcs:c3:m2.VAL')
    global_PVs['condenser_pitch'] = PV('32idcTXM:mcs3:m4.VAL')
    global_PVs['shaker_actuator'] = PV('32idcMC:shaker:run') # 0=stop, 1=run

    # Beam stop:
    global_PVs['beam_stop_x'] = PV('32idcTXM:mcs:c2:m1.VAL')
    global_PVs['beam_stop_y'] = PV('32idcTXM:mcs:c3:m6.VAL')

    # Pinhole:
    global_PVs['pin_hole_x'] = PV('32idcTXM:xps:c1:m3.VAL')
    global_PVs['pin_hole_y'] = PV('32idcTXM:xps:c1:m5.VAL')

    # Diffuser:
    global_PVs['diffuser_x'] = PV('32idcTXM:xps:c1:m2.VAL')

    # BPM:
    global_PVs['BPM_vert_readback'] = PV('32ida:fb3.VAL')
    global_PVs['BPM_horiz_readback'] = PV('32ida:fb4.VAL')
    
    # Feedback Loop DCM - BPM:
    global_PVs['BPM_DCM_Vert_FBL'] = PV('32ida:fb3.FBON') # 0=off, 1=ON
    global_PVs['BPM_DCM_Horiz_FBL'] = PV('32ida:fb4.FBON') # 0=off, 1=ON

    # CRL:
    #crl_actuators = PV('32idb:pfcu:sendCommand.VAL')
    global_PVs['crl_actuators_0'] = PV('32idbPLC:oY0')
    global_PVs['crl_actuators_1'] = PV('32idbPLC:oY1')
    global_PVs['crl_actuators_2'] = PV('32idbPLC:oY2')
    global_PVs['crl_actuators_3'] = PV('32idbPLC:oY3')
    global_PVs['crl_actuators_4'] = PV('32idbPLC:oY4')
    global_PVs['crl_actuators_5'] = PV('32idbPLC:oY5')
    global_PVs['crl_actuators_6'] = PV('32idbPLC:oY6')
    global_PVs['crl_actuators_7'] = PV('32idbPLC:oY7')

    # CCD motors:
    global_PVs['CCD_Motor'] = PV('32idcTXM:mxv:c1:m6.VAL')

    #shutter pv's:
    global_PVs['ShutterA_Open'] = PV('32idb:rshtrA:Open')
    global_PVs['ShutterA_Close'] = PV('32idb:rshtrA:Close')
    global_PVs['ShutterA_Move_Status'] = PV('PB:32ID:STA_A_FES_CLSD_PL')
    global_PVs['ShutterB_Open'] = PV('32idb:fbShutter:Open.PROC')
    global_PVs['ShutterB_Close'] = PV('32idb:fbShutter:Close.PROC')
    global_PVs['ShutterB_Move_Status'] = PV('PB:32ID:STA_B_SBS_CLSD_PL')
    global_PVs['ExternalShutter_Trigger'] = PV('32idcTXM:shutCam:go')
    # Fast shutter controls:
    global_PVs['Softglue_Shutter'] = PV('32idcTXM:SG3:DnCntr-1_PRESET') # Should be always 1
    global_PVs['Fast_Shutter_Uniblitz'] = PV('32idcTXM:uniblitz:control') # State 0 = Close, 1 = Open
    global_PVs['Fast_Shutter_Open'] = PV('32idcTXM:shutCam:ShutterManual')
    global_PVs['Fast_Shutter_Delay'] = PV('32idcTXM:shutCam:tDly')
    global_PVs['Fast_Shutter_Exposure'] = PV('32idcTXM:shutCam:tExpose')
    global_PVs['Fast_Shutter_Trigger'] = PV('32idcTXM:shutCam:go')
    global_PVs['Fast_Shutter_Trigger_Mode'] = PV('32idcTXM:shutCam:Triggered') # Manual / Triggered synchronization
    global_PVs['Fast_Shutter_Control'] = PV('32idcTXM:shutCam:ShutterCtrl') # Shutter control: manual or Auto
    global_PVs['Fast_Shutter_Relay'] = PV('32idcTXM:shutCam:Enable')
    global_PVs['Fast_Shutter_Trigger_Source'] = PV('32idcTXM:flyTriggerSelect')
    global_PVs['Fast_Shutter_Uniblitz'] = PV('32idcTXM:uniblitz:control')

    #fly macro:
    global_PVs['FlyTriggerSelect'] = PV('32idcTXM:flyTriggerSelect')
    if not TXM: # for the PI Micos
            global_PVs['FlyTriggerSelect'].put(0, wait=True)
            global_PVs['Set_encoder_to_motor_RBV'] = PV('32idcTXM:eFly:setEncoderPos')
            global_PVs['Set_encoder_to_motor_RBV'].put(1, wait=True)
            global_PVs['Fly_ScanDelta'] = PV('32idcTXM:eFly:scanDelta')
            global_PVs['Fly_StartPos'] = PV('32idcTXM:eFly:startPos')
            global_PVs['Fly_EndPos'] = PV('32idcTXM:eFly:endPos')
            global_PVs['Fly_SlewSpeed'] = PV('32idcTXM:eFly:slewSpeed')
            global_PVs['Fly_Taxi'] = PV('32idcTXM:eFly:taxi')
            global_PVs['Fly_Run'] = PV('32idcTXM:eFly:fly')
            global_PVs['Fly_ScanControl'] = PV('32idcTXM:eFly:scanControl')
            global_PVs['Fly_Calc_Projections'] = PV('32idcTXM:eFly:calcNumTriggers')
            global_PVs['Fly_Set_Encoder_Pos'] = PV('32idcTXM:eFly:EncoderPos')
            global_PVs['Theta_Array'] = PV('32idcTXM:eFly:motorPos.AVAL')

    else: # for the Professional Instrument
            global_PVs['FlyTriggerSelect'].put(1, wait=True)
#           global_PVs['custom_standard_scan'] = PV('32idcTXM:PSOFly3:scanControl') 
            global_PVs['Fly_ScanDelta'] = PV('32idcTXM:PSOFly3:scanDelta')
            global_PVs['Fly_StartPos'] = PV('32idcTXM:PSOFly3:startPos')
            global_PVs['Fly_EndPos'] = PV('32idcTXM:PSOFly3:endPos')
            global_PVs['Fly_SlewSpeed'] = PV('32idcTXM:PSOFly3:slewSpeed')
            global_PVs['Fly_Taxi'] = PV('32idcTXM:PSOFly3:taxi')
            global_PVs['Fly_Run'] = PV('32idcTXM:PSOFly3:fly')
            global_PVs['Fly_ScanControl'] = PV('32idcTXM:PSOFly3:scanControl')    # 0=standard; 1=custom
            global_PVs['Fly_Calc_Projections'] = PV('32idcTXM:PSOFly3:numTriggers')
            global_PVs['Theta_Array'] = PV('32idcTXM:PSOFly3:motorPos.AVAL')
            global_PVs['Fly_Set_Encoder_Pos'] = PV('32idcTXM:eFly:EncoderPos')

    # theta controls
    global_PVs['Reset_Theta'] = PV('32idcTXM:SG_RdCntr:reset.PROC')
    global_PVs['Proc_Theta'] = PV('32idcTXM:SG_RdCntr:cVals.PROC')
    global_PVs['Theta_Cnt'] = PV('32idcTXM:SG_RdCntr:aSub.VALB')

    #init misc pv's
    global_PVs['Image1_Callbacks'] = PV(variableDict['IOC_Prefix'] + 'image1:EnableCallbacks')
    global_PVs['ExternShutterExposure'] = PV('32idcTXM:shutCam:tExpose')
    #global_PVs['ClearTheta'] = PV('32idcTXM:recPV:PV1_clear')
    global_PVs['ExternShutterDelay'] = PV('32idcTXM:shutCam:tDly')

    # PV for the Attocube interferometers:
    global_PVs['Interfero_ZPX'] = PV('32MZ0:1pixelTriggerDma.VALA')
    global_PVs['Interfero_ZPY'] = PV('32MZ0:1pixelTriggerDma.VALB')
    global_PVs['det_trig_pulses'] = PV('32MZ0:1pixelTriggerDma.VALE')

    # OLD PV related to the Renishaw interferometers:
#   global_PVs['Interferometer'] = PV('32idcTXM:SG2:UpDnCntr-1_COUNTS_s')
#   global_PVs['Interferometer_Update'] = PV('32idcTXM:SG2:UpDnCntr-1_COUNTS_SCAN.PROC')
#   global_PVs['Interferometer_Reset'] = PV('32idcTXM:SG_RdCntr:reset.PROC')
#   global_PVs['Interferometer_Cnt'] = PV('32idcTXM:SG_RdCntr:aSub.VALB')
#   global_PVs['Interferometer_Arr'] = PV('32idcTXM:SG_RdCntr:cVals.AA')
#   global_PVs['Interferometer_Proc_Arr'] = PV('32idcTXM:SG_RdCntr:cVals.PROC')
#   global_PVs['Interferometer_Val'] = PV('32idcTXM:userAve4.VAL')
#   global_PVs['Interferometer_Mode'] = PV('32idcTXM:userAve4_mode.VAL')
#   global_PVs['Interferometer_Acquire'] = PV('32idcTXM:userAve4_acquire.PROC')

    #init proc1 pv's
    global_PVs['Proc1_Callbacks'] = PV(variableDict['IOC_Prefix'] + 'Proc1:EnableCallbacks')
    global_PVs['Proc1_ArrayPort'] = PV(variableDict['IOC_Prefix'] + 'Proc1:NDArrayPort')
    global_PVs['Proc1_Filter_Enable'] = PV(variableDict['IOC_Prefix'] + 'Proc1:EnableFilter')
    global_PVs['Proc1_Filter_Type'] = PV(variableDict['IOC_Prefix'] + 'Proc1:FilterType')
    global_PVs['Proc1_Num_Filter'] = PV(variableDict['IOC_Prefix'] + 'Proc1:NumFilter')
    global_PVs['Proc1_Reset_Filter'] = PV(variableDict['IOC_Prefix'] + 'Proc1:ResetFilter')
    global_PVs['Proc1_AutoReset_Filter'] = PV(variableDict['IOC_Prefix'] + 'Proc1:AutoResetFilter')
    global_PVs['Proc1_Filter_Callbacks'] = PV(variableDict['IOC_Prefix'] + 'Proc1:FilterCallbacks')

        #energy
    global_PVs['DCMmvt'] = PV('32ida:KohzuModeBO.VAL')
    global_PVs['GAPputEnergy'] = PV('32id:ID32us_energy')
    global_PVs['EnergyWait'] = PV('ID32us:Busy')
    global_PVs['DCMputEnergy'] = PV('32ida:BraggEAO.VAL')

    #interlaced
    global_PVs['Interlaced_PROC'] = PV('32idcTXM:iFly:interlaceFlySub.PROC')
    global_PVs['Interlaced_Theta_Arr'] = PV('32idcTXM:iFly:interlaceFlySub.VALC')
    global_PVs['Interlaced_Num_Cycles'] = PV('32idcTXM:iFly:interlaceFlySub.C')
    global_PVs['Interlaced_Num_Cycles_RBV'] = PV('32idcTXM:iFly:interlaceFlySub.VALH')
    global_PVs['Interlaced_Images_Per_Cycle'] = PV('32idcTXM:iFly:interlaceFlySub.A')
    global_PVs['Interlaced_Images_Per_Cycle_RBV'] = PV('32idcTXM:iFly:interlaceFlySub.VALF')
    global_PVs['Interlaced_Num_Sub_Cycles'] = PV('32idcTXM:iFly:interlaceFlySub.B')
    global_PVs['Interlaced_Num_Sub_Cycles_RBV'] = PV('32idcTXM:iFly:interlaceFlySub.VALG')
    log_lib.info('  *** Init general PVs: Done!')


def stop_scan(global_PVs, variableDict):
    log_lib.info(' ')
    log_lib.info('  *** Stop scan')
    global_PVs['Motor_SampleRot_Stop'].put(1)
    global_PVs['TIFF1_AutoSave'].put('No')
    global_PVs['TIFF1_Capture'].put(0)
    global_PVs['HDF1_Capture'].put(0)
    wait_pv(global_PVs['HDF1_Capture'], 0)
    reset_CCD(global_PVs, variableDict)
    reset_CCD(global_PVs, variableDict)
    disable_fast_shutter(global_PVs, variableDict)
    enable_smaract(global_PVs, variableDict)
    log_lib.info('  *** Stop scan: Done!')


def reset_CCD(global_PVs, variableDict):
    if 1: # Usual script
        global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)    # 
        global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True)  # sequence Internal / Overlapped / internal because of CCD bug!!
        global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)    #
        global_PVs['Proc1_Filter_Callbacks'].put( 'Every array' )
        #   global_PVs['HDF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
        global_PVs['Cam1_ImageMode'].put('Continuous', wait=True)
        if TXM == False:
            global_PVs['Cam1_FrameRate_on_off'].put(1, wait=True) # force a slow frame rate for the display
            global_PVs['Cam1_FrameRate_val'].put(5, wait=True) # force a slow frame rate for the display --> 5 fps
        global_PVs['Cam1_Display'].put(1)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire); wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)

    else:

        global_PVs['Cam1_NumImages'].put(100000000, wait=True)
        global_PVs['Cam1_AcquireTime'].put(1)
        global_PVs['Cam1_AcquirePeriod'].put(1)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire) # Start acquiring state
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 1)

        # Start the fake streaming mode:
        streaming_mode = 1
        while streaming_mode:
            global_PVs['Cam1_SoftwareTrigger'].put(1) # push the software trigger button
            time.sleep(0.4)
            if global_PVs['Cam1_Acquire'].get() == 0: # checking acquiring still ON
                streaming_mode == 0


def setup_detector(global_PVs, variableDict):
    log_lib.info(' ')
    log_lib.info('  *** setup_detector')
    if variableDict.has_key('Display_live'):
        log_lib.info('  *** *** disable live display')
        global_PVs['Cam1_Display'].put( int( variableDict['Display_live'] ) )
    global_PVs['Cam1_ImageMode'].put('Multiple')
    global_PVs['Cam1_ArrayCallbacks'].put('Enable')
    #global_PVs['Image1_Callbacks'].put('Enable')
    global_PVs['Cam1_AcquirePeriod'].put(float(variableDict['ExposureTime']))
    global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']))
    # if we are using external shutter then set the exposure time
    global_PVs['Cam1_FrameRateOnOff'].put(0)
    # if software trigger capture two frames (issue with Point grey grasshopper)
    if PG_Trigger_External_Trigger == 1:
        wait_time_sec = int(variableDict['ExposureTime']) + 5
#       global_PVs['Cam1_TriggerMode'].put('Ext. Standard', wait=True) #Ext. Standard
        global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True) #Ext. Standard
        global_PVs['Cam1_NumImages'].put(1, wait=True)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
    else:
        global_PVs['Cam1_TriggerMode'].put('Internal')
    #global_PVs['ClearTheta'].put(1)
    log_lib.info('  *** setup_detector: Done!')


def setup_writer(global_PVs, variableDict, filename=None):
    log_lib.info('  ')
    log_lib.info('  *** setup hdf_writer')
    global_PVs['HDF1_LazyOpen'].put(0)
    if variableDict.has_key('Recursive_Filter_Enabled'):
        if variableDict['Recursive_Filter_Enabled'] == 1:
#           global_PVs['Proc1_Callbacks'].put('Disable')
            global_PVs['Proc1_Callbacks'].put('Enable')
            global_PVs['Proc1_Filter_Enable'].put('Disable')
            global_PVs['HDF1_ArrayPort'].put('PROC1')
            global_PVs['Proc1_Filter_Type'].put( Recursive_Filter_Type )
            global_PVs['Proc1_Num_Filter'].put( int( variableDict['Recursive_Filter_N_Images'] ) )
            global_PVs['Proc1_Reset_Filter'].put( 1 )
            global_PVs['Proc1_AutoReset_Filter'].put( 'Yes' )
            global_PVs['Proc1_Filter_Callbacks'].put( 'Array N only' )
        else:
#           global_PVs['Proc1_Callbacks'].put('Disable')
            global_PVs['Proc1_Filter_Enable'].put('Disable')
            global_PVs['HDF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
    else:
#       global_PVs['Proc1_Callbacks'].put('Disable')
        global_PVs['Proc1_Filter_Enable'].put('Disable')
        global_PVs['HDF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
    global_PVs['HDF1_AutoSave'].put('Yes')
    global_PVs['HDF1_DeleteDriverFile'].put('No')
    global_PVs['HDF1_EnableCallbacks'].put('Enable')
    global_PVs['HDF1_BlockingCallbacks'].put('No')
    if variableDict.has_key('ProjectionsPerRot'):
        totalProj = int(variableDict['PreDarkImages']) + int(variableDict['PreWhiteImages']) + ( int(variableDict['Projections']) * int(variableDict['ProjectionsPerRot'])) + int(variableDict['PostDarkImages']) + int(variableDict['PostWhiteImages'])
    else:
        totalProj = int(variableDict['PreDarkImages']) + int(variableDict['PreWhiteImages']) + int(variableDict['Projections']) + int(variableDict['PostDarkImages']) + int(variableDict['PostWhiteImages'])
    global_PVs['HDF1_NumCapture'].put(totalProj)
    global_PVs['HDF1_FileWriteMode'].put(str(variableDict['FileWriteMode']), wait=True)
    if not filename == None:
        global_PVs['HDF1_FileName'].put(filename)
    global_PVs['HDF1_Capture'].put(1)
    wait_pv(global_PVs['HDF1_Capture'], 1)
    log_lib.info('  *** setup hdf_writer: Done!')


def setup_tiff_writer(global_PVs, variableDict, filename=None):
    log_lib.info('  ')
    log_lib.info('  *** setup_tiff_writer')
    global_PVs['TIFF1_ArrayPort'].put(variableDict['TIFFNDArrayPort'], wait=True)
    if variableDict.has_key('Recursive_Filter_Enabled'):
        if variableDict['Recursive_Filter_Enabled'] == 1:
#           global_PVs['Proc1_Callbacks'].put('Disable')
            global_PVs['Proc1_Callbacks'].put('Enable')
            global_PVs['Proc1_Filter_Enable'].put('Disable')
            global_PVs['TIFF1_ArrayPort'].put('PROC1')
            global_PVs['Proc1_Filter_Type'].put( Recursive_Filter_Type )
            global_PVs['Proc1_Num_Filter'].put( int( variableDict['Recursive_Filter_N_Images'] ) )
            global_PVs['Proc1_Reset_Filter'].put( 1 )
            global_PVs['Proc1_AutoReset_Filter'].put( 'Yes' )
            global_PVs['Proc1_Filter_Callbacks'].put( 'Array N only' )
#       else:
##          global_PVs['Proc1_Callbacks'].put('Disable')
#           global_PVs['Proc1_Filter_Enable'].put('Disable')
#           global_PVs['TIFF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
#   else:
##      global_PVs['Proc1_Callbacks'].put('Disable')
#       global_PVs['Proc1_Filter_Enable'].put('Disable')
#       global_PVs['TIFF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
    global_PVs['TIFF1_AutoSave'].put('Yes')
    global_PVs['TIFF1_DeleteDriverFile'].put('No')
    global_PVs['TIFF1_EnableCallbacks'].put('Enable')
    global_PVs['TIFF1_BlockingCallbacks'].put('No')
    totalProj = int(variableDict['Projections'])
    global_PVs['TIFF1_NumCapture'].put(totalProj)
    global_PVs['TIFF1_FileWriteMode'].put(str(variableDict['FileWriteMode']), wait=True)
    if not filename == None:
        global_PVs['TIFF1_FileName'].put(filename)
    global_PVs['TIFF1_Capture'].put(1)
    wait_pv(global_PVs['TIFF1_Capture'], 1)
    log_lib.info('  *** setup_tiff_writer: Done!')

def acquire_proj(global_PVs, variableDict):
    global_PVs['Cam1_Acquire'].put(DetectorAcquire)
    wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
    if variableDict['Use_Fast_Shutter']:
        global_PVs['Fast_Shutter_Trigger'].put(1)
#                wait_pv(global_PVs['Fast_Shutter_Trigger'], DetectorIdle, 60)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)
    else:
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)

def capture_multiple_projections(global_PVs, variableDict, num_proj, frame_type):
    log_lib.info('       ***  capture_multiple_projections %d ' % num_proj)
    wait_time_sec = int(variableDict['ExposureTime']) + 5
    global_PVs['Cam1_ImageMode'].put('Multiple')
    global_PVs['Cam1_FrameType'].put(frame_type)
    if PG_Trigger_External_Trigger == 1:
        #set external trigger mode
        global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True)
        global_PVs['Cam1_NumImages'].put(1)
        for i in range(int(num_proj)):
            global_PVs['Cam1_Acquire'].put(DetectorAcquire)
            wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
            global_PVs['Cam1_SoftwareTrigger'].put(1)
            wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
    else:
        global_PVs['Cam1_TriggerMode'].put('Internal')
        global_PVs['Cam1_NumImages'].put(int(num_proj))
        global_PVs['Cam1_Acquire'].put(DetectorAcquire, wait=True)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
    log_lib.info('       ***  capture_multiple_projections: Done!')

def acquire_proj_recursive_filt(global_PVs, variableDict):
    global_PVs['Proc1_Callbacks'].put('Enable', wait=True)
    for k in range(int(variableDict['Recursive_Filter_N_Images'])):
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        if variableDict['Use_Fast_Shutter']:
            global_PVs['Fast_Shutter_Trigger'].put(1)
#           wait_pv(global_PVs['Fast_Shutter_Trigger'], DetectorIdle, 60)
            wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)
        else:
            global_PVs['Cam1_SoftwareTrigger'].put(1)
            wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)
    log_lib.info('       ***  capture with rec. filt.: Done!')

def acq_mutliple_proj_per_rot(global_PVs, variableDict):
    for j in range( int(variableDict['ProjectionsPerRot']) ):
        log_lib.info('    acq. proj %i/%i' % (j+1, variableDict['ProjectionsPerRot']))
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        if variableDict['Use_Fast_Shutter']:
            global_PVs['Fast_Shutter_Trigger'].put(1)
#                    wait_pv(global_PVs['Fast_Shutter_Trigger'], DetectorIdle, 60)
            wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)
        else:
            global_PVs['Cam1_SoftwareTrigger'].put(1)
            wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)

def move_sample_in(global_PVs, variableDict):
    log_lib.info('       ***  move_sample_in: %s ' % str(variableDict['SampleXIn']))
#   global_PVs['Motor_X_Tile'].put(float(variableDict['SampleXIn']), wait=True)
#   global_PVs['Motor_SampleX'].put(float(variableDict['SampleXIn']), wait=True)
    global_PVs['Motor_Sample_Top_X'].put(float(variableDict['SampleXIn']), wait=True)
    global_PVs['Motor_Sample_Top_Z'].put(float(variableDict['SampleZIn']), wait=True)
    if False == wait_pv(global_PVs['Motor_Sample_Top_X_RBV'], float(variableDict['SampleXIn']), 60):
        log_lib.error('       ***  Motor_Sample_Top_X did not move in properly')
        print(global_PVs['Motor_Sample_Top_X_STATUS'].get())
        print(global_PVs['Motor_Sample_Top_X_MIP'].get())
        print(global_PVs['Motor_Sample_Top_X_RETRY'].get())
#   global_PVs['Motor_Sample_Top_Z'].put(float(variableDict['SampleZIn']), wait=True)
#   global_PVs['Motor_SampleY'].put(float(variableDict['SampleYIn']), wait=True)
#   global_PVs['Motor_SampleZ'].put(float(variableDict['SampleZIn']), wait=True)
#   global_PVs['Motor_SampleRot'].put(0, wait=True)
    log_lib.info('       ***  move_sample_in: %s: Done! ' % str(variableDict['SampleXIn']))


def move_sample_out(global_PVs, variableDict):
    # print 'move_sample_out()'
    log_lib.info('       ***  move_sample_out: %s ' % str(variableDict['SampleXOut']))
#   global_PVs['Motor_SampleRot'].put(float(variableDict['SampleRotOut']), wait=True)
#   global_PVs['Motor_X_Tile'].put(float(variableDict['SampleXOut']), wait=True)
#   global_PVs['Motor_SampleX'].put(float(variableDict['SampleXOut']), wait=True)
    global_PVs['Motor_Sample_Top_X'].put(float(variableDict['SampleXOut']), wait=True)
    global_PVs['Motor_Sample_Top_Z'].put(float(variableDict['SampleZOut']), wait=True)
    #global_PVs['Motor_SampleRot'].put(float(variableDict['SampleRotOut']), wait=True)
    if False == wait_pv(global_PVs['Motor_Sample_Top_X_RBV'], float(variableDict['SampleXOut']), 60):
        log_lib.error('       ***  Motor_Sample_Top_X did not move out properly')
        print(global_PVs['Motor_Sample_Top_X_STATUS'].get())
        print(global_PVs['Motor_Sample_Top_X_MIP'].get())
        print(global_PVs['Motor_Sample_Top_X_RETRY'].get())
#   global_PVs['Motor_Sample_Top_Z'].put(float(variableDict['SampleZOut']), wait=True)
#   global_PVs['Motor_SampleY'].put(float(variableDict['SampleYOut']), wait=True)
#   global_PVs['Motor_SampleZ'].put(float(variableDict['SampleZOut']), wait=True)
#   global_PVs['Motor_SampleRot'].put(0, wait=True)
    log_lib.info('       ***  move_sample_out: %s: Done!' % str(variableDict['SampleXOut']))

def open_shutters(global_PVs, variableDict):
    log_lib.info('       ***  open_shutters')
    if TESTING_MODE:
        log_lib.warning('       ***  testing mode - shutters are deactivated during the scans !!!!')
    else:
        if UseShutterA:
            global_PVs['ShutterA_Open'].put(1, wait=True)
            wait_pv(global_PVs['ShutterA_Move_Status'], ShutterA_Open_Value)
            time.sleep(3)
        if UseShutterB:
            global_PVs['ShutterB_Open'].put(1, wait=True)
            wait_pv(global_PVs['ShutterB_Move_Status'], ShutterB_Open_Value)
    log_lib.info('       ***  open_shutters: Done!')


def close_shutters(global_PVs, variableDict):
    log_lib.info('       ***  close_shutters')
    if TESTING_MODE:
        log_lib.warning('       ***  testing mode - shutters are deactivated during the scans !!!!')
    else:    
        if UseShutterA:
            global_PVs['ShutterA_Close'].put(1, wait=True)
            wait_pv(global_PVs['ShutterA_Move_Status'], ShutterA_Close_Value)
        if UseShutterB:
            global_PVs['ShutterB_Close'].put(1, wait=True)
            wait_pv(global_PVs['ShutterB_Move_Status'], ShutterB_Close_Value)
    log_lib.info('       ***  close_shutter: Done!')

def enable_fast_shutter(global_PVs, variableDict, rotation_trigger=False, delay=0.02):
    """Enable the hardware-triggered fast shutter.
    
    When this shutter is enabled, actions that capture a
    projection from the CCD will first open the fast shutter, then
    close it again afterwards. With ``rotation_trigger=True``, the
    CCD and shutter are triggered directly by the rotation stage
    (useful for fly scans). This method leaves the shutter closed
    by default.
    
    Parameters
    ----------
    rotation_trigger : bool, optional
      If false (default) the shutter/CCD are controlled by
      software. If true, the rotation stage encoder will trigger
      the shutter/CCD.
    delay : float, optional
      Time (in seconds) to wait for the fast shutter to close.
    
    """
    # Make sure Softglue circuit is configure correctly:
    global_PVs['Softglue_Shutter'].put(1, wait=True)
    # Close the shutter to start with
    global_PVs['Fast_Shutter_Control'].put(0, wait=True) # Manual mode
#    global_PVs['Fast_Shutter_Open'].put(0, wait=True) # Close the shutter
    # Determine what trigger the opening/closing of the shutter
    if rotation_trigger:
        # Put the FPGA input under rotary encoder control
        global_PVs['Fast_Shutter_Trigger_Mode'].put(1, wait=True) # Rotation stage encoder trigger mode
    else:
        # Put the FPGA input under software control
        global_PVs['Fast_Shutter_Trigger_Mode'].put(0, wait=True) # Manual trigger mode
    # Connect the shutter to the FPGA
    global_PVs['Fast_Shutter_Control'].put(1, wait=True) # Auto mode
    # Connect the camera to the fast shutter FPGA
    global_PVs['Fast_Shutter_Relay'].put(1, wait=True) # FAST_SHUTTER_RELAY_SYNCED
    # Set the FPGA trigger to the rotary encoder for this TXM
    global_PVs['Fast_Shutter_Trigger_Source'].put((TXM)) # 0 for the hydra, 1 for the TXM ensemble
    # Set the status flag for later use
#    fast_shutter_enabled = True
    # Set the camera delay
    global_PVs['Fast_Shutter_Delay'].put(delay, wait=True)
    # Disable the "uniblitz" fast shutter safety
    global_PVs['Fast_Shutter_Uniblitz'].put(0, wait=True)
    global_PVs['Fast_Shutter_Exposure'].put(float(variableDict['ExposureTime']) , wait=True)


def disable_fast_shutter(global_PVs, variableDict):
    """Disable the hardware-triggered fast shutter.
    
    This returns the TXM to the conventional software trigger
    mode, with the fast shutter open.

    """
    # Connect the trigger to the rotary encoder (to be safe)
    global_PVs['Fast_Shutter_Trigger_Mode'].put(1, wait=True) # FAST_SHUTTER_TRIGGER_ROTATION
    # Disconnect the shutter from the FPGA
    global_PVs['Fast_Shutter_Control'].put(0, wait=True) # FAST_SHUTTER_CONTROL_MANUAL
    # Connect the camera to the fast shutter FPGA
    global_PVs['Fast_Shutter_Relay'].put(0, wait=True) # FAST_SHUTTER_RELAY_DIRECT --> just trigger the camera
    # Set the FPGA trigger to the rotary encoder for this TXM
    global_PVs['Fast_Shutter_Trigger_Source'].put(int(TXM), wait=True)
    # Set the status flag for later use
#    fast_shutter_enabled = False
    # Open the shutter so it doesn't interfere with measurements
    global_PVs['Fast_Shutter_Open'].put(1, wait=True) # 0 = closed. It works because control mode switched to 0 above


def auto_focus_microCT(global_PVs, variableDict, rscan_range, nSteps, ScanMotorName):
    log_lib.info('  ***  start auto focus scan...')
    init_general_PVs(global_PVs, variableDict)

    if variableDict.has_key('StopTheScan'): # stopping the scan in a clean way
        stop_scan(global_PVs, variableDict)
    return
    setup_detector(global_PVs, variableDict)
    open_shutters(global_PVs, variableDict)

    # Get the CCD parameters:
    nRow = global_PVs['nRow'].get()
    nCol = global_PVs['nCol'].get()
    image_size = nRow * nCol

    Motor_Name = ScanMotorName
    log_lib.info('       ***  Scanning %s ' % Motor_Name)

    Motor_Start_Pos = global_PVs[Motor_Name].get() - rscan_range/2
    Motor_End_Pos = global_PVs[Motor_Name].get() + rscan_range/2
    vector_pos = numpy.linspace(Motor_Start_Pos, Motor_End_Pos, nSteps)
    vector_std = numpy.copy(vector_pos)

    global_PVs['Cam1_FrameType'].put(FrameTypeData, wait=True)
    global_PVs['Cam1_NumImages'].put(1, wait=True)
    
    cnt = 0
    for sample_pos in vector_pos:
        log_lib.info('       *** *** Motor position: %f' % sample_pos)
        global_PVs[Motor_Name].put(sample_pos, wait=True)
        time.sleep(0.25)

        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, 60)
        
        # Get the image loaded in memory
        img_vect = global_PVs['Cam1_Image'].get(count=image_size)
        #img = np.reshape(img_vect,[nRow, nCol])
        vector_std[cnt] = numpy.std(img_vect)
        log_lib.info('       *** *** Standard deviation: %s ' % str(vector_std[cnt]))
        cnt = cnt + 1

    # move the lens to the focal position:
    max_std = numpy.max(vector_std)
    focal_pos = vector_pos[numpy.where(vector_std == max_std)]
    log_lib.info('  *** *** Highest standard deviation: %s ' % str(max_std))
    log_lib.info('  *** *** Move piezo to %s ' % str(focal_pos))
    global_PVs[Motor_Name].put(focal_pos, wait=True)

    close_shutters(global_PVs, variableDict)
    reset_CCD(global_PVs, variableDict)


def disable_smaract(global_PVs, variableDict):
    log_lib.info('       ***  disabling the Smaract')
    global_PVs['zone_plate_x_StopAndGo'].put(0, wait=True)
    global_PVs['zone_plate_y_StopAndGo'].put(0, wait=True)
    global_PVs['zone_plate_z_StopAndGo'].put(0, wait=True)
    global_PVs['Motor_Sample_Top_X_StopAndGo'].put(0, wait=True) # 3=Go, 2=Move, 1=Pause, 0=Stop
    global_PVs['Motor_Sample_Top_Z_StopAndGo'].put(0, wait=True)
    log_lib.info('       ***  disabling the Smaract: Done!')
    
    
def enable_smaract(global_PVs, variableDict):
    log_lib.info('       ***  re-enabling the Smaract')
    global_PVs['zone_plate_x_StopAndGo'].put(3, wait=True)
    global_PVs['zone_plate_y_StopAndGo'].put(3, wait=True)
    global_PVs['zone_plate_z_StopAndGo'].put(3, wait=True)
    global_PVs['Motor_Sample_Top_X_StopAndGo'].put(3, wait=True) # 3=Go, 2=Move, 1=Pause, 0=Stop
    global_PVs['Motor_Sample_Top_Z_StopAndGo'].put(3, wait=True)
    log_lib.info('       ***  re-enabling the Smaract: Done!')
    

def add_theta(global_PVs, variableDict, theta_arr):
    log_lib.info('       ***  add_theta')
    fullname = global_PVs['HDF1_FullFileName_RBV'].get(as_string=True)
    try:
        hdf_f = h5py.File(fullname, mode='a')
        if theta_arr is not None:
            theta_ds = hdf_f.create_dataset('/exchange/theta', (len(theta_arr),))
            theta_ds[:] = theta_arr[:]
        hdf_f.close()
        log_lib.info('       ***  add_theta: Done!')
    except:
        traceback.print_exc(file=sys.stdout)
        log_lib.error('       ***  add_theta: Failed accessing:', fullname)

def update_theta_for_more_proj(orig_theta, variableDict):
    new_theta = []
    for val in orig_theta:
        for j in range( int(variableDict['ProjectionsPerRot']) ):
            new_theta += [val]
    return new_theta


def add_interferometer(global_PVs, variableDict, theta):
    if variableDict.has_key('UseInterferometer') and int(variableDict['UseInterferometer']) > 0:
            interf_zpx = global_PVs['Interfero_ZPX'].get()
            interf_zpy = global_PVs['Interfero_ZPY'].get()
            det_trig_pulses = global_PVs['det_trig_pulses'].get()
            add_interfero_hdf5(global_PVs, variableDict, interf_zpx,interf_zpy, det_trig_pulses)


def add_interfero_hdf5(global_PVs, variableDict, interf_zpx_arrs, interf_zpy_arrs, det_trig_pulses_arrs):
    log_lib.info(' ')
    log_lib.info('       ***  add_interfero_hdf5')
    wait_pv(global_PVs['HDF1_Capture_RBV'], 0, 10.0)
    fullname = global_PVs['HDF1_FullFileName_RBV'].get(as_string=True)
    try:
        log_lib.info('       ***  opening hdf5 file %s ' % fullname)
        hdf_f = h5py.File(fullname, mode='a')
        interf_zpx_ds = hdf_f.create_dataset('/measurement/instrument/interferometer/interfero_zpx_arrs', (len(interf_zpx_arrs),), dtype='f' )
        interf_zpx_ds[:] = interf_zpx_arrs[:]
        interf_zpy_ds = hdf_f.create_dataset('/measurement/instrument/interferometer/interfero_zpy_arrs', (len(interf_zpy_arrs),), dtype='f' )
        interf_zpy_ds[:] = interf_zpy_arrs[:]
        interf_trig_ds = hdf_f.create_dataset('/measurement/instrument/interferometer/det_trig_pulses_arrs', (len(det_trig_pulses_arrs),), dtype='f' )
        interf_trig_ds[:] = det_trig_pulses_arrs[:]
#       for i in range(len(interf_arrs)):
#           if len(interf_arrs[i]) == len(interf_arrs[0]):
#               interf_ds[i,:] = interf_arrs[i][:]
        hdf_f.close()
        log_lib.info('       ***  add_interfero_hdf5: Done')

    except:
        traceback.print_exc(file=sys.stdout)
        log_lib.error('       ***  add_interfero_hdf5: Failed accessing: %s' % fullname)


def setPSO(global_PVs, variableDict):
    log_lib.info(' ')
    log_lib.info('  *** get_calculated_num_projections')
    delta = abs((float(variableDict['SampleEndPos']) - float(variableDict['SampleStartPos'])) / (float(variableDict['Projections'])))
    slew_speed = (float(variableDict['SampleEndPos']) - float(variableDict['SampleStartPos'])) / (float(variableDict['Projections']) * (float(variableDict['ExposureTime']) + float(variableDict['CCD_Readout'])))
    log_lib.info('  *** *** start pos %f' % float(variableDict['SampleStartPos']))
    log_lib.info('  *** *** end pos %f' % float(variableDict['SampleEndPos']))
    global_PVs['Fly_StartPos'].put(float(variableDict['SampleStartPos']), wait=True)
    global_PVs['Fly_EndPos'].put(float(variableDict['SampleEndPos']), wait=True)
    global_PVs['Fly_SlewSpeed'].put(slew_speed, wait=True)
    global_PVs['Fly_ScanDelta'].put(delta, wait=True)
    time.sleep(3.0)
    calc_num_proj = global_PVs['Fly_Calc_Projections'].get()
    log_lib.info('  *** *** calculated number of projections: %f' % calc_num_proj)
    if calc_num_proj == None:
        log_lib.error('  *** *** Error getting fly calculated number of projections!')
        calc_num_proj = global_PVs['Fly_Calc_Projections'].get()
    if calc_num_proj != int(variableDict['Projections']):
        log_lib.warning('  *** *** updating number of projections from: %d to %d' % (variableDict['Projections'], calc_num_proj))
        variableDict['Projections'] = int(calc_num_proj)
    log_lib.info('  *** *** Number of projections: %d' % int(variableDict['Projections']))
    log_lib.info('  *** *** Fly calc triggers: %d' % int(calc_num_proj))
    log_lib.info('  *** get_calculated_num_projections: Done!')
    global_PVs['Fly_ScanControl'].put('Custom')

    log_lib.info(' ')
    log_lib.info('  *** Taxi before starting capture')
    global_PVs['Fly_Taxi'].put(1, wait=True)
    wait_pv(global_PVs['Fly_Taxi'], 0)
    log_lib.info('  *** Taxi before starting capture: Done!')


def acquire_fly(global_PVs, variableDict):
    theta = []
    FlyScanTimeout = (float(variableDict['Projections']) * (float(variableDict['ExposureTime']) + float(variableDict['CCD_Readout'])) ) + 30
    log_lib.info(' ')
    log_lib.info('  *** Fly Scan Time Estimate: %f minutes' % (FlyScanTimeout/60.))
    global_PVs['Reset_Theta'].put(1)
#   global_PVs['Fly_Set_Encoder_Pos'].put(1) # ensure encoder value match motor position -- only for the PIMicos
    global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']) )

    #num_images1 = ((float(variableDict['SampleEndPos']) - float(variableDict['SampleStartPos'])) / (delta + 1.0))
    num_images = int(variableDict['Projections'])
    global_PVs['Cam1_FrameType'].put(FrameTypeData, wait=True)
    global_PVs['Cam1_NumImages'].put(num_images, wait=True)
    global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True)
    # start acquiring
    global_PVs['Cam1_Acquire'].put(DetectorAcquire)
    wait_pv(global_PVs['Cam1_Acquire'], 1)
    log_lib.info(' ')
    log_lib.info('  *** Fly Scan: Start!')
    global_PVs['Fly_Run'].put(1, wait=True)
    wait_pv(global_PVs['Fly_Run'], 0)
    # wait for acquire to finish
    # if the fly scan wait times out we should call done on the detector
    if False == wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, FlyScanTimeout):
        global_PVs['Cam1_Acquire'].put(DetectorIdle)
    # set trigger move to internal for post dark and white
    #global_PVs['Cam1_TriggerMode'].put('Internal')
    log_lib.info('  *** Fly Scan: Done!')
    global_PVs['Proc_Theta'].put(1)
    #theta_cnt = global_PVs['Theta_Cnt'].get()
    theta = global_PVs['Theta_Array'].get(count=int(variableDict['Projections']))
    return theta

def acquire_pre_dark(variableDict, global_PVs):
    if int(variableDict['PreDarkImages']) > 0:
        log_lib.info(' ')
        log_lib.info('  *** Pre Dark Fields') 
        close_shutters(global_PVs, variableDict)
        capture_multiple_projections(global_PVs, variableDict, int(variableDict['PreDarkImages']), FrameTypeDark)
        log_lib.info('  *** Pre Dark Fields: Done!') 


def acquire_pre_flat(variableDict, global_PVs):
    if int(variableDict['PreWhiteImages']) > 0:
        log_lib.info(' ')
        log_lib.info('  *** Pre White Fields')
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime_Flat']) )
        open_shutters(global_PVs, variableDict)
        time.sleep(2)
        move_sample_out(global_PVs, variableDict)
        capture_multiple_projections(global_PVs, variableDict, int(variableDict['PreWhiteImages']), FrameTypeWhite)
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']) )
        log_lib.info('  *** Pre White Fields: Done!')


def acquire_post_flat(variableDict, global_PVs):
    if int(variableDict['PostWhiteImages']) > 0:
        log_lib.info(' ')
        log_lib.info('  *** Post White Fields')
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime_Flat']) )
        move_sample_out(global_PVs, variableDict)
        capture_multiple_projections(global_PVs, variableDict, int(variableDict['PostWhiteImages']), FrameTypeWhite)
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']) )
        log_lib.info('  *** Post White Fields: Done!')


def acquire_post_dark(variableDict, global_PVs):
    if int(variableDict['PostDarkImages']) > 0:
        log_lib.info(' ')
        log_lib.info('  *** Post Dark Fields') 
        close_shutters(global_PVs, variableDict)
        time.sleep(2)
        capture_multiple_projections(global_PVs, variableDict, int(variableDict['PostDarkImages']), FrameTypeDark)
        log_lib.info('  *** Post Dark Fields: Done!') 

def move_dataset_to_run_dir(global_PVs, variableDict):
    log_lib.info('  ***  move_dataset_to_run_dir')
    try:
        txm_ui = imp.load_source('txm_ui', '/local/usr32idc/DMagic/doc/demo/txm_ui.py')
        run_dir = txm_ui.directory()
        full_path = global_PVs['HDF1_FullFileName_RBV'].get(as_string=True)
        base_name = os.path.basename(full_path)
        run_full_path = run_dir + '/' + base_name
        shutil.move(full_path, run_full_path)
        log_lib.info('  ***  move_dataset_to_run_dir: Done!')
    except:
        log_lib.error('error moving dataset to run directory')
    

########################## Interlaced #########################
# CODE WORKING BUT NOT CALLED IN FUNCTIONS YET!
def gen_interlaced(variableDict):
#                   lower_bound, upper_bound, nproj, nsubsets)
# Description: Generate interlaced view angles
  lower_bound = variableDict['SampleStart_Rot']
  upper_bound = variableDict['SampleEnd_Rot']
  nsubsets = variableDict['Interlaced_Sub_Cycles']
  nproj = variableDict['Projections']
  
  rem = nproj%nsubsets
  step = (1.*upper_bound-lower_bound)/nproj
  indices = []
  for i in range(0, nsubsets):
    count = int((nproj/nsubsets) + (i<rem))
    for j in range(0, count):
      indices.append((j*nsubsets+i)*step+lower_bound)
    if i==0: # to add the upper_bound at the end of the first subset
      indices.append(upper_bound)
    if i==nsubsets: # to remove the upper_bound at the end of the first subset
      indices = indices[-1]
  return indices

def gen_interlaced_bidirectional(variableDict):
#        lower_bound, upper_bound, nproj, nsubsets):
  lower_bound = variableDict['SampleStart_Rot']
  upper_bound = variableDict['SampleEnd_Rot']
  nsubsets = variableDict['Interlaced_Sub_Cycles']
  nproj = variableDict['Projections']

  rem = nproj%nsubsets
  step = (1.*upper_bound-lower_bound)/nproj
  indices = []
  direction = True
  for i in range(0, nsubsets):
    count = int((nproj/nsubsets) + (i<rem))
    visit = range(0, count) if direction else reversed(range(0, count))
    for j in visit:
      indices.append((j*nsubsets+i)*step+lower_bound)
    if i==0: # to add the upper_bound at the end of the first subset
      indices.append(upper_bound)
    direction = not direction
  return indices

# Generate a theta vector for interlaced scan using the code (and medm window) of Tim Money
# Only work between 0 and 180 degrees
def gen_interlaced_theta_Tim():
    #set num cycles to 1 so we only do 1 scan
    global_PVs['Interlaced_Num_Cycles'].put(1, wait=True)
    global_PVs['Interlaced_Images_Per_Cycle'].put(int(variableDict['Projections']), wait=True)
    #global_PVs['Interlaced_Images_Per_Cycle_RBV']
    global_PVs['Interlaced_Num_Sub_Cycles'].put(int(variableDict['Interlaced_Sub_Cycles']), wait=True)
    #global_PVs['Interlaced_Num_Revs_RBV']
    global_PVs['Interlaced_PROC'].put(1, wait=True)
    theta_arr = global_PVs['Interlaced_Theta_Arr'].get(int(variableDict['Projections']))

    # transform the interalce vector: values do not exeed 180, vector in saw shape
    coeff = numpy.floor(theta_arr / 360)
    theta_arr_tmp = numpy.copy(theta_arr) - coeff *360
    theta_arr_tmp2 = 180 - (theta_arr_tmp - 180)
    theta_arr_tmp[numpy.where(theta_arr_tmp>180)] = theta_arr_tmp2[numpy.where(theta_arr_tmp>180)]
    theta_arr = theta_arr_tmp

    return theta_arr

def gen_interlaced_theta_W(variableDict):
    #set num cycles to 1 so we only do 1 scan
    numproj = variableDict['Projections']
    prime = variableDict['Interlaced_prime']
    nProj_per_rot = variableDict['Interlaced_prj_per_rot']

    seq = []
    i = 0
    modulus = False # False = angle will increase above 360 degrees
    while len(seq) < numproj:
        b = i
        i += 1
        r = 0
        q = 1 / prime
        while (b != 0):
            a = numpy.mod(b, prime)
            r += (a * q)
            q /= prime
            b = numpy.floor(b / prime)
        r *= (360 / nProj_per_rot)
        k = 0
        while (numpy.logical_and(len(seq) < numproj, k < nProj_per_rot)):
            if modulus ==False:
                seq.append(r + k * 360 / nProj_per_rot + 360. * (i + 1) - 720)
            else:
                seq.append(r + k * 360 / nProj_per_rot)
            k += 1
    return seq
########################## Interlaced #########################

def reset_angles_0_360(global_PVs):
    log_lib.info('Reset angle value between 0 & 360 deg')
    current_angle = global_PVs['Motor_SampleRot'].get()
    reset_angle = current_angle -360*numpy.floor(current_angle/360)
    global_PVs['Motor_SampleRot_set'].put(1) # switch motor in "set" mode
    global_PVs['Motor_SampleRot'].put(reset_angle) # reset rotation value between 0 and 360 deg
    global_PVs['Motor_SampleRot_set'].put(0) # switch motor in "use" mode
    
