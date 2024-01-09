from HSTB.drivers import kmall
import matplotlib.pyplot as plt
import numpy as np
import glob
from scipy.interpolate import interp1d
import time
import os

# fle = r"C:\Users\samuel.umfress\Desktop\MBES_TestData\0000_20230404_090112.kmall"
fle_dir = r'C:\Users\samuel.umfress\Documents\HSTB\Backscatter\KMALL Calibration Testing\FA100mData'
fles = glob.glob(fle_dir+'\\*.kmall')

start_time = time.time()

def read_kmall_file(fle):
    # This function reads a single .kmall file and returns a data array with reflectivty1, frequency, sector, beam_index,
    # and beam angle. There is also an empty array for for the computed correction values.
    # Also returns a integer cooresponding to the depth mode of the line.
    # Note that limiting the number of pings computed is useful to speed up testing.

    km = kmall.kmall(fle)
    reflectivity1 = []
    reflectivity2 = []
    frequency = []
    sector = []
    first_swath_freqs = []
    beam_index = []
    beam_angle = []
    while not km.eof:
        km.decode_datagram()
        if km.datagram_ident != 'MRZ':
            km.skip_datagram()
        else:
            km.read_datagram()
            depth_mode = km.datagram_data['pingInfo']['depthMode'] # this is gonna get the mode for every ping and only save the last one.
            sector_frequencies = km.datagram_data['txSectorInfo']['centreFreq_Hz']
            sector_numbs = km.datagram_data['sounding']['txSectorNumb']
            frequency.append([sector_frequencies[sector] for sector in sector_numbs])
            if len(frequency) == 1:
                sector.append(sector_numbs)
                first_swath_freqs = sector_frequencies
            elif sector_frequencies == first_swath_freqs:
                sector.append(sector_numbs)
            else:
                sector.append(np.add(sector_numbs, 3))

            ref1_ping = km.datagram_data['sounding']['reflectivity1_dB']
            reflectivity1.append(ref1_ping)
            ref2_ping = km.datagram_data['sounding']['reflectivity2_dB']
            reflectivity2.append(ref2_ping)
            beam_index.append(km.datagram_data['sounding']['soundingIndex'])
            beam_angle.append(km.datagram_data['sounding']['beamAngleReRx_deg'])

        if len(reflectivity1) > 200: #cuts off at 200 pings to run faster for testing
            break

    reflectivity1 = np.array(reflectivity1)
    reflectivity2 = np.array(reflectivity2)
    frequency = np.array(frequency)
    sector = np.array(sector)
    beam_index = np.array(beam_index)
    beam_angle = np.array(beam_angle)

    data = np.zeros((np.shape(reflectivity1)[0], np.shape(reflectivity1)[1], 7))
    data[:,:,0] = reflectivity1
    data[:,:,1] = frequency
    data[:,:,2] = sector
    data[:,:,3] = beam_index
    #data[:,:,4] will be used for the computed corr value
    data[:,:,5] = beam_angle
    data[:,:,6] = reflectivity2
    return data, depth_mode
    # return depth_mode

def create_data_pile(fles):
    # Concatenates all data arrays into a single "data pile" as if it were a single ping. I.e, concatenated along
    # the ping number axis. Also returns the "ping" indices of the start and end of each line and the associated depth mode.

    depth_mode_list = []
    line_ind_start = []
    line_ind_end = []
    for n in range(len(fles)):
        fle = fles[n]
        data, depth_mode = read_kmall_file(fle)
        if n == 0:
            data_pile = data
            line_ind_start.append(0)
            line_ind_end.append(len(data))
        else:
            data_pile = np.concatenate((data_pile, data), axis=0)
            line_ind_start.append(line_ind_end[n-1]+1)
            line_ind_end.append(line_ind_end[n-1]+1+len(data))
        depth_mode_list.append(depth_mode)

    #sorting mode, start/end indices based on mode. This section isn't necesarry if you sort in the corr function.
    # depth_mode_list, line_ind_start, line_ind_end = zip(*sorted(zip(depth_mode_list, line_ind_start, line_ind_end)))
    # depth_mode_list = list(depth_mode_list)
    # line_ind_start = list(line_ind_start)
    # line_ind_end = list(line_ind_end)

    return data_pile, depth_mode_list, line_ind_start, line_ind_end


def compute_ref_value(data_pile):
    # Averages all reflectivity values into a single scalar value.
    # If you want to filter out nadir and near nadir beams, you can do that easily with the beam indices though that's a
    # bit hacky. If you want to do it for real you would need to build in a routine to do so based on beam angle.

    ref1 = data_pile[:, :, 0] #if you wanted to filter out beams (i.e. nadir) you could do so with the first index here.
    ref_val = np.mean(ref1)
    return ref_val

def compute_corr(data_pile, depth_mode_list, line_ind_start, line_ind_end, ref_val, beam_angle_bins):
    corr_pile = np.subtract(data_pile[:,:,0], ref_val) #determining unique corr for every beam in every ping
    data_pile[:,:,4] = corr_pile #integrating that into the open data_pile array.
    depth_mode_set = np.array(list(set(depth_mode_list))) #determine a set of all modes in use.
    depth_mode_list = np.array(depth_mode_list)
    sector_pile = data_pile[:,:,2]
    sectors = int(np.max(sector_pile) - np.min(sector_pile) + 1) #total number of sectors in question

    calib_values = np.empty((sectors, len(beam_angle_bins), len(depth_mode_set))) #initializing an array to put the computer calibration values.
    calib_values[:, :, :] = np.nan #Fill it with nans.

    for i in range(len(depth_mode_set)): #looping through the modes
        depth_mode = depth_mode_set[i]
        mode_ind = np.nonzero(depth_mode_list == depth_mode)
        if np.shape(mode_ind)[1] == 1:
            data = data_pile[line_ind_start[mode_ind[0][0]]:line_ind_end[mode_ind[0][0]], :, :]
            print('For mode ' + str(depth_mode) + ', only 1 line detected. Should there be a reciprocal line?')
        if np.shape(mode_ind)[1] == 2:
            data1 = data_pile[line_ind_start[mode_ind[0][0]]:line_ind_end[mode_ind[0][0]], :, :]
            data2 = data_pile[line_ind_start[mode_ind[0][1]]:line_ind_end[mode_ind[0][1]], :, :]
            data = np.concatenate((data1, data2), axis=0)
        if np.shape(mode_ind)[1] >= 3:
            print('Error: For mode ' + str(depth_mode) + ', three lines were detected. There probably should be 2')
            break
        #the result of the above 13 lines is a snippet of the data pile for a given mode

        reflectivity1 = data[:,:,0]
        sector = data[:,:,2]
        # beam_index = data[:,:,3]
        # corr = data[:,:,4]
        # beam_angle = data[:,:,5]

        sectors = int(np.max(sector) - np.min(sector) + 1)
        num_pings = data.shape[0]
        corr_angle_rel = np.zeros((num_pings, len(beam_angle_bins), sectors))
        corr_angle_rel[:, :, :] = np.nan

        for n in range(sectors): #looping through the sectors
            ind = np.nonzero(data[:,:,2] != n)
            data_sector = np.zeros(data.shape)
            data_sector[:,:,:] = data[:,:,:] #initializing data_sector as np.zeros array avoids using the same reference as data variable.
            data_sector[ind] = np.nan
            beam_angle = data_sector[:,:,5]
            corr = data_sector[:,:,4]
            # corr_angle_rel = np.zeros(num_pings, len(beam_angle_bins), sectors)
            # corr_angle_rel[:,:,:] = np.nan

            for m in range(num_pings): #looping through the pings
                beam_angle_ping = beam_angle[m, :][np.isfinite(beam_angle[m, :])]
                if len(beam_angle_ping) != 0:
                    bin_ind1 = np.nonzero(np.nanmax(beam_angle_ping) > beam_angle_bins)[0][1]
                    bin_ind2 = np.nonzero(np.nanmin(beam_angle_ping) > beam_angle_bins)[0][0]
                    corr_ping = corr[m, :][np.isfinite(corr[m, :])]
                    corr_angle_rel_ping = interp1d(beam_angle_ping, corr_ping)(beam_angle_bins[bin_ind1:bin_ind2])
                    corr_angle_rel[m, bin_ind1:bin_ind2, n] = corr_angle_rel_ping

            calib_values[n, :, i] = np.nanmean(corr_angle_rel[:, :, n], axis=0)

    return data_pile, calib_values

#Execute the Functions

beam_angle_bins = np.arange(-80,80,1)*(-1) #Negative 1 is to align indexing with kmall convention.
data_pile, depth_mode_list, line_ind_start, line_ind_end = create_data_pile(fles)
ref_val = compute_ref_value(data_pile)
data_pile, calib_values = compute_corr(data_pile, depth_mode_list, line_ind_start, line_ind_end, ref_val, beam_angle_bins)


#Plotting

fig_dp, ax_dp = plt.subplots(1,1)
ax_dp.imshow(data_pile[:,:,0], aspect='auto')
for q in range(len(line_ind_end)):
    ind = line_ind_end[q]
    ax_dp.plot(ind*np.ones(data_pile.shape[1]), label=os.path.basename(fles[q]) + ' line end')

ax_dp.legend()

num_modes = calib_values.shape[2] #number of modes
num_sectors = calib_values.shape[0]
fig_corr, ax_corr = plt.subplots(num_modes,1)

for mode in range(num_modes):
    for sector in range(num_sectors):
        ax_corr[mode].plot(beam_angle_bins*(-1), calib_values[sector,:,mode], label='Sector #' + str(sector)) #*(-1) is so plot makes sense and appears as if viewing swath facing fwd.
        ax_corr[mode].set_xlabel('Beam Angle (Degrees)')
        ax_corr[mode].set_ylabel('Correction Value (dB)')
    ax_corr[mode].legend()

ref2_pile = data_pile[:, :, 6]
rough_beam_angle = data_pile[:, :, 5]
ref2_mean = np.mean(ref2_pile, axis=0)
ba_mean = np.mean(rough_beam_angle, axis=0)
fig_ref2, ax_ref2 = plt.subplots(1, 1)
ax_ref2.plot(ba_mean, ref2_mean)

print('Runtime is ', np.round((time.time()-start_time)/60,2), ' minutes.')

plt.show()

print('ITS THEEE END OF THE WORLLDDD AS WE KNOW IT')