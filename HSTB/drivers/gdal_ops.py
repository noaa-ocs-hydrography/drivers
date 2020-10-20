import os
import sys
import subprocess
import ast
import distutils.sysconfig
from datetime import datetime

from PIL import Image
import numpy as np

from HSTB.osgeo_importer import ogr, gdal, osr  # sets up gdal_data and s57 attributes
from HSTB.resources import create_env_cmd_list
from shapely.geometry import shape

# import matplotlib.pyplot as plt
# import matplotlib as mpl
# from matplotlib.colors import ListedColormap


_pythonpath = os.path.dirname(os.path.dirname(distutils.sysconfig.get_python_lib()))  # python_dir/lib/site-packages then back to python_dir
_use_env = "Pydro367"


def find_command(command):
    gdalfolder = os.path.dirname(gdal.__file__)
    finalpath = os.path.join(gdalfolder, 'scripts', command + '.py')
    if not os.path.exists(finalpath):
        realpath = os.path.join(_pythonpath, 'Scripts')
        finalpath = os.path.join(realpath, command + '.py')
        if not os.path.exists(finalpath):
            realpath = os.path.join(_pythonpath, 'Library', 'bin')
            finalpath = os.path.join(realpath, command + '.exe')
            if not os.path.exists(finalpath):
                print('{} was not found.  Please contact HSTB for assistance.'.format(finalpath))
                return ''
    return finalpath


def find_ogr2ogr():
    finalpath = os.path.join(_pythonpath, 'Library', 'bin', 'ogr2ogr.exe')
    if not os.path.exists(finalpath):
        print('{} was not found.  Please contact HSTB for assistance.'.format(finalpath))
        return ''
    else:
        return finalpath


def bag_to_raster(src_filename, out_filename, resX=None, resY=None, input_args="", output_args=""):
    """
    bag_to_tif(data/test_vr.bag, out.bag)
    results in:
       gdal_translate data/test_vr.bag -oo MODE=RESAMPLED_GRID out.bag

    bag_to_tif(data/test_vr.bag, out.tif, 5, 5, output_args='-co "VAR_ABSTRACT=My abstract"')
    results in:
       gdal_translate data/test_vr.bag -oo MODE=RESAMPLED_GRID -oo RESX=5 -oo RESY=5 out.tif -co "VAR_ABSTRACT=My abstract"
    """

    gdal_translate = find_command("gdal_translate")
    res_x_str = ""
    if resX:
        res_x_str = " -oo RESX=" + str(resX)
    res_y_str = ""
    if resY:
        res_y_str = " -oo RESY=" + str(resY)

    command = create_env_cmd_list(_use_env) + [gdal_translate, '"' + src_filename + '"', "-oo MODE=RESAMPLED_GRID" + res_x_str + res_y_str, input_args,
                                  '"' + out_filename + '"', output_args]
    full_command = " ".join(command)
    p = subprocess.Popen(full_command)
    p.wait()
    if os.path.exists(out_filename):
        return out_filename
    else:
        raise Exception("Failed to create tif from bag :" + full_command)


def tif_to_shp(src, ogr_format, userdest=None):
    print('**********Running SNM from TIF Utility**********')
    dest = ''
    area_sq_nm = 0
    timestamp = datetime.now().strftime('%m%d%y_%H%M%S')
    gdal_polygonize = find_command('gdal_polygonize')
    if gdal_polygonize:
        src_dir, src_name = os.path.split(src)
        if userdest is not None:
            dest = os.path.join(userdest, 'tifshp_' + timestamp + '.shp')
        else:
            dest = os.path.join(src_dir, 'tifshp_' + timestamp + '.shp')

        command = create_env_cmd_list(_use_env) + ['python', gdal_polygonize, '"' + src + '"', '-f', '"' + ogr_format + '"', '"' + dest + '"']
        print('Converting to shp file...')
        p = subprocess.Popen(" ".join(command))
        while p.poll() is None:
            pass
        if os.path.exists(dest):
            driver = ogr.GetDriverByName("ESRI Shapefile")
            dataSource = driver.Open(dest, 1)
            lyr = dataSource.GetLayer()
            a = []
            for feature in lyr:
                geom = feature.GetGeometryRef()
                a.append(geom.GetArea())
            a_np = np.array(a)
            area_sq_meters = a_np.sum()
            area_sq_nm = float(area_sq_meters / 3429904.000)
            print('{} in square meters, {} in SNM'.format(area_sq_meters, area_sq_nm))
            if src_name == 'tifblank.tif':
                os.remove(src)
        else:
            print('Conversion unsuccessful.  shp file not created.  Please contact HSTB.')
    else:
        print('SNM from TIF skipped.  No valid command found')
    print('**********SNM from TIF Complete**********')
    return dest, area_sq_nm


def dissolve_shapefile(self, src):
    print('**********Running Dissolve Shapefile Utility**********')
    dest = ''
    cmd = find_ogr2ogr()
    if cmd:
        print('Dissolving shapefile...{}'.format(src))
        src_dir, src_name = os.path.split(src)
        dest = os.path.splitext(src)[0] + '_DISSOLVED.shp'
        lyrname = os.path.splitext(src_name)[0]

        command = create_env_cmd_list(_use_env) + [cmd, '"' + dest + '"', '"' + src + '"', '-dialect', 'sqlite', '-sql',
                                      '"SELECT ST_Union(geometry) FROM ' + lyrname + '"']

        print('Writing to {}...'.format(dest))
        p = subprocess.Popen(" ".join(command))
        while p.poll() is None:
            pass
        if os.path.exists(dest):
            print('File successfully written')
            os.remove(src)
            os.remove(os.path.splitext(src)[0] + '.dbf')
            os.remove(os.path.splitext(src)[0] + '.shx')
            os.remove(os.path.splitext(src)[0] + '.prj')
        else:
            print('Conversion unsuccessful.  shp file not created.  Please contact HSTB.')
    else:
        print('Dissolve shapefile skipped.  No valid command found')
    print('**********Dissolve Shapefile Complete**********')
    return dest


def tif_to_shp_with_metrics(options, tif):
    if os.path.exists(tif):
        tifdest = single_band_mask_from_tif(tif)
        if os.path.exists(tifdest):
            shpdest, options['area_sq_nm'] = tif_to_shp(tifdest, 'ESRI Shapefile')
            if os.path.exists(shpdest):
                shpdest_dis = dissolve_shapefile(shpdest)
                if os.path.exists(shpdest_dis):
                    options['wktdata_shapefile'] = simplify_shapefile(shpdest_dis)

                    # Tack on projection from tif
                    epsg = return_epsg_from_tif(tif)
                    options['wktdata_shapefile'] += ', {}'.format(epsg)


def run_merge(src, dest, search_subdirectories=False, snm_calc=False):
    print('**********Running Merge GeoTIF Utility**********')
    gdalmerge = find_command('gdal_merge')
    if gdalmerge:
        images = []
        if search_subdirectories:
            for root, dirs, files in os.walk(src):
                for file in files:
                    extension = os.path.splitext(file)[1].lower()
                    if extension in ['.tif', '.tiff']:
                        images.append('"' + os.path.join(root, file) + '"')
                        print('Including {}'.format(file))
        else:
            for file in os.listdir(src):
                extension = os.path.splitext(file)[1].lower()
                if extension in ['.tif', '.tiff']:
                    images.append('"' + os.path.join(src, file) + '"')
                    print('Including {}'.format(file))
        print('Found {} images'.format(len(images)))
        if snm_calc:
            tot_snm = np.array([])
            for image in images:
                snm = tif_to_shp(image.strip('"'), 'ESRI Shapefile')
                tot_snm = np.append(tot_snm, [snm])
            print('Total SNM = {}'.format(tot_snm.sum()))
        command = create_env_cmd_list(_use_env) + ['python', gdalmerge] + images + \
            ['-init', '255', '-o', '"' + dest + '"']
        print('Combining images...')
        p = subprocess.Popen(" ".join(command))
        while p.poll() is None:
            pass
        if os.path.exists(dest):
            print('Combine complete.  {} generated.'.format(dest))
        else:
            print('Creation unsuccessful.  {} not generated.  Please contact HSTB.')
    else:
        print('Merge GeoTIF skipped.  No valid command found')
    print('**********Merge GeoTIF Complete**********')


def overlay_images(img_stack, dest, extents_ulx=None, extents_uly=None, extents_lrx=None, extents_lry=None,
                   colorbar='', compress=True):
    # img_stack - array of images, first goes on bottom, last on top
    print('**********Running Overlay Images Utility**********')
    gdalmerge = find_command('gdal_merge')
    if gdalmerge and img_stack and dest:
        command = create_env_cmd_list(_use_env) + ['python', gdalmerge]
        if compress:
            command += ['-co', 'compress=LZW']
        if (extents_ulx == None) or (extents_uly == None) or (extents_lrx == None) or (extents_lry == None):
            print('No extents given.')
            command += ['-init', '0', '-o', '"' + dest + '"']
        else:
            command += ['-init', '0', '-ul_lr', str(extents_ulx), str(extents_uly), str(extents_lrx),
                        str(extents_lry), '-o', '"' + dest + '"']
        for img in img_stack:
            command += ['"' + img + '"']
        print('Combining images...')
        p = subprocess.Popen(" ".join(command))
        while p.poll() is None:
            pass
        if os.path.exists(dest):
            print('Combine complete.  {} generated.'.format(dest))
            if colorbar:
                add_on_elements(dest, colorbar)
        else:
            print('Creation unsuccessful.  {} not generated.  Please contact HSTB.')
    else:
        print('Overlay Images skipped.  No valid command found')
    print('**********Overlay Images Complete**********')


def add_on_elements(src, cb=None):
    if os.path.exists(src):
        background = Image.open(src)
        dest = os.path.join(os.path.dirname(src), 'finalimage.tif')
        if cb != None:
            print('Attaching add on elements...')
            foreground = Image.open(cb)
            # you want to scale up (most likely up, unless a small sheet) by factor of 4
            # color bar is default 600,100, so scale y by factor of 6
            newfground_size = (int(background.size[0] / 4), int(background.size[0] / 24))
            newfground = foreground.resize((newfground_size[0], newfground_size[1]), Image.ANTIALIAS)
            background.paste(newfground, (background.size[0] / 2 - int(newfground_size[0] / 2),
                                          background.size[1] - newfground_size[1]), newfground)
            background.save(dest)


def single_band_mask_from_tif(src):
    print('Building mask tif...')
    gdal_calc = find_command('gdal_calc')
    dest = ''
    if gdal_calc:
        src_dir, src_name = os.path.split(src)
        dest = os.path.join(src_dir, 'tifblank.tif')

        command = create_env_cmd_list(_use_env) + ['python', gdal_calc, '-A', '"' + src + '"', '--outfile="' + dest + '"', '--calc="A>0"']
        p = subprocess.Popen(" ".join(command))
        while p.poll() is None:
            pass
        if os.path.exists(dest):
            print('Tif mask created')
        else:
            print('Unable to generate TIF mask using gdal_calc.')
    else:
        print('Single band mask skipped.  No valid command found')
    return dest


def pallete_to_rgb(src):
    print('Converting to RGB...')
    pct2rgb = find_command('pct2rgb')
    src_dir, src_name = os.path.split(src)
    dest = os.path.join(src_dir, os.path.splitext(src_name)[0] + '_rgb.tif')
    command = create_env_cmd_list(_use_env) + ['python', pct2rgb]
    command += ['"' + src + '"', '"' + dest + '"']
    p = subprocess.Popen(" ".join(command))
    while p.poll() is None:
        pass
    if os.path.exists(dest):
        print('Conversion complete')
    else:
        print('Unable to convert to RGB')
    return dest


def compress_raster(src, remove_orig=False):
    print('Compressing...')
    gdal_translate = find_command('gdal_translate')
    src_dir, src_name = os.path.split(src)
    dest_comp = os.path.join(src_dir, os.path.splitext(src_name)[0] + '_compressed.tif')
    command = ["cmd.exe", "/C", gdal_translate, '-co', 'compress=LZW',
               '"' + src + '"', '"' + dest_comp + '"']
    p = subprocess.Popen(" ".join(command))
    while p.poll() is None:
        pass
    if os.path.exists(dest_comp):
        # os.remove(src)
        print('Compression complete')
        return dest_comp
    else:
        print('Unable to compress')
    return ''


def floatingpoint_to_greyscale(src, compress=True):
    print('Converting to RGB...')
    gdal_translate = find_command('gdal_translate')
    src_dir, src_name = os.path.split(src)
    dest_comp = os.path.join(src_dir, os.path.splitext(src_name)[0] + '_rgb.tif')
    command = ["cmd.exe", "/C", gdal_translate]
    if compress:
        command += ['-co', 'compress=LZW']
    command += ['-co', 'PHOTOMETRIC=RGB', '-ot', 'Byte', '-scale', '"' + src + '"', '"' + dest_comp + '"']
    p = subprocess.Popen(" ".join(command))
    while p.poll() is None:
        pass
    if os.path.exists(dest_comp):
        # os.remove(src)
        print('Conversion complete')
    else:
        print('Unable to convert')


def build_color_configuration_file(src):
    print('Building color file based on max_min from TIF')
    if src:
        src_dir, src_name = os.path.split(src)
        dest = os.path.join(src_dir, os.path.splitext(src_name)[0] + '_colorfile.txt')
        infodata = gdal.Info(src)
        infodata = [inf.strip() for inf in infodata.split('\n')]
        minmax_data = [x for x in infodata if x[0:3] == 'Min']
        if minmax_data:
            minmax = minmax_data[0].split(' ')
            mindepth = float(minmax[0][4:])
            maxdepth = float(minmax[1][4:])
            depthdif = abs(maxdepth) - abs(mindepth)
            with open(dest, 'w+') as colfile:
                # Purp blue cyan green yellow orange red
                bnds = ['0 0 102 255', '0 0 255 255', '0 128 255 255', '0 255 0 255', '255 255 0 255',
                        '255 128 0 255', '255 0 0 255']
                workingdepth = mindepth
                for b in bnds:
                    colfile.write(str(workingdepth) + ' ' + b + '\n')
                    workingdepth -= (depthdif / 6)
                colfile.write('nv 0 0 0 0\n')  # This adds in transparency for no data values
    if os.path.exists(dest):
        print('New color file: {}'.format(dest))
        return dest
    return ''


def return_min_max(src):
    mindepth = 0
    maxdepth = 0
    if src:
        infodata = gdal.Info(src)
        infodata = [inf.strip() for inf in infodata.split('\n')]
        minmax_data = [x for x in infodata if x[0:3] == 'Min']
        if minmax_data:
            minmax = minmax_data[0].split(' ')
            mindepth = float(minmax[0][4:])
            maxdepth = float(minmax[1][4:])
    return mindepth, maxdepth


def build_colorbar_geotiff(src):
    mind, maxd = return_min_max(src)
    colorbar_pth = os.path.join(os.path.dirname(src), 'dem_colorbar.png')
    output_pth = os.path.join(os.path.dirname(src), 'tst.png')

    fig, ax = plt.subplots(figsize=(6, 1))
    fig.subplots_adjust(bottom=0.5)
    cmap = mpl.cm.rainbow
    norm = mpl.colors.Normalize(vmin=float(mind), vmax=float(maxd))
    cb1 = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation='horizontal')
    cb1.set_label('Depth in Meters')
    fig.savefig(colorbar_pth)
    return colorbar_pth


def floatingpoint_to_rgb_dem(src, compress=True):
    print('Generating color relief DEM...')
    gdaldem = find_command('gdaldem')
    if src:
        src_dir, src_name = os.path.split(src)
        dest = os.path.join(src_dir, os.path.splitext(src_name)[0] + '_dem.tif')
        colorfile = build_color_configuration_file(src)
        if colorfile:
            command = ["cmd.exe", "/C", gdaldem, 'color-relief', '-alpha']
            if compress:
                command += ['-co', 'compress=LZW']
            command += ['"' + src + '"', '"' + colorfile + '"', '"' + dest + '"']
            p = subprocess.Popen(" ".join(command))
            while p.poll() is None:
                pass
            if os.path.exists(dest):
                print('New digital elevation map created')
            else:
                print('Unable to run gdaldem.')
        else:
            print('Unable to generate colorfile from tif.')
    else:
        print('gdaldem skipped.  No valid command found')
    return dest


def reproject_raster(src, target_coord, target_zone, compress=True):
    print('Reprojecting raster...')
    gdalwarp = find_command('gdalwarp')
    if src and target_coord and target_zone:

        src_dir, src_name = os.path.split(src)
        dest = os.path.join(src_dir, os.path.splitext(src_name)[0] + '_reproj.tif')

        command = ["cmd.exe", "/C", gdalwarp]
        if compress:
            command += ['-co', 'compress=LZW']
        command += ['-t_srs', '"+proj=utm +zone=' + str(target_zone) + ' + datum=' + str(target_coord) + '"',
                    '-overwrite', '"' + src + '"', '"' + dest + '"']
        p = subprocess.Popen(" ".join(command))
        while p.poll() is None:
            pass
        if os.path.exists(dest):
            print('Reprojected Raster Created')
        else:
            print('Unable to reproject raster using gdalwarp.')
    else:
        print('Reproject raster skipped.  No valid command found')
    return dest


def working_tif_to_drimage_workflow(src, chrt):
    destchrt = reproject_raster(chrt, 'NAD83', '17N')
    destchrt = pallete_to_rgb(destchrt)
    destchrt = compress_raster(destchrt, remove_orig=True)

    cb = build_colorbar_geotiff(src)
    dest = floatingpoint_to_rgb_dem(src)
    dest_extents = get_upperleft_lowerright_extents(src)

    finalimage = r'N:\CSDL\HSTP\HSTP Test Data\Test Data\Charlene\TO\TJ_VDATUM_SHIP_2040_11_dh\Sheet\Working_Surfaces_&_Mosaics\Bathymetry\2016-313\merged_tif_chart.tif'
    overlay_images([destchrt, dest], finalimage, extents_ulx=dest_extents['ulx'],
                   extents_uly=dest_extents['uly'], extents_lrx=dest_extents['lrx'],
                   extents_lry=dest_extents['lry'], colorbar=cb)


class GdalOps():

    def find_command(self, command):
        return find_command(command)

    def find_ogr2ogr(self):
        return find_ogr2ogr()

    def overlay_images(self, img_stack, dest, extents_ulx=None, extents_uly=None, extents_lrx=None, extents_lry=None,
                       colorbar='', compress=True):
        return overlay_images(img_stack, dest, extents_ulx, extents_uly, extents_lrx, extents_lry,
                              colorbar, compress)

    def run_merge(self, src, dest, search_subdirectories=False, snm_calc=False):
        return run_merge(src, dest, search_subdirectories, snm_calc)

    def single_band_mask_from_tif(self, src):
        return single_band_mask_from_tif(src)

    def tif_to_shp(self, src, ogr_format, userdest=None):
        return tif_to_shp(src, ogr_format, userdest)

    def dissolve_shapefile(self, src):
        return dissolve_shapefile(src)

    def pallete_to_rgb(self, src):
        return pallete_to_rgb(src)

    def compress_raster(self, src, remove_orig=False):
        return compress_raster(src, remove_orig)

    def floatingpoint_to_greyscale(self, src, compress=True):
        return floatingpoint_to_greyscale(src, compress)

    def build_color_configuration_file(self, src):
        return build_color_configuration_file(src)

    def return_min_max(self, src):
        return return_min_max(src)

    def build_colorbar_geotiff(self, src):
        return build_colorbar_geotiff(src)

    def add_on_elements(self, src, cb=None):
        return add_on_elements(src, cb)

    def floatingpoint_to_rgb_dem(self, src, compress=True):
        return floatingpoint_to_rgb_dem(src, compress)

    def reproject_raster(self, src, target_coord, target_zone, compress=True):
        return reproject_raster(src, target_coord, target_zone, compress)

    def working_tif_to_drimage_workflow(self, src, chrt):
        return working_tif_to_drimage_workflow(src, chrt)


def simplify_shapefile(src):
    print('**********Running Simplify Shapefile Utility**********')
    wktdata = ''
    dest = ''
    if os.path.exists(src):
        driver = ogr.GetDriverByName("ESRI Shapefile")
        dataSource = driver.Open(src, 1)
        lyr = dataSource.GetLayer(0)
        feature = lyr.GetFeature(0)
        first = ast.literal_eval(feature.ExportToJson())
        shp_geom = shape(first['geometry'])
        print('Removing points within 50 meters of each other, preserving topology...')
        shp_geom_filtered = shp_geom.simplify(10)      # remove points within 10 meters of each other, attempt to preserve topology

        dest = os.path.splitext(src)[0] + '_SIMPLIFIED.shp'
        ds = driver.CreateDataSource(dest)
        layer = ds.CreateLayer('', None, ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
        defn = layer.GetLayerDefn()
        # For the multipolygon case, include each polygon geom
        if hasattr(shp_geom_filtered, 'geoms'):
            for g in shp_geom_filtered.geoms:
                feat = ogr.Feature(defn)
                feat.SetField('id', 123)
                geom = ogr.CreateGeometryFromWkb(g.wkb)
                feat.SetGeometry(geom)
                layer.CreateFeature(feat)
        # Here if just a single polygon
        else:
            feat = ogr.Feature(defn)
            feat.SetField('id', 123)
            geom = ogr.CreateGeometryFromWkb(shp_geom_filtered.wkb)
            feat.SetGeometry(geom)
            layer.CreateFeature(feat)
        wktdata = export_to_wkt(ds, dest)
    if os.path.exists(dest):
        dataSource = None
        driver = None
        lyr = None
        feature = None
        first = None
        print('Shapefile written to {}'.format(dest))
        os.remove(src)
        os.remove(os.path.splitext(src)[0] + '.dbf')
        os.remove(os.path.splitext(src)[0] + '.shx')
        os.remove(os.path.splitext(src)[0] + '.prj')
    else:
        print('Shapefile unsuccessful')
    print('**********Simplify Shapefile Complete**********')
    return wktdata


def return_epsg_from_tif(src):
    # This one took some looking up.  Getting stuff from osr.SpatialReference is not well documented
    #    For future info:
    #   srs.GetAttrValue("AUTHORITY", 0)
    #    Out[5]: 'EPSG'
    #   srs.GetAttrValue("AUTHORITY", 1)
    #    Out[6]: '27700'
    #   srs.GetAttrValue("PRIMEM|AUTHORITY", 1)
    #    Out[12]: '8901'
    #   srs.GetAttrValue("PROJCS|GEOGCS|AUTHORITY", 1)
    #    Out[13]: '4277'

    ds = gdal.Open(src)
    prj = ds.GetProjection()
    srs = osr.SpatialReference(wkt=prj)
    epsg = srs.GetAttrValue("AUTHORITY", 1)
    return epsg


def export_to_wkt(datasrc, src):
    multipoly = ogr.Geometry(ogr.wkbMultiPolygon)
    for lrs in range(0, datasrc.GetLayerCount()):
        tst = datasrc.GetLayer(lrs)
        for feat in range(0, tst.GetFeatureCount()):
            ft = tst.GetFeature(feat)
            multipoly.AddGeometry(ft.GetGeometryRef())
            # out_wkt.append(ft.GetGeometryRef().ExportToWkt())
    dest = os.path.splitext(src)[0] + '.wkt'
    wktdata = multipoly.ExportToWkt()
    with open(dest, 'w+') as fil:
        fil.write(wktdata)
    return wktdata


def get_extents(src):
    ds = gdal.Open(src)
    gt = ds.GetGeoTransform()
    cols = ds.RasterXSize
    rows = ds.RasterYSize

    ext = []
    xarr = [0, cols]
    yarr = [0, rows]

    for px in xarr:
        for py in yarr:
            x = gt[0] + (px * gt[1]) + (py * gt[2])
            y = gt[3] + (px * gt[4]) + (py * gt[5])
            ext.append([x, y])
        yarr.reverse()
    return ext


def get_upperleft_lowerright_extents(src):
    ext = get_extents(src)
    cornerextents = {'ulx': ext[0][0], 'uly': ext[0][1], 'lrx': ext[2][0], 'lry': ext[2][1]}
    return cornerextents


def reproject_coordinates(coords, src_srs, tgt_srs):
    trans_coords = []
    transform = osr.CoordinateTransformation(src_srs, tgt_srs)
    for x, y in coords:
        x, y, z = transform.TransformPoint(x, y)
        trans_coords.append([x, y])
    return trans_coords


def get_geog_extents(src):
    ds = gdal.Open(src)
    extents = get_extents(src)

    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())

    tgt_srs = src_srs.CloneGeogCS()
    geo_ext = reproject_coordinates(extents, src_srs, tgt_srs)
    return geo_ext
