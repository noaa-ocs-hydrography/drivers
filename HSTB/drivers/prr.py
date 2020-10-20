"""Python Reson Reader
G.Rice 9/10/10
V0.3.9 20150107
This is intended to help trouble shoot Reson data directly from the Reson datagrams.
It was inspired by The Great Sam Greenaway during his graduate work at UNH.
"""

import os, sys, struct, pickle, mmap
import numpy as np
import matplotlib.pyplot as plt
import time, calendar, math

try:
  basestring
except NameError:
  basestring = str
  
class x7kRead:
    """open a file in binary mode and give a packet reader
    the proper data blocks to read the data packets"""
    def __init__(self, infilename, autoplot = True):
        """opens and memory maps the file"""
        # format info for reading 7K files
        self.hypack_sz = 4
        self.hypack_fmt = '<I'
        self.netfrm_sz = 36
        self.netfrm_fmt ='<HHIHH4IHHI'
        # initialize flags for reading methods
        self.hdr_read = False
        self.data_read = False
        self.hypack_hdr = 0
        self.last_record_sz = 0
        self.corrupt_record = False
        self.split_record = False
        self.mapped = False
        self.noisy = True
        # find file type and open file
        self.infilename = infilename
        [self.inname,self.intype] = os.path.splitext(infilename)
        self.intype=self.intype[1:].lower()
        self.tempread = True
        if self.intype in ('7k', 's7k'):
            self.infile = open(infilename, 'rb')
        else:
            print ('invalid file type')
        self.infile.seek(0,2)
        self.filelen = self.infile.tell()
        self.infile.seek(0)
        if autoplot:
            plt.ion()

    def read(self,verbose=True):
        """Decides what type of reading needs to be done"""
        if self.hdr_read == True and self.data_read == False:
            self.packet.skipdata()
        if self.intype == '7k':
            self.read7k(verbose)
        elif self.intype == 's7k':
            self.reads7k(verbose)
        if verbose:
            print self.packet.datatype
        self.hdr_read = True
        self.data_read = False
    def reads7k(self,verbose):    
        """Processes data block according to the s7k format"""
        #read data record frame
        self.checkfile(verbose)
        if self.tempread:
            self.loc = self.infile.tell()
            self.packet = DataFrame(self.infile)
    
    def read7k(self,verbose = True):
        """Removes the Hypack Header and the Reson Network Frames and then assumes s7k format."""
        if self.split_record:
            self.infile.seek(36, 1)  # this takes into account the netframe header for the next read, but doesn't fix the problem
            self.hypack_hdr -= 36
            self.split_record = False
        if self.hypack_hdr < 0:     #this happens when a hypack header falls inside of a record
            if np.abs(self.hypack_hdr) > self.last_record_sz:   #I don't know why this happens
                self.hypack_hdr = 0
            else:                           #this goes back into the corrupted record to find the hypack header
                self.infile.seek(self.hypack_hdr, 1)
                temp = struct.unpack(self.hypack_fmt, self.infile.read(self.hypack_sz))[0]
                self.infile.seek(-self.hypack_hdr, 1)
                self.hypack_hdr += temp
        if self.hypack_hdr == 0:
            temp = self.infile.read(self.hypack_sz)
            if len(temp) == self.hypack_sz:
                [self.hypack_hdr] = struct.unpack(self.hypack_fmt, temp)
        temp = self.infile.read(self.netfrm_sz)
        self.reads7k(verbose = verbose)
        if len(temp) == self.netfrm_sz:
            self.netfrm_hdr = struct.unpack(self.netfrm_fmt, temp)
            self.last_record_sz = self.packet.header[3] + self.netfrm_sz
            self.hypack_hdr = self.hypack_hdr - self.last_record_sz
            if self.hypack_hdr < 0:
                self.corrupt_record = True
            else: self.corrupt_record = False
            if self.netfrm_hdr[5] < self.netfrm_hdr[6]: # this is when records are broken up
                self.split_record = True

    def skip(self):
        """Skips the data part of a record."""
        if self.hdr_read == False:
            self.read()
        self.packet.skipdata()
        self.hdr_read = False
        
    def get(self):
        """Reads the data part of a record."""
        if self.hdr_read == False:
            self.read(False)
        self.packet.getdata()
        self.data_read = True
        
    def display(self):
        """Displays the information from a packet using the records display method."""
        if self.data_read == False:
            self.get()
        self.packet.display()
        self.packet.subpack.display()
        
    def reset(self):
        """Resets to the beginning of the file."""
        self.infile.seek(0)
        self.hdr_read = False
        self.data_read = False
        self.hypack_hdr = 0
        self.tempread = True
        self.corrupt_record = False
        self.last_record_sz = 0
    
    def findpacket(self, datatype, verbose = True):
        """Finds the requested packet type and reads the packet"""
        self.read(verbose)
        while datatype != self.packet.datatype and self.tempread:
            self.read(verbose)
        if self.tempread:
            self.get()
        else:
            print 'no ' + str(datatype) + ' record found in file'
        
    def checkfile(self, verbose = True):
        """Read file to check for validity of next block"""
        self.badblock = True
        self.tempread = True
        count = 0
        while self.tempread and self.badblock:
            try:
                self.tempstr = self.infile.read(8)
                assert(len(self.tempstr)==8)
                self.temp = struct.unpack('<HHI',self.tempstr)
                if self.temp[2] == 65535:    #This is 0x0000FFFF, Reson Sync Pattern
                    self.infile.seek(-8,1)
                    self.badblock = False
                else:
                    self.infile.seek(-7,1)
                    count += 1
                    self.hdr_read = False
                    self.data_read = False
                    self.hypack_hdr = 0
                    self.last_record_sz = 0
            except AssertionError:
                # print "End of file"
                self.tempread = False
        if count != 0 and self.noisy:
            if verbose:
                print "reset " + str(count) + " bytes to " + str(self.infile.tell())
        
    def findval(self):
        """This is a hack to find where the range scale changes"""
        self.read()
        self.findpacket(7000)
        self.oldval = self.packet.ping7000.header[13]
        self.findpacket(7000)
        self.val = self.packet.ping7000.header[13]
        while self.val == self.oldval:
            self.findpacket(7000)
            self.oldval = self.val
            self.val = self.packet.ping7000.header[13]
        print self.oldval, self.val
    
    def mapfile(self, verbose = False, show_progress=True):
        """Maps the location of all the packets in the file.
        Parts of this method act as an intermediary between the
        reader class and the packet class, but may need to be
        moved to their own layer at some point."""
        self.map = mappack()
        count_corrupt = 0
        self.reset()
        progress = 0
        if show_progress:
            print 'Mapping file; 00 percent',
        while self.tempread == True:
            self.read(False)
            try:
                packettime = self.packet.gettime()
            except ValueError:
                print "Bad time stamp found at " + str(self.infile.tell())
                packettime = np.nan
                self.corrupt_record = True
            if self.corrupt_record:
                count_corrupt += 1
            if self.tempread == True:
                size = self.packet.datasize + self.packet.hdr_sz + self.packet.ft_sz
                self.skip()
                self.map.add(str(self.packet.datatype), self.loc, packettime, size = size)
                current = 100 * self.loc / self.filelen
                if current - progress >= 1:
                    progress = current
                    if show_progress:
                        sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
        self.reset()
        if show_progress:
            print '\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.'
        if verbose:
            self.map.printmap()
            print str(count_corrupt) + ' corrupt records found.'
        self.map.finalize()
        self.mapped = True
        
    def getrecord(self, recordtype, numrecord):
        """
        This method is designed to read records of a particular type
        from the file map.  If 7k files are read than the file type is switched 
        after mapping and before reading.  The subpacket object is returned for
        easy access to the fetched data and methods.
        """
        if not self.mapped:
            self.reset()
            self.mapfile()
        self.intype = 's7k'
        recordtype = str(recordtype)
        loc = int(self.map.packdir[recordtype][numrecord][0])
        self.infile.seek(loc)
        self.hdr_read = False
        self.data_read = False
        self.get()
        return self.packet.subpack
        
    def getping(self, numping):
        """This method is designed to read all records that are available for
        a particular ping.  The ping number, zero being the first ping in the
        file, is given.  All subrecords are stored in a dictionary named
        'ping', and 'header' is a list of the header information for these 
        packets.  The 7000 record is the base record, meaning this what all
        other packets are matched to time wise."""
        if not self.mapped:
            self.reset()
            self.mapfile()
        self.intype = 's7k'
        if self.map.packdir.has_key('7000'):
            if numping < len(self.map.packdir['7000']):
                self.ping = {}
                recordlist = self.map.packdir.keys()
                indx = np.nonzero('7000' == np.asarray(recordlist)[:])
                recordlist.pop(indx[0])
                self.getrecord(7000, numping)
                self.ping['header'] = self.packet.header
                self.ping['7000'] = self.packet.subpack
                t_ping = self.packet.gettime()
                for record in recordlist:
                    recorddir = np.asarray(self.map.packdir[record])
                    indx = np.nonzero(t_ping == recorddir[:,1])[0]
                    if len(indx) == 1:
                        self.getrecord(record, indx[0])
                        try:
                            self.ping[record] = self.packet.subpack
                        except AttributeError:
                            pass
                    elif len(indx) > 1:
                        print 'huh, more than one record of ' + record + ' type found.'
                return t_ping
            else: print 'ping is beyond record length.'
        else: print 'No 7000 record found!'
        
    def getnav(self, t_ping):
        """This method takes a time stamp and IF there is navigation in the
        file creates a "nav" dictionary for that time stamp, containing x, y,
        roll, pitch, heading, and heave."""
        if not self.mapped:
            self.reset()
            self.mapfile()
        self.intype = 's7k'
        self.nav = {}
        if self.map.packdir.has_key('1003'):
            recorddir = np.asarray(self.map.packdir['1003'])
            indx = np.nonzero(t_ping > recorddir[:, 1])[0]
            if len(indx) > 0:
                self.getrecord(1003, indx[-1])
                x1 = self.packet.subpack.header[3]
                y1 = self.packet.subpack.header[2]
                z1 = self.packet.subpack.header[4]
                t1 = recorddir[indx[-1], 1]
                if len(recorddir) > (indx[-1] + 1):
                    self.getrecord(1003, indx[-1] + 1)
                    x2 = self.packet.subpack.header[3]
                    y2 = self.packet.subpack.header[2]
                    z2 = self.packet.subpack.header[4]
                    t2 = recorddir[indx[-1] + 1, 1]
                    dt = t_ping - t1
                    dx = dt * (x1 - x2) / (t1 - t2)
                    dy = dt * (y1 - y2) / (t1 - t2)
                    dz = dt * (z1 - z2) / (t1 - t2)
                    self.nav['x'] = x1 + dx
                    self.nav['y'] = y1 + dy
                    self.nav['z'] = z1 + dz
                else:
                    self.nav['x'] = x1
                    self.nav['y'] = y1
                    self.nav['z'] = z1
        if self.map.packdir.has_key('1012'):
            recorddir = np.asarray(self.map.packdir['1012'])
            indx = np.nonzero(t_ping > recorddir[:, 1])[0]
            if len(indx) > 0:
                self.getrecord(1012, indx[-1])
                r1 = self.packet.subpack.header[0]
                p1 = self.packet.subpack.header[1]
                h1 = self.packet.subpack.header[2]
                t1 = recorddir[indx[-1], 1]
                if len(recorddir) > (indx[-1] + 1):
                    self.getrecord(1012, indx[-1] + 1)
                    r2 = self.packet.subpack.header[0]
                    p2 = self.packet.subpack.header[1]
                    h2 = self.packet.subpack.header[2]
                    t2 = recorddir[indx[-1] + 1, 1]
                    dt = t_ping - t1
                    dr = dt * (r1 - r2) / (t1 - t2)
                    dp = dt * (p1 - p2) / (t1 - t2)
                    dh = dt * (h1 - h2) / (t1 - t2)
                    self.nav['roll'] =  r1 + dr
                    self.nav['pitch'] =  p1 + dp
                    self.nav['heave'] = h1 + dh
                else:
                    self.nav['roll'] = r1
                    self.nav['pitch'] = p1
                    self.nav['heave'] = h1
        if self.map.packdir.has_key('1013'):
            recorddir = np.asarray(self.map.packdir['1013'])
            indx = np.nonzero(t_ping > recorddir[:, 1])[0]
            if len(indx) > 0:
                self.getrecord(1013, indx[-1])
                h1 = self.packet.subpack.header[0]
                t1 = recorddir[indx[-1], 1]
                if len(recorddir) > (indx[-1] + 1):
                    self.getrecord(1013, indx[-1] + 1)
                    h2 = self.packet.subpack.header[0]
                    t2 = recorddir[indx[-1] + 1, 1]
                    dt = t_ping - t1
                    dh = dt * (h1 - h2) / (t1 - t2)
                    self.nav['heading'] = h1 + dh
                else:
                    self.nav['heading'] = h1
                
    def close(self):
        """closes all open files"""
        self.infile.close()
        
    def extract(self):
        """This pulls out the first x pings as a hack."""
        self.outfilename = self.inname + '_prr.s7k'
        self.outfile = open(self.outfilename, 'wb')
        self.count = 0
        while self.count < 6:
            self.read(False)
            self.packet.skipdata()
            if self.packet.datatype == 7000:
                self.count += 1
        self.end = self.infile.tell()
        self.infile.seek(0)
        self.outfile.write(self.infile.read(self.end))
        self.infile.seek(0)
        self.outfile.close()
        
    def status(self):
        """Print the status of all flags"""
        print 'file name: '  + self.inname
        print 'file type: ' + self.intype
        print 'header read status: ' + str(self.hdr_read)
        print 'data read status: ' + str(self.data_read)
        print 'map status: ' + str(self.mapped)
        print 'size of hypack block remaining: ' + str(self.hypack_hdr)
        print 'size of last record: ' + str(self.last_record_sz)
        print 'split record: ' + str(self.split_record)
        print 'status of the current record is corrupt: ' + str(self.corrupt_record)
        print 'location in file (bytes from start): ' + str(self.infile.tell())
        
        
    def splitfile(self, outfilesize = 1000000):
        """
        Splits the file at the end of a ping (before a 7000 record) just after
        the outfilesize kwarg limit.  A text file is also provided with the
        Start / Stop times for the file.
        """
        # deal with files and names
        pathname, ftype = os.path.splitext(self.infilename)
        ftype=ftype[1:].lower()
        rawfile = open(self.infilename, 'rb')
        rawfile.seek(0,2)
        flen = rawfile.tell()
        rawfile.seek(0,0)
        txtfile = open(pathname+'.txt', 'w')
        # setup pointers, counters, and maps
        ptr = 0
        count = 0
        if not self.mapped:
            self.noisy = False
            self.mapfile()
        map7000 = self.map.packdir['7000']
        # find the offset between POSIX time and seconds of the day
        self.getrecord(7000,0)
        utctime = self.packet.gettime()
        daytime = self.packet.header[8:11]
        start = daytime[0] + daytime[1] * 3600 + daytime[2] * 60
        timeoffset = utctime - start
        while ptr < flen:
            outfilename = pathname + '_' + str(count) + '.' + ftype
            outfile = open(outfilename, 'wb')
            if ptr + outfilesize < flen:
                idx = np.nonzero(map7000[:,0] > ptr + outfilesize)[0]
                # need more logic here to deal with breaks near the end of the file?
                stop = map7000[idx[0] - 1, 1] - timeoffset
                outstr = outfilename + ',' + str(start) + ',' + str(stop) + '\n'
                txtfile.write(outstr)
                if ftype == '7k':
                    # we don't read all the way to the mapped location because of the Hypack header
                    readlen = int(map7000[idx[0], 0]) - ptr - 4
                elif ftype == 's7k':
                    readlen = int(map7000[idx[0], 0]) - ptr
                outfile.write(rawfile.read(readlen))
            else:
                outfile.write(rawfile.read(flen-ptr))
            count += 1
            ptr = rawfile.tell()
            outfile.close()
        txtfile.close()
        rawfile.close()
        
class DataFrame:
    """Designed to read the data frame header, data, and data footer from a
    provided file."""
    def __init__(self, infile):
        self.infile = infile
        self.setup()
        self.header = struct.unpack(self.fmt_hdr,self.infile.read(self.hdr_sz))
        self.read_data()
    
    def setup(self):
        """Header format"""
        self.fmt_hdr = '<2H4I2Hf2BH4I2H3I'
        self.hdr_sz = 64
        self.fmt_ft = '<I'
        self.ft_sz = 4
        
    def read_data(self):
        """Get the packet type"""
        self.datatype = self.header[12]
        self.datasize = self.header[3] - self.hdr_sz - self.ft_sz
        
    def readfoot(self):
        """Read in the data frame footer"""
        foot = self.infile.read(self.ft_sz)
        if len(foot) == 4:
            self.footer = struct.unpack(self.fmt_ft, foot)
        
    def getdata(self):
        """Calls the correct class to read the data part of the data frame"""
        if self.datatype == 7000:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7000(datablock)
        elif self.datatype == 7001:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7001(datablock)
        elif self.datatype == 7004:
            self.subpack = Data7004(self.infile)
        elif self.datatype == 7006:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7006(datablock)
        elif self.datatype == 7007:
            self.subpack = Data7007(self.infile)
        elif self.datatype == 7008:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7008(datablock)
        elif self.datatype == 7010:
            self.subpack = Data7010(self.infile)
        elif self.datatype == 7017:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7017(datablock)
        elif self.datatype == 7018:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7018(datablock,self.header[13], self.header[6])
        elif self.datatype == 7027:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7027(datablock)
        elif self.datatype == 7028:
            self.subpack = Data7028(self.infile)
        elif self.datatype == 7038:
            datablock = self.infile.read(self.datasize)
            self.subpack = Data7038(datablock)
        elif self.datatype == 7041:
            self.subpack = Data7041(self.infile)
        elif self.datatype == 7058:
            self.subpack = Data7058(self.infile)
        elif self.datatype == 7200:
            self.subpack = Data7200(self.infile)
        elif self.datatype == 7503:
            self.subpack = Data7503(self.infile)
        elif self.datatype == 1003:
            self.subpack = Data1003(self.infile)
        elif self.datatype == 1012:
            self.subpack = Data1012(self.infile)
        elif self.datatype == 1013:
            self.subpack = Data1013(self.infile)
        else:
            print 'Data packet type not read yet: ' + str(self.datatype)
            self.skipdata()
            self.infile.seek(-4,1) #skipdata already gets the footer
        
        self.readfoot()
        
    def skipdata(self):
        """Skips the packet if the data type is not desired."""
        self.datablock = self.infile.read(self.datasize)
        self.readfoot()     

    def gettime(self):
        """Converts the header time to seconds in Unix time (1970?) and returns it"""
        self.time_fmt = '%Y, %j, %H, %M'
        self.temptime = str(self.header[6:8])[1:-1] + ', ' + str(self.header[9:11])[1:-1]
        self.timestruct = time.strptime(self.temptime, self.time_fmt)
        self.utctime = calendar.timegm(self.timestruct) + self.header[8]
        return self.utctime
    
    def display(self):
        self.label = ('Protocol Version',
            'Offset',
            'Sync Pattern',
            'Size',
            'Optional data offset',
            'Optional data identifier',
            'Year',
            'Day',
            'Seconds',
            'Hours',
            'Minutes',
            'Reserved',
            'Record type identifier',
            'Device identifier',
            'System enumerator',
            'Reserved',
            'Flags',
            'Reserved',
            'Reserved',
            'Total fragmented records',
            'Fragment number')
        count = 0
        for item in self.header:
            print self.label[count] + ': ' + str(item)
            count += 1


class BaseMeta(type(object)):
    """metaclass to read the "label" attribute and convert it into usable attribute names"""

    def __new__(cls, name, bases, classdict):
        if 'label' in classdict:
            classdict['_data_keys'] = []
            for field in classdict['label']:
                nfield = field.replace(" ", "_").replace("(", "").replace("}", "")
                if nfield in classdict['_data_keys']:
                    # print "Duplicate field found -- %s in class %s" % (nfield, name)
                    i = 0
                    orig_field = nfield
                    while nfield in classdict['_data_keys']:
                        i += 1
                        nfield = "%s%02d" % (orig_field, i)
                classdict['_data_keys'].append(nfield)

            classdict['hdr_sz'] = struct.calcsize(classdict['fmt_hdr'])

        return type(object).__new__(cls, name, bases, classdict)


class BaseData(object):
    """This base class supports classes defining a "label" attribute which is made into read only attributes.
    Also supplies string representation and a display() which prints to stdout.
    """
    # tested packet types in file:
    # ['1003', '1012', '1013', '7000', '7001', '7004', '7006', '7008', '7027', '7028', '7200']
    # unsupported thus far: ['7022', '7300', '7503', '7777']

    __metaclass__ = BaseMeta

    def __init__(self, input_data):
        """This gets the format for each block type and then reads the block"""
        self.setup()
        if isinstance(input_data, basestring):
            datablock = input_data[:self.hdr_sz]
        elif hasattr(input_data, "read"):
            datablock = input_data.read(self.hdr_sz)
        else:
            raise Exception("Unrecognized input data type for %s" % self.__class__.__name__)
        self.header = struct.unpack(self.fmt_hdr, datablock)

    def setup(self):
        pass

    def get_display_string(self):
        result = ""
        for i in xrange(min(len(self.label), len(self.header))):
            result += self.label[i] + ': ' + str(self.header[i]) + "\n"
        return result

    def display(self):
        print self.__repr__()

    def __repr__(self):
        return self.get_display_string()

    def __dir__(self):
        """Custom return of attributes since we have a custom getattr function that adds data members"""
        s = self.__dict__.keys()
        s.extend(self._data_keys)
        s.extend(dir(self.__class__))
        ns = [v for v in s if v[0] != "_"]
        ns.sort()
        return ns

    def __getattr__(self, key):  # Get the value from the underlying subfield (perform any conversion necessary)
        try:
            i = self._data_keys.index(key)  # try to access the subfield
            return self.header[i]
        except:
            raise AttributeError(key + " not in " + str(self.__class__))

    def __setattr__(self, key, value):  # Get the value from the underlying subfield (perform any conversion necessary)
        try:
            i = self._data_keys.index(key)  # try to access the subfield
        except:
            super(BaseData, self).__setattr__(key, value)
        else:
            self.header[i] = value


class BasePlottableData(BaseData):
    def display(self):
        super(BasePlottableData, self).display()
        self.plot()

    def plot(self):
        raise Exception("Need to override the plot method")


class Data7000(BaseData):
    fmt_hdr = '<QIH4f2IfI5f2I5fIf3IfI8fH'
    label = ('SonarID',
             'Ping Number',
             'Multiping Sequence',
             'Frequency',
             'Sample Rate',
             'Receiver Bandwidth',
             'TX Pulse Width',
             'TX Pulse Type ID',
             'TX Pulse Envelope',
             'TX Pulse Envelope Parameter',
             'TX Pulse Reserved',
             'Max Ping Rate',
             'Ping Period',
             'Range Selection',
             'Power Selection',
             'Gain Selection',
             'Control Flags',
             'Projector Identifier',
             'Projector Beam Steering Angle Vertical',
             'Projector Beam Steering Angle Horizontal',
             'Projector Beam Width Vertical',
             'Projector Beam Width Horizontal',
             'Projector Beam Focal Point',
             'Projector Beam Weighting Window Type',
             'Projector Beam Weighting Window Parameter',
             'Transmit Flags',
             'Hydrophone Identifier',
             'Receive Beam Weighting Window',
             'Receive Beam Weighting Paramter',
             'Receive Flags',
             'Receive Beam Width',
             'Bottom Detection Filter Min Range',
             'Bottom Detection Filter Max Range',
             'Bottom Detection Filter Min Depth',
             'Bottom Detection Filter Max Depth',
             'Absorption',
             'Sound Velocity',
             'Spreading',
             'Reserved Flag')


class Data7001(BaseData):
    fmt_hdr = '<QI'
    label = ('SonarID',
             'Number of Devices',
             'Device ID',
             'Device Description',
             'Device Serial Number',
             'Device Info Length',
             'Device Info')

    def __init__(self, datablock):
        """This gets the format for each block type and then reads the block"""
        super(Data7001, self).__init__(datablock)
        self.datapointer = self.hdr_sz
        self.data = []
        self.read_data(datablock)

    def read_data(self, datablock):
        self.fmt_data = '<I64sQI'
        self.data_sz = struct.calcsize(self.fmt_data)
        for i in xrange(self.header[1]):
            device_data = list(struct.unpack(self.fmt_data, datablock[self.datapointer:self.datapointer + self.data_sz]))
            self.datapointer += self.data_sz
            device_info = datablock[self.datapointer: self.datapointer + device_data[-1]]
            device_data.append(device_info)
            self.datapointer += device_data[-2]
            self.data.append(device_data)


class Data7004(BasePlottableData):
    fmt_hdr = '<QI'
    label = ('SonarID',
             'Number of Beams')

    def __init__(self, infile):
        """This gets the format for each block type and then reads the block"""
        super(Data7004, self).__init__(infile)
        self.read_data(infile)

    def read_data(self, infile):
        self.fmt_data = '<' + str(4 * self.header[1]) + 'f'  # There are four sets of variables for each beam
        self.data_sz = 16 * self.header[1]                # There are four var at four bytes each
        self.data = np.asarray(struct.unpack(self.fmt_data, infile.read(self.data_sz)))
        self.data.shape = (4, -1)

    # def display(self):
    #    super(Data7004, self).display()
    #    for i in xrange(self.data[1]):
    #        self.label.append(str(i+1) + 'Beam Vertical Direction')
    #        self.label.append(str(i+1) +' Beam Horizontal Direction')
    #        self.label.append(str(i+1) +' -3dB Vertical Beam Width (Rad)')
    #        self.label.append(str(i+1) +' -3dB Horizontal Beam Width (Rad)')

    def plot(self):
        """Plots the 7004 record as one plot with four subplots."""
        numbeams = self.header[1]
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(411, xlim=(0, numbeams), autoscalex_on=False)
        self.ax1.plot(np.rad2deg(self.data[0, :]))
        self.ax1.set_ylabel('Along Track Angle (deg)')
        self.ax1.set_title('Beam Configuration Information')
        self.ax2 = self.fig.add_subplot(412, sharex=self.ax1, autoscalex_on=False)
        self.ax2.plot(np.rad2deg(self.data[1, :]))
        self.ax2.set_ylabel('Across Track Angle (deg)')
        self.ax3 = self.fig.add_subplot(413, sharex=self.ax1, autoscalex_on=False)
        self.ax3.plot(np.rad2deg(self.data[2, :]))
        self.ax3.set_ylabel('Along Track Beamwidth (deg)')
        self.ax4 = self.fig.add_subplot(414, sharex=self.ax1, autoscalex_on=False)
        self.ax4.plot(np.rad2deg(self.data[3, :]))
        self.ax4.set_ylabel('Across Track Beamwidth (deg)')
        self.ax4.set_xlabel('Beam Number')


class Data7006(BasePlottableData):
    fmt_hdr = '<QIHI2Bf'
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Number of Beams',
             'Flags',
             'Sound Velocity Flag',
             'Sound Velocity')

    def __init__(self, datablock):
        """This gets the format for each block type and then reads the block"""
        super(Data7006, self).__init__(datablock)
        self.datapointer = self.hdr_sz
        self.read_data(datablock)

    def read_data(self, datablock):
        self.numbeams = self.header[3]
        self.fmt_data = '<' + str(self.numbeams) + 'f' + str(self.numbeams) + 'B' + str(3 * self.numbeams) + 'f'
        self.data_sz = 17 * self.numbeams  # one U8 plus four f32 is 17
        self.data = np.array(struct.unpack(self.fmt_data, datablock[self.datapointer: self.datapointer + self.data_sz]))
        self.data.shape = (5, self.numbeams)
        self.detect = np.zeros((self.numbeams, 3))
        for i in xrange(self.numbeams):
            temp = (int(self.data[1, i]) & 12) / 4   # 12 is the mask to get the bottom detect type
                                                     # and divide by four to get to those bits
            if temp == 1:
                self.detect[i, :] = [1, 0, 0]
            elif temp == 2:
                self.detect[i, :] = [0, 1, 0]
            elif temp == 3:
                self.detect[i, :] = [0, 0, 1]

    def plot(self):
        rngplot = plt.scatter(xrange(self.numbeams), self.data[0].T, c=self.detect, edgecolor=self.detect)
        plt.xlim((0, self.numbeams))
        plt.ylim((self.data[0].max(), 0))
        plt.xlabel('Beam Number')
        plt.ylabel('Time (s)')
        plt.draw()


class Data7007(BaseData):
    fmt_hdr = '<QIHf2I8f2H2B'
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Beam Position',
             'Reserved',
             'Samples Per Side',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Number of Beams Per Side',
             'Current Beam Number',
             'Number of Bytes Per Sample',
             'Reserved')

    def __init__(self, infile):
        """This gets the format for each block type and then reads the block"""
        super(Data7007, self).__init__(infile)
        self.read_data(infile)

    def read_data(self, infile):
        self.fmt_data = '<' + str(self.header[5] * self.header[16]) + 'B'
        self.data_sz = self.header[5] * self.header[16]
        self.port = np.array(struct.unpack(self.fmt_data, infile.read(self.data_sz)))
        self.stbd = np.array(struct.unpack(self.fmt_data, infile.read(self.data_sz)))


class Data7008:
    hdr_dtype = np.dtype([('SonarID','Q'),('PingNumber','I'),('Multiping#','H'),
        ('Beams','H'),('Reserved1','H'),('Samples','I'),('RecordSubsetFlag','B'),
        ('RowColumnFlag','B'),('Reserved2','H'),('DataSampleSize','I')])
    data_dtype = np.dtype([('Amp','H'),('Phs','h')])
    def __init__(self, datablock):
        """This gets the format for each block type and then reads the block"""
        hdr_sz = Data7008.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz],Data7008.hdr_dtype)[0]
        self.read_data(datablock[hdr_sz:])
    
    def read_data(self,datablock):
        """Reading the original snippet message.
        This is reading the snippet data and is
        dependant on the information from the
        header. The steps 1)read each beam
        snippet size 2)read in the data for each
        beam, which could consist of magnitude,
        phase, I&Q, for each beam or element."""
            
        #define the format string and size for snippet data through bitwise ops
        #Thanks to Tom Weber and Les Peabody for helping figure this out
        fmt_flags = self.header['DataSampleSize']
        magval = 7 & fmt_flags
        phaseval = (240 & fmt_flags) >> 4
        iqval = (3840 & fmt_flags) >> 8
        elementflag = (28672 & fmt_flags) >> 12
        fmt = []
        if magval == 2:
            fmt.append(('Magnitude','H'))
        elif magval == 3:
            fmt.append(('Magnitude','I'))
        if phaseval == 2:
            fmt.append(('Phase','H'))
        elif phaseval == 3:
            fmt.append(('Phase','I'))
        if iqval == 1:
            fmt.append(('I','H'),('Q','H'))
        elif iqval == 2:
            fmt.append(('I','I'),('Q','I'))
        snip_fmt = np.dtype(fmt)
        beam_fmt = np.dtype([('BeamNumber','H'),('FirstSample','I'),('LastSample','I')])
        #read the beam snippet sizes (zones)
        self.numbeams = self.header['Beams']
        block_sz = self.numbeams * beam_fmt.itemsize
        self.beams = np.frombuffer(datablock[:block_sz], beam_fmt)
        temp = (self.beams['LastSample']-self.beams['FirstSample']).max() + 1
        self.numsnip = temp.max()
        if not (self.numsnip == temp).all():
            print "Warning: number of snippets is not consistent."
        
        #read snippet data as columns for each data type (mag/phase/i/q)
        snip = np.frombuffer(datablock[block_sz:], snip_fmt)
        #separate types out to different arrays
        ordertype = self.header[7]
        if magval != 0:
            self.mag = snip['Magnitude'].astype(np.float64)
            if ordertype == 0:
                self.mag.shape = (self.numbeams,self.numsnip)
                self.mag = self.mag.transpose()
            elif ordertype == 1:
                self.mag.shape = (self.numsnip,self.numbeams)
        if phaseval !=0:
            self.phase = snip['Phase'].astype(np.float64)
            if self.header[7] == 0:
                self.phase.shape = (self.numbeams,self.numsnip)
                self.phase = self.phase.transpose()
            elif self.header[7] == 1:
                self.phase.shape = (self.numsnip,self.numbeams)             
        if iqval != 0:
            self.iele = snip['I'].astype(np.float64)
            self.qele = snip['Q'].astype(np.float64)
            if self.header[7] == 0:
                self.iele.shape = (self.numbeams,self.numsnip)
                self.iele = self.iele.transpose()
                self.qele.shape = (self.numbeams,self.numsnip)
                self.qele = self.qele.transpose()
            elif self.header[7] == 1:
                self.iele.shape = (self.numsnip,self.numbeams)
                self.qele.shape = (self.numsnip,self.numbeams)                        
                            
    def plot(self):
        """plot any snippet data collected"""
        if hasattr(self, 'mag'):
            # plt.figure()
            magplot = plt.imshow(20*np.log10(self.mag), aspect = 'auto')
            plt.title('7008 20*log10*Magnitude')
            plt.xlabel('Beam number')
            plt.ylabel('Sample number in window')
        if hasattr(self, 'phase'):
            plt.figure()
            phaseplot = plt.imshow(self.phase, aspect = 'auto')
            plt.title('7008 Phase')
            plt.xlabel('Beam number')
            plt.ylabel('Sample number in window')
        plt.draw()

    def display(self):
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        print 'Size of snippet window: ' + str(self.numsnip) 
        self.plot()


class Data7010(BaseData):
    fmt_hdr = '<QIH2I'
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Samples',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved')

    def __init__(self, infile):
        """This gets the format for each block type and then reads the block"""
        super(Data7010, self).__init__(infile)
        self.read_data(infile)

    def read_data(self, infile):
        self.fmt_data = '<' + str(self.header[4] - 1) + 'I'
        self.data_sz = self.header[4] * 4
        self.data = struct.unpack(self.fmt_data, infile.read(self.data_sz))


class Data7017(BasePlottableData):
    fmt_hdr = '<QIH2IBI6fB2f14I'
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Number of Beams',
             'Data Block Size',
             'Detection algorithm',
             'Flags',
             'Min Depth',
             'Max Depth',
             'Min Range',
             'Max Range',
             'Min Nadir Search',
             'Max Nadir Search',
             'Automatic Filter Window',
             'Applied Roll',
             'Depth Gate Tilt',
             'Reserved')

    def __init__(self, datablock):
        """This gets the format for each block type and then reads the block.
        Format was created from Reson DFD Version 2.2"""
        super(Data7017, self).__init__(datablock)
        self.datapointer = self.hdr_sz
        self.read_data(datablock)

    def read_data(self, datablock):
        self.numbeams = self.header[3]
        fmt_base = 'HfI4fIf'
        if self.numbeams > 0:
            self.fmt_data = '<' + self.numbeams * fmt_base
            self.data_sz = struct.calcsize(self.fmt_data)
            self.data = np.array(struct.unpack(self.fmt_data, datablock[self.datapointer: self.datapointer + self.data_sz]))
            self.datapointer += self.data_sz
            self.data.shape = (self.numbeams, -1)
            self.detect = np.zeros((self.numbeams, 3))
            for i in xrange(self.numbeams):
                temp = (int(self.data[i, 3]) & 3)   # 3 is the mask to get the bottom detect type
                if temp == 1:
                    self.detect[i, :] = [1, 0, 0]
                elif temp == 2:
                    self.detect[i, :] = [0, 1, 0]
                elif temp == 3:
                    self.detect[i, :] = [0, 0, 1]
        else:
            self.data = None
            self.detect = None

    def plot(self):
        if self.data is not None:
            rngplot = plt.scatter(self.data[:,0],self.data[:,1],c=self.detect,edgecolor = self.detect)
            plt.xlim((0, self.numbeams))
            plt.ylim((self.data[1].max(), 0))
            plt.xlabel('Beam Number')
            plt.ylabel('?')
            plt.draw()
        else:
            print "No beams in record."


class Data7018:
    """This record had two versions, one for the 7111 and one for the 7125.
    In the beginning of 2011 the 7111 was brought in alignment with the 7125
    version."""
    hdr_dtype = np.dtype([('SonarID','Q'),('PingNumber','I'),('Multiping#','H'),
        ('Beams','H'),('Samples','I'),('Reserved','8I')])
    data_dtype = np.dtype([('Amp','H'),('Phs','h')])
    def __init__(self, datablock, sonar_type, year):
        if sonar_type == 7111 and year < 2011:
            print "This is old 7111 data and is no longer supported by this module."
        else:
            hdr_sz = Data7018.hdr_dtype.itemsize
            self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data7018.hdr_dtype)[0]
            self.read_data(datablock[hdr_sz:])
        
    def read_data(self, subdatablock):
        """
        Read the data into a numpy array.
        """
        beams = self.header['Beams']
        data = np.frombuffer(subdatablock, dtype = Data7018.data_dtype)
        self.mag = data['Amp'].astype('f')
        self.mag.shape = (-1,beams)
        self.phase = data['Phs'].astype('f')
        self.phase.shape = (-1,beams)

    def plot(self):
        """plot water column data"""
        plt.subplot(1,2,1)
        magplot = plt.imshow(20*np.log10(self.mag), aspect = 'auto')
        plt.title('7018 Magnitude')
        plt.xlabel('Beam number')
        plt.ylabel('Sample number')
        #plt.colorbar()
        plt.subplot(1,2,2)
        #plt.figure()
        phaseplot = plt.imshow(self.phase, aspect = 'auto')
        plt.title('7018 Phase')
        plt.xlabel('Beam number')
        plt.ylabel('Sample number')
        #plt.colorbar()
        plt.suptitle(('Ping number ' + str(self.header[1])))
        plt.draw()

    def display(self):
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        self.plot()


class Data7027(BasePlottableData):
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Number of Beams',
             'Data Field Size',
             'Detection algorithm',
             'Flags',
             'Sampling Rate',
             'Tx angle',
             'Reserved')
    fmt_hdr = '<QIH2IBI2f16I'

    def __init__(self, datablock):
        """This gets the format for each block type and then reads the block.
        Format was created from Reson DFD Version 2.2"""
        super(Data7027, self).__init__(datablock)
        self.datapointer = self.hdr_sz
        self.read_data(datablock)

    def read_data(self, datablock):
        self.numbeams = self.header[3]
        datafieldsize = self.header[4]
        if datafieldsize == 22:
            fmt_base = 'H2f2If'
        elif datafieldsize == 26:
            fmt_base = 'H2f2I2f'
        if self.numbeams > 0:
            self.fmt_data = '<' + self.numbeams * fmt_base
            self.data_sz = struct.calcsize(self.fmt_data)
            self.data = np.array(struct.unpack(self.fmt_data, datablock[self.datapointer: self.datapointer + self.data_sz]))
            self.datapointer += self.data_sz
            self.data.shape = (self.numbeams, -1)
            self.detect = np.zeros((self.numbeams, 3))
            for i in xrange(self.numbeams):
                temp = (int(self.data[i, 3]) & 3)   # 3 is the mask to get the bottom detect type
                if temp == 1:
                    self.detect[i, :] = [1, 0, 0]
                elif temp == 2:
                    self.detect[i, :] = [0, 1, 0]
                elif temp == 3:
                    self.detect[i, :] = [0, 0, 1]
        else:
            self.data = None
            self.detect = None

    def plot(self):
        if self.data is not None:
            rngplot = plt.scatter(self.data[:, 0], self.data[:, 1], c=self.detect, edgecolor=self.detect)
            plt.xlim((0, self.numbeams))
            plt.ylim((self.data[1].max(), 0))
            plt.xlabel('Beam Number')
            plt.ylabel('Sample Number')
            plt.draw()
        else:
            print "No beams in record."


class Data7028(BasePlottableData):
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Number of Beams',
             'Error flag',
             'Control flags',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved')
    fmt_hdr = '<QI2H2B7I'

    def __init__(self, infile):
        """This gets the format for each block type and then reads the block"""
        super(Data7028, self).__init__(infile)
        self.fmt_descriptor = '<H3I'
        self.descriptor_sz = struct.calcsize(self.fmt_descriptor)
        self.read_data(infile)

    def read_data(self, infile):
        self.numpoints = self.header[3]
        if self.header[4] == 0:
            self.descriptor = np.zeros((self.numpoints, 4))
            for beam in xrange(self.numpoints):
                self.descriptor[beam, :] = struct.unpack(self.fmt_descriptor, infile.read(self.descriptor_sz))
            self.beamwindow = self.descriptor[:, 3] - self.descriptor[:, 1] + 1
            self.maxbeam = int(self.descriptor[:, 0].max()) + 1
            self.maxwindow = self.beamwindow.max()
            self.snippets = np.zeros((self.maxbeam, self.maxwindow))
            for beam in xrange(self.numpoints):
                self.fmt_data = '<' + str(int(self.beamwindow[beam])) + 'H'
                self.data_sz = struct.calcsize(self.fmt_data)
                self.startoffset = int((self.maxwindow - self.beamwindow[beam]) / 2)
                self.snippets[int(self.descriptor[beam, 0]), self.startoffset: self.startoffset + self.beamwindow[beam]] = struct.unpack(self.fmt_data, infile.read(self.data_sz))
        else:
            # Error flag indicates no data.
            self.beamwindow = None
            self.maxbeam = None
            self.maxwindow = None
            self.snippets = None

    def plot(self):
        if self.snippets is not None:
            plt.figure()
            self.aspect = float(self.numpoints) / self.beamwindow.max()
            magplot = plt.imshow(20 * np.log10(self.snippets.T), aspect=self.aspect)
            plt.title('7028 20*log10*Magnitude')
            plt.xlabel('Beam number')
            plt.ylabel('Sample number in window')
            plt.draw()
        else:
            print "No snippets to plot"


class Data7038(BasePlottableData):
    fmt_hdr = '<QI2HIH2IH7I'
    label = ('SonarID',
             'Ping Number',
             'Reserved',
             'Elements',
             'Samples',
             'Element Reduction',
             'Start Sample',
             'Stop Sample',
             'Sample Type',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved')

    def __init__(self, datablock):
        """This gets the format for each block type and then reads the block"""
        super(Data7038, self).__init__(datablock)
        self.datapointer = self.hdr_sz
        self.read_data(datablock)

    def read_data(self, datablock):
        self.numelements = self.header[5]
        self.numsamples = self.header[7] - self.header[6] + 1  # plus one to include last sample?
        self.sample_sz = self.header[8]

        self.fmt_elements = '<' + str(self.numelements) + 'H'
        endread = struct.calcsize(self.fmt_elements) + self.datapointer
        self.elements = struct.unpack(self.fmt_elements, datablock[self.datapointer:endread])
        self.datapointer = endread

        if self.sample_sz == 8:
            self.sample_fmt = 'B'
        elif self.sample_sz == 12:
            self.sample_fmt = 'H'
        elif self.sample_sz == 16:
            self.sample_fmt = 'H'
        elif self.sample_sz == 32:
            self.sample_fmt = 'I'
        else:
            self.sample_fmt = 'unknown'
        if self.sample_fmt is not 'unknown':
            self.fmt_data = '<' + str(2 * self.numsamples * self.numelements) + self.sample_fmt
            endread = struct.calcsize(self.fmt_data) + self.datapointer
            self.data = np.array(struct.unpack(self.fmt_data, datablock[self.datapointer:endread]))
            self.datapointer = endread
            self.r = np.zeros(self.numsamples * self.numelements, complex)
            self.phase = np.zeros(self.numsamples * self.numelements)
            self.data.shape = (-1, 2)
            for c in xrange(len(self.data)):
                self.r[c] = complex(self.data[c, 0], self.data[c, 1])
                self.phase[c] = math.atan2(self.data[c, 1], self.data[c, 0])
        else:
            print 'unknown sample size to unpack'

    def plot(self):
        # reshape arrays for plotting
        self.phase.shape = (self.numsamples, self.numelements)
        self.r.shape = (self.numsamples, self.numelements)
        # for plot 1&2
        self.amp = abs(self.r)
        # for plot 3, take fft...
        self.ampfft = abs(np.fft.fft(self.r))
        # ...and swap the sides to center the 0 freq
        self.ampfft2 = np.zeros(self.ampfft.shape)
        self.ampfft2[:, self.numelements / 2:] = self.ampfft[:, :self.numelements / 2]
        self.ampfft2[:, :self.numelements / 2] = self.ampfft[:, self.numelements / 2:]

        f = plt.figure()
        # f.text(0.5, 0.975, 'From file ' + self.infilename,horizontalalignment = 'center', verticalalignment = 'top')
        plt.subplot(2, 2, 1)
        plt.imshow(self.amp, aspect='auto')
        plt.title('Element Amplitude')
        plt.ylabel('Samples')

        plt.subplot(2, 2, 2)
        plt.imshow(20 * np.log10(self.amp), aspect='auto')
        plt.title('20*log10(Element Amplitude)')
        plt.ylabel('Samples')

        plt.subplot(2, 2, 3)
        plt.imshow(20 * np.log10(self.ampfft2), aspect='auto')
        plt.title('20*log10(fft(Element Amplitude)')
        plt.ylabel('Samples')
        plt.xlabel('Element Number')

        plt.subplot(2, 2, 4)
        plt.imshow(self.phase, aspect='auto')
        plt.title('Element Phase')
        plt.ylabel('Samples')
        plt.xlabel('Element Number')

        plt.draw()


class Data7041(BasePlottableData):
    """This record is the compressed beam formed magnitude data as of 8/8/2011."""
    fmt_hdr = '<QI3Hf4I'
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Number of Beams',
             'Flags',
             'Sample Rate',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved')

    def __init__(self, infile):
        """This gets the format for each block type and then reads the block"""
        super(Data7041, self).__init__(infile)
        self.read_data(infile)

    def read_data(self, infile):
        self.numbeams = self.header[3]
        self.flags = self.header[4]
        if (self.flags & 1) == 1:
            self.dtype = 'H'
        else:
            self.dtype = 'B'
        if (self.flags & 128) == 128:
            self.beamid = 'f'
        else:
            self.beamid = 'H'
        self.data_fmt = '<' + self.beamid + 'I'
        self.data_sz = struct.calcsize(self.data_fmt)
        tempdata = []
        maxlen = 0
        for i in xrange(self.numbeams):
            self.beaminfo = struct.unpack(self.data_fmt, infile.read(self.data_sz))
            if self.beaminfo[1] > maxlen:
                maxlen = self.beaminfo[1]
            self.data2_fmt = '<' + str(self.beaminfo[1]) + self.dtype
            self.data2_sz = struct.calcsize(self.data2_fmt)
            tempdata.append(struct.unpack(self.data2_fmt, infile.read(self.data2_sz)))
        self.beamdata = np.zeros((self.numbeams, maxlen))
        for i, beam in enumerate(tempdata):
            self.beamdata[i, :len(beam)] = beam
        self.beamdata = self.beamdata.T

    def plot(self):
        """plot water column data"""
        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        magplot = plt.imshow(20 * np.log10(self.beamdata), aspect='auto')
        plt.title('7041 record - 20 * log10(Compressed Magnitude)')
        plt.xlabel('Beam number')
        plt.ylabel('Sample number')
        plt.colorbar()
        plt.draw()


class Data7058(BasePlottableData):
    fmt_hdr = '<QI2HBI7I'
    label = ('SonarID',
             'Ping Number',
             'Multi-ping Sequence',
             'Number of Beams',
             'Error flag',
             'Control flags',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved')

    def __init__(self, infile):
        """This gets the format for each block type and then reads the block"""
        super(Data7058, self).__init__(infile)
        self.fmt_descriptor = '<H3I'
        self.descriptor_sz = struct.calcsize(self.fmt_descriptor)
        self.read_data(infile)

    def read_data(self, infile):
        self.numpoints = self.header[3]
        if self.header[4] == 0:
            self.descriptor = np.zeros((self.numpoints, 4))
            for beam in xrange(self.numpoints):
                self.descriptor[beam, :] = struct.unpack(self.fmt_descriptor, infile.read(self.descriptor_sz))
            self.beamwindow = self.descriptor[:, 3] - self.descriptor[:, 1] + 1
            self.maxbeam = int(self.descriptor[:, 0].max()) + 1
            self.maxwindow = self.beamwindow.max()
            self.snippets = np.zeros((self.maxbeam, self.maxwindow))
            for beam in xrange(self.numpoints):
                self.fmt_data = '<' + str(int(self.beamwindow[beam])) + 'f'
                self.data_sz = struct.calcsize(self.fmt_data)
                self.startoffset = int((self.maxwindow - self.beamwindow[beam]) / 2)
                self.snippets[int(self.descriptor[beam, 0]), self.startoffset: self.startoffset + self.beamwindow[beam]] = struct.unpack(self.fmt_data, infile.read(self.data_sz))
        elif self.header[4] == 1:
            print '7058 "No calibration" error at ping ' + str(self.header[1])
        elif self.header[4] == 2:
            print '7058 "TVG Read error" error at ping ' + str(self.header[1])
        elif self.header[4] == 3:
            print '7058 "CTD not available" error at ping ' + str(self.header[1])
        elif self.header[4] == 4:
            print '7058 "Invalide sonar geometry" error at ping ' + str(self.header[1])
        elif self.header[4] == 5:
            print '7058 "Invalid sonar specifications" error at ping ' + str(self.header[1])
        elif self.header[4] == 6:
            print '7058 "Bottom detection failed" error at ping ' + str(self.header[1])
        elif self.header[4] == 7:
            print '7058 "No power" error at ping ' + str(self.header[1])
        elif self.header[4] == 8:
            print '7058 "No gain" error at ping ' + str(self.header[1])
        elif self.header[4] == 255:
            print '7058 "Missing c7k file" error at ping ' + str(self.header[1])
        else:
            print '7058 error flag at ping ' + str(self.header[1])

    def plot(self):
        plt.figure()
        self.aspect = float(self.numpoints) / self.beamwindow.max()
        magplot = plt.imshow(20 * np.log10(self.snippets.T), aspect=self.aspect)
        plt.title('7028 20*log10*Magnitude')
        plt.xlabel('Beam number')
        plt.ylabel('Sample number in window')
        plt.draw()


class Data7200(BaseData):
    fmt_hdr = '<QQ2HQQ2I64B16B64B128c'
    label = ('File ID',
             'Version Number',
             'Reserved',
             'Session ID',
             'Record Data Size',
             'Number of Devices',
             'Recording Name',
             'Recording Program Verision Number',
             'User Defined Name',
             'Notes')


class Data7503(BaseData):
    """Up through version 2.0 of the data format definition document this
    record is reported incorrectly.  There is no multiping sequence."""
    fmt_hdr = '<QI4f2IfI5f2I5fIf3IfI7fH6fI2H2f2dH2IfIf4B7I'
    label = ('Sonar ID',
             'Ping Number',
             'Frequency',
             'Sample rate',
             'Receiver bandwidth',
             'Tx pulse width',
             'Tx pulse type identifier',
             'Tx pulse envelope identifier',
             'Tx pulse envelope parameter',
             'Tx pulse reserved',
             'Max ping rate',
             'Ping period',
             'Range selection',
             'Power selection',
             'Gain selection',
             'Control flags',
             'Projector ID',
             'Projector beam steering angle vertical',
             'Projector beam steering angle horizontal',
             'Projector beam -3dB beam width vertical',
             'Projector beam -3dB beam width horizontal',
             'Projector beam focal point',
             'Projector beam weighting window type',
             'Projector beam weighting window parameter',
             'Transmit flags',
             'Hydrophone ID',
             'Receive beam weighting window',
             'Receive beam weighting parameter',
             'Receive flags',
             'Bottom detection filter min range',
             'Bottom detection filter max range',
             'Bottom detection filter min depth',
             'Bottom detection filter max depth',
             'Absorption',
             'Sound Velocity',
             'Spreading',
             'Reserved',
             'Tx array position offset X',
             'Tx array position offset Y',
             'Tx array position offset Z',
             'Head tilt X',
             'Head tilt Y',
             'Head tilt Z',
             'Ping state',
             'Equiangle/Equidistant Mode',
             '7kCenter mode',
             'Adaptive gate bottom filter min depth',
             'Adaptive gate bottom filter max depth',
             'Trigger out width',
             'Trigger out offset',
             '81xx series projector Selection',
             'Reserved',
             'Reserved',
             '81xx series alternate gain',
             'Reserved',
             'Coverage angle',
             'Coverage mode',
             'Quality filter flags',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved',
             'Reserved')


class Data1003(BaseData):
    label = ('DatumID',
            'Latency',
            'Northing (Lat)',
            'Easting (Lon)',
            'Height (m)',
            'Position Type',
            'UTM Zone',
            'Quality Flag',
            'Positioning Method',
            'Positioning Method (cont)')
    fmt_hdr = '<If3d5B'


class Data1012(BaseData):
    label = ('Roll', 'Pitch', 'Heave')
    fmt_hdr = '<3f'


class Data1013(BaseData):
    label = ('Heading')
    fmt_hdr = '<f'
            
class mappack:
    """Acts as a map for the location of each of the packets
    for a particular packet type for the file in question"""
    def __init__(self):
        """Makes the first entry in the array"""
        self.packdir = {}
        self.sizedir = {}
        
    def add(self, type, location=0, time=0, ping=0, size = 0):
        """Adds the location, time and ping to the tuple for the value type"""
        self.type = type
        self.store = [location,time,ping]
        if self.type in self.packdir:
            self.packdir[self.type].append(self.store)
            self.sizedir[self.type] += size
        else:
            self.packdir[self.type] = []
            self.packdir[self.type].append(self.store)
            self.sizedir[self.type] = size
            
    def finalize(self):
        for key in self.packdir.keys():
            temp = np.asarray(self.packdir[key])
            tempindx = temp[:,1].argsort()
            self.packdir[key] = temp[tempindx,:]
        
    def find(self,valtype,val):
        """Finds the desired packet either by time stamp or by ping number"""
        pass
        
    def printmap(self):
        keys = []
        totalsize = 0
        for i,v in self.packdir.iteritems():
            keys.append((i,len(v)))
            totalsize += self.sizedir[i]
        keys.sort()
        for key in keys:
            percent = 10000 * self.sizedir[str(key[0])]/totalsize
            print 'message ' + str(key[0]) + ' has ' + str(key[1]) + ' packets and ' + str(0.01 * percent) + '% of file'

    def plotmap(self):
        """
        Plots to location of each of the packets in the file.
        """
        keys = list(self.packdir.keys())
        keys.sort()
        plt.figure()
        for key in keys:
            plt.plot(self.packdir[key][:,0])
        plt.xlabel('Packet Number')
        plt.ylabel('Location in file')
        plt.legend(keys, loc = 'lower right')
            
    def save(self,outfilename):
        self.outfile = open(outfilename + '.prr','wb')
        pickle.dump(self.packdir,self.outfile)
        
    def load(self,infilename):
        self.infile = open(infilename + '.prr','r+b')
        pickle.load(self.infile)

def main():
    print """\n prr V-0.1 (for experimental use)'
This script is for reading files containing the Reson 7k format.

Enter the name of the file containing the data: """,
    infilename = sys.stdin.readline()[0:-1]
    print 'Filename read as: %s\n' %(infilename)
    reader = x7kRead(infilename)
    #reader.extract()
    reader.mapfile()
    firstping = reader.map.packdir['7000'][0][1]
    print 'The first ping time stamp in this file is ' + str(time.ctime(firstping))
    print 'Packet summary:'
    reader.map.printmap()
    reader.close()
    
    print "Press 'Enter' to exit"
    sys.stdin.readline()

if __name__ == '__main__':
    main()
        