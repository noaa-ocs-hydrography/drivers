import ctypes
import os

import numpy

from .helpers import *
from HSTB.time import UTC
import HSTPBin
install_path = HSTPBin.__path__[0]

os.chdir(install_path)
dll = ctypes.CDLL(os.path.join(install_path, r'hips_io_sdku.dll'))
dll.HIPSIO_Init(ctypes.c_wchar_p(""), 0)

#from HSTPBin.PyPeekXTF import TideErrorFile


def InitLicense(path_to_license=""):
    # must use wide character
    return dll.HIPSIO_Init(ctypes.c_wchar_p(""), 0)


'''
dll.LineExists(ctypes.c_wchar_p(r"E:\Data\HDCS_Data\A910\A910_SWMB\WH05\2000-307\232_2035")) #exists
dll.LineExists(ctypes.c_wchar_p(r"E:\Data\HDCS_Data\A910\A910_SWMB\WH05\2000-307\232_2034")) #doesn't exist

h, m, s, x = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_double()
dll.TmStoHMSX(ctypes.c_double(3661.01),ctypes.pointer(h), ctypes.pointer(m), ctypes.pointer(s), ctypes.pointer(x))
print h,m,s,x
dll.TmHMSXtoS.restype=ctypes.c_double  #set the return type -- ctypes assumes an int return otherwise
print dll.TmHMSXtoS(h, m, s, x)
'''

'''Turn this into cython?'''


''' Having a probem setting the return type to c_void_p where it was converting to a long rather than a pointer.  
subclassing prevents this cast from happening, see--
http://stackoverflow.com/questions/17840144/why-does-setting-ctypes-dll-function-restype-c-void-p-return-long
'''


class my_void_p(ctypes.c_void_p):
    pass


class HDCSdata(object):
    def __init__(self, ftype):
        self.ftype = ftype
        self._Open = getattr(dll, "%sOpenDir" % ftype)
        self._Open.restype = my_void_p
        self._ReadSummary = getattr(dll, "%sSummary" % ftype)
        self._ReadLineSummary = getattr(dll, "%sLineSegment" % ftype)
        self._Read = getattr(dll, "%sReadSeq" % ftype)
        self._SetStatus = getattr(dll, "%sSetSummaryStatus" % ftype)  # not needed for sequential write mode; done via WriteSummary
        self._BeginWrite = getattr(dll, "%sBgnSeqWriteLineSegment" % ftype)
        self._Write = getattr(dll, "%sSeqWrite" % ftype)
        self._EndWrite = getattr(dll, "%sEndSeqWriteLineSegment" % ftype)
        self._WriteSummary = getattr(dll, "%sEndSeqWriteSummary" % ftype)
        self._Close = getattr(dll, "%sClose" % ftype)

    def Open(self, lineDir, accessTypeToken):  # checked
        rcode = ctypes.c_int()
        ret = self._Open(ctypes.c_wchar_p(lineDir), ctypes.c_wchar_p(accessTypeToken), ctypes.pointer(rcode))
        return ret, not bool(rcode)

    def Close(self, sensor):
        ret = self._Close(sensor)
        return ret

    def SetStatus(self, sensor, summaryStatus):
        ret = self._SetStatus(sensor, ctypes.c_uint(summaryStatus))
        return ret

    def BeginWrite(self, sensor, source):
        ret = self._BeginWrite(sensor, ctypes.c_wchar_p(source))
        return ret

    def EndWrite(self, sensor, status):
        ret = self._EndWrite(sensor, ctypes.c_uint(status))
        return ret

    def WriteSummary(self, sensor, summaryStatus):
        ret = self._WriteSummary(sensor, ctypes.c_uint(summaryStatus))
        return ret


def isREC_STATUS_REJECTED(status):
    return bool(long(status) & 1 << 31)


class HDCSAttitude(HDCSdata):
    dtypes = ('Gyro', 'Heave', 'TrueHeave', 'Pitch', 'Roll', 'SSSGyro', 'Tide', 'TideError', 'GPSHeight', 'GPSTide', 'DeltaDraft', 'SSSSensorHeight', 'SSSSensorDepth')

    def __init__(self, ftype):
        if ftype in self.dtypes:
            if ftype != 'TideError':
                HDCSdata.__init__(self, ftype)
            else:
                self.ftype = ftype
        else:
            self.ftype = None

    def ReadSummary(self, sensor):  # checked
        numLineSegments, numRecords = ctypes.c_int(), ctypes.c_int()
        minTime, maxTime, minSensor, maxSensor = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
        summaryStatus = ctypes.c_uint()
        ret = self._ReadSummary(sensor, ctypes.pointer(numLineSegments), ctypes.pointer(numRecords), ctypes.pointer(minTime), ctypes.pointer(maxTime), ctypes.pointer(minSensor), ctypes.pointer(maxSensor), ctypes.pointer(summaryStatus))
        return ret, numLineSegments.value, numRecords.value, minTime.value, maxTime.value, minSensor.value, maxSensor.value, summaryStatus.value

    def ReadLineSummary(self, sensor, segidx):  # checked
        #sourceFileName = ctypes.create_string_buffer(1000)
        sourceFileName = ctypes.c_wchar_p()
        bgnIndex, endIndex = ctypes.c_int(), ctypes.c_int()
        minTime, maxTime, minSensor, maxSensor = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
        status = ctypes.c_uint()
        ret = self._ReadLineSummary(sensor, ctypes.c_int(segidx), ctypes.pointer(sourceFileName), ctypes.pointer(bgnIndex), ctypes.pointer(endIndex), ctypes.pointer(minTime), ctypes.pointer(maxTime), ctypes.pointer(minSensor), ctypes.pointer(maxSensor), ctypes.pointer(status))
        return ret, str(sourceFileName.value), bgnIndex.value, endIndex.value, minTime.value, maxTime.value, minSensor.value, maxSensor.value, status.value

    def Read(self, sensor):  # checked
        caris_time, val, status = ctypes.c_double(), ctypes.c_double(), ctypes.c_uint()
        ret = self._Read(sensor, ctypes.pointer(caris_time), ctypes.pointer(val), ctypes.pointer(status))
        return ret, caris_time.value, val.value, status.value

    def Write(self, sensor, caris_time, val, status):
        ret = self._Write(sensor, ctypes.c_double(caris_time), ctypes.c_double(val), ctypes.c_uint(status))
        return ret

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, oddFactorSkip=1, bMean=True, bOnlyAccepted=False):
        # Returns HDCS attitude data time series in N x 3 NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, sensor value, record status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        bCleanup = False  # watch variable to indicate we skipped some rejected records and need to remove nulls before returning NumPyArray
        if bVerbose:
            verboseData = {'summaryStatus': None, 'sourceFileName': None}
        # (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        rcode = 1
        rcodeCaris = 0    # HDCS I/O "Okay"=0
        if 1:  # self.SetHDCS_DATA_PATH(hdcsdatapath):
            if self.ftype != 'TideError':
                attitude, _bOK = self.Open(pathToPVDL, "query")
                if attitude:
                    (rcodeCaris, numLineSegments, numRecords, minTime, maxTime, minSensor, maxSensor,  # @UnusedVariable
                     summaryStatus) = self.ReadSummary(attitude)
                    # print rcodeCaris, minTime, minSensor
                    if rcodeCaris == 0:
                        if bVerbose:
                            verboseData['summaryStatus'] = summaryStatus
                            # ReadLineSummary for sourceFileName
                            (rcodeCaris, sourceFileName,
                             bgnIndex, endIndex, minTime, maxTime, minSensor, maxSensor,  # @UnusedVariable
                             lineSegmentStatus) = self.ReadLineSummary(attitude, 1)  # @UnusedVariable
                            # print rcodeCaris, sourceFileName,bgnIndex, endIndex,minTime, maxTime,minSensor, maxSensor,lineSegmentStatus
                            if rcodeCaris == 0:
                                verboseData['sourceFileName'] = sourceFileName
                        NumPyArray = numpy.zeros((numRecords, 3), numpy.float64)
                        for recordNum in range(numRecords):
                            attituderecord = NumPyArray[recordNum]
                            (rcodeCaris,
                             attituderecord[0],  # time in leftmost column [UTCs80],
                             attituderecord[1],  # sensor value in next column [radians or meters], and record status in last column
                             attituderecord[2]) = self.Read(attitude)
                            if rcodeCaris != 0:
                                rcode = 0
                                break
                            else:
                                if bOnlyAccepted and isREC_STATUS_REJECTED(attituderecord[-1]):
                                    NumPyArray[recordNum] = 0.
                                    bCleanup = True  # remember to remove null records before return
                                    continue
                    else:
                        rcode = 0
                    self.Close(attitude)
                else:
                    rcode = 0
            else:
                bVerbose = False
                attitude = TideErrorFile(pathToPVDL)
                numRecords = attitude.getNumberOfRecords()
                NumPyArray = numpy.zeros((numRecords, 3), numpy.float64)
                for recordNum in range(numRecords):
                    attituderecord = NumPyArray[recordNum]
                    attituderecord[:] = attitude.read(recordNum + 1)[1:]
        else:
            rcode = 0
        if not rcode:
            NumPyArray = None
            if bVerbose:
                verboseData = None
        elif oddFactorSkip > 1:
            oddFactorSkip = int(oddFactorSkip)
            if not oddFactorSkip % 2:
                oddFactorSkip += 1
            if bMean:
                sensorvector = NumPyArray[:, 1]
                remdr = len(sensorvector) % oddFactorSkip
                if remdr:
                    sensorvector = sensorvector[:-remdr]
                try:
                    sensorvector.shape = (len(sensorvector) / oddFactorSkip, oddFactorSkip)
                except:
                    print (len(sensorvector) / oddFactorSkip, oddFactorSkip)
                    return None
            NumPyArray = NumPyArray[oddFactorSkip / 2:len(NumPyArray) - oddFactorSkip / 2:oddFactorSkip]
            if bMean:
                NumPyArray[:, 1] = numpy.mean(sensorvector, axis=1)
        if bCleanup:
            NumPyArray = numpy.delete(NumPyArray, numpy.where(~NumPyArray.any(axis=1))[0], 0)
        if bVerbose:
            return NumPyArray, verboseData
        else:
            return NumPyArray

    def WriteTimeSeries(self, pathToPVDL, NumPyArray, verboseData=None, sourcename='', sourceTypeExt='', summaryStatus=None, havestatus=(1, None), sortBytime=True):
        # Writes HDCS attitude time series from N x 3 NumPyArray; assumes NumPyArray sorted chronologically
        # (NumPyArray columns are time, sensor value, record status; e.g., time vector=NumPyArray[:,0])
        # verboseData = {'summaryStatus':<>, 'sourceFileName':<>}
        havestatus, recstatus = havestatus  # time & sensor value are required; do we have record status...
        if not havestatus and recstatus is None:
            recstatus = ZERO_STATUS
        numRecords = numpy.shape(NumPyArray)[0]
        numFields = numpy.shape(NumPyArray)[1]
        if (numRecords > 0) and (numFields > 1):
            (_hdcsdatapath, _proj, _vess, _yday, line) = SeparatePathFromPVDL(pathToPVDL)
            if verboseData:
                summaryStatus = verboseData['summaryStatus']
                sourcename = verboseData['sourceFileName']
            else:
                summaryStatus = ZERO_STATUS
                if not sourcename:
                    sourcename = line + str(sourceTypeExt)
            rcode = 1
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            # check to see if path to P/V/D/L directory exists; create to leaf dir L, if needed
            if not os.access(pathToPVDL, os.F_OK):
                os.makedirs(pathToPVDL)
            attitude, _bOK = self.Open(pathToPVDL, "create")
            if attitude:
                if rcodeCaris == 0:
                    if not sourcename:
                        sourcename = line + str(sourceTypeExt)
                    rcodeCaris = self.BeginWrite(attitude, str(sourcename))  # str() for unicode conversion
                    if rcodeCaris == 0:
                        if sortBytime:
                            sortIdx = numpy.argsort(NumPyArray[:, 0])  # Sorted NumPyArray indicies according to [increasing] time
                        for recordNum in range(numRecords):
                            if sortBytime:
                                attituderecord = NumPyArray[sortIdx[recordNum]]
                            else:
                                attituderecord = NumPyArray[recordNum]
                            if havestatus:
                                recstatus = attituderecord[2]
                            rcodeCaris = self.Write(attitude,
                                                    attituderecord[0],  # time [UTCs80],
                                                    attituderecord[1],  # attitude data Gyro, Pitch, Roll [radians] or [True]Heave [meters],
                                                    asSignedInt(recstatus))          # and record status
                            if rcodeCaris != 0:
                                break
                        if rcodeCaris == 0:
                            rcodeCaris = self.EndWrite(attitude, ZERO_STATUS)  # status=0 per HIPS I/O docs
                            if rcodeCaris == 0:  # redundant set of summaryStatus; however, min/max stats happen here????
                                self.WriteSummary(attitude, asSignedInt(summaryStatus))  # Don't care about return status at this point; will [attempt to] close next...
                self.Close(attitude)
                if rcodeCaris != 0:
                    rcode = 0
            else:
                rcode = 0
        else:
            rcode = 0
        return rcode


class HDCSNav(HDCSdata):
    dtypes = ('Navigation', 'SSSNavigation')

    def __init__(self, ftype):
        if ftype in self.dtypes:
            HDCSdata.__init__(self, ftype)
        else:
            self.ftype = None

    def ReadSummary(self, sensor):
        numLineSegments, numRecords, coordtype = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        minTime, maxTime, minLat, maxLat, minLon, maxLon = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
        summaryStatus = ctypes.c_uint()
        ret = self._ReadSummary(sensor, ctypes.pointer(numLineSegments), ctypes.pointer(numRecords), ctypes.pointer(coordtype), ctypes.pointer(minTime), ctypes.pointer(maxTime), ctypes.pointer(minLat), ctypes.pointer(maxLat), ctypes.pointer(minLon), ctypes.pointer(maxLon), ctypes.pointer(summaryStatus))
        return ret, numLineSegments.value, numRecords.value, coordtype.value, minTime.value, maxTime.value, minLat.value, maxLat.value, minLon.value, maxLon.value, summaryStatus.value

    def ReadLineSummary(self, sensor, segidx):
        #sourceFileName = ctypes.create_string_buffer(1000)
        sourceFileName = ctypes.c_wchar_p()
        bgnIndex, endIndex = ctypes.c_int(), ctypes.c_int()
        minTime, maxTime, minLat, maxLat, minLon, maxLon = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
        status = ctypes.c_uint()
        ret = self._ReadLineSummary(sensor, ctypes.c_int(segidx), ctypes.pointer(sourceFileName), ctypes.pointer(bgnIndex), ctypes.pointer(endIndex), ctypes.pointer(minTime), ctypes.pointer(maxTime), ctypes.pointer(minLat), ctypes.pointer(maxLat), ctypes.pointer(minLon), ctypes.pointer(maxLon), ctypes.pointer(status))
        return ret, str(sourceFileName.value), bgnIndex.value, endIndex.value, minTime.value, maxTime.value, minLat.value, maxLat.value, minLon.value, maxLon.value, status.value

    def Read(self, sensor):
        caris_time, lat, lon, acc, status = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_uint()
        ret = self._Read(sensor, ctypes.pointer(caris_time), ctypes.pointer(lat), ctypes.pointer(lon), ctypes.pointer(acc), ctypes.pointer(status))
        return ret, caris_time.value, lat.value, lon.value, acc.value, status.value

    def Write(self, sensor, caris_time, lat, lon, acc, status):
        ret = self._Write(sensor, ctypes.c_double(caris_time), ctypes.c_double(lat), ctypes.c_double(lon), ctypes.c_double(acc), ctypes.c_uint(status))
        return ret

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, oddFactorSkip=1, bOnlyAccepted=False):
        # Returns HDCS navigation data time series in N x 5 NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, lat, lon, accuracy, status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        bCleanup = False  # watch variable to indicate we skipped some rejected records and need to remove nulls before returning NumPyArray
        if bVerbose:
            verboseData = {'summaryStatus': None, 'sourceFileName': None}
        # (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        rcode = 1
        rcodeCaris = 0    # HDCS I/O "Okay"=0
        nav, _bOK = self.Open(pathToPVDL, "query")
        if nav:
            (rcodeCaris, numLineSegments, numRecords, coordType, minTime, maxTime, minLat, maxLat, minLon, maxLon,  # @UnusedVariable
             summaryStatus) = self.ReadSummary(nav)
            if rcodeCaris == 0:
                if bVerbose:
                    verboseData['summaryStatus'] = summaryStatus
                    # ReadLineSummary for sourceFileName (note reread of numRecords)
                    (rcodeCaris, sourceFileName, coordType, numRecords, minTime, maxTime, minLat, maxLat, minLon, maxLon,  # @UnusedVariable
                     lineSegmentStatus) = self.ReadLineSummary(nav, 1)  # @UnusedVariable
                    if rcodeCaris == 0:
                        verboseData['sourceFileName'] = sourceFileName
                NumPyArray = numpy.zeros((numRecords, 5), numpy.float64)
                for recordNum in range(numRecords):
                    (rcodeCaris, tyme, latitude, longitude, accuracy, status) = self.Read(nav)
                    if rcodeCaris != 0:
                        rcode = 0
                        break  # bad record--break out of loop
                    else:
                        if bOnlyAccepted and isREC_STATUS_REJECTED(status):
                            bCleanup = True  # remember to remove null records before return
                            continue
                        NumPyArray[recordNum] = [tyme, latitude, longitude, accuracy, status]
            else:
                rcode = 0
            self.Close(nav)
        else:
            rcode = 0
        if not rcode:
            NumPyArray = None
            if bVerbose:
                verboseData = None
        elif oddFactorSkip > 1:
            oddFactorSkip = int(oddFactorSkip)
            if not oddFactorSkip % 2:
                oddFactorSkip += 1
            NumPyArray = NumPyArray[oddFactorSkip / 2:len(NumPyArray) - oddFactorSkip / 2:oddFactorSkip]
        if bCleanup:
            NumPyArray = numpy.delete(NumPyArray, numpy.where(~NumPyArray.any(axis=1))[0], 0)
        if bVerbose:
            return NumPyArray, verboseData
        else:
            return NumPyArray

    def WriteTimeSeries(self, pathToPVDL, NumPyArray, verboseData=None, sourcename='', sourceTypeExt='', haveaccuracy=(1, None), havestatus=(1, None), sortBytime=True):
        # Writes HDCS navigation time series from N x 5 NumPyArray; assumes NumPyArray sorted chronologically
        # (NumPyArray columns are time, lat, lon, accuracy, record status; e.g., time vector=NumPyArray[:,0])
        # verboseData = {'summaryStatus':<>, 'sourceFileName':<>}
        fieldcount = 3    # time, lat & lon are required; do we have accuracy and/or record status...
        haveaccuracy, recaccuracy = haveaccuracy
        if haveaccuracy:
            fieldcount += 1
        elif recaccuracy is None:
            recaccuracy = 0.0
        havestatus, recstatus = havestatus
        if havestatus:
            fieldcount += 1
        elif recstatus is None:
            recstatus = ZERO_STATUS
        numRecords = numpy.shape(NumPyArray)[0]
        numFields = numpy.shape(NumPyArray)[1]
        if (numRecords > 0) and (numFields >= fieldcount):
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)  # @UnusedVariable
            if verboseData:
                summaryStatus = verboseData['summaryStatus']
                sourcename = verboseData['sourceFileName']
            else:
                from HSTPBin import PyPeekXTF
                summaryStatus = PyPeekXTF.NAV_EXAMINED_BY_HYDROG_MASK
                if not sourcename:
                    sourcename = line + str(sourceTypeExt)
            rcode = 1
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            # check to see if path to P/V/D/L directory exists; create to leaf dir L, if needed
            if not os.access(pathToPVDL, os.F_OK):
                os.makedirs(pathToPVDL)
            nav, _bOK = self.Open(pathToPVDL, "create")
            if nav:
                if rcodeCaris == 0:
                    rcodeCaris = self.BeginWrite(nav, str(sourcename))  # str() for unicode conversion
                    if rcodeCaris == 0:
                        if sortBytime:
                            sortIdx = numpy.argsort(NumPyArray[:, 0])  # Sorted NumPyArray indicies according to [increasing] time
                        for recordNum in range(numRecords):
                            if sortBytime:
                                navrecord = NumPyArray[sortIdx[recordNum]]
                            else:
                                navrecord = NumPyArray[recordNum]
                            if haveaccuracy:
                                recaccuracy = navrecord[3]
                                if havestatus:
                                    recstatus = navrecord[4]
                            elif havestatus:
                                recstatus = navrecord[3]
                            rcodeCaris = self.Write(nav,
                                                    navrecord[0],   # time in leftmost column [UTCs80],
                                                    navrecord[1],   # latitude in next column [radians],
                                                    navrecord[2],   # longitude in next column [radians],
                                                    recaccuracy,    # accuracy in next column,
                                                    asSignedInt(recstatus))      # and record status in last column
                            if rcodeCaris != 0:
                                break
                        if rcodeCaris == 0:
                            rcodeCaris = self.EndWrite(nav, ZERO_STATUS)  # line summary status=0 per HIPS I/O docs
                            if rcodeCaris == 0:
                                self.WriteSummary(nav, asSignedInt(summaryStatus))    # Don't care about return status at this point; will [attempt to] close next...
                self.Close(nav)
                if rcodeCaris != 0:
                    rcode = 0
            else:
                rcode = 0

        else:
            rcode = 0
        return rcode

    def Dump(self, pth, out_pipe):
        numpy.set_printoptions(precision=3, suppress=True, threshold=20, formatter={'float': lambda x: '%.3f' % x})
        timeseries = self.ReadTimeSeries(pth)
        for rec in timeseries:
            dt = UTC.UTCs80ToDateTime(rec[0])
            s = " ".join([dt.strftime("%Y-%m-%d %H:%M:%S.%f"), "%f %f" % (numpy.rad2deg(rec[1]), numpy.rad2deg(rec[2])), str(rec[3:]).replace("[", "").replace("]", "")]) + "\n"
            out_pipe.write(s)
        numpy.set_printoptions()


class HDCSSideScan(HDCSdata):
    dtypes = ('SSS', 'SSSProc')

    def __init__(self, ftype='SSSProc'):
        if ftype in self.dtypes:
            self.ftype = ftype
            self._Open = getattr(dll, "%sOpenDir" % ftype)
            self._Open.restype = my_void_p
            self._ReadSummary = getattr(dll, "%sSummary" % ftype)
            self._ReadLineSummary = getattr(dll, "%sLineSegment" % ftype)
            self._ReadProfile = getattr(dll, "%sReadProfile" % ftype)
            if ftype == 'SSS':
                self._ReadProfile2 = getattr(dll, "%sReadProfile2" % ftype)
            self._SetStatus = getattr(dll, "%sSetSummaryStatus" % ftype)  # not needed for sequential write mode; done via WriteSummary
            self._BeginWrite = getattr(dll, "%sBgnSeqWriteLineSegment" % ftype)
            self._WriteProfile = getattr(dll, "%sWriteProfile" % ftype)
            self._EndWrite = getattr(dll, "%sEndSeqWriteLineSegment" % ftype)
            self._WriteSummary = getattr(dll, "%sEndSeqWriteSummary" % ftype)
            self._Close = getattr(dll, "%sClose" % ftype)
        else:
            self.ftype = None

    def ReadSummary(self, sensor):
        numLineSegments, numProfiles = ctypes.c_uint(), ctypes.c_uint()
        minTime, maxTime = ctypes.c_double(), ctypes.c_double()
        sensorModel, summaryStatus = ctypes.c_uint(), ctypes.c_uint()
        ret = self._ReadSummary(sensor, ctypes.pointer(numLineSegments), ctypes.pointer(numProfiles), ctypes.pointer(minTime), ctypes.pointer(maxTime), ctypes.pointer(sensorModel), ctypes.pointer(summaryStatus))
        return ret, numLineSegments.value, numProfiles.value, minTime.value, maxTime.value, sensorModel.value, summaryStatus.value

    def ReadLineSummary(self, sensor, segidx):
        sourceFileName = ctypes.c_wchar_p()
        bgnIndex, endIndex = ctypes.c_uint(), ctypes.c_uint()
        minTime, maxTime = ctypes.c_double(), ctypes.c_double()
        status = ctypes.c_uint()
        ret = self._ReadLineSummary(sensor, ctypes.c_uint(segidx), ctypes.pointer(sourceFileName), ctypes.pointer(bgnIndex), ctypes.pointer(endIndex), ctypes.pointer(minTime), ctypes.pointer(maxTime), ctypes.pointer(status))
        return ret, str(sourceFileName.value), bgnIndex.value, endIndex.value, minTime.value, maxTime.value, status.value

    def ReadRawProfile(self, sensor, profileIdx, ctype=ctypes.c_ubyte, dtype=numpy.uint8, readData=1):
        status = ctypes.c_uint()
        time_ = ctypes.c_double()
        fishDepth, fishDepthDerv, altitude, altitudeDerv, pingNum = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        TVG, sourcePower, Attenuation = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        resolution, sampleInterval, range, frequency, samplePort, sampleStbd =  ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        portTrace, stbdTrace = ctypes.pointer(ctype()), ctypes.pointer(ctype())
        TVG2, sourcePower2, Attenuation2 = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        resolution2, sampleInterval2, range2, frequency2, samplePort2, sampleStbd2 =  ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        portTrace2, stbdTrace2 = ctypes.pointer(ctype()), ctypes.pointer(ctype())
        ret = self._ReadProfile(sensor, ctypes.c_uint(profileIdx), ctypes.pointer(status), ctypes.pointer(time_),
                                ctypes.pointer(fishDepth), ctypes.pointer(fishDepthDerv), ctypes.pointer(altitude), ctypes.pointer(altitudeDerv), ctypes.pointer(pingNum),
                                ctypes.pointer(TVG), ctypes.pointer(sourcePower), ctypes.pointer(Attenuation),
                                ctypes.pointer(resolution), ctypes.pointer(sampleInterval), ctypes.pointer(range), ctypes.pointer(frequency), ctypes.pointer(samplePort), ctypes.pointer(sampleStbd),
                                ctypes.pointer(portTrace), ctypes.pointer(stbdTrace),
                                ctypes.pointer(TVG2), ctypes.pointer(sourcePower2), ctypes.pointer(Attenuation2),
                                ctypes.pointer(resolution2), ctypes.pointer(sampleInterval2), ctypes.pointer(range2), ctypes.pointer(frequency2), ctypes.pointer(samplePort2), ctypes.pointer(sampleStbd2),
                                ctypes.pointer(portTrace2), ctypes.pointer(stbdTrace2),
                                ctypes.c_int(readData))
        port_ptr = ctypes.POINTER(ctype * samplePort.value)
        portTrace_value = numpy.frombuffer(ctypes.cast(portTrace, port_ptr).contents, dtype)
        stbd_ptr = ctypes.POINTER(ctype * sampleStbd.value)
        stbdTrace_value = numpy.frombuffer(ctypes.cast(stbdTrace, stbd_ptr).contents, dtype)
        return ret, status.value, time_.value, pingNum.value, altitude.value, fishDepth.value, resolution.value, samplePort.value, sampleStbd.value, sampleInterval.value, portTrace_value, stbdTrace_value

    def ReadRawProfile2(self, sensor, profileIdx, ctype=ctypes.c_ubyte, dtype=numpy.uint8, readData=1):
        (rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, portTrace, stbdTrace) = self._ReadRawProfile2(sensor, profileIdx, 1, 1, 0)
        if rcode == 0 and readData != 0:
            (rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, port, stbd) = self._ReadRawProfile2(sensor, profileIdx, samplePort, sampleStbd, readData)
            if rcode == 0:
                portTrace = numpy.zeros(samplePort, numpy.uint8)
                stbdTrace = numpy.zeros(sampleStbd, numpy.uint8)
                portTrace[:] = port
                stbdTrace[:] = stbd
        return rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, portTrace, stbdTrace

    def _ReadRawProfile2(self, sensor, profileIdx, portSize, stbdSize, readData=1):   
        status = ctypes.c_uint()
        time_ = ctypes.c_double()
        fishDepth, fishDepthDerv, altitude, altitudeDerv, pingNum = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        TVG, sourcePower, Attenuation = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        resolution, sampleInterval, range, frequency, samplePort, sampleStbd =  ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        portTrace, portTraceSize, stbdTrace, stbdTraceSize = (ctypes.c_ubyte * portSize)(), ctypes.c_uint(), (ctypes.c_ubyte * stbdSize)(), ctypes.c_uint()
        TVG2, sourcePower2, Attenuation2 = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        resolution2, sampleInterval2, range2, frequency2, samplePort2, sampleStbd2 =  ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        portTrace2, portTraceSize2, stbdTrace2, stbdTraceSize2 = (ctypes.c_ubyte * portSize)(), ctypes.c_uint(), (ctypes.c_ubyte * stbdSize)(), ctypes.c_uint()
        ret = self._ReadProfile2(sensor, ctypes.c_uint(profileIdx), ctypes.pointer(status), ctypes.pointer(time_),
                                ctypes.pointer(fishDepth), ctypes.pointer(fishDepthDerv), ctypes.pointer(altitude), ctypes.pointer(altitudeDerv), ctypes.pointer(pingNum),
                                ctypes.pointer(TVG), ctypes.pointer(sourcePower), ctypes.pointer(Attenuation),
                                ctypes.pointer(resolution), ctypes.pointer(sampleInterval), ctypes.pointer(range), ctypes.pointer(frequency), ctypes.pointer(samplePort), ctypes.pointer(sampleStbd),
                                ctypes.pointer(portTrace), ctypes.pointer(portTraceSize), ctypes.pointer(stbdTrace), ctypes.pointer(stbdTraceSize),
                                ctypes.pointer(TVG2), ctypes.pointer(sourcePower2), ctypes.pointer(Attenuation2),
                                ctypes.pointer(resolution2), ctypes.pointer(sampleInterval2), ctypes.pointer(range2), ctypes.pointer(frequency2), ctypes.pointer(samplePort2), ctypes.pointer(sampleStbd2),
                                ctypes.pointer(portTrace2), ctypes.pointer(portTraceSize2), ctypes.pointer(stbdTrace2), ctypes.pointer(stbdTraceSize2),
                                ctypes.c_int(readData))
        return ret, status.value, time_.value, pingNum.value, altitude.value, fishDepth.value, resolution.value, samplePort.value, sampleStbd.value, sampleInterval.value, portTrace, stbdTrace

    def ReadProcProfile(self, sensor, profileIdx, ctype=ctypes.c_ubyte, dtype=numpy.uint8, readData=1):
        time_ = ctypes.c_double()
        status, pingNum, altitude, resolution, samplePort, sampleStbd = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        portTrace, stbdTrace = ctypes.pointer(ctype()), ctypes.pointer(ctype())
        ret = self._ReadProfile(sensor, ctypes.c_uint(profileIdx), ctypes.pointer(status), ctypes.pointer(time_),
                                ctypes.pointer(pingNum), ctypes.pointer(altitude), ctypes.pointer(resolution), ctypes.pointer(samplePort), ctypes.pointer(sampleStbd),
                                ctypes.pointer(portTrace), ctypes.pointer(stbdTrace),
                                ctypes.c_int(readData))
        port_ptr = ctypes.POINTER(ctype * samplePort.value)
        portTrace_value = numpy.frombuffer(ctypes.cast(portTrace, port_ptr).contents, dtype)
        stbd_ptr = ctypes.POINTER(ctype * sampleStbd.value)
        stbdTrace_value = numpy.frombuffer(ctypes.cast(stbdTrace, stbd_ptr).contents, dtype)
        return ret, status.value, time_.value, pingNum.value, altitude.value, -1, resolution.value, samplePort.value, sampleStbd.value, -1, portTrace_value, stbdTrace_value

    def ReadProfiles(self, pathToPVDL, bVerbose=False):
        '''Returns HDCS SideScan data
        imageArray, timeArray, altitudeArray (m), fishDepthArray (m), resolution (m), sampleInterval (s), samplePort
        '''
        sss, _bOK = self.Open(pathToPVDL, "query")
        imageArray = None
        timeArray = None
        altitudeArray = None
        fishDepthArray = None
        resolution = -1
        samplePortSize = -1
        sampleStbdSize = -1
        sampleIntervalInit = -1
        if sss:
            (rcodeCaris, numLineSegments, numProfiles, minTime, maxTime, sensorModel, summaryStatus)= self.ReadSummary(sss)
            #numProfiles = 2000
            if bVerbose:
                print(rcodeCaris, numLineSegments, numProfiles, minTime, maxTime, sensorModel, summaryStatus)
            #(rcode, sourceFileName, bgnIndex, endIndex, minTime, maxTime, status) = self.ReadLineSummary(sss, 1)
            #print(rcode, sourceFileName, bgnIndex, endIndex, minTime, maxTime, status)
            if rcodeCaris == 0:
                ctype = ctypes.c_ubyte
                dtype = numpy.uint8
                if self.ftype == 'SSS':
                    ReadProfile = self.ReadRawProfile
                else:
                    ReadProfile = self.ReadProcProfile
                for idx in range(numProfiles):
                    (rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, portTrace, stbdTrace) = ReadProfile(sss, idx + 1, ctype, dtype)
                    SS_16BIT = 0x40000000 & status
                    SS_GET_PORT_SHIFT = (0xff00 & status) >> 8
                    SS_GET_STBD_SHIFT = 0x00ff & status
                    if idx == 0:
                        #print(rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, portTrace, stbdTrace)
                        if status != 0:
                            if bVerbose:
                                print(rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, portTrace, stbdTrace)
                            if SS_16BIT:
                                ctype = ctypes.c_ushort
                                dtype = numpy.uint16
                                (rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, portTrace, stbdTrace) = ReadProfile(sss, idx + 1, ctype, dtype)
                                if bVerbose:
                                    print(rcode, status, time_, pingNum, altitude, fishDepth, resolution, samplePort, sampleStbd, sampleInterval, portTrace, stbdTrace)
                            else:
                                print("status ERROR!")
                        samplePortSize = samplePort
                        sampleStbdSize = sampleStbd
                        sampleIntervalInit = sampleInterval
                        imageArray = numpy.zeros((numProfiles, samplePortSize + sampleStbdSize), dtype)
                        timeArray = numpy.zeros(numProfiles, numpy.float64)
                        altitudeArray = numpy.zeros(numProfiles, numpy.int32)
                        fishDepthArray = numpy.zeros(numProfiles, numpy.int32)
                    if rcode == 0:
                        if len(portTrace) != samplePortSize or len(stbdTrace) != sampleStbdSize:
                            print('error', idx, samplePortSize, len(portTrace), sampleStbdSize, len(stbdTrace))
                        else:
                            imageArray[idx, :samplePortSize] = portTrace[::-1] / 2**SS_GET_PORT_SHIFT
                            imageArray[idx, samplePortSize:] = stbdTrace / 2**SS_GET_STBD_SHIFT
#                             imageArray[idx, :samplePortSize] = portTrace[::-1]
#                             imageArray[idx, samplePortSize:] = stbdTrace
                        timeArray[idx] = time_
                        altitudeArray[idx] = altitude
                        fishDepthArray[idx] = fishDepth
            self.Close(sss)
        if imageArray is None:
            return imageArray, timeArray, altitudeArray, fishDepthArray, resolution, sampleIntervalInit, samplePortSize
        else:
            return imageArray, timeArray, altitudeArray * 0.1, fishDepthArray * 0.1, resolution * 0.01, sampleIntervalInit * 0.001, samplePortSize

    def ReadContacts(self, pathToPVDL):
        '''Returns contacts list, each contact is a dictionary
VERSION 4
Colour Map =
2   ,2016-245,09:36:30,JJD,2016-245,17:36:32,JJD,239-1226,FSHCNT      ,1,1767  , 38.88,   29.1872636,  -91.6216657,  0.00,  0.00,  0.00,30  ,30  ,0 ,Fish                                                                            
1   ,2016-245,09:36:25,JJD,2016-245,17:36:29,JJD,239-1226,FSHCNT      ,1,1598  , 37.68,   29.1876550,  -91.6213599,  0.00,  0.00,  0.00,30  ,30  ,0 ,Fish                                                                            
5   ,2016-245,09:36:41,JJD,2016-245,17:36:43,JJD,239-1226,FSHCNT      ,1,1489  ,-25.80,   29.1876799,  -91.6205848,  0.00,  0.00,  0.00,30  ,30  ,0 ,Fish
7   ,2016-245,09:38:22,JJD,2016-245,17:38:36,JJD,239-1226,SIGCNT      ,1,2678  ,  6.21,   29.1850181,  -91.6229534,  0.93,  0.58,  0.67,30  ,30  ,0 ,obstn; possible fish
72  ,2016-102,17:51:57,Ale,2016-102,17:51:57,Ale,105_1604,DLRK        ,1,350, -7.77,   36.9398428,  -76.1884783,  2.26,  0.00,  0.00,60,60,0 ,contact

code - contact code (acronym)
status - accepted or rejected
size_at - size along track
size_ct - size cross track
large - False single contact, True multiple contacts
        '''
        contacts = []
        names = ['id', 'create_date', 'create_time', 'create_by', 'modify_date', 'modify_time', 'modify_by',
                 'line', 'code', 'count', 'ping', 'distance', 'lat', 'lon',
                 'height', 'width', 'length', 'size_at', 'size_ct', 'status', 'type']
        contact_path = os.path.join(pathToPVDL, 'Contact')
        if os.path.exists(contact_path):
            with open(contact_path, 'r') as f:
                for line in f.readlines():
                    items = line.split(',')
                    if len(items) == len(names):
                        dic = {names[i]:v.strip() for (i, v) in enumerate(items)}
                        dic['lat'] = float(dic['lat'])
                        dic['lon'] = float(dic['lon'])
                        dic['distance'] = float(dic['distance'])  # cross-track position?
                        dic['ping'] = int(dic['ping'])
                        dic['size_at'] = int(dic['size_at'])
                        dic['size_ct'] = int(dic['size_ct'])
                        dic['large'] = False
                        contacts.append(dic)
                    elif len(items) > len(names):
                        n = int(items[10])
                        if len(items) == 18 + 5 * n:
                            pings = []
                            for i in range(n):
                                idx = 11 + i * 5
                                ping = int(items[idx])
                                pings.append(ping)
                            ping_max = max(pings)
                            ping_min = min(pings)
                            items_ = items[:10] + items[-11:]
                            dic = {names[i]:v.strip() for (i, v) in enumerate(items_)}
                            dic['lat'] = float(dic['lat'])
                            dic['lon'] = float(dic['lon'])
                            dic['distance'] = 0.0  # cross-track position?
                            dic['ping'] = int((ping_max + ping_min)/2)
                            dic['size_at'] = int((ping_max - ping_min)/2) + 100
                            dic['size_ct'] = -1
                            dic['large'] = True
                            contacts.append(dic)
        return contacts


def Dump(pth, dtype="Navigation"):
    if dtype in HDCSNav.dtypes:
        h = HDCSNav(dtype)
    elif dtype in HDCSAttitude.dtypes:
        h = HDCSAttitude(dtype)
    o = h.ReadTimeSeries(pth, bVerbose=True)
    numpy.set_printoptions(precision=3, suppress=True, threshold=20, formatter={'float': lambda x: '%.3f' % x})
    print(o[0])
    print(o[1])
    numpy.set_printoptions()
