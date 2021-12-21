"""Python Reson Reader
G.Rice 9/10/10
V0.3.9 20150107
This is intended to help trouble shoot Reson data directly from the Reson datagrams.
It was inspired by The Great Sam Greenaway during his graduate work at UNH.

Updated for Python3
"""

import os, sys, struct, pickle
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta, timezone, datetime


class X7kRead:
    """
    Open a file in binary mode and give a packet reader the proper data blocks to read the data packets
    """

    def __init__(self, infilename, start_ptr=0, end_ptr=0):
        """
        opens and memory maps the file
        """
        # format info for reading 7K files
        self.hypack_sz = 4  # hypack header size
        self.hypack_fmt = '<I'
        self.netfrm_sz = 36  # Reson Network Frames size
        self.netfrm_fmt = '<HHIHH4IHHI'

        # initialize flags for reading methods
        self.eof = False  # end of file reached
        self.start_ptr = start_ptr
        self.end_ptr = end_ptr
        self.hdr_read = False  # header read status
        self.data_read = False  # data read status
        self.hypack_hdr = 0  # size of the hypack block remaining
        self.netfrm_hdr = 0  # size of the Reson block remaining
        self.last_record_sz = 0  # size of the last record
        self.corrupt_record = False  # status of the current record is corrupt
        self.split_record = False  # split record
        self.mapped = False  # status of the mapping

        # find file type and open file
        self.infilename = infilename
        [self.inname, self.intype] = os.path.splitext(infilename)
        self.intype = self.intype[1:].lower()
        self.tempread = True
        if self.intype in ('7k', 's7k'):
            self.infile = open(infilename, 'rb')
        else:
            print(f'invalid file type: {self.intype}')
        self.infile.seek(0, 2)
        self.filelen = self.infile.tell()
        self.infile.seek(0)

        self.packet = None  # the last decoded datagram
        self.map = None  # the mappack object generated on mapfile

    def read(self, verbose=False):
        """
        Decides what type of reading needs to be done
        """

        if self.infile.tell() >= self.start_ptr + self.filelen:
            self.eof = True

        if not self.eof:
            if self.hdr_read and not self.data_read:
                self.packet.skipdata()
            try:
                if self.intype == '7k':
                    self.read7k(verbose)
                elif self.intype == 's7k':
                    self.reads7k(verbose)
                if verbose:
                    print(self.packet.dtype)
                self.hdr_read = True
                self.data_read = False
            except EOFError:
                self.eof = True
                self.hdr_read = False
                self.data_read = False

    def reads7k(self, verbose):
        """Processes data block according to the s7k format"""
        # read data record frame
        packetsize = self.checkfile(verbose)
        if self.tempread:
            if packetsize is None:
                print('Unable to find packet size in header!')
            else:
                start_of_datagram = self.infile.tell()
                self.packet = Datagram(self.infile.read(packetsize), start_of_datagram)

    def read7k(self, verbose=True):
        """Removes the Hypack Header and the Reson Network Frames and then assumes s7k format."""
        if self.split_record:
            self.infile.seek(36, 1)  # this takes into account the netframe header for the next read, but doesn't fix the problem
            self.hypack_hdr -= 36
            self.split_record = False
        if self.hypack_hdr < 0:  # this happens when a hypack header falls inside of a record
            if np.abs(self.hypack_hdr) > self.last_record_sz:  # I don't know why this happens
                self.hypack_hdr = 0
            else:  # this goes back into the corrupted record to find the hypack header
                self.infile.seek(self.hypack_hdr, 1)
                temp = struct.unpack(self.hypack_fmt, self.infile.read(self.hypack_sz))[0]
                self.infile.seek(-self.hypack_hdr, 1)
                self.hypack_hdr += temp
        if self.hypack_hdr == 0:
            temp = self.infile.read(self.hypack_sz)
            if len(temp) == self.hypack_sz:
                [self.hypack_hdr] = struct.unpack(self.hypack_fmt, temp)
        temp = self.infile.read(self.netfrm_sz)
        self.reads7k(verbose=verbose)
        if len(temp) == self.netfrm_sz:
            self.netfrm_hdr = struct.unpack(self.netfrm_fmt, temp)
            self.last_record_sz = self.packet.header[3] + self.netfrm_sz
            self.hypack_hdr = self.hypack_hdr - self.last_record_sz
            if self.hypack_hdr < 0:
                self.corrupt_record = True
            else:
                self.corrupt_record = False
            if self.netfrm_hdr[5] < self.netfrm_hdr[6]:  # this is when records are broken up
                self.split_record = True

    def skip(self):
        """Skips the data part of a record."""
        if not self.hdr_read:
            self.read()
        self.hdr_read = False

    def get(self):
        """Reads the data part of a record."""
        if not self.hdr_read:
            self.read()
        try:
            self.packet.decode()
        except NotImplementedError as err:
            print(err)
        self.data_read = True

    def display(self):
        """Displays the information from a packet using the records display method."""
        if not self.data_read:
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

    def findpacket(self, datatype, verbose=True):
        """Finds the requested packet type and reads the packet"""
        self.read(verbose)
        while datatype != self.packet.datatype and self.tempread:
            self.read(verbose)
        if self.tempread:
            self.get()
        else:
            print('no ' + str(datatype) + ' record found in file')

    def checkfile(self, verbose=True):
        """Read file to check for validity of next block"""
        badblock = True
        self.tempread = True
        count = 0
        packetsize = None
        while self.tempread and badblock:
            try:
                tempstr = self.infile.read(8)
                temp = struct.unpack('<HHI', tempstr)
                if temp[2] == 65535:  # This is 0x0000FFFF, Reson Sync Pattern
                    packetsize = np.fromfile(self.infile, dtype=np.uint32, count=1)[0]
                    self.infile.seek(-12, 1)
                    badblock = False
                else:
                    self.infile.seek(-7, 1)
                    count += 1
                    self.hdr_read = False
                    self.data_read = False
                    self.hypack_hdr = 0
                    self.last_record_sz = 0
            except AssertionError:
                # print "End of file"
                self.tempread = False
        if count != 0:
            if verbose:
                print("reset " + str(count) + " bytes to " + str(self.infile.tell()))
        return packetsize

    def mapfile(self, verbose=False, show_progress=True):
        """Maps the location of all the packets in the file.
        Parts of this method act as an intermediary between the
        reader class and the packet class, but may need to be
        moved to their own layer at some point."""
        if not self.mapped:
            self.map = MapPack()
            count_corrupt = 0
            self.reset()
            progress = 0
            if show_progress:
                print('Mapping file')
                print('00 percent')
            while not self.eof:
                self.read(verbose=verbose)
                try:
                    packettime = self.packet.gettime()
                except ValueError:
                    print("Bad time stamp found at " + str(self.packet.datagram_start))
                    packettime = np.nan
                    self.corrupt_record = True
                if self.corrupt_record:
                    count_corrupt += 1
                if self.tempread:
                    self.skip()
                    self.map.add(str(self.packet.dtype), self.packet.datagram_start, packettime, size=self.packet.datagram_size)
                    current = 100 * self.infile.tell() / self.filelen
                    if current - progress >= 1:
                        progress = current
                        if show_progress:
                            sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' % {'percent': progress})
            self.reset()
            if show_progress:
                print('\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.')
            if verbose:
                self.map.printmap()
                print(str(count_corrupt) + ' corrupt records found.')
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
        self.eof = False
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
        if '7000' in self.map.packdir:
            if numping < len(self.map.packdir['7000']):
                ping = {}
                recordlist = self.map.packdir.keys()
                indx = np.nonzero('7000' == np.asarray(recordlist)[:])
                recordlist.pop(indx[0])
                self.getrecord(7000, numping)
                ping['header'] = self.packet.header
                ping['7000'] = self.packet.subpack
                t_ping = self.packet.gettime()
                for record in recordlist:
                    recorddir = np.asarray(self.map.packdir[record])
                    indx = np.nonzero(t_ping == recorddir[:, 1])[0]
                    if len(indx) == 1:
                        self.getrecord(record, indx[0])
                        try:
                            ping[record] = self.packet.subpack
                        except AttributeError:
                            pass
                    elif len(indx) > 1:
                        print('more than one record of ' + record + ' type found.')
                return t_ping
            else:
                print('ping is beyond record length.')
        else:
            print('No 7000 record found!')

    def getnav(self, t_ping):
        """This method takes a time stamp and IF there is navigation in the
        file creates a "nav" dictionary for that time stamp, containing x, y,
        roll, pitch, heading, and heave."""
        if not self.mapped:
            self.reset()
            self.mapfile()
        self.intype = 's7k'
        nav = {}
        if '1003' in self.map.packdir:
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
                    nav['x'] = x1 + dx
                    nav['y'] = y1 + dy
                    nav['z'] = z1 + dz
                else:
                    nav['x'] = x1
                    nav['y'] = y1
                    nav['z'] = z1
        if '1012' in self.map.packdir:
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
                    nav['roll'] = r1 + dr
                    nav['pitch'] = p1 + dp
                    nav['heave'] = h1 + dh
                else:
                    nav['roll'] = r1
                    nav['pitch'] = p1
                    nav['heave'] = h1
        if '1013' in self.map.packdir:
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
                    nav['heading'] = h1 + dh
                else:
                    nav['heading'] = h1

    def close(self):
        """closes all open files"""
        self.infile.close()

    def status(self):
        """Print the status of all flags"""
        print('file name: ' + self.inname)
        print('file type: ' + self.intype)
        print('header read status: ' + str(self.hdr_read))
        print('data read status: ' + str(self.data_read))
        print('map status: ' + str(self.mapped))
        print('size of hypack block remaining: ' + str(self.hypack_hdr))
        print('size of last record: ' + str(self.last_record_sz))
        print('split record: ' + str(self.split_record))
        print('status of the current record is corrupt: ' + str(self.corrupt_record))
        print('location in file (bytes from start): ' + str(self.infile.tell()))


class Datagram:
    """Designed to read the data frame header, data, and data footer from a
    provided file."""

    hdr_dtype = np.dtype([('ProtocolVersion', 'u2'), ('Offset', 'u2'), ('SyncPattern', 'u4'), ('Size', 'u4'),
                          ('OptionalDataOffset', 'u4'), ('OptionalDataIdentifier', 'u4'), ('Year', 'u2'), ('Day', 'u2'),
                          ('Seconds', 'f4'), ('Hours', 'u1'), ('Minutes', 'u1'), ('RecordVersion', 'u2'),
                          ('RecordTypeIdentifier', 'u4'), ('DeviceIdentifier', 'u4'), ('ReservedOne', 'u2'),
                          ('SystemEnumerator', 'u2'), ('ReservedTwo', 'u4'), ('Flags', 'u2'), ('ReservedThree', 'u2'),
                          ('ReservedFour', 'u4'), ('TotalRecordsFragmented', 'u4'), ('FragmentNumber', 'u4')])

    def __init__(self, fileblock, start_file_pointer):
        self.start_file_pointer = start_file_pointer
        hdr_sz = Datagram.hdr_dtype.itemsize
        self.header = np.frombuffer(fileblock[:hdr_sz], dtype=Datagram.hdr_dtype)[0]
        self.datagram_size = self.header[3]
        self.subpack = None
        self.decoded = False
        if self.header[1] == 2:
            self.valid = True
        else:
            self.valid = False
        self.datablock = fileblock[hdr_sz:-4]
        self.datablockheader = fileblock[:hdr_sz]
        self.datablockfooter = fileblock[-4:]
        self.checksum = np.frombuffer(fileblock[-4:], dtype=np.uint32, count=1)[0]
        self.dtype = self.header[12]
        self.time = None
        try:
            self.maketime()
        except ValueError:
            pass

    @property
    def datagram_start(self):
        return self.start_file_pointer

    @property
    def datagram_end(self):
        return self.start_file_pointer + self.datagram_size

    def get_datablock(self):
        bytestring = self.header.tobytes() + self.subpack.get_datablock() + self.checksum.tobytes()
        return bytestring

    def decode(self):
        """Calls the correct class to read the data part of the data frame"""
        if self.dtype == 7000:
            self.subpack = Data7000(self.datablock, self.time)
        elif self.dtype == 7001:
            self.subpack = Data7001(self.datablock, self.time)
        elif self.dtype == 7004:
            self.subpack = Data7004(self.datablock, self.time)
        # elif self.datatype == 7006:
        #     datablock = self.infile.read(self.datasize)
        #     self.subpack = Data7006(datablock)
        # elif self.datatype == 7007:
        #     self.subpack = Data7007(self.infile)
        # elif self.datatype == 7008:
        #     datablock = self.infile.read(self.datasize)
        #     self.subpack = Data7008(datablock)
        # elif self.datatype == 7010:
        #     self.subpack = Data7010(self.infile)
        # elif self.datatype == 7017:
        #     datablock = self.infile.read(self.datasize)
        #     self.subpack = Data7017(datablock)
        # elif self.datatype == 7018:
        #     datablock = self.infile.read(self.datasize)
        #     self.subpack = Data7018(datablock, self.header[13], self.header[6])
        # elif self.datatype == 7027:
        #     datablock = self.infile.read(self.datasize)
        #     self.subpack = Data7027(datablock)
        # elif self.datatype == 7028:
        #     self.subpack = Data7028(self.infile)
        # elif self.datatype == 7038:
        #     datablock = self.infile.read(self.datasize)
        #     self.subpack = Data7038(datablock)
        # elif self.datatype == 7041:
        #     self.subpack = Data7041(self.infile)
        # elif self.datatype == 7058:
        #     self.subpack = Data7058(self.infile)
        elif self.dtype == 7200:
            self.subpack = Data7200(self.datablock, self.time)
        # elif self.datatype == 7503:
        #     self.subpack = Data7503(self.infile)
        # elif self.datatype == 1003:
        #     self.subpack = Data1003(self.infile)
        # elif self.datatype == 1012:
        #     self.subpack = Data1012(self.infile)
        # elif self.datatype == 1013:
        #     self.subpack = Data1013(self.infile)
        else:
            raise NotImplementedError("Data record " + str(self.dtype) + " decoding is not yet supported.")
        self.decoded = True

    def maketime(self):
        """
        Parse the Reson 7KTIME convention and return utc seconds
        """
        year, julian_day, seconds, hours, minutes = self.header[6], self.header[7], self.header[8], self.header[9], self.header[10]
        temp_string = str(year).zfill(4) + ',' + str(julian_day).zfill(3) + ',' + str(hours).zfill(2) + ',' + str(minutes).zfill(2)
        tdata = datetime.strptime(temp_string, '%Y,%j,%H,%M')
        tdata = tdata.replace(tzinfo=timezone.utc)
        tdata = tdata + timedelta(microseconds=int(seconds * 1000000))
        self.time = tdata.timestamp()

    def gettime(self):
        """
        Calls the method "maketime" if needed and returns the POSIX time stamp.
        """
        if self.time is None:
            self.maketime()
        return self.time

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n, name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))


class BaseMeta(type):
    """metaclass to read the "hdr_dtype" attribute and convert it into usable attribute names"""

    def __new__(cls, name, bases, classdict):
        if 'hdr_dtype' in classdict:
            # map the dtype names to something python can use as a variable name
            classdict['_data_keys'] = {}
            for field in classdict['hdr_dtype'].names:
                nfield = field.replace(" ", "_").replace("/", "_").replace("(", "").replace("}", "").replace("#", "Num")
                if nfield in classdict['_data_keys']:
                    # print "Duplicate field found -- %s in class %s" % (nfield, name)
                    i = 0
                    orig_field = nfield
                    while nfield in classdict['_data_keys']:
                        i += 1
                        nfield = "%s%02d" % (orig_field, i)
                classdict['_data_keys'][nfield] = field
            # compute the raw size of the data for reading/writing to disk
            if "raw_dtype" in classdict:
                classdict['hdr_sz'] = classdict['raw_dtype'].itemsize
            else:
                classdict['hdr_sz'] = classdict['hdr_dtype'].itemsize

        return type.__new__(cls, name, bases, classdict)


class BaseData(object, metaclass=BaseMeta):
    """
    Note: By deriving classes from "BaseData" the reading of data via numpy into
    an attribute named "header" is automatically done.  It is a numpy record array.
    The names are in the hdr_type attribute from this class but also can be used
    directly by their names also.  Further the data will know how to print itself in
    string form and make a rudimentary plot (if it's based on BasePlottableData).

    Units conversions can also be specified and will be applied in the BaseData.

    To get this functionality follow these steps
    (Data49 class is a pretty clean example, Data65 is more complex)

    1) supply a "hdr_dtype" attribute that is a numpy dtype with record names like examples below

    2) optionally supply a "conversions" dictionary attribute with the names of the numpy fields
       and a multiplicative constant = {'TiltTx': 0.01, 'CenterFrequency': 10}

    3) IF the raw data is not in types that you want then supply a "raw_data" decription also,
       notice in the sample Data002 we are reading PingRate here as a short int "H"
       but the hdr_dtype will cause it to be converted to a float "f"

    4) IF you need to do advanced processing on some data (change units etc),
       override the __init__ and get_datablock, again shown in Data003

    For example:
    # this makes the simplest case, data format is already what we want
    class Data001(BaseData):
         hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'), ('PingRate',"f")])

    # This example will convert the PingRate from short int "H" into float "f" auto-magically
    class Data002(BaseData):
         hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'), ('PingRate',"f")])
         raw_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'), ('PingRate',"H")])

    # This example will convert the PingRate from short int "H" into float "f" auto-magically
    # but also convert the units from hundreths as the integer to a float.
    # -- remember that super(Data003, self) is calling the BaseData class functions:
    class Data003(BaseData):
         hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'), ('PingRate',"f")])
         raw_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'), ('PingRate',"H")])
         conversions = {'PingRate': 0.01} #ping rate was in integer hundreths
         def __init__(self, datablock, byteswap=False):
            super(Data003, self).__init__(datablock, byteswap=byteswap)
            # the conversions declared above has the effect of -- self.header['PingRate'] *= 0.01
            # you can still modify values here if need be -- addition or linear
            self.header['SystemSerialNum'] += 5
         def get_datablock(self, data=None):
            # Must convert the units back first then create the buffer
            tmp_header = self.header.copy()  # don't modify our in-memory data so make a copy first
            self.header['SystemSerialNum'] -= 5  # convert the serial number back that was manually implemented
            # ping rate will be automatically converted in the BaseData implementation
            return super(Data003, self).get_datablock(tmp_header)


    # e.g. if you create an instance of one of these three data classes like:
    mydata = DataXXX(datablock)

    # then the following would work the same:
    mydata.header['PingRate']
    mydata.header[2]
    mydata.PingRate

    # You get basic string output like these
    str(mydata)
    mydata.get_display_string()
    print(mydata)
    mydata.plot() # works if based on BasePlottableData (arrays of data -- not just single headers)
    mydata.display()  # this would also make a matplotlib plot if derived from BasePlottableData

    # Data can be exported using the get_datablock function too.
    new_datablock = mydata.get_datablock()
    """
    conversions = {}

    def __init__(self, datablock, byteswap=False, read_limit=1):
        """This gets the format for each block type and then reads the block
        read_limit is used to determine how much data is read, like a slice index.
          # By default it will read one record and read it as a single instance of the datatype (everything else will be like slices and be an array)
          [0] -- just the first record and as a single instance (easier indexing)
          # a positive integer specifies how many records it will try to read.
          [:2] -- first two records
          Zero or None will read all records.
          [:] -- read all records available
          A negative integer will read that many less than the number of records available.
          [:-1] -- reads all but the last record
        """
        try:
            raw_dtype = self.raw_dtype
        except AttributeError:
            raw_dtype = self.hdr_dtype
        if read_limit is None:
            read_limit = 0
        if read_limit > 0:
            num_packets = read_limit
        else:
            num_packets = int(len(datablock) / self.hdr_sz) - read_limit
        read_sz = self.hdr_sz * num_packets

        tmp_header = np.frombuffer(datablock[:read_sz], dtype=raw_dtype)

        if read_limit == 1:  # converts from an array to single instance of the data (special case)
            tmp_header = tmp_header[0]
        self.header = tmp_header.astype(self.hdr_dtype)
        self._convert()

    def _convert(self):
        if self.conversions:
            for k, v in list(self.conversions.items()):
                self.header[k] *= v

    def _revert(self, data):
        if self.conversions:
            data = data.copy()
            for k, v in list(self.conversions.items()):
                data[k] /= v
        return data

    def get_datablock(self, data=None):
        """data is either the data to convert into a buffer string or None in which case the default data is used.
        You would pass in a different data set from a derived class if there is units translation or something that
        must be done first
        """
        if data is None:
            data = self.header
        data = self._revert(data)
        try:
            raw_dtype = self.raw_dtype
        except AttributeError:
            raw_dtype = self.hdr_dtype
        tmp = data.astype(raw_dtype)
        datablock = tmp.tobytes()  # I believe this is what this should look like in Python3
        return datablock

    def get_display_string(self):
        """ Displays contents of the header to the command window. """
        result = ""
        for n, name in enumerate(self.header.dtype.names):
            result += name + ' : ' + str(self.header[name]) + "\n"
        return result

    def display(self):
        print(self.__repr__())

    def __repr__(self):
        return self.get_display_string()

    def __dir__(self):
        """Custom return of attributes since we have a custom getattr function that adds data members"""
        s = list(self.__dict__.keys())
        s.extend(list(self._data_keys.keys()))
        s.extend(dir(self.__class__))
        ns = sorted([v for v in s if v[0] != "_"])
        return ns

    def __getattr__(self, key):  # Get the value from the underlying subfield (perform any conversion necessary)
        try:
            ky2 = self._data_keys[key]  # try to access the subfield
            return self.header[ky2]
        except:
            raise AttributeError(key + " not in " + str(self.__class__))

    def __setattr__(self, key, value):  # Get the value from the underlying subfield (perform any conversion necessary)
        try:
            ky2 = self._data_keys[key]  # try to access the subfield
        except:
            super(BaseData, self).__setattr__(key, value)
        else:
            self.header[ky2] = value


class BasePlottableData(BaseData):
    def display(self):
        super(BasePlottableData, self).display()
        self.plot()

    def plot(self):
        fig, ax = plt.subplots(len(self.header.dtype.names), 1)
        for n, a in enumerate(ax):
            name = self.header.dtype.names[n]
            a.plot(self.header[name])
            a.set_title(name)
            a.set_xlim((0, len(self.header[name])))
            # a.set_xlabel('index')


class Data7000(BaseData):
    """
    Sonar Settings datagram
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultiPingSequence', 'u2'), ('Frequency', 'f4'),
                          ('SampleRate', 'f4'), ('ReceiverBandwidth', 'f4'), ('TXPulseWidth', 'f4'),
                          ('TXPulseTypeID', 'u4'), ('TXPulseEnvelope', 'u4'), ('TXPulseEnvelopeParameter', 'f4'),
                          ('TXPulseMode', 'u2'), ('TXPulseReserved', 'u2'), ('MaxPingRate', 'f4'), ('PingPeriod', 'f4'),
                          ('RangeSelection', 'f4'), ('PowerSelection', 'f4'), ('GainSelection', 'f4'), ('ControlFlags', 'u4'),
                          ('ProjectorIdentifier', 'u4'), ('ProjectorBeamSteeringAngleVertical', 'f4'),
                          ('ProjectorBeamSteeringAngleHorizontal', 'f4'), ('ProjectorBeamWidthVertical', 'f4'),
                          ('ProjectorBeamWidthHorizontal', 'f4'), ('ProjectorBeamFocalPoint', 'f4'),
                          ('ProjectorBeamWeightingWindowType', 'u4'), ('ProjectorBeamWeightingWindowParameter', 'f4'),
                          ('TransmitFlags', 'u4'), ('HydrophoneIdentifier', 'u4'), ('ReceiveBeamWeightingWindow', 'u4'),
                          ('ReceiveBeamWeightingParamter', 'f4'), ('ReceiveFlags', 'u4'), ('ReceiveBeamWidth', 'f4'),
                          ('BottomDetectionFilterMinRange', 'f4'), ('BottomDetectionFilterMaxRange', 'f4'),
                          ('BottomDetectionFilterMinDepth', 'f4'), ('BottomDetectionFilterMaxDepth', 'f4'),
                          ('Absorption', 'f4'), ('SoundVelocity', 'f4'), ('Spreading', 'f4'), ('ReservedFlag', 'u2')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7000, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime


class Data7001(BaseData):
    """
    Configuration record, generated on system startup, does not change during operation
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('NumberOfDevices', 'u4')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7001, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.device_header = np.dtype([('DeviceIdentifier', 'u4'), ('DeviceDescription', 'S60'), ('DeviceAlphaDataCard', 'u4'),
                                       ('DeviceSerialNumber', 'u8'), ('DeviceInfoLength', 'u4')])
        self.devices = []
        self.read_data(datablock[self.hdr_sz:])

    def read_data(self, datablock):
        numdevices = self.header[1]
        data_sz = self.device_header.itemsize
        datapointer = 0
        for i in range(numdevices):
            device_data = list(np.frombuffer(datablock[datapointer:datapointer + data_sz], dtype=self.device_header)[0])
            datapointer += data_sz
            variable_length = device_data[-1]
            info_data = list(np.frombuffer(datablock[datapointer: datapointer + variable_length], np.dtype([('DeviceInfo', f'S{variable_length}')]))[0])
            datapointer += data_sz
            device_data += info_data
            self.devices.append(device_data)

    def display(self):
        super(Data7001, self).display()
        for ddata in self.devices:
            for cnt, key in enumerate(self.device_header.names):
                print(f'{key} : {ddata[cnt]}')
            print(f'DeviceInfo : {ddata[-1]}')


class Data7002(BaseData):
    """
    Match Filter, contains sonar recieve match filter settings
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('Operation', 'u4'), ('StartFrequency', 'f4'),
                          ('StopFrequency', 'f4'), ('WindowType', 'u4'), ('ShadingValue', 'f4'),
                          ('EffectivePulseWidth', 'f4'), ('Reserved', '13u4')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7002, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime


class Data7004BeamsNew(BaseData):
    """
    The by-beam variables within 7004
    Expects you to update hdr_dtype from the Data7004 before initialization
    """
    hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', 'f'), ('BeamHorizontalDirectionAngle', 'f'),
                          ('BeamWidthAlongTrack', 'f'), ('BeamWidthAcrossTrack', 'f'), ('TxDelay', 'f')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data7004BeamsNew, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)


class Data7004BeamsOld(BaseData):
    """
    The by-beam variables within 7004
    Expects you to update hdr_dtype from the Data7004 before initialization
    """
    hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', 'f'), ('BeamHorizontalDirectionAngle', 'f'),
                          ('BeamWidthAlongTrack', 'f'), ('BeamWidthAcrossTrack', 'f')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data7004BeamsOld, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)


class Data7004(BasePlottableData):
    """
    Beam Geometry
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('NumberOfBeams', 'u4')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        super(Data7004, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.data = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        numbeams = self.header[1]
        if len(datablock) == numbeams * 4 * 4:
            dgram = Data7004BeamsOld
            dgram.hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', f'{numbeams}f'),
                                        ('BeamHorizontalDirectionAngle', f'{numbeams}f'),
                                        ('BeamWidthAlongTrack', f'{numbeams}f'),
                                        ('BeamWidthAcrossTrack', f'{numbeams}f')])
        elif len(datablock) == numbeams * 5 * 4:
            dgram = Data7004BeamsNew
            dgram.hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', f'{numbeams}f'),
                                        ('BeamHorizontalDirectionAngle', f'{numbeams}f'),
                                        ('BeamWidthAlongTrack', f'{numbeams}f'),
                                        ('BeamWidthAcrossTrack', f'{numbeams}f'), ('TxDelay', f'{numbeams}f')])
        else:
            print('Datagram 7004: expected either 4 or 5 variable records, could not determine datagram version')
            return
        dgram.hdr_sz = dgram.hdr_dtype.itemsize
        self.data = dgram(datablock)

    # def plot(self):
    #     """Plots the 7004 record as one plot with four subplots."""
    #     numbeams = self.header[1]
    #     self.fig = plt.figure()
    #     ax1 = self.fig.add_subplot(411, xlim=(0, numbeams), autoscalex_on=False)
    #     ax1.plot(np.rad2deg(self.data[0, :]))
    #     ax1.set_ylabel('Along Track Angle (deg)')
    #     ax1.set_title('Beam Configuration Information')
    #     ax2 = self.fig.add_subplot(412, sharex=ax1, autoscalex_on=False)
    #     ax2.plot(np.rad2deg(self.data[1, :]))
    #     ax2.set_ylabel('Across Track Angle (deg)')
    #     ax3 = self.fig.add_subplot(413, sharex=ax1, autoscalex_on=False)
    #     ax3.plot(np.rad2deg(self.data[2, :]))
    #     ax3.set_ylabel('Along Track Beamwidth (deg)')
    #     ax4 = self.fig.add_subplot(414, sharex=ax1, autoscalex_on=False)
    #     ax4.plot(np.rad2deg(self.data[3, :]))
    #     ax4.set_ylabel('Across Track Beamwidth (deg)')
    #     ax4.set_xlabel('Beam Number')

#
# class Data7006(BasePlottableData):
#     fmt_hdr = '<QIHI2Bf'
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Number of Beams',
#              'Flags',
#              'Sound Velocity Flag',
#              'Sound Velocity')
#
#     def __init__(self, datablock):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7006, self).__init__(datablock)
#         self.datapointer = self.hdr_sz
#         self.read_data(datablock)
#
#     def read_data(self, datablock):
#         self.numbeams = self.header[3]
#         self.fmt_data = '<' + str(self.numbeams) + 'f' + str(self.numbeams) + 'B' + str(3 * self.numbeams) + 'f'
#         self.data_sz = 17 * self.numbeams  # one U8 plus four f32 is 17
#         self.data = np.array(struct.unpack(self.fmt_data, datablock[self.datapointer: self.datapointer + self.data_sz]))
#         self.data.shape = (5, self.numbeams)
#         self.detect = np.zeros((self.numbeams, 3))
#         for i in range(self.numbeams):
#             temp = (int(self.data[1, i]) & 12) / 4  # 12 is the mask to get the bottom detect type
#             # and divide by four to get to those bits
#             if temp == 1:
#                 self.detect[i, :] = [1, 0, 0]
#             elif temp == 2:
#                 self.detect[i, :] = [0, 1, 0]
#             elif temp == 3:
#                 self.detect[i, :] = [0, 0, 1]
#
#     def plot(self):
#         rngplot = plt.scatter(range(self.numbeams), self.data[0].T, c=self.detect, edgecolor=self.detect)
#         plt.xlim((0, self.numbeams))
#         plt.ylim((self.data[0].max(), 0))
#         plt.xlabel('Beam Number')
#         plt.ylabel('Time (s)')
#         plt.draw()
#
#
# class Data7007(BaseData):
#     fmt_hdr = '<QIHf2I8f2H2B'
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Beam Position',
#              'Reserved',
#              'Samples Per Side',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Number of Beams Per Side',
#              'Current Beam Number',
#              'Number of Bytes Per Sample',
#              'Reserved')
#
#     def __init__(self, infile):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7007, self).__init__(infile)
#         self.read_data(infile)
#
#     def read_data(self, infile):
#         self.fmt_data = '<' + str(self.header[5] * self.header[16]) + 'B'
#         self.data_sz = self.header[5] * self.header[16]
#         self.port = np.array(struct.unpack(self.fmt_data, infile.read(self.data_sz)))
#         self.stbd = np.array(struct.unpack(self.fmt_data, infile.read(self.data_sz)))
#
#
# class Data7008:
#     hdr_dtype = np.dtype([('SonarID', 'Q'), ('PingNumber', 'I'), ('Multiping#', 'H'),
#                           ('Beams', 'H'), ('Reserved1', 'H'), ('Samples', 'I'), ('RecordSubsetFlag', 'B'),
#                           ('RowColumnFlag', 'B'), ('Reserved2', 'H'), ('DataSampleSize', 'I')])
#     data_dtype = np.dtype([('Amp', 'H'), ('Phs', 'h')])
#
#     def __init__(self, datablock):
#         """This gets the format for each block type and then reads the block"""
#         self.numbeams = None
#         self.beams = None
#         self.numsnip = None
#         self.mag = None
#         self.phase = None
#         self.iele = None
#         self.qele = None
#         hdr_sz = Data7008.hdr_dtype.itemsize
#         self.header = np.frombuffer(datablock[:hdr_sz], Data7008.hdr_dtype)[0]
#         self.read_data(datablock[hdr_sz:])
#
#     def read_data(self, datablock):
#         """Reading the original snippet message.
#         This is reading the snippet data and is
#         dependant on the information from the
#         header. The steps 1)read each beam
#         snippet size 2)read in the data for each
#         beam, which could consist of magnitude,
#         phase, I&Q, for each beam or element."""
#
#         # define the format string and size for snippet data through bitwise ops
#         # Thanks to Tom Weber and Les Peabody for helping figure this out
#         fmt_flags = self.header['DataSampleSize']
#         magval = 7 & fmt_flags
#         phaseval = (240 & fmt_flags) >> 4
#         iqval = (3840 & fmt_flags) >> 8
#         elementflag = (28672 & fmt_flags) >> 12
#         fmt = []
#         if magval == 2:
#             fmt.append(('Magnitude', 'H'))
#         elif magval == 3:
#             fmt.append(('Magnitude', 'I'))
#         if phaseval == 2:
#             fmt.append(('Phase', 'H'))
#         elif phaseval == 3:
#             fmt.append(('Phase', 'I'))
#         if iqval == 1:
#             fmt.append(('I', 'H'), ('Q', 'H'))
#         elif iqval == 2:
#             fmt.append(('I', 'I'), ('Q', 'I'))
#         snip_fmt = np.dtype(fmt)
#         beam_fmt = np.dtype([('BeamNumber', 'H'), ('FirstSample', 'I'), ('LastSample', 'I')])
#         # read the beam snippet sizes (zones)
#         self.numbeams = self.header['Beams']
#         block_sz = self.numbeams * beam_fmt.itemsize
#         self.beams = np.frombuffer(datablock[:block_sz], beam_fmt)
#         temp = (self.beams['LastSample'] - self.beams['FirstSample']).max() + 1
#         self.numsnip = temp.max()
#         if not (self.numsnip == temp).all():
#             print("Warning: number of snippets is not consistent.")
#
#         # read snippet data as columns for each data type (mag/phase/i/q)
#         snip = np.frombuffer(datablock[block_sz:], snip_fmt)
#         # separate types out to different arrays
#         ordertype = self.header[7]
#         if magval != 0:
#             self.mag = snip['Magnitude'].astype(np.float64)
#             if ordertype == 0:
#                 self.mag.shape = (self.numbeams, self.numsnip)
#                 self.mag = self.mag.transpose()
#             elif ordertype == 1:
#                 self.mag.shape = (self.numsnip, self.numbeams)
#         if phaseval != 0:
#             self.phase = snip['Phase'].astype(np.float64)
#             if self.header[7] == 0:
#                 self.phase.shape = (self.numbeams, self.numsnip)
#                 self.phase = self.phase.transpose()
#             elif self.header[7] == 1:
#                 self.phase.shape = (self.numsnip, self.numbeams)
#         if iqval != 0:
#             self.iele = snip['I'].astype(np.float64)
#             self.qele = snip['Q'].astype(np.float64)
#             if self.header[7] == 0:
#                 self.iele.shape = (self.numbeams, self.numsnip)
#                 self.iele = self.iele.transpose()
#                 self.qele.shape = (self.numbeams, self.numsnip)
#                 self.qele = self.qele.transpose()
#             elif self.header[7] == 1:
#                 self.iele.shape = (self.numsnip, self.numbeams)
#                 self.qele.shape = (self.numsnip, self.numbeams)
#
#     def plot(self):
#         """plot any snippet data collected"""
#         if hasattr(self, 'mag'):
#             # plt.figure()
#             magplot = plt.imshow(20 * np.log10(self.mag), aspect='auto')
#             plt.title('7008 20*log10*Magnitude')
#             plt.xlabel('Beam number')
#             plt.ylabel('Sample number in window')
#         if hasattr(self, 'phase'):
#             plt.figure()
#             phaseplot = plt.imshow(self.phase, aspect='auto')
#             plt.title('7008 Phase')
#             plt.xlabel('Beam number')
#             plt.ylabel('Sample number in window')
#         plt.draw()
#
#     def display(self):
#         for n, name in enumerate(self.header.dtype.names):
#             print(name + ' : ' + str(self.header[n]))
#         print('Size of snippet window: ' + str(self.numsnip))
#         self.plot()
#
#
# class Data7010(BaseData):
#     fmt_hdr = '<QIH2I'
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Samples',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved')
#
#     def __init__(self, infile):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7010, self).__init__(infile)
#         self.read_data(infile)
#
#     def read_data(self, infile):
#         self.fmt_data = '<' + str(self.header[4] - 1) + 'I'
#         self.data_sz = self.header[4] * 4
#         self.data = struct.unpack(self.fmt_data, infile.read(self.data_sz))
#
#
# class Data7017(BasePlottableData):
#     fmt_hdr = '<QIH2IBI6fB2f14I'
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Number of Beams',
#              'Data Block Size',
#              'Detection algorithm',
#              'Flags',
#              'Min Depth',
#              'Max Depth',
#              'Min Range',
#              'Max Range',
#              'Min Nadir Search',
#              'Max Nadir Search',
#              'Automatic Filter Window',
#              'Applied Roll',
#              'Depth Gate Tilt',
#              'Reserved')
#
#     def __init__(self, datablock):
#         """This gets the format for each block type and then reads the block.
#         Format was created from Reson DFD Version 2.2"""
#         super(Data7017, self).__init__(datablock)
#         self.datapointer = self.hdr_sz
#         self.read_data(datablock)
#
#     def read_data(self, datablock):
#         self.numbeams = self.header[3]
#         fmt_base = 'HfI4fIf'
#         if self.numbeams > 0:
#             self.fmt_data = '<' + self.numbeams * fmt_base
#             self.data_sz = struct.calcsize(self.fmt_data)
#             self.data = np.array(
#                 struct.unpack(self.fmt_data, datablock[self.datapointer: self.datapointer + self.data_sz]))
#             self.datapointer += self.data_sz
#             self.data.shape = (self.numbeams, -1)
#             self.detect = np.zeros((self.numbeams, 3))
#             for i in range(self.numbeams):
#                 temp = (int(self.data[i, 3]) & 3)  # 3 is the mask to get the bottom detect type
#                 if temp == 1:
#                     self.detect[i, :] = [1, 0, 0]
#                 elif temp == 2:
#                     self.detect[i, :] = [0, 1, 0]
#                 elif temp == 3:
#                     self.detect[i, :] = [0, 0, 1]
#         else:
#             self.data = None
#             self.detect = None
#
#     def plot(self):
#         if self.data is not None:
#             rngplot = plt.scatter(self.data[:, 0], self.data[:, 1], c=self.detect, edgecolor=self.detect)
#             plt.xlim((0, self.numbeams))
#             plt.ylim((self.data[1].max(), 0))
#             plt.xlabel('Beam Number')
#             plt.ylabel('?')
#             plt.draw()
#         else:
#             print("No beams in record.")
#
#
# class Data7018:
#     """This record had two versions, one for the 7111 and one for the 7125.
#     In the beginning of 2011 the 7111 was brought in alignment with the 7125
#     version."""
#     hdr_dtype = np.dtype([('SonarID', 'Q'), ('PingNumber', 'I'), ('Multiping#', 'H'),
#                           ('Beams', 'H'), ('Samples', 'I'), ('Reserved', '8I')])
#     data_dtype = np.dtype([('Amp', 'H'), ('Phs', 'h')])
#
#     def __init__(self, datablock, sonar_type, year):
#         self.mag = None
#         self.phase = None
#         if sonar_type == 7111 and year < 2011:
#             print("This is old 7111 data and is no longer supported by this module.")
#         else:
#             hdr_sz = Data7018.hdr_dtype.itemsize
#             self.header = np.frombuffer(datablock[:hdr_sz], dtype=Data7018.hdr_dtype)[0]
#             self.read_data(datablock[hdr_sz:])
#
#     def read_data(self, subdatablock):
#         """
#         Read the data into a numpy array.
#         """
#         beams = self.header['Beams']
#         data = np.frombuffer(subdatablock, dtype=Data7018.data_dtype)
#         self.mag = data['Amp'].astype('f')
#         self.mag.shape = (-1, beams)
#         self.phase = data['Phs'].astype('f')
#         self.phase.shape = (-1, beams)
#
#     def plot(self):
#         """plot water column data"""
#         plt.subplot(1, 2, 1)
#         magplot = plt.imshow(20 * np.log10(self.mag), aspect='auto')
#         plt.title('7018 Magnitude')
#         plt.xlabel('Beam number')
#         plt.ylabel('Sample number')
#         # plt.colorbar()
#         plt.subplot(1, 2, 2)
#         # plt.figure()
#         phaseplot = plt.imshow(self.phase, aspect='auto')
#         plt.title('7018 Phase')
#         plt.xlabel('Beam number')
#         plt.ylabel('Sample number')
#         # plt.colorbar()
#         plt.suptitle(('Ping number ' + str(self.header[1])))
#         plt.draw()
#
#     def display(self):
#         for n, name in enumerate(self.header.dtype.names):
#             print(name + ' : ' + str(self.header[n]))
#         self.plot()
#
#
# class Data7027(BasePlottableData):
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Number of Beams',
#              'Data Field Size',
#              'Detection algorithm',
#              'Flags',
#              'Sampling Rate',
#              'Tx angle',
#              'Reserved')
#     fmt_hdr = '<QIH2IBI2f16I'
#
#     def __init__(self, datablock):
#         """This gets the format for each block type and then reads the block.
#         Format was created from Reson DFD Version 2.2"""
#         super(Data7027, self).__init__(datablock)
#         self.datapointer = self.hdr_sz
#         self.read_data(datablock)
#
#     def read_data(self, datablock):
#         self.numbeams = self.header[3]
#         datafieldsize = self.header[4]
#         if datafieldsize == 22:
#             fmt_base = 'H2f2If'
#         elif datafieldsize == 26:
#             fmt_base = 'H2f2I2f'
#         if self.numbeams > 0:
#             self.fmt_data = '<' + self.numbeams * fmt_base
#             self.data_sz = struct.calcsize(self.fmt_data)
#             self.data = np.array(
#                 struct.unpack(self.fmt_data, datablock[self.datapointer: self.datapointer + self.data_sz]))
#             self.datapointer += self.data_sz
#             self.data.shape = (self.numbeams, -1)
#             self.detect = np.zeros((self.numbeams, 3))
#             for i in range(self.numbeams):
#                 temp = (int(self.data[i, 3]) & 3)  # 3 is the mask to get the bottom detect type
#                 if temp == 1:
#                     self.detect[i, :] = [1, 0, 0]
#                 elif temp == 2:
#                     self.detect[i, :] = [0, 1, 0]
#                 elif temp == 3:
#                     self.detect[i, :] = [0, 0, 1]
#         else:
#             self.data = None
#             self.detect = None
#
#     def plot(self):
#         if self.data is not None:
#             rngplot = plt.scatter(self.data[:, 0], self.data[:, 1], c=self.detect, edgecolor=self.detect)
#             plt.xlim((0, self.numbeams))
#             plt.ylim((self.data[1].max(), 0))
#             plt.xlabel('Beam Number')
#             plt.ylabel('Sample Number')
#             plt.draw()
#         else:
#             print("No beams in record.")
#
#
# class Data7028(BasePlottableData):
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Number of Beams',
#              'Error flag',
#              'Control flags',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved')
#     fmt_hdr = '<QI2H2B7I'
#
#     def __init__(self, infile):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7028, self).__init__(infile)
#         self.fmt_descriptor = '<H3I'
#         self.descriptor_sz = struct.calcsize(self.fmt_descriptor)
#         self.read_data(infile)
#
#     def read_data(self, infile):
#         self.numpoints = self.header[3]
#         if self.header[4] == 0:
#             self.descriptor = np.zeros((self.numpoints, 4))
#             for beam in range(self.numpoints):
#                 self.descriptor[beam, :] = struct.unpack(self.fmt_descriptor, infile.read(self.descriptor_sz))
#             self.beamwindow = self.descriptor[:, 3] - self.descriptor[:, 1] + 1
#             self.maxbeam = int(self.descriptor[:, 0].max()) + 1
#             self.maxwindow = self.beamwindow.max()
#             self.snippets = np.zeros((self.maxbeam, self.maxwindow))
#             for beam in range(self.numpoints):
#                 self.fmt_data = '<' + str(int(self.beamwindow[beam])) + 'H'
#                 self.data_sz = struct.calcsize(self.fmt_data)
#                 self.startoffset = int((self.maxwindow - self.beamwindow[beam]) / 2)
#                 self.snippets[int(self.descriptor[beam, 0]), self.startoffset: self.startoffset + self.beamwindow[beam]] = struct.unpack(self.fmt_data, infile.read(self.data_sz))
#         else:
#             # Error flag indicates no data.
#             self.beamwindow = None
#             self.maxbeam = None
#             self.maxwindow = None
#             self.snippets = None
#
#     def plot(self):
#         if self.snippets is not None:
#             plt.figure()
#             self.aspect = float(self.numpoints) / self.beamwindow.max()
#             magplot = plt.imshow(20 * np.log10(self.snippets.T), aspect=self.aspect)
#             plt.title('7028 20*log10*Magnitude')
#             plt.xlabel('Beam number')
#             plt.ylabel('Sample number in window')
#             plt.draw()
#         else:
#             print("No snippets to plot")
#
#
# class Data7038(BasePlottableData):
#     fmt_hdr = '<QI2HIH2IH7I'
#     label = ('SonarID',
#              'Ping Number',
#              'Reserved',
#              'Elements',
#              'Samples',
#              'Element Reduction',
#              'Start Sample',
#              'Stop Sample',
#              'Sample Type',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved')
#
#     def __init__(self, datablock):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7038, self).__init__(datablock)
#         self.datapointer = self.hdr_sz
#         self.read_data(datablock)
#
#     def read_data(self, datablock):
#         self.numelements = self.header[5]
#         self.numsamples = self.header[7] - self.header[6] + 1  # plus one to include last sample?
#         self.sample_sz = self.header[8]
#
#         self.fmt_elements = '<' + str(self.numelements) + 'H'
#         endread = struct.calcsize(self.fmt_elements) + self.datapointer
#         self.elements = struct.unpack(self.fmt_elements, datablock[self.datapointer:endread])
#         self.datapointer = endread
#
#         if self.sample_sz == 8:
#             self.sample_fmt = 'B'
#         elif self.sample_sz == 12:
#             self.sample_fmt = 'H'
#         elif self.sample_sz == 16:
#             self.sample_fmt = 'H'
#         elif self.sample_sz == 32:
#             self.sample_fmt = 'I'
#         else:
#             self.sample_fmt = 'unknown'
#         if self.sample_fmt != 'unknown':
#             self.fmt_data = '<' + str(2 * self.numsamples * self.numelements) + self.sample_fmt
#             endread = struct.calcsize(self.fmt_data) + self.datapointer
#             self.data = np.array(struct.unpack(self.fmt_data, datablock[self.datapointer:endread]))
#             self.datapointer = endread
#             self.r = np.zeros(self.numsamples * self.numelements, complex)
#             self.phase = np.zeros(self.numsamples * self.numelements)
#             self.data.shape = (-1, 2)
#             for c in range(len(self.data)):
#                 self.r[c] = complex(self.data[c, 0], self.data[c, 1])
#                 self.phase[c] = math.atan2(self.data[c, 1], self.data[c, 0])
#         else:
#             print('unknown sample size to unpack')
#
#     def plot(self):
#         # reshape arrays for plotting
#         self.phase.shape = (self.numsamples, self.numelements)
#         self.r.shape = (self.numsamples, self.numelements)
#         # for plot 1&2
#         self.amp = abs(self.r)
#         # for plot 3, take fft...
#         ampfft = abs(np.fft.fft(self.r))
#         # ...and swap the sides to center the 0 freq
#         ampfft2 = np.zeros(ampfft.shape)
#         ampfft2[:, self.numelements / 2:] = ampfft[:, :self.numelements / 2]
#         ampfft2[:, :self.numelements / 2] = ampfft[:, self.numelements / 2:]
#
#         f = plt.figure()
#         # f.text(0.5, 0.975, 'From file ' + self.infilename,horizontalalignment = 'center', verticalalignment = 'top')
#         plt.subplot(2, 2, 1)
#         plt.imshow(self.amp, aspect='auto')
#         plt.title('Element Amplitude')
#         plt.ylabel('Samples')
#
#         plt.subplot(2, 2, 2)
#         plt.imshow(20 * np.log10(self.amp), aspect='auto')
#         plt.title('20*log10(Element Amplitude)')
#         plt.ylabel('Samples')
#
#         plt.subplot(2, 2, 3)
#         plt.imshow(20 * np.log10(ampfft2), aspect='auto')
#         plt.title('20*log10(fft(Element Amplitude)')
#         plt.ylabel('Samples')
#         plt.xlabel('Element Number')
#
#         plt.subplot(2, 2, 4)
#         plt.imshow(self.phase, aspect='auto')
#         plt.title('Element Phase')
#         plt.ylabel('Samples')
#         plt.xlabel('Element Number')
#
#         plt.draw()
#
#
# class Data7041(BasePlottableData):
#     """This record is the compressed beam formed magnitude data as of 8/8/2011."""
#     fmt_hdr = '<QI3Hf4I'
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Number of Beams',
#              'Flags',
#              'Sample Rate',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved')
#
#     def __init__(self, infile):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7041, self).__init__(infile)
#         self.read_data(infile)
#
#     def read_data(self, infile):
#         self.numbeams = self.header[3]
#         self.flags = self.header[4]
#         if (self.flags & 1) == 1:
#             self.dtype = 'H'
#         else:
#             self.dtype = 'B'
#         if (self.flags & 128) == 128:
#             self.beamid = 'f'
#         else:
#             self.beamid = 'H'
#         self.data_fmt = '<' + self.beamid + 'I'
#         self.data_sz = struct.calcsize(self.data_fmt)
#         tempdata = []
#         maxlen = 0
#         for i in range(self.numbeams):
#             self.beaminfo = struct.unpack(self.data_fmt, infile.read(self.data_sz))
#             if self.beaminfo[1] > maxlen:
#                 maxlen = self.beaminfo[1]
#             self.data2_fmt = '<' + str(self.beaminfo[1]) + self.dtype
#             self.data2_sz = struct.calcsize(self.data2_fmt)
#             tempdata.append(struct.unpack(self.data2_fmt, infile.read(self.data2_sz)))
#         self.beamdata = np.zeros((self.numbeams, maxlen))
#         for i, beam in enumerate(tempdata):
#             self.beamdata[i, :len(beam)] = beam
#         self.beamdata = self.beamdata.T
#
#     def plot(self):
#         """plot water column data"""
#         fig = plt.figure()
#         ax = fig.add_subplot(111, aspect='equal')
#         magplot = plt.imshow(20 * np.log10(self.beamdata), aspect='auto')
#         plt.title('7041 record - 20 * log10(Compressed Magnitude)')
#         plt.xlabel('Beam number')
#         plt.ylabel('Sample number')
#         plt.colorbar()
#         plt.draw()
#
#
# class Data7058(BasePlottableData):
#     fmt_hdr = '<QI2HBI7I'
#     label = ('SonarID',
#              'Ping Number',
#              'Multi-ping Sequence',
#              'Number of Beams',
#              'Error flag',
#              'Control flags',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved')
#
#     def __init__(self, infile):
#         """This gets the format for each block type and then reads the block"""
#         super(Data7058, self).__init__(infile)
#         self.fmt_descriptor = '<H3I'
#         self.descriptor_sz = struct.calcsize(self.fmt_descriptor)
#         self.read_data(infile)
#
#     def read_data(self, infile):
#         self.numpoints = self.header[3]
#         if self.header[4] == 0:
#             self.descriptor = np.zeros((self.numpoints, 4))
#             for beam in range(self.numpoints):
#                 self.descriptor[beam, :] = struct.unpack(self.fmt_descriptor, infile.read(self.descriptor_sz))
#             self.beamwindow = self.descriptor[:, 3] - self.descriptor[:, 1] + 1
#             self.maxbeam = int(self.descriptor[:, 0].max()) + 1
#             self.maxwindow = self.beamwindow.max()
#             self.snippets = np.zeros((self.maxbeam, self.maxwindow))
#             for beam in range(self.numpoints):
#                 self.fmt_data = '<' + str(int(self.beamwindow[beam])) + 'f'
#                 self.data_sz = struct.calcsize(self.fmt_data)
#                 self.startoffset = int((self.maxwindow - self.beamwindow[beam]) / 2)
#                 self.snippets[int(self.descriptor[beam, 0]), self.startoffset: self.startoffset + self.beamwindow[beam]] = struct.unpack(self.fmt_data, infile.read(self.data_sz))
#         elif self.header[4] == 1:
#             print('7058 "No calibration" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 2:
#             print('7058 "TVG Read error" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 3:
#             print('7058 "CTD not available" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 4:
#             print('7058 "Invalide sonar geometry" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 5:
#             print('7058 "Invalid sonar specifications" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 6:
#             print('7058 "Bottom detection failed" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 7:
#             print('7058 "No power" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 8:
#             print('7058 "No gain" error at ping ' + str(self.header[1]))
#         elif self.header[4] == 255:
#             print('7058 "Missing c7k file" error at ping ' + str(self.header[1]))
#         else:
#             print('7058 error flag at ping ' + str(self.header[1]))
#
#     def plot(self):
#         plt.figure()
#         self.aspect = float(self.numpoints) / self.beamwindow.max()
#         magplot = plt.imshow(20 * np.log10(self.snippets.T), aspect=self.aspect)
#         plt.title('7028 20*log10*Magnitude')
#         plt.xlabel('Beam number')
#         plt.ylabel('Sample number in window')
#         plt.draw()
#
#
class Data7200(BaseData):
    """
    File header, always the first record of a 7k file
    """
    hdr_dtype = np.dtype([('FileIdentifier', '2u8'), ('VersionNumber', 'u2'), ('Reserved', 'u2'), ('SessionIdentifier', '2u8'),
                          ('RecordDataSize', 'u4'), ('NumberOfDevices', 'u4'), ('RecordingName', 'S64'),
                          ('RecordingProgramVersion', 'S16'), ('UserDefinedName', 'S64'), ('Notes', 'S128')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        super(Data7200, self).__init__(datablock, byteswap=byteswap)
        # the strings are 'null terminated' so strip the bytes from those messages
        self.header[6] = self.header[6].rstrip(b'\xff').rstrip(b'\x00').decode()
        self.header[7] = self.header[6].rstrip(b'\xff').rstrip(b'\x00').decode()
        self.header[8] = self.header[6].rstrip(b'\xff').rstrip(b'\x00').decode()
        self.header[9] = self.header[6].rstrip(b'\xff').rstrip(b'\x00').decode()

        self.time = POSIXtime
        self.record_data = []
        self.record_data_header = np.dtype([('DeviceIdentifier', 'u4'), ('SystemEnumerator', 'u2')])
        self.optional_data = []
        self.optional_data_header = np.dtype([('OptionalSize', 'u4'), ('OptionalOffset', 'u8')])

        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        numdevices = self.header[5]
        has_record_data = self.header[4] != 0
        datapointer = 0
        if has_record_data and datablock:
            data_sz = self.record_data_header.itemsize
            for i in range(numdevices):
                data = list(np.frombuffer(datablock[datapointer:datapointer + data_sz], dtype=self.record_data_header)[0])
                datapointer += data_sz
                self.record_data.append(data)
            if datablock[datapointer:]:
                data_sz = self.optional_data_header.itemsize
                data = list(np.frombuffer(datablock[datapointer:datapointer + data_sz], dtype=self.optional_data_header)[0])
                datapointer += data_sz
                self.optional_data.append(data)
#
#
# class Data7503(BaseData):
#     """Up through version 2.0 of the data format definition document this
#     record is reported incorrectly.  There is no multiping sequence."""
#     fmt_hdr = '<QI4f2IfI5f2I5fIf3IfI7fH6fI2H2f2dH2IfIf4B7I'
#     label = ('Sonar ID',
#              'Ping Number',
#              'Frequency',
#              'Sample rate',
#              'Receiver bandwidth',
#              'Tx pulse width',
#              'Tx pulse type identifier',
#              'Tx pulse envelope identifier',
#              'Tx pulse envelope parameter',
#              'Tx pulse reserved',
#              'Max ping rate',
#              'Ping period',
#              'Range selection',
#              'Power selection',
#              'Gain selection',
#              'Control flags',
#              'Projector ID',
#              'Projector beam steering angle vertical',
#              'Projector beam steering angle horizontal',
#              'Projector beam -3dB beam width vertical',
#              'Projector beam -3dB beam width horizontal',
#              'Projector beam focal point',
#              'Projector beam weighting window type',
#              'Projector beam weighting window parameter',
#              'Transmit flags',
#              'Hydrophone ID',
#              'Receive beam weighting window',
#              'Receive beam weighting parameter',
#              'Receive flags',
#              'Bottom detection filter min range',
#              'Bottom detection filter max range',
#              'Bottom detection filter min depth',
#              'Bottom detection filter max depth',
#              'Absorption',
#              'Sound Velocity',
#              'Spreading',
#              'Reserved',
#              'Tx array position offset X',
#              'Tx array position offset Y',
#              'Tx array position offset Z',
#              'Head tilt X',
#              'Head tilt Y',
#              'Head tilt Z',
#              'Ping state',
#              'Equiangle/Equidistant Mode',
#              '7kCenter mode',
#              'Adaptive gate bottom filter min depth',
#              'Adaptive gate bottom filter max depth',
#              'Trigger out width',
#              'Trigger out offset',
#              '81xx series projector Selection',
#              'Reserved',
#              'Reserved',
#              '81xx series alternate gain',
#              'Reserved',
#              'Coverage angle',
#              'Coverage mode',
#              'Quality filter flags',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved',
#              'Reserved')
#
#
# class Data1003(BaseData):
#     label = ('DatumID',
#              'Latency',
#              'Northing (Lat)',
#              'Easting (Lon)',
#              'Height (m)',
#              'Position Type',
#              'UTM Zone',
#              'Quality Flag',
#              'Positioning Method',
#              'Positioning Method (cont)')
#     fmt_hdr = '<If3d5B'
#
#
# class Data1012(BaseData):
#     label = ('Roll', 'Pitch', 'Heave')
#     fmt_hdr = '<3f'
#
#
# class Data1013(BaseData):
#     label = ('Heading')
#     fmt_hdr = '<f'


class MapPack:
    """Acts as a map for the location of each of the packets
    for a particular packet type for the file in question"""

    def __init__(self):
        """Makes the first entry in the array"""
        self.packdir = {}
        self.sizedir = {}

    def add(self, type, location=0, time=0, ping=0, size=0):
        """Adds the location, time and ping to the tuple for the value type"""
        self.type = type
        self.store = [location, time, ping]
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
            tempindx = temp[:, 1].argsort()
            self.packdir[key] = temp[tempindx, :]

    def find(self, valtype, val):
        """Finds the desired packet either by time stamp or by ping number"""
        pass

    def printmap(self):
        keys = []
        totalsize = 0
        for i, v in self.packdir.items():
            keys.append((i, len(v)))
            totalsize += self.sizedir[i]
        keys.sort()
        for key in keys:
            percent = 10000 * self.sizedir[str(key[0])] / totalsize
            print('message ' + str(key[0]) + ' has ' + str(key[1]) + ' packets and ' + str(0.01 * percent) + '% of file')

    def plotmap(self):
        """
        Plots to location of each of the packets in the file.
        """
        keys = list(self.packdir.keys())
        keys.sort()
        plt.figure()
        for key in keys:
            plt.plot(self.packdir[key][:, 0])
        plt.xlabel('Packet Number')
        plt.ylabel('Location in file')
        plt.legend(keys, loc='lower right')

    def save(self, outfilename):
        self.outfile = open(outfilename + '.prr', 'wb')
        pickle.dump(self.packdir, self.outfile)

    def load(self, infilename):
        self.infile = open(infilename + '.prr', 'r+b')
        pickle.load(self.infile)


def main():
    print('\n prr V-0.1 (for experimental use)')
    print('This script is for reading files containing the Reson 7k format.')
    print('Enter the name of the file containing the data:')

    infilename = sys.stdin.readline()[0:-1]
    print('Filename read as: %s\n' % (infilename))
    reader = X7kRead(infilename)
    # reader.extract()
    reader.mapfile()
    firstping = reader.map.packdir['7000'][0][1]
    print('Packet summary:')
    reader.map.printmap()
    reader.close()

    print("Press 'Enter' to exit")
    sys.stdin.readline()


if __name__ == '__main__':
    main()
