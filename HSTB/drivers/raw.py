"""
raw.py
G.Rice 20130824

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Version 0.0.4 20170606

This module is a distilled form of an earlier module, py60.  It was designed to work 
with data that follows the format from the er60 reference manual, but has been
extended by converting various matlab readers to add additional datagrams, such
as RAW1. 
"""
import glob
import os.path
import sys
import pickle
import xml.etree.ElementTree as et
import numpy as np
import copy
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from scipy import ndimage, signal
import cv2

import warnings

plt.ion()

saildrone_vessel_draft = 1.96


class readraw:
    """
    This class handles the file I/O for a Simrad RAW file using the datagram
    classes also contained in this module.  The provided filename is opened
    for reading.
    """

    def __init__(self, infilename, verbose=False, start_ptr=0, end_ptr=0):
        """
        Opens the given file and initializes some class variables.
        """
        self.infilename = infilename
        self.infile = open(infilename, 'rb')
        self.mapped = False
        self.is_read = False
        self.eof = False
        self.error = False
        self.start_ptr = start_ptr
        self.end_ptr = end_ptr

        # added with the inclusion of this driver in kluster.  You can specify where you want to start/end in the file
        #  with start_ptr/end_ptr.  If you do, seek_next_startbyte will find the starting place for decoding.
        if start_ptr != 0:
            self.at_right_byte = False
            self.seek_next_startbyte()
        else:
            self.at_right_byte = True

        if end_ptr:
            self.filelen = int(self.end_ptr - self.start_ptr)
        else:
            self.infile.seek(-self.start_ptr, 2)
            self.filelen = self.infile.tell()
        self.infile.seek(0, 2)
        self.max_filelen = self.infile.tell()
        self.infile.seek(self.start_ptr, 0)

    def close(self):
        self.infile.close()

    def seek_next_startbyte(self):
        """
        Determines if current pointer is at the start of a record.  If not, finds the next valid one.
        """
        record_ids = [b'XML0', b'CON0', b'CON1', b'NME0', b'RAW0', b'RAW3', b'TAG0']
        # check is to continue on until you find one of the record ids
        while not self.at_right_byte:
            cur_ptr = self.infile.tell()
            if cur_ptr >= self.start_ptr + self.filelen - 4:  # minus four for the seek we do to get ready for the next search
                self.eof = True
                raise ValueError('Unable to find sonar startbyte, checked for all valid datagrams: ')

            # consider start bytes right at the end of the given filelength as valid, even if they extend over to the next chunk
            srchdat = self.infile.read(min(100, (self.start_ptr + self.filelen) - cur_ptr))
            earliest = 999
            stx_idx = -1
            for poss_rec in record_ids:
                found_idx = srchdat.find(poss_rec)
                if -1 < found_idx < earliest:  # found an id, and it comes earlier than the current earliest found id
                    earliest = found_idx
                    stx_idx = found_idx

            if stx_idx >= 0:  # found a record id, start of the record would be four bytes behind to include the record size
                rec_start = cur_ptr + stx_idx - 4
                self.infile.seek(rec_start)
                self.at_right_byte = True

            if stx_idx < 0:
                self.infile.seek(-4, 1)  # get ready for the next search, allow for edge case where rec id is across chunks

    def read(self, dtype=None):
        """
        Reads the packet header.
        """

        # if running this without offset/maxlen arguments, don't have to worry about finding the startbyte.
        #    otherwise you gotta search for the next one...should only need to do it once
        if not self.at_right_byte:
            self.seek_next_startbyte()

        if self.infile.tell() >= self.start_ptr + self.filelen:
            self.eof = True
        if not self.eof:
            # an extra 8 bytes to get header and footer
            packetsize = 8 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0]
            self.infile.seek(-4, 1)
            if (self.filelen >= self.infile.tell() - self.start_ptr + packetsize) or (self.end_ptr > 0):
                self.packet = Datagram(self.infile.read(packetsize))
                self.is_read = True
                if not self.packet.valid:
                    self.error = True
            else:
                self.eof = True
                self.error = True
                print(f'Broken packet found at {self.infile.tell()}')
                print(f'Final packet size {packetsize}')
            if dtype is not None and self.packet.header[1] != dtype:
                self.read(dtype)

    def get(self):
        """
        Decodes the data section of the datagram if a packet has been read but
        not decoded.  If excecuted the is_read flag is set to False.
        """
        if self.is_read and not self.packet.decoded:
            self.packet.decode()
            self.is_read = False

    def mapfile(self, verbose=False):
        """
        Maps the datagrams in the file.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack()
            self.reset()
            print('Mapping file;           ', end='')
            while not self.eof:
                loc = self.infile.tell()
                self.read()
                dtype = self.packet.header[1]
                time = self.packet.gettime()
                self.map.add(str(dtype), loc, time)
                current = 100 * loc / self.filelen
                if current - progress >= 1 and verbose:
                    progress = current
                    sys.stdout.write(f'\b\b\b\b\b\b\b\b\b\b{progress} percent')
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            if self.error:
                print()
            else:
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
            mapfilename = self.infilename[:-3] + 'nav'
        try:
            self.map = mappack()
            self.map.load(mapfilename)
            self.mapped = True
            print(f'loaded file map {mapfilename}')
        except IOError:
            print(f'{mapfilename} map file not found.')

    def savefilemap(self):
        """
        Saves the mappack packdir dictionary for faster operations on a file in
        the future.  The file is saved under the same name as the loaded file
        but with a 'par' extension.
        """
        if self.mapped:
            mapfilename = self.infilename[:-3] + 'nav'
            self.map.save(mapfilename)
            print(f'file map saved to {mapfilename}')
        else:
            print('no map to save.')

    def getrecord(self, recordtype, recordnum):
        """
        Gets the record number of the described record type.
        """
        self.eof = False
        if not self.mapped:
            self.mapfile()
        if recordtype in self.map.packdir:
            loc = int(self.map.packdir[recordtype][recordnum][0])
            self.infile.seek(loc)
            self.read()
            self.get()
            return self.packet.subpack
        else:
            print(f'record {recordtype} not available.')
            return None

    def display(self):
        """
        Prints the current record header and record type header to the command
        window.  If the record type header display method also contains a plot
        function a plot will also be displayed.
        """
        if self.is_read:
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
        self.infile.seek(0)
        self.is_read = False
        self.eof = False
        if 'packet' in self.__dict__:
            del self.packet

    def _save_state(self):
        return [self.at_right_byte, self.infile.tell(), self.start_ptr, self.eof]

    def _load_state(self, stateblock: list):
        self.at_right_byte = stateblock[0]
        self.infile.seek(stateblock[1])
        self.start_ptr = stateblock[2]
        self.eof = stateblock[3]

    def fast_read_start_end_time(self):
        """
        Get the start and end time for the dataset without mapping the file first

        Returns
        -------
        list, [starttime: float, first time stamp in data, endtime: float, last time stamp in data]

        """

        starttime = None
        endtime = None
        stateblock = self._save_state()

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
                    raise ValueError(f'raw: {self.infilename}: Unable to read the time of the first record.')

        # Move the start/end file pointers towards the end of the file and get the last available time
        self.infile.seek(0, 2)
        chunksize = min(50 * 1024, self.infile.tell())  # pick 50 of reading just to make sure you get some valid records, or the filelength if it is less than that
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
            raise ValueError(f'raw: {self.infilename}: Unable to find a suitable packet to read the end time of the file')

        self._load_state(stateblock)
        return [starttime, endtime]

    def fast_read_serial_number(self):
        """
        Get the serial numbers and model number of the provided file without mapping the file first.

        Returns
        -------
        list, [serialnumber: int, secondaryserialnumber: int, sonarmodelnumber: str]

        """

        stateblock = self._save_state()

        self.infile.seek(0)
        self.eof = False

        self.read()
        datagram_type = str(self.packet.dtype)
        if datagram_type == 'CON0':
            self.get()
            sonarmodel = 'EK60'
            serialnumber = int(self.packet.subpack.serial_numbers[0])  # get the lowest freq serial number as the identifier
        elif datagram_type == 'XML0':
            self.get()
            sonarmodel = 'EK80'
            serialnumber = 0
            # if this is a config XML0 (which it always should be I think) it will have the installation parameters
            if self.packet.subpack.installation_parameters:
                serialnumber = int(self.packet.subpack.installation_parameters['tx_serial_number'])
            else:
                # try looking through the first few records
                for i in range(100):
                    self.read()
                    if self.packet.dtype == 'XML0':
                        self.get()
                        if self.packet.subpack.installation_parameters:
                            serialnumber = int(self.packet.subpack.installation_parameters['tx_serial_number'])
                            break
                if not serialnumber:
                    print(f'raw: WARNING - unable to find the XML0 Configuration record at the beginning of this file: {self.infilename}')
        else:
            raise ValueError(f'raw: Unable to find first configuration record, looked for CON0 and XML0, got {datagram_type}')

        self._load_state(stateblock)
        return [serialnumber, 0, sonarmodel]

    def return_installation_parameters(self):
        stateblock = self._save_state()

        self.infile.seek(0)
        self.eof = False
        self.read()
        try:
            assert self.packet.dtype in ['CON0', 'XML0']
        except AssertionError:
            print(f'raw: ERROR - we assume the first record is always either CON0 or XML0, and that is not the case for this file ({self.infilename})')
        self.get()
        iparams = self.packet.subpack.installation_parameters
        finalrec = {'installation_params': {'time': np.array([self.packet.subpack.time], dtype=float),
                                            'serial_one': np.array([iparams['tx_serial_number']], dtype=np.dtype('uint64')),
                                            'serial_two': np.array([iparams['tx_2_serial_number']], dtype=np.dtype('uint64')),
                                            'installation_settings': np.array([iparams], dtype=np.object)}}

        self._load_state(stateblock)
        return finalrec

    def has_position(self):
        """
        Return True if we find any position data in the NMEA records within the first 200 records of the file
        """
        stateblock = self._save_state()

        self.infile.seek(0)
        self.eof = False
        found = False
        for i in range(200):
            self.read()
            datagram_type = str(self.packet.dtype)
            if datagram_type == 'NME0':
                self.get()
                rec_nme0 =  self.packet.subpack
                if rec_nme0.header:
                    if 'lat' in self.packet.subpack.header:
                        found = True
                        break
        self._load_state(stateblock)
        return found

    def has_attitude(self):
        """
        Return True if we find any attitude data in the NMEA records within the first 200 records of the file
        """
        stateblock = self._save_state()

        self.infile.seek(0)
        self.eof = False
        found = False
        for i in range(200):
            self.read()
            datagram_type = str(self.packet.dtype)
            if datagram_type == 'NME0':
                self.get()
                rec_nme0 =  self.packet.subpack
                if rec_nme0.header:
                    if 'roll' in self.packet.subpack.header:
                        found = True
                        break
        self._load_state(stateblock)
        return found

    def preferred_nmea_position_record(self):
        """
        Get a list of the available position records in the file.  We want to prefer GGA, as the lat/lon data appears to have
        a higher precision for some reason, and it has altitude, which can be useful.
        """

        stateblock = self._save_state()
        self.infile.seek(0)
        self.eof = False
        list_of_pos_records = []
        for i in range(100):
            self.read()
            datagram_type = str(self.packet.dtype)
            if datagram_type == 'NME0':
                self.get()
                rec_nme0 =  self.packet.subpack
                if rec_nme0.header:
                    if rec_nme0.header['type'] not in list_of_pos_records:
                        list_of_pos_records.append(rec_nme0.header['type'])

        self._load_state(stateblock)
        if not list_of_pos_records:
            return None
        elif 'GGA' in list_of_pos_records:
            return 'GGA'
        elif 'RMC' in list_of_pos_records:
            return 'RMC'
        elif 'GLL' in list_of_pos_records:
            return 'GLL'

    def _sort_raw_xml0_pairings(self, raw_group: list, xml_group: list):
        if xml_group:  # RAW3
            # first align the raw and xml groups by channel id, so that you ensure you get the right ones
            raw_channel_ids = [rg.header['ChannelID'] for rg in raw_group]
            xml_channel_ids = [xmg.header['ChannelID'] for xmg in xml_group]
            try:
                sort_idxs = [raw_channel_ids.index(xid) for xid in xml_channel_ids]
            except ValueError:
                print(f'raw: ERROR - found mismatched RAW3 {raw_channel_ids} and XML0 {xml_channel_ids} groupings, skipping...')
                return None, None
            sortedxml = [xml_group[sid] for sid in sort_idxs]
            # now sort so that the lowest freq comes first
            xmlfreq = [float(xmg.header['Frequency']) for xmg in sortedxml]
            sort_freq_idxs = np.argsort(xmlfreq)
            return [raw_group[sidx] for sidx in sort_freq_idxs], [xml_group[sidx] for sidx in sort_freq_idxs]
        else:  # RAW0, no XML0 record that goes with it
            # sort so that the lowest freq comes first
            rawfreq = [float(rg.header['Frequency']) for rg in raw_group]
            sort_freq_idxs = np.argsort(rawfreq)
            return [raw_group[sidx] for sidx in sort_freq_idxs], xml_group

    def _process_raw_group(self, raw_group: list, xml_group: list, recs_to_read: dict, serialnumber: int):
        if raw_group:
            raw_group, xml_group = self._sort_raw_xml0_pairings(raw_group, xml_group)
            if isinstance(raw_group[0], Raw0):
                pulselengths = np.array([rg.header['PulseLength'] for rg in raw_group])
                sampleintervals = np.array([rg.header['SampleInterval'] for rg in raw_group])
                drafts = np.array([rg.header['TransducerDepth'] for rg in raw_group])
                soundspeed = np.array([rg.header['SoundVelocity'] for rg in raw_group])
            else:  # RAW3
                pulselengths = np.array([float(xg.header['PulseDuration']) for xg in xml_group])
                sampleintervals = np.array([float(xg.header['SampleInterval']) for xg in xml_group])
            offsets = np.array([rg.header['Offset'] for rg in raw_group])
            max_samples = max([rg.numsamples for rg in raw_group])

            max_pulse_len = pulselengths.max()
            if not np.all([sampleintervals[0] == si for si in sampleintervals]):
                raise ValueError('raw: All Sampling intervals are assumed to be the same but are not...')

            powers = np.full((max_samples, len(raw_group)), np.nan)
            for cnt, rg in enumerate(raw_group):
                offset = rg.header['Offset']
                if isinstance(raw_group[0], Raw0):
                    powers[offset:rg.numsamples, cnt] = rg.power
                else:
                    powers[offset:rg.numsamples, cnt] = 20 * np.log10(np.mean(np.abs(rg.complexsamples), axis=1))

            detect_idx = _image_detection(powers, threshold=30)
            pulse_samps = pulselengths / sampleintervals
            tx_corr = offsets + detect_idx - pulse_samps / 2
            twowaytraveltime = tx_corr * sampleintervals
            twowaytraveltime[detect_idx == -1] = np.nan
            valid = ~np.isnan(twowaytraveltime)
            if valid.all():
                # best return is the highest freq return that is within 'close_enough' of the lowest freq return.  Lets
                #  us get the best representation of the actual seafloor but avoid noise
                best_idx = np.where(valid)[0][0]
                close_enough = 2 * max_pulse_len
                final_best_idx = np.where((twowaytraveltime[best_idx] - twowaytraveltime) < close_enough)[0][-1]
                recs_to_read['ping']['time'].append([raw_group[final_best_idx].time])
                recs_to_read['ping']['counter'].append([0])
                recs_to_read['ping']['serial_num'].append([serialnumber])
                recs_to_read['ping']['tiltangle'].append([0.0])
                recs_to_read['ping']['delay'].append([0.0])
                recs_to_read['ping']['beampointingangle'].append([0.0])
                recs_to_read['ping']['txsector_beam'].append([0])
                recs_to_read['ping']['detectioninfo'].append([0])
                recs_to_read['ping']['qualityfactor'].append([0])
                recs_to_read['ping']['traveltime'].append([twowaytraveltime[final_best_idx]])
                recs_to_read['attitude']['time'].append(raw_group[final_best_idx].time)
                recs_to_read['attitude']['heave'].append(0.0)
                if isinstance(raw_group[0], Raw0):
                    recs_to_read['ping']['soundspeed'].append([soundspeed[final_best_idx]])
                    recs_to_read['ping']['frequency'].append([int(raw_group[final_best_idx].header['Frequency'])])
                    recs_to_read['attitude']['roll'].append(raw_group[final_best_idx].roll)
                    recs_to_read['attitude']['pitch'].append(raw_group[final_best_idx].pitch)
                    recs_to_read['attitude']['heading'].append(raw_group[final_best_idx].heading)
                    return drafts[final_best_idx]
                else:
                    recs_to_read['ping']['soundspeed'].append([0.0])
                    recs_to_read['ping']['frequency'].append([int(xml_group[final_best_idx].header['Frequency'])])
                    recs_to_read['attitude']['roll'].append(0.0)
                    recs_to_read['attitude']['pitch'].append(0.0)
                    recs_to_read['attitude']['heading'].append(0.0)
                    return 0.0
            return None
        else:
            return None

    def _initialize_sequential_read_datastore(self):
        return {'attitude': {'time': [], 'roll': [], 'pitch': [], 'heave': [], 'heading': []},
                'installation_params': {'time': [], 'serial_one': [], 'serial_two': [],
                                        'installation_settings': []},
                'ping': {'time': [], 'counter': [], 'soundspeed': [], 'serial_num': [],
                         'tiltangle': [], 'delay': [], 'frequency': [],
                         'beampointingangle': [], 'txsector_beam': [], 'detectioninfo': [],
                         'qualityfactor': [], 'traveltime': []},
                'runtime_params': {'time': [], 'mode': [], 'modetwo': [], 'yawpitchstab': [],
                                   'runtime_settings': []},
                'profile': {'time': None, 'depth': None, 'soundspeed': None},
                'navigation': {'time': [], 'latitude': [], 'longitude': [], 'altitude': []}}

    def _finalize_records(self, recs_to_read, draft, iparams):
        if self.start_ptr:
            # either the first chunk of a series of chunks, or we aren't doing a chunked read, so log the installation params
            iparams['installation_params']['installation_settings'][0]['waterline_vertical_location'] = str(draft)
            recs_to_read['installation_params'] = iparams
        else:
            recs_to_read['installation_params'] = {'time': np.array([]), 'serial_one': np.array([]), 'serial_two': np.array([]),
                                                   'installation_settings': np.array([])}
        # no runtime parameters to log with ek data
        recs_to_read['runtime_params']['time'] = np.array(recs_to_read['ping']['time'][0], np.float64)
        recs_to_read['runtime_params']['mode'] = np.array([''], 'U2')
        recs_to_read['runtime_params']['modetwo'] = np.array([''], 'U2')
        recs_to_read['runtime_params']['yawpitchstab'] = np.array([''], 'U2')
        recs_to_read['runtime_params']['runtime_settings'] = np.array([''], 'object')

        recs_to_read['attitude']['time'] = np.array(recs_to_read['attitude']['time'], np.float64)
        recs_to_read['attitude']['roll'] = np.array(recs_to_read['attitude']['roll'], np.float32)
        recs_to_read['attitude']['pitch'] = np.array(recs_to_read['attitude']['pitch'], np.float32)
        recs_to_read['attitude']['heading'] = np.array(recs_to_read['attitude']['heading'], np.float32)

        recs_to_read['navigation']['time'] = np.array(recs_to_read['navigation']['time'], np.float64)
        recs_to_read['navigation']['latitude'] = np.array(recs_to_read['navigation']['latitude'], np.float64)
        recs_to_read['navigation']['longitude'] = np.array(recs_to_read['navigation']['longitude'], np.float64)
        if 'altitude' in recs_to_read['navigation']:
            recs_to_read['navigation']['altitude'] = np.array(recs_to_read['navigation']['altitude'], np.float32)

        recs_to_read['ping']['time'] = np.array(recs_to_read['ping']['time'], np.float64)
        recs_to_read['ping']['counter'] = np.array(recs_to_read['ping']['counter'], 'uint32')
        recs_to_read['ping']['soundspeed'] = np.array(recs_to_read['ping']['soundspeed'], np.float32)
        recs_to_read['ping']['serial_num'] = np.array(recs_to_read['ping']['serial_num'], 'uint64')
        recs_to_read['ping']['tiltangle'] = np.array(recs_to_read['ping']['tiltangle'], np.float32)
        recs_to_read['ping']['delay'] = np.array(recs_to_read['ping']['delay'], np.float32)
        recs_to_read['ping']['frequency'] = np.array(recs_to_read['ping']['frequency'], 'int32')
        recs_to_read['ping']['beampointingangle'] = np.array(recs_to_read['ping']['beampointingangle'], np.float32)
        recs_to_read['ping']['txsector_beam'] = np.array(recs_to_read['ping']['txsector_beam'], np.float64)
        recs_to_read['ping']['detectioninfo'] = np.array(recs_to_read['ping']['detectioninfo'], 'int32')
        recs_to_read['ping']['qualityfactor'] = np.array(recs_to_read['ping']['qualityfactor'], 'float32')
        recs_to_read['ping']['traveltime'] = np.array(recs_to_read['ping']['traveltime'], 'float32')

        # jump to sv correct in Kluster, by putting in processed beam angles (we assume angle = 0)
        recs_to_read['ping']['rel_azimuth'] = np.full(recs_to_read['ping']['beampointingangle'].shape, 0.0, np.float32)
        recs_to_read['ping']['corr_pointing_angle'] = np.full(recs_to_read['ping']['beampointingangle'].shape, 0.0, np.float32)
        recs_to_read['ping']['processing_status'] = np.full(2, recs_to_read['ping']['beampointingangle'].shape, 'uint8')

        # build heave
        heavetime, newheave = calculate_heave_correction(recs_to_read['ping']['time'].ravel(), recs_to_read['ping']['traveltime'].ravel(),
                                                        recs_to_read['ping']['soundspeed'].ravel())
        if heavetime.shape[0] != recs_to_read['attitude']['time'].shape[0]:
            newheave = np.interp(recs_to_read['attitude']['time'], heavetime, newheave)
        recs_to_read['attitude']['heave'] = newheave
        return recs_to_read

    def sequential_read_records(self, first_installation_rec=False):
        """
        Using global recs_categories, parse out only the given datagram types by reading headers and decoding only
        the necessary datagrams.

        """

        if first_installation_rec:  # only return the needed installation parameters
            return self.return_installation_parameters()
        else:
            iparams = self.return_installation_parameters()
            serialnumber = iparams['installation_params']['installation_settings'][0]['tx_serial_number']
            sonarmodelnumber = iparams['installation_params']['installation_settings'][0]['sonar_model_number']
            transducer_names = iparams['installation_params']['installation_settings'][0]['ektransducer_names']
        recs_to_read = self._initialize_sequential_read_datastore()

        if sonarmodelnumber == 'EK60':
            desired_record = 'RAW0'
        else:
            desired_record = 'RAW3'
        navrec = self.preferred_nmea_position_record()
        if not navrec:
            utctme, lat, lon = get_saildrone_navigation(self.infilename)
            if utctme is None:
                print(f'raw: unable to find any position information either in this file or in nearby .gps.csv files: {self.infilename}')
                return None
            recs_to_read['navigation']['time'] = utctme
            recs_to_read['navigation']['latitude'] = lat
            recs_to_read['navigation']['longitude'] = lon
            recs_to_read['navigation'].pop('altitude')

        if self.start_ptr:
            self.at_right_byte = False  # for now assume that if a custom start pointer is provided, we need to seek the start byte
        self.infile.seek(self.start_ptr)
        self.eof = False

        heads = []
        xml_parameters = []
        rectime = 0
        draft = 0
        first_rec = True
        while not self.eof:
            self.read()  # find the start of the record and read the header
            datagram_type = str(self.packet.dtype)
            if datagram_type in [desired_record, 'XML0']:
                self.get()
                if datagram_type == 'XML0' and self.packet.subpack.type != 'Channel':
                    continue
                rec = self.packet.subpack
                # first head in the transducer group, or the first xml message (ideally we could assume xml is first, but Im not sure about that)
                if (not heads and datagram_type == desired_record) or (not xml_parameters and datagram_type == 'XML0'):
                    if datagram_type == 'XML0':
                        xml_parameters.append(rec)
                    else:
                        heads.append(rec)
                    if rectime and rec.time != rectime:
                        raise ValueError('raw: Found XML0/RAW3 datagrams out of sequence!')
                    rectime = rec.time
                else:  # one of the accompanying heads or messages
                    if rec.time == rectime:  # the rec is in the current group
                        if datagram_type == 'XML0':
                            xml_parameters.append(rec)
                        else:
                            heads.append(rec)
                    else:  # the time is different, so this must not belong to the current group
                        if (len(heads) != len(transducer_names)) or (len(xml_parameters) != len(transducer_names) and desired_record == 'RAW3'):
                            if self.start_ptr and first_rec:  # if you start in the middle of a group, just skip it, the other sequential_read will pick it up
                                heads = []
                                xml_parameters = []
                                rectime = 0
                            else:
                                print(f'raw: WARNING - found {desired_record} grouping at record time {rectime} that only contained {len(heads)}/{len(xml_parameters)} records/parameters, expected {len(transducer_names)}')
                        read_draft = self._process_raw_group(heads, xml_parameters, recs_to_read, serialnumber)
                        if read_draft is not None:
                            draft = read_draft
                        first_rec = False
                        heads = []
                        xml_parameters = []
                        if datagram_type == 'XML0':
                            xml_parameters.append(rec)
                        else:
                            heads.append(rec)
                        rectime = rec.time
            elif datagram_type == 'NME0' and navrec:
                self.get()
                sub_datagram_type = str(self.packet.subpack.rectype)
                if sub_datagram_type == navrec:
                    recs_to_read['navigation']['time'].append(self.packet.subpack.time)
                    recs_to_read['navigation']['latitude'].append(self.packet.subpack.header['lat'])
                    recs_to_read['navigation']['longitude'].append(self.packet.subpack.header['lon'])
                    if 'altitude' in self.packet.subpack.header:
                        recs_to_read['navigation']['altitude'].append(self.packet.subpack.header['altitude'])
                    elif 'altitude' in recs_to_read['navigation']:
                        recs_to_read['navigation'].pop('altitude')

        if not navrec:  # override for saildrone draft
            draft = saildrone_vessel_draft
        recs_to_read = self._finalize_records(recs_to_read, draft, iparams)
        recs_to_read['format'] = 'raw'
        return recs_to_read


class Datagram:
    """
    The datagram holder.  Reads the header section of the provided memory
    block and holds a list with the datagram information through the time
    stamp.  Also, the datagram type is stored in variable 'dtype'.  Flags
    are set to indicate whether the rest of the datagram has been decoded,
    and the decoded data is stored in a datagram specific object called
    'subpack'. The maketime method is called upon initialization and
    a 'time' variable is created containing a POSIX time with the packet
    time. 'valid' indicates whether the sync pattern is present, 'decoded'
    indicated if the datagram has been decoded, and 'checksum' contains the
    checksum field.
    Note: While not required of these datagrams, the size of the datagram, as
    if coming from a file, is expected at the beginning of these datablocks.
    """

    hdr_dtype = np.dtype([('Bytes', 'I'), ('Type', 'U4'), ('Time', 'Q')])

    def __init__(self, fileblock, byteswap=False):
        """
        Reads the header section, which is the first 16 bytes, of the
        given memory block.
        """
        tmp_dtype = np.dtype([('Bytes', 'I'), ('Type', 'S4'), ('Time', 'Q')])
        hdr_sz = tmp_dtype.itemsize
        tmp = np.frombuffer(fileblock[:hdr_sz], dtype=tmp_dtype)[0]
        self.header = tmp.astype(Datagram.hdr_dtype)
        self.decoded = False
        footer = np.frombuffer(fileblock[-4:], dtype=np.uint32, count=1)[0]
        if self.header[0] == footer:
            self.valid = True
        else:
            self.valid = False
        self.datablock = fileblock[hdr_sz:-4]
        self.dtype = self.header[1]
        self.maketime()

    def decode(self):
        """
        Directs to the correct decoder.
        """
        self.decoded = True
        if self.dtype == 'CON0':
            self.subpack = Con0(self.datablock, self.time)
        elif self.dtype == 'CON1':
            self.subpack = Con1(self.datablock, self.time)
        elif self.dtype == 'RAW0':
            self.subpack = Raw0(self.datablock, self.time)
        elif self.dtype == 'RAW1':
            self.subpack = Raw1(self.datablock, self.time)
        elif self.dtype == 'RAW3':
            self.subpack = Raw3(self.datablock, self.time)
        elif self.dtype == 'NME0':
            self.subpack = Nme0(self.datablock, self.time)
        elif self.dtype == 'TAG0':
            self.subpack = Tag0(self.datablock, self.time)
        elif self.dtype == 'XML0':
            self.subpack = Xml0(self.datablock, self.time)
        else:
            print(f'Data record {self.dtype} decoding is not yet supported.')
            self.decoded = False

    def maketime(self):
        """
        Converts the header time from number of 100 nanoseconds since 1601
        to POSIX time.  UTC is assumed.
        """
        self.time = self.header[2] / 10000000. - 11644473600  # from winNT to POSIX

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
            print(f'{name} : {self.header[n]}')
        print(f'POSIX time : {self.time}')


class Con0:
    """
    The primary configuration datagram.
    """
    hdr_dtype = np.dtype([('SurveyName', 'U128'), ('TransectName', 'U128'),
                          ('SounderName', 'U128'), ('Version', 'U30'), ('Spare', 'S98'),
                          ('TransducerCount', 'I')])
    transducer_dtype = np.dtype([('ChannelId', 'U128'), ('BeamType', 'I'),
                                 ('Frequency', 'f'), ('Gain', 'f'), ('EquivalentBeamAngle', 'f'),
                                 ('BeamWidthAlongship', 'f'), ('BeamWidthAthwartship', 'f'),
                                 ('AngleSensitivityAlongship', 'f'),
                                 ('AngleSensitivityAthwartship', 'f'),
                                 ('AngleOffsetAlongship', 'f'), ('AngleOffsetAthwartship', 'f'),
                                 ('PosX', 'f'), ('PosY', 'f'), ('PosZ', 'f'), ('DirX', 'f'), ('DirY', 'f'),
                                 ('DirZ', 'f'), ('PulseLengthTable', '5f'), ('Spare1', 'U8'),
                                 ('GainTable', '5f'), ('Spare2', 'S8'), ('SaCorrectionTable', '5f'),
                                 ('Spare3', 'S8'), ('GPTSoftwareVersion', 'U16'), ('Spare4', 'S28')])

    def __init__(self, datablock, utctime):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('SurveyName', 'S128'), ('TransectName', 'S128'),
                              ('SounderName', 'S128'), ('Version', 'S30'), ('Spare', 'S98'),
                              ('TransducerCount', 'I')])
        transducer_dtype = np.dtype([('ChannelId', 'S128'), ('BeamType', 'I'),
                                     ('Frequency', 'f'), ('Gain', 'f'), ('EquivalentBeamAngle', 'f'),
                                     ('BeamWidthAlongship', 'f'), ('BeamWidthAthwartship', 'f'),
                                     ('AngleSensitivityAlongship', 'f'),
                                     ('AngleSensitivityAthwartship', 'f'),
                                     ('AngleOffsetAlongship', 'f'), ('AngleOffsetAthwartship', 'f'),
                                     ('PosX', 'f'), ('PosY', 'f'), ('PosZ', 'f'), ('DirX', 'f'), ('DirY', 'f'),
                                     ('DirZ', 'f'), ('PulseLengthTable', '5f'), ('Spare1', 'S8'),
                                     ('GainTable', '5f'), ('Spare2', 'S8'), ('SaCorrectionTable', '5f'),
                                     ('Spare3', 'S8'), ('GPTSoftwareVersion', 'S16'), ('Spare4', 'S28')])
        hdr_sz = hdr_dtype.itemsize
        tmp_hdr = np.frombuffer(datablock[:hdr_sz],
                                dtype=hdr_dtype)[0]
        self.header = tmp_hdr.astype(Con0.hdr_dtype)
        tmp_transducers = np.frombuffer(datablock[hdr_sz:],
                                        dtype=transducer_dtype)
        self.transducers = tmp_transducers.astype(Con0.transducer_dtype)
        self.time = utctime

    def display(self, num_ducer=-1):
        """
        Displays contents of the header to the command window.
        """
        for n, name in enumerate(self.header.dtype.names):
            print(f'{name} : {self.header[n]}')
        if num_ducer >= 0:
            for n, name in enumerate(self.transducers[0].dtype.names):
                print(f'{name} : {self.transducers[num_ducer][n]}')

    @property
    def serial_numbers(self):
        serialnumbers = []
        for trns in self.transducers:
            trns_channelid = trns[0].split(' ')
            if len(trns_channelid) in [6, 7]:
                # something like 'GPT  18 kHz 009072056b0e 1-1 ES18-11' or 'GPT 120 kHz 0090720580f1 4-1 ES120'
                trns_channelid = trns_channelid[-3]
            elif len(trns_channelid) in [3]:
                # something like WBT 5197648-15 ES120-7C
                trns_channelid = trns_channelid[-2]
            else:
                raise ValueError(f'Unable to parse serial number from channel ID for this CON0 record: {trns[0]}')

            try:
                serialnumber = int(trns_channelid, 16)
            except:
                serialnumber = int(''.join([x for x in trns_channelid if x.isdigit()]), 16)
            serialnumbers.append(serialnumber)
        return serialnumbers

    @property
    def installation_parameters(self):
        transsets = {}
        transducer_names = []
        for i in range(len(self.transducers)):
            for nme in self.transducers.dtype.names:
                if nme[:5].lower() != 'spare':
                    if isinstance(self.transducers[i][nme], np.ndarray):
                        val = self.transducers[i][nme].tolist()
                    else:
                        val = self.transducers[i][nme]
                    transsets[f'ektransducer{i}_{nme}'] = val
                    if nme.lower() == 'channelid':
                        transducer_names.append(val)
        # isets represents the minimum information Kluster needs for processing
        isets = {'sonar_model_number': 'EK60', 'transducer_1_vertical_location': '0.000',
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
                 'tx_serial_number': self.serial_numbers[0], 'tx_2_serial_number': '0', 'active_position_system_number': '1',
                 'active_heading_sensor': 'motion_1', 'position_1_datum': 'WGS84'}
        transsets.update(isets)
        transsets['ektransducer_names'] = transducer_names
        return transsets


class Con1:
    """
    The ME70 configuration datagram.
    """

    def __init__(self, datablock, utctime):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        self.data = datablock
        self.time = utctime

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        print(f'{self.data}')


class Raw0:
    """
    The ping acoustic backscatter time series.
    """

    hdr_dtype = np.dtype([
        ('Channel', 'H'),
        ('Mode', 'H'),
        ('TransducerDepth', 'f'),
        ('Frequency', 'f'),
        ('TransmitPower', 'f'),
        ('PulseLength', 'f'),
        ('Bandwidth', 'f'),
        ('SampleInterval', 'f'),
        ('SoundVelocity', 'f'),
        ('AbsorptionCoefficient', 'f'),
        ('Heave', 'f'),
        ('Roll', 'f'),
        ('Pitch', 'f'),
        ('Temperature', 'f'),
        ('Heading', 'f'),
        ('TransmitMode', 'h'),
        ('Spare', 'S6'),
        ('Offset', 'I'),
        ('Count', 'I')])

    def __init__(self, datablock, utctime):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Raw0.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=Raw0.hdr_dtype)[0]
        self.numsamples = self.header['Count'] - self.header['Offset']
        mode = self.header['Mode']
        pointer = hdr_sz
        if mode & 1:
            self.power = np.frombuffer(datablock[pointer:pointer + self.numsamples * 2], dtype='h')
            pointer += self.numsamples * 2
            self.power = self.power.astype('float') * 10 * np.log10(2) / 256.
        if mode & 2:
            self.angle = np.frombuffer(datablock[pointer:pointer + self.numsamples * 2], dtype='2b')
            self.angle = self.angle.astype('float')
            pointer += self.numsamples * 2
            # convert to electrical angle
            self.angle *= 180. / 128
        self.time = utctime

    @property
    def heave(self):
        return self.header['Heave']

    @property
    def roll(self):
        return self.header['Roll']

    @property
    def pitch(self):
        return self.header['Pitch']

    @property
    def heading(self):
        return self.header['Heading']

    def bottom_detect(self, start=0, stop=0, dir=0):
        """
        This is a convenience function to make getting bottom detections
        more straightforward using the user supplied range gates.  This
        method uses the method bottom_detect_idx and
        to determine the range gate in samples provided information. 
        start and stop are ranges in meters.  Returned values are the two 
        way travel times, the electrical angles of the detection relative
        to boresight for the beam, and the reported power at the detection.
        """
        scaler = self.header['SoundVelocity'] * self.header['SampleInterval'] / 2
        start_idx = int(start / scaler)
        if stop == 0:
            stop_idx = -1
        else:
            stop_idx = int(stop / scaler)
        detections = self.bottom_detect_idx(start_idx, stop_idx, dir=0)
        twtt = np.asarray(detections) * self.header['SampleInterval']
        angle_along = self.angle[detections, 0]
        angle_across = self.angle[detections, 1]
        ## power needs to be converted to sv
        power = self.power[detections]
        return twtt, angle_along, angle_across, power

    def bottom_detect_idx(self, start=0, stop=-1, dir=0):
        """
        This method conducts both amplitude and phase detections and returns
        the detection index.  For an amplitude detection only one value is 
        returned.  For a phase detection all samples in the phase ramp are 
        returned.  In each case the type of detection is set in a class varible
        detection_type rather than return to remove clutter in what is
        returned.  See this method for what values mean.
        """
        a = self.amplitude_detect(start=start, stop=stop)
        p = self.phase_detect(a, start=start, stop=stop, dir=0)
        w = self.weber_detect(start=start, stop=stop, dir=0)
        overlap = len(set(p).intersection(set(w)))
        if len(p) < 30:  # and len(w) < 30:
            self.detection_type = 0
            return [a]
        # elif len(p) > 30 and len(w) > 30:
        # if overlap > 30:
        # self.detection_type = 3
        # return p
        # else:
        # self.detection_type = 2
        # return w
        # elif len(p) < 30 and len(w) > 30:
        # self.detection_type = 4
        # return w
        else:
            self.detection_type = 1
            return p

    def amplitude_detect(self, start=0, stop=-1, winlen=20, threshold=-100):
        """
        Conducts an amplitude detection on the current record. The start and
        stop index can be provided as a gate.  The returned index is relative
        to 0 and the start of the time series, not the start index provided.
        The end index can be negative to reference from the end of the time
        series.
        The detection point is the center of mass of the lower pass filtered
        power time series above a threshold.
        """
        # low pass filter the data
        win = np.hanning(winlen)
        win /= win.sum()
        filt_power = np.convolve(win, self.power, mode='same')
        # check the index range to look at the data
        if start < winlen / 2:
            start = int(winlen / 2)
        if stop < 0 and stop > -1 * winlen / 2:
            stop = -1 * int(winlen / 2)
        elif stop >= self.numsamples:
            stop = -1 * int(winlen / 2)
        detect_idx = None
        if start >= 0 and start < self.numsamples:
            # look for the max in the low passed index
            max_idx = filt_power[start:stop].argmax() + start
            # look for the edges around the max value that are above the threshold
            temp = np.nonzero(filt_power[start:max_idx] < threshold)[0]
            if len(temp) > 0:
                lower_idx = temp[-1] + start
            else:
                lower_idx = 0
            higher_idx = np.nonzero(filt_power[max_idx:stop] < threshold)[0][0] + max_idx
            # remove the weight below the threshold so center of mass is in the right place
            mass = (filt_power[lower_idx:higher_idx] - threshold).sum()
            test = 0
            detect_idx = lower_idx
            while test < mass / 2:
                test += filt_power[detect_idx] - threshold
                detect_idx += 1
            if detect_idx >= 1:
                detect_idx -= 1
        else:
            "start index not in range."
        return detect_idx

    def phase_detect(self, amp_idx, start=0, stop=-1, dir=0):
        """
        Conducts a traditional phase detection on the current record, using an
        amplitude detection to aid in finding the phase ramp.  The direction
        to conduct the phase detection is set with 0 as the acrosstrack and
        1 for along track (corrisponding to the location in the angle array).
        """
        thresh = 60  # where should this number come from?
        first_diff = self.angle[1:, dir] - self.angle[:-1, dir]
        abs_phs = np.abs(first_diff)
        temp = np.nonzero(abs_phs[:amp_idx] >= thresh)[0]
        if len(temp) > 0:
            start_phs = temp[-1] + 1
        else:
            start_phs = 0
        stop_phs = np.nonzero(abs_phs[amp_idx:] >= thresh)[0][0] + amp_idx
        phs_idx = range(start_phs, stop_phs)
        return phs_idx

    def weber_detect(self, start=0, stop=-1, dir=0):
        """
        Conducts a phase detection without an amplitude detection by looking 
        for the phase ramp as a section of small changes in angle.  Large
        spikes in the phase difference will cause a short ramp.
        """
        phs_diff = self.angle[:, dir]
        # Look at the first difference of the phase data to find the ramp edges
        delta_phs = phs_diff[1:] - phs_diff[:-1]
        abs_delta_phs = np.abs(delta_phs)
        # note the threshold is max/3, or ~1 rad change in phase.
        threshold = 256 / 3
        # find all values above threshold
        all_idx = np.nonzero(abs_delta_phs > threshold)[0]
        # look for most continuous section
        diff_idx = (all_idx[1:] - all_idx[:-1]).argmax()
        start_phs = all_idx[diff_idx]
        stop_phs = all_idx[diff_idx + 1]
        phs_idx = range(start_phs, stop_phs)
        return phs_idx

    def plot_timeseries(self, start_detects=-1):
        """
        Plots the amplitude and phase data time series.  If a value is supplied
        above zero it is used to set the start range for bottom detections and
        they are plotted as well.
        """
        fig = plt.figure()
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312, sharex=ax1)
        ax3 = fig.add_subplot(313, sharex=ax1, sharey=ax2)
        ax1.plot(self.power)
        ax2.plot(self.angle[:, 0])
        ax3.plot(self.angle[:, 1])
        ax1.set_ylabel('Amplitude')
        ax2.set_ylabel('Phase Along Track')
        ax3.set_ylabel('Phase Across Track')
        ax3.set_xlabel('Sample Number')
        if start_detects >= 0:
            idx = self.bottom_detect_idx(start=start_detects)
            ax1.plot(idx, self.power[idx])
            ax2.plot(idx, self.angle[idx, 0])
            ax3.plot(idx, self.angle[idx, 1])
        plt.draw()

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n, name in enumerate(self.header.dtype.names):
            print(f'{name} : {self.header[n]}')


class Raw1:
    """
    The sample datagram for SX90. Example could be from Lars Anderson circa 
    20081119.
    """
    hdr_dtype = np.dtype([
        ('channel', 'h'),
        ('datatype', 'b'),
        ('ncomplexpersample', 'b'),
        ('gaintx', 'f'),
        ('frequency', 'f'),
        ('transmitpower', 'f'),
        ('pulselength', 'f'),
        ('bandwidth', 'f'),
        ('sampleinterval', 'f'),
        ('soundvelocity', 'f'),
        ('absorptioncoefficient', 'f'),
        ('heave', 'f'),
        ('roll', 'f'),
        ('pitch', 'f'),
        ('temperature', 'f'),
        ('heading', 'f'),
        ('transmitmode', 'h'),
        ('pulseform', 'h'),
        ('dirx', 'f'),
        ('diry', 'f'),
        ('dirz', 'f'),
        ('gainrx', 'f'),
        ('sacorrection', 'f'),
        ('equivalentbeamangle', 'f'),
        ('beamwidthalongshiprx', 'f'),
        ('beamwidthathwartshiprx', 'f'),
        ('anglesensitivityalongship', 'f'),
        ('anglesensitivityathwartship', 'f'),
        ('angleoffsetalongship', 'f'),
        ('angleoffsetathwartship', 'f'),
        ('spare', 'S2'),
        ('noisefilter', 'h'),
        ('beamwidthmode', 'h'),
        ('beammode', 'h'),
        ('beamwidthhorizontaltx', 'f'),
        ('beamwidthverticaltx', 'f'),
        ('offset', 'i'),
        ('count', 'i')])

    def __init__(self, datablock, utctime):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Raw1.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=Raw1.hdr_dtype)[0]
        self.time = utctime

        if self.header['datatype'] >> 3 == 1:
            '''
            From Lars:
            sdata = fread(fid,[2*sampledata.ncomplexpersample,sampledata.count],'float32');
            sdata = reshape(sdata,[2 sampledata.ncomplexpersample sampledata.count]);
            trx32multiratefilterdelay = 16; %samples
            sdata = sdata(:,:,trx32multiratefilterdelay:end);
            sampledata.count = size(sdata,3);
            sampledata.data = squeeze(complex(sdata(1,:,:),sdata(2,:,:)));
            sampledata.power = 10*log10(squeeze(sum((sum(sdata,2)).^2)));
            '''
            # 'ncomplexpersample' is always 1, so ignoring it for simplicity
            self.sdata = np.frombuffer(datablock[hdr_sz:], 'c8')
            trx32multiratefilterdelay = 16
            self.data = self.sdata[trx32multiratefilterdelay:]
            # I think this is equivalent to the above...
            self.power = 10 * np.log10((np.square(np.abs(self.data))))
        else:
            print('raw datatype not understood')
            self.sdata = None
            self.data = None
            self.power = None

    def plot(self):
        """
        Plot the power data.
        """
        plt.figure()
        plt.plot(self.power)
        plt.xlabel('Sample Number')
        plt.ylabel('Power')
        plt.title('RAW1 datagram for channel ' + str(self.header['channel']))
        plt.grid()

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n, name in enumerate(self.header.dtype.names):
            print(f'{name} : {self.header[n]}')


class Raw3:
    """
    Raw EK80 sample read.  This was translated from Matlab code from Lars
    Andersen.
    """
    hdr_dtype = np.dtype([
        ('ChannelID', 'U128'),
        ('Mode_Low', 'B'),
        ('Mode_High', 'B'),
        ('Spare', 'S2'),
        ('Offset', 'I'),
        ('Count', 'I')])

    def __init__(self, datablock, utctime):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([
            ('ChannelID', 'S128'),
            ('Mode_Low', 'B'),
            ('Mode_High', 'B'),
            ('Spare', 'S2'),
            ('Offset', 'I'),
            ('Count', 'I')])
        hdr_sz = hdr_dtype.itemsize
        tmp = np.frombuffer(datablock[:hdr_sz],
                            dtype=hdr_dtype)[0]
        self.header = tmp.astype(Raw3.hdr_dtype)
        self.time = utctime

        self.numsamples = self.header['Count'] - self.header['Offset']
        pointer = hdr_sz
        self.power = None
        self.angle = None
        self.complexsamples = None
        # Read the samples
        if self.header['Mode_Low'] < 4:
            npointer = pointer + 2 * self.numsamples
            power = np.frombuffer(datablock[pointer: npointer], dtype='H')
            self.power = power * 10 * np.log10(2) / 256
            pointer = npointer
            if self.header['Mode_Low'] == 3:
                angle_dtype = np.dtype([('Alongship', 'B'), ('Athwartship', 'B')])
                npointer = pointer + 2 * self.numsamples
                self.angle = np.frombuffer(datablock[pointer: npointer], dtype=angle_dtype)
        elif self.header['Mode_Low'] == 8:
            ncomplex = self.header['Mode_High']  # of 2x4-byte Re+Im pairs/samp
            npointer = 8 * ncomplex * self.numsamples + pointer
            self.complexsamples = np.frombuffer(datablock[pointer:npointer], dtype='complex64')
            self.complexsamples.shape = (-1, ncomplex)
        else:
            raise ValueError(f'raw: RAW3 datagram found with unknown mode - ModeLow:{self.header["Mode_Low"]}, ModeHigh:{self.header["Mode_High"]}')

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n, name in enumerate(self.header.dtype.names):
            print(f'{name} : {self.header[n]}')


class Tag0:
    """
    The annotation datagram.
    """

    def __init__(self, datablock, utctime):
        textlen = len(datablock)
        tmp = np.frombuffer(datablock, dtype='S' + str(textlen))[0]
        self.string = tmp.astype('str')
        self.time = utctime

    def display(self):
        """print the annotation string."""
        print(f'{self.string}')


class Xml0:
    """
    The XML datagram.
    """

    def __init__(self, datablock, utctime):
        self.xmldata = {}
        self.serial_numbers = []
        self.time = utctime

        lastidx = datablock.find('>'.encode(), -4)
        if lastidx == -1:
            lastidx = None
        else:
            lastidx += 1
        root = et.fromstring(datablock[:lastidx])
        self.header = root.tag
        if root.tag == 'Configuration':
            self.configuration = root
            self.type = root.tag
        elif root.tag == 'Environment':
            self.environment = root
            self.type = root.tag
        elif root.tag == 'Parameter':
            if len(list(root)) == 1 and root[0].tag == 'Channel':
                self.header = root[0].attrib
                self.type = root[0].tag
            else:
                self.parameter = root
        else:
            self.type = root.tag
            self.unknown = root
        self._get_xml_data(root)
        if root.tag == 'Configuration':
            self._iparams = self.xmldata.copy()

    def _build_settings_dtype(self, record):
        """
        Build a numpy datatype based on the information in the provided
        datatype.
        """
        keys = ['Time', 'ChannelIndex']
        keys.extend(record.keys())
        idx = keys.index('ChannelID')
        keys.pop(idx)
        dtypes = []
        for n in range(len(keys)):
            dtypes.append('f')
        dtypes[0] = 'd'
        dtypes[1] = 'B'
        final = list(zip(keys, dtypes))
        return final

    @property
    def installation_parameters(self):
        if self.type == 'Configuration':
            tsets = self.return_transducer_metadata()
            isets = {'sonar_model_number': 'EK80', 'transducer_1_vertical_location': '0.000',
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
                     'tx_serial_number': self._iparams['TransducerSerialNumber0'], 'tx_2_serial_number': '0',
                     'active_position_system_number': '1', 'active_heading_sensor': 'motion_1', 'position_1_datum': 'WGS84'}
            isets.update(tsets)
            isets['ektransducer_names'] = self.return_transceiver_names()
            return isets
        else:
            return None

    def _search_xml_recs(self, root):
        if root.attrib:
            data = root.attrib
        else:
            data = {}
        if list(root):
            for cnt, childrec in enumerate(root):
                newdata = self._search_xml_recs(childrec)
                for transrec in ['TransducerName', 'TransducerCustomName', 'TransducerSerialNumber']:
                    if transrec in newdata:
                        newdata[transrec + str(cnt)] = newdata.pop(transrec)
                data.update(self._search_xml_recs(childrec))
        else:
            data = root.attrib
        return data

    def _get_xml_data(self, root):
        self.xmldata = self._search_xml_recs(root)

    def return_transceiver_names(self):
        tnames = []
        if self.configuration:
            transceivers_element = [x for x in self.configuration if x.tag == 'Transceivers']
            if transceivers_element:
                transceivers_element = transceivers_element[0]
                for tceiver in transceivers_element:
                    channels_element = tceiver[0]
                    for n, t in enumerate(channels_element):  # , resp: <Element 'Tranceivers'><Element 'Transceiver'><Element 'Channels'>
                        name = t.attrib['ChannelID']
                        tnames.append(name)
            else:
                raise ValueError('raw: XML0 configuration record, unable to find "Transceivers" xml tagged element')
        return tnames

    def return_transducer_metadata(self):
        transsets = {}
        if self.configuration:
            transceivers_element = [x for x in self.configuration if x.tag == 'Transceivers']
            if transceivers_element:
                transceivers_element = transceivers_element[0]
                for cnt, tceiver in enumerate(transceivers_element):
                    for ky, val in tceiver.attrib.items():
                        if isinstance(val, np.ndarray):
                            val = val.tolist()
                        transsets[f'ektransducer{cnt}_{ky}'] = val
        return transsets

    def display(self):
        """print the XML data."""
        print(f'{self.header}')


class Nme0:
    """The NMEA datagram."""

    def __init__(self, datablock, utctime):
        nmealen = len(datablock)
        tmp = np.frombuffer(datablock, dtype='S' + str(nmealen))[0]
        self.string = tmp.astype('str')
        self.string = self.string.split(',')
        self.time = utctime

        try:
            self.rectype = self.string[0][-3:].lstrip('$')
        except:
            self.rectype = 'Unknown'

        if self.rectype != 'Unknown':
            try:
                readmethod = getattr(self, '_' + self.rectype)
            except:  # we don't bother supporting all the NMEA messages, just decode the ones that we care about
                readmethod = None
            if readmethod:
                try:
                    self.header = readmethod()
                except:
                    # print(f'raw: Malformed {self.string[0]} found: {self.string}')
                    self.header = None
            else:
                self.header = None
        else:
            self.header = None

    def display(self):
        """Prints the NMEA string"""
        for entry in self.string:
            print(f'{entry}')

    def _ALR(self):  # Alarm state
        return {'type': 'ALR', 'ack_state': self.string[3], 'condition': self.string[4]}

    def _DTM(self):  # Datum reference
        dtm = {}
        dtm['type'] = 'DTM'
        dtm['code'] = self.string[1]
        dtm['subcode'] = self.string[2]
        dtm['latitude_offset'] = self.string[3]
        dtm['latitude_hemi'] = self.string[4]
        dtm['longitude_offset'] = self.string[5]
        dtm['longitude_hemi'] = self.string[6]
        dtm['altitude_offset'] = self.string[7]
        dtm['datum_name'] = self.string[8]
        return dtm

    def _GGA(self):  # Global positioning system fix data
        gga = {}
        gga['type'] = 'GGA'
        gga['daysec'] = (int(self.string[1][:2]) * 3600. +
                         int(self.string[1][2:4]) * 60. + float(self.string[1][4:]))
        gga['lat'] = int(self.string[2][:2]) + float(self.string[2][2:]) / 60
        if self.string[3] == 'S':
            gga['lat'] *= -1
        gga['lon'] = int(self.string[4][:3]) + float(self.string[4][3:]) / 60
        if self.string[5] == 'W':
            gga['lon'] *= -1
        gga['altitude'] = str(self.string[9])
        return gga

    def _GLL(self):  # Geographic Position
        gll = {}
        gll['type'] = 'GLL'
        gll['lat'] = int(self.string[1][:2]) + float(self.string[1][2:]) / 60
        if self.string[2] == 'S':
            gll['lat'] *= -1
        gll['lon'] = int(self.string[3][:3]) + float(self.string[3][3:]) / 60
        if self.string[4] == 'W':
            gll['lon'] *= -1
        gll['utc_time'] = f'{self.string[5][:2]}:{self.string[5][2:4]}:{self.string[5][4:]}'
        return gll

    def _HDT(self):  # Heading
        hdt = {}
        hdt['type'] = 'HDT'
        hdt['heading'] = float(self.string[1])
        return hdt

    def _SHR(self):  # Novatel inertial attitude data ($PASHR)
        pashr = {}
        pashr['type'] = 'PASHR'
        pashr['daysec'] = (int(self.string[1][:2]) * 3600. +
                           int(self.string[1][2:4]) * 60. + float(self.string[1][4:]))
        pashr['heading'] = float(self.string[2])
        pashr['roll'] = float(self.string[4])
        pashr['pitch'] = float(self.string[5])
        pashr['heave'] = float(self.string[6])
        return pashr

    def _RMC(self):  # recommended minimum navigation information
        rmc = {}
        rmc['type'] = 'RMC'
        rmc['utc_time'] = f'{self.string[1][:2]}:{self.string[1][2:4]}:{self.string[1][4:]}'
        rmc['status'] = 'Valid' if self.string[2] == 'A' else 'Warning'
        rmc['lat'] = int(self.string[3][:2]) + float(self.string[3][2:]) / 60
        if self.string[4] == 'S':
            rmc['lat'] *= -1
        rmc['lon'] = int(self.string[5][:3]) + float(self.string[5][3:]) / 60
        if self.string[6] == 'W':
            rmc['lon'] *= -1
        rmc['speed'] = float(self.string[7])
        rmc['course_made_good'] = float(self.string[8])
        rmc['date'] = f'{self.string[9][:2]}_{self.string[9][2:4]}_{self.string[9][4:6]}'
        return rmc

    def _VLW(self):  # distance travelled through the water
        vlw = {}
        vlw['type'] = 'VLW'
        vlw['total_distance'] = self.string[1]
        vlw['total_distance_type'] = self.string[2]
        vlw['distance_since_reset'] = self.string[3]
        vlw['distance_since_reset_type'] = self.string[4]
        return vlw

    def _ZDA(self):  # Time and date
        zda = {}
        zda['type'] = 'ZDA'
        zda['time'] = self.string[1]
        zda['day'] = self.string[2]
        zda['month'] = self.string[3]
        zda['year'] = self.string[4]
        hour = int(zda['time'][:2])
        minute = int(zda['time'][2:4])
        seconds = float(zda['time'][4:])
        dayseconds = hour * 3600 + minute * 60 + seconds
        # zda['posix'] = basetime(zda['year'],zda['month'],zda['day'], type = 1) + dayseconds
        return zda


class mappack:
    """
    Container for the file packet map.
    """

    def __init__(self):
        """Constructor creates a packmap dictionary"""
        self.packdir = {}

    def add(self, type, location=0, time=0, optional=None):
        """Adds the location (byte in file) to the tuple for the value type"""
        if type not in self.packdir:
            self.packdir[type] = []
        if optional is None:
            self.packdir[type].append([location, time])
        else:
            self.packdir[type].append([location, time, optional])

    def finalize(self):
        for key in self.packdir.keys():
            temp = np.asarray(self.packdir[key])
            tempindx = temp[:, 1].argsort()
            self.packdir[key] = temp[tempindx, :]

    def printmap(self):
        fmap = []
        for key in self.packdir:
            fmap.append((key, len(self.packdir[key])))
        fmap.sort()
        for entry in fmap:
            print(f'{entry[0]} has {entry[1]} packets')

    def save(self, outfilename):
        outfile = open(outfilename, 'wb')
        pickle.dump(self.packdir, outfile)
        outfile.close()

    def getnum(self, recordtype):
        """
        Returns the number of records of the provided record type.
        """
        if recordtype in self.packdir:
            return len(self.packdir[recordtype])
        else:
            return 0

    def load(self, infilename):
        infile = open(infilename, 'rb')
        self.packdir = pickle.load(infile)
        infile.close()


class useraw(readraw):
    """
    This is a subclass of Readraw, so inherits all the reading functions.
    Additional methods for plotting and manipulating data are added.  Upon
    initialization the file is mapped and the configuration datagram is read
    and saved as a class variable.
    """

    def __init__(self, infilename):
        readraw.__init__(self, infilename)
        self.mapfile()
        if 'CON0' in self.map.packdir:
            self.getrecord('CON0', 0)
            self.configuration = self.packet.subpack.transducers
        if 'XML0' in self.map.packdir:
            c = self.getrecord('XML0', 0)
            self.transducer_names = []
            if c.configuration:
                self.transducer_names = c.return_transceiver_names()
            self.build_xml_info()
        self.reset()

    def mapfile(self, verbose=False):
        """
        Maps the datagrams in the file, but separates the transducers (or beams
        in the case of the ME70) and the NMEA datagrams into separate listings
        in the resulting file map.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack()
            self.reset()
            print('Mapping file;           ', end='')
            while not self.eof:
                loc = self.infile.tell()
                self.read()
                dtype = self.packet.header[1]
                time = self.packet.gettime()
                if dtype == 'NME0':
                    self.get()
                    dtype = self.packet.subpack.string[0][1:]
                    self.map.add(str(dtype), loc, time)
                elif dtype == 'RAW0':
                    self.get()
                    txnum = self.packet.subpack.header['Channel']
                    self.map.add(str(dtype), loc, time, optional=txnum)
                elif dtype == 'RAW1':
                    self.get()
                    txnum = self.packet.subpack.header['channel']
                    self.map.add(str(dtype), loc, time, optional=txnum)
                elif dtype == 'RAW3':
                    self.get()
                    name = self.packet.subpack.header['ChannelID']
                    self.map.add(name, loc, time)
                else:
                    self.map.add(str(dtype), loc, time)
                current = 100 * loc / self.filelen
                if current - progress >= 1 and verbose:
                    progress = current
                    sys.stdout.write(f'\b\b\b\b\b\b\b\b\b\b{progress} percent')
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            if self.error:
                print()
            else:
                print('\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.')
            if verbose:
                self.map.printmap()
            self.mapped = True
        else:
            pass

    def build_xml_info(self):
        """
        Extract the xml data into a object variables. Configuration and
        environment are named as such.  The Parameters / Channel information is
        put into a 'settings' variable with a time stamp and the channel ID.
        """
        table_dtype = None
        settings = []
        if 'XML0' in self.map.packdir:
            numxml = self.map.getnum('XML0')
            for n in range(numxml):
                x = self.getrecord('XML0', n)
                if x.type == 'Channel':
                    if table_dtype == None:
                        table_dtype = self._build_settings_dtype(x.header)
                    c = np.zeros(1, dtype=table_dtype)[0]
                    c['Time'] = self.packet.gettime()
                    tx_idx = self.transducer_names.index(x.header['ChannelID'])
                    c['ChannelIndex'] = tx_idx
                    for m in x.header.keys():
                        if m != 'ChannelID':
                            c[m] = float(x.header[m])
                    settings.append(c)
                elif x.type == 'Configuration':
                    self.configuration = x.configuration
                elif x.type == 'Environment':
                    self.environment = x.environment
            self.settings = np.asarray(settings, dtype=table_dtype)
        else:
            print('No XML datagrams found.')

    def _build_settings_dtype(self, record):
        """
        Build a numpy datatype based on the information in the provided
        datatype.
        """
        keys = ['Time', 'ChannelIndex']
        keys.extend(record.keys())
        idx = keys.index('ChannelID')
        keys.pop(idx)
        dtypes = []
        for n in range(len(keys)):
            dtypes.append('f')
        dtypes[0] = 'd'
        dtypes[1] = 'B'
        final = list(zip(keys, dtypes))
        return final

    def get_xml_settings(self, channel_name, timestamp):
        """
        Provided a time stamp and the channel number of interest, the settings
        are returned as a numpy record array.
        """
        channel_index = self.transducer_names.index(channel_name)
        idx = np.nonzero((self.settings['ChannelIndex'] == channel_index)
                         & (self.settings['Time'] < timestamp))[0]
        if len(idx) == 0:
            idx = np.nonzero((self.settings['ChannelID'] == channel_index)
                             & (self.settings['Time'] >= timestamp))[0]
            if len(idx) == 0:
                return None
            else:
                return self.settings[idx[0]]
        else:
            return self.settings[idx[-1]]

    def plot_beam_timeseries(self, txnum=1, start=0, end=-1):
        """
        Plots all pings for the given transducer.  Defaults to plotting the
        first transducer and all points.  Provide a start and end number to
        limit the number displayed.
        """
        m = np.asarray(self.map.packdir['RAW0'])
        record_idx = np.nonzero(m[:, 2] == txnum)[0]
        self.getrecord('RAW0', record_idx[0])
        numsamples = self.packet.subpack.header['Count'] - self.packet.subpack.header['Offset']
        powers = np.zeros((numsamples, len(record_idx)))
        angle = np.zeros((numsamples, len(record_idx), 2))
        if end == -1:
            end = len(record_idx)
        if start >= 0:
            if len(record_idx) >= end:
                for k, n in enumerate(range(start, end)):
                    self.getrecord('RAW0', record_idx[n])
                    powers[:, k] = self.packet.subpack.power
                    angle[:, k, 0] = self.packet.subpack.angle[:, 0]
                    angle[:, k, 1] = self.packet.subpack.angle[:, 1]
                    temp = len(self.packet.subpack.power)
        fig = plt.figure()
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312, sharex=ax1, sharey=ax1)
        ax3 = fig.add_subplot(313, sharex=ax1, sharey=ax1)
        ax1.pcolormesh(powers)
        ax2.pcolormesh(angle[:, :, 0])
        ax3.pcolormesh(angle[:, :, 1])
        ax1.set_ylim((numsamples, 0))
        ax1.set_xlim((0, len(record_idx)))

    def display_config(self, txnum):
        """
        Displays the configuration information for the transducer number
        provided.  This is relative to the index number in the configuration
        file, not the transmit order, with the index starting a zero not one.
        """
        if 'CON0' in self.map.packdir:
            for n, name in enumerate(self.configuration[txnum].dtype.names):
                print(f'{name} : {self.configuration[txnum][n]}')
        else:
            print('This function does not currently support XML configuration display.')


def basetime(year, month, day, time_type=0):
    """
    Provides the POSIX time for the beginning of the week for the date
    given. If type = 0 the GPS week is returned as the base.  If type = 1 the
    beginning of the day is the base.
    """
    ordinal = datetime.toordinal(datetime(year, month, day))
    dow = datetime.fromordinal(ordinal).weekday() + 1
    if dow == 7:
        # shift sunday to be start of week.
        dow = 0
    # 719163 is the ordinal day for 1970-1-1
    if time_type == 0:
        POSIXdays = ordinal - 719163 - dow
    elif time_type == 1:
        POSIXdays = ordinal - 719163
    base = POSIXdays * 24 * 3600
    return base


def get_saildrone_navigation(raw_file: str):
    """
    Get all the navigation found in .gps.csv files that are in the same directory as the given .raw file

    Parameters
    ----------
    raw_file
        path to a .raw file

    Returns
    -------
    np.ndarray
        1d array of utctime in seconds
    np.ndarray
        1d array of latitude in degrees
    np.ndarray
        1d array of longitude in degrees
    """

    raw_dir = os.path.dirname(raw_file)
    possible_nav_files = glob.glob(raw_dir + r'/*.gps.csv')
    utctime = []
    latitude = []
    longitude = []
    for nf in possible_nav_files:
        newtme, newlat, newlon = read_saildrone_csv(nf)
        if newtme is not None:
            utctime.append(newtme)
            latitude.append(newlat)
            longitude.append(newlon)
    if utctime:
        utctime = np.concatenate(utctime)
        latitude = np.concatenate(latitude)
        longitude = np.concatenate(longitude)
        sortidx = np.argsort(utctime)
        utctime = utctime[sortidx]
        latitude = latitude[sortidx]
        longitude = longitude[sortidx]
    else:
        print(f"raw: ERROR - Unable to find any *.gps.csv files for saildrone navigation")
    return utctime, latitude, longitude


def read_saildrone_csv(csvpath: str):
    """
    Read one of the saildrone gps.csv files, to get navigation

    Parameters
    ----------
    csvpath
        path to a .gps.csv navigation file

    Returns
    -------
    np.ndarray
        1d array of utctime in seconds
    np.ndarray
        1d array of latitude in degrees
    np.ndarray
        1d array of longitude in degrees
    """

    try:
        data = np.recfromcsv(csvpath, encoding='utf8')
    except:
        print(f"raw: ERROR - Unable to read {csvpath} as csv")
        return None, None, None
    expected_columns = ('gps_fix', 'gps_date', 'gps_time', 'latitude', 'longitude')
    try:
        assert data.dtype.names == expected_columns
    except AssertionError:
        print(f"raw: ERROR - Attempted to read {csvpath}, expected columns {expected_columns}, found {data.dtype.names}")
        return None, None, None
    utctime = []
    date_time_data = np.concatenate([data['gps_date'][:, None], data['gps_time'][:, None]], axis=1)
    for dtdat in date_time_data:
        rawdat = datetime.strptime(f'{dtdat[0]}-{dtdat[1]}', '%Y-%m-%d-%H:%M:%S')
        rawdat = rawdat.replace(tzinfo=timezone.utc)
        utctime.append(float(rawdat.timestamp()))
    return np.array(utctime), data['latitude'], data['longitude']


def _expand_class_to_zero_gradient(classified, grad):
    """
    Extend the areas of large gradients to include the return to zero gradient
    and the likely area of maximum response.

    Parameters
    ----------
    classified : TYPE
        DESCRIPTION.
    grad : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    numsamples, numpings = classified.shape
    extended = classified.copy()
    grad_diff = np.diff(grad, axis=0)
    for n in range(numpings):
        ping = classified[:, n]
        classification, idx = np.unique(ping, return_index=True)
        for m, c in enumerate(classification):
            if c == 0:
                continue
            # find where the gradient goes to zero since this is where the max value should be
            # this is one of those lines of code that I won't understand later...
            zero_rel_idx = np.argwhere(grad[idx[m]:, n] < 0)
            if len(zero_rel_idx) == 0:
                feat_end_idx = -1
            else:
                zero_idx = int(zero_rel_idx[0][0] + idx[m])
                min_rel_idx = np.argwhere(grad_diff[zero_idx:, n] > 0)
                if len(min_rel_idx) == 0:
                    feat_end_idx = -1
                else:
                    feat_end_idx = int(min_rel_idx[0][0] + zero_idx)
            extended[idx[m]:feat_end_idx, n] = c
    return extended


def _get_detections_within_classes(classified, powers, grad):
    """
    Get the detections within each class for each ping.

    Parameters
    ----------
    expanded_class : TYPE
        DESCRIPTION.
    powers : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    numsamples, numpings = classified.shape
    detect_class = np.full_like(classified, 0)
    detect_powers = np.full(classified.shape, np.nan)
    detect_noise = np.full(classified.shape, np.nan)
    for n in range(numpings):
        class_ping = classified[:,n]
        power_ping = powers[:,n]
        classification= np.unique(class_ping)
        post_tx_idx = np.argwhere(grad[:,n] > 0)[0][0]
        for m,c in enumerate(classification):
            if c == 0:
                continue
            class_idx = np.argwhere(class_ping == c)
            rel_idx = np.argmax(power_ping[class_idx])
            detect_idx = class_idx[rel_idx][0]
            detect_class[detect_idx, n] = c
            detect_powers[detect_idx, n] = powers[detect_idx, n]
            detect_noise[detect_idx, n] = np.mean(power_ping[post_tx_idx:detect_idx])
    classification= np.unique(classified)
    class_sums = np.zeros((len(classification),3))
    class_sums[0,:] = np.nan
    class_idx = np.arange(1, len(classification))
    for n in class_idx:
        idx = np.where(detect_class == n)
        sig = detect_powers[idx]
        noise = detect_noise[idx]
        total = np.sum(10**(sig/10))
        class_sums[n,0] = len(sig)
        class_sums[n,1] = 10 * np.log10(total)
        class_sums[n,2] = np.mean(sig - noise)
    return detect_class, class_sums


def _select_class_detections(detects, class_sums, threshold):
    """
    Using the classified detections within the provided array and the number of
    points, sum power for all points in the class, and the average signal to
    noise for the class, determine the best seafloor.

    Parameters
    ----------
    detects : TYPE
        DESCRIPTION.
    class_sums : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    numsamples, numpings = detects.shape
    detect_idx = np.full(numpings, -1)
    # look for the strongest signal classes first
    sorted_class_idx = np.argsort(class_sums[:,1])[::-1]
    dcols = set()
    for idx in sorted_class_idx:
        if idx == 0:
            continue
        if class_sums[idx,2] < threshold:
            continue
        class_detect_idx = np.argwhere(detects == idx)
        scols = set(class_detect_idx[:,1])
        overlap = scols.intersection(dcols)
        # test for no overlap between classes
        if len(overlap) == 0:
            dcols = dcols.union(scols)
            detect_idx[class_detect_idx[:,1]] = class_detect_idx[:,0]
    return detect_idx


def _image_detection(powers, threshold: int = 30):
    """
    Perform a bottom detection by finding the maximum value per ping after
    applying  gausian and sobel filters.

    Parameters
    ----------
    powers : TYPE
        DESCRIPTION.
    blankidx : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    numsamples, numpings = powers.shape
    # use image edge detection to find the approximate seafloor
    im = ndimage.gaussian_filter(powers, 8)
    grad = ndimage.sobel(im, axis = 0, mode = 'constant')
    grad_threshold = grad[1:-1,:].std()
    # turn the positive gradient image into binary
    bgrad = np.full(grad.shape, False)
    bgrad[grad > grad_threshold] = True
    bgrad[[0,-1], :] = False # remove edge artifacts from the sobel filter
    # classify the gradient results
    numclass, classified = cv2.connectedComponents(bgrad.astype(np.uint8), connectivity = 8)
    expanded_class = _expand_class_to_zero_gradient(classified, grad)
    # get the max value within each ping for each class
    detects, class_sums = _get_detections_within_classes(expanded_class, powers,grad)
    detect_idx = _select_class_detections(detects, class_sums, threshold)
    return detect_idx


def calculate_heave_correction(ping_times: np.ndarray, traveltime: np.ndarray, soundspeed: np.ndarray,
                               fsampling: float = 1.0, fcutoff: float = 0.05):
    """
    Get the heave correction.

    butterworth low-pass filter to remove vessel heave and high-frequency artifacts from bathymetry fsampling Hz; must
    also interpolate bathymetry time series to same [fixed] rate fcutoff second periods [Hz]
    """

    calc_range = traveltime * (soundspeed / 2)

    fbutter = fcutoff / (fsampling / 2.)
    b, a = signal.butter(5, fbutter)

    clean_idx = ~np.isnan(traveltime)
    ping_times = ping_times[clean_idx]
    calc_range = calc_range[clean_idx]  # using the final detection as the reference bathtymetry

    pingTimes1Hz = np.arange(ping_times[0], ping_times[-1] + fsampling, fsampling)
    bottomDetections1Hz = np.interp(pingTimes1Hz, ping_times, calc_range)
    bottomDetections1Hz_LowPass = signal.filtfilt(b, a, bottomDetections1Hz)
    heave1Hz = bottomDetections1Hz - bottomDetections1Hz_LowPass
    clean_heave = np.interp(ping_times, pingTimes1Hz, heave1Hz)
    heave = np.full(len(clean_idx), np.nan)
    heave[clean_idx] = clean_heave[:]
    return ping_times, heave