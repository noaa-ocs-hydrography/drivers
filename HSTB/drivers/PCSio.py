import ctypes
import mmap
import os
import stat
import time
import sys
import glob
from datetime import datetime, timedelta, timezone
from collections import OrderedDict

import numpy as np

try:
    import xarray as xr
    xarray_enabled = True
except ImportError:
    xarray_enabled = False


from HSTB.drivers.pos_mv import PCSclassesV5R10
from HSTB.drivers.pos_mv import PCSclassesV5R9
from HSTB.drivers.pos_mv import PCSclassesV4


drivers = OrderedDict([("V5R10", PCSclassesV5R10),
                       ("V5R9", PCSclassesV5R9),
                       ("V4", PCSclassesV4),
                       ])


class PCSBaseFile(object):

    def __init__(self, fname=None, nCache=-1, bDebug=False, driver=None):
        """driver_version defines which PCSclasses file to use.
                None uses the first default
                a string value is the key to use with the drivers dict 
                    ex: "V5R10"
                a tuple of revision name and module object can specify a custom file
                    ex: ("V5R10", PCSclassesV5R10)
        """
        if driver is None:
            self.driver_key, self.driver = list(drivers.items())[0]
        else:
            try:
                self.driver = drivers[driver]
                self.driver_key = driver
            except KeyError:
                self.driver_key, self.driver = driver
        self.recHdr_size = ctypes.sizeof(self.driver.PCSRecordHeader)
        self.expandedHdrSize = ctypes.sizeof(self.driver.GrpRecordHeader)
        if fname:  # a pre-existing file
            self.LoadFile(fname, nCache, bDebug)
        else:  # create placeholders for the required data objects.
            pass

    def LoadFile(self, fname, nCache, bDebug=False):
        self.filename = fname
        self.filesize = os.stat(fname)[stat.ST_SIZE]
        try:
            self.sdffile = open(fname, 'r+b')
            self.msdffile = mmap.mmap(self.sdffile.fileno(), 0)
            self.style = 0
        except:
            self.msdffile = self.sdffile = open(fname, 'rb')
            self.style = 1
        if bDebug:
            print("using style", self.style)

        if bDebug:
            tic = time.time()
        self.CacheHeaders(nCache, bDebug)
        if bDebug:
            print(time.time() - tic, "seconds")

    def Readdata(self, data, pos=-1):
        '''Reads a ctypes dataset, any of the fixed size headers should work, can't read arbitrary sized data or ascii strings.
        Should call data.ReadFromFile( ) in general especially when reading ascii data or arbitrary length data.
        '''
        if pos >= 0:
            self.msdffile.seek(pos)
        if self.style == 0:  # read via string into the ctypes structure, works with file or mmap
            sz = ctypes.sizeof(data)
            s = self.msdffile.read(sz)
            if len(s) < sz:
                raise self.driver.EOD
            ctypes.memmove(ctypes.addressof(data), s, sz)
        else:
            self.msdffile.readinto(data)  # direct read -- only works on file/buffer objects (doesn't work with mmap)

    def ReadSensor(self, pos=-1):
        raise Exception("Need to override this method")

    def ReadSensorType(self, typeId, pos=-1):
        raise Exception("Need to override this method")

    def CacheHeaders(self, nCache=-1, bDebug=False):
        raise Exception("Need to override this method")

    def GetRecordClass(self, typeId, grp):
            # determine which record id it is and load that
        try:
            if grp == "$GRP":
                d = self.driver.GROUP_ID_VALUES
            elif grp == "$MSG":
                d = self.driver.MESSAGE_ID_VALUES
            rec = eval("self.driver." + d[typeId])  # has the mapping of record id to type
        except KeyError:
            raise self.driver.CORRUPT("typeId of %s (grp/msg=%s) is not recognized -- skip record data" % (str(typeId), grp))
        except UnboundLocalError:
            pass
        return rec

    def MakeRecordInstance(self, typeId, grp):
        return self.GetRecordClass(typeId, grp)()


class PCSFile(PCSBaseFile):

    def SkimSensor(self, pos=-1, skip=True):
        # Read the section header and figure out which data structure we are trying to read
        # cur = self.msdffile.tell() #if pos==-1 then we don't want to move the file pointer before final read -- store the current location
        if 0:
            sec = self.driver.PCSRecordHeader()  # get the general record header
            sec.ReadFromFile(self.msdffile, pos, skim=True)
            recpos = self.msdffile.tell() - self.recHdr_size
        else:
            # if sec.Start == "$GRP":
            sec = self.driver.GrpRecordHeader()  # get the expanded record header -- only valid for $GRP records
            sec.ReadFromFile(self.msdffile, pos, skim=True)
            recpos = self.msdffile.tell() - self.expandedHdrSize
        # skip to next message packet
        if skip:
            try:
                self.msdffile.seek(recpos + sec.Byte_count + self.recHdr_size)
            except ValueError:
                pass
        return recpos, sec

    def ReadSensor(self, pos=-1):
        recpos, sec = self.SkimSensor(pos, skip=False)
        # return the section data structure and following record that fit the data at the requested file position
        try:
            self.msdffile.seek(recpos)  # rewind and read the section header into the data record
            # print sec
            rec = self.ReadSensorType(sec.ID, sec.Start)
        except self.driver.CORRUPT as e:
            rec = None
            # print "*"*80
            # print e
            # print "!"*80
            self.msdffile.seek(recpos + sec.Byte_count + self.recHdr_size)

        return sec, rec

    def ReadSensorType(self, typeId, grp, pos=-1):
        rec = self.MakeRecordInstance(typeId, grp)
        rec.ReadFromFile(self.msdffile, pos)
        return rec

    def CacheHeaders(self, nCache=-1, bDebug=False, read_first_msg=False):
        '''Find the ping and section headers.  If a section is corrupt then following the ping header offset might lead back to the correct data.
        First SDF2 file has this error where one data section is a byte short but following the ping offset (rather than following all the sections) gets to the next ping header.

        nCache is the max number of ping headers to read up to and cache, -1 reads all ping headers.
        '''
        # hdr=FISHPACDATAPAGEHDR()

        # read_first_msg allows for just getting the first header of a long pos file
        # stick in a timer to let it time out if the grp or msg isn't showing up
        if read_first_msg:
            starttime = time.time()

        self.sensorHeaders = {}  # empty list of section headers and their absolute file positions for use with file.tell and file.seek
        self.sensorTimes = []
        self.msdffile.seek(0)  # start at beginning of file
        # if 1 or bDebug:
        #    print "\n\n\n!*!*!*!*!*!  SKIPPING INTO FILE  *!*!*!*!*!*!*!*!**!*\n\n\n"
        #    self.msdffile.seek(329380) #start at beginning of file
        try:
            spos = 0
            while nCache != 0:
                cpos = self.msdffile.tell()
                nCache -= 1
                if bDebug:
                    sec, rec = self.ReadSensor()
                    print(rec)
                else:
                    cpos, sec = self.SkimSensor()

                if sec.Start == "$GRP":
                    tt = sec.Time_types
                    t1 = tt & 0x0F
                    t2 = (tt & 0xF0) >> 4
                    if t1 == 2:
                        t = sec.Time_1
                    elif t2 == 2:
                        t = sec.Time_2
                    elif t1 == 1:
                        t = sec.Time_1
                    elif t2 == 1:
                        t = sec.Time_2
                    else:
                        t = sec.Time_1
                    curTime = (t, cpos)
                    try:
                        if abs(curTime[0] - lastTime[0]) > 60.0:  # @UndefinedVariable
                            self.sensorTimes.append(curTime)
                            lastTime = curTime  # @UnusedVariable
                            print(cpos)
                    except NameError:  # empty list -- populate the first item
                        self.sensorTimes.append(curTime)
                        lastTime = curTime  # @UnusedVariable
                self.sensorHeaders.setdefault((sec.ID, sec.Start), []).append(cpos)

                if self.msdffile.tell() >= self.filesize:
                    raise self.driver.EOD
                if bDebug:
                    print(self.msdffile.tell(), self.filesize)
                if read_first_msg:
                    if (read_first_msg in list(self.sensorHeaders.keys())) and self.sensorTimes:
                        break
                    elif abs(starttime - time.time()) > 3:
                        print('Unable to find {}, tried for 3 seconds.'.format(read_first_msg))
                        break
        except self.driver.EOD:
            if bDebug:
                print("Reached End of Data")
        # self.sensorTimes.append(curTime)
        # self.sensorTimes = np.array(self.sensorTimes, dtype=[('time', np.double), ('position', np.uint64)])
        # self.sensorTimes.sort(order = ["time", "position"])

    def QuickCache(self, grp, grp_id=-1, nCache=-1, bDebug=False):
        '''Use this function by opening a data file with cache size = 0 then call QuickCache with the type of data message 
        to cache the file positions for'''
        chunksize = 5 * 1024 * 1024
        self.msdffile.seek(0)  # start at beginning of file
        grp, grp_id = self.ConfirmGroupAndId(grp, grp_id)
        keystring = grp + chr(grp_id & 0x00FF) + chr((grp_id & 0xFF00) >> 8)  # six character string to search for which has the $GRP or $MSG tag and the group
        data = self.msdffile.read(chunksize)
        fileoffset = 0
        str_pos = -1
        position_list = self.sensorHeaders.setdefault((grp_id, grp), [])
        while len(data) > len(keystring):
            str_pos = data.find(b"$GRP" + chr(grp_id & 0x00FF).encode() + chr((grp_id & 0xFF00) >> 8).encode(), str_pos + 1)
            if str_pos >= 0:  # find returns -1 if no more tags found
                position_list.append(str_pos + fileoffset)
            else:
                # move the file pointer back to the last read data, just beyond the string in case the next tag was split on the chunk boundary
                if position_list and position_list[-1] + 6 > fileoffset:
                    fileoffset = position_list[-1] + len(keystring)
                else:  # didn't find any occurances -- go to almost the end of the current chunk
                    fileoffset = self.msdffile.tell() - len(keystring) + 1
                self.msdffile.seek(fileoffset)
                data = self.msdffile.read(chunksize)

    def ConfirmGroupAndId(self, grp, grp_id):
        if grp_id == -1:
            try:
                grp_id = self.driver.GROUP_VALUE_IDS[grp]
                grp = "$GRP"
            except KeyError:
                try:
                    grp_id = self.driver.MESSAGE_VALUE_IDS[grp]
                    grp = "$MSG"
                except KeyError:
                    raise Exception("Couldn't find the ID for grp=%s" % grp)
        return grp, grp_id

    def GetArray(self, grp, grp_id=-1, starttime=-1.0, endtime=-1.0):
        grp, grp_id = self.ConfirmGroupAndId(grp, grp_id)
        positions = self.sensorHeaders[(grp_id, grp)]
        if starttime < 0:
            i1 = 0
        else:
            fpos = self.sensorTimes[np.searchsorted(self.sensorTimes["time"], starttime, side="left")]['position']
            i1 = np.searchsorted(positions, fpos, side="left")
        if endtime < 0:
            i2 = len(positions)
        else:
            fpos = self.sensorTimes[np.searchsorted(self.sensorTimes["time"], endtime, side="right")]['position']
            i2 = np.searchsorted(positions, fpos, side="right")

        cls = self.GetRecordClass(grp_id, grp)
        # carray = np.array([cls()] * len(positions[i1:i2]), cls._dtype)
        carray = np.zeros(len(positions[i1:i2]), cls._dtype)
        for i, cpos in enumerate(positions[i1:i2]):
            try:
                carray[i] = np.ctypeslib.as_array(self.ReadSensorType(grp_id, grp, cpos))
            except self.driver.EOD:
                carray = carray[:-1]
        return carray

    def HeaveTimeSeries(self):
        return self.GetAllArrays("Heave_True_Heave_Data", 111, ["Time_Distance_Fields.Time_1", "Time_Distance_Fields.Time_types", "True_Heave", "Heave", ])


def weekly_seconds_to_UTC_timestamps(week_secs, weekstart_datetime=None, weekstart_year=None, weekstart_week=None):
    """
    Convert gps week seconds to UTC timestamp (seconds since 1970,1,1).  Takes in either a datetime object that
    represents the start of the week or a isocalendar (accessible through datetime) tuple that gives the same
    information.

    Expects weekstart_datetime to be the start of the week on Sunday

    Parameters
    ----------
    week_secs: np array, array of timestamps since the beginning of the week (how POS time is stored)
    weekstart_datetime: datetime.datetime, object representing the start of the UNIX week (Sunday)
    weekstart_year: int, year for the start of the week, ex: 2020
    weekstart_week: int, week number for the start of the week, ex: 14

    Returns
    -------
    weekstart: datetime object, represents the start of the UTC week
    timestamps: np array, same shape as week_secs, UTC timestamps

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


def _pos_convert(posfile, weekstart_year, weekstart_week):
    f = PCSFile(posfile, nCache=0)
    f.QuickCache('$GRP', 1)
    data = f.GetArray('$GRP', 1)
    if not data['Latitude'].any():
        raise ValueError('pos_to_xarray: Group1 not found, is required for xarray conversion')
    t_type = data['Time_Distance_Fields']['Time_types'][0]
    t1_type = t_type & 7
    if not t1_type == 2:  # UTC Weekly Seconds
        raise NotImplementedError('pos_to_xarray: Expected time in UTC Weekly Seconds (2), found : {} (0=POS, 1=GPS)'.format(t1_type))

    alt, lat, lon, weektime = data['Altitude'], data['Latitude'], data['Longitude'], data['Time_Distance_Fields']['Time_1']
    weekstart, utctime = weekly_seconds_to_UTC_timestamps(weektime, weekstart_year=weekstart_year, weekstart_week=weekstart_week)
    alt.astype(np.float32)

    # found this to be necessary for sbet/smrmsg, sorting here as well just in case
    time_indices = utctime.argsort()
    pos_dataset = xr.Dataset({'latitude': (['time'], lat[time_indices]),
                              'longitude': (['time'], lon[time_indices]),
                              'altitude': (['time'], alt[time_indices])},
                             coords={'time': utctime[time_indices]},
                             attrs={'reference': {'latitude': 'reference point', 'longitude': 'reference point',
                                                  'altitude': 'reference point'},
                                    'units': {'latitude': 'degrees', 'longitude': 'degrees', 'altitude': 'meters'}})
    return pos_dataset


def pos_to_xarray(posfile: str, weekstart_year: int, weekstart_week: int):
    if not xarray_enabled:
        raise EnvironmentError('pos_to_xarray: Unable to import xarray, pos_to_xarray disabled')
    attrs = {'mission_date': datetime.fromisocalendar(weekstart_year, weekstart_week, 1).strftime('%Y-%m-%d %H:%M:%S')}
    posdat = _pos_convert(posfile, weekstart_year, weekstart_week)
    attrs['pos_files'] = {os.path.split(posfile)[1]: [float(posdat.time.values[0]), float(posdat.time.values[-1])]}
    posdat.attrs = attrs
    return posdat


def posfiles_to_xarray(posfiles: list, weekstart_year: int = None, weekstart_week: int = None):
    newdata = []
    totalposfiles = {}
    for cnt, posf in enumerate(posfiles):
        print('Reading from {}'.format(posf))
        converted_data = pos_to_xarray(posf, weekstart_year=weekstart_year, weekstart_week=weekstart_week)
        newdata.append(converted_data)
        totalposfiles.update(converted_data.pos_files)
    navdata = xr.concat(newdata, dim='time')
    del newdata
    # pos files might be in any time order
    navdata = navdata.sortby('time', ascending=True)
    # shovel in the total file attributes
    navdata.attrs['pos_files'] = totalposfiles
    return navdata


def print_some_records(file_object, recordnum: int = 50):
    """
    Used in Kluster file analyzer, print out the first x records in the file for the user to examine
    """
    cur_counter = 0
    if isinstance(file_object, str):
        file_object = PCSFile(file_object)
    if isinstance(file_object, PCSFile):
        file_object.msdffile.seek(0)
        while cur_counter < recordnum + 1:
            cur_counter += 1
            curpos = file_object.msdffile.tell()
            print('*****************************************************')
            try:
                hdr, data = file_object.ReadSensor()
                print(hdr)
                print(data)
            except:
                file_object.msdffile.seek(curpos)
                _, hdr = file_object.SkimSensor()
                print(hdr)
                print('Cannot decode record')


def main():
    import optparse
    print("Version 12.2.b")
    tic = time.time()
    parser = optparse.OptionParser()

    def showhelp(opt, opt_str, val, p):
        parser.print_help()
        sys.exit(0)
    parser.add_option("-?", action='callback', callback=showhelp)
    parser.add_option("-i", "--inputfiles", dest='filefilter', type='string', default='', help=r'File filter to process matching files.  Specify a single file or wildcards.  E.g. c:\temp\test.sdf or c:\temp\*.sdf')
    parser.add_option("-o", "--output", dest='outname', type='string', default='.', help=r'Output directory to export data into. Trailing slash means place in directory otherwise last part of path is interpreted as root filename e.g.  C:\temp\ or c:\temp\ExportFiles_')

    parser.add_option("-w", "--writeback", dest="writeback_filter", type='string', default='', help=r"File filter of sensor.csv files to write values back into the original data files (listed in the CSVs)")

    parser.add_option("-d", "--dump", dest="dump_filter", type='string', default='', help=r"File filter of sdf2 or sdfx files to dump header/metadata to screen")

    # parser.add_option("-p", "--processes", dest='processes', type='int', default = 1, help='Number of processes (%d detected) to spawn while converting data'%number_of_processors())

    (opts, args) = parser.parse_args()
    if opts.filefilter:
        files = glob.glob(opts.filefilter)
        print("Preparing to process %d files:" % len(files))
        sorted_files = []
        for fname in files:
            pass
    if opts.writeback_filter:
        files = glob.glob(opts.writeback_filter)
        if files:
            pass
        else:
            print("No files match the file filter", opts.filefilter, opts.writeback_filter)

    if opts.dump_filter:
        files = glob.glob(opts.dump_filter)
        for fname in files:
            PCSFile(fname, bDebug=True)
            print("FINISHED DUMPING ", fname)


if __name__ == "__main__":
    # fname = r'e:\Data\POS_MV\2011_097_2805clip.000'
    #fname = r'G:\Data\PCS\2013_258B_2805.367'

    if 1:
        fname = r"C:\Data\PosPac\2019_216_2904.000"
        f = PCSFile(fname, nCache=0, bDebug=False, driver="V5R9")
        # f = PCSFile(fname)
        # fname = r'C:\PydroTrunk\DocsAndDemoData\pos_mv\v5\2016_313_S222.000'
        # f = PCSFile(fname, nCache=0, bDebug=False, driver="V5R9")
        f.CacheHeaders(read_first_msg=(20, "$MSG"))
        msg20 = f.GetArray("$MSG", 20)
        f.CacheHeaders()  # bDebug=True)
        msg20s = f.GetArray("$MSG", 20)
        # print f.ReadSensor(23796)
        # print f.ReadSensor(33256)
        # print f.ReadSensor()
        # print f.ReadSensor()
        # print f.ReadSensor()
        f = PCSFile(fname, nCache=0, bDebug=False, driver="V5R10")
        f.CacheHeaders(bDebug=True)
        #a = f.QuickCache("$GRP", 4)
        #a = f.GetArray("$GRP", 4)
        # print a[0]
        # print time.time()
        # print "run time", time.time()-tic, "aquisition time",f.sensorTimes[-1][0]-f.sensorTimes[0][0]

        # a=f.GetArray("Heave_True_Heave_Data", -1, 390000, 400006)
        fname = r'C:\PydroTrunk\DocsAndDemoData\pos_mv\v4\2013_258B_2805.367'
        f = PCSFile(fname, nCache=0, bDebug=False, driver="V4")
        f.CacheHeaders(bDebug=True)
    else:
        main()
