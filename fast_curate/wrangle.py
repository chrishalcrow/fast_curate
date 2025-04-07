"""
    Wrangling the data needed to construct the GUI
"""
import numpy as np
from copy import deepcopy
import pandas as pd

import spikeinterface.full as si
from compute import compute_autocorrelograms

class DataForGUI:

    def __init__(self, sorting_analyzer):

        self.merged_units = []
        self.sorting_analyzer = sorting_analyzer

        self.unit_ids = deepcopy(sorting_analyzer.unit_ids)

        self.total_samples = sorting_analyzer.get_num_samples()

        ###############   Get data from sorting analyzer ###############

        random_spikes_ext = sorting_analyzer.get_extension("random_spikes")
        #random_spike_indices = random_spikes_ext.get_data()
        random_spike_indices = si.random_spikes_selection(sorting_analyzer.sorting, max_spikes_per_unit=3000)
        #random_spikes = random_spikes_ext.get_random_spikes()
        spike_vector = sorting_analyzer.sorting.to_spike_vector()
        random_spikes = spike_vector[random_spike_indices]
        self.spikes = si.spike_vector_to_spike_trains([random_spikes], unit_ids = sorting_analyzer.unit_ids)[0]

        print("caching amplitudes...")
        self.amps = {}
        self.locs_x = {}
        self.locs_y = {}

        amps = sorting_analyzer.get_extension("spike_amplitudes").get_data()
        random_amps = amps[random_spike_indices]
        amps = None
        
        locs_y = sorting_analyzer.get_extension("spike_locations").get_data()['y']
        locs_x = sorting_analyzer.get_extension("spike_locations").get_data()['x']
        random_locs_x = locs_x[random_spike_indices]
        random_locs_y = locs_y[random_spike_indices]
        locs = None
        
        for unit_id in sorting_analyzer.unit_ids:
            self.amps[unit_id] = []
            self.locs_x[unit_id] = []
            self.locs_y[unit_id] = []

        for spike, amp, loc_x, loc_y in zip(random_spikes, random_amps, random_locs_x, random_locs_y):
            unit_id = spike['unit_index']
            self.amps[unit_id].append(amp)
            self.locs_x[unit_id].append(loc_x)
            self.locs_y[unit_id].append(loc_y)

        print("caching spikes...")
        self.template_similarity = sorting_analyzer.get_extension(
            "template_similarity").get_data()

        self.sparsity_mask = sorting_analyzer.sparsity.mask
        self.channel_locations = sorting_analyzer.get_channel_locations()
        self.unit_locations = sorting_analyzer.get_extension(
            "unit_locations").get_data()[:, 0:2]
        self.unit_xmin = min(self.channel_locations[:, 0])
        self.unit_xmax = max(self.channel_locations[:, 0])
        self.unit_ymin = min(self.channel_locations[:, 1])
        self.unit_ymax = max(self.channel_locations[:, 1])

        sparsity_for_pca = si.compute_sparsity(sorting_analyzer, radius_um=50)

        self.unit_id_to_channel_indices = sparsity_for_pca.unit_id_to_channel_indices
        self.waveforms = sorting_analyzer.get_extension("waveforms")

        max_channels = sorting_analyzer.channel_ids_to_indices(
            si.get_template_extremum_channel(sorting_analyzer).values()
        )
        templates_data = sorting_analyzer.get_extension("templates").get_data()
        self.templates = {unit_id_1:
                          templates_data[unit_id_1, :, max_channels[sorting_analyzer.sorting.id_to_index(
                              unit_id_1)]]
                          for unit_id_1 in sorting_analyzer.unit_ids}
        self.all_templates = {unit_id_1:
                              templates_data[unit_id_1, :, self.sparsity_mask[sorting_analyzer.sorting.id_to_index(
                                  unit_id_1)]]
                              for unit_id_1 in sorting_analyzer.unit_ids}

        quality_metrics = sorting_analyzer.get_extension(
            "quality_metrics").get_data().astype('float')
        template_metrics = sorting_analyzer.get_extension(
            "template_metrics").get_data().astype('float')

        self.metrics = pd.concat([quality_metrics, template_metrics], axis=1)
        print(self.metrics)

        all_correlograms, bins = sorting_analyzer.get_extension(
            "correlograms").get_data()
        self.correlograms = all_correlograms
        self.correlogram_bins = bins

        wide_correlograms = []
        for unit_id in sorting_analyzer.unit_ids:
            one_wide, bins = compute_autocorrelograms(self.spikes[unit_id], window_ms=500, bin_ms=5, fs=sorting_analyzer.sampling_frequency)
            wide_correlograms.append(one_wide)
        self.wide_correlograms = wide_correlograms
        self.wide_bins = bins
    
    def get_unit_data(self, unit_index):

        unit_data = {}

        unit_data['amps'] = self.amps[unit_index]
        unit_data['locs_x'] = np.nan_to_num(self.locs_x[unit_index])
        unit_data['locs_y'] = np.nan_to_num(self.locs_y[unit_index])

        unit_data['spikes'] = self.spikes[unit_index]

        unit_data['template'] = self.templates[unit_index]

        unit_data['correlograms'] = self.correlograms[unit_index][unit_index]
        unit_data['correlogram_bins'] = self.correlogram_bins

        unit_data['wide_correlograms'] = self.wide_correlograms[unit_index]
        unit_data['wide_bins'] = self.wide_bins

        unit_data['unit_location'] = self.unit_locations[unit_index]
        unit_data['binned_spikes'], _ = np.histogram(unit_data['spikes'], bins=20)
        unit_data['all_templates'] = self.all_templates[unit_index]

        unit_data['channel_locations'] = self.channel_locations

        return unit_data

