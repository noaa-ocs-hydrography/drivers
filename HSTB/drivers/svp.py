import os
import numpy as np
from datetime import datetime, timezone
from pyproj import CRS
from typing import Union

from HSTB.kluster import dms


class BaseSvp:
    """
    Base class for sound velocity file reader.  Currently only extended by CarisSvp, to read caris svp files.
    """
    def __init__(self):
        self.svpfile = ''
        self.sv_version = ''
        self.sv_name = ''
        self.sv_header = []
        self.sv_data = []
        self.julian_day = []
        self.time = []
        self.utctimestamp = []
        self.latitude = []
        self.longitude = []
        self.zone = None
        self.hemisphere = None
        self.src_crs = None
        self.src_epsg = None

    def build_epsg(self):
        """
        Coordinates are entered as latitude/longitude without any coordinate system encoding.  We assume WGS84 and 
        provide the potential zone/hemisphere for the data.  Also provide the geographic coordinate system EPSG for 
        the given lat lon coordinates
        """

        self.zone = [int((np.floor((int(d) + 180) / 6) % 60) + 1) for d in self.longitude]
        if np.unique(self.zone).size > 1:
            print('WARNING: Found profiles that are of differing zones: zone numbers {}'.format(self.zone))
        self.hemisphere = ['S' if l < 1 else 'N' for l in self.latitude]
        self.src_crs = [CRS.from_proj4('+proj=longlat +datum=WGS84'.format(zn[0], zn[1])) for zn in
                        zip(self.zone, self.hemisphere)]
        self.src_epsg = [c.to_epsg() for c in self.src_crs]
    
    def return_dict(self):
        """
        Export out the information in the class as a dict
        
        Returns
        -------
        dict
            dictionary of the class information
        """
        
        svp_dict = {'number_of_profiles': len(self.sv_data), 'svp_julian_day': self.julian_day, 
                    'svp_time_utc': self.utctimestamp, 'latitude': self.latitude, 'longitude': self.longitude,
                    'source_epsg': self.src_epsg, 'utm_zone': self.zone, 'utm_hemisphere': self.hemisphere,
                    'number_of_layers': [len(sv) for sv in self.sv_data], 'profiles': self.sv_data}
        return svp_dict

    def return_cast_statistics(self, cast_index: int = 0):
        """
        Build min,max,mean of depth and sound velocity for the specified cast

        Parameters
        ----------
        cast_index
            index of the cast in the class attribute lists

        Returns
        -------
        float
            minimum depth of cast in meters
        float
            maximum depth of cast in meters
        float
            mean depth of cast in meters
        float
            minimum sound velocity in meters per second
        float
            maximum sound velocity in meters per second
        float
            mean sound velocity in meters per second
        """

        cast = np.array(self.sv_data[cast_index])
        min_depth = cast[:, 0].min()
        max_depth = cast[:, 0].max()
        mean_depth = np.round(cast[:, 0].mean(), 3)
        min_sv = cast[:, 1].min()
        max_sv = cast[:, 1].max()
        mean_sv = np.round(cast[:, 1].mean(), 3)
        return min_depth, max_depth, mean_depth, min_sv, max_sv, mean_sv

    def summarize_file(self):
        """
        Prints a summary of the file, all casts contained and warnings related to utm zones, etc.
        """
        
        print('File "{}" contains {} casts'.format(self.sv_name, len(self.sv_header)))
        u_zones = np.unique(self.zone)
        u_hemisphere = np.unique(self.hemisphere)
        if u_zones.size == 1 and u_hemisphere.size == 1:
            print('- casts are all within the same utm zone/hemisphere: {}{}'.format(self.zone[0], self.hemisphere[0]))
        else:
            if u_zones.size > 1:
                print('*** found multiple zones in casts: {}'.format(list(u_zones)))
            if u_hemisphere.size > 1:
                print('*** found multiple hemispheres in casts: {}'.format(list(u_zones)))
        for cnt, utctime in enumerate(self.utctimestamp):
            print('Cast {}: {} EPSG:{} {} {}, {} layers'.format(cnt, utctime, self.src_epsg[cnt], self.latitude[cnt],
                                                                self.longitude[cnt], len(self.sv_data[cnt])))

    def summarize_cast(self, cast_index: int = 0):
        """
        Prints a summary of the cast selected (using the cast_index) including some basic statistics related to the 
        cast.
        
        Parameters
        ----------
        cast_index
            integer index of the cast in the base class lists
        """
        
        print('Cast {}: {} EPSG:{} {} {}, {} layers'.format(cast_index, self.utctimestamp[cast_index],
                                                            self.src_epsg[cast_index],
                                                            self.latitude[cast_index], self.longitude[cast_index],
                                                            len(self.sv_data[cast_index])))
        mind, maxd, meand, minsv, maxsv, meansv = self.return_cast_statistics(cast_index)
        print('Min depth: {}m, Max depth: {}m, Mean depth: {}m'.format(mind, maxd, meand))
        print('Min sv: {}m/s, Max sv: {}m/s, Mean sv: {}m/s'.format(minsv, maxsv, meansv))

    def write_caris(self, outputfile: str):
        """
        Write all casts contained in this class to a file, using the caris SVP format
        
        Parameters
        ----------
        outputfile
            absolute file path to the file you want to create with this method
        """
        
        if self.sv_header is None or self.sv_data is None:
            raise ValueError('No sv data found in class to write')
        if os.path.exists(outputfile):
            raise EnvironmentError(
                '{} already exists, please choose a file path that does not exist'.format(outputfile))
        self.sv_name = os.path.split(outputfile)[1]
        with open(outputfile, 'w+') as ofile:
            ofile.write('[SVP_VERSION_2]\n')
            ofile.write(self.sv_name + '\n')
            for cnt, jday in enumerate(self.julian_day):
                caris_time = datetime.utcfromtimestamp(self.utctimestamp[cnt]).strftime('%H:%M:%S')
                caris_lat = ':'.join([str(int(np.around(d))) for d in dms.dd2dms(self.latitude[cnt])])
                caris_lon = ':'.join([str(int(np.around(d))) for d in dms.dd2dms(self.longitude[cnt])])
                ofile.writelines(' '.join(['Section', jday, caris_time, caris_lat, caris_lon]) + '\n')
                ofile.writelines('\n'.join([str(n[0]) + ' ' + str(n[1]) for n in self.sv_data[cnt]]) + '\n')


class CarisSvp(BaseSvp):
    """
    Caris SVP file format reader

    From the online documentation:

    The first line of the file specifies the version of the SVP file
    The second line displays the name of the SVP file
    The next line is a section heading for each profile, containing:
     - the year and day (Julian date) that the profile was recorded
     - time stamp when the profile was recorded
     - the latitude and longitude of the profile location
     - the text of a comment added to the profile using the Edit Profile function
     - the SVP data displayed in two columns, one column containing the depth, and the other, the speed value for that depth.

    *** ASSUMING ALL TIME STAMPS PROVIDED IN SVP ARE IN UTC TIME. I can't find this mentioned anywhere, but all the SVP files
    that I have show that is true.  I think. ***
    *** ASSUMING ALL LAT/LON VALUES PROVIDED IN SVP ARE USING WGS84 COORDINATE SYSTEM.  Again this metadata is not
    encoded, and I believe depends on the source sensor. This assumption should not be that big a deal for operational
    use of this class. ***

    """

    def __init__(self, svpfile: str):
        """
        Initialize all the cast specific data as lists, where each element of the list is one cast from the svp file.

        The svp file may contain multiple svp file datasets, all concatenated within the same file
        
        EX:
        [SVP_VERSION_2]
        S222_PatchTest_DN077_master.svp
        Section 2020-077 05:34 37:14:25 -076:05:06
        0.283000 1475.243261
        1.283000 1473.016700
        2.283000 1471.911006
        3.283000 1471.861834
        4.283000 1472.012858
        Section 2020-077 09:59 37:15:45 -076:04:33
        0.095000 1475.384307
        1.095000 1474.512619
        2.095000 1473.674762
        3.095000 1472.971069
        4.095000 1472.976373
        4.577824 1473.500000
        
        self.sv_header = ['Section 2020-077 05:34 37:14:25 -076:05:06', 'Section 2020-077 09:59 37:15:45 -076:04:33']
        self.sv_data = [['0.283000 1475.243261',
                         '1.283000 1473.016700',
                         '2.283000 1471.911006',
                         '3.283000 1471.861834',
                         '4.283000 1472.012858'],
                        ['0.095000 1475.384307',
                         '1.095000 1474.512619',
                         '2.095000 1473.674762',
                         '3.095000 1472.971069',
                         '4.095000 1472.976373',
                         '4.577824 1473.500000']]    
        
        Parameters
        ----------
        svpfile
            absolute file path to the svp file, must have an .svp extension 
        """
        
        super().__init__()
        self.svpfile = svpfile
        self.sv_version, self.sv_name, self.sv_header, self.sv_data = self._caris_read_svp_elements(svpfile)
        self.julian_day, self.time, self.utctimestamp, self.latitude, self.longitude = self._caris_parse_svp_header(self.sv_header)
        self.build_epsg()
        
    def _caris_read_svp_elements(self, svp_path: str):
        """
        Read each cast contained in the caris svp file, parsing out the various fields.  Supports caris svp files that
        are concatenated.
        
        Parameters
        ----------
        svp_path
            full file path to the caris svp file
            
        Returns
        -------
        str
            caris svp version string, ex: 'SVP_VERSION_2'
        str
            filename of the svp file, ex: 'S222_PatchTest_DN077_master.svp'
        list
            list of caris svp headers
        list
            list of caris svp cast data (list of lists of depth vs sv)
        """
        
        if os.path.splitext(svp_path)[1] == '.svp':
            with open(svp_path, 'r') as svp:
                sv_version = svp.readline().rstrip().lstrip('[').rstrip(']')
                sv_name = svp.readline().rstrip()
                sv_header = svp.readline().rstrip()
                sv_data = svp.readlines()
                # look for concatenated files, they would have headers throughout the file
                list_sv_data = []
                list_sv_header = []
                
                new_data = []
                new_header = sv_header
                for ln in sv_data:
                    if ln[0:7] == 'Section':
                        list_sv_data.append(new_data)
                        list_sv_header.append(new_header)
                        new_header = ln.rstrip()
                        new_data = []
                    else:
                        new_data.append(tuple([float(x) for x in ln.rstrip().split()]))
                # catch the last catch (which will not end in a header)
                list_sv_data.append(new_data)
                list_sv_header.append(new_header)
        else:
            raise ValueError('Provided file does not have the .svp extension: {}'.format(svp_path))
        return sv_version, sv_name, list_sv_header, list_sv_data
    
    
    def _caris_parse_svp_header(self, sv_header: str):
        """
        Parses each caris svp header found.
        
        Parameters
        ----------
        sv_header
            space delimited caris svp header as string

        Returns
        -------
        list
            list of julian day identifiers for each cast, ex: ['2020-077', '2020-077']
        list
            list of times of each cast in caris svp format, ex: ['05:34', '09:59']
        list
            list of utctimestamps for each cast, ex: [1584423240.0, 1584439140.0]
        list
            list of latitudes for each cast, ex: [37.24027777777778, 37.2625]
        list
            list of longitudes for each cast, ex: [-76.085, -76.07583333333334]
        """

        header = None
        try:
            date = []
            svtime = []
            utctimestamp = []
            lat = []
            long = []
            for header in sv_header:
                s, d, tm, la, lo = header.split()
                date.append(d)
                svtime.append(tm)
                lat.append(np.round(dms.parse_dms_to_dd(la), 8))
                long.append(np.round(dms.parse_dms_to_dd(lo), 8))
                try:
                    if len(tm) == 5:
                        utctime = datetime.strptime(d + ' ' + tm, '%Y-%j %H:%M').replace(tzinfo=timezone.utc)
                    else:
                        utctime = datetime.strptime(d + ' ' + tm, '%Y-%j %H:%M:%S').replace(tzinfo=timezone.utc)
                    utctime = utctime.timestamp()
                    utctimestamp.append(utctime)
                except (TypeError, ValueError):
                    utctimestamp.append(None)
                    print('Unable to find valid date and time identifiers: {} {}.  Expect format YYYY-DDD HH:MM:SS'.format(d, tm))
        except:
            error = 'Error reading header\n{}\n'.format(header)
            error += 'Please verify that the svp file has the correct header'
            raise IOError(error)
        return date, svtime, utctimestamp, lat, long
