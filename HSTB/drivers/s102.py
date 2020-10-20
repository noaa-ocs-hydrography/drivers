import tempfile
import subprocess
import traceback
import functools

import h5py
import numpy


class S102File(h5py.File):
    top_level_keys = ('BathymetryCoverage', 'S102_Grid', 'S102_BathymetryCoverage')
    second_level_keys = ('BathymetryCoverage.01', 'S102_Grid.01', 'S102_BathymetryCoverage.01', 'BathymetryCoverage_01', 'S102_Grid_01', 'S102_BathymetryCoverage_01', )
    group_level_keys = ('Group.001', 'Group_001',)
    value_level_keys = ("values",)
    depth_keys = ("depth", "depths", 'elevation', "elevations", "S102_Elevation")

    def __init__(self, fname=""):
        super().__init__(fname, "r", driver="family", memb_size=681574400)

    def print_overview(self, display_nodes=10):
        depths = self.get_depths()
        print("shape of grid is", depths.shape)
        with numpy.printoptions(precision=2, suppress=True, linewidth=200):
            x, y = depths.shape
            r = max(x, y)
            step = int(r / display_nodes)
            print(depths[::step, ::step])

    def print_depth_attributes(self):
        hdf5 = self.get_depth_dataset()
        print(hdf5.attrs)

    def get_depth_dataset(self):
        for k in self.top_level_keys:
            if k in self:
                d = self[k]
                break
        try:
            d
        except NameError:
            raise KeyError(str(self.top_level_keys) + " were not found in " + str(list(self.keys())))

        for k in self.second_level_keys:
            if k in d:
                g = d[k]
                break
        try:
            g
        except NameError:
            raise KeyError(str(self.second_level_keys) + " were not found in " + str(list(d.keys())))

        for k in self.group_level_keys:
            if k in g:
                gp = g[k]
                break
        try:
            gp
        except NameError:
            raise KeyError(str(self.group_level_keys) + " were not found in " + str(list(g.keys())))

        for k in self.group_level_keys:
            if k in g:
                gp = g[k]
                break
        try:
            gp
        except NameError:
            raise KeyError(str(self.group_level_keys) + " were not found in " + str(list(g.keys())))

        for k in self.value_level_keys:
            if k in gp:
                v = gp[k]
                break
        try:
            v
        except NameError:
            raise KeyError(str(self.value_level_keys) + " were not found in " + str(list(gp.keys())))
        return v

    def get_depths(self):
        v = self.get_depth_dataset()
        # v.dtype
        # dtype([('S102_Elevation', '<f4'), ('S102_Uncertainty', '<f4')])
        for k in self.depth_keys:
            if k in v.dtype.names:
                return v[k]
        raise KeyError(str(self.depth_keys) + " were not found in " + str(list(v.dtype.names)))

    @staticmethod
    def convert_bag(bag_path, output_path, path_to_convertor=".\\BAG_to_S102.exe", buffer=False):
        cmd = '"' + path_to_convertor + '" "' + bag_path + '" "' + output_path + '"'
        print(cmd)
        if buffer:
            std_out = tempfile.TemporaryFile()  # deleted on exit from function
            std_err = tempfile.TemporaryFile()
        else:
            std_out = None
            std_err = None
        p = subprocess.Popen(cmd, stdout=std_out, stderr=std_err)
        p.wait()
        if buffer:
            std_out.seek(0)
            std_err.seek(0)
            out = std_out.read()
            err = std_err.read()
            print(out)
            print(err)

    def show_keys(self, obj, indent=0):
        try:  # print attributes of dataset or group
            print("    " * indent + "ATTRS: " + str(list(obj.attrs.items())))
        except:
            print("    " * indent + "No attributes")
        if hasattr(obj, "keys"):
            for k in obj.keys():
                print("    " * indent + k)
                self.show_keys(obj[k], indent + 1)
        else:
            print("    " * indent + str(obj))
            indent = indent + 1
            try:  # print out any dataset arrays
                for n in obj.dtype.names:
                    try:
                        s = str(obj[n][:10])
                        s = "    " * (indent + 1) + s.replace("\n", "\n" + "    " * (indent + 1))
                        print("    " * indent, n, obj[n].shape)
                        print(s)
                    except:
                        traceback.print_exc()
            except:
                try:
                    s = str(obj[:])
                    s = "    " * (indent + 1) + s.replace("\n", "\n" + "    " * (indent + 1))
                    print("    " * indent, obj.shape)
                    print(s)
                except:
                    print("    " * indent + "dtype not understood")


convertor_path = r"C:\Git_Repos\BagToS102\x64\Release\BAG_to_S102.exe"
bag_path = r"C:\Git_Repos\BagToS102\x64\Debug\LA_LB_Area_GEO.bag"
bag_path = r"C:\downloads\S102\S102__linux_from_NAVO\BAG_to_S102_converter\sample_data\LA_LB_Area_UTM_original.bag"
output_path = r"C:\Git_Repos\BagToS102\x64\Release\test_output"

convert=False
if convert:
    print("converting", bag_path, "to", output_path)
    S102File.convert_bag(bag_path, output_path, convertor_path)
    print("finished")

paths = [  # r"C:\downloads\S102\S102__linux_from_NAVO\BAG_to_S102_converter\sample_data\LA_LB_Area_UTM_original.bag_%d.h5",
    # r"C:\downloads\S102\s102_first_from_george\sample_output\LA_LB_AREA_UTM_S102_%d.h5",
    # r"C:\downloads\S102\s102_third_from_george\x64\Debug\LA_LB_Area_GEO_reprojected.bag_%d.h5",
    # r"C:\downloads\S102\s102_third_from_george\x64\Debug\BATHY_GEN_resolution_10m.bag_%d.h5",
    output_path + "_%d.h5",
    # r"C:\downloads\S102\sample_hdf5_data\h5ex_t_bitatt.h5",
]
# r"C:\downloads\S102\S102__linux_from_NAVO\BAG_to_S102_converter\sample_data\LA_LB_Area_UTM_original.bag_%d.h5"
for fname in paths:
    print(fname)
    f = S102File(fname)
    f.print_overview()
    f.print_depth_attributes()
    f.show_keys(f)
    d = f["Group_F"]["BathymetryCoverage"]

#
# list(f.attrs.items())
# # [('boundingBox.eastBoundLongitude', 392475.0), ('boundingBox.northBoundLatitude', 3754110.0), ('boundingBox.southBoundLatitude', 3738555.0), ('boundingBox.westBoundLongitude', 379470.0), ('geographicIdentifier', b'Long Beach, CA'), ('horizontalDatumEpoch', 2005.0), ('horizontalDatumReference', b'EPSG'), ('horizontalDatumValue', b'PROJCS["UTM-11N-Nad83",GEOGCS["unnamed",DATUM["North_American_Datum_1983",SPHEROID["North_American_Datum_1983",6378137,298.2572201434276],TOWGS84[0,0,0,0,0,0,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],EXTENSION["Scaler","0,0,0,0.01,0.01,0.'), ('issueDate', b'2016-06-13'), ('metaFeatures', b'LA_LB_Area_UTM_original.bag.gml'), ('metadata', b'LA_LB_Area_UTM_original.bag.xml'), ('productSpecification', b'BAG'), ('timeOfIssue', b'2016-06-13')]
# list(f.keys())
# # ['Group_F', 'S102_Grid', 'S102_Tracking_List', 'boundingBox', 'sequenceRule']
# d = f['boundingBox']
# d = f['S102_Grid']
# list(d.keys())
# # ['S102_Grid_01', 'axisNames']
# g = d["S102_Grid_01"]
# list(g.keys())
# # ['Group_001']
# g001=g['Group_001']
# list(g001.keys())
# # ['values']
# v = g001['values']
# v.shape
# # (3111, 2601)
# v.dtype
# # dtype([('S102_Elevation', '<f4'), ('S102_Uncertainty', '<f4')])
# v["S102_Elevation"].shape
# # (3111, 2601)
# numpy.min(v["S102_Elevation"])
# # -36.03
# numpy.max(v["S102_Elevation"])
# # 1000000.0
# depths = v["S102_Elevation"]
# numpy.set_printoptions(precision=2, suppress=True, linewidth=200)
# print(depths[::300, ::300])
# new_sample= r"C:\downloads\S102\S102_Update__from_NAVO_for_edition_2.0.0_June2019\BAG_to_S102_converter_v2_0\BAG_to_S102_converter\sample_data\102NOAA_LA_LB_AREA_GEO_%d.h5"
# h5py.File(new_sample, "r", driver="family", memb_size=681574400)
# # <HDF5 file "102NOAA_LA_LB_AREA_GEO_%d.h5" (mode r)>
# nf = h5py.File(new_sample, "r", driver="family", memb_size=681574400)
# list(nf.attrs.items())
# # [('eastBoundLongitude', -118.182045), ('epoch', b'20131016'), ('geographicIdentifier', b'Long Beach, CA'), ('horizontalDatumReference', b'EPSG'), ('horizontalDatumValue', 4326), ('issueDate', b'2018/6/28'), ('metaFeatures', b'sample_data/102NOAA_LA_LB_AREA_GEO.gml'), ('metadata', b'sample_data/102NOAA_LA_LB_AREA_GEO.xml'), ('northBoundLatitude', 33.92136), ('productSpecification', b'BAG'), ('southBoundLatitude', 33.780685), ('timeOfIssue', b'2018/6/28'), ('westBoundLongitude', -118.29966)]
# list(nf.keys())
# # ['BathymetryCoverage', 'Group_F', 'TracklingListCoverage']
# list(f.keys())
# # ['Group_F', 'S102_Grid', 'S102_Tracking_List', 'boundingBox', 'sequenceRule']
# nd = nf['BathymetryCoverage']
# list(nd.keys())
# # ['BathymetryCoverage_01', 'axisNames']
# nd01 = nd['BathymetryCoverage_01']
# list(nd01.keys())
# # ['Group_001']
# ng = nd01['Group_001']
# list(ng.keys())
# # ['values']
# nv = ng["values"]
# nv.shape
# # (3111, 2601)
# type(nv)
# # <class 'h5py._hl.dataset.Dataset'>
# nv.dtype
# # dtype([('depth', '<f4'), ('uncertainty', '<f4')])
# nv.compression
# # 'gzip'
# v.compression
# nv.fillvalue
# # (0., 0.)
# v.fillvalue
# # (0., 0.)
# ndepths=nv["depth"]
# print(ndepths[::300, ::300])
# debug = r"C:\Git_Repos\BagToS102\x64\Debug\test2_0_debug_%d.h5"
# nf = h5py.File(debug, "r", driver="family", memb_size=681574400)
# list(nf.attrs.items())
# # [('eastBoundLongitude', 491710.0), ('epoch', b'20131016'), ('geographicIdentifier', b'Long Beach, CA'), ('horizontalDatumReference', b'EPSG'), ('horizontalDatumValue', 4326), ('issueDate', b'2019-02-05'), ('metaFeatures', b'.\\test2_0_debug.gml'), ('metadata', b'.\\test2_0_debug.xml'), ('northBoundLatitude', 5719550.0), ('productSpecification', b'BAG'), ('southBoundLatitude', 5691370.0), ('timeOfIssue', b'2019-02-05'), ('westBoundLongitude', 458060.0)]
# list(nf.keys())
# # ['BathymetryCoverage', 'Group_F', 'TracklingListCoverage']
# nd = nf['BathymetryCoverage']
# list(nd.keys())
# # ['BathymetryCoverage_01', 'axisNames']
# nd01 = nd['BathymetryCoverage_01']
# ng = nd01['Group_001']
# nv = ng["values"]
# nv.dtype
# # dtype([('depth', '<f4'), ('uncertainty', '<f4')])
# nv.compression
# ndepths=nv["depth"]
# ndepths.size
# # 9482570
# ndepths.shape
# # (2818, 3365)
# print(ndepths[::300, ::300])
