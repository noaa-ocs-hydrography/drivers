import pytest
# from pytest import approx  #  approx wasn't working on numpy arrays, use the builtin numpy testing functions
from HSTPBin import PyPeekXTF
from HSTB.drivers import HDCSio
from HSTB.drivers import hipsio
import numpy

# @pytest.fixture  # creates an object used in the parameters of a function
# @pytest.fixture(scope="module", params=["smtp.gmail.com", "mail.python.org"])  #create only once for all tests in the module -- also can paramterize for multiple runs (use the request fixture that is always available)
# def smtp(request):
#    return smtplib.SMTP(request.param, port=587, timeout=5)

mb_path = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\E350_H11529_G\RU_MB_2006\Caris2006-289\311_1835"
sb_path = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\E350_H11529_G\RU_SB_2006\2006-226\100_1600"
sss_path = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\A910_Buffer\WH14\2000-310\800_2108"
numpy.set_printoptions(formatter={'float': '{: 0.7f}'.format})


@pytest.fixture(scope="module", params=[HDCSio, hipsio])
def CarisIO(request):
    if request.param == HDCSio:
        HDCSio.InitLicenseHDCS()
    yield request.param


@pytest.mark.parametrize("year,doy,expected", [
    (1980, 1, 19),
    (2012, 200, 35),
    #    (2012, 200, 36),  # an intentional error
])
def test_leap_seconds(year, doy, expected):
    assert PyPeekXTF.TmGetTAIUTCOffset(year, doy) == expected


@pytest.mark.parametrize("sensor_type,hdcspath,indices,values", [
    ("Tide", mb_path, [0, -1], [[845490947.8760000, 0.4090000, 0.0000000], [845491113.3789999, 0.4250000, 0.0000000]]),
    ("Roll", mb_path, [0, -1], [[845490947.8760000, -0.0275161, 0.0000000], [845491113.3789999, -0.0313671, 0.0000000]]),
    ("Pitch", mb_path, [0, -1], [[845490947.8760000, 0.0102635, 0.0000000], [845491113.3789999, 0.0113249, 0.0000000]]),
    ("Gyro", mb_path, [0, -1], [[845490947.8760000, 1.4602781, 0.0000000], [845491113.3789999, 1.4487763, 0.0000000]]),
    ("SSSGyro", mb_path, [0, -1], [[845490947.6059999, 1.4603257, 0.0000000], [845491113.1610000, 1.4490309, 0.0000000]]),
    ("GPSHeight", mb_path, [0, -1], [[845490947.8760000, -39.0230000, 0.0000000], [845491113.3789999, -37.9820000, 0.0000000]]),
    ("Heave", mb_path, [0, -1], [[845490947.8760000, -0.0840000, 0.0000000], [845491113.3789999, 0.0040000, 0.0000000]]),
])
def test_attitude(CarisIO, sensor_type, hdcspath, indices, values):
    att = CarisIO.HDCSAttitude(sensor_type).ReadTimeSeries(hdcspath)
    numpy.testing.assert_almost_equal(att[indices], values)
    # assert (att[indices] == approx(numpy.array(values))).all()


def test_write_tide(CarisIO):
    t = CarisIO.HDCSAttitude("Tide")
    o = t.ReadTimeSeries(mb_path, bVerbose=True)
    print o
    v = o[0]
    v[:, 1] += 1
    t.WriteTimeSeries(mb_path + "_o", v, o[1])
    o2 = t.ReadTimeSeries(mb_path + "_o", bVerbose=True)
    print o2
    numpy.testing.assert_almost_equal(v[:, 1], o2[0][:, 1])


def test_write_nav(CarisIO):
    n = CarisIO.HDCSNav("Navigation")
    o = n.ReadTimeSeries(mb_path, bVerbose=True)
    print o
    v = o[0]
    v[:, 0] += 1.0
    fake = numpy.array([[0., 0., -0., 0., 0.], [1., 0., -0., 0., 0.]])
    v = fake
    n.WriteTimeSeries(mb_path + "_o", v, o[1])
    o2 = n.ReadTimeSeries(mb_path + "_o", bVerbose=True)
    print o2
    numpy.testing.assert_almost_equal(v[:, 0], o2[0][:, 0])


@pytest.mark.parametrize("sensor_type,hdcspath,indices,values", [
    ("SLRange", mb_path, [0, -1], [[845490947.6059999, 0.0000000, 0.0164830, -1.0428000, 0.0000000, 0.0000000],
                                   [845491113.1610000, 0.0000000, 0.0140960, 1.0428000, 0.0000000, 0.0000000]]),
    ("ObservedDepths", mb_path, [0, -1], [[845490947.6860000, -0.1230000, -21.8550000, 13.7640000, 0.0000000, 201326592.0000000],
                                          [845491113.2410001, -0.1280000, 18.0570000, 13.0430000, 0.0000000, 201326592.0000000]]),
    ("ProcessedDepths", mb_path, [0, -1], [[845490947.6860000, 0.6528447, -1.3276895, 14.0250000, 0.0000000, 12582912.0000000],
                                           [845491113.2410001, 0.6528390, -1.3275605, 12.2440000, 0.0000000, 12582912.0000000]]),
])
def test_bathy(sensor_type, hdcspath, indices, values):
    att = HDCSio.HDCSBathy(sensor_type).ReadTimeSeries(hdcspath)
    numpy.testing.assert_almost_equal(att[indices], values)


@pytest.mark.parametrize("sensor_type,hdcspath,indices,values", [
    ("Navigation", mb_path, [0, -1], [[845490947.8760000, 0.6528409, -1.3276877, 0.0000000, 0.0000000], [845491113.3789999, 0.6528415, -1.3275597, 0.0000000, 0.0000000]]),
    ("SSSNavigation", sss_path, [0, -1], [[657925744.6600000, 0.7518598, -1.2342281, 0.0000000, 3221225472.0000000], [657926131.6760000, 0.7517919, -1.2339690, 0.0000000, 0.0000000]]),
])
def test_navigation(CarisIO, sensor_type, hdcspath, indices, values):
    att = CarisIO.HDCSNav(sensor_type).ReadTimeSeries(hdcspath)
    numpy.testing.assert_almost_equal(att[indices], values)


def test_tideerror():
    tef = PyPeekXTF.TideErrorFile(mb_path)
    assert 7 == tef.getNumberOfRecords()
    assert tef.read(1) == [0, 845490947.876, 0.0, 0]
    assert tef.read(7) == [0, 845491113.379, 0.0, 0]


"""
>>> HDCSio.InitLicenseHDCS()
(True, '')
>>> PyPeekXTF.InitLicense()
'c2c98f39ba82acc965'
>>> PyPeekXTF.IsLicensed()
True
>>> PyPeekXTF.HDCSInit()
True
>>> HDCSio.InitLicenseHDCS()
(True, '')
>>> PyPeekXTF.TmGetTAIUTCOffset(1980, 1)
19
>>> PyPeekXTF.TmGetTAIUTCOffset(2012, 185)
35

>>> hdcsdatapath = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data"
>>> PyPeekXTF.SetEnvironment('HDCS_DATA_PATH', hdcsdatapath)
True
>>> PyPeekXTF.HDCSInit()
True
>>> pathToPVDL = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\E350_H11529_G\RU_MB_2006\Caris2006-289\311_1835"
>>> attitude, bOK = PyPeekXTF.TideOpenDir(pathToPVDL, "query")
>>> attitude, bOK
(<Swig Object of type 'HDCS_ProcessedDepths' at 0xd98ee30>, 0)
>>> (rcodeCaris,numLineSegments, numRecords,minTime, maxTime,minSensor, maxSensor,summaryStatus) = PyPeekXTF.TideSummary(attitude)
>>> (rcodeCaris,numLineSegments, numRecords,minTime, maxTime,minSensor, maxSensor,summaryStatus)
(0, 1, 7, 845490947.876, 845491113.379, 0.342, 0.425, 0)
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845490947.876, 0.409, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845490977.877, 0.41, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845491007.927, 0.411, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845491037.977, 0.342, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845491067.978, 0.422, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845491098.028, 0.424, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[0, 845491113.379, 0.425, 0]
>>> PyPeekXTF.TideReadSeq(attitude)
[5001225, -9.255963134931783e+61, -9.255963134931783e+61, 3435973836L]
>>> PyPeekXTF.TideClose(attitude)
0
>>> tide = HDCSio.HDCSAttitude("Tide")
>>> tide
<HSTB.drivers.HDCSio.HDCSAttitude instance at 0x000000000E63ACC8>
>>> numpy.set_printoptions(formatter={'float': '{: 0.7f}'.format})



>>> sss_path = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\A910_Buffer\WH14\2000-310\800_2108"
>>> sb_path = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\E350_H11529_G\RU_SB_2006\2006-226\100_1600"
>>> mb_path = r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\E350_H11529_G\RU_MB_2006\Caris2006-289\311_1835"
>>> numpy.set_printoptions(formatter={'float': '{: 0.7f}'.format})
>>> HDCSio.HDCSAttitude("Tide").ReadTimeSeries(mb_path)
array([[ 845490947.8760000,  0.4090000,  0.0000000],
       [ 845490977.8770000,  0.4100000,  0.0000000],
       [ 845491007.9270000,  0.4110000,  0.0000000],
       [ 845491037.9770000,  0.3420000,  0.0000000],
       [ 845491067.9780000,  0.4220000,  0.0000000],
       [ 845491098.0280000,  0.4240000,  0.0000000],
       [ 845491113.3789999,  0.4250000,  0.0000000]])
>>> HDCSio.HDCSAttitude("Roll").ReadTimeSeries(mb_path)
array([[ 845490947.8760000, -0.0275161,  0.0000000],
       [ 845490947.9260000, -0.0274741,  0.0000000],
       [ 845490947.9760000, -0.0274360,  0.0000000],
       ...,
       [ 845491113.2790000, -0.0308430,  0.0000000],
       [ 845491113.3290000, -0.0311052,  0.0000000],
       [ 845491113.3789999, -0.0313671,  0.0000000]])
>>> HDCSio.HDCSAttitude("Pitch").ReadTimeSeries(mb_path)
array([[ 845490947.8760000,  0.0102635,  0.0000000],
       [ 845490947.9260000,  0.0103094,  0.0000000],
       [ 845490947.9760000,  0.0103478,  0.0000000],
       ...,
       [ 845491113.2790000,  0.0113203,  0.0000000],
       [ 845491113.3290000,  0.0113225,  0.0000000],
       [ 845491113.3789999,  0.0113249,  0.0000000]])
>>> HDCSio.HDCSAttitude("Gyro").ReadTimeSeries(mb_path)
array([[ 845490947.8760000,  1.4602781,  0.0000000],
       [ 845490947.9260000,  1.4602304,  0.0000000],
       [ 845490947.9760000,  1.4601867,  0.0000000],
       ...,
       [ 845491113.2790000,  1.4493045,  0.0000000],
       [ 845491113.3290000,  1.4490309,  0.0000000],
       [ 845491113.3789999,  1.4487763,  0.0000000]])
>>> HDCSio.HDCSAttitude("SSSGyro").ReadTimeSeries(mb_path)
array([[ 845490947.6059999,  1.4603257,  0.0000000],
       [ 845490947.6920000,  1.4602304,  0.0000000],
       [ 845490947.7780000,  1.4601867,  0.0000000],
       ...,
       [ 845491113.0150000,  1.4498329,  0.0000000],
       [ 845491113.0870000,  1.4493045,  0.0000000],
       [ 845491113.1610000,  1.4490309,  0.0000000]])
>>> HDCSio.HDCSAttitude("GPSHeight").ReadTimeSeries(mb_path)
array([[ 845490947.8760000, -39.0230000,  0.0000000],
       [ 845490947.9260000, -39.0240000,  0.0000000],
       [ 845490947.9760000, -39.0240000,  0.0000000],
       ...,
       [ 845491113.2790000, -37.9700000,  0.0000000],
       [ 845491113.3290000, -37.9760000,  0.0000000],
       [ 845491113.3789999, -37.9820000,  0.0000000]])
>>> HDCSio.HDCSAttitude("Heave").ReadTimeSeries(mb_path)
array([[ 845490947.8760000, -0.0840000,  0.0000000],
       [ 845490947.9260000, -0.0840000,  0.0000000],
       [ 845490947.9760000, -0.0850000,  0.0000000],
       ...,
       [ 845491113.2790000,  0.0040000,  0.0000000],
       [ 845491113.3290000,  0.0040000,  0.0000000],
       [ 845491113.3789999,  0.0040000,  0.0000000]])
>>> HDCSio.HDCSBathy("SLRange").ReadTimeSeries(mb_path)
array([[ 845490947.6059999,  0.0000000,  0.0164830, -1.0428000,  0.0000000,
         0.0000000],
       [ 845490947.6059999,  0.0000000,  0.0162190, -1.0341000,  0.0000000,
         0.0000000],
       [ 845490947.6059999,  0.0000000,  0.0159950, -1.0253000,  0.0000000,
         0.0000000],
       ...,
       [ 845491113.1610000,  0.0000000,  0.0137620,  1.0253000,  0.0000000,
         0.0000000],
       [ 845491113.1610000,  0.0000000,  0.0139860,  1.0341000,  0.0000000,
         0.0000000],
       [ 845491113.1610000,  0.0000000,  0.0140960,  1.0428000,  0.0000000,
         0.0000000]])
>>> HDCSio.HDCSBathy("ObservedDepths").ReadTimeSeries(mb_path)
array([[ 845490947.6860000, -0.1230000, -21.8550000,  13.7640000,
         0.0000000,  201326592.0000000],
       [ 845490947.6860000, -0.1230000, -21.4020000,  13.7650000,
         0.0000000,  201326592.0000000],
       [ 845490947.6860000, -0.1230000, -21.0020000,  13.7900000,
         0.0000000,  201326592.0000000],
       ...,
       [ 845491113.2410001, -0.1280000,  17.4350000,  13.0890000,
         0.0000000,  201326592.0000000],
       [ 845491113.2410001, -0.1290000,  17.8190000,  13.1130000,
         0.0000000,  201326592.0000000],
       [ 845491113.2410001, -0.1280000,  18.0570000,  13.0430000,
         0.0000000,  201326592.0000000]])
>>> HDCSio.HDCSBathy("ProcessedDepths").ReadTimeSeries(mb_path)
array([[ 845490947.6860000,  0.6528447, -1.3276895,  14.0250000,
         0.0000000,  12582912.0000000],
       [ 845490947.6860000,  0.6528446, -1.3276895,  14.0120000,
         0.0000000,  12582912.0000000],
       [ 845490947.6860000,  0.6528446, -1.3276894,  14.0240000,
         0.0000000,  12582912.0000000],
       ...,
       [ 845491113.2410001,  0.6528391, -1.3275605,  12.3090000,
         0.0000000,  12582912.0000000],
       [ 845491113.2410001,  0.6528391, -1.3275605,  12.3210000,
         0.0000000,  12582912.0000000],
       [ 845491113.2410001,  0.6528390, -1.3275605,  12.2440000,
         0.0000000,  12582912.0000000]])
>>> HDCSio.HDCSNav("Navigation").ReadTimeSeries(mb_path)
array([[ 845490947.8760000,  0.6528409, -1.3276877,  0.0000000,  0.0000000],
       [ 845490947.9260000,  0.6528409, -1.3276876,  0.0000000,  0.0000000],
       [ 845490947.9760000,  0.6528409, -1.3276876,  0.0000000,  0.0000000],
       ...,
       [ 845491113.2790000,  0.6528415, -1.3275598,  0.0000000,  0.0000000],
       [ 845491113.3290000,  0.6528415, -1.3275598,  0.0000000,  0.0000000],
       [ 845491113.3789999,  0.6528415, -1.3275597,  0.0000000,  0.0000000]])
>>> HDCSio.HDCSNav("SSSNavigation").ReadTimeSeries(sss_path)
array([[ 657925744.6600000,  0.7518598, -1.2342281,  0.0000000,
         3221225472.0000000],
       [ 657925744.9800000,  0.7518599, -1.2342277,  0.0000000,
         3221225472.0000000],
       [ 657925745.5410000,  0.7518599, -1.2342273,  0.0000000,
         3221225472.0000000],
       ...,
       [ 657926130.6350000,  0.7517925, -1.2339694,  0.0000000,  0.0000000],
       [ 657926131.1460000,  0.7517922, -1.2339692,  0.0000000,  0.0000000],
       [ 657926131.6760000,  0.7517919, -1.2339690,  0.0000000,  0.0000000]])
>>> tef = PyPeekXTF.TideErrorFile(r"C:\PydroTrunk\DocsAndDemoData\HDCS_Data\E350_H11529_G\RU_MB_2006\Caris2006-289\311_1835")
>>> tef.getNumberOfRecords()
7
>>> tef.read(0)
[5000064, -9.255963134931783e+61, -9.255963134931783e+61, 3435973836L]
>>> tef.read(1\)
Traceback (  File "<interactive input>", line 1
    tef.read(1\)
               ^
SyntaxError: unexpected character after line continuation character
>>> tef.read(1)
[0, 845490947.876, 0.0, 0]
>>> tef.read(2)
[0, 845490977.877, 0.0, 0]
>>> tef.read(3)
[0, 845491007.927, 0.0, 0]
>>> tef.read(4)
[0, 845491037.977, 0.0, 0]
>>> tef.read(5)
[0, 845491067.978, 0.0, 0]
>>> tef.read(6)
[0, 845491098.028, 0.0, 0]
>>> tef.read(7)
[0, 845491113.379, 0.0, 0]
>>> tef.read(8)
[5000064, -9.255963134931783e+61, -9.255963134931783e+61, 3435973836L]
"""
