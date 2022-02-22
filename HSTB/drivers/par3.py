"""
par.py
G.Rice 6/20/2012
Updated by E.Younkin 12/13/2019

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

Sign conventions
Pitch - Positive tilt up
Roll - Positive port side up
Acrosstrack xyz88 - Starboard Positive
Alongtrack xyz88 - Forward Positive
BeamPointingAngle data78 - port positive


V1.0 20191213
This module includes a number of different classes and methods for working with
Kongsberg all files, each of which are intended to serve at least one of three
purposes.  These are

   1) Provide access to the Kongsberg records for viewing or data extraction.
   2) Provide simplified access to a combination of Kongsberg data.
   3) Display information from Kongsberg records or data.
   
The primary classes in this module to be accessed directly are

    AllRead - used to get data records or blocks of records from a Kongsberg .all file.
    BatchRead - use Xarray and Dask modules to read multiple .all files in parallel.

"""

import sys
import os
import numpy as np
from numpy.lib.recfunctions import append_fields, merge_arrays
import pyproj
import datetime as dtm
import pickle
import struct
import re
import copy
from glob import glob

from matplotlib import pyplot as plt

recs_categories_80 = {'65': ['data.Time', 'data.Roll', 'data.Pitch', 'data.Heave', 'data.Heading'],
                      '73': ['time', 'header.Serial#', 'header.Serial#2', 'settings'],
                      '78': ['time', 'header.Counter', 'header.SoundSpeed', 'header.Ntx', 'header.Serial#',
                             'rx.TiltAngle', 'rx.Delay', 'rx.Frequency', 'rx.BeamPointingAngle',
                             'rx.TransmitSectorID', 'rx.DetectionInfo', 'rx.QualityFactor', 'rx.TravelTime'],
                      '82': ['time', 'header.Mode', 'header.ReceiverFixedGain', 'header.YawAndPitchStabilization', 'settings'],
                      '85': ['time', 'data.Depth', 'data.SoundSpeed'],
                      '80': ['time', 'Latitude', 'Longitude', 'gg_data.Altitude']}

recs_categories_translator_80 = {'65': {'Time': [['attitude', 'time']], 'Roll': [['attitude', 'roll']],
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

recs_categories_110 = {'65': ['data.Time', 'data.Roll', 'data.Pitch', 'data.Heave', 'data.Heading'],
                       '73': ['time', 'header.Serial#', 'header.Serial#2', 'settings'],
                       '78': ['time', 'header.Counter', 'header.SoundSpeed', 'header.Ntx', 'header.Serial#',
                              'rx.TiltAngle', 'rx.Delay', 'rx.Frequency', 'rx.BeamPointingAngle',
                              'rx.TransmitSectorID', 'rx.DetectionInfo', 'rx.QualityFactor', 'rx.TravelTime'],
                       '82': ['time', 'header.Mode', 'header.ReceiverFixedGain', 'header.YawAndPitchStabilization', 'settings'],
                       '85': ['time', 'data.Depth', 'data.SoundSpeed'],
                       '110': ['data.Time', 'source_data.Latitude', 'source_data.Longitude',
                               'source_data.Altitude']}

recs_categories_translator_110 = {'65': {'Time': [['attitude', 'time']], 'Roll': [['attitude', 'roll']],
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
                                  '110': {'Time': [['navigation', 'time']], 'Latitude': [['navigation', 'latitude']],
                                          'Longitude': [['navigation', 'longitude']],
                                          'Altitude': [['navigation', 'altitude']]}}

oldstyle_recs_categories = {'65': ['data.Time', 'data.Roll', 'data.Pitch', 'data.Heave', 'data.Heading'],
                            '73': ['time', 'header.Serial#', 'header.Serial#2', 'settings'],
                            '102': ['time', 'PingCounter', 'SoundSpeed', 'Ntx', 'SystemSerialNum',
                                    'rx.TiltAngle', 'rx.Delay', 'rx.CenterFrequency',
                                    'rx.BeamPointingAngle', 'rx.TransmitSectorID', 'rx.DetectionWindowLength',
                                    'rx.QualityFactor', 'rx.TravelTime'],
                            '82': ['time', 'header.Mode', 'header.ReceiverFixedGain', 'header.YawAndPitchStabilization', 'settings'],
                            '85': ['time', 'data.Depth', 'data.SoundSpeed'],
                            '80': ['time', 'Latitude', 'Longitude', 'gg_data.Altitude']}

oldstyle_recs_categories_translator = {'65': {'Time': [['attitude', 'time']], 'Roll': [['attitude', 'roll']],
                                              'Pitch': [['attitude', 'pitch']], 'Heave': [['attitude', 'heave']],
                                              'Heading': [['attitude', 'heading']]},
                                       '73': {'time': [['installation_params', 'time']],
                                              'Serial#': [['installation_params', 'serial_one']],
                                              'Serial#2': [['installation_params', 'serial_two']],
                                              'settings': [['installation_params', 'installation_settings']]},
                                       '102': {'time': [['ping', 'time']], 'PingCounter': [['ping', 'counter']],
                                               'SoundSpeed': [['ping', 'soundspeed']], 'Ntx': [['ping', 'ntx']],
                                               'SystemSerialNum': [['ping', 'serial_num']],
                                               'TiltAngle': [['ping', 'tiltangle']], 'Delay': [['ping', 'delay']],
                                               'CenterFrequency': [['ping', 'frequency']], 'BeamPointingAngle': [['ping', 'beampointingangle']],
                                               'TransmitSectorID': [['ping', 'txsector_beam']], 'DetectionWindowLength': [['ping', 'detectioninfo']],
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

sonar_translator = {'em122': [None, 'tx', 'rx', None], 'em302': [None, 'tx', 'rx', None], 'em304': [None, 'tx', 'rx', None],
                    'em710': [None, 'tx', 'rx', None], 'em712': [None, 'tx', 'rx', None], 'em2040': [None, 'tx', 'rx', None],
                    'em2040_dual_rx': [None, 'tx', 'rx_port', 'rx_stbd'],
                    'em2040_dual_tx': ['tx_port', 'tx_stbd', 'rx_port', None],
                    'em2040_dual_tx_rx': ['tx_port', 'tx_stbd', 'rx_port', 'rx_stbd'],
                    # EM2040c is represented in the .all file as em2045
                    'em2045': [None, 'txrx', None, None], 'em2045_dual': [None, 'txrx_port', 'txrx_stbd', None],
                    'em3002': [None, 'tx', 'rx', None], 'em2040p': [None, 'txrx', None, None],
                    'em3020': [None, 'tx', 'rx', None], 'em3020_dual': [None, 'txrx_port', 'txrx_stbd', None],
                    'me70': [None, 'txrx', None, None]}


class AllRead:
    """
    This is the primary class for working with Kongsberg data all files and
    providing access to the data records.  The concept behind this class is
    that the class is a file, and it lets to move around to different records
    in the file.  The class can contain a map of where all the records are in
    the file, a record or a dictionary of records belonging to a ping, and
    dictionary of navigation and attitude data, or other types of data such as
    runtime parameters.
    
    The current record can be found in a class variable called 'packet'.  This
    contains the "header" information that exists for all records, such as
    time, record type, record size.  The data for the record is contained in a
    data record type specific subpacket type inside of the variable packet
    called 'subpack'.  Each of these are their own classes with their own
    variables and methods for working with their own data.
    
    allRead methods of interest:
        getrecord
        getwatercolumn
        display
        getnav
        plot_navarray
        getruntime
        getsscast
        getping
        
    It is worth noting here that the getrecord method calls the mapfile
    method if a file map does not already exist.  The file map is also an
    allRead class variable called 'map'.  The map class has a number of methods 
    of its own, most notibly the method 'printmap' which displays the records 
    available in file and what percentage of the file they consume.  The labels
    for these records (record number) is listed in this map and can be used as 
    a reference when working from the commandline.
    
    """

    def __init__(self, infilename, start_ptr=0, end_ptr=0, byteswap=False, mode='rb'):
        """Make a instance of the allRead class."""
        self.infilename = infilename
        self.byteswap = byteswap
        self.infile = open(infilename, mode=mode)
        self.mapped = False
        self.packet_read = False
        self.eof = False
        self.error = False
        self.start_ptr = start_ptr
        self.end_ptr = end_ptr
        self.ems_with_rangeangle = [2040, 2045, 710, 712, 312, 122, 124, 302, 304, 850]  # 850 being the ME70
        self.ems_with_oldrangeangle = [3020, 1020, 120, 2000]
        self.time_buffer = []

        self.startbytesearch = self._build_startbytesearch()
        self.at_right_byte = False

        if end_ptr:
            self.filelen = int(self.end_ptr - self.start_ptr)
        else:
            self.infile.seek(-self.start_ptr, 2)
            self.filelen = self.infile.tell()
        self.infile.seek(0, 2)
        self.max_filelen = self.infile.tell()
        self.infile.seek(self.start_ptr, 0)

    def close(self, clean=False):
        """
        Close the file from which the data is being read.
        """
        self.infile.close()
        if clean:
            mapfilename = self.infilename + '.par'
            navfilename = self.infilename + '.nav'
            try:
                os.remove(mapfilename)
                os.remove(navfilename)
            except FileNotFoundError:
                pass

    def __enter__(self):
        """
        Start function for with statement
        Now this will work:
        with allRead(file):
                 ....

        The file will be closed automatically
        """
        return self

    def __exit__(self, *args):
        """
        Exit function for with statement
        """
        self.close()

    def _build_startbytesearch(self):
        """
        Build the regular expression we are going to use to find the next startbyte, if necessary.
        """
        # Possible datagram types as int
        recids = [68, 88, 102, 78, 83, 89, 107, 79, 65, 110, 67, 72, 80, 71, 85, 73, 105, 112, 82, 104, 66]
        # search for startbyte + one of the datagramtypes
        search_exp = b'\x02[' + b'|'.join([struct.pack('B', x) for x in recids]) + b']'
        # sonartype always follows datagramtype, include it to eliminate possible mismatches
        # EM2040c shows as 2045
        # EM2040p shows as 2040 (great)
        # EM3002 shows as 3020 (thats good, it aligns with spec)
        #
        # only including 204x, 71x, and 312 systems.  These use the Data78 rec, others use Depth datagram, different
        #   process

        emsrchs = []
        for em in self.ems_with_rangeangle + self.ems_with_oldrangeangle:
            if em == 124:
                sonartype = b'\|\x00'  # have to escape the special character so the regex looks for it
            else:
                sonartype = struct.pack('H', em)
            if sonartype == b'.\x01':
                sonartype = b'\.\x01'
            em_search_exp = search_exp + sonartype
            compiled_expr = re.compile(em_search_exp)
            emsrchs.append(compiled_expr)
        return emsrchs

    def seek_next_startbyte(self):
        """
        Determines if current pointer is at the start of a record.  If not, finds the next valid one.
        """
        # check is to continue on until you find the header pattern, which surrounds the STX byte.  Can't just
        #   search for \x02, regex pattern should be the smallest allowable to be 99.99% certain of start
        while not self.at_right_byte:
            cur_ptr = self.infile.tell()
            if cur_ptr >= self.start_ptr + self.filelen:
                self.eof = True
                raise ValueError('Unable to find sonar startbyte, is this sonar supported?')
            # consider start bytes right at the end of the given filelength as valid, even if they extend
            # over to the next chunk
            srchdat = self.infile.read(min(20, (self.start_ptr + self.filelen) - cur_ptr))
            stx_idx = 1
            # First loop through is mandatory to find a startbyte
            while stx_idx >= 0:
                stx_idx = srchdat.find(b'\x02')  # -1 if there is no startbyte
                if stx_idx >= 0:
                    possible_start = cur_ptr + stx_idx
                    self.infile.seek(possible_start)  # go to startbyte
                    datchk = self.infile.read(4)  # read the first four bytes
                    for srch in self.startbytesearch:
                        m = srch.search(datchk, 0)
                        if m:
                            self.infile.seek(possible_start - 4)  # found a valid start, go to the start of the record
                            self.at_right_byte = True
                            stx_idx = -1  # force quit the loop since you found the right byte
                            break
                if not self.at_right_byte:   # continue search in this srchdat chunk of the file
                    try:
                        srchdat = srchdat[stx_idx + 1:]  # Start after that invalid start byte, look for the next in the chunk
                        cur_ptr += stx_idx + 1
                    except:  # must be at the end of the chunk, so the next .find will return -1 anyway
                        pass

    def read(self):
        """
        Reads the header.
        """
        # if running this without offset/maxlen arguments, don't have to worry about finding STX
        #    otherwise you gotta search for the next one...should only need to do it once
        if not self.at_right_byte:
            self.seek_next_startbyte()

        if self.infile.tell() >= self.start_ptr + self.filelen:
            self.eof = True

        if not self.eof:
            # first element of the header is the packetsize
            if self.byteswap:
                packetsize = 4 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0].newbyteorder()
            else:
                packetsize = 4 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0]
            self.infile.seek(-4, 1)
            # with the max length argument, you want to make sure you get the end record, even if it is outside the
            #    range of your given maximum length.
            if (self.filelen >= self.infile.tell() - self.start_ptr + packetsize) or (self.end_ptr > 0):
                self.packet = Datagram(self.infile.read(packetsize), self.byteswap)
                self.packet_read = True
                if not self.packet.valid:
                    self.error = True
                    print("Record without proper STX or ETX found: {}".format(self.infile.tell()))
            else:
                self.eof = True
                self.error = True
                print("Broken packet found at", self.infile.tell())
                print("Final packet size", packetsize)

    def get(self):
        """
        Decodes the data section of the datagram if a packet has been read but
        not decoded.  If excecuted the packet_read flag is set to False.
        """
        if self.packet_read and not self.packet.decoded:
            try:
                self.packet.decode()
                if self.packet.dtype == 73:
                    if self.packet.subpack.fix_byte_offset:
                        # if you end up in here, it means we found an installation parameters entry that was too short
                        # we had to move back fix_byte_offset bytes, so adjust the file pointer accordingly
                        self.infile.seek(-self.packet.subpack.fix_byte_offset, 1)
                        self.at_right_byte = False
                        self.seek_next_startbyte()
            except NotImplementedError as err:
                print(err)
            self.packet_read = False
    
    def _better_merge_arrays(self, base_arr, arrone, arrtwo, arrthree):
        newdtype = np.dtype(base_arr.dtype.descr + arrone.dtype.descr + arrtwo.dtype.descr + arrthree.dtype.descr)
        newarray = np.empty(shape=base_arr.shape, dtype=newdtype)
        for field in base_arr.dtype.names:
            newarray[field] = base_arr[field]
        for field in arrone.dtype.names:
            newarray[field] = arrone[field]
        for field in arrtwo.dtype.names:
            newarray[field] = arrtwo[field]
        for field in arrthree.dtype.names:
            newarray[field] = arrthree[field]
        return newarray
    
    def _populate_rec(self):
        """
        Data78 comes in from sequential read by time/ping.  We want to just expand all the sector based arrays from
        sector-wise to beam-wise.  This will make our xarray Dataset only have time/beam dimensions, which makes
        further computation simple. 
        
        Creates some duplication, but compression will basically make the increased data stored take up like no space
        """
        try:
            rec = self.packet.subpack
        except AttributeError:
            print('Par3: No data found in packet.subpack for record')
            return None
        if type(rec) not in [Data78, Data102]:
            return rec
        elif np.isnan(rec.rx['TravelTime']).all():
            print('Par3: {}: Found invalid ping (did not contain travel time)'.format(rec.time))
            return None
        else:
            # any NaN returns for traveltime are set to 0, lets us easily filter later
            rec.rx['TravelTime'] = np.nan_to_num(rec.rx['TravelTime'])
            
            if 'Delay' not in rec.tx.dtype.names:
                # this is a duplicate, happens when running sequential read with start_ptr/end_ptr, eof doesnt kick in
                # shows here because 'Delay', etc.  are already removed from rec.tx
                return None

            # xarray Dataset must have no duplicate times (this appears to happen every now and then with dual head/dual ping)
            while rec.time in self.time_buffer:
                rec.time = rec.time + 0.000001
            self.time_buffer.append(rec.time)
            if len(self.time_buffer) > 10:
                self.time_buffer.remove(self.time_buffer[0])

            try:  # the data78 approach
                delay_array = rec.tx['Delay']
                freq_array = rec.tx['Frequency']
                tiltangle_array = rec.tx['TiltAngle']
                freqname = 'Frequency'
            except:  # the data102 approach
                if isinstance(rec.tx['Delay'], np.ndarray):
                    delay_array = rec.tx['Delay']
                    freq_array = rec.tx['CenterFrequency']
                    tiltangle_array = rec.tx['TiltAngle']
                    freqname = 'CenterFrequency'
                else:
                    delay_array = [rec.tx['Delay']]
                    freq_array = [rec.tx['CenterFrequency']]
                    tiltangle_array = [rec.tx['TiltAngle']]
                    freqname = 'CenterFrequency'

            # expand out the sector wise arrays to be beam wise
            populated_delay = np.empty(rec.rx['TransmitSectorID'].shape, dtype=[('Delay', np.float32)])
            populated_freq = np.empty(rec.rx['TransmitSectorID'].shape, dtype=[(freqname, np.int32)])
            populated_tiltangle = np.empty(rec.rx['TransmitSectorID'].shape, dtype=[('TiltAngle', np.float32)])
            for id in np.unique(rec.rx['TransmitSectorID']):
                populated_delay[rec.rx['TransmitSectorID'] == id] = delay_array[id]
                populated_freq[rec.rx['TransmitSectorID'] == id] = freq_array[id]
                populated_tiltangle[rec.rx['TransmitSectorID'] == id] = tiltangle_array[id]
            
            #rec.rx = merge_arrays([rec.rx, populated_delay, populated_freq, populated_tiltangle], flatten=True)
            rec.rx = self._better_merge_arrays(rec.rx, populated_delay, populated_freq, populated_tiltangle)

            new_tx_names = [n for n in rec.tx.dtype.names if n not in ['Delay', freqname, 'TiltAngle']]
            rec.tx = rec.tx[new_tx_names]

            return rec
                
    def _translate_to_array(self, data_list, override_type=None, uneven=False, maxlen=None, fullwith=None):
        """
        Translate and generate numpy array from list of records
        """

        if override_type is not None:
            typ = override_type
        else:
            typ = data_list[0].dtype

        Z = []

        if not uneven:
            for enu, row in enumerate(data_list):
                Z.append(translate_detectioninfo(row))
            newZ = np.array(Z, dtype=typ)
        else:
            newZ = np.full((len(data_list), maxlen), fullwith, dtype=typ)
            for i, j in enumerate(data_list):
                newZ[i][0:len(j)] = translate_detectioninfo(j)
        return newZ

    def has_old_style_rangeangle(self):
        """
        Simple method to determine whether this is of the new type of sonar that has the new rangeangle datagram 78
        or the old type that has the old rangeangle datagram 102
        """
        curptr = self.infile.tell()
        self.infile.seek(0)
        has_oldstyle = None
        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        self.eof = False
        self.read()
        while not self.eof:
            datagram_type = self.packet.dtype
            if datagram_type == 102:
                has_oldstyle = True
                break
            elif datagram_type == 78:
                has_oldstyle = False
                break
            else:
                self.read()
        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        if has_oldstyle is not None:
            return has_oldstyle
        try:
            sonarmodelnumber = self.packet.header[3]
            expectedmodelnumber = self.ems_with_rangeangle + self.ems_with_oldrangeangle
            if sonarmodelnumber not in self.ems_with_oldrangeangle + self.ems_with_rangeangle:
                raise ValueError('Unable to read file {}: sonar model number not recognized.  Found {}, expected one of {}'.format(self.infilename, sonarmodelnumber, expectedmodelnumber))
        except:
            raise EnvironmentError('File {} could not be read, no valid packets found'.format(self.infilename))
        # raise EnvironmentError('File {} has no old or new style rangeangle datagrams'.format(self.infilename))
        return False

    def has_data110(self):
        """
        Simple method to determine whether this is file contains network attitude velocity data110 records
        """

        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        self.infile.seek(0)
        found80 = 0
        has_data = False

        self.eof = False
        while found80 < 3:
            self.read()
            datagram_type = self.packet.dtype
            if datagram_type == 110:
                has_data = True
                break
            elif datagram_type == 80:
                found80 += 1
        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        return has_data

    def fast_read_start_end_time(self):
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

        # Read the first records till you get one that has time in the packet (most recs at this point i believe)
        while starttime is None:
            self.read()
            try:
                starttime = self.packet.time
            except AttributeError:  # no time for this packet
                self.read()
                try:
                    starttime = self.packet.time
                except AttributeError:
                    raise ValueError('Par3: Unable to read the time of the first record.  This is generally because the sonar model is one that is not currently enabled in this module')
        if starttime is None:
            raise ValueError('Unable to find a suitable packet to read the start time of the file')

        # Move the start/end file pointers towards the end of the file and get the last available time
        self.infile.seek(0, 2)
        chunksize = min(10 * 1024, self.infile.tell())  # pick 10k of reading just to make sure you get some valid records, or the filelength if it is less than that
        self.at_right_byte = False
        eof = self.infile.tell()
        self.start_ptr = eof - chunksize
        self.end_ptr = eof
        self.filelen = chunksize

        self.infile.seek(self.start_ptr)
        self.eof = False
        while not self.eof:
            self.read()
            try:
                endtime = self.packet.time
            except:
                pass
        if endtime is None:
            raise ValueError('Unable to find a suitable packet to read the end time of the file')
        self.infile.seek(curptr)
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
        recs_skipped = 0
        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        startptr = self.start_ptr

        self.infile.seek(0)
        while not found_install_params:
            self.read()
            datagram_type = str(self.packet.dtype)
            if datagram_type != '73':
                recs_skipped += 1
                if recs_skipped == 10:
                    print('Warning: not finding the installation parameters record at the beginning of {}'.format(self.infilename))
                continue
            self.get()
            try:
                serialnumber = self.packet.subpack.SerialNum
                serialnumbertwo = self.packet.subpack.SerialNum2
            except:
                raise ValueError('Error: unable to find the serial number records in the Data73 record')
            try:
                sonarmodel = self.packet.subpack.settings['sonar_model_number']
            except:
                raise ValueError('Error: unable to find the translated sonar model number in the Data73 record')
            found_install_params = True

        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        self.eof = False
        self.start_ptr = startptr
        return [serialnumber, serialnumbertwo, sonarmodel]

    def _only_keep_important_runtime(self, runtime_array: np.array):
        """
        Some sonar seem to log a runtime parameters entry almost every couple seconds.  This results in data that is
        almost unusable, as you are waiting to dump to json thousands of runtime parameter entries.  Here we just isolate
        the values that seem to change every few seconds (not_important_keys) and only keep the records that change
        according to the other keys.

        Parameters
        ----------
        runtime_array
            numpy array of dictionaries, each dict is a runtime parameters entry

        Returns
        -------
        np.array
            trimmed array of dicts for only those keys that we have deemed important
        """

        not_important_keys = ['AbsorptionCoefficent', 'Counter']
        data_lookup = []
        for cnt, ra in enumerate(runtime_array):
            data = ra.copy()
            [data.pop(ky) for ky in not_important_keys if ky in data]
            if data not in data_lookup:
                data_lookup.append(data)
            else:
                runtime_array[cnt] = {}
        return runtime_array

    def _finalize_records(self, recs_to_read, recs_count, sonarmodelnumber):
        """
        Take output from sequential_read_records and alter the type/size/translate as needed for Kluster to read and
        convert to xarray.  Major steps include
        - adding empty arrays so that concatenation later on will work
        - translate the runtime parameters from integer/binary codes to string identifiers for easy reading (and to
             allow comparing results between different file types)
        returns: recs_to_read, dict of dicts finalized
        """
        # first check for varying number of beams (see EM302)
        uneven = False
        maxlen = None
        if 'ping' in recs_to_read and recs_to_read['ping']['traveltime']:
            minlen = len(min(recs_to_read['ping']['traveltime'], key=lambda x: len(x)))
            maxlen = len(max(recs_to_read['ping']['traveltime'], key=lambda x: len(x)))
            if minlen != maxlen:
                print('par3: Found uneven number of beams from {} to {}'.format(minlen, maxlen))
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
                        try:  # data110 approach, concatenate the nav packets to one array
                            recs_to_read[rec][dgram] = np.concatenate(recs_to_read[rec][dgram])
                        except:  # data80 approach, cast as numpy array, just one list of values
                            recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])
                elif rec == 'ping':
                    if dgram == 'detectioninfo':
                        # same for detection info, but it also needs to be converted to something other than int8
                        recs_to_read[rec][dgram] = self._translate_to_array(recs_to_read[rec][dgram], override_type=np.int32, uneven=uneven, maxlen=maxlen, fullwith=2)
                    elif dgram == 'qualityfactor':
                        if uneven:
                            newrec = np.zeros((len(recs_to_read[rec][dgram]), maxlen), dtype=np.int32)
                            for i, j in enumerate(recs_to_read[rec][dgram]):
                                newrec[i][0:len(j)] = j
                            recs_to_read[rec][dgram] = newrec
                        else:
                            recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram], dtype=np.int32)
                    else:
                        if uneven and isinstance(recs_to_read[rec][dgram][0], np.ndarray):
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
                        pingmode = sonarmodelnumber in ['em302', 'em710', 'em304', 'em712']
                        recs_to_read[rec][dgram] = translate_mode(np.array(recs_to_read[rec][dgram]), pingmode=pingmode)
                    elif dgram == 'modetwo':
                        recs_to_read[rec][dgram] = translate_mode_two(np.array(recs_to_read[rec][dgram]))
                    else:
                        recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])
                else:
                    recs_to_read[rec][dgram] = np.array(recs_to_read[rec][dgram])

        if recs_to_read['navigation']['altitude'] is None or len(recs_to_read['navigation']['altitude']) == 0:
            recs_to_read['navigation'].pop('altitude')
        recs_to_read['runtime_params']['runtime_settings'] = self._only_keep_important_runtime(recs_to_read['runtime_params']['runtime_settings'])

        # finding spikes in latitude/longitude that go to 0 (only seen this once with old data), have to identify and remove
        for var in ['latitude', 'longitude']:
            dif = np.abs(np.diff(recs_to_read['navigation'][var]))
            spike_idx = dif >= 1  # just look for spikes greater than one degree, should cover most cases
            spikes = np.count_nonzero(spike_idx)
            remove_these = []
            if spikes:
                try:
                    spike_index = np.where(spike_idx)[0] - 3
                    varlength = len(recs_to_read['navigation'][var])
                    for cnt, spk in enumerate(spike_index):
                        last_good = recs_to_read['navigation'][var][spk - 1]
                        if spk not in remove_these:
                            still_bad = True
                            idx = 1
                            while still_bad:
                                if abs(recs_to_read['navigation'][var][spk + idx] - last_good) > 1:
                                    if (spk + idx) not in remove_these:
                                        remove_these.append(spk + idx)
                                elif idx >= 10 or (spk + idx + 1) >= varlength:
                                    still_bad = False
                                idx += 1
                except:
                    print('Unable to remove navigation spikes')
                # print('Removing {} {} spikes found in navigation record...'.format(len(remove_these), var))
                for rec_type in ['time', 'latitude', 'longitude', 'altitude']:
                    if rec_type in recs_to_read['navigation']:
                        recs_to_read['navigation'][rec_type] = np.delete(recs_to_read['navigation'][rec_type], remove_these)
                
        recs_to_read['ping']['processing_status'] = np.zeros_like(recs_to_read['ping']['beampointingangle'], dtype=np.uint8)

        # hack here to ensure that we don't have duplicate times across chunks, modify the last time slightly.
        #   next chunk might include a duplicate time
        if recs_to_read['ping']['time'].any() and recs_to_read['ping']['time'].size > 1:
            recs_to_read['ping']['time'][0] += 0.000010
            if recs_to_read['ping']['serial_num'][0] != recs_to_read['ping']['serial_num'][1]:
                recs_to_read['ping']['time'][1] += 0.000010

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

        # first determine whether we need to use the old or new style rangeangle datagram
        if not self.has_old_style_rangeangle():
            # prefer data110 for the higher rate altitude
            if self.has_data110():
                categories = recs_categories_110
                category_translator = recs_categories_translator_110
                # print('Using network attitude velocity 110, rangeangle 78')
            else:
                categories = recs_categories_80
                category_translator = recs_categories_translator_80
                # print('Using position 80, rangeangle 78')
        else:
            categories = oldstyle_recs_categories
            category_translator = oldstyle_recs_categories_translator
            # print('Using position 80, oldstyle rangeangle 102')

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
                rec = self._populate_rec()  # Build the rx delay and freq arrays if this is a rangeangle record
                if rec is not None:
                    for subrec in categories[datagram_type]:
                        #  override for nested recs, designated with periods in the recs_to_read dict
                        if subrec.find('.') > 0:
                            tmprec = getattr(rec, subrec.split('.')[0])
                            subrec = subrec.split('.')[1]
                        else:
                            tmprec = rec

                        val = None
                        if subrec == 'settings':
                            val = [getattr(tmprec, subrec)]
                        else:
                            try:  # flow for array/list attribute
                                val = list(getattr(tmprec, subrec))
                            except TypeError:  # flow for float/int attribute
                                try:
                                    val = [getattr(tmprec, subrec)]
                                except ValueError:  # it just isn't there
                                    print('par3: Unable to read {}: {} - {}'.format(datagram_type, tmprec, subrec))
                                    val = []
                            except AttributeError:  # flow for nested recs
                                try:
                                    val = [tmprec[subrec]]
                                except (TypeError, ValueError):  # it just isn't there
                                    print('par3: Unable to read {}: {} - {}'.format(datagram_type, tmprec, subrec))
                                    val = []

                        # generate new list or append to list for each rec of that dgram type found
                        for translated in category_translator[datagram_type][subrec]:
                            if recs_to_read[translated[0]][translated[1]] is None:
                                recs_to_read[translated[0]][translated[1]] = copy.copy(val)
                            else:
                                recs_to_read[translated[0]][translated[1]].extend(val)

            if datagram_type == '73' and first_installation_rec:
                self.eof = True
        recs_to_read = self._finalize_records(recs_to_read, recs_count, sonarmodelnumber)
        recs_to_read['format'] = 'all'
        return recs_to_read

    def mapfile(self, verbose=False, show_progress=True):
        """
        Maps the datagrams in the file.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack(self.infilename)
            self.reset()
            if show_progress:
                print('Mapping file;           ', end=' ')
            while not self.eof:
                loc = self.infile.tell()
                self.read()
                dtype = self.packet.header[2]
                dsize = self.packet.header[0]
                time = self.packet.gettime()
                if dtype == 107:
                    try:
                        self.get()
                        pingcounter = self.packet.subpack.header['PingCounter']
                        self.map.add(str(dtype), loc, time, dsize, pingcounter)
                    except:
                        print("Water column record at " + str(loc) + " skipped.")
                else:
                    self.map.add(str(dtype), loc, time, dsize)
                current = 100 * loc / self.filelen
                if current - progress >= 1:
                    progress = current
                    if show_progress:
                        sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' % {'percent': progress})
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            # set the number of watercolumn packets into the map object
            if '107' in self.map.packdir:
                pinglist = list(set(self.map.packdir['107'][:, 3]))
                self.map.numwc = len(pinglist)
            if self.error:
                print()
            else:
                if show_progress:
                    print('\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.')
            if verbose:
                self.map.printmap()
            self.mapped = True
        else:
            pass

    def loadfilemap(self, mapfilename=''):
        """
        Loads the packdir if the map object packdir has been saved previously.
        """
        if mapfilename == '':
            mapfilename = self.infilename + '.par'
        try:
            self.map = mappack()
            self.map.load(mapfilename)
            self.mapped = True
            print('Loaded file map ' + mapfilename)
        except IOError:
            print(mapfilename + ' map file not found.')

    def savefilemap(self):
        """
        Saves the mappack packdir dictionary for faster operations on a file in
        the future.  The file is saved under the same name as the loaded file
        but with a 'par' extension.
        """
        if self.mapped:
            mapfilename = self.infilename + '.par'
            self.map.save(mapfilename)
            print('file map saved to ' + mapfilename)
        else:
            print('no map to save.')

    def getrecord(self, recordtype, recordnum):
        """
        Gets the record number of the described record type.  The subpacket
        object is returned for easier access to the desired data.
        """
        self.eof = False
        if not self.mapped:
            self.mapfile()
        if str(recordtype) in self.map.packdir:
            loc = int(self.map.packdir[str(recordtype)][recordnum][0])
            # deal with moving within large files
            if loc > 2147483646:
                loc -= 2e9
                self.infile.seek(2e9)
                while loc > 2147483646:
                    loc -= 2e9
                    self.infile.seek(2e9, 1)
                self.infile.seek(loc, 1)
            else:
                self.infile.seek(loc)
            self.read()
            self.get()
            return self.packet.subpack
        else:
            print("record " + str(recordtype) + " not available.")
            return None

    def overwrite_record(self, recordtype, recordnum, bytestring):
        self.infile.seek(int(self.map.packdir[str(recordtype)][recordnum][0]))
        original_byte_count = np.frombuffer(self.infile.read(4), dtype=np.uint32)[0] + 4
        if original_byte_count != len(bytestring):
            raise Exception("bytestring was not the same size as the existing data in the .all file")

        self.infile.seek(int(self.map.packdir[str(recordtype)][recordnum][0]))
        self.infile.write(bytestring)

    def findpacket(self, recordtype, verbose=False):
        """
        Find the next record of the requested type.
        """
        self.read()
        while not self.eof:
            if verbose:
                print(self.packet.dtype)
            if recordtype == self.packet.dtype:
                break
            else:
                self.read()
        self.get()

    def getwatercolumn(self, recordnum):
        """
        This method is designed to get a watercolumn packet by the ping number
        where ping 0 is the first in the file.  Separate records are
        reassembled for the whole ping and stored as the current subpack class
        as if it were a single record.
        """
        # dt is for looking for packets with different time stamps.
        if not self.mapped:
            self.mapfile()
        pinglist = sorted(set(self.map.packdir['107'][:, 3]))
        if recordnum >= len(pinglist):
            print(str(len(pinglist)) + ' water column records available.')
            return None
        else:
            pingnum = pinglist[recordnum]
            inx = np.nonzero(self.map.packdir['107'][:, 3] == pingnum)[0]
            ping = self.getrecord(107, inx[0])
            numbeams = ping.header['Total#Beams']
            recordsremaining = list(range(ping.header['#OfDatagrams']))
            recordsremaining.pop(ping.header['Datagram#'] - 1)
            totalsamples, subbeams = ping.ampdata.shape
            rx = np.zeros(numbeams, dtype=Data107.nrx_dtype)
            # Initialize array to NANs. Source:http://stackoverflow.com/a/1704853/1982894
            ampdata = np.empty((totalsamples, numbeams), dtype=np.float32)
            ampdata.fill(np.NAN)

            rx[:subbeams] = ping.rx
            ampdata[:, :subbeams] = ping.ampdata
            beamcount = subbeams
            if len(inx) > 1:
                for n in inx[1:]:
                    ping = self.getrecord(107, n)
                    recordnumber = recordsremaining.index(ping.header['Datagram#'] - 1)
                    recordsremaining.pop(recordnumber)
                    numsamples, subbeams = ping.ampdata.shape
                    if numsamples > totalsamples:
                        temp = np.empty((numsamples - totalsamples, numbeams), dtype=np.float32)
                        temp.fill(np.NAN)
                        ampdata = np.append(ampdata, temp, axis=0)
                        totalsamples = numsamples
                    rx[beamcount:beamcount + subbeams] = ping.rx
                    ampdata[:numsamples, beamcount:beamcount + subbeams] = ping.ampdata
                    beamcount += subbeams
            if len(recordsremaining) > 0:
                print("Warning: Not all WC records have the same time stamp!")
            sortidx = np.argsort(rx['BeamPointingAngle'])
            self.packet.subpack.rx = rx[sortidx]
            self.packet.subpack.ampdata = ampdata[:, sortidx]
            self.packet.subpack.header[2] = 1
            self.packet.subpack.header[3] = 1
            self.packet.subpack.header[6] = numbeams
            return self.packet.subpack

    def display(self):
        """
        Prints the current record header and record type header to the command
        window.  If the record type header display method also contains a plot
        function a plot will also be displayed.
        """
        if self.packet_read:
            self.packet.display()
        elif 'packet' in self.__dict__:
            self.packet.display()
            if self.packet.decoded:
                self.packet.subpack.display()
        else:
            print('No record currently read.')

    def reset(self):
        """
        Puts the file pointer to the start and the eof to False.
        """
        self.infile.seek(self.start_ptr)
        self.packet_read = False
        self.eof = False
        if 'packet' in self.__dict__:
            del self.packet

    def getnav(self, tstamps, postype=80, att_type=65, degrees=True):
        """
        For each provided time stamp (single or array) an array
        of navigation data is returned for each of the provided time stamps.
        The returned array set consists of time, x(deg), y(deg), roll (deg), 
        pitch(deg), heave (meters), and heading (deg).  Time stamps are to be
        POSIX time stamps, and are assumed to be in UTC. Set the 'degrees'
        keyword to False have the returned attitude informaiton in radians.
        """
        # make incoming tstamp shape more flexible
        tstamps = np.asarray(tstamps)
        ndim = tstamps.shape
        if len(ndim) == 0:
            tstamps = np.array([tstamps])
        elif len(ndim) == 2:
            tstamps = tstamps[0]
        numpts = len(tstamps)
        # make an array of all the needed data
        if 'navarray' not in self.__dict__:
            self._build_navarray()
        # find bounding times for getting all needed nav data
        if str(att_type) in self.navarray and str(postype) in self.navarray:
            mintime = max(self.navarray[str(att_type)][0, 0], self.navarray[str(postype)][0, 0])
            maxtime = min(self.navarray[str(att_type)][-1, 0], self.navarray[str(postype)][-1, 0])
            navpts = np.zeros((numpts, 7))
            # look for time stamps in the time range
            idx_range = np.nonzero((tstamps <= maxtime) & (tstamps >= mintime))[0]
            if len(idx_range) > 0:
                pos = self.navarray[str(postype)]
                att = self.navarray[str(att_type)]
                # for time stamps in the time range, find that nav and att
                for i in idx_range:
                    ts = tstamps[i]
                    if pos[0, 0] < ts < pos[-1, 0]:
                        prev = np.nonzero(pos[:, 0] <= ts)[0][-1]
                        navpts[i, :3] = self._interp_points(tstamps[i], pos[prev, :], pos[prev + 1, :])
                    else:
                        navpts[i, :3] = np.nan
                    if att[0, 0] < ts < att[-1, 0]:
                        prev = np.nonzero(att[:, 0] <= tstamps[i])[0][-1]
                        navpts[i, 3:] = self._interp_points(tstamps[i], att[prev, :], att[prev + 1, :])[1:]
                    else:
                        navpts[i, 3:] = np.nan
            # convert roll(3), pitch(4) and heading(6) into radians 
            if not degrees:
                navpts[:, [3, 4, 6]] = np.deg2rad(navpts[:, [3, 4, 6]])
            return navpts

    def _interp_points(self, tstamp, pt1, pt2):
        """
        Performs an interpolation for the points given and returns the
        interpolated points.  The first field of each point array is assumed to
        be the time stamp, and all other values in the array are interpolated.
        """
        delta = pt2 - pt1
        result = pt1 + (tstamp - pt1[0]) * delta / delta[0]
        return result

    def _build_navarray(self, allrecords=False):
        """
        The objective is to do the work of building an array of the navigation
        data to speed up processing later.  It is stored in a dictionary of
        arrays for each navigation datagram.  Position information is in arrays
        ordered as time, latitude, longitude.  Attitude information is in
        arrays ordered as time, roll, pitch, heave, heading.
        Only an array for the first attitude sensor and first positioning
        sensor is pulled.
        """
        self.navarray = {}
        if not self.mapped:
            self.mapfile()
        if '80' in self.map.packdir:
            print('creating position array')
            numpos = len(self.map.packdir['80'])
            self.navarray['80'] = np.zeros((numpos, 3))
            for i in range(numpos):
                self.getrecord(80, i)
                if (self.packet.subpack.header['System'] & 3) == 1:
                    self.navarray['80'][i, 0] = self.packet.time
                    self.navarray['80'][i, 2] = self.packet.subpack.header[2]
                    self.navarray['80'][i, 1] = self.packet.subpack.header[3]
        if '65' in self.map.packdir:
            print('creating attitude array (65)')
            time = []
            roll = []
            pitch = []
            heave = []
            heading = []
            numatt = len(self.map.packdir['65'])
            for m in range(numatt):
                p65 = self.getrecord(65, m)
                if (p65.sensor_descriptor & 16) == 0:
                    time += list(p65.data['Time'])
                    roll += list(p65.data['Roll'])
                    pitch += list(p65.data['Pitch'])
                    heave += list(p65.data['Heave'])
                    heading += list(p65.data['Heading'])
            self.navarray['65'] = np.asarray(list(zip(time, roll, pitch, heave, heading)))

        if allrecords and '110' in self.map.packdir:
            print('creating attitude array (110)')
            time = []
            roll = []
            pitch = []
            heave = []
            heading = []
            exttime = []
            rollrate = []
            pitchrate = []
            yawrate = []
            downvel = []
            numatt = len(self.map.packdir['110'])
            pav = self.getrecord(110, 0)
            if pav.source == 'GRP102':
                for m in range(numatt):
                    pav = self.getrecord(110, m)
                    time += list(pav.data['Time'])
                    roll += list(pav.data['Roll'])
                    pitch += list(pav.data['Pitch'])
                    heave += list(pav.data['Heave'])
                    heading += list(pav.data['Heading'])
                    exttime += list(pav.source_data['Time1'].astype(np.float64) + pav._weektime)
                    rollrate += list(pav.source_data['RollRate'])
                    pitchrate += list(pav.source_data['PitchRate'])
                    yawrate += list(pav.source_data['YawRate'])
                    downvel += list(pav.source_data['DownVelocity'])
            elif pav.source == 'binary23':
                for m in range(numatt):
                    pav = self.getrecord(110, m)
                    time += list(pav.data['Time'])
                    roll += list(pav.data['Roll'])
                    pitch += list(pav.data['Pitch'])
                    heave += list(pav.data['Heave'])
                    heading += list(pav.data['Heading'])
                    exttime += list(pav.source_data['Seconds'] + pav.source_data['FracSeconds'])
                    rollrate += list(pav.source_data['RollRate'])
                    pitchrate += list(pav.source_data['PitchRate'])
                    yawrate += list(pav.source_data['YawRate'])
                    downvel += list(pav.source_data['DownVelocity'])
            elif pav.source == 'binary11':
                for m in range(numatt):
                    pav = self.getrecord(110, m)
                    if pav.source == 'binary11':
                        time += list(pav.data['Time'])
                        roll += list(pav.data['Roll'])
                        pitch += list(pav.data['Pitch'])
                        heave += list(pav.data['Heave'])
                        heading += list(pav.data['Heading'])
                        exttime += list(pav.source_data['Seconds'] + pav.source_data['FracSeconds'])
                        rollrate += list(pav.source_data['RollRate'])
                        pitchrate += list(pav.source_data['PitchRate'])
                        yawrate += list(pav.source_data['YawRate'])
                        downvel += list(pav.source_data['DownVelocity'])
            self.navarray['110'] = np.asarray(
                list(zip(time, roll, pitch, heave, heading, exttime, rollrate, pitchrate, yawrate, downvel)))
        if '104' in self.map.packdir:
            print('creating altitude (depth) array')
            num = len(self.map.packdir['104'])
            self.navarray['104'] = np.zeros((num, 2))
            for n in range(num):
                self.getrecord(104, n)
                self.navarray['104'][n, 0] = self.packet.gettime()
                self.navarray['104'][n, 1] = self.packet.subpack.header['Height']

    def save_navarray(self):
        """
        Creats an 'npy' file with the name of the all file that contains the
        navigation array used.
        """
        if 'navarray' not in self.__dict__:
            self._build_navarray()
        try:
            navfilename = self.infilename + '.nav'
            navfile = open(navfilename, 'wb')
            pickle.dump(self.navarray, navfile)
            navfile.close()
            print("Saved navarray to " + navfilename)
        except:
            pass

    def load_navarray(self):
        """
        Loads an 'npy' file with the name of the all file that contains the
        navigation array for this file name.
        """
        try:
            navfilename = self.infilename + '.nav'
            navfile = open(navfilename, 'rb')
            self.navarray = pickle.load(navfile)
            print("Loaded navarray from " + navfilename)
            navfile.close()
        except:
            print("No navarray file found.")

    def plot_navarray(self):
        """
        Plots the parts of the navarray.
        """
        if not hasattr(self, 'navarray'):
            self._build_navarray()
        fig = plt.figure()
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax3 = fig.add_subplot(614, sharex=ax2)
        ax4 = fig.add_subplot(615, sharex=ax2)
        ax5 = fig.add_subplot(616, sharex=ax2)
        ax1.plot(self.navarray['80'][:, 1], self.navarray['80'][:, 2])
        ax1.set_xlabel('Longitude (Degrees)')
        ax1.set_ylabel('Latitude (Degrees)')
        ax1.grid()
        ax2.plot(self.navarray['65'][:, 0], self.navarray['65'][:, 4])
        ax2.set_ylabel('Heading (Degrees)')
        ax2.set_xlabel('Time (Seconds)')
        ax2.grid()
        if '104' in self.navarray:
            ax3.plot(self.navarray['104'][:, 0], self.navarray['104'][:, 1])
        ax3.set_ylabel('Height (Meters)')
        ax3.grid()
        ax4.plot(self.navarray['65'][:, 0], self.navarray['65'][:, 1])
        ax4.plot(self.navarray['65'][:, 0], self.navarray['65'][:, 2])
        ax4.set_ylabel('Degress')
        ax4.legend(('Roll', 'Pitch'))
        ax4.grid()
        ax5.plot(self.navarray['65'][:, 0], self.navarray['65'][:, 3])
        ax5.set_ylabel('Heave (Meters)')
        ax5.set_xlabel('Time (Seconds)')
        ax5.grid()
        ax5.set_xlim((self.navarray['65'][:, 0].min(), self.navarray['65'][:, 0].max()))
        plt.draw()

    def _build_speed_array(self):
        """
        This method builds a speed array.  First it looks for speed in the
        positon (80d) datagram.  If not available the speed is calculated from
        the position in the navarray.
        """
        self.getrecord(80, 0)
        if self.packet.subpack.header['Speed'] > 655:
            print('creating speed array')
            if not hasattr(self, 'navarray'):
                self._build_navarray()
            numpts = len(self.navarray['80']) - 1
            self.speedarray = np.zeros((numpts, 2))
            self.utmzone = int((180. + self.navarray['80'][0, 1]) / 6) + 1
            toutm = pyproj.Proj(proj='utm', zone=self.utmzone, ellps='WGS84')
            a, b = toutm(self.navarray['80'][:, 1], self.navarray['80'][:, 2])
            da = a[:-1] - a[1:]
            db = b[:-1] - b[1:]
            dt = self.navarray['80'][:-1, 0] - self.navarray['80'][1:, 0]
            self.speedarray[:, 1] = np.abs(np.sqrt(da ** 2 + db ** 2) / dt)
            self.speedarray[:, 0] = self.navarray['80'][:-1, 0] + dt / 2
        else:
            num80 = len(self.map.packdir['80'])
            self.speedarray = np.zeros((num80, 2))
            for n in range(num80):
                self.getrecord(80, n)
                self.speedarray[n, 1] = self.packet.subpack.header['Speed']
                self.speedarray[n, 0] = self.packet.gettime()

    def getspeed(self, tstamps, time_to_average=1):
        """
        Calling the method with time stamps returns the speed at the time. An
        additional kwarg, time_to_average, defaults to 1.  This is the window on
        either side of the times provided that the speeds will be averaged over.
        If there are no times available the closest time is provided, unless
        outside of the range of the file, in which case Nan is returned for that
        value.
        """
        tta = time_to_average
        if not hasattr(self, 'speedarray'):
            self._build_speed_array()
        # make incoming tstamp shape more flexible
        tstamps = np.asarray(tstamps)
        ndim = tstamps.shape
        if len(ndim) == 0:
            tstamps = np.array([tstamps])
        elif len(ndim) == 2:
            tstamps = tstamps[0]
        numpts = len(tstamps)
        speeds = np.zeros(numpts)
        for n in range(numpts):
            idx = np.nonzero((self.speedarray[:, 0] > tstamps[n] - tta) & (self.speedarray[:, 0] < tstamps[n] + tta))[0]
            if len(idx) > 0:
                speeds[n] = self.speedarray[idx, 1].mean()
            else:
                dt = (self.speedarray[:-1, 0] - self.speedarray[1:, 0]).mean()
                if (tstamps[n] > self.speedarray[0, 0] - dt) and tstamps[n] < self.speedarray[-1, 0] + dt:
                    idx = np.abs(self.speedarray[:, 0] - tstamps[n]).argmin()
                    speeds[n] = self.speedarray[idx, 1]
                else:
                    speeds[n] = np.nan
        return speeds

    def _get_nav_stats(self):
        """
        This method is intended to augment the correlation of motion artifacts
        with bathymetry wobbles by providing the frequency content of the
        attitude data.
        """
        if not hasattr(self, 'navarray'):
            self._build_navarray()
        if not hasattr(self, 'speedarray'):
            self._build_speed_array()
        att = self.navarray['65']
        t = att[:, 0]
        dt = (t[1:] - t[:-1]).mean()
        f = np.fft.fftfreq(len(t), d=dt)
        win = np.hanning(len(t))
        filt = np.hanning(100)
        filt /= filt.sum()
        roll_fft = np.convolve(np.fft.fft(win * att[:, 1]), filt, mode='same')
        pitch_fft = np.convolve(np.fft.fft(win * att[:, 2]), filt, mode='same')
        heave_fft = np.convolve(np.fft.fft(win * att[:, 3]), filt, mode='same')
        plt.figure()
        plt.plot(f, np.log10(np.abs(roll_fft)))
        plt.plot(f, np.log10(np.abs(pitch_fft)))
        plt.plot(f, np.log10(np.abs(heave_fft)))
        plt.xlabel('Frequency (Hz)')
        plt.legend(('Roll', 'Pitch', 'Heave'))
        plt.grid()

    def _build_runtime_array(self):
        """
        This function builds an array of all the runtime parameters.
        """
        rtp = np.dtype([('Time', 'd'), ('RuntimePacket', Data82.hdr_dtype)])
        if not self.mapped:
            self.mapfile()
        num = len(self.map.packdir['82'])
        self._runtime_array = np.zeros(num, dtype=rtp)
        for n in range(num):
            self.getrecord(82, n)
            self._runtime_array[n]['Time'] = self.packet.gettime()
            self._runtime_array[n]['RuntimePacket'] = self.packet.subpack.header

    def getruntime(self, time, values=[]):
        """
        This method provides runtime information based on what was valid for
        the provided time stamp.  The time stamp is to be provided in POSIX
        time.  If the "value" kwarg is a value from the runtime parameters that
        value is returned.  Otherwise the whole runtime parameter subrecord is
        returned.  If an invalid time is provided "None" is returned.
        """
        if not hasattr(self, 'runtime_array'):
            self._build_runtime_array()
        idx = np.nonzero(self._runtime_array['Time'] < time)[0]
        if len(idx) > 0:
            idx = idx[-1]
        else:
            # the first records are often before the first runtime record
            idx = 0
        if len(values) > 0:
            if set(values) <= set(self._runtime_array['RuntimePacket'].dtype.fields):
                return self._runtime_array['RuntimePacket'][values][idx]
            else:
                return None
        else:
            return self._runtime_array[idx]['RuntimePacket']

    def _build_sscast_array(self):
        """
        This function builds an array of all the sound speed casts.
        """
        cast_dtype = np.dtype([('Time', 'd'), ('SSCast', np.object)])
        if not self.mapped:
            self.mapfile()
        num = len(self.map.packdir['85'])
        self._sscast_array = np.zeros(num, dtype=cast_dtype)
        for n in range(num):
            ping85 = self.getrecord(85, n)
            self._sscast_array[n]['Time'] = ping85.time
            self._sscast_array[n]['SSCast'] = ping85

    def getsscast(self, time):
        """
        This method provides cast information based on what was valid for
        the provided time stamp.  The time stamp is to be provided in POSIX
        time. Two arrays are returned.  The first is the sound speed header,
        the second is the sound speed data.  Both are in the sound speed
        datapacket data type.
        """
        if not hasattr(self, '_sscast_array'):
            self._build_sscast_array()
        idx = np.nonzero(self._sscast_array['Time'] < time)[0]
        if len(idx) > 0:
            return self._sscast_array[idx[-1]]['SSCast']
        else:
            return None

    def getping(self, pingtime=0, pingnumber=0, recordlist=[], extra=True):
        """
        This method provides all the datagrams and navigational information 
        associated with a ping.  Provide a keyword argument for either the time
        of the ping (kwarg pingtime) or the ping number (kwarg pingnumber) in 
        the file.  If both a time stamp and a ping number are provided the time
        stamp is used.  The navigation, attitude, runtime parameters and sound
        speed profile valid for the ping are also provided if the 'extra' kwarg
        is set to True.
        ***This method has not been properly tested***
        """
        if not self.mapped:
            self.mapfile()
        # first get the ping number if the ping time is provided
        if pingtime != 0:
            if '88' in self.map.packdir:
                n = '88'
            elif '68' in self.map.packdir:
                n = '68'
            else:
                n = None
            if n is not None:
                b = np.isclose([self.map.packdir['88'][:, 1]], [pingtime], rtol=0, atol=5e-4)
                idx = np.nonzero(b)[0]
                if len(idx) == 0:
                    pingnumber = None
                elif len(idx) == 1:
                    pingnumber = idx[0]
                else:
                    pingnumber = None
                    print('More than one ping with matching time stamp found.')
            # get the ping number in the file
            # pingnumber = xxx
            # if time is not found pingnumber = None
        if pingnumber is not None:
            # find the records available
            filerecords = list(self.map.packdir.keys())
            # make a list of the records to get depending on the type.
            if len(recordlist) == 0:
                # if no records specifically requested, get all (useful) available
                # XYZ
                if '88' in filerecords:
                    recordlist.append('88')
                elif '68' in filerecords:
                    recordlist.append('68')
                # Seabed Imagry
                if '89' in filerecords:
                    recordlist.append('89')
                elif '83' in filerecords:
                    recordlist.append('83')
                    # Range / Angle
                if '78' in filerecords:
                    recordlist.append('78')
                elif '102' in filerecords:
                    recordlist.append('102')
                # water column
                if '107' in filerecords:
                    recordlist.append('107')
            else:
                recordlist = [str(n) for n in recordlist]  # Support records as numbers
                for n in recordlist:
                    if n not in filerecords:
                        recordlist.remove(n)
            # now that the records to get are established as in the file...
            if len(recordlist) > 0:
                subpack = {}
                for n in recordlist:
                    if n != '107':
                        subpack[n] = self.getrecord(n, pingnumber)
                    elif n == '107':
                        subpack[n] = self.getwatercolumn(pingnumber)
                temp = copy.deepcopy(self.packet)
                if extra:
                    if pingtime == 0:
                        pingtime = self.packet.gettime()
                    subpack['speed'] = self.getspeed(pingtime)
                    subpack['Navigation'] = self.getnav(pingtime)
                    subpack['Runtime'] = self.getruntime(pingtime)
                    subpack['SoundSpeed'] = self.getsscast(pingtime)
                self.packet = temp
                # these fields are meaningless at this point.
                self.packet.header['Type'] = 0
                self.packet.header['Bytes'] = 0
                del self.packet.datablock
                self.packet.subpack = subpack
                return subpack
            return None
        return None


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
    ETX = b'\x03'

    hdr_dtype = np.dtype([('Bytes', 'I'), ('Start', 'B'), ('Type', 'B'),
                          ('Model', 'H'), ('Date', 'I'), ('Time', 'I')])

    def __init__(self, fileblock, byteswap=False):
        """Reads the header section, which is the first 16 bytes, of the
        given memory block."""
        # @todo would newbyteorder leave the data in place but reverse the endian of the dtypes?  Could use that instead of byteswap?
        # @todo byteswap is not implemented in the data classes -- so it shouldn't be used here either (currently)
        self.byteswap = byteswap
        hdr_sz = Datagram.hdr_dtype.itemsize
        self.header = np.frombuffer(fileblock[:hdr_sz], dtype=Datagram.hdr_dtype)
        if byteswap:
            self.header = self.header.byteswap()
        self.header = self.header[0]
        self.decoded = False
        if self.header[1] == 2:
            self.valid = True
        else:
            self.valid = False
        self.datablock = fileblock[hdr_sz:-3]
        # Storing data skipped in datablock
        self.datablockheader = fileblock[:hdr_sz]
        self.datablockfooter = fileblock[-3:]

        etx = np.frombuffer(fileblock[-3:-2], dtype=np.uint8, count=1)[0]
        if etx != self.ETX[0]:
            self.valid = False
        if byteswap:
            self.checksum = np.frombuffer(fileblock[-2:], dtype=np.uint16, count=1)[0].newbyteorder()
        else:
            self.checksum = np.frombuffer(fileblock[-2:], dtype=np.uint16, count=1)[0]
        self.dtype = self.header[2]
        try:
            self.maketime()
        except ValueError:
            pass

    def get_datablock(self, byteswap=None):
        # @todo byteswap is not implemented in the data classes -- so it shouldn't be used here either (currently)
        if byteswap is None:
            byteswap = self.byteswap

        if byteswap:
            header = self.header.byteswap()
        else:
            header = self.header
        bytestring = header.tobytes() + self.subpack.get_datablock(self.byteswap)
        # 4 bytes datagram size, 1 byte STX -- DATA -- 1 byte ETX, 2 byte checksum
        # I.e. 5 bytes excluded at start and 3 bytes at the end
        chksum = _checksum_all_bytes(bytestring[5:])
        if self.byteswap:
            chksum = chksum.newbyteorder()
        return bytestring + self.ETX + chksum.tobytes()

    def raw_rangeangleablock(self):
        return self.datablockheader + self.datablock + self.datablockfooter

    def decode(self):
        """
        Directs to the correct decoder.
        """
        if self.dtype == 48:
            self.subpack = Data48(self.datablock, self.time, self.byteswap)
        elif self.dtype == 49:
            self.subpack = Data49(self.datablock, self.time, self.byteswap)
        elif self.dtype == 51:
            self.subpack = Data51(self.datablock, self.time, self.header['Model'], self.byteswap)
        elif self.dtype == 65:
            self.subpack = Data65(self.datablock, self.time, self.byteswap)
        elif self.dtype == 66:
            self.subpack = Data66(self.datablock, self.time, self.header['Model'], self.byteswap)
        elif self.dtype == 67:
            self.subpack = Data67(self.datablock, self.time, self.byteswap)
        elif self.dtype == 68:
            self.subpack = Data68(self.datablock, self.time, self.byteswap)
        elif self.dtype == 71:
            self.subpack = Data71(self.datablock, self.time, self.byteswap)
        elif self.dtype == 73:
            self.subpack = Data73(self.datablock, self.header['Model'], self.time, self.byteswap)
        elif self.dtype == 78:
            self.subpack = Data78(self.datablock, self.time, self.byteswap)
        elif self.dtype == 79:
            self.subpack = Data79(self.datablock, self.time, self.byteswap)
        elif self.dtype == 80:
            self.subpack = Data80(self.datablock, self.time, self.byteswap)
        elif self.dtype == 82:
            self.subpack = Data82(self.datablock, self.time, self.byteswap)
        elif self.dtype == 83:
            self.subpack = Data83(self.datablock, self.time, self.byteswap)
        elif self.dtype == 85:
            self.subpack = Data85(self.datablock, self.time, self.byteswap)
        elif self.dtype == 88:
            self.subpack = Data88(self.datablock, self.time, self.byteswap)
        elif self.dtype == 89:
            self.subpack = Data89(self.datablock, self.time, self.byteswap)
        elif self.dtype == 102:
            self.subpack = Data102(self.datablock, self.time, self.byteswap)
        elif self.dtype == 104:
            self.subpack = Data104(self.datablock, self.time, self.byteswap)
        elif self.dtype == 105:
            # same definition for this data type
            self.subpack = Data73(self.datablock, self.header['Model'], self.time, self.byteswap)
        elif self.dtype == 107:
            self.subpack = Data107(self.datablock, self.time, self.byteswap)
        elif self.dtype == 109:
            self.subpack = Data109(self.datablock, self.time, self.byteswap)
        elif self.dtype == 110:
            self.subpack = Data110(self.datablock, self.time, self.byteswap)
        else:
            raise NotImplementedError("Data record " + str(self.dtype) + " decoding is not yet supported.")
        self.decoded = True

    def maketime(self):
        """
        Makes the time stamp of the current packet as a POSIX time stamp.
        UTC is assumed.
        """
        date = str(self.header[-2])
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970, 1, 1).toordinal()
        dayseconds = self.header[-1] * 0.001
        self.time = numdays * 24 * 60 * 60 + dayseconds

    def gettime(self):
        """
        Calls the method "maketime" if needed and returns the POSIX time stamp.
        """
        if 'time' not in self.__dict__:
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


class Data48(BaseData):
    """
    PU information and status 0x30 / '0' / 48.
    """
    hdr_dtype = np.dtype([('ByteOrderFlag', 'H'), ('System Serial#', 'H'),
                          ('UDPPort1', 'H'), ('UDPPort2', 'H'), ('UDPPort3', 'H'), ('UDPPort4', 'H'),
                          ('SystemDescriptor', 'I'), ('PUSoftwareVersion', 'S16'),
                          ('BSPSoftwareVersion', 'S16'), ('SonarHead/TransceiverSoftware1', 'S16'),
                          ('SonarHead/TransceiverSoftware2', 'S16'), ('HostIPAddress', 'I'),
                          ('TXOpeningAngle', 'B'), ('RXOpeningAngle', 'B'), ('Spare1', 'I'),
                          ('Spare2', 'H'), ('Spare3', 'B')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data48, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime


class Data49(BaseData):
    """
    PU Status datagram 0x31 / '1' / 49.  All values are converted to degrees,
    meters, and meters per second.
    """
    hdr_dtype = np.dtype([('StatusDatagramCount', 'H'), ('SystemSerialNum', 'H'),
                          ('PingRate', 'f'), ('PingCounter', 'H'), ('SwathDistance', 'I'),
                          ('SensorInputStatusUDP2', 'I'), ('SensorInputStatusSerial1', 'I'),
                          ('SensorInputStatusSerial2', 'I'), ('SensorInputStatusSerial3', 'I'),
                          ('SensorInputStatusSerial4', 'I'), ('PPSstatus', 'b'),
                          ('PositionStatus', 'b'), ('AttitudeStatus', 'b'), ('ClockStatus', 'b'),
                          ('HeadingStatus', 'b'), ('PUstatus', 'B'), ('LastHeading', "f"),
                          ('LastRoll', "f"), ('LastPitch', "f"), ('LastSonarHeave', "f"),
                          ('TransducerSoundSpeed', "f"), ('LastDepth', "f"), ('ShipVelocity', "f"),
                          ('AttitudeVelocityStatus', 'B'), ('MammalProtectionRamp', 'B'),
                          ('BackscatterOblique', 'b'), ('BackscatterNormal', 'b'), ('FixedGain', 'b'),
                          ('DepthNormalIncidence', 'B'), ('RangeNormalIncidence', 'H'),
                          ('PortCoverage', 'B'), ('StarboardCoverage', 'B'),
                          ('TransducerSoundSpeedFromProfile', "f"), ('YawStabAngle', "f"),
                          ('PortCoverageORAbeamVelocity', 'h'),
                          ('StarboardCoverageORDownVelocity', 'h'), ('EM2040CPUTemp', 'b')])

    raw_dtype = np.dtype([('StatusDatagramCount', 'H'), ('SystemSerialNum', 'H'),
                          ('PingRate', "H"), ('PingCounter', 'H'), ('SwathDistance', 'I'),
                          ('SensorInputStatusUDP2', 'I'), ('SensorInputStatusSerial1', 'I'),
                          ('SensorInputStatusSerial2', 'I'), ('SensorInputStatusSerial3', 'I'),
                          ('SensorInputStatusSerial4', 'I'), ('PPSstatus', 'b'),
                          ('PositionStatus', 'b'), ('AttitudeStatus', 'b'), ('ClockStatus', 'b'),
                          ('HeadingStatus', 'b'), ('PUstatus', 'B'), ('LastHeading', "H"),
                          ('LastRoll', "h"), ('LastPitch', "h"), ('LastSonarHeave', "h"),
                          ('TransducerSoundSpeed', "H"), ('LastDepth', "I"), ('ShipVelocity', "h"),
                          ('AttitudeVelocityStatus', 'B'), ('MammalProtectionRamp', 'B'),
                          ('BackscatterOblique', 'b'), ('BackscatterNormal', 'b'), ('FixedGain', 'b'),
                          ('DepthNormalIncidence', 'B'), ('RangeNormalIncidence', 'H'),
                          ('PortCoverage', 'B'), ('StarboardCoverage', 'B'),
                          ('TransducerSoundSpeedFromProfile', "H"), ('YawStabAngle', "h"),
                          ('PortCoverageORAbeamVelocity', 'h'),
                          ('StarboardCoverageORDownVelocity', 'h'), ('EM2040CPUTemp', 'b')])

    conversions = {'PingRate': 0.01, 'LastHeading': 0.01, 'LastRoll': 0.01, 'LastPitch': 0.01,
                   'LastSonarHeave': 0.01, 'TransducerSoundSpeed': 0.1, 'LastDepth': 0.01,
                   'ShipVelocity': 0.01, 'TransducerSoundSpeedFromProfile': 0.01, 'YawStabAngle': 0.01,
                   }

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data49, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime


class Data51(BaseData):
    """
    ExtraParameters datagram.
    """

    hdr_dtype = np.dtype([('Counter', 'H'), ('serial#', 'H'), ('ContentIdentifier', 'H')])

    def __init__(self, datablock, POSIXtime, model, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data51, self).__init__(datablock, byteswap=byteswap)
        self.model = model
        self.time = POSIXtime
        content_type = self.header[-1]
        if content_type == 1:
            self.data = datablock[self.hdr_sz:self.hdr_sz + 100]
        elif content_type == 2:
            pass
        elif content_type == 3:
            pass
        elif content_type == 4:
            pass
        elif content_type == 5:
            pass
        elif content_type == 6:
            data_sz = np.frombuffer(datablock[self.hdr_sz: self.hdr_sz + 2], dtype='H')[0]
            self.raw_rangeanglea = datablock[self.hdr_sz + 2: self.hdr_sz + 2 + data_sz]
            if model == 710:
                self._parse_710_bscorr()
            elif model == 122:
                self._parse_122_bscorr()

    def _parse_710_bscorr(self):
        """
        Parse the BSCorr file.
        """
        c = self.raw_rangeanglea.split('#')
        t = len(c)
        n = 0
        self.names = []
        self.swathnum = []
        self.modes = []
        self.powers = []
        self.data = []
        while n < t:
            if len(c[n]) > 0:
                header = c[n].split('\n')
                self.names.append(header[0])
                info = [int(x) for x in header[1].split('\t')]
                self.modes.append(info[0])
                self.swathnum.append(info[1])
                numsectors = info[2]
                sector = []
                secpower = []
                for m in range(numsectors):
                    n += 1
                    sectordata = c[n].split('\n')
                    sectorname = sectordata[0]
                    secpower.append(float(sectordata[1]))
                    numpts = int(sectordata[2])
                    angle = []
                    offset = []
                    for k in range(numpts):
                        a, d = sectordata[k + 3].split('\t')
                        angle.append(float(a))
                        offset.append(float(d))
                    sector.append(np.array(list(zip(angle, offset))))
                self.data.append(np.array(sector))
                self.powers.append(np.array(secpower))
            n += 1

    def _parse_122_bscorr(self):
        """
        Parse the BSCorr file.
        """
        c = self.raw_rangeanglea.split('\n')
        t = len(c) - 1  # no need to look at hex flag at end
        n = 0
        header = True
        section_idx = []
        self.names = []
        self.swathnum = []
        self.modes = []
        self.powers = []
        self.data = []
        # find all the sections to be parsed
        while n < t:
            if header == False:
                if (c[n][0] == '#') & (c[n + 1][0] == '#'):
                    section_idx.append(n)
            else:
                if c[n] == '# source level    lobe angle    lobe width':
                    header = False
            n += 1
        section_idx.append(t)
        for n in range(len(section_idx) - 1):
            m = section_idx[n]
            end = section_idx[n + 1]
            name_prefix = c[m][2:]
            if name_prefix == 'Shallow':
                mode = 2
            elif name_prefix == 'Medium':
                mode = 3
            elif name_prefix == 'Deep':
                mode = 4
            elif name_prefix == 'Very Deep':
                mode = 5
            else:
                mode = -1
                print('mode type not recognized: ' + name_prefix)
            m += 1
            while m < end:
                if c[m][0] == '#':
                    k = 1
                    data = []
                    swath_type = c[m][2:]
                    if swath_type[:12] == 'Single swath':
                        swath_num = 0
                    elif swath_type == 'Dual swath 1':
                        swath_num = 1
                    elif swath_type == 'Dual swath 2':
                        swath_num = 2
                    else:
                        swath_num = -1
                        # print 'swath type not used: ' + swath_type
                    self.names.append(name_prefix + ' - ' + swath_type)
                    self.swathnum.append(swath_num)
                    self.modes.append(mode)
                    while c[m + k][0] != '#' and m + k + 1 < end:
                        info = [int(x) for x in c[m + k].split()]
                        data.append(info)
                        k += 1
                    self.data.append(data)
                m += 1

    def plot_BSCorr(self, mode_number):
        """
        This is a hack to quickly display BSCorr files.  The mode number to
        to provide to this method is an integer, starting at 0, that
        conrrisponds to the mode in the BSCorr file.  Print the this object's
        'names' variable to see the order they are stored in.
        """
        if self.header[-1] == 6:
            data = self.data[mode_number]
            numswaths = len(data)
            fig, ax = plt.subplots()
            for n in range(numswaths):
                ax.plot(data[n][:, 0], data[n][:, 1], 'o:')
            r = ax.get_xlim()
            ax.set_xlim((max(r), min(r)))
            ax.set_xlabel('Beam Angle (deg, negative is to STBD)')
            ax.set_ylabel('BS Adjustment (dB)')
            ax.set_title('BSCorr: ' + self.names[mode_number])
            ax.grid()

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        super(Data51, self).display()
        if 'data' in self.__dict__:
            print(self.data)


class Data65_att(BasePlottableData):
    hdr_dtype = np.dtype([('Time', 'd'), ('Status', 'H'), ('Roll', 'f'), ('Pitch', 'f'),
                          ('Heave', 'f'), ('Heading', 'f')])
    raw_dtype = np.dtype([('Time', 'H'), ('Status', 'H'), ('Roll', 'h'), ('Pitch', 'h'),
                          ('Heave', 'h'), ('Heading', 'H')])
    conversions = {'Roll': 0.01, 'Pitch': 0.01, 'Heave': 0.01, 'Heading': 0.01}

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data65_att, self).__init__(datablock, byteswap=byteswap,
                                         read_limit=read_limit)  # read as many records as passed in
        self.time = POSIXtime
        self.header['Time'] = self.header['Time'] * 0.001 + self.time

    def get_datablock(self, data=None):
        tmp_header = self.header.copy()
        tmp_header['Time'] = (self.header['Time'] - self.time) * 1000
        return super(Data65_att, self).get_datablock(tmp_header)


class Data65(BaseData):
    """
    Attitude datagram 0x41/'A'/65. Data can be found in the array 'data' and
    is stored as time (POSIX), roll(deg), pitch(deg), heave(m),
    heading(deg).  sensor_descriptor does not appear to parse correctly...
    Perhaps it is not included in the header size so it is not sent to this
    object in the datablock?
    """

    hdr_dtype = np.dtype([('Counter', 'H'), ('serial#', 'H'), ('NumEntries', 'H')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data65, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.sensor_descriptor = np.frombuffer(datablock[-1:], dtype=np.uint8)[0]
        self.att = Data65_att(datablock[self.hdr_sz:-1], POSIXtime, byteswap=byteswap)
        self.data = self.att.header

    def get_display_string(self):
        value = super(Data65, self).get_display_string()
        value += 'Sensor Descriptor : ' + np.binary_repr(self.sensor_descriptor, 8) + "\n"
        # value += self.att.get_display_string()
        return value

    def display(self):
        super(Data65, self).display()
        self.att.display()

    def get_datablock(self, data=None):
        part1 = super(Data65, self).get_datablock()
        part2 = self.att.get_datablock()
        part3 = self.sensor_descriptor.tobytes()
        return part1 + part2 + part3


class Data66(BaseData):
    """
    PU BIST results output datagram 0x42/'B'/66.  The raw string text is parsed
    and provided in the array 'data' and 'metadata'.  The raw data 
    string is also available in the 'raw_data' class variable.
    """
    hdr_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('Test#', 'H'),
                          ('TestStatus', 'h')])

    def __init__(self, datablock, POSIXtime, model, byteswap=False):
        """
        Catches the binary datablock and decodes the record.
        """
        super(Data66, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.raw_data = datablock[self.hdr_sz:]
        self._model = model
        if self.header['Test#'] == 9 and self._model == 2040:
            self.testtype = 'ChannelNoise'
        elif self.header['Test#'] == 10 and self._model == 2040:
            self.testtype = 'NoiseSpectrum'
        elif self.header['Test#'] == 8 and self._model == 710:
            self.testtype = 'ChannelNoise'
        elif self.header['Test#'] == 9 and self._model == 710:
            self.testtype = 'NoiseSpectrum'
        else:
            self.testtype = 'Unknown'

    def parse(self):
        """
        Parses the text section. May change with sonar type?
        """
        if self.testtype == 'ChannelNoise':
            if self._model == 2040:
                self._2040_parse_noisetest()
            elif self._model == 710:
                self._710_parse_noisetest()
        elif self.testtype == 'NoiseSpectrum':
            if self._model == 2040:
                self._2040_parse_noisespectrum()
            elif self._model == 710:
                self._710_parse_noisespectrum()
        else:
            print('\n')
            print(self.raw_data)

    def _2040_parse_noisetest(self):
        """
        Should work for the 2040 as of SIS 4.15.
        """
        lines = self.raw_data.split('\n')
        nmax = len(lines)
        n = 0
        data = []
        # spin through all lines in the text
        while n < nmax:
            line = lines[n].split()
            if len(line) > 0:
                if line[0] == 'Channel':
                    self.label = line[1:]
                    numfreq = len(self.label)
                    freqcounter = list(range(numfreq))
                    for m in freqcounter:
                        data.append([])
                    n += 1
                    while n < nmax:
                        line = lines[n].split()
                        if len(line) > 0:
                            channel = line[0]
                            for m in freqcounter:
                                data[m].append(float(line[m + 1]))
                            n += 1
                        else:
                            break
                    n = nmax
            n += 1
        self.data = np.asarray(data).T

    def _710_parse_noisetest(self):
        """
        Should work for the EM710 as of SIS 4.15.
        """
        lines = self.raw_data.split('\n')
        nmax = len(lines)
        n = 0
        data = []
        go = False
        # spin through all lines in the text
        while n < nmax:
            line = lines[n].split()
            if len(line) > 0:
                if line[0] == 'Board':
                    go = True
                elif line[0] == 'Maximum':
                    go = False
                elif go:
                    temp = [float(x) for x in line[1:-1]]
                    data.append(temp)
                else:
                    pass
            n += 1
        self.data = np.asarray(data).T

    def _2040_parse_noisespectrum(self):
        """
        For the EM2040 as of SIS 4.15.
        """
        lines = self.raw_data.split('\n')
        nmax = len(lines)
        n = 0
        data = []
        freq = []
        go = False
        # spin through all lines in the text
        while n < nmax:
            line = lines[n].split()
            if len(line) > 0:
                if line[0][:4] == '----':
                    go = True
                elif line[0] == 'Summary...:':
                    go = False
                elif go:
                    temp = [float(x) for x in line[2::2]]
                    data.append(temp)
                    freq.append(float(line[0]))
                else:
                    pass
            n += 1
        self.data = np.asarray(data)
        self.freq = np.asarray(freq)

    def _710_parse_noisespectrum(self):
        """
        For the EM710 as of SIS 4.15.
        """
        lines = self.raw_data.split('\n')
        nmax = len(lines)
        n = 0
        data = []
        freq = []
        go = False
        # spin through all lines in the text
        while n < nmax:
            line = lines[n].split()
            if len(line) > 0:
                if line[0] == 'Board':
                    go = True
                elif line[0] == 'Maximum':
                    go = False
                elif go:
                    temp = [float(x) for x in line[2:-1]]
                    data.append(temp)
                    freq.append(float(line[0]))
                else:
                    pass
            n += 1
        self.data = np.asarray(data)
        self.freq = np.asarray(freq)
        idx = self.freq.argsort()
        self.freq = self.freq[idx]
        self.data = self.data[idx]

    def plot(self):
        """
        Plots the results of the BIST test if applicable.
        """
        self.parse()
        if self.testtype == 'ChannelNoise':
            if self._model == 2040:
                fig, ax = plt.subplots(len(self.label), 1)
                for n, a in enumerate(ax):
                    a.plot(self.data[:, n])
                    a.set_title(str(self.label[n]))
                    a.set_ylabel('dB')
                    a.set_xlim((0, self.data.shape[0]))
                a.set_xlabel('Channel Number')
                fig.suptitle(('Noise'))
            elif self._model == 710:
                plt.figure()
                plt.plot(self.data.flatten())
                plt.xlabel('Channel Number')
                plt.ylabel('Noise Level (dB)')
                plt.title('EM710 Noise Test')
                plt.grid()
                plt.xlim((0, len(self.data.flatten())))
            else:
                print('Plotting of ' + self.testtype + ' is not supported for the EM' + str(self._model))
        elif self.testtype == 'NoiseSpectrum':
            if self._model == 710 or self._model == 2040:
                l, w = self.data.shape
                legend = []
                for n in range(w):
                    legend.append('Board ' + str(n))
                plt.figure()
                plt.plot(self.freq, self.data)
                plt.xlabel('Frequency (kHz)')
                plt.ylabel('Noise Level (dB)')
                plt.title('EM' + str(self._model) + ' Noise Spectrum')
                plt.legend(legend)
                plt.grid()
            else:
                print('Plotting of ' + self.testtype + ' is not supported for the EM' + str(self._model))
        else:
            print("Plotting not supported")

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        super(Data66, self).display()
        print(self.raw_data)


class Data67(BaseData):
    """
    Clock datagram 043h / 67d / 'C'. Date is YYYYMMDD. Time is in miliseconds
    since midnight.
    """
    hdr_dtype = np.dtype([('ClockCounter', 'H'), ('SystemSerial#', 'H'),
                          ('Date', 'I'), ('Time', 'I'), ('1PPS', 'B')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data67, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        if len(datablock) > self.hdr_sz:
            print(len(datablock), self.hdr_sz)


class Data68_xyz(BasePlottableData):
    hdr_dtype = np.dtype([('Depth', "f"), ('AcrossTrack', "f"), ('AlongTrack', "f"),
                          ('BeamDepressionAngle', "f"), ('BeamAzimuthAngle', "f"),
                          ('OneWayRange', "f"), ('QualityFactor', 'B'),
                          ('DetectionWindowLength', "f"), ('Reflectivity', "f"), ('BeamNumber', 'B')])
    raw_dtype = np.dtype([('Depth', "h"), ('AcrossTrack', "h"), ('AlongTrack', "h"),
                          ('BeamDepressionAngle', "h"), ('BeamAzimuthAngle', "H"),
                          ('OneWayRange', "H"), ('QualityFactor', 'B'),
                          ('DetectionWindowLength', "B"), ('Reflectivity', "b"), ('BeamNumber', 'B')])
    conversions = {'BeamDepressionAngle': 0.01, 'BeamAzimuthAngle': 0.01, 'Reflectivity': 0.5}

    def __init__(self, datablock, data68_info, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data68_xyz, self).__init__(datablock, byteswap=byteswap,
                                         read_limit=read_limit)  # read as many records as passed in
        self._zres = data68_info['Zresolution']
        self.header['Depth'] *= self._zres
        self._xyres = data68_info['XYresolution']
        self.header['AcrossTrack'] *= self._xyres
        self.header['AlongTrack'] *= self._xyres
        self._samplerate = data68_info['SampleRate']
        self.header['OneWayRange'] /= self._samplerate
        # self.header['DetectionWindowLength'] *= 4    # not sure what this is for or what it means

    def get_datablock(self, data=None):
        tmp_header = self.header.copy()
        tmp_header['Depth'] /= self._zres
        tmp_header['AcrossTrack'] /= self._xyres
        tmp_header['AlongTrack'] /= self._xyres
        tmp_header['OneWayRange'] *= self._samplerate
        # tmp_header['DetectionWindowLength'] /= 4    # not sure what this is for or what it means
        return super(Data68_xyz, self).get_datablock(tmp_header)


class Data68(BaseData):
    """
    XYZ datagram 044h / 68d / 'D'. All values are converted to meters, degrees,
    or whole units.  The header sample rate may not be correct, but is 
    multiplied by 4 to make the one way travel time per beam appear correct. The
    detection window length per beam is in its raw form...
    """
    hdr_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('VesselHeading', "f"), ('SoundSpeed', "f"), ('TransducerDepth', "f"),
                          ('MaximumBeams', 'B'), ('ValidBeams', 'B'), ('Zresolution', "f"),
                          ('XYresolution', "f"), ('SampleRate', 'f')])
    raw_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('VesselHeading', "H"), ('SoundSpeed', "H"), ('TransducerDepth', "H"),
                          ('MaximumBeams', 'B'), ('ValidBeams', 'B'), ('Zresolution', "B"),
                          ('XYresolution', "B"), ('SampleRate', 'H')])
    conversions = {2: 0.01, 3: 0.1, 4: 0.01, 7: 0.01, 8: 0.01,
                   -1: 4,  # FIXME: revisit this number... it makes the range work but may not be correct
                   }

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data68, self).__init__(datablock, byteswap=byteswap)
        self.depthoffsetmultiplier = np.frombuffer(datablock[-1:], dtype='b')[0] * 65536
        self.header[4] += self.depthoffsetmultiplier
        self.xyz = Data68_xyz(datablock[self.hdr_sz:-1], self.header, byteswap=byteswap)
        self.data = self.xyz.header
        self.time = POSIXtime

    def get_datablock(self, data=None):
        tmp_header = self.header.copy()
        tmp_header.header[4] -= self.depthoffsetmultiplier
        part1 = super(Data68, self).get_datablock(tmp_header)
        part2 = self.xyz.get_datablock()
        part3 = np.frombuffer([self.depthoffsetmultiplier / 65536], dtype='b').tobytes()
        return part1 + part2 + part3

    def get_display_string(self):
        s = super(Data68, self).get_display_string()
        s += 'TransducerDepthOffsetMultiplier : ' + str(self.depthoffsetmultiplier) + "\n"
        # s += self.xyz.get_display_string()
        return s

    def display(self):
        super(Data68, self).display()
        self.xyz.display()


class Data71_ss(BasePlottableData):
    hdr_dtype = np.dtype([('Time', 'd'), ('SoundSpeed', 'f')])
    raw_dtype = np.dtype([('Time', 'H'), ('SoundSpeed', 'H')])
    conversions = {'SoundSpeed': 0.1}

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data71_ss, self).__init__(datablock, byteswap=byteswap,
                                        read_limit=read_limit)  # read as many records as passed in
        self._time = POSIXtime
        self.header['Time'] += self._time

    def get_datablock(self, data=None):
        tmp_header = self.header.copy()
        tmp_header['Time'] -= self._time
        return super(Data71_ss, self).get_datablock(tmp_header)


class Data71(BaseData):
    """
    Surface Sound Speed datagram 047h / 71d / 'G'.  Time is in POSIX time and
    sound speed is in meters per second.
    """
    hdr_dtype = np.dtype([('SoundSpeedCounter', 'H'), ('SystemSerial#', 'H'),
                          ('NumEntries', 'H')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data71, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.ss = Data71_ss(datablock[self.hdr_sz:-1], POSIXtime, byteswap=byteswap)
        self.data = self.ss.header
        self.endchar = datablock[-1:]

    def get_datablock(self, data=None):
        part1 = super(Data71, self).get_datablock()
        part2 = self.ss.get_datablock()
        part3 = self.endchar
        return part1 + part2 + part3


class Data73(BaseData):
    """
    Installation parameters datagram 049h (start) / 73d / 'I', 069h(stop)/ 105d
    / 'I' or 70h(remote) / 112d / 'r'.  There is a short header section and the
    remainder of the record is ascii, comma delimited.
    """
    hdr_dtype = np.dtype([('SurveyLine#', 'H'), ('Serial#', 'H'), ('Serial#2', 'H')])

    def __init__(self, datablock, modelnum, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data73, self).__init__(datablock, byteswap=byteswap)
        self.fix_byte_offset = 0
        try:
            temp = datablock[self.hdr_sz:].rstrip(b'\x00').decode('utf8').split(',')
        # I found one example of an early 2040 file where the installation parameters record was too short.  Try and find the actual
        # end and alter the file pointer post decoding, see AllRead.get()
        except UnicodeDecodeError:
            actual_end = datablock[-20:].find(b'\x03')
            if actual_end == -1:
                raise ValueError("ERROR: Found installation parameters record that cannot be decoded")
            self.fix_byte_offset = 20 - actual_end
            temp = datablock[self.hdr_sz:-self.fix_byte_offset].rstrip(b'\x00').decode('utf8').split(',')
            print('WARNING: Found unexpected length to the installation parameters record, had to find the actual end of the record')
        self.settings = {}
        self.ky_data73_translator = {'WLZ': 'waterline_vertical_location', 'SMH': 'system_main_head_serial_number',
                                     'HUN': 'hull_unit', 'HUT': 'hull_unit_offset', 'TXS': 'tx_serial_number',
                                     'T2S': 'tx_2_serial_number',
                                     'T2X': 'tx_no2_serial_number', 'R1S': 'rx_no1_serial_number',
                                     'R2S': 'rx_no2_serial_number', 'STC': 'system_transducer_configuration',
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
        self.ky_data73_val_translator = {'DSH': {'IN': 'uav_depth_sensor', 'NI': 'not_depth_sensor'},
                                         'P1M': {'0': 'active', '1': 'passive'}, 'P2M': {'0': 'active', '1': 'passive'},
                                         'P3M': {'0': 'active', '1': 'passive'},
                                         'P1T': {'0': 'system_time', '1': 'position_datagram'},
                                         'P2T': {'0': 'system_time', '1': 'position_datagram'},
                                         'P3T': {'0': 'system_time', '1': 'position_datagram'},
                                         'APS': {'0': 'position_1', '1': 'position_2', '2': 'position_3'},
                                         'SHC': {'0': 'trans_ss_used_in_profile', '1': 'trans_ss_notused_in_profile'},
                                         'CLS': {'0': 'ZDA', '1': 'active_pos', '2': 'operator_station'},
                                         'VSN': {'0': 'attvel_not_used', '1': 'attvel_sensor_1',
                                                 '2': 'attvel_sensor_2'},
                                         'PPS': {'-1': 'unknown', '0': 'not_in_use', '1': 'falling_edge',
                                                 '2': 'rising_edge'},
                                         'SNL': {'0': 'normal', '1': 'high', '2': 'very_high'},
                                         'ARO': {'2': 'com2', '3': 'com3', '8': 'udp5', '9': 'udp6'},
                                         'AHE': {'2': 'com2', '3': 'com3', '8': 'udp5', '9': 'udp6'},
                                         'AHS': {'0': 'position_3_udp2', '1': 'position_1_com1', '2': 'motion_1_com2',
                                                 '3': 'motion_2_com3', '4': 'position_3_com4', '5': 'multicast_1',
                                                 '6': 'multicast_2', '7': 'multicast_3', '8': 'attvel_1_udp5',
                                                 '9': 'attvel_2_udp6'}
                                         }
        self.ky_data73_sonar_translator = sonar_translator
        self.time = POSIXtime
        for entry in temp:
            data = entry.split('=')
            if len(data) == 2:
                ky = data[0]
                try:
                    val = self.ky_data73_val_translator[ky][data[1]]
                except KeyError:
                    val = data[1]
                try:
                    self.settings[self.ky_data73_translator[ky]] = val
                except KeyError:
                    self.settings[ky] = val
        self.settings['sonar_model_number'] = self.return_model_num(str(modelnum))

    def return_model_num(self, modelnum):
        # possibles are only where the number exactly matches one of the possibilities in the translator
        translator_keys = list(self.ky_data73_sonar_translator)
        translator_numbers = [re.sub("[^0-9]", "", x) for x in translator_keys]
        possibles = [translator_keys[cnt] for cnt, sonar in enumerate(translator_numbers) if sonar == modelnum]
        if len(possibles) == 0:
            if modelnum == '850':
                return 'me70'
            print('Unable to determine sonar model from {}'.format(modelnum))
            return modelnum
        elif len(possibles) == 1:
            return 'em' + modelnum
        else:
            # get here for all the 2040 variants
            offs = ['transducer_0_along_location', 'transducer_1_along_location', 'transducer_2_along_location',
                    'transducer_3_along_location']
            srch_offsets = [(off in self.settings) for off in offs]
            finalpossibles = []
            for poss in possibles:
                off_test = [(lvr is not None) for lvr in self.ky_data73_sonar_translator[poss]]
                if off_test == srch_offsets:
                    finalpossibles.append(poss)
            if len(finalpossibles) == 1:
                return finalpossibles[0]
            elif len(finalpossibles) > 1:  # this should only be when dual/non-dual have the same placement in sonar translator, see em3020
                dual_head_option = [f for f in finalpossibles if f.find('_dual') != -1]
                non_dual_head_option = [f for f in finalpossibles if f.find('_dual') == -1]
                if len(dual_head_option) == 1 and len(non_dual_head_option) == 1 and len(finalpossibles) == 2:  # this only works when checking dual vs non dual options
                    rollangles = [float(self.settings[ky]) for ky in ['transducer_0_roll_angle', 'transducer_1_roll_angle', 'transducer_2_roll_angle', 'transducer_3_roll_angle'] if ky in self.settings]
                    diffangle = max(rollangles) - min(rollangles)
                    if diffangle > 5:  # this is just a guess really, if the roll angles differ by more than 5 degrees, we guess dual head
                        return dual_head_option[0]
                    else:
                        return non_dual_head_option[0]
                else:
                    print('Found multiple sonar model number possibilities for this system: {}'.format(finalpossibles))

            print('Unable to determine sonar model from {}'.format(modelnum))
            return modelnum

    def get_display_string(self):
        """
        Displays contents of the header to the command window.
        """
        s = super(Data73, self).get_display_string()
        keys = sorted(list(self.settings.keys()))
        for key in keys:
            s += key + ' : ' + str(self.settings[key]) + "\n"
        return s

    def get_datablock(self, data=None):
        raise Exception("This data type is not exportable yet.  Need to confirm the format of the ascii data")


class Data78_ntx(BaseData):
    hdr_dtype = np.dtype([('TiltAngle', 'f'), ('Focusing', 'f'), ('SignalLength', 'f'), ('Delay', 'f'),
                          ('Frequency', 'f'), ('AbsorptionCoef', 'f'), ('WaveformID', 'B'),
                          ('TransmitSector#', 'B'), ('Bandwidth', 'f')])
    raw_dtype = np.dtype([('TiltAngle', 'h'), ('Focusing', 'H'), ('SignalLength', 'f'), ('Delay', 'f'),
                          ('Frequency', 'f'), ('AbsorptionCoef', 'H'), ('WaveformID', 'B'),
                          ('TransmitSector#', 'B'), ('Bandwidth', 'f')])
    conversions = {'TiltAngle': 0.01,  # convert to degrees
                   'Focusing': 0.1,  # convert to meters
                   'AbsorptionCoef': 0.01,  # convert to dB/km
                   }

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data78_ntx, self).__init__(datablock, byteswap=byteswap,
                                         read_limit=read_limit)  # read as many records as passed in


class Data78_nrx(BaseData):
    hdr_dtype = np.dtype([('BeamPointingAngle', 'f'), ('TransmitSectorID', 'B'), ('DetectionInfo', 'B'),
                          ('WindowLength', 'H'), ('QualityFactor', 'B'), ('Dcorr', 'b'), ('TravelTime', 'f'),
                          ('Reflectivity', 'f'), ('CleaningInfo', 'b'), ('Spare', 'B')])
    raw_dtype = np.dtype([('BeamPointingAngle', 'h'), ('TransmitSectorID', 'B'), ('DetectionInfo', 'B'),
                          ('WindowLength', 'H'), ('QualityFactor', 'B'), ('Dcorr', 'b'), ('TravelTime', 'f'),
                          ('Reflectivity', 'h'), ('CleaningInfo', 'b'), ('Spare', 'B')])
    conversions = {'BeamPointingAngle': 0.01,  # convert to degrees
                   'Reflectivity': 0.1,  # convert to dB
                   }

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data78_nrx, self).__init__(datablock, byteswap=byteswap,
                                         read_limit=read_limit)  # read as many records as passed in


class Data78(BaseData):
    """
    Raw range and angle datagram, aka 'N'/'4eh'/78d.  All data is contained
    in the header, rx, and tx arrays. the rx and tx arrays are ordered as in
    the data definition document, but have been converted to degrees, dB,
    meters, etc.
    The reported angles are in the transducer reference frame, so be careful of
    reverse mounted configurations. For the TX, forward angles are positive,
    for the RX angles to port are positive.
    """
    hdr_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('SoundSpeed', 'f'),
                          ('Ntx', 'H'), ('Nrx', 'H'), ('Nvalid', 'H'), ('SampleRate', 'f'), ('Dscale', 'I')])
    raw_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('SoundSpeed', 'H'),
                          ('Ntx', 'H'), ('Nrx', 'H'), ('Nvalid', 'H'), ('SampleRate', 'f'), ('Dscale', 'I')])
    conversions = {2: 0.1,  # sound speed to convert to meters/second
                   }

    def __init__(self, datablock, pingtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data78, self).__init__(datablock, byteswap=byteswap)
        self.time = pingtime
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        """Decodes the repeating parts of the record."""
        ntx = self.header[3]
        self.tx_data = Data78_ntx(datablock[:ntx * Data78_ntx.hdr_sz])
        self.tx = self.tx_data.header

        self.rx_data = Data78_nrx(datablock[ntx * Data78_ntx.hdr_sz:-1])
        self.rx = self.rx_data.header

        self.endchar = datablock[-1:]

    def get_datablock(self, data=None):
        part1 = super(Data78, self).get_datablock()
        part2 = self.tx_data.get_datablock()
        part3 = self.rx_data.get_datablock()
        part4 = self.endchar
        return part1 + part2 + part3 + part4

    def get_rx_time(self):
        """
        Returns the receive times in POSIX time.
        """
        txnum = sorted(self.tx['TransmitSector#'])
        # deal with EM2040 in 200 kHz where the tx sector idx are [0,2]
        if txnum.max() == len(txnum):
            txnum[-1] = txnum[-1] - 1
        txdelays = self.tx['Delay'][txnum]
        rxdelays = txdelays[self.rx['TransmitSectorID']].astype(np.float64)
        rxtime = self.rx['TravelTime'].astype(np.float64) + rxdelays + self.pingtime
        return rxtime


class Data79(BaseData):
    """
    Quality factor datagram 4fh / 79d / 'O'.
    """
    hdr_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('Nrx', 'H'), ('Npar', 'H')])  # The data format has a Spare Byte here...
    qf_dtype = np.dtype([('QualityFactor', 'f4')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data79, self).__init__(datablock, byteswap=byteswap)
        if self.header['Npar'] > 1:
            print("Warning: Datagram has expanded and may not parse correctly.")
        self.read(datablock[self.hdr_sz:-1])
        self.time = POSIXtime

    def read(self, datablock):
        """
        Reads the Quality Factor Datagram.
        """
        if self.header['Npar'] == 1:
            self.data = np.frombuffer(datablock, dtype=Data79.qf_dtype)
        else:
            print("Only parsing original IFREMER quality factor")
            step = 4 * self.header['Nrx'] * self.header['Npar']
            self.data = np.zeros(self.header['Nrx'], dtype=Data79.qf_dtype)
            for n in range(self.header['Nrx']):
                self.data = np.frombuffer(datablock[n * step:n * step + 4], dtype=Data79.qf_dtype)

    def get_datablock(self, data=None):
        raise Exception("Not Implemented")


class Data80_gga(BaseData):
    hdr_dtype = np.dtype([('MessageID', 'S5'), ('POSIX', 'd'),
                          ('Latitude', 'f'), ('LatDirection', 'S1'), ('Longitude', 'f'),
                          ('LonDirection', 'S1'), ('GPSQuality', 'B'), ('#SV', 'B'), ('HDOP', 'f'),
                          ('OrthometricHeight', 'f'), ('HeightUnits', 'S1'), ('GeoidSeparation', 'f'),
                          ('SeparationUnits', 'S1'), ('AgeOfDGPS', 'f'), ('ReferenceStationID', 'H'),
                          ('CheckSum', 'H')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        # don't call the base init as this is not a packed binary array but text data instead
        self.header = np.zeros(1, dtype=self.hdr_dtype)[0]
        temp = datablock.split(b',')
        for n, t in enumerate(temp):
            if len(t) > 0:
                if n == 0 or n == 3 or n == 5 or n == 10 or n == 12:
                    self.header[n] = t.decode()
                elif n == 1 or n == 8 or n == 9 or n == 11 or n == 13:
                    self.header[n] = float(t)
                elif n == 2:
                    deg = int(t[:2])
                    minutes = float(t[2:])
                    self.header[n] = deg + minutes / 60.
                elif n == 4:
                    deg = int(t[:3])
                    minutes = float(t[3:])
                    self.header[n] = deg + minutes / 60.
                elif n == 14:
                    t2 = t.split(b'*')
                    try:
                        self.header[-2] = int(t2[0])
                    except:
                        self.header[-2] = 0
                    try:
                        self.header[-1] = int(t2[1], 16)
                    except:
                        self.header[-1] = 0
                else:
                    self.header[n] = int(t)
            else:
                self.header[n] = None

    def get_datablock(self, data=None):
        raise Exception("Writing of GGA not supported yet.")


class Data80_ggk(BaseData):
    hdr_dtype = np.dtype([('MessageID', 'S5'), ('UTCTime', 'd'), ('UTCDay', 'S6'),
                          ('Latitude', 'f'), ('LatDirection', 'S1'), ('Longitude', 'f'),
                          ('LonDirection', 'S1'), ('GPSQuality', 'B'), ('#SV', 'B'), ('DOP', 'f'),
                          ('EllipsoidHeight', 'f'), ('HeightUnits', 'S1'), ('CheckSum', 'H')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        # don't call the base init as this is not a packed binary array but text data instead
        self.header = np.zeros(1, dtype=self.hdr_dtype)[0]
        temp = datablock.split(b',')
        for n, t in enumerate(temp):
            if len(t) > 0:
                if n == 0 or n == 2 or n == 4 or n == 6:
                    self.header[n] = t.decode()
                elif n == 1 or n == 9:
                    self.header[n] = float(t)
                elif n == 3:
                    deg = int(t[:2])
                    minutes = float(t[2:])
                    self.header[n] = deg + minutes / 60.
                elif n == 5:
                    deg = int(t[:3])
                    minutes = float(t[3:])
                    self.header[n] = deg + minutes / 60.
                elif n == 10:
                    self.header[n] = float(t[3:])
                elif n == 11:
                    t2 = t.split(b'*')
                    self.header[n] = t2[0].decode()
                    self.header[n + 1] = int(t2[1].rstrip(b'\x00'), 16)
                else:
                    self.header[n] = int(t)
            else:
                self.header[n] = None

    def get_datablock(self, data=None):
        raise Exception("Writing of GGK not supported yet.")


class Data80(BaseData):
    """
    Position datagram, 0x50 / 'P' / 80. Available data is in the header
    list, and all data has been converted to degrees or meters.
    """

    hdr_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('Latitude', 'd'),
                          ('Longitude', 'd'), ('Quality', 'f'), ('Speed', 'f'), ('Course', 'f'),
                          ('Heading', 'f'), ('System', 'B'), ('NumberInputBytes', 'B')])
    raw_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('Latitude', 'i'),
                          ('Longitude', 'i'), ('Quality', 'H'), ('Speed', 'H'), ('Course', 'H'),
                          ('Heading', 'H'), ('System', 'B'), ('NumberInputBytes', 'B')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the record."""
        super(Data80, self).__init__(datablock, byteswap=byteswap)
        # read the original datagram, of which the size is the last part of the header.
        self.raw_data = datablock[self.hdr_sz:self.hdr_sz + self.header[-1]]
        self.header['Latitude'] /= 20000000.  # convert to degrees
        self.header['Longitude'] /= 10000000.  # convert to degrees
        self.header['Quality'] *= 0.01  # convert to meters
        self.header['Speed'] *= 0.01  # convert to meters/second
        self.header['Course'] *= 0.01  # convert to degrees
        self.header['Heading'] *= 0.01  # convert to degrees
        self.time = POSIXtime
        self.gg_data = None
        self.parse_raw()

    def parse_raw(self):
        """
        Parses the raw_data that arrived in SIS and puts it in source_data.
        """
        try:
            msg_type = np.frombuffer(self.raw_data[:5], dtype='S5')
            if msg_type[0] == b'INGGA':
                self._parse_gga()
            elif msg_type[0] == b'GPGGA':
                self._parse_gga()
            elif msg_type[0] == b'INGGK':
                self._parse_ggk()
            elif msg_type[0] == b'GPGGK':
                self._parse_ggk()
        except AttributeError:
            print('Data80: Unable to find {} in this record'.format(msg_type[0]))

    def _parse_gga(self):
        """
        parse the gga string.
        """
        # try:
        self.gg_data = Data80_gga(self.raw_data)
        self.source_data = self.gg_data.header  # for backward compatibility
        self.gg_data.Altitude = self.gg_data.OrthometricHeight + self.gg_data.GeoidSeparation
        # except:
        #     print('Unable to process GGA string: {}'.format(self.raw_data))

    def _parse_ggk(self):
        """
        parse the ggk string.
        """
        try:
            self.gg_data = Data80_ggk(self.raw_data)
            self.source_data = self.gg_data.header  # for backward compatibility
            self.gg_data.Altitude = self.gg_data.EllipsoidHeight
        except:
            print('Unable to process GGK string: {}'.format(self.raw_data))

    def get_datablock(self, data=None):
        raise Exception("Not Implemented")

    def get_display_string(self):
        s = super(Data80, self).get_display_string()
        s += '\n***raw data record***\n'
        if self.gg_data is not None:
            s += self.gg_data.get_display_string()
        else:
            print('Data80: Unable to find gg_data')
        return s


class Data82(BaseData):
    """
    Runtime parameters datagram, 0x52 / 'R' / 82.
    Values that are converted into whole units include: AbsorptionCoefficent,
    TransmitPulseLength, TransmitBeamwidth, ReceiveBeamwidth, and
    TransmitAlongTilt.
    """

    hdr_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('OperatorStationStatus', 'B'), ('ProcessingUnitStatus', 'B'),
                          ('BSPStatus', 'B'), ('SonarHeadOrTransceiverStatus', 'B'),
                          ('Mode', 'B'), ('FilterID', 'B'), ('MinDepth', 'H'), ('MaxDepth', 'H'),
                          ('AbsorptionCoefficent', 'f'), ('TransmitPulseLength', 'f'),
                          ('TransmitBeamWidth', 'f'), ('TransmitPower', 'b'),
                          ('ReceiveBeamWidth', 'f'), ('ReceiveBandWidth50Hz', 'B'),
                          ('ReceiverFixedGain', 'B'), ('TVGlawCrossoverAngle', 'B'),
                          ('SourceOfSoundSpeed', 'B'), ('MaxPortSwathWidth', 'H'),
                          ('BeamSpacing', 'B'), ('MaxPortCoverage', 'B'),
                          ('YawAndPitchStabilization', 'B'), ('MaxStarboardCoverage', 'B'),
                          ('MaxStarboardSwathWidth', 'H'), ('TransmitAlongTilt', 'f'),
                          ('HiLoFrequencyAbsorptionCoeffRatio', 'B')])
    raw_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('OperatorStationStatus', 'B'), ('ProcessingUnitStatus', 'B'),
                          ('BSPStatus', 'B'), ('SonarHeadOrTransceiverStatus', 'B'),
                          ('Mode', 'B'), ('FilterID', 'B'), ('MinDepth', 'H'), ('MaxDepth', 'H'),
                          ('AbsorptionCoefficent', 'H'), ('TransmitPulseLength', 'H'),
                          ('TransmitBeamWidth', 'H'), ('TransmitPower', 'b'),
                          ('ReceiveBeamWidth', 'B'), ('ReceiveBandWidth50Hz', 'B'),
                          ('ReceiverFixedGain', 'B'), ('TVGlawCrossoverAngle', 'B'),
                          ('SourceOfSoundSpeed', 'B'), ('MaxPortSwathWidth', 'H'),
                          ('BeamSpacing', 'B'), ('MaxPortCoverage', 'B'),
                          ('YawAndPitchStabilization', 'B'), ('MaxStarboardCoverage', 'B'),
                          ('MaxStarboardSwathWidth', 'H'), ('TransmitAlongTilt', 'h'),
                          ('HiLoFrequencyAbsorptionCoeffRatio', 'B')])
    conversions = {'AbsorptionCoefficent': 0.01, 'TransmitPulseLength': 0.000001,
                   'TransmitBeamWidth': 0.1, 'ReceiveBeamWidth': 0.1, 'TransmitAlongTilt': 0.1,
                   }

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the record."""
        super(Data82, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.settings = self.translate_runtime_parameters_string(self.get_display_string())

    def repr_byte(self, field_number):
        """
        Prints the given 1 bite field in a binary form.
        """
        if isinstance(self.header[field_number], np.uint8):
            return str(np.binary_repr(self.header[field_number], width=8))

    def print_byte(self, field_number):
        print(self.repr_byte(field_number))

    def get_display_string(self):
        """
        Displays contents of the header to the command window.
        """
        s = ""
        bitfields = np.array([2, 3, 4, 5, 6, 7, 18, 20, 22, 26])
        for n, name in enumerate(self.header.dtype.names):
            if np.any(bitfields == n):
                s += name + ' : ' + np.binary_repr(self.header[n], width=8) + "\n"
            else:
                s += name + ' : ' + str(self.header[n]) + "\n"
        return s

    def translate_runtime_parameters_string(self, runtime_text):
        """
        translate the display string to dict for storing as xarray attribute for Kluster processing
        """
        translated_all = {}
        entries = runtime_text.split('\n')
        for entry in entries:
            if entry and (entry.find(':') != -1):  # valid entries look like 'key: value', the rest are headers or blank
                key, value = entry.split(':')
                translated_all[key.lstrip().rstrip()] = value.lstrip().rstrip()
        return translated_all


class Data83(BaseData):
    """
    Seabed Imagary datagram 053h / 83d / 'Seabed image data'.  All data is
    converted into whole units of degrees, meters, dB, etc, except Oblique
    Backscatter and Normal Backscatter which are in their raw form.
    """
    hdr_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('MeanAbsorption', "f"), ('PulseLength', "f"), ('RangeToNormal', 'H'),
                          ('StartRangeSampleOfTVG', 'H'), ('StopRangeSampleOfTVG', 'H'),
                          ('NormalIncidenceBS', "f"), ('ObliqueBS', "f"), ('TxBeamwidth', "f"),
                          ('TVGLawCrossoverAngle', "f"), ('NumberValidBeams', 'B')])
    raw_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('MeanAbsorption', "H"), ('PulseLength', "H"), ('RangeToNormal', 'H'),
                          ('StartRangeSampleOfTVG', 'H'), ('StopRangeSampleOfTVG', 'H'),
                          ('NormalIncidenceBS', "b"), ('ObliqueBS', "b"), ('TxBeamwidth', "H"),
                          ('TVGLawCrossoverAngle', "B"), ('NumberValidBeams', 'B')])
    conversions = {2: 0.01, 3: 10 ** -6,
                   7: 1,  # FIXME: check this
                   8: 1,  # FIXME: check this
                   9: 0.1, 10: 0.1,
                   }
    beaminfo_dtype = np.dtype([('BeamIndexNumber', 'B'), ('SortingDirection', 'b'),
                               ('#SamplesPerBeam', 'H'), ('CenterSample#', 'H')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data83, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        numbeams = self.header[-1]

        self._read(datablock[self.hdr_sz:], numbeams)

    def _read(self, datablock, numbeams):
        """
        Reads the data section of the record.
        """
        beaminfo_sz = Data83.beaminfo_dtype.itemsize
        samples_dtype = np.dtype([('Amplitude', "b")])
        samples_sz = samples_dtype.itemsize
        p = beaminfo_sz * numbeams
        self.beaminfo = np.frombuffer(datablock[:p], dtype=Data83.beaminfo_dtype)
        maxsamples = self.beaminfo['#SamplesPerBeam'].max()
        self.samples = np.zeros((numbeams, maxsamples), dtype='float')
        for n in range(numbeams):
            numsamples = self.beaminfo[n]['#SamplesPerBeam']
            temp = np.frombuffer(datablock[p:p + numsamples * samples_sz], dtype=samples_dtype)
            p += numsamples * samples_sz
            # startsample = self.beaminfo[n]['CenterSample#']
            self.samples[n, :numsamples] = temp.astype('float')[:]
        self.samples *= 0.5  # FIXME: check this

    def get_datablock(self, data=None):
        raise Exception("Not Implemented")


class Data85_soundspeed(BaseData):
    hdr_dtype = np.dtype([('Depth', 'd'), ('SoundSpeed', 'f')])
    raw_dtype = np.dtype([('Depth', 'I'), ('SoundSpeed', 'I')])
    conversions = {'SoundSpeed': 0.1}

    def __init__(self, datablock, depth_resolution, byteswap=False, read_limit=None):
        # add the depth resolution to just the current class instance rather than all occurances of Data85
        self.conversions = {'Depth': depth_resolution}
        self.conversions.update(Data85_soundspeed.conversions)
        super(Data85_soundspeed, self).__init__(datablock, byteswap=byteswap,
                                                read_limit=read_limit)  # read as many records as passed in
        self.depth_resolution = depth_resolution

    def plot(self):
        """
        Creates a simple plot of the cast.
        """
        plt.figure()
        plt.plot(self.data['SoundSpeed'], self.data['Depth'])
        plt.ylim((self.data['Depth'].max(), self.data['Depth'].min()))
        plt.xlabel('Sound Speed (m/s)')
        plt.ylabel('Depth (m)')
        plt.title('Cast at POSIX time ' + str(self.header['Time']))
        plt.draw()


class Data85(BaseData):
    """
    Sound Speed datagram 055h / 85d / 'U'. Time is in POSIX, depth
    is in meters, sound speed is in meters per second.
    """
    hdr_dtype = np.dtype([('ProfileCounter', 'H'), ('SystemSerial#', 'H'),
                          ('Date', 'I'), ('Time', "d"), ('NumEntries', 'H'), ('DepthResolution', 'H')])
    raw_dtype = np.dtype([('ProfileCounter', 'H'), ('SystemSerial#', 'H'),
                          ('Date', 'I'), ('Time', "I"), ('NumEntries', 'H'),
                          ('DepthResolution', 'H')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data85, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        depth_resolution = self.header['DepthResolution'] * 0.01

        self.ss = Data85_soundspeed(datablock[self.hdr_sz:-1], depth_resolution)
        self.last_byte = datablock[-1:]
        self.data = self.ss.header  # backward compatibility

    def get_datablock(self, data=None):
        # FIXME: Not sure what happens if TVG was removed
        part1 = super(Data85, self).get_datablock()
        part2 = self.ss.get_datablock()
        return part1 + part2 + self.last_byte

    def _maketime(self, date, time):
        """
        Makes the time stamp of the current packet as a POSIX time stamp.
        UTC is assumed.
        """
        date = str(date)
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970, 1, 1).toordinal()
        dayseconds = time  # * 0.001
        return numdays * 24 * 60 * 60 + dayseconds

    def plot(self):
        """
        Creates a simple plot of the cast.
        """
        self.ss.plot()

    def get_display_string(self):
        """
        Displays contents of the header to the command window.
        """
        s = super(Data85, self).get_display_string()
        s += "\n"
        s += "POSIXtime : " + str(self.time) + "\n"
        return s


class Data88_xyz(BaseData):
    hdr_dtype = np.dtype([('Depth', 'f'), ('AcrossTrack', 'f'), ('AlongTrack', 'f'),
                          ('WindowLength', 'H'), ('QualityFactor', 'B'), ('IncidenceAngleAdjustment', 'f'),
                          ('Detection', 'B'), ('Cleaning', 'b'), ('Reflectivity', 'f')])
    raw_dtype = np.dtype([('Depth', 'f'), ('AcrossTrack', 'f'), ('AlongTrack', 'f'),
                          ('WindowLength', 'H'), ('QualityFactor', 'B'), ('IncidenceAngleAdjustment', 'b'),
                          ('Detection', 'B'), ('Cleaning', 'b'), ('Reflectivity', 'h')])
    conversions = {'IncidenceAngleAdjustment': 0.1,  # convert to degrees
                   'Reflectivity': 0.1,  # convert to dB
                   }

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data88_xyz, self).__init__(datablock, byteswap=byteswap,
                                         read_limit=read_limit)  # read as many records as passed in


class Data88(BaseData):
    """
    XYZ datagram, 0x58 / 'X' / 88.  All data is in the header list or
    stored in the 'data' array.  Values have been converted to degrees and
    dB.
    """
    hdr_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('Heading', 'f'),
                          ('SoundSpeed', 'f'), ('TransmitDepth', 'f'), ('NumBeams', 'H'),
                          ('NumValid', 'H'), ('SampleFrequency', 'f'), ('Spare', 'i')])
    raw_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('Heading', 'H'),
                          ('SoundSpeed', 'H'), ('TransmitDepth', 'f'), ('NumBeams', 'H'),
                          ('NumValid', 'H'), ('SampleFrequency', 'f'), ('Spare', 'i')])
    conversions = {'Heading': 0.01,  # convert to degrees
                   'SoundSpeed': 0.1,  # convert to m/s
                   }

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data88, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.read(datablock[self.hdr_sz:])  # calling this way to maintain backward compatibility

    def read(self, datablock):
        """
        Reads the data section of the record.
        """
        # buffer length goes to -1 because of the uint8 buffer before etx
        self.xyz = Data88_xyz(datablock[:-1])
        self.last_byte = datablock[-1:]
        self.data = self.xyz.header

    def get_datablock(self, data=None):
        # FIXME: missing one character at the end??  See the read function
        part1 = super(Data88, self).get_datablock()
        part2 = self.xyz.get_datablock()
        return part1 + part2 + self.last_byte


class Data89_beaminfo(BaseData):
    hdr_dtype = np.dtype([('SortingDirection', 'b'), ('DetectionInfo', 'B'),
                          ('#SamplesPerBeam', 'H'), ('CenterSample#', 'H')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data89_beaminfo, self).__init__(datablock, byteswap=byteswap,
                                              read_limit=read_limit)  # read as many records as passed in


class Data89_samples(BaseData):
    hdr_dtype = np.dtype([('Amplitude', "f2")])  # FIXME: float16 is right type?
    raw_dtype = np.dtype([('Amplitude', "h")])
    conversions = {'Amplitude': 0.1,
                   }

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data89_samples, self).__init__(datablock, byteswap=byteswap,
                                             read_limit=read_limit)  # read as many records as passed in


class Data89(BaseData):
    """
    Seabed Image datagram 059h / 89d / 'Y'.
    """
    hdr_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('SamplingFreq', 'f'), ('RangeToNormal', 'H'), ('NormalBackscatter', "f"),
                          ('ObliqueBackscatter', "f"), ('TXBeamWidth', "f"), ('TVGCrossover', "f"),
                          ('NumberValidBeams', 'H')])
    raw_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('SamplingFreq', 'f'), ('RangeToNormal', 'H'), ('NormalBackscatter', "h"),
                          ('ObliqueBackscatter', "h"), ('TXBeamWidth', "H"), ('TVGCrossover', "H"),
                          ('NumberValidBeams', 'H')])
    conversions = {'NormalBackscatter': 0.1, 'ObliqueBackscatter': 0.1,
                   'TXBeamWidth': 0.1, 'TVGCrossover': 0.1,
                   }

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data89, self).__init__(datablock, byteswap=byteswap)
        numbeams = self.header[-1]
        self.time = POSIXtime

        self._read(datablock[self.hdr_sz:], numbeams)

    def _read(self, datablock, numbeams):
        """
        Reads the data section of the record. Backscatter is stored in one long
        array.  Use the included carve method to reshape the time series data
        into an array. Note the existance of the beam_position array that
        points to the start of each array.
        """
        samples_dtype = np.dtype([('Amplitude', "h")])
        self.beaminfo_data = Data89_beaminfo(datablock, read_limit=numbeams)
        self.beaminfo = self.beaminfo_data.header
        p = Data89_beaminfo.hdr_sz * numbeams
        t = self.beaminfo['#SamplesPerBeam'].sum()
        self.samples_data = Data89_samples(datablock[p:], read_limit=t)
        self.samples = self.samples_data.Amplitude

        self.beam_position = np.zeros(self.beaminfo['#SamplesPerBeam'].shape, dtype=np.uint32)
        for n in range(len(self.beam_position) - 1):
            self.beam_position[n + 1] = self.beaminfo['#SamplesPerBeam'][n] + self.beam_position[n]

    def get_datablock(self, data=None):
        # FIXME: Not sure what happens if reshape is called
        part1 = super(Data89, self).get_datablock()
        part2 = self.beaminfo_data.get_datablock()
        part3 = self.samples_data.get_datablock()
        return part1 + part2 + part3

    def reshape(self):
        """
        Reshapes the samples array and carves it into chunks. A 2D array is
        returned.
        """
        numbeams = self.header[-1]
        c = self.beaminfo['CenterSample#']
        t = self.beaminfo['#SamplesPerBeam']
        s = self.beaminfo['SortingDirection']
        # figure the array size
        bottom = t - c
        top = c.copy()
        idx = np.nonzero(s < 0)[0]
        top[idx] = bottom[idx]
        bottom[idx] = c[idx]
        maxsamples = top.max() + bottom.max()
        self.samplearray = np.zeros((maxsamples, numbeams), dtype=np.float16)
        self.samplearray[:] = np.nan
        centerpos = top.max()
        for n in range(len(self.beaminfo)):
            if t[n] > 0:
                pointer = self.beam_position[n]
                beamsamples = self.samples[pointer:pointer + t[n]]
                start = centerpos - top[n]
                self.samplearray[start:start + t[n], n] = beamsamples[::s[n]]
        return self.samplearray, centerpos

    def center(self):
        """
        Returns the center sample, which is at the bottom detection.
        """
        # at times the outer most beam has overflowed the max index.
        # this leads me to believe that the center sample counts with the first
        # sample in each beam, so the center is the start + the center count -1
        # GAR 20150127
        idx = self.beam_position + self.beaminfo['CenterSample#'] - 1
        center = self.samples[idx]
        sidx = np.nonzero(self.beaminfo['SortingDirection'] == -1)[0]
        idx = self.beam_position[sidx + 1] - self.beaminfo['CenterSample#'][sidx]
        center[sidx] = self.samples[idx]
        return center

    def plot(self):
        """
        Plots the output from the "center" method.
        """
        data, cidx = self.center()
        # beams = range(self.header[-1])
        # samples = range(-1*cidx, len(data)-cidx)
        # X,Y = np.meshgrid(beams, samples)
        # plt.pcolormesh(X,Y,data, cmap = 'gray')
        plt.imshow(data, aspect='auto', cmap='gray', interpolation='none')
        plt.clim((-80, 0))


class Data102_nrx(BaseData):
    hdr_dtype = np.dtype([('BeamPointingAngle', "f"), ('Range', "f"),
                          ('TransmitSectorID', 'B'), ('Reflectivity', "f"), ('QualityFactor', 'B'),
                          ('DetectionWindowLength', 'B'), ('BeamNumber', 'h'), ('Spare', 'H')])
    raw_dtype = np.dtype([('BeamPointingAngle', "h"), ('Range', "H"),
                          ('TransmitSectorID', 'B'), ('Reflectivity', "b"), ('QualityFactor', 'B'),
                          ('DetectionWindowLength', 'B'), ('BeamNumber', 'h'), ('Spare', 'H')])
    conversions = {'BeamPointingAngle': 0.01, 'Range': 0.25, 'Reflectivity': 0.5}

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data102_nrx, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in


class Data102_ntx(BaseData):
    hdr_dtype = np.dtype([('TiltAngle', "f"), ('FocusRange', "f"),
                          ('SignalLength', "f"), ('Delay', "f"),
                          ('CenterFrequency', 'I'), ('Bandwidth', "I"), ('SignalWaveformID', 'B'),
                          ('TransmitSector#', 'B')])
    raw_dtype = np.dtype([('TiltAngle', "h"), ('FocusRange', "H"),
                          ('SignalLength', "I"), ('Delay', "I"),
                          ('CenterFrequency', 'I'), ('Bandwidth', "H"), ('SignalWaveformID', 'B'),
                          ('TransmitSector#', 'B')])
    conversions = {'TiltAngle': 0.01, 'FocusRange': 0.1,
                   'SignalLength': 10 ** -6, 'Delay': 10 ** -6,
                   'Bandwidth': 10}

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data102_ntx, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in


class Data102(BaseData):
    """
    Range and angle datagram, 66h / 102 / 'f'.  All values are converted to
    whole units, meaning meters, seconds, degrees, Hz, etc.
    """
    hdr_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('Ntx', 'H'), ('Nrx', 'H'), ('SamplingFrequency', "f"), ('Depth', "f"),
                          ('SoundSpeed', "f"), ('MaximumBeams', 'H'), ('Spare1', 'H'), ('Spare2', 'H')])
    raw_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('Ntx', 'H'), ('Nrx', 'H'), ('SamplingFrequency', "I"), ('Depth', "i"),
                          ('SoundSpeed', "H"), ('MaximumBeams', 'H'), ('Spare1', 'H'),
                          ('Spare2', 'H')])
    conversions = {'SoundSpeed': 0.1, 'SamplingFrequency': 0.01, 'Depth': 0.01}

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data102, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.read(datablock[self.hdr_sz:-1])

    def read(self, datablock):
        """
        Reads the data section of the record and converts values to whole
        units.
        """
        ntx = self.header['Ntx']
        nrx = self.header['Nrx']
        # read ntx
        self.tx_data = Data102_ntx(datablock, read_limit=ntx)
        self.tx = self.tx_data.header  # maintain backward compatibility

        # read nrx -- skip over the tx data in the block
        self.rx_data = Data102_nrx(datablock[ntx * self.tx_data.hdr_sz:], read_limit=nrx)
        self.rx = self.rx_data.header  # maintain backward compatibility

        # include the twowaytraveltime from the provided range and sampling freq following the datagram note
        self.rx_data.TravelTime = self.rx_data.Range / self.SamplingFrequency
        try:
            self.rx = append_fields(self.rx_data.header, 'TravelTime', self.rx_data.TravelTime, dtypes=np.float32)
        except TypeError:  # only one traveltime found, so the dtype is float32
            self.rx = append_fields(self.rx_data.header, 'TravelTime', [self.rx_data.TravelTime], dtypes=np.float32)

    def get_datablock(self, data=None):
        # FIXME: Not sure what happens if TVG was removed
        part1 = super(Data102, self).get_datablock()
        part2 = self.tx_data.get_datablock()
        part3 = self.rx_data.get_datablock()
        return part1 + part2 + part3


class Data104(BaseData):
    """
    Depth (pressure) or height datagram, 0x68h / 'h' / 104.  Height information
    is converted to meters.
    """
    hdr_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('Height', "f"), ('HeightType', 'B')])
    raw_dtype = np.dtype([('Counter', 'H'), ('SystemSerial#', 'H'),
                          ('Height', "i"), ('HeightType', 'B')])
    conversions = {'Height': 0.01}

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the record."""
        super(Data104, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime


class Data107_nrx(BaseData):
    """This class is a bit different since the data is intertwined.  The datagrams 
    are written header followed by samples where the number of samples is in the header."""
    hdr_dtype = np.dtype([('BeamPointingAngle', "f"), ('StartRangeSample#', 'H'),
                          ('NumberSamples', 'H'), ('DetectedRange', 'H'), ('TransmitSector#', 'B'),
                          ('Beam#', 'B')])
    raw_dtype = np.dtype([('BeamPointingAngle', "h"),
                          ('StartRangeSample#', 'H'), ('NumberSamples', 'H'),
                          ('DetectedRange', 'H'), ('TransmitSector#', 'B'),
                          ('Beam#', 'B')])

    def __init__(self, datablock, byteswap=False, read_limit=None):
        # declare rx stuff
        if read_limit is None:
            raise Exception("Must specify a number of rx datagrams to read")
        p = 0  # pointer to where we are in the datablock
        nrx_sz = self.hdr_size
        nrx = read_limit
        self.header = np.zeros(nrx, dtype=self.raw_dtype)

        # declare amplitudes stuff
        amp_dtype = np.dtype([('SampleAmplitude', "b")])
        numamp = len(datablock) - nrx_sz * nrx  # figures out the total number of amplitudes in the datablock
        # Initialize array to NANs. Source:http://stackoverflow.com/a/1704853/1982894
        tempamp = np.empty(numamp, dtype=amp_dtype)
        tempamp[:] = np.NAN
        # get the rx and amplitude data
        pamp = 0
        for n in range(nrx):
            self.header[n] = np.frombuffer(datablock[p:p + nrx_sz], dtype=self.raw_dtype)
            p += nrx_sz
            # the number of samples for this beam
            beamsz = self.header[n][2]
            tempamp[pamp:pamp + beamsz] = np.frombuffer(datablock[p:p + beamsz], dtype=amp_dtype)
            p += beamsz
            pamp += beamsz
        self.header = self.header.astype(self.hdr_dtype)
        self.header['BeamPointingAngle'] *= 0.01
        # unwined the beam data into an array
        numsamples = self.header['NumberSamples']
        self.ampdata = np.empty((numsamples.max(), nrx), dtype=np.float32)
        self.ampdata[:] = np.NAN
        pamp = 0
        for n in range(nrx):
            self.ampdata[:numsamples[n], n] = 0.5 * tempamp[pamp:pamp + numsamples[n]].astype(np.float32)
            pamp += numsamples[n]

    def get_datablock(self, data=None):
        raise Exception("Not implemented")


class Data107_ntx(BaseData):
    hdr_dtype = np.dtype([('TiltTx', "f"), ('CenterFrequency', "I"),
                          ('TransmitSector#', 'B'), ('Spare', 'B')])
    raw_dtype = np.dtype([('TiltTx', "h"), ('CenterFrequency', "H"),
                          ('TransmitSector#', 'B'), ('Spare', 'B')])
    conversions = {'TiltTx': 0.01, 'CenterFrequency': 10}

    def __init__(self, datablock, byteswap=False, read_limit=None):
        super(Data107_ntx, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in


class Data107(BaseData):
    """
    The water column datagram, 6Bh / 107d / 'k'.  The receiver beams are roll
    stabilized.  Units have been shifted to whole units as in hertz, meters, 
    seconds, etc.  Watercolumn data is in ampdata as 0.5 dB steps.
    """
    hdr_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('#OfDatagrams', 'H'), ('Datagram#', 'H'), ('#TxSectors', 'H'),
                          ('Total#Beams', 'H'), ('NumberBeamsInDatagram', 'H'), ('SoundSpeed', "f"),
                          ('SamplingFrequency', "d"), ('TxHeave', "f"), ('TVGfunction', 'B'),
                          ('TVGoffset', 'b'), ('ScanningInfo', 'B'), ('Spare', '3B')])
    raw_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('#OfDatagrams', 'H'), ('Datagram#', 'H'), ('#TxSectors', 'H'),
                          ('Total#Beams', 'H'), ('NumberBeamsInDatagram', 'H'), ('SoundSpeed', "H"),
                          ('SamplingFrequency', "I"), ('TxHeave', "h"), ('TVGfunction', 'B'),
                          ('TVGoffset', 'b'), ('ScanningInfo', 'B'), ('Spare', '3B')])
    conversions = {'SoundSpeed': 0.1, 'SamplingFrequency': 0.01, 'TxHeave': 0.01}

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data107, self).__init__(datablock, byteswap=byteswap)
        self.hasTVG = True
        self.time = POSIXtime
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        """
        Reads the variable section of the datagram.
        """
        # declare tx stuff
        ntx = self.header[4]
        # get the tx data
        self.tx_data = Data107_ntx(datablock, read_limit=ntx)
        self.tx = self.tx_data.header
        p = ntx * self.tx_data.hdr_sz
        nrx = self.header[6]
        self.rx_data = Data107_nrx(datablock[p:], read_limit=nrx)
        self.rx = self.rx_data.header
        self.ampdata = self.rx_data.ampdata

    def get_datablock(self, data=None):
        # FIXME: Not sure what happens if TVG was removed
        part1 = super(Data107, self).get_datablock()
        part2 = self.tx_data.get_datablock()
        part3 = self.rx_data.get_datablock()
        return part1 + part2 + part3

    def deTVG(self, absorption, OFS, usec=True):
        """
        Removes the TVG function from the ampdata.  The TVG will be removed
        only if the hasTVG flag is set to True. A value for Alpha and OFS need
        to be provided since they do not exist in the water column datagram.
        The TVG function removed (from the datagram definition) is
        func_TVG = X * log(R) + 2 * Absorption * R + OFS + C
        Set the kwarg 'usec' to False to avoid applying the header c value.

        Absorption should be supplied in dB / m.
        """
        x = self.header['TVGfunction']
        if usec:
            c = self.header['TVGoffset']
        else:
            c = 0
        s = self.header['SoundSpeed']
        dt = self.header['SamplingFrequency']
        r = np.arange(len(self.ampdata)) * s / (2 * dt)
        f = x * np.log10(r) + 2 * absorption * r / 1000. + OFS + c
        f[0] = OFS + c
        f.shape = (len(f), -1)
        self.ampdata -= f
        self.hasTVG = False

    def plot(self):
        """
        Plots the watercolumn data.
        """
        a = self.rx['BeamPointingAngle']
        r = np.arange(len(self.ampdata))
        A, R = np.meshgrid(a, r)
        # swap sides through -1 to make the negative angle be the positive direction
        X = -1 * R * np.sin(np.deg2rad(A))
        Y = R * np.cos(np.deg2rad(A))
        plt.figure()
        im = plt.pcolormesh(X, Y, self.ampdata)
        plt.ylim((r.max(), 0))
        c = plt.colorbar()
        c.set_label('dB re $1\mu Pa$ at 1 meter')
        plt.xlabel('Across Track (meters)')
        plt.ylabel('Depth (meters)')
        cstd = np.nanstd(self.ampdata)
        cmean = np.nanmean(self.ampdata)
        im.set_clim((cmean - 3 * cstd, cmean + 3 * cstd))
        plt.grid()
        plt.draw()


class Data109(BaseData):
    """
    The Stave Data Datagram, 6Dh / 109d / 'm'.  This data definition does not
    exist in the normal documentation.  All values are converted to whole
    units.
    """
    hdr_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('#Datagrams', 'H'), ('Datagram#', 'H'), ('RxSamplingFrequency', "f"),
                          ('SoundSpeed', "f"), ('StartRangeRefTx', 'H'), ('TotalSample', 'H'),
                          ('#SamplesInDatagram', 'H'), ('Stave#', 'H'), ('#StavesPerSample', 'H'),
                          ('RangeToNormal', 'H'), ('Spare', 'H')])
    raw_dtype = np.dtype([('PingCounter', 'H'), ('SystemSerial#', 'H'),
                          ('#Datagrams', 'H'), ('Datagram#', 'H'), ('RxSamplingFrequency', "I"),
                          ('SoundSpeed', "H"), ('StartRangeRefTx', 'H'), ('TotalSample', 'H'),
                          ('#SamplesInDatagram', 'H'), ('Stave#', 'H'), ('#StavesPerSample', 'H'),
                          ('RangeToNormal', 'H'), ('Spare', 'H')])
    conversions = {'RxSamplingFrequency': 0.01, 'SoundSpeed': 0.1}

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        super(Data109, self).__init__(datablock, byteswap=byteswap)
        self.read(datablock[self.hdr_sz:])
        self.time = POSIXtime

    def read(self, datablock):
        """
        Reads the data portion of this datablock.  Data formats are defined
        after the header is read to accomidate sizes defined in the header.
        All values are converted to whole units.
        """
        Ns = self.header['#SamplesInDatagram']
        Ne = self.header['#StavesPerSample']
        read_fmt = str(Ne) + 'b'
        used_fmt = str(Ne) + 'f'
        read_dtype = np.dtype([('Sample#', 'H'), ('TvgGain', "h"),
                               ('StaveBackscatter', read_fmt)])
        self._read_dtype = read_dtype
        read_sz = read_dtype.itemsize
        used_dtype = np.dtype([('Sample#', 'H'), ('TvgGain', "f"),
                               ('StaveBackscatter', read_fmt)])
        self.data = np.frombuffer(datablock[:Ns * read_sz],
                                  dtype=read_dtype)
        self.data = self.data.astype(used_dtype)
        self.data['TvgGain'] *= 0.01
        self.data['StaveBackscatter'] *= 0.5

    def get_datablock(self, data=None):
        part1 = super(Data109, self).get_datablock()
        tmp_data = self.data.copy()
        tmp_data['TvgGain'] /= 0.01
        tmp_data['StaveBackscatter'] /= 0.5
        tmp_data = self.data.astype(self._read_dtype)
        # part2 = np.getbuffer(tmp_data)
        part2 = tmp_data.tobytes()
        return part1 + part2


class Data110_grp(BaseData):
    hdr_dtype = np.dtype([('GroupStart', 'S4'), ('GroupID', 'H'),
                          ('ByteCount', 'H'), ('Time1', 'd'), ('Time2', 'd'),
                          ('DistanceTag', 'd'), ('TimeTypes', 'B'), ('DistanceType', 'B'),
                          ('Latitude', 'd'), ('Longitude', 'd'), ('Altitude', 'd'),
                          ('AlongTrackVelocity', 'f'), ('AcrossTrackVelocity', 'f'),
                          ('DownVelocity', 'f'), ('Roll', 'd'), ('Pitch', 'd'),
                          ('Heading', 'd'), ('WanderAngle', 'd'), ('Heave', 'f'),
                          ('RollRate', 'f'), ('PitchRate', 'f'), ('YawRate', 'f'),
                          ('LongitudinalAcceleration', 'f'), ('TransverseAcceleration', 'f'),
                          ('DownAcceleration', 'f'), ('Pad', 'H'), ('CheckSum', 'H'),
                          ('MessageEnd', 'S2')])

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        super(Data110_grp, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in
        self.time = POSIXtime
        packettime = dtm.datetime.utcfromtimestamp(POSIXtime)
        # subtract 1 because the first day of the year does not start with zero
        ordinal = packettime.toordinal()
        dow = packettime.weekday() + 1.
        if dow == 7:
            # shift sunday to be start of week.
            dow = 0
        # 1970-1-1 is julian day 719163
        POSIXdays = ordinal - 719163. - dow
        self.weektime = POSIXdays * 24. * 3600.


class Data110_aaq(BaseData):
    hdr_dtype = np.dtype([('Header1', 'B'), ('Header2', 'B'),
                          ('Seconds', 'i'), ('FracSeconds', 'f'), ('Latitude', 'f'),
                          ('Longitude', 'f'), ('Altitude', 'f'), ('Heave', 'f'),
                          ('NorthVelocity', 'f'), ('EastVelocity', 'f'),
                          ('DownVelocity', 'f'), ('Roll', 'f'), ('Pitch', 'f'),
                          ('Heading', 'f'), ('RollRate', 'f'), ('PitchRate', 'f'),
                          ('YawRate', 'f'), ('StatusWord', 'H'), ('CheckSum', 'H')])
    raw_dtype = np.dtype([('Header1', 'B'), ('Header2', 'B'),
                          ('Seconds', '>i'), ('FracSeconds', '>H'), ('Latitude', '>i'),
                          ('Longitude', '>i'), ('Altitude', '>i'), ('Heave', '>h'),
                          ('NorthVelocity', '>h'), ('EastVelocity', '>h'),
                          ('DownVelocity', '>h'), ('Roll', '>h'), ('Pitch', '>h'),
                          ('Heading', '>H'), ('RollRate', '>h'), ('PitchRate', '>h'),
                          ('YawRate', '>h'), ('StatusWord', '>H'), ('CheckSum', '>H')])
    conversions = {'FracSeconds': 0.0001, 'Latitude': 90. / 2 ** 30, 'Longitude': 90. / 2 ** 30,
                   'Altitude': 0.01, 'Heave': 0.01, 'NorthVelocity': 0.01, 'EastVelocity': 0.01,
                   'DownVelocity': 0.01, 'Roll': 90. / 2 ** 14, 'Pitch': 90. / 2 ** 14,
                   'Heading': 90. / 2 ** 14, 'RollRate': 90. / 2 ** 14,
                   'PitchRate': 90. / 2 ** 14, 'YawRate': 90. / 2 ** 14}

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        super(Data110_aaq, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in
        
class Data110_aas(BaseData):
    hdr_dtype = np.dtype([('Header1', 'B'), ('Header2', 'B'),
                          ('Seconds', 'i'), ('FracSeconds', 'f'), ('Latitude', 'f'),
                          ('Longitude', 'f'), ('Altitude', 'f'), ('Heave', 'f'),
                          ('NorthVelocity', 'f'), ('EastVelocity', 'f'),
                          ('DownVelocity', 'f'), ('Roll', 'f'), ('Pitch', 'f'),
                          ('Heading', 'f'), ('RollRate', 'f'), ('PitchRate', 'f'),
                          ('YawRate', 'f'), ('DelayedHeaveSeconds', 'i'), ('DelayedHeaveFracSeconds', 'f'),
                          ('DelayedHeave', 'f'), ('StatusWord', 'H'), ('CheckSum', 'H')])
    raw_dtype = np.dtype([('Header1', 'B'), ('Header2', 'B'),
                          ('Seconds', '>i'), ('FracSeconds', '>H'), ('Latitude', '>i'),
                          ('Longitude', '>i'), ('Altitude', '>i'), ('Heave', '>h'),
                          ('NorthVelocity', '>h'), ('EastVelocity', '>h'),
                          ('DownVelocity', '>h'), ('Roll', '>h'), ('Pitch', '>h'),
                          ('Heading', '>H'), ('RollRate', '>h'), ('PitchRate', '>h'),
                          ('YawRate', '>h'), ('DelayedHeaveSeconds', '>i'), ('DelayedHeaveFracSeconds', '>H'),
                          ('DelayedHeave', '>h'), ('StatusWord', '>H'), ('CheckSum', '>H')])
    conversions = {'FracSeconds': 0.0001, 'Latitude': 90. / 2 ** 30, 'Longitude': 90. / 2 ** 30,
                   'Altitude': 0.01, 'Heave': 0.01, 'NorthVelocity': 0.01, 'EastVelocity': 0.01,
                   'DownVelocity': 0.01, 'Roll': 90. / 2 ** 14, 'Pitch': 90. / 2 ** 14,
                   'Heading': 90. / 2 ** 14, 'RollRate': 90. / 2 ** 14,
                   'PitchRate': 90. / 2 ** 14, 'YawRate': 90. / 2 ** 14, 'DelayedHeaveFracSeconds': 0.0001,
                   'DelayedHeave': 0.01}

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        super(Data110_aas, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in


class Data110_q42(BaseData):
    hdr_dtype = np.dtype([('Header', 'S1'),
                          ('Seconds', 'i'), ('FracSeconds', 'f'), ('Latitude', 'f'),
                          ('Longitude', 'f'), ('Altitude', 'f'), ('Heave', 'f'),
                          ('NorthVelocity', 'f'), ('EastVelocity', 'f'),
                          ('DownVelocity', 'f'), ('Roll', 'f'), ('Pitch', 'f'),
                          ('Heading', 'f'), ('RollRate', 'f'), ('PitchRate', 'f'),
                          ('YawRate', 'f'), ('StatusWord', 'H'), ('CheckSum', 'H')])
    raw_dtype = np.dtype([('Header', 'S1'),
                          ('Seconds', '>i'), ('FracSeconds', '>B'), ('Latitude', '>i'),
                          ('Longitude', '>i'), ('Altitude', '>i'), ('Heave', '>h'),
                          ('NorthVelocity', '>h'), ('EastVelocity', '>h'),
                          ('DownVelocity', '>h'), ('Roll', '>h'), ('Pitch', '>h'),
                          ('Heading', '>H'), ('RollRate', '>h'), ('PitchRate', '>h'),
                          ('YawRate', '>h'), ('StatusWord', '>H'), ('CheckSum', '>H')])
    conversions = {'FracSeconds': 0.01, 'Latitude': 90. / 2 ** 30, 'Longitude': 90. / 2 ** 30,
                   'Altitude': 0.01, 'Heave': 0.01, 'NorthVelocity': 0.01, 'EastVelocity': 0.01,
                   'DownVelocity': 0.01, 'Roll': 90. / 2 ** 14, 'Pitch': 90. / 2 ** 14,
                   'Heading': 90. / 2 ** 14, 'RollRate': 90. / 2 ** 14,
                   'PitchRate': 90. / 2 ** 14, 'YawRate': 90. / 2 ** 14}

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        super(Data110_q42, self).__init__(datablock, byteswap=byteswap,
                                          read_limit=read_limit)  # read as many records as passed in


class Data110_att(BaseData):
    hdr_dtype = np.dtype([('Time', 'd'), ('Roll', 'f'), ('Pitch', 'f'), ('Heave', 'f'),
                          ('Heading', 'f'), ('NumBytesInput', 'B')])
    raw_dtype = np.dtype([('Time', 'H'), ('Roll', 'h'), ('Pitch', 'h'), ('Heave', 'h'),
                          ('Heading', 'H'), ('NumBytesInput', 'B')])
    conversions = {'Time': 0.001, 'Roll': 0.01, 'Pitch': 0.01, 'Heave': 0.01, 'Heading': 0.01}

    def __init__(self, datablock, POSIXtime, byteswap=False, read_limit=None):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        if read_limit is None:
            raise Exception("read_limit can not be None for Data110_att")
        # Data110 can have an odd number of bytes for the datablock.  Kongsberg adds a \x00 byte to the datablock if
        #   datagram is an odd number of bytes.
        self.padding = b''
        if len(datablock) % 2 and datablock.endswith(b'\x00'):
            self.padding = datablock[-1:]
            datablock = datablock[:-1]
        raw_data_size = int(len(datablock) / read_limit - self.hdr_sz)
        raw_data_dtype = np.dtype([('Raw', 'V' + str(raw_data_size))])  # use void, if string is used then numpy will truncate a trailing \x00
        combined_dtype = np.dtype([('Proc', Data110_att.raw_dtype), ('Raw', raw_data_dtype)])
        temp = np.frombuffer(datablock[:read_limit * combined_dtype.itemsize], dtype=combined_dtype)
        self.header = temp['Proc'].astype(Data110_att.hdr_dtype)
        self.time = POSIXtime
        self._parse_raw(temp['Raw'], raw_data_size, read_limit)
        # self.data = np.zeros(self.numrecords, dtype = att_file_dtype)
        # datap = 0
        # for i in range(self.numrecords):
        # temp = np.frombuffer(datablock[datap:att_sz+datap],
        # dtype = att_file_dtype)
        # datap += att_sz + temp['NumBytesInput'][0]
        # self.data[i] = temp[['Time', 'Roll', 'Pitch', 'Heave', 'Heading']].astype(Data110.att_dtype)
        self._convert()
        self.header['Time'] += self.time

    def _parse_raw(self, raw_arrays, raw_data_size, read_limit):
        """
        Parses the raw data that arrived in SIS and puts it in source_data.  If
        the data type is not known source_data is None.
        """
        first_record = bytes(raw_arrays[0][0])
        self.raw_padding=[]
        if first_record[0:4] == b'$GRP':
            datablock = b""
            for raw in raw_arrays:
                r = raw.tobytes()  # same as bytes(raw), faster?
                datablock += r[:Data110_grp.hdr_sz]
                self.raw_padding.append(r[Data110_grp.hdr_sz:])
            self.raw_data = Data110_grp(datablock, self.time, read_limit=read_limit)
            self.weektime = self.raw_data.weektime
            self.source = 'GRP102'
        elif first_record[:2] == b'\xaaQ':  # seapath binary 23 format, see seatex format document
            datablock = b""
            for raw in raw_arrays:
                r = raw.tobytes()  # same as bytes(raw)
                datablock += r[:Data110_aaq.hdr_sz]
                self.raw_padding.append(r[Data110_grp.hdr_sz:])
            self.raw_data = Data110_aaq(datablock, self.time, read_limit=read_limit)
            self.source = 'binary23'
        elif first_record[:2] == b'\xaaS':  # seapath binary 26 format, see seatex format document
            datablock = b""
            for raw in raw_arrays:
                r = raw.tobytes()  # same as bytes(raw)
                datablock += r[:Data110_aas.hdr_sz]
                self.raw_padding.append(r[Data110_grp.hdr_sz:])
            self.raw_data = Data110_aas(datablock, self.time, read_limit=read_limit)
            self.source = 'binary26'
        elif first_record[0] == 113 and raw_data_size == 43:  # 113 being 'q'
            datablock = b""
            for raw in raw_arrays:
                r = raw.tobytes()  # same as bytes(raw)
                datablock += r[:Data110_q42.hdr_sz]
                self.raw_padding.append(r[Data110_grp.hdr_sz:])
            self.raw_data = Data110_q42(datablock, self.time, read_limit=read_limit)
            self.source = 'binary11'
        elif first_record[:2] == b'\xe88':
            raise NotImplementedError('Data110: Found CodaOctopus MCOM format, this is not currently implemented in the par driver')
        else:
            # self.source_data = np.getbuffer(np.ascontiguousarray(raw_arrays))
            self.source_data = np.ascontiguousarray(raw_arrays).tobytes()
            self.source = 'Unknown'
            raise NotImplementedError('Data110: Found unknown data format, start bytes = {}'.format(first_record[:2]))

    @property
    def source_data(self):
        return self.raw_data.header

    @source_data.setter
    def source_data(self, val):
        self.raw_data.header = val

    def _create_raw_datablocks(self):
        # have to convert the raw and proc back into individual records/arrays
        # Then 'zip' the corresponding proc+raw back to a single record
        # then write them out in order.

        if self.source  in ('GRP102', 'binary23', 'binary11'):
            datablock = [self.raw_data.get_datablock(src) + self.raw_padding[i] for i, src in enumerate(self.source_data)]
        else:
            datablock = self.source_data
        return datablock

    def get_datablock(self, data=None):
        tmp_header = self.header.copy()
        tmp_header['Time'] = (tmp_header['Time'] - self.time)
        tmp_header = self._revert(tmp_header)
        proc_arrays = tmp_header.astype(Data110_att.raw_dtype)
        proc_datas = [arr.tobytes() for arr in proc_arrays]

        raw_datas = self._create_raw_datablocks()
        bytestr = b""
        for i in range(len(proc_datas)):
            bytestr += proc_datas[i] + raw_datas[i]

        return bytestr + self.padding


class Data110(BaseData):
    """
    The Network Attitiude Datagram, 6Eh / 110d / 'n'.  Data is found in the header
    and in the 'data' array.  All values are in degrees, and meters.  The raw
    data is parsed and placed in source_data.
    """

    hdr_dtype = np.dtype([('Counter', 'H'), ('Serial#', 'H'), ('NumEntries', 'H'),
                          ('Sensor', 'B'), ('Spare', 'B')])

    def __init__(self, datablock, POSIXtime, byteswap=False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        super(Data110, self).__init__(datablock, byteswap=byteswap)
        self.time = POSIXtime
        self.read(datablock[self.hdr_sz:])

    def read(self, datablock):
        """Reads the data section of the record.  Time is POSIX time,
        angles are in degrees, distances in meters."""
        self.numrecords = self.header[2]
        self.att_data = Data110_att(datablock, self.time, read_limit=self.numrecords)

    # maintain backward compatibility
    @property
    def source(self):
        return self.att_data.source

    @source.setter
    def source(self, val):
        self.att_data.source = val

    @property
    def data(self):
        return self.att_data.header

    @data.setter
    def data(self, val):
        self.att_data.header = val

    @property
    def source_data(self):
        return self.att_data.source_data

    @source_data.setter
    def source_data(self, val):
        self.att_data.source_data = val

    def get_datablock(self, data=None):
        part1 = super(Data110, self).get_datablock()
        part2 = self.att_data.get_datablock()
        return part1 + part2


class mappack:
    """
    Container for the file packet map.
    """

    def __init__(self, infilename=None):
        """Constructor creates a packmap dictionary"""
        self.packdir = {}
        self.sizedir = {}
        self.numwc = None
        self.dtypes = {
            68: 'Old Depth',
            88: 'New Depth',
            102: 'Old Range/Angle',
            78: 'New Rangle/Angle',
            83: 'Old Seabed Imagry',
            89: 'New Seabead Imagry',
            107: 'Watercolumn',
            79: 'Quality Factor',
            65: 'Serial Attitude',
            110: 'Network Attitude',
            67: 'Clock',
            72: 'Heading',
            80: 'Position',
            71: 'Surface Sound Speed',
            85: 'Sound Speed Profile',
            73: 'Start Parameters',
            105: 'Stop Parameters',
            112: 'Remote Parameters',
            82: 'Runtime Parameters',
            104: 'Height',
            48: 'PU ID Output',
            49: 'PU Status',
            66: 'PU BIST Results',
            51: 'Extra Parameters'
        }
        self.totalfilesize = os.stat(infilename).st_size if infilename else 0
        self.infilename = infilename

    def add(self, type, location=0, time=0, size=0, pingcounter=None):
        """Adds the location (byte in file) to the tuple for the value type"""
        if type in self.packdir:
            if pingcounter is None:
                self.packdir[type].append([location, time, size])
            else:
                self.packdir[type].append([location, time, size, pingcounter])
            self.sizedir[type] += size
        else:
            if pingcounter is None:
                self.packdir[type] = []
                self.packdir[type].append([location, time, size])
            else:
                self.packdir[type] = []
                self.packdir[type].append([location, time, size, pingcounter])
            self.sizedir[type] = size

    def finalize(self):
        # @todo - I don't think this should use just asarray since it makes the integer locations into floats.  a dtype should be supplied instead.
        # >>> d = [(1, 3.5), (2,4.4), (0, 5.5)]
        # >>> a = numpy.asarray(d, dtype=[('pos', numpy.int64), ('time', numpy.float64)])
        # >>> self.packdir[key] = a[a['time'].argsort()]

        for key in list(self.packdir.keys()):
            temp = np.asarray(self.packdir[key])
            tempindx = temp[:, 1].argsort()
            self.packdir[key] = temp[tempindx, :]

    def printmap(self):
        keys = []
        totalsize = 0
        for i, v in self.packdir.items():
            keys.append((int(i), len(v)))
            totalsize += self.sizedir[i]
        keys.sort()
        for key in keys:
            dtype = self.gettype(key[0])
            percent = 100.0 * (self.sizedir[str(key[0])] / self.totalfilesize)
            print(dtype + ' ' + str(key[0]) + ' (' + hex(int(key[0])) + ') has ' + str(
                key[1]) + ' packets and is ' + '%0.2f' % percent + '% of file.')
        print('Total size of all packets: %d' % totalsize)
        print('Total file size %d' % self.totalfilesize)
        print('Percentage of total packet size vs total file size: %0.4f%%' % ((totalsize / self.totalfilesize) * 100.0))

    def getnum(self, recordtype):
        """
        Returns the number of records of the provided record type.
        """
        return len(self.packdir[str(recordtype)])

    def plotmap(self):
        """
        Plots to location of each of the packets in the file.
        """
        keys = sorted(self.packdir.keys())
        plt.figure()
        for key in keys:
            plt.plot(self.packdir[key][:, 0])
        plt.xlabel('Packet Number')
        plt.ylabel('Location in file')
        plt.legend(keys, loc='lower right')
        plt.grid()

    def save(self, outfilename):
        outfile = open(outfilename, 'wb')
        pickle.dump(self.__dict__, outfile)
        outfile.close()

    def gettype(self, dtype):
        if int(dtype) in self.dtypes:
            out = self.dtypes[int(dtype)]
        else:
            out = ''
        return out

    def load(self, infilename):
        infile = open(infilename, 'rb')
        self.__dict__ = pickle.load(infile)
        infile.close()
        self.totalfilesize = os.stat(infilename).st_size


def translate_detectioninfo(arr):
    """
    Translate the binary code to an int identifier
    'detectioninfo' = 0 for amplitude detect, 1 for phase detect, 2 for rejected due to invalid detection

    0xxxxxx0 = amplitude detect, 0xxxxxx1 = phase detect, 1xxxxxxx = rejected
    """
    rslt = np.zeros(arr.shape, dtype=int)
    first_bit_chk = np.bitwise_and(arr, (1 << 0)).astype(bool)
    last_bit_chk = np.bitwise_and(arr, (1 << 7)).astype(bool)

    rslt[np.where(last_bit_chk)] = 2
    rslt[np.intersect1d(np.where(last_bit_chk == False), np.where(first_bit_chk))] = 1
    rslt[np.intersect1d(np.where(last_bit_chk == False), np.where(first_bit_chk == False))] = 0
    return rslt


def translate_yawpitch(arr):
    """
    Translate the binary code to a string identifier

    'yawandpitchstabilization' = 'Y' for Yaw stab, 'P' for pitch stab, 'PY' for both, 'N' for neither
    # xxxxxx00 no yaw stab, xxxxxx10 yaw stab mean vessel heading
    # 1xxxxxxx pitch stab, 0xxxxxxx no pitch stab
    """
    rslt = np.full(arr.shape, 'N', dtype='U2')
    sec_bit_chk = np.bitwise_and(arr, (1 << 1)).astype(bool)
    last_bit_chk = np.bitwise_and(arr, (1 << 7)).astype(bool)

    rslt[np.intersect1d(np.where(last_bit_chk), np.where(sec_bit_chk))] = 'PY'
    rslt[np.intersect1d(np.where(last_bit_chk), np.where(sec_bit_chk == False))] = 'P'
    rslt[np.intersect1d(np.where(last_bit_chk == False), np.where(sec_bit_chk))] = 'Y'
    return rslt


def translate_mode(arr, pingmode=False):
    """
    Translate the binary code to a string identifier

    'mode' = 'CW' for continuous waveform, 'FM' for frequency modulated
    xx0xxxxx for CW, xx1xxxxx for FM

    If pingmode is true (only for EM710, EM302) checks the Ping mode instead of TX Pulse form

    'mode' = 'VS' for Very Shallow, 'SH' for Shallow, 'ME' for Medium, 'DE' for Deep, 'VD' for Very Deep, 'ED' for
    Extra Deep

    xxxx0000 for VS, xxxx0001 for SH, xxxx0010 for ME, xxxx0011 for DE, xxxx0100 for VD, xxxx0101 for ED

    """
    if pingmode:
        rslt = np.zeros(arr.shape, dtype='U2')
        frst_bit_chk = np.bitwise_and(arr, (1 << 0)).astype(bool)
        sec_bit_chk = np.bitwise_and(arr, (1 << 1)).astype(bool)
        thrd_bit_chk = np.bitwise_and(arr, (1 << 2)).astype(bool)
        rslt[np.intersect1d(np.intersect1d(np.where(frst_bit_chk == False), np.where(sec_bit_chk == False)),
                            np.where(thrd_bit_chk == False))] = 'VS'
        rslt[np.intersect1d(np.intersect1d(np.where(frst_bit_chk), np.where(sec_bit_chk == False)),
                            np.where(thrd_bit_chk == False))] = 'SH'
        rslt[np.intersect1d(np.intersect1d(np.where(frst_bit_chk == False), np.where(sec_bit_chk)),
                            np.where(thrd_bit_chk == False))] = 'ME'
        rslt[np.intersect1d(np.intersect1d(np.where(frst_bit_chk), np.where(sec_bit_chk)),
                            np.where(thrd_bit_chk == False))] = 'DE'
        rslt[np.intersect1d(np.intersect1d(np.where(frst_bit_chk == False), np.where(sec_bit_chk == False)),
                            np.where(thrd_bit_chk))] = 'VD'
        rslt[np.intersect1d(np.intersect1d(np.where(frst_bit_chk), np.where(sec_bit_chk == False)),
                            np.where(thrd_bit_chk))] = 'ED'
    else:
        rslt = np.zeros(arr.shape, dtype='U2')
        six_bit_chk = np.bitwise_and(arr, (1 << 5)).astype(bool)
        rslt[np.where(six_bit_chk)] = 'FM'
        rslt[np.where(six_bit_chk == False)] = 'CW'
    return rslt


def translate_mode_two(arr, receiver_fx_gain=False):
    """
    Translate the binary code to a string identifier

    For em2040c and dual head:
    'sub_mode' = 'vsCW', 'shCW', 'meCW', 'loCW', 'vlCW', 'elCW', 'shFM', 'loFM'
    x000xxxx for vsCW, x001xxxx for shCW, x010xxxx for meCW, x011xxxx for loCW, x100xxxx for vlCW,
    x101xxxx for elCW, x110xxxx for shFM, x111xxxx for loFM

    For em2040
    'sub_mode' = 'shCW', 'meCW', 'loCW', '__FM'
    xxxx00xx for shCW, xxxx01xx for meCW, xxxx10xx for loCW, xxxx11xx for FM

    """
    if receiver_fx_gain:
        raise NotImplementedError('Only the more modern modetwo translation is available at this time')
    rslt = np.zeros(arr.shape, dtype='U4')
    if arr[0] > 15:  # theoretically this would be for all the dual head/2040c systems
        five_bit_chk = np.bitwise_and(arr, (1 << 4)).astype(bool)
        six_bit_chk = np.bitwise_and(arr, (1 << 5)).astype(bool)
        seven_bit_chk = np.bitwise_and(arr, (1 << 6)).astype(bool)

        five_true = np.where(five_bit_chk == True)
        six_true = np.where(six_bit_chk == True)
        seven_true = np.where(seven_bit_chk == True)
        five_false = np.where(five_bit_chk == False)
        six_false = np.where(six_bit_chk == False)
        seven_false = np.where(seven_bit_chk == False)

        rslt[np.intersect1d(np.intersect1d(five_false, six_false), seven_false)] = 'vsCW'
        rslt[np.intersect1d(np.intersect1d(five_true, six_false), seven_false)] = 'shCW'
        rslt[np.intersect1d(np.intersect1d(five_false, six_true), seven_false)] = 'meCW'
        rslt[np.intersect1d(np.intersect1d(five_true, six_true), seven_false)] = 'loCW'
        rslt[np.intersect1d(np.intersect1d(five_false, six_false), seven_true)] = 'vlCW'
        rslt[np.intersect1d(np.intersect1d(five_true, six_false), seven_true)] = 'elCW'
        rslt[np.intersect1d(np.intersect1d(five_false, six_true), seven_true)] = 'shFM'
        rslt[np.intersect1d(np.intersect1d(five_true, six_true), seven_true)] = 'loFM'
    else:
        three_bit_chk = np.bitwise_and(arr, (1 << 2)).astype(bool)
        four_bit_chk = np.bitwise_and(arr, (1 << 3)).astype(bool)

        three_true = np.where(three_bit_chk == True)
        four_true = np.where(four_bit_chk == True)
        three_false = np.where(three_bit_chk == False)
        four_false = np.where(four_bit_chk == False)

        rslt[np.intersect1d(three_false, four_false)] = 'shCW'
        rslt[np.intersect1d(three_true, four_false)] = 'meCW'
        rslt[np.intersect1d(three_false, four_true)] = 'loCW'
        rslt[np.intersect1d(three_true, four_true)] = '__FM'
    return rslt


def plot_all_nav(directory='.'):
    """
    Plots the parts of the navarray from all files in the directory.
    """
    fig = plt.figure()
    ax1 = fig.add_subplot(221)
    ax2 = fig.add_subplot(222)
    ax3 = fig.add_subplot(614, sharex=ax2)
    ax4 = fig.add_subplot(615, sharex=ax2)
    ax5 = fig.add_subplot(616, sharex=ax2)
    flist = sorted(glob(directory + '/*.all'))
    clist = ['b', 'r', 'g', 'k', 'y', 'c']
    n = 0
    for f in flist:
        a = AllRead(f)
        if os.path.exists(f + '.nav'):
            a.load_navarray()
        else:
            a._build_navarray()
            a.save_navarray()
        ax1.plot(a.navarray['80'][:, 1], a.navarray['80'][:, 2], clist[n])
        ax1.set_xlabel('Longitude (Degrees)')
        ax1.set_ylabel('Latitude (Degrees)')
        ax1.grid(True)
        ax2.plot(a.navarray['65'][:, 0], a.navarray['65'][:, 4], clist[n])
        ax2.set_ylabel('Heading (Degrees)')
        ax2.set_xlabel('Time (Seconds)')
        ax2.grid(True)
        if '104' in a.navarray:
            ax3.plot(a.navarray['104'][:, 0], a.navarray['104'][:, 1], clist[n])
        ax3.set_ylabel('Height (Meters)')
        ax3.grid(True)
        ax4.plot(a.navarray['65'][:, 0], a.navarray['65'][:, 1], clist[n])
        ax4.plot(a.navarray['65'][:, 0], a.navarray['65'][:, 2], clist[n] + '--')
        ax4.set_ylabel('Degress')
        ax4.legend(('Roll', 'Pitch'))
        ax4.grid(True)
        ax5.plot(a.navarray['65'][:, 0], a.navarray['65'][:, 3], clist[n])
        ax5.set_ylabel('Heave (Meters)')
        ax5.set_xlabel('Time (Seconds)')
        ax5.grid(True)
        n += 1
        if n >= len(clist):
            n = 0
        plt.draw()


def _checksum_all_bytes(bytes):
    # Calculate checksum by sum of bytes method
    bytes = bytearray(bytes)
    chk = sum(bytes) % 2 ** 16
    return np.uint16(chk)


def checksum_raw_rangeangleablock(raw_rangeangleablock):
    # checksum for bytes between STX and ETX
    # Assuming that the format of the datablock is:
    # 4 bytes datagram size, 1 byte STX -- DATA -- 1 byte ETX, 2 byte checksum
    # I.e. 5 bytes excluded at start and 3 bytes at the end
    return _checksum_all_bytes(raw_rangeangleablock[5:-3])


def main():
    if len(sys.argv) > 1:
        a = AllRead(sys.argv[0])
        a.mapfile(True)
        a.close()
    else:
        print("No filename provided.")
        # run_test_mod()


def run_test_mod():
    """ sample for how to modify values and write them back out in a .all file """

    fname = r"C:\PydroTrunk\Collaboration\dasktest\0047_400short_fm_revised.all"
    a = AllRead(fname, mode="r+b")  # open the file for editing
    a.mapfile(True)
    record_type = 110
    rec_num = 0
    p = a.getrecord(record_type, rec_num)
    pos = int(a.map.packdir[str(record_type)][rec_num][0])
    a.infile.seek(pos)
    packetsize = a.packet.header['Bytes'] + 4
    print(list(zip(a.packet.header.dtype.names, a.packet.header)))
    print(a.packet.subpack)
    original_bytes = a.infile.read(packetsize)
    print(original_bytes)
    revised_bytes = a.packet.get_datablock()
    print(revised_bytes)
    print(len(original_bytes) == len(revised_bytes))
    # a.overwrite_record(record_type, rec_num, revised_bytes)
    # raise RuntimeError()


    # change roll
    record_type = 110
    for i, rec in enumerate(a.map.packdir[str(record_type)]):
        # @todo make a function that accesses/returns the a.packet object instead of just the subpack data
        sub_data = a.getrecord(record_type, i)
        # the allread keeps the packet and data inside a.packet and a.packet.subpack
        # to make sure we don't accidentally make copies and write the wrong data out we'll operate on that data.
        # for data110 there are two rolls, one in the header of the main packet (kongsberg) and one in the attitude senosr (PosMV etc)
        a.packet.subpack.att_data.Roll *= 0.0
        a.packet.subpack.att_data.raw_data.Roll *= 0.0
        a.packet.subpack.att_data.Roll *= 0.5
        a.packet.subpack.att_data.raw_data.Roll += 0.5
        revised_bytes = a.packet.get_datablock()
        # @todo It would be nice if Allread would remember where the packet came from so we could just do 'overwrite()' using current packet
        a.overwrite_record(record_type, i, revised_bytes)


    # change traveltimes
    record_type = 78
    for i, rec in enumerate(a.map.packdir[str(record_type)]):
        # @todo make a function that accesses/returns the a.packet object instead of just the subpack data
        sub_data = a.getrecord(record_type, i)
        # the allread keeps the packet and data inside a.packet and a.packet.subpack
        # to make sure we don't accidentally make copies and write the wrong data out we'll operate on that data.
        a.packet.subpack.rx_data.TravelTime *= 0.0
        a.packet.subpack.rx_data.TravelTime += 0.5
        revised_bytes = a.packet.get_datablock()
        a.overwrite_record(record_type, i, revised_bytes)

    # change roll
    record_type = 65
    for i, rec in enumerate(a.map.packdir[str(record_type)]):
        # @todo make a function that accesses/returns the a.packet object instead of just the subpack data
        sub_data = a.getrecord(record_type, i)
        # the allread keeps the packet and data inside a.packet and a.packet.subpack
        # to make sure we don't accidentally make copies and write the wrong data out we'll operate on that data.
        a.packet.subpack.att.Roll *= 0.0
        a.packet.subpack.att.Roll += 0.5
        revised_bytes = a.packet.get_datablock()
        # @todo It would be nice if Allread would remember where the packet came from so we could just do 'overwrite()' using current packet
        a.overwrite_record(record_type, i, revised_bytes)


class useall(AllRead):
    """
    Built as a subclass of the allRead class to perform higher level functions.
    The file is mapped and the navigation array is built upon init.

    ***Not currently working in Python 3.8, I basically designed Kluster to do all of these things - Eric***
    
    """

    def __init__(self, infilename, reload_map=True, save_filemap=True,
                 verbose=False, byteswap=False):
        AllRead.__init__(self, infilename, verbose, byteswap)
        if reload_map and os.path.exists(infilename + '.par'):
            self.loadfilemap()
        else:
            self.mapfile(show_progress=verbose)
            if save_filemap:
                self.savefilemap()

        if reload_map and os.path.exists(infilename + '.nav'):
            self.load_navarray(verbose)
        else:
            self._build_navarray(allrecords=True)
            if save_filemap:
                self.save_navarray(verbose)
        self.has_reported_error()
        self.installation_parameters = self.getrecord(73, 0)
        self.reset()

    def has_reported_error(self, print_error=True):
        """
        error_found = has_reported_error(**print_error)
        This method looks for reported errors in the runtime parameter flags
        (such as SonarHeadOrTransceiverStatus, BSPStatus, ProcessingUnitStatus,
        and OperatorStationStatus) and returns a boolean indicating if an error
        was found.

        *args
        -----

        None

        **kwargs
        --------

        print_error : If set to True (default) the error type is printed.

        returns
        -------

        error_found: a boolean indicating if an error was reported in any one
                     of the runtime parameters flags.
        """
        error_found = False
        try:
            self._build_runtime_array()
            if np.any(self._runtime_array['RuntimePacket']['SonarHeadOrTransceiverStatus']):
                print('***Sonar Head or Transceiver Status error found in Runtime Parameters***')
                error_found = True
            if np.any(self._runtime_array['RuntimePacket']['BSPStatus']):
                print('***BSP Status error found in Runtime Parameters***')
                error_found = True
            if np.any(self._runtime_array['RuntimePacket']['ProcessingUnitStatus']):
                print('***Processing Unit Status error found in Runtime Parameters***')
                error_found = True
            if np.any(self._runtime_array['RuntimePacket']['OperatorStationStatus']):
                print('***Operator Station Status error found in Runtime Parameters***')
                error_found = True
        except KeyError:
            print('Warning: No Runtime records found in file.')
        return error_found

    def is_dual_swath(self, POSIX=None):
        """
        Returns True or False depending on the flag set for the Mode in the
        runtime parameters record.  The information from the first runtime
        record is returned unless a POSIX time is provided.
        """
        if POSIX is None:
            runtime = self.getrecord(82, 0)
        else:
            times = self.map.packdir['82'][:, 1]
            idx = np.nonzero(times < POSIX)[0]
            # should probably be checking to make sure the length of idx > 0...
            runtime = self.getrecord(82, idx[-1])
        if (runtime.header['Mode'] & 192) == 0:
            return False
        else:
            return True

    def get_stats(self, display=True):
        """
        Get the basic statistics for the line including:
        Line name
        EM model
        Mode flags
        Mode2 flags
        Beam Spacing
        Yaw and Pitch Stabilzation flags
        Max angular coverage setting for port / starboard
        Detection mode which is found in FilterID2
        Operator Station Status
        ProcessingUnitStatus
        BSP Status
        Sonar Head or Transceiver Status
        Speed mean and standard deviation
        Heading mean and standard deviation
        Roll standard deviation
        Pitch standard deviation
        Heave standard deviation
        Start and end times
        Latitude minimum and maximum
        Longitude minimum and maximum
        Center beam depth mean and standard deviation
        Mode Change
        Cast applied at beginning of file
        Number of new casts applied in file
        Number of Pings
        """
        lenfname = len(self.infilename) - 4
        fmt_lenfname = 'S' + str(lenfname)
        stat_dtype = np.dtype([
            ('Filename', fmt_lenfname),
            ('EMModel', '<u2'),
            ('Mode', 'S8'),
            ('Mode2', 'S8'),
            ('BeamSpacing', 'S8'),
            ('YawAndPitchStabilization', 'S8'),
            ('AngularLimits', '<u2', 2),
            ('FilterID2', 'S8'),
            ('OperatorStationStatus', 'S4'),
            ('ProcessingUnitStatus', 'S4'),
            ('BSPStatus', 'S4'),
            ('SonarHeadOrTransceiverStatus', 'S4'),
            ('Speed', 'f', 2),
            ('Heading', 'f', 2),
            ('Roll', 'f'),
            ('Pitch', 'f'),
            ('Heave', 'f'),
            ('Times', 'd', 2),
            ('Latitude', 'f', 2),
            ('Longitude', 'f', 2),
            ('Depth', 'f', 2),
            ('ModeChange', 'b'),
            ('CastTime', 'S16'),
            ('NewCastNumber', 'B'),
            ('NumberOfPings', 'I')])
        info = np.zeros(1, dtype=stat_dtype)[0]
        info['Filename'] = self.infilename[:lenfname]
        s = self.getrecord(85, 0)
        info['EMModel'] = self.packet.header['Model']
        t = dtm.datetime.utcfromtimestamp(s.POSIXtime)
        info['CastTime'] = t.strftime('%Y-%m-%d %H:%M')
        self._build_sscast_array()
        numcasts = len(np.nonzero(s.POSIXtime != self._sscast_array['Time'])[0])
        info['NewCastNumber'] = numcasts
        r = self._runtime_array['RuntimePacket']
        info['Mode'] = np.binary_repr(r['Mode'][0], 8)
        info['Mode2'] = np.binary_repr(r['ReceiverFixedGain'][0], 8)
        info['BeamSpacing'] = np.binary_repr(r['BeamSpacing'][0], 8)
        info['YawAndPitchStabilization'] = np.binary_repr(r['YawAndPitchStabilization'][0], 8)
        info['AngularLimits'] = np.array([r['MaxPortCoverage'][0], r['MaxStarboardCoverage'][0]], dtype='u2')
        info['FilterID2'] = np.binary_repr(r['HiLoFrequencyAbsorptionCoeffRatio'][0], 8)
        if np.all(r['OperatorStationStatus']):
            info['OperatorStationStatus'] = 'Fail'
        else:
            info['OperatorStationStatus'] = 'Good'
        if np.all(r['ProcessingUnitStatus']):
            info['ProcessingUnitStatus'] = 'Fail'
        else:
            info['ProcessingUnitStatus'] = 'Good'
        if np.all(r['BSPStatus']):
            info['BSPStatus'] = 'Fail'
        else:
            info['BSPStatus'] = 'Good'
        if np.all(r['SonarHeadOrTransceiverStatus']):
            info['SonarHeadOrTransceiverStatus'] = 'Fail'
        else:
            info['SonarHeadOrTransceiverStatus'] = 'Good'
        mode_change = False
        if np.any(r['Mode'] != r['Mode'][0]):
            mode_change = True
        elif np.any(r['ReceiverFixedGain'] != r['ReceiverFixedGain'][0]):
            mode_change = True
        info['ModeChange'] = int(mode_change)
        self._build_speed_array()
        info['Speed'] = np.array([np.nanmean(self.speedarray[:, 1]), np.nanstd(self.speedarray[:, 1])])
        att = self.navarray['65']
        info['Heading'] = np.array([att[:, -1].mean(), att[:, -1].std()])
        info['Roll'] = att[:, 1].std()
        info['Pitch'] = att[:, 2].std()
        info['Heave'] = att[:, 3].std()
        info['Times'] = np.array([att[0, 0], att[-1, 0]])
        nav = self.navarray['80']
        info['Latitude'] = np.array([nav[:, 2].min(), nav[:, 2].max()])
        info['Longitude'] = np.array([nav[:, 1].min(), nav[:, 1].max()])
        try:
            depths = self.build_bathymetry()
            numpings, numbeams = depths[:, :, 0].shape
            centerbeam = int(numbeams / 2)
            centerdata = depths[:, centerbeam, 0]
            info['Depth'] = np.array([centerdata.mean(), centerdata.std()])
            info['NumberOfPings'] = self.map.getnum(88)
        except KeyError:
            info['Depth'] = np.array([np.nan, np.nan])
            if '107' in self.map.packdir:
                info['NumberOfPings'] = self.map.numwc
        if display:
            for n, name in enumerate(info.dtype.names):
                print(name + ' : ' + str(info[n]))
        return info

    def plot_wobbles(self, which_swath=0, heavefile=None, use_height=False, make_plot=1):
        """
        Based on the paper
        JE Hughes Clarke, Dynamic Motion Residuals in Swath Sonar Data: Ironing
        out the Creases, International Hydrographic Review, March 2003.
        Assuming a flat seafloor for simplicity.  A rough seafloor (based on
        std of across track depth?) should be added later. The high pass depth
        filter is applied along track by beam.
        """
        # going to be sloppy here... assuming all data types exist and in the same # of pings
        # figure out if in dual swath and the number of pings
        print('Beginning data extraction,', end=' ')
        if self.is_dual_swath():
            step = 2
            numrec = len(self.map.packdir['88']) / 2
        else:
            step = 1
            numrec = len(self.map.packdir['88'])

        # get installation parameters
        ip = self.getrecord(73, 0)
        wline = float(ip.settings['WLZ'])
        # get information on data sizes
        p78 = self.getrecord(78, 0)
        numtx = p78.header['Ntx']
        numrx = p78.header['Nrx']
        # allocate space
        depth88 = np.zeros((numrec, numrx))
        across88 = np.zeros((numrec, numrx))
        txnum = np.zeros((numrec, numrx), dtype=np.int)
        txheave = np.zeros(numrec)
        txpitch = np.zeros((numrec, numtx))
        txpitchvel = np.zeros((numrec, numtx))
        txtime = np.zeros((numrec, numtx))
        rectime = np.zeros(numrec)
        rxtime = np.zeros((numrec, numrx))
        rxroll = np.zeros((numrec, numrx))
        rxrollvel = np.zeros((numrec, numrx))

        # get the 78 record for rx times and sector numbers
        k = which_swath
        for n in range(numrec):
            p78 = self.getrecord(78, k)
            rectime[n] = self.packet.gettime()
            txnum[n, :] = p78.rx['TransmitSectorID']
            # just getting the rx time/roll for the middle of each swath for speed!
            #        idx = np.zeros(numtx, dtype = np.int)
            #        for m in range(numtx):
            #            ids = np.nonzero(txnum[n,:] == m)[0]
            #            idm = ids.mean() # this is roughly the middle of each swath
            #            idx[m] = idm.astype(np.int)
            rxtimes = p78.get_rx_time()
            rxtime[n, :] = rxtimes  # [idx]
            # getting the txtimes and pitch
            txdelay = p78.tx['Delay'].astype(np.float64)
            txtime[n, :] = p78.pingtime + txdelay
            k += step

        print('getting motion,', end=' ')
        # get all the attitude information
        att = self.navarray['65']
        attvel = self.navarray['110']  # this comes from the POS102 datagram inside the attitude
        # gettting this information for all times but by sector
        for n in range(numtx):
            txpitch[:, n] = np.interp(txtime[:, n], att[:, 0], att[:, 1], left=np.nan, right=np.nan)
            txpitchvel[:, n] = np.interp(txtime[:, n], attvel[:, 0], attvel[:, 7], left=np.nan, right=np.nan)
        for n in range(numrx):
            rxroll[:, n] = np.interp(rxtime[:, n], att[:, 0], att[:, 1], left=np.nan, right=np.nan)
            rxrollvel[:, n] = np.interp(rxtime[:, n], attvel[:, 0], attvel[:, 6], left=np.nan, right=np.nan)
        recheavevel = np.interp(rectime, attvel[:, 0], attvel[:, -1], left=np.nan, right=np.nan)

        # get the height data if available
        if '104' in self.navarray:
            rawheight = self.navarray['104']

        # get the depth, along track and heave data
        k = which_swath
        for n in range(numrec):
            p88 = self.getrecord(88, k)
            if use_height and '104' in self.navarray:
                # using the txtime from the first sector for heave!!!
                x_arm = float(ip.settings['S1X'])
                y_arm = float(ip.settings['S1Y'])
                txroll = np.interp(txtime[n, 0], att[:, 0], att[:, 1], left=np.nan, right=np.nan)
                induced_heave = x_arm * sin(np.deg2rad(txpitch[n, 0])) + y_arm * sin(np.deg2rad(txroll))
                height = np.interp(txtime[n, 0], rawheight[:, 0], rawheight[:, 1], left=np.nan, right=np.nan)
                depth88[n, :] = p88.data['Depth'] - height - induced_heave
            else:
                txheave[n] = p88.header['TransmitDepth'] + wline
                depth88[n, :] = p88.data['Depth'] + txheave[n]

            across88[n, :] = p88.data['AcrossTrack']
            k += step

        # get the true heave from a numpy array file with columns [time,realtime,delayed]
        dh = np.zeros(len(txheave))
        if heavefile is not None and not use_height:
            posheave = np.load(heavefile)
            heavediff = posheave[:, 1] - posheave[:, 2]
            dh = np.interp(rectime, posheave[:, 0], heavediff, left=np.nan, right=np.nan)
            if np.any(np.isnan(dh)):
                print(
                    '\n***Warning: Delayed Heave is not applied since it is not in correct time range for all file.***')
        txheave += dh
        dh.shape = (-1, 1)

        # get the water column data if available
        if '107' in self.map.packdir:
            # assuming the same number of XYZ88 and water column records...
            have_wc = True
            wcr = self.getwatercolumn(n)
            wc = np.zeros((numrec, wcr.header['Total#Beams']))
            for n in range(numrec):
                wcr = self.getwatercolumn(n)
                maxrange = wcr.rx['DetectedRange'].min() - 2
                ampdata = wcr.ampdata[:maxrange, :].astype(np.float64)
                ampdata = 10 ** (ampdata / 10.)
                ampmean = ampdata.mean(axis=0)
                wc[n, :] = 10 * np.log10(ampmean)
        else:
            have_wc = False

        # apply true heave before filtering
        depth88 = depth88 - dh

        # Begin bathymetry processing
        print('filtering bathymetry,', end=' ')
        # Establish the bathymetry filter using the motion time series
        t = att[:, 0]
        dt = (t[1:] - t[:-1]).mean()
        freq = fft.fftfreq(len(t), dt)
        roll = att[:, 1]
        pitch = att[:, 2]
        roll_fft = fft.fft(roll)
        pitch_fft = fft.fft(pitch)
        max_freq_idx = np.array([roll_fft.argmax(), pitch_fft.argmax()]).max()
        max_freq = np.abs(freq[max_freq_idx])
        # setting the filter length to four times the max response per JHC p.22
        filtertime = 4 / max_freq
        # plot the filter response with the roll / pitch
        #        win = np.hanning(int(filtertime/dt))
        #        win /= win.sum()
        #        win_freq = fft.fftfreq(len(win), dt)
        #        win_fft = fft.fft(win)
        #        roll_lp = np.convolve(roll, win, mode = 'same')
        #        roll_hp = roll - roll_lp
        #        roll_hp_fft = fft.fft(roll_hp)
        #        pitch_lp = np.convolve(pitch, win, mode = 'same')
        #        pitch_hp = pitch - pitch_lp
        #        pitch_hp_fft = fft.fft(pitch_hp)
        #        filt_fig = plt.figure()
        #        roll_ax = filt_fig.add_subplot(311)
        #        roll_ax.plot(freq, np.log10(np.abs(roll_fft)))
        #        roll_ax.plot(freq, np.log10(np.abs(roll_hp_fft)))
        #        roll_ax.legend(('Raw','Filtered'))
        #        roll_ax.set_title('Roll')
        #        win_ax = filt_fig.add_subplot(312, sharex = roll_ax)
        #        win_ax.plot(win_freq, np.log10(np.abs(win_fft)))
        #        pitch_ax = filt_fig.add_subplot(313, sharex = roll_ax, sharey = roll_ax)
        #        pitch_ax.plot(freq, np.log10(np.abs(pitch_fft)))
        #        pitch_ax.plot(freq, np.log10(np.abs(pitch_hp_fft)))
        #        pitch_ax.set_xlabel('Frequency (Hz)')
        #        pitch_ax.set_title('Pitch')
        #        filt_fig.suptitle('Filter length set to ' + str(filtertime.round()) + ' seconds.')

        # Get the average ping period for setting the filter length
        ping_period = (txtime[1:, 0] - txtime[:-1, 0]).mean()
        # Set ping filter length based motion time series
        filter_len = int(filtertime / ping_period)
        print('Filter length set to ' + str(filter_len) + ' seconds.', end=' ')
        # data at the edges that is not filtered properly and not to be included in analysis
        rem = int(filter_len / 2)
        # Check to see if ping rate is high enough to support this analysis
        motion_to_ping_ratio = 1 / (max_freq * ping_period)
        print('Motion period to ping period ratio is ' + str(motion_to_ping_ratio.round()))
        # this threshold is suggested by the JHC paper (p.6)
        if motion_to_ping_ratio < 10:
            print('***Warning: the ping rate may not capture the motion time series properly for this analysis.***')
        # build the window and filter the data
        win = np.hanning(filter_len)
        win /= win.sum()
        low_pass = np.zeros(depth88.shape)
        for n in range(numrx):
            low_pass[:, n] = np.convolve(depth88[:, n], win, mode='same')
        if filter_len > 1:
            high_pass = depth88 - low_pass
        else:
            high_pass = depth88
        # adjust the attitude range
        if rem == 0:
            rem = 1
        txheave = txheave[rem:-rem].astype(np.dtype([('Heave (m)', np.float)]))
        txpitch = txpitch[rem:-rem, :].astype(np.dtype([('Pitch (deg)', np.float)]))
        txpitchvel = txpitchvel[rem:-rem, :].astype(np.dtype([('Pitch Rate (deg/s)', np.float)]))
        txtime = txtime[rem:-rem].astype(np.dtype([('TX Time (s)', np.float)]))
        rxtime = rxtime[rem:-rem, :].astype(np.dtype([('RX Time (s)', np.float)]))
        rxroll = rxroll[rem:-rem, :].astype(np.dtype([('Roll (deg)', np.float)]))
        rxrollvel = rxrollvel[rem:-rem, :].astype(np.dtype([('Roll Rate (deg/s)', np.float)]))
        recheavevel = recheavevel[rem:-rem].astype(np.dtype([('Heave Rate (m/s)', np.float)]))
        # identify which beam is in which sector.  Remove the ones that switch sector
        beamtx = txnum.mean(axis=0)

        # regress the "good" data range
        print('Regressing swaths and beams,', end=' ')
        good_data_range = numrec - 2 * rem
        # first over the swath
        mainswath_slope = np.zeros((good_data_range), dtype=np.dtype([('Swath Slope (deg)', np.float)]))
        swath_mean = np.zeros((good_data_range), dtype=np.dtype([('Swath Mean (deg)', np.float)]))
        sector_slope = np.zeros((good_data_range, numtx), dtype=np.dtype([('Sector Slope (deg)', np.float)]))
        sector_mean = np.zeros((good_data_range, numtx), dtype=np.dtype([('Sector Mean (deg)', np.float)]))
        for n in range(good_data_range):
            if not np.all(np.isnan(high_pass[rem + n, :])):
                result = np.polyfit(across88[rem + n, :], high_pass[rem + n, :], 1)
                swath_mean[n] = result[1]
                mainswath_slope[n] = 180. * np.arctan(result[0]) / np.pi
                for m in range(numtx):
                    txid = np.nonzero(txnum[rem + n, :] == m)[0]
                    if len(txid) > 0:
                        result = np.polyfit(across88[rem + n, txid], high_pass[rem + n, txid], 1)
                        sector_mean[n, m] = result[1]
                        sector_slope[n, m] = 180. * np.arctan(result[0]) / np.pi
        # This section correlates a time delay by beam
        # The bias angle (flat seafloor, as in low passed, minus original) is computed and
        # regressed against the roll rate.
        along_mean = np.zeros(numrx, dtype=np.dtype([('Beam Angle Bias to Roll Rate Mean', np.float)]))
        along_slope = np.zeros(numrx, dtype=np.dtype([('Beam Angle Bias to Roll Rate Slope', np.float)]))
        along_residuals = np.zeros(numrx, dtype=np.dtype([('Beam Angle Bias to Roll Rate Residual', np.float)]))
        # find the angles
        orig_angle = 180. / np.pi * np.arctan2(depth88, across88)
        # see notes in green book from 20160208
        depths = low_pass.mean(axis=1)
        depths = np.tile(depths, [numrx, 1])
        range_at_angle = np.sqrt(across88 ** 2 + depths.T ** 2)
        bias_angle = orig_angle - 180. / np.pi * np.arccos(low_pass / (range_at_angle - high_pass / np.cos(orig_angle)))
        bias_angle = bias_angle[rem:-rem, :]
        # for each beam, fit a line to corralate the angle bias to the roll rate
        for n in range(numrx):
            if np.any(np.isnan(bias_angle)):
                idx = np.nonzero(~np.isnan(bias_angle[:, n]))[0]
            else:
                idx = np.arange(good_data_range)
            xtemp = rxrollvel[idx, n].astype(np.float)
            ytemp = bias_angle[idx, n]
            # the fit
            result = np.polyfit(xtemp, ytemp, 1)
            along_mean[n] = result[1]
            along_slope[n] = result[0]
            # find the residuals
            linefunc = np.poly1d(result)
            bias_estimate = linefunc(xtemp)
            along_residuals[n] = np.std(bias_estimate - ytemp)
        bias_angle = bias_angle.astype(np.dtype([('Beam Angle Bias (Deg)', np.float)]))

        # plot the bathymetry
        print('plotting,', end=' ')
        fig = plt.figure()
        fig.suptitle('Hanning filter Length of ' + str(filter_len))
        ax1 = fig.add_subplot(141)
        im1 = ax1.imshow(depth88[rem:-rem, :], aspect='auto', interpolation='none')
        ax1.set_title('XYZ88 Depth')
        plt.colorbar(im1)
        ax2 = fig.add_subplot(142, sharex=ax1, sharey=ax1)
        im2 = ax2.imshow(low_pass[rem:-rem, :], aspect='auto', interpolation='none')
        ax2.set_title('Low Pass Depth')
        plt.colorbar(im2)
        ax3 = fig.add_subplot(122, sharex=ax1, sharey=ax1)
        im3 = ax3.imshow(high_pass[rem:-rem, :], aspect='auto', interpolation='none')
        hp_mean = np.nanmean(high_pass[rem:-rem, :])
        hp_std = np.nanstd(high_pass[rem:-rem, :])
        im3.set_clim((hp_mean - hp_std, hp_mean + hp_std))
        im3.set_cmap('gray')
        ax3.set_title('High Pass Depth')
        plt.colorbar(im3)
        ax4 = ax3.twinx()
        ax4.grid(color='r', linestyle='-', linewidth='2')
        ax4.patch.set_alpha(0)
        ax4.set_zorder(1)

        # plot scatter plots
        if make_plot & 1:
            self._plot_wobble_scatter(rxrollvel[:, numrx / 2], mainswath_slope, title='Roll Rate vs Swath Slope')
        # self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,0], title = 'Roll Rate vs Sector 0 Slope')
        # self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,1], title = 'Roll Rate vs Sector 1 Slope')
        # self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,2], title = 'Roll Rate vs Sector 2 Slope')
        #        self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,7], title = 'Roll Rate vs Sector 7 Slope')
        # self._plot_wobble_scatter(recheavevel, swath_mean, title = 'Heave Rate vs Swath Mean')
        # self._plot_wobble_scatter(txheave, swath_mean, title = 'Heave vs Swath Mean')
        #        self._plot_wobble_scatter(txpitchvel[:,1], swath_mean, title = 'Pitch Rate vs Swath Mean')
        #        self._plot_wobble_scatter(txpitch, swath_mean, title = 'Pitch vs Swath Mean')

        # plot the along track fits
        beams = np.arange(numrx)
        temp = 180. / np.pi * np.arctan2(low_pass[rem:-rem, :], across88[rem:-rem, :]) - 90
        pointing_angles = temp.mean(axis=0).astype(np.dtype([('Pointing Angle (Deg)', np.float)]))
        beams = beams.astype(np.dtype([('Beam Number', np.float)]))
        across_mean_range = across88.mean(axis=0)
        across_mean_range = across_mean_range.astype(np.dtype([('Across Track Range (m)', np.float)]))
        # self._plot_wobble_scatter(pointing_angles, along_slope, title = 'Beam Angular Bias to Roll Rate Slope Fit vs Across Track Distance', txid = beamtx)
        # self._plot_wobble_scatter(beams, along_mean, title = 'Interept of fit to Roll Rate vs Beam Number')

        # plot a single beam's roll rate vs bias to demonstrate where the regressed plots come from.
        # beam = 20
        # self._plot_wobble_scatter(rxrollvel[:,beam], bias_angle[:,beam], title = 'Regressing beam ' + str(beam) + ' Roll Velocity vs Angular Bias')
        print('done!')
        # np.savez('angles',across = across88[rem:-rem,:],lowpass = low_pass[rem:-rem,:])

    def _plot_wobble_scatter(self, data1, data2, title='', fit=True, mean=False, txid=None, residual=None):
        """
        Takes in two one dimensional record numpy arrays and plots them as
        a scatter plot.  A fit line can also be added.
        """
        plt.figure()
        name1 = data1.dtype.names[0]
        name2 = data2.dtype.names[0]
        if residual is None:
            plt.plot(data1, data2, 'b.')
        else:
            plt.errorbar(data1[name1], data2[name2], yerr=residual.astype('float'))
        plt.xlabel(name1)
        plt.ylabel(name2)
        plt.grid()
        # working around nan values for the fit
        idx = np.nonzero(~np.isnan(data2[name2]))[0]
        if fit:
            result, covarmat = np.polyfit(data1[name1][idx], data2[name2][idx], 1, cov=True)
            linefunc = np.poly1d(result)
            xmin = data1[name1].min()
            xmax = data1[name1].max()
            xdata = np.array([xmin, xmax])
            ydata = linefunc(xdata)
            plt.plot(xdata, ydata, 'g-')
            s = 'Slope: {:0.2e} +/- {:0.2e}'.format(result[0], np.sqrt(covarmat[0, 0]))
            title = title + '\n' + s
            if txid is not None:
                # dealing with the beams that switch sectors
                idx = np.nonzero(txid % 1 == 0)[0]
                txvals = set(txid[idx])
                for n in txvals:
                    idx = np.nonzero(txid == n)
                    result = np.polyfit(data1[name1][idx], data2[name2][idx], 1)
                    linefunc = np.poly1d(result)
                    xmin = data1[name1][idx].min()
                    xmax = data1[name1][idx].max()
                    xdata = np.array([xmin, xmax])
                    ydata = linefunc(xdata)
                    plt.plot(xdata, ydata, 'r-')
                    s = '%0.2e' % result[0]
                    title = title + ', txid ' + str(int(n)) + ' slope: ' + s
        if mean:
            result = np.polyfit(data1[name1], data2[name2], 1)
            linefunc = np.poly1d(result)
            xmin = data1[name1].min()
            xmax = data1[name1].max()
            ymean = data2[name2].mean()
            plt.hlines(ymean, xmin, xmax, colors='g')
            s = 'Mean: %0.2e' % ymean
            title = title + '\n' + s
            if txid is not None:
                # dealing with the beams that switch sectors
                idx = np.nonzero(txid % 1 == 0)[0]
                txvals = set(txid[idx])
                for n in txvals:
                    idx = np.nonzero(txid == n)
                    ymean = data2[name2][idx].mean()
                    xmin = data1[name1][idx].min()
                    xmax = data1[name1][idx].max()
                    plt.hlines(ymean, xmin, xmax, colors='r')
                    s = '%0.2e' % ymean
                    title = title + ', txid ' + str(int(n)) + ' M: ' + s
        plt.title(title)
        plt.draw()

    def build_bathymetry(self, apply_tx_depth=True):
        """
        Build and return a numpings by numbeams by 3 array of the xyz88
        depths, acrosstrack and alongtrack offsets.  The transmit depth
        is added to the bathymetry.
        """
        num88 = self.map.getnum(88)
        d = self.getrecord(88, 0)
        numbeams = d.header['NumBeams']
        vals = np.zeros((num88, numbeams, 3))
        for n in np.arange(num88):
            d = self.getrecord(88, n)
            if apply_tx_depth:
                vals[n, :, 0] = d.data['Depth'] + d.header['TransmitDepth']
            else:
                vals[n, :, 0] = d.data['Depth']
            vals[n, :, 1] = d.data['AcrossTrack']
            vals[n, :, 2] = d.data['AlongTrack']
        return vals

    def position_XYZ(self, pingnumber, vertical_reference='ellipsoid',
                     ellipsoid='WGS84'):
        """
        Gets the provided ping number (relative to pings in the file, with the
        first ping being zero) XYZ data, and applies the position, heading and
        vertical height.  The type of vertical height to be applied is set with
        the 'vertical_reference' kwarg, with valid optioins being 'transducer',
        'waterline', and 'ellipsoid', where the 'ellipsoid' is the default. The
        ellipsoid used for the vessel positioning system should be supplied in
        a PROJ4 agreeable string.

        Only valid detections are returned. The returned numpy data type array
        has entries for each valid sounding and contains fields for 'Beam'
        number, 'Latitude', 'Longitude', and 'Depth'.
        """
        dtype = np.dtype([('Beam', 'H'),
                          ('Longitude', 'd'),
                          ('Latitude', 'd'),
                          ('Depth', 'f')])
        # resolve the vertical
        ip = self.installation_parameters
        p = self.getrecord(88, pingnumber)
        t = self.packet.gettime()
        if vertical_reference == 'ellipsoid':
            m = self.getnav(t, postype='GGK')[0]
            v = m[7]
        elif vertical_reference == 'waterline':
            v = p.header['TransmitDepth']
            m = self.getnav(t)[0]
        elif vertical_reference == 'transducer':
            m = self.getnav(t)[0]
            v = 0
        # acount for pitch induced heave, using the time stamp of the record...
        if np.any(np.isnan(m)):
            out = np.zeros(1, dtype=dtype)
            out['Beam'] = -1
            out['Longitude'] = np.nan
            out['Latitude'] = np.nan
            out['Depth'] = np.nan
        else:
            x_arm = float(ip.settings['S1X'])
            y_arm = float(ip.settings['S1Y'])
            induced_heave = (x_arm * sin(np.deg2rad(m[4])) +
                             y_arm * sin(np.deg2rad(m[3])))
            beams = np.nonzero(p.data['Detection'] < 129)[0]
            depths = p.data['Depth'][beams] - v - induced_heave
            # do the rotation of X and Y by the heading, and add the vector to the position
            horz_beam_ang = np.arctan2(p.data['AcrossTrack'][beams],
                                       p.data['AlongTrack'][beams])
            r = np.sqrt(p.data['AcrossTrack'][beams] ** 2 +
                        p.data['AlongTrack'][beams] ** 2)
            az = (180 / np.pi * horz_beam_ang + m[6]) % 360
            lon = np.zeros(len(r)) + m[1]
            lat = np.zeros(len(r)) + m[2]
            # remove nans before they get to pyproj
            if np.any(np.isnan(r)) or np.any(np.isnan(az)):
                idx = np.nonzero(~np.isnan(r))[0]
                r = r[idx]
                az = az[idx]
                lat = lat[idx]
                lon = lon[idx]
                depths = depths[idx]
                beams = beams[idx]
                idx = np.nonzero(~np.isnan(az))[0]
                r = r[idx]
                az = az[idx]
                lat = lat[idx]
                lon = lon[idx]
                depths = depths[idx]
                beams = beams[idx]
            g = pyproj.Geod(ellps='WGS84')
            pos = g.fwd(lon, lat, az, r)
            out = np.zeros(len(beams), dtype=dtype)
            out['Beam'] = beams
            out['Longitude'] = pos[0]
            out['Latitude'] = pos[1]
            out['Depth'] = depths
        return out

    def km_backscatter_normalization(self, pingnumber):
        """
        This method satisfies two functions.  Both the beam footprint area
        adjustment and the lambertian corrections are provided by beam for the
        ping time provided.  These adjustment estimates are based on
        Erik Hammerstad:
        "Backscattering and Seabed Image Reflectivity", January 7th 2000.
        and also to a Kongsberg white paper
        "Backscatter Corrections" (no date).

        This method takes the ping number in the file and returns two arrays
        containing the beam footprint and the lambertian adjustment for each
        beam.

        Also, the following is from Mark Amend via email 20150203:
        "
        Following-up here. I heard from Kjell Nilsen regarding your questions.
        Here was his response, hope it helps clarify some things for your
        analysis:

        The footprint area (A0 on page 5) is calculated using the sound speed
        at the transducer depth. This is the same speed as is given in the
        header of the depth and the raw range datagrams. This is a small
        simplification, but makes it easier to recalculate the applied TVG.
        The TX beam alongship opening angle is, like Torgrim told, not
        corrected for the individual frequencies of the different sectors.
        This will probably be implemented in a later release,

        The TVG applied to the water column data is much simpler, its strictly
        an Xlog R + 2AR + C function, as described in the datagram manual.
        The absorption coefficient (A) used is the average value calculated for
        each TX sector, given in the raw range and angle 78 datagram.
        The X was earlier fixed to 30, and C to 0. But in the last releases the
        X and the C are now operator set paramters. X and C are documented in
        the datagram. Default X is still 30. Default C is set to 20, to change
        the backscatter data 8 bit dynamic range from +/- 64 dB to -84 to +44
        dB. This is done to be able to investigate very weak echoes in the
        water column.
        "

        Thanks to JB and his willingness to share UNB tribal knowledge!
        """

        subpacks = self.getping(pingnumber=pingnumber,
                                recordlist=['78', '88', '89'], extra=False)
        if subpacks is not None:
            # pull out the supporting data
            ping89 = subpacks['89']
            bso = ping89.header['NormalBackscatter']
            bsn = ping89.header['ObliqueBackscatter']
            rtn = ping89.header['RangeToNormal']
            ping78 = subpacks['78']
            sr = ping78.header['SampleRate']
            r = ping78.rx['TravelTime']
            txid = ping78.rx['TransmitSectorID']
            pulse = ping78.tx['SignalLength']
            txnum = ping78.tx['TransmitSector#'].sort()
            c = ping78.header['SoundSpeed']
            depths = subpacks['88'].data['Depth']

            # get the runtime parameters that are needed
            txwx, rxwx = self.getruntime(ping78.pingtime, ['TransmitBeamWidth'
                , 'ReceiveBeamWidth'])
            txwx, rxwx = np.deg2rad([txwx, rxwx])

            # compute the lambertian avg
            rs = r * sr  # two way range sample number
            rco = rtn / np.cos(ping89.header['TVGCrossover'] * np.pi / 180)
            dbs = bso - bsn
            # calculate the BSo value for all ranges
            lamb = 20 * np.log10(rtn / rs)
            # add the BSn adjustment for the ranges in the BSn regime
            if dbs != 0:
                bsn_idx = np.nonzero(rs < rco)[0]
                delta_samp = rs[bsn_idx] - rtn
                # deal with samples that are just under the range to normal
                ds_idx = np.nonzero(delta_samp < 0)[0]
                if len(ds_idx) > 0:
                    delta_samp[ds_idx] = 0
                lamb[bsn_idx] = lamb[bsn_idx] + dbs * (1 - np.sqrt((delta_samp) / (rco - rtn)))

            # compute the beam foot print
            pulse = pulse[txnum].squeeze()
            pulselen = pulse[txid]
            rn2 = (rtn / sr) ** 2  # range to normal squared as twtt
            footprint = rxwx * txwx * (r * c / 2) ** 2  # An from document
            rn2_div_r2 = rn2 / r ** 2
            div_idx = np.nonzero(rn2_div_r2 > 1)[0]
            if len(div_idx) > 0:
                rn2_div_r2[div_idx] = 1 - 2 ** (-50)  # making this number just less than one
            footo = c ** 2 * pulselen * txwx * r / 2 / np.sqrt(1 - rn2_div_r2)  # A0 from document
            # finding the crossover from An to Ao is documented differently
            A0_idx = np.nonzero(footprint > footo)[0]
            footprint[A0_idx] = footo[A0_idx]
            footprint = 10 * np.log10(footprint)
            return footprint, lamb
        else:
            print("ping number is not valid.")
            return None, None

    def buildBS89center(self, useinvalid=False, filter_3std=True, footprint=True, lambertian=True):
        """
        Build an array of all the center snippets from all 89 datagrams.  Any
        values that are less than -200 are set to nan.
        Need to confirm if the direction needs to be flipped.
        """
        if '89' in self.map.packdir:
            num89 = len(self.map.packdir['89'])
            # assuming that if 89 exists so does 88...
            ping88 = self.getrecord(88, 0)
            numbeams = ping88.header['NumBeams']
            bs89 = np.zeros((num89, numbeams)) + np.nan
            for n in range(num89):
                ping89 = self.getrecord(89, n)
                samples = ping89.center()
                numvalid = ping89.header['NumberValidBeams']
                if not useinvalid:
                    if numvalid != numbeams:
                        detect = ping89.beaminfo['DetectionInfo']
                        idx = np.nonzero(detect > 127)[0]
                        samples[idx] = np.nan
                        temp = np.zeros(numbeams)
                        temp[:numvalid] = samples
                        samples = temp
                if not footprint or not lambertian:
                    ft, lb = self.km_backscatter_normalization(n)
                    if not footprint:
                        samples += ft
                    if not lambertian:
                        samples += lb
                bs89[n, :] = samples
            if filter_3std:
                bsm = bs89.mean()
                bsd = bs89.std()
                idx = np.nonzero((bs89 < bsm - bsd * 3) | (bs89 > bsm + bsd * 3))
                bs89[idx[0], idx[1]] = np.nan
                print("Data was filtered to be between " + str(bsm - bsd * 3) + " and " + str(bsm + bsd * 3) + "dB.")
            return bs89
        else:
            print("No 89 datagram found")
            return None

    def buildBS78(self, useinvalid=False, footprint=True):
        """
        Builds an array of all the Reflectivity from the 78 datagrams and
        returns it.
        """

        if '78' in self.map.packdir:
            num78 = len(self.map.packdir['78'])
            ping78 = self.getrecord(78, 0)
            numbeams = ping78.header['Nrx']
            bs78 = np.zeros((num78, numbeams))
            for n in range(num78):
                ping78 = self.getrecord(78, n)
                bs78[n, :] = ping78.rx['Reflectivity']
                if not useinvalid:
                    detect = ping78.rx['DetectionInfo']
                    idx = np.nonzero(detect > 127)[0]
                    bs78[n, idx] = np.nan
            return bs78
        else:
            print("No 78 datagram found.")

    def plot_bs(self, bs, bs_range=3):
        """
        Plots the provided backscatter imagry.
        """
        bs_std = np.nanstd(bs)
        bs_mean = np.nanmean(bs)
        bs_min = bs_mean - bs_range * bs_std
        bs_max = bs_mean + bs_range * bs_std
        plt.figure()
        plt.imshow(bs, aspect='auto', cmap='gray', clim=(bs_min, bs_max))
        cbar = plt.colorbar()
        cbar.set_label('dB re $1\mu Pa$ at 1 meter')
        ax = plt.gca()
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_ylabel('Along track')
        ax.set_xlabel('Across track')
        plt.draw()

    def build_BSCorr_info(self, which_swath=0, plot_bs=False, lambertian=True):
        """
        This method gets all the backscatter from the file, bins the data in
        'step' sized bins by sector, and then gets a linear average for each
        bin.  The returned values are the averaged bin values, the counts per
        bin, and the center angles for each bin.
        """
        # find if the system is reverse mounted so roll is applied correctly
        ping73 = self.getrecord(73, 0)
        S2R = float(ping73.settings['S2R'])
        # S2H = float(ping73.settings['S2H'])
        # S1H = float(ping73.settings['S1H'])
        # yaw = (S2H + S1H) % 180
        # yaw = S1H % 180
        # if abs(yaw) > 90:
        # the system is reverse mounted
        #    S2R *= -1
        print("Getting backscatter...")
        bs = self.buildBS89center(lambertian=lambertian)
        if plot_bs:
            self.plot_bs(bs)
        # determine dual swath
        if self.is_dual_swath():
            step = 2
            bs = bs[which_swath::2, :]
        else:
            step = 1
        txid = np.zeros(bs.shape)
        beam_angle = np.zeros(bs.shape)  # relative to vertical
        num78, temp = bs.shape
        ping78 = self.getrecord(78, 0)
        sectors = ping78.tx['TransmitSector#']
        print("Getting sector and angle information:          ", end=' ')
        k = which_swath
        progress = 0
        for n in range(num78):
            ping78 = self.getrecord(78, k)
            rxtimes = ping78.get_rx_time()
            roll = self.getnav(rxtimes)[:, 3]  # in degrees
            txid[n, :] = ping78.rx['TransmitSectorID']
            beam_angle[n, :] = ping78.rx['BeamPointingAngle'] + roll + S2R
            k += step
            temp = np.round((n * 100.) / num78)
            if temp > progress:
                progress = temp
                print('\b\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' % {'percent': progress}, end=' ')
        print('\n')
        print("Sorting backscatter by angle", end=' ')
        angle_width = 1
        angles = np.arange(-80.5, 80.5, angle_width)
        bp = np.zeros((len(angles), len(sectors)))
        count = np.zeros(bp.shape)
        for m, s in enumerate(sectors):
            sector_idx = np.nonzero(txid == s)
            b = bs[sector_idx[0], sector_idx[1]].astype(np.float64)
            sector_angles = beam_angle[sector_idx[0], sector_idx[1]]
            for n, a in enumerate(angles):
                a_idx = np.nonzero((a < sector_angles) & (a + angle_width > sector_angles))[0]
                if len(a_idx) > 0:
                    vals = 10 ** (b[a_idx] / 10)
                    bp[n, m] = 10 * np.log10(np.nanmean(vals))
                    count[n, m] = len(a_idx)
                else:
                    bp[n, m] = np.nan
                # print '.',
            print('\nFinished Sector ' + str(s), end=' ')
        print("\nDone!")
        return bp, count, angles + angle_width / 2.

    def plot_all_BIST_noise(self, xticklabels=[]):
        """
        Finds all noise BIST records in the file and plots them.  If no
        xticklables are provided the speed is assumed to be increasing and the
        speed is taken from the file.
        - what is Kongsberg backscatter referenced to?
        - do we need to be more careful about mapping the speed label to the
        correct records?
        """
        # build a list of all noise tests and the time they were completed.
        num66 = self.map.getnum(66)
        noisetests = []
        spectests = []
        for n in range(num66):
            p66 = self.getrecord(66, n)
            if p66.testtype == 'ChannelNoise':
                t = self.packet.gettime()
                noisetests.append([n, t])
            elif p66.testtype == 'NoiseSpectrum':
                t = self.packet.gettime()
                spectests.append([n, t])
        numnoise = len(noisetests)
        numspec = len(spectests)
        num66 = self.map.getnum(66)
        if p66._model == 2040:
            # Get some information about the noise datagram.
            self.getrecord(66, noisetests[0][0])
            self.packet.subpack.parse()
            label = self.packet.subpack.label
            datashape = self.packet.subpack.data.shape
            # Go through all tests and extract the noise data
            allnoise = np.zeros((numnoise, datashape[0], datashape[1]))
            allnoise[:, :, :] = np.nan
            for n in range(numnoise):
                self.getrecord(66, noisetests[n][0])
                self.packet.subpack.parse()
                allnoise[n, :, :] = self.packet.subpack.data
            speed = self.getspeed(np.array(noisetests)[:, 1])
            speed = speed.astype(np.int)
            # Find the color range for the plots
            cmax = allnoise.max()
            cmin = allnoise.min()
            # set up the xticks
            if xticklabels == []:
                xticklabels = list(set(speed))
            spacing = len(speed) / len(xticklabels)
            xticks = list(range(spacing / 2, len(speed), spacing))
            # Plot the data
            fig, ax = plt.subplots(len(label), 1)
            for n, a in enumerate(ax):
                c = a.pcolormesh(allnoise[:, :, n].T)
                c.set_clim((cmin, cmax))
                a.set_ylabel('Channel (#)')
                a.set_ylim((0, allnoise.shape[1]))
                a.set_xlim((0, allnoise.shape[0]))
                a.set_title(label[n])
            self.packet.subpack.parse()
            label = self.packet.subpack.label
            datashape = self.packet.subpack.data.shape
            # Go through all tests and extract the noise data
            allnoise = np.zeros((numnoise, datashape[0], datashape[1]))
            allnoise[:, :, :] = np.nan
            for n in range(numnoise):
                self.getrecord(66, noisetests[n][0])
                self.packet.subpack.parse()
                allnoise[n, :, :] = self.packet.subpack.data
            speed = self.getspeed(np.array(noisetests)[:, 1])
            speed = speed.astype(np.int)
            # Find the color range for the plots
            cmax = allnoise.max()
            cmin = allnoise.min()
            # set up the xticks
            if xticklabels == []:
                xticklabels = list(set(speed))
            spacing = len(speed) / len(xticklabels)
            xticks = list(range(spacing / 2, len(speed), spacing))
            # Plot the data
            fig, ax = plt.subplots(len(label), 1)
            for n, a in enumerate(ax):
                c = a.pcolormesh(allnoise[:, :, n].T)
                c.set_clim((cmin, cmax))
                a.set_ylabel('Channel (#)')
                a.set_ylim((0, allnoise.shape[1]))
                a.set_xlim((0, allnoise.shape[0]))
                a.set_title(label[n])
                a.set_xticks([])
            a.set_xticks(xticks)
            a.set_xticklabels(xticklabels)
            a.set_xlabel('Meters per Second')
            fig.suptitle(('All Noise Level Tests'))
            bar = fig.colorbar(c, ax=ax.ravel().tolist())
            bar.set_label('Unknown Kongsberg Units')
            a.set_xticks([])
            a.set_xticks(xticks)
            a.set_xticklabels(xticklabels)
            a.set_xlabel('Meters per Second')
            fig.suptitle(('All Noise Level Tests'))
            bar = fig.colorbar(c, ax=ax.ravel().tolist())
            bar.set_label('Unknown Kongsberg Units')
        elif p66._model == 710:
            p66 = self.getrecord(66, noisetests[0][0])
            p66.parse()
            numchannels = len(p66.data.flatten())
            allnoise = np.zeros((numnoise, numchannels))
            allnoise[:, :] = np.nan
            if numspec > 0:
                p66 = self.getrecord(66, spectests[0][0])
                p66.parse()
                numfreqs = len(p66.data.flatten())
                allspec = np.zeros((numspec, numfreqs))
                for n in range(numspec):
                    p66 = self.getrecord(66, spectests[n][0])
                    p66.parse()
                    allspec[n, :] = p66.data.flatten()
                freq = [str(x) for x in p66.freq]
                c2max = allspec.max()
                c2min = allspec.min()
            # Go through all tests and extract the noise data
            for n in range(numnoise):
                p66 = self.getrecord(66, noisetests[n][0])
                p66.parse()
                allnoise[n, :] = p66.data.flatten()

            # Find the color range for the plots
            cmax = allnoise.max()
            cmin = allnoise.min()
            # set up the xticks
            if xticklabels == []:
                speed = self.getspeed(np.array(noisetests)[:, 1])
                speed = speed.astype(np.int)
                xticklabels = list(set(speed))
                xlabel = 'Meters per Second'
                xspacing = len(speed) / len(xticklabels)
                xticks = list(range(xspacing / 2, len(speed), xspacing))
            elif len(xticklabels) == 1:
                xlabel = 'Alongside'
                xticks = []
                xticklabels = []
            # Plot the data
            fig = plt.figure()
            ax = fig.add_subplot(111)
            c = ax.pcolormesh(allnoise.T)
            c.set_clim((cmin, cmax))
            ax.set_ylabel('Channel (#)')
            ax.set_ylim((0, allnoise.shape[1]))
            ax.set_xlim((0, allnoise.shape[0]))
            ax.set_xticks([])
            ax.set_xticks(xticks)
            ax.set_xticklabels(xticklabels)
            ax.set_xlabel(xlabel)
            ax.set_title(('All Noise Level Tests'))
            bar = fig.colorbar(c, ax=ax)
            bar.set_label('Noise Levels (dB)')
            if numspec > 0:
                yspacing = numfreqs / len(freq)
                yticks = list(range(yspacing / 2, numfreqs, yspacing))
                fig2 = plt.figure()
                ax2 = fig2.add_subplot(111)
                c2 = ax2.pcolormesh(allspec.T)
                c2.set_clim((c2min, c2max))
                ax2.set_ylabel('Frequency (kHz)')
                ax2.set_ylim((0, allspec.shape[1]))
                ax2.set_yticks([])
                ax2.set_yticks(yticks)
                ax2.set_yticklabels(freq)
                ax2.set_xlim((0, allspec.shape[0]))
                ax2.set_xticks([])
                ax2.set_xticks(xticks)
                ax2.set_xticklabels(xticklabels)
                ax2.set_xlabel(xlabel)
                ax2.set_title(('All Noise Spectrum Level Tests'))
                bar2 = fig2.colorbar(c2, ax=ax2)
                bar2.set_label('Noise Levels (dB)')
                return allnoise.T, allspec.T, xticklabels, freq
            else:
                return allnoise.T, np.array([]), xticklabels, []

    def extract_passive_wc(self, badsamples=20):
        """
        Builds an array of noise data by averaging the watercolumn from the
        file. TVG is not removed from the water column backscatter because
        there is assumed to be no TVG in passive mode (confirmed by Kongsberg).
        The speed and linear average noise by beam is returned.
        """
        # there are some unfilled samples at the end of the array
        print("***Warning: dropping the last " + str(badsamples) + " samples in range***")
        speeds = []
        noise = []
        #    pingfft = []
        totalsamples = 0
        if '80' not in self.map.packdir:
            altfile = self.infilename[:-3] + 'all'
            if os.path.isfile(altfile):
                b = allRead(altfile)
                b.mapfile()
            else:
                print('No Speed source found')
        else:
            altfile = ''
        if '107' in self.map.packdir:
            numwc = len(set(self.map.packdir['107'][:, 3]))
            for n in range(numwc):
                subpack = self.getwatercolumn(n)
                if len(altfile) == 0:
                    speed = self.getspeed(self.packet.gettime())
                else:
                    speed = b.getspeed(self.packet.gettime())
                if not np.isnan(speed):
                    speeds.append(speed)
                    if totalsamples == 0:
                        totalsamples = subpack.ampdata.shape[0] - badsamples
                    wc = subpack.ampdata[:totalsamples, :].astype(np.float64)
                    wc = 10 ** (wc / 10)
                    noise.append(10 * np.log10(wc.mean(axis=0)))
        if len(altfile) != 0:
            b.close()
        # rearrange the data into arrays and by increasing speed
        noise = np.asarray(noise).T
        speeds = np.squeeze(np.asarray(speeds))
        idx = np.argsort(speeds)
        speeds = np.squeeze(speeds[idx])
        noise = np.squeeze(noise[:, idx])
        # go through each beam for the series and find the indices that are outside of 3std
        raw_std = noise.std(axis=1)
        raw_mean = noise.mean(axis=1)
        raw_idx = []
        for m in range(noise.shape[0]):
            temp_idx = np.nonzero(
                (noise[m, :] > raw_mean[m] + 3 * raw_std[m]) | (noise[m, :] < raw_mean[m] - 3 * raw_std[m]))
            if len(temp_idx) > 0:
                for k in temp_idx[0]:
                    raw_idx.append(k)
        raw_bad_idx = np.array(list(set(raw_idx)))
        filtered = np.delete(noise, raw_bad_idx, axis=1)
        # take the mean of the remaining data
        lin_noise = 10 ** (filtered / 10)
        lin_mean_noise = lin_noise.mean(axis=1)
        mean_noise = np.squeeze(10 * np.log10(lin_mean_noise))
        return speeds, noise, mean_noise

    def get_measured_used_sss(self):
        """
        This method extracts the surface sound speed as measured and samples it
        based on the time stamps of the XYZ88 record.  Both the XYZ88 Surface
        Sound Speed and the measured sound speed are returned.
        """
        t = self.map.packdir['88'][:, 1]
        mss = self.get_sss(t)
        fss = np.zeros(len(t))
        for n, m in enumerate(fss):
            s = self.getrecord(88, n)
            fss[n] = s.header['SoundSpeed']
        return np.array([t, mss, fss]).T

    def build_wc_h5(self):
        """
        This is a method for building hdf5 files containing the watercolumn
        data.  The purpose is to improve access to multiple records for running
        statistics quickly and simply without running out of memory.
        """
        if have_tables:
            outfilename = self.infilename + '.h5'
            # build the header table used for finding specific metadata
            self.tblfile = tbl.openFile(outfilename, mode='w', title='Storing watercolumn data')
            metadata_grp = self.tblfile.create_group('/', 'metadata', 'Header Information')
            header_tbl = self.tblfile.create_table(metadata_grp, 'header', wcheader, 'table of header data')
            hdr = header_tbl.row
            extra_tbl = self.tblfile.create_table(metadata_grp, 'extra', wcextra, 'table of supporting extra data')
            extra = extra_tbl.row
            # save any general file metadata
            fileinfo_tbl = self.tblfile.create_table(metadata_grp, 'fileinfo', wcfile, 'table of file data')
            fileinfo = fileinfo_tbl.row
            fileinfo['Infilename'] = self.infilename
            fileinfo.append()
            fileinfo_tbl.flush()
            # create a group to hold the water column data from each ping
            wc_group = self.tblfile.create_group('/', 'Watercolumn', title='The data')
            # numwc is just an estimate.  Not all pings have packets with the same time stamp
            if not self.mapped:
                self.mapfile()
            numwc = len(set(self.map.packdir['107'][:, 1]))
            progress = 0
            for n in range(numwc):
                ping = self.getwatercolumn(n)
                # get the ping header information
                hdr['PingCounter'] = ping.header['PingCounter']
                hdr['SystemSerialNum'] = ping.header['SystemSerial#']
                hdr['NumOfDatagrams'] = ping.header['#OfDatagrams']
                hdr['DatagramNum'] = ping.header['Datagram#']
                hdr['NumTxSectors'] = ping.header['#TxSectors']
                hdr['TotalNumBeams'] = ping.header['Total#Beams']
                hdr['NumBeamsInDatagram'] = ping.header['NumberBeamsInDatagram']
                hdr['SoundSpeed'] = ping.header['SoundSpeed']
                hdr['SamplingFrequency'] = ping.header['SamplingFrequency']
                hdr['TxHeave'] = ping.header['TxHeave']
                hdr['TVGfunction'] = ping.header['TVGfunction']
                hdr['ScanningInfo'] = ping.header['ScanningInfo']
                hdr.append()
                # storing the wc in linear units
                wc = 10 ** (ping.ampdata / 20)
                try:
                    name = 'ping' + str(ping.header['PingCounter'])
                    x = self.tblfile.createCArray(wc_group, name, tbl.Float32Atom(), wc.shape)
                    x[:, :] = wc
                except:
                    print(numwc)
                # get additional helpful info
                t = self.packet.gettime()
                extra['POSIXtime'] = t
                extra['Speed'] = self.getspeed(t)
                extra['PingInFile'] = n
                x, y = ping.ampdata.shape
                extra['TotalSamples'] = x
                extra['TotalBeams'] = y
                extra['PingMean'] = wc.mean()
                extra['PingStd'] = wc.std()
                extra['PingName'] = name
                extra.append()
                current = 100 * n / numwc
                if current - progress >= 1:
                    progress = current
                    sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' % {'percent': progress})
            header_tbl.flush()
            extra_tbl.flush()
            self.tblfile.close()
        else:
            print("pytables module unavailable.")


def print_some_records(file_object: AllRead, recordnum: int = 50):
    """
    Used in Kluster file analyzer, print out the first x records in the file for the user to examine
    """
    cur_counter = 0
    if isinstance(file_object, str):
        file_object = AllRead(file_object)
    if isinstance(file_object, AllRead):
        file_object.infile.seek(0)
        file_object.eof = False
        while not file_object.eof and cur_counter < recordnum + 1:
            cur_counter += 1
            print('*****************************************************')
            file_object.read()
            try:
                print(file_object.packet.display())
            except:
                print('unable to display packet')
                continue
            try:
                file_object.get()
            except:
                print('unable to decode record')
                continue
            try:
                print(file_object.packet.subpack)
            except:
                print('no decoded data found to display')
                continue
            if file_object.packet.dtype in [78, 102]:
                print(file_object.packet.subpack.tx_data)
                print(file_object.packet.subpack.rx_data)
            elif file_object.packet.dtype == 65:
                print(file_object.packet.subpack.att)
            elif file_object.packet.dtype == 110:
                print(file_object.packet.subpack.att_data)
            elif file_object.packet.dtype == 85:
                print(file_object.packet.subpack.ss)
    else:
        print(f'PAR3: Found file object that is not an instance of AllRead: {file_object}')


def kluster_read_test(file_object, byte_count: int = 2000000):
    """
    Used in Kluster file analyzer, print out the kluster desired records in a chunk of the file with byte length byte_count
    """
    if isinstance(file_object, str):
        file_object = AllRead(file_object)
    if isinstance(file_object, AllRead):
        print(f'File: {file_object.infilename}')
        print(f'File size: {file_object.max_filelen}')
        print(f'Has Data110 record: {file_object.has_data110()}')
        print(f'Has older rangeangle datagram: {file_object.has_old_style_rangeangle()}')
        if byte_count == -1:
            byte_count = file_object.max_filelen
        else:
            byte_count = min(byte_count, file_object.max_filelen)
        file_object.infile.seek(0)
        file_object.end_ptr = byte_count
        file_object.start_ptr = 0
        file_object.filelen = int(file_object.end_ptr - file_object.start_ptr)
        data = file_object.sequential_read_records(first_installation_rec=False)
        for ky, val in data.items():
            if isinstance(val, dict):
                for subky, subval in val.items():
                    if isinstance(subval, dict):
                        for subsubky, subsubval in subval.items():
                            try:
                                print(subsubky, subsubval.shape, f'Found NaN values: {np.count_nonzero(np.isnan(subsubval))}', f'Found zero values: {np.count_nonzero(subsubval == 0)}')
                            except:
                                print(subsubky)
                            print(subsubval)
                    else:
                        try:
                            print(subky, subval.shape, f'Found NaN values: {np.count_nonzero(np.isnan(subval))}', f'Found zero values: {np.count_nonzero(subval == 0)}')
                        except:
                            print(subky)
                        print(subval)
            else:
                try:
                    print(ky, val.shape, f'Found NaN values: {np.count_nonzero(np.isnan(val))}', f'Found zero values: {np.count_nonzero(val == 0)}')
                except:
                    print(ky)
                print(val)
    else:
        print(f'PAR3: Found file object that is not an instance of AllRead: {file_object}')


if __name__ == '__main__':
    main()
