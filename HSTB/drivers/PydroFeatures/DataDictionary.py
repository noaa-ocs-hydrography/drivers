from __future__ import with_statement

import wx
from TextCtrlNumValidator import *
import os, time
import cPickle
import fileinput
import re
import copy
import traceback

from mx import DateTime
import codecs
import itertools


from DataDictionary_wdr import *
from Cookbook import GetCurrentTimeStr,SortBy
import Constants
import NOAAcarto
import ContactFunctions
import RegistryHelpers
import PSSParamDialog
from HSTPBin import PyPeekXTF
from PyPeekXTF import PyUTMToWGS84
import ProgressProcess
import DegreeParser
from HSTB.time import UTC  

# !!! ogr import must be done AFTER gdal SetConfigOption !!!
import ogr # don't use 'from osgeo import ogr', as Pydro SENCs contain pickled objects of type <class 'ogr.Geometry'>--not <class 'osgeo.ogr.Geometry'>

QUA3_STATUS = PyPeekXTF.OD_DEPTH_QUALITY_0_MASK + PyPeekXTF.OD_DEPTH_QUALITY_1_MASK

_dHSTP=Constants.UseDebug()  # Control debug stuff (=0 to hide debug menu et al from users in the field)
INFINITY = Constants.INFINITY()
RAD2DEG=Constants.RAD2DEG()
DEG2RAD=Constants.DEG2RAD()
FEET2METERS=Constants.FEET2METERS()
FATH2METERS=Constants.FATH2METERS()
METERS2METERS=1.0
NULLDEPTHstr=str(Constants.NULLDEPTH())
NULLTIMEstr='1980-001.00:00:00.000'



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
    return timeStr

def GetOGRDatasetLayer(pathToFile, parentwin=None):
    try:
        ogrdataset = ogr.Open(str(pathToFile))
        # OGR field definitions may change layer-to-layer within a dataset; hence, must normalize NamedChoices to intersection of all
        # OGRDatasetLineGenerator must heed the normalized NamedChoices, sorting output accordingly for 1:1 mapping to user's parsing template
        # ConvertOGRdb may utilize "extra" fields outside of the normalized choices (e.g. changing S-57 attributes) per on-the-fly changes in OGRDatasetFieldGenerator
        # See also handling of on-the-fly field changes in ConvertPathfinderDatabaseGPsDPs
        for layerIdx in xrange(ogrdataset.GetLayerCount()):
            ogrlayer = ogrdataset.GetLayer(layerIdx)
            ogrlayerdefn = ogrlayer.GetLayerDefn()
            ogrlayerNamedChoices = [ogrlayerdefn.GetFieldDefn(idx).GetName() for idx in xrange(ogrlayerdefn.GetFieldCount())]
            try:
                ogrlayerNamedChoicesSet.intersection_update(set(ogrlayerNamedChoices))
            except:
                ogrlayerNamedChoicesSet = set(ogrlayerNamedChoices)
        prefAttrs = ['userid','SORIND','SORDAT','obstim','obsdpt','tidadj','VALSOU','WATLEV','remrks','tidfil']
        prefAttrs = [attr for attr in prefAttrs if attr in ogrlayerNamedChoicesSet.intersection(set(prefAttrs))] # per desired ordering...
        othrAttrs = [attr for attr in ogrlayerNamedChoices if attr in list(ogrlayerNamedChoicesSet.difference(set(prefAttrs)))] # ...otherwise, retain that in field defn  
        othrAttrs.sort()
        return ogrdataset,prefAttrs+othrAttrs+["GeomType","GeomXYlist"]
    except:
        traceback.print_exc()
        wx.MessageBox("There was an error reading the OGR dataset. \n"+
                      "See the console window for more information. ",
                      "Error", wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, parentwin)
        return [None]*3

class DataDictDialogBase(wx.Dialog):
    def __init__(self, parent, dlgtype, catdata):
        wx.Dialog.__init__(self, parent, -1, "Adv. Options", wx.DefaultPosition, wx.Size(400,250), wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.catdata=catdata
        self.Attach(dlgtype)
    def Attach(self, dlgtype):
        self.dlg=dlgtype(self, False)
        self.Defval = self.FindWindowById(ID_DEFAULTVAL)
        self.Script = self.FindWindowById(ID_SCRIPT)
        self.Defval.SetValue(self.catdata[GenericToGPDPDialog.DEF_VALUE])
        self.Script.SetValue(self.catdata[GenericToGPDPDialog.MOD_SCRIPT])
        wx.EVT_BUTTON(self, ID_OKBTN, self.OnOK)
        wx.EVT_BUTTON(self, ID_CANCELBTN, self.OnCancel)
    def OnOK(self, event):
        self.catdata[GenericToGPDPDialog.DEF_VALUE]=self.Defval.GetValue()
        self.catdata[GenericToGPDPDialog.MOD_SCRIPT]=self.Script.GetValue()
        self.EndModal(wx.ID_OK)
    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

class LatLonDlg(DataDictDialogBase):
    def __init__(self, parent, catdata):
        DataDictDialogBase.__init__(self, parent, LatLonUTMDialog, catdata)
        self.SetTitle("Position Parsing Options")
        self.SetSize(wx.Size(240,380))
        self.CoordTypeRadio = self.FindWindowById(ID_COORDTYPE)
        self.CoordTypeRadio.SetSelection(self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.COORDTYPE])
        wx.EVT_RADIOBOX(self, ID_COORDTYPE, self.OnRadio)
        self.ZoneSpin = self.FindWindowById(ID_ZONENUM)
        self.ZoneSpin.SetValue(self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.ZONE])
        self.RadiansCB = self.FindWindowById(ID_RADIANSCB)
        self.RadiansCB.SetValue(self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.RADIANS])
        self.CalcByRange = self.FindWindowById(ID_CALCBYRANGE)
        self.CalcByRange.SetValue(self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.CALCRB])
        self.ChangeEnabled(self.CoordTypeRadio.GetSelection())
    def OnOK(self, event):
        self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.COORDTYPE]=self.CoordTypeRadio.GetSelection()
        self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.ZONE]=self.ZoneSpin.GetValue()
        self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.RADIANS]=self.RadiansCB.GetValue()
        self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.CALCRB]=self.CalcByRange.GetValue()
        DataDictDialogBase.OnOK(self, event)
    def OnRadio(self, event):
        self.ChangeEnabled(event.GetSelection())
    def ChangeEnabled(self, LL_UTM):
        '''Use selection values from the radio box choosing format'''
        if LL_UTM==0:
            self.ZoneSpin.Enable(0)
            self.RadiansCB.Enable(1)
        elif LL_UTM==1:
            self.ZoneSpin.Enable(1)
            self.RadiansCB.Enable(0)

class TimeDlg(DataDictDialogBase):
    def __init__(self, parent, catdata):
        DataDictDialogBase.__init__(self, parent, TimeDialog, catdata)
        self.SetTitle("Time Parsing Options")
        self.SetSize(wx.Size(400,391))
        if self.catdata[GenericToGPDPDialog.ADV_FUNC]:
            self.FormatChoice = self.FindWindowById(ID_FORMATCHOICE)
            self.FormatChoice.SetStringSelection(self.catdata[GenericToGPDPDialog.ADV_FUNC][0])
            self.FormatText = self.FindWindowById(ID_FORMATTEXT)
            self.FormatText.SetValue(self.catdata[GenericToGPDPDialog.ADV_FUNC][1])
            self.ReText = self.FindWindowById(ID_ADVANCEDTEXT)
            self.ReText.SetValue(self.catdata[GenericToGPDPDialog.ADV_FUNC][2])
            self.UseBox = self.FindWindowById(ID_PARSE)
            self.UseBox.SetValue(self.catdata[GenericToGPDPDialog.USE_OR_REQUIRED])
    def OnOK(self, event):
        self.catdata[GenericToGPDPDialog.ADV_FUNC]=[]
        self.catdata[GenericToGPDPDialog.ADV_FUNC].append(self.FormatChoice.GetStringSelection())
        self.catdata[GenericToGPDPDialog.ADV_FUNC].append(self.FormatText.GetValue())
        self.catdata[GenericToGPDPDialog.ADV_FUNC].append(self.ReText.GetValue())
        self.catdata[GenericToGPDPDialog.USE_OR_REQUIRED]=self.UseBox.GetValue()
        DataDictDialogBase.OnOK(self, event)

class UnitsDlg(DataDictDialogBase):
    def __init__(self, parent, catdata):
        DataDictDialogBase.__init__(self, parent, DepthUnitsDialog, catdata)
        self.SetTitle("Time Parsing Options")
        self.SetSize(wx.Size(240,250))
        if self.catdata[GenericToGPDPDialog.ADV_FUNC]:
            self.FormatChoice = self.FindWindowById(ID_UNITCHOICE)
            self.FormatChoice.SetStringSelection(self.catdata[GenericToGPDPDialog.ADV_FUNC][GenericToGPDPDialog.UNITS])
    def OnOK(self, event):
        self.catdata[GenericToGPDPDialog.ADV_FUNC]=[]
        self.catdata[GenericToGPDPDialog.ADV_FUNC].append(self.FormatChoice.GetStringSelection())
        self.catdata[GenericToGPDPDialog.ADV_FUNC].append(1) #bogus multiplication factor
        DataDictDialogBase.OnOK(self, event)

class GeneralOptionsDlg(DataDictDialogBase):
    def __init__(self, parent, catdata):
        DataDictDialogBase.__init__(self, parent, GeneralDialog, catdata)
        self.SetSize(wx.Size(240,230))


def CheckForRequisiteHDCSstructure(parent=None, bSilent=False):
    errmsg=""
    rcode,pathToP = RegistryHelpers.GetDirFromUser(parent, RegistryKey="DPsConvertToDir",                                                   
                                                   Message='Associate the incoming DPs to a HIPS/SIPS "project"')
    if rcode==wx.ID_OK:
        # check for VesselConfig dir (config/TAI-UTC file not needed under license-free HIPS I/O)
        pathTo=pathToP[:pathToP.rfind(os.sep)]+os.sep
        pathToVCFdir = pathTo+'VesselConfig'
        #pathToTAIUTC = pathTo+'config'+os.sep+'TAI-UTC'
        #if not os.access(pathToTAIUTC, os.F_OK):
        #    errmsg+=pathToTAIUTC+' does not exist.\n'
        if not os.access(pathToVCFdir, os.F_OK):
            errmsg+='VCF directory '+pathToVCFdir+' does not exist.\n'
        if errmsg and not bSilent:
            wx.MessageBox(errmsg,'Error Notice', wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, parent)
    else:
        pathToVCFdir=""
    return rcode,pathToP,pathToVCFdir,errmsg

class GenericToGPDPDialog(wx.Frame):
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
    def OnCloseWindow(self, event):
        win = wx.Window_FindFocus() 
        if win != None: 
            win.Disconnect(-1, -1, wx.wxEVT_KILL_FOCUS) 
        self.Destroy() 
    def CloseFunc(self, event):
        self.Close()
    def RankOrderedList(self):
        def cmp1(x,y):
            if x[1][0][self.RANK]<y[1][0][self.RANK]: return -1
            else: return 0
        l=self.Categories.items()
        l.sort(cmp1)
        return l
    def ShowTimeDlg(self):
        self.UpdateData()
        dlg=TimeDlg(self, self.Data[self.SelName])
        dlg.CenterOnParent()
        if wx.ID_OK==dlg.ShowModal():
            self.InitControls()
    def ShowUnitsDlg(self):
        self.UpdateData()
        cat=self.Data[self.SelName]
        dlg=UnitsDlg(self, cat)
        dlg.CenterOnParent()
        if wx.ID_OK==dlg.ShowModal():
            if cat[self.ADV_FUNC][self.UNITS]=="Meters": cat[self.ADV_FUNC][self.FACTOR]=METERS2METERS
            elif cat[self.ADV_FUNC][self.UNITS]=="Fathoms": cat[self.ADV_FUNC][self.FACTOR]=FATH2METERS
            elif cat[self.ADV_FUNC][self.UNITS]=="Feet": cat[self.ADV_FUNC][self.FACTOR]=FEET2METERS
            self.InitControls()
    def ShowLatLonDlg(self,bIsPtGeomSetting=False):
        positionSettings=0
        self.UpdateData()
        dlg=LatLonDlg(self, self.Data[self.SelName])
        dlg.CenterOnParent()
        if wx.ID_OK==dlg.ShowModal():
            positionSettings=self.Data[self.SelName][self.ADV_FUNC]
        if positionSettings:
            self.OnLatLonSettings(positionSettings,bIsPtGeomSetting)
    def OnLatLonSettings(self,positionSettings,bIsPtGeomSetting=False):
        LatLon,ObsLatObsLon = [self.LATDATATYPE_STR,self.LONDATATYPE_STR],[self.OLATDATATYPE_STR,self.OLONDATATYPE_STR]
        bCalcByRB=positionSettings[self.CALCRB]
        clicked,alt = [],[]
        if self.SelName in LatLon:
            clicked,alt = LatLon,ObsLatObsLon
        elif self.SelName in ObsLatObsLon:
            clicked,alt = ObsLatObsLon,LatLon
        if reduce(lambda i,j: i or j, map(lambda k: self.Data[k][self.USE_OR_REQUIRED], alt)): # somewhat moot to check either ObsLatObsLon USE_OR_REQUIREDs, as range/br can only be [not]applied to both lat & lon
            bAltAlreadyUnChecked=False
        else:
            bAltAlreadyUnChecked=True
        if bIsPtGeomSetting: # then synchronize all clicked settings to alt...
            others = LatLon+ObsLatObsLon
            others.remove(self.SelName)
            for k in [self.SelName]+others: # sync all, doing self.SelName first
                self.Data[k][self.USE_OR_REQUIRED]=1 # ibid.
                self.Data[k][self.ADV_FUNC]=positionSettings[:]
        else: # ...otherwise, if want to use range and bearing for LatLon/ObsLatObsLon, disable/uncheck that use in ObsLatObsLon/LatLon (resp.)--iff LatLon/ObsLatObsLon (resp.) not already unchecked
            self.UsePointGeomData.SetValue(0) # assume disparate settings amongst [Obs]Lat/Lon--and clear GeomType/GeomXYlist option (see also UsePointGeomData's wx.EVT_CHECKBOX)
            for k in clicked:
                self.Data[k][self.ADV_FUNC]=positionSettings[:]
                if not (not bCalcByRB and bAltAlreadyUnChecked): # synch clicked use checkbox, unless calculate using Range/Azimuth checkbox is clear for clicked and use checkbox is already clear for alt
                    self.Data[k][self.USE_OR_REQUIRED]= not bCalcByRB
            for k in alt:
                # synch alt use checkbox & calculate using Range/Azimuth checkbox (CALCRB), unless clicked CALCRB is clear and use checkbox is already clear for alt
                if not (not bCalcByRB and bAltAlreadyUnChecked):
                    self.Data[k][self.USE_OR_REQUIRED] = 1 # must use other coords in order for range bearing to work
                    self.Data[k][self.ADV_FUNC][self.CALCRB] = 0 #not using range and bearing
        self.InitControls()
    def ShowGeneralDlg(self):
        dlg=GeneralOptionsDlg(self, self.Data[self.SelName])
        if wx.ID_OK==dlg.ShowModal():
            self.InitControls()
    def __init__(self, parent, pssobj, PathToEmptyForm):
        #seperating the category data from the controls so that we can pickle the categories for template creation
        self.parent=parent
        self.PSS=pssobj
        self.PathToEmptyForm = PathToEmptyForm
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
        titles=[
            ["Use",5,20],["Data Type",40,70],["Delimiter", 115, 40],["Field Num", 170, 50],
            ["Start Col", 230,70],["End Col", 285, 70],["Named Field", 350,90],["Advanced",450,55], ["Parsed Val",510,90],#["Format",445,90],
            ]
        layout=[
            [wx.CheckBox,8,20],[wx.StaticText,40,70],[wx.TextCtrl, 120, 30],[wx.TextCtrl,170,50],
            [wx.TextCtrl,240,30],[wx.TextCtrl,290,30],[wx.Choice,350,90],[wx.Button,450,50],[wx.StaticText,510,90],
            ]
        self.FunctionsAndControls={
            self.LATDATATYPE_STR:copy.copy(layout)+[self.ShowLatLonDlg,None, None, lambda con, pt, val: pt.SetLatitude(val)], #+["Dec Deg", "DMS (:;.)"]
            self.OLATDATATYPE_STR:copy.copy(layout)+[self.ShowLatLonDlg,None, None, lambda con, pt, val: pt.SetObsLatitude(val)],#+["Dec Deg", "DMS (:;.)"]
            self.LONDATATYPE_STR:copy.copy(layout)+[self.ShowLatLonDlg,None, None, lambda con, pt, val: pt.SetLongitude(val)],#+["Dec Deg", "DMS (:;.)"]
            self.OLONDATATYPE_STR:copy.copy(layout)+[self.ShowLatLonDlg,None, None, lambda con, pt, val: pt.SetObsLongitude(val)],#+["Dec Deg", "DMS (:;.)"]
            "THU (TPEh)":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: pt.SetTHU(val)],
            "Time":copy.copy(layout)+[self.ShowTimeDlg,None, None, lambda con, pt, val: pt.SetTime(val)],#+["UTCSec80", "HMS (:;.)"]
            "Depth":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: pt.SetDepth(val)],
            "ObsDepth":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: pt.SetObsDepth(val)],
            "TVU (TPEv)":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: pt.SetTVU(val)],
            "Height":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: con.SetHeight(val)],
            "Remarks":copy.copy(layout)+[self.ShowGeneralDlg,None, None, lambda con, pt, val: con.SetRemarks(val)],
            "Recommends":copy.copy(layout)+[self.ShowGeneralDlg,None, None, lambda con, pt, val: con.SetRecommendations(val)],
            "Display Name":copy.copy(layout)+[self.ShowGeneralDlg,None, None, lambda con, pt, val: con.SetDisplayName(val)],
            "Office Notes":copy.copy(layout)+[self.ShowGeneralDlg,None, None, lambda con, pt, val: con.SetOther(val)],
            "Range":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: pt.SetRange(val)],
            "Azimuth":copy.copy(layout)+[self.ShowGeneralDlg,None, None, lambda con, pt, val: pt.SetAzimuth(val)],
            "Tide":copy.copy(layout)+[self.ShowUnitsDlg,None, None, lambda con, pt, val: pt.SetTide(val)],
            "<Filter>":copy.copy(layout)+[self.ShowGeneralDlg,None, None, lambda con, pt, val: None],
            }
        self.openedfile=""
        # build a combined dictionary for convenience  
        # can modify either the Categories dictionary or the underlying Data/Functions dictionaries        
        self.MakeCategories()

        wx.Frame.__init__(self, parent, -1, "Generic GPs/DPs Import", wx.DefaultPosition, wx.Size(668, 725), wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER | wx.NO_FULL_REPAINT_ON_RESIZE)
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNFACE))
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_CLOSE(self, self.OnCloseWindow)

        # wx.Windows uses the first editable control added as the default focus object (which receives focus temporarilly regardless of what
        # was actually clicked when recieving focus from another frame)
        self.HeaderStatic = wx.StaticText(parent=self, id=10000, label="Start at line")
        self.HeaderTxt = wx.TextCtrl(parent=self, id=10001, value="1", size=wx.Size(30,-1))
        self.MultiDelim = wx.CheckBox(parent=self, id=10002, label="Treat multiple delimeters as one")
        self.InsertAsPanel = wx.Panel(self, -1, size=wx.Size(300,50)) # put InsertAs radiobox on wx.Panel that's a child of frame; otherwise, wx.EVT_RADIOBOX doesn't work
        self.InsertAs = wx.RadioBox(parent=self.InsertAsPanel, id=10003, label="Insert As", choices=["GPs","DPs","Chart GPs","Checkpoints"], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.InsertAsPanel.SetSize(self.InsertAsPanel.GetBestSize())
        wx.EVT_RADIOBOX(self, 10003, self.OnInsertAsChoice)
        self.RetainDBRecordsetData = wx.CheckBox(parent=self, id=10004, label="Retain complete recordset information for ADO data "+str(self.ADODB_TYPES).replace("'",'').replace('|*',' '))
        self.UseS57AttrData = wx.CheckBox(parent=self, id=10005, label="S-57 Data ---> Insert named field S-57 attribute acronym data into object class:")
        wx.EVT_CHECKBOX(self.UseS57AttrData, 10005, self.ToggleUseS57AttrData)
        self.S57ObjectClass = wx.Choice(parent=self, id=10006, size=wx.Size(220,-1))
        self.InitS57ObjClassChoices()
        self.UsePointGeomData = wx.CheckBox(parent=self, id=10007, label="Point, Lines, Polygons ---> Create item spatial data as per named field geometry (GeomType/GeomXYlist)")
        wx.EVT_CHECKBOX(self.UsePointGeomData, 10007, self.OnPtGeomSetting)
        self.PointGeomAdvButton = wx.Button(parent=self, id=10008, label="LL/UTM", size=wx.Size(50,-1), style=0 )
        wx.EVT_BUTTON(self,10008,self.OnPtGeomSetting)
        idDatum = 10009 # start of available id range, per last used in all ctrls above

        self.parser = DegreeParser.DegreeParser(self, -1, style=wx.WANTS_CHARS) #wx.TAB_TRAVERSAL)

        fctrlYposA,fctrlYposB = 25,10 # Y-coordinate of field ctrls = fctrlYposA*index + fctrlYposB
        index=0 # index for vertical spacing of GUI ctrl groups
        newctrlY = fctrlYposA*index + fctrlYposB
        for control in range(self.NUM_CTRLS): #make the text headings
            txt=titles[control]
            wx.StaticText( parent=self, id=idDatum+index*self.NUM_CTRLS+control, label=txt[0], pos=[txt[1],newctrlY], size=wx.Size(txt[2],-1), style=0 )
        L=self.RankOrderedList()
        for name, [data, ctrls] in L:
            index+=1
            if name=="<Filter>":
                index+=0.5 # insert half a linefeed space
            newctrlY = fctrlYposA*index + fctrlYposB
            for control in range(self.NUM_CTRLS):
                lay_control=ctrls[control]
                if lay_control[0] == wx.CheckBox:
                    ctrls[control] = wx.CheckBox( parent=self, id=idDatum+index*self.NUM_CTRLS+control, label="",  pos=[lay_control[1],newctrlY], size=wx.Size(lay_control[2],-1), style=0 )
                    if data[control] not in [0,1]:
                        ctrls[control].SetValue(1)
                        ctrls[control].Enable(0)
                elif lay_control[0] == wx.TextCtrl:
                    ctrls[control] = wx.TextCtrl( parent=self, id=idDatum+index*self.NUM_CTRLS+control, value="", pos=[lay_control[1],newctrlY], size=wx.Size(lay_control[2],-1), style=0 )
                    wx.EVT_SET_FOCUS(ctrls[control], self.OnTextBoxFocus)        
                    wx.EVT_KILL_FOCUS(ctrls[control], self.OnLostTextBoxFocus)        
                elif lay_control[0] == wx.Choice:
                    ctrls[control] = wx.Choice( parent=self, id=idDatum+index*self.NUM_CTRLS+control, choices=[], pos=[lay_control[1],newctrlY], size=wx.Size(lay_control[2],-1), style=0 )
                    ctrls[control].SetValue=ctrls[control].SetStringSelection
                    ctrls[control].GetValue=ctrls[control].GetStringSelection
                    wx.EVT_CHOICE(self, ctrls[control].GetId(), self.OnNamedChoice)
                elif lay_control[0] == wx.StaticText:
                    ctrls[control] = wx.StaticText( parent=self, id=idDatum+index*self.NUM_CTRLS+control, label="", pos=[lay_control[1],newctrlY], size=wx.Size(lay_control[2],-1), style=0 )
                    ctrls[control].SetValue=ctrls[control].SetLabel
                    ctrls[control].GetValue=ctrls[control].GetLabel
                elif lay_control[0] == wx.Button:
                    if control!=self.ADV_BUTTON or ctrls[self.ADV_FUNC]: 
                        ctrls[control] = wx.Button( parent=self, id=idDatum+index*self.NUM_CTRLS+control, label="", pos=[lay_control[1],newctrlY], size=wx.Size(lay_control[2],-1), style=0 )
                        ctrls[control].SetValue=ctrls[control].SetLabel
                        ctrls[control].GetValue=ctrls[control].GetLabel
                        wx.EVT_BUTTON(self, ctrls[control].GetId(), self.OnAdvancedButton)
        self.InitControls()
        index+=1.5 # linefeed for next GUI ctrls
        hmargin1,hmargin2,hgutter1,hgutter2 = 5,10,6,24
        newtxtctrlY = int(fctrlYposA*index+fctrlYposB)
        newctrlY = newtxtctrlY+4
        self.parser.SetSize(150,newtxtctrlY,100,25)
        self.parser.Show(0) #hidden
        self.HeaderStatic.SetPosition([hmargin2,newctrlY])
        newctrlX = self.HeaderStatic.GetPosition()[0] + self.HeaderStatic.GetSize()[0] + hgutter1
        self.HeaderTxt.SetPosition([newctrlX,newtxtctrlY])       # to the right of the header static text
        newctrlX += self.HeaderTxt.GetSize()[0] + hgutter2  # to the right of the header text box
        self.MultiDelim.SetPosition([newctrlX,newctrlY])
        newctrlX += self.MultiDelim.GetSize()[0] + hgutter2 # to the right of mult. delim. checkbox text
        self.InsertAsPanel.SetPosition([newctrlX,newtxtctrlY-int(fctrlYposA*0.5)])
        index+=1.5
        newctrlY = int(25*index+14)
        self.RetainDBRecordsetData.SetPosition([hmargin2,newctrlY])
        index+=1
        newtxtctrlY,newctrlY = int(25*index+10),int(25*index+14)
        self.UseS57AttrData.SetPosition([hmargin2,newctrlY])
        newctrlX = self.UseS57AttrData.GetPosition()[0] + self.UseS57AttrData.GetSize()[0] + hgutter1
        self.S57ObjectClass.SetPosition([newctrlX,newtxtctrlY])
        self.S57ObjectClass.SetSize(wx.Size(self.S57ObjectClass.GetBestSize()[0],-1))
        index+=1
        newtxtctrlY,newctrlY = int(25*index+10),int(25*index+14)
        self.UsePointGeomData.SetPosition([hmargin2,newctrlY])
        newctrlX = self.UsePointGeomData.GetPosition()[0] + self.UsePointGeomData.GetSize()[0] + hgutter1
        self.PointGeomAdvButton.SetPosition([newctrlX,newtxtctrlY])
        index+=1
        newctrlY = int(25*index+14)
        self.FileDisplayPanel = wx.Panel(parent=self, id=-1, pos=wx.Point(hmargin1,newctrlY), size=wx.Size(400,300), style=wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.FileDisplay = wx.stc.StyledTextCtrl(parent=self.FileDisplayPanel, id=-1, size=wx.Size(400,300), style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.FileDisplay.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, 'face:Courier New,size:10,fore:#000000,back:#FFFFFF') # nominal style
        self.FileDisplay.StyleClearAll()
        #self.FileDisplay.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, wx.Font(10,wx.SWISS,wx.NORMAL,wx.NORMAL))
        self.FileDisplay.StyleSetSpec(1,"face:Courier New,size:10,fore:#FF0000,back:#FFFF00,bold") # for fixed-field highlights
        self.FileDisplay.StyleSetSpec(2,"face:Courier New,size:10,fore:#FF0000,back:#00FFFF,bold") # for delimited-field highlights
        self.FileDisplay.SetMargins(0,0)
        self.FileDisplay.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        self.FileDisplay.SetMarginWidth(1, self.FileDisplay.TextWidth(wx.stc.STC_STYLE_LINENUMBER,str(self.DATA_LINES)+' '))
        filedisplaySizer = wx.BoxSizer(wx.HORIZONTAL)
        filedisplaySizer.Add(self.FileDisplay, 1, wx.EXPAND)
        self.FileDisplayPanel.SetSizer(filedisplaySizer)
        self.FileDisplayPanel.SetAutoLayout(True)
        self.FileDisplay.SetBufferedDraw(False)
        self.FileDisplay.SetEOLMode(wx.stc.STC_EOL_LF)
        wx.stc.EVT_STC_UPDATEUI(self.FileDisplay, -1, self.OnFileDisplayUpdateUI)
        self.maxlenLine = 0
        wx.stc.EVT_STC_ZOOM(self.FileDisplay, -1, self.OnFileDisplayZoom)
        self.SelName,self.SelCtrl = None,None
        wx.EVT_LEFT_UP(self.FileDisplay, self.OnSelectionChanged)
        wx.EVT_SET_FOCUS(self.FileDisplay, self.OnFileDisplayFocusGained)
        wx.EVT_KILL_FOCUS(self.FileDisplay, self.OnFileDisplayFocusLost)
        self.MakeMenu()
        self.OnSize(None)
    def OnFileDisplayUpdateUI(self, event):
        event.Skip()
    def OnFileDisplayZoom(self, event):
        event.Skip()
        self.FileDisplay.SetMarginWidth(1, self.FileDisplay.TextWidth(wx.stc.STC_STYLE_LINENUMBER,str(self.DATA_LINES)+' '))
        # BUGFIX: scale horizontal scroll bar (thumb)...
        self.FileDisplay.GotoPos(self.FileDisplay.GetLineEndPosition(self.maxlenLine))
        self.FileDisplay.GotoPos(0)
    def OnFileDisplayFocusGained(self, event):
        event.Skip()
        if _dHSTP: bDisableEditing=False
        else: bDisableEditing=True
        self.FileDisplay.SetReadOnly(bDisableEditing)
    def OnFileDisplayFocusLost(self, event):
        event.Skip()
        self.FileDisplay.SetReadOnly(False)
    def OnInsertAsChoice(self, event=None):
        # note: don't use event methods--as that parameter is optional
        if self.InsertAs.GetStringSelection()=="DPs": # if InsertAs DPs, Time & ObsDepth are required; ADO recordsets are not allowed (see notes in OnProcess for files of type ADODB_EXT)
            self.SetUseTimeObsDepthAndNoUseADOrs()
        else:
            self.SetUseTimeObsDepthAndNoUseADOrs(False)
    def SetUseTimeObsDepthAndNoUseADOrs(self, bRequired=True):
        timeCB,obsDepthCB = [self.Categories[txtDataType][1][0] for txtDataType in ('Time','ObsDepth')]
        if bRequired:
            timeCB.Enable(0)
            obsDepthCB.Enable(0)
            self.RetainDBRecordsetData.Enable(0)
            timeCB.SetValue(1)
            obsDepthCB.SetValue(1)
            self.RetainDBRecordsetData.SetValue(0)
        else:
            timeCB.Enable(1)
            obsDepthCB.Enable(1)
            self.RetainDBRecordsetData.Enable(1)
    def ToggleUseS57AttrData(self, event=None):
        # note: don't use event methods--as that parameter is optional (do direct query of checkbox status)    
        pass        
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
    def InitS57ObjClassChoices(self):
        self.S57ObjectClass.Clear()
        oAcronymNameIdx=1
        S57ObjClassChoices=NOAAcarto.s57noaafeatures.keys()
        S57ObjClassChoices.sort()
        for oAcronym in S57ObjClassChoices:
            self.S57ObjectClass.Append("%s (%s)"%(oAcronym,NOAAcarto.s57objectclasses[oAcronym][oAcronymNameIdx]))
    def InitControls(self):
        bForceRB=0
        for name, [data, ctrls] in self.Categories.iteritems():
            #setup the choice box for named fields
            ctrls[self.NAMED_FIELD].Clear()
            for s in self.NamedChoices: ctrls[self.NAMED_FIELD].Append(s)
            #set the data for controls
            for control in range(self.NUM_CTRLS):
                try: ctrls[control].SetValue(data[control])
                except AttributeError: pass # buttons may not be created - therefore no SetValue method
                except TypeError: 
                    if control==self.RANK: ctrls[control].SetValue(name)
                    else: raise "Unhandled TypeError"
            try:
                if data[self.DELIM]==self.NamedDelim and float(data[self.FIELD_NUM])>0 and float(data[self.FIELD_NUM])<=len(self.NamedChoices):
                    ctrls[self.NAMED_FIELD].SetSelection(int(float(data[self.FIELD_NUM]))-1)
            except ValueError:
                pass #null string (empty textbox) causes exception
            if name in (self.LATDATATYPE_STR,self.LONDATATYPE_STR,self.OLATDATATYPE_STR,self.OLONDATATYPE_STR):
                if data[self.ADV_FUNC][self.CALCRB]:
                    bForceRB=1
        for data, ctrls in (self.Categories["Range"], self.Categories["Azimuth"]):
            ctrls[self.USE_OR_REQUIRED].Enable(not bForceRB)
            if bForceRB: 
                data[self.USE_OR_REQUIRED]=1
                ctrls[self.USE_OR_REQUIRED].SetValue(1)
        if self.openedfile:
            self.sbar.SetStatusText("File: %s"%self.openedfile,0)
    def UpdateData(self):
        for name, [data, ctrls] in self.Categories.iteritems():
            #Get the data for controls (except buttons)
            for control in range(self.NUM_CTRLS):
                try: data[control]=ctrls[control].GetValue()
                except AttributeError: pass #buttons are controlled by the dialogs they spawn.  Don't update values here.
    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        x,y=self.FileDisplayPanel.GetPosition()
        self.FileDisplayPanel.SetSize(x,y,w-x*2, h-y-5)
    def FindControl(self, window):
        for datatype,controls in self.FunctionsAndControls.iteritems():
            for ctrl in range(self.NUM_CTRLS):
                if controls[ctrl]==window:
                    return datatype, ctrl
        return "",-1
    def OnTextBoxFocus(self, event):
        self.SelName,self.SelCtrl = self.FindControl(event.GetEventObject())
        ctrls=self.FunctionsAndControls[self.SelName]
        self.HighlightFileDisplay()
        event.Skip()
    def OnLostTextBoxFocus(self, event):
        SelName,SelCtrl = self.FindControl(event.GetEventObject())
        if SelCtrl in (self.DELIM, self.FIELD_NUM):
            try:
                f=int(float(self.FunctionsAndControls[SelName][self.FIELD_NUM].GetValue()))
                if f<1 or f>len(self.NamedChoices) or self.FunctionsAndControls[SelName][self.DELIM].GetValue() != self.NamedDelim:
                    ind=-1 # clear the choice box - mismatched delimiter or field number
                else:
                    ind=f-1 #show the name value in the choice box
            except ValueError: #null/empty text box
                ind=-1 # clear the choice box
            self.FunctionsAndControls[SelName][self.NAMED_FIELD].SetSelection(ind)
        event.Skip()
    def OnNamedChoice(self, evt):
        self.SelName,self.SelCtrl = self.FindControl(evt.GetEventObject())
        self.FunctionsAndControls[self.SelName][self.START_COL].SetValue("")
        self.FunctionsAndControls[self.SelName][self.END_COL].SetValue("")
        self.FunctionsAndControls[self.SelName][self.DELIM].SetValue(self.NamedDelim)
        self.FunctionsAndControls[self.SelName][self.FIELD_NUM].SetValue(str(evt.GetSelection()+1))
        self.HighlightFileDisplay()
        evt.Skip()
    def OnAdvancedButton(self, event):
        self.SelName,self.SelCtrl = self.FindControl(event.GetEventObject())
        self.FunctionsAndControls[self.SelName][self.ADV_FUNC]()
    def OnPtGeomSetting(self, event):
        self.UpdateData()
        # use Lat/Northing advanced processing dialog/data (LatLonDlg)--then synchronize settings to the others for clarity
        self.SelName = self.LATDATATYPE_STR # this attribute used elsewhere...todo: self.SelCtrl too?
        if event.GetId()==self.UsePointGeomData.GetId(): # reset/sync [Obs]Lat/Lon settings (no dialog)
            positionSettings = [0,8,0,0] # COORDTYPE,ZONE,RADIANS,CALCRB
            self.OnLatLonSettings(positionSettings,bIsPtGeomSetting=True)
        elif self.UsePointGeomData.GetValue(): # PointGeomAdvButton event--show/sync through dialog
            self.FunctionsAndControls[self.LATDATATYPE_STR][self.ADV_FUNC](bIsPtGeomSetting=True)
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
    def ClearFileDisplayHeader(self):
        try: nFirstLine=int(self.HeaderTxt.GetValue())-1
        except: nFirstLine=0
        for n in xrange(nFirstLine): # drill down past user-indicator header rows, clearing any stale styling on the way
            lineStartPos = self.FileDisplay.PositionFromLine(n)
            self.FileDisplay.StartStyling(lineStartPos,0x1f) # mask to protect 3 indicator bits--only desire to modify 5 bits of text style
            lenLine = self.FileDisplay.GetLineEndPosition(n) - lineStartPos
            if lenLine > 0: self.FileDisplay.SetStyling(lenLine,wx.stc.STC_STYLE_DEFAULT)
    def HighlightFileDisplay(self):
        bIgnoreMultiDelim = self.MultiDelim.GetValue()
        ctrls = self.FunctionsAndControls[self.SelName]
        self.FileDisplay.ClearDocumentStyle()
        sPos,ePos = self.FileDisplay.GetSelection()
        #if sPos!=ePos: # BUGFIX!: perturb/reset selection to overcome ClearDocumentStyle()'s inability to wipeout previous styling contained on line having the selection
        #    if sPos > ePos: sPos,ePos = ePos,sPos
        #    #lPos = self.FileDisplay.PositionFromLine(self.FileDisplay.LineFromPosition(sPos))
        #    self.FileDisplay.GotoPos(sPos)
        #    self.FileDisplay.SetSelection(sPos,ePos)
        self.UpdateData()
        try: nFirstLine=int(self.HeaderTxt.GetValue())-1
        except: nFirstLine=0
        txt = self.FileDisplay.GetLine(nFirstLine)
        if txt:
            #display parsed values for each category used
            for name,[data,fctrls] in self.Categories.iteritems():
                if data[self.USE_OR_REQUIRED] or data[self.DEF_VALUE]:
                    if data[self.USE_OR_REQUIRED]:
                        val=self.GetFieldStringsFromText(txt, data)
                    else:
                        val=data[self.DEF_VALUE]
                    #if val:
                    #    print "First '%s' raw string to be parsed: %s"%(name,val)
                    # do advanced processing...
                    try:
                        exec data[self.MOD_SCRIPT] # by executing here there is access to the line,contact,point structures
                    except:
                        val="BadModifierScript"
                        print "-"*15, "User Script Exception", "-"*15
                        traceback.print_exc()
                    if val.strip() and val!="BadModifierScript":
                        if name == "Time":
                            exp = self.CompiledTimeRE()
                            val = ParseTime(exp, val)
                        elif data[self.ADV_BUTTON]=="Units": # precludes "Time" (adv button is 'Format') and lat/lon (adv buttons are 'LL/UTM')--other elifs
                            try:
                                val = "%.3f"%(float(val)*data[self.ADV_FUNC][self.FACTOR])
                            except:
                                val="ConversionFailed"
                        elif name in (self.LATDATATYPE_STR,self.LONDATATYPE_STR,self.OLATDATATYPE_STR,self.OLONDATATYPE_STR):
                            try:
                                if data[self.ADV_FUNC][self.COORDTYPE]==0:
                                    if data[self.ADV_FUNC][self.RADIANS]==0:
                                        deg,strin = self.parser.ParseString(val)
                                        val = str(deg)
                                    else:
                                        val = str(float(deg)*RAD2DEG)
                            except:
                                val="ConversionFailed"
                else: val="N/A"
                fctrls[self.SAMPLE_DATA].SetValue(val) #sets the text on the right side of dialog for each category
            if ctrls[self.START_COL].GetValue() and ctrls[self.END_COL].GetValue(): # highlight fixed columns--note: columns are zero-based
                sCol,eCol = float(ctrls[self.START_COL].GetValue()),float(ctrls[self.END_COL].GetValue())
                self.ClearFileDisplayHeader()
                for n in xrange(nFirstLine, self.FileDisplay.GetLineCount()):
                    lineStartPos = self.FileDisplay.PositionFromLine(n)
                    startPos = lineStartPos+sCol
                    lenLine = self.FileDisplay.GetLineEndPosition(n) - lineStartPos
                    if lenLine > 0:
                        if startPos-lineStartPos < lenLine: # style the data field...
                            self.FileDisplay.StartStyling(startPos,0x1f) # mask to protect 3 indicator bits--only desire to modify 5 bits of text style
                            lenStyle = min(eCol-sCol,lenLine-sCol) # don't want to style beyond end of line
                            self.FileDisplay.SetStyling(lenStyle,1) # style=1 for fixed field highlight
            elif ctrls[self.DELIM].GetValue() and ctrls[self.FIELD_NUM].GetValue(): # highlight delimited fields--note: fields are one-based
                d = ctrls[self.DELIM].GetValue()
                if d.isspace(): rep=","
                else: rep=" "
                for fld in ctrls[self.FIELD_NUM].GetValue().split(","):
                    fNum = int(fld.lower().replace("e","")) # convert field into (one-based) integer from string
                    self.ClearFileDisplayHeader()
                    for n in range(nFirstLine, self.FileDisplay.GetLineCount()):
                        lineStartPos,lineEndPos = self.FileDisplay.PositionFromLine(n),self.FileDisplay.GetLineEndPosition(n)
                        txt = self.FileDisplay.GetLine(n)
                        lenLine = lineEndPos - lineStartPos
                        if lenLine > 0:
                            pos=[-1] # prepend the beginning of line
                            if bIgnoreMultiDelim: #cheap way of getting rid of duplicate delimiters
                                while txt.find(d+d)>=0: txt=txt.replace(d+d,rep+d,1)
                            while txt.find(d, pos[-1]+1)>=0:
                                pos.append(txt.find(d, pos[-1]+1)) #append position of delimiters
                            pos.append(lenLine) #append the end of line
                            try:
                                startPos = lineStartPos+pos[fNum-1]+1 # recall, fields are one-based & column positions are zero-based
                                if startPos-lineStartPos < lenLine: # style the data field...
                                    if "e" in fld.lower(): # ...need endPos first...
                                        endPos = lineEndPos
                                    else:
                                        endPos = lineStartPos+pos[fNum]
                                    self.FileDisplay.StartStyling(startPos,0x1f) # mask to protect 3 indicator bits--only desire to modify 5 bits of text style
                                    lenStyle = min(endPos-startPos,lineEndPos-startPos) # don't want to style beyond end of line
                                    self.FileDisplay.SetStyling(lenStyle,2) # style=2 for delimited-field highlight
                            except IndexError:
                                pass
    def OnSelectionChanged(self, event):
        #user changed the highlight in the data window.
        event.Skip() # get this out to the wx.stc.StyledTextCtrl handler to make selection behave normally
        self.sbar.SetStatusText("File: %s"%self.openedfile,0)
        if self.SelCtrl:
            sPos,ePos = self.FileDisplay.GetSelection()
            if sPos!=ePos: #selection is non-zero width
                if sPos > ePos: sPos,ePos = ePos,sPos
                startRow = self.FileDisplay.LineFromPosition(sPos)
                startCol = sPos-self.FileDisplay.PositionFromLine(startRow)
                endRow = self.FileDisplay.LineFromPosition(ePos)
                endCol = ePos-self.FileDisplay.PositionFromLine(endRow)
                if startRow==endRow: #make sure didn't multi-row select
                    if self.SelCtrl in [self.START_COL, self.END_COL]: 
                        #the selected text control was column delimeters
                        self.FunctionsAndControls[self.SelName][self.START_COL].SetValue(str(startCol))
                        self.FunctionsAndControls[self.SelName][self.END_COL].SetValue(str(endCol))
                        self.FunctionsAndControls[self.SelName][self.DELIM].SetValue("")
                        self.FunctionsAndControls[self.SelName][self.FIELD_NUM].SetValue("")
                        self.HighlightFileDisplay()
                    elif self.SelCtrl in [self.DELIM, self.FIELD_NUM]:
                        # the selected text control was a delimeted field control
                        ltxt,txt = self.FileDisplay.GetLine(startRow).replace('\r',''),self.FileDisplay.GetSelectedText()
                        lineEndCol = self.FileDisplay.GetLineEndPosition(startRow)
                        if startRow>0:
                            lineStartCol = self.FileDisplay.GetLineEndPosition(startRow-1)+1
                        else:
                            lineStartCol = 0
                        lineEndCol -= lineStartCol
                        if txt and (txt[0]==txt[-1] or startCol==0 or endCol==lineEndCol):
                            delim=""
                            fields=""
                            if txt[0]==txt[-1]: #start and end character are the same - i.e. the delimiting character
                                delim=txt[0]
                            elif startCol==0: #first field
                                delim=txt[-1]
                            else: #last field
                                delim=txt[0]
                            if delim:
                                try:
                                    idxStart,idxEnd = len(ltxt[:startCol].split(delim))+1,len(ltxt[:endCol-1].split(delim))
                                    if idxStart>idxEnd: idxStart=idxEnd
                                    fieldsStr = ",".join([str(idx) for idx in range(idxStart,idxEnd+1)])
                                    self.FunctionsAndControls[self.SelName][self.DELIM].SetValue(delim)
                                    self.FunctionsAndControls[self.SelName][self.FIELD_NUM].SetValue(fieldsStr)
                                    self.FunctionsAndControls[self.SelName][self.START_COL].SetValue("")
                                    self.FunctionsAndControls[self.SelName][self.END_COL].SetValue("")
                                    self.HighlightFileDisplay()
                                except ValueError:
                                    pass
                            else: self.sbar.SetStatusText("File: %s - Selection can't contain delimiter other than at beginning and end"%self.openedfile,0)
                        else: self.sbar.SetStatusText("File: %s - Couldn't determine delimiter (start/end must be same character)"%self.openedfile,0)
                else: self.sbar.SetStatusText("File: %s - Can't select across multiple rows"%self.openedfile,0)
            else:  self.sbar.SetStatusText("File: %s - Nothing Selected"%self.openedfile,0)
        else:
            self.FileDisplay.SetToolTipString("Click in a Data Type field/column above and then select data field/columns here")
    def MakeMenu(self):
        self.sbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)  # Create a status bar--start with 1 field, then specify actual #...
        nfields=1
        self.sbar.SetFieldsCount(nfields)   # start with 2 w/default widths [-1,-1]; apps add more
        self.mainmenu = wx.MenuBar()
        # Make a Help menu
        menu = wx.Menu()
        openID = wx.NewId()
        menu.Append(openID, 'Open template')
        saveID = wx.NewId()
        menu.Append(saveID, 'Save template')
        dataID = wx.NewId()
        menu.Append(dataID, 'Open data file')
        processID = wx.NewId()
        menu.Append(processID, 'Process file(s)')
        # HSTP:  'Help' is an event appropriately handled in ZFrame
        wx.EVT_MENU(self, dataID, self.OnOpenDataFile)
        wx.EVT_MENU(self, saveID, self.OnSaveTemplate)
        wx.EVT_MENU(self, openID, self.OnOpenTemplate)
        wx.EVT_MENU(self, processID, self.OnProcess)

        menu.AppendSeparator()
        self.clearID = wx.NewId()
        menu.Append(self.clearID, 'Clear Template')
        wx.EVT_MENU(self, self.clearID, self.OnOpenTemplate)
        exitID = wx.NewId()
        menu.Append(exitID, 'Close\tAlt-X')
        wx.EVT_MENU(self, exitID, self.CloseFunc)
        self.mainmenu.Append(menu, '&File')

        self.SetMenuBar(self.mainmenu)

        # set the menu accelerator table...
        aTable = wx.AcceleratorTable([(wx.ACCEL_ALT,  ord('X'), wx.ID_CLOSE),
                                     (wx.ACCEL_CTRL, ord('S'), saveID)])
        self.SetAcceleratorTable(aTable)
    def OnProcess(self, event, ftype=0, dTitle="", regkey="", fFilter=""):
        #make sure fields are filled out
        self.UpdateData() #make sure using the current displayed data
        if self.IsShown(): parent=self
        else: parent=self.GetParent()
        # todo: idiot check for .shp file (e.g., user chose .dbf from Shapefile set)
        if not dTitle:
            dTitle="Choose input data file(s)"
        bAllowMulti=True
        if ftype==0:
            if not regkey:
                regkey="GenericSourceFiles"
            if not fFilter:
                fFilter="|".join(("All Files|*.*","|".join(self.DB_TYPES)))
        elif ftype==1:
            regkey="VelocitySVFiles"
            fFilter="VelocWin Q files|*.??Q"
        elif ftype==2:
            regkey="CarisSVP"
            fFilter="HIPS SVP files|*.svp"
        elif ftype==3:
            dTitle="Choose Trimble/Pathfinder Database file(s)"
            regkey="PathfinderMDBFiles"
            fFilter='MS Access|*.mdb'
        elif ftype==4:
            dTitle="Choose Velocwin Diver Least Depth Report(s)"
            regkey="VelocwinDiverLDReports"
            fFilter='Velocwin Dive Reports|*.*'
        elif ftype==5:
            dTitle="Choose Caris Notebook GML file(s)"
            regkey="CarisNotebookGMLFiles"
            fFilter='Notebook GML files|*.gml'
        bOK,errmsg = True,''
        rcode,filenames = RegistryHelpers.GetFilenameFromUser(parent, bSave=0, RegistryKey=regkey, Title=dTitle, fFilter=fFilter, bMulti=bAllowMulti)
        if rcode==wx.ID_OK:
            bAsGPs,bAsDPs,bAsChartGPs,bAsCheckpoints = [False]*4 # some tested below ftype if-else block
            if ftype==0 or ftype==5: # GenericSourceFiles and Caris Notebook GML; evaluate conversion file list--any database-based and OGR/ADO-based data complicates parser validation...
                bAsGPs,bAsDPs,bAsChartGPs,bAsCheckpoints = [txtInsertAs==self.InsertAs.GetStringSelection() for txtInsertAs in ('GPs', 'DPs', 'Chart GPs', 'Checkpoints')]
                sourcePathsAndNames = self.PSS.QCIncomingDataFilesList(filenames,bAreGPs=bAsGPs,bAreDPs=bAsDPs,bAreChartGPs=bAsChartGPs,bAreCheckpoints=bAsCheckpoints)
                if sourcePathsAndNames:
                    bUsePtGeomData = self.UsePointGeomData.GetValue()
                    bParseDepth = False
                    if bAsDPs: contype="DP"
                    else: contype="GP"
                    fextset = set(filter(lambda fext: fext!='', [os.path.splitext(sourcePathAndName[0])[-1].lower() for sourcePathAndName in sourcePathsAndNames]))
                    ogrdbset,adodbset = set(self.OGRDB_EXT),set(self.ADODB_EXT)
                    dbsets = ogrdbset.union(adodbset)
                    #if ogrdbset: bHaveOGRfile=True
                    #else: bHaveOGRfile=False
                    if dbsets.intersection(fextset): bHaveDBfile=True # have at least one OGR/ADO database specified, therefore only delimeter-based fields valid...
                    else: bHaveDBfile=False
                    if fextset.issubset(ogrdbset): bAllOGRwithgeom=True
                    else: bAllOGRwithgeom=False
                    #if dbsets.difference(fextset): bHaveNonDBfile=True
                    #else: bHaveNonDBfile=False
                    for name, [data, ctrls] in self.Categories.iteritems(): #check for complete parser categories...
                        bIsPosField = name in (self.LATDATATYPE_STR,self.LONDATATYPE_STR,self.OLATDATATYPE_STR,self.OLONDATATYPE_STR)
                        if bHaveDBfile: #if any database-based files, all data types used/required must be parsed via delimited fields (not arbitrary start/end columns)...
                            if data[self.USE_OR_REQUIRED] and not (data[self.DELIM] and data[self.FIELD_NUM]):
                                if bIsPosField and bAllOGRwithgeom and bUsePtGeomData: # delimiter/field num for position coords not required
                                    continue # skip to parser's next data type
                                if not bAllOGRwithgeom and bIsPosField:
                                    bOK,errmsg = (False,
                                                  "Not all the database files specified support named field \n"+
                                                  "geometry.  Specify delimeter+field for all position data \n"+
                                                  "types to parse those files having no named field geometry. ")
                                else:
                                    bOK,errmsg = (False,
                                                  "The category '%s' is not complete. \n"%(name)+
                                                  "\n"+
                                                  "There are some databases specified in your conversion \n"+
                                                  "file list.  Database fields must be parsed via field \n"+
                                                  "number, not fixed start/end columns.  Note that database \n"+
                                                  "fields are shown as semicolon-delimited text in the file \n"+
                                                  "viewing area below (use File...Open data file). ")
                                break
                        else: # parser for all used/required data types specified?
                            if data[self.USE_OR_REQUIRED]:
                                if not (data[self.START_COL] and data[self.END_COL]) and not (data[self.DELIM] and data[self.FIELD_NUM]):
                                    bOK,errmsg = (False,
                                                  "The category '%s' is not complete. \n"%(name)+
                                                  "Specify delimeter+field or start/end columns. ")
                                    break
                        if name=="Depth" and data[self.USE_OR_REQUIRED]: bParseDepth=True # and will check later if have clash with S-57 VALSOU data
                    if bOK:
                        # check other options before proceeding with files...
                        bUseS57AttrData = self.UseS57AttrData.GetValue()
                        if bUseS57AttrData:
                            try:
                                oAcronym = self.S57ObjectClass.GetStringSelection().split()[0] # choices are <oAcronym (oName)>
                            except:
                                oAcronym = None
                            if not (oAcronym or bAllOGRwithgeom): # OGR layer name may be oAcronym; e.g., Notebook GML
                                bOK,errmsg = (False,
                                              "No S-57 object class is specified.  Choose an \n"+
                                              "S-57 object class to insert attribute data \n"+
                                              "according to any matching acronym-named fields, \n"+
                                              "or uncheck the S-57 Data option, and try again. ")
                            elif bParseDepth and "VALSOU" in self.NamedChoices:
                                bNoS57ok = wx.MessageBox("You have specified that 'Depth' is to be parsed and that \n"+
                                                         "S-57 attribute data be inserted; however, there are VALSOU \n"+
                                                         "data present--see named fields. \n"+
                                                         "\n"+
                                                         "Pydro XML 'Depth' and 'VALSOU' data are one in the same.  \n"+
                                                         "Choose the 'Yes' button to continue with import, and have \n"+
                                                         "the 'VALSOU' data trump that otherwise parsed through that \n"+
                                                         "otherwise specified in 'Depth'. ",
                                                         "OK to trump 'Depth' with 'VALSOU' data?", wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION, self)
                                if bNoS57ok==wx.NO:
                                    bOK = False
                        else: oAcronym = None
                else:
                    bOK = False
            elif ftype==3: # PathfinderMDBFiles; note: no parser template QC herein
                # TODO: don't delete "duplicate lines" until verified as such in recordset loop (need to return bToDelete[GPs,DPs])
                # note that for Pathfinder db data, do not need to set up naming for GPs and DPs (Tide - DP/GP field); former gets pathToFile and latter gets pathToPVDL (both incl. (any) .<extension>)
                sourcePathsAndNamesPathfinderGPs = self.PSS.QCIncomingDataFilesList(filenames,bAreGPs=True)
                sourcePathsAndNamesPathfinderDPs = self.PSS.QCIncomingDataFilesList(filenames,bAreDPs=True)
                # note: sourcePaths common to both; assign to a new 'sourcePaths' list per below, for filenames loop below
                if not sourcePathsAndNamesPathfinderGPs and not sourcePathsAndNamesPathfinderDPs:
                    bOK = False
                elif sourcePathsAndNamesPathfinderGPs and sourcePathsAndNamesPathfinderDPs:
                    bAsGPs,bAsDPs,contype = True,True,"GP/DP"
                    sourcePaths = [tple[0] for tple in sourcePathsAndNamesPathfinderGPs]
                elif sourcePathsAndNamesPathfinderGPs:
                    bAsGPs,bAsDPs,contype = True,False,"GP"
                    sourcePaths = [tple[0] for tple in sourcePathsAndNamesPathfinderGPs]
                elif sourcePathsAndNamesPathfinderDPs:
                    bAsGPs,bAsDPs,contype = False,True,"DP"
                    sourcePaths = [tple[0] for tple in sourcePathsAndNamesPathfinderDPs]
            elif ftype==4: # Velocwin Diver Least Depth Reports; note: no parser template QC herein
                bAsDPs,contype = True,"DP"
                linename = wx.GetTextFromUser('Enter DP "line" name for the incoming \n'+
                                              'Velocwin Diver Least Depth DP(s) .',
                                              'DP Line Name', "DiveDPs_%d-%03d"%tuple(time.localtime())[slice(0,8,7)], self)
                if not self.PSS.QCIncomingDataFilesList([linename],[linename],bAreDPs=True):
                    bOK = False
                else: # OK to proceed; however, Velocwin Diver Least Depth Reports handled outside of regular data source(s) loop--in ConvertVelocwinDiverLDReportDPs()
                    sourcePathsAndNames=[]
            else: # ftype in (1,2) # VelocitySVFiles & CarisSVP; note: no parser template QC herein
                sourcePathsAndNames = self.PSS.QCIncomingDataFilesList(filenames,bAreGPs=True)
                if not sourcePathsAndNames:
                    bOK = False
                else:
                    bAsGPs,contype = True,"GP"
            if bOK and bAsDPs:
                if ftype==3:
                    sourcePathsAndNames = sourcePathsAndNamesPathfinderDPs
                rcode,pathToP,pathToVCFdir,hdcsfserrmsg = CheckForRequisiteHDCSstructure(self.parent,bSilent=True)
                if rcode!=wx.ID_OK or hdcsfserrmsg:
                    errmsg+=hdcsfserrmsg
                    bOK = False
                else:
                    dlg = PSSParamDialog.ConvertDPsParams(parent, self.PSS, None, pathToVCFdir)
                    dlg.CentreOnParent()
                    if dlg.ShowModal()!=PSSParamDialog.ID_CANCELCONVDP:
                        pathToPVD = pathToP.replace(os.sep,'/') + '/'+ dlg.convDPparams['defVCF'] + '/pending/'  # note:  YEAR-DOY pending until first DP encountered in ConvertLineData()
                        sourcePaths,sourceNames = [tple[0] for tple in sourcePathsAndNames],[tple[1] for tple in sourcePathsAndNames]
                        for sourceNamesIdx in range(len(sourceNames)):
                            sourceNames[sourceNamesIdx] = pathToPVD + sourceNames[sourceNamesIdx]
                        sourcePathsAndNames = zip(sourcePaths,sourceNames)
                        dlg.Destroy()
                    else:
                        if ftype==3: # PathfinderMDBFiles; might have desireable GPs data...
                            if bAsGPs:
                                bProceed = wx.MessageBox("Skipping DPs in Trimble/Pathfinder Database. \n"+
                                                         "Do you want to continue with import of GPs? ",
                                                         "Continue with Pathfinder GPs?", wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION, self)
                                if bProceed==wx.NO:  bOK = False
                        else:
                            bOK = False
            if bOK:
                # note: skip ignored for ConvertVelocWin & ConvertCarisSVP (hardcoded to convert all records)
                try: skip=int(self.HeaderTxt.GetValue())-1
                except: skip=0
                if skip<0: skip=0
                if ftype!=3:
                    sourcePaths = [tple[0] for tple in sourcePathsAndNames]
                if ftype==4: # Velocwin Diver Least Depth Report(s)
                    xmlobj = PyPeekXTF.CContactsFile()
                    xmlobj.Open("")
                    self.ConvertVelocwinDiverLDReportDPs(xmlobj,filenames,pathToPVD+linename)

                with ProgressProcess.SingleProgress(0,len(sourcePaths),"%.1f%% "+contype+" files inserted") as progbar:
                
                    for sourceIdx in range(len(sourcePaths)):
                        xmlobj = PyPeekXTF.CContactsFile()
                        xmlobj.Open("")
                        sourcePath = sourcePaths[sourceIdx]
                        if ftype!=3:
                            sourceName = sourcePathsAndNames[sourceIdx][1]
                        if ftype==0 or ftype==5:
                            fext = os.path.splitext(sourcePath)[-1].lower()
                            if fext in self.ADODB_EXT:
                                bRetainADORecordsetSetting = self.RetainDBRecordsetData.GetValue()
                                # todo: note--not allowing disconnected recordsets for DPs, until absolute tsortedIdxs is retained as well AND updated according to DP edit migration (use has based on un-editable fields for dbkey, or otherwise unique key--as is done w/ AWOIS RECID)
                                bRetainADORecordset = bRetainADORecordsetSetting and not bAsDPs
                                self.ConvertADOdb(xmlobj,sourcePath,sourceName,bAsDPs,bUseS57AttrData,oAcronym,bRetainADORecordset,skip)
                            elif fext in self.OGRDB_EXT:
                                if fext in (".mif",".mid",".tab",".gml",".kml"): # jlr: OGR uses mitab for MIF/MID access, and that means one (vice zero) based indices; also empirically see same for gml (Notebook export) and kml
                                    startIdx = 1
                                else:
                                    startIdx = 0
                                self.ConvertOGRdb(xmlobj,sourcePath,sourceName,bAsDPs,bUsePtGeomData,bUseS57AttrData,oAcronym,skip,startIdx)
                            else:
                                self.ConvertTXT(xmlobj,sourcePath,sourceName,bAsDPs,bUseS57AttrData,oAcronym,skip)
                        elif ftype==1:
                            self.ConvertVelocWin(xmlobj,sourcePath,sourceName)
                        elif ftype==2:
                            self.ConvertCarisSVP(xmlobj,sourcePath,sourceName)
                        elif ftype==3:
                            sourceNameGPs,sourceNameDPs = [],[]
                            if bAsGPs:  sourceNameGPs = sourcePathsAndNamesPathfinderGPs[sourceIdx][1] # else = [], per above
                            if bAsDPs:  sourceNameDPs = sourcePathsAndNames[sourceIdx][1] # ibid.; note that sourcePathsAndNamesPathfinderDPs + PathToPVD info --> sourcePathsAndNames, above
                            self.ConvertPathfinderDatabaseGPsDPs(xmlobj,sourcePath,sourceNameGPs,sourceNameDPs,skip) # note: intention is bUsePtGeomData==bUseS57AttrData==True (oAcronym on-the-fly)
                        progbar.Update(sourceIdx)
        if not bOK and errmsg:
            wx.MessageBox(errmsg, 'Error', wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)

    def OnOpenDataFile(self, event):
        rcode,filename = RegistryHelpers.GetFilenameFromUser(self, bSave=0, RegistryKey="OpenGPSourceFile", fFilter="|".join(("All Files|*.*","|".join(self.DB_TYPES))))
        if rcode==wx.ID_OK:
            self.LoadDataFile(filename)
            self.openedfile = filename
            self.sbar.SetStatusText("File: %s"%filename,0)
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
                    wx.MessageBox("There was an error reading the OGR dataset. \n"+
                                  "See the console window for more information. ",
                                  "Error", wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
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
                wx.MessageBox("There was an error reading the ADO dataset. \n"+
                              "See the console window for more information. ",
                              "Error", wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
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
    def LoadDataFile(self, filename):
        self.FileDisplay.ClearAll()
        line,maxlenLine = 0,(0,0)
        self.InitNamedFields()
        fext = os.path.splitext(filename)[-1].lower()
        if fext in self.OGRDB_EXT: # OGR-supported formats
            ogrdataset,self.NamedChoices = GetOGRDatasetLayer(filename, parentwin=self)
            self.NamedDelim = self.DBFIELD_DELIM
            if ogrdataset:
                for data in self.OGRDatasetLineGenerator(ogrdataset, self.DATA_LINES):
                    self.FileDisplay.AddText(data+'\n')
                    # BUGFIX: maxlenLine used to scale horizontal scroll bar (otherwise doesn't resize)
                    lenLine=len(data)+1
                    if lenLine > maxlenLine[-1]: maxlenLine=(line,lenLine)
                    line+=1
        elif fext in self.ADODB_EXT: # ADO-supported formats
            tblsheetName,adoconn,adors = ContactFunctions.GetADOConnectionViaMSJetProvider(filename, parentwin=self)
            if adors:
                self.NamedDelim,self.NamedChoices = self.DBFIELD_DELIM,map(lambda idx,fielditem=adors.Fields.Item: fielditem(idx).Name, range(adors.Fields.Count))
                for data in self.ADORSLineGenerator(adors, self.DATA_LINES):
                    self.FileDisplay.AddText(data+'\n')
                    # BUGFIX: maxlenLine used to scale horizontal scroll bar (otherwise doesn't resize)
                    lenLine=len(data)+1
                    if lenLine > maxlenLine[-1]: maxlenLine=(line,lenLine)
                    line+=1
        else: # otherwise text-based file (w/ or w/o an extension)
            for data in self.TextfileReadlineGenerator(filename):
                if line > self.DATA_LINES:
                    break
                self.FileDisplay.AddText(data)
                # BUGFIX: maxlenLine used to scale horizontal scroll bar (otherwise doesn't resize)
                lenLine=len(data)+1
                if lenLine > maxlenLine[-1]: maxlenLine=(line,lenLine)
                line+=1
        maxlenLine=maxlenLine[0]
        self.FileDisplay.GotoPos(self.FileDisplay.GetLineEndPosition(maxlenLine)) # BUGFIX: scale horizontal scroll bar (thumb)
        self.FileDisplay.GotoPos(0)
        self.maxlenLine = maxlenLine
        self.InitControls()
    def OnSaveTemplate(self, event):
        rcode, filename = RegistryHelpers.GetFilenameFromUser(self, bSave=1, RegistryKey="OpenGPTemplate", fFilter="GP Feature Parser|*.afp")
        if rcode==wx.ID_OK:
            fil=open(filename, "w+")
            self.UpdateData()
            ver=7
            cPickle.dump(ver, fil)
            cPickle.dump(self.NamedDelim, fil)
            cPickle.dump(self.NamedChoices, fil)
            cPickle.dump(self.Data, fil)
            cPickle.dump(self.HeaderTxt.GetValue(), fil)
            cPickle.dump(self.MultiDelim.GetValue(), fil)
            cPickle.dump(self.InsertAs.GetStringSelection(), fil)
            cPickle.dump(self.RetainDBRecordsetData.GetValue(), fil)
            cPickle.dump(self.UseS57AttrData.GetValue(), fil)
            cPickle.dump(self.S57ObjectClass.GetStringSelection(), fil) # use string vice id, as choice could change in the future--with name being more stable than index
            cPickle.dump(self.UsePointGeomData.GetValue(), fil)
            cPickle.dump(self.FileDisplay.GetText(), fil)
            cPickle.dump(self.openedfile, fil)
    def OnOpenTemplate(self, event):
        if event.GetId()==self.clearID:
            rcode,filename = wx.ID_OK,self.PathToEmptyForm
        else:
            rcode,filename = RegistryHelpers.GetFilenameFromUser(self, bSave=0, RegistryKey="OpenASCIITemplate", fFilter="ASCII Feature Parser|*.afp")
        if rcode==wx.ID_OK:
            self.OpenTemplate(self.PathToEmptyForm) # clear in any case, as previous versions of parser files may not wipe out any new settings that are active in the dialog
            if filename!=self.PathToEmptyForm:
                self.OpenTemplate(filename)
    def OpenTemplate(self, filename):
        fil=open(filename, "r")
        ver=cPickle.load(fil)
        self.NamedDelim = cPickle.load(fil)
        self.NamedChoices = cPickle.load(fil)
        self.Data = cPickle.load(fil)
        self.MakeCategories() #rebuild combined dictionary containing Data and Windows Controls
        self.InitS57ObjClassChoices() #clear s57 object class ctrl--otherwise, as a SetStringSelection("") below doesn't clear anything
        if ver==1:
            self.SoundingFactor = cPickle.load(fil) #garbage
            self.HeaderTxt.SetValue("1")
            self.MultiDelim.SetValue(False)
        elif ver==2:
            self.HeaderTxt.SetValue(cPickle.load(fil))
            self.MultiDelim.SetValue(cPickle.load(fil))
        elif ver==3:
            self.HeaderTxt.SetValue(cPickle.load(fil))
            self.MultiDelim.SetValue(cPickle.load(fil))
            if cPickle.load(fil): txtInsertAs="Chart GPs"
            else: txtInsertAs="GPs"
            self.InsertAs.SetStringSelection(txtInsertAs)
        elif ver==4:
            self.HeaderTxt.SetValue(cPickle.load(fil))
            self.MultiDelim.SetValue(cPickle.load(fil))
            bAsChartGPs=cPickle.load(fil)
            self.RetainDBRecordsetData.SetValue(cPickle.load(fil))
            if bAsChartGPs: txtInsertAs="Chart GPs"
            else: txtInsertAs="GPs"
            self.InsertAs.SetStringSelection(txtInsertAs)
        elif ver==5:
            self.HeaderTxt.SetValue(cPickle.load(fil))
            self.MultiDelim.SetValue(cPickle.load(fil))
            bAsChartGPs=cPickle.load(fil)
            bAsCheckpoints=cPickle.load(fil)
            self.RetainDBRecordsetData.SetValue(cPickle.load(fil))
            self.UseS57AttrData.SetValue(cPickle.load(fil))
            self.S57ObjectClass.SetStringSelection(cPickle.load(fil))
            self.UsePointGeomData.SetValue(cPickle.load(fil))
            self.FileDisplay.SetText(cPickle.load(fil))
            self.openedfile = cPickle.load(fil)
            if bAsChartGPs: txtInsertAs="Chart GPs"
            elif bAsCheckpoints: txtInsertAs="Checkpoints"
            else: txtInsertAs="GPs"
            self.InsertAs.SetStringSelection(txtInsertAs)
        elif ver==6:
            self.HeaderTxt.SetValue(cPickle.load(fil))
            self.MultiDelim.SetValue(cPickle.load(fil))
            bAsChartGPs=cPickle.load(fil)
            bAsCheckpoints=cPickle.load(fil)
            self.RetainDBRecordsetData.SetValue(cPickle.load(fil))
            self.UseS57AttrData.SetValue(cPickle.load(fil))
            self.S57ObjectClass.SetStringSelection(cPickle.load(fil))
            self.UsePointGeomData.SetValue(cPickle.load(fil))
            self.FileDisplay.SetText(cPickle.load(fil))
            self.openedfile = cPickle.load(fil)
            bAsDPs=cPickle.load(fil)
            if bAsDPs: txtInsertAs="DPs"
            elif bAsChartGPs: txtInsertAs="Chart GPs"
            elif bAsCheckpoints: txtInsertAs="Checkpoints"
            else: txtInsertAs="GPs"
            self.InsertAs.SetStringSelection(txtInsertAs)
        elif ver==7:
            self.HeaderTxt.SetValue(cPickle.load(fil))
            self.MultiDelim.SetValue(cPickle.load(fil))
            self.InsertAs.SetStringSelection(cPickle.load(fil))
            self.RetainDBRecordsetData.SetValue(cPickle.load(fil))
            self.UseS57AttrData.SetValue(cPickle.load(fil))
            self.S57ObjectClass.SetStringSelection(cPickle.load(fil))
            self.UsePointGeomData.SetValue(cPickle.load(fil))
            self.FileDisplay.SetText(cPickle.load(fil))
            self.openedfile = cPickle.load(fil)
        self.OnInsertAsChoice() # to handle [dis,en]able of Time & ObsDepth Use, per InsertAs DPs status
        #self.UpdateData()
        self.InitControls()
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
            bIgnoreMultiDelim = self.MultiDelim.GetValue()
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
                bProceed = wx.MessageBox("The named fields in the data set being processed do \n"+
                                         "not match those in the current data parser template. \n"+
                                         "The parsed attributes from %s \n"%os.path.basename(sourcePath)+
                                         "will be limited to those matches in the template: \n"+
                                         "\n"+
                                         "Templated fields not present in current dataset layer(s): \n"+
                                         "   %s \n"%",".join(missingNamedFields)+
                                         "\n"+
                                         "Continue with this file? ('No' to skip) \n",
                                         'Warning: Named Field Mismatch -- Continue with this file?', wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION, self)
                if bProceed==wx.NO: bOK=False
            if bOK:
                fieldsAndGeomGen = self.OGRDatasetFieldGenerator(ogrdataset, skip, startIdx)
                getFieldStrings=self.GetFieldStringsFromOGR
                bOk,numfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs, bUsePtGeomData, bUseS57AttrData, oAcronym)
                if (numfeatures > 0) and not (bAsDPs and not bOk):
                    self.ConvertLineData(xmlobj, sourceName, bAsDPs, bTimeSortCon=bAsDPs)
    def ConvertTXT(self, xmlobj, sourcePath, sourceName, bAsDPs, bUseS57AttrData, oAcronym, skip=0):
        fieldsAndGeomGen = self.TextFieldsGenerator(sourcePath, skip)
        getFieldStrings = self.GetFieldStringsFromText
        bOk,numfeatures = self.ParseLineData(xmlobj, sourceName, fieldsAndGeomGen, getFieldStrings, bAsDPs, bUseS57AttrData=bUseS57AttrData, oAcronym=oAcronym)
        if (numfeatures > 0) and not (bAsDPs and not bOk):
            self.ConvertLineData(xmlobj, sourceName, bAsDPs, bTimeSortCon=bAsDPs)
    def ParseLineData(self, xmlobj, sourceName,  fieldsAndGeomGen, getFieldStrings, bAsDPs, bUsePtGeomData=False, bUseS57AttrData=False, oAcronym=None):
        # re-entrant/accumulation functionality via single line in xmlobj argument
        cl = PyPeekXTF.CContactLine()
        if xmlobj.GetNumLines()==0:
            xmlobj.AddLine(sourceName, cl)
        else:
            xmlobj.GetLine(0, cl)
        if bAsDPs:
            contype="DP"
            defaultVCF = sourceName.split('/')[-3]
        else: #bAsChartGPs, bAsCheckpoints, or [generic] GPs
            contype="GP"
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
        con,pt = PyPeekXTF.CContact(),PyPeekXTF.CContactPoint()
        currUser,currTimeStr = self.PSS.GetUser(),"%.0f"%time.time()
        oAcronymPrev = oAcronym 
        for featureStuff,featureGeom in fieldsAndGeomGen:
            try:
                oAcronym,feature = featureStuff
                if oAcronym != oAcronymPrev:
                    aAcronymsNOAA = set(itertools.chain(*NOAAcarto.s57noaafeatures[oAcronym]))
            except:
                feature = featureStuff
            bFilteredRecord = False
            conNumStr = str(recIdx)
            if bAsDPs:
                conNumStr+='/1' # DPs use pseudo profile/beam
            cl.AddContact(conNumStr, con) # ConvertData() will override con name subsequent to (any) (re)sort
            con.SetType(contype) # "GP" or "DP", per above
            con.SetFlags("%08x"%QUA3_STATUS)  # Initialize items to be unrejected w/quality=3
            con.AddPoint("1", pt) # need a point even if bUsePtGeomData, as other attributes need access to a point structure
            if bAsDPs:
                con.SetVesselHeading('000') # todo: add to parser dialog
                con.SetVesselName(defaultVCF)
                con.SetTGTEvent(str(recIdx))
                pt.SetProfile(str(recIdx))
                pt.SetBeam('1')
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
                                con.Remove()
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
                                if val=="TimeParseFailed":
                                    raise ValueError
                            if data[self.ADV_BUTTON]=="Units":
                                val = str(float(val)*data[self.ADV_FUNC][self.FACTOR])
                            elif name in (self.LATDATATYPE_STR,self.LONDATATYPE_STR,self.OLATDATATYPE_STR,self.OLONDATATYPE_STR):
                                if data[self.ADV_FUNC][self.COORDTYPE]==0:
                                    if data[self.ADV_FUNC][self.RADIANS]==0:
                                        deg,strin = self.parser.ParseString(val)
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
                            pt.SetObsDepth(NULLDEPTHstr)
                        elif name=="Time":
                            pt.SetTime(NULLTIMEstr)
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
                                pt.SetDepth(valStr)
                                obsDepthStr = pt.GetObsDepth(NULLDEPTHstr)[-1]
                                if obsDepthStr==NULLDEPTHstr:
                                    pt.SetObsDepth(valStr)
                            try:
                                s57data[oAcronym][aAcronym] = NOAAcarto.GetS57AcronymDataFromNominalValue(aAcronym, valStr)
                            except:
                                print "*** Skipping INVALID S-57 object/attribute '%s/%s' value(s)=%s for %s - %s"%(oAcronym,aAcronym,valStr,cl.GetName()[-1],conNumStr)
                    ContactFunctions.SetS57ContactData(con, s57data, bClearAllExisting=False)
                    con.SetEvent("UserS57Edit", currUser, currTimeStr)
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
                    pt.SetLatitude(str(newlat))
                    pt.SetLongitude(str(newlon))
                elif ObsLat[self.ADV_FUNC][self.CALCRB] or ObsLon[self.ADV_FUNC][self.CALCRB]: # note: calc lat/lon from olat/lon + dist/az mutually exclusive of vice-versa; really should have a validator to prevent user from specifying double (redundant) calc
                    olat,olon = pt.GetLatitudeDouble(),pt.GetLongitudeDouble()
                    dist,az = pt.GetRangeDouble(),pt.GetAzimuthDouble()
                    newlat,newlon,baz = PyPeekXTF.PyForwardAzDeg(olat, olon, dist, az)
                    #print olat, olon, newlat, newlon
                    pt.SetObsLatitude(str(newlat))
                    pt.SetObsLongitude(str(newlon))
            else: # get (multi)pt data from OGR feature geometry ("POINT","LINESTRING","MULTIPOINT","POLYGON",...)
                # note: leaving multipt data in (any) DPs (only pt 0 is [currently] written out to HIPS
                # todo: don't ignore range/azimuth advanced processing prefs
                fgeomrefname,fgeomXYlist = featureGeom
                if bInUTM:
                    #fgeomXYlist = [(-lon,lat) for lat,lon in [PyUTMToWGS84(zoneUTM,east,north,"N")[-2:] for east,north in fgeomXYlist]] # r,lat,lon--lon (-)E <-- PyUTMToWGS84, want [-lon,lat]s--(-)W
                    import mesh
                    fgeomXYlist = mesh.ConvertPointsToLL(fgeomXYlist, zoneUTM)
                elif bInRAD:
                    fgeomXYlist = [(lon*RAD2DEG,lat*RAD2DEG) for lon,lat in fgeomXYlist]
                nPts = len(fgeomXYlist)
                if nPts==1:
                    fgeomrefname="POINT"
                elif nPts==2:
                    fgeomrefname="MULTIPOINT"
                con.SetEvent("pointGeometry", currUser, fgeomrefname)
                # recall, we already have a pt instance in con for first point
                try:
                    longitude,latitude = fgeomXYlist[0] # get first point, regardless of type
                except IndexError:
                    bAnySkipped=True
                    print "-"*15, "No Geometry Found", "-"*15
                    print "Skipped feature record %d; check data file: %s"%(recIdx,sourceName)
                    con.Remove()
                    if not bAsDPs:
                        recIdx+=1 # but retain numbering--'bad' GP number(s) are skipped in PSS
                    continue # for feature,featureGeom in fieldsAndGeomGen
                latStr = "%.8f"%latitude
                lonStr = "%.8f"%longitude
                pt.SetObsLatitude(latStr)
                pt.SetObsLongitude(lonStr)
                pt.SetLatitude(latStr)
                pt.SetLongitude(lonStr)
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
                        con.AddPoint(str(ptIdx), pt)
                        pt.SetLatitude(latStr)
                        pt.SetLongitude(lonStr)
                        pt.SetObsLatitude(latStr)
                        pt.SetObsLongitude(lonStr)
                        #if timeStr: pt.SetTime(timeStr) # repeat pt 1's time,depth,odepth,range,azimuth,tide? (see comment above)
                        #if depthStr: pt.SetDepth(depthStr)
                        #if odepthStr: pt.SetObsDepth(odepthStr)
                        #if rangeStr: pt.SetRange(rangeStr)
                        #if azimuthStr: pt.SetAzimuth(azimuthStr)
                        #if tideStr: pt.SetTide(tideStr)
                        ptIdx+=1
            recIdx+=1
            oAcronymPrev = oAcronym 
        if bCriticalParserException:
            wx.MessageBox('Failed to parse required data field "%s" in record #%d. \n'%(name,recIdx)+
                          "Zero %s inserted.  Check your template and input \n"%(contype+'s')+
                          "data file and try again. ",
                          'No %s Inserted -- Critical Parser Error'%(contype+'s'), wx.OK | wx.CENTRE | wx.ICON_ERROR, self)
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
                wx.MessageBox(msgText, msgTitle, wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
        numfeatures = recIdx-1
        return (not bCriticalParserException, numfeatures)
    def SortXMLLine0ByConPt0Time(self, xmlobj):
        clOld,clNew,con,pt = PyPeekXTF.CContactLine(),PyPeekXTF.CContactLine(),PyPeekXTF.CContact(),PyPeekXTF.CContactPoint()
        xmlobj.GetLine(0,clOld)
        clName = clOld.GetName()[-1]
        clOld.InitContactIterator()
        tsortedIdxs=[]
        conIdx=0
        while clOld.GetNextContact(con):
            con.GetPoint(0,pt)
            tsortedIdxs.append((conIdx,pt.GetTime()[-1]))
            conIdx+=1
        tsortedIdxs = [idxTimeTuple[0] for idxTimeTuple in SortBy(tsortedIdxs,1)]
        for idx in range(len(tsortedIdxs)): # change from absolute indexs to sequential-relative indexes (per sequential index changes each AppendContact takeaway, below)
            tsortedIdxs = tsortedIdxs[:idx] + [seqrelIdx - int(seqrelIdx > tsortedIdxs[idx]) for seqrelIdx in tsortedIdxs[idx:]]
        xmlobj.AddLine("_tempLcopy_",clNew)
        for conIdx in tsortedIdxs:
            clOld.GetContact(conIdx,con)
            clNew.AppendContact(con)
        clOld.Remove()
        clNew.SetName(clName)
        return clNew
    def ConvertLineData(self, xmlobj, sourceName, bAsDPs=False, bTimeSortCon=False):
        if xmlobj.GetNumLines()==1:
            if bTimeSortCon:
                cl = self.SortXMLLine0ByConPt0Time(xmlobj)
                con,pt = PyPeekXTF.CContact(),PyPeekXTF.CContactPoint()
                cl.InitContactIterator()
                recIdx=1 # one-based index
                while cl.GetNextContact(con):
                    conNumStr = str(recIdx)
                    if bAsDPs:
                        con.GetPoint(0,pt)
                        pt.SetProfile(conNumStr)
                        conNumStr+='/1' # DPs use profile/beam for contact number
                    con.SetNumber(conNumStr)
                    recIdx+=1
            else:
                cl = PyPeekXTF.CContactLine()
                xmlobj.GetLine(0,cl)
            cl.SetDOB('DataDictionary.Convert', GetCurrentTimeStr())
            if bAsDPs:  # YEAR-DOY defaults to that date of first record; todo: ? put AddLine and this inside con loop, catching each date change (if so, do same for ContactFunctions.ConvertHypackTGTs)
                # note: upstream QC on sourceName guarantees non-overlapping "L" name for DPs; so, no QC needed on YEAR-DOY changes to protect against ConFile duplicate XML line/source namespace
                con,pt = PyPeekXTF.CContact(),PyPeekXTF.CContactPoint()
                cl.GetContact(0,con)
                con.GetPoint(0,pt)
                cl.SetName(sourceName.replace("pending",'-'.join(ContactFunctions.GetPtTimeStrs(pt)[:2])))
            self.PSS.AddContacts(xmlobj)
        else:
            wx.MessageBox('No data converted for "line": \n'+
                          "%s \n"%(sourceName)+
                          "Check your template and input data file(s). \n"+
                          "(E.g., make sure parser template value \n"+
                          "'Start at line' does not exceed the total \n"+
                          "number of records in (each of) the input \n"+
                          "data file(s).) ",
                          'No GPs/DPs Inserted', wx.OK | wx.CENTRE | wx.ICON_EXCLAMATION, self)
