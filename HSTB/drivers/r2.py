"""
r2.py
G.Rice 20130916
V0.0.1 20130916

Intended to read R2Sonic files.
"""

import numpy as np
from matplotlib import pyplot as plt
import pickle
import sys

class read:
    """
    The class for handling the file.
    """
    def __init__(self, infilename, verbose = False):
        """Make a instance of the allRead class."""
        self.infilename = infilename
        self.infile = open(infilename, 'rb')
        self.filetype = infilename.rsplit('.')[1]
        self.mapped = False
        self.packet_read = False
        self.eof = False
        self.error = False
        self.infile.seek(0,2)
        self.filelen = self.infile.tell()
        self.infile.seek(0)
        
    def close(self):
        self.infile.close()
        
    def read(self, verbose = False):
        """
        Reads the header.
        """
        if self.infile.tell() == self.filelen:
                self.eof = True
        if not self.eof:
            if self.filetype == 'R2S':
                header = np.fromfile(self.infile, dtype=('<I,S4,>I,>I'), count=1)[0]
                self.hypackheader = header[0]
                packetsize = header[2]
                hdrlen = 4
                packettype = header[1]
                if self.hypackheader != packetsize:
                    self.eof = True
            else:
                header = np.fromfile(self.infile, dtype=('S4,>I,>I'), count=1)[0]
                packetsize = header[1]
                hdrlen = 3
                packettype = header[1]
            if len(header) == hdrlen and not self.eof:
                self.infile.seek(-12, 1)
                if self.filelen >= self.infile.tell() + packetsize:
                    self.packet = Datagram(self.infile.read(packetsize))
                    self.packet_read = True
                    if verbose:
                        print packettype
                else:
                    self.eof = True
                    self.error = True
                    print "Broken packet of type' + packettype + ' found at", self.infile.tell()
                    print "Final packet size", packetsize
            else:
                self.eof = True
                self.error = True
                print "Broken packet found at", self.infile.tell()
                print "Final packet size", packetsize
                
    def get(self):
        """
        Decodes the data section of the datagram if a packet has been read but
        not decoded.  If excecuted the packet_read flag is set to False.
        """
        if self.packet_read and not self.packet.decoded:
            self.packet.decode()
            self.packet_read = False
        
    def mapfile(self, verbose = False):
        """
        Maps the datagrams in the file.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack()
            self.reset()
            print 'Mapping file;           ',
            while not self.eof:
                loc = self.infile.tell()
                self.read()
                if not self.eof:
                    time = self.packet.gettime()
                    self.map.add(self.packet.dtype, loc, time)
                current = 100 * loc / self.filelen
                if current - progress >= 1 and verbose:
                    progress = current
                    sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            if self.error:
                print
            else:
                print '\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.'
            if verbose:
                self.map.printmap()
            self.mapped = True
        else:
            pass
        
    def loadfilemap(self, mapfilename = ''):
        """
        Loads the packdir if the map object packdir has been saved previously.
        """
        if mapfilename == '':
            mapfilename = self.infilename[:-3] + 'r2'
        try:
            self.map = mappack()
            self.map.load(mapfilename)
            self.mapped = True
            print 'loaded file map ' + mapfilename
        except IOError:
            print mapfilename + ' map file not found.'
            
    def savefilemap(self):
        """
        Saves the mappack packdir dictionary for faster operations on a file in
        the future.  The file is saved under the same name as the loaded file
        but with a 'par' extension.
        """
        if self.mapped:
            mapfilename = self.infilename[:-3] + 'r2'
            self.map.save(mapfilename)
            print 'file map saved to ' + mapfilename
        else:
            print 'no map to save.'
            
    def getrecord(self, recordtype, recordnum):
        """
        Gets the record number of the described record type.
        """
        if not self.mapped:
            self.mapfile()
        if self.map.packdir.has_key(str(recordtype)):
            loc = self.map.packdir[str(recordtype)][recordnum][0]
            self.infile.seek(loc)
            self.read()
            self.get()
            return self.packet.subpack
        else:
            print "record " + str(recordtype) + " not available."
            return None
            
    def findpacket(self, recordtype, verbose = False):
        """
        Find the next record of the requested type.
        """
        self.read()
        while not self.eof:
            if verbose:
                print self.packet.dtype
            if recordtype == self.packet.dtype:
                break
            else:
                self.read()
        self.get()
            
    def display(self):
        """
        Prints the current record header and record type header to the command
        window.  If the record type header display method also contains a plot
        function a plot will also be displayed.
        """
        if self.__dict__.has_key('packet'):
            self.packet.display()
        else:
            print 'No record currently read.'
        
    def reset(self):
        """
        Puts the file pointer to the start and the eof to False.
        """
        self.infile.seek(0)
        self.packet_read = False
        self.eof = False
        if self.__dict__.has_key('packet'):
            del self.packet
        
class use(read):
    """
    This class inherits from the read class, but is meant to provide simpiler
    (higher level) access to split datagrams, such as the water column and 
    snippts records.
    """
    
    def mapfile(self, verbose = False):
        """
        Maps the datagrams in the file, but also adds the ping number and order
        number in the file map to aid in reconstruction of split records.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack()
            self.reset()
            print 'Mapping file;           ',
            while not self.eof:
                loc = self.infile.tell()
                self.read()
                if not self.eof:
                    self.get()
                    time = self.packet.gettime()
                    self.map.add(self.packet.dtype, loc, time)
                current = 100 * loc / self.filelen
                if current - progress >= 1 and verbose:
                    progress = current
                    sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            if self.error:
                print
            else:
                print '\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.'
            if verbose:
                self.map.printmap()
            self.mapped = True
        else:
            pass
        
    def getrecord(self, recordtype, recordnum):
        """
        Gets the record number of the described record type.
        """
        if not self.mapped:
            self.mapfile()
        if self.map.packdir.has_key(str(recordtype)):
            loc = self.map.packdir[str(recordtype)][recordnum][0]
            self.infile.seek(loc)
            self.read()
            self.get()
            return self.packet.subpack
        else:
            print "record " + str(recordtype) + " not available."
            return None
            
    def findpacket(self, recordtype, verbose = False):
        """
        Find the next record of the requested type.
        """
        self.read()
        while not self.eof:
            if verbose:
                print self.packet.dtype
            if recordtype == self.packet.dtype:
                break
            else:
                self.read()
        self.get()
          
class Datagram:
    """
    The datagram holder.  Reads the header section of the provided memory
    block and holds a list with the datagram information through the time
    stamp.  Also, the datagram type is stored in variable 'dtype'.  Flags
    are set to indicate whether the rest of the datagram has been decoded,
    and the decoded data is stored in a datagram specific object called
    'subpack'. The maketime method is called upon decoding the record, and
    a 'time' variable is created containing a POSIX time with the packet
    time. 'valid' indicates whether the sync pattern is present, 'decoded'
    indicated if the datagram has been decoded, and 'checksum' contains the
    checksum field.
    Note: While not required of these datagrams, the size of the datagram, as
    if coming from a file, is expected at the beginning of these datablocks.
    """
    
    hdr_dtype = np.dtype([('PacketName','>S4'),('PacketSize','>I'),
        ('DataStreamID','>I')])
        
    H0_dtype = np.dtype([('SectionName','>S2'),('Size','>H'),
        ('Model#','>S12'),('SerialNumber','>S12'),('TimeSeconds','>I'),
        ('TimeNanoseconds','>I'),('PingNumber','>I'),('PingPeriod','>f'),
        ('SoundSpeed','>f'),('Frequency','>f'),('TxPower','>f'),
        ('TxPulseWidth','>f'),('TxBeamwidthVert','>f'),
        ('TxBeamwidthHoriz','>f'),('TxSteeringVert','>f'),
        ('TxSteeringHoriz','>f'),('TxMiscInfo','>H'),('VTXOffset','h'),
        ('RxBandwidth','>f'),('RxSampleRate','>f'),('RxRange','>f'),
        ('RxGain','>f'),('RxSpreading','>f'),('RxAbsorption','>f'),
        ('RxMountTilt','>f'),('RxMiscInfo','>I'),('reserved','>H'),
        ('Beams','>H')])
    
    def __init__(self, fileblock):
        """
        Reads the header section, which is the first 12 bytes, of the
        given memory block.
        """
        hdr_sz = Datagram.hdr_dtype.itemsize
        H0_sz = Datagram.H0_dtype.itemsize
        self.header = np.frombuffer(fileblock, dtype = Datagram.hdr_dtype, count = 1)[0]
        self.decoded = False
        self.dtype = self.header[0]
        if np.frombuffer(fileblock[hdr_sz:hdr_sz+2], dtype = '>S2') == 'H0':
            self.subheader = np.frombuffer(fileblock, dtype = Datagram.H0_dtype, offset = hdr_sz, count = 1)[0]
            self.datablock = fileblock[hdr_sz+H0_sz:]
            # the snippet and truepix datagrams have a larger header...
            if self.dtype == 'SNI0' or self.dtype == 'TPX0':
                self.datablock = self.datablock[6*4:]
        else:
            self.datablock = fileblock[hdr_sz:]
        
    def decode(self):
        """
        Directs to the correct decoder.
        """
        self.decoded = True
        if self.dtype == 'BTH0':
            self.subpack = BTH0(self.datablock, self.subheader['Beams'])
        elif self.dtype == 'SNI0':
            self.subpack = SNI0(self.datablock)
        elif self.dtype == 'WCD0':
            self.subpack = WCD0(self.datablock)
        else:
            self.decoded = False
            print "Data record " + str(self.header[0]) + " decoding is not yet supported."
        
    def gettime(self):
        """
        Returns the time stamp for the record in POSIX time.
        """
        if self.__dict__.has_key('subheader'):
            time = (self.subheader['TimeSeconds'] + 
                float(self.subheader['TimeNanoseconds'])/10**9)
        else:
            time = np.nan
        return time
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        if self.__dict__.has_key('subheader'):
            for n,name in enumerate(self.subheader.dtype.names):
                print name + ' : ' + str(self.subheader[n])
        
class BTH0:
    """
    R2Sonic bathy packet.
    """
            
    def __init__(self, datablock, numpts):
        """
        Catches the binary datablock and calls other functions to decode the
        data.
        """
        self.numpts = numpts
        self._read(datablock)
        self._decode()

    def _read(self, datablock):
        """
        Reads the data section of the record.
        """
        subhdr_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H')])
        subhdr_sz = subhdr_dtype.itemsize
        p = 0
        while p < len(datablock):
            subhdr = np.frombuffer(datablock[p:p+subhdr_sz], dtype=subhdr_dtype)[0]
            subblock = datablock[p:p+subhdr[1]]
            if subhdr[0] == 'R0':
                self._readR0(subblock)
            elif subhdr[0] == 'A0':
                self._readA0(subblock)
            elif subhdr[0] == 'A2':
                self._readA2(subblock)
            elif subhdr[0] == 'I1':
                self._readI1(subblock)
            elif subhdr[0] == 'G0':
                self._readG0(subblock)
            elif subhdr[0] == 'G1':
                # This data type is not decoded.
                self.G1 = None
            elif subhdr[0] == 'Q0':
                self._readQ0(subblock)
            else:
                print "Unknown bathy subtype found!"
            p += subhdr[1]
                
    def _readR0(self, datablock):
        """
        Reads the bathy subsection and puts it in R0. The data are converted
        into two way travel times and placed into the data array.
        """
        numleft = self.numpts & 1
        R0_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('ScalingFactor','>f'),('Range','>' + str(self.numpts) + '>H'),
            ('unused','>' + str(numleft) + 'H')])
        self.R0 = np.frombuffer(datablock, dtype = R0_dtype)[0]

    def _readA0(self, datablock):
        """
        Reads the equiangle beam pointing angles.
        """
        A0_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('AngleFirst','>f'),('AngleLast','>f'),('MoreInfo','>6f')])
        self.A0 = np.frombuffer(datablock, dtype = A0_dtype)[0]
        
    def _readA2(self, datablock):
        """
        Reads the arbitrarily-spaced beam pointing angles.
        """
        numleft = self.numpts & 1
        A2_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('AngleFirst','>f'),('ScalingFactor','>f'),('MoreInfo','>6f'),
            ('AngleStep','>' + str(self.numpts) + 'H'),
            ('unused','>' + str(numleft) + 'H')])
        self.A2 = np.frombuffer(datablock, dtype = A2_dtype)[0]

    def _readI1(self, datablock):
        """
        Reads the intensity subsection and puts it in R0.  The intensity is 
        converted to float32 and multiplied by the scaling factor.
        """
        numleft = self.numpts & 1
        I1_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('ScalingFactor','>f'),
            ('Intensity','>' + str(self.numpts) + '>H'),
            ('unused','>' + str(numleft) + 'H')])
        self.I1 = np.frombuffer(datablock, dtype = I1_dtype)
            
    def _readG0(self, datablock):
        """
        Reads the straight-line depth gate subsection.
        """
        G0_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('DepthGateMin','>f32'),('DepthGateMax','>f32'),
            ('DepthGateSlope','>f32')])
        self.G0 = np.frombuffer(datablock, dtype = G0_dtype)[0]
        
    def _readQ0(self, datablock):
        """
        Reads the quality flag subsection.
        """
        Q0_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
                             ('Quality', str(self.numpts/8) + '>I')])
        self.Q0 = np.frombuffer(datablock, dtype = Q0_dtype)[0]
    
    def _decode(self):
        """
        Converts each of the raw data types into real numbers using their
        scaling factors and places them in an easily accessible array.
        """
        data_descr = [('Range','f'),('Angle','f')]
        if self.__dict__.has_key('I1'):
            data_descr.append(('Intensity','f'))
        if self.__dict__.has_key('Q0'):
            data_descr.append(('QualityFlag','B'))
        self.data = np.zeros(self.numpts, dtype = np.dtype(data_descr))
        if self.__dict__.has_key('R0'):
            self.data['Range'] = self.R0['Range'].astype('f') * self.R0['ScalingFactor']
        if self.__dict__.has_key('A0'):
            self.data['Angle'] = np.linspace(self.A0['AngleFirst'], self.A0['AngleLast'], self.numpts)
        elif self.__dict__.has_key('A2'):
            self.data['Angle'] = self._makeA2angles()
        if self.__dict__.has_key('I1'):
            self.data['Intensity'] = self.I1['Intensity'] * self.I1['ScalingFactor']
        if self.__dict__.has_key('Q0'):
            self.data['QualityFlag'] = self._makeQ0flags()
            
    def _makeA2angles(self):
        """
        Makes an array of the equispaced A2 angles.
        """
        angles = np.zeros(self.numpts, dtype = 'f')
        base = self.A2['AngleFirst'].astype('f')
        s = np.single(0, dtype = 'I')
        for n in range(self.numpts):
            s += self.A2['AngleStep'][n].astype('I')
            angles[n] = base + s * self.A2['ScalingFactor']
        return angles
        
    def _makeQ0flags(self):
        """
        Makes an returns the quality flags from the Q0 data.
        """
        qf = np.zeros(self.numpts, dtype = 'B')
        vals = self.Q0['Quality']
        b = 0
        for n in range(len(vals)):
            val = vals[n]
            for m in range(8,0,-1):
                qf[b] = np.bitwise_and(np.right_shift(val,4*(m-1)), 15)
                b += 1
        return qf
        
        
class SNI0:
    """
    R2Sonic snippet packet.
    """
        
    def __init__(self, datablock):
        """
        Catches the binary datablock and calls other functions to decode the
        data.
        """
        self._read(datablock)
        self._decode()
        
    def _read(self, datablock):
        """
        Reads the data section of the snippet record. The number of snippets
        and the number of beams in this record are not clear before reading. As
        a result the records are stuffed into two expanding numpy arrays as the
        data is read.  The information about each section is read into 
        "snippet_info" and the snippets are read into the object array
        "snippets". The snippet values are converted into floats before
        storage.
        """
        S1_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('PingNumber','>I'),('Snippet#','>H'),('Samples','>H'),
            ('FirstSample','>I'),('Angle','>f'),('ScalingFactorFirst','>f'),
            ('ScalingFactorLast','>f'),('reserved','>I')])
        S1_size = S1_dtype.itemsize
        self.snippet_info = np.zeros(0, dtype = S1_dtype)
        self.snippets = []
        n = 0
        p = 0
        while p < len(datablock):
            temp = np.frombuffer(datablock,dtype = S1_dtype, count = 1, offset = p)[0]
            self.snippet_info = np.append(self.snippet_info, temp)
            numsnip = self.snippet_info['Samples'][n]
            numleft = numsnip & 1
            p += S1_size
            temp = np.frombuffer(datablock, dtype = '>H', count = numsnip, offset = p)            
            temp = np.array(temp, dtype = 'f')
            self.snippets.append(temp)
            n += 1
            p += 2* (numleft + numsnip)
        self.snippets = np.asarray(self.snippets)
        
    def _decode(self):
        """
        Apply the scaling information to the snippets array.
        """
        numsubrecords = len(self.snippet_info)
        for n in range(numsubrecords):
            num,first,last = self.snippet_info[['Samples','ScalingFactorFirst','ScalingFactorLast']][n]
            if first != 0 and last != 0:
                self.snippets[n] *= np.linspace(first,last,num=num)
            elif first != 0:
                self.snippets[n] *= first
                
                
class WCD0:
    """
    From the R2Sonic 2024 manual:
    // The water column data contains real-time beamformer 16-bit magnitude data
    // (beam amplitude) and optional 16-bit split-array phase data (intra-beam
    // direction). Maximum data rate is about 70 megabytes per second (assuming
    // 256 beams, 68.4 kHz sample rate, and phase data enabled). The sample rate
    // (and signal bandwidth) varies with transmit pulse width and range setting.
    // Maximum ping data size is about 32 megabytes (assuming 256 beams of 32768
    // samples, and phase data enabled), but max size may change in the future.
    // The number of beamformed data samples normally extends somewhat further
    // than the user's range setting.
    //
    // When the operator enables water column mode, each sonar ping outputs
    // numerous 'WCD0' packets containing: one H0 header section, one A1 beam
    // angle section, and many M1 or M2 data sections. The section order may
    // change in the future, so plan for that in your data acquisition.
    //
    // Each M1 or M2 section contains a subset of the ping data. Its header
    // indicates its size position to help you assemble the full ping array.
    //
    // You may wish to detect missing M1 or M2 data sections (perhaps a lost
    // UDP packet), and then fill the gap with zeros or perhaps data from the
    // previous ping (to reduce visual disturbances), and then increment an
    // error counter for network health monitoring purposes.
    //
    // The water column data is basically in polar coordinates, so you may
    // wish to geometrically warp it into the familiar wedge shape for display.
    // Consider using OpenGL or Direct3D texture mapping.
    """
    def __init__(self, datablock):
        """
        Decides which parsing method to use based on the first two bytes.
        """
        dtype = np.frombuffer(datablock, dtype = '>S2', count = 1)[0]
        if dtype == 'A1':
            self._readA1(datablock)
        elif dtype == 'M1':
            self._readM1(datablock)
        elif dtype == 'M2':
            pass
        else:
            print 'Unknown Water Column subrecord found!'
            
    def _readA1(self, datablock):
        """
        Reads the Angle section.
        """
        section_size = np.frombuffer(datablock, dtype = '>H', offset = 2, count = 1)[0]
        # The number of beams is the (section size minus the other fields) / 4        
        numbeams = (section_size - (2+2+6*4)) / 4
        A1_dtype = np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('MoreInfo','>6f'),('BeamAngle','>' + str(numbeams) + 'f')])
        self.A1 = np.frombuffer(datablock, dtype = A1_dtype, count = 1)[0]
        
    def _readM1(self, datablock):
        """
        Reads the Magnitude (only) datablock type.
        """
        M1_dtype= np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('PingNumber','>I'),('ScalingFactor','>f'),('TotalSamples','>I'),
            ('FirstSample','>I'),('Samples','>H'),('TotalBeams','>H'),
            ('FirstBeam','>H'),('Beams','>H'),('reserved','>2I')])
        self.M1 = np.frombuffer(datablock, dtype = M1_dtype, count = 1)[0]
        numsamples = self.M1['Beams'] * self.M1['Samples']
        self.magnitude = np.frombuffer(datablock, dtype = '>H', count = numsamples)
        self.magnitude.shape = (self.M1['Beams'], self.M1['Samples'])
        
    def _readM2(self, datablock):
        """
        Reads the Magnitude (only) datablock type.
        """
        M2_dtype= np.dtype([('SectionName','>S2'),('SectionSize','>H'),
            ('PingNumber','>I'),('ScalingFactor','>f'),('TotalSamples','>I'),
            ('FirstSample','>I'),('Samples','>H'),('TotalBeams','>H'),
            ('FirstBeam','>H'),('Beams','>H'),('reserved','>2I')])
        self.M2 = np.frombuffer(datablock, dtype = M2_dtype, count = 1)[0]
        numsamples = self.M1['Beams'] * self.M1['Samples'] * 2
        temp = np.frombuffer(datablock, dtype = '>H', count = numsamples)
        temp.shape = (2,-1)
        self.magnitude = temp[0,:]
        self.magnitude.shape = (self.M1['Beams'], self.M1['Samples'])
        self.phase = temp[1,:]
        self.phape.shape = (self.M1['Beams'], self.M1['Samples'])
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        if self.__dict__.has_key('A1'):
            for n,name in enumerate(self.A1.dtype.names):
                print name + ' : ' + str(self.A1[n])
        if self.__dict__.has_key('M1'):
            for n,name in enumerate(self.M1.dtype.names):
                print name + ' : ' + str(self.M1[n])
        elif self.__dict__.has_key('M2'):
            for n,name in enumerate(self.M2.dtype.names):
                print name + ' : ' + str(self.M2[n])
    
            
class mappack:
    """
    Container for the file packet map.
    """
    def __init__(self):
        """Constructor creates a packmap dictionary"""
        self.packdir = {}
       
    def add(self, type, location=0, time=0):
        """Adds the location (byte in file) to the tuple for the value type"""
        if type not in self.packdir:
            self.packdir[type] = []
        self.packdir[type].append([location,time])
            
    def finalize(self):
        for key in self.packdir.keys():
            self.packdir[key] = np.asarray(self.packdir[key])
        
    def printmap(self):
        keys = []
        for i,v in self.packdir.iteritems():
            keys.append((i,len(v)))
        keys.sort()
        for key in keys:
            print str(key[0]) + ' has ' + str(key[1]) + ' packets'
            
    def save(self, outfilename):
        outfile = open(outfilename, 'wb')
        pickle.dump(self.packdir, outfile)
        outfile.close()
        
    def load(self,infilename):
        infile = open(infilename, 'rb')
        self.packdir = pickle.load(infile)
        infile.close()

        
def main():        
    if len(sys.argv) > 1:
        a = r2read(sys.argv[1])
        a.mapfile(True)
        a.close()
    else:
        print "No filename provided."
        
if __name__ == '__main__':
    main()