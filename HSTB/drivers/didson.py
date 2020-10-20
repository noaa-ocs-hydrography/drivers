# -*- coding: utf-8 -*-
"""
didson.py

G.Rice 20170315
V 0.0.2 20170517

A reader for Didson data records.

The format for these records was largely taken from provided matlab code since
the provided data definition (PDF) was found to be hard to follow or incorrect.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
plt.ion()
import imageio


class open_didson:
    """
    A class for handing Didson data files.
    """
    def __init__(self, infilename):
        """
        Open the file and return a handle.
        """
        self.infilename = infilename
        self.infile = open(infilename, 'rb')
        self.eof = False
        self.error = False
        finfo = np.fromfile(self.infile, 'S3,b', count = 1)[0]
        self.version = finfo[0] + str(finfo[1])
        self.infile.seek(0,2)
        self.filelen = self.infile.tell()
        self.infile.seek(0)
        if self.version == 'DDF4':
            self.header = Master_Header4(self.infile.read(1024))
            numbeams = self.header['NumRawBeams']
            samples  = self.header['SamplesPerChannel']
            self._recordlen = 1024 + numbeams * samples
            self.angles = np.linspace(-14.5, 14.5, num = numbeams)
        else:
            print "File version not recognized: " + self.version
        
    def close(self):
        self.infile.close()
        
    def read(self):
        """
        Reads the data record.
        """
        if self.infile.tell() == self.filelen:
                self.eof = True
        if not self.eof:
            if self.filelen >= self.infile.tell() + self._recordlen:
                datablock = self.infile.read(self._recordlen)
                self.packet = Record(datablock, self.header, self.angles)
            else:
                self.eof = True
                self.error = True
                print "Broken packet found at", self.infile.tell()
            
    def getrecord(self, recordnum):
        """
        Gets the record number of the described record type.
        """
        if recordnum <= self.header['FrameTotal']:
            fh_len = self.header.itemsize
            record_position = fh_len + self._recordlen * recordnum
            self.infile.seek(record_position)
            self.read()
            return self.packet
        else:
            print "Record number exceeds number of records in file."
            return None
        
    def get_filtered(self, recordnum, filter_len = 50):
        """
        Gets a series of records and runs an highpass filter to remove the
        background noise and look for transient features.  A record object for
        the requested record number is returned, but the data has been replaced
        by the filtered version.
        
        If the requested record is less than 1/2 the filter length closer to
        the beginning or end of the file, the filter will be not be centered on
        the requested record.
        """
        if recordnum < 0:
            recordnum += self.header['FrameTotal']
        #set the filter number fo the records
        filt_len = int(filter_len)
        filt_start = recordnum - filt_len / 2
        filt_end = recordnum + filt_len - filt_len / 2
        shift = 0
        if filt_start < 0:
            shift  = abs(filt_start)
        elif filt_end > self.header['FrameTotal']:
            shift = self.header['FrameTotal'] - filt_end
        filt_start += shift
        filt_end += shift
        rec_rng = np.arange(filt_start,filt_end)
        # get the data
        raw_data = np.zeros((self.header['SamplesPerChannel'],
                            self.header['NumRawBeams'],
                            filt_len), dtype = np.uint8)
        for m,n in enumerate(rec_rng):
            temp = self.getrecord(n)
            if temp is not None:
                raw_data[:,:,m] = temp.data
                if n == recordnum:
                    prim = temp
        bg = raw_data.mean(axis = 2)
        hp = prim.data - bg
        prim.data = hp
        return prim
        
    def display_file_info(self):
        """
        Prints the file header.
        """
        for n,name in enumerate(self.header.dtype.names):
            if name == 'RsvdData':
                pass
            else:
                print name + ' : ' + str(self.header[n])
        
    def reset(self):
        """
        Puts the file pointer to the start and the eof to False.
        """
        self.infile.seek(0)
        self.eof = False
        if self.__dict__.has_key('packet'):
            del self.packet
            
def Master_Header4(datablock):
    """
    Read the file header from the provided buffer and return as numpy record 
    array.
    """
    mh_dtype = np.dtype([('Start','S3'),
                        ('Version',np.uint8),
                        ('FrameTotal',np.uint32),
                        ('FrameRate',np.uint32),
                        ('HighResolution',np.uint32),
                        ('NumRawBeams',np.uint32),
                        ('SampleRate',np.float32),
                        ('SamplesPerChannel',np.uint32),
                        ('ReceiverGain',np.uint32),
                        ('WindowStart',np.uint32),
                        ('WindowLength',np.uint32),
                        ('Reverse',np.uint32),
                        ('SN',np.uint32),
                        ('Date','S32'),
                        ('HeaderID', 'S256'),
                        ('UserID1',np.int32),
                        ('UserID2',np.int32),
                        ('UserID3',np.int32),
                        ('UserID4',np.int32),
                        ('StartFrame',np.uint32),
                        ('EndFrame',np.uint32),
                        ('TimeLapse',np.uint32),
                        ('RecordInterval',np.uint32),
                        ('RadioSeconds',np.int32),
                        ('FrameInterval',np.uint32),
                        ('Flags',np.uint32),
                        ('RsvdData', 'a644')])
    header = np.frombuffer(datablock, dtype = mh_dtype)[0]
    return header

class Record:
    """
    Read the data frame header and the data.
    """
    def __init__(self, datablock, metadata, angles):
        fh_dtype = np.dtype([('FrameNumber',np.uint32),
                             ('FrameTime',np.uint32,2),
                             ('Start','S3'),
                             ('Version',np.uint8),
                             ('Status',np.uint32),
                             ('Year',np.uint32),
                             ('Month',np.uint32),
                             ('Day',np.uint32),
                             ('Hour',np.uint32),
                             ('Minute',np.uint32),
                             ('Second',np.uint32),
                             ('Centisecond',np.uint32),
                             ('TransmitMode',np.uint32),
                             ('WindowStart',np.uint32),
                             ('WindowLength',np.uint32),
                             ('Threshold',np.uint32),
                             ('Intensity',np.uint32),
                             ('ReceiverGain', np.uint32),
                             ('PowerSupplyTemp',np.uint32),
                             ('A/DTemp',np.uint32),
                             ('Humidity',np.uint32),
                             ('Focus',np.uint32),
                             ('Battery',np.uint32),
                             ('UserValue1','S16'),
                             ('UserValue2','S8'),
                             ('PanWCom',np.float32),
                             ('TiltWCom',np.float32),
                             ('Velocity',np.float32),
                             ('Depth',np.float32),
                             ('Altitude',np.float32),
                             ('Pitch',np.float32),
                             ('PitchRate',np.float32),
                             ('Roll',np.float32),
                             ('RollRate',np.float32),
                             ('Heading',np.float32),
                             ('HeadingRate',np.float32),
                             ('SonarPan',np.float32),
                             ('SonarTilt',np.float32),
                             ('SonarRoll',np.float32),
                             ('Latitude',np.float64),
                             ('Longitude',np.float64),
                             ('SonarPosition',np.float32),
                             ('ConfigFlags',np.uint32),
                             ('RsvdData','a828')])
        self.header = np.frombuffer(datablock, dtype = fh_dtype, count = 1)[0]
        fh_len = fh_dtype.itemsize
        self.data = np.frombuffer(datablock[fh_len:], dtype = np.uint8)
        self.data.shape = (512,-1)
        self.angles = angles
        self.metadata = metadata
        
    def plot_sb(self):
        """
        Plot the data as sample vs beam.
        """
        plt.figure()
        plt.imshow(self.data, aspect = 'auto', interpolation = 'none')
        plt.title('Record Number ' + str(self.header['FrameNumber']))
        plt.xlabel('Beam Number')
        plt.ylabel('Sample Number')
        
    def plot_xy(self):
        """
        Plot the data as X vs Y.
        """
        fs = self.metadata['SampleRate']
        numsamples = self.metadata['SamplesPerChannel']
        r = 1500 * np.arange(numsamples) / fs
        R,A = np.meshgrid(r,np.deg2rad(self.angles))
        X = R * np.sin(A)
        Y = R * np.cos(A)
        plt.figure()
        plt.pcolormesh(X.T,Y.T,self.data)
        plt.title('Record Number ' + str(self.header['FrameNumber']))
        plt.xlabel('Acrosstrack (m)')
        plt.ylabel('Alongtrack (m)')
        plt.colorbar()
        
    def reproj(self):
        """
        Reproject from sample / beam to x / y and return new array.
        """
        c = int(512 * np.sin(np.deg2rad(14.5)))
        rpdata = ndimage.geometric_transform(self.data, self._cart2pol, 
                                             output_shape = (512, 2*c),
                                             extra_keywords = {'c':c})
        rpdata = np.flipud(rpdata)
        return rpdata
        
    def _cart2pol(self, output, c):
        """
        Helper function for _reproj.
        """
        x = output[0]
        y = output[1]-c
        r = np.sqrt(x**2 + y**2)
        t = np.round((np.rad2deg(np.arctan2(y,x)) + 14.5) / 0.3)
        return (r,t)
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            if name == 'Data':
                pass
            if name == 'RsvdData':
                pass
            elif name == 'ConfigFlags':
                print name + ' : ' + np.binary_repr(self.header[n])
            else:
                print name + ' : ' + str(self.header[n])
                
def make_filtered_movie(infilename, outfilename = 'test.mp4', filter_len = None):
    """
    
    """
    d = open_didson(infilename)
    numrecords = d.header['FrameTotal']
    r = d.getrecord(0)
    f = r.reproj()
    data = np.zeros((numrecords, f.shape[0], f.shape[1]))
    progress = 0
    print "processing " + str(numrecords) + " records."
    for n in range(numrecords):
        if filter_len == None:
            r = d.get_filtered(n)
        else:
            r = d.get_filtered(n, filter_len)
        f = r.reproj()
        data[n,:,:] = f
        current = 100 * n / numrecords
        if current - progress >= 1:
            progress = current
            sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
    imageio.mimwrite(outfilename, data)
    
    