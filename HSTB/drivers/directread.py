import sqlite3 as lite
from xml.dom import minidom
import enum
import os

class DirectNav(object):
    concreteAttributeEnum = enum.IntEnum("concreteObjectColumns", (('concreteObjectId',0), ('attributeId',1), ('integerValue',2), ('floatValue',3), ('stringValue',4))) 
    masterEditsetEnum = enum.IntEnum("masterEditsetColumns", (('id',0), ('lineId',1), ('type',2), ('source',3), ('state',4), ('startTime',5), ('endTime',6))) 
    def __init__(self, pathToHipsDatabase):
        '''(hdcsdatapath, proj, vess, yday, line) = SeparatePathFromPVDL(pathToPVDL)'''
        ME = self.masterEditsetEnum
        CA = self.concreteAttributeEnum
        self.dictObjId = {}
        self.pathToHipsDatabase = pathToHipsDatabase
        if os.path.exists(pathToHipsDatabase):
            with lite.connect(pathToHipsDatabase) as con:
                cur = con.cursor()
                self.table_names = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

                #iterate all the records rleated to Navigation data
                rows = cur.execute("SELECT * FROM concreteAttribute WHERE attributeId=17").fetchall()
                for row in rows:
                    objId = row[CA.concreteObjectId]
                    self.dictObjId[objId]={}
                    dom=minidom.parseString(row[CA.stringValue]) #string value holds an XML dataset describing raw data files and which HDCS line it relates to
                    
                    #Find the navigation element which specifies the dataset name used in other records
                    for e in dom.getElementsByTagName("Element"):
                        if e.getAttribute('Name') == "Navigation": 
                            self.dictObjId[objId]['DataName']=e.childNodes[0].nodeValue
                            dataname = e.childNodes[0].nodeValue
                            break
                        else: e=None
                    
                    #go up from the navigation element to element that would hold the path element which specifies the raw data file location
                    source_element = e.parentNode.parentNode.parentNode
                    source_element.attributes.items()  #[(u'Name', u'Source')]
                    for child in source_element.childNodes:
                        for attr in child.attributes.items():
                            if attr[0]=='Name' and attr[1]=='Path':
                                path_element = child
                                self.dictObjId[objId]['RawPath'] = str(path_element.childNodes[0].nodeValue)
                                self.dictObjId[objId][dataname] = str(path_element.childNodes[0].nodeValue)
                    
                    #Now find the HDCS line path for this record
                    for e in dom.getElementsByTagName("Element"):
                        if e.getAttribute('Name') == "Name":
                            try: 
                                if str(e.childNodes[0].nodeValue)=='HDCS':
                                    break
                            except:
                                e=None
                        else: 
                            e=None
                    if e:
                        for hdcs_converter_child in e.parentNode.childNodes:
                            if hdcs_converter_child.getAttribute('Name') == "Sources":
                                for sources_child in hdcs_converter_child.childNodes:
                                    if sources_child.getAttribute('Name') == "Source":
                                        for source_child in sources_child.childNodes:
                                            if source_child.getAttribute('Name') == "Path":
                                                self.dictObjId[objId]['HDCSPath'] = str(source_child.childNodes[0].nodeValue)
                    
                    #find the edits to Nav if any
                    rows = cur.execute("SELECT * FROM masterEditset WHERE lineId = %d"%objId).fetchall()
                    self.dictObjId[objId]['edits']={}
                    for row in rows:
                        self.dictObjId[objId]['edits'].setdefault(row[ME.source], {})[row[ME.id]]=(row[ME.startTime], row[ME.endTime])
                    
                rows = cur.execute("SELECT * FROM concreteAttribute WHERE attributeId=18").fetchall()
                for row in rows:
                    self.dictObjId[row[CA.concreteObjectId]]['ActiveNav'] = row[CA.stringValue] 
                #print self.dictObjId

        else:
            raise Exception("File Not Found "+pathToHipsDatabase)
    def ReadTimeSeries(self, pathToPVDL, bVerbose=False, oddFactorSkip=1, bOnlyAccepted=False):
        # Returns HDCS navigation data time series in N x 5 NumPyArray (inherently sorted by time)
        # (NumPyArray columns are time, lat, lon, accuracy, status; e.g., time vector=NumPyArray[:,0])
        # bVerbose controls return of tuple NumPyArray,"verboseData", as per that needed for quasi-verbatum reconstruction of data using WriteTimeSeries() method
        fname = None
        for id, obj in self.dictObjId.items():
            if obj['HDCSPath'].replace("/", "\\").lower()==pathToPVDL.replace("/", "\\").lower():
                fname = obj['RawPath']
                break
        fname =  r'E:\Data\Kongsberg\H12786_DN154_RawData\0000_20150603_135615_S5401.all'
        print 'changed rawpath to ', fname
        if fname:
            import par, datetime
            all = par.useall(fname, bShowProgress=False)
            nav = all.navarray['80']
            #apply edits
            for k, (starttime, endtime) in obj['edits']:
                nav = scipy.compress(scipy.logical_or(nav[:,0]<starttime,  nav[:,0]>endtime), nav, axis=0)
    
            if bVerbose:
                verboseData = {'summaryStatus':None, 'sourceFileName':None}
            
            (numRecords, minTime, maxTime, minLat, maxLat, minLon, maxLon) = (len(nav[:,1]), min(nav[:,0]), max(nav[:,0]), min(nav[:,2]), max(nav[:,2]), min(nav[:,1]), max(nav[:,1]))
            minTime = PosixToUTCs80(minTime)
            maxTime = PosixToUTCs80(maxTime)
            if bVerbose:
                verboseData['summaryStatus']=ZERO_STATUS
                # ReadLineSummary for sourceFileName (note reread of numRecords)
                verboseData['sourceFileName']=fname
            NumPyArray=scipy.zeros((numRecords, 5), scipy.float64)
            rcodeCaris, accuracy, status = 0,0,0 
            for recordNum in xrange(numRecords):
                (posix_time,longitude,latitude) = nav[recordNum]
                tyme = PosixToUTCs80(posix_time)
                
                NumPyArray[recordNum] = [tyme,latitude*Constants.DEG2RAD(),longitude*Constants.DEG2RAD(),accuracy,status]
            if oddFactorSkip > 1:
                oddFactorSkip = int(oddFactorSkip)
                if not oddFactorSkip%2: oddFactorSkip+=1
                NumPyArray = NumPyArray[oddFactorSkip/2:len(NumPyArray)-oddFactorSkip/2:oddFactorSkip]
            if bVerbose:
                return NumPyArray,verboseData
            else:
                return NumPyArray
    def WriteTimeSeries(self, pathToPVDL, NumPyArray, verboseData=None, sourcename='', sourceTypeExt='', haveaccuracy=(1,None), havestatus=(1,None), sortBytime=True):
        raise Exception("DirectReadNav does not support writing")
