"""
sbet.py
G.Rice
20121116
V 0.2
Last updated 20160316

modified by S. Greenaway

Writen for Sam to extract SBETS in to an array.  More complex functions
may follow.  A numcolumns key work argument was also added to all for the
parsing of other POSPac out files.

SBET fields are:
0: 'time - gps week seconds
1: 'latitude - radians
2: 'longitude - radians
3: 'altitude - meters
4: 'x_vel'
5: 'y_vel'
6: 'z_vel'
7: 'roll'
8: 'pitch'
9:'platform_heading'
10:'wander_angle'
11:'x_acceleration'
12:'y_acceleration'
13:'z_acceleration'
14:'x_angular_rate'
15:'y_angular_rate'
16:'z_angular'

navdif fields are:

0: time - gps week seconds
1: North Position difference - meters
2: East Position difference - meters
3: Down Position difference - meters
4: North Velocity difference - meters / second
5: East Velocity difference - meters / second
6: Down Velocity difference - meters / second
7: Roll difference - degrees
8: Pitch difference - degrees
9: Heading difference - degrees
10: 2D radial position difference - meters
11: 3D radial position difference - meters
12: 2D radial velocity difference - meters / second
13: 3D radial velocity difference - meters / second

smrmsg (uncertainty) files are:

0: time - gps week seconds
1: North position RMS error - meters
2: East position RMS error - meters
3: Down position RMS error - meters
4: North velocity RMS error - meters / second
5: East velocity RMS error - meters / second
6: Down velotiy RMS error - meters / second
7: Roll RMS error - arc minutes
8: Pitch RMS error - arc minutes
9: Heading RMS error - arc - minutes
"""

from datetime import datetime, timedelta, timezone
import numpy as np
import struct
import xarray as xr
import matplotlib.pyplot as plt
import os
from pyproj import CRS

plt.ion()


def read(infilename, columns = [], numcolumns = 17):
    """
    Reads the sbet file from the provided filename.  Columns is a list of
    column numbers to be read; if empty all columns are read.  An array is
    returned with the requested columns with time always being the first
    column.
    """
    #read the data
    data = np.fromfile(infilename, dtype = float)
    data.shape = (-1, numcolumns)
    # figure out which columns are to be exported
    if len(columns) == 0:
        outcolumns = np.arange(0,numcolumns)
    else:
        outcolumns = []
        outcolumns.append(1)
        for entry in columns:
            outcolumns.append(entry)
        outcolumns = np.asarray(outcolumns)
    
    return data[:, outcolumns]


def fft(infilename, columns = []):
    """
    Reads the file by the name provided and takes the fft of each column and
    returns the result.  Each column in the returned array corrisponds to the
    column requested, where the first column is always the frequencies.  The
    complex result is rearranged to put negative and positive frequencies in
    the correct location.
    """
    data = read(infilename, columns)
    fftdata = np.zeros(data.shape, dtype = complex)
    numsamples, numcolums = data.shape
    sample_period = np.mean(data[1:,0] - data[:-1,0])
    # get the frequencies
    fftdata[:,0] = np.fft.fftshift(np.fft.fftfreq(numsamples, sample_period))
    # get the fft of all columns
    fftdata[:,1:] = np.fft.fftshift(np.fft.fft(data[:,1:], axis = 0))
    return fftdata


def plot_nav(navarray, basetime = 0):
    """
    Creates a plot similar to Glen's other navarrays such as from Kongsberg 
    systems, etc.
    """
    time = navarray[:,0] + basetime
    fig = plt.figure()
    ax1 = fig.add_subplot(221)
    ax2 = fig.add_subplot(222)
    ax3 = fig.add_subplot(614, sharex = ax2)
    ax4 = fig.add_subplot(615, sharex = ax2)
    ax5 = fig.add_subplot(616, sharex = ax2)
    ax1.plot(np.rad2deg(navarray[:,2]),np.rad2deg(navarray[:,1]))
    ax1.set_xlabel('Longitude (Degrees)')
    ax1.set_ylabel('Latitude (Degrees)')
    ax1.grid()
    ax2.plot(time,np.rad2deg(navarray[:,9]))
    ax2.set_ylabel('Heading (Degrees)')
    ax2.set_xlabel('Time (Seconds)')
    ax2.grid()
    ax3.plot(time,navarray[:,3])
    ax3.set_ylabel('Height (Meters)')
    ax3.grid()
    ax4.plot(time,np.rad2deg(navarray[:,7]))
    ax4.plot(time,np.rad2deg(navarray[:,8]))
    ax4.set_ylabel('Degress')
    ax4.legend(('Roll','Pitch'))
    ax4.grid()
    ax5.plot(time,navarray[:,4])
    ax5.plot(time,navarray[:,5])
    ax5.plot(time,navarray[:,6])
    ax5.set_ylabel('Speed (Meters / Second)')
    ax5.set_xlabel('Time (Seconds)')
    ax5.legend(('X','Y','Z'))
    ax5.grid()
    ax2.set_xlim((time.min(),time.max()))
    plt.draw()
    
    
def get_time(year, daynumber):
    """
    Converts the year and day of year to get a base time in seconds since 1970
    for the GPS week.  This is so the data can be compared with POSIX time.
    """
    # subtract 1 because the first day of the year does not start with zero
    ordinal = datetime.toordinal(datetime(year,1,1)) + daynumber - 1
    dow = datetime.fromordinal(ordinal).weekday() + 1
    if dow == 7:
        # shift sunday to be start of week.
        dow = 0
    # 1970-1-1 is julian day 719163
    POSIXdays = ordinal - 719163 - dow
    basetime = POSIXdays * 24 * 3600
    return basetime


def get_export_info_from_log(logfile):
    """
    Read the POSPac export log to get the relevant attributes for the exported SBET.  SBET basically has no metadata,
    so this log file it generates is the only way to figure it out.  Log file is plain text, looks something like this:

    --------------------------------------------------------------------------------
    EXPORT Data Export Utility [Jun 18 2018]
    Copyright (c) 1997-2018 Applanix Corporation.  All rights reserved.
    Date : 09/09/18    Time : 17:01:12
    --------------------------------------------------------------------------------
    Mission date        : 9/9/2018
    Input file          : S:\2018\OPR-G343-FH-18\H13131\POSPac_Projects\FH_2702_R2Sonic\2018-252_AM\RTX\RTX\H13131_251_2702\Proc\sbet_H13131_251_2702.out
    Output file         : S:\2018\OPR-G343-FH-18\H13131\POSPac_Projects\FH_2702_R2Sonic\2018-252_AM\RTX\RTX\H13131_251_2702\Export\export_H13131_251_2702.out
    Output Rate Type    : Specified Time Interval
    Time Interval       : 0.020
    Start time          : 0.000
    End time            : 999999.000
    UTC offset          : 18.000
    Lat/Lon units       : Radians
    Height              : Ellipsoidal
    Grid                : Universal Transverse Mercator 
    Zone                : UTM North 01 (180W to 174W) 
    Datum               : NAD83 (2011) 
    Ellipsoid           : GRS 1980 
    Transformation type : 14 Parameter
    Target epoch        : 2018.687671
    --------------------------------------------------------------------------------
    Processing completed.

    Parameters
    ----------
    logfile: str, file path to the log file

    Returns
    -------
    attrs: dict, relevant data from the log file as a dictionary

    """
    try:
        attributes = {}
        with open(logfile, 'r') as lfile:
            lns = lfile.readlines()
            for ln in lns:
                # if ln[0:10] == 'Input file':
                #     infile = ln.split(' : ')[1].rstrip()
                #     infile = os.path.split(infile)[1]
                #     attributes['input_sbet_file'] = infile
                if ln[0:11] == 'Output file':
                    outfile = ln.split(' : ')[1].rstrip()
                    outfile = os.path.split(outfile)[1]
                    attributes['exported_sbet_file'] = outfile
                # if ln[0:13] == 'Time Interval':
                #     samplerate = float(ln.split(' : ')[1].rstrip())
                #     samplerate_hz = str(1 / samplerate)
                #     attributes['sbet_sample_rate_hertz'] = samplerate_hz
                elif ln[0:5] == 'Datum':
                    dtm = ln.split(' : ')[1].rstrip().upper()
                    if dtm.find('NAD83') != -1:
                        dtm = 'NAD83'
                    elif dtm.find('WGS84') != -1:
                        dtm = 'WGS84'
                    attributes['sbet_datum'] = dtm
                # elif ln[0:4] == 'Zone':
                #     attributes['sbet_zone'] = ln.split(' : ')[1].rstrip()
                # elif ln[0:4] == 'Grid':
                #     attributes['sbet_grid'] = ln.split(' : ')[1].rstrip()
                elif ln[0:9] == 'Ellipsoid':
                    attributes['sbet_ellipsoid'] = ln.split(' : ')[1].rstrip()
                elif ln[0:7] == 'Mission':
                    attributes['sbet_mission_date'] = ln.split(' : ')[1].rstrip()
                    if attributes['sbet_mission_date']:
                        attributes['sbet_mission_date'] = datetime.strptime(attributes['sbet_mission_date'], '%m/%d/%Y')
        req_keys = ['sbet_mission_date', 'sbet_ellipsoid', 'sbet_datum', 'exported_sbet_file']
        for ky in req_keys:
            if ky not in attributes:
                print('{}: Not a valid export log file, unable to find the {} line'.format(logfile, ky))
                return None
        return attributes
    except TypeError:
        print('Expected a string path to the logfile, got {}'.format(logfile))
        return None
    except FileNotFoundError:
        print('Logfile does not exist: {}'.format(logfile))
        return None
    

def weekly_seconds_to_UTC_timestamps(week_secs, weekstart_datetime=None, weekstart_year=None, weekstart_week=None):
    """
    Convert gps week seconds to UTC timestamp (seconds since 1970,1,1).  Takes in either a datetime object that
    represents the start of the week or a isocalendar (accessible through datetime) tuple that gives the same 
    information.

    Expects weekstart_datetime to be the start of the week on Sunday
    
    Parameters
    ----------
    week_secs: numpy array, array of timestamps since the beginning of the week (how SBET time is stored)
    weekstart_datetime: datetime.datetime, object representing the start of the UNIX week (Sunday)
    weekstart_year: int, year for the start of the week, ex: 2020
    weekstart_week: int, week number for the start of the week, ex: 14

    Returns
    -------
    weekstart: datetime object, represents the start of the UTC week
    timestamps: numpy array, same shape as week_secs, UTC timestamps

    """
    if weekstart_datetime is None and (weekstart_year is not None) and (weekstart_week is not None):
        weekstart = datetime.strptime(str(weekstart_year) + '-' + str(weekstart_week) + '-' + str(1), '%G-%V-%u')
        # this gets you week start if week started on Monday (ISO standard).  We want UNIX time where the week starts
        #    on Sunday
        weekstart = weekstart - timedelta(days=1)
    elif weekstart_datetime is not None:
        weekstart = weekstart_datetime
        weekstart = weekstart - timedelta(days=weekstart.weekday())
    else:
        raise ValueError('Expected either weekstart_datetime or both weekstart_year/weekstart_week.')
    
    utc_weekly_offset = weekstart.replace(tzinfo=timezone.utc).timestamp()
    timestamps = week_secs + utc_weekly_offset

    return weekstart, timestamps


def _sbet_convert(sbetfile, weekstart_year, weekstart_week):
    """
    Perform the load and conversion to xarray for the POS MV SBET

    Parameters
    ----------
    sbetfile: str, full file path to the sbet file
    weekstart_year: int, if you aren't providing a logfile, must provide the year of the sbet here
    weekstart_week: int, if you aren't providing a logfile, must provide the week of the sbet here

    Returns
    -------
    dat: xarray Dataset, data from the sbet relevant to our survey processing


    """
    sbet_data = np.fromfile(sbetfile, dtype=float)
    try:
        sbet_data.shape = (-1, 17)
    except ValueError:
        print('Unable to load the sbet file, found an odd number of records...')
        return None

    # retain time, lat, lon, altitude
    sbet_data = sbet_data[:, 0:4]
    weekstart, sbet_data[:, 0] = weekly_seconds_to_UTC_timestamps(sbet_data[:, 0], weekstart_year=weekstart_year,
                                                                  weekstart_week=weekstart_week)

    alt = sbet_data[:, 3]
    alt = alt.astype(np.float32)

    # found this to be necessary for smrmsg, sorting here as well just in case
    time_indices = sbet_data[:, 0].argsort()
    sbetdat = xr.Dataset({'sbet_latitude': (['time'], np.rad2deg(sbet_data[:, 1][time_indices])),
                          'sbet_longitude': (['time'], np.rad2deg(sbet_data[:, 2][time_indices])),
                          'sbet_altitude': (['time'], alt[time_indices])},
                         coords={'time': sbet_data[:, 0][time_indices]},
                         attrs={'reference': {'sbet_latitude': 'reference point', 'sbet_longitude': 'reference point',
                                              'sbet_altitude': 'reference point'},
                                'units': {'sbet_latitude': 'degrees', 'sbet_longitude': 'degrees', 'sbet_altitude': 'meters'}})
    return sbetdat


def _smrmsg_convert(smrmsgfile, weekstart_year, weekstart_week):
    """
    Perform the load and conversion to xarray for the POS MV SMRMSG error file

    Parameters
    ----------
    smrmsgfile: str, full file path to the smrmsg file
    weekstart_year: int, if you aren't providing a logfile, must provide the year of the sbet here
    weekstart_week: int, if you aren't providing a logfile, must provide the week of the sbet here

    Returns
    -------
    dat: xarray Dataset, data from the smrmsg relevant to our survey processing

    """
    smrmsg_data = np.fromfile(smrmsgfile, dtype=float)
    try:
        smrmsg_data.shape = (-1, 10)
    except ValueError:
        print('Unable to load the smrmsg file, found an odd number of records...')
        return None
    weekstart, smrmsg_data[:, 0] = weekly_seconds_to_UTC_timestamps(smrmsg_data[:, 0],
                                                                    weekstart_year=weekstart_year,
                                                                    weekstart_week=weekstart_week)
    npe = smrmsg_data[:, 1]
    npe = npe.astype(np.float32)
    epe = smrmsg_data[:, 2]
    epe = epe.astype(np.float32)
    dpe = smrmsg_data[:, 3]
    dpe = dpe.astype(np.float32)

    # motion error is in arc-minutes, convert to degrees
    roll_error = smrmsg_data[:, 7] * (1 / 60)
    roll_error = roll_error.astype(np.float32)
    pitch_error = smrmsg_data[:, 8] * (1 / 60)
    pitch_error = pitch_error.astype(np.float32)
    heading_error = smrmsg_data[:, 9] * (1 / 60)
    heading_error = heading_error.astype(np.float32)

    # sort by time, i'm finding smrmsg files that are all over the place
    time_indices = smrmsg_data[:, 0].argsort()
    smrmsgdat = xr.Dataset({'sbet_north_position_error': (['time'], npe[time_indices]), 'sbet_east_position_error': (['time'], epe[time_indices]),
                            'sbet_down_position_error': (['time'], dpe[time_indices]), 'sbet_roll_error': (['time'], roll_error[time_indices]),
                            'sbet_pitch_error': (['time'], pitch_error[time_indices]), 'sbet_heading_error': (['time'], heading_error[time_indices])},
                           coords={'time': smrmsg_data[:, 0][time_indices]},
                           attrs={'reference': {'sbet_north_position_error': 'None', 'sbet_east_position_error': 'None',
                                                'sbet_down_position_error': 'None', 'sbet_roll_error': 'None',
                                                'sbet_pitch_error': 'None', 'sbet_heading_error': 'None'},
                                  'units': {'sbet_north_position_error': 'meters (1 sigma)',
                                            'sbet_east_position_error': 'meters (1 sigma)',
                                            'sbet_down_position_error': 'meters (1 sigma)', 'sbet_roll_error': 'degrees (1 sigma)',
                                            'sbet_pitch_error': 'degrees (1 sigma)', 'sbet_heading_error': 'degrees (1 sigma)'}})
    return smrmsgdat


def sbet_to_xarray(sbetfile, smrmsgfile=None, logfile=None, weekstart_year=None, weekstart_week=None, override_datum=None,
                   override_grid=None, override_zone=None, override_ellipsoid=None):
    """
    Convert an sbet to an xarray Dataset object, containing the metadata and variables that we are interested in.

    You can include the error file as well, if so, it will be interpolated to the sbet
    
    Use in one of two modes:
    
    1. With an exported log file from POSPac...
    
        sbet = sbet_to_xarray(r"C:\collab\dasktest\data_dir\sbet_logs\2904_2019_KongsbergEM2040_2019-190_NAD83_SBET.out", 
                              r"C:\collab\dasktest\data_dir\sbet_logs\export_Mission 1.log")
        <xarray.Dataset>
        Dimensions:    (time: 1121501)
        Coordinates:
          * time       (time) float64 1.507e+09 1.507e+09 ... 1.507e+09 1.507e+09
        Data variables:
            sbet_latitude   (time) float64 36.93 36.93 36.93 36.93 ... 36.94 36.94 36.94
            sbet_longitude  (time) float64 -76.34 -76.34 -76.34 ... -76.37 -76.37 -76.37
            sbet_altitude   (time) float64 -37.49 -37.49 -37.49 ... -36.98 -36.98 -36.98
        Attributes:
            mission_date:       2017-10-05 00:00:00
            grid:               Universal Transverse Mercator
            zone:               UTM North 20 (66W to 60W)
            datum:              NAD83
            ellipsoid:          NAD83
            logging rate (hz):  50
    
    2. With explicit week information (need the week/year to convert from weekly seconds to POSIX timestamp)

        sbet = sbet_to_xarray(r"C:\collab\dasktest\data_dir\sbet_logs\2904_2019_KongsbergEM2040_2019-190_NAD83_SBET.out",
                              weekstart_year=2017, weekstart_week=40, override_datum='WGS84')
        <xarray.Dataset>
        Dimensions:    (time: 1121501)
        Coordinates:
          * time       (time) float64 1.507e+09 1.507e+09 ... 1.507e+09 1.507e+09
        Data variables:
            sbet_latitude   (time) float64 36.93 36.93 36.93 36.93 ... 36.94 36.94 36.94
            sbet_longitude  (time) float64 -76.34 -76.34 -76.34 ... -76.37 -76.37 -76.37
            sbet_altitude   (time) float64 -37.49 -37.49 -37.49 ... -36.98 -36.98 -36.98
        Attributes:
            logging rate (hz):  50
            mission_date:       2017-10-01 00:00:00
            datum:              WGS84
    
    Parameters
    ----------
    sbetfile: str, full file path to the sbet file
    smrmsgfile: str, full file path to the sbet file
    logfile: str, full file path to the sbet export log file
    weekstart_year: int, if you aren't providing a logfile, must provide the year of the sbet here
    weekstart_week: int, if you aren't providing a logfile, must provide the week of the sbet here
    override_datum: optional, str, provide a string datum identifier if you want to override what is read from the log
                    or you don't have a log, ex: 'NAD83 (2011)'
    override_grid: optional, str, provide a string grid identifier if you want to override what is read from the log
                   or you don't have a log, ex: 'Universal Transverse Mercator'
    override_zone: optional, str, provide a string zone identifier if you want to override what is read from the log
                   or you don't have a log, ex: 'UTM North 20 (66W to 60W)'
    override_ellipsoid: optional, str, provide a string ellipsoid identifier if you want to override what is read from
                        the log or you don't have a log, ex: 'GRS80'

    Returns
    -------
    xarray Dataset
        data and attribution from the sbet relevant to our survey processing
    """

    if logfile is not None:
        attrs = get_export_info_from_log(logfile)
        if attrs is None:
            raise ValueError('Log file invalid, does not contain the correct lines.')
        attrs.pop('exported_sbet_file')
        if not attrs['sbet_datum'] or attrs['sbet_mission_date'] is None:
            raise ValueError('Provided log does not seem to have either a datum or a mission date: {}'.format(logfile))
        weekstart_year, weekstart_week, weekstart_day = attrs['sbet_mission_date'].isocalendar()
        attrs['sbet_mission_date'] = attrs['sbet_mission_date'].strftime('%Y-%m-%d %H:%M:%S')
    elif weekstart_year is not None and weekstart_week is not None and override_datum is not None:
        attrs = {'sbet_mission_date': datetime.fromisocalendar(weekstart_year, weekstart_week, 1).strftime('%Y-%m-%d %H:%M:%S')}
    else:
        raise ValueError('Expected either a log file to be provided or a year/week representing the start of the week and a datum.')

    sbetdat = _sbet_convert(sbetfile, weekstart_year, weekstart_week)
    if smrmsgfile is not None:
        smrmsgdat = _smrmsg_convert(smrmsgfile, weekstart_year, weekstart_week)
        if smrmsgdat is not None:
            # smrmsg is 1hz, sbetdat can be anything, generally 50hz (exported) or 200hz
            smrmsgdat = smrmsgdat.interp_like(sbetdat)

            # interp_like auto switches to float64 in order to provide NaNs where needed, according to docs
            smrmsgdat['sbet_north_position_error'] = smrmsgdat['sbet_north_position_error'].astype(np.float32)
            smrmsgdat['sbet_east_position_error'] = smrmsgdat['sbet_east_position_error'].astype(np.float32)
            smrmsgdat['sbet_down_position_error'] = smrmsgdat['sbet_down_position_error'].astype(np.float32)
            smrmsgdat['sbet_roll_error'] = smrmsgdat['sbet_roll_error'].astype(np.float32)
            smrmsgdat['sbet_pitch_error'] = smrmsgdat['sbet_pitch_error'].astype(np.float32)
            smrmsgdat['sbet_heading_error'] = smrmsgdat['sbet_heading_error'].astype(np.float32)
            sbetdat = xr.merge([sbetdat, smrmsgdat])

    if override_datum is not None:
        attrs['sbet_datum'] = override_datum
    if override_ellipsoid is not None:
        attrs['sbet_ellipsoid'] = override_ellipsoid
    if override_grid is not None:
        attrs['sbet_grid'] = override_grid
    if override_zone is not None:
        attrs['sbet_zone'] = override_zone
    sbet_rate = np.round(int(1 / (sbetdat.time[1] - sbetdat.time[0])), -1)  # nearest ten hz
    attrs['sbet_logging rate (hz)'] = str(sbet_rate)
    attrs['nav_files'] = {os.path.split(sbetfile)[1]: sbet_fast_read_start_end_time(sbetfile)}
    if smrmsgfile is not None:
        attrs['nav_error_files'] = {os.path.split(smrmsgfile)[1]: smrmsg_fast_read_start_end_time(smrmsgfile)}
    else:
        attrs['nav_error_files'] = {}

    sbetdat.attrs = attrs
    return sbetdat


def sbets_to_xarray(sbetfiles: list, smrmsgfiles: list = None, logfiles: list = None, weekstart_year: int = None,
                    weekstart_week: int = None, override_datum: str = None, override_grid: str = None,
                    override_zone: str = None, override_ellipsoid: str = None):
    """
    convenience function for running sbet_to_xarray multiple times and concatenating the result

    Parameters
    ----------
    sbetfiles
        list of full file paths to the sbet files
    smrmsgfiles
        list of full file paths to the smrmsg files
    logfiles
        list of full file paths to the sbet export log files
    weekstart_year
        if you aren't providing a logfile, must provide the year of the sbet here
    weekstart_week
        if you aren't providing a logfile, must provide the week of the sbet here
    override_datum
        provide a string datum identifier if you want to override what is read from the log or you don't have a log, ex: 'NAD83 (2011)'
    override_grid
        provide a string grid identifier if you want to override what is read from the log or you don't have a log, ex: 'Universal Transverse Mercator'
    override_zone
        provide a string zone identifier if you want to override what is read from the log or you don't have a log, ex: 'UTM North 20 (66W to 60W)'
    override_ellipsoid
        provide a string ellipsoid identifier if you want to override what is read from the log or you don't have a log, ex: 'GRS80'

    Returns
    -------
    xarray Dataset
        data and attribution from the sbets relevant to our survey processing
    """

    newdata = []
    # concatenating datasets will override the attributes, no existing way to do combine_attrs='update'
    totalsbetfiles = {}
    totalerrorfiles = {}
    for cnt, sbet in enumerate(sbetfiles):
        if smrmsgfiles:
            sfile = smrmsgfiles[cnt]
        else:
            sfile = None
        if logfiles:
            lfile = logfiles[cnt]
        else:
            lfile = None
        converted_data = sbet_to_xarray(sbet, smrmsgfile=sfile, logfile=lfile, weekstart_year=weekstart_year,
                                        weekstart_week=weekstart_week, override_datum=override_datum, override_grid=override_grid,
                                        override_zone=override_zone, override_ellipsoid=override_ellipsoid)
        newdata.append(converted_data)
        totalsbetfiles.update(converted_data.nav_files)
        totalerrorfiles.update(converted_data.nav_error_files)
    navdata = xr.concat(newdata, dim='time')
    del newdata
    # sbet files might be in any time order
    navdata = navdata.sortby('time', ascending=True)
    # shovel in the total file attributes
    navdata.attrs['nav_files'] = totalsbetfiles
    navdata.attrs['nav_error_files'] = totalerrorfiles
    return navdata


def smrmsg_to_xarray(smrmsgfile, logfile=None, weekstart_year=None, weekstart_week=None):
    """
    Convert an smrmsg file to an xarray Dataset object, containing the metadata and variables that we are interested in.

    Parameters
    ----------
    smrmsgfile: str, full file path to the smrmsg file (SBET uncertainty file)
    logfile: str, full file path to the sbet export log file
    weekstart_year: int, if you aren't providing a logfile, must provide the year of the sbet here
    weekstart_week: int, if you aren't providing a logfile, must provide the week of the sbet here

    Returns
    -------
    dat: xarray Dataset, data and attribution from the sbet relevant to our survey processing

    """
    if logfile is not None:
        attrs = get_export_info_from_log(logfile)
        if attrs['sbet_mission_date'] is None:
            raise ValueError('Provided log does not seem to have a mission date: {}'.format(logfile))
        weekstart_year, weekstart_week, weekstart_day = attrs['sbet_mission_date'].isocalendar()
    elif weekstart_year is not None and weekstart_week is not None:
        attrs = {}
    else:
        raise ValueError('Expected either a log file to be provided or a year/week representing the start of the week.')

    smrmsgdat = _smrmsg_convert(smrmsgfile, weekstart_year, weekstart_week)
    if smrmsgdat is not None:
        smrmsg_rate = int(1 / (smrmsgdat.time[1] - smrmsgdat.time[0]))

        final_attrs = {}
        if 'sbet_mission_date' not in attrs:
            attrs = {'sbet_mission_date': datetime.fromisocalendar(weekstart_year, weekstart_week, 1).strftime('%Y-%m-%d %H:%M:%S')}
        final_attrs['sbet_mission_date'] = attrs['mission_date']
        final_attrs['sbet_logging rate (hz)'] = smrmsg_rate
        final_attrs['sbet_source_file'] = smrmsgfile
        smrmsgdat.attrs = final_attrs
    else:
        smrmsgdat = None
    return smrmsgdat


def is_sbet(sbetfile: str):
    """
    Check if the file is an sbet.  Ideally we just rely on the checking if the file contains an even number of 17 doubles,
    but add in the time check just in case.

    Parameters
    ----------
    sbetfile
        file path to a POSPac sbet file

    Returns
    -------
    bool
        True if file is an sbet, False if not
    """

    try:
        with open(sbetfile, 'rb') as ofil:
            dat = ofil.read(8 * 17 * 2)  # read the first two records (8 bytes per double, 17 doubles, 2 records)
            ofil.seek(0, 2)
            totalsize = ofil.tell()
    except:
        print('unable to read sbet file: {}'.format(sbetfile))
        return False

    # POSPac system files like iin_2020_2097_S222_B.out that reside in the Proc folder of the POSPac project look
    #   identical to the sbet.  We can only identify them by name unfortunately.
    ignore_these_prefixes = ['vnav', 'iinkar', 'iin', 'xp']
    prefix = os.path.split(sbetfile)[1].split('_')[0]
    if prefix in ignore_these_prefixes:
        print('skipping {} as it is a POSPac system file'.format(sbetfile))
        return False

    try:
        unpacked = struct.unpack('d'*34, dat)
        time_diff = np.abs(unpacked[0] - unpacked[17])
    except:
        print('Unable to read from {}'.format(sbetfile))
        return False

    if time_diff < 10:  # not checking for gaps here, just ensuring that these two records contain time
        if totalsize % 17 == 0:
            return True
        else:
            # print('sbet does not contain a multiple of 17 total records: {}'.format(sbetfile))
            return False
    else:
        # print('sbet failed time difference check: {}'.format(sbetfile))
        return False


def is_smrmsg(smrmsgfile: str):
    """
    Check if the file is an smrmsg file.  Ideally we just rely on the checking if the file contains an even number of 10 doubles,
    but add in the time check just in case.

    Parameters
    ----------
    smrmsgfile
        file path to a POSPac smrmsg file

    Returns
    -------
    bool
        True if file is an smrmsg, False if not
    """

    try:
        with open(smrmsgfile, 'rb') as ofil:
            dat = ofil.read(8 * 10 * 2)  # read the first two records (8 bytes per double, 17 doubles, 2 records)
            ofil.seek(0, 2)
            totalsize = ofil.tell()
    except:
        print('unable to read smrmsg file: {}'.format(smrmsgfile))
        return False

    # POSPac system files like g111_2020_2097_S222_B.out that reside in the Extract folder of the POSPac project look
    #   identical to the smrmsg.  We can only identify them by name unfortunately.
    ignore_these_prefixes = ['g111', 's2rms', 'srms', 'vrms', 'rmsg']
    prefix = os.path.split(smrmsgfile)[1].split('_')[0]
    if prefix in ignore_these_prefixes:
        print('skipping {} as it is a POSPac system file'.format(smrmsgfile))
        return False

    try:
        unpacked = struct.unpack('d'*20, dat)
        time_diff = np.abs(unpacked[0] - unpacked[10])
    except:
        print('Unable to read from {}'.format(smrmsgfile))
        return False

    if time_diff < 10:  # not checking for gaps here, just ensuring that these two records contain time
        if totalsize % 10 == 0:
            return True
        else:
            # print('smrmsg does not contain a multiple of 10 total records')
            return False
    else:
        # print('smrmsg failed time difference check')
        return False


def sbet_fast_read_start_end_time(sbetfile: str):
    """
    Determine the start and end time of the provided POSPac sbet file by reading the first and last record.

    Parameters
    ----------
    sbetfile
        full file path to a POSPac sbet file

    Returns
    -------
    list
        list of floats, [start time, end time] for the sbet
    """

    try:
        with open(sbetfile, 'rb') as ofil:
            firsttime = struct.unpack('d', ofil.read(8))[0]  # read the first time
            ofil.seek(-17 * 8, 2)  # go to the start of the last record
            lasttime = struct.unpack('d', ofil.read(8))[0]  # read the last time
        return [float(np.round(firsttime, 3)), float(np.round(lasttime, 3))]
    except:
        print('unable to read sbet file: {}'.format(sbetfile))
        return None
    
    
def smrmsg_fast_read_start_end_time(smrmsgfile: str):
    """
    Determine the start and end time of the provided POSPac smrmsg file by reading the first and last record.

    Parameters
    ----------
    smrmsgfile
        full file path to a POSPac smrmsg file

    Returns
    -------
    list
        list of floats, [start time, end time] for the smrmsg file
    """

    try:
        with open(smrmsgfile, 'rb') as ofil:
            firsttime = struct.unpack('d', ofil.read(8))[0]  # read the first time
            ofil.seek(-10 * 8, 2)  # go to the start of the last record
            lasttime = struct.unpack('d', ofil.read(8))[0]  # read the last time
        return [float(np.round(firsttime, 3)), float(np.round(lasttime, 3))]
    except:
        print('unable to read smrmsg file: {}'.format(smrmsgfile))
        return None
