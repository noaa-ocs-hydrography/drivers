# -*- coding: utf-8 -*-
"""
flierfinder2bag.py

Created on Wed Sep 12 12:51:42 2018

@author: grice

V 0.0.3  Last updated 20180914

This method contians a series of methods for updating bags based on the output
of flier finder.  A feature file may be used to limit which fliers are removed.
"""

import sys, os
from shutil import copyfile
from glob import glob
import csv
from osgeo import gdal, osr
import numpy as np
import matplotlib.pyplot as plt
import tables as tbl
try:
    from hyo2 import bag as baglib
    have_baglib = True
except:
    have_baglib = False
#import parse_bag_meta as pbm

plt.ion()

__doc__ = 'flierfinder2bag'
__version__ = '0.0.3'

default_feat_types = ['OBSTRN', 'UWTROC', 'WRECKS']


def process_all_files(flier_path,
                      bag_path='',
                      feature_path='',
                      buffer_size=16,
                      feat_types=None,
                      output_name_update='roombaed',
                      output_path='',
                      fix_trackinglist=True):
    """
    Given a path or several paths, updated all bag by removing all fliers
    that do not correlate with features.  This is the primary method for this
    module.
    
    args:
        
        flier_path : The directory path for the '*soundings.000' files.
    
    kwargs:
        
        bag_path : The directory path for the bag files corresponding to the
                   flier files.  Default is an empty string (''), which causes
                   the bag_path to default to the flier_path.
                   
        feature_path : The directory path for the bag files corresponding to 
                       the flier files.  Default is an empty string (''), which
                       causes the bag_path to default to the flier_path.
        
        buffer_size : The radius around fliers to look for correlated features.
                      The default is 16, and is meters assuming the bag file
                      is projected in meters.
        
        feat_types : The s57 layers to use in the feature file to look for
                     features.  Default layers include 'OBSTRN', 'UWTROC', 
                     and 'WRECKS'.
                     
        output_name_update : A string to insert into the end of the file base
                             name to differentiate it from the original file.
                             The default is 'roombaed'.
                             
        output_path : A directory for where to put the created files.  Default
                      is an empty string (''), which causes the output_path
                      to default to the bag_path.
                      
        fix_tracklinglist : A boolean that causes the bag trackling list to be
                            examined for sign.  Old bag files written in CARIS
                            HIPS were written as depths rather than elevation,
                            causing the sign to the incorrect.  This method
                            reverses the sign of the tracking list if the sign
                            is determined to be incorrect.  See the method
                            'fix_bag_trackinglist' for more details. Default
                            is True.
        
    """
    if feat_types is None:
        feat_types = default_feat_types

    # print('Passed path to fliers: %s' % flier_path)

    run_list, report_list = find_all_files(flier_path, bag_path, feature_path)
    numfiles = len(run_list)

    print('Processing ' + str(numfiles) + ' flier finder files, skipping ' +
          str(len(report_list)) + ' files.')
    for n, run in enumerate(run_list):
        flier_file, bag_file, feature_file = run
        path, f = os.path.split(flier_file)
        print(str(n + 1) + '/' + str(numfiles) + ': ' + f)
        fliers, fliers_file = open_flier_finder_output(flier_file)
        bag_wkt, res, xmin, ymin = get_bag_info(bag_file)
        feature_ds = open_feature_file(feature_file)
        position_list = find_uncorrelated_features(feature_ds,
                                                   fliers,
                                                   bag_wkt,
                                                   buffer=buffer_size,
                                                   feat_types=feat_types)
        bag_index_array = convert_coordinates_to_index(position_list,
                                                       res, xmin, ymin)
        update_new_bag(bag_file,
                       bag_index_array,
                       name_update=output_name_update,
                       new_path=output_path,
                       fix_trackinglist=fix_trackinglist)
    if len(report_list) > 0:
        print('These files were not found to have the required correlating files:')
        print(report_list)
        
def summarize_all_files(flier_path,
                        bag_path='',
                        summary_file_name='',
                        output_path='',
                        search_subdir = True):
    """
    Given a path or several paths, summarize the fliers for all bags.
    
    args:
        
        flier_path : The directory path for the '*soundings.000' files.
    
    kwargs:
        
        bag_path : The directory path for the bag files corresponding to the
                   flier files.  Default is an empty string (''), which causes
                   the bag_path to default to the flier_path.
                     
        summary_file_name : If a name is provided the summary is writen to this
                            file.  If no name is provided the summary is only
                            printed to the screen.
                             
        output_path : A directory for where to put the created files.  Default
                      is an empty string (''), which causes the output_path
                      to default to the bag_path.
        
    """
    run_list, report_list = find_all_files(flier_path, 
                                           bag_path, 
                                           find_feature_file=False,
                                           search_subdir = search_subdir)
    numfiles = len(run_list)
    summary = []
    print('Processing ' + str(numfiles) + ' flier finder files, skipping ' +
          str(len(report_list)) + ' files.')
    for n, run in enumerate(run_list):
        flier_file, bag_file, feature_file = run
        path, f = os.path.split(flier_file)
        print(str(n + 1) + '/' + str(numfiles) + ': ' + f)
        file_summary = summarize_flier_types(flier_file, bag_file)
        p, b = os.path.split(bag_file)
        file_summary['bag'] = b
        summary.append(file_summary)
    if len(report_list) > 0:
        print('These files were not found to have the required correlating files:')
        print(report_list)
    for n in summary:
        print(n)
    if len(summary_file_name) > 0:
        if len(output_path) > 0:
            csvfilename = os.path.join(output_path, 
                                       summary_file_name)
        else:
            csvfilename = summary_file_name
            
        write_out_summary(summary, csvfilename)
        

def find_all_files(flier_path,
                   bag_path='', 
                   feature_path='',
                   find_feature_file = True,
                   search_subdir = True):
    """
    Given a path or several paths, return a list for the files required
    to remove the bag nodes containing fliers that do not correlate with
    features in the feature file.  A second list is also returned containing
    a list of all the flier files that did not have the needed correlating
    files.
    
    Flier files are found by searching for files with the name 
    '*.soundings.000'.  Corrisponding bag files are found by searching for
    files with the same prefix (before the first '.' in the flier file name).
    Feature files are found by searching all files with the extension 
    '_CS.000' or '_CU.000' for the same registry number as the 
    """
    corr_files = []
    uncorr_files = []
    if search_subdir:
        subdir = '*/'
    else:
        subdir = ''
    if bag_path == '':
        bag_path = flier_path
    if feature_path == '':
        feature_path = flier_path
    flier_search = os.path.join(flier_path, subdir + '*.soundings.000')
    print("Search path for fliers files: {}".format(flier_search))
    flier_list = glob(flier_search)
    for f in flier_list:
        # find the bag file
        p, fname = os.path.split(f)
        root = fname.split('.', maxsplit=1)[0]
        bag_search = os.path.join(bag_path, subdir + root + '*.bag')
        bag_list = glob(bag_search)
        if len(bag_list) > 1:
            print('Several matching bags found to ' +
                  fname + '.  Taking the first one.')
        if len(bag_list) > 0:
            bagname = bag_list[0]
        else:
            bagname = None
        if find_feature_file:
            # find the feature file name
            regnum = fname.split('_', maxsplit=1)[0]
            CS_search = os.path.join(feature_path, subdir + '*' + str(regnum) + '*_CS.000')
            CS_list = glob(CS_search)
            CU_search = os.path.join(feature_path, subdir + '*' + str(regnum) + '*_CU.000')
            CU_list = glob(CU_search)
            feature_list = CS_list + CU_list
            if len(feature_list) > 1:
                print('Several matching bags found to ' + CS_search + ' or ' +
                      CU_search + '.  Taking the first one.')
            if len(feature_list) > 0:
                featurename = feature_list[0]
            else:
                featurename = None
        else:
            featurename = ''
        if bagname is not None and featurename is not None:
            corr_files.append([f, bagname, featurename])
        else:
            uncorr_files.append(f)
    return corr_files, uncorr_files

def remove_fliers_from_bag(flier_path,
                           bag_path,
                           output_name_update='roombaed',
                           output_path='',
                           fix_trackinglist=True,
                           only_deep = True):
    """
    Create a new bag but with nodes associated with fliers removed.
    
    args:
        
        flier_path : The  path for the '*soundings.000' file.
        
        bag_path : The path for the bag file.
    
    kwargs:
        
        output_name_update : A string to insert into the end of the file base
                             name to differentiate it from the original file.
                             The default is 'roombaed'.
                             
        output_path : A directory for where to put the created files.  Default
                      is an empty string (''), which causes the output_path
                      to default to the bag_path.
                      
        fix_tracklinglist : A boolean that causes the bag trackling list to be
                            examined for sign.  Old bag files written in CARIS
                            HIPS were written as depths rather than elevation,
                            causing the sign to the incorrect.  This method
                            reverses the sign of the tracking list if the sign
                            is determined to be incorrect.  See the method
                            'fix_bag_trackinglist' for more details. Default
                            is True.
                            
        only_deep : A boolean indicating to only remove the deep fliers.
                    Default is True.
        
    """

    fliers, fliers_file = open_flier_finder_output(flier_path)
    try:
        bag_wkt, res, xmin, ymin = get_bag_info(bag_path)
        position_list = transform_feature_reference_system(fliers, bag_wkt)
        bag_index_array = convert_coordinates_to_index(position_list,
                                                       res, xmin, ymin)
        total_count = len(bag_index_array)
        if only_deep:
            deep_index_array, shoal_index_array, unknown = find_deep_fliers(bag_path, bag_index_array)
            deep_count = len(deep_index_array)
            shoal_count = len(shoal_index_array)
            status = f'{shoal_count} shoal fliers of {total_count} fliers total.  Removing {deep_count} fliers.'
            bag_index_array = deep_index_array
        else:
            status = f'Removing {total_count} fliers'
        update_new_bag(bag_path,
                       bag_index_array,
                       name_update=output_name_update,
                       new_path=output_path,
                       fix_trackinglist=fix_trackinglist)
    except ValueError:
        status = 'BAG failed to open'
    except:
        status = 'Unknown error occured' + sys.exc_info()[0]
    finally:
        print(status)
        return status
    
def summarize_flier_types(flier_path, bag_path):
    """
    Summarize the fliers found by flier finder.
    
    args:
        
        flier_path : The  path for the '*soundings.000' file.
        
        bag_path : The path for the bag file.
            
    """
    fliers, fliers_file = open_flier_finder_output(flier_path)
    flier_flags = get_fliers_flags(fliers)
    total_count = len(flier_flags)
    summary = {}
    summary['total_count'] = total_count
    # get a count on each flag type
    flags = flier_flags.astype(np.int)
    f_types = set(flags)
    for n in f_types:
        idx = np.nonzero(n == flags)[0]
        summary[n] = len(idx)
    try:
        bag_wkt, res, xmin, ymin = get_bag_info(bag_path)
        position_list = transform_feature_reference_system(fliers, bag_wkt)
        bag_index_array = convert_coordinates_to_index(position_list,
                                                       res, xmin, ymin)
        total_count = len(bag_index_array)
        deep_index_array, shoal_index_array, unknown = find_deep_fliers(bag_path, bag_index_array)
        summary['shoal_count'] = len(shoal_index_array)
    except ValueError:
        print('BAG failed to open')
        summary['shoal_count'] = -1
    finally:
        return summary

def get_bag_info(bagfilename):
    """
    Given a bag file name (including the path), open and get the spatial
    reference information, the resolution, and the southwest corner and return 
    this information.
    
    The spatial reference information is returned as wkt.
    """
    bag_wkt = None
    # dimensions from the elevation layer since not found in geotransform
    with tbl.open_file(bagfilename, 'r') as bagfile:
        elev = bagfile.root.BAG_root.elevation
        numrows, numcols = elev.shape
    bag_gdal = gdal.Open(bagfilename)
    # georef information from GDAL since working the bag xml is a pain
    if bag_gdal is not None:
        bag_georef = bag_gdal.GetGeoTransform()
        bag_wkt = bag_gdal.GetProjection()
        resx, resy = bag_georef[1], bag_georef[5]
        # gdal is cell centered, not node centered, so 1/2 cell adjustment
        xmin = bag_georef[0] + 0.5 * resx
        ymin = bag_georef[3] + numrows * resy - 0.5 * resy
    if have_baglib:
        bagfile = baglib.BAGFile(bagfilename)
        metadata = baglib.meta.Meta(bagfile.metadata())
        resx, resy = metadata.res_x, metadata.res_y
        xmin, ymin = metadata.sw
        # print("BAG metadata -> res: %.2f, x min: %.2f, y min: %.2f" % (resx, xmin, ymin))
    if bag_wkt is not None:
        return bag_wkt, resx, xmin, ymin
    else:
        raise ValueError('Bag failed to open with GDAL.')
        
#def hack_bag_xml(bagfilename):
#    """
#    Get the bag georef info from the bag xml.
#    """
#    with tbl.open_file(bagfilename, 'r') as bag:
#        meta = bag.root.BAG_root.metadata.read()
#        xml = meta.tostring().decode()
#    if xml[-1] == '\x00':
#        parser = pbm.Meta(xml[:-1])
#    else:
#        parser = pbm.Meta(xml)
#    return parser
    
def open_flier_finder_output(flier_finder_s57_file):
    """
    Provided a flier finder s57 sounding file name, return the GDAL layer
    containing all the sounding features and the file reference.
    
    The file reference is returned to avoid closing the file (by going out
    of scope.)  This reference must exist for as long as the layer is to be
    used.
    """
    # open the flier file
    fliers = gdal.OpenEx(flier_finder_s57_file, gdal.OF_VECTOR)
    if fliers is None:
        print("Flier file open failed.\n")
        sys.exit(1)
    flyr = fliers.GetLayerByName('SOUNDG')
    flyr.ResetReading()
    return flyr, fliers


def open_feature_file(feature_filename):
    """
    Provided the feature file, open the file and return the file object.
    """
    # open the feature file
    features_ds = gdal.OpenEx(feature_filename, gdal.OF_VECTOR)
    if features_ds is None:
        print("Feature file open failed.\n")
        sys.exit(1)
    return features_ds


def find_uncorrelated_features(feature_file, fliers, bag_wkt, buffer=16,
                               feat_types=None):
    """
    Provided a GDAL feature file and a GDAL layer containing the fliers as
    GDAL features (these are assumed to be single point polygons), return
    all of the positions of the non-correlated items in the provided spatial
    reference system. The spatial reference system must be provided as WKT.
    
    A correlation between the feature file and flier is within the provided 
    "buffer" value (default = 16).  Units for the buffer are the same as the
    WKT projection.
    
    The spatial reference system of the flier layer is assumed to be the 
    
    The feature file layer types to be used for correlation can also be
    provided as a list of strings.  The default layer types include 'OBSTRN', 
    'UWTROC' and 'WRECKS'.
    """
    if feat_types is None:
        feat_types = default_feat_types

    # get a transformation to utmthe bag reference system
    dest_srs = osr.SpatialReference()
    dest_srs.ImportFromWkt(bag_wkt)
    # get the number of feature file layers to work with
    numlyrs = feature_file.GetLayerCount()
    # get the spatial info for the fliers
    flier_srs = fliers.GetSpatialRef()
    flier_trans = osr.CoordinateTransformation(flier_srs, dest_srs)
    # the fliers that are not correlated with features
    corr_idx = []
    # cycle through all the fliers
    for n, k in enumerate(fliers):
        g = k.geometry()
        if g.GetGeometryCount() > 1:
            print('multipoint flier found: ' + str(n))
        else:
            flier = g.GetGeometryRef(0)
            flier.Transform(flier_trans)
            # sort through all the feature layers
            for m in range(numlyrs):
                slyr = feature_file.GetLayerByIndex(m)
                sname = slyr.GetName()
                # make sure this is a feature layer type we want to work with
                if sname in feat_types:
                    slyr.ResetReading()
                    feat_srs = slyr.GetSpatialRef()
                    feat_trans = osr.CoordinateTransformation(feat_srs, dest_srs)
                    # work through all the features in the layer
                    for f in slyr:
                        feat = f.GetGeometryRef()
                        # project the point so we can work in meters
                        feat.Transform(feat_trans)
                        dist = feat.Distance(flier)
                        if dist < buffer:
                            corr_idx.append(n)
    fliers.ResetReading()
    uncor_list = []
    for n, k in enumerate(fliers):
        if n not in corr_idx:
            g = k.geometry()
            flier = g.GetGeometryRef(0)
            flier.Transform(flier_trans)
            uncor_list.append(flier.GetPoint())
    return uncor_list

def transform_feature_reference_system(fliers, bag_wkt):
    """
    Provided a GDAL layer containing the fliers as GDAL features (these are 
    assumed to be single point polygons), return all of the positions of the 
    items in the provided spatial reference system. The spatial reference
    system must be provided as WKT.
    """
    # get a transformation to utmthe bag reference system
    dest_srs = osr.SpatialReference()
    dest_srs.ImportFromWkt(bag_wkt)
    # get the spatial info for the fliers
    flier_srs = fliers.GetSpatialRef()
    flier_trans = osr.CoordinateTransformation(flier_srs, dest_srs)
    # cycle through all the fliers
    flier_pos = []
    fliers.ResetReading()
    for n, k in enumerate(fliers):
        g = k.geometry()
        if g.GetGeometryCount() > 1:
            print('multipoint flier found: ' + str(n))
        else:
            flier = g.GetGeometryRef(0)
            flier.Transform(flier_trans)
            flier_pos.append(flier.GetPoint())
    return flier_pos

def convert_coordinates_to_index(position_list, res, xmin, ymin):
    """
    Provided a list of positions in the same spatial reference system as the
    assoiated array, with the array's resolution, minimum x, and minimum y,
    return an array of indexes for those positions.
    
    The position is assumed to be offset in the positive direction by 1/2 of
    the cel size.
    """
    # given a list of points to remove, get the index for the bag
    index_array = np.array(position_list)
    index_array[:, 0] = np.round((index_array[:, 0] - xmin) / res - 0.5)
    index_array[:, 1] = np.round((index_array[:, 1] - ymin) / res - 0.5)
    index_array = index_array.astype(np.int)
    return index_array

def find_deep_fliers(bagfilename, node_index):
    """
    Reduce the provided list of indicies to only the deep fliers by comparing
    the index to the surounding nodes.
    """
    deep_index = []
    shoal_index = []
    gok_index = []
    with tbl.open_file(bagfilename, 'r') as bag:
        elev = bag.root.BAG_root.elevation
        numrows, numcols = elev.shape
        for p in node_index:
            row = p[1]
            col = p[0]
            # set the area to check for comparison of depth looking for edges
            loc = [1,1]
            if row > 0:
                ubuf = row - 1
            else:
                ubuf = row
                loc[0] = 0
            if row < numrows - 1:
                dbuf = row + 2
            else:
                dbuf = row + 1
            if col > 0:
                lbuf = col - 1
            else:
                lbuf = col
                loc[1] = 0
            if col < numcols - 1:
                rbuf = col + 2
            else:
                rbuf = col + 1
            # build the array to compare to the point
            area = elev[ubuf:dbuf,lbuf:rbuf]
            val = elev[row,col]
            m = area == 1000000  # testing for the no data value
            m[loc[0],loc[1]] = True  # remove the point we are comparing
            comp = np.ma.masked_array(area, m)
            # compare and save index if deeper than comparison area
            if np.all(comp > val):
                deep_index.append(p)
            elif np.all(comp < val):
                shoal_index.append(p)
            else:
                gok_index.append(p)
        deep_index = np.asarray(deep_index)
        shoal_index = np.asarray(shoal_index)
        gok_index = np.asarray(gok_index)
        return deep_index, shoal_index, gok_index
    
def get_fliers_flags(fliers):
    """
    Return an array of the flier flags as inserted into the depth flier finder.
    """
    fliers.ResetReading()
    numf = fliers.GetFeatureCount()
    flags = np.zeros(numf)
    for n, f in enumerate(fliers):
        g = f.geometry()
        h = g.GetGeometryRef(0) # soundings are multipoint, but there is only 1
        flags[n] = h.GetZ()
    return flags
        
def update_new_bag(bagfilename, node_index, name_update='roombaed',
                   new_path='', fix_trackinglist=True):
    """
    Given a bag file name (including the path), copy the file to the new path
    and update the name with name_update.  This new file has the nodes listed
    in node_index updated with the bag no data value (1,000,000).
    """
    # setup the name
    path, filename = os.path.split(bagfilename)
    root, ext = os.path.splitext(filename)
    if len(new_path) == 0:
        new_path = path
    newbagname = os.path.join(new_path, root + '_' + name_update + '.bag')
    # copy the file
    copyfile(bagfilename, newbagname)
    # fix the trackling list
    if fix_trackinglist:
        fix_bag_trackinglist(newbagname)
    # replace the nodes in the array
    with tbl.open_file(newbagname, 'r+') as bagout:
        elev_array = bagout.root.BAG_root.elevation
        uncert_array = bagout.root.BAG_root.uncertainty
        tracklist = bagout.root.BAG_root.tracking_list
        for p in node_index:
            t = tracklist.row
            t['row'] = p[1]
            t['col'] = p[0]
            t['depth'] = elev_array[p[1], p[0]]
            t['uncertainty'] = uncert_array[p[1], p[0]]
            t['track_code'] = 9
            t['list_series'] = 9
            t.append()
            elev_array[p[1], p[0]] = 1000000
            uncert_array[p[1], p[0]] = 1000000
        bagout.flush()
    return newbagname

def fix_bag_trackinglist(bagfilename, verbose=True):
    """
    Given a bag filename, fix an old bag file written in CARIS HIPS that have
    the elevation in the tracking list written with the wrong sign (likely due 
    to being a depth rather than elevation).
    
    If the tracking list values (which were the original depths) are greater
    than all grid elevations (which contains the designated values) the
    trackling list values are assumed to be reversed.  The assumption is that
    all designations were for shoaler depths.
    """
    with tbl.open_file(bagfilename, mode='r+') as bagfile:
        tracklist = bagfile.root.BAG_root.tracking_list.read()
        depths = tracklist['depth']
        if len(depths) > 0:
            row = tracklist['row']
            col = tracklist['col']
            elev = bagfile.root.BAG_root.elevation
            designated = elev[row, col]
            if np.all(depths > designated):
                depths *= -1
                bagfile.root.BAG_root.tracking_list.modify_column(colname='depth', column=depths)
                bagfile.flush()
                print('Updated trackinglist sign for ' + bagfilename)
                
def write_out_summary(summary, csvfilename):
    """
    Write the provided dictionary to the provided filename.
    """
    fieldnames = ['bag','total_count','shoal_count',1,2,3,4,5,6]
    with open(csvfilename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames = fieldnames)
        writer.writeheader()
        for row in summary:
            writer.writerow(row)

def main():
    print("Running %s v.%s" % (__doc__, __version__))

    cwd = os.getcwd()
    # look in the subdirectories
    cwd = os.path.join(cwd, '*')
    process_all_files(cwd)


if __name__ == "__main__":
    main()
