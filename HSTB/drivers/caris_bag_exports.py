import subprocess
import os

from winreg import ConnectRegistry, HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx
import numpy

from HSTB.drivers.carisapi import get_bands_from_csar, command_finder_hips
from HSTB.drivers import bag


caris_batch, caris_version = command_finder_hips()


class CSAR_Exception(IOError):
    pass


# Move this to carisapi when carisapi is updated
def vr_csar_to_vrbag(csar_path, bag_path, band="Depth", uncertainty="Uncertainty", uncertainty_type="PRODUCT_UNCERT",
                     abstract="VR Bag Export", status="ONGOING", vert_datum="4326",
                     party_name="Pydro", party_position="Silver Spring", party_org="NOAA, NOS", party_role="POINT_OF_CONTACT",
                     legal="OTHER_RESTRICTIONS", other="This dataset is not a standalone navigational product",
                     security="UNCLASSIFIED", notes="Unclassified", verbose=True):
    """
    Wrap the carisbatch.exe ExportVRSurfaceToBAG command
    Parameters
    ----------
    csar_path
    bag_path
    band
    uncertainty
    uncertainty_type
    abstract
    status
    vert_datum
    party_name
    party_position
    party_org
    party_role
    legal
    other
    security
    notes
    verbose

    Returns
    -------

    """
    fullcommand = (
        r'"%s" --run ExportVRSurfaceToBAG' % caris_batch,
        '--include-band %s' % band,
        '--uncertainty "%s"' % uncertainty,
        '--uncertainty-type %s' % uncertainty_type,
        '--abstract "%s"' % abstract,
        '--status %s' % status,
        '--vertical-datum %s' % vert_datum,
        '--party-name "%s"' % party_name,
        '--party-position "%s"' % party_position,
        '--party-organization "%s"' % party_org,
        '--party-role %s' % party_role,
        '--legal-constraints %s' % legal,
        '--other-constraints "%s"' % other,
        '--security-constraints %s' % security,
        '--notes "%s"' % notes,
        '"' + csar_path + '"',
        '"' + bag_path + '"'
    )
    if verbose:
        print(fullcommand)
    p = subprocess.Popen(' '.join(fullcommand))
    p.wait()


def convert_csar(surface, outputname, output_type="GeoTIFF", bandname='Depth', additional_opts="", verbose=True):
    '''Runs ExportRaster with all the options.  Example: carisbatch.exe --run ExportRaster --output-format
    GeoTIFF --include-band Depth C:\HIPSData\Products\VR.csar C:\HIPSData\Products\VR.tiff'''

    fullcommand = '"' + caris_batch + '" --run ExportRaster --output-format ' + output_type + ' --include-band'
    fullcommand += ' ' + bandname + ' ' + additional_opts + ' "' + surface + '" "' + outputname + '"'
    if verbose:
        print(fullcommand)
    p = subprocess.Popen(fullcommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    data = p.communicate()
    if verbose:
        print(data)
    return data


class TemporaryCsarExport(object):
    extensions = {"GeoTIFF": "tif", "BAG": "bag"}

    def __init__(self, csar_file, bandname="", export="GeoTIFF", permanent=False):
        """ Creates a temporary export raster of the csar supplied.  Deletes the file when the object is deleted.
        bandname will use Depth or Elevation or Intensity if not otherwise specified
        export can be BAG or GeoTIFF
        """
        self.permanent = permanent
        self.bandname = self.get_bandname(csar_file, bandname)
        self.export_filename = self.get_unique_name(csar_file, self.extensions[export])

        if export == "BAG":
            additional_opts = '-L COPYRIGHT -a "abstract descr." -D 4326 -N "exported for survey outlines" -R USER -A UNCLASSIFIED -s ONGOING -U UNKNOWN'
        elif export == "GeoTIFF":
            additional_opts = ""
        else:
            raise Exception("Unrecognized export type")
        use_bandname = self.bandname
        if " " in use_bandname:
            use_bandname = '"' + use_bandname + '"'  # if the bandname has a space in it, we need to wrap it in quotes
        data = convert_csar(csar_file, self.export_filename, output_type=export, bandname=use_bandname, additional_opts=additional_opts,
                                verbose=False)
        if data[1]:
            raise CSAR_Exception
        else:
            print(data[0])

    def get_bandname(self, csar_file, prefer_bandname="", fallback=True):
        """
        Parameters
        ----------
        csar_file
            full file path to csar data
        prefer_bandname
            Band name to check first (or only - based on fallback)
        fallback
            Specify if standard band names should be checked if the preferred one is not in the data

        Returns
        -------
        string
            band name found in the csar data

        Raises
        ------
        Exception
            If none of the default bandnames are found.
            Also if the prefer_bandname is not found and fallback=False was specified

        """
        bands = get_bands_from_csar(csar_file)
        bands_lower = [b.lower() for b in bands]
        # print(bands)
        bandname = prefer_bandname
        # if no band name given then use one of the most common ones if found.
        if not bandname or fallback:
            for b in (bandname, "Depth", "Elevation", "Intensity"):
                if b.lower() in bands_lower:
                    index = bands_lower.index(b.lower())
                    bandname = bands[index]
                    break
        if bandname not in bands:
            if fallback and len(bands) == 1:
                bandname = bands[0]
            else:
                raise Exception("Did not find requested band '{}' layer in {}".format(bandname, str(bands)))
        return bandname

    def get_band_used(self):
        return self.bandname

    def get_exported_filename(self):
        return self.export_filename

    @staticmethod
    def make_name(basename, num, ext):
        return basename + "." + str(num) + "." + ext

    @staticmethod
    def get_unique_name(basename, ext):
        num = 0
        while os.path.exists(TemporaryCsarExport.make_name(basename, num, ext)):
            num += 1
        return TemporaryCsarExport.make_name(basename, num, ext)

    def __del__(self):
        if not self.permanent:
            try:
                os.remove(self.get_exported_filename())
            except FileNotFoundError:  # likely an error exoorting from Caris (a VR surface will cause this)
                pass
            except PermissionError:
                print("Permission error removing - did another program open it?", self.get_exported_filename())


class TemporaryBAGExport(TemporaryCsarExport):

    def __init__(self, input_file, export="GeoTIFF", resX=None, resY=None, permanent=False, input_args="", output_args=""):
        """ Creates a temporary export raster of the bag supplied.  Deletes the file when the object is deleted.
        bandname will use Depth or Elevation or Intensity if not otherwise specified
        export can be BAG or GeoTIFF
        """
        self.permanent = permanent
        self.bandname = "Elevation"
        self.export_filename = self.get_unique_name(input_file, self.extensions[export])
        # let the resolution go to full res and then have the simplify reduce it.  (1/2 the min res)
        # nodata value is empirical as letting it be numpy.nan wasn't working in the polygonize
        cell_size = numpy.min(resX, resY)
        bag_supergrid_dx, bag_supergrid_dy, self.sr_cell_size = bag.VRBag_to_TIF(input_file, self.export_filename, sr_cell_size=cell_size,
                                                                                 mode=bag.MIN, nodata=3.4028234663852886e+38)
        # gdal_ops.bag_to_raster(input_file, self.export_filename, resX=resX, resY=resY, input_args=input_args, output_args=output_args)


class TemporaryVR_BagExport(TemporaryCsarExport):
    def __init__(self, csar_file, use_bandname="", permanent=False):
        """ Creates a temporary export VR Bag of the CSAR supplied.  Deletes the file when the object is deleted.
        bandname will use Depth or Elevation or Intensity if not otherwise specified
        export can be BAG or GeoTIFF
        """
        self.permanent = permanent
        self.bandname = self.get_bandname(csar_file, use_bandname)
        self.export_filename = self.get_unique_name(csar_file, self.extensions["BAG"])

        vr_csar_to_vrbag(csar_file, self.export_filename, band=self.bandname)
