import pytest
from HSTPBin import PyPeekXTF
# from HSTB.drivers import contacts


@pytest.fixture(scope="module", params=[PyPeekXTF, ])  # contacts
def contact_module(request):
    """Runs tests with the C++ and python versions of contacts to ensure both conform"""
    yield request.param


@pytest.fixture(scope="module")
def cf(contact_module):
    confile = contact_module.CContactsFile()
    confile.Open("")
    return confile


@pytest.fixture(scope="module")
def cl(contact_module, cf):
    cl = contact_module.CContactLine()
    cf.GetLine(0, cl)
    return cl


@pytest.fixture(scope="module")
def con(contact_module, cf, cl):
    con = contact_module.CContact()
    cl.GetContact(0, con)
    return con


def test_line(contact_module, cf):
    cl = contact_module.CContactLine()
    cf.AddLine("Test1", cl)
    cl2 = contact_module.CContactLine()
    # cl.SetDOB('ENC_S57dict.GetXML', GetCurrentTimeStr())
    cf.AddLine("Test2", cl2)
    assert cf.GetNumLines() == 2
    cf.Save("test.xml", 1)
    xml = open("test.xml", "r").read()
    assert '<HSTPVersion>11.000000</HSTPVersion><line name="Test1"/><line name="Test2"/>' in xml
    cl3 = contact_module.CContactLine()
    cf.GetLine(0, cl3)
    assert cl3.GetName()[1] == "Test1"


def test_contact(contact_module, cf, cl):
    con = contact_module.CContact()
    cl.AddContact("Number_One", con)
    con.SetType("GP")
    con.SetFlags("012A3BF00")

    cf.Save("test.xml", 1)
    xml = open("test.xml", "r").read()
    print(xml)

    assert '<contact number="Number_One"><FType>GP</FType><flags>012A3BF00</flags></contact>' in xml


def test_points(contact_module, cf, cl, con):
    pt = contact_module.CContactPoint()
    con.AddPoint("1", pt)  # need a point even if bUsePtGeomData, as other attributes need access to a point structure
    pt.SetProfile("222")
    pt.SetBeam("111")
    pt.SetObsDepth("55")
    pt.SetDepth("44")
    pt.SetTime("11:22")
    pt.SetLatitude("33.456")
    pt.SetLongitude("-111.987")

    cf.Save("test.xml", 1)
    xml = open("test.xml", "r").read()
    print(xml)

    assert '<point number="1"><profile>222</profile><beam>111</beam><obsdepth>55</obsdepth><depth>44</depth><time>11:22</time><lat>33.456</lat><lon>-111.987</lon></point>' in xml


def test_attributes(contact_module, cf, cl, con):
    charts = contact_module.CContactCharts()
    chart = contact_module.CContactChart()
    con.AddCharts(charts)
    charts.AddChart("12345", chart)
    print(chart.GetText())
    chart.SetText("34521")
    print(chart.GetText())
    chart.SetDToN("not_true")
    print(chart.GetReport())
    charts.AddChart("67890", chart)
    chart.SetDToN("False")
    chart.SetReport("True")
    print(chart.GetText())
    charts.GetChart(0, chart)
    chart.SetDToN("true")  # write after reading from xml object
    chart.SetReport("false")
    print(chart.GetDToN(), "should be 'true'")

    cf.Save("test.xml", 1)
    xml = open("test.xml", "r").read()
    print(xml)

    assert '<AffectedCharts><Chart Meta="12345" DToN="true" Report="false">34521</Chart><Chart Meta="67890" DToN="False" Report="True">67890</Chart></AffectedCharts>' in xml


def test_xpath_and_charts(contact_module, cf):
    # affchartsMetadata = []  # ["11506, 42nd Ed., 12/01/2005; USCG LNM: 12/30/2005 (2/15/2006); NGA NTM: None (2/8/2006), (11506_1;11506_2) 1:40000;1:20000", ...]
    xmlobj = cf
    rncs = {}  # use dictionary keys to assemble list of unique charts
    if xmlobj.XPathQuery('./line/contact/AffectedCharts'):
        ccharts = contact_module.CContactCharts()
        chart = contact_module.CContactChart()
        while xmlobj.NextChild(ccharts):
            for idx in range(ccharts.GetNumCharts()):
                print(ccharts.GetChart(idx, chart))
                print(chart.GetText())
                rncs[chart.GetText()[1]] = None
    print(rncs)

    assert len(rncs) == 2
    assert rncs["34521"] is None
