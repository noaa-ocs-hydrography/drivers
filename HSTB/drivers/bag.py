import os
from xml.etree import ElementTree as et
import datetime
import tempfile
import math

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    def tqdm(iterate_stuff, *args, **kywrds):
        return iterate_stuff  # if this doesn't work, try iter(iterate_stuff)
import h5py
import numpy

try:
    import scipy
except ModuleNotFoundError:
    print("scipy did not import, interpolate_vr_bag function will not work")
from osgeo import gdal, osr, ogr

from HSTB.shared.gridded_coords import Grid, affine_center
import HSTB.resources

DEBUGGING = False
if DEBUGGING:
    import matplotlib.pyplot as plt

# current bag 1.5+ spec
gmd = '{http://www.isotc211.org/2005/gmd}'
gml = '{http://www.opengis.net/gml/3.2}'
gco = '{http://www.isotc211.org/2005/gco}'
gmi = '{http://www.isotc211.org/2005/gmi}'
bagschema = "{http://www.opennavsurf.org/schema/bag}"
xlink = '{http://www.w3.org/1999/xlink}'
xsi = '{http://www.w3.org/2001/XMLSchema-instance}'

# bag 1.0 - 1.4 spec
smXML_10 = "{http://metadata.dgiwg.org/smXML}"
xsi_10 = '{http://www.w3.org/2001/XMLSchema-instance}'
gml_10 = "{http://www.opengis.net/gml}"
xsi_10 = "{http://www.w3.org/2001/XMLSchema-instance}"



# Caris has a bug where if the namepsaces don't use these namespaces (i.e. if element tree changes them to ns0, ns1 the Caris won't load the data
def register_bag15_namespace():
    et.register_namespace("gmi", "http://www.isotc211.org/2005/gmi")
    et.register_namespace('gmd', "http://www.isotc211.org/2005/gmd")
    et.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")
    et.register_namespace('gml', "http://www.opengis.net/gml/3.2")
    et.register_namespace('gco', "http://www.isotc211.org/2005/gco")
    et.register_namespace('xlink', "http://www.w3.org/1999/xlink")
    et.register_namespace('bag', "http://www.opennavsurf.org/schema/bag")

def register_bag10_namespace():
    # Overwrite current namespaces with old namespaces
    et.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")
    et.register_namespace('xlink', "http://www.w3.org/1999/xlink")
    et.register_namespace('gml', "http://www.opengis.net/gml")
    et.register_namespace('smXML', "http://metadata.dgiwg.org/smXML")

def register_all_namespaces(filename):
    namespaces = dict([node for _, node in et.iterparse(filename, events=['start-ns'])])
    for ns in namespaces:
        et.register_namespace(ns, namespaces[ns])

register_bag15_namespace()

class UseBag10Namespaces():
    """ Bags are no longer thread safe.  Caris needs specific namespaces but elementtree does this globally
        So if you open bags in two thread you could accidentally write bags with the wrong namespace if both are 
        writing the xml out at the same time.

    """
    def __enter__(self):
        register_bag10_namespace()
    def __exit__(self, *args):
        register_bag15_namespace()

class BAGError(Exception):
    """ BAG class for exceptions"""

    def __init__(self, message, *args):
        if isinstance(message, Exception):
            msg = message.args[0] if len(message.args) > 0 else ''
        else:
            msg = message

        self.message = msg
        # allow users initialize misc. arguments as any other builtin Error
        Exception.__init__(self, message, *args)


class Refinement(Grid):
    def __init__(self, depth, uncertainty, res_x, res_y, sw_x=0, sw_y=0):
        """ Note that refinements have a geotransform that is based on cell corners while the data is defined to be at the
        cell centers, so use affine_center to get the data positions -- maybe the should be reversed and return cell centers
        and have to do extra math to get cell edges.

        Parameters
        ----------
        depth
        uncertainty
        res_x
        res_y
        sw_x
        sw_y
        """
        super().__init__((sw_x, sw_y), depth.shape, (res_x, res_y), allocate=False)
        self.depth = depth
        if uncertainty is None:
            uncertainty = numpy.zeros(self.depth.shape, dtype=numpy.float32)
        self.uncertainty = uncertainty
    def get_xy_pts_arrays(self):
        r, c = numpy.indices(self.depth.shape)  # make indices into array elements that can be converted to x,y coordinates
        pts = numpy.array([r, c, r, c, self.depth, self.uncertainty]).reshape(6, -1)
        pts = pts[:, pts[4] != VRBag.fill_value]  # remove nodata points

        pts[0], pts[1] = affine_center(pts[0], pts[1], *self.geotransform)
        return pts

    def get_xy_pts_matrix(self):
        r, c = numpy.indices(self.depth.shape)  # make indices into array elements that can be converted to x,y coordinates
        pts = numpy.array([r, c, r, c, self.depth, self.uncertainty])
        pts[0], pts[1] = affine_center(pts[2], pts[3], *self.geotransform)
        return pts

class SRBag(h5py.File):
    fill_value = 1000000.
    DEPTH = 'depth'
    tracking_list_type = [('row', numpy.uint32),
                          ('col', numpy.uint32),
                          (DEPTH, numpy.float32),
                          ('uncertainty', numpy.float32),
                          ('track_code', numpy.uint8),
                          ('list_series', numpy.uint16)]

    @classmethod
    def from_existing_bag(cls, existing_file_full_path, new_file_full_path):
        """Open an existing bag file and use its metadata to create a new bag file.
        Basically a lazy way to create data from an existing metadata (projection info etc.) as a template.
        """
        if os.path.exists(new_file_full_path):
            raise FileExistsError(new_file_full_path, "target bag file already exists")
        if not os.path.exists(existing_file_full_path):
            raise FileNotFoundError(existing_file_full_path, "was not found")
        f = h5py.File(existing_file_full_path)
        existing_xml_metadata = f['/BAG_root/metadata']
        bag = cls.new_bag(new_file_full_path, xml_metadata=existing_xml_metadata)
        return bag

    @staticmethod
    def make_xml(hcrs, llx, lly, urx, ury,
                 west_lon, south_lat, east_lon, north_lat,
                 height, width, res_x, res_y,
                 vcrs=None, date=None, res_unit="m",
                 individual="unknown", organization="unknown",
                 position_name="unknown", citation="", abstract="", vert_uncert_code="unknown",
                 step_description=None, desc_datetime=None,
                 restriction="otherRestrictions", constraints=None, classification="unclassified", user_note="none"):
        template_xml_path = HSTB.resources.path_to_resource("bag_template.xml")
        template_xml = open(template_xml_path).read()
        if isinstance(hcrs, str):
            template_xml = template_xml.replace("${HORIZ_WKT}", hcrs)
        else:
            template_xml = template_xml.replace("${HORIZ_WKT}", hcrs.ExportToWkt())

        if vcrs is None:
            template_xml = template_xml.replace('${VERT_WKT:VERT_CS["unknown", VERT_DATUM["unknown", 2000]]}',
                                                'VERT_CS["unknown", VERT_DATUM["unknown", 2000]]')
        elif isinstance(vcrs, str):
            template_xml = template_xml.replace('${VERT_WKT:VERT_CS["unknown", VERT_DATUM["unknown", 2000]]}', vcrs)
        else:
            template_xml = template_xml.replace('${VERT_WKT:VERT_CS["unknown", VERT_DATUM["unknown", 2000]]}', vcrs.ExportToWkt())

        template_xml = template_xml.replace("${WEST_LONGITUDE}", str(west_lon))
        template_xml = template_xml.replace("${EAST_LONGITUDE}", str(east_lon))
        template_xml = template_xml.replace("${SOUTH_LATITUDE}", str(south_lat))
        template_xml = template_xml.replace("${NORTH_LATITUDE}", str(north_lat))

        template_xml = template_xml.replace("${INDIVIDUAL_NAME:unknown}", str(individual))
        template_xml = template_xml.replace("${ORGANISATION_NAME:unknown}", str(organization))
        template_xml = template_xml.replace("${POSITION_NAME:unknown}", str(position_name))
        if date is None:
            date = datetime.datetime.now()
        if isinstance(date, datetime.datetime):  # convert to just date
            date = date.date()
        if isinstance(date, datetime.date):  # convert to iso string
            date = date.isoformat()
        template_xml = template_xml.replace("${DATE}", date)

        template_xml = template_xml.replace("${CONTACT_ROLE:author}", "author")
        template_xml = template_xml.replace("${METADATA_STANDARD_NAME:ISO 19139}", "ISO 19139")
        template_xml = template_xml.replace("${METADATA_STANDARD_VERSION:1.1.0}", "1.1.0")
        template_xml = template_xml.replace("${RES_UNIT}", str(res_unit))  # assuming meters!
        template_xml = template_xml.replace("${RESX}", str(res_x))
        template_xml = template_xml.replace("${RESY}", str(res_y))
        template_xml = template_xml.replace("${HEIGHT}", str(height))
        template_xml = template_xml.replace("${WIDTH}", str(width))
        template_xml = template_xml.replace("${CORNER_POINTS}", "{},{} {},{}".format(llx, lly, urx, ury))
        template_xml = template_xml.replace("${XML_IDENTIFICATION_CITATION:}", str(citation))
        template_xml = template_xml.replace("${ABSTRACT:}", str(abstract))
        template_xml = template_xml.replace("${VERTICAL_UNCERT_CODE:unknown}", str(vert_uncert_code))
        template_xml = template_xml.replace("${PROCESS_STEP_DESCRIPTION}", str(step_description))
        if desc_datetime is None:
            desc_datetime = datetime.datetime.now()
        if isinstance(desc_datetime, datetime.datetime):
            desc_datetime = desc_datetime.isoformat()
        template_xml = template_xml.replace("${DATETIME}", str(desc_datetime))
        template_xml = template_xml.replace("${RESTRICTION_CODE:otherRestrictions}", str(restriction))
        template_xml = template_xml.replace("${RESTRICTION_OTHER_CONSTRAINTS:unknown}", str(constraints))
        template_xml = template_xml.replace("${CLASSIFICATION:unclassified}", str(classification))
        template_xml = template_xml.replace("${SECURITY_USER_NOTE:none}", str(user_note))
        return template_xml

    @classmethod
    def new_bag(cls, input_file_full_path, xml_metadata="", **kywrds):
        """ Create a new bag given the metadata which contains the coordinate system corner positions

        Parameters
        ----------
        input_file_full_path
            filename to be created or revised
        xml_metadata
            xml as a string or h5py dataset
        kywrds
            named arguments for the h5py file opening (like 'mode')

        Returns
        -------
        VRBag instance which is stored at the path given

        """
        kywrds = kywrds.copy()  # don't change the callers data in case they are using a dict object
        kywrds['mode'] = "w"  # make sure the file is set for write access

        f = h5py.File(input_file_full_path, **kywrds)
        root = f.require_group('/BAG_root')
        # root.attrs["Bag Version"] = numpy.string_("1.6.2")
        tid = h5py.h5t.C_S1.copy()
        tid.set_size(32)
        H5T_C_S1_64 = h5py.Datatype(tid)
        root.attrs.create('Bag Version', data="1.6.2", dtype=H5T_C_S1_64)

        if not xml_metadata:
            srs = osr.SpatialReference()  # supply WGS84 as a default -- user needs to override this
            srs.ImportFromEPSG(4326)
            xml_metadata = cls.make_xml(srs, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        if isinstance(xml_metadata, str):
            metadata = numpy.array(list(xml_metadata), dtype="S1")
        else:
            metadata = xml_metadata
        root.create_dataset("metadata", maxshape=(None,), data=metadata, compression='gzip', compression_opts=9)

        tracking_rec_array = numpy.array([], dtype=cls.tracking_list_type)
        fill = numpy.array([(0, 0, 0., 0., 0, 0)], dtype=cls.tracking_list_type)
        root.create_dataset("tracking_list", maxshape=(None,), data=tracking_rec_array, fillvalue=fill, compression='gzip', compression_opts=9)
        root["tracking_list"].attrs.create("Tracking List Length", 0, dtype=numpy.uint32)

        root.create_dataset("elevation", data=numpy.array([[], []], dtype=numpy.float32), maxshape=(None, None), fillvalue=cls.fill_value,
                            compression='gzip', compression_opts=9)
        root.create_dataset("uncertainty", data=numpy.array([[], []], dtype=numpy.float32), maxshape=(None, None), fillvalue=cls.fill_value,
                            compression='gzip', compression_opts=9)
        f.close()
        # remove any mode and open the file for edit access
        kywrds['mode'] = "r+"
        bag = SRBag(input_file_full_path, **kywrds)
        return bag

    def __init__(self, input_file_full_path, *args, min_version=(1,5,0), **kywrds):
        """ Loads bag dataset from an hdf5 file.

        The min_version keyword is used to prevent older bags (ver < 1.5) from being loaded unless the caller knows the driver has necessary
        backward compatibility.  At time of writing, only the read/set_temporal_extents was made backward compatible.
        A ValueError will be raised if the version requirement is not met.

        Parameters
        ----------
        input_file_full_path
            full path to the file to be read
        args
            positional arguments passed along to h5py.File
        min_version
            minimum version of the bag spec to allow, default to 1.5.0
        kywrds
            keywords passed along to h5py.File, like mode (which defaults to rw but should be changed to r)
        """
        # @todo Add backward compatibility for the primary xml attributes that are used like geographic extent
        # @todo -- switch default from read/write to read
        if len(args) == 0 and "mode" not in kywrds:  # make sure the file is set for read access if not otherwise specified
            kywrds = kywrds.copy()
            kywrds['mode'] = 'r'  # "r+"
        super().__init__(input_file_full_path, *args, **kywrds)
        self.bag_root = self['/BAG_root']
        # self.elevation = self.bag_root["elevation"]
        # self.uncertainty = self.bag_root["uncertainty"]

        # metadata = ''.join(map(bytes.decode, self.bag_root['metadata']))
        metadata = self.bag_root['metadata'][:].tobytes().decode().replace("\x00", "")
        self.xml_root = et.fromstring(metadata)
        if min_version:  # passing None allows everything
            major, minor, release = self.metadata_version()
            if not (major >= min_version[0] and minor >= min_version[1] and release >= min_version[2]):
                raise ValueError(f"Bag metadata did not meet minimum version requirement, file {self.metadata_version()} vs {min_version}"  )
    def metadata_version(self):
        """Returns (major, minor, rev) or None.  Current options are (1,0,0) or (1,5,0)"""
        if smXML_10 in self.xml_root.tag:
            return (1,0,0)
        elif gmi in self.xml_root.tag:
            return (1,5,0)  # version 1.5.0+
        else:
            return (0, 0, 0)

    @property
    def elevation(self):
        return self.bag_root["elevation"]

    @property
    def uncertainty(self):
        return self.bag_root["uncertainty"]

    def set_res(self, super_grid_res):
        self.cell_size_x, self.cell_size_y = super_grid_res

    def set_origin(self, origin):
        self.minx, self.miny = origin

    def set_elevation(self, elev):
        self.bag_root["elevation"][:] = elev
        self.recompute_mins_and_maxs()

    def set_uncertainty(self, uncrt):
        self.bag_root["uncertainty"][:] = uncrt
        self.recompute_mins_and_maxs()

    def recompute_mins_and_maxs(self):
        # min max in overviews - base elevation layer
        valid_elev = self.elevation[numpy.array(self.elevation) != self.fill_value]
        try:
            elev_max = valid_elev.max()
            elev_min = valid_elev.min()
        except ValueError:  # if no valid depths are found then it'll raise a ValueError
            elev_max = 0.0
            elev_min = 0.0
        self.elevation.attrs["Maximum Elevation Value"] = elev_max
        self.elevation.attrs["Minimum Elevation Value"] = elev_min
        del valid_elev

        valid_uncertainty = self.uncertainty[numpy.array(self.uncertainty) != self.fill_value]
        try:
            uncertainty_max = valid_uncertainty.max()
            uncertainty_min = valid_uncertainty.min()
        except ValueError:  # if no valid uncertainties are found then it'll raise a ValueError
            uncertainty_max = 0.0
            uncertainty_min = 0.0
        self.uncertainty.attrs["Maximum Uncertainty Value"] = uncertainty_max
        self.uncertainty.attrs["Minimum Uncertainty Value"] = uncertainty_min

        del valid_uncertainty

    @property
    def cell_size_x(self):
        return self.col_info[1]

    @property
    def cell_size_y(self):
        return self.row_info[1]

    @cell_size_x.setter
    def cell_size_x(self, val):
        self._rc_resolution_element(self._columns_element).text = str(val)
        self._set_geo_strings()

    @cell_size_y.setter
    def cell_size_y(self, val):
        self._rc_resolution_element(self._rows_element).text = str(val)
        self._set_geo_strings()

    @property
    def numx(self):
        return self.col_info[0]

    @property
    def numy(self):
        return self.row_info[0]

    @numx.setter
    def numx(self, val):
        if self.elevation.shape[1] != val:
            self._resize_grid((self.numy, val))
            self._rc_dimension_element(self._columns_element).text = str(val)
            self._set_geo_strings()

    @numy.setter
    def numy(self, val):
        if self.elevation.shape[0] != val:
            self._resize_grid((val, self.numx))
            self._rc_dimension_element(self._rows_element).text = str(val)
            self._set_geo_strings()

    @property
    def uom_x(self):
        return self.col_info[2]

    @property
    def uom_y(self):
        return self.row_info[2]

    @property
    def _dimensions_elements(self):
        elements = {}
        md_dimension = self.xml_root.findall(
            gmd + 'spatialRepresentationInfo/' + gmd + 'MD_Georectified/' + gmd + 'axisDimensionProperties/' + gmd + 'MD_Dimension')
        for elem in md_dimension:
            for sub_elem in elem:
                for sub_sub_elem in sub_elem:
                    if sub_sub_elem.text in ('column', "row"):
                        elements[sub_sub_elem.text] = elem
        return elements

    @property
    def _columns_element(self):
        return self._dimensions_elements['column']

    @property
    def _rows_element(self):
        return self._dimensions_elements['row']

    @staticmethod
    def _rc_dimension_element(element):
        for ss_elem in element:
            if ss_elem.tag == gmd + 'dimensionSize':
                for sss_elem in ss_elem:
                    return sss_elem

    def _resize_grid(self, shape):
        if None not in shape:  # in an uninitialized file the sizes may be strings or empty which comes out as None
            self.elevation.resize(shape)
            self.uncertainty.resize(shape)

    @staticmethod
    def _rc_resolution_element(element):
        for ss_elem in element:
            if ss_elem.tag == gmd + 'resolution':
                for sss_elem in ss_elem:
                    return sss_elem

    @staticmethod
    def _rc_info(element):
        try:
            cnt = int(VRBag._rc_dimension_element(element).text)
        except ValueError:
            cnt = 0
        try:
            res = float(VRBag._rc_resolution_element(element).text)
        except ValueError:
            res = 0.0
        uom = VRBag._rc_resolution_element(element).get('uom')
        # for ss_elem in element:
        #     if ss_elem.tag == gmd + 'dimensionSize':
        #         for sss_elem in ss_elem:
        #             cnt = int(sss_elem.text)
        #     if ss_elem.tag == gmd + 'resolution':
        #         for sss_elem in ss_elem:
        #             res = float(sss_elem.text)
        #             uom = sss_elem.get('uom')
        return cnt, res, uom

    @property
    def col_info(self):
        return self._rc_info(self._columns_element)

    @property
    def row_info(self):
        return self._rc_info(self._rows_element)

    def read_meta_row_col(self):
        """
        Read meta_cols, meta_dx, meta_dx_uom info

        """
        meta_cols_arr = {}
        md_dimension = self.xml_root.findall(
            gmd + 'spatialRepresentationInfo/' + gmd + 'MD_Georectified/' + gmd + 'axisDimensionProperties/' + gmd + 'MD_Dimension')
        for elem in md_dimension:
            for sub_elem in elem:
                for sub_sub_elem in sub_elem:
                    # print (sub_sub_elem.tag, sub_sub_elem.text, sub_sub_elem.attrib)
                    if sub_sub_elem.text in ('column', "row"):
                        if sub_sub_elem.text == 'column':
                            meta_rc = 'meta_cols'
                            meta_dxy = 'meta_dx'
                            meta_uom = 'meta_dx_uom'
                        else:
                            meta_rc = 'meta_rows'
                            meta_dxy = 'meta_dy'
                            meta_uom = 'meta_dy_uom'

                        for ss_elem in elem:
                            if ss_elem.tag == gmd + 'dimensionSize':
                                for sss_elem in ss_elem:
                                    meta_cols = sss_elem.text
                                    meta_cols_arr[meta_rc] = meta_cols
                            if ss_elem.tag == gmd + 'resolution':
                                for sss_elem in ss_elem:
                                    meta_dx = sss_elem.text
                                    meta_cols_arr[meta_dxy] = meta_dx
                                    meta_dx_uom = sss_elem.get('uom')
                                    # print ('meta_dx_uom: ' + meta_dx_uom)
                                    meta_cols_arr[meta_uom] = meta_dx_uom
        return meta_cols_arr

    @property
    def bounding_box_element(self):
        box_elem = self.xml_root.findall(gmd + 'identificationInfo/' + bagschema + 'BAG_DataIdentification/' +
                                         gmd + 'extent/' + gmd + 'EX_Extent/' + gmd + 'geographicElement/' + gmd + 'EX_GeographicBoundingBox')
        for elem in box_elem:
            return elem

    def _get_bounds_decimal_elem(self, tag):
        for elem in self.bounding_box_element:
            if elem.tag == gmd + tag:
                for decimal_elem in elem:
                    return decimal_elem

    @property
    def bounding_box_north_element(self):
        return self._get_bounds_decimal_elem("northBoundLatitude")

    @property
    def bounding_box_south_element(self):
        return self._get_bounds_decimal_elem("southBoundLatitude")

    @property
    def bounding_box_east_element(self):
        return self._get_bounds_decimal_elem("eastBoundLongitude")

    @property
    def bounding_box_west_element(self):
        return self._get_bounds_decimal_elem("westBoundLongitude")

    @property
    def minx(self):
        corner_pt = self.corner_points_string.split()
        try:
            meta_sw_pt = corner_pt[0].split(',')
            x = float(meta_sw_pt[0])
        except ValueError:
            x = 1e20
        return x
    @property
    def maxx(self):
        x = self.minx + self.cell_size_x * (self.numx - 1)
        return x

    @minx.setter
    def minx(self, val):
        llx = float(val)
        self._set_geo_strings(llx=llx)

    @property
    def corner_points_element(self):
        corner_points = self.xml_root.findall(gmd + 'spatialRepresentationInfo/' + gmd + 'MD_Georectified/' + gmd + 'cornerPoints')
        for elem in corner_points:
            for sub_elem in elem:
                for sub_sub_elem in sub_elem:
                    return sub_sub_elem

    @property
    def corner_points_string(self):
        # print (sub_sub_elem.tag, sub_sub_elem.text, sub_sub_elem.attrib)
        return str(self.corner_points_element.text)

    @property
    def miny(self):
        corner_pt = self.corner_points_string.split()
        meta_sw_pt = corner_pt[0].split(',')
        try:
            y = float(meta_sw_pt[1])
        except IndexError:
            y = 1e20
        return y
    @property
    def maxy(self):
        y = self.miny + self.cell_size_y * (self.numy - 1)
        return y

    @miny.setter
    def miny(self, val):
        lly = float(val)
        self._set_geo_strings(lly=lly)
    def read_temporal_extents(self):
        bag_format = self.metadata_version()
        if bag_format[0] == 1 and bag_format[1] == 0:
            temporal_hierarchy = ['identificationInfo', smXML_10 + 'BAG_DataIdentification', 'extent', smXML_10 + 'EX_Extent',
                                  'temporalElement', smXML_10 + 'EX_TemporalExtent', 'extent', 'TimePeriod']
            use_gml = ""
        else:
            temporal_hierarchy = [gmd + 'identificationInfo', bagschema + 'BAG_DataIdentification', gmd + 'extent', gmd + 'EX_Extent',
                                  gmd + 'temporalElement', gmd + 'EX_TemporalExtent', gmd + 'extent', gml + 'TimePeriod']
            use_gml = gml
        temporal_root = "/".join(temporal_hierarchy)
        begin_elem = self.xml_root.findall(temporal_root + "/" + use_gml + 'beginPosition')
        end_elem = self.xml_root.findall(temporal_root + "/" + use_gml + 'endPosition')
        if begin_elem:
            begin_val = begin_elem[0].text
        else:
            begin_val = ""
        if end_elem:
            end_val = end_elem[0].text
        else:
            end_val = ""
        return begin_val, end_val
    def set_temporal_extents(self, begin, end):
        """
          <gmd:temporalElement>
            <gmd:EX_TemporalExtent>
              <gmd:extent>
                <gml:TimePeriod gml:id="temporal-extent-1" xsi:type="gml:TimePeriodType">
                  <gml:beginPosition>2018-06-29T07:20:48</gml:beginPosition>
                  <gml:endPosition>2018-07-06T21:54:43</gml:endPosition>
                </gml:TimePeriod>
              </gmd:extent>
            </gmd:EX_TemporalExtent>
          </gmd:temporalElement>
        """
        # convert datetimes to isoformat strings.  Dates does not convert with time, so the timetuples could make both work if needed.
        # begin = datetime.datetime(*begin.timetuple()[:6]).isoformat()
        if isinstance(begin, (datetime.date, datetime.datetime)):
            begin = begin.isoformat()
        if isinstance(end, (datetime.date, datetime.datetime)):
            end = end.isoformat()
        bag_format = self.metadata_version()
        if bag_format[0] == 1 and bag_format[1] == 0:
            temporal_hierarchy = ['identificationInfo', smXML_10 + 'BAG_DataIdentification', 'extent', smXML_10 + 'EX_Extent',
                                  'temporalElement', smXML_10 + 'EX_TemporalExtent', 'extent', 'TimePeriod']
            use_gml = ""
        else:
            temporal_hierarchy = [gmd + 'identificationInfo', bagschema + 'BAG_DataIdentification', gmd + 'extent', gmd + 'EX_Extent',
                                  gmd + 'temporalElement', gmd + 'EX_TemporalExtent', gmd + 'extent', gml + 'TimePeriod']
            use_gml = gml
        temporal_root = "/".join(temporal_hierarchy)
        begin_elem = self.xml_root.findall(temporal_root + "/" + use_gml + 'beginPosition')
        end_elem = self.xml_root.findall(temporal_root + "/" + use_gml + 'endPosition')
        if not begin_elem or not end_elem:
            parent = self.xml_root
            for elem in temporal_hierarchy:
                found = parent.findall(elem)
                if not found:
                    new_elem = et.SubElement(parent, elem)
                    if "TimePeriod" in elem:
                        new_elem.set(use_gml + 'id', "temporal-extent-1")
                        new_elem.set(xsi + 'type', "gml:TimePeriodType")
                    found = [new_elem]
                parent = found[0]
            if not begin_elem:
                begin_elem = [et.SubElement(parent, use_gml+"beginPosition")]
            if not end_elem:
                end_elem = [et.SubElement(parent, use_gml+"endPosition")]

        begin_elem[0].text = begin
        end_elem[0].text = end

    def _set_geo_strings(self, llx=None, lly=None):
        if llx is None:
            llx = self.minx
        if lly is None:
            lly = self.miny

        urx = llx + self.cell_size_x * (self.numx - 1)  # for bag metadata adjust the corner to center of cell
        ury = lly + self.cell_size_y * (self.numy - 1)
        corner_string = "{},{} {},{}".format(llx, lly, urx, ury)
        self.corner_points_element.text = corner_string
        # set the bounding box in lat/lon
        wgs = osr.SpatialReference()
        wgs.ImportFromEPSG(4326)
        transform = osr.CoordinateTransformation(self.srs, wgs)

        south_lat, west_lon = transform.TransformPoint(llx, lly)[:2]
        north_lat, east_lon = transform.TransformPoint(urx, ury)[:2]

        self.bounding_box_north_element.text = str(north_lat)
        self.bounding_box_east_element.text = str(east_lon)
        self.bounding_box_south_element.text = str(south_lat)
        self.bounding_box_west_element.text = str(west_lon)

        elem = self.xml_root.findall(gmd + 'identificationInfo/' + bagschema + 'BAG_DataIdentification/' +
                                     gmd + 'spatialResolution/' + gmd + 'MD_Resolution/' +
                                     gmd + 'distance/' + gco + 'Distance')
        elem[0].text = str(self.cell_size_y)

    def read_meta_llx_lly(self):
        """
        Read meta_llx, meta_lly info

        """
        return {'meta_llx': self.minx, 'meta_lly': self.miny}

    @property
    def _horizontal_crs_element(self):
        md_reference_system = self.xml_root.findall(
            gmd + 'referenceSystemInfo/' + gmd + 'MD_ReferenceSystem/' + gmd + 'referenceSystemIdentifier/' + gmd + 'RS_Identifier')
        for elem in md_reference_system:
            for sub_elem in elem:
                if sub_elem.tag == gmd + 'code':
                    for sub_sub_elem in sub_elem:
                        return sub_sub_elem

    @property
    def horizontal_crs_wkt(self):
        """
        Read meta_horizontal_proj info

        """
        meta_horizontal_proj = self._horizontal_crs_element.text.replace('\n', '')
        return meta_horizontal_proj

    @horizontal_crs_wkt.setter
    def horizontal_crs_wkt(self, val):
        self._horizontal_crs_element.text = val

    @property
    def _vertical_crs_element(self):
        md_reference_system = self.xml_root.findall(
            gmd + 'referenceSystemInfo/' + gmd + 'MD_ReferenceSystem/' + gmd + 'referenceSystemIdentifier/' + gmd + 'RS_Identifier')
        search_terms = ['VERT_CS', 'VERTCRS']
        for term in search_terms:
            for elem in md_reference_system:
                for sub_elem in elem:
                    if sub_elem.tag == gmd + 'code':
                        for sub_sub_elem in sub_elem:
                            if term in sub_sub_elem.text.upper():
                                return sub_sub_elem

    @property
    def vertical_crs_wkt(self):
        """
        Read meta_horizontal_proj info

        """
        meta_vertical_proj = self._vertical_crs_element.text.replace('\n', '')
        return meta_vertical_proj

    @vertical_crs_wkt.setter
    def vertical_crs_wkt(self, val):
        self._vertical_crs_element.text = val

    @property
    def srs(self):
        srs = osr.SpatialReference()
        srs.ImportFromWkt(self.horizontal_crs_wkt)
        return srs

    def read_meta_horizontal_proj(self):
        return self.horizontal_crs_wkt

    def commit_xml(self):
        """Write the xml element into the bag, it is held in memory until this is called"""
        bag_format = self.metadata_version()
        if bag_format[0] == 1 and bag_format[1] == 0:
            with UseBag10Namespaces() as nm:
                metadata = et.tostring(self.xml_root).decode()
        else:
            metadata = et.tostring(self.xml_root).decode()
        try:
            del self.bag_root["metadata"]
        except:
            pass
        self.bag_root.create_dataset("metadata", maxshape=(None,), data=numpy.array(list(metadata), dtype="S1"))

    def flush(self):
        if self.mode != 'r':
            self.commit_xml()
        super().flush()

    def close(self):
        if self.mode != 'r':
            self.commit_xml()
        super().close()

    @property
    def xml_string(self):
        metadata = et.tostring(self.xml_root).decode()
        return metadata

    @property
    def pretty_xml_string(self):
        try:
            from bs4 import BeautifulSoup
            metadata = BeautifulSoup(self.xml_string, "xml").prettify()
            return metadata
        except ModuleNotFoundError:
            return self.xml_string

    @xml_string.setter
    def xml_string(self, metadata):
        self.xml_root = et.fromstring(metadata)


class VRBag(SRBag):
    INDEX = "index"
    DIMX = 'dimensions_x'
    DIMY = 'dimensions_y'
    RESX = 'resolution_x'
    RESY = 'resolution_y'
    SW_X = 'sw_corner_x'
    SW_Y = 'sw_corner_y'
    DEPTH = SRBag.DEPTH
    DEPTH_UNCRT = 'depth_uncrt'
    varres_metadata_type = [(INDEX, numpy.uint32),
                            (DIMX, numpy.uint32),
                            (DIMY, numpy.uint32),
                            (RESX, numpy.float32),
                            (RESY, numpy.float32),
                            (SW_X, numpy.float32),
                            (SW_Y, numpy.float32)]
    varres_refinements_type = [(DEPTH, numpy.float32),
                               (DEPTH_UNCRT, numpy.float32)]

    varres_tracking_list_type = [('row', numpy.uint32),
                                 ('col', numpy.uint32),
                                 ('sub_row', numpy.uint32),
                                 ('sub_col', numpy.uint32),
                                 (DEPTH, numpy.float32),
                                 ('uncertainty', numpy.float32),
                                 ('track_code', numpy.uint8),
                                 ('list_series', numpy.uint16)]

    @classmethod
    def new_bag(cls, input_file_full_path, xml_metadata="", **kywrds):
        """ Create a new bag given the metadata which contains the coordinate system corner positions

        Parameters
        ----------
        input_file_full_path
            filename to be created or revised
        xml_metadata
            xml as a string or h5py dataset
        kywrds
            named arguments for the h5py file opening (like 'mode')

        Returns
        -------
        VRBag instance which is stored at the path given

        """
        # create the SR grid first then add the VR data
        sr = super().new_bag(input_file_full_path, xml_metadata, **kywrds)
        sr.close()
        del sr

        kywrds = kywrds.copy()  # don't change the callers data in case they are using a dict object
        kywrds['mode'] = "r+"  # we made a bag above, so now open as VR for read/write
        f = h5py.File(input_file_full_path, **kywrds)
        root = f['/BAG_root']

        # make sure to pass in a list of tuples.  list of lists yields the wrong data shape (not sure why)
        rec_array = numpy.array([[], []], dtype=VRBag.varres_metadata_type)
        fill = numpy.array([(4294967295, 0, 0, -1., -1., -1., -1.)], dtype=VRBag.varres_metadata_type)
        root.create_dataset("varres_metadata", maxshape=(None, None), data=rec_array, fillvalue=fill, compression='gzip', compression_opts=9)

        refinements_rec_array = numpy.array([[]], dtype=VRBag.varres_refinements_type)
        fill = numpy.array([(VRBag.fill_value, VRBag.fill_value)], dtype=VRBag.varres_refinements_type)
        root.create_dataset("varres_refinements", maxshape=(1, None), data=refinements_rec_array, fillvalue=fill, compression='gzip',
                            compression_opts=9)

        var_tracking_rec_array = numpy.array([], dtype=VRBag.varres_tracking_list_type)
        fill = numpy.array([(0, 0, 0, 0, 0., 0., 0, 0)], dtype=VRBag.varres_tracking_list_type)
        root.create_dataset("varres_tracking_list", maxshape=(None,), data=var_tracking_rec_array, fillvalue=fill, compression='gzip',
                            compression_opts=9)
        root["varres_tracking_list"].attrs.create("VR Tracking List Length", 0, dtype=numpy.uint32)

        f.close()
        # remove any mode and open the file for edit access
        if 'mode' in kywrds:
            kywrds.pop('mode')
        vr = VRBag(input_file_full_path, "r+", **kywrds)
        return vr

    def __init__(self, input_file_full_path, *args, **kywrds):
        super().__init__(input_file_full_path, *args, **kywrds)

        try:
            self.varres_metadata = self.bag_root['varres_metadata']
            self.varres_refinements = self.bag_root['varres_refinements']
            # self.fill_value = self.varres_refinements.fillvalue[0]  # the depth fill value, not the stddev fill
        except KeyError:
            raise BAGError("Could not find VR metadata, probably an SR BAG")

    @property
    def vr_depth(self):
        return self.varres_refinements[self.varres_refinements.dtype.names[0]][0]

    @property
    def vr_uncrt(self):
        return self.varres_refinements[self.varres_refinements.dtype.names[1]][0]

    def set_refinements(self, data: list, elev_func=None, uncert_func=None, local_offset=False):
        """ Set ALL the varres_refinements using a list of lists of numpy arrays.
        elevation and uncertainty overview layers will be computed as well as many attributes

        Parameters
        ----------
        data
            list of lists of :class:Refinements
        elev_func
            callback to compute representative value, numpy.mean is used if set to None
        uncert_func
            callback to compute representative value, numpy.mean is used if set to None
        local_offset
            bool which defines if the offset is local to the refinement or includes the bag global positioning
            both should have the half cell offset to center the data plus any additional offset.
            Example: A bag in UTM with 3x3 supercells of 64m sizes, minx = 32 (meaning the first cell goes from 0 - 64)
            If setting a 12m resolution cell offset by 2m from the refinement edge in the 2nd row and 1st column use:
            ref = Refinement(depths, uncrt, 12, 12, 2, 2)  # 2 for the shift from the edge
            set_refinement(2,1, ref, local_offset=True)
            or
            ref = Refinement(depths, uncrt, 12, 12, 64 + 2, 64*2 2)  # 64 per row or column, rows are Y coordinate
            set_refinement(2,1,ref, local_offset=False)
            or
            ref = Refinement(depths, uncrt, 12, 12, vr.minx-vr.cell_size_x/2 + cols*cell_size_x + 2,
                                                    vr.miny-vr.cell_size_y/2 + rows*cell_size_y + 2)  # 64 per row or column
            set_refinement(2,1, ref, local_offset=False)

        Returns
        -------

        """
        self.numy = 0  # essentially clears all existing data in the i,j grids (varres_metadata, elevation, uncertainty)
        self.numy = len(data)
        self.numx = len(data[0])

        if 0:
            for i, row_list in enumerate(data):
                for j, refinement in enumerate(row_list):
                    self.set_refinement(i, j, refinement, update_attr=False, elev_func=elev_func, uncert_func=uncert_func)
        if 1:
            if elev_func is None:
                elev_func = numpy.mean
            if uncert_func is None:
                uncert_func = numpy.mean

            varres_fill = self.varres_metadata.fillvalue
            elev_fill = self.elevation.fillvalue
            uncert_fill = self.uncertainty.fillvalue
            # @todo May speed things up to build the elevation and uncertainty array as numpy objects and then set the h5py
            # since it seems that setting h5py data individually by index is slower than I'd expect
            total_refinement_size = 0
            for i, row_list in enumerate(data):
                for j, refinement in enumerate(row_list):
                    if refinement is not None:
                        total_refinement_size += refinement.depth.size
            self.varres_refinements.resize((1, total_refinement_size))
            refinement_idx = 0
            print("Storing VR Tiles")
            for i, row_list in enumerate(tqdm(data, mininterval=.7)):
                for j, refinement in enumerate(row_list):
                    if refinement is not None:
                        # update the elevation and uncertainty overviews
                        self.elevation[i, j] = elev_func(refinement.depth[refinement.depth != self.fill_value])
                        valid_uncertainty = refinement.uncertainty[refinement.uncertainty != self.fill_value]
                        if len(valid_uncertainty) > 0:
                            self.uncertainty[i, j] = uncert_func(valid_uncertainty)
                        else:
                            self.uncertainty[i, j] = self.fill_value
                        self._write_refinement_at_index(refinement, refinement_idx)
                        if local_offset:
                            mx = refinement.minx + refinement.cell_size_x / 2.0
                            my = refinement.miny + refinement.cell_size_y / 2.0
                        else:
                            bag_llx = self.minx - self.cell_size_x / 2.0
                            bag_lly = self.miny - self.cell_size_y / 2.0
                            supergrid_x = j * self.cell_size_x
                            supergrid_y = i * self.cell_size_y
                            refinement_llx = bag_llx + supergrid_x
                            refinement_lly = bag_lly + supergrid_y
                            mx = refinement.minx - refinement_llx + refinement.cell_size_x / 2.0
                            my = refinement.miny - refinement_lly + refinement.cell_size_y / 2.0
                        self.varres_metadata[i, j] = (refinement_idx, refinement.depth.shape[0], refinement.depth.shape[1],
                                                      refinement.cell_size_x, refinement.cell_size_y, mx, my)
                        refinement_idx += refinement.depth.size
                    else:
                        # turns out setting these with fill values can take an exceedingly long time --
                        # so at the top of the function we wipe out existing data instead and let h5py fill them all
                        pass
                        # self.varres_metadata[i, j] = varres_fill
                        # self.elevation[i, j] = elev_fill
                        # self.uncertainty[i, j] = uncert_fill

        self.recompute_mins_and_maxs()

    def append_refinement(self, refinement):
        current_size = self.varres_refinements.size
        array = refinement.depth
        new_size = (1, current_size + array.size)
        self.varres_refinements.resize(new_size)
        self._write_refinement_at_index(refinement, current_size)
        return current_size

    def remove_refinement(self, i, j):
        supergrid_meta = self.bag_root['varres_metadata'][i][j]
        idx, dimx, dimy = supergrid_meta[self.INDEX], supergrid_meta[self.DIMX], supergrid_meta[self.DIMY]
        supergrid_size = dimx * dimy
        if supergrid_size > 0:
            total_size = self.varres_refinements.size
            # compress the refinements array
            remaining_datasizse = total_size - idx - supergrid_size
            self.varres_refinements[:, idx: remaining_datasizse - supergrid_size] = self.varres_refinements[:,
                                                                                                 idx + supergrid_size:remaining_datasizse]
            # fix all the other refinements to point to the new index locations
            # find indices that are real values, 0xffffffff is used for empty grids
            not_max_int = self.varres_metadata[:, :, self.INDEX] != 0xffffffff
            # find indices past what was deleted
            idx_was_moved = self.varres_metadata[:, :, self.INDEX] > idx
            self.varres_metadata[numpy.logical_and(not_max_int, idx_was_moved), self.INDEX] -= supergrid_size
        self.varres_metadata[i, j] = self.varres_metadata.fillvalue
        self.elevation[i, j] = self.elevation.fillvalue
        self.uncertainty[i, j] = self.uncertainty.fillvalue

    def read_refinement_old(self, i, j):
        index_start = self.varres_metadata[i, j, "index"]

        dimensions_x = self.varres_metadata[i, j, "dimensions_x"]
        dimensions_y = self.varres_metadata[i, j, "dimensions_y"]
        resolution_x = self.varres_metadata[i, j, "resolution_x"]
        resolution_y = self.varres_metadata[i, j, "resolution_y"]
        sw_corner_x = self.varres_metadata[i, j, "sw_corner_x"]
        sw_corner_y = self.varres_metadata[i, j, "sw_corner_y"]

        if index_start < 0xffffffff:
            index_end = index_start + int(dimensions_x * dimensions_y)
            # Using vr_depth or vr_uncrt reads the entire array, so we need to read the index range first then grab the depth
            #   -- much much faster for a large dataset
            # tile = self.vr_depth[index_start:index_end].reshape(dimensions_y, dimensions_x)
            tile = self.varres_refinements[:, index_start:index_end][self.varres_refinements.dtype.names[0]].reshape(dimensions_y, dimensions_x)
            # uncrt = self.vr_uncrt[index_start:index_end].reshape(dimensions_y, dimensions_x)
            uncrt = self.varres_refinements[:, index_start:index_end][self.varres_refinements.dtype.names[1]].reshape(dimensions_y, dimensions_x)
            ref = Refinement(tile, uncrt, resolution_x, resolution_y, sw_corner_x, sw_corner_y)
        else:
            ref = None
        return ref

    def refinement_extents(self, i, j, mdata=None):
        if mdata is None:
            mdata = self.varres_metadata[i, j]
        index_start = mdata["index"]

        if index_start < 0xffffffff:
            resolution_x = mdata["resolution_x"]
            resolution_y = mdata["resolution_y"]
            sw_corner_x = mdata["sw_corner_x"]
            sw_corner_y = mdata["sw_corner_y"]

            bag_supergrid_dx = self.cell_size_x
            bag_supergrid_dy = self.cell_size_y
            bag_llx = self.minx - bag_supergrid_dx / 2.0  # @todo seems the llx is center of the supergridd cel?????
            bag_lly = self.miny - bag_supergrid_dy / 2.0

            supergrid_x = j * bag_supergrid_dx
            supergrid_y = i * bag_supergrid_dy
            refinement_llx = bag_llx + supergrid_x + sw_corner_x - resolution_x / 2.0  # @TODO implies swcorner is to the center and not the exterior
            refinement_lly = bag_lly + supergrid_y + sw_corner_y - resolution_y / 2.0
            corners = ((refinement_llx, refinement_lly), (refinement_llx + supergrid_x + resolution_x, refinement_lly + supergrid_y + resolution_y))
        else:
            corners = None
        return corners

    def read_refinement(self, i, j):
        mdata = self.varres_metadata[i, j]
        index_start = mdata["index"]

        if index_start < 0xffffffff:
            dimensions_x = mdata["dimensions_x"]
            dimensions_y = mdata["dimensions_y"]
            resolution_x = mdata["resolution_x"]
            resolution_y = mdata["resolution_y"]
            # sw_corner_x = mdata["sw_corner_x"]
            # sw_corner_y = mdata["sw_corner_y"]

            index_end = index_start + int(dimensions_x * dimensions_y)
            # Using vr_depth or vr_uncrt reads the entire array, so we need to read the index range first then grab the depth
            #   -- much much faster for a large dataset
            # tile = self.vr_depth[index_start:index_end].reshape(dimensions_y, dimensions_x)
            data = self.varres_refinements[:, index_start:index_end]
            tile = data[self.varres_refinements.dtype.names[0]].reshape(dimensions_y, dimensions_x)
            # uncrt = self.vr_uncrt[index_start:index_end].reshape(dimensions_y, dimensions_x)
            uncrt = data[self.varres_refinements.dtype.names[1]].reshape(dimensions_y, dimensions_x)

            # bag_supergrid_dx = self.cell_size_x
            # bag_supergrid_dy = self.cell_size_y
            # bag_llx = self.minx - bag_supergrid_dx / 2.0  # @todo seems the llx is center of the supergridd cel?????
            # bag_lly = self.miny - bag_supergrid_dy / 2.0
            #
            # supergrid_x = j * bag_supergrid_dx
            # supergrid_y = i * bag_supergrid_dy
            # refinement_llx = bag_llx + supergrid_x + sw_corner_x - resolution_x / 2.0  # @TODO implies swcorner is to the center and not the exterior
            # refinement_lly = bag_lly + supergrid_y + sw_corner_y - resolution_y / 2.0
            (refinement_llx, refinement_lly), (refinement_urx, refinement_ury) = self.refinement_extents(i, j, mdata)
            ref = Refinement(tile, uncrt, resolution_x, resolution_y, refinement_llx, refinement_lly)
        else:
            ref = None
        return ref

    get_refinement = read_refinement

    def recompute_mins_and_maxs(self):
        super().recompute_mins_and_maxs()
        # min max in varres metadata
        self.varres_metadata.attrs['max_dimensions_y'] = self.varres_metadata[:, :, self.DIMY].max()
        self.varres_metadata.attrs['max_resolution_y'] = self.varres_metadata[:, :, self.RESY].max()
        self.varres_metadata.attrs['max_resolution_x'] = self.varres_metadata[:, :, self.RESX].max()
        self.varres_metadata.attrs['max_dimensions_x'] = self.varres_metadata[:, :, self.DIMX].max()
        if self.varres_metadata.attrs['max_dimensions_x'] > 0:  # zero meand the whole VR is empty
            self.varres_metadata.attrs['min_dimensions_x'] = self.varres_metadata[self.varres_metadata[:, :, self.DIMX] > 0, self.DIMX].min()
            self.varres_metadata.attrs['min_dimensions_y'] = self.varres_metadata[self.varres_metadata[:, :, self.DIMY] > 0, self.DIMY].min()
            self.varres_metadata.attrs['min_resolution_x'] = self.varres_metadata[self.varres_metadata[:, :, self.RESX] > 0, self.RESX].min()
            self.varres_metadata.attrs['min_resolution_y'] = self.varres_metadata[self.varres_metadata[:, :, self.RESY] > 0, self.RESY].min()
        else:
            self.varres_metadata.attrs['min_dimensions_x'] = 0
            self.varres_metadata.attrs['min_dimensions_y'] = 0
            self.varres_metadata.attrs['min_resolution_x'] = -1
            self.varres_metadata.attrs['min_resolution_y'] = -1

        # min max in refinements
        valid_depths = self.vr_depth[numpy.array(self.vr_depth) != self.fill_value]
        try:
            depth_max = valid_depths.max()
            depth_min = valid_depths.min()
        except (ValueError, TypeError):
            depth_max = 0.0
            depth_min = 0.0
        self.varres_refinements.attrs["max_depth"] = depth_max
        self.varres_refinements.attrs["min_depth"] = depth_min
        del valid_depths

        valid_uncrt = self.vr_uncrt[numpy.array(self.vr_uncrt) != self.fill_value]
        try:
            uncrt_max = valid_uncrt.max()
            uncrt_min = valid_uncrt.min()
        except (ValueError, TypeError):
            uncrt_max = 0.0
            uncrt_min = 0.0
        self.varres_refinements.attrs["max_uncrt"] = uncrt_max
        self.varres_refinements.attrs["min_uncrt"] = uncrt_min
        del valid_uncrt

    def _write_refinement_at_index(self, refinement, idx):
        self.varres_refinements[0, idx:idx + refinement.depth.size, self.DEPTH] = refinement.depth.ravel()
        self.varres_refinements[0, idx:idx + refinement.uncertainty.size, self.DEPTH_UNCRT] = refinement.uncertainty.ravel()
        # self.varres_refinements[0, current_size:new_size[1]] = array.ravel()

    def set_refinement(self, i, j, refinement, update_attr=True, elev_func=None, uncert_func=None, local_offset=False):
        # get the index of where to write the data
        if refinement is not None:
            array = refinement.depth
        supergrid_meta = self.bag_root['varres_metadata'][i][j]
        idx, dimx, dimy = supergrid_meta[self.INDEX], supergrid_meta[self.DIMX], supergrid_meta[self.DIMY]
        if elev_func is None:
            elev_func = numpy.mean
        if uncert_func is None:
            uncert_func = numpy.mean

        if refinement is None or array is None or array.size == 0:  # remove the refinement
            self.remove_refinement(i, j)
        else:
            if dimx * dimy == array.size:  # replace the refinement in place
                # insert the array data into the varres_refinements
                self._write_refinement_at_index(refinement, idx)
            # otherwise refinement exists and is a different size or doesn't exist
            elif dimx == 0 and dimy == 0:  # adding a new array - allocate space at the end of the array
                idx = self.append_refinement(refinement)
            elif dimx * dimy != array.shape[0] * array.shape[1]:  # if exists already and is changing shape
                # @TODO check if the old data was setting any of the min/max values so a recompute would be needed
                # currently just always recomputing but could be sped up by only recomputing min/max as needed

                # then remove the existing data
                self.remove_refinement(i, j)
                # allocate space at the end of the array
                idx = self.append_refinement(refinement)
            else:
                raise BAGError("How did we get here")

            # update the varres_metadata to describe the refinement
            # make sure to pass in a list of tuples for metadata.  list of lists yields the wrong data shape (not sure why)
            if local_offset:
                mx = refinement.minx + refinement.cell_size_x / 2.0
                my = refinement.miny + refinement.cell_size_y / 2.0
            else:
                bag_llx = self.minx - self.cell_size_x / 2.0
                bag_lly = self.miny - self.cell_size_y / 2.0
                supergrid_x = j * self.cell_size_x
                supergrid_y = i * self.cell_size_y
                refinement_llx = bag_llx + supergrid_x
                refinement_lly = bag_lly + supergrid_y
                mx = refinement.minx - refinement_llx + refinement.cell_size_x / 2.0
                my = refinement.miny - refinement_lly + refinement.cell_size_y / 2.0

            self.varres_metadata[i, j] = (idx, array.shape[0], array.shape[1],
                                          refinement.cell_size_x, refinement.cell_size_y, mx, my)

            # update the elevation and uncertainty overviews
            self.elevation[i, j] = elev_func(refinement.depth[refinement.depth != self.fill_value])
            self.uncertainty[i, j] = uncert_func(refinement.uncertainty[refinement.uncertainty != self.fill_value])

        # update the other metadata attributes if needed
        if update_attr:
            self.recompute_mins_and_maxs()

    def get_valid_refinements(self):
        return self.varres_metadata[:, :, "dimensions_x"] > 0

    def get_res_x(self):
        return self.varres_metadata[:, :, "resolution_x"]

    def get_res_y(self):
        return self.varres_metadata[:, :, "resolution_y"]

    def get_max_depth(self):
        return self.vr_depth[self.vr_depth < self.fill_value].max()

    def get_min_depth(self):
        return self.vr_depth.min()

    def _resize_grid(self, shape):
        if None not in shape:  # in an uninitialized file the sizes may be strings or empty which comes out as None
            super()._resize_grid(shape)
            self.varres_metadata.resize(shape)


def convert_sr_to_vr_bag(sr_path, vr_path, cells_per_supergrid=16):
    # test_sr_bag = r"K:\Survey_Outline_Examples\debugging\H12917_MB_4m_MLLW_final.csar.bag"
    orig_bag = SRBag(sr_path)
    # new_vr_bag = r"K:\Survey_Outline_Examples\debugging\H12917_4m_vr_conversion.bag"
    try:
        os.remove(vr_path)
    except FileNotFoundError:
        pass
    bag = VRBag.from_existing_bag(r"K:\Survey_Outline_Examples\debugging\H12917_MB_4m_MLLW_final.csar.bag", vr_path)
    # make tiles of 16x16 from the SR bag
    vr_tiles = []
    refinement_cell_cnt = cells_per_supergrid
    supergrid_res_x = orig_bag.cell_size_x * refinement_cell_cnt
    supergrid_res_y = orig_bag.cell_size_y * refinement_cell_cnt
    refinement_resx = orig_bag.cell_size_x
    refinement_resy = orig_bag.cell_size_y

    numy = orig_bag.numy  # these are properties that do lookups into the metadata xml, so cache the values and use that
    numx = orig_bag.numx
    print("converting SR to VR")
    for i in tqdm(range(0, numy, refinement_cell_cnt), mininterval=0.7):
        vr_tiles.append([])
        for j in range(0, numx, refinement_cell_cnt):
            refinement_depth = orig_bag.elevation[i:i + refinement_cell_cnt, j:j + refinement_cell_cnt]
            if (refinement_depth == SRBag.fill_value).all():
                refinement = None
            else:
                refinement_uncert = orig_bag.uncertainty[i:i + refinement_cell_cnt, j:j + refinement_cell_cnt]
                # at the end of the data we need to pad with fill values or the shapes/resolution will be wrong
                if numy - i < refinement_cell_cnt or numx - j < refinement_cell_cnt:
                    pad_i = refinement_cell_cnt - (numy - i)
                    pad_j = refinement_cell_cnt - (numx - j)
                    if pad_i < 0:
                        pad_i = 0
                    if pad_j < 0:
                        pad_j = 0
                    refinement_depth = numpy.pad(refinement_depth, ((0, pad_i), (0, pad_j)), "constant", constant_values=VRBag.fill_value)
                    refinement_uncert = numpy.pad(refinement_uncert, ((0, pad_i), (0, pad_j)), "constant", constant_values=VRBag.fill_value)
                refinement = Refinement(refinement_depth, refinement_uncert,
                                        refinement_resx, refinement_resy,
                                        0, 0)  # SW corner is set in 1/2 of a cell by default
            vr_tiles[-1].append(refinement)
    bag.set_refinements(vr_tiles)
    # change the resolution to the new supergrid size --
    # if this is forgottent then it won't load in caris since GDAL will get angry about the data overrunning the grid sizes
    bag.set_res((refinement_cell_cnt * orig_bag.cell_size_x, refinement_cell_cnt * orig_bag.cell_size_y))
    # move the lower left corner from the center of the first SR cell to the center of the supergrid

    bag.minx = orig_bag.minx + (refinement_cell_cnt - 1) * orig_bag.cell_size_x / 2.0
    bag.miny = orig_bag.miny + (refinement_cell_cnt - 1) * orig_bag.cell_size_y / 2.0
    bag.close()


# treat data as points, get the mask or treat as cell areas (combine with min/max/mean)
POINT, MASK, DATA_LOC_MASK, MIN, MAX, MEAN = range(6)
# when using cell areas determine how to treat the potential gaps from the individual cells to the supergrid boundary,
STRETCH, FILL, NOTHING = range(3)


def VRBag_to_TIF(input_file_full_path, dst_filename, sr_cell_size=None, mode=MIN, edge_option=STRETCH, use_blocks=True, nodata=numpy.nan,
                 count_file_ext=".temp.cnt", snap_to_grid=False):
    """

    Parameters
    ----------
    input_file_full_path : str
        Full path to BAG file
    dst_filename : str
        Full path to output TIFF file
    sr_cell_size : float
        cell size for resulting TIF.
        None will use the highest resolution cell size from the BAG file
    mode : int
        One of the defined modes of operation from the enumeration of POINT, DATA_LOC_MASK, DATA, MIN, MAX, MEAN.
        If mode is MIN, MAX or MEAN the BAG cells are treated as pixels that have area.
        If mode is POINT or MASK then the cells are treated as points that fall at the center of the cell.
        The difference between MASK and DATA_LOC_MASK is that the MASK shows all cells that could have had data
        while DATA_LOC_MASK only returns cells that will would data (Which doesn Glen want?).
    edge_option : int
        Supply a value from the enumeration STRETCH, FILL, NOTHING.
        Used if `mode` is one of the cell areas options, otherwise ignored.
    use_blocks : bool
        Boolean value to determine if the TIFF should use blocks in storage and if the
        program should load everything into memory (faster) or load the data piecewise (more robust)
    nodata : float
        The value to use in the resulting TIFF as no data.

    Returns
    -------

    """

    vr = VRBag(input_file_full_path)

    bag_supergrid_dx = vr.cell_size_x
    bag_supergrid_nx = vr.numx
    bag_supergrid_dy = vr.cell_size_y
    bag_supergrid_ny = vr.numy
    bag_llx = vr.minx - bag_supergrid_dx / 2.0  # @todo seems the llx is center of the supergridd cel?????
    bag_lly = vr.miny - bag_supergrid_dy / 2.0

    good_refinements = vr.get_valid_refinements()  # bool matrix of which refinements have data
    index2d = numpy.argwhere(good_refinements)
    # sort indices based on resolution areas
    res_area = vr.get_res_x()[good_refinements] * vr.get_res_y()[good_refinements]
    index2d = index2d[numpy.argsort(res_area)]

    # Adjust coordinates for the bag being able to extend outside the individual supergrids
    # Really it would be better to find the largest overlap and then fit to that exactly but this works for now.

    # So start from 1/2 supergrid below and run n+1 supergrids which ends up 1/2 above the end of the supergrids
    # sr_grid = Grid([bag_llx - bag_supergrid_dx/2.0, bag_lly - bag_supergrid_dy/2.0], [(bag_supergrid_nx+1) * bag_supergrid_dx, (bag_supergrid_ny+1) * bag_supergrid_dy], sr_cell_size, allocate=False)
    # Revise this to be the largest resolution refinement and buffer on either side for that amount.  Better than 1/2 supergrid at least
    possible_overlap_x = vr.get_res_x()[good_refinements].max()
    possible_overlap_y = vr.get_res_y()[good_refinements].max()
    if sr_cell_size is None or sr_cell_size == 0:
        sr_cell_size = min(vr.get_res_x()[good_refinements].min(), vr.get_res_y()[good_refinements].min())  # / 2.0
    # For deomstration purposes, make our grid line up with the GDAL grid.
    # GDAL uses the bottom left (BAG origin) and doesn't consider the possible overrun that BAG has
    # so extend by the number of cells necessary to have the BAG origin fall on a cell corner
    num_cells_to_extend_x = int(possible_overlap_x / sr_cell_size) + 1
    possible_overlap_x = num_cells_to_extend_x * sr_cell_size
    num_cells_to_extend_y = int(possible_overlap_y / sr_cell_size) + 1
    possible_overlap_y = num_cells_to_extend_y * sr_cell_size

    xcells = int((2 * possible_overlap_x + bag_supergrid_nx * bag_supergrid_dx) / sr_cell_size) + 1
    ycells = int((2 * possible_overlap_y + bag_supergrid_ny * bag_supergrid_dy) / sr_cell_size) + 1
    sr_grid = Grid([bag_llx - possible_overlap_x, bag_lly - possible_overlap_y], [xcells, ycells], sr_cell_size, allocate=False)

    bagds = gdal.Open(input_file_full_path)
    if os.path.exists(dst_filename):
        os.remove(dst_filename)
    if os.path.exists(dst_filename + count_file_ext):
        os.remove(dst_filename + count_file_ext)
    fileformat = "GTiff"
    driver = gdal.GetDriverByName(fileformat)
    options = ["BLOCKXSIZE=256", "BLOCKYSIZE=256", "TILED=YES", "COMPRESS=LZW", "BIGTIFF=YES"]
    ds_val = driver.Create(dst_filename, sr_grid.numx, sr_grid.numy, bands=1, eType=gdal.GDT_Float32, options=options)
    ds_cnt = driver.Create(dst_filename + count_file_ext, sr_grid.numx, sr_grid.numy, bands=1, eType=gdal.GDT_Float32, options=options)

    ds_val.SetProjection(bagds.GetProjection())
    # bag_xform = bagds.GetGeoTransform()
    if snap_to_grid:
        half_x_grid = sr_grid.cell_size_x / 2  # Get half grid size so pixels are placed on 2,6,10 for 4m instead of 0,4,8s
        half_y_grid = sr_grid.cell_size_y / 2
        x_shift = math.floor((sr_grid.orig_x -half_x_grid)  /  sr_grid.cell_size_x) *  sr_grid.cell_size_x + half_x_grid  # Move to grid and force west
        y_shift = math.ceil((sr_grid.maxy - half_y_grid) / sr_grid.cell_size_y) *  sr_grid.cell_size_y + half_y_grid # Move to grid and force north
        xform = (x_shift, sr_grid.cell_size_x, 0, y_shift, 0, -sr_grid.cell_size_y)
    else: 
        xform = (sr_grid.orig_x, sr_grid.cell_size_x, 0, sr_grid.maxy, 0, -sr_grid.cell_size_y)
    ds_val.SetGeoTransform(xform)
    r_val = ds_val.GetRasterBand(1)
    r_val.SetNoDataValue(0)
    ds_cnt.SetProjection(bagds.GetProjection())
    ds_cnt.SetGeoTransform(xform)
    r_cnt = ds_cnt.GetRasterBand(1)
    r_cnt.SetNoDataValue(0)
    bagds = None  # close the bag file

    if use_blocks is None:
        use_blocks = True if int(bag_supergrid_ny * bag_supergrid_dy) * int(bag_supergrid_nx * bag_supergrid_dx) * 4 > 1000000000 else False

    if not use_blocks:
        grid_val = r_val.ReadAsArray()
        grid_count = r_cnt.ReadAsArray()
        col_offset = 0
        row_offset = 0

    for i, j in tqdm(numpy.flipud(index2d), mininterval=.7):  # [:25]:
        # index_start,dimensions_x,dimensions_y,resolution_x,resolution_y,sw_corner_x,sw_corner_y = varres_metadata_np[i, j]
        index_start = vr.varres_metadata[i, j, "index"]
        dimensions_x = vr.varres_metadata[i, j, "dimensions_x"]
        dimensions_y = vr.varres_metadata[i, j, "dimensions_y"]
        resolution_x = vr.varres_metadata[i, j, "resolution_x"]
        resolution_y = vr.varres_metadata[i, j, "resolution_y"]
        sw_corner_x = vr.varres_metadata[i, j, "sw_corner_x"]
        sw_corner_y = vr.varres_metadata[i, j, "sw_corner_y"]

        # print('Processing Tile_{0}_{1}  row x col: {2}x{3}   res:{4:.2f}  cornerx:{5:.2f}  size:x={6:.2f} y={7:.2f}'.format(i, j, dimensions_x, dimensions_y, resolution_x, sw_corner_x, dimensions_x*resolution_x, dimensions_y*resolution_y))
        # @TODO check this for accuracy
        supergrid_x = j * bag_supergrid_dx
        supergrid_y = i * bag_supergrid_dy
        refinement_llx = bag_llx + supergrid_x + sw_corner_x - resolution_x / 2.0  # @TODO implies swcorner is to the center and not the exterior
        refinement_lly = bag_lly + supergrid_y + sw_corner_y - resolution_y / 2.0
        index_end = index_start + int(dimensions_x * dimensions_y)
        # Using vr_depth or vr_uncrt reads the entire array, so we need to read the index range first then grab the depth
        #   -- much much faster for a large dataset
        # tile = self.vr_depth[index_start:index_end].reshape(dimensions_y, dimensions_x)
        tile = vr.varres_refinements[:, index_start:index_end][vr.varres_refinements.dtype.names[0]].reshape(dimensions_y, dimensions_x)
        # uncrt = self.vr_uncrt[index_start:index_end].reshape(dimensions_y, dimensions_x)
        # uncrt = self.varres_refinements[:, index_start:index_end][self.varres_refinements.dtype.names[1]].reshape(dimensions_y, dimensions_x)
        tile[tile == vr.fill_value] = numpy.nan

        # @TODO remember to pad the first/last row+col to remove the dead space "pane" between the refinement and the supergrid edge
        # compute the edges of the grid rows/columns and their related indices in the final SR grid
        if mode in (POINT, MASK, DATA_LOC_MASK):
            # use the cell centers which means the start/end index will be the same
            yends = ystarts = refinement_lly + numpy.arange(dimensions_y) * resolution_y + resolution_y / 2.0
            xends = xstarts = refinement_llx + numpy.arange(dimensions_x) * resolution_x + resolution_x / 2.0
        else:
            # determine the edges of the cells so they can be mapped into the new geotiff overlapped coordinate
            ystarts = refinement_lly + numpy.arange(dimensions_y) * resolution_y
            yends = refinement_lly + (numpy.arange(dimensions_y) + 1) * resolution_y - .000001
            xstarts = refinement_llx + numpy.arange(dimensions_x) * resolution_x
            xends = refinement_llx + (numpy.arange(dimensions_x) + 1) * resolution_x - .000001

            if edge_option in (STRETCH, FILL):
                # FILL always stretches the fist+last row/col to the edge of the supercell
                # STRETCH only fills the gap if the refinement is close the the edge
                # -- thinking the user didn't mean to leave the gap inherent in the BAG format
                apply_stretch = edge_option == STRETCH and sw_corner_x <= resolution_x and sw_corner_y <= resolution_y
                if edge_option == FILL or apply_stretch:
                    # print(xstarts[0], xends[-1], ystarts[0], yends[-1])
                    xstarts[0] = min(xstarts[0], bag_llx + supergrid_x)
                    xends[-1] = max(xends[-1], bag_llx + supergrid_x + bag_supergrid_dx - .000001)
                    ystarts[0] = min(ystarts[0], bag_lly + supergrid_y)
                    yends[-1] = max(yends[-1], bag_lly + supergrid_y + bag_supergrid_dy - .000001)
                    # print(xstarts[0], xends[-1], ystarts[0], yends[-1])
                if edge_option == STRETCH and not apply_stretch:
                    print("not stretched??")

        # convert the BAG coordinates into geotiff pixel indices
        # also reverse the rows since bag is lowerleft and tif is upper left
        row_end_indices = (sr_grid.numrow - 1) - numpy.array(sr_grid.row_index(ystarts), numpy.int_)
        row_start_indices = (sr_grid.numrow - 1) - numpy.array(sr_grid.row_index(yends), numpy.int_)
        col_start_indices = numpy.array(sr_grid.col_index(xstarts), numpy.int_)
        col_end_indices = numpy.array(sr_grid.col_index(xends), numpy.int_)

        if DEBUGGING:
            row_min = int(min(row_start_indices.min(), row_end_indices.min()))
            col_min = int(min(col_start_indices.min(), col_end_indices.min()))
            row_max = int(max(row_start_indices.max(), row_end_indices.max())) + 1
            col_max = int(max(col_start_indices.max(), col_end_indices.max())) + 1
            if row_min < 0 or row_max < 0 or col_min < 0 or col_max < 0:
                print("something is less than zero")
        if use_blocks:  # read the part of the geotiff that we need and modify it then write it back after applying the refinement grid
            row_offset = int(min(row_start_indices.min(), row_end_indices.min()))
            col_offset = int(min(col_start_indices.min(), col_end_indices.min()))
            row_max = int(max(row_start_indices.max(), row_end_indices.max())) + 1
            col_max = int(max(col_start_indices.max(), col_end_indices.max())) + 1
            # grid_val = r_val.ReadAsArray(row_offset, col_offset, row_max - row_offset, col_max - col_offset)
            # grid_count = r_cnt.ReadAsArray(row_offset, col_offset, row_max - row_offset, col_max - col_offset)  # col_offset, row_offset, col_max-col_offset, row_max-row_offset
            grid_val = r_val.ReadAsArray(col_offset, row_offset, col_max - col_offset, row_max - row_offset)
            grid_count = r_cnt.ReadAsArray(col_offset, row_offset, col_max - col_offset,
                                           row_max - row_offset)  # col_offset, row_offset, col_max-col_offset, row_max-row_offset

        # iterate the refinement cells and place each into the final SR grid
        for tile_i in range(tile.shape[0]):
            for tile_j in range(tile.shape[1]):
                cur_val = tile[tile_i, tile_j]
                # If there is real data or we are creating the MASK (which is jsut a map of cell centers) then write a value into output
                if not numpy.isnan(cur_val) or mode is MASK:
                    col_row_slice = numpy.s_[row_start_indices[tile_i] - row_offset:row_end_indices[tile_i] + 1 - row_offset,
                                    col_start_indices[tile_j] - col_offset:col_end_indices[tile_j] + 1 - col_offset]
                    if mode == MEAN:
                        grid_val[col_row_slice] += cur_val
                    elif mode == MIN:
                        grid_val[col_row_slice][grid_count[col_row_slice] == 0] = cur_val
                        grid_val[col_row_slice] = numpy.minimum(grid_val[col_row_slice], cur_val)
                    elif mode == MAX:
                        grid_val[col_row_slice][grid_count[col_row_slice] == 0] = cur_val
                        grid_val[col_row_slice] = numpy.maximum(grid_val[col_row_slice], cur_val)
                    elif mode in (POINT, DATA_LOC_MASK):
                        grid_val[col_row_slice] = cur_val
                    grid_count[col_row_slice] += 1
        if DEBUGGING:
            row_min = int(min(row_start_indices.min(), row_end_indices.min()))
            col_min = int(min(col_start_indices.min(), col_end_indices.min()))
            row_max = int(max(row_start_indices.max(), row_end_indices.max())) + 1
            col_max = int(max(col_start_indices.max(), col_end_indices.max())) + 1
            _plot(grid_val[row_min - row_offset:row_max - row_offset, col_min - col_offset:col_max - col_offset], "tile %d %d" % (i, j))

        # write out the current block to the TIFF file before we load/operate on the next one
        if use_blocks:
            r_val.WriteArray(grid_val, col_offset, row_offset)
            r_cnt.WriteArray(grid_count, col_offset, row_offset)
            if DEBUGGING:
                _plot(r_val.ReadAsArray(), 'grid before averaging')

    # normalize the TIF if needed (divide value by count for MEAN)
    # then write the array into the raster band
    if use_blocks:
        # plot(r_val.ReadAsArray(), 'grid before averaging')

        block_sizes = r_val.GetBlockSize()
        row_block_size = block_sizes[0]
        col_block_size = block_sizes[1]
        row_size = r_val.XSize
        col_size = r_val.YSize
        r_val.SetNoDataValue(nodata)
        for ic in tqdm(range(0, col_size, col_block_size), mininterval=.7):
            if ic + col_block_size < col_size:
                cols = col_block_size
            else:
                cols = col_size - ic
            for ir in tqdm(range(0, row_size, row_block_size), mininterval=.7):
                if ir + row_block_size < row_size:
                    rows = row_block_size
                else:
                    rows = row_size - ir
                data = r_val.ReadAsArray(ir, ic, rows, cols)
                cnt = r_cnt.ReadAsArray(ir, ic, rows, cols)
                if mode == MEAN:
                    with numpy.errstate(divide='ignore'):
                        res = data / cnt
                    res[cnt == 0] = nodata
                elif mode in (MIN, MAX, POINT):
                    res = data
                    res[cnt == 0] = nodata
                elif mode in (MASK, DATA_LOC_MASK):
                    res = data
                    res[cnt == 0] = nodata
                    res[cnt != 0] = 1
                r_val.WriteArray(res, ir, ic)
    else:
        if mode == MEAN:
            grid_val = grid_val / grid_count
            grid_val[grid_count == 0] = nodata
        elif mode in (MIN, MAX, POINT):
            grid_val[grid_count == 0] = nodata
        elif mode == MASK:
            grid_val[grid_count == 0] = nodata
            grid_val[grid_count != 0] = 1
        # print("min {}, max {}".format(numpy.nanmin(grid_val), numpy.nanmax(grid_val)))
        # grid_val = numpy.flipud(grid_val)
        r_val.SetNoDataValue(nodata)
        r_val.WriteArray(grid_val)
        # plot(r_val.ReadAsArray(), 'read back from tiff')

    # if use_blocks:
    #     grid_val = r_val.ReadAsArray()  # for testing read the whole thing -- this breaks on a super large file of course
    #     grid_count = r_cnt.ReadAsArray()  # for testing read the whole thing -- this breaks on a super large file of course
    #
    # plt.gca().invert_yaxis()
    # plot(grid_val, 'SR grid at res {}'.format(sr_cell_size, {MIN: "Min", MAX: "Max", MEAN: "Mean"}[mode]))
    #
    # plot(grid_count, "count")

    # a = numpy.fromfunction(lambda i, j: i + j, a.shape, dtype=numpy.float32)  # add a gradient

    ds_cnt = None  # close the count file so it can be deleted
    ds_val = None  # close the count file so it can be deleted
    try:
        pass
        # os.remove(dst_filename + count_file_ext)
    except PermissionError:
        pass
    return bag_supergrid_dx, bag_supergrid_dy, sr_cell_size



def interpolate_vr_bag(input_file_full_path, dst_filename, sr_cell_size=None, method='linear', use_blocks=True, nodata=numpy.nan):
    """ Interpolation scheme
    Create the POINT version of the TIFF with only data at precise points of VR BAG
    Load in blocks with enough buffer around the outside (nominally 3x3 supergrids with 1 supergrid buffer)
        run scipy.interpolate.griddata on the block (use linear as cubic causes odd peaks and valleys)
        copy the interior (3x3 supergrids without the buffer area) into the output TIFF

    Create the MIN (or MAX) version of the TIFF
    Load blocks of data and copy any NaNs from the MIN (cell based coverage) into the INTERP grid to remove erroneous interpolations,
    this essentially limits coverage to VR cells that were filled
    """
    fobj, point_filename = tempfile.mkstemp(".point.tif")
    os.close(fobj)
    fobj, min_filename = tempfile.mkstemp(".min.tif")
    os.close(fobj)
    if not DEBUGGING:
        dx, dy, cell_sz = VRBag_to_TIF(input_file_full_path, point_filename, sr_cell_size=sr_cell_size, mode=POINT, use_blocks=use_blocks,
                                       nodata=nodata)
        VRBag_to_TIF(input_file_full_path, min_filename, sr_cell_size=sr_cell_size, mode=MIN, use_blocks=use_blocks, nodata=nodata)
    else:
        dx, dy, cell_sz = 128, 128, 1.07
        point_filename = r"C:\Data\BAG\GDAL_VR\H-10771\ExampleForEven\H-10771_python.1m_point.tif"
        min_filename = r"C:\Data\BAG\GDAL_VR\H-10771\ExampleForEven\H-10771_python.1m_min.tif"

    points_ds = gdal.Open(point_filename)
    points_band = points_ds.GetRasterBand(1)
    points_no_data = points_band.GetNoDataValue()
    coverage_ds = gdal.Open(min_filename)
    coverage_band = coverage_ds.GetRasterBand(1)
    coverage_no_data = coverage_band.GetNoDataValue()
    interp_ds = points_ds.GetDriver().Create(dst_filename, points_ds.RasterXSize, points_ds.RasterYSize, bands=1, eType=points_band.DataType,
                                             options=["BLOCKXSIZE=256", "BLOCKYSIZE=256", "TILED=YES", "COMPRESS=LZW", "BIGTIFF=YES"])
    interp_ds.SetProjection(points_ds.GetProjection())
    interp_ds.SetGeoTransform(points_ds.GetGeoTransform())
    interp_band = interp_ds.GetRasterBand(1)
    interp_band.SetNoDataValue(nodata)

    if use_blocks:
        pixels_per_supergrid = int(max(dx / cell_sz, dy / cell_sz)) + 1
        row_block_size = col_block_size = 3 * pixels_per_supergrid
        row_buffer_size = col_buffer_size = 1 * pixels_per_supergrid
        row_size = interp_band.XSize
        col_size = interp_band.YSize
        for ic in tqdm(range(0, col_size, col_block_size), mininterval=.7):
            cols = col_block_size
            if ic + col_block_size > col_size:  # read a full set of data by offsetting the column index back a bit
                ic = col_size - cols
            col_buffer_lower = col_buffer_size if ic >= col_buffer_size else ic
            col_buffer_upper = col_buffer_size if col_size - (ic + col_block_size) >= col_buffer_size else col_size - (ic + col_block_size)
            read_cols = col_buffer_lower + cols + col_buffer_upper
            for ir in tqdm(range(0, row_size, row_block_size), mininterval=.7):
                rows = row_block_size
                if ir + row_block_size > row_size:
                    ir = row_size - rows
                row_buffer_lower = row_buffer_size if ir >= row_buffer_size else ir
                row_buffer_upper = row_buffer_size if row_size - (ir + row_block_size) >= row_buffer_size else row_size - (ir + row_block_size)
                read_rows = row_buffer_lower + rows + row_buffer_upper
                points_array = points_band.ReadAsArray(ir - row_buffer_lower, ic - col_buffer_lower, read_rows, read_cols)

                # Find the points that actually have data as N,2 array shape that can index the data arrays
                if numpy.isnan(points_no_data):
                    point_indices = numpy.nonzero(~numpy.isnan(points_array))
                else:
                    point_indices = numpy.nonzero(points_array != points_no_data)
                # if there were any data points then do interpolation -- could be all empty space too which raises Exception in griddata
                if len(point_indices[0]):
                    # get the associated data values
                    point_values = points_array[point_indices]
                    # interpolate all the other points in the array
                    # (actually it's interpolating everywhere which is a waste of time where there is already data)
                    xi, yi = numpy.mgrid[row_buffer_lower:row_buffer_lower + row_block_size,
                             col_buffer_lower:col_buffer_lower + col_block_size]
                    interp_data = scipy.interpolate.griddata(numpy.transpose(point_indices), point_values,
                                                             (xi, yi), method=method)
                    # mask based on the cell coverage found using the MIN mode
                    coverage_data = coverage_band.ReadAsArray(ir, ic, row_block_size, col_block_size)
                    interp_data[coverage_data == coverage_no_data] = nodata
                    # Write the data into the TIF on disk
                    interp_band.WriteArray(interp_data, ir, ic)
        if DEBUGGING:
            points_array = points_band.ReadAsArray()
            interp_array = interp_band.ReadAsArray()
            _plot(points_array)
            _plot(interp_array)
    else:
        points_array = points_band.ReadAsArray()
        coverage_data = coverage_band.ReadAsArray()

        # Find the points that actually have data
        if numpy.isnan(points_no_data):
            point_indices = numpy.nonzero(~numpy.isnan(points_array))
        else:
            point_indices = numpy.nonzero(points_array != points_no_data)
        # get the associated data values
        point_values = points_array[point_indices]
        # interpolate all the other points in the array (actually interpolating everywhere which is a waste of time where there is already data)
        xi, yi = numpy.mgrid[0:points_array.shape[0], 0:points_array.shape[1]]
        interp_data = scipy.interpolate.griddata(numpy.transpose(point_indices), point_values,
                                                 (xi, yi), method=method)
        _plot(interp_data)
        # mask based on the cell coverage found using the MIN mode
        interp_data[coverage_data == coverage_no_data] = nodata
        _plot(interp_data)
        # Write the data into the TIF on disk
        interp_band.WriteArray(interp_data)

    # release the temporary tif files and delete them
    point_band = None
    point_ds = None
    coverage_band = None
    coverage_ds = None
    if not DEBUGGING:
        os.remove(min_filename)
        os.remove(point_filename)


def _plot(a, title=''):
    if DEBUGGING:
        plt.figure()
        plt.imshow(a, aspect='auto')
        plt.title(title)
        plt.draw()
        plt.show()


if __name__ == "__main__":
    if 1:
        VRBag_to_TIF(r"K:\Survey_Outline_Examples\Debugging\H12993_MB_VR_MLLW.bag", r"K:\Survey_Outline_Examples\Debugging\H12993_MB.bag.tif", 8)
    if 0:
        bag = VRBag.new_bag(r"K:\Survey_Outline_Examples\debugging\from_scratch.bag")
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(26900 + 10)  # zone 10 north
        bag.horizontal_crs_wkt = srs.ExportToWkt()

        stripes = Refinement(numpy.array(([1, 1, 1, 1],
                                          [2, 2, 2, 2],
                                          [4, 4, 4, 4],
                                          [0, 1, 0, 1]), dtype=numpy.float32), None, 64 / 3, 64 / 3)

        diag = Refinement(numpy.array(([1, 0, 0, 0],
                                       [0, 1, 0, 0],
                                       [0, 0, 1, 0],
                                       [0, 0, 0, 1]), dtype=numpy.float32), None, 64 / 3, 64 / 3)

        low = Refinement(numpy.array(([1, 0, 0],
                                      [0, 0, 0],
                                      [0, 1, 0]), dtype=numpy.float32), None, 64 / 2, 64 / 2)

        llx, lly = 502000, 5290000
        resx, resy = 64, 64

        bag.set_refinements([[stripes, stripes, None], [diag, diag, None], [low, None, None]])
        bag.set_res((resx, resy))
        bag.set_origin((llx, lly))
        # print(bag.pretty_xml_string)
        bag.close()
        del bag
        if 0:
            # make a bag with no data just to create an xml element
            xml = VRBag.make_xml(srs, 0, 0, 0, 0, 0, 0, 0, 0, 1024, 1024, 64.32, 64.32)
            bag = VRBag.new_bag(r"K:\Survey_Outline_Examples\debugging\just_xml.bag", xml)
            bag.minx = llx
            bag.miny = lly
            bag._set_geo_strings()
            # print(bag.pretty_xml_string)
            xml2 = bag.xml_string
            bag.close()
            del bag

    if 0:
        # try modifying a caris made vr bag and see if it still works
        import os
        import shutil

        try:
            os.remove(r"K:\Survey_Outline_Examples\Variable_resolution\H12993_MB_VR_MLLW - Copy3.bag")
        except FileNotFoundError:
            pass
        shutil.copyfile(r"K:\Survey_Outline_Examples\Variable_resolution\H12993_MB_VR_MLLW.bag",
                        r"K:\Survey_Outline_Examples\Variable_resolution\H12993_MB_VR_MLLW - Copy3.bag")
        bag = VRBag(r"K:\Survey_Outline_Examples\Variable_resolution\H12993_MB_VR_MLLW - Copy3.bag")
        bag.xml_string = bag.xml_string  # is elementtree breaking something -- this should be a no-op except it changes namespaces
        print(bag.pretty_xml_string)
        # bag.minx = llx
        # bag.miny = lly
        # bag.xml_string = xml2
        bag.close()
        """
        XML input source: BAG_root/metadata
        Validation output: INVALID
        Reasons:
         - Element '{http://www.opengis.net/gml/3.2}TimePeriod', attribute '{http://www.w3.org/2001/XMLSchema-instance}type': The QName value 'gml:TimePeriodType' has no corresponding namespace declaration in scope., line 240
         - <string>:240:0:ERROR:SCHEMASV:SCHEMAV_CVC_DATATYPE_VALID_1_2_1: Element '{http://www.opengis.net/gml/3.2}TimePeriod', attribute '{http://www.w3.org/2001/XMLSchema-instance}type': The QName value 'gml:TimePeriodType' has no corresponding namespace declaration in scope.
         - The gmd:spatialRepresentationType/gmd:MD_SpatialRepresentationTypeCode should be set to 'grid' [$5.3.1.2].
        """

    if 0:
        bag = VRBag.from_existing_bag(r"K:\Survey_Outline_Examples\Variable_resolution\H12993_MB_VR_MLLW.bag",
                                      r"K:\Survey_Outline_Examples\Variable_resolution\from_copied_xml.bag")
        the_x = numpy.array(([1, 0, 0, 2],
                             [0, 1, 2, 0],
                             [0, 2, 1, 0],
                             [2, 0, 0, 1]), dtype=numpy.float32)
        x_refinement = Refinement(the_x, None, bag.cell_size_x / (the_x.shape[0] - 1), bag.cell_size_y / (the_x.shape[1] - 1))

        import random

        data = []
        for i in range(256):
            data.append([])
            for j in range(256):
                if random.random() < .05:
                    data[-1].append(x_refinement)
                else:
                    data[-1].append(None)
        bag.set_refinements(data)
        # bag.set_res((resx, resy))
        # bag.set_origin((llx, lly))
        bag.close()
    print("done")
    import sys  # pycharm is staying in a console after debugging, so just forcing it to close (do I have a switch wrong?)
    if 0:
        sssfile = SRBag.new_bag(r'c:\temp\testbounds.bag')
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(26900 + 10)  # zone 10 north
        sssfile.horizontal_crs_wkt = srs.ExportToWkt()
        sss_data = numpy.zeros((4, 7))
        sssfile.numx = sss_data.shape[1]  # columns
        sssfile.numy = sss_data.shape[0]  # rows

        sssfile.set_elevation(sss_data)
        sssfile.set_uncertainty(numpy.zeros(sss_data.shape))

        sssfile.set_res((2, 2))
        sssfile.set_origin((500000, 4000000))
        sssfile.close()

        del sssfile
    sys.exit()

if 0:  # sample of changing coordinate referenec system in a bag
    from HSTB.drivers import bag
    sr = bag.SRBag(r"C:\Pydro22_Dev\NOAA\site-packages\Python38\git_repos\s100py\tests\s102\F00788_SR_8m_32610.bag", mode="r+")
    sr.horizontal_crs_wkt
    Out[4]: 'PROJCS["NAD83 / UTM zone 10N",GEOGCS["NAD83",DATUM["North American Datum 1983",SPHEROID["GRS 1980",6378137,298.2572221010041,AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree (supplier to define representation)",0.0174532925199433,AUTHORITY["EPSG","9122"]],EXTENSION["tx_authority","NA83"],AUTHORITY["EPSG","4269"]],PROJECTION["Transverse_Mercator",AUTHORITY["EPSG","16010"]],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-123],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","26910"]]'
    from osgeo import osr
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(32610)
    sr.horizontal_crs_wkt = crs.ExportToWkt()
    sr.close()
