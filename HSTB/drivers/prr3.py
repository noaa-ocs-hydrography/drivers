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


recs_categories_7006 = {'1012': ['time', 'Roll', 'Pitch', 'Heave'],
                        '1013': ['time', 'Heading'],
                        '7503': ['time', 'header'],
                      '78': ['time', 'header.Counter', 'header.SoundSpeed', 'header.Ntx', 'header.Serial#',
                             'rx.TiltAngle', 'rx.Delay', 'rx.Frequency', 'rx.BeamPointingAngle',
                             'rx.TransmitSectorID', 'rx.DetectionInfo', 'rx.QualityFactor', 'rx.TravelTime'],
                      '82': ['time', 'header.Mode', 'header.ReceiverFixedGain', 'header.YawAndPitchStabilization', 'settings'],
                      '85': ['time', 'data.Depth', 'data.SoundSpeed'],
                      '80': ['time', 'Latitude', 'Longitude', 'gg_data.Altitude']}

recs_categories_translator = {'65': {'Time': [['attitude', 'time']], 'Roll': [['attitude', 'roll']],
                                        'Pitch': [['attitude', 'pitch']], 'Heave': [['attitude', 'heave']],
                                        'Heading': [['attitude', 'heading']]},
                                 '73': {'time': [['installation_params', 'time']],
                                        'Serial#': [['installation_params', 'serial_one']],
                                        'Serial#2': [['installation_params', 'serial_two']],
                                        'settings': [['installation_params', 'installation_settings']]},
                                 '78': {'time': [['ping', 'time']], 'Counter': [['ping', 'counter']],
                                        'SoundSpeed': [['ping', 'soundspeed']], 'Ntx': [['ping', 'ntx']],
                                        'Serial#': [['ping', 'serial_num']], 'TiltAngle': [['ping', 'tiltangle']], 'Delay': [['ping', 'delay']],
                                        'Frequency': [['ping', 'frequency']], 'BeamPointingAngle': [['ping', 'beampointingangle']],
                                        'TransmitSectorID': [['ping', 'txsector_beam']], 'DetectionInfo': [['ping', 'detectioninfo']],
                                        'QualityFactor': [['ping', 'qualityfactor']], 'TravelTime': [['ping', 'traveltime']]},
                                 '82': {'time': [['runtime_params', 'time']], 'Mode': [['runtime_params', 'mode']],
                                        'ReceiverFixedGain': [['runtime_params', 'modetwo']],
                                        'YawAndPitchStabilization': [['runtime_params', 'yawpitchstab']],
                                        'settings': [['runtime_params', 'runtime_settings']]},
                                 '85': {'time': [['profile', 'time']], 'Depth': [['profile', 'depth']],
                                        'SoundSpeed': [['profile', 'soundspeed']]},
                                 '80': {'time': [['navigation', 'time']], 'Latitude': [['navigation', 'latitude']],
                                        'Longitude': [['navigation', 'longitude']],
                                        'Altitude': [['navigation', 'altitude']]}}
recs_categories_result = {'attitude':  {'time': None, 'roll': None, 'pitch': None, 'heave': None, 'heading': None},
                          'installation_params': {'time': None, 'serial_one': None, 'serial_two': None,
                                                  'installation_settings': None},
                          'ping': {'time': None, 'counter': None, 'soundspeed': None, 'ntx': None, 'serial_num': None,
                                   'tiltangle': None, 'delay': None, 'frequency': None,
                                   'beampointingangle': None, 'txsector_beam': None, 'detectioninfo': None,
                                   'qualityfactor': None, 'traveltime': None},
                          'runtime_params': {'time': None, 'mode': None, 'modetwo': None, 'yawpitchstab': None,
                                             'runtime_settings': None},
                          'profile': {'time': None, 'depth': None, 'soundspeed': None},
                          'navigation': {'time': None, 'latitude': None, 'longitude': None, 'altitude': None}}


class X7kRead:
    """
    Open a file in binary mode and give a packet reader the proper data blocks to read the data packets
    """

    def __init__(self, infilename, start_ptr=0, end_ptr=0):
        """
        opens and memory maps the file
        """

        if start_ptr > end_ptr:
            raise ValueError(f'prr3: start pointer ({start_ptr}) must be greater than end pointer ({end_ptr})')
        # initialize flags for reading methods
        self.eof = False  # end of file reached
        self.hdr_read = False  # header read status
        self.data_read = False  # data read status
        self.last_record_sz = 0  # size of the last record
        self.corrupt_record = False  # status of the current record is corrupt
        self.split_record = False  # split record
        self.mapped = False  # status of the mapping

        self.start_ptr = start_ptr
        self.end_ptr = end_ptr
        self.at_right_byte = False
        self.protocol_version = None

        # find file type and open file
        self.infilename = infilename
        [self.inname, self.intype] = os.path.splitext(infilename)
        self.intype = self.intype[1:].lower()
        self.tempread = True
        if self.intype in ('7k', 's7k'):
            self.infile = open(infilename, 'rb')
            if end_ptr:  # file length is only from start to end pointer
                self.filelen = int(self.end_ptr - self.start_ptr)
            else:  # file length is the whole file
                self.infile.seek(-self.start_ptr, 2)
                self.filelen = self.infile.tell()
            self.infile.seek(0, 2)
            self.max_filelen = self.infile.tell()  # max file length is useful when you use end pointer/start pointer
            self.infile.seek(self.start_ptr, 0)
        else:
            self.infile = None
            self.filelen = 0
            self.max_filelen = 0
            print(f'invalid file type: {self.intype}')

        self.packet = None  # the last decoded datagram
        self.map = None  # the mappack object generated on mapfile
        self._get_protocol_version()

    def _get_protocol_version(self):
        curptr = self.infile.tell()
        if self.intype == '7k':
            self.infile.seek(44, 0)
        else:
            self.infile.seek(4, 0)
        syncpattern = self.infile.read(4)
        assert syncpattern == b'\xff\xff\x00\x00'
        self.infile.seek(-8, 1)
        self.protocol_version = np.frombuffer(self.infile.read(2), dtype='u2')[0]
        if self.protocol_version < 5:
            print(f'prr3: Warning, found protocol version = {self.protocol_version}, only version 5 is tested')
        self.infile.seek(curptr)

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

    def reads7k(self, verbose=True):
        """Processes data block according to the s7k format"""
        # read data record frame
        if not self.at_right_byte:
            self.seek_next_startbyte()
        packetsize = self.checkfile(verbose)
        if self.tempread:
            if packetsize is None:
                print('Unable to find packet size in header!')
            else:
                start_of_datagram = self.infile.tell()
                self.last_record_sz = packetsize
                self.packet = Datagram(self.infile.read(packetsize), start_of_datagram)

    def read7k(self, verbose=True):
        """Removes the Hypack Header and the Reson Network Frames and then assumes s7k format."""
        # format info for reading 7K files
        hypack_hdr = 0  # size of the hypack block remaining
        hypack_sz = 4  # hypack header size
        netfrm_sz = 36  # Reson Network Frames size
        hypack_fmt = '<I'
        netfrm_fmt = '<HHIHH4IHHI'

        if self.split_record:
            self.infile.seek(netfrm_sz, 1)  # this takes into account the netframe header for the next read, but doesn't fix the problem
            hypack_hdr -= netfrm_sz
            self.split_record = False
        if hypack_hdr < 0:  # this happens when a hypack header falls inside of a record
            if np.abs(hypack_hdr) > self.last_record_sz:  # I don't know why this happens
                hypack_hdr = 0
            else:  # this goes back into the corrupted record to find the hypack header
                self.infile.seek(hypack_hdr, 1)
                temp = struct.unpack(hypack_fmt, self.infile.read(hypack_sz))[0]
                self.infile.seek(-hypack_hdr, 1)
                hypack_hdr += temp
        if hypack_hdr == 0:
            temp = self.infile.read(hypack_sz)
            if len(temp) == hypack_sz:
                [hypack_hdr] = struct.unpack(hypack_fmt, temp)
        temp = self.infile.read(netfrm_sz)
        self.reads7k(verbose=verbose)
        if len(temp) == netfrm_sz:
            netfrm_hdr = struct.unpack(netfrm_fmt, temp)
            self.last_record_sz = self.packet.header[3] + netfrm_sz
            hypack_hdr = hypack_hdr - self.last_record_sz
            if hypack_hdr < 0:
                self.corrupt_record = True
            else:
                self.corrupt_record = False
            if netfrm_hdr[5] < netfrm_hdr[6]:  # this is when records are broken up
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
        self.eof = False
        self.hdr_read = False
        self.data_read = False
        self.tempread = True
        self.corrupt_record = False
        self.last_record_sz = 0
        self.split_record = False

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
                    self.last_record_sz = 0
            except AssertionError:
                # print "End of file"
                self.tempread = False
        if count != 0:
            if verbose:
                print("reset " + str(count) + " bytes to " + str(self.infile.tell()))
        return packetsize

    def seek_next_startbyte(self):
        """
        Determines if current pointer is at the start of a record.  If not, finds the next valid one.
        """
        # check is to continue on until you find the header pattern, which surrounds the sync pattern sequence.  Can't just
        #   search for \x00\x00\xff\xff, need to also find protocol version to get it all matched up correctly
        while not self.at_right_byte:
            cur_ptr = self.infile.tell()
            if cur_ptr >= self.start_ptr + self.filelen:
                self.eof = True
                raise ValueError('prr3: Unable to find sonar startbyte, is this sonar supported?')
            # consider start bytes right at the end of the given filelength as valid, even if they extend
            # over to the next chunk
            srchdat = self.infile.read(min(20, (self.start_ptr + self.filelen) - cur_ptr))
            stx_idx = 1
            # First loop through is mandatory to find a startbyte
            while stx_idx >= 0:
                stx_idx = srchdat.find(b'\xff\xff\x00\x00')  # -1 if there is no sync pattern
                if stx_idx >= 0:
                    possible_start = cur_ptr + stx_idx
                    self.infile.seek(possible_start - 4)  # go to protocol version
                    datchk = np.frombuffer(self.infile.read(2), dtype='u2')[0]
                    if datchk == self.protocol_version:
                        self.infile.seek(-2, 1)  # found a valid start, go to the start of the record
                        self.at_right_byte = True
                        break
                if stx_idx < 0:
                    self.infile.seek(-4, 1)  # get ready for the next search, allow for edge case where sync pattern is across chunks
                if not self.at_right_byte:   # continue search in this srchdat chunk of the file
                    try:
                        srchdat = srchdat[stx_idx + 1:]  # Start after that invalid start byte, look for the next in the chunk
                        cur_ptr += stx_idx + 1
                    except:  # must be at the end of the chunk, so the next .find will return -1 anyway
                        pass

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
        if recordtype in self.map.packdir:
            loc = int(self.map.packdir[recordtype][numrecord][0])
            self.infile.seek(loc)
            self.hdr_read = False
            self.data_read = False
            self.eof = False
            self.get()
            return self.packet.subpack
        else:
            print(f'Unable to find record {recordtype} in file')
            self.packet = None

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
        dgram = get_datagram_by_number(self.dtype)
        if dgram is not None:
            self.subpack = dgram(self.datablock, self.time)
            self.decoded = True
        else:
            self.subpack = None
            self.decoded = False

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


def get_datagram_by_number(datagram_number: int):
    try:
        return sys.modules[__name__].__dict__[f'Data{datagram_number}']
    except KeyError:
        print(f'prr3: Unable to find datagram class for Data{datagram_number}')
        return None


class Data1000(BaseData):
    """
    Reference Point Datagram
    """
    hdr_dtype = np.dtype([('XRefPointToGravity', 'f4'), ('YRefPointToGravity', 'f4'), ('ZRefPointToGravity', 'f4'),
                          ('WaterLevelToGravity', 'f4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1000, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


class Data1003(BaseData):
    """
    Position Datagram
    """
    hdr_dtype = np.dtype([('DatumIdentifier', 'u4'), ('Latency', 'f4'), ('LatitudeNorthing', 'f8'),
                          ('LongitudeEasting', 'f8'), ('Height', 'f8'), ('PositionFlag', 'u1'), ('UtmZone', 'u1'),
                          ('QualityFlag', 'u1'), ('PositionMethod', 'u1'), ('NumberOfSatellites', 'u1')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        if len(datablock) == 37:  # it includes numberofsatellites
            super(Data1003, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        elif len(datablock) == 36:
            self.hdr_dtype = np.dtype([('DatumIdentifier', 'u4'), ('Latency', 'f4'), ('LatitudeNorthing', 'f8'),
                                       ('LongitudeEasting', 'f8'), ('Height', 'f8'), ('PositionFlag', 'u1'),
                                       ('UtmZone', 'u1'), ('QualityFlag', 'u1'), ('PositionMethod', 'u1')])
            self.hdr_sz = self.hdr_dtype.itemsize
            super(Data1003, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        else:
            raise NotImplementedError('prr3: Found a Data1003 datablock that is neither 36 nor 37 long, not sure what it is')
        self.time = utctime


class Data1008(BaseData):
    """
    Depth Datagram
    """
    hdr_dtype = np.dtype([('DepthDescriptor', 'u1'), ('CorrectionFlag', 'u1'), ('Reserved', 'u2'),
                          ('Depth', 'f4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1008, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


class Data1009(BaseData):
    """
    Sound Velocity Profile Datagram
    """
    hdr_dtype = np.dtype([('PositionFlag', 'u1'), ('ReservedOne', 'u1'), ('ReservedTwo', 'u2'),
                          ('Latitude', 'f8'), ('Longitude', 'f8'), ('NumberOfLayers', 'u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1009, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.profile_depth = []
        self.profile_data = []
        self.position = (self.header['Latitude'], self.header['Longitude'])
        self.numlayers = self.header['NumberOfLayers']
        self.read_data(datablock[self.hdr_sz:])

    def read_data(self, datablock):
        self.profile_depth = []
        self.profile_data = []
        layer_dtype = np.dtype([('depth', 'f4'), ('sv', 'f4')])
        datapointer = 0
        for i in range(self.numlayers):
            device_data = list(np.frombuffer(datablock[datapointer:datapointer + layer_dtype.itemsize], dtype=layer_dtype)[0])
            datapointer += layer_dtype.itemsize
            self.profile_depth.append(device_data[0])
            self.profile_data.append(device_data[1])


class Data1010(BaseData):
    """
    CTD Datagram
    """
    hdr_dtype = np.dtype([('Frequency', 'f4'), ('SoundVelocitySourceFlag', 'u1'), ('SoundVelocityAlgorithm', 'u1'),
                          ('ConductivityFlag', 'u1'), ('PressureFlag', 'u1'), ('PositionFlag', 'u1'),
                          ('SampleContentValidity', 'u1'), ('Reserved', 'u2'), ('Latitude', 'f8'), ('Longitude', 'f8'),
                          ('SampleRate', 'f4'), ('NumberOfLayers', 'u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        super(Data1010, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.profile_conductivity = []
        self.profile_temperature = []
        self.profile_depth = []
        self.profile_soundvelocity = []
        self.profile_absorption = []
        self.position = (self.header['Latitude'], self.header['Longitude'])
        self.numlayers = self.header['NumberOfLayers']
        self.read_data(datablock[self.hdr_sz:])

    def read_data(self, datablock):
        self.profile_conductivity = []
        self.profile_temperature = []
        self.profile_depth = []
        self.profile_soundvelocity = []
        self.profile_absorption = []
        layer_dtype = np.dtype([('cond', 'f4'), ('temp', 'f4'), ('depth', 'f4'), ('sv', 'f4'), ('absorp', 'f4')])
        datapointer = 0
        for i in range(self.numlayers):
            device_data = list(np.frombuffer(datablock[datapointer:datapointer + layer_dtype.itemsize], dtype=layer_dtype)[0])
            datapointer += layer_dtype.itemsize
            self.profile_conductivity.append(device_data[0])
            self.profile_temperature.append(device_data[1])
            self.profile_depth.append(device_data[2])
            self.profile_soundvelocity.append(device_data[3])
            self.profile_absorption.append(device_data[4])


class Data1012(BaseData):
    """
    Roll Pitch Heave Datagram
    """
    hdr_dtype = np.dtype([('Roll', 'f4'), ('Pitch', 'f4'), ('Heave', 'f4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1012, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


class Data1013(BaseData):
    """
    Heading Datagram
    """
    hdr_dtype = np.dtype([('Heading', 'f4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1013, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


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

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7000, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


class Data7001(BaseData):
    """
    Configuration record, generated on system startup, does not change during operation
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('NumberOfDevices', 'u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7001, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
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

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7002, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


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
    hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', 'f4'), ('BeamHorizontalDirectionAngle', 'f4'),
                          ('BeamWidthAlongTrack', 'f4'), ('BeamWidthAcrossTrack', 'f4')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data7004BeamsOld, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)


class Data7004(BaseData):
    """
    Beam Geometry
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('NumberOfBeams', 'u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7004, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numbeams = self.header[1]
        self.data = None
        self.fig = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        if len(datablock) == self.numbeams * 4 * 4:
            dgram = Data7004BeamsOld
            dgram.hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', f'{self.numbeams}f'),
                                        ('BeamHorizontalDirectionAngle', f'{self.numbeams}f'),
                                        ('BeamWidthAlongTrack', f'{self.numbeams}f'),
                                        ('BeamWidthAcrossTrack', f'{self.numbeams}f')])
        elif len(datablock) == self.numbeams * 5 * 4:
            dgram = Data7004BeamsNew
            dgram.hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', f'{self.numbeams}f'),
                                        ('BeamHorizontalDirectionAngle', f'{self.numbeams}f'),
                                        ('BeamWidthAlongTrack', f'{self.numbeams}f'),
                                        ('BeamWidthAcrossTrack', f'{self.numbeams}f'), ('TxDelay', f'{self.numbeams}f')])
        else:
            print('Datagram 7004: expected either 4 or 5 variable records, could not determine datagram version')
            return
        dgram.hdr_sz = dgram.hdr_dtype.itemsize
        self.data = dgram(datablock)

    def plot(self):
        """Plots the 7004 record as one plot with four subplots."""
        self.fig = plt.figure()
        ax1 = self.fig.add_subplot(411, xlim=(0, self.numbeams), autoscalex_on=False)
        ax1.plot(np.rad2deg(self.data.BeamVerticalDirectionAngle[0]))
        ax1.set_ylabel('Along Track Angle (deg)')
        ax1.set_title('Beam Configuration Information')
        ax2 = self.fig.add_subplot(412, sharex=ax1, autoscalex_on=False)
        ax2.plot(np.rad2deg(self.data.BeamHorizontalDirectionAngle[0]))
        ax2.set_ylabel('Across Track Angle (deg)')
        ax3 = self.fig.add_subplot(413, sharex=ax1, autoscalex_on=False)
        ax3.plot(np.rad2deg(self.data.BeamWidthAlongTrack[0]))
        ax3.set_ylabel('Along Track Beamwidth (deg)')
        ax4 = self.fig.add_subplot(414, sharex=ax1, autoscalex_on=False)
        ax4.plot(np.rad2deg(self.data.BeamWidthAcrossTrack[0]))
        ax4.set_ylabel('Across Track Beamwidth (deg)')
        ax4.set_xlabel('Beam Number')


class Data7006Beams(BaseData):
    """
    The by-beam variables within 7006
    Expects you to update hdr_dtype from the Data7006 before initialization
    """
    hdr_dtype = np.dtype([('Range', 'f4'), ('Quality', 'u1'), ('Intensity', 'f4'),
                          ('MinTravelTimeToFilter', 'f4'), ('MaxTravelTimeToFilter', 'f4')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data7006Beams, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)


class Data7006(BaseData):
    """
    SUPERSEDED BY 7027
    Bathymetric Data, sonar bottom detection results
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultiPingSequence', 'u2'), ('NumberOfBeams', 'u4'),
                          ('Flags', 'u1'), ('SoundVelocityFlag', 'u1'), ('SoundVelocity', 'f4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7006, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numbeams = self.header[3]
        self.data = None
        self.fig = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        if len(datablock) == self.numbeams * 17:
            dgram = Data7006Beams
            dgram.hdr_dtype = np.dtype([('Range', f'{self.numbeams}f4'), ('Quality', f'{self.numbeams}u1'),
                                        ('Intensity', f'{self.numbeams}f4'), ('MinTravelTimeToFilter', f'{self.numbeams}f4'),
                                        ('MaxTravelTimeToFilter', f'{self.numbeams}f4')])
        else:
            print(f'Datagram 7006: Unexpected Datablock size, {len(datablock)} not equal to {self.numbeams} * 17')
            return
        dgram.hdr_sz = dgram.hdr_dtype.itemsize
        self.data = dgram(datablock)


class Data7007Beams(BaseData):
    """
    The by-beam variables within 7007
    Expects you to update hdr_dtype from the Data7007 before initialization
    """
    hdr_dtype = np.dtype([('PortBeams', 'f4'), ('StarboardBeams', 'f4')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data7007Beams, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)


class Data7007(BaseData):
    """
    Side Scan Record
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultiPingSequence', 'u2'), ('BeamPosition', 'f4'),
                          ('ControlFlags', 'u4'), ('SamplesPerSide', 'u4'), ('NadirDepth', 'u4'), ('Reserved', '7f4'),
                          ('NumberOfBeams', 'u2'), ('CurrentBeamNumber', 'u2'), ('NumberOfBytes', 'u1'), ('DataTypes', 'u1')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7007, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numbeams = self.header[8]
        self.numbytes = self.header[10]
        self.data = None
        self.fig = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        dtyp = f'{self.numbeams}f{self.numbytes}'
        if len(datablock) == self.numbeams * self.numbytes * 2:
            dgram = Data7007Beams
            dgram.hdr_dtype = np.dtype([('PortBeams', dtyp), ('StarboardBeams', dtyp)])
        else:
            print(f'Datagram 7006: Unexpected Datablock size, {len(datablock)} not equal to {self.numbeams} * {self.numbytes} * 2')
            return
        dgram.hdr_sz = dgram.hdr_dtype.itemsize
        self.data = dgram(datablock)


class Data7008(BaseData):
    """
    DEPRECATED Generic Water Column Data, superseded by 7018 and 7028
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('NumberOfBeams', 'u2'), ('ReservedOne', 'u2'), ('Samples', 'u4'), ('RecordSubsetFlag', 'u1'),
                          ('RowColumnFlag', 'u1'), ('ReservedTwo', 'u2'), ('DataSampleSize', 'u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7008, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numbeams = self.header[3]
        self.beams = None
        self.numsnip = None
        self.mag = None
        self.phase = None
        self.iele = None
        self.qele = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        """
        Reading the original snippet message. This is reading the snippet data and is dependant on the information
        from the header. The steps 1) read each beam snippet size 2)read in the data for each beam, which could consist
        of magnitude, phase, I&Q, for each beam or element.
        """

        # define the format string and size for snippet data through bitwise ops
        # Thanks to Tom Weber and Les Peabody for helping figure this out
        fmt_flags = self.header['DataSampleSize']
        magval = 7 & fmt_flags
        phaseval = (240 & fmt_flags) >> 4
        iqval = (3840 & fmt_flags) >> 8
        elementflag = (28672 & fmt_flags) >> 12
        fmt = []
        if magval == 2:
            fmt.append(('Magnitude', 'H'))
        elif magval == 3:
            fmt.append(('Magnitude', 'I'))
        if phaseval == 2:
            fmt.append(('Phase', 'H'))
        elif phaseval == 3:
            fmt.append(('Phase', 'I'))
        if iqval == 1:
            fmt.append(('I', 'H'))
            fmt.append(('Q', 'H'))
        elif iqval == 2:
            fmt.append(('I', 'I'))
            fmt.append(('Q', 'I'))
        snip_fmt = np.dtype(fmt)
        beam_fmt = np.dtype([('BeamNumber', 'H'), ('FirstSample', 'I'), ('LastSample', 'I')])
        # read the beam snippet sizes (zones)
        block_sz = self.numbeams * beam_fmt.itemsize
        self.beams = np.frombuffer(datablock[:block_sz], beam_fmt)
        temp = (self.beams['LastSample'] - self.beams['FirstSample']).max() + 1
        self.numsnip = temp.max()
        if not (self.numsnip == temp).all():
            print("Warning: number of snippets is not consistent.")

        # read snippet data as columns for each data type (mag/phase/i/q)
        snip = np.frombuffer(datablock[block_sz:], snip_fmt)
        # separate types out to different arrays
        ordertype = self.header['RowColumnFlag']
        if magval != 0:
            self.mag = snip['Magnitude'].astype(np.float64)
            if ordertype == 0:
                self.mag.shape = (self.numbeams, self.numsnip)
                self.mag = self.mag.transpose()
            elif ordertype == 1:
                self.mag.shape = (self.numsnip, self.numbeams)
        if phaseval != 0:
            self.phase = snip['Phase'].astype(np.float64)
            if self.header[7] == 0:
                self.phase.shape = (self.numbeams, self.numsnip)
                self.phase = self.phase.transpose()
            elif self.header[7] == 1:
                self.phase.shape = (self.numsnip, self.numbeams)
        if iqval != 0:
            self.iele = snip['I'].astype(np.float64)
            self.qele = snip['Q'].astype(np.float64)
            if self.header[7] == 0:
                self.iele.shape = (self.numbeams, self.numsnip)
                self.iele = self.iele.transpose()
                self.qele.shape = (self.numbeams, self.numsnip)
                self.qele = self.qele.transpose()
            elif self.header[7] == 1:
                self.iele.shape = (self.numsnip, self.numbeams)
                self.qele.shape = (self.numsnip, self.numbeams)

    def plot(self):
        """plot any snippet data collected"""
        if self.mag is not None:
            plt.figure()
            mg = self.mag.copy()
            mg[mg == 0] = np.nan  # force NAN to get over divide by zero issues
            magplot = plt.imshow(20 * np.log10(mg), aspect='auto')
            plt.title('7008 20*log10*Magnitude')
            plt.xlabel('Beam number')
            plt.ylabel('Sample number in window')
            plt.colorbar()
        if self.phase is not None:
            plt.figure()
            phaseplot = plt.imshow(self.phase, aspect='auto')
            plt.title('7008 Phase')
            plt.xlabel('Beam number')
            plt.ylabel('Sample number in window')
        plt.draw()

    def display(self):
        for n, name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        print('Size of snippet window: ' + str(self.numsnip))
        self.plot()


class Data7010Beams(BaseData):
    """
    The by-beam variables within 7007
    Expects you to update hdr_dtype from the Data7007 before initialization
    """
    hdr_dtype = np.dtype([('Gain', 'f4')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data7010Beams, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)


class Data7010(BaseData):
    """
    TVG Values, one for each sample in the ping
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Samples', 'u4'), ('Reserved', '8u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7010, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numsamples = self.header[3]
        self.data = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        if len(datablock) == self.numsamples * 4:
            dgram = Data7010Beams
            dgram.hdr_dtype = np.dtype([('Gain', f'{self.numsamples}f4')])
        else:
            print(f'Datagram 7010: Unexpected Datablock size, {len(datablock)} not equal to {self.numsamples} * 4')
            return
        dgram.hdr_sz = dgram.hdr_dtype.itemsize
        self.data = dgram(datablock)


class Data7012(BaseData):
    """
    Ping Motion Data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Samples', 'u4'), ('Flags', 'u2'), ('ErrorFlags', 'u4'), ('SamplingRate', 'f4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7012, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numsamples = self.header[3]
        self.pitch = None
        self.roll = None
        self.heading = None
        self.heave = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        cur_counter = 0
        if self.header['Flags'] & 1:
            self.pitch = np.frombuffer(datablock[cur_counter:4], np.dtype([('Pitch', 'f4')]))
            cur_counter += 4
        if self.header['Flags'] & 2:
            self.roll = np.frombuffer(datablock[cur_counter:4 * self.numsamples], np.dtype([('Roll', f'{self.numsamples}f4')]))
            cur_counter += 4 * self.numsamples
        if self.header['Flags'] & 4:
            self.heading = np.frombuffer(datablock[cur_counter:4 * self.numsamples], np.dtype([('Heading', f'{self.numsamples}f4')]))
            cur_counter += 4 * self.numsamples
        if self.header['Flags'] & 8:
            self.heave = np.frombuffer(datablock[cur_counter:4 * self.numsamples], np.dtype([('Heave', f'{self.numsamples}f4')]))
            cur_counter += 4 * self.numsamples


class Data7014(BaseData):
    """
    Adaptive Gate Record
    """
    hdr_dtype = np.dtype([('RecordHeaderSize', 'u2'), ('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('NumberOfGates', 'u4'), ('GateDescriptorSize', 'u2')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7014, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numgates = self.header[4]
        self.data = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        strt_counter = 0
        gate_dtype = np.dtype([('Angle', 'f4'), ('MinLimit', 'f4'), ('MaxLimit', 'f4')])
        gate_dsize = gate_dtype.itemsize
        for i in range(self.numgates):
            gate_data = np.frombuffer(datablock[strt_counter:strt_counter + gate_dsize], gate_dtype)
            self.data.append(gate_data)
            strt_counter += gate_dsize


class Data7021Board(BaseData):
    """
    BITE record data by Board
    """
    hdr_dtype = np.dtype([('SourceName', 'S64'), ('SourceAddress', 'u1'), ('ReservedOne', 'f4'), ('ReservedTwo', 'u2'),
                          ('DownlinkTimeSentYear', 'u2'), ('DownlinkTimeSentDay', 'u2'), ('DownlinkTimeSentSeconds', 'f4'),
                          ('DownlinkTimeSentHours', 'u1'), ('DownlinkTimeSentMinutes', 'u1'), ('UplinkTimeSentYear', 'u2'),
                          ('UplinkTimeSentDay', 'u2'), ('UplinkTimeSentSeconds', 'f4'), ('UplinkTimeSentHours', 'u1'),
                          ('UplinkTimeSentMinutes', 'u1'), ('BiteTimeReceivedYear', 'u2'), ('BiteTimeReceivedDay', 'u2'),
                          ('BiteTimeReceivedSeconds', 'f4'), ('BiteTimeReceivedHours', 'u1'), ('BiteTimeReceivedMinutes', 'u1'),
                          ('Status', 'u1'), ('NumberOfFields', 'u2'), ('BiteStatusBits', '4u8')])

    def __init__(self, datablock, byteswap=False, read_limit=1):
        super(Data7021Board, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.numfields = self.header['NumberOfFields']
        self.field_dtype = np.dtype([('FieldNumber', 'u2'), ('NameValueRangeText', 'S64'), ('SensorType', 'u1'),
                                     ('Minimum', 'f4'), ('Maximum', 'f4'), ('Value', 'f4')])
        self.field_sz = self.field_dtype.itemsize
        self.data = None
        self.read(datablock[self.hdr_sz:])
        self.totalsize = self.hdr_sz + (self.numfields * self.field_sz)

    def read(self, datablock):
        strt_counter = 0
        for i in range(self.numfields):
            gate_data = np.frombuffer(datablock[strt_counter:strt_counter + self.field_sz], self.field_dtype)
            self.data.append(gate_data)
            strt_counter += self.field_sz


class Data7021(BaseData):
    """
    BITE record, Built in Test Environment, contains troubleshooting data
    """
    hdr_dtype = np.dtype([('NumberOfBoards', 'u2')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7021, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numboards = self.header[0]
        self.data = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        strt_counter = 0
        for board in range(self.numboards):
            data = Data7021Board(datablock[strt_counter:])
            strt_counter += data.totalsize
            self.data.append(data)


class Data7022(BaseData):
    """
    Sonar Source Version
    """
    hdr_dtype = np.dtype([('VersionString', 'S32')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7022, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime


class Data7027(BaseData):
    """
    SUPERSEDED BY 7047
    Raw Detection Data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Detections', 'u4'), ('DataFieldSize', 'u4'), ('DetectionAlgorithm', 'u1'), ('Flags', 'u4'),
                          ('SamplingRate', 'f4'), ('TxAngle', 'f4'), ('AppliedRoll', 'f4'), ('Reserved', '15u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7027, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numdetections = self.header[3]
        self.data = None
        self.detect_dtype = np.dtype([('BeamDescriptor', 'u2'), ('DetectionPoint', 'f4'), ('RxAngle', 'f4'), ('DetectionFlags', 'u4'),
                                      ('Quality', 'u4'), ('Uncertainty', 'f4'), ('Intensity', 'f4'), ('MinLimit', 'f4'), ('MaxLimit', 'f4')])
        self.detect_dsize = self.detect_dtype.itemsize
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        strt_counter = 0
        for i in range(self.numdetections):
            data = np.frombuffer(datablock[strt_counter:], self.detect_dtype)
            strt_counter += self.detect_dsize
            self.data.append(data)


class Data7028(BaseData):
    """
    Snippet Data, sonar snippet imagery data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Detections', 'u2'), ('ErrorFlags', 'u1'), ('ControlFlags', 'u1'), ('Flags', 'u4'),
                          ('SamplingRate', 'f4'), ('Reserved', '5u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7028, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numdetections = self.header[3]
        self.descriptor = None
        self.beamwindow = None
        self.maxbeam = None
        self.maxwindow = None
        self.snippets = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        if self.header['ErrorFlags'] == 0:
            self.descriptor = np.zeros((self.numpoints, 4))
            strt_counter = 0
            fmt_descriptor = '<H3I'
            descriptor_sz = struct.calcsize(fmt_descriptor)
            for beam in range(self.numpoints):
                self.descriptor[beam, :] = struct.unpack(fmt_descriptor, datablock[strt_counter:strt_counter + descriptor_sz])
                strt_counter += descriptor_sz
            self.beamwindow = self.descriptor[:, 3] - self.descriptor[:, 1] + 1
            self.maxbeam = int(self.descriptor[:, 0].max()) + 1
            self.maxwindow = self.beamwindow.max()
            self.snippets = np.zeros((self.maxbeam, self.maxwindow))
            for beam in range(self.numpoints):
                fmt_data = '<' + str(int(self.beamwindow[beam])) + 'H'
                data_sz = struct.calcsize(fmt_data)
                startoffset = int((self.maxwindow - self.beamwindow[beam]) / 2)
                beam_data = struct.unpack(fmt_data, datablock[strt_counter:strt_counter + data_sz])
                strt_counter += data_sz
                self.snippets[int(self.descriptor[beam, 0]), startoffset: startoffset + self.beamwindow[beam]] = beam_data


class Data7041(BaseData):
    """
    Compressed Beamformed Intensity Data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Beams', 'u2'), ('Flags', 'u2'), ('SampleRate', 'f4'), ('Reserved', '4u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=1):
        super(Data7041, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.time = utctime
        self.numbeams = self.header[3]
        self.data = None
        self.beam_identifiers = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        self.data = []
        self.beam_identifiers = []
        flags = self.header[4]
        if (flags & 256) == 256:
            beamid = 'f4'
        else:
            beamid = 'u2'
        cur_pointer = 0
        for i in range(self.numbeams):
            data_fmt = np.dtype(beamid)
            data_sz = data_fmt.itemsize
            beaminfo = np.frombuffer(datablock[cur_pointer:cur_pointer + data_sz], data_fmt)[0]
            cur_pointer += data_sz
            data_fmt = np.dtype('u4')
            data_sz = data_fmt.itemsize
            numsamples = np.frombuffer(datablock[cur_pointer:cur_pointer + data_sz], data_fmt)[0]
            cur_pointer += data_sz
            self.beam_identifiers.append(beaminfo)
            data_fmt = np.dtype(f'{int(numsamples)}{beamid}')
            data_sz = data_fmt.itemsize
            beamdata = np.frombuffer(datablock[cur_pointer:cur_pointer + data_sz], data_fmt)[0]
            cur_pointer += data_sz
            self.data.append(beamdata)


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

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        super(Data7200, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        # the strings are 'null terminated' so strip the bytes from those messages
        self.header['RecordingName'] = self.header['RecordingName'][0].rstrip(b'\xff').rstrip(b'\x00').decode()
        self.header['RecordingProgramVersion'] = self.header['RecordingProgramVersion'][0].rstrip(b'\xff').rstrip(b'\x00').decode()
        self.header['UserDefinedName'] = self.header['UserDefinedName'][0].rstrip(b'\xff').rstrip(b'\x00').decode()
        self.header['Notes'] = self.header['Notes'][0].rstrip(b'\xff').rstrip(b'\x00').decode()

        self.time = utctime
        self.record_data = []
        self.record_data_header = np.dtype([('DeviceIdentifier', 'u4'), ('SystemEnumerator', 'u2')])
        self.optional_data = []
        self.optional_data_header = np.dtype([('OptionalSize', 'u4'), ('OptionalOffset', 'u8')])

        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        numdevices = int(self.header['NumberOfDevices'])
        has_record_data = int(self.header['RecordDataSize']) != 0
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


class Data7503(BaseData):
    """
    Remote Control Sonar Settings Datagram, one is produced with each ping
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('Frequency', 'f4'),
                          ('SampleRate', 'f4'), ('ReceiverBandwidth', 'f4'), ('TXPulseWidth', 'f4'),
                          ('TXPulseTypeID', 'u4'), ('TXPulseEnvelope', 'u4'), ('TXPulseEnvelopeParameter', 'f4'),
                          ('TXPulseMode', 'u2'), ('TXPulseReserved', 'u2'), ('MaxPingRate', 'f4'), ('PingPeriod', 'f4'),
                          ('RangeSelection', 'f4'), ('PowerSelection', 'f4'), ('GainSelection', 'f4'), ('ControlFlags', 'u4'),
                          ('ProjectorIdentifier', 'u4'), ('ProjectorBeamSteeringAngleVertical', 'f4'),
                          ('ProjectorBeamSteeringAngleHorizontal', 'f4'), ('ProjectorBeamWidthVertical', 'f4'),
                          ('ProjectorBeamWidthHorizontal', 'f4'), ('ProjectorBeamFocalPoint', 'f4'),
                          ('ProjectorBeamWeightingWindowType', 'u4'), ('ProjectorBeamWeightingWindowParameter', 'f4'),
                          ('TransmitFlags', 'u4'), ('HydrophoneIdentifier', 'u4'), ('ReceiveBeamWeightingWindow', 'u4'),
                          ('ReceiveBeamWeightingParamter', 'f4'), ('ReceiveFlags', 'u4'),
                          ('BottomDetectionFilterMinRange', 'f4'), ('BottomDetectionFilterMaxRange', 'f4'),
                          ('BottomDetectionFilterMinDepth', 'f4'), ('BottomDetectionFilterMaxDepth', 'f4'),
                          ('Absorption', 'f4'), ('SoundVelocity', 'f4'), ('Spreading', 'f4'), ('VernierOperationMode', 'u1'),
                          ('AutomaticFilterWindow', 'u1'), ('TxArrayPositionOffsetX', 'f4'), ('TxArrayPositionOffsetY', 'f4'),
                          ('TxArrayPositionOffsetZ', 'f4'), ('HeadTiltX', 'f4'), ('HeadTiltY', 'f4'), ('HeadTiltZ', 'f4'),
                          ('PingState', 'u4'), ('BeamSpacingMode', 'u2'), ('SonarSourceMode', 'u2'), ('AdaptiveGateBottomMinDepth', 'f4'),
                          ('AdaptiveGateBottomMaxDepth', 'f4'), ('TriggerOutWidth', 'f8'), ('TriggerOutOffset', 'f8'),
                          ('EightSeriesProjectorSelection', 'u2'), ('ReservedOne', '2u4'), ('EightSeriesAlternateGain', 'f4'),
                          ('VernierFilter', 'u1'), ('ReservedTwo', 'u1'), ('CustomBeams', 'u2'), ('CoverageAngle', 'f4'),
                          ('CoverageMode', 'u1'), ('QualityFilterFlags', 'u1'), ('HorizontalReceiverBeamSteeringAngle', 'f4'),
                          ('FlexModeSectorCoverage', 'f4'), ('FlexModeSectorSteering', 'f4'), ('ConstantSpacing', 'f4'),
                          ('BeamModeSelection', 'u2'), ('DepthGateTilt', 'f4'), ('AppliedFrequency', 'f4'),
                          ('ElementNumber', 'u4'), ('MaxImageHeight', 'u4'), ('BytesPerPixel', 'u4')])

    def __init__(self, datablock, utctime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        if len(datablock) == 268:
            super(Data7503, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        elif len(datablock) == 260:
            self.hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('Frequency', 'f4'),
                                       ('SampleRate', 'f4'), ('ReceiverBandwidth', 'f4'), ('TXPulseWidth', 'f4'),
                                       ('TXPulseTypeID', 'u4'), ('TXPulseEnvelope', 'u4'), ('TXPulseEnvelopeParameter', 'f4'),
                                       ('TXPulseMode', 'u2'), ('TXPulseReserved', 'u2'), ('MaxPingRate', 'f4'), ('PingPeriod', 'f4'),
                                       ('RangeSelection', 'f4'), ('PowerSelection', 'f4'), ('GainSelection', 'f4'), ('ControlFlags', 'u4'),
                                       ('ProjectorIdentifier', 'u4'), ('ProjectorBeamSteeringAngleVertical', 'f4'),
                                       ('ProjectorBeamSteeringAngleHorizontal', 'f4'), ('ProjectorBeamWidthVertical', 'f4'),
                                       ('ProjectorBeamWidthHorizontal', 'f4'), ('ProjectorBeamFocalPoint', 'f4'),
                                       ('ProjectorBeamWeightingWindowType', 'u4'), ('ProjectorBeamWeightingWindowParameter', 'f4'),
                                       ('TransmitFlags', 'u4'), ('HydrophoneIdentifier', 'u4'), ('ReceiveBeamWeightingWindow', 'u4'),
                                       ('ReceiveBeamWeightingParamter', 'f4'), ('ReceiveFlags', 'u4'),
                                       ('BottomDetectionFilterMinRange', 'f4'), ('BottomDetectionFilterMaxRange', 'f4'),
                                       ('BottomDetectionFilterMinDepth', 'f4'), ('BottomDetectionFilterMaxDepth', 'f4'),
                                       ('Absorption', 'f4'), ('SoundVelocity', 'f4'), ('Spreading', 'f4'), ('VernierOperationMode', 'u1'),
                                       ('AutomaticFilterWindow', 'u1'), ('TxArrayPositionOffsetX', 'f4'), ('TxArrayPositionOffsetY', 'f4'),
                                       ('TxArrayPositionOffsetZ', 'f4'), ('HeadTiltX', 'f4'), ('HeadTiltY', 'f4'), ('HeadTiltZ', 'f4'),
                                       ('PingState', 'u4'), ('BeamSpacingMode', 'u2'), ('SonarSourceMode', 'u2'), ('AdaptiveGateBottomMinDepth', 'f4'),
                                       ('AdaptiveGateBottomMaxDepth', 'f4'), ('TriggerOutWidth', 'f8'), ('TriggerOutOffset', 'f8'),
                                       ('EightSeriesProjectorSelection', 'u2'), ('ReservedOne', '2u4'), ('EightSeriesAlternateGain', 'f4'),
                                       ('VernierFilter', 'u1'), ('ReservedTwo', 'u1'), ('CustomBeams', 'u2'), ('CoverageAngle', 'f4'),
                                       ('CoverageMode', 'u1'), ('QualityFilterFlags', 'u1'), ('HorizontalReceiverBeamSteeringAngle', 'f4'),
                                       ('FlexModeSectorCoverage', 'f4'), ('FlexModeSectorSteering', 'f4'), ('ConstantSpacing', 'f4'),
                                       ('BeamModeSelection', 'u2'), ('DepthGateTilt', 'f4'), ('AppliedFrequency', 'f4'),
                                       ('ElementNumber', 'u4')])
            self.hdr_sz = self.hdr_dtype.itemsize
            super(Data7503, self).__init__(datablock, byteswap=byteswap, read_limit=read_limit)
        self.settings = {'waterline_vertical_location': '0.0'}
        self.ky_data73_translator = {'SonarID': 'system_main_head_serial_number',
                                     'S0Z': 'transducer_0_vertical_location', 'S0X': 'transducer_0_along_location',
                                     'S0Y': 'transducer_0_athwart_location', 'S0H': 'transducer_0_heading_angle',
                                     'S0R': 'transducer_0_roll_angle', 'S0P': 'transducer_0_pitch_angle',
                                     'S1Z': 'transducer_1_vertical_location', 'S1X': 'transducer_1_along_location',
                                     'S1Y': 'transducer_1_athwart_location', 'S1H': 'transducer_1_heading_angle',
                                     'S1R': 'transducer_1_roll_angle', 'S1P': 'transducer_1_pitch_angle',
                                     'S1N': 'transducer_1_number_modules', 'S2Z': 'transducer_2_vertical_location',
                                     'S2X': 'transducer_2_along_location', 'S2Y': 'transducer_2_athwart_location',
                                     'S2H': 'transducer_2_heading_angle', 'S2R': 'transducer_2_roll_angle',
                                     'S2P': 'transducer_2_pitch_angle', 'S2N': 'transducer_2_number_modules',
                                     'S3Z': 'transducer_3_vertical_location', 'S3X': 'transducer_3_along_location',
                                     'S3Y': 'transducer_3_athwart_location', 'S3H': 'transducer_3_heading_angle',
                                     'S3R': 'transducer_3_roll_angle', 'S3P': 'transducer_3_pitch_angle',
                                     'S0S': 'tx_2_array_size', 'S3S': 'rx_2_array_size',
                                     'S1S': 'tx_array_size', 'S2S': 'rx_array_size', 'GO1': 'sonar_head_1_gain_offset',
                                     'GO2': 'sonar_head_2_gain_offset', 'OBO': 'outer_beam_offset',
                                     'FGD': 'high_low_freq_gain_difference', 'TSV': 'transmitter_software_version',
                                     'RSV': 'receiver_software_version', 'BSV': 'bsp_software_version',
                                     'PSV': 'processing_unit_software_version', 'DDS': 'dds_software_version',
                                     'OSV': 'operator_station_software_version', 'DSV': 'datagram_format_version',
                                     'DSX': 'pressure_sensor_along_location', 'DSY': 'pressure_sensor_athwart_location',
                                     'DSZ': 'pressure_sensor_vertical_location', 'DSD': 'pressure_sensor_time_delay',
                                     'DSO': 'pressure_sensor_offset', 'DSF': 'pressure_sensor_scale_factor',
                                     'DSH': 'pressure_sensor_heave', 'APS': 'active_position_system_number',
                                     'P1Q': 'position_1_quality_check', 'P1M': 'position_1_motion_compensation',
                                     'P1T': 'position_1_time_stamp', 'P1Z': 'position_1_vertical_location',
                                     'P1X': 'position_1_along_location', 'P1Y': 'position_1_athwart_location',
                                     'P1D': 'position_1_time_delay', 'P1G': 'position_1_datum',
                                     'P2Q': 'position_2_quality_check', 'P2M': 'position_2_motion_compensation',
                                     'P2T': 'position_2_time_stamp', 'P2Z': 'position_2_vertical_location',
                                     'P2X': 'position_2_along_location', 'P2Y': 'position_2_athwart_location',
                                     'P2D': 'position_2_time_delay', 'P2G': 'position_2_datum',
                                     'P3Q': 'position_3_quality_check', 'P3M': 'position_3_motion_compensation',
                                     'P3T': 'position_3_time_stamp', 'P3Z': 'position_3_vertical_location',
                                     'P3X': 'position_3_along_location', 'P3Y': 'position_3_athwart_location',
                                     'P3D': 'position_3_time_delay', 'P3G': 'position_3_datum',
                                     'P3S': 'position_3_serial_or_ethernet',
                                     'MSZ': 'motion_sensor_1_vertical_location',
                                     'MSX': 'motion_sensor_1_along_location', 'MSY': 'motion_sensor_1_athwart_location',
                                     'MRP': 'motion_sensor_1_roll_ref_plane', 'MSD': 'motion_sensor_1_time_delay',
                                     'MSR': 'motion_sensor_1_roll_angle', 'MSP': 'motion_sensor_1_pitch_angle',
                                     'MSG': 'motion_sensor_1_heading_angle',
                                     'NSZ': 'motion_sensor_2_vertical_location',
                                     'NSX': 'motion_sensor_2_along_location', 'NSY': 'motion_sensor_2_athwart_location',
                                     'NRP': 'motion_sensor_2_roll_ref_plane', 'NSD': 'motion_sensor_2_time_delay',
                                     'NSR': 'motion_sensor_2_roll_angle', 'NSP': 'motion_sensor_2_pitch_angle',
                                     'NSG': 'motion_sensor_2_heading_angle', 'GCG': 'gyrocompass_heading_offset',
                                     'MAS': 'roll_scaling_factor', 'SHC': 'transducer_depth_sound_speed_source',
                                     'PPS': '1pps_clock_sync', 'CLS': 'clock_source', 'CLO': 'clock_offset',
                                     'VSN': 'active_attitude_velocity', 'VSU': 'attitude_velocity_sensor_1_address',
                                     'VSE': 'attitude_velocity_sensor_1_port',
                                     'VTU': 'attitude_velocity_sensor_2_address',
                                     'VTE': 'attitude_velocity_sensor_2_port',
                                     'ARO': 'active_roll_pitch_sensor', 'AHE': 'active_heave_sensor',
                                     'AHS': 'active_heading_sensor', 'VSI': 'ethernet_2_address',
                                     'VSM': 'ethernet_2_network_mask', 'MCAn': 'multicast_sensor_address',
                                     'MCUn': 'multicast_sensor_port', 'MCIn': 'multicast_sensor_identifier',
                                     'MCPn': 'multicast_position_system_number', 'SNL': 'ship_noise_level',
                                     'CPR': 'cartographic_projection', 'ROP': 'responsible_operator',
                                     'SID': 'survey_identifier', 'RFN': 'raw_file_name',
                                     'PLL': 'survey_line_identifier',
                                     'COM': 'comment'}
        self.time = utctime


class MapPack:
    """Acts as a map for the location of each of the packets
    for a particular packet type for the file in question"""

    def __init__(self):
        """Makes the first entry in the array"""
        self.packdir = {}
        self.sizedir = {}

    def add(self, typ, location=0, time=0, ping=0, size=0):
        """Adds the location, time and ping to the tuple for the value type"""
        typ = typ
        store = [location, time, ping]
        if typ in self.packdir:
            self.packdir[typ].append(store)
            self.sizedir[typ] += size
        else:
            self.packdir[typ] = []
            self.packdir[typ].append(store)
            self.sizedir[typ] = size

    def finalize(self):
        for key in self.packdir.keys():
            temp = np.asarray(self.packdir[key])
            tempindx = temp[:, 1].argsort()
            self.packdir[key] = temp[tempindx, :]

    def find_nearest(self, file_loc: int, mode: str = 'next'):
        """Finds the nearest packet to the given file location in bytes"""
        cur_closest = None
        rectype = None
        recdata = None
        for typ in list(self.packdir.keys()):
            locs = self.packdir[typ][:, 0]
            if mode == 'nearest':
                diff = np.abs(locs - file_loc)
            elif mode == 'next':
                diff = locs - file_loc
                diff[diff < 0] = np.nan
            try:
                closest_index = np.nanargmin(diff)
                if (cur_closest is None) or (diff[closest_index] < cur_closest):
                    cur_closest = diff[closest_index]
                    rectype, recdata = typ, int(self.packdir[typ][closest_index, 0])
            except ValueError:
                pass
        return rectype, recdata

    def printmap(self):
        keys = []
        totalsize = 0
        for i, v in self.packdir.items():
            keys.append((i, len(v)))
            totalsize += self.sizedir[i]
        keys.sort()
        for key in keys:
            percent = 10000 * self.sizedir[str(key[0])] / totalsize
            print('message ' + str(key[0]) + ' has ' + str(key[1]) + ' packets and ' + str(round(0.01 * percent, 2)) + '% of file')

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
        outfile = open(outfilename + '.prr', 'wb')
        pickle.dump(self.packdir, outfile)
        outfile.close()
