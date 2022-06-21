"""Python Reson Reader
G.Rice 9/10/10
V0.3.9 20150107
This is intended to help trouble shoot Reson data directly from the Reson datagrams.
It was inspired by The Great Sam Greenaway during his graduate work at UNH.

Updated for Python3, Eric Younkin, DEC 2021
"""

import os, sys, struct, pickle
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta, timezone, datetime
import copy


recs_categories_7027 = {'1003': ['time', 'LatitudeNorthing', 'LongitudeEasting', 'Height'],
                        '1009': ['time', 'data.Depth', 'data.SoundSpeed'],
                        '1012': ['time', 'Roll', 'Pitch', 'Heave'],
                        '1013': ['time', 'Heading'],
                        '7001': ['serial_one', 'serial_two'],
                        '7027': ['time', 'PingNumber', 'TxAngleArray', 'RxAngle', 'Uncertainty', 'DetectionFlags',  # flags for amp/phase detect
                                 'TravelTime', 'Intensity'],
                        '7030': ['time', 'translated_settings'],
                        '7503': ['time', 'SoundVelocity', 'TXPulseTypeID', 'TransmitFlags', 'Frequency', 'BeamSpacingMode',
                                 'full_settings']}

recs_categories_translator_7027 = {'1003': {'time': [['navigation', 'time']], 'LatitudeNorthing': [['navigation', 'latitude']],
                                            'LongitudeEasting': [['navigation', 'longitude']],
                                            'Height': [['navigation', 'altitude']]},
                                   '1009': {'time': [['profile', 'time']], 'Depth': [['profile', 'depth']],
                                            'SoundSpeed': [['profile', 'soundspeed']]},
                                   '1012': {'time': [['attitude', 'time']], 'Roll': [['attitude', 'roll']],
                                            'Pitch': [['attitude', 'pitch']], 'Heave': [['attitude', 'heave']]},
                                   '1013': {'time': [['attitude', 'htime']], 'Heading': [['attitude', 'heading']]},
                                   '7001': {'serial_one': [['installation_params', 'serial_one']],
                                            'serial_two': [['installation_params', 'serial_two']]},
                                   '7027': {'time': [['ping', 'time']], 'PingNumber': [['ping', 'counter']],
                                            'TxAngleArray': [['ping', 'tiltangle']], 'RxAngle': [['ping', 'beampointingangle']],
                                            'Intensity': [['ping', 'reflectivity']],
                                            'Uncertainty': [['ping', 'qualityfactor']], 'TravelTime': [['ping', 'traveltime']],
                                            'DetectionFlags': [['ping', 'detectioninfo']]},
                                   '7030': {'time': [['installation_params', 'time']],
                                            'translated_settings': [['installation_params', 'installation_settings']]},
                                   '7503': {'time': [['runtime_params', 'time']],
                                            'SoundVelocity': [['runtime_params', 'soundspeed']],
                                            'TXPulseTypeID': [['runtime_params', 'mode']],
                                            'BeamSpacingMode': [['runtime_params', 'modetwo']],
                                            'TransmitFlags': [['runtime_params', 'yawpitchstab']],
                                            'Frequency': [['runtime_params', 'frequency']],
                                            'full_settings': [['runtime_params', 'runtime_settings']]}}

recs_categories_7027_1016 = {'1003': ['time', 'LatitudeNorthing', 'LongitudeEasting', 'Height'],
                             '1009': ['time', 'data.Depth', 'data.SoundSpeed'],
                             '1016': ['datatime', 'Roll', 'Pitch', 'Heave', 'Heading'],
                             '7001': ['serial_one', 'serial_two'],
                             '7027': ['time', 'PingNumber', 'TxAngleArray', 'RxAngle', 'Uncertainty', 'DetectionFlags',  # flags for amp/phase detect
                                      'TravelTime', 'Intensity'],
                             '7030': ['time', 'translated_settings'],
                             '7503': ['time', 'SoundVelocity', 'TXPulseTypeID', 'TransmitFlags', 'Frequency', 'BeamSpacingMode',
                                      'full_settings']}

recs_categories_translator_7027_1016 = {'1003': {'time': [['navigation', 'time']], 'LatitudeNorthing': [['navigation', 'latitude']],
                                                 'LongitudeEasting': [['navigation', 'longitude']],
                                                 'Height': [['navigation', 'altitude']]},
                                        '1009': {'time': [['profile', 'time']], 'Depth': [['profile', 'depth']],
                                                 'SoundSpeed': [['profile', 'soundspeed']]},
                                        '1016': {'datatime': [['attitude', 'time']], 'Roll': [['attitude', 'roll']],
                                                 'Pitch': [['attitude', 'pitch']], 'Heading': [['attitude', 'heading']],
                                                 'Heave': [['attitude', 'heave']]},
                                        '7001': {'Serial#': [['installation_params', 'serial_one']],
                                                 'Serial#2': [['installation_params', 'serial_two']]},
                                        '7027': {'time': [['ping', 'time']], 'PingNumber': [['ping', 'counter']],
                                                 'TxAngleArray': [['ping', 'tiltangle']], 'RxAngle': [['ping', 'beampointingangle']],
                                                 'Intensity': [['ping', 'reflectivity']],
                                                 'Uncertainty': [['ping', 'qualityfactor']], 'TravelTime': [['ping', 'traveltime']],
                                                 'DetectionFlags': [['ping', 'detectioninfo']]},
                                        '7030': {'time': [['installation_params', 'time']],
                                                 'translated_settings': [['installation_params', 'installation_settings']]},
                                        '7503': {'time': [['runtime_params', 'time']],
                                                 'SoundVelocity': [['runtime_params', 'soundspeed']],
                                                 'TXPulseTypeID': [['runtime_params', 'mode']],
                                                 'BeamSpacingMode': [['runtime_params', 'modetwo']],
                                                 'TransmitFlags': [['runtime_params', 'yawpitchstab']],
                                                 'Frequency': [['runtime_params', 'frequency']],
                                                 'full_settings': [['runtime_params', 'runtime_settings']]}}

recs_categories_result = {'attitude':  {'time': None, 'htime': None, 'roll': None, 'pitch': None, 'heave': None, 'heading': None},
                          'installation_params': {'time': None, 'serial_one': None, 'serial_two': None,
                                                  'installation_settings': None},
                          'ping': {'time': None, 'counter': None, 'tiltangle': None, 'frequency': None, 'reflectivity': None,
                                   'beampointingangle': None, 'txsector_beam': None, 'detectioninfo': None,
                                   'qualityfactor': None, 'traveltime': None},
                          'runtime_params': {'time': None, 'soundspeed': None, 'mode': None, 'modetwo': None, 'yawpitchstab': None,
                                             'frequency': None, 'runtime_settings': None},
                          'profile': {'time': None, 'depth': None, 'soundspeed': None},
                          'navigation': {'time': None, 'latitude': None, 'longitude': None, 'altitude': None}}

# Appendix B - Device identifier lookup to retrieve model number
device_identifiers = {20: 'T20', 22: 'T20Dual', 30: 'F30', 50: 'T50', 51: 'T51', 52: 'T50Dual', 103: 'GenericMBES',
                      1000: 'OdomMB1', 1002: 'OdomMB2', 4013: 'TC4013', 7003: 'PDS', 7005: 'ProScan', 7012: '7012', 7100: '7100',
                      7101: '7101', 7102: '7102', 7111: '7111', 7112: '7112', 7123: '7123', 7125: '7125', 7128: '7128',
                      7130: '7130', 7150: '7150', 7160: '7160', 8100: '8100', 8101: '8101', 8102: '8102', 8111: '8111',
                      8123: '8123', 8124: '8124', 8125: '8125', 8128: '8128', 8150: '8150', 8160: '8160', 9000: 'E20',
                      9001: 'Deso5', 9002: 'Deso5DS', 10000: 'DMS05', 10001: '335B', 10002: '332B', 10010: 'SBE37',
                      10200: 'Litton200', 11000: 'FS-DW-SBP', 11001: 'FS-DW-LFSSS', 11002: 'FS-DW-HFSSS',
                      12000: 'RPT319', 13002: 'NorbitFLS', 13003: 'NorbitBathy', 13004: 'NorbitiWBMS', 13005: 'NorbitBathyCompact',
                      13007: 'NorbitBathy', 13008: 'NorbitBathy', 13009: 'NorbitDeepSea', 13010: 'NorbitDeepSea',
                      13011: 'NorbitDeepSea', 13012: 'NorbitiLidar', 13016: 'NorbitBathySTX', 13017: 'NorbitBathySTX',
                      13018: 'NorbitiWBMSe', 14000: 'HydroSweep3DS', 14001: 'HydroSweep3MD50', 14002: 'HydroSweep3MD30'}


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
        self.filelen = self.max_filelen

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
            if cur_ptr >= self.start_ptr + self.filelen - 4:  # minus four for the seek we do to get ready for the next search
                self.eof = True
                raise ValueError('Unable to find sonar startbyte, is this sonar supported?')

            # consider start bytes right at the end of the given filelength as valid, even if they extend
            # over to the next chunk
            srchdat = self.infile.read(min(100, (self.start_ptr + self.filelen) - cur_ptr))
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

    def has_datagram(self, datagramnum, max_records: int = 50):
        """
        Search for the given datagram sequentially through the file.  A fast way of finding a datagram you expect
        at the beginning without mapping the file first.  If max records is provided, only search through that many
        records.
        """
        if not isinstance(datagramnum, list):
            datagramnum = [datagramnum]
        datagramnum = [str(dg) for dg in datagramnum]
        founddatagram = [False] * len(datagramnum)

        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        startptr = self.start_ptr

        # Read the first records till you get one that the given dtype
        found = False
        self.infile.seek(0)
        currecords = 0
        while not self.eof:
            if max_records and currecords >= max_records:
                break
            self.read()
            currecords += 1
            datagram_type = str(self.packet.dtype)
            if datagram_type in datagramnum:
                founddatagram[datagramnum.index(datagram_type)] = True
            if all(founddatagram):
                found = True
                break

        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        self.eof = False
        self.start_ptr = startptr
        return found

    def fast_read_start_end_time(self, only_start = False):
        """
        Get the start and end time for the dataset without mapping the file

        Returns
        -------
        list, [starttime: float, first time stamp in data, endtime: float, last time stamp in data]

        """
        starttime = None
        endtime = None
        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        startptr = self.start_ptr
        oldfilelen = self.filelen

        # Read the first records till you get one that has time in the packet (most recs at this point i believe)
        self.infile.seek(0)
        while starttime is None:
            self.read()
            try:
                starttime = self.packet.time
            except AttributeError:  # no time for this packet
                self.read()
                try:
                    starttime = self.packet.time
                except AttributeError:
                    raise ValueError('Prr3: Unable to read the time of the first record.')
        if starttime is None:
            raise ValueError('Prr3: Unable to find a suitable packet to read the start time of the file')
        if only_start:
            self.infile.seek(curptr)
            self.filelen = oldfilelen
            self.at_right_byte = cur_startstatus
            self.eof = False
            self.start_ptr = startptr
            return starttime, None

        # Move the start/end file pointers towards the end of the file and get the last available time
        # the last record is the file manifest, this can be huge, and you need to start reading before it.  Pick a large
        #   number that should be larger than the file manifest.  Start small, get bigger
        self.infile.seek(0, 2)
        chunks = [min(15000000, self.infile.tell()), min(30000000, self.infile.tell()), min(60000000, self.infile.tell())]
        for chunksize in chunks:
            self.at_right_byte = False
            eof = self.max_filelen
            self.start_ptr = eof - chunksize
            self.end_ptr = eof
            self.filelen = chunksize

            self.infile.seek(self.start_ptr)
            self.eof = False
            while not self.eof:
                try:
                    self.read()
                    endtime = self.packet.time
                except:
                    pass
            if endtime:
                break
        self.infile.seek(curptr)
        self.filelen = oldfilelen
        self.at_right_byte = cur_startstatus
        self.eof = False
        self.start_ptr = startptr

        return [starttime, endtime]

    def fast_read_serial_number(self):
        """
        Get the serial numbers and model number of the provided file

        Returns
        -------
        list, [serialnumber: int, secondaryserialnumber: int, sonarmodelnumber: str]

        """
        found_install_params = False
        found_modelnum = False
        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        startptr = self.start_ptr

        serialnumber = 0
        serialnumbertwo = 0
        sonarmodel = ''

        if not self.has_datagram(7001, 20):
            print('Warning: Unable to find Datagram 7001 in the first 20 records, serial number will be 0')
            found_install_params = True

        self.infile.seek(0)
        while not found_install_params or not found_modelnum:
            self.read()
            datagram_type = str(self.packet.dtype)
            if datagram_type not in ['7000', '7027', '7001']:
                continue

            if datagram_type == '7001' and not found_install_params:
                self.get()
                try:
                    serialnumber = self.packet.subpack.serial_one
                    serialnumbertwo = self.packet.subpack.serial_two
                except:
                    raise ValueError('Error: unable to find the serial number records in the Data7001 record')
                found_install_params = True
            elif datagram_type in ['7000', '7027'] and not found_modelnum:
                self.get()
                try:
                    sonarmodel = device_identifiers[self.packet.header['DeviceIdentifier']]
                except:
                    raise ValueError('Error: unable to find the translated sonar model number in the Data7027 record')
                found_modelnum = True

        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        self.eof = False
        self.start_ptr = startptr
        return [serialnumber, serialnumbertwo, sonarmodel]

    def return_empty_installparams(self, model_num: str = '', serial_num_one: int = 0, serial_num_two: int = 0):
        starttime, _ = self.fast_read_start_end_time(only_start=True)
        isets = {'sonar_model_number': model_num, 'transducer_1_vertical_location': '0.000',
                 'transducer_1_along_location': '0.000', 'transducer_1_athwart_location': '0.000',
                 'transducer_1_heading_angle': '0.000', 'transducer_1_roll_angle': '0.000',
                 'transducer_1_pitch_angle': '0.000', 'transducer_2_vertical_location': '0.000',
                 'transducer_2_along_location': '0.000', 'transducer_2_athwart_location': '0.000',
                 'transducer_2_heading_angle': '0.000', 'transducer_2_roll_angle': '0.000',
                 'transducer_2_pitch_angle': '0.000', 'position_1_time_delay': '0.000',  # seconds
                 'position_1_vertical_location': '0.000', 'position_1_along_location': '0.000',
                 'position_1_athwart_location': '0.000', 'motion_sensor_1_time_delay': '0.000',
                 'motion_sensor_1_vertical_location': '0.000', 'motion_sensor_1_along_location': '0.000',
                 'motion_sensor_1_athwart_location': '0.000', 'motion_sensor_1_roll_angle': '0.000',
                 'motion_sensor_1_pitch_angle': '0.000', 'motion_sensor_1_heading_angle': '0.000',
                 'waterline_vertical_location': '0.000', 'system_main_head_serial_number': '0',
                 'tx_serial_number': '0', 'tx_2_serial_number': '0', 'firmware_version': '',
                 'active_position_system_number': '1', 'active_heading_sensor': 'motion_1', 'position_1_datum': 'WGS84',
                 'software_version': '', 'sevenk_version': '', 'protocol_version': ''}
        finalrec = {'installation_params': {'time': np.array([starttime], dtype=float),
                                            'serial_one': np.array([serial_num_one], dtype=np.dtype('uint16')),
                                            'serial_two': np.array([serial_num_two], dtype=np.dtype('uint16')),
                                            'installation_settings': np.array([isets], dtype=np.object)}}
        return finalrec

    def _finalize_records(self, recs_to_read, recs_count, sonarmodelnumber, serialnumber):
        """
        Take output from sequential_read_records and alter the type/size/translate as needed for Kluster to read and
        convert to xarray.  Major steps include
        - adding empty arrays so that concatenation later on will work
        - translate the runtime parameters from integer/binary codes to string identifiers for easy reading (and to
             allow comparing results between different file types)
        returns: recs_to_read, dict of dicts finalized
        """
        # first check for varying number of beams
        uneven = False
        maxlen = None
        if 'ping' in recs_to_read and recs_to_read['ping']['traveltime']:
            minlen = len(min(recs_to_read['ping']['traveltime'], key=lambda x: len(x)))
            maxlen = len(max(recs_to_read['ping']['traveltime'], key=lambda x: len(x)))
            if minlen != maxlen:
                # print('prr3: Found uneven number of beams from {} to {}'.format(minlen, maxlen))
                uneven = True

        for rec in recs_to_read:
            for dgram in recs_to_read[rec]:
                if recs_count[rec] == 0:
                    if rec != 'runtime_params' or dgram == 'time':
                        # found no records, empty array
                        recs_to_read[rec][dgram] = np.zeros(0)
                    else:
                        # found no records, empty array of strings for the mode/stab records
                        recs_to_read[rec][dgram] = np.zeros(0, 'U2')
                elif rec in ['attitude', 'navigation']:  # these recs have time blocks of data in them, need to be concatenated
                    if dgram == 'altitude' and not recs_to_read[rec][dgram]:
                        pass
                    else:
                        if dgram in ['latitude', 'longitude']:
                            recs_to_read[rec][dgram] = np.rad2deg(np.array(recs_to_read[rec][dgram]))
                        elif dgram == 'heading':  # convert negative heading to 0-360deg heading
                            recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram]) % 360
                        elif dgram == 'heave':  # heave is positive up kluster wants positive down
                            recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram]) * -1
                        elif dgram == 'roll':
                            recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])
                        else:
                            recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])
                elif rec == 'ping':
                    if recs_to_read[rec][dgram] is None:  # frequency, txsector_beam are None at first
                        pass
                    elif uneven and isinstance(recs_to_read[rec][dgram][0], np.ndarray):
                        newrec = np.zeros((len(recs_to_read[rec][dgram]), maxlen), dtype=recs_to_read[rec][dgram][0].dtype)
                        for i, j in enumerate(recs_to_read[rec][dgram]):
                            newrec[i][0:len(j)] = j
                        recs_to_read[rec][dgram] = newrec
                    else:
                        recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])
                elif rec == 'runtime_params':
                    if dgram == 'yawpitchstab':
                        recs_to_read[rec][dgram] = translate_yawpitch(np.array(recs_to_read[rec][dgram]))
                    elif dgram == 'mode':
                        recs_to_read[rec][dgram] = translate_mode(np.array(recs_to_read[rec][dgram]))
                    elif dgram == 'modetwo':
                        recs_to_read[rec][dgram] = translate_mode_two(np.array(recs_to_read[rec][dgram]))
                    else:
                        recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])
                else:
                    recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])

        # heading can come from a different record, if the freq is different we address that here
        if 'htime' in recs_to_read['attitude']:
            if recs_to_read['attitude']['time'].size != recs_to_read['attitude']['htime'].size:  # get indices of nearest runtime for each ping
                hindex = np.searchsorted(recs_to_read['attitude']['htime'], recs_to_read['attitude']['time']).clip(0, recs_to_read['attitude']['htime'].size - 1)
                recs_to_read['attitude']['heading'] = recs_to_read['attitude']['heading'][hindex]
            recs_to_read['attitude'].pop('htime')

        # reconfigure the ping/runtime results to match what Kluster wants
        recs_to_read['ping']['txsector_beam'] = np.zeros(recs_to_read['ping']['detectioninfo'].shape, dtype='uint8')
        if recs_to_read['ping']['time'].size != recs_to_read['runtime_params']['time'].size:  # get indices of nearest runtime for each ping
            rindex = np.searchsorted(recs_to_read['runtime_params']['time'], recs_to_read['ping']['time']).clip(0, recs_to_read['runtime_params']['time'].size - 1)
        else:
            rindex = np.full(recs_to_read['ping']['time'].shape, True, bool)
        recs_to_read['ping']['soundspeed'] = recs_to_read['runtime_params'].pop('soundspeed')[rindex]
        recs_to_read['ping']['mode'] = recs_to_read['runtime_params'].pop('mode')[rindex]
        recs_to_read['ping']['modetwo'] = recs_to_read['runtime_params'].pop('modetwo')[rindex]
        recs_to_read['ping']['yawpitchstab'] = recs_to_read['runtime_params'].pop('yawpitchstab')[rindex]

        # shift frequency to the ping container AND expand to ping/beam dimension as Kluster expects this for multisector systems
        recs_to_read['ping']['frequency'] = recs_to_read['runtime_params'].pop('frequency')[rindex]
        recs_to_read['ping']['frequency'] = (np.ones_like(recs_to_read['ping']['qualityfactor']) * recs_to_read['ping']['frequency'][:, None])
        recs_to_read['ping']['frequency'] = recs_to_read['ping']['frequency'].astype('int32')

        recs_to_read['ping']['detectioninfo'] = translate_detectioninfo(recs_to_read['ping']['detectioninfo'])

        # empty records we expect with sector wise systems that we need to cover for Kluster
        recs_to_read['ping']['serial_num'] = np.full(recs_to_read['ping']['counter'].shape, serialnumber, dtype='uint16')
        recs_to_read['ping']['delay'] = np.full_like(recs_to_read['ping']['tiltangle'], 0.0)

        # drop the empty altitude record if it is empty
        if recs_to_read['navigation']['altitude'] is None or len(recs_to_read['navigation']['altitude']) == 0:
            recs_to_read['navigation'].pop('altitude')
        else:
            recs_to_read['navigation']['altitude'] = recs_to_read['navigation']['altitude'].astype(np.float32)

        # drop the empty reflectivity record if it is empty
        if recs_to_read['ping']['reflectivity'] is None or all(recs_to_read['ping']['reflectivity'] == None):
            recs_to_read['ping'].pop('reflectivity')
        else:
            recs_to_read['ping']['reflectivity'] = recs_to_read['ping']['reflectivity'].astype(np.float32)

        # cover the instance where there is no 7030 record for install params
        if not recs_to_read['installation_params']['time'].any():
            recs_to_read['installation_params'] = self.return_empty_installparams(sonarmodelnumber, serialnumber)['installation_params']

        recs_to_read['runtime_params']['time'] = np.array([recs_to_read['runtime_params']['time'][0]], dtype=float)
        recs_to_read['runtime_params']['runtime_settings'] = np.array(recs_to_read['runtime_params']['runtime_settings'], dtype=np.object)

        # # I do this in the other drivers, might include it later...
        #
        # for var in ['latitude', 'longitude']:
        #     dif = np.abs(np.diff(recs_to_read['navigation'][var]))
        #     spike_idx = dif >= 1  # just look for spikes greater than one degree, should cover most cases
        #     spikes = np.count_nonzero(spike_idx)
        #     remove_these = []
        #     if spikes:
        #         try:
        #             spike_index = np.where(spike_idx)[0] - 3
        #             varlength = len(recs_to_read['navigation'][var])
        #             for cnt, spk in enumerate(spike_index):
        #                 last_good = recs_to_read['navigation'][var][spk - 1]
        #                 if spk not in remove_these:
        #                     still_bad = True
        #                     idx = 1
        #                     while still_bad:
        #                         if abs(recs_to_read['navigation'][var][spk + idx] - last_good) > 1:
        #                             if (spk + idx) not in remove_these:
        #                                 remove_these.append(spk + idx)
        #                         elif idx >= 10 or (spk + idx + 1) >= varlength:
        #                             still_bad = False
        #                         idx += 1
        #         except:
        #             print('Unable to remove navigation spikes')
        #         # print('Removing {} {} spikes found in navigation record...'.format(len(remove_these), var))
        #         for rec_type in ['time', 'latitude', 'longitude', 'altitude']:
        #             if rec_type in recs_to_read['navigation']:
        #                 recs_to_read['navigation'][rec_type] = np.delete(recs_to_read['navigation'][rec_type],
        #                                                                  remove_these)

        recs_to_read['ping']['processing_status'] = np.zeros_like(recs_to_read['ping']['beampointingangle'],
                                                                  dtype=np.uint8)

        # hack here to ensure that we don't have duplicate times across chunks, modify the first time slightly.
        #   next chunk might include a duplicate time
        if recs_to_read['ping']['time'].any() and recs_to_read['ping']['time'].size > 1:
            recs_to_read['ping']['time'][0] += 0.000010

        # mask the empty beams that we add where there are no beams to get nice squared arrays.  By setting detection
        #  to rejected and traveltime to NaN, the processed data will be automatically rejected.
        if uneven:
            msk = recs_to_read['ping']['traveltime'] == 0
            recs_to_read['ping']['detectioninfo'][msk] = 2
            recs_to_read['ping']['traveltime'][msk] = np.float32(np.nan)

        # need to sort/drop uniques, keep finding duplicate times in attitude/navigation datasets
        for dset_name in ['attitude', 'navigation']:
            # first handle these cases where variables are of a different size vs time, I believe this is some issue with older datasets
            #  and the data65 record, need to determine the actual cause as the 'fix' used here is not great
            for dgram in recs_to_read[dset_name]:
                if dgram != 'time':
                    try:
                        assert recs_to_read[dset_name][dgram].shape[0] == recs_to_read[dset_name]['time'].shape[0]
                    except AssertionError:
                        dgramsize = recs_to_read[dset_name][dgram].shape[0]
                        timesize = recs_to_read[dset_name]["time"].shape[0]
                        msg = f'variable {dgram} has a length of {dgramsize}, where time has a length of {timesize}'
                        if recs_to_read[dset_name][dgram].ndim == 2:  # shouldn't be seen with attitude/navigation datasets anyway
                            raise NotImplementedError(msg + ', handling this for 2 dimensional cases is not implemented')
                        elif timesize < dgramsize:  # trim to time size
                            recs_to_read[dset_name][dgram] = recs_to_read[dset_name][dgram][:timesize]
                            print('Warning: ' + msg + f', trimming {dgram} to length {timesize}')
                        else:
                            recs_to_read[dset_name][dgram] = np.concatenate([recs_to_read[dset_name][dgram], [recs_to_read[dset_name][dgram][-1]] * (timesize - dgramsize)])
                            print('Warning: ' + msg + f', filling {dgram} by repeating last element {timesize - dgramsize} times')

            dset = recs_to_read[dset_name]
            _, index = np.unique(dset['time'], return_index=True)
            if dset['time'].size != index.size:
                # print('par3: Found duplicate times in {}, removing...'.format(dset_name))
                for var in dset:
                    dset[var] = dset[var][index]
            if not np.all(dset['time'][:-1] <= dset['time'][1:]):
                # print('par3: {} is not sorted, sorting...'.format(dset_name))
                index = np.argsort(dset['time'])
                for var in dset:
                    dset[var] = dset[var][index]
        return recs_to_read

    def sequential_read_records(self, first_installation_rec=False):
        """
        Using global recs_categories, parse out only the given datagram types by reading headers and decoding only
        the necessary datagrams.

        """
        serialnumber, serialnumbertwo, sonarmodelnumber = self.fast_read_serial_number()

        # first determine whether we need to use 1016 or the 1012/1013 pair for sensor data
        if self.has_datagram([1012, 1013], 300):
            categories = recs_categories_7027
            category_translator = recs_categories_translator_7027
        elif self.has_datagram(1016, 300):
            categories = recs_categories_7027_1016
            category_translator = recs_categories_translator_7027_1016
        else:
            raise ValueError('prr3: Attempted to read Reson s7k data using either 1012,1013 or 1016 for sensor data, unable to find either')
        has_installation_rec = self.has_datagram(7030, 20)
        if not has_installation_rec and first_installation_rec:
            return self.return_empty_installparams(sonarmodelnumber, serialnumber, serialnumbertwo)
        decoded_runtime = False

        # recs_to_read is the returned dict of records parsed from the file
        recs_to_read = copy.deepcopy(recs_categories_result)
        recs_count = dict([(k, 0) for k in recs_to_read])

        if self.start_ptr:
            self.at_right_byte = False  # for now assume that if a custom start pointer is provided, we need to seek the start byte
        self.infile.seek(self.start_ptr)
        self.eof = False
        while not self.eof:
            self.read()  # find the start of the record and read the header
            datagram_type = str(self.packet.dtype)
            if datagram_type in list(categories.keys()):  # if the header indicates this is a record you want...
                for rec_ident in list(category_translator[datagram_type].values())[0]:
                    recs_count[rec_ident[0]] += 1
                self.get()  # read the rest of the datagram and decode the data
                rec = self.packet.subpack
                if rec is not None:
                    for subrec in categories[datagram_type]:
                        #  override for nested recs, designated with periods in the recs_to_read dict
                        if subrec.find('.') > 0:
                            tmprec = getattr(rec, subrec.split('.')[0])
                            subrec = subrec.split('.')[1]
                        else:
                            tmprec = rec

                        val = None
                        if subrec == 'translated_settings':
                            val = [getattr(tmprec, subrec)]
                        elif subrec == 'Height' and tmprec is None:  # handle case where gg_data is not found
                            val = [np.nan]
                        elif subrec == 'full_settings':
                            if not decoded_runtime:
                                val = [getattr(tmprec, subrec)]
                                decoded_runtime = True
                            else:
                                continue
                        else:
                            try:  # flow for array/list attribute
                                val = list(getattr(tmprec, subrec))
                            except TypeError:  # flow for float/int attribute
                                try:
                                    val = [getattr(tmprec, subrec)]
                                except ValueError:  # it just isn't there
                                    print('prr3: Unable to read {}: {} - {}'.format(datagram_type, tmprec, subrec))
                                    val = []
                            except AttributeError:  # flow for nested recs
                                try:
                                    val = [tmprec[subrec]]
                                except (TypeError, ValueError):  # it just isn't there
                                    print('prr3: Unable to read {}: {} - {}'.format(datagram_type, tmprec, subrec))
                                    val = []

                        # generate new list or append to list for each rec of that dgram type found
                        for translated in category_translator[datagram_type][subrec]:
                            if recs_to_read[translated[0]][translated[1]] is None:
                                recs_to_read[translated[0]][translated[1]] = copy.copy(val)
                            else:
                                recs_to_read[translated[0]][translated[1]].extend(val)

            if datagram_type == '7030' and first_installation_rec:
                self.eof = True
        recs_to_read = self._finalize_records(recs_to_read, recs_count, sonarmodelnumber, serialnumber)
        recs_to_read['format'] = 's7k'
        return recs_to_read


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
            if self.dtype == 7030:
                self.subpack = dgram(self.datablock, self.time, self.header['DeviceIdentifier'])
            else:
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
         def __init__(self, datablock):
            super(Data003, self).__init__(datablock)
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

    def __init__(self, datablock, read_limit=1):
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
        except KeyError:
            raise AttributeError(key + " not in " + str(self.__class__))

    def __setattr__(self, key, value):  # Get the value from the underlying subfield (perform any conversion necessary)
        try:
            ky2 = self._data_keys[key]  # try to access the subfield
        except KeyError:
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

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1000, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime


class Data1003(BaseData):
    """
    Position Datagram
    """
    hdr_dtype = np.dtype([('DatumIdentifier', 'u4'), ('Latency', 'f4'), ('LatitudeNorthing', 'f8'),
                          ('LongitudeEasting', 'f8'), ('Height', 'f8'), ('PositionFlag', 'u1'), ('UtmZone', 'u1'),
                          ('QualityFlag', 'u1'), ('PositionMethod', 'u1'), ('NumberOfSatellites', 'u1')])

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        if len(datablock) == 37:  # it includes numberofsatellites
            super(Data1003, self).__init__(datablock, read_limit=read_limit)
        elif len(datablock) == 36:
            self.hdr_dtype = np.dtype([('DatumIdentifier', 'u4'), ('Latency', 'f4'), ('LatitudeNorthing', 'f8'),
                                       ('LongitudeEasting', 'f8'), ('Height', 'f8'), ('PositionFlag', 'u1'),
                                       ('UtmZone', 'u1'), ('QualityFlag', 'u1'), ('PositionMethod', 'u1')])
            self.hdr_sz = self.hdr_dtype.itemsize
            super(Data1003, self).__init__(datablock, read_limit=read_limit)
        else:
            raise NotImplementedError('prr3: Found a Data1003 datablock that is neither 36 nor 37 long, not sure what it is')
        self.time = utctime


class Data1008(BaseData):
    """
    Depth Datagram
    """
    hdr_dtype = np.dtype([('DepthDescriptor', 'u1'), ('CorrectionFlag', 'u1'), ('Reserved', 'u2'),
                          ('Depth', 'f4')])

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1008, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime


class Data1009(BaseData):
    """
    Sound Velocity Profile Datagram
    """
    hdr_dtype = np.dtype([('PositionFlag', 'u1'), ('ReservedOne', 'u1'), ('ReservedTwo', 'u2'),
                          ('Latitude', 'f8'), ('Longitude', 'f8'), ('NumberOfLayers', 'u4')])

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1009, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data1010, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1012, self).__init__(datablock, read_limit=read_limit)
        self.Roll = np.rad2deg(self.Roll)
        self.Pitch = np.rad2deg(self.Pitch)
        self.time = utctime


class Data1013(BaseData):
    """
    Heading Datagram
    """
    hdr_dtype = np.dtype([('Heading', 'f4')])

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1013, self).__init__(datablock, read_limit=read_limit)
        self.Heading = np.rad2deg(self.Heading)
        self.time = utctime


class Data1015(BaseData):
    """
    Navigation Datagram if logged via PDS, otherwise you should get the 1003 Position record
    """
    hdr_dtype = np.dtype([('VerticalReference', 'u1'), ('Latitude', 'f8'), ('Longitude', 'f8'),
                          ('HorizontalPositionAccuracy', 'f4'), ('VesselHeight', 'f4'), ('HeightAccuracy', 'f4'),
                          ('SpeedOverGround', 'f4'), ('CourseOverGround', 'f4'), ('Heading', 'f4')])

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1015, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime


class Data1016(BaseData):
    """
    Attitude Datagram if logged via PDS, otherwise you should get the 1012 RollPitchHeave record
    """
    hdr_dtype = np.dtype([('NumberOfDatasets', 'u1')])

    def __init__(self, datablock, utctime, read_limit=1):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1016, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime
        self.datatime = None
        self.Roll = None
        self.Pitch = None
        self.Heave = None
        self.Heading = None
        self.numrecords = self.header['NumberOfDatasets']
        self.read_data(datablock[self.hdr_sz:])

    def read_data(self, datablock):
        data_dtype = np.dtype([('TimeOffset', 'u2'), ('Roll', 'f4'), ('Pitch', 'f4'), ('Heave', 'f4'), ('Heading', 'f4')])
        data = np.frombuffer(datablock, dtype=data_dtype, count=self.numrecords)
        self.datatime = (data['TimeOffset'] / 1000) + self.time
        self.Roll = np.rad2deg(data['Roll'])
        self.Pitch = np.rad2deg(data['Pitch'])
        self.Heave = data['Heave']
        self.Heading = np.rad2deg(data['Heading'])


class Data1020(BaseData):
    """
    Sonar Installation Identifiers
    """
    hdr_dtype = np.dtype([('SystemIdentificationNumber', 'u4'), ('TransmitterID', 'u4'), ('ReceiverID', 'u4'),
                          ('StandardConfigurationOOptions', 'u4'), ('ConfigurationFixedParameters', 'u4'),
                          ('TxLength', 'f4'), ('TxWidth', 'f4'), ('TxHeight', 'f4'), ('TxRadius', 'f4'),
                          ('SRPtoTxX', 'f4'), ('SRPtoTxY', 'f4'), ('SRPtoTxZ', 'f4'),
                          ('TxRoll', 'f4'), ('TxPitch', 'f4'), ('TxYaw', 'f4'),
                          ('RxLength', 'f4'), ('RxWidth', 'f4'), ('RxHeight', 'f4'), ('RxRadius', 'f4'),
                          ('SRPtoRxX', 'f4'), ('SRPtoRxY', 'f4'), ('SRPtoRxZ', 'f4'),
                          ('RxRoll', 'f4'), ('RxPitch', 'f4'), ('RxYaw', 'f4'),
                          ('Frequency', 'f4'), ('VRPtoSRPX', 'f4'), ('VRPtoSRPY', 'f4'), ('VRPtoSRPZ', 'f4'),
                          ('CableLength', 'f4'), ('Reserved', '44u1')])

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data1020, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7000, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime
        self.settings = None
        self.translate_settings()

    def translate_settings(self):
        self.settings = {}


class Data7001(BaseData):
    """
    Configuration record, generated on system startup, does not change during operation
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('NumberOfDevices', 'u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7001, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime
        self.device_header = np.dtype([('DeviceIdentifier', 'u4'), ('DeviceDescription', 'S60'), ('DeviceAlphaDataCard', 'u4'),
                                       ('DeviceSerialNumber', 'u8'), ('DeviceInfoLength', 'u4')])
        self.devices = []
        self.serial_one = 0
        self.serial_two = 0
        self.read_data(datablock[self.hdr_sz:])

    def read_data(self, datablock):
        numdevices = self.header[1]
        data_sz = self.device_header.itemsize
        datapointer = 0
        if not numdevices:
            print('Warning: Unable to find hardware devices in Datagram 7001, serial number is unknown.')
        for i in range(numdevices):
            device_data = list(np.frombuffer(datablock[datapointer:datapointer + data_sz], dtype=self.device_header)[0])
            datapointer += data_sz
            variable_length = device_data[-1]
            info_data = list(np.frombuffer(datablock[datapointer: datapointer + variable_length], np.dtype([('DeviceInfo', f'S{variable_length}')]))[0])
            datapointer += variable_length
            device_data += info_data
            # descrp looks something like this in its raw state, 'SN3521033\x001\x000\x003\x003'
            # we just want the integers
            # sometimes it is just 'n/a', so we just leave serial number attributes as zero
            descrp = device_data[1].decode()
            trimmed_descrp = descrp if descrp[:2] != 'SN' else descrp[2:]
            serialnum = ''
            for descrpchar in trimmed_descrp:
                try:
                    serialnum += str(int(descrpchar))
                except ValueError:
                    break

            if serialnum:  # if n/a, this is empty string
                if i == 0:
                    self.serial_one = serialnum
                elif i == 1:
                    self.serial_two = serialnum
                else:
                    print('WARNING: Found a sonar with more than two devices, which is not supported in Kluster')
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

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7002, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime


class Data7004BeamsNew(BaseData):
    """
    The by-beam variables within 7004
    Expects you to update hdr_dtype from the Data7004 before initialization
    """
    hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', 'f'), ('BeamHorizontalDirectionAngle', 'f'),
                          ('BeamWidthAlongTrack', 'f'), ('BeamWidthAcrossTrack', 'f'), ('TxDelay', 'f')])

    def __init__(self, datablock, read_limit=None):
        super(Data7004BeamsNew, self).__init__(datablock, read_limit=read_limit)


class Data7004BeamsOld(BaseData):
    """
    The by-beam variables within 7004
    Expects you to update hdr_dtype from the Data7004 before initialization
    """
    hdr_dtype = np.dtype([('BeamVerticalDirectionAngle', 'f4'), ('BeamHorizontalDirectionAngle', 'f4'),
                          ('BeamWidthAlongTrack', 'f4'), ('BeamWidthAcrossTrack', 'f4')])

    def __init__(self, datablock, read_limit=None):
        super(Data7004BeamsOld, self).__init__(datablock, read_limit=read_limit)


class Data7004(BaseData):
    """
    Beam Geometry
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('NumberOfBeams', 'u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7004, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, read_limit=None):
        super(Data7006Beams, self).__init__(datablock, read_limit=read_limit)


class Data7006(BaseData):
    """
    SUPERSEDED BY 7027
    Bathymetric Data, sonar bottom detection results
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultiPingSequence', 'u2'), ('NumberOfBeams', 'u4'),
                          ('Flags', 'u1'), ('SoundVelocityFlag', 'u1'), ('SoundVelocity', 'f4')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7006, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, read_limit=None):
        super(Data7007Beams, self).__init__(datablock, read_limit=read_limit)


class Data7007(BaseData):
    """
    Side Scan Record
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultiPingSequence', 'u2'), ('BeamPosition', 'f4'),
                          ('ControlFlags', 'u4'), ('SamplesPerSide', 'u4'), ('NadirDepth', 'u4'), ('Reserved', '7f4'),
                          ('NumberOfBeams', 'u2'), ('CurrentBeamNumber', 'u2'), ('NumberOfBytes', 'u1'), ('DataTypes', 'u1')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7007, self).__init__(datablock, read_limit=read_limit)
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
            print(f'Datagram 7007: Unexpected Datablock size, {len(datablock)} not equal to {self.numbeams} * {self.numbytes} * 2')
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

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7008, self).__init__(datablock, read_limit=read_limit)
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
        # elementflag = (28672 & fmt_flags) >> 12
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
            plt.imshow(20 * np.log10(mg), aspect='auto')
            plt.title('7008 20*log10*Magnitude')
            plt.xlabel('Beam number')
            plt.ylabel('Sample number in window')
            plt.colorbar()
        if self.phase is not None:
            plt.figure()
            plt.imshow(self.phase, aspect='auto')
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

    def __init__(self, datablock, read_limit=None):
        super(Data7010Beams, self).__init__(datablock, read_limit=read_limit)


class Data7010(BaseData):
    """
    TVG Values, one for each sample in the ping
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Samples', 'u4'), ('Reserved', '8u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7010, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7012, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7014, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, read_limit=1):
        super(Data7021Board, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7021, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7022, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime


class Data7027(BaseData):
    """
    Raw Detection Data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Detections', 'u4'), ('DataFieldSize', 'u4'), ('DetectionAlgorithm', 'u1'), ('Flags', 'u4'),
                          ('SamplingRate', 'f4'), ('TxAngle', 'f4'), ('AppliedRoll', 'f4'), ('Reserved', '15u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7027, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime
        self.numdetections = self.header[3]
        self.data = None
        self.TxAngleArray = None
        self.RxAngle = None
        self.Uncertainty = None
        self.TravelTime = None
        self.DetectionFlags = None
        self.Intensity = None
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        newdetect_dtype = np.dtype([('BeamDescriptor', 'u2'), ('DetectionPoint', 'f4'), ('RxAngle', 'f4'), ('DetectionFlags', 'u4'),
                                    ('Quality', 'u4'), ('Uncertainty', 'f4'), ('Intensity', 'f4'), ('MinLimit', 'f4'), ('MaxLimit', 'f4')])
        # from reson dfd 2.41
        olddetect_dtype = np.dtype([('BeamDescriptor', 'u2'), ('DetectionPoint', 'f4'), ('RxAngle', 'f4'), ('DetectionFlags', 'u4'),
                                    ('Quality', 'u4'), ('Uncertainty', 'f4'), ('SignalStrength', 'f4')])
        # from reson dfd 2.20
        evenolderdetect_dtype = np.dtype([('BeamDescriptor', 'u2'), ('DetectionPoint', 'f4'), ('RxAngle', 'f4'), ('DetectionFlags', 'u4'),
                                          ('Quality', 'u4'), ('Uncertainty', 'f4')])
        decoded = False
        for dtyp in [newdetect_dtype, olddetect_dtype, evenolderdetect_dtype]:
            if dtyp.itemsize * self.numdetections == len(datablock):
                self.data = np.frombuffer(datablock, dtype=dtyp, count=self.numdetections)
                decoded = True
        if not decoded:
            raise ValueError('Data7027: Unable to decode datagram, tried all known data format definitions for this datagram')
        # June2022/EY - beam angles are always negative to positive in 7027, I find this to be the opposite of what the Reson
        # convention should be (port + up).  multiplying by neg one appears to resolve this issue.  Not sure why this is.
        self.RxAngle = [np.rad2deg(self.data['RxAngle']) * -1]
        self.TxAngleArray = [np.full(self.data['RxAngle'].size, self.TxAngle, dtype=np.float32)]
        self.Uncertainty = [self.data['Uncertainty']]
        self.TravelTime = [self.data['DetectionPoint'] / self.SamplingRate]
        self.DetectionFlags = [self.data['DetectionFlags']]
        if 'Intensity' in self.data.dtype.names:
            self.Intensity = [self.data['Intensity']]


class Data7028(BaseData):
    """
    Snippet Data, sonar snippet imagery data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Detections', 'u2'), ('ErrorFlags', 'u1'), ('ControlFlags', 'u1'), ('Flags', 'u4'),
                          ('SamplingRate', 'f4'), ('Reserved', '5u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7028, self).__init__(datablock, read_limit=read_limit)
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


class Data7030(BaseData):
    """
    Sonar Installation Parameters
    """
    hdr_dtype = np.dtype([('Frequency', 'f4'), ('LengthFirmwareVersion', 'u2'), ('FirmwareVersion', '128u1'), ('LengthSoftwareVersion', 'u2'),
                          ('SoftwareVersion', '128u1'), ('LengthSevenkSoftwareVersion', 'u2'), ('SevenkSoftwareVersion', '128u1'),
                          ('LengthProtocolVersion', 'u2'), ('ProtocolVersion', '128u1'), ('TransmitX', 'f4'), ('TransmitY', 'f4'),
                          ('TransmitZ', 'f4'), ('TransmitRoll', 'f4'), ('TransmitPitch', 'f4'), ('TransmitHeading', 'f4'),
                          ('ReceiveX', 'f4'), ('ReceiveY', 'f4'), ('ReceiveZ', 'f4'), ('ReceiveRoll', 'f4'), ('ReceivePitch', 'f4'),
                          ('ReceiveHeading', 'f4'), ('MotionX', 'f4'), ('MotionY', 'f4'), ('MotionZ', 'f4'), ('MotionRoll', 'f4'),
                          ('MotionPitch', 'f4'), ('MotionHeading', 'f4'), ('MotionTimeDelay', 'u2'), ('PositionX', 'f4'),
                          ('PositionY', 'f4'), ('PositionZ', 'f4'), ('PositionTimeDelay', 'u2'), ('Waterline', 'f4')])

    def __init__(self, datablock, utctime, device_id: int, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7030, self).__init__(datablock, read_limit=read_limit)
        self.deviceid = device_id
        self.time = utctime
        self.translated_firmwareversion = ''.join([chr(i) for i in self.FirmwareVersion[0] if i != 0])
        self.translated_softwareversion = ''.join([chr(i) for i in self.SoftwareVersion[0] if i != 0])
        self.translated_7kversion = ''.join([chr(i) for i in self.SevenkSoftwareVersion[0] if i != 0])
        self.translated_protocolversion = ''.join([chr(i) for i in self.ProtocolVersion[0] if i != 0])

        self.translated_settings = None
        self.translate_settings()

    def _format_num(self, rawnum: float):
        if rawnum == 0:
            return '0.000'
        else:
            return "{:.3f}".format(round(float(rawnum), 3))

    def translate_settings(self):
        try:
            modelnum = device_identifiers[self.deviceid]
        except:
            print(f'Data7030: Unrecognized device identifier: {self.deviceid}')
            modelnum = 'Unknown'
        # translated settings will be in the Kongsberg convention, which is what Kluster follows.  Flip the x/y and the z sign convention.
        self.translated_settings = {'sonar_model_number': modelnum, 'transducer_1_vertical_location': self._format_num(-self.TransmitZ),
                                    'transducer_1_along_location': self._format_num(self.TransmitY), 'transducer_1_athwart_location': self._format_num(self.TransmitX),
                                    'transducer_1_heading_angle': self._format_num(self.TransmitHeading), 'transducer_1_roll_angle': self._format_num(np.rad2deg(self.TransmitRoll)),
                                    'transducer_1_pitch_angle': self._format_num(np.rad2deg(self.TransmitPitch)), 'transducer_2_vertical_location': self._format_num(-self.ReceiveZ),
                                    'transducer_2_along_location': self._format_num(self.ReceiveY), 'transducer_2_athwart_location': self._format_num(self.ReceiveX),
                                    'transducer_2_heading_angle': self._format_num(np.rad2deg(self.ReceiveHeading)), 'transducer_2_roll_angle': self._format_num(np.rad2deg(self.ReceiveRoll)),
                                    'transducer_2_pitch_angle': self._format_num(np.rad2deg(self.ReceivePitch)), 'position_1_time_delay': self._format_num(self.PositionTimeDelay * 1000),  # seconds
                                    'position_1_vertical_location': self._format_num(-self.PositionZ), 'position_1_along_location': self._format_num(self.PositionY),
                                    'position_1_athwart_location': self._format_num(self.PositionX), 'motion_sensor_1_time_delay': self._format_num(self.MotionTimeDelay * 1000),
                                    'motion_sensor_1_vertical_location': self._format_num(-self.MotionZ), 'motion_sensor_1_along_location': self._format_num(self.MotionY),
                                    'motion_sensor_1_athwart_location': self._format_num(self.MotionX), 'motion_sensor_1_roll_angle': self._format_num(np.rad2deg(self.MotionRoll)),
                                    'motion_sensor_1_pitch_angle': self._format_num(np.rad2deg(self.MotionPitch)), 'motion_sensor_1_heading_angle': self._format_num(np.rad2deg(self.MotionHeading)),
                                    'waterline_vertical_location': self._format_num(-self.Waterline), 'system_main_head_serial_number': '0',
                                    'active_position_system_number': '1', 'active_heading_sensor': 'motion_1', 'position_1_datum': 'WGS84',
                                    'tx_serial_number': '0', 'tx_2_serial_number': '0', 'firmware_version': self.translated_firmwareversion,
                                    'software_version': self.translated_softwareversion, 'sevenk_version': self.translated_7kversion,
                                    'protocol_version': self.translated_protocolversion}


class Data7041(BaseData):
    """
    Compressed Beamformed Intensity Data
    """
    hdr_dtype = np.dtype([('SonarID', 'u8'), ('PingNumber', 'u4'), ('MultipingSequence', 'u2'),
                          ('Beams', 'u2'), ('Flags', 'u2'), ('SampleRate', 'f4'), ('Reserved', '4u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        super(Data7041, self).__init__(datablock, read_limit=read_limit)
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

    def __init__(self, datablock, utctime, read_limit=None):
        super(Data7200, self).__init__(datablock, read_limit=read_limit)
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


class Data7300(BaseData):
    """
    File Catalog Record
    """

    hdr_dtype = np.dtype([('Size', 'u4'), ('Version', 'u2'), ('NumberofRecords', 'u4'), ('Reserved', 'u4')])

    def __init__(self, datablock, utctime, read_limit=1):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data7300, self).__init__(datablock, read_limit=read_limit)
        self.time = utctime
        self.data = None
        self.numrecords = self.header['NumberofRecords']
        self.read_data(datablock[self.hdr_sz:])

    def read_data(self, datablock):
        data_dtype = np.dtype([('Size', 'u4'), ('Offset', 'u8'), ('RecordType', 'u2'), ('DeviceIdentifier', 'u2'),
                               ('SystemEnumerator', 'u2'), ('Year', 'u2'), ('Day', 'u2'), ('Seconds', 'f4'),
                               ('Hours', 'u1'), ('Minutes', 'u1'), ('RecordCount', 'u4'), ('Reserved', '8u2')])
        self.data = np.frombuffer(datablock, dtype=data_dtype, count=self.numrecords)


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

    def __init__(self, datablock, utctime, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        if len(datablock) == 268:  # some versions will not have the last two entries
            super(Data7503, self).__init__(datablock, read_limit=read_limit)
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
            super(Data7503, self).__init__(datablock, read_limit=read_limit)
            self.time = utctime
            self.ky_data7503_translator = {'SonarID': 'sonar_id', 'SampleRate': 'sample_rate_hertz',
                                           'ReceiverBandwidth': 'receiver_bandwidth_3db_hertz', 'TXPulseWidth': 'tx_pulse_width_seconds',
                                           'TXPulseTypeID': 'tx_pulse_type_id', 'TXPulseEnvelope': 'tx_pulse_envelope_identifier',
                                           'TXPulseEnvelopeParameter': 'tx_pulse_envelope_parameter', 'TXPulseMode': 'tx_single_multiping_mode',
                                           'MaxPingRate': 'maximum_ping_rate_per_second', 'PingPeriod': 'ping_period_seconds',
                                           'RangeSelection': 'range_selection_meters', 'PowerSelection': 'power_selection_db_re_1micropascal',
                                           'GainSelection': 'gain_selection_db', 'ProjectorIdentifier': 'projector_selection',
                                           'ProjectorBeamWeightingWindowType': 'projector_weighting_window_type',
                                           'HydrophoneIdentifier': 'hydrophone_identifier', 'ReceiveBeamWeightingWindow': 'receiver_weighting_window_type',
                                           'BottomDetectionFilterMinRange': 'bottom_detect_filter_min_range',
                                           'BottomDetectionFilterMaxRange': 'bottom_detect_filter_max_range',
                                           'BottomDetectionFilterMinDepth': 'bottom_detect_filter_min_depth',
                                           'BottomDetectionFilterMaxDepth': 'bottom_detect_filter_max_depth',
                                           'Absorption': 'absorption_db_km', 'SoundVelocity': 'sound_velocity_meters_per_sec',
                                           'Spreading': 'spreading_loss_db', 'VernierOperationMode': 'vernier_operation_mode',
                                           'AutomaticFilterWindow': 'automatic_filter_window_size_percent_depth',
                                           'HeadTiltX': 'head_tilt_acrosstrack', 'HeadTiltY': 'head_tilt_alongtrack',
                                           'PingState': 'ping_state', 'BeamSpacingMode': 'beam_spacing_mode',
                                           'SonarSourceMode': 'sonar_source_mode', 'AdaptiveGateBottomMinDepth': 'adaptive_gate_min_depth',
                                           'AdaptiveGateBottomMaxDepth': 'adaptive_gate_max_depth', 'TriggerOutWidth': 'trigger_out_width',
                                           'TriggerOutOffset': 'trigger_out_offset', 'EightSeriesProjectorSelection': 'eight_series_projector_selection',
                                           'EightSeriesAlternateGain': 'eight_series_alternate_gain_db', 'VernierFilter': 'vernier_filter_settings',
                                           'CustomBeams': 'custom_beams', 'CoverageAngle': 'coverage_angle_radians', 'CoverageMode': 'coverage_mode',
                                           'QualityFilterFlags': 'quality_filter_enabled', 'HorizontalReceiverBeamSteeringAngle': 'receiver_beam_steering_angle_radians',
                                           'FlexModeSectorCoverage': 'flexmode_coverage_sector_radians', 'FlexModeSectorSteering': 'flexmode_steering_angle_radians',
                                           'ConstantSpacing': 'constant_beam_spacing_meters', 'BeamModeSelection': 'sonar_xml_beam_mode_index',
                                           'DepthGateTilt': 'depth_gate_tilt_angle_radians', 'AppliedFrequency': 'transmit_frequency_slider'}
            self.ky_data7503_val_translator = {'TXPulseTypeID': {0: 'CW', 1: 'FM'},
                                               'TXPulseEnvelope': {0: 'tapered_rectangular', 1: 'tukey', 2: 'hamming', 3: 'han', 4: 'rectangular'},
                                               'TXPulseMode': {1: 'single_ping', 2: 'multiping2', 3: 'multiping3', 4: 'multiping4'},
                                               'ProjectorBeamWeightingWindowType': {0: 'rectangular', 1: 'chebychev'},
                                               'ReceiveBeamWeightingWindow': {0: 'chebychev', 1: 'kaiser'},
                                               'PingState': {0: 'disabled', 1: 'enabled', 2: 'externally_triggered'},
                                               'BeamSpacingMode': {1: 'equiangle', 2: 'equidistant', 3: 'flex', 4: 'intermediate'},
                                               'SonarSourceMode': {0: 'normal', 1: 'autopilot', 2: 'calibration'},
                                               'EightSeriesProjectorSelection': {0: 'stick', 1: 'main_array', 2: 'extended_range'},
                                               'CoverageMode': {0: 'reduce_spacing', 1: 'reduce_beams'},
                                               'QualityFilterFlags': {0: 'disabled', 1: 'enabled'}}

    @property
    def control_flags(self):
        """
        Return the translated control flags
        """
        settings = {}
        if 'ControlFlags' in self.header.dtype.names:
            data = self.header['ControlFlags'][0]
            binctrl = format(data, '#034b')  # convert to binary, string length 34 to account for the leading '0b' and 32 bits
            settings['auto_range_method'] = str(int(binctrl[-4:], 2))
            settings['auto_bottom_detection_filter_method'] = str(int(binctrl[-8:-4], 2))
            settings['bottom_detection_range_filter_enabled'] = str(bool(int(binctrl[-9], 2)))
            settings['bottom_detection_depth_filter_enabled'] = str(bool(int(binctrl[-10], 2)))
            settings['receiver_gain_autogain'] = str(bool(int(binctrl[-11], 2)))
            settings['receiver_gain_fixedgain'] = str(bool(int(binctrl[-12], 2)))
            settings['trigger_out_high'] = str(bool(int(binctrl[-15], 2)))
            settings['system_active'] = str(bool(int(binctrl[-16], 2)))
            settings['adaptive_search_window_passive'] = str(bool(int(binctrl[-20], 2)))
            settings['pipe_gating_filter_enabled'] = str(bool(int(binctrl[-21], 2)))
            settings['adaptive_gate_depth_filter_fixed'] = str(bool(int(binctrl[-22], 2)))
            settings['adaptive_gate_enabled'] = str(bool(int(binctrl[-23], 2)))
            settings['adaptive_gate_depth_filter_enabled'] = str(bool(int(binctrl[-24], 2)))
            settings['trigger_out_enabled'] = str(bool(int(binctrl[-25], 2)))
            settings['trigger_in_edge_negative'] = str(bool(int(binctrl[-26], 2)))
            settings['pps_edge_negative'] = str(bool(int(binctrl[-27], 2)))
            settings['timestamp_state_ok'] = str(int(binctrl[-29:-27], 2) == 3)
            settings['depth_filter_follow_seafloor'] = str(bool(int(binctrl[-30], 2)))
            settings['reduced_coverage_for_constant_spacing'] = str(bool(int(binctrl[-31], 2)))
            settings['is_simulator'] = str(bool(int(binctrl[-32], 2)))
        return settings

    @property
    def receive_flags(self):
        """
        Return the translated receive flags
        """
        settings = {}
        if 'ReceiveFlags' in self.header.dtype.names:
            data = self.header['ReceiveFlags'][0]
            binctrl = format(data, '#034b')  # convert to binary, string length 34 to account for the leading '0b' and 32 bits
            settings['roll_compensation_indicator'] = str(bool(int(binctrl[-1], 2)))
            settings['heave_compensation_indicator'] = str(bool(int(binctrl[-3], 2)))
            settings['dynamic_focusing_method'] = str(int(binctrl[-8:-4], 2))
            settings['doppler_compensation_method'] = str(int(binctrl[-12:-8], 2))
            settings['match_filtering_method'] = str(int(binctrl[-16:-12], 2))
            settings['tvg_method'] = str(int(binctrl[-20:-16], 2))
            settings['multi_ping_number_of_pings'] = str(int(binctrl[-24:-20], 2))
        return settings

    @property
    def offsets_and_angles(self):
        """
        Return the translated offsets, angles in a format that matches our Kluster/Kongsberg format.  We do some math to get
        us to the arrays rel ref point.  Also add in some blank entries for angles, IMU location that we use in Kluster.
        """
        settings = {}
        # Reson - X = Across, Y = Along, Z = Vertical
        # Reson reference point is the center of the receiver in (x, z) directions, and center of transmitter in y direction
        if 'TxArrayPositionOffsetY' in self.header.dtype.names:  # along ship offset from center of RX to center of TX
            data = self.header['TxArrayPositionOffsetY'][0]
            # this is the TX offset from the sonar reference point
            settings['transducer_1_along_refpt_offset'] = '0.0'  # TX Along is always 0 (see ref point)
            # this is the RX offset from the sonar reference point
            settings['transducer_2_along_refpt_offset'] = str(round(-float(data), 3))  # RX Along is the reverse of (center of rx to center of tx, center of tx is the rp)
        else:
            print('prr3: Expected TxArrayPositionOffsetY in Data7503, unable to build offsets')
        if 'TxArrayPositionOffsetX' in self.header.dtype.names:  # across ship offset from center of RX to center of TX
            data = self.header['TxArrayPositionOffsetX'][0]
            settings['transducer_1_athwart_refpt_offset'] = str(round(float(data), 3))  # TX Across is (center of rx to center of tx, center of rx is the rp)
            settings['transducer_2_athwart_refpt_offset'] = '0.000'  # RX Across is always 0 (see ref point)
        else:
            print('prr3: Expected TxArrayPositionOffsetX in Data7503, unable to build offsets')
        if 'TxArrayPositionOffsetZ' in self.header.dtype.names:  # vertical ship offset from center of RX to center of TX
            settings['transducer_1_vertical_refpt_offset'] = str(round(-float(data), 3))  # TX Down is the reverse (to make it positive down) of (center of rx to center of tx, center of rx is the rp)
            settings['transducer_2_vertical_refpt_offset'] = '0.000'  # RX Offset is always 0 (see ref point)
        else:
            print('prr3: Expected TxArrayPositionOffsetZ in Data7503, unable to build offsets')
        return settings

    @property
    def full_settings(self):
        """
        Return the dict that includes all the useful entries in the 7503 record translated so that you can understand them
        """
        settings = self.offsets_and_angles
        settings.update(self.control_flags)
        settings.update(self.receive_flags)
        for entry in self.header.dtype.names:
            data = self.header[entry][0]
            if entry in self.ky_data7503_translator:
                newkey = self.ky_data7503_translator[entry]
                if entry in self.ky_data7503_val_translator:
                    try:
                        data = self.ky_data7503_val_translator[entry][data]
                    except KeyError:
                        pass
                settings[newkey] = str(data)
        return settings


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
        diff = None
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


def translate_yawpitch(arr):
    """
    Translate the binary code to a string identifier

    'yawandpitchstabilization' = 'Y' for Yaw stab, 'P' for pitch stab, 'PY' for both, 'N' for neither
    # xxxx0000 no pitch stab, any other means pitch stabilized
    # 0000xxxx no yaw stab, any other means yaw stab
    """
    rslt = np.full(arr.shape, 'N', dtype='U2')
    pstab = np.bitwise_and(arr, 15).astype(bool)
    ystab = np.bitwise_and(arr, 240).astype(bool)

    rslt[pstab] = 'P'
    rslt[ystab] = 'Y'
    rslt[np.logical_and(pstab, ystab)] = 'PY'

    return rslt


def translate_mode(arr):
    """
    Translate the integer code to a string identifier

    'mode' = 'CW' for continuous waveform, 'FM' for frequency modulated, 'MP' for Multi-Ping
    0 for CW, 1 for FM, 2 or 3 for MP

    """
    rslt = np.full(arr.shape, '', dtype='U2')
    rslt[arr == 0] = 'CW'
    rslt[arr == 1] = 'FM'
    rslt[arr == 2] = 'MP'
    rslt[arr == 3] = 'MP'

    return rslt


def translate_mode_two(arr):
    """
    Translate the integer code to a string identifier

    1 = Equiangle (EqAn), 2 = EquiDistant (EqDs), 3 = Flex (Flex), 4 = Intermediate (Intr)

    """
    rslt = np.full(arr.shape, '', dtype='U4')
    rslt[arr == 1] = 'EqAn'
    rslt[arr == 2] = 'EqDs'
    rslt[arr == 3] = 'Flex'
    rslt[arr == 4] = 'Intr'

    return rslt


def translate_detectioninfo(arr):
    """
    Translate the binary code to an int identifier
    'detectioninfo' = 0 for amplitude detect, 1 for phase detect, 2 for rejected due to invalid detection

    xxxxxxx0 = amplitude detect, xxxxxxx1 = phase detect
    """

    rslt = np.zeros(arr.shape, dtype=int)
    if rslt.size == 0:
        return rslt

    first_bit_chk = np.bitwise_and(arr, (1 << 0)).astype(bool)
    sec_bit_chk = np.bitwise_and(arr, (1 << 1)).astype(bool)

    rslt[np.where(sec_bit_chk)] = 1
    rslt[np.where(first_bit_chk)] = 0
    return rslt
