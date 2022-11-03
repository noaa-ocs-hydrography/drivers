import datetime
import os

import numpy

from hyo2.soundspeed.atlas import woa13, woa18
from hyo2.abc.lib.progress.cli_progress import CliProgress
from hyo2.soundspeed.formats.writers.caris import Caris

# from hyo2.soundspeed.soundspeed import SoundSpeedLibrary

# load WOA in the default sound speed manager place, if not found then download it automatically

# this is just needed for progress reporting, the default goes to command line
# a tqdm console progress could be made and replace the default one from prj, if the time was warranted.
# prj = SoundSpeedLibrary()

# set the data folder somewhere else if you like but it needs to end with a directory named WOA13 for SSM to work right,
# instead of prj.data_folder it could be os.path.split(__file__)[0] to be local to this file.
# active_model = prj.atlases.woa13  # Let SSM make the path choice - change here to RTOFS etc if desired

try:
    # put the data in supplementals
    import HSTB.resources

    woa13_folder = HSTB.resources.path_to_NOAA("supplementals", "woa13")
    woa18_folder = HSTB.resources.path_to_NOAA("supplementals", "woa18")

except:
    # if that failed then put it local to this script
    woa18_folder = os.path.split(__file__)[0]
    woa13_folder = woa18_folder

class fake_project:
    def __init__(self):
        self.progress = CliProgress()


# Try WOA 2018, if not there then try WOA 2013.
# If neither exist then download 2018
active_model = woa18.Woa18(woa18_folder, fake_project())
loaded = active_model.is_present()
if not loaded:
    active_model = woa13.Woa13(woa13_folder, fake_project())
    loaded = active_model.is_present()

# Neither exist so download 2018
if not loaded:
    active_model = woa18.Woa18(woa18_folder, fake_project())
    print("Downloading Model '{}' to {}".format(active_model.desc, active_model.data_folder))
    # note: don't call prj.download_woa13() since it will not use the directory
    # set in active_woa unless you initialize prj properly too.
    downloaded = active_model.download_db()
    if downloaded:
        print("Finished downloading WOA to ", active_model.data_folder)
        loaded = active_model.load_grids()
        if not loaded:
            raise FileNotFoundError("Model data did not load properly.  Is it corrupt?")
            # print("failed to load WOA")
    else:
        raise FileNotFoundError("Model was not found AND failed to download from UNH")
        # print("failed to load WOA")


def get_profile(lat, lon, dt=None, screen_dump=False):
    """ Create a synthetic cast from the World Ocean Atlas.  Currently using WOA 2018 or 2013
    Parameters
    ----------
    lat : float
        latitude in degrees
    lon : float
        longitude in degrees
    dt : datetime object
        datetime.datetime object.  Month is the most important attribute
    screen_dump : bool
        print to the screen for cheap test/debugging

    Returns
    -------
    avg_profile, min_profile, max_profile which are hyo2.soundspeed.profile.profile.Profile objects

    """
    # profiles = active_woa.query(38.118125, -76.214864)  # uses today
    # FYI only the month is used in the lookup for a profile,
    # the other time info goes into metadata which NBS will probably discard
    profiles = active_model.query(lat, lon, dt)  # May 18, 2018 at 1205
    if profiles is not None:
        avg_profile = profiles.l[0]
        min_profile = profiles.l[1]
        max_profile = profiles.l[2]
        if screen_dump:
            for p in min_profile, avg_profile, max_profile:
                print(list(zip(p.data.depth, p.data.speed)))
    else:
        avg_profile, min_profile, max_profile = None, None, None
    return avg_profile, min_profile, max_profile


def iter_woa_lat_lon_times(lat1, lon1, time1, lat2, lon2, time2):
    """ Given bounding lats, lons and times, iterates all the unique positions and times that SoundSpeedManager could supply.

    Parameters
    ----------
    lat1
        a bounding latituge in degrees
    lon1
        a bounding longitude in degrees
    time1
        a bounding datetime object
    lat2
        a bounding latituge in degrees
    lon2
        a bounding longitude in degrees
    time2
        a bounding datetime object

    Returns
    -------
    lat, lon, datetime

    """
    # Get the bounding indices to figure out how many points to evaluate at
    lat_base_idx1, lon_base_idx1 = active_model.grid_coords(lat=lat1, lon=lon1)
    lat_base_idx2, lon_base_idx2 = active_model.grid_coords(lat=lat2, lon=lon2)
    num_lats = abs(lat_base_idx2 - lat_base_idx1) + 1
    num_lons = abs(lon_base_idx2 - lon_base_idx1) + 1
    # make an array of the lat,lon points to evaluate the WOA at
    lats = numpy.linspace(lat1, lat2, num_lats)
    lons = numpy.linspace(lon1, lon2, num_lons)
    # Loop from the beginning time to the end time by month since that is the resolution of the WOA
    date1 = datetime.datetime(time1.year, time1.month, 1)
    date2 = datetime.datetime(time2.year, time2.month, 1)
    current = min(date1, date2)
    current = datetime.datetime(current.year, current.month, 1)  # first day of the new month
    end = max(date1, date2)
    while current <= end:
        for lat in lats:
            for lon in lons:
                yield lat, lon, current
        current = current + datetime.timedelta(days=32)
        current = datetime.datetime(current.year, current.month, 1)  # first day of the next month


def iter_woa_lat_lon_times_gridded(lat1, lon1, time1, lat2, lon2, time2):
    """ Similar to iter_woa_lat_lon_times but returns lat and lon of the World Ocean Atlas positions
    rather than using numpy.linspace on the supplied lat/lon

    Returns
    -------
    lat, lon, datetime

    """
    for raw_lat, raw_lon, dt in iter_woa_lat_lon_times(lat1, lon1, time1, lat2, lon2, time2):
        lat_idx, lon_idx = active_model.grid_coords(raw_lat, raw_lon)
        yield active_model.lat[lat_idx], active_model.lon[lon_idx], dt



def make_svp_file(lat, lon, dt, output_filename, writer=None):
    """ Create a sound speed file, defaults to Caris SVP format if not supplied.
    Parameters
    ----------
    lat
        latitude in degrees
    lon
        longitude in degrees
    dt
        datetime of the cast desired
    output_filename

    writer
        SoundSpeedManager soundspeed.format.writer instance, Caris() is used as a default

    Returns
    -------
    boolean
        True if the WOA contained data and it was written to the output_filename

    """
    if writer is None:
        writer = Caris()  # appends casts by default
    output_path, local_filename = os.path.split(output_filename)
    if not local_filename:
        local_filename = None  # convert empty string to None and allow for SSM to make its own filename
    prj = fake_project()

    profiles = active_model.query(lat, lon, dt)  # May 18, 2018 at 1205
    if profiles is not None:
        # if we don't supply a local_filename then SSM will make filenames based on WOA version + datetime
        ret = writer.write(ssp=profiles, data_path=output_path, data_file=local_filename, project=prj)
    else:
        ret = False
    return ret


def make_svp_file_range(lat1, lon1, time1, lat2, lon2, time2, output_filename):
    # The world ocean atlas has data at some resolution (5 degree, 1 degree or 0.25 degree depending on version)
    #   and has annual, seasonal and monthly casts.
    # Take the given bounds in lat/lon and find how many positions should be made
    # Then find which months should be used
    # Then create a multicast Caris SVP format file with those positions and times containing the average profile returned by sound speed manager

    for lat, lon, dt in iter_woa_lat_lon_times(lat1, lon1, time1, lat2, lon2, time2):
        make_svp_file(lat, lon, dt, output_filename)


# if __name__ == '__main__':
# sample usage:
#     ave_cast, min_cast, max_cast = get_profile(lat, lon, datetime.utcfromtimestamp(posix))
#     llt = list(iter_woa_lat_lon_times_gridded(38.5, -75, datetime.datetime(2020, 2, 1), 39, -74.5, datetime.datetime(2020, 3, 1)))
#     make_svp_file_range(38.5, -75, datetime.datetime(2020, 2, 1), 39, -74.5, datetime.datetime(2020, 3, 1), r"c:\\temp\\test.svp")  # bethany beach, DE