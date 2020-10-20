import os
from sets import Set
import tempfile
import datetime
import enum
from ConfigParser import ConfigParser

import scipy
from scipy import concatenate, argsort, mean
from win32api import ShellExecute, GetComputerName, GetVersionEx

from HSTB.shared import Constants
_dHSTP = Constants.UseDebug()  # Control debug stuff (=0 to hide debug menu et al from users in the field)
if not _dHSTP:
    # disable warnings; e.g.,
    # C:\Python23\Pydro\HDCSio.py:20: FutureWarning: x<<y losing bits or changing sign will return a long in Python 2.4 and up
    #  DEPTH_REJECTED_MASK = 1 << 31   # == PD_DEPTH_REJECTED_MASK == OD_DEPTH_REJECTED_MASK
    # C:\Python23\Pydro\HDCSio.py:25: FutureWarning: hex()/oct() of negative int will return a signed string in Python 2.4 and up
    #  DEPTH_REJECTED_MASK_0xX = hex(DEPTH_REJECTED_MASK)[:3]
    # C:\Python23\Pydro\HDCSio.py:26: FutureWarning: hex()/oct() of negative int will return a signed string in Python 2.4 and up
    #  PDEPTH_REJECTED_MASK_0xXXX = hex(PDEPTH_REJECTED_MASK)[:5]
    # C:\Python23\Pydro\HDCSio.py:27: FutureWarning: hex()/oct() of negative int will return a signed string in Python 2.4 and up
    #  ODEPTH_REJECTED_MASK_0xXXX = hex(ODEPTH_REJECTED_MASK)[:5]
    def _theevilunwarner(*args, **kwargs):
        pass
    import warnings
    warnings.warn = _theevilunwarner
    warnings.warn_explicit = _theevilunwarner

from HSTB.shared.Cookbook import SortBy, XMLDocument, ydhms_mjd
from HSTB.shared.RegistryHelpers import GetPathFromRegistry, SavePathToRegistry
from HSTPBin import PyPeekXTF
from HSTPBin.PyMidTierPeek import CNavPos, CNavArray, CSwathBoundsArray
from HSTB.drivers import par
from .helpers import *
from HSTB.time import UTC

PathToApp = os.getcwd() + "\\"


def InitLicenseHDCS():
    if not PyPeekXTF.GetEnvironment('HDCS_DATA_PATH', "")[0]:
        PyPeekXTF.SetEnvironment('HDCS_DATA_PATH', PathToApp[:-1])
    if not PyPeekXTF.GetEnvironment('uslXhasp_key', "")[0]:
        PyPeekXTF.SetEnvironment('uslXhasp_key', PathToApp[:-1] + "\\BSBfiles\\loc_key.dat")
    tempdir = tempfile.gettempdir()
    if not PyPeekXTF.GetEnvironment('uslXscratch', "")[0]:
        PyPeekXTF.SetEnvironment('uslXscratch', tempdir)
    if not PyPeekXTF.GetEnvironment('PyTempPath', "")[0]:
        PyPeekXTF.SetEnvironment('PyTempPath', tempdir)
    pathToDatumfile = PathToApp[:-1] + "\\BSBfiles\\datum.dat"
    pathToMapDeffile = PathToApp[:-1] + "\\BSBfiles\\MapDef.dat"
    if not PyPeekXTF.GetEnvironment('uslXdatum', "")[0]:
        PyPeekXTF.SetEnvironment('uslXdatum', pathToDatumfile)
    if not PyPeekXTF.GetEnvironment('pyDatum_Dat', "")[0]:
        PyPeekXTF.SetEnvironment('pyDatum_Dat', pathToDatumfile)
    if not PyPeekXTF.GetEnvironment('pyMapDef_Dat', "")[0]:
        PyPeekXTF.SetEnvironment('pyMapDef_Dat', pathToMapDeffile)
    sLic = PyPeekXTF.InitLicense()
    if PyPeekXTF.IsLicensed():
        bHaveLicense, sWarning = True, ""
        sLicInfo = "License: " + sLic + "   exp:" + PyPeekXTF.GetExpiry(sLic, "")[1]
        if not PyPeekXTF.HDCSInit():
            bHaveLicense, sWarning = False, "HDCS not initialized correctly\n%s" % sLicInfo
        # try:  # write it to registry so HydroMI can see the license string
        #    SavePathToRegistry("License", sLic, bLocalMachine=0)
        #    SavePathToRegistry("License", sLic, bLocalMachine=1)
        # except:
        #    pass
    else:
        bHaveLicense, sWarning = DoubleCheckHDCSioLicense()
    return bHaveLicense, sWarning


def DoubleCheckHDCSioLicense():
    sWarning = ""
    for bLM in xrange(2):  # check both local machine and current user and see if either works
        bHaveLicense, sLic = False, ""
        try:
            sLic = GetPathFromRegistry("License", "", bLocalMachine=bLM)
            PyPeekXTF.SetLicense(sLic)
            if PyPeekXTF.IsLicensed():
                bHaveLicense, sWarning = True, ""
                sLicInfo = "License: " + sLic + "   exp:" + PyPeekXTF.GetExpiry(sLic, "")[1]
                if not PyPeekXTF.HDCSInit():
                    bHaveLicense, sWarning = True, "HDCS not initialized correctly\n%s" % sLicInfo
                break
            else:
                sWarning = "Your HSTP license is invalid or expired"
        except:  # registry key didn't exist
            pass
    return bHaveLicense, sWarning


def EmailLicenseRequest(event=None):
    strAddress = 'mailto:barry.gallagher@noaa.gov?&cc=jack.riley@noaa.gov,barry.gallagher@noaa.gov&subject=Pydro License Request (v%s)&body=' % Constants.PydroVersion()
    strBody = PyPeekXTF.GetMacAddress("")[1].upper() + ',' + GetComputerName() + '%0A' + str(GetVersionEx())
    ShellExecute(0, 'open', strAddress + strBody, None, "", 1)


def GetLicenseCredentials():
    mac = PyPeekXTF.GetMacAddress("")[1]
    sLic = GetPathFromRegistry("License", "", bLocalMachine=1)
    if not sLic:  # user didn't have permissions to write into local machine registry -- check the current user.
        sLic = GetPathFromRegistry("License", "", bLocalMachine=0)
    return mac, sLic


def UpdateLicense(sLic):
    sNotices, sWarning = [], ""
    if sLic:
        try:
            SavePathToRegistry("License", sLic, bLocalMachine=0)
        except WindowsError:
            sNotice = ("You do not have sufficient privileges to store/update the Pydro license string \n" +
                       "in the windows registry (HKEY_CURRENT_USER/SOFTWARE/Tranya/Pydro/License). \n" +
                       "\n" +
                       "Pydro is fully functional during your processing session, provided the \n" +
                       "license string you entered is valid.  However, the next time you (re)start \n" +
                       "Pydro you are required to repeat the same license string update process. \n" +
                       "Contact your administrator to update the Pydro license string in the registry. ",)[0]
            sNotices.append(sNotice)
        try:
            SavePathToRegistry("License", sLic, bLocalMachine=1)
        except WindowsError:
            sNotice = ("You do not have sufficient privileges to update the Pydro license string for all users, \n" +
                       "ONLY the CURRENT user is licensed to run Pydro.  IF it is desired that all users be \n" +
                       "able to use Pydro on this machine without having to register the license individually, \n" +
                       "run Pydro with Admin rights and update the license string again sometime. " +
                       "(HKEY_LOCAL_MACHINE/SOFTWARE/Tranya/Pydro/License)",)[0]
            sNotices.append(sNotice)
        PyPeekXTF.SetLicense(sLic)
        if PyPeekXTF.IsLicensed():
            exp = PyPeekXTF.GetExpiry(sLic, "")[1]
            if exp:
                sNotices.append("Your HSTP license expires in " + exp)
            if not PyPeekXTF.HDCSInit():  # moot if license-free DLL used; otherwise, means not licensed to use HIPS I/O
                sWarning = "Your HIPS key was not found or is expired"
    return sNotices, sWarning


def GetUTCGPSLeapseconds(year, doy):
    try:
        leapseconds = PyPeekXTF.TmGetTAIUTCOffset(year, doy) - PyPeekXTF.TmGetTAIUTCOffset(1980, 1)
    except:
        leapseconds = int(UTC.PyTmYDStoUTCs80(year, doy, 0) - 86400. * (sum(ydhms_mjd(year, doy, 0, 0, 0)) - sum(ydhms_mjd(1980, 1, 0, 0, 0))))
    if leapseconds == 15 and (year > 2012 or (year == 2012 and doy > 182)):
        leapseconds = 16  # to bridge to next HIPS I/O update
    return leapseconds


def GetWGridInfo(pathtowgridbase, bPrintErr=True):
    # todo: .csar
    utmzone, utmhemi, res, surfattrs = None, None, None, None
    pathtowgridbaseFile, pathtowgridbaseExt = os.path.splitext(pathtowgridbase)
    # get UTM hemisphere & zone from .xml or .fsh
    if pathtowgridbaseExt.lower() == '.hns' and os.path.exists(pathtowgridbaseFile + '.xml'):  # if BASE try to use .xml metadata first...
        xmlmetadata = XMLDocument()
        xmlmetadata = xmlmetadata.parse(pathtowgridbaseFile + '.xml')
        for coordSysElem in xmlmetadata.getAll("CoordinateSystem"):
            try:  # SystemString="NEMR,NA83,UM,0,0,0,500000,0.9996,0,-123,0": -123 is central meridian (for utmzone); unsure of false northing (for utmhemi)
                utmzone = (180 + int(coordSysElem["SystemString"].split(',')[-2])) / 6 + 1
                if 1 <= utmzone and utmzone <= 60:
                    utmhemi = "N"  # todo: use false northing, 0->'N', 10000000->'S' (UM assumed)
                else:
                    utmzone = None
            except:
                utmzone = None
        if not res:
            for resolutionElem in xmlmetadata.getAll("Resolution"):
                try:
                    res = float(resolutionElem["value"])
                except:
                    res = None
    elif pathtowgridbaseExt.lower() == '.csar':
        try:
            f = open(pathtowgridbase, 'rb')
            d = f.read()
            utmhemi = d.split('UTM-')[1].split('-')[0]
            utmzone, utmhemi = int(utmhemi[:-1]), utmhemi[-1]
        except:
            pass
    try:
        surfattrs = PyPeekXTF.GetSurfaceAttributes(pathtowgridbase)[:-1]
        if not res and utmzone:
            if 'Depth' in surfattrs:
                surfattr = 'Depth'
            else:
                surfattr = surfattrs[0]
            temp = PyPeekXTF.CHDCSSurfaceReader(pathtowgridbase, surfattr, utmzone)
            res = temp.GetResolutionX()
            del temp
    except:
        pass
    if not utmzone:  # or otherwise no/not BASE .xml from above, go to fieldsheet .fsh for metadata...
        pf2 = pathtowgridbase.replace('\\', '/').rfind('/')
        pf1 = pathtowgridbase.replace('\\', '/')[:pf2].rfind('/')
        pathtofshfile = pathtowgridbase[:pf2] + pathtowgridbase[pf1:pf2] + '.fsh'
        fshmetadata = ConfigParser()
        try:    # .fsh files have some nonWin .ini-based formatting that we don't care to hear about...
            fshmetadata.readfp(open(pathtofshfile))
        except:
            pass
        try:    # ...but, we care about be able to parse the COORDINATESYSTEMKEY...
            projstr = fshmetadata.get('SHEET POSITION', 'COORDINATESYSTEMKEY').split('-')[1]    # e.g. COORDINATESYSTEMKEY =='UTM-18N' or 'UTM-18N-Nad83'
            utmzone, utmhemi = int(projstr[:-1]), projstr[-1:]
        except:
            pass
    if not res:  # or otherwise no/not BASE .xml from above, go to .def for metadata...
        defmetadata = ConfigParser()
        try:    # in case .def files have some nonWin .ini-based formatting that we don't care to hear about...
            defmetadata.readfp(open(pathtowgridbaseFile + '.def'))
        except:
            pass
        try:
            res = float(defmetadata.get('PARAMETERS', 'RESOLUTION'))
        except:
            pass
    if not surfattrs:
        surfattrs = ['Depth', ]
    if bPrintErr:
        if not (utmzone and utmhemi):
            print "Failed to parse geodetic projection from .xml and .fsh file.\n(%s and %s)" % (pathtowgridbaseFile + '.xml', pathtofshfile)
        if not res:
            print "Failed to parse grid resolution from .xml and .def file.\n(%s and %s)" % (pathtowgridbaseFile + '.xml', pathtowgridbaseFile + '.def')
    return (utmzone, utmhemi, res, surfattrs)


HDCSFILEGROUPS = {'NAV': ['Navigation', 'SSSNavigation', 'EventMk'],  # 'SOW'
                  'ATTITUDE': ['Gyro', 'Heave', 'TrueHeave', 'Pitch', 'Roll', 'Tide', 'TideError', 'GPSHeight', 'GPSTide', 'SSSGyro'],  # 'DeltaDraft','SSSSensorDepth','SSSSensorHeight','SSSCableOut'
                  'BATHY': ['SLRange', 'ObservedDepths', 'ProcessedDepths'],  # 'TPE'
                  'IMAGERY': ['SSSSideScan', 'SSSProcessedSideScan']}  # ,'SOUNDSPEED':['SSP','SVP']}
ACTIVEHDCSFILEGROUPS = []
for hdcsfiletype in HDCSFILEGROUPS.values():
    ACTIVEHDCSFILEGROUPS += hdcsfiletype
for excludeFType in ['ProcessedDepths', 'SSSSideScan', 'SSSProcessedSideScan']:
    ACTIVEHDCSFILEGROUPS.remove(excludeFType)
HDCSFILEUNITS = {"[degrees]": Set(('Gyro', 'Pitch', 'Roll', 'SSSGyro')),
                 "[meters]": Set(('Heave', 'TrueHeave', 'DeltaDraft', 'Tide', 'TideError', 'GPSTide', 'GPSHeight', 'SSSCableOut'))}
ADJSENSORFTYPES = HDCSFILEGROUPS['ATTITUDE']
ADJTIMESFTYPES = HDCSFILEGROUPS['ATTITUDE'] + HDCSFILEGROUPS['NAV'] + HDCSFILEGROUPS['BATHY']
for excludeFType in ['ProcessedDepths', 'Tide', 'TideError', 'GPSTide']:  # exclude time adjustability list for types where it does not make sense or otherwise is dangerous
    ADJTIMESFTYPES.remove(excludeFType)

RAD2DEG = Constants.RAD2DEG()
QUA3_STATUS = PyPeekXTF.OD_DEPTH_QUALITY_0_MASK + PyPeekXTF.OD_DEPTH_QUALITY_1_MASK


def isREC_STATUS_REJECTED(status):
    return bool(long(status) & 1L << 31)


DEPTH_REJECTED_MASK = 1L << 31   # == PD_DEPTH_REJECTED_MASK == OD_DEPTH_REJECTED_MASK == 2147483648L; todo: signed in 32-bit Python 2.4+
REJECTED_DEPTH_MASK = float(PyPeekXTF.PD_DEPTH_REJECTED_MASK)  # signed per C macro ((1L)<<31) == -2147483648 (not in Pydro64)
REJECTED_TYPE_MASK1 = 1L << 30   # == PD_DEPTH_REJECTED_BY_HYDROG_MASK == OD_DEPTH_REJECTED_BY_SWATHED_MASK
REJECTED_TYPE_MASK2 = 1L << 22   # == OD_DEPTH_REJECTED_BY_HYDROG_MASK (== PD_DEPTH_QUALITY_1_MASK)
PDEPTH_REJECTED_MASK = DEPTH_REJECTED_MASK | REJECTED_TYPE_MASK1    # ProcessedDepth rejected-by-hydrographer
ODEPTH_REJECTED_MASK = PDEPTH_REJECTED_MASK | REJECTED_TYPE_MASK2   # ObservedDepth rejected-by-hydrographer
DEPTH_REJECTED_MASK_0xX = hex(DEPTH_REJECTED_MASK)[:3]
PDEPTH_REJECTED_MASK_0xXXX = hex(PDEPTH_REJECTED_MASK)[:5]
ODEPTH_REJECTED_MASK_0xXXX = hex(ODEPTH_REJECTED_MASK)[:5]
PDEPTH_UNREJECT_MASK_0xXXX = hex(int(PDEPTH_REJECTED_MASK_0xXXX, 16) ^ int('0xfff', 16))
ODEPTH_UNREJECT_MASK_0xXXX = hex(int(ODEPTH_REJECTED_MASK_0xXXX, 16) ^ int('0xfff', 16))
REJECTED_NAV_MASK = float(PyPeekXTF.NAV_REJECTED_MASK)
BRK_INTERPOLATE_NAV_MASK = float(PyPeekXTF.NAV_BLOCK_INTERP_MASK)
REJ_INTERPOLATE_GYRO_STATUS = float(PyPeekXTF.GYRO_REJECTED_MASK | PyPeekXTF.GYRO_REJECTED_BY_HYDROG_MASK)


class ConfirmOpen:
    '''Swig 1.3.17 (at least) has a function "t_output_helper" that changes reference or pointer output variables into
    a tuple to be returned.  Problem is that it will eat an opening NULL pointer return assuming, I guess, that the function was
    really trying to return void.  Unfortunately we want our null pointer and return code form the Caris open functions'''

    def __init__(self, OrigFunc):
        self.OFunct = OrigFunc

    def __call__(self, *args):
        ret = self.OFunct(*args)
        try:
            if len(ret) == 2:
                pass  # good return (hopefully valid at least) of file pointer and rcode
        except TypeError:
            # Only received an int back (rcode) and the file pointer was eaten by SWIG
            ret = [None, ret]
        return ret


class HDCSdata:
    def __init__(self):
        # logfile (plain text) interface was removed in hipsio 9
        # Leave Stubs here in case we start writing to the logfile.xml in the future
        # self.OpenLog = PyPeekXTF.LogFileOpen
        # self.OpenLog = ConfirmOpen(self.OpenLog)
        self.OpenLog = lambda pth, mode: None, False

        # self.Log = PyPeekXTF.LogFileAppendText
        self.Log = lambda handle, txt: None
        # self.CloseLog = PyPeekXTF.LogFileClose
        self.CloseLog = lambda handle: None

    def SetHDCS_DATA_PATH(self, hdcsdatapath):
        if hdcsdatapath:
            PyPeekXTF.SetEnvironment('HDCS_DATA_PATH', hdcsdatapath)
            rcode = PyPeekXTF.HDCSInit()
        else:
            rcode = None
        return rcode


sample_HDCS_SQLite_record = '''
>>> con = lite.connect(r'E:\Data\Kongsberg\H12786_Central_Chesapeake_Bay\H12786_Central_Chesapeake_Bay.hips')
>>> cur = con.cursor()

#find tables
>>> cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
[(u'simpleFeatureVersion',), (u'dataset',), (u'sqlite_sequence',), (u'attribute',), (u'attributeExpectedValue',),
 (u'object',), (u'concreteObject',), (u'concreteAttribute',), (u'objectState',), (u'objectAttribute',),
 (u'catalogModTime',), (u'pdIndex',), (u'pdIndex_node',), (u'pdIndex_rowid',), (u'pdIndex_parent',),
 (u'lineIndex',), (u'lineIndex_node',), (u'lineIndex_rowid',), (u'lineIndex_parent',), (u'editset',),
 (u'masterEditset',), (u'hipsProjectVersion',), (u'sqlite_stat1',), (u'CSAR_MASTER',), (u'CSAR_MORTON',),
 (u'CSAR_MORTON_SEQ',), (u'CSAR_CTSCHEMA',), (u'CSAR_CTSCHEMA_SEQ',), (u'CSAR_CT1_SEQ',), (u'CSAR_CT1',),
 (u'CSAR_CT2_SEQ',), (u'CSAR_CT2',), (u'CSAR_CT3_SEQ',), (u'CSAR_CT3',)]

#find columns
>>> cur.execute("SELECT * FROM concreteAttribute")
>>> cur.description
(('concreteObjectId', None, None, None, None, None, None), ('attributeId', None, None, None, None, None, None), ('integerValue', None, None, None, None, None, None), ('floatValue', None, None, None, None, None, None), ('stringValue', None, None, None, None, None, None), ('sequenceNumber', None, None, None, None, None, None))

#Get a record
>>> cur.execute("SELECT * FROM concreteAttribute WHERE attributeId=17")
>>> rows = cur.fetchall()
>>> print rows[0]

<?xml version="1.0"?>
<Dictionary>
    <Composite Name="sources">
        <Composite Name="Converter">
            <Element Name="Name" Type="string">Simrad</Element>
            <Composite Name="Metadata"/>
            <Composite Name="Sources">
                <Composite Name="Source">
                    <Element Name="Path" Type="string">R:\\2015_Raw\\H12786-Central_Chesapeake_Bay\\MBES\\H12786_DN154\\0000_20150603_135615_S5401.all</Element>
                    <Composite Name="Metadata">
                        <Composite Name="DatagramSources">
                            <Element Name="Navigation" Type="string">Simrad.EM 3000 Position 1</Element>
                        </Composite>
                    </Composite>
                </Composite>
            </Composite>
        </Composite>
        <Composite Name="Converter">
            <Element Name="Name" Type="string">HDCS</Element>
            <Composite Name="Metadata"/>
            <Composite Name="Sources">
                <Composite Name="Source">
                    <Element Name="Path" Type="string">P:\\HDCS_Data\\H12786_Central_Chesapeake_Bay\\2015_BHII_S5401_EM2040_kRP\\2015-154\\0000_20150603_135615_S5401</Element>
                    <Composite Name="Metadata"/>
                </Composite>
            </Composite>
        </Composite>
        <Composite Name="Converter">
            <Element Name="Name" Type="string">POSDIRECT</Element>
            <Composite Name="Metadata"/>
            <Composite Name="Sources">
                <Composite Name="Source">
                    <Element Name="Path" Type="string">R:\\2015_Raw\\H12786-Central_Chesapeake_Bay\\POS\\POSPac_H12674_DN154.000</Element>
                    <Composite Name="Metadata">
                        <Element Name="TimeReference" Type="double">1117497600</Element>
                        <Element Name="TimeOffset" Type="double">0</Element>
                        <Composite Name="DatagramSources">
                            <Element Name="DelayedHeave" Type="string">Applanix.ApplanixGroup111</Element>
                            <Element Name="DelayedHeaveRMS" Type="string">Applanix.ApplanixGroup111</Element>
                            <Element Name="DelayedHeave" Type="string">Applanix.ApplanixGroup111</Element>
                            <Element Name="DelayedHeaveRMS" Type="string">Applanix.ApplanixGroup111</Element>
                        </Composite>
                    </Composite>
                </Composite>
            </Composite>
        </Composite>
    </Composite>
</Dictionary>

#pull the xml string into a DOM object
>>> from xml.dom import minidom
>>> dom=minidom.parseString(rows[0][4])

#Find the navigation element
>>> for e in dom.getElementsByTagName("Element"):
...     print e.attributes.items()
...     if e.getAttribute('Name') == "Navigation": break

#go up from the navigation element to element that would hold the path element
>>> c = e.parentNode.parentNode.parentNode
>>> c.attributes.items()
[(u'Name', u'Source')]
>>> for i in c.childNodes:
...     print i.attributes.items()
...
[(u'Type', u'string'), (u'Name', u'Path')]
[(u'Name', u'Metadata')]

#find the path element and the filename is in the nodeValue of the textElement child.
>>> p=c.childNodes[0]
>>> p.attributes.items()
[(u'Type', u'string'), (u'Name', u'Path')]
>>> p.childNodes
[<DOM Text node "u'R:\\2015_Ra'...">]
>>> p.childNodes[0].nodeValue
u'R:\\2015_Raw\\H12786-Central_Chesapeake_Bay\\MBES\\H12786_DN154\\0000_20150603_135615_S5401.all'

>>> fname=p.childNodes[0].nodeValue
>>> fname
u'R:\\2015_Raw\\H12786-Central_Chesapeake_Bay\\MBES\\H12786_DN154\\0000_20150603_135615_S5401.all'
>>> fname = u'E:\\Data\\Kongsberg\\H12786_DN154_RawData\\0000_20150603_135615_S5401.all'

>>> import par
>>> all = par.useall(fname)
#show POSIX time, lon, lat for first ten points.
>>> all.navarray['80'][:10]
array([[  1.43333978e+09,  -7.63426740e+01,   3.81784842e+01],
       [  1.43333978e+09,  -7.63426723e+01,   3.81784822e+01],
       [  1.43333978e+09,  -7.63426708e+01,   3.81784800e+01],
       [  1.43333978e+09,  -7.63426693e+01,   3.81784780e+01],
       [  1.43333978e+09,  -7.63426678e+01,   3.81784758e+01],
       [  1.43333978e+09,  -7.63426663e+01,   3.81784738e+01],
       [  1.43333978e+09,  -7.63426650e+01,   3.81784716e+01],
       [  1.43333978e+09,  -7.63426636e+01,   3.81784695e+01],
       [  1.43333978e+09,  -7.63426625e+01,   3.81784673e+01],
       [  1.43333978e+09,  -7.63426613e+01,   3.81784652e+01]])
>>> datetime.datetime.fromtimestamp(all.navarray['80'][0][0])
datetime.datetime(2015, 6, 3, 9, 56, 15, 322000)
>>> datetime.datetime.utcfromtimestamp(1.43333978e+09)
datetime.datetime(2015, 6, 3, 13, 56, 20)


>>> cur.execute("SELECT * FROM masterEditset")
<sqlite3.Cursor object at 0x0000000003E6BC00>
>>> cur.description
(('id', None, None, None, None, None, None), ('lineId', None, None, None, None, None, None), ('type', None, None, None, None, None, None), ('source', None, None, None, None, None, None), ('state', None, None, None, None, None, None), ('startTime', None, None, None, None, None, None), ('endTime', None, None, None, None, None, None))
>>> rows = cur.execute("SELECT * FROM masterEditset WHERE linId = %d"%lineIdNumber).fetchall()
Traceback (most recent call last):
  File "<interactive input>", line 1, in <module>
OperationalError: no such column: linId
>>> rows = cur.execute("SELECT * FROM masterEditset WHERE lineId = 9").fetchall()
>>> rows
[(1, 9, u'Navigation', u'Applanix.SBET', -1610612736, 986745275.5110719, 986745290.7106789), (2, 9, u'Navigation', u'Applanix.SBET', -1073741824, 986745344.8792827, 986745387.6381781)]

'''


def PosixToUTCs80(posix_time):
    dt = datetime.datetime.utcfromtimestamp(posix_time)
    jd = UTC.PyTmYMDtoJD(dt.year, dt.month, dt.day)
    sec = UTC.PyTmHMSXtoS(dt.hour, dt.minute, dt.second, dt.microsecond / 1000000.0)
    return UTC.PyTmYDStoUTCs80(dt.year, jd, sec)


class DirectNav(HDCSdata):
    concreteAttributeEnum = enum.IntEnum("concreteObjectColumns", (('concreteObjectId', 0), ('attributeId', 1), ('integerValue', 2), ('floatValue', 3), ('stringValue', 4)))
    masterEditsetEnum = enum.IntEnum("masterEditsetColumns", (('id', 0), ('lineId', 1), ('type', 2), ('source', 3), ('state', 4), ('startTime', 5), ('endTime', 6)))

    def __init__(self, pathToHipsDatabase):
        '''(hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)'''
        import sqlite3 as lite
        from xml.dom import minidom
        ME = self.masterEditsetEnum
        CA = self.concreteAttributeEnum
        self.dictObjId = {}
        self.pathToHipsDatabase = pathToHipsDatabase
        if os.path.exists(pathToHipsDatabase):
            with lite.connect(pathToHipsDatabase) as con:
                cur = con.cursor()
                self.table_names = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

                # iterate all the records rleated to Navigation data
                rows = cur.execute("SELECT * FROM concreteAttribute WHERE attributeId=17").fetchall()
                for row in rows:
                    objId = row[CA.concreteObjectId]
                    self.dictObjId[objId] = {}
                    dom = minidom.parseString(row[CA.stringValue])  # string value holds an XML dataset describing raw data files and which HDCS line it relates to

                    # Find the navigation element which specifies the dataset name used in other records
                    for e in dom.getElementsByTagName("Element"):
                        if e.getAttribute('Name') == "Navigation":
                            self.dictObjId[objId]['DataName'] = e.childNodes[0].nodeValue
                            dataname = e.childNodes[0].nodeValue
                            break
                        else:
                            e = None

                    # go up from the navigation element to element that would hold the path element which specifies the raw data file location
                    source_element = e.parentNode.parentNode.parentNode
                    source_element.attributes.items()  # [(u'Name', u'Source')]
                    for child in source_element.childNodes:
                        for attr in child.attributes.items():
                            if attr[0] == 'Name' and attr[1] == 'Path':
                                path_element = child
                                self.dictObjId[objId]['RawPath'] = str(path_element.childNodes[0].nodeValue)
                                self.dictObjId[objId][dataname] = str(path_element.childNodes[0].nodeValue)

                    # Now find the HDCS line path for this record
                    for e in dom.getElementsByTagName("Element"):
                        if e.getAttribute('Name') == "Name":
                            try:
                                if str(e.childNodes[0].nodeValue) == 'HDCS':
                                    break
                            except:
                                e = None
                        else:
                            e = None
                    if e:
                        for hdcs_converter_child in e.parentNode.childNodes:
                            if hdcs_converter_child.getAttribute('Name') == "Sources":
                                for sources_child in hdcs_converter_child.childNodes:
                                    if sources_child.getAttribute('Name') == "Source":
                                        for source_child in sources_child.childNodes:
                                            if source_child.getAttribute('Name') == "Path":
                                                self.dictObjId[objId]['HDCSPath'] = str(source_child.childNodes[0].nodeValue)

                    # find the edits to Nav if any
                    rows = cur.execute("SELECT * FROM masterEditset WHERE lineId = %d" % objId).fetchall()
                    self.dictObjId[objId]['edits'] = {}
                    for row in rows:
                        self.dictObjId[objId]['edits'].setdefault(row[ME.source], {})[row[ME.id]] = (row[ME.startTime], row[ME.endTime])

                rows = cur.execute("SELECT * FROM concreteAttribute WHERE attributeId=18").fetchall()
                for row in rows:
                    self.dictObjId[row[CA.concreteObjectId]]['ActiveNav'] = row[CA.stringValue]
                # print self.dictObjId

        else:
            raise Exception("File Not Found " + pathToHipsDatabase)

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, oddFactorSkip=1, bOnlyAccepted=False):
        # Returns HDCS navigation data time series in N x 5 NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, lat, lon, accuracy, status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        fname = None
        for id, obj in self.dictObjId.items():
            objHDCSPath = obj.get('HDCSPath', '')
            if objHDCSPath:
                if objHDCSPath.replace("/", "\\").lower() == pathToPVDL.replace("/", "\\").lower():
                    fname = obj['RawPath']
                    break
            else:  # Caris changed to no longer use HDCSPath in <projDB>.hips in 9.x+?
                objRawPath = obj.get('RawPath', '')
                if os.path.splitext(os.path.basename(objRawPath))[0].lower() == os.path.basename(pathToPVDL).lower():
                    fname = objRawPath
                    break
        # fname =  r'E:\Data\Kongsberg\H12786_DN154_RawData\0000_20150603_135615_S5401.all'
        # fname = r'E:\Data\CARIS\DirectNav\0012_20160407_171718_NancyFoster.all'
        # print 'changed rawpath to ', fname
        if fname:
            print pathToPVDL, "using nav from", fname
            all = par.useall(fname, verbose=False)
            nav = all.navarray['80']
            # apply edits
            for k, (starttime, endtime) in obj['edits']:
                nav = scipy.compress(scipy.logical_or(nav[:, 0] < starttime, nav[:, 0] > endtime), nav, axis=0)

            if bVerbose:
                verboseData = {'summaryStatus': None, 'sourceFileName': None}
            (numRecords, minTime, maxTime, minLat, maxLat, minLon, maxLon) = (len(nav[:, 1]), min(nav[:, 0]), max(nav[:, 0]), min(nav[:, 2]), max(nav[:, 2]), min(nav[:, 1]), max(nav[:, 1]))
            minTime = PosixToUTCs80(minTime)
            maxTime = PosixToUTCs80(maxTime)
            if bVerbose:
                verboseData['summaryStatus'] = ZERO_STATUS
                # ReadLineSummary for sourceFileName (note reread of numRecords)
                verboseData['sourceFileName'] = fname
            NumPyArray = scipy.zeros((numRecords, 5), scipy.float64)
            rcodeCaris, accuracy, status = 0, 0, 0
            for recordNum in xrange(numRecords):
                (posix_time, longitude, latitude) = nav[recordNum]
                tyme = PosixToUTCs80(posix_time)

                NumPyArray[recordNum] = [tyme, latitude * Constants.DEG2RAD(), longitude * Constants.DEG2RAD(), accuracy, status]
            if oddFactorSkip > 1:
                oddFactorSkip = int(oddFactorSkip)
                if not oddFactorSkip % 2:
                    oddFactorSkip += 1
                NumPyArray = NumPyArray[oddFactorSkip / 2:len(NumPyArray) - oddFactorSkip / 2:oddFactorSkip]
            if bVerbose:
                return NumPyArray, verboseData
            else:
                return NumPyArray
        else:
            print 'did not find nav file for', pathToPVDL

    def WriteTimeSeries(self, pathToPVDL, NumPyArray, verboseData=None, sourcename='', sourceTypeExt='', haveaccuracy=(1, None), havestatus=(1, None), sortBytime=True):
        raise Exception("DirectReadNav does not support writing")


class HDCSNav(HDCSdata):
    def __init__(self, ftype):
        if ftype in ('Navigation', 'SSSNavigation'):
            self.ftype = ftype
            self.Open = getattr(PyPeekXTF, "%sOpenDir" % ftype)
            self.Open = ConfirmOpen(self.Open)
            self.ReadSummary = getattr(PyPeekXTF, "%sSummary" % ftype)
            self.ReadLineSummary = getattr(PyPeekXTF, "%sLineSegment" % ftype)
            self.Read = getattr(PyPeekXTF, "%sReadSeq" % ftype)
            self.SetStatus = getattr(PyPeekXTF, "%sSetSummaryStatus" % ftype)  # not needed for sequential write mode; done via WriteSummary
            self.BeginWrite = getattr(PyPeekXTF, "%sBgnSeqWriteLineSegment" % ftype)
            self.Write = getattr(PyPeekXTF, "%sSeqWrite" % ftype)
            self.EndWrite = getattr(PyPeekXTF, "%sEndSeqWriteLineSegment" % ftype)
            self.WriteSummary = getattr(PyPeekXTF, "%sEndSeqWriteSummary" % ftype)
            self.Close = getattr(PyPeekXTF, "%sClose" % ftype)
        else:
            self.ftype = None

    def GetSpatiotemporalBounds(self, pathToPVDL):
        minTime, maxTime, minLat, maxLat, minLon, maxLon = (0, 0, 0, 0, 0, 0)
        (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        if self.SetHDCS_DATA_PATH(hdcsdatapath):
            nav, bOK = self.Open(pathToPVDL, "query")
            if nav:
                (rcodeCaris,
                 numLineSegments, numRecords,
                 coordType,
                 minTime, maxTime,
                 minLat, maxLat, minLon, maxLon,
                 summaryStatus) = self.ReadSummary(nav)
            else:  # try DirectNav
                if True:  # try:
                    dnav = DirectNav(os.sep.join((hdcsdatapath, proj, proj + '.hips')))
                    NumPyArray = dnav.ReadTimeSeries(pathToPVDL)
                    minTime, minLat, minLon = [NumPyArray[:, c].min() for c in (0, 1, 2)]
                    maxTime, maxLat, maxLon = [NumPyArray[:, c].max() for c in (0, 1, 2)]
                else:  # except:
                    pass
        return (minTime, maxTime, minLat, maxLat, minLon, maxLon)

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, oddFactorSkip=1, bOnlyAccepted=False):
        # Returns HDCS navigation data time series in N x 5 NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, lat, lon, accuracy, status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        bCleanup = False  # watch variable to indicate we skipped some rejected records and need to remove nulls before returning NumPyArray
        if bVerbose:
            verboseData = {'summaryStatus': None, 'sourceFileName': None}
        (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        rcode = 1
        rcodeCaris = 0    # HDCS I/O "Okay"=0
        if self.SetHDCS_DATA_PATH(hdcsdatapath):
            nav, bOK = self.Open(pathToPVDL, "query")
            if nav:
                (rcodeCaris,
                 numLineSegments, numRecords,
                 coordType,
                 minTime, maxTime,
                 minLat, maxLat, minLon, maxLon,
                 summaryStatus) = self.ReadSummary(nav)
                if rcodeCaris == 0:
                    if bVerbose:
                        verboseData['summaryStatus'] = summaryStatus
                        # ReadLineSummary for sourceFileName (note reread of numRecords)
                        (rcodeCaris,
                         sourceFileName,
                         coordType, numRecords,
                         minTime, maxTime,
                         minLat, maxLat, minLon, maxLon,
                         lineSegmentStatus) = self.ReadLineSummary(nav, 1)
                        if rcodeCaris == 0:
                            verboseData['sourceFileName'] = sourceFileName
                    NumPyArray = scipy.zeros((numRecords, 5), scipy.float64)
                    for recordNum in xrange(numRecords):
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
            NumPyArray = scipy.delete(NumPyArray, scipy.where(~NumPyArray.any(axis=1))[0], 0)
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
        numRecords = scipy.shape(NumPyArray)[0]
        numFields = scipy.shape(NumPyArray)[1]
        if (numRecords > 0) and (numFields >= fieldcount):
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            if verboseData:
                summaryStatus = verboseData['summaryStatus']
                sourcename = verboseData['sourceFileName']
            else:
                summaryStatus = PyPeekXTF.NAV_EXAMINED_BY_HYDROG_MASK
                if not sourcename:
                    sourcename = line + str(sourceTypeExt)
            rcode = 1
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                # check to see if path to P/V/D/L directory exists; create to leaf dir L, if needed
                if not os.access(pathToPVDL, os.F_OK):
                    os.makedirs(pathToPVDL)
                nav, bOK = self.Open(pathToPVDL, "create")
                if nav:
                    if rcodeCaris == 0:
                        rcodeCaris = self.BeginWrite(nav, str(sourcename))  # str() for unicode conversion
                        if rcodeCaris == 0:
                            if sortBytime:
                                sortIdx = argsort(NumPyArray[:, 0])  # Sorted NumPyArray indicies according to [increasing] time
                            for recordNum in xrange(numRecords):
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
        else:
            rcode = 0
        return rcode


class HDCSAttitude(HDCSdata):
    def __init__(self, ftype):
        if ftype in ('Gyro', 'Heave', 'TrueHeave', 'Pitch', 'Roll', 'SSSGyro', 'Tide', 'TideError', 'GPSHeight', 'GPSTide', 'DeltaDraft'):
            self.ftype = ftype
            if ftype != 'TideError':
                self.Open = getattr(PyPeekXTF, "%sOpenDir" % ftype)
                self.Open = ConfirmOpen(self.Open)
                self.ReadSummary = getattr(PyPeekXTF, "%sSummary" % ftype)
                self.ReadLineSummary = getattr(PyPeekXTF, "%sLineSegment" % ftype)
                self.Read = getattr(PyPeekXTF, "%sReadSeq" % ftype)
                self.SetStatus = getattr(PyPeekXTF, "%sSetSummaryStatus" % ftype)  # not needed for sequential write mode; done via WriteSummary
                self.BeginWrite = getattr(PyPeekXTF, "%sBgnSeqWriteLineSegment" % ftype)
                self.Write = getattr(PyPeekXTF, "%sSeqWrite" % ftype)
                self.EndWrite = getattr(PyPeekXTF, "%sEndSeqWriteLineSegment" % ftype)
                self.WriteSummary = getattr(PyPeekXTF, "%sEndSeqWriteSummary" % ftype)
                self.Close = getattr(PyPeekXTF, "%sClose" % ftype)
        else:
            self.ftype = None

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, oddFactorSkip=1, bMean=True, bOnlyAccepted=False):
        # Returns HDCS attitude data time series in N x 3 NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, sensor value, record status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        bCleanup = False  # watch variable to indicate we skipped some rejected records and need to remove nulls before returning NumPyArray
        if bVerbose:
            verboseData = {'summaryStatus': None, 'sourceFileName': None}
        (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        rcode = 1
        rcodeCaris = 0    # HDCS I/O "Okay"=0
        if self.SetHDCS_DATA_PATH(hdcsdatapath):
            if self.ftype != 'TideError':
                attitude, bOK = self.Open(pathToPVDL, "query")
                if attitude:
                    (rcodeCaris,
                     numLineSegments, numRecords,
                     minTime, maxTime,
                     minSensor, maxSensor,
                     summaryStatus) = self.ReadSummary(attitude)
                    if rcodeCaris == 0:
                        if bVerbose:
                            verboseData['summaryStatus'] = summaryStatus
                            # ReadLineSummary for sourceFileName
                            (rcodeCaris,
                             sourceFileName,
                             bgnIndex, endIndex,
                             minTime, maxTime,
                             minSensor, maxSensor,
                             lineSegmentStatus) = self.ReadLineSummary(attitude, 1)
                            if rcodeCaris == 0:
                                verboseData['sourceFileName'] = sourceFileName
                        NumPyArray = scipy.zeros((numRecords, 3), scipy.float64)
                        for recordNum in xrange(numRecords):
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
                attitude = PyPeekXTF.TideErrorFile(pathToPVDL)
                numRecords = attitude.getNumberOfRecords()
                NumPyArray = scipy.zeros((numRecords, 3), scipy.float64)
                for recordNum in xrange(numRecords):
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
                NumPyArray[:, 1] = mean(sensorvector, axis=1)
        if bCleanup:
            NumPyArray = scipy.delete(NumPyArray, scipy.where(~NumPyArray.any(axis=1))[0], 0)
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
        numRecords = scipy.shape(NumPyArray)[0]
        numFields = scipy.shape(NumPyArray)[1]
        if (numRecords > 0) and (numFields > 1):
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            if verboseData:
                summaryStatus = verboseData['summaryStatus']
                sourcename = verboseData['sourceFileName']
            else:
                summaryStatus = ZERO_STATUS
                if not sourcename:
                    sourcename = line + str(sourceTypeExt)
            rcode = 1
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                # check to see if path to P/V/D/L directory exists; create to leaf dir L, if needed
                if not os.access(pathToPVDL, os.F_OK):
                    os.makedirs(pathToPVDL)
                attitude, bOK = self.Open(pathToPVDL, "create")
                if attitude:
                    if rcodeCaris == 0:
                        if not sourcename:
                            sourcename = line + str(sourceTypeExt)
                        rcodeCaris = self.BeginWrite(attitude, str(sourcename))  # str() for unicode conversion
                        if rcodeCaris == 0:
                            if sortBytime:
                                sortIdx = argsort(NumPyArray[:, 0])  # Sorted NumPyArray indicies according to [increasing] time
                            for recordNum in xrange(numRecords):
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
        else:
            rcode = 0
        return rcode


class HDCSBathy(HDCSdata):
    def __init__(self, ftype, numBeams=None):   # no need to specify numBeams for Read* methods (currently, they return all beams)
        if ftype in ('SLRange', 'ObservedDepths', 'ProcessedDepths', 'TPE'):
            self.ftype = ftype
            self.numBeams = numBeams
            self.numProfiles = None
            self.Open = getattr(PyPeekXTF, "%sOpenDir" % ftype)
            self.Open = ConfirmOpen(self.Open)
            self.ReadSummary = getattr(PyPeekXTF, "%sSummary" % ftype)
            self.ReadLineSummary = getattr(PyPeekXTF, "%sLineSegment" % ftype)
            self.ReadProfile = getattr(PyPeekXTF, "%sReadProfileSeq" % ftype)
            self.ReadProfileIndexed = getattr(PyPeekXTF, "%sReadProfile" % ftype)
            self.SetToolType = getattr(PyPeekXTF, "%sSetToolType" % ftype)  # not needed for sequential write mode; it's in BeginWriteSummary
            self.BeginWriteProfile = getattr(PyPeekXTF, "%sBgnSeqWriteProfile" % ftype)
            self.EndWriteProfile = getattr(PyPeekXTF, "%sEndSeqWriteProfile" % ftype)
            self.Read = getattr(PyPeekXTF, "%sReadSeq" % ftype)
            self.ReadIndexed = getattr(PyPeekXTF, "%sRead" % ftype)
            self.SetStatus = getattr(PyPeekXTF, "%sSetSummaryStatus" % ftype)  # not needed for sequential write mode; done via EndWriteSummary
            self.Remove = getattr(PyPeekXTF, "%sRemoveDir" % ftype)
            self.BeginWriteLine = getattr(PyPeekXTF, "%sBgnSeqWriteLineSegment" % ftype)
            self.BeginWriteSummary = getattr(PyPeekXTF, "%sBgnSeqWriteSummary" % ftype)
            self.Write = getattr(PyPeekXTF, "%sSeqWrite" % ftype)
            self.EndWriteLine = getattr(PyPeekXTF, "%sEndSeqWriteLineSegment" % ftype)
            self.EndWriteSummary = getattr(PyPeekXTF, "%sEndSeqWriteSummary" % ftype)
            self.Close = getattr(PyPeekXTF, "%sClose" % ftype)
        else:
            self.ftype = None

    def SetNumBeams(self, numBeams):
        self.numBeams = numBeams

    def GetProfileBeamOffset(self, pathToPVDL, profNo):
        startBeam = None
        if self.ftype in ('ObservedDepths', 'ProcessedDepths', 'TPE'):
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                bathy, bOK = self.Open(pathToPVDL, "query")
                if bathy:
                    if self.ftype == 'TPE':
                        (rcodeCaris, numBeams, startBeam, proftime, pingnum,
                         summaryStatus) = self.ReadProfileIndexed(bathy, profNo)
                    else:
                        (rcodeCaris, numBeams, startBeam, proftime, xducerPitch, xducerRoll,
                         summaryStatus) = self.ReadProfileIndexed(bathy, profNo)
                    if rcodeCaris != 0:
                        startBeam = None
        return startBeam

    def GetPD(self, pathToPVDL, profNo, beamNo, hdcsTime=None):
        # hdcsTime is an extra requirment; should be supplied when profNo,beamNo address can be fooled--i.e., for Migrated DPs
        beamdata = None   # assume beam data will not be found...
        if self.ftype == 'ProcessedDepths':
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                # First try a direct indexed-based read...
                bathy, bOK = self.Open(pathToPVDL, "query")
                if bathy:
                    (rcodeCaris, numBeams, startBeam, proftime,
                     xducerLat, minLat, maxLat, xducerLon, minLon, maxLon,
                     gyro, heave, pitch, roll, tide, speed, xducerPitch, xducerRoll,
                     summaryStatus) = self.ReadProfileIndexed(bathy, profNo)
                    if rcodeCaris == 0:
                        onebasedBeamIdx = beamNo - startBeam + 1
                        if onebasedBeamIdx > 0:
                            (rcodeCaris, beamtime,
                             alongTrack, acrossTrack, lat, lon, depth,
                             accuracy, status) = self.ReadIndexed(bathy, profNo, onebasedBeamIdx)
                            if (hdcsTime != None) and (beamtime != hdcsTime):  # if matching times is important, veto rcodeCaris if beamtime bust (see comments above on parameter hdcsTime)
                                rcodeCaris = -1
                            if rcodeCaris == 0:
                                beamdata = {'depth': depth, 'lat': lat, 'lon': lon,
                                            'time': beamtime, 'tide': tide,
                                            'status': status}
                    self.Close(bathy)
                else:
                    print "Failed to open %s for ProcessedDepths query." % pathToPVDL
            else:
                print "Unable to mount %s for ProcessedDepths query." % hdcsdatapath
        if beamdata:
            beamdata['lat'] *= RAD2DEG
            beamdata['lon'] *= RAD2DEG
        return beamdata

    def GetTPU(self, pathToPVDL, profNo, beamNo, hdcsTime=None):
        # hdcsTime is an extra requirment; should be supplied when profNo,beamNo address can be fooled--i.e., for Migrated DPs
        tpedata = None   # assume beam data will not be found...
        if self.ftype == 'TPE':
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                # First try a direct indexed-based read...
                bathy, bOK = self.Open(pathToPVDL, "query")
                if bathy:
                    (rcodeCaris, numBeams, startBeam, proftime, pingnum,
                     summaryStatus) = self.ReadProfileIndexed(bathy, profNo)
                    if rcodeCaris == 0:
                        onebasedBeamIdx = beamNo - startBeam + 1
                        if onebasedBeamIdx > 0:
                            (rcodeCaris, beamtime, depthTPE, posTPE,
                             status) = self.ReadIndexed(bathy, profNo, onebasedBeamIdx)
                            if (hdcsTime != None) and (beamtime != hdcsTime):  # if matching times is important, veto rcodeCaris if beamtime bust (see comments above on parameter hdcsTime)
                                rcodeCaris = -1
                            if rcodeCaris == 0:
                                tpedata = {'TVU': depthTPE, 'THU': posTPE, 'time': beamtime, 'status': status}
                    self.Close(bathy)
                else:
                    print "Failed to open %s for TPE query." % pathToPVDL
            else:
                print "Unable to mount %s for TPE query." % hdcsdatapath
        return tpedata

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, bMiddleBeamOnly=False, oddFactorSkip=1, bUseList=False, bOnlyAccepted=False):
        # Returns HDCS bathy data time series in N x [6, unless TPE--then 4] NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, <4x beam data> or <2x TPE data>, status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        bOnlyAccepted &= bMiddleBeamOnly  # don't mess around with skipping rejected if whole swathe is involved
        bCleanup = False  # watch variable to indicate we skipped some rejected records and need to remove nulls before returning NumPyArray
        if bVerbose:
            verboseData = {'toolType': None, 'coordinateType': None,
                           'numProfiles': None, 'numDepths': None,
                           'summaryStatus': None, 'sourceFileName': None, 'profiles': []}
            profileData = verboseData['profiles']
            # profiles:
            #   SLRange/ObservedDepths = [numBeams,startbeam,ptime,pitch,roll,status]
            #   ProcessedDepths = [numBeams,startbeam,ptime,lat,lon,minlat,maxlat,minlon,maxlon,gyro,heave,pitch,roll,tide,speed,xpitch,xroll,status]
            #   TPE = [numBeams,startbeam,ptime,pingnum,status]
        (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        rcode = 1
        rcodeCaris = 0    # HDCS I/O "Okay"=0
        if self.SetHDCS_DATA_PATH(hdcsdatapath):
            bathy, bOK = self.Open(pathToPVDL, "query")
            if bathy:
                if self.ftype == 'SLRange':
                    (rcodeCaris,
                     toolType,
                     numLineSegments, numProfiles, numDepths,
                     minTime, maxTime,
                     summaryStatus) = self.ReadSummary(bathy)
                elif self.ftype == 'ObservedDepths':
                    (rcodeCaris,
                     toolType,
                     numLineSegments, numProfiles, numDepths,
                     minTime, maxTime,
                     minDepth, maxDepth,
                     summaryStatus) = self.ReadSummary(bathy)
                elif self.ftype == 'ProcessedDepths':
                    (rcodeCaris,
                     toolType, coordinateType,
                     numLineSegments, numProfiles, numDepths,
                     minTime, maxTime,
                     minDepth, maxDepth,
                     minLat, maxLat, minLon, maxLon,
                     summaryStatus) = self.ReadSummary(bathy)
                else:  # self.ftype=='TPE'
                    (rcodeCaris,
                     numLineSegments, numProfiles, numDepths,
                     minTime, maxTime,
                     toolType, coordinateType,  # aka--in CARIS API--sounderType, positionType (resp.)
                     minDepthTPE, maxDepthTPE, minPosTPE, maxPosTPE,
                     summaryStatus) = self.ReadSummary(bathy)
                if rcodeCaris == 0:
                    if bVerbose:
                        verboseData['summaryStatus'] = summaryStatus
                        verboseData['numDepths'] = numDepths
                        verboseData['numProfiles'] = numProfiles
                        verboseData['toolType'] = toolType
                        # ReadLineSummary for sourceFileName (note reread of numProfiles)
                        if self.ftype == 'SLRange':
                            (rcodeCaris,
                             sourceFileName,
                             numLineSegments, numProfiles,
                             minTime, maxTime,
                             lineSegmentStatus) = self.ReadLineSummary(bathy, 1)
                        elif self.ftype == 'ObservedDepths':
                            (rcodeCaris,
                             sourceFileName,
                             numLineSegments, numProfiles,
                             minTime, maxTime,
                             minDepth, maxDepth,
                             lineSegmentStatus) = self.ReadLineSummary(bathy, 1)
                        elif self.ftype == 'ProcessedDepths':
                            verboseData['coordinateType'] = coordinateType
                            (rcodeCaris,
                             sourceFileName,
                             numLineSegments, numProfiles,
                             minTime, maxTime,
                             minDepth, maxDepth,
                             minLat, maxLat, minLon, maxLon,
                             lineSegmentStatus) = self.ReadLineSummary(bathy, 1)
                        else:  # self.ftype=='TPE':
                            (rcodeCaris,
                             sourceFileName,
                             numLineSegments, numProfiles,
                             minTime, maxTime,
                             lineSegmentStatus) = self.ReadLineSummary(bathy, 1)
                        if rcodeCaris == 0:
                            verboseData['sourceFileName'] = sourceFileName
                    if bMiddleBeamOnly:
                        ReadBeam, ReadProfile = self.ReadIndexed, self.ReadProfileIndexed
                    else:
                        ReadBeam, ReadProfile = self.Read, self.ReadProfile
                    self.numProfiles = numProfiles
                    self.numBeams = numDepths / numProfiles
                    for profileNum in xrange(numProfiles):
                        if bMiddleBeamOnly:
                            rpargs = [bathy, profileNum + 1]
                        else:
                            rpargs = [bathy, ]
                        if self.ftype == 'ProcessedDepths':
                            (rcodeCaris,
                             numBeams, startBeam,
                             proftime,
                             xducerLat, minLat, maxLat,
                             xducerLon, minLon, maxLon,
                             gyro, heave, pitch, roll, tide, speed,
                             xducerPitch, xducerRoll,
                             profileStatus) = ReadProfile(*rpargs)
                        elif self.ftype == 'TPE':
                            (rcodeCaris,
                             numBeams, startBeam,
                             proftime, pingnum,
                             profileStatus) = ReadProfile(*rpargs)
                        else:  # self.ftype=='SLRange' or self.ftype=='ObservedDepths':
                            (rcodeCaris,
                             numBeams, startBeam,
                             proftime,
                             xducerPitch, xducerRoll,
                             profileStatus) = ReadProfile(*rpargs)
                        if rcodeCaris == 0:
                            if bVerbose:
                                if self.ftype == 'ProcessedDepths':
                                    profileData.append([numBeams, startBeam, proftime, xducerLat, minLat, maxLat, xducerLon, minLon, maxLon, gyro, heave, pitch, roll, tide, speed, xducerPitch, xducerRoll, profileStatus])
                                elif self.ftype == 'TPE':
                                    profileData.append([numBeams, startBeam, proftime, pingnum, profileStatus])
                                else:  # 'SLRange' or 'ObservedDepths'
                                    profileData.append([numBeams, startBeam, proftime, xducerPitch, xducerRoll, profileStatus])
                            if bMiddleBeamOnly:
                                onebasedBeamIdx = max(1, numBeams / 2)  # beamNo-startBeam+1; if onebasedBeamIdx > 0:
                                rbargs = [bathy, profileNum + 1, onebasedBeamIdx]  # one-based profile number
                                numBeams = 1
                            else:
                                rbargs = [bathy, ]
                            if self.ftype == 'TPE':
                                profiles = scipy.zeros((numBeams, 4), scipy.float64)
                            else:
                                profiles = scipy.zeros((numBeams, 6), scipy.float64)
                            for beamNum in xrange(numBeams):
                                # get pointer to current profiles record
                                profilerecord = profiles[beamNum]
                                if self.ftype == 'SLRange' or self.ftype == 'ObservedDepths':
                                    (rcodeCaris,
                                     profilerecord[0],  # time [UTCs80],
                                     profilerecord[1],  # range [meters] or alongTrack [meters],
                                     profilerecord[2],  # travelTime [seconds] or acrossTrack [meters],
                                     profilerecord[3],  # acrossAngle [radians] or depth [meters],
                                     profilerecord[4],  # alongAngle [radians] or depth accuracy, and status
                                     profilerecord[5]) = ReadBeam(*rbargs)
                                elif self.ftype == 'ProcessedDepths':
                                    (rcodeCaris,
                                     profilerecord[0],  # time [UTCs80],
                                     alongTrack, acrossTrack,
                                     profilerecord[1],  # latitude [radians],
                                     profilerecord[2],  # longitude [radians],
                                     profilerecord[3],  # depth [meters],
                                     profilerecord[4],  # depth accuracy, and status
                                     profilerecord[5]) = ReadBeam(*rbargs)
                                else:  # self.ftype=='TPE':
                                    (rcodeCaris,
                                     profilerecord[0],  # time [UTCs80],
                                     profilerecord[1],  # depthTPE (TVU) [meters, 95% CI],
                                     profilerecord[2],  # posTPE (THU) [meters, 95% CI], and status
                                     profilerecord[3]) = ReadBeam(*rbargs)
                                if rcodeCaris != 0:
                                    break  # bad depth--break out of loop
                                else:
                                    if bOnlyAccepted and isREC_STATUS_REJECTED(profilerecord[-1]):  # recall, and only possible if in bMiddleBeamOnly mode
                                        profiles[beamNum] = 0.
                                        bCleanup = True  # remember to remove null records before return
                                        continue
                            if rcodeCaris == 0:
                                if profileNum == 0:
                                    if bUseList:
                                        NumPyArray = [profiles]
                                    else:
                                        NumPyArray = profiles
                                else:
                                    if bUseList:
                                        NumPyArray.append(profiles)
                                    else:
                                        NumPyArray = concatenate((NumPyArray, profiles))
                            else:
                                print "Bad profilerecord (%d) depth -- beamNum = %d" % (profileNum, beamNum)
                                break  # something bad in depth loop...break out of profile loop
                        else:
                            print "Bad profile -- profileNum = %d" % profileNum
                            break  # bad profile--break out of loop
                else:
                    rcode = 0
                self.Close(bathy)
            else:
                rcode = 0
        else:
            rcode = 0
        if not rcode:
            NumPyArray = None
            if bVerbose:
                verboseData = None
        elif oddFactorSkip > 1:  # TODO: assumes not bVerbose and not bUseList
            oddFactorSkip = int(oddFactorSkip)
            if not oddFactorSkip % 2:
                oddFactorSkip += 1
            NumPyArray = NumPyArray[oddFactorSkip / 2:len(NumPyArray) - oddFactorSkip / 2:oddFactorSkip]
        if bCleanup:
            if bUseList:
                nullprofile = [0.] * len(NumPyArray[0])
                NumPyArray = [r for r in NumPyArray if r != nullprofile]
            else:
                NumPyArray = scipy.delete(NumPyArray, scipy.where(~NumPyArray.any(axis=1))[0], 0)
        if bVerbose:
            return NumPyArray, verboseData
        else:
            return NumPyArray

    def WriteTimeSeries(self, pathToPVDL, NumPyArray, verboseData=None, sourcename='', sourceTypeExt='', toolType=None, coordinateType=None, summaryStatus=None, startingBeamNo=1, beamForProfileTime=1, haverangeORalongTrack=(1, None), havealongAngleORdepthAccuracy=(1, None), havestatus=(1, None), sortBytime=True, pdSVPapplied=True, bUseList=False):
        # Writes HDCS bathy data time series from N x [5,6] NumPyArray; assumes NumPyArray sorted chronologically
        # (NumPyArray columns are time, <4x beam data>, status=0x0 (opt.--def. to 0x0); e.g., time vector=NumPyArray[:,0])
        # ASSUMPTION:  if numBeams < 3 --> VBES data; and VBES ProcessedDepths NumPyArray has [only] one beam per profile (unlike SLR & OD)
        # sortBytime is ignored (i.e., is regarded as False) if verboseData not None
        if verboseData:
            profileData = verboseData['profiles']
            sourcename = verboseData['sourceFileName']
            # numBeams contained in profileData, as is startingBeamNo
            numDepths, numProfiles = verboseData['numDepths'], verboseData['numProfiles']
            isVBESdata = None  # isVBESdata is moot--VBES bit is given in summaryStatus word; writeDual is moot as well--encapsulated in block(s) conditioned on isVBESdata
            summaryStatus = verboseData['summaryStatus']
            toolType = verboseData['toolType']
            if self.ftype == 'ProcessedDepths':
                coordinateType = verboseData['coordinateType']
        else:
            profileData = []
            # sourcename is set after bathy.Open, below
            numBeams = self.numBeams
            if bUseList:
                numDepths = sum(scipy.shape(npa)[0] for npa in NumPyArray)
                numProfiles = len(NumPyArray)
            else:
                numDepths = scipy.shape(NumPyArray)[0]
                numProfiles = numDepths / numBeams
            if numBeams == 1:   # if single-beam echosounder data, create a dual frequency depth & specify 'Selected'...
                isVBESdata = 1
                writeDual = 1
            elif numBeams == 2:  # is dual-freq. echosounder data supplied?
                isVBESdata = 1
                writeDual = 0
            else:               # else, is multibeam data; self.numBeams!=None IFF specified in __init__ or prior ReadTimeSeries
                isVBESdata = 0
                writeDual = 0
            if summaryStatus is None:
                if self.ftype == 'ProcessedDepths':
                    summaryStatus = PyPeekXTF.PD_EXAMINED_BY_FILTER_MASK + PyPeekXTF.PD_EXAMINED_BY_HYDROG_MASK + PyPeekXTF.PD_TIDE_APPLIED_MASK
                    if pdSVPapplied:
                        summaryStatus |= PyPeekXTF.PD_SVP_CORRECTED_MASK
                else:
                    summaryStatus = PyPeekXTF.OD_EXAMINED_BY_FILTER_MASK + PyPeekXTF.OD_EXAMINED_BY_HYDROG_MASK
            if isVBESdata:
                # note 0x0 is valid summaryStatus, toolType, and coordinateType
                if self.ftype == 'ObservedDepths':  # 'SLRange' (range.h) does not have a singlebeam flag bit
                    summaryStatus |= PyPeekXTF.OD_SINGLEBEAM_MASK
                if toolType is None:
                    toolType = PyPeekXTF.HIPS_TYPE_HKHYDRO_SB
            else:   # MBES data or otherwise VBES data wherein toolType is specified and are not messing with isVBESdata/writeDual stuff (i.e., for purposes other than PSSObject.ConvertDPsToHDCS; e.g., PostAcqTools read/write records)
                if toolType is None:
                    toolType = PyPeekXTF.HIPS_TYPE_GENERIC  # or use HIPS_TYPE_XTF_RESON?
            if self.ftype == 'ProcessedDepths':
                if coordinateType is None:
                    coordinateType = PyPeekXTF.GEO_LAT_LONG

        if bUseList:
            numFields = scipy.shape(NumPyArray[0])[1]
        else:
            numFields = scipy.shape(NumPyArray)[1]
        if self.ftype == 'SLRange' or self.ftype == 'ObservedDepths':
            fieldcount = 3    # time, travelTime/acrossTrack, and acrossAngle/depth are required
            haverangeORalongTrack, recrangeORalongTrack = haverangeORalongTrack
            if haverangeORalongTrack:
                fieldcount += 1
            elif recrangeORalongTrack is None:
                recrangeORalongTrack = 0.0
        elif self.ftype == 'ProcessedDepths':
            fieldcount = 4    # time, latitude, longitude, and depth are required
        else:  # self.ftype=='TPE':
            fieldcount = 3    # time, depthTPE (TVU), posTPE (THU) are required

        havealongAngleORdepthAccuracy, recalongAngleORdepthAccuracy = havealongAngleORdepthAccuracy
        if havealongAngleORdepthAccuracy:
            fieldcount += 1
        elif recalongAngleORdepthAccuracy is None:
            recalongAngleORdepthAccuracy = 0.0
        havestatus, recstatus = havestatus
        if havestatus:
            fieldcount += 1
        elif recstatus is None:
            recstatus = ZERO_STATUS

        if (numDepths > 0) and (numFields >= fieldcount):  # and (((verboseData)and(len(profileData)==numProfiles)) or ((startingBeamNo<=beamForProfileTime)and(beamForProfileTime<numBeams+startingBeamNo))):
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            rcode = 1
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                # check to see if path to P/V/D/L directory exists; create to leaf dir L, if needed
                if not os.access(pathToPVDL, os.F_OK):
                    os.makedirs(pathToPVDL)
                bathy, bOK = self.Open(pathToPVDL, "create")
                if bathy:
                    if rcodeCaris == 0:
                        if not sourcename:
                            sourcename = line + str(sourceTypeExt)
                        rcodeCaris = self.BeginWriteLine(bathy, str(sourcename))  # str() for unicode conversion
                        if self.ftype == 'SLRange' or self.ftype == 'ObservedDepths':
                            rcodeCaris = self.BeginWriteSummary(bathy, toolType)
                        elif self.ftype == 'ProcessedDepths':
                            rcodeCaris = self.BeginWriteSummary(bathy, toolType, coordinateType)
                        else:  # self.ftype=='TPE'
                            rcodeCaris = self.BeginWriteSummary(bathy)
                        if rcodeCaris == 0:
                            depthNum = -1
                            if sortBytime and not verboseData and not bUseList:
                                sortIdx = argsort(NumPyArray[:, 0])  # Sorted NumPyArray indicies according to [increasing] time
                            for profileNum in xrange(numProfiles):
                                if sortBytime and not verboseData and not bUseList:
                                    profilerecord = NumPyArray[sortIdx[depthNum + 1]]
                                elif not bUseList:
                                    profilerecord = NumPyArray[depthNum + 1]
                                else:
                                    profilerecord = NumPyArray[profileNum][0]

                                if not verboseData:
                                    if beamForProfileTime == startingBeamNo:
                                        profileTime = profilerecord[0]
                                    else:
                                        if sortBytime and not bUseList:
                                            profileTime = NumPyArray[sortIdx[depthNum + 1 + beamForProfileTime - startingBeamNo]][0]
                                        elif not bUseList:
                                            profileTime = NumPyArray[depthNum + 1 + beamForProfileTime - startingBeamNo][0]
                                        else:
                                            profileTime = NumPyArray[profileNum][beamForProfileTime - startingBeamNo][0]
                                    if self.ftype == 'ProcessedDepths':
                                        xducerLat, xducerLon = profilerecord[1:3]  # okay for DPs; FUTURE: change to compute mean position of profile
                                        minLat, minLon = profilerecord[1:3]  # FUTURE: need to search profile for lat/lon limits
                                        maxLat, maxLon = profilerecord[1:3]
                                        xducerPitch, xducerRoll, gyro, heave, pitch, roll, speed = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0   # HIPS I/O says these are obsolete
                                        tide = 0.0  # FUTURE?
                                    elif self.ftype == 'TPE':
                                        pingnum = 1
                                    else:  # germane to SLRange & ObservedDepths
                                        xducerPitch, xducerRoll = 0.0, 0.0  # HIPS I/O says these are obsolete
                                    profileStatus = ZERO_STATUS
                                else:  # verboseData
                                    if self.ftype == 'SLRange' or self.ftype == 'ObservedDepths':
                                        numBeams, startingBeamNo, profileTime, xducerPitch, xducerRoll, profileStatus = profileData[profileNum]
                                    elif self.ftype == 'ProcessedDepths':
                                        numBeams, startingBeamNo, profileTime, xducerLat, xducerLon, minLat, maxLat, minLon, maxLon, gyro, heave, pitch, roll, tide, speed, xducerPitch, xducerRoll, profileStatus = profileData[profileNum]
                                    else:  # self.ftype=='TPE'
                                        numBeams, startingBeamNo, profileTime, pingnum, profileStatus = profileData[profileNum]
                                if self.ftype == 'SLRange' or self.ftype == 'ObservedDepths':
                                    if isVBESdata:
                                        rcodeCaris = self.BeginWriteProfile(bathy,
                                                                            3, startingBeamNo,  # Always have 3 depths/profile for VBES (hi/lo/sel)
                                                                            profileTime,
                                                                            xducerPitch, xducerRoll,
                                                                            asSignedInt(profileStatus))
                                    else:  # multibeam data or otherwise as dictated by verboseData profile data
                                        rcodeCaris = self.BeginWriteProfile(bathy,
                                                                            numBeams, startingBeamNo,
                                                                            profileTime,
                                                                            xducerPitch, xducerRoll,
                                                                            asSignedInt(profileStatus))
                                elif self.ftype == 'ProcessedDepths':
                                    rcodeCaris = self.BeginWriteProfile(bathy,
                                                                        numBeams, startingBeamNo,
                                                                        profileTime,
                                                                        xducerLat, xducerLon,
                                                                        minLat, maxLat, minLon, maxLon,
                                                                        gyro, heave, pitch, roll, tide, speed,
                                                                        xducerPitch, xducerRoll,
                                                                        asSignedInt(profileStatus))
                                else:  # self.ftype=='TPE'
                                    rcodeCaris = self.BeginWriteProfile(bathy,
                                                                        numBeams, startingBeamNo,
                                                                        profileTime, pingnum,
                                                                        asSignedInt(profileStatus))
                                if rcodeCaris == 0:
                                    for beamNum in xrange(numBeams):
                                        if not bUseList:  # note: bUseList beamNum->depthNum: NumPyArray[profileNum][beamNum]
                                            depthNum = profileNum * numBeams + beamNum
                                        if sortBytime and not verboseData and not bUseList:
                                            profilerecord = NumPyArray[sortIdx[depthNum]]
                                        elif not bUseList:
                                            profilerecord = NumPyArray[depthNum]
                                        else:
                                            profilerecord = NumPyArray[profileNum][beamNum]
                                        if self.ftype == 'SLRange' or self.ftype == 'ObservedDepths':
                                            if haverangeORalongTrack:
                                                recrangeORalongTrack = profilerecord[1]
                                                rectravelTimeORacrossTrack = profilerecord[2]
                                                recacrossAngleORdepth = profilerecord[3]
                                                if havealongAngleORdepthAccuracy:
                                                    recalongAngleORdepthAccuracy = profilerecord[4]
                                                    if havestatus:
                                                        recstatus = profilerecord[5]
                                                elif havestatus:
                                                    recstatus = profilerecord[4]
                                            else:
                                                rectravelTimeORacrossTrack = profilerecord[1]
                                                recacrossAngleORdepth = profilerecord[2]
                                                if havealongAngleORdepthAccuracy:
                                                    recalongAngleORdepthAccuracy = profilerecord[3]
                                                    if havestatus:
                                                        recstatus = profilerecord[4]
                                                elif havestatus:
                                                    recstatus = profilerecord[3]
                                            rcodeCaris = self.Write(bathy,
                                                                    profilerecord[0],             # time [UTCs80],
                                                                    recrangeORalongTrack,         # range [meters] or alongTrack [meters],
                                                                    rectravelTimeORacrossTrack,   # travelTime [seconds] or acrossTrack [meters],
                                                                    recacrossAngleORdepth,        # acrossAngle [radians] or depth [meters],
                                                                    recalongAngleORdepthAccuracy,  # alongAngle [radians] or depthAccuracy,
                                                                    asSignedInt(recstatus))       # and status
                                        elif self.ftype == 'ProcessedDepths':
                                            if havealongAngleORdepthAccuracy:
                                                recalongAngleORdepthAccuracy = profilerecord[4]
                                                if havestatus:
                                                    recstatus = profilerecord[5]
                                            elif havestatus:
                                                recstatus = profilerecord[4]
                                            alongTrack, acrossTrack = 0.0, 0.0
                                            rcodeCaris = self.Write(bathy,
                                                                    profilerecord[0],             # time [UTCs80],
                                                                    alongTrack, acrossTrack,
                                                                    profilerecord[1],             # latitude [radians],
                                                                    profilerecord[2],             # longitude [radians],
                                                                    profilerecord[3],             # depth [meters],
                                                                    recalongAngleORdepthAccuracy,  # alongAngle [radians] or depthAccuracy,
                                                                    asSignedInt(recstatus))       # and status
                                        else:  # self.ftype=='TPE'
                                            if havestatus:
                                                recstatus = profilerecord[3]
                                            rcodeCaris = self.Write(bathy,
                                                                    profilerecord[0],             # time [UTCs80],
                                                                    profilerecord[1],             # depthTPE (TVU) [meters, 95% CI],
                                                                    profilerecord[2],             # posTPE (THU) [meters, 95% CI],
                                                                    asSignedInt(recstatus))       # and status
                                        if rcodeCaris != 0:
                                            break  # bad beam--break out of depth loop
                                    if rcodeCaris == 0:   # if OK, finish up VBES profile as needed...
                                        if isVBESdata and (self.ftype == 'SLRange' or self.ftype == 'ObservedDepths'):
                                            if writeDual:  # write dual frequency beam using same depth
                                                rcodeCaris = self.Write(bathy,
                                                                        profilerecord[0],             # time [UTCs80],
                                                                        recrangeORalongTrack,         # range [meters] or alongTrack [meters],
                                                                        rectravelTimeORacrossTrack,   # travelTime [seconds] or acrossTrack [meters],
                                                                        recacrossAngleORdepth,        # acrossAngle [radians] or depth [meters],
                                                                        recalongAngleORdepthAccuracy,  # alongAngle [radians] or depthAccuracy,
                                                                        asSignedInt(recstatus))       # and status
                                            # always write selected beam for SLRange & ObservedDepths
                                            rcodeCaris = self.Write(bathy,
                                                                    profilerecord[0],             # time [UTCs80],
                                                                    recrangeORalongTrack,         # range [meters] or alongTrack [meters],
                                                                    rectravelTimeORacrossTrack,   # travelTime [seconds] or acrossTrack [meters],
                                                                    recacrossAngleORdepth,        # acrossAngle [radians] or depth [meters],
                                                                    recalongAngleORdepthAccuracy,  # alongAngle [radians] or depthAccuracy,
                                                                    asSignedInt(recstatus))       # and status
                                        rcodeCaris = self.EndWriteProfile(bathy)
                                    if rcodeCaris != 0:
                                        break  # bad beam or profile--break out of profile loop
                                else:
                                    break  # unable to begin a profile--break out of profile loop
                            rcodeCaris = self.EndWriteLine(bathy, ZERO_STATUS)  # status=0 per HIPS I/O docs
                            if rcodeCaris == 0:
                                self.EndWriteSummary(bathy, asSignedInt(summaryStatus))   # Don't care about return status at this point; will [attempt to] close next...
                    self.Close(bathy)
                    if rcodeCaris != 0:
                        rcode = 0
                else:
                    rcode = 0
            else:
                rcode = 0
        else:
            rcode = 0
        return rcode


class HDCSEventMk(HDCSdata):
    def __init__(self):
        self.Open = PyPeekXTF.EMOpenDir
        self.Open = ConfirmOpen(self.Open)
        self.ReadSummary = PyPeekXTF.EMSummary
        self.ReadLineSummary = PyPeekXTF.EMLineSegment
        self.Read = PyPeekXTF.EMReadSeq
        self.SetStatus = PyPeekXTF.EMSetSummaryStatus  # not needed for sequential write mode; done via WriteSummary
        self.BeginWrite = PyPeekXTF.EMBgnSeqWriteLineSegment
        self.Write = PyPeekXTF.EMSeqWrite
        self.EndWrite = PyPeekXTF.EMEndSeqWriteLineSegment
        self.WriteSummary = PyPeekXTF.EMEndSeqWriteSummary
        self.Close = PyPeekXTF.EMClose

    def ReadTimeSeries(self, pathToPVDL, bVerbose=False):
        # Returns HDCS Events data time series in N x 4 list (inherently sorted by time)
        # (list columns are number, time, text, status)
        if bVerbose:
            verboseData = {'summaryStatus': None, 'sourceFileName': None}
        (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
        rcode = 1
        rcodeCaris = 0    # HDCS I/O "Okay"=0
        if self.SetHDCS_DATA_PATH(hdcsdatapath):
            em, bOK = self.Open(pathToPVDL, "query")
            if em:
                (rcodeCaris,
                 numLineSegments, numRecords,
                 minTime, maxTime,
                 summaryStatus) = self.ReadSummary(em)
                if rcodeCaris == 0:
                    if bVerbose:
                        verboseData['summaryStatus'] = summaryStatus
                        # ReadLineSummary for sourceFileName (note reread of numRecords)
                        (rcodeCaris,
                         sourceFileName,
                         bgnIndex, endIndex,
                         minTime, maxTime,
                         lineSegmentStatus) = self.ReadLineSummary(em, 1)
                        if rcodeCaris == 0:
                            verboseData['sourceFileName'] = sourceFileName
                    emlist = []
                    for recordNum in xrange(numRecords):
                        (rcodeCaris, number, beamtime, text, status) = self.Read(em)
                        if rcodeCaris == 0:
                            emlist.append([number, beamtime, text, status])
                        else:
                            rcode = 0
                            break   # bad record--break out of loop
                else:
                    rcode = 0
                self.Close(em)
            else:
                rcode = 0
        else:
            rcode = 0
        if not rcode:
            emlist = []
            if bVerbose:
                verboseData = None
        if bVerbose:
            return emlist, verboseData
        else:
            return emlist

    def WriteTimeSeries(self, pathToPVDL, emlist, verboseData=None, sourcename='', sourceTypeExt='', recstatus=None, sortBytime=False):
        # Writes HDCS Events time series from N x 4 list; assumes list sorted chronologically
        # (list columns are number, time, text, record status)
        numRecords = len(emlist)
        if numRecords > 0 and len(emlist[0]) > 2:
            if len(emlist[0]) == 4:
                havestatus = 1
            else:
                havestatus = 0
                if recstatus is None:
                    recstatus = ZERO_STATUS
            (hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)
            if verboseData:
                summaryStatus = verboseData['summaryStatus']
                sourcename = verboseData['sourceFileName']
            else:
                summaryStatus = ZERO_STATUS
                if not sourcename:
                    sourcename = line + str(sourceTypeExt)
            rcode = 1
            rcodeCaris = 0    # HDCS I/O "Okay"=0
            if self.SetHDCS_DATA_PATH(hdcsdatapath):
                # check to see if path to P/V/D/L directory exists; create to leaf dir L, if needed
                if not os.access(pathToPVDL, os.F_OK):
                    os.makedirs(pathToPVDL)
                em, bOK = self.Open(pathToPVDL, "create")
                if em:
                    if rcodeCaris == 0:
                        rcodeCaris = self.BeginWrite(em, str(sourcename))  # str() for unicode conversion
                        if rcodeCaris == 0:
                            emlistS = SortBy(emlist, 1)  # sort emlist by time
                            if not emlistS == SortBy(emlist, 0):  # if emIDs not strictly increasing...
                                print "  --Event #s not strictly increasing with time--will use simple index for Event IDs."
                                for idx in xrange(numRecords):
                                    emlistS[idx][0] = idx + 1     # ...replace with simple index 1:numRecords
                            for recordNum in xrange(numRecords):
                                emrecord = emlistS[recordNum]     # use sorted emlist (emlistS)
                                if havestatus:
                                    recstatus = emrecord[3]
                                rcodeCaris = self.Write(em,
                                                        emrecord[0],    # emID
                                                        emrecord[1],    # time [UTCs80],
                                                        emrecord[2][:79],    # text (79 + NULL terminator = 80 chars--max per HDCS I/O docs),
                                                        asSignedInt(recstatus))      # and record status
                                if rcodeCaris != 0:
                                    break
                            if rcodeCaris == 0:
                                rcodeCaris = self.EndWrite(em, ZERO_STATUS)  # status=0 per HIPS I/O docs
                                if rcodeCaris == 0:
                                    self.WriteSummary(em, asSignedInt(summaryStatus))  # Don't care about return status at this point; will [attempt to] close next...
                    self.Close(em)
                    if rcodeCaris != 0:
                        rcode = 0
                else:
                    rcode = 0
            else:
                rcode = 0
        else:
            rcode = 0
        return rcode
