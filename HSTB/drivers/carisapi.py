import os
import sys
import time
import re
import subprocess
import datetime
import tempfile
from queue import Queue, Empty
import threading
import xml.etree.ElementTree as ET
import json
from math import cos, sin, asin, sqrt, degrees
from collections import defaultdict
import glob
from winreg import ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx

import geopy.distance
import numpy as np
from pyproj import Proj, transform


import hyo2.grids.csar2  # hydrofficecsar.raw.csar
from hyo2.grids.grids_manager import GridsManager

from HSTB.time.UTC import UTCs80ToDateTime
import HSTB.resources

# This should be moved out of the HSTB.drivers.carisapi or the test data moved local to drivers
from HSTB.Charlene import benchmark
from HSTB.Charlene import processing_report
from HSTB.Charlene import pyText2Pdf
import HSTB.Charlene
charlene_test_folder = os.path.join(os.path.realpath(os.path.dirname(HSTB.Charlene.__file__)), 'tests')

_TCARI_CONVERTED = False
_HDCSIO_CONVERTED = False

if _TCARI_CONVERTED:
    from HSTB.tides import tidestation
    from HSTB.tides.tcari import TCARI

if _HDCSIO_CONVERTED:
    pass
    from HSTB.drivers import HDCSio

    def hdcsio_read():
        nav = HDCSio.HDCSNav('Navigation')

        return nav
else:
    def hdcsio_read():
        raise NotImplementedError("HDCSio is not implemented in Python 3 yet")


ON_POSIX = 'posix' in sys.builtin_module_names

# lic_success, val = HDCSio.InitLicenseHDCS()
# if not lic_success:
#    print "Pydro License did not initialize for MAC:"
#    print HDCSio.GetLicenseCredentials()
# else:
#    print 'Pydro License: {}'.format(HDCSio.GetLicenseCredentials())


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    # lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    r = 3440  # Radius of earth in nautical miles. Use 6371 for kilometers. 3959 for miles.
    return c * r


def dms_to_dec_degrees(d, m, s):
    decdegrees = d + (m * 60) + (s / 3600)
    return decdegrees


def vincenty(lon1, lat1, lon2, lat2):
    # convert radians to decimal degrees
    lon1, lat1, lon2, lat2 = degrees(lon1), degrees(lat1), degrees(lon2), degrees(lat2)
    # vincenty accounts for oblate spheroid
    return geopy.distance.vincenty((lat1, lon1), (lat2, lon2)).nm


# def pydro_lic_check():
#    return lic_success


def read_stats_from_hdcs(projfolder, vers):
    if vers >= 11:
        stats = read_stats_from_hdcs_v11(projfolder)
        return stats
    else:
        stats = read_stats_from_hdcs_v10(projfolder)
        return stats


def read_stats_from_hdcs_v11(projfolder):
    mintime = []
    maxtime = []
    tottime = []
    lats = []
    lons = []
    lnm = []
    hdcsio_lnm = []
    process_history = []
    nav = hdcsio_read()
    data = [['' for x in range(3)] for y in range(len(os.listdir(projfolder)))]

    hdcsfolders = []
    for fold in os.listdir(projfolder):
        if os.path.isdir(os.path.join(projfolder, fold)):
            hdcsfolders.append(fold)

    for count, hdcsfolder in enumerate(hdcsfolders):
        processlog = os.path.join(projfolder, hdcsfolder, 'Process.log')
        try:
            with open(processlog) as jsonfile:
                jsondata = json.load(jsonfile)
            navdata = nav.ReadTimeSeries(os.path.join(projfolder, hdcsfolder))
            i = 0
            navdata = np.array(navdata)

            if os.path.exists(os.path.join(projfolder, hdcsfolder, 'LogFile')):
                process_history.append(tuple((hdcsfolder, 'ImportTideToHIPS')))
            while i < len(navdata) - 1:
                hdcsio_lnm.append(vincenty(navdata[i][2], navdata[i][1], navdata[i + 1][2], navdata[i + 1][1]))
                i += 1

            for proc in jsondata['processes']:
                procid = str(proc['definition']['base']['identification']['id'])
                process_history.append(tuple((hdcsfolder, procid)))
                if procid[:12] == 'ImportToHIPS':
                    data[count][0] = proc['parameters']['Metadata']['ConversionSummary'].splitlines()
                    if 'BathySummary' in list(proc['parameters']['Metadata'].keys()):
                        data[count][1] = proc['parameters']['Metadata']['BathySummary'].splitlines()
                    if 'NavigationSummary' in list(proc['parameters']['Metadata'].keys()):
                        navtext = proc['parameters']['Metadata']['NavigationSummary'].splitlines()
                        data[count][2] = navtext
                        mintemp = time.strptime(navtext[5].split('=')[1], '%Y %j %H:%M:%S')
                        maxtemp = time.strptime(navtext[7].split('=')[1], '%Y %j %H:%M:%S')
                        mintime.append(mintemp)
                        maxtime.append(maxtemp)
                        tottime.append(time.mktime(maxtemp) - time.mktime(mintemp))
                        lat1 = float(navtext[8].split('=')[1])
                        lat2 = float(navtext[9].split('=')[1])
                        lon1 = float(navtext[10].split('=')[1])
                        lon2 = float(navtext[11].split('=')[1])
                        lnm.append(haversine(lon1, lat1, lon2, lat2))
                        lats.extend([degrees(lat1), degrees(lat2)])
                        lons.extend([degrees(lon1), degrees(lon2)])
        except:
            print('Unable to read process log from line {}'.format(processlog))
            return

    history_dict = defaultdict(list)
    for line, proc in process_history:
        history_dict[line].append(proc)
    starttime = time.strftime('%j %H:%M:%S', min(mintime))
    endtime = time.strftime('%j %H:%M:%S', max(maxtime))
    tot = np.array(tottime)
    totaltime = tot.sum()
    tot = np.array(hdcsio_lnm)
    totalmiles = tot.sum()
    lats, lons = np.array(lats), np.array(lons)
    extent_stats = [lats.min(), lats.max(), lons.min(), lons.max()]
    return {'history_dict': history_dict, 'process_history': process_history, 'starttime': starttime,
            'endtime': endtime,
            'totaltime': totaltime, 'totalmiles': totalmiles, 'data': data, 'hdcsio_lnm': hdcsio_lnm,
            'extent_stats': extent_stats}


def read_stats_from_hdcs_v10(projfolder):
    mintime = []
    maxtime = []
    tottime = []
    lats = []
    lons = []
    lnm = []
    hdcsio_lnm = []
    process_history = []
    nav = hdcsio_read()
    data = [['' for x in range(3)] for y in range(len(os.listdir(projfolder)))]
    for count, hdcsfolder in enumerate(os.listdir(projfolder)):
        processlog = os.path.join(projfolder, hdcsfolder, 'Process.log')
        try:
            tree = ET.parse(processlog)
            root = tree.getroot()
            found = False
            navdata = nav.ReadTimeSeries(os.path.join(projfolder, hdcsfolder))
            i = 0
            navdata = np.array(navdata)

            if os.path.exists(os.path.join(projfolder, hdcsfolder, 'LogFile')):
                process_history.append(tuple((hdcsfolder, 'ImportTideToHIPS')))
            while i < len(navdata) - 1:
                hdcsio_lnm.append(vincenty(navdata[i][2], navdata[i][1], navdata[i + 1][2], navdata[i + 1][1]))
                i += 1
            for process in root.iterfind('process'):
                id = process.find('id')
                process_history.append(tuple((hdcsfolder, id.text)))
                if id.text[:12] == 'ImportToHIPS':
                    for port in process.findall('port'):
                        if port.find('id').text == 'Metadata':
                            for attribute in port.find('source').find('data').find('complex').findall('attribute'):
                                if attribute.find('id').text == 'ConversionSummary':
                                    converttext = attribute.find('simple').find('value').text.splitlines()
                                    data[count][0] = converttext
                                if attribute.find('id').text == 'BathySummary':
                                    try:
                                        bathytext = attribute.find('simple').find('value').text.splitlines()
                                        data[count][1] = bathytext
                                    except:
                                        pass
                                if attribute.find('id').text == 'NavigationSummary':
                                    navtext = attribute.find('simple').find('value').text.splitlines()
                                    data[count][2] = navtext
                                    mintemp = time.strptime(navtext[5].split('=')[1], '%Y %j %H:%M:%S')
                                    maxtemp = time.strptime(navtext[7].split('=')[1], '%Y %j %H:%M:%S')
                                    mintime.append(mintemp)
                                    maxtime.append(maxtemp)
                                    tottime.append(time.mktime(maxtemp) - time.mktime(mintemp))
                                    lat1 = float(navtext[8].split('=')[1])
                                    lat2 = float(navtext[9].split('=')[1])
                                    lon1 = float(navtext[10].split('=')[1])
                                    lon2 = float(navtext[11].split('=')[1])
                                    lnm.append(haversine(lon1, lat1, lon2, lat2))
                                    lats.extend([degrees(lat1), degrees(lat2)])
                                    lons.extend([degrees(lon1), degrees(lon2)])
                                    found = True
                                    break
                        if found:
                            break
        except:
            # We had one odd example of a json process log in 10.4.2, try to read it here just in case
            try:
                with open(processlog) as jsonfile:
                    jsondata = json.load(jsonfile)
                navdata = nav.ReadTimeSeries(os.path.join(projfolder, hdcsfolder))
                i = 0
                navdata = np.array(navdata)

                if os.path.exists(os.path.join(projfolder, hdcsfolder, 'LogFile')):
                    process_history.append(tuple((hdcsfolder, 'ImportTideToHIPS')))
                while i < len(navdata) - 1:
                    hdcsio_lnm.append(vincenty(navdata[i][2], navdata[i][1], navdata[i + 1][2], navdata[i + 1][1]))
                    i += 1

                for proc in jsondata['processes']:
                    procid = str(proc['definition']['base']['identification']['id'])
                    process_history.append(tuple((hdcsfolder, procid)))
                    if procid[:12] == 'ImportToHIPS':
                        data[count][0] = proc['parameters']['Metadata'][0]['ConversionSummary'][0].splitlines()
                        if 'BathySummary' in list(proc['parameters']['Metadata'][0].keys()):
                            data[count][1] = proc['parameters']['Metadata'][0]['BathySummary'][0].splitlines()
                        if 'NavigationSummary' in list(proc['parameters']['Metadata'][0].keys()):
                            navtext = proc['parameters']['Metadata'][0]['NavigationSummary'][0].splitlines()
                            data[count][2] = navtext
                            mintemp = time.strptime(navtext[5].split('=')[1], '%Y %j %H:%M:%S')
                            maxtemp = time.strptime(navtext[7].split('=')[1], '%Y %j %H:%M:%S')
                            mintime.append(mintemp)
                            maxtime.append(maxtemp)
                            tottime.append(time.mktime(maxtemp) - time.mktime(mintemp))
                            lat1 = float(navtext[8].split('=')[1])
                            lat2 = float(navtext[9].split('=')[1])
                            lon1 = float(navtext[10].split('=')[1])
                            lon2 = float(navtext[11].split('=')[1])
                            lnm.append(haversine(lon1, lat1, lon2, lat2))
                            lats.extend([degrees(lat1), degrees(lat2)])
                            lons.extend([degrees(lon1), degrees(lon2)])
            except:
                print('Unable to read process log from line {}'.format(processlog))
                return

    history_dict = defaultdict(list)
    for line, proc in process_history:
        history_dict[line].append(proc)
    starttime = time.strftime('%j %H:%M:%S', min(mintime))
    endtime = time.strftime('%j %H:%M:%S', max(maxtime))
    tot = np.array(tottime)
    totaltime = tot.sum()
    tot = np.array(hdcsio_lnm)
    totalmiles = tot.sum()
    lats, lons = np.array(lats), np.array(lons)
    extent_stats = [lats.min(), lats.max(), lons.min(), lons.max()]
    return {'history_dict': history_dict, 'process_history': process_history, 'starttime': starttime, 'endtime': endtime,
            'totaltime': totaltime, 'totalmiles': totalmiles, 'data': data, 'hdcsio_lnm': hdcsio_lnm,
            'extent_stats': extent_stats}


def parse_charlene_carislog(carislog):
    excludedwarnings = [['Static values used instead.', 28], ['Vessel settings used instead.', 30],
                        ['Device model from vessel settings used instead.', 48]]  # two chars for /n
    alreadywarned = []
    alreadyerror = []
    warningdict = {'Delayed heave was selected but no data was found': ['If you load delayed heave using pos options "Create ___ SBET" or ".000 Delayed Heave" Charlene',
                                                                        'will attempt to check delayed heave at SVC and Merge.  This warning probably came up because you have',
                                                                        'MBES data that does not have POS files or is not covered by POS data, or POS import failed.'],
                   'The post-processed time extents do not entirely cover the line': ['Shows up during .000 import, you have MBES data that is not covered by POS data.',
                                                                                      'Double check that you have all your POS files selected in Charlene.  Make sure you',
                                                                                      'start POS MV logging before you start the sonar and log POS MV for 5 minutes after MBES end.'],
                   'The post-processed data has gaps greater than the max allowed': ['Charlene by default will gaps up to 2 seconds on import.  This message means you have a',
                                                                                     'gap greater than 2 seconds in your imported data.  You can manually process to widen the',
                                                                                     'gap or reacquire/post process the POS data.'],
                   'The times of the records were outside the time range for the data': ['Caris will look at the times in the POS data and match them to times in the MBES data.',
                                                                                         'This message means that you have times that are in POS but not in MBES data.  Generally not a concern.'],
                   'Post-processed data is not available for the line': ['When Caris imports from SBET (or .000), it matches times to the MBES data.  This means that you have',
                                                                         'MBES data that does not appear to have a matching SBET/.000.  Not an issue if you load from multiple',
                                                                         "SBETs, as Charlene will just try each SBET with it's own Load SBET process and let Caris apply",
                                                                         "the SBET where it fits and pass where it does not.  Just make sure that all lines have 'SBET_Loaded = Yes'",
                                                                         "Otherwise it is probably likely that you have the wrong SBETs (from an incorret day) or no SBETs at all."],
                   'Some transducer depths are above water': ['Generally not an issue.  For Sound Velocity / beam steering, Caris uses the following to position the transducer:',
                                                              '  - SVP (Z value), Heave/Pitch/Roll, HVF Waterline, Dynamic Draft',
                                                              'This warning means it ended up with the tranducer above the waterline at some point using these values',
                                                              'You will probably see fliers that have a negative z value in Subset Editor, these can just be cleaned out.'],
                   'No Svp was found for the specified time stamp': ['Using the method that you picked in Charlene (ex: Nearest in Distance in 4 Hours),',
                                                                     'Caris was unable to find a cast that fits your MBES data.  Probably either did not include',
                                                                     'All of your SVP files or you have a line that is outside of 4 hours (if you picked that method)'],
                   'Input datum model does not completely cover survey data': ['You have a VDatum (or other separation model) that does not fully cover',
                                                                               'all of your lines.  You can see this by bringing in the VDatum csar in Caris to see',
                                                                               'the overlap.  You will probably need an additional area included in your',
                                                                               'separation model.  Please contact HSTB.'],
                   'Cannot georeference bathymetry for track lines': ['Georeference Bathymetry failed.  Usually this is because it could not find',
                                                                      'GPS Height.  If you are loading SBETs, those probably failed, otherwise your',
                                                                      'MBES files do not have GPS Height.  Check the caris log for more details.'],
                   'TPU does not exist': ['This warning shows when you try to create a CUBE surface',
                                          '(Which requires uncertainty to generate) without having first',
                                          'run Georeference Bathymetry.  Or you attempted to run Georeference',
                                          'Bathymetry and it failed.']}

    errordict = {'There is no GPS Height data available for this line.': ['This could be several things:,'
                                                                          ' - If you selected Create SBET, it most likely did not work and you have no SBET height loaded',
                                                                          ' - If you loaded SBET or .000 Height, it did not apply because of time stamp matching or something else',
                                                                          ' - If you relied on .all GGK height, it was not present',
                                                                          'Look at your height source and make sure it exists and is coming from the right files'],
                 'No lines were successfully merged': ['This error shows when your Georeference Bathymetry process (which',
                                                       'includes merge) fails.  Should have accompanying warnings that will',
                                                       'tell you why this process failed.'],
                 'No TPU found for any survey lines to process': ['Shows when you attempt to generate a CUBE surface without having successfully',
                                                                  'run Georeferenced Bathymetry (which contains merge/tpu processing)',
                                                                  'CUBE requires TPU to run, check the log to see why Georeference Bathy failed.'],
                 'Insufficient data provided for swath estimation': ['Usually seen when you pick the wrong projection.  It searches for data',
                                                                     'and is unable to find it because you chose the wrong UTM zone.'],
                 'There is no overlapping data for the surface': ['This is almost always because the line projection is either',
                                                                  'completely wrong or the surface projection and the line',
                                                                  'projection do not match.  Check to see if your utm zone makes sense']}

    process_overview = {'Conversion': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ImportHIPSFromAuxiliaryAPP_POSMV': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ImportHIPSFromAuxiliaryAPP_SBET': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ImportHIPSFromAuxiliaryAPP_RMS': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ImportTideToHIPS': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'TCARI': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': [], 'count': 0},
                        'GeoreferenceHIPSBathymetry': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'SoundVelocityCorrectHIPSWithCARIS': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ComputeHIPSGPSTide': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'MergeHIPS': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ComputeHIPSTPU': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'CreateHIPSGrid': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'CreateSIPSBeamPattern': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'ComputeSIPSTowfishNavigation': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []},
                        'CreateSIPSMosaic': {'start': '', 'end': '', 'warning': [], 'warn_explain': [], 'error': [], 'error_explain': []}}
    activeproc = ''
    sbetproc = False

    with open(carislog, 'r') as carislogfile:
        carislines = carislogfile.readlines()
        for l in carislines:
            if l[0:20] == '*******Running TCARI':
                process_overview['TCARI']['start'] = l.rstrip()
                activeproc = 'TCARI'
            elif l[0:12] == '*******TCARI':
                process_overview['TCARI']['end'] = l.rstrip()
                activeproc = 'TCARI'
            elif activeproc == 'TCARI' and l[0:23] == '^^^ End tide processing':
                process_overview['TCARI']['count'] += 1
            elif l[0:6] == '======':
                rawmsg = l.split(':')[0][7:]
                savemsg = l[7:len(l) - 8]
                if rawmsg in ['Hypack RAW, HSX start', 'Kongsberg ALL start', 'Teledyne S7K start', 'Klein SDF start',
                              'Edgetech JSF start']:
                    process_overview['Conversion']['start'] = savemsg
                    activeproc = 'Conversion'
                elif rawmsg in ['Hypack RAW, HSX end', 'Kongsberg ALL end', 'Teledyne S7K end', 'Klein SDF end',
                                'Edgetech JSF end']:
                    process_overview['Conversion']['end'] = savemsg
                    activeproc = 'Conversion'
                elif rawmsg == 'Import HIPS From Applanix POS MV start':
                    process_overview['ImportHIPSFromAuxiliaryAPP_POSMV']['start'] = savemsg
                    activeproc = 'ImportHIPSFromAuxiliaryAPP_POSMV'
                elif rawmsg == 'Import HIPS From Applanix POS MV end':
                    process_overview['ImportHIPSFromAuxiliaryAPP_POSMV']['end'] = savemsg
                    activeproc = 'ImportHIPSFromAuxiliaryAPP_POSMV'
                elif rawmsg == 'Import HIPS From Applanix SBET start':
                    process_overview['ImportHIPSFromAuxiliaryAPP_SBET']['start'] = savemsg
                    activeproc = 'ImportHIPSFromAuxiliaryAPP_SBET'
                elif rawmsg == 'Import HIPS From Applanix SBET end':
                    process_overview['ImportHIPSFromAuxiliaryAPP_SBET']['end'] = savemsg
                    activeproc = 'ImportHIPSFromAuxiliaryAPP_SBET'
                elif rawmsg == 'Import HIPS From Applanix RMS start':
                    process_overview['ImportHIPSFromAuxiliaryAPP_RMS']['start'] = savemsg
                    activeproc = 'ImportHIPSFromAuxiliaryAPP_RMS'
                elif rawmsg == 'Import HIPS From Applanix RMS end':
                    process_overview['ImportHIPSFromAuxiliaryAPP_RMS']['end'] = savemsg
                    activeproc = 'ImportHIPSFromAuxiliaryAPP_RMS'
                elif rawmsg == 'Import Tide to HIPS start':
                    process_overview['ImportTideToHIPS']['start'] = savemsg
                    activeproc = 'ImportTideToHIPS'
                elif rawmsg == 'Import Tide to HIPS end':
                    process_overview['ImportTideToHIPS']['end'] = savemsg
                    activeproc = 'ImportTideToHIPS'
                elif rawmsg == 'Georeference Bathymetry start':
                    process_overview['GeoreferenceHIPSBathymetry']['start'] = savemsg
                    activeproc = 'GeoreferenceHIPSBathymetry'
                elif rawmsg == 'Georeference Bathymetry end':
                    process_overview['GeoreferenceHIPSBathymetry']['end'] = savemsg
                    activeproc = 'GeoreferenceHIPSBathymetry'
                elif rawmsg == 'Sound Velocity Correct using CARIS Algorithm start':
                    process_overview['SoundVelocityCorrectHIPSWithCARIS']['start'] = savemsg
                    activeproc = 'SoundVelocityCorrectHIPSWithCARIS'
                elif rawmsg == 'Sound Velocity Correct using CARIS Algorithm end':
                    process_overview['SoundVelocityCorrectHIPSWithCARIS']['end'] = savemsg
                    activeproc = 'SoundVelocityCorrectHIPSWithCARIS'
                elif rawmsg == 'Compute HIPS GPS Tide start':
                    process_overview['ComputeHIPSGPSTide']['start'] = savemsg
                    activeproc = 'ComputeHIPSGPSTide'
                elif rawmsg == 'Compute HIPS GPS Tide end':
                    process_overview['ComputeHIPSGPSTide']['end'] = savemsg
                    activeproc = 'ComputeHIPSGPSTide'
                elif rawmsg == 'Merge HIPS start':
                    process_overview['MergeHIPS']['start'] = savemsg
                    activeproc = 'MergeHIPS'
                elif rawmsg == 'Merge HIPS end':
                    process_overview['MergeHIPS']['end'] = savemsg
                    activeproc = 'MergeHIPS'
                elif rawmsg == 'Compute HIPS TPU start':
                    process_overview['ComputeHIPSTPU']['start'] = savemsg
                    activeproc = 'ComputeHIPSTPU'
                elif rawmsg == 'Compute HIPS TPU end':
                    process_overview['ComputeHIPSTPU']['end'] = savemsg
                    activeproc = 'ComputeHIPSTPU'
                elif rawmsg == 'Create HIPS Grid using CUBE start':
                    process_overview['CreateHIPSGrid']['start'] = savemsg
                    activeproc = 'CreateHIPSGrid'
                elif rawmsg == 'Create HIPS Grid using CUBE end':
                    process_overview['CreateHIPSGrid']['end'] = savemsg
                    activeproc = 'CreateHIPSGrid'
                elif rawmsg == 'Create SIPS Beam Pattern using Side Scan start':
                    process_overview['CreateSIPSBeamPattern']['start'] = savemsg
                    activeproc = 'CreateSIPSBeamPattern'
                elif rawmsg == 'Create SIPS Beam Pattern using Side Scan end':
                    process_overview['CreateSIPSBeamPattern']['end'] = savemsg
                    activeproc = 'CreateSIPSBeamPattern'
                elif rawmsg == 'Create SIPS Beam Pattern using Side Scan start':
                    process_overview['CreateSIPSBeamPattern']['start'] = savemsg
                    activeproc = 'CreateSIPSBeamPattern'
                elif rawmsg == 'Create SIPS Beam Pattern using Side Scan end':
                    process_overview['CreateSIPSBeamPattern']['end'] = savemsg
                    activeproc = 'CreateSIPSBeamPattern'
                elif rawmsg == 'Compute SIPS Towfish Navigation start':
                    process_overview['ComputeSIPSTowfishNavigation']['start'] = savemsg
                    activeproc = 'ComputeSIPSTowfishNavigation'
                elif rawmsg == 'Compute SIPS Towfish Navigation end':
                    process_overview['ComputeSIPSTowfishNavigation']['end'] = savemsg
                    activeproc = 'ComputeSIPSTowfishNavigation'
                elif rawmsg == 'Create SIPS Mosaic using SIPS Side Scan start':
                    process_overview['CreateSIPSMosaic']['start'] = savemsg
                    activeproc = 'CreateSIPSMosaic'
                elif rawmsg == 'Create SIPS Mosaic using SIPS Side Scan end':
                    process_overview['CreateSIPSMosaic']['end'] = savemsg
                    activeproc = 'CreateSIPSMosaic'
            elif l[0:7].lower() == 'warning':
                skip = False
                for ex in excludedwarnings:
                    if l[len(l) - ex[1]:].rstrip() == ex[0]:
                        skip = True
                if not skip:
                    process_overview[activeproc]['warning'].append(l.rstrip())
                    for warn in warningdict:
                        if (l.find(warn) != -1) and (warn not in alreadywarned):
                            alreadywarned.append(warn)
                            process_overview[activeproc]['warn_explain'].append([warn, warningdict[warn]])
            elif l[0:5].lower() == 'error':
                process_overview[activeproc]['error'].append(l.rstrip())
                for err in errordict:
                    if (l.find(err) != -1) and (err not in alreadyerror):
                        alreadyerror.append(err)
                        process_overview[activeproc]['error_explain'].append([err, errordict[err]])
            elif l[0:7] == 'POSMV: ':
                if l.find('SBET') != -1:
                    sbetproc = True
    return process_overview, sbetproc


def support_files_finder(command, suppress_exception=True):
    cubeparams = ''
    depth_coverage = ''
    depth_object = ''
    if command.startswith('"') and command.endswith('"'):
        command = command[1:-1]
    sys_dir = os.path.join(os.path.dirname(os.path.dirname(command)), 'system')
    xmlfiles = glob.glob(os.path.join(sys_dir, '*.xml'))
    txtfiles = glob.glob(os.path.join(sys_dir, '*.txt'))

    valid_cubeparams = ['CUBEParams_NOAA_2019.xml', 'CUBEParams_NOAA_2018.xml', 'CUBEParams_NOAA_2017.xml']
    valid_depth_cc = ['NOAA_DepthRanges_CompleteCoverage_2019.txt', 'NOAA_DepthRanges_CompleteCoverage_2018.txt',
                      'NOAA_DepthRanges_CompleteCoverage_2017.txt']
    valid_depth_obj = ['NOAA_DepthRanges_ObjectDetection_2019.txt', 'NOAA_DepthRanges_ObjectDetection_2018.txt',
                       'NOAA_DepthRanges_ObjectDetection_2017.txt']

    for cbparams in valid_cubeparams:
        fullcb = os.path.join(sys_dir, cbparams)
        if fullcb in xmlfiles:
            cubeparams = fullcb
            break
    for depthcc in valid_depth_cc:
        fullcc = os.path.join(sys_dir, depthcc)
        if fullcc in txtfiles:
            depth_coverage = fullcc
            break
    for depthdo in valid_depth_obj:
        fulldo = os.path.join(sys_dir, depthdo)
        if fulldo in txtfiles:
            depth_object = fulldo
            break

    if cubeparams and depth_coverage and depth_object:
        return cubeparams, depth_coverage, depth_object
    else:
        if not suppress_exception:
            mess = "Caris Support Files not found at {}".format(sys_dir)
            raise Exception(mess)
        else:
            return cubeparams, depth_coverage, depth_object


def command_finder_old():
    # carisbatch finder, in case you installed somewhere dumb or don't have it installed at all
    name = 'carisbatch.exe'
    command = ''
    batch_engine = ''
    pathlist = [r'C:\Program Files\CARIS\HIPS and SIPS\10.4', r'C:\Program Files\CARIS\HIPS and SIPS\10.3',
                r'C:\Program Files\CARIS\HIPS and SIPS\10.2']
    for path in pathlist:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path, topdown=True):
                if name in files:
                    batch_engine = os.path.join(root, name)
                    break
            break
    if batch_engine:
        command = '"' + batch_engine + '"'
    else:
        raise Exception("No Batch Engine found...is CARIS installed at C:\Program Files\CARIS\HIPS and SIPS?")
    return command


def caris_command_finder(exe_name, accepted_versions, app_key):
    batch_engine = ''
    vers = ''
    regHKLM = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
    for vHIPS in accepted_versions:
        try:
            kBDB = OpenKey(regHKLM, os.sep.join(('SOFTWARE', 'CARIS', 'HIPS', vHIPS, 'Environment Variables')))
            p2hipsinst = QueryValueEx(kBDB, "install_dir")[0]
            batch_engine = os.path.join(p2hipsinst, 'bin', exe_name)
            # if the carisbatch doesn't exist then continue to the next version of caris
            if not os.path.exists(batch_engine):
                continue
            vers = float(vHIPS)
            break
        except WindowsError:
            continue
    return batch_engine, vers


def command_finder_hips():
    batch_engine, vers = caris_command_finder('carisbatch.exe', ('11.2', '11.1', '10.4', '10.3', '10.2'), "HIPS")
    if not batch_engine:
        raise Exception("No Batch Engine found...is CARIS HIPS and SIPS installed?")
    return batch_engine, vers


def command_finder_base():
    batch_engine, vers = caris_command_finder('carisbatch.exe', ('5.3', '5.2', '5.1', '4.4', '4.3', '4.2'), 'BASE Editor')
    if not batch_engine:
        raise Exception("No Batch Engine found...is CARIS BASE Editor installed?")
    return batch_engine, vers


def get_bands_from_csar(path_to_csar):
    """ Open a csar file and return the bands.  Returns a list.
    For a sounding csar probably like this:
        ['Depth', 'Deep', 'Density', 'Hypothesis_Count', 'Hypothesis_Strength', 'Mean', 'Node_Std_Dev', 'Shoal', 'Std_Dev', 'Uncertainty', 'User_Nominated']
    For a sidescan csar then something like this:
        ['Intensity', 'Density', 'Standard_Deviation', 'Weights']
    """
    grids = GridsManager()
    grids.add_path(path_to_csar)
    list(grids.grid_list)
    grids.set_current(path_to_csar)
    DEFAULT_CHUNK_SIZE = 1073741824  # 1GB    4294967296  # 4GB
    grids.open_to_read_current(DEFAULT_CHUNK_SIZE)
    return list(grids.layer_names())


def find_csar_band_name(csar, log=None):
    if os.path.splitext(csar)[1] == '.csar':
        # c = hydroffice.csar.raw.csar.CsarBase()
        band_names = get_bands_from_csar(csar)
        out = ''
        b = ''

        found = False
        out = 'Searching for VDatum bands "NAD83_MLLW" and "WGS84_MLLW"\n'
        for b in band_names:
            if b in ['NAD83-MLLW', 'WGS84-MLLW', 'NAD83_MLLW', 'WGS84_MLLW']:
                out += 'found VDatum band {}'.format(b)
                found = True
                break
        if not found:
            out += 'Searching for other NAD83/WGS84 prefixed band names\n'
            for b in band_names:
                if b[0:6] in ['NAD83_', 'WGS84_']:
                    out += 'found VDatum band {}'.format(b)
                    found = True
                    break
        if not found:
            out += 'Searching for VDatum bands "Elevation", "Datum Height" and "Height"\n'
            for b in band_names:
                if b in ['Datum Height', 'Elevation', 'Height']:
                    out += 'found VDatum band {}'.format(b)
                    found = True
                    break
        if not found:
            out += 'Searching for VDatum bands "Depth"\n'
            for b in band_names:
                if b in ['Depth']:
                    out += 'found VDatum band {}'.format(b)
                    found = True
                    break
        if not found:
            out += 'Could not find expected VDatum band.  Need NAD83-MLLW, WGS84-MLLW, Elevation, Height or Datum Height.\n'
            out += 'Found {}'.format(band_names)
            b = ''
        if log:
            with open(log, 'a+') as logger:
                print(out, file=logger)
                print(out)
        return b
    elif os.path.splitext(csar)[1] == '.asc':
        if log:
            with open(log, 'a+') as logger:
                print("Found .asc file: using 'Band 1' band name", file=logger)
                print("Found .asc file: using 'Band 1' band name")
        return 'Band 1'
    else:
        if log:
            with open(log, 'a+') as logger:
                print("File format unsupported:  Require .asc or .csar file", file=logger)
                print("File format unsupported:  Require .asc or .csar file")
        return ''


def proj_to_epsg(coord, proj):
    if coord == 'NAD83':
        zone = proj[9:len(proj) - 1]
        if len(zone) == 2:
            return '269' + zone
        elif len(zone) == 1:
            return '2690' + zone
        else:
            raise IOError('Invalid projection: {}, {}'.format(coord, proj))
    elif coord == 'WGS84':
        zone = proj[9:len(proj) - 1]
        if len(zone) == 2:
            return '326' + zone
        elif len(zone) == 1:
            return '3260' + zone
        else:
            raise IOError('Invalid projection: {}, {}'.format(coord, proj))
    else:
        raise IOError('Invalid coordinate system: {}'.format(coord))


def wgs84_epsg_utmzone_finder(maxlon, minlon):
    maxlon = int(maxlon)
    minlon = int(minlon)
    msg = ''
    maxlon_zone = str(30 - ((int(maxlon) * -1) / 6))
    if len(str(maxlon_zone)) == 1:
        maxlon_zone = '3260' + str(maxlon_zone)
    else:
        maxlon_zone = '326' + str(maxlon_zone)

    minlon_zone = str(30 - ((int(minlon) * -1) / 6))
    if len(str(minlon_zone)) == 1:
        minlon_zone = '3260' + str(minlon_zone)
    else:
        minlon_zone = '326' + str(minlon_zone)

    if int(maxlon_zone) != int(minlon_zone):
        msg = 'Spanning more than one UTM zone: {}, {}'.format(minlon_zone, maxlon_zone)
    return maxlon_zone, msg


def nad83_epsg_utmzone_finder(maxlon, minlon):
    maxlon = int(maxlon)
    minlon = int(minlon)
    msg = ''
    maxlon_zone = str(30 - ((int(maxlon) * -1) / 6))
    if len(str(maxlon_zone)) == 1:
        maxlon_zone = '2690' + str(maxlon_zone)
    else:
        maxlon_zone = '269' + str(maxlon_zone)

    minlon_zone = str(30 - ((int(minlon) * -1) / 6))
    if len(str(minlon_zone)) == 1:
        minlon_zone = '2690' + str(minlon_zone)
    else:
        minlon_zone = '269' + str(minlon_zone)

    if int(maxlon_zone) != int(minlon_zone):
        msg = 'Spanning more than one UTM zone: {}, {}'.format(minlon_zone, maxlon_zone)
    return maxlon_zone, msg


def proj_from_svp(svp_path):
    if svp_path.endswith(".svp"):
        with open(svp_path, 'r') as svp:
            version = svp.readline()
            name = svp.readline()
            header = svp.readline()
            try:
                section, date, lat, int = [header.split()[i] for i in [1, 2, 3, 4]]
            except:
                error = 'Error reading {}\n'.format(svp_path)
                error += 'Please verify that the svp file has the correct header'
                raise IOError(error)
            degree_long = int.split(':')[0]
            lon_zone = str(30 - ((int(degree_long) * -1) / 6))
            if lat[0] == '-':
                return 'UTM Zone ' + lon_zone + 'S'
            return 'UTM Zone ' + lon_zone + 'N'
    else:
        return ''

# helper function to retrieve the path to the NOAA folder in PydroXL


def retrieve_noaa_folder_path():
    folder_path = HSTB.resources.path_to_HSTB()
    if not os.path.exists(folder_path):
        raise RuntimeError("the folder does not exist: %s" % folder_path)
    # print "NOAA folder: {}".format(folder_path)
    return folder_path

# helper function to retrieve the install prefix path for PydroXL


def retrieve_install_prefix():
    folder_path = HSTB.resources.path_to_root_env()
    if not os.path.exists(folder_path):
        raise RuntimeError("the folder does not exist: %s" % folder_path)
    # print "install prefix: %s" % folder_path
    return folder_path

# helper function to retrieve the path to the "Scripts" folder in PydroXL


def retrieve_scripts_folder():
    folder_path = HSTB.resources.path_to_root_env("Scripts")
    if not os.path.exists(folder_path):
        raise RuntimeError("the folder does not exist: %s" % folder_path)
    # print "scripts folder: %s" % folder_path
    return folder_path

# helper function to retrieve the path to the "activate.bat" batch file in PydroXL


def retrieve_activate_batch():

    scripts_prefix = retrieve_scripts_folder()
    file_path = os.path.realpath(os.path.join(scripts_prefix, "activate.bat"))
    if not os.path.exists(file_path):
        raise RuntimeError("the file does not exist: %s" % file_path)
    # print "activate batch file: %s" % file_path
    return file_path


class CarisAPI():
    def __init__(self, processtype='', hdcs_folder='', hvf='', project_name='', sheet_name='', vessel_name='', day_num='',
                 input_format='', logger=os.path.join(os.path.dirname(__file__), 'log.txt'), benchcsv='', coord_mode='',
                 proj_mode='', noaa_support_files=False, benchfrom='', benchto='', benchtoraw='',
                 bench=True, progressbar=None, base=False, hipsips=True):
        self.benchclass = benchmark.Benchmark(benchfrom, benchto, benchtoraw)
        self.benchfrom = benchfrom
        self.benchto = benchto
        self.benchtoraw = benchtoraw
        self.progressbar = progressbar
        self.processtype = processtype
        self.hdcs_folder = hdcs_folder
        self.hvf = hvf
        self.project_name = project_name
        self.sheet_name = sheet_name
        self.vessel_name = vessel_name
        self.day_num = day_num
        self.onlysurface_additionalvessel = ''
        self.noaa_support_files = noaa_support_files
        if hipsips:
            self.hipscommand, self.hipsversion = command_finder_hips()
            self.hdcsio_read = hdcsio_read()
            if self.noaa_support_files:
                self.cubeparams, self.depth_coverage, self.depth_object = support_files_finder(self.hipscommand)
        else:
            self.hipscommand, self.hipsversion = '', ''
        if base:
            self.basecommand, self.baseversion = command_finder_base()
        else:
            self.basecommand, self.baseversion = '', ''
        self.bathy_type = 'MULTIBEAM'
        self.input_format = input_format
        self.logger = logger
        self.bench = bench
        self.benchcsv = benchcsv
        self.converted_lines = []
        self.coord = coord_mode
        self.proj = proj_mode
        self.proj_to_epsg = proj_to_epsg
        self.totalmiles = ''
        self.starttime = ''
        self.endtime = ''
        self.totaltime = ''

    def enqueue_output(self, out, queue):
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()

    def run_this_old_old(self, fullcommand):
        p = subprocess.Popen(fullcommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        while p.poll() is None:
            if self.progressbar:
                self.progressbar.UpdatePulse('Running Caris Processes')
            for line in iter(p.stdout.readline, b''):
                print((">>> " + line.rstrip()))

    def run_this(self, fullcommand):
        with open(self.logger, 'a+') as log:
            # log.write(fullcommand)
            p = subprocess.Popen(fullcommand, stdout=log, stderr=log)
            while p.poll() is None:
                if self.progressbar:
                    self.progressbar.UpdatePulse('Running Caris Processes')
                time.sleep(.1)

    def run_this_old_old_old_old(self, fullcommand):
        log = open(self.logger, 'a+')
        log.write(fullcommand)
        templog = open('templog.txt', 'wb')
        p = subprocess.Popen(fullcommand, stdout=templog, stderr=subprocess.STDOUT)
        readtemp = open('templog.txt', 'r')
        while p.poll() is None:
            if self.progressbar:
                self.progressbar.UpdatePulse('Running Caris Processes')
            t = readtemp.read()
            if t:
                print(t)
                log.write(t)
            time.sleep(.1)
        t = readtemp.read()
        if t:
            print(t)
            log.write(t)
        readtemp.close()
        templog.close()
        os.remove('templog.txt')

    def run_this_old(self, fullcommand):
        p = subprocess.Popen(fullcommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output, errors = p.communicate()
        log = open(self.logger, 'a+')
        print(output)
        print(output, file=log)
        print(errors)
        print(errors, file=log)

    def run_this_old_old_old(self, fullcommand):
        log = open(self.logger, 'w+')
        p = subprocess.Popen(fullcommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
                             close_fds=ON_POSIX)
        q = Queue()
        t = threading.Thread(target=self.enqueue_output, args=(p.stdout, q))
        # t.daemon()
        t.start()
        while t.isAlive():
            if self.progressbar:
                self.progressbar.UpdatePulse('Running Caris Processes')
            try:
                line = q.get(timeout=.1)
            except Empty:
                pass
            else:
                print(line, end=' ')
                print(line, end=' ', file=log)

    def caris_hips_license_check(self, printout=True):
        fullcommand = self.hipscommand + ' --version'
        test = -1
        out = subprocess.Popen(fullcommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = out.stdout.read()
        out = out.splitlines()

        # first stage: Just see if the modules are enabled, will at least see if they configured Caris to run
        if printout:
            if self.logger is not None:
                if not os.path.exists(os.path.split(self.logger)[0]):
                    os.makedirs(os.path.split(self.logger)[0])
                with open(self.logger, 'a+') as log:
                    print('\n'.join(out))
                    print('\n'.join(out), file=log)
                    print('\n****************************************************\n')
                    print('\n****************************************************\n', file=log)
            else:
                out.append('\nUnable to access log file: {}\n'.format(self.logger))
        for line in out:
            if line[:4] == 'HIPS':
                test = line.find('Yes')
                break

        if test == -1:
            return False, out
        else:
            # second stage: Try to write a csar to see if you are licensed
            car = CarisAPI(bench=False)
            tstsrc = os.path.join(charlene_test_folder, 'tstraster.csar')
            desttif = os.path.join(charlene_test_folder, 'delete_me.tif')
            if os.path.exists(desttif):
                os.remove(desttif)
            car.export_raster(tstsrc, 'GeoTIFF', desttif)
            if os.path.exists(desttif):
                os.remove(desttif)
                return True, out
            else:
                out = ['License check failed:  Ensure that modules are enabled in Caris and a valid license is activated.']
                return False, out

    def caris_base_license_check(self, printout=True):
        # if not already enabled, enable base
        if not self.basecommand:
            self.basecommand, self.baseversion = command_finder_base()
            if not self.basecommand:
                out = 'License check failed:  Base switch not set in CarisAPI and no valid Base Editor command found.'
                return False, out

        fullcommand = self.basecommand + ' --version'
        test = -1
        out = subprocess.Popen(fullcommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = out.stdout.read()
        out = out.splitlines()

        # first stage: Just see if the modules are enabled, will at least see if they configured Caris to run
        if printout:
            if self.logger is not None:
                if not os.path.exists(os.path.split(self.logger)[0]):
                    os.makedirs(os.path.split(self.logger)[0])
                with open(self.logger, 'a+') as log:
                    print('\n'.join(out))
                    print('\n'.join(out), file=log)
                    print('\n****************************************************\n')
                    print('\n****************************************************\n', file=log)
            else:
                out.append('\nUnable to access log file: {}\n'.format(self.logger))
        for line in out:
            if line[:15] == 'Feature Editing':
                test = line.find('Yes')
                break
            # They changed the fucking name to 'BASE Editor', of course, in 5.3 the jerks
            elif line[:11] == 'BASE Editor':
                test = line.find('Yes')
                break

        if test == -1:
            return False, out
        else:
            # second stage: Try to write a csar to see if you are licensed
            car = CarisAPI(bench=False, base=True, hipsips=False)
            tstsrc = os.path.join(charlene_test_folder, 'tstraster.csar')
            desttif = os.path.join(charlene_test_folder, 'delete_me.tif')
            if os.path.exists(desttif):
                os.remove(desttif)
            car.export_raster(tstsrc, 'GeoTIFF', desttif, forcebase=True)
            if os.path.exists(desttif):
                os.remove(desttif)
                return True, out
            else:
                print(out)
                out = ['License check failed:  Ensure that modules are enabled in Caris and a valid license is activated.']
                return False, out

    def processlog_read(self, transferstats, options):
        if self.hipsversion < 11:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name, self.vessel_name, self.day_num)
            # querybyline not supported, don't use the converted_lines stuff
            convlines = []
        else:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name)
            convlines = self.converted_lines
        #history_dict, process_history, self.starttime, self.endtime, self.totaltime, self.totalmiles, data, hdcsio_lnm, extent_stats = read_stats_from_hdcs(hdcspath)
        hdcsstats = read_stats_from_hdcs(hdcspath, self.hipsversion)
        if hdcsstats:
            self.starttime = hdcsstats['starttime']
            self.endtime = hdcsstats['endtime']
            self.totaltime = hdcsstats['totaltime']
            self.totalmiles = hdcsstats['totalmiles']

            hips = os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips')
            thr = threading.Thread(target=processing_report.process_reader, args=(self.processtype, hdcsstats['history_dict'],
                                                                                  self.starttime, self.endtime,
                                                                                  self.totaltime, self.totalmiles,
                                                                                  hdcsstats['extent_stats'],
                                                                                  self.project_name, self.sheet_name,
                                                                                  self.vessel_name, self.day_num,
                                                                                  self.logger, transferstats, hdcspath, hips,
                                                                                  options['acqcomments'], self.hipsversion,
                                                                                  convlines))
            thr.start()
            while thr.isAlive():
                if self.progressbar:
                    self.progressbar.UpdatePulse('Generating Log...')
                time.sleep(.1)
            carislog_summary, sbetproc = parse_charlene_carislog(options['carislogger'])
            thr = threading.Thread(target=processing_report.end_status_report, args=(self.processtype, hdcsstats['history_dict'],
                                                                                     self.vessel_name,
                                                                                     self.day_num, self.logger,
                                                                                     transferstats, hdcspath, hips,
                                                                                     carislog_summary, sbetproc, self.hipsversion,
                                                                                     convlines))
            thr.start()
            while thr.isAlive():
                if self.progressbar:
                    self.progressbar.UpdatePulse('Generating Status Report...')
                time.sleep(.1)

    def create_new_hips_project(self):
        hipsfile = os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips')
        epsg = proj_to_epsg(self.coord, self.proj)
        if not os.path.exists(hipsfile):
            fullcommand = self.hipscommand + ' --run CreateHIPSFile --output-crs EPSG:' + epsg + ' "' + hipsfile + '"'
            if self.bench:
                self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
            else:
                self.run_this(fullcommand)

    def convert_mbes(self, raw_file, kongs_height='EM_HEIGHT', overwrite=False):
        '''Runs ImporttoHIPS with all options.  Example: carisbatch.exe --run ImportToHIPS --input-format HYPACK
        --convert-bathymetry MULTIBEAM C:\HIPSData\PreProcess\000_1111.HSX file:///C:/HIPSData/HDCS_Data/Test/
        Test.hips?Vessel=HypackVessel2017;Day=2017-006'''
        rawfiles = ''
        epsg = proj_to_epsg(self.coord, self.proj)

        if self.hipsversion < 11:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name, self.vessel_name, self.day_num)
        else:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name)

        for line in raw_file:
            rawfiles += '"' + line + '" '
            tempraw = os.path.split(line)[1]
            line_path = os.path.join(hdcspath, tempraw[:len(tempraw) - 4])
            self.converted_lines.append(line_path)

        fullcommand = self.hipscommand + ' --run ImportToHIPS --input-format ' + self.input_format
        fullcommand += ' --input-crs EPSG:' + epsg
        if self.hipsversion >= 11:
            fullcommand += ' --vessel-file "' + self.hvf + '"'
        if overwrite:
            fullcommand += ' --overwrite BATHY --overwrite NAVIGATION --overwrite MOTION'
        if self.input_format == 'HYPACK':
            fullcommand += ' --convert-bathymetry ' + self.bathy_type + ' ' + rawfiles
        elif self.input_format == 'KONGSBERG':
            fullcommand += ' --convert-navigation --gps-height-device ' + kongs_height + ' ' + rawfiles
        elif self.input_format == 'TELEDYNE_7k':
            fullcommand += ' --navigation-device POSITION --heading-device HEADING --motion-device RPH'
            fullcommand += ' --swath-device BATHYMETRY ' + rawfiles
        elif self.input_format == 'GSF':
            fullcommand += ' --depth-source TRUE ' + rawfiles

        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips')
        if self.hipsversion < 11:
            fullcommand += '?Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'
        else:
            fullcommand += '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def daynum_extents(self, epsg, overwritelines=[]):
        lat = []
        lon = []
        msg = ''

        if self.hipsversion < 11:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name, self.vessel_name, self.day_num)
        else:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name)

        if self.converted_lines == []:
            for folder in os.listdir(hdcspath):
                line_path = os.path.join(hdcspath, folder)
                if os.path.isdir(line_path):
                    self.converted_lines.append(line_path)

        if overwritelines:
            # keep only converted lines that match raw data (overwritelines is raw data, converted_lines are hdcs)
            keep_lines = []
            for procline in self.converted_lines:
                procfolder = os.path.split(procline)[1]
                for rawfile in overwritelines:
                    rawfilename = os.path.splitext(os.path.split(rawfile)[1])[0]
                    if procfolder == rawfilename:
                        keep_lines.extend([procline])
                        break
            print('AM_PM_LineFinder: Found {} lines for the day, running on {} lines'.format(len(self.converted_lines),
                                                                                             (len(keep_lines))))
            self.converted_lines = keep_lines

        nav = self.hdcsio_read
        for hdcsline in self.converted_lines:
            try:
                navdata = nav.ReadTimeSeries(hdcsline)
                lat.append(np.rad2deg(navdata[:, 1].max()))
                lat.append(np.rad2deg(navdata[:, 1].min()))
                lon.append(np.rad2deg(navdata[:, 2].max()))
                lon.append(np.rad2deg(navdata[:, 2].min()))
            except:
                raise Exception('Unable to read navigation from line {}'.format(hdcsline))

        lat = np.array(lat)
        lon = np.array(lon)
        '''if self.coord == 'NAD83':
            epsg, msg = nad83_epsg_utmzone_finder(lon.max(), lon.min())
        elif self.coord == 'WGS84':
            epsg, msg = wgs84_epsg_utmzone_finder(lon.max(), lon.min())
        else:
            raise Exception("Unknown coordinate system.  Please use NAD83 or WGS84.")

        if msg:
            with open(self.logger, 'a+') as log:
                log.write(msg)
                print msg'''

        outproj = Proj(init='epsg:' + str(epsg))
        inproj = Proj(init='epsg:4326')  # WGS84
        lowxextent, lowyextent = lon.min(), lat.min()
        highxextent, highyextent = lon.max(), lat.max()

        lowxextent_final, lowyextent_final = transform(inproj, outproj, lowxextent, lowyextent)
        highxextent_final, highyextent_final = transform(inproj, outproj, highxextent, highyextent)
        return str(epsg), str(lowxextent_final - 2000), str(lowyextent_final - 2000), \
            str(highxextent_final + 2000), str(highyextent_final + 2000)

    def tcari_tides(self, tcarifile, mode):
        if _TCARI_CONVERTED:
            count = 0
            fstr = ''
            pre_msgs = []
            post_msgs = []
            lines = self.converted_lines
            tc = TCARI.LoadTCARIFile(tcarifile)

            tidetypes = {"Observed": tidestation.TideStation.OBSERVED,
                         "Verified": tidestation.TideStation.VERIFIED,
                         "Predicted": tidestation.TideStation.GENERATED}
            tidetype = tidetypes[mode]

            if lines:
                with open(self.logger, 'a+') as log:
                    startmsg = '*******Running TCARI Tide Processor*******\r\n'
                    print(startmsg)
                    log.write(startmsg)
                    # tidetype = self.tcaridata.ChooseTideTypeIfMultiple(self)
                    nav = HDCSio.HDCSNav('Navigation')
                    times = []
                    remove_paths = []
                    for path in lines:
                        try:
                            o = nav.ReadTimeSeries(path)
                            if len(o) > 0:
                                times.append([o[:, 0].min(), o[:, 0].max()])
                        except:
                            msg = "Error reading data from:'%s'\nRemoving path '%s'\n" % (path, path)
                            print(msg)
                            log.write(msg)
                            remove_paths.append(path)
                            pre_msgs.append(msg)
                            count += 1
                    for path in remove_paths:
                        lines.remove(path)
                    if times:
                        if tidetype != tidestation.TideStation.GENERATED:
                            t = np.array(times, np.float64)
                            mintime, maxtime = UTCs80ToDateTime(t[:, 0].min()), UTCs80ToDateTime(t[:, 1].max())
                            begindate = mintime - datetime.timedelta(360. / (24 * 60))
                            enddate = maxtime + datetime.timedelta(360. / (24 * 60))
                            # add buffer for AutoQC, as pos files could exist outside of caris min/max time
                            begindate -= datetime.timedelta(hours=3)
                            enddate += datetime.timedelta(hours=3)
                            thr = threading.Thread(target=tc.DownloadWLData, kwargs={
                                'begindate': begindate, 'enddate': enddate, 'tidetype': tidetype, 'bShowProgress': False})
                            thr.start()
                            while thr.isAlive():
                                if self.progressbar:
                                    self.progressbar.UpdatePulse('Running Pydro TCARI')
                                time.sleep(.1)
                            bPred = False
                        else:
                            bPred = True
                        automation_args = []
                        thr = threading.Thread(target=TCARI.TideCorrectHDCS, args=(tc, lines), kwargs={
                            'bPredicted': bPred, 'tidetype': tidetype, 'bShowLog': False, 'bWarnOutOfGrid': False,
                            'automation_args': automation_args})
                        thr.start()
                        while thr.isAlive():
                            if self.progressbar:
                                self.progressbar.UpdatePulse('Running Pydro TCARI')
                            time.sleep(.1)
                        try:
                            fstr = automation_args[0]
                            tcnt = automation_args[1]
                        except:
                            pass
                        else:
                            count += tcnt

                    else:
                        print(("Caris navigation data missing. \n" +
                               "Either the files could not be read or the data was corrupt."))
                    if fstr:
                        tcaris_msgs = open(fstr, "rb").read()
                    else:
                        h, fstr = tempfile.mkstemp('.log.txt', 'TC_')
                        os.close(h)
                        tcaris_msgs = ""
                    outf = open(fstr, 'wb')
                    outf.write("\n".join(pre_msgs))
                    outf.write(tcaris_msgs)
                    outf.write("\n".join(post_msgs))
                    outf.close()
                    log.write("\n".join(pre_msgs))
                    log.write(tcaris_msgs)
                    log.write("\n".join(post_msgs))
                    if count > 0:
                        print()
                        "There were errors or warnings in creating the HDCS tides.\nSee the Charlene caris_log file for more information."
                    endmsg = '*******TCARI Tide Processor Complete*******\r\n'
                    print(endmsg)
                    log.write(endmsg)
                    TCARI.SaveTCARIFile(tc, tcarifile)
            return fstr
        else:
            raise NotImplementedError("TCARI is not in Python 3 yet")

    def convert_sss(self, raw_file, overwrite=False):
        '''Runs ImporttoHIPS with all options.  Example: carisbatch.exe --run ImportToHIPS --input-format KLEIN
        --convert-side-scan HIGH --pressure-sensor-psi 300 --pressure-sensor-range 05 C:\HIPSData\PreProcess\000_1111.HSX
        file:///C:/HIPSData/HDCS_Data/Test/Test.hips?Vessel=HypackVessel2017;Day=2017-006'''
        epsg = proj_to_epsg(self.coord, self.proj)
        rawfiles = ''

        if self.hipsversion < 11:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name, self.vessel_name, self.day_num)
        else:
            hdcspath = os.path.join(self.hdcs_folder, self.sheet_name)

        for line in raw_file:
            rawfiles += '"' + line + '" '
            tempraw = os.path.split(line)[1]
            line_path = os.path.join(hdcspath, tempraw[:len(tempraw) - 4])
            self.converted_lines.append(line_path)

        fullcommand = self.hipscommand + ' --run ImportToHIPS --input-format ' + self.input_format
        fullcommand += ' --input-crs EPSG:' + epsg
        if self.hipsversion >= 11:
            fullcommand += ' --vessel-file "' + self.hvf + '"'
        if overwrite:
            fullcommand += ' --overwrite SIDE_SCAN --overwrite NAVIGATION --overwrite MOTION'
        if self.input_format == 'KLEIN':
            fullcommand += ' --convert-side-scan HIGH'
            fullcommand += ' --pressure-sensor-psi 300 --pressure-sensor-range 05 '
        elif self.input_format == 'EDGETECH_JSF':
            fullcommand += ' --sensor-altitude-location SENSOR --convert-from-cable-out'
            fullcommand += ' --sensor-depth-location SENSOR '
        elif self.input_format == 'XTF':
            fullcommand += ' --convert-side-scan 12 --convert-layback-cable-out CABLEOUT '
        elif self.input_format == 'HYPACK_HIGH':
            fullcommand = self.hipscommand + ' --run ImportToHIPS --input-format HYPACK'
            fullcommand += ' --input-crs EPSG:' + epsg
            if self.hipsversion >= 11:
                fullcommand += ' --vessel-file "' + self.hvf + '"'
            if overwrite:
                fullcommand += ' --overwrite SIDE_SCAN --overwrite NAVIGATION --overwrite MOTION'
            fullcommand += ' --convert-side-scan HIGH --convert-bathymetry NONE --convert-from-cable-out'
            fullcommand += ' --navigation-device 0 --heading-device 0 --port-device 1 --ss-position-device 2 '
        elif self.input_format == 'HYPACK_LOW':
            fullcommand = self.hipscommand + ' --run ImportToHIPS --input-format HYPACK'
            fullcommand += ' --input-crs EPSG:' + epsg
            if self.hipsversion >= 11:
                fullcommand += ' --vessel-file "' + self.hvf + '"'
            if overwrite:
                fullcommand += ' --overwrite SIDE_SCAN --overwrite NAVIGATION --overwrite MOTION'
            fullcommand += ' --convert-side-scan LOW --convert-bathymetry NONE --convert-from-cable-out'
            fullcommand += ' --navigation-device 0 --heading-device 0 --port-device 1 --ss-position-device 2 '
        fullcommand += rawfiles
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips')
        if self.hipsversion < 11:
            fullcommand += '?Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'
        else:
            fullcommand += '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def create_beampattern(self, type, bbpfile, querybyline=False):
        '''Runs CreateSIPSBeamPattern with all the options.  Example: carisbatch.exe --run CreateSIPSBeamPattern
        --mosaic-engine SIPS_BACKSCATTER --beam-pattern-file C:\HIPSData\SIPS\beampatternfile.bbp
        file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''

        fullcommand = self.hipscommand + ' --run CreateSIPSBeamPattern --mosaic-engine ' + type
        fullcommand += ' --beam-pattern-file "' + bbpfile + '" '
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    fullcommand += '"'
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def create_mosaic(self, epsg, extentlowx, extentlowy, extenthighx, extenthighy, resolution, beampattern, type,
                      outputname, update=True, querybyline=False):
        '''Rune CreateSIPSMosaic with all the options.  Example: carisbatch.exe --run CreateSIPSMosaic
        --mosaic-engine SIPS_BACKSCATTER --output-crs EPSG:26919 --extent 300000 5000000 350000 5050000
        --resolution 1.0m --beam-pattern-file c:\HIPSData\SIPS\beampattern.bbp
        file:///C:/HIPSData/HDCS_Data/Test/Test.hips C:\HIPSData\Products\mosaic1m.csar'''

        fullcommand = self.hipscommand + ' --run CreateSIPSMosaic --mosaic-engine ' + type + ' --output-crs EPSG:' + epsg
        if not update:
            fullcommand += ' --beam-pattern-file-operation USE_EXISTING'
        if type == 'SIPS_SIDESCAN':
            fullcommand += ' --extrapolate-time 5.0 --beam-pattern BOTH --tvg 10db 10db'
        if type == 'SIPS_BACKSCATTER':
            pass
        fullcommand += ' --extent ' + extentlowx + ' ' + extentlowy + ' ' + extenthighx + ' ' + extenthighy
        fullcommand += ' --resolution ' + resolution + ' --beam-pattern-file "' + beampattern + '" '
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    pass
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def recompute_towfish_nav(self, querybyline=False):
        '''Runs ComputeSIPSTowfishNavigation with all the options.  Example: carisbatch.exe --run
        ComputeSIPSTowfishNavigation --use-cmg --smooth-sensor GYRO file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''

        fullcommand = self.hipscommand + ' --run ComputeSIPSTowfishNavigation '
        #fullcommand += '--smooth-sensor SSSSensor --smooth-sensor SSSCable --use-cmg '
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    fullcommand += '"'
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def import_tide(self, tide_file, zdf=False):
        '''Runs ImportTideToHIPS with all the options.  Example: carisbatch.exe --run ImportTideToHIPS --tide-file
        C:\HIPSData\Tide\tidefile.tid file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''

        fullcommand = self.hipscommand + ' --run ImportTideToHIPS --tide-file "' + tide_file + '" '
        if zdf:
            fullcommand += '--interpolation-type MULTI_STATION '
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def import_auxiliary(self, datatype, source, height=None, delheave=None, height_rms=None,
                         delheave_rms=None, nav=None, nav_rms=None, querybyline=False):
        '''Runs ImportHIPSFromAuxiliary with all the options.  Example: carisbatch.exe --run ImportHIPSFromAuziliary
         --input-format APP_POSMV --allow-partial --delayed-heave 0 --delayed-heave-rms 0 C:\HIPSData\POS\DN170.000
         file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''
        fullcommand = self.hipscommand + ' --run ImportHIPSFromAuxiliary --input-format ' + datatype + ' '
        fullcommand += '--allow-partial "' + source + '" '

        if height:
            fullcommand += '--gps-height 0sec '
        if height_rms:
            fullcommand += '--gps-height-rms 0sec '
        if delheave:
            fullcommand += '--delayed-heave 0sec '
        if delheave_rms:
            fullcommand += '--delayed-heave-rms 0sec '
        if nav:
            fullcommand += '--navigation '
        if nav_rms:
            fullcommand += '--navigation-rms 1sec '
        if True not in [height, delheave, height_rms, delheave_rms, nav, nav_rms]:
            print([height, delheave, height_rms, delheave_rms, nav, nav_rms])
            print("{} not a valid process type".format(datatype))
            fullcommand = ''
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    fullcommand += '"'
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def svc(self, svp_file, heavesource, select_method):
        '''Runs SoundVelocityCorrectHIPSWithCARIS with all the options.  Example: carisbatch.exe --run
        SoundVelocityCorrectHIPSWithCARIS --ssp --svp-file C:\HIPSData\SVC\cast.svp --profile-selection-method
        NEAREST_IN_TIME file:///C:/HIPSData/HDCS_Data/Test/Test.hips?Vessel=Vessel1'''
        if svp_file:
            fullcommand = self.hipscommand + ' --run SoundVelocityCorrectHIPSWithCARIS --svp-file "' + svp_file + '"'
        else:
            fullcommand = self.hipscommand + ' --run SoundVelocityCorrectHIPSWithCARIS'
        if select_method == 'NEAREST_IN_DISTANCE' or select_method == 'NEAREST_IN_TIME':
            fullcommand += ' --profile-selection-method ' + select_method
        elif select_method == 'NEAREST_IN_DISTANCE_WITHIN':
            fullcommand += ' --profile-selection-method ' + select_method
            fullcommand += ' --nearest-distance-hours 4'
        fullcommand += ' --heave-source "' + heavesource + '" --ssp '
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def compute_gps_tide(self, inputdata, heave_or_delayed, remote_heave=None, waterline=None, vdatum=None, fixed=None):
        '''Runs ComputeHIPSGPSTide with all the options.  Example: carisbatch.exe --run ComputeHIPSGPSTide
        --datum-separation-type MODEL --datum-model-file c:\HIPSData\Vdatum\vdatum.csar --dynamic-heave DELAYED_HEAVE
        --mru-remote-heave --antenna-offset --dynamic-draft --waterline REALTIME file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''
        fullcommand = ''
        if vdatum:
            band_name = find_csar_band_name(inputdata, log=self.logger)
            fullcommand = self.hipscommand + ' --run ComputeHIPSGPSTide --datum-separation-type MODEL'
            fullcommand += ' --datum-model-file "' + inputdata + '" --dynamic-heave ' + heave_or_delayed
            fullcommand += ' --datum-model-band "' + band_name + '" --dynamic-draft'
        if fixed:
            fullcommand = self.hipscommand + ' --run ComputeHIPSGPSTide --datum-separation-type FIXED'
            fullcommand += ' --datum-fixed-height "' + inputdata + '" --dynamic-heave ' + heave_or_delayed
            fullcommand += ' --dynamic-draft'
        if remote_heave:
            fullcommand += ' --mru-remote-heave'
        if waterline:
            fullcommand += ' --waterline ' + waterline
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def compute_hips_sep_model(self, heave_or_delayed):
        '''Runs ComputeHIPSSeparationModel with all the options.  Example: carisbatch.exe --run ComputeHIPSSeparationModel
        --datum-separation-type MODEL --datum-model-file c:\HIPSData\Vdatum\vdatum.csar --dynamic-heave DELAYED_HEAVE
        --mru-remote-heave --antenna-offset --dynamic-draft --waterline REALTIME file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''

        fullcommand = self.hipscommand + ' --run ComputeHIPSSeparationModel --resolution 10m'
        fullcommand += '" --dynamic-heave ' + heave_or_delayed
        fullcommand += ' --mru-remote-heave --antenna-offset --dynamic-draft --waterline REALTIME '
        fullcommand += '"file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def merge(self, tide_or_gps, heave_or_delayed):
        '''Runs MergeHIPS with all the options.  Example: carisbatch.exe --run MergeHIPS --tide GPS
        file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''
        fullcommand = self.hipscommand + ' --run MergeHIPS --tide ' + tide_or_gps + ' --heave-source ' + heave_or_delayed
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def compute_tpu(self, tide_meas, tide_zone, sv_meas, sv_surf, source, tcari=False, delayed=False, added=None):
        '''Runs ComputeHIPSTPU with all the options.  Example: carisbatch.exe --run ComputeHIPSTPU --tide-measured 1.0m
         --sv measured 1500m/s --source-heave REALTIME file:///C:/HIPSData/HDCS_Data/Test/Test.hips?Vessel=Vessel1;
         Day=2017-005'''
        source_nav = ''
        source_sonar = ''
        source_gyro = ''
        source_pitch = ''
        source_roll = ''
        source_heave = ''
        source_tide = ''
        if source is "VESSEL":
            source_nav = "VESSEL"
            source_sonar = "VESSEL"
            source_gyro = "VESSEL"
            source_pitch = "VESSEL"
            source_roll = "VESSEL"
            source_heave = "VESSEL"
            source_tide = "STATIC"
        elif source is "REALTIME":
            source_nav = "REALTIME"
            source_sonar = "REALTIME"
            source_gyro = "REALTIME"
            source_pitch = "REALTIME"
            source_roll = "REALTIME"
            source_heave = "REALTIME"
            source_tide = "STATIC"
        if delayed:
            source_heave = "DELAYED"
        if tcari:
            source_tide = "REALTIME"

        if added == None:
            fullcommand = self.hipscommand + ' --run ComputeHIPSTPU --tide-measured ' + tide_meas + ' --tide-zoning ' + tide_zone
            fullcommand += ' --sv-measured ' + sv_meas + ' --sv-surface ' + sv_surf + ' --source-navigation ' + source_nav
            fullcommand += ' --source-sonar ' + source_sonar + ' --source-gyro ' + source_gyro + ' --source-pitch ' + source_pitch
            fullcommand += ' --source-roll ' + source_roll + ' --source-heave ' + source_heave + ' --source-tide ' + source_tide
            fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

            if self.bench:
                self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
            else:
                self.run_this(fullcommand)

        else:
            finaladded = []
            for line in added:
                justline = os.path.split(line)[1]
                finaladded.append(justline[:len(justline) - 4])
            last = len(finaladded) % 4
            iters = len(finaladded) / 4
            print('Total lines to Compute TPU = {}'.format(len(finaladded)))
            print('Running process on {} 4-line blocks'.format(iters))
            print('Running final process on {} leftover lines\n'.format(last))
            count = 0
            while count < iters:
                fullcommand = self.hipscommand + ' --run ComputeHIPSTPU --tide-measured ' + tide_meas + ' --tide-zoning ' + tide_zone
                fullcommand += ' --sv-measured ' + sv_meas + ' --sv-surface ' + sv_surf + ' --source-navigation ' + source_nav
                fullcommand += ' --source-sonar ' + source_sonar + ' --source-gyro ' + source_gyro + ' --source-pitch ' + source_pitch
                fullcommand += ' --source-roll ' + source_roll + ' --source-heave ' + source_heave + ' --source-tide ' + source_tide
                fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name,
                                                           self.sheet_name + '.hips?')
                fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + ';Line=' + finaladded[count * 4]
                fullcommand += '&Line=' + finaladded[count * 4 + 1] + '&Line=' + finaladded[count * 4 + 2] + '&Line=' + \
                               finaladded[count * 4 + 3] + '"'

                if self.bench:
                    self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
                else:
                    self.run_this(fullcommand)
                count += 1
            fullcommand = self.hipscommand + ' --run ComputeHIPSTPU --tide-measured ' + tide_meas + ' --tide-zoning ' + tide_zone
            fullcommand += ' --sv-measured ' + sv_meas + ' --sv-surface ' + sv_surf + ' --source-navigation ' + source_nav
            fullcommand += ' --source-sonar ' + source_sonar + ' --source-gyro ' + source_gyro + ' --source-pitch ' + source_pitch
            fullcommand += ' --source-roll ' + source_roll + ' --source-heave ' + source_heave + ' --source-tide ' + source_tide
            fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name,
                                                       self.sheet_name + '.hips?')
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num

            if last == 3:
                fullcommand += ';Line=' + finaladded[count * 4] + '&Line=' + finaladded[count * 4 + 1] + '&Line=' + \
                               finaladded[count * 4 + 2] + '"'
                if self.bench:
                    self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
                else:
                    self.run_this(fullcommand)
            if last == 2:
                fullcommand += ';Line=' + finaladded[count * 4] + '&Line=' + finaladded[count * 4 + 1] + '"'
                if self.bench:
                    self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
                else:
                    self.run_this(fullcommand)
            if last == 1:
                fullcommand += ';Line=' + finaladded[count * 4] + '"'
                if self.bench:
                    self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
                else:
                    self.run_this(fullcommand)

    def georef_bathymetry(self, tideopts, svcopts, gpstideopts, mergeopts, tpuopts, querybyline=False):
        # Only available in Caris 11 and beyond

        fullcommand = self.hipscommand + ' --run GeoreferenceHIPSBathymetry'
        if tideopts:
            if tideopts['file']:
                fullcommand += ' --tide-file "' + tideopts['file'] + '"'
        if svcopts:
            fullcommand += ' --compute-svc --ssp --profile-selection-method ' + svcopts['algorithm']
            if svcopts['file']:
                fullcommand += ' --svp "' + svcopts['file'] + '"'
            if svcopts['algorithm'] == 'NEAREST_IN_DISTANCE_WITHIN':
                fullcommand += ' --nearest-distance-hours 4'
        if gpstideopts:
            fullcommand += ' --compute-gps-vertical-adjustment'
            if gpstideopts['method'] == 'VDatum':
                band_name = find_csar_band_name(gpstideopts['file'], log=self.logger)
                fullcommand += ' --datum-model-file "' + gpstideopts['file'] + '"'
                fullcommand += ' --datum-model-band "' + band_name + '"'
            elif gpstideopts['method'] == 'static_offset':
                fullcommand += ' --vertical-offset "' + gpstideopts['staticopts'] + '"'
        fullcommand += ' --vertical-datum-reference ' + mergeopts['vertref']
        fullcommand += ' --heave-source ' + mergeopts['heavesrc']
        fullcommand += ' --compute-tpu'
        fullcommand += ' --tide-measured ' + tpuopts['options'][0] + ' --tide-zoning ' + tpuopts['options'][1]
        fullcommand += ' --sv-measured ' + tpuopts['options'][2] + ' --sv-surface ' + tpuopts['options'][3]
        fullcommand += ' --source-navigation ' + tpuopts['source']['source_nav']
        fullcommand += ' --source-sonar ' + tpuopts['source']['source_sonar']
        fullcommand += ' --source-gyro ' + tpuopts['source']['source_gyro']
        fullcommand += ' --source-pitch ' + tpuopts['source']['source_pitch']
        fullcommand += ' --source-roll ' + tpuopts['source']['source_roll']
        fullcommand += ' --source-heave ' + tpuopts['source']['source_heave']
        fullcommand += ' --source-tide ' + tpuopts['source']['source_tide']
        fullcommand += ' --output-components'

        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    fullcommand += '"'
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def new_hips_surface(self, epsg, extentlowx, extentlowy, extenthighx, extenthighy, resolution, iho, outputname, querybyline=False):
        '''Runs CreateHIPSGridWithCUBE with all the options.  Example: carisbatch.exe --run CreateHIPSGridWithCube
        --output-crs EPSG:26919 --extent 300000 5000000 350000 5050000 --resolution 1.0m --iho-order S44_1A
         file:///C:/HIPSData/HDCS_Data/Test/Test.hips C:\HIPSData\Products\CUBE1m.csar'''

        if resolution == '0.5m':
            cuberes = 'NOAA_0.5m'
        elif resolution == '1.0m':
            cuberes = 'NOAA_1m'
        elif resolution == '2.0m':
            cuberes = 'NOAA_2m'
        elif resolution == '4.0m':
            cuberes = 'NOAA_4m'
        elif resolution == '8.0m':
            cuberes = 'NOAA_8m'
        elif resolution == '16.0m':
            cuberes = 'NOAA_16m'
        else:
            raise AttributeError('{} Resolution is not supported'.format(resolution))

        fullcommand = self.hipscommand + ' --run CreateHIPSGridWithCube --output-crs EPSG:' + epsg + ' --extent '
        fullcommand += extentlowx + ' ' + extentlowy + ' ' + extenthighx + ' ' + extenthighy
        fullcommand += ' --keep-up-to-date'
        if self.noaa_support_files:
            fullcommand += ' --cube-config-file="' + self.cubeparams + '" --cube-config-name="' + cuberes + '"'
        fullcommand += ' --resolution ' + resolution + ' --iho-order ' + iho + ' "file:///'
        fullcommand += os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    pass
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num

        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def finalize_hips(self, outputname, minz, maxz, uncertainty='GREATER', applydesignated=True):
        '''Runs FinalizeRaster with all the options.  Example: carisbatch.exe --run FinalizeRaster --filter
        10.0m 40.0m --apply-designated --uncertainty-source GREATER C:\HIPSData\Products\CUBE1m.csar
        C:\HIPSData\Products\CUBE1m_Final.csar'''
        finalname = outputname[0:len(outputname) - 5] + '_final_' + minz + 'to' + maxz + '.cube'
        if applydesignated:
            fullcommand = self.hipscommand + ' --run FinalizeRaster --filter -' + maxz + ' -' + minz + ' --apply-designated '
            fullcommand += '--include-band Density --include-band Depth --include-band Hypothesis_Count '
            fullcommand += '--include-band Hypothesis_Strength --include-band Mean --include-band Node_Std_Dev '
            fullcommand += '--include-band Std_Dev --include-band Uncertainty --include-band User_Nominated '
            fullcommand += '--uncertainty-source ' + uncertainty + ' "' + outputname + '" "' + finalname + '"'
        else:
            fullcommand = self.hipscommand + ' --run FinalizeRaster --filter -' + maxz + ' -' + minz + ' '
            fullcommand += '--include-band Density --include-band Depth --include-band Hypothesis_Count '
            fullcommand += '--include-band Hypothesis_Strength --include-band Mean --include-band Node_Std_Dev '
            fullcommand += '--include-band Std_Dev --include-band Uncertainty --include-band User_Nominated '
            fullcommand += '--uncertainty-source ' + uncertainty + ' "' + outputname + '" "' + finalname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def new_vr_surface(self, mode, epsg, extentlowx, extentlowy, extenthighx, extenthighy, maxgrid, mingrid,
                       outputname, objrange=False, comprange=False, querybyline=False):
        '''Runs CreateVRSurface with all the options.  Example: carisbatch.exe --run CreateVRSurface
         --estimation-method CARIS_DENSITY --output-crs EPSG:26919 --extent 300000 5000000 350000 5050000
         --max-grid-size 64 --min-grid-size 4 file:///C:/HIPSData/HDCS_Data/Test/Test.hips
         C:\HIPSData\Products\VR.csar'''
        depthrange = ''
        fullcommand = ''

        if self.noaa_support_files:
            if comprange:
                depthrange = self.depth_coverage
            elif objrange:
                depthrange = self.depth_object
            elif mode == 'RANGE':
                print('No range file selected.  Please use the objrange or comprange switch to calculate a RANGE VR surface.')
                return

        if mode == 'RANGE':
            fullcommand = self.hipscommand + ' --run CreateVRSurface --estimation-method ' + mode + ' --output-crs EPSG:'
            fullcommand += epsg + ' --extent ' + extentlowx + ' ' + extentlowy + ' ' + extenthighx + ' ' + extenthighy
            if self.noaa_support_files:
                fullcommand += ' --range-file "' + depthrange
            fullcommand += '" --keep-partial-bins --input-band DEPTH --max-grid-size ' + maxgrid
            fullcommand += ' --min-grid-size ' + mingrid + ' --include-flag ACCEPTED "file:///'
            fullcommand += os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
            if querybyline:
                for line in self.converted_lines:
                    linename = os.path.splitext(os.path.split(line)[1])[0]
                    fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                    if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                        # last line
                        pass
                    else:
                        fullcommand += '&'
            else:
                fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
            if self.onlysurface_additionalvessel:
                fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
            fullcommand += '"'
            fullcommand += ' "' + outputname + '"'

        if mode == 'CALDER_RICE':
            fullcommand = self.hipscommand + ' --run CreateVRSurface --estimation-method ' + mode + ' --output-crs EPSG:'
            fullcommand += epsg + ' --extent ' + extentlowx + ' ' + extentlowy + ' ' + extenthighx + ' ' + extenthighy
            fullcommand += ' --finest-resolution 0.10m --coarsest-resolution 16.0m --points-per-cell 15'
            fullcommand += ' --area SWATH --keep-partial-bins'
            fullcommand += ' --max-grid-size ' + maxgrid + ' --min-grid-size ' + mingrid + ' --include-flag ACCEPTED "file:///'
            fullcommand += os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
            if querybyline:
                for line in self.converted_lines:
                    linename = os.path.splitext(os.path.split(line)[1])[0]
                    fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                    if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                        # last line
                        pass
                    else:
                        fullcommand += '&'
            else:
                fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
            if self.onlysurface_additionalvessel:
                fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
            fullcommand += '"'
            fullcommand += ' "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def populate_vr_surface(self, mode, iho, outputname, querybyline=False):
        '''Runs PopulateVRSurface with all the options.  Example: carisbatch.exe --run PopulateVRSurface --population-method
         CUBE --input-band Depth --include-flag ACCEPTED C:\HIPSData\Products\VR.csar file:///C:/HIPSData/HDCS_Data/Test/Test.hips'''

        fullcommand = self.hipscommand + ' --run PopulateVRSurface --population-method ' + mode + ' --input-band Depth'
        fullcommand += ' --include-flag ACCEPTED --iho-order ' + iho + ' --vertical-uncertainty "Depth TPU"'
        fullcommand += ' --horizontal-uncertainty "Position TPU" --display-bias HIGHEST --disambiguation-method DENSITY_LOCALE'
        if self.noaa_support_files:
            fullcommand += ' --cube-config-file="' + self.cubeparams + '" --cube-config-name="NOAA_VR"'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        if querybyline:
            for line in self.converted_lines:
                linename = os.path.splitext(os.path.split(line)[1])[0]
                fullcommand += 'Vessel=' + self.vessel_name + ';Line=' + linename
                if self.converted_lines.index(line) == (len(self.converted_lines) - 1):
                    # last line
                    pass
                else:
                    fullcommand += '&'
        else:
            fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def add_to_raster(self, outputname):
        '''Runs AddtoHIPSGrid with all the options.  Example: carisbatch.exe --run AddtoHIPSGrid
                 file:///C:/HIPSData/HDCS_Data/Test/Test.hips C:\HIPSData\Products\CUBE1m.csar'''
        fullcommand = self.hipscommand + ' --run AddtoHIPSGrid'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def remove_from_raster(self, outputname):
        '''Runs RemoveFromHIPSGrid with all the options.  Example: carisbatch.exe --run RemoveFromHIPSGrid
                 file:///C:/HIPSData/HDCS_Data/Test/Test.hips C:\HIPSData\Products\CUBE1m.csar'''
        fullcommand = self.hipscommand + ' --run RemoveFromHIPSGrid'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def add_to_vr(self, outputname):
        '''Runs AddtoVRSurface with all the options.  Example: carisbatch.exe --run AddToVRSurface
                 file:///C:/HIPSData/HDCS_Data/Test/Test.hips C:\HIPSData\Products\CUBE1m.csar'''
        fullcommand = self.hipscommand + ' --run AddtoVRSurface --update-type BOTH'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def remove_from_vr(self, outputname):
        '''Runs RemoveFromVRSurface with all the options.  Example: carisbatch.exe --run RemoveFromVRSurface
                 file:///C:/HIPSData/HDCS_Data/Test/Test.hips C:\HIPSData\Products\CUBE1m.csar'''
        fullcommand = self.hipscommand + ' --run RemoveFromVRSurface --update-type BOTH'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def add_to_mosaic(self, outputname, beampattern, type):
        '''Runs AddToSIPSMosaic with all the options.  Example carisbatch.exe --run AddToSIPSMosaic
        --mosaic-engine SIPS_SIDESCAN file:///C:/HIPSData/HDCS_Data/Test/Test.hips
        C:\HIPSData\Products\Mosaic.csar'''

        fullcommand = self.hipscommand + ' --run AddtoSIPSMosaic --mosaic-engine ' + type
        fullcommand += ' --beam-pattern-file "' + beampattern + '"'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def remove_from_mosaic(self, outputname):
        '''Runs AddToSIPSMosaic with all the options.  Example carisbatch.exe --run RemoveFromSIPSMosaic
        --mosaic-engine SIPS_SIDESCAN file:///C:/HIPSData/HDCS_Data/Test/Test.hips
        C:\HIPSData\Products\Mosaic.csar'''

        fullcommand = self.hipscommand + ' --run RemoveFromSIPSMosaic'
        fullcommand += ' "file:///' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips?')
        fullcommand += 'Vessel=' + self.vessel_name + ';Day=' + self.day_num
        if self.onlysurface_additionalvessel:
            fullcommand += '&Vessel=' + self.onlysurface_additionalvessel + ';Day=' + self.day_num
        fullcommand += '"'
        fullcommand += ' "' + outputname + '"'
        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def render_raster(self, surface, outputname, bandname='Depth'):
        '''Runs RenderRaster with all the options.  Example: carisbatch.exe --run RenderRaster --input-band
        Depth C:\HIPSData\Products\Raster.csar C:\HIPSData\Products\Rasterimg.csar'''

        fullcommand = self.hipscommand + ' --run RenderRaster --input-band ' + bandname
        fullcommand += ' ' + ' "' + surface + '" "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def export_raster(self, surface, output_type, outputname, bandname='Depth', forcebase=False):
        '''Runs ExportRaster with all the options.  Example: carisbatch.exe --run ExportRaster --output-format
        GeoTIFF --include-band Depth C:\HIPSData\Products\VR.csar C:\HIPSData\Products\VR.tiff'''

        if forcebase:
            if not self.basecommand:
                lic, msg = self.caris_base_license_check(printout=False)
                if not lic:
                    return
            fullcommand = self.basecommand + ' --run ExportRaster --output-format ' + output_type + ' --include-band'
        else:
            fullcommand = self.hipscommand + ' --run ExportRaster --output-format ' + output_type + ' --include-band'
        fullcommand += ' ' + bandname + ' "' + surface + '" "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def shift_raster(self, inputfile, outputfile, shiftfile, inputformat='RASTER', input_band='Depth',
                     elev_band='NAD83_MLLW'):
        r'''Runs ShiftElevationBands with all the options.  Example: carisbatch.exe --run ShiftElevationBands
        --shift-type RASTER --input-band ALL --shift-file "D:\NAD83-MLLW_Expanded.csar" --elevation-band NAD83_MLLW
        "D:\F00768_Laser.csar" "D:\F00768_Laser_New_NAD83_MLLW.csar"'''
        fullcommand = self.hipscommand + ' --run ShiftElevationBands --shift-type ' + str(inputformat)
        fullcommand += ' --input-band ' + input_band + ' --shift-file "' + shiftfile + '" --elevation-band ' + elev_band
        fullcommand += ' "' + inputfile + '" "' + outputfile + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def import_points_to_csar(self, source, output_epsg, dest_csar, resolution='8m', prim_band='Depth', grid_method='BASIC',
                              inputformat='ASCII', input_epsg=None, infofile=None):
        '''Runs ImportPoints with all the options.  Example: carisbatch.exe --run ImportPoints --input-format ASCII
        --input-crs EPSG:26918 --output-crs EPSG:26918 --gridding-method BASIC --resolution 8m --info-file
        c:\path_to_info_file --primary-band Depth c:\path_to_ascii_data c:\path_to_dest_csar'''
        if not self.basecommand:
            lic, msg = self.caris_base_license_check(printout=False)
            if not lic:
                return

        if str(inputformat) == 'ASCII':
            fullcommand = self.basecommand + ' --run ImportPoints --input-format ' + str(inputformat)
            if input_epsg:
                fullcommand += ' --input-crs EPSG:' + str(input_epsg)
            fullcommand += ' --output-crs EPSG:' + str(output_epsg)
            if infofile:
                fullcommand += ' --info-file "' + str(infofile) + '"'
        else:
            print('Invalid input format - {}.  This format is not supported.'.format(inputformat))
            return
        if grid_method:
            fullcommand += ' --resolution ' + str(resolution) + ' --gridding-method ' + grid_method
        fullcommand += ' --primary-band ' + prim_band + ' "' + source + '" "' + dest_csar + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def export_csar_to_ascii(self, inputcsar, output_crs, outputascii, inputband='Depth', inputprecision='9',
                             coordformat='LLDG_DD'):
        '''Runs ExportCoverageToASCII with all the options.  Example:  carisbatch.exe -r exportcoveragetoascii
        --include-band Depth 9 --output-crs EPSG:6319 --coordinate-format LLDG_DD --coordinate-precision 9
        --coordinate-unit m "F00768_Laser_rawdepths.csar" "F00768_Laser_rawdepths.txt"'''

        # 9 is max precision in carisbatch
        fullcommand = self.hipscommand + ' --run exportcoveragetoascii --include-band "' + str(inputband) + '" ' + str(inputprecision)
        fullcommand += ' --output-crs EPSG:' + output_crs + ' --coordinate-format "' + coordformat + '" --coordinate-precision '
        fullcommand += inputprecision + ' --coordinate-unit m "' + inputcsar + '" "' + outputascii + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def vr_csar_to_sr_csar(self, surface, output_res, outputname):
        '''Runs ResampleSurfacetoRaster with all the options.  Example: carisbatch.exe --run ResampleSurfacetoRaster
        --output-format GeoTIFF --include-band Depth C:\HIPSData\Products\VR.csar C:\HIPSData\Products\VR.tiff'''

        fullcommand = self.hipscommand + ' --run ResampleSurfacetoRaster --resolution ' + str(output_res)
        fullcommand += ' "' + surface + '" "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def bag_to_csar(self, bag, outputname):
        '''Runs CopytoCsar with all the options.  Example: carisbatch.exe --run CopytoCsar C:\HIPSData\Products\bag.bag
        C:\HIPSData\Products\bag.csar'''

        fullcommand = self.hipscommand + ' --run CopytoCsar'
        fullcommand += ' "' + bag + '" "' + outputname + '"'

        if self.bench:
            self.benchclass.run(fullcommand, self.logger, self.benchcsv, self.progressbar)
        else:
            self.run_this(fullcommand)

    def qctools_py3(self, outputname, flierfinder=False, gridqa=False, holidayfinder=False,
                    holidayfindermode="OBJECT_DETECTION", vr=False):
        # retrive the path to the "activate.bat"
        activate_file = retrieve_activate_batch()
        # script's input variables
        grid_path = outputname  # VR
        # grid_path = "C:\\Users\\gmasetti\\Desktop\\test_vr\\H12880_MB_1m_MLLW_Final.csar"  # SR

        flier_finder = "0"
        holiday_finder = "0"
        grid_qa = "0"

        if flierfinder:
            flier_finder = "1"
        if holidayfinder:
            holiday_finder = "1"
        if gridqa:
            grid_qa = "1"

        start = retrieve_noaa_folder_path()
        spackages = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        qcscripts = os.path.join(spackages, 'Python3', 'hyo2', 'qc', 'scripts', 'qc_scripts.py')
        startpy = retrieve_install_prefix()

        if os.path.exists(grid_path):
            args = ["cmd.exe", "/K", "set pythonpath=", "&&",  # run shell (/K: leave open (debugging), /C close the shell)
                    activate_file, "Pydro367", "&&",  # activate the Pydro36 virtual environment
                    'python', qcscripts,  # call the script with a few arguments
                    '"' + grid_path.replace("&", "^&") + '"',  # surface path
                    flier_finder,  # flier finder arguments
                    holiday_finder, holidayfindermode,  # holiday finder arguments
                    grid_qa,  # grid QA arguments
                    self.sheet_name + '_QC'  # QCTools Output Folder Name
                    ]
            subprocess.Popen(' '.join(args), creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            print("**QCTools skipped: This surface does not exist: {}**".format(grid_path))

    def log_to_pdf(self):
        outputpdf = os.path.splitext(self.logger)[0] + '.pdf'
        pdfclass = pyText2Pdf.pyText2Pdf(input_file=self.logger, output_file=outputpdf)
        pdfclass.Convert()

    def open_hips(self):
        fullcommand = '"' + os.path.join(os.path.split(self.hipscommand)[0], 'caris_hips.exe') + '"'
        fullcommand += ' "' + os.path.join(self.hdcs_folder, self.sheet_name, self.sheet_name + '.hips"')
        subprocess.Popen(fullcommand)
