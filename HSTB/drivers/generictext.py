#supply a parsing object and return lists 
import copy
import traceback
import time
import re
import cPickle
import datetime
import itertools
import codecs
try:
    from collections import OrderedDict
except: #2.4, 2.5, 2.6 compatibility
    from _ordereddict import ordereddict as OrderedDict

from mx import DateTime

from HSTB.shared import geodesy  
from HSTB.shared import coordinates
from HSTB.time import UTC  

REGS={}
REGS['DAY']=r"\D*(?P<day>\d+)" #day field plus delimeter(s) before the value
REGS['MO']=r"\D*(?P<month>\d+)" #month field plus delimeter(s) before the value
REGS['YR']=r"\D*(?P<year>\d+)" #year field plus delimeter(s) before the value
REGS['H']=r"\D*(?P<hours>\d+)" #hour field plus delimeter(s) before the field
REGS['M']=r"\D*(?P<minutes>\d+)" #minutes field plus delimeter(s) before the field
REGS['S']=r"\D*(?P<seconds>\d+)" #seconds field plus delimeter(s) before the field
REGS['s']=r"\D*(?P<seconds>\d+[\.]?\d*)" #seconds field plus delimeter(s) before the field
REGS['m']=r"\D*(?P<minutes>\d+[\.]?\d*)" #minutes field plus delimeter(s) before the field
REGS['h']=r"\D*(?P<hours>\d+[\.]?\d*)" #hours field plus delimeter (s) before the field
REGS['SOD']=r"\D*(?P<seconds>\d+[\.]?\d*)" #seconds field plus delimeter(s) before the field
REGS['DOY']=r"\D*(?P<DOY>\d+)" #day of year field plus delimeter(s) before the value
REGS['UTC80']=r"\D*(?P<UTC80>\d+[\.]?\d*)" #UTC seconds since 1980 (caris time) field plus delimeter(s) before the field
REGS['AM']=r"\W*(?P<am_pm>[apAP][mM])" #find AM or PM marker + skips any non-alphanumeric leading characters (comma tab space etc.)
REGS['YYYYMMDD']=r"\D*(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})" #four digit year, two digit month and day with no delimiter between

def ParseTime(exp, strn):
    m=exp.match(strn)
    timeStr="TimeParseFailed"
    dt=None
    if m:
        parsed=m.groupdict()
        try: #Look for UTC seconds since 1980 (CARIS time)
            utc=float(parsed['UTC80'])
            year,doy,sec=UTC.PyTmUTCs80toYDS(utc)
        except KeyError: # time is in a Date and Time of Day format
            try: #look for Year, Day of Year
                year,doy = int(parsed['year']),int(parsed['DOY'])
            except KeyError:
                try: #look for Year, month, day
                    year,month,day=int(parsed['year']),int(parsed['month']),int(parsed['day'])
                    doy=UTC.PyTmYMDtoJD(year, month, day)
                except KeyError: #no date found
                    year=1980
                    doy=1
            sec=0
            try:
                try:
                    if parsed['am_pm'].lower()=="pm" and float(parsed['hours'])!=12: sec+=12*3600.0
                    if parsed['am_pm'].lower()=="am" and float(parsed['hours'])==12: sec-=12*3600.0
                except KeyError: pass
                sec+=float(parsed['hours'])*3600.0
            except KeyError: pass
            try: sec+=float(parsed['minutes'])*60.0
            except KeyError: pass
            try: sec+=float(parsed['seconds'])
            except KeyError: pass
        #seeing problem of 1 1 1990 12:00:00.00 changing to 11:60:00.0  in PyTmStoHMSX
        h,m,ns,x=UTC.PyTmStoHMSX(sec)
        s=ns+x
        if year < 100:  # use zero-padding if we have a 2-digit year
            year='%02d'%year
        else:
            year=str(year)
        timeStr = year+'-%03d'%doy+'.'+"%02d:%02d:%06.3f"%(h,m,s)
        if int(year)<100:
            if int(year)<50:
                yr=int(year)+2000
            else:
                yr=int(year)+1900
        else:
            yr=int(year)
        mon, day = UTC.PyTmYJDtoMD(yr, doy)
        dt = datetime.datetime(yr, mon, day, h,m,ns,int(x*1000000))
    return timeStr, dt

class GenericTextReader(object):
    #self.Data holds the parsing parameters (column or field number, delimiter etc) for the file to be read.
    #self.DefaultDta holds a starting point for the self.Data.
    #self.FunctionsAndControls holds the gui widgets that represent each item in self.Data and callable functions used to set the data
    #self.Categories just combines self.Data and self.FunctionsAndControls so they are matched.
    
    
    USE_OR_REQUIRED,RANK,DELIM,FIELD_NUM,START_COL,END_COL,NAMED_FIELD,ADV_BUTTON,SAMPLE_DATA,ADV_FUNC,DEF_VALUE,MOD_SCRIPT,SET_FUNC = range(13) # corresponds to length of a self.FunctionsAndCtrls.values()(see __init__(), below; ordering must match!)
    LATDATATYPE_STR,LONDATATYPE_STR,OLATDATATYPE_STR,OLONDATATYPE_STR = "Lat/Northing","Lon/Easting","Obs Lat/N","Obs Lon/E"
    NUM_CTRLS = 9 #number of controls per feature field on dialog
    COORDTYPE,ZONE,RADIANS,CALCRB = 0,1,2,3
    UNITS,FACTOR = 0,1
    DATA_LINES = 25
    DBFIELD_DELIM=';'
    ADODB_TYPES = ("MS Excel|*.xls","dBASE|*.dbf","MS Access|*.mdb")
    OGRDB_TYPES = ("MapInfo Interchange Format|*.mif;*.mid;*.tab","ESRI Shapefile|*.shp")
    DB_TYPES = ADODB_TYPES + OGRDB_TYPES
    ADODB_EXT,OGRDB_EXT = (".xls",".dbf",".mdb"),(".mif",".mid",".tab",".shp",".gml",".kml") # note: all lower case
    def RankOrderedList(self):
        def cmp1(x,y):
            if x[1][0][self.RANK]<y[1][0][self.RANK]: return -1
            else: return 0
        l=self.Categories.items()
        l.sort(cmp1)
        return l
    def __init__(self):
        #separating the category data from the controls so that we can pickle the categories for template creation
        
        self.ver = 8
        self.NamedDelim=""
        self.NamedChoices=[]
        self.HeaderTxt="1"
        self.MultiDelim=False
        self.InsertAs="GPs"
        self.RetainDBRecordsetData=False
        self.UseS57AttrData=False
        self.S57ObjectClass=""  # use string vice id, as choice could change in the future--with name being more stable than index
        self.UsePointGeomData=False
        self.FileDisplay=""
        self.openedfile=""
        self.Description="Text Format Description"

        self.DefaultData={
            self.LATDATATYPE_STR:[-1,0,"","","","","","LL/UTM","NA",[0,8,0,0],"",""],
            self.OLATDATATYPE_STR:[-1,10,"","","","","","LL/UTM","NA",[0,8,0,0],"",""],
            self.LONDATATYPE_STR:[-1,5,"","","","","","LL/UTM","NA",[0,8,0,0],"",""],
            self.OLONDATATYPE_STR:[-1,15,"","","","","","LL/UTM","NA",[0,8,0,0],"",""],
            "THU (TPEh)":[0,16,"","","","","","Units","NA",["Meters",1],"",""],
            "Time":[1,20,"","","","","","Format","NA",["MO DAY YR h m s","",""],"1 1 1990 12:00:00.00",""],
            "Depth":[0,25,"","","","","","Units","NA",["Meters",1],"",""],
            "ObsDepth":[0,30,"","","","","","Units","NA",["Meters",1],"",""],
            "TVU (TPEv)":[0,31,"","","","","","Units","NA",["Meters",1],"",""],
            "Height":[0,35,"","","","","","Units","NA",["Meters",1],"",""],
            "Remarks":[0,40,"","","","","","Adv","NA",[],"",""],
            "Recommends":[0,45,"","","","","","Adv","NA",[],"",""],
            "Display Name":[0,50,"","","","","","Adv","NA",[],"",""],
            "Office Notes":[0,55,"","","","","","Adv","NA",[],"",""],
            "Range":[0,60,"","","","","","Units","NA",["Meters",1],"",""],
            "Azimuth":[0,65,"","","","","","Adv","NA",[],"",""],
            "Tide":[0,80,"","","","","","Units","NA",["Meters",1],"",""],
            "<Filter>":[0,99,"","","","","","Adv","NA",[],"",""],
            }
        self.Data=copy.copy(self.DefaultData)
        self.InitNamedFields()
        layout=[None, None, None, None, None, None, None, None, None] #See DataDictionary for how to set this up -- a control for each data field
        self.FunctionsAndControls={
            self.LATDATATYPE_STR:copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Latitude',val)], #+["Dec Deg", "DMS (:;.)"]
            self.OLATDATATYPE_STR:copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('ObsLatitude',val)],#+["Dec Deg", "DMS (:;.)"]
            self.LONDATATYPE_STR:copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Longitude',val)],#+["Dec Deg", "DMS (:;.)"]
            self.OLONDATATYPE_STR:copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('ObsLongitude',val)],#+["Dec Deg", "DMS (:;.)"]
            "THU (TPEh)":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('THU',val)],
            "Time":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Time',val)],#+["UTCSec80", "HMS (:;.)"]
            "Depth":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Depth',val)],
            "ObsDepth":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('ObsDepth',val)],
            "TVU (TPEv)":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('TVU',val)],
            "Height":copy.copy(layout)+[None,None, None, lambda con, pt, val: con.setdefault('Height',val)],
            "Remarks":copy.copy(layout)+[None,None, None, lambda con, pt, val: con.setdefault('Remarks',val)],
            "Recommends":copy.copy(layout)+[None,None, None, lambda con, pt, val: con.setdefault('Recommendations',val)],
            "Display Name":copy.copy(layout)+[None,None, None, lambda con, pt, val: con.setdefault('DisplayName',val)],
            "Office Notes":copy.copy(layout)+[None,None, None, lambda con, pt, val: con.setdefault('Other',val)],
            "Range":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Range',val)],
            "Azimuth":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Azimuth',val)],
            "Tide":copy.copy(layout)+[None,None, None, lambda con, pt, val: pt.setdefault('Tide',val)],
            "<Filter>":copy.copy(layout)+[None,None, None, lambda con, pt, val: None],
            }


    def MakeCategories(self):
        # build a combined dictionary for convenience  
        # can modify either the Categories dictionary or the underlying Data/Functions dictionaries        
        self.Categories={} 
        for k in self.Data.keys():
            try:
                self.Categories[k]=[self.Data[k], self.FunctionsAndControls[k]]
            except KeyError: #watch for any fields removed from the parser
                print k, "is no longer supported in the feature import"
                del self.Data[k]
        for k in self.FunctionsAndControls.keys(): #give a default value to any new fields in the parser
            if not self.Data.has_key(k):
                print k, "not in the template - giving a default value"
                self.Data[k]=self.DefaultData[k]
                self.Categories[k]=[self.Data[k], self.FunctionsAndControls[k]]
    def InitNamedFields(self,NamedDelim="",NamedChoices=[]):
        self.NamedDelim = NamedDelim
        self.NamedChoices = NamedChoices
    def CompiledTimeRE(self):
        """ Return the compiled regular expression for the selected time parsing format """
        cat=self.Data["Time"]
        expressions=cat[self.ADV_FUNC]
        if expressions[0]=="Regular Expression":
            regexp=expressions[2]
        else:
            if expressions[0]=="Custom":
                strn=expressions[1]
            else:
                strn=expressions[0]
            regexp=""
            params=strn.split()
            for p in params:
                regexp+=REGS[p]
        return re.compile(regexp, re.VERBOSE)

    def __dbfieldtostr(self, field, nullreplace=" "):
        if not field and field!=0:
            rstr=nullreplace
        elif hasattr(field,'Format'): # handle ADO zero-Date (12/30/1899) issue; mx.DateTime is robust to "print <badADOdate>" and "str(<badADOdate>)", but will regard year==1899-->no calendar info in field, just HH:MM:SS
            field = DateTime.DateTimeFromCOMDate(field)
            if field.year==1899: # return only HH:MM:SS
                rstr = "%02d:%02d:%02d"%(field.hour,field.minute,field.second)
            else:
                rstr = str(field)
        else: # encode all other field types to 'str' via 'unicode', and replace "invalid" characters (DBFIELD_DELIM, degree symbol & other position formatting)
            try:
                # unicode(field) ->  unicode(str(field)), useful if field of type 'int' & 'float'; OK for 'str' and moot 'unicode'
                rstr = Constants.stripXMLillegalchars(unicode(field).encode('utf-8','ignore'))
            except UnicodeDecodeError: # -> field is 'str' and contains byte ordinal not in range(128)
                pass
            rstr = rstr.replace(self.DBFIELD_DELIM,':').replace('\x0b','').replace('\xb0','')
        return rstr.replace("\r\n","").replace("\r","").replace("\n","") # first saw a "\r\n" in a RSD CEF .shp file field...remove the other <CR>/<LF> for good measure
    def OGRDatasetLineGenerator(self, ogrdataset, nMax=-1):
        for layerIdx in xrange(ogrdataset.GetLayerCount()):
            ogrlayer = ogrdataset.GetLayer(layerIdx)
            ogrlayerdefn = ogrlayer.GetLayerDefn()
            numrecords,numfields = ogrlayer.GetFeatureCount(),ogrlayerdefn.GetFieldCount() # latter assumes homogenous feature records (same fields/length)
            if nMax>=0:
                numrecords = min((nMax, numrecords))
                nMax -= numrecords
            for n in xrange(numrecords):
                feature,fdata = ogrlayer.GetNextFeature(),[]
                if self.NamedChoices:
                    for item in [feature.GetFieldIndex(itemname) for itemname in self.NamedChoices if itemname not in ("GeomType","GeomXYlist")]:
                        fdata.append(self.__dbfieldtostr(feature.GetField(item)))
                else:
                    for item in xrange(numfields):
                        fdata.append(self.__dbfieldtostr(feature.GetField(item)))
                fgeomrefname,fgeomXYlist = self.FetchOGRFeatureGeometry(feature)
                if not fgeomXYlist:
                    fgeomrefname,fgeomXYlist = " "," "
                fdata = self.DBFIELD_DELIM.join((self.DBFIELD_DELIM.join(fdata),fgeomrefname,str(fgeomXYlist)))
                yield (fdata)
    def ADORSLineGenerator(self, adors, nMax=-1):
        numrecords,numfields = adors.RecordCount,adors.Fields.Count
        adors.MoveFirst()
        if nMax>=0: numrecords=min((nMax, numrecords))
        for n in xrange(numrecords):
            data = self.DBFIELD_DELIM.join(map(lambda f:self.__dbfieldtostr(f), map(lambda item: adors.Fields.Item(item).Value, range(numfields))))
            yield (data)
            adors.MoveNext()
    def TextLineGenerator(self, filename, skip):
        for line in self.TextfileReadlineGenerator(filename):
            if skip>0:
                skip-=1
            elif line.strip():
                line=line.replace("\r","").replace("\n","")
                yield (line)
    def TextFieldsGenerator(self, filename, skip):
        geom=None
        fieldsGen = self.TextLineGenerator(filename, skip)
        for fields in fieldsGen:
            yield (fields,geom)
    def OGRDatasetFieldGenerator(self, ogrdataset, skip=0, startIdx=0):
        cachedData,cachedNamedChoices = copy.copy(self.Data),copy.copy(self.NamedChoices)
        for layerIdx in xrange(ogrdataset.GetLayerCount()):
            ogrlayer = ogrdataset.GetLayer(layerIdx)
            oAcronym = ogrlayer.GetName()
            if oAcronym not in NOAAcarto.s57noaafeatures:
                oAcronym = None
            numrecords = ogrlayer.GetFeatureCount()
            ogrlayerdefn = ogrlayer.GetLayerDefn()
            ogrlayerNamedChoices = [ogrlayerdefn.GetFieldDefn(idx).GetName() for idx in xrange(ogrlayerdefn.GetFieldCount())]
            # change Categories {} Data {} Field Num per Named Field (re)ordering in ogr layer to maintain 1:1 mapping
            self.NamedChoices = ogrlayerNamedChoices
            for v in self.Data.itervalues():
                currFieldNum,currNamedField = v[self.FIELD_NUM],v[self.NAMED_FIELD]
                if currFieldNum and currNamedField:
                    try:
                        v[self.FIELD_NUM] = str(ogrlayerNamedChoices.index(currNamedField)+1) # note that getFieldStrings (bound method) parser wants field # as a string, and Data Dictionary parser field indexes are 1-based (not 0)
                    except ValueError:
                        v[self.FIELD_NUM],v[self.NAMED_FIELD] = "",""
            self.MakeCategories() #rebuild combined dictionary containing Data and Windows Controls; note: add'l template specs are not clobbered (e.g., advanced processing scripts)
            if (numrecords-skip) > 0:
                try:
                    for n in xrange(skip+startIdx,numrecords+startIdx):
                        #print "OGR record ",n+1
                        ogrlayerFeature=ogrlayer.GetFeature(n)
                        if ogrlayerFeature: # jlr: added b/c GetFeature(0) returning NoneType for MIF/MID
                            yield ((oAcronym,ogrlayerFeature),self.FetchOGRFeatureGeometry(ogrlayerFeature))
                    skip = 0
                except:
                    traceback.print_exc()
#                    wx.MessageBox("There was an error reading the OGR dataset. \n"+
#                                  "See the console window for more information. ",
#                                  "Error", wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
                    break
            else:
                skip = max(0,skip-numrecords)
            # restore combined dictionary containing Data and Windows Controls from cached copy
            self.NamedChoices,self.Data = cachedNamedChoices,cachedData
            self.MakeCategories()
    def ADORSFieldGenerator(self, adors, skip=0, bEvaluateMP=False, mpFieldName=None, mpPremierPtNum=1, mpLonFieldName=None, mpLatFieldName=None, fgeomrefname=None):
        fgeomXYlist=[]
        numrecords = adors.RecordCount-skip
        if numrecords > 0:
            adors.MoveFirst()
            if skip>0: adors.Move(skip)
            if bEvaluateMP and (mpFieldName in self.NamedChoices) and (mpLonFieldName in self.NamedChoices) and (mpLatFieldName in self.NamedChoices):
                bMultipointCursor = True
            else:
                bMultipointCursor = False
            try:
                recordindex=1
                while recordindex < numrecords:
                    #print "ADO record ",n+skip+1, adors.Fields.Item(0)
                    if bMultipointCursor: # evaluate geometry
                        #data = self.DBFIELD_DELIM.join(map(lambda f:self.__dbfieldtostr(f), map(lambda item: adors.Fields.Item(item).Value, range(numfields))))
                        rsFieldsItem = adors.Fields.Item
                        fgeomXYlist.append((rsFieldsItem(mpLonFieldName).Value, rsFieldsItem(mpLatFieldName).Value)) # x,y
                        adors.MoveNext()
                        recordindex += 1
                        while rsFieldsItem(mpFieldName).Value!=1 and recordindex < numrecords:
                            fgeomXYlist.append((rsFieldsItem(mpLonFieldName).Value, rsFieldsItem(mpLatFieldName).Value)) # x,y
                            adors.MoveNext()
                            recordindex += 1
                        if rsFieldsItem(mpFieldName).Value==1: # back up to last pt in multipt...
                            adors.MovePrevious()
                        else: #...otherwise, end of file; stay put and append last pt
                            fgeomXYlist.append((rsFieldsItem(mpLonFieldName).Value, rsFieldsItem(mpLatFieldName).Value)) # x,y
                    yield (adors.Fields,(fgeomrefname,fgeomXYlist))
                    if bMultipointCursor:
                        fgeomXYlist = []
                        adors.MoveNext()
                    else:
                        recordindex += 1
                        adors.MoveNext()
                if not bMultipointCursor:
                    yield (adors.Fields,(fgeomrefname,fgeomXYlist))
            except:
                traceback.print_exc()
#                 wx.MessageBox("There was an error reading the ADO dataset. \n"+
#                               "See the console window for more information. ",
#                               "Error", wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
    def CarisSVPGenerator(self, filename):
        data,geom = "",None
        srcSVP="source svp file="+filename+"\n"
        version=0
        for line in fileinput.input(filename.encode('utf-8')): # note: fileinput doesn't like unicode; fixed in > Python 2.3?
            if version==0:
                if line.upper().find("[SVP_VERSION_2]")>=0: version=2
            else:
                if data!="" and line.lower().find("section")>=0:
                    yield (data,geom) #return the previous casts data
                    data="" #clear the buffer
                if line.lower().find("section")>=0:
                    #create a semicolon seperator between section header and cast data
                    data+=line.replace('\r','').replace('\n','').replace(';',':')+" ; "
                    while data.find("  ")>=0: data=data.replace("  "," ") #consolidate spaces
                    data+=srcSVP
                elif line[0:5]=="[SVP_":
                    pass #line was a header
                elif line[1:3]==':\\' or line.lower().find('.svp')>=0:
                    srcSVP="source svp file="+line
                else:
                    #append cast data with linefeeds still inplace - going to remarks field where we want linefeeds
                    if data.lower().find("section")>=0: #make sure data has a section header first
                        data+=line.replace(';',':')
        yield (data,geom)
    def VelocWinGenerator(self, filename):
        data,geom = "",None
        for line in fileinput.input(filename.encode('utf-8')): # note: fileinput doesn't like unicode; fixed in > Python 2.3?
            data+=line.replace('\r','').replace('\n','').replace(';',':')+";"
        yield (data,geom)
    def VelocwinDiveDPGenerator(self, filenames):
        for filename in filenames:
            for datageomTuple in self.VelocWinGenerator(filename):
                yield datageomTuple
    def TextfileReadlineGenerator(self, filename):
        f=open(filename,"r")
        # first, check for unicode--detect byte order mark...
        data,bUni = f.readline(),False
        for sEnc,uBOM in [("%s_%s"%(sBOM[4:7],sBOM[7:]),getattr(codecs,sBOM)) for sBOM in ("BOM_UTF8","BOM_UTF16_LE","BOM_UTF16_BE","BOM_UTF32_LE","BOM_UTF32_BE")]:
            if data.startswith(uBOM):
                bUni=True
                break
        if bUni:
            f=codecs.open(filename,'r',sEnc)
            f.read(len(uBOM))
        else:
            f.seek(0)
        for data in [dataLine for dataLine in f.readlines() if dataLine]:
            yield data

    def SaveTemplate(self, filename):
        fil=open(filename, "w+")
        ver=8
        cPickle.dump(ver, fil)
        cPickle.dump(self.NamedDelim, fil)
        cPickle.dump(self.NamedChoices, fil)
        cPickle.dump(self.Data, fil)
        cPickle.dump(self.HeaderTxt, fil)
        cPickle.dump(self.MultiDelim, fil)
        cPickle.dump(self.InsertAs, fil)
        cPickle.dump(self.RetainDBRecordsetData, fil)
        cPickle.dump(self.UseS57AttrData, fil)
        cPickle.dump(self.S57ObjectClass, fil) # use string vice id, as choice could change in the future--with name being more stable than index
        cPickle.dump(self.UsePointGeomData, fil)
        cPickle.dump(self.FileDisplay, fil)
        cPickle.dump(self.openedfile, fil)
        cPickle.dump(self.Description, fil)
        
    def OpenTemplate(self, filename):
        fil=open(filename, "r")
        ver=cPickle.load(fil)
        self.NamedDelim = cPickle.load(fil)
        self.NamedChoices = cPickle.load(fil)
        self.Data = cPickle.load(fil)
        self.MakeCategories() #rebuild combined dictionary containing Data and Windows Controls
        if ver==1:
            self.SoundingFactor = cPickle.load(fil) #garbage
            self.HeaderTxt="1"
            self.MultiDelim=False
        elif ver==2:
            self.HeaderTxt=cPickle.load(fil)
            self.MultiDelim=cPickle.load(fil)
        elif ver==3:
            self.HeaderTxt=cPickle.load(fil)
            self.MultiDelim=cPickle.load(fil)
            if cPickle.load(fil): txtInsertAs="Chart GPs"
            else: txtInsertAs="GPs"
            self.InsertAs=txtInsertAs
        elif ver==4:
            self.HeaderTxt=cPickle.load(fil)
            self.MultiDelim=cPickle.load(fil)
            bAsChartGPs=cPickle.load(fil)
            self.RetainDBRecordsetData=cPickle.load(fil)
            if bAsChartGPs: txtInsertAs="Chart GPs"
            else: txtInsertAs="GPs"
            self.InsertAs=txtInsertAs
        elif ver in (5, 6):
            self.HeaderTxt=cPickle.load(fil)
            self.MultiDelim=cPickle.load(fil)
            bAsChartGPs=cPickle.load(fil)
            bAsCheckpoints=cPickle.load(fil)
            self.RetainDBRecordsetData=cPickle.load(fil)
            self.UseS57AttrData=cPickle.load(fil)
            self.S57ObjectClass=cPickle.load(fil)
            self.UsePointGeomData=cPickle.load(fil)
            self.FileDisplay=cPickle.load(fil)
            self.openedfile = cPickle.load(fil)
            if ver==5:
                if bAsChartGPs: txtInsertAs="Chart GPs"
                elif bAsCheckpoints: txtInsertAs="Checkpoints"
                else: txtInsertAs="GPs"
            elif ver==6:
                bAsDPs=cPickle.load(fil)
                if bAsDPs: txtInsertAs="DPs"
                elif bAsChartGPs: txtInsertAs="Chart GPs"
                elif bAsCheckpoints: txtInsertAs="Checkpoints"
                else: txtInsertAs="GPs"
            self.InsertAs=txtInsertAs
        elif ver in (7,8):
            self.HeaderTxt=cPickle.load(fil)
            self.MultiDelim=cPickle.load(fil)
            self.InsertAs=cPickle.load(fil)
            self.RetainDBRecordsetData=cPickle.load(fil)
            self.UseS57AttrData=cPickle.load(fil)
            self.S57ObjectClass=cPickle.load(fil)
            self.UsePointGeomData=cPickle.load(fil)
            self.FileDisplay=cPickle.load(fil)
            self.openedfile = cPickle.load(fil)
            if ver==8:
                self.Description = cPickle.load(fil)
        
        
    def GetFieldStringsFromText(self, txt, category):
        if category[self.START_COL] and category[self.END_COL]: #use fixed columns
            data = txt[int(float(category[self.START_COL])):int(float(category[self.END_COL]))] #slice the data
            #print txt
            #print category[self.START_COL],category[self.END_COL], txt[int(float(category[self.START_COL])):int(float(category[self.END_COL]))]
        elif category[self.DELIM] and category[self.FIELD_NUM]: #highlight delimited fields
            #should really convert to regex for this whole routine
            #d = ctrls[self.DELIM].GetValue()
            #for fld in ctrls[self.FIELD_NUM].GetValue().split(","):
            #d,f= category[self.DELIM], int(float(category[self.FIELD_NUM]))
            d = category[self.DELIM]
            pos=[-1] # prepend the beginning of line
            bIgnoreMultiDelim = self.bIgnoreMulti
            if bIgnoreMultiDelim: #cheap way of getting rid of duplicate delimeters
                while txt.find(d+d)>=0: txt=txt.replace(d+d,d)
            while txt.find(d, pos[-1]+1)>=0:
                pos.append(txt.find(d, pos[-1]+1)) #append position of delimiters
            pos.append(len(txt)) #append the end of line
            try:
                datalist=[]
                for fld in category[self.FIELD_NUM].split(","):
                    f=int(fld.lower().replace("e",""))
                    if "e" in fld.lower(): end=pos[-1] #end of the line
                    else: end=pos[f]
                    datalist.append(txt[pos[f-1]+1:end])
                data=d.join(datalist)
            except:
                print "*** Invalid Text Field Num = %s in %s"%(category[self.FIELD_NUM],category[self.RANK]) # bad field - doesn't exist in record
                data = ""
        else:
            data = ""
        return data
    
    def FetchOGRFeatureGeometry(self, ogrlayerFeature):
        """returns tuple (geometry type/name, XY tuple list)"""
        #"""sets attributes fgeomrefname,fgeomXYlist (geometry type/name & XY tuple list)"""
        try:
            fgeomref = ogrlayerFeature.GetGeometryRef()
            fgeomrefname = fgeomref.GetGeometryName() #e.g., "POINT","LINESTRING","MULTIPOINT","POLYGON",...
            try:
                if fgeomref.GetGeometryCount()>0: fgeomref=fgeomref.GetGeometryRef(0) #todo: multiple linear rings in "POLYGON"--GML geometry schema?
                fgeomXYlist = map(lambda idx: (fgeomref.GetX(idx),fgeomref.GetY(idx)), range(fgeomref.GetPointCount()))
            except:
                fgeomXYlist = []
        except:
            fgeomrefname,fgeomXYlist = "",[]
        return (fgeomrefname,fgeomXYlist)
    def GetFieldStringsFromOGR(self, ogrlayerFeature, category):
        if category[self.DELIM] and category[self.FIELD_NUM]: # ADO/OGR data fields parsed via delimited text, not fixed start/end columns
            try:
                datalist=[]
                for fld in category[self.FIELD_NUM].split(","):
                    f=int(fld)-1 #adjust for the database having a zero based index
                    fmax=ogrlayerFeature.GetFieldCount()
                    if f < fmax: # => Feature data fields...
                        val=ogrlayerFeature.GetField(f)
                        val = self.__dbfieldtostr(val, nullreplace="")
                    else: # ...else in GeometryRef portion of category field parsing--todo: this is currently unused
                        g=f-fmax
                        fgeomrefname,fgeomXYlist = self.FetchOGRFeatureGeometry(ogrlayerFeature)
                        if g==0: # (want geometry type/name)
                            val=fgeomrefname
                        elif g==1: # (want geometry XY tuple list)
                            val=str(fgeomXYlist) # use eval(val) to get XY tuple list back
                    datalist.append(val)
                data=self.DBFIELD_DELIM.join(datalist)
            except:
                print "*** Invalid OGR Field Num %s"%str(fld) # bad field - doesn't exist in record
                data = ""
        else: # no delimited fields specified; don't worry about msg to user at this point because this is really caught upstream, in OnProcess()
            data = ""
        return data
    def GetFieldStringsFromADORS(self, adorsFields, category):
        if category[self.DELIM] and category[self.FIELD_NUM]: # ADO/OGR data fields parsed via delimited text, not fixed start/end columns
            try:
                datalist=[]
                for fld in category[self.FIELD_NUM].split(","):
                    f=int(fld)-1 #adjust for the database having a zero based index
                    val=adorsFields.Item(f).Value 
                    val = self.__dbfieldtostr(val, nullreplace="")
                    datalist.append(val)
                data=self.DBFIELD_DELIM.join(datalist)
            except:
                print "*** Invalid ADO Field Num %s"%str(fld) # bad field - doesn't exist in record
                data = ""
        else: # no delimited fields specified; don't worry about msg to user at this point because this is really caught upstream, in OnProcess()
            data = ""
        return data
    def ConvertCarisSVP(self, xmlobj, sourcePath, sourceName):
        fieldsAndGeomGen = self.CarisSVPGenerator(sourcePath)
        getFieldStrings = self.GetFieldStringsFromText
        bOk,numfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs=False)
        if numfeatures > 0:
            self.ConvertLineData(xmlobj, sourceName)
    def ConvertVelocWin(self, xmlobj, sourcePath, sourceName):
        fieldsAndGeomGen = self.VelocWinGenerator(sourcePath)
        getFieldStrings = self.GetFieldStringsFromText
        bOk,numfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs=False)
        if numfeatures > 0:
            self.ConvertLineData(xmlobj, sourceName)
    def ConvertVelocwinDiverLDReportDPs(self, xmlobj, filenames, pathToPVDL):
        fieldsAndGeomGen = self.VelocwinDiveDPGenerator(filenames)
        getFieldStrings = self.GetFieldStringsFromText
        bOk,numfeatures = self.ParseLineData(xmlobj, pathToPVDL, fieldsAndGeomGen, getFieldStrings, bAsDPs=True)
        if numfeatures > 0:
            self.ConvertLineData(xmlobj, pathToPVDL, bAsDPs=True, bTimeSortCon=True)
    def ConvertPathfinderDatabaseGPsDPs(self, xmlobj, sourcePath, sourceNameGPs, sourceNameDPs, skip=0):
        bTides,SQLstmts = [],[]
        bOstensiblyAsGPs,bOstensiblyAsDPs = sourceNameGPs!=[],sourceNameDPs!=[] # won't know what we really have until gen_ADORecordsetsViaMSJetProvider(f(tables,SQLstmt)) below
        if bOstensiblyAsGPs and bOstensiblyAsDPs:
            bTides=[0,1]
        elif bOstensiblyAsGPs:
            bTides=[0]
        else: #elif bOstensiblyAsDPs:
            bTides=[1]
        for bTide in bTides:
            SQLstmts.append("SELECT * FROM [%s] WHERE [Tide - DP/GP] = "+"'%d'"%bTide)
        pathfinderRSgen = ContactFunctions.gen_ADORecordsetsViaMSJetProvider(sourcePath,SQLstmts,parentwin=self)
        #try: bTidePrev=bTides[0]
        #except: bTidePrev=None
        bTidePrev,tblsheetNamePrev,bIncomingDataPrev = None,None,None
        getFieldStrings = self.GetFieldStringsFromADORS
        # fundamental attributes common to all Pathfinder MDB tables
        # note that these are included in TrimblePathfinderDBbase.parser template, and template includes (e.g.) RECDAT,Time advanced script
        dtypenames = [self.LATDATATYPE_STR,self.OLATDATATYPE_STR,self.LONDATATYPE_STR,self.OLONDATATYPE_STR,"Time","Remarks","Display Name"]
        pathfindernames = ["Latitude","Latitude","Longitude","Longitude",("RECDAT","Time"),"Remarks","UserID"] # 1:1 with dtypenames
        numfeatures,parsedfeatures = 0,0
        for SQLstmt,tblsheetName,adors in pathfinderRSgen: # note: db table choice dialog happens here, not in pathfinderRSgen instantiation above
            bTide = int(SQLstmt.split()[-1].replace("'",""))
            numrecords,numfields = adors.RecordCount,adors.Fields.Count
            bIncomingData = numrecords > 0
            bParse = bIncomingData
            bObjTypeToggle = tblsheetName!=tblsheetNamePrev
            bRefreshParams = bIncomingData and bObjTypeToggle
            bConTypeChange = (bTidePrev!=None) and (bTide!=bTidePrev) # will convert any data on type GP/DP change
            bConvert = bIncomingDataPrev and bConTypeChange
            if bConvert:
                if bTidePrev:
                    sourceName = sourceNameDPs
                else:
                    sourceName = sourceNameGPs
                self.ConvertLineData(xmlobj, sourceName, bAsDPs=bTidePrev, bTimeSortCon=bTidePrev)
                xmlobj = PyPeekXTF.CContactsFile()
                xmlobj.Open("")
                numfeatures,parsedfeatures = 0,0
                bTidePrev,tblsheetNamePrev,bIncomingDataPrev = None,tblsheetName,None
            if bRefreshParams:
                oAcronym,fgeomrefname = None,None
                namingData = tblsheetName.split('_')
                try: # Pathfinder table naming XXXXXX_[P,L,A], or other (e.g. "GenLine", "GenArea")
                    oAcronym = namingData[0]
                    fgeomrefname = ("POINT","MULTIPOINT","POLYGON")[["P","L","A"].index(namingData[-1])]
                except:
                    try:
                        oAcronym = None # todo: or "$CSYMB"?
                        fgeomrefname = ("MULTIPOINT","POLYGON")[["GenLine","GenArea"].index(namingData[0])]
                    except:
                        pass
                # seed Categories {} with changes in fundamental attributes--but (possibly) having different column indicies
                self.InitNamedFields(self.DBFIELD_DELIM,map(lambda idx,fielditem=adors.Fields.Item: fielditem(idx).Name, range(numfields)))
                for dname,pfinders in zip(dtypenames,pathfindernames):
                    if dname!="Time":
                        self.Data[dname][self.FIELD_NUM] = str(self.NamedChoices.index(pfinders)+1) # note that getFieldStrings (bound method) parser wants field # as a string, and Data Dictionary parser field indexes are 1-based (not 0)
                    else:
                        self.Data[dname][self.FIELD_NUM] = ",".join([str(self.NamedChoices.index(pfinder)+1) for pfinder in pfinders])
                self.MakeCategories() #rebuild combined dictionary containing Data and Windows Controls; note: add'l template specs are not clobbered (e.g., advanced processing scripts)
            if bParse:
                if bTide:
                    sourceName = sourceNameDPs
                else:
                    sourceName = sourceNameGPs
                if fgeomrefname in ("MULTIPOINT","POLYGON"):
                    fieldsAndGeomGen = self.ADORSFieldGenerator(adors, skip, bEvaluateMP=True, mpFieldName="Position_ID", mpLonFieldName="Longitude", mpLatFieldName="Latitude", fgeomrefname=fgeomrefname)
                    bUsePtGeomData = True
                else:
                    fieldsAndGeomGen = self.ADORSFieldGenerator(adors, skip)
                    bUsePtGeomData = False
                # TO DO: what about not bOk (bCriticalParserException) when bAsDPs (=bTide)
                bOk,parsedfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bTide, bUsePtGeomData, bUseS57AttrData=True, oAcronym=oAcronym)
                numfeatures+=parsedfeatures
                bTidePrev,tblsheetNamePrev,bIncomingDataPrev = bTide,tblsheetName,True
        if bIncomingDataPrev:
            self.ConvertLineData(xmlobj, sourceName, bAsDPs=bTide, bTimeSortCon=bTide) # convert any remaining data; sourceName and bTide per last parse
    def ConvertADOdb(self, xmlobj, sourcePath, sourceName, bAsDPs, bUseS57AttrData, oAcronym, bRetainADORecordset, skip=0):
        tblsheetName,adoconn,adors = ContactFunctions.GetADOConnectionViaMSJetProvider(sourcePath, parentwin=self)
        if adors:
            adors.SetActiveConnection(None)    # disconnect recordset from conn
            adoconn.Close()
            del adoconn
            numfields = adors.Fields.Count
            #numrecords = adors.RecordCount
            #if numrecords > 0: # todo: necessary?; see ConvertPathfinderDatabaseGPsDPs
            adors.MoveFirst()
            fieldnames = map(lambda idx,fielditem=adors.Fields.Item: fielditem(idx).Name, range(numfields))
            fieldsAndGeomGen = self.ADORSFieldGenerator(adors, skip)
            getFieldStrings = self.GetFieldStringsFromADORS
            bOk,numfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs, bUseS57AttrData=bUseS57AttrData, oAcronym=oAcronym)
            if (numfeatures > 0) and not (bAsDPs and not bOk):
                self.ConvertLineData(xmlobj, sourceName, bAsDPs, bTimeSortCon=bAsDPs)
                if bRetainADORecordset:
                    returnedData = {'fieldnames':fieldnames,'ADOrecordset':adors}    # note rs is left Open
                    self.PSS.AddGenericADOrecordset(sourceName, returnedData) # todo: some DB recoredsets crash Pydro when EditorNotebook 'i'NFO button is used to bring up grid dialog
    def ConvertOGRdb(self, xmlobj, sourcePath, sourceName, bAsDPs, bUsePtGeomData, bUseS57AttrData, oAcronym, skip=0, startIdx=0):
        ogrdataset,ogrNamedChoices = GetOGRDatasetLayer(sourcePath, parentwin=self)
        if ogrdataset:
            currDataNamedFields = set([v[self.NAMED_FIELD] for v in self.Data.itervalues() if v[self.FIELD_NUM] and v[self.NAMED_FIELD]])
            missingNamedFields = currDataNamedFields.difference(set([namedc for namedc in ogrNamedChoices if namedc]))
            bOK=True
            if currDataNamedFields and missingNamedFields:
                missingNamedFields = list(missingNamedFields)
                missingNamedFields.sort()
#                 bProceed = wx.MessageBox("The named fields in the data set being processed do \n"+
#                                          "not match those in the current data parser template. \n"+
#                                          "The parsed attributes from %s \n"%os.path.basename(sourcePath)+
#                                          "will be limited to those matches in the template: \n"+
#                                          "\n"+
#                                          "Templated fields not present in current dataset layer(s): \n"+
#                                          "   %s \n"%",".join(missingNamedFields)+
#                                          "\n"+
#                                          "Continue with this file? ('No' to skip) \n",
#                                          'Warning: Named Field Mismatch -- Continue with this file?', wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION, self)
#                 if bProceed==wx.NO: bOK=False
            if bOK:
                fieldsAndGeomGen = self.OGRDatasetFieldGenerator(ogrdataset, skip, startIdx)
                getFieldStrings=self.GetFieldStringsFromOGR
                bOk,numfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs, bUsePtGeomData, bUseS57AttrData, oAcronym)
                if (numfeatures > 0) and not (bAsDPs and not bOk):
                    self.ConvertLineData(xmlobj, sourceName, bAsDPs, bTimeSortCon=bAsDPs)
    def ConvertTXT(self, sourcePath, sourceName, bAsDPs, bUseS57AttrData, oAcronym, skip=0):
        fieldsAndGeomGen = self.TextFieldsGenerator(sourcePath, skip)
        getFieldStrings = self.GetFieldStringsFromText
        bOk,results = self.ParseLineDataToDict(sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs, bUseS57AttrData=bUseS57AttrData, oAcronym=oAcronym)
        return bOk,results 

    def ParseString(self, rawstr):
        if "n" in rawstr.lower() or "s" in rawstr.lower():
            dec = coordinates.LatStrToDec(rawstr)
        else:
            dec = coordinates.LonStrToDec(rawstr)
        if dec == None: dec = -999.0
        return dec, rawstr
    def ParseLineDataToDict(self, sourceName,  fieldsAndGeomGen, getFieldStrings, bAsDPs, bUsePtGeomData=False, bUseS57AttrData=False, oAcronym=None, Username="", bIgnoreMulti=False):
        #print "Removed Flags = QUA3STATUS"
        #print "changed how user is passed in."
        #print "need to sync the mutlidelim checkbox to the self.multi"
        self.bIgnoreMulti=bIgnoreMulti
        
        # re-entrant/accumulation functionality via single line in xmlobj argument
        result = OrderedDict()
        if bUsePtGeomData: # set variables for con (multi)pt OGRdb data conversion
            positionSettings = self.Data[self.LATDATATYPE_STR][self.ADV_FUNC]
            if positionSettings[self.COORDTYPE]==0:
                bInUTM = False
                if positionSettings[self.RADIANS]==0:
                    bInRAD = False
                else:
                    bInRAD = True
            else: # COORDTYPE==1 (UTM)
                bInUTM,zoneUTM,bInRAD = True,positionSettings[self.ZONE],False
        if bUseS57AttrData:
            fakecategorydata = (max(self.DELIM,self.FIELD_NUM)+1)*[None]
            fakecategorydata[self.DELIM] = self.DBFIELD_DELIM
            if oAcronym:
                aAcronymsNOAA = set(itertools.chain(*NOAAcarto.s57noaafeatures[oAcronym]))
        bCriticalParserException,bAnySkipped,bAnyFiltered = False,False,False
        #categoriesL=self.RankOrderedList() # ordered list for consistent feature data record access, fwiw (?)
        #namesL=[itm[0] for itm in categoriesL]
        recIdx=1
        currUser,currTimeStr = Username,"%.0f"%time.time()
        oAcronymPrev = oAcronym 
        if bAsDPs:
            contype="DP"
            defaultVCF = sourceName.split('/')[-3]
        else: #bAsChartGPs, bAsCheckpoints, or [generic] GPs
            contype="GP"

        for featureStuff,featureGeom in fieldsAndGeomGen:
            con = {}
            try:
                oAcronym,feature = featureStuff
                if oAcronym != oAcronymPrev:
                    aAcronymsNOAA = set(itertools.chain(*NOAAcarto.s57noaafeatures[oAcronym]))
            except:
                feature = featureStuff
            con['raw']=str(feature)
            bFilteredRecord = False
            conNumStr = str(recIdx)
            if bAsDPs:
                conNumStr+='/1' # DPs use pseudo profile/beam
            result[conNumStr]=con # ConvertData() will override con name subsequent to (any) (re)sort
            con['Type']=contype # "GP" or "DP", per above
            #con['Flags']= "%08x"%HDCSio.QUA3_STATUS  # Initialize items to be unrejected w/quality=3
            pt={}
            con['Points']={"1":pt} # need a point even if bUsePtGeomData, as other attributes need access to a point structure
            if bAsDPs:
                con['VesselHeading']='000' # todo: add to parser dialog
                con['VesselName']=defaultVCF
                con['TGTEvent'] = str(recIdx)
                pt['Profile']=str(recIdx)
                pt['Beam']='1'
            UTMDict={}
            for name, [data, ctrls] in self.Categories.iteritems():#categoriesL:
                bIsPosField = name in (self.LATDATATYPE_STR,self.LONDATATYPE_STR,self.OLATDATATYPE_STR,self.OLONDATATYPE_STR)
                if not (bUsePtGeomData and bIsPosField): # (will do con (multi)pt data later)
                    if data[self.USE_OR_REQUIRED]:
                        val = getFieldStrings(feature, data)
                    else:
                        val = data[self.DEF_VALUE]
                    try:
                        exec data[self.MOD_SCRIPT] # function of val; user scripts also have access to con & pt object-namespace (to the extent of having attributes, a priori)
                    except:
                        print "-"*15, "User Script Exception", "-"*15
                        traceback.print_exc()
                    if name=="<Filter>":
                        try: # e.g., to prevent "SyntaxError: unexpected EOF while parsing" with Trimble-Pathfinder .mdb data
                            if eval(str(val)):
                                bFilteredRecord,bAnyFiltered = True,True
                                print "Skipped filtered feature record %d"%recIdx
                                result.popitem() #con.Remove()
                                if not bAsDPs:
                                    recIdx+=1 # but retain GP numbering--filtered GP number(s) are skipped in PSS
                                break # for name, [data, ctrls] in self.Categories.iteritems()--then (below) continue for feature,featureGeom in fieldsAndGeomGen
                        except:
                            pass
                    if val: #don't allow null strings
                        try:
                            if name == "Time":
                                exp = self.CompiledTimeRE()
                                val = ParseTime(exp, val)
                                if val[0]=="TimeParseFailed":
                                    raise ValueError
                            if data[self.ADV_BUTTON]=="Units":
                                val = str(float(val)*data[self.ADV_FUNC][self.FACTOR])
                            elif name in (self.LATDATATYPE_STR,self.LONDATATYPE_STR,self.OLATDATATYPE_STR,self.OLONDATATYPE_STR):
                                if data[self.ADV_FUNC][self.COORDTYPE]==0:
                                    if data[self.ADV_FUNC][self.RADIANS]==0:
                                        deg,strin = self.ParseString(val)
                                        val = str(deg)
                                    else:
                                        val = str(float(deg)*RAD2DEG)
                                else:
                                    UTMDict[name] = [float(val), data[self.ADV_FUNC][self.ZONE], ctrls[self.SET_FUNC]]
                            if not UTMDict: # if any field category other position type--wherein ADV_FUNC/COORDTYPE transformation involved--set con/pt data
                                ctrls[self.SET_FUNC](con, pt, val)
                        except ValueError:
                            print "-"*15, "Parser Exception", "-"*15
                            print "Check data file: %s"%sourceName
                            traceback.print_exc()
                            if data[self.USE_OR_REQUIRED]:
                                bCriticalParserException=True
                                break # for name, [data, ctrls] in self.Categories.iteritems()--then (below) break for feature,featureGeom in fieldsAndGeomGen
                    elif bAsDPs: # and empty val; override DP data with null values
                        if name=="ObsDepth":
                            pt['ObsDepth']=NULLDEPTHstr
                        elif name=="Time":
                            pt['Time']=NULLTIMEstr
            if bCriticalParserException:
                break # for feature,featureGeom in fieldsAndGeomGen
            if bFilteredRecord:
                continue # for feature,featureGeom in fieldsAndGeomGen
            if bUseS57AttrData and oAcronym:
                aAcronyms = set(self.NamedChoices).intersection(aAcronymsNOAA) # see declarations above feature for-loop
                if aAcronyms:
                    s57data = {oAcronym:{}}#aAcronym:[<data>,...]}}
                    for aAcronym in aAcronyms:
                        fakecategorydata[self.FIELD_NUM] = str(self.NamedChoices.index(aAcronym)+1) # note that getFieldStrings (bound method) parser wants field # as a string, and Data Dictionary parser field indexes are 1-based (not 0)
                        valStr = getFieldStrings(feature, fakecategorydata)
                        if valStr: # S-57 attribute data can trump XML data, notwithstanding that otherwise configured for parsing--as per idiot box in OnProcess()
                            # VALSOU<--con/pt depth is statically linked
                            # i.e., always mapped from item data--not changeable from S-57 editor
                            # Also, no need to instantiate S-57 XML attribute data for these--handled in PSSObject.SynchronizePSSFeaturesWithHDCS()
                            if aAcronym=="VALSOU":
                                pt['Depth']=valStr
                                obsDepthStr = pt.get('ObsDepth', NULLDEPTHstr)
                                if obsDepthStr==NULLDEPTHstr:
                                    pt['ObsDepth']=valStr
                            try:
                                s57data[oAcronym][aAcronym] = NOAAcarto.GetS57AcronymDataFromNominalValue(aAcronym, valStr)
                            except:
                                print "*** Skipping INVALID S-57 object/attribute '%s/%s' value(s)=%s for %s - %s"%(oAcronym,aAcronym,valStr,cl.GetName()[-1],conNumStr)
                    ContactFunctions.SetS57ContactData(con, s57data, bClearAllExisting=False)
                    ev = con.get('Event',{})
                    ev["UserS57Edit"]=(currUser, currTimeStr)
                    con['Event']=ev
            if not bUsePtGeomData: # (will do con (multi)pt data in else block...)
                #convert UTM positions which require Easting AND Northing to convert to Lat/Lon
                for Nstr,Estr in [[self.LATDATATYPE_STR,self.LONDATATYPE_STR],[self.OLATDATATYPE_STR,self.OLONDATATYPE_STR]]:
                    try: 
                        north,zn,LatFunc = UTMDict[Nstr]
                        east,zn2,LonFunc = UTMDict[Estr]
                        if zn==zn2: #make sure dialogs had the same UTM zone input
                            r,lat,lon = PyUTMToWGS84(zn, east, north,"N")
                            lon*=-1 # Geotrans sign convention is reversed from ours
                            LatFunc(con, pt, str(lat))
                            LonFunc(con, pt, str(lon))
                        else: print "UTM zone mismatch",Nstr,zn,Estr,zn2
                    except KeyError:
                        pass
                        #print Nstr,"LL not UTM"
                Lat,Lon,ObsLat,ObsLon = self.Data[self.LATDATATYPE_STR],self.Data[self.LONDATATYPE_STR],self.Data[self.OLATDATATYPE_STR],self.Data[self.OLONDATATYPE_STR]
                if Lat[self.ADV_FUNC][self.CALCRB] or Lon[self.ADV_FUNC][self.CALCRB]:
                    olat,olon = pt.GetObsLatitudeDouble(),pt.GetObsLongitudeDouble()
                    dist,az = pt.GetRangeDouble(),pt.GetAzimuthDouble()
                    newlat,newlon,baz = PyPeekXTF.PyForwardAzDeg(olat, olon, dist, az)
                    #print olat, olon, newlat, newlon
                    pt['Latitude']=str(newlat)
                    pt['Longitude']=str(newlon)
                elif ObsLat[self.ADV_FUNC][self.CALCRB] or ObsLon[self.ADV_FUNC][self.CALCRB]: # note: calc lat/lon from olat/lon + dist/az mutually exclusive of vice-versa; really should have a validator to prevent user from specifying double (redundant) calc
                    olat,olon = pt.GetLatitudeDouble(),pt.GetLongitudeDouble()
                    dist,az = pt.GetRangeDouble(),pt.GetAzimuthDouble()
                    newlat,newlon,baz = PyPeekXTF.PyForwardAzDeg(olat, olon, dist, az)
                    #print olat, olon, newlat, newlon
                    pt['ObsLatitude']=str(newlat)
                    pt['ObsLongitude']=str(newlon)
            else: # get (multi)pt data from OGR feature geometry ("POINT","LINESTRING","MULTIPOINT","POLYGON",...)
                # note: leaving multipt data in (any) DPs (only pt 0 is [currently] written out to HIPS
                # todo: don't ignore range/azimuth advanced processing prefs
                fgeomrefname,fgeomXYlist = featureGeom
                if bInUTM:
                    #fgeomXYlist = [(-lon,lat) for lat,lon in [PyUTMToWGS84(zoneUTM,east,north,"N")[-2:] for east,north in fgeomXYlist]] # r,lat,lon--lon (-)E <-- PyUTMToWGS84, want [-lon,lat]s--(-)W
                    fgeomXYlist = geodesy.ConvertPointsToLL(fgeomXYlist, zoneUTM)
                elif bInRAD:
                    fgeomXYlist = [(lon*RAD2DEG,lat*RAD2DEG) for lon,lat in fgeomXYlist]
                nPts = len(fgeomXYlist)
                if nPts==1:
                    fgeomrefname="POINT"
                elif nPts==2:
                    fgeomrefname="MULTIPOINT"
                ev = con.get('Event',{})
                ev["pointGeometry"]=(currUser, fgeomrefname)
                con['Event']=ev
                # recall, we already have a pt instance in con for first point
                try:
                    longitude,latitude = fgeomXYlist[0] # get first point, regardless of type
                except IndexError:
                    bAnySkipped=True
                    print "-"*15, "No Geometry Found", "-"*15
                    print "Skipped feature record %d; check data file: %s"%(recIdx,sourceName)
                    result.popitem() #con.Remove()
                    if not bAsDPs:
                        recIdx+=1 # but retain numbering--'bad' GP number(s) are skipped in PSS
                    continue # for feature,featureGeom in fieldsAndGeomGen
                latStr = "%.8f"%latitude
                lonStr = "%.8f"%longitude
                pt['ObsLatitude'] = latStr
                pt['ObsLongitude'] = lonStr
                pt['Latitude'] = latStr
                pt['Longitude'] = lonStr
                # echo following pt "1" attributes to other points (if any) [?add parser support for data lists (a la fgeomXYlist field data) for these?]
                #timeStr,depthStr,odepthStr,rangeStr,azimuthStr,tideStr = pt.GetTime()[1],pt.GetDepth()[1],pt.GetObsDepth()[1],pt.GetRange()[1],pt.GetAzimuth()[1],pt.GetTide()[1]
                if fgeomrefname != "POINT": # look for more points--"2",...,"<n>"
                    if fgeomrefname=="POLYGON": # make sure last point in polygon is equal to first point; if not, create it
                        if ','.join((lonStr,latStr))!="%.8f,%.8f"%fgeomXYlist[-1]:
                            fgeomXYlist.append(fgeomXYlist[0])
                    ptIdx=2
                    for longitude,latitude in fgeomXYlist[1:]: #(already did first pt)
                        latStr = "%.8f"%latitude
                        lonStr = "%.8f"%longitude
                        pt={}
                        con['Points']={str(ptIdx):pt} # need a point even if bUsePtGeomData, as other attributes need access to a point structure
                        pt['Latitude']=latStr
                        pt['Longitude']=lonStr
                        pt['ObsLatitude']=latStr
                        pt['ObsLongitude']=lonStr
                        ptIdx+=1
            recIdx+=1
            oAcronymPrev = oAcronym 
        if bCriticalParserException:
#             wx.MessageBox('Failed to parse required data field "%s" in record #%d. \n'%(name,recIdx)+
#                           "Zero %s inserted.  Check your template and input \n"%(contype+'s')+
#                           "data file and try again. ",
#                           'No %s Inserted -- Critical Parser Error'%(contype+'s'), wx.OK | wx.CENTRE | wx.ICON_ERROR, self)
            print 'Failed to parse required data field "%s" in record #%d. \n'%(name,recIdx)+ "Zero %s inserted.  Check your template and input \n"%(contype+'s')+  "data file and try again. "
            print 'No %s Inserted -- Critical Parser Error'%(contype+'s')
        else:
            msgText = ""
            if bAnySkipped and bAnyFiltered:
                msgText = ("Incomplete data record(s) skipped; also, data records \n"+
                           "filtered.  See Pydro console window for more details. ",)[0]
                msgTitle = "Skipped & Filtered %s Records"%contype
            elif bAnySkipped:
                msgText = ("Incomplete data record(s) skipped.  See \n"+
                           "Pydro console window for error details. ",)[0]
                msgTitle = "Skipped %s Record(s)"%contype
            elif bAnyFiltered:
                msgText = ("Filtered data record(s) skipped.  See \n"+
                           "Pydro console window for more details. ",)[0]
                msgTitle = "Filtered %s Record(s)"%contype
            if msgText:
                #wx.MessageBox(msgText, msgTitle, wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
                print msgText
                print msgTitle
        numfeatures = recIdx-1
        return (not bCriticalParserException, result)
