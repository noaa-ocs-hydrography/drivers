import os

from hyo2.soundspeed.atlas import woa13, woa18
from hyo2.abc.lib.progress.cli_progress import CliProgress

# from hyo2.soundspeed.soundspeed import SoundSpeedLibrary

# load WOA in the default sound speed manager place, if not found then download it automatically

# this is just needed for progress reporting, the default goes to command line
# a tqdm console progress could be made and replacethe default one from prj, if the time was warranted.
# prj = SoundSpeedLibrary()

# set the data folder somewhere else if you like but it needs to end with a directory named WOA13 for SSM to work right,
# instead of prj.data_folder it could be os.path.split(__file__)[0] to be local to this file.
# active_model = prj.atlases.woa13  # Let SSM make the path choice - change here to RTOFS etc if desired

try:
    # put the data in supplementals
    import HSTB.resources
    import tqdm

    folder = HSTB.resources.path_to_NOAA("supplementals", "woa13")

except:
    # if that failed then put it local to this script
    folder = os.path.split(__file__)[0]


class fake_project:
    def __init__(self):
        self.progress = CliProgress()


# Try WOA 2018, if not there then try WOA 2013.
# If neither exist then download 2018
active_model = woa18.Woa18(folder, fake_project())
loaded = active_model.is_present()
if not loaded:
    active_model = woa13.Woa13(folder, fake_project())
    loaded = active_model.is_present()

# Neither exist so download 2018
if not loaded:
    active_model = woa18.Woa18(folder, fake_project())
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
    avg_profile = profiles.l[0]
    min_profile = profiles.l[1]
    max_profile = profiles.l[2]
    if screen_dump:
        for p in min_profile, avg_profile, max_profile:
            print(list(zip(p.data.depth, p.data.speed)))
    return avg_profile, min_profile, max_profile

# sample usage:
# from HSTB.scripts import woa
# ave_cast, min_cast, max_cast = woa.get_profile(lat, lon, datetime.utcfromtimestamp(posix))
