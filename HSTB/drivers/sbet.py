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
import xarray as xr
import matplotlib.pyplot as plt
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
                if ln[0:5] == 'Datum':
                    attributes['datum'] = ln.split(' : ')[1].rstrip()
                elif ln[0:4] == 'Zone':
                    attributes['zone'] = ln.split(' : ')[1].rstrip()
                elif ln[0:4] == 'Grid':
                    attributes['grid'] = ln.split(' : ')[1].rstrip()
                elif ln[0:9] == 'Ellipsoid':
                    attributes['ellipsoid'] = ln.split(' : ')[1].rstrip()
                elif ln[0:7] == 'Mission':
                    attributes['mission_date'] = ln.split(' : ')[1].rstrip()
                    if attributes['mission_date']:
                        attributes['mission_date'] = datetime.strptime(attributes['mission_date'], '%m/%d/%Y')
        return attributes
    except TypeError:
        print('Expected a string path to the logfile, got {}'.format(logfile))
    except FileNotFoundError:
        print('Logfile does not exist: {}'.format(logfile))


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
    sbetdat = xr.Dataset({'latitude': (['time'], np.rad2deg(sbet_data[:, 1][time_indices])),
                          'longitude': (['time'], np.rad2deg(sbet_data[:, 2][time_indices])),
                          'altitude': (['time'], alt[time_indices])},
                         coords={'time': sbet_data[:, 0][time_indices]},
                         attrs={'reference': {'latitude': 'reference point', 'longitude': 'reference point',
                                              'altitude': 'reference point'},
                                'units': {'latitude': 'degrees', 'longitude': 'meters', 'altitude': 'meters'}})
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
    smrmsgdat = xr.Dataset({'north_position_error': (['time'], npe[time_indices]), 'east_position_error': (['time'], epe[time_indices]),
                            'down_position_error': (['time'], dpe[time_indices]), 'roll_error': (['time'], roll_error[time_indices]),
                            'pitch_error': (['time'], pitch_error[time_indices]), 'heading_error': (['time'], heading_error[time_indices])},
                           coords={'time': smrmsg_data[:, 0][time_indices]},
                           attrs={'reference': {'north_position_error': 'None', 'east_position_error': 'None',
                                                'down_position_error': 'None', 'roll_error': 'None',
                                                'pitch_error': 'None', 'heading_error': 'None'},
                                  'units': {'north_position_error': 'meters (1 sigma)',
                                            'east_position_error': 'meters (1 sigma)',
                                            'down_position_error': 'meters (1 sigma)', 'roll_error': 'degrees (1 sigma)',
                                            'pitch_error': 'degrees (1 sigma)', 'heading_error': 'degrees (1 sigma)'}})
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
            latitude   (time) float64 36.93 36.93 36.93 36.93 ... 36.94 36.94 36.94
            longitude  (time) float64 -76.34 -76.34 -76.34 ... -76.37 -76.37 -76.37
            altitude   (time) float64 -37.49 -37.49 -37.49 ... -36.98 -36.98 -36.98
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
            latitude   (time) float64 36.93 36.93 36.93 36.93 ... 36.94 36.94 36.94
            longitude  (time) float64 -76.34 -76.34 -76.34 ... -76.37 -76.37 -76.37
            altitude   (time) float64 -37.49 -37.49 -37.49 ... -36.98 -36.98 -36.98
        Attributes:
            logging rate (hz):  50
            mission_date:       2017-10-01 00:00:00
            datum:              WGS84
    
    Parameters
    ----------
    sbetfile: str, full file path to the sbet file
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
    dat: xarray Dataset, data and attribution from the sbet relevant to our survey processing

    """
    if logfile is not None:
        attrs = get_export_info_from_log(logfile)
        if not attrs['datum'] or attrs['mission_date'] is None:
            raise ValueError('Provided log does not seem to have either a datum or a mission date: {}'.format(logfile))
        weekstart_year, weekstart_week, weekstart_day = attrs['mission_date'].isocalendar()
        attrs['mission_date'] = attrs['mission_date'].strftime('%Y-%m-%d %H:%M:%S')
    elif weekstart_year is not None and weekstart_week is not None and override_datum is not None:
        attrs = {'mission_date': datetime.fromisocalendar(weekstart_year, weekstart_week, 1).strftime('%Y-%m-%d %H:%M:%S')}
    else:
        raise ValueError('Expected either a log file to be provided or a year/week representing the start of the week and a datum.')

    sbetdat = _sbet_convert(sbetfile, weekstart_year, weekstart_week)
    sbet_rate = np.round(int(1 / (sbetdat.time[1] - sbetdat.time[0])), -1)  # nearest ten hz
    if smrmsgfile is not None:
        smrmsgdat = _smrmsg_convert(smrmsgfile, weekstart_year, weekstart_week)
        if smrmsgdat is not None:
            # smrmsg is 1hz, sbetdat can be anything, generally 50hz (exported) or 200hz
            smrmsgdat = smrmsgdat.interp_like(sbetdat)

            # interp_like auto switches to float64 in order to provide NaNs where needed, according to docs
            smrmsgdat['north_position_error'] = smrmsgdat['north_position_error'].astype(np.float32)
            smrmsgdat['east_position_error'] = smrmsgdat['east_position_error'].astype(np.float32)
            smrmsgdat['down_position_error'] = smrmsgdat['down_position_error'].astype(np.float32)
            smrmsgdat['roll_error'] = smrmsgdat['roll_error'].astype(np.float32)
            smrmsgdat['pitch_error'] = smrmsgdat['pitch_error'].astype(np.float32)
            smrmsgdat['heading_error'] = smrmsgdat['heading_error'].astype(np.float32)
            sbetdat = xr.merge([sbetdat, smrmsgdat])

    if override_datum is not None:
        attrs['datum'] = override_datum
    if override_ellipsoid is not None:
        attrs['ellipsoid'] = override_ellipsoid
    if override_grid is not None:
        attrs['grid'] = override_grid
    if override_zone is not None:
        attrs['zone'] = override_zone
    attrs['logging rate (hz)'] = str(sbet_rate)
    attrs['source_file'] = sbetfile

    sbetdat.attrs = attrs
    return sbetdat


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
        if attrs['mission_date'] is None:
            raise ValueError('Provided log does not seem to have a mission date: {}'.format(logfile))
        weekstart_year, weekstart_week, weekstart_day = attrs['mission_date'].isocalendar()
    elif weekstart_year is not None and weekstart_week is not None:
        attrs = {}
    else:
        raise ValueError('Expected either a log file to be provided or a year/week representing the start of the week.')

    smrmsgdat = _smrmsg_convert(smrmsgfile, weekstart_year, weekstart_week)
    if smrmsgdat is not None:
        smrmsg_rate = int(1 / (smrmsgdat.time[1] - smrmsgdat.time[0]))

        final_attrs = {}
        if 'mission_date' not in attrs:
            attrs['mission_date'] = weekstart.strftime('%Y-%m-%d %H:%M:%S')
        final_attrs['mission_date'] = attrs['mission_date']
        final_attrs['logging rate (hz)'] = smrmsg_rate
        final_attrs['source_file'] = smrmsgfile
        smrmsgdat.attrs = final_attrs
    else:
        smrmsgdat = None
    return smrmsgdat
