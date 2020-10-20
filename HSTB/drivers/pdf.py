import copy
from time import gmtime, asctime, localtime

from reportlab.platypus import BaseDocTemplate, PageTemplate, NextPageTemplate, Frame, \
                        Paragraph, Preformatted, XPreformatted, Table, TableStyle, Image, Spacer, \
                        CondPageBreak, KeepTogether, PageBreak
from reportlab.lib import pagesizes
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.sequencer import getSequencer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing,_DrawingEditorMixin
from reportlab.graphics.charts.barcharts import VerticalBarChart,HorizontalBarChart
from reportlab.graphics.charts.linecharts import VerticalLineChart,HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie,Pie3d
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgets.grids import ShadedRect
from reportlab.graphics.widgets.markers import makeMarker

from HSTB.shared import Constants


defaultPageSize = (8.5*inch, 11*inch)
html2space = 2*"&nbsp;"

USstateAndTerritoryNames = [
    'Alabama',       'Alaska',              'American Samoa', 'Arizona',
    'Arkansas',      'California',          'Colorado',       'Connecticut',
    'Delaware',      'District of Columbia','Florida',        'Georgia',
    'Guam',          'Hawaii',              'Idaho',          'Illinois',
    'Indiana',       'Iowa',                'Kansas',         'Kentucky',
    'Louisiana',     'Maine',               'Maryland',       'Massachusetts',
    'Michigan',      'Minnesota',           'Mississippi',    'Missouri',
    'Montana',       'Nebraska',            'Nevada',         'New Hampshire',
    'New Jersey',    'New Mexico',          'New York',       'North Carolina',
    'North Dakota',  'Ohio',                'Oklahoma',       'Oregon',
    'Pennsylvania',  'Puerto Rico',         'Rhode Island',   'South Carolina',
    'South Dakota',  'Tennessee',           'Texas',          'Utah',
    'Vermont',       'Virgin Islands',      'Virginia',       'Washington',
    'West Virginia', 'Wisconsin',           'Wyoming'
    ]

USstateAndTerritoryAbbr = [
    'AL', 'AK', 'AS', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC',
    'FL', 'GA', 'GU', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY',
    'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE',
    'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR',
    'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VI',
    'VA', 'WA', 'WV', 'WI', 'WY'
    ]

# str -> utf-8 unicode, for reportlab 2.x compatibility
def GetUnicode(obj):
    try:
        if type(obj) is UnicodeType: return obj
        elif type(obj) is StringType:
            # our xml "text" values are (in general) a mixture of characters and byte code(s)--the latter per some unicode character(s)
            # treat as 'utf-8' (subset); failing that, go with latin-1 compatible 'iso-8859-1' (superset)
            # so, no problem if single unicoding; otherwise, latin-1 characters take precedence (where utf-8 non iso-8859-1 characters will be mangled) 
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return obj.decode('iso-8859-1')
        elif type(obj) is ListType: return map(GetUnicode,obj)
        else: return obj
    except:
        return obj


class PieFigure(_DrawingEditorMixin,Drawing):
    def __init__(self,width=200,height=150,pieType="Pie",bShowBoundary=False,*args,**kw):
        Drawing.__init__(self,width,height,*args,**kw)
        if pieType=="Pie":
            self._add(self,Pie(),name='chart',validate=None,desc="The pie object")
        else: #default to Pie3d
            self._add(self,Pie3d(),name='chart',validate=None,desc="The pie object")
        if bShowBoundary:
            self.background = ShadedRect()
            self.background.fillColorStart = colors.white
            self.background.fillColorEnd = colors.white
            self.background.numShades = 1
            self.background.strokeWidth = 0.5
            self.background.height = height
            self.background.width = width
        #self._add(self,0,name='preview',validate=None,desc=None)
    def GetChart(self):
        return self.chart
    def SetLabels(self,labelList,labelRadiusFraction=0.70,fontname="Helvetica-Bold",fontsize=10):
        self.chart.labels = labelList
        self.chart.slices.labelRadius = labelRadiusFraction
        self.chart.slices.fontName = fontname
        self.chart.slices.fontSize = fontsize
        self.chart.slices.fontColor = colors.black
    def GetLegend(self):
        return self.Legend
    def SetLegend(self,colorsAndLabels,x=None,y=None,dxChartSpace=36,legendAlign='right',fontname="Helvetica-Bold",fontsize=10,dxTextSpace=10,dy=10,dx=10,dySpace=15,maxCols=2):
        self._add(self,Legend(),name='Legend',validate=None,desc="The pie legend object")
        self.Legend.fontName = fontname
        self.Legend.fontSize = fontsize
        self.Legend.dxTextSpace = dxTextSpace
        self.Legend.dy = dy
        self.Legend.dx = dx
        self.Legend.deltay = dySpace
        self.Legend.alignment = legendAlign
        self.Legend.columnMaximum = maxCols
        self.Legend.colorNamePairs = colorsAndLabels
        if None in (x,y):
            x = self.chart.x+self.chart.width+dxChartSpace
            legendY1,legendY2 = self.Legend.getBounds()[1::2]
            legendH = abs(legendY2-legendY1)
            figH = self.height
            y = figH/2+legendH/2 # drawing is relative to document template flowable space --> self.x,self.y=0,0 (although these are real attributes)
        self.Legend.x = x
        self.Legend.y = y
    #def GetTitle(self):
    #    return self.Title
    #def SetTitle(self,x=None,y=None,titleText="",w=None,h=None,titleAlign='middle',fontname="Helvetica-Bold",fontsize=7):
    #    if None in (x,y):
    #        x,y = [val/2 for val in self.chart.getBounds()[-2:]] #chartMaxX/2,chartMaxY/2
    #    self._add(self,Label(),name='Title',validate=None,desc="The pie title object")
    #    self.Title.fontName = fontname
    #    self.Title.fontSize = fontsize
    #    self.Title.x = x
    #    self.Title.y = y
    #    self.Title._text = titleText
    #    self.Title.maxWidth = w
    #    self.Title.height = h
    #    self.Title.textAnchor = titleAlign
    def ReCenterXs(self):
        try:
            spaceRight = self.width - self.Legend.getBounds()[2]
        except:
            spaceRight = self.width - self.chart.width
        self.chart.x += spaceRight/2.
        try:
            self.Legend.x += spaceRight/2.
        except:
            pass

class ReportPageTemplate(PageTemplate):
    def __init__(self, id, pageSize=defaultPageSize, top=1, bottom=1, left=1, right=1):
        self.pagesize,(self.pageWidth,self.pageHeight) = pageSize,pageSize
        self.nTop,self.nBottom,self.nLeft,self.nRight = top*inch,bottom*inch,left*inch,right*inch
        frameList = self.CreateTemplateFrames()      # overload this virtual function in all derived classes
        PageTemplate.__init__(self, id, frameList, pagesize=pageSize)   # note lack of onPage
    def CreateTemplateFrames(self):
        raise "Must overload CreateTemplateFrame()"

class FrontSummaryTemplate(ReportPageTemplate):
    def CreateTemplateFrames(self):
        return [Frame(self.nLeft,
                      self.nBottom,
                      self.pageWidth - (self.nLeft + self.nRight),
                      self.pageHeight - (self.nTop + self.nBottom),
                      id='cover',
                      leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)]
    def afterDrawPage(self, canvas, doc):
        canvas.saveState()
        if doc.page==1:
            canvas.setFont('Times-Italic',8)
            canvas.drawString(self.nLeft, 0.75*self.nBottom, "Generated by Pydro v%s on %s [UTC]"%(Constants.PydroFullVersion(),asctime(gmtime())))
        else:
            canvas.setFont('Times-Roman',10)
            canvas.drawCentredString(doc.pagesize[0] / 2, 0.75*self.nBottom, 'Page %d' % canvas.getPageNumber())
        canvas.restoreState()

class ChapterCoverTemplate(ReportPageTemplate):
    def CreateTemplateFrames(self):
        return [Frame(self.nLeft,
                      self.nBottom,
                      self.pageWidth - (self.nLeft + self.nRight),
                      0.65*self.pageHeight - self.nBottom, id='chcover',
                      leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)]

class ColumnsTemplate(ReportPageTemplate):
    def __init__(self, id, pageSize=defaultPageSize, top=1, bottom=1, left=1, right=1, ncols=1, colsep=0.25):
        self.nCols,self.nCol = ncols,colsep*inch
        top = max(1,top)    # for room for afterDrawPage stuff at top of page
        ReportPageTemplate.__init__(self, id, pageSize, top, bottom, left, right)
    def CreateTemplateFrames(self):
        colWidth = (1./self.nCols) * (self.pageWidth - (self.nLeft + (self.nCols-1)*self.nCol + self.nRight))
        frameList = [Frame(self.nLeft,
                           self.nBottom,
                           colWidth,
                           self.pageHeight - (self.nTop + self.nBottom),
                           id='0',
                           leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)]
        for idNo in range(1,self.nCols):
            frameList.append(Frame(self.nLeft + idNo*(self.nCol+colWidth),
                                   self.nBottom,
                                   colWidth,
                                   self.pageHeight - (self.nTop + self.nBottom),
                                   id='%s'%idNo,
                                   leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0))
        return frameList
    def afterDrawPage(self, canvas, doc):
        y = self.pageHeight - .7*self.nTop
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.drawString(self.nLeft, y+8, doc.title)
        canvas.drawRightString(self.pageWidth - self.nRight, y+8, doc.chapter)
        canvas.line(self.nLeft, y, self.pageWidth - self.nRight, y)
        canvas.drawCentredString(doc.pagesize[0] / 2, 0.75*self.nBottom, 'Page %d' % canvas.getPageNumber())
        canvas.restoreState()

class FeatureReportTemplate(BaseDocTemplate):
    def __init__(self,filename,title,subject,author,pagesize=defaultPageSize, top=1, bottom=1, left=1, right=1, col=0.25):
        self.nTop,self.nBottom,self.nLeft,self.nRight,self.nCol = top,bottom,left,right,col
        self.pagesize = pagesize
        BaseDocTemplate.__init__(self,filename,pagesize=pagesize)
        if not title: title=u"Pydro Feature Report"
        if not author: author=u"NOAA"
        if not subject: subject=u"NOAA Hydrographic Survey"
        self.title,self.author,self.subject = GetUnicode([title,author,subject])
        styleSheet = getSampleStyleSheet()
        styleSheet.add(ParagraphStyle(name='CenteredHeading1',
                                      parent=styleSheet['Title'],
                                      alignment=TA_CENTER), alias='cenh1')
        styleSheet.add(ParagraphStyle(name='CenteredHeading2',
                                      parent=styleSheet['Heading2'],
                                      alignment=TA_CENTER), alias='cenh2')
        styleSheet.add(ParagraphStyle(name='CenteredLabel2',
                                      parent=styleSheet['Heading2'],
                                      alignment=TA_CENTER), alias='clab2')
        styleSheet.add(ParagraphStyle(name='FigCaption',
                                      parent=styleSheet['Italic'],
                                      alignment=TA_CENTER), alias='figc')
        styleSheet.add(ParagraphStyle(name='CenteredDisc',
                                      parent=styleSheet['BodyText'],
                                      alignment=TA_CENTER), alias='cend')
        self._T1 = styleSheet['Title']            # fontbasesize=18
        self._H2 = styleSheet['Heading2']         # fontbasesize=14
        self._CH1 = styleSheet['CenteredHeading1']# fontbasesize=18
        self._CH2 = styleSheet['CenteredHeading2']# fontbasesize=14
        self._CL2 = styleSheet['CenteredLabel2']  # fontbasesize=14
        self._FC = styleSheet['FigCaption']       # fontbasesize=10
        self._PC = copy.copy(styleSheet['FigCaption']) # fontbasesize=10
        self._PC.name = 'PicCaption' # not conditioned upon in afterFlowable()--for X.X.n labeling
        self._B = styleSheet['BodyText']          # fontbasesize=10
        self._CB = styleSheet['CenteredDisc']     # fontbasesize=10
        self._BU = styleSheet['Bullet']           # fontbasesize=10
        self.seq = getSequencer()
        self.seq.setFormat('Chapter','1')    # TODO: change to 'Section'
        self.seq.reset('Chapter')
        self.seqChapter = {}
        self.seq.setFormat('Section','1')    # TODO: change to 'SubSection'
        self.seq.reset('Section')
        self.seq.setFormat('Figure', '1')
        self.seq.reset('Figure')
        self.seqchainChapterSection = {}
        self.seq.chain('Section','Figure')
        self.report = {}
        self.reportOutlineLabels = {}
    def getReportChActiveTemplateFrameSize(self,chapter):
        try:
            for flw in self.report.get(chapter,[])[::-1]:
                if isinstance(flw,NextPageTemplate):
                    return self.pageTemplateSize[flw.action[-1]]
        except:
            return self.pagesize
    def getReportChFlowablesList(self,chapter):
        return self.report.get(chapter,None)
    def initReportChFlowablesList(self,chapter):
        self.report[chapter] = []
        self.seqchainChapterSection[chapter] = 0
    def afterInit(self):
        self.pageTemplateSize = {}
        self.addPageTemplates(FrontSummaryTemplate('Cover', self.pagesize,self.nTop,self.nBottom,self.nLeft,self.nRight))
        self.pageTemplateSize['Cover'] = tuple([getattr(self.pageTemplates[-1].frames[0],dStr) for dStr in ("width","height")])
        self.addPageTemplates(ChapterCoverTemplate('ChCover', self.pagesize,self.nTop,self.nBottom,self.nLeft,self.nRight))
        self.pageTemplateSize['ChCover'] = tuple([getattr(self.pageTemplates[-1].frames[0],dStr) for dStr in ("width","height")])
        self.addPageTemplates(ColumnsTemplate('Normal', self.pagesize,self.nTop,self.nBottom,self.nLeft,self.nRight,ncols=1))
        self.pageTemplateSize['Normal'] = tuple([getattr(self.pageTemplates[-1].frames[0],dStr) for dStr in ("width","height")])
        self.addPageTemplates(ColumnsTemplate('TwoColumn', self.pagesize,self.nTop,self.nBottom,self.nLeft,self.nRight,ncols=2,colsep=self.nCol))
        self.pageTemplateSize['TwoColumn'] = tuple([getattr(self.pageTemplates[-1].frames[0],dStr) for dStr in ("width","height")])
        self.addPageTemplates(ColumnsTemplate('ThreeColumn', self.pagesize,self.nTop,self.nBottom,self.nLeft,self.nRight,ncols=3,colsep=self.nCol))
        self.pageTemplateSize['ThreeColumn'] = tuple([getattr(self.pageTemplates[-1].frames[0],dStr) for dStr in ("width","height")])
        self.chapter = ""
        self._uniqueKeyChapterNo = 1
        self._uniqueKeySectionNo = 1
        self._uniqueKeyFigureNo = 1
    def beforeDocument(self):
        self.canv.showOutline()
        self.canv.setTitle(self.title)
        self.canv.setSubject(self.subject)
        self.canv.setAuthor(self.author)
    def afterFlowable(self, flowable):
        """Detect Level 1 and 2 headings (, build outline,
        and track chapter title."""
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style in ('Title', 'CenteredHeading1'):
                self.chapter = flowable.getPlainText()
                if style=='CenteredHeading1' and not self.chapter:
                    self.chapter='Summary'
                print "Chapter = %s"%self.chapter
                key = 'ch%d' % self._uniqueKeyChapterNo
                self.canv.bookmarkPage(key)
                try:
                    outlineEntryText = self.reportOutlineLabels[flowable.getPlainText()]
                except:
                    outlineEntryText = ''
                if not outlineEntryText:
                    outlineEntryText = self.chapter
                self.canv.addOutlineEntry(outlineEntryText, key, 0, 0)
                self._uniqueKeyChapterNo = self._uniqueKeyChapterNo + 1
                self._uniqueKeySectionNo = 1
                self._uniqueKeyFigureNo = 1
            elif style in ('Heading2', 'CenteredHeading2'):
                self.section = flowable.text
                key = 'ch%ds%d' % (self._uniqueKeyChapterNo, self._uniqueKeySectionNo)
                self.canv.bookmarkPage(key)
                try:
                    outlineEntryText = self.reportOutlineLabels[flowable.getPlainText()]
                except:
                    outlineEntryText = ''
                if not outlineEntryText:
                    outlineEntryText = flowable.getPlainText()
                self.canv.addOutlineEntry(outlineEntryText,key, 1, 1)
                self._uniqueKeySectionNo += 1
                self._uniqueKeyFigureNo = 1
            elif style=='FigCaption':
                key = 'ch%ds%df%d' % (self._uniqueKeyChapterNo, self._uniqueKeySectionNo, self._uniqueKeyFigureNo)
                self.canv.bookmarkPage(key)
                try:
                    outlineEntryText = self.reportOutlineLabels[flowable.getPlainText()]
                except:
                    outlineEntryText = ''
                if not outlineEntryText:
                    outlineEntryText = flowable.getPlainText()
                self.canv.addOutlineEntry(outlineEntryText,key, 2, 0)
                self._uniqueKeyFigureNo += 1
    def AddedChapter(self, chapter):
        # as of Reportlab 1.19, reportlab.lib.sequencer class method 'this' made private as '_this'
        # i'm thinking that using public methods 'next' & 'reset' don't quite cut it for work around--chained sequences get reset on 'next' (todo: verify this)
        # for now, use private method
        self.seqChapter[chapter] = self.seq._this('Chapter')
    def getChapterNoAndSectionNo(self, chapter):
        return (self.seqChapter[chapter],self.seqchainChapterSection[chapter])
    def getParagraphs(self,textBlock):
        return textBlock.replace('\r\n','\n').strip().split('\n') # e.g., wx textctrls have just linefeeds; AWOIS memo text have carriage return + linefeeds
    def getFontTag(self, fontname='',fontsize='',fontcolor='',fontsizekicker=0):
        if fontname or fontsize or fontcolor:
            fontTag = '<font'
            if fontname: fontTag += ' face="%s"'%fontname
            if fontsize: fontTag += ' size="%d"'%max(2,fontsize+fontsizekicker) # bottom out at fontsize=2, to protect against shrinking-to-negative
            if fontcolor: fontTag += ' color="%s"'%fontcolor
            fontTag += '>%s</font>'
        else: fontTag = '%s'
        return fontTag
    def title1(self,chapter,text,outlinelabel='',fontname='',fontsize='',fontcolor=''):
        """Use to designate feature type chapters (e.g., using ChapterCoverTemplate); chapter argument must be in _report.keys().
        Elements of title1 are bookmarked and shown in the PDF document outline (parent nodes of heading2)."""
        reportCh = self.report[chapter]
        reportCh.append(PageBreak())  # note page break
        fontTag = self.getFontTag(fontname,fontsize,fontcolor,8)
        p = Paragraph(fontTag%('<seq id="Chapter"/> - ' + GetUnicode(text)), self._T1)
        self.AddedChapter(chapter)
        reportCh.append(p)
        self.reportOutlineLabels[p.getPlainText()]=outlinelabel
    def cheading1(self,chapter,text,outlinelabel='',fontname='',fontsize='',fontcolor=''):
        """Use to label feature sections; chapter argument must be in _report.keys().
        Elements of cheading1 are bookmarked for use in outline (parent nodes of cheading2)."""
        reportCh = self.report[chapter]
        reportCh.append(CondPageBreak(inch))
        fontTag = self.getFontTag(fontname,fontsize,fontcolor,8)
        p = Paragraph(fontTag%GetUnicode(text), self._CH1)
        reportCh.append(p)
        self.reportOutlineLabels[p.getPlainText()]=outlinelabel
    def heading2(self,chapter,text,outlinelabel='',fontname='',fontsize='',fontcolor=''):
        """Use to designate feature address/title(=text argument); chapter argument must be in _report.keys().
        Elements of heading2 are bookmarked and shown in the PDF document outline."""
        reportCh = self.report[chapter]
        #chNumber = reportCh[2].identity().split('>')[1].split('-')[0].strip()
        reportCh.append(CondPageBreak(inch))
        self.seqchainChapterSection[chapter]+=1
        self.seq.next('Section')    # keeps track of total # of items in report & resets Fiqure sequencer
        fontTag = self.getFontTag(fontname,fontsize,fontcolor,4)
        seqChapter,seqchainChapterSection = self.getChapterNoAndSectionNo(chapter)
        p = Paragraph(fontTag%'%d.%d)%s%s'%(seqChapter,seqchainChapterSection,html2space,GetUnicode(text)), self._H2)
        #p.outlineLabel = "Hello"+text
        reportCh.append(p)
        self.reportOutlineLabels[p.getPlainText()]=outlinelabel
    def cheading2(self,chapter,text,outlinelabel='',fontname='',fontsize='',fontcolor=''):
        """Use to label feature sub-sections; chapter argument must be in _report.keys().
        Elements of cheading2 are bookmarked for use in outline (child nodes of cheading1)."""
        reportCh = self.report[chapter]
        reportCh.append(CondPageBreak(inch))
        fontTag = self.getFontTag(fontname,fontsize,fontcolor,4)
        p = Paragraph(fontTag%GetUnicode(text), self._CH2)
        reportCh.append(p)
        self.reportOutlineLabels[p.getPlainText()]=outlinelabel
    def clabel2(self,chapter,text,fontname='',fontsize='',fontcolor=''):
        """Use to label feature sub-sections; chapter argument must be in _report.keys().
        Elements of clabel2 are NOT bookmarked for use in outline."""
        reportCh = self.report[chapter]
        reportCh.append(CondPageBreak(inch))
        fontTag = self.getFontTag(fontname,fontsize,fontcolor,4)
        p = Paragraph(fontTag%GetUnicode(text), self._CL2)
        reportCh.append(p)
    def figcaption(self,chapter,text,outlinelabel='',fontname='',fontsize='',fontcolor=''):
        """Use to label figures.
        Elements are bookmarked for use in outline, seq. numbered according to section number"""
        fontTag = self.getFontTag(fontname,fontsize,fontcolor)
        p = Paragraph(fontTag%GetUnicode(text), self._FC)
        self.report[chapter].append(p)
        self.reportOutlineLabels[p.getPlainText()]=outlinelabel
    def memoTable(self,chapter,tblList,colWidths=None,rowHeights=None,fontname='',fontsize='',fontcolor=''):
        t = Table(GetUnicode(tblList), colWidths, rowHeights)
        tstyleList = [('ALIGN', (0,0), (-1,-1), 'LEFT'),
                      ('VALIGN',(0,0), (-1,-1), 'TOP')]
        if fontname: tstyleList.append(('FONTNAME', (0,0), (-1,-1), fontname))
        if fontsize: tstyleList.append(('FONTSIZE', (0,0), (-1,-1), fontsize))
        if fontcolor: tstyleList.append(('TEXTCOLOR', (0,0), (-1,-1), fontcolor))
        t.setStyle(TableStyle(tstyleList))
        self.report[chapter].append(t)
    def table(self,chapter,tblList,fontname='',fontsize='',fontcolor=''):
        t = Table(GetUnicode(tblList))
        tstyleList = [('ALIGN', (0,0), (-1,-1), 'CENTRE'),
                      ('GRID', (0,1), (-1,-1), 0.25, colors.black)]
        if fontname: tstyleList.append(('FONTNAME', (0,0), (-1,-1), fontname))
        if fontsize: tstyleList.append(('FONTSIZE', (0,0), (-1,-1), fontsize))
        if fontcolor: tstyleList.append(('TEXTCOLOR', (0,0), (-1,-1), fontcolor))
        t.setStyle(TableStyle(tstyleList))
        self.report[chapter].append(t)
    def categoryVvalueChart(self,chapter,ordinateValues,abscissaCategories,chartType='HorizontalBarChart',markerType=None,
                            gridlinesX=False,gridlinesY=True,ordinateTics=10,bIncludeZero=True,ordinateFmtType='%0.3f',chartIdx=0,
                            pageHfraction=1.0,chartX=None,chartY=None,chartH=None,chartW=None,
                            title="",captionLabel="",caption="",fontname='',fontsize='',fontcolor=''):
        abscissaCategories,title,captionLabel,caption = GetUnicode([abscissaCategories,title,captionLabel,caption])
        ##testing
        #from numpy import randn,histogram
        #mu,sigma = 100,15
        #x = list(mu + sigma*randn(10000))
        #ordinateTics=10
        #ordinateValues,abscissaCategories = histogram(x,100,normed=True)
        #ordinateValues,abscissaCategories = [list(ordinateValues)],list(abscissaCategories)
        #for idx in xrange(len(abscissaCategories)):
        #    if idx%5: abscissaCategories[idx]=''
        #    else: abscissaCategories[idx]='%.2f'%abscissaCategories[idx]
        ##print abscissaCategories[:10],abscissaCategories[-10:]
        ##testing
        # if no X/Y & H/W scaling specified, set to fill up page within margins
        if chartType in ("HorizontalBarChart","HorizontalLineChart","VerticalBarChart"): # note: no "VerticalLineChart"
            pageWidth,pageHeight = self.pagesize # in points
            nLeft,nBottom,nRight,nTop = [val*inch for val in self.nLeft,self.nBottom,self.nRight,self.nTop] # inches to points
            availH,availW = pageHfraction*(pageHeight-(nTop+nBottom)),pageWidth-(nLeft+nRight)
            pgMinDim,pgMaxDim = min(pageWidth/inch,pageHeight/inch),max(pageWidth/inch,pageHeight/inch) # inches
            nGutter = min(pgMinDim/17.,pgMaxDim/22.)*inch # 0.5" nominal gutter based on 8.5" x 11" paper size
            # todo: QC size (e.g., >0)
            if chartX==None or chartY==None or chartH==None or chartW==None:
                chartX,chartY,chartH,chartW,drawH,drawW = nGutter,nGutter,availH-3*nGutter,availW-1.25*nGutter,availH-1.5*nGutter,availW-0.5*nGutter
            else:
                chartX,chartY,chartH,chartW = [val*inch for val in chartX,chartY,chartH,chartW]
                drawH,drawW = chartH+1.5*nGutter,chartW+0.75*nGutter
            bIsHorizontal,bIsBarChart = chartType.find('Horizontal')==0,chartType.find('BarChart')>0
            if bIsHorizontal:
                if bIsBarChart:
                    bXisValueYisCategory,bXisCategoryYisValue = True,False
                    gridlinesX,gridlinesY = gridlinesY,gridlinesX
                    chartObj = HorizontalBarChart()
                    for dataSeries in ordinateValues:
                        dataSeries.reverse()
                    ordinateValues.reverse()
                    abscissaCategories.reverse()
                else: # note: HorizontalLineChart has same aspect as VerticalBarChart
                    bXisValueYisCategory,bXisCategoryYisValue = False,True
                    chartObj = HorizontalLineChart()
            else: # note: only vertical chart possible is barchart
                bXisValueYisCategory,bXisCategoryYisValue = False,True
                chartObj = VerticalBarChart()
            if bXisValueYisCategory:
                labelsAngle,labelsAnchor,labelsDX,labelsDY = 0,'e',-max([len(val) for val in abscissaCategories]),0
                if gridlinesX:
                    chartObj.valueAxis.tickUp = chartH
                if gridlinesY:
                    chartObj.categoryAxis.tickRight = chartW
            else: # bXisCategoryYisValue
                labelsAngle,labelsAnchor,labelsDX,labelsDY = 30,'ne',0,0
                if gridlinesX:
                    chartObj.categoryAxis.tickUp = chartH
                if gridlinesY:
                    chartObj.valueAxis.tickRight = chartW
            colorPalette = [colors.lightcoral,colors.cornflower,colors.darkseagreen,colors.tan,colors.aquamarine,
                            colors.lightsteelblue,colors.cadetblue,colors.thistle,colors.steelblue]
            if bIsBarChart:
                chartObj.bars[0].fillColor = colorPalette[chartIdx%len(colorPalette)] # todo: bars[0],[1],... if ordinateValues a list of lists (stacked bars)
            else:
                chartObj.joinedLines = 1
                chartObj.lines[0].strokeWidth = 2 # todo: lines[0],[1],... if ordinateValues a list of lists (multiple lines)
                chartObj.lines[0].strokeColor = colorPalette[chartIdx%len(colorPalette)] # ibid.
                #todo: chartObj.lines[0].symbol = makeMarker('FilledCircle') # or 'Circle', others?
                if markerType: chartObj.lines[0].symbol = makeMarker(markerType)
            chartObj.data = ordinateValues
            chartObj.x,chartObj.y = chartX,chartY
            chartObj.height,chartObj.width = chartH,chartW
            ordinateMin = min([min(ordinateValuesSet) for ordinateValuesSet in ordinateValues])
            ordinateMax = max([max(ordinateValuesSet) for ordinateValuesSet in ordinateValues])
            if bIncludeZero:
                ordinateMin = min(0,ordinateMin)
                ordinateMax = max(0,ordinateMax)
            # evaluate ordinate range in graph string-label space and adjust ordinate[Min,Max,Step] accordingly
            ordinateMinGstr,ordinateMaxGstr = [ordinateGstr.replace('%','').split()[0] for ordinateGstr in (ordinateFmtType%ordinateMin,ordinateFmtType%ordinateMax)]
            ordinateMinG,ordinateMaxG = float(ordinateMaxGstr),float(ordinateMinGstr)
            bAdjustMinMax = True
            if ordinateMinG==ordinateMaxG:
                # if constant y-value graph, set range to span from zero (regardless of bIncludeZero)
                bAdjustMinMax = False
                if ordinateMinG!=0.: # y-values!=0
                    if ordinateMax > 0: ordinateMin=0
                    else: ordinateMax=0
                else: # y-values==0, set range to [0,1]
                    ordinateMin,ordinateMax = 0,1.
                ordinateMinG,ordinateMaxG = ordinateMin,ordinateMax
                ordinateTics=2
            #  determine smallest significant ordinateStep, per desired ordinateTicSize--using stepwise reduction down to 1
            for ordinateTicSize in range(ordinateTics,1,-1):
                ordinateStep = abs((ordinateMaxG-ordinateMinG)/ordinateTicSize)
                ordinateStepGstr = ordinateFmtType%ordinateStep
                ordinateStepGstr = ordinateStepGstr.replace('%','').split()[0]
                ordinateStepG = float(ordinateStepGstr)
                if ordinateStepG!=0:
                    ordinateStep=ordinateStepG
                    break
            if bAdjustMinMax:
                if ordinateMin!=0: # extend y-axis on low side...
                    ordinateMin -= ordinateStep
                if ordinateMax!=0: # then extend y-axis on high side, but don't exceed 100%...
                    try:
                        if (ordinateMax+ordinateStep)>=100 and ordinateFmtType[-1]=='%': ordinateMax = 100.
                        else: ordinateMax += ordinateStep
                    except: # ostensibly b/c invalid ordinateFmtType
                        ordinateMax += ordinateStep
            chartObj.valueAxis.valueMin,chartObj.valueAxis.valueMax,chartObj.valueAxis.valueStep = ordinateMin,ordinateMax,ordinateStep
            chartObj.valueAxis.labelTextFormat = ordinateFmtType
            chartObj.categoryAxis.labels.boxAnchor = labelsAnchor
            chartObj.categoryAxis.labels.dx,chartObj.categoryAxis.labels.dy = labelsDX,labelsDY
            chartObj.categoryAxis.labels.angle = labelsAngle
            chartObj.categoryAxis.categoryNames = abscissaCategories
            chartObjDrawing = Drawing(drawW,drawH)
            chartObjDrawing.add(chartObj)
            if title:
                self.CPage(chapter,0.5+drawH/inch) # todo: had to hack this b/c [start,end]Keep not working
                self.clabel2(chapter,title,fontname,fontsize,fontcolor)
            self.report[chapter].append(chartObjDrawing)
            if captionLabel or caption:
                self.report[chapter].append(self.aTextFlowable('<b>%s</b> %s'%(captionLabel,caption),fontname=fontname,fontsize=fontsize,fontcolor=fontcolor))
    def pieChart(self,chapter,dataList,labelList,chartType='Pie',x=None,y=None,pieSize=None,bShowLabels=False,bShowLegend=True,
                 bShowBoundary=False,caption="",outlinelabel="",fontname='',fontsize='',fontcolor=''):
        labelList,caption,outlinelabel = GetUnicode([labelList,caption,outlinelabel])
        ##testing
        #dataList = [0.31, 0.148, 0.108, 0.076]#, 0.033, 0.03, 0.019, 0.126, 0.15]
        #labelList = ['IHO Special Order', 'IHO Order 1', 'IHO Order 2/3', '> IHO Order 2/3']#, '5', '6', '7', '8', 'X']
        #bShowLegend,bShowLabels = True,True
        #bShowBoundary=True
        ##testing
        # if no X/Y & H/W scaling specified, set to fill up page within margins
        if chartType in ("Pie","Pie3d"):
            pageWidth,pageHeight = self.pagesize # all below in points, except where noted
            nLeft,nBottom,nRight,nTop = [val*inch for val in self.nLeft,self.nBottom,self.nRight,self.nTop]
            availH,availW = pageHeight-(nTop+nBottom),pageWidth-(nLeft+nRight)
            pieSizeAvail = min(availH,availW)
            if x==None or y==None:
                x,y = 0,0
            else:
                x,y = [val*inch for val in x,y]
            if pieSize==None:
                pieSize = pieSizeAvail
            else:
                pieSize *= inch
                pieSize = min(pieSize,pieSizeAvail)
            drawH,drawW = pieSize,max(pieSize,availW)
            if chartType=="Pie3d":
                drawH *= .38 # fudge factor for nominal size reduction to default oblique Pie3d sizing
            pieDrawing = PieFigure(drawW,drawH,chartType,bShowBoundary=bShowBoundary)
            chartObj = pieDrawing.GetChart()
            chartObj.data = dataList
            chartObj.x = x
            chartObj.y = y
            chartObj.width = pieSize
            chartObj.height = drawH
            chartObj.slices.strokeWidth=1 #0.5
            pieColorPalette = [colors.lightcoral,colors.cornflower,colors.darkseagreen,colors.tan,colors.aquamarine,
                               colors.lightsteelblue,colors.cadetblue,colors.thistle,colors.steelblue]
            pieNumPaletteColors = len(pieColorPalette)
            pieNumSlices = len(dataList)
            labelList = ["%d - %s"%(labelIdx,labelStr) for labelIdx,labelStr in zip(range(1,len(labelList)+1),labelList)]
            if bShowLabels:
                pieDrawing.SetLabels([labelStr.split(' - ')[0] for labelStr in labelList])
            pieColorsAndLabels = [(pieColorPalette[pieSlice%pieNumPaletteColors],labelList[pieSlice]) for pieSlice in range(pieNumSlices)]
            sliceIdx=0
            for sliceColor,sliceLabel in pieColorsAndLabels:
                chartObj.slices[sliceIdx].fillColor = sliceColor
                sliceIdx+=1
            if bShowLegend:
                if fontname and fontsize:
                    pieDrawing.SetLegend(pieColorsAndLabels,fontname=fontname,fontsize=fontsize,maxCols=pieNumSlices)
                else:
                    pieDrawing.SetLegend(pieColorsAndLabels,maxCols=pieNumSlices)
            pieDrawing.ReCenterXs()
            self.report[chapter].append(pieDrawing)
    def image(self,chapter,path,margW=None,margH=None,bMaintainAspect=True,caption="",bFigure=True,outlinelabel="",fontname='',fontsize='',fontcolor=''):
        caption,outlinelabel = GetUnicode([caption,outlinelabel])
        I = Image(path)
        imageW,imageH = I.drawWidth,I.drawHeight
        maxW,maxH = self.getReportChActiveTemplateFrameSize(chapter)
        if bFigure or caption:
            maxH *= 0.85 # 85% fudge factor on page height in an effort to prevent blank pages due to excessive length from <image>+<caption> (+<"Feature Images"> handled in PSSObject.CreateFeatureReport)
        # determine "marginalized" image frame width & height--as per user-specified; otherwise, image size not-to-exceed max page size
        if margW or margH:
            try: # marginalize width
                margW*=inch
                if margW > maxW:
                    margW=maxW
                    bMaintainAspect=True # if invalid marginalized size, force maintain aspect
            except:
                margW=min(imageW,maxW)
                bMaintainAspect=True # if no marginalized size, force maintain aspect
            try: # marginalize height
                margH*=inch
                if margH > maxH:
                    margH=maxH
                    bMaintainAspect=True # ibid.
            except:
                margH=min(imageH,maxH)
                bMaintainAspect=True # ibid.
        else:
            margW,margH = min(imageW,maxW),min(imageH,maxH)
        bImageTooBig = (imageW > maxW) or (imageH > maxH)
        if bMaintainAspect:
            aratio = float(imageH)/imageW
            arect = float(margH)/margW
            if aratio > arect:
                I.drawWidth,I.drawHeight = margH/aratio,margH
            else:
                I.drawWidth,I.drawHeight = margW,margW*aratio
        else:
            I.drawWidth,I.drawHeight = margW,margH
        if bFigure or caption:
            s=self.startKeep(chapter)
        self.report[chapter].append(I)
        if bFigure: # note: may or may not have "caption"; nonetheless, want autolabel & outline entry
            self.figcaption(chapter,'Figure %d.%d.'%self.getChapterNoAndSectionNo(chapter)+'<seq template="%(Figure+)s"/>'+'   %s'%caption,outlinelabel,fontname,fontsize,fontcolor)
        else: # i.e. no autolabel & outline entry
            if caption: self.cdisc(chapter,caption,style=self._PC)
        if bFigure or caption:
            self.endKeep(chapter,s)
    def nextTemplate(self,chapter,templName):
        f = NextPageTemplate(templName)
        self.report[chapter].append(f)
    def newPage(self,chapter):
        self.report[chapter].append(PageBreak())
    def CPage(self,chapter,inches):
        self.report[chapter].append(CondPageBreak(inches*inch))
    def startKeep(self,chapter):
        return len(self.report[chapter])
    def endKeep(self,chapter,s):
        S = self.report[chapter]
        k = KeepTogether(S[s:])
        S[s:] = [k]
    def space(self,chapter,inches=1./6):
        if inches: self.report[chapter].append(Spacer(0,inches*inch))
    def disc(self,chapter,text,klass=Paragraph,style=None,fontname='',fontsize='',fontcolor=''):
        text = GetUnicode(text)
        if not style: style=self._B
        fontTag = self.getFontTag(fontname,fontsize,fontcolor)
        for txtFlowable in self.getParagraphs(text):
            P = klass(fontTag%txtFlowable, style)
            self.report[chapter].append(P)
    def cdisc(self,chapter,text,klass=Paragraph,style=None,fontname='',fontsize='',fontcolor=''):
        text = GetUnicode(text)
        if not style: style=self._CB
        self.disc(chapter,text,klass,style,fontname,fontsize,fontcolor)
    def aTextFlowable(self,text,klass=Paragraph,style=None,fontname='',fontsize='',fontcolor=''):
        if text is None: text=''
        else: text = GetUnicode(text)
        if not style: style=self._B
        fontTag = self.getFontTag(fontname,fontsize,fontcolor)
        return klass(fontTag%text, style)
    def appendFlowable(self,chapter,aFlowable):
        self.report[chapter].append(aFlowable)
    def restartList(self):
        getSequencer().reset('blist')
    def alist(self,chapter,text,doBullet=1,fontname='',fontsize='',fontcolor=''):
        text = GetUnicode(text)
        fontTag = self.getFontTag(fontname,fontsize,fontcolor)
        for txtFlowable in self.getParagraphs(text):
            if doBullet:
                txtFlowable='<bullet><seq id="blist"/>.</bullet>'+txtFlowable
            P = Paragraph(fontTag%txtFlowable, self._BU)
            self.report[chapter].append(P)
    def bullet(self,chapter,text,fontname='',fontsize='',fontcolor=''):
        text = GetUnicode(text)
        fontTag = self.getFontTag(fontname,fontsize,fontcolor)
        for txtFlowable in self.getParagraphs(text):
            # str -> unicode, for reportlab 2.x compatibility
            txtFlowable=('<bullet>></bullet>'+txtFlowable)
            P = Paragraph(fontTag%txtFlowable, self._BU)
            self.report[chapter].append(P)
