"""
par.py
G.Rice 6/20/2012

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

V0.4.4 20170829
This module includes a number of different classes and methods for working with
Kongsberg all files, each of which are intended to serve at least one of three
purposes.  These are

   1) Provide access to the Kongsberg records for viewing or data extraction.
   2) Provide simplified access to a combination of Kongsberg data.
   3) Display information from Kongsberg records or data.
   
The primary classes in this module to be accessed directly are

    allRead - used to get data records or blocks of records.
    useall - inherites from allRead, but performs higher level jobs.
    resolve_file_depths - get new xyz data from the range / angle data.

Each of these classes is described in more detail with their own docstrings.
Some standalone methods that use the above classes for data access are also 
included at the end of this module.  The methods of interest are

    build_BSCorr
    plot_extinction
    noise_from_passive_wc
    
and are also described in more detail in their docstrings.
    
"""

import numpy as np
from numpy import sin, cos, pi
from numpy import fft
from matplotlib import pyplot as plt
from mpl_toolkits.basemap import pyproj
from mpl_toolkits.basemap import Basemap
import datetime as dtm
import sys, os, copy
import pickle
import re
from glob import glob
try:
    import tables as tbl
    have_tables = True
except ImportError:
    have_tables = False
try:
    import svp
    have_svp_module = True
except ImportError:
    have_svp_module = False
# suppress numpy rank warnings
import warnings
warnings.simplefilter('ignore', np.RankWarning)

plt.ion()
    
class allRead:
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
    available in file and what percetage of the file they consume.  The labels
    for these records (record number) is listed in this map and can be used as 
    a reference when working from the commandline.
    
    """
    def __init__(self, infilename, verbose = False, byteswap = False):
        """Make a instance of the allRead class."""
        self.infilename = infilename
        self.byteswap = byteswap
        self.infile = open(infilename, 'rb')
        self.mapped = False
        self.packet_read = False
        self.eof = False
        self.error = False
        self.infile.seek(0,2)
        self.filelen = self.infile.tell()
        self.infile.seek(0)
        
    def close(self, clean = False):
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
            except:
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

    def __exit__(self,*args):
        """
        Exit function for with statement
        """
        self.close()

    def read(self):
        """
        Reads the header.
        """
        if self.infile.tell() == self.filelen:
                self.eof = True
        if not self.eof:
            if self.byteswap:
                packetsize = 4 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0].newbyteorder()
            else:
                packetsize = 4 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0]
            self.infile.seek(-4, 1)
            if self.filelen >= self.infile.tell() + packetsize:
                self.packet = Datagram(self.infile.read(packetsize), self.byteswap)
                self.packet_read = True
                if not self.packet.valid:
                    self.error = True
                    print("Record without proper STX or ETX found.")
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
            except NotImplementedError as err:
                print(err.message)
            self.packet_read = False
        
    def mapfile(self, print_map = False, show_progress = False):
        """
        Maps the datagrams in the file.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack()
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
                        sys.stdout.write(
                                '\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            # set the number of watercolumn packets into the map object
            if '107' in self.map.packdir:
                pinglist = list(set(self.map.packdir['107'][:,3]))
                self.map.numwc = len(pinglist)
            if self.error:
                pass
            else:
                if show_progress:
                    print('\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.')
            if print_map:
                self.map.printmap()
            self.mapped = True
        else:
            pass

    def quickmap(self, print_map = False, record_types=[], chunkmb = 20):
        """
        quickmap(print_map**, record_types**, chunkmb)

        Search for the file for records and map their position for easy access.
        If only specific records are desired, they can be supplied as a list,
        causing only these records to exist in the file map.  If specific
        record types are not supplied then all (supported) record types are
        searched for and indexed.

        This method is a faster way to map a file then mapfile but shold
        produce the same results.

        At this time the supported em systems includes the em3002, em2040(c),
        em710, em712, em302, em304, em122, and em124.  The em model number is
        used as part of the search for records, and therefore the particular
        system needs to be supported within this module.

        *args
        -------
        None

        **kwargs
        -------
        print_map = False.  If set to True the map.printmap method is called to
            display the records available in the map.

        record_types = []. If a list of record id integers are provided, only
            these records will be indexed and added to the file map.  The
            record ids are the integer representations of the records listed in
            the Kongsberg EM data definition, or if the record is not listed
            as a integer, it is the integer representation of the hexidecimal
            id.

        chunkmb = 20.  This is the number of megabytes to read into memory for
            record searching.

        All hail the B.
        """
        # set up the em model ids
        ems = [3002, 2040, 2045, 710, 712, 302, 304, 122, 124]
        ems_hex = ['\\xba\\x0b', '\\xf8\\x07', '\\xfd\\x07', '\\xc6\\x02', '\\xc8\\x02',
                   '\\x2e\\x01', '\x30\\x01', '\\x7a\\x00', '\\x7c\\x00']
        em_set = False
        # define what to look for in the header once a record is found.
        hdr_dtype = np.dtype([('Bytes','I'),('Start','B'),('Type','B'),
                              ('Model','H'),('Date','I'),('Time','I'),
                              ('PingCount','H')])
        hdr_size = hdr_dtype.itemsize
        # set up the mapping object.
        self.map = mappack()

        # initialize the data reading process
        self.reset()  # start at beginning of file
        chunksize = chunkmb * 1024 * 1024
        data = self.infile.read(chunksize)
        next_data = self.infile.read(chunksize)
        fileoffset = 0
        search_block_pos = 0

        # Create a regular expression that wants a \x02 followed by a record type specified by the user or in the master map.dtypes key list
        compiled_expr = self._build_quickmap_regex(record_types)

        # Look for a match as long as there is enough data left in the file
        # Read the file til the end or we are close enough there can't be any real data remaining
        while len(data) > hdr_size:
            while 1:
                m = compiled_expr.search(data, search_block_pos)
                if m:  # If a record header was potentially found, then let's try to read and store the position down below
                    #  - but there is a chance this is a false positive since we are jsut looking for a two byte combo that could randomly occur
                    search_block_pos = m.start()
                    # print "not found at expected loc."
                    # print "re found block type ", ord(data[search_block_pos + 1]), "at", search_block_pos
                else:  # no potential record block was found so set the flag that we need more data
                    search_block_pos = -1
                    # print "not found at expected location, no more \x02's in chunk either"

                # this is where the record would be relative to the pattern
                str_block_pos = search_block_pos - 4
                # if we found something, do stuff with it if not too close to the end of the chunk
                if search_block_pos >= 0 and search_block_pos < len(data) - hdr_size:
                    possible_hdr = data[str_block_pos:str_block_pos + hdr_size]
                    # parse the data chunk
                    hdr = np.frombuffer(possible_hdr, dtype=hdr_dtype)[0]
                    if hdr[0] > chunksize or hdr[0] < hdr_size:  # unrealistic block sizes
                        search_block_pos += 1
                        continue  # the next record is not a legit header so I doubt this was a real record we found
                    if em_set or hdr['Type'] in ems:
                        str_file_pos = fileoffset + str_block_pos
                        # convert the time to something simple to store for now
                        tmp_time = hdr['Date'] + hdr['Time'] / 864000
                        if hdr['Type'] == 107:
                            self.map.add(str(hdr['Type']), str_file_pos, tmp_time, hdr[0], hdr[-1])
                        else:
                            self.map.add(str(hdr['Type']), str_file_pos, tmp_time, hdr[0])
                    if not em_set and hdr['Model'] in ems:
                        em_set = True
                        ems_idx = ems.index(hdr['Model'])
                        ems_str = ems_hex[ems_idx]
                        compiled_expr = self._build_quickmap_regex(record_types, ems_str)
                    search_block_pos += hdr[0]
                # Now check if the search block is too close to the end and we need more data to finish reading the header
                # OR if the expected position of the next search block is in the next data chunk
                if search_block_pos > len(data) - hdr_size:
                    if search_block_pos < len(data):  # the header is close to the end of the chunk, so store it and read more so we can process it
                        carry_over = data[search_block_pos:]
                        search_block_pos = 0
                    else:  # next record block is in the next chunk of file, set the search position to where that data is supposed to be
                        carry_over = ""
                        search_block_pos = search_block_pos - len(data)
                    break
                # if we didn't find anything, move to the next file chunk
                if search_block_pos < 0:
                    search_block_pos = 0
                    carry_over = ""
                    break

            # read the next chunk of data
            fileoffset = self.infile.tell() - len(carry_over)
            data = carry_over + next_data
            next_data = self.infile.read(chunksize)

        self.map.finalize()

    def _build_quickmap_regex(self, record_types, model=None):
        """
        Build and return the search string to find records in the file based on
        the provided records ids and the model if available. The pattern is a 
        \x02 (STX) followed by the desired record types specified by the user 
        or in the master map.dtypes key list.

        Both the compiled regular expression and a list of the record ids as
        characters is returned.
        """
        all_id_types = list(self.map.dtypes.keys())
        if not record_types:
            recordid = all_id_types
        else:
            recordid = record_types
        # Create a regular expression that wants a \x02 followed by a record type specified by the user or in the master map.dtypes key list
        rec_ids_exp = r"[\x" + r"\x".join(["%02x" % v for v in recordid]) + "]"
        search_exp = r"\x02" + rec_ids_exp
        # if we know the em system in this file, add it to the pattern
        if model is not None:
            search_exp = search_exp + model
        compiled_expr = re.compile(search_exp)
        return compiled_expr

    def loadfilemap(self, mapfilename = '', verbose = True):
        """
        Loads the packdir if the map object packdir has been saved previously.
        """
        if mapfilename == '':
            mapfilename = self.infilename + '.par'
        try:
            self.map = mappack()
            self.map.load(mapfilename)
            self.mapped = True
            if verbose:
                print('Loaded file map ' + mapfilename)
        except IOError:
            print(mapfilename + ' map file not found.')

    def savefilemap(self, verbose = True):
        """
        Saves the mappack packdir dictionary for faster operations on a file in
        the future.  The file is saved under the same name as the loaded file
        but with a 'par' extension.
        """
        if self.mapped:
            mapfilename = self.infilename + '.par'
            self.map.save(mapfilename)
            if verbose:
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
            self.mapfile(show_progress = True)
        if str(recordtype) in self.map.packdir:
            loc = int(self.map.packdir[str(recordtype)][recordnum][0])
            # deal with moving within large files
            if loc > 2147483646:
                loc -= 2e9
                self.infile.seek(2e9)
                while loc > 2147483646:
                    loc -= 2e9
                    self.infile.seek(2e9,1)
                self.infile.seek(loc,1)
            else:
                self.infile.seek(loc)
            self.read()
            self.get()
            return self.packet.subpack
        else:
            print("record " + str(recordtype) + " not available.")
            return None
            
    def findpacket(self, recordtype, verbose = False):
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
        
    def getwatercolumn(self,recordnum):
        """
        This method is designed to get a watercolumn packet by the ping number
        where ping 0 is the first in the file.  Separate records are
        reassembled for the whole ping and stored as the current subpack class
        as if it were a single record.
        """
        # dt is for looking for packets with different time stamps.
        if not self.mapped:
            self.mapfile()
        pinglist = list(set(self.map.packdir['107'][:,3]))
        pinglist.sort()
        if recordnum >= len(pinglist):
            print(str(len(pinglist)) + ' water column records available.')
            return None
        else:
            pingnum = pinglist[recordnum]
            inx = np.nonzero(self.map.packdir['107'][:,3] == pingnum)[0]
            ping = self.getrecord(107,inx[0])
            numbeams = ping.header['Total#Beams']
            recordsremaining = list(range(ping.header['#OfDatagrams']))
            recordsremaining.pop(ping.header['Datagram#']-1)
            totalsamples, subbeams = ping.ampdata.shape
            rx = np.zeros(numbeams, dtype = Data107.nrx_dtype)
            # Initialize array to NANs. Source:http://stackoverflow.com/a/1704853/1982894
            ampdata = np.empty((totalsamples, numbeams), dtype = np.float32)
            ampdata.fill(np.NAN)

            rx[:subbeams] = ping.rx
            ampdata[:,:subbeams] = ping.ampdata
            beamcount = subbeams
            if len(inx) > 1:
                for n in inx[1:]:
                    ping = self.getrecord(107, n)
                    recordnumber = recordsremaining.index(ping.header['Datagram#']-1)
                    recordsremaining.pop(recordnumber)
                    numsamples, subbeams = ping.ampdata.shape
                    if numsamples > totalsamples:
                        temp = np.empty((numsamples - totalsamples, numbeams), dtype = np.float32)
                        temp.fill(np.NAN)
                        ampdata = np.append(ampdata, temp, axis = 0)
                        totalsamples = numsamples
                    rx[beamcount:beamcount+subbeams] = ping.rx
                    ampdata[:numsamples,beamcount:beamcount+subbeams] = ping.ampdata
                    beamcount += subbeams
            if len(recordsremaining) > 0:
                print("Warning: Not all WC records have the same time stamp!")
            sortidx = np.argsort(rx['BeamPointingAngle'])
            self.packet.subpack.rx = rx[sortidx]
            self.packet.subpack.ampdata = ampdata[:,sortidx]
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
        self.infile.seek(0)
        self.packet_read = False
        self.eof = False
        if 'packet' in self.__dict__:
            del self.packet
        
    def getnav(self, tstamps, postype = 80, att_type = 65, degrees = True):
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
        # get the data to be used and reformat it for easy use
        go = True
        if str(postype) in self.navarray:
            if postype == 80:
                pos = self.navarray[str(postype)]
            elif postype == 'GGK':
                temp = self.navarray['GGK']
                len_pos = len(temp)
                pos = np.zeros((len_pos, 4))
                for m,n in enumerate(temp.dtype.names[:-1]):
                    pos[:,m] = temp[n].astype('float')
                pos[:,1:3] = pos[:,2:0:-1] # swap lat and lon
        else:
            go = False
        if str(att_type) in self.navarray:
            if att_type == 65:
                att = self.navarray[str(att_type)]
            elif att_type == 110:
                att = self.navarray[str(att_type)][:5]   
        else:
            go = False
        # find bounding times for getting all needed nav data
        if go:
            mintime = max(att[0,0], pos[0,0])
            maxtime = min(att[-1,0], pos[-1,0])
            navpts = np.zeros((numpts,8))
            # look for time stamps in the time range
            idx_range = np.nonzero((tstamps <= maxtime) & (tstamps >= mintime))[0]
            if len(idx_range) > 0:
                # for time stamps in the time range, find that nav and att
                for i in idx_range:
                    ts = tstamps[i]
                    if ts > pos[0,0] and ts < pos[-1,0]:
                        prev = np.nonzero(pos[:,0] <= ts)[0][-1]
                        temp = self._interp_points(tstamps[i], pos[prev,:], pos[prev + 1,:])
                        if len(temp) > 3:
                            navpts[i,[0,1,2,7]] = temp
                        else:
                            navpts[i,:3] = temp
                            navpts[i,7] = np.nan
                    else:
                        navpts[i,[0,1,2,7]] = np.nan
                    if ts > att[0,0] and ts < att[-1,0]:
                        prev = np.nonzero(att[:,0] <= tstamps[i])[0][-1]
                        navpts[i,3:7] = self._interp_points(tstamps[i], att[prev,:], att[prev + 1,:])[1:]
                    else:
                        navpts[i,3:7] = np.nan
            else:
                navpts += np.nan
            # convert roll(3), pitch(4) and heading(6) into radians 
            if not degrees:
                navpts[:,[3,4,6]] = np.deg2rad(navpts[:,[3,4,6]])
            return navpts
        else:
            return None
                
    def _interp_points(self, tstamp, pt1, pt2):
        """
        Performs an interpolation for the points given and returns the
        interpolated points.  The first field of each point array is assumed to
        be the time stamp, and all other values in the array are interpolated.
        """
        delta = pt2 - pt1
        result = pt1 + (tstamp - pt1[0]) * delta / delta[0]
        return result
            
    def _build_navarray(self, allrecords = False, verbose = True):
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
            p = self.getrecord(80,0)
            if verbose:
                print('creating position array')
            numpos = len(self.map.packdir['80'])
            self.navarray['80'] = np.zeros((numpos,3))
            use_ggk = False
            p.parse_raw()
            if p.source_data[0] == 'INGGK' or p.source_data[0] == 'GPGGK':
                if verbose:
                    print('creating GGK array')
                use_ggk = True
                ggk = np.dtype([('Time','d'),
                                ('Latitude','f'),
                                ('Longitude','f'),
                                ('Height','f'),
                                ('Quality','B')])
                self.navarray['GGK'] = np.zeros((numpos), dtype = ggk)
            for i in range(numpos):
                p = self.getrecord(80, i)
                if (p.header['System'] & 3) == 1:
                    self.navarray['80'][i,0] = self.packet.time
                    self.navarray['80'][i,2] = p.header[2]
                    self.navarray['80'][i,1] = p.header[3]
                    if use_ggk:
                        p.parse_raw()
                        y = 1
                        x = 1
                        if p.source_data[4] == 'S':
                            y = -1
                        if p.source_data[6] == 'W':
                            x = -1
                        self.navarray['GGK'][i]['Time'] = p._ggk_time
                        self.navarray['GGK'][i]['Latitude'] = y*p.source_data[3]
                        self.navarray['GGK'][i]['Longitude'] = x*p.source_data[5]
                        self.navarray['GGK'][i]['Height'] = p.source_data[10]
                        self.navarray['GGK'][i]['Quality'] = p.source_data[7]
        if '65' in self.map.packdir:
            if verbose:
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
            self.navarray['65'] = np.asarray(list(zip(time,roll,pitch,heave,heading)))
           
        if allrecords and '110' in self.map.packdir:
            if verbose:
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
            pav = self.getrecord(110,0)
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
            self.navarray['110'] = np.asarray(list(zip(time,roll,pitch,heave,heading,exttime,rollrate,pitchrate,yawrate,downvel)))
        if '104' in self.map.packdir:
            if verbose:
                print('creating altitude (depth) array')
            num = len(self.map.packdir['104'])
            self.navarray['104'] = np.zeros((num,2))
            for n in range(num):
                self.getrecord(104, n)
                self.navarray['104'][n,0] = self.packet.gettime()
                self.navarray['104'][n,1] = self.packet.subpack.header['Height']
                
    def save_navarray(self, verbose = True):
        """
        Creats an 'npy' file with the name of the all file that contains the
        navigation array used.
        """
        if 'navarray' not in self.__dict__:
            self._build_navarray()
        try:
            navfilename = self.infilename + '.nav'
            navfile = open(navfilename,'wb')
            pickle.dump(self.navarray, navfile)
            navfile.close()
            if verbose:
                print("Saved navarray to " + navfilename)
        except:
            pass
        
    def load_navarray(self, verbose = True):
        """
        Loads an 'npy' file with the name of the all file that contains the
        navigation array for this file name.
        """
        navfilename = self.infilename + '.nav'
        if os.path.exists(navfilename):
            try:
                # Python3 has issues with pickled objects made with Python2
                #  https://stackoverflow.com/questions/28218466/unpickling-a-python-2-object-with-python-3
                with open(navfilename,'rb') as navfile:
                    self.navarray = pickle.load(navfile)
            except UnicodeDecodeError:
                #with open(navfilename, 'rb') as navfile:
                #    self.navarray = pickle.load(navfile, encoding='latin1')
                print('par module does not support nav files generated in Python2.')
            if verbose:
                print("Loaded navarray from " + navfilename)
            navfile.close()
        else:
            print("No navarray file found.")
            
    def plot_navarray(self):
        """
        Plots the parts of the navarray.
        """
        if not hasattr(self,'navarray'):
            self._build_navarray()
        fig = plt.figure()
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax3 = fig.add_subplot(614, sharex = ax2)
        ax4 = fig.add_subplot(615, sharex = ax2)
        ax5 = fig.add_subplot(616, sharex = ax2)
        ax1.plot(self.navarray['80'][:,1],self.navarray['80'][:,2])
        ax1.set_xlabel('Longitude (Degrees)')
        ax1.set_ylabel('Latitude (Degrees)')
        ax1.grid()
        ax2.plot(self.navarray['65'][:,0],self.navarray['65'][:,4])
        ax2.set_ylabel('Heading (Degrees)')
        ax2.set_xlabel('Time (Seconds)')
        ax2.grid()
        if '104' in self.navarray:
            ax3.plot(self.navarray['104'][:,0],self.navarray['104'][:,1])
        ax3.set_ylabel('Height (Meters)')
        ax3.grid()
        ax4.plot(self.navarray['65'][:,0],self.navarray['65'][:,1])
        ax4.plot(self.navarray['65'][:,0],self.navarray['65'][:,2])
        ax4.set_ylabel('Degress')
        ax4.legend(('Roll','Pitch'))
        ax4.grid()
        ax5.plot(self.navarray['65'][:,0],self.navarray['65'][:,3])
        ax5.set_ylabel('Heave (Meters)')
        ax5.set_xlabel('Time (Seconds)')
        ax5.grid()
        ax5.set_xlim((self.navarray['65'][:,0].min(),self.navarray['65'][:,0].max()))
        plt.draw()
        
    def _build_speed_array(self):
        """
        This method builds a speed array.  First it looks for speed in the
        positon (80d) datagram.  If not available the speed is calculated from
        the position in the navarray.
        """
        self.getrecord(80,0)
        if self.packet.subpack.header['Speed'] > 655:
            if not hasattr(self, 'navarray'):
                self._build_navarray()
            numpts = len(self.navarray['80'])-1
            self.speedarray = np.zeros((numpts,2))
            self.utmzone = int((180. + self.navarray['80'][0,1]) / 6) + 1
            toutm = pyproj.Proj(proj = 'utm', zone = self.utmzone, ellps = 'WGS84')
            a,b = toutm(self.navarray['80'][:,1],self.navarray['80'][:,2])
            da = a[:-1] - a[1:]
            db = b[:-1] - b[1:]
            dt = self.navarray['80'][:-1,0] - self.navarray['80'][1:,0]
            self.speedarray[:,1] = np.abs(np.sqrt(da**2 + db**2) / dt)
            self.speedarray[:,0] = self.navarray['80'][:-1,0] + dt/2
        else:
            num80 = len(self.map.packdir['80'])
            self.speedarray = np.zeros((num80,2))
            for n in range(num80):
                self.getrecord(80, n)
                self.speedarray[n,1] = self.packet.subpack.header['Speed']
                self.speedarray[n,0] = self.packet.gettime()
                
    def getspeed(self, tstamps, time_to_average = 1):
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
            idx = np.nonzero((self.speedarray[:,0] > tstamps[n] - tta)&(self.speedarray[:,0] < tstamps[n] + tta))[0]
            if len(idx) > 0:
                speeds[n] = self.speedarray[idx,1].mean()
            else:
                dt = (self.speedarray[:-1,0] - self.speedarray[1:,0]).mean()
                if (tstamps[n] > self.speedarray[0,0] - dt) and tstamps[n] < self.speedarray[-1,0] + dt:
                    idx = np.abs(self.speedarray[:,0] - tstamps[n]).argmin()
                    speeds[n] = self.speedarray[idx,1]
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
        t = att[:,0]
        dt = (t[1:]-t[:-1]).mean()
        f = np.fft.fftfreq(len(t), d = dt)
        win = np.hanning(len(t))
        filt = np.hanning(100)
        filt /= filt.sum()
        roll_fft = np.convolve(np.fft.fft(win*att[:,1]),filt, mode = 'same')
        pitch_fft = np.convolve(np.fft.fft(win*att[:,2]),filt, mode = 'same')
        heave_fft = np.convolve(np.fft.fft(win*att[:,3]),filt, mode = 'same')
        plt.figure()
        plt.plot(f,np.log10(np.abs(roll_fft)))
        plt.plot(f,np.log10(np.abs(pitch_fft)))
        plt.plot(f,np.log10(np.abs(heave_fft)))
        plt.xlabel('Frequency (Hz)')
        plt.legend(('Roll','Pitch','Heave'))
        plt.grid()

    def _build_runtime_array(self):
        """
        This function builds an array of all the runtime parameters.
        """
        rtp = np.dtype([('Time','d'),('RuntimePacket',Data82.hdr_dtype)])
        if not self.mapped:
            self.mapfile()
        num = len(self.map.packdir['82'])
        self._runtime_array = np.zeros(num, dtype = rtp)
        for n in range(num):
            self.getrecord(82,n)
            self._runtime_array[n]['Time'] = self.packet.gettime()
            self._runtime_array[n]['RuntimePacket'] = self.packet.subpack.header
            
    def getruntime(self, time, values = []):
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
        cast_dtype = np.dtype([('Time','d'),('SSCast', np.object)])
        if not self.mapped:
            self.mapfile()
        num = len(self.map.packdir['85'])
        self._sscast_array = np.zeros(num, dtype = cast_dtype)
        for n in range(num):
            ping85 = self.getrecord(85,n)
            self._sscast_array[n]['Time'] = ping85.POSIXtime
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
        
    def _build_sss_array(self):
        """
        This function builds an array of all the surface sound speed records.
        """
        if not self.mapped:
            self.mapfile()
        numrecords = len(self.map.packdir['71'])
        s = self.getrecord(71,0)
        m = s.header['NumEntries']
        sss_dtype = s.data.dtype
        self._sss_array = np.zeros(numrecords * m, dtype = sss_dtype)
        for n in range(numrecords):
            ping71 = self.getrecord(71,n)
            self._sss_array[n*m:(n+1)*m] = ping71.data[:]
            
    def get_sss(self, time):
        """
        This method provides the surface sound speed based on what was
        measured at the the provided time stamp.  The time stamp is to be
        provided in POSIX time.
        """
        if not hasattr(self, '_sss_array'):
            self._build_sss_array()
        s = self._sss_array
        sss = np.interp(time, s['Time'], s['SoundSpeed'])
        return sss
    
    def plot_sss(self):
        """
        Plot the surface sound speed as measured.
        """
        if not hasattr(self, '_sss_array'):
            self._build_sss_array()
        plt.figure()
        plt.plot(self._sss_array['Time'], self._sss_array['SoundSpeed'])
        plt.xlabel('Time (POSIX)')
        plt.ylabel('Surface Sound Speed (Measured, m/s)')
        plt.grid()
            
    def getping(self, pingtime = 0, pingnumber = 0, recordlist = [], extra = True):
        """
        This method provides all the datagrams and navigational information 
        associated with a ping.  Provide a keyword argument for either the time
        of the ping (kwarg pingtime) or the ping number (kwarg pingnumber) in 
        the file.  If both a time stamp and a ping number are provided the time
        stamp is used.  The navigation, attitude, runtime parameters aand sound
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
                b = np.isclose([self.map.packdir['88'][:,1]],[pingtime], rtol = 0, atol = 5e-4)
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
                recordlist = [str(n) for n in recordlist] # Support records as numbers
                for n in recordlist:
                    if n not in filerecords:
                        recordlist.remove(n)
            # now that the records to get are established as in the file...
            if len(recordlist) > 0:
                subpack = {}
                for n in recordlist:
                    if n != '107':
                        subpack[n] = self.getrecord(n,pingnumber)
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
    
    hdr_dtype = np.dtype([('Bytes','I'),('Start','B'),('Type','B'),
        ('Model','H'),('Date','I'),('Time','I')])
    
    def __init__(self, fileblock, byteswap = False):
        """Reads the header section, which is the first 16 bytes, of the
        given memory block."""
        self.byteswap = byteswap
        hdr_sz = Datagram.hdr_dtype.itemsize
        self.header = np.frombuffer(fileblock[:hdr_sz], dtype = Datagram.hdr_dtype)
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
        self.datablockheader =  fileblock[:hdr_sz]
        self.datablockfooter = fileblock[-3:]
        
        etx = np.frombuffer(fileblock[-3:-2], dtype=np.uint8, count=1)[0]
        if etx != 3:
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
        
    def rawdatablock(self):
        return self.datablockheader + self.datablock + self.datablockfooter
        
    def decode(self):
        """
        Directs to the correct decoder.
        """
        if self.dtype == 48:
            self.subpack = Data48(self.datablock, self.byteswap)
        elif self.dtype == 49:
            self.subpack = Data49(self.datablock, self.byteswap)
        elif self.dtype == 51:
            self.subpack = Data51(self.datablock, self.header['Model'], self.byteswap)
        elif self.dtype == 65:
            self.subpack = Data65(self.datablock, self.time, self.byteswap)
        elif self.dtype == 66:
            self.subpack = Data66(self.datablock, self.header['Model'], self.byteswap)
        elif self.dtype == 67:
            self.subpack = Data67(self.datablock, self.byteswap)
        elif self.dtype == 68:
            self.subpack = Data68(self.datablock, self.header['Model'], self.byteswap)
        elif self.dtype == 71:
            self.subpack = Data71(self.datablock, self.time, self.byteswap)
        elif self.dtype == 73:
            self.subpack = Data73(self.datablock, self.byteswap)
        elif self.dtype == 78:
            self.subpack = Data78(self.datablock, self.time, self.byteswap)
        elif self.dtype == 79:
            self.subpack = Data79(self.datablock, self.byteswap)
        elif self.dtype == 80:
            self.subpack = Data80(self.datablock, self.byteswap)
        elif self.dtype == 82:
            self.subpack = Data82(self.datablock, self.byteswap)
        elif self.dtype == 83:
            self.subpack = Data83(self.datablock, self.byteswap)
        elif self.dtype == 85:
            self.subpack = Data85(self.datablock, self.byteswap)
        elif self.dtype == 88:
            self.subpack = Data88(self.datablock, self.byteswap)
        elif self.dtype == 89:
            self.subpack = Data89(self.datablock, self.byteswap)
        elif self.dtype == 102:
            self.subpack = Data102(self.datablock, self.byteswap)
        elif self.dtype == 104:
            self.subpack = Data104(self.datablock, self.byteswap)
        elif self.dtype == 105:
            #same definition for this data type
            self.subpack = Data73(self.datablock, self.byteswap)
        elif self.dtype == 107:
            self.subpack = Data107(self.datablock, self.byteswap)
        elif self.dtype == 109:
            self.subpack = Data109(self.datablock, self.byteswap)
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
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970,1,1).toordinal()
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
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))


class Data(object):
    """
    Displays contents of the header to the command window.
    """
    def display(self):
        header = np.zeros(0)
        for n, name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))


class Data48:
    """
    PU information and status 0x30 / '0' / 48.
    """
    
    hdr_dtype = np.dtype([('ByteOrderFlag','H'),('System Serial#','H'),
        ('UDPPort1','H'),('UDPPort2','H'),('UDPPort3','H'),('UDPPort4','H'),
        ('SystemDescriptor','I'),('PUSoftwareVersion','S16'),
        ('BSPSoftwareVersion','S16'),('SonarHead/TransceiverSoftware1','S16'),
        ('SonarHead/TransceiverSoftware2','S16'),('HostIPAddress','I'),
        ('TXOpeningAngle','B'),('RXOpeningAngle','B'),('Spare1','I'),
        ('Spare2','H'),('Spare3','B')])
        
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        
        hdr_sz = Data48.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=Data48.hdr_dtype)[0]
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
            

class Data49:
    """
    PU Status datagram 0x31 / '1' / 49.  All values are converted to degrees,
    meters, and meters per second.
    """
    
    hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'),
        ('PingRate',"f"),('PingCounter','H'),('SwathDistance','I'),
        ('SensorInputStatusUDP2','I'),('SensorInputStatusSerial1','I'),
        ('SensorInputStatusSerial2','I'),('SensorInputStatusSerial3','I'),
        ('SensorInputStatusSerial4','I'),('PPSstatus','b'),
        ('PositionStatus','b'),('AttitudeStatus','b'),('ClockStatus','b'),
        ('HeadingStatus','b'),('PUstatus','B'),('LastHeading',"f"),
        ('LastRoll',"f"),('LastPitch',"f"),('LastSonarHeave',"f"),
        ('TransducerSoundSpeed',"f"),('LastDepth',"f"),('ShipVelocity',"f"),
        ('AttitudeVelocityStatus','B'),('MammalProtectionRamp','B'),
        ('BackscatterOblique','b'),('BackscatterNormal','b'),('FixedGain','b'),
        ('DepthNormalIncidence','B'),('RangeNormalIncidence','H'),
        ('PortCoverage','B'),('StarboardCoverage','B'),
        ('TransducerSoundSpeedFromProfile',"f"),('YawStabAngle',"f"),
        ('PortCoverageORAbeamVelocity','h'),
        ('StarboardCoverageORDownVelocity','h'),('EM2040CPUTemp','b')])
        
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        
        hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'),
            ('PingRate',"H"),('PingCounter','H'),('SwathDistance','I'),
            ('SensorInputStatusUDP2','I'),('SensorInputStatusSerial1','I'),
            ('SensorInputStatusSerial2','I'),('SensorInputStatusSerial3','I'),
            ('SensorInputStatusSerial4','I'),('PPSstatus','b'),
            ('PositionStatus','b'),('AttitudeStatus','b'),('ClockStatus','b'),
            ('HeadingStatus','b'),('PUstatus','B'),('LastHeading',"H"),
            ('LastRoll',"h"),('LastPitch',"h"),('LastSonarHeave',"h"),
            ('TransducerSoundSpeed',"H"),('LastDepth',"I"),('ShipVelocity',"h"),
            ('AttitudeVelocityStatus','B'),('MammalProtectionRamp','B'),
            ('BackscatterOblique','b'),('BackscatterNormal','b'),('FixedGain','b'),
            ('DepthNormalIncidence','B'),('RangeNormalIncidence','H'),
            ('PortCoverage','B'),('StarboardCoverage','B'),
            ('TransducerSoundSpeedFromProfile',"H"),('YawStabAngle',"h"),
            ('PortCoverageORAbeamVelocity','h'),
            ('StarboardCoverageORDownVelocity','h'),('EM2040CPUTemp','b')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=hdr_dtype)[0]
        self.header = self.header.astype(Data49.hdr_dtype)
        self.header['PingRate'] *= 0.01
        self.header['LastHeading'] *= 0.01
        self.header['LastRoll'] *= 0.01
        self.header['LastPitch'] *= 0.01
        self.header['LastSonarHeave'] *= 0.01
        self.header['TransducerSoundSpeed'] *= 0.1
        self.header['LastDepth'] *= 0.01
        self.header['ShipVelocity'] *= 0.01
        self.header['TransducerSoundSpeedFromProfile'] *= 0.1
        self.header['YawStabAngle'] *= 0.01
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
class Data51:
    """
    ExtraParameters datagram.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('ContentIdentifier','H')])
        
    def __init__(self, datablock, model, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_sz = Data51.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=Data51.hdr_dtype)[0]
        content_type = self.header[-1]
        if content_type == 1:
            self.data = datablock[hdr_sz:hdr_sz + 100]
        elif content_type == 2:
            pass
        elif content_type == 3:
            pass
        elif content_type == 4:
            pass
        elif content_type == 5:
            pass
        elif content_type == 6:
            data_sz = np.frombuffer(datablock[hdr_sz:hdr_sz+2], dtype='H')[0]
            self.rawdata = datablock[hdr_sz+2:hdr_sz+2+data_sz]
            if model == 710:
                self._parse_710_bscorr()
            elif model == 122:
                self._parse_122_bscorr()
            
    def _parse_710_bscorr(self):
        """
        Parse the BSCorr file.
        """
        c = self.rawdata.split('#')
        t = len(c)
        n = 0
        self.names =[]
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
                        a,d = sectordata[k+3].split('\t')
                        angle.append(float(a))
                        offset.append(float(d))
                    sector.append(np.array(list(zip(angle,offset))))
                self.data.append(np.array(sector))
                self.powers.append(np.array(secpower))
            n += 1

    def _parse_122_bscorr(self):
        """
        Parse the BSCorr file.
        """
        c = self.rawdata.split('\n')
        t = len(c) - 1 # no need to look at hex flag at end 
        n = 0
        header = True
        section_idx = []
        self.names =[]
        self.swathnum = []
        self.modes = []
        self.powers = []
        self.data = []
        # find all the sections to be parsed
        while n < t:
            if header == False:
                if (c[n][0] =='#') & (c[n+1][0] == '#'):
                    section_idx.append(n)
            else:
                if c[n] == '# source level    lobe angle    lobe width':
                    header = False
            n += 1
        section_idx.append(t)
        for n in range(len(section_idx)-1):
            m = section_idx[n]
            end = section_idx[n+1]
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
                    while c[m+k][0] != '#' and m+k+1 < end:
                        info = [int(x) for x in c[m+k].split()]
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
                ax.plot(data[n][:,0],data[n][:,1], 'o:')
            r = ax.get_xlim()
            ax.set_xlim((max(r),min(r)))
            ax.set_xlabel('Beam Angle (deg, negative is to STBD)')
            ax.set_ylabel('BS Adjustment (dB)')
            ax.set_title('BSCorr: ' + self.names[mode_number])
            ax.grid()
    
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        if 'data' in self.__dict__:
            print(self.data)
        
class Data65:
    """
    Attitude datagram 0x41/'A'/65. Data can be found in the array 'data' and
    is stored as time (POSIX), roll(deg), pitch(deg), heave(m), 
    heading(deg).  sensor_descriptor does not appear to parse correctly... 
    Perhaps it is not included in the header size so it is not sent to this
    object in the datablock?
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('NumEntries','H')])
    att_dtype = np.dtype([('Time','d'),('Status','H'),('Roll','f'),('Pitch','f'),
        ('Heave','f'),('Heading','f')])
        
    def __init__(self, datablock, POSIXtime, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        self.time = POSIXtime
        hdr_sz = Data65.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=Data65.hdr_dtype)[0]
        self.sensor_descriptor = np.frombuffer(datablock[-1:], dtype=np.uint8)[0]
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """
        Reads the data section of the record.  Time is in POSIX time,
        angles are in degrees, distances in meters.
        """
        att_file_dtype = np.dtype([('Time','H'),('Status','H'),('Roll','h'),('Pitch','h'),
            ('Heave','h'),('Heading','H')])
        self.data = np.frombuffer(datablock[:-1], dtype=att_file_dtype)
        self.data = self.data.astype(Data65.att_dtype)
        self.data['Time'] = self.data['Time'] * 0.001 + self.time
        self.data['Roll'] *= 0.01
        self.data['Pitch'] *= 0.01
        self.data['Heave'] *= 0.01
        self.data['Heading'] *= 0.01
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        print('Sensor Descriptor : ' + np.binary_repr(self.sensor_descriptor,8))

class Data66:
    """
    PU BIST results output datagram 0x42/'B'/66.  The raw string text is parsed
    and provided in the array 'data' and 'metadata'.  The raw data 
    string is also available in the 'raw_data' class variable.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('Test#','H'),
        ('TestStatus','h')])
        
    def __init__(self, datablock, model, byteswap = False):
        """
        Catches the binary datablock and decodes the record.
        """
        hdr_sz = Data66.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data66.hdr_dtype)[0]
        self.raw_data = datablock[hdr_sz:]
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
                                data[m].append(float(line[m+1]))
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
                fig,ax = plt.subplots(len(self.label),1)
                for n,a in enumerate(ax):
                    a.plot(self.data[:,n])
                    a.set_title(str(self.label[n]))
                    a.set_ylabel('dB')
                    a.set_xlim((0,self.data.shape[0]))
                a.set_xlabel('Channel Number')
                fig.suptitle(('Noise'))
            elif self._model == 710:
                plt.figure()
                plt.plot(self.data.flatten())
                plt.xlabel('Channel Number')
                plt.ylabel('Noise Level (dB)')
                plt.title('EM710 Noise Test')
                plt.grid()
                plt.xlim((0,len(self.data.flatten())))
            else:
                print('Plotting of ' + self.testtype + ' is not supported for the EM' + str(self._model))
        elif self.testtype == 'NoiseSpectrum':
            if self._model == 710 or self._model == 2040:
                l,w = self.data.shape
                legend = []
                for n in range(w):
                    legend.append('Board ' + str(n))
                plt.figure()
                plt.plot(self.freq,self.data)
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
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        print(self.raw_data)
            
class Data67:
    """
    Clock datagram 043h / 67d / 'C'. Date is YYYYMMDD. Time is in miliseconds
    since midnight.
    """
    hdr_dtype = np.dtype([('ClockCounter','H'),('SystemSerial#','H'),
        ('Date','I'),('Time','I'),('1PPS','B')])
    def __init__(self,datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Data67.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], 
            dtype = Data67.hdr_dtype)[0]
        if len(datablock) > hdr_sz:
            print(len(datablock), hdr_sz)
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
class Data68:
    """
    XYZ datagram 044h / 68d / 'D'. All values are converted to meters, degrees,
    or whole units.  The header sample rate may not be correct, but is 
    multiplied by 4 to make the one way travel time per beam appear correct. The
    detection window length per beam is in its raw form...
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('VesselHeading',"f"),('SoundSpeed',"f"),('TransducerDepth',"f"),
        ('MaximumBeams','B'),('ValidBeams','B'),('Zresolution',"f"),
        ('XYresolution',"f"),('SampleRate','f')])
    xyz_dtype = np.dtype([('Depth',"f"),('AcrossTrack',"f"),('AlongTrack',"f"),
        ('BeamDepressionAngle',"f"),('BeamAzimuthAngle',"f"),
        ('OneWayRange',"f"),('QualityFactor','B'),
        ('DetectionWindowLength',"f"),('Reflectivity',"f"),('BeamNumber','B')])
        
    def __init__(self,datablock, model, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('VesselHeading',"H"),('SoundSpeed',"H"),('TransducerDepth',"H"),
            ('MaximumBeams','B'),('ValidBeams','B'),('Zresolution',"B"),
            ('XYresolution',"B"),('SampleRate','H')])
        hdr_sz = hdr_dtype.itemsize
        self._model = model
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data68.hdr_dtype)
        self.header[2] *= 0.01
        self.header[3] *= 0.1
        self.header[4] *= 0.01
        self.header[7] *= 0.01
        self.header[8] *= 0.01
        self.header[-1] *= 4    # revisit this number... it makes the range work but may not be correct
        self.depthoffsetmultiplier = np.frombuffer(datablock[-1:], dtype = 'b')[0] * 65536
        self.header[4] += self.depthoffsetmultiplier
        self.read(datablock[hdr_sz:-1])
        
    def read(self, datablock):
        """
        Decodes the repeating data section, and shifts all values into meters,
        degrees, or whole units.
        """
        decode_depth = "h"
        if self._model == 300 or self._model == 120:
            decode_depth = "H"
        xyz_dtype = np.dtype([('Depth',decode_depth),('AcrossTrack',"h"),('AlongTrack',"h"),
            ('BeamDepressionAngle',"h"),('BeamAzimuthAngle',"H"),
            ('OneWayRange',"H"),('QualityFactor','B'),
            ('DetectionWindowLength',"B"),('Reflectivity',"b"),('BeamNumber','B')])       
        self.data = np.frombuffer(datablock, dtype = xyz_dtype)
        self.data = self.data.astype(Data68.xyz_dtype)
        self.data['Depth'] *= self.header['Zresolution']
        self.data['AcrossTrack'] *= self.header['XYresolution']
        self.data['AlongTrack'] *= self.header['XYresolution']
        self.data['BeamDepressionAngle'] *= 0.01
        self.data['BeamAzimuthAngle'] *= 0.01
        self.data['OneWayRange'] /= self.header['SampleRate']
        #self.data['DetectionWindowLength'] *= 4    # not sure what this is for or what it means
        self.data['Reflectivity'] *= 0.5
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        print('TransducerDepthOffsetMultiplier : ' + str(self.depthoffsetmultiplier))
            
    
class Data71:
    """
    Surface Sound Speed datagram 047h / 71d / 'G'.  Time is in POSIX time and
    sound speed is in meters per second.
    """
    hdr_dtype = np.dtype([('SoundSpeedCounter','H'),('SystemSerial#','H'),
        ('NumEntries','H')])
    data_dtype = np.dtype([('Time','d'),('SoundSpeed','f')])
    
    def __init__(self, datablock, POSIXtime, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        data_dtype = np.dtype([('Time','H'),('SoundSpeed','H')])
        hdr_sz = Data71.hdr_dtype.itemsize
        data_sz = data_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], 
            dtype = Data71.hdr_dtype)[0]
        self.data = np.frombuffer(datablock[hdr_sz:-1], dtype = data_dtype)
        self.data = self.data.astype(Data71.data_dtype)
        self.data['Time'] += POSIXtime
        self.data['SoundSpeed'] *= 0.1
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
        
class Data73:
    """
    Installation parameters datagram 049h (start) / 73d / 'I', 069h(stop)/ 105d
    / 'I' or 70h(remote) / 112d / 'r'.  There is a short header section and the
    remainder of the record is ascii, comma delimited.
    """
    hdr_dtype = np.dtype([('SurveyLine#','H'),('Serial#','H'),('Serial#2','H')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Data73.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data73.hdr_dtype)[0]
        temp = datablock[hdr_sz:].decode().split(',')
        self.settings = {}
        for entry in temp:
            data = entry.split('=')
            if len(data) == 2:
                self.settings[entry[:3]] = data[1]
                
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        keys = list(self.settings.keys())
        keys.sort()
        for key in keys:
            print(key + ' : ' + str(self.settings[key]))
    
    
class Data78:
    """
    Raw range and angle datagram, aka 'N'/'4eh'/78d.  All data is contained
    in the header, rx, and tx arrays. the rx and tx arrays are ordered as in
    the data definition document, but have been converted to degrees, dB,
    meters, etc.
    The reported angles are in the transducer reference frame, so be careful of
    reverse mounted configurations. For the TX, forward angles are positive, 
    for the RX angles to port are positive.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('SoundSpeed','f'),
        ('Ntx','H'),('Nrx','H'),('Nvalid','H'),('SampleRate','f'),('Dscale','I')])
    ntx_dtype = np.dtype([('TiltAngle','f'),('Focusing','f'),('SignalLength','f'),('Delay','f'),
        ('Frequency','f'),('AbsorptionCoef','f'),('WaveformID','B'),
        ('TransmitSector#','B'),('Bandwidth','f')])
    nrx_dtype = np.dtype([('BeamPointingAngle','f'),('TransmitSectorID','B'),('DetectionInfo','B'),
        ('WindowLength','H'),('QualityFactor','B'),('Dcorr','b'),('TravelTime','f'),
        ('Reflectivity','f'),('CleaningInfo','b'),('Spare','B')])
    
    def __init__(self, datablock, pingtime, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('SoundSpeed','H'),
            ('Ntx','H'),('Nrx','H'),('Nvalid','H'),('SampleRate','f'),('Dscale','I')])
        hdr_sz = hdr_dtype.itemsize
        self.pingtime = pingtime
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=hdr_dtype)[0]
        self.header = self.header.astype(Data78.hdr_dtype)
        self.header[2] *= 0.1  # sound speed to convert to meters/second
        self.read(datablock[hdr_sz:])

    def read(self, datablock):
        """Decodes the repeating parts of the record."""
        ntx_file_dtype = np.dtype([('TiltAngle','h'),('Focusing','H'),('SignalLength','f'),('Delay','f'),
            ('Frequency','f'),('AbsorptionCoef','H'),('WaveformID','B'),
            ('TransmitSector#','B'),('Bandwidth','f')])
        ntx_file_sz = ntx_file_dtype.itemsize
        nrx_file_dtype = np.dtype([('BeamPointingAngle','h'),('TransmitSectorID','B'),('DetectionInfo','B'),
            ('WindowLength','H'),('QualityFactor','B'),('Dcorr','b'),('TravelTime','f'),
            ('Reflectivity','h'),('CleaningInfo','b'),('Spare','B')])
        ntx = self.header[3]
        self.tx = np.frombuffer(datablock[:ntx*ntx_file_sz], dtype = ntx_file_dtype)
        self.tx = self.tx.astype(Data78.ntx_dtype)
        self.tx['TiltAngle'] *= 0.01  # convert to degrees
        self.tx['Focusing'] *= 0.1   # convert to meters
        self.tx['AbsorptionCoef'] *= 0.01  # convert to dB/km
        self.rx = np.frombuffer(datablock[ntx*ntx_file_sz:-1], dtype = nrx_file_dtype)
        self.rx = self.rx.astype(Data78.nrx_dtype)
        self.rx['BeamPointingAngle'] *= 0.01  # convert to degrees
        self.rx['Reflectivity'] *= 0.1   # convert to dB
        
    def get_rx_time(self):
        """
        Returns the receive times in POSIX time.
        """
        txnum = self.tx['TransmitSector#']
        txnum.sort()
        # deal with EM2040 in 200 kHz where the tx sector idx are [0,2]
        if txnum.max() == len(txnum):
            txnum[-1] = txnum[-1] - 1
        txdelays = self.tx['Delay'][txnum]
        rxdelays = txdelays[self.rx['TransmitSectorID']].astype(np.float64)
        rxtime = self.rx['TravelTime'].astype(np.float64) + rxdelays + self.pingtime
        return rxtime
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
    
class Data79:
    """
    Quality factor datagram 4fh / 79d / 'O'.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('Nrx','H'),('Npar','H')]) # The data format has a Spare Byte here...
    qf_dtype = np.dtype([('QualityFactor','f4')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Data79.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data79.hdr_dtype)[0]
        if self.header['Npar'] > 1:
            print("Warning: Datagram has expanded and may not parse correctly.")
        self.read(datablock[hdr_sz:-1])
            
    def read(self, datablock):
        """
        Reads the Quality Factor Datagram.
        """
        if self.header['Npar'] == 1:
            self.data = np.frombuffer(datablock, dtype = Data79.qf_dtype)
        else:
            print("Only parsing original IFREMER quality factor")
            step = 4 * self.header['Nrx'] * self.header['Npar']
            self.data = np.zeros(self.header['Nrx'], dtype = Data79.qf_dtype)
            for n in range(self.header['Nrx']):
                self.data = np.frombuffer(datablock[n*step:n*step+4],
                    dtype = Data79.qf_dtype)
                    
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
    
    
class Data80:
    """
    Position datagram, 0x50 / 'P' / 80. Available data is in the header
    list, and all data has been converted to degrees or meters.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('Latitude','d'),
        ('Longitude','d'),('Quality','f'),('Speed','f'),('Course','f'),
        ('Heading','f'),('System','B'),('NumberInputBytes','B')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the record."""
        hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('Latitude','i'),
            ('Longitude','i'),('Quality','H'),('Speed','H'),('Course','H'),
            ('Heading','H'),('System','B'),('NumberInputBytes','B')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        # read the original datagram, of which the size is the last part of the header.
        self.raw_data = datablock[hdr_sz:hdr_sz+self.header[-1]]
        self.header = self.header.astype(Data80.hdr_dtype)
        self.header['Latitude'] /= 20000000.  # convert to degrees
        self.header['Longitude'] /= 10000000.  # convert to degrees
        self.header['Quality'] *= 0.01       # convert to meters
        self.header['Speed'] *= 0.01       # convert to meters/second
        self.header['Course'] *= 0.01       # convert to degrees
        self.header['Heading'] *= 0.01       # convert to degrees
        
    def parse_raw(self):
        """
        Parses the raw_data that arrived in SIS and puts it in source_data.
        """
        try:
            msg_type = np.frombuffer(self.raw_data[:5], dtype = 'S5')[0].decode()
            if msg_type == 'INGGA':
                self._parse_gga()
            elif msg_type == 'GPGGA':
                self._parse_gga()
            elif msg_type == 'INGGK':
                self._parse_ggk()
            elif msg_type == 'GPGGK':
                self._parse_ggk()
        except AttributeError:
            print('Unable to parse raw data from data80')
            
    def _parse_gga(self):
        """
        parse the gga string.
        """
        gga_dtype = np.dtype([('MessageID','S5'),('POSIX','d'),
            ('Latitude','f'),('LatDirection','S1'),('Longitude','f'),
            ('LonDirection','S1'),('GPSQuality','B'),('#SV','B'),('HDOP','f'),
            ('OrthometricHeight','f'),('HeightUnits','S1'),('GeoidSeparation','f'),
            ('SeparationUnits','S1'),('AgeOfDGPS','f'),('ReferenceStationID','H'),
            ('CheckSum','H')])
            
        self.source_data = np.zeros(1, dtype = gga_dtype)[0]
        temp = self.raw_data.decode().rstrip('\x00').split(',')
        for n,t in enumerate(temp):
            if len(t) > 0:
                if n == 0 or n == 3 or n == 5 or n == 10 or n == 12:
                    self.source_data[n] = t
                elif n == 1 or n == 8 or n == 9 or n == 11 or n == 13:
                    self.source_data[n] = float(t)
                elif n == 2:
                    deg = int(t[:2])
                    min = float(t[2:])
                    self.source_data[n] = deg + min/60.
                elif n == 4:
                    deg = int(t[:3])
                    min = float(t[3:])
                    self.source_data[n] = deg + min/60.
                elif n == 14:
                    t2 = t.split('*')
                    self.source_data[-2] = int(t2[0])
                    self.source_data[-1] = int(t2[1],16)
                else:
                    self.source_data[n] = int(t)
            else:
                self.source_data[n] = None
                
    def _parse_ggk(self):
        """
        parse the ggk string.
        """
        ggk_dtype = np.dtype([('MessageID','S5'),('UTCTime','S10'),('UTCDay','S6'),
            ('Latitude','f'),('LatDirection','S1'),('Longitude','f'),
            ('LonDirection','S1'),('GPSQuality','B'),('#SV','B'),('DOP','f'),
            ('EllipsoidHeight','f'),('HeightUnits','S1'),('CheckSum','H')])
            
        self.source_data = np.zeros(1, dtype = ggk_dtype)[0]
        temp = self.raw_data.decode().rstrip('\x00').split(',')
        for n,t in enumerate(temp):
            if len(t) > 0:
                if n == 0 or n == 1 or n == 2 or n == 4 or n == 6:
                    self.source_data[n] = t
                elif n == 9:
                    self.source_data[n] = float(t)
                elif n == 3:
                    deg = int(t[:2])
                    min = float(t[2:])
                    self.source_data[n] = deg + min/60.
                elif n == 5:
                    deg = int(t[:3])
                    min = float(t[3:])
                    self.source_data[n] = deg + min/60.
                elif n == 10:
                    self.source_data[n] = float(t[3:])
                elif n == 11:
                    t2 = t.split('*')
                    self.source_data[-2] = t2[0]
                    self.source_data[-1] = int(t2[1],16)
                else:
                    self.source_data[n] = int(t)
            else:
                self.source_data[n] = None
        year = int(self.source_data[2][4:]) + 2000 # hard coding for 21 century :(
        month = int(self.source_data[2][:2])
        day = int(self.source_data[2][2:4])
        hour = int(self.source_data[1][:2])
        minute = int(self.source_data[1][2:4])
        second = float(self.source_data[1][4:])        
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970,1,1).toordinal()
        dayseconds = hour * 3600. + minute * 60. + second 
        self._ggk_time = numdays * 24 * 60 * 60 + dayseconds
        
        
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        self.parse_raw()
        print('\n***raw data record***')
        for n,name in enumerate(self.source_data.dtype.names):
            print(name + ' : ' + str(self.source_data[n]))
        
class Data82:
    """
    Runtime parameters datagram, 0x52 / 'R' / 82.
    Values that are converted into whole units include: AbsorptionCoefficent,
    TransmitPulseLength, TransmitBeamwidth, ReceiveBeamwidth, and
    TransmitAlongTilt.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('OperatorStationStatus','B'),('ProcessingUnitStatus','B'),
        ('BSPStatus','B'),('SonarHeadOrTransceiverStatus','B'),
        ('Mode','B'),('FilterID','B'),('MinDepth','H'),('MaxDepth','H'),
        ('AbsorptionCoefficent','f'),('TransmitPulseLength','f'),
        ('TransmitBeamWidth','f'),('TransmitPower','b'),
        ('ReceiveBeamWidth','f'),('ReceiveBandWidth50Hz','B'),
        ('ReceiverFixedGain','B'),('TVGlawCrossoverAngle','B'),
        ('SourceOfSoundSpeed','B'),('MaxPortSwathWidth','H'),
        ('BeamSpacing','B'),('MaxPortCoverage','B'),
        ('YawAndPitchStabilization','B'),('MaxStarboardCoverage','B'),
        ('MaxStarboardSwathWidth','H'),('TransmitAlongTilt','f'),
        ('HiLoFrequencyAbsorptionCoeffRatio','B')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the record."""
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('OperatorStationStatus','B'),('ProcessingUnitStatus','B'),
            ('BSPStatus','B'),('SonarHeadOrTransceiverStatus','B'),
            ('Mode','B'),('FilterID','B'),('MinDepth','H'),('MaxDepth','H'),
            ('AbsorptionCoefficent','H'),('TransmitPulseLength','H'),
            ('TransmitBeamWidth','H'),('TransmitPower','b'),
            ('ReceiveBeamWidth','B'),('ReceiveBandWidth50Hz','B'),
            ('ReceiverFixedGain','B'),('TVGlawCrossoverAngle','B'),
            ('SourceOfSoundSpeed','B'),('MaxPortSwathWidth','H'),
            ('BeamSpacing','B'),('MaxPortCoverage','B'),
            ('YawAndPitchStabilization','B'),('MaxStarboardCoverage','B'),
            ('MaxStarboardSwathWidth','H'),('TransmitAlongTilt','h'),
            ('HiLoFrequencyAbsorptionCoeffRatio','B')])
        hdr_sz = hdr_dtype.itemsize
        temp = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = temp.astype(Data82.hdr_dtype)
        self.header['AbsorptionCoefficent'] *= 0.01
        self.header['TransmitPulseLength'] *= 0.000001
        self.header['TransmitBeamWidth'] *= 0.1
        self.header['ReceiveBeamWidth'] *= 0.1
        self.header['TransmitAlongTilt'] *= 0.1        
    
    def print_byte(self, field_number):
        """
        Prints the given 1 bite field in a binary form.
        """
        if type(self.header[field_number]) == np.uint8:
            print(np.binary_repr(self.header[field_number], width = 8))
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        bitfields = np.array([2,3,4,5,6,7,18,20,22,26])
        for n,name in enumerate(self.header.dtype.names):
            if np.any(bitfields == n):
                print(name + ' : ' + np.binary_repr(self.header[n], width = 8))
            else:
                print(name + ' : ' + str(self.header[n]))
                
                
class Data83:
    """
    Seabed Imagary datagram 053h / 83d / 'Seabed image data'.  All data is
    converted into whole units of degrees, meters, dB, etc, except Oblique
    Backscatter and Normal Backscatter which are in their raw form.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('MeanAbsorption',"f"),('PulseLength',"f"),('RangeToNormal','H'),
        ('StartRangeSampleOfTVG','H'),('StopRangeSampleOfTVG','H'),
        ('NormalIncidenceBS',"f"),('ObliqueBS',"f"),('TxBeamwidth',"f"),
        ('TVGLawCrossoverAngle',"f"),('NumberValidBeams','B')])
    beaminfo_dtype = np.dtype([('BeamIndexNumber','B'),('SortingDirection','b'),
        ('#SamplesPerBeam','H'),('CenterSample#','H')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('MeanAbsorption',"H"),('PulseLength',"H"),('RangeToNormal','H'),
            ('StartRangeSampleOfTVG','H'),('StopRangeSampleOfTVG','H'),
            ('NormalIncidenceBS',"b"),('ObliqueBS',"b"),('TxBeamwidth',"H"),
            ('TVGLawCrossoverAngle',"B"),('NumberValidBeams','B')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data83.hdr_dtype)
        self.header[2] *= 0.01
        self.header[3] *= 10**-6
        self.header[7] *= 1  # check this
        self.header[8] *= 1  # check this
        self.header[9] *= 0.1  
        self.header[10] *= 0.1
        numbeams = self.header[-1]
        self._read(datablock[hdr_sz:], numbeams)
    
    def _read(self, datablock, numbeams):
        """
        Reads the data section of the record.
        """
        beaminfo_sz = Data89.beaminfo_dtype.itemsize
        samples_dtype = np.dtype([('Amplitude',"b")])    
        samples_sz = samples_dtype.itemsize
        p = beaminfo_sz*numbeams
        self.beaminfo = np.frombuffer(datablock[:p],
            dtype = Data89.beaminfo_dtype)
        maxsamples = self.beaminfo['#SamplesPerBeam'].max()
        self.samples = np.zeros((numbeams,maxsamples), dtype = 'float')
        for n in range(numbeams):
            numsamples = self.beaminfo[n]['#SamplesPerBeam']
            temp = np.frombuffer(datablock[p:p+numsamples*samples_sz],
                dtype = samples_dtype)
            p += numsamples*samples_sz
            #startsample = self.beaminfo[n]['CenterSample#']
            self.samples[n,:numsamples] = temp.astype('float')[:]
        self.samples *= 0.5  # check this

        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))

            
class Data85:
    """
    Sound Speed datagram 055h / 85d / 'U'. Time is in POSIX, depth
    is in meters, sound speed is in meters per second.
    """
    hdr_dtype = np.dtype([('ProfileCounter','H'),('SystemSerial#','H'),
        ('Date','I'),('Time',"d"),('NumEntries','H'),('DepthResolution','H')])
    data_dtype = np.dtype([('Depth','d'),('SoundSpeed','f')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('ProfileCounter','H'),('SystemSerial#','H'),
            ('Date','I'),('Time',"I"),('NumEntries','H'),
            ('DepthResolution','H')])
        hdr_sz = hdr_dtype.itemsize
        data_dtype = np.dtype([('Depth','I'),('SoundSpeed','I')])
        self.header = np.frombuffer(datablock[:hdr_sz], 
            dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data85.hdr_dtype)
        self.POSIXtime = self._maketime(self.header['Date'], self.header['Time'])
        depth_resolution = self.header['DepthResolution'] * 0.01
        self.data = np.frombuffer(datablock[hdr_sz:-1], dtype = data_dtype)
        self.data = self.data.astype(Data85.data_dtype)
        self.data['Depth'] *= depth_resolution
        self.data['SoundSpeed'] *= 0.1
        
    def _maketime(self, date, time):
        """
        Makes the time stamp of the current packet as a POSIX time stamp.
        UTC is assumed.
        """
        date = str(date)
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970,1,1).toordinal()
        dayseconds = time #* 0.001
        return numdays * 24 * 60 * 60 + dayseconds
        
    def plot(self):
        """
        Creates a simple plot of the cast.
        """
        plt.figure()
        plt.plot(self.data['SoundSpeed'],self.data['Depth'])
        plt.ylim((self.data['Depth'].max(), self.data['Depth'].min()))
        plt.xlabel('Sound Speed (m/s)')
        plt.ylabel('Depth (m)')
        plt.title('Cast at POSIX time ' + str(self.header['Time']))
        plt.draw()
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        print("POSIXtime : " + str(self.POSIXtime))
         
class Data88:
    """
    XYZ datagram, 0x58 / 'X' / 88.  All data is in the header list or
    stored in the 'data' array.  Values have been converted to degrees and
    dB.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('Heading','f'),
        ('SoundSpeed','f'),('TransmitDepth','f'),('NumBeams','H'),
        ('NumValid','H'),('SampleFrequency','f'),('Spare','i')])
    hdr_file_dtype = np.dtype([('PingCounter', 'H'), ('Serial#', 'H'), ('Heading', 'H'),
                               ('SoundSpeed', 'H'), ('TransmitDepth', 'f'), ('NumBeams', 'H'),
                               ('NumValid', 'H'), ('SampleFrequency', 'f'), ('Spare', 'i')])
    xyz_dtype = np.dtype([('Depth','f'),('AcrossTrack','f'),('AlongTrack','f'),
        ('WindowLength','H'),('QualityFactor','B'),('IncidenceAngleAdjustment','f'),
        ('Detection','B'),('Cleaning','b'),('Reflectivity','f')])
    xyz_file_dtype = np.dtype([('Depth', 'f'), ('AcrossTrack', 'f'), ('AlongTrack', 'f'),
                               ('WindowLength', 'H'), ('QualityFactor', 'B'), ('IncidenceAngleAdjustment', 'b'),
                               ('Detection', 'B'), ('Cleaning', 'b'), ('Reflectivity', 'h')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""

        hdr_sz = Data88.hdr_file_dtype.itemsize
        header = np.frombuffer(datablock[:hdr_sz], dtype=Data88.hdr_file_dtype)[0]
        self.header = header.astype(Data88.hdr_dtype)
        self.header['Heading'] *= 0.01  # convert to degrees
        self.header['SoundSpeed'] *= 0.1   # convert to m/s
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """
        Reads the data section of the record.
        """
        xyz_sz = Data88.xyz_file_dtype.itemsize
        #buffer length goes to -1 because of the uint8 buffer before etx
        self.data = np.frombuffer(datablock[:-1], dtype=Data88.xyz_file_dtype)
        self.data = self.data.astype(Data88.xyz_dtype)
        self.data['IncidenceAngleAdjustment'] *= 0.1  # convert to degrees
        self.data['Reflectivity'] *= 0.1 # convert to dB

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
            
            
class Data89:
    """
    Seabed Image datagram 059h / 89d / 'Y'.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('SamplingFreq','f'),('RangeToNormal','H'),('NormalBackscatter',"f"),
        ('ObliqueBackscatter',"f"),('TXBeamWidth',"f"),('TVGCrossover',"f"),
        ('NumberValidBeams','H')])
    beaminfo_dtype = np.dtype([('SortingDirection','b'),('DetectionInfo','B'),
        ('#SamplesPerBeam','H'),('CenterSample#','H')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('SamplingFreq','f'),('RangeToNormal','H'),('NormalBackscatter',"h"),
            ('ObliqueBackscatter',"h"),('TXBeamWidth',"H"),('TVGCrossover',"H"),
            ('NumberValidBeams','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data89.hdr_dtype)
        self.header['NormalBackscatter'] *= 0.1
        self.header['ObliqueBackscatter'] *= 0.1
        self.header['TXBeamWidth'] *= 0.1
        self.header['TVGCrossover'] *= 0.1
        numbeams = self.header[-1]
        self._read(datablock[hdr_sz:], numbeams)
    
    def _read(self, datablock, numbeams):
        """
        Reads the data section of the record. Backscatter is stored in one long
        array.  Use the included carve method to reshape the time series data
        into an array. Note the existance of the beam_position array that
        points to the start of each array.
        """
        beaminfo_sz = Data89.beaminfo_dtype.itemsize
        samples_dtype = np.dtype([('Amplitude',"h")])    
        p = beaminfo_sz*numbeams
        self.beaminfo = np.frombuffer(datablock[:p],
            dtype = Data89.beaminfo_dtype)
        t = self.beaminfo['#SamplesPerBeam'].sum()
        samples = np.frombuffer(datablock[p:p+t*samples_dtype.itemsize],
            dtype = samples_dtype)
        self.samples = samples.astype(np.float16) # float16 is right type?
        self.samples *= 0.1
        self.beam_position = np.zeros(self.beaminfo['#SamplesPerBeam'].shape, dtype = np.uint32)
        for n in range(len(self.beam_position)-1):
            self.beam_position[n+1] = self.beaminfo['#SamplesPerBeam'][n] + self.beam_position[n]

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
        idx = np.nonzero(s<0)[0]
        top[idx] = bottom[idx]
        bottom[idx] = c[idx]
        maxsamples = top.max() + bottom.max()
        self.samplearray = np.zeros((maxsamples,numbeams), dtype = np.float16)
        self.samplearray[:] = np.nan
        centerpos = top.max()
        for n in range(len(self.beaminfo)):
            if t[n] > 0:
                pointer = self.beam_position[n]
                beamsamples = self.samples[pointer:pointer+t[n]]
                start = centerpos - top[n]
                self.samplearray[start:start+t[n],n] = beamsamples[::s[n]]
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
        data,cidx = self.center()
        #beams = range(self.header[-1])
        #samples = range(-1*cidx, len(data)-cidx)
        #X,Y = np.meshgrid(beams, samples)
        #plt.pcolormesh(X,Y,data, cmap = 'gray')
        plt.imshow(data, aspect = 'auto', cmap = 'gray', interpolation = 'none')
        plt.clim((-80,0))

        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
            
            
class Data102:
    """
    Range and angle datagram, 66h / 102 / 'f'.  All values are converted to
    whole units, meaning meters, seconds, degrees, Hz, etc.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('Ntx','H'),('Nrx','H'),('SamplingFrequency',"f"),('Depth',"f"),
        ('SoundSpeed',"f"),('MaximumBeams','H'),('Spare1','H'),('Spare2','H')])
    ntx_dtype = np.dtype([('TiltAngle',"f"),('FocusRange',"f"),
        ('SignalLength',"f"),('Delay',"f"),
        ('CenterFrequency','I'),('Bandwidth',"I"),('SignalWaveformID','B'),
        ('TransmitSector#','B')])
    nrx_dtype = np.dtype([('BeamPointingAngle',"f"),('Range',"f"),
        ('TransmitSectorID','B'),('Reflectivity',"f"),('QualityFactor','B'),
        ('DetectionWindowLength','B'),('BeamNumber','h'),('Spare','H')])
   
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('Ntx','H'),('Nrx','H'),('SamplingFrequency',"I"),('Depth',"i"),
            ('SoundSpeed',"H"),('MaximumBeams','H'),('Spare1','H'),
            ('Spare2','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data102.hdr_dtype)
        self.header['SoundSpeed'] *= 0.1
        self.header['SamplingFrequency'] *= 0.01
        self.header['Depth'] *= 0.01
        self.read(datablock[hdr_sz:-1])

    def read(self, datablock):
        """
        Reads the data section of the record and converts values to whole
        units.
        """
        # declare ntx stuff
        ntx_dtype = np.dtype([('TiltAngle',"h"),('FocusRange',"H"),
            ('SignalLength',"I"),('Delay',"I"),
            ('CenterFrequency','I'),('Bandwidth',"H"),('SignalWaveformID','B'),
            ('TransmitSector#','B')])
        ntx_sz = ntx_dtype.itemsize
        ntx = self.header['Ntx']
        # declare nrx stuff
        nrx_dtype = np.dtype([('BeamPointingAngle',"h"),('Range',"H"),
            ('TransmitSectorID','B'),('Reflectivity',"b"),('QualityFactor','B'),
            ('DetectionWindowLength','B'),('BeamNumber','h'),('Spare','H')])
        nrx_sz = nrx_dtype.itemsize
        nrx = self.header['Nrx']
        # read ntx
        self.tx = np.frombuffer(datablock[:ntx * ntx_sz], 
            dtype = ntx_dtype)
        self.tx = self.tx.astype(Data102.ntx_dtype)
        self.tx['TiltAngle'] *= 0.01
        self.tx['FocusRange'] *= 0.1
        self.tx['SignalLength'] *= 10**-6
        self.tx['Delay'] *= 10**-6
        self.tx['Bandwidth'] *= 10
        # read nrx
        self.rx = np.frombuffer(datablock[ntx * ntx_sz:], dtype = nrx_dtype)
        self.rx = self.rx.astype(Data102.nrx_dtype)
        self.rx['BeamPointingAngle'] *= 0.01
        self.rx['Range'] *= 0.25
        self.rx['Reflectivity'] *= 0.5
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
class Data104:
    """
    Depth (pressure) or height datagram, 0x68h / 'h' / 104.  Height information
    is converted to meters.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('Height',"f"),('HeightType','B')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the record."""
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('Height',"i"),('HeightType','B')])
        self.header = np.frombuffer(datablock, dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data104.hdr_dtype)
        self.header['Height'] = 0.01 * self.header['Height']
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
            
class Data107:
    """
    The water column datagram, 6Bh / 107d / 'k'.  The receiver beams are roll
    stabilized.  Units have been shifted to whole units as in hertz, meters, 
    seconds, etc.  Watercolumn data is in ampdata as 0.5 dB steps.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('#OfDatagrams','H'),('Datagram#','H'),('#TxSectors','H'),
        ('Total#Beams','H'),('NumberBeamsInDatagram','H'),('SoundSpeed',"f"),
        ('SamplingFrequency',"d"),('TxHeave',"f"),('TVGfunction','B'),
        ('TVGoffset','b'),('ScanningInfo','B'),('Spare','3B')])
    ntx_dtype = np.dtype([('TiltTx',"f"),('CenterFrequency',"I"),
        ('TransmitSector#','B'),('Spare','B')])
    nrx_dtype = np.dtype([('BeamPointingAngle',"f"),('StartRangeSample#','H'),
        ('NumberSamples','H'),('DetectedRange','H'),('TransmitSector#','B'),
        ('Beam#','B')])
        
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('#OfDatagrams','H'),('Datagram#','H'),('#TxSectors','H'),
            ('Total#Beams','H'),('NumberBeamsInDatagram','H'),('SoundSpeed',"H"),
            ('SamplingFrequency',"I"),('TxHeave',"h"),('TVGfunction','B'),
            ('TVGoffset','b'),('ScanningInfo','B'),('Spare','3B')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data107.hdr_dtype)
        self.header['SoundSpeed'] *= 0.1
        self.header['SamplingFrequency'] *= 0.01
        self.header['TxHeave'] *= 0.01
        self.read(datablock[hdr_sz:])
        self.hasTVG = True
        
    def read(self, datablock):
        """
        Reads the variable section of the datagram.
        """
        # declare tx stuff
        ntx_dtype = np.dtype([('TiltTx',"h"),('CenterFrequency',"H"),
            ('TransmitSector#','B'),('Spare','B')])
        ntx_sz = ntx_dtype.itemsize    
        ntx = self.header[4]
        # declare rx stuff
        nrx_dtype = np.dtype([('BeamPointingAngle',"h"),
            ('StartRangeSample#','H'),('NumberSamples','H'),
            ('DetectedRange','H'),('TransmitSector#','B'),
            ('Beam#','B')])
        nrx_sz = nrx_dtype.itemsize
        nrx = self.header[6]
        self.rx = np.zeros(nrx, dtype = nrx_dtype)
        # declare amplitudes stuff
        numamp = len(datablock) - ntx_sz * ntx - nrx_sz * nrx
        amp_dtype = np.dtype([('SampleAmplitude',"b")])
        # Initialize array to NANs. Source:http://stackoverflow.com/a/1704853/1982894
        tempamp = np.empty(numamp, dtype = amp_dtype)
        tempamp[:] = np.NAN
        # get the tx data
        self.tx = np.frombuffer(datablock[:ntx*ntx_sz], dtype = ntx_dtype)
        p = ntx*ntx_sz
        self.tx = self.tx.astype(Data107.ntx_dtype)
        self.tx['TiltTx'] *= 0.01
        self.tx['CenterFrequency'] *= 10
        # get the rx and amplitude data
        pamp = 0
        for n in range(nrx):
            self.rx[n] = np.frombuffer(datablock[p:p+nrx_sz], 
                dtype = nrx_dtype)
            p += nrx_sz
            # the number of samples for this beam
            beamsz = self.rx[n][2]
            tempamp[pamp:pamp+beamsz] = \
                np.frombuffer(datablock[p:p+beamsz], dtype = amp_dtype)
            p += beamsz
            pamp += beamsz
        self.rx = self.rx.astype(Data107.nrx_dtype)
        self.rx['BeamPointingAngle'] *= 0.01
        # unwined the beam data into an array
        numsamples = self.rx['NumberSamples']
        self.ampdata = np.empty((numsamples.max(), nrx), dtype = np.float32)
        self.ampdata[:] = np.NAN
        pamp = 0
        for n in range(nrx):
            self.ampdata[:numsamples[n],n] = 0.5*tempamp[pamp:pamp+numsamples[n]].astype(np.float32)
            pamp += numsamples[n]
            
    def deTVG(self, absorption, OFS, usec = True):
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
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
    def plot(self):
        """
        Plots the watercolumn data.
        """
        a = self.rx['BeamPointingAngle']
        s = self.header['SoundSpeed']
        dt = self.header['SamplingFrequency']
        r = np.arange(len(self.ampdata)) * s / (2 * dt)
        A,R = np.meshgrid(a,r)
        # swap sides through -1 to make the negative angle be the positive direction
        X = -1*R * np.sin(np.deg2rad(A))
        Y = R * np.cos(np.deg2rad(A))
        plt.figure()
        im = plt.pcolormesh(X,Y,self.ampdata)
        plt.ylim((r.max(),0))
        c = plt.colorbar()
        c.set_label('dB re $1\mu Pa$ at 1 meter')
        plt.xlabel('Across Track (meters)')
        plt.ylabel('Depth (meters)')
        cstd = np.nanstd(self.ampdata)
        cmean = np.nanmean(self.ampdata)
        im.set_clim((cmean-3*cstd, cmean+3*cstd))
        plt.grid()
        plt.draw()
        
class Data109:
    """
    The Stave Data Datagram, 6Dh / 109d / 'm'.  This data definition does not
    exist in the normal documentation.  All values are converted to whole
    units.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('#Datagrams','H'),('Datagram#','H'),('RxSamplingFrequency',"f"),
        ('SoundSpeed',"f"),('StartRangeRefTx','H'),('TotalSample','H'),
        ('#SamplesInDatagram','H'),('Stave#','H'),('#StavesPerSample','H'),
        ('RangeToNormal','H'),('Spare','H')])
        
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('#Datagrams','H'),('Datagram#','H'),('RxSamplingFrequency',"I"),
            ('SoundSpeed',"H"),('StartRangeRefTx','H'),('TotalSample','H'),
            ('#SamplesInDatagram','H'),('Stave#','H'),('#StavesPerSample','H'),
            ('RangeToNormal','H'),('Spare','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz],
            dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data109.hdr_dtype)
        self.header['RxSamplingFrequency'] *= 0.01
        self.header['SoundSpeed'] *= 0.1
        self.read(datablock[hdr_sz:])
        
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
        read_dtype = np.dtype([('Sample#','H'),('TvgGain',"h"),
            ('StaveBackscatter',read_fmt)])
        read_sz = read_dtype.itemsize
        used_dtype = np.dtype([('Sample#','H'),('TvgGain',"f"),
            ('StaveBackscatter',read_fmt)])
        self.data = np.frombuffer(datablock[:Ns*read_sz],
            dtype = read_dtype)
        self.data = self.data.astype(used_dtype)
        self.data['TvgGain'] *= 0.01
        self.data['StaveBackscatter'] *= 0.5
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
        
        
class Data110:
    """
    The Network Attitiude Datagram, 6Eh / 110d / 'n'.  Data is found in the header
    and in the 'data' array.  All values are in degrees, and meters.  The raw
    data is parsed and placed in source_data.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('Serial#','H'),('NumEntries','H'),
        ('Sensor','B'),('Spare','B')])
    att_dtype = np.dtype([('Time','d'),('Roll','f'),('Pitch','f'),('Heave','f'),
        ('Heading','f'),('NumBytesInput','B')])
    
    def __init__(self, datablock, POSIXtime, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_sz = Data110.hdr_dtype.itemsize
        self.time = POSIXtime
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data110.hdr_dtype)[0]
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """Reads the data section of the record.  Time is POSIX time,
        angles are in degrees, distances in meters."""
        att_file_dtype = np.dtype([('Time','H'),('Roll','h'),('Pitch','h'),('Heave','h'),
            ('Heading','H'),('NumBytesInput','B')])
        att_sz = att_file_dtype.itemsize
        self.numrecords = self.header[2]

        raw_data_size = int((len(datablock) - 1)/ self.numrecords - att_sz)
        raw_data_dtype = np.dtype([('Raw','S' + str(raw_data_size))])
        read_dtype = np.dtype([('Proc', att_file_dtype),('Raw', raw_data_dtype)])
        temp = np.frombuffer(datablock[:self.numrecords * read_dtype.itemsize], dtype = read_dtype)
        self.data = temp['Proc'].astype(Data110.att_dtype)
        self._parse_raw(temp['Raw'])
        # self.data = np.zeros(self.numrecords, dtype = att_file_dtype)
        # datap = 0
        # for i in range(self.numrecords):
            # temp = np.frombuffer(datablock[datap:att_sz+datap],
                # dtype = att_file_dtype)
            # datap += att_sz + temp['NumBytesInput'][0]
            # self.data[i] = temp[['Time','Roll','Pitch','Heave', 'Heading']].astype(Data110.att_dtype)
        self.data['Time'] = self.data['Time'] * 0.001 + self.time
        self.data['Roll'] *= 0.01
        self.data['Pitch'] *= 0.01
        self.data['Heave'] *= 0.01
        self.data['Heading'] *= 0.01
        
    def _parse_raw(self, raw_data):
        """
        Parses the raw data that arrived in SIS and puts it in source_data.  If
        the data type is not known source_data is None.
        """
        if raw_data[0][0][0:4] == b'$GRP':
            source_dtype = np.dtype([('GroupStart','S4'),('GroupID','H'),
                ('ByteCount','H'),('Time1','d'),('Time2','d'),
                ('DistanceTag','d'),('TimeTypes','B'),('DistanceType','B'),
                ('Latitude','d'),('Longitude','d'),('Altitude','d'),
                ('AlongTrackVelocity','f'),('AcrossTrackVelocity','f'),
                ('DownVelocity','f'),('Roll','d'),('Pitch','d'),
                ('Heading','d'),('WanderAngle','d'),('Heave','f'),
                ('RollRate','f'),('PitchRate','f'),('YawRate','f'),
                ('LongitudinalAcceleration','f'),('TransverseAcceleration','f'),
                ('DownAcceleration','f'),('Pad','H'),('CheckSum','H'),
                ('MessageEnd','S2')])
            
            self.source_data = np.fromiter(raw_data, dtype = source_dtype, count = self.numrecords)
            packettime = dtm.datetime.utcfromtimestamp(self.time)
            # subtract 1 because the first day of the year does not start with zero
            ordinal = packettime.toordinal()
            dow = packettime.weekday() + 1.
            if dow == 7:
                # shift sunday to be start of week.
                dow = 0
            # 1970-1-1 is julian day 719163
            POSIXdays = ordinal - 719163. - dow
            self._weektime = POSIXdays * 24. * 3600.
            self.source = 'GRP102'
        elif raw_data[0][0][:2] == b'\xaaQ':
            source_dtype = np.dtype([('Header1','B'),('Header2','B'),
                ('Seconds','>i'),('FracSeconds','>H'),('Latitude','>i'),
                ('Longitude','>i'),('Height','>i'),('Heave','>h'),
                ('NorthVelocity','>h'),('EastVelocity','>h'),
                ('DownVelocity','>h'),('Roll','>h'),('Pitch','>h'),
                ('Heading','>H'),('RollRate','>h'),('PitchRate','>h'),
                ('YawRate','>h'),('StatusWord','>H'),('CheckSum','>H')])
            source_usetype = np.dtype([('Header1','B'),('Header2','B'),
                ('Seconds','i'),('FracSeconds','f'),('Latitude','f'),
                ('Longitude','f'),('Height','f'),('Heave','f'),
                ('NorthVelocity','f'),('EastVelocity','f'),
                ('DownVelocity','f'),('Roll','f'),('Pitch','f'),
                ('Heading','f'),('RollRate','f'),('PitchRate','f'),
                ('YawRate','f'),('StatusWord','H'),('CheckSum','H')])
            temp = np.fromiter(raw_data, dtype = source_dtype, count = self.numrecords)
            self.source_data = temp
            self.source_data = np.zeros(len(temp), dtype = source_usetype)
            self.source_data['Header1'] = temp['Header1']
            self.source_data['Header2'] = temp['Header2']
            self.source_data['Seconds'] = temp['Seconds']
            self.source_data['FracSeconds'] = 0.0001 * temp['FracSeconds'].astype(np.float32)
            self.source_data['Latitude'] = 90. / 2**30 * temp['Latitude'].astype(np.float32)
            self.source_data['Longitude'] = 90. / 2**30 * temp['Longitude'].astype(np.float32)
            self.source_data['Height'] = 0.01 * temp['Height'].astype(np.float32)
            self.source_data['Heave'] = 0.01 * temp['Heave'].astype(np.float32)
            self.source_data['NorthVelocity'] = 0.01 * temp['NorthVelocity'].astype(np.float32)
            self.source_data['EastVelocity'] = 0.01 * temp['EastVelocity'].astype(np.float32)
            self.source_data['DownVelocity'] = 0.01 * temp['DownVelocity'].astype(np.float32)
            self.source_data['Roll'] = 90. / 2**14 * temp['Roll'].astype(np.float32)
            self.source_data['Pitch']  = 90. / 2**14 * temp['Pitch'].astype(np.float32)
            self.source_data['Heading'] = 90. / 2**14 * temp['Heading'].astype(np.float32)
            self.source_data['RollRate']  = 90. / 2**14 * temp['RollRate'].astype(np.float32)
            self.source_data['PitchRate']  = 90. / 2**14 * temp['PitchRate'].astype(np.float32)
            self.source_data['YawRate']  = 90. / 2**14 * temp['YawRate'].astype(np.float32)
            self.source = 'binary23'
        elif raw_data[0][0][0] == b'q' and len(raw_data[0][0]) == 42:
            source_dtype = np.dtype([('Header','S1'),
                ('Seconds','>i'),('FracSeconds','>B'),('Latitude','>i'),
                ('Longitude','>i'),('Height','>i'),('Heave','>h'),
                ('NorthVelocity','>h'),('EastVelocity','>h'),
                ('DownVelocity','>h'),('Roll','>h'),('Pitch','>h'),
                ('Heading','>H'),('RollRate','>h'),('PitchRate','>h'),
                ('YawRate','>h'),('StatusWord','>H'),('CheckSum','>H')])
            source_usetype = np.dtype([('Header','S1'),
                ('Seconds','i'),('FracSeconds','f'),('Latitude','f'),
                ('Longitude','f'),('Height','f'),('Heave','f'),
                ('NorthVelocity','f'),('EastVelocity','f'),
                ('DownVelocity','f'),('Roll','f'),('Pitch','f'),
                ('Heading','f'),('RollRate','f'),('PitchRate','f'),
                ('YawRate','f'),('StatusWord','H'),('CheckSum','H')])
            temp = np.fromiter(raw_data, dtype = source_dtype, count = self.numrecords)
            self.source_data = np.zeros(len(temp), dtype = source_usetype)
            self.source_data['Header'] = temp['Header']
            self.source_data['Seconds'] = temp['Seconds']
            self.source_data['FracSeconds'] = 0.01 * temp['FracSeconds'].astype(np.float32)
            self.source_data['Latitude'] = 90. / 2**30 * temp['Latitude'].astype(np.float32)
            self.source_data['Longitude'] = 90. / 2**30 * temp['Longitude'].astype(np.float32)
            self.source_data['Height'] = 0.01 * temp['Height'].astype(np.float32)
            self.source_data['Heave'] = 0.01 * temp['Heave'].astype(np.float32)
            self.source_data['NorthVelocity'] = 0.01 * temp['NorthVelocity'].astype(np.float32)
            self.source_data['EastVelocity'] = 0.01 * temp['EastVelocity'].astype(np.float32)
            self.source_data['DownVelocity'] = 0.01 * temp['DownVelocity'].astype(np.float32)
            self.source_data['Roll'] = 90. / 2**14 * temp['Roll'].astype(np.float32)
            self.source_data['Pitch']  = 90. / 2**14 * temp['Pitch'].astype(np.float32)
            self.source_data['Heading'] = 90. / 2**14 * temp['Heading'].astype(np.float32)
            self.source_data['RollRate']  = 90. / 2**14 * temp['RollRate'].astype(np.float32)
            self.source_data['PitchRate']  = 90. / 2**14 * temp['PitchRate'].astype(np.float32)
            self.source_data['YawRate']  = 90. / 2**14 * temp['YawRate'].astype(np.float32)
            self.source = 'binary11'
        else:
            self.source_data = raw_data
            self.source = 'Unknown'
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print(name + ' : ' + str(self.header[n]))
            
class useall(allRead):
    """
    Built as a subclass of the allRead class to perform higher level functions.
    The file is mapped and the navigation array is built upon init.
    """
    def __init__(self, infilename, reload_map = True, save_filemap = True, 
                 verbose = False, byteswap = False):
        allRead.__init__(self,infilename,verbose,byteswap)
        if reload_map and os.path.exists(infilename + '.par'):
            self.loadfilemap(verbose = verbose)
        else:
            self.mapfile(show_progress = verbose)
            if save_filemap:
                self.savefilemap(verbose = verbose)
        
        if reload_map and os.path.exists(infilename + '.nav'):
            self.load_navarray(verbose)
        else:
            self._build_navarray(allrecords = True, verbose = verbose)
            if save_filemap:
                self.save_navarray(verbose)
        self.has_reported_error()
        self.installation_parameters = self.getrecord(73,0)
        self.reset()
        
    def has_reported_error(self, print_error = True):
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
        
    def is_dual_swath(self, POSIX = None):
        """
        Returns True or False depending on the flag set for the Mode in the
        runtime parameters record.  The information from the first runtime
        record is returned unless a POSIX time is provided.
        """
        if POSIX is None:
            runtime = self.getrecord(82,0)
        else:
            times = self.map.packdir['82'][:,1]
            idx = np.nonzero(times < POSIX)[0]
            # should probably be checking to make sure the length of idx > 0...
            runtime = self.getrecord(82,idx[-1])
        if (runtime.header['Mode'] & 192) == 0:
            return False
        else:
            return True
            
    def get_stats(self, display = True):
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
            ('Filename',fmt_lenfname),
            ('EMModel','<u2'),
            ('Mode','S8'),
            ('Mode2','S8'),
            ('BeamSpacing','S8'),
            ('YawAndPitchStabilization','S8'),
            ('AngularLimits','<u2',2),
            ('FilterID2','S8'),
            ('OperatorStationStatus','S4'),
            ('ProcessingUnitStatus','S4'),
            ('BSPStatus','S4'),
            ('SonarHeadOrTransceiverStatus','S4'),
            ('Speed','f',2),
            ('Heading','f',2),
            ('Roll','f'),
            ('Pitch','f'),
            ('Heave','f'),
            ('Times','d',2),
            ('Latitude','f',2),
            ('Longitude','f',2),
            ('Depth','f',2),
            ('ModeChange','b'),
            ('CastTime','S16'),
            ('NewCastNumber','B'),
            ('NumberOfPings','I')])
        info = np.zeros(1, dtype = stat_dtype)[0]
        info['Filename'] = self.infilename[:lenfname]
        s = self.getrecord(85,0)
        info['EMModel'] = self.packet.header['Model']
        t = dtm.datetime.utcfromtimestamp(s.POSIXtime)
        info['CastTime'] = t.strftime('%Y-%m-%d %H:%M')
        self._build_sscast_array()
        numcasts = len(np.nonzero(s.POSIXtime != self._sscast_array['Time'])[0])
        info['NewCastNumber'] = numcasts
        r = self._runtime_array['RuntimePacket']
        info['Mode'] = np.binary_repr(r['Mode'][0],8)
        info['Mode2'] = np.binary_repr(r['ReceiverFixedGain'][0],8)
        info['BeamSpacing'] = np.binary_repr(r['BeamSpacing'][0],8)
        info['YawAndPitchStabilization'] = np.binary_repr(r['YawAndPitchStabilization'][0],8)
        info['AngularLimits'] = np.array([r['MaxPortCoverage'][0],r['MaxStarboardCoverage'][0]], dtype = 'u2')
        info['FilterID2'] = np.binary_repr(r['HiLoFrequencyAbsorptionCoeffRatio'][0],8)
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
        info['Speed'] = np.array([np.nanmean(self.speedarray[:,1]),np.nanstd(self.speedarray[:,1])])
        att = self.navarray['65']
        info['Heading'] = np.array([att[:,-1].mean(), att[:,-1].std()])
        info['Roll'] = att[:,1].std()
        info['Pitch'] = att[:,2].std()
        info['Heave'] = att[:,3].std()
        info['Times'] = np.array([att[0,0],att[-1,0]])
        nav = self.navarray['80']
        info['Latitude'] = np.array([nav[:,2].min(),nav[:,2].max()])
        info['Longitude'] = np.array([nav[:,1].min(),nav[:,1].max()])
        try:
            depths = self.build_bathymetry()
            numpings, numbeams = depths[:,:,0].shape
            centerbeam = int(numbeams/2)
            centerdata = depths[:,centerbeam,0]
            info['Depth'] = np.array([centerdata.mean(),centerdata.std()])
            info['NumberOfPings'] = self.map.getnum(88)
        except KeyError:
            info['Depth'] = np.array([np.nan,np.nan])
            if '107' in self.map.packdir:
                info['NumberOfPings'] = self.map.numwc
        if display:
            for n,name in enumerate(info.dtype.names):
                print(name + ' : ' + str(info[n]))
        return info
        
    def plot_wobbles(self, which_swath = 0, heavefile = None, use_height = False, make_plot = 1):
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
            numrec = len(self.map.packdir['88'])/2
        else:
            step = 1
            numrec = len(self.map.packdir['88'])
            
        # get installation parameters
        ip = self.getrecord(73,0)
        wline = float(ip.settings['WLZ'])
        # get information on data sizes 
        p78 = self.getrecord(78,0)
        numtx = p78.header['Ntx']
        numrx = p78.header['Nrx']
        # allocate space
        depth88 = np.zeros((numrec,numrx))
        across88 = np.zeros((numrec,numrx))
        txnum = np.zeros((numrec,numrx), dtype = np.int)
        txheave = np.zeros(numrec)
        txpitch = np.zeros((numrec,numtx))
        txpitchvel = np.zeros((numrec,numtx))
        txtime = np.zeros((numrec,numtx))
        rectime = np.zeros(numrec)
        rxtime = np.zeros((numrec,numrx))
        rxroll = np.zeros((numrec,numrx))
        rxrollvel = np.zeros((numrec,numrx))
            
        # get the 78 record for rx times and sector numbers
        k = which_swath
        for n in range(numrec):
            p78 = self.getrecord(78,k)
            rectime[n] = self.packet.gettime()
            txnum[n,:] = p78.rx['TransmitSectorID']
            # just getting the rx time/roll for the middle of each swath for speed!
    #        idx = np.zeros(numtx, dtype = np.int)
    #        for m in range(numtx):
    #            ids = np.nonzero(txnum[n,:] == m)[0]
    #            idm = ids.mean() # this is roughly the middle of each swath
    #            idx[m] = idm.astype(np.int)
            rxtimes = p78.get_rx_time()
            rxtime[n,:] = rxtimes # [idx]
            # getting the txtimes and pitch
            txdelay = p78.tx['Delay'].astype(np.float64)
            txtime[n,:] = p78.pingtime + txdelay
            k += step
        
        print('getting motion,', end=' ')
        # get all the attitude information
        att = self.navarray['65']
        attvel = self.navarray['110'] # this comes from the POS102 datagram inside the attitude
        # gettting this information for all times but by sector
        for n in range(numtx):
            txpitch[:,n] = np.interp(txtime[:,n], att[:,0], att[:,1], left = np.nan, right = np.nan)
            txpitchvel[:,n] = np.interp(txtime[:,n], attvel[:,0], attvel[:,7], left = np.nan, right = np.nan)
        for n in range(numrx):
            rxroll[:,n] = np.interp(rxtime[:,n], att[:,0], att[:,1], left = np.nan, right = np.nan)
            rxrollvel[:,n] = np.interp(rxtime[:,n], attvel[:,0], attvel[:,6], left = np.nan, right = np.nan)
        recheavevel = np.interp(rectime, attvel[:,0], attvel[:,-1], left = np.nan, right = np.nan)

        # get the height data if available
        if '104' in self.navarray:
            rawheight = self.navarray['104']
            
        # get the depth, along track and heave data
        k = which_swath
        for n in range(numrec):
            p88 = self.getrecord(88,k)
            if use_height and '104' in self.navarray:
                # using the txtime from the first sector for heave!!!
                x_arm = float(ip.settings['S1X'])
                y_arm = float(ip.settings['S1Y'])
                txroll = np.interp(txtime[n,0], att[:,0], att[:,1], left = np.nan, right = np.nan)
                induced_heave = x_arm * sin(np.deg2rad(txpitch[n,0])) + y_arm * sin(np.deg2rad(txroll))
                height = np.interp(txtime[n,0], rawheight[:,0], rawheight[:,1], left = np.nan, right = np.nan)
                depth88[n,:] = p88.data['Depth'] - height - induced_heave
            else:
                txheave[n] = p88.header['TransmitDepth'] + wline
                depth88[n,:] = p88.data['Depth'] + txheave[n]
                
            across88[n,:] = p88.data['AcrossTrack']
            k += step
        
        # get the true heave from a numpy array file with columns [time,realtime,delayed]
        dh = np.zeros(len(txheave))
        if heavefile is not None and not use_height:
            posheave = np.load(heavefile)
            heavediff = posheave[:,1] - posheave[:,2]
            dh = np.interp(rectime, posheave[:,0], heavediff, left = np.nan, right = np.nan)
            if np.any(np.isnan(dh)):
                print('\n***Warning: Delayed Heave is not applied since it is not in correct time range for all file.***')
        txheave += dh
        dh.shape = (-1,1)

        # get the water column data if available
        if '107' in self.map.packdir:
            # assuming the same number of XYZ88 and water column records...
            have_wc = True
            wcr = self.getwatercolumn(n)
            wc = np.zeros((numrec,wcr.header['Total#Beams']))
            for n in range(numrec):
                wcr = self.getwatercolumn(n)
                maxrange = wcr.rx['DetectedRange'].min()-2
                ampdata = wcr.ampdata[:maxrange,:].astype(np.float64)
                ampdata = 10**(ampdata/10.)
                ampmean = ampdata.mean(axis = 0)
                wc[n,:] = 10*np.log10(ampmean)
        else:
            have_wc = False

        # apply true heave before filtering
        depth88 = depth88 - dh
        
        # Begin bathymetry processing
        print('filtering bathymetry,', end=' ')
        # Establish the bathymetry filter using the motion time series
        t = att[:,0]
        dt = (t[1:] - t[:-1]).mean()
        freq = fft.fftfreq(len(t),dt)
        roll = att[:,1]
        pitch = att[:,2]
        roll_fft = fft.fft(roll)
        pitch_fft = fft.fft(pitch)
        max_freq_idx = np.array([roll_fft.argmax(),pitch_fft.argmax()]).max()
        max_freq = np.abs(freq[max_freq_idx])
        # setting the filter length to four times the max response per JHC p.22
        filtertime = 4/max_freq 
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
        ping_period = (txtime[1:,0] - txtime[:-1,0]).mean()
        # Set ping filter length based motion time series
        filter_len = int(filtertime / ping_period)
        print('Filter length set to ' + str(filter_len) + ' seconds.', end=' ')
        # data at the edges that is not filtered properly and not to be included in analysis
        rem = int(filter_len / 2)
        # Check to see if ping rate is high enough to support this analysis
        motion_to_ping_ratio = 1/(max_freq * ping_period)
        print('Motion period to ping period ratio is ' + str(motion_to_ping_ratio.round()))
        # this threshold is suggested by the JHC paper (p.6)
        if motion_to_ping_ratio < 10:
            print('***Warning: the ping rate may not capture the motion time series properly for this analysis.***')
        # build the window and filter the data
        win = np.hanning(filter_len)
        win /= win.sum()
        low_pass = np.zeros(depth88.shape)
        for n in range(numrx):
            low_pass[:,n] = np.convolve(depth88[:,n], win, mode='same')
        if filter_len > 1:
            high_pass = depth88 - low_pass
        else:
            high_pass = depth88
        # adjust the attitude range
        if rem == 0:
            rem = 1
        txheave = txheave[rem:-rem].astype(np.dtype([('Heave (m)',np.float)]))
        txpitch = txpitch[rem:-rem,:].astype(np.dtype([('Pitch (deg)',np.float)]))
        txpitchvel = txpitchvel[rem:-rem,:].astype(np.dtype([('Pitch Rate (deg/s)',np.float)]))
        txtime = txtime[rem:-rem].astype(np.dtype([('TX Time (s)',np.float)]))
        rxtime = rxtime[rem:-rem,:].astype(np.dtype([('RX Time (s)',np.float)]))
        rxroll = rxroll[rem:-rem,:].astype(np.dtype([('Roll (deg)',np.float)]))
        rxrollvel = rxrollvel[rem:-rem,:].astype(np.dtype([('Roll Rate (deg/s)',np.float)]))
        recheavevel = recheavevel[rem:-rem].astype(np.dtype([('Heave Rate (m/s)',np.float)]))
        # identify which beam is in which sector.  Remove the ones that switch sector
        beamtx = txnum.mean(axis = 0)      
        
        # regress the "good" data range
        print('Regressing swaths and beams,', end=' ')
        good_data_range = numrec-2*rem
        # first over the swath
        mainswath_slope = np.zeros((good_data_range), dtype = np.dtype([('Swath Slope (deg)',np.float)]))
        swath_mean = np.zeros((good_data_range), dtype = np.dtype([('Swath Mean (deg)',np.float)]))
        sector_slope = np.zeros((good_data_range,numtx), dtype = np.dtype([('Sector Slope (deg)',np.float)]))
        sector_mean = np.zeros((good_data_range,numtx), dtype = np.dtype([('Sector Mean (deg)',np.float)]))
        for n in range(good_data_range):
            if not np.all(np.isnan(high_pass[rem+n,:])):
                result = np.polyfit(across88[rem+n,:], high_pass[rem+n,:],1)
                swath_mean[n] = result[1]
                mainswath_slope[n] = 180. * np.arctan(result[0])/np.pi
                for m in range(numtx):
                    txid = np.nonzero(txnum[rem+n,:] == m)[0]
                    if len(txid) > 0:
                        result = np.polyfit(across88[rem+n,txid], high_pass[rem+n,txid],1)
                        sector_mean[n,m] = result[1]
                        sector_slope[n,m] = 180. * np.arctan(result[0])/np.pi
        # This section correlates a time delay by beam
        # The bias angle (flat seafloor, as in low passed, minus original) is computed and
        # regressed against the roll rate.
        along_mean = np.zeros(numrx, dtype = np.dtype([('Beam Angle Bias to Roll Rate Mean',np.float)]))
        along_slope = np.zeros(numrx, dtype = np.dtype([('Beam Angle Bias to Roll Rate Slope',np.float)]))
        along_residuals = np.zeros(numrx, dtype = np.dtype([('Beam Angle Bias to Roll Rate Residual',np.float)]))
        # find the angles
        orig_angle = 180. / np.pi * np.arctan2(depth88,across88)
        # see notes in green book from 20160208
        depths = low_pass.mean(axis = 1)
        depths = np.tile(depths, [numrx,1])
        range_at_angle = np.sqrt(across88**2 + depths.T**2)
        bias_angle = orig_angle - 180. / np.pi * np.arccos(low_pass / (range_at_angle - high_pass/np.cos(orig_angle)))
        bias_angle = bias_angle[rem:-rem, :]
        # for each beam, fit a line to corralate the angle bias to the roll rate
        for n in range(numrx):
            if np.any(np.isnan(bias_angle)):
                idx = np.nonzero(~np.isnan(bias_angle[:,n]))[0]
            else:
                idx = np.arange(good_data_range)
            xtemp = rxrollvel[idx,n].astype(np.float)
            ytemp = bias_angle[idx,n]
            # the fit
            result = np.polyfit(xtemp, ytemp, 1)
            along_mean[n] = result[1]
            along_slope[n] = result[0]
            # find the residuals
            linefunc = np.poly1d(result)
            bias_estimate = linefunc(xtemp)
            along_residuals[n] = np.std(bias_estimate - ytemp)
        bias_angle = bias_angle.astype(np.dtype([('Beam Angle Bias (Deg)',np.float)]))

            
        # plot the bathymetry
        print('plotting,', end=' ')
        fig = plt.figure()
        fig.suptitle('Hanning filter Length of ' + str(filter_len))
        ax1 = fig.add_subplot(141)
        im1 = ax1.imshow(depth88[rem:-rem,:], aspect = 'auto', interpolation = 'none')
        ax1.set_title('XYZ88 Depth')
        plt.colorbar(im1)
        ax2 = fig.add_subplot(142, sharex = ax1, sharey = ax1)
        im2 = ax2.imshow(low_pass[rem:-rem,:], aspect = 'auto', interpolation = 'none')
        ax2.set_title('Low Pass Depth')
        plt.colorbar(im2)
        ax3 = fig.add_subplot(122, sharex = ax1, sharey = ax1)
        im3 = ax3.imshow(high_pass[rem:-rem,:], aspect = 'auto', interpolation = 'none')
        hp_mean = np.nanmean(high_pass[rem:-rem,:])
        hp_std = np.nanstd(high_pass[rem:-rem,:])
        im3.set_clim((hp_mean - hp_std, hp_mean + hp_std))
        im3.set_cmap('gray')
        ax3.set_title('High Pass Depth')
        plt.colorbar(im3)
        ax4 = ax3.twinx()
        ax4.grid(color = 'r', linestyle = '-', linewidth = '2')
        ax4.patch.set_alpha(0)
        ax4.set_zorder(1)
        
        # plot scatter plots
        if make_plot & 1:
            self._plot_wobble_scatter(rxrollvel[:,numrx/2], mainswath_slope, title = 'Roll Rate vs Swath Slope')
        #self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,0], title = 'Roll Rate vs Sector 0 Slope')
        #self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,1], title = 'Roll Rate vs Sector 1 Slope')
        #self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,2], title = 'Roll Rate vs Sector 2 Slope')
#        self._plot_wobble_scatter(rxrollvel[:,numrx/2], sector_slope[:,7], title = 'Roll Rate vs Sector 7 Slope')
        #self._plot_wobble_scatter(recheavevel, swath_mean, title = 'Heave Rate vs Swath Mean')
        #self._plot_wobble_scatter(txheave, swath_mean, title = 'Heave vs Swath Mean')
#        self._plot_wobble_scatter(txpitchvel[:,1], swath_mean, title = 'Pitch Rate vs Swath Mean')
#        self._plot_wobble_scatter(txpitch, swath_mean, title = 'Pitch vs Swath Mean')

        # plot the along track fits
        beams = np.arange(numrx)
        temp = 180. / np.pi * np.arctan2(low_pass[rem:-rem,:], across88[rem:-rem, :]) - 90
        pointing_angles = temp.mean(axis = 0).astype(np.dtype([('Pointing Angle (Deg)',np.float)]))
        beams = beams.astype(np.dtype([('Beam Number',np.float)]))
        across_mean_range = across88.mean(axis = 0)
        across_mean_range = across_mean_range.astype(np.dtype([('Across Track Range (m)',np.float)]))
        #self._plot_wobble_scatter(pointing_angles, along_slope, title = 'Beam Angular Bias to Roll Rate Slope Fit vs Across Track Distance', txid = beamtx)
        #self._plot_wobble_scatter(beams, along_mean, title = 'Interept of fit to Roll Rate vs Beam Number')

        # plot a single beam's roll rate vs bias to demonstrate where the regressed plots come from.
        #beam = 20
        #self._plot_wobble_scatter(rxrollvel[:,beam], bias_angle[:,beam], title = 'Regressing beam ' + str(beam) + ' Roll Velocity vs Angular Bias')
        print('done!')
        # np.savez('angles',across = across88[rem:-rem,:],lowpass = low_pass[rem:-rem,:])
        
    def _plot_wobble_scatter(self, data1, data2, title = '', fit = True, mean = False, txid = None, residual = None):
        """
        Takes in two one dimensional record numpy arrays and plots them as
        a scatter plot.  A fit line can also be added.
        """
        plt.figure()
        name1 = data1.dtype.names[0]
        name2 = data2.dtype.names[0]
        if residual is None:
            plt.plot(data1,data2,'b.')
        else:
            plt.errorbar(data1[name1], data2[name2], yerr = residual.astype('float'))
        plt.xlabel(name1)
        plt.ylabel(name2)
        plt.grid()
        # working around nan values for the fit
        idx = np.nonzero(~np.isnan(data2[name2]))[0]
        if fit:
             result, covarmat= np.polyfit(data1[name1][idx], data2[name2][idx], 1, cov = True)
             linefunc = np.poly1d(result)
             xmin = data1[name1].min()
             xmax = data1[name1].max()
             xdata = np.array([xmin,xmax])
             ydata = linefunc(xdata)
             plt.plot(xdata,ydata,'g-')
             s = 'Slope: {:0.2e} +/- {:0.2e}'.format(result[0],np.sqrt(covarmat[0,0]))
             title = title + '\n' + s
             if txid is not None:
                 # dealing with the beams that switch sectors
                 idx = np.nonzero(txid%1==0)[0]
                 txvals = set(txid[idx])
                 for n in txvals:
                     idx = np.nonzero(txid == n)
                     result= np.polyfit(data1[name1][idx], data2[name2][idx],1)
                     linefunc = np.poly1d(result)
                     xmin = data1[name1][idx].min()
                     xmax = data1[name1][idx].max()
                     xdata = np.array([xmin,xmax])
                     ydata = linefunc(xdata)
                     plt.plot(xdata,ydata,'r-')
                     s = '%0.2e' %result[0]
                     title = title + ', txid ' + str(int(n)) + ' slope: ' + s
        if mean:
            result= np.polyfit(data1[name1], data2[name2],1)
            linefunc = np.poly1d(result)
            xmin = data1[name1].min()
            xmax = data1[name1].max()
            ymean = data2[name2].mean()
            plt.hlines(ymean,xmin,xmax,colors = 'g')
            s = 'Mean: %0.2e' %ymean
            title = title + '\n' + s
            if txid is not None:
                # dealing with the beams that switch sectors
                idx = np.nonzero(txid%1==0)[0]
                txvals = set(txid[idx])
                for n in txvals:
                    idx = np.nonzero(txid == n)
                    ymean = data2[name2][idx].mean()
                    xmin = data1[name1][idx].min()
                    xmax = data1[name1][idx].max()
                    plt.hlines(ymean,xmin,xmax, colors = 'r')
                    s = '%0.2e' %ymean
                    title = title + ', txid ' + str(int(n)) + ' M: ' + s
        plt.title(title)
        plt.draw()
        
    def build_bathymetry(self, apply_tx_depth = True):
        """
        Build and return a numpings by numbeams by 3 array of the xyz88
        depths, acrosstrack and alongtrack offsets.  The transmit depth
        is added to the bathymetry.
        """
        num88 = self.map.getnum(88)
        d = self.getrecord(88,0)
        numbeams = d.header['NumBeams']
        vals = np.zeros((num88,numbeams,3))
        for n in np.arange(num88):
            d = self.getrecord(88,n)
            if apply_tx_depth:
                vals[n,:,0] = d.data['Depth'] + d.header['TransmitDepth']
            else:
                vals[n,:,0] = d.data['Depth']
            vals[n,:,1] = d.data['AcrossTrack']
            vals[n,:,2] = d.data['AlongTrack']
        return vals
    
    def position_XYZ(self, pingnumber, vertical_reference = 'ellipsoid',
                     ellipsoid = 'WGS84'):
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
        dtype = np.dtype([('Beam','H'),
                          ('Longitude','d'),
                          ('Latitude','d'),
                          ('Depth','f')])
        # resolve the vertical
        ip = self.installation_parameters
        p = self.getrecord(88, pingnumber)
        t = self.packet.gettime()
        if vertical_reference == 'ellipsoid':
            m = self.getnav(t, postype = 'GGK')[0]
            v = m[7]
        elif vertical_reference == 'waterline':
            v = p.header['TransmitDepth']
            m = self.getnav(t)[0]
        elif vertical_reference == 'transducer':
            m = self.getnav(t)[0]
            v = 0
        # acount for pitch induced heave, using the time stamp of the record...
        if np.any(np.isnan(m)):
            out = np.zeros(1,dtype = dtype)
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
            r = np.sqrt(p.data['AcrossTrack'][beams]**2 + 
                        p.data['AlongTrack'][beams]**2)
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
            g = pyproj.Geod(ellps = 'WGS84')
            pos = g.fwd(lon,lat,az,r)
            out = np.zeros(len(beams),dtype = dtype)
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
        
        subpacks = self.getping(pingnumber = pingnumber, 
                                recordlist = ['78','88','89'], extra = False)
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
            txwx,rxwx = self.getruntime(ping78.pingtime, ['TransmitBeamWidth'
                ,'ReceiveBeamWidth'])
            txwx,rxwx = np.deg2rad([txwx,rxwx])
           
            # compute the lambertian avg
            rs = r * sr # two way range sample number
            rco = rtn/np.cos(ping89.header['TVGCrossover'] * np.pi/180)
            dbs = bso - bsn
            # calculate the BSo value for all ranges
            lamb = 20*np.log10(rtn/rs)
            # add the BSn adjustment for the ranges in the BSn regime
            if dbs != 0:
                bsn_idx = np.nonzero(rs < rco)[0]
                delta_samp = rs[bsn_idx]-rtn
                # deal with samples that are just under the range to normal
                ds_idx = np.nonzero(delta_samp < 0)[0]
                if len(ds_idx) > 0:
                    delta_samp[ds_idx] = 0
                lamb[bsn_idx] = lamb[bsn_idx] + dbs*(1 - np.sqrt((delta_samp)/(rco-rtn)))

            # compute the beam foot print
            pulse = pulse[txnum].squeeze()
            pulselen = pulse[txid]
            rn2 = (rtn / sr)**2 # range to normal squared as twtt
            footprint = rxwx * txwx * (r*c/2)**2 # An from document
            rn2_div_r2 = rn2/r**2
            div_idx = np.nonzero(rn2_div_r2 > 1)[0]
            if len(div_idx) > 0:
                rn2_div_r2[div_idx] = 1 - 2**(-50) # making this number just less than one
            footo = c**2*pulselen*txwx*r/2/np.sqrt(1-rn2_div_r2) # A0 from document
            # finding the crossover from An to Ao is documented differently
            A0_idx = np.nonzero(footprint > footo)[0]
            footprint[A0_idx] = footo[A0_idx]
            footprint = 10*np.log10(footprint)
            return footprint, lamb
        else:
            print("ping number is not valid.")
            return None, None            
            
    def buildBS89center(self, useinvalid = False, filter_3std = True, footprint = True, lambertian = True):
        """
        Build an array of all the center snippets from all 89 datagrams.  Any
        values that are less than -200 are set to nan.
        Need to confirm if the direction needs to be flipped.
        """
        if '89' in self.map.packdir:
            num89 = len(self.map.packdir['89'])
            # assuming that if 89 exists so does 88...
            ping88 = self.getrecord(88,0)
            numbeams = ping88.header['NumBeams']
            bs89 = np.zeros((num89,numbeams)) + np.nan
            for n in range(num89):
                ping89 = self.getrecord(89,n)
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
                bs89[n,:] = samples
            if filter_3std:
                bsm = bs89.mean()
                bsd = bs89.std()
                idx = np.nonzero((bs89 < bsm - bsd * 3) | (bs89 > bsm + bsd * 3))
                bs89[idx[0],idx[1]] = np.nan
                print("Data was filtered to be between " + str(bsm - bsd * 3) + " and " + str(bsm + bsd * 3) + "dB.")
            return bs89
        else:
            print("No 89 datagram found")
            return None

    def buildBS78(self, useinvalid = False, footprint = True):
        """
        Builds an array of all the Reflectivity from the 78 datagrams and
        returns it.
        """
               
        if '78' in self.map.packdir:
            num78 = len(self.map.packdir['78'])
            ping78 = self.getrecord(78,0)
            numbeams = ping78.header['Nrx']
            bs78 = np.zeros((num78,numbeams))
            for n in range(num78):
                ping78 = self.getrecord(78,n)
                bs78[n,:] = ping78.rx['Reflectivity']
                if not useinvalid:
                    detect = ping78.rx['DetectionInfo']
                    idx = np.nonzero(detect > 127)[0]
                    bs78[n,idx] = np.nan
            return bs78
        else:
            print("No 78 datagram found.")
            
    def plot_bs(self, bs, bs_range = 3):
        """
        Plots the provided backscatter imagry.
        """
        bs_std = np.nanstd(bs)
        bs_mean = np.nanmean(bs)
        bs_min = bs_mean - bs_range * bs_std
        bs_max = bs_mean + bs_range * bs_std
        plt.figure()
        plt.imshow(bs, aspect = 'auto', cmap = 'gray', clim = (bs_min, bs_max))
        cbar = plt.colorbar()
        cbar.set_label('dB re $1\mu Pa$ at 1 meter')
        ax = plt.gca()
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_ylabel('Along track')
        ax.set_xlabel('Across track')
        plt.draw()
            
    def build_BSCorr_info(self, which_swath = 0, plot_bs = False, lambertian = True):
        """
        This method gets all the backscatter from the file, bins the data in
        'step' sized bins by sector, and then gets a linear average for each
        bin.  The returned values are the averaged bin values, the counts per
        bin, and the center angles for each bin.
        """
        # find if the system is reverse mounted so roll is applied correctly
        ping73 = self.getrecord(73,0)
        S2R = float(ping73.settings['S2R'])
        # S2H = float(ping73.settings['S2H'])
        #S1H = float(ping73.settings['S1H'])
        #yaw = (S2H + S1H) % 180
        #yaw = S1H % 180
        #if abs(yaw) > 90:
            # the system is reverse mounted
        #    S2R *= -1
        print("Getting backscatter...")
        bs = self.buildBS89center(lambertian = lambertian)
        if plot_bs:
            self.plot_bs(bs)
        # determine dual swath
        if self.is_dual_swath():
            step = 2
            bs = bs[which_swath::2,:]
        else:
            step = 1
        txid = np.zeros(bs.shape)
        beam_angle = np.zeros(bs.shape) # relative to vertical
        num78,temp = bs.shape
        ping78 = self.getrecord(78,0)
        sectors = ping78.tx['TransmitSector#']
        print("Getting sector and angle information:          ", end=' ')
        k = which_swath
        progress = 0
        for n in range(num78):
            ping78 = self.getrecord(78,k)
            rxtimes = ping78.get_rx_time()
            roll = self.getnav(rxtimes)[:,3] # in degrees
            txid[n,:] = ping78.rx['TransmitSectorID']
            beam_angle[n,:] = ping78.rx['BeamPointingAngle'] + roll + S2R
            k += step
            temp = np.round((n * 100.)/num78)
            if  temp > progress:
                progress = temp
                print('\b\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress}, end=' ')
        print('\n')
        print("Sorting backscatter by angle", end=' ')
        angle_width = 1
        angles = np.arange(-80.5,80.5,angle_width)
        bp = np.zeros((len(angles),len(sectors)))
        count = np.zeros(bp.shape)
        for m,s in enumerate(sectors):
            sector_idx = np.nonzero(txid == s)
            b = bs[sector_idx[0],sector_idx[1]].astype(np.float64)
            sector_angles = beam_angle[sector_idx[0],sector_idx[1]]
            for n,a in enumerate(angles):
                a_idx = np.nonzero((a<sector_angles) & (a+angle_width>sector_angles))[0]
                if len(a_idx) > 0:
                    vals = 10**(b[a_idx]/10)
                    bp[n,m] = 10 * np.log10(np.nanmean(vals))
                    count[n,m] = len(a_idx)
                else:
                    bp[n,m] = np.nan
                # print '.',
            print('\nFinished Sector ' + str(s), end=' ')
        print("\nDone!")
        return bp,count,angles+angle_width/2.
            
    def plot_all_BIST_noise(self, xticklabels = []):
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
            p66 = self.getrecord(66,n)
            if p66.testtype == 'ChannelNoise':
                t = self.packet.gettime()
                noisetests.append([n,t])
            elif p66.testtype == 'NoiseSpectrum':
                t = self.packet.gettime()
                spectests.append([n,t])
        numnoise = len(noisetests)
        numspec = len(spectests)
        num66 = self.map.getnum(66)
        if p66._model == 2040:
            # Get some information about the noise datagram.
            self.getrecord(66,noisetests[0][0])
            self.packet.subpack.parse()
            label = self.packet.subpack.label
            datashape = self.packet.subpack.data.shape
            # Go through all tests and extract the noise data
            allnoise = np.zeros((numnoise,datashape[0],datashape[1]))
            allnoise[:,:,:] = np.nan
            for n in range(numnoise):
                self.getrecord(66,noisetests[n][0])
                self.packet.subpack.parse()
                allnoise[n,:,:] = self.packet.subpack.data
            speed = self.getspeed(np.array(noisetests)[:,1])
            speed = speed.astype(np.int)
            # Find the color range for the plots
            cmax = allnoise.max()
            cmin = allnoise.min()
            # set up the xticks
            if xticklabels == []:
                xticklabels = list(set(speed))
            spacing = len(speed) / len(xticklabels)
            xticks = list(range(spacing/2, len(speed), spacing))
            # Plot the data
            fig,ax = plt.subplots(len(label),1)
            for n,a in enumerate(ax):
                c = a.pcolormesh(allnoise[:,:,n].T)
                c.set_clim((cmin,cmax))
                a.set_ylabel('Channel (#)')
                a.set_ylim((0,allnoise.shape[1]))
                a.set_xlim((0,allnoise.shape[0]))
                a.set_title(label[n])
            self.packet.subpack.parse()
            label = self.packet.subpack.label
            datashape = self.packet.subpack.data.shape
            # Go through all tests and extract the noise data
            allnoise = np.zeros((numnoise,datashape[0],datashape[1]))
            allnoise[:,:,:] = np.nan
            for n in range(numnoise):
                self.getrecord(66,noisetests[n][0])
                self.packet.subpack.parse()
                allnoise[n,:,:] = self.packet.subpack.data
            speed = self.getspeed(np.array(noisetests)[:,1])
            speed = speed.astype(np.int)
            # Find the color range for the plots
            cmax = allnoise.max()
            cmin = allnoise.min()
            # set up the xticks
            if xticklabels == []:
                xticklabels = list(set(speed))
            spacing = len(speed) / len(xticklabels)
            xticks = list(range(spacing/2, len(speed), spacing))
            # Plot the data
            fig,ax = plt.subplots(len(label),1)
            for n,a in enumerate(ax):
                c = a.pcolormesh(allnoise[:,:,n].T)
                c.set_clim((cmin,cmax))
                a.set_ylabel('Channel (#)')
                a.set_ylim((0,allnoise.shape[1]))
                a.set_xlim((0,allnoise.shape[0]))
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
            p66 = self.getrecord(66,noisetests[0][0])
            p66.parse()
            numchannels = len(p66.data.flatten())
            allnoise = np.zeros((numnoise,numchannels))
            allnoise[:,:] = np.nan
            if numspec > 0:
                p66 = self.getrecord(66,spectests[0][0])
                p66.parse()
                numfreqs = len(p66.data.flatten())
                allspec = np.zeros((numspec,numfreqs))
                for n in range(numspec):
                    p66 = self.getrecord(66,spectests[n][0])
                    p66.parse()
                    allspec[n,:] = p66.data.flatten()
                freq = [str(x) for x in p66.freq]
                c2max = allspec.max()
                c2min = allspec.min()
            # Go through all tests and extract the noise data
            for n in range(numnoise):
                p66 = self.getrecord(66,noisetests[n][0])
                p66.parse()
                allnoise[n,:] = p66.data.flatten()

            # Find the color range for the plots
            cmax = allnoise.max()
            cmin = allnoise.min()
            # set up the xticks
            if xticklabels == []:
                speed = self.getspeed(np.array(noisetests)[:,1])
                speed = speed.astype(np.int)
                xticklabels = list(set(speed))
                xlabel = 'Meters per Second'
                xspacing = len(speed) / len(xticklabels)
                xticks = list(range(xspacing/2, len(speed), xspacing))
            elif len(xticklabels) == 1:
                xlabel = 'Alongside'
                xticks = []
                xticklabels = []
            # Plot the data            
            fig = plt.figure()
            ax = fig.add_subplot(111)
            c = ax.pcolormesh(allnoise.T)
            c.set_clim((cmin,cmax))
            ax.set_ylabel('Channel (#)')
            ax.set_ylim((0,allnoise.shape[1]))
            ax.set_xlim((0,allnoise.shape[0]))
            ax.set_xticks([])
            ax.set_xticks(xticks)
            ax.set_xticklabels(xticklabels)
            ax.set_xlabel(xlabel)
            ax.set_title(('All Noise Level Tests'))
            bar = fig.colorbar(c, ax=ax)
            bar.set_label('Noise Levels (dB)')
            if numspec > 0:
                yspacing = numfreqs / len(freq)
                yticks = list(range(yspacing/2, numfreqs, yspacing))
                fig2 = plt.figure()
                ax2 = fig2.add_subplot(111)
                c2 = ax2.pcolormesh(allspec.T)
                c2.set_clim((c2min,c2max))
                ax2.set_ylabel('Frequency (kHz)')
                ax2.set_ylim((0,allspec.shape[1]))
                ax2.set_yticks([])
                ax2.set_yticks(yticks)
                ax2.set_yticklabels(freq)
                ax2.set_xlim((0,allspec.shape[0]))
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
            
    def extract_passive_wc(self, badsamples = 20):
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
            numwc = len(set(self.map.packdir['107'][:,3]))
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
                    wc = subpack.ampdata[:totalsamples,:].astype(np.float64)
                    wc = 10**(wc/10)
                    noise.append(10 * np.log10(wc.mean(axis = 0)))
        if len(altfile) != 0:
            b.close()
        # rearrange the data into arrays and by increasing speed
        noise = np.asarray(noise).T
        speeds = np.squeeze(np.asarray(speeds))
        idx = np.argsort(speeds)
        speeds = np.squeeze(speeds[idx])
        noise = np.squeeze(noise[:,idx])
        # go through each beam for the series and find the indices that are outside of 3std
        raw_std = noise.std(axis = 1)
        raw_mean = noise.mean(axis = 1)
        raw_idx = []
        for m in range(noise.shape[0]):
            temp_idx = np.nonzero((noise[m,:] > raw_mean[m] + 3*raw_std[m])|(noise[m,:] < raw_mean[m] - 3*raw_std[m]))
            if len(temp_idx) > 0:
                for k in temp_idx[0]:
                    raw_idx.append(k)
        raw_bad_idx = np.array(list(set(raw_idx)))
        filtered = np.delete(noise, raw_bad_idx, axis = 1)
        # take the mean of the remaining data
        lin_noise = 10**(filtered/10)
        lin_mean_noise = lin_noise.mean(axis = 1)
        mean_noise = np.squeeze(10 * np.log10(lin_mean_noise))
        return speeds, noise, mean_noise
    
    def get_measured_used_sss(self):
        """
        This method extracts the surface sound speed as measured and samples it
        based on the time stamps of the XYZ88 record.  Both the XYZ88 Surface
        Sound Speed and the measured sound speed are returned.
        """
        t = self.map.packdir['88'][:,1]
        mss = self.get_sss(t)
        fss = np.zeros(len(t))
        for n,m in enumerate(fss):
            s = self.getrecord(88,n)
            fss[n] = s.header['SoundSpeed']
        return np.array([t,mss,fss]).T
        
    def build_wc_h5(self):
        """
        This is a method for building hdf5 files containing the watercolumn
        data.  The purpose is to improve access to multiple records for running
        statistics quickly and simply without running out of memory.
        """
        if have_tables:
            outfilename = self.infilename + '.h5'
            # build the header table used for finding specific metadata
            self.tblfile = tbl.openFile(outfilename, mode = 'w', title = 'Storing watercolumn data')
            metadata_grp = self.tblfile.create_group('/','metadata','Header Information')
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
            wc_group = self.tblfile.create_group('/','Watercolumn', title = 'The data')
            # numwc is just an estimate.  Not all pings have packets with the same time stamp
            if not self.mapped:
                self.mapfile()
            numwc = len(set(self.map.packdir['107'][:,1]))
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
                wc = 10**(ping.ampdata/20)
                try:
                    name = 'ping' + str(ping.header['PingCounter'])
                    x = self.tblfile.createCArray(wc_group,name,tbl.Float32Atom(),wc.shape)
                    x[:,:] = wc
                except:
                    print(numwc)
                # get additional helpful info
                t = self.packet.gettime()
                extra['POSIXtime'] = t
                extra['Speed'] = self.getspeed(t)
                extra['PingInFile'] = n
                x,y = ping.ampdata.shape
                extra['TotalSamples'] = x
                extra['TotalBeams'] = y
                extra['PingMean'] = wc.mean()
                extra['PingStd'] = wc.std()
                extra['PingName'] = name
                extra.append()
                current = 100 * n / numwc
                if current - progress >= 1:
                    progress = current
                    sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
            header_tbl.flush()
            extra_tbl.flush()
            self.tblfile.close()
        else:
            print("pytables module unavailable.")

if have_tables:
    class wcfile(tbl.IsDescription):
        """
        Used by the "build_wc_h5" method in the useall class.
        """
    
        Infilename          = tbl.StringCol(33)
        
    class wcextra(tbl.IsDescription):
        """
        Used by the "build_wc_h5" method in the useall class.
        """
        POSIXtime           = tbl.Float64Col()
        Speed               = tbl.Float32Col()
        PingInFile          = tbl.UInt16Col()
        TotalSamples        = tbl.UInt32Col()
        TotalBeams          = tbl.UInt32Col()
        PingMean            = tbl.Float32Col()
        PingStd             = tbl.Float32Col()
        PingName            = tbl.StringCol(8)
               
    class wcheader(tbl.IsDescription):
        """
        Used by the "build_wc_h5" method in the useall class.
        """
        
        PingCounter         = tbl.UInt16Col()
        SystemSerialNum     = tbl.UInt16Col()
        NumOfDatagrams      = tbl.UInt16Col()
        DatagramNum         = tbl.UInt16Col()
        NumTxSectors        = tbl.UInt16Col()
        TotalNumBeams       = tbl.UInt16Col()
        NumBeamsInDatagram  = tbl.UInt16Col()
        SoundSpeed          = tbl.Float32Col()
        SamplingFrequency   = tbl.Float64Col()
        TxHeave             = tbl.Float32Col()
        TVGfunction         = tbl.UInt8Col()
        TVGoffset           = tbl.Int8Col()
        ScanningInfo        = tbl.UInt8Col()
            
class mappack:
    """
    Container for the file packet map.
    """
    def __init__(self):
        """Constructor creates a packmap dictionary"""
        self.packdir = {}
        self.sizedir = {}
        self.numwc = None
        self.dtypes = {
            68 : 'Old Depth',
            88 : 'New Depth',
            102 : 'Old Range/Angle',
            78 : 'New Rangle/Angle',
            83 : 'Old Seabed Imagry',
            89 : 'New Seabead Imagry',
            107 : 'Watercolumn',
            79 : 'Quality Factor',
            65 : 'Serial Attitude',
            110 : 'Network Attitude',
            67 : 'Clock',
            72 : 'Heading',
            80 : 'Postion',
            71 : 'Surface Sound Speed',
            85 : 'Sound Speed Profile',
            73 : 'Start Parameters',
            105 : 'Stop Parameters',
            112 : 'Remote Parameters',
            82 : 'Runtime Parameters',
            104 : 'Height',
            48 : 'PU ID Output',
            49 : 'PU Status',
            66 : 'PU BIST Results',
            51 : 'Extra Parameters'
            }
        
    def add(self, dtype, location, time, size, pingcounter = None):
        """Adds the location (byte in file) to the tuple for the value type"""
        if dtype not in self.packdir:
            self.packdir[dtype] = []
            self.sizedir[dtype] = 0
        if pingcounter is None:
            self.packdir[dtype].append([location, time, size])
        else:
            self.packdir[dtype].append([location, time, size, pingcounter])
        self.sizedir[dtype] += size
        
    def merge_maps(self, map_obj):
        """
        Add many entries from other mappack objects into a single map.  This
        method assumes the maps are not finalized into arrays.
        """
        for key in list(map_obj.packdir.keys()):
            if key not in self.packdir:
                self.packdir[key] = []
                self.sizedir[key] = 0
            self.packdir[key].extend(map_obj.packdir[key])
            self.sizedir[key] += map_obj.sizedir[key]
            
    def finalize(self):
        for key in list(self.packdir.keys()):
            temp = np.asarray(self.packdir[key])
            tempindx = temp[:,1].argsort()
            self.packdir[key] = temp[tempindx,:]

    def printmap(self):
        keys = []
        totalsize = 0
        for i,v in self.packdir.items():
            keys.append((int(i),len(v)))
            totalsize += self.sizedir[i]
        keys.sort()
        for key in keys:
            dtype = self.gettype(key[0])
            percent = 10000 * self.sizedir[str(key[0])]/totalsize
            print(dtype + ' ' + str(key[0]) + ' (' + hex(int(key[0])) + ') has ' + str(key[1]
                ) + ' packets and is ' + str(0.01*percent) + '% of file.')
            
    def getnum(self, recordtype):
        """
        Returns the number of records of the provided record type.
        """
        return len(self.packdir[str(recordtype)])
            
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
        
    def load(self,infilename):
        infile = open(infilename, 'rb')
        try:
            # Python3 has issues with pickled objects made with Python2
            # https://stackoverflow.com/questions/28218466/unpickling-a-python-2-object-with-python-3
            self.__dict__ = pickle.load(infile)
        except UnicodeDecodeError:
            # self.__dict__ = pickle.load(infile, encoding='latin1')
            print('par module does not support nav files generated in Python2.')
        infile.close()        
        
class resolve_file_depths:
    """
    This class treats each file as an object for creating resolved depths. 
    
    The steps here follow the process outlined in "Application of Surface Sound
    Speed Measurements in Post-Processing for Multi-Sector Multibeam 
    Echosounders" by J.D. Beaudion, J. E. Hughes Clarke, and J.E. Barlett, 
    International Hydrographic Review, v.5, no.3, p.26-31.
    http://www.omg.unb.ca/omg/papers/beaudoin_IHR_nov2004.pdf
    """
    def __init__(self, primaryfile, pre = None, post = None):
        """
        Open an All file, map it and make the navigation array. Maybe at some
        point having the previous and post files will help with resolving
        depths that fall outside the navigation for the primary file.
        """
        self.have_ssp_file = False
        self.have_patchtest = False
        self.p = allRead(primaryfile)
        if os.path.isfile(primaryfile[:-3] + 'par'):
            self.p.loadfilemap()
        else:
            self.p.mapfile()
            self.p.savefilemap()
        self.p._build_navarray()
        
        # set whether to applying heading, or keep the output in the sonar ref frame
        self.apply_heading = False
        self.apply_xducer_depth = False
        
    def set_patch_test_values(self, roll_offset=0, pitch_offset=0, heading_offset=0, position_delay=0, attitude_delay=0):
        """
        This method is used for setting the classes patch test values as
        derived from a patch test. Provide the orentation offsets in degrees,
        and the time offsets in seconds.
        """
        self.roll_offset = roll_offset
        self.pitch_offset = pitch_offset
        self.heading_offset = heading_offset
        self.position_delay = position_delay
        self.attitude_delay = attitude_delay
        
        self.have_patchtest = True
        
    def resolve_all_pings(self, ssp_filename):
        """
        still working this out.
        """
        self.ssp_filename = ssp_filename
        numpings = len(self.p.map.packdir['78'])
        for ping in range(numpings):
            self.resolve_ping(ping)
        
    def resolve_ping(self, recordnum, ssp_filename = None):
        """
        First hack at resolving a depth... not sure how this is going to work.
        Figuring it out as I go.  Need to add a better way for checking to see
        if a file is loaded, replacing a file, etc.
        """
        # set the ssp filename
        if ssp_filename is not None:
            self.ssp_filename = ssp_filename
            self.have_ssp_file = True
        elif self.have_ssp_file:
            pass
        else:
            self.have_ssp_file = False
            
        if not self.have_patchtest:
            self.set_patch_test_values()
            
        self.get_supporting_data(recordnum)
        tstamp, rxnav, twtt, azimuth, beam_depression, heave = self.get_ping_angle_bearing(recordnum)
        #get which side the pings are on
        swathside = np.sign(beam_depression)
        # get cast for the first sounding in the ping
        casttime = dtm.datetime.utcfromtimestamp(tstamp[0])
        # h_range is from the transducer.
        h_range, depth = self.raytrace(twtt, beam_depression, self.xducer_depth, self.surface_ss, casttime)
        h_range *= swathside
        # return the depth measurement to being referenced to the transducer.
        if not self.apply_xducer_depth:
            depth -= self.xducer_depth
        
        x = h_range * cos(np.deg2rad(azimuth)) + self.txoffset[1]
        y = h_range * sin(np.deg2rad(azimuth)) + self.txoffset[0]
        
        if self.apply_heading:
            h = rxnav[:,6]  # get the heading
            x += self.txoffset[0]*np.sin(h) + self.txoffset[1]*np.cos(h)
            y += self.txoffset[0]*np.cos(h) - self.txoffset[1]*np.sin(h)
        else:
            x += self.txoffset[0]
            y += self.txoffset[1]
        
        return tstamp, x, y, depth
    
    def get_supporting_data(self, recordnum):
        """
        Gets the supporting navigation, sounds speed, vessel offsets to support
        the process of resolving a depths.
        """
        # installation information
        self.p.getrecord('73', 0)
        settings = self.p.packet.subpack.settings
        self.settings = settings
        self.txoffset = np.asarray([settings['S1X'], settings['S1Y'], settings['S1Z']], 
            dtype = 'float')
        self.txrot = np.asarray([settings['S1R'], settings['S1P'], settings['S1H']], 
            dtype = 'float')
        self.rxoffset = np.asarray([settings['S2X'], settings['S2Y'], settings['S2Z']], 
            dtype = 'float')
        self.rxrot = np.asarray([settings['S2R'], settings['S2P'], settings['S2H']], 
            dtype = 'float')
        self.xducer_depth = float(settings['S1Z']) - float(settings['WLZ'])
        
        # ping information
        if '78' in self.p.map.packdir:
            self.p.getrecord('78', recordnum)
        else:
            self.p.getrecord('102', recordnum)
        self.tstamp = self.p.packet.time
        self.header = self.p.packet.subpack.header
        self.tx = self.p.packet.subpack.tx
        self.rx = self.p.packet.subpack.rx
        self.surface_ss = self.header['SoundSpeed']
    
    def get_ping_angle_bearing(self, recordnum):
        """
        Do all the rotation stuff.
        """        
        # TX is reverse mounted: subtract 180 from heading installation angle,
        # and flip sign of the pitch offset.
        # RX is reverse mounted: subtract 180 from heading installation angle,
        # and flip the sign of the beam steering angles and the sign of the
        # receiver roll offset.  ~ per Jonny B 20120928
        
        if np.abs(self.txrot[2]) > 90:
            txo = -1
        else: txo = 1
        if np.abs(self.rxrot[2]) > 90:
            rxo = -1
        else: rxo = 1
        
        tx_vector = txo * np.mat([1,0,0]).T
        rx_vector = rxo * np.mat([0,1,0]).T

        txnum = self.tx['TransmitSector#'].argsort()  # this is getting the transmit # order
        
        # form array of transmit times
        if self.header['Ntx'] > 1:
            txtimes = []
            for indx in txnum:
                txtimes.append(self.tstamp + self.tx['Delay'][indx])
        else:
            txtimes = [self.tstamp + self.tx['Delay'][0]]
        txnav = self.p.getnav(txtimes)  # this is in tx sector order

        # make a TX rotation matrix for each sector in the "ping"
        TX = []
        # the alignment matrix
        TXa = self.rot_mat(self.txrot[0], self.txrot[1], self.txrot[2])
        for entry in txnav:
            # the orientation matrix for each sector
            TXo = self.rot_mat(entry[3],entry[4],entry[6])
            TX.append(TXo * TXa * tx_vector)
        # get receive times to get navigation information
        rxtimes = np.zeros(len(self.rx))
        if '78' in self.p.map.packdir:
            twowaytraveltimes = self.rx['TravelTime']
        else:
            twowaytraveltimes = self.rx['Range']/ self.header['SamplingFrequency']
        for i, txtime in enumerate(txtimes):
            # this gets the index of all rx beams belonging to a particular tx
            rxnums = np.nonzero(self.rx['TransmitSectorID'] == i)[0]
            # then it adds the tx offset to that particular group of rx
            rxtimes[rxnums] = twowaytraveltimes[rxnums].astype(np.float64) + txtime
        
        # find the beam pointing vector for each beam
        beam_depression = np.zeros(len(self.rx))
        azimuth = np.zeros(len(self.rx))
        
        # the rx alignment matrix
        RXa = self.rot_mat(self.rxrot[0], self.rxrot[1], self.rxrot[2])
        # get the nav for all rx times in this ping
        rxnav = self.p.getnav(rxtimes)
        heave = np.zeros(len(self.rx))
        for i, entry in enumerate(rxnav):
            # the orientation matrix for each receive beam
            RXo = self.rot_mat(entry[3] + self.roll_offset, 
                entry[4]+self.pitch_offset, entry[6]+self.heading_offset)
            RX = RXo * RXa * rx_vector
            tx_indx = int(self.rx['TransmitSectorID'][i])  # get the tx number
            heave[i] = (rxnav[i][5] + txnav[tx_indx][5])/2
            # this section of code is in radians
            rx_steer = np.deg2rad(self.rx['BeamPointingAngle'][i]) * rxo
            tx_steer = np.deg2rad(self.tx['TiltAngle'][txnum[tx_indx]]) * txo
            misalign = np.arccos(TX[tx_indx].T * RX) - pi/2
            x = sin(tx_steer)
            y1 = -sin(rx_steer) / cos(misalign)
            y2 = x * np.tan(misalign)
            y = y1 + y2
            z = np.sqrt(1 - x**2 - y**2)
            BVp = np.array([x,y,z])
            Xp = TX[tx_indx].T
            Zp = np.cross(Xp,RX.T)
            Yp = np.cross(Zp,Xp)
            Rgeo = np.array([Xp,Yp,Zp]).T
            BV = np.dot(Rgeo,BVp.T)
            beam_depression[i] = np.arctan2(BV[2],np.sqrt(BV[0]**2 + BV[1]**2))
            azimuth[i] = np.arctan2(BV[1],BV[0])
            # end radians section of code
            if i == 0:
                print('TX, RX')
                print(TX[tx_indx])
                print(RX)
                print('txsteer, rxsteer, misalign')
                print(np.rad2deg([tx_steer, rx_steer]))
                print(misalign)
                print('heave, draft of xducer')
                print(txnav[tx_indx][5])
                print(str(self.xducer_depth + heave[i]))
                print('x,y1,y2,y,z')
                print(x, y1, y2, y, z)
                print('Xp,Yp,Zp')
                print(Xp)
                print(Yp)
                print(Zp)
                print('BVp, Rgeo, BV')
                print(BVp)
                print(Rgeo)
                print(BV)
                print('beam depression 0, azimuth 0')
                print(np.rad2deg(beam_depression[0]))
                print(np.rad2deg(azimuth[0]))
                
           
        beam_depression = np.rad2deg(beam_depression)
        azimuth = np.rad2deg(azimuth)
        if not self.apply_heading:
            azimuth -= rxnav[:,6]
        morethan360 = np.nonzero(azimuth > 360)[0]
        azimuth[morethan360] -= 360
        lessthanzero = np.nonzero(azimuth < 0)[0]
        azimuth[lessthanzero] += 360
        
        return rxtimes, rxnav, twowaytraveltimes, azimuth, beam_depression, heave
    
    def rot_mat(self, theta, phi, gamma, degrees = True):
        """
        Make the rotation matrix for a set of angles and return the matrix.
        All file angles are in degrees, so incoming angles are degrees.
        """
        if degrees == True:
            t,p,g = np.deg2rad([theta,phi,gamma])
        else:
            t,p,g = theta, phi, gamma
        rmat = np.mat(
            [[cos(p)*cos(g), sin(t)*sin(p)*cos(g) - cos(t)*sin(g), cos(t)*sin(p)*cos(g) + sin(p)*sin(g)],
            [cos(p)*sin(g), sin(t)*sin(p)*sin(g) + cos(t)*cos(g), cos(t)*sin(p)*sin(g) - sin(t)*cos(g)],
            [-sin(p), sin(t)*cos(p), cos(t)*cos(p)]]
            )
        return rmat
        
    def raytrace(self, twowaytraveltimes, beam_depression, xducer_depth, surface_ss, casttime):
        """
        Calls Jonny B's SV class to do the ray trace if possible, otherwise just assumes
        surface_ss for whole water column.  Need to make this so it does not load a new file
        if the file name is the same.  This might also require updates to JB's code...
        """
        
        if have_svp_module and self.have_ssp_file:
            y = np.zeros(len(beam_depression))
            z = np.zeros(len(beam_depression))
            profile = svp.SV()
            profile.read_hips(self.ssp_filename, time = casttime)
            indx = 0
            for twtt,angle in zip(twowaytraveltimes,beam_depression):
                if not np.isnan(angle):
                    y[indx], z[indx] = profile.raytrace(xducer_depth, angle, surface_ss, twtt)
                    indx +=1

        else:
            print('Unable to use Jonny B svp module.  Assuming surface sound speed throughout watercolumn!')
            y = surface_ss/2 * twowaytraveltimes * cos(np.deg2rad(beam_depression))
            z = xducer_depth + surface_ss/2 * twowaytraveltimes * sin(np.deg2rad(beam_depression))
            
        return y, z
            
    def compare_to_xyz(self, recordnum, svfile = None):
        """
        Plots the results of resolve_ping(recordnum) to the xyz record(88 or 68).
        """
        if '88' in self.p.map.packdir:
            self.p.getrecord(88, recordnum)
        else:
            self.p.getrecord(68, recordnum)
        za = self.p.packet.subpack.data['Depth']
        ya = self.p.packet.subpack.data['AcrossTrack']
        xa = self.p.packet.subpack.data['AlongTrack']
        
        # to compare, make sure heading is not being applied.
        temp = self.apply_heading, self.apply_xducer_depth
        self.apply_heading = False
        self.apply_xducer_depth = False
        tstamp, xb, yb, zb = self.resolve_ping(recordnum, svfile)
        # reset the apply_heading default
        self.apply_heading, self.apply_xducer_depth = temp
        
        plt.ion()
        plt.figure()
        plt.subplot(311)
        plt.plot(xa, 'g.', xb, 'b.')
        plt.legend(('xyz datagram','range/angle datagram'))
        plt.ylabel(('x(m)'))
        plt.subplot(312)
        plt.plot(ya, 'g.', yb, 'b.')
        plt.ylabel(('y(m)'))
        plt.subplot(313)
        plt.plot(za, 'g.', zb, 'b.')
        plt.ylabel(('z(m)'))
        plt.xlabel(('Beam #'))
        plt.suptitle(('record ' + str(recordnum)))
        
        plt.figure()
        plt.subplot(311)
        plt.plot(xa-xb, 'r.')
        plt.ylabel(('delta x(m)'))
        plt.subplot(312)
        plt.plot(ya-yb, 'r.')
        plt.ylabel(('delta y(m)'))
        plt.subplot(313)
        plt.plot(za-zb, 'r.')
        plt.ylabel(('delta Z(m)'))
        plt.xlabel(('Beam #'))
        plt.suptitle(('xyz - resolved for record ' + str(recordnum)))
        plt.draw()

def build_BSCorr(fname1, fname2, which_swath = 0, bs_mean = None, plot_bs = True, lambertian = True, debug = False):
    """
    This function is intended to build a BSCorr.txt file for a Kongsberg
    multibeam that has a compatable version of SIS (4.1.x and later,
    depending on the system).  Provide two file names.  The two files are
    plotted so that the range of pings in each file can be manually selected.
    The selected pings are then stacked to look for the average in each sector
    and by beam.
    
    -For the EM710-
    From Gard Skokland:
    The second line in the bscorr file is describing the swath
    The first number indicate which mode (very shallow, shallow etc.).
    The second number indicate which swath (single=0, first in dual=1, second in dual=2).
    The third number tells you how many sectors you have (for EM710, 3)

    The fourth line indicates the source level used for this sector,
    and the the fifth line indicates how many  inputs you have in this sector (in this case 6  for port sector, 11 for the middel sector and 6 for starboard)
    Maximum allowed inputs per sector is 32. 
    That gives 96 for the whole swath. Since the swath is maximum 70/70, total 140 degrees, you will then be able to have approxemately one correction input per 1.5 degree.
    This is a very time consuming job if you do it manually, but I think the deault 10 degrees is a little to big step.

    -For the EM122-
    ...
    """
    a = useall(fname1)
    b = useall(fname2)
    # get the current bscorr info
    a51 = a.getrecord(51,0)
    # get the metadata for the BSCorr file
    a78 = a.getrecord(78,0)
    asonartype = a.packet.header['Model']
    anumsectors = a78.header['Ntx']
    a82 = a.getrecord(82,0)
    amode = a82.header['Mode']
    adual_swath = ((amode & 128) == 128)
    b78 = b.getrecord(78,0)
    bsonartype = b.packet.header['Model']
    bnumsectors = b78.header['Ntx']
    b82 = b.getrecord(82,0)
    bmode = b82.header['Mode']
    bdual_swath = ((bmode & 128) == 128)
    
    mode = (amode & 7) + 1
    if adual_swath and mode < 5:
        swath = ', Dual Swath (' + str(which_swath) + ').'
        bscorr_swath = which_swath + 1
    else:
        swath = ', Single Swath.'
        bscorr_swath = 0
    title = "Mode type is " + str(mode
        ) + ", the number of sectors is " + str(anumsectors
        ) + ", and the sonar type is " + str(asonartype
        ) + swath
    print("\n" + title + "\n")
    if asonartype != bsonartype or anumsectors != bnumsectors or amode != bmode or adual_swath != bdual_swath:
        print("***These files should not be compared for BSCorr purposes.***")
        
    # extract the right data from the BSCorr for this mode
    swathnum = np.array(a51.swathnum)
    modes = np.array(a51.modes)
    idx = np.nonzero((modes == mode)&(swathnum == bscorr_swath))[0]
    if len(idx) == 1:
        bscorr_data = a51.data[idx[0]]
        bscorr_sectors = []
        if asonartype == 710:
            for n in range(anumsectors):
                bscorr_sectors.append(bscorr_data[n])
        elif asonartype == 122:
            bscorr_sectors = bscorr_data
    else:
        print("No match for settings found in BSCorr!!!")
    
    # get the backscatter for each line
    abp, acount, angles = a.build_BSCorr_info(which_swath = which_swath, plot_bs = plot_bs, lambertian = lambertian)
    bbp, bcount, angles = b.build_BSCorr_info(which_swath = which_swath, plot_bs = plot_bs, lambertian = lambertian)
    
    # dropping the data near nadir from the nomalization.  Kjell does something similar...
    #idx = np.nonzero((angles < 15) & (angles > -15))
    #abp[idx,:] = np.nan
    #bbp[idx,:] = np.nan
    
    # find the average values as a difference from the mean
    abp_lin = 10**(abp/10)
    bbp_lin = 10**(bbp/10)
    if bs_mean == None:
        bs_mean = 10*np.log10((np.nanmean(abp_lin) + np.nanmean(bbp_lin))/2)
        bs_mean = int(bs_mean * 100)/100.
    print('Normalizing backscatter to ' + str(bs_mean)) 
    m,n = abp.shape
    bp_mean = np.zeros((m,n))
    for s in range(n):
        if asonartype == 710:
            for r in range(m):
                if np.isnan(abp[r,s]) & np.isnan(bbp[r,s]):
                    bp_mean[r,s] = np.nan
                elif np.isnan(abp[r,s]):
                    bp_mean[r,s] = bbp[r,s]
                elif np.isnan(bbp[r,s]):
                    bp_mean[r,s] = abp[r,s]
                else:
                    bp_mean[r,s] = 10*np.log10((10**(abp[r,s]/10) + 10**(bbp[r,s]/10)) / 2)
        elif asonartype == 122:
            idx = np.nonzero(~np.isnan(abp[:,s]))
            abp_mean = np.nanmean(abp[:,s])
            bbp_mean = np.nanmean(bbp[:,s])
            bp_mean[:,s] = np.nan
            bp_mean[idx,s] = (abp_mean + bbp_mean) / 2.
    bp_mean -= bs_mean
    
    # combine the BScorr file with the averaged output
    bscorr_interp = []
    for n in range(anumsectors):
        if asonartype == 710:
            temp = bscorr_sectors[n]
            idx = temp[:,0].argsort() # angles are in reverse order in the BSCorr
            temp = temp[idx,:]
            bscorr_interp.append(np.interp(angles,temp[:,0],temp[:,1], left = np.nan, right = np.nan))
        elif asonartype == 122:
            temp = bscorr_sectors[n]
            idx = np.nonzero(~np.isnan(bp_mean[:,n]))
            vals = np.zeros(len(bp_mean)) + np.nan
            vals[idx] = int(temp[0])
            bscorr_interp.append(vals)
    bscorr_interp = np.asarray(bscorr_interp).T
    
    # make the plot
    amin = angles.min()
    amax = angles.max()
    f1 = plt.figure()
    ax1 = f1.add_subplot(411)
    ax1.plot(angles, abp, 'g-+')
    ax1.plot(angles, bbp, 'r-*')
    ax1.set_ylabel('First and Second Files\ndB re 1 $\mu$Pa at 1 meter')
    ax1.set_xlim((amax,amin))
    plt.grid()
    ax2 = f1.add_subplot(412)
    ax2.plot(angles, bp_mean, 'g-+')
    ax2.plot(angles, (bscorr_interp - np.nanmean(bscorr_interp)) * 0.01, 'r-*')
    ax2.set_ylabel('File Mean and BSCorr\ndB re 1 $\mu$Pa at 1 meter')
    ax2.set_xlim((amax,amin))
    plt.grid()
    ax3 = f1.add_subplot(413)
    ax3.plot(angles, bp_mean + bscorr_interp,'-*')
    ax3.set_ylabel('For BSCorr Input\ndB re 1 $\mu$Pa at 1 meter')
    ax3.set_xlim((amax,amin))
    plt.grid()
    ax4 = f1.add_subplot(817)
    ax4.plot(angles, acount, '-+')
    ax4.set_ylabel('File A Count')
    ax4.set_xlim((amax,amin))
    plt.grid()
    ax5 = f1.add_subplot(818)
    ax5.plot(angles, bcount, '-*')
    ax5.set_xlabel('Angle (Degrees)')
    ax5.set_ylabel('File B Count')
    ax5.set_xlim((amax,amin))
    plt.grid()
    f1.suptitle(title + '\n Normalized to ' + str(bs_mean))
    #plt.tight_layout()
    plt.show()
    
    if asonartype == 710:
        # output text file
        outname = fname1.split('_')[2] + '_' + fname2.split('_')[2] + '.bscorr'
        outfile = open(outname,'w')
        s = swath.split()[1]
        metatitle = 'Mode,Number of Sectors,Sonar Type,Swath Type/Number,BS Mean\n'
        metadata = str(mode) + "," + str(anumsectors) + "," + str(asonartype
            ) + ',' + s + str(which_swath) + ',' + str(bs_mean) + '\n'
        outfile.write(metatitle)
        outfile.write(metadata)
        
        angletitle = ''
        dataout = ['','','']
        for n,a in enumerate(angles):
            if a%5 == 0:
                angletitle = angletitle + str(a) + ','
                for m in range(anumsectors):
                    bs = bp_mean[n,m]
                    if np.isnan(bs) or np.isnan(bscorr_interp[n,m]):
                        dataout[m] = dataout[m] + ','
                    else:
                        dataout[m] = dataout[m] + str(bs + bscorr_interp[n,m]) + ','
        angletitle = angletitle + '\n'
        outfile.write(angletitle)
        for m in range(anumsectors):
            outfile.write(dataout[m] + '\n')
        outfile.write('BSCorr\n')
        outfile.close()
    assert(not debug)

def plot_extinction(fdir = '.', plot_mean = False, plot_lines = True,
                    modes = [], mindepth = None, maxdepth = None,
                    maxport = None, maxstbd = None):
    """
    extinction_KM.py
    
    G.Rice 20140110
    V 0.0.2 last updated 20140325
    
    Written to read the xyz datagram and plot the outermost valid beam on either
    as a function of acrosstrack vs depth with the the mode as the color.
    
    This function can easily be changed to make the backscatter the color instead.
    """
    flist = glob(fdir + '/*.all') 
    numf = len(flist)
    infiles = []
    numxyz = []
    bathy_type = 88
    for f in range(numf):
        infiles.append(useall(flist[f]))
        if '88' in infiles[f].map.packdir:
            numxyz.append(len(infiles[f].map.packdir['88']))
        elif '68' in infiles[f].map.packdir:
            numxyz.append(len(infiles[f].map.packdir['68']))
            bathy_type = 68
        else:
            numxyz.append(0)
    
    total = np.asarray(numxyz).sum()
    points = np.zeros((total*2, 3))
    markers = np.zeros(total*2)
    count = 0
    
    for k,f in enumerate(infiles):
        mode = []
        for n in range(len(f.map.packdir['82'])):
            f.getrecord(82,n)
            m = f.packet.subpack.header['Mode']
            t = f.packet.gettime()
            mode.append([t,m])
        mode_idx = 0
        for n in range(numxyz[k]):
            f.getrecord(bathy_type, n)
            t = f.packet.gettime()
            if mode[mode_idx][0] <= t and mode_idx < len(mode)-1:
                mode_idx += 1
            b = f.packet.subpack.data
            if bathy_type == 88:
                idx = np.nonzero(b['Detection'] < 128)[0] # look for valid detections
                vals = idx[[1,-1]]
                points[count:count+2,0] = b['AcrossTrack'][vals]
                points[count:count+2,1] = b['Depth'][vals]
                points[count:count+2,2] = b['Reflectivity'][vals]
            elif bathy_type == 68:
                if f.packet.subpack.header['ValidBeams'] > 50:
                    points[count:count+2,0] = b['AcrossTrack'][[1,-1]]
                    points[count:count+2,1] = b['Depth'][[1,-1]]
                    points[count:count+2,2] = b['Reflectivity'][[1,-1]]
                else:
                    points[count:count+2,0] = np.nan
                    points[count:count+2,1] = np.nan
                    points[count:count+2,2] = np.nan
            markers[count:count+2] = int(mode[mode_idx][1] & 7)
            count +=2
    
    for f in infiles:       
        f.close()
        
    # get the average across track swath width by port and starboard
    sidx = np.nonzero(points[:,0] > 0)[0]
    pidx = np.nonzero(points[:,0] < 0)[0]
    pd, pam = _build_extinction_curve(points[pidx,1],points[pidx,0])
    sd, sam = _build_extinction_curve(points[sidx,1],points[sidx,0])
    
    # get the lines indicating the percentage of depth
    if mindepth == None:
        mindepth = np.nanmin(points[:,1])
    if maxdepth == None:
        maxdepth = np.nanmax(points[:,1])
    if maxport == None:
        maxport = 1.05*np.nanmin(points[:,0])
    if maxstbd == None:
        maxstbd = 1.05*np.nanmax(points[:,0])
    lines, labels = _percent_depth_lines(maxdepth, maxport, maxstbd)    
    
    plt.ion()
    
    if len(modes) == 0:
        modes = ['Very Shallow', 'Shallow', 'Medium', 'Deep', 'Very Deep', 'Extra Deep']
    marker = set(markers)
    fig = plt.figure(figsize = (12,6))
    ax = fig.add_subplot(111)
    
    for m in marker:
        idx = np.nonzero(markers == m)[0]
        ax.plot(points[idx,0], points[idx,1], linestyle = 'None', marker = 'o', 
                label = modes[int(m)])
    if plot_mean:
        ax.plot(pam, pd, 'g', linewidth = 3)
        ax.plot(sam, sd, 'g', linewidth = 3)
    if plot_lines:
        for n in range(len(lines)):
            m = 0.9
            ax.plot(lines[n,:,0],lines[n,:,1], 'k', alpha = 0.6)
            ax.text(m*lines[n,1,0],m*lines[n,1,1], labels[n], size = 14, 
                horizontalalignment='center', verticalalignment='center', 
                bbox=dict(facecolor='white', edgecolor = 'none', alpha=0.5))
            ax.plot(-lines[n,:,0],lines[n,:,1], 'k', alpha = 0.6)
            ax.text(m*-lines[n,1,0],m*lines[n,1,1], labels[n], size = 14, 
                horizontalalignment='center', verticalalignment='center',
                bbox=dict(facecolor='white', edgecolor = 'none', alpha=0.5))

    ax.set_xlabel('Across Track (m)')
    ax.set_ylabel('Depth (m)')
    plt.legend(loc = 'center')
    plt.grid(True)
    ax.set_title('Extinction Depth Test')
    
    delta = maxdepth - mindepth
    space = 0.05 * delta

    ax.set_ylim((maxdepth + space, mindepth - space))
    ax.set_xlim((1.05 * maxport, 1.05 * maxstbd))
    
    plt.draw()
    
    # return pam,pd,sam,sd
    
def _percent_depth_lines(maxdepth, minx, maxx):
    """
    Returns the lines for plotting the percent depth based on the depth and
    min/max across track distaces provided.
    """
    if np.abs(minx) > maxx:
        xmax = np.abs(minx)
    else:
        xmax = maxx
    lines = np.zeros((7,2,2))
    labels = []
    for n in range(len(lines)):
        x = maxdepth * (n+1) / 2.
        if x < xmax:
            lines[n,1,:] = [x,maxdepth]
            labels.append(str(n+1) + 'X')
        else:
            lines[n,1,:] = [xmax, xmax * maxdepth / x]
            labels.append(str(n+1) + 'X')
    return lines, labels
            
def _build_extinction_curve(depths, across, binsize = 200):
    """
    This method takes a bunch of series of points, defined as depth and
    distance across track, and runs a hanning window over the data of size
    binsize by depth, where the binsize is the number of samples in each depth
    bin.  The depth estimates are speaced by half the binsize and the steps are
    defined by the amount of data available.
    """
    halfbin = binsize/2
    # defining the window function
    winres = 50
    win = np.hanning(winres)
    #clean out nans
    cleanidx = np.nonzero(~np.isnan(across))
    depths = depths[cleanidx]
    across = across[cleanidx]
    # sort the data by depth
    sidx = depths.argsort()
    depths = depths[sidx]
    across = across[sidx]
    # the output variables
    depthstep = []
    am = []
    steps = list(range(halfbin, len(depths), halfbin))
    for n in steps:
        try:
            dvals = depths[n-halfbin : n+halfbin]
            avals = across[n-halfbin : n+halfbin]
        except:
            dvals = depths[n-halfbin:]
            avals = across[n-halfbin:]
        dmin = dvals.min()
        dmax = dvals.max()
        depthstep.append((dmin + dmax)/2) # middle of the window
        depthwin = np.linspace(dmin,dmax,num = winres)
        winvals = np.interp(dvals, depthwin, win) # build window values at the right places
        am.append( np.sum(avals * winvals) / winvals.sum() ) # window and normalize
    return depthstep, am
    
def noise_from_passive_wc(path = '.', by_file = True, speed_change_rate = 10, 
                          speed_bins = [], extension = 'wcd', 
                          which_swath = 'all', cmax = -10., cmin = -65.):
    """
    Builds an array of noise data by averaging the watercolumn from the files
    at the provided path.  The kwarg speed_change_rate defines the number of
    pings that should be expected between speeds.  TVG is not removed from the
    water column backscatter because there is assumed to be no TVG in passive
    mode.
    Get FFT by speed - commented out so as not to bog down the process.  This
    appears not to work properly.
    Adding a "which_swath" kwarg to decide if to use both swaths for a dual
    swath system.  This can be "all", "odd" or "even" pings.
    """
    badsamples = 20  # there are some unfilled samples at the end of the array
    print("***Warning: dropping the last " + str(badsamples) + " samples***")    
    scr = speed_change_rate
    flist = glob(os.path.join(path, '*.' + extension))
    flist.sort()
    speeds = []
    noise = []
    fnum = []
#    pingfft = []
    totalsamples = 0
    counter = 0
    for m,f in enumerate(flist):
        path, fname = os.path.split(f)
        print('Working on file ' + fname)
        a = useall(f)
        a.mapfile()
        if '80' not in a.map.packdir:
            altfile = f[:-3] + 'all'
            if os.path.isfile(altfile):
                b = useall(altfile)
                b.mapfile()
            else:
                print('No Speed source found for ' + fname)
                break
        else:
            altfile = ''
        if '107' in a.map.packdir:
            numwc = a.map.numwc
            if which_swath == 'all':
                pingnum = np.arange(numwc)
            elif which_swath == 'odd':
                pingnum = np.arange(1,numwc,2)
            elif which_swath == 'even':
                pingnum = np.arange(0,numwc,2)
            for n in pingnum:
                subpack = a.getwatercolumn(n)
                if len(altfile) == 0:
                    speed = a.getspeed(a.packet.gettime())
                else:
                    speed = b.getspeed(a.packet.gettime())
                if not np.isnan(speed):
                    speeds.append(speed)
                    fnum.append(m)
                    if totalsamples == 0:
                        totalsamples = subpack.ampdata.shape[0] - badsamples
                    wc = subpack.ampdata[:totalsamples,:].astype(np.float64)
                    # wc_fft = np.fft.rfft(wc[:,100])#, axis = 0)
                    wc = 10**(wc/10)
                    noise.append(10 * np.log10(wc.mean(axis = 0)))
                    # pingfft.append(wc_fft.real)#np.squeeze(wc_fft.mean(axis = 1).real))
                    counter += 1
        a.close()
        if len(altfile) >0:
            b.close()
#    freq = np.fft.rfftfreq(wc.shape[0],1/subpack.header['SamplingFrequency'])
    # rearrange the data into arrays and by increasing speed
    noise = np.asarray(noise).T
#    pingfft = np.asarray(pingfft).T
    speeds = np.squeeze(np.asarray(speeds))
    fnum = np.squeeze(np.asarray(fnum))
    idx = np.argsort(speeds)
    speeds = np.squeeze(speeds[idx])
    fnum = np.squeeze(fnum[idx])
    noise = noise[:,idx]
#    pingfft = np.squeeze(pingfft[:,idx])
#    avg_fft = np.zeros((pingfft.shape[0],numspeeds))
    if by_file == True:
        avespeeds = np.zeros(len(flist))
        mean_noise = np.zeros((noise.shape[0],len(flist)))
        sorted_noise = np.zeros(noise.shape)
        sorted_fnum = np.zeros(fnum.shape)
        count = 0
        # first find the average speed for each of the files
        for n in range(len(flist)):
            idx = np.nonzero(fnum == n)[0]
            avespeeds[n] = np.mean(speeds[idx])
        speed_idx = np.argsort(avespeeds)
        for n,s in enumerate(speed_idx):
            # get the data from files in order of increasing speed
            idx = np.nonzero(fnum == s)[0]
            raw = noise[:,idx]
            # sort the data into the speed order for plotting
            sorted_noise[:,count:count + len(idx)] = noise[:,idx]
            sorted_fnum[count:count + len(idx)] = n
            count += len(idx)
            # filter to get rid of the bursts - this is in log space
            raw_std = raw.std(axis = 1)
            raw_mean = raw.mean(axis = 1)
            raw_idx = []
            # go through each beam for the series and find the indices that are outside of 3std
            for m in range(raw.shape[0]):
                temp_idx = np.nonzero((raw[m,:] > raw_mean[m] + 3*raw_std[m])|(raw[m,:] < raw_mean[m] - 3*raw_std[m]))
                if len(temp_idx) > 0:
                    for k in temp_idx[0]:
                        raw_idx.append(k)
            raw_bad_idx = np.array(list(set(raw_idx)))
            filtered = np.delete(raw, raw_bad_idx, axis = 1)
    #        filtered_fft_by_speed = np.delete(fft_by_speed, raw_bad_idx, axis=1)
            # take the mean of the remaining data
            lin_noise = 10**(filtered/10)
            lin_mean_noise = lin_noise.mean(axis = 1)
            mean_noise[:,n] = np.squeeze(10 * np.log10(lin_mean_noise))
    #        avg_fft[:,n] = np.squeeze(filtered_fft_by_speed.mean(axis = 1))
        #assert False
        numspeeds = len(flist)
        fnum = sorted_fnum
        noise = sorted_noise
        avespeeds = avespeeds[speed_idx]
    else:
        noise = np.squeeze(noise[:,idx])
        if len(speed_bins) == 0:
            idx, avespeeds = _find_speed_bins(speeds, scr)#, plotfig = True)
        else:
            idx, avespeeds = _assign_speed_bins(speeds, speed_bins)
        numspeeds = len(avespeeds)
        mean_noise = np.zeros((noise.shape[0],numspeeds))
        for n in range(numspeeds):
            raw = noise[:,idx[n,0]:idx[n,1]]
    #        fft_by_speed = pingfft[:,idx[n,0]:idx[n,1]]
            # filter to get rid of the bursts - this is in log space
            raw_std = raw.std(axis = 1)
            raw_mean = raw.mean(axis = 1)
            raw_idx = []
            # go through each beam for the series and find the indices that are outside of 3std
            for m in range(raw.shape[0]):
                temp_idx = np.nonzero((raw[m,:] > raw_mean[m] + 3*raw_std[m])|(raw[m,:] < raw_mean[m] - 3*raw_std[m]))
                if len(temp_idx) > 0:
                    for k in temp_idx[0]:
                        raw_idx.append(k)
            raw_bad_idx = np.array(list(set(raw_idx)))
            filtered = np.delete(raw, raw_bad_idx, axis = 1)
    #        filtered_fft_by_speed = np.delete(fft_by_speed, raw_bad_idx, axis=1)
            # take the mean of the remaining data
            lin_noise = 10**(filtered/10)
            lin_mean_noise = lin_noise.mean(axis = 1)
            mean_noise[:,n] = np.squeeze(10 * np.log10(lin_mean_noise))
    #        avg_fft[:,n] = np.squeeze(filtered_fft_by_speed.mean(axis = 1))
    # plot all pings
    tickloc = []
    speed_legend = []
    for n in range(len(avespeeds)):
        if by_file == True:
            idx = np.nonzero(n == fnum)[0]
            tickloc.append(int(np.mean([idx[0],idx[-1]])))
        else:
            tickloc.append(int(idx[n].mean()))
        speed_legend.append('%0.1f'%(avespeeds[n]))
    fig, ax = plt.subplots(1,1)
    im = ax.imshow(noise, aspect = 'auto')
    im.set_cmap('viridis')
    im.set_clim((cmin, cmax))
    bar = plt.colorbar(mappable = im)
    bar.set_label('Pressure (dB re $1\mu Pa / \sqrt{Hz}$ )')
    ax.set_ylabel('Beam Number')
    ax.set_xlabel('Speed (m/s)')
    ax.set_title('Passive Mode Noise Tests')
    ax.set_xticks(tickloc)
    ax.set_xticklabels(speed_legend)
#    plt.figure()
#    im = plt.imshow(pingfft, aspect = 'auto')
#    bar = plt.colorbar()
#    bar.set_label('height')
#    plt.ylabel('stuff')
#    plt.xlabel('Speed')
#    plt.title('stuff')
#    ax = im.get_axes()
#    ax.set_xticks(tickloc)
#    ax.set_xticklabels(speed_legend)
    # plot the average of each
    plt.figure()
    for n in range(numspeeds):
        plt.plot(mean_noise[:,n])
        plt.xlabel('Beam')
        plt.ylabel('dB re $1\mu Pa / \sqrt{Hz}$')
    plt.legend(speed_legend, title = 'Speed (m/s)')
    plt.xlim([0,mean_noise.shape[0]])
    plt.ylim((cmin,cmax))
    plt.title('Mean Noise by Beam Number')
    plt.grid()
#    plt.figure()
#    for n in range(numspeeds):
#        plt.plot(freq, avg_fft[:,n])
#        plt.xlabel('Frequency')
#        plt.ylabel('stuff')
#    plt.legend(speed_legend)
#    plt.xlim([0,mean_noise.shape[0]])
#    plt.title('stuff')
#    plt.grid()
        
def _find_speed_bins(speeds, speed_change_rate = 10, plotfig = False):
    """
    Takes an array of speeds and provides grouping assuming that the
    acceleration steps were not longer than the provided number in
    the kwarg speed_change_rate, which defaults to 10 steps. The first and last
    index for each boundary is provided along with the array of speeds.
    The speeds are assumed to already to be sorted into assending order.
    """
    scr = speed_change_rate
    # accelerations
    ds = speeds[1:] - speeds[:-1]
    # bin accelerations
    counts,intervals = np.histogram(ds)
    # find where there are only a few accelerations in a bin
    idx = np.nonzero(counts < scr)
    # find the indicies where accelerations were lower.
    diffidx = []
    if len(idx) > 0:
        id = idx[0][0]
        accel_threshold = intervals[id+1]
        idx = np.nonzero(ds < accel_threshold)[0]
        if len(idx) > 1:
            # look for where indices are not all in a row
            diffidx = idx[1:] - idx[:-1]
            didx = np.nonzero(diffidx > 1)[0]
            # confirm the following
            end_idx = idx[didx]
            # add last point assuming it is good
            end_idx = np.append(end_idx, len(ds))
            # add zero as the first index and get the start of each range
            start_idx = np.zeros(len(end_idx), dtype = np.int)
            for n in range(len(start_idx)-1):
                start_idx[n+1] = idx[didx[n]+1]
            # look for really short sections that are not worth using
            for n in range(len(start_idx)-1, -1, -1):
                if start_idx[n] > end_idx[n]-scr:
                    start_idx = np.delete(start_idx, n)
                    end_idx = np.delete(end_idx, n)
        else:
            start_idx = np.array([0])
            end_idx = np.array([-1])
    else:
        start_idx = np.array([0])
        end_idx = np.array([-1])
    # get the averages for the index ranges
    ave_speeds = []
    for n in range(len(start_idx)):
        ave_speeds.append(speeds[start_idx[n]:end_idx[n]].mean())
    if plotfig and len(diffidx) > 0:
        # make the speed decision plot
        f1 = plt.figure()
        af1 = f1.add_subplot(311)
        af1.plot(ds)
        af1.hlines(accel_threshold, 0, len(ds),'r')
        af1.vlines(end_idx,0,ds.max(),'r')
        af1.vlines(start_idx,0,ds.max(),'g')
        af1.set_xlabel('Ping Count')
        af1.set_ylabel('Acceleration ($m/s^2$)')
        af1.set_title(('How the Speeds Were Chosen'))
        af2 = f1.add_subplot(312)
        af2.plot(diffidx)
        af2.hlines(scr, 0, len(diffidx),'r')
        af2.vlines(didx,0,diffidx.max(),'r')
        af2.set_xlabel('Index')
        af2.set_ylabel('Index Diff')
        af2 = f1.add_subplot(312)
        af2.plot(diffidx)
        af2.hlines(scr, 0, len(diffidx),'r')
        af2.vlines(didx,0,diffidx.max(),'r')
        af2.set_xlabel('Index')
        af2.set_ylabel('Index Diff')
        af3 = f1.add_subplot(313)
        af3.plot(speeds)
        af3.hlines(ave_speeds, 0, len(speeds),'r')
        af3.set_xlabel('Index')
        af3.set_ylabel('Speed')
    # elif len(diffidx) > 0:
        # print 'no data to plot for speeds'
    return np.array(list(zip(start_idx,end_idx))), ave_speeds
    
def _assign_speed_bins(speeds, speed_bins, diff_from_bin = 0.5):
    """
    Takes speeds and the bins and returns the index for the ranges of each.
    diff_from_bin is used to decide how far off the center of the bin that a
    speed can be grouped into.
    """
    sb_idx = []
    used_speeds = []
    for sb in speed_bins:
        idxs = np.nonzero((speeds < sb + diff_from_bin) & (speeds > sb - diff_from_bin))[0]
        if len(idxs) > 0:
            sb_idx.append([idxs[0],idxs[-1]+1])
            used_speeds.append(sb)
    # find the indicies where accelerations were lower.
    return np.array(sb_idx), used_speeds

def summarize_directory(directory = '.', save_filemaps = False):
    """
    Print a summary of all the lines in the directory.
    """
    flist = glob(directory + '/*.all')
    flist.sort()
    if len(flist) > 0:
        f = os.path.split(flist[0])[1]
        #f = flist[0]
        infile = useall(f)
        vals = infile.get_stats(False)
        dtype = vals.dtype
        info = np.zeros(len(flist), dtype = dtype)
        info[0] = vals
        infile.close()
        for n in range(1,len(flist)):
            f = os.path.split(flist[n])[1]
            #f = flist[n]
            infile = useall(f, save_filemap = save_filemaps)
            info[n] = infile.get_stats(False)
        return info
    else:
        return None

def build_log(directory = '.', logname = 'all_stats.log', sep = ',',
              numping_comment = 100, save_filemaps = False):
    """
    Build a CSV file with the settings used in the directory.  Only the
    settings used in the beginning of each file are listed.
    """
    # make the header line
    vals = ['Filename','Mode','Pulse Type','Dual Swath','Coverage PORT/STBD (deg)',
            'Beam Spacing','Mean / STD Depth (m)','Heading (deg)','Speed (m/s)',
            'First Cast Time','Number of New Casts','Comments']
    header = ''
    for v in vals:
        header = header + v + sep
    header = header + '\n'
    # get the log info from the files
    log = summarize_directory(directory, save_filemaps)
    outfile = open(logname, 'w')
    outfile.write(header)
    # write the data for each file
    for n in log:
        outfile.write(n['Filename'] + sep)
        mode = n['Mode'][-4:]
        dualswath = n['Mode'][:2]
        if n['EMModel'] == 2040 or n['EMModel'] == 2045:
            if mode == '0000':
                outfile.write('200 kHz')
            elif mode == '0001':
                outfile.write('300 kHz')
            elif mode == '0010':
                outfile.write('400 kHz')
            else:
                outfile.write('Unknown')
            outfile.write(sep)
            pulsetype = n['Mode2'][1:6]
            if pulsetype == '11100':
                outfile.write('Long FM')
            elif pulsetype == '11000':
                outfile.write('Short FM')
            elif pulsetype == '00011':
                outfile.write('FM')
            elif pulsetype == '10100':
                outfile.write('Extra Long CW')
            elif pulsetype == '10000':
                outfile.write('Very Long CW')
            elif pulsetype == '01100' or pulsetype == '00010':
                outfile.write('Long CW')
            elif pulsetype == '01000' or pulsetype == '00001':
                outfile.write('Medium CW')
            elif pulsetype == '00000':
                outfile.write('Short CW')
            outfile.write(sep)
        else:
            pulsetype = n['Mode'][2:4]
            if mode == '0000':
                outfile.write('Very Shallow')
            elif mode == '0001':
                outfile.write('Shallow')
            elif mode == '0010':
                outfile.write('Medium')
            elif mode == '0011':
                outfile.write('Deep')
            elif mode == '0100':
                outfile.write('Very Deep')
            elif mode == '0101':
                outfile.write('Extra Deep')
            outfile.write(sep)
            if pulsetype == '00':
                outfile.write('CW')
            elif pulsetype == '01':
                outfile.write('Mixed')
            elif pulsetype == '10':
                outfile.write('FM')
            outfile.write(sep)
        if dualswath == '00':
            outfile.write('Single Swath')
        elif dualswath == '01':
            outfile.write('Fixed')
        elif dualswath == '10':
            outfile.write('Dynamic')
        outfile.write(sep)
        outfile.write(str(n['AngularLimits'][0]) + '/' + str(n['AngularLimits'][1]))
        outfile.write(sep)
        if n['BeamSpacing'][-2:] == '00':
            outfile.write('Beam Spacing')
        elif n['BeamSpacing'][-2:] == '01':
            outfile.write('Equidistant')
        elif n['BeamSpacing'][-2:] == '10':
            outfile.write('Equiangular')
        elif n['BeamSpacing'][-2:] == '11':
            outfile.write('HD Equidistant')
        outfile.write(sep)
        if np.isnan(n['Depth'][0]):
            outfile.write('No Depth')
        else:
            outfile.write(str(int(n['Depth'][0])) + ' / ' + str(int(n['Depth'][1])))
        outfile.write(sep)
        outfile.write(str(round(n['Heading'][0],1)))
        outfile.write(sep)
        outfile.write(str(round(n['Speed'][0],1)))
        outfile.write(sep)
        outfile.write(n['CastTime'])
        outfile.write(sep)
        outfile.write(str(n['NewCastNumber']))
        comment = False
        if n['ModeChange']:
            outfile.write(sep)
            comment = True
            outfile.write('Mode changed during file')
        if n['NumberOfPings'] < numping_comment:
            if comment:
                outfile.write(';')
            else:
                outfile.write(sep)
                comment = True
            outfile.write('Line has ' + str(n['NumberOfPings']) + ' pings')
        if n['OperatorStationStatus'] == 'Fail':
            if comment:
                outfile.write(';')
            else:
                outfile.write(sep)
                comment = True
            outfile.write('Error Found in Operator Station Status')
        if n['ProcessingUnitStatus'] == 'Fail':
            if comment:
                outfile.write(';')
            else:
                outfile.write(sep)
                comment = True
            outfile.write('Error Found in Processing Unit Status')
        if n['BSPStatus'] == 'Fail':
            if comment:
                outfile.write(';')
            else:
                outfile.write(sep)
                comment = True
            outfile.write('Error Found in BSP Status')
        if n['SonarHeadOrTransceiverStatus'] == 'Fail':
            if comment:
                outfile.write(';')
            else:
                outfile.write(sep)
                comment = True
            outfile.write('Error Found in Sonar Head Or Transceiver Status')
        outfile.write('\n')
    outfile.close()

def plot_all_nav(directory = '.', add_map = False):
    """
    Plots the parts of the navarray from all files in the directory.
    """
    fig = plt.figure()
    ax1 = fig.add_subplot(221)
    ax2 = fig.add_subplot(222)
    ax3 = fig.add_subplot(614, sharex = ax2)
    ax4 = fig.add_subplot(615, sharex = ax2)
    ax5 = fig.add_subplot(616, sharex = ax2)
    flist = glob(directory + '/*.all')
    flist.sort()
    clist = ['b','r','g','k','y','c']
    n = 0
    for f in flist:
        a = allRead(f)
        if os.path.exists(f + '.nav'):
            a.load_navarray()
        else:
            a._build_navarray()
            a.save_navarray()
        ax1.plot(a.navarray['80'][:,1],a.navarray['80'][:,2], clist[n])
        ax1.set_xlabel('Longitude (Degrees)')
        ax1.set_ylabel('Latitude (Degrees)')
        ax1.grid(True)
        ax2.plot(a.navarray['65'][:,0],a.navarray['65'][:,4], clist[n])
        ax2.set_ylabel('Heading (Degrees)')
        ax2.set_xlabel('Time (Seconds)')
        ax2.grid(True)
        if '104' in a.navarray:
            ax3.plot(a.navarray['104'][:,0],a.navarray['104'][:,1], clist[n])
        ax3.set_ylabel('Height (Meters)')
        ax3.grid(True)
        ax4.plot(a.navarray['65'][:,0],a.navarray['65'][:,1], clist[n])
        ax4.plot(a.navarray['65'][:,0],a.navarray['65'][:,2], clist[n] + '--')
        ax4.set_ylabel('Degress')
        ax4.legend(('Roll','Pitch'))
        ax4.grid(True)
        ax5.plot(a.navarray['65'][:,0],a.navarray['65'][:,3], clist[n])
        ax5.set_ylabel('Heave (Meters)')
        ax5.set_xlabel('Time (Seconds)')
        ax5.grid(True)
        n += 1
        if n >= len(clist):
            n = 0
        plt.draw()
    if add_map:
        xlim = ax1.get_xlim()
        ylim = ax1.get_ylim() 
        m = Basemap(llcrnrlon = xlim[0], urcrnrlon = xlim[1], 
                    llcrnrlat = ylim[0], urcrnrlat = ylim[1],
                    resolution = 'l', ax = ax1)
        m.drawcoastlines()

def _checksum_all_bytes(bytes):
    # Calculate checksum by sum of bytes method
    bytes = bytearray(bytes)
    chk = sum(bytes) % 2**16
    return np.uint16(chk)

def checksum_rawdatablock(rawdatablock):
    # checksum for bytes between STX and ETX
    # Assuming that the format of the datablock is:
    # 4 bytes datagram size, 1 byte STX -- DATA -- 1 byte ETX, 2 byte checksum
    # I.e. 5 bytes excluded at start and 3 bytes at the end
    return _checksum_all_bytes(rawdatablock[5:-3])

def main():        
    if len(sys.argv) > 1:
        a = allRead(sys.argv[1])
        a.mapfile(True)
        a.close()
    else:
        print("No filename provided.")
        
if __name__ == '__main__':
    main()