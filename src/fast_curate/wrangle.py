"""
    Wrangling the data needed to construct the GUI
"""
import numpy as np
from copy import deepcopy
import pandas as pd

import spikeinterface.full as si
from compute import compute_autocorrelograms

def get_scaled_templates(templates, std_templates, percentiles):

    scaled_templates = {}
    scaled_stds = {}      
    scaled_perc = {}
    for (unit_id, template_data), std_template, perc_template in zip(templates.items(), std_templates.values(), percentiles.values()):
        #min_value = np.min(template_data)
        abs_max_value = np.max(abs(template_data))

        scaled_templates[unit_id] = template_data/abs_max_value
        scaled_stds[unit_id] = std_template/abs_max_value
        scaled_perc[unit_id] = perc_template/abs_max_value

    return scaled_templates, scaled_stds, scaled_perc

class DataForGUI:

    def __init__(self, sorting_analyzer, have_extension):
        """Extract data from the sorting_analyzer for the curation, and cache in `DataForGUI` object."""

        print("Wrangling, caching and computing with data...")

        self.merged_units = []
        self.sorting_analyzer = sorting_analyzer
        self.unit_ids = deepcopy(sorting_analyzer.unit_ids)
        self.total_samples = sorting_analyzer.get_num_samples()

        ###############   Get data from sorting analyzer ###############

        random_spike_indices = si.random_spikes_selection(sorting_analyzer.sorting, max_spikes_per_unit=3000)
        spike_vector = sorting_analyzer.sorting.to_spike_vector()
        random_spikes = spike_vector[random_spike_indices]
        self.spikes = si.spike_vector_to_spike_trains([random_spikes], unit_ids = sorting_analyzer.unit_ids)[0]

        self.amps = {}
        if have_extension['spike_amplitudes']:
            amps = sorting_analyzer.get_extension("spike_amplitudes").get_data()
            random_amps = amps[random_spike_indices]

            for unit_id in sorting_analyzer.unit_ids:
                self.amps[unit_id] = []
            
            for spike, amp in zip(random_spikes, random_amps):
                unit_id = sorting_analyzer.unit_ids[spike['unit_index']]
                self.amps[unit_id].append(amp)
        amps = None

        self.locs_x = {}
        self.locs_y = {}
        if have_extension['spike_locations']:
            locs_y = sorting_analyzer.get_extension("spike_locations").get_data()['y']
            locs_x = sorting_analyzer.get_extension("spike_locations").get_data()['x']
            random_locs_x = locs_x[random_spike_indices]
            random_locs_y = locs_y[random_spike_indices]
            
            for unit_id in sorting_analyzer.unit_ids:
                self.locs_x[unit_id] = []
                self.locs_y[unit_id] = []

            for spike, loc_x, loc_y in zip(random_spikes, random_locs_x, random_locs_y):
                unit_id = sorting_analyzer.unit_ids[spike['unit_index']]
                self.locs_x[unit_id].append(loc_x)
                self.locs_y[unit_id].append(loc_y)
        
        self.channel_locations = sorting_analyzer.get_channel_locations()
        self.unit_xmin = min(self.channel_locations[:, 0])
        self.unit_xmax = max(self.channel_locations[:, 0])
        self.unit_ymin = min(self.channel_locations[:, 1])
        self.unit_ymax = max(self.channel_locations[:, 1])
        if have_extension["unit_locations"]:
            self.unit_locations = sorting_analyzer.get_extension(
                "unit_locations").get_data()[:, 0:2]
        
        if have_extension['templates']:
            self.sparsity_mask = sorting_analyzer.sparsity.mask
            max_channels = sorting_analyzer.channel_ids_to_indices(
                si.get_template_extremum_channel(sorting_analyzer).values()
            )
            templates_data = sorting_analyzer.get_extension("templates").get_data()
            std_data = sorting_analyzer.get_extension("templates").get_data("std")
            percentile_data = sorting_analyzer.get_extension("templates").get_data("pencentile_99")
            self.templates = {unit_id_1:
                          templates_data[unit_index_1, :, max_channels[unit_index_1]]
                          for unit_index_1, unit_id_1 in enumerate(sorting_analyzer.unit_ids)}
            all_templates = {unit_id_1:
                              templates_data[unit_index_1, :, self.sparsity_mask[unit_index_1]]
                              for unit_index_1, unit_id_1 in enumerate(sorting_analyzer.unit_ids)}
            std_templates = {unit_id_1:
                              std_data[unit_index_1, :, self.sparsity_mask[unit_index_1]]
                              for unit_index_1, unit_id_1 in enumerate(sorting_analyzer.unit_ids)}
            perc_templates = {unit_id_1:
                              percentile_data[unit_index_1, :, self.sparsity_mask[unit_index_1]]
                              for unit_index_1, unit_id_1 in enumerate(sorting_analyzer.unit_ids)}
            self.scaled_templates, self.scaled_stds, self.scaled_perc = get_scaled_templates(all_templates, std_templates, perc_templates)
        else:
            self.templates = {}
            self.all_templates = {}
        
        if have_extension["correlograms"]:
            all_correlograms, bins = sorting_analyzer.get_extension(
                "correlograms").get_data()
        else:
            all_correlograms = {}
            for unit_id in sorting_analyzer.unit_ids:
                one_corr, bins = compute_autocorrelograms(self.spikes[unit_id], window_ms=50, bin_ms=2, fs=sorting_analyzer.sampling_frequency)
                all_correlograms[unit_id] = {}
                all_correlograms[unit_id][unit_id] = one_corr
        self.correlograms = all_correlograms
        self.correlogram_bins = bins

        wide_correlograms = []
        for unit_id in sorting_analyzer.unit_ids:
            one_wide, bins = compute_autocorrelograms(self.spikes[unit_id], window_ms=500, bin_ms=5, fs=sorting_analyzer.sampling_frequency)
            wide_correlograms.append(one_wide)
        self.wide_correlograms = wide_correlograms
        self.wide_bins = bins
 
        quality_metrics = pd.DataFrame()
        if have_extension['quality_metrics']:
            quality_metrics = sorting_analyzer.get_extension(
                "quality_metrics").get_data().astype('float')
        
        template_metrics = pd.DataFrame()
        if have_extension['template_metrics']:
            template_metrics = sorting_analyzer.get_extension(
                "template_metrics").get_data().astype('float')

        self.metrics = pd.concat([quality_metrics, template_metrics], axis=1)

    
    def get_unit_data(self, unit_index):
        """For a given unit, extract unit data from all data."""

        unit_data = {}

        unit_data['amps'] = self.amps.get(unit_index)
        unit_data['locs_x'] = np.nan_to_num(self.locs_x.get(unit_index))
        unit_data['locs_y'] = np.nan_to_num(self.locs_y.get(unit_index))

        unit_data['spikes'] = self.spikes[unit_index]

        unit_data['template'] = self.templates.get(unit_index)

        unit_data['correlograms'] = self.correlograms[unit_index][unit_index]
        unit_data['correlogram_bins'] = self.correlogram_bins

        unit_data['wide_correlograms'] = self.wide_correlograms[unit_index]
        unit_data['wide_bins'] = self.wide_bins

        try:
            unit_data['unit_location'] = self.unit_locations[unit_index]
        except:
            unit_data['unit_location'] = None

        unit_data['binned_spikes'], _ = np.histogram(unit_data['spikes'], bins=20)
        unit_data['scaled_templates'] = self.scaled_templates.get(unit_index)
        unit_data['scaled_stds'] = self.scaled_stds.get(unit_index)
        unit_data['scaled_perc'] = self.scaled_perc.get(unit_index)

        unit_data['channel_locations'] = self.channel_locations

        isi_violations_ratio = self.metrics['isi_violations_ratio']
        if isi_violations_ratio is not None:
            unit_data['isi'] = isi_violations_ratio.get(unit_index)
        else:
            unit_data['isi'] = None

        return unit_data

