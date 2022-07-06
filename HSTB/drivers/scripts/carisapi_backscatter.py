import os

from HSTB.drivers.carisapi import CarisAPI

# project information that is required for you to enter here
hdcs_folder = r'D:\charlene_dest\OPR-PXXX-FA-17\HXXXXX\Processed\Sonar_Data\HDCS_Data'
sheetname = 'HXXXXX_MB'
output_epsg = '26910'

# all of the usual caris output will go to the log file
logfile = r"D:\charlene_dest\OPR-PXXX-FA-17\HXXXXX\newlogfile.txt"
# this is the beampatternfile that will be created
new_beampattern_file = r"D:\charlene_dest\OPR-PXXX-FA-17\HXXXXX\my_test_bbp.bbp"
# this is the backscatter mosaic that will be created
output_mosaic = r"D:\charlene_dest\OPR-PXXX-FA-17\HXXXXX\my_test.csar"
# this is the resolution of the created backscatter mosaic
mosaic_resolution = '4.0m'

cpi = CarisAPI(hdcs_folder=hdcs_folder, sheet_name=sheetname, bench=False, logger=logfile)
# you currently have to do the license check for the version logic to work later on
valid, licoutput = cpi.caris_hips_license_check()

if valid:
    # get the sheet extents so the gridding engine understands where the corners of the grid are
    _, lowx, lowy, highx, highy = cpi.daynum_extents(output_epsg)

    # this is currently required (creating the beam pattern file) although I think you can just let create_mosaic do it technically
    print('Creating Beam Pattern File...')
    cpi.create_beampattern('SIPS_BACKSCATTER', new_beampattern_file)
    if os.path.exists(new_beampattern_file):
        print(f'Beam Pattern file created - {new_beampattern_file}')
    else:
        print('ERROR: Failed to create Beam Pattern File, see log for details')

    # create a new backscatter mosaic, if you have a later version of caris, will automatically do the WMA_AREA_AVG routine
    print('Running Backscatter Processing...')
    cpi.create_mosaic(output_epsg, lowx, lowy, highx, highy, mosaic_resolution, new_beampattern_file, 'SIPS_BACKSCATTER',
                      output_mosaic, update=False)
    if os.path.exists(output_mosaic):
        print(f'CSAR created - {output_mosaic}')
    else:
        print('ERROR: Failed to create CSAR, see log for details')
else:
    print('You do not currently have a valid caris license, skipping backscatter processing.')