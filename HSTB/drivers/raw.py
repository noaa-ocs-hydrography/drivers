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

import sys
import pickle
import xml.etree.ElementTree as et
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings

plt.ion()


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

    def fast_read_start_end_time(self):
        """
        Get the start and end time for the dataset without mapping the file first

        Returns
        -------
        list, [starttime: float, first time stamp in data, endtime: float, last time stamp in data]

        """

        starttime = None
        endtime = None
        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        startptr = self.start_ptr
        cureof = self.eof

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

        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        self.eof = cureof
        self.start_ptr = startptr
        return [starttime, endtime]

    def fast_read_serial_number(self):
        """
        Get the serial numbers and model number of the provided file without mapping the file first.

        Returns
        -------
        list, [serialnumber: int, secondaryserialnumber: int, sonarmodelnumber: str]

        """

        cur_startstatus = self.at_right_byte  # after running, we reset the pointer and start byte status
        curptr = self.infile.tell()
        startptr = self.start_ptr
        cureof = self.eof

        self.infile.seek(0)
        self.eof = False

        self.read()
        datagram_type = str(self.packet.dtype)
        if datagram_type in 'CON0':
            self.get()
            sonarmodel = 'EK60'
            serialnumber = int(self.packet.subpack.serial_numbers[0])  # get the lowest freq serial number as the identifier
        elif datagram_type in 'XML0':
            self.get()
            sonarmodel = 'EK80'
            serialnumber = 0
            # if this is a config XML0 (which it always should be I think) it will have the installation parameters
            if self.packet.subpack.installation_parameters:
                serialnumber = int(self.packet.subpack.installation_parameters['TransducerSerialNumber0'])
            else:
                # try looking through the first few records
                for i in range(100):
                    self.read()
                    if self.packet.dtype == 'XML0':
                        self.get()
                        if self.packet.subpack.installation_parameters:
                            serialnumber = int(self.packet.subpack.installation_parameters['TransducerSerialNumber0'])
                            break
                if not serialnumber:
                    print(f'raw: WARNING - unable to find the XML0 Configuration record at the beginning of this file: {self.infilename}')
        else:
            raise ValueError(f'raw: Unable to find first configuration record, looked for CON0 and XML0, got {datagram_type}')

        self.infile.seek(curptr)
        self.at_right_byte = cur_startstatus
        self.eof = cureof
        self.start_ptr = startptr
        return [serialnumber, 0, sonarmodel]


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
            self.subpack = Con0(self.datablock)
        elif self.dtype == 'CON1':
            self.subpack = Con1(self.datablock)
        elif self.dtype == 'RAW0':
            self.subpack = Raw0(self.datablock)
        elif self.dtype == 'RAW1':
            self.subpack = Raw1(self.datablock)
        elif self.dtype == 'RAW3':
            self.subpack = Raw3(self.datablock)
        elif self.dtype == 'NME0':
            self.subpack = Nme0(self.datablock)
        elif self.dtype == 'TAG0':
            self.subpack = Tag0(self.datablock)
        elif self.dtype == 'XML0':
            self.subpack = Xml0(self.datablock)
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

    def __init__(self, datablock):
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


class Con1:
    """
    The ME70 configuration datagram.
    """

    def __init__(self, datablock):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        self.data = datablock

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

    def __init__(self, datablock):
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

    def __init__(self, datablock):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Raw1.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz],
                                    dtype=Raw1.hdr_dtype)[0]
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

    def __init__(self, datablock):
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
        self.numsamples = self.header['Count'] - self.header['Offset']
        pointer = hdr_sz
        # Read the samples
        if self.header['Mode_Low'] < 4:
            npointer = pointer + 2 * self.numsamples
            power = np.frombuffer(datablock[pointer: npointer], dtype='H')
            self.power = power * 10 * np.log10(2) / 256
            pointer = npointer
            if self.header['Mode_Low'] == 3:
                angle_dtype = np.dtype(['Alongship', 'B'], ['Athwartship', 'B'])
                npointer = pointer + 2 * self.numsamples
                self.angle = np.frombuffer(datablock[pointer: npointer],
                                           dtype=angle_dtype)
        elif self.header['Mode_Low'] == 8:
            ncomplex = self.header['Mode_High']  # of 2x4-byte Re+Im pairs/samp
            npointer = 8 * ncomplex * self.numsamples + pointer
            self.complexsamples = np.frombuffer(datablock[pointer:npointer],
                                                dtype='complex64')
            self.complexsamples.shape = (-1, ncomplex)
        else:
            print('Unknown Sample Mode')

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

    def __init__(self, datablock):
        textlen = len(datablock)
        tmp = np.frombuffer(datablock, dtype='S' + str(textlen))[0]
        self.string = tmp.astype('str')

    def display(self):
        """print the annotation string."""
        print(f'{self.string}')


class Xml0:
    """
    The XML datagram.
    """

    def __init__(self, datablock):
        self.xmldata = {}
        self.installation_parameters = {}
        self.serial_numbers = []
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
            self.unknown = root
        self._get_xml_data(root)
        if root.tag == 'Configuration':
            self.installation_parameters = self.xmldata.copy()

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

    def display(self):
        """print the XML data."""
        print(f'{self.header}')


class Nme0:
    """The NMEA datagram."""

    def __init__(self, datablock):
        nmealen = len(datablock)
        tmp = np.frombuffer(datablock, dtype='S' + str(nmealen))[0]
        self.string = tmp.astype('str')
        self.string = self.string.split(',')
        try:
            if self.string[0][-3:] == 'GGA':
                self.header = self._GGA()
            elif self.string[0][-3:] == 'HDT':
                self.header = self._HDT()
            elif self.string[0] == '$PASHR':
                self.header = self._PASHR()
            elif self.string[0][-3:] == 'ZDA':
                self.header = self._ZDA()
        except:
            msg = f'Malformed {self.string[0]} found.'
            warnings.warn(msg)
            self.header = None

    def display(self):
        """Prints the NMEA string"""
        for entry in self.string:
            print(f'{entry}')

    def _GGA(self):
        gga = {}
        gga['type'] = self.string[0]
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

    def _HDT(self):
        hdt = {}
        hdt['type'] = self.string[0]
        hdt['heading'] = float(self.string[1])
        return hdt

    def _PASHR(self):
        pashr = {}
        pashr['type'] = self.string[0]
        pashr['daysec'] = (int(self.string[1][:2]) * 3600. +
                           int(self.string[1][2:4]) * 60. + float(self.string[1][4:]))
        pashr['heading'] = float(self.string[2])
        pashr['roll'] = float(self.string[4])
        pashr['pitch'] = float(self.string[5])
        pashr['heave'] = float(self.string[6])
        return pashr

    def _ZDA(self):
        zda = {}
        zda['type'] = self.string[0]
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
            for n, t in enumerate(c.configuration[1][0][0]):  # , resp: <Element 'Tranceivers'><Element 'Transceiver'><Element 'Channels'>
                name = t.attrib['ChannelID']
                self.transducer_names.append(name)
                # newname = n
                # self.map.packdir[newname] = self.map.packdir.pop(name)
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
